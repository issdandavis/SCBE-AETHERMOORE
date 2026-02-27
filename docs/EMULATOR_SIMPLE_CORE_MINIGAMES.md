# Emulator Mode: Simple Core + Mini-Games

Goal: keep the main visual/gameplay loop simple (Pokemon Ruby/Sapphire-like), and move complex systems into optional mini-games.

## What this mode does

- Core loop stays simple:
  - movement
  - dialogue
  - battle
  - progression
- Complex systems are injected as separate training/game-design rows:
  - careers
  - gacha squad strategy
  - Poly Pad (cell phone / in-game PC)
  - CodeLab IDE tickets (debug/test/refactor mini-game)
  - governance/autonomy systems
  - fighter-pilot tactical mini-games

## Packs

- Core loop pack:
  - `training-data/game_design_sessions/isekai_core_loop.jsonl`
- Mini-game pack:
  - `training-data/game_design_sessions/isekai_minigames.jsonl`
- Poly Pad mini-game pack:
  - `training-data/game_design_sessions/isekai_polypad_minigames.jsonl`
- Hybrid pack:
  - `training-data/game_design_sessions/isekai_emulator_hybrid.jsonl`

Regenerate packs:

```powershell
python scripts/build_emulator_packs.py
```

## Run command

```powershell
python demo/rom_emulator_bridge.py `
  --rom C:\path\to\crystal.gbc `
  --steps 5000 `
  --smart-agent `
  --game pokemon_crystal `
  --story-pack training-data/game_design_sessions/isekai_core_loop.jsonl `
  --story-pack training-data/game_design_sessions/isekai_minigames.jsonl `
  --story-pack training-data/game_design_sessions/isekai_polypad_minigames.jsonl `
  --story-pack-mode both `
  --story-pack-every 700 `
  --i-own-this-rom
```

Or use helper script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_emulator_simple_core.ps1 -RomPath C:\path\to\crystal.gbc -Steps 5000
```

## Cloud training flow

1. Run emulator session locally/headless to generate `training-data/rom_sessions/*.jsonl`.
2. Upload JSONL outputs to Hugging Face dataset repo from Colab.
3. Train LoRA/QLoRA in Colab (or long-run on GCP/AWS).
4. Track sidekick growth in append-only memory:

```powershell
python scripts/sidekick_memory.py init
python scripts/sidekick_memory.py log --task "Poly Pad mission review" --action "Summarize active mission and suggest next checkpoint" --outcome "Player picked safe route" --tags polypad,mission,sidekick --also-sft
python scripts/sidekick_memory.py build-sft
```

## If GIF preview is too large

Use tighter GIF settings so viewers do not reject the image:

```powershell
python demo/rom_emulator_bridge.py `
  --rom C:\path\to\crystal.gbc `
  --steps 4000 `
  --gif demo\rom_preview_small.gif `
  --gif-scale 0.35 `
  --gif-fps 8 `
  --gif-max-frames 140 `
  --i-own-this-rom
```
