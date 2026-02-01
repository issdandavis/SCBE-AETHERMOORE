# CLAUDE.md - Project Instructions for AI Assistants

## Project Overview

**SCBE-AETHERMOORE** is an AI safety and governance framework using hyperbolic geometry (Poincaré ball model) for exponential cost scaling of adversarial behavior. The system implements a **14-layer security pipeline** with post-quantum cryptography (Kyber768 + ML-DSA-65).

**Core Innovation**: Adversarial intent costs exponentially more the further it drifts from safe operation, making attacks computationally infeasible.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Languages** | TypeScript (canonical), Python (reference) |
| **Node Version** | >= 18.0.0 |
| **Python Version** | >= 3.9 |
| **Test Frameworks** | Vitest (TS), pytest (Python) |
| **API Framework** | FastAPI + Uvicorn |

## Common Commands

```bash
# Install dependencies
npm install
pip install -r requirements.txt

# Build
npm run build              # Compile TypeScript
npm run typecheck          # Type check only

# Test
npm test                   # Run all TypeScript tests
npm test -- --coverage     # With coverage
python -m pytest tests/ -v # Run Python tests

# Code quality
npm run format             # Format TypeScript (Prettier)
npm run lint               # Lint TypeScript
npm run check:circular     # Check for circular dependencies

# Run API server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
src/
├── harmonic/           # CORE: 14-layer pipeline (TypeScript)
│   ├── pipeline14.ts   # Main pipeline implementation
│   ├── hyperbolic.ts   # Poincaré ball operations (L5-7)
│   ├── harmonicScaling.ts  # Harmonic wall (L12)
│   └── sacredTongues.ts    # 6×256 tokenizer
├── crypto/             # Cryptographic primitives (TypeScript)
├── spiralverse/        # RWP protocol & envelope encryption
├── symphonic/          # Symphonic cipher (audio-based crypto)
├── symphonic_cipher/   # Python reference implementations
├── api/                # FastAPI REST server
├── fleet/              # Multi-agent orchestration
│   └── polly-pads/     # Distributed consensus pads
├── spectral/           # FFT coherence analysis
├── agent/              # Single agent abstractions
├── agentic/            # Multi-agent AI platform
├── ai_orchestration/   # AI orchestration layer
├── gateway/            # API gateway & routing
├── network/            # Network topology & combat mesh
├── spaceTor/           # Trust-based overlay network
├── selfHealing/        # Self-healing infrastructure
├── tokenizer/          # Token processing utilities
├── pqc/                # Post-quantum crypto wrappers
├── physics_sim/        # Physics simulation models
├── lambda/             # Serverless function handlers
└── core/               # Core types & utilities

tests/
├── L1-basic/           # Smoke tests
├── L2-unit/            # Unit tests
├── L3-integration/     # Integration tests
├── L4-property/        # Property-based tests
├── L5-security/        # Security boundary tests
├── L6-adversarial/     # Adversarial attack tests
├── harmonic/           # Layer & pipeline tests
├── enterprise/         # Compliance tests (FIPS, SOC2)
├── cross-industry/     # Fleet scenarios (bank, healthcare, manufacturing)
├── cross-language/     # TypeScript/Python parity tests
├── industry_standard/  # NIST, Byzantine, side-channel tests
├── spiralverse/        # RWP envelope tests
├── fleet/              # Fleet manager tests
├── spectral/           # Spectral coherence tests
└── symphonic/          # Audio gate tests
```

## 14-Layer Architecture

Every module maps to specific layers - tag files with `@layer` comments:

- **L1-2**: Complex context → Realification
- **L3-4**: Weighted transform → Poincaré embedding
- **L5**: Hyperbolic distance (invariant)
- **L6-7**: Breathing + Möbius phase
- **L8**: Multi-well realms
- **L9-10**: Spectral + spin coherence
- **L11**: Triadic temporal distance
- **L12**: Harmonic wall (risk amplification)
- **L13**: Risk decision → ALLOW/QUARANTINE/DENY
- **L14**: Audio axis (FFT telemetry)

## Code Style

### TypeScript (from .prettierrc)
- Semicolons: Required
- Quotes: Single quotes
- Line width: 100 characters
- Indentation: 2 spaces
- Trailing commas: ES5 style

### Python
- Black formatter with 120 char line length
- Google-style docstrings
- Type hints required for all functions

### File Header Convention
```typescript
/**
 * @file filename.ts
 * @module harmonic/module-name
 * @layer Layer X, Layer Y
 * @component Component Name
 * @version 3.x.x
 */
```

## Development Guidelines

### Dual Implementation Strategy
- **TypeScript is canonical** (production)
- **Python is reference** (research/validation)
- Always update TypeScript first, then Python
- Cross-language tests in `tests/cross-language/` validate parity

