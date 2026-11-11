#!/usr/bin/env python3
"""Audit the fail-closed release boundary for prime-token frozen input access."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

CONTRACT_SCHEMA = "scbe.prime-token-frozen-input-access-release-contract.v1"
STATE_SCHEMA = "scbe.prime-token-frozen-input-access-release-state.v1"
REPORT_SCHEMA = "scbe.prime-token-frozen-input-access-release-audit.v1"
NOT_AUTHORIZED = "NOT_AUTHORIZED"


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _string_set(value: Any, label: str, errors: list[str]) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        errors.append(f"{label} must be a list of non-empty strings")
        return set()
    if len(set(value)) != len(value):
        errors.append(f"{label} contains duplicates")
    return set(value)


def audit_release(*, contract_path: Path, state_path: Path) -> dict[str, Any]:
    contract_file = contract_path.resolve(strict=True)
    state_file = state_path.resolve(strict=True)
    contract = _object(contract_file, "release contract")
    state = _object(state_file, "release state")
    errors: list[str] = []
    blockers: list[str] = []

    if contract.get("schema") != CONTRACT_SCHEMA:
        errors.append("release contract schema mismatch")
    if state.get("schema") != STATE_SCHEMA:
        errors.append("release state schema mismatch")
    contract_id = str(contract.get("contract_id") or "")
    if not contract_id or state.get("contract_id") != contract_id:
        errors.append("release state targets a different contract")

    required_arms = _string_set(contract.get("required_arms"), "required_arms", errors)
    observed_arms = _string_set(state.get("arms"), "state arms", errors)
    missing_arms = sorted(required_arms - observed_arms)
    if missing_arms:
        blockers.append(f"missing required arms: {', '.join(missing_arms)}")

    required_metrics = _string_set(contract.get("required_metrics"), "required_metrics", errors)
    observed_metrics = _string_set(state.get("metrics"), "state metrics", errors)
    missing_metrics = sorted(required_metrics - observed_metrics)
    if missing_metrics:
        blockers.append(f"missing required metrics: {', '.join(missing_metrics)}")

    minimums = contract.get("minimums")
    observed = state.get("observed")
    count_gates: dict[str, dict[str, Any]] = {}
    if not isinstance(minimums, dict) or not isinstance(observed, dict):
        errors.append("minimums and observed must be JSON objects")
    else:
        for name, minimum in sorted(minimums.items()):
            if not isinstance(minimum, int) or minimum < 0:
                errors.append(f"minimum {name} must be a non-negative integer")
                continue
            actual = observed.get(name)
            passed = isinstance(actual, int) and not isinstance(actual, bool) and actual >= minimum
            count_gates[name] = {
                "minimum": minimum,
                "observed": actual,
                "passed": passed,
            }
            if not passed and name != "fresh_seeds":
                blockers.append(f"{name} is below {minimum}: observed {actual!r}")

    seeds = state.get("seeds")
    if not isinstance(seeds, list) or not all(isinstance(seed, int) for seed in seeds):
        errors.append("state seeds must be a list of integers")
        seed_count = 0
    else:
        seed_count = len(set(seeds))
        if seed_count != len(seeds):
            errors.append("state seeds contain duplicates")
    fresh_seed_minimum = int((minimums or {}).get("fresh_seeds", 0)) if isinstance(minimums, dict) else 0
    if seed_count < fresh_seed_minimum:
        blockers.append(f"fresh seed count is below {fresh_seed_minimum}: observed {seed_count}")

    required_evidence = contract.get("required_evidence")
    evidence = state.get("evidence")
    evidence_gates: dict[str, dict[str, Any]] = {}
    if not isinstance(required_evidence, dict) or not isinstance(evidence, dict):
        errors.append("required_evidence and state evidence must be JSON objects")
    else:
        for evidence_id, accepted_value in sorted(required_evidence.items()):
            accepted = _string_set(accepted_value, f"accepted statuses for {evidence_id}", errors)
            entry = evidence.get(evidence_id)
            if not isinstance(entry, dict):
                blockers.append(f"missing evidence: {evidence_id}")
                evidence_gates[evidence_id] = {"passed": False, "status": None}
                continue
            status = str(entry.get("status") or "")
            artifact_path: Path | None = None
            artifact = entry.get("path")
            if artifact:
                artifact_path = Path(str(artifact)).resolve(strict=False)
                if not artifact_path.is_file():
                    blockers.append(f"evidence path is unavailable for {evidence_id}")
                elif entry.get("read_status_from_artifact"):
                    try:
                        artifact_value = _object(artifact_path, f"evidence {evidence_id}")
                        status = str(artifact_value.get("status") or "")
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        errors.append(f"cannot read evidence status for {evidence_id}: {exc}")
                expected_hash = str(entry.get("sha256") or "").casefold()
                if expected_hash:
                    if len(expected_hash) != 64:
                        errors.append(f"invalid sha256 for {evidence_id}")
                    elif artifact_path.is_file() and sha256_file(artifact_path) != expected_hash:
                        errors.append(f"sha256 mismatch for {evidence_id}")
                elif entry.get("immutable"):
                    errors.append(f"immutable evidence lacks sha256: {evidence_id}")
            elif entry.get("immutable"):
                blockers.append(f"immutable evidence path is missing: {evidence_id}")
            passed = status in accepted and artifact_path is not None and artifact_path.is_file()
            evidence_gates[evidence_id] = {
                "accepted_statuses": sorted(accepted),
                "path": str(artifact_path) if artifact_path else None,
                "passed": passed,
                "status": status or None,
            }
            if not passed:
                blockers.append(f"{evidence_id} status is {status or 'MISSING'}")

    state_authority = state.get("authority")
    if not isinstance(state_authority, dict):
        errors.append("state authority must be a JSON object")
    else:
        for field in ("training_intake", "merge", "promotion"):
            if state_authority.get(field) != NOT_AUTHORIZED:
                errors.append(f"state authority drifted for {field}")
        if state_authority.get("partial_unfreeze") != "NONE":
            errors.append("state authority drifted for partial_unfreeze")
        if state_authority.get("tool_dispatch") != "DISABLED":
            errors.append("state authority drifted for tool_dispatch")

    status = "READY_FOR_MANUAL_TRAINING_RELEASE_REVIEW"
    if blockers:
        status = "WAITING_FOR_RELEASE_REQUIREMENTS"
    if errors:
        status = "INVALID_RELEASE_STATE"

    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "contract_id": contract_id,
        "error_count": len(errors),
        "errors": errors,
        "blocker_count": len(set(blockers)),
        "blockers": sorted(set(blockers)),
        "inputs": {
            "contract": str(contract_file),
            "contract_sha256": sha256_file(contract_file),
            "state": str(state_file),
            "state_sha256": sha256_file(state_file),
        },
        "gates": {
            "counts": count_gates,
            "required_arms": not missing_arms,
            "required_metrics": not missing_metrics,
            "fresh_seeds": seed_count >= fresh_seed_minimum,
            "evidence": evidence_gates,
        },
        "authority": {
            "training_intake": NOT_AUTHORIZED,
            "merge": NOT_AUTHORIZED,
            "promotion": NOT_AUTHORIZED,
            "partial_unfreeze": "NONE",
            "tool_dispatch": "DISABLED",
        },
        "claim_boundary": (
            "Passing means only that a separately authorized human may review a material training launch. "
            "This evaluator never launches training and grants no scoring, merge, serving, promotion, tool "
            "dispatch, or partial-unfreeze authority."
        ),
    }
    report["report_sha256"] = canonical_sha256(report)
    return report


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(pending, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit_release(contract_path=args.contract, state_path=args.state)
    atomic_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "error_count": report["error_count"],
                "blocker_count": report["blocker_count"],
                "report_sha256": report["report_sha256"],
            },
            sort_keys=True,
        )
    )
    if report["status"] == "READY_FOR_MANUAL_TRAINING_RELEASE_REVIEW":
        return 0
    return 1 if report["error_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
