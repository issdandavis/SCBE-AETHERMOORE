# Zapier Automation (SCBE)

Use Zapier as the orchestration layer for Notion/Dropbox/Gmail actions.

## 1) Create Zapier Trigger
- App: **Webhooks by Zapier**
- Event: **Catch Hook**
- Copy webhook URL.

## 2) Set Webhook URL
```powershell
$env:ZAPIER_WEBHOOK_URL="https://hooks.zapier.com/hooks/catch/.../.../"
```

## 3) Run Hub Sync (Zapier enabled)
```powershell
python scripts/system/system_hub_sync.py --vault-path "C:/Users/issda/OneDrive/Documents/DOCCUMENTS/A follder" --push
```

## Cost-Control Defaults (important)
- Default mode is `summary`:
  - emits only `sync_completed` and `sync_failed`
  - does **not** emit `sync_started`
- Built-in cooldown is `900s` to avoid repeated paid tasks.

### Cheapest mode
```powershell
python scripts/system/system_hub_sync.py --zapier-mode fail-only
```

### Explicit managed mode
```powershell
python scripts/system/system_hub_sync.py --zapier-mode summary --zapier-cooldown-seconds 1800
```

### Lowest-cost smoke test (no Notion/Git/Dropbox side effects)
```powershell
python scripts/system/system_hub_sync.py --vault-path "C:/Users/issda/OneDrive/Documents/DOCCUMENTS/A follder" --skip-notion --skip-git --skip-dropbox --zapier-mode summary --zapier-cooldown-seconds 3600
```

## Events Emitted
- `sync_started`
- `sync_completed`
- `sync_failed`

The script now prints explicit Zapier decisions for easy auditing:
- `[zapier] emitted <event>`
- `[zapier] skipped <event> (cooldown=...s)`

## Payload Fields (sync_completed)
- `event`
- `timestamp_utc`
- `duration_seconds`
- `repo_root`
- `synced_file_count`
- `synced_files`
- `obsidian_snapshot`
- `dropbox_remote`
- `dry_run`

## Recommended Zap Actions
1. Filter by `event`.
2. Create Notion DB row for `sync_completed`.
3. Send Gmail summary for `sync_failed`.
4. Optional: write run log to Dropbox/Drive.

## Dry-run Validation
```powershell
python scripts/system/system_hub_sync.py --vault-path "C:/Users/issda/OneDrive/Documents/DOCCUMENTS/A follder" --dry-run
```

## Optional flags
- `--no-include-hf-training-docs`: skip `training-data/hf-digimon-egg` in Obsidian snapshot.
