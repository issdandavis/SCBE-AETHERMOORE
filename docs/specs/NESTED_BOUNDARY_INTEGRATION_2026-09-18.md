# Nested decimal regions and weighted boundaries

Status: exact-cell reuse and local bridge mechanics tested on 2026-09-18.
Live routing integration and learned benefit are unmeasured. This is an
implementation interpretation of the user's existing nested-decimal design.

## Existing parts, before adding a new one

The connected Loom workspace already contains:

| Component under `loom/` | Actual responsibility |
|---|---|
| `experiments/clay_world_controller_20260823/clay_nested_calibration.py` | `NestedCalibrationCell`: exact rational intervals, parent-preserving refinements, tensor centers and explicit widths |
| `experiments/clay_world_controller_20260823/clay_hierarchical_multisign.py` | Symbolic phase addresses, six Rubix face ports, separate polarity and execution-receipt phase transitions |
| `experiments/clay_world_controller_20260823/clay_realm_breath_tool.py` | Earlier positive-amplitude breathing profile, Jacobian, time derivative and nested amplitude calibration |
| `experiments/clay_anchored_pivots_20260915/nested_sign_fields/field.py` | Exact nested reference frames and signed channels; separate region identities and coordinates |
| `game_engine/nested_decimal_fingerprint.py` | Older float-appended fingerprint experiment; finite-precision loss is documented in its tests |

The interval path and the symbolic phase address are different schemas. Do not
erase leading zeros or infer that an ordinal phase label defines an interval.
Do not use the float-appended fingerprint as boundary authority. Hashes identify
representations; they do not authenticate their author or grant permissions.

## Address, inner metric, then crossing

An address such as `0.0.1.0` selects the exact interval `[1/100, 11/1000)`.
Appending a subdivision retains its ancestry. In several axes, a region stores
one cell per axis. Parent and child relations preserve the exact paths. These
are finite, refinable addresses, not fractional spatial dimensions.

For axis cell center `c_i`, width `h_i`, and exact coordinate `x_i`, first compute

```
q_i = 2 * (x_i - c_i) / h_i
G = diag(w_i / sum(w)), with positive bounded weights
E(q) = q^T G q
S = (3/4) * sqrt(G)
u = S q
```

The subtraction and division happen with exact fractions before conversion to
floating point. For an in-region point, each `q_i` is in `[-1, 1)` and
`||u|| <= 3/4`. Deep regions remain distinguishable even when converting their
global coordinates directly to float would make them equal. Finite execution
still has limited precision; nearby local positions can also round together.

Each region owns its relative axis weights. Changing those weights changes
local geometry without changing the exact cell identity. The initial prototype
uses diagonal positive metrics, not arbitrary curvature or learned couplings.
Changing positive metric weights alone does not change a region's topology;
explicit adjacency and gate changes would change connectivity.

Use the declared SCBE profile to compute the proposal:

```
u' = F_b(u), using PY_FULL14's positive breathing schedule
q' = S^-1 u'
x'_i = c_i + (h_i/2) * q'_i
J_local = S^-1 * J_F(u) * S
```

The Jacobian holds the region and weights fixed. If weights become functions of
the state, their derivatives must also enter the chain rule. It is not a
derivative through a discrete wall-crossing decision. The candidate's rational
carrier exactly records a finite computed result; it does not make tanh exact.

The earlier Loom realm tool uses `1 + amplitude*sin(phase)` with amplitude below
one. Repaired PY_FULL14 uses `exp(log1p(b_max)*sin(phase))`. These profiles have
different parameters and must not be silently substituted or share mislabeled
receipts. The new local bridge explicitly tests the repaired PY_FULL14 source.

## The walled-city interpretation

Regions are districts, nested children are inner districts, their metrics are
local travel rules, and declared gates connect districts. Half-open cells give
adjacent regions an unambiguous seam. A breathing proposal can cross a cell wall
while remaining inside its computational unit ball; the bridge reports both
facts instead of clipping the crossing out of existence.

```mermaid
flowchart LR
    A[Exact cell path and coordinates] --> B[Local weighted chart]
    B --> C[L6 breathing and Jacobian]
    C --> D[Candidate and crossed faces]
    D -. proposed integration .-> E[Declared directed gate]
    E --> F[Mandatory authorization decisions]
    F --> G[Execute only final ALLOW]
```

The existing directed CFI and final-decision composition remain authoritative.
A small distance, high interaction weight, child membership or inside-cell
proposal never grants execution rights. The prototype always reports
`may_authorize=false` and mutates no world state.

## Local verification and next connection

Prototype: `C:/dev/loom/experiments/scbe_nested_boundary_20260918/`.
It imports the existing cells and tests the repaired SCBE worktree, rather than
cloning either implementation. Run `python -m pytest -o addopts='' -q` there;
`SCBE_REVIEW_ROOT` can point to another reviewed checkout.

Sixteen tests passed: 80-level address separation despite identical global
floats, parent containment, exact shared seams, metric changes, malformed
inputs, expansion beyond a wall without clipping or authorization, and analytic
Jacobians checked against finite differences at three seeded interior points.
The existing calibration module's nine tests also passed separately.

Next connect explicit region IDs and transition proposals to a declared gate
graph, with policy version and source provenance. A rebase into a neighboring
chart must preserve the proposed global coordinate and its error information;
it must not relabel an out-of-region value as admitted. Dynamic weights need
versioned updates and derivative/conditioning limits. Compare flat, unweighted
nested and weighted nested variants under equal compute, data and parameter
budgets before any training or efficiency claim. No running model or current
authorization path was switched to the prototype.
