"""
Calendar + TimeClock — Operational Scheduling for SCBE
======================================================

Two systems in one:

1. **Calendar**: Deadlines, milestones, recurring events. Tracks grant
   deadlines, patent filings, content schedules, and deployment windows.

2. **TimeClock**: API key rotation, session timers, rate limit tracking,
   and cost budgeting per provider per day/week/month.

The notice board (from switchboard.py) receives calendar alerts and
timeclock events so all agents stay informed.

@module ops/calendar_clock
@layer Layer 13 (governance scheduling)
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# Calendar
# ═══════════════════════════════════════════════════════════════

class EventType(str, Enum):
    DEADLINE = "deadline"       # Hard deadline (grant, patent, filing)
    MILESTONE = "milestone"    # Project milestone
    RECURRING = "recurring"    # Repeating event (content publish, backup)
    DEPLOYMENT = "deployment"  # Deploy window
    MEETING = "meeting"        # Meeting / call
    REMINDER = "reminder"      # Soft reminder
    KEY_ROTATION = "key_rotation"  # API key rotation schedule


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CalendarEvent:
    """A single calendar event."""
    event_id: str
    title: str
    event_type: EventType
    priority: EventPriority
    due_date: str             # ISO 8601: "2026-05-17"
    due_time: str = "23:59"   # HH:MM
    description: str = ""
    tags: List[str] = field(default_factory=list)
    recurrence_days: int = 0  # 0 = no recurrence, 7 = weekly, 30 = monthly
    completed: bool = False
    created_at: float = field(default_factory=time.time)
    alert_days_before: List[int] = field(default_factory=lambda: [7, 3, 1, 0])

    @property
    def due_datetime(self) -> datetime:
        return datetime.fromisoformat(f"{self.due_date}T{self.due_time}")

    @property
    def days_remaining(self) -> int:
        delta = self.due_datetime - datetime.now()
        return max(0, delta.days)

    @property
    def is_overdue(self) -> bool:
        return datetime.now() > self.due_datetime and not self.completed

    @property
    def is_urgent(self) -> bool:
        return self.days_remaining <= 3 and not self.completed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "type": self.event_type.value,
            "priority": self.priority.value,
            "due_date": self.due_date,
            "due_time": self.due_time,
            "days_remaining": self.days_remaining,
            "is_overdue": self.is_overdue,
            "is_urgent": self.is_urgent,
            "completed": self.completed,
            "tags": self.tags,
        }


class Calendar:
    """SCBE operational calendar."""

    def __init__(self):
        self._events: Dict[str, CalendarEvent] = {}

    def add(
        self,
        title: str,
        due_date: str,
        event_type: EventType = EventType.REMINDER,
        priority: EventPriority = EventPriority.NORMAL,
        due_time: str = "23:59",
        description: str = "",
        tags: Optional[List[str]] = None,
        recurrence_days: int = 0,
        alert_days: Optional[List[int]] = None,
    ) -> CalendarEvent:
        """Add an event to the calendar."""
        event = CalendarEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            title=title,
            event_type=event_type,
            priority=priority,
            due_date=due_date,
            due_time=due_time,
            description=description,
            tags=tags or [],
            recurrence_days=recurrence_days,
            alert_days_before=alert_days or [7, 3, 1, 0],
        )
        self._events[event.event_id] = event
        return event

    def complete(self, event_id: str) -> bool:
        """Mark an event as completed."""
        event = self._events.get(event_id)
        if not event:
            return False
        event.completed = True

        # If recurring, spawn the next occurrence
        if event.recurrence_days > 0:
            next_due = event.due_datetime + timedelta(days=event.recurrence_days)
            self.add(
                title=event.title,
                due_date=next_due.strftime("%Y-%m-%d"),
                event_type=event.event_type,
                priority=event.priority,
                due_time=event.due_time,
                description=event.description,
                tags=event.tags,
                recurrence_days=event.recurrence_days,
            )
        return True

    def upcoming(self, days: int = 30) -> List[CalendarEvent]:
        """Get upcoming events within N days."""
        cutoff = datetime.now() + timedelta(days=days)
        events = [
            e for e in self._events.values()
            if not e.completed and e.due_datetime <= cutoff
        ]
        return sorted(events, key=lambda e: e.due_datetime)

    def overdue(self) -> List[CalendarEvent]:
        """Get all overdue events."""
        return [e for e in self._events.values() if e.is_overdue]

    def urgent(self) -> List[CalendarEvent]:
        """Get all urgent events (<=3 days)."""
        return [e for e in self._events.values() if e.is_urgent]

    def by_type(self, event_type: EventType) -> List[CalendarEvent]:
        """Get events by type."""
        return [e for e in self._events.values()
                if e.event_type == event_type and not e.completed]

    def by_tag(self, tag: str) -> List[CalendarEvent]:
        """Get events with a specific tag."""
        return [e for e in self._events.values()
                if tag in e.tags and not e.completed]

    def alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts (events within their alert windows)."""
        alerts = []
        for event in self._events.values():
            if event.completed:
                continue
            days = event.days_remaining
            for alert_day in event.alert_days_before:
                if days == alert_day:
                    alerts.append({
                        "event": event.to_dict(),
                        "alert_type": "due_today" if alert_day == 0
                                      else f"{alert_day}_days_warning",
                        "severity": "critical" if alert_day == 0
                                     else "high" if alert_day <= 1
                                     else "normal",
                    })
                    break
        return alerts

    def summary(self) -> Dict[str, Any]:
        """Calendar summary."""
        active = [e for e in self._events.values() if not e.completed]
        return {
            "total_events": len(self._events),
            "active": len(active),
            "overdue": len(self.overdue()),
            "urgent": len(self.urgent()),
            "upcoming_7d": len(self.upcoming(7)),
            "upcoming_30d": len(self.upcoming(30)),
        }

    def save(self, path: str) -> None:
        """Save calendar to JSON."""
        data = [e.to_dict() for e in self._events.values()]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_scbe_defaults(cls) -> "Calendar":
        """Create calendar pre-loaded with known SCBE deadlines."""
        cal = cls()

        # Grant deadlines
        cal.add("Schmidt Sciences LOI Submission", "2026-05-17",
                event_type=EventType.DEADLINE, priority=EventPriority.CRITICAL,
                tags=["grant", "schmidt"], alert_days=[30, 14, 7, 3, 1, 0])

        # Patent deadlines
        cal.add("USPTO #63/961,403 Missing Parts Filing ($82)", "2026-04-19",
                event_type=EventType.DEADLINE, priority=EventPriority.CRITICAL,
                tags=["patent", "uspto"], alert_days=[30, 14, 7, 3, 1, 0])

        cal.add("Non-Provisional Patent Deadline", "2027-01-11",
                event_type=EventType.DEADLINE, priority=EventPriority.HIGH,
                tags=["patent", "non-provisional"])

        cal.add("arXiv Submission Expiry", "2026-03-14",
                event_type=EventType.DEADLINE, priority=EventPriority.HIGH,
                tags=["arxiv", "paper"])

        # Recurring ops
        cal.add("Push training data to HuggingFace", "2026-03-01",
                event_type=EventType.RECURRING, priority=EventPriority.NORMAL,
                recurrence_days=7, tags=["training", "huggingface"])

        cal.add("Governance audit snapshot", "2026-03-01",
                event_type=EventType.RECURRING, priority=EventPriority.NORMAL,
                recurrence_days=14, tags=["audit", "governance"])

        cal.add("API key rotation check", "2026-03-01",
                event_type=EventType.KEY_ROTATION, priority=EventPriority.HIGH,
                recurrence_days=30, tags=["security", "keys"])

        cal.add("Content publish cycle", "2026-03-01",
                event_type=EventType.RECURRING, priority=EventPriority.NORMAL,
                recurrence_days=3, tags=["content", "marketing"])

        return cal


