from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from python.scbe.prime_token_independent_replay import reconstruct_material_replay_cases
from python.scbe.prime_token_material_cases import (
    BENCHMARK_SCHEMA,
    CLOSED_SOURCE_SNAPSHOT_SCHEMA,
    FIXED_FUNCTION_CLASSES,
    SOURCE_FAMILY_AUDIT_SCHEMA,
    build_material_case_bundle,
    build_query_input,
    frozen_output_vocabulary,
    plan_material_cases,
    query_session_id,
)
from python.scbe.prime_token_query_harvest import (
    REVIEW_QUEUE_SCHEMA,
    review_queue_sha256,
)

FAMILIES = ("family-a", "family-b", "family-c")
SOURCES = {
    "family-a": (r"C:\sources\a-one.md", r"C:\sources\a-two.md"),
    "family-b": (r"C:\sources\b-one.py",),
    "family-c": (r"C:\sources\c-one.md",),
}


def _audit() -> dict:
    canonical = []
    for family, paths in SOURCES.items():
        for index, path in enumerate(paths):
            canonical.append(
                {
                    "path": path,
                    "family_id": family,
                    "content_sha256": f"{FAMILIES.index(family) + 1:02x}{index:02x}".ljust(64, "0"),
                }
            )
    return {
        "schema": SOURCE_FAMILY_AUDIT_SCHEMA,
        "status": "VERIFIED_SOURCE_FAMILY_BOUNDARY_WAITING",
        "error_count": 0,
        "families": [{"family_id": family} for family in FAMILIES],
        "canonical_sources": canonical,
    }


def _query(index: int, family: str, path: str, *, session: str | None = None) -> dict:
    stratum = FIXED_FUNCTION_CLASSES[index % len(FIXED_FUNCTION_CLASSES)]
    return {
        "id": f"query-{family}-{index}",
        "query": f"Explain route {index} for {family} with enough distinct words.",
        "query_source_uri": f"private-session://{session or f'session-{family}-{index}'}/0/{index}",
        "relevant_source_suffix": path.replace("\\", "/").removeprefix("C:/"),
        "review": {"topic_groups": [stratum]},
    }


def _benchmark(*, large: bool = True) -> dict:
    queries = []
    counts = {"family-a": 30, "family-b": 10, "family-c": 10} if large else {family: 3 for family in FAMILIES}
    for family, count in counts.items():
        paths = SOURCES[family]
        for index in range(count):
            queries.append(_query(index, family, paths[index % len(paths)]))
    return {
        "schema": BENCHMARK_SCHEMA,
        "private_runtime_only": True,
        "queries": queries,
    }


def _closed_sessions(benchmark: dict) -> list[str]:
    return [query_session_id(row["query_source_uri"]) for row in benchmark["queries"]]


def _queue(benchmark: dict) -> dict:
    candidates = []
    for ordinal, row in enumerate(benchmark["queries"]):
        candidates.append(
            {
                "candidate_id": row["id"],
                "query_sha256": sha256(row["query"].encode("utf-8")).hexdigest(),
                "session_id": query_session_id(row["query_source_uri"]),
                "chunk_index": 0,
                "turn_ordinal": ordinal,
                "topic_groups": row["review"]["topic_groups"],
                "query": row["query"],
            }
        )
    queue = {
        "schema": REVIEW_QUEUE_SCHEMA,
        "dataset": "fixture://closed-sessions",
        "dataset_sha256": "f" * 64,
        "session_ids": _closed_sessions(benchmark),
        "selection_policy": {"fixture": True},
        "candidate_count": len(candidates),
        "candidates": candidates,
        "prospective_boundary": {
            "catalog_generated_at_utc": "2026-11-11T00:00:00+00:00",
            "catalog_sha256": "a" * 64,
            "manifest_sha256": "b" * 64,
        },
    }
    queue["queue_sha256"] = review_queue_sha256(queue)
    return queue


def _snapshot(tmp_path: Path, benchmark: dict) -> Path:
    sessions_root = tmp_path / "sessions"
    sessions_root.mkdir()
    sources = []
    for session in sorted(set(_closed_sessions(benchmark))):
        path = sessions_root / f"rollout-{session}.jsonl"
        path.write_text(f'{{"session":"{session}"}}\n', encoding="utf-8")
        stat = path.stat()
        sources.append(
            {
                "path": str(path.resolve()),
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "source_session": session,
            }
        )
    snapshot = {
        "schema": CLOSED_SOURCE_SNAPSHOT_SCHEMA,
        "created_at_utc": "2026-11-11T00:01:00+00:00",
        "sessions_root": str(sessions_root.resolve()),
        "catalog_generated_at_utc": "2026-11-11T00:00:00+00:00",
        "sources": sources,
    }
    path = tmp_path / "CLOSED_SOURCE_SNAPSHOT.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    return path


