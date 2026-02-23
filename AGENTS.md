# Repository Guidelines

## Project Structure & Module Organization
- Core TypeScript code lives in `src/` (governance pipeline, crypto, agentic components).
- Python modules and runtime services are in `python/`, `api/`, and `agents/`.
- Tests are split between `tests/` (Python + integration) and TS unit tests run by Vitest.
- Documentation and architecture notes are in `docs/`.
- Deployment/runtime assets are in `deploy/`, `k8s/`, `docker`-related scripts in `scripts/`, and generated artifacts in `dist/`, `artifacts/`, and `training-data/`.

## Build, Test, and Development Commands
- `npm run build`: cleans and compiles TypeScript (`dist/`).
- `npm run typecheck`: strict TS type check without emit.
- `npm test`: runs Vitest suite.
- `npm run test:python`: runs `pytest tests/ -v`.
- `npm run test:all`: runs TS + Python tests.
- `npm run lint` / `npm run format`: Prettier checks/fixes for TS.
- `npm run lint:python` / `npm run format:python`: Flake8 and Black for Python.
- `npm run docker:build` and `npm run docker:compose`: local container workflow.

## Coding Style & Naming Conventions
- TypeScript: 2-space indentation, `camelCase` variables/functions, `PascalCase` classes/types, explicit exported types on public APIs.
- Python: Black formatting, snake_case for functions/modules, PascalCase classes.
- Keep modules scoped by domain (`crypto`, `agentic`, `harmonic`, `m4mesh`) and avoid cross-layer side effects.

## Testing Guidelines
- Add/modify tests with every behavior change.
- TS tests: colocate by feature or under `tests/` using `*.test.ts`.
- Python tests: `tests/**/test_*.py` naming.
- For security/interop changes, include at least one deterministic regression test and one boundary/invalid-input test.

## Commit & Pull Request Guidelines
- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
- Keep PRs scoped; include purpose, changed paths, test evidence, and rollback notes.
- Link issues/tasks and attach screenshots only for UI changes.
- Do not commit secrets, generated caches (`.pytest_cache`, `.hypothesis`, local logs), or machine-specific config.

## Security & Configuration Tips
- Keep secrets in environment variables; never hardcode keys/tokens.
- Validate all external inputs at boundaries (API, MCP tools, dataset ingest).
- Prefer deterministic outputs for governance/audit paths and log decision-relevant metadata.
