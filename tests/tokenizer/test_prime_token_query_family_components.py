from __future__ import annotations

import hashlib
import json
from pathlib import Path

from python.scbe.prime_token_query_family_components import (
    STATUS_INVALID,
    STATUS_UNDERPOWERED,
    STATUS_VERIFIED,
    audit_query_session_family_components,
)
from python.scbe.prime_token_query_harvest import review_queue_sha256


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _fixture(tmp_path: Path) -> dict[str, Path]:
    database_hash = "d" * 64
    sources = []
    canonical = []
    for family in range(3):
        path = tmp_path / f"source-{family}.md"
        path.write_text(f"source family {family}", encoding="utf-8")
        sources.append(
            {
                "source_uri": str(path),
                "unique_suffix": f"source-{family}",
            }
        )
        canonical.append(
            {
                "path": str(path),
                "family_id": f"family-{family}",
                "source_kind": "fixture",
                "license_name": "fixture",
                "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "catalog_source_rows": 1,
            }
        )

    candidates = []
    labels = []
    strata = ("source_research", "prime_sieve", "tongue_braid")
    for index in range(30):
        family = index % 3
        query = f"Private component fixture request {index} for family {family}."
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        session = f"session-{family}-{(index // 3) % 2}"
        candidates.append(
            {
                "candidate_id": f"request-{query_hash[:16]}",
                "query_sha256": query_hash,
                "session_id": session,
                "chunk_index": 0,
                "source_schema": "clay.direct-speech-turn.v1",
                "authored_at_utc": f"2026-11-13T10:{index:02d}:00+00:00",
                "turn_ordinal": index,
                "topic_groups": [strata[family]],
                "query": query,
            }
        )
        labels.append(
            {
                "query_sha256": query_hash,
                "decision": "accept",
                "relevant_source_suffix": f"source-{family}",
                "review_stratum": strata[family],
                "rationale": "Fixture relevance decision.",
            }
        )
    queue = {
        "schema": "scbe.prime-token-independent-review-queue.v1",
        "dataset": str(tmp_path / "private.jsonl"),
        "dataset_sha256": "a" * 64,
        "session_ids": sorted({row["session_id"] for row in candidates}),
        "selection_policy": {"scope_revision": "fixture-v1"},
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    queue["queue_sha256"] = review_queue_sha256(queue)
    queue_path = _write(tmp_path / "QUEUE.json", queue)
    labels_path = _write(
        tmp_path / "LABELS.json",
        {
            "schema": "scbe.prime-token-independent-review-labels.v1",
            "queue_sha256": queue["queue_sha256"],
            "reviewer": "fixture-reviewer",
            "reviewed_at_utc": "2026-11-13T12:00:00+00:00",
            "labels": labels,
        },
    )
    inventory_path = _write(
        tmp_path / "INVENTORY.json",
        {
            "schema": "clay.prime-token-catalog-source-suffixes.v1",
            "catalog_sha256": database_hash,
            "source_count": len(sources),
            "sources": sources,
        },
    )
    family_path = _write(
        tmp_path / "FAMILIES.json",
        {
            "schema": "scbe.prime-token-source-family-audit.v1",
            "error_count": 0,
            "catalog": {"database_sha256": database_hash},
            "canonical_sources": canonical,
        },
    )
    return {
        "queue": queue_path,
        "labels": labels_path,
        "inventory": inventory_path,
        "families": family_path,
    }


def _audit(paths: dict[str, Path]) -> dict:
    return audit_query_session_family_components(
        review_queue=paths["queue"],
        review_labels=paths["labels"],
        source_inventory=paths["inventory"],
        source_family_audit=paths["families"],
    )


def test_builds_three_disjoint_components_without_emitting_private_text(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    report = _audit(paths)

    assert report["status"] == STATUS_VERIFIED
    assert report["error_count"] == 0
    assert report["observed"]["accepted_query_count"] == 30
    assert report["observed"]["query_session_count"] == 6
    assert report["observed"]["target_family_count"] == 3
    assert report["observed"]["indivisible_component_count"] == 3
    assert report["observed"]["query_session_overlap_count"] == 0
    assert report["observed"]["target_family_overlap_count"] == 0
    assert all(row["query_count"] == 10 for row in report["folds"].values())
    assert all(report["gates"].values())
    assert report["authority"]["training_intake"] == "NOT_AUTHORIZED"
    serialized = json.dumps(report)
    assert "Private component fixture request" not in serialized
    assert "session-0-0" not in serialized


def test_component_and_fold_digest_is_invariant_to_input_order(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    first = _audit(paths)
    queue = json.loads(paths["queue"].read_text(encoding="utf-8"))
    labels = json.loads(paths["labels"].read_text(encoding="utf-8"))
    inventory = json.loads(paths["inventory"].read_text(encoding="utf-8"))
    families = json.loads(paths["families"].read_text(encoding="utf-8"))
    queue["candidates"].reverse()
    queue["session_ids"].reverse()
    queue["queue_sha256"] = review_queue_sha256(queue)
    labels["labels"].reverse()
    labels["queue_sha256"] = queue["queue_sha256"]
    inventory["sources"].reverse()
    families["canonical_sources"].reverse()
    _write(paths["queue"], queue)
    _write(paths["labels"], labels)
    _write(paths["inventory"], inventory)
    _write(paths["families"], families)

    second = _audit(paths)

    assert second["status"] == STATUS_VERIFIED
    assert second["component_split_sha256"] == first["component_split_sha256"]


def test_cross_family_session_is_kept_in_one_underpowered_component(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    queue = json.loads(paths["queue"].read_text(encoding="utf-8"))
    labels = json.loads(paths["labels"].read_text(encoding="utf-8"))
    bridge_session = queue["candidates"][0]["session_id"]
    bridged_hash = next(
        row["query_sha256"]
        for row in queue["candidates"]
        if row["session_id"] == bridge_session and row["query_sha256"] != queue["candidates"][0]["query_sha256"]
    )
    label = next(row for row in labels["labels"] if row["query_sha256"] == bridged_hash)
    label["relevant_source_suffix"] = "source-1"
    _write(paths["labels"], labels)

    report = _audit(paths)

    assert report["status"] == STATUS_UNDERPOWERED
    assert report["observed"]["indivisible_component_count"] == 2
    merged = next(row for row in report["components"] if row["family_count"] == 2)
    assert merged["family_ids"] == ["family-0", "family-1"]
    assert report["gates"]["minimum_indivisible_components"] is False
    assert report["observed"]["target_family_overlap_count"] == 0


def test_one_giant_component_is_underpowered_not_split(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    queue = json.loads(paths["queue"].read_text(encoding="utf-8"))
    labels = json.loads(paths["labels"].read_text(encoding="utf-8"))
    for row in queue["candidates"]:
        row["session_id"] = "one-bridge-session"
    queue["session_ids"] = ["one-bridge-session"]
    queue["queue_sha256"] = review_queue_sha256(queue)
    labels["queue_sha256"] = queue["queue_sha256"]
    _write(paths["queue"], queue)
    _write(paths["labels"], labels)

    report = _audit(paths)

    assert report["status"] == STATUS_UNDERPOWERED
    assert report["observed"]["indivisible_component_count"] == 1
    assert report["observed"]["maximum_component_share"] == 1.0
    assert report["gates"]["all_folds_nonempty"] is False
    assert report["gates"]["maximum_component_share"] is False


def test_unknown_source_suffix_fails_closed(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    labels = json.loads(paths["labels"].read_text(encoding="utf-8"))
    labels["labels"][0]["relevant_source_suffix"] = "unknown-source"
    _write(paths["labels"], labels)

    report = _audit(paths)

    assert report["status"] == STATUS_INVALID
    assert report["error_count"] == 1
    assert "unknown source suffix" in report["errors"][0]
    assert report["authority"]["scoring"] == "NOT_AUTHORIZED"
