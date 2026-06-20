"""Tests for agent bus event schema versioning + reader gating.

Covers agents/agent_bus_schema.py (validate_event / validate_log / parse_version)
and the training reader's schema gate (agent_bus_training.TrainingTrigger), which
must skip events the validator rejects so an incompatible payload can't skew the
perf window that drives autonomous training.
"""

from __future__ import annotations

import json

import pytest

from agents.agent_bus_schema import (
    CURRENT_SCHEMA_VERSION,
    MIGRATIONS,
    parse_version,
    validate_event,
    validate_log,
)


def _v1_event(**overrides):
    """A minimal, valid current-version event."""
    event = {
        "task_type": "ask",
        "query": "hello",
        "timestamp": "2026-06-10T00:00:00Z",
        "success": True,
        "_schema_version": CURRENT_SCHEMA_VERSION,
    }
    event.update(overrides)
    return event


# ── parse_version ───────────────────────────────────────────────────────────


def test_parse_version_splits_semver():
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version(" 10.0.4 ") == (10, 0, 4)


def test_parse_version_rejects_garbage():
    with pytest.raises(ValueError):
        parse_version("1.0")
    with pytest.raises(ValueError):
        parse_version("not.a.version")


# ── validate_event ───────────────────────────────────────────────────────────


def test_valid_current_event_accepted():
    result = validate_event(_v1_event())
    assert result.ok is True
    assert result.version == CURRENT_SCHEMA_VERSION
    assert result.migrated is False


def test_missing_version_treated_as_current():
    event = _v1_event()
    del event["_schema_version"]
    result = validate_event(event)
    assert result.ok is True
    assert result.version == CURRENT_SCHEMA_VERSION


def test_future_major_version_rejected():
    result = validate_event(_v1_event(_schema_version="2.0.0"))
    assert result.ok is False
    assert "future major version" in (result.reason or "")


def test_older_major_without_migration_rejected():
    result = validate_event(_v1_event(_schema_version="0.9.0"))
    assert result.ok is False
    assert "no migration registered" in (result.reason or "")


def test_older_major_with_registered_migration_accepted(monkeypatch):
    calls = {}

    def _migrate(record):
        calls["ran"] = True
        return record

    monkeypatch.setitem(MIGRATIONS, "0.9.0", _migrate)
    result = validate_event(_v1_event(_schema_version="0.9.0"))
    assert result.ok is True
    assert result.migrated is True
    assert calls.get("ran") is True


def test_newer_minor_accepted_with_warning():
    result = validate_event(_v1_event(_schema_version="1.99.0"))
    assert result.ok is True
    assert "newer minor version" in (result.reason or "")


def test_unparseable_version_rejected():
    result = validate_event(_v1_event(_schema_version="banana"))
    assert result.ok is False
    assert "unparseable version" in (result.reason or "")


def test_missing_required_v1_field_rejected():
    event = _v1_event()
    del event["success"]
    result = validate_event(event)
    assert result.ok is False
    assert "missing required v1 fields" in (result.reason or "")
    assert "success" in (result.reason or "")


# ── validate_log ──────────────────────────────────────────────────────────────


def test_validate_log_counts_accept_reject_warn(tmp_path):
    log = tmp_path / "events.jsonl"
    lines = [
        json.dumps(_v1_event()),  # accepted
        json.dumps(_v1_event(_schema_version="1.99.0")),  # accepted + warning
        json.dumps(_v1_event(_schema_version="2.0.0")),  # rejected (future major)
        "{not valid json",  # rejected (bad JSON)
        "",  # blank, skipped
    ]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = validate_log(log)
    assert report.accepted == 2
    assert report.rejected == 2
    assert report.warnings == 1
    assert len(report.rejections) == 2
    assert report.version_counts.get(CURRENT_SCHEMA_VERSION) == 1


def test_validate_log_missing_file_is_empty_report(tmp_path):
    report = validate_log(tmp_path / "does_not_exist.jsonl")
    assert report.total == 0
    assert report.accepted == 0
    assert report.rejected == 0


# ── training reader gate (the fix) ───────────────────────────────────────────


def test_training_reader_skips_incompatible_events(tmp_path):
    from agents.agent_bus_training import TrainingTrigger

    log = tmp_path / "events.jsonl"
    lines = [
        json.dumps(_v1_event(success=True)),
        json.dumps(_v1_event(success=False)),
        json.dumps(_v1_event(success=True)),
        # future major version — must NOT be counted in the perf window
        json.dumps(_v1_event(_schema_version="2.0.0", success=False)),
    ]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    perf = TrainingTrigger(events_log=log).measure()
    assert perf is not None
    assert perf.total == 3  # the 2.0.0 event was gated out
    assert perf.successes == 2
    assert perf.failures == 1
