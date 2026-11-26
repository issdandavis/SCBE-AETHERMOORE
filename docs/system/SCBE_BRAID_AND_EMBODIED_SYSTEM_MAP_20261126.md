# SCBE Braid and Embodied System Map — 2026-11-26

Status: executable-source crosswalk plus proposed integration boundary

## The shape already present

The deep idea is not one giant mechanism. It is a set of typed lanes that can
be braided without pretending they are independent entropy:

```text
canonical identity (bytes, source spans, hashes)
  -> exact views (trits, Six Tongues, AST roles, locations)
  -> geometric views (Poincare distance, palette, phase, wafer position)
  -> temporal braid (immediate, memory, governance, predictive)
  -> authority/state commitment (policy, action, result, previous root)
  -> capability-gated execution (software now; robot adapters later)
  -> signed receipt and replay
```

One byte rendered in six tongues is still one byte. One AST rendered as trits,
colors, and coordinates is still one AST. The value is in different operations
becoming cheap and inspectable, not in manufacturing new secret entropy.

## What is real today

| Mechanism                          | Status                              | Executable authority                                                 | Evidence checked 2026-11-26                                                            |
| ---------------------------------- | ----------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Temporal T-braid                   | IMPLEMENTED                         | `packages/kernel/src/tBraid.ts`                                      | 94/94 focused Vitest checks passed                                                     |
| Toroidal crossing braid            | IMPLEMENTED                         | `demos/toroidal_braid.py`                                            | 2,000/2,000 inverse trials; cyclic seam, writhe distinction, and braid relation passed |
| AST six-face trits                 | IMPLEMENTED                         | `python/scbe/ast_cube_encoder.py`                                    | 21/21 focused Pytest checks passed; exact source side lane retained                    |
| Fixed four-fixture context palette | IMPLEMENTED in adjacent lane        | `C:/dev/clay-wafer-net/clay_wafer_net/context_phase.py`              | 7/7 focused unittest checks passed                                                     |
| Six Tongues exact views            | IMPLEMENTED and previously measured | `C:/dev/six-tongues-geoseal/aethermoore.py` and SCBE tokenizer code  | architecture book records exhaustive round-trip evidence; not replayed in this slice   |
| Cross-vector token ledger          | IMPLEMENTED                         | `python/scbe/cross_vector_token_analysis.py` and token route sources | book records exact UTF-8 identity plus typed derived axes                              |
| Triadic Field Sequence Commitment  | PROPOSED                            | `docs/security/TRIADIC_FIELD_SEQUENCE_COMMITMENT_20260925.md`        | design and verification plan exist; production implementation absent                   |
| Repository source root             | IMPLEMENTED in this slice           | `src/integrity/repositoryManifest.ts`                                | deterministic manifest, Merkle root, and detached Ed25519 tests                        |
| `conlang-lang` lane                | UNKNOWN/STAGING                     | `C:/dev/conlang-lang/AGENTS.md` only                                 | no implementation files found                                                          |

## Two braids that must stay distinct

`tBraid.ts` computes four time-derived scalar strands, projects them into a 1D
Poincare interval, sums six pairwise distances, and derives a policy score. Its
Yang-Baxter test checks that an unweighted all-pairs distance is invariant under
strand permutation. This is a temporal-consistency observation.

`toroidal_braid.py` executes adjacent over/under crossings on a cyclic strand
array. It has inverse words, seam wrapping, and writhe. This is a reversible
route descriptor.

They can share a receipt, but one is not proof of the other. A safe adapter can
put the temporal metric in the state lane and the crossing word in a public
route-descriptor field, then sign the standardized commitment. Neither value is
secret key material.

## The syntax/fractal/palette bridge that is still missing

The AST encoder already supplies, per node:

- stable node type and depth;
- six signed tongue-role trits;
- a deterministic six-axis nested location;
- exact source bytes and SHA-256 in a separate bijective lane.

The context-palette sketch already supplies:

- exactly four fixtures;
- wall/inner-shell position;
- one hue per fixture;
- signed hue reflection;
- palette rollover between sessions.

No current adapter was found that takes an AST subtree, derives a declared
fractal scale, and applies that scale as a palette offset while preserving the
source identity and inverse/provenance record. That connection is PROPOSED, not
finished code.

