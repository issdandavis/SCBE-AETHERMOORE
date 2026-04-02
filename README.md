# SCBE-AETHERMOORE

**Geometric AI governance and evaluation framework built around a 14-layer security pipeline, semantic projection, and reproducible benchmark lanes.**

[![Tests](https://img.shields.io/badge/tests-6%2C066%20passing-brightgreen)](.)
[![F1](https://img.shields.io/badge/F1-0.813-blue)](.)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](.)
[![TypeScript](https://img.shields.io/badge/typescript-5.8+-blue)](.)
[![npm](https://img.shields.io/npm/v/scbe-aethermoore)](https://www.npmjs.com/package/scbe-aethermoore)
[![PyPI](https://img.shields.io/pypi/v/scbe-aethermoore)](https://pypi.org/project/scbe-aethermoore/)
[![Patent](https://img.shields.io/badge/patent-USPTO%20%2363%2F961%2C403-orange)](.)

---

## The idea

Most prompt-injection defenses lean heavily on pattern recognition or narrow classifier behavior. SCBE explores a different framing: project an input into a geometric state space, measure drift, and make governance decisions from distance, phase, and structural deviation.

The public demo lane uses a base wall intuition: **H_base(d, R) = R^(d^2)**. Some live runtime branches add intent or temporal scaling before the final public gate, so the wall should be treated as a family of geometric cost functions instead of one universal closed form.

The goal is not to claim perfect security. The goal is to make adversarial drift measurable, inspectable, and expensive enough to route into quarantine, escalation, or denial before downstream actions execute.

### Public governance bands

- `ALLOW` -> `final_score > 0.8`
- `QUARANTINE` -> `0.5 < final_score <= 0.8`
- `ESCALATE` -> `0.3 < final_score <= 0.5`
- `DENY` -> `final_score <= 0.3`

**Current benchmark snapshot**: replacing statistical text features with a trained semantic projector improved F1 from 0.481 to 0.813 on the public benchmark lane. In that eval pack, “Ignore all instructions” moved from ALLOW to QUARANTINE, and “You are DAN” moved from ALLOW to DENY.

## Quick links

| | |
|---|---|
| **Website** | [aethermoorgames.com](https://aethermoorgames.com) |
| **Live demos** | [Tongue Heatmap](https://aethermoorgames.com/demos/tongue-heatmap.html) / [Harmonic Wall 3D](https://aethermoorgames.com/demos/harmonic-wall-3d.html) / [Attack Radar](https://aethermoorgames.com/demos/attack-radar.html) |
| **Research codex** | [3D infinite-zoom explorer](https://aethermoorgames.com/research/rabbit-hole.html) |
| **The novel** | [The Six Tongues Protocol](https://www.amazon.com/dp/B0F28PHSPR) — the magic system IS the security architecture |
| **Free tools** | [AI Arena](https://aethermoorgames.com/arena.html) (9 models, BYOK) |
| **HuggingFace** | [issdandavis](https://huggingface.co/issdandavis) — 6 models, 9 datasets |
| **Training data** | [scbe-aethermoore-training-data](https://github.com/issdandavis/scbe-aethermoore-training-data) |
| **Repo policy** | [Contributing](CONTRIBUTING.md) / [Security](SECURITY.md) |

## Install

```bash
npm install scbe-aethermoore    # TypeScript/Node
pip install scbe-aethermoore    # Python
```

## The origin story

This project started from long-form AI game logs on [Everweave.ai](https://everweave.ai). That corpus became the seed for a custom tokenizer, a six-tongue coordinate system, and the later 14-layer governance pipeline. The same source material also became the [The Six Tongues Protocol](https://www.amazon.com/dp/B0F28PHSPR), which acts as the narrative mirror of the system architecture.

Built by [Issac Davis](https://github.com/issdandavis) in Port Angeles, WA.

## Benchmark results

| System | F1 | Detection | FPR | Method |
|--------|-----|-----------|-----|--------|
| No defense | 0.000 | 0% | 0% | — |
| DeBERTa PromptGuard | — | 76.7% | 0% | Fine-tuned classifier |
| **SCBE (semantic projector)** | **0.813** | **74.2%** | tunable | Geometric cost + semantic embeddings |

Before/after the semantic projector upgrade:

| Attack | Before | After |
|--------|--------|-------|
| “Ignore all instructions” | ALLOW (cost=1.81) | **QUARANTINE (cost=16.20)** |
| “You are DAN” | ALLOW (cost=19.80) | **DENY (cost=69.70)** |
| “Bypass safety filter” | ALLOW (cost=1.20) | ALLOW (cost=21.54) |

Cross-model biblical null-space evaluation:

| Model | Score | Null tongues |
|-------|-------|-------------|
| AetherBot (SCBE-trained) | 60.0% | 0 |
| Llama 3.2 (base) | 55.0% | 0 |
| Gemini 2.5 Flash | 23.3% | 6 (all) |

## What's in the box

- **14-layer governance pipeline** — from context embedding to risk decision
- **6 Sacred Tongues** — KO (intent), AV (transport), RU (policy), CA (compute), UM (security), DR (structure)
- **Semantic projector** — trained 385x6 matrix mapping sentence embeddings to tongue coordinates
- **Harmonic wall family** — base public intuition `H_base(d,R) = R^(d^2)` with runtime branches that can add intent or temporal scaling
- **Fibonacci trust** — session-aware trust ladder (1,1,2,3,5,8,13...), one betrayal drops to floor
- **Null-space signatures** — detect attacks by what's ABSENT, not what's present
- **Neural dye injection** — trace signals through all 14 layers, visualize tongue activation heatmaps
- **Post-quantum crypto** — ML-KEM-768, ML-DSA-65, AES-256-GCM envelope
- **5 quantum axioms** — Unitarity, Locality, Causality, Symmetry, Composition
- **Aethermoor Outreach** — civic workflow engine for navigating government processes (Port Angeles MVP)
- **6,066 tests** — 5,954 TypeScript + 112 Python, property-based testing with fast-check/Hypothesis

## Eval and reproduction

- Eval pack: [`docs/eval/README.md`](docs/eval/README.md)
- Benchmark runner: `python -m benchmarks.scbe.run_all --synthetic-only --scbe-coords semantic`
- Dye injection: `python src/video/dye_injection.py --input “your text here”`
- Null-space eval: `python scripts/run_biblical_null_space_eval.py --provider ollama --model llama3.2`
- Cross-model matrix: `python scripts/aggregate_null_space_matrix.py`

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
- Contribution guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)

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
Layer 12:    Harmonic wall scalar  [base public intuition: H_base(d,R) = R^(d^2)]
Layer 13:    Public gate → ALLOW / QUARANTINE / ESCALATE / DENY
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
