from __future__ import annotations

import json
from pathlib import Path

import pytest

from python.scbe.prime_token_query_harvest import (
    REVIEW_LABEL_SCHEMA,
    build_reviewed_benchmark,
    harvest_review_queue,
)


def _dataset(path: Path) -> Path:
    rows = [
        {
            "session_id": "2026-09-05-test",
            "chunk_index": 0,
            "text": (
                "Assistant: context\n\n"
                "Issac: Can the prime sieve route this request?\n\n"
                "Assistant: answer\n\n"
                "Issac: Can the prime sieve route this request?\n\n"
                "Issac: My 5W system uses who what when where why."
            ),
        },
        {
            "session_id": "2026-09-05-test",
            "chunk_index": 1,
            "text": "Issac: # AGENTS.md instructions for a prime worker",
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def test_harvest_is_deterministic_deduplicated_and_rejects_context(
    tmp_path: Path,
) -> None:
    queue = harvest_review_queue(_dataset(tmp_path / "chunks.jsonl"))
    assert queue["candidate_count"] == 2
    assert [row["turn_ordinal"] for row in queue["candidates"]] == [0, 2]
    assert queue["candidates"][0]["topic_groups"] == ["prime_sieve"]
    assert queue["candidates"][1]["topic_groups"] == ["five_w"]


def test_review_labels_are_hash_bound_and_minimum_enforced(tmp_path: Path) -> None:
    queue = harvest_review_queue(_dataset(tmp_path / "chunks.jsonl"))
    labels = {
        "schema": REVIEW_LABEL_SCHEMA,
        "queue_sha256": queue["dataset_sha256"],
        "reviewer": "test-reviewer",
        "reviewed_at_utc": "2026-11-07T00:00:00Z",
        "labels": [
            {
                "query_sha256": queue["candidates"][0]["query_sha256"],
                "decision": "accept",
                "relevant_source_suffix": "dev/loom/clay_sieve.py",
            },
            {
                "query_sha256": queue["candidates"][1]["query_sha256"],
                "decision": "reject",
            },
        ],
    }
    benchmark = build_reviewed_benchmark(queue, labels, minimum_queries=1)
    assert benchmark["query_provenance"] == "independent_external"
    assert len(benchmark["queries"]) == 1
    assert benchmark["queries"][0]["query_source_uri"].startswith("private-session://")
    with pytest.raises(ValueError, match="at least 2"):
        build_reviewed_benchmark(queue, labels, minimum_queries=2)


def test_review_rejects_wrong_dataset_hash(tmp_path: Path) -> None:
    queue = harvest_review_queue(_dataset(tmp_path / "chunks.jsonl"))
    labels = {
        "schema": REVIEW_LABEL_SCHEMA,
        "queue_sha256": "0" * 64,
        "reviewer": "test-reviewer",
        "reviewed_at_utc": "2026-11-07T00:00:00Z",
        "labels": [],
    }
    with pytest.raises(ValueError, match="dataset hash"):
        build_reviewed_benchmark(queue, labels, minimum_queries=1)
