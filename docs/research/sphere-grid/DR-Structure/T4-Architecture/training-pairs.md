---
type: training-data
parent: "Architecture"
tongue: "DR"
format: "sft"
---

# Training Pairs: Architecture

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Design fleet comms | Sacred Tongue transport, governance scanning, audit |
| Architect training pipeline | Data funnel, gate, train, eval, deploy cycle |

## How These Are Used

1. Agent fails at task requiring Architecture
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #DR