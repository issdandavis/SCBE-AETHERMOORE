# SCBE–Clay Multiplane Layer Map

**Map ID:** `scbe-clay-multiplane-layer-map-v1`  
**Version:** 1.2.0  
**Date:** 2026-07-31  
**Status:** implementation crosswalk and integration contract  
**Canonical SCBE profile:** named per execution; no cross-profile parity is implied

## Purpose

This map turns the earlier **Layer Ladder** artifact into an engineering
contract without confusing four different meanings of “layer”:

1. `SCBE.L01`–`SCBE.L14`: deterministic governance and telemetry runtime.
2. `HODGE.H0`–`HODGE.H3`: structural assurance over vertices, edges,
   triangles, and tetrahedra.
3. `TRAIN.T0`–`TRAIN.T4`: curriculum order for Clay data.
4. `CLAY.*` and `GEOM.*`: neural components and representation overlays.

`MULTIPLEX.*` is the typed identity/thread bridge between compatible planes.
It is not another meaning of numbered layer and does not become `SCBE.L15`.

The SCBE layer index remains authoritative for numbered runtime roles. The
Hodge ladder is an orthogonal verifier. It does not become four extra SCBE
layers, and the SCBE layers are not Transformer blocks.

## Authority and claim rules

Use evidence in this order:

1. executed code and tests for the named runtime profile;
2. `docs/specs/CANONICAL_FORMULA_REGISTRY.md`;
3. `docs/specs/LAYER_INDEX.md`;
4. `docs/CORE_AXIOMS_CANONICAL_INDEX.md`;
5. configuration and revision-pinned receipts;
6. public maps and research notes;
7. historical descriptions.

Every map entry uses separate labels:

| Field | Values |
|---|---|
| implementation | `active`, `experimental`, `compatibility`, `historical`, `missing`, `blocked`, `local_uncommitted` |
| verification | `passing_at_revision`, `test_defined`, `untested`, `failing`, `skipped`, `unobserved`, `stale` |
| claim class | `invariant`, `implementation_guarantee`, `measured`, `design_hypothesis`, `metaphor` |

“Measured” is not “integrated,” and “integrated” is not “improved a neural
model.” A neural promotion requires a controlled training result.

## System view

```text
TRAIN.T0..T4  ── prepares revision-pinned semantic bundles ───────────────┐
                                                                          v
GEOM.*         ── deterministic representation / input-side transforms ─> CLAY.*
                                                                          |
                                                                          v
SCBE.L01..L12 ── state, geometry, coherence, time, bounded score ─────────┤
                                                                          v
                                                                     SCBE.L13
HODGE.H0..H3  ── optional topology receipt ── explicit adapter only ──────┤
TLCFI.*       ── optional directed-path receipt ─ explicit adapter only ─┤
MULTIPLEX.*   ── optional same-joint cross-plane receipt ────────────────┤
                                                                          |
                                                                          v
SCBE.L14      <── telemetry, receipts, replay, operator-visible evidence ─┘
```

This is a dependency graph. Ordinal layer number is not necessarily execution
order. In particular, TypeScript and the compact Python reference compute
Layer 14 before Layer 13 because audio coherence is a risk input. The expanded
Python profile computes Layer 13 before producing its Layer 14 waveform.

## Plane A — canonical SCBE runtime

