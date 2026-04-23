---
type: training-data
parent: "Audit Trail"
tongue: "UM"
format: "sft"
---

# Training Pairs: Audit Trail

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Audit trail for deployment | Record every step, hash-chain all |
| Verify trail integrity | Walk hash chain, verify each record |

## How These Are Used

1. Agent fails at task requiring Audit Trail
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #UM