# ═══════════════════════════════════════════════════════════════
# TimeClock — Rate Limiting + Budget Tracking + Key Rotation
# ═══════════════════════════════════════════════════════════════

@dataclass
class ProviderBudget:
    """Budget and usage tracking for a single LLM provider."""
    provider: str
    daily_budget_usd: float = 5.0
    weekly_budget_usd: float = 25.0
    monthly_budget_usd: float = 100.0
    daily_spent: float = 0.0
    weekly_spent: float = 0.0
    monthly_spent: float = 0.0
    daily_calls: int = 0
    weekly_calls: int = 0
    monthly_calls: int = 0
    daily_limit_calls: int = 1000    # Rate limit
    last_reset_daily: float = field(default_factory=time.time)
    last_reset_weekly: float = field(default_factory=time.time)
    last_reset_monthly: float = field(default_factory=time.time)

    def can_spend(self, amount: float) -> bool:
        """Check if we're within budget."""
        self._auto_reset()
        return (
            self.daily_spent + amount <= self.daily_budget_usd
            and self.weekly_spent + amount <= self.weekly_budget_usd
            and self.monthly_spent + amount <= self.monthly_budget_usd
            and self.daily_calls < self.daily_limit_calls
        )

    def record_spend(self, amount: float) -> None:
        """Record a spend."""
        self._auto_reset()
        self.daily_spent += amount
        self.weekly_spent += amount
        self.monthly_spent += amount
        self.daily_calls += 1
        self.weekly_calls += 1
        self.monthly_calls += 1

    def _auto_reset(self) -> None:
        """Reset counters when periods roll over."""
        now = time.time()
        if now - self.last_reset_daily > 86400:
            self.daily_spent = 0.0
            self.daily_calls = 0
            self.last_reset_daily = now
        if now - self.last_reset_weekly > 604800:
            self.weekly_spent = 0.0
            self.weekly_calls = 0
            self.last_reset_weekly = now
        if now - self.last_reset_monthly > 2592000:
            self.monthly_spent = 0.0
            self.monthly_calls = 0
            self.last_reset_monthly = now

    def utilization(self) -> Dict[str, float]:
        """Return utilization percentages."""
        self._auto_reset()
        return {
            "daily_budget_pct": self.daily_spent / max(self.daily_budget_usd, 0.01) * 100,
            "weekly_budget_pct": self.weekly_spent / max(self.weekly_budget_usd, 0.01) * 100,
            "monthly_budget_pct": self.monthly_spent / max(self.monthly_budget_usd, 0.01) * 100,
            "daily_calls_pct": self.daily_calls / max(self.daily_limit_calls, 1) * 100,
        }


