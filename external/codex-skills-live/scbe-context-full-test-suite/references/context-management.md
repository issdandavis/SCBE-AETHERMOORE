# SCBE Context Management

Use this order so the repo stays readable.

## First Reads

1. `git status --short`
2. `git diff --name-only`
3. `docs/map-room/session_handoff_latest.md`
4. `package.json`
5. `docs/local-branch-validation.md`

## Read Next Only If Needed

- the exact changed files
- `scripts/branch_validation.ps1` when branch-wide validation is required
- failing test files
- current PR or code-scanning context

## Avoid By Default

- archive docs
- generated `artifacts/`
- `training/` outputs
- cache dirs
- unrelated dirty files

## Rule of Thumb

- one-file fix: read diff + touched tests
- security batch: read diff + touched tests + current code-scanning alert details
- branch stabilization: add handoff + validation docs + `branch_validation.ps1`
