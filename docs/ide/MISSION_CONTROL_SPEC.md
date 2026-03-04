# SCBE IDE - Mission Control Specification

**Document version**: 0.1.0
**Date**: 2026-02-19
**Status**: DRAFT
**Patent reference**: USPTO Application #63/961,403
**Depends on**: [MVP_SPEC.md](./MVP_SPEC.md), [BUILD_PLAN_90D.md](./BUILD_PLAN_90D.md)
**Source files referenced**:
- `src/fleet/polly-pad.ts` (PollyPadManager)
- `src/fleet/polly-pad-runtime.ts` (PadRuntime, SquadSpace, UnitRuntime)
- `src/fleet/polly-pads/mode-pad.ts` (ModePad, 6 specialist modes)
- `src/fleet/polly-pads/closed-network.ts` (ClosedNetwork, air-gapped comms)
- `src/harmonic/voxelRecord.ts` (harmonicCost, scbeDecide, quorum validation)

---

## 1. Paradigm Shift: From Developer Tool to Mission Control Middleware

### 1.1 The Problem with the IDE Frame

The MVP spec (MVP_SPEC.md) describes the SCBE IDE as a "governance-first integrated development environment." That framing is correct for the V0 desktop product, but it undersells the runtime architecture already implemented in the codebase. The Polly Pad system -- `polly-pad-runtime.ts`, `mode-pad.ts`, `closed-network.ts` -- is not IDE infrastructure. It is a fully specified autonomous agent governance runtime that happens to be observable through an IDE interface.

The paradigm shift is this: **the IDE is not the product. The IDE is the cockpit window into a Polly Pad runtime that governs autonomous AI swarms operating in communication-denied environments.**

### 1.2 What Already Exists

The codebase already implements the core machinery for autonomous swarm governance:

| Component | File | What It Does |
|-----------|------|-------------|
| **Per-agent workspaces** | `polly-pad.ts` | Each agent gets a persistent, auditable workspace (notes, sketches, tools) with dimensional flux states (POLLY/QUASI/DEMI/COLLAPSED), Sacred Tongue tier progression (KO through DR), XP/milestones, and a full audit trail. |
| **Dual-zone runtime** | `polly-pad-runtime.ts` | Each unit has 6 Polly Pads (one per PadMode: ENGINEERING, NAVIGATION, SYSTEMS, SCIENCE, COMMS, MISSION). Each pad has HOT (exploratory) and SAFE (execution) zones. Promotion from HOT to SAFE requires an SCBE ALLOW decision plus optional BFT quorum (4/6). |
| **Squad coordination** | `polly-pad-runtime.ts` | `SquadSpace` tracks unit positions, computes proximity graphs, elects leaders (lowest hEff + highest coherence), validates BFT quorum (n=6, f=1, threshold=4), and maps risk fields across the swarm. |
| **Mode switching** | `mode-pad.ts` | `ModePad` supports dynamic switching between 6 specialist modes with persistent memory across switches and reboots. Mode switch history is preserved for audit. |
| **Air-gapped comms** | `closed-network.ts` | `ClosedNetwork` enforces air-gapped operation with 4 allowed channels (local_squad_mesh, earth_deep_space, onboard_sensors, emergency_beacon). Messages are HMAC-signed. Earth contact queuing handles blackout periods -- messages queue when contact is unavailable and flush on reconnection. |
| **Governance decisions** | `voxelRecord.ts` | `scbeDecide()` computes ALLOW/QUARANTINE/DENY from dStar (hyperbolic drift), coherence, and hEff (harmonic cost). `harmonicCost()` implements H(d*, R) = R * pi^(phi * d*). `validateQuorum()` enforces BFT with n=6, f=1, threshold=4. |

### 1.3 The Cockpit Window Model

The IDE surfaces this runtime through visual panels, but the runtime operates independently. This is the critical architectural distinction:

```
                    Ground Control (IDE)
                    +------------------+
                    |  Governance Panel |   <-- Reads governance decisions
                    |  Decision Replay  |   <-- Replays blackout history
                    |  Envelope Manager |   <-- Signs & uploads envelopes
                    |  Swarm Dashboard  |   <-- Visualizes swarm state
                    +--------+---------+
                             |
                    earth_deep_space channel (8-24 min latency)
                             |
              +--------------+--------------+
              |     Polly Pad Runtime       |
              |  +------+ +------+ +------+ |
              |  |Unit 1| |Unit 2| |Unit 3| |   <-- 6 pads each
              |  +------+ +------+ +------+ |
              |  +------+ +------+ +------+ |
              |  |Unit 4| |Unit 5| |Unit 6| |
              |  +------+ +------+ +------+ |
              |                              |
              |  SquadSpace (BFT quorum)     |
              |  ClosedNetwork (air-gapped)  |
              |  Harmonic Wall (autonomous)  |
              +------------------------------+
```

### 1.4 Reactive vs. Proactive Governance

The MVP spec describes a **reactive** model: human approves each action. For deep space operations with 8-24 minute one-way light delay, this is not viable. The Mars-grade extension introduces **proactive governance** through Decision Envelopes:

| Aspect | Reactive (MVP V0) | Proactive (Mission Control) |
|--------|-------------------|----------------------------|
| Decision authority | Human clicks Approve/Deny per action | Pre-signed envelopes define autonomous decision space |
| Latency tolerance | < 50ms (local) | 8-24 minutes (interplanetary) |
| Failure mode | Goal blocks at `review_required` | Swarm continues within envelope bounds |
| Trust model | Human-in-the-loop always | BFT quorum + envelope constraints + resource gating |
| Audit trail | Hash-chained log, review on demand | Merkle Mountain Range, cryptographic proof of every blackout action |
| Harmonic Wall role | Gatekeeper (blocks or allows) | Autonomous governor (resource-adjusted, self-regulating) |

### 1.5 The Harmonic Wall as Autonomous Governor

In the MVP, the Harmonic Wall computes a cost and the decision gate checks thresholds. In Mission Control, the Harmonic Wall becomes an autonomous governor that modulates its own behavior based on real-time resource availability:

- **Gatekeeper mode** (MVP): `H(d*, R) = R * pi^(phi * d*)` computes a static cost. If cost exceeds threshold, action is denied.
- **Governor mode** (Mission Control): `H_resource(d*, R, resources) = R * pi^(phi * d*) * product(S_i)` dynamically adjusts cost based on remaining resources. As resources deplete, the Harmonic Wall automatically contracts the autonomy envelope, freezing non-essential actions before any resource reaches zero.

---

## 2. The Three Mars-Grade Extensions

These extensions build on the existing codebase without replacing any existing types or functions. Each extends a specific component.

### 2.1 Decision Envelope (Polly Gate Extension)

#### Problem

`canPromoteToSafe()` in `polly-pad-runtime.ts` returns a boolean: the pad either promotes to SAFE or it does not. This is adequate when a human operator is available within seconds. It is not adequate when the nearest human is 24 light-minutes away and the swarm must make hundreds of governance decisions during a communication blackout.

#### Solution: Envelope-Aware Decision

Replace the boolean gate with an envelope-aware decision function:

```typescript
// Existing (polly-pad-runtime.ts, line 175)
function canPromoteToSafe(pad: PadRuntime, state: UnitState, quorumVotes?: number): boolean

// Extended
function envelopeDecide(
  pad: PadRuntime,
  state: UnitState,
  envelope: DecisionEnvelope,
  quorumVotes?: number
): EnvelopeDecision
```

The `DecisionEnvelope` is a signed, time-bounded document that pre-authorizes classes of actions within defined parameters. Instead of asking "can this pad promote right now?" the system asks "does this action fall within the pre-authorized envelope?"

#### Three Boundary Types

