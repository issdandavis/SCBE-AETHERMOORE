# Architecture Overview
This document is a working architecture map, not the final formula authority. For canonical runtime state and formula precedence, read `CANONICAL_SYSTEM_STATE.md` and `docs/specs/CANONICAL_FORMULA_REGISTRY.md` first.

## 1. Project Structure

```
SCBE-AETHERMOORE/
├── api/                      # FastAPI REST endpoints (Python)
│   ├── main.py               # Main application interface with /v1/authorize, /v1/agents, /v1/fleet/*
│   └── persistence.py        # SQLite persistence layer
├── src/                      # Main source code (TypeScript + Python)
│   ├── index.ts              # Main TypeScript entry point
│   ├── harmonic/             # Harmonic scaling and audio-axis transforms
│   │   └── spiralSeal.ts     # SpiralSeal AES-256-GCM encryption
│   ├── crypto/               # Cryptographic primitives
│   │   ├── envelope.ts       # Envelope encryption with HMAC-based key derivation
│   │   ├── hkdf.ts           # HMAC-based key derivation
│   │   ├── jcs.ts            # JSON Canonicalization Scheme
│   │   ├── kms.ts            # Key Management Service
│   │   └── replayGuard.ts    # Bloom filter replay protection
│   ├── spiralverse/          # roundtable witness protocol v2.1
│   │   └── index.ts          # Policy helpers, tongue validation
│   ├── fleet/                # Fleet management system
│   │   └── fleet-manager.ts  # Agent registration, trust, tasks
│   ├── network/              # Network & routing
│   │   ├── contact-graph.ts  # Contact graph routing
│   │   └── hybrid-crypto.ts  # Hybrid post-quantum encryption
│   ├── spectral/             # Spectral coherence transforms
│   ├── symphonic/            # Symphonic cipher components
│   ├── symphonic_cipher/     # Python AI safety (AIVerifier)
│   │   └── ai_verifier.py    # Intent classification, policy enforcement
│   ├── ai_orchestration/     # Agent orchestration
│   ├── security/             # Security utilities
│   └── scbe_14layer_reference.py  # 14-layer governance pipeline reference implementation
├── tests/                    # Test suites (organized by tier)
│   ├── L1-basic/             # Homebrew quick sanity tests
│   ├── L2-unit/              # Unit tests
│   ├── L3-integration/       # Integration tests
│   ├── L4-property/          # Property-based tests (fast-check)
│   ├── L5-security/          # Security tests
│   ├── L6-adversarial/       # Adversarial robustness tests
│   ├── enterprise/           # Enterprise compliance (SOC2, ISO, FIPS)
│   ├── industry_standard/    # AI safety governance tests
│   ├── spiralverse/          # roundtable witness protocol tests
│   └── *.py                  # Python test modules
├── .github/workflows/        # continuous integration and delivery pipelines
│   ├── ci.yml                # Main continuous integration workflow
│   ├── deploy-aws.yml        # AWS Lambda deployment
│   ├── scbe-tests.yml        # Test orchestration
│   └── release.yml           # Release automation
├── docs/                     # Documentation
├── examples/                 # Usage examples & fleet scenarios
├── SYSTEM_STATUS.md          # Production readiness status
├── CHANGELOG.md              # Change history
├── package.json              # TypeScript dependencies
├── pyproject.toml            # Python dependencies
├── Dockerfile                # Container build
└── docker-compose.yml        # Unified stack deployment
```

## 2. High-Level System Diagram

