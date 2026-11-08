from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from python.scbe.prime_token_catalog import InputRecord, PrimeTokenCatalogBuilder, sha256_file
from python.scbe.prime_token_prospective import (
    PREPARATION_SCHEMA,
    SOURCE_INVENTORY_SCHEMA,
    build_e92_prospective_run,
    canonical_sha256,
    json_bytes,
)
from python.scbe.prime_token_prospective_verify import verify_e92_prospective_bundle
from python.scbe.prime_token_query_harvest import (
    REVIEW_LABEL_SCHEMA,
    REVIEW_QUEUE_SCHEMA,
    review_queue_sha256,
)


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _fixture(tmp_path: Path) -> dict[str, Path]:
    catalog_root = tmp_path / "catalog"
    builder = PrimeTokenCatalogBuilder(catalog_root, section_chars=256, range_size=128)
    records = [
        ("source0.md", "Prime sieve factors and composite survivors remain exact."),
        ("source1.md", "Who what when where and why organize active reading."),
        ("source2.md", "Speech rhythm marks nouns verbs and sentence relations."),
        ("source3.md", "Atomic elements and chemistry support material research."),
        ("source4.md", "Package documentation verifies wheels hashes and releases."),
        ("source5.md", "A highway junction routes a car beneath the bridge."),
    ]
    for name, text in records:
        builder.ingest_record(
            InputRecord(
                text=text,
                source_uri=f"local://fixture/{name}",
                source_kind="fixture",
                license_name="fixture",
            )
        )
    builder.finalize()
    catalog = catalog_root / "catalog.sqlite3"
    catalog_hash = sha256_file(catalog)
    candidates = []
    query_templates = (
        "Research the prime sieve source request {index}.",
        "Use who what when where why for source request {index}.",
        "Publish package documentation source request {index}.",
    )
    for index in range(30):
        query = query_templates[index % len(query_templates)].format(index=index)
        query_hash = sha256(query.encode("utf-8")).hexdigest()
        candidates.append(
            {
                "candidate_id": f"request-{query_hash[:16]}",
                "query_sha256": query_hash,
                "session_id": f"session-{index}",
                "chunk_index": 0,
                "source_schema": "clay.direct-speech-turn.v1",
                "authored_at_utc": f"2026-11-07T10:{index:02d}:00+00:00",
                "turn_ordinal": index,
                "topic_groups": ["source_research"],
                "query": query,
            }
        )
    queue = {
        "schema": REVIEW_QUEUE_SCHEMA,
        "dataset": str(tmp_path / "prospective.jsonl"),
        "dataset_sha256": "d" * 64,
        "session_ids": [row["session_id"] for row in candidates],
        "selection_policy": {"ordering": "fixture"},
        "prospective_boundary": {
            "catalog_sha256": catalog_hash,
            "catalog_generated_at_utc": "2026-11-07T09:36:44+00:00",
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    queue["queue_sha256"] = review_queue_sha256(queue)
    queue_path = _write(tmp_path / "QUEUE.json", queue)
    source_rows = [
        {
            "source_uri": f"local://fixture/{name}",
            "unique_suffix": name,
        }
        for name, _text in records
    ]
    source_inventory = {
        "schema": SOURCE_INVENTORY_SCHEMA,
        "catalog": str(catalog),
        "catalog_sha256": catalog_hash,
        "source_count": len(source_rows),
        "sources": source_rows,
    }
    source_path = _write(tmp_path / "SOURCES.json", source_inventory)
    labels = {
        "schema": REVIEW_LABEL_SCHEMA,
        "queue_sha256": queue["queue_sha256"],
        "reviewer": "independent-test-reviewer",
        "reviewed_at_utc": "2026-11-07T11:00:00+00:00",
        "labels": [
            {
                "query_sha256": row["query_sha256"],
                "decision": "accept",
                "relevant_source_suffix": records[index % len(records)][0],
                "review_stratum": f"stratum-{index % 3}",
                "rationale": "Synthetic fixture relevance label.",
            }
            for index, row in enumerate(candidates)
        ],
    }
    labels_path = _write(tmp_path / "LABELS.json", labels)
    receipt_core = {
        "schema": PREPARATION_SCHEMA,
        "status": "READY_FOR_INDEPENDENT_HASH_BOUND_REVIEW_NO_SCORING",
        "queue": str(queue_path),
        "queue_file_sha256": sha256_file(queue_path),
        "queue_content_sha256": queue["queue_sha256"],
        "candidate_count": len(candidates),
        "catalog": str(catalog),
        "catalog_sha256": catalog_hash,
        "source_count": len(source_rows),
        "template_sha256": "t" * 64,
        "source_inventory_sha256": canonical_sha256(source_inventory),
        "scoring": "NOT_AUTHORIZED_BY_PREPARATION",
        "training_intake": "NOT_AUTHORIZED",
        "serving": "NOT_AUTHORIZED",
        "merge": "NOT_AUTHORIZED",
        "promotion": "NOT_AUTHORIZED",
    }
    receipt = {**receipt_core, "receipt_sha256": canonical_sha256(receipt_core)}
    receipt_path = _write(tmp_path / "PREPARATION.json", receipt)
    return {
        "catalog": catalog,
        "queue": queue_path,
        "labels": labels_path,
        "source_inventory": source_path,
        "preparation": receipt_path,
    }


def _run(paths: dict[str, Path]) -> dict[str, dict]:
    return build_e92_prospective_run(
        queue_path=paths["queue"],
        labels_path=paths["labels"],
        preparation_receipt_path=paths["preparation"],
        source_inventory_path=paths["source_inventory"],
        catalog_database=paths["catalog"],
        control_seeds=(3, 5, 7),
        limit=5,
    )


def _write_bundle(path: Path, bundle: dict[str, dict]) -> Path:
    path.mkdir()
    (path / "BENCHMARK.json").write_bytes(json_bytes(bundle["benchmark"]))
    (path / "RESULT.json").write_bytes(json_bytes(bundle["result"]))
    (path / "RUN_RECEIPT.json").write_bytes(json_bytes(bundle["receipt"]))
    return path


def test_e92_prospective_run_is_strict_controlled_and_nonpromoting(tmp_path: Path) -> None:
    bundle = _run(_fixture(tmp_path))

    assert bundle["benchmark"]["query_provenance"] == "independent_external"
    assert len(bundle["benchmark"]["queries"]) == 30
    assert bundle["result"]["candidate_arm"] == "late_output_fused"
    assert bundle["result"]["query_count"] == 30
    assert len(bundle["result"]["arms"]["random_rank_fusion"]) == 3
    assert {
        "random_rank_fusion_seed_3",
        "random_rank_fusion_seed_5",
        "random_rank_fusion_seed_7",
    }.issubset(bundle["result"]["gates"])
    assert bundle["result"]["diversity"]["relevant_source_count"] == 6
    assert bundle["result"]["diversity"]["topic_strata_count"] == 3
    assert bundle["receipt"]["promotion"] == "NOT_AUTHORIZED"
    assert bundle["receipt"]["training_intake"] == "NOT_AUTHORIZED"
    assert bundle["receipt"]["review_summary"]["decision_count"] == 30
    assert bundle["receipt"]["review_summary"]["accepted_count"] == 30

    verification = verify_e92_prospective_bundle(_write_bundle(tmp_path / "bundle", bundle))
    assert verification["status"] == "VERIFIED_E92_PROSPECTIVE_NO_AUTOMATIC_PROMOTION"
    assert verification["error_count"] == 0
    assert verification["promotion"] == "NOT_AUTHORIZED"


def test_e92_prospective_run_refuses_incomplete_or_unbalanced_review(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    labels = json.loads(paths["labels"].read_text(encoding="utf-8"))
    incomplete = deepcopy(labels)
    incomplete["labels"][0]["decision"] = "UNREVIEWED"
    _write(paths["labels"], incomplete)
    with pytest.raises(ValueError, match="accept/reject plus rationale"):
        _run(paths)

    _write(paths["labels"], labels)
    unbalanced = deepcopy(labels)
    for row in unbalanced["labels"]:
        row["relevant_source_suffix"] = "source0.md"
    _write(paths["labels"], unbalanced)
    with pytest.raises(ValueError, match="six relevant catalog sources"):
        _run(paths)


def test_e92_prospective_run_refuses_mutated_preparation_receipt(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    receipt = json.loads(paths["preparation"].read_text(encoding="utf-8"))
    receipt["candidate_count"] = 29
    _write(paths["preparation"], receipt)

    with pytest.raises(ValueError, match="content hash mismatch"):
        _run(paths)


def test_e92_independent_verifier_rejects_mutated_result(tmp_path: Path) -> None:
    bundle = _run(_fixture(tmp_path))
    output = _write_bundle(tmp_path / "bundle", bundle)
    result = json.loads((output / "RESULT.json").read_text(encoding="utf-8"))
    result["arms"]["late_output_fused"][0]["metrics"]["mrr"] += 0.25
    _write(output / "RESULT.json", result)

    verification = verify_e92_prospective_bundle(output)
    assert verification["status"] == "INVALID_E92_PROSPECTIVE_BUNDLE"
    assert verification["error_count"] >= 1
