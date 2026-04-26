#!/usr/bin/env python3
"""Benchmark specialist training buckets before adapter promotion.

This is a lightweight, deterministic benchmark for extracted/regularized SFT
records. It scores whether each bucket has train/eval coverage, valid message
schema, provenance, split separation, and enough records to justify a training
smoke run.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONSOLIDATION_DIR = REPO_ROOT / "artifacts" / "ai_training_consolidation" / "latest"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "benchmark" / "specialist_bucket_readiness"
PURPOSES = ("operator_agent_bus", "governance_security", "research_bridge")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    malformed = 0
    if not path.exists():
        return rows, 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if isinstance(item, dict):
                rows.append(item)
            else:
                malformed += 1
    return rows, malformed


def valid_messages(row: dict[str, Any]) -> bool:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return False
    for message in messages:
        if not isinstance(message, dict):
            return False
        if not str(message.get("role", "")).strip():
            return False
        if not str(message.get("content", "")).strip():
            return False
    return True


def has_provenance(row: dict[str, Any]) -> bool:
    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        return False
    return bool(metadata.get("source_path")) and bool(metadata.get("dedupe_key"))


def benchmark_bucket(purpose: str, manifest: dict[str, Any]) -> dict[str, Any]:
    outputs = manifest.get("outputs") or {}
    train_path = Path(str(outputs.get("train", "")))
    eval_path = Path(str(outputs.get("eval", "")))
    train_rows, train_malformed = read_jsonl(train_path)
    eval_rows, eval_malformed = read_jsonl(eval_path)
    all_rows = train_rows + eval_rows

    valid_count = sum(1 for row in all_rows if valid_messages(row))
    provenance_count = sum(1 for row in all_rows if has_provenance(row))
    dedupe_keys = {
        str((row.get("metadata") or {}).get("dedupe_key", ""))
        for row in all_rows
        if isinstance(row.get("metadata"), dict)
    }
    duplicate_count = max(0, len(all_rows) - len([key for key in dedupe_keys if key]))
    train_eval_overlap = {
        str((row.get("metadata") or {}).get("dedupe_key", ""))
        for row in train_rows
        if isinstance(row.get("metadata"), dict)
    } & {
        str((row.get("metadata") or {}).get("dedupe_key", ""))
        for row in eval_rows
        if isinstance(row.get("metadata"), dict)
    }

    total = max(len(all_rows), 1)
    schema_score = valid_count / total
    provenance_score = provenance_count / total
    coverage_score = min(1.0, len(train_rows) / 10.0) * 0.6 + min(1.0, len(eval_rows) / 3.0) * 0.4
    split_score = 0.0 if train_eval_overlap else 1.0
    malformed_penalty = min(1.0, (train_malformed + eval_malformed) / total)
    duplicate_penalty = min(1.0, duplicate_count / total)
    readiness_score = max(
        0.0,
        (0.30 * schema_score)
        + (0.25 * provenance_score)
        + (0.25 * coverage_score)
        + (0.20 * split_score)
        - (0.25 * malformed_penalty)
        - (0.15 * duplicate_penalty),
    )

    decision = "PASS" if readiness_score >= 0.85 and len(train_rows) > 0 and len(eval_rows) > 0 else "HOLD"
    return {
        "schema_version": "scbe_specialist_bucket_readiness_report_v1",
        "generated_at_utc": utc_now(),
        "purpose": purpose,
        "readiness_score": round(readiness_score, 6),
        "score": round(readiness_score, 6),
        "success_rate": 1.0 if decision == "PASS" else 0.0,
        "decision": decision,
        "train_records": len(train_rows),
        "eval_records": len(eval_rows),
        "valid_message_records": valid_count,
        "provenance_records": provenance_count,
        "malformed_records": train_malformed + eval_malformed,
        "duplicate_count": duplicate_count,
        "train_eval_overlap_count": len([key for key in train_eval_overlap if key]),
        "inputs": {
            "train": str(train_path),
            "eval": str(eval_path),
            "manifest": str(Path(str(manifest.get("outputs", {}).get("manifest", "")))),
        },
    }


def run(consolidation_dir: Path, output_dir: Path, purposes: tuple[str, ...] = PURPOSES) -> dict[str, Any]:
    plan = load_json(consolidation_dir / "consolidation_plan.json")
    specialists = {item["purpose"]: item for item in plan.get("specialists", []) if isinstance(item, dict)}
    output_dir.mkdir(parents=True, exist_ok=True)
    reports: dict[str, Any] = {}
    for purpose in purposes:
        specialist = specialists.get(purpose)
        if not specialist:
            continue
        manifest_path = Path(str(specialist["regularized_train"])).with_name(f"{purpose}_manifest.json")
        manifest = load_json(manifest_path)
        report = benchmark_bucket(purpose, manifest)
        report_path = output_dir / f"{purpose}_readiness.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        reports[purpose] = {"path": str(report_path), **report}

    summary = {
        "schema_version": "scbe_specialist_bucket_readiness_summary_v1",
        "generated_at_utc": utc_now(),
        "reports": reports,
        "passed": [purpose for purpose, report in reports.items() if report["decision"] == "PASS"],
        "held": [purpose for purpose, report in reports.items() if report["decision"] != "PASS"],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark specialist bucket readiness")
    parser.add_argument("--consolidation-dir", default=str(DEFAULT_CONSOLIDATION_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    print(json.dumps(run(Path(args.consolidation_dir), Path(args.output_dir)), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
