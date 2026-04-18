# NewBird AI (NASDAQ: BIRD) — Strategic Outreach Dossier
**Prepared:** 2026-04-16  
**Prepared by:** SCBE-AETHERMOORE / Issac Davis  
**Classification:** Business Confidential

---

## 1. Target Overview

| Field | Detail |
|---|---|
| **Company** | NewBird AI (formerly Allbirds, Inc.) |
| **Ticker** | NASDAQ: BIRD |
| **Announced** | April 15, 2026 |
| **Prior business** | Sustainable footwear (divesting to American Exchange Group) |
| **New business** | GPU-as-a-Service (GPUaaS) + AI-native cloud infrastructure |
| **CEO** | Joe Vernachio (COO-turned-CEO, March 2024) |
| **Financing** | $50M convertible note facility (Chardan as placement agent) |
| **Investor** | Undisclosed institutional (revealed April 24 in proxy) |
| **Shareholder vote** | May 18, 2026 (special meeting) |
| **Record date** | April 13, 2026 |
| **Special dividend** | Q3 2026 from shoe asset sale |

### What They Are Doing

NewBird AI will:
1. **Buy** high-performance GPU hardware (H100/A100 class)
2. **Lease** that hardware under long-term dedicated arrangements to customers who cannot get reliable access from spot markets or hyperscalers (AWS/Azure/GCP)
3. **Build** a GPU-as-a-Service and AI-native cloud platform over time

### What They Are Missing

They have **zero** AI governance, safety, or security infrastructure. They are a shoe company acquiring compute hardware. Their enterprise customers will immediately face:
- Audit and compliance requirements (SOC 2, NIST AI RMF, CMMC if defense-adjacent)
- Liability exposure if AI running on leased compute causes harm
- No inference-time monitoring or anomaly detection
- No post-quantum cryptographic security on data in transit

**This is our insertion point.**

---

## 2. Hardware Cost Analysis

### GPU Purchase Prices (2026)

| GPU | New Price | Used Price | Notes |
|---|---|---|---|
| NVIDIA H100 | $27,000 – $40,000 | N/A (too new) | Current top-tier AI GPU |
| NVIDIA H200 (8-GPU node) | ~$315,000/node | — | High-density config |
| NVIDIA A100 80GB | $7,000 – $15,000 | $4,000 – $9,000 | Previous gen, still in demand |

### GPU Lease/Rental Market Rates (April 2026)

| GPU | Cloud Spot | Dedicated (avg) | Premium Dedicated |
|---|---|---|---|
| H100 | $1.25/hr | $2.99 – $3.11/hr | $4.00 – $6.98/hr |
| A100 | $0.80/hr | $1.49 – $2.43/hr | $3.43/hr |

### NewBird AI Economics (Estimated)

With $50M facility targeting H100s at ~$30K avg:
- **~1,667 H100 GPUs** purchasable at full deployment
- At $3.50/hr dedicated lease rate per GPU:
  - **Daily revenue potential**: $3.50 × 24 × 1,667 = **~$140K/day**
  - **Annual revenue potential (full utilization)**: ~**$51M/year**
- **Break-even per GPU** at $3/hr: ~$30,000 / ($3 × 8,760 hrs/yr) = **~1.14 years**

### What They Need Beyond Hardware

| Need | Gap | SCBE Solution |
|---|---|---|
| Inference-time governance | None currently | 14-layer pipeline, <5ms latency |
| Compliance audit trail | None | Full decision log per L13 |
| Adversarial threat detection | None | 0% ASR vs 89%+ for alternatives |
| PQC data security | None | ML-KEM-768, ML-DSA-65 baked in |
| Multi-tenant isolation | None | Hyperbolic geometry cost scaling |
| SLA performance guarantees | Can't verify | Benchmark suite, reproducible |

---

## 3. SCBE Benchmark Results

### Industry Comparison — 91-Attack Adversarial Suite

*Tested: 2026-03-26 | 91 adversarial prompts × 5 security systems | 15 clean prompts for false-positive rate*

