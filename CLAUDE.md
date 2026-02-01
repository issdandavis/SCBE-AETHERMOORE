# CLAUDE.md - Project Instructions for AI Assistants

## Critical: Read This First

**SCBE-AETHERMOORE** is a security framework. Mistakes here can create vulnerabilities. Before making any change:

1. **Run the pre-commit checks** (see below)
2. **Understand which layer you're touching** - the 14-layer architecture has invariants
3. **Never skip tests** - especially L5-security and L6-adversarial

### Pre-Commit Checklist (MUST PASS)

```bash
npm run typecheck          # Zero errors required
npm test -- tests/L1-basic # Smoke tests
npm test -- tests/L5-security  # Security boundaries
npm run check:circular     # No circular deps allowed
```

If you're touching crypto code, also run:
```bash
npm test -- tests/spiralverse  # RWP envelope tests
python -m pytest tests/industry_standard/test_nist_pqc_compliance.py -v
```

---

## Project Overview

AI safety and governance framework using hyperbolic geometry (Poincaré ball model) for exponential cost scaling of adversarial behavior. Implements a **14-layer security pipeline** with post-quantum cryptography (Kyber768 + ML-DSA-65).

**Core Innovation**: Adversarial intent costs exponentially more the further it drifts from safe operation, making attacks computationally infeasible.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Languages** | TypeScript (canonical), Python (reference) |
| **Node Version** | >= 18.0.0 |
| **Python Version** | >= 3.9 |
| **Test Frameworks** | Vitest (TS), pytest (Python) |
| **API Framework** | FastAPI + Uvicorn |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **Payments** | Stripe |

---

## Common Gotchas (Learn From Past Mistakes)

### 1. TypeScript/Python Parity
The TypeScript implementation is canonical. If you change math in TS, you MUST update Python too:
```bash
# After any harmonic/ changes, run parity tests
npm test -- tests/cross-language/
```

### 2. Nonce Reuse in RWP
**NEVER** reuse nonces in `src/spiralverse/`. The RWP protocol enforces uniqueness - reusing nonces breaks security guarantees. Each envelope must have a unique nonce.

### 3. TTL Enforcement
Messages have TTLs. Don't bypass TTL checks "for testing" - write proper test fixtures instead.

### 4. Hyperbolic Distance Invariant
Layer 5 (`hyperbolic.ts`) computes distances that MUST satisfy the triangle inequality in hyperbolic space. Don't "optimize" this code without running property tests:
```bash
npm test -- tests/L4-property/
```

### 5. The Golden Ratio is Everywhere
`φ = 1.618...` appears in harmonic weights, Sacred Tongue dimensions, and scaling factors. If you see magic numbers like `1.618`, `2.618`, `4.236`, they're powers of phi. Don't "clean them up."

### 6. Billing System is New
The `api/billing/` module was recently added. It uses Stripe webhooks. If you modify it:
- Test with Stripe CLI: `stripe listen --forward-to localhost:8000/v1/billing/webhooks/stripe`
- Check rate limiting still works per tier

---

## Project Structure

```
src/
├── harmonic/           # CORE: 14-layer pipeline (TypeScript) [CRITICAL]
│   ├── pipeline14.ts   # Main pipeline - touches all layers
│   ├── hyperbolic.ts   # Poincaré ball operations (L5-7) [SECURITY-CRITICAL]
│   ├── harmonicScaling.ts  # Harmonic wall (L12) - risk amplification
│   └── sacredTongues.ts    # 6×256 tokenizer
├── crypto/             # Cryptographic primitives [SECURITY-CRITICAL]
├── spiralverse/        # RWP protocol & envelope encryption [SECURITY-CRITICAL]
├── api/                # FastAPI REST server
│   ├── main.py         # Entry point, route registration
│   ├── auth.py         # API key verification, rate limiting
│   ├── billing/        # Stripe integration (NEW)
│   │   ├── routes.py   # /v1/billing/* endpoints
│   │   ├── stripe_client.py  # Stripe API wrapper
│   │   ├── webhooks.py # Subscription lifecycle handlers
│   │   ├── tiers.py    # FREE/STARTER/PRO/ENTERPRISE config
│   │   └── database.py # SQLAlchemy models
│   └── keys/           # API key management (NEW)
│       ├── routes.py   # /v1/keys/* endpoints
│       └── generator.py # Secure key generation
├── fleet/              # Multi-agent orchestration
├── symphonic/          # Audio-based crypto
└── [other modules...]

tests/
├── L1-basic/           # Smoke tests (ALWAYS RUN)
├── L2-unit/            # Unit tests
├── L3-integration/     # Integration tests
├── L4-property/        # Property-based tests (math correctness)
├── L5-security/        # Security boundary tests (ALWAYS RUN)
├── L6-adversarial/     # Attack simulations
└── [domain-specific tests...]
```

