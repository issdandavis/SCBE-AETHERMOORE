---
name: scbe-context-full-test-suite
description: Manage context and run validation for the SCBE-AETHERMOORE monorepo without loading unnecessary repo noise. Use when work needs a fast repo handoff, diff-first context trimming, a decision about targeted vs core vs full test lanes, or a repeatable full-suite run using the branch validation workflow.
---

# SCBE Context Full Test Suite

Keep context small, then run the narrowest test lane that proves the change.

## Quick Start

1. Identify the branch, touched files, and whether the worktree is noisy.
2. Read only the highest-signal context first:
   - current diff for touched files
   - `docs/map-room/session_handoff_latest.md`
   - `package.json`
   - `docs/local-branch-validation.md`
   - `scripts/branch_validation.ps1` when branch-wide validation is needed
3. Choose the smallest useful validation lane:
   - targeted tests for one feature or bug fix
   - `core` branch validation for a safe branch-wide gate
   - `full` branch validation only when broader regression coverage matters
4. Record exact commands and outcomes.

## Context Rules

- Start with `git status --short` and `git diff --name-only`.
- Do not read large docs, generated artifacts, or old reports unless they directly affect the current change.
- Prefer current sources over archive docs.
- Treat these paths as default first reads for SCBE repo state:
  - `docs/map-room/session_handoff_latest.md`
  - `docs/local-branch-validation.md`
  - `package.json`
  - changed files only
- Use `references/context-management.md` for the repo-specific context triage order.

## Validation Rules

- Prefer targeted commands first when a change is narrow.
- Use the repo validation script for branch-wide safety:
  - `pwsh -File .\scripts\branch_validation.ps1 -Branch <branch> -Profile core`
  - `pwsh -File .\scripts\branch_validation.ps1 -Branch <branch> -Profile full`
- Use the wrapper in this skill when you want a deterministic entrypoint:
  - `scripts/run_scbe_validation.ps1`
- Use `references/full-test-suite.md` for lane selection, expected commands, and fallback behavior.

## Output Expectations

- Report what was run.
- Report what passed or failed.
- Distinguish targeted evidence from branch-wide evidence.
- Call out when the run is blocked by environment issues, pre-existing failures, or missing tools.

## Resources

### scripts/

- `scripts/run_scbe_validation.ps1`
  - wraps the repo branch-validation workflow
  - falls back to direct root commands if the branch validator is unavailable

### references/

- `references/context-management.md`
  - repo-specific context loading order for SCBE-AETHERMOORE
- `references/full-test-suite.md`
  - test-lane selection and command map for targeted, core, and full validation