| ID | Role and axiom | Typed contract | Required invariant | Active symbols |
|---|---|---|---|---|
| `SCBE.L01` | Complex context state; Composition | context `t: R^D` → phase-aware `{real,imag}: C^D` | deterministic construction for fixed input/config | `layer1ComplexState`; `layer_1_complex_state`; `layer_1_complex_context` |
| `SCBE.L02` | Realification; Unitarity | `C^D` → `R^(2D)` | preserve the represented complex norm | `layer2Realification`; `layer_2_realification`; `layer_2_realify` |
| `SCBE.L03` | SPD weighted transform; Locality | `x: R^n`, metric `G` → `x_G: R^n` | `G` is symmetric positive-definite for the claimed general contract | `layer3WeightedTransform`; `layer_3_weighted_transform`; `layer_3_weighted` |
| `SCBE.L04` | Poincaré embedding; Unitarity | `R^n` → open unit ball `B^n` | finite output and `||u|| < 1` | `layer4PoincareEmbedding`; `layer_4_poincare_embedding`; `layer_4_poincare` |
| `SCBE.L05` | Hyperbolic distance; Symmetry | `u,v in B^n` → `d_H >= 0` | identity, symmetry, triangle inequality on the declared finite domain | `layer5HyperbolicDistance`; `layer_5_hyperbolic_distance` |
| `SCBE.L06` | Breathing transform; Causality | ball state + time/radial factor → ball state | radial diffeomorphism; **not** an isometry | `layer6BreathingTransform`; `layer_6_breathing_transform`; `layer_6_breathing` |
| `SCBE.L07` | Phase/Möbius transform; Unitarity | ball state + supported translation/rotation → ball state | preserve the supported metric behavior and ball containment | `layer7PhaseTransform`; `layer_7_phase_transform`; `layer_7_phase` |
| `SCBE.L08` | Realm distance; Locality | state + realm centers → minimum distance and realm identity | select over declared centers only; retain the winning-center receipt | `layer8RealmDistance`; `layer_8_realm_distance`; `layer_8_multi_well` |
| `SCBE.L09` | Spectral coherence; Symmetry | real signal → scalar in `[0,1]` | bounded, finite, and explicit empty-input policy | `layer9SpectralCoherence`; `layer_9_spectral_coherence` |
| `SCBE.L10` | Spin coherence; Symmetry | phases/phasors → scalar in `[0,1]` for active profiles | resultant is normalized by total magnitude/count | `layer10SpinCoherence`; `layer_10_spin_coherence` |
| `SCBE.L11` | Triadic temporal aggregation; Causality | short/mid/long evidence → non-negative aggregate | strict profile attribution; no unqualified parity claim | `layer11TriadicTemporal`; `layer_11_triadic_temporal`; `layer_11_triadic_distance` |
| `SCBE.L12` | Harmonic score; Symmetry | distance `d>=0`, phase deviation `pd>=0` → `(0,1]` | use registered `BOUNDED_SCORE = 1/(1+d+2pd)` | `layer12HarmonicScaling`; `layer_12_harmonic_scaling` |
| `SCBE.L13` | Risk decision; Causality | risk evidence + bounded score → decision + risk receipt | name the profile’s composition and decision enum | `layer13RiskDecision`; `layer_13_risk_decision`; `layer_13_decision` |
| `SCBE.L14` | Audio/telemetry output; Composition | signal/cross-system state → scalar coherence or waveform | output type and execution index are profile-specific | `layer14AudioAxis`; `layer_14_audio_axis` |

### Profile differences that must be recorded

| Profile | Layer 11 | Layer 12 | Layer 13 | Layer 14 and execution |
|---|---|---|---|---|
| `TS_PIPELINE14` | normalized quadratic mean | `BOUNDED_SCORE` | risk divided by score; `ALLOW/QUARANTINE/DENY` | scalar coherence; L14 executes before L13 |
| `PY_REFERENCE14` | normalized phi-power mean | `BOUNDED_SCORE` | weighted risk composition | scalar coherence; L14 executes before L13 |
| `PY_FULL14` | feature-space Euclidean aggregate | `BOUNDED_SCORE` | distance thresholds; `ALLOW/REVIEW/DENY` | waveform array; L13 executes before L14 |

There are additional wiring differences. `TS_PIPELINE14` and
`PY_REFERENCE14` feed the post-L7 state to L8 and feed L8 distance to L12.
`PY_FULL14` currently feeds L8 a pre-L6 state and feeds L11’s aggregate to
L12. A receipt must therefore include the profile and revision, not only
“SCBE 14-layer.”

## Plane B — Hodge structural assurance

The source artifact numbers these as layers 1–4. This map namespaces them as
`H0`–`H3` so they cannot be mistaken for `SCBE.L01`–`SCBE.L04`.

| ID | Lives on | Detects | Operator | Admission precondition |
|---|---|---|---|---|
| `HODGE.H0` | vertices | connected components | `L0 = d1 d1^T` | declared vertices |
| `HODGE.H1` | edges | loops | `L1 = d1^T d1 + d2 d2^T` | every edge endpoint exists |
| `HODGE.H2` | triangles | voids | `L2 = d2^T d2 + d3 d3^T` | every triangle face exists |
| `HODGE.H3` | tetrahedra | 3-cavities | `L3 = d3^T d3` | every tetrahedral face exists |

### Structural gates

1. **Closure gate:** require `d_k d_(k+1) = 0`. A higher simplex with a
   missing face is refused before the boundary matrix is built.
2. **Exact topology:** `beta_k = dim ker(L_k)`.
3. **Soft fill dial:** `beta_k(sigma)` counts eigenvalues at or below
   `sigma`. It measures near-holes without pretending they are exact holes.
