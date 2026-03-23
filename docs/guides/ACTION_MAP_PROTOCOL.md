# Action Map Protocol

Use the action-map lane when you want a repeatable end-to-end workflow trace instead of loose notes or one-off summaries.

It records:

- `start`, `step`, and `close` events for one run
- changed files, touched layers, tools, skills, proof, and artifacts
- a compiled `action_map.json`
- training-ready `training_rows.jsonl`
- a small `run_summary.json`

## Fast Commands

From the command center:

- `haction-start <task>`
- `haction-step <run_id> <summary>`
- `haction-close <run_id> <summary>`
- `haction-build <run_id>`
- `haction-status [run_id]`

Direct CLI:

```powershell
python scripts/system/action_map_protocol.py start --task "repo cleanup"
python scripts/system/action_map_protocol.py step --run-id <run_id> --summary "sorted core vs archive lanes"
python scripts/system/action_map_protocol.py close --run-id <run_id> --summary "cleanup map compiled" --status completed
python scripts/system/action_map_protocol.py build --run-id <run_id>
python scripts/system/action_map_protocol.py status --run-id <run_id>
```

## Output Layout

Runs land under `training/runs/action_maps/<run_id>/`:

- `events.jsonl`: append-only event log
- `action_map.json`: compiled workflow map
- `training_rows.jsonl`: training-ready workflow rows
- `run_summary.json`: quick status/paths

## Why It Exists

This is the repo-local answer to command telemetry capture:

- `command center` keeps fast human/operator entrypoints
- `cross-talk` remains the multi-agent relay surface
- `action maps` preserve the workflow trace in a training-friendly form
- `cleanup work` can now produce a governed map instead of disappearing into chat history

## Cleanup Use

For cleanup or repo triage runs, pair this with `python scripts/system/repo_ordering.py`.

The compiled action map will attach:

- current git dirty-root snapshot
- repo-ordering categories when `artifacts/repo-ordering/latest.json` exists
- a `cleanup_focus` block so the next pass can target the largest active buckets first
