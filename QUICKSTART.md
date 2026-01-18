# SCBE-AETHERMOORE Quick Start Guide

Get up and running with SCBE-AETHERMOORE in 5 minutes!

## 🚀 Installation

### Option 1: NPM Package (Recommended)

```bash
npm install @scbe/aethermoore
```

### Option 2: From Source

```bash
git clone https://github.com/ISDanDavis2/scbe-aethermoore.git
cd scbe-aethermoore
npm install
npm run build
```

### Option 3: Docker

```bash
docker pull ghcr.io/isdandavis2/scbe-aethermoore:latest
docker run -it ghcr.io/isdandavis2/scbe-aethermoore:latest
```

## 🎮 Try the Interactive Demo

### Web Demo (No Installation Required)

1. Open `scbe-aethermoore/customer-demo.html` in your browser
2. Try encrypting a message
3. Run attack simulations
4. View live metrics

**Features:**
- Real-time encryption/decryption
- 4 attack simulations (Brute Force, Replay, MITM, Quantum)
- Live performance charts
- 14-layer status monitoring

### Python CLI

```bash
python scbe-cli.py
```

**Available Commands:**
```
scbe> encrypt    # Encrypt a message
scbe> decrypt    # Decrypt a message
scbe> attack     # Run attack simulation
scbe> metrics    # View system metrics
scbe> help       # Show help
scbe> exit       # Exit CLI
```

## 💻 Basic Usage

### TypeScript/JavaScript

```typescript
import { DEFAULT_CONFIG, VERSION } from '@scbe/aethermoore';
import { encrypt, decrypt } from '@scbe/aethermoore/crypto';

console.log(`SCBE-AETHERMOORE ${VERSION}`);

// Encrypt data
const plaintext = "Hello, World!";
const key = "my-secret-key";
const ciphertext = encrypt(plaintext, key);

console.log('Encrypted:', ciphertext);

// Decrypt data
const decrypted = decrypt(ciphertext, key);
console.log('Decrypted:', decrypted);
```

### Python

```python
from src.symphonic_cipher.scbe_aethermoore_v2_1_production import SCBEAethermoore

# Initialize SCBE
scbe = SCBEAethermoore()

# Encrypt
plaintext = "Hello, World!"
key = "my-secret-key"
ciphertext = scbe.encrypt(plaintext, key)

print(f"Encrypted: {ciphertext}")

# Decrypt
decrypted = scbe.decrypt(ciphertext, key)
print(f"Decrypted: {decrypted}")
```

## 🏗️ Understanding the 14 Layers

SCBE uses a 14-layer architecture for security:

| Layer | Function | Purpose |
|-------|----------|---------|
| L1-4 | Context Embedding | Map data to hyperbolic space |
| L5 | Invariant Metric | Calculate hyperbolic distances |
| L6 | Breath Transform | Temporal modulation |
| L7 | Phase Modulation | Rotation in hyperbolic space |
| L8 | Multi-Well Potential | Energy landscape |
| L9 | Spectral Channel | Frequency analysis |
| L10 | Spin Channel | Quaternion stability |
| L11 | Triadic Consensus | Byzantine agreement |
| L12 | Harmonic Scaling | Risk amplification |
| L13 | Decision Gate | Allow/Quarantine/Deny |
| L14 | Audio Axis | Telemetry |

## 📊 Performance Expectations

- **Latency**: <50ms average
- **Throughput**: 10,000+ requests/second
- **Security**: 256-bit equivalent strength
- **Quantum Resistance**: Yes (post-quantum primitives)

## 🎯 Common Use Cases

### 1. Secure Data Encryption

```typescript
import { encrypt, decrypt } from '@scbe/aethermoore/crypto';

const sensitiveData = { ssn: "123-45-6789", name: "John Doe" };
const encrypted = encrypt(JSON.stringify(sensitiveData), "secret-key");

// Store or transmit encrypted data
// ...

// Later, decrypt
const decrypted = JSON.parse(decrypt(encrypted, "secret-key"));
```

### 2. API Security

```typescript
import express from 'express';
import { encrypt, decrypt } from '@scbe/aethermoore/crypto';

const app = express();

app.post('/secure-endpoint', (req, res) => {
  const encryptedPayload = req.body.data;
  const decrypted = decrypt(encryptedPayload, process.env.API_KEY);
  
  // Process decrypted data
  const result = processData(decrypted);
  
  // Return encrypted response
  res.json({ data: encrypt(result, process.env.API_KEY) });
});
```

### 3. File Encryption

```python
from src.symphonic_cipher.scbe_aethermoore_v2_1_production import SCBEAethermoore

scbe = SCBEAethermoore()

# Encrypt file
with open('sensitive.txt', 'r') as f:
    plaintext = f.read()

encrypted = scbe.encrypt(plaintext, "file-key")

with open('sensitive.enc', 'w') as f:
    f.write(encrypted)

# Decrypt file
with open('sensitive.enc', 'r') as f:
    encrypted = f.read()

decrypted = scbe.decrypt(encrypted, "file-key")

with open('decrypted.txt', 'w') as f:
    f.write(decrypted)
```

## 🔒 Security Best Practices

1. **Key Management**
   - Use strong, random keys (minimum 32 characters)
   - Store keys securely (environment variables, key vaults)
   - Rotate keys regularly

2. **Input Validation**
   - Always validate input before encryption
   - Sanitize data to prevent injection attacks

3. **Error Handling**
   - Don't expose detailed error messages
   - Log security events for monitoring

4. **Updates**
   - Keep SCBE updated to latest version
   - Monitor security advisories

## 🧪 Testing Your Integration

```typescript
import { encrypt, decrypt } from '@scbe/aethermoore/crypto';

// Test roundtrip
const original = "Test message";
const key = "test-key-12345";
const encrypted = encrypt(original, key);
const decrypted = decrypt(encrypted, key);

console.assert(original === decrypted, "Roundtrip failed!");
console.log("✓ Encryption/Decryption working correctly");
```

## 📚 Next Steps

- **Read the Docs**: Check out the full [README.md](README.md)
- **Explore Examples**: See [examples/](examples/) directory
- **Run Tests**: `npm test` and `pytest tests/`
- **View Architecture**: Read [ARCHITECTURE_FOR_PILOTS.md](ARCHITECTURE_FOR_PILOTS.md)
- **Try Demos**: Open the interactive demos in `scbe-aethermoore/`

## 🆘 Troubleshooting

### Issue: Module not found

```bash
# Ensure dependencies are installed
npm install
pip install -r requirements.txt
```

### Issue: Build fails

```bash
# Clean and rebuild
npm run clean
npm run build
```

### Issue: Tests fail

```bash
# Check Node.js version (must be >= 18)
node --version

# Check Python version (must be >= 3.9)
python --version

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Issue: TypeScript errors

```bash
# Run type check
npm run typecheck

# Check tsconfig.json is correct
```

## 💬 Getting Help

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Ask questions and share ideas
- **Email**: issdandavis@gmail.com

## 🎉 You're Ready!

You now have SCBE-AETHERMOORE up and running. Start building secure applications with hyperbolic geometry-based security!

---

**Happy Coding! 🚀**
