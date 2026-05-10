# M6 SphereMesh / GeoSeed Network — Specification

Last updated: 2026-05-10
Status: **research substrate operational, sphere model pre-build**

## 1) What M6 is

M6 is the geometric substrate and training direction underneath M5.

M5 sells one governed read at a time. M6 is the model that those reads compose
into: a 6-seed, 6-tongue, multi-nodal geometry over the existing 14-layer
SCBE stack, with Sacred Eggs as the controlled mutation/genesis gate and a
21D canonical state lift for decision consistency.

M6 is not a product. M6 is what the M5 capture lane is feeding.

Where M5 is the sellable workflow foundry, M6 is the controlled genesis and
topology layer: how multiple seeds, tongues, nodes, and governance states
form a coherent network without losing auditability.

## 2) Design anchor

M6 has four invariants. Anything called "M6" must respect all four.

### 2.1) Six seed channels (the Sacred Tongues)

Six dimensions, each a 16x16 token grid (256 tokens), each weighted by powers
of phi (golden ratio). Each tongue has multiple **faces** — a routing face,
a coding face, a spirit face — that map bijectively to different downstream
artifacts.

| Tongue | Code | phi-weight | Routing face | Coding face (typical) |
|---|---|---|---|---|
| Kor'aelin | KO | 1.00 | command / control intent | Python |
| Avali | AV | 1.62 | transport / routing | JavaScript / TypeScript |
| Runethic | RU | 2.62 | policy / permissions | Rust |
| Cassisivadan | CA | 4.24 | computation / transformation | Mathematica |
| Umbroth | UM | 6.85 | privacy / protection | Haskell |
| Draumric | DR | 11.09 | schema / authentication | Markdown |

Each seed can initialize a node, role, or governance perspective. A
multi-nodal system is valid only when the combined state remains consistent
across the 14-layer pipeline. The phi-weighting is what makes the metric a
Langues Weighting System (LWS) and not just six parallel channels.

Real implementations:
- TypeScript: `src/tokenizer/`, `packages/sixtongues/`
- Python: `src/symphonic_cipher/scbe_aethermoore/` and root `symphonic_cipher/`

### 2.2) Fourteen-layer dressing and governance stamps

Every M6 record is dressed with the full 14-layer SCBE pipeline. No record
exists in M6 without a governance stamp.

The 14 layers (see `docs/LAYER_INDEX.md` for canonical detail):

| Layers | Function | Role in M6 |
|---|---|---|
| L1-L2 | Complex context → realification | Lifts raw input into the substrate |
| L3 | Weighted transform (LWS phi-weights) | Applies the 6-tongue weighting |
| L4 | Poincare embedding | Projects into the hyperbolic ball |
| L5 | Hyperbolic distance | Defines the metric M6 trains under |
| L6-L7 | Breathing transform + Mobius phase | Adds temporal dynamics, preserves metric |
| L8 | Multi-well realms (Hamiltonian CFI) | The realm-state machine M6 navigates |
| L9-L10 | Spectral + spin coherence (FFT) | Anomaly substrate |
| L11 | Triadic temporal distance | The d_tri(t) signal that intent-shapes M6 |
| L12 | Harmonic wall H(d, pd) = 1/(1 + phi*d_H + 2*pd) | The bounded score every M6 record carries |
| L13 | Risk decision | The decision M6 must learn to predict |
| L14 | Audio axis (FFT telemetry) | The cross-system signaling channel |

The 5-axiom mesh (Unitarity, Locality, Causality, Symmetry, Composition) gates
the whole stack — see `docs/CORE_AXIOMS_CANONICAL_INDEX.md`.

### 2.3) Sacred Eggs as controlled genesis gate

Sacred Eggs are the only controlled mutation surface in M6. New seeds, new
realms, new tongue grids only enter the substrate through an Egg. An Egg
carries:

- **hatch:** a new node or agent becomes active
- **tongue:** native routing channel
- **ritual:** training or school type
- **credits:** progress and trust history
- **shell integrity:** state protection and rollback boundary

An Egg only opens through:

- a quorum-signed governance event (the flock governor pattern in
  `project_mother_avion_auth`),
- a passing axiom-mesh check on the proposed mutation,
- a harmonic-wall score in the ALLOW band.

An egg should not become an unbounded autonomous actor. It enters through
governance gates and acquires privileges through observed behavior.

### 2.4) 21D canonical state lift

