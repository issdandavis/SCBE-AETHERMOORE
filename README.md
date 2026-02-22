# SCBE-AETHERMOORE

## Quantum-Resistant AI Agent Governance

**The mathematically-proven security layer your AI fleet needs.**

[![Tests](https://img.shields.io/badge/tests-950%20passing-brightgreen)](.)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](.)
[![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue)](.)
[![Release & Deploy](https://github.com/issdandavis/SCBE-AETHERMOORE/actions/workflows/release-and-deploy.yml/badge.svg)](https://github.com/issdandavis/SCBE-AETHERMOORE/actions/workflows/release-and-deploy.yml)

---

## What Is This?

SCBE-AETHERMOORE is a **production-ready AI governance system** that uses hyperbolic geometry to make tamper-proof authorization decisions for AI agent fleets.

Think of it as a **mathematical bouncer** for your AI agents - one that can't be fooled by prompt injection, can't be bribed, and mathematically proves every decision.

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **14-Layer Security Pipeline** | Every request passes through 14 mathematical transformations |
| **Hyperbolic Geometry** | Decisions mapped to Poincaré ball - center=safe, edge=risky |
| **Rogue Agent Detection** | Swarms detect intruders through pure math - no messaging required |
| **Multi-Signature Consensus** | Critical operations require cryptographic agreement |
| **Zero False Positives** | Legitimate agents never get flagged |
| **Jam-Resistant** | Works without RF/network - agents "feel" each other mathematically |

### Benchmark Results

```
SCBE (Harmonic + Langues):  95.3% detection rate
ML Anomaly Detection:       89.6%
Pattern Matching:           56.6%
Linear Threshold:           38.7%
```

---

## Architecture Docs (Index)

- **SCBE Kernel Spec (Canonical):** `SPEC.md`
- **Langues Weighting System (Layer 3 + 6):** `docs/LANGUES_WEIGHTING_SYSTEM.md`
- **HYDRA Orchestration (Execution Plane):** `docs/hydra/ARCHITECTURE.md`
- **Concept Glossary (Indexable Terms):** `CONCEPTS.md`
- **Research Drafts (Non-Canonical):** `docs/research/README.md`

---


## What npm users actually get

When users install `scbe-aethermoore` from npm, they get:

- compiled JS/TypeScript API from `dist/src`
- CLI entrypoint (`scbe`)
- SixTongues Python helper assets
- starter fleet templates + use-case scenarios from `examples/npm/`

They do **not** receive the full mono-repo runtime stack (e.g., all docs, test suites, and UI source).

## Pre-made AI agents and use-case starters

Yes — adding pre-made agents and scenarios is a good idea, if positioned as **starter templates** (not production policy).

Included templates:

- `examples/npm/agents/fraud_detection_fleet.json`
- `examples/npm/agents/research_browser_fleet.json`
- `examples/npm/use-cases/financial_fraud_triage.json`
- `examples/npm/use-cases/autonomous_research_review.json`

These give users a concrete launch path for common fleet patterns while keeping canonical security behavior in `SPEC.md`.

## Live Demos

### 1. Rogue Agent Detection
```bash
curl https://YOUR_API/v1/demo/rogue-detection
```
Watch 6 legitimate agents detect and quarantine a phase-null intruder using only math.

### 2. Swarm Coordination
```bash
curl https://YOUR_API/v1/demo/swarm-coordination?agents=20
```
See 20 agents self-organize without any central coordinator.

### 3. Pipeline Visualization
```bash
curl "https://YOUR_API/v1/demo/pipeline-layers?trust=0.8&sensitivity=0.7"
```
See exactly how each of the 14 layers processes a request.

---

## Architecture

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
Layer 12:    score = 1 / (1 + d_H + 2 * phaseDeviation)  [HARMONIC SCALING]
Layer 13:    Risk' → ALLOW / QUARANTINE / DENY
Layer 14:    Audio Axis (FFT telemetry)

═══════════════════════════════════════════════════════════════════
```

### The Six Sacred Tongues

| Tongue | Code | Domain | Weight |
|--------|------|--------|--------|
| Kor'aelin | KO | Control & Orchestration | 1.00 |
| Avali | AV | I/O & Messaging | 1.62 |
| Runethic | RU | Policy & Constraints | 2.62 |
| Cassisivadan | CA | Logic & Computation | 4.24 |
| Umbroth | UM | Security & Privacy | 6.85 |
| Draumric | DR | Types & Structures | 11.09 |

**Policy Levels:**
- `standard` → KO required
- `strict` → RU required
- `critical` → RU + UM + DR required

---

## Quick Start

### Docker (Fastest)
```bash
docker run -p 8080:8080 -e SCBE_API_KEY=your-key ghcr.io/issdandavis/scbe-aethermoore
```

### Docker Terminal Control (No UI)
```powershell
# Doctor + health checks
.\scripts\scbe_docker_status.ps1 -Action doctor -Stack api

# Start/stop stack
.\scripts\scbe_docker_status.ps1 -Action up -Stack api
.\scripts\scbe_docker_status.ps1 -Action down -Stack api
```

See `docs/DOCKER_TERMINAL_OPERATIONS.md` for full stack control commands.

Docker MCP terminal-only workflow:
```powershell
.\scripts\scbe_mcp_terminal.ps1 -Action doctor
.\scripts\scbe_mcp_terminal.ps1 -Action tools
.\scripts\scbe_mcp_terminal.ps1 -Action gateway
```

### Local Development
```bash
git clone https://github.com/issdandavis/SCBE-AETHERMOORE.git
cd SCBE-AETHERMOORE
npm install && pip install -r requirements.txt
export SCBE_API_KEY="your-key"
uvicorn api.main:app --port 8080
```

### Cloud Deployment

**AWS Lambda:**
```bash
cd aws && sam build && sam deploy --guided
```

**Google Cloud Run:**
```bash
cd deploy/gcloud && ./deploy.sh YOUR_PROJECT_ID
```

---

## Memory Sealing API (MVP)

The MVP memory API in `src/api/main.py` persists sealed blobs so they can be retrieved and unsealed later. Configure the storage backend before running the API server:

```bash
# Required: where sealed blobs are stored on disk
export SCBE_STORAGE_PATH="./sealed_blobs"

# Optional: storage backend selection (default: filesystem)
export SCBE_STORAGE_BACKEND="filesystem"
```

The API will write one JSON file per 6D position in the configured directory. Ensure the process has read/write access to this path when using `/seal-memory` and `/retrieve-memory`.

---

## Fleet API (Pilot Demo)

Run a complete fleet scenario through the 14-layer SCBE pipeline:
## API Usage

### Authorize an Agent Action
```bash
curl -X POST https://YOUR_API/v1/authorize \
  -H "SCBE_api_key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "fraud-detector-001",
    "action": "READ",
    "target": "transaction_stream",
    "context": {"sensitivity": 0.3}
  }'
```

**Response:**
```json
{
  "decision": "ALLOW",
  "decision_id": "dec_a1b2c3d4e5f6",
  "score": 0.847,
  "explanation": {
    "trust_score": 0.8,
    "distance": 0.234,
    "risk_factor": 0.09
  },
  "token": "scbe_a1b2c3d4_dec_a1b2",
  "expires_at": "2026-01-15T10:05:00Z"
}
```

### Run Fleet Scenario
```bash
curl -X POST https://YOUR_API/v1/fleet/run-scenario \
  -H "SCBE_api_key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_name": "fraud-detection",
    "agents": [
      {"agent_id": "detector-001", "name": "Fraud Detector", "initial_trust": 0.85},
      {"agent_id": "scorer-002", "name": "Risk Scorer", "initial_trust": 0.75}
    ],
    "actions": [
      {"agent_id": "detector-001", "action": "READ", "target": "transactions"},
      {"agent_id": "scorer-002", "action": "WRITE", "target": "risk_db"}
    ]
  }'
```

---

## Use Cases

| Industry | Application |
|----------|-------------|
| **Financial Services** | Fraud detection AI that can't be manipulated |
| **Healthcare** | HIPAA-compliant AI decisions with audit trails |
| **Defense/Aerospace** | Jam-resistant swarm coordination |
| **Autonomous Systems** | Multi-agent coordination without central authority |
| **Enterprise AI** | Constitutional safety checks for LLM agents |

---

## Test Status

| Suite | Status | Count |
|-------|--------|-------|
| TypeScript | ✅ Passing | 950/950 |
| Python | ✅ Passing | 97/103 |

---

## Technical Specifications

### Post-Quantum Cryptography
- **Kyber768**: Key exchange (NIST approved)
- **Dilithium3**: Digital signatures (NIST approved)
- **AES-256-GCM**: Symmetric encryption
- **HKDF-SHA256**: Key derivation

### Mathematical Foundations
- **Poincaré Ball Model**: Hyperbolic geometry
- **Hamiltonian Mechanics**: Energy conservation
- **Möbius Addition**: Gyrogroup operations
- **Quasicrystal Lattice**: 6D → 3D projection

---

## Resources & Links

### Live Demo & Packages
- **Live Demo**: [SCBE Swarm Coordinator](https://scbe-aethermoore-ezaociw8wy6t5rnaynzvzc.streamlit.app/) - Interactive Streamlit dashboard
- **npm Package**: [scbe-aethermoore](https://www.npmjs.com/package/scbe-aethermoore) - `npm install scbe-aethermoore`
- **GitHub Pages**: [Project Site](https://issdandavis.github.io/SCBE-AETHERMOORE/)

### Documentation (Notion)
- [SCBE-AETHERMOORE System State Report (Feb 2026)](https://aethermoorgames.notion.site/) - Production-ready docs
- [SCBE + Sacred Eggs Integration Pack](https://aethermoorgames.notion.site/) - Complete integration guide
- [Phase-Breath Hyperbolic Governance (14-Layer Core v1.2)](https://aethermoorgames.notion.site/) - Mathematical core mapping
- [Polly Pads: Mode-Switching Architecture](https://aethermoorgames.notion.site/) - Autonomous AI architecture
- [Topological Linearization for CFI](https://aethermoorgames.notion.site/) - Patent analysis & Hamiltonian paths

### Products & Templates
- **Gumroad**: [aethermoorgames.gumroad.com](https://aethermoorgames.gumroad.com) - Notion templates, AI workflow tools
- **Ko-fi**: [ko-fi.com/izdandavis](https://ko-fi.com/izdandavis) - Support development

### Social & Updates
- **X/Twitter**: [@davisissac](https://x.com/davisissac)
- **Substack**: [Issac "Izreal" Davis](https://substack.com/profile/153446638-issac-izreal-davis)

---

## Contact

**Issac Daniel Davis**
Email: issdandavis@gmail.com
GitHub: [@issdandavis](https://github.com/issdandavis)

---

## License

Proprietary. Contact for licensing inquiries.

---

*Built with hyperbolic geometry. Secured by mathematics.*


## Publishing (AI-assisted)

Use `docs/PUBLISHING.md` for a safe human+AI release flow, including preflight checks and dry-run packaging.
