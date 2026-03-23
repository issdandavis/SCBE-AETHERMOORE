---
type: training-data
parent: "Sovereign Command"
tongue: "KO"
format: "sft"
---

# Training Pairs: Sovereign Command

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Full codebase refactor | Scout maps, builder refactors, guardian audits, teacher docs |
| Production incident | Healer diagnoses, builder patches, guardian monitors |

## How These Are Used

1. Agent fails at task requiring Sovereign Command
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #KO