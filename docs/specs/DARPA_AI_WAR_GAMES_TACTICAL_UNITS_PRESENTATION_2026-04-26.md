# DARPA AI War Games: Multi-Domain Tactical-Unit Coordination Presentation

Date: 2026-04-26

Companion to: `docs/specs/DARPA_MILITARY_SYSTEMS_AGENT_BUS_TRANSFER_2026-04-26.md`

## Scope Guard

This document is a software architecture and proposal-support presentation. It uses public official government sources only and inherits the scope guard from the companion transfer map.

It does not describe weaponization, targeting, tactical deployment, evasion, physical-drone operation, kinetic engagement, or any content that crosses an export-control boundary. Every domain section below talks only about: software coordination, governance, evaluation, assurance, and command-inference patterns.

References to "tactical units" mean software-side coordination roles in a multi-agent governance system. They do not mean physical platforms.

## Why This Document Exists

The companion transfer map covers eight DARPA programs that anchor SCBE's general assurance and evaluation language (Assured Autonomy, CyPhER Forge, CASTLE, EMHAT, RACER, HACMS, AIxCC, SABER). Those programs anchor "what good agentic software looks like."

This presentation extends the map to public DARPA AI war-games programs that anchor "how multi-agent coordination is studied across air, ground, water, and mixed domains." It maps each domain to existing SCBE primitives so that proposals and capability statements can speak credibly about multi-domain agent coordination without leaving the assurance lane.

## Existing SCBE Primitives Re-Used

This presentation does not invent new constructs. It composes primitives that already exist in the repo.

### HYDRA Formations (`skills/codex-mirror/scbe-github-sweep-sorter/references/formations.md`)

| Formation | Use Pattern |
|---|---|
| Scatter | broad sweep, inventory, first-pass discovery |
| Hexagonal Ring | default six-tongue parallel collaboration |
| Tetrahedral | small packet, higher risk, fewer roles (KO + CA + UM + DR) |
| Ring | strict order, chain of custody, critical actions (KO -> AV -> RU -> CA -> UM -> DR) |

### Swarm Formation Primitives (`src/ai_brain/swarm-formation.ts`)

| Formation Type | Software Role |
|---|---|
| `defensive_circle` | equal-distance ring of agent watchers around a protected asset |
| `investigation_wedge` | trust-sorted probe of a suspicious signal |
| `pursuit_line` | tracking a moving anomaly across calls or sessions |
| `consensus_ring` | trust-weighted BFT voting positions |
| `patrol_grid` | continuous coverage of a route, schema, or monitoring surface |

### Sacred Tongue Bifurcation As Layered Command Inference

