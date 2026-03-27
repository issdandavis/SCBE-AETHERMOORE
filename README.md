# SCBE-AETHERMOORE

## Runtime governance for AI agents

**SCBE-AETHERMOORE is a runtime governance layer for AI agents that detects and blocks unsafe behavior using semantic-channel analysis, session memory, and geometry-based containment.**

[![Tests](https://img.shields.io/badge/tests-950%20passing-brightgreen)](.)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](.)
[![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue)](.)
[![npm](https://img.shields.io/npm/v/scbe-aethermoore)](https://www.npmjs.com/package/scbe-aethermoore)
[![PyPI](https://img.shields.io/pypi/v/scbe-aethermoore)](https://pypi.org/project/scbe-aethermoore/)

---

## Start here

- Primary site: `https://aethermoorgames.com`
- GitHub Pages mirror: `https://issdandavis.github.io/SCBE-AETHERMOORE/`
- Public red-team surface: `https://aethermoorgames.com/redteam.html`
- Research hub: [`docs/research/index.html`](docs/research/index.html)

SCBE is not another model wrapper. It is a governed execution layer that sits between agent intent and environment access.

## What is implemented

- A 14-layer governance pipeline for evaluating agent actions
- A 6-channel semantic coordinate system for policy, security, structure, and execution signals
- Session-aware escalation and fail-closed governance decisions
- Hydra and HydraArmor integration surfaces for multi-agent and extension-driven use
- A public adversarial benchmark lane with local reproduction paths

## Hero mechanism: null-space signatures

The most distinctive detection mechanism in the current public stack is **null-space signatures**.

Instead of only classifying what is present in a prompt, SCBE measures which semantic channels are abnormally absent. Benign prompts usually activate several channels in a balanced pattern. Adversarial prompts often suppress one or more critical channels, leaving a stable “hole” in the 6D activation vector. That absence pattern becomes the signal.

- Explainer + visualizer: [`docs/research/null-space-signatures.html`](docs/research/null-space-signatures.html)
- Local benchmark lane: [`tests/adversarial/test_adversarial_benchmark.py`](tests/adversarial/test_adversarial_benchmark.py)

## Current public benchmark snapshot

Current public benchmark framing is:

| System | Attacks blocked | Clean false positives |
|---|---:|---:|
| **SCBE-AETHERMOORE** | **91 / 91** | **0 / 15** |
| ProtectAI DeBERTa v2 | 62 / 91 | not published here |
| Keyword filter baseline | 27 / 91 | high |

Use the eval pack below for reproduction context and claim boundaries instead of treating the headline alone as proof:

- Eval pack: [`docs/eval/README.md`](docs/eval/README.md)
- Verification note: [`docs/research/BENCHMARK_VERIFICATION_2026-03-23.md`](docs/research/BENCHMARK_VERIFICATION_2026-03-23.md)
- Industry comparison runner: `python scripts/benchmark/scbe_vs_industry.py`

## Install and first evaluation

Package distribution:

```bash
npm install scbe-aethermoore
pip install scbe-aethermoore
```

Local repo evaluation:

```bash
git clone https://github.com/issdandavis/SCBE-AETHERMOORE.git
cd SCBE-AETHERMOORE
pytest tests/adversarial/test_adversarial_benchmark.py -v
python scripts/benchmark/scbe_vs_industry.py
```

If you want one documented reproduction path, start with [`docs/eval/README.md`](docs/eval/README.md).

## Canonical public docs

- Architecture overview: [`docs/research/architecture-overview.html`](docs/research/architecture-overview.html)
- Eval pack: [`docs/eval/README.md`](docs/eval/README.md)
- Research hub: [`docs/research/index.html`](docs/research/index.html)
- System blueprint v2: [`docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md`](docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md)
- Review + cleanup report: [`docs/reports/SYSTEM_SURFACE_REVIEW_2026-03-26.md`](docs/reports/SYSTEM_SURFACE_REVIEW_2026-03-26.md)

## Notes on claim boundaries

- The primary public domain is `aethermoorgames.com`; GitHub Pages is the mirror surface.
- Experimental theory pages and commercial surfaces should not be treated as the same evidence layer.
- Benchmark files in `tests/`, `scripts/benchmark/`, and `docs/eval/` are the public reproduction lane.

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
curl $SCBE_BASE_URL/v1/demo/rogue-detection
```
Watch 6 legitimate agents detect and quarantine a phase-null intruder using only math.

### 2. Swarm Coordination
```bash
curl $SCBE_BASE_URL/v1/demo/swarm-coordination?agents=20
```
See 20 agents self-organize without any central coordinator.

### 3. Pipeline Visualization
```bash
curl "$SCBE_BASE_URL/v1/demo/pipeline-layers?trust=0.8&sensitivity=0.7"
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
curl -X POST $SCBE_BASE_URL/v1/authorize \
  -H "SCBE_API_KEY: your-key" \
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

### Export Signed Audit Bundle
```bash
curl -G $SCBE_BASE_URL/audit/export \
  -H "SCBE_API_KEY: your-key" \
  --data-urlencode "from=2026-01-01T00:00:00Z" \
  --data-urlencode "to=2026-01-31T23:59:59Z"
```

Returns a signed bundle (`bundle`) plus detached hash manifest (`manifest`) that auditors can verify offline. See `docs/audit-export-offline-verification.md` for verification steps.

### Run Fleet Scenario
```bash
curl -X POST $SCBE_BASE_URL/v1/fleet/run-scenario \
  -H "SCBE_API_KEY: your-key" \
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

### Commercial & Pilot
- **Commercial terms overview**: `COMMERCIAL.md`
- **Customer agreement template**: `CUSTOMER_LICENSE_AGREEMENT.md`
- **2-week pilot outbound one-pager**: `docs/monetization/OUTBOUND_ONE_PAGER_2026-03-09.md`

### Social & Updates
- **X/Twitter**: [@davisissac](https://x.com/davisissac)
- **Substack**: [Issac "Izreal" Davis](https://substack.com/profile/153446638-issac-izreal-davis)

---

## Support This Project

SCBE-AETHERMOORE is built by a solo developer. If it helps your team manage AI agents safely, consider supporting continued development:

| | Link |
|---|---|
| **GitHub Sponsors** | [github.com/sponsors/issdandavis](https://github.com/sponsors/issdandavis) |
| **Ko-fi** | [ko-fi.com/izdandavis](https://ko-fi.com/izdandavis) |
| **SaaS API** | Usage-based governance API — [contact for access](mailto:issdandavis@gmail.com?subject=SCBE%20API%20Access) |
| **Book** | [*The Six Tongues Protocol*](https://www.amazon.com/dp/B0GSSFQD9G) on Kindle |

---

## Contact

**Issac Daniel Davis**
Email: issdandavis@gmail.com
GitHub: [@issdandavis](https://github.com/issdandavis)

---

## License

Open-source core is available under the MIT License (`LICENSE`).

Commercial terms apply to designated proprietary components and enterprise delivery packages. See:
- `COMMERCIAL.md`
- `CUSTOMER_LICENSE_AGREEMENT.md`

For enterprise licensing/support inquiries: `issdandavis@gmail.com`.

---

*Built with hyperbolic geometry. Secured by mathematics.*


## Publishing (AI-assisted)

Use `docs/PUBLISHING.md` for a safe human+AI release flow, including preflight checks and dry-run packaging.
