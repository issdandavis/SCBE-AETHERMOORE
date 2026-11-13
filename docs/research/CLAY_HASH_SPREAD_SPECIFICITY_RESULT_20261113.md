# Clay hash-spread specificity result — 2026-11-13

## Outcome

The factor-specificity hypothesis did not pass.  Shuffled-factor selection and
equal-width deterministic hash spreading were effectively tied, while ordinary
random multi-view sampling led the global market.  The preregistered verdict is
`NO_SELECTION`.  No checkpoint is promoted, no layer is partially unfrozen,
and no execution authority changes.

Run:
`C:\dev\clay-training-runs\paired-orbit-data-20261113\multiview-hash-specificity-v1`

- Campaign: `1c4e47d38453b781fe1a1f35df0478a07cf2426470bea96f70084a88c48a6518`.
- Result: `0deb8e9b96a09f42f527b7ff72c1bfaf39b3ecc712f3e227f2853265975c29e8`.
- Gate: `5e8664cb324accd4ddf11dac35c3ba21ecf1ca53dc80b8da1c0cff2d7b499b87`.
- Independent result audit:
  `4ee18b6a1a8bfc665534ee3fb4e546d65f7aa357b4c71bd6253d2f271e87f7cf`.
- Exact exposure audit:
  `f0701502dc50be7261d336fb6c7b5085e3a02cd400acdea189c8a8226e68fd65`.

## Global market

| Data arm | Held accuracy | Stable F1 | Worst stable | Cross entropy | Anchor accuracy | Gradient cosine | Weight drift |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| static unique | 0.8302 | 0.7064 | 0.4051 | 0.5532 | **0.9814** | 0.0040 | 13.8676 |
| random multi-view | **0.9035** | **0.7696** | **0.5208** | **0.2837** | 0.9793 | **0.2840** | **14.5786** |
| shuffled factor | 0.8812 | 0.7528 | 0.4728 | 0.3328 | 0.9803 | 0.1416 | 13.1447 |
| deterministic hash spread | 0.8819 | 0.7522 | 0.4711 | 0.3329 | 0.9798 | 0.1362 | 13.4558 |

All arms used the same 6,917-parameter MLP, 30,000 rows per fold, 4,800
optimizer steps, five initializations, three held sectors, and exact exposure
schedules.  All 60 horses changed all 6,917 learned scalars.

## Sector market

| Held sector | Arm | Accuracy | Stable F1 | Worst stable |
| ---: | --- | ---: | ---: | ---: |
| 1 | static | 0.8006 | 0.8380 | 0.6818 |
| 1 | random | **0.8677** | **0.8927** | **0.7846** |
| 1 | shuffled | 0.8097 | 0.8474 | 0.6571 |
| 1 | hash | 0.8150 | 0.8529 | 0.6518 |
| 4 | static | 0.9626 | 0.4976 | 0.0000 |
| 4 | random | **0.9882** | **0.5339** | 0.0277 |
| 4 | shuffled | 0.9880 | 0.5335 | 0.0275 |
| 4 | hash | 0.9877 | 0.5286 | **0.0300** |
| 7 | static | 0.7275 | 0.7837 | 0.5337 |
| 7 | random | **0.8547** | **0.8822** | **0.7501** |
| 7 | shuffled | 0.8459 | 0.8775 | 0.7339 |
| 7 | hash | 0.8431 | 0.8752 | 0.7314 |

Sector 4 is the warning against trusting headline accuracy.  Every multi-view
arm reached roughly 0.988 accuracy, but worst-stable-class accuracy remained
only 0.028--0.030.  The aggregate score hides a minority-action bottleneck.

## Matched comparisons

| Comparison | Accuracy delta | Acc wins | Stable-F1 delta | F1 wins | Worst-stable delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| shuffled - hash | -0.00076 | 8/15 | +0.00053 | 9/15 | +0.00177 |
| shuffled - random | -0.02235 | 6/15 | -0.01681 | 8/15 | -0.04797 |
| shuffled - static | +0.05092 | 12/15 | +0.04635 | 13/15 | +0.06770 |
| random - hash | +0.02159 | 12/15 | +0.01735 | 13/15 | +0.04974 |
| random - static | **+0.07327** | **15/15** | **+0.06316** | **15/15** | **+0.11567** |

The shuffled and hash selectors are indistinguishable at this power.  That
refutes the claim that the shuffled-factor advantage was specific to those
factor cells.  The robust observation is instead that valid multi-view support
beats the single canonical sheet.  Random multi-view won every matched
accuracy and stable-F1 comparison against static data, but it was a control,
not the preregistered primary, so this run cannot promote it.

## What happened in the weights and outputs

Random multi-view produced the largest mean weight displacement (14.5786),
the highest cross-view gradient cosine (0.2840), and the latest mean selected
checkpoint (step 4,293).  Its mean layer delta norms were 9.294 for the input
matrix, 10.559 for the hidden matrix, and 3.715 for the output matrix.  The
corresponding shuffled values were 8.364, 9.537, and 3.322; hash values were
8.570, 9.752, and 3.416.  The stronger movement was paid for with useful
transfer rather than anchor collapse.

At the output, random sampling traded some action-4 recall for action-3 recall:

| Arm | Action-1 recall | Action-2 | Action-3 | Action-4 |
| --- | ---: | ---: | ---: | ---: |
| static | 0.604 | 0.969 | 0.798 | 0.865 |
| random | 0.830 | 0.999 | **0.843** | 0.813 |
| shuffled | 0.809 | 0.999 | 0.668 | **0.917** |
| hash | **0.835** | 0.999 | 0.645 | 0.896 |

That better action-3 support explains much of random's higher stable F1 and
worst-class score.  Static data also produced 39.7 predictions per horse into
classes absent from a held split, versus 1.13 for random, 1.73 for shuffled,
and 2.27 for hash.

## Data exposure and causal interpretation

The source-pinned auditor reconstructed all 15 sampling streams without using
model outcomes.  Every horse drew exactly 921,600 rows.  Every 30,000-row
position was seen, with counts from 8 to 58 and median 31; minimum entropy
evenness was 0.99839.  Repetition was therefore matched.  The result depends on
which concept-orbit rows were repeated, not on one arm simply receiving more
updates.

The hash selector was a real intervention: conditional hash entropy was about
0.999987 in every fold versus roughly 0.9979 for random and shuffled.  It did
not improve learning.  Flattening a surrogate cell table appears to disturb
useful natural co-occurrence without adding information.  Random multi-view
sampling retained broader valid view variation and slightly better true-factor
coverage in two of three folds.

This supports the user's data principle in a narrower, measured form:
repeated exposure builds a concept only when the repeated views preserve useful
relations.  More even coverage of an arbitrary coordinate system is not the
same as a better concept gradient.

## Independent verification

The independent verifier imports neither the producer nor its gate.  It
verified 24 bank manifests, 60 horse receipts, 180 initial/best/final
checkpoint hashes, five matched initialization groups, every weight-effect
field, all three selection contracts, the complete aggregate market, and every
stratified gate field.  It reproduced `NO_SELECTION` exactly.

- Independent audit file SHA-256:
  `893bb8430a38410b516ff6820839995c5038536ac03d37cd88c64129c6992a65`.
- Exposure audit file SHA-256:
  `86f015a91eb211d55ea3a873c12fc26eb84c827321d335a87448105dd41a7002`.

The next legitimate experiment is a fresh preregistered confirmation with
random multi-view as the primary arm against static, shuffled, and hash
controls.  It must use new data and model seeds; this failed primary gate must
not be relabeled after the outcome.

