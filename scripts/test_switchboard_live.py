"""Live test of the Switchboard with Grok API."""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                if val and key.strip():
                    os.environ.setdefault(key.strip(), val.strip())

from src.fleet.switchboard import (
    Switchboard, NoticeBoard, TaskType, TaskPriority, CostTier, classify_task,
)
from src.ops.calendar_clock import Calendar, TimeClock


def test_providers():
    board = NoticeBoard()
    switch = Switchboard(board)

    print("=" * 60)
    print("  SCBE SWITCHBOARD — Provider Status")
    print("=" * 60)
    for p in switch.available_providers():
        status = "READY" if p["available"] else "NO KEY"
        cost = p["cost_per_1k_tokens"]
        print(f"  {p['provider']:15} {status:8} {p['tier']:10} ${cost:.4f}/1k")
    print()


def test_classification():
    print("=== TASK CLASSIFICATION ===")
    for prompt in [
        "Write unit tests for the auth module",
        "Research competitor products in AI safety",
        "Write a blog post about hyperbolic geometry",
        "Evaluate governance pipeline security",
        "Summarize this 50-page report",
        "Design the database schema for user sessions",
    ]:
        tt = classify_task(prompt)
        print(f"  [{tt.value:12}] {prompt}")
    print()


async def test_grok_live():
    board = NoticeBoard()
    switch = Switchboard(board)

    print("=== LIVE GROK EXECUTION ===")
    ticket = switch.submit(
        "You are the Grok node in SCBE-AETHERMOORE fleet. "
        "Say: GROK ONLINE. Then in one sentence, describe what "
        "an AI governance framework using hyperbolic geometry does.",
        task_type=TaskType.ANALYSIS,
        priority=TaskPriority.NORMAL,
        max_cost=CostTier.STANDARD,
    )
    result = await switch.execute(ticket.ticket_id)
    print(f"Status:   {result.status}")
    print(f"Provider: {result.assigned_provider}")
    print(f"Model:    {result.assigned_model}")
    print(f"Result:   {result.result}")
    print()

    print("=== NOTICE BOARD ===")
    for notice in board.read_all():
        print(f"  [{notice.status:8}] {notice.author:12} | {notice.message[:70]}")
    print()
    print(f"Board: {board.summary()}")
    print()


def test_calendar():
    print("=== CALENDAR — SCBE DEADLINES ===")
    cal = Calendar.load_scbe_defaults()
    print(f"Summary: {cal.summary()}")
    print()

    print("Upcoming (30 days):")
    for e in cal.upcoming(30):
        urgency = "URGENT" if e.is_urgent else "OVERDUE" if e.is_overdue else "ok"
        print(f"  [{urgency:7}] {e.days_remaining:3d}d | {e.title} ({e.due_date})")
    print()

    print("Alerts:")
    for a in cal.alerts():
        print(f"  [{a['severity']:8}] {a['event']['title']}")
    print()


def test_timeclock():
    print("=== TIMECLOCK — Provider Budgets ===")
    tc = TimeClock.load_scbe_defaults()
    status = tc.status()
    print(f"Session: {status['session_duration_minutes']} min")
    print()
    for name, budget in status["budgets"].items():
        print(f"  {name:15} {budget['daily']}")
    print()
    print(f"Keys needing rotation: {status['keys_needing_rotation']}")
    print()


if __name__ == "__main__":
    test_providers()
    test_classification()
    test_calendar()
    test_timeclock()

    # Only run live Grok test if key is available
    if os.environ.get("XAI_API_KEY"):
        asyncio.run(test_grok_live())
    else:
        print("Skipping live Grok test — XAI_API_KEY not set")
