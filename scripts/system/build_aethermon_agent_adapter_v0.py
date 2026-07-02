#!/usr/bin/env python3
"""Build the local AETHERMON agent adapter v0 training target.

This is a small, verified local-training lane:

    AETHERMON receipts + AetherDesk browser-use + coding-system SFT
      -> compact train/holdout JSONL
      -> local QLoRA profile
      -> preflightable adapter target

It intentionally does not start training. The first contract is that the
dataset and profile are concrete, small, and safe to inspect before GPU work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
SFT_DIR = REPO_ROOT / "training-data" / "sft"
DEFAULT_AETHERMON_RECEIPTS = REPO_ROOT / "artifacts" / "aethermon_training_arena" / "episode_receipts.jsonl"
DEFAULT_AETHERMON_SUMMARY = REPO_ROOT / "artifacts" / "aethermon_training_arena" / "episode_summary.json"
DEFAULT_TRAIN = SFT_DIR / "aethermon_agent_adapter_v0_train.sft.jsonl"
DEFAULT_HOLDOUT = SFT_DIR / "aethermon_agent_adapter_v0_holdout.sft.jsonl"
DEFAULT_MANIFEST = SFT_DIR / "aethermon_agent_adapter_v0.manifest.json"
DEFAULT_PROFILE = REPO_ROOT / "config" / "model_training" / "aethermon-agent-adapter-v0-local.json"

AETHERMON_SYSTEM = (
    "You are an AETHERMON agent adapter. Choose one legal action from the observation. "
    "Return concise JSON only with action, reason, expected_events, and safety. "
    "Use receipts as truth; do not invent hidden state."
)

SOURCE_LIMITS = {
    "aethermon_ticks": 64,
    "aetherdesk_browser_use": 16,
    "coding_system_full": 48,
}


@dataclass(frozen=True)
class BuildInputs:
    receipts: Path
    summary: Path
    browser_use: Path
    coding_system: Path
    train_out: Path
    holdout_out: Path
    manifest_out: Path
    profile_out: Path
    train_ratio: float
    base_model: str
    max_steps: int


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def read_jsonl(path: Path, *, limit: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def stable_id(*parts: str) -> str:
    return hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()[:16]


def action_row(tick: dict[str, Any], source_path: Path) -> dict[str, Any]:
    before = tick["before"]
    assistant = {
        "action": tick["action"],
        "reason": tick.get("policy", {}).get("reason", ""),
        "expected_events": tick.get("events", []),
        "safety": {
            "valid": bool(tick.get("valid")),
            "legal_actions_checked": tick.get("policy", {}).get("observed_legal_actions", before.get("legal_actions", [])),
            "receipt_tick": tick.get("tick"),
        },
    }
    return {
        "messages": [
            {"role": "system", "content": AETHERMON_SYSTEM},
            {
                "role": "user",
                "content": "Choose the next AETHERMON action for this observation:\n"
                + json.dumps(before, sort_keys=True, ensure_ascii=True),
            },
            {"role": "assistant", "content": json.dumps(assistant, sort_keys=True, ensure_ascii=True)},
        ],
        "meta": {
            "source": "aethermon_training_arena_receipt",
            "source_path": rel(source_path),
            "domain": "aethermon",
            "kind": "action_policy_tick",
            "tick": tick.get("tick"),
            "valid": bool(tick.get("valid")),
            "success_after_tick": bool(tick.get("success")),
            "version": "v0",
        },
    }


def summary_row(summary: dict[str, Any], source_path: Path) -> dict[str, Any]:
    answer = {
        "success": summary.get("success"),
        "turns": summary.get("turns"),
        "total_reward": summary.get("total_reward"),
        "final_objective_state": summary.get("final_observation", {}),
        "promotion_rule": "Only promote adapter behavior after held-out action validity and episode success improve.",
    }
    return {
        "messages": [
            {"role": "system", "content": AETHERMON_SYSTEM},
            {
                "role": "user",
                "content": "Summarize the verified AETHERMON episode receipt and state whether it is trainable.",
            },
            {"role": "assistant", "content": json.dumps(answer, sort_keys=True, ensure_ascii=True)},
        ],
        "meta": {
            "source": "aethermon_training_arena_summary",
            "source_path": rel(source_path),
            "domain": "aethermon",
            "kind": "episode_summary",
            "success": bool(summary.get("success")),
            "version": "v0",
        },
    }


def load_aethermon_rows(receipts_path: Path, summary_path: Path, limit: int) -> list[dict[str, Any]]:
    ticks = read_jsonl(receipts_path, limit=limit)
    rows = [action_row(tick, receipts_path) for tick in ticks if tick.get("valid") is not None and "before" in tick]
    if summary_path.exists():
        rows.append(summary_row(json.loads(summary_path.read_text(encoding="utf-8")), summary_path))
    return rows


def normalize_existing_row(row: dict[str, Any], source_path: Path, source_name: str) -> dict[str, Any] | None:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return None
    normalized = {
        "messages": [
            {"role": str(item.get("role", "")), "content": str(item.get("content", ""))}
            for item in messages
            if item.get("role") and item.get("content")
        ],
        "meta": {
            **(row.get("meta") if isinstance(row.get("meta"), dict) else {}),
            "source_path": rel(source_path),
            "adapter_mix_source": source_name,
            "version": "v0",
        },
    }
    return normalized if len(normalized["messages"]) >= 2 else None


def take_existing_rows(path: Path, source_name: str, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_jsonl(path, limit=limit):
        normalized = normalize_existing_row(row, path, source_name)
        if normalized:
            rows.append(normalized)
    return rows


def split_rows(rows: list[dict[str, Any]], train_ratio: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    keyed = sorted(
        rows,
        key=lambda row: stable_id(
            row.get("meta", {}).get("source", row.get("meta", {}).get("adapter_mix_source", "unknown")),
            json.dumps(row.get("messages", []), sort_keys=True, ensure_ascii=True),
        ),
    )
    if len(keyed) <= 1:
        return keyed, []
    split_at = max(1, min(len(keyed) - 1, int(round(len(keyed) * train_ratio))))
    return keyed[:split_at], keyed[split_at:]


def write_profile(inputs: BuildInputs) -> None:
    profile = {
        "schema_version": "scbe_model_training_profile_v1",
        "profile_id": "aethermon-agent-adapter-v0-local",
        "title": "AETHERMON agent adapter v0 local proof profile",
        "description": (
            "Small local QLoRA proof target. Built for 6GB VRAM constraints; run dry-run/preflight before any GPU training."
        ),
        "backend": "local-qlora-peft",
        "base_model": inputs.base_model,
        "dataset": {
            "root": "training-data/sft",
            "train_files": [inputs.train_out.name],
            "eval_files": [inputs.holdout_out.name],
        },
        "training": {
            "max_seq_length": 512,
            "batch_size": 1,
            "gradient_accumulation_steps": 8,
            "max_steps": inputs.max_steps,
            "lora_rank": 8,
            "lora_alpha": 16,
            "lora_dropout": 0.05,
            "learning_rate": 0.0001,
            "gradient_checkpointing": True,
            "seed": 42,
            "save_total_limit": 2,
        },
        "evaluation": {
            "commands": {
                "oracle_control": "npm run training:aethermon-adapter:eval:oracle -- --json",
                "abstain_control": "npm run training:aethermon-adapter:eval:abstain -- --json",
                "score_predictions": (
                    "python scripts/system/eval_aethermon_agent_adapter_v0.py "
                    "--mode predictions --predictions <predictions.jsonl> --json"
                ),
            },
            "gates": [
                "heldout_json_action_validity",
                "legal_action_membership",
                "aethermon_episode_success",
                "coding_json_parse_validity",
            ],
            "do_not_promote_without": "adapter-vs-base holdout comparison receipt",
        },
        "local_constraints": {
            "target_vram_gb": 6,
            "disk_headroom_note": "Keep output/checkpoint count small; delete failed scratch runs before scaling.",
            "recommended_first_command": (
                "python scripts/system/preflight_zero_cost_training.py "
                "--profile config/model_training/aethermon-agent-adapter-v0-local.json --json"
            ),
        },
    }
    inputs.profile_out.parent.mkdir(parents=True, exist_ok=True)
    inputs.profile_out.write_text(json.dumps(profile, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def build(inputs: BuildInputs) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    rows.extend(load_aethermon_rows(inputs.receipts, inputs.summary, SOURCE_LIMITS["aethermon_ticks"]))
    rows.extend(take_existing_rows(inputs.browser_use, "aetherdesk_browser_use", SOURCE_LIMITS["aetherdesk_browser_use"]))
    rows.extend(take_existing_rows(inputs.coding_system, "coding_system_full", SOURCE_LIMITS["coding_system_full"]))
    if not rows:
        raise SystemExit("no rows found for AETHERMON adapter target")

    train_rows, holdout_rows = split_rows(rows, inputs.train_ratio)
    write_jsonl(inputs.train_out, train_rows)
    write_jsonl(inputs.holdout_out, holdout_rows)
    write_profile(inputs)

    counts_by_source = {}
    for row in rows:
        source = row.get("meta", {}).get("source") or row.get("meta", {}).get("adapter_mix_source") or "unknown"
        counts_by_source[source] = counts_by_source.get(source, 0) + 1

    manifest = {
        "schema": "aethermon_agent_adapter_v0_manifest",
        "generated_at": utc_now(),
        "source": "scripts/system/build_aethermon_agent_adapter_v0.py",
        "profile": rel(inputs.profile_out),
        "outputs": {
            "train": rel(inputs.train_out),
            "holdout": rel(inputs.holdout_out),
            "manifest": rel(inputs.manifest_out),
        },
        "inputs": {
            "aethermon_receipts": rel(inputs.receipts),
            "aethermon_summary": rel(inputs.summary),
            "browser_use": rel(inputs.browser_use),
            "coding_system": rel(inputs.coding_system),
        },
        "counts": {
            "total": len(rows),
            "train": len(train_rows),
            "holdout": len(holdout_rows),
            "by_source": dict(sorted(counts_by_source.items())),
        },
        "boundary": {
            "claim": "local adapter target prepared; no model improvement claim until training and heldout eval run",
            "safe_first_run": "40-80 max steps on 0.5B/1.5B before any 3B scale-up",
        },
    }
    inputs.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    inputs.manifest_out.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AETHERMON agent adapter v0 local training target.")
    parser.add_argument("--receipts", type=Path, default=DEFAULT_AETHERMON_RECEIPTS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_AETHERMON_SUMMARY)
    parser.add_argument("--browser-use", type=Path, default=SFT_DIR / "aetherdesk_browser_use_v1.sft.jsonl")
    parser.add_argument("--coding-system", type=Path, default=SFT_DIR / "coding_system_full_v1_train.sft.jsonl")
    parser.add_argument("--train-out", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--holdout-out", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--profile-out", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--train-ratio", type=float, default=0.85)
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    parser.add_argument("--max-steps", type=int, default=60)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    inputs = BuildInputs(
        receipts=args.receipts,
        summary=args.summary,
        browser_use=args.browser_use,
        coding_system=args.coding_system,
        train_out=args.train_out,
        holdout_out=args.holdout_out,
        manifest_out=args.manifest_out,
        profile_out=args.profile_out,
        train_ratio=args.train_ratio,
        base_model=args.base_model,
        max_steps=args.max_steps,
    )
    manifest = build(inputs)
    if args.json:
        print(json.dumps({"ok": True, **manifest}, indent=2, ensure_ascii=True))
    else:
        print("AETHERMON adapter target built")
        print(f"  train:   {manifest['outputs']['train']} ({manifest['counts']['train']} rows)")
        print(f"  holdout: {manifest['outputs']['holdout']} ({manifest['counts']['holdout']} rows)")
        print(f"  profile: {manifest['profile']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
