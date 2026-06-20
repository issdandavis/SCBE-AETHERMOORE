# Repository Guidelines

## Project Structure & Module Organization

This is a mixed TypeScript, Python, and Rust repository for SCBE-AETHERMOORE. Core TypeScript packages live in `src/`, with public entry points exported through `package.json` and built into `dist/`. Python packages are also under `src/`, with root CLIs such as `scbe.py`, `scbe-cli.py`, and `six-tongues-cli.py`. Tests are organized in `tests/` by domain (`tests/crypto/`, `tests/api/`, `tests/L2-unit/`, etc.). Supporting apps and packages live in `apps/`, `packages/`, and `services/`; scripts and automation live in `scripts/`; docs, references, and research material live in `docs/`, `research/`, and `references/`. Avoid committing generated output from `dist/`, `artifacts/`, or caches unless a release process explicitly requires it.

## Build, Test, and Development Commands

- `npm run build`: clean and compile the TypeScript source.
- `npm run build:watch`: run TypeScript compilation in watch mode.
- `npm test`: run the Vitest suite.
- `npm run test:coverage`: run Vitest with coverage.
- `npm run test:python`: run `pytest tests/ -v`.
- `npm run test:rust`: run Rust tests for `rust/scbe_core`.
- `npm run test:all`: run the standard TypeScript and Python suites.
- `npm run typecheck`: run TypeScript without emitting files.
- `npm run lint`: check TypeScript formatting with Prettier.
- `npm run lint:python`: run Flake8 over Python source and tests.

## Coding Style & Naming Conventions

Use Prettier for TypeScript (`npm run format`) and Black for Python (`npm run format:python`). Python targets 3.11+, uses 120-character lines, and is checked by Ruff/Flake8. Keep TypeScript modules focused and colocate domain code under matching `src/<domain>/` folders. Use `camelCase` for variables/functions, `PascalCase` for classes/types, and `snake_case` for Python modules and functions.

## Testing Guidelines

Name Python tests `test_*.py`, classes `Test*`, and functions `test_*`. Use pytest markers from `pytest.ini` such as `unit`, `integration`, `security`, `property`, or `slow` when scope matters. Prefer focused tests near the touched domain directory, and run the narrow suite first before `npm run test:all`.

## Commit & Pull Request Guidelines

Recent history follows Conventional Commits, for example `feat(cli): add describe command` and `chore(deps): bump grpcio`. Keep commits scoped and imperative. Pull requests should include a summary, linked issue when available, test evidence, and screenshots or logs for UI, CLI, or operational changes.

## Security & Configuration Tips

Start from `.env.example`; do not commit real secrets, local databases, or credential exports. Run secret-sensitive changes against `.gitleaks.toml` expectations and keep external dependencies pinned through the existing lockfiles.
