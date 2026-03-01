#!/usr/bin/env python3
"""
Firebase Sync — CLI for inspecting and pushing data to Firebase Firestore
=========================================================================

Commands::

    python scripts/firebase_sync.py status          # Show all collections + doc counts
    python scripts/firebase_sync.py push-training    # Push polly_logs JSONL to Firebase
    python scripts/firebase_sync.py push-tentacles   # Push OctoArmor tentacle snapshot

@module scripts/firebase_sync
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ─── Load .env ────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[1]
_env_path = REPO_ROOT / ".env"
if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                if _v and _k.strip():
                    os.environ.setdefault(_k.strip(), _v.strip())

# ─── Ensure repo root is on sys.path for imports ─────
sys.path.insert(0, str(REPO_ROOT))


def get_firebase() -> "FirebaseSync":
    """Initialize and return a connected FirebaseSync instance."""
    from src.fleet.firebase_connector import FirebaseSync

    fb = FirebaseSync()
    if not fb.initialize():
        print("[ERROR] Firebase initialization failed.")
        print("  Check FIREBASE_CREDENTIALS_PATH and FIREBASE_PROJECT_ID in .env")
        print(f"  Credentials path: {fb.credentials_path or '(not set)'}")
        print(f"  Project ID:       {fb.project_id}")
        sys.exit(1)
    return fb


# ─── status ───────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> None:
    """Show all collections and document counts."""
    fb = get_firebase()

    collections = [
        "pollypad_sessions",
        "training_pairs",
        "tentacle_snapshots",
        "agent_registry",
        "aethernet_posts",
        "aethernet_tasks",
    ]

    print(f"\n  Firebase Project: {fb.project_id}")
    print(f"  Credentials:     {fb.credentials_path or '(ADC)'}")
    print(f"  Connected:       {fb.connected}")
    print()
    print("  Collection               Documents")
    print("  " + "-" * 45)

    total = 0
    for coll_name in collections:
        count = 0
        try:
            for _ in fb._db.collection(coll_name).limit(10000).stream():
                count += 1
        except Exception as exc:
            print(f"  {coll_name:<26} ERROR: {exc}")
            continue
        suffix = "+" if count >= 10000 else ""
        print(f"  {coll_name:<26} {count}{suffix}")
        total += count

    print("  " + "-" * 45)
    print(f"  {'TOTAL':<26} {total}")
    print()

    # Platform stats via the new method
    stats = fb.get_platform_stats()
    if stats.get("connected"):
        print("  AetherNet Platform Stats:")
        print(f"    Agents:         {stats.get('agents', 0)}")
        print(f"    Posts:          {stats.get('posts', 0)}")
        print(f"    Tasks:          {stats.get('tasks', 0)}")
        print(f"    Training Pairs: {stats.get('training_pairs', 0)}")
    print()


# ─── push-training ────────────────────────────────────

def cmd_push_training(args: argparse.Namespace) -> None:
    """Push training data from training-data/polly_logs/ to Firebase."""
    fb = get_firebase()

    logs_dir = REPO_ROOT / "training-data" / "polly_logs"
    if not logs_dir.exists():
        print(f"[ERROR] polly_logs directory not found: {logs_dir}")
        sys.exit(1)

    jsonl_files = sorted(logs_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"[WARN] No JSONL files found in {logs_dir}")
        return

    print(f"\n  Found {len(jsonl_files)} JSONL file(s) in {logs_dir}")
    print()

    total_pushed = 0
    total_errors = 0

    for jsonl_path in jsonl_files:
        pairs = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    pairs.append(record)
                except json.JSONDecodeError:
                    total_errors += 1

        if not pairs:
            print(f"  {jsonl_path.name}: 0 pairs (skipped)")
            continue

        # Push in batches of 500 (Firestore batch write limit)
        batch_size = 500
        file_pushed = 0
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i : i + batch_size]
            # Tag each pair with source file info
            for pair in batch:
                pair.setdefault("source_file", jsonl_path.name)
                pair.setdefault("source", "polly_logs")
            ok = fb.push_training_batch(batch)
            if ok:
                file_pushed += len(batch)
            else:
                total_errors += len(batch)

        print(f"  {jsonl_path.name}: {file_pushed} pairs pushed")
        total_pushed += file_pushed

    print()
    print(f"  Total pushed:  {total_pushed}")
    if total_errors:
        print(f"  Total errors:  {total_errors}")
    print()


# ─── push-tentacles ──────────────────────────────────

def cmd_push_tentacles(args: argparse.Namespace) -> None:
    """Push current OctoArmor tentacle status snapshot to Firebase."""
    fb = get_firebase()

    try:
        from src.fleet.octo_armor import HydraOctoArmor
    except ImportError as exc:
        print(f"[ERROR] Cannot import OctoArmor: {exc}")
        print("  Falling back to synthetic snapshot.")
        # Build a minimal synthetic snapshot so the push path still works
        synthetic = [
            {
                "tentacle": name,
                "available": True,
                "has_key": False,
                "cost": "FREE",
                "rpm": "0/0",
                "rpd": "0/0",
                "default_model": "unknown",
                "free_models": 0,
                "notes": "synthetic snapshot (OctoArmor import failed)",
            }
            for name in [
                "groq", "cerebras", "mistral", "openrouter",
                "google", "cohere", "github", "cloudflare",
            ]
        ]
        ok = fb.save_tentacle_snapshot(synthetic)
        if ok:
            print("  Synthetic tentacle snapshot saved to Firebase.")
        else:
            print("  [ERROR] Failed to save tentacle snapshot.")
        return

    print("\n  Initializing OctoArmor...")
    hydra = HydraOctoArmor()
    status = hydra.tentacle_status()

    available = sum(1 for t in status if t.get("available"))
    total = len(status)
    print(f"  Tentacles: {available}/{total} available")

    ok = fb.save_tentacle_snapshot(status)
    if ok:
        print("  Tentacle snapshot saved to Firebase.")
    else:
        print("  [ERROR] Failed to save tentacle snapshot.")

    # Print summary table
    print()
    print("  Tentacle        Available  Cost       Model")
    print("  " + "-" * 60)
    for t in status:
        name = t.get("tentacle", "?")
        avail = "YES" if t.get("available") else "no"
        cost = t.get("cost", "?")
        model = t.get("default_model", "?")
        print(f"  {name:<16} {avail:<10} {cost:<10} {model}")
    print()


# ─── CLI ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Firebase Sync — inspect and push data to Firestore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/firebase_sync.py status\n"
            "  python scripts/firebase_sync.py push-training\n"
            "  python scripts/firebase_sync.py push-tentacles\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    sub.add_parser("status", help="Show all collections and document counts")
    sub.add_parser("push-training", help="Push polly_logs JSONL files to Firebase")
    sub.add_parser("push-tentacles", help="Push OctoArmor tentacle status snapshot")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "status": cmd_status,
        "push-training": cmd_push_training,
        "push-tentacles": cmd_push_tentacles,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
