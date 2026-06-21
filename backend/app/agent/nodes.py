import json
import asyncio
from datetime import datetime
from typing import Literal, Optional

from langsmith import traceable
from langchain_core.messages import AIMessage, HumanMessage

from langgraph.graph import END
from langgraph.types import Command

from .state import OverallState
from .utils import create_llm, format_conversation, extract_tool_schemas
from .prompts import TOOL_CALLING_PROMPT, MISSING_INFO_PROMPT, HELP_AGENT_PROMPT
from app.schemas import FunctionCallPayload
from app.shared import client
from app.agent.tools import (
    create_transaction_tool,
    create_account,
    get_account_info,
    update_account_info,
    delete_account,
    get_transaction_tool,
    list_transactions_by_account_tool,
)


# ── Helper: write AgentEvent to DB ────────────────────────────────────────────

def _write_agent_event(session_id: str, agent_name: str, event_type: str, payload: dict):
    """
    Persist an AgentEvent record to PostgreSQL for metric tracking.
    Runs synchronously in a thread-pool via asyncio.to_thread at call site.
    """
    try:
        from app.db.database import SessionLocal
        from app.db.models import AgentEvent

        db = SessionLocal()
        try:
            event = AgentEvent(
                session_id=session_id,
                agent_name=agent_name,
                event_type=event_type,
                payload=payload,
                created_at=datetime.utcnow(),
            )
            db.add(event)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        # Never crash the agent because of a logging failure
        print(f"[AgentEvent] Failed to write event: {exc}")


async def write_agent_event(session_id: Optional[str], agent_name: str, event_type: str, payload: dict):
    """Async wrapper so agents can await DB writes without blocking."""
    if not session_id:
        return
    await asyncio.to_thread(_write_agent_event, session_id, agent_name, event_type, payload)


# ── Intent Classifier ─────────────────────────────────────────────────────────

@traceable(client=client, project_name="bank-bot", name="intent-classify", run_type="chain")
async def intent_classifier(
    state: OverallState,
) -> Command[Literal["account_info_agent", "transaction_agent", "help_agent", "__end__"]]:
    """
    Classify the user's intent based on the latest message.
    Routes to account_info_agent, transaction_agent, or help_agent.
    """
    last_user_msg = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )

    if not last_user_msg:
        return Command(goto="__end__")

    prompt = (
        "Classify the user's banking query into exactly one of these categories: "
        "account_info, transaction, help.\n\n"
        f'User query: "{last_user_msg.content}"\n\n'
        "Rules:\n"
        "- account_info: balance, account details, create/update/close account\n"
        "- transaction: transfer money, send funds, payment, view transaction history\n"
        "- help: everything else — FAQs, how-to, troubleshooting, general questions\n\n"
        "Respond with ONLY one word: account_info, transaction, or help."
    )

    llm = create_llm()
    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    intent = response.content.strip().lower()

    valid_intents = {"account_info", "transaction", "help"}
    if intent not in valid_intents:
        intent = "help"

    next_agent = f"{intent}_agent"

    await write_agent_event(
        state.get("session_id"), "intent_classifier", "COMPLETED",
        {"intent": intent, "query": last_user_msg.content}
    )

    return Command(
        goto=next_agent,
        update={"current_intent": intent},
    )


# ── Account Info Agent ────────────────────────────────────────────────────────

