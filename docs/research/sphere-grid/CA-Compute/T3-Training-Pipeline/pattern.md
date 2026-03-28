---
type: pattern
parent: "Training Pipeline"
tongue: "CA"
---

# Pattern: Training Pipeline

> Data prep, governance scan, train, eval, push to HF

## Core Approach

An agent at PARTIAL (0.30) executes this with degraded performance.
An agent at MASTERED (0.90+) executes optimally and can [[teach]] it.

## Key Concepts

- SFT/DPO/GRPO training
- Quality gate scanning
- HuggingFace integration

## Integration

- Uses [[CA-Compute/CA-Domain|CA]] primitives
- Governed by [[governance-scan]] at every step
- Results feed into [[CA-Compute/T3-Training-Pipeline/training-pairs|training pairs]]

#sphere-grid #pattern #CA