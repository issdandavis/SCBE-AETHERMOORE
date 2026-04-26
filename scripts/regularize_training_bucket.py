#!/usr/bin/env python3
"""Build a purpose-scoped regularized training bucket.

This consumes the inventory from ``training_dataset_inventory.py`` and emits
deduplicated train/eval JSONL for one purpose bucket.  It deliberately refuses
to consume quarantined/LFS/raw files so a model run uses only records that have
an explicit schema adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = REPO_ROOT / "artifacts" / "training_inventory" / "latest" / "inventory.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "training_regularized" / "latest"
READY_STATUSES = {"ready_messages", "ready_prompt_response"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _record_text(messages: list[dict[str, str]]) -> str:
    return "\n".join(f"{msg.get('role', '')}: {msg.get('content', '')}" for msg in messages)


def _dedupe_key(messages: list[dict[str, str]]) -> str:
    text = _record_text(messages)
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def normalize_record(raw: dict[str, Any], source_row: dict[str, Any], index: int) -> dict[str, Any] | None:
    messages: list[dict[str, str]]
    if isinstance(raw.get("messages"), list):
        messages = []
        for msg in raw["messages"]:
            if not isinstance(msg, dict):
                return None
            role = str(msg.get("role", "")).strip()
            content = str(msg.get("content", "")).strip()
            if not role or not content:
                return None
            messages.append({"role": role, "content": content})
    elif raw.get("instruction") is not None and raw.get("response") is not None:
        instruction = str(raw.get("instruction", "")).strip()
        response = str(raw.get("response", "")).strip()
        if not instruction or not response:
            return None
        messages = [{"role": "user", "content": instruction}, {"role": "assistant", "content": response}]
    else:
        return None

    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    metadata = dict(metadata)
    metadata.update(
        {
            "source_path": source_row["path"],
            "source_sha256": source_row.get("sha256"),
            "source_record_index": index,
            "dataset_family": source_row.get("purpose"),
            "purpose": source_row.get("purpose"),
            "split": source_row.get("split_hint"),
            "regularization_status": source_row.get("regularization_status"),
        }
    )
    key = _dedupe_key(messages)
    metadata["dedupe_key"] = key
    return {"messages": messages, "metadata": metadata}


def _read_jsonl(path: Path, source_row: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    skipped = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, line in enumerate(handle):
            raw_line = line.strip()
            if not raw_line:
                continue
            try:
                raw = json.loads(raw_line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            if not isinstance(raw, dict):
                skipped += 1
                continue
            normalized = normalize_record(raw, source_row, index)
            if normalized is None:
                skipped += 1
                continue
            rows.append(normalized)
    return rows, skipped


def load_inventory(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "local_datasets" not in payload:
        raise ValueError(f"inventory missing local_datasets: {path}")
    return payload


def build_bucket(inventory_path: Path, purpose: str, output_root: Path) -> dict[str, Any]:
    inventory = load_inventory(inventory_path)
    source_rows = [
        row
        for row in inventory["local_datasets"]
        if row.get("purpose") == purpose
        and row.get("extension") == ".jsonl"
        and row.get("regularization_status") in READY_STATUSES
    ]

    train_records: list[dict[str, Any]] = []
    eval_records: list[dict[str, Any]] = []
    seen: set[str] = set()
    skipped_records = 0
    duplicate_records = 0
    source_files: list[str] = []

    for source_row in source_rows:
        path = _repo_path(source_row["path"])
        rows, skipped = _read_jsonl(path, source_row)
        skipped_records += skipped
        source_files.append(source_row["path"])
        target = eval_records if source_row.get("split_hint") == "eval" else train_records
        for row in rows:
            key = row["metadata"]["dedupe_key"]
            if key in seen:
                duplicate_records += 1
                continue
            seen.add(key)
            target.append(row)

    output_dir = output_root / purpose
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / f"{purpose}_train.regularized.jsonl"
    eval_path = output_dir / f"{purpose}_eval.regularized.jsonl"
    manifest_path = output_dir / f"{purpose}_manifest.json"

    with train_path.open("w", encoding="utf-8") as handle:
        for row in train_records:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
    with eval_path.open("w", encoding="utf-8") as handle:
        for row in eval_records:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")

    manifest = {
        "schema_version": "scbe_regularized_bucket_manifest_v1",
        "generated_at_utc": _utc_now(),
        "purpose": purpose,
        "inventory_path": str(inventory_path),
        "source_file_count": len(source_files),
        "source_files": source_files,
        "train_records": len(train_records),
        "eval_records": len(eval_records),
        "duplicates_removed": duplicate_records,
        "skipped_records": skipped_records,
        "outputs": {
            "train": str(train_path),
            "eval": str(eval_path),
            "manifest": str(manifest_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Regularize one SCBE training purpose bucket")
    parser.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    parser.add_argument("--purpose", default="coding_model")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args()

    manifest = build_bucket(Path(args.inventory), args.purpose, Path(args.output_root))
    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
