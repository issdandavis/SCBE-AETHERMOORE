# Code Scanning Remediation - 2026-04-21

This branch exists to clear repo-wide baseline failures that were blocking unrelated pull requests and to reduce the open GitHub code-scanning backlog from easy, low-risk fixes downward.

## What Was Fixed

### Baseline CI and formatting debt

- Repo-wide TypeScript formatting drift that caused `CI -> Lint and Format Check` to fail.
- Repo-wide Python formatting drift in files outside the branch's original target surface.
- Lightweight Python lint debt such as unused imports, unused globals, unused locals, and empty or over-broad exception handlers.

### Security and exposure fixes

- Removed clear-text persistence of raw sender and subject metadata in `scripts/apollo/agentic_email_triage.py`.
- Removed exception-string exposure from `scripts/aetherbrowser/api_server.py` contact submission path.
- Earlier branch work also tightened weak exception handling, sensitive logging, shell/path injection patterns, and workflow permission declarations.

### Easy static-analysis wins

- Removed stray no-op expressions and dead symbols in:
  - `src/crypto/tri_bundle.py`
  - `src/glass_box/tongue_fabrication.py`
  - `src/neurogolf/token_braid.py`
  - `scripts/benchmark/rule_sweep7.py`
  - `docs/static/polly-companion.js`
  - `src/training/execution_feedback.py`
  - `src/training/flight_trainer.py`
- Cleaned tokenizer decode noise in `src/tokenizer/sacred_tongues_hf.py`.

## What Caused These Issues

1. Repo-wide baseline debt was allowed to accumulate on `main`.
2. PRs unrelated to the failing surfaces inherited global CI and formatting failures.
3. Several helper scripts stored or echoed operational data too directly.
4. Dead code and placeholder expressions were left behind after partial refactors.
5. Formatting gates existed, but local pre-push validation was not consistently run against the same scopes as CI.

## Prevention Rules

### Rule 1: Keep baseline gates green

If `main` is red on shared gates, fix the baseline first before asking feature PRs to carry unrelated CI debt.

### Rule 2: Run the same local checks CI runs

Before push on shared Python and frontend surfaces:

```powershell
python -m black --target-version py311 --line-length 120 src tests
python -m ruff check .
npx prettier --check "src/**/*.ts" "tests/**/*.ts"
npm test
```

For scoped changes, run targeted checks first, then the matching shared gate if the edited path participates in it.

### Rule 3: Do not store raw sensitive metadata in queue or log surfaces

- Email senders, subjects, tokens, API material, and message bodies should be hashed, redacted, or summarized before queue persistence.
- API responses must not return raw exception text to callers on production-facing routes.

### Rule 4: Remove dead placeholders during the same edit

If a refactor leaves:

- unused imports
- unused locals
- no-op symbol lookups
- placeholder branches

remove them before push instead of waiting for scanner cleanup later.

### Rule 5: Shared workflows need explicit ownership

When a workflow is shared by many PRs, changes to its permissions, formatting scope, and runtime assumptions should be treated as repo maintenance, not hidden inside a feature PR.

## Suggested Next Steps

1. Merge the baseline branch so stale PRs stop inheriting unrelated failures.
2. Re-run CodeQL on the merged head.
3. Burn down remaining open alerts by severity order:
   - exception exposure and sensitive logging
   - shell/path injection
   - unused-symbol noise
   - structural notes and warnings
4. Keep one living remediation note per cleanup wave instead of scattering fix rationale across PR comments.
