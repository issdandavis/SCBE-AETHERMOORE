# SCBE-AETHERMOORE Minimal

A clean, minimal implementation of the SCBE risk scoring system. One file. One function. Works.

## Installation

```bash
# Copy scbe_core.py to your project, or:
pip install scbe-aethermoore  # Full package
```

## Quick Start

```python
from scbe_core import validate_action, Decision

# Evaluate an action
result = validate_action(
    context=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],  # 6D context vector
    action="read_data"
)

print(result.decision)  # Decision.ALLOW
print(result.risk_score)  # 0.15
print(result.processing_time_ms)  # 0.02
```

## Decision Types

| Decision | Meaning | Risk Range |
|----------|---------|------------|
| `ALLOW` | Safe to proceed | 0.0 - 0.3 |
| `QUARANTINE` | Needs human review | 0.3 - 0.7 |
| `DENY` | Blocked | 0.7 - 1.0 |

## Components

### 1. SCBEGate (Risk Scoring)

```python
from scbe_core import SCBEGate, SCBEConfig

# Custom configuration
config = SCBEConfig(
    allow_threshold=0.25,
    quarantine_threshold=0.6,
    use_hyperbolic=False,  # Euclidean performs equivalently (verified)
    harmonic_ratio=1.5,
)

gate = SCBEGate(config)
result = gate.evaluate([0.5, 0.5, 0.5, 0.5, 0.5, 0.5], "deploy_service")
```

### 2. SacredTonguesEncoder (Domain Separation)

```python
from scbe_core import SacredTonguesEncoder

# Encode data in different "tongues"
encoder = SacredTonguesEncoder("KO")  # Control Flow tongue
encoded = encoder.encode(b"Hello World")
decoded = encoder.decode(encoded)

assert decoded == b"Hello World"
```

Available tongues: `KO`, `AV`, `RU`, `CA`, `UM`, `DR`

### 3. RWPEnvelope (Tamper-Evident Messages)

```python
from scbe_core import RWPEnvelope

# Create and seal
envelope = RWPEnvelope("KO", "my-agent", {"action": "transfer", "amount": 100})
sealed = envelope.seal(b"secret_key_32_bytes_long!!!!")

# Verify and open
payload = RWPEnvelope.verify(sealed, b"secret_key_32_bytes_long!!!!")
if payload is None:
    print("Tampered or invalid!")  # Fail-to-noise: no error details
```

## Honest Claims

**What's proven:**
- The geometry (Poincaré ball) provides a valid metric space
- Risk scoring works for basic anomaly detection
- Sacred Tongues encoding is bijective (100% test coverage)
- RWP envelopes are tamper-evident

**What's NOT proven:**
- Hyperbolic distance does NOT outperform Euclidean for detection
  (Verified in `experiments/hyperbolic_vs_baselines.py`, AUC: 0.9995 vs 0.9553)
- The "518,400× security multiplier" is a weight product, not security metric
- The 95.3% detection rate lacks documented methodology

## Dependencies

None! Pure Python stdlib.

## License

MIT
