# Neurogolf D8 Voting Proposal

Status: proposal only. Neurogolf is treated as a parallel-owned lane, so this note captures the implementation shape without editing `src/neurogolf`.

## Why This Exists

The latest golf/putter work found a real verifier weakness: MBPP library grafts could pass cherry-picked asserts while being semantically wrong. The corrected rule is the right one:

- search on one oracle surface
- accept only on a held-back oracle surface
- classify overfit and weak-oracle suspects instead of counting them as solves

For ARC-style grid tasks, Neurogolf already has the stronger invariant: exact reproduction of every training pair before a candidate can be trusted. D8 and color-permutation voting should preserve that invariant. The voting layer should make the solver less brittle, not looser.

## Proposed Mechanism

Wrap `synthesize_program` with a transform-vote layer:

1. Build transformed copies of the task.
2. Run the existing Neurogolf synthesis unchanged on each transformed task.
3. Invert the transform on each candidate prediction.
4. Re-run the exact train verifier in the original task frame.
5. Keep only candidates that reproduce all train outputs exactly.
6. Return the passing candidate with the lowest cost, using deterministic tie-breaks.

The proctor must never inspect the hidden answer. It can inspect only train inputs, train outputs, candidate execution, exact-match status, cost, and receipts.

## D8 Transform Set

Use the square dihedral group:

- identity
- rotate 90
- rotate 180
- rotate 270
- flip horizontal
- flip vertical
- transpose main diagonal
- transpose anti-diagonal

Rectangular grids need explicit handling because 90-degree rotations and diagonal transposes swap width and height. They are valid only when every transformed train and test grid remains a legal ARC grid and the inverse transform is unambiguous.

## Color-Permutation Voting

Color voting should be conservative:

- preserve background `0` by default
- canonicalize seen colors from train pairs
- apply candidate color renamings consistently across inputs and outputs
- invert the color transform before original-frame verification
- allow nonzero color permutations only when the transformed train pairs remain internally consistent

This is useful because many ARC rules are color-agnostic but solver paths can still overfit to concrete color ids.

## Cost And Tie Rules

If multiple candidates pass exact train verification:

1. choose the lowest Neurogolf cost
2. then the shortest IR/program representation
3. then a stable transform order
4. then a stable candidate id

This keeps the scorecard reproducible.

## Ensemble With Putter/Golf

The combined jurisdiction should work like this:

- `putter`: proposes code analogies or small-basis transforms
- `driver`: proposes Neurogolf ARC/grid programs
- `model`: may propose, but failures are recorded rather than hidden
- `proctor`: verifies execution/exact train match and seals the receipt

If both putter and driver pass their relevant verifier, accept the lowest-cost verified candidate. Do not credit the model for a club's deterministic solve. Do not call a weak-oracle pass genuine.

## Required Tests

Add focused tests before landing implementation:

- D8 recovery: a task missed in the original orientation but solved under a rotated/flipped view.
- Inversion: transformed candidate output maps back to the exact original-frame output.
- Color permutation: a color-renamed task solves while preserving background `0`.
- Rectangular grids: rotations/transposes either work correctly or are rejected explicitly.
- No false accept: a transformed candidate that fails any train pair is rejected.
- Determinism: two passing candidates choose the same winner on repeated runs.
- Receipt attribution: scorecard credits the club and transform, not an unverified model guess.

## Non-Goals

- No test-time gradient training. TTT-style methods are outside the tiny/static solver budget.
- No weakening of exact-train verification.
- No answer-driven steering.
- No claim of "genuine" capability from public-only or cherry-picked tests.

## Summary

D8 and color-permutation voting are the cheap ARC-winner lessons worth stealing. The core discipline remains unchanged: generate broadly, verify strictly, report honestly.
