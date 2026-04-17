# Sacred Tongues Governance System Canonical State

**Updated**: 2026-04-08  
**Purpose**: define what is canonical, what is legacy, and what is experimental so the working tree stops arguing with itself.

For the practical repo operating map, read `REPO_SURFACE_MAP.md`.
For the document classification and consolidation rules, read `docs/operations/DOCUMENT_MANAGEMENT_OPERATING_MODEL.md`.
For expanded-first naming rules, read `docs/CANONICAL_NAMING_EXPANDED_FIRST.md`.

## Authority Order

1. `docs/specs/CANONICAL_FORMULA_REGISTRY.md` — mathematical source of truth
2. Runtime entrypoints actually in use:
   - `api/main.py` — governance/control application interface
   - `src/api/main.py` — minimum-viable-product and product application interface
3. Test and benchmark lanes that prove current behavior
4. Public docs (`README.md`, `ARCHITECTURE.md`, website pages)
5. Legacy notes, historical reports, research drafts, handoff notes

If a lower-priority document disagrees with a higher-priority one, the lower-priority document is stale and must be updated.

## Current Canonical Runtime Formula

The canonical Layer 12 harmonic wall is:

`H(d*, R) = R^((φ · d*)²)`

Source: `docs/specs/CANONICAL_FORMULA_REGISTRY.md`

## Legacy Formula Status

The following formulas may still appear in older public docs, tests, demos, or historical notes:

- `H(d, R) = R^(d²)`
- `score = 1 / (1 + d_H + 2 * phaseDeviation)`
- `H(d,pd) = 1 / (1 + d + 2*pd)`

These should be treated as **legacy or bounded scoring variants**, not the current canonical harmonic wall, unless a file explicitly marks them as:

- legacy behavior,
- bounded runtime scorer,
- compatibility path,
- or experiment.

## Runtime Surface

### Governance Application Interface
- Entry: `api/main.py`
- Role: authorization, fleet scenarios, and audit/control-plane behavior

### Minimum-Viable-Product and Product Application Interface
- Entry: `src/api/main.py`
- Role: broader product endpoints, search/model behavior, and product-side flows

These are related but not the same runtime surface. Docs must label which one they are describing.

## Status Language

Use this wording unless a document has a narrower scope:

- **Operational**: yes
- **Pilot-ready**: yes
- **Bank-ready / enterprise-regulated-ready**: no
- **Mathematically active / evolving**: yes

Avoid blanket `production ready` statements without scope. If production language is used, it must say **which surface** is production-ready.

## Repo Reality

This repository currently contains several layers of work in one tree:

- canonical runtime code,
- public package surface,
- research and theory,
- training pipelines and datasets,
- demos and website surfaces,
- operational scripts and deployment targets.

That is acceptable for now, but it means:

- this repo is a **working lab + product repo**,
- not every file is canonical,
- and repo splitting should happen **after** the authority and surface map are stable.

## Immediate Documentation Rules

When runtime behavior changes:

1. update the canonical formula or state doc first,
2. update the repo doc or test that proves the change,
3. update the human-readable handoff/memory note if that lane is still being used.

## Near-Term Repo Boundaries

Do not split repos yet. First stabilize documentation and public/runtime boundaries.

When the repo is ready to split, the likely boundaries are:

1. `scbe-core` — governance and geometry core runtime package
2. `scbe-product` — product application interface, demos, site, search, user experience
3. `scbe-training` — corpora, training pipelines, and dataset generation
4. `scbe-research` — experimental theory, notebooks, and speculative branches

Until then, this repository remains the authoritative working tree.
