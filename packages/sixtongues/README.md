# Six Tongues Tokenizer + GeoSeal CLI

> SCBE-AETHERMOORE cryptographic toolkit for conlang tokenization and context-aware sealing.

This is a **self-contained Python CLI** that implements the core of the SCBE-AETHERMOORE system:

- Six Sacred Tongues bijective tokenization (256 tokens per tongue)
- Cross-tongue translation (KO->AV->DR, etc.)
- Blend / unblend of multi-tongue streams
- GeoSeal: context-aware encryption with HEALPix spatial indexing
- Built-in `selftest` for round-trip and integrity checks

Designed for **secure AI-to-AI messaging**, semantic steganography, and post-quantum-ready, context-bound cryptography.

---

## Features

### Six Tongues Tokenizer
- 6 independent conlang "alphabets" (256 tokens each)
- Byte <-> token mapping is **bijective** (no collisions, full coverage)
- Human-readable, LLM-friendly token streams
- Golden ratio weighting per tongue (phi^0 through phi^5)

### Cross-Tongue Translation
- Re-encode a token stream from one tongue to another without touching the underlying bytes
- Example: KO -> AV -> DR, preserving exact payload

### Blend / Unblend
- Interleave multiple tongues according to a pattern (e.g. `KO:2,AV:1,DR:1`)
- Perfectly reversible; preserves byte-exact data

### GeoSeal (Context-Aware Encryption)
- Projects lat/long into HEALPix-style spatial index
- Wraps payloads with context metadata (location, tag, timestamp, TTL)
- HMAC-SHA256 signature verification
- Key derivation using PBKDF2
- PQC hooks ready for Kyber/Dilithium integration

### Self-Test Mode
- Comprehensive verification of all subsystems
- Run with no arguments: `python sixtongues.py`

---

## Installation

**Requirements:**
- Python 3.9+
- numpy

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependency
pip install numpy
```

---

## Quickstart

### 1. Encode bytes into KO tokens

```bash
echo -n "hello" | python sixtongues.py encode --tongue KO
```

### 2. Decode tokens back to bytes

```bash
python sixtongues.py decode --tongue KO "ko'ka ko'ke ko'ki ko'ko ko'ku"
```

### 3. Cross-translate KO -> AV

```bash
echo "ko'ka ko'ke ko'ki" | python sixtongues.py xlate --src KO --dst AV
```

### 4. Blend multi-tongue stream

```bash
echo -n "secret" | python sixtongues.py blend --pattern KO:2,AV:1,DR:1
```

### 5. Unblend back to bytes

```bash
python sixtongues.py unblend --pattern KO:2,AV:1,DR:1 < blended.txt
```

### 6. GeoSeal encrypt

```bash
echo -n "classified" | python sixtongues.py geoseal-encrypt \
  --lat 48.118 --lon -123.430 --tag "demo"
# Key is printed to stderr, envelope to stdout
```

### 7. GeoSeal decrypt

```bash
python sixtongues.py geoseal-decrypt --key <hex-key> --expect-tag "demo" < sealed.json
```

### 8. Run full self-test

```bash
python sixtongues.py
```

Expected output:
```
selftest ok
```

---

## CLI Reference

```
sixtongues.py <command> [options]

Commands:
  encode              Encode bytes to Sacred Tongue tokens
  decode              Decode Sacred Tongue tokens to bytes
  xlate               Translate between tongues
  blend               Blend bytes into multi-tongue stream
  unblend             Unblend multi-tongue stream to bytes
  geoseal-encrypt     Wrap data with GeoSeal envelope
  geoseal-decrypt     Verify and unwrap GeoSeal envelope
  tokens              List token table for a tongue

Run with no command to execute selftest.
```

### encode
```bash
python sixtongues.py encode --tongue {KO,AV,RU,CA,UM,DR} [--text TEXT]
```

### decode
```bash
python sixtongues.py decode --tongue {KO,AV,RU,CA,UM,DR} [tokens]
```

### xlate
```bash
python sixtongues.py xlate --src TONGUE --dst TONGUE [tokens]
```

### blend
```bash
python sixtongues.py blend --pattern "KO:2,AV:1,DR:1" [--text TEXT]
```

### unblend
```bash
python sixtongues.py unblend --pattern "KO:2,AV:1,DR:1" [tokens]
```

### geoseal-encrypt
```bash
python sixtongues.py geoseal-encrypt --lat FLOAT --lon FLOAT [--tag TAG] [--key HEX] [--ttl SECONDS]
```

### geoseal-decrypt
```bash
python sixtongues.py geoseal-decrypt --key HEX [--expect-tag TAG] [--no-expiry-check]
```

### tokens
```bash
python sixtongues.py tokens --tongue {KO,AV,RU,CA,UM,DR}
```

---

## The Six Sacred Tongues

| Tongue | Weight (phi^n) | Character |
|--------|---------------|-----------|
| **KO** | 1.000 | Foundation, stability |
| **AV** | 1.618 | Context, boundaries |
| **RU** | 2.618 | Binding, transformation |
| **CA** | 4.236 | Structure, bitcraft |
| **UM** | 6.854 | Veil, mystery |
| **DR** | 11.090 | Order, dreaming |

Each tongue has 256 unique tokens mapping bijectively to byte values 0-255.

---

## Security Model

**This is prototype cryptographic software.** Treat it as a research and integration tool, not a fully audited production system.

- Tokenization and blending are **exact, reversible transforms**. They do not provide confidentiality by themselves.
- GeoSeal uses HMAC-SHA256 for integrity and PBKDF2 for key derivation. The XOR encryption is a placeholder - production should use AES-GCM.
- PQC hooks (Kyber/Dilithium) are structured in but not yet implemented.

The design is intentionally:
- Deterministic
- Testable (`selftest`)
- Easy to extend with standard crypto libraries

---

## Use Cases

- **Secure AI agent messaging**: Encode payloads into Sacred Tongue tokens, GeoSeal with context
- **Semantic steganography**: Hide bytes in conlang-like tokens instead of hex/base64
- **Post-quantum experimentation**: PQC-ready structure for future ML-KEM/ML-DSA integration
- **Worldbuilding tools**: Generate consistent, reversible in-universe "languages"

---

## License

MIT License. See LICENSE file.

---

## Author

**Issac Daniel Davis**
Port Angeles, Washington, USA
SCBE-AETHERMOORE / Six Sacred Tongues / GeoSeal

Patent Pending: USPTO #63/961,403
