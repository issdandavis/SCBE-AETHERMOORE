# SCBE Self-Improvement Loop

## Loop Architecture

1. **Observe**: collect outputs from scripts, chain runs, and external checks.
2. **Diagnose**: identify one gap with a concrete file/function/service surface.
3. **Draft**: propose a patch to an existing skill, reference file, or chain asset.
4. **Validate**: run or simulate a verification check (test/assertion/pattern).
5. **Route**: update tri-fold summary with patch and integration impact.

## Good Patch Shape

- One patch file per action.
- Patch anchored to canonical files, not duplicates.
- Include both rationale and measurable effect.

## Skill Draft Rule

When creating a child skill:

- reference parent glossary/constants by linking `../scbe-system-engine/references/...`
- avoid copying canonical definitions.
- keep files under 200 lines unless a reference split is required.

## Closure Rule

Never end at a report-only response.
Every observation must produce either:

- code/reference patch, or
- explicit blocked-actions plan with service IDs and issue template.
