# GitHub And CI Operations

This guide covers PR visibility, workflow audit, and repo health from the local stack.

## Core Files

- `scripts/system/github_workflow_audit.py`
- `.github/workflows/`
- `docs/operations/2026-03-16-github-portfolio-map.md`

## Fast Commands

### Portfolio and PR state

```powershell
gh repo list issdandavis --limit 100
gh pr list --repo issdandavis/SCBE-AETHERMOORE --state all --limit 20
gh pr view 550 --repo issdandavis/SCBE-AETHERMOORE
```

### Workflow state

```powershell
gh run list --repo issdandavis/SCBE-AETHERMOORE --limit 20
python scripts/system/github_workflow_audit.py
```

## What The Audit Script Does

- reads workflow inventory
- reads recent runs
- triages failures into green / yellow / red
- suggests likely fix classes

## Portfolio Rule

Use `SCBE-AETHERMOORE` as the live integration surface. Use extracted repos like `aetherbrowser`, `phdm-21d-embedding`, `six-tongues-geoseal`, and `spiralverse-protocol` as module faces, not parallel mainlines.

## When To Use This Lane

- A PR is open and you need to know whether the repo is green.
- Branches and side repos are drifting.
- You want a fast health check without manually clicking through GitHub.
