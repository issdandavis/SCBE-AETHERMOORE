# System Connector Hub

Unifies Notion, Obsidian, GitHub, and Dropbox into one reproducible sync flow.

## What It Does
- Pulls Notion pages using `scripts/notion-sync.js`.
- Copies synced docs into your Obsidian vault snapshot folder.
- Stages and commits docs/training artifacts to GitHub.
- Uploads a zip backup to Dropbox.

## Required Environment Variables
- `NOTION_API_KEY`
- `DROPBOX_TOKEN`
- `OBSIDIAN_VAULT_PATH` (or pass `--vault-path`)

## One-Command Sync
```powershell
python scripts/system/system_hub_sync.py --vault-path "C:/Users/issda/OneDrive/Documents/ObsidianVault" --push
```

## Targeted Notion Page Sync
```powershell
python scripts/system/system_hub_sync.py --config-key scbeAethermooreUnifiedSystemReport --vault-path "C:/path/to/vault"
```

## Dry Run (No Writes)
```powershell
python scripts/system/system_hub_sync.py --dry-run --vault-path "C:/path/to/vault"
```

## Output Paths
- Obsidian snapshots: `ObsidianVault/SCBE-Hub/notion-sync/<timestamp>/`
- Dropbox backups: `/SCBE/backups/scbe-hub-sync-<timestamp>.zip`

## Notes
- The script only commits `docs/` and `training-data/hf-digimon-egg/`.
- Keep `NOTION_API_KEY` and `DROPBOX_TOKEN` in secrets/env, never in source files.
