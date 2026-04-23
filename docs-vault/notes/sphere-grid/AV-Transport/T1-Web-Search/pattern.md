---
type: pattern
parent: "Web Search"
tongue: "AV"
---

# Pattern: Web Search

> Every search result governance-scanned before return

## Core Approach

An agent at PARTIAL (0.30) executes this with degraded performance.
An agent at MASTERED (0.90+) executes optimally and can [[teach]] it.

## Key Concepts

- Governed search pipeline
- Source ranking
- Injection detection

## Integration

- Uses [[AV-Transport/AV-Domain|AV]] primitives
- Governed by [[governance-scan]] at every step
- Results feed into [[AV-Transport/T1-Web-Search/training-pairs|training pairs]]

#sphere-grid #pattern #AV