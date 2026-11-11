#!/usr/bin/env python3
"""Wait for reviewed E92 inputs, then run the pinned canonical-source-family gate once."""

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

SCHEMA = "scbe.e92-source-family-gate-watcher.v1"
PREPARER_SCHEMA = "clay.prime-token-preparer-watcher.v1"
SELECTION_SCHEMA = "clay.prime-token-selection-audit-watcher.v1"
REPORT_SCHEMA = "clay.e92-source-family-gate.v1"
PREPARER_READY = {"PACKET_READY_NO_SCORING", "PACKET_ALREADY_READY_NO_SCORING"}
SELECTION_READY = {"AUDIT_VERIFIED_NO_SCORING", "AUDIT_ALREADY_VERIFIED_NO_SCORING"}
REPORT_VERIFIED = "VERIFIED_SOURCE_FAMILY_DIVERSITY"
REPORT_UNDERPOWERED = "SOURCE_FAMILY_DIVERSITY_UNDERPOWERED"
NOT_AUTHORIZED = "NOT_AUTHORIZED"

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected.casefold():
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


def _base(preparer: Mapping[str, Any], selection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "updated_at_utc": utc_now(),
        "preparer_status": str(preparer.get("status") or "UNKNOWN"),
        "selection_audit_status": str(selection.get("status") or "UNKNOWN"),
        "candidate_count": int(preparer.get("candidate_count", 0)),
        "labels": "NOT_OPENED",
        "scoring": NOT_AUTHORIZED,
        "training_intake": NOT_AUTHORIZED,
        "serving": NOT_AUTHORIZED,
        "merge": NOT_AUTHORIZED,
        "promotion": NOT_AUTHORIZED,
    }


def _verified_report(
    path: Path,
    *,
    source_family_audit: Path,
    source_inventory: Path,
    labels: Path,
) -> dict[str, Any]:
    report = read_object(path)
    if report.get("schema") != REPORT_SCHEMA or int(report.get("error_count", -1)) != 0:
        raise RuntimeError("source-family report did not close without errors")
    if report.get("status") not in {REPORT_VERIFIED, REPORT_UNDERPOWERED}:
        raise RuntimeError("source-family report has an unsupported terminal status")
    inputs = report.get("inputs") if isinstance(report.get("inputs"), Mapping) else {}
    expected_hashes = {
        "source_family_audit_sha256": sha256_file(source_family_audit),
        "source_inventory_sha256": sha256_file(source_inventory),
        "labels_sha256": sha256_file(labels),
    }
    for field, expected in expected_hashes.items():
        if str(inputs.get(field) or "").casefold() != expected:
            raise RuntimeError(f"source-family report input hash mismatch: {field}")
    authority = report.get("authority") if isinstance(report.get("authority"), Mapping) else {}
    for field in ("scoring", "training_intake", "merge", "promotion"):
        if authority.get(field) != NOT_AUTHORIZED:
            raise RuntimeError(f"source-family report unexpectedly authorizes {field}")
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
    run_command: Runner | None = None,
) -> dict[str, Any]:
    state_dir.mkdir(parents=True, exist_ok=True)
    status_path = state_dir / "SOURCE_FAMILY_GATE_WATCHER_STATUS.json"
    preparer = read_object(preparer_status_path.resolve(strict=True))
    selection = read_object(selection_status_path.resolve(strict=True))
    if preparer.get("schema") != PREPARER_SCHEMA:
        raise ValueError("unexpected preparer status schema")
    if selection.get("schema") != SELECTION_SCHEMA:
        raise ValueError("unexpected selection-audit status schema")
    base = _base(preparer, selection)

    if preparer.get("status") not in PREPARER_READY:
        status = {**base, "status": "WAITING_FOR_PREPARATION_PACKET"}
        atomic_json(status_path, status)
        return status
    if selection.get("status") not in SELECTION_READY:
        status = {**base, "status": "WAITING_FOR_EXACT_SELECTION_AUDIT"}
        atomic_json(status_path, status)
        return status

    packet_dir = Path(str(preparer.get("output_dir") or "")).resolve(strict=True)
    source_inventory = (packet_dir / "CATALOG_SOURCE_SUFFIXES.json").resolve(strict=True)
    require_hash(
        source_inventory,
        str(preparer.get("source_inventory_file_sha256") or ""),
        "source inventory",
    )
    source_family_audit = source_family_audit.resolve(strict=True)
    auditor = auditor.resolve(strict=True)
    require_hash(source_family_audit, source_family_audit_sha256, "source-family audit")
    require_hash(auditor, auditor_sha256, "source-family auditor")

    if not labels_path.is_file():
        status = {
            **base,
            "status": "WAITING_FOR_INDEPENDENT_LABELS",
            "labels": "NOT_PRESENT",
            "source_inventory_sha256": sha256_file(source_inventory),
        }
        atomic_json(status_path, status)
        return status

    labels = labels_path.resolve(strict=True)
    report_path = state_dir / "SOURCE_FAMILY_GATE.json"
    pending_report = state_dir / ".SOURCE_FAMILY_GATE.pending.json"
    if pending_report.exists():
        status = {
            **base,
            "status": "PENDING_GATE_REPORT_REQUIRES_AUDIT",
            "labels": "PRESENT_NOT_REPORTED",
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
            "--source-family-audit",
            str(source_family_audit),
            "--source-inventory",
            str(source_inventory),
            "--labels",
            str(labels),
            "--output",
            str(pending_report),
        ]
        result = command_runner(command)
        (state_dir / "SOURCE_FAMILY_AUDITOR_STDOUT.log").write_text(result.stdout, encoding="utf-8")
        (state_dir / "SOURCE_FAMILY_AUDITOR_STDERR.log").write_text(result.stderr, encoding="utf-8")
        if result.returncode not in {0, 2}:
            raise RuntimeError(f"source-family auditor failed with {result.returncode}")
        _verified_report(
            pending_report,
            source_family_audit=source_family_audit,
            source_inventory=source_inventory,
            labels=labels,
        )
        os.replace(pending_report, report_path)

    report = _verified_report(
        report_path,
        source_family_audit=source_family_audit,
        source_inventory=source_inventory,
        labels=labels,
    )
    passed = report["status"] == REPORT_VERIFIED
    status = {
        **base,
        "status": ("SOURCE_FAMILY_GATE_VERIFIED" if passed else "SOURCE_FAMILY_GATE_UNDERPOWERED"),
        "labels": "OPENED_BY_PINNED_SOURCE_FAMILY_AUDITOR",
        "gate_result": report["status"],
        "gate_report": str(report_path),
        "gate_report_sha256": sha256_file(report_path),
        "observed": report.get("observed", {}),
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
    }
    terminal = {"SOURCE_FAMILY_GATE_VERIFIED", "SOURCE_FAMILY_GATE_UNDERPOWERED"}
    while True:
        status = run_cycle(**kwargs)
        print(json.dumps(status, sort_keys=True), flush=True)
        if args.once or status["status"] in terminal:
            return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
