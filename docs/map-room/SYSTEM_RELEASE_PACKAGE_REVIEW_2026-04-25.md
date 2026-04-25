# System Release Package Review - 2026-04-25

## Purpose

Review the current SCBE-AETHERMOORE system files and release packages, then define the practical release plan by surface.

This is an operator-facing plan. It does not declare the whole repository production-ready. The repository is currently a working lab plus product repo with multiple release surfaces.

## Current Release Surfaces

| Surface | Current State | Evidence | Release Role |
|---|---|---|---|
| npm package | Guarded and packable | `artifacts/npm-pack/pack.json`, `scripts/npm_pack_guard.js` | Public SDK / GeoSeal CLI lane |
| Python package | Guarded and buildable | `artifacts/pypi-dist/`, `scripts/pypi_dist_guard.py` | Python runtime/API/operator package lane |
| GitHub Pages / docs | Publish surface present | `docs/index.html`, `docs/support.html`, `docs/redteam.html`, `scripts/system/verify_docs_publish_surface.py` | Public proof and product explanation lane |
| Backend API | Partial release surface | `src/api/main.py`, `api/main.py`, release tracker | Needs deploy/auth smoke discipline before public production claims |
| Frontend app | Prototype/partial | `app/`, `docs/`, release tracker | Needs intentional build artifact and backend target proof |
| CLI / operator tooling | Active and improving | `scripts/scbe-system-cli.py`, `bin/geoseal.cjs`, `scripts/system/agentbus_pipe.mjs` | Best current operational control surface |
| Buyer deliverables | Structured but older | `deliverables/SCBE_Production_Pack/` | Sellable template/product pack, separate from core runtime package |
| Training/model artifacts | Active accumulation | `training-data/`, `artifacts/training_*`, `artifacts/ai_training_consolidation/` | Model-development surface, not public release surface by default |
| Kaggle/Colab notebooks | Consolidated but not all active | `docs/map-room/KAGGLE_KERNEL_CONSOLIDATION_2026-04-25.md` | Remote compute lane; keep only current active training notebooks |
| Docker/deploy | Multiple candidate stacks | `Dockerfile*`, `docker-compose*.yml`, `deploy/`, `k8s/` | Needs one blessed deploy path per release object |

## Verified Checks From This Review

```powershell
node scripts\npm_pack_guard.js --pack-json artifacts\npm-pack\pack.json
```

Result: npm tarball guard passed for `scbe-aethermoore-4.0.3.tgz`, 1267 entries, no banned files reported.

```powershell
python scripts\pypi_dist_guard.py --dist-dir artifacts\pypi-dist
```

Result: PyPI guard passed for 2 artifacts, 0 violations.

```powershell
python scripts\system\verify_docs_publish_surface.py --root docs --require index.html --require support.html --require redteam.html
```

Result: docs publish surface verified.

## Main Finding

The repository has usable release pieces, but the release story is too broad. The next release should not try to ship "everything." It should ship one tight trunk and treat everything else as downstream branches.

The best trunk right now is:

1. `npm package` for public TypeScript/GeoSeal SDK use.
2. `Python package` for local/runtime/operator use.
3. `CLI / agent-bus endpoint` for actual work execution.
4. `docs` for proof, support, and explanation.

Backend API, frontend app, buyer packs, training, Kaggle, and Docker should remain secondary release objects until each has a clean smoke path.

## Problems To Fix Before A Public Release

### 1. Dirty Worktree Is Too Large

The repo has many modified, deleted, and untracked files across docs, notes, source, tests, training, and proposal surfaces. This makes release evidence hard to trust.

Plan:

- Freeze a release branch from the current feature branch only after deciding what belongs in this release.
- Do not stage broad docs or notes changes.
- Use exact-path commits only.
- Treat deleted proposal files as high-risk until private packet routing is confirmed.

### 2. Public Package Surface Is Still Broad

The npm package guard passes, but the tarball still includes `dist/packages/kernel` and many compiled internals. That may be valid, but it should be an intentional SDK boundary, not accidental.

Plan:

- Define `public_api_v1`: root, `harmonic`, `crypto`, `tokenizer`, `spiralauth`, `governance`, `geoseal` CLI.
- Move experimental exports behind non-default subpaths or keep them undocumented.
- Add one temp-install smoke per intended export.

### 3. Python Package Ships A Large Runtime Surface

The PyPI guard passes, but `pyproject.toml` includes broad packages such as `api*`, `python*`, `src.*`, `schemas`, and several experimental lanes.

Plan:

