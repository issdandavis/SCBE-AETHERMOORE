# SCBE-AETHERMOORE: Getting Started Guide

**Document ID:** SCBE-ENABLE-2026-001  
**Version:** 1.0.0  
**Date:** January 18, 2026  
**Author:** Isaac Davis

---

## Overview

SCBE-AETHERMOORE is a post-quantum hybrid encryption system combining:

- **14-layer hyperbolic geometry** for AI safety governance
- **SpiralSeal SS1** for authenticated encryption (AES-256-GCM + Kyber768 + Dilithium3)
- **Six Sacred Tongues** for spell-text encoding

This guide covers installation, basic usage, and production deployment.

---

## Quick Install

### Option 1: pip install (recommended)

```bash
pip install scbe-aethermoore
```

### Option 2: From source

```bash
git clone https://github.com/issdandavis/scbe-aethermoore-demo.git
cd scbe-aethermoore-demo
pip install -e .
```

---

## Dependencies

### Required

```
numpy>=1.24.0
scipy>=1.10.0
pycryptodome>=3.19.0
```

### Optional (for real post-quantum crypto)

```
pypqc>=0.0.6          # Real Kyber768 + Dilithium3 (NIST PQC)
```

### Development

```
pytest>=7.0.0
pytest-cov>=4.0.0
```

---

## Minimal Example

```python
from symphonic_cipher.scbe_aethermoore.spiral_seal import SpiralSealSS1

# Create sealer with master secret (32 bytes)
master_secret = b'your-32-byte-secret-key-here!!'  # Use KMS in production!
ss = SpiralSealSS1(master_secret=master_secret, kid='k01')

# Seal (encrypt) data
plaintext = b"API_KEY=sk-abc123xyz"
aad = "service=openai;env=prod"
sealed = ss.seal(plaintext, aad=aad)
print(sealed)
# Output: SS1|kid=k01|aad=service=openai;env=prod|salt=ru:...|nonce=ko:...|ct=ca:...|tag=dr:...

# Unseal (decrypt) data
recovered = ss.unseal(sealed, aad=aad)
assert recovered == plaintext
```

---

## Post-Quantum Mode

For quantum-resistant encryption, install `pypqc` and use hybrid mode:

```bash
pip install pypqc
```

```python
from symphonic_cipher.scbe_aethermoore.spiral_seal import SpiralSealSS1

# Hybrid mode: Kyber768 + AES-256-GCM
ss = SpiralSealSS1(
    master_secret=master_secret,
    kid='k01',
    mode='hybrid'  # Enables Kyber768 key encapsulation
)

# Seal with signature
sealed = ss.seal(plaintext, aad=aad, sign=True)

# Check PQC status
status = ss.get_status()
print(status['key_exchange']['backend'])  # 'pypqc' or 'fallback'
```

---

## Risk Governance

Use the 14-layer pipeline for AI safety decisions:

```python
from symphonic_cipher.scbe_aethermoore import constants
from symphonic_cipher.scbe_aethermoore.axiom_grouped import (
    LanguesMetric, HyperspacePoint
)

# Create governance metric
metric = LanguesMetric()

# Evaluate a context point
point = HyperspacePoint(trust=0.7, risk=0.3)
L = metric.compute(point)
risk_level, decision = metric.risk_level(L)

print(f"Risk: {risk_level}, Decision: {decision}")
# Output: Risk: LOW, Decision: ALLOW
```

---

## Environment Variables

Configure via environment for production:

| Variable               | Default     | Description                       |
| ---------------------- | ----------- | --------------------------------- |
| `SCBE_MASTER_SECRET`   | (none)      | 32-byte hex-encoded master secret |
| `SCBE_KID`             | `k01`       | Key identifier for rotation       |
| `SCBE_MODE`            | `symmetric` | `symmetric` or `hybrid`           |
| `SCBE_METRICS_BACKEND` | `stdout`    | `stdout`, `prometheus`, `datadog` |

```bash
export SCBE_MASTER_SECRET=$(openssl rand -hex 32)
export SCBE_MODE=hybrid
```

---

## Verify Installation

Run the test suite to verify everything works:

```bash
# Quick verification
python -c "from symphonic_cipher.scbe_aethermoore.spiral_seal import SpiralSealSS1; print('OK')"

# Full test suite (250 tests)
pytest tests/test_scbe_comprehensive.py tests/test_industry_grade.py -v
```

---

## PQC Backend Status

Check which cryptographic backend is active:

```python
from symphonic_cipher.scbe_aethermoore.spiral_seal.key_exchange import get_pqc_status
from symphonic_cipher.scbe_aethermoore.spiral_seal.signatures import get_pqc_sig_status

print(get_pqc_status())
# {'available': True, 'backend': 'pypqc', 'algorithm': 'Kyber768', ...}

print(get_pqc_sig_status())
# {'available': True, 'backend': 'pypqc', 'algorithm': 'Dilithium3', ...}
```

**Warning**: If backend shows `fallback`, you're using classical crypto simulation. Install `pypqc` for real post-quantum security.

---

## Production Checklist

Before deploying to production:

- [ ] **Master secret from KMS** - Never hardcode secrets
- [ ] **Real PQC backend** - `pip install pypqc`
- [ ] **AAD binding** - Always include context in AAD
- [ ] **Key rotation** - Configure rotation policy
- [ ] **Metrics enabled** - Set `SCBE_METRICS_BACKEND`
- [ ] **Tests passing** - Run full test suite

---

## API Reference

### SpiralSealSS1

| Method                            | Description                        |
| --------------------------------- | ---------------------------------- |
| `seal(plaintext, aad, sign)`      | Encrypt and return SS1 blob        |
| `unseal(blob, aad, verify_sig)`   | Decrypt SS1 blob                   |
| `sign(message)`                   | Dilithium3 signature (hybrid mode) |
| `verify(message, signature)`      | Verify signature                   |
| `rotate_key(new_kid, new_secret)` | Rotate master secret               |
| `get_status()`                    | Get crypto backend status          |

### LanguesMetric

| Method           | Description                 |
| ---------------- | --------------------------- |
| `compute(point)` | Compute Langues metric L    |
| `risk_level(L)`  | Get risk level and decision |

---

## Troubleshooting

### "No cryptographic backend available"

```bash
pip install pycryptodome
# or
pip install cryptography
```

### "Using classical fallback"

```bash
pip install pypqc
```

### Import errors

```bash
pip install -e .  # Reinstall in editable mode
```

---

## Next Steps

- [SPIRALSEAL_SS1_COMPLETE.md](SPIRALSEAL_SS1_COMPLETE.md) - Full SS1 specification
- [COMPREHENSIVE_MATH_SCBE.md](COMPREHENSIVE_MATH_SCBE.md) - Mathematical foundations
- [Production Readiness](../src/.kiro/specs/production-readiness/requirements.md) - Production gaps

---

_SCBE-AETHERMOORE: Post-quantum AI safety infrastructure._
