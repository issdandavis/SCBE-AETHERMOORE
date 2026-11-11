from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import pytest

from python.scbe.prime_token_catalog import (
    InputRecord,
    PrimeTokenCatalogBuilder,
    audit_catalog_relational_integrity,
    sha256_file,
)
from python.scbe.prime_token_prospective import (
    PREPARATION_SCHEMA,
    SOURCE_CHAIN_BUNDLE_FILES,
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
    integrity_path = _write(
        tmp_path / "CATALOG_INTEGRITY.json",
        audit_catalog_relational_integrity(catalog),
    )
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
    selection_audit_core = {
        "schema": "clay.prime-token-selection-audit.v1",
        "status": "PASS_EXACT_SELECTION_REPLAY_NO_SCORING",
        "dataset_sha256": queue["dataset_sha256"],
        "queue_sha256": queue["queue_sha256"],
        "input_rows": len(candidates),
        "candidate_count": len(candidates),
        "selection_rate": 1.0,
        "reason_counts": {"accepted": len(candidates)},
        "accepted_topic_counts": {"source_research": len(candidates)},
        "accepted_query_sha256": [row["query_sha256"] for row in candidates],
        "exact_candidate_replay": True,
        "private_text_emitted": False,
        "labels_opened": False,
        "scoring_authorized": False,
        "training_authorized": False,
        "promotion_authorized": False,
    }
    selection_audit = {
        **selection_audit_core,
        "audit_sha256": canonical_sha256(selection_audit_core),
    }
    selection_audit_path = _write(tmp_path / "QUEUE_SELECTION_AUDIT.json", selection_audit)
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
        "selection_audit": selection_audit_path,
        "labels": labels_path,
        "source_inventory": source_path,
        "preparation": receipt_path,
        "catalog_integrity": integrity_path,
    }


def _run(paths: dict[str, Path]) -> dict[str, Any]:
    return build_e92_prospective_run(
        queue_path=paths["queue"],
        selection_audit_path=paths["selection_audit"],
        labels_path=paths["labels"],
        preparation_receipt_path=paths["preparation"],
        source_inventory_path=paths["source_inventory"],
        catalog_integrity_receipt_path=paths["catalog_integrity"],
        catalog_database=paths["catalog"],
        control_seeds=(3, 5, 7),
        limit=5,
    )


def _write_bundle(path: Path, bundle: dict[str, Any]) -> Path:
    path.mkdir()
    (path / "BENCHMARK.json").write_bytes(json_bytes(bundle["benchmark"]))
    (path / "RESULT.json").write_bytes(json_bytes(bundle["result"]))
    source_chain = bundle["source_chain"]
    for role, filename in SOURCE_CHAIN_BUNDLE_FILES.items():
        (path / filename).write_bytes(json_bytes(source_chain[role]))
    (path / "RUN_RECEIPT.json").write_bytes(json_bytes(bundle["receipt"]))
    return path


def test_e92_prospective_run_is_strict_controlled_and_nonpromoting(
    tmp_path: Path,
) -> None:
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
    assert bundle["result"]["route_control_contract"]["passes"] is True
    assert all("passes_finite_sample_uncertainty" in gate for gate in bundle["result"]["gates"].values())
    assert bundle["receipt"]["promotion"] == "NOT_AUTHORIZED"
    assert bundle["receipt"]["training_intake"] == "NOT_AUTHORIZED"
    assert bundle["receipt"]["review_summary"]["decision_count"] == 30
    assert bundle["receipt"]["review_summary"]["accepted_count"] == 30

    verification = verify_e92_prospective_bundle(
        _write_bundle(tmp_path / "bundle", bundle),
        expected_control_seeds=(3, 5, 7),
    )
    assert verification["status"] == "VERIFIED_E92_PROSPECTIVE_NO_AUTOMATIC_PROMOTION"
    assert verification["error_count"] == 0
    assert verification["promotion"] == "NOT_AUTHORIZED"


