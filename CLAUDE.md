# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SCBE-AETHERMOORE** is an AI safety and governance framework using hyperbolic geometry (Poincare ball model) for exponential cost scaling of adversarial behavior. Implements a **14-layer security pipeline** with post-quantum cryptography.

**Core Innovation**: Adversarial intent costs exponentially more the further it drifts from safe operation, making attacks computationally infeasible.

| Aspect | Details |
|--------|---------|
| **Languages** | TypeScript (canonical), Python (reference) |
| **Node** | >= 18.0.0 |
| **Python** | >= 3.11 |
| **Test Frameworks** | Vitest (TS), pytest (Python) |
| **Property Testing** | fast-check (TS), Hypothesis (Python) |
| **API** | FastAPI + Uvicorn |
| **TypeScript** | ^5.8.3, target ES2022, CommonJS |
| **Package Entry** | `./dist/src/index.js` |

## Common Commands

```bash
# Build
npm run build              # Clean + compile TypeScript
npm run build:src          # Compile TypeScript only (no clean)
npm run typecheck          # Type check only (no emit)

# Test - TypeScript
npm test                   # Run all TS tests (vitest run)
npx vitest run tests/harmonic/pipeline14.test.ts  # Run single test file
npx vitest run -t "test name pattern"             # Run single test by name
npx vitest --watch         # Watch mode

# Test - Python
python -m pytest tests/ -v                         # Run all Python tests
python -m pytest tests/test_harmonic_scaling.py -v  # Run single file
python -m pytest tests/test_foo.py::test_bar -v     # Run single test function
python -m pytest -m homebrew tests/                 # Quick smoke tests
python -m pytest -m "enterprise and security" tests/ # Subset by markers
python -m pytest -m "not slow" tests/               # Skip slow tests
python -m pytest -x tests/                          # Stop at first failure (CI mode)

# Code quality
npm run format             # Prettier (TS)
npm run format:python      # Black, 120 char (Python)
npm run lint               # Prettier --check (TS)
npm run lint:python        # flake8, 120 char (Python)
npm run check:circular     # Circular dependency check (madge)

# API server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Docker
npm run docker:build && npm run docker:run
```

## Critical Gotcha: Dual `symphonic_cipher` Packages

There are **two** `symphonic_cipher/` directories with **different** math:

| Location | Formula | Purpose |
|----------|---------|---------|
| **Root** `symphonic_cipher/` | `H(d,R) = R^(d²)` | Exponential cost multiplier |
| **`src/symphonic_cipher/`** | `H(d,pd) = 1/(1+d+2*pd)` | Bounded safety score in (0,1] |

**Import collision**: Many test files do `sys.path.insert(0, "src/")`, which causes `import symphonic_cipher` to resolve to the `src/` version instead of root. Tests use `_IS_SAFETY_SCORE` flag to detect which variant loaded. When writing new tests, be explicit about which module you need.

The `tests/conftest.py` adds the project root to `sys.path` and patches `ai_brain` submodule aliases for legacy import paths.

## liboqs PQC Migration

Newer versions of liboqs renamed algorithms:
- `Dilithium3` → `ML-DSA-65`
- `Kyber768` → `ML-KEM-768`

Use the `_select_dsa_algorithm()` / `_select_kem_algorithm()` helper pattern to try the new name first, then fall back to the old name.

## Architecture

### 14-Layer Pipeline

| Layers | Function | Key Files |
|--------|----------|-----------|
| **L1-2** | Complex context → Realification | `src/harmonic/pipeline14.ts` |
| **L3-4** | Weighted transform → Poincare embedding | `languesMetric.ts`, `pipeline14.ts` |
| **L5** | Hyperbolic distance `dH = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))` | `hyperbolic.ts` |
| **L6-7** | Breathing transform + Mobius phase | `hyperbolic.ts`, `adaptiveNavigator.ts` |
| **L8** | Multi-well realms (Hamiltonian CFI) | `hamiltonianCFI.ts` |
| **L9-10** | Spectral + spin coherence (FFT) | `spectral/index.ts` |
| **L11** | Triadic temporal distance | `causality_axiom.py` |
| **L12** | Harmonic wall: `H(d,pd) = 1/(1+d_H+2*pd)` | `harmonicScaling.ts` |
| **L13** | Risk decision: ALLOW / QUARANTINE / ESCALATE / DENY | Swarm governance |
| **L14** | Audio axis (FFT telemetry) | `audioAxis.ts`, `vacuumAcoustics.ts` |

