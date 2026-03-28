---
type: training-data
parent: "Data Collection"
tongue: "RU"
format: "sft"
---

# Training Pairs: Data Collection

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Collect SCBE mentions in papers | Search arxiv/scholar, extract citations |
| Gather training from game logs | Parse Everweave logs, structure as SFT |

## How These Are Used

1. Agent fails at task requiring Data Collection
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #RU