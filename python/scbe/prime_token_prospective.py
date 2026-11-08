"""Strict, receipt-bound one-shot execution for the E92 prospective gate."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from python.scbe.prime_token_benchmark import (
    BENCHMARK_SCHEMA,
    MIN_CAPABILITY_QUERIES,
    evaluate_late_output_fused_catalog,
)
from python.scbe.prime_token_catalog import (
    LATE_OUTPUT_FUSION_REVISION,
    sha256_file,
)
from python.scbe.prime_token_query_harvest import (
    REVIEW_LABEL_SCHEMA,
    REVIEW_QUEUE_SCHEMA,
    build_reviewed_benchmark,
    review_queue_sha256,
)

PREPARATION_SCHEMA = "clay.prime-token-prospective-review-preparation.v1"
SOURCE_INVENTORY_SCHEMA = "clay.prime-token-catalog-source-suffixes.v1"
E92_RUN_SCHEMA = "scbe.e92-prospective-run.v1"
SHA256_RE = re.compile(r"[0-9a-f]{64}")


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _aware_datetime(value: Any, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def _load_object(path: Path, *, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _verify_preparation_receipt(
    receipt: Mapping[str, Any],
    *,
    receipt_path: Path,
    queue_path: Path,
    queue: Mapping[str, Any],
    catalog_database: Path,
    source_inventory: Mapping[str, Any],
) -> None:
    if receipt.get("schema") != PREPARATION_SCHEMA:
        raise ValueError("unknown preparation receipt schema")
    if receipt.get("status") != "READY_FOR_INDEPENDENT_HASH_BOUND_REVIEW_NO_SCORING":
        raise ValueError("preparation receipt is not review-ready")
    receipt_core = dict(receipt)
    claimed_receipt_hash = str(receipt_core.pop("receipt_sha256", "")).casefold()
    if not SHA256_RE.fullmatch(claimed_receipt_hash) or claimed_receipt_hash != canonical_sha256(
        receipt_core
    ):
        raise ValueError("preparation receipt content hash mismatch")
    if Path(str(receipt.get("queue") or "")).resolve() != queue_path:
        raise ValueError("preparation receipt points to another queue")
    if Path(str(receipt.get("catalog") or "")).resolve() != catalog_database:
        raise ValueError("preparation receipt points to another catalog")
    if str(receipt.get("queue_file_sha256") or "").casefold() != sha256_file(queue_path):
        raise ValueError("prepared queue file hash mismatch")
    if str(receipt.get("queue_content_sha256") or "").casefold() != str(
        queue.get("queue_sha256") or ""
    ).casefold():
        raise ValueError("prepared queue content hash mismatch")
    if str(receipt.get("catalog_sha256") or "").casefold() != sha256_file(catalog_database):
        raise ValueError("prepared catalog hash mismatch")
    if int(receipt.get("candidate_count", -1)) != int(queue.get("candidate_count", -2)):
        raise ValueError("preparation candidate count mismatch")
    if int(receipt.get("source_count", -1)) != int(source_inventory.get("source_count", -2)):
        raise ValueError("preparation source count mismatch")
    if str(receipt.get("source_inventory_sha256") or "").casefold() != canonical_sha256(
        source_inventory
    ):
        raise ValueError("prepared source inventory hash mismatch")
    if receipt.get("scoring") != "NOT_AUTHORIZED_BY_PREPARATION":
        raise ValueError("preparation receipt unexpectedly authorizes scoring")
    if any(
        receipt.get(field) != "NOT_AUTHORIZED"
        for field in ("training_intake", "serving", "merge", "promotion")
    ):
        raise ValueError("preparation receipt weakens a no-promotion boundary")
    if receipt_path.stat().st_size <= 0:
        raise ValueError("preparation receipt is empty")


def _validate_queue(queue: Mapping[str, Any], *, catalog_sha256: str) -> list[dict[str, Any]]:
    if queue.get("schema") != REVIEW_QUEUE_SCHEMA:
        raise ValueError("unknown review queue schema")
    actual_hash = review_queue_sha256(queue)
    if queue.get("queue_sha256") != actual_hash:
        raise ValueError("review queue content hash mismatch")
    boundary = queue.get("prospective_boundary")
    if not isinstance(boundary, Mapping):
        raise ValueError("prospective queue has no frozen catalog boundary")
    if str(boundary.get("catalog_sha256") or "").casefold() != catalog_sha256:
        raise ValueError("prospective queue targets another catalog")
    cutoff = _aware_datetime(
        boundary.get("catalog_generated_at_utc"),
        label="catalog freeze timestamp",
    )
    candidates = queue.get("candidates")
    if not isinstance(candidates, list) or int(queue.get("candidate_count", -1)) != len(
        candidates
    ):
        raise ValueError("prospective queue candidate count mismatch")
    if len(candidates) < MIN_CAPABILITY_QUERIES:
        raise ValueError(
            f"prospective queue needs at least {MIN_CAPABILITY_QUERIES} candidates"
        )
    ids: set[str] = set()
    hashes: set[str] = set()
    validated = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping):
            raise ValueError(f"candidate {index} is not an object")
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        query = str(candidate.get("query") or "").strip()
        query_hash = str(candidate.get("query_sha256") or "").strip().casefold()
        session_id = str(candidate.get("session_id") or "").strip()
        authored = _aware_datetime(
            candidate.get("authored_at_utc"),
            label=f"candidate {index} authored timestamp",
        )
        if authored <= cutoff:
            raise ValueError(f"candidate {index} is not after the catalog freeze")
        if not candidate_id or candidate_id in ids:
            raise ValueError(f"candidate {index} has a missing or duplicate id")
        if not session_id:
            raise ValueError(f"candidate {index} has no source session")
        if not query or sha256(query.encode("utf-8")).hexdigest() != query_hash:
            raise ValueError(f"candidate {index} query hash mismatch")
        if query_hash in hashes:
            raise ValueError(f"candidate {index} duplicates a query hash")
        ids.add(candidate_id)
        hashes.add(query_hash)
        validated.append(dict(candidate))
    return validated


def _source_suffixes(source_inventory: Mapping[str, Any], *, catalog_sha256: str) -> set[str]:
    if source_inventory.get("schema") != SOURCE_INVENTORY_SCHEMA:
        raise ValueError("unknown catalog source inventory schema")
    if str(source_inventory.get("catalog_sha256") or "").casefold() != catalog_sha256:
        raise ValueError("source inventory targets another catalog")
    rows = source_inventory.get("sources")
    if not isinstance(rows, list) or int(source_inventory.get("source_count", -1)) != len(rows):
        raise ValueError("source inventory count mismatch")
    suffixes = [str(row.get("unique_suffix") or "").strip() for row in rows if isinstance(row, Mapping)]
    if len(suffixes) != len(rows) or not all(suffixes) or len(set(suffixes)) != len(suffixes):
        raise ValueError("source inventory suffixes must be complete and unique")
    return set(suffixes)


def _strict_labels(
    labels: Mapping[str, Any],
    *,
    queue_sha256: str,
    candidates: Sequence[Mapping[str, Any]],
    source_suffixes: set[str],
) -> dict[str, Any]:
    if labels.get("schema") != REVIEW_LABEL_SCHEMA:
        raise ValueError("unknown review label schema")
    if str(labels.get("queue_sha256") or "").casefold() != queue_sha256:
        raise ValueError("labels target another queue")
    reviewer = str(labels.get("reviewer") or "").strip()
    reviewed_at = _aware_datetime(labels.get("reviewed_at_utc"), label="review time")
    if not reviewer:
        raise ValueError("reviewer identity is required")
    candidate_by_hash = {str(row["query_sha256"]): row for row in candidates}
    raw_labels = labels.get("labels")
    if not isinstance(raw_labels, list):
        raise ValueError("review labels must be a list")
    decisions: dict[str, dict[str, Any]] = {}
    accepted_suffixes: list[str] = []
    accepted_strata: list[str] = []
    for index, raw in enumerate(raw_labels):
        if not isinstance(raw, Mapping):
            raise ValueError(f"label {index} is not an object")
        query_hash = str(raw.get("query_sha256") or "").strip().casefold()
        if query_hash not in candidate_by_hash or query_hash in decisions:
            raise ValueError(f"label {index} has an unknown or duplicate query hash")
        decision = str(raw.get("decision") or "").strip()
        rationale = str(raw.get("rationale") or "").strip()
        if decision not in {"accept", "reject"} or not rationale:
            raise ValueError(f"label {index} requires accept/reject plus rationale")
        if decision == "accept":
            suffix = str(raw.get("relevant_source_suffix") or "").strip()
            stratum = str(raw.get("review_stratum") or "").strip()
            if suffix not in source_suffixes:
                raise ValueError(f"label {index} has an unknown source suffix")
            if not stratum:
                raise ValueError(f"label {index} needs a reviewed stratum")
            accepted_suffixes.append(suffix)
            accepted_strata.append(stratum)
        decisions[query_hash] = dict(raw)
    expected_hashes = set(candidate_by_hash)
    if set(decisions) != expected_hashes:
        raise ValueError("every prospective candidate requires exactly one decision")
    latest_authored = max(
        _aware_datetime(row.get("authored_at_utc"), label="candidate authored timestamp")
        for row in candidates
    )
    if reviewed_at <= latest_authored:
        raise ValueError("review time must be after every candidate authorship time")
    accepted_count = len(accepted_suffixes)
    if accepted_count < MIN_CAPABILITY_QUERIES:
        raise ValueError(
            f"review accepted {accepted_count}; at least {MIN_CAPABILITY_QUERIES} are required"
        )
    source_counts = Counter(accepted_suffixes)
    max_source_share = max(source_counts.values()) / accepted_count
    if len(source_counts) < 6:
        raise ValueError("review needs at least six relevant catalog sources before scoring")
    if max_source_share > 0.4:
        raise ValueError("one relevant source exceeds the 40-percent pre-score cap")
    if len(set(accepted_strata)) < 3:
        raise ValueError("review needs at least three strata before scoring")
    return {
        "reviewer": reviewer,
        "reviewed_at_utc": reviewed_at.isoformat(),
        "decision_count": len(decisions),
        "accepted_count": accepted_count,
        "rejected_count": len(decisions) - accepted_count,
        "review_strata": sorted(set(accepted_strata)),
        "relevant_source_count": len(source_counts),
        "max_relevant_source_share": max_source_share,
        "relevant_source_query_counts": dict(sorted(source_counts.items())),
    }


def build_e92_prospective_run(
    *,
    queue_path: str | Path,
    labels_path: str | Path,
    preparation_receipt_path: str | Path,
    source_inventory_path: str | Path,
    catalog_database: str | Path,
    control_seeds: Sequence[int] = (11, 29, 47),
    limit: int = 20,
) -> dict[str, dict[str, Any]]:
    """Validate the sealed review chain, then execute the E92 evaluator once."""
    queue_file = Path(queue_path).resolve(strict=True)
    labels_file = Path(labels_path).resolve(strict=True)
    preparation_file = Path(preparation_receipt_path).resolve(strict=True)
    source_file = Path(source_inventory_path).resolve(strict=True)
    catalog_file = Path(catalog_database).resolve(strict=True)
    queue = _load_object(queue_file, label="review queue")
    labels = _load_object(labels_file, label="review labels")
    preparation = _load_object(preparation_file, label="preparation receipt")
    source_inventory = _load_object(source_file, label="source inventory")
    catalog_hash = sha256_file(catalog_file)
    candidates = _validate_queue(queue, catalog_sha256=catalog_hash)
    suffixes = _source_suffixes(source_inventory, catalog_sha256=catalog_hash)
    _verify_preparation_receipt(
        preparation,
        receipt_path=preparation_file,
        queue_path=queue_file,
        queue=queue,
        catalog_database=catalog_file,
        source_inventory=source_inventory,
    )
    review_summary = _strict_labels(
        labels,
        queue_sha256=str(queue["queue_sha256"]),
        candidates=candidates,
        source_suffixes=suffixes,
    )
    benchmark = build_reviewed_benchmark(
        queue,
        labels,
        minimum_queries=MIN_CAPABILITY_QUERIES,
    )
    if benchmark.get("schema") != BENCHMARK_SCHEMA:
        raise ValueError("review did not produce the expected benchmark schema")
    benchmark_payload = json_bytes(benchmark)
    benchmark_hash = sha256(benchmark_payload).hexdigest()
    result = evaluate_late_output_fused_catalog(
        catalog_file,
        benchmark,
        benchmark_sha256=benchmark_hash,
        control_seeds=control_seeds,
        limit=limit,
    )
    result_payload = json_bytes(result)
    receipt_core = {
        "schema": E92_RUN_SCHEMA,
        "status": "E92_PROSPECTIVE_COMPLETE_NO_AUTOMATIC_PROMOTION",
        "algorithm_revision": LATE_OUTPUT_FUSION_REVISION,
        "result_status": result["status"],
        "catalog": str(catalog_file),
        "catalog_sha256": catalog_hash,
        "queue": str(queue_file),
        "queue_file_sha256": sha256_file(queue_file),
        "queue_content_sha256": queue["queue_sha256"],
        "labels_file_sha256": sha256_file(labels_file),
        "preparation_receipt_file_sha256": sha256_file(preparation_file),
        "source_inventory_file_sha256": sha256_file(source_file),
        "benchmark_sha256": benchmark_hash,
        "result_sha256": sha256(result_payload).hexdigest(),
        "implementation_hashes": {
            "prime_token_catalog.py": sha256_file(
                Path(__file__).resolve().with_name("prime_token_catalog.py")
            ),
            "prime_token_benchmark.py": sha256_file(
                Path(__file__).resolve().with_name("prime_token_benchmark.py")
            ),
            "prime_token_query_harvest.py": sha256_file(
                Path(__file__).resolve().with_name("prime_token_query_harvest.py")
            ),
            "prime_token_prospective.py": sha256_file(Path(__file__).resolve()),
        },
        "review_summary": review_summary,
        "control_seeds": list(control_seeds),
        "result_limit": limit,
        "training_intake": "NOT_AUTHORIZED",
        "serving": "NOT_AUTHORIZED",
        "merge": "NOT_AUTHORIZED",
        "promotion": "NOT_AUTHORIZED",
        "claim_boundary": (
            "This is a source-disjoint retrieval evaluation. A candidate pass does not automatically "
            "promote package defaults, probability tables, serving, tokenizers, adapters, or core weights."
        ),
    }
    receipt = {**receipt_core, "receipt_sha256": canonical_sha256(receipt_core)}
    return {"benchmark": benchmark, "result": result, "receipt": receipt}
