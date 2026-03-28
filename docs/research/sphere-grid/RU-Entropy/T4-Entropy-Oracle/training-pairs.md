---
type: training-data
parent: "Entropy Oracle"
tongue: "RU"
format: "sft"
---

# Training Pairs: Entropy Oracle

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Entropy spiking in layer 7 | Check OU params, alert if diverging |
| Predict next bottleneck | Analyze entropy trends across 14 layers |

## How These Are Used

1. Agent fails at task requiring Entropy Oracle
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #RU