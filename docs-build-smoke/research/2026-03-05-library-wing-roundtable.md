# Library Wing v1 — Multi-Model Round Table + Parallel Worktree Lanes

## Objective
Build a self-owned training wing that:
- reuses ChoiceScript-style branch/testing data
- loads compact RAG capsules (1-5 windows)
- runs multiple perspectives in parallel lanes
- writes deterministic artifacts for retraining and governance review

## Why This Matches Your Idea
Your "notes on guitar strings" analogy maps directly:
- each string = one model lane (`research`, `trainer`, `governance`, `product`, `ops`)
- each round = one synchronized chord
- conductor = consensus merge step

## Implemented Components

1. `src/knowledge/choicescript_loop_adapter.py`
- Converts `training-data/game_sessions/*.jsonl` into SFT-ready JSONL.
- Exports compact lane notes used by round-table models.

2. `src/knowledge/library_wing.py`
- Parallel perspective engine (`ThreadPoolExecutor`).
- Lane notes with citations and scores.
- Consensus builder and markdown/json report output.

3. `scripts/knowledge/run_library_wing.py`
- Orchestrates full loop:
  - ChoiceScript loop export
  - Capsule load (`training/context_capsules/capsule_5w.json`)
  - Obsidian vault ingestion
  - Parallel round-table execution

## Run It

```powershell
python scripts/knowledge/run_library_wing.py --rounds 2
```

Outputs in `artifacts/library_wing/`:
- `choicescript_sft.jsonl`
- `choicescript_notes.txt`
- `roundtable_<timestamp>.json`
- `roundtable_<timestamp>.md`
- `run_summary.json`

## HubSpot Legacy Role
Included as an ops lane (`ops-chair`) so CRM/organization perspective is part of the round table without blocking the core loop.

## Safety + Ownership
- No dependency on paid closed orchestration layer.
- Uses local artifacts + open APIs + your own dataset paths.
- Keeps active context small and reproducible.
