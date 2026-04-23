---
type: training-data
parent: "Seal Enforcement"
tongue: "UM"
format: "sft"
---

# Training Pairs: Seal Enforcement

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Seal governance decision | KDF from tongue seed, encrypt, cross-thread, anchor |
| Verify sealed artifact | Decode AEAD, verify threading, check chain |

## How These Are Used

1. Agent fails at task requiring Seal Enforcement
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #UM