Every M6 decision lifts to a 21-dimensional canonical brain-state before the
decision is committed. This is the AI Brain Mapping in `src/ai_brain/`
(TypeScript canonical) and `src/symphonic_cipher/scbe_aethermoore/ai_brain/`
(Python reference).

The 21D lift exists so two M6 records produced by different tongues, different
times, different operators can be compared in a single common space. Without
the lift, the harmonic wall score is local; with the lift, it is comparable.

The lift is built from:

- 6 direct tongue axes
- pairwise tongue interactions
- higher-order interaction surfaces
- self-imaginary / internal-state axes

This is a research surface. Production use exposes only bounded, testable
outputs.

## 3) The substrate that exists today

This is what is real in the repo right now and what the M6 sphere model will
compose on top of:

| Layer of M6 | Real artifact |
|---|---|
| Six tongues (tokenizer + lexicon) | `src/tokenizer/`, `packages/sixtongues/`, `src/symphonic/`, lexicon drift gate `lexicon_dimension_report.py` |
| 14-layer pipeline (canonical) | `src/harmonic/pipeline14.ts` and the modules under `src/harmonic/` |
| 14-layer pipeline (Python reference) | `src/symphonic_cipher/` (CAUTION: dual-package collision, see `CLAUDE.md` §"Dual symphonic_cipher Packages") |
| Hyperbolic distance (L5) | `src/harmonic/hyperbolic.ts` |
| Hamiltonian CFI / multi-well (L8) | `src/harmonic/hamiltonianCFI.ts` |
| Spectral/spin coherence (L9-L10) | `src/spectral/index.ts` |
| Triadic temporal (L11) | `src/symphonic_cipher/.../causality_axiom.py` |
| Harmonic wall (L12) | `src/harmonic/harmonicScaling.ts` |
| Audio axis (L14) | `src/harmonic/audioAxis.ts`, `src/harmonic/vacuumAcoustics.ts` |
| 21D state lift | `src/ai_brain/` (TS) and `src/symphonic_cipher/scbe_aethermoore/ai_brain/` (Py) |
| Sacred Eggs (concept + auth path) | flock governor pattern; codified in memory; not yet a single module |
| 5-axiom mesh | `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/` |
| GeoSeal v1 primitives | imported by v2/compass/hyperbolic_rag (see `project_geoseal_v2_shape`) |
| Capture lane (M5 → M6 fuel) | HF datasets `polly-chat-live/`, `polly-leads/`, `polly-funnel/`; `scripts/polly/consolidate_to_sft.py` |

## 4) Governance requirements

Each M6 node must be able to emit:

- identity metadata
- seed lineage
- active tongue weights
- layer coverage
- risk tier
- recent state transitions
- parent / child or peer relationship
- rollback / quarantine route

If a node cannot emit all nine, it is not an M6 node — it is a proto-node and
must remain inside an Egg until it can.

## 5) The sphere model — what isn't built yet

The sphere model is the thing **named** "GeoSeed Network" — six seed spheres
arranged so that movement in any one tongue is a constrained motion on a
phi-spaced toroidal interlattice (see
`discovery_phi_toroidal_resonant_cavity`,
`discovery_toroidal_polyhedral_confinement`,
`discovery_gyroscopic_interlattice`).

The sphere model is research-stage. The substrate above can support it; the
glue does not yet exist as a single module. When it lands, it will live at:

- `src/geoseed/` — the sphere geometry, the phi-toroidal cavity, the 5
  Platonic constraint surfaces, the GeoSeal v1+ primitives composed into a
  single addressing scheme
- `scripts/train_m6_spheremesh.py` — the training entry point that consumes
  M5-captured SFT pairs (`polly-chat-live/`, `polly-leads/`) and trains the
  GeoSeed sphere assignments
- `tests/geoseed/` — invariance and equivariance gates (the same
  bit-identical equivariance pattern proved in
  `project_atomic_tongue_observer_result`)

These three paths are reserved. They do not exist yet. The substrate they
will compose is real.

## 6) Training signal

M6 training does not synthesize data. It consumes the M5 capture lane:

```
M5 paying customer → governed delivery → capture lane
        │
        ├─ polly-chat-live/   (chat traffic from Polly)
        ├─ polly-leads/       (form intake records)
        └─ polly-funnel/      (per-event funnel beacons, event-prefixed)
                │
                ▼
        scripts/polly/consolidate_to_sft.py --include-leads
                │
                ▼
        SFT training pairs (chat + lead-derived)
                │
                ▼
        M6 training entry (future scripts/train_m6_spheremesh.py)
```

