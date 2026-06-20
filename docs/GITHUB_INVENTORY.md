# GitHub Inventory

Status: generated from local checkout inspection on 2026-06-14.

## Repository Identity

- Remote: `https://github.com/issdandavis/SCBE-AETHERMOORE.git`
- Current branch: `main`
- Current commit: `cdd71a3f4`
- Last commit: `feat(cli): undo (past tense) + ask/do split`
- Upstream delta: local `main` is 6 commits ahead of `origin/main`, 0 behind.

## Tracked File Inventory

Total tracked files: 6,832.

Largest tracked top-level areas:

| Path | Files |
|---|---:|
| `src/` | 1,056 |
| `tests/` | 1,033 |
| `scripts/` | 884 |
| `kindle-app/` | 584 |
| `external/` | 465 |
| `docs/` | 434 |
| `packages/` | 253 |
| `content/` | 247 |
| `notes/` | 227 |
| `config/` | 100 |
| `symphonic_cipher/` | 96 |
| `skills/` | 95 |
| `.github/` | 91 |
| `api/` | 82 |
| `agents/` | 73 |
| `python/` | 68 |

Common tracked extensions:

| Extension | Files |
|---|---:|
| `.py` | 2,748 |
| `.md` | 1,377 |
| `.ts` | 695 |
| `.png` | 495 |
| `.json` | 379 |
| `.js` | 136 |
| `.ps1` | 131 |
| `.yaml` | 125 |
| `.html` | 109 |
| `.yml` | 103 |

## Primary Surfaces

- Governance/runtime core: `src/index.ts`, `src/harmonic/`, `src/crypto/`,
  `src/governance/`, `packages/kernel/`
- Python reference/runtime: `python/scbe/`, `src/api/`, `api/`
- Tokenizer/tongues/compiler: `src/tokenizer/`, `src/tongues/`,
  `src/ca_lexicon/`, `python/scbe/tongue_isa.py`
- Agentic/operator systems: `src/fleet/`, `packages/agent-bus/`,
  `packages/agent-bus-py/`, `agents/`, `.agents/skills/`
- Product and app lanes: `public/`, `app/`, `apps/`, `products/`,
  `aether-browser/`, `aetherdesk/`, `kindle-app/`
- Research/training: `notes/`, `notebooks/`, `training/`, `training-data/`,
  `scripts/train/`, `scripts/eval/`, `scripts/benchmark/`
- Lore/corpus: `content/`, `book/`, `articles/`, `src/spiralverse/`

## Build And Package Manifests

Tracked manifests include:

- Root Node/Python: `package.json`, `pyproject.toml`, `requirements.txt`,
  `requirements-lock.txt`, `pytest.ini`, `tsconfig.json`, `vitest.config.ts`,
  `playwright.config.ts`
- Packages: `packages/agent-bus/package.json`,
  `packages/agent-bus-py/pyproject.toml`, `packages/cli/package.json`,
  `packages/kernel/package.json`, `packages/polly-pad-py/pyproject.toml`,
  `packages/workflow-engine/package.json`
- Apps/services: `ai-ide/package.json`, `apps/mobile/pwa/package.json`,
  `apps/scbe-github-app/package.json`, `services/scbe-shim/package.json`,
  `kindle-app/package.json`
- Rust/PQC: `rust/scbe_core/Cargo.toml`, `python/pqc/pyproject.toml`,
  `python/pqc/setup.py`
- Deployment: `Dockerfile*`, `docker-compose*.yml`, `vercel.json`,
  `render.yaml`, `firebase.json`

## GitHub Actions

Tracked workflows: 76 under `.github/workflows/`.

Major workflow categories:

- CI/test: `ci.yml`, `scbe-tests.yml`, `daily-tests.yml`,
  `nightly-python-full.yml`
- Security: `codeql.yml`, `codeql-analysis.yml`, `security-checks.yml`,
  `weekly-security-audit.yml`, `daily-secret-scan.yml`
- Publishing: `npm-publish.yml`, `npm-publish-cli.yml`,
  `npm-publish-agent-bus.yml`, `pypi-publish.yml`,
  `pypi-publish-agent-bus.yml`, `release.yml`
