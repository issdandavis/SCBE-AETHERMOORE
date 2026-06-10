#!/usr/bin/env python3
"""Build GeoSeal/STISA receipts for functional coding benchmark reports.

This makes model outputs inspectable through the same tokenizer, STISA,
transport-hash, and route surfaces used by GeoSeal. It does not change benchmark
scores; it adds a replayable evidence layer for improvement and training.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = REPO_ROOT / "artifacts" / "coding_agent_benchmarks" / "latest" / "report.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "coding_agent_benchmarks" / "latest" / "geoseal_receipts.json"


def _run_code_packet(source: str, source_name: str, language: str, timeout: int) -> tuple[dict[str, Any] | None, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".ts", encoding="utf-8", delete=False) as handle:
        handle.write(source)
        temp_path = Path(handle.name)
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.geoseal_cli",
                "code-packet",
                "--source-file",
                str(temp_path),
                "--source-name",
                source_name,
                "--language",
                language,
            ],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    finally:
        temp_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        return None, proc.stderr.strip() or proc.stdout.strip()
    try:
        return json.loads(proc.stdout), ""
    except json.JSONDecodeError as exc:
        return None, f"invalid GeoSeal JSON: {exc}: {proc.stdout[:400]}"


def _receipt_from_packet(row: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    stisa = packet.get("stisa") or {}
    semantic = packet.get("semantic_expression") or {}
    route_ir = packet.get("route_ir") or {}
    transport = packet.get("transport") or {}
    return {
        "task_id": row.get("task_id"),
        "passed": bool(row.get("passed")),
        "initial_passed": bool(row.get("initial_passed", row.get("passed"))),
        "repaired": bool(row.get("repaired")),
        "source_sha256": transport.get("source_sha256"),
        "token_sha256": transport.get("token_sha256"),
        "transport_tongue": transport.get("tongue"),
        "token_count": (packet.get("tokenizer") or {}).get("token_count"),
        "lexical_token_count": len(packet.get("lexical_tokens") or []),
        "stisa_version": stisa.get("version"),
        "stisa_row_count": len(stisa.get("token_rows") or []),
        "stisa_field_count": len(stisa.get("field_definitions") or []),
        "atomic_state_count": len(packet.get("atomic_states") or []),
        "semantic_label": semantic.get("label"),
        "semantic_quarks": semantic.get("quarks") or [],
        "route_signature": ((route_ir.get("route") or {}).get("signature")),
        "plan_sha256": ((route_ir.get("hashes") or {}).get("plan_sha256")),
        "first_failure": _first_failure(row),
    }


def _first_failure(row: dict[str, Any]) -> dict[str, Any] | None:
    for check in row.get("checks") or []:
        if not check.get("passed"):
            return {
                "index": check.get("index"),
                "receipt_status": check.get("receipt_status"),
                "error": check.get("error"),
                "expected_result": check.get("expected_result"),
                "actual_result": check.get("actual_result"),
                "expected_state": check.get("expected_state"),
                "actual_state": check.get("actual_state"),
            }
    error = row.get("error")
    return {"error": error} if error else None


def build_receipts(report: dict[str, Any], timeout: int) -> dict[str, Any]:
    results = []
    for result in report.get("results") or []:
        task_receipts = []
        for row in result.get("tasks") or []:
            source = str(row.get("final_code") or row.get("extracted_code") or "")
            if not source.strip():
                task_receipts.append(
                    {
                        "task_id": row.get("task_id"),
                        "passed": False,
                        "geoseal_ok": False,
                        "error": "empty source",
                    }
                )
                continue
            packet, error = _run_code_packet(
                source,
                source_name=f"{result.get('adapter', 'model')}::{row.get('task_id', 'task')}.ts",
                language="typescript",
                timeout=timeout,
            )
            if packet is None:
                task_receipts.append(
                    {
                        "task_id": row.get("task_id"),
                        "passed": bool(row.get("passed")),
                        "geoseal_ok": False,
                        "error": error,
                        "first_failure": _first_failure(row),
                    }
                )
            else:
                task_receipts.append({"geoseal_ok": True, **_receipt_from_packet(row, packet)})
        results.append(
            {
                "adapter": result.get("adapter"),
                "summary": result.get("summary") or {},
                "receipt_summary": {
                    "tasks": len(task_receipts),
                    "geoseal_ok": sum(1 for item in task_receipts if item.get("geoseal_ok")),
                    "passed": sum(1 for item in task_receipts if item.get("passed")),
                    "failed_with_receipts": sum(
                        1 for item in task_receipts if item.get("geoseal_ok") and not item.get("passed")
                    ),
                },
                "tasks": task_receipts,
            }
        )
    return {
        "schema": "scbe_geoseal_functional_receipts_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report_benchmark": report.get("benchmark"),
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    payload = build_receipts(report, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote GeoSeal receipts: {args.output}")
    for result in payload["results"]:
        summary = result["receipt_summary"]
        print(
            f"{result['adapter']}: geoseal_ok={summary['geoseal_ok']}/{summary['tasks']} "
            f"passed={summary['passed']} failed_with_receipts={summary['failed_with_receipts']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
