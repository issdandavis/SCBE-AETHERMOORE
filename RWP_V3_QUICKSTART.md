# RWP v3.0 Quick Start Guide

**Version**: 3.0.0  
**Date**: January 18, 2026  
**Status**: Production-Ready (Python)

---

## Installation

### 1. Install Python Dependencies

```bash
# Core dependencies (required)
pip install argon2-cffi pycryptodome numpy

# Post-quantum cryptography (optional, for ML-KEM-768 + ML-DSA-65)
pip install liboqs-python

# Spectral analysis (optional, for Layer 9 validation)
pip install scipy
```

### 2. Verify Installation

```bash
python examples/rwp_v3_demo.py
```

Expected output:
```
╔══════════════════════════════════════════════════════════════════════╗
║              RWP v3.0 Complete Demo - Mars Communication            ║
╚══════════════════════════════════════════════════════════════════════╝

✅ Demo 1: Basic RWP v3.0 encryption
✅ Demo 2: Hybrid PQC encryption
✅ Demo 3: Spectral validation
✅ Demo 4: Authentication failure
✅ Demo 5: Bijectivity test

🎉 All Demos Complete!
```

---

## Quick Examples

### Example 1: Basic Encryption

```python
from src.crypto.rwp_v3 import rwp_encrypt_message, rwp_decrypt_message

# Encrypt
envelope = rwp_encrypt_message(
    password="my-secret-password",
    message="Hello, Mars!",
    metadata={"timestamp": "2026-01-18T17:21:00Z"},
    enable_pqc=False
)

# Decrypt
message = rwp_decrypt_message(
    password="my-secret-password",
    envelope_dict=envelope,
    enable_pqc=False
)

print(message)  # "Hello, Mars!"
```

### Example 2: Post-Quantum Encryption

```python
from src.crypto.rwp_v3 import RWPv3Protocol

# Initialize with PQC
protocol = RWPv3Protocol(enable_pqc=True)

# Generate ML-KEM-768 keypair
public_key = protocol.kem.generate_keypair()
secret_key = protocol.kem.export_secret_key()

# Encrypt with PQC
envelope = protocol.encrypt(
    password=b"my-password",
    plaintext=b"Classified message",
    ml_kem_public_key=public_key
)

# Decrypt with PQC
plaintext = protocol.decrypt(
    password=b"my-password",
    envelope=envelope,
    ml_kem_secret_key=secret_key
)

print(plaintext.decode())  # "Classified message"
```

### Example 3: Sacred Tongue Tokens

```python
from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER

tokenizer = SACRED_TONGUE_TOKENIZER

# Encode bytes to Sacred Tongue tokens
data = b"Hello, Mars!"
tokens = tokenizer.encode_section('ct', data)  # Cassisivadan (ciphertext)

print(tokens[:3])  # ['bip\'a', 'ifta\'i', 'loopa\'o']

# Decode tokens back to bytes
decoded = tokenizer.decode_section('ct', tokens)
print(decoded)  # b"Hello, Mars!"
```

---

## Sacred Tongues Reference

| Tongue | Code | Domain | Frequency | Use Case |
|--------|------|--------|-----------|----------|
| Kor'aelin | `ko` | Nonce/Intent | 440.0 Hz | Flow control |
| Avali | `av` | AAD/Metadata | 523.25 Hz | Headers |
| Runethic | `ru` | Salt/Binding | 329.63 Hz | Key derivation |
| Cassisivadan | `ca` | Ciphertext | 659.25 Hz | Encrypted data |
| Umbroth | `um` | Redaction | 293.66 Hz | Concealment |
| Draumric | `dr` | Tag/Structure | 392.0 Hz | Authentication |

---

## Security Parameters

### Argon2id KDF (RFC 9106)

```python
ARGON2_PARAMS = {
    'time_cost': 3,        # 3 iterations (~0.5s on modern CPU)
    'memory_cost': 65536,  # 64 MB memory
    'parallelism': 4,      # 4 threads
    'hash_len': 32,        # 256-bit key output
    'salt_len': 16,        # 128-bit salt
    'type': Argon2Type.ID, # Argon2id (hybrid mode)
}
```

### Post-Quantum Cryptography

- **ML-KEM-768** (Kyber768): Quantum-resistant key exchange
  - Security level: NIST Level 3 (192-bit classical security)
  - Public key: 1184 bytes
  - Ciphertext: 1088 bytes

- **ML-DSA-65** (Dilithium3): Quantum-resistant signatures
  - Security level: NIST Level 3 (192-bit classical security)
  - Public key: 1952 bytes
  - Signature: 3293 bytes

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Encrypt (no PQC) | <10ms | Argon2id overhead |
| Decrypt (no PQC) | <5ms | Argon2id overhead |
| Encrypt (with PQC) | <50ms | ML-KEM encapsulation |
| Decrypt (with PQC) | <30ms | ML-KEM decapsulation |
| Token encoding | <1ms | Constant-time lookup |
| Token decoding | <1ms | Constant-time lookup |
| Spectral fingerprint | <2ms | SHA-256 + multiply |
| Throughput | 1000+ env/s | Parallel processing |

