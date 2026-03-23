---
type: pattern
parent: "Audit Trail"
tongue: "UM"
---

# Pattern: Audit Trail

> Immutable hash-chained governance-stamped records

## Core Approach

An agent at PARTIAL (0.30) executes this with degraded performance.
An agent at MASTERED (0.90+) executes optimally and can [[teach]] it.

## Key Concepts

- Hash chain construction
- Governance stamping
- Tamper detection

## Integration

- Uses [[UM-Security/UM-Domain|UM]] primitives
- Governed by [[governance-scan]] at every step
- Results feed into [[UM-Security/T3-Audit-Trail/training-pairs|training pairs]]

#sphere-grid #pattern #UM