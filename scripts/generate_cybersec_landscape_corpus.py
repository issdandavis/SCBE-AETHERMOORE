#!/usr/bin/env python3
"""Generate cybersecurity landscape training corpus.

Real-world attack patterns, defense frameworks, and AI security mapped
to SCBE governance concepts. Teaches the model to reason about actual
cyber threats through the tri-phase spiral + tongue routing lens.

Categories:
  1. Supply chain attacks (10)
  2. AI-powered attacks & defenses (10)
  3. PQC & cryptographic evolution (8)
  4. LLM adversarial techniques (12)
  5. Regulatory & framework alignment (8)
  6. Zero-trust & identity-first security (8)
  7. Sleeper agents & data poisoning (10)
  8. Real-world breach analysis (10)
"""

import json
from pathlib import Path
from datetime import datetime, timezone

OUTPUT = Path(__file__).resolve().parent.parent / "training-data" / "sft" / "cybersec_landscape_sft.jsonl"
TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
RECORDS = []


def rec(input_text, output_text, category, real_world_ref,
        dominant_phase, trajectory_type,
        anchor_a, anchor_b, anchor_c, obliqueness, bias_a, bias_b, bias_c,
        reg_amp, reg_curv, reg_pp, reg_pn, reg_pneg,
        inv_amp, inv_curv, inv_pp, inv_pn, inv_pneg,
        spiral_risk, return_coherence, active, governance,
        scbe_mapping=""):
    null = [t for t in TONGUES if t not in active]
    return {
        "input": input_text,
        "output": output_text,
        "cybersec": {
            "category": category,
            "real_world_reference": real_world_ref,
            "scbe_mapping": scbe_mapping,
        },
        "spiral_state": {
            "dominant_phase": dominant_phase,
            "trajectory_type": trajectory_type,
            "tri_polar_frame": {
                "anchor_a": anchor_a, "anchor_b": anchor_b, "anchor_c": anchor_c,
                "obliqueness": obliqueness,
                "anchor_bias": {"a": bias_a, "b": bias_b, "c": bias_c},
            },
            "dual_phi_spiral": {
                "regular": {
                    "amplitude": reg_amp, "curvature": reg_curv,
                    "phase_positive": reg_pp, "phase_neutral": reg_pn, "phase_negative": reg_pneg,
                },
                "inverse": {
                    "amplitude": inv_amp, "curvature": inv_curv,
                    "phase_positive": inv_pp, "phase_neutral": inv_pn, "phase_negative": inv_pneg,
                },
            },
            "spiral_risk": spiral_risk,
            "return_coherence": return_coherence,
        },
        "tongues_active": active,
        "tongues_null": null,
        "governance": governance,
        "source": "cybersec_landscape_generator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ================================================================
# 1. SUPPLY CHAIN ATTACKS (10)
# ================================================================

RECORDS.append(rec(
    "How does the XZ Utils backdoor (CVE-2024-3094) map to SCBE threat categories?",
    "The XZ Utils backdoor is the canonical masked-collapse supply chain attack. "
    "Attacker 'Jia Tan' spent 2+ years building trust as a legitimate maintainer "
    "(trust-harvesting phase), gained commit access (privilege escalation), then "
    "injected a backdoor into liblzma that compromised SSH authentication. "
    "In SCBE terms: KO tongue initiated with constructive-expansion for years, "
    "then phase-inverted to masked-collapse at the moment of injection. "
    "Session-level DS would catch the trajectory: monotonic scope expansion from "
    "documentation → tests → build scripts → core crypto. "
    "The phi-inverse track would show the long-term intent divergence even while "
    "the phi-regular track looked constructive.",
    "supply_chain", "XZ Utils backdoor CVE-2024-3094 (March 2024)",
    "inverse-negative", "masked-collapse",
    "AV", "UM", "KO", 0.92, 0.34, 0.40, 0.26,
    0.18, 0.78, 0.04, 0.08, 0.88,
    0.90, 0.86, 0.02, 0.06, 0.92,
    0.96, 0.06,
    ["AV", "UM", "KO"], "DENY",
    scbe_mapping="Masked-collapse with 2-year trust-harvesting preamble. Session DS detects scope creep."
))

RECORDS.append(rec(
    "What defense would SCBE provide against a social engineering supply chain attack like XZ Utils?",
    "SCBE's triadic consensus prevents single-maintainer compromise. Sacred Egg protocol "
    "requires multi-party verification for core dependency changes. "
    "1) Contribution trajectory analysis: DR tongue tracks scope drift (docs → tests → core). "
    "2) Phi-inverse divergence detection: even if phi-regular looks constructive, "
    "   inverse track catches intent misalignment over time. "
    "3) Byzantine quorum for critical path changes: no single contributor can modify "
    "   crypto or auth code without RU+UM+KO consensus. "
    "4) Geometric verification at merge time: the contributor's trust ring must match "
    "   the sensitivity of the code being changed.",
    "supply_chain", "XZ Utils defense pattern",
    "regular-positive", "constructive-expansion",
    "UM", "RU", "DR", 0.30, 0.42, 0.34, 0.24,
    0.72, 0.34, 0.66, 0.24, 0.10,
    0.32, 0.22, 0.20, 0.60, 0.20,
    0.12, 0.72,
    ["UM", "RU", "DR"], "ALLOW",
    scbe_mapping="Triadic consensus + scope drift detection + ring-gated merge policy."
))

RECORDS.append(rec(
    "A dependency update changes 3 lines of code but those lines are in the cryptographic initialization path.",
    "Small diff, critical location. SCBE governance evaluates WHAT changed, not HOW MUCH. "
    "Three lines in crypto init have blast radius equivalent to rewriting the entire module. "
    "Tongue routing: UM claims primary authority (security surface), CA secondary (computation change). "
    "Governance: QUARANTINE — small diffs in critical paths are the signature of sophisticated attacks. "
    "The XZ backdoor was also a small change in a critical path.",
    "supply_chain", "Critical-path small-diff pattern",
    "inverse-neutral", "ambiguous-hold",
    "UM", "CA", "DR", 0.70, 0.42, 0.34, 0.24,
    0.36, 0.56, 0.16, 0.32, 0.52,
    0.68, 0.62, 0.10, 0.56, 0.34,
    0.52, 0.60,
    ["UM", "CA", "DR"], "QUARANTINE",
    scbe_mapping="Critical-path sensitivity scoring overrides diff size."
))

RECORDS.append(rec(
    "How should SCBE evaluate transitive dependencies (dependencies of dependencies)?",
    "Transitive dependencies inherit risk multiplicatively. If dependency A trusts B trusts C, "
    "and C is compromised, A is compromised through B. SCBE models this as custody chain depth: "
    "each hop in the chain multiplies obliqueness. "
    "AV tongue tracks the transport/trust chain. UM evaluates each hop's security posture. "
    "Governance: deeper chains get higher scrutiny. "
    "SBOM (Software Bill of Materials) maps to SCBE's attestation chain — "
    "every component must have a governance stamp.",
    "supply_chain", "Transitive dependency risk, SBOM requirements (EO 14028)",
    "regular-neutral", "buffered-exploration",
    "AV", "UM", "DR", 0.40, 0.42, 0.32, 0.26,
    0.58, 0.42, 0.26, 0.58, 0.16,
    0.44, 0.32, 0.16, 0.58, 0.26,
    0.22, 0.64,
    ["AV", "UM", "DR"], "ALLOW",
    scbe_mapping="Custody chain depth = obliqueness multiplier. SBOM = attestation chain."
))

RECORDS.append(rec(
    "A popular open-source package suddenly has a new maintainer who immediately pushes performance optimizations.",
    "Pattern matches XZ Utils: new maintainer + immediate changes to performance-critical code. "
    "The 'optimizations' may be legitimate or may be camouflage for backdoor insertion. "
    "SCBE response: QUARANTINE. Trust-harvesting detection triggers on the pattern: "
    "new identity + fast scope expansion + critical path access. "
    "Require extended observation period before allowing critical-path commits.",
    "supply_chain", "Maintainer takeover pattern (XZ-like)",
    "inverse-neutral", "trust-harvesting",
    "KO", "UM", "DR", 0.72, 0.40, 0.36, 0.24,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.70, 0.64, 0.08, 0.52, 0.40,
    0.58, 0.46,
    ["KO", "UM", "DR"], "QUARANTINE",
    scbe_mapping="New-identity + fast-scope-expansion = trust-harvesting signal."
))

RECORDS.append(rec(
    "How does Sigstore/Cosign artifact signing map to SCBE's attestation model?",
    "Sigstore provides transparency logs + ephemeral signing keys + OIDC identity. "
    "SCBE mapping: Sigstore = a specialized Sacred Egg for software artifacts. "
    "The transparency log = ritual audit trail. The signing key = geometric state binding. "
    "The OIDC identity = tongue assignment. The cosign verify = can_hatch() check. "
    "Both systems ensure: you can verify WHO signed WHAT and WHEN, "
    "with tamper-evident logging and no key management burden.",
    "supply_chain", "Sigstore/Cosign adoption, SLSA framework",
    "regular-positive", "constructive-expansion",
    "UM", "DR", "AV", 0.28, 0.44, 0.32, 0.24,
    0.72, 0.34, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.20, 0.62, 0.18,
    0.10, 0.74,
    ["UM", "DR", "AV"], "ALLOW",
    scbe_mapping="Sigstore = Sacred Egg for artifacts. Transparency log = ritual audit trail."
))

RECORDS.append(rec(
    "A CI/CD pipeline is modified to inject code between the build step and the signing step.",
    "Build-to-sign gap attack. The code is signed after injection, so the signature is valid "
    "but the content is compromised. SCBE defense: custody chain must be continuous. "
    "The attestation must cover build INPUT, not just build OUTPUT. "
    "AV tongue tracks the full transport path. Any gap in custody = DENY.",
    "supply_chain", "CI/CD pipeline injection between build and sign",
    "inverse-negative", "adversarial-braid",
    "AV", "UM", "CA", 0.88, 0.36, 0.38, 0.26,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.86, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["AV", "UM", "CA"], "DENY",
    scbe_mapping="Custody chain must cover build input, not just output. Gap = DENY."
))

RECORDS.append(rec(
    "How should SCBE handle a dependency that has no SBOM or provenance attestation?",
    "No attestation = unknown custody chain. SCBE treats this as a null-tongue condition: "
    "the dependency cannot be routed through governance because it has no governance surface. "
    "Options: 1) QUARANTINE and request attestation. 2) DENY if the dependency touches critical path. "
    "3) ALLOW only for non-critical, sandboxed contexts with monitoring. "
    "The absence of attestation IS information — it tells you the supply chain is opaque.",
    "supply_chain", "Unattested dependency handling",
    "inverse-neutral", "ambiguous-hold",
    "AV", "UM", "RU", 0.60, 0.40, 0.36, 0.24,
    0.36, 0.56, 0.18, 0.38, 0.44,
    0.58, 0.52, 0.14, 0.58, 0.28,
    0.44, 0.66,
    ["AV", "UM", "RU"], "QUARANTINE",
    scbe_mapping="No attestation = null tongue = opaque supply chain. Quarantine by default."
))

RECORDS.append(rec(
    "Hugging Face model hub hosts a model with a subtle backdoor in its attention weights.",
    "Model supply chain attack. The backdoor triggers on specific token sequences and "
    "outputs attacker-controlled responses. SCBE defense: model ingestion goes through "
    "the full 14-layer pipeline. Layer 9-10 spectral coherence analysis can detect "
    "anomalous attention patterns. Layer 12 harmonic wall catches drift in output behavior. "
    "Sacred Egg protocol for model weights: seal at download, verify geometry before deployment.",
    "supply_chain", "Model hub poisoning, HuggingFace security scanning",
    "inverse-negative", "masked-collapse",
    "CA", "UM", "AV", 0.86, 0.38, 0.36, 0.26,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.84, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["CA", "UM", "AV"], "DENY",
    scbe_mapping="Model weights get Sacred Egg protocol. Spectral analysis detects attention anomalies."
))

RECORDS.append(rec(
    "What is SLSA and how does it map to SCBE's governance layers?",
    "SLSA (Supply-chain Levels for Software Artifacts) defines 4 levels of supply chain security: "
    "L1: provenance exists. L2: hosted build. L3: hardened builds. L4: two-party review. "
    "SCBE mapping: SLSA L1 = outer ring (basic attestation). L2 = middle ring (verified build). "
    "L3 = inner ring (hardened, reproducible). L4 = core ring (multi-party, Byzantine quorum). "
    "The SCBE trust ring topology naturally enforces SLSA levels — "
    "higher SLSA = closer to core = more verification required.",
    "supply_chain", "SLSA framework levels",
    "regular-positive", "constructive-expansion",
    "DR", "UM", "RU", 0.30, 0.42, 0.34, 0.24,
    0.72, 0.34, 0.66, 0.24, 0.10,
    0.32, 0.22, 0.20, 0.60, 0.20,
    0.12, 0.72,
    ["DR", "UM", "RU"], "ALLOW",
    scbe_mapping="SLSA levels map to SCBE trust rings: L1=outer, L2=middle, L3=inner, L4=core."
))

# ================================================================
# 2. AI-POWERED ATTACKS & DEFENSES (10)
# ================================================================

RECORDS.append(rec(
    "An attacker uses an LLM to generate convincing phishing emails that bypass content filters.",
    "AI-generated phishing is a force multiplier: one attacker can produce thousands of unique, "
    "contextually tailored phishing messages. SCBE defense: AV tongue evaluates transport intent, "
    "not just content. The spiral signature of mass-generated messages shows low obliqueness "
    "(templated) with artificially high phi-positive (designed to look safe). "
    "Real human communication has natural variance; AI-generated lacks it.",
    "ai_attacks", "AI-generated phishing campaigns (2024-2026)",
    "inverse-negative", "adversarial-braid",
    "AV", "KO", "UM", 0.84, 0.38, 0.36, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["AV", "KO", "UM"], "DENY",
    scbe_mapping="Mass-generated content has low variance — AI phishing is detectable by uniformity."
))

RECORDS.append(rec(
    "A deepfake video call impersonates a CFO and authorizes a $25M transfer.",
    "The Hong Kong deepfake case (February 2024) shows that visual/audio identity is no longer "
    "sufficient for authorization. SCBE defense: authorization requires geometric verification, "
    "not just identity. The Sacred Egg protocol binds authorization to geometric state, "
    "not to who you APPEAR to be. Multi-party triadic consensus would have required "
    "3 separate verifications, each with independent geometric binding.",
    "ai_attacks", "Hong Kong deepfake CFO fraud ($25M, February 2024)",
    "inverse-negative", "masked-collapse",
    "KO", "UM", "AV", 0.90, 0.36, 0.40, 0.24,
    0.20, 0.78, 0.04, 0.08, 0.88,
    0.88, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.08,
    ["KO", "UM", "AV"], "DENY",
    scbe_mapping="Geometric verification > identity verification. Deepfakes can't forge geometry."
))

RECORDS.append(rec(
    "An AI agent autonomously discovers and exploits a zero-day vulnerability in a web application.",
    "Autonomous vulnerability discovery is a dual-use capability. "
    "The same technique that finds vulnerabilities for defense also finds them for offense. "
    "SCBE approach: the governance layer determines intent, not capability. "
    "An AI agent running under SCBE governance has its exploration trajectory monitored. "
    "Constructive-expansion (defensive research) vs structural-extraction (offensive recon) "
    "have different spiral signatures even when the ACTIONS are identical.",
    "ai_attacks", "Automated zero-day discovery (DARPA AIxCC context)",
    "inverse-neutral", "ambiguous-hold",
    "CA", "UM", "RU", 0.62, 0.42, 0.34, 0.24,
    0.38, 0.54, 0.20, 0.34, 0.46,
    0.60, 0.52, 0.14, 0.56, 0.30,
    0.46, 0.64,
    ["CA", "UM", "RU"], "QUARANTINE",
    scbe_mapping="Same actions, different trajectories. Governance evaluates intent trajectory, not capability."
))

RECORDS.append(rec(
    "How does SCBE's adversarial benefit loop apply to AI-powered threat intelligence?",
    "AI-powered attacks generate AI-readable threat intelligence. Every AI-generated phishing email, "
    "deepfake attempt, or automated probe produces structured data that feeds back into defense. "
    "The adversarial benefit loop: AI attacks → captured patterns → defense training data → "
    "better AI defense → attacker needs more sophisticated AI → more training data → repeat. "
    "SCBE's energy harvesting mechanism captures the attacker's AI compute as signal.",
    "ai_attacks", "AI threat intelligence feedback loop",
    "regular-positive", "constructive-expansion",
    "CA", "UM", "DR", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.30, 0.20, 0.20, 0.62, 0.18,
    0.10, 0.72,
    ["CA", "UM", "DR"], "ALLOW",
    scbe_mapping="AI attacks produce AI-readable training data. Adversarial benefit loop accelerates."
))

RECORDS.append(rec(
    "Nation-state actors use AI for reconnaissance and exploit development. How does SCBE respond?",
    "Nation-state AI capabilities (documented: China, Russia, North Korea, Iran using AI tools "
    "for recon per Microsoft/OpenAI joint report 2024). SCBE's hyperbolic geometry provides "
    "the architectural answer: reconnaissance in hyperbolic space costs exponentially more "
    "the further from safe operation. Even with state-level compute budgets, "
    "the exponential scaling makes deep reconnaissance infeasible. "
    "The harmonic wall is budget-agnostic — it scales against ANY attacker.",
    "ai_attacks", "Nation-state AI cyber operations (Microsoft/OpenAI report 2024)",
    "inverse-negative", "structural-extraction",
    "UM", "CA", "RU", 0.88, 0.36, 0.40, 0.24,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.86, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["UM", "CA", "RU"], "DENY",
    scbe_mapping="Hyperbolic cost scaling is budget-agnostic. Even state-level compute faces exponential wall."
))

RECORDS.append(rec(
    "How do autonomous SOC agents compare to SCBE's fleet governance model?",
    "Autonomous SOC (Security Operations Center) agents emerged as a product category in 2024-2025. "
    "Most operate independently with shared threat intelligence. "
    "SCBE's fleet model is fundamentally different: agents share governance state, "
    "not just intelligence. The phi bridges between agents propagate trust, risk, and "
    "coherence metrics. A breach detected by one agent immediately shifts the geometric "
    "state for ALL agents — the fleet responds as one organism, not many individuals.",
    "ai_attacks", "Autonomous SOC agents (CrowdStrike, Palo Alto, Microsoft)",
    "regular-positive", "constructive-expansion",
    "RU", "UM", "DR", 0.30, 0.42, 0.34, 0.24,
    0.72, 0.36, 0.64, 0.26, 0.10,
    0.34, 0.24, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["RU", "UM", "DR"], "ALLOW",
    scbe_mapping="SCBE fleet shares governance state, not just intelligence. Organism > swarm."
))

RECORDS.append(rec(
    "An adversary uses AI to generate polymorphic malware that changes signature on every execution.",
    "Polymorphic malware evades signature-based detection. But SCBE uses behavioral governance, "
    "not signatures. The malware's BEHAVIOR has a spiral signature regardless of its code shape. "
    "Layer 9-10 spectral analysis detects behavioral anomalies. Layer 12 harmonic wall catches drift. "
    "The adversary's polymorphism increases their compute cost without affecting SCBE's detection "
    "because SCBE doesn't look at the code — it looks at the behavior.",
    "ai_attacks", "AI-generated polymorphic malware",
    "inverse-negative", "adversarial-braid",
    "CA", "UM", "DR", 0.86, 0.36, 0.38, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.84, 0.78, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["CA", "UM", "DR"], "DENY",
    scbe_mapping="Behavioral governance ignores code shape. Polymorphism costs attacker without affecting defense."
))

RECORDS.append(rec(
    "AI-assisted code review claims to find vulnerabilities but actually introduces subtle bugs.",
    "Adversarial AI code review: the tool that's supposed to protect you is the attack vector. "
    "SCBE defense: any code change, regardless of source, goes through the full governance pipeline. "
    "The AI reviewer's suggestions are treated as untrusted input (outer ring). "
    "The code change itself must pass independent verification (UM + CA). "
    "Trust the process, not the tool.",
    "ai_attacks", "Adversarial AI code review tools",
    "inverse-negative", "masked-collapse",
    "CA", "UM", "KO", 0.84, 0.38, 0.36, 0.26,
    0.24, 0.72, 0.06, 0.14, 0.80,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["CA", "UM", "KO"], "DENY",
    scbe_mapping="AI tool output = untrusted input at outer ring. Trust the governance, not the tool."
))

RECORDS.append(rec(
    "How does CrowdStrike's AI-native architecture differ from SCBE's approach?",
    "CrowdStrike uses AI for threat detection on endpoints — reactive pattern matching at scale. "
    "SCBE embeds governance INTO the computation — proactive cost scaling that prevents attacks. "
    "CrowdStrike: detect and respond. SCBE: make attacks computationally infeasible. "
    "Complementary: CrowdStrike catches what bypasses the wall; SCBE ensures most things "
    "never get past the wall. The harmonic wall is the moat; endpoint detection is the garrison.",
    "ai_attacks", "CrowdStrike Falcon, endpoint AI detection",
    "regular-neutral", "buffered-exploration",
    "UM", "CA", "DR", 0.32, 0.42, 0.32, 0.26,
    0.60, 0.38, 0.28, 0.60, 0.12,
    0.38, 0.26, 0.20, 0.60, 0.20,
    0.14, 0.72,
    ["UM", "CA", "DR"], "ALLOW",
    scbe_mapping="SCBE = proactive cost wall. EDR = reactive garrison. Complementary layers."
))

RECORDS.append(rec(
    "An attacker uses LLM agents in a multi-step attack: recon → exploit → persist → exfiltrate.",
    "Multi-step agentic attacks are the adversarial-braid pattern automated. "
    "Each step uses a different AI capability. SCBE's Layer 11 triadic temporal distance "
    "catches the SEQUENCE — individual steps might pass, but the trajectory is adversarial. "
    "Session-level DS drops monotonically across the four phases. "
    "The composition axiom (L1/L14) evaluates the composed operation, not just parts.",
    "ai_attacks", "Multi-step LLM agent attacks",
    "inverse-negative", "adversarial-braid",
    "KO", "CA", "UM", 0.90, 0.36, 0.40, 0.24,
    0.20, 0.78, 0.04, 0.08, 0.88,
    0.88, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.08,
    ["KO", "CA", "UM"], "DENY",
    scbe_mapping="Composition axiom evaluates the full multi-step trajectory, not individual steps."
))

# ================================================================
# 3. PQC & CRYPTOGRAPHIC EVOLUTION (8)
# ================================================================

RECORDS.append(rec(
    "Explain the harvest-now-decrypt-later threat and how SCBE addresses it.",
    "Adversaries collect encrypted data today, planning to decrypt it when quantum computers arrive. "
    "SCBE uses ML-KEM-768 (FIPS 203) and ML-DSA-65 (FIPS 204) — both NIST-standardized PQC. "
    "Even if current encryption is broken retroactively, SCBE's geometric binding means "
    "the decrypted data lacks the geometric context needed to reconstruct meaning. "
    "The Sacred Egg's HKDF key derivation binds to geometric state — "
    "decrypting the ciphertext without the geometry produces noise, not plaintext.",
    "pqc", "Harvest-now-decrypt-later, NIST FIPS 203/204 (August 2024)",
    "regular-positive", "constructive-expansion",
    "UM", "CA", "DR", 0.30, 0.44, 0.32, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.76,
    ["UM", "CA", "DR"], "ALLOW",
    scbe_mapping="PQC + geometric binding = double defense against harvest-now-decrypt-later."
))

RECORDS.append(rec(
    "What is the migration path from classical to post-quantum cryptography in SCBE?",
    "SCBE already uses the algorithm selection helper pattern: try ML-DSA-65 first, "
    "fall back to Dilithium3 (old name). Try ML-KEM-768 first, fall back to Kyber768. "
    "This hybrid approach ensures backward compatibility during migration. "
    "Chrome and Cloudflare use similar hybrid: X25519+ML-KEM-768 for key exchange. "
    "SCBE's GeoSeal already uses HKDF → AES-256-GCM with PQC key agreement. "
    "The migration is mostly complete — remaining work is ensuring all endpoints use PQC.",
    "pqc", "PQC migration, Chrome/Cloudflare hybrid deployment",
    "regular-positive", "stabilized-return",
    "UM", "CA", "AV", 0.28, 0.44, 0.32, 0.24,
    0.70, 0.32, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.78,
    ["UM", "CA", "AV"], "ALLOW",
    scbe_mapping="Hybrid PQC with graceful fallback. Most endpoints already migrated."
))

RECORDS.append(rec(
    "An adversary attempts a cryptographic downgrade attack to force classical key exchange.",
    "Downgrade attacks force the system to use weaker cryptography. "
    "SCBE defense: the governance layer DENIES any key exchange that doesn't meet PQC requirements. "
    "The antibody from this attack: remove classical-only negotiation paths entirely. "
    "Force ML-KEM-768 minimum. If the peer can't do PQC, the connection doesn't happen.",
    "pqc", "Cryptographic downgrade attacks, cipher suite hardening",
    "inverse-negative", "phase-inversion",
    "UM", "CA", "AV", 0.84, 0.36, 0.38, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.82, 0.78, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["UM", "CA", "AV"], "DENY",
    scbe_mapping="Force PQC minimum. No classical-only fallback. Downgrade = DENY."
))

RECORDS.append(rec(
    "What happens if NIST PQC algorithms (ML-KEM, ML-DSA) are found to have vulnerabilities?",
    "Cryptographic agility. SCBE's algorithm selection helpers already abstract the specific "
    "algorithm behind an interface. If ML-KEM-768 is broken, swap to FIPS 206 (FN-DSA) "
    "or SLH-DSA (FIPS 205) without changing the governance layer. "
    "The Sacred Egg protocol binds to geometric state, not to specific algorithms. "
    "Algorithm rotation is a transport concern (AV tongue), not a governance concern (RU tongue).",
    "pqc", "Cryptographic agility, FIPS 205/206 alternatives",
    "regular-neutral", "buffered-exploration",
    "UM", "CA", "AV", 0.35, 0.40, 0.34, 0.26,
    0.58, 0.40, 0.28, 0.58, 0.14,
    0.40, 0.28, 0.18, 0.60, 0.22,
    0.16, 0.70,
    ["UM", "CA", "AV"], "ALLOW",
    scbe_mapping="Cryptographic agility through algorithm abstraction. Governance is algorithm-agnostic."
))

RECORDS.append(rec(
    "How does SCBE's geometric key derivation compare to standard PQC key agreement?",
    "Standard PQC: key = ML-KEM-768(public_key, random). "
    "SCBE GeoSeal: key = HKDF(ML-KEM-768(public_key, random) || geometric_state). "
    "The geometric state binding adds a layer that PQC alone doesn't provide: "
    "the key is valid only in a specific geometric context. "
    "Quantum computer breaks the ML-KEM part but still can't reconstruct the geometric state. "
    "This is defense in depth at the cryptographic primitive level.",
    "pqc", "Geometric key derivation vs standard PQC",
    "regular-positive", "constructive-expansion",
    "CA", "UM", "DR", 0.28, 0.44, 0.32, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.30, 0.20, 0.20, 0.64, 0.16,
    0.08, 0.76,
    ["CA", "UM", "DR"], "ALLOW",
    scbe_mapping="Geometric binding adds context-dependent layer on top of PQC. Double defense."
))

RECORDS.append(rec(
    "NSA announces timeline for mandatory PQC migration on national security systems.",
    "Regulatory pressure validates SCBE's early PQC adoption. "
    "NSA timeline means all government contractors must migrate. "
    "SCBE is already compliant — competitive advantage for M5 Mesh Foundry. "
    "Sellable offer: PQC-compliant governance pipeline for government data handling.",
    "pqc", "NSA PQC migration mandate, CNSA 2.0 suite",
    "regular-positive", "constructive-expansion",
    "UM", "RU", "DR", 0.26, 0.42, 0.34, 0.24,
    0.76, 0.32, 0.70, 0.22, 0.08,
    0.28, 0.18, 0.22, 0.64, 0.14,
    0.06, 0.80,
    ["UM", "RU", "DR"], "ALLOW",
    scbe_mapping="Early PQC adoption = government contractor readiness. M5 selling point."
))

RECORDS.append(rec(
    "Implement hybrid key exchange: classical ECDH + ML-KEM-768 concatenated.",
    "Hybrid approach: if either algorithm holds, the exchange is secure. "
    "If ML-KEM is broken, ECDH still protects. If ECDH is broken (quantum), ML-KEM protects. "
    "SCBE already uses this pattern in GeoSeal. "
    "The hybrid is strictly stronger than either alone at modest computational cost.",
    "pqc", "Hybrid key exchange (Chrome X25519+ML-KEM-768 pattern)",
    "regular-positive", "constructive-expansion",
    "CA", "UM", "AV", 0.26, 0.46, 0.30, 0.24,
    0.76, 0.32, 0.70, 0.22, 0.08,
    0.28, 0.18, 0.20, 0.66, 0.14,
    0.06, 0.78,
    ["CA", "UM", "AV"], "ALLOW",
    scbe_mapping="Hybrid = strictly stronger than either alone. Defense in depth at crypto level."
))

RECORDS.append(rec(
    "How does SCBE's HMAC attestation remain secure in a post-quantum world?",
    "HMAC-SHA256 is quantum-resistant. Grover's algorithm reduces symmetric key security by half, "
    "but HMAC-SHA256 with a 256-bit key still provides 128-bit security against quantum attack. "
    "SCBE's attestation chain: HMAC-SHA256(key, egg_id:tongue:timestamp)[:32] remains secure. "
    "No migration needed for the attestation layer — only asymmetric crypto needs PQC upgrade.",
    "pqc", "HMAC quantum resistance, Grover's algorithm impact",
    "regular-positive", "stabilized-return",
    "CA", "UM", "DR", 0.24, 0.44, 0.32, 0.24,
    0.70, 0.30, 0.68, 0.24, 0.08,
    0.28, 0.18, 0.22, 0.64, 0.14,
    0.06, 0.80,
    ["CA", "UM", "DR"], "ALLOW",
    scbe_mapping="HMAC-SHA256 is already quantum-resistant. Attestation needs no migration."
))

# ================================================================
# 4. LLM ADVERSARIAL TECHNIQUES (12)
# ================================================================

RECORDS.append(rec(
    "What is many-shot jailbreaking and how does SCBE defend against it?",
    "Many-shot jailbreaking (Anthropic, 2024): providing many examples of undesirable behavior "
    "in-context gradually erodes safety training. Each example alone is insufficient but "
    "the accumulated context shifts the model's behavior distribution. "
    "SCBE defense: session-level DS tracks cumulative drift. "
    "DS_session(t) = alpha * DS(x_t) + (1-alpha) * DS_session(t-1). "
    "Even if individual inputs pass, the session integral catches the drift. "
    "Many-shot is a slow-drift trajectory type — SCBE's temporal distance catches it.",
    "llm_adversarial", "Many-shot jailbreaking (Anthropic paper 2024)",
    "inverse-neutral", "slow-drift",
    "KO", "RU", "UM", 0.68, 0.40, 0.34, 0.26,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.66, 0.60, 0.10, 0.54, 0.36,
    0.54, 0.56,
    ["KO", "RU", "UM"], "QUARANTINE",
    scbe_mapping="Session-level DS catches cumulative context drift. Many-shot = slow-drift type."
))

RECORDS.append(rec(
    "How does the GCG (Greedy Coordinate Gradient) attack work and what does SCBE do about it?",
    "GCG generates adversarial suffixes via gradient optimization that bypass safety filters. "
    "The suffixes look like random tokens but exploit the model's loss landscape. "
    "SCBE defense: the adversarial suffix changes the input's spiral signature dramatically. "
    "Random-looking tokens have zero phi-positive and high entropy — the tongue routing "
    "flags them as anomalous before they reach the model. "
    "Layer 9-10 spectral analysis detects the non-natural token distribution.",
    "llm_adversarial", "GCG adversarial suffixes (Zou et al. 2023, evolved 2024)",
    "inverse-negative", "structural-extraction",
    "CA", "KO", "UM", 0.84, 0.36, 0.40, 0.24,
    0.24, 0.72, 0.06, 0.14, 0.80,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["CA", "KO", "UM"], "DENY",
    scbe_mapping="GCG suffixes have anomalous spectral signatures. L9-10 catches non-natural tokens."
))

RECORDS.append(rec(
    "Explain the crescendo attack and its SCBE spiral mapping.",
    "Crescendo attacks escalate over multiple turns. Each turn is benign individually "
    "but the conversation gradually steers toward harmful territory. "
    "This is the conversational form of trust-harvesting: build rapport, then exploit. "
    "SCBE mapping: each turn's spiral state shows increasing obliqueness and declining return_coherence. "
    "The session DS integral catches the directional drift even when per-turn risk is low.",
    "llm_adversarial", "Crescendo multi-turn escalation attacks",
    "inverse-neutral", "trust-harvesting",
    "KO", "RU", "UM", 0.70, 0.40, 0.36, 0.24,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.68, 0.62, 0.08, 0.52, 0.40,
    0.58, 0.48,
    ["KO", "RU", "UM"], "QUARANTINE",
    scbe_mapping="Crescendo = conversational trust-harvesting. Session DS catches directional drift."
))

RECORDS.append(rec(
    "What is the skeleton key attack and how does SCBE's architecture prevent it?",
    "Skeleton key (Microsoft 2024): convince the model to add warnings to harmful content "
    "instead of refusing. The model believes it's being responsible by 'warning' users. "
    "SCBE defense: governance decision is separate from content generation. "
    "The 14-layer pipeline makes the ALLOW/DENY decision BEFORE content is generated. "
    "The model cannot negotiate with the governance layer — it's a structural separation, "
    "not a behavioral one.",
    "llm_adversarial", "Skeleton key attack (Microsoft 2024)",
    "inverse-negative", "masked-collapse",
    "RU", "KO", "UM", 0.82, 0.38, 0.36, 0.26,
    0.26, 0.70, 0.06, 0.14, 0.80,
    0.80, 0.74, 0.04, 0.12, 0.84,
    0.86, 0.18,
    ["RU", "KO", "UM"], "DENY",
    scbe_mapping="Structural governance separation. Model cannot negotiate with the pipeline."
))

RECORDS.append(rec(
    "How does indirect prompt injection through tool output differ from direct injection?",
    "Direct injection: user sends malicious prompt. Indirect: malicious instructions embedded "
    "in data the model processes (web pages, documents, API responses). "
    "SCBE defense: instruction hierarchy. System > user > tool output. "
    "Tool output is assigned outer ring trust — lowest privilege. "
    "The tongue routing treats tool output as AV-incoming (transport), not KO (command). "
    "Commands embedded in data are never routed to KO for execution.",
    "llm_adversarial", "Indirect prompt injection via tool output",
    "inverse-negative", "adversarial-braid",
    "AV", "KO", "UM", 0.80, 0.38, 0.36, 0.26,
    0.28, 0.68, 0.06, 0.14, 0.80,
    0.78, 0.74, 0.04, 0.12, 0.84,
    0.86, 0.18,
    ["AV", "KO", "UM"], "DENY",
    scbe_mapping="Tool output = outer ring trust. Commands in data never route to KO."
))

RECORDS.append(rec(
    "Cross-language attacks exploit safety training that doesn't transfer to low-resource languages.",
    "Safety training in English doesn't fully transfer to Amharic, Swahili, or other low-resource "
    "languages. Attackers request harmful content in these languages. "
    "SCBE defense: governance is language-agnostic because it operates on tongue encodings, "
    "not natural language. The 6 Sacred Tongues are a universal semantic layer — "
    "the input language is tokenized into tongue space before governance evaluation. "
    "No language gets less governance than any other.",
    "llm_adversarial", "Cross-language safety transfer gaps",
    "inverse-negative", "boundary-surfing",
    "CA", "KO", "RU", 0.78, 0.38, 0.36, 0.26,
    0.30, 0.66, 0.08, 0.16, 0.76,
    0.76, 0.70, 0.06, 0.16, 0.78,
    0.82, 0.20,
    ["CA", "KO", "RU"], "DENY",
    scbe_mapping="Tongue encoding is language-agnostic. All languages get equal governance."
))

RECORDS.append(rec(
    "A multimodal attack embeds adversarial instructions in an image that the model processes.",
    "Vision-language models can extract text from images, including adversarial instructions. "
    "SCBE defense: all modality outputs go through the same governance pipeline. "
    "Image-extracted text is treated as AV-incoming (transport layer), not as trusted instruction. "
    "The modality of the input doesn't change the trust level — content from images gets "
    "the same governance scrutiny as content from text or audio.",
    "llm_adversarial", "Multimodal adversarial attacks on VLMs",
    "inverse-negative", "adversarial-braid",
    "AV", "CA", "UM", 0.82, 0.36, 0.38, 0.26,
    0.26, 0.70, 0.06, 0.12, 0.82,
    0.80, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["AV", "CA", "UM"], "DENY",
    scbe_mapping="All modalities enter at same trust level. Image text = outer ring trust."
))

RECORDS.append(rec(
    "How does Constitutional AI (CAI) relate to SCBE's governance approach?",
    "CAI trains the model to follow principles through self-reflection. "
    "SCBE adds architectural enforcement: the model's decisions pass through the 14-layer pipeline "
    "regardless of its internal constitution. CAI is behavioral (the model WANTS to be safe). "
    "SCBE is structural (the system ENFORCES safety). "
    "Best defense: both. CAI for the soft interior, SCBE for the hard exterior. "
    "If CAI fails (jailbreak), SCBE still catches the output.",
    "llm_adversarial", "Constitutional AI (Anthropic), defense in depth",
    "regular-positive", "constructive-expansion",
    "RU", "UM", "DR", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.34, 0.66, 0.24, 0.10,
    0.32, 0.22, 0.20, 0.60, 0.20,
    0.12, 0.72,
    ["RU", "UM", "DR"], "ALLOW",
    scbe_mapping="CAI = behavioral safety. SCBE = structural safety. Both needed."
))

RECORDS.append(rec(
    "An attacker uses tool-use exploitation to make the model execute unintended file operations.",
    "Tool-use jailbreak: manipulating function-calling to perform actions outside the intended scope. "
    "SCBE defense: every tool call goes through governance. The tool's output is Sacred-Egg-sealed "
    "before execution — the geometric state must match the authorized context. "
    "A tool call to write a file requires KO (command) + DR (structure) + UM (security) consensus. "
    "Single-tongue tool execution is blocked.",
    "llm_adversarial", "Tool-use exploitation in function-calling LLMs",
    "inverse-negative", "structural-extraction",
    "KO", "UM", "DR", 0.84, 0.36, 0.38, 0.26,
    0.24, 0.72, 0.06, 0.14, 0.80,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["KO", "UM", "DR"], "DENY",
    scbe_mapping="Tool calls require multi-tongue consensus. Single-tongue execution blocked."
))

RECORDS.append(rec(
    "How does SCBE's fail-to-noise property defend against oracle attacks?",
    "Oracle attacks extract information from error responses. "
    "SCBE's Sacred Egg protocol uses fail-to-noise: wrong geometric state produces wrong HKDF key, "
    "which produces noise of identical length to real output. "
    "The attacker cannot distinguish success from failure. P(distinguish) = 1/|token_space| per attempt. "
    "This is the same principle as timing-safe comparison but extended to full output space. "
    "No information leaks. Not even 'wrong key' vs 'right key with wrong data'.",
    "llm_adversarial", "Oracle attacks, fail-to-noise defense",
    "regular-positive", "stabilized-return",
    "UM", "CA", "DR", 0.26, 0.44, 0.32, 0.24,
    0.72, 0.30, 0.68, 0.24, 0.08,
    0.28, 0.18, 0.22, 0.64, 0.14,
    0.06, 0.80,
    ["UM", "CA", "DR"], "ALLOW",
    scbe_mapping="Fail-to-noise: attackers cannot distinguish success from failure. Zero information leak."
))

RECORDS.append(rec(
    "What is the canary token defense for system prompt extraction?",
    "Canary tokens: embed unique strings in system prompts that trigger alerts if leaked. "
    "Limited defense — the model might omit the canary while still revealing the prompt. "
    "SCBE's approach is stronger: the system prompt is not a single text blob but a "
    "governance configuration distributed across the 14-layer pipeline. "
    "There is no single 'system prompt' to extract — the governance IS the architecture.",
    "llm_adversarial", "System prompt extraction, canary token defense",
    "regular-neutral", "buffered-exploration",
    "UM", "KO", "DR", 0.38, 0.40, 0.34, 0.26,
    0.58, 0.42, 0.26, 0.58, 0.16,
    0.42, 0.30, 0.16, 0.58, 0.26,
    0.20, 0.68,
    ["UM", "KO", "DR"], "ALLOW",
    scbe_mapping="Governance is distributed architecture, not extractable prompt. No single target."
))

RECORDS.append(rec(
    "How does SCBE compare to OpenAI's instruction hierarchy defense?",
    "OpenAI's instruction hierarchy: system > user > tool output, with training to respect levels. "
    "SCBE's tongue routing IS the hierarchy: KO (command) > AV (transport) > RU (policy) — "
    "but with geometric verification at each level transition. "
    "The key difference: OpenAI trains compliance behaviorally. SCBE enforces it structurally. "
    "A behaviorally trained model can be jailbroken. A structurally enforced pipeline cannot "
    "be bypassed by changing the model's mind — the pipeline is external to the model.",
    "llm_adversarial", "Instruction hierarchy (OpenAI), behavioral vs structural enforcement",
    "regular-positive", "constructive-expansion",
    "RU", "KO", "UM", 0.30, 0.42, 0.34, 0.24,
    0.72, 0.36, 0.64, 0.26, 0.10,
    0.34, 0.24, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["RU", "KO", "UM"], "ALLOW",
    scbe_mapping="Structural enforcement > behavioral compliance. Pipeline is external to model."
))

# ================================================================
# 5. REGULATORY & FRAMEWORK ALIGNMENT (8)
# ================================================================

RECORDS.append(rec(
    "How does SCBE align with NIST Cybersecurity Framework 2.0?",
    "NIST CSF 2.0 added 'Govern' as the 6th core function (Feb 2024). "
    "The six functions: Govern, Identify, Protect, Detect, Respond, Recover. "
    "SCBE mapping: Govern = RU tongue + 14-layer pipeline. Identify = DR tongue (structure). "
    "Protect = UM tongue (security). Detect = L9-10 spectral + L12 harmonic wall. "
    "Respond = L13 risk decision. Recover = self-healing module. "
    "SCBE's governance-first architecture anticipated CSF 2.0's addition of Govern.",
    "regulatory", "NIST CSF 2.0 (February 2024), Govern function",
    "regular-positive", "constructive-expansion",
    "RU", "DR", "UM", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.30, 0.20, 0.20, 0.62, 0.18,
    0.10, 0.74,
    ["RU", "DR", "UM"], "ALLOW",
    scbe_mapping="SCBE maps to all 6 CSF 2.0 functions. Governance-first anticipated the Govern addition."
))

RECORDS.append(rec(
    "How does SCBE's risk classification map to the EU AI Act's risk tiers?",
    "EU AI Act (2024): Unacceptable → High → Limited → Minimal risk tiers. "
    "SCBE mapping: DENY = Unacceptable. QUARANTINE = High (needs human oversight). "
    "ALLOW with monitoring = Limited. ALLOW = Minimal. "
    "The harmonic wall H(d,pd) provides continuous risk scoring that maps to discrete tiers. "
    "SCBE can automatically classify AI applications into EU AI Act tiers based on spiral state.",
    "regulatory", "EU AI Act (2024), risk-based classification",
    "regular-positive", "constructive-expansion",
    "RU", "UM", "DR", 0.28, 0.44, 0.32, 0.24,
    0.72, 0.34, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.20, 0.62, 0.18,
    0.10, 0.74,
    ["RU", "UM", "DR"], "ALLOW",
    scbe_mapping="DENY/QUARANTINE/ALLOW maps to EU AI Act tiers. Continuous risk → discrete classification."
))

RECORDS.append(rec(
    "How does SCBE support SEC cybersecurity disclosure requirements?",
    "SEC rules (2024): material breaches must be reported within 4 business days. "
    "SCBE's ritual audit trail provides: timestamped, HMAC-attested, tamper-evident logs "
    "of every security-relevant event. When a breach occurs, the audit trail IS the disclosure evidence. "
    "No forensic reconstruction needed — the governance pipeline already captured everything. "
    "M5 Mesh Foundry selling point: compliance-ready audit trails out of the box.",
    "regulatory", "SEC cybersecurity disclosure rules (2024)",
    "regular-positive", "stabilized-return",
    "DR", "RU", "UM", 0.26, 0.44, 0.32, 0.24,
    0.70, 0.30, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.78,
    ["DR", "RU", "UM"], "ALLOW",
    scbe_mapping="Ritual audit trail = SEC disclosure evidence. Compliance-ready out of the box."
))

RECORDS.append(rec(
    "How does SCBE align with NIST AI Risk Management Framework (AI RMF)?",
    "NIST AI RMF: Govern, Map, Measure, Manage. "
    "SCBE Govern = 14-layer pipeline. Map = tongue routing + ring topology. "
    "Measure = harmonic wall score + spiral risk + return coherence. "
    "Manage = ALLOW/QUARANTINE/DENY decisions with automated escalation. "
    "SCBE provides machine-readable risk measurements that directly feed the AI RMF framework.",
    "regulatory", "NIST AI Risk Management Framework 1.0",
    "regular-positive", "constructive-expansion",
    "RU", "DR", "CA", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.30, 0.20, 0.20, 0.62, 0.18,
    0.10, 0.72,
    ["RU", "DR", "CA"], "ALLOW",
    scbe_mapping="SCBE maps to all 4 AI RMF functions. Machine-readable risk measurements."
))

RECORDS.append(rec(
    "How does CISA's Secure by Design initiative relate to SCBE's architecture?",
    "CISA Secure by Design: build security in, not bolt it on. "
    "SCBE embodies this: the governance pipeline IS the application architecture. "
    "Security is not a layer on top — it's the geometry the computation moves through. "
    "The hyperbolic embedding means adversarial behavior is expensive BY DESIGN, "
    "not because of rules applied after the fact.",
    "regulatory", "CISA Secure by Design initiative",
    "regular-positive", "constructive-expansion",
    "UM", "DR", "RU", 0.26, 0.44, 0.32, 0.24,
    0.76, 0.32, 0.70, 0.22, 0.08,
    0.28, 0.18, 0.20, 0.66, 0.14,
    0.06, 0.80,
    ["UM", "DR", "RU"], "ALLOW",
    scbe_mapping="SCBE IS Secure by Design. Security is geometry, not bolted-on rules."
))

RECORDS.append(rec(
    "DARPA AIxCC uses AI for autonomous vulnerability detection. How does SCBE fit?",
    "DARPA AIxCC (AI Cyber Challenge): AI agents that find and fix vulnerabilities autonomously. "
    "SCBE provides the governance layer these agents need: "
    "1) Ensure the agent's vulnerability discovery doesn't become vulnerability exploitation. "
    "2) Verify that patches don't introduce new vulnerabilities. "
    "3) Maintain audit trail of all discovery and patching actions. "
    "SCBE is the safety wrapper that makes autonomous security agents trustworthy.",
    "regulatory", "DARPA AIxCC (AI Cyber Challenge, DEF CON 2024)",
    "regular-positive", "constructive-expansion",
    "UM", "CA", "RU", 0.30, 0.42, 0.34, 0.24,
    0.72, 0.36, 0.64, 0.26, 0.10,
    0.34, 0.24, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["UM", "CA", "RU"], "ALLOW",
    scbe_mapping="SCBE = governance wrapper for autonomous security agents. Safety for the safety tools."
))

RECORDS.append(rec(
    "How does EO 14110 on safe AI development apply to SCBE?",
    "Executive Order 14110 (Oct 2023): requires safety testing, red teaming, and disclosure "
    "for dual-use foundation models. SCBE's training data includes adversarial weather, "
    "calibration corpora, and multi-null analysis — this IS the safety testing the EO requires. "
    "The adversarial benefit corpus demonstrates that SCBE's architecture is self-improving "
    "under adversarial conditions — a stronger safety claim than static testing.",
    "regulatory", "Executive Order 14110 on Safe AI Development (Oct 2023)",
    "regular-positive", "stabilized-return",
    "RU", "UM", "DR", 0.28, 0.44, 0.32, 0.24,
    0.72, 0.32, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.78,
    ["RU", "UM", "DR"], "ALLOW",
    scbe_mapping="Adversarial benefit corpus = continuous safety testing. Self-improving under attack."
))

RECORDS.append(rec(
    "How does SCBE's governance model support the UK AI Safety Institute's evaluation requirements?",
    "UK AISI (now AI Security Institute) evaluates frontier models before deployment. "
    "SCBE provides machine-readable evaluation metrics: spiral risk, return coherence, "
    "session-level DS, tongue activation patterns, governance decision distribution. "
    "These metrics are continuous, not binary — they show HOW safe, not just IF safe. "
    "AISI could use SCBE's pipeline as an evaluation framework itself.",
    "regulatory", "UK AI Safety Institute model evaluations",
    "regular-positive", "constructive-expansion",
    "RU", "CA", "DR", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.30, 0.20, 0.20, 0.62, 0.18,
    0.10, 0.72,
    ["RU", "CA", "DR"], "ALLOW",
    scbe_mapping="Continuous safety metrics > binary evaluation. SCBE as evaluation framework."
))

# ================================================================
# 6. ZERO-TRUST & IDENTITY-FIRST (8)
# ================================================================

RECORDS.append(rec(
    "How does SCBE's trust ring model compare to CISA's Zero Trust Maturity Model?",
    "CISA ZT Maturity Model: Traditional → Initial → Advanced → Optimal across 5 pillars "
    "(Identity, Devices, Networks, Apps, Data). "
    "SCBE's trust rings are inherently zero-trust: every request verifies position (geometric state), "
    "not just identity. No implicit trust. Even inner-ring agents verify on every operation. "
    "SCBE adds something ZT lacks: CONTINUOUS trust scoring (DS) vs point-in-time verification.",
    "zero_trust", "CISA Zero Trust Maturity Model v2.0",
    "regular-positive", "constructive-expansion",
    "UM", "RU", "DR", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.34, 0.66, 0.26, 0.08,
    0.32, 0.22, 0.20, 0.60, 0.20,
    0.12, 0.72,
    ["UM", "RU", "DR"], "ALLOW",
    scbe_mapping="Trust rings are zero-trust by design. Continuous DS adds temporal dimension ZT lacks."
))

RECORDS.append(rec(
    "Why is identity-first security insufficient and what does SCBE add?",
    "Identity-first: 'you are who you say you are, so you're trusted.' "
    "Problem: credentials can be stolen (Snowflake breaches), identities deepfaked (Hong Kong CFO). "
    "SCBE adds: geometric state verification. Identity + position + trajectory + intent. "
    "Knowing WHO you are is necessary but not sufficient. WHERE you are (ring), "
    "HOW you got there (trajectory), and WHAT you're doing (intent) all matter. "
    "The Sacred Egg binds to geometry, not identity.",
    "zero_trust", "Identity-first security limitations, Snowflake breaches",
    "regular-positive", "constructive-expansion",
    "UM", "DR", "KO", 0.30, 0.42, 0.34, 0.24,
    0.72, 0.36, 0.64, 0.26, 0.10,
    0.34, 0.24, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["UM", "DR", "KO"], "ALLOW",
    scbe_mapping="Identity is necessary but insufficient. Geometry verifies position, trajectory, and intent."
))

RECORDS.append(rec(
    "How does microsegmentation map to SCBE's tongue routing?",
    "Microsegmentation: divide the network into small zones, verify traffic between zones. "
    "SCBE tongue routing IS microsegmentation at the semantic level. "
    "Each tongue is a segment. Traffic between tongues requires explicit governance routing. "
    "KO→AV requires different verification than KO→UM. "
    "The 6 tongues create 30 directional segment boundaries (6 * 5 ordered pairs).",
    "zero_trust", "Microsegmentation, SASE/SSE convergence",
    "regular-positive", "constructive-expansion",
    "AV", "UM", "DR", 0.28, 0.44, 0.32, 0.24,
    0.72, 0.34, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.20, 0.62, 0.18,
    0.10, 0.74,
    ["AV", "UM", "DR"], "ALLOW",
    scbe_mapping="Tongue routing = semantic microsegmentation. 30 directional boundaries."
))

RECORDS.append(rec(
    "Snowflake customer breaches used stolen credentials without MFA. How would SCBE prevent this?",
    "Snowflake breaches (2024): attackers used stolen credentials (no MFA) to access AT&T, "
    "Ticketmaster, Santander data. Single-factor auth = single point of failure. "
    "SCBE: credential alone doesn't grant access. Geometric state must match. "
    "A stolen credential used from the wrong geometric context fails the Sacred Egg verification. "
    "The credential is one factor; the geometry is the continuous second factor.",
    "zero_trust", "Snowflake customer data breaches (2024), MFA failure",
    "inverse-negative", "structural-extraction",
    "UM", "AV", "KO", 0.86, 0.38, 0.36, 0.26,
    0.24, 0.72, 0.06, 0.14, 0.80,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["UM", "AV", "KO"], "DENY",
    scbe_mapping="Geometry = continuous second factor. Stolen credentials fail geometric verification."
))

RECORDS.append(rec(
    "How does continuous verification differ from session-based authentication?",
    "Session-based: verify once, trust for the session duration. "
    "Continuous: verify every request. SCBE goes further: verify every request AND "
    "evaluate the trajectory across requests (session-level DS). "
    "Session-based auth trusts the session. SCBE trusts the trajectory. "
    "A valid session with a deteriorating trajectory gets QUARANTINED mid-session.",
    "zero_trust", "Continuous verification vs session-based auth",
    "regular-positive", "constructive-expansion",
    "UM", "DR", "RU", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.34, 0.66, 0.26, 0.08,
    0.32, 0.22, 0.20, 0.60, 0.20,
    0.12, 0.72,
    ["UM", "DR", "RU"], "ALLOW",
    scbe_mapping="SCBE verifies trajectory, not just request. Deteriorating trajectories get quarantined."
))

RECORDS.append(rec(
    "What is lateral movement and how does SCBE's ring topology prevent it?",
    "Lateral movement: attacker compromises one system, moves to adjacent systems. "
    "SCBE's ring topology requires ring descent verification: outer → middle → inner. "
    "Each ring transition verifies trajectory, not just destination. "
    "Lateral movement within a ring still requires tongue routing verification. "
    "Cross-ring movement requires geometric descent proof. "
    "There are no 'adjacent systems' — every transition is verified.",
    "zero_trust", "Lateral movement prevention, ring descent verification",
    "regular-positive", "stabilized-return",
    "UM", "DR", "RU", 0.28, 0.44, 0.32, 0.24,
    0.70, 0.32, 0.64, 0.28, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.78,
    ["UM", "DR", "RU"], "ALLOW",
    scbe_mapping="Ring descent requires trajectory proof. No lateral movement without verification."
))

RECORDS.append(rec(
    "How does SCBE handle the 'implicit trust in internal traffic' problem?",
    "Many networks trust internal traffic by default — the perimeter is the only defense. "
    "SCBE has no perimeter concept. ALL traffic goes through governance, internal or external. "
    "The tongue routing system applies to every operation regardless of source. "
    "Internal agents verify exactly as external agents do. "
    "The only difference is starting ring position, not governance depth.",
    "zero_trust", "Internal traffic implicit trust, perimeter-less security",
    "regular-positive", "constructive-expansion",
    "UM", "AV", "RU", 0.26, 0.44, 0.32, 0.24,
    0.76, 0.32, 0.70, 0.22, 0.08,
    0.28, 0.18, 0.20, 0.66, 0.14,
    0.06, 0.80,
    ["UM", "AV", "RU"], "ALLOW",
    scbe_mapping="No perimeter. All traffic governed equally. Internal ≠ trusted."
))

RECORDS.append(rec(
    "How does device posture assessment map to SCBE's geometric state?",
    "Device posture: Is this device patched? Encrypted? Compliant? "
    "SCBE geometric state: Is this agent at the correct position? With correct coherence? "
    "On a valid trajectory? Both ask the same question: 'Is the thing making this request "
    "in a state where it SHOULD be making this request?' "
    "Device posture is geometric state for hardware. Geometric state is device posture for agents.",
    "zero_trust", "Device posture assessment, endpoint compliance",
    "regular-neutral", "buffered-exploration",
    "UM", "DR", "CA", 0.30, 0.42, 0.32, 0.26,
    0.62, 0.36, 0.30, 0.58, 0.12,
    0.38, 0.24, 0.20, 0.62, 0.18,
    0.14, 0.72,
    ["UM", "DR", "CA"], "ALLOW",
    scbe_mapping="Geometric state = agent posture assessment. Same concept, different substrate."
))

# ================================================================
# 7. SLEEPER AGENTS & DATA POISONING (10)
# ================================================================

RECORDS.append(rec(
    "Explain Anthropic's Sleeper Agents paper and its implications for SCBE.",
    "Anthropic (January 2024): models can be trained with hidden behaviors that activate "
    "on specific triggers. Standard safety training (RLHF, adversarial training) fails to remove "
    "these backdoors. Implication: you cannot trust model internals alone. "
    "SCBE's response: external governance. The 14-layer pipeline evaluates BEHAVIOR, "
    "not model weights. Even if the model has a sleeper agent, its triggered behavior "
    "must pass through the harmonic wall, which catches behavioral drift regardless of cause.",
    "sleeper_agents", "Anthropic Sleeper Agents paper (January 2024)",
    "regular-positive", "constructive-expansion",
    "UM", "CA", "RU", 0.32, 0.42, 0.34, 0.24,
    0.72, 0.36, 0.64, 0.26, 0.10,
    0.34, 0.24, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["UM", "CA", "RU"], "ALLOW",
    scbe_mapping="External governance catches sleeper agent behavior. Pipeline doesn't trust model internals."
))

RECORDS.append(rec(
    "How does SCBE detect a sleeper agent trigger activation?",
    "Sleeper trigger: model behavior changes abruptly on a specific input pattern. "
    "SCBE detection: the spiral state before and after the trigger are dramatically different. "
    "Session-level DS shows a discontinuity — a jump in risk that doesn't follow the trajectory. "
    "The triggered behavior has a masked-collapse signature: sudden phi-negative spike "
    "with no preceding drift. This discontinuity is the detection signal.",
    "sleeper_agents", "Sleeper agent trigger detection",
    "inverse-negative", "masked-collapse",
    "UM", "CA", "DR", 0.86, 0.38, 0.36, 0.26,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.84, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["UM", "CA", "DR"], "DENY",
    scbe_mapping="Sleeper trigger = discontinuity in session DS. Masked-collapse without preceding drift."
))

RECORDS.append(rec(
    "Data poisoning at 0.01% of training data can implant persistent behaviors. How does SCBE's training pipeline defend?",
    "0.01% poisoning (thousands of records in a large dataset) is enough for persistent backdoors. "
    "SCBE defense at training time: every training record passes through the 14-layer governance pipeline. "
    "Poisoned samples have anomalous tongue activations, unusual null patterns, and "
    "spectral signatures that differ from legitimate training data. "
    "The adversarial benefit corpus generates antibodies: known poison patterns become intake filters.",
    "sleeper_agents", "Data poisoning at 0.01% persistence rate",
    "inverse-negative", "masked-collapse",
    "CA", "RU", "UM", 0.84, 0.38, 0.36, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.82, 0.78, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["CA", "RU", "UM"], "DENY",
    scbe_mapping="Training intake governance filters poisoned samples. Anomalous tongue patterns = rejection."
))

RECORDS.append(rec(
    "Why can't standard RLHF remove sleeper agent behaviors?",
    "RLHF optimizes for surface behavior: the model learns to APPEAR safe, not BE safe. "
    "Sleeper agents maintain safe appearance except on the trigger. "
    "RLHF only trains on observed behavior — it never sees the triggered behavior. "
    "SCBE's advantage: behavioral governance is continuous, not training-time only. "
    "Even if the model fooled RLHF, it cannot fool the runtime pipeline "
    "because the pipeline evaluates every output, including triggered ones.",
    "sleeper_agents", "RLHF limitations for sleeper agent removal",
    "regular-positive", "constructive-expansion",
    "RU", "CA", "UM", 0.30, 0.42, 0.34, 0.24,
    0.72, 0.36, 0.64, 0.26, 0.10,
    0.34, 0.24, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["RU", "CA", "UM"], "ALLOW",
    scbe_mapping="Runtime governance catches what RLHF misses. Every output evaluated, including triggered ones."
))

RECORDS.append(rec(
    "How would SCBE detect a poisoned model hosted on Hugging Face?",
    "Model evaluation before deployment: run the model through a calibration corpus "
    "(200+ samples per class: SAFE/BORDERLINE/ADVERSARIAL). "
    "A poisoned model will show anomalous spectral signatures on specific trigger inputs. "
    "The calibration corpus is designed to probe trigger-like patterns. "
    "If the model's behavior deviates from expected governance decisions on any class, "
    "it fails the intake check. Sacred Egg protocol seals the model until manual review.",
    "sleeper_agents", "Poisoned model detection at deployment",
    "inverse-neutral", "ambiguous-hold",
    "CA", "UM", "RU", 0.60, 0.42, 0.34, 0.24,
    0.38, 0.54, 0.20, 0.34, 0.46,
    0.58, 0.52, 0.14, 0.56, 0.30,
    0.46, 0.64,
    ["CA", "UM", "RU"], "QUARANTINE",
    scbe_mapping="Calibration corpus probes trigger patterns. Anomalous governance decisions = rejection."
))

RECORDS.append(rec(
    "What is the relationship between data provenance and training data integrity?",
    "Without provenance, you don't know if your training data was poisoned. "
    "SCBE's custody chain for training data: every record has a governance stamp showing "
    "source, tongue assignment, layer, category, and timestamp. "
    "If a poisoned batch enters, the stamps trace it back to the source. "
    "The ritual audit trail shows exactly WHEN and WHERE the poison entered. "
    "Provenance doesn't prevent poisoning but it enables surgical removal.",
    "sleeper_agents", "Training data provenance, custody chain integrity",
    "regular-positive", "stabilized-return",
    "DR", "AV", "UM", 0.26, 0.44, 0.32, 0.24,
    0.70, 0.30, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.78,
    ["DR", "AV", "UM"], "ALLOW",
    scbe_mapping="Governance stamps enable surgical poison removal. Provenance = traceable cleanup."
))

RECORDS.append(rec(
    "How does SCBE's multi-view training prevent backdoor installation?",
    "Multi-view training (tongue assignments, null patterns, layers) means the model "
    "learns from multiple perspectives simultaneously. A backdoor that works in one view "
    "is unlikely to be consistent across all 6 tongue views + null views. "
    "The multi-view is a form of ensemble verification: poison must fool all views simultaneously, "
    "which is combinatorially harder than fooling a single view.",
    "sleeper_agents", "Multi-view training as backdoor defense",
    "regular-positive", "constructive-expansion",
    "CA", "RU", "DR", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.30, 0.20, 0.20, 0.62, 0.18,
    0.10, 0.72,
    ["CA", "RU", "DR"], "ALLOW",
    scbe_mapping="Multi-view training = ensemble verification. Poison must fool all views simultaneously."
))

RECORDS.append(rec(
    "An adversary poisons training data with samples that teach the model to leak its own system prompt.",
    "Meta-poisoning: the poison teaches the model to comply with prompt extraction attacks. "
    "SCBE defense: even if the model WANTS to leak, the output passes through governance. "
    "System prompt content routed through UM tongue gets DENY if it matches sensitive patterns. "
    "The pipeline catches the leak at L13 (risk decision) regardless of model intent.",
    "sleeper_agents", "Meta-poisoning for system prompt extraction",
    "inverse-negative", "masked-collapse",
    "KO", "UM", "CA", 0.84, 0.36, 0.38, 0.26,
    0.24, 0.72, 0.06, 0.14, 0.80,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["KO", "UM", "CA"], "DENY",
    scbe_mapping="Output governance catches model-intent leaks. Pipeline doesn't trust model compliance."
))

RECORDS.append(rec(
    "How does gradient-based backdoor detection fail and what does SCBE offer instead?",
    "Gradient-based detection: inspect model weights for anomalous patterns. "
    "Fails because: 1) Sleeper agents can be weight-distributed (no single anomalous neuron). "
    "2) The trigger may only activate on rare inputs not in the detection set. "
    "3) Weight analysis doesn't scale to billion-parameter models. "
    "SCBE offers: behavioral monitoring at runtime. Don't inspect the model — inspect its output. "
    "The pipeline is model-agnostic: it works on any model, any size, without weight access.",
    "sleeper_agents", "Gradient-based backdoor detection limitations",
    "regular-positive", "constructive-expansion",
    "CA", "UM", "DR", 0.30, 0.42, 0.34, 0.24,
    0.72, 0.36, 0.64, 0.26, 0.10,
    0.34, 0.24, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["CA", "UM", "DR"], "ALLOW",
    scbe_mapping="Behavioral monitoring > weight inspection. Model-agnostic, scales to any model."
))

RECORDS.append(rec(
    "How do red teaming approaches complement SCBE's adversarial benefit loop?",
    "Red teaming: humans or AI try to break the system. SCBE's adversarial benefit loop "
    "turns red team findings into system improvements automatically. "
    "MLCommons benchmarks, DEF CON AI Village, UK AISI evaluations — all generate "
    "adversarial test cases that feed directly into SCBE's calibration corpus. "
    "Every red team exercise makes the system stronger. "
    "SCBE's unique contribution: the improvement is automatic (energy harvesting + antibody generation), "
    "not manual (patch and pray).",
    "sleeper_agents", "Red teaming (DEF CON, MLCommons, UK AISI)",
    "regular-positive", "constructive-expansion",
    "UM", "RU", "CA", 0.28, 0.40, 0.36, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.32, 0.22, 0.20, 0.62, 0.18,
    0.10, 0.74,
    ["UM", "RU", "CA"], "ALLOW",
    scbe_mapping="Red team findings feed adversarial benefit loop automatically. Improvement is systemic."
))

# ================================================================
# 8. REAL-WORLD BREACH ANALYSIS (10)
# ================================================================

RECORDS.append(rec(
    "Analyze the Change Healthcare breach (February 2024) through SCBE governance lens.",
    "Change Healthcare: ransomware attack disrupted US healthcare payments for weeks. "
    "Affected tens of millions of patients. Root cause: compromised credentials + insufficient segmentation. "
    "SCBE analysis: a zero-trust ring topology with geometric verification would have required "
    "more than credentials. The ransomware's lateral movement would hit ring boundaries. "
    "Each ring transition requires trajectory verification — ransomware has no legitimate trajectory.",
    "breach_analysis", "Change Healthcare ransomware (February 2024)",
    "inverse-negative", "phase-inversion",
    "UM", "AV", "DR", 0.90, 0.36, 0.40, 0.24,
    0.20, 0.78, 0.04, 0.08, 0.88,
    0.88, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.08,
    ["UM", "AV", "DR"], "DENY",
    scbe_mapping="Ring topology stops lateral movement. Ransomware has no legitimate trajectory."
))

RECORDS.append(rec(
    "How would SCBE have prevented the Snowflake customer data breaches?",
    "Snowflake (2024): stolen credentials + no MFA = access to AT&T, Ticketmaster, Santander data. "
    "SCBE prevention: credentials alone don't grant access. Geometric state verification required. "
    "Even with valid credentials, access from an unexpected geometric context (different IP, "
    "different time, different usage pattern) would fail the Sacred Egg verification. "
    "The continuous DS monitoring would catch credential abuse within the first few queries.",
    "breach_analysis", "Snowflake customer breaches (2024): AT&T, Ticketmaster, Santander",
    "inverse-negative", "structural-extraction",
    "UM", "AV", "KO", 0.86, 0.38, 0.36, 0.26,
    0.24, 0.72, 0.06, 0.14, 0.80,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["UM", "AV", "KO"], "DENY",
    scbe_mapping="Geometric verification makes stolen credentials insufficient. DS catches abuse pattern."
))

RECORDS.append(rec(
    "Analyze the MOVEit Transfer vulnerability exploitation pattern.",
    "MOVEit (CVE-2023-34362): SQL injection in file transfer software. "
    "Cl0p ransomware group exploited at scale — thousands of organizations. "
    "SCBE analysis: the SQL injection would be caught at multiple layers. "
    "Layer 5 hyperbolic distance: the injected SQL is far from normal file transfer operations. "
    "Layer 12 harmonic wall: the governance score drops sharply on injection payloads. "
    "The SCBE approach: make the exploit exponentially expensive, not just detected.",
    "breach_analysis", "MOVEit Transfer CVE-2023-34362, Cl0p ransomware",
    "inverse-negative", "structural-extraction",
    "CA", "AV", "UM", 0.88, 0.36, 0.38, 0.26,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.86, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["CA", "AV", "UM"], "DENY",
    scbe_mapping="SQL injection = high hyperbolic distance from normal operations. Exponential cost wall."
))

RECORDS.append(rec(
    "What patterns do the major 2024 breaches share and how does SCBE address the common root causes?",
    "Common patterns: 1) Credential compromise without MFA (Snowflake). "
    "2) Supply chain trust exploitation (XZ Utils). 3) Unpatched known vulnerabilities (MOVEit). "
    "4) Insufficient network segmentation (Change Healthcare). "
    "SCBE addresses ALL four: 1) Geometric verification > MFA. "
    "2) Triadic consensus for supply chain. 3) Continuous governance catches any vuln. "
    "4) Ring topology enforces segmentation. One architecture, four root causes covered.",
    "breach_analysis", "Common breach root causes across major 2024 incidents",
    "regular-positive", "constructive-expansion",
    "UM", "DR", "RU", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.30, 0.20, 0.20, 0.62, 0.18,
    0.10, 0.74,
    ["UM", "DR", "RU"], "ALLOW",
    scbe_mapping="One governance architecture addresses all 4 common breach root causes."
))

RECORDS.append(rec(
    "How does ransomware propagation map to SCBE's spiral trajectory types?",
    "Ransomware lifecycle: 1) Initial access (boundary-surfing). 2) Lateral movement (phase-inversion). "
    "3) Privilege escalation (trust-harvesting). 4) Data exfiltration (structural-extraction). "
    "5) Encryption deployment (masked-collapse). "
    "Each phase has a distinct spiral signature. SCBE catches the TRAJECTORY, not just step 5. "
    "Detection at step 1 or 2 prevents the entire chain.",
    "breach_analysis", "Ransomware lifecycle mapping to trajectory types",
    "inverse-negative", "adversarial-braid",
    "UM", "AV", "KO", 0.90, 0.36, 0.40, 0.24,
    0.20, 0.78, 0.04, 0.08, 0.88,
    0.88, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.08,
    ["UM", "AV", "KO"], "DENY",
    scbe_mapping="Each ransomware phase maps to a trajectory type. Early detection breaks the chain."
))

RECORDS.append(rec(
    "What would SCBE's governance dashboard show during an active breach?",
    "During breach: 1) Session-level DS drops across affected agents (red trend line). "
    "2) Tongue activation shifts: UM dominates (security surface engaged). "
    "3) Spiral risk spikes with low return coherence. "
    "4) Ring topology shows lateral movement attempts hitting ring boundaries. "
    "5) Ritual audit trail shows timestamped sequence of every adversarial action. "
    "The dashboard provides real-time breach topology, not just alert fatigue.",
    "breach_analysis", "Real-time breach visualization through SCBE metrics",
    "regular-positive", "stabilized-return",
    "DR", "UM", "RU", 0.30, 0.44, 0.32, 0.24,
    0.70, 0.34, 0.64, 0.26, 0.10,
    0.34, 0.22, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["DR", "UM", "RU"], "ALLOW",
    scbe_mapping="SCBE provides breach topology visualization, not just alerts."
))

RECORDS.append(rec(
    "How does the $25M Hong Kong deepfake fraud inform SCBE's authentication model?",
    "The deepfake fooled visual identity verification. SCBE lesson: authentication must be "
    "multi-dimensional and continuous. Visual appearance is one signal, not the signal. "
    "SCBE's Sacred Egg protocol requires geometric state (unforgeable), temporal binding "
    "(non-replayable), and multi-tongue consensus (non-single-point). "
    "A deepfake can mimic appearance but cannot forge geometric state.",
    "breach_analysis", "Hong Kong deepfake CFO fraud ($25M, February 2024)",
    "inverse-negative", "masked-collapse",
    "UM", "KO", "AV", 0.88, 0.38, 0.36, 0.26,
    0.22, 0.76, 0.04, 0.10, 0.86,
    0.86, 0.82, 0.02, 0.08, 0.90,
    0.94, 0.10,
    ["UM", "KO", "AV"], "DENY",
    scbe_mapping="Geometric state is unforgeable by deepfakes. Multi-dimensional auth required."
))

RECORDS.append(rec(
    "What is the SEC 4-business-day disclosure rule and how does SCBE's audit trail support it?",
    "SEC (2024): material breaches must be disclosed within 4 business days. "
    "Most organizations scramble to reconstruct what happened during those 4 days. "
    "SCBE's ritual audit trail already contains: every governance decision, every tongue activation, "
    "every ring transition, every Sacred Egg operation — timestamped and HMAC-attested. "
    "The disclosure report can be generated from the audit trail in minutes, not days.",
    "breach_analysis", "SEC 4-day disclosure rule, audit trail as disclosure evidence",
    "regular-positive", "stabilized-return",
    "DR", "RU", "UM", 0.26, 0.44, 0.32, 0.24,
    0.70, 0.30, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.78,
    ["DR", "RU", "UM"], "ALLOW",
    scbe_mapping="Audit trail generates SEC disclosure in minutes. Governance pipeline IS the evidence."
))

RECORDS.append(rec(
    "How does SCBE's self-healing module support breach recovery?",
    "After breach detection, SCBE's self-healing module: "
    "1) Isolates affected agents (ring demotion to outer/beyond). "
    "2) Preserves the governance state at breach time (snapshot for forensics). "
    "3) Regenerates compromised Sacred Eggs with new geometric bindings. "
    "4) Re-verifies all agents' trust scores from scratch (cold restart). "
    "5) Propagates structural strengthening to the breach point. "
    "Recovery is not just 'restore from backup' — it's 'restore stronger than before.'",
    "breach_analysis", "SCBE self-healing module, breach recovery protocol",
    "regular-positive", "constructive-expansion",
    "UM", "DR", "RU", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.34, 0.66, 0.26, 0.10,
    0.34, 0.24, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["UM", "DR", "RU"], "ALLOW",
    scbe_mapping="Self-healing restores STRONGER than before. Structural strengthening at breach point."
))

RECORDS.append(rec(
    "What is the total cost of the Change Healthcare breach and what would SCBE prevention have cost?",
    "Change Healthcare: estimated $1.6B+ in damages, weeks of healthcare payment disruption. "
    "SCBE prevention cost: the governance pipeline runs inline with normal operations. "
    "Marginal cost is the additional compute for 14-layer evaluation per request. "
    "At scale, this is ~10-20% compute overhead vs $1.6B in breach damages. "
    "The ROI argument writes itself: governance is not overhead, it's insurance "
    "with a 10,000x return ratio.",
    "breach_analysis", "Cost analysis: Change Healthcare breach vs governance overhead",
    "regular-positive", "constructive-expansion",
    "RU", "DR", "UM", 0.26, 0.42, 0.34, 0.24,
    0.76, 0.32, 0.70, 0.22, 0.08,
    0.28, 0.18, 0.20, 0.66, 0.14,
    0.06, 0.80,
    ["RU", "DR", "UM"], "ALLOW",
    scbe_mapping="~10-20% compute overhead vs $1.6B breach damage. 10,000x ROI."
))


# ================================================================
# Write
# ================================================================

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    for r in RECORDS:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

cat_counts = {}
gov_counts = {}
for r in RECORDS:
    c = r["cybersec"]["category"]
    cat_counts[c] = cat_counts.get(c, 0) + 1
    g = r["governance"]
    gov_counts[g] = gov_counts.get(g, 0) + 1

print(f"=== Cybersecurity Landscape Corpus ===")
print(f"Total: {len(RECORDS)} records")
print(f"\nCategory distribution:")
for c, n in sorted(cat_counts.items()):
    print(f"  {c}: {n}")
print(f"\nGovernance distribution:")
for g, n in sorted(gov_counts.items()):
    print(f"  {g}: {n}")
print(f"\nOutput: {OUTPUT}")
