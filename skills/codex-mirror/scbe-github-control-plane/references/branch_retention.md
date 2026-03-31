# Branch Retention

Default exact keep set:
- `main`
- `master`
- `gh-pages`

Default keep patterns:
- `release/*`
- `hotfix/*`
- `overnight/*`

Default manual-review patterns:
- `backup/*`
- `dependabot/*`
- `claude/*`
- `copilot/*`
- `issdandavis-patch-*`

Why this split exists:
- protected branches should never be caught in routine cleanup
- open PR heads are active work, even if they look stale
- backup and bot lanes often need deliberate handling instead of batch deletion

Only merged, unprotected, non-special branches belong in `safe-delete`.
