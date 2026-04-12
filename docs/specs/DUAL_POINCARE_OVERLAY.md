# Dual Poincare Overlay

## Purpose

The dual Poincare overlay is a fast, fail-closed verification layer for Pump-side state validation.
It evaluates the same event in two independent hyperbolic embeddings and only accepts states that
remain inside both trust regions and exhibit matching loop geometry.

## Core Object

For one `state21` event, define:

- Ball A: governance / geo opinion of state
- Ball B: semantic / spectral opinion of state

The current implementation maps:

- Ball A -> `u[0:6]`
- Ball B -> `theta[0:6]`, lifted through `sin(theta_i)` before projection

Both are projected into Poincare-ball coordinates with independent embedding strengths.

## Trust Intersection

Let:

- `u_A` be the Ball A point
- `u_B` be the Ball B point
- `c_A`, `c_B` be trust centers
- `eps_A`, `eps_B` be trust radii

Acceptance requires:

`d_H(u_A, c_A) <= eps_A`

and

`d_H(u_B, c_B) <= eps_B`

This is the practical "Venn overlap" gate: both geometries must agree that the state is inside
their trusted region.

## Loop Verification

Each ball runs a 4-step commutator loop using Mobius addition:

`u1 = u ⊕ a`

`u2 = u1 ⊕ b`

`u3 = u2 ⊕ (-a)`

`u4 = u3 ⊕ (-b)`

The loop displacement is:

`Delta = d_H(u, u4)`

Per-ball acceptance requires:

`Delta_A <= tau_A`

`Delta_B <= tau_B`

Cross-ball agreement requires:

`|Delta_A - Delta_B| <= eta`

This checks geometry-of-processing, not only point location.

## Control Symbol

`NEG_ZERO_FREEZE` is a control symbol, not IEEE floating `-0`.

On `NEG_ZERO_FREEZE`:

1. Project both ball states into their trust regions.
2. Force `HOLD`.
3. Require quorum to exit.
4. Still run and log the dual loop metrics.

This preserves the "freeze, inspect, and defend" semantics already used in SCBE governance.

## Current Defaults

- Ball A indices: `(0, 1, 2, 3, 4, 5)`
- Ball B indices: `(6, 7, 8, 9, 10, 11)`
- Ball A alpha: `0.15`
- Ball B alpha: `0.15`
- Trust radius: `1.5`
- Loop step scale: `0.08`
- Loop displacement max: `0.35`
- Delta match tolerance: `0.2`

Ball B is embedded conservatively on purpose. A higher alpha over-amplifies the phase slice and
causes the second ball to stop behaving like a soft second opinion of the same event.

## Implementation

- [dual_overlay.py](C:/Users/issda/SCBE-AETHERMOORE/src/polly_pump/dual_overlay.py)
- [test_polly_pump_dual_overlay.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_polly_pump_dual_overlay.py)

## Status

This is an experimental Pump-side verifier built on live SCBE primitives:

- `state21` parsing
- Poincare hyperbolic distance
- Mobius addition

It is suitable for further integration work, but it is not yet canonical governance law.