| Boundary Type | Execution Logic | Recovery Path |
|---------------|-----------------|---------------|
| **AUTO_ALLOW** | Execute immediately if within envelope parameters (dStar, coherence, hEff all within envelope bounds). Log to local audit chain. No quorum required. | If action produces unexpected results, log anomaly and continue. Auto-revoke AUTO_ALLOW for the specific action class if anomaly count exceeds 3 within one epoch. |
| **QUARANTINE** | Execute in HOT zone only (no SAFE promotion). Require BFT quorum (4/6 votes). Log with full context to Merkle audit chain. Results isolated from primary systems until quorum review at next heartbeat cycle. | If quorum rejects during review, roll back quarantined changes. Demote pad to HOT (call `demotePad()`). Add audit entry with `result: 'warning'`. |
| **DENY** | Do not execute. Log the denial with full context. If the action was critical (marked `priority: 'mission_critical'` in envelope), escalate to emergency key override. | If emergency key override is invoked, re-evaluate with emergency thresholds (2x allowMaxCost, 0.5x allowMinCoherence). Log as emergency override in audit chain with override justification. If still DENY under emergency thresholds, the action is absolutely blocked. |

#### Envelope Lifecycle

```
sign --> upload --> activate --> expire --> replace
  |                   |            |          |
  |  Ground control   |  Swarm     |  Clock   |  Ground control
  |  signs with       |  validates |  reaches |  signs and
  |  ML-DSA-65        |  signature |  expiry  |  uploads
  |  private key      |  and       |  epoch   |  replacement
  |                   |  caches    |          |  before expiry
  |                   |  locally   |          |
```

1. **Sign**: Ground control constructs the envelope JSON (action classes, parameter bounds, expiry epoch, resource minimums) and signs it with an ML-DSA-65 private key. The envelope includes the public key hash for verification.
2. **Upload**: Envelope is transmitted over `earth_deep_space` channel. If the channel is in BLACKOUT, the envelope is queued in the ClosedNetwork's `earthQueue` and delivered when contact resumes.
3. **Activate**: The swarm leader (elected via `SquadSpace.findLeader()`) validates the signature, checks the expiry is in the future, and distributes the envelope to all units via `local_squad_mesh` broadcast. Each unit caches the active envelope.
4. **Expire**: When the swarm's epoch clock reaches the envelope's `expiryEpoch`, the envelope transitions to expired state. Units fall back to the most recently expired envelope with `fallbackBehavior: 'conservative'` (all actions become QUARANTINE) until a replacement arrives.
5. **Replace**: Ground control signs and uploads a new envelope before the current one expires. Overlap periods are allowed -- the newer envelope takes precedence. If replacement arrives late (after expiry), units operate in conservative fallback until the new envelope activates.

#### Emergency Key Override

Each squad carries an emergency key pair (ML-KEM-768 encapsulated, stored in the onboard HSM). Emergency override requires:

1. **Initiator**: Any unit can propose emergency override.
2. **Quorum**: 4/6 units must vote to activate the emergency key.
3. **Scope**: Emergency override applies only to the specific denied action, not to the entire envelope.
4. **Logging**: Every emergency override is logged with a distinct `emergency_override` tag in the Merkle audit chain, including: initiating unit, quorum votes, original denial reason, override justification, and outcome.
5. **Automatic report**: When earth contact resumes, emergency overrides are flagged as priority-1 in the sync payload so ground control reviews them immediately.

---

### 2.2 Resource-Adjusted Harmonic Wall

#### Original Formula

From `voxelRecord.ts` (line 147):

```typescript
export function harmonicCost(dStar: number, R: number = 1.5): number {
  return R * Math.pow(Math.PI, PHI * dStar);
}
```

Where:
- `dStar` = hyperbolic realm distance (drift from safe center)
- `R` = base resistance (default 1.5)
- `PHI` = golden ratio (1 + sqrt(5)) / 2 = 1.618...
- Result: `H(d*, R) = R * pi^(phi * d*)`

This formula is resource-blind. It computes the same cost whether the rover has 95% battery or 5% battery. For autonomous operations, the governance cost must reflect the real cost of action given current resource constraints.

#### Extended Formula

```
H_resource(d*, R, resources) = R * pi^(phi * d*) * product(S_i)
```

Where `S_i` is the scarcity multiplier for resource `i`:

```
S_i = 1 / r_i^2
```

- `r_i` = current level of resource `i`, normalized to [0, 1] where 1 = fully available and 0 = depleted.
- When `r_i = 1.0` (resource fully available): `S_i = 1.0` (no amplification)
- When `r_i = 0.5` (resource at 50%): `S_i = 4.0` (4x cost amplification)
- When `r_i = 0.1` (resource at 10%): `S_i = 100.0` (100x cost amplification)
- When `r_i -> 0` (resource approaching depletion): `S_i -> infinity` (action becomes computationally impossible)

The product of all scarcity multipliers means that degradation in ANY resource increases the cost of ALL actions. This is intentional: a rover with low bandwidth should also be more conservative with power, because it cannot call for help if it makes a power-critical mistake.

#### Cost Multiplier Table

| Resource Level (r_i) | Scarcity (S_i) | Effect on Base Cost | Practical Meaning |
|----------------------|----------------|--------------------|--------------------|
| 1.00 | 1.0x | No change | Resource fully available |
| 0.80 | 1.6x | Mild increase | Nominal operations, slight caution |
| 0.60 | 2.8x | Moderate increase | Non-essential actions start becoming expensive |
| 0.50 | 4.0x | Significant increase | Only mission-relevant actions affordable |
| 0.30 | 11.1x | Steep increase | Only critical actions affordable |
| 0.20 | 25.0x | Severe increase | Emergency operations only |
| 0.10 | 100.0x | Near-prohibitive | Survival actions only |
| 0.05 | 400.0x | Prohibitive | Nothing except emergency beacon |
| 0.01 | 10,000.0x | Frozen | All actions effectively impossible |

#### Tracked Resources

Each unit tracks 6 resource dimensions, mapped to the 6 Sacred Tongues for namespace separation:

| Resource | Sacred Tongue | Unit | Depletion Consequence |
|----------|--------------|------|----------------------|
| **Power** (battery/solar) | KO | Watt-hours remaining / max capacity | Total system shutdown |
| **Bandwidth** (comms capacity) | AV | Bits/sec available / max throughput | Loss of squad coordination |
| **Thermal margin** (operating temp headroom) | RU | Degrees from thermal limit / max range | Component damage, forced hibernation |
| **Mechanical wear** (actuator/wheel life) | CA | Remaining cycles / rated lifetime | Loss of mobility or manipulation |
| **Propellant** (fuel, compressed gas) | UM | Mass remaining / initial mass | Inability to maneuver or return |
| **Storage** (disk/memory capacity) | DR | Bytes free / total capacity | Loss of audit trail, data corruption |

#### The Freezing Effect

The product formulation creates a natural "freezing" behavior. Consider a unit with these resource levels:

```
Power:    0.80  ->  S_power    = 1.56
Bandwidth: 0.90  ->  S_bandwidth = 1.23
Thermal:  0.70  ->  S_thermal  = 2.04
Mechanical: 0.95 ->  S_mech     = 1.11
Propellant: 0.30 ->  S_prop     = 11.11
Storage:  0.85  ->  S_storage  = 1.38
```

Combined scarcity multiplier: `1.56 * 1.23 * 2.04 * 1.11 * 11.11 * 1.38 = 59.9x`

A base harmonic cost of `H = 100` becomes `H_resource = 5,990`. Against default thresholds (`allowMaxCost = 1,000`, `quarantineMaxCost = 1,000,000`), this action that would normally be ALLOW is now QUARANTINE -- entirely because propellant is low. The swarm self-regulates: it becomes more conservative as resources deplete, without any ground control intervention.

When multiple resources are low simultaneously, the product compounds rapidly:

```
Power: 0.30, Bandwidth: 0.40, Thermal: 0.50 (other resources at 1.0)
Combined: 11.11 * 6.25 * 4.0 = 277.8x
```

At this compound scarcity, even low-drift actions (dStar near 0) face significant cost amplification. The system freezes naturally -- not by a hard shutdown command, but by making every non-survival action too expensive to pass the governance gate.

---

### 2.3 Blackout Audit Chain (Merkle Mountain Range)

#### Problem

The existing audit trail in `polly-pad.ts` is a linear array of `AuditEntry` objects. During normal operations with earth contact, this is sufficient -- entries are transmitted to ground control as they occur. During a communication blackout (which can last hours or days during Mars conjunction), the swarm accumulates thousands of audit entries with no way to prove to ground control that the entries are complete, unmodified, and in order.

