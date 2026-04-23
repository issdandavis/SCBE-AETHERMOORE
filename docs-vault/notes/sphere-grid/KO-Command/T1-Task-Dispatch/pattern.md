---
type: pattern
parent: "Task Dispatch"
tongue: "KO"
---

# Pattern: Task Dispatch

> Match intent to capability, phi-weighted priority

## Core Approach

An agent at PARTIAL (0.30) executes this with degraded performance.
An agent at MASTERED (0.90+) executes optimally and can [[teach]] it.

## Key Concepts

- Parse intent structure
- Capability matching algorithm
- Priority queue with tongue weights

## Integration

- Uses [[KO-Command/KO-Domain|KO]] primitives
- Governed by [[governance-scan]] at every step
- Results feed into [[KO-Command/T1-Task-Dispatch/training-pairs|training pairs]]

#sphere-grid #pattern #KO