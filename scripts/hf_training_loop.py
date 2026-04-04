#!/usr/bin/env python3
"""
Autonomous HF Training Loop — Headless Game + Governance + HuggingFace Push
===========================================================================

Runs the Aethermoor game headless with AI autopilot, collects training data
through the SCBE governance pipeline (L7/L9/L12/L14), and pushes approved
SFT pairs to HuggingFace Hub.

Usage::

    # Quick run (100 steps, local only)
    python scripts/hf_training_loop.py

    # Full autonomous run (1000 steps, push to HF)
    python scripts/hf_training_loop.py --steps 1000 --push

    # Continuous mode (runs until killed)
    python scripts/hf_training_loop.py --continuous --push

    # Batch size for export threshold
    python scripts/hf_training_loop.py --steps 5000 --batch 100 --push

Environment:
    HF_TOKEN  — HuggingFace write token (required for --push)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Ensure project root and demo/ are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = PROJECT_ROOT / "demo"
for p in [str(PROJECT_ROOT), str(DEMO_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("hf_training_loop")

GAME_SESSIONS_DIR = PROJECT_ROOT / "training-data" / "game_sessions"


def load_env() -> None:
    """Load .env from project root."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.is_file():
        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=env_path, override=False)
        except ImportError:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip().strip("\"'")
                    if key and key not in os.environ:
                        os.environ[key] = value


def count_local_pairs() -> int:
    """Count total training pairs in game_sessions/."""
    total = 0
    for f in GAME_SESSIONS_DIR.glob("*.jsonl"):
        with open(f, "r", encoding="utf-8") as fh:
            total += sum(1 for _ in fh)
    return total


def run_game_session(steps: int) -> int:
    """Run one headless game session and return number of new training pairs.

    The game's built-in hf_trainer daemon writes JSONL to
    training-data/game_sessions/ automatically.
    """
    before = count_local_pairs()

    try:
        from headless import run_headless

        gif_path = str(PROJECT_ROOT / "artifacts" / f"training_session_{int(time.time())}.gif")
        os.makedirs(os.path.dirname(gif_path), exist_ok=True)

        hd = run_headless(
            num_steps=steps,
            ai_pilot=True,
            save_gif_path=gif_path,
            capture_every=4,
            max_frames=300,
            gif_fps=10,
            gif_scale=0.4,
        )
        logger.info("Headless session complete: %d frames captured", hd.frame_count)
    except Exception as e:
        logger.error("Headless session failed: %s", e)
        logger.info("Falling back to gacha squad demo...")
        run_gacha_fallback(steps)

    after = count_local_pairs()
    new_pairs = after - before
    return new_pairs


def run_gacha_fallback(steps: int) -> None:
    """Generate training data from gacha subsystem when full game fails."""
    try:
        sys.path.insert(0, str(DEMO_DIR))
        from gacha_squad_demo import main as gacha_main

        gacha_main()
        logger.info("Gacha demo fallback completed")
    except Exception as e:
        logger.error("Gacha fallback also failed: %s", e)
        # Ultra-fallback: use hf_trainer directly
        from hf_trainer import RealTimeHFTrainer, load_dotenv as _ld

        _ld()
        trainer = RealTimeHFTrainer()
        trainer.start()
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        for i in range(min(steps, 500)):
            trainer.record_choice(
                context=f"Auto-generated scenario #{i}",
                choice="Proceed",
                alternatives=["Wait", "Retreat"],
                outcome=f"Outcome #{i}: path revealed",
                tongue=tongues[i % 6],
                layers=[5, 12],
            )
            trainer.record_battle(
                attacker="Izack",
                defender=f"Monster_{i}",
                action="Cipher Strike",
                damage=10 + i,
                tongue=tongues[i % 6],
            )
        time.sleep(5)
        trainer.stop()
        status = trainer.get_status_dict()
        logger.info("Ultra-fallback: %d approved, %d batches", status["approved"], status["batches"])


def push_new_batches_to_hf(repo_id: str, since_ts: float) -> int:
    """Push any JSONL files created after since_ts to HuggingFace Hub."""
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        logger.warning("No HF_TOKEN — skipping push")
        return 0

    from huggingface_hub import HfApi

    api = HfApi(token=token)

    # Ensure dataset repo exists
    try:
        api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
    except Exception as e:
        logger.warning("Could not create/verify repo %s: %s", repo_id, e)

    pushed = 0
    for filepath in sorted(GAME_SESSIONS_DIR.glob("*.jsonl")):
        if filepath.stat().st_mtime >= since_ts:
            try:
                api.upload_file(
                    path_or_fileobj=str(filepath),
                    path_in_repo=f"game_sessions/{filepath.name}",
                    repo_id=repo_id,
                    repo_type="dataset",
                )
                pushed += 1
                logger.info("Pushed: %s", filepath.name)
            except Exception as e:
                logger.error("Failed to push %s: %s", filepath.name, e)

    return pushed


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous HF Training Loop")
    parser.add_argument("--steps", type=int, default=300, help="Game ticks per session (default: 300)")
    parser.add_argument("--push", action="store_true", help="Push to HuggingFace Hub")
    parser.add_argument("--continuous", action="store_true", help="Run continuously until killed")
    parser.add_argument("--repo", type=str, default="SCBE-AETHER/aethermoor-training-v1", help="HF dataset repo ID")
    parser.add_argument("--batch", type=int, default=100, help="Trainer batch size")
    parser.add_argument("--autonomous", action="store_true", help="Alias for --continuous")
    args = parser.parse_args()

    load_env()

    continuous = args.continuous or args.autonomous
    hf_token = os.environ.get("HF_TOKEN", "")

    logger.info("=" * 60)
    logger.info("SCBE Autonomous HF Training Loop")
    logger.info("  Steps/session : %d", args.steps)
    logger.info("  HF push       : %s", "YES" if (args.push and hf_token) else "NO (local only)")
    logger.info("  HF token      : %s", "configured" if hf_token else "NOT SET")
    logger.info("  Repo          : %s", args.repo)
    logger.info("  Continuous    : %s", continuous)
    logger.info("  Existing data : %d pairs in game_sessions/", count_local_pairs())
    logger.info("=" * 60)

    session = 0
    total_new = 0

    while True:
        session += 1
        session_start = time.time()
        logger.info("--- Session %d ---", session)

        new_pairs = run_game_session(args.steps)
        total_new += new_pairs
        logger.info("Session %d: +%d new pairs (%d total new)", session, new_pairs, total_new)

        if args.push and hf_token and new_pairs > 0:
            pushed = push_new_batches_to_hf(args.repo, session_start)
            logger.info("Pushed %d files to HF Hub", pushed)

        if not continuous:
            break

        logger.info("Sleeping 5s before next session...")
        time.sleep(5)

    logger.info("=" * 60)
    logger.info("Training loop finished")
    logger.info("  Sessions      : %d", session)
    logger.info("  New pairs     : %d", total_new)
    logger.info("  Total on disk : %d", count_local_pairs())
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
