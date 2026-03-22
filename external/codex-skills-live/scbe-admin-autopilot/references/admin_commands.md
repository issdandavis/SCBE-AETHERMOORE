# SCBE Admin Autopilot Command Set

## Environment

```powershell
setx SCBE_ADMIN_PHONE "+1-000-000-0000"
setx SCBE_ADMIN_EMAIL "ops@example.com"
```

## Storage Ship/Verify/Prune

```powershell
python C:/Users/issda/SCBE-AETHERMOORE/scripts/system/ship_verify_prune.py \
  --source C:/Users/issda/SCBE-AETHERMOORE/artifacts \
  --dest C:/Users/issda/OneDrive/SCBE-Backups \
  --dest C:/Users/issda/Dropbox/SCBE-Backups \
  --min-verified-copies 2 \
  --delete-source
```

## Dry Run Safety Check

```powershell
python C:/Users/issda/SCBE-AETHERMOORE/scripts/system/ship_verify_prune.py \
  --source C:/Users/issda/SCBE-AETHERMOORE/artifacts \
  --dest C:/Users/issda/OneDrive/SCBE-Backups \
  --dest C:/Users/issda/Dropbox/SCBE-Backups \
  --min-verified-copies 2 \
  --dry-run
```
