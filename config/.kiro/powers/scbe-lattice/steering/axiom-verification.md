# Axiom Verification Guide

## The 14 Axioms (A1-A14)

### Geometric Axioms (A1-A8)

| Axiom | Name                | Requirement           | Test                              |
| ----- | ------------------- | --------------------- | --------------------------------- |
| A1    | Input Domain        | t ∈ ℂ^D               | `test_complex_state_construction` |
| A2    | Realification       | ℂ^D → ℝ^{2D} isometry | `test_realification_isometry`     |
| A3    | SPD Weighting       | G positive definite   | `test_weighted_transform_spd`     |
| A4    | Poincaré Embed      | ‖u‖ < 1 - ε           | `test_poincare_clamping`          |
| A5    | Hyperbolic Distance | Metric properties     | `test_hyperbolic_distance_metric` |
| A6    | Breathing           | Diffeomorphism        | `test_breathing_diffeomorphism`   |
| A7    | Phase Transform     | Isometry              | `test_phase_isometry`             |
| A8    | Realm Distance      | min_k d_H(u, μ_k)     | `test_realm_distance`             |

### Signal Axioms (A9-A11)

| Axiom | Name           | Requirement             | Test                         |
| ----- | -------------- | ----------------------- | ---------------------------- |
| A9    | Regularization | Bounded denominators    | `test_signal_regularization` |
| A10   | Coherence      | All features ∈ [0,1]    | `test_coherence_bounds`      |
| A11   | Triadic        | Weighted temporal norms | `test_triadic_aggregation`   |

### Risk Axioms (A12-A14)

| Axiom | Name              | Requirement           | Test                          |
| ----- | ----------------- | --------------------- | ----------------------------- |
| A12   | Harmonic          | H = exp(d\*²)         | `test_harmonic_amplification` |
| A13   | Quasi-Dimensional | Multi-sphere geometry | `test_quasi_dimensional`      |
| A14   | Conformal         | Möbius consistency    | `test_conformal_invariants`   |

## Running Verification

### Full Suite

```bash
pytest tests/test_scbe_14layers.py -v --tb=short
```

### By Axiom Group

```bash
# Geometric (A1-A8)
pytest tests/test_scbe_14layers.py -k "complex or realif or spd or poincare or hyperbolic or breathing or phase or realm" -v

# Signal (A9-A11)
pytest tests/test_scbe_14layers.py -k "spectral or spin or triadic" -v

# Risk (A12-A14)
pytest tests/test_scbe_14layers.py -k "harmonic or risk" -v
```

### Property-Based Tests

```bash
# Run with hypothesis
pytest tests/test_scbe_comprehensive.py -v --hypothesis-show-statistics
```

## Manual Verification

### A4: Poincaré Clamping

```python
import numpy as np
from src.scbe_14layer_reference import poincare_embed

# Test with extreme input
x = np.array([100.0, 200.0, 300.0])
u = poincare_embed(x, alpha=1.0, epsilon=1e-5)

assert np.linalg.norm(u) < 1.0 - 1e-5, "A4 violated: point outside ball"
print(f"✓ A4: norm = {np.linalg.norm(u):.10f} < 0.99999")
```

### A5: Hyperbolic Distance Metric

```python
from src.scbe_14layer_reference import hyperbolic_distance

u = np.array([0.3, 0.4])
v = np.array([0.5, 0.1])
w = np.array([0.2, 0.6])

# Non-negativity
assert hyperbolic_distance(u, v) >= 0, "A5 violated: negative distance"

# Identity
assert hyperbolic_distance(u, u) < 1e-10, "A5 violated: d(u,u) != 0"

# Symmetry
assert abs(hyperbolic_distance(u, v) - hyperbolic_distance(v, u)) < 1e-10, "A5 violated: asymmetric"

# Triangle inequality
d_uv = hyperbolic_distance(u, v)
d_vw = hyperbolic_distance(v, w)
d_uw = hyperbolic_distance(u, w)
assert d_uw <= d_uv + d_vw + 1e-10, "A5 violated: triangle inequality"

print("✓ A5: All metric properties satisfied")
```

### A12: Harmonic Amplification

```python
from src.scbe_14layer_reference import harmonic_scale

# Low distance → low amplification
d_low = 0.5
H_low = harmonic_scale(d_low)
print(f"d* = {d_low} → H = {H_low:.4f}")

# High distance → exponential amplification
d_high = 3.0
H_high = harmonic_scale(d_high)
print(f"d* = {d_high} → H = {H_high:.4f}")

# Verify exponential growth
import math
expected = math.exp(d_high ** 2)
assert abs(H_high - expected) < 1e-6, "A12 violated: H != exp(d*²)"
print(f"✓ A12: H = exp(d*²) = {expected:.4f}")
```

## Compliance Report

Generate a full compliance report:

```bash
python tests/compliance_report.py --format markdown --output tests/scbe_compliance_report.md
```

Report includes:

- Pass/fail status for each axiom
- Test coverage metrics
- Performance benchmarks
- Recommendations for failed tests
