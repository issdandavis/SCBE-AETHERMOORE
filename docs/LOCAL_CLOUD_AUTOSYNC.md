# Local Cloud Autosync

This runner keeps local repo changes mirrored to cloud storage on a timer.

## Files
- `scripts/local_cloud_autosync.py`
- `scripts/run_local_cloud_autosync.ps1`
- `training/local_cloud_sync.json`
- `training/ingest/latest_local_cloud_sync.txt`
- `training/ingest/local_cloud_sync_state.json`

## What it does
1. Polls local files by glob include/exclude rules.
2. Detects added/modified/removed files.
3. Creates a timestamped sync bundle:
   - `training/runs/local_cloud_sync/<run_id>/manifest.json`
   - `training/runs/local_cloud_sync/<run_id>/index.json`
   - `training/runs/local_cloud_sync/<run_id>.zip`
4. Uploads bundle to selected cloud targets.
5. Rotates old local sync runs based on `keep_runs`.
6. Skips duplicate cloud uploads with fingerprint dedupe (`dedupe_uploads`).

## Cloud targets
- `github` (default enabled in config): uploads bundle assets to a GitHub release tag.
- `hf`: uploads run folder to a Hugging Face dataset repo path.
- `dropbox`: local sync-folder copy by default (or API upload if `shipping.dropbox.use_api=true`).
- `adobe`: copies bundle assets into your local Adobe Creative Cloud sync folder.
- `gdrive`: copies bundle assets into your local Google Drive sync folder.
- `proton`: copies bundle assets into your local Proton Drive sync folder.

## Required credentials
- GitHub release target:
  - `GH_TOKEN` or `GITHUB_TOKEN`
  - `gh` CLI installed/auth-ready
- Hugging Face target:
  - `HF_TOKEN`
  - `huggingface_hub` installed
  - `shipping.hf.repo_id` set in config
- Dropbox target:
  - `DROPBOX_TOKEN`

## Start once (single snapshot)
```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
pwsh -File scripts/run_local_cloud_autosync.ps1 -Once
```

## Start continuous autosync (recommended)
```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
pwsh -File scripts/run_local_cloud_autosync.ps1
```

## Install as scheduled background task
```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
pwsh -File scripts/install_local_cloud_sync_task.ps1 -TaskName SCBE-LocalCloudSync -IntervalMinutes 2
```

## Override targets per run
```powershell
pwsh -File scripts/run_local_cloud_autosync.ps1 -Once -ShipTargets github,dropbox
pwsh -File scripts/run_local_cloud_autosync.ps1 -Once -ShipTargets hf
pwsh -File scripts/run_local_cloud_autosync.ps1 -Once -ShipTargets adobe
pwsh -File scripts/run_local_cloud_autosync.ps1 -Once -ShipTargets dropbox,gdrive,proton,adobe
```

## Adobe Cloud setup
- Option 1 (auto-detect): leave `shipping.adobe.base_dir` empty and ensure one of these exists:
  - `%USERPROFILE%\\Creative Cloud Files`
  - `%USERPROFILE%\\Adobe Creative Cloud Files`
- Option 2 (explicit): set env var `ADOBE_CLOUD_SYNC_DIR` or set `shipping.adobe.base_dir` in `training/local_cloud_sync.json`.

## Dropbox / Google Drive / Proton setup
- Dropbox:
  - Auto-detects `%USERPROFILE%\\Dropbox*`
  - Or set `DROPBOX_SYNC_DIR` / `shipping.dropbox.base_dir`
- Google Drive:
  - Auto-detects `%USERPROFILE%\\Drive`, `%USERPROFILE%\\Google Drive`, `%USERPROFILE%\\My Drive`
  - Or set `GOOGLE_DRIVE_SYNC_DIR` / `shipping.gdrive.base_dir`
- Proton Drive:
  - Auto-detects `%USERPROFILE%\\Proton Drive*`
  - Or set `PROTON_DRIVE_SYNC_DIR` / `shipping.proton.base_dir`

## Notes
- If no changes are detected, the runner logs `status=no_changes`.
- If cloud upload fails, the snapshot still stays local under `training/runs/local_cloud_sync`.
- Duplicate upload protection is enabled by default (`dedupe_uploads: true`).
- `latest_local_cloud_sync.txt` points to the most recent run folder.
