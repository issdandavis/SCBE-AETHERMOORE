---
name: multi-agent-cloud-offload
description: Deterministically sort, bundle, verify, and offshore local files through multiple AI/model lanes while capturing training rows and method evidence. Use when Codex needs to inventory folders, batch-process files, upload them to cloud targets such as rclone-backed Google Drive, Hugging Face, or GitHub, and only delete sources after the configured number of verified targets succeed.
---

# Multi Agent Cloud Offload

Use this skill when file loss would be unacceptable and the task requires a strict inventory-to-verification pipeline rather than ad hoc copying.

## Core Workflow

1. Read the control files first:
   - `scripts/multi_agent_offload.py`
   - `scripts/multi_agent_offload.json`
   - `scripts/run_multi_agent_offload.ps1`
2. Treat source deletion as blocked until destination verification succeeds.
3. Prefer `rclone` targets with remote hash verification for delete authority.
4. Keep `required_verified_targets` at `2` or higher unless the user explicitly accepts lower durability.
5. Run a dry-run before any live offload:

```powershell
pwsh -File scripts/run_multi_agent_offload.ps1 -DryRun -NoProcess -MaxFiles 3
```

6. Run a live non-deleting pass before any delete pass:

```powershell
pwsh -File scripts/run_multi_agent_offload.ps1 -MaxFiles 3
```

7. Use `-DeleteSource` only after the run artifacts show the required number of verified targets for each file:

```powershell
pwsh -File scripts/run_multi_agent_offload.ps1 -MaxFiles 3 -DeleteSource
```

## Verification Rule

- Never delete after a plain copy or API acknowledgement alone.
- Delete only when the run output proves the configured verification gate passed.
- The default runner writes per-file evidence into:
  - `training/runs/multi_agent_offload/<run_id>/file_results.json`
  - `training/runs/multi_agent_offload/<run_id>/run_summary.json`
  - `training/runs/multi_agent_offload/<run_id>/method_registry.json`

## Training Capture

Every processed file should produce a training/example row at:

- `training/runs/multi_agent_offload/<run_id>/training_rows.jsonl`

Use those rows to curate later uploads to Hugging Face datasets. Treat them as audit artifacts first and training data second.

## Adjustment Points

- Change source folders, lane models, and shipping targets in `scripts/multi_agent_offload.json`.
- Use `--source-root` overrides for narrow test passes.
- Use `--targets` to constrain a run to specific destinations.
- Use `--reprocess` when the routing policy or model mix changed and old successes are no longer authoritative.

## Reference

Read `references/runbook.md` when changing durability policy, target ordering, or the live run procedure.
