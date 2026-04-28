# Repo Restructure Phase 0/1 Contract

## Purpose

This contract defines the non-negotiable guardrails for the major build + launch restructure. It exists to prevent a repo-wide breakage hunt before path moves begin.

## Branch and Checkpoint Rules

- Migration branch: `chore/repo-launch-restructure`
- First migration commit must be inventory/docs only.
- Rollback marker text: `last known green commit before moves`
- Runtime and core build roots stay frozen until Phase 0/1 gates are green.

## Do-Not-Move-Yet Roots

Do not move these paths during Phase 0/1:

- `src/`
- `python/`
- `api/`
- `tests/`
- `packages/`
- `.github/`
- `package.json`
- `pyproject.toml`
- `pytest.ini`
- `tsconfig*.json`
- `vitest.config.ts`

## Launch Profile Contract

One command entrypoint is required, but startup must be profile-scoped.

Profiles:

- `dev-min`
- `browser`
- `training`
- `contracts`
- `full-local`

`dev-min` is the safe default and must not start every service.

## Required Gates Before Path Moves

All must pass before Phase 2:

1. Path reference scan for soon-to-move roots and absolute local paths.
2. Secret/config sweep.
3. Markdown link/path validation.
4. Launch preflight checks.
5. Focused build/test verification from root.

## Generated Data Policy (Pre-Move)

- `generated/` defaults to local-only/ignored unless explicitly promoted.
- `artifacts/` is split into:
  - disposable operational outputs
  - canonical evidence/proposal records
- `training-data/` is selectively canonical and cannot be blindly moved into `generated/`.

## Rollout Boundaries

Phase 0/1 deliverables include:

- inventory
- path dependency matrix
- migration map
- preflight and scanner tooling
- launch profile contract

Phase 2 directory moves are blocked until this contract is satisfied and signed off.