This is the data-quality-beats-training-speed principle: M6 trains on real
governed deliveries, not on scraped corpora. M5 revenue is the M6 dataset.

## 7) Gates

M6 inherits all M5 gates and adds three of its own:

1. **Axiom-mesh gate** — every training step must clear the 5 axioms
   (Unitarity, Locality, Causality, Symmetry, Composition). See
   `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/`.
2. **Lexicon drift gate** — every released checkpoint must match the
   canonical 6-tongue lexicon. See `lexicon_dimension_report.py`.
3. **Executable promotion gate** — adapters need executable benchmark pass
   (not just training metrics) before release. See
   `tests/eval/multi_seed_gate_eval.py`.

If any gate fails, the checkpoint is not promoted and is not pushed to HF.

## 8) Minimal prototype (what to build first)

1. Define six seed records (one per tongue) with identity metadata, tongue,
   role, allowed action set.
2. Route a task through at least three nodes.
3. Record all handoffs in the agent bus
   (`.aethermoor-bus/workspaces/<workspace-id>/`).
4. Apply L13 governance to each transition.
5. Lift each transition state into 21D and store the lifted vector alongside
   the raw record.
6. Emit a final report showing lineage, risk changes, output provenance, and
   the 21D distance between input and output states.

This prototype does not require `src/geoseed/`. It exercises the substrate
that already exists and proves the M5 capture lane can serve as the M6
training feed.

## 9) Open research seams

These are real seams the sphere model will need to close. Each has a memory
entry with the current best understanding:

- **Toroidal polyhedral confinement** — phi-winding + 5 Platonic constraint
  surfaces as a continuous geometric hash; MitM-immune by construction.
- **Phi toroidal resonant cavity** — six phi-scaled walls; cost scales as
  R^(122.99·d²); cryptographic strength from geometry.
- **Gyroscopic interlattice** — phi-spacing as a controlled lattice
  distortion.
- **Polyhedral friction training** — constraint surfaces produce a training
  signal; an L_geometry loss term.
- **Gravity battery / Sisyphus** — training carves permanent paths through
  the polyhedral lattice.
- **47D complex manifold** — 6 real + C(6,2) + C(6,3) + 6 imaginary = 47D,
  matches the 47 lore realities.
- **Multi-attention holographic fold (MAHSS)** — combine K attention via HRR
  bound to roles, fold via L7 Mobius, query via unbinding.
- **DNA-strand composition substrate** — DNA-strand objects unify
  MAHSS / ΔS / circuit-breaker / slide / harness / telemetry.

The sphere model is the place where these compose.

## 10) Position vs external work

M6's defensible position is **multi-axiom composition over Geometric Deep
Learning** — patent-defensible cross-domain transfer through the 5-axiom mesh
plus the phi-weighted Sacred Tongues plus the harmonic wall.

External adjacent work:
- DARPA MRC (~2011-2017) — historical lineage, SCBE positions as
  post-quantum hyperbolic successor.
- Anthropic Petri — detection-only auditing tool; composes with SCBE
  enforcement, does not replace it.
- Anthropic Natural Language Autoencoders — SCBE primitives close several
  NLA limitations (harmonic wall = bounded faithfulness; Möbius equivariance
  kills steganography; 6 Sacred Tongues = multi-seed convergence answer; L14
  audio = anti-anthropomorphization channel).

## 11) Boundary

Do not sell M6 as a finished product until:

- node identity is deterministic and inspectable
- cross-node routing is logged
- privilege escalation is gated
- rollback and quarantine are tested
- buyer-facing language is separated from internal lore

Until then, M6 stays under the M5 cover: customers buy the read, M6 trains in
the back room.

## 12) See also

- `docs/M5_MESH_PRODUCT_SERVICE_BLUEPRINT.md` — the revenue surface that
  feeds M6
- `docs/LAYER_INDEX.md` — 14-layer canonical reference
- `docs/CORE_AXIOMS_CANONICAL_INDEX.md` — 5-axiom canonical reference
- `docs/LANGUES_WEIGHTING_SYSTEM.md` — phi-weighted Langues metric deep dive
- `docs/SCBE_SYSTEM_OVERVIEW.md` — pipeline architecture
- `docs/SPEC.md` — SCBE Kernel Specification (canonical)
- `docs/SYSTEM_ARCHITECTURE.md` — detailed architecture