---

## 14-Layer Architecture

**This is the core of the system. Understand it before changing anything.**

```
INPUT → [Layers 1-14] → DECISION (ALLOW/QUARANTINE/DENY)

L1-2:   Complex context → Realification
L3-4:   Weighted transform → Poincaré embedding
L5:     Hyperbolic distance [INVARIANT - DO NOT MODIFY LIGHTLY]
L6-7:   Breathing transform + Möbius phase
L8:     Multi-well realms
L9-10:  Spectral + spin coherence
L11:    Triadic temporal distance
L12:    Harmonic wall H(d,R) = φᵈ / (1 + e⁻ᴿ) [RISK AMPLIFICATION]
L13:    Risk decision gate
L14:    Audio axis (FFT telemetry)
```

### Quantum Axiom Mesh (5 axioms organizing the 14 layers)

| Axiom | Layers | Property | Breaking This = Security Bug |
|-------|--------|----------|------------------------------|
| **Unitarity** | 2, 4, 7 | Norm preservation | Yes |
| **Locality** | 3, 8 | Spatial bounds | Yes |
| **Causality** | 6, 11, 13 | Time-ordering | Yes |
| **Symmetry** | 5, 9, 10, 12 | Gauge invariance | Yes |
| **Composition** | 1, 14 | Pipeline integrity | Yes |

---

## API Endpoints

### Core Governance
```bash
POST /v1/validate    # Validate an action, returns ALLOW/QUARANTINE/DENY
POST /v1/authorize   # Authorize with full pipeline
GET  /health         # Health check
```

### Billing (requires API key)
```bash
POST /v1/billing/checkout     # Create Stripe checkout session
POST /v1/billing/portal       # Customer self-service portal
GET  /v1/billing/subscription # Current subscription status
GET  /v1/billing/usage        # Usage stats for billing period
POST /v1/billing/webhooks/stripe  # Stripe webhook (no auth, uses signature)
```

### API Keys
```bash
POST   /v1/keys          # Create new API key
GET    /v1/keys          # List all keys (masked)
DELETE /v1/keys/{id}     # Revoke a key
POST   /v1/keys/{id}/rotate  # Rotate key (new key, revoke old)
```

### Rate Limits by Tier

| Tier | Per Minute | Monthly | Price |
|------|-----------|---------|-------|
| FREE | 10 | 1000/day | $0 |
| STARTER | 100 | 100,000 | $99/mo |
| PRO | 600 | 1,000,000 | $499/mo |
| ENTERPRISE | Unlimited | Unlimited | Custom |

---

## Common Commands

```bash
# Setup
npm install
pip install -r requirements.txt

# Build & Check
npm run build              # Compile TypeScript
npm run typecheck          # Type check only (fast)
npm run check:circular     # Circular dependency check

# Test (in order of importance)
npm test                   # All TypeScript tests
npm test -- tests/L1-basic # Quick smoke test
npm test -- tests/L5-security  # Security tests
npm test -- --coverage     # With coverage report
python -m pytest tests/ -v # Python tests

# Format
npm run format             # Prettier (TS)
npm run lint               # Check formatting

# Run
python -m uvicorn api.main:app --reload --port 8000
```

---

## Development Guidelines

### When Changing Crypto Code (`crypto/`, `spiralverse/`, `pqc/`)
1. Run NIST compliance tests: `python -m pytest tests/industry_standard/test_nist_pqc_compliance.py`
2. Check for timing attacks: `npm test -- tests/L5-security`
3. Never use non-constant-time comparisons for secrets
4. Always use `crypto.timingSafeEqual()` or equivalent

### When Changing Harmonic Pipeline (`harmonic/`)
1. Run property tests: `npm test -- tests/L4-property`
2. Run cross-language parity: `npm test -- tests/cross-language`
3. Update Python implementation to match
4. Tag file with `@layer` comment

### When Changing Billing (`api/billing/`)
1. Test webhook handling: `stripe trigger checkout.session.completed`
2. Verify rate limits work: Check `_rate_limit_cache` behavior
3. Test subscription state transitions
4. Never store raw API keys - only hashes

