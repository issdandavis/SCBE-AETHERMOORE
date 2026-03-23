#!/usr/bin/env python3
"""Build a deduplicated SFT staging file from multi-agent offload training rows."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUN_ROOT = REPO_ROOT / "training" / "runs" / "multi_agent_offload"
DEFAULT_OUTPUT = REPO_ROOT / "training" / "sft_records" / "sft_multi_agent_offload.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert per-run multi-agent offload training rows into a merged SFT staging file."
    )
    parser.add_argument(
        "--run-root",
        default=str(DEFAULT_RUN_ROOT),
        help=f"Offload run root (default: {DEFAULT_RUN_ROOT})",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output JSONL path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--min-output-chars",
        type=int,
        default=5,
        help="Skip rows whose assistant output is shorter than this many characters.",
    )
    return parser.parse_args()


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_key(record: dict[str, Any]) -> str:
    meta = record.get("metadata", {})
    source_sha = _safe_str(meta.get("source_sha256"))
    payload = {
        "instruction": record.get("instruction", ""),
        "response": record.get("response", ""),
        "source_sha256": source_sha,
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def transform_row(row: dict[str, Any], run_id: str, source_file: str, min_output_chars: int) -> dict[str, Any] | None:
    instruction = _safe_str(row.get("instruction"))
    response = _safe_str(row.get("output", row.get("response", "")))
    if not instruction or len(response) < min_output_chars:
        return None

    input_payload = row.get("input", {}) if isinstance(row.get("input"), dict) else {}
    metadata = row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {}

    return {
        "instruction": instruction,
        "response": response,
        "source": "multi_agent_offload",
        "metadata": {
            "origin": "multi_agent_offload",
            "run_id": run_id,
            "source_file": source_file.replace("\\", "/"),
            "source_sha256": _safe_str(metadata.get("source_sha256")),
            "timestamp_utc": _safe_str(metadata.get("timestamp_utc")),
            "relative_path": _safe_str(input_payload.get("relative_path")),
            "assigned_lane": _safe_str(input_payload.get("assigned_lane")),
            "assigned_provider": _safe_str(input_payload.get("assigned_provider")),
            "assigned_model": _safe_str(input_payload.get("assigned_model")),
            "selected_lane": _safe_str(input_payload.get("selected_lane")),
            "size_bytes": int(input_payload.get("size") or 0),
        },
    }


def build_sft_records(run_root: Path, output_path: Path, min_output_chars: int) -> dict[str, Any]:
    run_files = sorted(run_root.glob("*/training_rows.jsonl"))
    raw_rows = 0
    kept_rows = 0
    skipped_short = 0
    duplicates_removed = 0
    seen: set[str] = set()
    records: list[dict[str, Any]] = []

    for training_rows in run_files:
        run_id = training_rows.parent.name
        with training_rows.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                raw_rows += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    skipped_short += 1
                    continue
                record = transform_row(row, run_id, str(training_rows), min_output_chars)
                if record is None:
                    skipped_short += 1
                    continue
                key = _dedupe_key(record)
                if key in seen:
                    duplicates_removed += 1
                    continue
                seen.add(key)
                kept_rows += 1
                records.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    summary = {
        "run_root": str(run_root),
        "output_path": str(output_path),
        "run_files": len(run_files),
        "raw_rows": raw_rows,
        "kept_rows": kept_rows,
        "skipped_short_or_empty": skipped_short,
        "duplicates_removed": duplicates_removed,
        "min_output_chars": min_output_chars,
    }
    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    return summary


def main() -> int:
    args = parse_args()
    summary = build_sft_records(
        run_root=Path(args.run_root).expanduser(),
        output_path=Path(args.output).expanduser(),
        min_output_chars=int(args.min_output_chars),
    )
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
