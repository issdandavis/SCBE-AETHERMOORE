# Getting Started with SCBE Lattice Manager

## Prerequisites

```bash
# Install Python dependencies
pip install numpy scipy hypothesis pytest

# Verify installation
python -c "import numpy; import scipy; print('Ready')"
```

## Quick Start

### 1. Run the Demo

```bash
python examples/demo_scbe_system.py
```

This demonstrates:

- 14-layer SCBE pipeline execution
- Risk scoring with harmonic amplification
- Decision gating (ALLOW/QUARANTINE/DENY)

### 2. Run Tests

```bash
# All tests
pytest tests/test_scbe_14layers.py -v

# Specific layer tests
pytest tests/test_scbe_14layers.py -k "poincare" -v
pytest tests/test_scbe_14layers.py -k "breathing" -v
pytest tests/test_scbe_14layers.py -k "harmonic" -v
```

### 3. Generate Compliance Report

```bash
python tests/compliance_report.py
```

Output: `tests/scbe_compliance_report.md`

## Common Tasks

### Embed a Vector into Poincaré Ball

```python
import numpy as np
from src.scbe_14layer_reference import poincare_embed

# Raw vector (any dimension)
x = np.array([0.8, 0.6, 0.5, 0.4, 0.3, 0.2])

# Embed with clamping (ensures ||u|| < 1)
u = poincare_embed(x, alpha=1.0, epsilon=1e-5)
print(f"Embedded: {u}, norm: {np.linalg.norm(u):.6f}")
```

### Compute Hyperbolic Distance

```python
from src.scbe_14layer_reference import hyperbolic_distance

# Two points in Poincaré ball
u = np.array([0.3, 0.4, 0.0])
v = np.array([0.5, 0.1, 0.2])

d = hyperbolic_distance(u, v)
print(f"Hyperbolic distance: {d:.4f}")
```

### Run Full Pipeline

```python
from src.scbe_14layer_reference import scbe_14layer_pipeline
import numpy as np

# Context vector (amplitudes + phases)
amplitudes = np.array([0.8, 0.6, 0.5, 0.4, 0.3, 0.2])
phases = np.linspace(0, np.pi/4, 6)
t = np.concatenate([amplitudes, phases])

# Telemetry and audio signals
telemetry = np.sin(np.linspace(0, 4*np.pi, 256))
audio = np.sin(2*np.pi*440*np.linspace(0, 1, 512))

# Execute pipeline
result = scbe_14layer_pipeline(
    t=t, D=6,
    breathing_factor=1.0,
    telemetry_signal=telemetry,
    audio_frame=audio
)

print(f"Decision: {result['decision']}")
print(f"Risk: {result['risk_prime']:.4f}")
print(f"Harmonic: {result['harmonic_scale']:.4f}")
```

## File Map

| Component         | File                            |
| ----------------- | ------------------------------- |
| 14-Layer Pipeline | `src/scbe_14layer_reference.py` |
| Unified CPSE      | `src/scbe_cpse_unified.py`      |
| Aethermoore Core  | `src/aethermoore.py`            |
| Symphonic Cipher  | `src/symphonic_cipher/core.py`  |
| Tests             | `tests/test_scbe_14layers.py`   |
| Demo              | `examples/demo_scbe_system.py`  |
| Compliance        | `tests/compliance_report.py`    |

## Next Steps

1. Read `docs/COMPREHENSIVE_MATH_SCBE.md` for axiom proofs
2. Study `docs/LANGUES_WEIGHTING_SYSTEM.md` for 6D tensor math
3. Run `examples/demo_integrated_system.py` for full system demo
