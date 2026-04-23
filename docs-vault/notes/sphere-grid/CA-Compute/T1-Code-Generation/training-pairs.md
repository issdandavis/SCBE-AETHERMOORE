---
type: training-data
parent: "Code Generation"
tongue: "CA"
format: "sft"
---

# Training Pairs: Code Generation

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Implement Poincare distance | Write function with arcosh, add property test |
| Add Sacred Tongue to tokenizer | Follow existing pattern, update TONGUE_KEYS |

## How These Are Used

1. Agent fails at task requiring Code Generation
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #CA