4. **Hodge-only cospectral limit:** equal Laplacian spectra do not imply equal
   shape. This limitation does not apply to Layer 5’s coordinate metric or
   Layer 9’s signal FFT.
5. **Tangential probe bundle:** when a Hodge identity claim is made, a single
   overlay is insufficient. Use multiple attachment sites and retain both
   separating and blind-probe results.

Measured source behavior, reproduced 2026-07-30:

- filled versus hollow triangle: identical `L0`, `beta1: 1 -> 0`;
- hollow versus solid tetrahedron: identical `L0` and `L1`,
  `beta2: 1 -> 0`;
- incomplete triangle: refused at the missing face;
- six-vertex cospectral pair: non-isomorphic despite identical spectrum;
- pendant probes: 4/6 sites separated that pair and 2/6 were blind.

## Split invariant tracks

There is no active Hodge-to-Layer-13 adapter in the three canonical profiles.
The tracks remain separate unless a caller explicitly binds their receipts.

| Input change | SCBE metric/signal track | Hodge/TLCFI structural track |
|---|---|---|
| coordinate drift, same topology | Layer 5 can change | topology can remain unchanged |
| topology change, same sampled coordinates | Layer 5 may be blind | closure or Betti evidence can change |
| cospectral non-isomorphic graphs | unrelated until a graph-to-coordinate encoder is named | eigenvalue multiset is blind; probes may separate |
| signal change, same graph | Layer 9 can change | graph evidence remains unchanged |
| illegal directed CFG transition | Layer 5/9 do not establish edge legality | exact adjacency/path check must change |

### Measured same-input comparison

`C:\dev\loom\clay_split_invariant_tracks.py` runs the fixed six-vertex
cospectral pair through both tracks and an isomorphic relabel control.

| Comparison | Result | Reading |
|---|---:|---|
| cospectral pair encoded as ordered adjacency coordinates → Layer 5 | `d_H = 0.6650305663` | separates those coordinates |
| same pair encoded as sorted spectrum coordinates → Layer 5 | `d_H = 0.0` | upstream encoding is blind |
| one graph versus its isomorphic relabel, ordered adjacency coordinates | `d_H = 1.2680303279` | raw coordinate order creates a false difference |
| same relabel control, spectrum | max difference `2.22e-15` | relabel-invariant |
| Hodge spectrum on non-isomorphic pair | identical | cospectral blind spot confirmed |
| six pendant probes | 4 separating, 2 blind | multi-site bundle carries the useful structural evidence |
| Layer 9 constant versus alternating signal | `0.99999984` versus `0.0` | signal FFT is an orthogonal lane |

The conclusion is not “Layer 5 beats Hodge.” Layer 5 can only measure the
coordinates an upstream encoder preserves. Ordered adjacency preserves
label-specific details but is not graph-isomorphism invariant. Sorted spectra
are isomorphism-invariant but incomplete.

### Optional TLCFI track

TLCFI is related to SCBE but is not a numbered member of the canonical
fourteen-layer runtime.

The installed Python surface
`src/symphonic_cipher/topological_cfi.py`:

- uses directed adjacency, source/sink conditions, Ghouila-Houri, and exact
  bitmask DP for Hamiltonicity;
- builds runtime coordinates from graph-Laplacian **eigenvectors**, not an
  eigenvalue-multiset identity test;
- measures Euclidean deviation from a fitted principal curve, not Layer 5
  `d_H` and not Layer 9 FFT coherence.

On the fixed pair, its 3D pairwise embedding signature differed by `0.22984931`,
so the cospectral pair did not collide. But the signature also changed by
`0.37121452` under an isomorphic relabeling. The current truncated embedding is
therefore not established as a stable graph-identity invariant.

More materially, `TopologicalCFI.check_transition(0,1)` returned `VALID` when
both nodes existed but edge `0→1` did not. Its symbolic compatibility path also
returned valid because it checks repetition, not CFG adjacency. The
axiom-grouped `CFIMonitor` is a different implementation and does reject a
missing edge first. The TypeScript implementation uses golden-path position
and neighborhood Jaccard as a “spectral” proxy. Receipts must name the exact
surface.

Until the installed Python runtime checks edge membership, its principal-curve
result cannot be the sole legal-transition gate.

### Optional attachment points

