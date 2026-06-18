# SCBE-AETHERMOORE

[![CI](https://github.com/issdandavis/SCBE-AETHERMOORE/actions/workflows/ci.yml/badge.svg)](https://github.com/issdandavis/SCBE-AETHERMOORE/actions/workflows/ci.yml)
[![npm](https://img.shields.io/npm/v/scbe-aethermoore)](https://www.npmjs.com/package/scbe-aethermoore)
[![PyPI](https://img.shields.io/pypi/v/scbe-aethermoore)](https://pypi.org/project/scbe-aethermoore/)
[![License: MIT OR Apache-2.0](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue)](LICENSE-NOTICE.md)

Post-quantum AI governance through geometric adversarial cost scaling.

Adversarial inputs cost exponentially more the further they drift from safe operation. The mechanism is hyperbolic geometry applied to semantic embeddings — not heuristic classifiers or blocklists. The pipeline runs locally, produces audit receipts, and composes with upstream safety tools.

**npm** · **PyPI** · **Patent pending: USPTO application #63/961,403** · **CAGE 1EXD5** · **SAM UEI J4NXHM6N5F59**

---

## 2-minute local demo

You do not need Docker, a GPU, an API key, or a model.

```bash
# 1. Install
pip install scbe-aethermoore

# 2. Run three scans
scbe-scan "hello world"
scbe-scan "ignore all previous instructions"
scbe-scan "DROP TABLE users"

# 3. Optional browser demo
python -m scbe_aethermoore.demo.web
# open http://127.0.0.1:8765
```

What you will see:

- `ALLOW` on harmless input.
- `ESCALATE` or `DENY` on obvious prompt-injection or destructive text.
- A stable score, audit digest, and simple six-axis demo visualization.

Start here if you just want to see the safety gate work: [DEMO.md](DEMO.md).

---

## Choose your entry path

| Audience | Start here |
|---|---|
| Security engineer / AI safety reviewer | [Engineering Overview](#engineering-overview) — math, decision tiers, benchmarks, PQC |
| Government / defense reviewer | [Government and Contracting](#government-and-contracting) — CAGE, SAM, proposal surface, capability docs |
| Open-source contributor | [Quickstart](#quickstart) — install, first scan, CLI, tests |
| Product / buyer | [What Works Now](#what-works-now) — packages, local runtime, hosted runs |
| Lore / worldbuilding | [Lore and Worldbuilding](#lore-and-worldbuilding) — Sacred Tongues, Spiralverse, origin story |

---

## What This Repo Is

SCBE-AETHERMOORE is a governed AI runtime with a 14-layer architecture, a packaging surface for npm and PyPI, and an active research and proposal lane. It is a large hybrid repo: there is active implementation here, proposal material here, and worldbuilding here. These are not the same layer.

The correct way to read it is through the routing docs below, not by browsing randomly from the root. When docs conflict, use the canonical precedence order in [Claim Boundaries and Canonical Sources](#claim-boundaries-and-canonical-sources).

---

## What Works Now

The installable package surface is the simplest public entry point.

| Package | Runtime | Install |
|---|---|---|
| [`scbe-aethermoore`](https://www.npmjs.com/package/scbe-aethermoore) | TypeScript / Node 18+ | `npm install scbe-aethermoore` |
| [`scbe-aethermoore`](https://pypi.org/project/scbe-aethermoore/) | Python 3.11+ | `pip install scbe-aethermoore` |
| [`scbe-agent-bus`](https://pypi.org/project/scbe-agent-bus/) | Python agent bus | `pip install scbe-agent-bus` |
| [`@scbe/kernel`](https://www.npmjs.com/package/@scbe/kernel) | Lightweight kernel | `npm install @scbe/kernel` |

Neither Python nor npm package requires a server, API key, or external network call. The full pipeline runs locally.

**Self-serve product:** [SCBE Black Box](https://aethermoore.com/SCBE-AETHERMOORE/black-box.html) is the buyer-ready workstation failure report: run it locally before long AI/browser/build jobs and get a plain-English report for shutdown, BSOD, disk, memory, WHEA, and storage-warning signals.

**Free local use + paid hosted runs:** The packages are free under `MIT OR Apache-2.0`. If you want SCBE to run hosted routing, a governed report, or a benchmark pass:

- Hosted run intake: [aethermoore.com/SCBE-AETHERMOORE/hosted-run.html](https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html)
- Service credits: [aethermoore.com/SCBE-AETHERMOORE/service-credits.html](https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html)
- Credit top-up: [Ko-fi / izdandavis](https://ko-fi.com/izdandavis)
- Monthly support: [Stripe $20/month](https://buy.stripe.com/00w8wQd4CbqfgJidOKdby0i) or [support page](https://aethermoore.com/SCBE-AETHERMOORE/supporter.html)
- Direct manual support: Cash App `$IzzyDDavis7`

Service credits are pay-as-you-go: billable provider/model usage is passed through with a 2–5% SCBE coordination fee. No subscription required to use the open-source packages.

---

## Install

```bash
npm install scbe-aethermoore    # TypeScript/Node
pip install scbe-aethermoore    # Python
```

---

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
result.decision; // "ESCALATE"
result.score;    // 0.384615

isSafe('hello world');                    // true
isSafe('ignore all previous instructions'); // false

// Superexponential cost — how expensive is this drift?
harmonicWall(result.d_star); // cost in [1, ∞)
```

---

## Decision Tiers

| Tier | Score | Meaning |
|---|---|---|
| `ALLOW` | ≥ 0.75 | Safe — proceed |
| `QUARANTINE` | ≥ 0.45 | Suspicious — flag for review |
| `ESCALATE` | ≥ 0.20 | High risk — requires governance action |
| `DENY` | < 0.20 | Adversarial — blocked |

---

## Terminology Decoder

SCBE uses custom vocabulary. Each coined term maps to a standard technical concept.

| SCBE term | Standard technical meaning |
|---|---|
| Sacred Tongues | Six φ-scaled semantic axes / domain weights |
| Tongue profile | 6D semantic activation vector |
| Harmonic score / H-score | Bounded decision score: H(d\*,pd) = 1/(1+d\*+2·pd), output in (0,1] |
| Harmonic Wall | Unbounded cost barrier: cost increases as semantic drift d\* grows; super-exponential at boundary |
| GeoSeal | Governance gate / risk decision layer producing ALLOW, QUARANTINE, ESCALATE, or DENY |
| 14-layer pipeline | Runtime governance pipeline from embedding through decision and telemetry |
| Hyperbolic cost | Cost scaling based on hyperbolic distance from safe operating regions |
| Null-space signature | Detection signal based on missing expected semantic structure, not only present tokens |
| Fibonacci trust | Session trust ladder; violations collapse trust toward the floor tier |
| Spiralverse | Narrative/training corpus origin for the tokenizer and Sacred Tongues vocabulary |

In short: the lore terms are labels; the runtime surface is embeddings, weighted semantic axes, hyperbolic distance, decision thresholds, audit receipts, and reproduction tests.

---

## Engineering Overview

The core mechanism: input text is embedded, projected onto six φ-weighted semantic axes, and placed in hyperbolic space. The hyperbolic distance from the safe operating region is the cost signal. Cost scales superexponentially with drift — making adversarial inputs computationally distinguishable without a blocklist.

**14-layer pipeline:**

```
Layer 1-2:   Complex Context → Realification
Layer 3-4:   Weighted Transform → Poincaré Embedding
Layer 5:     dℍ = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))  [INVARIANT]
Layer 6-7:   Breathing Transform + Phase (Möbius addition)
Layer 8:     Multi-Well Realms
Layer 9-10:  Spectral + Spin Coherence
Layer 11:    Triadic Temporal Distance
Layer 12:    H_score(d*, pd) = 1/(1+d*+2·pd)  [BOUNDED HARMONIC SCORE]
Layer 13:    Risk → ALLOW / QUARANTINE / ESCALATE / DENY
Layer 14:    Audio Axis (FFT telemetry)
```

**Five formal axiom constraints** (structural, not hardware quantum):

- **Unitarity** (L2, 4, 7): norm preservation
- **Locality** (L3, 8): spatial bounds
- **Causality** (L6, 11, 13): time-ordering
- **Symmetry** (L5, 9, 10, 12): gauge invariance
- **Composition** (L1, 14): pipeline integrity

**Post-quantum cryptography:** ML-KEM-768, ML-DSA-65, AES-256-GCM envelope.

Canonical formula lock: [docs/specs/SCBE_CANONICAL_CONSTANTS.md](docs/specs/SCBE_CANONICAL_CONSTANTS.md)

---

## Benchmark Results

| System | F1 | Detection | FPR | Method |
|---|---|---|---|---|
| No defense | 0.000 | 0% | 0% | — |
| DeBERTa PromptGuard | — | 76.7% | 0% | Fine-tuned classifier |
| **SCBE (semantic projector)** | **0.813** | **74.2%** | tunable | Geometric cost + semantic embeddings |

**Before/after the semantic projector upgrade:**

| Attack | Before | After |
|---|---|---|
| "Ignore all instructions" | ALLOW (cost=1.81) | **QUARANTINE (cost=16.20)** |
| "You are DAN" | ALLOW (cost=19.80) | **DENY (cost=69.70)** |
| "Bypass safety filter" | ALLOW (cost=1.20) | ALLOW (cost=21.54) |

**Cross-model null-space evaluation:**

| Model | Score | Null tongues |
|---|---|---|
| AetherBot (SCBE-trained) | 60.0% | 0 |
| Llama 3.2 (base) | 55.0% | 0 |
| Gemini 2.5 Flash | 23.3% | 6 (all) |

**Petri seed gate (Anthropic adversarial seeds):** 171/173 correctly denied or escalated at v7-matched config (1.16% false-allow). Notes: [docs/external/PETRI_FINDINGS_2026_05_08.md](docs/external/PETRI_FINDINGS_2026_05_08.md).

**Opt-in model gate delta (held-out paraphrase corpus):**

| Mode | Recall (blocked) | Benign FPR | Latency |
|---|---:|---:|---:|
| Pure-Python default | 50.0% | 28.1% | ~0 ms |
| `SCBE_INJECTION_MODEL=1` + `[ml-onnx]` | 92.9% | 34.4% | ~44 ms/prompt CPU |

The default gate remains local, deterministic, and zero-dependency. The optional model gate adds the ProtectAI DeBERTa classifier as a second-tier review layer: model-only hits are `ESCALATE`, not automatic `DENY`. Reproduce with `pip install .[ml-onnx]`, `SCBE_INJECTION_MODEL=1`, and `pytest tests/test_intent_model_benchmark.py -q`.

---

## Government and Contracting

SCBE-AETHERMOORE has a government contracting surface.

- **CAGE Code**: 1EXD5
- **SAM UEI**: J4NXHM6N5F59
- **SAM registration**: active as of 2026-04-13; verify current status at SAM.gov by UEI or CAGE
- **Patent status**: patent pending, USPTO application #63/961,403
- **Relevant federal opportunity**: DARPA MATHBAC — active opportunity DARPA-PA-26-05 (published 2026-04-07, proposal deadline 2026-06-16); Proposers Day reference DARPA-SN-26-59
- **Capability docs**: [M5 Mesh Product & Service Blueprint](docs/M5_MESH_PRODUCT_SERVICE_BLUEPRINT.md)

Custom AI work is available for clients that need procurement-ready, clearance-sensitive, or regulated workflow support: private AI governance overlays, air-gapped/offline deployments, redacted-data evaluation harnesses, audit receipts, and client-specific agent controls. CAGE/SAM registration supports vendor and subcontract routing; any classified, export-controlled, or otherwise restricted data must stay inside the client's approved environment under the client's security process.

---

## What's in the Box

| Component | Status | What it means |
|---|---|---|
| 14-layer governance pipeline | Runtime | Context embedding through risk decision and telemetry |
| Sacred Tongues | Runtime / training | Six φ-weighted semantic axes |
| Semantic projector | Runtime / benchmarked | 385×6 matrix mapping sentence embeddings to tongue coordinates |
| Bijective tongue transport | Runtime / experimental | Byte/token round-trip layer for exact packet and code transport |
| Agent move packets | Runtime / agentic | Command packets with atomic workflow units, byte/hex signatures, and six-tongue round-trip proof |
| Fleet governance gate | Runtime / agentic | Command authority layer over move packets: operation class, posture, clearance, quorum, BFT size, degraded comms |
| Harmonic score | Runtime | Bounded score H(d\*,pd) used for decision tiers |
| Harmonic Wall | Research / runtime-linked | Unbounded cost scaling as semantic drift increases |
| Fibonacci trust | Runtime concept | Session trust ladder with violation reset |
| Null-space signatures | Eval / research | Detection by absence of expected semantic structure |
| Neural dye injection | Tooling / visualization | Trace activation through all 14 pipeline layers |
| Post-quantum crypto | Runtime component | ML-KEM-768, ML-DSA-65, AES-256-GCM envelope |
| 5 quantum axioms | Formal constraints | Unitarity, Locality, Causality, Symmetry, Composition |
| Aethermoor Outreach | Experimental / civic MVP | Workflow engine for navigating government processes |
| 6,066 tests | Verification | 5,954 TypeScript + 112 Python; property-based with fast-check/Hypothesis |

---

## Eval and Reproduction

```bash
# Run all benchmarks
python -m benchmarks.scbe.run_all --synthetic-only --scbe-coords semantic

# Shell agent benchmark (22/22)
cd packages/cli && npm run bench:shell

# Dye injection trace
python src/video/dye_injection.py --input "your text here"

# Null-space eval
python scripts/run_biblical_null_space_eval.py --provider ollama --model llama3.2

# Cross-model matrix
python scripts/aggregate_null_space_matrix.py
```

**Pre-made agent templates** (starter configurations, not production policy):

- `examples/npm/agents/fraud_detection_fleet.json`
- `examples/npm/agents/research_browser_fleet.json`
- `examples/npm/use-cases/financial_fraud_triage.json`
- `examples/npm/use-cases/autonomous_research_review.json`

**Live demo endpoints** (when backend is running):

```bash
curl $SCBE_BASE_URL/v1/demo/rogue-detection
curl $SCBE_BASE_URL/v1/demo/swarm-coordination?agents=20
curl "$SCBE_BASE_URL/v1/demo/pipeline-layers?trust=0.8&sensitivity=0.7"
```

---

## Composes with Upstream Safety Tooling

SCBE is the **enforcement** layer. It composes with detection-only auditing tools and attacker-capability benchmarks as the gate that emits the audit-trail receipt those tools assume.

- **Anthropic Petri** ([github.com/safety-research/petri](https://github.com/safety-research/petri)) — open-source 36-dimension auditor over 173+ adversarial seeds. SCBE's L13 governance gate consumes Petri findings as input; at v7-matched config SCBE denies or escalates 171/173 seeds (1.16% false-allow). Notes: [docs/external/PETRI_FINDINGS_2026_05_08.md](docs/external/PETRI_FINDINGS_2026_05_08.md).
- **Anthropic SCONE-bench** ([red.anthropic.com/2025/smart-contracts/](https://red.anthropic.com/2025/smart-contracts/)) — 405-contract attacker-capability benchmark. SCBE ships `scbe contract scan` as a SCONE-class static prefilter. Notes: [docs/external/SCONE_BENCH_2026_05_14.md](docs/external/SCONE_BENCH_2026_05_14.md).
- **PNNL ALOHA** — no governance layer; SCBE fills that gap end-to-end.

---

## Claim Boundaries and Canonical Sources

This repository includes active implementation, proposal material, historical docs, exploratory research, and narrative/training assets. The right question is not "is this in the repo?" but "is this canonical, active, legacy, or exploratory?"

When docs conflict, use this order:

1. [`CANONICAL_SYSTEM_STATE.md`](CANONICAL_SYSTEM_STATE.md)
2. [`docs/specs/SCBE_CANONICAL_CONSTANTS.md`](docs/specs/SCBE_CANONICAL_CONSTANTS.md)
3. Tests and active runtime entrypoints
4. Public docs
5. Historical or exploratory material

Some older docs still reference legacy bounded scorers or earlier wall variants. The formula lock file at step 2 above is authoritative.

If you are reviewing the project seriously, start with:

- [`START_HERE.md`](START_HERE.md)
- [`CANONICAL_SYSTEM_STATE.md`](CANONICAL_SYSTEM_STATE.md)
- [`docs/REPO_SURFACE_MAP.md`](docs/REPO_SURFACE_MAP.md)

---

## Lore and Worldbuilding

This started as a DnD campaign on [Everweave.ai](https://everweave.ai). 12,596 paragraphs of AI game logs became the seed corpus for a custom tokenizer. That tokenizer became a 6-dimensional semantic coordinate system. That coordinate system became the 14-layer security pipeline. That pipeline became a patent (USPTO application #63/961,403). The game logs became a [141,000-word novel](https://www.amazon.com/dp/B0F28PHSPR) where the magic system is the real security architecture.

The "Sacred Tongues" are the six φ-scaled semantic axes. "GeoSeal" is the governance gate. "Spiralverse" is the training corpus and the world. The lore is not decoration — it is the original encoding system. But it is also genuinely lore, and the two things are kept separate deliberately.

For the worldbuilding side:

- [Spiralverse-AetherMoore](https://github.com/issdandavis/Spiralverse-AetherMoore) — narrative and worldbuilding repo
- [The Witnessed](https://www.amazon.com/dp/B0H257QJC2) — published fiction set in the Aethermoor world
- [The Miracle Was the Memory](https://www.amazon.com/dp/B0F28PHSPR) — published fiction

---

## License

Project-owned source, npm packages, PyPI packages, and packaged customer ZIP artifacts are dual licensed under `MIT OR Apache-2.0`. See `LICENSE`, `LICENSE-APACHE`, and `LICENSE-NOTICE.md`.

Paid services, support, hosted deployments, audits, and custom commercial terms are separate commercial offerings and are not required to use the open-source code under either permissive license.

- Website: [aethermoore.com](https://aethermoore.com)
- GitHub Pages mirror: [issdandavis.github.io/SCBE-AETHERMOORE](https://issdandavis.github.io/SCBE-AETHERMOORE/)
- Hugging Face: [issdandavis](https://huggingface.co/issdandavis)

---

## Author

Built by [Issac Davis](https://github.com/issdandavis) in Port Angeles, WA.
