# Triadic Braid Source Map

Date: 2026-05-02

Purpose: keep triadic braid work source-faithful before adding more agentic harness features. The repo already contains several distinct "three is stable" primitives. They should be wired together as a family, not reimplemented as a loose metaphor.

## Canonical Surfaces

### Tri-Bundle DNA

Canonical code:

- `src/crypto/tri_bundle.py`
- `src/crypto/harmonic_dark_fill.py`

Deprecated predecessor:

- `src/symphonic_cipher/scbe_aethermoore/tri_braid_dna.py`

Role:

- Packet and token substrate.
- Three bundles: Light, Sound, Math.
- Three sub-strands per bundle.
- Twenty-seven values per cluster before phi-scaled effective-state expansion.
- Order matters through inner bundle hashes and outer cluster hashes.

Harness use:

- Use for compact agent handoff payloads and bijective packet traces.
- Use `cluster_id`, `energy`, and `synchronization_score` as receipt fields.
- Do not route new work through `tri_braid_dna.py`; it points to `tri_bundle.py` as canonical.

### Layer 11 Triadic Temporal Gate

Source notes:

- `training-data/research_bridge_smoke/smoke-bridge-20260318T090000Z/sources/obsidian/01de077037_2026-03-13-l11-triadic-temporal-axiom-draft.md`

Live code:

- `src/crypto/dual_lattice_integration.py`

Role:

- Temporal and causal admissibility layer.
- Works over local path triads.
- Keeps `d_tri` as the triadic temporal distance.
- Uses a separate temporal residual for causal monotonicity, bounded velocity, and bounded acceleration.

Harness use:

- Use as the lane-change safety model for agentic workflows.
- A handoff can move lanes only when the previous/current/next action triad remains admissible.
- Bad transitions should emit explicit denial or quarantine witnesses instead of soft prose.

### Sheaf Consensus Three Watchers

Source notes:

- `training-data/research_bridge_smoke/smoke-bridge-20260318T090000Z/sources/obsidian/2b031292e5_aethermoor_spiral_engine_mvp.md`
- `training-data/research_bridge_smoke/smoke-bridge-20260318T090000Z/sources/obsidian/eddaefd8ac_sheaf_consensus_gate.md`

Live code:

- `src/harmonic/sheaf_consensus_gate.py`
- `scripts/sheaf_consensus_gate.py`

Role:

- Runtime gate over three temporal signals: fast, memory, governance.
- Computes `triadic_stable`, obstruction count, projected assignment, and ALLOW / QUARANTINE / DENY.

Harness use:

- Use for agent-to-agent delegation gates.
- Fast = immediate tool outcome.
- Memory = retained packet / prior trace compatibility.
- Governance = permission tier and route decision.

### NeuroGolf Triadic Anchor

Live code:

- `src/neurogolf/triadic_anchor.py`
- `src/neurogolf/token_braid.py`
- `src/neurogolf/pqc_braid_thread.py`

Tests:

- `tests/test_neurogolf_triadic_anchor.py`
- `tests/test_neurogolf_token_braid.py`

Role:

- Finds stable three-axis couplings in task topology.
- Token braid scores combine Sacred Tongue tokens, geometry, TritVoxel bands, and PQC fingerprinting.
- The default braid tongues are CA, UM, DR.

Harness use:

- Use to classify coding tasks into reusable skill families.
- A mini-skill should be promoted only when it shows stable triadic anchors across examples, not just one lucky trace.
- Use null-space and wormhole-axis reports to find compact handoff channels.

### Hamiltonian / Ternary Trust Tube Braid

Live code:

- `src/ai_brain/hamiltonian-braid.ts`
- `src/symphonic_cipher/scbe_aethermoore/ai_brain/hamiltonian_braid.py`

Tests:

- `tests/ai_brain/hamiltonian-braid.test.ts`
- `tests/test_hamiltonian_braid.py`

Role:

- Upgrades a single rail into a trust tube.
- Uses dual ternary phase states.
- Valid transitions are local in ternary phase space.
- Projection, braid distance, and harmonic cost make lane deviation explicit.

Harness use:

- Use for "blinker" signaling between lanes.
- Provider/model/language/permission lane switches should have a declared signal and a valid adjacent transition.
- Non-adjacent jumps should be flagged unless an explicit re-anchor or quarantine path exists.

## Agentic Harness Mapping

The agentic coding harness should treat "triadic braid" as four cooperating checks:

1. Packet braid: `tri_bundle.py` encodes the compact action/context/evidence packet.
2. Temporal braid: L11 checks previous/current/next action consistency.
3. Consensus braid: sheaf gate checks fast/memory/governance agreement.
4. Skill braid: NeuroGolf anchors check whether a task pattern is stable enough to reuse or promote.

Recommended handoff packet fields:

- `task_id`
- `from_agent`
- `to_agent`
- `lane`
- `lane_signal`
- `permission_tier`
- `tri_bundle_cluster_id`
- `packet_sha256`
- `semantic_shadow`
- `fast_signal`
- `memory_signal`
- `governance_signal`
- `triadic_stable`
- `l11_delta`
- `anchor_family`
- `anchor_quality`
- `decision`

## Next Implementation Target

Add a thin `TriadicHandoffGate` around the existing secure handoff layer:

1. Build a tri-bundle receipt for the compact handoff payload.
2. Require a lane-change signal when provider/language/permission tier changes.
3. Run sheaf consensus over fast/memory/governance.
4. Attach L11-style previous/current/next transition evidence when a trace has enough history.
5. Optionally attach NeuroGolf-style anchor evidence when promoting a mini-skill.

This gives the harness a stable three-point action frame without forcing every subsystem into one rigid polyhedral stack.