```
                                 ┌─────────────────────────────────────┐
                                 │         External Clients            │
                                 │ (application interface consumers, agent fleets) │
                                 └─────────────────┬───────────────────┘
                                                   │
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Application Interface Gateway (FastAPI)                    │
│  POST /v1/authorize  │  POST /v1/agents  │  POST /v1/fleet/*  │  GET /health │
└──────────────────────────────────────────────────────────────────────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    │                              │                              │
                    ▼                              ▼                              ▼
        ┌───────────────────┐          ┌───────────────────┐          ┌───────────────────┐
        │ Agent Safety      │          │ 14-Layer          │          │ Fleet Manager     │
        │ (AIVerifier)      │          │ Governance        │          │ (Trust/Tasks)     │
        │                   │          │ Pipeline          │          │                   │
        │                   │          │                   │          │                   │
        │ • classify_intent │          │ Layer 1-14:       │          │ • Agent registry  │
        │ • enforce_policy  │          │ Complex→Audio     │          │ • Trust scoring   │
        │ • constitutional  │          │ Hyperbolic        │          │ • Task lifecycle  │
        │   _check          │          │ Geometry          │          │ • Roundtable      │
        └───────────────────┘          └───────────────────┘          └───────────────────┘
                    │                              │                              │
                    └──────────────────────────────┼──────────────────────────────┘
                                                   │
                                                   ▼
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                        Cryptographic Core                                │
        │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
        │  │ SpiralSeal  │  │  Envelope   │  │ Roundtable  │  │ Six Sacred      │ │
│  │ AES-256-GCM │  │ key deriv.  │  │ Multi-Sig   │  │ Tongues         │ │
        │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
        └─────────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
                              ┌─────────────────────────────────┐
                              │        Persistence Layer        │
                              │    SQLite / In-Memory Cache     │
                              └─────────────────────────────────┘
```

## 3. Core Components

### 3.1. Application Interface Gateway (Python/FastAPI)

**Name:** Governance application interface gateway

**Description:** RESTful application interface providing governance decisions, agent management, and fleet orchestration. Authenticates via `SCBE_api_key` header. Processes requests through the 14-layer governance pipeline for authorization decisions.

**Technologies:** Python 3.11+, FastAPI, Uvicorn, SQLite

**Deployment:** AWS Lambda, Google Cloud Run, Replit, Docker

**Key Endpoints:**
- `POST /v1/authorize` - Main governance decision
- `POST /v1/agents` - Register new agent with spectral identity
- `GET /v1/agents/{id}` - Get agent info
- `POST /v1/consensus` - Multi-signature roundtable approval
- `POST /v1/fleet/run-scenario` - Fleet demo scenarios
- `GET /v1/health` - Health check

### 3.2. 14-Layer Governance Pipeline

**Name:** Hyperbolic Geometry Security Pipeline

**Description:** The core mathematical engine that processes inputs through 14 sequential transformations using hyperbolic geometry in the Poincaré ball model. Each layer adds governance and security properties. Layer-level formulas in this file are descriptive only; the canonical formula source is `docs/specs/CANONICAL_FORMULA_REGISTRY.md`.

**Technologies:** TypeScript, Python (NumPy)

**Layers:**
1. Complex Context - Complex number embedding
2. Realification - Real manifold mapping
3. Weighted Transform - Trust-weighted operations
4. Poincaré Embedding - Hyperbolic ball projection
5. Hyperbolic Metric - Distance calculations
6. Breathing Transform - Dynamic scaling
7. Phase Transform - Angular phase alignment
8. Multi-Well Realms - Stability wells
9. Spectral Coherence - Frequency analysis
10. Spin Coherence - Quantum-inspired coherence
11. Triadic Temporal - Time-based validation
12. Harmonic Wall - canonical wall `H(d*, R) = R^((φ · d*)²)`
13. Composite Risk - Risk aggregation
14. Audio Axis - Final output encoding

### 3.3. AI Safety Framework (AIVerifier)

**Name:** Agent safety and governance module

**Description:** Constitutional safety framework providing intent classification, policy enforcement, output validation, and audit logging. Detects malicious patterns such as ransomware and exploits while also recognizing legitimate security operations.

**Technologies:** Python, Regex pattern matching

**Key Methods:**
- `classify_intent()` - Pattern-based malicious vs legitimate classification
- `enforce_policy()` - Block/approve based on risk level
- `validate_ai_output()` - Detect dangerous commands, credential leaks
- `constitutional_check()` - Anthropic-style response validation
- `get_audit_log()` - Audit trail with timestamps

