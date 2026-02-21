#!/usr/bin/env python3
"""Normalize Gumroad automation JSONL logs into an HF-ready training dataset.

Workflow:
1. Read raw events from --source (default: training/aethermoore_ops_training.jsonl)
2. Validate fields and canonicalize event formats
3. Emit a cleaned JSONL dataset file
4. Emit dataset manifest and verification summary

Useful outputs:
- training-data/gumroad-automation/gumroad_automation.jsonl
- training-data/gumroad-automation/manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from huggingface_hub import HfApi, login
except Exception:  # pragma: no cover
    HfApi = None
    login = None


EVENT_LABEL_MAP = {
    "gumroad_match": 0,
    "gumroad_uploaded": 1,
    "gumroad_logged": 2,
    "gumroad_skip": 3,
    "gumroad_error": 4,
    "gumroad_unknown": -1,
}

REQUIRED_FIELDS = {"dataset", "run_id", "run_index", "created_at_utc", "event_type"}


@dataclass
class ValidationState:
    total_lines: int = 0
    valid_events: int = 0
    invalid_lines: int = 0
    missing_fields: int = 0
    unknown_events: int = 0
    errors: list[str] = None  # type: ignore[assignment]
    run_ids: set[str] | None = None  # type: ignore[assignment]
    event_counts: dict[str, int] = None  # type: ignore[assignment]
    product_counts: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.errors = []
        self.run_ids = set()
        self.event_counts = defaultdict(int)
        self.product_counts = defaultdict(int)


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _load_source_records(path: Path, state: ValidationState) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        state.total_lines += 1
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            state.invalid_lines += 1
            state.errors.append(f"line={line_no}: invalid JSON ({exc})")
            continue
        if not isinstance(obj, dict):
            state.invalid_lines += 1
            state.errors.append(f"line={line_no}: non-object payload")
            continue

        missing = [f for f in REQUIRED_FIELDS if f not in obj]
        if missing:
            state.missing_fields += 1
            state.errors.append(f"line={line_no}: missing required fields {missing}")
            continue

        records.append(obj)
        state.valid_events += 1
        state.run_ids.add(str(obj.get("run_id")))
        event_type = str(obj.get("event_type", "gumroad_unknown"))
        state.event_counts[event_type] += 1
        if "product" in obj and obj["product"]:
            state.product_counts[str(obj["product"])] += 1

    return records


def _normalize_event(event_type: str) -> str:
    normalized = str(event_type or "gumroad_unknown").strip().lower()
    if not normalized.startswith("gumroad_"):
        normalized = f"gumroad_{normalized}"
    if normalized in ("gumroad_match", "gumroad_uploaded", "gumroad_logged", "gumroad_skip", "gumroad_error"):
        return normalized
    return "gumroad_unknown"


def _build_example(raw: dict[str, Any], run_index: int) -> dict[str, Any]:
    event_type = _normalize_event(str(raw.get("event_type", "gumroad_unknown")))
    event_time = str(raw.get("created_at_utc", "")).strip() or datetime.now(timezone.utc).isoformat()
    product = raw.get("product") or ""
    image = raw.get("image") or ""
    status = raw.get("status") or ""
    reason = raw.get("reason") or ""
    message = raw.get("message") or ""
    targets = raw.get("targets") or []
    label = EVENT_LABEL_MAP.get(event_type, -1)

    prompt = (
        f"Gumroad automation event. Run {raw.get('run_id')} pass {run_index}. "
        f"Product: {product}. Image: {image}. Status: {status or 'n/a'}. "
        f"Reason: {reason or 'none'}."
    )
    completion = {
        "match": "ACTION_MATCHED",
        "uploaded": "IMAGE_UPLOADED",
        "logged": "IMAGE_UPLOADED_PENDING_VERIFICATION",
        "skip": "NO_IMAGE_MATCH",
        "error": "AUTOMATION_ERROR",
        "unknown": "UNKNOWN_STATE",
    }[event_type.replace("gumroad_", "")]

    uid = _sha1(f'{raw.get("run_id")}-{run_index}-{product}-{image}-{event_time}-{event_type}')

    return {
        "id": uid,
        "source": "gumroad_automation",
        "created_at_utc": event_time,
        "run_id": str(raw.get("run_id")),
        "run_index": int(run_index),
        "targets": targets,
        "dataset": "gumroad_automation",
        "event_type": event_type,
        "event_label_id": label,
        "event_label_name": event_type.replace("gumroad_", ""),
        "product": product,
        "image": image,
        "status": status,
        "reason": reason,
        "message": message,
        "input_text": prompt,
        "target_text": completion,
        "training_prompt": prompt,
        "expected_action": completion,
    }


def _emit_dataset(records: list[dict[str, Any]], out_path: Path, state: ValidationState) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8") as f:
        for event in records:
            event_type = _normalize_event(str(event.get("event_type", "gumroad_unknown")))
            if event_type not in EVENT_LABEL_MAP:
                state.unknown_events += 1
            example = _build_example(event, int(event.get("run_index", 0)))
            f.write(json.dumps(example) + "\n")
            count += 1
    return count


def _write_manifest(manifest_path: Path, records: list[dict[str, Any]], output_path: Path, state: ValidationState, dataset_info: str) -> None:
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(state.source_path),
        "output_file": str(output_path),
        "dataset": dataset_info,
        "total_source_records": len(records),
        "summary": {
            "valid_events": state.valid_events,
            "invalid_lines": state.invalid_lines,
            "missing_fields": state.missing_fields,
            "unknown_event_types": state.unknown_events,
            "unique_runs": len(state.run_ids or []),
            "run_ids": sorted(state.run_ids or []),
            "event_counts": dict(state.event_counts or {}),
            "product_counts": dict(state.product_counts or {}),
        },
        "checks": {
            "passes": state.errors == [] and state.invalid_lines == 0 and state.missing_fields == 0,
            "errors": state.errors[:25],
            "has_content": len(records) > 0,
        },
        "label_map": EVENT_LABEL_MAP,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _upload_hf(file_path: Path, repo_id: str) -> None:
    if HfApi is None or login is None:
        raise RuntimeError("huggingface_hub not installed; cannot upload")
    token = __import__("os").environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN environment variable is required for upload")
    login(token=token)
    api = HfApi()
    api.upload_file(
        path_or_fileobj=str(file_path),
        path_in_repo=f"data/{file_path.name}",
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Add gumroad automation dataset export: {file_path.name}",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Gumroad automation logs to HF-ready JSONL")
    parser.add_argument("--source", default=str(Path("training") / "aethermoore_ops_training.jsonl"), help="Source jsonl log")
    parser.add_argument("--out-dir", default=str(Path("training-data") / "gumroad-automation"), help="Output directory")
    parser.add_argument("--dataset", default="gumroad_automation", help="Dataset name used in output metadata")
    parser.add_argument("--run-id", default=None, help="Optional filter for specific run_id")
    parser.add_argument("--verify-only", action="store_true", help="Only run verification and summary checks")
    parser.add_argument("--upload-hf", action="store_true", help="Upload output jsonl to Hugging Face")
    parser.add_argument("--hf-repo", default=None, help="HF dataset repo id (required if --upload-hf)")
    return parser.parse_args()


def _filter_records(records: list[dict[str, Any]], run_id: str | None) -> list[dict[str, Any]]:
    if run_id is None:
        return records
    filtered = [r for r in records if str(r.get("run_id")) == str(run_id)]
    return filtered


def main() -> int:
    args = _parse_args()
    source = Path(args.source).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_file = out_dir / f"{args.dataset}.jsonl"
    manifest_path = out_dir / "manifest.json"

    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")

    state = ValidationState()
    state.source_path = source  # type: ignore[attr-defined]
    records = _load_source_records(source, state)
    filtered = _filter_records(records, args.run_id)

    if not filtered and args.run_id:
        raise ValueError(f"No events found for run_id={args.run_id}")

    if args.verify_only:
        _write_manifest(manifest_path, filtered, out_file, state, args.dataset)
        print(json.dumps({
            "verify_only": True,
            "source": str(source),
            "input_records": len(filtered),
            "valid_events": state.valid_events,
            "invalid_lines": state.invalid_lines,
            "missing_fields": state.missing_fields,
            "unknown_events": state.unknown_events,
            "manifest": str(manifest_path),
        }, indent=2))
        return 0 if (state.invalid_lines == 0 and state.missing_fields == 0) else 1

    _emit_dataset(filtered, out_file, state)
    _write_manifest(manifest_path, filtered, out_file, state, args.dataset)
    print(f"Wrote {len(filtered)} rows to {out_file}")
    print(f"Wrote manifest to {manifest_path}")

    if args.upload_hf:
        if not args.hf_repo:
            raise ValueError("--hf-repo required when --upload-hf is set")
        _upload_hf(out_file, args.hf_repo)
        _upload_hf(manifest_path, args.hf_repo)
        print(f"Uploaded {out_file.name} + manifest.json to {args.hf_repo}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
