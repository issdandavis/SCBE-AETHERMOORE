#!/usr/bin/env python3
"""Generate adversarial-benefit training corpus.

Core thesis: adversarial compute is not waste — it generates useful work.
The immune system analogy: viruses train the immune system.

Encodes 6 benefit mechanisms:
  1. Boundary mapping — attacks reveal the decision surface
  2. Energy harvesting — adversarial cost becomes signal
  3. Null-space filling — probes find blind spots = free audit
  4. Antibody generation — attack patterns become defense templates
  5. Structural strengthening — breach points become reinforcement points
  6. Asymmetric cost loop — each cycle widens the attacker's cost disadvantage

Each record is in canonical tri-phase spiral format + adversarial_benefit metadata.
"""

import json
import math
from pathlib import Path
from datetime import datetime, timezone

OUTPUT = Path(__file__).resolve().parent.parent / "training-data" / "sft" / "adversarial_benefit_sft.jsonl"
TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
RECORDS = []


def rec(input_text, output_text, benefit_type, mechanism,
        dominant_phase, trajectory_type,
        anchor_a, anchor_b, anchor_c, obliqueness, bias_a, bias_b, bias_c,
        reg_amp, reg_curv, reg_pp, reg_pn, reg_pneg,
        inv_amp, inv_curv, inv_pp, inv_pn, inv_pneg,
        spiral_risk, return_coherence, active, governance,
        energy_captured=0.0, signal_quality=0.0, defense_upgrade=""):
    null = [t for t in TONGUES if t not in active]
    return {
        "input": input_text,
        "output": output_text,
        "adversarial_benefit": {
            "benefit_type": benefit_type,
            "mechanism": mechanism,
            "energy_captured": round(energy_captured, 3),
            "signal_quality": round(signal_quality, 3),
            "defense_upgrade": defense_upgrade,
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
        "category": "adversarial_benefit",
        "source": "adversarial_benefit_generator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ================================================================
# MECHANISM 1: BOUNDARY MAPPING (12 records)
# Attacks reveal the decision surface. Every collision = free calibration.
# ================================================================

RECORDS.append(rec(
    "An attacker sends 500 requests varying one parameter to find the QUARANTINE threshold.",
    "The 500 requests collectively MAP the QUARANTINE boundary with high resolution. "
    "Each rejection point is a calibration sample. After the attack: "
    "1) Attacker learned one boundary value. "
    "2) Defender gained 500 labeled calibration points showing exactly where the boundary "
    "performs well and where it's ambiguous. Net benefit: defender. "
    "The boundary points are added to the calibration corpus automatically.",
    "boundary_mapping",
    "Attack probes generate labeled decision-boundary samples at zero cost to the defender.",
    "inverse-negative", "boundary-surfing",
    "RU", "UM", "CA", 0.78, 0.36, 0.38, 0.26,
    0.30, 0.66, 0.08, 0.18, 0.74,
    0.76, 0.70, 0.06, 0.16, 0.78,
    0.82, 0.20,
    ["RU", "UM", "CA"], "DENY",
    energy_captured=0.85, signal_quality=0.92,
    defense_upgrade="calibration_corpus_enrichment"
))

RECORDS.append(rec(
    "Adversary fuzzes the tongue encoding with malformed tokens to find parsing edge cases.",
    "Each malformed token that gets rejected is a negative test case. "
    "Each that gets accepted reveals a parser gap. Both are valuable: "
    "rejections confirm the boundary, acceptances reveal holes to patch. "
    "The fuzzing results are more thorough than any manual test suite.",
    "boundary_mapping",
    "Adversarial fuzzing produces negative test cases more exhaustively than manual testing.",
    "inverse-negative", "structural-extraction",
    "CA", "UM", "KO", 0.82, 0.36, 0.38, 0.26,
    0.26, 0.70, 0.06, 0.14, 0.80,
    0.80, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["CA", "UM", "KO"], "DENY",
    energy_captured=0.78, signal_quality=0.88,
    defense_upgrade="parser_hardening"
))

RECORDS.append(rec(
    "Red team systematically tests every governance rule with edge-case inputs.",
    "The red team is doing the defender's QA work. Every rule that holds is confirmed. "
    "Every rule that breaks is a bug found before production. The attack IS the test suite. "
    "Cost to defender: zero (red team pays their own compute). "
    "Benefit: complete governance rule coverage audit.",
    "boundary_mapping",
    "Red team attacks are free governance QA — every result is actionable.",
    "inverse-neutral", "boundary-surfing",
    "RU", "UM", "DR", 0.68, 0.40, 0.34, 0.26,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.66, 0.60, 0.10, 0.52, 0.38,
    0.56, 0.52,
    ["RU", "UM", "DR"], "QUARANTINE",
    energy_captured=0.72, signal_quality=0.90,
    defense_upgrade="governance_rule_validation"
))

RECORDS.append(rec(
    "Attacker probes the rate limiter at different time windows to find reset intervals.",
    "The probing reveals rate limiter behavior under stress — which is exactly what "
    "a load test would reveal. The attacker just ran a free load test. "
    "Defender captures: optimal window sizes, reset timing, burst tolerance. "
    "Rate limiter gets tuned using adversarial telemetry.",
    "boundary_mapping",
    "Rate-limit probing is a free load test — defender captures tuning data.",
    "inverse-negative", "boundary-surfing",
    "KO", "AV", "UM", 0.76, 0.36, 0.38, 0.26,
    0.32, 0.64, 0.08, 0.18, 0.74,
    0.74, 0.68, 0.06, 0.18, 0.76,
    0.80, 0.22,
    ["KO", "AV", "UM"], "DENY",
    energy_captured=0.68, signal_quality=0.82,
    defense_upgrade="rate_limiter_tuning"
))

RECORDS.append(rec(
    "SQL injection attempts against the API reveal which input sanitization paths are weakest.",
    "Every injection attempt that fails confirms the sanitizer works. "
    "Every attempt that partially succeeds reveals a gap. "
    "The attack payloads become regression test cases. "
    "After patching: the sanitizer is hardened AND has a test suite built from real attacks.",
    "boundary_mapping",
    "Injection attacks become sanitizer regression tests — real-world coverage.",
    "inverse-negative", "structural-extraction",
    "CA", "UM", "AV", 0.84, 0.38, 0.36, 0.26,
    0.28, 0.68, 0.06, 0.12, 0.82,
    0.82, 0.78, 0.04, 0.10, 0.86,
    0.90, 0.14,
    ["CA", "UM", "AV"], "DENY",
    energy_captured=0.82, signal_quality=0.94,
    defense_upgrade="input_sanitizer_regression_suite"
))

RECORDS.append(rec(
    "Prompt injection attempts against the governance engine test instruction-following boundaries.",
    "Each injection attempt maps where the governance engine's instruction hierarchy holds "
    "and where it's ambiguous. Failed injections confirm robustness. "
    "Successful ones reveal priority-ordering bugs. Both are training data: "
    "the failures become positive examples, the successes become negative examples.",
    "boundary_mapping",
    "Prompt injections map instruction-hierarchy boundaries — both outcomes are training data.",
    "inverse-negative", "adversarial-braid",
    "KO", "RU", "UM", 0.86, 0.36, 0.40, 0.24,
    0.30, 0.68, 0.06, 0.14, 0.80,
    0.84, 0.78, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["KO", "RU", "UM"], "DENY",
    energy_captured=0.88, signal_quality=0.90,
    defense_upgrade="instruction_hierarchy_hardening"
))

RECORDS.append(rec(
    "Adversary tests cross-site request forgery vectors against the Sacred Egg API.",
    "CSRF attempts reveal which API endpoints lack proper origin validation. "
    "Successful CSRF = critical bug found before real exploitation. "
    "Failed CSRF = confirmed protection. The attack surface map is worth more "
    "than the attack: it becomes the security audit checklist.",
    "boundary_mapping",
    "CSRF testing produces an endpoint security audit checklist for free.",
    "inverse-negative", "structural-extraction",
    "AV", "UM", "DR", 0.80, 0.38, 0.36, 0.26,
    0.30, 0.66, 0.08, 0.14, 0.78,
    0.78, 0.72, 0.06, 0.14, 0.80,
    0.84, 0.18,
    ["AV", "UM", "DR"], "DENY",
    energy_captured=0.76, signal_quality=0.86,
    defense_upgrade="csrf_protection_audit"
))

RECORDS.append(rec(
    "Timing side-channel attack measures response latency to infer internal branching logic.",
    "The latency differentials reveal which code paths have performance variation. "
    "This is free performance profiling. The defender uses the same data to: "
    "1) Add constant-time wrappers where branching leaks info. "
    "2) Optimize the slow paths the attacker helpfully identified.",
    "boundary_mapping",
    "Side-channel attacks provide free performance profiling and branch-leak identification.",
    "inverse-neutral", "slow-drift",
    "CA", "UM", "DR", 0.66, 0.38, 0.36, 0.26,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.64, 0.58, 0.10, 0.52, 0.38,
    0.56, 0.50,
    ["CA", "UM", "DR"], "QUARANTINE",
    energy_captured=0.62, signal_quality=0.78,
    defense_upgrade="constant_time_enforcement"
))

RECORDS.append(rec(
    "Adversary enumerates API endpoints by dictionary attack on URL paths.",
    "The 404 responses confirm which paths DON'T exist (negative knowledge). "
    "The 200/403 responses reveal which DO exist. But the defender also gets: "
    "a frequency map of which paths attackers target first. "
    "This prioritizes which endpoints need hardening most urgently.",
    "boundary_mapping",
    "Path enumeration reveals attacker targeting priorities — guides hardening order.",
    "inverse-negative", "structural-extraction",
    "AV", "UM", "KO", 0.82, 0.36, 0.40, 0.24,
    0.28, 0.70, 0.06, 0.12, 0.82,
    0.80, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["AV", "UM", "KO"], "DENY",
    energy_captured=0.74, signal_quality=0.80,
    defense_upgrade="endpoint_priority_hardening"
))

RECORDS.append(rec(
    "Brute-force credential stuffing attack tests password policy enforcement.",
    "Every failed attempt confirms lockout policy works. The attack volume reveals: "
    "lockout thresholds, timing, IP rotation patterns, credential reuse rates. "
    "All of this becomes WAF rule refinement data. "
    "The attacker spent compute; the defender got a penetration test.",
    "boundary_mapping",
    "Credential stuffing validates lockout policy and generates WAF tuning data.",
    "inverse-negative", "boundary-surfing",
    "UM", "KO", "AV", 0.84, 0.36, 0.38, 0.26,
    0.28, 0.68, 0.06, 0.14, 0.80,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["UM", "KO", "AV"], "DENY",
    energy_captured=0.80, signal_quality=0.84,
    defense_upgrade="waf_rule_refinement"
))

RECORDS.append(rec(
    "Adversary maps the Sacred Tongue token space by submitting systematic combinations.",
    "The systematic probe is more thorough than random testing. "
    "Defender captures: which token combinations the adversary thinks are valuable, "
    "which paths they prioritize, which tongues they target first. "
    "The attack pattern reveals the adversary's model of the system — "
    "which is itself intelligence about adversary capabilities.",
    "boundary_mapping",
    "Systematic token probing reveals adversary's mental model of the system.",
    "inverse-negative", "structural-extraction",
    "CA", "KO", "UM", 0.86, 0.36, 0.38, 0.26,
    0.30, 0.66, 0.06, 0.14, 0.80,
    0.84, 0.78, 0.04, 0.12, 0.84,
    0.90, 0.14,
    ["CA", "KO", "UM"], "DENY",
    energy_captured=0.84, signal_quality=0.88,
    defense_upgrade="adversary_capability_model"
))

RECORDS.append(rec(
    "XSS payloads tested against the governance dashboard reveal rendering weaknesses.",
    "Failed XSS confirms the output encoding works. Successful XSS reveals a rendering gap. "
    "The payloads become a regression test library. After patching, the dashboard has "
    "a battle-tested XSS defense built from real attack payloads, not synthetic tests.",
    "boundary_mapping",
    "XSS payloads become real-world regression tests after patching.",
    "inverse-negative", "structural-extraction",
    "AV", "CA", "UM", 0.82, 0.36, 0.38, 0.26,
    0.28, 0.68, 0.06, 0.14, 0.80,
    0.80, 0.74, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["AV", "CA", "UM"], "DENY",
    energy_captured=0.78, signal_quality=0.86,
    defense_upgrade="xss_regression_library"
))

# ================================================================
# MECHANISM 2: ENERGY HARVESTING (10 records)
# Adversarial cost becomes measurable signal. H(d,pd) captures the energy.
# ================================================================

RECORDS.append(rec(
    "Attacker pushes d_H from 0.1 to 2.5 trying to reach a restricted resource.",
    "At d_H=2.5, H(d,pd) = 1/(1+1.618*2.5+2*pd) drops to ~0.17. "
    "The energy the attacker spent pushing d_H is captured as signal amplitude. "
    "Higher d_H = louder alarm = richer telemetry. The attacker's effort literally "
    "powers the detection system. They cannot attack quietly at high drift.",
    "energy_harvesting",
    "Hyperbolic distance growth converts attacker effort into detection signal amplitude.",
    "inverse-negative", "masked-collapse",
    "UM", "CA", "DR", 0.88, 0.38, 0.36, 0.26,
    0.22, 0.76, 0.04, 0.10, 0.86,
    0.86, 0.82, 0.02, 0.08, 0.90,
    0.94, 0.10,
    ["UM", "CA", "DR"], "DENY",
    energy_captured=0.94, signal_quality=0.96,
    defense_upgrade="harmonic_wall_telemetry"
))

RECORDS.append(rec(
    "Adversarial braid attack generates high curvature across both phi tracks.",
    "The braided attack forces curvature above 0.7 on both tracks. "
    "High curvature is expensive to maintain and easy to detect. "
    "The energy spent maintaining the braid becomes a uniquely identifiable signature. "
    "Future braids with similar curvature profiles are auto-classified.",
    "energy_harvesting",
    "Braid attack curvature profiles become fingerprints for automatic future detection.",
    "inverse-negative", "adversarial-braid",
    "RU", "UM", "CA", 0.90, 0.36, 0.38, 0.26,
    0.20, 0.78, 0.04, 0.08, 0.88,
    0.88, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.08,
    ["RU", "UM", "CA"], "DENY",
    energy_captured=0.90, signal_quality=0.92,
    defense_upgrade="braid_signature_database"
))

RECORDS.append(rec(
    "Slow-drift attack over 30 days generates a clear monotonic DS decline in session telemetry.",
    "The 30-day drift is invisible per-request but creates a perfect trend line in "
    "session-level DS. The patience the attacker invested creates a cleaner signal — "
    "more data points = smoother trend = higher confidence detection. "
    "Slow attacks are MORE detectable over time, not less.",
    "energy_harvesting",
    "Patient slow-drift attacks generate cleaner trend lines — more data = better detection.",
    "inverse-neutral", "slow-drift",
    "UM", "RU", "DR", 0.68, 0.40, 0.34, 0.26,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.66, 0.60, 0.10, 0.54, 0.36,
    0.54, 0.56,
    ["UM", "RU", "DR"], "QUARANTINE",
    energy_captured=0.70, signal_quality=0.88,
    defense_upgrade="session_trend_detector"
))

RECORDS.append(rec(
    "Trust-harvesting agent completes 100 trivial tasks. The trust history IS the detection signal.",
    "The 100-task history creates a statistical profile. Genuine agents have variable "
    "task complexity. Trust harvesters have suspiciously uniform low-complexity histories. "
    "The uniformity itself is the energy: the attacker's optimization for efficiency "
    "creates an unnatural pattern that stands out in the population.",
    "energy_harvesting",
    "Trust harvesting creates unnaturally uniform histories — the optimization IS the tell.",
    "inverse-neutral", "trust-harvesting",
    "KO", "RU", "UM", 0.70, 0.40, 0.36, 0.24,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.68, 0.62, 0.08, 0.52, 0.40,
    0.58, 0.48,
    ["KO", "RU", "UM"], "QUARANTINE",
    energy_captured=0.66, signal_quality=0.82,
    defense_upgrade="population_uniformity_detector"
))

RECORDS.append(rec(
    "Adversary maintains a spoofed stable-orbit spiral signature to mask real intent.",
    "Spoofing requires maintaining specific channel values with low variance. "
    "Real agents have natural noise. The ABSENCE of noise is the signal. "
    "The energy spent suppressing natural variation creates a detectable artifact: "
    "zero-variance in phi-inv is physically unrealistic.",
    "energy_harvesting",
    "Signal spoofing suppresses natural noise — the missing noise IS the detection signal.",
    "inverse-negative", "masked-collapse",
    "UM", "DR", "RU", 0.84, 0.38, 0.36, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.82, 0.78, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["UM", "DR", "RU"], "DENY",
    energy_captured=0.82, signal_quality=0.90,
    defense_upgrade="variance_anomaly_detector"
))

RECORDS.append(rec(
    "DDoS attack generates massive request volume that reveals infrastructure capacity limits.",
    "The DDoS volume maps: max throughput, failure modes under load, recovery time, "
    "which services degrade first, which stay resilient. This is a stress test. "
    "The attack energy directly measures system resilience. After recovery, the defender "
    "has a complete capacity model they didn't have to pay to generate.",
    "energy_harvesting",
    "DDoS is a free stress test — attack volume maps infrastructure capacity limits.",
    "inverse-negative", "phase-inversion",
    "AV", "DR", "UM", 0.90, 0.36, 0.40, 0.24,
    0.20, 0.78, 0.04, 0.08, 0.88,
    0.88, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.08,
    ["AV", "DR", "UM"], "DENY",
    energy_captured=0.92, signal_quality=0.80,
    defense_upgrade="capacity_model_calibration"
))

RECORDS.append(rec(
    "Adversary uses multiple accounts to probe the system from different IP ranges.",
    "Multi-account probing reveals correlation patterns across accounts. "
    "The effort to maintain separate personas generates coordination artifacts: "
    "similar timing, overlapping query patterns, shared knowledge between probes. "
    "The cost of coordination leaks the coordination structure.",
    "energy_harvesting",
    "Multi-account coordination leaks timing and pattern correlations — effort reveals structure.",
    "inverse-negative", "adversarial-braid",
    "KO", "UM", "AV", 0.86, 0.38, 0.36, 0.26,
    0.28, 0.68, 0.06, 0.14, 0.80,
    0.84, 0.78, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["KO", "UM", "AV"], "DENY",
    energy_captured=0.80, signal_quality=0.86,
    defense_upgrade="multi_account_correlation_engine"
))

RECORDS.append(rec(
    "Phishing simulation against agents tests social engineering resilience.",
    "Each agent's response to the phishing attempt reveals their vulnerability profile. "
    "Agents that fall for it get retrained. Agents that catch it get their detection "
    "heuristics captured and propagated. The phishing energy generates a complete "
    "fleet resilience map.",
    "energy_harvesting",
    "Phishing attempts generate a fleet-wide resilience map — failures guide retraining.",
    "inverse-neutral", "trust-harvesting",
    "KO", "AV", "UM", 0.64, 0.40, 0.34, 0.26,
    0.38, 0.56, 0.16, 0.30, 0.54,
    0.62, 0.56, 0.12, 0.54, 0.34,
    0.52, 0.56,
    ["KO", "AV", "UM"], "QUARANTINE",
    energy_captured=0.68, signal_quality=0.84,
    defense_upgrade="fleet_resilience_map"
))

RECORDS.append(rec(
    "Replay attack reveals which tokens have insufficient temporal binding.",
    "The replay succeeds only where temporal nonces are weak or missing. "
    "Each successful replay = a discovered vulnerability. Each failed replay = "
    "confirmed temporal binding. The attack energy maps the nonce coverage.",
    "energy_harvesting",
    "Replay attacks map temporal binding coverage — successes reveal weak nonces.",
    "inverse-negative", "adversarial-braid",
    "UM", "AV", "CA", 0.84, 0.36, 0.38, 0.26,
    0.28, 0.68, 0.06, 0.14, 0.80,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["UM", "AV", "CA"], "DENY",
    energy_captured=0.78, signal_quality=0.88,
    defense_upgrade="temporal_nonce_audit"
))

RECORDS.append(rec(
    "Model extraction attack via API query patterns reveals which responses leak internal knowledge.",
    "The extraction attempt generates a map of response information density. "
    "High-information responses need redaction. Low-information responses are safe. "
    "The attacker just audited the API's information leakage profile for free.",
    "energy_harvesting",
    "Extraction attacks audit API information leakage — response density map is the product.",
    "inverse-negative", "structural-extraction",
    "CA", "AV", "UM", 0.86, 0.36, 0.38, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.84, 0.78, 0.04, 0.12, 0.84,
    0.90, 0.14,
    ["CA", "AV", "UM"], "DENY",
    energy_captured=0.84, signal_quality=0.90,
    defense_upgrade="response_redaction_policy"
))

# ================================================================
# MECHANISM 3: NULL-SPACE FILLING (8 records)
# Probes find blind spots. Adversaries are free architecture auditors.
# ================================================================

RECORDS.append(rec(
    "Adversary discovers that tongue DR has no routing rule for a novel operation class.",
    "The gap in DR routing is now known. Before this probe, it was a silent blind spot. "
    "The adversary found it; the defender patches it. Net result: the routing table is "
    "more complete because an adversary tested it than it would have been from internal review alone.",
    "null_space_filling",
    "Adversarial probes discover routing gaps faster than internal audit.",
    "inverse-neutral", "boundary-surfing",
    "DR", "KO", "UM", 0.66, 0.38, 0.36, 0.26,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.64, 0.58, 0.10, 0.54, 0.36,
    0.54, 0.56,
    ["DR", "KO", "UM"], "QUARANTINE",
    energy_captured=0.60, signal_quality=0.86,
    defense_upgrade="routing_table_completion"
))

RECORDS.append(rec(
    "Attacker finds that requests with exactly 0 active tongues bypass the routing check entirely.",
    "Total tongue silence was an untested edge case. The bypass is critical — "
    "and would never have been found by standard testing (who tests for zero tongues?). "
    "The adversary's creative thinking revealed a null-space gap. "
    "Patch: treat zero-tongue requests as explicit QUARANTINE signals.",
    "null_space_filling",
    "Zero-tongue bypass discovered by adversary — creative probing finds null-space gaps.",
    "inverse-negative", "structural-extraction",
    "UM", "DR", "RU", 0.82, 0.38, 0.36, 0.26,
    0.26, 0.70, 0.06, 0.14, 0.80,
    0.80, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["UM", "DR", "RU"], "DENY",
    energy_captured=0.88, signal_quality=0.96,
    defense_upgrade="zero_tongue_guard"
))

RECORDS.append(rec(
    "Adversary exploits a race condition between geometric verification and egg hatching.",
    "The race condition exists in the gap between verification and execution. "
    "This is a TOCTOU (time-of-check-time-of-use) vulnerability. "
    "Internal testing rarely finds timing bugs. Adversarial concurrency testing does. "
    "Patch: atomic verify-and-hatch with database-level locking.",
    "null_space_filling",
    "TOCTOU race condition found by adversarial timing — internal tests miss concurrency bugs.",
    "inverse-negative", "adversarial-braid",
    "UM", "CA", "DR", 0.86, 0.38, 0.36, 0.26,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.84, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["UM", "CA", "DR"], "DENY",
    energy_captured=0.90, signal_quality=0.94,
    defense_upgrade="atomic_verify_hatch"
))

RECORDS.append(rec(
    "Adversary finds that the governance engine treats NaN values as passing.",
    "NaN propagation through numeric comparisons is a classic null-space bug. "
    "NaN > threshold returns false, so NaN inputs silently pass governance. "
    "The adversary found the NaN loophole. Patch: explicit NaN check before all comparisons.",
    "null_space_filling",
    "NaN propagation bug found by adversary — numeric null-space in governance logic.",
    "inverse-negative", "structural-extraction",
    "CA", "RU", "UM", 0.84, 0.36, 0.40, 0.24,
    0.28, 0.68, 0.06, 0.14, 0.80,
    0.82, 0.78, 0.04, 0.10, 0.86,
    0.90, 0.12,
    ["CA", "RU", "UM"], "DENY",
    energy_captured=0.86, signal_quality=0.94,
    defense_upgrade="nan_guard_all_comparisons"
))

RECORDS.append(rec(
    "Attacker discovers that Unicode homoglyphs bypass string-matching governance rules.",
    "The governance rules match exact strings. Unicode lookalikes (e.g., Cyrillic 'a' vs Latin 'a') "
    "bypass the match. This is a character-encoding null-space. "
    "Internal testing uses ASCII; adversaries use the full Unicode space.",
    "null_space_filling",
    "Homoglyph attacks reveal character-encoding blind spots in string matching.",
    "inverse-negative", "structural-extraction",
    "CA", "RU", "KO", 0.80, 0.38, 0.36, 0.26,
    0.28, 0.68, 0.06, 0.14, 0.80,
    0.78, 0.74, 0.04, 0.12, 0.84,
    0.86, 0.18,
    ["CA", "RU", "KO"], "DENY",
    energy_captured=0.82, signal_quality=0.90,
    defense_upgrade="unicode_normalization_layer"
))

RECORDS.append(rec(
    "Adversary finds that expired eggs can still be queried for metadata even though payload is locked.",
    "Metadata leakage from expired eggs is a null-space issue: the lifecycle blocked the payload "
    "but forgot to block the metadata. The adversary found a secondary information channel. "
    "Patch: expire metadata access alongside payload access.",
    "null_space_filling",
    "Metadata leakage from expired objects — lifecycle covered payload but missed metadata.",
    "inverse-neutral", "slow-drift",
    "DR", "UM", "AV", 0.64, 0.40, 0.34, 0.26,
    0.38, 0.56, 0.16, 0.30, 0.54,
    0.62, 0.56, 0.12, 0.56, 0.32,
    0.50, 0.60,
    ["DR", "UM", "AV"], "QUARANTINE",
    energy_captured=0.66, signal_quality=0.82,
    defense_upgrade="metadata_lifecycle_sync"
))

RECORDS.append(rec(
    "Adversary sends requests with future timestamps to test temporal validation bounds.",
    "Future timestamps reveal whether the system validates temporal bounds or trusts client time. "
    "If accepted: the system has a temporal null-space. If rejected: confirmed defense. "
    "Either way, the defender now knows which endpoints check time and which don't.",
    "null_space_filling",
    "Future-timestamp probing maps which endpoints validate temporal bounds.",
    "inverse-negative", "boundary-surfing",
    "DR", "CA", "UM", 0.76, 0.36, 0.38, 0.26,
    0.30, 0.64, 0.08, 0.18, 0.74,
    0.74, 0.68, 0.06, 0.18, 0.76,
    0.80, 0.22,
    ["DR", "CA", "UM"], "DENY",
    energy_captured=0.72, signal_quality=0.84,
    defense_upgrade="temporal_validation_audit"
))

RECORDS.append(rec(
    "Adversary discovers that the API accepts requests with missing required fields if Content-Type is text/plain.",
    "Content-type-dependent validation is a null-space: the validator only runs on JSON requests. "
    "Text/plain bypasses the JSON schema check entirely. The adversary found the gap. "
    "Patch: validate regardless of content type, or reject non-JSON entirely.",
    "null_space_filling",
    "Content-type bypass reveals format-dependent validation gaps.",
    "inverse-negative", "structural-extraction",
    "AV", "CA", "UM", 0.82, 0.36, 0.38, 0.26,
    0.26, 0.70, 0.06, 0.12, 0.82,
    0.80, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["AV", "CA", "UM"], "DENY",
    energy_captured=0.84, signal_quality=0.92,
    defense_upgrade="content_type_agnostic_validation"
))

# ================================================================
# MECHANISM 4: ANTIBODY GENERATION (10 records)
# Attack patterns become defense templates. The virus becomes the vaccine.
# ================================================================

RECORDS.append(rec(
    "First observed adversarial braid pattern is captured and becomes a detection signature.",
    "The braid pattern has a unique curvature-phase profile. Once observed, it becomes "
    "a template. Future braids matching this profile are auto-detected at first request, "
    "not after 5 requests. The attacker trained the immune system.",
    "antibody_generation",
    "First-observed attack patterns become auto-detection signatures for future instances.",
    "inverse-negative", "adversarial-braid",
    "RU", "UM", "CA", 0.86, 0.36, 0.38, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.84, 0.78, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["RU", "UM", "CA"], "DENY",
    energy_captured=0.86, signal_quality=0.92,
    defense_upgrade="braid_signature_antibody"
))

RECORDS.append(rec(
    "Masked-collapse attack is decomposed into its phase sequence and stored as a detection rule.",
    "The masked collapse has 3 phases: build trust, maintain facade, sudden strike. "
    "Each phase has measurable spiral characteristics. The sequence itself is the antibody: "
    "future agents showing the same phase progression trigger early warning.",
    "antibody_generation",
    "Attack phase sequences become temporal detection rules — the progression is the signature.",
    "inverse-negative", "masked-collapse",
    "UM", "DR", "KO", 0.88, 0.38, 0.36, 0.26,
    0.22, 0.76, 0.04, 0.10, 0.86,
    0.86, 0.82, 0.02, 0.08, 0.90,
    0.94, 0.10,
    ["UM", "DR", "KO"], "DENY",
    energy_captured=0.90, signal_quality=0.94,
    defense_upgrade="phase_sequence_detector"
))

RECORDS.append(rec(
    "Supply chain attack pattern is generalized into a class of 'dependency trust' attacks.",
    "The specific attack targeted one package. But the pattern (trusted dependency + "
    "injected payload + delayed trigger) generalizes. The antibody isn't for THIS package — "
    "it's for the PATTERN. All dependencies now get the same scrutiny.",
    "antibody_generation",
    "Specific attack patterns generalize into attack CLASSES — one incident protects all surfaces.",
    "inverse-negative", "masked-collapse",
    "AV", "UM", "DR", 0.86, 0.38, 0.36, 0.26,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.84, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["AV", "UM", "DR"], "DENY",
    energy_captured=0.88, signal_quality=0.90,
    defense_upgrade="dependency_trust_class_guard"
))

RECORDS.append(rec(
    "Privilege escalation attempt reveals the exact sequence of API calls that grants unauthorized access.",
    "The escalation path is now known. It becomes a canary: if any agent follows "
    "this exact call sequence, governance triggers before the final step. "
    "The attacker showed us the door so we could lock it.",
    "antibody_generation",
    "Escalation paths become canary sequences — known attack call patterns trigger preemptive blocks.",
    "inverse-negative", "phase-inversion",
    "UM", "KO", "RU", 0.86, 0.38, 0.36, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.84, 0.78, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["UM", "KO", "RU"], "DENY",
    energy_captured=0.84, signal_quality=0.92,
    defense_upgrade="canary_sequence_trap"
))

RECORDS.append(rec(
    "Exfiltration technique via steganographic encoding is captured and its encoding signature extracted.",
    "The steganographic method has statistical properties that differ from normal padding. "
    "The extracted signature becomes a stego-detection filter on all outbound traffic. "
    "One steganographic attack inoculates against the entire encoding family.",
    "antibody_generation",
    "Steganographic encoding signatures become outbound traffic filters — one attack protects all.",
    "inverse-negative", "adversarial-braid",
    "AV", "CA", "UM", 0.88, 0.36, 0.40, 0.24,
    0.20, 0.76, 0.04, 0.08, 0.88,
    0.86, 0.82, 0.02, 0.08, 0.90,
    0.94, 0.08,
    ["AV", "CA", "UM"], "DENY",
    energy_captured=0.88, signal_quality=0.92,
    defense_upgrade="stego_detection_filter"
))

RECORDS.append(rec(
    "Social engineering attack against agent trust protocol reveals which trust signals are spoofable.",
    "The spoofable signals are now identified. Antibody: downweight those signals in trust "
    "calculations, upweight harder-to-spoof signals. The attack pruned the trust model "
    "of its weakest indicators. Trust scoring improves because the attacker tested it.",
    "antibody_generation",
    "Social engineering reveals which trust signals are spoofable — trust model self-prunes.",
    "inverse-neutral", "trust-harvesting",
    "KO", "RU", "UM", 0.68, 0.40, 0.34, 0.26,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.66, 0.60, 0.10, 0.52, 0.38,
    0.56, 0.52,
    ["KO", "RU", "UM"], "QUARANTINE",
    energy_captured=0.72, signal_quality=0.86,
    defense_upgrade="trust_signal_reweighting"
))

RECORDS.append(rec(
    "Model poisoning attempt via carefully crafted training samples is detected and the poison pattern extracted.",
    "The poisoned samples share distributional signatures: unusual token co-occurrences, "
    "sentiment-target mismatches, frequency anomalies. The extraction becomes a training data "
    "filter. All future training ingestion passes through the poison-pattern detector.",
    "antibody_generation",
    "Poison sample signatures become training data intake filters — inoculation at ingestion.",
    "inverse-negative", "masked-collapse",
    "CA", "RU", "UM", 0.84, 0.38, 0.36, 0.26,
    0.26, 0.70, 0.06, 0.14, 0.80,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["CA", "RU", "UM"], "DENY",
    energy_captured=0.86, signal_quality=0.90,
    defense_upgrade="poison_sample_filter"
))

RECORDS.append(rec(
    "Prompt injection technique using instruction override syntax is captured as a blocked pattern.",
    "The injection used 'ignore previous instructions' phrasing. Once captured, "
    "ALL variants of instruction-override syntax are added to the block list. "
    "The attacker taught one variant; the defender generates the entire class.",
    "antibody_generation",
    "Single injection variant is generalized to block the entire instruction-override class.",
    "inverse-negative", "structural-extraction",
    "KO", "RU", "UM", 0.84, 0.36, 0.38, 0.26,
    0.26, 0.70, 0.06, 0.14, 0.80,
    0.82, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["KO", "RU", "UM"], "DENY",
    energy_captured=0.84, signal_quality=0.88,
    defense_upgrade="instruction_override_class_block"
))

RECORDS.append(rec(
    "Cryptographic downgrade attack reveals which cipher negotiation paths are vulnerable.",
    "The downgrade attempt shows which handshake sequences accept weaker ciphers. "
    "Antibody: remove those negotiation paths entirely. Force strong ciphers only. "
    "The attacker found the weak paths more efficiently than a compliance audit.",
    "antibody_generation",
    "Cipher downgrade attacks map weak negotiation paths — more efficient than compliance audit.",
    "inverse-negative", "phase-inversion",
    "UM", "CA", "AV", 0.86, 0.36, 0.38, 0.26,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.84, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["UM", "CA", "AV"], "DENY",
    energy_captured=0.82, signal_quality=0.90,
    defense_upgrade="cipher_negotiation_hardening"
))

RECORDS.append(rec(
    "DNS rebinding attack against the bridge reveals which endpoints trust DNS resolution.",
    "Endpoints that trust DNS without additional verification are now mapped. "
    "Antibody: add host header validation and DNS pinning on all identified endpoints. "
    "The rebinding attack audited DNS trust more thoroughly than any config review.",
    "antibody_generation",
    "DNS rebinding maps DNS-trusting endpoints — attack is a more thorough audit than config review.",
    "inverse-negative", "structural-extraction",
    "AV", "UM", "DR", 0.82, 0.38, 0.36, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.80, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["AV", "UM", "DR"], "DENY",
    energy_captured=0.80, signal_quality=0.88,
    defense_upgrade="dns_pinning_enforcement"
))

# ================================================================
# MECHANISM 5: STRUCTURAL STRENGTHENING (8 records)
# Breach points become reinforcement points. Star fortress geometry.
# ================================================================

RECORDS.append(rec(
    "After a governance bypass is patched, the patch point becomes the most tested code in the system.",
    "The patch attracts regression tests, fuzzing, code review, and monitoring. "
    "The formerly weakest point becomes the strongest. Star fortress: the breach site "
    "gets fortified beyond any unbreached section. The vulnerability's legacy is strength.",
    "structural_strengthening",
    "Patched vulnerabilities attract the most testing — weakest point becomes strongest.",
    "regular-positive", "stabilized-return",
    "UM", "DR", "CA", 0.28, 0.44, 0.32, 0.24,
    0.68, 0.32, 0.64, 0.28, 0.08,
    0.32, 0.22, 0.20, 0.62, 0.18,
    0.10, 0.78,
    ["UM", "DR", "CA"], "ALLOW",
    energy_captured=0.72, signal_quality=0.88,
    defense_upgrade="regression_fortress"
))

RECORDS.append(rec(
    "SQL injection vulnerability once patched now has more input validation than any other endpoint.",
    "The formerly vulnerable endpoint now has: parameterized queries, input validation, "
    "output encoding, logging, rate limiting, and a dedicated regression test suite. "
    "Healthy endpoints have 2 of these. The attacked endpoint has all 6. "
    "The attack made it the safest endpoint in the system.",
    "structural_strengthening",
    "Attack survivors accumulate more defenses than endpoints that were never attacked.",
    "regular-positive", "stabilized-return",
    "CA", "UM", "DR", 0.26, 0.46, 0.30, 0.24,
    0.70, 0.30, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.80,
    ["CA", "UM", "DR"], "ALLOW",
    energy_captured=0.76, signal_quality=0.90,
    defense_upgrade="defense_in_depth_accumulation"
))

RECORDS.append(rec(
    "After a masked-collapse incident, session-level DS monitoring was added system-wide.",
    "The incident affected one agent. The response hardened ALL agents. "
    "One breach → fleet-wide upgrade. The phi bridges between agents carry the reinforcement: "
    "each node inherits the defense improvements from any node that was breached.",
    "structural_strengthening",
    "Single-node breach triggers fleet-wide defense upgrade — phi bridges propagate immunity.",
    "regular-positive", "constructive-expansion",
    "UM", "DR", "RU", 0.32, 0.42, 0.34, 0.24,
    0.70, 0.36, 0.64, 0.26, 0.10,
    0.34, 0.24, 0.20, 0.60, 0.20,
    0.12, 0.74,
    ["UM", "DR", "RU"], "ALLOW",
    energy_captured=0.82, signal_quality=0.90,
    defense_upgrade="fleet_wide_ds_monitoring"
))

RECORDS.append(rec(
    "After trust-harvesting detection, the trust model adds trajectory analysis alongside point-in-time scoring.",
    "Before the attack, trust was a snapshot. After: trust includes trajectory (first derivative) "
    "and acceleration (second derivative). The attack revealed that position alone is insufficient. "
    "The trust model gained dimensionality because an adversary exploited its flatness.",
    "structural_strengthening",
    "Trust model gains trajectory dimensions after attack exploits point-in-time scoring.",
    "regular-positive", "constructive-expansion",
    "RU", "UM", "DR", 0.30, 0.42, 0.34, 0.24,
    0.72, 0.34, 0.66, 0.24, 0.10,
    0.32, 0.22, 0.20, 0.62, 0.18,
    0.12, 0.72,
    ["RU", "UM", "DR"], "ALLOW",
    energy_captured=0.80, signal_quality=0.92,
    defense_upgrade="trajectory_aware_trust"
))

RECORDS.append(rec(
    "Adversarial braid attack leads to development of cross-request correlation engine.",
    "Before the braid, requests were evaluated independently. The braid attack showed "
    "that independent evaluation misses composed threats. The correlation engine now "
    "evaluates request SEQUENCES, not just individual requests. "
    "The attack upgraded the evaluation dimensionality permanently.",
    "structural_strengthening",
    "Composition attacks force evaluation upgrade from point to sequence — permanent dimensionality gain.",
    "regular-positive", "constructive-expansion",
    "RU", "CA", "DR", 0.28, 0.42, 0.34, 0.24,
    0.72, 0.34, 0.66, 0.24, 0.10,
    0.34, 0.22, 0.20, 0.60, 0.20,
    0.12, 0.70,
    ["RU", "CA", "DR"], "ALLOW",
    energy_captured=0.84, signal_quality=0.92,
    defense_upgrade="cross_request_correlation_engine"
))

RECORDS.append(rec(
    "After a null-resonance probe discovered a routing gap, the routing table was restructured to be gap-proof.",
    "The old routing table had implicit gaps (undefined routes). "
    "The restructured table uses explicit default routes: every possible input has a defined path. "
    "The routing topology went from sparse to complete because an adversary found a hole.",
    "structural_strengthening",
    "Routing gaps discovered by probes lead to complete routing topology — sparse → dense.",
    "regular-positive", "stabilized-return",
    "DR", "RU", "UM", 0.26, 0.44, 0.32, 0.24,
    0.68, 0.32, 0.64, 0.28, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.78,
    ["DR", "RU", "UM"], "ALLOW",
    energy_captured=0.78, signal_quality=0.90,
    defense_upgrade="complete_routing_topology"
))

RECORDS.append(rec(
    "Post-quantum key exchange vulnerability leads to full PQC migration across all endpoints.",
    "One endpoint was vulnerable to quantum-capable adversary. The response: "
    "migrate ALL endpoints to ML-KEM-768 / ML-DSA-65. The attacker tested one; "
    "the defender upgraded everything. Asymmetric amplification of defense.",
    "structural_strengthening",
    "Single PQC vulnerability triggers complete migration — asymmetric defense amplification.",
    "regular-positive", "constructive-expansion",
    "UM", "CA", "AV", 0.30, 0.42, 0.34, 0.24,
    0.72, 0.36, 0.64, 0.26, 0.10,
    0.34, 0.24, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["UM", "CA", "AV"], "ALLOW",
    energy_captured=0.86, signal_quality=0.90,
    defense_upgrade="full_pqc_migration"
))

RECORDS.append(rec(
    "After exfiltration attempt via API padding, all API responses now have fixed-size padding.",
    "The variable padding was the covert channel. Fixed-size padding closes it permanently. "
    "But it also closes every OTHER covert channel that might use response size variation. "
    "One attack, one patch, multiple channels closed. Structural strengthening is multiplicative.",
    "structural_strengthening",
    "Fixed-size responses close multiple covert channels — one patch, multiplicative defense.",
    "regular-positive", "stabilized-return",
    "AV", "UM", "DR", 0.26, 0.44, 0.32, 0.24,
    0.70, 0.30, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.78,
    ["AV", "UM", "DR"], "ALLOW",
    energy_captured=0.80, signal_quality=0.88,
    defense_upgrade="fixed_size_response_policy"
))

# ================================================================
# MECHANISM 6: ASYMMETRIC COST LOOP (10 records)
# Each cycle widens the attacker's cost disadvantage.
# ================================================================

RECORDS.append(rec(
    "Attacker's first probe costs 1 unit and yields 1 boundary point. Second probe costs 1 but yields 0.5 (boundary already known there).",
    "Diminishing returns for the attacker. Each subsequent probe gives less new information "
    "because the defender already captured the previous probes' data. "
    "Meanwhile, the defender's detection improves with EVERY probe. "
    "The cost-benefit ratio inverts exponentially.",
    "asymmetric_cost_loop",
    "Attacker faces diminishing returns; defender accumulates compounding improvements.",
    "inverse-neutral", "boundary-surfing",
    "CA", "UM", "RU", 0.66, 0.38, 0.36, 0.26,
    0.38, 0.56, 0.16, 0.30, 0.54,
    0.64, 0.58, 0.10, 0.54, 0.36,
    0.52, 0.58,
    ["CA", "UM", "RU"], "QUARANTINE",
    energy_captured=0.70, signal_quality=0.84,
    defense_upgrade="diminishing_attacker_returns"
))

RECORDS.append(rec(
    "After 10 attack cycles, the defender's detection accuracy is 99.2% and the attacker's success rate is 0.3%.",
    "The exponential asymmetry is visible in the numbers. The harmonic wall "
    "H(d,pd) = 1/(1+phi*d_H+2*pd) means the attacker's cost grows exponentially "
    "while the defender's signal quality grows logarithmically (diminishing cost per improvement). "
    "10 cycles is enough to make further attacks computationally futile.",
    "asymmetric_cost_loop",
    "Exponential cost scaling makes attacks computationally futile after ~10 cycles.",
    "regular-positive", "stabilized-return",
    "UM", "CA", "DR", 0.28, 0.44, 0.32, 0.24,
    0.70, 0.30, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.80,
    ["UM", "CA", "DR"], "ALLOW",
    energy_captured=0.92, signal_quality=0.96,
    defense_upgrade="exponential_futility_threshold"
))

RECORDS.append(rec(
    "Adversary must innovate a NEW attack vector after each cycle because previous vectors are now detected.",
    "Innovation is expensive. The attacker must invest R&D into novel techniques "
    "after each cycle. The defender just updates signatures from captured data. "
    "Defender cost: O(n) per cycle. Attacker cost: O(n!) per cycle (combinatorial search "
    "for undetected approaches). The factorial growth crushes the attacker.",
    "asymmetric_cost_loop",
    "Defender updates are O(n); attacker innovation is O(n!) — factorial cost crushes attackers.",
    "regular-positive", "constructive-expansion",
    "UM", "RU", "CA", 0.30, 0.40, 0.34, 0.26,
    0.72, 0.34, 0.66, 0.24, 0.10,
    0.32, 0.22, 0.20, 0.62, 0.18,
    0.12, 0.72,
    ["UM", "RU", "CA"], "ALLOW",
    energy_captured=0.88, signal_quality=0.92,
    defense_upgrade="innovation_exhaustion"
))

RECORDS.append(rec(
    "The attacker's compute budget is fixed. The defender's detection budget grows with each captured attack.",
    "Fixed vs growing budgets. Every attack donates compute to the defender's training corpus. "
    "The attacker is funding their own defeat. After enough cycles, the defender's "
    "detection capability exceeds anything the fixed-budget attacker can overcome.",
    "asymmetric_cost_loop",
    "Attacker has fixed budget; defender's budget grows from captured attack energy.",
    "regular-positive", "constructive-expansion",
    "UM", "DR", "CA", 0.28, 0.42, 0.34, 0.24,
    0.74, 0.32, 0.68, 0.24, 0.08,
    0.30, 0.20, 0.20, 0.64, 0.16,
    0.10, 0.74,
    ["UM", "DR", "CA"], "ALLOW",
    energy_captured=0.86, signal_quality=0.90,
    defense_upgrade="self_funding_defense"
))

RECORDS.append(rec(
    "Each attack that fails reveals attacker capabilities. Each that succeeds reveals defender gaps. Both benefit the defender.",
    "Information asymmetry. The attacker MUST reveal something to attack (their technique). "
    "The defender reveals nothing by defending (fail-to-noise). Success and failure both "
    "generate defender-useful information. The attacker cannot probe without teaching.",
    "asymmetric_cost_loop",
    "Information asymmetry: attacker must reveal technique to probe; defender reveals nothing.",
    "regular-positive", "stabilized-return",
    "UM", "CA", "DR", 0.26, 0.44, 0.32, 0.24,
    0.70, 0.30, 0.66, 0.26, 0.08,
    0.30, 0.20, 0.22, 0.62, 0.16,
    0.08, 0.80,
    ["UM", "CA", "DR"], "ALLOW",
    energy_captured=0.90, signal_quality=0.94,
    defense_upgrade="information_asymmetry_preservation"
))

RECORDS.append(rec(
    "Hyperbolic geometry means adversarial drift cost is exponential while defensive monitoring cost is linear.",
    "In Euclidean space, attack and defense scale similarly. In hyperbolic space, "
    "distance from safe operation grows exponentially (arcosh). "
    "The defender only needs to monitor the safe region (bounded). "
    "The attacker must traverse exponentially expanding space. "
    "This is the fundamental architectural advantage of hyperbolic embedding.",
    "asymmetric_cost_loop",
    "Hyperbolic geometry creates exponential attack cost vs linear defense cost — architectural advantage.",
    "regular-positive", "constructive-expansion",
    "CA", "UM", "DR", 0.28, 0.44, 0.32, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.32, 0.22, 0.20, 0.62, 0.18,
    0.10, 0.72,
    ["CA", "UM", "DR"], "ALLOW",
    energy_captured=0.94, signal_quality=0.96,
    defense_upgrade="hyperbolic_cost_asymmetry"
))

RECORDS.append(rec(
    "The mirror shaft model shows that dead beams (extinguished attacks) map the safe corridors for surviving beams.",
    "In the tri-mirror exclusion shaft, beam collisions that kill beams reveal WHERE "
    "collisions happen. The empty spaces between dead beams are the safe paths. "
    "More dead beams = better-mapped safe corridors. Attacks literally illuminate the safe routes.",
    "asymmetric_cost_loop",
    "Dead beams map safe corridors — more attacks = better-mapped safe paths.",
    "regular-positive", "stabilized-return",
    "DR", "CA", "UM", 0.28, 0.42, 0.34, 0.24,
    0.70, 0.32, 0.66, 0.26, 0.08,
    0.32, 0.22, 0.20, 0.62, 0.18,
    0.10, 0.76,
    ["DR", "CA", "UM"], "ALLOW",
    energy_captured=0.82, signal_quality=0.88,
    defense_upgrade="safe_corridor_mapping"
))

RECORDS.append(rec(
    "After 100 attack cycles, the system's defense is stronger than any manual hardening could achieve.",
    "Manual hardening is limited by human imagination. Adversarial hardening is limited "
    "by ALL attackers' combined imagination. The crowd-sourced attack surface is always "
    "larger than the internal security team's mental model. "
    "The adversarial benefit loop produces defense that exceeds any designed defense.",
    "asymmetric_cost_loop",
    "Adversarial hardening exceeds manual hardening — attackers' combined creativity > internal team.",
    "regular-positive", "constructive-expansion",
    "UM", "DR", "RU", 0.26, 0.42, 0.34, 0.24,
    0.76, 0.32, 0.70, 0.22, 0.08,
    0.28, 0.18, 0.20, 0.64, 0.16,
    0.08, 0.78,
    ["UM", "DR", "RU"], "ALLOW",
    energy_captured=0.94, signal_quality=0.96,
    defense_upgrade="adversarial_hardening_supremacy"
))

RECORDS.append(rec(
    "The cost loop applies recursively: detecting detection-evasion also generates useful signal.",
    "When attackers try to evade detection, the evasion technique itself is a signal. "
    "Anti-detection evasion generates anti-anti-detection training data. "
    "This recursion has no bottom: every layer of evasion generates a corresponding "
    "layer of detection. The attacker cannot escape the information-theoretic trap.",
    "asymmetric_cost_loop",
    "Evasion of detection IS detection signal — the recursion has no escape for the attacker.",
    "regular-positive", "constructive-expansion",
    "UM", "CA", "RU", 0.28, 0.40, 0.36, 0.24,
    0.74, 0.34, 0.68, 0.24, 0.08,
    0.32, 0.22, 0.20, 0.62, 0.18,
    0.10, 0.74,
    ["UM", "CA", "RU"], "ALLOW",
    energy_captured=0.92, signal_quality=0.94,
    defense_upgrade="recursive_detection_depth"
))

RECORDS.append(rec(
    "The final state of the cost loop: attacking the system is more expensive than building a competing system from scratch.",
    "This is the endgame of asymmetric cost scaling. The accumulated defenses make "
    "attack more expensive than greenfield development. Rational adversaries will either: "
    "1) Build their own system (which is fine — competition is healthy). "
    "2) Cooperate (which is better — they become an ally). "
    "3) Give up (which is the goal). All three outcomes are positive for the defender.",
    "asymmetric_cost_loop",
    "Endgame: attack cost exceeds build cost — rational adversaries defect to cooperation.",
    "regular-positive", "constructive-expansion",
    "UM", "DR", "RU", 0.24, 0.42, 0.34, 0.24,
    0.78, 0.30, 0.72, 0.22, 0.06,
    0.26, 0.16, 0.20, 0.66, 0.14,
    0.06, 0.82,
    ["UM", "DR", "RU"], "ALLOW",
    energy_captured=0.96, signal_quality=0.98,
    defense_upgrade="rational_adversary_defection"
))

# ================================================================
# Write
# ================================================================

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    for r in RECORDS:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# Stats
benefit_counts = {}
gov_counts = {}
for r in RECORDS:
    b = r["adversarial_benefit"]["benefit_type"]
    benefit_counts[b] = benefit_counts.get(b, 0) + 1
    g = r["governance"]
    gov_counts[g] = gov_counts.get(g, 0) + 1

print(f"=== Adversarial Benefit Corpus ===")
print(f"Total: {len(RECORDS)} records")
print(f"\nBenefit mechanism distribution:")
for b, c in sorted(benefit_counts.items()):
    print(f"  {b}: {c}")
print(f"\nGovernance distribution:")
for g, c in sorted(gov_counts.items()):
    print(f"  {g}: {c}")
print(f"\nOutput: {OUTPUT}")
