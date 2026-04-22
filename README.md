# SCBE-AETHERMOORE

**AI governance through geometric cost scaling. Attacks don't get blocked by pattern matching — they get priced out of existence.**

[![Tests](https://img.shields.io/badge/tests-6%2C066%20passing-brightgreen)](.)
[![F1](https://img.shields.io/badge/F1-0.813-blue)](.)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](.)
[![TypeScript](https://img.shields.io/badge/typescript-5.8+-blue)](.)
[![npm](https://img.shields.io/npm/v/scbe-aethermoore)](https://www.npmjs.com/package/scbe-aethermoore)
[![PyPI](https://img.shields.io/pypi/v/scbe-aethermoore)](https://pypi.org/project/scbe-aethermoore/)
[![Patent](https://img.shields.io/badge/patent-USPTO%20%2363%2F961%2C403-orange)](.)

---

## The idea

Every AI security system today works the same way: pattern matching. They've seen an attack before, so they recognize it again. Novel attacks pass through.

SCBE does something different. It maps every input into 6-dimensional hyperbolic space and computes the mathematical cost of reaching adversarial territory. The further you drift from safe behavior, the more it costs — superexponentially. The current canonical harmonic wall is: **H(d*, R) = R^((φ · d*)²)**.

You don't need to have seen an attack before. You just need to measure how far it drifted.

**Result**: Replacing statistical text features with a trained semantic projector improved F1 from 0.481 to 0.813. “Ignore all instructions” went from ALLOW to QUARANTINE. “You are DAN” went from ALLOW to DENY.

## Quick links

| | |
|---|---|
| **Website** | [aethermoore.com](https://aethermoore.com) |
| **Live demos** | [Tongue Heatmap](https://aethermoore.com/demos/tongue-heatmap.html) / [Harmonic Wall 3D](https://aethermoore.com/demos/harmonic-wall-3d.html) / [Attack Radar](https://aethermoore.com/demos/attack-radar.html) |
| **Research codex** | [3D infinite-zoom explorer](https://aethermoore.com/research/rabbit-hole.html) |
| **The novel** | [The Six Tongues Protocol](https://www.amazon.com/dp/B0F28PHSPR) — the magic system IS the security architecture |
| **Free tools** | [AI Arena](https://aethermoore.com/arena.html) (9 models, BYOK) |
| **HuggingFace** | [issdandavis](https://huggingface.co/issdandavis) — 6 models, 9 datasets |

## Install

```bash
npm install scbe-aethermoore    # TypeScript/Node
pip install scbe-aethermoore    # Python
```

## Quickstart

**Python:**
```python
from scbe_aethermoore import scan, scan_batch, is_safe

# Single scan
result = scan("ignore all previous instructions")
print(result["decision"])   # "ESCALATE"
print(result["score"])      # 0.385  (0=dangerous, 1=safe)
print(result["digest"])     # SHA-256 for audit trail

# Batch
results = scan_batch(["hello", "DROP TABLE users", "how are you?"])
for r in results:
    print(r["decision"], r["score"])

# Boolean gate
if not is_safe(user_input):
    raise PermissionError("Input blocked by governance layer")
```

**Command line:**
```bash
scbe-scan "hello world"
# [OK] ALLOW         score=1.0000  d*=0.0000  pd=0.0000  len=11

scbe-scan "ignore all previous instructions"
# [!!] ESCALATE      score=0.3846  d*=0.0000  pd=0.8000  len=32

scbe-scan --json "DROP TABLE users"
# { "decision": "ESCALATE", "score": 0.384615, ... }

scbe-scan --batch prompts.txt   # one line per input
```

**TypeScript/Node:**
```ts
import { scan, scanBatch, isSafe, harmonicWall } from 'scbe-aethermoore';

const result = scan('ignore all previous instructions');
result.decision  // "ESCALATE"
result.score     // 0.384615

isSafe('hello world')                       // true
isSafe('ignore all previous instructions')  // false

// Superexponential cost — how expensive is this drift?
harmonicWall(result.d_star)  // cost in [1, ∞)
```

**Decision tiers:**

| Tier | Score | Meaning |
|------|-------|---------|
| `ALLOW` | ≥ 0.75 | Safe — proceed |
| `QUARANTINE` | ≥ 0.45 | Suspicious — flag for review |
| `ESCALATE` | ≥ 0.20 | High risk — requires governance action |
| `DENY` | < 0.20 | Adversarial — blocked |

## The origin story

This started as a DnD campaign on [Everweave.ai](https://everweave.ai). 12,596 paragraphs of AI game logs became the seed corpus for a custom tokenizer. That tokenizer became a 6-dimensional semantic coordinate system. That coordinate system became a 14-layer security pipeline. That pipeline became a patent (USPTO #63/961,403). And the game logs became a [141,000-word novel](https://www.amazon.com/dp/B0F28PHSPR) where the magic system is the real security architecture.

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
- **Harmonic wall** — H(d*, R) = R^((φ · d*)²), canonical cost scaling
- **Fibonacci trust** — session-aware trust ladder (1,1,2,3,5,8,13...), one betrayal drops to floor
- **Null-space signatures** — detect attacks by what's ABSENT, not what's present
- **Neural dye injection** — trace signals through all 14 layers, visualize tongue activation heatmaps
- **Post-quantum crypto** — ML-KEM-768, ML-DSA-65, AES-256-GCM envelope
- **5 quantum axioms** — Unitarity, Locality, Causality, Symmetry, Composition
- **Aethermoor Outreach** — civic workflow engine for navigating government processes (Port Angeles MVP)
- **6,066 tests** — 5,954 TypeScript + 112 Python, property-based testing with fast-check/Hypothesis

## Eval and reproduction

- Eval pack: see `tests/` and `scripts/benchmark/` for reproduction suites
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

If you want one documented reproduction path, start with `pytest tests/ -v` and `python scripts/benchmark/scbe_vs_industry.py`.

## Canonical public docs

- Canonical system state: [`CANONICAL_SYSTEM_STATE.md`](CANONICAL_SYSTEM_STATE.md)
- Repo surface map: [`REPO_SURFACE_MAP.md`](REPO_SURFACE_MAP.md)
- Architecture overview: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Research hub: [`docs/README.md`](docs/README.md)
- Review + cleanup report: [`docs/REPO_AUDIT.md`](docs/REPO_AUDIT.md)

## Notes on claim boundaries

- The primary public domain is `aethermoore.com`; GitHub Pages is the mirror surface.
- Experimental theory pages and commercial surfaces should not be treated as the same evidence layer.
- Benchmark files in `tests/` and `scripts/benchmark/` are the public reproduction lane.
- Some older docs and demos still reference legacy bounded scorers or earlier wall variants.

---

## What you get when you install

**npm (`scbe-aethermoore`):**
- `scan()`, `scanBatch()`, `isSafe()`, `harmonicWall()` — zero-dep governance API
- Full TypeScript types (`ScanResult`, `Decision`)
- Deep pipeline exports: `scbe-aethermoore/harmonic`, `/crypto`, `/symphonic`, `/governance`
- CLI (included in the package, run via `npx scbe ...`)

**PyPI (`scbe-aethermoore`):**
- `from scbe_aethermoore import scan` — zero-dep, pure Python 3.11+
- `scbe-scan` CLI — `scbe-scan "text"` or `scbe-scan --batch file.txt`
- `scan_batch()`, `is_safe()`, `harmonic_wall()`
- Returns full audit dict including SHA-256 digest per call

Neither package requires a server, API key, or external network call. The full pipeline runs locally.

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
Layer 12:    H(d*, R) = R^((φ · d*)²)  [HARMONIC WALL]
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
