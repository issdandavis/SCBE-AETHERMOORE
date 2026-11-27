# Six-view masked-byte routing benchmark

**Status:** dataset/evaluator contract implemented; no model-quality result is claimed yet.
**Question:** do six reversible byte views improve reconstruction, and does
adaptive candidate routing add a gain beyond the representation alone?

**Runtime:** `src/tokenizer/masked_byte_benchmark.py`
**Tests:** `tests/tokenizer/test_masked_byte_benchmark.py`

The runtime generates split-bound deterministic structured cases, validates
per-step work receipts, rejects hidden budget or parameter mismatches, computes
exact recovery and target NLL from normalized 256-byte candidate distributions,
checks that committed bytes are distribution argmaxes, and reports `B - A`
separately from `C - B`.
Model training and the first three-seed run remain open work.

## Three arms

| Arm | State representation | Refinement schedule |
|---|---|---|
| A: byte baseline | One ordinary 0-255 byte ID | Fixed schedule |
| B: six-view control | The same byte exposed through all six Sacred Tongue bijections | The same fixed schedule and candidate budget as C |
| C: adaptive route | The same six views as B | Select the next unresolved position from the model's candidate distributions using the declared routing score |

The six views are reversible labels of one byte. They add no source entropy and
must not be counted as six independent observations.

## Dataset

Use deterministic structured byte sequences with disjoint train, validation and
test generators. Start with bounded records such as length-prefixed fields,
small JSON objects, checksummed packets and repeated nested delimiters. Reserve
entire generator seeds and templates for the held-out test set so exact recovery
cannot be achieved by memorizing records.

Mask the same positions for all three arms. Report separate buckets for random
single-byte masks, contiguous spans and structure-bearing bytes such as lengths,
delimiters and checksums.

## Matched controls

- Same train/validation/test examples and mask schedule.
- Same trainable parameter count, within one percent.
- Same optimizer, update count and random seeds.
- Same maximum candidate evaluations and refinement steps for B and C.
- A size-matched byte-only control in addition to the ordinary baseline.
- At least three seeds. Report the pooled standard deviation and call a result
  **UNDERPOWERED** unless the gain exceeds twice that value.
- A claimed win must beat both the size-matched control and the no-intervention
  byte baseline.

Wall-clock time is diagnostic because kernels differ. Candidate evaluations,
model forward passes and estimated multiply-accumulates are the primary compute
budget.

## Required measurements

1. Exact byte recovery over the full masked region.
2. Per-byte negative log likelihood or calibrated candidate loss.
3. Work-to-recovery: candidate evaluations and forward passes required to reach
   exact recovery.
4. Unresolved positions after each refinement step.
5. Failure buckets by mask type and sequence structure.
6. Model parameters, peak memory, training updates and inference compute.

Report representation gain as `B - A` and routing gain as `C - B`. Do not
attribute `C - A` entirely to routing.

## Routing contract

An unresolved token is a candidate distribution over bytes, not a seventh
alphabet. A routing decision must record:

```json
{
  "step": 0,
  "position": 12,
  "score": 0.73,
  "candidate_evaluations": 1,
  "reason": "highest declared uncertainty reduction"
}
```

The router may use entropy, expected uncertainty reduction or a pre-registered
weighted score. It may not inspect the hidden target, spend an unreported extra
forward pass, or bill several candidate evaluations as one. The evaluator must
recompute the work count from the trace.

## Interpretation boundary

- A B-over-A result supports the representation under the tested model and
  compute budget.
- A C-over-B result supports the routing rule under the tested budget.
- A tie is useful: it shows that reversible relabeling alone did not add signal.
- None of the arms establishes a cryptographic, patent-scope or general language
  modeling claim.

Related comparison points are D3PM structured transition matrices
(`arXiv:2107.03006`) and latent predictions over undecoded positions
(`arXiv:2602.03769`). ClassDiffusion (`arXiv:2405.17532`) concerns
image-personalization semantic preservation and is not the direct routing
baseline for this byte experiment.
