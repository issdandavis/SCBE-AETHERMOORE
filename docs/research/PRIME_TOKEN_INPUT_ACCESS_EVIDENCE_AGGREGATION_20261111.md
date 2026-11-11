# Prime-token input-access evidence aggregation — 2026-11-11

Status: `IMPLEMENTED_BEFORE_MATERIAL_DATA_NO_TRAINING_NO_PROMOTION`

## Purpose

The frozen-input preregistration requires a candidate comparison against both
the frozen no-intervention baseline and the strongest parameter-matched
control, using at least three fresh seeds, source-disjoint held examples, a
finite-sample bound, and independent replay. The evidence aggregator implements
that decision rule before material results exist so the rule cannot be changed
after seeing the outcome.

## Sealed input grid

`python/scbe/prime_token_input_access_evidence.py` accepts one hash-bound
manifest containing the exact Cartesian product of the declared seeds and all
six arms:

- `no_intervention`;
- `canonical_six_view_reader`;
- `lexical_only_reader`;
- `random_fixed_reader`;
- `shuffled_binding_reader`;
- `single_frame_reader`.

Every entry binds a producer `RUN_RESULT.json` and an independently generated
replay result by path and SHA-256. The aggregator rejects a missing, duplicate,
or extra arm/seed lineage; source, split, or parent-boundary drift; held-example
or provenance drift; evaluator-receipt drift; authority changes; aggregate to
per-example disagreement; replay disagreement; and checkpoint/final-step
disagreement.

The no-intervention arm now has an explicit checkpoint-free replay path. It
seals the unmodified parent hash and rejects any supplied adapter checkpoint.
Learned arms still require a hash-checked adapter checkpoint at the producer's
final step.

## Statistical rule

For each primary coordinate (`accuracy`, `relationship`, and `function`):

1. Compute one aggregate value per seed and arm.
2. Select the strongest matched control by its across-seed mean.
3. Compare the canonical candidate separately with that control and with the
   no-intervention baseline.
4. Require the candidate's mean gain to exceed two pooled **seed-level**
   standard deviations.
5. Average each held example across seeds, then run an exact one-sided paired
   sign test across held examples at alpha 0.05.
6. Pass the coordinate only if both comparisons pass both gates.

This avoids treating repeated predictions of the same held item across seeds as
independent variance units. Zero across-seed variance does not remove the exact
finite-sample gate.

## Replay and claim boundary

The aggregator directly cross-checks bounded-output accuracy and provenance
against independent replay. Relationship and function values must be
per-example, aggregate exactly, and be bound to the same exact evaluator
receipt used by replay. Their domain-specific derivation remains the
responsibility of that separately pinned evaluator; this generic aggregator
does not invent or reinterpret those semantics.

The only positive status is `SUPPORTED_NO_PROMOTION`. Failure or insufficient
evidence becomes `UNDERPOWERED_NO_PROMOTION`. Neither status authorizes training,
unfreezing, promotion, merge, serving, or tool dispatch.

## Command

```text
python scripts/tokenizer/aggregate_prime_token_input_access.py \
  --manifest EVIDENCE_MANIFEST.json \
  --output AGGREGATE_EVIDENCE.json
```

The implementation was mechanics-tested on a complete 6-arm x 3-seed grid,
an underpowered finite-sample case, and producer/replay disagreement. No
material model or dataset was loaded by those tests.