### Quantum Axiom Mesh (5 axioms across 14 layers)

Each axiom has a Python implementation in `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/`:

1. **Unitarity** (L2, 4, 7): Norm preservation — `unitarity_axiom.py`
2. **Locality** (L3, 8): Spatial bounds — `locality_axiom.py`
3. **Causality** (L6, 11, 13): Time-ordering — `causality_axiom.py`
4. **Symmetry** (L5, 9, 10, 12): Gauge invariance — `symmetry_axiom.py`
5. **Composition** (L1, 14): Pipeline integrity — `composition_axiom.py`

### Sacred Tongues (Langues Metric)

6 dimensions with golden ratio weights: **KO, AV, RU, CA, UM, DR**. Each has a 16x16 token grid (256 tokens per language). Tongue weights scale by phi: KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09.

### Risk Decision Tiers (L13)

- **ALLOW**: Safe operation
- **QUARANTINE**: Suspicious, needs review
- **ESCALATE**: High risk, requires governance
- **DENY**: Adversarial, blocked

## Project Structure (Key Directories)

```
src/
├── harmonic/              # CORE: 14-layer pipeline (TypeScript)
├── crypto/                # PQC primitives (ML-KEM-768, ML-DSA-65, AES-256-GCM)
├── symphonic/             # TypeScript port of Symphonic Cipher
├── symphonic_cipher/      # Python reference (CAUTION: import collision, see above)
│   └── scbe_aethermoore/
│       ├── ai_brain/      # 21D brain mapping
│       ├── axiom_grouped/ # 5 Quantum Axiom implementations
│       └── concept_blocks/
│           ├── decide.py, plan.py, sense.py, steer.py, coordinate.py  # Navigation primitives
│           ├── web_agent/  # Autonomous web agent (semantic antivirus, publishers, tongue transport)
│           ├── cstm/       # Story engine, player agent, nursery, kernel
│           ├── context_catalog/      # 25 task archetype mappings
│           ├── context_credit_ledger/ # MMCCL blockchain credits
│           └── heart_vault/          # Core vault logic
├── ai_brain/              # 21D AI Brain Mapping (TypeScript)
├── fleet/                 # Multi-agent orchestration
├── gateway/               # Unified SCBE API Gateway
├── api/                   # REST API (FastAPI Python + Express TS)
├── spectral/              # FFT coherence analysis (L9-10)
├── network/               # Network security (SpaceTor router)
└── selfHealing/           # Failure recovery

agents/                    # Root-level agent implementations
├── antivirus_membrane.py  # Threat scanning + turnstile
├── browser_agent.py       # SCBE-governed browser automation
├── kernel_antivirus_gate.py # Kernel telemetry policy engine
└── extension_gate.py      # Enemy-first extension gating

packages/wit/              # WASM Component Model interfaces
├── scbe-crypto/           # KEM, DSA, Symmetric, Hashing, Spiral Seal
├── scbe-transform/        # Tongue Encoder, Harmonics, Pipeline
└── host/                  # Unified host API

scripts/                   # Build, training, deployment scripts
training-data/             # SFT/DPO training data, game scenarios, evals
deploy/                    # Hetzner VPS deploy, Docker Compose, .env template
```

### npm Package Exports

