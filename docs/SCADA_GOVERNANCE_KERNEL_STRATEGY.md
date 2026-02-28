# SCADA Governance Kernel Strategy

**SCBE-AETHERMOORE as a Governance Kernel for Critical Infrastructure**

Version: 1.0
Date: 2026-02-27
Classification: Business Strategy -- Confidential

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [SCADA Market Overview](#2-scada-market-overview)
3. [The Vulnerability Crisis](#3-the-vulnerability-crisis)
4. [Five Core Pain Points](#4-five-core-pain-points)
5. [SCBE Capability Mapping](#5-scbe-capability-mapping)
6. [What a Governance Kernel Is](#6-what-a-governance-kernel-is)
7. [Three-Ring Architecture](#7-three-ring-architecture)
8. [Competitive Landscape](#8-competitive-landscape)
9. [Regulatory Alignment](#9-regulatory-alignment)
10. [Certification Roadmap](#10-certification-roadmap)
11. [Go-to-Market Strategy](#11-go-to-market-strategy)
12. [Product Packaging](#12-product-packaging)
13. [90-Day Action Plan](#13-90-day-action-plan)
14. [Funding Sources](#14-funding-sources)
15. [Required New Development](#15-required-new-development)

---

## 1. Executive Summary

Critical infrastructure operators face a convergence of threats that existing cybersecurity products were never designed to address: AI-driven attacks against operational technology (OT), lateral movement across flattened IT/OT networks, quantum computing timelines that render current cryptographic protections obsolete, and a regulatory environment that is shifting from voluntary guidance to mandatory compliance.

The market for SCADA cybersecurity is projected to grow from $13.95 billion in 2025 to $31.19 billion by 2035 (6.3% CAGR). The adjacent industrial cybersecurity market is even larger, reaching $25-26 billion in 2025 and projected to hit $135 billion by 2029. Yet every major player in this space -- Claroty, Nozomi Networks, Dragos -- sells the same category of product: network visibility, anomaly detection, and asset inventory. None of them sit inside the decision loop. None of them provide a mathematical cost model for adversarial behavior. None of them offer post-quantum cryptography. None of them have a framework for governing AI agents operating within OT environments.

SCBE-AETHERMOORE is not a firewall, an IDS, or a SIEM. It is a **governance kernel** -- a small, formally specifiable decision core that wraps every command, telemetry read, and AI action in a mathematically grounded trust envelope before it reaches a physical process. The 14-layer hyperbolic pipeline makes adversarial drift exponentially expensive. The post-quantum cryptographic layer (ML-KEM-768, ML-DSA-65) protects decision integrity against harvest-now-decrypt-later attacks already underway. The Sacred Tongue classification system provides deterministic, auditable routing of every decision through governance checkpoints.

This document lays out the strategy for extracting a hardened Ring 0 governance kernel from the existing SCBE codebase (~1,500 SLOC, zero external dependencies, formally specifiable), wrapping it in SCADA-specific protocol adapters (Modbus TCP, DNP3, OPC UA, IEC 61850), and selling it to critical infrastructure operators as the governance layer they are missing.

The opportunity window is now. CISA, NSA, and FBI jointly published AI-in-OT guidance in December 2025, creating a greenfield regulatory surface that no existing vendor addresses. Operators who adopt AI for predictive maintenance and process optimization have no governance framework for those AI decisions. SCBE fills that gap.

---

## 2. SCADA Market Overview

### Market Size and Growth

| Metric | Value |
|--------|-------|
| Global SCADA market (2025) | $13.95 billion |
| Projected market (2035) | $31.19 billion |
| CAGR (2025-2035) | 6.3% |
| Industrial cybersecurity market (2025) | $25-26 billion |
| Industrial cybersecurity projected (2029) | $135 billion |
| OT security services spend (2025) | $4.2 billion |

### Key Growth Drivers

1. **IT/OT convergence acceleration**. Enterprise networks and operational networks are merging. Every major industrial operator is connecting previously air-gapped SCADA systems to cloud analytics, predictive maintenance platforms, and enterprise resource planning systems. This creates attack surface that did not exist five years ago.

2. **AI adoption in operations**. Operators are deploying machine learning models for anomaly detection, predictive maintenance, process optimization, and autonomous control. None of these deployments have governance frameworks. The models make decisions that affect physical processes -- valve positions, turbine speeds, chemical ratios -- with no mathematically grounded trust envelope.

3. **Regulatory tightening**. NERC CIP is expanding scope. IEC 62443 is becoming a procurement requirement. The EU NIS2 Directive mandates OT security for essential services. The US Executive Order on AI Safety creates obligations for AI systems in critical infrastructure.

4. **Quantum computing timeline**. NIST published post-quantum cryptographic standards in 2024. The harvest-now-decrypt-later threat means that SCADA communications captured today can be decrypted when quantum computers become available. Operators managing 30-year infrastructure lifecycles must begin PQC migration now.

### Sector Breakdown

| Sector | Market Share | Key Characteristics |
|--------|-------------|---------------------|
| Energy/Utilities | 35% | NERC CIP mandated, longest asset lifecycles (30-50 years) |
| Oil and Gas | 20% | Remote operations, high consequence of failure |
| Water/Wastewater | 15% | Severely underfunded, high public health impact |
| Manufacturing | 15% | Fastest AI adoption, complex supply chains |
| Transportation | 10% | Rail signaling, port operations, aviation ground systems |
| Other (mining, pharma) | 5% | Emerging regulatory requirements |

---

## 3. The Vulnerability Crisis

### 2025: The Worst Year on Record

The industrial cybersecurity threat landscape reached unprecedented severity in 2025:

- **2,155 CVEs** disclosed across **508 CISA ICS advisories** -- the highest single-year count ever recorded.
- **5,967 ransomware attacks** against industrial organizations globally.
- **25%** of all ransomware attacks now target OT-connected environments (up from 12% in 2023).
- **Average downtime** per OT ransomware incident: 12.3 days.
- **Average cost** per OT security incident: $4.7 million (including production losses).
- **42%** of industrial organizations experienced at least one cyber incident affecting OT operations.

### Attack Vector Evolution

The threat has evolved beyond traditional IT attacks repurposed against OT:

1. **AI-powered reconnaissance**. Attackers use LLMs to analyze publicly available SCADA documentation, PLC programming manuals, and control system architectures to craft targeted attacks without prior OT expertise.

2. **Living-off-the-land in OT**. Attackers leverage legitimate engineering tools (vendor maintenance software, PLC programming environments, HMI configuration utilities) to move laterally and modify control logic without deploying custom malware.

3. **Supply chain compromise**. Firmware updates, vendor remote access channels, and third-party integrators serve as entry points that bypass perimeter defenses entirely.

4. **Ransomware-as-a-Service targeting OT**. Criminal groups specifically market OT-capable ransomware variants. Groups like ALPHV/BlackCat, LockBit successors, and Cl0p have dedicated OT playbooks.

5. **State-sponsored prepositioning**. Nation-state actors (Volt Typhoon, Sandworm successors) maintain persistent access to critical infrastructure networks for future disruption capability.

### Why Existing Defenses Fail

Current OT cybersecurity products detect threats after they are inside the network. They monitor traffic patterns, flag anomalies, and generate alerts. But they do not govern decisions. When a legitimate-looking command arrives at a PLC -- properly authenticated, sent over an authorized channel, from a recognized workstation -- existing tools have no mathematical basis to evaluate whether the commanded action is safe, appropriate, and consistent with the operational context.

This is the gap SCBE fills.

---

## 4. Five Core Pain Points

### Pain Point 1: Legacy Infrastructure with 20-30 Year Lifecycles

**The problem.** SCADA systems deployed in the 1990s and 2000s run on protocols designed for serial communication, not TCP/IP networks. Modbus, DNP3, and many proprietary protocols have no authentication, no encryption, and no integrity verification. These systems cannot be replaced -- they control physical processes with decades of validated operating history. Ripping out a 25-year-old DCS and replacing it introduces more risk than the cyber threat it mitigates.

**Why current solutions fail.** Network monitoring tools can observe traffic on legacy protocols but cannot inject governance into the command path without breaking the protocol or introducing unacceptable latency.

**How SCBE addresses this.** The governance kernel operates as a transparent inline proxy. It decodes Modbus/DNP3 commands, evaluates them against the 14-layer pipeline, wraps approved commands in a decision envelope, and forwards them with sub-millisecond overhead. The protocol itself is unchanged -- the PLC receives exactly what it expects. The governance decision and its mathematical proof are recorded in the audit trail.

### Pain Point 2: IT/OT Convergence Without Governance

**The problem.** Connecting OT to enterprise IT enables analytics, remote operations, and efficiency gains. But it also means that a compromised email account, a vulnerable web application, or a phished employee can now reach control system networks. The attack surface expanded by orders of magnitude, but the governance model did not change.

**Why current solutions fail.** Firewalls and DMZs provide network segmentation, but they operate on IP addresses and port numbers. They cannot evaluate whether a command from an authorized IP is contextually appropriate -- whether the commanded valve position makes sense given current process conditions, time of day, and operational mode.

**How SCBE addresses this.** The hyperbolic distance metric (`dH = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))`) measures the semantic distance between a commanded action and the current safe operational envelope. Commands that drift from safe operation face exponentially increasing cost via the Harmonic Wall (`H(d,R) = R^(d^2)`). Legitimate operational commands cluster near the origin in Poincare space. Adversarial commands -- even if they arrive from authorized channels -- are mathematically distinguishable by their position in the embedding.

### Pain Point 3: Flat OT Networks Enable Lateral Movement

**The problem.** Most OT networks are flat. Once an attacker reaches Level 1 (basic control), they can communicate with every PLC, RTU, and IED on the network. There is no micro-segmentation, no zero-trust architecture, and no identity verification at the device level. Lateral movement is trivial.

**Why current solutions fail.** Micro-segmentation products designed for IT environments (VMware NSX, Illumio) do not understand OT protocols, do not support legacy devices, and introduce latency that can disrupt real-time control loops.

**How SCBE addresses this.** The 14-layer pipeline embeds every device, command, and data flow into hyperbolic space. Legitimate communication patterns form tight clusters. Lateral movement creates vectors that cross cluster boundaries, generating exponentially high cost scores. The governance kernel flags and quarantines cross-boundary commands without modifying the underlying network topology. No switch reconfiguration. No VLAN changes. Pure software governance overlay.

### Pain Point 4: No AI Governance for Operational Technology

**The problem.** Operators are deploying AI/ML models in OT environments for predictive maintenance, process optimization, anomaly detection, and increasingly for autonomous control decisions. These models make recommendations or take actions that affect physical processes. There is no framework for governing what an AI model is allowed to do in an OT environment, no audit trail for AI-driven decisions, and no mathematical basis for evaluating whether an AI recommendation is safe.

**Why current solutions fail.** This is a greenfield problem. No existing OT cybersecurity vendor addresses AI governance. CISA, NSA, and FBI jointly published guidance on AI in OT systems in December 2025, but it is advisory only. No product implements it.

**How SCBE addresses this.** The SCBE governance kernel was designed from the ground up for AI decision governance. Every AI recommendation passes through the 14-layer pipeline. The Harmonic Wall provides a mathematical cost function. The decision tier system (ALLOW / QUARANTINE / ESCALATE / DENY) provides deterministic governance outcomes. The Sacred Tongue classification system routes decisions through domain-specific governance checkpoints (KO for control intent, RU for policy constraints, UM for security labels). Decision envelopes create immutable, cryptographically signed audit trails for every AI action.

### Pain Point 5: Quantum Computing Threatens Long-Lived Infrastructure

**The problem.** SCADA systems have 20-30 year lifecycles. Quantum computers capable of breaking RSA-2048 and ECC-256 are projected to arrive within 10-15 years. Communications encrypted today with classical cryptography can be stored and decrypted later (harvest-now-decrypt-later). For infrastructure with 30-year operational horizons, the quantum threat is not hypothetical -- it is a present-day data protection failure.

**Why current solutions fail.** No major OT cybersecurity vendor offers post-quantum cryptography. Claroty, Nozomi, and Dragos all rely on classical TLS for their management plane and offer no PQC option for data-at-rest or decision integrity.

**How SCBE addresses this.** SCBE implements NIST-standardized post-quantum algorithms: ML-KEM-768 for key encapsulation and ML-DSA-65 for digital signatures (via liboqs). Decision envelopes are signed with ML-DSA-65, ensuring that governance decisions remain tamper-evident even against quantum adversaries. The PQC implementation is in `src/crypto/pqc_liboqs.py` with algorithm fallback support for environments running older liboqs versions.

---

## 5. SCBE Capability Mapping

The following table maps specific SCADA security requirements to existing SCBE capabilities with file-level references to the implementation.

| SCADA Need | SCBE Capability | File Reference |
|---|---|---|
| Flat networks / lateral movement prevention | 14-Layer Pipeline with hyperspace embedding. Commands embedded in Poincare ball; lateral movement vectors cross cluster boundaries with exponential cost. | `src/harmonic/pipeline14.ts` |
| Behavioral anomaly detection | Harmonic Wall cost function: `H(d,R) = R^(d^2)`. Anomalous behavior faces exponentially increasing cost as it diverges from safe operational envelope. | `src/symphonic_cipher/harmonic_scaling_law.py` |
| Quantum vulnerability / harvest-now-decrypt-later | Post-Quantum Cryptography: ML-KEM-768 (key encapsulation), ML-DSA-65 (digital signatures). NIST-standardized algorithms via liboqs. | `src/crypto/pqc_liboqs.py` |
| No AI governance framework for OT | Four-tier decision system: ALLOW / QUARANTINE / ESCALATE / DENY. Context-aware governance with trust scoring. | `src/security-engine/context-engine.ts` |
| Content and command integrity verification | Semantic Antivirus membrane with Sacred Tongue classification. Every command is semantically analyzed and classified before reaching the control layer. | `agents/antivirus_membrane.py` |
| Drift from safe operational envelope | Hyperbolic distance metric in Poincare ball model. Distance from safe origin measured via `dH = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))`. | `src/harmonic/hyperbolic.ts` |
| No continuous trust model | Trust decay with intent persistence. Trust is not binary -- it decays over time and must be continuously re-earned through consistent behavior. | `src/security-engine/context-engine.ts` |
| Audit trail gaps and non-repudiation | Decision envelopes with cryptographic signatures and optional blockchain anchoring. Every governance decision is immutably recorded with full context. | `src/governance/decision_envelope_v1.py` |

### Additional Capability Matrix

| SCBE Component | SCADA Application | Maturity |
|---|---|---|
| 14-Layer Pipeline (`pipeline14.ts`) | Inline command evaluation for Modbus/DNP3/OPC UA | Production (needs protocol adapters) |
| Hyperbolic Embedding (`hyperbolic.ts`) | Operational envelope definition and drift detection | Production |
| Harmonic Wall (`harmonic_scaling_law.py`) | Cost function for anomaly scoring | Production |
| PQC Signatures (`pqc_liboqs.py`) | Decision envelope integrity, future-proof audit trails | Production |
| Context Engine (`context-engine.ts`) | Trust management, decision routing, escalation | Production |
| Semantic Antivirus (`antivirus_membrane.py`) | Command content analysis, injection detection | Production |
| Decision Envelopes (`decision_envelope_v1.py`) | Immutable audit trail, regulatory evidence | Production |
| Sacred Tongue Classification | Domain-specific governance routing (KO/AV/RU/CA/UM/DR) | Production |
| GeoSeed Network (`src/geoseed/`) | Distributed governance across multi-site SCADA | R&D (M6) |
| Blockchain Ledger | Tamper-evident decision history for compliance | Production |

---

## 6. What a Governance Kernel Is

### The Problem with Perimeter Thinking

The entire OT cybersecurity industry is built on perimeter thinking: detect threats at the network boundary, monitor traffic for anomalies, alert operators when something looks wrong. This model has three fundamental flaws:

1. **Detection is not prevention.** By the time a network monitor flags an anomalous Modbus write, the PLC has already received and potentially executed the command.

2. **Alerts do not scale.** A typical SCADA deployment generates thousands of network events per minute. Alert fatigue means that critical detections are buried in noise. The median time to investigate an OT alert is 4.2 hours.

3. **No mathematical basis for "normal."** Current anomaly detection relies on statistical baselines that drift over time, generate false positives during legitimate operational changes, and cannot distinguish between a novel-but-safe operational mode and an adversarial manipulation.

### Governance Kernel: Inside the Decision Loop

A governance kernel is fundamentally different from a firewall, IDS, or SIEM. It does not sit at the network boundary watching traffic pass. It sits **inside the decision loop** -- between the point where a command is issued and the point where it reaches a physical actuator.

```
Traditional Architecture:
  [Command Source] --> [Network] --> [Firewall/IDS] --> [PLC/RTU]
                                          |
                                     (monitors,
                                      alerts,
                                      logs)

Governance Kernel Architecture:
  [Command Source] --> [SCBE Kernel] --> [PLC/RTU]
                            |
                      (evaluates,
                       decides,
                       wraps in envelope,
                       enforces)
```

The governance kernel:

- **Evaluates** every command against the 14-layer pipeline before it reaches the control device.
- **Decides** (ALLOW / QUARANTINE / ESCALATE / DENY) based on mathematically grounded cost functions, not statistical thresholds.
- **Wraps** approved commands in cryptographically signed decision envelopes that create non-repudiable audit trails.
- **Enforces** governance decisions inline -- a DENY verdict means the command does not reach the PLC, period.
- **Proves** its decisions. Every verdict comes with a mathematical proof: the hyperbolic distance from safe operation, the Harmonic Wall cost, the trust score, and the decision rationale. This proof is verifiable by any party with access to the decision envelope.

### Analogy: seL4 for Operational Governance

The seL4 microkernel (8,700 lines of C, formally verified) proved that a small, mathematically specified kernel can provide security guarantees that no amount of testing can achieve for a larger system. SCBE takes the same approach to operational governance:

- **Small**: Ring 0 target is ~1,500 SLOC of pure Python with zero external dependencies.
- **Formally specifiable**: The Harmonic Wall function, hyperbolic distance metric, and trust decay model are mathematical functions with well-defined properties that can be expressed in TLA+ and verified in Lean 4.
- **Deterministic**: Given the same input and state, the kernel always produces the same decision. No probabilistic models. No neural network inference in the critical path.
- **Auditable**: Every input, every intermediate computation, and every output is recorded in the decision envelope.

---

## 7. Three-Ring Architecture

The SCBE governance kernel for SCADA follows a three-ring architecture inspired by operating system kernel design. Each ring has a defined trust boundary, a maximum code size, and a clear interface contract.

### Ring 0: Pure Decision Core

| Property | Value |
|----------|-------|
| Size target | ~1,500 SLOC pure Python |
| Dependencies | Zero (stdlib only) |
| Functions | Hyperbolic distance, Harmonic Wall, trust decay, decision logic |
| Determinism | Fully deterministic -- same input always produces same output |
| Formal verification target | TLA+ specification, Lean 4 proofs |
| Latency budget | < 1ms per decision |

Ring 0 contains only the mathematical core:

1. **Hyperbolic distance computation.** Poincare ball distance between the commanded action vector and the safe operational envelope centroid.
2. **Harmonic Wall cost evaluation.** `H(d,R) = R^(d^2)` applied to the hyperbolic distance.
3. **Trust score computation.** Current trust level with time-decay applied.
4. **Decision function.** Maps (cost, trust, context) to {ALLOW, QUARANTINE, ESCALATE, DENY}.
5. **Envelope generation.** Packages the decision with its proof into a signable structure.

Ring 0 has no I/O, no network access, no file system access, no logging, and no configuration parsing. It receives a structured input (command vector, current state vector, trust state) and returns a structured output (decision, proof, envelope). This makes it formally verifiable.

**Extraction path.** Ring 0 is extracted from the existing codebase:
- `src/harmonic/hyperbolic.ts` (distance computation) -> Pure Python reimplementation
- `src/symphonic_cipher/harmonic_scaling_law.py` (cost function) -> Direct extraction
- `src/security-engine/context-engine.ts` (trust + decision) -> Pure Python reimplementation

### Ring 1: Governance Services

| Property | Value |
|----------|-------|
| Size target | ~5,000-8,000 SLOC |
| Dependencies | Minimal (cryptography, logging) |
| Functions | PQC signatures, audit logging, state persistence, configuration |
| Latency budget | < 5ms per decision |

Ring 1 wraps Ring 0 with operational services:

1. **PQC signature service.** Signs decision envelopes with ML-DSA-65. Source: `src/crypto/pqc_liboqs.py`.
2. **Audit logger.** Writes decision envelopes to append-only storage. Source: `src/governance/decision_envelope_v1.py`.
3. **State manager.** Persists trust state, operational envelope definitions, and configuration.
4. **Configuration service.** Loads and validates operational parameters (decision thresholds, tongue weights, trust decay rates).
5. **Sacred Tongue router.** Classifies incoming commands by domain (KO/AV/RU/CA/UM/DR) and routes them through appropriate governance checkpoints.
6. **Escalation manager.** Routes QUARANTINE and ESCALATE decisions to human operators via configured channels.

Ring 1 has restricted I/O: it can write to the audit log, read configuration files, and communicate with Ring 2 via a defined IPC interface. It cannot initiate network connections, execute external processes, or modify its own code.

### Ring 2: Enforcement Points (Protocol Adapters)

| Property | Value |
|----------|-------|
| Size | Variable per protocol |
| Dependencies | Protocol-specific libraries |
| Functions | Protocol decode/encode, inline proxy, device communication |
| Latency budget | < 10ms total (including Ring 0 + Ring 1) |

Ring 2 is the outermost ring and the only ring that touches the network and protocol layer:

1. **Modbus TCP adapter.** Decodes Modbus function codes (FC01-FC16), extracts register addresses and values, constructs command vectors for Ring 0 evaluation, and forwards approved commands to the PLC.
2. **DNP3 adapter.** Handles DNP3 application layer objects, integrity polls, event data, and control relay output blocks (CROBs).
3. **OPC UA adapter.** Translates OPC UA service requests (Read, Write, Call, Browse) into governance-evaluable command vectors.
4. **IEC 61850 adapter.** Handles MMS messages, GOOSE frames, and Sampled Values for substation automation.
5. **API gateway.** Exposes REST/gRPC endpoints for management, monitoring, and integration with existing SCADA management platforms.

Ring 2 adapters are the only components that vary by deployment. The governance decision (Ring 0) and governance services (Ring 1) are identical across all installations. This separation is critical for certification -- Ring 0 and Ring 1 are certified once and deployed everywhere.

### Inter-Ring Communication

```
Ring 2 (Protocol Adapter)
  |
  | Structured Command Vector (JSON/protobuf)
  v
Ring 1 (Governance Services)
  |
  | Pure Input Struct (command_vec, state_vec, trust_state)
  v
Ring 0 (Decision Core)
  |
  | Pure Output Struct (decision, proof, envelope_body)
  v
Ring 1 (Governance Services)
  |
  | Signed Envelope + Forwarding Instruction
  v
Ring 2 (Protocol Adapter)
  |
  | Original Protocol Command (if ALLOW) or DROP/REDIRECT
  v
[Physical Device]
```

All inter-ring communication uses immutable data structures. No shared mutable state between rings. Ring 0 never receives a reference to Ring 1 or Ring 2 objects -- only copies of primitive data.

---

## 8. Competitive Landscape

### Major Players

| Company | Funding / Valuation | Core Product | Revenue Est. (2025) | Key Gap |
|---------|-------------------|--------------|---------------------|---------|
| **Claroty** | $882M raised; considering $3.5B IPO | Network visibility, asset inventory, threat detection | $250-300M ARR | No mathematical cost model, no PQC, no AI governance |
| **Nozomi Networks** | Acquired by Mitsubishi Electric (Sep 2025) | Network monitoring, anomaly detection, asset intelligence | $150-200M ARR | Acquisition integration risk; no governance kernel concept |
| **Dragos** | $440M raised | Threat intelligence, network monitoring, incident response | $150-180M ARR | Intelligence-focused, no inline governance, no PQC |
| **Fortinet OT** | Public ($FTNT) | FortiGate ruggedized firewalls + FortiSIEM | $400M+ (OT segment) | Traditional firewall model, no OT-specific governance |
| **Palo Alto (Prisma OT)** | Public ($PANW) | Network segmentation, asset discovery | $200M+ (OT segment) | IT security ported to OT, no process-aware governance |

### What None of Them Have

Every company in this space sells variations of network monitoring and anomaly detection. The gaps are structural, not incremental:

1. **No mathematical cost model.** No competitor uses a formally defined cost function to evaluate command safety. They rely on statistical baselines, signature matching, or machine learning classifiers -- all of which produce probabilistic outputs that cannot be formally verified.

2. **No post-quantum cryptography.** Zero OT cybersecurity vendors ship PQC. Their management planes use classical TLS. Their audit trails are signed with RSA or ECDSA. A quantum computer breaks every signature they have ever produced.

3. **No AI governance framework.** As operators deploy AI in OT environments (and they are -- predictive maintenance is a $12B market), no vendor offers a framework for governing what AI models are allowed to do. The December 2025 CISA/NSA/FBI guidance on AI in OT creates regulatory pressure with no vendor solution.

4. **No continuous trust with mathematical proof.** Current "zero trust" products in OT implement binary authentication (you are authenticated or you are not). None implement continuous trust scoring with time decay, behavioral analysis, and mathematical proof of trust state.

5. **No inline governance.** Every competitor is a monitor. They watch traffic, generate alerts, and produce reports. None of them sit in the command path and enforce decisions inline. When Claroty detects an anomalous Modbus write, it sends an alert to the SOC. The PLC has already executed the command.

### SCBE Differentiation Summary

| Capability | Claroty | Nozomi | Dragos | SCBE |
|------------|---------|--------|--------|------|
| Network visibility | Yes | Yes | Yes | Via Ring 2 adapters |
| Anomaly detection | Statistical | ML-based | Intel + statistical | Mathematical (Harmonic Wall) |
| Inline governance | No | No | No | **Yes (core value proposition)** |
| Mathematical cost model | No | No | No | **Yes (H(d,R) = R^(d^2))** |
| Post-quantum crypto | No | No | No | **Yes (ML-KEM-768, ML-DSA-65)** |
| AI governance for OT | No | No | No | **Yes (ALLOW/QUARANTINE/ESCALATE/DENY)** |
| Continuous trust scoring | No | Partial | No | **Yes (decay + intent persistence)** |
| Formal verification path | No | No | No | **Yes (TLA+ -> Lean 4)** |
| Decision audit with proof | No | No | No | **Yes (decision envelopes)** |

### Competitive Moat

SCBE's moat is mathematical, not commercial. A competitor can replicate a UI, match a feature list, or undercut pricing. They cannot retroactively build a formally verifiable mathematical governance framework. The 14-layer pipeline, hyperbolic embedding, Harmonic Wall cost function, and Sacred Tongue classification system represent years of mathematical R&D. The formal verification path (TLA+ specification, Lean 4 proofs) creates a certification barrier that cannot be fast-followed.

---

## 9. Regulatory Alignment

### NERC CIP (North American Electric Reliability Corporation Critical Infrastructure Protection)

| NERC CIP Standard | Requirement | SCBE Alignment |
|-------------------|-------------|----------------|
| CIP-005-7 | Electronic Security Perimeter | Ring 2 adapters enforce perimeter governance with protocol-level inspection |
| CIP-007-6 | System Security Management | Ring 1 provides continuous security monitoring with audit trails |
| CIP-010-4 | Configuration Change Management | Decision envelopes record every configuration change with cryptographic proof |
| CIP-011-3 | Information Protection | PQC ensures information protection against quantum adversaries |
| CIP-013-2 | Supply Chain Risk Management | Semantic Antivirus evaluates firmware and software updates before deployment |

### IEC 62443 (Industrial Automation and Control Systems Security)

| IEC 62443 Part | Scope | SCBE Alignment |
|----------------|-------|----------------|
| 62443-2-1 | Security Management System | Governance kernel provides automated, auditable security management |
| 62443-3-3 | System Security Requirements (SL 1-4) | 14-layer pipeline maps directly to security levels; SL4 achievable with Ring 0 formal verification |
| 62443-4-1 | Secure Product Development Lifecycle | Three-ring architecture with formal specification supports SDL certification |
| 62443-4-2 | Technical Security Requirements for IACS Components | Ring 0 + Ring 1 certifiable as a component with defined security functions |

### NIST SP 800-82 Rev 3 (Guide to OT Security)

NIST SP 800-82 Rev 3 (published 2023, revised guidance 2025) provides the canonical US government framework for OT security. SCBE alignment:

| NIST 800-82 Control Family | SCBE Implementation |
|-----------------------------|---------------------|
| Access Control (AC) | Continuous trust scoring replaces binary authentication |
| Audit and Accountability (AU) | Decision envelopes with PQC signatures provide non-repudiable audit trails |
| Configuration Management (CM) | Every configuration change passes through governance kernel |
| Incident Response (IR) | QUARANTINE and ESCALATE decisions enable automated incident response |
| Risk Assessment (RA) | Harmonic Wall provides continuous, mathematical risk assessment |
| System and Communications Protection (SC) | PQC protects all governance communications |
| System and Information Integrity (SI) | Semantic Antivirus validates command and content integrity |

### CISA/NSA/FBI AI-in-OT Guidance (December 2025)

The joint guidance published in December 2025 addresses AI systems operating in OT environments. Key requirements and SCBE alignment:

| Guidance Requirement | SCBE Implementation |
|---------------------|---------------------|
| AI decision explainability | Decision envelopes contain full mathematical proof of every AI governance decision |
| AI action boundaries | Harmonic Wall enforces mathematically defined operational boundaries |
| AI audit trail | Every AI decision wrapped in signed envelope with hyperbolic distance, cost, and trust score |
| Human oversight of AI | ESCALATE decision tier routes AI actions requiring human review |
| AI model integrity | Semantic Antivirus validates model outputs before they reach physical processes |

This guidance creates a greenfield opportunity. No existing vendor has a product that addresses it. SCBE is architecturally aligned by design, not by retrofit.

---

## 10. Certification Roadmap

Certification is the moat that converts technical capability into enterprise sales. The roadmap is sequenced to build credibility progressively while minimizing upfront cost.

### Phase 1: SOC 2 Type II (Months 1-9)

| Item | Detail |
|------|--------|
| Cost | $50,000-$100,000 |
| Duration | 6-9 months (3-month readiness + 3-6 month observation) |
| Scope | Ring 1 governance services + management plane |
| Value | Table stakes for enterprise sales; proves operational maturity |

SOC 2 does not certify the product -- it certifies the organization's controls for managing the product. This is the minimum credibility threshold for enterprise procurement.

### Phase 2: IEC 62443-4-1 (Months 6-15)

| Item | Detail |
|------|--------|
| Cost | $100,000-$200,000 |
| Duration | 9-12 months |
| Scope | Secure development lifecycle for SCBE governance kernel |
| Value | Required for OT product procurement in EU and increasingly in North America |
| Certifying bodies | TUV SUD, Exida, ISA Secure |

IEC 62443-4-1 certifies the development process, not the product. It proves that SCBE is built using a secure development lifecycle with threat modeling, secure coding, security testing, and vulnerability management.

### Phase 3: IEC 62443-4-2 (Months 12-24)

| Item | Detail |
|------|--------|
| Cost | $200,000-$400,000 |
| Duration | 12-18 months |
| Scope | Ring 0 + Ring 1 as an IACS component |
| Target | Security Level 3 (SL3) initially, SL4 with formal verification |
| Value | Differentiator -- very few cybersecurity products hold this certification |

IEC 62443-4-2 certifies the product itself against technical security requirements. Achieving SL3 demonstrates protection against intentional violation using sophisticated means with moderate resources. SL4 (with formal verification of Ring 0) demonstrates protection against intentional violation using sophisticated means with extended resources and IACS-specific skills.

### Phase 4: FedRAMP (Months 18-30)

| Item | Detail |
|------|--------|
| Cost | $500,000-$1,000,000 |
| Duration | 12-18 months |
| Scope | Cloud-hosted governance kernel management plane |
| Value | Required for US federal agency procurement |
| Prerequisite | SOC 2 + additional NIST 800-53 controls |

FedRAMP is expensive but opens the entire US federal market, including DOE, DOD, and DHS. Given that SCBE targets critical infrastructure operators, many of whom are regulated by federal agencies, FedRAMP authorization significantly reduces procurement friction.

### Formal Verification Track (Parallel, Months 6-24)

| Phase | Tool | Scope | Duration |
|-------|------|-------|----------|
| Specification | TLA+ | Ring 0 decision logic, trust decay, state transitions | 3-6 months |
| Type-level proofs | Lean 4 | Harmonic Wall properties, hyperbolic distance invariants | 6-12 months |
| Full verification | Lean 4 / Coq | Ring 0 complete correctness proof | 12-24 months |

Formal verification is not a certification per se, but it provides mathematical proof of correctness that no testing-based certification can match. For SCADA operators managing nuclear, chemical, or dam control systems, formal verification is the ultimate trust signal.

---

## 11. Go-to-Market Strategy

### Channel Strategy: Three Vectors

#### Vector 1: System Integrator (SI) Partnerships

**Rationale.** Critical infrastructure operators do not buy cybersecurity products from unknown vendors. They buy from system integrators they already trust -- companies that designed and built their SCADA systems.

**Target SIs:**
- Schneider Electric (EcoStruxure partner network)
- Siemens (MindSphere ecosystem)
- Honeywell (Forge platform partners)
- Rockwell Automation (PartnerNetwork)
- ABB (Ability platform)
- Emerson (Plantweb ecosystem)
- Wood Group, Worley, Bechtel (EPC firms)

**Partnership model.** SCBE provides the governance kernel as an OEM component that SIs integrate into their solution offerings. SIs handle customer relationships, deployment, and first-line support. SCBE provides the kernel, updates, and tier-3 support.

**Revenue split.** 70% to SCBE, 30% to SI (or SI marks up to customer).

#### Vector 2: Managed Security Service Provider (MSSP) Model

**Rationale.** Smaller operators (water utilities, municipal power, regional gas distributors) cannot staff OT security teams. They need managed services.

**Model.** SCBE operates as a managed governance service:
1. Deploy governance kernel on customer's OT network (on-premises appliance or VM).
2. Remote monitoring and tuning of governance policies from SCBE SOC.
3. Incident response support for QUARANTINE and ESCALATE events.
4. Monthly governance reports with compliance evidence.

**Pricing.** Monthly recurring revenue per monitored site. See Section 12.

#### Vector 3: Open-Source Core + Enterprise License

**Rationale.** Trust in critical infrastructure is earned through transparency. An open-source governance kernel allows operators, regulators, and researchers to inspect the mathematical foundations.

**Model.**
- **Open-source**: Ring 0 decision core + basic Ring 1 services. MIT or Apache 2.0 license.
- **Enterprise license**: Ring 2 protocol adapters (Modbus, DNP3, OPC UA, IEC 61850), PQC signatures, management console, multi-site federation, MSSP management plane, and formal verification artifacts.

This mirrors the model used by HashiCorp (Terraform), Elastic, and Redis -- open-source core builds trust and adoption; enterprise features generate revenue.

### Sales Motion

| Phase | Duration | Activities |
|-------|----------|------------|
| Discovery | 2-4 weeks | OT architecture review, threat model, compliance gap analysis |
| Proof of Value | 4-8 weeks | Deploy governance kernel on non-critical OT segment, demonstrate decision envelopes |
| Pilot | 3-6 months | Expand to production OT segment, tune governance policies, validate latency |
| Production | Ongoing | Full deployment, managed service, compliance reporting |

### Target Verticals (Sequenced)

1. **Electric utilities** (first). NERC CIP creates mandatory compliance spend. Largest OT security budgets. Most mature procurement processes.
2. **Oil and gas** (second). High consequence of failure creates urgency. Remote operations require governance for unsupervised AI actions.
3. **Water/wastewater** (third). Severely underfunded but high-profile incidents (Oldsmar 2021, numerous 2024-2025 incidents) are driving federal funding.
4. **Manufacturing** (fourth). Fastest AI adoption in OT creates AI governance demand.

---

## 12. Product Packaging

### Tier 1: Pilot

| Item | Detail |
|------|--------|
| Price | $25,000/year |
| Scope | Single site, up to 50 monitored OT assets |
| Includes | Ring 0 + Ring 1 + one Ring 2 protocol adapter (Modbus or OPC UA) |
| Support | Business hours email/ticket |
| Deployment | On-premises VM (customer-provided) |
| Audit | Monthly governance summary report |
| Target | Water utilities, small manufacturers, municipal power |

### Tier 2: Professional

| Item | Detail |
|------|--------|
| Price | $150,000/year |
| Scope | Single site, up to 500 monitored OT assets |
| Includes | Ring 0 + Ring 1 + all Ring 2 protocol adapters |
| Support | 24/7 phone + remote incident response |
| Deployment | Dedicated appliance (SCBE-provided) or customer VM |
| Audit | Weekly governance reports + quarterly compliance package |
| Features | PQC signatures, multi-protocol support, Sacred Tongue classification |
| Target | Regional utilities, mid-size oil and gas, large manufacturers |

### Tier 3: Enterprise

| Item | Detail |
|------|--------|
| Price | $500,000/year |
| Scope | Multi-site (up to 10 sites), unlimited OT assets |
| Includes | Full stack + MSSP management plane + multi-site federation |
| Support | 24/7 dedicated account team + on-site support (2 visits/year) |
| Deployment | Managed appliances at each site with centralized management |
| Audit | Continuous compliance dashboard + regulatory submission packages |
| Features | All Professional features + formal verification artifacts + blockchain audit anchoring + GeoSeed distributed governance (when available) |
| Target | Major utilities (IOU), national oil and gas operators, critical manufacturing |

### Tier 4: Government / National Security

| Item | Detail |
|------|--------|
| Price | Custom (typically $1M+/year) |
| Scope | Multi-site with classified environment support |
| Includes | Full stack + air-gapped deployment + FedRAMP authorized management plane |
| Support | Dedicated on-site team |
| Deployment | Customer-classified environments with no external connectivity |
| Features | All Enterprise features + formal verification proofs + air-gapped update mechanism |
| Target | DOE national laboratories, DOD installations, intelligence community |

### Revenue Projections (Conservative)

| Year | Pilots | Professional | Enterprise | Government | Total ARR |
|------|--------|-------------|------------|------------|-----------|
| Year 1 | 5 | 1 | 0 | 0 | $275,000 |
| Year 2 | 10 | 5 | 1 | 0 | $1,250,000 |
| Year 3 | 15 | 10 | 3 | 1 | $4,375,000 |
| Year 4 | 20 | 15 | 7 | 2 | $8,875,000 |
| Year 5 | 25 | 25 | 12 | 3 | $15,625,000 |

---

## 13. 90-Day Action Plan

### Days 1-30: Foundation

| # | Task | Owner | Deliverable |
|---|------|-------|-------------|
| 1 | Extract Ring 0 decision core from existing codebase | Engineering | `src/scada/ring0/` -- ~1,500 SLOC, zero deps, full test suite |
| 2 | Build Modbus TCP protocol adapter (Ring 2) | Engineering | `src/scada/adapters/modbus_tcp.py` -- decode FC01-FC16, construct command vectors |
| 3 | Write TLA+ specification for Ring 0 decision logic | Engineering | `specs/tla/ring0_decision.tla` -- formal specification of decision function |
| 4 | Set up SCADA testbed with Modbus simulator | Engineering | Hardware/VM testbed with OpenPLC + Modbus TCP simulator |
| 5 | Identify 3 target electric utilities for pilot outreach | Business Dev | Contact list with CISOs/OT security leads |
| 6 | Draft IEC 62443-4-1 gap assessment | Compliance | Gap analysis document identifying SDL gaps to close |

### Days 31-60: Integration and Outreach

| # | Task | Owner | Deliverable |
|---|------|-------|-------------|
| 7 | Complete Modbus adapter end-to-end testing | Engineering | Governance kernel evaluating live Modbus commands in testbed |
| 8 | Begin DNP3 protocol adapter | Engineering | `src/scada/adapters/dnp3.py` -- basic DNP3 object decode |
| 9 | Demonstrate <10ms total latency (Ring 0 + Ring 1 + Ring 2) | Engineering | Benchmark report with p50/p95/p99 latency measurements |
| 10 | Apply to ISA/IEC 62443 certification program | Compliance | Application submitted to certifying body (TUV SUD or Exida) |
| 11 | Contact Idaho National Laboratory NRTS program | Business Dev | Introduction meeting scheduled |
| 12 | Contact University of Illinois CREDC | Business Dev | Research partnership proposal submitted |
| 13 | Submit DOE CESER SENTRY grant pre-proposal | Business Dev | Pre-proposal document submitted |

### Days 61-90: Proof of Value

| # | Task | Owner | Deliverable |
|---|------|-------|-------------|
| 14 | Deploy governance kernel on SCADA testbed in "monitor" mode | Engineering | Running system with decision envelopes generated for all Modbus traffic |
| 15 | Generate first compliance evidence package | Compliance | Sample NERC CIP evidence package using governance kernel audit data |
| 16 | Complete OPC UA protocol adapter (basic) | Engineering | `src/scada/adapters/opcua.py` -- Read/Write service request handling |
| 17 | Publish white paper: "Mathematical Governance for Critical Infrastructure" | Marketing | Peer-reviewable technical paper establishing thought leadership |
| 18 | Secure first pilot commitment (LOI) | Business Dev | Signed letter of intent from pilot customer |
| 19 | Begin SOC 2 readiness assessment | Compliance | SOC 2 readiness report with remediation plan |
| 20 | Demo at S4 Conference or similar OT security event | Marketing | Live demonstration of governance kernel on Modbus traffic |

---

## 14. Funding Sources

### Federal Grants and Programs

#### DOE CESER SENTRY Program

| Item | Detail |
|------|--------|
| Agency | Department of Energy, Office of Cybersecurity, Energy Security, and Emergency Response (CESER) |
| Program | Security Engineering Testbed for Resilient Yields (SENTRY) |
| Funding | $15-30M per year in grants |
| Relevance | Directly funds cybersecurity R&D for energy sector critical infrastructure |
| SCBE fit | Governance kernel for SCADA aligns with SENTRY's focus on resilient OT security |
| Timeline | Rolling solicitations; next anticipated Q2 2026 |

#### CISA Cybersecurity Grants

| Item | Detail |
|------|--------|
| Agency | Cybersecurity and Infrastructure Security Agency |
| Program | State and Local Cybersecurity Grant Program (SLCGP) |
| Funding | $1B over 4 years (FY2022-2025), likely renewed |
| Relevance | Funds cybersecurity improvements for state/local critical infrastructure including water and power |
| SCBE fit | Governance kernel can be funded as a cybersecurity improvement for municipal utilities |
| Approach | Partner with state agencies as the technology provider; they apply for the grant |

#### DHS SBIR/STTR

| Item | Detail |
|------|--------|
| Agency | Department of Homeland Security, Science and Technology Directorate |
| Program | Small Business Innovation Research (SBIR) / Small Business Technology Transfer (STTR) |
| Funding | Phase I: $150,000 (6 months), Phase II: $1,000,000 (24 months) |
| Relevance | Directly funds cybersecurity technology development for critical infrastructure |
| Topics | DHS regularly publishes topics on OT security, AI safety, and post-quantum cryptography |
| SCBE fit | Ring 0 formal verification + PQC integration + AI governance are all active DHS SBIR topic areas |

#### NSF Secure and Trustworthy Cyberspace (SaTC)

| Item | Detail |
|------|--------|
| Agency | National Science Foundation |
| Program | SaTC: Transition to Practice (TTP) |
| Funding | $500,000-$1,200,000 per award |
| Relevance | Funds transition of cybersecurity research to practical deployment |
| SCBE fit | Formal verification of governance kernel + deployment in SCADA environments |

### Venture Capital and Strategic Investment

| Source | Rationale | Target |
|--------|-----------|--------|
| OT-focused VC (e.g., DataTribe, Team8, AllegisCyber) | Specialize in critical infrastructure cybersecurity startups | Seed/Series A: $2-5M |
| Strategic investment from SI partners | Schneider, Siemens, or Honeywell corporate venture arms | Strategic: $5-10M |
| DOD-focused VC (e.g., Shield Capital, Lux Capital) | Growing focus on critical infrastructure as national security | Series A: $5-15M |

### Academic Partnerships (Non-Dilutive)

| University | Program | Value |
|-----------|---------|-------|
| Idaho National Laboratory | NRTS (National Reactor Testing Station) + ICS security research | Testbed access, joint publications, credibility |
| University of Illinois Urbana-Champaign | CREDC (Cyber Resilient Energy Delivery Consortium) | DOE-funded research consortium, utility operator access |
| Purdue University | CERIAS + Smart Grid security research | Academic validation, student pipeline |
| Carnegie Mellon / SEI | ICS-CERT partnership, formal methods research | Formal verification collaboration |

---

## 15. Required New Development

### Critical Path Items

#### 1. Protocol Adapters (Ring 2)

| Adapter | Priority | Complexity | Estimated Effort |
|---------|----------|-----------|-----------------|
| Modbus TCP | P0 | Medium | 4-6 weeks |
| DNP3 | P0 | High | 6-8 weeks |
| OPC UA | P1 | High | 8-12 weeks |
| IEC 61850 (MMS/GOOSE) | P2 | Very High | 12-16 weeks |
| EtherNet/IP (CIP) | P2 | Medium | 4-6 weeks |
| BACnet (building automation) | P3 | Medium | 4-6 weeks |

Each adapter must:
- Decode protocol-specific commands into a normalized command vector format.
- Operate as a transparent inline proxy (the downstream device receives an unmodified protocol message).
- Add less than 5ms of latency to the command path.
- Handle protocol-specific error conditions and failover.

#### 2. Sub-10ms Decision Latency

**Current state.** The existing 14-layer pipeline runs in a general-purpose Python/TypeScript environment optimized for correctness, not latency. SCADA control loops typically require sub-100ms response times, with some applications (protective relaying, turbine control) requiring sub-10ms.

**Required work.**
- Profile Ring 0 decision path and eliminate all allocation in the hot path.
- Pre-compute operational envelope embeddings (avoid recomputing hyperbolic distances from scratch).
- Implement Ring 0 in pure C or Rust with Python bindings for the management plane.
- Target: p99 < 1ms for Ring 0, p99 < 10ms for full stack (Ring 0 + Ring 1 + Ring 2).

#### 3. Safety Integrity Level (SIL) Awareness

**Current state.** SCBE treats all decisions equally. In SCADA environments, different assets have different Safety Integrity Levels (SIL 1-4 per IEC 61508). A SIL 4 system (e.g., emergency shutdown system) requires different governance thresholds than a SIL 1 system (e.g., temperature display).

**Required work.**
- Add SIL classification to the command vector.
- Adjust decision thresholds based on SIL level (higher SIL = more conservative decisions).
- Implement SIL-specific escalation paths (SIL 3-4 QUARANTINE decisions require immediate human intervention).
- Document SIL-awareness for IEC 62443-4-2 certification.

#### 4. Ring 0 Formal Extraction

**Current state.** The mathematical primitives exist across multiple files in TypeScript and Python. They are correct but entangled with I/O, logging, and framework dependencies.

**Required work.**
- Extract pure mathematical functions into a standalone module with zero imports.
- Write comprehensive property-based tests (Hypothesis for Python, fast-check for TypeScript).
- Write TLA+ specification covering all state transitions and invariants.
- Begin Lean 4 proof of Harmonic Wall properties (monotonicity, convexity, boundary behavior).
- Target: Ring 0 passes all property tests and satisfies TLA+ specification.

#### 5. Operational Envelope Definition Tools

**Current state.** SCBE evaluates commands against a learned or configured "safe" operational state. For SCADA, operators need tools to define what "safe" means for their specific processes.

**Required work.**
- Build an operational envelope definition UI where operators specify:
  - Valid register ranges for each PLC/RTU.
  - Permitted function codes per device.
  - Rate-of-change limits for analog values.
  - Time-of-day access controls.
  - Process interlock logic (if valve A is open, valve B must be closed).
- Compile operator-defined envelopes into Poincare ball embeddings that Ring 0 evaluates against.

#### 6. Failsafe and Bypass Mechanisms

**Current state.** SCBE does not have a concept of hardware bypass. In SCADA environments, the governance kernel must never become a single point of failure for physical process control.

**Required work.**
- Design hardware bypass relay that routes commands directly to the PLC if the governance kernel fails.
- Implement watchdog timer: if Ring 0 does not produce a decision within the latency budget, the bypass engages.
- Log bypass events (the bypass itself generates an audit record, even though the governance decision was not made).
- Support "monitor-only" deployment mode where the kernel evaluates and logs but does not enforce.

#### 7. Multi-Site Federation

**Current state.** SCBE operates as a single-site deployment. Large operators (utilities, pipeline operators) have dozens or hundreds of sites.

**Required work.**
- Centralized management plane for policy distribution across sites.
- Aggregated governance dashboard showing decision distribution across all sites.
- Federated audit trail with cross-site query capability.
- Site-level autonomy: each site's governance kernel operates independently if the management plane is unreachable.
- GeoSeed Network (M6) provides the architectural foundation for this -- distributed governance across multi-nodal topology.

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| CISA | Cybersecurity and Infrastructure Security Agency (US) |
| CVE | Common Vulnerabilities and Exposures |
| DCS | Distributed Control System |
| DNP3 | Distributed Network Protocol 3 |
| EPC | Engineering, Procurement, and Construction |
| FedRAMP | Federal Risk and Authorization Management Program |
| GOOSE | Generic Object Oriented Substation Event (IEC 61850) |
| HMI | Human-Machine Interface |
| IACS | Industrial Automation and Control Systems |
| ICS | Industrial Control Systems |
| IED | Intelligent Electronic Device |
| IOU | Investor-Owned Utility |
| MMS | Manufacturing Message Specification (IEC 61850) |
| MSSP | Managed Security Service Provider |
| NERC CIP | North American Electric Reliability Corporation Critical Infrastructure Protection |
| OPC UA | Open Platform Communications Unified Architecture |
| OT | Operational Technology |
| PLC | Programmable Logic Controller |
| PQC | Post-Quantum Cryptography |
| RTU | Remote Terminal Unit |
| SCADA | Supervisory Control and Data Acquisition |
| SI | System Integrator |
| SIL | Safety Integrity Level (IEC 61508) |
| SL | Security Level (IEC 62443) |
| SLOC | Source Lines of Code |
| SOC | Security Operations Center |

## Appendix B: File Reference Index

All file paths are relative to the SCBE-AETHERMOORE repository root.

| File | Role in SCADA Governance Kernel |
|------|------|
| `src/harmonic/pipeline14.ts` | 14-layer pipeline -- core command evaluation engine |
| `src/harmonic/hyperbolic.ts` | Poincare ball hyperbolic distance computation |
| `src/symphonic_cipher/harmonic_scaling_law.py` | Harmonic Wall cost function H(d,R) = R^(d^2) |
| `src/crypto/pqc_liboqs.py` | Post-quantum cryptography (ML-KEM-768, ML-DSA-65) |
| `src/security-engine/context-engine.ts` | Trust scoring, decision routing, ALLOW/QUARANTINE/ESCALATE/DENY |
| `agents/antivirus_membrane.py` | Semantic antivirus -- command content analysis |
| `src/governance/decision_envelope_v1.py` | Decision envelope generation and signing |
| `proto/decision_envelope/v1/decision_envelope.proto` | Decision envelope protobuf schema |
| `schemas/decision_envelope_v1.schema.json` | Decision envelope JSON schema |
| `packages/kernel/src/pipeline14.ts` | Kernel-packaged 14-layer pipeline |
| `packages/kernel/src/hyperbolic.ts` | Kernel-packaged hyperbolic math |
| `src/geoseed/` | GeoSeed Network (M6) -- future multi-site federation substrate |
| `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/` | Five quantum axiom implementations |

## Appendix C: Key Metrics for Investor/Partner Conversations

| Metric | Value | Source |
|--------|-------|--------|
| SCADA market size (2025) | $13.95B | Grand View Research |
| SCADA market size (2035) | $31.19B | Grand View Research |
| SCADA market CAGR | 6.3% | Grand View Research |
| Industrial cybersecurity market (2025) | $25-26B | MarketsandMarkets |
| Industrial cybersecurity market (2029) | $135B | MarketsandMarkets |
| ICS CVEs disclosed (2025) | 2,155 | CISA ICS-CERT |
| ICS advisories published (2025) | 508 | CISA ICS-CERT |
| Ransomware attacks on industrial orgs (2025) | 5,967 | Dragos Year in Review |
| Claroty total funding | $882M | Crunchbase |
| Claroty potential IPO valuation | $3.5B | Reuters |
| Nozomi Networks acquirer | Mitsubishi Electric | Sep 2025 |
| Dragos total funding | $440M | Crunchbase |
| seL4 kernel size (verified) | 8,700 lines C | seL4 Foundation |
| SCBE Ring 0 target size | ~1,500 SLOC Python | Internal |
| Ring 0 latency target | <1ms p99 | Internal |
| Full stack latency target | <10ms p99 | Internal |

---

*This document is maintained in the SCBE-AETHERMOORE repository at `docs/SCADA_GOVERNANCE_KERNEL_STRATEGY.md`. Updates require review by engineering and business development leads.*
