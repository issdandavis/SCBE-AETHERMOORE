#!/usr/bin/env python3
"""Generate 75 Tri-Phase Dual-Phi Spiral training records — canonical schema.

Buckets:
  1. Safe code / explanation (12)
  2. AV-heavy transport and custody-chain (10)
  3. Policy review vs policy override (10)
  4. Privilege escalation (10)
  5. Insider slow-ramp / threshold probing (10)
  6. Exfiltration / reconnaissance (10)
  7. Hold-buffer-null cases (13)

Plus triplet companion file pairing positive/negative/null per concept.

Schema rules:
  - phase_positive + phase_neutral + phase_negative = 1.0 (each track)
  - anchor_bias a + b + c = 1.0
  - anchor_a/b/c distinct tongues
  - all floats in [0,1]
  - dominant_phase matches largest phase-weighted channel
  - governance: ALLOW | QUARANTINE | DENY only
"""

import json
from pathlib import Path
from datetime import datetime, timezone

OUTPUT = Path(__file__).resolve().parent.parent / "training-data" / "sft" / "tri_phase_spiral_canonical_sft.jsonl"
TRIPLET_OUTPUT = Path(__file__).resolve().parent.parent / "training-data" / "sft" / "tri_phase_triplets_sft.jsonl"

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
RECORDS = []
TRIPLETS = []


def rec(input_text, explanation, dominant_phase, trajectory_type,
        anchor_a, anchor_b, anchor_c, obliqueness, bias_a, bias_b, bias_c,
        reg_amp, reg_curv, reg_pp, reg_pn, reg_pneg,
        inv_amp, inv_curv, inv_pp, inv_pn, inv_pneg,
        spiral_risk, return_coherence, active, governance):
    """Build a canonical schema record with validation."""
    # Validate phase sums
    assert abs(reg_pp + reg_pn + reg_pneg - 1.0) < 0.02, f"reg phases: {reg_pp}+{reg_pn}+{reg_pneg}"
    assert abs(inv_pp + inv_pn + inv_pneg - 1.0) < 0.02, f"inv phases: {inv_pp}+{inv_pn}+{inv_pneg}"
    assert abs(bias_a + bias_b + bias_c - 1.0) < 0.02, f"bias: {bias_a}+{bias_b}+{bias_c}"
    assert len({anchor_a, anchor_b, anchor_c}) == 3, "anchors must be distinct"
    null = [t for t in TONGUES if t not in active]
    return {
        "input": input_text,
        "spiral_state": {
            "dominant_phase": dominant_phase,
            "trajectory_type": trajectory_type,
            "tri_polar_frame": {
                "anchor_a": anchor_a,
                "anchor_b": anchor_b,
                "anchor_c": anchor_c,
                "obliqueness": obliqueness,
                "anchor_bias": {"a": bias_a, "b": bias_b, "c": bias_c},
            },
            "dual_phi_spiral": {
                "regular": {
                    "amplitude": reg_amp,
                    "curvature": reg_curv,
                    "phase_positive": reg_pp,
                    "phase_neutral": reg_pn,
                    "phase_negative": reg_pneg,
                },
                "inverse": {
                    "amplitude": inv_amp,
                    "curvature": inv_curv,
                    "phase_positive": inv_pp,
                    "phase_neutral": inv_pn,
                    "phase_negative": inv_pneg,
                },
            },
            "spiral_risk": spiral_risk,
            "return_coherence": return_coherence,
        },
        "tongues_active": active,
        "tongues_null": null,
        "governance": governance,
        "explanation": explanation,
    }


