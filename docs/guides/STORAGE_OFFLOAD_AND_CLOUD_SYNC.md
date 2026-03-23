# Storage, Offload, And Cloud Sync

This guide covers verified cloud sync, offload, and repo-local run manifests.

## Core Files

- `docs/LOCAL_CLOUD_AUTOSYNC.md`
- `scripts/run_local_cloud_autosync.ps1`
- `scripts/multi_agent_offload.py`
- `scripts/start_multi_agent_offload_background.ps1`
- `training/local_cloud_sync.json`
- `training/ingest/local_cloud_sync_state.json`

## Two Main Modes

### 1. Local cloud autosync

Use this to snapshot repo changes and ship bundles to selected cloud targets.

```powershell
pwsh -File scripts/run_local_cloud_autosync.ps1 -Once
pwsh -File scripts/run_local_cloud_autosync.ps1 -Once -ShipTargets github,dropbox
pwsh -File scripts/run_local_cloud_autosync.ps1
```

### 2. Multi-agent offload

Use this for deterministic file triage, cloud shipping, and optional training-row capture.

```powershell
python scripts/multi_agent_offload.py --config scripts/multi_agent_offload.json --dry-run
python scripts/multi_agent_offload.py --config scripts/multi_agent_offload.json --max-files 5
```

Background start:

```powershell
pwsh -File scripts/start_multi_agent_offload_background.ps1
```

## Operating Rule

- Copy first.
- Verify the cloud target.
- Delete local sources only after verification succeeds.

## When To Use This Lane

- Disk pressure is rising.
- You need a reproducible archive trail.
- You want file movement to also produce training or audit metadata.
