# Runbook

## Safety Baseline

- Use dry-run first.
- Use live copy second.
- Use delete mode last.
- Keep at least two verified targets before deletion unless the user explicitly changes the policy.

## Primary Files

- `scripts/multi_agent_offload.py`
- `scripts/multi_agent_offload.json`
- `scripts/run_multi_agent_offload.ps1`

## Practical Commands

Dry-run a tiny sample:

```powershell
pwsh -File scripts/run_multi_agent_offload.ps1 -DryRun -NoProcess -MaxFiles 3
```

Run processing without deleting:

```powershell
pwsh -File scripts/run_multi_agent_offload.ps1 -MaxFiles 3
```

Narrow to one source root:

```powershell
pwsh -File scripts/run_multi_agent_offload.ps1 -SourceRoot C:\Users\issda\OneDrive -MaxFiles 3
```

Delete only after verified destinations succeed:

```powershell
pwsh -File scripts/run_multi_agent_offload.ps1 -MaxFiles 3 -DeleteSource
```

## Evidence to Inspect

- `training/runs/multi_agent_offload/<run_id>/file_results.json`
- `training/runs/multi_agent_offload/<run_id>/run_summary.json`
- `training/runs/multi_agent_offload/<run_id>/method_registry.json`
- `training/runs/multi_agent_offload/<run_id>/training_rows.jsonl`

## Notes

- `rclone` targets are the preferred delete-safe path because the runner compares remote MD5 against the local bundle MD5.
- GitHub and Hugging Face targets are useful backups, but the current runner treats them as non-delete-authoritative because they are acknowledged uploads, not hash-verified remote copies.