@dataclass
class KeySlot:
    """A single API key slot with rotation metadata."""
    provider: str
    env_var: str
    last_rotated: float = field(default_factory=time.time)
    rotation_interval_days: int = 30
    is_active: bool = True
    notes: str = ""

    @property
    def days_since_rotation(self) -> float:
        return (time.time() - self.last_rotated) / 86400

    @property
    def needs_rotation(self) -> bool:
        return self.days_since_rotation >= self.rotation_interval_days

    def rotate(self) -> None:
        """Mark as rotated (actual key change is manual)."""
        self.last_rotated = time.time()


class TimeClock:
    """Tracks API usage, budgets, rate limits, and key rotation."""

    def __init__(self):
        self._budgets: Dict[str, ProviderBudget] = {}
        self._keys: Dict[str, KeySlot] = {}
        self._session_start: float = time.time()

    def add_provider(
        self,
        provider: str,
        daily_budget: float = 5.0,
        weekly_budget: float = 25.0,
        monthly_budget: float = 100.0,
        daily_limit: int = 1000,
    ) -> None:
        """Register a provider for budget tracking."""
        self._budgets[provider] = ProviderBudget(
            provider=provider,
            daily_budget_usd=daily_budget,
            weekly_budget_usd=weekly_budget,
            monthly_budget_usd=monthly_budget,
            daily_limit_calls=daily_limit,
        )

    def add_key(
        self,
        provider: str,
        env_var: str,
        rotation_days: int = 30,
        notes: str = "",
    ) -> None:
        """Register an API key for rotation tracking."""
        self._keys[f"{provider}:{env_var}"] = KeySlot(
            provider=provider,
            env_var=env_var,
            rotation_interval_days=rotation_days,
            notes=notes,
        )

    def can_use(self, provider: str, estimated_cost: float = 0.001) -> bool:
        """Check if a provider is within budget and rate limits."""
        budget = self._budgets.get(provider)
        if not budget:
            return True  # No budget = no limits
        return budget.can_spend(estimated_cost)

    def record_use(self, provider: str, cost: float) -> None:
        """Record API usage."""
        budget = self._budgets.get(provider)
        if budget:
            budget.record_spend(cost)

    def keys_needing_rotation(self) -> List[KeySlot]:
        """Get all keys that need rotation."""
        return [k for k in self._keys.values() if k.needs_rotation]

    def rotate_key(self, provider: str, env_var: str) -> bool:
        """Mark a key as rotated."""
        key = self._keys.get(f"{provider}:{env_var}")
        if key:
            key.rotate()
            return True
        return False

    def session_duration(self) -> float:
        """How long this session has been running (seconds)."""
        return time.time() - self._session_start

    def status(self) -> Dict[str, Any]:
        """Full timeclock status."""
        return {
            "session_duration_minutes": round(self.session_duration() / 60, 1),
            "budgets": {
                name: {
                    "daily": f"${b.daily_spent:.3f} / ${b.daily_budget_usd:.2f}",
                    "weekly": f"${b.weekly_spent:.3f} / ${b.weekly_budget_usd:.2f}",
                    "monthly": f"${b.monthly_spent:.3f} / ${b.monthly_budget_usd:.2f}",
                    "calls_today": b.daily_calls,
                    **b.utilization(),
                }
                for name, b in self._budgets.items()
            },
            "keys": {
                kid: {
                    "provider": k.provider,
                    "env_var": k.env_var,
                    "days_since_rotation": round(k.days_since_rotation, 1),
                    "needs_rotation": k.needs_rotation,
                    "active": k.is_active,
                }
                for kid, k in self._keys.items()
            },
            "keys_needing_rotation": len(self.keys_needing_rotation()),
        }

    @classmethod
    def load_scbe_defaults(cls) -> "TimeClock":
        """Create a timeclock pre-configured for SCBE providers."""
        tc = cls()

        # Provider budgets
        tc.add_provider("openai", daily_budget=2.0, weekly_budget=10.0, monthly_budget=40.0)
        tc.add_provider("xai", daily_budget=2.0, weekly_budget=10.0, monthly_budget=40.0)
        tc.add_provider("claude", daily_budget=3.0, weekly_budget=15.0, monthly_budget=60.0)
        tc.add_provider("gemini", daily_budget=1.0, weekly_budget=5.0, monthly_budget=20.0)
        tc.add_provider("huggingface", daily_budget=0.5, weekly_budget=2.0, monthly_budget=5.0)
        tc.add_provider("ollama", daily_budget=0.0, weekly_budget=0.0, monthly_budget=0.0, daily_limit=10000)
        tc.add_provider("perplexity", daily_budget=1.0, weekly_budget=5.0, monthly_budget=20.0)

        # Key rotation schedules
        tc.add_key("openai", "OPENAI_API_KEY", rotation_days=90, notes="platform.openai.com/api-keys")
        tc.add_key("xai", "XAI_API_KEY", rotation_days=90, notes="console.x.ai")
        tc.add_key("claude", "ANTHROPIC_API_KEY", rotation_days=90)
        tc.add_key("gemini", "GOOGLE_AI_API_KEY", rotation_days=90)
        tc.add_key("github", "GITHUB_TOKEN", rotation_days=90, notes="Fine-grained PAT")
        tc.add_key("huggingface", "HF_TOKEN", rotation_days=180)
        tc.add_key("telegram", "TELEGRAM_BOT_TOKEN", rotation_days=365)
        tc.add_key("asana", "ASANA_PAT", rotation_days=90)
        tc.add_key("perplexity", "PERPLEXITY_API_KEY", rotation_days=90)
        tc.add_key("twitter", "X_BEARER_TOKEN", rotation_days=90)
        tc.add_key("uspto", "USPTO_API_KEY", rotation_days=365)

        return tc
