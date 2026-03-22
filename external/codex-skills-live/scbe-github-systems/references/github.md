# GitHub Workflow for SCBE Repos

Prefer the repo's own rules first (especially `SCBE-AETHERMOORE-working/CLAUDE.md`), then apply this checklist.

## Conventions

- Use Conventional Commits, matching the repo guidance:
  - `feat(scope): ...`
  - `fix(scope): ...`
  - `docs(scope): ...`
  - `test(scope): ...`
  - `refactor(scope): ...`
  - `chore: ...`
- Keep branch names aligned with intent: `feat/...`, `fix/...`, `docs/...`, `chore/...`.

## PR Checklist (Before Opening or Updating)

- Confirm what repo you are in and that the target branch is correct.
- Run core tests and checks:
  - `npm test`
  - `npm run typecheck`
  - `python -m pytest tests/ -v`
- Check `.github/workflows/` for any required CI steps (format, lint, build, coverage).
- Map changes to modules/layers where practical (helps reviewers reason about safety impacts).
- For security-sensitive changes (crypto, secrets, auth, envelope formats), add focused tests and scrutinize for regressions.

## Review Checklist (When Reading a PR)

- Is TypeScript (canonical) consistent with Python (reference), or is divergence intentional and documented?
- Are new files tagged/layered as expected by repo convention?
- Do changes affect the decision gate (L13), thresholds, or risk scaling (L12)? If yes, demand tests and clear reasoning.
- Are secrets excluded and configs handled safely?

## CI/Automation Pointers

- GitHub Actions workflows: `SCBE-AETHERMOORE-working/.github/workflows/`
- Docker/dev env: `SCBE-AETHERMOORE-working/Dockerfile`, `SCBE-AETHERMOORE-working/docker-compose.yml`
