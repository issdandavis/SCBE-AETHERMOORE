#!/usr/bin/env python3
"""
Build HYDRA training funnel artifacts from local JSONL sources.

This runner is intentionally non-invasive:
- It reuses hydra.training_funnel.TrainingFunnel for output contracts.
- It does not mutate existing source datasets.
- It can optionally push to HF and trigger Colab.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from hydra.training_funnel import SFTPair, TrainingFunnel


DEFAULT_INCLUDE_GLOBS = [
    "training-data/**/*.jsonl",
    "training/intake/**/*.jsonl",
    "artifacts/**/*.jsonl",
]

DEFAULT_EXCLUDE_GLOBS = [
    "training-data/funnel/*.jsonl",
    "training-data/funnel/*.json",
    "training-data/funnel/**/*.jsonl",
    "training-data/funnel/**/*.json",
    "**/.venv/**",
    "**/node_modules/**",
]

PROMPT_KEYS = [
    "prompt",
    "instruction",
    "input",
    "question",
    "query",
    "task",
    "text",
]

RESPONSE_KEYS = [
    "response",
    "output",
    "answer",
    "completion",
    "result",
    "detail",
]

SOURCE_HINTS = {
    "spiral": "spiral_search",
    "notion": "notion",
    "telegram": "telegram",
    "mesh": "mesh",
    "governance": "governance",
    "browser": "browser",
    "obsidian": "obsidian",
}


@dataclass
class NormalizedRow:
    instruction: str
    prompt: str
    response: str
    source: str
    tongue: str
    confidence: float
    source_file: str
    metadata: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build HYDRA funnel from JSONL sources")
    parser.add_argument("--repo-root", default=".", help="Repo root path")
    parser.add_argument(
        "--output-dir",
        default="training-data/funnel",
        help="Output folder for funnel artifacts",
    )
    parser.add_argument(
        "--include-glob",
        action="append",
        default=[],
        help="Glob pattern(s) to include; repeatable",
    )
    parser.add_argument(
        "--exclude-glob",
        action="append",
        default=[],
        help="Glob pattern(s) to exclude; repeatable",
    )
    parser.add_argument("--max-files", type=int, default=0, help="Optional cap on files")
    parser.add_argument("--max-records", type=int, default=0, help="Optional cap on records")
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Keep duplicate prompt/response rows",
    )
    parser.add_argument(
        "--hf-repo",
        default="issdandavis/scbe-aethermoore-training-data",
        help="HF dataset repo id",
    )
    parser.add_argument("--push-hf", action="store_true", help="Push generated funnel artifacts to HF")
    parser.add_argument("--split", default="train", help="HF split path used by push_to_hf")
    parser.add_argument("--trigger-colab", action="store_true", help="Trigger Colab after build")
    parser.add_argument("--tongue", default="KO", help="Tongue used when triggering Colab")
    parser.add_argument(
        "--colab-notebook-url",
        default="",
        help="Optional Colab notebook URL override",
    )
    return parser.parse_args()


def file_matches_any(path: Path, patterns: list[str], repo_root: Path) -> bool:
    try:
        rel = path.relative_to(repo_root).as_posix()
    except ValueError:
        rel = path.as_posix()
    for pat in patterns:
        if Path(rel).match(pat) or fnmatch.fnmatch(rel, pat):
            return True
    return False


def discover_files(
    repo_root: Path,
    include_patterns: list[str],
    exclude_patterns: list[str],
    max_files: int,
) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for pattern in include_patterns:
        for p in repo_root.glob(pattern):
            if not p.is_file():
                continue
            resolved = p.resolve()
            if resolved in seen:
                continue
            if file_matches_any(resolved, exclude_patterns, repo_root):
                continue
            seen.add(resolved)
            out.append(resolved)
            if max_files > 0 and len(out) >= max_files:
                return sorted(out)
    return sorted(out)


def normalize_source(path: Path) -> str:
    text = path.as_posix().lower()
    for hint, value in SOURCE_HINTS.items():
        if hint in text:
            return value
    parent = path.parent.name.strip().lower().replace("-", "_").replace(" ", "_")
    return parent or "unknown"


def _str_val(record: dict[str, Any], key: str) -> str:
    value = record.get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def normalize_messages(messages: list[dict[str, Any]]) -> tuple[str, str, str]:
    system_parts: list[str] = []
    user_parts: list[str] = []
    assistant_parts: list[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "")).strip().lower()
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role in {"user", "human"}:
            user_parts.append(content)
        elif role == "assistant":
            assistant_parts.append(content)
    instruction = "\n\n".join(system_parts)
    prompt = "\n\n".join(user_parts)
    response = assistant_parts[-1] if assistant_parts else ""
    return instruction, prompt, response


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_tongue(record: dict[str, Any]) -> str:
    tongue = _str_val(record, "tongue")
    if tongue:
        return tongue
    tongues = record.get("tongues")
    if isinstance(tongues, list):
        merged = ",".join(str(t).strip() for t in tongues if str(t).strip())
        return merged
    return ""


def normalize_confidence(record: dict[str, Any]) -> float:
    for key in ("confidence", "decision_confidence"):
        raw = record.get(key)
        if raw is None:
            continue
        try:
            return clamp01(float(raw))
        except (TypeError, ValueError):
            continue
    return 1.0


def normalize_row(record: dict[str, Any], source_file: Path) -> NormalizedRow | None:
    messages = record.get("messages")
    instruction = ""
    prompt = ""
    response = ""

    if isinstance(messages, list):
        instruction, prompt, response = normalize_messages(messages)

    if not prompt:
        for key in PROMPT_KEYS:
            prompt = _str_val(record, key)
            if prompt:
                break

    if not response:
        for key in RESPONSE_KEYS:
            response = _str_val(record, key)
            if response:
                break

    if not instruction and _str_val(record, "instruction") and _str_val(record, "prompt"):
        instruction = _str_val(record, "instruction")

    if not prompt and _str_val(record, "instruction") and not instruction:
        prompt = _str_val(record, "instruction")

    if not prompt or not response:
        return None

    source = normalize_source(source_file)
    tongue = normalize_tongue(record)
    confidence = normalize_confidence(record)

    metadata = {}
    raw_meta = record.get("metadata")
    if isinstance(raw_meta, dict):
        metadata = raw_meta
    elif isinstance(raw_meta, str):
        try:
            parsed = json.loads(raw_meta)
            if isinstance(parsed, dict):
                metadata = parsed
        except json.JSONDecodeError:
            metadata = {"raw": raw_meta}

    return NormalizedRow(
        instruction=instruction,
        prompt=prompt,
        response=response,
        source=source,
        tongue=tongue,
        confidence=confidence,
        source_file=str(source_file),
        metadata=metadata,
    )


def iter_jsonl_rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                yield payload


def write_merged(
    output_dir: Path,
    rows: list[NormalizedRow],
) -> Path:
    merged_path = output_dir / "merged_all.jsonl"
    with merged_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {
                "prompt": row.prompt,
                "response": row.response,
                "metadata": json.dumps(
                    {
                        "source": row.source,
                        "tongue": row.tongue,
                        "confidence": row.confidence,
                        "source_file": row.source_file,
                        **row.metadata,
                    },
                    ensure_ascii=True,
                ),
                "source_file": row.source_file,
                "category": row.source,
            }
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return merged_path


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    include = args.include_glob or list(DEFAULT_INCLUDE_GLOBS)
    exclude = list(DEFAULT_EXCLUDE_GLOBS) + list(args.exclude_glob or [])

    files = discover_files(
        repo_root=repo_root,
        include_patterns=include,
        exclude_patterns=exclude,
        max_files=max(0, int(args.max_files)),
    )

    dedupe: set[str] = set()
    normalized: list[NormalizedRow] = []
    files_scanned = 0
    rows_scanned = 0

    for file_path in files:
        files_scanned += 1
        for raw in iter_jsonl_rows(file_path):
            rows_scanned += 1
            row = normalize_row(raw, file_path)
            if row is None:
                continue
            key = hashlib.sha256(
                f"{row.prompt}\n{row.response}\n{row.source}\n{row.tongue}".encode("utf-8", errors="ignore")
            ).hexdigest()
            if not args.no_dedupe and key in dedupe:
                continue
            if not args.no_dedupe:
                dedupe.add(key)
            normalized.append(row)
            if args.max_records > 0 and len(normalized) >= int(args.max_records):
                break
        if args.max_records > 0 and len(normalized) >= int(args.max_records):
            break

    funnel = TrainingFunnel(output_dir=str(output_dir))
    for row in normalized:
        funnel.sft_pairs.append(
            SFTPair(
                instruction=row.instruction,
                input=row.prompt,
                output=row.response,
                source=row.source,
                tongue=row.tongue,
                confidence=row.confidence,
            )
        )
        funnel.stats[row.source] = funnel.stats.get(row.source, 0) + 1

    local_paths = funnel.save_local()
    merged_path = write_merged(output_dir, normalized)

    hf_result = {"status": "skipped"}
    if args.push_hf:
        hf_msg = funnel.push_to_hf(repo_id=args.hf_repo, split=str(args.split))
        hf_result = {"status": "ok" if hf_msg.startswith("Pushed ") else "error", "message": hf_msg}

    colab_result = {"status": "skipped"}
    if args.trigger_colab:
        notebook = args.colab_notebook_url.strip() or None
        colab_msg = funnel.trigger_colab_training(tongue=args.tongue, notebook_url=notebook)
        colab_result = {"status": "ok" if "triggered" in colab_msg.lower() else "info", "message": colab_msg}

    source_counts: dict[str, int] = {}
    for row in normalized:
        source_counts[row.source] = source_counts.get(row.source, 0) + 1

    summary = {
        "repo_root": str(repo_root),
        "output_dir": str(output_dir),
        "files_scanned": files_scanned,
        "rows_scanned": rows_scanned,
        "sft_pairs": len(funnel.sft_pairs),
        "dpo_triples": len(funnel.dpo_triples),
        "by_source": source_counts,
        "paths": {
            **local_paths,
            "merged_all": str(merged_path),
        },
        "hf": hf_result,
        "colab": colab_result,
    }

    summary_path = output_dir / "build_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["summary_path"] = str(summary_path)

    print(json.dumps(summary, indent=2))
    if args.push_hf and hf_result.get("status") == "error":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