def test_query_input_is_target_invariant_and_source_view_is_query_only() -> None:
    first = build_query_input(
        "Route this request through the bounded field.",
        "private-session://session-one/0/1",
    )
    second = build_query_input(
        "Route this request through the bounded field.",
        "private-session://session-one/0/1",
    )
    assert first == second
    record = first["records"][0]
    assert record["views"]["source"] == {
        "source_kind": "private-session",
        "session_sha256": first["query_session_sha256"],
        "query_sha256": first["query_sha256"],
        "query_source_uri_sha256": record["views"]["source"]["query_source_uri_sha256"],
    }
    rendered = repr(record)
    assert "family-a" not in rendered
    assert "five_w" in record["views"]
    assert len(first["token_ids"]) <= 512
    assert first["owner_positions"] == [0]
    assert first["output_positions"] == [len(first["token_ids"]) - 1]


def test_default_plan_enforces_real_concentration_and_final_test_floor() -> None:
    benchmark = _benchmark()
    plan = plan_material_cases(
        benchmark,
        _audit(),
        closed_query_sessions=_closed_sessions(benchmark),
    )
    assert plan["status"] == "PLANNED_NO_WRITE_NO_TRAINING_AUTHORITY"
    assert plan["query_count"] == 50
    assert plan["concentration"]["largest_source_fraction"] == pytest.approx(0.30)
    assert plan["concentration"]["largest_family_fraction"] == pytest.approx(0.60)
    assert plan["split_manifest"]["lane_counts"]["final_test"] == 30
    assert all(plan[key] is False for key in ("training_authorized", "promotion_authorized", "tool_dispatch"))
    lane_families = plan["split_manifest"]["lane_source_families"]
    lane_sessions = plan["split_manifest"]["lane_query_source_families"]
    for left_index, left in enumerate(("train", "validation", "final_test")):
        for right in ("train", "validation", "final_test")[left_index + 1 :]:
            assert not set(lane_families[left]) & set(lane_families[right])
            assert not set(lane_sessions[left]) & set(lane_sessions[right])


def test_target_change_does_not_change_packet_input_identity() -> None:
    benchmark = _benchmark()
    first = plan_material_cases(
        benchmark,
        _audit(),
        closed_query_sessions=_closed_sessions(benchmark),
    )
    changed = deepcopy(benchmark)
    changed["queries"][0]["relevant_source_suffix"] = "sources/a-two.md"
    second = plan_material_cases(
        changed,
        _audit(),
        closed_query_sessions=_closed_sessions(changed),
    )
    first_row = next(row for rows in first["lanes"].values() for row in rows if row["record_id"] == "query-family-a-0")
    second_row = next(
        row for rows in second["lanes"].values() for row in rows if row["record_id"] == "query-family-a-0"
    )
    assert first_row["target_source_path"] != second_row["target_source_path"]
    assert first_row["packet_input_sha256"] == second_row["packet_input_sha256"]
    assert first_row["records"] == second_row["records"]


def test_cross_family_query_session_bridge_fails_closed() -> None:
    benchmark = _benchmark(large=False)
    benchmark["queries"][3]["query_source_uri"] = benchmark["queries"][0]["query_source_uri"]
    with pytest.raises(ValueError, match="fewer than three components"):
        plan_material_cases(
            benchmark,
            _audit(),
            closed_query_sessions=_closed_sessions(benchmark),
            minimum_final_test=3,
            maximum_source_fraction=1.0,
            maximum_family_fraction=1.0,
        )


def test_output_vocabulary_is_a_prelabel_cartesian_product() -> None:
    vocabulary = frozen_output_vocabulary(_audit())
    assert len(vocabulary["rows"]) == len(FAMILIES) * len(FIXED_FUNCTION_CLASSES)
    assert [row["token_id"] for row in vocabulary["rows"]] == list(range(224, 236))
    assert {(row["relationship_class"], row["function_class"]) for row in vocabulary["rows"]} == {
        (family, function) for family in FAMILIES for function in FIXED_FUNCTION_CLASSES
    }