- Keep PyPI as an operator/runtime package, not a minimal SDK, unless intentionally split later.
- Add smoke tests for installed console scripts: `scbe`, `geoseal`, `scbe-system`, `scbe-code-prism`.
- Decide whether `api*` belongs in the first public PyPI package or should wait.

### 4. Backend And Frontend Are Not The First Release Trunk

The release tracker already marks backend API and frontend app as partial. They should not block a package/docs release unless the release claims them.

Plan:

- Scope first release notes as package + CLI + docs.
- Keep API/frontend as "preview" unless app-to-backend smoke is attached.
- Add one black-box health/auth/action smoke before promoting backend.

### 5. Buyer Deliverables Need Product Alignment

`deliverables/SCBE_Production_Pack` is structured, but dated `2026-03-24`. It contains useful packs: governance toolkit, HYDRA templates, n8n workflows, and content spin engine. It is a sales/download product, not the same as the runtime release.

Plan:

- Keep this as `buyer_pack_v1`.
- Update only the buyer start guide, inventory, and validation checklist.
- Do not mix runtime code release notes into buyer pack docs.

### 6. Training Artifacts Need Bucket Promotion Gates

Training data and model artifacts are active but should not drive the public release. They need buckets by purpose:

- `coding_model`
- `operator_agent_bus`
- `governance_security`
- `aligned_foundations`
- `research_bridge`
- `commerce_product`

Plan:

- Promote only regularized datasets with manifest, train/eval split, source bucket, and quality score.
- Keep raw exports and old notebooks out of release artifacts.
- Use Kaggle only for current active training kernels.

## Release Plan

### Phase 1 - Stabilize The Trunk

Goal: one releasable package/docs/CLI surface.

Actions:

- Run focused checks: `npm run publish:check:strict`, `python scripts/pypi_dist_guard.py --dist-dir artifacts/pypi-dist`, docs publish check, agent-bus endpoint smoke.
- Create a release issue using the GitHub release standard.
- Attach command evidence and artifact paths.
- Freeze the release scope to npm, PyPI, CLI/operator, docs.

Exit criteria:

- Package guards pass.
- Temp install smoke passes for npm and PyPI.
- `agentbus run` works from the CLI as a user endpoint.
- Docs support/redteam/index pages exist.

### Phase 2 - Split Release Objects By Purpose

Goal: stop every branch from pretending to be part of the same release.

Actions:

- Mark backend API and frontend app as preview unless smoke evidence exists.
- Mark buyer deliverables as a separate downloadable product pack.
- Mark training/model outputs as internal model-development assets.
- Mark Kaggle/Colab as remote compute support, not release packages.

Exit criteria:

- Release notes list in-scope and out-of-scope objects.
- Each object has one owner file and one smoke command.

### Phase 3 - Tighten Package Boundaries

Goal: reduce accidental public surface.

Actions:

- Review `package.json` exports and `files`.
- Review `pyproject.toml` include/exclude rules.
- Add a generated package manifest diff to each release.
- Add tests that fail if unexpected package paths appear.

Exit criteria:

- npm and PyPI manifests are both intentional.
- No raw training, private proposal, local secret, external repo, or test cache material ships.

### Phase 4 - Promote Backend/API Only After Black-Box Smoke

Goal: only claim API readiness when an outside user can use it.

Actions:

- Start the selected API surface.
- Hit health, auth failure, auth success, and one real action route.
- Document required environment variables.
- Decide whether `api/main.py` or `src/api/main.py` is the public runtime for this release.

Exit criteria:

- One command starts the service.
- One script verifies it from the outside.
- No hidden `.secrets` dependency.

### Phase 5 - Training And Model Consolidation

Goal: make training useful without polluting release.

Actions:

- Keep active Kaggle set to the four current coding/training kernels.
- Archive old notebooks after local pull.
- Promote regularized datasets by purpose bucket.
- Evaluate merged coding model against baseline tasks before adding another dataset.

Exit criteria:

- Each model bucket has train/eval split, manifest, and evaluation record.
- No new dataset is added unless it improves a target score or fills a missing capability.

## Recommended Immediate Next Actions

1. Create a release issue from `.github/ISSUE_TEMPLATE/release_readiness.yml`.
2. Run a fresh release evidence pass on this branch.
3. Commit or quarantine only release-scope files.
4. Produce release notes for `package + CLI + docs`, not full-stack production.
5. Start a separate buyer-pack refresh after the runtime package release is stable.

## Operator Rule

Do not release from the whole repo narrative. Release from declared objects.

For the next release, the declared objects should be:

- npm package
- Python package
- CLI / agent-bus operator tooling
- GitHub Pages / docs

Everything else is a branch, not the trunk.
