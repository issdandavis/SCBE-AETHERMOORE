---
type: training-data
parent: "Training Pipeline"
tongue: "CA"
format: "sft"
---

# Training Pairs: Training Pipeline

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Train on Sacred Tongue corpus | SFT from tokenizer data, LoRA, eval accuracy |
| Fine-tune governance classifier | ALLOW/DENY as labels, DPO training |

## How These Are Used

1. Agent fails at task requiring Training Pipeline
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #CA