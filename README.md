# Symphonic Cipher + SCBE-AETHERMOORE

**Intent-Modulated Conlang + Hyperbolic Governance System**

*Last Updated: January 15, 2026*

---

## SCBE-AETHERMOORE: Hyperbolic Governance for AI Safety

A 14-layer hyperbolic geometry system where adversarial intent costs exponentially more the further it drifts from safe operation.

### Quick Summary

| Metric | Value |
|--------|-------|
| **Detection Rate** | 95.3% |
| **vs Linear Systems** | +56.6% |
| **Mathematical Proofs** | 12 axioms verified |
| **Post-Quantum Safe** | Kyber/ML-DSA integrated |

### Key Differentiators

1. **Harmonic Wall**: `H(d) = exp(d²)` - exponential cost for deviation
2. **Langues Metric**: 6D phase-shifted exponential with Six Sacred Tongues
3. **Hyperbolic Geometry**: Poincaré ball where boundary = infinite cost
4. **Fluxing Dimensions**: Polly/Quasi/Demi dimensional breathing

### One-Liner

> "Hyperbolic geometry firewall for autonomous systems where adversarial behavior costs exponentially more the further it drifts from safe operation."

### Architecture

```
14-LAYER PIPELINE
═══════════════════════════════════════════════════════════════════

Layer 1-2:   Complex Context → Realification
Layer 3-4:   Weighted Transform → Poincaré Embedding
Layer 5:     dℍ = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))  [INVARIANT]
Layer 6-7:   Breathing Transform + Phase (Möbius addition)
Layer 8:     Multi-Well Realms
Layer 9-10:  Spectral + Spin Coherence
Layer 11:    Triadic Temporal Distance
Layer 12:    H(d,R) = R^(d²)  [HARMONIC WALL]
Layer 13:    Risk' → ALLOW / QUARANTINE / DENY
Layer 14:    Audio Axis (FFT telemetry)

═══════════════════════════════════════════════════════════════════
```

### Quantum Axiom Mesh (5 axioms organizing 14 layers)

| Axiom | Layers | Property |
|-------|--------|----------|
| **Unitarity** | 2, 4, 7 | Norm preservation |
| **Locality** | 3, 8 | Spatial bounds |
| **Causality** | 6, 11, 13 | Time-ordering |
| **Symmetry** | 5, 9, 10, 12 | Gauge invariance |
| **Composition** | 1, 14 | Pipeline integrity |

### The Langues Metric

```
L(x,t) = Σ w_l exp(β_l · (d_l + sin(ω_l t + φ_l)))
```

**Six Sacred Tongues:**

| Tongue | Weight (φ^k) | Phase | Frequency |
|--------|-------------|-------|-----------|
| KO | 1.00 | 0° | 1.000 |
| AV | 1.62 | 60° | 1.125 |
| RU | 2.62 | 120° | 1.250 |
| CA | 4.24 | 180° | 1.333 |
| UM | 6.85 | 240° | 1.500 |
| DR | 11.09 | 300° | 1.667 |

### Fluxing Dimensions

```
L_f(x,t) = Σ νᵢ(t) wᵢ exp[βᵢ(dᵢ + sin(ωᵢt + φᵢ))]

Flux ODE: ν̇ᵢ = κᵢ(ν̄ᵢ - νᵢ) + σᵢ sin(Ωᵢt)
```

| ν Value | State | Meaning |
|---------|-------|---------|
| ν ≈ 1.0 | **Polly** | Full dimension active |
| 0.5 < ν < 1 | **Quasi** | Partial participation |
| 0 < ν < 0.5 | **Demi** | Minimal participation |
| ν ≈ 0.0 | **Collapsed** | Dimension off |

### Benchmark Results

```
SCBE (Harmonic + Langues):  95.3%
ML Anomaly Detection:       89.6%
Pattern Matching:           56.6%
Linear Threshold:           38.7%
```

### Usage

```python
from symphonic_cipher.scbe_aethermoore.axiom_grouped import (
    LanguesMetric, FluxingLanguesMetric, DimensionFlux,
    HyperspacePoint, verify_all_axioms
)

# Create metric
metric = LanguesMetric(beta_base=1.0)

# Assess a state
state = HyperspacePoint(intent=0.5, trust=0.8, risk=0.2)
L = metric.compute(state)
risk, decision = metric.risk_level(L)
print(f"L={L:.2f} → {risk} → {decision}")

# With fluxing dimensions
flux_metric = FluxingLanguesMetric(flux=DimensionFlux.quasi())
L_f, D_f = flux_metric.compute_with_flux_update(state)
print(f"L_f={L_f:.2f}, effective_dim={D_f:.2f}")
```

### Running the Benchmark

```bash
python symphonic_cipher/scbe_aethermoore/axiom_grouped/benchmark_comparison.py
```

### Running All Proofs

