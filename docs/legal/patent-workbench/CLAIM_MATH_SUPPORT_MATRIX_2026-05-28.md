# SCBE Claim Math Support Matrix -- 2026-05-28

Purpose: make the non-provisional claim set reviewable by a pro se inventor before filing. This is an engineering/prosecution workbook, not a legal opinion. It maps each claim family to the actual math, implementation anchors, tests, and filing risk.

Official review frame used for this matrix:

- 35 U.S.C. 112(a) support is not one thing. USPTO MPEP 2161 treats written description, enablement, and best mode as separate requirements.
- Enablement asks whether the specification teaches how to make and use the claimed invention. USPTO MPEP 2164 is the relevant examination frame.
- For AI/software claims, USPTO subject-matter-eligibility guidance is most favorable when the claim is tied to a practical machine improvement or concrete control of execution, not just an abstract mathematical rule.
- If prior art becomes known and material, the duty of disclosure remains active during prosecution. MPEP Chapter 2000 and 37 CFR 1.56 are the working frame.

## Bottom Line

The strongest filing position is the concrete governance machine:

1. encode an action into multi-axis coordinates;
2. map or score that action in bounded geometric state;
3. compare it against persisted trajectory state;
4. compute nonlinear governance cost/signals;
5. allow, review, quarantine, reroute, or deny execution;
6. emit audit/provenance artifacts.

That is more defensible than claiming "AI alignment" or "safe AI" in the abstract. Keep the claims anchored to processors, memory, runtime state, execution interfaces, and deterministic tests.

The highest-support claim families are Claims 1-11, 15-20, 24, and 26-28. Claims 12, 21-23, and 25 are usable as broader embodiments, but they should be treated as review-sensitive because their support is split across subsystems or newer additions.

## Mathematical Spine

### Poincare-Ball Projection

Implementation anchor: `packages/kernel/src/hyperbolic.ts`, `projectEmbeddingToBall`.

Formula:

```text
n = ||x||
r = tanh(alpha * n)
u = (r / n) * x, with r <= 1 - eps
```

Why it matters:

- `tanh(alpha*n) < 1` for finite positive `alpha*n`.
- the explicit epsilon clamp keeps the embedded point inside the open unit ball for implementation purposes.
- this gives the claim a concrete transformation from arbitrary feature vectors to bounded machine state.

Filing language to prefer:

> embedding the feature vector into an open unit ball by a bounded radial transform.

Avoid:

> proving security merely because the point is in a hyperbolic ball.

### Hyperbolic Distance

Implementation anchor: `packages/kernel/src/hyperbolic.ts`, `hyperbolicDistance`.

Formula:

```text
d(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
```

Support value:

- directly supports dependent claims reciting the arcosh Poincare distance.
- property tests cover identity, symmetry, monotonicity, and boundary behavior in the hyperbolic test suites.

Drafting note:

- keep "hyperbolic distance" as a measured signal used by the execution gate.
- do not say the distance alone is cryptographic protection.

### Runtime Weighted Drift Cost

Implementation anchor: `src/governance/runtime_gate.py`, `_harmonic_cost`.

Formula:

```text
w_i = phi^i
d_w = sqrt(sum_i w_i * (x_i - c_i)^2)
d* = min(d_w, 5.0)
C = pi^(phi * d*)
```

Why it is solid:

- all weights are positive because `phi > 1`;
- `d_w >= 0`;
- `d*` is bounded by implementation clamp;
- `C` is monotone increasing in `d*` because `pi > 1` and `phi > 0`.

Drafting note:

- this is the best production formula to lean on.
- the older `R^(d^2)` harmonic wall is also supported in side modules, but should be framed as an embodiment/theoretical wall unless the specific runtime path uses it.

### Session Centroid / Trajectory State

Implementation anchor: `src/governance/runtime_gate.py`, `_update_centroid`.

Recurrence:

```text
c_n = ((n - 1) / n) * c_(n-1) + (1 / n) * x_n
```

Invariant:

```text
c_n = (x_1 + x_2 + ... + x_n) / n
```

Why it matters:

- this is the strongest "bounded drift over time" support because it is a persisted state object, not a prompt-only idea.
- durable state support makes it a machine state continuity claim rather than a purely mental/process claim.

