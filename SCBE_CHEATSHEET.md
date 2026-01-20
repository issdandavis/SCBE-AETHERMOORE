# SCBE-AETHERMOORE Cheat Sheet

Quick reference for using SCBE in your projects.

## 🚀 CLI Commands

```bash
# Start the CLI
scbe

# Available commands
tutorial   # Interactive tutorial (START HERE!)
encrypt    # Encrypt a message
decrypt    # Decrypt a message
attack     # Run attack simulation
metrics    # Display system metrics
help       # Show all commands
exit       # Exit the CLI
```

## 📝 Python Quick Reference

### Basic Encryption

```python
from symphonic_cipher import SymphonicCipher

# Initialize
cipher = SymphonicCipher()

# Encrypt
ciphertext = cipher.encrypt("Hello, World!", "my-secret-key")

# Decrypt
plaintext = cipher.decrypt(ciphertext, "my-secret-key")
```

### Harmonic Signature

```python
from symphonic_cipher.core import HarmonicSynthesizer

# Create synthesizer
synth = HarmonicSynthesizer()

# Generate harmonic signature
intent = '{"action": "transfer", "amount": 1000}'
signature = synth.synthesize(intent, "my-key")

# Verify signature
is_valid = synth.verify(intent, "my-key", signature)
```

### Feistel Network

```python
from symphonic_cipher.core import FeistelPermutation

# Initialize with 6 rounds
feistel = FeistelPermutation(rounds=6)

# Encrypt data
encrypted = feistel.encrypt(b"secret data", "my-key")

# Decrypt data
decrypted = feistel.decrypt(encrypted, "my-key")
```

## 💻 TypeScript Quick Reference

### Harmonic Scaling

```typescript
import { harmonicScale } from '@scbe/aethermoore/harmonic';

// Calculate harmonic scaling
const distance = 0.5;
const risk = 2.0;
const scaled = harmonicScale(distance, risk);
// Result: risk^(distance²) = 2^0.25 ≈ 1.19
```

### PQC Provider

```typescript
import { PQCProvider } from '@scbe/aethermoore/harmonic';

// Initialize post-quantum crypto
const pqc = new PQCProvider();

// Generate key pair
const { publicKey, privateKey } = pqc.generateKeyPair();

// Encrypt
const ciphertext = pqc.encrypt(publicKey, 'secret message');

// Decrypt
const plaintext = pqc.decrypt(privateKey, ciphertext);
```

### Quasicrystal Lattice

```typescript
import { QCLatticeProvider } from '@scbe/aethermoore/harmonic';

// Initialize lattice
const lattice = new QCLatticeProvider();

// Map point to lattice
const point = [0.5, 0.3, 0.8];
const latticePoint = lattice.mapToLattice(point);

// Verify lattice properties
const isValid = lattice.verifyLatticePoint(latticePoint);
```

## 🔐 Security Best Practices

### Key Management

```python
# ✅ GOOD: Use strong, unique keys
key = "scbe-2026-production-key-a1b2c3d4e5f6"

# ❌ BAD: Weak or reused keys
key = "password123"
```

### Nonce Handling

```python
# ✅ GOOD: Generate unique nonce per message
import secrets
nonce = secrets.token_bytes(16)

# ❌ BAD: Reusing nonces
nonce = b"fixed-nonce"  # NEVER DO THIS!
```

### Error Handling

```python
# ✅ GOOD: Catch and handle errors
try:
    plaintext = cipher.decrypt(ciphertext, key)
except Exception as e:
    print(f"Decryption failed: {e}")
    # Don't reveal key material in errors!

# ❌ BAD: Exposing sensitive info
except Exception as e:
    print(f"Failed with key: {key}")  # NEVER DO THIS!
```

## 📊 Performance Targets

| Operation          | Target | Typical |
| ------------------ | ------ | ------- |
| Encryption         | <1ms   | 0.5ms   |
| Decryption         | <1ms   | 0.5ms   |
| FFT (N=1024)       | <500μs | 300μs   |
| Feistel (6 rounds) | <100μs | 50μs    |
| Signature Gen      | <1ms   | 0.8ms   |
| Signature Verify   | <1ms   | 0.7ms   |

## 🛡️ Security Guarantees

| Attack Type  | Resistance  | Notes                   |
| ------------ | ----------- | ----------------------- |
| Brute Force  | 2^256       | Keyspace too large      |
| Replay       | 100%        | Nonce tracking          |
| MITM         | 100%        | Tag verification        |
| Quantum      | 128-bit PQ  | Post-quantum primitives |
| Side-Channel | Timing-safe | Constant-time ops       |
| Differential | Avalanche   | 1-bit → 50% change      |

## 🎯 Common Use Cases

### Blockchain Transaction Signing

```python
# Sign transaction intent
intent = '{"from": "0x123", "to": "0x456", "amount": 1000}'
signature = cipher.sign(intent, private_key)

# Verify on-chain
is_valid = cipher.verify(intent, public_key, signature)
```

### Secure File Storage

```python
# Encrypt file
with open('secret.txt', 'rb') as f:
    plaintext = f.read()
    ciphertext = cipher.encrypt(plaintext, key)

with open('secret.enc', 'wb') as f:
    f.write(ciphertext)

# Decrypt file
with open('secret.enc', 'rb') as f:
    ciphertext = f.read()
    plaintext = cipher.decrypt(ciphertext, key)
```

### API Authentication

```typescript
// Generate auth token
const token = crypto.generateHarmonicSignature(JSON.stringify({ userId, timestamp }), apiSecret);

// Verify token
const isValid = crypto.verifyHarmonicSignature(
  JSON.stringify({ userId, timestamp }),
  apiSecret,
  token
);
```

## 🔧 Troubleshooting

### "Decryption failed"

- Check that you're using the same key for encrypt/decrypt
- Verify the ciphertext wasn't corrupted
- Ensure you're using the same SCBE version

### "Nonce already used"

- Generate a new nonce for each message
- Don't reuse nonces across sessions

### "Invalid signature"

- Verify the intent string matches exactly
- Check that the key is correct
- Ensure no whitespace differences

### "Performance too slow"

- Check payload size (target: <1KB)
- Verify FFT size is power of 2
- Profile with `metrics` command

## 📚 Learn More

- **Tutorial**: Run `scbe` and type `tutorial`
- **Full Docs**: See `docs/` directory
- **Examples**: Check `examples/` directory
- **Tests**: Run `npm test` or `pytest`

## 🆘 Getting Help

1. Run `scbe` and type `tutorial`
2. Check `QUICKSTART.md`
3. Read `docs/GETTING_STARTED.md`
4. Open an issue on GitHub

---

**Pro Tip**: Start with the CLI tutorial! It's the fastest way to understand SCBE.

```bash
scbe
scbe> tutorial
```