| Runtime checkpoint | Optional structural evidence | Required scope |
|---|---|---|
| after `SCBE.L02` | `HODGE.H0` component receipt | only when the input declares a graph/node topology |
| after `SCBE.L03` | `HODGE.H0/H1` closure receipt | only when weighted relations claim preserved endpoints/edges |
| after `SCBE.L07–L08` | cycle/realm-topology receipt | only when a route claims topological preservation |
| before `SCBE.L13` | exact edge/path verdict, optionally Hodge probe bundle | only when Layer 13 consumes an explicitly configured adapter |
| `SCBE.L14` | evidence envelope | record observed, unobserved, and not-applicable fields separately |

If topology is unavailable, its mask is `unobserved` or `not_applicable`; it
is never silently converted into a zero residual or a pass.

## Plane C — Clay curriculum

The second-PC file `CLAY_TRAINING_LAYERS.md` defines this separate data order:

| ID | Curriculum role | Examples | Promotion requirement |
|---|---|---|---|
| `TRAIN.T0` | foundation | bytes, counting, number buckets, aligned symbol faces | substrate and primitive held-outs pass |
| `TRAIN.T1` | skills | arithmetic, correction/divots, precedence, self-hosting code | beat no-intervention and size-matched controls |
| `TRAIN.T2` | reasoning | process tokens, candidate ledgers, routing traces | evaluator verified; source-disjoint gain |
| `TRAIN.T3` | knowledge | broad code/math, representation and structural corpora | retention matrix shows no protected-skill regression |
| `TRAIN.T4` | identity | voice, tongues, multiview, brain/geometry | adapter or input-side branch starts as a no-op and passes promotion gates |

### `TRAIN.T3` external tool specializations

External tool adapters are catalog entries, not additional runtime or neural
layers. They receive no `SCBE.L*`, `HODGE.H*`, `GEOM.*`, or Transformer-block
number.

| Adapter ID | Neutral Clay surface | Stage | Current status |
|---|---|---|---|
| `ADAPTER.DESMOS.GRAPHING` | `CLAY.PLOT.2D` through `clay.plot.v1` | `TRAIN.T3` | `blocked`, `untested`, design hypothesis |
| `ADAPTER.DESMOS.GEOMETRY` | `CLAY.GEOMETRY.2D` through `clay.plot.v1` | `TRAIN.T3` | `blocked`, `untested`, design hypothesis |
| `ADAPTER.DESMOS.3D` | `CLAY.PLOT.3D` through `clay.plot.v1` | `TRAIN.T3` | `blocked`, `untested`, design hypothesis |

Shared promotion gate:

```text
TRAIN.T1 talk PASS
  AND TRAIN.T1 code/execution PASS
  AND TRAIN.T2 call -> executor -> tokenized result -> inverse/cycle PASS
```

Otherwise all three adapters remain blocked. Calls enter through the canonical
serializer and frozen tokenizer; results return through the same serializer and
tokenizer. No renderer or image tensor may bypass that route. Raw Desmos
documentation/API bytes have training weight zero; only Clay's neutral
tokenizer-visible envelope may re-enter at runtime. Boundary and licensing
details are in
`C:\dev\loom\experiments\clay_open_core_20260730\DESMOS_TOOL_BOUNDARY.md`.

The remote training note is a curriculum proposal, not the runtime layer
authority. Its useful rule survives: do not pour all corpora into a blind mix.
However, a downstream-only adapter cannot recover information destroyed by a
frozen input recurrence. New skills that require new input structure need
input-side access or a parallel sidecar, not merely more downstream width.

Current corpus authority is
`C:\dev\dataset-index\clay_hf_layer_manifest_v1.json`:

- 82 Hugging Face datasets inventoried;
- 26,698 complete semantic joints reference 80,094 multiview rows;
- status `BLOCKED_PENDING_TRANSFORMS`;
- `training_authorized: false`.

No training job may interpret catalog presence as license, contamination, or
schema approval.

## Plane D — representation and neural overlays