A simple hash chain (SHA-256 linking each entry to the previous) proves ordering and tamper-evidence, but it has a problem: to verify entry N, you must download and verify entries 1 through N. After a multi-day blackout with thousands of entries, this is prohibitively slow over a bandwidth-constrained deep space link.

#### Solution: Merkle Mountain Range (MMR)

When comms enter BLACKOUT state (detected via `ClosedNetwork.config.earthContactAvailable === false`), the audit system switches from linear chain to Merkle Mountain Range structure.

MMR is an append-only data structure with the following properties:

| Property | Complexity | Why It Matters |
|----------|-----------|----------------|
| Append new entry | O(1) amortized | Swarm can log thousands of entries without performance degradation |
| Inclusion proof (prove entry X is in the chain) | O(log n) | Ground control can verify any single entry without downloading the entire chain |
| Sync (bring ground control up to date) | O(peaks) | Only the MMR peaks (typically 5-15 hashes) need to be transmitted to establish chain state |
| Consistency proof (prove chain was not modified) | O(log n) | Prove that the chain ground control knew before blackout is a prefix of the current chain |

#### MMR Structure

An MMR is a list of perfect binary Merkle trees of decreasing size. Each tree's root is a "peak." When a new entry is appended, it creates a new single-node tree. If the last two trees have the same height, they merge into a new tree of height+1. This merge cascades until no two adjacent trees have the same height.

```
After 11 entries:

         Peak 0 (height 3)          Peak 1 (h1)    Peak 2 (h0)
              /    \                     / \             |
            /        \                 /     \         [10]
          /            \             [8]     [9]
        /     \      /     \
      /  \   / \   / \   [7]
    [0] [1] [2] [3] [4] [5] [6]

Peaks: [hash_of_tree_0, hash_of_tree_1, hash_of_tree_2]
MMR root: hash(peak_0 || peak_1 || peak_2)
```

#### What Each Entry Contains

Every governance decision during blackout is logged as an MMR leaf with the following fields:

```typescript
interface BlackoutAuditEntry {
  /** Monotonic sequence number */
  seq: number;
  /** Unix timestamp (ms) */
  timestamp: number;
  /** Acting unit ID */
  unitId: string;
  /** Pad mode that produced this action */
  padMode: PadMode;  // ENGINEERING | NAVIGATION | SYSTEMS | SCIENCE | COMMS | MISSION
  /** Code zone */
  zone: CodeZone;  // HOT | SAFE
  /** SCBE governance decision */
  decision: Decision;  // ALLOW | QUARANTINE | DENY
  /** Hyperbolic drift at decision time */
  dStar: number;
  /** Coherence at decision time */
  coherence: number;
  /** Effective harmonic cost (resource-adjusted) */
  hEffResource: number;
  /** Envelope ID that authorized this action */
  envelopeId: string;
  /** BFT quorum proof (4/6 votes) */
  quorumProof: QuorumProof;
  /** Resource snapshot at execution time */
  resources: ResourceSnapshot;
  /** Action description */
  actionSummary: string;
  /** Hash of the action payload */
  actionPayloadHash: string;
}
```

#### Cryptographic Guarantees

Ground control receives cryptographic proof that every action taken during a blackout was:

1. **Validated by BFT quorum (4/6)**: Each audit entry contains a `QuorumProof` with `n=6, f=1, threshold=4`. The proof includes individual agent signatures (ML-DSA-65) over the entry's content hash. Ground control can independently verify each signature against the known public keys of the squad members. This uses the same `validateQuorum()` function from `voxelRecord.ts` -- no new quorum mechanism is needed.

2. **Within a signed Decision Envelope**: Each entry references an `envelopeId`. Ground control can verify that (a) the envelope was signed by ground control's own ML-DSA-65 key, (b) the envelope was active (not expired) at the entry's timestamp, and (c) the action class recorded in the entry falls within the envelope's authorized action classes. If any entry references an unknown or expired envelope, it is flagged for immediate review.

3. **Resource-checked at execution time**: Each entry contains a `ResourceSnapshot` (power, bandwidth, thermal, mechanical, propellant, storage levels at execution time). Ground control can verify that the resource-adjusted harmonic cost (`hEffResource`) is consistent with the snapshot values and the base harmonic cost formula. If the logged `hEffResource` is lower than what the formula would produce from the logged resource levels, the entry is fraudulent.

#### Sync Protocol When Comms Resume

When `ClosedNetwork.setEarthContact(true)` is called (earth contact restored), the following sync protocol executes:

1. **Peak exchange**: The swarm leader transmits the current MMR peaks (typically 5-15 SHA-256 hashes, total < 1 KB) over the `earth_deep_space` channel.

2. **Ground control verifies consistency**: Ground control compares the received peaks against the last-known MMR state from before blackout. If the pre-blackout peaks are a valid prefix of the current peaks, the chain is consistent -- no entries were removed or modified during blackout.

3. **Delta sync**: Ground control requests only the entries added since the last known position. The swarm transmits these entries in order. Each entry is verified against the MMR inclusion proof.

4. **Priority flagging**: Entries with `decision: 'DENY'`, emergency overrides, or resource levels below 20% on any dimension are flagged as priority-1 for immediate ground control review.

5. **Envelope refresh**: Ground control uses the synced data to prepare and upload a new Decision Envelope informed by the blackout period's actual behavior.

6. **Acknowledgment**: Ground control transmits an ACK containing the verified MMR root hash. The swarm marks all synced entries as `verified_by_ground: true`.

If consistency check fails (peaks do not form a valid extension of the pre-blackout state), the entire blackout audit chain is flagged as compromised. Ground control must then request a full chain download and perform entry-by-entry forensic analysis. This triggers an automatic restriction of the swarm's envelope to `QUARANTINE`-only until the discrepancy is resolved.

---

## 3. SCBE Polly Pad Swarm vs. NASA cFS / AMPCS Comparison

| Feature | NASA cFS / AMPCS | Polly Pad Swarm |
|---------|-----------------|-----------------|
| **Architecture** | Command Sequences (Procedural) -- ground operators write step-by-step command scripts that execute in order. Each command is individually validated and time-tagged. The spacecraft is a passive executor. | Agentic Governance (Intent-based) -- ground operators define decision envelopes (intent boundaries). The swarm autonomously decides how to achieve objectives within those boundaries. Each unit is an active decision-maker. |
| **Latency handling** | Time-tagged command buffers -- commands are pre-loaded with absolute or relative execution times. The spacecraft's clock triggers each command. If conditions change, the command executes anyway unless a pre-programmed fault response cancels it. | Autonomous Decision Envelopes -- signed documents that pre-authorize classes of actions within parameter bounds. The swarm evaluates real-time conditions against envelope constraints and makes autonomous decisions. No pre-scripted execution order. |
| **Trust model** | Perimeter security -- the Deep Space Network (DSN) link is the trust boundary. Commands are authenticated via SDLS (Space Data Link Security) at the link layer. Once authenticated, commands execute with full authority. No internal trust differentiation between subsystems. | Byzantine Fault Tolerance (BFT) -- n=6, f=1, threshold=4. Every governance decision requires 4/6 squad members to agree. A compromised or malfunctioning unit cannot unilaterally execute high-risk actions. Internal trust is continuously evaluated via coherence scores and harmonic cost. |
| **Risk management** | Static thresholds -- fault protection uses pre-defined limit checks (temperature > X, voltage < Y). Responses are pre-scripted (safe mode, power-off sequence). Thresholds are fixed until ground uploads new tables. | Predictive ambient risk scoring -- the Harmonic Wall (`H_resource`) continuously computes action cost as a function of hyperbolic drift, coherence, AND real-time resource levels. Risk thresholds are dynamic: they tighten automatically as resources deplete. No ground intervention needed for threshold adjustment. |
| **Fault recovery** | Pre-scripted responses -- fault protection software detects anomalies and selects from a table of pre-programmed responses. Complex multi-fault scenarios may not have pre-scripted responses, leading to safe mode (full stop until ground intervenes). | Autonomous self-healing + quorum -- the swarm can redistribute tasks when a unit fails (heartbeat miss protocol), dynamically adjust mode assignments (ModePad switching), and collectively decide on recovery actions via BFT quorum. The system degrades gracefully rather than entering full-stop safe mode. |
| **Audit trail** | Telemetry downlink -- engineering telemetry is downlinked at scheduled intervals. The ground system correlates telemetry with command history. During blackout, telemetry is stored in onboard recorder and downlinked when contact resumes. No cryptographic proof of ordering or completeness. | Merkle-proven governance chain -- every governance decision is logged in a Merkle Mountain Range with BFT quorum signatures. Ground control receives O(log n) cryptographic proofs that the chain is complete, ordered, and untampered. Every entry proves it was authorized by a valid envelope and validated by quorum. |
| **Multi-agent coordination** | N/A (single flight computer) -- cFS runs on a single flight computer (or redundant pair in cold standby). There is no concept of multiple autonomous agents collaborating on tasks. Multi-spacecraft missions use separate ground operations teams. | 6-pad swarm with mode switching -- each unit has 6 specialist pads (ENGINEERING, NAVIGATION, SYSTEMS, SCIENCE, COMMS, MISSION) that can switch dynamically based on mission needs. The squad coordinates via BFT quorum, proximity-aware mesh networking, and shared risk field computation. |
| **Crypto** | Standard TLS / SDLS -- Space Data Link Security (CCSDS 355.0-B-2) uses AES-128/256 for confidentiality and AES-CMAC for authentication. Not post-quantum secure. Key management is ground-controlled via pre-placed key tables. | Post-quantum (ML-KEM-768, ML-DSA-65) -- NIST FIPS 203/204 post-quantum algorithms for key encapsulation and digital signatures. Envelope signing uses ML-DSA-65. Emergency key exchange uses ML-KEM-768. Resistant to quantum computer attacks on Shor's algorithm. |
| **Extensibility** | Requires ground software update -- new functionality requires uploading new command sequences, parameter tables, or (rarely) flight software patches. Each patch is a multi-month review process. | Envelope-driven capability evolution -- ground control can expand or contract swarm autonomy by signing new envelopes. New action classes can be authorized without flight software updates. The envelope schema is extensible. |