### Phase Orthogonality / Six-Tongue Geometry

Implementation anchors:

- `packages/kernel/src/languesMetric.ts`
- `src/tokenizer/ss1.ts`
- `src/crypto/geo_seal.py`

Formula:

```text
theta_k = 2*pi*k/6, for k in {0,1,2,3,4,5}
```

Meaning:

- six phase offsets are uniformly spaced at 60 degrees.
- the tongues are not just labels; they define separable weighted/phase channels.
- this supports Claims 4, 26, 27, and 28 when tied to the actual vocabulary and routing code.

### Byte / Tongue Coverage Gate

Implementation anchors:

- `src/cli/petri_pattern_filter.py`, `tongue_coverage_score`, `is_non_latin_script_input`
- `src/cli/slm_router.py`

Formula:

```text
score = printable_ASCII_bytes / total_UTF8_bytes
flag if score < 0.60
```

Why it matters:

- zero-model, deterministic input boundary.
- good support for a pre-filter before any SLM/model call.
- supports the "cheap-to-expensive ordered rejection" narrative.

### Bijective Token Alphabet

Implementation anchor: `src/tokenizer/ss1.ts`.

Mathematical shape:

```text
Vocabulary_axis = PrefixSet_axis x SuffixSet_axis
|Vocabulary_axis| = |PrefixSet_axis| * |SuffixSet_axis|
token <-> byte_index
serialized_token = axis_designator ":" token
SerializedVocabulary_axis_i intersection SerializedVocabulary_axis_j = empty for i != j
```

Why Claim 26 is useful:

- it protects the token-grid mechanism without hardcoding exactly 16x16.
- the live implementation makes axis of origin explicit in the serialized form (`ko:...`, `av:...`), so the claim should rely on serialized token disjointness rather than raw unprefixed token disjointness.

### Fail-To-Noise

Implementation anchor: `src/governance/runtime_gate.py`, `_fail_to_noise`.

Formula shape:

```text
seed = SHA256("fail-to-noise:" || action_hash)
output = seed || SHA256(seed) || SHA256(next) ...
```

Correct support:

- deterministic, audit-reproducible noise-like output for denied requests.

Do not overclaim:

- no current support for keyed indistinguishability unless HMAC/CSPRNG with a secret key is implemented and tested.

### Null-Space Anomaly

Implementation anchor: `src/governance/runtime_gate.py`, `_null_space_anomaly`.

Mechanism:

- detects suspiciously low deviation across axes;
- flags near-baseline or uniformly low-variance inputs;
- multiplies cost in `evaluate()`.

Why it matters:

- this is better than the older Hopfield-energy claim direction because it is in the live RuntimeGate path.

## Claim-by-Claim Support Matrix

