"""Brick 1 continual learning — warm-start from Brick 0 with replay boost.

Wraps scripts/train/lora_tongue_table.py per docs/BRICK1_CONTINUAL_LEARNING_PLAN.md:

  * Warm-start LoRA from artifacts/tongue-table-lora-brick0-v5/lora_final
  * Mix dataset: 60% Brick 0 replay + 40% Brick 1 boost (row-replicated)
  * lr 3e-5, cosine schedule with 25-step warmup
  * max_steps 750, eval_every 25, early_stop 0.90

The dataset-level 60/40 mix approximates the plan's "interleave 1 boost batch
every 3 training batches" without a custom Sampler — since the trainer shuffles
per epoch, the gradient distribution matches batch-level interleave.

Usage:
    python scripts/train_brick1_continual.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REPLAY = REPO_ROOT / "data" / "tongue_drill" / "drill_langues_full.jsonl"
BOOST = REPO_ROOT / "data" / "tongue_drill" / "brick1_boost.jsonl"
MERGED = REPO_ROOT / "data" / "tongue_drill" / "brick1_mix.jsonl"
RESUME_ADAPTER = REPO_ROOT / "artifacts" / "tongue-table-lora-brick0-v5" / "lora_final"
OUTPUT = REPO_ROOT / "artifacts" / "tongue-table-lora-brick1-v1"

# Plan target ratio: 60% brick0 replay / 40% boost
TARGET_BOOST_SHARE = 0.40


def build_mix() -> dict:
    replay_rows = [json.loads(line) for line in REPLAY.read_text(encoding="utf-8").splitlines() if line.strip()]
    boost_rows = [json.loads(line) for line in BOOST.read_text(encoding="utf-8").splitlines() if line.strip()]

    n_replay = len(replay_rows)
    # Solve: boost_count / (replay_count + boost_count) = TARGET_BOOST_SHARE
    target_boost = int(round(n_replay * TARGET_BOOST_SHARE / (1 - TARGET_BOOST_SHARE)))
    n_boost_src = len(boost_rows)
    if n_boost_src == 0:
        raise SystemExit(f"Boost file is empty: {BOOST}")

    repeats_full = target_boost // n_boost_src
    remainder = target_boost - repeats_full * n_boost_src
    merged: list[dict] = list(replay_rows)
    for _ in range(repeats_full):
        merged.extend(boost_rows)
    merged.extend(boost_rows[:remainder])

    MERGED.parent.mkdir(parents=True, exist_ok=True)
    with MERGED.open("w", encoding="utf-8") as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return {
        "replay_rows": n_replay,
        "boost_source_rows": n_boost_src,
        "boost_emitted": target_boost,
        "total_rows": len(merged),
        "effective_boost_share": round(target_boost / len(merged), 4),
    }


def launch_training(mix_stats: dict) -> int:
    if not RESUME_ADAPTER.exists():
        raise SystemExit(f"Resume adapter missing: {RESUME_ADAPTER}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "brick1_mix_stats.json").write_text(json.dumps(mix_stats, indent=2), encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/train/lora_tongue_table.py",
        "--base_model", "Qwen/Qwen2.5-0.5B",
        "--data", str(MERGED.relative_to(REPO_ROOT)),
        "--output", str(OUTPUT.relative_to(REPO_ROOT)),
        "--resume_adapter", str(RESUME_ADAPTER),
        "--max_steps", "750",
        "--eval_every", "25",
        "--lr", "3e-5",
        "--lr_scheduler_type", "cosine",
        "--warmup_steps", "25",
        "--early_stop_score", "0.90",
        "--map_weights", json.dumps({
            "transport_atomic": 1.0,
            "cartography_state": 2.0,
            "cross_braid_code": 1.5,
        }),
        "--default_map_weight", "1.0",
    ]
    print("[BRICK1] launching:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(REPO_ROOT))


def main() -> int:
    if not REPLAY.exists():
        raise SystemExit(f"Replay source missing: {REPLAY}")
    if not BOOST.exists():
        raise SystemExit(
            f"Boost file missing: {BOOST}. Run scripts/build_brick1_boost.py first."
        )

    print(f"[BRICK1] replay: {REPLAY}")
    print(f"[BRICK1] boost:  {BOOST}")
    print(f"[BRICK1] mixed:  {MERGED}  (target boost share {TARGET_BOOST_SHARE:.0%})")
    print(f"[BRICK1] resume: {RESUME_ADAPTER}")
    print(f"[BRICK1] output: {OUTPUT}")

    stats = build_mix()
    print(f"[BRICK1] mix built: {stats}")

    return launch_training(stats)


if __name__ == "__main__":
    raise SystemExit(main())
