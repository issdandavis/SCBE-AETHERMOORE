# Quasi-Integer Recoupling

Generated: 2026-05-31

## Definition

Quasi-integer recoupling is the SCBE middle-layer operation that maps a continuous,
fractional, or method-dependent value back into a declared discrete state while
preserving the raw value, error, tolerance, confidence, and loss boundary.

It is not plain rounding. Rounding discards uncertainty. Recoupling records the
uncertainty and lets the reaction packet decide whether the transform remains
bijective, recoverable, ambiguous, or invalid.

## Why This Is Chemically Reasonable

Chemistry already moves between continuous and symbolic representations:

- formal charge is an integer-like Lewis-structure accounting value;
- partial charge is method-dependent and fractional;
- bond order can be formal/integer-like, aromatic/resonance-like, or fractional
  depending on the model;
- molecular graphs need discrete bond/charge states even when upstream evidence
  comes from electron-density proxies or descriptor models.

RDKit exposes this split directly. It stores formal charges and bond/aromaticity
states on molecular graphs, and it can compute Gasteiger partial charges as atom
properties named `_GasteigerCharge`.

## Packet Rule

Every recoupling result should carry:

```json
{
  "raw_value": 1.49,
  "recoupled_value": 1.5,
  "label": "aromatic-or-resonance-like",
  "error": 0.01,
  "tolerance": 0.1,
  "confidence": 0.9,
  "decision": "RECOUPLED",
  "reason": "nearest state within tolerance"
}
```

Allowed decisions:

- `RECOUPLED`: nearest state is within tolerance;
- `AMBIGUOUS`: raw value is equidistant between states;
- `OUT_OF_RANGE`: nearest state exists but exceeds tolerance;
- `INVALID`: raw value is not finite or cannot be evaluated.

## Current Implementation

Code:

- `python/scbe/quasi_integer_recoupling.py`

Presets:

- integer ladder for formal-charge-like states;
- half-integer ladder;
- chemical bond-order ladder: `0`, `1`, `1.5`, `2`, `3`;
- formal-charge ladder: `-4` through `4`.

Harness integration:

- `evaluate_bijective_reaction()` accepts recoupling objects as field values.
- If the recoupling is valid, the recoupled value participates in identity
  comparison.
- The full raw recoupling object remains engraved in the field check.

## Claim Boundary

This is a computational representation bridge. It does not claim that every
fractional quantum-chemical value has one true integer state. It claims that a
declared tolerance and state ladder can safely convert continuous evidence into
auditable symbolic packets.

## Sources

- RDKit `rdPartialCharges.ComputeGasteigerCharges` documentation: computes
  Gasteiger charges and stores them under `_GasteigerCharge`.
- IUPAC Gold Book formal charge entry: formal charge is a Lewis-structure
  accounting quantity using valence electrons, lone pairs, and half bond count.
- RDKit `rdDetermineBonds.DetermineBondOrders` documentation: assigns
  connectivity and bond orders from coordinates and charge context.
- IUPAC Gold Book bond order entry: valence-bond bond order can be treated as a
  weighted average of formal bond orders.
