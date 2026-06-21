# 🏦 BankingBot – Multi-Agent Banking Assistant

A production-grade **multi-agent banking chatbot** built with LangGraph, FastAPI, PostgreSQL, and an in-memory/Redis fallback caching system. The chatbot features a React UI, intelligent agent routing, and full conversation memory.

---

## 📂 Project Structure

```text
FinAgent/ (Monorepo Root)
├── backend/            # FastAPI Backend & LangGraph Agent
│   ├── app/            # Core application code
│   ├── alembic/        # Database migrations
│   ├── scripts/        # Benchmarking & simulation scripts
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/           # React + Vite UI
│   ├── src/            # Components, pages, hooks, utilities
│   ├── public/         # Static assets
│   └── package.json
└── README.md           # Unified instructions (this file)
```

---

## 🏗️ Architecture

```text
User Query
    │
    ▼
┌──────────────────────────────────────────────────────┐
│              LangGraph Multi-Agent Graph             │
│                                                      │
│   ┌──────────────────┐                               │
│   │  intent_classifier│  ← classifies every query   │
│   └────────┬─────────┘                               │
│            │                                         │
│    ┌───────┼──────────┐                              │
│    ▼       ▼          ▼                              │
│ account  transaction  help                           │
│ _info    _agent       _agent                         │
│ _agent   (transfer,   (LLM-powered                   │
│ (CRUD)   history)     FAQ/support)                   │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  FastAPI REST Layer                                  │
│  /auth  /account  /transactions  /chat  /sessions    │
└──────────────────────────────────────────────────────┘
        │                          │
        ▼                          ▼
   PostgreSQL                   Redis / InMemoryFallback
  (persistent DB)         (conversation cache + auth tokens)
```

---

## 🚀 Running Locally

### Prerequisites
* Python 3.9+
* Node.js 20+
* PostgreSQL 15+
* An NVIDIA NIM API Key (configured in `backend/.env`)

---

### 1️⃣ Start the Backend
Navigate to the `backend` folder, activate the virtual environment, and run the FastAPI server:

```bash
cd backend
venv\Scripts\activate      # On Windows (Command Prompt/PowerShell)
uvicorn app.main:app --reload --port 8001
```

* **Interactive API Documentation:** Open [http://localhost:8001/docs](http://localhost:8001/docs) to explore the API.

---

### 2️⃣ Start the Frontend
Navigate to the `frontend` folder and start the Vite development server:

```bash
cd frontend
npm run dev
```

* **Application URL:** Open [http://localhost:5173](http://localhost:5173) in your browser.
* *Note: You can register a new user directly in the UI to log in and start chatting.*

---

## 📡 Key Features
* **Multi-Agent Orchestration**: Utilizes a StateGraph to route user intents dynamically to Account, Transaction, or Support specialists.
* **Auto-Fallback Caching**: Connects automatically to Redis, but falls back gracefully to a task-safe in-memory cache if Redis is not running.
* **Stateful Conversations**: Remembers chat histories across sessions and handles incomplete queries gracefully.
* **Conversational Formatting**: Translates raw database tables or JSON outputs into friendly, human-readable text blocks.
