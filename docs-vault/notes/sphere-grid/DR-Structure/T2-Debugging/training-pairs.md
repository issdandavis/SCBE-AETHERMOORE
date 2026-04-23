---
type: training-data
parent: "Debugging"
tongue: "DR"
format: "sft"
---

# Training Pairs: Debugging

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| AssertionError in tests | Read assertion, check expected vs actual, trace |
| Governance returning DENY | Check 9D vector, verify bounds, log path |

## How These Are Used

1. Agent fails at task requiring Debugging
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #DR