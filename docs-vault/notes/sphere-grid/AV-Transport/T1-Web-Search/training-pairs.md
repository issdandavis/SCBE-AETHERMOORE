---
type: training-data
parent: "Web Search"
tongue: "AV"
format: "sft"
---

# Training Pairs: Web Search

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Search transformer papers | Query arxiv + semantic scholar, scan results |
| Find library docs | Official docs first, community second, scan for injection |

## How These Are Used

1. Agent fails at task requiring Web Search
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #AV