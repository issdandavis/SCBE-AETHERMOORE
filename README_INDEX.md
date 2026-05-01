# SCBE Canonical Index Guide

This repository contains **both canonical protocol material and experimental research**.
To reduce ambiguity for human readers and AI indexers, treat files as follows.

> **Repo shape note (2026-04):** the canonical specs, ops docs, and business
> docs were moved out of the repo root into `docs/{specs,ops,business}` under
> the reorg branch `chore/repo-shape-2026-04`. Update bookmarks accordingly.
> The plan and inventory live at `docs/ops/REPO_REORG_2026-04.md` and
> `artifacts/repo_reorg/inventory_2026-04.json`.

## Canonical (authoritative)

- `docs/specs/SPEC.md` — normative protocol specification
- `docs/specs/CONCEPTS.md` — conservative glossary and implementation-aligned definitions
- `docs/specs/ARCHITECTURE.md` — primary architecture overview
- `docs/specs/SYSTEM_ARCHITECTURE.md` — detailed system architecture
- `docs/specs/LAYER_INDEX.md` — 14-layer pipeline reference
- `docs/specs/SCBE_SYSTEM_OVERVIEW.md` — high-level system overview
- `docs/specs/CANONICAL_SYSTEM_STATE.md` — current canonical system state
- `docs/specs/STRUCTURE.md` — repo structure description
- `docs/specs/SYSTEM_OVERVIEW.mermaid.md` — system overview diagram
- `docs/specs/Spiralverse_Game_Design_Bible.md` — Spiralverse design bible
- `CITATION.cff` — canonical authorship and citation metadata
- `llms.txt` — crawler/indexing guidance
- `docs/hydra/ARCHITECTURE.md` — HYDRA execution-plane reference architecture
- `docs/core-theorems/SACRED_EGGS_GENESIS_BOOTSTRAP_AUTHORIZATION.md` — genesis/bootstrap authorization theorem surface

## Operations and planning

- `docs/ops/REPO_REORG_2026-04.md` — current repo reshape plan (this reorg)
- `docs/ops/RESTRUCTURE_PLAN.md` — historical restructure plan
- `docs/ops/REPO_AUDIT.md`, `docs/ops/REPO_REPORT.md`, `docs/ops/REPO_BOUNDARY_PLAN.md`,
  `docs/ops/REPO_SURFACE_MAP.md` — repo audit + boundary surfaces
- `docs/ops/APP_STORE_STRATEGY.md` — GeoShell app-store direction
- `docs/ops/DEPLOYMENT_STRATEGY.md` — deployment strategy
- `docs/ops/ROADMAP_90_DAY_TO_PILOT.md` — 90-day pilot roadmap
- `docs/ops/STATE_OF_SYSTEM.md`, `docs/ops/SYSTEM_STATUS.md` — current state
- `docs/ops/SYSTEM_IMPROVEMENT_RECOMMENDATIONS.md` — system improvements
- `docs/ops/PROJECT_COMPLETION_STATUS.md` — completion status
- `docs/ops/TEST_AUDIT_REPORT.md`, `docs/ops/TEST_FAILURE_ANALYSIS.md` — test health
- `docs/ops/CLEANUP_NOTES.md`, `docs/ops/SPLIT_NOTICE.md`, `docs/ops/INSTRUCTIONS.md`,
  `docs/ops/OVERNIGHT_TASKS.md`, `docs/ops/DEMOS.md` — operational notes
- `docs/ops/AGENTIC_EXECUTION_REVIEW_TEMPORAL_LAYERS.md` — agent execution review
- `docs/ops/MERGE_AND_STASH_PLAYBOOK.md` — git merge/stash playbook
- `docs/ops/OPERATOR_SHIPPING_RAIL.md` — operator shipping rail

## Business / patent / pitch

- `docs/business/COMMERCIAL.md` — commercial overview
- `docs/business/CUSTOMER_LICENSE_AGREEMENT.md` — customer license
- `docs/business/PATENT_CLAIMS_COVERAGE.md`, `docs/business/PATENT_DETAILED_DESCRIPTION.md`,
  `docs/business/PATENT_FIGURES.txt`, `docs/business/SCBE_PATENT_PORTFOLIO.md` — patent material
- `docs/business/PITCH_EMAIL_BANK_INNOVATION_LAB.md` — outreach
- `docs/business/PACKAGE_SUMMARY.txt`, `docs/business/VIDEO_SCRIPT_90SEC.md`,
  `docs/business/ZENODO_ABSTRACT.md` — supporting materials

## Non-canonical (research / exploratory)

- `experimental/` — prototypes, reference implementations, and toy models
- `experiments/` — short-lived experiments
- `docs/research/` — research drafts and R&D proposals
- notebooks, scratch analyses, and draft architecture narratives not linked from `docs/specs/SPEC.md`

## Canonical naming

Use these names consistently in metadata and releases:

- **SCBE**: Spectral Context Bound Encryption
- **Entropic Defense Engine**: risk-governance and policy enforcement layer
- **AI Governance**: decision, quorum, lineage, and policy controls around model/tool execution
- **GeoSeal**: the canonical CLI product surface
- **GeoShell**: the unified visual shell that hosts SCBE apps and games (formerly the `scbe-visual-system` desktop app)

## Source-of-truth policy

If wording conflicts across files, prefer:

1. `docs/specs/SPEC.md`
2. `docs/specs/CONCEPTS.md`
3. implementation tests and release notes
4. experimental artifacts

This policy exists to prevent indexing drift and "AI confusion" caused by mixed-authority documents.
