from __future__ import annotations

import json
from pathlib import Path

import pytest

from python.scbe.prime_token_query_harvest import (
    REVIEW_LABEL_SCHEMA,
    build_reviewed_benchmark,
    harvest_review_queue,
    review_queue_sha256,
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
                "Issac: My 5W system uses who what when where why.\n\n"
                "Issac: Retained source order: 4 assistant: research a book\n\n"
                "Issac: [42] tool exec call: publish the manuscript\n\n"
                'Issac: {"command": ["research", "book"], "environment_id": "local"}'
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


def test_harvest_accepts_scrubbed_direct_speech_with_source_provenance(
    tmp_path: Path,
) -> None:
    path = tmp_path / "direct-speech.jsonl"
    rows = [
        {
            "schema": "clay.direct-speech-turn.v1",
            "source_session": "source-hash-a",
            "turn": 7,
            "text": "Please research how the prime sieve should route this source.",
        },
        {
            "schema": "clay.direct-speech-turn.v1",
            "source_session": "source-hash-b",
            "turn": 3,
            "text": "This authentic request is unrelated to every selected topic.",
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    queue = harvest_review_queue(path)

    assert queue["candidate_count"] == 1
    assert queue["session_ids"] == ["source-hash-a", "source-hash-b"]
    assert queue["selection_policy"]["accepted_input_schemas"] == ["clay.direct-speech-turn.v1"]
    candidate = queue["candidates"][0]
    assert candidate["session_id"] == "source-hash-a"
    assert candidate["chunk_index"] == 7
    assert candidate["source_schema"] == "clay.direct-speech-turn.v1"
    assert candidate["topic_groups"] == ["prime_sieve", "source_research"]


def test_review_labels_are_hash_bound_and_minimum_enforced(tmp_path: Path) -> None:
    queue = harvest_review_queue(_dataset(tmp_path / "chunks.jsonl"))
    labels = {
        "schema": REVIEW_LABEL_SCHEMA,
        "queue_sha256": queue["queue_sha256"],
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
    with pytest.raises(ValueError, match="exact review queue"):
        build_reviewed_benchmark(queue, labels, minimum_queries=1)


def test_review_queue_hash_binds_policy_and_candidates(tmp_path: Path) -> None:
    queue = harvest_review_queue(_dataset(tmp_path / "chunks.jsonl"))
    original = queue["queue_sha256"]
    assert original == review_queue_sha256(queue)

    queue["selection_policy"]["max_chars"] = 999

    assert review_queue_sha256(queue) != original
    labels = {
        "schema": REVIEW_LABEL_SCHEMA,
        "queue_sha256": original,
        "reviewer": "test-reviewer",
        "reviewed_at_utc": "2026-11-07T00:00:00Z",
        "labels": [],
    }
    with pytest.raises(ValueError, match="queue content hash"):
        build_reviewed_benchmark(queue, labels, minimum_queries=1)
