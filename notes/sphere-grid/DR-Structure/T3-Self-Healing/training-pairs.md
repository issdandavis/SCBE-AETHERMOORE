---
type: training-data
parent: "Self Healing"
tongue: "DR"
format: "sft"
---

# Training Pairs: Self Healing

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Agent crashed mid-task | Restore from checkpoint, retry, log recovery |
| Memory pressure warning | Compact L0, archive L1 to L2, continue |

## How These Are Used

1. Agent fails at task requiring Self Healing
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #DR