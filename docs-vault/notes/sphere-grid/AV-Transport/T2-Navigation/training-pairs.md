---
type: training-data
parent: "Navigation"
tongue: "AV"
format: "sft"
---

# Training Pairs: Navigation

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Navigate to settings page | SENSE structure, PLAN clicks, STEER, DECIDE |
| Multi-step form fill | Track state across pages, validate before submit |

## How These Are Used

1. Agent fails at task requiring Navigation
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #AV