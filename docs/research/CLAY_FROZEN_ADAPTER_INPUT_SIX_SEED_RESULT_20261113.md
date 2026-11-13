# Clay frozen-adapter input access: six-seed result — 2026-11-13

## Outcome

Two preregistered three-seed campaigns now have independent, read-only
inference replays.  Across all six seeds, a frozen-core adapter that received
the actual input reached `0.03485` mean coding accuracy.  The same-size learned
null adapter remained at `0.00000`, and the no-intervention parent reached
`0.00076`.  Counting behavior was reproduced exactly for every adapter and
seed, and the frozen parent tensors remained bit-identical.

This is evidence that input access can add a narrow skill without dislodging
the measured parent behavior.  It is not evidence of a capable coding model:
absolute coding accuracy is only about 3.5%.  Neither campaign authorizes
promotion, deployment, execution authority, deletion, or partial unfreezing.

## Six-seed market

| Arm | Coding scores | Mean | Sample SD |
| --- | --- | ---: | ---: |
| frozen adapter with input | .03182, .05455, .01364, .04091, .03182, .03636 | 0.03485 | 0.01338 |
| equal-size learned null | .00000, .00000, .00000, .00000, .00000, .00000 | 0.00000 | 0.00000 |
| no intervention | .00000, .00000, .00000, .00000, .00455, .00000 | 0.00076 | 0.00186 |

| Comparison | Mean delta | 2 x pooled seed SD | Paired wins/losses | Exact two-sided p |
| --- | ---: | ---: | ---: | ---: |
| input adapter vs no intervention | +0.03409 | 0.01911 | 46 / 1 | 6.82e-13 |
| input adapter vs learned null | +0.03485 | 0.01892 | 46 / 0 | 2.84e-14 |

The six-seed row is a transparent aggregation of two locked three-seed
campaigns, not a newly preregistered selection gate.  Each constituent campaign
independently cleared its registered dispersion and finite-uncertainty checks.

## What the learner actually saw

The training stream is a deterministic shuffled cycle, not an unmeasured claim
that a large corpus was present.

- Parent counting bank: 306 unique training rows, batch 128, 28,000 steps.
  That is 9,333 complete passes plus one 128-row batch, or 2,856,026 example
  presentations.  Each row appears 9,333 or 9,334 times per parent horse.
- Adapter coding bank: 1,314 unique add/subtract/multiply rows, batch 128,
  18,000 steps.  That is 1,636 complete passes plus four 128-row batches, or
  2,150,216 example presentations.  Each row appears 1,636 or 1,637 times per
  trained adapter horse.
- The candidate and learned-null arms have the same trainable parameter count,
  target stream, step budget, and exposure depth.  The intervention is whether
  the adapter receives real token input or a constant null input.

This isolates an important data rule.  Repetition can accumulate a gradient
over support that the model can observe, but it cannot create missing support
or bypass an information barrier.  The separate paired-orbit experiments show
the complementary result: wider valid geometry-view coverage beat deeper exact
repetition.  A future image/audio lane therefore needs receipts for unique
concepts, views per concept, presentations per view, and held-out source/view
families rather than one undifferentiated epoch count.

## Independent replay receipts

First three seeds (`20261119`, `20261120`, `20261122`):

- Producer result: `462f6c7c81a821aa8e924596ffe18ef9d293705da229232ee7989922d85212bf`
- Replay result: `39418fc22b247ad57f3ba2effb3b553dd4d6d82043edcbe863852ee3b418f8bd`
- Prediction ledger: `a27edc24600a49399be27b8f15a70938c17778aef6134917d8f52ac7248a4153`
- Ledger rows: 2,466

Continuation seeds (`20261123`, `20261124`, `20261125`):

- Producer result: `56dc23f4cafc81ab0113f021663a386ada24a2cb212087458ccb4bc206e91c4a`
- Replay result: `ba0a97c6e678dc5d9c406a6da146c78c3cd32da1f5e06091a8807c3b80cf054b`
- Prediction ledger: `e373e3c645dd12a5886b7dce2a7665eb59928fa85c906f7b6127e6a3fa011b5a`
- Ledger rows: 2,466

Both replays independently reconstructed all four data-split hashes, derived
the 92,763 trainable parameters, verified checkpoint lineage, reproduced every
prediction and metric, and found every frozen core bit-identical.  Their common
status is `PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION`; partial unfreeze is
`NONE`.

## Next controlled question

Do not spend more blind epochs on this 1,314-row table.  The next material test
must increase source-disjoint concept and operation coverage while preserving
the same input-visible candidate, learned-null, and no-intervention controls.
Log exposure as a tensor with at least
`concept x operation x view x source-family x presentation-count`, then relate
that ledger to per-region gradient and error saturation.  This tests the user's
"build gradients across a concept" hypothesis without confusing repeated
examples with new information.
