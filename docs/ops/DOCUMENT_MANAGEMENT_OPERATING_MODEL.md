# Document Management Operating Model

Updated: 2026-05-01
Status: Active

## Purpose

Keep documentation aligned with runtime truth and prevent stale or duplicate docs from becoming accidental authority.

## Authority Tiers

1. Runtime code + proving tests
2. Canonical specs/state
3. Operator runbooks
4. Public docs
5. Research notes and historical artifacts

If tiers disagree, higher tier wins and lower tier must be updated or demoted.

## Channel Model

- Main channel: canonical + operational docs
- Side channel: helpful support docs
- Archive channel: preserved history
- Dry channel: exploratory notes
- Gated channel: generated artifacts and heavy outputs

## Required Cleanup Rules

1. Canonical doc must be unique per topic.
2. Lower-authority duplicates become shims that point to canonical files.
3. Broken path references are treated as defects and fixed immediately.
4. Open-work markers must have either:
   - an owner + due date, or
   - explicit "historical note" status.

## Executable Review Loop

Run this loop before release or major refactors.

```powershell
python scripts/system/docs_finish_audit.py --json
python scripts/system/docs_finish_audit.py --write-report artifacts/docs/doc_finish_audit.json
```

## Done Criteria

- no broken local markdown links in main-channel docs
- no unresolved contact strings in security/ops docs
- each unfinished marker appears in the audit report with owner/action
- duplicate docs either consolidated or converted to shims
