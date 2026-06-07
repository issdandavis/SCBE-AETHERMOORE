---
tags: [prime-fog, numerical-emulsion, factor-pressure, alignment-ledger, axis-gate, falsification]
updated_at: 2026-06-05
---

# Numerical Emulsion Axis

Status: FALSIFIED as a standalone search lane.

This tested the "prime as phase boundary" idea directly:

```text
prime field <-> composite emulsion collar <-> prime field
```

## Axis

Implemented in `scripts/research/prime_alignment_ledger.py`:

`numerical_emulsion`

Definition:

```text
score(row) =
    log1p(tau(scan_prime - 1) + tau(scan_prime + 1))
  + log1p(max tau(scan_prime +/- d), d=1..6)
  + left/right divisor-pressure asymmetry over d=1..6
```

It is label-free:

- uses `scan_prime`,
- uses local divisor counts around `scan_prime`,
- uses no `future_anchor`,
- uses no `first_anchor_*`,
- uses no fitted target statistics.

Artifact:

`artifacts/prime_alignment_ledger_numerical_emulsion/gate_demo.json`

Run:

```powershell
python scripts\research\prime_alignment_ledger.py --rings K,L,M,N --gate-demo --gate-seeds 120 --axes frozen,numerical_emulsion --out-dir artifacts\prime_alignment_ledger_numerical_emulsion
```

## Result

| Ring | Precision | Null p95 | Count error | Verdict |
| --- | ---: | ---: | ---: | --- |
| K | 0.358 | 0.372 | +240 | FAIL precision, FAIL count |
| L | 0.349 | 0.360 | +229 | FAIL precision, FAIL count |
| M | 0.409 | 0.421 | +197 | FAIL precision, FAIL count |
| N | 0.355 | 0.373 | +189 | FAIL precision, FAIL count |

Verdict: rejected. The factor-pressure collar creates many structured local
maxima, but they are not identity-honest anchor locations. It sees emulsion
volume, not a usable prime-anchor lane.

## Interpretation

The metaphor is still useful as a substrate concept: primes can be treated as
interfaces surrounded by composite factor pressure. But this simple frozen
collar score does not cross the gate. Any future "numerical emulsion" attempt
needs a new coordinate, not another weighting of the same local tau collar.
