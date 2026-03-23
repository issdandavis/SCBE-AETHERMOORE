---
type: training-data
parent: "Test Writing"
tongue: "CA"
format: "sft"
---

# Training Pairs: Test Writing

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Test governance gate | L2: unit verdicts, L4: random 9D vectors, L5: bypass |
| Test fleet transport | L3: end-to-end delivery, L6: payload injection |

## How These Are Used

1. Agent fails at task requiring Test Writing
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #CA