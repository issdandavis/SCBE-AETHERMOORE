---
type: pattern
parent: "Navigation"
tongue: "AV"
---

# Pattern: Navigation

> SENSE-PLAN-STEER-DECIDE loop

## Core Approach

An agent at PARTIAL (0.30) executes this with degraded performance.
An agent at MASTERED (0.90+) executes optimally and can [[teach]] it.

## Key Concepts

- State machine navigation
- Backtracking on failure
- Session persistence

## Integration

- Uses [[AV-Transport/AV-Domain|AV]] primitives
- Governed by [[governance-scan]] at every step
- Results feed into [[AV-Transport/T2-Navigation/training-pairs|training pairs]]

#sphere-grid #pattern #AV