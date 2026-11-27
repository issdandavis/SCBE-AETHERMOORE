# Patent, natural-math and hardware proof crosswalk

This is an engineering evidence map, not a legal opinion or a statement of
patent scope. The strongest preserved local claim snapshot available during
this review identifies itself as an internal drafting note and has SHA-256
`a6398a88bbfad16e965a5322dae6d5eb0484e7fd2f93d75d6bc36f911008b08f`.
The official filed specification and acknowledgement packet were not present in
the inspected sources, so claim numbers below are provisional mappings to that
recovered twelve-claim snapshot.

## Evidence labels

- **SOURCE**: text or code that exists at a named revision.
- **RESULT**: a theorem checked by Lean or a test that was actually executed.
- **INFERENCE**: a bounded interpretation of those results.
- **HYPOTHESIS**: a claim that still needs a controlled experiment.

## Recovered-claim map

| Recovered claim concept | Current formal result | What remains open |
|---|---|---|
| Claim 1: Poincare-ball authorization | `SCBE/Geometry.lean` proves the positive denominator, an `acosh` argument at least one, symmetry and the diagonal case for the exact distance argument. | Context provenance, trusted-realm construction, floating-point refinement and the deployed allow/deny threshold are not proved. |
| Claims 2-3: breathing and phase transforms | No general metric-invariance theorem is asserted. The executable audit retains a counterexample to the older general-isometry statement. | State the permitted transform class and prove its actual metric or deformation law. |
| Claim 4: topological CFI | `SCBE/Routing.lean` proves that every executed transition belongs to a supplied directed policy and that fuel bounds the path length. | CFG extraction, dimensional lifting, principal-curve construction and runtime deviation correspondence are separate obligations. |
| Claims 8 and 11: combined enforcement | `SCBE/Composition.lean` proves veto-preserving decision composition and that an authorized step needs both a legal directed edge and all checks allowing. | Show that every production adapter supplies all mandatory checks and that every execution surface uses the guarded step. |
| Claims 9, 10 and 12: false positives, overhead and precomputation | Lean establishes no performance result. | Controlled Euclidean baselines, query-latency measurements, memory cost and deployment receipts are required. |

## Natural mathematics versus fixed-width hardware

`SCBE/TokenArrays.lean` makes the boundary executable:

1. `naturalWeightedSum` is the exact natural-number reference semantics for a
   quantized non-negative token contribution.
2. `naturalWeightedSum_chunks` proves that any finite chunking has the same
   result as one full pass. This licenses independent block computation of this
   additive summary; it does not license arbitrary parallelization of an entire
   tokenizer or model.
3. `hardwareWeightedSum` models an unsigned `width`-bit accumulator as reduction
   modulo `2^width`.
4. `hardware_exact_of_noOverflow` proves equality with the natural semantics
   only when the exact total is below the word modulus.
5. `eightBit_wrap_example` is a checked counterexample: the natural result is
   `400`, while an eight-bit accumulator returns `144`.

The existing Python field uses signed floating-point weights and rounded matrix
coordinates. Its growth term uses weight magnitudes. The Lean integer model is
therefore a quantized hardware refinement boundary, not a claim that IEEE
floating-point execution equals real or natural-number arithmetic.

## Nested weighted token field

**SOURCE:** `python/scbe/nested_weight_token_field.py` defines

```text
side_i = base_side * nesting_ratio^i * common_growth_ratio.
```

**RESULT:** `nestedSide_succ` proves, in exact real arithmetic,

```text
side_(i+1) = nesting_ratio * side_i
```

for every layer and every common multiplier. `nestedSide_positive` proves that
positive base, ratio and multiplier produce positive sides. The Python suite
separately checks the rounded implementation with tolerances.

**INFERENCE:** the ratio invariant does not depend on how the common growth
multiplier is computed, so the bounded `exp(gain * tanh(...))` term may be
optimized without changing the exact recurrence, provided every layer receives
the same multiplier.

**HYPOTHESIS:** the representation improves learning, candidate selection or
throughput. Those are empirical questions, not consequences of the ratio proof.

## Six views, transitions and routing

The formal and experimental claims stay separate:

- **State result:** `SCBE/Codecs.lean` proves sequence round trips and
  cross-Tongue translation laws under six byte equivalences. The implementation
  audit checks the concrete 256-entry tables.
- **Transition hypothesis:** structured discrete corruption may exploit a
  geometry, but the useful contribution must be measured against other
  transition matrices.
- **Routing hypothesis:** pinned candidates and weighted alternatives may reduce
  work-to-recovery by choosing which unresolved byte to refine next.

The controlled three-arm experiment is specified in
`../../docs/specs/SIX_VIEW_MASKED_BYTE_ROUTING_BENCHMARK.md`.

