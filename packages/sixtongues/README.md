# SixTongues CLI

**Sacred Tongue Encoding & Encryption Tool**

Part of the SCBE-AETHERMOORE AI Safety Framework.

## Overview

SixTongues provides a command-line interface for encoding binary data using the Six Sacred Tongues - a cryptographic encoding system that transforms bytes into pronounceable, memorable word-tokens.

Each Sacred Tongue has 16 prefixes × 16 suffixes = 256 unique tokens, providing a bijective mapping for all possible byte values.

## The Six Sacred Tongues

| Code | Name | Domain | Harmonic |
|------|------|--------|----------|
| KO | Kor'aelin | Nonce/Flow/Intent | 440 Hz |
| AV | Avali | AAD/Header/Metadata | 523 Hz |
| RU | Runethic | Salt/Binding | 294 Hz |
| CA | Cassisivadan | Ciphertext/Bitcraft | 659 Hz |
| UM | Umbroth | Redaction/Veil | 196 Hz |
| DR | Draumric | Tag/Structure | 392 Hz |

## Installation

```bash
# No installation required - just run the script
python sixtongues.py --help

# Or make it executable
chmod +x sixtongues.py
./sixtongues.py --help
```

## Quick Start

```bash
# Encode a message in Kor'aelin (default)
python sixtongues.py encode -i "Hello"

# Encode in a specific tongue
python sixtongues.py encode -i "Hello" -t ca

# Decode tokens back to text
python sixtongues.py decode -i "sil'ar sil'un sil'an sil'an sil'oth"

# Encrypt a message
python sixtongues.py encrypt -m "Secret message" -p "your-password"

# Decrypt an envelope
python sixtongues.py decrypt -f envelope.json -p "your-password"

# List all tongues
python sixtongues.py list

# Run demo
python sixtongues.py demo
```

## Commands

### encode
Convert input bytes to Sacred Tongue tokens.

```bash
sixtongues encode [-t TONGUE] [-i INPUT | -f FILE | -x HEX] [-o OUTPUT]
```

### decode
Convert Sacred Tongue tokens back to bytes.

```bash
sixtongues decode [-t TONGUE] [-i TOKENS | -f FILE] [-o OUTPUT] [-x]
```

### encrypt
Encrypt a message and output a Sacred Tongue encoded envelope.

```bash
sixtongues encrypt [-m MESSAGE | -f FILE] [-p PASSWORD] [-o OUTPUT]
```

### decrypt
Decrypt a Sacred Tongue encoded envelope.

```bash
sixtongues decrypt [-e ENVELOPE | -f FILE] [-p PASSWORD] [-o OUTPUT]
```

### list
Display information about all Six Sacred Tongues.

```bash
sixtongues list
```

### validate
Validate a custom lexicon JSON file.

```bash
sixtongues validate lexicon.json
```

### demo
Run an interactive demonstration.

```bash
sixtongues demo
```

## Token Format

Each token follows the format: `prefix'suffix`

Example tokens in Kor'aelin:
- `sil'a` (byte 0x00)
- `kor'ae` (byte 0x11)
- `vara'esh` (byte 0xFF)

## Custom Lexicons

You can create custom lexicon files in JSON format:

```json
{
  "version": "1.0.0",
  "tongues": [
    {
      "code": "xx",
      "name": "Custom Tongue",
      "prefixes": ["p0", "p1", "p2", ..., "p15"],
      "suffixes": ["s0", "s1", "s2", ..., "s15"],
      "domain": "custom/purpose",
      "harmonicFrequency": 432.0
    }
  ]
}
```

Validate with: `sixtongues validate your-lexicon.json`

## Security Notes

The built-in encryption in this CLI is a **demonstration implementation** using simple XOR with PBKDF2. For production use, integrate with:

- **RWP v3 Protocol**: XChaCha20-Poly1305 + Argon2id
- **ML-KEM-768**: Post-quantum key encapsulation
- **ML-DSA-65**: Post-quantum signatures

See the full SCBE-AETHERMOORE framework for production-grade cryptography.

## License

MIT License - See LICENSE file for details.

## Links

- GitHub: https://github.com/anthropics/scbe-aethermoore
- Documentation: https://scbe-aethermoore.readthedocs.io
- npm Package: @scbe/aethermoore
