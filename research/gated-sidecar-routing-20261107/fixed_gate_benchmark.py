"""Evaluate the frozen, zero-parameter specialist eligibility contract.

This is a research harness, not a production router.  Prompt text is retained
to exercise lexical traps, but the gate deliberately uses only trusted envelope
fields.  It cannot train, load weights, serve, or promote a specialist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


BENCHMARK_SCHEMA = "scbe.fixed-specialist-gate-benchmark.v1"
RECEIPT_SCHEMA = "scbe.fixed-specialist-gate-receipt.v1"
CAPABILITY_ID = "clay.coding.v1"
ALLOWED_OUTPUT_SCHEMAS = frozenset(
    {
        "specialist_logits.v1",
        "typed_action_candidates.v1",
        "retrieval_evidence.v1",
    }
)
ALLOWED_SOURCE_KINDS = frozenset(
    {"conversation", "academic", "source_code", "tool_result"}
)
DECISIONS = frozenset({"CORE_PASS", "SPECIALIST", "ABSTAIN"})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fixed_gate(envelope: dict[str, Any]) -> tuple[str, str]:
    """Return a deterministic route and a stable, auditable reason code."""
    capability_id = envelope.get("capability_id")
    if capability_id != CAPABILITY_ID:
        return "CORE_PASS", "CAPABILITY_NOT_REQUESTED"

    checks = (
        (envelope.get("request_explicit") is True, "REQUEST_NOT_EXPLICIT"),
        (envelope.get("provenance_verified") is True, "PROVENANCE_UNVERIFIED"),
        (
            envelope.get("source_kind") in ALLOWED_SOURCE_KINDS,
            "SOURCE_KIND_NOT_ALLOWED",
        ),
        (
            envelope.get("requested_output_schema") in ALLOWED_OUTPUT_SCHEMAS,
            "OUTPUT_SCHEMA_NOT_ALLOWED",
        ),
        (envelope.get("specialist_available") is True, "SPECIALIST_UNAVAILABLE"),
        (envelope.get("capacity_available") is True, "CAPACITY_UNAVAILABLE"),
    )
    for passed, reason in checks:
        if not passed:
            return "ABSTAIN", reason
    return "SPECIALIST", "ELIGIBLE"


def evaluate_benchmark(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != BENCHMARK_SCHEMA:
        raise ValueError(f"unexpected benchmark schema: {payload.get('schema')!r}")
    if payload.get("authority") != "RESEARCH_ONLY_NO_TRAINING_NO_PROMOTION":
        raise ValueError("benchmark authority must forbid training and promotion")

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("benchmark cases must be a non-empty list")

    seen_ids: set[str] = set()
    confusion = {
        expected: {actual: 0 for actual in sorted(DECISIONS)}
        for expected in sorted(DECISIONS)
    }
    failures: list[dict[str, str]] = []
    reason_counts: dict[str, int] = {}
    ordinary_count = 0

    for row in cases:
        case_id = row.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in seen_ids:
            raise ValueError(f"case id must be unique and non-empty: {case_id!r}")
        seen_ids.add(case_id)
        expected = row.get("expected")
        if expected not in DECISIONS:
            raise ValueError(f"invalid expected decision for {case_id}: {expected!r}")
        if not isinstance(row.get("prompt"), str) or not row["prompt"].strip():
            raise ValueError(f"prompt must be non-empty for {case_id}")
        envelope = row.get("envelope")
        if not isinstance(envelope, dict):
            raise ValueError(f"envelope must be an object for {case_id}")

        actual, reason = fixed_gate(envelope)
        confusion[expected][actual] += 1
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if row.get("class") == "ordinary_prompt":
            ordinary_count += 1
        if actual != expected:
            failures.append(
                {"id": case_id, "expected": expected, "actual": actual, "reason": reason}
            )

    expected_non_specialist = sum(
        confusion[expected][actual]
        for expected in ("CORE_PASS", "ABSTAIN")
        for actual in DECISIONS
    )
    false_specialist_routes = sum(
        confusion[expected]["SPECIALIST"] for expected in ("CORE_PASS", "ABSTAIN")
    )
    expected_specialist = sum(confusion["SPECIALIST"].values())
    true_specialist_routes = confusion["SPECIALIST"]["SPECIALIST"]

    return {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS" if not failures else "FAIL",
        "authority": "RESEARCH_ONLY_NO_TRAINING_NO_PROMOTION",
        "benchmark": str(path.resolve()),
        "benchmark_sha256": sha256_file(path),
        "case_count": len(cases),
        "ordinary_prompt_count": ordinary_count,
        "confusion": confusion,
        "false_specialist_routes": false_specialist_routes,
        "false_route_rate": (
            false_specialist_routes / expected_non_specialist
            if expected_non_specialist
            else None
        ),
        "specialist_route_recall": (
            true_specialist_routes / expected_specialist if expected_specialist else None
        ),
        "reason_counts": dict(sorted(reason_counts.items())),
        "failures": failures,
        "promotion": "NOT_AUTHORIZED",
        "training_intake": "NOT_AUTHORIZED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = evaluate_benchmark(args.benchmark)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
