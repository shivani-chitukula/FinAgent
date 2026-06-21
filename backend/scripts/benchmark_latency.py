"""
benchmark_latency.py
────────────────────────────────────────────────────────────────────────────────
Benchmarks /chat endpoint latency with and without Redis conversation cache
to validate the "50% latency reduction via Redis caching" metric claim.

Usage:
    python scripts/benchmark_latency.py --base-url http://localhost:8000 \
                                         --email test@example.com \
                                         --password testpass123

How it works:
    Phase 1 (Cold / No Cache):
        Start a fresh session each time. Redis has no history → cold path.
        Each request goes straight to the LLM with no cached context.

    Phase 2 (Warm / With Cache):
        Re-use the same session. Redis already has conversation history.
        Each request loads history from Redis (O(1)) before LLM call.

    The measured latency includes: Redis lookup + LLM call + DB write.
    The difference isolates the Redis history-loading overhead.

Requirements:
    pip install httpx rich
"""

import argparse
import asyncio
import json
import statistics
import time

import httpx

try:
    from rich.console import Console
    from rich.table import Table

    console = Console()
except ImportError:
    print("Install rich: pip install rich")
    import sys
    sys.exit(1)

# Queries used for benchmarking (varied enough to trigger real LLM responses)
BENCHMARK_QUERIES = [
    "What is my account balance?",
    "Show me my account details.",
    "What type of account do I have?",
    "What currency is my account in?",
    "Can you help me with banking questions?",
    "What transactions have I made recently?",
    "How do I transfer money?",
    "What is the minimum balance required?",
    "Tell me about savings accounts.",
    "Is my account currently active?",
]


