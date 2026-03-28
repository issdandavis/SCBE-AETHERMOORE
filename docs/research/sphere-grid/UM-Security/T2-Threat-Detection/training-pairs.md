---
type: training-data
parent: "Threat Detection"
tongue: "UM"
format: "sft"
---

# Training Pairs: Threat Detection

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Unusual API access pattern | Compare to immune memory, check credential stuffing |
| Agent behavior diverging | Compute drift distance, quarantine if threshold |

## How These Are Used

1. Agent fails at task requiring Threat Detection
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #UM