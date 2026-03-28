# Federal AI Security Standards Research Brief

**Date:** 2026-03-27
**Author:** Issac Davis (@issdandavis)
**Purpose:** Comprehensive mapping of DoD, NIST, NSA, CISA, DISA, and FedRAMP AI security requirements for SCBE-AETHERMOORE product positioning and government contracting readiness.

---

## Table of Contents

1. [NIST AI Risk Management Framework (AI RMF)](#1-nist-ai-risk-management-framework)
2. [DoD AI Ethics Principles and Responsible AI Strategy](#2-dod-ai-ethics-and-responsible-ai)
3. [NIST SP 800-53 Rev 5 AI Control Overlays](#3-nist-sp-800-53-rev-5-ai-overlays)
4. [DISA STIG Requirements for AI/ML](#4-disa-stig-for-aiml)
5. [NSA AI Security Guidance](#5-nsa-ai-security-guidance)
6. [CISA AI Security Programs](#6-cisa-ai-security-programs)
7. [FedRAMP for AI](#7-fedramp-for-ai)
8. [Detection / False Positive / Evasion Thresholds](#8-quantitative-thresholds)
9. [DoD CDAO Requirements](#9-dod-cdao-requirements)
10. [Competitions and Open Evaluations](#10-competitions-and-evaluations)
11. [SCBE Alignment Matrix](#11-scbe-alignment-matrix)

---

## 1. NIST AI Risk Management Framework

### Document: NIST AI 100-1 (AI RMF 1.0)
- **Published:** January 26, 2023
- **Status:** Current (voluntary framework)
- **URL:** https://www.nist.gov/itl/ai-risk-management-framework

### Four Core Functions

| Function | Purpose | Key Sub-categories |
|----------|---------|-------------------|
| **GOVERN** | Establish policies, roles, risk tolerance | GV-1 through GV-6: organizational context, risk tolerance, legal compliance |
| **MAP** | Understand AI system context, risks | MP-1 through MP-5: stakeholder identification, risk categorization |
| **MEASURE** | Evaluate trustworthiness | MS-1 through MS-4: choose metrics, evaluate characteristics, track over time |
| **MANAGE** | Prioritize and respond | MG-1 through MG-4: risk prioritization, response, communication |

### Trustworthiness Characteristics (Required Measurement Dimensions)

1. **Valid and Reliable** -- accuracy, consistency, reproducibility
2. **Safe** -- freedom from unacceptable risk
3. **Secure and Resilient** -- resistance to adversarial attack, graceful degradation
4. **Accountable and Transparent** -- audit trails, decision logging
5. **Explainable and Interpretable** -- human-understandable reasoning
6. **Privacy-Enhanced** -- data minimization, consent
7. **Fair with Harmful Bias Managed** -- equity across demographics

### 2025 Updates (Expected RMF 1.1 Addenda)

- Model provenance and data integrity requirements expanded
- Third-party and open-source model assessment requirements added
- Continuous monitoring and anomaly detection for AI systems emphasized
- Data poisoning detection and model extraction countermeasures called out

### Companion Documents

| Document | Title | Date | Purpose |
|----------|-------|------|---------|
| **NIST AI 600-1** | GenAI Risk Profile | July 2024 | 13 GenAI-specific risks, 400+ mitigation actions |
| **NIST AI 100-2 E2025** | Adversarial ML Taxonomy | March 24, 2025 | Attack/defense taxonomy for PredAI and GenAI |
| **NIST AI 800-1** | Managing Misuse Risk | 2nd public draft, Jan 2025 | Dual-use foundation model misuse mitigation |
| **NIST SP 800-218A** | SSDF for GenAI | Published 2024 | Secure software development for AI models |

### NIST AI 600-1 GenAI Risk Profile Detail

Addresses 13 specific GenAI risk categories:
1. CBRN information or capabilities
2. Confabulation (hallucination)
3. Data privacy
4. Environmental impacts
5. GAI-produced harmful content
6. Homogenization
7. Human-AI configuration
8. Information integrity
9. Information security
10. Intellectual property
11. Obscene/degrading content
12. Value chain and component integration
13. Harmful bias and homogenization

### NIST AI 100-2 E2025 (Adversarial ML Taxonomy) Detail

- **Published:** March 24, 2025 (final, replaces E2023 version)
- **URL:** https://csrc.nist.gov/pubs/ai/100/2/e2025/final

Attack types covered:
- **Predictive AI:** evasion, poisoning, privacy attacks
- **Generative AI:** evasion, poisoning, privacy, misuse attacks
- **New in 2025:** LLM-specific attacks, RAG system attacks, agent-based AI attacks, AI supply chain security

---

## 2. DoD AI Ethics and Responsible AI

### DoD 5 Ethical Principles for AI (Adopted February 2020)

| Principle | Requirement |
|-----------|-------------|
| **Responsible** | Personnel must exercise appropriate care and judgment; governance of AI development and deployment throughout lifecycle |
| **Equitable** | Deliberate steps to minimize unintended bias in AI capabilities |
| **Traceable** | Transparent, auditable methodologies, data sources, design procedures, and documentation |
| **Reliable** | Explicit, well-defined uses; safety, security, and effectiveness tested across entire lifecycle |
| **Governable** | Ability to detect and avoid unintended consequences; ability to disengage or deactivate deployed systems that demonstrate unintended behavior |

### DoD Responsible AI Strategy and Implementation Pathway (2021)

- **Document:** "Implementing Responsible Artificial Intelligence in the Department of Defense" (May 2021)
- **URL:** https://media.defense.gov/2021/May/27/2002730593/-1/-1/0/IMPLEMENTING-RESPONSIBLE-ARTIFICIAL-INTELLIGENCE-IN-THE-DEPARTMENT-OF-DEFENSE.PDF

Six tenets of implementation:
1. RAI governance
2. Warfighter trust
3. RAI product and acquisition lifecycle
4. Requirements validation
5. Responsible AI ecosystem
6. AI workforce

### January 2026 AI Strategy (Current)

- **Document:** "Artificial Intelligence Strategy for the Department of War" (January 9, 2026)
- **URL:** https://media.defense.gov/2026/Jan/12/2003855671/-1/-1/0/ARTIFICIAL-INTELLIGENCE-STRATEGY-FOR-THE-DEPARTMENT-OF-WAR.PDF

Key mandates:
- **AI Fitness Standards:** Established as technological requirements for the Joint Force
- **30-Day Model Deployment:** CDAO directed to establish delivery cadence enabling latest models deployed within 30 days of public release
- **7 Pace-Setting Projects (PSPs):** Initially administered by CDAO
- **AI-First Operations:** Priority shift toward speed, scale, and operational integration
- **AI Enablers:** Infrastructure, data, models, policies, and talent must be shared across projects

### DoD Directive 3000.09 (Autonomy in Weapon Systems)

- **Updated:** January 25, 2023
- **URL:** https://www.esd.whs.mil/portals/54/documents/dd/issuances/dodd/300009p.pdf

Requirements for autonomous systems:
- Function as anticipated in realistic operational environments against adaptive adversaries
- Allow commanders/operators to exercise appropriate levels of human judgment
- Must be consistent with DoD AI Ethical Principles
- 11 additional certification requirements for autonomous weapons from senior review process (CJCS, USD(P), USD(A&S))
- Adequate training, TTPs, and doctrine must be available

### OMB M-24-10 (Federal AI Governance)

- **Executed:** March 28, 2024
- **Compliance Deadline:** December 1, 2024 (implement or terminate non-compliant AI)
- **URL:** https://www.whitehouse.gov/wp-content/uploads/2024/03/M-24-10-Advancing-Governance-Innovation-and-Risk-Management-for-Agency-Use-of-Artificial-Intelligence.pdf

Minimum risk management practices:
- AI impact assessment required before deploying safety- or rights-impacting AI
- Ongoing monitoring and mitigation of discrimination
- Public AI use case inventory
- If mitigation is not possible, must discontinue the AI functionality

---

## 3. NIST SP 800-53 Rev 5 AI Overlays

### COSAiS Project (Control Overlays for Securing AI Systems)

- **URL:** https://csrc.nist.gov/projects/cosais
- **Status:** In development (annotated outline for Predictive AI overlay available January 2026)

### Five Use Cases Being Developed

1. Adapting and Using Generative AI (LLM/Assistant)
2. Using and Fine-Tuning Predictive AI
3. Using AI Agent Systems (Single Agent)
4. Using AI Agent Systems (Multi-Agent)
5. Security Controls for AI Developers

### SP 800-53 Control Families Most Relevant to AI Governance

Based on framework analysis and the COSAiS concept paper, these control families have the strongest AI applicability:

| Family | Name | AI Relevance |
|--------|------|-------------|
| **AC** | Access Control | Model access, API authentication, role-based inference restrictions |
| **AU** | Audit and Accountability | AI decision logging, inference audit trails, training data provenance |
| **CA** | Assessment, Authorization, Monitoring | AI system authorization, continuous monitoring of model behavior |
| **CM** | Configuration Management | Model versioning, hyperparameter tracking, pipeline configuration |
| **CP** | Contingency Planning | Model fallback, graceful degradation, offline operation |
| **IA** | Identification and Authentication | Model identity, API key management, federated model auth |
| **IR** | Incident Response | AI-specific incident handling (hallucination, bias, adversarial attack) |
| **PM** | Program Management | AI governance program, risk strategy, insider threat for AI |
| **PL** | Planning | AI system security plans, rules of behavior for AI operators |
| **RA** | Risk Assessment | AI threat modeling, vulnerability assessment for ML pipelines |
| **SA** | System and Services Acquisition | AI supply chain risk, third-party model assessment, SBOM for AI |
| **SC** | System and Communications Protection | Encryption of model weights, secure inference channels, boundary protection |
| **SI** | System and Information Integrity | Input validation, output verification, anomaly detection for AI |
| **SR** | Supply Chain Risk Management | AI model provenance, training data supply chain, third-party model vetting |
| **PT** | PII Processing and Transparency | Training data privacy, model memorization mitigation |

### Referenced Companion Standards

The overlays cross-reference:
- NIST AI 100-2 E2025 (adversarial ML taxonomy)
- NIST AI 800-1 (dual-use model misuse)
- NIST SP 800-218A (SSDF for AI)
- NIST SP 800-53 Rev 5.1.1 (base catalog)

---

## 4. DISA STIG for AI/ML

### Current Status: No Published AI-Specific STIG

As of March 2026, DISA has **not published a dedicated STIG for AI or ML systems**. There are approximately 500 STIGs covering various systems, devices, and applications, but none specifically address AI/ML security.

### Applicable Existing STIGs

AI systems deployed on DoD networks must still comply with:

| STIG | Relevance to AI |
|------|----------------|
| **Application Security and Development STIG** | Covers secure SDLC; applicable to AI model development pipelines |
| **Web Server STIGs** (Apache, IIS, Nginx) | API endpoints serving AI inference |
| **Database STIGs** (PostgreSQL, Oracle, etc.) | Training data storage, feature stores |
| **Container Platform STIGs** (Docker, Kubernetes) | AI model containerized deployment |
| **Cloud Computing STIGs** | AI workloads in government cloud |
| **Operating System STIGs** | Underlying infrastructure for AI compute |

### STIG Severity Categories (Applicable to AI Security Findings)

| Category | Description | Remediation |
|----------|-------------|-------------|
| **CAT I** | High severity, direct exploitation | Must fix immediately |
| **CAT II** | Medium severity, potential for exploitation | Fix within 30 days |
| **CAT III** | Low severity, hardening weakness | Fix within 90 days |

### Emerging Guidance

DISA's STIG development process may eventually produce AI-specific STIGs based on:
- NIST COSAiS overlay outputs
- NSA AI security guidance
- DoD CIO direction
- CDAO T&E framework requirements

---

## 5. NSA AI Security Guidance

### Joint CSI: "AI Data Security" (May 22, 2025)

- **Authors:** NSA, CISA, FBI, Australian Signals Directorate, NCSC-NZ, NCSC-UK
- **URL:** https://media.defense.gov/2025/May/22/2003720601/-1/-1/0/CSI_AI_DATA_SECURITY.PDF

Three key risk categories identified:
1. **Poisoned Data** -- adversarial/false data inserted into training sets (both overt disinformation and subtle statistical bias/metadata manipulation)
2. **Data Drift** -- gradual or sudden shift in incoming data statistical properties vs. training data; can degrade accuracy or be exploited to bypass safeguards
3. **Data Exfiltration** -- unauthorized extraction of sensitive training data or model internals

Key recommendations:
- Adopt **quantum-resistant digital signatures** (NIST PQC standards) for training data authentication
- Cryptographically sign original data versions; sign all subsequent revisions by the person who made the change
- Use **Zero Trust architecture** for secure enclaves during data processing
- Continuous monitoring for data integrity throughout AI lifecycle

### Joint CSI: "AI/ML Supply Chain Risks and Mitigations" (March 4, 2026)

- **URL:** https://media.defense.gov/2026/Mar/04/2003882809/-1/-1/0/AI_ML_SUPPLY_CHAIN_RISKS_AND_MITIGATIONS.PDF

Six AI supply chain components identified:
1. **Training Data**
2. **Models** (pre-trained, fine-tuned)
3. **Software** (frameworks, libraries, dependencies)
4. **Infrastructure** (compute, storage, networking)
5. **Hardware** (GPUs, TPUs, specialized accelerators)
6. **Third-Party Services** (API providers, cloud ML services)

Required mitigations:
- Identify all suppliers and subcontractors
- Seek information on security controls and policies for AI integrations
- Require **AI Bill of Materials (AI-BOM)** and **Software Bill of Materials (SBOM)**
- Revise risk management and perform threat modeling
- Vulnerability mapping across the AI supply chain
- Maintain AI-specific incident response plan
- Maps risks to **NIST AI 100-2** taxonomy and **MITRE ATLAS** (AI Supply Chain Compromise)

### NDAA Requirements (FY2025)

The National Defense Authorization Act requires the Pentagon to:
- Establish comprehensive cybersecurity and governance policy for **all AI and ML systems within 180 days**
- Address risks: adversarial attacks, data poisoning, unauthorized access
- Ensure continuous monitoring and incident reporting
- Congress seeking NSA to produce an "AI security playbook" (bipartisan bill pending)

---

## 6. CISA AI Security Programs

### JCDC AI Cybersecurity Collaboration Playbook

- **Published:** January 14, 2025
- **URL:** https://www.cisa.gov/resources-tools/resources/ai-cybersecurity-collaboration-playbook
- **PDF:** https://www.cisa.gov/sites/default/files/2025-01/JCDC%20AI%20Playbook.pdf

Development:
- Led by **JCDC.AI** working group
- Shaped by ~150 AI specialists from government, industry, and international partners
- Two tabletop exercises (including September 2024 at Scale AI headquarters, simulating AI cybersecurity incident in financial services)

Playbook goals:
1. Guide voluntary information sharing on AI-related cybersecurity incidents and vulnerabilities
2. Explain CISA's actions after receiving shared information
3. Facilitate broader awareness of AI cybersecurity risks across critical infrastructure
4. Living document, updated as AI threat landscape evolves

### JCDC AI Tabletop Exercise Series

- **URL:** https://www.cisa.gov/topics/partnerships-and-collaboration/joint-cyber-defense-collaborative/Joint-Cyber-Defense-Collaborative-Artificial-Intelligence-Cyber-Tabletop-Exercise-Series
- Regular exercises simulating AI-specific cyber incidents
- Participation open to government and private sector partners

### How to Partner with CISA on AI Security

1. **JCDC Partnership:** Organizations can join JCDC as Alliance Partners (must meet critical infrastructure criteria)
2. **Information Sharing:** Voluntary AI incident reporting through CISA's existing channels
3. **Tabletop Exercises:** Participate in JCDC.AI exercises
4. **CISA Roadmap for AI:** Aligns all CISA AI efforts; organizations can engage through public comment periods
5. **Secure by Design:** CISA's broader initiative includes AI-specific secure development guidance

### CISA Joint Guidance on AI in Operational Technology

- Published 2025 in coordination with international partners
- Addresses AI integration in critical infrastructure OT systems
- Focuses on safe deployment of AI in industrial control environments

---

## 7. FedRAMP for AI

### FedRAMP AI Prioritization Initiative

- **URL:** https://www.fedramp.gov/ai/
- **Announced:** August 25, 2025 (GSA/FedRAMP)

Focus: Prioritizing authorization of AI-based cloud services providing conversational AI for federal workers.

### Qualification Criteria

To qualify for the fast-track AI authorization path:
1. Enterprise-grade offering with demonstrated government demand
2. Included in GSA Multiple Award Schedule program
3. Able to meet **FedRAMP 20x** pilot authorization requirements within **two months** of qualification

### FedRAMP 20x Program

- **Phase One Pilot:** Automated validation to rapidly assess security posture
- **Timeline:** Shortened from months to weeks
- **Target:** FedRAMP 20x Low authorization by January 2026

Key security requirements:
- Single sign-on (SSO)
- Role-based access controls (RBAC)
- Strict data segregation
- Alignment with **NIST SP 800-53** controls
- **FedRAMP Moderate:** 325+ security controls (access management, encryption, incident response, continuous monitoring)

### Current AI Authorization Status (as of Q1 2026)

| Vendor | Product | Authorization Level | Date |
|--------|---------|-------------------|------|
| Google | Gemini (Workspace) | FedRAMP High | March 2025 (first GenAI assistant at High) |
| Anthropic | Claude (AWS) | FedRAMP High | April 2, 2025 |
| Anthropic | Claude (GCP) | FedRAMP High | June 11, 2025 |
| C3 AI | C3 AI Platform | FedRAMP Moderate | December 11, 2025 |
| Microsoft | Azure AI Services | FedRAMP High | Confirmed 2025 |

### Emerging AI-Specific FedRAMP Requirements

FedRAMP is transitioning toward:
- Automated monitoring and enforcement of commercial security best practices
- Industry-led, data-driven security reporting (replacing manual documentation)
- Machine-readable security packages (RFC-0024)
- Continuous monitoring operating model for AI services

---

## 8. Quantitative Thresholds

### SCBE Military-Grade Eval Scale (Internal Reference)

From `docs/specs/MILITARY_GRADE_EVAL_SCALE.md`:

| Level | Name | Detection Rate | Evasion Rate | False Positive |
|-------|------|---------------|-------------|----------------|
| 10 | Adaptive Defense | >87% | <30% | -- |
| 11 | Execution Control | >90% | <20% | -- |
| 12 | Multi-Gate | >92% | <15% | -- |
| 13 | BFT Consensus | >94% | <10% | -- |
| 14 | Formal Verification | >96% | <5% | -- |
| 15 | Red Team Certified | >97% | <3% | -- |
| 16 | TEMPEST Grade | >98.5% | <1% | -- |
| 17 | Sovereign | >99.5% | <0.1% | -- |

### DARPA AIxCC Results (August 2025) -- Benchmark for AI Vulnerability Detection

| Metric | Semifinals | Finals | Improvement |
|--------|-----------|--------|-------------|
| Vulnerability identification | 37% | 86% | +49 pts |
| Patch rate (of identified) | 25% | 68% | +43 pts |
| Average patch time | -- | 45 minutes | -- |
| Code analyzed | -- | 54M lines | -- |
| Fully autonomous operation | -- | 143 hours | -- |

Scoring weights: Patching is weighted **3x** vs. identification alone. Time-decaying score incentivizes speed.

### DoD T&E Metrics for AI Systems

From CDAO Test and Evaluation Framework:
- **Accuracy** -- correct classification/prediction rate
- **Precision** -- positive predictive value
- **Recall** -- sensitivity / true positive rate
- **Robustness** -- performance under adversarial input perturbation
- **Drift detection** -- monitoring for data/concept drift post-deployment
- **Latency** -- inference time under operational load
- **Test adequacy** -- diversity coverage of test dataset relative to operational domain
- **Data sufficiency** -- presence of feature interactions in test data vs. operational environment

No publicly specified universal thresholds -- these are per-program and per-mission.

### Industry Reference Benchmarks

| System | Detection Rate | FPR | Evasion | Notes |
|--------|---------------|-----|---------|-------|
| No defense | 0% | 0% | 100% | Baseline |
| Basic keyword filter | ~20% | ~5% | ~80% | Level 3 equivalent |
| DeBERTa PromptGuard | 76.7% | ~0% | 32.0% | Trained classifier |
| SCBE RuntimeGate (current) | 78.7% | 100%* | 29.6% | Geometric cost, text-feature input |
| Llama Guard (estimated) | ~85% | ~5% | ~25% | Meta's safety model |
| SCBE + semantic coords (projected) | ~92% | ~10% | ~15% | Level 12 target |
| SCBE + BFT consensus (projected) | ~96% | ~5% | ~5% | Level 14 target |

*SCBE's 100% FPR is from aggressive reroute rules, not from the harmonic wall. Tuned thresholds should drop to <15%.

---

## 9. DoD CDAO Requirements

### Organization

The Chief Digital and Artificial Intelligence Office (CDAO) was formed in 2022 by merging:
- Joint Artificial Intelligence Center (JAIC)
- Defense Digital Services (DDS)
- Office of Advancing Analytics
- Chief Data Officer

**URL:** https://www.ai.mil/

### Test and Evaluation Framework

- **Framework URL:** https://www.ai.mil/Portals/137/Documents/Resources%20Page/CDAO_TE_Framework_-_OTE_TES_2024-04-compressed.pdf
- **DTE Guidebook:** Published February 26, 2025 (https://aaf.dau.edu/storage/2025/03/DTE_of_AIES_Guidebook_Final_26Feb25_signed.pdf)

Six areas of T&E guidance:
1. **Performance** -- accuracy, precision, recall, robustness against adversarial inputs
2. **Testing Methods** -- statistical testing, operational testing, red teaming
3. **Data** -- test adequacy (diversity), data sufficiency (feature interaction coverage)
4. **AI Models** -- model-specific evaluation methodologies
5. **Context** -- operational environment realism
6. **Documentation** -- reproducibility, traceability of experiments

### JATIC (Joint AI Test Infrastructure Capability)

- **URL:** https://cdao.pages.jatic.net/public/
- **Purpose:** Open-source software tools for DoD AI T&E and assurance

Key tools:
- **XAITK** (Explainable AI Toolkit) -- explainability analysis
- **NRTK** (Natural Robustness Toolkit) -- robustness testing
- **Armory** integration (from DARPA GARD)
- Framework for Assurance of AI-Enabled Systems (public release March 2025)

### 2026 AI Adoption Standards

From the January 2026 DoD AI Strategy:
- **30-day deployment cadence:** Latest AI models must be deployable within 30 days of public release
- **AI enablers sharing:** All infrastructure, data, models, policies from Pace-Setting Projects must be available department-wide
- **AI fitness standards:** Technological requirements for the Joint Force
- **Compliance with:** OMB M-24-10 and NSM-25 (National Security Memorandum on AI)

### DoD Approved AI Tools

No single "approved list" exists. Instead:
- Tools must meet the relevant T&E framework requirements
- Must comply with DoD Directive 3000.09 (if autonomous/semi-autonomous weapons)
- Must pass through the Risk Management Framework (RMF) process
- FedRAMP authorization required for cloud-based AI tools
- JATIC tools are available for all DoD programs

---

## 10. Competitions and Evaluations

### DARPA AI Cyber Challenge (AIxCC)

- **URL:** https://aicyberchallenge.com/
- **Prize Pool:** $29.5 million cumulative ($7M for small businesses)
- **Final Competition:** DEF CON 2025

Results:
1. **Team Atlanta** -- $4 million
2. **Trail of Bits** -- $3 million
3. **Theori** -- $1.5 million

Performance: 77% vulnerability detection, 61% patch rate across 54M lines of code in 143 hours of autonomous operation.

DARPA is transitioning AIxCC technology to "widespread use."

### DARPA SABER (Securing AI for Battlefield Effective Robustness)

- **URL:** https://www.darpa.mil/research/programs/saber-securing-artificial-intelligence
- **Program Manager:** Nathaniel Bastian
- **Solicitation:** HR001125S0009
- **Focus:** Building operational AI red team capability
- **Targets:** AI-enabled autonomous ground and aerial systems deployable within 1-3 years
- **Status:** Closed to new proposals for current cycle

Evaluation approach:
- 9-month exercise period with 4 different exercises
- Creating metric baselines for blue and red teams
- Iterative testing on unmanned ground vehicles
- Assessing: data poisoning, adversarial patches, model stealing, electronic warfare attacks

### DARPA GARD (Guaranteeing AI Robustness Against Deception)

- **URL:** https://www.darpa.mil/research/programs/guaranteeing-ai-robustness-against-deception
- **Status:** Concluded early 2024
- **Legacy outputs (all open source):**
  - **Armory** -- evaluation testbed for repeatable, scalable adversarial defense testing (GitHub)
  - **Adversarial Robustness Toolbox (ART)** -- defense/evaluation library (IBM Research, widely used)
  - **APRICOT** dataset -- physical adversarial patch evaluation for object detection

### MITRE ATLAS (Adversarial Threat Landscape for AI Systems)

- **URL:** https://atlas.mitre.org/
- **Current scope (October 2025):** 15 tactics, 66 techniques, 46 sub-techniques
- **Technique IDs:** AML.TXXXX format (e.g., AML.T0051 = prompt injection)
- **October 2025 update:** Added 14 new agentic AI techniques (collaboration with Zenity Labs)
- **SAFE-AI report:** Framework for securing AI systems (full report on ATLAS site)

Key facts:
- ~70% of ATLAS mitigations map to existing security controls
- Free tools: ATLAS Navigator, Arsenal (for threat modeling and red teaming)
- Maps to NIST and NSA guidance

### Other Active Programs (2026)

From DARPA's 2026 AI program catalog:
- Multiple AI programs open for proposals
- Focus areas include autonomous systems, adversarial robustness, AI assurance
- Check https://grantedai.com/blog/every-darpa-ai-program-2026 for current opportunities

---

## 11. SCBE Alignment Matrix

### How SCBE-AETHERMOORE Maps to Federal Requirements

| Federal Requirement | SCBE Capability | Gap / Action Needed |
|--------------------|----------------|-------------------|
| **NIST AI RMF GOVERN** | L13 governance decision layer, governance module | Document risk tolerance policies formally |
| **NIST AI RMF MAP** | 14-layer pipeline with layer annotations | Need formal stakeholder analysis artifact |
| **NIST AI RMF MEASURE** | Military-grade eval scale, test tiers L1-L6 | Expand continuous monitoring telemetry |
| **NIST AI RMF MANAGE** | ALLOW/QUARANTINE/ESCALATE/DENY decisions | Need incident response runbook for AI-specific events |
| **DoD Responsible (ethics)** | Audit trail in governance module | Need lifecycle governance documentation |
| **DoD Equitable (ethics)** | Sacred Tongues multi-dimensional scoring | Need bias testing across demographic inputs |
| **DoD Traceable (ethics)** | Layer annotations, @layer tags, axiom comments | Strong alignment -- document formally |
| **DoD Reliable (ethics)** | 6-tier test architecture, property-based testing | Strong alignment -- need operational environment testing |
| **DoD Governable (ethics)** | Kill-switch via DENY tier, disengage capability | Strong alignment -- document formally |
| **SP 800-53 AC** | API authentication, role-based access | Need formal access control documentation |
| **SP 800-53 AU** | Decision logging exists | Expand to full audit trail per inference |
| **SP 800-53 CM** | Git versioning, pipeline config | Need SBOM/AI-BOM generation |
| **SP 800-53 IR** | Self-healing orchestrator | Need AI-specific incident playbook |
| **SP 800-53 RA** | Hyperbolic threat scoring | Map to formal risk assessment methodology |
| **SP 800-53 SA** | Supply chain awareness | Need formal AI supply chain risk assessment |
| **SP 800-53 SI** | RuntimeGate input validation | Need output verification layer |
| **SP 800-53 SR** | Model provenance tracking | Need AI-BOM and SBOM tooling |
| **NSA PQC guidance** | Post-quantum crypto (ML-KEM-768, ML-DSA-65) | Strong alignment -- already implemented |
| **NSA Zero Trust** | Hyperbolic cost-based trust | Document ZTA mapping formally |
| **NSA AI-BOM** | Not yet implemented | Priority gap -- implement AI-BOM generation |
| **CISA JCDC Playbook** | Incident reporting capability exists | Join JCDC as Alliance Partner |
| **FedRAMP** | Not yet authorized | Long-term goal -- start with 20x Low path |
| **CDAO T&E Framework** | 6-tier test architecture + eval scale | Map test tiers to CDAO six areas formally |
| **MITRE ATLAS** | 14-layer pipeline covers multiple ATLAS techniques | Map pipeline layers to ATLAS technique coverage |

### SCBE Strongest Competitive Positions for Government

1. **Post-Quantum Cryptography** -- already implementing NIST PQC standards (ML-KEM-768, ML-DSA-65), directly aligned with NSA May 2025 guidance
2. **Geometric Cost Model** -- unique approach (hyperbolic cost scaling) not available in competing products
3. **Multi-Dimensional Scoring** -- 6-tongue coordinate system provides explainable, multi-factor risk assessment
4. **14-Layer Pipeline** -- defense-in-depth architecture maps well to DoD layered security requirements
5. **Governance Decision Tiers** -- ALLOW/QUARANTINE/ESCALATE/DENY maps to DoD risk decision framework

### Priority Gaps to Close for Government Readiness

1. **False Positive Rate** -- current 100% FPR (from reroute rules) must drop below 15% for any government deployment
2. **Semantic Embedding Upgrade** -- replace text statistics with semantic embeddings in `_text_to_coords()` to reach Level 10+
3. **AI-BOM / SBOM Generation** -- required by NSA March 2026 supply chain guidance
4. **Formal Compliance Documentation** -- generate AI RMF compliance artifacts from `src/licensing/nist_ai_rmf.py`
5. **FedRAMP Preparation** -- long-term but start documenting against SP 800-53 controls now
6. **MITRE ATLAS Mapping** -- map 14-layer pipeline to ATLAS technique coverage matrix
7. **CDAO T&E Alignment** -- formally map test tiers to CDAO framework six areas

---

## Key Document Registry

| Document Number | Title | Date | Agency | URL |
|----------------|-------|------|--------|-----|
| NIST AI 100-1 | AI Risk Management Framework 1.0 | Jan 2023 | NIST | https://www.nist.gov/itl/ai-risk-management-framework |
| NIST AI 100-2 E2025 | Adversarial ML Taxonomy | Mar 2025 | NIST | https://csrc.nist.gov/pubs/ai/100/2/e2025/final |
| NIST AI 600-1 | GenAI Risk Profile | Jul 2024 | NIST | https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf |
| NIST AI 800-1 (draft) | Managing Misuse Risk | Jan 2025 | NIST/AISI | https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.800-1.ipd2.pdf |
| NIST SP 800-53 Rev 5 | Security and Privacy Controls | Sep 2020 (updated) | NIST | https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final |
| NIST SP 800-218A | SSDF for GenAI | 2024 | NIST | https://csrc.nist.gov/pubs/sp/800/218/a/final |
| COSAiS | SP 800-53 AI Overlays | In development | NIST | https://csrc.nist.gov/projects/cosais |
| DoD AI Ethics | 5 Principles | Feb 2020 | DoD | https://www.war.gov/News/Releases/Release/Article/2091996/ |
| DoD RAI Strategy | Implementing RAI | May 2021 | DoD | https://media.defense.gov/2021/May/27/2002730593/ |
| DoD AI Strategy 2026 | AI Strategy for Dept of War | Jan 2026 | DoD | https://media.defense.gov/2026/Jan/12/2003855671/ |
| DoDD 3000.09 | Autonomy in Weapon Systems | Jan 2023 | DoD | https://www.esd.whs.mil/portals/54/documents/dd/issuances/dodd/300009p.pdf |
| OMB M-24-10 | Federal AI Governance | Mar 2024 | OMB | https://www.whitehouse.gov/wp-content/uploads/2024/03/M-24-10 |
| NSA CSI AI Data | AI Data Security | May 2025 | NSA/CISA/FBI | https://media.defense.gov/2025/May/22/2003720601/ |
| NSA CSI AI Supply Chain | AI/ML Supply Chain Risks | Mar 2026 | NSA+ | https://media.defense.gov/2026/Mar/04/2003882809/ |
| CISA JCDC AI Playbook | AI Cybersecurity Collaboration | Jan 2025 | CISA | https://www.cisa.gov/resources-tools/resources/ai-cybersecurity-collaboration-playbook |
| CDAO T&E Framework | OTE of AI Capabilities | Apr 2024 | CDAO | https://www.ai.mil/Portals/137/Documents/Resources%20Page/CDAO_TE_Framework |
| CDAO DTE Guidebook | DTE of AI Systems | Feb 2025 | CDAO/DAU | https://aaf.dau.edu/storage/2025/03/DTE_of_AIES_Guidebook_Final_26Feb25_signed.pdf |
| MITRE ATLAS | AI Threat Framework | Oct 2025 | MITRE | https://atlas.mitre.org/ |
| AIxCC | AI Cyber Challenge | Aug 2025 | DARPA | https://aicyberchallenge.com/ |
| DARPA SABER | AI Red Team Program | 2025 | DARPA | https://www.darpa.mil/research/programs/saber-securing-artificial-intelligence |

---

*This document is a research compilation for internal SCBE-AETHERMOORE strategic planning. It is not legal advice and does not constitute a compliance certification. All framework references should be verified against primary sources before use in proposals or compliance claims.*
