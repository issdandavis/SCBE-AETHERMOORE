---
type: pattern
parent: "Hypothesis Generation"
tongue: "RU"
---

# Pattern: Hypothesis Generation

> Turn observations into ranked testable hypotheses

## Core Approach

An agent at PARTIAL (0.30) executes this with degraded performance.
An agent at MASTERED (0.90+) executes optimally and can [[teach]] it.

## Key Concepts

- Knowledge gap detection
- Prior probability estimation
- Testability ranking

## Integration

- Uses [[RU-Entropy/RU-Domain|RU]] primitives
- Governed by [[governance-scan]] at every step
- Results feed into [[RU-Entropy/T1-Hypothesis-Generation/training-pairs|training pairs]]

#sphere-grid #pattern #RU