```
scbe-aethermoore            # Main
scbe-aethermoore/harmonic   # 14-layer pipeline
scbe-aethermoore/symphonic  # Symphonic cipher
scbe-aethermoore/crypto     # Cryptographic primitives
scbe-aethermoore/spiralverse # Spiralverse protocol
scbe-aethermoore/tokenizer  # Sacred Tongues tokenizer
scbe-aethermoore/phdm       # Polyhedral Hamiltonian Defense Manifold
scbe-aethermoore/ai_brain   # 21D AI Brain Mapping
scbe-aethermoore/governance # Governance module
```

## Test Architecture

### Tiered Tests (L1-L6)

| Tier | Purpose | Framework |
|------|---------|-----------|
| **L1-basic** | Smoke / sanity | Vitest |
| **L2-unit** | Isolated functions | Vitest |
| **L3-integration** | Component interactions | Vitest |
| **L4-property** | Random-input proofs | fast-check (100+ iterations) |
| **L5-security** | Crypto boundary enforcement | Vitest |
| **L6-adversarial** | Attack simulations | Vitest |

### File Naming

- **TypeScript**: `{module}.{tier}.test.ts` (e.g., `spectral.property.test.ts`)
- **Python**: `test_{module}.py` or `test_{module}_{context}.py`

### pytest Configuration (pytest.ini)

- `asyncio_mode = auto` — async tests just work
- `--strict-markers` — typos in markers cause failures
- `--basetemp=artifacts/pytest_tmp` — temp files go to artifacts/
- Coverage: `source = src`, targets 80% lines/functions/statements, 70% branches

### pytest Markers

**Tier**: `enterprise`, `professional`, `homebrew`
**Domain**: `quantum`, `ai_safety`, `agentic`, `compliance`, `stress`, `security`, `formal`, `integration`, `property`, `slow`, `unit`, `perf`, `benchmark`
**Component**: `api`, `crypto`, `math`, `governance`, `pqc`

## Code Style

### TypeScript (.prettierrc)
- Semicolons required, single quotes, 100 char lines, 2-space indent, ES5 trailing commas

### Python
- Black (120 char), flake8 (120 char), Google-style docstrings, type hints on all functions

### File Headers
```typescript
/**
 * @file filename.ts
 * @module harmonic/module-name
 * @layer Layer X, Layer Y
 * @component Component Name
 */
```

Add axiom compliance comments where applicable: `// A4: Clamping` or `# A2: Unitarity check`.

## Development Guidelines

### Dual Implementation Strategy
- **TypeScript is canonical** (production). Update TS first, then Python.
- Cross-language parity tests in `tests/cross-language/` and `tests/interop/`.

### When Adding Features
1. Tag files with `@layer` comments
2. Document which axiom your code satisfies
3. Write tests in the correct tier directory (L1 through L6)
4. Update CHANGELOG.md for notable changes
5. Keep TS and Python in sync

### Commit Convention
```
feat(harmonic): add layer X implementation
fix(crypto): resolve timing attack in envelope
test(harmonic): add property-based tests
refactor(spectral): optimize FFT implementation
```

## CI/CD

### Key Workflows (`.github/workflows/`)
- `ci.yml` — Main pipeline (build, test, lint)
- `npm-publish.yml` / `auto-publish.yml` — NPM publishing
- `release-and-deploy.yml` — Release management
- `docker-publish.yml` — Docker image publishing
- `weekly-security-audit.yml` — Automated security audits

### Docker
Multi-stage build: Node 20 (TS compile) → liboqs (PQC) → Python 3.11 → runtime (ports 8080 + 3000).

## Key Documentation

| File | Purpose |
|------|---------|
| `LAYER_INDEX.md` | Complete 14-layer architecture reference |
| `SPEC.md` | SCBE Kernel Specification (canonical) |
| `SYSTEM_ARCHITECTURE.md` | Detailed architecture |
| `docs/LANGUES_WEIGHTING_SYSTEM.md` | Langues metric deep dive |
| `docs/hydra/ARCHITECTURE.md` | HYDRA orchestration |
| `docs/PUBLISHING.md` | Safe release flow |
