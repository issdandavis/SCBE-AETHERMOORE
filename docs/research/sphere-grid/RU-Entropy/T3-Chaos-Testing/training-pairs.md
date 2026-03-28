---
type: training-data
parent: "Chaos Testing"
tongue: "RU"
format: "sft"
---

# Training Pairs: Chaos Testing

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Chaos test governance gate | Inject malformed 9D vectors, verify DENY |
| Stress test fleet transport | Simultaneous sends, verify no data loss |

## How These Are Used

1. Agent fails at task requiring Chaos Testing
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #RU