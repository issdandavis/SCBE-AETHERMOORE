# Monorepo Consolidation Authority

## Goal

Turn `SCBE-AETHERMOORE` from a clone-heavy research monorepo into a repo where a new person can:

1. clone it,
2. find the real product path quickly,
3. run the right surface without understanding the whole research universe,
4. ignore the rest unless they intentionally want research or archives.

This is a **single-repo consolidation plan**, not a repo-splitting plan.

---

## Primary Rule

The repo must expose four explicit zones:

1. `product`
2. `platform`
3. `research`
4. `archive`

Everything in the repository must be classifiable into one of those four zones.

If something cannot be classified, it is noise and should be moved, renamed, or removed.

---

## Zone Definitions

### Product

This is the smallest runnable surface that an outside operator should care about first.

Product code must satisfy all of these:

- directly runnable
- documented at the root
- owned
- tested enough to be treated as intentional
- not dependent on research-only scripts to boot

Current likely product-facing surfaces in this repo:

- `public/`
- `app/`
- `api/`
- `products/`
- `scripts/aetherbrowser/`
- selected product-facing docs in `docs/`

### Platform

Shared capabilities that the product actually depends on, but which are not themselves the first-run product surface.

Platform code should include:

- tokenizer and tongues infrastructure
- GeoSeal and governance runtime primitives
- coding spine / shared IR
- selected crypto and training-adjacent runtime primitives

Current likely platform-heavy surfaces:

- `src/tokenizer/`
- `src/tongues/`
- `src/coding_spine/`
- `src/governance/`
- `src/crypto/`
- `src/geoseal_cli.py`
- selected `python/scbe/`

### Research

Active experiments, generators, evaluation harnesses, training scripts, notebooks, and theory-linked implementation work that are still useful but are not required for the primary product boot path.

Research can be large, but it must be clearly marked as non-product.

Current likely research-heavy surfaces:

- `scripts/train/`
- `scripts/eval/`
- `scripts/benchmark/`
- `training/`
- `training-data/`
- `notebooks/`
- `notes/`
- `experiments/`
- `experimental/`
- `benchmarks/`
- `papers/`-like or reference-heavy note areas

### Archive

Historical, duplicated, superseded, imported, or dormant material that should remain available but should not shape the first-run experience.

Archive content should not live at the root if it is no longer first-class.

Current likely archive candidates:

- `external/`
- `external_repos/`
- `exports/`
- old demos or one-off intake/output trees
- stale screenshots and operator scratch files currently at repo root

---

## Product-First Clone Standard

A stranger should be able to clone the repo and do this in under five minutes:

1. read one root README,
2. identify the primary product surface,
3. run one documented command sequence,
4. know which directories are optional.

If the repo does not satisfy that, it is not consolidated enough.

---

## Root Authority Policy

The repository root must become narrow and intentional.

### Root should keep

- one canonical `README.md`
- one repo map
- one quickstart
- one environment template
- essential package/build manifests
- top-level legal and license files

### Root should stop carrying as first-class

- long theory dumps
- screenshot artifacts
- stale one-off reports
- multiple overlapping system summaries
- parallel README-like files with no clear authority

### Root documents that should become authority-linked, not peer competitors

These already exist and need hierarchy instead of duplication:

- `README.md`
- `README_INDEX.md`
- `REPO_SURFACE_MAP.md`
- `STRUCTURE.md`
- `ARCHITECTURE.md`
- `STATE_OF_SYSTEM.md`
- `SCBE_SYSTEM_OVERVIEW.md`

The root README should become the entry point, and the others should be subordinate references.

---

## Recommended First Consolidation Target

Do **not** begin by splitting the repo into multiple GitHub repositories.

Do begin by making one official product path and demoting everything else.

### Recommended operational target

Define one first-class product lane centered on:

- browser/runtime surface
- local API/provider surface
- the minimum platform libraries that support it

In current repo terms, that means the first consolidation pass should revolve around:

- `public/`
- `app/`
- `api/`
- `scripts/aetherbrowser/`
- selected `src/` runtime/platform modules

Everything else should explicitly support that lane, live in research, or move toward archive.

---

## Execution Phases

### Phase 1: Authority

Create and adopt:

- one product quickstart
- one repo zone inventory
- one root authority hierarchy

No large moves yet.

### Phase 2: Root cleanup

Reduce root-level noise by moving:

- screenshots
- stale reports
- one-off dumps
- historical notes

into `archive/` or `docs/archive/` style lanes.

### Phase 3: Product enclosure

Create one clear product subtree or product authority lane that defines:

- app entrypoint
- API entrypoint
- required env vars
- build/run/test path

### Phase 4: Platform enclosure

Mark which `src/` and `python/` modules are true platform dependencies.

These stay close to product.

### Phase 5: Research demotion

Everything experimental but valuable gets explicitly labeled as research and moved away from the first-run path.

### Phase 6: Archive and offload

Dormant or duplicated material moves to archive zones or cold storage.

---

## Non-Goals

This plan does not require:

- creating many new GitHub repos
- deleting research value
- deleting theory notes
- instantly repackaging the entire codebase

The job is to make the repo legible and runnable first.

---

## Success Criteria

The consolidation pass is successful when all of these are true:

- a clone newcomer can find the product path quickly
- the root no longer looks like a dump surface
- product, platform, research, and archive are explicit
- root docs stop competing with each other
- active research remains available without pretending to be product

---

## Immediate Next Moves

1. Maintain a machine-readable inventory of root surfaces and their target zones.
2. Write the product-first quickstart based on the chosen official lane.
3. Identify which root files are authority docs versus archive candidates.
4. Move obvious non-authority root clutter out of the first-run path.
