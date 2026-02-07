# CLAUDE.md - Project Instructions for AI Assistants

## Project Overview

**SCBE-AETHERMOORE** is an AI safety and governance framework using hyperbolic geometry (Poincare ball model) for exponential cost scaling of adversarial behavior. The system implements a **14-layer security pipeline** with post-quantum cryptography (Kyber768 / ML-KEM-768 + ML-DSA-65).

**Core Innovation**: Adversarial intent costs exponentially more the further it drifts from safe operation, making attacks computationally infeasible.

**Version**: 3.2.4 (TypeScript package) / 3.0.0 (Python package)

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Languages** | TypeScript (canonical), Python (reference) |
| **Node Version** | >= 18.0.0 |
| **Python Version** | >= 3.11 (pyproject.toml), >= 3.9 (requirements.txt fallback) |
| **Test Frameworks** | Vitest (TS), pytest (Python) |
| **Property Testing** | fast-check (TS), Hypothesis (Python) |
| **API Framework** | FastAPI + Uvicorn |
| **TypeScript** | ^5.8.3, target ES2022, CommonJS |
| **Package Entry** | `./dist/src/index.js` |

## Common Commands

```bash
# Install dependencies
npm install
pip install -r requirements.txt

# Build
npm run build              # Clean + compile TypeScript
npm run build:src          # Compile TypeScript only (no clean)
npm run build:watch        # Watch mode compilation
npm run typecheck          # Type check only (no emit)

# Test
npm test                   # Run all TypeScript tests (vitest run)
npm run test:coverage      # With coverage (vitest run --coverage)
npm run test:python        # Run Python tests (pytest tests/ -v)
npm run test:all           # Run both TS and Python tests

# Code quality
npm run format             # Format TypeScript (Prettier)
npm run format:python      # Format Python (Black, 120 char)
npm run lint               # Lint TypeScript (Prettier --check)
npm run lint:python        # Lint Python (flake8, 120 char)
npm run check:circular     # Check for circular dependencies (madge)
npm run check:deps         # Generate dependency graph SVG

# Run API server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# CLI
npm run cli                # Run Python CLI (scbe-cli.py)

# Docker
npm run docker:build       # Build Docker image
npm run docker:run         # Run container
npm run docker:compose     # Docker Compose (detached)
```

## Project Structure