Issac's quine observation supplies the recursion rule. A quine can be used as a
fractal generator when its verified reconstruction is iterated at smaller
scales:

```text
Q_0 = canonical seed
Q_(d+1) = reconstruct(execute(describe(Q_d)))
F_(d+1) = place(scale(F_d), route(Q_(d+1)))
```

The quine preserves the declared identity or invariant; the scale-and-place
operator creates self-similarity. A quine by itself is not yet a fractal. The
fractal claim requires a contraction or subdivision rule, at least two depths,
a stop condition, and a measured invariant across scales. Evolutionary quines
may change state, but each generation must retain the rule hash, parent hash,
and reconstruction receipt.

The smallest honest implementation is an `AstPaletteProjection` sidecar:

```text
input:  occurrence_id, AST node path, six face trits, source hash
quine:  versioned describe/execute/reconstruct rule and generation receipt
scale:  explicit contraction/subdivision operator with a named formula
color:  base hue + signed scale offset mod 360
output: derived palette coordinates + parent occurrence_id + transform version
check:  deterministic replay, reconstruction invariant, source identity unchanged,
        shuffled-offset control
```

It must remain a visualization/router feature until a controlled task shows a
gain over a size- and compute-matched ordinary positional encoding.

## From compute bricks to a growing embodied AI

The robot-kit idea already has separate ancestors:

- `docs/specs/HARDWARE_REQUIREMENTS.md` defines SOVEREIGN through SURVIVAL power
  tiers, including 5-25 W backpack/field compute;
- `docs/system/HARDWARE_SOFTWARE_AI_INTERCHANGE_MAP_20261107.md` implements a
  typed capability router with energy, latency, privacy, fidelity, and policy
  gates;
- `docs/research/vr_ai_operations_game_substrate.md` defines a body-in-loop VR
  operations room and later robot adapter;
- `docs/research/mtef_research_compendium_2026-06-17.md` records hybrid energy
  harvesting research while keeping integrated hardware unproven.

The missing joint is a measured modular-compute contract. A future brick should
declare at least:

```text
ComputeBrick {
  identity_root, firmware_root, model_root, owner_key_id,
  cpu, gpu_or_npu, vram_or_unified_memory, storage,
  idle_w, sustained_w, peak_w, thermal_limit_w,
  battery_wh, charge_inputs, measured_harvest_w,
  data_bus, power_bus, physical_ports,
  sensors, actuators, display_or_vr_endpoints,
  capabilities, forbidden_actions, emergency_stop,
  parent_bricks, assembly_receipt
}
```

Bricks form a graph, not a magical pooled GPU. The scheduler may place model
layers, KV cache, tools, and safety services only where bandwidth, memory,
thermal, power, identity, and policy all pass. Joining two bricks creates an
assembly receipt and a new capability set; it does not silently expand either
brick's authority.

Motion harvesting belongs on the input side of the power ledger:

```text
stored_energy_next = stored_energy_now
                   + plug_input
                   + measured_motion_harvest
                   - compute_draw
                   - motor_draw
                   - conversion_loss
```

The backpack motion source may extend standby time or charge sensors. It cannot
be described as powering a large GPU until measured watt-hours exceed the
complete compute, cooling, motor, and conversion budget. That comparison is a
design instrument, not a reason to discard the idea.

The screen is optional. The same brick may expose no display, a front/back
panel, a phone, or a VR endpoint. Perception and control remain typed I/O; an
actuator command still crosses collision, human-zone, energy, capability, and
emergency-stop gates.

## Build order

1. EXECUTED: establish the signed whole-repository source root so later work
   has trustworthy bytes independent of GitHub.
2. NEXT: implement the AST-to-palette projection as a sidecar with exact parent
   identity, deterministic replay, and a shuffled-offset negative control.
3. NEXT: define `ComputeBrick` and `BrickAssembly` schemas plus a simulator for
   power, memory, bandwidth, thermals, and capability composition.
4. LATER: connect the simulator to the existing interchange router and VR
   operations substrate.
5. HARDWARE-IN-THE-LOOP LAST: measure one physical compute brick and one motion
   harvester before making portable-runtime or energy-autonomy claims.

This ordering keeps the far-future vision intact while giving every step an
executable surface, a receipt, and a failure condition.
