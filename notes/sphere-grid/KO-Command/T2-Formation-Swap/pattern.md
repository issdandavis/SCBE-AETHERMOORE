---
type: pattern
parent: "Formation Swap"
tongue: "KO"
---

# Pattern: Formation Swap

> Checkpoint-swap-restore for zero-downtime rotation

## Core Approach

An agent at PARTIAL (0.30) executes this with degraded performance.
An agent at MASTERED (0.90+) executes optimally and can [[teach]] it.

## Key Concepts

- State checkpointing
- Role reassignment protocol
- Zero-downtime rotation

## Integration

- Uses [[KO-Command/KO-Domain|KO]] primitives
- Governed by [[governance-scan]] at every step
- Results feed into [[KO-Command/T2-Formation-Swap/training-pairs|training pairs]]

#sphere-grid #pattern #KO