| ID | Component | Contract | Current status |
|---|---|---|---|
| `GEOM.CUBE_PINSTRIPE` | `C:\dev\loom\cube_pinstripe.py` | deterministic cube-face area warp | `experimental`, `measured`; 5.15545 → 1.22463 distortion receipt, but no automated signed-Jacobian/foldover/seam test and no neural ablation |
| `GEOM.COGNITIVE_CHANNELS54` | `src/cognitive_governance/hypercube_geometry.py` | 54 governance channels with inner/outer bounds | `experimental`; terminology and L2/L-infinity projection contracts require correction and direct tests |
| `GEOM.CUBE_TOKEN` | `python/scbe/cube_token.py`, `cube_faces.py` | core token with multiple derived faces | active components; reversibility must be declared per face, not once for the whole bundle |
| `GEOM.BINARY_HAMMING_COVER` | `C:\dev\loom\clay_binary_sphere.py` | finite Hamming-space cover/reachability | measured discrete overlay; not a continuous hypersphere |
| `CLAY.STATE21` | `C:\dev\clay-repo\home\training\clay_state21.py` | parameter-free cross-layer state/basin features | tested component |
| `CLAY.HARMONIC_TRACE` | `C:\dev\clay-repo\home\training\clay_harmonic_trace.py` | zero-gated neural sidecar | tested component; unified training gain explicitly unmeasured |
| `CLAY.CROSS_PRIMARY_BRAID` | `scripts/experiments/cross_primary_braid_consistency.py` | proposed cross-primary consistency experiment | `blocked`; dependency and durable input/output receipts are absent |
| `CLAY.CONNECTX_CUBE_VIEW` | local Clay training files | reversible ConnectX token view | `local_uncommitted`; not a pinstripe warp and not a neural win |
| `CLAY.SPLIT_INVARIANT_TRACKS` | `C:\dev\loom\clay_split_invariant_tracks.py` | coordinate, signal, Hodge, and TLCFI comparison | measured; 7 tests pass; runtime TLCFI left unchanged |
| `CLAY.INERT_BUFFER_CAPTURE` | `C:\dev\loom\clay_inert_buffer_gate.py` | zero-parameter buffer/capture sidecar with conserved main, quarantine, and removal lanes | `experimental`, measured mechanically; 13 tests pass; release gate defaults to exact zero; no live runtime or neural-gain claim |

Representation overlays may feed Clay or SCBE, but they do not acquire an SCBE
layer number. Their record must name:

```text
source schema + coordinate system + transform + inverse/loss declaration
+ invariants + provenance + objective + evaluator + revision
```

### Buffer–capture contract

The inert-buffer overlay keeps dilution and removal as different operations:

```text
M0 = M + C
chi = M / (M + B + epsilon)
e = (M / (M0 + epsilon)) * chi
```

- `B` is a non-reactive reserve. It lowers bounded contact concentration
  `chi`; it does not remove reactive inventory.
- `C` is pump-captured inventory. It is the only removal lane and requires a
  receipt.
- residual `M` is split between exposed and quarantined lanes; signed
  cancellation is reported separately and never called removal.
- `release_gate = 0` leaves the model input bit-exact, even when the proposed
  chamber settings are nonzero.

The fixed probe used a known reactive mask over a `512 x 32` array. Inert-only
and pump-only both produced `0.25` mean exposure and bit-exact equal tensor
output (`torch.equal`; `max|delta| = 0.0`), but their receipts were opposite: inert-only quarantined
`9819.45996` absolute units and removed `0`; pump-only quarantined `0` and
removed `9819.45996`. Combined exposure was `0.0625`. This proves the
accounting distinction, not a learned detector or capability gain.

The overlay stays before a trainable input-access sidecar and returns
`PASS/QUARANTINE` evidence to the existing policy. It does not replace
`clay_consolidate` recall-only quarantine or SCBE's canonical quarantine lock,
and it is not wired into command execution.

## Plane E — multiplex identity/thread bridge

Plane E restores the cross-plane bridge already present in
`C:\dev\loom\LAYER_STACK_ALL_PLANES.html` and implemented by
`C:\dev\loom\clay_multiplex.py`. It is an orthogonal overlay, not another
runtime stage.

| ID | Role | Typed contract | Boundary |
|---|---|---|---|
| `MULTIPLEX.IDENTITY_THREAD` | bind the same ordered vertices across two declared representation graphs | `(L1, L2, vertex_set_id, identity_map, w)` → supra-Laplacian receipt | equal cardinality and an explicit vertex bijection are required |
| `MULTIPLEX.CIRCUIT_BOARD` | connect TRAIN, GEOM, CLAY, SCBE, Hodge, multiplex, and evidence planes | typed pins/nets under one `semantic_joint_id` and one frozen tokenizer | circuit contract is wiring evidence; `training_authorized: false` |

For the implemented two-plane identity coupling:

```text
L_supra = [[L1 + wI, -wI],
           [   -wI, L2 + wI]]
```

The binding states that vertex `i` in one declared plane and vertex `i` in the
other represent the same semantic identity. It does not permit coupling
unrelated records or planes with different vertex sets.

The measured controls remain load-bearing:

- `w = 0` is blind;
- empty and complete reference graphs are universally blind because they
  commute with the compared Laplacians;
- noncommutation does not guarantee separation;
- path permutation `(0, 2, 5, 3, 1, 4)` is noncommuting but has separation
  `1.776e-15` at the measured tolerance.