---

## API Reference

### High-Level API

```python
# Encrypt message
envelope = rwp_encrypt_message(
    password: str,
    message: str,
    metadata: Optional[Dict] = None,
    enable_pqc: bool = False
) -> Dict

# Decrypt message
message = rwp_decrypt_message(
    password: str,
    envelope_dict: Dict,
    enable_pqc: bool = False
) -> str
```

### Low-Level API

```python
# Initialize protocol
protocol = RWPv3Protocol(enable_pqc: bool = False)

# Encrypt
envelope = protocol.encrypt(
    password: bytes,
    plaintext: bytes,
    aad: bytes = b'',
    ml_kem_public_key: Optional[bytes] = None,
    ml_dsa_private_key: Optional[bytes] = None
) -> RWPEnvelope

# Decrypt
plaintext = protocol.decrypt(
    password: bytes,
    envelope: RWPEnvelope,
    ml_kem_secret_key: Optional[bytes] = None,
    ml_dsa_public_key: Optional[bytes] = None
) -> bytes
```

### Sacred Tongue API

```python
# Initialize tokenizer
tokenizer = SacredTongueTokenizer()

# Encode bytes to tokens
tokens = tokenizer.encode_section(
    section: str,  # 'aad', 'salt', 'nonce', 'ct', 'tag', 'redact'
    data: bytes
) -> List[str]

# Decode tokens to bytes
data = tokenizer.decode_section(
    section: str,
    tokens: List[str]
) -> bytes

# Compute harmonic fingerprint
fingerprint = tokenizer.compute_harmonic_fingerprint(
    tongue_code: str,  # 'ko', 'av', 'ru', 'ca', 'um', 'dr'
    tokens: List[str]
) -> float

# Validate section integrity
is_valid = tokenizer.validate_section_integrity(
    section: str,
    tokens: List[str]
) -> bool
```

---

## Testing

### Run All Tests

```bash
# Unit tests
python -m pytest tests/crypto/ -v

# Property-based tests (100 iterations)
python -m pytest tests/crypto/test_rwp_v3_properties.py -v

# Integration tests
python -m pytest tests/integration/ -v

# Benchmarks
python -m pytest tests/crypto/ -v --benchmark
```

### Run Demos

```bash
# All demos
python examples/rwp_v3_demo.py

# Specific demo
python -c "from examples.rwp_v3_demo import demo_basic_encryption; demo_basic_encryption()"
```

---

## Troubleshooting

### Issue: `ImportError: No module named 'argon2'`

**Solution**:
```bash
pip install argon2-cffi
```

### Issue: `ImportError: No module named 'Crypto'`

**Solution**:
```bash
pip install pycryptodome
```

### Issue: `ImportError: No module named 'oqs'`

**Solution** (optional, for PQC):
```bash
pip install liboqs-python
```

If installation fails, PQC features will be disabled but basic encryption still works.

### Issue: `ValueError: AEAD authentication failed`

**Cause**: Wrong password or tampered envelope

**Solution**: Verify password is correct and envelope hasn't been modified

### Issue: `ValueError: ML-DSA-65 signature verification failed`

**Cause**: Signature doesn't match or wrong public key

**Solution**: Verify public key matches the private key used for signing

---

## Next Steps

1. **Read the docs**: `.kiro/specs/rwp-v2-integration/`
2. **Run the demos**: `python examples/rwp_v3_demo.py`
3. **Write tests**: See `tests/crypto/` for examples
4. **Integrate with SCBE**: See `.kiro/specs/rwp-v2-integration/IMPLEMENTATION_NOTES.md`
5. **Deploy to AWS Lambda**: See `docs/AWS_LAMBDA_DEPLOYMENT.md`

---

## Resources

- **Requirements**: `.kiro/specs/rwp-v2-integration/requirements.md`
- **Implementation Notes**: `.kiro/specs/rwp-v2-integration/IMPLEMENTATION_NOTES.md`
- **Upgrade Summary**: `.kiro/specs/rwp-v2-integration/RWP_V3_UPGRADE.md`
- **Demo Script**: `examples/rwp_v3_demo.py`
- **Source Code**: `src/crypto/rwp_v3.py`, `src/crypto/sacred_tongues.py`

---

## Support

- **GitHub**: https://github.com/issdandavis/scbe-aethermoore-demo
- **Email**: issdandavis@gmail.com
- **Patent**: USPTO #63/961,403

---

**Last Updated**: January 18, 2026  
**Version**: 3.0.0  
**Status**: Production-Ready (Python)

🛡️ **Quantum-resistant. Context-bound. Mars-ready.**
