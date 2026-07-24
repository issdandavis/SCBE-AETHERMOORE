# SCBE Canonical System State

**Version:** 2.0.0
**Updated:** 2026-07-24
**Purpose:** define authority, runtime profiles, and evidence language

## Authority Order

1. Executed code and tests for the named runtime profile.
2. `docs/specs/CANONICAL_FORMULA_REGISTRY.md`.
3. `docs/specs/LAYER_INDEX.md`.
4. `docs/CORE_AXIOMS_CANONICAL_INDEX.md`.
5. Runtime-specific configuration and receipts.
6. Public summaries and architecture maps.
7. Historical reports, articles, proposals, and research notes.

When a lower authority conflicts with a higher one, the lower document is
stale for that claim. Historical files may remain for provenance, but they do
not define current runtime behavior.

## Current Runtime Profiles

SCBE does not have one byte-identical fourteen-layer runtime. The active
profiles are:

| Profile | Source | Status |
|---|---|---|
| `TS_PIPELINE14` | `packages/kernel/src/pipeline14.ts` | active TypeScript pipeline |
| `PY_REFERENCE14` | `src/scbe_14layer_reference.py` | active Python reference |
| `PY_FULL14` | `src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py` | active expanded Python implementation |
| `PUBLIC_SCAN` | `src/index.ts`, `src/scbe_aethermoore/__init__.py` | package-facing scan/helper surface |

Their roles align, but Layer 11 aggregation and Layer 13 decisions are not
fully equivalent. A result must name its profile.

## Formula Resolution

There is no unqualified canonical harmonic formula. The registered regimes
are:

- `BOUNDED_SCORE`: fourteen-layer Layer 12 safety score,
- `BOUNDED_WALL`: bounded theorem/standalone risk multiplier,
- `QUADRATIC_EXP_COST`: squared-distance cost helper,
- `PI_EXP_COST`: resource and access-cost helper.

Exact equations and sources live in
`docs/specs/CANONICAL_FORMULA_REGISTRY.md`.

## Axiom Resolution

The repository has three distinct axiom surfaces:

1. five structural axioms organizing Layers 1-14,
2. operational rules A0-A7 in `config/scbe_core_axioms_v1.yaml`,
3. formula-level behavior tests such as
   `tests/industry_standard/test_formal_axioms_reference.py`.

Their mappings are documented in `docs/CORE_AXIOMS_CANONICAL_INDEX.md`.
Passing one surface does not prove all three.

## Evidence Language

Use these labels:

- **Invariant:** derived for a named formula and stated domain.
- **Implementation guarantee:** validated and tested behavior of a named code
  path.
- **Measured:** result tied to a dataset, command, configuration, and artifact.
- **Design hypothesis:** proposed mechanism requiring controlled evaluation.
- **Metaphor:** explanatory language with no proof status.

Do not use "mathematically guaranteed safe," "unbreakable," "100% secure," or
"production ready" without a bounded property, runtime, threat model, and
evidence artifact.

The repository-reported F1 value `0.813` remains a reported historical result
until one current artifact records the exact corpus, command, configuration,
and revision that reproduce it.

## Current Axiom Overlay

`AxiomLens` is the executable five-dimensional diagnostic overlay. It reports:

- five residual channels,
- an observation mask,
- evidence coverage and status,
- analytical state and time gradients,
- edge residuals and deltas,
- a lossy 3D stereo visualization.

An unobserved result is explicitly marked `unobserved`; zero observed loss is
not represented as complete evidence.

## Runtime Boundaries

The repository is a working lab and product tree containing:

- canonical runtime code,
- compatibility packages,
- experiments and theory,
- training and benchmark lanes,
- product and website surfaces,
- historical and proposal documents.

This is acceptable only while authority remains explicit. New code and docs
must point to a runtime profile instead of claiming repo-wide parity.

## Documentation Rules

When behavior changes:

1. update executable tests,
2. update the formula registry,
3. update the layer index,
4. update the public summary,
5. attach or regenerate the evidence artifact.

Compatibility shims may preserve old links, but only one file owns each
canonical document.
