from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.tokenizer.watch_prime_token_open_source_readiness import measure_readiness


def _write_collector(path: Path) -> str:
    path.write_text(
        """
import hashlib
import re
INTERNAL_MARKERS = ("<internal>",)
MAX_TRAINING_CHARS = 1000
SYSTEM_REMINDER = re.compile(r"<reminder>.*?</reminder>", re.DOTALL)
def extract_user_text(record):
    if record.get("role") != "user":
        return None
    return record["text"], record["timestamp"]
def normalized_hash(text):
    return hashlib.sha256(" ".join(text.casefold().split()).encode()).hexdigest()
def _source_session(path):
    return hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]
def source_is_closed(path):
    return "closed" in path.name
""".lstrip(),
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "scbe.prime-token-catalog.v1",
                "generated_at_utc": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )


def _write_rollout(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_counts_open_sources_without_emitting_text(tmp_path: Path) -> None:
    collector = tmp_path / "collector.py"
    collector_hash = _write_collector(collector)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    sessions = tmp_path / "sessions"
    _write_rollout(
        sessions / "rollout-open.jsonl",
        [
            {"role": "user", "timestamp": "2026-01-02T00:00:00+00:00", "text": "private candidate alpha"},
            {"role": "user", "timestamp": "2026-01-02T00:01:00+00:00", "text": "private candidate beta"},
            {"role": "assistant", "timestamp": "2026-01-02T00:02:00+00:00", "text": "ignored"},
        ],
    )

    result = measure_readiness(
        sessions_root=sessions,
        catalog_manifest=manifest,
        collector_path=collector,
        collector_sha256=collector_hash,
        minimum_candidates=3,
        minimum_closed_sessions=2,
    )

    assert result["status"] == "WAITING_FOR_MORE_AUTHORED_TURNS_AND_DISTINCT_SESSIONS"
    assert result["observed"]["eligible_unique_turns"] == 2
    assert result["observed"]["open_source_sessions"] == 1
    assert result["deficits"]["eligible_candidates"] == 1
    assert result["deficits"]["additional_distinct_sessions_even_if_current_sources_close"] == 1
    serialized = json.dumps(result)
    assert "private candidate" not in serialized
    assert "rollout-open.jsonl" not in serialized


def test_reports_ready_only_after_candidate_and_closed_session_minimums(tmp_path: Path) -> None:
    collector = tmp_path / "collector.py"
    collector_hash = _write_collector(collector)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    sessions = tmp_path / "sessions"
    for index in range(2):
        _write_rollout(
            sessions / f"rollout-closed-{index}.jsonl",
            [
                {
                    "role": "user",
                    "timestamp": "2026-01-02T00:00:00+00:00",
                    "text": f"distinct candidate {index}",
                }
            ],
        )

    result = measure_readiness(
        sessions_root=sessions,
        catalog_manifest=manifest,
        collector_path=collector,
        collector_sha256=collector_hash,
        minimum_candidates=2,
        minimum_closed_sessions=2,
    )

    assert result["status"] == "READY_FOR_PINNED_COLLECTOR"
    assert result["observed"]["closed_source_sessions"] == 2
    assert result["observed"]["eligible_unique_turns"] == 2
    assert result["deficits"] == {
        "eligible_candidates": 0,
        "closed_source_sessions": 0,
        "additional_distinct_sessions_even_if_current_sources_close": 0,
    }


def test_rejects_unpinned_collector(tmp_path: Path) -> None:
    collector = tmp_path / "collector.py"
    _write_collector(collector)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    sessions = tmp_path / "sessions"
    sessions.mkdir()

    with pytest.raises(RuntimeError, match="collector hash mismatch"):
        measure_readiness(
            sessions_root=sessions,
            catalog_manifest=manifest,
            collector_path=collector,
            collector_sha256="0" * 64,
            minimum_candidates=30,
            minimum_closed_sessions=3,
        )
