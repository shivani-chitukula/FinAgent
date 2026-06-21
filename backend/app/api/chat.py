import json
import time
import asyncio
from datetime import datetime
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.db.models import Message, User, ChatSession
from app.db.database import get_db
from app.api.user import get_current_user
from app.api.sessions import get_current_session
from app.schemas import ChatQuery
from app.db.schemas import SenderEnum
from app.core.redis_client import redis_client
from app.core.config import config
from app.agent.graph import multi_agent_graph

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Redis conversation history helpers ────────────────────────────────────────

async def load_conversation_history(user_id: UUID, session_id: UUID) -> list[BaseMessage]:
    """Load conversation history from Redis cache (fast path) or return empty list."""
    redis_key = f"chat:history:{user_id}:{session_id}"
    history_json = await redis_client.get(redis_key)

    if not history_json:
        return []

    history = []
    for msg in json.loads(history_json):
        if msg["sender"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        else:
            history.append(AIMessage(content=msg["content"]))
    return history


async def save_conversation_to_redis(user_id: UUID, session_id: UUID, history: list[BaseMessage]):
    """Persist conversation history to Redis with a TTL to avoid unbounded growth."""
    redis_key = f"chat:history:{user_id}:{session_id}"
    history_data = [
        {
            "sender": "user" if isinstance(msg, HumanMessage) else "bot",
            "content": msg.content,
        }
        for msg in history
    ]
    await redis_client.set(
        redis_key,
        json.dumps(history_data),
        ex=config.REDIS_HISTORY_TTL,  # default 3600 seconds
    )


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
async def chat_endpoint(
    chat_query: ChatQuery,
    session: ChatSession = Depends(get_current_session),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = chat_query.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # ── Retrieve auth token from Redis (stored by get_current_user) ───────────
    token_key = f"user:{current_user.user_id}:auth_token"
    token = await redis_client.get(token_key)

    # ── Check query response cache in Redis (fast path) ───────────────────────
    t_start = time.perf_counter()
    cache_key = f"chat:response:{session.session_id}:{query}"
    try:
        cached_response = await redis_client.get(cache_key)
        if cached_response:
            data = json.loads(cached_response)
            latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
            
            def save_cached_messages():
                from app.db.database import SessionLocal
                local_db = SessionLocal()
                try:
                    user_msg = Message(
                        session_id=session.session_id,
                        content=query,
                        sender=SenderEnum.user,
                        timestamp=datetime.utcnow(),
                        message_metadata={"latency_ms": latency_ms, "cache_hit": True},
                    )
                    local_db.add(user_msg)
                    
                    ai_msg = Message(
                        session_id=session.session_id,
                        content=data["ai_response"],
                        sender=SenderEnum.bot,
                        timestamp=datetime.utcnow(),
                        message_metadata={
                            "latency_ms": latency_ms,
                            "cache_hit": True,
                            "intent": data.get("intent"),
                        },
                    )
                    local_db.add(ai_msg)
                    local_db.commit()
                    local_db.refresh(user_msg)
                    local_db.refresh(ai_msg)
                    local_db.expunge_all()
                    return user_msg, ai_msg
                finally:
                    local_db.close()
            
            user_msg, ai_msg = await asyncio.to_thread(save_cached_messages)
            return {
                "user_message_id": str(user_msg.message_id),
                "ai_response": data["ai_response"],
                "intent": data.get("intent"),
                "latency_ms": latency_ms,
                "cache_hit": True,
            }
    except Exception:
        pass

    # ── Load conversation history from Redis ──────────────────────────────────
    conversation_history = await load_conversation_history(
        current_user.user_id, session.session_id
    )
    cache_hit = len(conversation_history) > 0
    conversation_history.append(HumanMessage(content=query))

    # ── Build graph state ──────────────────────────────────────────────────────
    graph_state = {
        "messages": conversation_history,
        "is_authenticated": getattr(current_user, "is_authenticated", True),
        "user_id": str(current_user.user_id),
        "reauth_required": False,
        "auth_token": token,
        "current_intent": None,
        "session_id": str(session.session_id),
    }

    # ── Invoke the multi-agent graph ───────────────────────────────────────────
    result = await multi_agent_graph.ainvoke(
        graph_state,
        config={
            "configurable": {
                "user_id": str(current_user.user_id),
                "session_id": str(session.session_id),
                # thread_id scopes the InMemorySaver checkpoint per session
                "thread_id": str(session.session_id),
            }
        },
    )

    latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

    # ── Extract AI response ────────────────────────────────────────────────────
    ai_response: Optional[str] = None
    if "messages" in result and len(result["messages"]) > len(conversation_history):
        ai_response = result["messages"][-1].content

    # ── Persist messages to PostgreSQL (background thread) ────────────────────
    def save_messages():
        from app.db.database import SessionLocal
        local_db = SessionLocal()
        try:
            user_msg = Message(
                session_id=session.session_id,
                content=query,
                sender=SenderEnum.user,
                timestamp=datetime.utcnow(),
                message_metadata={"latency_ms": latency_ms, "cache_hit": cache_hit},
            )
            local_db.add(user_msg)

            ai_msg = None
            if ai_response:
                ai_msg = Message(
                    session_id=session.session_id,
                    content=ai_response,
                    sender=SenderEnum.bot,
                    timestamp=datetime.utcnow(),
                    message_metadata={
                        "latency_ms": latency_ms,
                        "cache_hit": cache_hit,
                        "intent": result.get("current_intent"),
                    },
                )
                local_db.add(ai_msg)

            local_db.commit()
            local_db.refresh(user_msg)
            if ai_msg:
                local_db.refresh(ai_msg)
            
            # Detach models from local_db session to allow safe cross-thread read access
            local_db.expunge_all()
            return user_msg, ai_msg
        finally:
            local_db.close()

    user_msg, ai_msg = await asyncio.to_thread(save_messages)

    # ── Update Redis conversation cache ────────────────────────────────────────
    await save_conversation_to_redis(
        current_user.user_id, session.session_id, result["messages"]
    )

    if ai_response:
        try:
            # Do NOT cache transactions (state-changing operations) or failed/error messages
            is_transaction = result.get("current_intent") == "transaction"
            is_error = any(word in ai_response.lower() for word in ["sorry", "failed", "unsuccessful", "error"])
            if not is_transaction and not is_error:
                await redis_client.set(
                    cache_key,
                    json.dumps({"ai_response": ai_response, "intent": result.get("current_intent")}),
                    ex=config.REDIS_HISTORY_TTL,
                )
        except Exception:
            pass

    return {
        "user_message_id": str(user_msg.message_id),
        "ai_response": ai_response,
        "intent": result.get("current_intent"),
        "latency_ms": latency_ms,
        "cache_hit": cache_hit,
    }
