# SCBE Canonical Index Guide

This repository contains both canonical protocol material and active exploratory work.

Use this file to avoid mixing the public viewing path with archive or research noise.

## Canonical First

For the cleanest reading order, prefer:

1. `README.md`
2. `START_HERE.md`
3. `docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md`
4. `CANONICAL_SYSTEM_STATE.md`
5. `docs/specs/SCBE_CANONICAL_CONSTANTS.md`
6. `SPEC.md`
7. `CONCEPTS.md`

These are the safest files to treat as routing or definition surfaces.

## Public Implementation Guides

After the canonical files above, use:

- `docs/REPO_SURFACE_MAP.md`
- `docs/evidence/EVIDENCE_24_24.md`
- `docs/LAYER_INDEX.md`
- `docs/SCBE_SYSTEM_OVERVIEW.md`
- `package.json`

These help a technical reviewer understand where the live code and package surfaces actually are.

## Consolidation Authority

When the task is about making the repo legible as a product-bearing monorepo rather than a loose research dump, use:

- `docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md`
- `config/repo_consolidation_inventory.json`

These define the active product/platform/research/archive boundary strategy.

## Non-Canonical Or Lower-Authority Material

Treat these as useful but not authoritative by default:

- `experimental/`
- proposal packets
- historical notes
- demos and narrative surfaces
- notebooks, research fragments, and archive-heavy directories

## Source-Of-Truth Policy

If wording conflicts across files, prefer:

1. `CANONICAL_SYSTEM_STATE.md`
2. `docs/specs/SCBE_CANONICAL_CONSTANTS.md`
3. `SPEC.md`
4. `CONCEPTS.md`
5. implementation tests and active runtime code
6. exploratory or historical material

This policy exists to reduce indexing drift and to keep GitHub viewers from treating every experimental page as the product definition.
