# DTN Mars Comms — Curriculum Placement Guide

Generated: 2026-04-05 | Source: `training/intake/web_research/dtn_mars_comms.md`
Ingested: 13 oriented SFT records (L2:5, L3:8)

## 5-Agent Consensus: 20 Concept Placements Across L0-L3 + Training Pad

---

## L0 — Binary Substrate (4 placements)

| # | Concept | Tongue | Rationale |
|---|---------|--------|-----------|
| 1 | **Bundle Existence** (present/absent) | KO | Pure binary state: bundle IS or IS NOT at a node. `has_bundle = 1 or 0`. |
| 2 | **TTL as Binary Expiry Gate** | RU | `alive = (now < expiry) ? 1 : 0`. Irreversible one-way bit transition. |
| 3 | **Custody Transfer as Ownership Bit-Flip** | KO | Synchronized two-bit flip: `owner[sender]=0, owner[receiver]=1`. Atomic. |
| 4 | **Signal Occlusion as Binary Channel State** | DR | `channel_open = 0 or 1`. Mars behind the Sun = bit flip to 0. |

**L0 theme**: Every DTN primitive reduces to a single-bit or two-bit state transition with zero semantic content.

---

## L1 — Structural (6 placements)

| # | Concept | Tongue | Rationale |
|---|---------|--------|-----------|
| 5 | **Bundle Protocol Header Structure** | DR | 6-field protocol frame: source EID, dest EID, timestamp, TTL, payload, extensions. |
| 6 | **Contact Graph Topology** | DR/CA | Time-varying directed graph. Nodes = relays, edges = time-windowed contacts. |
| 7 | **Convergence Layer Architecture** | DR | Adapter pattern: heterogeneous transports → uniform bundle interface. |
| 8 | **Fragmentation/Reassembly Schema** | CA | Fragment metadata (offset, total_length, flags). Deterministic byte-level reassembly. |
| 9 | **Custody Transfer Chain** | KO | Directed acyclic ownership graph. Each hop ACKs custody, releases predecessor. |
| 10 | **Store-and-Forward Node Topology** | DR | Relay graph: nodes are buffers with forwarding rules. No end-to-end path required. |

**L1 theme**: DR-dominant (4/6). All concepts are structural patterns, protocol frames, and graph topologies — above raw binary, below semantic meaning.

---

## L2 — Semantic (5 placements)

| # | Concept | Tongue | Rationale |
|---|---------|--------|-----------|
| 11 | **Store-and-Forward as Deferred Meaning** | AV | Meaning doesn't require instant delivery. Stored in suspension until context resolves. |
| 12 | **Context Occlusion as Intentional Absence** | RU | Maps to null pattern. Blocked path ≠ failure. Absence IS trainable semantic signal. |
| 13 | **FEC as Redundant Meaning Encoding** | DR | 6-tongue system IS forward error correction. Same concept, 6 parallel channels. |
| 14 | **Mars Distance as Cognitive Latency** | CA | Deeper semantic work = higher "cognitive latency". L2 sits at "Mars distance". |
| 15 | **Custody as Layer Ownership of Meaning** | KO | Orientation handoff: L2 packet re-stamped as meaning transfers between stages. |

**L2 theme**: All 6 tongues except UM represented. The unifying insight: meaning is a routable, storable, redundantly-encoded resource that tolerates delay and absence.

---

## L3 — Governance (5 placements)

| # | Concept | Tongue | Rationale |
|---|---------|--------|-----------|
| 16 | **Custody Transfer as Trust Delegation** | RU | Governance act: authorize, delegate, revoke. Failure triggers rollback policy. |
| 17 | **Bundle TTL as Harmonic Decay Policy** | RU/CA | TTL parallels `H(d,pd) = 1/(1+φ*d_H+2*pd)`. Adversarial bundles expire before delivery. |
| 18 | **QUARANTINE = Context Occlusion** | RU | Occlusion is not rejection — it IS QUARANTINE. Held bundles await governance review. |
| 19 | **Contact Graph as Governance Schedule** | KO/RU | Processing windows = contact windows. Batch governance decisions during capacity. |
| 20 | **Axiom Custody Groups** | DR/RU | Each axiom is a jurisdiction. Causality owns L6/L11/L13, Symmetry owns L5/L9/L10/L12. |

**L3 theme**: RU-dominant (5/5 include RU). DTN's physical constraints become governance metaphors — the geometry enforces the policy.

---

## Training Pad Integration (5 exercises, 0 new code needed)

| Exercise | DTN Concept | Pad Component | What It Teaches |
|----------|-------------|---------------|-----------------|
| **DTN Relay** | Store-and-forward | `Cell.history` + `write()` FIX detection | Failure-storage IS the protocol, not a bug |
| **Solar Conjunction** | Occlusion tolerance | `LifeGuard.observe()` returning empty notes | Silence is a valid system state |
| **Ground Station Protocol** | Convergence layer | `Membrane.evaluate()` | Passing execution ≠ reaching destination |
| **Fragment Assembly** | Bundle fragmentation | Multi-cell `connect()` chains | Each fragment is independently valuable |
| **Contact Window Scheduling** | Contact graphs | `TrainingPad.run_and_release()` | Batch scheduling = Mars-style contact windows |

**Key finding**: The Training Pad already implements DTN semantics structurally. Every integration point needs only curriculum content, not new code.

---

## Tongue Distribution Across All 20 Placements

| Tongue | Count | Primary Domain |
|--------|-------|----------------|
| RU (Runeveil) | 9 | Governance, entropy, policy enforcement |
| DR (Draethis) | 8 | Structure, architecture, protocol design |
| KO (Korenth) | 6 | Intent, command, dispatch |
| CA (Caelith) | 4 | Compute, logic, latency |
| AV (Avalith) | 1 | Wisdom, deferred knowledge |
| UM (Umbravox) | 0 | Security (not represented — DTN is about tolerance, not threat) |

## Cross-Layer Concept Bridges

Some DTN concepts appear at multiple layers with different treatment:

- **Custody Transfer**: L0 (bit-flip) → L1 (chain topology) → L2 (meaning handoff) → L3 (trust delegation)
- **Store-and-Forward**: L0 (binary presence) → L1 (relay graph) → L2 (deferred meaning)
- **Occlusion**: L0 (channel state) → L2 (intentional absence) → L3 (QUARANTINE)
- **TTL/Lifetime**: L0 (expiry gate) → L3 (harmonic decay policy)

These bridges ARE the curriculum — same concept at increasing abstraction is how Polly learns depth.