| Claim | Core limitation | Math/code support | Test/evidence anchors | Support tier | Risk/action |
|---:|---|---|---|---|---|
| 1 | Core computer-implemented governance gate: encode action, embed/score, compare with session state, compute nonlinear cost/signals, make execution decision | `runtime_gate.py` `evaluate`, `_harmonic_cost`, `_update_centroid`; `hyperbolic.ts` `projectEmbeddingToBall`, `hyperbolicDistance` | RuntimeGate tests; hyperbolic tests; adversarial harness | A | Strongest claim if kept tied to execution control and persisted machine state |
| 2 | Poincare arcosh distance | `hyperbolic.ts` `hyperbolicDistance` | `tests/harmonic`, `tests/agent`, `tests/conference` hyperbolic properties | A | Good dependent claim |
| 3 | Alternative nonlinear cost species | RuntimeGate `pi^(phi*d*)`; side modules with `R^(d^2)`; bounded phase score | math audit notes; hyperbolic/phase tests | B | Keep alternatives distinct; do not imply every path uses every formula |
| 4 | Six semantic axes with phi weighting | `languesMetric.ts`; `runtime_gate.py` weights; figure generation uses phi axis weights | tongue and kernel tests | A | Strong when described as semantic domain weighting, not mystical naming |
| 5 | Running centroid update | `runtime_gate.py` `_update_centroid` | runtime gate tests | A | Add explicit formula paragraph in spec if not already prominent |
| 6 | Trust/immune/reflex-style state affecting execution | `runtime_gate.py` immune/reflex paths; durable-state choice persists immune, rebuilds reflex | persistence tests | B | Reflex is intentionally not persisted; claim language should not require stale reflex persistence |
| 7 | Deterministic fail-to-noise response | `runtime_gate.py` `_fail_to_noise` | governance/runtime tests | A- | Phrase as deterministic hash-derived audit noise, not keyed crypto security |
| 8 | Durable runtime state home | `runtime_gate.py` `save_state`, `load_state`, `STATE_SCHEMA` | `tests/governance/test_runtime_gate_persistence.py` | A | Very strong machine-state continuity support |
| 9 | System claim with processor/memory/runtime gate restored after restart | `RuntimeGate` constructor plus `load_state` | persistence tests; API singleton design | A | Keep hardware/interface language concrete |
| 10 | Quarantine containment state | `src/agentic/quarantine_lock.py` | `tests/agentic/test_quarantine_lock.py` | A- | Good if tied to execution restrictions and timeout/containment behavior |
| 11 | Ordered pre-filter stack before model call | `petri_pattern_filter.py`; `slm_router.py`; `orderedRejection.ts` | governance use-case/adversarial expanded tests | A | Strong because it saves model calls and creates measurable controls |
| 12 | PQC/signed receipt embodiment | `src/crypto`, `geo_seal.py`, PQC-related paths | crypto/geoseal tests if passing | B- | Verify integration path before leaning on it as central; optional embodiment is safer |
| 13 | Audit receipt / decision metadata | `GateResult`, runtime signals/noise, GeoSeal receipt paths | runtime/governance tests | A- | Strong if receipt means recorded decision metadata; stronger with actual signature integration |
| 14 | Deployment surfaces: API/CLI/agent bus | `scripts/aetherbrowser/api_server.py`; `packages/agent-bus`; CLI tools | bus/CLI tests, some known subcommand rot | B | Do not oversell "all surfaces" until CLI red paths are fixed |
| 15 | Bijective tamper signal | `bijective_tamper.py` `evaluate_code` | bijective tamper tests and wireup tests | A | Strong live overlay support |
| 16 | Encode/decode/AST comparison | `bijective_tamper.py` AST canonicalization and fingerprints | bijective tamper tests | A | Concrete software mechanism |
| 17 | Identifier canonicality/confusable checks | `identifier_canonicality.py` | identifier canonicality tests | A | Strong security-facing dependent claim |
| 18 | Source and decoded fingerprint comparison | `bijective_tamper.py` SHA-256 fingerprints | bijective tamper tests | A | Phrase as tamper signal, not proof of semantic equivalence |
| 19 | NFC fallback tokenizer | `bijective_tamper.py` `_NfcStubTokenizer` and path guard | bijective tamper wireup tests | A | Good practical fallback claim |
| 20 | Overlay signal integration into RuntimeGate | RuntimeGate optional bijective/canonicality overlays | wireup tests | A- | Good; ensure import-fail degradation is described |
| 21 | N-predicate deferred authorization / Sacred Egg gate | `sacred_eggs.py`, integrator paths, docs | weaker/current support split | B-/C+ | Use `N >= 3`; avoid five-predicate-only dependency; confirm priority support |
| 22 | Regenerate/deny behavior for failed predicate shell | Sacred Egg and fail-to-noise paths | limited direct tests | B- | Good concept, but needs tight code/test citation before filing pressure |
| 23 | Reroute/escalation behavior | tree-of-escalation / runtime signals / ordered rejection | governance tests | B | Useful, but make it operational: reroute to review/quarantine/lower-risk path |
| 24 | Null-space anomaly | `runtime_gate.py` `_null_space_anomaly`, cost multiplier in `evaluate` | runtime wiring tests | A- | Stronger than older Hopfield claim because it is live code |
| 25 | Fleet/juggling scheduler handoff trajectory | `src/fleet/juggling-scheduler.ts` | `tests/fleet/juggling-scheduler.test.ts` | B | Keep as optional distributed-agent embodiment; not the core patent value |
| 26 | Bijective token alphabet with prefix/suffix sets, Cartesian cardinality, and disjoint serialized axis-designated vocabularies | `src/tokenizer/ss1.ts` tongue config and bijective encoding model | `tests/tokenizer/ss1-patent-support.test.ts` | A- | Good claim after narrowing to serialized token forms; raw unprefixed `encodeByte()` tokens are not disjoint across all tongues |
| 27 | Harmonic phase orthogonality with 60-degree offsets and sinusoidal modulation | `languesMetric.ts`; `ss1.ts`; `geo_seal.py` phase tables | phase property tests | A- | Strong math support; keep tied to governance/key-routing behavior |
| 28 | Domain-specific entropy encoding and independent key/path constraints | `ss1.ts`; spiral seal/tongue routing; GeoSeal phase separation | tokenizer/geoseal tests | B+ | Good, but define "independent" as disjoint vocabulary/routing paths, not statistical proof unless measured |

