# Sector-gradient node-growth result — 2026-11-10

Status: deterministic mechanics pass. No model-quality, semantic-independence,
speed, promotion, or unfreeze claim.

## What is now real

`python/scbe/sector_gradient_growth.py` builds an adaptive visual mesh over the
existing algebraic radial token table. Canonical opcode bytes use the existing
trichromatic board projection. Each sector packs bounded gradient stops and
grows two radial children only when the split strictly lowers measured RGB
reconstruction error. Leaves must cover every source cell exactly once and may
not exceed the declared depth.

The reference renderer produced an actual 384 x 384 PNG at:

`C:\dev\clay-training-runs\sector-gradient-node-growth-20261110\run-seed-20261110-v2\sector-gradient-growth.png`

PNG SHA-256:
`aeb56b9941226d18c7b1a7c4fba9228ab8f2472c80c172fb46597bb2cc26e9af`

## Fixed fixture evidence

| Metric | Candidate | Shuffled binding control |
|---|---:|---:|
| Root nodes | 8 | 8 |
| Total nodes | 40 | 56 |
| Grown nodes | 16 | 24 |
| Leaves | 24 | 32 |
| Maximum depth | 2 | 2 |
| Packed leaf stops | 56 | 64 |
| Flat RGB MSE | 8,833.8958 | 8,043.5104 |
| Fixed-gradient RGB MSE | 7,017.6146 | 6,849.3854 |
| Adaptive RGB MSE | 0.0 | 0.0 |

The source fixture contained 37 distinct opcode colors. Pixel interpolation
rendered 4,214 distinct non-background RGB values. The shuffled control also
reached zero error, but needed more nodes and stops. This is evidence that the
candidate fixture is more compact under this exact deterministic partition,
not evidence that byte-derived color adds independent information.

## Control caught during development

The first gradient fitter could be worse than a flat fill on alternating color
samples. The baseline test failed. The final fitter now measures both options
and retains the packed mean whenever a gradient loses. Accepted child growth
must then improve on that winning parent representation. This prevents visual
detail from being reported as fidelity when its measured reconstruction error
is actually higher.

## Verification

`python -m pytest tests/tokenizer/test_sector_gradient_growth.py tests/tokenizer/test_algebraic_radial_token_table.py -q`

Result: 20 passed. The suite covers deterministic receipts, exact bounded leaf
coverage, observed growth, no-growth uniform control, added pixel shades,
shuffled binding, invalid budgets, and the pre-existing table invariants.

## Dense sector-ply extension

The follow-up renderer separates the topology budget from the terminal palette
budget. Three stops still decide every split; only after the node tree is fixed
may a leaf pack as many as eight source-aligned stops. This prevents added color
fidelity from erasing the error signal that causes node growth.

Measured output:

`C:\dev\clay-training-runs\sector-gradient-node-growth-20261110\run-seed-20261110-v4\sector-gradient-growth.png`

Matched three-stop control:

`C:\dev\clay-training-runs\sector-gradient-node-growth-20261110\run-seed-20261110-v4\sector-gradient-growth-3-stop-control.png`

Both renders used the same 24-node topology: 8 roots grew into 16 leaves. The
dense candidate packed 64 stops instead of 44, reduced adaptive RGB MSE from
3,117.65625 to 0, increased the rendered non-background palette to 9,352
colors, and produced a different PNG hash. All eight declared checks passed.

Verification after the extension: 22 tests passed.

## Explicit growth-preserving fidelity gate

The v5 measurement makes the relationship between tree growth and image
fidelity an explicit regression gate instead of relying on two separate
checks. The dense candidate and its three-stop control must have the same
child topology and the same positive `grown_node_count`; the dense candidate
must also render strictly more non-background colors.

Measured receipt:

`C:\dev\clay-training-runs\sector-gradient-node-growth-20261110\run-seed-20261110-v5\metrics.json`

Both variants retained 8 grown internal nodes in the same 24-node tree. The
dense sector ply packed 64 stops rather than 44 and rendered 9,352 distinct
colors rather than 5,065, a gain of 4,287 shades. Its adaptive RGB MSE was 0,
compared with 3,117.65625 for the matched control. All ten declared checks
passed, including the new `node_growth_preserved_with_dense_palette` and
`denser_leaf_palette_adds_rendered_colors` checks.

