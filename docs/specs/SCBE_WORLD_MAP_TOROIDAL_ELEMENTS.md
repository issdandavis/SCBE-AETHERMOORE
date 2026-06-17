# SCBE World Map: Toroidal Board, Land, Air, Water

Status: working map over executable subsystems.

This document captures the elemental map that sits over the reversible cube
engine. The map is not the compute primitive. The compute primitive is the
bijective board/toroidal braid substrate. The map is the teaching and navigation
layer that lets the system be explained as a world.

## Core Split

| Layer | Meaning | Status |
| --- | --- | --- |
| Engine | Reversible board plus toroidal braid geometry. This is the substrate that can run forward and backward. | Executable proof in `python/scbe/toroidal_braid.py`. |
| Glass | Same operation substrate viewed through different decoders/faces. | Exists across cube faces, code faces, chemistry faces, and governance faces. |
| World map | Land, air, and water as system-function maps over the engine. | Useful for navigation, explanation, dashboards, and product framing. |

The engine is where correctness lives. The world map is where comprehension
lives.

## Proof Receipt

The toroidal braid proof uses crossings on a cyclic strand ring:

- `Crossing(i, over=True)` is an over-crossing between strand positions `i` and
  `i + 1 mod N`.
- `Crossing(i, over=False)` is the corresponding under-crossing.
- The inverse of a braid word is the reversed word with every crossing flipped
  over/under.
- The seam crossing wraps `N - 1` to `0`, making the board toroidal.

Current executable receipt:

```text
schema: scbe_toroidal_braid_proof_v1
samples: 2000
passed: 2000
strands: 8
word_len: 60
bijective: true
```

Additional invariants:

- Cyclic loop wraps around the torus and its inverse restores identity.
- Over and under produce the same endpoint permutation but opposite writhe, so
  they are distinct braids rather than plain swaps.
- The braid relation holds on the toroidal ring.

## Element Map

| Element | User phrase | System meaning | Grounded status |
| --- | --- | --- | --- |
| Board / Torus | "toroidal, over/under, cyclic, bijective" | Reversible braid-group substrate. This is the geometry everything sits on. | `python/scbe/torus.py`, `python/scbe/toroidal_braid.py`, `tests/test_toroidal_braid.py`. |
| Land | "grounded in code" | The solid build surface: opcode core, AST cube, polyglot/code emitters, and reversible address space. | `python/scbe/board.py`, `python/scbe/polyglot.py`, `python/scbe/ast_cube_encoder.py`, `rust/ast_cube`. |
| Air | "air out through physics and chemistry" | Transform/reaction faces: atomic tokenization, chemical fusion, physics and chemistry adapters, reaction-state packets. | `python/scbe/atomic_tokenization.py`, `python/scbe/chemical_fusion.py`, `python/scbe/reaction_state.py`, `src/physics_sim/`. |
| Water / Sea | "hydrofluidics, pipes of information, dams for water+power+multi-system, recycle water, last-use water as weight" | Flow and resource management: routing, pressure, reuse, governance gates as dams, receipts as reservoirs, and spacecraft-style multi-use resources. | `src/physics_sim/fluids.py`, `src/security-engine/policy-fields.ts`, `python/scbe/cognition_syscall.py`, `docs/research/chemistry_cli_space_systems_2026-05-31.md`. |

## Found Note Anchors

These are the strongest local anchors found during the note search. The repo
anchors are the canonical committed references. The `Documents/Avalon Files`
paths are local source-note mirrors found outside the repo.

| Topic | Local anchor | Why it matters |
| --- | --- | --- |
| Toroidal geometry | `python/scbe/torus.py`; `content/articles/2026-03-05-25d-quadtree-octree-hybrid.md`; `docs/specs/SCBE_TECHNICAL_PACKET_v1.md` | Establishes periodic locality, wraparound seams, phase torus, and toroidal cavity language. |
| Tesseract / hypercube | `docs/benchmarks/RUBIX_BROWSER_HYPERCUBE_BENCHMARK.md`; `docs/superpowers/specs/2026-05-22-geoseed-infinity-box-runtime.md`; `notes/theory/pooled-reaction-energy-storage.md` | Keeps tesseract language grounded as permission/state/phase geometry or solar-cavity metaphor, not a false physical claim. |
| Hypershapes | `docs/M6_SEED_MULTI_NODAL_NETWORK_SPEC.md`; `docs/SCBE_FULL_SYSTEM_MAP.md`; `tests/test_toroidal_polyhedral_proof.py` | Connects toroidal confinement, polyhedral constraints, and multi-node geometry. |
| Metamaterials | `notes/theory/2026-04-06-gyroscopic-interlattice-magnetic-arrays.md`; `docs/llms.txt` | Provides a hardware/material metaphor for topological edge behavior and post-quantum material framing. |
| Coding in chemistry | `notes/theory/binary-parental-tree-nodal-topology.md`; `notes/theory/hard-judge-concept-review.md`; `notes/round-table/2026-03-20-molecular-orbitals-of-context.md` | Grounds atomic tokenization, valence, bond strength, molecular context, and chemical fusion as the air/reaction layer. |
| Space chemistry and space systems | `docs/research/chemistry_cli_space_systems_2026-05-31.md`; `notes/theory/pooled-reaction-energy-storage.md` | Grounds the space lane in NASA CEA/PAHdb/SAM/CheMin-style evidence workflows and resource-aware energy storage. |
| Water / flow / pressure | `src/physics_sim/fluids.py`; `notes/theory/pooled-reaction-energy-storage.md`; `src/security-engine/policy-fields.ts` | Connects pipe pressure, water constraints, upkeep load, policy pressure, and governed release. |

