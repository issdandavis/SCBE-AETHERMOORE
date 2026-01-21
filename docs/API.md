# SCBE-AETHERMOORE API Reference

> Complete API documentation for the Spectral Context-Bound Encryption framework

[![npm version](https://img.shields.io/npm/v/scbe-aethermoore.svg)](https://www.npmjs.com/package/scbe-aethermoore)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Patent Pending](https://img.shields.io/badge/Patent-Pending-blue.svg)](./PATENT_PROVISIONAL_APPLICATION.md)

## Installation

### npm (TypeScript/JavaScript)
```bash
npm install scbe-aethermoore
```

### pip (Python)
```bash
pip install -r requirements.txt
```

### From Source
```bash
git clone https://github.com/ISDanDavis2/scbe-aethermoore.git
cd scbe-aethermoore
npm install && pip install -r requirements.txt
```

---

## Quick Start

### TypeScript
```typescript
import { SCBE14LayerPipeline, TrustManager, SpiralSeal } from 'scbe-aethermoore';

// Initialize the 14-layer pipeline
const pipeline = new SCBE14LayerPipeline();

// Seal sensitive data
const sealed = await pipeline.seal({
  data: "sensitive-payload",
  context: { userId: "alice", role: "admin" }
});

// Retrieve with trust verification
const result = await pipeline.retrieve(sealed, { userId: "alice" });
console.log(result.decision); // "ALLOW" or "DENY"
```

### Python
```python
from src.scbe_14layer_reference import SCBE14LayerPipeline

# Initialize pipeline
pipeline = SCBE14LayerPipeline()

# Seal data with context binding
sealed = pipeline.seal(
    data="sensitive-payload",
    context={"user_id": "alice", "role": "admin"}
)

# Retrieve with verification
result = pipeline.retrieve(sealed, context={"user_id": "alice"})
print(result["decision"])  # "ALLOW" or "DENY"
```

---

## Core Classes

### SCBE14LayerPipeline

The main orchestrator for the 14-layer security stack.

```typescript
class SCBE14LayerPipeline {
  constructor(config?: PipelineConfig);
  
  // Seal data with context binding
  seal(params: SealParams): Promise<SealedPayload>;
  
  // Retrieve and verify sealed data
  retrieve(sealed: SealedPayload, context: Context): Promise<RetrieveResult>;
  
  // Get pipeline metrics
  getMetrics(): PipelineMetrics;
}
```

#### SealParams
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | `string \| Buffer` | Yes | Data to encrypt |
| `context` | `Context` | Yes | Binding context (user, role, etc.) |
| `ttl` | `number` | No | Time-to-live in seconds |
| `layers` | `number[]` | No | Specific layers to apply (default: all 14) |

#### RetrieveResult
| Field | Type | Description |
|-------|------|-------------|
| `decision` | `"ALLOW" \| "DENY" \| "QUARANTINE"` | Access decision |
| `data` | `string \| null` | Decrypted data (null if denied) |
| `riskScore` | `number` | 0-1 risk assessment |
| `layerResults` | `LayerResult[]` | Per-layer verification results |

---

### TrustManager

Manages trust scoring using the Langues Weighting System.

```typescript
class TrustManager {
  constructor(config?: TrustConfig);
  
  // Evaluate trust for a context
  evaluate(context: Context): TrustScore;
  
  // Update trust based on behavior
  updateTrust(userId: string, event: TrustEvent): void;
  
  // Get trust history
  getHistory(userId: string): TrustHistory;
}
```

#### TrustScore
| Field | Type | Description |
|-------|------|-------------|
| `score` | `number` | 0-1 trust score |
| `confidence` | `number` | 0-1 confidence level |
| `factors` | `TrustFactor[]` | Contributing factors |
| `recommendation` | `string` | Action recommendation |

#### Trust Thresholds
| Score Range | Classification | Action |
|-------------|----------------|--------|
| 0.8 - 1.0 | Trusted | ALLOW |
| 0.5 - 0.8 | Cautious | ALLOW with logging |
| 0.2 - 0.5 | Suspicious | QUARANTINE |
| 0.0 - 0.2 | Untrusted | DENY |

---

### SpiralSeal

Sacred Tongue cryptographic encoding with quantum resistance.

```typescript
class SpiralSeal {
  constructor(config?: SpiralConfig);
  
  // Encode with Sacred Tongue
  encode(data: string, tongue: SacredTongue): EncodedPayload;
  
  // Decode Sacred Tongue payload
  decode(payload: EncodedPayload): string;
  
  // Verify integrity
  verify(payload: EncodedPayload): boolean;
}
```

#### Sacred Tongues
| Tongue | Code | Security Level | Use Case |
|--------|------|----------------|----------|
| Hebrew | `HE` | 256-bit | Financial, Legal |
| Sanskrit | `SA` | 256-bit | Medical, Research |
| Arabic | `AR` | 256-bit | Government, Defense |
| Greek | `GR` | 192-bit | Academic, Scientific |
| Latin | `LA` | 192-bit | Historical, Archival |
| Chinese | `ZH` | 256-bit | International, Trade |

---

### HarmonicScaling

Implements the patented Harmonic Scaling Law (H(d) = R^(d/d₀)).

```typescript
class HarmonicScaling {
  constructor(config?: HarmonicConfig);
  
  // Calculate harmonic distance
  calculate(d: number): number;
  
  // Verify super-exponential growth
  verifySuperExponential(d1: number, d2: number): boolean;
  
  // Get scaling metrics
  getMetrics(): HarmonicMetrics;
}
```

#### Harmonic Constants
| Constant | Symbol | Value | Description |
|----------|--------|-------|-------------|
| Base | R | 10.0 | Scaling base |
| Reference Distance | d₀ | 1.0 | Normalization factor |
| Growth Factor | α | 2.303 | ln(R) |

---

### PHDM (Polyhedral Hamiltonian Defense Manifold)

Intrusion detection using 16 canonical polyhedra.

```typescript
class PHDM {
  constructor(config?: PHDMConfig);
  
  // Detect intrusion
  detect(event: SecurityEvent): DetectionResult;
  
  // Get manifold state
  getState(): ManifoldState;
  
  // Update defense posture
  updatePosture(threat: ThreatLevel): void;
}
```

#### Polyhedra
| Index | Name | Vertices | Security Role |
|-------|------|----------|---------------|
| 0 | Tetrahedron | 4 | Basic validation |
| 1 | Cube | 8 | Context binding |
| 2 | Octahedron | 6 | Integrity check |
| 3 | Dodecahedron | 20 | Complex verification |
| 4 | Icosahedron | 12 | Quantum resistance |
| ... | ... | ... | ... |

---

## Layer Reference

### The 14-Layer Security Stack

| Layer | Name | Function | Module |
|-------|------|----------|--------|
| 1 | Context | Contextual encryption | `context-encoder` |
| 2 | Metric | Distance-based security | `langues-metric` |
| 3 | Breath | Temporal dynamics | `breath-layer` |
| 4 | Phase | Phase space encryption | `phase-encoder` |
| 5 | Potential | Energy-based security | `potential-field` |
| 6 | Spectral | Frequency domain | `spectral-coherence` |
| 7 | Spin | Quantum spin states | `spin-encoder` |
| 8 | Triadic | Three-way verification | `triadic-gate` |
| 9 | Harmonic | Resonance-based security | `harmonic-scaling` |
| 10 | Decision | Adaptive security | `decision-engine` |
| 11 | Audio | Cymatic patterns | `audio-axis` |
| 12 | Quantum | Post-quantum crypto | `pqc-layer` |
| 13 | Anti-Fragile | Self-healing | `self-healing` |
| 14 | Topological CFI | Control flow integrity | `hamiltonian-cfi` |

---

## Configuration

### Pipeline Configuration
```typescript
const config: PipelineConfig = {
  // Security level (1-5)
  securityLevel: 3,
  
  // Enable quantum resistance
  quantumResistant: true,
  
  // PQC algorithm
  pqcAlgorithm: "ML-KEM-768",
  
  // Trust thresholds
  trustThresholds: {
    allow: 0.8,
    quarantine: 0.5,
    deny: 0.2
  },
  
  // Logging
  logging: {
    level: "info",
    destination: "stdout"
  }
};
```

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `SCBE_SECURITY_LEVEL` | `3` | Security level (1-5) |
| `SCBE_PQC_ENABLED` | `true` | Enable post-quantum crypto |
| `SCBE_LOG_LEVEL` | `info` | Logging verbosity |
| `SCBE_TRUST_THRESHOLD` | `0.8` | Default trust threshold |

---

## Error Handling

### Error Types
```typescript
class SCBEError extends Error {
  code: string;
  layer?: number;
  recoverable: boolean;
}

// Specific errors
class ContextMismatchError extends SCBEError { code: "CONTEXT_MISMATCH" }
class TrustViolationError extends SCBEError { code: "TRUST_VIOLATION" }
class IntegrityError extends SCBEError { code: "INTEGRITY_FAILED" }
class QuantumThreatError extends SCBEError { code: "QUANTUM_THREAT" }
```

### Error Codes
| Code | Description | Recovery |
|------|-------------|----------|
| `CONTEXT_MISMATCH` | Context doesn't match sealed data | Re-authenticate |
| `TRUST_VIOLATION` | Trust score below threshold | Escalate to admin |
| `INTEGRITY_FAILED` | Data tampering detected | Reject and log |
| `QUANTUM_THREAT` | Quantum attack detected | Activate PQC fallback |
| `LAYER_FAILURE` | Specific layer failed | Check layer logs |

---

## TypeScript Types

```typescript
// Core types
interface Context {
  userId: string;
  role?: string;
  timestamp?: number;
  metadata?: Record<string, unknown>;
}

interface SealedPayload {
  ciphertext: string;
  nonce: string;
  contextHash: string;
  layers: LayerMetadata[];
  version: string;
}

interface LayerResult {
  layer: number;
  name: string;
  passed: boolean;
  score: number;
  details?: string;
}

// Enums
enum Decision {
  ALLOW = "ALLOW",
  DENY = "DENY",
  QUARANTINE = "QUARANTINE"
}

enum ThreatLevel {
  NONE = 0,
  LOW = 1,
  MEDIUM = 2,
  HIGH = 3,
  CRITICAL = 4
}
```

---

## Python API

### Main Classes
```python
from src.scbe_14layer_reference import SCBE14LayerPipeline
from src.crypto.sacred_tongues import SacredTongueEncoder
from src.crypto.rwp_v3 import RWPv3Envelope

# Pipeline
pipeline = SCBE14LayerPipeline()
result = pipeline.seal(data, context)

# Sacred Tongue
encoder = SacredTongueEncoder(tongue="hebrew")
encoded = encoder.encode("sensitive data")

# RWP Envelope
envelope = RWPv3Envelope()
wrapped = envelope.wrap(payload, signatures=["sig1", "sig2"])
```

### Decorators
```python
from src.scbe.decorators import require_trust, audit_log

@require_trust(threshold=0.8)
@audit_log
def sensitive_operation(data: str, context: dict) -> dict:
    # Operation is only executed if trust >= 0.8
    return process(data)
```

---

## CLI Reference

```bash
# Seal data
scbe seal --data "secret" --context '{"user": "alice"}'

# Retrieve data
scbe retrieve --sealed <payload> --context '{"user": "alice"}'

# Check trust score
scbe trust --user alice

# Run diagnostics
scbe diagnose --verbose

# Version info
scbe --version
```

---

## Performance

### Benchmarks (M1 MacBook Pro)
| Operation | Time | Throughput |
|-----------|------|------------|
| Seal (14 layers) | 2.3ms | 435 ops/sec |
| Retrieve (14 layers) | 1.8ms | 556 ops/sec |
| Trust evaluation | 0.4ms | 2,500 ops/sec |
| PQC key generation | 12ms | 83 ops/sec |

### Memory Usage
| Component | Memory |
|-----------|--------|
| Pipeline (idle) | 45 MB |
| Per sealed payload | 2.1 KB |
| Trust cache (1000 users) | 8 MB |

---

## See Also

- [README.md](../README.md) - Quick start guide
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [DEMOS.md](../DEMOS.md) - Demo scenarios
- [MATHEMATICAL_PROOFS.md](./MATHEMATICAL_PROOFS.md) - Formal proofs

---

*Patent Pending - USPTO Application #63/961,403*