---

## 4. Mission Phase State Machine

```
LAUNCH --> TRANSIT --> ORBIT_INSERT --> DESCENT --> LANDING --> SURFACE_OPS --> RETURN_PREP --> ASCENT --> TRANSIT_HOME --> REENTRY
                                                                   |
                                                             EMERGENCY_OPS
```

Any phase can transition to EMERGENCY_OPS. EMERGENCY_OPS can transition back to the phase it interrupted once the emergency is resolved.

### Phase Definitions

#### LAUNCH

| Attribute | Value |
|-----------|-------|
| **Primary mode** | ENGINEERING (structural integrity, vibration monitoring, propulsion health) |
| **Envelope profile** | AUTO_ALLOW: telemetry reporting, vibration monitoring, thermal monitoring. QUARANTINE: propulsion adjustments, deployment sequences. DENY: science operations, non-essential comms, navigation changes. |
| **Resource priorities** | 1. Power (launch batteries), 2. Thermal (ascent heating), 3. Mechanical (vibration stress) |
| **Comms expectations** | LIVE (ground tracking stations + relay satellites). Continuous telemetry. Sub-second latency. |
| **Fallback if transition fails** | If TRANSIT transition fails (orbit not achieved): remain in LAUNCH mode, activate emergency propulsion protocols. If orbit is decaying, transition to EMERGENCY_OPS. Envelope automatically restricts to survival-only actions. |

#### TRANSIT

| Attribute | Value |
|-----------|-------|
| **Primary mode** | NAVIGATION (trajectory monitoring, course corrections, celestial navigation) |
| **Envelope profile** | AUTO_ALLOW: trajectory monitoring, star tracker calibration, routine telemetry, power management. QUARANTINE: course correction burns, antenna repointing, software updates. DENY: propulsion system reconfiguration, science instrument activation. |
| **Resource priorities** | 1. Propellant (mid-course corrections are limited), 2. Power (solar distance varies), 3. Bandwidth (increasing delay) |
| **Comms expectations** | LIVE transitioning to DELAYED. One-way latency grows from seconds to minutes. Contact windows may narrow as distance increases. Periodic BLACKOUT possible during solar conjunction. |
| **Fallback if transition fails** | If ORBIT_INSERT transition fails (bad trajectory): remain in TRANSIT mode, NAVIGATION pad computes correction burn options. If correction is within envelope, execute autonomously. If not, queue for ground approval. If BLACKOUT, use emergency envelope with wider QUARANTINE bounds for trajectory corrections. |

#### ORBIT_INSERT

| Attribute | Value |
|-----------|-------|
| **Primary mode** | NAVIGATION (orbit insertion burn timing, orbit determination) with ENGINEERING as secondary (propulsion health) |
| **Envelope profile** | AUTO_ALLOW: attitude determination, star tracker, IMU health checks. QUARANTINE: orbit insertion burn execution, orbit trim maneuvers. DENY: science operations, non-critical communications, software updates. |
| **Resource priorities** | 1. Propellant (insertion burn is mission-critical and non-repeatable), 2. Power (burn draws peak current), 3. Thermal (engine thermal limits) |
| **Comms expectations** | DELAYED (minutes). Likely BLACKOUT during the burn itself (antenna pointing constraints). Pre-burn: envelope uploaded with full burn authorization. |
| **Fallback if transition fails** | If DESCENT transition fails (orbit not stable): remain in ORBIT_INSERT, execute orbit trim maneuvers under QUARANTINE governance. If orbit is dangerously elliptical, transition to EMERGENCY_OPS for emergency circularization burn. |

#### DESCENT

| Attribute | Value |
|-----------|-------|
| **Primary mode** | NAVIGATION (terrain-relative navigation, hazard avoidance) with SYSTEMS as secondary (landing system health) |
| **Envelope profile** | AUTO_ALLOW: terrain mapping, hazard detection, altitude sensing, attitude control. QUARANTINE: landing site retargeting, descent engine throttle adjustments. DENY: science operations, non-essential telemetry, uplink processing. |
| **Resource priorities** | 1. Propellant (descent fuel is precisely budgeted), 2. Power (landing radar and terrain sensors), 3. Thermal (aerobraking heating) |
| **Comms expectations** | BLACKOUT or severely DELAYED. Descent is fully autonomous. Pre-descent: envelope uploaded with wide AUTO_ALLOW for terrain-relative navigation decisions. Ground control observes but cannot intervene. |
| **Fallback if transition fails** | If LANDING transition fails (abort triggered): remain in DESCENT mode with emergency ascent profile. NAVIGATION pad computes abort trajectory. If propellant permits, attempt re-landing at alternate site. If not, ascend to orbit and transition to EMERGENCY_OPS. |

#### LANDING

| Attribute | Value |
|-----------|-------|
| **Primary mode** | SYSTEMS (post-landing health checks, deployment sequences) with ENGINEERING (structural integrity verification) |
| **Envelope profile** | AUTO_ALLOW: systems health telemetry, structural integrity checks, solar panel deployment, antenna deployment. QUARANTINE: mobility system activation, instrument deployment, initial drive commands. DENY: long-range traverse, drilling operations, sample handling. |
| **Resource priorities** | 1. Power (solar panel deployment is time-critical), 2. Storage (landing data must be preserved), 3. Bandwidth (first opportunity to report to Earth) |
| **Comms expectations** | DELAYED (minutes). First contact opportunity after descent blackout. Priority: transmit landing confirmation + health status. Download descent telemetry as bandwidth allows. |
| **Fallback if transition fails** | If SURFACE_OPS transition fails (critical system not deployed): remain in LANDING mode, repeat deployment sequences. If deployment is mechanically jammed (mechanical wear resource depleting), transition to EMERGENCY_OPS for diagnostic and workaround procedures. |

#### SURFACE_OPS