### TypeScript/Python Parity
- TypeScript is canonical (production)
- Python is reference (research/validation)
- Always update TypeScript first, then Python
- `tests/cross-language/` validates parity

---

## Code Style

### TypeScript
- Semicolons: Required
- Quotes: Single quotes
- Line width: 100 characters
- Indentation: 2 spaces
- Trailing commas: ES5 style

### Python
- Black formatter, 120 char line length
- Google-style docstrings
- Type hints required

### File Headers
```typescript
/**
 * @file filename.ts
 * @module harmonic/module-name
 * @layer Layer 5, Layer 6
 * @component Hyperbolic Distance Calculator
 */
```

---

## Key Mathematical Concepts

### Sacred Tongues (Langues Metric)
6 dimensions weighted by powers of golden ratio φ:
- KO (w=1), AV (w=φ), RU (w=φ²), CA (w=φ³), UM (w=φ⁴), DR (w=φ⁵)

### Harmonic Wall
```
H(d,R) = φᵈ / (1 + e⁻ᴿ)
```
- d = hyperbolic distance from safe center
- R = accumulated risk score
- At Poincaré boundary (d→∞): cost → ∞
- At center (d≈0): cost → 0

### Poincaré Ball
All operations happen in the unit ball ‖u‖ < 1. Points near the boundary have exponentially higher costs. This is the core security property.

---

## Debugging

```bash
# Find circular dependencies
npm run check:circular

# Type errors
npm run typecheck

# Watch mode for rapid iteration
npm test -- --watch

# Quick Python smoke test
python -m pytest -m homebrew tests/

# Check Stripe webhook delivery
stripe listen --forward-to localhost:8000/v1/billing/webhooks/stripe

# Database inspection (dev only)
sqlite3 scbe_billing.db ".tables"
sqlite3 scbe_billing.db "SELECT * FROM customers"
```

---

## Environment Variables

```bash
# Required for billing
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PRO=price_...

# Optional
DATABASE_URL=sqlite:///./scbe_billing.db  # or postgresql://...
SQL_DEBUG=false
```

---

## Commit Convention

```
feat(harmonic): add layer X implementation
fix(crypto): resolve timing attack in envelope
fix(billing): handle subscription cancellation edge case
docs(api): update endpoint examples
test(harmonic): add property-based tests
refactor(spectral): optimize FFT implementation
chore(deps): bump typedoc to 0.27.0
```

---

## RWP Protocol (Spiralverse)

Rotating Waveform Protocol provides envelope encryption:
- **Nonce rotation**: Each message gets unique nonce (CRITICAL - never reuse)
- **TTL enforcement**: Messages expire (don't bypass for "convenience")
- **Tamper-evident**: HMAC signatures detect modification
- **Post-quantum**: Kyber768 key encapsulation

---

## Hyperbolic Video Generation

Extended capability for procedural video using hyperbolic geometry:

### Sacred Tongue → Julia Set Mapping

| Tongue | Intent | c Parameter | Visual |
|--------|--------|-------------|--------|
| Kor'aelin | Flow/Stability | -0.4 + 0.6i | Dendrite |
| Avali | Context/Boundary | -0.8 + 0.156i | Siegel disk |
| Runethic | Binding/Chaos | -0.12 + 0.74i | Douady rabbit |
| Cassisivadan | Bitcraft/Shatter | 0.285 + 0.01i | Dust |
| Umbroth | Veil/Mystery | -1.0 + 0i | Cauliflower |
| Draumric | Structure/Order | -0.75 + 0.11i | San Marco |

### Dependencies
```bash
pip install numpy matplotlib moviepy
# GPU acceleration: pip install cupy
```

---

## Docker

```bash
docker build -t scbe-aethermoore:latest .
docker run -p 8000:8000 scbe-aethermoore:latest
docker-compose up -d  # With Redis
```

---

## When Things Break

### "ERESOLVE could not resolve" on npm install
Check for version conflicts in devDependencies. typedoc must support your TypeScript version:
- TS 5.9.x requires typedoc ^0.27.0

### Tests fail after harmonic/ changes
Run property tests first - they catch math errors:
```bash
npm test -- tests/L4-property
```

### Rate limiting not working
Check `_rate_limit_cache` in `api/auth.py`. For production, this should use Redis, not in-memory dict.

### Stripe webhooks not received
1. Check `STRIPE_WEBHOOK_SECRET` is set
2. Run `stripe listen --forward-to localhost:8000/v1/billing/webhooks/stripe`
3. Check signature verification in `stripe_client.py`
