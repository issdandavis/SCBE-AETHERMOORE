# GitHub Remote Worker

This repo can use GitHub Actions as a free remote worker for heavier or longer
commands than this machine should carry locally.

## What This Gives You

- ad hoc remote command execution on `ubuntu-latest`
- Python and Node bootstrap when the repo has the expected files
- log capture in `artifacts/remote-worker/command.log`
- metadata and exit code capture
- artifact upload from `artifacts/remote-worker/**` plus an optional extra glob

This is a remote worker, not a persistent VM.

## Files

- workflow: `.github/workflows/free-remote-worker.yml`
- local dispatcher: `scripts/system/github_remote_worker.py`
- n8n dispatch sample: `workflows/n8n/github_remote_worker_payload.sample.json`

## Local Requirements

- `gh` CLI installed and authenticated
- admin or workflow-dispatch access to the target repo
- the workflow committed to the target GitHub repository

The dispatcher defaults to:

```text
issdandavis/SCBE-AETHERMOORE
```

Override that with:

```bash
export SCBE_GITHUB_REMOTE_REPO=owner/name
```

or pass `--repo owner/name`.

## Dry Run

```bash
.venv/bin/python scripts/system/github_remote_worker.py dispatch \
  "python -m pytest tests/aetherbrowser tests/aethermoore_constants" \
  --task-label remote-pytest-slice \
  --dry-run
```

## Dispatch A Real Job

```bash
.venv/bin/python scripts/system/github_remote_worker.py dispatch \
  "python -m pytest tests/aetherbrowser tests/aethermoore_constants" \
  --task-label remote-pytest-slice \
  --watch
```

By default this runs on the remote repo default branch. Use `--ref some-branch`
if you need a specific pushed branch.

The default artifact behavior only uploads `artifacts/remote-worker/**`.
Pass `--artifact-glob some/path/**` only when you intentionally want more files.

## Check Latest Status

```bash
.venv/bin/python scripts/system/github_remote_worker.py status
```

## Trigger From n8n Or Any Webhook Client

The sample payload in
`workflows/n8n/github_remote_worker_payload.sample.json` is intended for
GitHub `repository_dispatch`. Typical call:

```bash
gh api repos/issdandavis/SCBE-AETHERMOORE/dispatches \
  --method POST \
  --input workflows/n8n/github_remote_worker_payload.sample.json
```

## Notes

- `working_directory` is resolved relative to the repo root on the runner.
- `install_mode=auto` tries `requirements.txt`, editable Python install, and
  `npm install` when relevant files exist.
- `artifact_glob` is optional. Leave it empty unless you want extra artifacts
  beyond the remote-worker logs and metadata.
- If the command fails, the workflow still uploads logs and artifacts, then
  exits nonzero at the end.
