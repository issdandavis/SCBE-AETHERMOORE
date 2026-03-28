---
type: training-data
parent: "Hypothesis Generation"
tongue: "RU"
format: "sft"
---

# Training Pairs: Hypothesis Generation

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Attention clusters at phi=0.5 | Hypothesis: resonance point in phase tunnel |
| Loss plateaus at epoch 50 | Hypothesis: LR schedule needs warmup |

## How These Are Used

1. Agent fails at task requiring Hypothesis Generation
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #RU