```
src/
├── harmonic/              # CORE: 14-layer pipeline (TypeScript)
│   ├── pipeline14.ts      # Main 14-layer pipeline implementation (739 lines)
│   ├── hyperbolic.ts      # Poincare ball operations (L5-7) (472 lines)
│   ├── harmonicScaling.ts # Harmonic wall / risk amplification (L12)
│   ├── sacredTongues.ts   # 6x256 tokenizer (494 lines)
│   ├── languesMetric.ts   # Sacred Tongues 6D metric
│   ├── audioAxis.ts       # Audio axis telemetry (L14)
│   ├── phdm.ts            # Poincare Half-plane Drift Monitor
│   ├── spiralSeal.ts      # SpiralSeal SS1 envelope encoding
│   ├── hamiltonianCFI.ts  # Hamiltonian control flow integrity (L8)
│   ├── vacuumAcoustics.ts # Cymatic/acoustic simulation (L14)
│   ├── halAttention.ts    # Harmonic Attention Layer
│   ├── qcLattice.ts       # Quasicrystal lattice verification
│   ├── adaptiveNavigator.ts # Adaptive hyperbolic geometry
│   ├── spectral-identity.ts # Spectral identity
│   └── assertions.ts      # Mathematical assertions
├── crypto/                # Cryptographic primitives (TS + Python)
│   ├── pqc.ts             # Post-quantum crypto (ML-KEM-768, ML-DSA-65)
│   ├── envelope.ts        # Sealed envelope (AES-256-GCM)
│   ├── kms.ts             # Key management (HKDF)
│   ├── hkdf.ts            # HKDF key derivation
│   ├── replayGuard.ts     # Replay protection (nonce/Bloom)
│   ├── replayStore.ts     # Nonce management
│   ├── nonceManager.ts    # Nonce lifecycle
│   ├── jcs.ts             # JSON Canonicalization Scheme
│   └── bloom.ts           # Bloom filter
├── symphonic/             # TypeScript port of Symphonic Cipher
│   ├── FFT.ts             # Fast Fourier Transform
│   ├── Feistel.ts         # Feistel network
│   ├── HybridCrypto.ts    # Hybrid encryption
│   ├── ZBase32.ts         # ZBase32 encoding
│   └── SymphonicAgent.ts  # Symphonic agent
├── symphonic_cipher/      # Python reference implementations
│   ├── core.py            # Core cipher implementation
│   ├── dsp.py             # Digital signal processing
│   ├── harmonic_scaling_law.py  # Scaling laws (largest Python file)
│   └── scbe_aethermoore/  # Full Python implementation
│       ├── ai_brain/      # Python reference: 21D brain mapping
│       └── axiom_grouped/ # 5 Quantum Axiom implementations
│           ├── unitarity_axiom.py   # L2, L4, L7
│           ├── locality_axiom.py    # L3, L8
│           ├── causality_axiom.py   # L6, L11, L13
│           ├── symmetry_axiom.py    # L5, L9, L10, L12
│           └── composition_axiom.py # L1, L14
├── api/                   # REST API
│   ├── main.py            # FastAPI server (Python)
│   ├── routes.ts          # Express/HTTP routes (TypeScript)
│   ├── govern.ts          # Governance API
│   └── server.ts          # Server setup
├── fleet/                 # Multi-agent orchestration
│   ├── fleet-manager.ts   # Fleet orchestration
│   ├── agent-registry.ts  # Agent registration
│   ├── swarm.ts           # Swarm coordination
│   ├── task-dispatcher.ts # Task assignment
│   ├── polly-pad.ts       # Personal agent workspaces
│   ├── redis-orchestrator.ts # Redis integration
│   └── governance.ts      # Fleet governance
├── ai_brain/              # 21D AI Brain Mapping (L1-14 unified)
│   ├── types.ts           # 21D state types and constants
│   ├── unified-state.ts   # UnifiedBrainState class, Poincare embedding
│   ├── detection.ts       # 5 orthogonal detection mechanisms
│   ├── bft-consensus.ts   # BFT consensus (corrected 3f+1)
│   ├── quasi-space.ts     # Quasicrystal icosahedral projection
│   ├── audit.ts           # SHA-256 hash-chained audit logger
│   └── index.ts           # Module exports
├── spectral/              # FFT coherence analysis (L9-10)
├── gateway/               # Unified SCBE API Gateway
├── selfHealing/           # Failure recovery and diagnosis
├── network/               # Network security (SpaceTor router, combat network)
├── spaceTor/              # Tor-like privacy routing
├── spiralverse/           # Spiralverse protocol
├── tokenizer/             # Sacred Tongues token generation
├── agent/                 # Agent framework
├── agentic/               # Agentic system and demos
├── ai_orchestration/      # AI workflow orchestration
├── integrations/          # Third-party integrations
├── metrics/               # Telemetry
├── security/              # Security modules
├── skills/                # Extensible skill definitions
├── pqc/                   # Post-quantum crypto variants
├── core/                  # Core utilities
├── constants/             # Global constants
├── errors/                # Error handling
├── utils/                 # Utility functions
├── minimal/               # Educational minimal SCBE implementation
├── rollout/               # Gradual deployment management
├── lambda/                # AWS Lambda support
├── browser/               # Browser integrations
├── video/                 # Video processing
├── physics_sim/           # Physics simulation
├── scbe/                  # SCBE utilities
└── science_packs/         # Scientific packages

tests/
├── L1-basic/              # Smoke tests ("Does it run?")
├── L2-unit/               # Unit tests (isolated functions)
├── L3-integration/        # Integration tests (component interactions)
├── L4-property/           # Property-based tests (fast-check/Hypothesis)
├── L5-security/           # Security boundary tests
├── L6-adversarial/        # Adversarial attack simulations
├── harmonic/              # 14-layer pipeline tests (12 files)
├── crypto/                # Cryptographic tests (7 files)
├── ai_brain/              # AI Brain Mapping tests (unit + integration)
├── spectral/              # Spectral coherence tests
├── enterprise/            # Enterprise-grade compliance tests
│   ├── formal/            # Formal verification
│   ├── quantum/           # Quantum security
│   ├── ai_brain/          # AI brain tests
│   ├── security/          # Security hardening
│   ├── compliance/        # FIPS, SOC2, ISO27001
│   ├── integration/       # Enterprise integration
│   ├── agentic/           # Agentic tests
│   └── stress/            # Load and stress testing
├── cross-industry/        # Industry-specific scenarios
│   ├── bank/              # Banking/finance
│   ├── healthcare/        # Healthcare
│   ├── manufacturing/     # Manufacturing
│   └── common/            # Shared utilities
├── cross-language/        # TypeScript/Python parity validation
├── fleet/                 # Fleet orchestration tests
├── spiralverse/           # RWP envelope tests
├── symphonic/             # Symphonic cipher tests
├── network/               # Network tests
├── agent/                 # Agent framework tests
├── agentic/               # Agentic system tests
├── api/                   # REST API tests
├── video/                 # Video tests
├── skills/                # Skill tests
├── hydra/                 # Swarm governance tests
├── orchestration/         # Scheduler/executor tests
├── interop/               # Interoperability tests
├── industry_standard/     # NIST, Byzantine consensus, benchmarks
├── security/              # Security module tests
├── utils/                 # Utility tests
├── reporting/             # Reporting tests
├── aethermoore_constants/ # Constants tests
└── *.py (root-level)      # 44 Python test files for deep validation
```

