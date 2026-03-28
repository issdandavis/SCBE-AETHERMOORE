---
type: training-data
parent: "Site Mapping"
tongue: "AV"
format: "sft"
---

# Training Pairs: Site Mapping

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Map documentation site | BFS from root, extract API docs, build graph |
| Inventory blog posts | Map /blog path, extract metadata, return catalog |

## How These Are Used

1. Agent fails at task requiring Site Mapping
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #AV