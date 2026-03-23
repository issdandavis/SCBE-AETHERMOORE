# Repo Map

## What This Repo Is

`SCBE-AETHERMOORE` is a hybrid monorepo.

It contains:

- a TypeScript security and governance library
- Python API and runtime services
- HYDRA and operator scripts
- webtoon/manhwa production tooling
- datasets, exports, and large documentation archives

The repo is not cleanly split into one product surface. Orientation depends on the user's goal.

## Primary Lanes

### 1. Core Library Lane

Use this when the question is about the 14-layer system, cryptography, package exports, or governance math.

- `src/index.ts`
- `src/harmonic/`
- `src/crypto/`
- `src/governance/`
- `src/symphonic/`
- `src/tokenizer/`

`package.json` is the quickest way to see the npm/export surface.

### 2. Python Service Lane

Use this when the question is about running FastAPI services, SaaS control plane work, HYDRA routes, storage, or API endpoints.

- `src/api/main.py`
- `src/api/saas_routes.py`
- `src/api/hydra_routes.py`
- `api/main.py`
- `api/persistence.py`
- `api/metering.py`

Important distinction:

- `src/api/main.py` is the newer MVP/control-plane lane with HYDRA, memory sealing, and SaaS additions.
- `api/main.py` is the older production-governance lane with `/v1/*`, billing hooks, persistence, and agent authorization.

### 3. Operator Script Lane

Use this when the question is about how people actually drive the system locally.

- `scripts/hydra_command_center.ps1`
- `scripts/hydra.ps1`
- `scripts/scbe_terminal_ops.py`
- `scripts/scbe_docker_status.ps1`
- `scripts/scbe_mcp_terminal.ps1`
- `scripts/run_aetherbrowse_service.ps1`

This is where many practical workflows live first.

### 4. Content And Image Lane

Use this when the question is about webtoon/manhwa generation, image consistency, or publishing automation.

- `scripts/webtoon_gen.py`
- `scripts/webtoon_quality_gate.py`
- `scripts/assemble_manhwa_strip.py`
- `scripts/grok_image_gen.py`
- `artifacts/webtoon/`
- `docs/specs/WEBTOON_IMAGE_CONSISTENCY_SYSTEM.md`

### 5. Test Lane

Use this when the user asks "is this real?" or "what is covered?"

- `tests/`
- `pytest.ini`
- `vitest.config.ts`

Prefer tests over docs when there is ambiguity about current behavior.

## Usually Noisy Lanes

These are often useful, but not the best first stop for code orientation:

- `artifacts/` for generated outputs and evidence packs
- `training-data/` for corpora and SFT material
- `docs/archive/` and other archive directories
- snapshot or duplicate-style folders like `SCBE-AETHERMOORE-v3.0.0`
- one-off demos and experiments unless the user explicitly asks for them

## Good First Files

- `AGENTS.md`
- `package.json`
- `README.md`
- `src/index.ts`
- `src/api/main.py`
- `api/main.py`
- `scripts/hydra_command_center.ps1`

## If The User Asks "Where Do I Start?"

Use this mapping:

- "Explain the security stack" -> `src/harmonic/`, `src/crypto/`, `src/index.ts`
- "Run the main API" -> `src/api/main.py` and `api/main.py`, then explain which one fits the task
- "How do I operate this from terminal?" -> `scripts/hydra_command_center.ps1`
- "How do I generate or review manhwa?" -> `scripts/webtoon_gen.py`, `scripts/assemble_manhwa_strip.py`, `docs/specs/WEBTOON_IMAGE_CONSISTENCY_SYSTEM.md`
- "What is published to npm?" -> `package.json` and `dist/`
