# Clay multi-view exposure-depth preregistration — 2026-11-13

## Question

When every data arm receives twice as many optimizer draws, does exact
repetition catch the independently sampled three-view curriculum, or does wider
valid concept support retain its advantage?

The preceding confirmation remains `NO_SELECTION`; this run does not revise its
gate after seeing the result.  It tests a new exposure-depth question using new
model and data seeds.

## Locked campaign

- Arms: `static_unique`, `static_repeated`, `curriculum_independent`.
- Primary: `curriculum_independent`.
- Controls: both static arms.
- Seeds: `173, 191, 211, 227, 251`.
- Data seed offset: `2,000,000`.
- Held sectors: `1, 4, 7`.
- Rows per arm/fold: `30,000`.
- Held and anchor rows/fold: `10,000` each.
- Steps: `4,800`; batch: `192`; expected row exposure: `30.72`.
- Exact-repetition underlying-concept exposure: `92.16` expected.
- Learning rate: `0.001`; AdamW decay: `0.0001`.
- Hidden width: `64`; stable-class support: at least `32`.
- Horses: `45`.

## Gate and interpretation

The primary comparison is stratified by held sector because the completed run
showed that raw pooling mixes tasks with substantially different class support.
For accuracy and stable macro-F1, the primary arm must:

1. have a positive mean delta against both controls in every held sector;
2. exceed the larger of two pooled standard deviations and a conservative
   finite-evaluation floor of `2 / sqrt(10,000) = 0.02` against both controls
   in at least two of three sectors; and
3. retain anchor accuracy within two percentage points in every sector.

Global pooled metrics, matched win/loss counts, worst stable-class accuracy,
all-supported F1, sparse-class support, weight drift, gradient coherence, best
step, and final trace direction remain mandatory diagnostics.  A miss is
`NO_SELECTION`, not evidence that more width or unfreezing is required.

No result from this mechanics campaign authorizes promotion, execution
authority, partial unfreezing, or deletion of earlier checkpoints.

The frozen evaluator is
`python/scbe/clay_multiview_stratified_gate.py`; the CLI writes a separate
receipt and never changes the producer's verdict or weights.

