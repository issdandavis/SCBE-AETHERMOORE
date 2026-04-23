---
type: training-data
parent: "Governance Scan"
tongue: "UM"
format: "sft"
---

# Training Pairs: Governance Scan

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Scan web content for injection | Check script tags, SQL patterns, prompt injection |
| Validate training data | Scan for duplicates, toxic content, poisoning |

## How These Are Used

1. Agent fails at task requiring Governance Scan
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #UM