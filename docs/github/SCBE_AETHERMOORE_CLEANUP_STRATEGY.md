# SCBE-AETHERMOORE GitHub Cleanup Strategy

Date: 2026-07-16

## Objective

Turn the current SCBE-AETHERMOORE worktree into clean, reviewable GitHub lanes
without losing user work, rewriting remote history, or mixing unrelated systems
into one pull request.

## Current operating rules

- Do not push directly to `main`.
- Do not pull, merge, rebase, reset, or clean while the worktree is dirty.
- Do not delete generated files until they are classified.
- Prefer focused branches and focused PRs over one large cleanup PR.
- Treat Kaggle artifacts, package archives, credentials, cache files, and synced
cloud material as high-risk until reviewed.

## Branch strategy

Use one branch per product lane:

| Lane | Branch name | Purpose |
| --- | --- | --- |
| AAP / Kaggle agent tooling | `codex/aap-geoseal-tools-20260716` | AAP package guard, probes, submission workflow |
| ARC / Rubix tooling | `codex/arc-rubix-geoseal-20260716` | ARC solver, dashboard, verify-search bridge |
| Package/release control | `codex/package-registry-control-20260716` | Package inventory, registry guard, release docs |
| AetherDesk UI/runtime | AetherDesk repo only | Keep separate from SCBE-AETHERMOORE |
| Research/proposals | `codex/research-proposals-20260716` | DARPA/CLARA/Biohub/writeup docs |
| Scratch quarantine | no PR until reviewed | Temporary probes, refute scripts, local archives |

## File classification policy

### Keep and stage in focused PRs

- Source scripts under `scripts/system/` that have stable CLI value.
- Docs under `docs/` that explain a command, lane, or reproducible result.
- Harness exports in `src/coding_spine/agent_tool_bridge.py`.
- GeoSeal CLI routes in `bin/geoseal.cjs`.
- Tests only when they are tied to the same lane.

### Quarantine before deciding

- `_tmp_*.py`, `_verify_*.py`, `_probe*.py`, `_dbg.py`, `_bypass.py`.
- Downloaded competition zips and large local artifacts.
- Generated `reports/` output unless it is intentionally used as a receipt.
- `.tgz` package tarballs unless they are release artifacts.

### Do not commit by default

- Local cache folders.
- Raw Kaggle downloads.
- Secret-bearing config or exports.
- OneDrive/Dropbox/GitHub personal data dumps.
- Broad generated dashboards unless they are explicitly release assets.

## PR grouping

### PR 1: AAP GeoSeal tooling

Likely files:

- `bin/geoseal.cjs`
- `src/coding_spine/agent_tool_bridge.py`
- `scripts/system/aap_family_probe.py`
- `scripts/system/aap_blend_probe.py`
- `scripts/system/aap_package_submit.py`
- `scripts/system/aap_local_meta_eval.py`
- `scripts/system/aap_validation_scaffold.py`
- `docs/AAP_FAMILY_PROBE.md`
- `docs/AAP_BLEND_PROBE.md`
- `docs/AAP_GEOSEAL_PACKAGE_GUARD.md`

Goal: make Autonomous Agent Prediction packaging, probing, and submission
repeatable from GeoSeal.

### PR 2: ARC / Rubix reusable tooling

Likely files:

- `scripts/system/arc_rubix_solver.py`
- `scripts/system/arc_rubix_score.py`
- `scripts/system/arc_rubix_dashboard.py`
- `scripts/system/arc_rubix_loop.py`
- `scripts/system/geoseal_verify_search.py`
- `docs/ARC_RUBIX_GEOSEAL.md`
- `docs/GEOSEAL_VERIFY_SEARCH.md`
- `bin/geoseal.cjs`
- `src/coding_spine/agent_tool_bridge.py`

Goal: preserve NeuroGolf lessons as reusable local ARC/verify-search tooling.

### PR 3: package registry / release control

Likely files:

- `scripts/system/package_registry_control.py`
- `docs/system/package_release_control.md`
- `bin/geoseal.cjs`
- any related package metadata changes after review

Goal: make npm/PyPI package status inspectable without accidental publishing.

### PR 4+: unrelated lanes

Everything else should be split only after inspection:

- Code Prism changes.
- Loom/typewriter/material-flow changes.
- Harmonic/topological linearization changes.
- DARPA/CLARA proposal docs.
- Biohub tracking work.
- Aether browser probes.

## Commit policy

Use conventional commits:

```text
feat(geoseal): add AAP package guard
feat(kaggle): add AAP family and blend probes
feat(arc): add Rubix local loop and dashboard
docs(github): add SCBE cleanup strategy
```

Each commit should include:

- What changed.
- Which command validates or exercises it.
- Whether external submission was attempted.
- Whether generated artifacts are intentionally included.

## Verification policy

Use three gates:

1. `compile/package gate`: file layout and syntax.
2. `local runtime gate`: run the command or local mini-eval.
3. `external result gate`: Kaggle/GitHub/registry status when applicable.

Do not claim success from gate 1 alone.

## Immediate next steps

1. Create a new branch for AAP/GeoSeal work from current state.
2. Stage only AAP files and shared GeoSeal/harness files.
3. Review `git diff --cached` before commit.
4. Commit AAP lane.
5. Repeat for ARC/Rubix lane.
6. Quarantine scratch files with an explicit keep/delete list before cleanup.

No destructive cleanup should happen until these branches and commits exist.
