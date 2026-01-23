# SCBE-AETHERMOORE Quick Start Guide

## Installation

### TypeScript/Node.js

```bash
npm install @scbe/aethermoore
```

### Python

```bash
pip install -e .
```

## TypeScript Examples

### 1. Hyperbolic Distance Calculation

```typescript
import { HyperbolicPoint, poincareDistance } from '@scbe/aethermoore/harmonic';

// Create points in Poincaré ball (must satisfy ||p|| < 1)
const p1: HyperbolicPoint = { x: 0.5, y: 0.3, z: 0.1 };
const p2: HyperbolicPoint = { x: 0.2, y: 0.4, z: 0.2 };

// Calculate hyperbolic distance
const distance = poincareDistance(p1, p2);
console.log(`Hyperbolic distance: ${distance}`);
```

### 2. Harmonic Scaling

```typescript
import { harmonicScale } from '@scbe/aethermoore/harmonic';

// Calculate harmonic scaling: H(d,R) = R^(d²)
const dimension = 6;
const baseRisk = 1.5;
const scaledRisk = harmonicScale(dimension, baseRisk);

console.log(`Harmonic scaling H(${dimension}, ${baseRisk}) = ${scaledRisk}`);
// Output: ~2.18×10⁶
```

### 3. Envelope Encryption

```typescript
import { encrypt, decrypt } from '@scbe/aethermoore/crypto';

const plaintext = 'Sensitive data';
const key = 'my-secret-key';

// Encrypt
const ciphertext = await encrypt(plaintext, key);
console.log(`Encrypted: ${ciphertext}`);

// Decrypt
const decrypted = await decrypt(ciphertext, key);
console.log(`Decrypted: ${decrypted}`);
```

### 4. Nonce Management

```typescript
import { NonceManager } from '@scbe/aethermoore/crypto';

const nonceManager = new NonceManager();

// Generate nonce
const nonce = nonceManager.generate();
console.log(`Nonce: ${nonce}`);

// Validate nonce (prevents replay attacks)
const isValid = nonceManager.validate(nonce);
console.log(`Valid: ${isValid}`); // true first time, false on replay
```

### 5. Circuit Breaker Pattern

```typescript
import { CircuitBreaker } from '@scbe/aethermoore/rollout';

const breaker = new CircuitBreaker({
  failureThreshold: 5,
  resetTimeout: 60000, // 1 minute
});

async function riskyOperation() {
  return breaker.execute(async () => {
    // Your operation here
    const response = await fetch('https://api.example.com/data');
    return response.json();
  });
}

try {
  const result = await riskyOperation();
  console.log('Success:', result);
} catch (error) {
  console.error('Circuit breaker opened:', error);
}
```

## Python Examples

### 1. Symphonic Cipher Signing

```python
from symphonic_cipher.core import SymphonicCipher

# Initialize cipher
cipher = SymphonicCipher()

# Sign transaction intent
intent = '{"amount": 500, "to": "0x123..."}'
signature = cipher.sign(intent, key="my-secret-key")
print(f"Signature: {signature}")

# Verify signature
is_valid = cipher.verify(intent, signature, key="my-secret-key")
print(f"Valid: {is_valid}")
```

### 2. Harmonic Scaling Law

```python
from symphonic_cipher.harmonic_scaling_law import harmonic_scale

# Calculate H(d,R) = R^(d²)
dimension = 6
base_risk = 1.5
scaled = harmonic_scale(dimension, base_risk)

print(f"H({dimension}, {base_risk}) = {scaled:.2e}")
# Output: ~2.18e+06
```

### 3. Dual Lattice Consensus

```python
from symphonic_cipher.dual_lattice_consensus import DualLatticeConsensus

# Initialize consensus system
consensus = DualLatticeConsensus(num_nodes=3)

# Submit transaction
tx = {"amount": 100, "to": "0xabc"}
result = consensus.submit_transaction(tx)

print(f"Consensus reached: {result['consensus']}")
print(f"Signatures: {result['signatures']}")
```

### 4. Topological CFI (Control Flow Integrity)

```python
from symphonic_cipher.topological_cfi import TopologicalCFI

# Initialize CFI
cfi = TopologicalCFI()

# Define control flow graph
cfi.add_edge("start", "process")
cfi.add_edge("process", "validate")
cfi.add_edge("validate", "end")

# Validate execution path
path = ["start", "process", "validate", "end"]
is_valid = cfi.validate_path(path)

print(f"Path valid: {is_valid}")
```

### 5. Flat Slope Encoder

```python
from symphonic_cipher.flat_slope_encoder import FlatSlopeEncoder

# Initialize encoder
encoder = FlatSlopeEncoder()

# Encode data with flat slope property
data = b"Hello, SCBE!"
encoded = encoder.encode(data)

print(f"Encoded: {encoded.hex()}")

# Decode
decoded = encoder.decode(encoded)
print(f"Decoded: {decoded.decode()}")
```

## Cross-Language Integration

### TypeScript → Python

```typescript
// TypeScript: Generate hyperbolic point
import { HyperbolicPoint } from '@scbe/aethermoore/harmonic';

const point: HyperbolicPoint = { x: 0.5, y: 0.3, z: 0.1 };
console.log(JSON.stringify(point));
// Output: {"x":0.5,"y":0.3,"z":0.1}
```

```python
# Python: Use the point
import json

point_json = '{"x":0.5,"y":0.3,"z":0.1}'
point = json.loads(point_json)

# Use in SCBE calculations
from symphonic_cipher.core import calculate_risk
risk = calculate_risk(point)
print(f"Risk: {risk}")
```

## Running Tests

### TypeScript

```bash
npm test
```

### Python

```bash
pytest tests/ -v
```

### All Tests

```bash
npm run test:all
```

## Next Steps

1. **Explore Examples**: Check `examples/` directory for more code samples
2. **Read Documentation**: See `docs/` for detailed API reference
3. **Try Demos**: Open `scbe-aethermoore/customer-demo.html` in browser
4. **Review Architecture**: Read `ARCHITECTURE_FOR_PILOTS.md`

## Common Issues

### TypeScript: Module not found

```bash
npm install
npm run build
```

### Python: Import errors

```bash
pip install -e .
# or
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Tests failing

```bash
# Clean and rebuild
npm run clean
npm run build
npm test
```

## Support

- **Issues**: https://github.com/issdandavis/scbe-aethermoore-demo/issues
- **Email**: issdandavis@gmail.com
- **Documentation**: See `docs/` directory

---

**Ready to build secure systems with hyperbolic geometry!** 🌌🔐
