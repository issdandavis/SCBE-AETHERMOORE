#!/usr/bin/env python3
"""Prepare a matched-budget code A/B benchmark and optionally train it.

This is the sane replacement for comparing `code_baseline_l3.jsonl` against
`code_triangulated_sft.jsonl` at full size on a free notebook lane. The
triangulated corpus is much larger, so we first match by estimated token budget
before any training run is attempted.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = REPO_ROOT / "training-data" / "code_baseline_l3.jsonl"
DEFAULT_TRIANGULATED = REPO_ROOT / "training-data" / "code_triangulated_sft.jsonl"
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "research" / "code_ab_fast"


def extract_text(record: dict[str, Any]) -> str:
    """Normalize a training row into a single text field."""
    if isinstance(record.get("text"), str) and record["text"].strip():
        return record["text"].strip()

    messages = record.get("messages")
    if isinstance(messages, list):
        parts: list[str] = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role", "")).strip()
            content = str(message.get("content", "")).strip()
            if role and content:
                parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        if parts:
            return "\n".join(parts)

    prompt = str(record.get("prompt", "")).strip()
    response = str(record.get("response", "") or record.get("completion", "")).strip()
    if prompt and response:
        return (
            "<|im_start|>system\nYou are an SCBE-AETHERMOORE coding assistant.<|im_end|>\n"
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n{response}<|im_end|>"
        )

    return ""


def estimate_tokens(text: str) -> int:
    """Cheap token estimate for matching compute budgets."""
    return max(1, len(text) // 4)


def load_text_records(path: Path) -> list[dict[str, Any]]:
    """Load JSONL rows and attach normalized text plus an estimated token count."""
    loaded: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for row_index, line in enumerate(handle):
            if not line.strip():
                continue
            record = json.loads(line)
            text = extract_text(record)
            if len(text) < 32:
                continue
            loaded.append(
                {
                    "text": text,
                    "estimated_tokens": estimate_tokens(text),
                    "row_index": row_index,
                }
            )
    return loaded


def clamp_records(
    records: list[dict[str, Any]],
    *,
    target_tokens: int,
    max_records: int | None,
    seed: int,
) -> list[dict[str, Any]]:
    """Sample rows until the requested approximate token budget is reached."""
    shuffled = list(records)
    random.Random(seed).shuffle(shuffled)

    kept: list[dict[str, Any]] = []
    used_tokens = 0
    for record in shuffled:
        if max_records is not None and len(kept) >= max_records:
            break
        next_tokens = used_tokens + int(record["estimated_tokens"])
        if kept and next_tokens > target_tokens:
            break
        kept.append(record)
        used_tokens = next_tokens

    if not kept and shuffled:
        kept.append(shuffled[0])
    return kept


def summarize_records(records: list[dict[str, Any]]) -> dict[str, float | int]:
    tokens = [int(record["estimated_tokens"]) for record in records]
    total_tokens = sum(tokens)
    avg_tokens = (total_tokens / len(tokens)) if tokens else 0.0
    return {
        "rows": len(records),
        "estimated_tokens": total_tokens,
        "avg_estimated_tokens": round(avg_tokens, 2),
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps({"text": row["text"]}, ensure_ascii=False) + "\n")


def build_manifest(
    *,
    baseline_source: Path,
    triangulated_source: Path,
    baseline_full: list[dict[str, Any]],
    baseline_prepared: list[dict[str, Any]],
    triangulated_full: list[dict[str, Any]],
    triangulated_prepared: list[dict[str, Any]],
    seed: int,
    max_baseline_rows: int | None,
) -> dict[str, Any]:
    target_tokens = sum(int(row["estimated_tokens"]) for row in baseline_prepared)
    return {
        "seed": seed,
        "baseline_source": str(baseline_source),
        "triangulated_source": str(triangulated_source),
        "max_baseline_rows": max_baseline_rows,
        "target_token_budget": target_tokens,
        "full": {
            "baseline": summarize_records(baseline_full),
            "triangulated": summarize_records(triangulated_full),
        },
        "prepared": {
            "baseline": summarize_records(baseline_prepared),
            "triangulated": summarize_records(triangulated_prepared),
        },
        "ratio": {
            "full_rows": round(len(triangulated_full) / max(1, len(baseline_full)), 4),
            "full_tokens": round(
                summarize_records(triangulated_full)["estimated_tokens"]
                / max(1, summarize_records(baseline_full)["estimated_tokens"]),
                4,
            ),
            "prepared_rows": round(len(triangulated_prepared) / max(1, len(baseline_prepared)), 4),
            "prepared_tokens": round(
                summarize_records(triangulated_prepared)["estimated_tokens"]
                / max(1, summarize_records(baseline_prepared)["estimated_tokens"]),
                4,
            ),
        },
        "training_defaults": {
            "model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
            "epochs": 1,
            "max_steps_per_condition": 75,
            "lora_rank": 8,
            "max_seq_length": 512,
        },
    }


def prepare_benchmark(
    *,
    baseline_path: Path,
    triangulated_path: Path,
    artifact_dir: Path,
    max_baseline_rows: int | None,
    seed: int,
) -> dict[str, Any]:
    baseline_full = load_text_records(baseline_path)
    triangulated_full = load_text_records(triangulated_path)

    baseline_prepared = clamp_records(
        baseline_full,
        target_tokens=sum(int(row["estimated_tokens"]) for row in baseline_full),
        max_records=max_baseline_rows,
        seed=seed,
    )
    target_tokens = sum(int(row["estimated_tokens"]) for row in baseline_prepared)
    triangulated_prepared = clamp_records(
        triangulated_full,
        target_tokens=target_tokens,
        max_records=None,
        seed=seed,
    )

    baseline_out = artifact_dir / "baseline_matched.jsonl"
    triangulated_out = artifact_dir / "triangulated_matched.jsonl"
    write_jsonl(baseline_out, baseline_prepared)
    write_jsonl(triangulated_out, triangulated_prepared)

    manifest = build_manifest(
        baseline_source=baseline_path,
        triangulated_source=triangulated_path,
        baseline_full=baseline_full,
        baseline_prepared=baseline_prepared,
        triangulated_full=triangulated_full,
        triangulated_prepared=triangulated_prepared,
        seed=seed,
        max_baseline_rows=max_baseline_rows,
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--triangulated", type=Path, default=DEFAULT_TRIANGULATED)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-baseline-rows", type=int, default=5000)
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only build the matched dataset manifest. Training is intentionally omitted by default.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = prepare_benchmark(
        baseline_path=args.baseline,
        triangulated_path=args.triangulated,
        artifact_dir=args.artifact_dir,
        max_baseline_rows=args.max_baseline_rows,
        seed=args.seed,
    )

    print(json.dumps(manifest, indent=2))
    if args.prepare_only:
        return 0

    print(
        "\nPrepared matched-budget datasets. "
        "Training is intentionally left manual so the notebook lane can choose GPU/CPU safely."
    )
    print(
        "Recommended next step: use the manifest rows and token budget with a capped-step "
        "QLoRA runner instead of the full 47k-row triangulated corpus."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
