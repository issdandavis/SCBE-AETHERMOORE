---
tags: [prime-fog, geometry, circle-inscription, fermat-two-squares, gauss-circle]
updated_at: 2026-06-05
---

# Circle Inscription Geometry

Status: geometric rotation closed. It recovers known arithmetic structure and
the same fluctuation wall.

The tested rotation:

```text
prime p -> circle x^2 + y^2 = p^2
```

Then inspect two surfaces:

1. lattice points on the boundary;
2. lattice points in the interior versus area `pi*p^2`.

## Boundary Inscription

For odd primes:

```text
p ≡ 1 mod 4 -> 12 boundary lattice points
p ≡ 3 mod 4 ->  4 boundary lattice points
```

This is Fermat's two-squares theorem in geometric clothing. If `p ≡ 1 mod 4`,
then `p = a^2 + b^2`, so the radius-`p` circle gains the eight non-axis points
from sign/order symmetries, plus the four axis points. If `p ≡ 3 mod 4`, only
the axis points survive.

So the boundary count is a `p mod 4` detector: a known wheel lane.

## Interior Inscription

For the interior count:

```text
N(p) = #{(x,y) in Z^2 : x^2 + y^2 <= p^2}
E(p) = N(p) - pi*p^2
```

The error sits on the Gauss circle problem surface. In the measured range it
stays at square-root-scale fluctuation: bounded enough to describe a wall, but
not structured enough to select the next prime.

This is the same shape seen in the address tower and Riemann-zero frame:

```text
known smooth surface + square-root-scale discrepancy
```

## Verdict

Circle inscription is a clean geometric explanation, not a new lane:

```text
boundary -> Fermat / mod 4 wheel
interior -> Gauss circle discrepancy wall
```

It belongs in the geometric-rotations closure. It does not reopen targeting.
