# Technology Stack & Build System

## Core Technologies

### TypeScript (Cryptographic Envelope)

- **Language**: TypeScript with ES modules (`.js` extensions in imports)
- **Runtime**: Node.js (uses `node:crypto`, `node:perf_hooks`)
- **Cryptography**: Native Node.js crypto module (AES-256-GCM, SHA-256, HMAC, HKDF)
- **Testing**: Jest/Vitest with `test()` syntax

### Python (Mathematical Core)

- **Language**: Python 3.11+
- **Libraries**: NumPy, SciPy (for Hilbert transform)
- **Mathematical**: Hyperbolic geometry, Poincaré ball operations, FFT

## Key Libraries & Patterns

- **Cryptographic Operations**: Node.js native crypto module
- **Hyperbolic Geometry**: Custom implementation of Möbius addition, breathing transforms
- **Metrics**: Pluggable backends (stdout, datadog, prometheus, OTLP)
- **Error Handling**: "Fail-to-noise" policy with opaque error messages

## Environment Variables

All configuration uses `SCBE_*` prefix:

- `SCBE_KMS_KID`: Key identifier (default: 'key-v1')
- `SCBE_ENV`: Environment (default: 'prod')
- `SCBE_PROVIDER_ID`: Provider identifier
- `SCBE_MODEL_ID`: Model identifier
- `SCBE_METRICS_BACKEND`: Metrics backend (default: 'stdout')

## Common Commands

```bash
# TypeScript tests
npm test
npm test -- acceptance.tamper.test.ts

# Python axiom compliance
python src/scbe_cpse_unified.py

# Type check
npx tsc --noEmit

# Run example
node examples/usage.js
```

## Code Style

### TypeScript

- Use async/await for cryptographic operations
- Import with `.js` extensions for ES modules
- Prefer `Buffer` over `Uint8Array` for crypto

### Python

- Type hints for all functions
- Dataclasses for configuration
- NumPy arrays for vector operations
- Axiom compliance comments (e.g., `# A4: Clamping`)
