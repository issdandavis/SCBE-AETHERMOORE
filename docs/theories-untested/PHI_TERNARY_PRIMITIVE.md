---
name: Phi-Ternary Primitive
description: Golden-ratio-weighted ternary logic — engineering primitive from Riemann/Bible research session
type: theory-untested
date: 2026-03-26
---

# Phi-Ternary: Golden-Ratio-Weighted Ternary Logic

## Definition

```
q in {-1, 0, +1}    (ternary state: inhibit / neutral / activate)
w = phi^k            (golden ratio scale: depth, cost, hierarchy)
x = q * w            (phi-lifted ternary value)
```

Ternary decides DIRECTION. Phi decides STRENGTH.

## Properties

- Neutral (0) is a REAL active state, not absence of decision
- Positive and negative mirror symmetrically: +phi^k and -phi^k
- Scale is self-similar: 1, phi, phi^2, ... ladder
- Logic and magnitude are separated

## Dual Ternary

Two independent phi-ternary systems verify each other:
- Agreement: both say the same thing -> 1 = 1
- Disagreement: non-congruent object detected (adversarial signal)

Maps to existing system:
- System A: Hamiltonian Braid (Mirror/Shift/Refactor)
- System B: Governance Gate (ALLOW/QUARANTINE/DENY)

## Origin

Extracted from Riemann Hypothesis exploration:
- Ternary center forced at Re(s) = 1/2 by geometry of three symmetric states
- R = 1.5 = half of 3 = the harmonic wall default
- Plateau's 120 degrees = 360/3 = same geometric forcing
- The neutral state prevents the system from collapsing to binary

## Status

Implemented and tested:
- src/primitives/phi_ternary.py
- tests/test_phi_ternary.py (32 tests, all pass)
- NOT yet wired into the main pipeline
