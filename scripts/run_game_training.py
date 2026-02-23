#!/usr/bin/env python3
"""
Run AI agents through training games and export SFT + DPO data.

Uses the ChoiceEngine to auto-play the governance simulator (and other games)
with diverse AI agents, capturing every decision as training data.

Usage:
    python scripts/run_game_training.py
    python scripts/run_game_training.py --agents 500 --game governance_simulator
    python scripts/run_game_training.py --export-dpo

Author: Issac Davis
Date: 2026-02-22
Part of SCBE-AETHERMOORE (USPTO #63/961,403)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from symphonic_cipher.scbe_aethermoore.concept_blocks.choice_engine import ChoiceEngine


GAMES_DIR = PROJECT_ROOT / "training-data" / "games"
OUTPUT_DIR = PROJECT_ROOT / "training-data"

# Default initial stats for the governance simulator
GOVERNANCE_STATS = {
    "authority": 5.0,    # KO - Kor'aelin
    "diplomacy": 5.0,    # AV - Avali
    "integrity": 5.0,    # RU - Runethic
    "intelligence": 5.0, # CA - Cassisivadan
    "structure": 5.0,    # DR - Draumric
    "mystery": 5.0,      # UM - Umbroth
}


def find_games() -> dict[str, Path]:
    """Discover all game files in the games directory."""
    games: dict[str, Path] = {}
    if not GAMES_DIR.exists():
        return games
    for game_dir in sorted(GAMES_DIR.iterdir()):
        if not game_dir.is_dir():
            continue
        for f in game_dir.iterdir():
            if f.suffix in (".twee", ".tw", ".json"):
                games[game_dir.name] = f
                break
    return games


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI agents through training games")
    parser.add_argument("--game", default=None, help="Specific game to play (default: all)")
    parser.add_argument("--agents", type=int, default=100, help="Number of agents per game")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--temperature", type=float, default=1.0, help="Agent decision temperature")
    parser.add_argument("--export-dpo", action="store_true", help="Also export DPO preference pairs")
    parser.add_argument("--output", default=str(OUTPUT_DIR / "sft_games.jsonl"), help="SFT output path")
    args = parser.parse_args()

    print("=" * 60)
    print("SCBE-AETHERMOORE Game Training Pipeline")
    print("=" * 60)

    # Discover games
    games = find_games()
    if not games:
        print("ERROR: No games found in training-data/games/", file=sys.stderr)
        sys.exit(1)

    print(f"\nDiscovered {len(games)} game(s):")
    for name, path in games.items():
        print(f"  {name}: {path.name}")

    # Filter to specific game if requested
    if args.game:
        if args.game not in games:
            print(f"ERROR: Game '{args.game}' not found. Available: {list(games.keys())}", file=sys.stderr)
            sys.exit(1)
        games = {args.game: games[args.game]}

    # Run playthroughs
    engine = ChoiceEngine()

    for game_name, game_path in games.items():
        print(f"\n--- Loading: {game_name} ---")
        graph = engine.load_game(game_path, game_id=game_name)
        print(f"  Scenes: {graph.total_scenes()}")
        print(f"  Entry points: {graph.entry_points}")
        print(f"  Exit points: {len(graph.exit_points)}")
        print(f"  Branching factor: {graph.branching_factor():.2f}")

        print(f"\n--- Running {args.agents} agent playthroughs ---")
        trajectories = engine.auto_play(
            game_id=game_name,
            n_agents=args.agents,
            seed=args.seed,
            temperature=args.temperature,
            initial_stats=GOVERNANCE_STATS,
        )

        completed = sum(1 for t in trajectories if t.completed)
        print(f"  Completed: {completed}/{len(trajectories)}")

    # Export SFT
    print(f"\n--- Exporting SFT data ---")
    sft_count = engine.export_sft(args.output)
    print(f"  SFT records: {sft_count}")
    print(f"  Output: {args.output}")

    # Export DPO if requested
    if args.export_dpo:
        dpo_path = Path(args.output).with_stem(Path(args.output).stem.replace("sft_", "dpo_"))
        print(f"\n--- Exporting DPO pairs ---")
        dpo_count = engine.export_dpo_pairs(dpo_path)
        print(f"  DPO pairs: {dpo_count}")
        print(f"  Output: {dpo_path}")

    # Summary
    summary = engine.summary()
    print(f"\n--- Summary ---")
    print(json.dumps(summary, indent=2))

    print("\n" + "=" * 60)
    print("Game training pipeline complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
