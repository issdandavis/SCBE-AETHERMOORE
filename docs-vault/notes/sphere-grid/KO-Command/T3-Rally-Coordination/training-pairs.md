---
type: training-data
parent: "Rally Coordination"
tongue: "KO"
format: "sft"
---

# Training Pairs: Rally Coordination

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
| Fleet behind on deadline | Rally all agents, 15% boost, focus bottleneck |
| Three agents coordinating | Rally + formation swap for max coherence |

## How These Are Used

1. Agent fails at task requiring Rally Coordination
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #KO