| Attribute | Value |
|-----------|-------|
| **Primary mode** | SCIENCE (sample collection, analysis, experiments) with MISSION (objective prioritization, schedule management) |
| **Envelope profile** | AUTO_ALLOW: science observations, imaging, sample analysis, routine traverse, telemetry. QUARANTINE: drilling operations, sample caching, long-range traverse (> 100m), rock abrasion. DENY: propulsion system activation, flight software modification, communication system reconfiguration. |
| **Resource priorities** | 1. Power (diurnal solar cycle management), 2. Mechanical (wheel and actuator wear), 3. Storage (science data volume) |
| **Comms expectations** | Mixed LIVE/DELAYED/BLACKOUT. Relay satellite passes provide DELAYED windows. Direct-to-Earth provides DELAYED (8-24 min). Solar conjunction causes extended BLACKOUT (weeks). Envelope refresh cycle: every relay pass. |
| **Fallback if transition fails** | If RETURN_PREP transition fails (return window missed): remain in SURFACE_OPS, extend science operations, wait for next return window. If no return window exists (sample return mission constraint), transition to extended operations mode with conservation-focused envelope. |

#### RETURN_PREP

| Attribute | Value |
|-----------|-------|
| **Primary mode** | ENGINEERING (ascent vehicle checkout, propulsion prep) with MISSION (timeline management, sample loading) |
| **Envelope profile** | AUTO_ALLOW: vehicle health checks, propulsion system warm-up, sample container sealing, pre-launch diagnostics. QUARANTINE: propellant loading, sample transfer operations. DENY: science operations (mission is now return-focused), surface traverse, non-essential experiments. |
| **Resource priorities** | 1. Propellant (ascent fuel must be verified full), 2. Power (launch systems require peak power), 3. Mechanical (launch mechanism must be verified) |
| **Comms expectations** | DELAYED. Ground control must verify readiness before launch authorization. Envelope includes launch-go/no-go criteria that the swarm evaluates autonomously against a ground-signed checklist. |
| **Fallback if transition fails** | If ASCENT transition fails (launch window missed): remain in RETURN_PREP, safe propulsion system, wait for next launch window. Envelope reverts to conservation mode. If propulsion system fault detected, transition to EMERGENCY_OPS. |

#### ASCENT

| Attribute | Value |
|-----------|-------|
| **Primary mode** | NAVIGATION (ascent guidance, orbit targeting) with ENGINEERING (propulsion monitoring) |
| **Envelope profile** | AUTO_ALLOW: ascent guidance, engine health monitoring, attitude control, trajectory tracking. QUARANTINE: engine shutdown timing, orbit injection adjustments. DENY: all non-ascent operations. |
| **Resource priorities** | 1. Propellant (ascent burn budget), 2. Power (guidance and control), 3. Thermal (engine thermal margins) |
| **Comms expectations** | BLACKOUT during ascent (antenna pointing constraints). Pre-ascent envelope includes full ascent authority. Post-insertion: re-establish contact and downlink ascent telemetry. |
| **Fallback if transition fails** | If TRANSIT_HOME transition fails (orbit not achieved): remain in ASCENT mode, compute correction options. If propellant remains, attempt orbit adjustment. If not, transition to EMERGENCY_OPS in orbit. |

#### TRANSIT_HOME

| Attribute | Value |
|-----------|-------|
| **Primary mode** | NAVIGATION (return trajectory, course corrections) with COMMS (increasing bandwidth as Earth approaches) |
| **Envelope profile** | AUTO_ALLOW: trajectory monitoring, sample container thermal management, routine telemetry. QUARANTINE: course corrections, antenna repointing. DENY: sample container opening, unnecessary propulsion burns. |
| **Resource priorities** | 1. Power (solar increases as Earth approaches), 2. Propellant (final corrections), 3. Thermal (sample integrity) |
| **Comms expectations** | DELAYED transitioning to LIVE. Latency decreases. Bandwidth increases. More frequent envelope refreshes. |
| **Fallback if transition fails** | If REENTRY transition fails (trajectory too steep/shallow): remain in TRANSIT_HOME, compute correction burn. Envelope allows emergency trajectory correction under QUARANTINE governance. |

#### REENTRY

| Attribute | Value |
|-----------|-------|
| **Primary mode** | SYSTEMS (heat shield monitoring, parachute deployment) with NAVIGATION (entry guidance) |
| **Envelope profile** | AUTO_ALLOW: all entry guidance, heat shield monitoring, parachute deployment triggers, beacon activation. QUARANTINE: entry angle adjustments. DENY: none -- all survival actions are AUTO_ALLOW during reentry. |
| **Resource priorities** | 1. Thermal (heat shield is the mission), 2. Mechanical (parachute deployment), 3. Power (beacon and tracking) |
| **Comms expectations** | BLACKOUT during plasma phase. Pre-entry: full authority envelope uploaded. Post-blackout: beacon activation for recovery tracking. |
| **Fallback if transition fails** | There is no fallback. Reentry is a one-way commitment. The envelope is maximally permissive. Every survival action is AUTO_ALLOW. |

#### EMERGENCY_OPS

| Attribute | Value |
|-----------|-------|
| **Primary mode** | SYSTEMS (diagnosis, triage) with all other modes available for emergency tasking |
| **Envelope profile** | All actions become QUARANTINE by default. Emergency key override available for survival-critical actions that would otherwise be DENY. AUTO_ALLOW restricted to: telemetry, health monitoring, emergency beacon. |
| **Resource priorities** | Dynamic -- determined by the emergency. Power is always priority 1. |
| **Comms expectations** | Attempt contact on all available channels. Emergency beacon activated. If BLACKOUT, all emergency actions logged with enhanced MMR detail (full payload hashes, not just summaries). |
| **Fallback if transition fails** | If the originating phase cannot be re-entered after emergency resolution, the swarm evaluates the next valid phase transition. If no valid transition exists, remain in EMERGENCY_OPS with conservation-focused envelope until ground contact. |

---

## 5. Swarm Heartbeat Protocol

### 5.1 Heartbeat Payload

Each unit broadcasts a heartbeat message via `local_squad_mesh` at a configurable interval (default: 10 seconds during SURFACE_OPS, 2 seconds during DESCENT/ASCENT/REENTRY).

```typescript
interface HeartbeatMessage {
  /** Unit identifier */
  unitId: string;
  /** Monotonic heartbeat sequence number */
  seq: number;
  /** Unix timestamp (ms) */
  timestamp: number;
  /** Currently active specialist mode */
  mode: PadMode;  // ENGINEERING | NAVIGATION | SYSTEMS | SCIENCE | COMMS | MISSION
  /** Current code zone of the active pad */
  zone: CodeZone;  // HOT | SAFE
  /** Power level normalized [0, 1] */
  power: number;
  /** NK coherence [0, 1] */
  coherence: number;
  /** Currently executing task ID (or null if idle) */
  currentTask: string | null;
  /** Detected anomalies since last heartbeat */
  anomalies: AnomalyReport[];
  /** 3D position [x, y, z] */
  position: [number, number, number];
  /** Resource snapshot (all 6 resources) */
  resources: ResourceSnapshot;
  /** Current envelope ID */
  activeEnvelopeId: string;
  /** HMAC-SHA256 of payload (using squad shared key) */
  hmac: string;
}

interface AnomalyReport {
  /** Anomaly type */
  type: 'sensor_fault' | 'resource_depleting' | 'coherence_drop' | 'quorum_disagreement' | 'envelope_expiring' | 'unknown';
  /** Severity 0.0 (informational) to 1.0 (critical) */
  severity: number;
  /** Human-readable description */
  description: string;
}
```

### 5.2 Heartbeat Miss Protocol

When a unit misses heartbeats, the squad responds with escalating severity:

| Missed Beats | Classification | Squad Response |
|-------------|---------------|----------------|
| 1 | Stale | Log as informational. No action. Likely a minor mesh delay. |
| 2 | Warning | Squad leader queries the unit directly via `local_squad_mesh` unicast. Log as warning. Other units begin evaluating task redistribution plans (but do not execute yet). |
| 3 | Lost | Unit classified as LOST. Squad initiates the following recovery sequence. |

**On 3 missed heartbeats (unit classified LOST):**

1. **Task redistribution**: The lost unit's active task is redistributed to the unit with the lowest current hEff and compatible mode. If no unit has the required mode active, the nearest unit switches mode (via `ModePad.switchMode()`) to take over. The redistribution is logged in the MMR audit chain.

