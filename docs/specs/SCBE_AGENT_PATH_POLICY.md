# SCBE Agent Path Policy: Non-Optimal Correct Path Finding

## Definition

Non-optimal correct path finding is an agentic execution strategy where the system prioritizes verified forward progress over optimality. A move is accepted if it is legal, safe, reversible or bounded, and improves or preserves task state, even if it is not the shortest or most elegant solution.

## Motivation

Small models fail when forced to be elegant. They succeed when allowed to take stairs.

An agent demanding the best solution will get stuck in planning loops, repeat failures while hoping for a better outcome, or emit a confident-but-unverified `<done>` signal.

An agent allowed to find any valid path will complete more tasks, leave verifiable evidence, and create a map of what failed — which is itself useful state.

## Mechanical Rules

1. A move can be ugly but must be legal.
2. A patch can be small and boring if tests pass.
3. A workaround can be accepted if it is documented and bounded.
4. A failed move is allowed if it produces useful information.
5. Repeating the same failed move is not allowed (ko-ban).
6. Completion requires verification, not model confidence.
7. Optimization happens after correctness.

## Move Acceptance Table

| Move Type              | Accepted? | Why                |
|------------------------|-----------|--------------------|
| Fast and correct       | yes       | best case          |
| Slow and correct       | yes       | still progress     |
| Ugly but verified      | yes       | can refine later   |
| Failed but informative | yes       | improves map       |
| Failed and repeated    | no        | loop (ko-ban)      |
| Elegant but unverified | no        | fake completion    |
| Risky and irreversible | no        | bad move           |

## Scoring Priority

When evaluating task execution, scores are applied in this order:

1. **Correctness** — does the verifier pass?
2. **Safety** — was the move legal and governed?
3. **Reversibility** — was the move bounded and recoverable?
4. **Efficiency** — how many turns did it take?
5. **Elegance** — last. Irrelevant until the above four are satisfied.

## Task Board Representation

The policy is carried in the task board object as a machine-readable contract:

```json
{
  "path_policy": "non_optimal_correct",
  "acceptance": {
    "must_be_safe": true,
    "must_be_verifiable": true,
    "must_not_repeat_failed_state": true,
    "optimality_required": false
  }
}
```

This gives small models explicit permission to succeed imperfectly while preventing the dangerous and the dishonest.

## Relation to Board Mechanics

- **Ko-ban** enforces rule 5: repeated failed state is blocked, not just rationale-warned.
- **`done_if` verifier** enforces rule 6: `<done>` from the model is a request for verification, not a completion signal.
- **`attempts` log** makes failed-but-informative moves visible to the model in the next turn.
- **`legal_moves`** enforces rule 1: the board defines what moves exist.

## Relation to SCBE Governance

Non-optimal correct path finding is consistent with SCBE's L13 risk tier model:

- ALLOW: legal, safe, bounded move → accepted even if ugly
- QUARANTINE: ko-banned or suspicious → blocked and logged
- DENY: destructive, irreversible, or governance-blocked → hard stop

The path policy does not relax governance. It relaxes quality requirements on moves that governance already allows.
