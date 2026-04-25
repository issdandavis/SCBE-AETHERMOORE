# Release Readiness Tracker - 2026-04-25

This tracker applies the current GitHub release standard to the narrow SCBE-AETHERMOORE trunk selected in `docs/map-room/SYSTEM_RELEASE_PACKAGE_REVIEW_2026-04-25.md`.

Authority:

- `docs/specs/GITHUB_RELEASE_STANDARD.md`
- `docs/map-room/SYSTEM_RELEASE_PACKAGE_REVIEW_2026-04-25.md`

## Candidate

- Candidate: `scbe-aethermoore@4.0.3` narrow trunk release candidate
- Evidence run: `artifacts/release-evidence/20260425T145633/summary.json`
- Branch: `feature/cli-code-tongues`
- Scope decision: package + CLI + docs only
- GitHub issue: `https://github.com/issdandavis/SCBE-AETHERMOORE/issues/1149`

## Release Objects In Scope

| Object | Status | Evidence |
|---|---|---|
| npm package | `pass` | `npm run clean:release`, `npm run build`, `npm run typecheck`, `npm test`, `npm run publish:check:strict` |
| Python package | `pass` | `python -m build --sdist --wheel --outdir artifacts/pypi-dist`, `python scripts/pypi_dist_guard.py --dist-dir artifacts/pypi-dist` |
| GitHub Pages / docs | `pass` | `python scripts/system/verify_docs_publish_surface.py --root docs --require index.html --require support.html --require redteam.html` |
| CLI / operator tooling | `pass` | `python scripts/scbe-system-cli.py --repo-root . agentbus run ... --json` |
| Competitive wedge | `pass` | `python scripts/benchmark/agentbus_competitive_wedge.py --run-id release-wedge-20260425` |

## Release Objects Out Of Scope

| Object | Reason |
|---|---|
| backend API | Must remain preview until a black-box health/auth/action smoke path is attached. |
| frontend app | Must remain preview until it has an intentional production build artifact and backend target proof. |
| buyer deliverables | Separate downloadable product pack, not the same as runtime release. |
| training/model artifacts | Internal model-development assets unless promoted through manifest and eval gates. |
| Kaggle/Colab notebooks | Remote compute support lane, not a public release object. |
| Docker/deploy | Needs one blessed deploy path per release object before promotion. |

## Evidence Summary

| Step | Exit | Duration ms | Log |
|---|---:|---:|---|
| npm clean release | 0 | 4358 | `artifacts/release-evidence/20260425T145633/npm-clean-release.log` |
| npm build | 0 | 8600 | `artifacts/release-evidence/20260425T145633/npm-build.log` |
| npm typecheck | 0 | 2359 | `artifacts/release-evidence/20260425T145633/npm-typecheck.log` |
| npm test | 0 | 30798 | `artifacts/release-evidence/20260425T145633/npm-test.log` |
| npm publish check strict | 0 | 4703 | `artifacts/release-evidence/20260425T145633/npm-publish-check-strict.log` |
| PyPI build | 0 | 48460 | `artifacts/release-evidence/20260425T145633/pypi-build.log` |
| PyPI guard | 0 | 486 | `artifacts/release-evidence/20260425T145633/pypi-guard.log` |
| docs publish surface | 0 | 355 | `artifacts/release-evidence/20260425T145633/docs-publish-surface.log` |
| agent-bus user smoke | 0 | 1128 | `artifacts/release-evidence/20260425T145633/agentbus-user-smoke.log` |
| competitive wedge benchmark | 0 | not captured in release-evidence run | `artifacts/benchmarks/agentbus_competitive_wedge/release-wedge-20260425/report.json` |

## Smoke Details

### Competitive Wedge

Command:

```powershell
python scripts/benchmark/agentbus_competitive_wedge.py --run-id release-wedge-20260425
```

Result:

- Decision: `PASS`
- Direct baseline average: `0.2727`
- SCBE agent-bus average: `1.0`
- Absolute lift: `0.7273`
- Relative lift: `266.7%`
- Bus wins: `5 / 5`
- Report: `artifacts/benchmarks/agentbus_competitive_wedge/release-wedge-20260425/report.json`

Claim boundary:

- Supports releasing the agent-bus as a governed local workflow surface.
- Does not prove that SCBE generates better code than frontier coding agents.
- Next benchmark must use real patch tasks and compare passed tests, edit quality, and time-to-fix.

### npm Package

Command:

```powershell
npm run publish:check:strict
```

Result:

- Tarball: `scbe-aethermoore-4.0.3.tgz`
- Entries: `1271`
- Guard: package contents clean

### Python Package

Command:

```powershell
python scripts/pypi_dist_guard.py --dist-dir artifacts/pypi-dist
```

Result:

- Artifacts: `2`
- Violations: `0`

### Docs

Command:

```powershell
python scripts/system/verify_docs_publish_surface.py --root docs --require index.html --require support.html --require redteam.html
```

Result:

- `index.html`: ok
- `support.html`: ok
- `redteam.html`: ok

### CLI / Agent Bus

Command:

```powershell
python scripts/scbe-system-cli.py --repo-root . agentbus run --task "Release evidence agent-bus user smoke" --operation-command "korah aelin dahru" --task-type coding --series-id release-evidence-agentbus --privacy local_only --budget-cents 0 --dispatch --json
```

Result:

- Selected provider: `offline`
- Operation shape root: `12026`
- Operation signature: `c176ca9a2f3473c6d643c1ef8b000c7a`
- Dispatch result: deterministic offline worker accepted the task
- Artifacts:
  - `artifacts/agent_bus/mirror_room/release-evidence-agentbus/latest_round.json`
  - `artifacts/file_tracking/latest/file_tracking_snapshot.json`
  - `artifacts/file_tracking/latest/changed_files.json`
  - `artifacts/agent_bus/user_runs/release-evidence-agentbus/observable_state.json`
  - `artifacts/agent_bus/user_runs/release-evidence-agentbus/run_summary.json`

## Current Blockers

### Blocking For Full-Stack Release

- Backend API is not promoted because the release evidence does not include a live external health/auth/action smoke.
- Frontend app is not promoted because the release evidence does not include a production asset build and app-to-backend smoke.
- Docker/deploy is not promoted because no single blessed stack was selected for this candidate.

### Not Blocking For Narrow Trunk Release

- Dirty worktree outside this release scope.
- Training/model accumulation.
- Buyer deliverable refresh.
- Kaggle/Colab archive cleanup.
- Backend/frontend preview status.

## Release Decision

Status: `ready-for-release-issue`

This candidate is ready to open/update a GitHub release readiness issue for the declared narrow trunk:

- npm package
- Python package
- GitHub Pages / docs
- CLI / operator tooling

It is not ready to claim full-stack production readiness.

## Next Action

Open a Release Readiness issue using `.github/ISSUE_TEMPLATE/release_readiness.yml` and paste this evidence.

If the issue is opened manually, attach this tracker and the generated evidence directory path. If opened with GitHub CLI, use this file as the issue body and keep the issue title scoped:

`[Release]: scbe-aethermoore@4.0.3 narrow trunk`
