---
name: scbe-entropy-dynamics
description: Monitor and compute entropy, time flow, and quantum state dynamics for the SCBE-AETHERMOORE 7th/8th/9th dimensions. Use when debugging entropy anomalies, time drift, quantum decoherence, or tuning the Ornstein-Uhlenbeck process parameters.
---

# SCBE Entropy Dynamics

Use this skill for reasoning about the three higher-dimensional dynamics (time, entropy, quantum) that govern SCBE-AETHERMOORE system health.

## Three Dynamic Dimensions

### Dimension 7: Time Flow τ̇(t)
```
τ̇(t) = 1.0 + DELTA_DRIFT_MAX · sin(OMEGA_TIME · t)
```
- Normal flow = 1.0
- Oscillates in range [1 - DELTA_DRIFT_MAX, 1 + DELTA_DRIFT_MAX] = [0.5, 1.5]
- Period = 60 seconds (OMEGA_TIME = 2π/60)
- **Hard constraint**: τ̇ > 0 (causality — time never reverses)
- With current parameters, minimum is 0.5 > 0, so causality is always satisfied under normal operation

### Dimension 8: Entropy Flow η̇
```
η̇ = BETA · (ETA_TARGET - η) + 0.1 · sin(t)
```
- Ornstein-Uhlenbeck mean-reverting drift toward ETA_TARGET = 4.0
- BETA = 0.1 controls reversion speed
- Periodic perturbation amplitude = 0.1
- **Bounds**: η must stay within [ETA_MIN=2.0, ETA_MAX=6.0]

### Dimension 9: Quantum State q(t)
```
q(t) = q₀ · e^(-iHt)
```
- Unitary evolution preserves |q| = |q₀|
- Phase rotates at rate H (Hamiltonian energy)
- **Health checks**: Fidelity f_q ≥ 0.9, Von Neumann entropy S_q ≤ 0.2

## Shannon Entropy Computation

```python
# For the 6D context vector:
magnitudes = [|x| if complex else float(x) for x in context_vector]
histogram = np.histogram(magnitudes, bins=16, density=True)
η = -Σ p · log₂(p + 1e-9)  # over non-zero bins
```

- Uses 16 bins for granularity
- density=True normalizes to probability distribution
- 1e-9 epsilon prevents log(0)

## Key Constants

| Constant       | Value   | Role                               |
|----------------|---------|-------------------------------------|
| DELTA_DRIFT_MAX| 0.5     | Max time drift amplitude            |
| OMEGA_TIME     | 2π/60   | Time cycle frequency (1/min)        |
| BETA           | 0.1     | Entropy mean-reversion rate         |
| ETA_TARGET     | 4.0     | Entropy attractor                   |
| ETA_MIN        | 2.0     | Entropy floor (QUARANTINE below)    |
| ETA_MAX        | 6.0     | Entropy ceiling (QUARANTINE above)  |
| KAPPA_ETA_MAX  | 0.1     | Max entropy curvature               |
| DOT_TAU_MIN    | 0.0     | Causality floor (τ̇ must exceed)    |

## Diagnostic Workflow

1. **Entropy anomaly**: Check if context vector has degenerate components (all same value → low entropy, or uniform random → high entropy).
2. **Time drift**: Verify OMEGA_TIME period matches expected system cycle. Check if external clock sync is causing discontinuities.
3. **Quantum decoherence**: Check if Hamiltonian H is stable. Large H causes fast phase rotation which can reduce fidelity measurements.
4. **Curvature spike**: Compute numerical second derivative of η(t). If |κ_η| > KAPPA_ETA_MAX, the entropy landscape is too volatile.

## Guardrails

1. Entropy computation must handle mixed float/complex arrays gracefully.
2. The O-U process parameters (BETA, ETA_TARGET) are tuned together — changing one requires re-evaluating the other.
3. Quantum evolution must use exact unitary operator, not approximations.
4. Time flow monitoring should raise alerts well before τ̇ approaches 0.