2. **SAFE zone revocation**: All of the lost unit's SAFE zone promotions are revoked. This prevents any in-progress SAFE-zone operation from completing unsupervised. Implemented by broadcasting a `zone_revoke` message for the lost unit's ID. Other units update their local state to reject any SAFE-zone claims from the lost unit.

3. **Resource re-estimation**: The squad re-computes the combined resource profile without the lost unit's contribution. If the lost unit carried shared resources (e.g., a relay antenna extending bandwidth, a solar array supplement), the scarcity multipliers for those resources increase immediately.

4. **Leader re-election**: If the lost unit was the squad leader, a new leader is elected via `SquadSpace.findLeader()` (lowest `hEff - coherence * 1000` score among remaining units). The new leader's first action is to broadcast a leader announcement and re-verify the active envelope.

5. **Quorum adjustment**: With 5 remaining units, the BFT quorum threshold adjusts: n=5, f=1, threshold=4 (still requires 4 votes, but from 5 units instead of 6, giving less margin). If a second unit is lost (n=4), threshold=3. Below n=4, quorum cannot be met and the squad enters EMERGENCY_OPS with all actions at QUARANTINE.

### 5.3 Recovery Protocol (Unit Comes Back Online)

When a previously-LOST unit resumes heartbeat transmission:

1. **Identity verification**: The returning unit's first heartbeat is verified against its known ML-DSA-65 public key. The squad does not accept the unit back until identity is cryptographically confirmed.

2. **State reconciliation**: The returning unit receives:
   - Current epoch and active envelope (from squad leader)
   - MMR peaks (so it can reconstruct the audit chain state)
   - Updated squad roster (in case other units were also lost)
   - Current task assignments

3. **Probationary period**: The returning unit starts in HOT zone on all pads, regardless of its zone state when it went LOST. It must re-earn SAFE promotion through normal `canPromoteToSafe()` checks.

4. **Quorum restoration**: Once the returning unit is verified and synchronized, the quorum parameters are restored (e.g., back to n=6, f=1, threshold=4 if all 6 units are present).

5. **Diagnostic submission**: The returning unit must submit a diagnostic report explaining the outage. This report is logged in the MMR audit chain and flagged for ground control review. If the diagnostic indicates hardware failure, the unit may be restricted to reduced capability via a narrower local envelope.

---

## 6. Ground Control Cockpit

The Ground Control Cockpit is the IDE panel set that surfaces when the SCBE IDE is operating in Mission Control mode. It replaces (or augments) the standard Governance Panel, Action Queue, and Audit Log Viewer with mission-aware equivalents.

### 6.1 Decision Replay

**Purpose**: Step through every governance decision made during a communication blackout, in order, with full context.

**Interface**:
- Timeline scrubber: horizontal bar representing the blackout period. Each governance decision is a marker on the timeline. Markers are color-coded: green (AUTO_ALLOW), yellow (QUARANTINE), red (DENY), purple (emergency override).
- Detail panel: selecting a marker shows the full `BlackoutAuditEntry` for that decision, including: acting unit, pad mode, zone, decision, dStar, coherence, hEffResource, envelope ID, quorum votes, resource snapshot, and action summary.
- Play/pause/step controls: automatically advance through decisions at configurable speed (1x, 5x, 10x, 50x real-time). Pause at any point to inspect.
- Filter controls: filter by unit, mode, decision type, resource threshold ("show only decisions where power < 30%"), anomaly presence.
- Verification indicator: each entry shows a green checkmark if its MMR inclusion proof verifies, or a red X if verification fails.

**Data source**: MMR delta sync payload received after blackout ends. Cached locally for replay.

### 6.2 Retroactive Override

**Purpose**: After reviewing blackout decisions, ground control can flag specific decisions for future envelope restrictions. This does not undo past actions (which are already executed), but ensures the behavior is not repeated.

