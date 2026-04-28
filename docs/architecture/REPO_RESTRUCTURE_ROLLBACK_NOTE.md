# Repo Restructure Rollback Note

- Migration branch: `chore/repo-launch-restructure`
- Last known green commit before moves: `e648d2f1`
- Commit summary: docs-only checkpoint (inventory + contract + migration map)

## Why this marker exists

If a later migration batch introduces regressions, reset the restructure lane to this checkpoint and replay changes in smaller batches with the Phase 0/1 gates enabled.