@traceable(client=client, project_name="bank-bot", name="account-info", run_type="chain")
async def account_info_agent(
    state: OverallState,
) -> Command[Literal["__end__"]]:
    """
    Handles all account-related operations:
    create_account, get_account_info, update_account_info, delete_account.
    """
    session_id = state.get("session_id")
    await write_agent_event(session_id, "account_info_agent", "STARTED", {})

    tools = [create_account, get_account_info, update_account_info, delete_account]
    llm = create_llm()
    tool_schemas = extract_tool_schemas(tools)
    tool_names = [tool.name for tool in tools]

    prompt = TOOL_CALLING_PROMPT.format(
        tool_schemas_json=json.dumps(tool_schemas),
        chat_history=format_conversation(state["messages"]),
        user_input=state["messages"][-1].content,
    )

    try:
        raw = await llm.ainvoke([{"role": "user", "content": prompt}])
        content = raw.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        response = FunctionCallPayload.model_validate_json(content)
    except Exception as exc:
        error_msg = AIMessage(content="I had trouble processing your account request. Please try again.")
        await write_agent_event(session_id, "account_info_agent", "FAILED", {"error": str(exc)})
        return Command(goto="__end__", update={"messages": state["messages"] + [error_msg]})

    # Filter out hallucinated parameters
    tool_map = {tool.name: tool for tool in tools}
    if response.tool in tool_map:
        tool_args = set(tool_map[response.tool].args.keys())
        response.provided = {k: v for k, v in response.provided.items() if k in tool_args}
        response.missing = [k for k in response.missing if k in tool_args]

    # If tool is missing or parameters incomplete, ask for missing info
    missing_fields = [f for f in response.missing if f != "token"]
    if (
        response.tool is None
        or response.tool not in tool_names
        or missing_fields
    ):
        missing_prompt = MISSING_INFO_PROMPT.format(missing_info_field=missing_fields or response.tool)
        missing_response = await llm.ainvoke([{"role": "user", "content": missing_prompt}])
        error_msg = AIMessage(content=missing_response.content)
        await write_agent_event(
            session_id, "account_info_agent", "INCOMPLETE",
            {"missing": missing_fields, "tool": response.tool}
        )
        return Command(goto="__end__", update={"messages": state["messages"] + [error_msg]})

    # Inject auth token automatically
    response.provided["token"] = state.get("auth_token")
    try:
        result = await tool_map[response.tool].ainvoke(response.provided)
        format_prompt = (
            "You are a friendly and polite banking assistant. Formulate a conversational final response for the user "
            "based on the following tool execution result. Translate any JSON, Python dictionaries, IDs, or raw data into a clean, "
            "natural-language message. Do not show raw JSON or dict syntax like '{key: value}' to the user. Make sure to present "
            "important information (like account numbers or balances) clearly and user-friendly.\n\n"
            f"User message: {state['messages'][-1].content}\n"
            f"Tool result: {result}\n\n"
            "Final Response:"
        )
        format_response = await llm.ainvoke([{"role": "user", "content": format_prompt}])
        response_msg = AIMessage(content=format_response.content.strip())
        await write_agent_event(
            session_id, "account_info_agent", "COMPLETED",
            {"tool": response.tool, "result_preview": str(result)[:200]}
        )
    except Exception as exc:
        response_msg = AIMessage(content=f"The account operation failed: {exc}")
        await write_agent_event(session_id, "account_info_agent", "FAILED", {"error": str(exc)})

    return Command(goto="__end__", update={"messages": state["messages"] + [response_msg]})


# ── Transaction Agent ─────────────────────────────────────────────────────────

