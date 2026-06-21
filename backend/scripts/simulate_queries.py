"""
simulate_queries.py
────────────────────────────────────────────────────────────────────────────────
Simulates 500+ banking queries against the live BankingBot API.

Usage:
    python scripts/simulate_queries.py --base-url http://localhost:8000 \
                                       --email test@example.com \
                                       --password testpass123

Requirements:
    pip install httpx rich

What it measures:
    - Total queries sent (500+)
    - Successful responses (HTTP 200/201 + non-empty ai_response)
    - Failed responses
    - Task completion rate (%)
    - Per-intent breakdown
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from typing import Optional

import httpx

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import track
    console = Console()
except ImportError:
    print("Install rich for pretty output: pip install rich")
    sys.exit(1)


# ── Query Bank ────────────────────────────────────────────────────────────────

ACCOUNT_QUERIES = [
    "What is my account balance?",
    "Show me my account details.",
    "What type of account do I have?",
    "What currency is my account in?",
    "Can you show me my account info?",
    "How much money do I have?",
    "What is my current balance?",
    "Tell me my account number.",
    "Get my account information.",
    "Display my account summary.",
    "What is the balance in my savings account?",
    "I want to know my account status.",
    "Is my account active?",
    "Show balance for my account.",
    "Retrieve my account details please.",
    "How much is left in my account?",
    "View my account balance.",
    "Check my account.",
    "What accounts do I have?",
    "Give me a summary of my account.",
    "I'd like to create a new savings account with ₹5000.",
    "Open a current account with 10000 rupees.",
    "Create a savings account with balance 2000 in INR.",
    "I want to open a new account with 500 USD.",
    "Set up a new savings account for me.",
    "Open an account with initial balance of 15000.",
    "Create a checking account.",
    "I need a new bank account with 3000 balance.",
    "Can you open a current account in USD for me?",
    "Make a new account with 1000 rupees.",
    "Update my account type to current.",
    "Change my account currency to USD.",
    "Modify my account details.",
    "I want to upgrade my account.",
    "Switch my account to savings.",
    "Update my account info.",
    "Change my account type.",
    "Modify the currency on my account to EUR.",
    "Update my account to current type.",
    "I want to change my account settings.",
    "Close my account.",
    "Delete my bank account.",
    "I want to deactivate my account.",
    "Close the savings account.",
    "Shut down my account.",
]

TRANSACTION_QUERIES = [
    "Transfer 500 rupees from account 123456789012 to 987654321098.",
    "Send 1000 to account 111122223333.",
    "Pay 250 from my account 100200300400 to 500600700800.",
    "Transfer ₹2000 from 121212121212 to 343434343434.",
    "Send money 750 from 555566667777 to 888899990000.",
    "I want to transfer 300 from account 001002003004 to 005006007008.",
    "Make a payment of 5000 from 777788889999 to 111100002222.",
    "Send 150 from 333344445555 to 666677778888.",
    "Transfer 10000 rupees from 999900001111 to 222233334444.",
    "Pay 800 to account 444455556666 from 777788889999.",
    "Initiate a transfer of 500 from 123456789000 to 000987654321.",
    "Send 2500 from account 112233445566 to 998877665544.",
    "Transfer funds: 900 from 445566778899 to 123456000000.",
    "Move 3000 from 667788990011 to 554433221100.",
    "Send 400 from 100000000001 to 200000000002.",
    "Transfer 600 from 300000000003 to 400000000004.",
    "Pay 1500 to 500000000005 from 600000000006.",
    "Send 200 from 700000000007 to 800000000008.",
    "Transfer 750 from 900000000009 to 100000000000.",
    "Move 5500 from 110000000000 to 220000000000.",
    "Show me my transaction history for account 123456789012.",
    "List all transactions from account 987654321098.",
    "What transactions have I made from 111122223333?",
    "Get transaction history for account 444455556666.",
    "Show transactions for account 777788889999.",
    "List payments from account 001002003004.",
    "What are recent transactions on account 121212121212?",
    "Retrieve all transfers from account 333344445555.",
    "Transaction history for 555566667777 please.",
    "Show me all debits from 888899990000.",
    "Get details of transaction abc-123.",
    "Show transaction with ID xyz-456.",
    "Fetch transaction 789-abc.",
    "What happened in transaction ref-001?",
    "Details on transaction 000111.",
    "Get transaction with reference id txn-202401.",
    "Look up transaction with ID 2024-TXN-007.",
    "Check the status of transaction ABC123.",
    "Find transaction by ID: TX_9876.",
    "What is the status of my last transaction?",
]

HELP_QUERIES = [
    "What can you do?",
    "How do I transfer money?",
    "What banking services are available?",
    "Can you help me with my account?",
    "What is the minimum balance?",
    "How do I open a new account?",
    "What currencies are supported?",
    "How do I check my balance?",
    "What account types are available?",
    "Is there a transaction limit?",
    "How do I reset my password?",
    "Why did my transaction fail?",
    "What should I do if my account is locked?",
    "How does the banking bot work?",
    "What is the maximum transfer limit?",
    "How secure is this banking bot?",
    "Can I have multiple accounts?",
    "How long do transactions take?",
    "What is a reference ID?",
    "How do I report fraud?",
    "What happens if I enter the wrong account number?",
    "Can I cancel a transaction?",
    "What fees are charged for transfers?",
    "How often can I check my balance?",
    "What is a current account vs savings account?",
    "Do you support international transfers?",
    "What is INR?",
    "How do I close my account safely?",
    "Can I reopen a closed account?",
    "What documents are needed to open an account?",
    "How do I update my contact information?",
    "What is the interest rate on savings?",
    "How is my money protected?",
    "What is two-factor authentication?",
    "How do I get a statement?",
    "Can I set a spending limit?",
    "What is the daily transfer limit?",
    "How do I contact human support?",
    "Is there a mobile app?",
    "How do I log out securely?",
]


@dataclass
class SimResult:
    intent: str
    query: str
    success: bool
    status_code: int
    response_preview: str = ""
    error: str = ""


@dataclass
class SimStats:
    total: int = 0
    success: int = 0
    failed: int = 0
    by_intent: dict = field(default_factory=dict)

    @property
    def completion_rate(self) -> float:
        return (self.success / self.total * 100) if self.total else 0.0


# ── Core Simulation Logic ─────────────────────────────────────────────────────

async def register_and_login(client: httpx.AsyncClient, base_url: str, email: str, password: str) -> str:
    """Register (if needed) and login; return bearer token."""
    # Try registration
    await client.post(f"{base_url}/register", json={
        "name": "Simulation User",
        "email": email,
        "phone_number": "9999999999",
        "password": password,
    })

    # Login
    resp = await client.post(f"{base_url}/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


async def create_session(client: httpx.AsyncClient, base_url: str, token: str) -> str:
    """Create a new chat session and return session_id."""
    resp = await client.post(
        f"{base_url}/sessions/initialize",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json()["session_id"]


async def send_query(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    query: str,
    intent: str,
    sem: asyncio.Semaphore,
) -> SimResult:
    async with sem:
        try:
            resp = await client.post(
                f"{base_url}/chat/",
                json={"query": query},
                headers={"Authorization": f"Bearer {token}"},
                timeout=60.0,
            )
            data = resp.json()
            ai_response = data.get("ai_response") or ""
            success = resp.status_code in (200, 201) and bool(ai_response)
            return SimResult(
                intent=intent,
                query=query[:60] + "..." if len(query) > 60 else query,
                success=success,
                status_code=resp.status_code,
                response_preview=ai_response[:80] if ai_response else "",
            )
        except Exception as exc:
            return SimResult(
                intent=intent,
                query=query[:60],
                success=False,
                status_code=0,
                error=str(exc),
            )


def build_query_list():
    """
    Build a list of (intent, query) tuples totalling 500+.
    We repeat the base sets to reach the target count.
    """
    queries = []
    base = (
        [("account_info", q) for q in ACCOUNT_QUERIES]
        + [("transaction", q) for q in TRANSACTION_QUERIES]
        + [("help", q) for q in HELP_QUERIES]
    )
    # Cycle through base set until we hit 500
    target = 500
    while len(queries) < target:
        queries.extend(base)
    return queries[:target]


async def run_simulation(base_url: str, email: str, password: str, concurrency: int = 5):
    console.print("\n[bold blue]╔══════════════════════════════════════╗")
    console.print("[bold blue]║   BankingBot – Query Simulation      ║")
    console.print("[bold blue]╚══════════════════════════════════════╝\n")

    async with httpx.AsyncClient(base_url=base_url) as http:
        # Auth
        console.print("[cyan]→ Authenticating...")
        token = await register_and_login(http, base_url, email, password)
        console.print("[green]✓ Authenticated\n")

        # Session
        console.print("[cyan]→ Creating chat session...")
        await create_session(http, base_url, token)
        console.print("[green]✓ Session created\n")

        queries = build_query_list()
        console.print(f"[yellow]→ Sending {len(queries)} queries (concurrency={concurrency})...\n")

        sem = asyncio.Semaphore(concurrency)
        tasks = [
            send_query(http, base_url, token, q, intent, sem)
            for intent, q in queries
        ]
        results: list[SimResult] = await asyncio.gather(*tasks)

    # ── Compute stats ──────────────────────────────────────────────────────────
    stats = SimStats()
    stats.by_intent = {"account_info": {"total": 0, "success": 0},
                        "transaction": {"total": 0, "success": 0},
                        "help": {"total": 0, "success": 0}}

    for r in results:
        stats.total += 1
        if r.success:
            stats.success += 1
        else:
            stats.failed += 1
        if r.intent in stats.by_intent:
            stats.by_intent[r.intent]["total"] += 1
            if r.success:
                stats.by_intent[r.intent]["success"] += 1

    # ── Print results table ────────────────────────────────────────────────────
    table = Table(title="Simulation Results by Intent", show_header=True, header_style="bold cyan")
    table.add_column("Agent", style="bold")
    table.add_column("Queries Sent", justify="right")
    table.add_column("Successful", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Completion Rate", justify="right", style="yellow bold")

    for intent, d in stats.by_intent.items():
        rate = d["success"] / d["total"] * 100 if d["total"] else 0
        table.add_row(
            intent.replace("_", " ").title(),
            str(d["total"]),
            str(d["success"]),
            str(d["total"] - d["success"]),
            f"{rate:.1f}%",
        )

    # Total row
    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        str(stats.total),
        str(stats.success),
        str(stats.failed),
        f"[bold]{stats.completion_rate:.1f}%[/bold]",
    )

    console.print(table)

    # ── Summary ────────────────────────────────────────────────────────────────
    color = "green" if stats.completion_rate >= 90 else "yellow" if stats.completion_rate >= 70 else "red"
    console.print(f"\n[bold {color}]Overall Task Completion Rate: {stats.completion_rate:.1f}%[/bold {color}]")

    if stats.completion_rate >= 90:
        console.print("[green]✓ METRIC VALIDATED: 90%+ task completion achieved![/green]")
    else:
        console.print(f"[yellow]⚠ Target is 90%. Current: {stats.completion_rate:.1f}%[/yellow]")

    # Save report
    report = {
        "total_queries": stats.total,
        "successful": stats.success,
        "failed": stats.failed,
        "completion_rate_pct": round(stats.completion_rate, 2),
        "by_intent": stats.by_intent,
    }
    with open("simulation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    console.print("\n[dim]Report saved to simulation_report.json[/dim]")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BankingBot query simulation")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default="simuser@bankbot.dev")
    parser.add_argument("--password", default="SimPass@123")
    parser.add_argument("--concurrency", type=int, default=5,
                        help="Max concurrent requests (default: 5)")
    args = parser.parse_args()

    asyncio.run(run_simulation(args.base_url, args.email, args.password, args.concurrency))


if __name__ == "__main__":
    main()
