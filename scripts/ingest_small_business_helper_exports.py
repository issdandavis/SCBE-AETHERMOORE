#!/usr/bin/env python3
"""Convert Small Business Helper mobile exports into repo-native chat SFT rows.

Accepted inputs:
- Thread bundle JSON exports from `small-business-helper.html`
- SFT JSONL exports from the same mobile lane
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "artifacts" / "mobile_exports" / "small-business-helper"
DEFAULT_OUTPUT = REPO_ROOT / "training-data" / "sft" / "small_business_helper_mobile.jsonl"
DEFAULT_SUMMARY = REPO_ROOT / "artifacts" / "training" / "small_business_helper_mobile.summary.json"
DEFAULT_SYSTEM_PROMPT = (
    "You are Polly Helper, a practical small-business operations assistant. "
    "Be direct, structured, and risk-aware. Default to read-only guidance, "
    "surface compliance or legal risk early, and do not imply that any "
    "destructive or financial action has already happened."
)

_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bssh-(rsa|ed25519)\s+[A-Za-z0-9+/=]{20,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*([^\s\"']{8,})"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def path_for_manifest(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Small Business Helper mobile exports into chat SFT JSONL")
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Input files or directories. Defaults to artifacts/mobile_exports/small-business-helper/",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT), help="Output JSONL path")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY), help="Summary JSON path")
    return parser.parse_args()


def scrub_text(text: str) -> str:
    cleaned = str(text or "")
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned.strip()


def scrub_obj(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, list):
        return [scrub_obj(item) for item in value]
    if isinstance(value, dict):
        return {str(key): scrub_obj(val) for key, val in value.items()}
    return value


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return rows
    return rows


def iter_input_files(inputs: list[str]) -> list[Path]:
    roots = [Path(item) for item in inputs] if inputs else [DEFAULT_INPUT]
    files: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root.is_file():
            candidates = [root]
        elif root.is_dir():
            candidates = sorted(
                [*root.rglob("*.json"), *root.rglob("*.jsonl")],
                key=lambda item: str(item).lower(),
            )
        else:
            continue
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(candidate)
    return files


def bundle_rows(bundle: dict[str, Any], source_label: str) -> list[dict[str, Any]]:
    messages = bundle.get("messages")
    if not isinstance(messages, list):
        return []

    session = bundle.get("session")
    system_prompt = scrub_text(bundle.get("systemPrompt") or DEFAULT_SYSTEM_PROMPT) or DEFAULT_SYSTEM_PROMPT
    compare_models = bundle.get("compareModels")
    if not isinstance(compare_models, list):
        compare_models = []

    rows: list[dict[str, Any]] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        if str(message.get("role")) != "assistant":
            continue
        if bool(message.get("initial")) or str(message.get("lane") or "") == "error":
            continue
        assistant_text = scrub_text(message.get("content") or "")
        if not assistant_text:
            continue

        prompt = ""
        for prior in range(index - 1, -1, -1):
            previous = messages[prior]
            if isinstance(previous, dict) and str(previous.get("role")) == "user":
                prompt = scrub_text(previous.get("content") or "")
                if prompt:
                    break
        if not prompt:
            continue

        session_id = ""
        if isinstance(session, dict):
            session_id = scrub_text(session.get("id") or "")

        rows.append(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": assistant_text},
                ],
                "track": "polly_chat",
                "source_type": "small_business_helper_mobile",
                "quality": "captured",
                "surface": "small_business_helper",
                "source": source_label,
                "metadata": {
                    "session_id": session_id,
                    "assistant_name": scrub_text(bundle.get("assistantName") or "Polly Helper"),
                    "primary_model": scrub_text(bundle.get("primaryModel") or ""),
                    "model": scrub_text(message.get("model") or ""),
                    "lane": scrub_text(message.get("lane") or "primary"),
                    "label": scrub_text(message.get("label") or ""),
                    "compare_models": [scrub_text(item) for item in compare_models if scrub_text(item)],
                    "title": scrub_text(bundle.get("title") or "Small Business Helper"),
                    "export_source": scrub_text(bundle.get("source") or "small_business_helper_mobile"),
                    "exported_at": scrub_text(bundle.get("exportedAt") or ""),
                    "timestamp": scrub_text(message.get("createdAt") or ""),
                },
            }
        )
    return rows


def record_to_chat_row(record: dict[str, Any], source_label: str) -> dict[str, Any] | None:
    if isinstance(record.get("messages"), list):
        messages = [item for item in record["messages"] if isinstance(item, dict)]
        system = next(
            (scrub_text(item.get("content") or "") for item in messages if item.get("role") == "system"),
            "",
        )
        user = next(
            (scrub_text(item.get("content") or "") for item in messages if item.get("role") == "user"),
            "",
        )
        assistant = next(
            (scrub_text(item.get("content") or "") for item in messages if item.get("role") == "assistant"),
            "",
        )
        if not user or not assistant:
            return None
        return {
            "messages": [
                {"role": "system", "content": system or DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant},
            ],
            "track": scrub_text(record.get("track") or "polly_chat"),
            "source_type": scrub_text(record.get("source_type") or "small_business_helper_mobile"),
            "quality": scrub_text(record.get("quality") or "captured"),
            "surface": scrub_text(record.get("surface") or "small_business_helper"),
            "source": source_label,
            "metadata": scrub_obj(record.get("metadata") or {}),
        }

    user = scrub_text(record.get("input") or record.get("instruction") or "")
    assistant = scrub_text(record.get("output") or record.get("response") or "")
    if not user or not assistant:
        return None

    metadata = record.get("metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {"raw_metadata": scrub_text(metadata)}

    normalized_metadata = scrub_obj(metadata) if isinstance(metadata, dict) else {}
    return {
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "track": "polly_chat",
        "source_type": scrub_text(record.get("source") or "small_business_helper_mobile"),
        "quality": "captured",
        "surface": "small_business_helper",
        "source": source_label,
        "metadata": {
            "session_id": scrub_text(record.get("session_id") or ""),
            "model": scrub_text(record.get("model") or ""),
            "lane": scrub_text(record.get("lane") or ""),
            "title": scrub_text(record.get("title") or "Small Business Helper"),
            **normalized_metadata,
        },
    }


def dedupe_key(row: dict[str, Any]) -> tuple[str, str, str]:
    messages = row.get("messages") or []
    user = ""
    assistant = ""
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") == "user":
            user = str(message.get("content") or "").strip().lower()
        elif message.get("role") == "assistant":
            assistant = str(message.get("content") or "").strip().lower()
    model = str((row.get("metadata") or {}).get("model") or "").strip().lower()
    return user, assistant, model


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(scrub_obj(row), ensure_ascii=False) + "\n")


def ingest_exports(input_files: list[Path], output_path: Path, summary_path: Path) -> dict[str, Any]:
    kept_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    stats = Counter()
    files_seen: list[str] = []

    for path in input_files:
        source_label = path_for_manifest(path)
        files_seen.append(source_label)

        candidate_rows: list[dict[str, Any]] = []
        if path.suffix.lower() == ".json":
            stats["bundle_files"] += 1
            payload = read_json(path)
            if payload is None:
                stats["invalid_files"] += 1
                continue
            candidate_rows = bundle_rows(payload, source_label)
        elif path.suffix.lower() == ".jsonl":
            stats["jsonl_files"] += 1
            for record in read_jsonl(path):
                row = record_to_chat_row(record, source_label)
                if row is None:
                    stats["skipped_rows"] += 1
                    continue
                candidate_rows.append(row)
        else:
            continue

        for row in candidate_rows:
            key = dedupe_key(row)
            if not key[0] or not key[1]:
                stats["skipped_rows"] += 1
                continue
            if key in seen:
                stats["duplicates_removed"] += 1
                continue
            seen.add(key)
            kept_rows.append(row)
            stats["kept_rows"] += 1

    write_jsonl(output_path, kept_rows)
    summary = {
        "generated_at": utc_now(),
        "input_files": files_seen,
        "output_path": path_for_manifest(output_path),
        "summary_path": path_for_manifest(summary_path),
        "counts": {
            "bundle_files": stats["bundle_files"],
            "jsonl_files": stats["jsonl_files"],
            "invalid_files": stats["invalid_files"],
            "kept_rows": stats["kept_rows"],
            "skipped_rows": stats["skipped_rows"],
            "duplicates_removed": stats["duplicates_removed"],
        },
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    args = parse_args()
    input_files = iter_input_files(args.inputs)
    summary = ingest_exports(input_files, Path(args.out), Path(args.summary))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