### 3.4. Fleet Management System

**Name:** Fleet Manager

**Description:** Manages agent swarms with spectral identity registration, trust scoring with auto-quarantine, task lifecycle management, and roundtable consensus for critical operations.

**Technologies:** TypeScript

**Key Features:**
- Agent registration with spectral identity (eigenvalue signature)
- Trust scoring (0.0-1.0) with auto-quarantine at < 0.3
- Task lifecycle: create → assign → complete/retry
- Governance tiers: KO → AV → RU → CA → UM → DR
- Roundtable consensus requiring 4+ tongues

### 3.5. Cryptographic Core

**Name:** Spiral Seal cryptographic suite

**Description:** Production-grade cryptographic primitives including envelope encryption, key derivation, replay protection, and multi-signature protocols.

**Technologies:** Node.js crypto, TypeScript

**Components:**
- **SpiralSeal (SpiralSealSS1)** - AES-256-GCM encryption
- **Envelope System** - HMAC-based key derivation, additional authenticated data coverage, nonce discipline
- **Roundtable witness protocol v2.1** - roundtable multi-signature with Six Sacred Tongues
- **Replay Guard** - Bloom filter replay protection

### 3.6. Six Sacred Tongues (Langues Metric)

**Name:** Sacred Tongue protocol phases

**Description:** Cryptographic protocol phases that govern authorization levels. Each "tongue" represents a governance domain.

| Tongue | Name | Domain |
|--------|------|--------|
| KO | Kor'aelin | Control & Orchestration |
| AV | Avali | I/O & Messaging |
| RU | Runethic | Policy & Constraints |
| CA | Cassisivadan | Logic & Computation |
| UM | Umbroth | Security & Privacy |
| DR | Draumric | Types & Structures |

**Policy Levels:**
- `standard` - Requires KO tongue
- `strict` - Requires RU tongue
- `critical` - Requires RU + UM + DR tongues

## 4. Data Stores

### 4.1. SQLite (Persistence)

**Name:** governance system persistence layer

**Type:** SQLite

**Purpose:** Stores agent registrations, authorization decisions, audit logs, and task states.

**Key Tables:** `agents`, `decisions`, `tasks`, `audit_log`

### 4.2. In-Memory Cache

**Name:** Replay Guard / Trust Cache

**Type:** In-memory Bloom filter + LRU cache

**Purpose:** Fast replay detection and trust score caching.

## 5. External Integrations / Application Interfaces

| Service | Purpose | Integration |
|---------|---------|-------------|
| AWS Lambda | Serverless deployment | SAM/CloudFormation |
| Google Cloud Run | Container deployment | Docker |
| Replit | Development hosting | Nix config |

## 6. Deployment & Infrastructure

**Cloud Providers:** Amazon Web Services, Google Cloud, Replit

**Key Services:**
- AWS Lambda (scbe-agent-swarm-core)
- Google Cloud Run (studio-956103948282.us-central1.run.app)
- Replit (spiral-shield.replit.app)

**Continuous integration pipeline:** GitHub Actions
- `ci.yml` - Build, lint, test
- `deploy-aws.yml` - AWS Lambda deployment
- `scbe-tests.yml` - Multi-tier test execution

**Monitoring:** Custom telemetry via `src/metrics/telemetry.ts`

## 7. Security Considerations

**Authentication:** application interface key header (`SCBE_api_key`)

**Authorization:**
- 14-layer pipeline risk assessment
- Six Sacred Tongues multi-signature
- AIVerifier policy enforcement

**Data Encryption:**
- transport layer security in transit
- AES-256-GCM at rest (SpiralSeal)
- HMAC-based key derivation with SHA-256

**Key Security Features:**
- Replay attack protection (Bloom filter)
- Nonce discipline (session-bound prefixes)
- Constitutional AI safety checks
- Audit logging with timestamps

## 8. Development & Testing Environment

