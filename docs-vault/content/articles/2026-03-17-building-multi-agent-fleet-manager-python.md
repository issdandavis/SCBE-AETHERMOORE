# Building a Multi-Agent Fleet Manager in Python

Running one AI agent is straightforward. Running fifty of them -- with health monitoring, task distribution, fault tolerance, and governance voting -- requires a fleet manager. SCBE-AETHERMOORE's Flock Shepherd is a production-grade implementation of exactly that, and it is open source.

This article walks through the architecture, with real code from the `flock_shepherd.py` module.

## The Metaphor: Shepherd and Sheep

Every agent in the fleet is a "Sheep" with a role, health score, and position in 6D trust space. The "Flock" is the fleet manager that orchestrates their lifecycle.

```python
from src.symphonic_cipher.scbe_aethermoore.flock_shepherd import (
    Flock, TrainingTrack, SheepRole
)

# Create a fleet
fleet = Flock()

# Spawn agents with different specializations
leader = fleet.spawn("Atlas", track=TrainingTrack.SYSTEM)       # Becomes LEADER
validator = fleet.spawn("Sage", track=TrainingTrack.GOVERNANCE)  # Becomes VALIDATOR
worker = fleet.spawn("Forge", track=TrainingTrack.FUNCTIONS)     # Becomes EXECUTOR
```

The `TrainingTrack` determines the default role. System-trained agents lead. Governance-trained agents validate. Function-trained agents execute. You can override this, but the defaults enforce separation of concerns.

## Agent Lifecycle: Spawn, Monitor, Retire

Each Sheep tracks its own health through a **coherence score** from 0.0 to 1.0. This is not an arbitrary metric -- it maps to a position in the Poincare ball model used by SCBE's 14-layer pipeline.

Three thresholds govern agent state transitions:

| Coherence | Label | Action |
|-----------|-------|--------|
| >= 0.70 | HEALTHY | Normal operation |
| 0.50 - 0.69 | FAIR | Warning, increased monitoring |
| 0.30 - 0.49 | WARNING | Eligible for task redistribution |
| < 0.30 | CRITICAL | Auto-quarantine (ISOLATED state) |

The state machine is self-healing. Successful task completions recover coherence; failures degrade it:

```python
@dataclass
class Sheep:
    coherence: float = 1.0

    def degrade(self, amount: float = 0.05) -> None:
        """Degrade coherence after an error."""
        self.coherence = max(0.0, self.coherence - amount)
        if self.coherence < COHERENCE_ISOLATE:  # 0.30
            self.state = SheepState.ISOLATED

    def recover(self, amount: float = 0.02) -> None:
        """Recover coherence after successful task."""
        self.coherence = min(1.0, self.coherence + amount)
        if self.state == SheepState.ISOLATED and self.coherence >= COHERENCE_WARN:
            self.state = SheepState.ACTIVE
```

Notice the asymmetry: degradation is 2.5x faster than recovery. This means an agent that starts failing rapidly gets quarantined, but an agent that recovers must prove sustained good behavior before rejoining the fleet.

## Task Distribution with Auto-Selection

Tasks enter a queue with a priority and a training track. The fleet manager auto-selects the best agent:

```python
# Add a governance evaluation task
task = fleet.add_task(
    "Evaluate policy compliance for deployment #47",
    track=TrainingTrack.GOVERNANCE,
    priority=2
)

# Auto-assign to the best available governance agent
fleet.assign_task(task.task_id)
```

The selection algorithm is simple but effective: filter by track specialization, then sort by coherence (highest first), then by experience (tasks completed). If no specialist is available, any healthy agent can pick up the task.

When an agent is retired or quarantined mid-task, its tasks become "orphaned." A single call redistributes them:

```python
# An agent goes down
fleet.retire(leader.sheep_id)

# Reassign its abandoned tasks
reassigned = fleet.redistribute_orphans()
print(f"Redistributed {reassigned} orphaned tasks")
```

## Balanced Ternary Governance Voting

Here is where the Flock Shepherd diverges from typical fleet managers. Every significant action goes through a **governance vote** using balanced ternary encoding.

Balanced ternary uses digits {-1, 0, +1} instead of {0, 1}. The governance mapping:

| Decision | Trit Value | Meaning |
|----------|-----------|---------|
| ALLOW | +1 | Positive affirmation |
| QUARANTINE | 0 | Uncertain, needs review |
| DENY | -1 | Reject the action |

Every active VALIDATOR agent casts a vote based on its coherence. The votes are packed into a balanced ternary word and summarized:

```python
result = fleet.vote_on_action("deploy model v2.1 to production")

# result = {
#     "action": "deploy model v2.1 to production",
#     "consensus": "ALLOW",
#     "net_score": 3,
#     "votes": ["ALLOW", "ALLOW", "QUARANTINE", "ALLOW"],
#     "voter_ids": ["sheep-a1b2", "sheep-c3d4", "sheep-e5f6", "sheep-g7h8"],
#     "packed_bt": "BT(1101)",
# }
```

The packed balanced ternary representation `BT(1101)` encodes the entire vote in a single trit-word. This is not just compact -- it enables trit-level logic operations. You can AND two vote records together to find consensus, OR them to find any approval, or compute Shannon entropy to measure agreement.

## Byzantine Fault Tolerance

The fleet calculates its BFT tolerance dynamically:

```python
@property
def bft_tolerance(self) -> int:
    """Max Byzantine agents the flock can tolerate.
    BFT requires n >= 3f + 1, so f = (n - 1) // 3.
    """
    n = sum(1 for s in self.sheep.values()
            if s.state != SheepState.FROZEN)
    return max(0, (n - 1) // 3)
```

With 10 active agents, the fleet tolerates 3 malicious or faulty agents. With 4, it tolerates 1. The health dashboard reports this in real time:

```python
print(fleet.status_dashboard())
```

Output:
```
FLOCK STATUS
========================================
Total Agents: 10
  Active: 7  Idle: 1  Busy: 2
  Isolated: 0  Frozen: 0

Average Coherence: 0.847
Healthy: 8/10
BFT Tolerance: f=3

Tracks:
  system: 3 agents, coherence=0.890
  governance: 4 agents, coherence=0.825
  functions: 3 agents, coherence=0.830
```

## Sacred Tongue Affinity

Each agent role maps to one of six Sacred Tongues -- a tokenization language from SCBE's geometric trust model:

| Role | Tongue | Weight (phi-scaled) |
|------|--------|-------------------|
| LEADER | KO | 1.00 |
| VALIDATOR | AV | 1.62 |
| EXECUTOR | RU | 2.62 |
| OBSERVER | UM | 6.85 |

This is not cosmetic. The tongue affinity determines how an agent's governance decisions are weighted in the 6D trust space of the Poincare ball model. A VALIDATOR's vote carries more geometric weight than an EXECUTOR's, reflecting its specialization.

## Running It as a SaaS

The Flock Shepherd powers SCBE's SaaS API with three pricing tiers:

| Plan | Flocks | Agents | Monthly Governance Evals |
|------|--------|--------|------------------------|
| Starter | 1 | 8 | 5,000 |
| Growth | 5 | 40 | 25,000 |
| Enterprise | 25 | 250 | 100,000 |

The full API runs on FastAPI with Stripe billing integration. Try it:

```bash
pip install scbe-aethermoore
uvicorn src.api.main:app --reload --port 8000
# Visit http://localhost:8000/docs for Swagger UI
```

Source code: [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) -- see `src/symphonic_cipher/scbe_aethermoore/flock_shepherd.py` and `src/api/saas_routes.py`.
