---
name: scbe-flock-shepherd
description: Manage and orchestrate the AI flock — spawn agents, assign roles (leader/validator/executor/observer), track health and coherence, redistribute tasks, view fleet status, and govern agent interactions via SCBE governance gates. Use when managing multiple AI agents, coordinating swarm tasks, checking agent health, or shepherding the flock.
---

# SCBE Flock Shepherd

Orchestrate a governed fleet of AI agents. The flock is a set of HYDRA heads connected through the Spine, each with a role, health score, and position in the 6D Poincare trust space.

## Core Concepts

- **Flock**: The full set of active AI agents under SCBE governance
- **Sheep**: An individual agent (HYDRA head) that has been trained and deployed
- **Shepherd**: This skill — the coordinator that manages the flock
- **Pen**: A grouping of agents by specialty (system/governance/functions tracks)
- **Shearing**: Extracting learned artifacts from agents for federated fusion

## Agent Roles (from hydra/swarm_governance.py)

| Role | Purpose | Tongue |
|------|---------|--------|
| LEADER | Proposes actions, coordinates | KO (assertive) |
| VALIDATOR | Votes on proposals via BFT | AV (receptive) |
| EXECUTOR | Executes approved actions | RU (grounded) |
| OBSERVER | Monitors, reports anomalies | UM (silence) |

## Flock Operations

### 1. Spawn Agent
Create a new HYDRA head and register it with the Spine.

```python
# Use hydra/head.py HydraHead + hydra/spine.py
from hydra.head import HydraHead, AIType
from hydra.spine import HydraSpine

head = HydraHead(
    head_id="sheep-001",
    ai_type=AIType.CLAUDE,  # or CODEX, GPT, GEMINI, LOCAL
    name="Governance Specialist",
)
spine = HydraSpine()
await spine.register_head(head)
```

### 2. Assign Roles
Map agents to specialties based on training track.

```python
# Track -> Role mapping
TRACK_ROLES = {
    "system": AgentRole.LEADER,       # Architecture knowledge
    "governance": AgentRole.VALIDATOR, # Policy/safety checks
    "functions": AgentRole.EXECUTOR,   # Code execution
}
```

### 3. Health Check
Monitor agent coherence using the 6D Poincare ball position.

```python
# From hydra/swarm_governance.py SwarmAgent
agent.coherence  # 0.0 to 1.0
agent.state      # ACTIVE, IDLE, VOTING, EXECUTING, ISOLATED, FROZEN
agent.position   # 6D vector in Poincare ball

# Isolation threshold
if agent.coherence < 0.3:
    agent.state = AgentState.ISOLATED  # Quarantine
```

### 4. Task Distribution
Use balanced ternary governance to decide task routing.

```python
# Pack agent votes as governance trits
from src.symphonic_cipher.scbe_aethermoore.trinary import BalancedTernary

votes = ["ALLOW", "ALLOW", "DENY", "QUARANTINE", "ALLOW"]
packed = BalancedTernary.pack_decisions(votes)
summary = packed.governance_summary()
# summary["consensus"] -> "ALLOW" (net positive)
```

### 5. Flock Status Dashboard

Report format:
```
FLOCK STATUS
============
Total Agents: 6
  Active:   4  (KO=1, AV=2, RU=1)
  Idle:     1  (UM=1)
  Isolated: 1  (DR=1, coherence=0.21)

Consensus Health: 83% (5/6 above threshold)
BFT Tolerance: f=1 (can tolerate 1 Byzantine agent)

Training Tracks:
  system:     2 agents, 847 SFT pairs
  governance: 2 agents, 312 SFT pairs
  functions:  2 agents, 521 SFT pairs
```

### 6. Redistribute Work
When an agent is isolated or frozen, redistribute its pending tasks.

Steps:
1. Identify orphaned tasks from isolated agent
2. Find available agents with matching track specialty
3. Use BFT consensus to approve redistribution
4. Update the Spine ledger with new assignments
5. Log the redistribution in membrane_log.jsonl

### 7. Shearing (Extract Learned Artifacts)
Pull training artifacts from agents for federated fusion.

```python
# Use training/federated_orchestrator.py
# Each agent produces a manifest with quality/safety/latency metrics
# The orchestrator fuses them through promotion gates
```

## Key Files

| File | Purpose |
|------|---------|
| `hydra/head.py` | Universal AI interface (HydraHead) |
| `hydra/spine.py` | Central coordinator (HydraSpine) |
| `hydra/swarm_governance.py` | BFT + hyperbolic governance (SwarmAgent) |
| `hydra/consensus.py` | Byzantine consensus protocol |
| `hydra/switchboard.py` | Message routing between heads |
| `hydra/ledger.py` | Immutable action ledger |
| `hydra/llm_providers.py` | Multi-provider LLM abstraction |
| `training/federated_orchestrator.py` | Multi-cloud artifact fusion |
| `training/train_node_fleet_three_specialty.py` | 3-specialist training |
| `agents/browser/fleet_coordinator.py` | Browser fleet orchestration |

## Governance Integration

All flock operations pass through the SCBE governance gate:
1. Agent spawn -> governance check (is this agent type allowed?)
2. Task assignment -> governance check (does agent have clearance?)
3. Code execution -> governance check (is the code safe?)
4. Artifact fusion -> governance check (do quality gates pass?)

The flock shepherd NEVER bypasses governance. Every action is logged.
