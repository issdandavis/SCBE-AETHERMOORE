# Contributing to SCBE-AETHERMOORE

Thanks for contributing.

## Scope

SCBE-AETHERMOORE is a mixed TypeScript and Python repository for:
- geometric AI governance and evaluation
- cryptographic and policy infrastructure
- agentic runtime surfaces
- research, benchmark, and demo artifacts

Keep changes narrow. Prefer one behavior change per pull request.

## Workflow

1. Branch from `main`.
2. Make the smallest complete change that solves the problem.
3. Add or update tests for every behavior change.
4. Open a pull request against `main`.

Use short-lived branches. Do not keep merged branches around as long-term working lanes unless they are intentionally archival.

## Local Development

Core commands:

```bash
npm run build
npm run typecheck
npm test
npm run test:python
npm run test:all
```

Formatting and linting:

```bash
npm run lint
npm run format
npm run lint:python
npm run format:python
```

## Code Standards

- TypeScript: strict typing, 2-space indentation, focused modules, explicit public types.
- Python: Black formatting, type hints where practical, snake_case naming.
- Keep modules scoped by domain and avoid cross-layer side effects.
- Do not mix generated outputs with hand-authored source changes in the same pull request unless the generated output is the point of the change.

## Tests

- Add at least one regression test for bug fixes.
- Add at least one invalid-input or boundary test for security-sensitive changes.
- Run targeted tests first, then the relevant aggregate command.
- Do not increase the pre-existing failure count.

## Commit Style

Use Conventional Commits:

- `feat(scope): ...`
- `fix(scope): ...`
- `docs(scope): ...`
- `test(scope): ...`
- `chore(scope): ...`

## Pull Request Expectations

Every pull request should include:
- what changed
- why it changed
- affected modules or paths
- test evidence
- any rollback or migration notes if behavior changed materially

## Generated Data And Secrets

- Never commit secrets, tokens, or machine-specific credentials.
- Keep local caches, logs, and transient training outputs out of normal source PRs.
- Large datasets belong in the separate training-data repository, not in the main code repo.