def test_bundle_writer_is_immutable_and_binds_all_runtime_files(
    tmp_path: Path,
) -> None:
    benchmark = _benchmark(large=False)
    benchmark_path = tmp_path / "BENCHMARK.json"
    audit_path = tmp_path / "SOURCE_FAMILY_AUDIT.json"
    queue_path = tmp_path / "SOURCE_QUEUE.json"
    snapshot_path = _snapshot(tmp_path, benchmark)
    ordinary_path = tmp_path / "ordinary-source.jsonl"
    retention_path = tmp_path / "retention-source.jsonl"
    benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
    audit_path.write_text(json.dumps(_audit()), encoding="utf-8")
    queue_path.write_text(json.dumps(_queue(benchmark)), encoding="utf-8")
    ordinary_path.write_text(
        json.dumps(
            {
                "id": "ordinary-1",
                "text": "ordinary packet-free prompt",
                "source_family": "ordinary-family",
                "source_locator": "fixture://ordinary/1",
                "content_sha256": "1" * 64,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    retention_path.write_text(
        json.dumps(
            {
                "id": "retention-1",
                "text": "retention packet-free prompt",
                "source_family": "retention-family",
                "source_locator": "fixture://retention/1",
                "content_sha256": "2" * 64,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "bundle"
    receipt = build_material_case_bundle(
        benchmark_path=benchmark_path,
        source_family_audit_path=audit_path,
        source_queue_path=queue_path,
        closed_source_snapshot_path=snapshot_path,
        ordinary_source_path=ordinary_path,
        retention_source_path=retention_path,
        output_dir=output,
        minimum_final_test=3,
        maximum_source_fraction=1.0,
        maximum_family_fraction=1.0,
    )
    assert receipt["status"] == "BUILT_NO_TRAINING_AUTHORITY"
    assert receipt["lane_counts"] == {
        "train": 3,
        "validation": 3,
        "final_test": 3,
        "ordinary": 1,
        "retention": 1,
    }
    cases = json.loads((output / "CASES_MANIFEST.json").read_text(encoding="utf-8"))
    assert cases["source_disjoint"] is True
    assert cases["query_session_disjoint"] is True
    assert set(cases["files"]) == {
        "train",
        "validation",
        "final_test",
        "ordinary",
        "retention",
    }
    reconstruction = reconstruct_material_replay_cases(
        {
            "schema": "scbe.prime-token-material-runtime.v1",
            "arm": "canonical_six_view_reader",
            "seed": 17,
            "source_manifest": str(output / "SOURCE_MANIFEST.json"),
            "source_manifest_sha256": receipt["source_manifest_sha256"],
            "split_manifest": str(output / "SPLIT_MANIFEST.json"),
            "split_manifest_sha256": receipt["split_manifest_sha256"],
            "cases_manifest": str(output / "CASES_MANIFEST.json"),
            "cases_manifest_sha256": receipt["cases_manifest_sha256"],
            "evaluator_receipt": str(output / "EVALUATOR_RECEIPT.json"),
            "evaluator_receipt_sha256": receipt["evaluator_receipt_sha256"],
        }
    )
    assert reconstruction["receipt"]["held_case_count"] == 6
    assert reconstruction["receipt"]["producer_targets_consumed"] is False
    with pytest.raises(FileExistsError, match="already exists"):
        build_material_case_bundle(
            benchmark_path=benchmark_path,
            source_family_audit_path=audit_path,
            source_queue_path=queue_path,
            closed_source_snapshot_path=snapshot_path,
            ordinary_source_path=ordinary_path,
            retention_source_path=retention_path,
            output_dir=output,
            minimum_final_test=3,
            maximum_source_fraction=1.0,
            maximum_family_fraction=1.0,
        )


def test_bundle_writer_rejects_queue_session_absent_from_closed_snapshot(
    tmp_path: Path,
) -> None:
    benchmark = _benchmark(large=False)
    benchmark_path = tmp_path / "BENCHMARK.json"
    audit_path = tmp_path / "SOURCE_FAMILY_AUDIT.json"
    queue_path = tmp_path / "SOURCE_QUEUE.json"
    snapshot_path = _snapshot(tmp_path, benchmark)
    ordinary_path = tmp_path / "ordinary-source.jsonl"
    retention_path = tmp_path / "retention-source.jsonl"
    benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
    audit_path.write_text(json.dumps(_audit()), encoding="utf-8")
    queue_path.write_text(json.dumps(_queue(benchmark)), encoding="utf-8")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["sources"].pop()
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    row = {
        "id": "row-1",
        "text": "packet-free fixture",
        "source_locator": "fixture://row/1",
        "content_sha256": "c" * 64,
    }
    ordinary_path.write_text(
        json.dumps({**row, "source_family": "ordinary-family"}) + "\n",
        encoding="utf-8",
    )
    retention_path.write_text(
        json.dumps({**row, "id": "row-2", "source_family": "retention-family"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="absent from the closed snapshot"):
        build_material_case_bundle(
            benchmark_path=benchmark_path,
            source_family_audit_path=audit_path,
            source_queue_path=queue_path,
            closed_source_snapshot_path=snapshot_path,
            ordinary_source_path=ordinary_path,
            retention_source_path=retention_path,
            output_dir=tmp_path / "bundle",
            minimum_final_test=3,
            maximum_source_fraction=1.0,
            maximum_family_fraction=1.0,
        )
