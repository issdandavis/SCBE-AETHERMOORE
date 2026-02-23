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
- `src/` is the main codebase. Key areas: `src/harmonic/` (14-layer pipeline), `src/crypto/`, `src/api/`, `src/agentic/`, and `src/symphonic_cipher/`.
- `tests/` contains Python and TS-aligned validation suites (unit, integration, adversarial, interop).
- `scripts/` contains operational tooling (dataset generation/merge, Docker and MCP helpers).
- `training-data/` stores JSONL corpora and schemas used for SFT pipelines.
- Treat `artifacts/`, `training/runs/`, and local DB/cache files as generated outputs; avoid committing them unless required.

## Build, Test, and Development Commands
- `npm run build` — clean and compile TypeScript to `dist/`.
- `npm run typecheck` — TS static checks without emitting files.
- `npm test` — run Vitest suite.
- `npm run test:python` — run Python tests (`pytest tests/ -v`).
- `npm run test:all` — run TS + Python suites.
- `npm run lint` and `npm run lint:python` — Prettier and flake8 checks.
- `npm run format` and `npm run format:python` — TS and Python formatting.
- Docker/MCP ops: `npm run docker:doctor:api`, `npm run mcp:doctor`.

## Coding Style & Naming Conventions
- TypeScript: strict typing, small focused modules, `camelCase` for vars/functions, `PascalCase` for classes/types.
- Python: PEP 8 with type hints and docstrings; Black formatting (120-char line limit).
- Test files: Python `test_*.py`; TS `*.test.ts`.
- Prefer explicit metadata fields (`track`, `source_type`, `quality`) in training records.

## Testing Guidelines
- Frameworks: Vitest (TS), pytest + Hypothesis (Python).
- Add regression tests for every bug fix (code and math behavior).
- Run targeted tests for changed modules first, then `npm run test:all`.
- Do not increase pre-existing failure counts.

## Commit & Pull Request Guidelines
- Use Conventional Commits with scope, e.g. `feat(training): ...`, `fix(physics): ...`, `chore(docker): ...`.
- PRs should include:
  - concise summary of behavior changes,
  - affected paths/modules,
  - test evidence (commands + results),
  - linked issue(s) when applicable.
- Keep PRs focused; avoid unrelated generated artifacts or secrets.

## Security & Configuration Tips
- Never commit API tokens or secrets; use `.env.example` as template.
- Prefer script-based ops (`scripts/scbe_docker_status.ps1`, `scripts/scbe_mcp_terminal.ps1`) for reproducible local control.