### External Note Mirrors

| Topic | External local note | Found signal |
| --- | --- | --- |
| Tesseract light trap / energy storage | `C:/Users/issda/Documents/Avalon Files/2026-05-12 thermal energy vii sunlgiht trapping in a vaccume chamber lgihtnsystem.md` | Original "Tesseract Light Trap" thread; reframed as a solar thermal cavity/receiver where repeated reflection becomes heat and then slower storage/release. |
| Atomic tokenizer / chemistry coding | `C:/Users/issda/Documents/Avalon Files/Messges Dumps_trainging files/Untitled.md` | Glucose-string analogy, heavy-water weight analogy, atomic tokenizer as clean composable unit, and Mars/dynamic operations checkpointing. |
| STISA atomic token implementation | `C:/Users/issda/Documents/Avalon Files/theory/knowledge-graph-fill.md` | O(1) opcode-to-feature lookup, 8-dimensional atomic feature vectors, six-channel trit vectors, vectorized fusion, rhombic score, and execution metrics. |
| Metamaterials | `C:/Users/issda/Documents/Avalon Files/theory/2026-04-06-gyroscopic-interlattice-magnetic-arrays.md` | Topological gyroscopic metamaterials, Halbach-like directed confinement, and phi-toroidal resonant cavity mapping. |
| Toroidal cavity | `C:/Users/issda/Documents/Avalon Files/federal/DARPA_CLARA_Proposal_Master.md` | Combined toroidal cavity cost amplification figures and defense/proposal framing. |
| Tesseract correction / water constraints | `C:/Users/issda/Documents/Avalon Files/theory/pooled-reaction-energy-storage.md` | "Do not pool the light. Pool the reaction."; storage modes include water sourcing, panel cleaning, upkeep load, and reaction reservoirs. |

## Land: Code As Ground

Land is the stable surface. It is where code compiles, ASTs encode, opcodes
stand, and reversible addresses can be inspected.

Concrete subsystem mapping:

- `python/scbe/board.py` gives the reversible board address.
- `python/scbe/torus.py` wraps that board into periodic locality.
- `python/scbe/polyglot.py` emits code faces from the same operation substrate.
- `python/scbe/ast_cube_encoder.py` and `rust/ast_cube` turn source code into
  cube-vector terrain.

Land does not need to be a metaphor for compute power. It is simply the place
where the compute becomes solid enough to stand on.

## Air: Chemistry And Physics As Transform Space

Air is the transform field. It is where tokens become atoms, atoms become bonds,
and reactions decide whether a state is stable, uncertain, or unsafe.

Concrete subsystem mapping:

- `atomic_tokenization.py` maps tokens to semantic elements and six-channel
  trit vectors.
- `chemical_fusion.py` combines token states into reconstruction decisions.
- `reaction_state.py` gives a packet form for reaction-style transforms.
- `src/physics_sim/` provides real physics and fluid calculations that can
  become adapters or evidence lanes.

This is the correct place for chemistry language. It should remain a reaction
and decoder layer unless a real external chemistry engine is attached through a
receipt-bearing bridge.

## Water / Sea: Flow, Dams, Reuse, Pressure

Water is the sharpest system map because it is resource management, not just
visual texture.

In spacecraft and closed-loop engineering, one resource can have several lives:
drinking water, process water, radiation shielding mass, thermal mass, ballast,
reaction mass, and waste stream. The SCBE equivalent is an information/resource
flow that must be routed, slowed, reused, audited, or blocked depending on
pressure and risk.

Concrete subsystem mapping:

- Fluid mechanics: `src/physics_sim/fluids.py` computes density, velocity,
  dynamic pressure, pipe pressure drop, and flow properties.
- Governance pressure: `src/security-engine/policy-fields.ts` computes policy
  pressure in hyperspace.
- Decision dams: `python/scbe/cognition_syscall.py` maps governed calls into
  allow/escalate/deny style outcomes.
- Reaction reservoirs: `notes/theory/pooled-reaction-energy-storage.md` says
  to control the slower downstream reaction, output shape, audit trail, and
  release path.

So the dam is not decorative. The governance gate is the dam:

```text
intent/input -> channel pressure -> gate/dam -> audited release or hold
```

The water layer also explains save-points and reuse. If the engine is bijective,
then flow can be reversed to a checkpoint. If a resource is multi-use, the
system should not discard it after first use; it should route it through the next
safe function with a receipt.

## What Is Load-Bearing

Load-bearing:

- Bijective reversible engine.
- Toroidal braid substrate.
- No-aliasing discipline for reversible writes.
- Disjoint-lane commutativity for safe parallelism.
- Governance gate as a real flow regulator.
- Atomic/chemical token layers as real decoders and evidence transforms.

Not load-bearing yet:

- Terrain skins.
- Lands/sea visuals.
- Dashboard art.
- Any claim that the map adds compute power beyond the reversible Turing-complete
  substrate.

The map is valuable because it makes the system teachable and navigable. It does
not need to add compute power to be useful.

## Next Implementation Hooks

1. Add a `scbe world-map --json` command that emits this mapping as a machine
   readable packet.
2. Attach live proof receipts from `python.scbe.toroidal_braid.demo_receipt()`.
3. Add a water-flow demo that maps policy pressure to dam/open/hold/recycle
   decisions.
4. Add a dashboard layer later: land = code terrain, air = chemistry/reaction
   field, water = governed flow and resource reuse.