Multiplex, Hodge, SCBE, tool, and executor results cannot enter the neural core
as hidden tensors. They must be canonically serialized and traverse the same
frozen tokenizer before re-entering `CLAY.WAFER_A`. B256 carries the resulting
token identity inside the model; this does not mean retokenizing between
Transformer blocks.

The executable circuit contract is:

- `C:\dev\loom\experiments\clay_open_core_20260730\clay_stista_multiplane_circuit_v1.json`
- `C:\dev\loom\experiments\clay_open_core_20260730\validate_clay_stista_multiplane_circuit.py`
- `C:\dev\loom\experiments\clay_open_core_20260730\CLAY_STISTA_MULTIPLANE_CIRCUIT_VALIDATION.json`

It maps seven planes to 14 components over 17 typed nets and six explicit
forward, re-entry, and backward/inverse routes. All STISTA/Loom siblings share
one information budget under their semantic joint; adding faces is consistency
training, not new entropy.

## Decision DAG and fail-closed behavior

```text
source accepted?
  no  -> REJECT
  yes
schema + license + split + revision complete?
  no  -> HOLD
  yes
representation transform passes its domain and inverse/loss contract?
  no  -> QUARANTINE
  yes
SCBE profile completes with finite bounded outputs?
  no  -> DENY
  yes
does this decision claim graph topology or identity?
  no  -> mark Hodge NOT_APPLICABLE
  yes -> require Hodge closure and the declared identity probes
does this decision claim a legal CFG transition?
  no  -> mark TLCFI NOT_APPLICABLE
  yes -> require exact directed edge/path membership
         (principal-curve deviation alone is insufficient at this revision)
SCBE.L13 decision + SCBE.L14 receipt -> RELEASE / QUARANTINE / DENY
```

## Verification and release gates

### Existing focused tests

```powershell
# Hodge artifact
python C:\dev\loom\clay_hodge.py
python C:\dev\loom\clay_hypergraph.py

# SCBE Python contracts
python -m pytest `
  tests/industry_standard/test_formal_axioms_reference.py `
  tests/test_l11_canonical_aggregation.py `
  tests/harmonic/test_pipeline14_governance.py

# SCBE TypeScript profile
npx vitest run tests/harmonic/pipeline14.test.ts

# Actual Clay cross-layer components
python -m pytest `
  C:\dev\clay-repo\home\training\test_clay_state21.py `
  C:\dev\clay-repo\home\training\test_clay_harmonic_trace.py

# Split invariant tracks
python C:\dev\loom\clay_split_invariant_tracks.py
python -m pytest -q C:\dev\loom\test_clay_split_invariant_tracks.py

# Inert buffer / pump-capture sidecar
python C:\dev\loom\clay_inert_buffer_gate.py
python -m pytest -q C:\dev\loom\test_clay_inert_buffer_gate.py

