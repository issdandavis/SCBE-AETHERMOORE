# Repo Surface Segmentation

This repository now uses explicit distribution surfaces so users do not need to pull the full working tree.

## Surfaces

1. `core_public`
- Runtime code and package metadata only.
- Built from `config/governance/distribution_profiles.json`.
- Intended for install/use.

2. `sellable_bundle`
- Revenue-facing pages, sales scripts, and market-facing docs.
- Keeps patent-sensitive and bulky local artifacts out.

3. `internal_full`
- Internal operations surface for maintainers.
- Excludes bulky local/generated directories.

## Build Commands

```powershell
python scripts/system/build_distribution_profile.py --profile core_public
python scripts/system/build_distribution_profile.py --profile sellable_bundle
python scripts/system/build_distribution_profile.py --profile internal_full
```

Outputs are generated under `artifacts/release_profiles/` with a zip plus JSON manifest.

## GitHub Portfolio Governance

Tier and surface topic assignment can be applied from sectioning CSV:

```powershell
python scripts/system/github_repo_governance_apply.py --csv artifacts/governance/github_repo_sectioning_issdandavis_*.csv --dry-run
python scripts/system/github_repo_governance_apply.py --csv artifacts/governance/github_repo_sectioning_issdandavis_*.csv --apply
```

## Family Intake Into Master

Use the intake script to harvest unique lightweight files from duplicate repo families into `external/intake/` for consolidation:

```powershell
python scripts/system/github_family_intake.py --owner issdandavis --canonical AI-Workflow-Architect --variants AI-Workflow-Architect-1 AI-Workflow-Architect-1.2.2 ai-workflow-architect-main ai-workflow-architect-pro ai-workflow-architect-replit --family ai-workflow-architect
```