### Security Requirements
- All crypto operations must be constant-time
- Validate inputs before cryptographic processing
- Never commit `.env` files or secrets
- Use HMAC for integrity checks
- Use `Buffer` for crypto operations in TypeScript

### Testing Requirements
- Unit tests in appropriate `tests/` tier
- Property-based tests for mathematical functions (fast-check/Hypothesis)
- Coverage targets: 80% lines, 80% functions, 70% branches
- Test markers: `enterprise`, `professional`, `homebrew`, `property`, `stress`

### When Adding Features
1. Tag files with `@layer` comments
2. Document which axiom your code satisfies
3. Write comprehensive tests
4. Update CHANGELOG.md for notable changes

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):
```
feat(harmonic): add layer X implementation
fix(crypto): resolve timing attack in envelope
docs(api): update endpoint examples
test(harmonic): add property-based tests
refactor(spectral): optimize FFT implementation
chore: bump dependencies
```

## Key Concepts

### Sacred Tongues (Langues Metric)
6 dimensions with golden ratio weights: KO, AV, RU, CA, UM, DR

### Harmonic Wall
Risk amplification formula: `H(d,R) = φᵈ / (1 + e⁻ᴿ)`
- Exponential cost for deviation from safe operation
- Poincaré boundary = infinite cost
- Trustworthy center = near-zero cost

### Quantum Axiom Mesh (5 axioms across 14 layers)
1. **Unitarity** (L2, 4, 7): Norm preservation
2. **Locality** (L3, 8): Spatial bounds
3. **Causality** (L6, 11, 13): Time-ordering
4. **Symmetry** (L5, 9, 10, 12): Gauge invariance
5. **Composition** (L1, 14): Pipeline integrity

## Test Tiers (L1-L6)

Tests are organized into tiers by complexity and purpose:

| Tier | Purpose | Run Command |
|------|---------|-------------|
| **L1-basic** | Smoke tests, quick sanity checks | `npm test -- tests/L1-basic` |
| **L2-unit** | Unit tests for individual functions | `npm test -- tests/L2-unit` |
| **L3-integration** | Integration tests across modules | `npm test -- tests/L3-integration` |
| **L4-property** | Property-based tests (fast-check) | `npm test -- tests/L4-property` |
| **L5-security** | Security boundary tests | `npm test -- tests/L5-security` |
| **L6-adversarial** | Adversarial attack simulations | `npm test -- tests/L6-adversarial` |

## RWP Protocol (Spiralverse)

The **Rotating Waveform Protocol (RWP)** provides envelope encryption with:
- Nonce rotation and uniqueness enforcement
- TTL-based message expiration
- Tamper-evident signatures
- Post-quantum key encapsulation

## Hyperbolic Video Generation

The framework extends to procedural video synthesis using hyperbolic geometry:

### Core Components
- **Poincaré Embeddings**: Context vectors mapped to curved space for bounded, non-Euclidean visual evolution
- **Fractal Chaos Layers**: Julia/Mandelbrot sets driven by lattice parameters
- **Lattice Watermarking**: Ring-LWE quantum-resistant signatures in frame LSBs
- **Harmonic Audio**: Golden-ratio weighted overtones synced to visual geometry

### Sacred Tongue Intent Mapping

| Tongue | Intent | Julia c Parameter | Visual Character |
|--------|--------|-------------------|------------------|
| **Kor'aelin** | Flow/Stability | -0.4 + 0.6i | Connected, dendrite-like |
| **Avali** | Context/Boundary | -0.8 + 0.156i | Siegel disk (bounded) |
| **Runethic** | Binding/Chaos | -0.12 + 0.74i | Douady rabbit (fractal) |
| **Cassisivadan** | Bitcraft/Shatter | 0.285 + 0.01i | Scattered dust |
| **Umbroth** | Veil/Mystery | -1.0 + 0i | Cauliflower (hidden) |
| **Draumric** | Structure/Order | -0.75 + 0.11i | San Marco dragon |

### Video Generation Pipeline
1. Generate hyperbolic trajectory from context vectors
2. Render Mandelbrot frames with intent-modulated c parameter
3. Embed Ring-LWE watermarks in frame LSBs
4. Synthesize golden-ratio harmonic audio
5. Composite with moviepy/ffmpeg

### Dependencies
```bash
pip install numpy matplotlib moviepy
# Optional for 4K: pip install cupy  # GPU acceleration
```

## Debugging Tips

```bash
npm run check:circular    # Find module dependency issues
npm run typecheck         # Check types before building
npm test -- --watch       # Watch mode for development
python -m pytest -m homebrew tests/  # Quick smoke tests
```

## Docker

```bash
docker build -t scbe-aethermoore:latest .
docker run -p 8000:8000 scbe-aethermoore:latest
docker-compose up -d  # With Redis orchestration
```
