# Clay shuffled-factor confirmation result — 2026-11-13

## Outcome

The shuffled-factor selector replicated its directional lead on fresh data and
model seeds, but it did not clear the preregistered sector/control gate.  The
verdict is `NO_SELECTION`.  No checkpoint is promoted, no layer is partially
unfrozen, and no execution authority changes.

Run:
`C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-shuffled-confirm-v1`

- Result: `1f636d08d7392bce2f3607da04208ff6de68fcfdb8d7d29a12afeb0f70ad843f`
- Stratified gate:
  `94b353e73f75906a9ea570bf0afdae549f68b0bde14fa6732797ba0355d126e5`
- Exact exposure audit:
  `096a9ffd63464901d2d81218b55b8da4f0efa60b19bd553afde6912e143899c9`
- Exposure-audit file:
  `a320e1e4170f792a0935d8256c54102b98d3ccab5b8145d870cfae9d545635fb`

## Global market

| Data arm | Held accuracy | Stable F1 | Worst stable | Anchor accuracy | Gradient cosine | Weight drift |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static unique | 0.8312 | 0.7065 | 0.4153 | 0.9810 | 0.2242 | 13.7794 |
| random multi-view | 0.8627 | 0.7283 | 0.4202 | 0.9798 | 0.3643 | 14.2608 |
| semantic factor | 0.8707 | 0.7339 | 0.4778 | 0.9585 | 0.4848 | 12.3427 |
| shuffled factor | **0.8974** | **0.7556** | **0.4984** | 0.9801 | 0.4909 | 12.5929 |

Every arm used the same 6,917-parameter standard MLP, 30,000 training rows,
4,800 optimizer steps, five new model seeds, three held sectors, and 10,000-row
held and anchor banks.  All 60 horses changed every learned scalar.

The directional replication is real but narrower than a pass.  Shuffled factor
beat static unique in all 15 matched accuracy and stable-F1 pairs, random
multi-view in 11/15 pairs for each metric, and semantic factor in 13/15 pairs.
The registered gate also requires positive deltas in every sector and margins
above `max(2 x pooled seed SD, 0.02)` in at least two sectors against every
control.

## Sector gate

| Control | Sector | Accuracy delta / required | Stable-F1 delta / required | Anchor retained |
| --- | ---: | ---: | ---: | :---: |
| semantic factor | 1 | +0.0645 / 0.0817 | +0.0512 / 0.0636 | yes |
| semantic factor | 4 | +0.0028 / 0.0200 | +0.0023 / 0.0200 | yes |
| semantic factor | 7 | +0.0128 / 0.0522 | +0.0115 / 0.0414 | yes |
| random multi-view | 1 | +0.0713 / 0.0649 | +0.0571 / 0.0511 | yes |
| random multi-view | 4 | +0.0001 / 0.0200 | -0.0020 / 0.0200 | yes |
| random multi-view | 7 | +0.0325 / 0.0861 | +0.0267 / 0.0696 | yes |
| static unique | 1 | +0.0758 / 0.0587 | +0.0605 / 0.0430 | yes |
| static unique | 4 | +0.0249 / 0.0200 | +0.0078 / 0.0200 | yes |
| static unique | 7 | +0.0979 / 0.0981 | +0.0790 / 0.0796 | yes |

Against static data, sector 7 missed its noise floor by only `0.00020` accuracy
and `0.00058` stable F1, but a near miss is still a miss.  More importantly,
sector 4 stable F1 was slightly below random multi-view, and no sector cleared
the semantic-factor variance threshold.  Pooling these sectors into one global
mean would hide those failures.

## Data and receipt audit

The independent v2 exposure audit used no outcome values to reconstruct the
schedule.  It verified all 60 completed horse lineages, all input-bank
manifests, and 15 deterministic CPU sampling streams.  Each horse received
exactly 921,600 row presentations.  Every 30,000-row position was seen; counts
ranged from 9 to 60 with median 31.  The full per-row count vectors and their
hashes are retained in `EXPOSURE_AUDIT_V2.json`.

An independent outcome pass also verified:

- 60/60 horse receipts;
- 180/180 initial, best, and final checkpoint state hashes;
- 15/15 matched initialization groups;
- 3/3 selection receipts with zero selected-index and exact-feature overlap;
- exact recomputation of every sector delta, variance threshold, retention
  check, gate field, result receipt, and gate receipt.

## Interpretation

The repeated global lead supports keeping shuffled spread as a research data
primitive.  It does not show that shuffled factor signatures are uniquely
useful.  The selector may simply be acting as a deterministic hash/spread over
the candidate pool.  The next controlled run should compare it directly with a
factor-free deterministic hash-signature selector on fresh rows and seeds,
while retaining random multi-view and static controls.  That is a mechanism
test, not a post-hoc power extension of this failed gate.