@traceable(client=client, project_name="bank-bot", name="transaction", run_type="chain")
async def transaction_agent(
    state: OverallState,
) -> Command[Literal["__end__"]]:
    """
    Handles all transaction operations:
    create_transaction, get_transaction, list_transactions_by_account.
    """
    session_id = state.get("session_id")
    await write_agent_event(session_id, "transaction_agent", "STARTED", {})

    tools = [
        create_transaction_tool,
        list_transactions_by_account_tool,
        get_transaction_tool,
    ]
    llm = create_llm()
    tool_schemas = extract_tool_schemas(tools)
    tool_names = [tool.name for tool in tools]

    prompt = TOOL_CALLING_PROMPT.format(
        tool_schemas_json=json.dumps(tool_schemas),
        chat_history=format_conversation(state["messages"]),
        user_input=state["messages"][-1].content,
    )

    try:
        raw = await llm.ainvoke([{"role": "user", "content": prompt}])
        content = raw.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        response = FunctionCallPayload.model_validate_json(content)
    except Exception as exc:
        error_msg = AIMessage(content="I had trouble processing your transaction request. Please try again.")
        await write_agent_event(session_id, "transaction_agent", "FAILED", {"error": str(exc)})
        return Command(goto="__end__", update={"messages": state["messages"] + [error_msg]})

    # Filter out hallucinated parameters
    tool_map = {tool.name: tool for tool in tools}
    if response.tool in tool_map:
        tool_args = set(tool_map[response.tool].args.keys())
        response.provided = {k: v for k, v in response.provided.items() if k in tool_args}
        response.missing = [k for k in response.missing if k in tool_args]

    missing_fields = [f for f in response.missing if f != "token"]
    if (
        response.tool is None
        or response.tool not in tool_names
        or missing_fields
    ):
        missing_prompt = MISSING_INFO_PROMPT.format(missing_info_field=missing_fields or response.tool)
        missing_response = await llm.ainvoke([{"role": "user", "content": missing_prompt}])
        error_msg = AIMessage(content=missing_response.content)
        await write_agent_event(
            session_id, "transaction_agent", "INCOMPLETE",
            {"missing": missing_fields, "tool": response.tool}
        )
        return Command(goto="__end__", update={"messages": state["messages"] + [error_msg]})

    response.provided["token"] = state.get("auth_token")
    try:
        result = await tool_map[response.tool].ainvoke(response.provided)
        format_prompt = (
            "You are a friendly and polite banking assistant. Formulate a conversational final response for the user "
            "based on the following tool execution result. Translate any JSON, Python dictionaries, IDs, or raw data into a clean, "
            "natural-language message. Do not show raw JSON or dict syntax like '{key: value}' to the user. Make sure to present "
            "important information (like transaction IDs or reference numbers) clearly and user-friendly.\n\n"
            f"User message: {state['messages'][-1].content}\n"
            f"Tool result: {result}\n\n"
            "Final Response:"
        )
        format_response = await llm.ainvoke([{"role": "user", "content": format_prompt}])
        response_msg = AIMessage(content=format_response.content.strip())
        await write_agent_event(
            session_id, "transaction_agent", "COMPLETED",
            {"tool": response.tool, "result_preview": str(result)[:200]}
        )
    except Exception as exc:
        response_msg = AIMessage(content=f"The transaction operation failed: {exc}")
        await write_agent_event(session_id, "transaction_agent", "FAILED", {"error": str(exc)})

    return Command(goto="__end__", update={"messages": state["messages"] + [response_msg]})


# ── Help / Support Agent ──────────────────────────────────────────────────────

@traceable(client=client, project_name="bank-bot", name="support", run_type="chain")
async def help_agent(
    state: OverallState,
) -> Command[Literal["__end__"]]:
    """
    LLM-powered customer support agent.
    Answers general banking questions, FAQs, and provides guidance.
    """
    session_id = state.get("session_id")
    await write_agent_event(session_id, "help_agent", "STARTED", {})

    llm = create_llm()
    user_input = state["messages"][-1].content if state["messages"] else ""

    prompt = HELP_AGENT_PROMPT.format(
        chat_history=format_conversation(state["messages"][:-1]),  # history without latest msg
        user_input=user_input,
    )

    try:
        raw = await llm.ainvoke([{"role": "user", "content": prompt}])
        response_content = raw.content.strip()
        await write_agent_event(session_id, "help_agent", "COMPLETED", {})
    except Exception as exc:
        response_content = (
            "I'm here to help! You can ask me about your account balance, "
            "transfer funds, or check transaction history. What would you like to do?"
        )
        await write_agent_event(session_id, "help_agent", "FAILED", {"error": str(exc)})

    response_msg = AIMessage(content=response_content)
    return Command(goto="__end__", update={"messages": state["messages"] + [response_msg]})
