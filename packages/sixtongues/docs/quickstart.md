# SixTongues Quickstart Guide

Welcome to SixTongues - the Sacred Tongue encoding system for cryptographic data.

## What is SixTongues?

SixTongues transforms binary data into pronounceable word-tokens using six mystical languages. Each byte (0-255) maps to a unique word in each tongue.

**Example**: The byte `0x48` (letter 'H') becomes:
- Kor'aelin: `keth'ar`
- Avali: `oriel'la`
- Cassisivadan: `ifta'ta`

## 5-Minute Tutorial

### Step 1: Test the Installation

```bash
python sixtongues.py --version
# Output: sixtongues 1.0.0
```

### Step 2: Encode Your First Message

```bash
python sixtongues.py encode -i "Hi"
# Output: sil'ar sil'un
```

This encodes "Hi" (bytes 0x48, 0x69) into Kor'aelin tokens.

### Step 3: Decode It Back

```bash
python sixtongues.py decode -i "sil'ar sil'un"
# Output: Hi
```

### Step 4: Try Different Tongues

```bash
# Avali (diplomatic tongue)
python sixtongues.py encode -i "Hi" -t av
# Output: oriel'la maren'na

# Cassisivadan (mathematical tongue)
python sixtongues.py encode -i "Hi" -t ca
# Output: ifta'ta loopa'sa
```

### Step 5: Encrypt a Secret Message

```bash
python sixtongues.py encrypt -m "My secret" -p "password123"
```

Output:
```json
{
  "version": "sixtongues-1.0",
  "nonce": "vel'ae zar'ia ...",
  "salt": "khar'ak drath'eth ...",
  "ct": "bip'a bop'e ...",
  "tag": "anvil'a tharn'e ..."
}
```

Notice each section uses a different tongue:
- **nonce** → Kor'aelin (flow/intent)
- **salt** → Runethic (binding)
- **ct** → Cassisivadan (ciphertext)
- **tag** → Draumric (structure)

### Step 6: Decrypt the Message

Save the envelope to a file, then:

```bash
python sixtongues.py decrypt -f envelope.json -p "password123"
# Output: My secret
```

## The Six Sacred Tongues

| Tongue | Domain | Character |
|--------|--------|-----------|
| **Kor'aelin** | Nonces, intent | Flowing, commanding |
| **Avali** | Headers, metadata | Diplomatic, resonant |
| **Runethic** | Salts, bindings | Ancient, permanent |
| **Cassisivadan** | Ciphertext | Mathematical, rhythmic |
| **Umbroth** | Redactions | Shadowy, veiled |
| **Draumric** | Auth tags | Forged, structural |

View all tongues:
```bash
python sixtongues.py list
```

## Common Use Cases

### Encode a File

```bash
python sixtongues.py encode -f secret.bin -o encoded.txt
```

### Decode to File

```bash
python sixtongues.py decode -f encoded.txt -o recovered.bin
```

### Pipe from/to Commands

```bash
echo "Hello" | python sixtongues.py encode
# Output: sil'ar sil'un sil'an sil'an sil'oth

cat tokens.txt | python sixtongues.py decode
```

### Validate Custom Lexicon

```bash
python sixtongues.py validate my-custom-lexicon.json
```

## Token Anatomy

Each token has the format: `prefix'suffix`

- **Prefix**: 4-bit high nibble (0-15) → 16 choices
- **Suffix**: 4-bit low nibble (0-15) → 16 choices
- **Total**: 16 × 16 = 256 unique tokens per tongue

The apostrophe `'` acts as the morpheme seam between prefix and suffix.

## Interactive Demo

Run the built-in demo to see all features:

```bash
python sixtongues.py demo
```

## Next Steps

1. **Custom Lexicons**: Create your own tongues with custom vocabularies
2. **RWP v3 Integration**: Use with the full SCBE-AETHERMOORE framework
3. **Post-Quantum**: Upgrade to ML-KEM-768 for quantum-safe encryption

## Getting Help

```bash
python sixtongues.py --help
python sixtongues.py encode --help
python sixtongues.py encrypt --help
```

## Links

- Full Documentation: https://scbe-aethermoore.readthedocs.io
- GitHub: https://github.com/anthropics/scbe-aethermoore
- npm: `npm install @scbe/aethermoore`

---

*May your tokens speak true. - The Sacred Tongue Keepers*