**Interface**:
- Right-click any decision in the Decision Replay timeline.
- Select "Flag for Restriction" -- opens a dialog with:
  - **Action class** (auto-populated from the flagged entry's action summary)
  - **New boundary** (dropdown: move from AUTO_ALLOW to QUARANTINE, or from QUARANTINE to DENY)
  - **Scope** (this unit only, all units, specific modes)
  - **Justification** (free-text, required)
- Flagged restrictions are queued for inclusion in the next envelope refresh.

**Constraint**: Retroactive override cannot change the past audit chain. It only influences future envelopes. The original decision and the retroactive flag are both recorded in the audit trail.

### 6.3 Envelope Refresh

**Purpose**: Sign and upload new Decision Envelopes to the swarm.

**Interface**:
- **Envelope editor**: form-based creation with the following fields:
  - Action classes (multi-select from defined taxonomy)
  - Boundary assignments per class (AUTO_ALLOW / QUARANTINE / DENY)
  - Parameter bounds (max dStar, min coherence, max hEff per class)
  - Resource minimums (if any resource drops below this level, the action class escalates from AUTO_ALLOW to QUARANTINE)
  - Expiry epoch (absolute time, with visual countdown)
  - Fallback behavior on expiry (conservative / maintain_last / custom)
- **Template library**: pre-built envelopes for each mission phase (TRANSIT, SURFACE_OPS, etc.)
- **Diff view**: compare the new envelope against the currently active one, highlighting changes.
- **Sign button**: signs the envelope with the ground control ML-DSA-65 private key (stored in the IDE's Secure Vault).
- **Upload button**: transmits the signed envelope over `earth_deep_space` channel. If channel is BLACKOUT, envelope is queued with visual indicator showing queue position.
- **Status tracking**: shows whether the envelope was received by the swarm (ACK) or is still in transit/queued.

### 6.4 Selective Command Injection

**Purpose**: Target specific units with mode or task overrides without modifying the global envelope.

**Interface**:
- Unit selector: dropdown or swarm map click to select target unit(s).
- Command types:
  - **Mode switch**: force a unit to switch to a specific specialist mode (e.g., "Unit 3: switch to ENGINEERING mode, reason: ground control diagnosis").
  - **Task assignment**: assign a specific task to a unit, bypassing the normal task distribution.
  - **Task cancellation**: cancel a unit's current task.
  - **Zone override**: force a pad back to HOT zone.
  - **Resource alert**: send a resource advisory (e.g., "conserve propellant, reduce traverse distance").
- All commands are governance-checked against the active envelope before transmission.
- All commands are logged in the ground control audit trail with operator ID and justification.

**Constraint**: Commands transmitted over `earth_deep_space` are subject to latency. The IDE shows estimated delivery time based on current one-way light time. Commands are not guaranteed to arrive in order if multiple are sent during a single contact window.

### 6.5 Swarm Health Dashboard

**Purpose**: Real-time (when LIVE or DELAYED) or last-known (when BLACKOUT) visualization of swarm state.

**Components**:

- **Swarm map**: 3D or 2D projection of unit positions (from heartbeat `position` fields). Lines between units show proximity graph (from `SquadSpace.neighbors()`). Line thickness indicates mesh signal strength.
- **Unit cards**: one card per unit showing:
  - Unit ID and current status (active / stale / warning / lost)
  - Active mode and zone
  - Power level (bar chart, color-coded: green > 60%, yellow > 30%, red < 30%)
  - Coherence score (0-1 gauge)
  - Current task (if any)
  - Last heartbeat timestamp (with "X seconds ago" relative display)
  - Anomaly count since last clear
- **Resource overview**: stacked bar chart showing all 6 resource dimensions across all units. Highlights units with any resource below 30%.
- **Risk field**: heat map overlay on the swarm map showing the SCBE decision (`SquadSpace.riskField()`) for each unit. Green (ALLOW), yellow (QUARANTINE), red (DENY).
- **Leader indicator**: the current squad leader is visually distinguished (crown icon or highlighted border).
- **Blackout indicator**: when comms are in BLACKOUT, the dashboard displays "LAST KNOWN STATE -- [timestamp]" prominently. All data freezes at the last received heartbeat values. A countdown shows estimated time until next contact window (if known).

### 6.6 MMR Verification Panel

**Purpose**: Verify cryptographic proofs from the blackout audit chain.

**Interface**:

- **Chain overview**: visual representation of the MMR structure (tree peaks, entry count, root hash).
- **Consistency check**: one-click button to verify that the current MMR is a consistent extension of the pre-blackout MMR. Shows green (consistent) or red (inconsistent, with details).
- **Inclusion proof verifier**: enter or select an entry sequence number. The panel computes and displays the O(log n) inclusion proof path. Each hash in the path is shown with pass/fail indicator.
- **Batch verification**: verify all entries in a time range. Progress bar, with failed entries highlighted in the Decision Replay timeline.
- **Quorum verification**: for each entry, verify that the BFT quorum proof contains valid ML-DSA-65 signatures from 4 or more known squad members. Failed signature verifications are flagged.
- **Export**: export the full MMR structure, proofs, and verification results as JSON for external audit tools.

---

## 7. Build Plan Integration

These extensions integrate into the existing 90-day build plan (BUILD_PLAN_90D.md) as targeted additions to existing phase deliverables. They do not extend the timeline.

### Week 6 (Phase 2): Decision Envelope Schema + Resource-Aware Harmonic Cost

**Additions to existing Week 6 deliverables** (Secure Vault + Goal Lifecycle):

| Deliverable | Effort | Integration Point |
|-------------|--------|-------------------|
| `DecisionEnvelope` TypeScript interface and validation functions | 2 days | Extends `voxelRecord.ts` decision system |
| `envelopeDecide()` function that wraps `scbeDecide()` with envelope awareness | 1 day | Replaces `canPromoteToSafe()` boolean with richer return type |
| `ResourceSnapshot` type and 6-resource tracking data model | 1 day | Extends `UnitState` in `polly-pad-runtime.ts` |
| `harmonicCostResource()` function implementing the scarcity multiplier product | 1 day | Extends `harmonicCost()` in `voxelRecord.ts` |
| Unit tests for scarcity multiplier edge cases (r_i = 0, r_i = 1, multi-resource products) | 0.5 days | `tests/harmonic/` |
| Property-based tests: `harmonicCostResource() >= harmonicCost()` for all valid inputs | 0.5 days | `tests/L4-property/` |

**Total added effort**: ~6 days. This fits within Week 6 because the Vault and Goal Lifecycle work is already budgeted at 5 days, and Week 6 has buffer from the Vault work being constrained (no UI polish needed for V0 vault).

### Week 9 (Phase 3): BFT Quorum for QUARANTINE Escalation + Blackout Audit Chain

**Additions to existing Week 9 deliverables** (Research-Task-Approve-Execute Loop):

| Deliverable | Effort | Integration Point |
|-------------|--------|-------------------|
| QUARANTINE escalation path: actions in QUARANTINE boundary require BFT quorum before execution | 1 day | Extends governance gating in RTAE loop |
| `MerkleMountainRange` class: append, inclusion proof, consistency proof, peaks, root hash | 3 days | New data structure, standalone implementation |
| `BlackoutManager` class: switches audit system to MMR on BLACKOUT detection | 1 day | Integrates with `ClosedNetwork.config.earthContactAvailable` |
| `BlackoutAuditEntry` type with full context (quorum proof, resource snapshot, envelope reference) | 0.5 days | Extends `AuditEntry` from `polly-pad.ts` |
| MMR sync protocol: peak exchange, delta sync, priority flagging | 1 day | Integrates with `ClosedNetwork.setEarthContact()` |
| Unit tests for MMR: append ordering, inclusion proof verification, consistency after tampering | 1 day | `tests/fleet/` |
| Integration test: simulate blackout, accumulate entries, restore contact, verify sync | 0.5 days | `tests/L3-integration/` |

**Total added effort**: ~8 days. This is aggressive for a single week. Mitigation: the MMR implementation is a pure data structure with no external dependencies. It can be started in Week 8 as a background task alongside the AI governance gating work, which is primarily UI-focused.

### Week 12 (Phase 4): Ground Control Replay/Override UI + MMR Verification Panel

**Additions to existing Week 12 deliverables** (Cross-Platform Testing + Offline Mode):

| Deliverable | Effort | Integration Point |
|-------------|--------|-------------------|
| Decision Replay UI: timeline scrubber, detail panel, play/pause/step controls | 2 days | New tab in the Governance Panel (right panel) |
| Retroactive Override: right-click flag, restriction dialog, queue for envelope refresh | 1 day | Extension of Decision Replay |
| MMR Verification Panel: consistency check, inclusion proof verifier, batch verification | 2 days | New tab in the Governance Panel |
| Swarm Health Dashboard: unit cards, resource overview, risk field visualization | 2 days | Replaces or augments the existing Governance Panel decision feed |
| Integration with existing cross-platform testing: verify Mission Control panels render on Windows + macOS | 1 day | Part of existing cross-platform matrix |

**Total added effort**: ~8 days. This compresses the cross-platform testing and offline validation. Mitigation: the Mission Control panels are read-only visualizations -- they display data but do not modify system state. This makes them lower-risk to ship without extensive cross-platform testing. The critical path (MMR verification, decision replay) can be tested on the primary platform (Windows) with macOS testing deferred to Week 13.

### Post-V0: Full Mission Phase State Machine + Predictive Resource Modeling

These features are explicitly deferred to V1 or V2:

| Feature | Target | Rationale |
|---------|--------|-----------|
| Full 10-phase state machine with automated transitions | V1 | Requires mission simulation infrastructure not in V0 scope. The phase definitions in this document are specification, not implementation -- V0 implements SURFACE_OPS only. |
| Predictive resource modeling (project resource depletion curves, pre-compute when freezing will occur) | V1 | Requires historical resource data and curve-fitting. V0 uses instantaneous resource snapshots only. |
| Envelope template library for all mission phases | V1 | Depends on full state machine. V0 ships with a generic envelope template. |
| Swarm simulation mode (test envelopes against simulated swarm behavior before uploading) | V2 | Requires a full physics + resource simulation engine. High effort, high value, but not V0. |
| Multi-squad coordination (multiple squads of 6 units, inter-squad governance) | V2 | Current SquadSpace handles a single squad of 6. Multi-squad is an architecture extension. |
| Heartbeat protocol over real UHF radio (hardware integration) | V2+ | V0 and V1 use software-simulated mesh. Hardware integration requires partner hardware. |

---

## 8. Implementation Files

The following new source files will be created to implement the three Mars-grade extensions. Each file extends the existing fleet module without modifying existing source files.

### 8.1 `src/fleet/polly-pads/decision-envelope.ts`

**Purpose**: Decision Envelope types, validation, and EnvelopeManager.

**Contents**:

| Export | Type | Description |
|--------|------|-------------|
| `DecisionEnvelope` | interface | Signed document defining autonomous decision boundaries. Fields: id, version, signedBy (ground control key hash), signedAt, expiryEpoch, actionClasses (map of action class name to boundary type), parameterBounds (max dStar, min coherence, max hEff per class), resourceMinimums (per-class resource floors), fallbackBehavior, signature (ML-DSA-65). |
| `EnvelopeBoundary` | type | `'AUTO_ALLOW' \| 'QUARANTINE' \| 'DENY'` |
| `EnvelopeDecision` | interface | Result of `envelopeDecide()`. Fields: boundary (EnvelopeBoundary), reason (string), envelopeId (string), requiresQuorum (boolean), emergencyOverrideAvailable (boolean). |
| `ActionClass` | interface | Definition of an action class within an envelope. Fields: name, description, defaultBoundary, parameterBounds, resourceMinimums. |
| `EmergencyOverride` | interface | Record of an emergency key override. Fields: overrideId, initiatingUnit, quorumVotes, originalDenialReason, justification, outcome, timestamp. |
| `EnvelopeManager` | class | Manages envelope lifecycle (cache active, validate signatures, check expiry, handle transitions). Methods: `activate(envelope)`, `isActive()`, `getActive()`, `envelopeDecide(pad, state, actionClass, quorumVotes?)`, `handleExpiry()`, `emergencyOverride(unitId, actionClass, justification, quorumVotes)`. |
| `validateEnvelopeSignature` | function | Verify ML-DSA-65 signature on an envelope. |
| `createEnvelopeTemplate` | function | Generate a pre-filled envelope for a given mission phase. |

**Depends on**: `voxelRecord.ts` (scbeDecide, harmonicCost, SCBEThresholds), `polly-pad-runtime.ts` (PadRuntime, UnitState, CodeZone), `closed-network.ts` (ClosedNetwork for transport).

### 8.2 `src/fleet/polly-pads/resource-harmonic.ts`

**Purpose**: Scarcity multipliers and resource-aware harmonic cost computation.

**Contents**:

| Export | Type | Description |
|--------|------|-------------|
| `ResourceSnapshot` | interface | Current levels of all 6 tracked resources. Fields: power (number, 0-1), bandwidth (number, 0-1), thermalMargin (number, 0-1), mechanicalWear (number, 0-1), propellant (number, 0-1), storage (number, 0-1). |
| `ScarcityMultiplier` | interface | Computed scarcity for a single resource. Fields: resource (ResourceName), level (number), scarcity (number). |
| `ResourceName` | type | `'power' \| 'bandwidth' \| 'thermalMargin' \| 'mechanicalWear' \| 'propellant' \| 'storage'` |
| `RESOURCE_TONGUE_MAP` | const | Maps each ResourceName to its Sacred Tongue: power->KO, bandwidth->AV, thermalMargin->RU, mechanicalWear->CA, propellant->UM, storage->DR. |
| `scarcityMultiplier` | function | `(resourceLevel: number) => number`. Computes `1 / r^2` with clamping: r is clamped to [0.01, 1.0] to avoid division by zero (floor scarcity = 10,000x). |
| `combinedScarcity` | function | `(resources: ResourceSnapshot) => number`. Computes product of all 6 scarcity multipliers. |
| `harmonicCostResource` | function | `(dStar: number, R: number, resources: ResourceSnapshot) => number`. Computes `R * pi^(phi * dStar) * combinedScarcity(resources)`. Extends the existing `harmonicCost()` from `voxelRecord.ts`. |
| `resourceDecide` | function | `(dStar: number, coherence: number, resources: ResourceSnapshot, thresholds: SCBEThresholds) => Decision`. Calls `harmonicCostResource()` then `scbeDecide()` with the resource-adjusted hEff. |
| `resourceReport` | function | `(resources: ResourceSnapshot) => ScarcityMultiplier[]`. Returns per-resource scarcity breakdown for dashboard display. |

**Depends on**: `voxelRecord.ts` (harmonicCost, scbeDecide, SCBEThresholds, PHI constant).

### 8.3 `src/fleet/polly-pads/blackout-audit.ts`

**Purpose**: Merkle Mountain Range implementation and BlackoutManager.

**Contents**:

| Export | Type | Description |
|--------|------|-------------|
| `MMRNode` | interface | A node in the MMR tree. Fields: hash (string), height (number), left? (MMRNode), right? (MMRNode). |
| `MMRPeaks` | type | `string[]` -- array of peak hashes. |
| `InclusionProof` | interface | Proof that an entry is in the MMR. Fields: entryIndex (number), entryHash (string), path (ProofStep[]), root (string). |
| `ProofStep` | interface | A single step in an inclusion proof. Fields: hash (string), position ('left' \| 'right'). |
| `ConsistencyProof` | interface | Proof that the MMR is a valid extension of a previous state. Fields: oldPeaks (MMRPeaks), newPeaks (MMRPeaks), valid (boolean). |
| `BlackoutAuditEntry` | interface | Full audit entry for blackout period. Fields as defined in Section 2.3 of this document. |
| `MerkleMountainRange` | class | Append-only MMR data structure. Methods: `append(data: string): number` (returns leaf index), `getRoot(): string`, `getPeaks(): MMRPeaks`, `inclusionProof(index: number): InclusionProof`, `verifyInclusion(proof: InclusionProof): boolean`, `consistencyProof(oldPeaks: MMRPeaks): ConsistencyProof`, `size(): number`, `toJSON(): object`, `static fromJSON(data: object): MerkleMountainRange`. |
| `BlackoutManager` | class | Manages the transition between linear audit chain and MMR during blackout. Methods: `onBlackoutStart()` (switch to MMR mode), `onBlackoutEnd()` (prepare sync payload), `logEntry(entry: BlackoutAuditEntry): number` (append to MMR), `prepareSyncPayload(lastKnownPeaks: MMRPeaks): SyncPayload` (compute delta for ground control), `verifySyncAck(ackRootHash: string): boolean` (confirm ground received correct data). Integrates with `ClosedNetwork` for blackout detection. |
| `SyncPayload` | interface | Data transmitted to ground control on contact restoration. Fields: peaks (MMRPeaks), root (string), newEntries (BlackoutAuditEntry[]), consistencyProof (ConsistencyProof), priorityFlags (number[] -- indices of entries requiring immediate review). |
| `verifyBlackoutEntry` | function | Standalone verification: checks quorum signatures, envelope reference validity, and resource-cost consistency for a single BlackoutAuditEntry. |

**Depends on**: `voxelRecord.ts` (QuorumProof, validateQuorum), `decision-envelope.ts` (DecisionEnvelope), `resource-harmonic.ts` (ResourceSnapshot, harmonicCostResource), `closed-network.ts` (ClosedNetwork for blackout detection), Node.js `crypto` (SHA-256 for Merkle hashing).

---

## Appendix A: Notation Reference

| Symbol | Meaning | Source |
|--------|---------|--------|
| `d*` (dStar) | Hyperbolic realm distance from safe center | `UnitState.dStar` in `polly-pad-runtime.ts` |
| `H(d*, R)` | Harmonic cost (original) | `harmonicCost()` in `voxelRecord.ts` |
| `H_resource(d*, R, resources)` | Resource-adjusted harmonic cost | Section 2.2 |
| `S_i` | Scarcity multiplier for resource i | `1 / r_i^2` |
| `r_i` | Normalized resource level [0, 1] | `ResourceSnapshot` fields |
| `phi` (PHI) | Golden ratio (1 + sqrt(5)) / 2 | Constant in `voxelRecord.ts` |
| `pi` | 3.14159... | `Math.PI` |
| `R` | Base resistance (default 1.5) | Second parameter to `harmonicCost()` |
| `n` | Total units in squad | Default 6, in `SquadSpace.quorumOk()` |
| `f` | Maximum faulty units tolerated | Default 1 (BFT: n >= 3f + 1) |
| `threshold` | Minimum votes for quorum | Default 4 (BFT: 2f + 1) |
| `nu` (v) | Flux coefficient [0, 1] | `PollyPad.nu` in `polly-pad.ts` |

## Appendix B: Glossary Additions

These terms extend the glossary in MVP_SPEC.md Appendix B.

| Term | Definition |
|------|-----------|
| **Decision Envelope** | A signed, time-bounded document that pre-authorizes classes of actions within defined parameters. Ground control signs it; the swarm executes within it. |
| **Scarcity Multiplier** | `S_i = 1 / r_i^2` -- transforms a normalized resource level into a cost multiplier. Lower resources = higher cost. |
| **Freezing Effect** | The natural behavior where depleting resources make non-essential actions computationally impossible via compounding scarcity multipliers. |
| **Merkle Mountain Range (MMR)** | An append-only data structure that provides O(1) append, O(log n) inclusion proofs, and O(peaks) sync. Used for blackout audit chains. |
| **MMR Peak** | The root hash of a perfect binary tree within the MMR. The set of peaks defines the MMR state. |
| **Inclusion Proof** | A cryptographic proof (O(log n) hashes) that a specific entry exists within an MMR. |
| **Consistency Proof** | A cryptographic proof that an MMR is a valid extension of a previous MMR state (no entries were removed or modified). |
| **Blackout** | A period when `earth_deep_space` communication channel is unavailable. The swarm operates autonomously within envelope bounds. |
| **Emergency Key Override** | A quorum-gated (4/6) mechanism to override a DENY decision for mission-critical actions when ground control is unreachable. |
| **Heartbeat** | Periodic broadcast by each unit containing its current state. Used for health monitoring, leader election, and lost-unit detection. |
| **Mission Phase** | One of 10 operational phases (LAUNCH through REENTRY) that determine the primary mode, envelope profile, resource priorities, and comms expectations for the swarm. |
| **Ground Control Cockpit** | The Mission Control view of the SCBE IDE, providing decision replay, retroactive override, envelope management, command injection, swarm health visualization, and MMR verification. |
