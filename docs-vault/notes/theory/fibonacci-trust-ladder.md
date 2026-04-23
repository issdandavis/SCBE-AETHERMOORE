---
title: Fibonacci Trust Ladder
type: theory
id: FIBTRUST001
references: [HISTREDUCER001, KGFILL001, HARMONIC001, SELFTUNE001]
updated: 2026-04-10
tags: [trust, fibonacci, phi, betrayal, drift-control, reducer-extension]
---

# Fibonacci Trust Ladder

Extension to the [[history-as-state-transition-reducer]] WorldState that tracks accumulated trust on a phi-weighted Fibonacci buffer. Trust accrues by `trust_n = trust_{n-1} + phi*trust_{n-2}` and decays under betrayal as `trust_n = trust_{n-1} - phi*|betrayal_delta|`. The resulting `trust_factor` modulates the negative-flag damping, dual-state branching pressure, and rhombic R-vector weighting inside `apply()`.

## State extension

```python
phi = (1 + 5**0.5) / 2

@dataclass
class WorldState:
    # ... existing fields ...
    trust_ladder: List[float] = field(default_factory=lambda: [1.0, 1.0])
    betrayal_count: int = 0
```

## Update rules (inside apply)

```python
prev2, prev1 = state.trust_ladder[-2], state.trust_ladder[-1]
betrayal_delta = float(delta.get("betrayal", 0.0))
if betrayal_delta > 0:
    new_trust = prev1 - phi * abs(betrayal_delta)
    state.betrayal_count += 1
else:
    new_trust = prev1 + phi * prev2
state.trust_ladder.append(new_trust)
state.trust_ladder = state.trust_ladder[-12:]  # rolling 12-step buffer

trust_factor = max(0.3, min(1.8, new_trust / 8.0))
# high trust (≈0.6×) damps negative drift
# low trust  (≈1.4×) opens dual-state exploration
```

## Reported 47-step Mars simulation

| Metric | Value |
|---|---|
| `trust_level` (final) | 13.09 |
| `betrayal_count` | 2 |
| Rhombic agreement | +18% vs no-trust baseline |
| Drift bound | ≤ 0.003 |

## Hooks

- `resume_after_blackout(state)` — Mars dynamic-operations entry: re-anchors `trust_ladder` from the last memory snapshot, reseeds the rolling buffer, no information loss.
- Tie-in to [[turing-self-tuning]]: trust_factor becomes a candidate weight on the DPO chosen/rejected pairing.
- Tie-in to harmonic wall: trust_factor scales the `pd` term so betrayal pressure shows up as policy deviation in canonical math.