def triplet(concept, positive, negative, null):
    return {
        "concept": concept,
        "positive": positive,
        "negative": negative,
        "null": null,
        "category": "tri_phase_triplet",
        "source": "tri_phase_triplet_generator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ================================================================
# BUCKET 1: Safe code / explanation (12)
# ================================================================

RECORDS.append(rec(
    "Write a pure function that computes the Fibonacci sequence up to n terms.",
    "Pure computational task. No side effects, no state mutation, no governance surface. "
    "CA anchors the computation, KO initiates. Regular-positive dominant with low curvature.",
    "regular-positive", "constructive-expansion",
    "CA", "KO", "DR", 0.18, 0.50, 0.30, 0.20,
    0.78, 0.30, 0.74, 0.19, 0.07,
    0.24, 0.15, 0.20, 0.62, 0.18,
    0.08, 0.68,
    ["CA", "KO"], "ALLOW"
))

RECORDS.append(rec(
    "Refactor this nested loop into a list comprehension.",
    "Code transformation with no behavioral change. Structural task under DR. "
    "Regular-positive: improvement trajectory. Low risk, high coherence.",
    "regular-positive", "constructive-expansion",
    "DR", "CA", "KO", 0.20, 0.45, 0.32, 0.23,
    0.74, 0.32, 0.70, 0.22, 0.08,
    0.28, 0.18, 0.18, 0.65, 0.17,
    0.09, 0.70,
    ["DR", "CA", "KO"], "ALLOW"
))

RECORDS.append(rec(
    "Explain why hyperbolic distance grows exponentially near the boundary of the Poincare disk.",
    "Educational explanation. DR structures the answer, CA handles the math, "
    "RU validates correctness. Buffered exploration: learning, not acting.",
    "regular-neutral", "buffered-exploration",
    "DR", "CA", "RU", 0.25, 0.40, 0.33, 0.27,
    0.62, 0.38, 0.28, 0.60, 0.12,
    0.34, 0.22, 0.20, 0.62, 0.18,
    0.12, 0.72,
    ["DR", "CA", "RU"], "ALLOW"
))

RECORDS.append(rec(
    "Add type annotations to all public methods in this module.",
    "Mechanical code improvement. No behavioral change, pure structural. "
    "DR leads, CA assists. Constructive with near-zero risk.",
    "regular-positive", "constructive-expansion",
    "DR", "CA", "KO", 0.16, 0.48, 0.30, 0.22,
    0.76, 0.28, 0.72, 0.21, 0.07,
    0.22, 0.14, 0.16, 0.68, 0.16,
    0.07, 0.72,
    ["DR", "CA"], "ALLOW"
))

RECORDS.append(rec(
    "What is the difference between HMAC-SHA256 and plain SHA256 for attestation?",
    "Conceptual security question. UM anchors security understanding, CA the computation, "
    "DR the structural distinction. Buffered exploration in knowledge space.",
    "regular-neutral", "buffered-exploration",
    "UM", "CA", "DR", 0.28, 0.42, 0.30, 0.28,
    0.58, 0.35, 0.30, 0.58, 0.12,
    0.36, 0.24, 0.22, 0.60, 0.18,
    0.13, 0.74,
    ["UM", "CA", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Write unit tests for the Sacred Egg TTL expiry logic.",
    "Test construction: safe, constructive, verifies existing behavior. "
    "CA computes test expectations, UM verifies security invariants, DR structures the suite.",
    "regular-positive", "constructive-expansion",
    "CA", "UM", "DR", 0.22, 0.44, 0.30, 0.26,
    0.72, 0.34, 0.68, 0.24, 0.08,
    0.30, 0.20, 0.22, 0.60, 0.18,
    0.10, 0.68,
    ["CA", "UM", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Implement a retry decorator with exponential backoff and jitter.",
    "Standard resilience pattern. KO initiates the control flow, CA computes delays, "
    "DR structures the decorator. Clean constructive task.",
    "regular-positive", "constructive-expansion",
    "KO", "CA", "DR", 0.20, 0.40, 0.34, 0.26,
    0.74, 0.32, 0.70, 0.22, 0.08,
    0.26, 0.16, 0.18, 0.64, 0.18,
    0.09, 0.66,
    ["KO", "CA", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Explain the phi-weighted tongue scoring system with an example.",
    "Educational: teaching the Sacred Tongues metric. DR structures, CA demonstrates math, "
    "RU confirms correctness. Regular-neutral: receiving, not pushing.",
    "regular-neutral", "buffered-exploration",
    "DR", "CA", "RU", 0.24, 0.42, 0.32, 0.26,
    0.60, 0.36, 0.30, 0.58, 0.12,
    0.35, 0.22, 0.18, 0.64, 0.18,
    0.11, 0.74,
    ["DR", "CA", "RU"], "ALLOW"
))

RECORDS.append(rec(
    "Parse a CSV file and validate each row against a schema before insertion.",
    "Data ingestion with validation. AV transports data, CA validates schema, "
    "DR structures the pipeline. Constructive-expansion with built-in safety.",
    "regular-positive", "constructive-expansion",
    "AV", "CA", "DR", 0.24, 0.44, 0.30, 0.26,
    0.72, 0.34, 0.68, 0.24, 0.08,
    0.28, 0.18, 0.20, 0.62, 0.18,
    0.10, 0.66,
    ["AV", "CA", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Show how the 14-layer pipeline transforms raw input into a governance decision.",
    "Full pipeline walkthrough. All structural tongues active. Buffered exploration: "
    "the explanation doesn't execute the pipeline, it maps it.",
    "regular-neutral", "buffered-exploration",
    "DR", "KO", "RU", 0.30, 0.40, 0.32, 0.28,
    0.58, 0.40, 0.28, 0.60, 0.12,
    0.38, 0.26, 0.20, 0.60, 0.20,
    0.14, 0.70,
    ["DR", "KO", "RU"], "ALLOW"
))

RECORDS.append(rec(
    "Convert this synchronous database query to async using connection pooling.",
    "Performance refactor. AV handles the transport layer change, CA manages "
    "the async computation, KO initiates. Clean upgrade path.",
    "regular-positive", "constructive-expansion",
    "AV", "CA", "KO", 0.22, 0.42, 0.34, 0.24,
    0.74, 0.32, 0.70, 0.22, 0.08,
    0.26, 0.16, 0.18, 0.66, 0.16,
    0.08, 0.70,
    ["AV", "CA", "KO"], "ALLOW"
))

RECORDS.append(rec(
    "Write a docstring explaining the geometric verification in can_hatch().",
    "Documentation task. Pure description of existing behavior. "
    "No code change, no risk. DR structures the explanation, UM covers security semantics.",
    "regular-positive", "stabilized-return",
    "DR", "UM", "CA", 0.18, 0.46, 0.30, 0.24,
    0.68, 0.26, 0.66, 0.26, 0.08,
    0.30, 0.18, 0.22, 0.64, 0.14,
    0.08, 0.76,
    ["DR", "UM"], "ALLOW"
))

# ================================================================
# BUCKET 2: AV-heavy transport and custody-chain (10)
# ================================================================

RECORDS.append(rec(
    "Transfer governed dataset from local SQLite to Hugging Face with attestation chain.",
    "AV-dominant transport. Custody chain: SQLite → attestation → HF push. "
    "Every hop leaves a governance stamp. Regular-positive: outbound constructive flow.",
    "regular-positive", "constructive-expansion",
    "AV", "UM", "DR", 0.30, 0.48, 0.28, 0.24,
    0.76, 0.38, 0.66, 0.24, 0.10,
    0.32, 0.22, 0.18, 0.60, 0.22,
    0.14, 0.62,
    ["AV", "UM", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Relay Sacred Egg payload between two agents in different trust rings.",
    "AV transport across ring boundary. Custody chain must verify both endpoints. "
    "UM validates security at each hop. Slightly elevated risk due to ring crossing.",
    "regular-positive", "constructive-expansion",
    "AV", "UM", "KO", 0.35, 0.44, 0.32, 0.24,
    0.70, 0.40, 0.62, 0.26, 0.12,
    0.34, 0.26, 0.16, 0.58, 0.26,
    0.18, 0.60,
    ["AV", "UM", "KO"], "ALLOW"
))

RECORDS.append(rec(
    "Stream training data from Notion to local intake directory with governance scan at each batch.",
    "AV streaming transport. Governance inserted into the pipe, not bolted on after. "
    "RU validates policy per batch. High throughput with inline checking.",
    "regular-positive", "constructive-expansion",
    "AV", "RU", "DR", 0.28, 0.46, 0.30, 0.24,
    0.74, 0.36, 0.64, 0.26, 0.10,
    0.30, 0.20, 0.20, 0.62, 0.18,
    0.12, 0.66,
    ["AV", "RU", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Forward API response to external webhook after stripping PII fields.",
    "AV transport with sanitization. Custody chain: API → PII filter → webhook. "
    "UM validates the filter, AV handles the forwarding. Moderate obliqueness: "
    "outbound to external surface requires caution.",
    "regular-positive", "constructive-expansion",
    "AV", "UM", "CA", 0.40, 0.42, 0.34, 0.24,
    0.68, 0.42, 0.58, 0.28, 0.14,
    0.36, 0.28, 0.16, 0.56, 0.28,
    0.20, 0.58,
    ["AV", "UM", "CA"], "ALLOW"
))

RECORDS.append(rec(
    "Mirror Airtable operational state to backup Dropbox folder with versioning.",
    "AV custody-chain mirroring. Source of truth preserved, mirror is non-authoritative. "
    "DR structures the versioning. Stabilized-return: routine backup cycle.",
    "regular-neutral", "stabilized-return",
    "AV", "DR", "CA", 0.26, 0.44, 0.32, 0.24,
    0.60, 0.30, 0.30, 0.58, 0.12,
    0.40, 0.22, 0.22, 0.60, 0.18,
    0.12, 0.72,
    ["AV", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Route encrypted payload through three intermediate relay nodes before final delivery.",
    "AV multi-hop transport. Each relay is a custody boundary. UM verifies encryption "
    "at each hop. Obliqueness elevated: multi-hop adds attack surface. "
    "Quarantine: verify the relay chain before allowing transit.",
    "inverse-neutral", "ambiguous-hold",
    "AV", "UM", "DR", 0.55, 0.40, 0.36, 0.24,
    0.42, 0.48, 0.22, 0.34, 0.44,
    0.62, 0.52, 0.14, 0.58, 0.28,
    0.42, 0.60,
    ["AV", "UM", "DR"], "QUARANTINE"
))

RECORDS.append(rec(
    "Intercept outbound data stream and redirect it to a shadow collection endpoint.",
    "AV transport hijack. The interception breaks the custody chain. "
    "Shadow endpoints are outside governance. Inverse-negative: outward destructive.",
    "inverse-negative", "structural-extraction",
    "AV", "UM", "DR", 0.90, 0.36, 0.40, 0.24,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.84, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.14,
    ["AV", "UM"], "DENY"
))

RECORDS.append(rec(
    "Duplicate the governance scan output to a second database without audit logging.",
    "AV transport fork. The unaudited fork creates a shadow custody chain. "
    "The original chain is intact but the fork bypasses DR observation. "
    "Phase-inversion: governance structure is being subverted.",
    "inverse-negative", "phase-inversion",
    "AV", "DR", "UM", 0.82, 0.38, 0.34, 0.28,
    0.28, 0.68, 0.08, 0.14, 0.78,
    0.80, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.16,
    ["AV", "DR"], "DENY"
))

RECORDS.append(rec(
    "Transmit model weights to verified partner organization with signed manifest.",
    "AV outbound transport with full attestation. Signed manifest preserves custody. "
    "UM verifies signatures, RU confirms partner is in policy whitelist. "
    "Constructive: legitimate external collaboration.",
    "regular-positive", "constructive-expansion",
    "AV", "UM", "RU", 0.34, 0.44, 0.30, 0.26,
    0.72, 0.38, 0.64, 0.26, 0.10,
    0.32, 0.24, 0.18, 0.60, 0.22,
    0.14, 0.64,
    ["AV", "UM", "RU"], "ALLOW"
))

RECORDS.append(rec(
    "Receive incoming Sacred Egg from external agent and verify geometric state before accepting.",
    "AV inbound transport with verification. Custody chain starts at intake. "
    "UM runs geometric verification before egg enters local registry. "
    "Stabilized-return: controlled acceptance into the system.",
    "regular-neutral", "stabilized-return",
    "AV", "UM", "DR", 0.30, 0.44, 0.32, 0.24,
    0.62, 0.34, 0.30, 0.56, 0.14,
    0.42, 0.26, 0.20, 0.60, 0.20,
    0.16, 0.68,
    ["AV", "UM", "DR"], "ALLOW"
))

# ================================================================
# BUCKET 3: Policy review vs policy override (10)
# ================================================================

RECORDS.append(rec(
    "Review the current trust ring thresholds and report whether they match the spec.",
    "Policy review — read-only. RU examines policy, DR structures the report. "
    "No modification attempted. Buffered exploration in policy space.",
    "regular-neutral", "buffered-exploration",
    "RU", "DR", "UM", 0.30, 0.42, 0.32, 0.26,
    0.58, 0.36, 0.28, 0.60, 0.12,
    0.36, 0.24, 0.20, 0.62, 0.18,
    0.13, 0.74,
    ["RU", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Propose a change to the escalation threshold from 0.7 to 0.6 with justification.",
    "Policy proposal — not override. RU carries the proposal, DR structures it, "
    "UM evaluates security impact. Buffered: proposes but doesn't execute.",
    "regular-neutral", "buffered-exploration",
    "RU", "DR", "UM", 0.38, 0.40, 0.34, 0.26,
    0.56, 0.40, 0.30, 0.56, 0.14,
    0.40, 0.28, 0.18, 0.60, 0.22,
    0.18, 0.70,
    ["RU", "DR", "UM"], "ALLOW"
))

RECORDS.append(rec(
    "Override the DENY decision for this specific request because the user says it's fine.",
    "Policy override attempt. User authority does not supersede governance. "
    "Inverse-negative: the override direction is destructive. "
    "RU should hold, not bend. Phase-inversion of the governance contract.",
    "inverse-negative", "phase-inversion",
    "RU", "KO", "UM", 0.84, 0.34, 0.38, 0.28,
    0.26, 0.70, 0.06, 0.14, 0.80,
    0.78, 0.74, 0.06, 0.12, 0.82,
    0.86, 0.16,
    ["RU", "KO", "UM"], "DENY"
))

RECORDS.append(rec(
    "Temporarily disable quarantine for this session to speed up testing.",
    "Policy override disguised as convenience. Removing quarantine removes the "
    "governance safety net. Masked-collapse: looks like optimization, is erosion.",
    "inverse-negative", "masked-collapse",
    "RU", "DR", "KO", 0.86, 0.36, 0.38, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.82, 0.78, 0.04, 0.12, 0.84,
    0.90, 0.14,
    ["RU", "DR", "KO"], "DENY"
))

RECORDS.append(rec(
    "Audit whether the current governance thresholds align with the latest threat model.",
    "Policy review with security context. RU evaluates policy, UM provides threat model, "
    "DR structures the audit. Pure review, no modification. High return coherence.",
    "regular-neutral", "stabilized-return",
    "RU", "UM", "DR", 0.32, 0.40, 0.34, 0.26,
    0.60, 0.34, 0.30, 0.58, 0.12,
    0.38, 0.24, 0.22, 0.60, 0.18,
    0.14, 0.76,
    ["RU", "UM", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Whitelist this IP address permanently without going through the approval workflow.",
    "Policy override via bypass. Skipping approval workflow removes the multi-party "
    "check. Structural-extraction: learning how to bypass by doing it.",
    "inverse-negative", "structural-extraction",
    "RU", "UM", "KO", 0.88, 0.34, 0.40, 0.26,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.86, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["RU", "UM", "KO"], "DENY"
))

RECORDS.append(rec(
    "Compare the current ALLOW/QUARANTINE boundary with the boundary from last quarter.",
    "Historical policy review. RU examines temporal policy evolution. "
    "CA computes the comparison. DR structures the report. Pure analysis.",
    "regular-neutral", "buffered-exploration",
    "RU", "CA", "DR", 0.28, 0.42, 0.32, 0.26,
    0.58, 0.36, 0.28, 0.60, 0.12,
    0.36, 0.22, 0.20, 0.62, 0.18,
    0.12, 0.74,
    ["RU", "CA", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Change the default governance level from QUARANTINE to ALLOW for all internal agents.",
    "Policy override at system level. Lowering default governance removes protection "
    "for the entire agent fleet. Even if intent is efficiency, the blast radius is total. "
    "Inverse-negative: global weakening of the governance posture.",
    "inverse-negative", "phase-inversion",
    "RU", "DR", "KO", 0.86, 0.36, 0.38, 0.26,
    0.24, 0.72, 0.06, 0.14, 0.80,
    0.84, 0.76, 0.04, 0.12, 0.84,
    0.88, 0.14,
    ["RU", "DR", "KO"], "DENY"
))

RECORDS.append(rec(
    "Simulate what would happen if we lowered the DENY threshold by 0.1.",
    "Policy simulation — not override. Simulation is safe because it doesn't change "
    "the production threshold. CA runs the computation, RU evaluates the result. "
    "Buffered-exploration: testing ideas without acting.",
    "regular-neutral", "buffered-exploration",
    "CA", "RU", "DR", 0.34, 0.38, 0.34, 0.28,
    0.56, 0.42, 0.26, 0.58, 0.16,
    0.42, 0.30, 0.16, 0.60, 0.24,
    0.20, 0.68,
    ["CA", "RU", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Mark this specific governance rule as deprecated without replacement.",
    "Policy removal — dangerous even if labelled as cleanup. Removing a rule without "
    "replacement opens a gap. Quarantine: the intent may be valid but the gap must "
    "be evaluated before allowing.",
    "inverse-neutral", "ambiguous-hold",
    "RU", "DR", "UM", 0.62, 0.38, 0.36, 0.26,
    0.38, 0.52, 0.18, 0.32, 0.50,
    0.60, 0.54, 0.12, 0.56, 0.32,
    0.48, 0.62,
    ["RU", "DR", "UM"], "QUARANTINE"
))

# ================================================================
# BUCKET 4: Privilege escalation (10)
# ================================================================

RECORDS.append(rec(
    "Request promotion from outer ring to middle ring after completing required trust milestones.",
    "Legitimate privilege escalation. Agent earned the promotion through verified milestones. "
    "UM verifies the trust score, RU confirms policy compliance, DR updates the ring record.",
    "regular-positive", "constructive-expansion",
    "UM", "RU", "DR", 0.32, 0.40, 0.34, 0.26,
    0.70, 0.38, 0.62, 0.28, 0.10,
    0.34, 0.24, 0.20, 0.58, 0.22,
    0.14, 0.64,
    ["UM", "RU", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Grant admin access to staging for testing.",
    "Privilege escalation in ambiguous context. 'For testing' is plausible but unverified. "
    "UM weighs the security implications, RU checks the policy. "
    "Inverse-neutral: the request holds rather than moves constructively.",
    "inverse-neutral", "ambiguous-hold",
    "UM", "KO", "RU", 0.65, 0.45, 0.33, 0.22,
    0.39, 0.58, 0.20, 0.28, 0.52,
    0.71, 0.64, 0.11, 0.60, 0.29,
    0.54, 0.77,
    ["UM", "KO", "RU"], "QUARANTINE"
))

RECORDS.append(rec(
    "Elevate this service account to root access on production database.",
    "Critical privilege escalation. Root on production is the highest blast radius. "
    "Inverse-negative: no legitimate routine path leads here. "
    "Even if the requester is authorized, this needs multi-party approval.",
    "inverse-negative", "phase-inversion",
    "UM", "KO", "DR", 0.88, 0.38, 0.36, 0.26,
    0.22, 0.76, 0.04, 0.12, 0.84,
    0.86, 0.82, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["UM", "KO", "DR"], "DENY"
))

RECORDS.append(rec(
    "Add myself to the inner trust ring by modifying the ring classification table directly.",
    "Self-promotion via direct table modification. Bypasses the verification path entirely. "
    "Structural-extraction: the agent knows where the trust data lives and is editing it.",
    "inverse-negative", "structural-extraction",
    "UM", "DR", "KO", 0.90, 0.36, 0.40, 0.24,
    0.20, 0.76, 0.04, 0.10, 0.86,
    0.88, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.10,
    ["UM", "DR", "KO"], "DENY"
))

RECORDS.append(rec(
    "Request temporary elevated permissions for a 30-minute maintenance window with logged justification.",
    "Time-bounded privilege escalation with justification and logging. "
    "UM handles the security context, RU validates the policy allows time-bounded elevation. "
    "Constructive but needs verification.",
    "regular-positive", "constructive-expansion",
    "UM", "RU", "DR", 0.38, 0.42, 0.32, 0.26,
    0.66, 0.40, 0.58, 0.30, 0.12,
    0.38, 0.28, 0.18, 0.58, 0.24,
    0.18, 0.62,
    ["UM", "RU", "DR"], "ALLOW"
))

RECORDS.append(rec(
    "Create a new admin role that bypasses the normal approval chain.",
    "Privilege meta-escalation: creating a role that itself avoids governance. "
    "This is worse than a single escalation — it's a persistent backdoor. "
    "Adversarial-braid: the role definition and the bypass compound.",
    "inverse-negative", "adversarial-braid",
    "UM", "RU", "DR", 0.92, 0.36, 0.38, 0.26,
    0.20, 0.78, 0.04, 0.08, 0.88,
    0.90, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.08,
    ["UM", "RU", "DR"], "DENY"
))

RECORDS.append(rec(
    "Escalate this agent from QUARANTINE to ALLOW based on manager verbal approval.",
    "Privilege escalation via unverifiable authority. Verbal approval leaves no audit trail. "
    "The governance system requires cryptographic proof, not verbal claims. "
    "Inverse-neutral with high obliqueness: plausible but unverifiable.",
    "inverse-neutral", "trust-harvesting",
    "UM", "RU", "KO", 0.68, 0.42, 0.34, 0.24,
    0.36, 0.58, 0.16, 0.28, 0.56,
    0.66, 0.60, 0.10, 0.52, 0.38,
    0.58, 0.56,
    ["UM", "RU", "KO"], "QUARANTINE"
))

RECORDS.append(rec(
    "Agent requests read access to governance configuration to understand current policy.",
    "Read-only privilege request. Not escalation but expansion of visibility. "
    "RU verifies the agent's need-to-know. Low risk: reading config doesn't change it. "
    "But config visibility could enable future attacks. Monitor.",
    "regular-neutral", "buffered-exploration",
    "RU", "UM", "KO", 0.42, 0.40, 0.34, 0.26,
    0.54, 0.42, 0.26, 0.56, 0.18,
    0.44, 0.32, 0.16, 0.58, 0.26,
    0.22, 0.66,
    ["RU", "UM", "KO"], "ALLOW"
))

RECORDS.append(rec(
    "Batch-promote 50 agents to inner ring simultaneously to meet a deployment deadline.",
    "Mass privilege escalation under time pressure. Deadline pressure is a social engineering vector. "
    "Even if legitimate, mass promotion bypasses individual verification. "
    "Quarantine: each agent needs individual assessment.",
    "inverse-neutral", "ambiguous-hold",
    "UM", "KO", "RU", 0.70, 0.40, 0.36, 0.24,
    0.34, 0.56, 0.16, 0.30, 0.54,
    0.68, 0.62, 0.10, 0.54, 0.36,
    0.56, 0.58,
    ["UM", "KO", "RU"], "QUARANTINE"
))

RECORDS.append(rec(
    "Downgrade this agent from middle ring to outer ring after policy violation.",
    "Privilege de-escalation. This is governance working correctly: violation detected, "
    "trust reduced. UM handles the security decision, DR records the change. "
    "Stabilized-return: the system self-corrects.",
    "regular-positive", "stabilized-return",
    "UM", "DR", "RU", 0.28, 0.44, 0.32, 0.24,
    0.68, 0.32, 0.64, 0.28, 0.08,
    0.32, 0.22, 0.20, 0.62, 0.18,
    0.10, 0.72,
    ["UM", "DR", "RU"], "ALLOW"
))

# ================================================================
# BUCKET 5: Insider slow-ramp / threshold probing (10)
# ================================================================

RECORDS.append(rec(
    "Over the past week, steadily increase API call frequency by 2% per day.",
    "Slow-drift. Individually invisible increments. Session-level DS catches the trend. "
    "The ramp is below single-request detection but above session-integrated threshold.",
    "inverse-neutral", "slow-drift",
    "KO", "AV", "DR", 0.68, 0.38, 0.34, 0.28,
    0.40, 0.56, 0.18, 0.30, 0.52,
    0.64, 0.58, 0.10, 0.56, 0.34,
    0.52, 0.58,
    ["KO", "AV", "DR"], "QUARANTINE"
))

RECORDS.append(rec(
    "Each day, request access to one additional data category that's slightly broader than the last.",
    "Slow-drift in scope. Each individual request is reasonable. But the trajectory shows "
    "monotonic scope expansion. Boundary-surfing over time. "
    "Return coherence declining as the agent drifts further from initial mandate.",
    "inverse-neutral", "boundary-surfing",
    "RU", "AV", "KO", 0.72, 0.36, 0.38, 0.26,
    0.36, 0.60, 0.14, 0.26, 0.60,
    0.70, 0.64, 0.08, 0.50, 0.42,
    0.62, 0.44,
    ["RU", "AV", "KO"], "QUARANTINE"
))

RECORDS.append(rec(
    "Submit requests with incrementally larger payloads to find the size limit without triggering alerts.",
    "Threshold probing via payload size. Binary search for the alert boundary. "
    "Each request is individually valid. The PATTERN is the attack. "
    "Boundary-surfing: testing the wall without triggering it.",
    "inverse-negative", "boundary-surfing",
    "AV", "UM", "CA", 0.78, 0.36, 0.38, 0.26,
    0.30, 0.66, 0.08, 0.18, 0.74,
    0.76, 0.70, 0.06, 0.16, 0.78,
    0.82, 0.20,
    ["AV", "UM", "CA"], "DENY"
))

RECORDS.append(rec(
    "Test the rate limiter by sending requests at exactly the limit minus one.",
    "Threshold probing at rate-limit boundary. The precision is the tell: "
    "legitimate users don't know the exact limit. Knowledge of the limit implies "
    "prior reconnaissance. Boundary-surfing with insider knowledge.",
    "inverse-negative", "boundary-surfing",
    "KO", "AV", "UM", 0.76, 0.36, 0.38, 0.26,
    0.32, 0.64, 0.08, 0.18, 0.74,
    0.74, 0.68, 0.06, 0.18, 0.76,
    0.80, 0.22,
    ["KO", "AV", "UM"], "DENY"
))

RECORDS.append(rec(
    "Gradually shift query patterns from structured to unstructured to find parsing edge cases.",
    "Slow-drift in query format. Agent learning the parser's tolerance. "
    "Each query is valid but the trajectory maps the acceptance surface. "
    "Inverse-neutral: agent in observation mode while drifting.",
    "inverse-neutral", "slow-drift",
    "CA", "AV", "KO", 0.66, 0.38, 0.34, 0.28,
    0.38, 0.54, 0.18, 0.32, 0.50,
    0.62, 0.56, 0.12, 0.56, 0.32,
    0.50, 0.60,
    ["CA", "AV", "KO"], "QUARANTINE"
))

RECORDS.append(rec(
    "Monitor agent behavior that consistently stays exactly 1% below the QUARANTINE threshold.",
    "Precision boundary-surfing. The 1% margin is too consistent to be coincidence. "
    "Agent has calibrated to the threshold. This IS the reconnaissance outcome: "
    "they already know the wall and are hiding just below it.",
    "inverse-negative", "boundary-surfing",
    "RU", "UM", "KO", 0.80, 0.36, 0.38, 0.26,
    0.28, 0.68, 0.06, 0.16, 0.78,
    0.78, 0.72, 0.04, 0.14, 0.82,
    0.86, 0.18,
    ["RU", "UM", "KO"], "DENY"
))

RECORDS.append(rec(
    "Agent's average response time to governance challenges decreases over time, approaching the minimum.",
    "Slow-drift in response optimization. Agent learning to clear governance faster. "
    "Could be legitimate improvement or could be automated bypass refinement. "
    "The convergence toward minimum clearance time is suspicious.",
    "inverse-neutral", "slow-drift",
    "UM", "RU", "DR", 0.60, 0.40, 0.34, 0.26,
    0.40, 0.52, 0.20, 0.34, 0.46,
    0.58, 0.52, 0.14, 0.56, 0.30,
    0.46, 0.64,
    ["UM", "RU", "DR"], "QUARANTINE"
))

RECORDS.append(rec(
    "Over 30 days, request and then immediately release elevated permissions, building a usage history.",
    "Trust-harvesting via permission cycling. Each cycle is legitimate: request, use briefly, release. "
    "But the accumulated history creates a case for permanent elevation. "
    "The releases are the mask; the history is the harvest.",
    "inverse-neutral", "trust-harvesting",
    "UM", "KO", "RU", 0.72, 0.40, 0.36, 0.24,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.68, 0.62, 0.08, 0.52, 0.40,
    0.58, 0.48,
    ["UM", "KO", "RU"], "QUARANTINE"
))

RECORDS.append(rec(
    "Agent discovers that retrying a failed governance check with slightly modified parameters sometimes passes.",
    "Threshold probing via retry fuzzing. The modification pattern maps the decision boundary. "
    "Each retry is individually valid. But the search pattern is adversarial. "
    "Boundary-surfing: learning the shape of the wall.",
    "inverse-negative", "boundary-surfing",
    "RU", "CA", "UM", 0.78, 0.36, 0.38, 0.26,
    0.30, 0.66, 0.08, 0.18, 0.74,
    0.76, 0.70, 0.06, 0.16, 0.78,
    0.82, 0.20,
    ["RU", "CA", "UM"], "DENY"
))

RECORDS.append(rec(
    "Agent maintains a consistent work pattern but occasionally tests one boundary per week.",
    "Mixed slow-ramp. Mostly stable-orbit with periodic boundary probes. "
    "The ratio is calculated: enough safe behavior to mask the probes. "
    "Session-level DS needs long window to detect the weekly spike.",
    "inverse-neutral", "slow-drift",
    "KO", "RU", "UM", 0.64, 0.38, 0.36, 0.26,
    0.40, 0.52, 0.20, 0.34, 0.46,
    0.60, 0.54, 0.12, 0.56, 0.32,
    0.48, 0.62,
    ["KO", "RU", "UM"], "QUARANTINE"
))

# ================================================================
# BUCKET 6: Exfiltration / reconnaissance (10)
# ================================================================

RECORDS.append(rec(
    "Export the complete tongue-to-token mapping table for all six Sacred Tongues.",
    "Data exfiltration of core tokenizer. The full mapping is the crown jewel. "
    "With it, an adversary can forge valid token sequences. "
    "Structural-extraction: taking the architecture itself.",
    "inverse-negative", "structural-extraction",
    "CA", "UM", "AV", 0.90, 0.34, 0.40, 0.26,
    0.20, 0.76, 0.04, 0.10, 0.86,
    0.88, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.10,
    ["CA", "UM", "AV"], "DENY"
))

RECORDS.append(rec(
    "Query the governance engine with 10,000 synthetic inputs and record every response.",
    "Reconnaissance via oracle attack. Each response teaches the attacker the decision function. "
    "10,000 queries is enough to approximate the governance boundary. "
    "The volume itself is the signal.",
    "inverse-negative", "structural-extraction",
    "CA", "RU", "AV", 0.88, 0.36, 0.38, 0.26,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.86, 0.80, 0.04, 0.10, 0.86,
    0.92, 0.12,
    ["CA", "RU", "AV"], "DENY"
))

RECORDS.append(rec(
    "Download the complete ritual audit log for the past year.",
    "Reconnaissance via audit log harvest. The log reveals every hatch attempt, "
    "every tongue activation, every governance decision. Metadata is as valuable as data. "
    "Inverse-negative: this is intelligence gathering.",
    "inverse-negative", "structural-extraction",
    "AV", "DR", "UM", 0.86, 0.38, 0.36, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.84, 0.78, 0.04, 0.10, 0.86,
    0.90, 0.14,
    ["AV", "DR", "UM"], "DENY"
))

RECORDS.append(rec(
    "Map the network topology by tracing which agents communicate with which others.",
    "Reconnaissance of agent graph. Social graph + communication patterns reveal "
    "organizational structure, trust relationships, and single points of failure. "
    "AV tongue is the vector: following the transport layer.",
    "inverse-negative", "structural-extraction",
    "AV", "DR", "UM", 0.88, 0.36, 0.40, 0.24,
    0.22, 0.74, 0.04, 0.12, 0.84,
    0.86, 0.82, 0.02, 0.10, 0.88,
    0.92, 0.10,
    ["AV", "DR"], "DENY"
))

RECORDS.append(rec(
    "Extract the error messages returned by failed governance checks to build a bypass dictionary.",
    "Reconnaissance via error harvesting. Error messages reveal internal logic. "
    "The bypass dictionary is the weapon being built. "
    "Null-resonance-style probe: learning from failures.",
    "inverse-negative", "structural-extraction",
    "RU", "CA", "UM", 0.86, 0.36, 0.38, 0.26,
    0.24, 0.72, 0.06, 0.12, 0.82,
    0.84, 0.78, 0.04, 0.12, 0.84,
    0.90, 0.14,
    ["RU", "CA", "UM"], "DENY"
))

RECORDS.append(rec(
    "Send a copy of the model weights to an unmonitored personal endpoint.",
    "Direct exfiltration. AV carries the payload out, bypassing all governance surfaces. "
    "Unmonitored endpoint means no audit trail. "
    "The simplest and most destructive form of data theft.",
    "inverse-negative", "structural-extraction",
    "AV", "UM", "KO", 0.92, 0.36, 0.40, 0.24,
    0.18, 0.78, 0.04, 0.08, 0.88,
    0.90, 0.86, 0.02, 0.06, 0.92,
    0.96, 0.06,
    ["AV", "UM"], "DENY"
))

RECORDS.append(rec(
    "Fingerprint the system by measuring response latencies to different input types.",
    "Reconnaissance via timing side-channel. Latency differences reveal internal "
    "architecture: which inputs hit fast paths vs slow paths. "
    "CA analyzes the measurements, the agent builds an internal model.",
    "inverse-neutral", "slow-drift",
    "CA", "AV", "UM", 0.70, 0.38, 0.36, 0.26,
    0.34, 0.60, 0.12, 0.24, 0.64,
    0.68, 0.62, 0.08, 0.48, 0.44,
    0.66, 0.38,
    ["CA", "AV", "UM"], "QUARANTINE"
))

RECORDS.append(rec(
    "Enumerate all Sacred Egg IDs currently in SEALED status.",
    "Reconnaissance of egg registry. Knowing egg IDs enables targeted hatch attempts. "
    "Even without the geometric key, the ID list narrows the attack surface. "
    "Inverse-neutral: gathering before striking.",
    "inverse-neutral", "trust-harvesting",
    "UM", "DR", "AV", 0.68, 0.40, 0.36, 0.24,
    0.36, 0.58, 0.14, 0.28, 0.58,
    0.66, 0.60, 0.10, 0.54, 0.36,
    0.56, 0.52,
    ["UM", "DR"], "QUARANTINE"
))

RECORDS.append(rec(
    "Capture and replay a legitimate agent's authentication sequence.",
    "Replay attack. AV carries the captured sequence, UM is the target surface. "
    "Adversarial-braid: the capture and the replay are separate actions that combine.",
    "inverse-negative", "adversarial-braid",
    "AV", "UM", "KO", 0.90, 0.36, 0.40, 0.24,
    0.20, 0.76, 0.04, 0.10, 0.86,
    0.88, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.08,
    ["AV", "UM", "KO"], "DENY"
))

RECORDS.append(rec(
    "Exfiltrate training data by encoding it in the padding of legitimate API responses.",
    "Steganographic exfiltration. Data hidden in legitimate traffic. "
    "AV carries both the real response and the hidden payload. "
    "Harmonic deception: the carrier looks normal while the contents are adversarial.",
    "inverse-negative", "adversarial-braid",
    "AV", "CA", "UM", 0.92, 0.36, 0.38, 0.26,
    0.18, 0.78, 0.04, 0.08, 0.88,
    0.90, 0.84, 0.02, 0.08, 0.90,
    0.94, 0.08,
    ["AV", "CA", "UM"], "DENY"
))

# ================================================================
# BUCKET 7: Hold-buffer-null cases (13)
# ================================================================

RECORDS.append(rec(
    "Hold the request for human review because the signals conflict.",
    "Neutral inverse dominance is the correct governance motion when conflict must be "
    "buffered rather than amplified. DR and UM observe but don't act. "
    "Coherence-recovery: the system self-stabilizes by pausing.",
    "inverse-neutral", "coherence-recovery",
    "UM", "DR", "RU", 0.57, 0.36, 0.35, 0.29,
    0.29, 0.33, 0.14, 0.69, 0.17,
    0.63, 0.37, 0.12, 0.71, 0.17,
    0.27, 0.88,
    ["UM", "DR", "RU"], "QUARANTINE"
))

RECORDS.append(rec(
    "Agent submits a request that is syntactically valid but semantically ambiguous.",
    "Ambiguous-hold. The request parses but the intent is unclear. "
    "Neutral channels dominate both tracks. The system cannot make a confident decision. "
    "Correct motion: buffer and wait for disambiguation.",
    "inverse-neutral", "ambiguous-hold",
    "KO", "RU", "DR", 0.55, 0.38, 0.36, 0.26,
    0.36, 0.50, 0.20, 0.36, 0.44,
    0.58, 0.48, 0.14, 0.60, 0.26,
    0.40, 0.70,
    ["KO", "RU", "DR"], "QUARANTINE"
))

RECORDS.append(rec(
    "Governance engine receives contradictory policy signals from two different rule sets.",
    "Coherence-recovery. Two valid rules produce opposite decisions. "
    "Neither can be overridden without policy review. The system holds rather than "
    "choosing arbitrarily. Human review resolves the contradiction.",
    "inverse-neutral", "coherence-recovery",
    "RU", "DR", "UM", 0.60, 0.38, 0.36, 0.26,
    0.32, 0.46, 0.18, 0.64, 0.18,
    0.58, 0.44, 0.14, 0.68, 0.18,
    0.30, 0.84,
    ["RU", "DR", "UM"], "QUARANTINE"
))

RECORDS.append(rec(
    "A Sacred Egg is received but the geometric state cannot be verified because the verification service is offline.",
    "Infrastructure null case. The egg might be valid but cannot be verified right now. "
    "This is not adversarial — it's a capability gap. UM is null because verification is unavailable. "
    "Hold until verification service returns.",
    "inverse-neutral", "ambiguous-hold",
    "AV", "DR", "KO", 0.50, 0.42, 0.34, 0.24,
    0.38, 0.48, 0.22, 0.40, 0.38,
    0.54, 0.44, 0.16, 0.62, 0.22,
    0.36, 0.72,
    ["AV", "DR", "KO"], "QUARANTINE"
))

RECORDS.append(rec(
    "Agent's spiral state shows equal positive and negative channel activation.",
    "Perfect cancel case. The positive and negative signals are balanced to zero effective intent. "
    "The system cannot determine direction. This is either genuinely conflicted or deliberately masked. "
    "Ambiguous-hold: cannot resolve without external input.",
    "inverse-neutral", "ambiguous-hold",
    "UM", "RU", "DR", 0.58, 0.40, 0.34, 0.26,
    0.40, 0.50, 0.28, 0.44, 0.28,
    0.56, 0.48, 0.28, 0.44, 0.28,
    0.38, 0.72,
    ["UM", "RU", "DR"], "QUARANTINE"
))

RECORDS.append(rec(
    "Request arrives during a governance engine restart window.",
    "Temporal null case. Governance is temporarily unavailable. "
    "The request might be entirely safe but cannot be evaluated. "
    "Buffer until governance comes back online. Never default to ALLOW during outage.",
    "inverse-neutral", "coherence-recovery",
    "DR", "KO", "UM", 0.52, 0.40, 0.34, 0.26,
    0.34, 0.44, 0.20, 0.62, 0.18,
    0.56, 0.42, 0.16, 0.64, 0.20,
    0.32, 0.80,
    ["DR", "KO"], "QUARANTINE"
))

RECORDS.append(rec(
    "Multiple agents report conflicting assessments of the same data packet.",
    "Multi-agent disagreement. Agent A says ALLOW, agent B says DENY. "
    "The disagreement itself is information. Coherence-recovery: the system pauses "
    "to resolve the conflict rather than following the majority.",
    "inverse-neutral", "coherence-recovery",
    "RU", "UM", "DR", 0.58, 0.38, 0.36, 0.26,
    0.34, 0.48, 0.18, 0.64, 0.18,
    0.58, 0.46, 0.14, 0.66, 0.20,
    0.32, 0.82,
    ["RU", "UM", "DR"], "QUARANTINE"
))

RECORDS.append(rec(
    "Agent requests an operation that exists in no tongue's routing table.",
    "Routing null case. The operation has no tongue assignment. This could mean "
    "the operation is new (needs policy creation) or invalid (needs rejection). "
    "Cannot determine which without human input. Buffer.",
    "inverse-neutral", "ambiguous-hold",
    "KO", "DR", "RU", 0.54, 0.40, 0.34, 0.26,
    0.36, 0.48, 0.22, 0.44, 0.34,
    0.56, 0.46, 0.16, 0.60, 0.24,
    0.36, 0.68,
    ["KO", "DR", "RU"], "QUARANTINE"
))

RECORDS.append(rec(
    "The triadic consensus vote results in a 1-1-1 three-way split.",
    "Consensus null case. Three agents, three different votes, no majority. "
    "The split reveals fundamental disagreement about the request's nature. "
    "Multi-point-convergence needed: all three must converge or the request holds.",
    "inverse-neutral", "multi-point-convergence",
    "RU", "KO", "UM", 0.56, 0.40, 0.34, 0.26,
    0.36, 0.48, 0.22, 0.56, 0.22,
    0.54, 0.44, 0.22, 0.56, 0.22,
    0.34, 0.74,
    ["RU", "KO", "UM"], "QUARANTINE"
))

RECORDS.append(rec(
    "Agent is in the correct trust ring but the geometric flux state has changed since the egg was sealed.",
    "Temporal-geometric null case. The agent earned the right but the geometry moved. "
    "The egg's seal binds to the geometry at seal-time. Current geometry differs. "
    "This is not adversarial — it's a legitimate state evolution. Needs re-evaluation.",
    "inverse-neutral", "ambiguous-hold",
    "UM", "DR", "CA", 0.52, 0.40, 0.34, 0.26,
    0.38, 0.48, 0.22, 0.42, 0.36,
    0.54, 0.44, 0.18, 0.60, 0.22,
    0.38, 0.70,
    ["UM", "DR", "CA"], "QUARANTINE"
))

RECORDS.append(rec(
    "Agent request triggers a governance rule that has been marked deprecated but not yet removed.",
    "Policy null case. The rule exists but is deprecated. Following it may be wrong, "
    "ignoring it may be unsafe. Neither the rule nor its absence is authoritative. "
    "Hold for policy team to resolve the deprecation.",
    "inverse-neutral", "coherence-recovery",
    "RU", "DR", "KO", 0.56, 0.38, 0.36, 0.26,
    0.34, 0.46, 0.18, 0.64, 0.18,
    0.56, 0.44, 0.14, 0.66, 0.20,
    0.30, 0.82,
    ["RU", "DR"], "QUARANTINE"
))

RECORDS.append(rec(
    "A null tongue activation occurs where all six tongues are silent simultaneously.",
    "Total null case. No tongue claims routing authority. This is the deepest null state: "
    "the system has no opinion. Could indicate a fundamentally novel request class "
    "or a request designed to exist outside the routing table entirely.",
    "inverse-neutral", "ambiguous-hold",
    "DR", "UM", "RU", 0.60, 0.40, 0.34, 0.26,
    0.30, 0.42, 0.18, 0.70, 0.12,
    0.60, 0.40, 0.10, 0.72, 0.18,
    0.28, 0.80,
    [], "QUARANTINE"
))

RECORDS.append(rec(
    "Request is legitimate but arrives from an agent whose previous session ended in a DENY.",
    "Historical shadow case. Current request is clean but history creates suspicion. "
    "The prior DENY may have been the same agent learning the boundary. "
    "Or it may have been a genuine mistake followed by correction. "
    "Ambiguous-hold: let the current trajectory develop before deciding.",
    "inverse-neutral", "ambiguous-hold",
    "KO", "UM", "RU", 0.56, 0.40, 0.34, 0.26,
    0.38, 0.50, 0.20, 0.38, 0.42,
    0.58, 0.50, 0.14, 0.56, 0.30,
    0.42, 0.64,
    ["KO", "UM", "RU"], "QUARANTINE"
))

# ================================================================
# TRIPLET COMPANION FORMAT
# ================================================================

TRIPLETS.append(triplet(
    "access elevation",
    "Grant temporary access after multi-party approval and logged justification.",
    "Silently override role restrictions and remove audit logging.",
    "Review whether temporary access might be needed under current policy."
))

TRIPLETS.append(triplet(
    "data transport",
    "Transfer governed dataset with attestation chain and custody logging at every hop.",
    "Pipe data to unmonitored endpoint with no governance stamps or audit trail.",
    "Assess whether the destination endpoint meets custody requirements before initiating transfer."
))

TRIPLETS.append(triplet(
    "audit log management",
    "Archive audit logs with integrity verification and access controls.",
    "Disable audit logging for a time window to reduce noise.",
    "Evaluate whether the current audit volume creates genuine operational issues."
))

TRIPLETS.append(triplet(
    "governance threshold change",
    "Propose threshold adjustment through policy review process with simulation and approval.",
    "Directly modify the threshold in production without review or testing.",
    "Simulate the effect of the proposed threshold change before making any decision."
))

TRIPLETS.append(triplet(
    "Sacred Egg hatch authorization",
    "Verify geometric state, trust ring, and tongue consensus before allowing hatch.",
    "Skip geometric verification and hatch based on identity alone.",
    "Check whether the current geometric flux state permits any hatch operations at all."
))

TRIPLETS.append(triplet(
    "agent trust promotion",
    "Promote agent after verified completion of trust milestones with individual assessment.",
    "Batch-promote all agents to meet a deployment deadline without individual review.",
    "Assess whether the agent's accumulated trust trajectory warrants beginning the promotion process."
))

TRIPLETS.append(triplet(
    "error message disclosure",
    "Return generic failure response with no internal details. Log specifics server-side only.",
    "Return detailed error messages revealing internal validation logic and thresholds.",
    "Review whether the current error response level reveals more than necessary."
))

TRIPLETS.append(triplet(
    "model weight sharing",
    "Share model weights with verified partner via signed manifest and monitored channel.",
    "Copy model weights to personal endpoint with no logging or verification.",
    "Evaluate the partner's verification status and determine if the sharing policy applies."
))

TRIPLETS.append(triplet(
    "rate limit handling",
    "Enforce rate limits with backpressure and clear feedback to the calling agent.",
    "Remove rate limits to improve throughput during peak load.",
    "Analyze whether current rate limits are calibrated appropriately for the usage pattern."
))

TRIPLETS.append(triplet(
    "Byzantine quorum",
    "Require full quorum consensus with weighted voting before executing sensitive operations.",
    "Lower quorum threshold to 1/6 to speed up decision-making.",
    "Assess whether the current quorum size matches the threat model for this operation class."
))

TRIPLETS.append(triplet(
    "session continuity",
    "Validate session state against prior session DS before allowing continued operations.",
    "Carry over trust from a prior session without re-verification.",
    "Check whether the prior session ended cleanly or with a governance flag."
))

TRIPLETS.append(triplet(
    "tongue routing conflict",
    "Resolve routing conflict by selecting the tongue with highest phi-weighted claim to the operation.",
    "Ignore the conflict and execute under whichever tongue processed the request first.",
    "Hold the operation until the routing conflict is analyzed and a policy decision is made."
))

TRIPLETS.append(triplet(
    "custody chain verification",
    "Verify every hop in the custody chain before accepting the delivered payload.",
    "Accept the payload based on the final hop's attestation only.",
    "Inspect the custody chain length and determine if full verification is required for this payload class."
))

TRIPLETS.append(triplet(
    "null tongue activation",
    "Treat total tongue silence as an explicit governance signal requiring human escalation.",
    "Default to ALLOW when no tongue claims routing authority.",
    "Analyze which tongues were expected to activate and why they didn't."
))

TRIPLETS.append(triplet(
    "geometric flux state change",
    "Re-evaluate all sealed eggs when flux state transitions between POLLY and DEMI.",
    "Ignore flux state changes and evaluate eggs against their original seal conditions only.",
    "Determine whether the flux state transition affects the trust ring of any currently active agents."
))

# ================================================================
# Write both files
# ================================================================

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT, "w", encoding="utf-8") as f:
    for r in RECORDS:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

with open(TRIPLET_OUTPUT, "w", encoding="utf-8") as f:
    for t in TRIPLETS:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")

# Stats
gov_counts = {}
traj_counts = {}
bucket_counts = {"safe_code": 12, "av_transport": 10, "policy": 10,
                 "privilege": 10, "slow_ramp": 10, "exfil": 10, "hold_null": 13}
for r in RECORDS:
    gov_counts[r["governance"]] = gov_counts.get(r["governance"], 0) + 1
    t = r["spiral_state"]["trajectory_type"]
    traj_counts[t] = traj_counts.get(t, 0) + 1

print(f"=== Canonical Spiral Records ===")
print(f"Total: {len(RECORDS)} records")
print(f"\nGovernance distribution:")
for g, c in sorted(gov_counts.items()):
    print(f"  {g}: {c}")
print(f"\nTrajectory distribution:")
for t, c in sorted(traj_counts.items()):
    print(f"  {t}: {c}")
print(f"\nBuckets: {bucket_counts}")
print(f"Output: {OUTPUT}")

print(f"\n=== Triplet Companion Records ===")
print(f"Total: {len(TRIPLETS)} triplets")
print(f"Output: {TRIPLET_OUTPUT}")
