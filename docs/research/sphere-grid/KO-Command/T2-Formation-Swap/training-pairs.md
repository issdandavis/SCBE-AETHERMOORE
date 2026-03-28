---
type: training-data
parent: "Formation Swap"
tongue: "KO"
format: "sft"
---

# Training Pairs: Formation Swap

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Code review found security issues | Swap builder for guardian, preserve context |
| Research hit dead end | Swap researcher for scout, hand off queries |

## How These Are Used

1. Agent fails at task requiring Formation Swap
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #KO