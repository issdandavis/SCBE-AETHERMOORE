---
tags: [prime-fog, prime-circuit, circle-of-fifths, residue-wheel, alignment-ledger, axis-gate, falsification]
updated_at: 2026-06-05
---

# Prime Circuit Geometry

Status: FALSIFIED as a standalone search lane.

This tested the "circle of fifths for primes" idea:

```text
prime value -> residue-wheel phase
log(prime) -> ring radius
local prime-to-prime transitions -> circuit bend
```

## Axis

Implemented in `scripts/research/prime_alignment_ledger.py`:

`prime_circuit_geometry`

Definition:

```text
point(p) = log(p) * (cos(2π * (p mod 210) / 210),
                    sin(2π * (p mod 210) / 210))

score(row) =
    local turn angle through previous/current/next scan_prime on this wheel
  + 0.25 * radial step-size change
```

It is label-free:

- uses `scan_prime`,
- uses previous/current/next scan primes in scan order,
- uses no `future_anchor`,
- uses no `first_anchor_*`,
- uses no tuned anchor residues.

Artifact:

`artifacts/prime_alignment_ledger_prime_circuit/gate_demo.json`

Run:

```powershell
python scripts\research\prime_alignment_ledger.py --rings K,L,M,N --gate-demo --gate-seeds 120 --axes frozen,prime_circuit_geometry --out-dir artifacts\prime_alignment_ledger_prime_circuit
```

## Result

| Ring | Precision | Null p95 | Count error | Verdict |
| --- | ---: | ---: | ---: | --- |
| K | 0.390 | 0.373 | +185 | PASS precision, FAIL count |
| L | 0.359 | 0.360 | +181 | FAIL precision, FAIL count |
| M | 0.414 | 0.421 | +141 | FAIL precision, FAIL count |
| N | 0.374 | 0.373 | +149 | PASS precision, FAIL count |

Verdict: rejected. The circuit has a weak identity flicker on K and N, but it
does not clear precision on every ring and it over-predicts every ring. It is a
scatterer, not a count-honest lane.

## Interpretation

The transformation is a valid visualization substrate: it folds primes onto a
wheel in the same spirit that the circle of fifths folds notes by recurring
frequency relationship. But the current local-bend score does not turn that
visual circuit into a usable anchor locator.

If this family is revisited, the next version should not be another smooth
local curvature score. It would need a count-bounded circuit rule or a
count-matched circular-shift null before any apparent precision edge is trusted.