```bash
python symphonic_cipher/scbe_aethermoore/axiom_grouped/langues_metric.py
```

---

## Symphonic Cipher (Original)

**Quantum-Resistant Geometric Security System**

---

## Quick Start (For Non-Coders)

**What this does:** Protects your data using math, geometry, and quantum-safe encryption.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Test everything works (should see "84 passed")
pip install pytest && python -m pytest tests/test_pqc.py -v

# 3. Try it out
python -c "
from symphonic_cipher.scbe_aethermoore.qc_lattice import quick_validate
result = quick_validate('user123', 'read_data')
print(f'Decision: {result.decision.value}')
print(f'Confidence: {result.confidence:.0%}')
"
```

---

## What's In This Codebase

| Folder | What It Does |
|--------|--------------|
| `pqc/` | **Quantum-safe encryption** - Uses Kyber768 + Dilithium3 (unbreakable by quantum computers) |
| `qc_lattice/` | **Geometric verification** - Uses quasicrystals (never-repeating patterns) and 16 3D shapes |
| Core files | **Math engine** - 9-dimensional calculations, 14-layer security pipeline |

---

## For AWS Lambda

```python
from symphonic_cipher.scbe_aethermoore.qc_lattice import IntegratedAuditChain
import json

chain = IntegratedAuditChain(use_pqc=True)

def lambda_handler(event, context):
    validation, sig = chain.add_entry(event['user'], event['action'])
    return {
        'statusCode': 200 if validation.decision.value == 'ALLOW' else 403,
        'body': json.dumps({'decision': validation.decision.value})
    }
```

---

## Original System: Intent-Modulated Conlang + Harmonic Verification System

A mathematically rigorous authentication protocol that combines:
- Private conlang (constructed language) dictionary mapping
- Modality-driven harmonic synthesis
- Key-driven Feistel permutation
- Studio engineering DSP pipeline
- AI-based feature extraction and verification
- RWP v3 cryptographic envelope

### Overview

The Symphonic Cipher authenticates commands by encoding them as audio waveforms with specific harmonic signatures. Different "intent modalities" (STRICT, ADAPTIVE, PROBE) produce different overtone patterns that can be verified through FFT analysis.

### Architecture

```
[Conlang Phrase] → [Token IDs] → [Feistel Permutation] → [Harmonic Synthesis]
        ↓
[DSP Chain: Gain → EQ → Compression → Reverb → Panning]
        ↓
[RWP v3 Envelope: HMAC-SHA256 + Nonce + Timestamp]
        ↓