def test_e92_prospective_run_refuses_incomplete_or_unbalanced_review(
    tmp_path: Path,
) -> None:
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


def test_e92_prospective_run_refuses_mutated_preparation_receipt(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    receipt = json.loads(paths["preparation"].read_text(encoding="utf-8"))
    receipt["candidate_count"] = 29
    _write(paths["preparation"], receipt)

    with pytest.raises(ValueError, match="content hash mismatch"):
        _run(paths)


def test_e92_prospective_run_refuses_failed_catalog_integrity_receipt(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    integrity = json.loads(paths["catalog_integrity"].read_text(encoding="utf-8"))
    integrity["status"] = "RELATIONAL_INTEGRITY_FAIL"
    _write(paths["catalog_integrity"], integrity)

    with pytest.raises(ValueError, match="integrity receipt status is not a pass"):
        _run(paths)


def test_e92_prospective_run_refuses_selection_audit_authority_drift(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    audit = json.loads(paths["selection_audit"].read_text(encoding="utf-8"))
    audit["labels_opened"] = True
    audit_core = dict(audit)
    audit_core.pop("audit_sha256")
    audit["audit_sha256"] = canonical_sha256(audit_core)
    _write(paths["selection_audit"], audit)

    with pytest.raises(ValueError, match="selection audit authority invariant failed: labels_opened"):
        _run(paths)


def test_e92_independent_verifier_rejects_mutated_result(tmp_path: Path) -> None:
    bundle = _run(_fixture(tmp_path))
    output = _write_bundle(tmp_path / "bundle", bundle)
    result = json.loads((output / "RESULT.json").read_text(encoding="utf-8"))
    result["arms"]["late_output_fused"][0]["metrics"]["mrr"] += 0.25
    _write(output / "RESULT.json", result)

    verification = verify_e92_prospective_bundle(
        output,
        expected_control_seeds=(3, 5, 7),
    )
    assert verification["status"] == "INVALID_E92_PROSPECTIVE_BUNDLE"
    assert verification["error_count"] >= 1


def test_e92_independent_verifier_rejects_route_width_contract_tampering(
    tmp_path: Path,
) -> None:
    bundle = _run(_fixture(tmp_path))
    output = _write_bundle(tmp_path / "bundle", bundle)
    result_path = output / "RESULT.json"
    receipt_path = output / "RUN_RECEIPT.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    result["route_control_contract"]["rows"][0]["route_null_width"] += 1
    result_path.write_bytes(json_bytes(result))
    receipt["result_sha256"] = sha256_file(result_path)
    receipt_core = dict(receipt)
    receipt_core.pop("receipt_sha256")
    receipt["receipt_sha256"] = canonical_sha256(receipt_core)
    receipt_path.write_bytes(json_bytes(receipt))

    verification = verify_e92_prospective_bundle(
        output,
        expected_control_seeds=(3, 5, 7),
    )
    assert verification["status"] == "INVALID_E92_PROSPECTIVE_BUNDLE"
    assert any("route_control_contract" in error for error in verification["errors"])


def test_e92_independent_verifier_rejects_control_seed_substitution(
    tmp_path: Path,
) -> None:
    bundle = _run(_fixture(tmp_path))
    output = _write_bundle(tmp_path / "bundle", bundle)
    result_path = output / "RESULT.json"
    receipt_path = output / "RUN_RECEIPT.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    result["control_seeds"] = [3, 5, 11]
    result_path.write_bytes(json_bytes(result))
    receipt["control_seeds"] = [3, 5, 11]
    receipt["result_sha256"] = sha256_file(result_path)
    receipt_core = dict(receipt)
    receipt_core.pop("receipt_sha256")
    receipt["receipt_sha256"] = canonical_sha256(receipt_core)
    receipt_path.write_bytes(json_bytes(receipt))

    verification = verify_e92_prospective_bundle(
        output,
        expected_control_seeds=(3, 5, 7),
    )
    assert verification["status"] == "INVALID_E92_PROSPECTIVE_BUNDLE"
    assert any("expected seeds" in error for error in verification["errors"])


def test_e92_independent_verifier_rejects_query_source_substitution(
    tmp_path: Path,
) -> None:
    bundle = _run(_fixture(tmp_path))
    output = _write_bundle(tmp_path / "bundle", bundle)
    result_path = output / "RESULT.json"
    receipt_path = output / "RUN_RECEIPT.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    result["arms"]["random_rank_fusion"][0]["outcomes"][0]["query_source_uri"] = "private-session://forged-source/0"
    result_path.write_bytes(json_bytes(result))
    receipt["result_sha256"] = sha256_file(result_path)
    receipt_core = dict(receipt)
    receipt_core.pop("receipt_sha256")
    receipt["receipt_sha256"] = canonical_sha256(receipt_core)
    receipt_path.write_bytes(json_bytes(receipt))

    verification = verify_e92_prospective_bundle(
        output,
        expected_control_seeds=(3, 5, 7),
    )
    assert verification["status"] == "INVALID_E92_PROSPECTIVE_BUNDLE"
    assert any("query source mismatch" in error for error in verification["errors"])


def test_e92_independent_verifier_reconstructs_benchmark_from_source_chain(
    tmp_path: Path,
) -> None:
    bundle = _run(_fixture(tmp_path))
    output = _write_bundle(tmp_path / "bundle", bundle)
    labels_path = output / SOURCE_CHAIN_BUNDLE_FILES["labels"]
    receipt_path = output / "RUN_RECEIPT.json"
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    labels["labels"][0]["relevant_source_suffix"] = "source1.md"
    labels_path.write_bytes(json_bytes(labels))
    receipt["source_chain_bundle"]["labels"]["sha256"] = sha256_file(labels_path)
    receipt_core = dict(receipt)
    receipt_core.pop("receipt_sha256")
    receipt["receipt_sha256"] = canonical_sha256(receipt_core)
    receipt_path.write_bytes(json_bytes(receipt))

    verification = verify_e92_prospective_bundle(
        output,
        expected_control_seeds=(3, 5, 7),
    )
    assert verification["status"] == "INVALID_E92_PROSPECTIVE_BUNDLE"
    assert any("do not reconstruct from the source chain" in error for error in verification["errors"])


def test_e92_independent_verifier_rejects_rebound_selection_audit(
    tmp_path: Path,
) -> None:
    bundle = _run(_fixture(tmp_path))
    output = _write_bundle(tmp_path / "bundle", bundle)
    audit_path = output / SOURCE_CHAIN_BUNDLE_FILES["selection_audit"]
    receipt_path = output / "RUN_RECEIPT.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    audit["accepted_query_sha256"] = list(reversed(audit["accepted_query_sha256"]))
    audit_core = dict(audit)
    audit_core.pop("audit_sha256")
    audit["audit_sha256"] = canonical_sha256(audit_core)
    audit_path.write_bytes(json_bytes(audit))
    changed_hash = sha256_file(audit_path)
    receipt["selection_audit_file_sha256"] = changed_hash
    receipt["source_chain_bundle"]["selection_audit"]["sha256"] = changed_hash
    receipt["source_chain_bundle"]["selection_audit"]["source_file_sha256"] = changed_hash
    receipt_core = dict(receipt)
    receipt_core.pop("receipt_sha256")
    receipt["receipt_sha256"] = canonical_sha256(receipt_core)
    receipt_path.write_bytes(json_bytes(receipt))

    verification = verify_e92_prospective_bundle(
        output,
        expected_control_seeds=(3, 5, 7),
    )
    assert verification["status"] == "INVALID_E92_PROSPECTIVE_BUNDLE"
    assert any("selection audit candidate hash order mismatch" in error for error in verification["errors"])