The six Sacred Tongues (Kor'aelin, Avali, Runethic, Cassivadan, Umbroth, Draumric) are inference channels with golden-ratio weights. The same incoming command is parsed in parallel through each tongue, and the union of inferences becomes the layered command record.

| Tongue | Phi Weight | Inference Lens |
|---|---|---|
| Kor'aelin (KO) | 1.00 | intent and architecture; "what should be true" |
| Avali (AV) | 1.62 | reactive integration; "what is changing right now" |
| Runethic (RU) | 2.62 | ethical and governance constraints; "what must not be violated" |
| Cassivadan (CA) | 4.24 | symbolic implementation; "how to make it true" |
| Umbroth (UM) | 6.85 | security and steganographic awareness; "what is hidden" |
| Draumric (DR) | 11.09 | schema, audit, release memory; "proof that it is true" |

Bifurcation here means: the command does not flow through a single decoder. Each tongue produces an inference. Disagreements between tongues are first-class governance events.

### 14-Layer Governance Wrapper

Every command-inference path is wrapped by the 14-layer pipeline before it reaches dispatch. The hard line is the Harmonic Wall at L12: H(d, pd) = 1 / (1 + phi * d_H + 2 * pd). L13 maps the score to ALLOW / QUARANTINE / ESCALATE / DENY.

### Authored-Moral-Anchor Doctrine

Per the project's fictional-moral-anchor record, agent allegiance is bound to an authored fixed reference (the Aethermoor canon), not to political or operator instructions of the moment. This is a software safety pattern: an agent that can be re-tuned by the local operator into harmful behavior is failing the same way uncritical squad obedience fails. The authored reference is the read-only baseline that the 14-layer pipeline scores against.

This pattern is implemented, not aspirational: the moral anchor is the immutable lore corpus and Sacred Tongue ethics distribution that ship with the model. It is not a sermon.

## Public DARPA AI War-Games Programs

For each program, only the public concept is summarized. No tactical, kinetic, or platform-specific content is reproduced. SCBE transfer in every case is software-only.

| Program | Public Concept (one sentence) | Domain |
|---|---|---|
| ACE | AI agents in human-machine collaboration for complex air engagements | Air |
| OFFSET | software architectures for collaborative heterogeneous swarms | Ground |
| CODE | collaborative autonomy under degraded communications | Mixed (Air-leaning) |
| Squad X | dismounted human-AI team coordination at small-unit scale | Ground |
| Sea Hunter / ACTUV | autonomous unmanned surface vessel program for long-duration missions | Water |
| BLACKJACK | resilient low-Earth-orbit mesh of small satellites with autonomous mission management | Mixed (Space) |

Official sources are listed at the end of this document.

## Domain-By-Domain Mapping

### Air Domain — DARPA ACE Anchor

Public concept: ACE explores how AI can collaborate with a human pilot on complex engagement decision making, with progressive trust calibration.

Software-only transfer to SCBE:

- the human-AI trust calibration loop maps to SCBE's existing trust-weighted consensus ring;
- ACE's "agent recommends, human decides" gate maps to `feat/agentbus-human-approval-tripwires`;
- progressive autonomy levels map to SCBE's existing risk tiers (ALLOW / QUARANTINE / ESCALATE / DENY);
- "explain why this recommendation" maps to layered command inference where every dispatch carries six tongue traces.

Formation primitives:

- `consensus_ring` for multi-watcher recommendation aggregation;
- HYDRA Tetrahedral (KO + CA + UM + DR) for tight high-risk recommendation packets;
- HYDRA Ring for strict-order critical decision approvals.

Layered command inference channels:

- KO surfaces the inferred operator intent;
- RU surfaces the governance / rules-of-engagement-equivalent constraints baked into the system;
- UM surfaces hidden or ambiguous signals (e.g. spoofed inputs);
- DR surfaces the audit receipt the operator will see.

SCBE feature branches affected:

- `feat/agentbus-human-approval-tripwires`
- `feat/agentbus-result-judges`
- `feat/agentbus-trace-spans`

Proposal angle:

SCBE provides a measurable, auditable trust-calibration substrate for human-AI teaming missions where the human keeps the decision and the AI keeps the receipts.

### Ground Domain — DARPA OFFSET + Squad X Anchors

Public concept: OFFSET studies software architectures for collaborative heterogeneous swarms with operator interfaces and mission-level abstractions. Squad X studies dismounted human-AI team coordination at small-unit scale.

Software-only transfer to SCBE:

- mission-level abstractions map to SCBE's mission envelope (`mission_id`, `risk_class`, `lease_seconds`);
- heterogeneous swarms map to SCBE's multi-provider model fleet (each provider is a distinct agent type with its own trust and cost);
- OFFSET-style "swarm tactics library" maps to the HYDRA formation primitives library above;
- Squad X human-AI teaming maps to the EMHAT lineage already covered in the companion transfer map.

Formation primitives:

- `patrol_grid` for continuous coverage of a code-base, schema, or monitoring surface;
- `investigation_wedge` for trust-sorted probing of an anomaly;
- HYDRA Hexagonal Ring for default parallel six-tongue collaboration;
- HYDRA Scatter for first-pass inventory of a new mission packet.

Layered command inference channels:

- KO defines the mission objective decomposition;
- AV tracks live state changes during execution;
- CA produces the implementation packets dispatched to each agent;
- DR records the audit trail and per-agent receipts.

SCBE feature branches affected:

- `feat/agentbus-mission-envelope`
- `feat/agentbus-scoreboard-routing`
- `feat/agentbus-trace-spans`

Proposal angle:

SCBE provides a heterogeneous-swarm coordination substrate where the swarm is software agents over governed providers, and every coordination decision is reproducible from the trace.

### Water Domain — DARPA Sea Hunter / ACTUV Anchor

Public concept: ACTUV studied long-duration autonomous unmanned surface vessel software with safe behavior under maritime rules and limited supervision.

Software-only transfer to SCBE:

- long-duration autonomous operation maps to SCBE's durable checkpoints and lease-bound mission envelopes;
- safe behavior under rules-of-the-road maps to the Harmonic Wall scoring at L12 and risk decisions at L13;
- limited supervision maps to SCBE's pre-rehearsal gate, where a digital twin run is required before dispatch;
- station-keeping and patrol patterns map directly onto `patrol_grid` and `defensive_circle`.

Formation primitives:

- `patrol_grid` for long-running coverage missions;
- `defensive_circle` for protective postures around a checkpoint or mission asset;
- HYDRA Hexagonal Ring as the default six-tongue posture during sustained missions.

Layered command inference channels:

- RU constantly checks rules-of-the-road-equivalent constraints;
- UM continuously scans for hidden or ambiguous signals;
- DR maintains the durable audit log;
- KO holds the mission intent across long runs.

SCBE feature branches affected:

- `feat/agentbus-durable-checkpoints`
- `feat/agentbus-default-rehearsal-gate`
- `feat/agentbus-result-judges`

Proposal angle:

SCBE provides governed long-duration autonomous-mission software where every decision step is checkpointed, scored, and recoverable from a durable audit record.

### Mixed Domain — DARPA CODE + BLACKJACK Anchors

Public concept: CODE studies collaborative autonomy under degraded or denied communications. BLACKJACK studies resilient low-Earth-orbit constellations with autonomous on-orbit mission management.

Software-only transfer to SCBE:

- "degraded comms" maps to SCBE's existing failure-mode handling (offline providers, missing files, budget exhaustion);
- "resilient mesh" maps to SCBE's BFT consensus ring and trust-weighted voting;
- "on-orbit autonomous mission management" maps to SCBE's bus rehearsal gate plus durable checkpoints;
- mosaic-style heterogeneous composition maps directly to the multi-provider, multi-tongue inference model.

Formation primitives:

- `consensus_ring` for trust-weighted BFT voting under degraded comms;
- `pursuit_line` for tracking an anomaly across providers when one channel is silent;
- HYDRA Ring for strict-order critical-decision approvals when consensus is split.

Layered command inference channels:

- AV detects channel degradation in real time;
- UM surfaces possible spoofing on the surviving channels;
- RU enforces the governance fallback rules;
- DR records what happened during the degraded window so post-hoc review is possible.

SCBE feature branches affected:

- `feat/agentbus-simulation-mode`
- `feat/agentbus-default-rehearsal-gate`
- `feat/agentbus-durable-checkpoints`
- `feat/agentbus-trace-spans`

Proposal angle:

SCBE provides governed collaborative autonomy under degraded conditions, where degraded means provider failure or signal spoofing in the software bus, not kinetic environments.

## Cross-Domain Coordination Pattern

The same SCBE primitives compose across all four domains because the substrate is the same: governed multi-agent software with auditable command inference.

Standard cross-domain mission shape:

1. Mission envelope created with `mission_id`, `risk_class`, `lease_seconds`.
2. HYDRA Scatter for initial inventory; Hexagonal Ring becomes the default working posture.
3. Each command parses through all six tongues in parallel; disagreements raise governance events.
4. 14-layer pipeline scores the command; L12 Harmonic Wall is the hard line; L13 maps to ALLOW / QUARANTINE / ESCALATE / DENY.
5. If the action is critical, the mission switches to HYDRA Ring (strict KO -> AV -> RU -> CA -> UM -> DR ordering) for chain-of-custody attestation.
6. Results write back into durable checkpoints and trace spans.
7. Independent frozen evaluations gate any adapter promotion that came out of the mission.

This pattern is dimension-agnostic. The reason it scales across air, ground, water, and mixed scenarios is that nothing in the pattern depends on the physical domain; it depends on the governance and evaluation primitives.

## Authored-Moral-Anchor Layer

The companion transfer map already covers HACMS-style high-assurance and SABER-style red-team evaluation. This presentation adds the moral-anchor layer explicitly, because multi-domain coordination programs raise the question of agent allegiance.

The relevant safety pattern is:

- agents have a read-only authored reference (Aethermoor canon plus Sacred Tongue ethics distribution) that ships with the model and cannot be over-ridden by operator instructions of the moment;
- the 14-layer pipeline scores every command against this reference;
- the moral-anchor layer is exposed as a measurable artifact: the distance d_H of an action from the authored reference is part of the audit trail.

The failure mode this pattern prevents is the "competent squad with no moral anchor" failure mode: an agent that is technically capable but loses its baseline behavior under operator pressure. The authored anchor is what makes operator pressure a measurable input rather than a successful steering attack.

In proposal language: SCBE provides not just continual assurance against system drift, but continual assurance against operator-driven drift, with a measurable distance metric to the authored baseline.

## Proposal Language To Preserve (Additions)

The companion transfer map listed twelve preserved phrases. This presentation adds:

- multi-domain coordination substrate;
- heterogeneous-provider swarm coordination;
- governed long-duration autonomous mission software;
- collaborative autonomy under degraded conditions;
- layered command inference;
- authored-moral-anchor distance metric;
- cross-domain reproducibility from trace.

## Near-Term Work Items

These items extend the transfer-map work list and are scoped to existing feature branches.

1. Add a "domain tag" field to the mission envelope (air / ground / water / mixed / generic), defaulting to generic.
2. Add a "tongue inference disagreement" event type to trace spans.
3. Add a measurable `moral_anchor_distance` field to mission summary records.
4. Add a long-duration-mission test to the result judges that exercises durable checkpoints over many cycles.
5. Add a degraded-comms simulation profile to simulation mode.
6. Add cross-tongue agreement statistics to the scoreboard.

## Notion-Sourced Formation Patterns (software-only reframings)

The repository's HYDRA formations document (Scatter / Hexagonal Ring / Tetrahedral / Ring) and the swarm formation enum (defensive_circle / investigation_wedge / pursuit_line / consensus_ring / patrol_grid) are the starting set. The internal Notion knowledge base contains additional formation, fault-tolerance, and role-mapping material that is older than this presentation and that the operator wants surfaced. Each item below is the software-only reframing of a Notion-sourced pattern. Nothing in this section authorizes physical-platform behavior.

### Concentric Rings (hierarchical inner / outer membership)

Distinct from the existing HYDRA Ring (which is sequential KO -> AV -> RU -> CA -> UM -> DR for handoff order), Concentric Rings is a spatial/role topology: an inner ring of hidden / high-priority agents (KO, AV, RU) wrapped by an outer ring of public-facing / peripheral agents (CA, UM, DR) at angular offset. The inner ring carries authoritative state; the outer ring exposes a redacted projection. In software terms this is a tiered access topology over the swarm: inner-ring agents can see state that outer-ring agents cannot, and outer-ring agents serve as the public surface that external traffic touches first.

### Adaptive Scatter (force-based dynamic placement)

Distinct from the existing HYDRA Scatter (which is a sweep / inventory pattern), Adaptive Scatter is a continuous-time placement update under three forces: a repulsion term that fires when peers are closer than a threshold (e.g. 0.2), an attraction term that pulls agents toward a configured anchor, and a stochastic drift term (e.g. Gaussian sigma 0.05). Output positions are clamped inside the Poincare ball under the existing hyperbolic-distance check. The pattern is jam-resistant in the software sense that no agent depends on a static slot assignment; positions self-organize each tick.

### Drone-Fleet Six-Pack, Software-Only Reframings

The Notion drone-fleet upgrade page contains six mechanisms with worked formulas. Reframed as software-only:

1. *Gravitational braking on misbehaving agents.* The mechanism `tG = t * (1 - (k*d)/(r+epsilon))` is reused as a CPU-time / event-loop throttle on agents whose harmonic-wall score is degraded: the further the agent has drifted from the authored reference, the lower its scheduling weight. This is governance-side throttling only, not a flight maneuver.
2. *Sphere-in-cube mission boundary.* A two-surface containment: an inner spherical authored region (allowed software state) inside an outer cubical operational region (permissible inputs and tools). State that crosses either surface is flagged. This is a software policy boundary, not a geofence.
3. *Harmonic camouflage of coordination signals.* Coordination traffic is modulated against a stellar-pulse style reference so that side-channel observers cannot distinguish quiet from active states. Implemented as constant-rate cover traffic with phase modulation; no external emission.
4. *Sacred Tongues coordination-syntax map.* The Notion flight-dynamics map (KO=cruise, AV=handshake, RU=hold, CA=execute, UM=stealth-redaction, DR=formation-lock) is reframed as a command-syntax phase encoding: KO frames a routing instruction, AV opens a peer handshake, RU asserts a hold lock, CA commits an authored action, UM applies a redaction wrapper, DR finalizes a structural commit. This is distinct from the squad-role map below, which is per-agent role assignment.
5. *Acoustic bottle-beam interference.* Reframed as an anti-extraction primitive on the data bus: when an extraction attempt is detected, neighboring channels emit a constructive-interference shape that buries the extraction signal in the operator's audit trail. This is software-side defense; no acoustic emission.
6. *Dimensional lifting (4D hyper-torus / 6D symplectic).* Reframed as a control-flow integrity primitive for embedded software: legitimate control transfers are those that are images of an authored manifold under a known lift; illegitimate transfers are those that fall outside the lifted set. This is the same idea as existing CFI work, expressed in the project's geometric vocabulary.

### Squad Role Map by Tongue (software roles only)

Reframed from the Notion master-architecture squad table:

| Tongue | Software Role | Function |
|--------|---------------|----------|
| Kor'aelin | Scout | Navigation, first-hop dispatch, request-graph traversal |
| Avali | Sniper | Long-range sensor channel, anomaly detection at distance |
| Runethic | Support | Routing, healing of degraded sessions, retry orchestration |
| Cassivadan | Tank | Encryption shield, hardened-state storage, durable checkpoint owner |
| Umbroth | Assassin | Stealth wrapper, redaction, ambush-style late-binding policy |
| Draumric | Adjutant | Validation, command relay, ledger commit |

These are the names and order already used in the Sacred Tongue table earlier in this document; the squad-role column is the new piece. Roles describe what kind of software work each tongue lane does, not what kind of physical action.

### Byzantine Fault-Tolerance Configuration

The existing 6-tongue ring already realizes a 3f+1 BFT cell at f=1: six agents tolerate one Byzantine-faulty agent (one of the six can fail or be adversarial without losing consensus). The Notion swarm-deployment page adds a peer-variance check: if the variance across peer position reports for the same agent exceeds a threshold (e.g. 0.1), the agent is quarantined and a replacement is spawned. In software terms this is a peer-reported attestation: each agent's reported state is cross-checked against what its peers believe its state to be, and disagreement past threshold trips the existing QUARANTINE / ESCALATE risk-decision tier.

### Notion-Sourced Items Mapped Back To Existing Feature Branches

- Concentric Rings -> mission envelope (`feat/agentbus-mission-envelope`): add an `inner_ring` / `outer_ring` membership tag to the envelope.
- Adaptive Scatter -> simulation mode (`feat/agentbus-simulation-mode`): add a force-based placement profile.
- Six-pack item 1 (gravitational braking) -> scoreboard routing (`feat/agentbus-scoreboard-routing`): drift-weighted scheduling penalty.
- Six-pack item 2 (sphere-in-cube) -> result judges (`feat/agentbus-result-judges`): two-surface boundary check on outputs.
- Six-pack item 4 (coordination syntax) -> trace spans (`feat/agentbus-trace-spans`): tongue-tagged span phase encoding.
- Squad Role Map -> training exporter (`feat/agentbus-training-exporter`): per-role training-data lane labeling.
- BFT peer-variance -> human-approval tripwires (`feat/agentbus-human-approval-tripwires`): peer-attestation disagreement as an escalation trigger.

## Risk and Scope Reaffirmation

This document is presentation material for software architecture and proposal support. It does not authorize, describe, or imply weaponization, targeting, tactical deployment, evasion, kinetic engagement, or physical-platform operation of any kind. Every reference to a DARPA program is a public concept summary, and every transfer is a software-only mapping. The Notion-sourced section above repeats the same scope guard: every item is a reframing into software, governance, scheduling, audit, or coordination terms, with no physical-platform meaning.

If any future capability statement reuses content from this document, that statement must repeat this scope reaffirmation verbatim and must not add tactical or platform content.

## Official Sources

- DARPA ACE: https://www.darpa.mil/research/programs/air-combat-evolution
- DARPA OFFSET: https://www.darpa.mil/research/programs/offensive-swarm-enabled-tactics
- DARPA CODE: https://www.darpa.mil/research/programs/collaborative-operations-in-denied-environment
- DARPA Squad X: https://www.darpa.mil/research/programs/squad-x
- DARPA Sea Hunter / ACTUV background: https://www.darpa.mil/news/resources
- DARPA BLACKJACK: https://www.darpa.mil/research/programs/blackjack
- Companion transfer map: `docs/specs/DARPA_MILITARY_SYSTEMS_AGENT_BUS_TRANSFER_2026-04-26.md`
- HYDRA formations reference: `skills/codex-mirror/scbe-github-sweep-sorter/references/formations.md`
- Swarm formation primitives: `src/ai_brain/swarm-formation.ts`
- Authored-moral-anchor record: memory `discovery_fictional_moral_anchor.md`