[Verification: MAC Check + Harmonic Analysis + AI Classification]
```

### Mathematical Foundation

#### 1. Dictionary Mapping (Section 2)

Bijection between lexical tokens and integer IDs:

```
∀τ ∈ D: id(τ) ∈ {0, ..., |D|-1}
```

#### 2. Modality Encoding (Section 3)

Each modality M determines which overtones are emitted via mask M(M):

| Modality | Mask M(M) | Description |
|----------|-----------|-------------|
| STRICT | {1, 3, 5} | Odd harmonics (binary intent) |
| ADAPTIVE | {1, 2, 3, 4, 5} | Full series (non-binary intent) |
| PROBE | {1} | Fundamental only |

#### 3. Per-Message Secret (Section 4)

```
K_msg = HMAC_{k_master}(ASCII("msg_key" || n))
```

#### 4. Feistel Permutation (Section 5)

4-round balanced Feistel network:

```
L^(r+1) = R^(r)
R^(r+1) = L^(r) ⊕ F(R^(r), k^(r))
```

#### 5. Harmonic Synthesis (Section 6)

```
x(t) = Σᵢ Σₕ∈M(M) (1/h) sin(2π(f₀ + vᵢ'·Δf)·h·t)
```

Where:
- f₀ = 440 Hz (base frequency)
- Δf = 30 Hz (frequency step per token ID)

#### 6. DSP Pipeline (Sections 3.2-3.10)

- **Gain Stage**: v₁ = g · v₀, where g = 10^(G_dB/20)
- **Mic Pattern Filter**: v₂[i] = v₁[i] · (a + (1-a)·cos(θᵢ - θ_axis))
- **Parametric EQ**: Biquad IIR filter with peak/shelf modes
- **Compressor**: Piecewise-linear gain reduction with attack/release
- **Convolution Reverb**: z[n] = (x * h)[n]
- **Stereo Panning**: Constant-power law L/R distribution

#### 7. RWP v3 Envelope (Section 7)

```
C = "v3." || σ || AAD_canon || t || n || b64url(x)
sig = HMAC_{k_master}(C)
```

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```python
from symphonic_cipher import SymphonicCipher, Modality

# Create cipher with auto-generated key
cipher = SymphonicCipher()

# Encode a conlang phrase
envelope = cipher.encode(
    phrase="korah aelin dahru",
    modality=Modality.ADAPTIVE,
    tongue="KO"
)

# Verify envelope
success, message = cipher.verify(envelope)
print(f"Verified: {success}")
```

### Running the Demo

```bash
python demo.py
```

### Running Tests

```bash
pytest symphonic_cipher/tests/ -v
```

### Security Properties

1. **HMAC-SHA256 Integrity**: Envelope tampering is detected
2. **Nonce-based Replay Protection**: Each message uses unique nonce
3. **Timestamp Expiry**: Messages expire after 60 seconds
4. **Key-driven Permutation**: Token order is secret without key
5. **Harmonic Verification**: Modality must match declared intent
6. **AI Liveness Detection**: Synthetic/replay audio is flagged

### Constants

| Symbol | Value | Description |
|--------|-------|-------------|
| f₀ | 440 Hz | Base frequency (A4) |
| Δf | 30 Hz | Frequency step per token ID |
| H_max | 5 | Maximum overtone index |
| SR | 44,100 Hz | Sample rate |
| T_sec | 0.5 s | Waveform duration |
| R | 4 | Feistel rounds |
| τ_max | 60,000 ms | Replay window |
| ε_f | 2 Hz | Frequency tolerance |
| ε_a | 0.15 | Amplitude tolerance |

### Conlang Vocabulary

Default vocabulary:

| Token | ID | Frequency |
|-------|-----|-----------|
| korah | 0 | 440 Hz |
| aelin | 1 | 470 Hz |
| dahru | 2 | 500 Hz |
| melik | 3 | 530 Hz |
| sorin | 4 | 560 Hz |
| tivar | 5 | 590 Hz |
| ulmar | 6 | 620 Hz |
| vexin | 7 | 650 Hz |

Extended vocabulary supports negative IDs (e.g., "shadow" = -1 → 410 Hz).

---

## License

MIT License

---

## Advanced Modules (New)

### Post-Quantum Cryptography (PQC)

Quantum-safe encryption using NIST-approved algorithms:

| Algorithm | Purpose | Size |
|-----------|---------|------|
| **Kyber768** | Key exchange | 1184 byte public key |
| **Dilithium3** | Digital signatures | 3293 byte signature |

```python
from symphonic_cipher.scbe_aethermoore.pqc import Kyber768, Dilithium3

# Key exchange
keypair = Kyber768.generate_keypair()
result = Kyber768.encapsulate(keypair.public_key)
shared_secret = Kyber768.decapsulate(keypair.secret_key, result.ciphertext)

# Signatures
sig_keys = Dilithium3.generate_keypair()
signature = Dilithium3.sign(sig_keys.secret_key, b"message")
is_valid = Dilithium3.verify(sig_keys.public_key, b"message", signature)
```

### Quasicrystal Lattice

6D → 3D projection for geometric verification:

- **Phason Shift**: Instant key rotation without changing logic
- **Crystallinity Detection**: Catches periodic attack patterns
- **Golden Ratio**: Icosahedral symmetry (never-repeating patterns)

### PHDM (16 Polyhedra)

| Type | Shapes | Count |
|------|--------|-------|
| Platonic | Tetrahedron, Cube, Octahedron, Dodecahedron, Icosahedron | 5 |
| Archimedean | Truncated Tetrahedron, Cuboctahedron, Icosidodecahedron | 3 |
| Kepler-Poinsot | Small Stellated Dodecahedron, Great Dodecahedron | 2 |
| Toroidal | Szilassi, Császár | 2 |
| Johnson | Pentagonal Bipyramid, Triangular Cupola | 2 |
| Rhombic | Rhombic Dodecahedron, Bilinski Dodecahedron | 2 |

---

## Key Terms (Glossary)

| Term | Simple Meaning |
|------|----------------|
| **Kyber768** | Secure key sharing that quantum computers can't break |
| **Dilithium3** | Digital signatures that quantum computers can't forge |
| **Quasicrystal** | Ordered pattern that never repeats (like Penrose tiles) |
| **Phason** | Shifts the "valid region" for instant key rotation |
| **HMAC Chain** | Linked records where each depends on the previous |
| **Hamiltonian Path** | Route visiting each shape exactly once |
| **Golden Ratio (φ)** | 1.618... - appears in icosahedral geometry |

---

## References

- HMAC-SHA256: RFC 2104
- Feistel Networks: Luby-Rackoff, 1988
- Biquad Filters: Audio EQ Cookbook
- MFCC: Davis & Mermelstein, 1980
- Kyber: NIST PQC Round 3 Winner
- Dilithium: NIST PQC Round 3 Winner
- Icosahedral Quasicrystals: Shechtman et al., 1984
- Poincaré Ball Model: Hyperbolic Geometry
- Möbius Addition: Gyrogroup Theory

---

*SCBE-AETHERMOORE © 2026 Isaac Thorne / SpiralVerse OS*