- Docs/pages: `docs.yml`, `pages-deploy.yml`, `pages-auto-deploy.yml`
- Automation: `auto-triage.yml`, `auto-changelog.yml`, `auto-merge.yml`,
  `auto-rebase-prs.yml`, `workflow-audit.yml`
- Research/training: `weekly-hf-sync.yml`, `daily-training-validator.yml`,
  `research-feed.yml`, `overnight-pipeline.yml`
- Benchmarks/product: `public-agentic-benchmarks.yml`,
  `swe-local-benchmark.yml`, `polly-product-delivery.yml`

## Submodules

Configured submodules:

- `external/Entropicdefenseengineproposal`
- `external/claude-code-plugins-plus-skills`
- `external/designer-skills`
- `external_repos/Spiralverse-AetherMoore`
- `external_repos/ai-workflow-architect`
- `external_repos/aws-lambda-simple-web-app`
- `external_repos/scbe-quantum-prototype`
- `external_repos/scbe-security-gate`
- `external_repos/spiralverse-protocol`
- `external_repos/visual-computer-kindle-ai`
- `spiralverse-protocol`

Current local status shows these submodule worktrees as deleted/missing. Do not
stage those deletions unless the intent is to remove the submodules.

## Largest Tracked Files

Largest tracked files are mostly notebooks, images, and generated reader assets:

- `docs/static/books/six-tongues-cover.jpg` (~2.85 MB)
- `notebooks/spiralverse_protocol_training_generator.ipynb` (~1.45 MB)
- `docs/static/showcase/polly_human_reference_sheet.png` (~0.85 MB)
- `content/book/reader-edition/the-six-tongues-protocol-full.md` (~0.74 MB)
- `notebooks/spiralverse_federated_training_colab.ipynb` (~0.56 MB)
- `examples/SCBEAgent/uv.lock` (~0.55 MB)
- `notebooks/webtoon_panel_generation_embedded_colab.ipynb` (~0.54 MB)
- `packages/cli/bin/scbe.js` (~0.41 MB)

## Local Working Tree State

Current modified tracked files include:

- `AGENTS.md`
- `bin/geoseal.cjs`
- `python/scbe/tongue_isa.py`
- `scripts/agents/scbe_code.py`
- `scripts/system/review_system_and_notes.py`
- `scripts/system/scbe_skill_tool_bridge.mjs`
- `skills/cloud-storage-local-storage-management/scripts/storage_route_scan.ps1`
- `tests/agents/test_scbe_code.py`
- `tests/smoke/test_npm_geoseal_bin.py`

Current untracked additions include:

- `docs/SCBE_FULL_SYSTEM_MAP.md`
- `docs/GITHUB_INVENTORY.md`
- many `.agents/skills/scbe-*` local skills
- `.codex/`

Current deleted tracked paths are mostly submodule directories:

- `external/*`
- `external_repos/*`
- `spiralverse-protocol`

## Local Disk Noise

The filesystem contains far more than tracked Git source. Notable local counts:

- `artifacts/`: over 141,000 files
- `node_modules/`: over 10,000 files
- `.hypothesis/`: hundreds of files

These should not be treated as GitHub source inventory unless explicitly staged
or intentionally archived.

## Recent Tags

Recent tags include:

- `kernel-data-sync-20260608T081307Z`
- `kernel-data-sync-20260601T081647Z`
- `v4.2.0`
- `cli/v4.3.16`
- `agent-bus-py-v0.3.0`
- `v4.1.3`
- `v4.0.9`
- `v4.0.3`

## Inventory Risks

- The repo mixes product, platform, research, lore, generated evidence, and
  operator automation. `START_HERE.md` and `docs/REPO_SURFACE_MAP.md` should
  remain the routing authority.
- Several docs still describe different formula variants. Use
  `docs/specs/CANONICAL_FORMULA_REGISTRY.md` for formula status.
- Submodule deletions are present locally and should be handled deliberately.
- New `.agents/skills` and `.codex` content may be local operational state; audit
  before committing.
- `artifacts/` is massive locally and should stay out of normal GitHub commits
  unless a specific evidence artifact is required.
