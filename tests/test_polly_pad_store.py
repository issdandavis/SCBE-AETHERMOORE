from __future__ import annotations

from pathlib import Path

from hydra.polly_pad import PollyPadStore


def _store(tmp_path: Path) -> PollyPadStore:
    db_path = tmp_path / "pads.db"
    return PollyPadStore(str(db_path))


def test_decommission_and_cousin_inherits_compact(tmp_path: Path) -> None:
    store = _store(tmp_path)
    pad_id = store.ensure_pad("pad-planner", metadata={"role": "planner"})

    compact = {
        "task_id": "task-1",
        "state": "partial",
        "notes": "resume from checkpoint",
    }
    store.write_compact(pad_id, compact)
    store.decommission(pad_id, reason="task_failed", exit_log={"error": "timeout"})

    cousin_id = store.spawn_cousin(pad_id, reason="takeover")
    cousin = store.get_pad(cousin_id)
    assert cousin is not None
    assert cousin["status"] == "active"
    assert cousin["parent_pad_id"] == pad_id
    assert cousin["metadata"]["inherited_from"] == pad_id
    assert cousin["metadata"]["inherited_compact"] == compact


def test_recovery_ledger_prevents_duplicate_tracking(tmp_path: Path) -> None:
    store = _store(tmp_path)
    failed_task_id = "failed-task-42"
    assert store.has_recovery(failed_task_id) is False

    store.record_recovery(
        failed_task_id=failed_task_id,
        source_pad_id="pad-a",
        cousin_pad_id="pad-b",
        takeover_task_id="task-takeover-1",
    )
    assert store.has_recovery(failed_task_id) is True

    # Re-record should keep recovery present and not throw.
    store.record_recovery(
        failed_task_id=failed_task_id,
        source_pad_id="pad-a",
        cousin_pad_id="pad-c",
        takeover_task_id="task-takeover-2",
    )
    assert store.has_recovery(failed_task_id) is True


def test_events_are_recorded_for_audit(tmp_path: Path) -> None:
    store = _store(tmp_path)
    pad_id = store.ensure_pad("pad-memory", metadata={"role": "memory"})
    store.log_event(pad_id, "book_opened", {"doc_id": "doc-1"})
    store.log_event(pad_id, "web_lookup", {"url": "https://example.com"})

    events = store.list_events(pad_id, limit=10)
    assert len(events) == 2
    assert {events[0]["event_type"], events[1]["event_type"]} == {"book_opened", "web_lookup"}
