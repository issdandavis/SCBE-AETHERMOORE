---
type: training-data
parent: "Task Dispatch"
tongue: "KO"
format: "sft"
---

# Training Pairs: Task Dispatch

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Route code review to right agent | Match to builder (CA), check activation >= 0.3 |
| Distribute 5 tasks across 3 agents | Load-balance by AP bank and activation coverage |

## How These Are Used

1. Agent fails at task requiring Task Dispatch
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #KO