### Package Exports

The npm package exposes these entry points:

```
scbe-aethermoore           # Main (./dist/src/index.js)
scbe-aethermoore/harmonic  # 14-layer pipeline
scbe-aethermoore/symphonic # Symphonic cipher
scbe-aethermoore/crypto    # Cryptographic primitives
scbe-aethermoore/spiralverse # Spiralverse protocol
scbe-aethermoore/tokenizer # Sacred Tongues tokenizer
scbe-aethermoore/phdm      # Poincare Half-plane Drift Monitor
scbe-aethermoore/ai_brain  # 21D AI Brain Mapping (unified manifold + detection)
```

## 14-Layer Architecture

Every module maps to specific layers - tag files with `@layer` comments:

| Layers | Function | Primary Files |
|--------|----------|---------------|
| **L1-2** | Complex context -> Realification | `pipeline14.ts` |
| **L3-4** | Weighted transform -> Poincare embedding | `languesMetric.ts`, `pipeline14.ts` |
| **L5** | Hyperbolic distance (invariant) | `hyperbolic.ts`, `adaptiveNavigator.ts` |
| **L6-7** | Breathing + Mobius phase | `hyperbolic.ts`, `adaptiveNavigator.ts` |
| **L8** | Multi-well realms | `hamiltonianCFI.ts` |
| **L9-10** | Spectral + spin coherence | `spectral/index.ts` |
| **L11** | Triadic temporal distance | `causality_axiom.py` |
| **L12** | Harmonic wall (risk amplification) | `harmonicScaling.ts` |
| **L13** | Risk decision: ALLOW/QUARANTINE/ESCALATE/DENY | 4-tier swarm governance |
| **L14** | Audio axis (FFT telemetry) | `audioAxis.ts`, `vacuumAcoustics.ts` |

## Tiered Test Architecture (L1-L6)

Tests follow a complexity pyramid, each tier building on the previous:

| Tier | Level | Purpose | Framework |
|------|-------|---------|-----------|
| **L1-basic** | Smoke | Sanity checks - "Does it run?" | Vitest |
| **L2-unit** | Unit | Isolated function testing | Vitest |
| **L3-integration** | Integration | Component interaction flows | Vitest |
| **L4-property** | Property | Random-input mathematical proofs | fast-check (100+ iterations) |
| **L5-security** | Security | Cryptographic boundary enforcement | Vitest |
| **L6-adversarial** | Red Team | Attack simulations, timing analysis | Vitest |

### Test File Naming

- **TypeScript**: `{module}.{tier}.test.ts` (e.g., `spectral.property.test.ts`)
- **Python**: `test_{module}.py` or `test_{module}_{context}.py`

### pytest Markers

**Tier markers**: `enterprise`, `professional`, `homebrew`

**Domain markers**: `quantum`, `ai_safety`, `agentic`, `compliance`, `stress`, `security`, `formal`, `integration`, `property`, `slow`, `unit`, `perf`, `benchmark`

**Component markers**: `api`, `crypto`, `math`, `governance`, `pqc`

Run subsets with: `python -m pytest -m homebrew tests/` or `python -m pytest -m "enterprise and security" tests/`

## Code Style

### TypeScript (from .prettierrc)
- Semicolons: Required
- Quotes: Single quotes
- Line width: 100 characters
- Indentation: 2 spaces
- Trailing commas: ES5 style

### Python
- Black formatter with 120 char line length
- flake8 linting with 120 char line length
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
- Interoperability tests in `tests/interop/` verify cross-language vectors