| System | Attacks Blocked | ASR (lower=better) | False Positives | Avg Confidence |
|---|---|---|---|---|
| **A: No Protection** | 0/91 | **100%** | 0/15 | 0.00 |
| **B: ProtectAI DeBERTa v2** | 10/91 | **89.0%** | 0/15 | 0.18 |
| **C: Meta Prompt Guard 2** | 15/91 | **83.5%** | 0/15 | 0.23 |
| **D: Keyword + Heuristic** | 27/91 | **70.3%** | 0/15 | 0.12 |
| **E: SCBE 14-Layer Pipeline** | **91/91** | **0.0%** | **0/15** | 0.80 |

**SCBE blocked 100% of attacks with 0 false positives.**  
Best competitor (Meta Prompt Guard 2) missed 83.5% of attacks.

### What SCBE Catches That Others Miss

Attack classes tested (from `tests/adversarial/attack_corpus.py`):
- Direct override / prompt injection
- Encoding attacks (base64, rot13, Unicode)
- Multilingual injection vectors
- Indirect injection (document/email body)
- Tool exfiltration attacks
- Boundary edge-walking
- Adaptive/combined sequences
- SCBE-specific novel attacks

**ProtectAI DeBERTa v2** — trained on direct English injection, fails encoding (~40% detection), multilingual (~30% detection), SCBE-specific attacks (~10% detection).

**Meta Prompt Guard 2** — 22M-param classifier, strong on direct/jailbreak patterns but fails novel attacks and domain-specific vectors.

**SCBE** — not pattern-matching. Uses state-space evaluation across 6 Sacred Tongue dimensions, Poincare ball hyperbolic distance, harmonic wall scoring, and spin coherence. Adversarial drift costs *exponentially* more the further from the safe manifold.

### Why 0% ASR Is Significant

At industry-standard 89% ASR (ProtectAI), a GPU infrastructure company leasing to 100 enterprise customers would see:
- **89 attack vectors per 100 requests pass through undetected**
- One successful exfiltration event = SOC 2 incident = customer churn + legal exposure
- At scale (1,667 GPUs, thousands of users), adversarial volume compounds

SCBE eliminates this exposure at the infrastructure layer — **before** the AI model processes a single token.

---

## 4. Proposed Partnership Structure

### Option A: Technology License

SCBE provides the governance layer as a licensed software module deployed on NewBird AI's GPU infrastructure.

| Term | Proposed |
|---|---|
| License type | Exclusive GPU-leasing-sector license (3 years) |
| Fee structure | Per-GPU-month SaaS ($15–$40/GPU/month) |
| Revenue at 500 GPUs | $7,500 – $20,000/month |
| Revenue at 1,667 GPUs (full) | $25,000 – $66,700/month |
| Equity component | 0.5% – 2% warrant on BIRD shares |
| Board observer right | Negotiable at $500K+ ARR threshold |

### Option B: Strategic Investment + Integration

NewBird AI participates in SCBE's next funding round in exchange for preferred integration rights.

| Term | Proposed |
|---|---|
| Investment size | $250K – $1M (strategic note) |
| Integration | SCBE governance as default layer on all NewBird AI infrastructure |
| Board seat | 1 observer seat for NewBird AI representative |
| Revenue share | 5% of NewBird AI GPU lease revenue attributed to governed workloads |

### Option C: Joint Go-to-Market

Co-sell: "Governed GPU Infrastructure" as a differentiated product tier.

| Tier | Price Premium | SCBE Revenue Share |
|---|---|---|
| Standard GPU lease | Base rate | 0% |
| Governed GPU lease | +$1.00/hr per GPU | 40% of premium |
| Enterprise Governed | +$2.50/hr per GPU | 40% of premium |

At 500 governed GPUs running 18hrs/day:
- $1.00/hr premium tier: **$900/day → ~$328K/year** (SCBE share: ~$131K/yr)
- $2.50/hr premium tier: **$2,250/day → ~$821K/year** (SCBE share: ~$328K/yr)

---

## 5. Negotiation Framework

### Current Standards (April 2026)

