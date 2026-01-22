# SCBE-AETHERMOORE Project Structure

> **File Tag System**: All source files include a header with `@layer`, `@module`, and `@component` tags for navigation.

---

## Directory Layout

```
scbe-aethermoore-demo/
├── src/                          # Source code
│   ├── api/                      # REST API (FastAPI)
│   ├── crypto/                   # Cryptographic primitives
│   ├── fleet/                    # Fleet orchestration (Redis/BullMQ)
│   ├── harmonic/                 # 14-Layer Pipeline (CORE)
│   ├── network/                  # Network security (SpaceTor, Combat routing)
│   ├── physics_sim/              # Physics simulation
│   ├── spectral/                 # Spectral coherence
│   ├── spiralverse/              # Spiralverse protocol
│   ├── symphonic/                # Symphonic cipher (TypeScript)
│   └── symphonic_cipher/         # Symphonic cipher (Python)
│
├── tests/                        # Test suites (728+ tests)
│   ├── harmonic/                 # Layer tests
│   ├── enterprise/               # Compliance tests
│   ├── network/                  # Network tests
│   └── spiralverse/              # RWP tests
│
├── dashboard/                    # Real-time monitoring UI
├── demos/                        # Demo scripts
├── docs/                         # Documentation
│   ├── images/                   # Architecture diagrams
│   ├── guides/                   # User guides
│   └── reference/                # Technical reference
│
├── scripts/                      # Build & deployment scripts
│   ├── windows/                  # Windows batch files
│   └── unix/                     # Unix shell scripts
│
├── config/                       # Configuration files
└── .github/workflows/            # CI/CD pipelines
```

---

## 14-Layer Pipeline Reference

| Layer | File | Function | Description |
|-------|------|----------|-------------|
| **Layer 1** | `src/harmonic/pipeline14.ts` | `layer1ComplexState` | Context → Complex vector (amplitude + phase) |
| **Layer 2** | `src/harmonic/pipeline14.ts` | `layer2Realification` | ℂᴰ → ℝ²ᴰ isometric embedding |
| **Layer 3** | `src/harmonic/pipeline14.ts` | `layer3WeightedTransform` | SPD metric weighting (φ^k) |
| **Layer 4** | `src/harmonic/pipeline14.ts` | `layer4PoincareEmbedding` | Map to Poincaré ball (‖u‖ < 1) |
| **Layer 5** | `src/harmonic/hyperbolic.ts` | `hyperbolicDistance` | d_ℍ(u,v) via arcosh formula |
| **Layer 6** | `src/harmonic/pipeline14.ts` | `layer6BreathingTransform` | Temporal modulation (diffeomorphism) |
| **Layer 7** | `src/harmonic/hyperbolic.ts` | `mobiusAddition` | Möbius isometry (gyrovector) |
| **Layer 8** | `src/harmonic/pipeline14.ts` | `layer8RealmDistance` | Min distance to trusted realm centers |
| **Layer 9** | `src/harmonic/pipeline14.ts` | `layer9SpectralCoherence` | FFT-based pattern stability |
| **Layer 10** | `src/harmonic/pipeline14.ts` | `layer10SpinCoherence` | Phase alignment measure |
| **Layer 11** | `src/harmonic/pipeline14.ts` | `layer11TriadicTemporal` | Multi-timescale aggregation |
| **Layer 12** | `src/harmonic/harmonicScaling.ts` | `harmonicScale` | Risk amplifier: H(d,R) = φᵈ / (1 + e⁻ᴿ) |
| **Layer 13** | `src/harmonic/pipeline14.ts` | `layer13RiskDecision` | ALLOW / QUARANTINE / DENY |
| **Layer 14** | `src/harmonic/audioAxis.ts` | `computeAudioAxisFeatures` | Hilbert transform telemetry |

---

## Key Components

### Core Engine (`src/harmonic/`)
- `pipeline14.ts` - Complete 14-layer pipeline
- `hyperbolic.ts` - Poincaré ball operations
- `harmonicScaling.ts` - Risk amplification
- `sacredTongues.ts` - 6×256 vocabulary tokenizer
- `phdm.ts` - Poincaré Half-plane Drift Monitor

### Cryptography (`src/crypto/`)
- `envelope.ts` - Sealed envelope (AES-256-GCM)
- `kms.ts` - Key management (HKDF)
- `replayGuard.ts` - Nonce/Bloom filter protection
- `pqc.ts` - Post-quantum (ML-KEM-768, ML-DSA-65)

### Fleet Management (`src/fleet/`)
- `redis-orchestrator.ts` - Multi-agent coordination
- `index.ts` - Fleet exports

### API (`src/api/`)
- `main.py` - FastAPI server (6 endpoints)
- WebSocket `/ws/dashboard` for real-time streaming

---

## File Tag Convention

All source files should include a header block:

```typescript
/**
 * @file hyperbolic.ts
 * @module harmonic/hyperbolic
 * @layer Layer 5, Layer 7
 * @component Poincaré Ball Operations
 * @version 3.0.0
 */
```

```python
"""
@file: main.py
@module: api
@component: REST API Server
@version: 3.0.0
"""
```

---

## Test Categories

| Category | Directory | Tests | Coverage |
|----------|-----------|-------|----------|
| Hyperbolic Geometry | `tests/harmonic/` | ~180 | Poincaré, Möbius, boundaries |
| Harmonic Pipeline | `tests/harmonic/` | ~120 | 14-layer, scaling, CFI |
| Enterprise Compliance | `tests/enterprise/` | ~100 | FIPS 140-3, SOC 2 |
| Spectral Coherence | `tests/spectral/` | ~80 | FFT, phase alignment |
| Network Security | `tests/network/` | ~70 | Combat routing, trust |
| Crypto & Envelope | `tests/` | ~60 | Nonce, tamper detection |
| Integration | `tests/spiralverse/` | ~82 | RWP policy, acceptance |

---

## Quick Commands

```bash
# Run all tests
npm test

# Run specific layer tests
npm test -- tests/harmonic/hyperbolic.test.ts

# Run Python demo
python demo_memory_shard.py

# Start API server
python -m uvicorn src.api.main:app --reload

# Build TypeScript
npm run build

# Generate proof pack
./scripts/make_proof_pack.sh
```

---

_Last updated: January 2026_
