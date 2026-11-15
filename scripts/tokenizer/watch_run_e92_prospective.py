#!/usr/bin/env python3
"""Wait for all E92 authorities, then run and independently verify once.

The watcher never creates or chooses review labels. It does not open the labels
file until the queue, preparation packet, exact selection replay, and
query-session/target-family component gate are all ready and hash-bound. A
verified result still authorizes no training, serving, merge, or promotion.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable, Mapping

SCHEMA = "scbe.e92-prospective-run-watcher.v1"
COLLECTOR_SCHEMA = "clay.codex-prospective-watcher.v1"
PREPARER_SCHEMA = "clay.prime-token-preparer-watcher.v1"
SELECTION_SCHEMA = "clay.prime-token-selection-audit-watcher.v1"
COMPONENT_WATCHER_SCHEMA = "scbe.prime-token-query-session-family-component-watcher.v1"
COMPONENT_REPORT_SCHEMA = "scbe.prime-token-query-session-family-components.v1"
COLLECTOR_READY = "READY_FOR_HUMAN_HASH_BOUND_REVIEW"
PREPARER_READY = {"PACKET_READY_NO_SCORING", "PACKET_ALREADY_READY_NO_SCORING"}
SELECTION_READY = {"AUDIT_VERIFIED_NO_SCORING", "AUDIT_ALREADY_VERIFIED_NO_SCORING"}
COMPONENT_READY = "QUERY_SESSION_FAMILY_COMPONENT_GATE_VERIFIED"
COMPONENT_REPORT_VERIFIED = "VERIFIED_QUERY_SESSION_FAMILY_COMPONENT_SPLIT"
VERIFIED_STATUS = "VERIFIED_E92_PROSPECTIVE_NO_AUTOMATIC_PROMOTION"
COMPONENT_AUTHORITY = {
    "scoring": "NOT_AUTHORIZED",
    "training_intake": "NOT_AUTHORIZED",
    "execution": "NONE",
    "merge": "NOT_AUTHORIZED",
    "promotion": "NOT_AUTHORIZED",
    "partial_unfreeze": "NONE",
}
COMPONENT_THRESHOLDS = {
    "minimum_accepted_queries": 30,
    "minimum_query_sessions": 3,
    "minimum_manifest_bound_families": 2,
    "minimum_indivisible_components": 3,
    "maximum_component_share": 0.8,
}


Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected.casefold():
        raise RuntimeError(f"{label} hash mismatch: {actual}")


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _forbidden_component_keys(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in {"query", "session_id"}:
                found.append(str(key))
            found.extend(_forbidden_component_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_forbidden_component_keys(item))
    return found


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(pending, path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_hidden(command: list[str]) -> subprocess.CompletedProcess[str]:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    )


def _base(
    collector: Mapping[str, Any],
    preparer: Mapping[str, Any],
    selection: Mapping[str, Any],
    component: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "updated_at_utc": utc_now(),
        "collector_status": str(collector.get("status") or "UNKNOWN"),
        "preparer_status": str(preparer.get("status") or "UNKNOWN"),
        "selection_audit_status": str(selection.get("status") or "UNKNOWN"),
        "component_gate_status": str(component.get("status") or "UNKNOWN"),
        "candidate_count": int(collector.get("candidate_count", 0)),
        "labels": "NOT_OPENED",
        "scoring": "NOT_AUTHORIZED",
        "training_intake": "NOT_AUTHORIZED",
        "serving": "NOT_AUTHORIZED",
        "merge": "NOT_AUTHORIZED",
        "promotion": "NOT_AUTHORIZED",
    }


def _verified_component_report(
    component_status: Mapping[str, Any],
    *,
    queue: Path,
    labels: Path,
    source_inventory: Path,
) -> tuple[Path, dict[str, Any]]:
    if component_status.get("gate_result") != COMPONENT_REPORT_VERIFIED:
        raise RuntimeError("component watcher gate result is not verified")
    if component_status.get("labels") != "OPENED_BY_PINNED_COMPONENT_AUDITOR":
        raise RuntimeError("component watcher did not record pinned label access")
    if component_status.get("authority") != COMPONENT_AUTHORITY:
        raise RuntimeError("component watcher authority differs from the fail-closed contract")
    for field, expected in COMPONENT_AUTHORITY.items():
        if component_status.get(field) != expected:
            raise RuntimeError(f"component watcher top-level authority mismatch: {field}")
    report_path = Path(str(component_status.get("gate_report") or "")).resolve(strict=True)
    require_hash(
        report_path,
        str(component_status.get("gate_report_sha256") or ""),
        "component report",
    )
    report = read_object(report_path)
    if (
        report.get("schema") != COMPONENT_REPORT_SCHEMA
        or report.get("status") != COMPONENT_REPORT_VERIFIED
        or int(report.get("error_count", -1)) != 0
        or report.get("errors") != []
    ):
        raise RuntimeError("component report is not a clean verified split")
    if report.get("authority") != COMPONENT_AUTHORITY:
        raise RuntimeError("component report authority differs from the fail-closed contract")
    if report.get("thresholds") != COMPONENT_THRESHOLDS:
        raise RuntimeError("component report thresholds differ from the frozen contract")
    if tuple(report.get("fold_names") or ()) != ("fold-0", "fold-1", "fold-2"):
        raise RuntimeError("component report fold names differ from the frozen contract")
    gates = report.get("gates")
    if not isinstance(gates, Mapping) or not gates or not all(value is True for value in gates.values()):
        raise RuntimeError("component report contains a failed gate")
    if _forbidden_component_keys(report):
        raise RuntimeError("component report contains raw query or session fields")

    report_core = dict(report)
    declared_report_hash = str(report_core.pop("report_sha256", "")).casefold()
    if canonical_sha256(report_core) != declared_report_hash:
        raise RuntimeError("component report digest does not replay")
    split_payload = {
        "fold_names": report.get("fold_names"),
        "components": report.get("components"),
        "folds": report.get("folds"),
    }
    split_hash = canonical_sha256(split_payload)
    if split_hash != str(report.get("component_split_sha256") or "").casefold():
        raise RuntimeError("component split digest does not replay")
    if split_hash != str(component_status.get("component_split_sha256") or "").casefold():
        raise RuntimeError("component watcher split binding mismatch")

    inputs = report.get("inputs")
    if not isinstance(inputs, Mapping):
        raise RuntimeError("component report inputs are missing")
    expected_paths = {
        "review_queue": queue,
        "review_labels": labels,
        "source_inventory": source_inventory,
    }
    expected_hashes = {
        "review_queue_sha256": sha256_file(queue),
        "review_labels_sha256": sha256_file(labels),
        "source_inventory_sha256": sha256_file(source_inventory),
    }
    for field, expected in expected_paths.items():
        if Path(str(inputs.get(field) or "")).resolve(strict=True) != expected:
            raise RuntimeError(f"component report input path mismatch: {field}")
    for field, expected in expected_hashes.items():
        if str(inputs.get(field) or "").casefold() != expected:
            raise RuntimeError(f"component report input hash mismatch: {field}")
    source_family = Path(str(inputs.get("source_family_audit") or "")).resolve(strict=True)
    require_hash(
        source_family,
        str(inputs.get("source_family_audit_sha256") or ""),
        "component source-family audit",
    )
    return report_path, report


def _verified_result(path: Path) -> dict[str, Any]:
    verification = read_object(path)
    if (
        verification.get("status") != VERIFIED_STATUS
        or int(verification.get("error_count", -1)) != 0
        or verification.get("training_intake") != "NOT_AUTHORIZED"
        or verification.get("serving") != "NOT_AUTHORIZED"
        or verification.get("merge") != "NOT_AUTHORIZED"
        or verification.get("promotion") != "NOT_AUTHORIZED"
    ):
        raise RuntimeError("independent E92 verification did not close cleanly")
    return verification


def run_cycle(
    *,
    collector_status_path: Path,
    preparer_status_path: Path,
    selection_status_path: Path,
    component_status_path: Path,
    labels_path: Path,
    catalog_database: Path,
    catalog_database_sha256: str,
    catalog_integrity_audit: Path,
    catalog_integrity_audit_sha256: str,
    runner: Path,
    runner_sha256: str,
    verifier: Path,
    verifier_sha256: str,
    output_dir: Path,
    state_dir: Path,
    control_seeds: tuple[int, ...],
    limit: int,
    python_executable: str,
    run_command: Runner | None = None,
) -> dict[str, Any]:
    state_dir.mkdir(parents=True, exist_ok=True)
    status_path = state_dir / "E92_WATCHER_STATUS.json"
    collector = read_object(collector_status_path.resolve(strict=True))
    preparer = read_object(preparer_status_path.resolve(strict=True))
    selection = read_object(selection_status_path.resolve(strict=True))
    component = read_object(component_status_path.resolve(strict=True))
    if collector.get("schema") != COLLECTOR_SCHEMA:
        raise ValueError("unexpected collector status schema")
    if preparer.get("schema") != PREPARER_SCHEMA:
        raise ValueError("unexpected preparer status schema")
    if selection.get("schema") != SELECTION_SCHEMA:
        raise ValueError("unexpected selection-audit status schema")
    if component.get("schema") != COMPONENT_WATCHER_SCHEMA:
        raise ValueError("unexpected component-gate status schema")
    base = _base(collector, preparer, selection, component)

    if collector.get("status") != COLLECTOR_READY:
        status = {**base, "status": "WAITING_FOR_PROSPECTIVE_QUEUE"}
        atomic_json(status_path, status)
        return status
    if preparer.get("status") not in PREPARER_READY:
        status = {**base, "status": "WAITING_FOR_PREPARATION_PACKET"}
        atomic_json(status_path, status)
        return status
    if selection.get("status") not in SELECTION_READY:
        status = {**base, "status": "WAITING_FOR_EXACT_SELECTION_AUDIT"}
        atomic_json(status_path, status)
        return status

    queue = Path(str(preparer.get("queue") or "")).resolve(strict=True)
    audit = Path(str(selection.get("output") or "")).resolve(strict=True)
    packet_dir = Path(str(preparer.get("output_dir") or "")).resolve(strict=True)
    preparation_receipt = (packet_dir / "PREPARATION_RECEIPT.json").resolve(strict=True)
    source_inventory = (packet_dir / "CATALOG_SOURCE_SUFFIXES.json").resolve(strict=True)
    require_hash(queue, str(preparer.get("queue_file_sha256") or ""), "queue")
    require_hash(queue, str(selection.get("queue_file_sha256") or ""), "selection queue")
    require_hash(audit, str(selection.get("audit_file_sha256") or ""), "selection audit")
    require_hash(
        preparation_receipt,
        str(preparer.get("receipt_file_sha256") or ""),
        "preparation receipt",
    )
    require_hash(
        source_inventory,
        str(preparer.get("source_inventory_file_sha256") or ""),
        "source inventory",
    )
    if component.get("status") != COMPONENT_READY:
        status = {**base, "status": "WAITING_FOR_QUERY_SESSION_FAMILY_COMPONENT_GATE"}
        atomic_json(status_path, status)
        return status
    catalog_database = catalog_database.resolve(strict=True)
    require_hash(catalog_database, catalog_database_sha256, "catalog database")
    boundary = collector.get("catalog_boundary")
    if not isinstance(boundary, Mapping) or boundary.get("catalog_sha256") != catalog_database_sha256.casefold():
        raise RuntimeError("collector catalog boundary does not match the pinned database")
    catalog_integrity_audit = catalog_integrity_audit.resolve(strict=True)
    require_hash(
        catalog_integrity_audit,
        catalog_integrity_audit_sha256,
        "catalog integrity audit",
    )
    runner = runner.resolve(strict=True)
    verifier = verifier.resolve(strict=True)
    require_hash(runner, runner_sha256, "E92 runner")
    require_hash(verifier, verifier_sha256, "E92 verifier")

    if not labels_path.is_file():
        status = {
            **base,
            "status": "WAITING_FOR_INDEPENDENT_LABELS",
            "queue_file_sha256": sha256_file(queue),
            "selection_audit_file_sha256": sha256_file(audit),
            "labels": "NOT_PRESENT",
        }
        atomic_json(status_path, status)
        return status

    labels = labels_path.resolve(strict=True)
    component_report, component_payload = _verified_component_report(
        component,
        queue=queue,
        labels=labels,
        source_inventory=source_inventory,
    )

    output_dir = output_dir.resolve()
    pending_output = output_dir.with_name(output_dir.name + ".pending")
    verification_path = state_dir / "E92_VERIFICATION.json"
    if pending_output.exists():
        status = {
            **base,
            "status": "PENDING_OUTPUT_REQUIRES_AUDIT",
            "labels": "PRESENT_NOT_REPORTED",
        }
        atomic_json(status_path, status)
        return status

    command_runner = run_command or run_hidden
    if not output_dir.exists():
        command = [
            python_executable,
            "-X",
            "utf8",
            "-B",
            str(runner),
            "--queue",
            str(queue),
            "--selection-audit",
            str(audit),
            "--labels",
            str(labels),
            "--preparation-receipt",
            str(preparation_receipt),
            "--source-inventory",
            str(source_inventory),
            "--catalog-integrity-audit",
            str(catalog_integrity_audit),
            "--component-report",
            str(component_report),
            "--catalog-database",
            str(catalog_database),
            "--output-dir",
            str(output_dir),
            "--limit",
            str(limit),
        ]
        for seed in control_seeds:
            command.extend(("--control-seed", str(seed)))
        result = command_runner(command)
        (state_dir / "E92_RUNNER_STDOUT.log").write_text(result.stdout, encoding="utf-8")
        (state_dir / "E92_RUNNER_STDERR.log").write_text(result.stderr, encoding="utf-8")
        if result.returncode != 0:
            status = {
                **base,
                "status": "E92_RUNNER_FAILED",
                "labels": "PRESENT_NOT_REPORTED",
                "returncode": result.returncode,
            }
            atomic_json(status_path, status)
            raise RuntimeError(f"E92 runner failed with {result.returncode}")

    if not output_dir.is_dir():
        raise RuntimeError("E92 runner returned without a result bundle")
    if not verification_path.exists():
        pending_verification = state_dir / ".E92_VERIFICATION.pending.json"
        if pending_verification.exists():
            raise FileExistsError(f"pending verification requires audit: {pending_verification}")
        verify_command = [
            python_executable,
            "-X",
            "utf8",
            "-B",
            str(verifier),
            "--bundle",
            str(output_dir),
            "--output",
            str(pending_verification),
        ]
        for seed in control_seeds:
            verify_command.extend(("--control-seed", str(seed)))
        verification_result = command_runner(verify_command)
        (state_dir / "E92_VERIFIER_STDOUT.log").write_text(verification_result.stdout, encoding="utf-8")
        (state_dir / "E92_VERIFIER_STDERR.log").write_text(verification_result.stderr, encoding="utf-8")
        if verification_result.returncode != 0:
            raise RuntimeError(f"independent E92 verifier failed with {verification_result.returncode}")
        _verified_result(pending_verification)
        os.replace(pending_verification, verification_path)

    verification = _verified_result(verification_path)
    status = {
        **base,
        "status": "E92_RESULT_INDEPENDENTLY_VERIFIED",
        "labels": "OPENED_BY_PINNED_E92_RUNNER",
        "scoring": "COMPLETED_BY_PINNED_E92_RUNNER",
        "query_count": int(verification["query_count"]),
        "result_dir": str(output_dir),
        "result_receipt_sha256": sha256_file(output_dir / "RUN_RECEIPT.json"),
        "verification_file_sha256": sha256_file(verification_path),
        "component_report_file_sha256": sha256_file(component_report),
        "component_split_sha256": component_payload["component_split_sha256"],
        "training_intake": "NOT_AUTHORIZED",
        "serving": "NOT_AUTHORIZED",
        "merge": "NOT_AUTHORIZED",
        "promotion": "NOT_AUTHORIZED",
    }
    atomic_json(status_path, status)
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collector-status", required=True, type=Path)
    parser.add_argument("--preparer-status", required=True, type=Path)
    parser.add_argument("--selection-status", required=True, type=Path)
    parser.add_argument("--component-status", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--catalog-database", required=True, type=Path)
    parser.add_argument("--catalog-database-sha256", required=True)
    parser.add_argument("--catalog-integrity-audit", required=True, type=Path)
    parser.add_argument("--catalog-integrity-audit-sha256", required=True)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--runner-sha256", required=True)
    parser.add_argument("--verifier", required=True, type=Path)
    parser.add_argument("--verifier-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--control-seed", type=int, action="append", default=[])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.limit < 1 or args.poll_seconds < 5:
        parser.error("limit must be positive and poll-seconds at least 5")
    kwargs = {
        "collector_status_path": args.collector_status,
        "preparer_status_path": args.preparer_status,
        "selection_status_path": args.selection_status,
        "component_status_path": args.component_status,
        "labels_path": args.labels,
        "catalog_database": args.catalog_database,
        "catalog_database_sha256": args.catalog_database_sha256,
        "catalog_integrity_audit": args.catalog_integrity_audit,
        "catalog_integrity_audit_sha256": args.catalog_integrity_audit_sha256,
        "runner": args.runner,
        "runner_sha256": args.runner_sha256,
        "verifier": args.verifier,
        "verifier_sha256": args.verifier_sha256,
        "output_dir": args.output_dir,
        "state_dir": args.state_dir,
        "control_seeds": tuple(args.control_seed or (11, 29, 47)),
        "limit": args.limit,
        "python_executable": sys.executable,
    }
    while True:
        status = run_cycle(**kwargs)
        print(json.dumps(status, sort_keys=True), flush=True)
        if args.once or status["status"] == "E92_RESULT_INDEPENDENTLY_VERIFIED":
            return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
