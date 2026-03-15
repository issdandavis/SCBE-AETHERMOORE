# AI Terminal GitHub Management

This is the terminal-first workflow for keeping one repo usable while still preserving evidence, outputs, and cloud state.

## What This Solves

- tells you where to run the sweep from
- generates one sweep summary for local repo state
- optionally captures GitHub repo inventory
- gives AI agents one governed packet instead of letting them collide
- keeps outputs and caches separate from source code

## Where To Run It From

Run from the repo root:

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
python .\scripts\system\run_github_sweep.py --repo-root . --include-github
```

If you are in another shell location, this also works:

```powershell
python C:\Users\issda\SCBE-AETHERMOORE\scripts\system\run_github_sweep.py --repo-root C:\Users\issda\SCBE-AETHERMOORE --include-github
```

## What It Writes

Outputs go to:

- `artifacts/agent-sweeps/github_sweep_latest.json`
- `artifacts/agent-sweeps/github_repo_inventory_latest.json` when `--include-github` is used
- `artifacts/repo-hygiene/latest_report.json` when `repo_hygiene.py` exists in the target repo

## Local Cleanup Loop

Use this order:

1. Sweep and classify

```powershell
python .\scripts\system\run_github_sweep.py --repo-root . --include-github
```

2. If present, run repo hygiene report

```powershell
python .\scripts\system\repo_hygiene.py report
```

3. Snapshot before pruning

```powershell
python .\scripts\system\repo_hygiene.py snapshot
```

4. Only prune safe untracked noise

```powershell
python .\scripts\system\repo_hygiene.py clean --apply
```

## How To Think About Dirty Files

Dirty does not mean bad. It means your working tree differs from the last commit.

There are four common classes:

- source of truth
  - code, docs, schemas, workflow templates
- evidence and outputs
  - artifacts, training records, reports
- cache and local app state
  - reproducible and usually not worth tracking
- machine-local or temporary state
  - useful on one PC, not useful as canonical repo history

Examples:

- `src/`, `tests/`, `docs/`, `scripts/` usually stay in repo
- `artifacts/` and large `training/` outputs usually need archive/cloud strategy
- `.n8n_local_iso/.cache/n8n/...` is cache, not canonical workflow knowledge

## GitHub Management For AI Agents

First confirm auth:

```powershell
gh auth status
```

List repos:

```powershell
gh repo list issdandavis --limit 100
```

Open PR queue:

```powershell
gh pr list --limit 50
```

Open issues:

```powershell
gh issue list --limit 50
```

The rule is:

- do discovery first
- classify second
- assign agent lanes third
- edit only after ownership is explicit

## HYDRA Roundtable Rules

Use the mirrored skill:

- `skills/codex-mirror/scbe-github-sweep-sorter`

Use it with:

- `scbe-ai-to-ai-communication`

Default patterns:

- `scatter`
  - discovery across many repos or many alerts
- `hexagonal-ring`
  - normal collaborative coding on one shared repo
- `tetrahedral`
  - smaller high-risk coding packets
- `ring`
  - ordered approvals and critical actions

Default quorum guidance:

- low-risk discovery: `3/6`
- medium-risk changes: `4/6`
- critical actions: `5/6`

## Naming And Organization Rules

Do not mass-rename the repo in one pass.

Do this instead:

1. classify
2. move caches out of the way
3. archive outputs to cloud or a dedicated data lane
4. rename source paths only when a stable boundary is clear

Good rename candidates are:

- vague root names
- legacy snapshot roots
- duplicated app names
- generated folders pretending to be source

Bad rename candidates are:

- active code paths with imports
- public package names
- workflow files currently in use

## Cloud Organization

Use GitHub for:

- canonical source
- issues, PRs, labels, role topics
- private asset repos when needed

Use cloud/archive storage for:

- bulky artifacts
- large training corpora
- media outputs
- reproducible reports that do not need to live in main source history

## Current Reality

This repo is not “bad.” It is overloaded.

The fix is not deletion by panic. The fix is:

- source in repo
- outputs archived
- cache ignored
- agents routed through one packet lane
