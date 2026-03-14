# 2026-03-14 Monorepo Baseline

## Goal

Do not split the work across more repos right now.

The safer model is:

- keep one working monorepo
- label the top-level roots clearly
- stop mixing canonical code, generated output, archives, and experiments
- make cleanup lane-by-lane instead of trying one giant rewrite

This gives you one place to work from without pretending every root has the same status.

## Baseline Facts

- Current local branch: `book/six-tongues-protocol-v1`
- Linked worktrees: `12`
- Repo state: heavily dirty
- Clone state: shallow
- `HEAD` lineage root commits: `4`
- Repo-wide reachable root commits across all refs: `6`
- Ordering snapshot artifact: `artifacts/repo-ordering/latest.json`
- Ordering snapshot script: `scripts/system/repo_ordering.py`

## Working Rule

Use a single-repo model with explicit lane labels:

- `canonical`
- `subproject-local`
- `content-publishing`
- `research-experimental`
- `generated-runtime`
- `legacy-readonly`
- `archive-snapshot`
- `external-vendored`
- `workspace-meta`

The important point is not to force a repo split.

The important point is to stop treating all roots as equal.

## Canonical Working Spine

These are the roots that should be treated as the main working spine unless a specific subproject says otherwise:

- `src/`
- `tests/`
- `docs/`
- `scripts/`
- `config/`
- `schemas/`
- root manifests:
  - `package.json`
  - `pyproject.toml`
  - `requirements-lock.txt`
  - `pytest.ini`
  - `tsconfig.json`
  - `vitest.config.ts`

## Subproject-Local Lanes

These are real working lanes, but they should not silently redefine the whole repo:

- `api/`
- `app/`
- `conference-app/`
- `dashboard/`
- `hydra/`
- `mcp/`
- `packages/`
- `python/`
- `services/`
- `shopify/`
- `ui/`
- `workflows/`

These can stay in the monorepo.

What they need is ownership and boundary discipline.

## Generated / Runtime Lanes

These should be treated as output zones, not canonical authored source:

- `training/`
- `.n8n_local_iso/`
- `artifacts/`
- `dist/`
- `node_modules/`
- `exports/`
- `backups/`
- `sealed_blobs/`
- `training-data/`
- `__pycache__/`
- `.pytest_cache/`
- `.pytest_tmp_hallpass_review/`

If these keep living beside source, that is fine.

But they need to be recognized as generated/runtime lanes first.

## Content / Publishing Lanes

- `content/`
- `articles/`
- `notes/`
- `paper/`
- `products/`
- `public/`
- `assets/`
- `policies/`

These are not “mess.”

They are a separate content surface and should stay separate from source cleanup decisions.

## Legacy / Archive Signals

These are the strongest candidates for `legacy-readonly` or `archive-snapshot` handling:

- `SCBE-AETHERMOORE-v3.0.0/`
- `scbe-aethermoore/`
- `spiralverse-protocol/`
- `symphonic_cipher/`
- `aether-browser/`

Also visible are root-vs-`src/` duplicate patterns that need explicit decisions instead of silent coexistence:

- `symphonic_cipher/` vs `src/symphonic_cipher/`
- `training/` vs `src/training/`
- `skills/` vs `src/skills/`
- `sealed_blobs/` vs `src/sealed_blobs/`
- `game/` vs `src/game/`
- `physics_sim/` vs `src/physics_sim/`

## Dirty Hotspots

Top dirty areas from the 2026-03-14 snapshot:

- `training/`: `1248`
- `.n8n_local_iso/`: `738`
- `content/`: `338`
- `artifacts/`: `273`
- `scripts/`: `168`
- `src/`: `101`
- stale tracked root `kindle-app/`: `79`
- stale tracked root `demo/`: `45`
- `docs/`: `31`
- `tests/`: `26`

This is why blind cleanup is dangerous.

Most of the noise is not in the canonical source spine.

## History Notes

The repo is shallow, so the oldest reachable commits are local boundaries, not guaranteed full history.

Current useful history markers:

- earliest reachable repo-wide root: `a8ba6447` on `2025-12-28`
- additional parentless roots on `2026-01-15`
- first major SCBE system root: `8a841566` on `2026-01-17`
- extra repo-wide roots also exist for side branches such as `gh-pages` and the shallow boundary

So the monorepo did not grow from one perfectly clean root.

It has merged lineages.

That matters for cleanup decisions.

## Safe Next Order

### Phase 1

- keep the single working repo model
- use `scripts/system/repo_ordering.py` as the baseline snapshot tool
- keep branch validation on `chore/branch-validation-bootstrap`

### Phase 2

- quarantine runtime/cache noise first
- identify tracked-but-missing renamed roots:
  - `kindle-app`
  - `demo`
  - `aetherbrowse`
  - `tmp`
- decide which duplicate roots are authoritative and which become `legacy-readonly`

### Phase 3

- only after the above, move or archive physical directories
- do not do mass deletes from the dirty tree

## Command Reference

Refresh the ordering snapshot:

```powershell
python scripts/system/repo_ordering.py
```

Refresh the clean branch validation lane:

```powershell
pwsh -File .\scripts\branch_validation.ps1 -Branch chore/branch-validation-bootstrap -Profile core
```

## Short Verdict

You do not need a multi-repo coding model.

You need one repo with explicit lane labels and a rule that only the canonical spine gets to define system-wide truth.