# STISTA/Loom multiplane circuit and multiplex bridge
python C:\dev\loom\experiments\clay_open_core_20260730\validate_clay_stista_multiplane_circuit.py
python -m pytest -q C:\dev\loom\experiments\clay_open_core_20260730\test_validate_clay_stista_multiplane_circuit.py
python C:\dev\loom\clay_multiplex.py
```

`tests/test_scbe_14layers.py` is a standalone custom runner, not a
pytest-collected authority, and its Layer 13 expectations are stale.

### Validation receipt — 2026-07-30

| Surface | Result |
|---|---:|
| `clay_hodge.py` self-test | `PASS` |
| `clay_hypergraph.py` self-test | `PASS` |
| SCBE focused Python suites above | `42 passed` |
| `tests/harmonic/pipeline14.test.ts` | `32 passed` |
| installed Python TLCFI existing suites | `33 passed` |
| TypeScript Hamiltonian CFI existing suite | `40 passed` |
| Clay State21 + HarmonicTrace tests | `24 passed` |
| split invariant tracks | `7 passed`; Ruff clean |
| inert buffer / pump-capture sidecar | `13 passed`; Ruff clean; py_compile pass |
| STISTA/Loom multiplane circuit | `8 passed`; 7 planes, 14 components, 17 nets, 6 routes; three exact tokenizer round trips |
| multiplex identity/thread bridge | `PASS`; includes `w=0`, two commuting controls, and the noncommuting-blind converse control |

The Clay run emitted one pytest-cache permission warning after the tests
passed; no behavioral test failed. The existing TLCFI suites pass, but they do
not cover the known-node nonedge accepted by the installed Python runtime; the
split-track characterization test records that gap separately.

### Neural promotion

A representation or sidecar is promoted only when it:

1. starts as an exact no-op or is compared with a matched parameter control;
2. runs at least three seeds;
3. beats both no-intervention and size-matched controls by more than
   `2 × pooled standard deviation`, otherwise prints `UNDERPOWERED`;
4. passes evaluator leak/collapse checks;
5. improves a source-disjoint downstream task;
6. preserves protected skills;
7. records data revisions, configuration, checkpoint hashes, and full receipts.

## Known contradictions to quarantine

1. `tower_map.py` and `clay_factory.py` carry stale SCBE formulas and must not
   be used as current layer authority.
2. The expanded Python file has historical header/comment claims that conflict
   with its live bounded Layer 12 and non-isometric Layer 6.
3. TypeScript Layer 3’s general SPD wording is broader than its current
   elementwise square-root implementation; treat the tested/default diagonal
   case as the supported contract until corrected.
4. The remote desktop’s `docs/specs/LAYER_INDEX.md` is older than the laptop’s
   2026-07-24 canonical index. It is evidence of drift, not an authority to
   merge back.
5. `LAYER_MATH_COMPRESSED.md` contains historical exponential/Cauchy Layer 12
   variants. Current fourteen-layer profiles consume `BOUNDED_SCORE`.
6. The installed Python TLCFI, the axiom-grouped monitor, and the TypeScript
   Hamiltonian CFI are behaviorally different surfaces. The installed Python
   runtime currently accepts an absent transition edge when both endpoint
   nodes are known.

## Provenance receipt

| Artifact | Location | SHA-256 / revision | Use |
|---|---|---|---|
| Layer Ladder artifact | `C:\dev\loom\LAYER_LADDER_ARTIFACT.md` | `3A8319071BA51653C00190596A53159A7A3170EA67FBE8ABFADB9A909E779ED3` | conceptual and measured Hodge source |
| Hodge implementation | `C:\dev\loom\clay_hodge.py` | `2FCFCEC31C712D4370A708504C10705C94C9F3C3E28FD372250772EA1BB8F629`; source commit `a99bdeb` | executable H0–H3 evidence |
| Hypergraph/probe implementation | `C:\dev\loom\clay_hypergraph.py` | `661E4B377F495F8B89CD5F4AD99CE952FA84A80666A07EDEFF75A657B67BAE38`; source commit `47e85c6` | closure, phase, cospectral, tangential evidence |
| Canonical SCBE index | `docs/specs/LAYER_INDEX.md` | commit `e44cb29fa` | runtime role authority |
| Canonical formula registry | `docs/specs/CANONICAL_FORMULA_REGISTRY.md` | active v2.0.0 | formula/profile authority |
| Remote curriculum | `DESKTOP-K2JGGGI:C:\Users\ddavi\dev\clay\CLAY_TRAINING_LAYERS.md` | `F9195B4D16EFC06727910C70E816302E746B2EB46D5110966BF01C984D7BAC90` | curriculum evidence only |
| Remote J-space formula | `DESKTOP-K2JGGGI:C:\Users\ddavi\dev\clay\home\writings\FORMULA_polymorphic_j_space_training_20260730.md` | `4682760562852BAD59D2C29BCAB963BE2C833742B4E04EBCE8B3CCCFEB70AD00` | design hypothesis only |
| Remote tangential tree | `DESKTOP-K2JGGGI:C:\Users\ddavi\dev\SCBE-AETHERMOORE\docs\specs\MECHANICAL_LAYER_TANGENTIAL_TREE.md` | `0380BAEDAA517C35284B195E9110044154ED90CBFBC1ED08B9999F9D137A1667` | architecture vocabulary only |
| Corpus manifest | `C:\dev\dataset-index\clay_hf_layer_manifest_v1.json` | `2014B4C241B64F2207D33BBEF91D24BCD84305B7A58D91F67313D9D6F2B18BF0` | training admission authority |
| Dual-PC handoff | `C:\dev\dataset-index\DUAL_PC_CLAY_DATA_HANDOFF_20260729.md` | `AD04C562E5C7017710F99B387EB9C71183F2A345A191F2B504D11CECDD2336FC` | bridge and semantic-joint receipt |
| Cube pinstripe receipt | `C:\dev\clay_home\evaluations\cube_pinstripe_20260730.json` | `AFE476951D4D2EF0F832905F6D880EDE859638C5A23D1A11DABA4B60EC6E559A` | measured geometric result only |
| Split-track source | `C:\dev\loom\clay_split_invariant_tracks.py` | `2A219376E50304EEAE2ACC5C2B36C94AB815FFBB29C4D565820E91C101415749` | reproducible coordinate/Hodge/TLCFI comparison |
| Split-track receipt | `C:\dev\clay_home\evaluations\split_invariant_tracks_20260730.json` | `CF9254883C3511218137465AAF851836EBC37D571DF17EF771F43C8E0C7E9434` | measured results and exact surface revisions |
| Inert-buffer source | `C:\dev\loom\clay_inert_buffer_gate.py` | `1B14C439BB6D41B98F1F2E3B9F4442B09BD3F28072F876A83998C2361154CB5A` | conservative zero-parameter buffer/capture sidecar |
| Inert-buffer receipt | `C:\dev\clay_home\evaluations\inert_buffer_gate_20260730.json` | `72A131DF25030E29A2C46E2AF8E3FF23F23A445C9D5999120D0685362030B2D9` | matched mechanical controls and claim boundary |
| Multiplex implementation | `C:\dev\loom\clay_multiplex.py` | `9C36D2EBCE51A284F7B191E94532A792F6AA46A13137EB7D02D40A7C7E501FCF` | measured two-plane identity coupling and blind controls; local-modified evidence |
| STISTA/Loom circuit | `C:\dev\loom\experiments\clay_open_core_20260730\clay_stista_multiplane_circuit_v1.json` | `3E6BE912DFBD7443C105C340222DFB5E2F99913ABD2D1EBBBC8F5632BDE3C272` | typed plane/component/pin/net contract; training remains unauthorized |
| Circuit validation receipt | `C:\dev\loom\experiments\clay_open_core_20260730\CLAY_STISTA_MULTIPLANE_CIRCUIT_VALIDATION.json` | `8740684AED761AB3C6B2B1D30563B5CDBF111C4A03B1998DF500CF08DB25383B` | exact local hashes, route counts, round trips, and multiplex controls |

The remote files were read in place over the existing `sidekick` SSH/Tailscale
route. No remote code, model, checkpoint, or dataset was modified or copied.

### Second-PC disposition

| Remote source | Disposition |
|---|---|
| `Dropbox\clay-kernel\bridge\clay_hf_layer_manifest_v1.json` | hash-identical to the laptop manifest; current data-admission evidence |
| `dev\SCBE-AETHERMOORE\docs\LAYER_INDEX.md` and `docs\specs\LAYER_INDEX.md` | internally consistent July 19 snapshot, but superseded by the laptop’s July 24 canonical index |
| `dev\SCBE-AETHERMOORE\docs\SCBE_FULL_SYSTEM_MAP.md` | useful cross-system inventory; supporting map, not formula authority |
| `dev\SCBE-AETHERMOORE\notes\sphere-grid\hodge\` | six provisional design overlays using an unvalidated `1.3x` multiplier; hypothesis only |
| `dev\SCBE-AETHERMOORE\src\cognitive_governance\hypercube_geometry.py` | experimental channel geometry; requires corrected terminology and direct invariants |
| `dev\SCBE-AETHERMOORE\src\storage\hypersphere_index.py` | experimental concentric retrieval geometry; keep separate from continuous cube pinstripe |
| `dev\SCBE-AETHERMOORE\src\fleet\drone-fleet\sphereCubeTopology.ts` | sphere-geodesic route constrained by cube bounds; separate fleet overlay |
| `dev\loom\DUAL_FACE_GRAPH_VEINS_RESULT_20260729.md` | newer than the remote Loom HEAD; uncommitted/copy-derived evidence |
| `dev\clay\home\ingest\dynamic_braid\README.md` | design/integration input; no promotion without an executable receipt |
| `dev\clay\CLAY_CONSERVED_LATTICE_PLAN.md` | plan only |

Remote checkout status at inspection:

- SCBE: clean `main@4eac200d`, reference-only versus the newer laptop lane;
- Clay: `agent/clay-training-process@10a2a48`, 110 dirty entries;
- Loom: `main@0baca0e`, 11 dirty entries.

Those dirty trees were deliberately not bulk-synchronized.

## Change control

Any future edit to this map must:

1. name the affected plane;
2. preserve the canonical `SCBE.Lxx` meanings;
3. record profile-specific execution order;
4. update exact source revisions and test receipts;
5. mark contradictions instead of silently reconciling them;
6. require a promotion gate before changing `experimental` to `active`.

The machine-readable companion is
`docs/specs/scbe_clay_multiplane_layer_map_v1.json`.
