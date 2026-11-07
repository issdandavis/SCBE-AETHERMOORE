from __future__ import annotations

import json
from pathlib import Path

import pytest

from python.scbe.prime_token_query_harvest import (
    EXPLICIT_ROUTE_SCOPE_REVISION,
    REVIEW_LABEL_SCHEMA,
    build_explicit_route_review_scope,
    build_reviewed_benchmark,
    harvest_review_queue,
    query_hashes_from_benchmark,
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


def _explicit_route_dataset(path: Path) -> Path:
    rows = []
    texts = [
        *(f"Use five w who what when where why for request {index}." for index in range(4)),
        *(f"Publish manuscript package request {index} for readers." for index in range(22)),
        *(f"Trace the tongue braid request {index} through layers." for index in range(22)),
        *(f"Research source metadata request {index} with evidence." for index in range(22)),
        "A prime sieve request is outside this balanced scope.",
        "Research and publish overlap and must not enter an exclusive stratum.",
    ]
    for index, text in enumerate(texts):
        session_index = 0 if index == 3 else index
        rows.append(
            {
                "schema": "clay.direct-speech-turn.v1",
                "source_session": f"scope-session-{session_index}",
                "turn": index,
                "text": text,
            }
        )
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_explicit_route_scope_is_balanced_exclusive_and_hash_bound(tmp_path):
    queue = harvest_review_queue(_explicit_route_dataset(tmp_path / "voice.jsonl"))
    excluded = {next(row["query_sha256"] for row in queue["candidates"] if row["topic_groups"] == ["publication"])}
    scope = build_explicit_route_review_scope(
        queue,
        excluded_query_sha256=excluded,
    )

    assert scope["candidate_count"] == 63
    assert scope["selection_policy"]["scope_revision"] == EXPLICIT_ROUTE_SCOPE_REVISION
    assert scope["queue_sha256"] == review_queue_sha256(scope)
    assert not excluded & {row["query_sha256"] for row in scope["candidates"]}
    counts = {
        stratum: sum(row["review_stratum"] == stratum for row in scope["candidates"])
        for stratum in ("five_w", "publication", "tongue_braid", "source_research")
    }
    assert counts == {
        "five_w": 3,
        "publication": 20,
        "tongue_braid": 20,
        "source_research": 20,
    }
    assert len(scope["session_ids"]) == 63


def test_explicit_route_scope_requires_complete_review_and_preserves_stratum(tmp_path):
    queue = harvest_review_queue(_explicit_route_dataset(tmp_path / "voice.jsonl"))
    scope = build_explicit_route_review_scope(queue)
    labels = {
        "schema": REVIEW_LABEL_SCHEMA,
        "queue_sha256": scope["queue_sha256"],
        "reviewer": "test-reviewer",
        "reviewed_at_utc": "2026-11-07T00:00:00Z",
        "labels": [
            {
                "query_sha256": row["query_sha256"],
                "decision": "accept",
                "relevant_source_suffix": "fixture.md",
            }
            for row in scope["candidates"]
        ],
    }
    benchmark = build_reviewed_benchmark(scope, labels)
    assert benchmark["review_scope_sha256"] == scope["queue_sha256"]
    assert benchmark["review_scope_revision"] == EXPLICIT_ROUTE_SCOPE_REVISION
    assert {row["review"]["review_stratum"] for row in benchmark["queries"]} == {
        "five_w",
        "publication",
        "tongue_braid",
        "source_research",
    }

    labels["labels"].pop()
    with pytest.raises(ValueError, match="decision for every candidate"):
        build_reviewed_benchmark(scope, labels)


def test_query_hashes_from_benchmark_are_exact():
    benchmark = {
        "schema": "scbe.prime-token-benchmark.v1",
        "queries": [{"query": "Exact private query."}],
    }
    assert query_hashes_from_benchmark(benchmark) == {
        "f49966146f4059fdbefa022cc8936f3d4b8b937e3038f2241479d1f70a53dd04"
    }
