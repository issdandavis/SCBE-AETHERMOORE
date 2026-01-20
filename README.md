# SCBE-AETHERMOORE v4.0

> **Spectral Context-Bound Encryption + Hyperbolic Governance for AI-to-AI Communication**

[![Patent Pending](https://img.shields.io/badge/Patent-USPTO%20%2363%2F961%2C403-blue)](https://github.com/ISDanDavis2/scbe-aethermoore)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://www.python.org/)

**Status (Jan 2026):** Pilot-ready prototype with functional core. Not yet compliance-certified for regulated enterprise.

---

## What This Is

SCBE-AETHERMOORE is a framework for **agent-to-agent governance and communication** where:

- Agents exchange messages in a **sealed envelope** (cryptographic binding)
- The receiver runs a **deterministic governance gate** before acting
- "Context drift" and abnormal behavior are scored using **geometry + coherence metrics**
- Outputs are **fail-closed** with **low-leak error behavior** (no helpful oracle)

Think of it as:
> **"Crypto for the message + math-based rules for whether the agent is allowed to act on it."**

---

## What It's For

Designed for situations like:

- AI "workers" collaborating (tools, planners, schedulers, multi-agent systems)
- Preventing **replay**, **tampering**, **downgrade**, and **unauthorized actions**
- Forcing agent actions through **ALLOW / QUARANTINE / DENY** decisions
- Maintaining an **audit trail** across all decisions

---

## Core Idea (Plain English)

1. Turn "what's happening" (context, intent, telemetry) into a vector
2. Embed that vector into a **Poincaré ball** (hyperbolic trust space)
3. Measure **distance to a trusted realm** and apply a risk amplifier
4. Combine with coherence checks (spectral / phase stability)
5. Output a governance decision

This produces a score that's:
- **Auditable** — you can show the math
- **Stable** — small changes don't cause chaotic decisions
- **Integratable** — wraps around existing systems

---

## Architecture

```
[Agent Message + Context] → [Envelope (crypto)] → [SCBE Gate] → Decision
                                                            → [Audit chain]
```

### 14-Layer Reference Model

| Layer | Name | Function |
|-------|------|----------|
| 1 | Complex State | Context → complex vector (amplitude + phase) |
| 2 | Realification | ℂᴰ → ℝ²ᴰ embedding |
| 3 | Weighted Transform | SPD metric weighting |
| 4 | Poincaré Embedding | Map to hyperbolic ball (‖u‖ < 1) |
| 5 | Hyperbolic Distance | d_ℍ(u,v) via arcosh formula |
| 6 | Breathing Transform | Temporal modulation (diffeomorphism) |
| 7 | Phase Transform | Möbius isometry (gyrovector addition) |
| 8 | Realm Distance | Min distance to trusted zone centers |
| 9 | Spectral Coherence | FFT-based pattern stability |
| 10 | Spin Coherence | Phase alignment measure |
| 11 | Triadic Temporal | Multi-timescale distance aggregation |
| 12 | Harmonic Scaling | Risk amplifier: H(d,R) = φᵈ / (1 + e⁻ᴿ) |
| 13 | Risk Decision | ALLOW / QUARANTINE / DENY |
| 14 | Audio Axis | Hilbert transform telemetry |

> **Note:** Context vectors are configurable dimension (typically 6D or 12D depending on integration).

---

## What Is Implemented Today

### ✅ Implemented (Pilot-Ready)

- **Hyperbolic embedding + distance metric** (Poincaré ball)
- **Möbius transformations** (true isometries via gyrovector operations)
- **Risk amplification** (harmonic scaling)
- **Three-way governance decision**: `ALLOW / QUARANTINE / DENY`
- **Demo**: Memory shard sealed retrieval controlled by governance
- **12,000+ lines of tests** (TypeScript + Python)
- **Dashboard**: Real-time monitoring UI
- **API endpoints**: 6 REST endpoints for integration
- **Fleet orchestration**: Redis/BullMQ-based agent coordination

### ⚠️ Optional / Environment-Dependent

- **PQC integration** (ML-KEM-768, ML-DSA-65) — requires liboqs bindings
- **Sacred Tongue tokenizer** — full 6×256 vocabulary implemented
- **Enterprise compliance** (SOC2/FIPS/ISO) — requires external certification

---

## Quick Start

### Python Demo
```bash
pip install numpy scipy argon2-cffi pycryptodome
python demo_memory_shard.py
```

### TypeScript
```bash
npm install
npm test
```

### Run Proof Pack
```bash
./scripts/make_proof_pack.sh
```

This generates evidence at `docs/evidence/<timestamp>/` containing:
- `system_info.txt` — environment details
- `npm_test_output.txt` — test results
- `pytest_output.txt` — Python test results
- `demo_memory_shard_output.txt` — end-to-end demo
- `pip_freeze.txt`, `npm_deps.txt` — dependency snapshots

---

## Security Model

- **Confidentiality/integrity/authenticity** reduce to standard cryptography (AEAD, HKDF, signatures; PQC when enabled)
- **Hyperbolic governance + coherence scoring** are best described as:
  - Authorization policy + anomaly detection, **not** "new cryptography"
- **Fail-closed with low-leak error behavior:** Unauthorized requests return uniform errors, do not expose internal state, and avoid acting as an oracle

---

## Key Differentiator

| Traditional Security | SCBE-AETHERMOORE |
|---------------------|------------------|
| "Do you have the key?" | "Are you the right entity, in the right context?" |
| Possession-based | Context-based |
| Binary (yes/no) | Three-way (allow/quarantine/deny) |
| Opaque ML models | Deterministic, auditable math |

---

## Project Structure

```
scbe-aethermoore-demo/
├── src/
│   ├── crypto/          # Cryptographic primitives + PQC
│   ├── harmonic/        # Hyperbolic geometry + scaling
│   ├── fleet/           # Redis/BullMQ orchestration
│   ├── api/             # REST API endpoints
│   └── scbe_14layer_reference.py  # Reference implementation
├── dashboard/           # Monitoring UI
├── tests/               # 12,000+ lines of tests
├── docs/                # Documentation + evidence
└── scripts/             # Build + proof pack generation
```

---

## Roadmap

| Track | Status | Description |
|-------|--------|-------------|
| **Pilot** | ✅ Now | Demos + integration adapters + runbooks |
| **Security** | 🔄 In Progress | Independent audit + threat model + adversarial harness |
| **Enterprise** | ⏳ Planned | SOC 2 Type II + pentest + operational readiness |

---

## Comparison: Darktrace vs SCBE-AETHERMOORE

| Dimension | Darktrace | SCBE-AETHERMOORE |
|-----------|-----------|------------------|
| **Maturity** | 10+ yrs, thousands of deployments | Pilot-ready prototype |
| **Mechanism** | ML + behavioral baselining | Deterministic scoring + thresholds |
| **Explainability** | Good (factors, summaries) | Excellent (explicit score components) |
| **AI/Agent Focus** | Generalized endpoint security | Purpose-built for agent-to-agent |
| **Prevention** | Mostly detection + response | Action gating (deny/quarantine) |
| **False Positives** | Tuned over time | Deterministic thresholds, tuneable |
| **PQC** | Varies by deployment | Optional, environment-dependent |

**Positioning:**
- **Darktrace:** Detect weird behavior in networks
- **SCBE-AETHERMOORE:** Govern what AI agents are allowed to do to each other

---

## Patent Notice

> **US Provisional Application #63/961,403** (filed Jan 15, 2026)
> This repository is licensed under Apache 2.0.

---

## Contact

- **Author:** Issac Daniel Davis
- **GitHub:** [@ISDanDavis2](https://github.com/ISDanDavis2)
- **Email:** issdandavis@gmail.com

---

## Documentation

| Document | Description |
|----------|-------------|
| `QUICKSTART.md` | Get running in 5 minutes |
| `FULL_SYSTEM_ENABLEMENT.md` | Complete technical specification (~20K words) |
| `SYSTEM_INTEGRATION.md` | Component integration guide |
| `docs/ENTERPRISE_TESTING_GUIDE.md` | 41 correctness properties |
| `docs/AUDIT_RESPONSE_ACTION_PLAN.md` | Patent + security fixes |
| `PATENT_STRATEGY_ACTION_ITEMS.md` | Critical improvements |

---

*Built for the age of autonomous agents.*
