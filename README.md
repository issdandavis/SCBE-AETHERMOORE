# SCBE 14-Layer Hyperbolic Governance System

Complete implementation of the Spectral Context-Bound Encryption (SCBE) 14-layer hyperbolic governance pipeline with rigorous mathematical foundations.

## Overview

This system implements a mathematically proven security and governance framework using:
- **Hyperbolic Geometry** (Poincaré ball model)
- **Complex Analysis** (state representation)
- **Riemannian Geometry** (metric preservation)
- **Signal Processing** (spectral and spin coherence)
- **Information Theory** (entropy and risk quantification)

## Mathematical Foundation

All 14 layers are proven from first principles. See `docs/scbe_proofs_complete.tex` for complete mathematical proofs.

### Layer Architecture

1. **Layer 1**: Complex State Construction - Maps features to ℂ^D
2. **Layer 2**: Realification - Isometric embedding to ℝ^{2D}
3. **Layer 3**: Weighted Transform - SPD matrix weighting
4. **Layer 4**: Poincaré Embedding - Maps to hyperbolic ball 𝔹^n
5. **Layer 5**: Hyperbolic Distance - Computes d_ℍ metric
6. **Layer 6**: Breathing Transform - Radial diffeomorphism
7. **Layer 7**: Phase Transform - Möbius addition + rotation (isometry)
8. **Layer 8**: Realm Distance - d* = min_k d_ℍ(u, μ_k)
9. **Layer 9**: Spectral Coherence - FFT-based pattern analysis
10. **Layer 10**: Spin Coherence - Complex phasor alignment
11. **Layer 11**: Triadic Temporal - Multi-timescale aggregation
12. **Layer 12**: Harmonic Scaling - H(d*, R) = R^{d*²}
13. **Layer 13**: Risk Decision - Three-way classification
14. **Layer 14**: Audio Axis - Acoustic telemetry processing

## Installation

### Dependencies

```bash
# Core dependencies
pip install numpy>=1.20.0
pip install scipy>=1.7.0

# Optional (for visualization and demos)
pip install matplotlib>=3.3.0
```

### Python Version

Requires Python 3.8 or higher.

## Quick Start

### 1. Run the Reference Implementation

```bash
python src/scbe_14layer_reference.py
```

This will execute all 14 layers individually and demonstrate the full pipeline.

### 2. Run Comprehensive Tests

```bash
python tests/test_scbe_14layers.py
```

Expected output: All tests passing (50+ individual layer tests).

### 3. Run Interactive Demo

```bash
python examples/demo_scbe_system.py
```

This demonstrates:
- Benign traffic handling
- Suspicious activity detection
- Malicious attack blocking
- Temporal pattern evolution
- Custom risk weighting strategies
- Breathing parameter effects
- Risk landscape visualization

## File Structure

```
SCBE_Production_Pack/
├── src/
│   ├── scbe_14layer_reference.py      # Standalone 14-layer implementation
│   └── scbe_cpse_unified.py           # Full system with axiom validation
├── tests/
│   └── test_scbe_14layers.py          # Comprehensive test suite
├── examples/
│   └── demo_scbe_system.py            # Interactive demo scenarios
├── docs/
│   └── scbe_proofs_complete.tex       # Mathematical proofs
├── config/
│   ├── scbe.alerts.yml                # Alert configuration
│   ├── sentinel.yml                   # Monitoring config
│   └── steward.yml                    # Governance rules
└── README.md                          # This file
```

## Usage Examples

### Basic Pipeline Execution

```python
from scbe_14layer_reference import scbe_14layer_pipeline
import numpy as np

# Create input context
amplitudes = np.array([0.8, 0.6, 0.5, 0.4, 0.3, 0.2])
phases = np.linspace(0, np.pi/4, 6)
t = np.concatenate([amplitudes, phases])

# Generate telemetry signals
telemetry = np.sin(np.linspace(0, 4*np.pi, 256))
audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 512))

# Run pipeline
result = scbe_14layer_pipeline(
    t=t,
    D=6,
    breathing_factor=1.0,
    telemetry_signal=telemetry,
    audio_frame=audio
)

print(f"Decision: {result['decision']}")
print(f"Risk: {result['risk_prime']:.6f}")
```

---

**Status**: ✓ All 14 layers implemented and verified
**Test Coverage**: 50+ unit tests passing
**Mathematical Validation**: Axioms A1-A12 proven and verified

For complete documentation, see sections below.
