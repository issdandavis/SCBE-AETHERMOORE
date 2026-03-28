---
type: training-data
parent: "Documentation"
tongue: "DR"
format: "sft"
---

# Training Pairs: Documentation

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Document sphere grid API | Overview, reference, examples, gotchas |
| Write agent onboarding | Archetype selection, AP system, first unlock |

## How These Are Used

1. Agent fails at task requiring Documentation
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #DR