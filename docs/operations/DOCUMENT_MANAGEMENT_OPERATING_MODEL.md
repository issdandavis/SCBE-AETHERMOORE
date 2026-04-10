# SCBE Document Management Operating Model

Last updated: 2026-04-08
Status: canonical operating guide for document authority, consolidation, and update order

## Purpose

This file defines how documents are managed in this repository so the repo stops acting like:

- a runtime codebase,
- a storage dump,
- a research notebook,
- and a public product surface

all at once.

Use this file when:

- consolidating overlapping docs,
- deciding which document is authoritative,
- updating formulas or status language,
- or deciding whether something belongs in `docs/`, `notes/`, `training-data/`, or generated output paths.

## Core Rule

Every document must belong to one primary class.

If a document starts doing more than one job, split it or demote it.

## Document Classes

### 1. Canonical

These define the current system truth.

Examples:

- `CANONICAL_SYSTEM_STATE.md`
- `docs/specs/CANONICAL_FORMULA_REGISTRY.md`

Use for:

- formula authority
- runtime authority
- status language authority
- boundary/ownership decisions

### 2. Operational

These are solo-operator working docs used to run the system.

Examples:

- `REPO_SURFACE_MAP.md`
- `REPO_BOUNDARY_PLAN.md`
- `docs/operations/DARPA_SAM_GOV_CONTACTS_AND_PROPOSAL_STATUS.md`
- this file

Use for:

- startup and navigation
- contact/status tracking
- cleanup and operating procedures
- “what do I update first?”

### 3. Public Surface

These explain the system outwardly but are not allowed to override canonical files.

Examples:

- `README.md`
- `ARCHITECTURE.md`
- `SYSTEM_ARCHITECTURE.md`
- public website/docs pages

Use for:

- public explanation
- package surface
- product framing
- high-level architecture

### 4. Runtime Reference

These describe or point to active code surfaces.

Examples:

- `package.json`
- `api/main.py`
- `src/api/main.py`
- targeted test files that prove live behavior

Use for:

- run commands
- endpoint surfaces
- package exports
- implementation-backed behavior

### 5. Exploratory / Research

These hold active theory, experiments, and future branches.

Examples:

- `notes/`
- `notebooks/`
- `paper/`
- exploratory specs for phi joints, M4NMM, bundle systems, mesh systems

Use for:

- in-progress ideas
- speculative math
- future architecture branches

These are not allowed to silently redefine runtime behavior.

### 6. Historical / Handoff

These explain how the system evolved or preserve prior discussion state.

Examples:

- handoff notes
- review reports
- old session summaries
- old migration plans

Use for:

- provenance
- memory
- context transfer

These are useful, but not authoritative.

### 7. Generated / Evidence / Storage

These are outputs, receipts, corpora, or machine noise.

Examples:

- `artifacts/`
- `dist/`
- `build/`
- `output/`
- most of `training-data/`
- `exports/`
- local DB/cache files

Use for:

- evidence
- exports
- generated assets
- corpus storage

These should not define the system story.

## Authority Order

When documents disagree, resolve them in this order:

1. `docs/specs/CANONICAL_FORMULA_REGISTRY.md`
2. `CANONICAL_SYSTEM_STATE.md`
3. active runtime code and test lanes
4. operational docs
5. public docs
6. research notes
7. historical/handoff docs
8. generated evidence and storage

Lower layers must be updated when they drift from higher ones.

## Update Order

When runtime behavior changes, update in this order:

1. canonical formula or state file
2. code or test proving the behavior
3. operational map if the surface changed
4. public docs
5. research or handoff notes that still need to mirror the change

## Formula Change Rule

If a scoring law or runtime formula changes:

1. update `docs/specs/CANONICAL_FORMULA_REGISTRY.md`
2. update `CANONICAL_SYSTEM_STATE.md`
3. update any live runtime docs that name the old formula
4. mark the old formula as legacy, bounded, compatibility, or experimental

Do not present two formulas as “basically the same” unless they are explicitly defined as equivalent under a bounded mapping and the mapping is written down.

## Status Language Rule

Use one status vocabulary across the repo:

- operational
- pilot-ready
- enterprise/bank-ready
- experimental

Avoid broad “production ready” statements without scope.

## River Map for Documents

Use the following channel model when sorting docs.

### Main channel

Current canonical and operational docs.

Examples:

- `CANONICAL_SYSTEM_STATE.md`
- `REPO_SURFACE_MAP.md`
- this file
- `docs/specs/CANONICAL_FORMULA_REGISTRY.md`

### Side channel

Useful but non-authoritative support docs.

Examples:

- proposal support docs
- packaging notes
- release checklists

### Archive channel

Historical but intentionally preserved docs.

Examples:

- old review reports
- old migration plans
- old handoff notes

### Dry channel

Exploratory docs that should not flow back into the main narrative unless promoted.

Examples:

- phi/fractal experimental notes
- mesh theory branches
- draft proofs

### Gated channel

Generated outputs and storage-heavy evidence.

Examples:

- `artifacts/`
- `training-data/`
- exports
- generated reports

These can inform the system, but they do not own the story.

## Consolidation Rules

When multiple docs cover the same topic:

1. choose the highest-authority file as the destination
2. move short-lived checklists into an operational file
3. turn the old file into a pointer, or leave it historical
4. do not keep multiple “master” docs for the same subject

## Minimal Solo-Builder Doc Set

If the repo gets noisy, keep these current first:

1. `CANONICAL_SYSTEM_STATE.md`
2. `REPO_SURFACE_MAP.md`
3. `docs/specs/CANONICAL_FORMULA_REGISTRY.md`
4. this file
5. the operator doc for the lane you are actively using

Everything else can lag briefly without breaking the whole repo.

## Do Not Use the Repo as Blind Storage

Storage is acceptable.
Storage without classification is what breaks the repo.

If a file is mainly:

- generated output,
- dataset material,
- temporary evidence,
- screenshots,
- exports,
- or machine-state residue,

it belongs in a generated/evidence path and should be treated as gated channel material.

## Future Extension

If you later build a stateful doc-registry agent, treat it as an operator over this model, not a replacement for it.

The document model should stay simple enough to operate by hand first.
