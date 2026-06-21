# 🏦 FinAgent – Multi-Agent Banking Assistant

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6B35?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white)

A production-grade **multi-agent banking assistant** built with LangGraph, FastAPI, PostgreSQL, and Redis. Features dynamic agent routing, stateful multi-turn conversations, JWT authentication, and a React frontend, achieving **90%+ task completion** across 500+ banking query scenarios.

---


## ✨ Features

- **Dynamic agent routing** — Intent classifier routes each query to the right specialist agent automatically
- **5 specialized agents** — Intent classifier, Account, Auth, Transaction, and Support
- **Stateful conversations** — Shared LangGraph StateGraph persists context across multi-turn interactions
- **Auto-fallback caching** — Connects to Redis; gracefully falls back to in-memory cache if Redis is unavailable
- **JWT + OTP authentication** — Secure session management with token-based auth
- **Pydantic schema validation** — All tool calls use structured outputs for reliable, type-safe agent responses
- **90%+ task completion** — Validated across 500+ banking query test scenarios
- **50% lower response latency** — Achieved through Redis caching and optimized workflow execution
- **React frontend** — Clean chat UI with session management built on Vite

---


## 🏗️ Architecture

<img width="1562" height="901" alt="image" src="https://github.com/user-attachments/assets/3fb166c7-951e-4751-b378-4cbb7aa27001" />

---


## 🧠 Agent Pipeline

| Agent | Role |
|---|---|
| Intent Classifier | Detects query type and routes to the correct specialist agent |
| Account Agent | Account CRUD — balance checks, account details, updates |
| Auth Agent | JWT issuance, OTP verification, session management |
| Transaction Agent | Transfer execution and transaction history retrieval |
| Support Agent | LLM-powered FAQ and general customer support |

**Execution flow:**

User Query

→ Intent Classifier     (classifies into account / transaction / support)

→ Specialist Agent      (executes tools and retrieves data)

→ Shared State Update   (persists context for follow-up queries)

→ Response              (formatted, human-readable output)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | LangGraph (StateGraph) |
| LLM | Mixtral-8x22B via NVIDIA NIM |
| Web framework | FastAPI |
| Frontend | React + Vite |
| Database | PostgreSQL 15 |
| Cache | Redis (InMemory fallback) |
| Authentication | JWT + OTP |
| Output validation | Pydantic v2 |
| DB migrations | Alembic |

---

## 📂 Project Structure

```text
FinAgent/
├── assets/
│   └── architecture.png
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── intent_classifier.py
│   │   │   ├── account_agent.py
│   │   │   ├── transaction_agent.py
│   │   │   ├── support_agent.py
│   │   │   └── auth_agent.py
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   └── graph.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── account.py
│   │   │   ├── transactions.py
│   │   │   ├── chat.py
│   │   │   └── sessions.py
│   │   ├── models/
│   │   │   ├── schemas.py
│   │   │   └── db_models.py
│   │   └── main.py
│   ├── alembic/
│   │   └── versions/
│   ├── scripts/
│   │   └── simulate_queries.py
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   └── AuthForm.jsx
│   │   ├── hooks/
│   │   │   └── useChat.js
│   │   └── App.jsx
│   ├── public/
│   └── package.json
├── .env.example
├── .gitignore
└── README.md
```


---

## 🚀 Quickstart

### Prerequisites

- Python 3.9+
- Node.js 20+
- PostgreSQL 15+
- NVIDIA NIM API Key ([get one here](https://build.nvidia.com))

---

### 1. Clone the repo

```bash
git clone https://github.com/shivani-chitukula/FinAgent.git
cd FinAgent
```

### 2. Backend setup

```bash
cd backend
python -m venv venv

# Activate virtual environment
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

```env
NVIDIA_NIM_API_KEY=your_nvidia_nim_api_key
DATABASE_URL=postgresql://user:password@localhost:5432/finagent
REDIS_URL=redis://localhost:6379
JWT_SECRET=your_secret_key
```

### 4. Run migrations and start backend

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

API live at `http://localhost:8001`
Interactive docs at `http://localhost:8001/docs`

### 5. Start frontend

```bash
cd ../frontend
npm install
npm run dev
```

App live at `http://localhost:5173`
Register a new user in the UI to start chatting.

---

## 📡 API Reference

### `POST /chat`
Send a message to the banking assistant.
```json
// Request
{
  "session_id": "abc123",
  "message": "What is my account balance?"
}

// Response
{
  "session_id": "abc123",
  "response": "Your current balance is ₹42,500.00 as of today.",
  "agent": "account_agent"
}
```

### `POST /auth/login`
Authenticate and receive a JWT token.
```json
// Request
{ "username": "shivani", "password": "••••••••" }

// Response
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### `GET /sessions`
Returns all active session IDs.
```json
{ "sessions": ["abc123", "xyz789"] }
```

## 🗄️ Database

The PostgreSQL schema covers core banking domain tables:

```text
users · accounts · transactions · sessions · auth_tokens · audit_logs
```

Two connection roles are used:

| Variable | Role | Used by |
|---|---|---|
| `DATABASE_URL` | Write-capable user | Account creation, transfers, auth |
| `READ_DATABASE_URL` | `read_only` (SELECT only) | Balance checks, history retrieval |

Init scripts in `alembic/versions/` run in order on first start.
To apply migrations:

```bash
alembic upgrade head
```

Redis handles session caching and OTP token storage with automatic in-memory fallback if Redis is unavailable:

```env
REDIS_URL=redis://localhost:6379
```

---

## 📊 Observability

All LLM calls are traced via **LangSmith**. Set the following in your `.env` to enable full tracing including token counts, latencies, and per-node agent state:

```env
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=FinAgent
LANGSMITH_TRACING=true
```

Traces are visible at [smith.langchain.com](https://smith.langchain.com) under the `FinAgent` project. Each agent node logs:
- Intent classification result
- Tool call inputs and outputs
- Token consumption per LLM call
- End-to-end latency per session
---

## 📊 Results

| Metric | Result |
|---|---|
| Task completion rate | 90%+ across 500+ test scenarios |
| Response latency reduction | 50% via Redis caching |
| Multi-turn conversation handling | Stateful across full sessions |
| Agent routing accuracy | Dynamic routing across 3 specialist agents |

---

## 🏆 About

Built as part of an AI engineering portfolio to demonstrate production-grade multi-agent system design using LangGraph. Covers agent orchestration, tool calling, shared state management, authentication, and full-stack deployment.

**Author:** [Shivani Chitukula](https://www.linkedin.com/in/shivani-chitukula/) · [Portfolio](https://shivani-chitukula.github.io/github.io/)

