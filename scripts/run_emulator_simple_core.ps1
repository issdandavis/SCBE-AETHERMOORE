param(
    [Parameter(Mandatory = $true)]
    [string]$RomPath,
    [int]$Steps = 5000,
    [string]$OutDir = "training-data/rom_sessions",
    [string]$GifPath = "demo/headless_simple_core.gif"
)

$ErrorActionPreference = "Stop"

Write-Host "Building emulator packs (core + mini-games)..."
python scripts/build_emulator_packs.py

Write-Host "Running ROM bridge in simple-core mode with mini-game injections..."
python demo/rom_emulator_bridge.py `
  --rom $RomPath `
  --steps $Steps `
  --smart-agent `
  --game pokemon_crystal `
  --out-dir $OutDir `
  --gif $GifPath `
  --story-pack training-data/game_design_sessions/isekai_core_loop.jsonl `
  --story-pack training-data/game_design_sessions/isekai_minigames.jsonl `
  --story-pack-mode both `
  --story-pack-every 700 `
  --i-own-this-rom

Write-Host "Done."
