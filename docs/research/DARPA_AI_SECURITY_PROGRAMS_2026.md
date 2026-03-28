# DARPA AI Security Programs Research — March 2026

**Compiled:** 2026-03-27
**Author:** Issac Daniel Davis (issdandavis)
**Purpose:** Map DARPA programs, BAAs, evaluation criteria, and DoD adoption pathways to SCBE-AETHERMOORE capabilities.

---

## Table of Contents

1. [Active DARPA Programs (2024-2026)](#1-active-darpa-programs-2024-2026)
2. [Upcoming BAAs and Proposers Days](#2-upcoming-baas-and-proposers-days)
3. [GARD, TAII/AIQ, and AIE Status](#3-gard-taiiaq-and-aie-status)
4. [DARPA Evaluation Criteria for AI Security](#4-darpa-evaluation-criteria-for-ai-security)
5. [Programs Matching SCBE Core Innovations](#5-programs-matching-scbe-core-innovations)
6. [DoD AI Adoption Pathway for Small/Solo Developers](#6-dod-ai-adoption-pathway)
7. [SCBE Capability-to-Program Mapping Matrix](#7-scbe-capability-to-program-mapping-matrix)

---

## 1. Active DARPA Programs (2024-2026)

### 1.1 SABER — Securing Artificial Intelligence for Battlefield Effective Robustness

| Field | Detail |
|-------|--------|
| **Office** | Information Innovation Office (I2O) |
| **BAA** | HR001125S0009 |
| **Status** | Awards underway (BAE Systems contracted; proposal window closed June 3, 2025) |
| **Duration** | Single-phase, 24-month program |
| **Classification** | Secret collateral |
| **URL** | https://www.darpa.mil/research/programs/saber-securing-artificial-intelligence |

**What SABER does:**
Builds an operational AI red team to assess battlefield AI systems against:
- Data poisoning (manipulating training data to degrade AI performance)
- Adversarial patches (physical modifications that deceive AI models)
- Model stealing (extracting AI capabilities to replicate or manipulate them)
- Electronic warfare attacks

**Structure:** 24-month cycles of AI security operational test and evaluation exercises (SABER-OpX) with four key stages:
1. Baseline gathering
2. Experimentation
3. Evaluation
4. Continuous assessment

**Primary Metric:** Failure rate of autonomy to complete objective — AI red teams use PACE (Physical, Adversarial AI, Cyber, Electronic warfare) techniques/tools to degrade AI-based perception.

**SCBE Alignment:** SCBE's 14-layer pipeline, adversarial attack detection via hyperbolic geometry, and the military-grade evaluation scale (17-point) directly map to SABER's evaluation framework. SCBE could serve as a **defensive layer** that SABER red teams test against, or as an **evaluation metric framework** for SABER-OpX exercises.

---

### 1.2 CLARA — Compositional Learning-And-Reasoning for AI Complex Systems Engineering

| Field | Detail |
|-------|--------|
| **Office** | I2O |
| **Solicitation** | DARPA-PA-25-07-02 |
| **Status** | OPEN — Proposals due April 10, 2026 (abstracts encouraged by March 2, 2026) |
| **Funding** | Up to $2M per award |
| **Award Target** | June 9, 2026 (120 calendar days from posting) |
| **URL** | https://www.darpa.mil/research/programs/clara |

**What CLARA does:**
Creates high-assurance, broadly applicable AI systems-of-systems by integrating:
- **Machine Learning (ML)** — speed and flexibility
- **Automated Reasoning (AR)** — verifiability based on automated logical proofs

**Key Definition:** "Assurance under CLARA means verifiability with strong explainability to humans, based on automated logical proofs and hierarchical, vetted logic building blocks."

**SCBE Alignment:** SCBE's 14-layer pipeline IS a hierarchical composition of ML (tongue encoding, spectral analysis) and formal verification (axiom mesh, governance gate). The 5 quantum axioms (Unitarity, Locality, Causality, Symmetry, Composition) are exactly the kind of "vetted logic building blocks" CLARA seeks. **This is the highest-priority program for SCBE right now — abstracts were due March 2 but full proposals are due April 10, 2026.**

**ACTION ITEM:** Evaluate whether a late abstract or direct proposal submission is viable by April 10, 2026.

---

### 1.3 AIQ — Artificial Intelligence Quantified

| Field | Detail |
|-------|--------|
| **Office** | I2O |
| **Status** | Active (awards made, research ongoing) |
| **URL** | https://www.darpa.mil/research/programs/aiq-artificial-intelligence-quantified |

**What AIQ does:**
Develops mathematical foundations to **guarantee** AI system performance — not just test it with quizzes. Three capability levels:
1. **Specific problems** — can this AI solve X?
2. **Classes of problems** — can this AI solve problems like X?
3. **Natural classes** — can this AI generalize reliably?

**Two Technical Areas:**
- TA1: Rigorous mathematical foundations for AI evaluation
- TA2: Empirical verification and scaling using open-source AI models

**NIST Partnership:** AIQ works closely with NIST and DoD to ensure deployed AI systems have predictable performance.

**SCBE Alignment:** SCBE's continuous cost function H(d,R) = R^(d^2) provides exactly the mathematical formalism AIQ seeks — a quantifiable, guaranteed relationship between agent drift and security cost. The Langues Metric provides multi-dimensional evaluation. SCBE's 17-point military-grade evaluation scale maps to AIQ's structured capability assessment.

---

### 1.4 AI Forward Initiative

| Field | Detail |
|-------|--------|
| **Office** | I2O (umbrella initiative) |
| **Budget** | $310M in FY2025 request |
| **Status** | Active — overarching initiative, not a single solicitation |
| **URL** | https://www.darpa.mil/research/programs/ai-forward |

**What AI Forward does:**
Explores new directions for AI research resulting in **trustworthy systems for national security missions**, with focus on:
- Trustworthiness
- Reliable operation
- Appropriate human interaction
- Ethical national security application

AI Forward is the umbrella under which I2O organizes AI Exploration (AIE) opportunities. AIEs are deliberately fast — DARPA uses streamlined contracting to target start dates within **3 months** of announcement with **30-45 day** response windows.

**SCBE Alignment:** AI Forward's mission statement ("trustworthy AI for national security") is SCBE's entire thesis. The fast-cycle AIE mechanism is ideal for a solo developer with a working prototype.

---

### 1.5 AIxCC — AI Cyber Challenge

| Field | Detail |
|-------|--------|
| **Office** | I2O |
| **Status** | Final competition at DEF CON 2025; transition phase 2025-2026 |
| **Prizes** | $29.5M cumulative, $7M for small businesses |
| **URL** | https://www.darpa.mil/research/programs/ai-cyber |

**What AIxCC does:**
Two-year competition for AI systems that automatically find and fix vulnerabilities in critical code. Top prize: $4M. DARPA is now eyeing transition of AIxCC tech to "widespread use."

**SCBE Alignment:** SCBE's autonomous web agent, semantic antivirus membrane, and continuous monitoring pipeline could participate in future AIxCC-style challenges or support transition activities.

---

### 1.6 CASTLE — Cyber Agents for Security Testing and Learning Environments

| Field | Detail |
|-------|--------|
| **Office** | I2O |
| **Status** | Active |
| **PM** | Tejas Patel |

**What CASTLE does:**
Uses reinforcement learning to create and train cyber agents that counter advanced persistent threats (APTs) in networks — more effective than current manual approaches.

**SCBE Alignment:** SCBE's multi-agent fleet orchestration, shepherd/flock governance, and BFT consensus directly support CASTLE's goals of autonomous cyber defense with governance constraints.

---

### 1.7 Assured Autonomy

| Field | Detail |
|-------|--------|
| **Office** | I2O |
| **Status** | Active (mature program) |
| **URL** | https://www.darpa.mil/research/programs/assured-autonomy |

**What it does:**
Creates technology for **continual assurance** of Learning-Enabled Cyber Physical Systems (LE-CPSs). Assurance is defined as safety and functional correctness provided provisionally at design time, then continuously monitored, updated, and evaluated at operation-time.

**Key Methods:**
- Mathematically verifiable approaches for ML algorithms
- Runtime monitoring for safety envelopes
- Challenge problems in autonomous vehicles (air, land, underwater)

**SCBE Alignment:** SCBE's self-healing orchestrator, flux contraction toward safe origin, and fail-to-noise (Axiom A4) are exactly what Assured Autonomy needs for runtime assurance of autonomous systems.

---

### 1.8 COMPASS — Critical Orientation of Mathematics to Produce Advancements in Science and Security

| Field | Detail |
|-------|--------|
| **Office** | Defense Sciences Office (DSO) |
| **Status** | Solicitation closed May 12, 2025; awards expected in progress |
| **URL** | https://www.darpa.mil/research/programs/compass |

**What COMPASS does:**
Explores how new mathematical frameworks enable paradigm-shifting problem formulations that better characterize:
- Complex systems
- Stochastic processes
- Random geometric structures

**SCBE Alignment:** SCBE's Poincare ball model, hyperbolic distance functions, Langues Metric with phi-weighted dimensions, and 21D canonical state lift ARE novel mathematical frameworks for complex systems. COMPASS is the most theoretically aligned program — though the solicitation window has closed, the research direction validates SCBE's approach.

---

### 1.9 SIEVE — Securing Information for Encrypted Verification and Evaluation

| Field | Detail |
|-------|--------|
| **Office** | I2O |
| **Status** | Active |
| **URL** | https://www.darpa.mil/research/programs/securing-information-for-encrypted-verification-and-evaluation |

**What SIEVE does:**
Substantially decreases the asymptotic complexity of post-quantum zero-knowledge proof techniques, specifically ZK proofs that rely on post-quantum hardness assumptions.

**SCBE Alignment:** SCBE's post-quantum cryptographic envelope (ML-KEM-768, ML-DSA-65, AES-256-GCM) and the Spiral Seal protocol align with SIEVE's post-quantum verification goals. The Sacred Vault v3 (Argon2id + XChaCha20-Poly1305 + 6-tongue cross-threading) adds novel PQC primitives.

---

### 1.10 QBI 2026 — Quantum Benchmarking Initiative

| Field | Detail |
|-------|--------|
| **Office** | Microsystems Technology Office (MTO) |
| **Status** | Active — 11 companies advanced to Stage B |
| **Goal** | Utility-scale fault-tolerant quantum computing by 2033 |
| **URL** | https://www.darpa.mil/work-with-us/opportunities/darpa-pa-26-02 |

**Companies in Stage B:** IBM, IonQ, Quantinuum, and 8 others.

**SCBE Alignment:** SCBE's post-quantum cryptography is designed to resist quantum attacks. As QBI advances toward fault-tolerant quantum computing, SCBE's PQC envelope becomes more relevant, not less.

---

## 2. Upcoming BAAs and Proposers Days

### 2.1 OPEN NOW — High Priority

| Program | Type | Deadline | Funding | Solicitation |
|---------|------|----------|---------|-------------|
| **CLARA** | Full proposals | **April 10, 2026** | Up to $2M/award | DARPA-PA-25-07-02 |
| **I2O Office-Wide BAA** | Abstracts | November 1, 2026 | $500K-$5M/award | HR001126S0001 |
| **I2O Office-Wide BAA** | Full proposals | November 30, 2026 | $500K-$5M/award | HR001126S0001 |

### 2.2 Upcoming Proposers Days

| Event | Date | Location | Focus |
|-------|------|----------|-------|
| **VITAL Proposers Day** | March 31, 2026 | Arlington, VA + webcast | Autonomous lifesaving (medical) |
| **O-Circuit Proposers Day** | TBD 2026 | TBD | TBD |

### 2.3 Recently Closed (Monitor for Future Cycles)

| Program | Closed | BAA | Notes |
|---------|--------|-----|-------|
| SABER | June 3, 2025 | HR001125S0009 | Awards to BAE Systems; 24-month cycles = next cycle ~mid-2027 |
| COMPASS | May 12, 2025 | DARPA-EA-25-02-03 | Mathematical frameworks |
| PICASSO | Jan 16, 2026 | TBD | Proposers Day was Jan 16 |
| CyPhER Forge | Jan 22, 2026 | TBD | Industry Day was Jan 22 |

### 2.4 I2O BAA Thrust Areas (Permanent Open Door)

The FY2026 I2O Office-Wide BAA (HR001126S0001) accepts proposals in four areas:

1. **Transformative AI** — trustworthy, explainable, ethically-aligned systems
2. **Resilient and Secure Software** — software that resists attacks and failures
3. **Offensive and Defensive Cybersecurity** — AI-enabled cyber ops
4. **Information Domain Operations** — cognitive/semantic operations, digital artifact tracking, adversarial influence

**SCBE maps to Thrust Areas 1, 2, and 3.**

---

## 3. GARD, TAII/AIQ, and AIE Status

### 3.1 GARD — Guaranteeing AI Robustness Against Deception

| Field | Detail |
|-------|--------|
| **Status** | **CONCLUDED** — Transitioned to operational DoD components (CDAO) in early 2024 |
| **Duration** | 4 years (~2020-2024) |
| **PM** | Hava Siegelmann |
| **URL** | https://www.darpa.mil/research/programs/guaranteeing-ai-robustness-against-deception |

**What GARD produced:**
1. **Armory** — Virtual evaluation platform for repeatable, scalable adversarial defense testing (open source on GitHub)
2. **Adversarial Robustness Toolbox (ART)** — Tools for defending and evaluating ML models against adversarial threats (widely adopted)
3. **APRICOT Dataset** — Physical adversarial patch attack dataset for object detection systems

**GARD's Metrics:**
- Robustness against broad categories of attacks (not just known attack patterns)
- System-level resilience (not just model-level accuracy)
- Theoretical ML foundations for identifying vulnerabilities

**GARD's Legacy:** While GARD itself is concluded, its tools and metrics are the **baseline** that SABER and future programs build upon. SCBE should benchmark against ART/Armory to establish credibility.

**SCBE Alignment:** SCBE's philosophy ("injection is inevitable, execution is controllable") is the next evolution beyond GARD's detection-focused approach. GARD proved you can detect adversarial attacks; SCBE argues you should constrain their execution cost. Position SCBE as "post-GARD" technology.

---

### 3.2 AIQ (Successor to "Testing AI" Concepts)

There is no program specifically called "TAII" (Testing AI for AI). The closest equivalent is **AIQ (Artificial Intelligence Quantified)** — see Section 1.3 above.

**AIQ Metrics:**
- Mathematical guarantees about AI generalization (not just test-set accuracy)
- Quantified capability assessment across three levels (specific, class, natural class)
- Collaboration with NIST for standardized evaluation frameworks
- Evaluation criteria: scientific/technical merit, DARPA mission relevance, cost realism

---

### 3.3 AIE — AI Exploration

| Field | Detail |
|-------|--------|
| **Status** | Ongoing mechanism under AI Forward umbrella |
| **Program Announcement** | DARPA-PA-25-03 |
| **URL** | SAM.gov: search for DARPA-PA-25-03 |

**How AIE works:**
- Fast-track funding mechanism (start within 3 months of announcement)
- Short response windows (30-45 days from announcement to abstract)
- Broad eligibility: large/small businesses, universities, non-traditional contractors
- Individual opportunities appear in I2O's solicitation feed

**How to track AIE opportunities:**
1. Subscribe to I2O updates at darpa.mil
2. Set SAM.gov watch on DARPA's I2O contracting office
3. Monitor DARPAConnect community
4. Check grantedai.com/blog for compilations

**Recent AIE topics of interest:**
- Interpretable reinforcement learning
- Logical AI
- AI knowledge representation
- ML mapped to physics (ML2P)

---

## 4. DARPA Evaluation Criteria for AI Security

### 4.1 SABER Evaluation Framework (Current Gold Standard)

**Primary Metric:** Autonomy failure rate under adversarial conditions

**PACE Attack Taxonomy:**
| Category | Attack Types | Detection Required |
|----------|-------------|-------------------|
| **P**hysical | Manufacturing/materials-based attacks | Sensor-level |
| **A**dversarial AI | Digital adversarial examples, data poisoning | Model-level |
| **C**yber | Network, software exploitation | System-level |
| **E**lectronic Warfare | Jamming, spoofing, deception | Signal-level |

**Evaluation Structure:**
- 24-month cycles of operational test and evaluation (SABER-OpX)
- Red teams develop attack techniques against AI-enabled autonomous systems
- Ground and aerial platforms tested in battlefield environment settings
- Iterative assessment with continuous evaluation

### 4.2 GARD-Era Metrics (Baseline)

| Metric | GARD Threshold | SCBE Current | SCBE Projected |
|--------|---------------|--------------|----------------|
| Detection rate (adversarial inputs) | Not fixed — measured per attack class | 78.7% | 92%+ (with semantic coords) |
| Evasion rate (adaptive attacker) | Measured, not thresholded | 29.6% | <15% (with BFT consensus) |
| Robustness to novel attacks | Required: defend against broad categories | Partial | Strong (geometric = category-agnostic) |
| Open-source reproducibility | Required | Yes (MIT + npm/PyPI) | Yes |

### 4.3 AIQ Mathematical Foundations

AIQ requires:
1. **Formal guarantees** — not just empirical accuracy, but provable bounds on performance
2. **Generalization proofs** — math showing why performance holds beyond training distribution
3. **Quantified capability** — numerical measures of what the system can/cannot do
4. **NIST alignment** — compatibility with NIST evaluation standards

### 4.4 DoD AI Security Framework (FY2026 NDAA, Section 1513)

The FY2026 National Defense Authorization Act directs DoD to create an AI security framework covering:

| Requirement | SCBE Coverage |
|-------------|--------------|
| Supply chain vulnerabilities (data poisoning, adversarial tampering) | 14-layer pipeline with tamper detection (C3) |
| Unintentional data exposure | Tongue encoding + dispersal across 6D space |
| Workforce risks | Governance gate with human-in-the-loop (ESCALATE tier) |
| Security monitoring | Layer 14 audio telemetry + spectral coherence (L9-10) |
| NIST SP 800 series alignment | 74 NIST SP 800-53 controls verified |
| CMMC integration | CMMC 2.0 Ready status |

**Timeline:** DoD must report implementation plan to Congress by **June 16, 2026**.

### 4.5 NIST Cyber AI Profile (December 2025 Draft)

NIST published a preliminary draft of the **Cybersecurity Framework Profile for Artificial Intelligence** (NIST IR 8596) on December 16, 2025.

**Six CSF Functions for AI:**
1. **Govern** — AI risk governance
2. **Identify** — AI asset identification and risk assessment
3. **Protect** — AI system safeguards
4. **Detect** — AI anomaly and attack detection
5. **Respond** — AI incident response
6. **Recover** — AI system recovery

**SCBE already maps to all six** through the NIST AI RMF compliance module (`src/licensing/nist_ai_rmf.py`).

---

## 5. Programs Matching SCBE Core Innovations

### 5.1 Geometric/Mathematical Approaches to AI Safety

**Best Match: COMPASS + AIQ**

SCBE's Poincare ball model IS a novel mathematical framework for AI safety:
- Hyperbolic distance function creates exponential cost for adversarial drift
- This is exactly what COMPASS sought: "paradigm-shifting problem formulations that better characterize complex systems"
- AIQ needs mathematical guarantees — H(d,R) = R^(d^2) provides a formally analyzable cost function

**Supporting Research:** arXiv paper 2504.14668 — "A Byzantine Fault Tolerance Approach towards AI Safety" (April 2025) validates the BFT+AI safety intersection that SCBE already implements.

**SCBE Assets:**
- `src/harmonic/hyperbolic.ts` — Poincare ball implementation
- `src/harmonic/pipeline14.ts` — 14-layer pipeline
- `tests/adversarial/` — Attack simulation suite
- `docs/evidence/SCBE_SECURITY_EVIDENCE_PACK.md` — Honest metrics

### 5.2 Byzantine Fault Tolerance in AI Systems

**Best Match: CLARA + Assured Autonomy**

SCBE already has:
- BFT consensus module (`src/ai_brain/bft-consensus.ts`)
- 6-council review with independent evaluation
- 4/6 quorum requirement for governance decisions
- Test suite: `tests/ai_brain/bft-consensus.test.ts`

The April 2025 arXiv paper on BFT for AI safety uses geometric median as an aggregation rule — SCBE uses the Poincare ball model for the same purpose but in hyperbolic space, which is provably stronger for high-dimensional anomaly detection.

### 5.3 Multi-Model Governance

**Best Match: CLARA + AI Forward + CASTLE**

SCBE's multi-model governance is exactly what DoD needs:
- Shepherd/flock architecture for multi-agent coordination
- Independent tongue-based evaluation per council member
- Governance gate with ALLOW/QUARANTINE/ESCALATE/DENY tiers
- No single point of failure — distributed consensus

### 5.4 AI Estate/Lifecycle Management

**Best Match: Assured Autonomy + NIST Cyber AI Profile**

SCBE covers the full AI lifecycle:
- Training data provenance (SFT pipeline with source tracking)
- Runtime monitoring (spectral coherence, audio telemetry)
- Incident response (self-healing orchestrator, flux contraction)
- Audit trail (decision-level JSONL logs, SIEM integration)
- Recovery (Axiom A7: Recoverability)

### 5.5 Real-Time Video AI Processing for Defense

**No direct DARPA program match found** for real-time video processing specifically. However:
- SABER evaluates AI perception systems (which include video/imaging)
- Assured Autonomy tests camera feed integrity
- SCBE's video processing module (`src/video/`) and page analyzer could be positioned for ISR applications

### 5.6 Post-Quantum Cryptography for AI Systems

**Best Match: SIEVE + QBI context**

SCBE's PQC envelope is production-ready:
- ML-KEM-768 (key encapsulation) — NIST-approved
- ML-DSA-65 (digital signatures) — NIST-approved
- AES-256-GCM (symmetric encryption)
- Sacred Vault v3 (Argon2id + XChaCha20-Poly1305)

This is a **differentiator** — most AI safety systems have NO PQC layer. SCBE is quantum-ready by design.

---

## 6. DoD AI Adoption Pathway

### 6.1 How a Solo Developer Gets DARPA's Attention

**Ranked by feasibility and speed:**

#### Path 1: I2O Office-Wide BAA (Highest Probability)
- **What:** Submit an abstract to the FY2026 I2O BAA (HR001126S0001)
- **Deadline:** November 1, 2026 (abstracts), November 30, 2026 (proposals)
- **Funding:** $500K - $5M
- **Why it works:** Broadest scope, no specific program match required, explicitly welcomes non-traditional contractors
- **SCBE positioning:** Thrust Area 1 (Transformative AI — trustworthy, explainable systems)

#### Path 2: CLARA Proposal (Highest Alignment, Tight Deadline)
- **What:** Submit a full proposal to CLARA
- **Deadline:** April 10, 2026
- **Funding:** Up to $2M
- **Why it works:** SCBE's compositional ML+reasoning architecture IS what CLARA seeks
- **Risk:** Abstracts were due March 2 — submitting without prior abstract is possible but disadvantaged

#### Path 3: AI Exploration (AIE) Fast Track
- **What:** Watch for AIE opportunities under AI Forward umbrella
- **Timeline:** Opportunities appear with 30-45 day windows, start within 3 months
- **Why it works:** Fastest path, streamlined contracting, broad eligibility including small businesses
- **How to monitor:** SAM.gov watch on I2O, DARPAConnect, DARPA events page

#### Path 4: SBIR/STTR Phase I (Reauthorized March 2026)
- **What:** Apply for Phase I when new topics publish (expected April-May 2026)
- **Funding:** Phase I: $50K-$250K; Phase II: $750K-$1.5M
- **New feature:** Strategic Breakthrough Awards up to $30M for scaling companies
- **How to apply:** Register at dodsbirsttr.mil, watch for DARPA-specific topics
- **Key change:** Mandatory due diligence on ownership, patents, employee backgrounds

#### Path 5: Defense Innovation Unit (DIU) Commercial Solutions Opening
- **What:** Submit to DIU's ongoing CSO process for AI/ML or Cyber portfolios
- **Why it works:** Designed for commercial tech companies; uses Other Transaction Authority (OTA)
- **Timeline:** Rolling submissions
- **URL:** https://www.diu.mil/work-with-us

#### Path 6: DARPAConnect + Direct Outreach
- **What:** Register on DARPAConnect, attend virtual events, network with PMs
- **Why it works:** DARPA PMs actively seek novel approaches at events
- **URL:** https://www.darpaconnect.us

### 6.2 TRL Assessment for SCBE

| TRL | Definition | SCBE Status |
|-----|-----------|-------------|
| 1 | Basic principles observed | DONE — Hyperbolic cost scaling proven |
| 2 | Technology concept formulated | DONE — 14-layer pipeline designed |
| 3 | Experimental proof of concept | DONE — 950+ tests passing |
| 4 | Technology validated in lab | DONE — Adversarial benchmarks run |
| 5 | Technology validated in relevant environment | PARTIAL — Simulation only, no field deployment |
| 6 | Technology demonstrated in relevant environment | NOT YET — Need operational deployment |
| 7 | System prototype demonstrated in operational environment | NOT YET |
| 8 | System complete and qualified | NOT YET |
| 9 | System proven in operational environment | NOT YET |

**Current SCBE TRL: 4-5** (validated in lab environment with comprehensive test suite but not yet deployed in operational defense environment)

**What's needed for TRL 6:**
1. Deploy SCBE in a relevant operational context (even simulated battlefield is sufficient)
2. Demonstrate the 14-layer pipeline against realistic adversarial scenarios
3. Show integration with existing defense systems/APIs

**Funding alignment:**
- TRL 1-3: SBIR Phase I, DARPA seedlings
- TRL 4-6: SBIR Phase II, DARPA programs, DIU prototypes
- TRL 6+: Acquisition, production contracts

### 6.3 SBIR/STTR Status (Critical Update — March 2026)

**The SBIR/STTR program has been reauthorized.**

The Senate passed S. 3971 unanimously on March 3, 2026. The House followed on March 17, 2026 (345-41). Awaiting presidential signature. Reauthorized through September 30, 2031.

**Major changes:**
1. **Strategic Breakthrough Awards** — up to $30M per company for scaling (new mechanism, no precedent)
2. **Mandatory due diligence** — ownership, patents, employee backgrounds, financial ties to countries of concern
3. **DoD new solicitations expected April-May 2026**

**SCBE preparation checklist:**
- [ ] Register at dodsbirsttr.mil if not already
- [ ] Prepare SAM.gov entity registration (required)
- [ ] Document patent status (USPTO #63/961,403 — provisional)
- [ ] Prepare 5-page technical brief for rapid response
- [ ] Monitor for DARPA AI security SBIR topics

### 6.4 DARPA + NIST Relationship

DARPA programs explicitly align with NIST frameworks:

| NIST Framework | DARPA Program Using It | SCBE Coverage |
|---------------|----------------------|--------------|
| AI RMF 1.0 | AIQ, Assured Autonomy | Full (22 checks, `src/licensing/nist_ai_rmf.py`) |
| SP 800-53 Rev 5 | SABER evaluations | 74 controls verified |
| FIPS 140-3 | Crypto requirements | ML-KEM-768, ML-DSA-65 compatible |
| Cyber AI Profile (IR 8596) | FY2026 NDAA Section 1513 | Mapped to all 6 CSF functions |
| CMMC 2.0 | Defense contractor requirement | Ready status |

### 6.5 NAICS Codes for SCBE Federal Contracting

| Code | Description | Relevance |
|------|-------------|-----------|
| 541512 | Computer Systems Design Services | Primary |
| 541519 | Other Computer Related Services | AI governance as a service |
| 541715 | R&D in Physical, Engineering, and Life Sciences | Hyperbolic geometry R&D |
| 511210 | Software Publishers | npm/PyPI packages |

---

## 7. SCBE Capability-to-Program Mapping Matrix

| SCBE Capability | DARPA Program(s) | TRL Match | Priority |
|----------------|-------------------|-----------|----------|
| 14-layer security pipeline | SABER, CLARA, Assured Autonomy | 4-5 | HIGH |
| Hyperbolic cost scaling (Poincare ball) | COMPASS, AIQ, CLARA | 4 | HIGH |
| Post-quantum cryptography | SIEVE, QBI (context) | 5 | MEDIUM |
| BFT consensus governance | CLARA, Assured Autonomy | 4 | HIGH |
| Multi-agent fleet orchestration | CASTLE, AI Forward | 4 | MEDIUM |
| Adversarial attack detection | SABER, (GARD legacy tools) | 4 | HIGH |
| Sacred Tongues tokenization | AIQ (mathematical foundations) | 3-4 | LOW (novel, hard to position) |
| NIST RMF compliance | FY2026 NDAA Sec 1513 | 5 | HIGH (regulatory, not DARPA direct) |
| Autonomous web agent | CASTLE, AIxCC | 4 | MEDIUM |
| Swarm coordination (jam-resistant) | SABER, (OFFSET legacy) | 3-4 | MEDIUM |
| Self-healing recovery | Assured Autonomy | 4 | MEDIUM |
| Audit/governance trail | NIST Cyber AI Profile, SABER | 5 | HIGH |

---

## 8. Recommended Action Plan (Next 90 Days)

### Immediate (This Week)

1. **Evaluate CLARA proposal feasibility** — deadline April 10, 2026
   - Read full solicitation DARPA-PA-25-07-02
   - Assess whether submitting without prior abstract is viable
   - Draft 5-page technical approach if proceeding

2. **Register on SAM.gov** if not already registered (required for all federal opportunities)

3. **Register on DARPAConnect** — networking and event access

### Short-Term (April 2026)

4. **Submit CLARA proposal** OR note lessons for I2O BAA
5. **Benchmark SCBE against GARD tools** — run Armory + ART against SCBE pipeline
6. **Monitor SBIR reauthorization** — watch for first DoD AI security topics

### Medium-Term (May-June 2026)

7. **Submit SBIR Phase I** when AI security topics appear
8. **Submit DIU CSO proposal** for AI/ML or Cyber portfolio
9. **Prepare I2O BAA abstract** (due November 1, 2026)

### Ongoing

10. **Set SAM.gov alert** for DARPA I2O
11. **Check DARPA events page weekly** for new AIE opportunities
12. **Track dodsbirsttr.mil** for new SBIR topics (first Wednesday of each month when active)

---

## Sources

### DARPA Program Pages
- [SABER](https://www.darpa.mil/research/programs/saber-securing-artificial-intelligence)
- [CLARA](https://www.darpa.mil/research/programs/clara)
- [AIQ](https://www.darpa.mil/research/programs/aiq-artificial-intelligence-quantified)
- [AI Forward](https://www.darpa.mil/research/programs/ai-forward)
- [AIxCC](https://www.darpa.mil/research/programs/ai-cyber)
- [GARD](https://www.darpa.mil/research/programs/guaranteeing-ai-robustness-against-deception)
- [Assured Autonomy](https://www.darpa.mil/research/programs/assured-autonomy)
- [COMPASS](https://www.darpa.mil/research/programs/compass)
- [SIEVE](https://www.darpa.mil/research/programs/securing-information-for-encrypted-verification-and-evaluation)
- [QBI 2026](https://www.darpa.mil/work-with-us/opportunities/darpa-pa-26-02)

### BAAs and Solicitations
- [SABER BAA FAQ (HR001125S0009)](https://www.darpa.mil/sites/default/files/attachment/2025-04/darpa-program-saber-faqs.pdf)
- [SABER Proposers Day Presentation](https://www.darpa.mil/sites/default/files/attachment/2025-03/program-darpa-saber-proposer-day-presentation.pdf)
- [CLARA FAQ](https://www.darpa.mil/sites/default/files/attachment/2026-03/darpa-program-clara-faq.pdf)
- [I2O Office-Wide BAA](https://www.darpa.mil/about/offices/i2o)
- [DARPA R&D Opportunities](https://www.darpa.mil/work-with-us/opportunities)
- [DARPA Office-Wide BAAs](https://www.darpa.mil/research/opportunities/baa)

### Proposers Days
- [VITAL Proposers Day (March 31, 2026)](https://www.darpa.mil/events/2026/proposers-day-vital)
- [Protean Proposers Day (Feb 20, 2026)](https://www.darpa.mil/events/2026/proposers-day-protean)
- [DARPA Events Calendar](https://www.darpa.mil/events)

### SBIR/STTR
- [DARPA SBIR/STTR Topics](https://www.darpa.mil/work-with-us/communities/small-business/sbir-sttr-topics)
- [DoD SBIR/STTR Portal](https://www.dodsbirsttr.mil/)
- [SBIR/STTR Reauthorization Status](https://sbirgrantwriters.com/sbir-blog-sbir-sttr-landscape-2026)
- [Congress Passes SBIR/STTR Reauthorization](https://grantedai.com/blog/sbir-sttr-reauthorization-passes-congress-strategic-breakthrough-awards-2026)
- [SBIR Reauthorization Guide](https://grantedai.com/learn/guides/sbir-reauthorization-2026-guide)

### DoD and NIST Frameworks
- [FY2026 NDAA AI Security Framework](https://www.crowell.com/en/insights/client-alerts/cmmc-for-ai-defense-policy-law-imposes-ai-security-framework-and-requirements-on-contractors)
- [NIST Cyber AI Profile Draft (IR 8596)](https://csrc.nist.gov/pubs/ir/8596/iprd)
- [DoD AI Cybersecurity RMF Tailoring Guide](https://dodcio.defense.gov/Portals/0/Documents/Library/AI-CybersecurityRMTailoringGuide.pdf)
- [DARPA FY2026 Budget Estimates](https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/budget_justification/pdfs/03_RDT_and_E/RDTE_Vol1_DARPA_MasterJustificationBook_PB_2026.pdf)

### Defense Innovation Unit
- [DIU Work With Us](https://www.diu.mil/work-with-us)
- [DIU Portfolio](https://www.diu.mil/solutions/portfolio)
- [DIU + CDAO AI Deployment](https://www.diu.mil/latest/diu-and-cdao-deploying-ai-for-strategic-impact)

### Analysis and Compilations
- [Every DARPA AI Program You Can Apply To in 2026](https://grantedai.com/blog/every-darpa-ai-program-2026)
- [DARPA Perspective on AI and Autonomy at DoD (CSIS)](https://www.csis.org/analysis/darpa-perspective-ai-and-autonomy-dod)
- [DARPA I2O BAA Analysis (EverGlade)](https://everglade.com/darpa-i2o-office-wide-baa-opens-the-door-for-breakthroughs-in-information-innovation/)
- [DARPA Transitions GARD Tech (DefenseScoop)](https://defensescoop.com/2024/03/27/darpa-transitions-tech-gard-program-cdao/)
- [BFT for AI Safety (arXiv 2504.14668)](https://arxiv.org/abs/2504.14668)
- [DARPA Math + AI Breakthroughs](https://www.darpa.mil/news/2025/math-ai-tomorrows-breakthroughs)