**Local Setup:**
```bash
# Install dependencies
npm install
pip install -r requirements.txt

# Run TypeScript tests
npm test

# Run Python tests
pytest tests/ -v

# Start the application interface locally
uvicorn api.main:app --reload
```

**Testing Frameworks:**
- TypeScript: Vitest, fast-check (property-based)
- Python: Pytest, Hypothesis

**Test Tiers:**
- L1-basic: Homebrew quick sanity
- L2-unit: Unit tests
- L3-integration: Integration tests
- L4-property: Property-based tests
- L5-security: Security tests
- L6-adversarial: Adversarial robustness

**Code Quality:** Prettier (TS), Black/Flake8 (Python)

## 9. Future Considerations / Roadmap

- [ ] hardware security module integration
- [ ] NIST post-quantum cryptography compliance tests (requires liboqs)
- [ ] Byzantine consensus network simulation
- [ ] Side-channel resistance validation on hardware
- [ ] SOC 2 Type II audit preparation

## 10. Project Identification

**Project Name:** SCBE-AETHERMOORE (repository identifier for the Sacred Tongues governance system)

**Repository URL:** https://github.com/issdandavis/SCBE-AETHERMOORE

**Primary Contact:** Issac Daniel Davis (issdandavis@gmail.com)

**Date of Last Update:** 2026-04-08

## 11. Glossary / Legacy Shortforms

| Expanded Label | Legacy / Machine-Stable Shortform | Context / When to Use |
|---|---|---|
| Sacred Tongues governance system / repository identifier | `SCBE`, `SCBE-AETHERMOORE` | Use the expanded form in prose and headings. Keep the shortform only for repository paths, package names, and import statements. |
| governance and geometry core | `SCBE core` | Preferred when referring to the legacy mathematical and runtime engine. |
| roundtable witness protocol | `RWP` | Expand in documentation and comments. Keep `RWP` in protocol labels and code. |
| multi-agent orchestration layer | `HYDRA` | Use the expanded form in prose. Keep `HYDRA` for layer-specific module names. |
| phase-breath hyperbolic governance mapping | `PHDM` | Expand in narrative text. Keep the shortform only where an existing file, command, or spec surface depends on it. |
| canonical compact representation profile | `SS1` | Use the full phrase in human-facing text. Keep `SS1` for internal profile identifiers and code surfaces. |
| application interface gateway | `API Gateway` | Expand everywhere except where exact route prefixes, framework decorators, or published endpoint labels must stay unchanged. |
| command-line interface | `CLI` | Expand in documentation. Keep `CLI` in command names, launcher text, and help output. |
| post-quantum cryptography | `PQC` | Expand in prose. Keep `PQC` in compliance checklists, library references, and implementation labels. |
| additional authenticated data | `AAD` | Expand except in cryptographic function signatures and implementation-specific parameter names. |
| HMAC-based key derivation function | `HKDF` | Expand except inside the actual `hkdf.ts` module, function calls, or test labels that depend on the shortform. |
| Galois/counter mode | `GCM` | Expand in explanatory prose. Keep `GCM` in cipher names and implementation references. |
| hardware security module | `HSM` | Expand in documentation. Keep `HSM` in configuration keys and integration points. |
| transport layer security | `TLS` | Expand except in protocol specifications, certificate details, and cipher-suite lists. |
| continuous integration pipeline | `CI pipeline` | Expand in prose. Keep `CI` in workflow filenames, badges, and automation triggers. |
| Six Sacred Tongues governance phases | `KO/AV/RU/CA/UM/DR` | Use the full phrase in prose. Tongue codes remain mandatory in machine-facing protocol and tokenizer logic. |
| Poincare ball | none | Always use the full descriptive phrase for the hyperbolic geometry model. |
| constitutional safety framework | `Constitutional AI` | Prefer the expanded phrase in system docs. Keep the legacy phrase only when referencing the external concept name. |
| spectral identity | none | Use the full descriptive phrase for the eigenvalue-based agent fingerprint. |
