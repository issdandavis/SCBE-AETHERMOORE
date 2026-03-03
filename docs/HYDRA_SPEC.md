# HYDRA Spec (Standalone)

Status: Canonical
Source: docs/HYDRA_COORDINATION.md (Notion-synced) + hydra/ code tree
Version: 0.1.0
Last updated: 2026-03-03

## Purpose

HYDRA is a multi-agent coordination layer that provides:
- Parallel "swarm browser" task execution via six Sacred Tongue agents.
- Replayable audit trails (ledger + manifest hashes).
- Fault tolerance via quorum and Byzantine-style thresholds.
- Governance gating (ALLOW / QUARANTINE / DENY) integrated with SCBE outputs.

Normative sources:
- `docs/HYDRA_COORDINATION.md` (architecture and governance flows)
- `hydra/` (Python implementation modules)

Non-goals (this spec):
- Defining the full SCBE 14-layer math (see `LAYER_INDEX.md`)
- Defining post-quantum primitives in detail (see `src/crypto/`)
- UI/UX requirements (terminal-native is assumed)

## Roles and Agents

HYDRA uses six Sacred Tongue agents as a "swarm browser" execution plane.
Each tongue is associated with a phase angle and a primary capability:

| Tongue | Role | Phase (deg) | Capability |
|--------|------|-------------|------------|
| KO | SCOUT | 0 | Navigate |
| AV | VISION | 60 | Screenshot / capture |
| RU | READER | 120 | Extract / parse |
| CA | CLICKER | 180 | Interact |
| UM | TYPER | 240 | Input |
| DR | JUDGE | 300 | Verify / validate |

The "phase angle" is a first-class signal used for phase-locking (synchronization).
Phase-locking is used to:
- Increase trust in joint decisions when phases converge
- Degrade or quarantine collaboration when phases diverge

## Core Components

The coordination stack is composed of:
- **Spine** (`hydra/spine.py`): orchestrator coordinating tasks, agents, and consensus.
- **Heads** (`hydra/head.py`): model providers / universal AI interface adapters.
- **Limbs** (`hydra/limbs.py`): execution backends (browser drivers, tool runners).
- **Librarian** (`hydra/librarian.py`): memory + indexing layer.
- **Ledger** (`hydra/ledger.py`): append-only audit records with idempotency invariants.
- **Consensus** (`hydra/consensus.py`): Byzantine quorum (4/6 threshold, f=1).
- **Spectral** (`hydra/spectral.py`): GFSS / anomaly detection.
- **Swarm Browser** (`hydra/swarm_browser.py`): six-agent browser execution plane.
- **Browsers** (`hydra/browsers.py`): browser backend adapters (Playwright/Selenium/CDP).
- **Switchboard** (`hydra/switchboard.py`): task routing and dispatch.
- **Swarm Governance** (`hydra/swarm_governance.py`): SCBE decision integration.

## State Model

### UnitState (9D operational state)

HYDRA unit state is treated as a 9-dimensional vector:

| Field | Type | Kind |
|-------|------|------|
| x, y, z | number | position |
| vx, vy, vz | number | velocity |
| coherence | number [0,1] | governance |
| d_star | number | governance (realm distance) |
| h_eff | number | governance (harmonic score) |

### Voxel Record (atomic state commit)

Voxel records bind:
- **Coordinates**: 6D voxel coordinate (X,Y,Z,V,P,S) + tongue + epoch + mode
- **Governance snapshot**: coherence, dStar, hEff, decision
- **Content payload**: encrypted/sealed
- **Quorum proof**: votes/signatures/path traces

## Governance Gates

HYDRA uses multiple gates; the minimum canonical set:

### G0 — Flux-state gate
Entities are in one of the flux states: `POLLY`, `SUPERPOSITION`, `COLLAPSED`, `ENTANGLED`.
The flux state determines allowed ops, allowed realms, and max step norms.
Implementation: `packages/kernel/src/fluxState.ts`

### G1 — Realm access gate
If `allowedRealms` is restricted, navigation MUST target allowed realms only.

### G2 — Step norm gate
Enforce `maxStepNorm` on navigation step vectors.

### G3 — COLLAPSED "nearest realm only" gate
In `COLLAPSED` state, navigation MUST target nearest realm center.

### G4 — SCBE decision gate
Compute decision (ALLOW/QUARANTINE/DENY) from coherence/dStar/hEff thresholds.
- DENY blocks privileged actions (e.g., promote HOT->SAFE, commit voxel).
- QUARANTINE allows observation but blocks side effects.
- ALLOW permits execution and commits.

### G5 — Quorum gate
For actions requiring consensus, require threshold votes:
- n >= 3f + 1
- threshold >= 2f + 1
- Canonical for n=6 and f=1: threshold=4.

### G6 — Phase-lock gate (ENTANGLED)
ENTANGLED collaboration requires sufficient phase-lock score.
If unlocked, degrade to observe-only or force QUARANTINE pending re-lock.
Implementation: `packages/kernel/src/fluxState.ts` (FluxDynamicsContext)

## Update Rules

Minimal deterministic update rules:

### U0 — Neighbor detection
Compute proximity neighbors within radius R using positions (x,y,z).

### U1 — Phase update and lock scoring
Maintain oscillatory phases per agent; compute lock score between partners.
Lock score must be replayable given the same timebase and inputs.

### U2 — Zone promotion (HOT -> SAFE)
Requires SCBE gate to be ALLOW AND quorum votes >= threshold.

## Theorems / Invariants (As System Contracts)

### T0 — Ledger idempotency
Duplicate idempotency keys MUST NOT create a second write.

### T1 — Canonical agent ordering
For spectral/graph ops, sort by stable agent_id before matrix construction.

### T2 — Quorum safety
If n >= 3f + 1 and threshold >= 2f + 1, a single faulty agent cannot unilaterally force ALLOW.

## File/Module Expectations

Minimum required modules:
- `hydra/spine.py`
- `hydra/consensus.py`
- `hydra/spectral.py`
- `hydra/ledger.py`
- `hydra/swarm_browser.py`
- `hydra/browsers.py`
- `hydra/swarm_governance.py`
- `hydra/switchboard.py`
- `docs/HYDRA_SPEC.md` (this file)
- `docs/hydra_index.json` (machine index)

## Open Questions

- Explicit definition of "phase" (per tongue, per agent, per task) and timebase source.
- Exact mapping between SCBE L5-L13 numerical outputs and HYDRA thresholds.
- Whether breathing feedback (Kuramoto order parameter -> L6 breathing config) should be formalized.
