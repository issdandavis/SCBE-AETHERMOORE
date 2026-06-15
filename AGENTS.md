# Repository Guidelines

## Project Structure & Module Organization

This is a mixed TypeScript, Python, and Rust repository for SCBE-AETHERMOORE. Core TypeScript packages live in `src/`, with public entry points exported through `package.json` and built into `dist/`. Python packages and runtime helpers are under `python/`, `api/`, and `agents/`, with root CLIs such as `scbe.py`, `scbe-cli.py`, and `six-tongues-cli.py`. Tests live in `tests/`, organized by domain and scope. Supporting apps and packages live in `apps/`, `packages/`, and `services/`; automation lives in `scripts/`; docs and research material live in `docs/`, `research/`, and `references/`. Treat `dist/`, `artifacts/`, caches, and local training runs as generated output unless a release process explicitly requires them.

## Build, Test, and Development Commands

- `npm run build`: clean and compile TypeScript into `dist/`.
- `npm run build:watch`: compile TypeScript in watch mode.
- `npm test`: run the Vitest suite.
- `npm run test:python`: run `pytest tests/ -v`.
- `npm run test:rust`: run Rust tests for `rust/scbe_core`.
- `npm run test:all`: run the standard TypeScript and Python suites.
- `npm run typecheck`: run TypeScript checks without emitting files.
- `npm run lint` / `npm run format`: check or fix TypeScript formatting.
- `npm run lint:python` / `npm run format:python`: run Flake8 or Black for Python.

## Coding Style & Naming Conventions

Use Prettier for TypeScript and Black for Python. Python targets 3.11+ and uses 120-character lines in CI. Keep modules scoped to their domain (`crypto`, `agentic`, `harmonic`, `m4mesh`, etc.) and avoid cross-layer side effects. Use `camelCase` for TypeScript variables/functions, `PascalCase` for classes/types, and `snake_case` for Python modules/functions.

## Testing Guidelines

Add or update tests for behavior changes. Python tests should be named `test_*.py`; TypeScript tests should use `*.test.ts`. Use pytest markers from `pytest.ini` such as `unit`, `integration`, `security`, `property`, or `slow` when scope matters. Run focused tests first, then broader suites when touching shared contracts, CLI behavior, security gates, or generated outputs.

## Commit & Pull Request Guidelines

Recent history follows Conventional Commits, for example `feat(cli): add describe command` and `chore(deps): bump grpcio`. Keep commits scoped and imperative. Pull requests should include a concise summary, affected paths, linked issues when available, test evidence, and screenshots or logs for UI, CLI, or operational changes.

## Security & Configuration Tips

Start from `.env.example`; do not commit secrets, local databases, credential exports, or machine-specific config. Keep dependency changes pinned through existing lockfiles, and run secret-sensitive changes against the repository's security checks before pushing.
