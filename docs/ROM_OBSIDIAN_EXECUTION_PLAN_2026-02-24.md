# ROM Emulator + Obsidian Hub Execution Plan (2026-02-24)

## Scope

1. ROM emulator data-generation pipeline.
2. Obsidian multi-AI workspace hub where agents collaborate.

## Current state (implemented)

### ROM emulator

- `demo/rom_emulator_bridge.py`
  - Legal gate: requires `--i-own-this-rom`.
  - Supports `.gb` / `.gbc` via PyBoy headless backend.
  - Generates training JSONL (`prompt/response`) in `training-data/rom_sessions`.
  - Optional OCR dialogue extraction + GIF export.
- `docs/ROM_EMULATOR_COLAB.md`
  - Colab workflow for dependency install, run, and dataset upload.

### Obsidian collaboration

- `scripts/run_multi_ai_content_sync.py`
  - Builds offline-first run artifacts + snapshots.
- `scripts/system/system_hub_sync.py`
  - Syncs Notion outputs to Obsidian, Git, Dropbox, Zapier.
- `scripts/system/obsidian_multi_ai_domino.ps1`
  - Domino wrapper for multi-step run pipeline.
- `scripts/system/rom_obsidian_domino.ps1`
  - One-command ROM -> Obsidian run wrapper.
- `scripts/system/update_training_totals.ps1`
  - Canonical training-data count snapshot + Round Table/Shared State sync.
- `scripts/system/cross_talk_append.ps1`
  - Structured inter-AI handoff appender for `Cross Talk.md` and `Sessions/`.
- `docs/OBSIDIAN_MULTI_AI_DOMINO.md`
  - Existing runbook.

## Gaps (remaining)

### ROM emulator

- No GBA backend implemented yet (PyBoy is GB/GBC only).
- No direct integration from emulator run metadata into SCBE governance capsule format.
- No deterministic replay artifact (input trace file) for audit reproducibility.

### Obsidian hub

- No one-command bootstrap for a standard collaboration workspace layout.
- No default templates for task handoff, decision record, and run logs in vault.

## Changes added in this patch

### Obsidian hub bootstrap

- Added `--init-obsidian-hub` to `scripts/system/system_hub_sync.py`.
- Added `-InitHub` switch to `scripts/system/obsidian_multi_ai_domino.ps1`.
- Added `scripts/system/rom_obsidian_domino.ps1` to chain ROM generation and Obsidian sync in one command.
- Bootstrap creates standard lanes under `<Vault>\SCBE-Hub`:
  - `00-Inbox`, `01-Map-Room`, `02-Task-Board`, `03-Agents`,
    `04-Runs`, `05-Evidence`, `06-Knowledge`, `07-Protocols`, `Templates`.
- Added baseline notes/templates if missing:
  - `README.md`
  - `02-Task-Board/active_tasks.md`
  - `03-Agents/agent_registry.md`
  - `Templates/task.md`
  - `Templates/agent_handoff.md`
  - `Templates/decision_record.md`
  - `Templates/run_log.md`
  - `01-Map-Room/session_handoff_latest.md` (copied from repo if available).

## Next implementation order

1. ROM backend expansion:
   - Add mGBA backend adapter for `.gba`.
   - Keep legal gate + local-ROM-only model.
2. Governance binding:
   - Emit SCBE `StateVector` + `DecisionRecord` per ROM session.
3. Replay determinism:
   - Save input trace and seed for replay-verifiable runs.
4. Obsidian workflow:
   - Add optional “domino triggers” mapping from queue note changes to run commands.

## Run commands

Initialize hub + run domino:

```powershell
.\scripts\system\obsidian_multi_ai_domino.ps1 `
  -VaultPath "C:\path\to\vault" `
  -InitHub `
  -SyncNotion
```

ROM bridge (GB/GBC):

```powershell
python demo/rom_emulator_bridge.py `
  --rom "C:\path\to\owned_rom.gb" `
  --steps 8000 `
  --max-pairs 600 `
  --i-own-this-rom
```

One-command ROM -> Obsidian:

```powershell
.\scripts\system\rom_obsidian_domino.ps1 `
  -RomPath "C:\path\to\crystal.gbc" `
  -VaultPath "C:\path\to\vault" `
  -InitHub $true `
  -SmartAgent $true `
  -CaptureGif
```
