---
type: pattern
parent: "Site Mapping"
tongue: "AV"
---

# Pattern: Site Mapping

> BFS crawl with governance scanning per page

## Core Approach

An agent at PARTIAL (0.30) executes this with degraded performance.
An agent at MASTERED (0.90+) executes optimally and can [[teach]] it.

## Key Concepts

- BFS/DFS crawl strategies
- Content extraction
- Link graph analysis

## Integration

- Uses [[AV-Transport/AV-Domain|AV]] primitives
- Governed by [[governance-scan]] at every step
- Results feed into [[AV-Transport/T3-Site-Mapping/training-pairs|training pairs]]

#sphere-grid #pattern #AV