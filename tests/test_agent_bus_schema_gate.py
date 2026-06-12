"""Regression tests for agent-bus schema-version gating.

These lock the Tier-1 guarantee from agents/AGENT_BUS_NOTES.md: every event
carries a ``_schema_version``, and BOTH the validator and the read/replay path
reject events from unknown *future* major versions instead of silently trusting
them. Until this file landed the behavior existed but was unverified.

Implementation under test:
  - agents/agent_bus_schema.py   (validate_event / validate_log)
  - agents/agent_bus_replay.py   (replay_log — the live read path)
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.agent_bus_schema import CURRENT_SCHEMA_VERSION, validate_event
from agents.agent_bus_replay import replay_log


def _evt(**over: object) -> dict[str, object]:
    """A minimal valid v1 event; override fields per-test."""
    rec: dict[str, object] = {
        "task_type": "ask",
        "query": "hello",
        "timestamp": "2026-06-10T00:00:00Z",
        "success": True,
        "_schema_version": CURRENT_SCHEMA_VERSION,
    }
    rec.update(over)
    return rec


def test_validate_event_accepts_current_version() -> None:
    assert validate_event(_evt()).ok is True


def test_validate_event_rejects_future_major() -> None:
    res = validate_event(_evt(_schema_version="2.0.0"))
    assert res.ok is False
    assert "future major" in (res.reason or "")


def test_validate_event_accepts_newer_minor_with_warning() -> None:
    res = validate_event(_evt(_schema_version="1.9.0"))
    assert res.ok is True
    assert res.reason  # newer-minor warning surfaced, but accepted


def test_validate_event_rejects_missing_required_fields() -> None:
    bad = _evt()
    del bad["query"]
    res = validate_event(bad)
    assert res.ok is False
    assert "missing required" in (res.reason or "")


def test_validate_event_rejects_unparseable_version() -> None:
    res = validate_event(_evt(_schema_version="not.a.version"))
    assert res.ok is False


def test_validate_event_missing_version_treated_as_current() -> None:
    bad = _evt()
    del bad["_schema_version"]
    assert validate_event(bad).ok is True


def test_replay_log_skips_future_major_events(tmp_path: Path) -> None:
    """End-to-end: the read path must drop a future-major event, not crash or trust it."""
    log = tmp_path / "events.jsonl"
    log.write_text(
        "\n".join(
            [
                json.dumps(_evt(query="good")),
                json.dumps(_evt(query="from the future", _schema_version="2.0.0")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = replay_log(log)
    assert report["total_events"] == 1
    assert report["skipped_invalid"] == 1
