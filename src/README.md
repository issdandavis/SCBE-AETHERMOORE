# SCBE-AETHERMOORE

**Post-Quantum Hybrid Encryption with Hyperbolic Geometry for AI Safety**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Features

- **SpiralSeal SS1**: AES-256-GCM + Kyber768 + Dilithium3 hybrid encryption
- **14-Layer Pipeline**: Hyperbolic geometry risk governance (Axioms A1-A12)
- **Six Sacred Tongues**: Spell-text encoding for ciphertext
- **250+ Tests**: HIPAA, NIST, PCI-DSS, GDPR, IEC 62443 compliance

## Quick Start

```bash
pip install scbe-aethermoore
```

```python
from symphonic_cipher.scbe_aethermoore.spiral_seal import SpiralSealSS1

ss = SpiralSealSS1(master_secret=b'32-byte-secret-key-from-kms!!!!', kid='k01')
sealed = ss.seal(b"secret data", aad="context=prod")
plaintext = ss.unseal(sealed, aad="context=prod")
```

## Post-Quantum Security

```bash
pip install scbe-aethermoore[pqc]  # Includes pypqc for real Kyber/Dilithium
```

```python
ss = SpiralSealSS1(master_secret=secret, mode='hybrid')  # Kyber768 + AES-GCM
```

## Documentation

- [Product Quickstart](../docs/PRODUCT_QUICKSTART.md)
- [SpiralSeal implementation](symphonic_cipher/scbe_aethermoore/spiral_seal/)
- [Compressed layer math](../docs/specs/LAYER_MATH_COMPRESSED.md)

## License

MIT License - See LICENSE file.

---

_SCBE-AETHERMOORE: Hyperbolic geometry for AI safety._
