# Master Intake Plan

This plan tracks code/content harvested from duplicate repo families into the master workspace.

## Intake Roots

- `external/intake/ai-workflow-architect/`
- `external/intake/scbe-production-pack/`

## Harvest Reports

- `artifacts/governance/github_family_intake_ai-workflow-architect_20260303T041449Z.json`
- `artifacts/governance/github_family_intake_scbe-production-pack_20260303T041748Z.json`

## Suggested Merge Targets

1. AI workflow family
- Candidate service connectors:
  - `server/services/githubClient.ts`
  - `server/services/notionClient.ts`
  - `server/services/zapierService.ts`
  - `server/services/roundtableCoordinator.ts`
- Candidate app integration docs:
  - `INFRASTRUCTURE_SETUP.md`
  - `DEPLOYMENT_GUIDE.md`
  - `PRICING.md`

2. SCBE production pack family
- Candidate audit docs:
  - `TEST_AUDIT_REPORT.md`

## Merge Rules

- Prefer copying only reusable modules and docs into `src/` or `docs/system/`.
- Do not bulk-vendor whole repos into runtime package paths.
- Keep harvested family snapshots in `external/intake/` as review evidence.
- Mark non-canonical repos as `archive-candidate` before archive/delete actions.

