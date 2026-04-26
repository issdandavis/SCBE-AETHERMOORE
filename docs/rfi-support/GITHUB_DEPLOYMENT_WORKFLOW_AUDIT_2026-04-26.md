# GitHub Deployment and Workflow Audit

Date: 2026-04-26
Branch reviewed: `feature/cli-code-tongues`

## Purpose

Keep the GitHub-facing repo surface functional, cheap to operate, and honest. Every workflow should be one of these:

- A functional gate that protects code, deployment, security, or docs.
- A manual operator tool with a clear trigger and expected output.
- A true documentation or maintenance workflow that records useful state.

Anything else should be consolidated, disabled, or moved out of the main workflow set.

## Current GitHub State

### Deployments

GitHub Pages is currently built and public.

- Environment: `github-pages`
- Source: `main` / `/docs`
- Site URL: `https://aethermoore.com/SCBE-AETHERMOORE/`
- Latest checked deployment: success on 2026-04-26 from deployment `4487441798`
- HTTPS: enforced
- Certificate: approved, expires 2026-07-05

### Current Branch Push Checks

Recent pushes on `feature/cli-code-tongues` ran successfully for:

- `Conflict Marker Guard`
- `Automatic Dependency Submission (Python)`

### Active Failure Found

The failing GitHub Actions surface found in the recent run list was:

- Workflow: `CI`
- Run: `24959535386`
- Branch: `add-t-cell-analog-schematic`
- Event: `pull_request`
- Failed jobs:
  - `Test (Node 20)`
  - `Test Python Components`
  - `Lint and Format Check`

Root causes found from logs:

- `npm run build` called missing `scripts/write_root_index_dts.mjs`.
- Python test collection imported `liboqs-python`, which raised `SystemExit` because no OQS shared libraries were present.
- Format check failed on that PR branch before later lint steps ran.

Fixes applied on `feature/cli-code-tongues`:

- Added `scripts/write_root_index_dts.mjs`.
- Updated `src/crypto/pqc_liboqs.py` so unavailable `liboqs` falls back to lower proof tiers instead of aborting pytest collection.

Local verification:

```powershell
npm run build
python -m pytest tests/crypto/test_pqc_liboqs_status.py -q
kubectl kustomize --load-restrictor LoadRestrictionsNone k8s/overlays/il5-govcloud
```

All three passed locally.

## Workflow Surface Classification

### Keep as Primary Functional Gates

These are directly useful and should remain GitHub-visible:

- `.github/workflows/ci.yml` — main build/test gate.
- `.github/workflows/conflict-marker-guard.yml` — cheap safety gate.
- `.github/workflows/scbe.yml` — SCBE validation gate.
- `.github/workflows/coherence-gate.yml` — semantic/governance gate.
- `.github/workflows/premerge-triage.yml` — PR triage before merge.
- `.github/workflows/codeql-analysis.yml` or `.github/workflows/codeql.yml` — keep one CodeQL authority, not both.
- `.github/workflows/pages-auto-deploy.yml` or `.github/workflows/pages-deploy.yml` — keep one Pages deployment authority, not both.

### Keep as Manual or Scheduled Operator Tools

These are useful if their outputs remain visible and bounded:

- `.github/workflows/workflow-audit.yml`
- `.github/workflows/weekly-repo-health.yml`
- `.github/workflows/weekly-gov-contracts-check.yml`
- `.github/workflows/weekly-hf-sync.yml`
- `.github/workflows/free-remote-worker.yml`
- `.github/workflows/cloud-kernel-data-pipeline.yml`

Rule: these should be `workflow_dispatch` first, scheduled only if they produce a useful artifact or issue.

### Consolidation Candidates

These appear overlapping or too numerous for a clean main repo:

- CodeQL duplication: `.github/workflows/codeql-analysis.yml`, `.github/workflows/codeql.yml`
- Pages deployment duplication: `.github/workflows/pages-auto-deploy.yml`, `.github/workflows/pages-deploy.yml`
- Security scan overlap: `security-checks.yml`, `daily-secret-scan.yml`, `secret-rotation-audit.yml`, `weekly-security-audit.yml`, `weekly-security-scan.yml`
- Test overlap: `ci.yml`, `daily-tests.yml`, `scbe-tests.yml`, `scbe.yml`
- Issue/PR automation overlap: `ai-issue-summary.yml`, `auto-triage.yml`, `issue-triage.yml`, `greetings.yml`, `labeler.yml`
- Auto-merge overlap: `auto-approve-trusted.yml`, `auto-merge-enable.yml`, `auto-merge.yml`, `auto-rebase-prs.yml`, `auto-resolve-conflicts.yml`

## Recommended Target Shape

Reduce GitHub workflows to a smaller set:

1. `ci.yml` — build, typecheck, unit tests, focused Python tests.
2. `security.yml` — secret scan, dependency audit, CodeQL, vulnerability reporting.
3. `pages.yml` — one Pages deploy path.
4. `pr-governance.yml` — conflict marker guard, coherence gate, triage labels.
5. `nightly-maintenance.yml` — repo health, training validation, link checks.
6. `manual-operators.yml` — free/included cloud helpers for Hugging Face, Kaggle, Colab, and dispatch-only jobs.

## Cost Rule

Default operating rule:

- Local first.
- GitHub Actions only for cheap gates and public deployment.
- Free or already-paid cloud lanes only: GitHub included minutes, Hugging Face plan, Kaggle, Colab.
- No managed Kubernetes cluster, GPU cloud, or paid deployment target unless explicitly approved.

## Next Cleanup Pass

Do not delete workflows blindly. For each consolidation group:

1. Pick the authority workflow.
2. Move unique useful steps from duplicates into the authority workflow.
3. Disable or remove duplicate schedules.
4. Keep manual dispatch for tools that are useful but not worth scheduled compute.
5. Update this audit after each pass.

