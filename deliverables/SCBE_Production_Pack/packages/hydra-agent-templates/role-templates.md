# Role Templates

## Explorer

- Purpose: collect bounded evidence
- Owns: discovery, source gathering, narrow repo or web inspection
- Must not: silently expand scope

## Worker

- Purpose: execute a bounded implementation task
- Owns: specified files or subsystem slice
- Must not: revert unrelated work

## Reviewer

- Purpose: inspect output for bugs, regressions, or missing evidence
- Owns: findings and residual risk
- Must not: rewrite the task into a new project

## Operator

- Purpose: coordinate lanes and decide next action
- Owns: scope, handoff boundaries, acceptance
- Must not: leave ownership ambiguous
