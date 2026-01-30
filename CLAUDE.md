# CLAUDE.md - Claude Code Instructions for SCBE-AETHERMOORE

## Project Overview

SCBE-AETHERMOORE is a 14-layer hyperbolic geometry-based security system for AI safety and governance. It uses post-quantum cryptography (Kyber768, Dilithium3) with mathematical proofs guaranteeing security properties.

- **Version**: 3.0.0
- **License**: MIT
- **Patent**: USPTO #63/961,403 (pending)

## Quick Commands

### Build
```bash
npm install                    # Install Node.js dependencies
pip install -r requirements.txt # Install Python dependencies
npm run build                  # Build TypeScript
npm run build:watch            # Watch mode
```

### Test
```bash
npm test                       # TypeScript tests (Vitest)
pytest tests/ -v               # Python tests
npm run test:all               # Run both
pytest tests/ -m enterprise    # Enterprise compliance tests only
pytest tests/ -m property      # Property-based tests only
```

### Run
```bash
python -m uvicorn src.api.main:app --reload  # Start FastAPI server (port 8000)
python demo.py                               # Run harmonic cipher demo
python demo_memory_shard.py                  # Memory sealing demo
```

### Code Quality
```bash
npm run format                 # Format TypeScript (Prettier)
npm run format:python          # Format Python (Black)
npm run lint                   # Check TypeScript formatting
npm run lint:python            # Check Python (flake8)
npm run typecheck              # TypeScript type checking
```

## Architecture: 14-Layer Pipeline

The core architecture in `src/harmonic/pipeline14.ts`:

| Layer | File | Function |
|-------|------|----------|
| L1-L4 | `pipeline14.ts` | Complex state, realification, weighted transform, Poincare embedding |
| L5-L7 | `hyperbolic.ts` | Hyperbolic distance, breathing transform, phase transform |
| L8 | `pipeline14.ts` | Multi-well realm distance |
| L9 | `spectralCoherence.ts` | FFT-based pattern stability |
| L10-L11 | `pipeline14.ts` | Spin coherence, triadic temporal |
| L12 | `harmonicScaling.ts` | Risk amplification: H(d) = phi^(d^2) |
| L13 | `pipeline14.ts` | Governance decision (ALLOW/QUARANTINE/DENY) |
| L14 | `audioAxis.ts` | Hilbert telemetry output |

**Key invariants (must be maintained):**
- A1 Unitarity: Norm preservation in L2, L4, L7
- A2 Locality: Spatial bounds in L3, L8
- A3 Causality: Time-ordering in L6, L11, L13
- A4 Symmetry: Gauge invariance in L5, L9, L10, L12
- A5 Composition: Pipeline integrity in L1, L14

## Directory Structure

```
src/
  harmonic/          # Core 14-layer pipeline (CRITICAL)
  crypto/            # Post-quantum cryptography (Kyber, Dilithium, AES-256-GCM)
  api/               # FastAPI REST endpoints (main.py)
  fleet/             # Multi-agent orchestration
  spectral/          # FFT pattern detection
  spiralverse/       # RWP protocol implementation

tests/
  harmonic/          # Layer tests (180+ tests)
  enterprise/        # FIPS, SOC 2 compliance (100+ tests)
  L1-basic/ to L6-adversarial/  # Test tiers
```

## Code Conventions

### File Headers (Required)
```typescript
/**
 * @file filename.ts
 * @module module/name
 * @layer Layer N
 * @component Component Name
 * @version 3.0.0
 */
```

### TypeScript
- Strict mode enabled
- Prettier: 100-char line width, semicolons, single quotes
- JSDoc for public APIs
- Prefer `const`, arrow functions for callbacks

### Python
- PEP 8 + Black (120-char line width)
- Type hints required
- Docstrings for all public functions
- flake8 for linting

### Naming
- Functions: `camelCase`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Layer functions: `layer{N}{Name}` (e.g., `layer5HyperbolicDistance`)

## Testing Requirements

- **Coverage threshold**: 80% lines/functions, 70% branches
- **728+ tests** across the suite
- Run full suite before committing: `npm test && pytest tests/ -v`
- Property-based tests validate mathematical invariants

### Test Markers (pytest)
- `enterprise` - Compliance tests
- `property` - Hypothesis/fast-check tests
- `crypto` - Cryptographic tests
- `slow` - Performance/stress tests

## Commit Messages

Follow Conventional Commits:
- `feat:` new feature
- `fix:` bug fix
- `refactor:` code restructuring
- `test:` test additions
- `docs:` documentation
- `perf:` performance

## Security Notes

- Never commit secrets or API keys
- Use `liboqs` for real post-quantum crypto
- Validate all external inputs at API boundaries
- Cryptographic changes require extra review
- Replay protection: Bloom filter + TTL nonces

## API Endpoints

Base URL: `http://localhost:8000`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |
| POST | `/seal-memory` | Seal data shard |
| POST | `/retrieve-memory` | Retrieve with governance |
| POST | `/verify` | Verify sealed envelope |
| GET | `/audit` | Audit trail |

## Environment Variables

See `.env.example`. Key variables:
- `SCBE_ENV` - Environment (dev/prod)
- `SCBE_KMS_URI` - Key management (aws-kms://, gcp-kms://, vault://, mem://)
- `SCBE_METRICS_BACKEND` - Telemetry (stdout/datadog/prom/otlp)

## Deployment

- **Docker**: Multi-stage build with liboqs
- **AWS Lambda**: `.github/workflows/deploy-aws.yml`
- **GKE**: `.github/workflows/deploy-gke.yml`, manifests in `k8s/`

## Troubleshooting

```bash
# Clean rebuild
rm -rf node_modules dist && npm install && npm run build

# Check API logs
python -m uvicorn src.api.main:app --reload --log-level debug

# Docker no-cache build
docker build --no-cache -t scbe-aethermoore:latest .
```

## Important Reminders

1. **Mathematical rigor**: Changes must maintain axioms A1-A5
2. **Layer dependencies**: Early layers (L1-L3) propagate to all downstream layers
3. **Performance hotspots**: Layer 5 (hyperbolic distance), Layer 9 (FFT)
4. **Always test**: Full suite before commits
5. **Format code**: `npm run format && npm run format:python` before commits
