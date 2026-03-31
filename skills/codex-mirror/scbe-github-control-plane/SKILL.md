---
name: scbe-github-control-plane
description: Audit GitHub branch, PR, and cleanup state for one repo with explicit keep, safe-delete, and manual-review buckets, then route anything ambiguous to browser proof instead of blind deletion.
---

# SCBE GitHub Control Plane

Use this skill when the user wants GitHub cleaned up without guesswork.

It replaces ad hoc branch poking with one repeatable audit:
- canonical branches and protected patterns
- open PR heads that must be preserved
- merged branches that are actually safe to delete
- unmerged or special-pattern branches that require manual review
- optional reachability checks for known bad commits

## Quick Start

From the repo root:

```powershell
python .\scripts\system\github_control_plane.py --repo-root . --sensitive-sha 27db3abe
```

Full JSON:

```powershell
python .\scripts\system\github_control_plane.py --repo-root . --json
```

The report writes to:
- `artifacts/github-control/github_control_latest.json`
- `artifacts/github-control/github_control_latest.md`

## Operating Rules

1. Audit before deleting anything.
2. Treat `main`, `master`, `gh-pages`, and active `overnight/*` lanes as protected by default.
3. Preserve all open PR heads.
4. Only treat merged, unprotected, non-special branches as safe delete candidates.
5. Route backups, dependabot lanes, bot lanes, and anything unmerged to manual review.

Read `references/branch_retention.md` if the keep rules need adjustment.
Read `references/browser_fallback.md` when the command line is not enough and GitHub UI proof is needed.

## Browser Use

Use browser or Playwright only when the audit alone is not enough:
- branch protection state
- PR UI proof
- visual branch cleanup confirmation

Do not open the browser just to list branches that the report already classified.
