#!/usr/bin/env python3
"""
Build emulator-ready story packs with a simple core loop and optional mini-games.

Outputs:
- core loop pack (simple Pokemon-like progression)
- mini-game pack (advanced systems: careers, gacha, pilot, Poly Pad, governance)
- hybrid pack (core + mini-game rows)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            rows.append(obj)
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def is_minigame_row(row: Dict[str, Any]) -> bool:
    topic = str((row.get("metadata") or {}).get("topic", "")).lower()
    prompt = str(row.get("prompt", "")).lower()
    signal = f"{topic} {prompt}"
    triggers = (
        "career",
        "gacha",
        "autonomous",
        "technical-narrative",
        "mini-game",
        "pilot",
        "fleet",
        "governance",
        "poly pad",
        "polypad",
        "in-game pc",
        "pc box",
        "phone",
    )
    return any(t in signal for t in triggers)


def normalize_mode(row: Dict[str, Any], mode: str) -> Dict[str, Any]:
    out = dict(row)
    meta = dict(out.get("metadata", {}) if isinstance(out.get("metadata"), dict) else {})
    meta["mode"] = mode
    out["metadata"] = meta
    if not out.get("event_type"):
        out["event_type"] = "game_design"
    return out


def dedupe(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        key = (str(row.get("prompt", "")).strip(), str(row.get("response", "")).strip())
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build simple-core + minigame emulator packs")
    parser.add_argument(
        "--input",
        default="training-data/game_design_sessions/isekai_game.jsonl",
        help="Primary game design JSONL",
    )
    parser.add_argument(
        "--pilot-pack",
        default="training-data/game_design_sessions/pilot_minigames_open_source.jsonl",
        help="Optional pilot mini-game JSONL",
    )
    parser.add_argument(
        "--polypad-pack",
        default="training-data/game_design_sessions/isekai_polypad_minigames.jsonl",
        help="Optional Poly Pad / in-game PC mini-game JSONL",
    )
    parser.add_argument(
        "--out-core",
        default="training-data/game_design_sessions/isekai_core_loop.jsonl",
        help="Core loop output JSONL",
    )
    parser.add_argument(
        "--out-minigame",
        default="training-data/game_design_sessions/isekai_minigames.jsonl",
        help="Mini-games output JSONL",
    )
    parser.add_argument(
        "--out-hybrid",
        default="training-data/game_design_sessions/isekai_emulator_hybrid.jsonl",
        help="Hybrid (core + mini-game) output JSONL",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    primary = read_jsonl(Path(args.input))
    pilot = read_jsonl(Path(args.pilot_pack))
    polypad = read_jsonl(Path(args.polypad_pack))

    core_rows: List[Dict[str, Any]] = []
    mini_rows: List[Dict[str, Any]] = []

    for row in primary:
        if is_minigame_row(row):
            mini_rows.append(normalize_mode(row, "mini_game"))
        else:
            core_rows.append(normalize_mode(row, "core_loop"))

    for row in pilot:
        mini_rows.append(normalize_mode(row, "mini_game"))
    for row in polypad:
        mini_rows.append(normalize_mode(row, "mini_game"))

    core_rows = dedupe(core_rows)
    mini_rows = dedupe(mini_rows)
    hybrid_rows = dedupe(core_rows + mini_rows)

    core_n = write_jsonl(Path(args.out_core), core_rows)
    mini_n = write_jsonl(Path(args.out_minigame), mini_rows)
    hybrid_n = write_jsonl(Path(args.out_hybrid), hybrid_rows)

    print(f"core loop rows: {core_n} -> {Path(args.out_core)}")
    print(f"mini-game rows: {mini_n} -> {Path(args.out_minigame)}")
    print(f"hybrid rows:    {hybrid_n} -> {Path(args.out_hybrid)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
