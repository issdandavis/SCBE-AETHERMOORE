# Pull / Sync Skill Card

summary: Prepare repository pull, sync, merge, or rebase work without hiding the risk.
triggers: pull, sync, merge, rebase

## Worksheet

- Inspect branch, upstream, and dirty files first.
- Refuse to overwrite unrelated local edits.
- Prefer fetch/status/diff before pull when the tree is dirty.
- Route execution through `scbe x git ...` so receipts capture the exact action.
