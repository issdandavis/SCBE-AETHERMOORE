# Repository Inventory Backup (2026-03-01)

This folder stores local-ignored material that was backed up before cleanup.

- `agent_roundtable_20260301.zip`:
  - Snapshot of `artifacts/agent_roundtable` at backup time.
- `notes_dossier_20260301.zip`:
  - Snapshot of `training/runs/notes_dossier` at backup time.

## Restore

```powershell
# Optional restore to original locations
Expand-Archive backups\repo_inventory\agent_roundtable_20260301.zip
Expand-Archive backups\repo_inventory\notes_dossier_20260301.zip
```

## Note

`scripts/system/sort_obsidian_vault.py` is included because it is used in repeated cleanup and inventory workflows.