async def register_and_login(client: httpx.AsyncClient, base_url: str, email: str, password: str) -> str:
    await client.post(f"{base_url}/register", json={
        "name": "Benchmark User",
        "email": email,
        "phone_number": "8888888888",
        "password": password,
    })
    resp = await client.post(f"{base_url}/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


async def create_session(client: httpx.AsyncClient, base_url: str, token: str) -> str:
    resp = await client.post(
        f"{base_url}/sessions/initialize",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json()["session_id"]


async def send_and_time(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    query: str,
) -> float:
    """Send a chat query and return wall-clock latency in milliseconds."""
    t0 = time.perf_counter()
    try:
        await client.post(
            f"{base_url}/chat/",
            json={"query": query},
            headers={"Authorization": f"Bearer {token}"},
            timeout=90.0,
        )
    except Exception:
        pass  # Still record elapsed time even on error
    return (time.perf_counter() - t0) * 1000  # ms


async def run_cold_phase(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    queries: list[str],
    runs_per_query: int,
) -> list[float]:
    """
    Cold phase: create a NEW session before every query so Redis has no history.
    """
    latencies = []
    for query in queries:
        for _ in range(runs_per_query):
            await create_session(client, base_url, token)  # fresh session = cold cache
            latency = await send_and_time(client, base_url, token, query)
            latencies.append(latency)
    return latencies


async def run_warm_phase(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    queries: list[str],
    runs_per_query: int,
) -> list[float]:
    """
    Warm phase: reuse the SAME session so Redis holds growing conversation history.
    First query warms the cache; subsequent queries benefit from it.
    """
    await create_session(client, base_url, token)
    latencies = []
    # Warm-up: send 3 messages to populate Redis cache
    warmup = ["What is my balance?", "Tell me about accounts.", "How do transfers work?"]
    for q in warmup:
        await send_and_time(client, base_url, token, q)

    # Actual benchmark
    for query in queries:
        for _ in range(runs_per_query):
            latency = await send_and_time(client, base_url, token, query)
            latencies.append(latency)
    return latencies


def summarise(latencies: list[float]) -> dict:
    return {
        "count": len(latencies),
        "mean_ms": round(statistics.mean(latencies), 2),
        "median_ms": round(statistics.median(latencies), 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "stdev_ms": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0.0,
        "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
    }


async def run_benchmark(base_url: str, email: str, password: str, runs: int):
    console.print("\n[bold blue]╔═══════════════════════════════════════════╗")
    console.print("[bold blue]║   BankingBot – Redis Latency Benchmark    ║")
    console.print("[bold blue]╚═══════════════════════════════════════════╝\n")

    async with httpx.AsyncClient(base_url=base_url) as http:
        console.print("[cyan]→ Authenticating...")
        token = await register_and_login(http, base_url, email, password)
        console.print("[green]✓ Authenticated\n")

        console.print(f"[yellow]→ Phase 1: Cold cache benchmark ({runs} runs/query, {len(BENCHMARK_QUERIES)} queries)...")
        cold_latencies = await run_cold_phase(http, base_url, token, BENCHMARK_QUERIES, runs)
        console.print("[green]✓ Cold phase complete\n")

        console.print(f"[yellow]→ Phase 2: Warm cache benchmark ({runs} runs/query, {len(BENCHMARK_QUERIES)} queries)...")
        warm_latencies = await run_warm_phase(http, base_url, token, BENCHMARK_QUERIES, runs)
        console.print("[green]✓ Warm phase complete\n")

    cold_stats = summarise(cold_latencies)
    warm_stats = summarise(warm_latencies)

    reduction_pct = (
        (cold_stats["mean_ms"] - warm_stats["mean_ms"]) / cold_stats["mean_ms"] * 100
        if cold_stats["mean_ms"] > 0 else 0
    )

    # ── Results Table ──────────────────────────────────────────────────────────
    table = Table(title="Latency Results (milliseconds)", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Cold (No Cache)", justify="right")
    table.add_column("Warm (Redis Cache)", justify="right")
    table.add_column("Reduction", justify="right", style="yellow bold")

    metrics = [
        ("Mean", "mean_ms"),
        ("Median", "median_ms"),
        ("Min", "min_ms"),
        ("Max", "max_ms"),
        ("Std Dev", "stdev_ms"),
        ("P95", "p95_ms"),
    ]
    for label, key in metrics:
        cold_v = cold_stats[key]
        warm_v = warm_stats[key]
        diff = ((cold_v - warm_v) / cold_v * 100) if cold_v > 0 else 0
        color = "green" if diff > 0 else "red"
        table.add_row(
            label,
            f"{cold_v} ms",
            f"{warm_v} ms",
            f"[{color}]{diff:+.1f}%[/{color}]",
        )

    console.print(table)

    # ── Summary ────────────────────────────────────────────────────────────────
    color = "green" if reduction_pct >= 50 else "yellow" if reduction_pct >= 25 else "red"
    console.print(f"\n[bold {color}]Mean Latency Reduction: {reduction_pct:.1f}%[/bold {color}]")

    if reduction_pct >= 50:
        console.print("[green]✓ METRIC VALIDATED: 50%+ latency reduction via Redis caching![/green]")
    else:
        console.print(f"[yellow]⚠ Target is 50%. Current: {reduction_pct:.1f}%. "
                       "Ensure Redis is running and the server is warm.[/yellow]")

    # Save report
    report = {
        "cold_cache": cold_stats,
        "warm_cache_redis": warm_stats,
        "mean_latency_reduction_pct": round(reduction_pct, 2),
        "metric_validated": reduction_pct >= 50,
    }
    with open("latency_report.json", "w") as f:
        json.dump(report, f, indent=2)
    console.print("\n[dim]Report saved to latency_report.json[/dim]")


def main():
    parser = argparse.ArgumentParser(description="BankingBot Redis latency benchmark")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default="benchuser@bankbot.dev")
    parser.add_argument("--password", default="BenchPass@123")
    parser.add_argument("--runs", type=int, default=3,
                        help="Runs per query in each phase (default: 3)")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.base_url, args.email, args.password, args.runs))


if __name__ == "__main__":
    main()
