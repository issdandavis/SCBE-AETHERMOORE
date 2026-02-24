# Obsidian Multi-AI Domino Workflow

This runbook chains existing SCBE sync systems into one multi-agent workflow.

## What it does

1. Runs `scripts/run_multi_ai_content_sync.py` to generate training-ready run artifacts.
2. Optionally initializes `SCBE-Hub` in Obsidian (task board, map room, templates, agent registry).
3. Runs `scripts/system/system_hub_sync.py` to push a snapshot into Obsidian and optionally Git/Dropbox/webhooks.
3. Appends lifecycle events to `training/runs/multi_ai_sync/domino_events.jsonl`.

## Command

```powershell
.\scripts\system\obsidian_multi_ai_domino.ps1 `
  -VaultPath "C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder" `
  -InitHub `
  -SyncNotion `
  -NotionConfigKey multiAiDevelopmentCoordination `
  -PushGit `
  -SkipDropbox:$false
```

## Dry run

```powershell
.\scripts\system\obsidian_multi_ai_domino.ps1 `
  -VaultPath "C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder" `
  -SyncNotion `
  -DryRun
```

## Inputs

- `-VaultPath` or `OBSIDIAN_VAULT_PATH` (required)
- `-InitHub` optional (bootstraps `SCBE-Hub` collaboration lanes/templates)
- `-SyncNotion` optional
- `-NotionConfigKey` repeatable optional
- `-HfDatasetRepo` optional
- `-PushGit` optional
- `-SkipDropbox` optional
- `-DropboxRemoteDir` optional
- `-DryRun` optional

## Outputs

- `training/ingest/latest_multi_ai_sync.txt`
- `training/runs/multi_ai_sync/<timestamp>/...`
- `training/runs/multi_ai_sync/domino_events.jsonl`
- Obsidian snapshot folder: `<VaultPath>\SCBE-Hub\notion-sync\<timestamp>`
- Optional hub bootstrap:
  - `<VaultPath>\SCBE-Hub\00-Inbox`
  - `<VaultPath>\SCBE-Hub\01-Map-Room`
  - `<VaultPath>\SCBE-Hub\02-Task-Board`
  - `<VaultPath>\SCBE-Hub\03-Agents`
  - `<VaultPath>\SCBE-Hub\04-Runs`
  - `<VaultPath>\SCBE-Hub\05-Evidence`
  - `<VaultPath>\SCBE-Hub\06-Knowledge`
  - `<VaultPath>\SCBE-Hub\07-Protocols`
  - `<VaultPath>\SCBE-Hub\Templates`

## Adobe Creative note

This workflow does not directly automate Adobe app UI. For Adobe integration, use a file-based bridge:

1. Generate assets/specs from this repo.
2. Drop jobs into a watched folder used by your Adobe automation (UXP/CEP/ExtendScript).
3. Return rendered outputs into a tracked folder for the same domino chain.