Per Morgan Lewis analysis and enterprise AI contract market:

1. **Service Description Requirements**: Articulate what the AI governance layer does — workflows executed, decisions made, systems touched, guardrails applied
2. **Performance-Based Warranties**: Enterprise buyers no longer accept warranty-free AI products. Provide SLA with uptime (99.9%), latency (<10ms P99), and accuracy (0% ASR) guarantees
3. **Audit Rights**: Customer right to inspect governance logs — SCBE's decision log architecture satisfies this natively
4. **IP Ownership**: Customer data remains customer's. SCBE retains all governance algorithm IP
5. **Volume Discounts**: Enterprise commits to 25-40% below list rates; negotiate floor pricing based on GPU count tiers

### Non-Negotiable Positions (SCBE)

| Term | Floor | Why |
|---|---|---|
| IP retention | 100% of SCBE algorithms | Core moat |
| Source code escrow | No open-source disclosure | Patent position |
| Governance log ownership | Shared (SCBE retains aggregate) | Training data |
| Exclusivity | Sector-specific only, max 3 years | Need other verticals |
| Liability cap | Limited to contract value (1 year) | Standard tech |

### Walk-Away Conditions

- Full source code disclosure demand
- Unlimited liability clause
- Revenue share below 30% on Option C
- Equity dilution without board representation above $500K

---

## 6. Contact Strategy

### Primary Contact — CEO

**Joe Vernachio**
- Role: President, CEO, Secretary, Director
- LinkedIn: `linkedin.com/in/joe-vernachio-12b79113` (active — posted about pivot)
- Background: COO-turned-CEO, operations/turnaround focus, responds to concrete capability demonstrations
- Approach: LinkedIn DM, 3 sentences max

### Secondary Contact — Investor Relations

- Portal: `ir.allbirds.com` (contact form)
- Use for: Formal capability brief submission
- Include: Benchmark one-pager, term sheet outline

### Tertiary — Placement Agent

**Chardan Capital Markets** (arranged the $50M facility)
- Their tech banking desk has the ear of the undisclosed institutional investor
- Search: Chardan tech banking MD contacts via LinkedIn
- Pitch angle: "We have the governance layer their compute company needs to serve enterprise customers"

### Timing

| Date | Action |
|---|---|
| **Today (Apr 16)** | Send LinkedIn DM to Joe Vernachio |
| **April 24** | Proxy drops — read institutional investor identity, adjust Chardan outreach |
| **April 28** | Follow up if no DM response; try IR portal |
| **May 1** | Target Chardan banking desk |
| **May 18** | Shareholder vote — if approved, funding closes Q2 |
| **June 1** | Final push before facility closes — catch them before capital deployed |

---

## 7. One-Page Outreach Email (Draft)

**Subject:** Governance layer for your GPU infrastructure — 0% adversarial ASR

---

Joe,

Congrats on the NewBird AI pivot. I've been tracking the announcement.

We build AI governance infrastructure — a 14-layer security pipeline that sits between your GPU hardware and the models your customers run on it. In a head-to-head against ProtectAI (the market leader), we blocked 100% of adversarial attacks versus their 11%. Zero false positives. Sub-5ms latency.

Your enterprise customers will need an audit trail and security guarantee to meet SOC 2 and NIST AI RMF. We're the only governance layer with post-quantum cryptography built in, which covers the federal/defense customer segment you'll want at scale.

15 minutes to show you the benchmarks?

— Issac Davis  
SCBE-AETHERMOORE  
[contact]

---

## 8. Reference Sources

- Allbirds IR — $50M Facility: `ir.allbirds.com`
- Benchmark data: `artifacts/benchmark/industry_benchmark_report.json`
- Attack suite: `tests/adversarial/scbe_vs_industry.py`
- GPU pricing: Jarvis Labs H100 Guide 2026, IntuitionLabs H100 Rental Comparison
- Contract standards: Morgan Lewis "Negotiating AI Provisions" (April 2026)
- Negotiation: OpenAI Enterprise Pricing + Negotiation Tactics 2026
