# Atomic node context and frozen-component stitch protocol

Status: **implemented mechanics; neural gain and training authorization absent**

Runtime profile: `PY_REFERENCE14+ATOMIC_STITCH_V1`

Date: 2026-11-13

## Outcome

The smallest useful context bundle is not a copy of every tensor. It is a
six-part packet that preserves identity while letting local node relationships
change:

| Part | Required state | Why it crosses a stitch |
|---|---|---|
| Identity deed | semantic root, representation ID, tokenizer ID, token-table SHA-256 | Prevents a derived view from becoming a new fact. |
| Frozen atomic state | exact token index, `AtomicTokenState`, six trits, negative/dual state, resilience, adaptivity, trust | Reuses the implemented token-to-atom map without changing it. |
| Local geometry | coordinate, typed neighbor IDs, distance, coupling, provenance | Gives each node a bounded neighborhood instead of an untyped dense context. |
| Dynamic controller | semantic charge, node hardness, edge tension, total-charge constraint | Lets relations alter a proposed weighting while preserving a global invariant. |
| Time/phase telemetry | monotonic step, context epoch, dimensionless drift increment, wrapped phase | Separates execution order from periodic phase. |
| Receipt | payload hash, parent hash, runtime profile, reaction packet, claim boundary | Makes every handoff replayable and tamper-evident. |

Storage is `O(N + E)` for `N` nodes and `E` local edges. A production graph
should keep `E` sparse. The reference solver is dense and therefore
`O(N^3)`; it is a correctness prototype, not the throughput kernel. A sparse
conjugate-gradient implementation is the later scaling path.

## Existing seams reused

- `python/scbe/atomic_tokenization.py` already supplies `AtomicTokenState`, the
  semantic element, six balanced trits, negative/dual state, and bounded
  resilience/adaptivity/trust values.
- `python/scbe/chemical_fusion.py` already combines node votes, edge
  electronegativity tension, coherence cost, and valence pressure.
- `python/scbe/reaction_state.py` already supplies canonical hashing,
  identity-bearing endpoints, loss accounting, and hash-linked receipts.
- `python/scbe/phdm_embedding.py` remains a geometric view. It does not receive
  compiler authority.
- The external Clay circuit at
  `loom/experiments/clay_open_core_20260730/CLAY_STISTA_MULTIPLANE_CIRCUIT.md`
  requires canonical serialization through the same frozen tokenizer before
  results re-enter Wafer A.

The external receipt is
`clay.stista-multiplane-current-validation.v1`, recorded on 2026-10-15 with
status `PASS_CURRENT_SOURCE_BINDINGS`, 7 planes, 17 components, 24 nets, and 6
routes. Its self-hash remains valid, but it is now **historical evidence**:
`src/scbe_14layer_reference.py` no longer matches the source digest pinned by
that receipt. The stitch registry binds the historical receipt digest and marks
the source drift instead of claiming a current validation. The receipt pins
tokenizer SHA-256
`6c14a5cd26188678f920273cff49483f535e340caa98e3a7eb4d3285286c37c6`,
vocabulary size 4096, and B256 table SHA-256
`fc85ad01480c1d0b72de32645b77538dfc0110cc58461eb9e8f9a50bc2d51009`.
Its runtime negative controls pass, but its promotion decision is `BLOCKED`
and `training_authorized` is false. This overlay does not alter that result.

## Local-to-global charge controller

For node `i`, the frozen atomic map supplies a local electronegativity-like
value `chi_i`. The new stitch solves the convex semantic controller

```text
E(q) = 1/2 q^T (H + L_K) q + (chi - H q0)^T q
subject to sum_i q_i = Q_total
```

where `H` is positive node hardness and `L_K` is the weighted local graph
Laplacian. The augmented linear system is

```text
[ H + L_K   1 ] [q]      [H q0 - chi]
[   1^T     0 ] [lambda] = [ Q_total   ].
```

This gives the requested behavior: each node responds to its own state and its
declared neighbors, while one exact global constraint prevents charge from
appearing or disappearing. Bounds are handled by an active-set solve of the
same convex quadratic. Each activated bound causes the remaining coupled
variables to be re-solved, and convergence is checked with equality,
complementarity, and projected KKT residuals. A radial rescale is not used.

This is **QEq-inspired semantic routing**, not a physical charge prediction.
In atomistic models, learned local electronegativities plus a global charge
equilibration constraint are an established way to include nonlocal charge
redistribution. They also have known pathologies such as spurious long-range
transfer and over-polarization, so shuffled-edge, dissociation, and cap
controls are mandatory. See:

