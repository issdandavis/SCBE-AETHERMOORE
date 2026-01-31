# SCBE Secure Bank Demo

A visual demonstration of the SCBE-AETHERMOORE 14-layer security system protecting financial transactions.

## What This Shows

1. **Real-time Security Visualization** - Watch all 14 security layers process each transaction
2. **Encrypted Envelopes** - See the AES-256-GCM encrypted data with signatures
3. **Attack Simulation** - Click "Simulate Hacker Attack" to see the system block threats

## How to Run

### Option 1: Open Directly
Just open `demo/index.html` in any web browser.

### Option 2: With a Server
```bash
# Using Python
cd demo && python -m http.server 8080

# Using Node
npx serve demo
```

Then visit: http://localhost:8080

## Features Demonstrated

| Feature | How It's Shown |
|---------|----------------|
| 14-Layer Pipeline | Each layer lights up green as it processes |
| Hyperbolic Geometry | Layers 4-7 show Poincare ball operations |
| Post-Quantum Ready | Envelope shows multi-signature structure |
| Replay Protection | Attack simulation shows nonce detection |
| Tamper Detection | Attack simulation shows spectral analysis |

## For Buyers/Investors

This demo shows a simplified visualization of the actual SCBE security system. The real implementation includes:

- **63,000+ lines** of production code
- **1,150+ automated tests** (98% pass rate)
- **Post-quantum cryptography** (ML-KEM-768, ML-DSA-65)
- **Patent-pending** hyperbolic geometry approach

Contact: [Your contact info here]
