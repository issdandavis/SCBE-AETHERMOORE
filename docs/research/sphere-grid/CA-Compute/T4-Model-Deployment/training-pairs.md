---
type: training-data
parent: "Model Deployment"
tongue: "CA"
format: "sft"
---

# Training Pairs: Model Deployment

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Deploy new tokenizer model | Canary to staging, monitor accuracy, promote |
| Rollback broken deployment | Identify regression, activate rollback |

## How These Are Used

1. Agent fails at task requiring Model Deployment
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #CA