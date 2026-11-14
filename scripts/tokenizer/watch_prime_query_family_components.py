#!/usr/bin/env python3
"""Wait for reviewed prime-token inputs, then seal the pinned component audit once."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable

SCHEMA = "scbe.prime-token-query-session-family-component-watcher.v1"
PREPARER_SCHEMA = "clay.prime-token-preparer-watcher.v1"
SELECTION_SCHEMA = "clay.prime-token-selection-audit-watcher.v1"
REPORT_SCHEMA = "scbe.prime-token-query-session-family-components.v1"
PREPARER_READY = {"PACKET_READY_NO_SCORING", "PACKET_ALREADY_READY_NO_SCORING"}
SELECTION_READY = {"AUDIT_VERIFIED_NO_SCORING", "AUDIT_ALREADY_VERIFIED_NO_SCORING"}
REPORT_VERIFIED = "VERIFIED_QUERY_SESSION_FAMILY_COMPONENT_SPLIT"
REPORT_UNDERPOWERED = "QUERY_SESSION_FAMILY_SPLIT_UNDERPOWERED"
REPORT_INVALID = "INVALID_QUERY_SESSION_FAMILY_SPLIT"
NOT_AUTHORIZED = "NOT_AUTHORIZED"
AUTHORITY = {
    "scoring": NOT_AUTHORIZED,
    "training_intake": NOT_AUTHORIZED,
    "execution": "NONE",
    "merge": NOT_AUTHORIZED,
    "promotion": NOT_AUTHORIZED,
    "partial_unfreeze": "NONE",
}
TERMINAL_STATUS_BY_REPORT = {
    REPORT_VERIFIED: "QUERY_SESSION_FAMILY_COMPONENT_GATE_VERIFIED",
    REPORT_UNDERPOWERED: "QUERY_SESSION_FAMILY_COMPONENT_GATE_UNDERPOWERED",
    REPORT_INVALID: "QUERY_SESSION_FAMILY_COMPONENT_GATE_INVALID_NEEDS_REVIEW",
}
RETURN_CODE_BY_REPORT = {REPORT_VERIFIED: 0, REPORT_INVALID: 1, REPORT_UNDERPOWERED: 2}
HEX64 = frozenset("0123456789abcdef")

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def require_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected.strip().casefold():
        raise RuntimeError(f"{label} hash mismatch: {actual}")


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


def _validate_settings(
    *,
    fold_names: Sequence[str],
    minimum_accepted_queries: int,
    minimum_sessions: int,
    minimum_families: int,
    maximum_component_share: float,
) -> tuple[str, ...]:
    folds = tuple(str(value).strip() for value in fold_names)
    if len(folds) < 2 or any(not value for value in folds) or len(set(folds)) != len(folds):
        raise ValueError("fold names must contain at least two unique nonempty values")
    if min(minimum_accepted_queries, minimum_sessions, minimum_families) < 1:
        raise ValueError("component minimums must be positive")
    if not 0.0 < maximum_component_share <= 1.0:
        raise ValueError("maximum component share must be in (0, 1]")
    return folds


def _base(
    preparer: Mapping[str, Any],
    selection: Mapping[str, Any],
    *,
    fold_names: Sequence[str],
    minimum_accepted_queries: int,
    minimum_sessions: int,
    minimum_families: int,
    maximum_component_share: float,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "updated_at_utc": utc_now(),
        "preparer_status": str(preparer.get("status") or "UNKNOWN"),
        "selection_audit_status": str(selection.get("status") or "UNKNOWN"),
        "candidate_count": int(preparer.get("candidate_count", 0)),
        "labels": "NOT_OPENED",
        "fold_names": list(fold_names),
        "thresholds": {
            "minimum_accepted_queries": minimum_accepted_queries,
            "minimum_query_sessions": minimum_sessions,
            "minimum_manifest_bound_families": minimum_families,
            "maximum_component_share": maximum_component_share,
        },
        "authority": dict(AUTHORITY),
        **AUTHORITY,
        "serving": NOT_AUTHORIZED,
    }


def _forbidden_report_keys(value: Any, *, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}"
            if str(key) in {"query", "session_id"}:
                found.append(child)
            found.extend(_forbidden_report_keys(item, path=child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_forbidden_report_keys(item, path=f"{path}[{index}]"))
    return found


def _is_hex64(value: Any) -> bool:
    text = str(value or "").casefold()
    return len(text) == 64 and all(char in HEX64 for char in text)


def _verified_report(
    path: Path,
    *,
    review_queue: Path,
    review_labels: Path,
    source_inventory: Path,
    source_family_audit: Path,
    fold_names: Sequence[str],
    minimum_accepted_queries: int,
    minimum_sessions: int,
    minimum_families: int,
    maximum_component_share: float,
) -> dict[str, Any]:
    report = read_object(path)
    status = str(report.get("status") or "")
    if report.get("schema") != REPORT_SCHEMA or status not in TERMINAL_STATUS_BY_REPORT:
        raise RuntimeError("component report has an unsupported schema or status")
    error_count = int(report.get("error_count", -1))
    if status == REPORT_INVALID:
        if error_count < 1:
            raise RuntimeError("invalid component report has no recorded errors")
    elif error_count != 0:
        raise RuntimeError("component report did not close without errors")

    inputs = report.get("inputs") if isinstance(report.get("inputs"), Mapping) else {}
    expected_hashes = {
        "review_queue_sha256": sha256_file(review_queue),
        "review_labels_sha256": sha256_file(review_labels),
        "source_inventory_sha256": sha256_file(source_inventory),
        "source_family_audit_sha256": sha256_file(source_family_audit),
    }
    for field, expected in expected_hashes.items():
        if str(inputs.get(field) or "").casefold() != expected:
            raise RuntimeError(f"component report input hash mismatch: {field}")

    authority = report.get("authority") if isinstance(report.get("authority"), Mapping) else {}
    if dict(authority) != AUTHORITY:
        raise RuntimeError("component report authority differs from the fail-closed contract")
    if _forbidden_report_keys(report):
        raise RuntimeError("component report contains raw query or session fields")

    thresholds = report.get("thresholds") if isinstance(report.get("thresholds"), Mapping) else {}
    expected_thresholds = {
        "minimum_accepted_queries": minimum_accepted_queries,
        "minimum_query_sessions": minimum_sessions,
        "minimum_manifest_bound_families": minimum_families,
        "minimum_indivisible_components": len(fold_names),
        "maximum_component_share": maximum_component_share,
    }
    if dict(thresholds) != expected_thresholds or tuple(report.get("fold_names") or ()) != tuple(fold_names):
        raise RuntimeError("component report thresholds or neutral folds differ from the pinned contract")

    gates = report.get("gates") if isinstance(report.get("gates"), Mapping) else {}
    all_gates = bool(gates) and all(value is True for value in gates.values())
    if status == REPORT_VERIFIED and not all_gates:
        raise RuntimeError("verified component report has a failed gate")
    if status == REPORT_UNDERPOWERED and all_gates:
        raise RuntimeError("underpowered component report has no failed gate")

    split_payload = {
        "fold_names": report.get("fold_names"),
        "components": report.get("components"),
        "folds": report.get("folds"),
    }
    if (
        not _is_hex64(report.get("component_split_sha256"))
        or canonical_sha256(split_payload) != str(report["component_split_sha256"]).casefold()
    ):
        raise RuntimeError("component split digest does not replay")
    declared_report_hash = str(report.get("report_sha256") or "").casefold()
    report_without_hash = dict(report)
    report_without_hash.pop("report_sha256", None)
    if not _is_hex64(declared_report_hash) or canonical_sha256(report_without_hash) != declared_report_hash:
        raise RuntimeError("component report digest does not replay")
    return report


def run_cycle(
    *,
    preparer_status_path: Path,
    selection_status_path: Path,
    labels_path: Path,
    source_family_audit: Path,
    source_family_audit_sha256: str,
    auditor: Path,
    auditor_sha256: str,
    state_dir: Path,
    python_executable: str,
    fold_names: Sequence[str] = ("fold-0", "fold-1", "fold-2"),
    minimum_accepted_queries: int = 30,
    minimum_sessions: int = 3,
    minimum_families: int = 2,
    maximum_component_share: float = 0.8,
    run_command: Runner | None = None,
) -> dict[str, Any]:
    folds = _validate_settings(
        fold_names=fold_names,
        minimum_accepted_queries=minimum_accepted_queries,
        minimum_sessions=minimum_sessions,
        minimum_families=minimum_families,
        maximum_component_share=maximum_component_share,
    )
    state_dir.mkdir(parents=True, exist_ok=True)
    status_path = state_dir / "QUERY_SESSION_FAMILY_COMPONENT_WATCHER_STATUS.json"
    preparer = read_object(preparer_status_path.resolve(strict=True))
    selection = read_object(selection_status_path.resolve(strict=True))
    if preparer.get("schema") != PREPARER_SCHEMA:
        raise ValueError("unexpected preparer status schema")
    if selection.get("schema") != SELECTION_SCHEMA:
        raise ValueError("unexpected selection-audit status schema")
    base = _base(
        preparer,
        selection,
        fold_names=folds,
        minimum_accepted_queries=minimum_accepted_queries,
        minimum_sessions=minimum_sessions,
        minimum_families=minimum_families,
        maximum_component_share=maximum_component_share,
    )

    if preparer.get("status") not in PREPARER_READY:
        status = {**base, "status": "WAITING_FOR_PREPARATION_PACKET"}
        atomic_json(status_path, status)
        return status
    if selection.get("status") not in SELECTION_READY:
        status = {**base, "status": "WAITING_FOR_EXACT_SELECTION_AUDIT"}
        atomic_json(status_path, status)
        return status

    packet_dir = Path(str(preparer.get("output_dir") or "")).resolve(strict=True)
    review_queue = Path(str(preparer.get("queue") or "")).resolve(strict=True)
    source_inventory = (packet_dir / "CATALOG_SOURCE_SUFFIXES.json").resolve(strict=True)
    if source_inventory.parent != packet_dir:
        raise RuntimeError("source inventory escaped the prepared packet")
    require_hash(review_queue, str(preparer.get("queue_file_sha256") or ""), "review queue")
    require_hash(
        source_inventory,
        str(preparer.get("source_inventory_file_sha256") or ""),
        "source inventory",
    )
    source_family_audit = source_family_audit.resolve(strict=True)
    auditor = auditor.resolve(strict=True)
    require_hash(source_family_audit, source_family_audit_sha256, "source-family audit")
    require_hash(auditor, auditor_sha256, "component auditor")

    if not labels_path.is_file():
        status = {
            **base,
            "status": "WAITING_FOR_INDEPENDENT_LABELS",
            "labels": "NOT_PRESENT",
            "review_queue_sha256": sha256_file(review_queue),
            "source_inventory_sha256": sha256_file(source_inventory),
        }
        atomic_json(status_path, status)
        return status

    labels = labels_path.resolve(strict=True)
    report_path = state_dir / "QUERY_SESSION_FAMILY_COMPONENTS.json"
    pending_report = state_dir / ".QUERY_SESSION_FAMILY_COMPONENTS.pending.json"
    if pending_report.exists():
        status = {
            **base,
            "status": "PENDING_COMPONENT_REPORT_REQUIRES_AUDIT",
            "labels": "PRESENT_NOT_OPENED_WITH_PENDING_REPORT",
        }
        atomic_json(status_path, status)
        return status

    command_runner = run_command or run_hidden
    if not report_path.exists():
        command = [
            python_executable,
            "-X",
            "utf8",
            "-B",
            str(auditor),
            "--review-queue",
            str(review_queue),
            "--review-labels",
            str(labels),
            "--source-inventory",
            str(source_inventory),
            "--source-family-audit",
            str(source_family_audit),
            "--output",
            str(pending_report),
            "--minimum-accepted-queries",
            str(minimum_accepted_queries),
            "--minimum-sessions",
            str(minimum_sessions),
            "--minimum-families",
            str(minimum_families),
            "--maximum-component-share",
            str(maximum_component_share),
        ]
        for fold in folds:
            command.extend(("--fold-name", fold))
        result = command_runner(command)
        (state_dir / "COMPONENT_AUDITOR_STDOUT.log").write_text(result.stdout, encoding="utf-8")
        (state_dir / "COMPONENT_AUDITOR_STDERR.log").write_text(result.stderr, encoding="utf-8")
        if result.returncode not in set(RETURN_CODE_BY_REPORT.values()):
            raise RuntimeError(f"component auditor failed with {result.returncode}")
        pending = _verified_report(
            pending_report,
            review_queue=review_queue,
            review_labels=labels,
            source_inventory=source_inventory,
            source_family_audit=source_family_audit,
            fold_names=folds,
            minimum_accepted_queries=minimum_accepted_queries,
            minimum_sessions=minimum_sessions,
            minimum_families=minimum_families,
            maximum_component_share=maximum_component_share,
        )
        if result.returncode != RETURN_CODE_BY_REPORT[pending["status"]]:
            raise RuntimeError("component auditor return code disagrees with its report")
        os.replace(pending_report, report_path)

    report = _verified_report(
        report_path,
        review_queue=review_queue,
        review_labels=labels,
        source_inventory=source_inventory,
        source_family_audit=source_family_audit,
        fold_names=folds,
        minimum_accepted_queries=minimum_accepted_queries,
        minimum_sessions=minimum_sessions,
        minimum_families=minimum_families,
        maximum_component_share=maximum_component_share,
    )
    status = {
        **base,
        "status": TERMINAL_STATUS_BY_REPORT[report["status"]],
        "labels": "OPENED_BY_PINNED_COMPONENT_AUDITOR",
        "gate_result": report["status"],
        "gate_report": str(report_path),
        "gate_report_sha256": sha256_file(report_path),
        "component_split_sha256": report["component_split_sha256"],
        "observed": report.get("observed", {}),
        "gates": report.get("gates", {}),
    }
    atomic_json(status_path, status)
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparer-status", required=True, type=Path)
    parser.add_argument("--selection-status", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--source-family-audit", required=True, type=Path)
    parser.add_argument("--source-family-audit-sha256", required=True)
    parser.add_argument("--auditor", required=True, type=Path)
    parser.add_argument("--auditor-sha256", required=True)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--fold-name", action="append", default=[])
    parser.add_argument("--minimum-accepted-queries", type=int, default=30)
    parser.add_argument("--minimum-sessions", type=int, default=3)
    parser.add_argument("--minimum-families", type=int, default=2)
    parser.add_argument("--maximum-component-share", type=float, default=0.8)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds < 5:
        parser.error("poll-seconds must be at least 5")
    kwargs = {
        "preparer_status_path": args.preparer_status,
        "selection_status_path": args.selection_status,
        "labels_path": args.labels,
        "source_family_audit": args.source_family_audit,
        "source_family_audit_sha256": args.source_family_audit_sha256,
        "auditor": args.auditor,
        "auditor_sha256": args.auditor_sha256,
        "state_dir": args.state_dir,
        "python_executable": sys.executable,
        "fold_names": tuple(args.fold_name or ("fold-0", "fold-1", "fold-2")),
        "minimum_accepted_queries": args.minimum_accepted_queries,
        "minimum_sessions": args.minimum_sessions,
        "minimum_families": args.minimum_families,
        "maximum_component_share": args.maximum_component_share,
    }
    terminal = set(TERMINAL_STATUS_BY_REPORT.values())
    while True:
        status = run_cycle(**kwargs)
        print(json.dumps(status, sort_keys=True), flush=True)
        if args.once or status["status"] in terminal:
            return 1 if status["status"].endswith("INVALID_NEEDS_REVIEW") else 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
