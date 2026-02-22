# Repository Guidelines

## Project Structure & Module Organization
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