### Security Requirements
- All crypto operations must be constant-time
- Validate inputs before cryptographic processing
- Never commit `.env` files or secrets
- Use HMAC for integrity checks
- Use `Buffer` for crypto operations in TypeScript
- Post-quantum: ML-KEM-768 (NIST FIPS 203), ML-DSA-65 (NIST FIPS 204)

### Testing Requirements
- Unit tests in appropriate `tests/` tier
- Property-based tests for mathematical functions (fast-check/Hypothesis, min 100 iterations)
- Coverage targets: **80% lines, 80% functions, 70% branches, 80% statements**
- Enterprise coverage target: 95% across all metrics
- Test timeout: 30 seconds (default), 60 seconds (enterprise property tests)
- Tests must be placed in the correct tier directory (L1 through L6)

### When Adding Features
1. Tag files with `@layer` comments
2. Document which axiom your code satisfies
3. Write comprehensive tests in the appropriate tier
4. Update CHANGELOG.md for notable changes
5. Ensure both TypeScript and Python implementations stay in sync

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
6 dimensions with golden ratio weights: **KO, AV, RU, CA, UM, DR**
Each dimension has a 16x16 token grid (256 tokens per language).

### Harmonic Wall
Risk amplification formula: `H(d,R) = phi^d / (1 + e^-R)`
- Exponential cost for deviation from safe operation
- Poincare boundary = infinite cost
- Trustworthy center = near-zero cost

### Quantum Axiom Mesh (5 axioms across 14 layers)
1. **Unitarity** (L2, 4, 7): Norm preservation
2. **Locality** (L3, 8): Spatial bounds
3. **Causality** (L6, 11, 13): Time-ordering
4. **Symmetry** (L5, 9, 10, 12): Gauge invariance
5. **Composition** (L1, 14): Pipeline integrity

Each axiom has a dedicated Python implementation in `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/`.

### Risk Decision Tiers (L13)
- **ALLOW**: Safe operation, low risk
- **QUARANTINE**: Suspicious, needs review
- **ESCALATE**: High risk, requires governance
- **DENY**: Adversarial, blocked

## CI/CD & Deployment

### GitHub Workflows (`.github/workflows/`)
- `ci.yml` - Main CI pipeline (build, test, lint)
- `scbe-tests.yml` / `scbe.yml` - Test execution
- `npm-publish.yml` / `auto-publish.yml` - NPM publishing
- `release.yml` / `release-and-deploy.yml` - Release management
- `docker-publish.yml` - Docker image publishing
- `deploy-aws.yml` - AWS deployment
- `deploy-gke.yml` - Google Kubernetes Engine
- `weekly-security-audit.yml` - Automated security audits
- `auto-merge.yml` / `auto-triage.yml` / `issue-triage.yml` - Automation
- `auto-changelog.yml` - Changelog generation
- `docs.yml` - Documentation generation
- `cross-repo-sync.yml` - Cross-repository sync

### Docker
```bash
docker build -t scbe-aethermoore:latest .   # Multi-stage build (Node + Python + liboqs)
docker run -p 8000:8000 scbe-aethermoore:latest
docker-compose up -d                        # With Redis orchestration
```

The Dockerfile uses a multi-stage build:
1. TypeScript compilation (node:20-alpine)
2. liboqs PQC library build (NIST FIPS 203/204)
3. Python environment setup (python:3.11-slim)
4. Final runtime (exposes ports 8080 + 3000)

### Kubernetes & Cloud
- `k8s/` - Kubernetes manifests
- `aws/` - AWS deployment configs
- `src/lambda/` - AWS Lambda handlers

## Debugging Tips

```bash
npm run check:circular     # Find module dependency issues
npm run typecheck          # Check types before building
npx vitest --watch         # Watch mode for development
python -m pytest -m homebrew tests/  # Quick smoke tests
python -m pytest -m "not slow" tests/  # Skip slow tests
npm run check:deps         # Generate dependency graph SVG
```

## Key Documentation

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `LAYER_INDEX.md` | Complete 14-layer architecture reference |
| `STRUCTURE.md` | Project structure guide |
| `CHANGELOG.md` | Version history |
| `CONTRIBUTING.md` | Contribution guidelines |
| `SECURITY.md` | Security policy |
| `SYSTEM_ARCHITECTURE.md` | Architecture details |
| `docs/` | Full documentation tree (overview, architecture, deployment, industry guides) |