- [Neural Message Passing for Quantum Chemistry](https://arxiv.org/abs/1704.01212)
- [A fourth-generation high-dimensional neural network potential with accurate electrostatics including non-local charge transfer](https://www.nature.com/articles/s41467-020-20427-2)
- [Incorporating long-range electrostatics in neural network potentials via variational charge equilibration](https://www.nature.com/articles/s41524-024-01225-6)
- [Pushing charge equilibration-based machine learning potentials to their limits](https://www.nature.com/articles/s41524-025-01791-3)

## The small stitch layer

The frozen runtime is not unfrozen. `frozen_stitch_protocol.py` registers one
continuous path:

```text
byte/token identity
  -> atomic tokenization
  -> local atomic neighborhood
  -> frozen chemical fusion
  -> STISTA multiplane contract
  -> pinned SCBE L0-L14 reference runtime
  -> named 9D telemetry envelope
  -> PHDM 21D geometric view
  -> deterministic action compiler
  -> frozen tokenizer re-entry
  -> reaction ledger
```

Each boundary declares:

- source and target component;
- payload schema and required keys;
- the only adapter-delta slots it accepts;
- a byte limit;
- freeze policy and authority;
- payload, stitch, and reaction-packet hashes.

Every contract wire schema must equal both the source boundary's declared
output schema and the target boundary's declared input schema. Payloads,
adapter deltas, and reaction packets are stored as canonical finite JSON, so a
caller cannot mutate a sealed envelope through a retained dictionary or list.
Verification rebinds packet step, operation, endpoints, component IDs, context
epoch, adapter delta, previous hash, and registry hash to the envelope. Compiler
hashes and gate decisions receive additional type/value checks. The envelope is
still an unsigned audit receipt, not an execution credential.

The registry also has a fail-closed policy floor. Runtime enum hints are
validated as values, registry lookup maps are read-only, and a caller-supplied
registry cannot downgrade `action.compiler`, remove its canonical gate-decision
enum, or assign execution authority to another component. Rehashing is not an
authority reset: the reaction packet must retain the three affirmative checks,
exact engravings, empty loss ledger, exact claim boundary, and only the declared
metadata/recalculation fields.

The reference-governance component pins the current
`src/scbe_14layer_reference.py` SHA-256 and inventories the actual callable
sections in execution order: intent modulation; complex state; realification;
weighted transform; Poincare embedding and distance; breathing; phase; realm;
spectral, spin, and triadic observations; harmonic scaling; audio observation;
then L13 risk decision. The stitch does not alter those functions or their
weights. It only gives the frozen runtime a typed STISTA ingress and a typed 9D
egress with the source digest and layer-contract output attached.

Only `action.compiler` has `EXECUTE_AFTER_GATE`. Atomic charge, STISTA,
telemetry, and geometry can propose, observe, or validate; none may bypass the
compiler. The default adapter delta is empty. The atomic seam exposes only
`edge_gain`, `charge_gain`, and `drift_gain`, each bounded to `[-1, 1]`.

The executable connection to frozen fusion is:

```text
w_i = max(0.05, 1 + charge_gain * q_i)
```

At `charge_gain = 0`, the stitched result is exactly the frozen fusion
baseline for the same nodes and edges. That equality is tested. Nonzero gain
is an intervention, not a promotion.

## Fiber and time analogies: bounded translation

The useful fiber-optic analogy is a transmission matrix with adjustable input
or junction conditions. Real multimode-fiber control uses an external spatial
light modulator, measured feedback, and an optimizer; the fiber does not simply
become self-aware. The software analogue is therefore an explicit controller
that changes bounded edge gains and measures crosstalk, throughput, and loss.
See [adaptive wavefront shaping in nonlinear multimode fibres](https://www.nature.com/articles/s41566-018-0167-7).

Token drift is similarly kept separate from physical time dilation. The
implemented scheduler telemetry is

```text
pressure = a * mean_charge_motion + b * congestion + c * route_cost
model_time_increment = 1 / (1 + pressure)
phase = (2*pi*frequency*step_clock) mod 2*pi.
```

`step_clock` is monotonic; `phase` wraps. This can schedule or visualize a
simulation, but it is not photon delay, proper time, or a relativity claim.

## Controls required before training promotion

Run all arms with identical token identities, data, seeds, parameter budgets,
and evaluator:

1. frozen fusion, `charge_gain = 0`;
2. the same number of random bounded adapter values;
3. shuffled local edges with unchanged degree distribution;
4. local-only message passing without the global charge constraint;
5. semantic equilibration plus bounded charge gain;
6. a size-matched ordinary MLP/message-passing adapter.

Measure exact round trip, conservation error, residual, finite outputs,
throughput, crosstalk, task loss, action validity, and source-disjoint
generalization. Use at least three seeds. Promotion requires the intervention
to beat both the no-intervention baseline and the size-matched control by two
pooled standard deviations. A mechanics pass is not a gain.

## Reproduce the mechanics receipt

```powershell
python scripts/research/atomic_context_stitch_demo.py not build the compiler
python -m pytest -q `
  tests/governance/test_atomic_context_bundle.py `
  tests/governance/test_frozen_stitch_protocol.py `
  tests/governance/test_atomic_tokenization_and_fusion.py `
  tests/test_reaction_state_packet.py
```

Current focused result: `51 passed`. This includes adversarial rehash,
custom-registry policy-downgrade, immutable-registry, and near-saturated
active-set cases. A separate fixed-seed stress probe compared 360 feasible
box-and-sum quadratics against exhaustive active-face enumeration and passed
every case.

The demo emits `PASS_MECHANICS_ONLY`, both frozen and nonzero-gain votes, the
semantic charges, conservation/residual diagnostics, all relevant hashes, and
an explicit `training_authorized: false` boundary.