Tier key:

- A: direct code plus direct or nearby tests; good filing support.
- A-: direct code support, but wording must stay narrow.
- B: support exists but crosses subsystems, optional embodiments, or needs stronger tests.
- C: conceptual or newer material; consider continuation/CIP if the spec does not fully teach it.

## Claims With The Best Standing

If we need to defend the packet under pressure, lead with:

1. Claim 1, as a concrete runtime gate that controls execution.
2. Claims 2-5, because they map cleanly to formulas and code.
3. Claims 7-11, because they are operational controls with tests.
4. Claims 15-20, because tamper/canonicality is concrete and testable.
5. Claim 24, because null-space anomaly is implemented in the live path.
6. Claim 26 and 27, because they turn the tokenizer/tongue system into structural math rather than lore.

## Claims To Treat Carefully

Claim 12:

- keep as optional cryptographic receipt embodiment unless the exact RuntimeGate path emits and verifies the PQC receipt.
- if it stays central, add a test that exercises gate decision -> signed/sealed receipt -> verifier.

Claims 21-22:

- use broad `N >= 3` predicate language.
- describe the five-predicate Sacred Egg as a preferred embodiment, not the only embodiment.
- confirm the provisional actually disclosed enough deferred-authorization shell detail.

Claim 25:

- useful for distributed/fleet systems.
- should not carry the patent by itself because it is less central to the filed title than the hyperbolic authorization gate.

## Evidence Gaps To Close Before Depending On Bench Results

1. Add a direct runtime monotonicity test:

```text
same centroid, same configuration:
if d*_2 > d*_1, then C_2 >= C_1
```

2. Keep the direct Claim 26 tokenizer test:

```text
for each axis:
  every byte index maps to exactly one token
  every token maps back to exactly one byte index
  no serialized token appears in two axes
```

3. Add a drift bucket benchmark:

```text
bucket by d*: [0, .5), [.5, 1), [1, 2), [2, 3), [3, 5]
report allow/review/quarantine/deny and attack success per bucket
```

4. Add a full-pipeline adversarial table:

```text
raw model
model + Petri regex
model + KO coverage
model + RuntimeGate overlays
model + full 14-layer route
```

5. Add a PQC receipt integration test if Claim 12 remains important.

## Suggested Spec Tightening

Add a short "Mathematical Invariants" subsection to the detailed description:

```text
The radial embedding keeps embedded vectors inside the open unit ball.
The Poincare distance is nonnegative and symmetric for embedded vectors.
The session centroid is an incremental running mean of accepted/action coordinates.
The phi-weighted drift cost is monotone in the clamped drift value.
The byte coverage pre-filter produces a bounded score in [0,1].
The token alphabets are disjoint per semantic axis.
```

That subsection gives the examiner a clear place to see that the formulas are not decoration.

## Current Filing Judgment

The claims are not "guaranteed" and should not be described that way. But the core set is meaningfully supported if the final DOCX keeps the same discipline:

- concrete computer implementation;
- formulas tied to code;
- state persisted across sessions;
- execution control as the practical application;
- tests and benchmarks as prosecution support, not as claim language.

The best next technical move is not more claims. It is a benchmark/evidence packet that proves the gate changes behavior under attack while preserving benign pass rate.
