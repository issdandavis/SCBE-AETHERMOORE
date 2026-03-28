# Signed Multi-Plane Encoding (Prototype)

Status: Experimental prototype  
Code: `experiments/signed_multiplane_encoding_demo.py`  
Tests: `tests/test_signed_multiplane_encoding.py`

## Summary

This prototype tests a state-expansion idea:

- Standard binary two-plane symbol space: `(0/1)^2 = 4` states
- Balanced ternary two-plane symbol space: `(-1/0/+1)^2 = 9` states
- Signed-binary two-plane symbol space: `(+/-0, +/-1)^2 = 16` states

The signed-binary representation uses signed zero as a distinct symbolic state
for routing/history metadata, while preserving arithmetic compatibility.

## Representation

Per plane, define a signed bit:

- magnitude `m in {0, 1}`
- sign `s in {-1, +1}`

Scalar value:

- if `m=1`: `x = s`
- if `m=0`: `x = +/-0` (symbolic state retained by sign)

Unit-interval map for each signed bit:

- `-1 -> 0`
- `-0 -> 0.5 - eps`
- `+0 -> 0.5 + eps`
- `+1 -> 1`

## Geometry

Codewords are built with two components:

1. Sphere/spiral anchor (`Fibonacci sphere`) for global indexing
2. Rotated local vector for per-state offset:
   - signed: `[a, b, z_signed_zero]`
   - ternary: `[a, b, 0]`

Then:

`codeword = anchor + local_scale * (R * local_vector)`

where `R` is a 3D rotation matrix from slant angles.

## Decode

Decode by nearest-neighbor lookup in the deterministic codebook.

## Current empirical output

From `python experiments/signed_multiplane_encoding_demo.py --noise-std 0.04`:

- capacity:
  - binary: `2.000` bits
  - ternary: `3.170` bits
  - signed: `4.000` bits
- round-trip nearest decode:
  - signed: `1.000`
  - ternary: `1.000`

## Run

```powershell
python experiments/signed_multiplane_encoding_demo.py --noise-std 0.04
pytest -q tests/test_signed_multiplane_encoding.py
```

## Notes

- This is an encoding/geometry experiment, not a cryptographic security claim.
- Signed zero should be treated as metadata state, not numeric semantic value.
