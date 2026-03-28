---
type: training-data
parent: "Fleet Transport"
tongue: "AV"
format: "sft"
---

# Training Pairs: Fleet Transport

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Ship training data to HuggingFace | Scan, seal with RU+CA, push via API |
| Sync agent state across fleet | Checkpoint, transport via bus, verify |

## How These Are Used

1. Agent fails at task requiring Fleet Transport
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #AV