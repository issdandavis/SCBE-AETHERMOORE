#!/usr/bin/env python3
"""Run Library Wing v1.

Builds modular training inputs from:
- ChoiceScript session loops
- Context capsules
- Obsidian vault notes

Then runs a multi-perspective round-table in parallel lanes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge.choicescript_loop_adapter import ChoiceScriptLoopAdapter
from src.knowledge.library_wing import (
    LibraryWingRoundTable,
    load_capsule_context,
    load_choicescript_context,
    load_obsidian_context,
)


def discover_obsidian_vaults() -> list[Path]:
    cfg = Path.home() / "AppData" / "Roaming" / "Obsidian" / "obsidian.json"
    if not cfg.exists():
        return []
    try:
        payload = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    vaults = payload.get("vaults", {})
    paths = []
    for _, entry in vaults.items():
        p = entry.get("path")
        if p:
            paths.append(Path(p))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Library Wing multi-model loop runner")
    parser.add_argument("--prompt", default="Build modular multi-model training loops for Aether Library Wing")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--session-files", type=int, default=20)
    parser.add_argument("--obsidian-files", type=int, default=60)
    parser.add_argument("--capsule", default="training/context_capsules/capsule_5w.json")
    parser.add_argument("--out", default="artifacts/library_wing")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) ChoiceScript loop export
    adapter = ChoiceScriptLoopAdapter(PROJECT_ROOT / "training-data" / "game_sessions")
    sft_path = out_dir / "choicescript_sft.jsonl"
    notes_path = out_dir / "choicescript_notes.txt"
    sft_count = adapter.export_sft_jsonl(sft_path, file_limit=args.session_files)
    notes_count = adapter.export_notes(notes_path, max_notes=300, file_limit=args.session_files)

    # 2) Build context pool
    context_items = []
    capsule_path = PROJECT_ROOT / args.capsule
    if capsule_path.exists():
        context_items.extend(load_capsule_context(capsule_path))

    context_items.extend(load_choicescript_context(notes_path))

    vaults = discover_obsidian_vaults()
    if vaults:
        context_items.extend(load_obsidian_context(vaults[0], max_files=args.obsidian_files))

    # 3) Run round-table
    engine = LibraryWingRoundTable(repo_root=PROJECT_ROOT, output_root=out_dir)
    run = engine.run(prompt=args.prompt, context_items=context_items, rounds=args.rounds)

    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path, md_path = engine.save_run(run, stem=f"roundtable_{stamp}")

    # 4) Emit run summary
    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "sft_records": sft_count,
        "choicescript_notes": notes_count,
        "context_items": len(context_items),
        "roundtable_json": str(json_path),
        "roundtable_md": str(md_path),
        "vault_count": len(vaults),
        "vault_used": str(vaults[0]) if vaults else None,
    }
    summary_path = out_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
