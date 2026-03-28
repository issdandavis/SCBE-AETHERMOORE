---
type: skill-sphere
tongue: "KO"
tier: 1
name: "Task Dispatch"
cost: 8.0
phi: 0.00
---

# Task Dispatch

> Route tasks to appropriate agents

**Domain:** [[KO-Command/KO-Domain|KO (Command)]]
**Tier:** 1 | **Cost:** 8.0 AP | **Phi:** +0.00

## Inside This Sphere

- [[KO-Command/T1-Task-Dispatch/pattern|Core Pattern]] -- Match intent to capability, phi-weighted priority
- [[KO-Command/T1-Task-Dispatch/training-pairs|Training Pairs]] -- SFT data for this skill
- [[KO-Command/T1-Task-Dispatch/concepts|Key Concepts]] -- What to learn

## Activation

| Level | Range | Meaning |
|-------|-------|---------|
| DORMANT | 0.00-0.09 | Cannot use |
| LATENT | 0.10-0.29 | Aware, cannot invoke |
| **PARTIAL** | **0.30-0.59** | **Usable (degraded)** |
| CAPABLE | 0.60-0.89 | Fully functional |
| MASTERED | 0.90-1.00 | Peak, can teach |

## Connections

- **Prereq:** None (entry point)
- **Unlocks:** [[KO-Command/T2-Formation-Swap/_sphere|T2 Formation Swap]]
- [[adjacency-ripple]] bleeds growth to adjacent spheres
- [[computational-necessity]] can ACCELERATE this sphere

#sphere-grid #KO #tier-1