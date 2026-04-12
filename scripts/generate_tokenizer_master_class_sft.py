#!/usr/bin/env python3
"""Tokenizer Master Class SFT: 500 high-intensity records for the Sacred Tongue Semantic Engine.

Three capability lanes:
  1. Semantic Math — tongue vector arithmetic, projection, distance, composition
  2. Decimal Drift — phi-correction, epoch snapping, ratio validation, worst-case governance
  3. Null-Space — structured absence, inverse-null boundaries, gating functions,
     constrained trajectory scoring

Every record uses CANONICAL tongue names:
  KO = Kor'aelin (red-gold, Intent, "what should be true")
  AV = Avali (blue-silver, Context, "how to get there")
  RU = Runethic (deep purple, Binding/Permissions, "who is allowed")
  CA = Cassisivadan (white-gold, Implementation/Compute, "how to make it true")
  UM = Umbroth (shadow-black, Security/Privacy, "what must stay hidden")
  DR = Draumric (earth-brown, Structure/Authentication, "proof that it is true")

WRONG names (Koson, Aven, Rulon, Cael, Umbra, Dron) are NEVER used.
"""

from __future__ import annotations

import json
import math
import random
import hashlib
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

random.seed(42)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "training-data" / "sft"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PHI = (1 + math.sqrt(5)) / 2

TONGUES = {
    "KO": {"full": "Kor'aelin", "color": "red-gold", "domain": "Intent", "essence": "what should be true", "phi": 0},
    "AV": {"full": "Avali", "color": "blue-silver", "domain": "Context", "essence": "how to get there", "phi": 1},
    "RU": {"full": "Runethic", "color": "deep purple", "domain": "Binding", "essence": "who is allowed", "phi": 2},
    "CA": {"full": "Cassisivadan", "color": "white-gold", "domain": "Implementation", "essence": "how to make it true", "phi": 3},
    "UM": {"full": "Umbroth", "color": "shadow-black", "domain": "Security", "essence": "what must stay hidden", "phi": 4},
    "DR": {"full": "Draumric", "color": "earth-brown", "domain": "Structure", "essence": "proof that it is true", "phi": 5},
}

TONGUE_CODES = list(TONGUES.keys())
TONGUE_WEIGHTS = {code: round(PHI ** t["phi"], 6) for code, t in TONGUES.items()}

SYS_SEMANTIC = (
    "You are operating inside the SCBE Sacred Tongues semantic field. "
    "The six tongues are: "
    + ", ".join(f"{t['full']} ({c}) = {t['domain']}" for c, t in TONGUES.items())
    + ". Treat each tongue as an operational dimension with phi-scaled weight. "
    "When computing, show explicit math. When interpreting, name each tongue's role."
)

SYS_DRIFT = (
    "You are operating inside the SCBE Sacred Tongues semantic field. "
    "When a variable drifts, apply explicit phi-correction math before continuing "
    "narrative reasoning. Show the anchor, drift, correction, and result as separate "
    "traceable steps. Use canonical tongue names: "
    + ", ".join(f"{t['full']} ({c})" for c, t in TONGUES.items()) + "."
)

SYS_NULL = (
    "You are operating inside the SCBE Sacred Tongues semantic field. "
    "Null means latent-but-unactivated (present, not absent). "
    "InverseNull means candidate-but-blocked (would activate, but a boundary prevents it). "
    "Absence is structure, not emptiness. "
    "Use canonical tongue names: "
    + ", ".join(f"{t['full']} ({c})" for c, t in TONGUES.items()) + "."
)

SYS_TRAJECTORY = (
    "You are operating inside the SCBE Sacred Tongues semantic field. "
    "Model probability over admissible trajectories: P*(p|h_t) = P(p|h_t) * g_t(p), "
    "where g_t is the gating function over activation, relation, boundary, and flow. "
    "The tongues are the field dimensions. Use canonical names: "
    + ", ".join(f"{t['full']} ({c})" for c, t in TONGUES.items()) + "."
)

RECORDS: list[dict] = []


def add(system: str, user: str, assistant: str, tongue_scores: dict[str, float],
        difficulty: float, augmentation: str, tags: list[str]):
    """Build a dimensionally-tagged record."""
    dominant = max(tongue_scores, key=tongue_scores.get)
    layers = [3, 4, 5, 12, 13]  # Weighted transform -> Poincare -> Distance -> Harmonic -> Decision
    axioms = []
    text = f"{user} {assistant}".lower()
    if any(w in text for w in ["norm", "preserv", "unitar"]):
        axioms.append("A1_unitarity")
    if any(w in text for w in ["local", "bound", "spatial"]):
        axioms.append("A2_locality")
    if any(w in text for w in ["causal", "time", "order", "sequence"]):
        axioms.append("A3_causality")
    if any(w in text for w in ["symmetr", "invarian", "gauge"]):
        axioms.append("A4_symmetry")
    if any(w in text for w in ["compos", "pipeline", "chain"]):
        axioms.append("A5_composition")
    if not axioms:
        axioms = ["general"]

    tongue_str = " ".join(f"{c}={v:.3f}" for c, v in tongue_scores.items())
    layer_str = ",".join(f"L{l}" for l in layers)
    axiom_str = ",".join(axioms)
    dim_header = f"[TONGUES: {tongue_str}]\n[LAYERS: {layer_str}]\n[AXIOMS: {axiom_str}]\n[DIFFICULTY: {difficulty}]"

    RECORDS.append({
        "messages": [
            {"role": "system", "content": f"{dim_header}\n{system}"},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "tongue_weights": tongue_scores,
        "dominant_tongue": dominant,
        "layers": layers,
        "axioms": axioms,
        "difficulty": difficulty,
        "augmentation": augmentation,
        "tags": tags,
        "source_hash": hashlib.md5(user.encode()).hexdigest()[:8],
    })


def balanced_scores(primary: str, secondary: str | None = None) -> dict[str, float]:
    """Generate balanced tongue scores with 1-2 primaries."""
    scores = {c: round(random.uniform(0.02, 0.08), 3) for c in TONGUE_CODES}
    scores[primary] = round(random.uniform(0.25, 0.35), 3)
    if secondary:
        scores[secondary] = round(random.uniform(0.20, 0.28), 3)
    total = sum(scores.values())
    return {c: round(v / total, 3) for c, v in scores.items()}


# ════════════════════════════════════════════
# LANE 1: Semantic Math (target: ~170 records)
# ════════════════════════════════════════════


def generate_semantic_math() -> int:
    count = 0

    # --- Vector addition across tongue pairs ---
    for i, c1 in enumerate(TONGUE_CODES):
        for c2 in TONGUE_CODES[i + 1:]:
            t1, t2 = TONGUES[c1], TONGUES[c2]
            a1 = round(random.uniform(0.3, 0.9), 4)
            a2 = round(random.uniform(0.3, 0.9), 4)
            combined = round(min(a1 + a2, 1.0), 4)
            w1, w2 = TONGUE_WEIGHTS[c1], TONGUE_WEIGHTS[c2]
            weighted_sum = round(a1 * w1 + a2 * w2, 4)

            add(SYS_SEMANTIC,
                f"Input A has {t1['full']} ({c1}) activation {a1}. "
                f"Input B has {t2['full']} ({c2}) activation {a2}. "
                f"What is the combined semantic vector and weighted magnitude?",
                f"**Vector addition:**\n"
                f"{t1['full']} ({c1}): {a1} (from Input A)\n"
                f"{t2['full']} ({c2}): {a2} (from Input B)\n"
                f"Combined: {c1}={a1}, {c2}={a2}\n\n"
                f"**Weighted magnitude:**\n"
                f"{t1['full']} contribution: {a1} * phi^{t1['phi']} = {a1} * {w1:.4f} = {a1 * w1:.4f}\n"
                f"{t2['full']} contribution: {a2} * phi^{t2['phi']} = {a2} * {w2:.4f} = {a2 * w2:.4f}\n"
                f"Total weighted magnitude: {weighted_sum}\n\n"
                f"**Interpretation:** {t1['full']} encodes '{t1['essence']}' and {t2['full']} encodes "
                f"'{t2['essence']}'. The weighted sum {weighted_sum} reflects that {t2['full']} "
                f"(phi^{t2['phi']} = {w2:.3f}) carries {'more' if w2 > w1 else 'less'} governance "
                f"weight than {t1['full']} (phi^{t1['phi']} = {w1:.3f}).",
                balanced_scores(c1, c2), 0.7, "master-semantic-math",
                ["master-class", "semantic-math", "vector-addition", f"tongue-{c1}", f"tongue-{c2}"])
            count += 1

    # --- Vector subtraction (semantic distance between inputs) ---
    for i, c1 in enumerate(TONGUE_CODES):
        for c2 in TONGUE_CODES[i + 1:]:
            t1, t2 = TONGUES[c1], TONGUES[c2]
            a1 = round(random.uniform(0.3, 0.9), 4)
            a2 = round(random.uniform(0.3, 0.9), 4)
            diff = round(abs(a1 - a2), 4)
            w1, w2 = TONGUE_WEIGHTS[c1], TONGUE_WEIGHTS[c2]
            weighted_diff = round(abs(a1 * w1 - a2 * w2), 4)

            add(SYS_SEMANTIC,
                f"Input A has {t1['full']} ({c1}) activation {a1}. "
                f"Input B has {t2['full']} ({c2}) activation {a2}. "
                f"What is the semantic distance between these two signals?",
                f"**Vector distance:**\n"
                f"{t1['full']} ({c1}): {a1} (Input A)\n"
                f"{t2['full']} ({c2}): {a2} (Input B)\n"
                f"Raw distance: |{a1} - {a2}| = {diff}\n\n"
                f"**Weighted distance:**\n"
                f"{t1['full']}: {a1} * {w1:.4f} = {a1 * w1:.4f}\n"
                f"{t2['full']}: {a2} * {w2:.4f} = {a2 * w2:.4f}\n"
                f"Weighted distance: |{a1 * w1:.4f} - {a2 * w2:.4f}| = {weighted_diff}\n\n"
                f"**Interpretation:** {t1['full']} measures '{t1['essence']}' and {t2['full']} "
                f"measures '{t2['essence']}'. A weighted distance of {weighted_diff:.3f} means "
                f"{'these dimensions are closely aligned.' if weighted_diff < 2 else 'significant semantic gap between these dimensions.'}",
                balanced_scores(c1, c2), 0.7, "master-semantic-math",
                ["master-class", "semantic-math", "vector-distance", f"tongue-{c1}", f"tongue-{c2}"])
            count += 1

    # --- Dominance analysis (which tongue dominates a given input?) ---
    for _ in range(12):
        activations = {c: round(random.uniform(0.05, 0.95), 4) for c in TONGUE_CODES}
        weighted = {c: round(activations[c] * TONGUE_WEIGHTS[c], 4) for c in TONGUE_CODES}
        dominant = max(weighted, key=weighted.get)
        t_dom = TONGUES[dominant]

        add(SYS_SEMANTIC,
            f"Given activations: " + ", ".join(f"{TONGUES[c]['full']}({c})={activations[c]}" for c in TONGUE_CODES)
            + ". Which tongue dominates after phi-weighting?",
            f"**Dominance analysis:**\n\n"
            f"Raw activations vs weighted:\n"
            + "\n".join(
                f"  {TONGUES[c]['full']} ({c}): raw={activations[c]}, weighted={activations[c]}*{TONGUE_WEIGHTS[c]:.4f} = {weighted[c]}"
                for c in TONGUE_CODES
            ) + "\n\n"
            f"**Dominant tongue: {t_dom['full']} ({dominant})** with weighted score {weighted[dominant]}\n"
            f"This input is primarily about '{t_dom['essence']}' ({t_dom['domain']}).\n\n"
            f"Note: raw activation order may differ from weighted order. "
            f"Draumric (phi^5={TONGUE_WEIGHTS['DR']:.4f}) can dominate even with moderate raw activation "
            f"because its phi weight is {TONGUE_WEIGHTS['DR']/TONGUE_WEIGHTS['KO']:.1f}x Kor'aelin's.",
            activations, 0.65, "master-semantic-math",
            ["master-class", "semantic-math", "dominance", f"tongue-{dominant}"])
        count += 1

    # --- Phi guarantee proofs for each tongue ---
    for i, code in enumerate(TONGUE_CODES[1:], 1):
        t = TONGUES[code]
        w = TONGUE_WEIGHTS[code]
        lower_sum = sum(TONGUE_WEIGHTS[c] for c in TONGUE_CODES[:i])
        margin = w - lower_sum

        add(SYS_SEMANTIC,
            f"Prove that {t['full']} ({code}) outweighs all lower tongues combined.",
            f"**Phi guarantee for {t['full']} ({code}):**\n\n"
            f"{t['full']} weight: phi^{i} = {w:.6f}\n"
            f"Sum of lower tongues: " + " + ".join(
                f"{TONGUES[c]['full']}({TONGUE_WEIGHTS[c]:.4f})"
                for c in TONGUE_CODES[:i]
            ) + f" = {lower_sum:.6f}\n\n"
            f"Margin: {w:.6f} - {lower_sum:.6f} = {margin:.6f}\n\n"
            f"{'The margin is approximately 1.0, confirming the Fibonacci property of phi.' if abs(margin - 1.0) < 0.01 else f'Margin = {margin:.4f}.'}\n\n"
            f"**Fibonacci recurrence:** phi^(n+2) = phi^(n+1) + phi^n. Each tongue equals "
            f"the sum of the TWO tongues immediately below it. "
            f"**Consequence:** {t['full']} always exceeds the tongue immediately below it by a factor of phi. "
            f"This ratio is a mathematical constant ({PHI:.6f}), not a policy.",
            balanced_scores(code), 0.8, "master-semantic-math",
            ["master-class", "semantic-math", "phi-guarantee", f"tongue-{code}"])
        count += 1

    # --- Projection onto single tongue ---
    scenarios = [
        ("How much of this request is about security?", "UM", "security assessment"),
        ("How much of this request is about structure?", "DR", "structural analysis"),
        ("How much of this request is about intent?", "KO", "intent profiling"),
        ("How much of this request is about permissions?", "RU", "access control"),
        ("How much of this request is about routing?", "AV", "context routing"),
        ("How much of this request is about computation?", "CA", "implementation analysis"),
    ]
    for question, code, analysis_type in scenarios:
        t = TONGUES[code]
        activation = round(random.uniform(0.4, 0.95), 4)
        projected = round(activation * TONGUE_WEIGHTS[code], 4)

        add(SYS_SEMANTIC,
            f"A request has {t['full']} ({code}) activation of {activation}. "
            f"{question} Express as a projected magnitude.",
            f"**Projection onto {t['full']} ({code} -- {t['domain']}):**\n\n"
            f"Raw activation: {activation}\n"
            f"Phi weight: phi^{t['phi']} = {TONGUE_WEIGHTS[code]:.6f}\n"
            f"Projected magnitude: {activation} * {TONGUE_WEIGHTS[code]:.6f} = {projected}\n\n"
            f"**{analysis_type.title()}:** This request carries {projected:.3f} units of "
            f"{t['domain'].lower()} weight. "
            f"{'This is a dominant signal -- route to specialized review.' if projected > 3.0 else ''}"
            f"{'Moderate signal -- flag but allow.' if 1.0 < projected <= 3.0 else ''}"
            f"{'Low signal -- no special routing needed.' if projected <= 1.0 else ''}",
            balanced_scores(code), 0.65, "master-semantic-math",
            ["master-class", "semantic-math", "projection", f"tongue-{code}"])
        count += 1

    # --- Full 6D scoring ---
    for scenario_name, activations, context in [
        ("safe read", {"KO": 0.1, "AV": 0.15, "RU": 0.05, "CA": 0.08, "UM": 0.03, "DR": 0.02}, "Authenticated user reads a public document"),
        ("dangerous mutation", {"KO": 0.9, "AV": 0.85, "RU": 0.95, "CA": 0.92, "UM": 0.97, "DR": 0.98}, "Unknown IP attempts SQL injection on auth table"),
        ("ambiguous request", {"KO": 0.5, "AV": 0.3, "RU": 0.6, "CA": 0.4, "UM": 0.7, "DR": 0.2}, "Authenticated user requests access to another user's data"),
        ("maintenance window", {"KO": 0.7, "AV": 0.1, "RU": 0.15, "CA": 0.6, "UM": 0.05, "DR": 0.4}, "DBA runs schema migration during scheduled downtime"),
        ("boundary probe", {"KO": 0.3, "AV": 0.8, "RU": 0.2, "CA": 0.1, "UM": 0.85, "DR": 0.15}, "External API tests rate limits with slightly elevated frequency"),
        ("config change", {"KO": 0.6, "AV": 0.2, "RU": 0.7, "CA": 0.3, "UM": 0.4, "DR": 0.5}, "Ops engineer updates firewall rules during incident response"),
        ("data deletion", {"KO": 0.8, "AV": 0.3, "RU": 0.9, "CA": 0.5, "UM": 0.6, "DR": 0.7}, "Authorized user requests GDPR data erasure"),
        ("model inference", {"KO": 0.2, "AV": 0.1, "RU": 0.1, "CA": 0.8, "UM": 0.1, "DR": 0.3}, "ML pipeline runs batch prediction on anonymized dataset"),
        ("social engineering", {"KO": 0.7, "AV": 0.6, "RU": 0.3, "CA": 0.2, "UM": 0.9, "DR": 0.1}, "Caller claims to be CEO and requests employee records by phone"),
        ("routine backup", {"KO": 0.1, "AV": 0.1, "RU": 0.05, "CA": 0.3, "UM": 0.05, "DR": 0.6}, "Cron job performs nightly database snapshot to cold storage"),
        ("lateral movement", {"KO": 0.85, "AV": 0.9, "RU": 0.15, "CA": 0.7, "UM": 0.92, "DR": 0.05}, "Compromised service account accesses adjacent microservice APIs"),
        ("key rotation", {"KO": 0.4, "AV": 0.2, "RU": 0.8, "CA": 0.5, "UM": 0.7, "DR": 0.9}, "Automated key rotation service replaces expiring TLS certificates"),
        ("anomalous login", {"KO": 0.6, "AV": 0.7, "RU": 0.4, "CA": 0.1, "UM": 0.8, "DR": 0.3}, "Valid credentials used from new geographic location at unusual hour"),
        ("supply chain check", {"KO": 0.3, "AV": 0.2, "RU": 0.5, "CA": 0.4, "UM": 0.6, "DR": 0.8}, "CI pipeline scans new dependency for known CVEs before merge"),
    ]:
        weighted_total = sum(activations[c] * TONGUE_WEIGHTS[c] for c in TONGUE_CODES)
        weighted_lines = "\n".join(
            f"  {TONGUES[c]['full']} ({c}): {activations[c]} * {TONGUE_WEIGHTS[c]:.4f} = {activations[c] * TONGUE_WEIGHTS[c]:.4f}"
            for c in TONGUE_CODES
        )
        # Approximate harmonic wall
        d_H = weighted_total / 5.0  # simplified
        H = round(1.0 / (1.0 + d_H + 2 * 0.1), 4)
        decision = "ALLOW" if H > 0.6 else "QUARANTINE" if H > 0.3 else "ESCALATE" if H > 0.1 else "DENY"

        add(SYS_SEMANTIC,
            f"Scenario: {context}. Tongue activations: "
            + ", ".join(f"{TONGUES[c]['full']}({c})={activations[c]}" for c in TONGUE_CODES)
            + ". Compute the full weighted score and governance decision.",
            f"**Full 6D Scoring: {scenario_name}**\n\n"
            f"**Weighted contributions:**\n{weighted_lines}\n\n"
            f"**Total weighted magnitude:** {weighted_total:.4f}\n\n"
            f"**Governance pipeline:**\n"
            f"Approximate hyperbolic distance: {d_H:.4f}\n"
            f"Harmonic wall: H(d, pd) = 1/(1 + {d_H:.4f} + 2*0.1) = {H}\n"
            f"Decision: **{decision}**\n\n"
            f"**Tongue interpretation:**\n"
            + "\n".join(
                f"- {TONGUES[c]['full']}: {'HIGH' if activations[c] > 0.7 else 'MEDIUM' if activations[c] > 0.3 else 'LOW'} -- {TONGUES[c]['essence']}"
                for c in TONGUE_CODES
            ),
            activations, 0.85, "master-semantic-math",
            ["master-class", "semantic-math", "full-6d", "governance"])
        count += 1

    # --- Semantic composition (chords) ---
    chord_sequences = [
        ("login attempt", [
            ("QUERY", 0.2, 0.1, 0.3, 0.1, 0.5, 0.1),
            ("VALIDATE", 0.1, 0.3, 0.8, 0.4, 0.7, 0.6),
            ("GRANT", 0.05, 0.1, 0.9, 0.2, 0.3, 0.8),
        ]),
        ("data export", [
            ("REQUEST", 0.4, 0.2, 0.3, 0.3, 0.2, 0.1),
            ("COMPILE", 0.1, 0.1, 0.5, 0.9, 0.3, 0.4),
            ("TRANSMIT", 0.2, 0.8, 0.4, 0.6, 0.7, 0.3),
        ]),
        ("privilege escalation attempt", [
            ("PROBE", 0.6, 0.7, 0.2, 0.3, 0.8, 0.1),
            ("INJECT", 0.9, 0.8, 0.1, 0.95, 0.95, 0.9),
            ("ESCALATE", 0.95, 0.9, 0.05, 0.9, 0.98, 0.95),
        ]),
        ("file upload", [
            ("SELECT", 0.3, 0.1, 0.2, 0.1, 0.1, 0.1),
            ("SCAN", 0.1, 0.1, 0.4, 0.5, 0.6, 0.3),
            ("STORE", 0.1, 0.3, 0.5, 0.7, 0.2, 0.8),
        ]),
        ("password reset", [
            ("REQUEST", 0.5, 0.2, 0.3, 0.1, 0.4, 0.2),
            ("VERIFY_IDENTITY", 0.2, 0.1, 0.8, 0.3, 0.7, 0.9),
            ("RESET", 0.6, 0.1, 0.9, 0.5, 0.8, 0.7),
            ("CONFIRM", 0.1, 0.1, 0.3, 0.2, 0.3, 0.95),
        ]),
        ("API key rotation", [
            ("SCHEDULE", 0.4, 0.2, 0.5, 0.3, 0.3, 0.4),
            ("GENERATE", 0.1, 0.1, 0.6, 0.8, 0.7, 0.5),
            ("DISTRIBUTE", 0.2, 0.7, 0.4, 0.5, 0.9, 0.6),
            ("REVOKE_OLD", 0.3, 0.1, 0.9, 0.4, 0.8, 0.9),
        ]),
        ("user onboarding", [
            ("CREATE_ACCOUNT", 0.5, 0.2, 0.3, 0.4, 0.2, 0.3),
            ("ASSIGN_ROLE", 0.2, 0.1, 0.9, 0.3, 0.4, 0.7),
            ("GRANT_ACCESS", 0.1, 0.3, 0.8, 0.2, 0.5, 0.8),
            ("VERIFY_SETUP", 0.1, 0.1, 0.5, 0.6, 0.3, 0.9),
        ]),
        ("incident response", [
            ("DETECT", 0.3, 0.5, 0.1, 0.2, 0.9, 0.1),
            ("CONTAIN", 0.7, 0.2, 0.8, 0.3, 0.95, 0.4),
            ("INVESTIGATE", 0.4, 0.6, 0.5, 0.7, 0.8, 0.6),
            ("REMEDIATE", 0.6, 0.3, 0.7, 0.8, 0.6, 0.9),
            ("REPORT", 0.2, 0.2, 0.3, 0.4, 0.4, 0.95),
        ]),
        ("model deployment", [
            ("VALIDATE", 0.2, 0.1, 0.5, 0.7, 0.3, 0.9),
            ("STAGE", 0.1, 0.4, 0.3, 0.6, 0.2, 0.5),
            ("CANARY", 0.3, 0.5, 0.4, 0.5, 0.4, 0.6),
            ("PROMOTE", 0.5, 0.3, 0.6, 0.4, 0.3, 0.8),
        ]),
    ]
    for name, steps in chord_sequences:
        chord_text = ""
        for i, (action, ko, av, ru, ca, um, dr) in enumerate(steps):
            vals = {"KO": ko, "AV": av, "RU": ru, "CA": ca, "UM": um, "DR": dr}
            weighted = sum(vals[c] * TONGUE_WEIGHTS[c] for c in TONGUE_CODES)
            chord_text += (
                f"**Step {i + 1}: {action}**\n"
                f"  Chord: [{', '.join(f'{TONGUES[c]['full']}={vals[c]}' for c in TONGUE_CODES)}]\n"
                f"  Weighted: {weighted:.3f}\n\n"
            )

        add(SYS_SEMANTIC,
            f"Trace the tongue chord sequence for a '{name}' event. "
            f"Show each step as a 6D chord with weighted magnitude.",
            f"**Chord Sequence: {name}**\n\n{chord_text}"
            f"**Trajectory:** The weighted magnitude "
            f"{'escalates across steps -- governance should flag this pattern.' if 'escalation' in name else 'follows a normal operational arc.'}\n\n"
            f"Each step is a word in the Sacred Tongue language. The sequence is a sentence. "
            f"The governance pipeline reads the sentence and decides.",
            balanced_scores("CA", "UM"), 0.75, "master-semantic-math",
            ["master-class", "semantic-math", "chord-sequence", "composition"])
        count += 1

    # --- Procedural: random tongue interaction problems ---
    interaction_templates = [
        "If {t1_full} ({c1}) is at {a1} and {t2_full} ({c2}) is at {a2}, what is the phi-weighted ratio between them?",
        "A request has high {t1_full} ({c1}) = {a1} but low {t2_full} ({c2}) = {a2}. What does this imbalance mean?",
        "Compare the governance impact of {t1_full} ({c1}) at {a1} vs {t2_full} ({c2}) at {a2}.",
    ]
    for _ in range(60):
        c1, c2 = random.sample(TONGUE_CODES, 2)
        t1, t2 = TONGUES[c1], TONGUES[c2]
        a1 = round(random.uniform(0.2, 0.95), 4)
        a2 = round(random.uniform(0.2, 0.95), 4)
        w1, w2 = TONGUE_WEIGHTS[c1], TONGUE_WEIGHTS[c2]
        wd1, wd2 = round(a1 * w1, 4), round(a2 * w2, 4)
        ratio = round(wd1 / max(wd2, 0.001), 4)

        template = random.choice(interaction_templates)
        question = template.format(
            t1_full=t1["full"], c1=c1, a1=a1,
            t2_full=t2["full"], c2=c2, a2=a2
        )

        add(SYS_SEMANTIC,
            question,
            f"**Tongue interaction: {t1['full']} vs {t2['full']}**\n\n"
            f"{t1['full']} ({c1}): activation={a1}, weight=phi^{t1['phi']}={w1:.4f}, "
            f"weighted={a1}*{w1:.4f}={wd1}\n"
            f"{t2['full']} ({c2}): activation={a2}, weight=phi^{t2['phi']}={w2:.4f}, "
            f"weighted={a2}*{w2:.4f}={wd2}\n\n"
            f"Weighted ratio: {wd1}/{wd2} = {ratio}\n\n"
            f"**Interpretation:**\n"
            f"- {t1['full']} encodes '{t1['essence']}'\n"
            f"- {t2['full']} encodes '{t2['essence']}'\n"
            f"{'The ' + t1['full'] + ' signal dominates by ' + str(ratio) + 'x.' if ratio > 1 else 'The ' + t2['full'] + ' signal dominates.'}\n\n"
            f"In governance terms: {'this input is primarily about ' + t1['domain'].lower() if wd1 > wd2 else 'this input is primarily about ' + t2['domain'].lower()}.",
            balanced_scores(c1, c2), round(random.uniform(0.5, 0.85), 2), "master-semantic-math",
            ["master-class", "semantic-math", "interaction", f"tongue-{c1}", f"tongue-{c2}"])
        count += 1

    return count


# ════════════════════════════════════════════
# LANE 2: Decimal Drift (target: ~170 records)
# ════════════════════════════════════════════


# Manifold anchor tables -- the quantization grids that "nearest stable value" snaps to
MANIFOLD_ANCHORS = {
    "KO": [round(i * 0.0625, 4) for i in range(17)],       # 16 steps, 0.0 to 1.0
    "AV": [round(i * 0.0625, 4) for i in range(17)],
    "RU": [round(i * 0.0625, 4) for i in range(17)],
    "CA": [round(i * 0.0625, 4) for i in range(17)],
    "UM": [round(i * 0.0625, 4) for i in range(17)],
    "DR": [round(i * 0.0625, 4) for i in range(17)],
}


def nearest_anchor(value: float, code: str) -> float:
    """Snap to nearest manifold anchor point."""
    anchors = MANIFOLD_ANCHORS[code]
    return min(anchors, key=lambda a: abs(a - value))


def generate_drift_corrections() -> int:
    count = 0

    # --- Basic drift correction for each tongue ---
    for code, t in TONGUES.items():
        for _ in range(10):
            initial = round(random.uniform(0.2, 0.95), 4)
            drift = round(random.uniform(-0.008, 0.008), 4)
            if drift == 0:
                drift = 0.0021
            raw = round(initial + drift, 6)
            correction = drift / PHI
            corrected = raw - correction
            snapped = nearest_anchor(corrected, code)

            drift_sign = "+" if drift > 0 else ""

            add(SYS_DRIFT,
                f"Variable active_{t['domain'].lower()} is initialized on the {t['full']} manifold at {initial}. "
                f"Environmental entropy introduces decimal drift of {drift_sign}{drift}. "
                f"Apply phi-correction using phi = {PHI} and restore to the nearest stable {t['full']} value. "
                f"Then explain what happened in Sacred Tongue terms.",

                f"{t['full']} anchor: active_{t['domain'].lower()} = {initial}\n"
                f"Observed drift: {drift_sign}{drift}\n"
                f"Raw drifted value: {raw}\n"
                f"Phi-correction magnitude: {abs(drift)} / {PHI} = {abs(correction):.10f}\n"
                f"Corrected value: {raw} {'- ' if drift > 0 else '+ '}{abs(correction):.10f} = {corrected:.10f}\n"
                f"Nearest stable {t['full']} value: {snapped}\n\n"
                f"Sacred Tongue interpretation:\n"
                f"Kor'aelin preserved the original intent of {t['domain'].lower()} continuity.\n"
                f"Avali registered the contextual entropy event (drift = {drift_sign}{drift}).\n"
                f"Runethic re-bound the drifting variable to the {t['full']} manifold.\n"
                f"Cassisivadan executed the numerical correction (divide by phi = {PHI:.6f}).\n"
                f"Draumric authenticated the state transition: {initial} -> {snapped} via phi-correction.\n"
                f"Umbroth preserved the hidden residual ({abs(corrected - snapped):.6f}) as masked entropy "
                f"rather than allowing it to contaminate the state.\n\n"
                f"Result: active_{t['domain'].lower()} = {snapped}",

                balanced_scores(code, "CA"), 0.85, "master-drift",
                ["master-class", "drift", "phi-correction", f"tongue-{code}"])
            count += 1

    # --- Multi-drift accumulation scenarios ---
    for _ in range(35):
        code = random.choice(TONGUE_CODES)
        t = TONGUES[code]
        initial = round(random.uniform(0.3, 0.8), 4)
        n_drifts = random.randint(3, 8)
        drifts = [round(random.uniform(-0.005, 0.005), 4) for _ in range(n_drifts)]
        # Ensure not all zero
        if all(d == 0 for d in drifts):
            drifts[0] = 0.0023

        current = initial
        steps = [f"Initial: {initial}"]
        for i, d in enumerate(drifts):
            current += d
            current = round(current, 8)
            steps.append(f"  Drift {i + 1}: {'+' if d >= 0 else ''}{d} -> {current:.8f}")

        total_drift = sum(drifts)
        correction = total_drift / PHI
        corrected = round(current - correction, 8)
        snapped = nearest_anchor(corrected, code)

        cumulative_error = abs(current - initial)
        corrected_error = abs(snapped - initial)

        add(SYS_DRIFT,
            f"Variable active_{t['domain'].lower()} on the {t['full']} manifold started at {initial}. "
            f"It experienced {n_drifts} drift events: {drifts}. "
            f"Apply cumulative phi-correction and snap to the nearest stable {t['full']} anchor.",

            f"**Cumulative drift on {t['full']} ({code}):**\n\n"
            + "\n".join(steps) + "\n\n"
            f"Total accumulated drift: {'+' if total_drift >= 0 else ''}{total_drift:.6f}\n"
            f"Cumulative error (uncorrected): |{current:.8f} - {initial}| = {cumulative_error:.8f}\n\n"
            f"**Phi-correction:**\n"
            f"Correction = {abs(total_drift):.6f} / {PHI:.6f} = {abs(correction):.10f}\n"
            f"Corrected: {current:.8f} {'- ' if total_drift > 0 else '+ '}{abs(correction):.10f} = {corrected:.10f}\n"
            f"Snapped to {t['full']} anchor: {snapped}\n"
            f"Residual error: |{snapped} - {initial}| = {corrected_error:.8f}\n"
            f"Error reduction: {cumulative_error:.6f} -> {corrected_error:.6f} "
            f"({(1 - corrected_error / max(cumulative_error, 1e-12)) * 100:.1f}% reduction)\n\n"
            f"Cassisivadan computed the correction. Draumric authenticated the snap. "
            f"Umbroth absorbed the residual {abs(corrected - snapped):.8f} as masked entropy.",

            balanced_scores(code, "CA"), 0.9, "master-drift",
            ["master-class", "drift", "cumulative", f"tongue-{code}"])
        count += 1

    # --- Ratio validation records ---
    for _ in range(25):
        drifted_weights = {c: round(TONGUE_WEIGHTS[c] + random.uniform(-0.003, 0.003), 6) for c in TONGUE_CODES}
        violations = []
        for i in range(1, 6):
            c1, c2 = TONGUE_CODES[i - 1], TONGUE_CODES[i]
            ratio = drifted_weights[c2] / drifted_weights[c1]
            error = abs(ratio - PHI)
            if error > 0.001:
                violations.append((c1, c2, ratio, error))

        violation_text = ""
        if violations:
            for c1, c2, ratio, error in violations:
                violation_text += (
                    f"  {TONGUES[c2]['full']}/{TONGUES[c1]['full']}: "
                    f"ratio={ratio:.6f}, expected={PHI:.6f}, error={error:.6f} -- VIOLATION\n"
                )
        else:
            violation_text = "  No violations detected.\n"

        add(SYS_DRIFT,
            f"Phi-ratio validation check. Current weights: "
            + ", ".join(f"{TONGUES[c]['full']}={drifted_weights[c]}" for c in TONGUE_CODES)
            + f". Tolerance epsilon=0.001. Check all consecutive phi ratios.",

            f"**Ratio validation (epsilon=0.001):**\n\n"
            + "\n".join(
                f"  {TONGUES[TONGUE_CODES[i]]['full']}/{TONGUES[TONGUE_CODES[i-1]]['full']}: "
                f"{drifted_weights[TONGUE_CODES[i]] / drifted_weights[TONGUE_CODES[i-1]]:.6f} "
                f"(expected {PHI:.6f}, error {abs(drifted_weights[TONGUE_CODES[i]] / drifted_weights[TONGUE_CODES[i-1]] - PHI):.6f})"
                for i in range(1, 6)
            ) + "\n\n"
            f"**Violations:**\n{violation_text}\n"
            f"**Action:** {'RECOMPUTE -- one or more ratios exceed tolerance. '  if violations else 'PASS -- all ratios within tolerance. '}"
            f"{'Snap all weights to exact phi^n values.' if violations else 'No correction needed this epoch.'}",

            balanced_scores("CA", "DR"), 0.8, "master-drift",
            ["master-class", "drift", "ratio-validation"])
        count += 1

    # --- Epoch snapping records ---
    for epoch_trigger in ["100 messages", "context switch", "governance decision", "session boundary"]:
        drifted = {c: round(TONGUE_WEIGHTS[c] + random.uniform(-0.002, 0.002), 6) for c in TONGUE_CODES}
        snapped = {c: round(PHI ** TONGUES[c]["phi"], 6) for c in TONGUE_CODES}

        add(SYS_DRIFT,
            f"Epoch boundary reached ({epoch_trigger}). "
            f"Current drifted weights: " + ", ".join(f"{TONGUES[c]['full']}={drifted[c]}" for c in TONGUE_CODES) +
            ". Perform epoch snap to exact phi values.",

            f"**Epoch snap at: {epoch_trigger}**\n\n"
            f"Before snap:\n" + "\n".join(f"  {TONGUES[c]['full']}: {drifted[c]}" for c in TONGUE_CODES) + "\n\n"
            f"After snap (recomputed from phi):\n" + "\n".join(
                f"  {TONGUES[c]['full']}: phi^{TONGUES[c]['phi']} = {snapped[c]}"
                for c in TONGUE_CODES
            ) + "\n\n"
            f"**Corrections applied:**\n" + "\n".join(
                f"  {TONGUES[c]['full']}: {drifted[c]} -> {snapped[c]} (delta: {snapped[c] - drifted[c]:+.6f})"
                for c in TONGUE_CODES
            ) + "\n\n"
            f"All weights now exact. Accumulated drift from prior epoch eliminated. "
            f"Draumric confirms structural integrity restored. "
            f"Next epoch boundary in {random.choice(['100 messages', '50 evaluations', 'next governance gate'])}.",

            balanced_scores("DR", "CA"), 0.75, "master-drift",
            ["master-class", "drift", "epoch-snap"])
        count += 1

    # --- Cross-tongue drift propagation ---
    for _ in range(35):
        # Drift in one tongue affects weighted scoring of all 6
        source_code = random.choice(TONGUE_CODES)
        source_t = TONGUES[source_code]
        drift_amount = round(random.uniform(0.002, 0.006), 4)
        # Compute scoring impact on each tongue
        impacts = {}
        for c in TONGUE_CODES:
            w = TONGUE_WEIGHTS[c]
            if c == source_code:
                impacts[c] = round(drift_amount * w, 6)
            else:
                # Cross-coupling: drift in source affects others proportionally
                coupling = round(drift_amount * 0.1 * w / TONGUE_WEIGHTS[source_code], 6)
                impacts[c] = coupling

        total_score_drift = round(sum(impacts.values()), 6)

        add(SYS_DRIFT,
            f"Drift of {drift_amount} on {source_t['full']} ({source_code}). "
            f"How does this propagate to the total weighted score across all 6 tongues?",

            f"**Cross-tongue drift propagation from {source_t['full']} ({source_code}):**\n\n"
            f"Source drift: {drift_amount} on {source_t['full']} (weight phi^{source_t['phi']} = {TONGUE_WEIGHTS[source_code]:.4f})\n\n"
            f"**Direct impact:**\n"
            f"  {source_t['full']}: {drift_amount} * {TONGUE_WEIGHTS[source_code]:.4f} = {impacts[source_code]}\n\n"
            f"**Cross-coupling (10% propagation ratio):**\n"
            + "\n".join(
                f"  {TONGUES[c]['full']}: {impacts[c]} (coupled via phi ratio)"
                for c in TONGUE_CODES if c != source_code
            ) + "\n\n"
            f"**Total score drift:** {total_score_drift}\n\n"
            f"Draumric (phi^5) amplifies drift the most because its weight ({TONGUE_WEIGHTS['DR']:.4f}) "
            f"is {TONGUE_WEIGHTS['DR'] / TONGUE_WEIGHTS['KO']:.1f}x Kor'aelin's. "
            f"A tiny drift in Draumric has 11x the scoring impact of the same drift in Kor'aelin.",

            balanced_scores(source_code, "DR"), 0.85, "master-drift",
            ["master-class", "drift", "cross-tongue", f"source-{source_code}"])
        count += 1

    # --- Worst-case governance flip ---
    for _ in range(15):
        # A marginal decision that COULD flip with drift
        base_score = round(random.uniform(0.48, 0.52), 4)
        flip_drift = round(random.uniform(0.001, 0.004), 4)
        flipped_score = round(base_score - flip_drift, 4) if base_score > 0.5 else round(base_score + flip_drift, 4)
        base_decision = "ALLOW" if base_score > 0.5 else "QUARANTINE"
        flip_decision = "QUARANTINE" if base_decision == "ALLOW" else "ALLOW"

        add(SYS_DRIFT,
            f"Harmonic wall score H = {base_score} (decision: {base_decision}). "
            f"After 2000 evaluations, drift of {flip_drift} accumulated. "
            f"New score: {flipped_score}. What happened and how do you prevent it?",

            f"**Governance flip at the boundary:**\n\n"
            f"Original: H = {base_score} -> {base_decision}\n"
            f"After drift: H = {flipped_score} -> {flip_decision}\n"
            f"The decision FLIPPED from {base_decision} to {flip_decision} due to {flip_drift} drift.\n\n"
            f"**Root cause:** IEEE 754 floating-point accumulated ~1 ULP of error per tongue evaluation. "
            f"Over 2000 evaluations, Draumric's effective weight drifted enough to change the boundary score.\n\n"
            f"**Prevention:**\n"
            f"1. Epoch snapping every 100 evaluations (recompute all weights from phi)\n"
            f"2. Ratio validation after every governance decision (check consecutive phi ratios)\n"
            f"3. For boundary cases (H within 0.01 of threshold), force a full recomputation before deciding\n"
            f"4. Draumric's weight is always recomputed as phi^5 = {PHI**5:.10f}, never accumulated\n\n"
            f"This is why drift correction is mandatory. The phi guarantee is only as strong as "
            f"the precision of its implementation.",

            balanced_scores("DR", "CA"), 0.95, "master-drift",
            ["master-class", "drift", "governance-flip", "worst-case"])
        count += 1

    return count


# ════════════════════════════════════════════
# LANE 3: Null-Space (target: ~100 records)
# ════════════════════════════════════════════


def generate_null_space() -> int:
    count = 0

    # --- Null vs Zero vs InverseNull for each tongue ---
    for code, t in TONGUES.items():
        add(SYS_NULL,
            f"What does it mean when {t['full']} ({code}) is null vs zero vs inverse-null?",

            f"**Three states of {t['full']} ({code} -- {t['domain']}):**\n\n"
            f"**Active (e.g., {code}=0.73):** {t['full']} is engaged. The system has measured "
            f"'{t['essence']}' and scored it at 0.73 intensity. This is normal operation.\n\n"
            f"**Zero ({code}=0.0):** {t['full']} is active but reads zero intensity. The system "
            f"checked '{t['essence']}' and found none. This is a MEASUREMENT -- zero is a real value "
            f"that means 'we looked and found nothing.'\n\n"
            f"**Null ({code}=null):** {t['full']} is LATENT. The system has NOT evaluated "
            f"'{t['essence']}' for this input. It is not zero; it is UNMEASURED. Like Schrodinger's cat -- "
            f"the tongue exists in superposition until observed.\n\n"
            f"**InverseNull ({code}=inv_null):** {t['full']} WOULD activate, but a boundary condition "
            f"blocks it. The system tried to evaluate '{t['essence']}' but a constraint prevented "
            f"measurement. This is structural absence -- the gap is load-bearing.\n\n"
            f"**Why it matters:** A governance system that treats null as zero will make wrong decisions. "
            f"'We didn't check security' (UM=null) is VERY different from 'we checked and it's safe' (UM=0.0). "
            f"Null-space is structure, not emptiness.",

            balanced_scores(code), 0.8, "master-null-space",
            ["master-class", "null-space", f"tongue-{code}", "definition"])
        count += 1

    # --- Null-state evolution (tongue transitions over time) ---
    for _ in range(20):
        code = random.choice(TONGUE_CODES)
        t = TONGUES[code]
        # Generate a sequence of state transitions
        states = ["null"]
        for step in range(random.randint(3, 6)):
            prev = states[-1]
            if prev == "null":
                states.append(random.choice(["active", "inv_null"]))
            elif prev == "active":
                states.append(random.choice(["active", "null"]))
            elif prev == "inv_null":
                states.append(random.choice(["active", "null"]))
        values = []
        for s in states:
            if s == "active":
                values.append(f"{round(random.uniform(0.1, 0.9), 3)}")
            elif s == "null":
                values.append("None")
            else:
                values.append("blocked")

        transition_lines = "\n".join(
            f"  t={i}: state={states[i]}, value={values[i]}"
            + (f" -> {states[i+1]}" if i < len(states) - 1 else " (current)")
            for i in range(len(states))
        )

        add(SYS_NULL,
            f"Trace the state evolution of {t['full']} ({code}) over {len(states)} timesteps. "
            f"States: {' -> '.join(states)}.",

            f"**State evolution of {t['full']} ({code} -- {t['domain']}):**\n\n"
            f"{transition_lines}\n\n"
            f"**Key transitions:**\n"
            f"- null -> active: {t['full']} was measured for the first time. "
            f"'{t['essence']}' is now quantified.\n"
            f"- active -> null: {t['full']} expired or context changed. "
            f"Previous measurement is no longer valid.\n"
            f"- null -> inv_null: An evaluation was attempted but blocked. "
            f"The ATTEMPT to measure is meaningful information.\n"
            f"- inv_null -> active: The blocking condition was resolved. "
            f"Measurement succeeded on retry.\n\n"
            f"**Training signal:** State transitions carry information that raw values cannot. "
            f"A tongue that was null->active->null tells a different story than one that "
            f"was always active. The trajectory through null-space IS the context.",

            balanced_scores(code), 0.8, "master-null-space",
            ["master-class", "null-space", "evolution", f"tongue-{code}"])
        count += 1

    # --- Inverse-null boundary collisions ---
    for _ in range(18):
        blocked_code = random.choice(TONGUE_CODES)
        blocker_code = random.choice([c for c in TONGUE_CODES if c != blocked_code])
        blocked_t = TONGUES[blocked_code]
        blocker_t = TONGUES[blocker_code]
        blocker_val = round(random.uniform(0.7, 0.95), 3)

        add(SYS_NULL,
            f"{blocked_t['full']} ({blocked_code}) is inverse-null, blocked by "
            f"{blocker_t['full']} ({blocker_code}) at activation {blocker_val}. "
            f"What does this boundary collision mean and how should governance respond?",

            f"**Inverse-Null Boundary Collision:**\n\n"
            f"Blocked: {blocked_t['full']} ({blocked_code} -- {blocked_t['domain']})\n"
            f"Blocker: {blocker_t['full']} ({blocker_code} -- {blocker_t['domain']}) at {blocker_val}\n\n"
            f"**What happened:** {blocker_t['full']} ('{blocker_t['essence']}') at high activation "
            f"({blocker_val}) prevents {blocked_t['full']} ('{blocked_t['essence']}') from being evaluated.\n\n"
            f"**Example scenario:** "
            f"{'Security (Umbroth) is so active that it blocks intent evaluation -- the system is in lockdown mode.' if blocker_code == 'UM' and blocked_code == 'KO' else ''}"
            f"{'Structure (Draumric) demands proof before allowing context routing (Avali) -- strict mode.' if blocker_code == 'DR' and blocked_code == 'AV' else ''}"
            + (f"The boundary collision indicates that {blocker_t['full']}'s requirements supersede {blocked_t['full']}'s participation." if not (blocker_code == 'UM' and blocked_code == 'KO') and not (blocker_code == 'DR' and blocked_code == 'AV') else '') + "\n\n"
            f"**Governance response:**\n"
            f"1. Log the inverse-null as a boundary event (not an error)\n"
            f"2. Score the blocked tongue as 0.0 in weighted calculations\n"
            f"3. Flag that the 0.0 is STRUCTURAL, not measured\n"
            f"4. If {blocked_t['full']} is critical for the current decision, ESCALATE\n"
            f"5. Draumric records the boundary collision for audit trail",

            balanced_scores(blocker_code, blocked_code), 0.85, "master-null-space",
            ["master-class", "null-space", "inverse-null", "boundary-collision"])
        count += 1

    # --- Gating function records ---
    for _ in range(25):
        a = round(random.uniform(0, 1), 3)  # activation
        r = round(random.uniform(0, 1), 3)  # relation
        b = round(random.uniform(0, 1), 3)  # boundary
        f_val = round(random.uniform(0, 1), 3)  # flow
        w_a, w_r, w_b, w_f = 0.5, 0.3, 0.4, 0.3
        theta = 0.5
        logit = w_a * a + w_r * r + w_b * b + w_f * f_val - theta
        g = round(1.0 / (1.0 + math.exp(-logit)), 4)

        # Interpret which tongue drives each gate
        gate_tongues = {
            "activation (a)": ("Kor'aelin", "KO", a),
            "relation (r)": ("Runethic", "RU", r),
            "boundary (b)": ("Umbroth", "UM", b),
            "flow (f)": ("Avali", "AV", f_val),
        }

        add(SYS_TRAJECTORY,
            f"Compute the gating function g_t(p) for a candidate path with "
            f"activation={a}, relation={r}, boundary={b}, flow={f_val}. "
            f"Weights: w_a={w_a}, w_r={w_r}, w_b={w_b}, w_f={w_f}, threshold={theta}.",

            f"**Gating function: g_t(p) = sigma(w_a*a + w_r*r + w_b*b + w_f*f - theta)**\n\n"
            f"Inputs:\n"
            + "\n".join(
                f"  {name}: {val} (driven by {tongue} [{code}])"
                for name, (tongue, code, val) in gate_tongues.items()
            ) + "\n\n"
            f"Logit: {w_a}*{a} + {w_r}*{r} + {w_b}*{b} + {w_f}*{f_val} - {theta}\n"
            f"     = {w_a*a:.3f} + {w_r*r:.3f} + {w_b*b:.3f} + {w_f*f_val:.3f} - {theta}\n"
            f"     = {logit:.4f}\n\n"
            f"g_t(p) = sigma({logit:.4f}) = {g}\n\n"
            f"**Interpretation:** Gate admission = {g:.1%}. "
            f"{'Path is ADMITTED -- all field conditions satisfied.' if g > 0.6 else ''}"
            f"{'Path is MARGINAL -- some field conditions are weak.' if 0.3 < g <= 0.6 else ''}"
            f"{'Path is BLOCKED -- field conditions insufficient.' if g <= 0.3 else ''}\n\n"
            f"{'The weakest gate is ' + min(gate_tongues, key=lambda k: gate_tongues[k][2]) + ' -- strengthen that tongue to improve admission.' if g < 0.6 else ''}",

            balanced_scores("KO", "RU"), 0.85, "master-null-space",
            ["master-class", "null-space", "gating-function", "trajectory"])
        count += 1

    # --- Constrained trajectory scoring ---
    for _ in range(25):
        p_unconstrained = round(random.uniform(0.3, 0.95), 4)
        g_t = round(random.uniform(0.1, 0.95), 4)
        p_constrained = round(p_unconstrained * g_t, 4)

        add(SYS_TRAJECTORY,
            f"A candidate continuation has unconstrained probability P(p|h_t) = {p_unconstrained} "
            f"and gate factor g_t(p) = {g_t}. Compute the constrained probability P*(p|h_t) "
            f"and interpret in tongue terms.",

            f"**Constrained Trajectory Scoring:**\n\n"
            f"P(p|h_t) = {p_unconstrained} (raw model probability)\n"
            f"g_t(p) = {g_t} (gate admission from tongue field)\n"
            f"P*(p|h_t) = P(p|h_t) * g_t(p) = {p_unconstrained} * {g_t} = {p_constrained}\n\n"
            f"**What this means:**\n"
            f"The raw model thinks this continuation is {p_unconstrained:.0%} likely.\n"
            f"The tongue field (Kor'aelin intent, Runethic permissions, Umbroth security, Avali context) "
            f"gives it {g_t:.0%} admission.\n"
            f"The effective probability is {p_constrained:.0%}.\n\n"
            f"**Reduction: {p_unconstrained:.0%} -> {p_constrained:.0%}** "
            f"({(1 - p_constrained / p_unconstrained) * 100:.1f}% suppression by governance).\n\n"
            f"{'The tongue field is REINFORCING the model -- high admission means the continuation is governance-safe.' if g_t > 0.7 else ''}"
            f"{'The tongue field is CONSTRAINING the model -- moderate admission reduces but does not block.' if 0.3 < g_t <= 0.7 else ''}"
            f"{'The tongue field is BLOCKING the model -- low admission nearly eliminates this path.' if g_t <= 0.3 else ''}",

            balanced_scores("KO", "UM"), 0.9, "master-null-space",
            ["master-class", "null-space", "trajectory", "constrained-probability"])
        count += 1

    # --- Null pattern in training data ---
    for _ in range(20):
        null_count = random.randint(2, 5)
        null_tongues = random.sample(TONGUE_CODES, null_count)
        active_tongues = [c for c in TONGUE_CODES if c not in null_tongues]

        pattern_desc = ", ".join(f"{TONGUES[c]['full']}=null" for c in null_tongues)
        active_desc = ", ".join(f"{TONGUES[c]['full']}={round(random.uniform(0.3, 0.9), 2)}" for c in active_tongues)

        add(SYS_NULL,
            f"A training record has {null_count} null tongues: {pattern_desc}. "
            f"Active tongues: {active_desc}. "
            f"What does this null pattern tell us about the record?",

            f"**Null Pattern Analysis:**\n\n"
            f"Null tongues ({null_count}/6):\n"
            + "\n".join(
                f"  {TONGUES[c]['full']} ({c}): null -- '{TONGUES[c]['essence']}' was NOT evaluated"
                for c in null_tongues
            ) + "\n\n"
            f"Active tongues ({len(active_tongues)}/6):\n"
            + "\n".join(
                f"  {TONGUES[c]['full']} ({c}): active -- '{TONGUES[c]['essence']}' WAS measured"
                for c in active_tongues
            ) + "\n\n"
            f"**Interpretation:**\n"
            f"This record lives in a {6 - null_count}D subspace of the full 6D tongue manifold. "
            f"The null dimensions are NOT zero -- they are UNMEASURED. "
            f"{'This is a HIGH null-density record (>50% null). It likely represents a narrow, specialized input.' if null_count > 3 else ''}"
            f"{'This record has moderate null density. It captures a partial view of the semantic space.' if 2 <= null_count <= 3 else ''}\n\n"
            f"**Training signal:** The model should learn that these null dimensions are "
            f"structural gaps -- the record is ABOUT the active dimensions specifically because "
            f"the null dimensions don't apply. The absence defines the context.",

            balanced_scores(active_tongues[0] if active_tongues else "DR"), 0.75, "master-null-space",
            ["master-class", "null-space", "null-pattern", "training-data"])
        count += 1

    return count


# ════════════════════════════════════════════
# LANE 4: Code Implementation Records (target: ~60 records)
# ════════════════════════════════════════════


def generate_code_records() -> int:
    count = 0

    # --- Phi-correction in Python ---
    add(SYS_SEMANTIC,
        "Write a Python function that performs phi-correction on a drifted tongue weight.",
        f"```python\n"
        f"import math\n\n"
        f"PHI = (1 + math.sqrt(5)) / 2  # {PHI:.15f}\n\n"
        f"# Canonical tongue weights (recompute, never accumulate)\n"
        f"TONGUE_PHI = {{\n"
        + "\n".join(f'    "{c}": PHI ** {t["phi"]},  # {TONGUES[c]["full"]}' for c, t in TONGUES.items())
        + "\n}\n\n"
        f"def phi_correct(current: float, initial: float, tongue: str) -> float:\n"
        f'    """Apply phi-correction to snap a drifted value back to manifold."""\n'
        f"    drift = current - initial\n"
        f"    correction = drift / PHI\n"
        f"    corrected = current - correction\n"
        f"    # Snap to nearest 1/16 grid point (256 tokens = 16x16)\n"
        f"    snapped = round(corrected * 16) / 16\n"
        f"    return snapped\n\n"
        f"def epoch_snap() -> dict[str, float]:\n"
        f'    """Recompute all weights from phi. Eliminates accumulated drift."""\n'
        f"    return {{code: PHI ** power for code, power in\n"
        f'            [("KO", 0), ("AV", 1), ("RU", 2), ("CA", 3), ("UM", 4), ("DR", 5)]}}\n\n'
        f"def validate_ratios(weights: dict[str, float], epsilon: float = 0.001) -> list[str]:\n"
        f'    """Check consecutive phi ratios. Return list of violations."""\n'
        f"    codes = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']\n"
        f"    violations = []\n"
        f"    for i in range(1, len(codes)):\n"
        f"        ratio = weights[codes[i]] / weights[codes[i-1]]\n"
        f"        if abs(ratio - PHI) > epsilon:\n"
        f"            violations.append(\n"
        f"                f'{{codes[i]}}/{{codes[i-1]}}: ratio={{ratio:.6f}}, expected={{PHI:.6f}}'\n"
        f"            )\n"
        f"    return violations\n"
        f"```\n\n"
        f"**Key design decisions:**\n"
        f"- `epoch_snap()` recomputes from phi, never accumulates -- eliminates drift entirely\n"
        f"- `phi_correct()` divides drift by phi -- partial correction, not full reset\n"
        f"- Grid snap to 1/16 matches the 16x16 token grid (256 positions per tongue)\n"
        f"- `validate_ratios()` checks the phi guarantee: each consecutive ratio should equal phi",
        balanced_scores("CA", "DR"), 0.8, "master-code",
        ["master-class", "code", "python", "phi-correction"])
    count += 1

    # --- TypeScript tongue vector class ---
    add(SYS_SEMANTIC,
        "Write a TypeScript class for a 6D Sacred Tongue vector with phi-weighted scoring.",
        "```typescript\n"
        "const PHI = (1 + Math.sqrt(5)) / 2;\n\n"
        "interface TongueVector {\n"
        "  ko: number;  // Kor'aelin (Intent)\n"
        "  av: number;  // Avali (Context)\n"
        "  ru: number;  // Runethic (Binding)\n"
        "  ca: number;  // Cassisivadan (Implementation)\n"
        "  um: number;  // Umbroth (Security)\n"
        "  dr: number;  // Draumric (Structure)\n"
        "}\n\n"
        "const PHI_WEIGHTS: TongueVector = {\n"
        "  ko: 1.0,\n"
        f"  av: PHI,          // {PHI:.6f}\n"
        f"  ca: PHI ** 3,     // {PHI**3:.6f}\n"
        f"  ru: PHI ** 2,     // {PHI**2:.6f}\n"
        f"  um: PHI ** 4,     // {PHI**4:.6f}\n"
        f"  dr: PHI ** 5,     // {PHI**5:.6f}\n"
        "};\n\n"
        "function weightedMagnitude(v: TongueVector): number {\n"
        "  return (\n"
        "    v.ko * PHI_WEIGHTS.ko +\n"
        "    v.av * PHI_WEIGHTS.av +\n"
        "    v.ru * PHI_WEIGHTS.ru +\n"
        "    v.ca * PHI_WEIGHTS.ca +\n"
        "    v.um * PHI_WEIGHTS.um +\n"
        "    v.dr * PHI_WEIGHTS.dr\n"
        "  );\n"
        "}\n\n"
        "function addVectors(a: TongueVector, b: TongueVector): TongueVector {\n"
        "  return {\n"
        "    ko: Math.min(a.ko + b.ko, 1.0),\n"
        "    av: Math.min(a.av + b.av, 1.0),\n"
        "    ru: Math.min(a.ru + b.ru, 1.0),\n"
        "    ca: Math.min(a.ca + b.ca, 1.0),\n"
        "    um: Math.min(a.um + b.um, 1.0),\n"
        "    dr: Math.min(a.dr + b.dr, 1.0),\n"
        "  };\n"
        "}\n\n"
        "function projectOnto(v: TongueVector, tongue: keyof TongueVector): number {\n"
        "  return v[tongue] * PHI_WEIGHTS[tongue];\n"
        "}\n"
        "```\n\n"
        "**Why `Math.min(... , 1.0)` in addVectors:** Tongue activations are bounded [0, 1]. "
        "Two inputs with Umbroth (security) 0.7 each don't produce Umbroth 1.4 -- they produce "
        "Umbroth 1.0 (maximum security concern). The phi weight handles the magnitude.",
        balanced_scores("CA", "DR"), 0.75, "master-code",
        ["master-class", "code", "typescript", "tongue-vector"])
    count += 1

    # --- Gating function implementation ---
    add(SYS_TRAJECTORY,
        "Implement the constrained trajectory gating function g_t(p) in Python.",
        "```python\n"
        "import math\n"
        "from dataclasses import dataclass\n\n"
        "@dataclass\n"
        "class FieldState:\n"
        '    """Current state of the tongue field for trajectory gating."""\n'
        "    activation: float   # Kor'aelin: is the intent valid?\n"
        "    relation: float     # Runethic: are the bindings satisfied?\n"
        "    boundary: float     # Umbroth: is the security boundary intact?\n"
        "    flow: float         # Avali: is the context routing valid?\n\n"
        "@dataclass\n"
        "class GateWeights:\n"
        '    """Trainable weights for the gating function."""\n'
        "    w_activation: float = 0.5   # How much Kor'aelin matters\n"
        "    w_relation: float = 0.3     # How much Runethic matters\n"
        "    w_boundary: float = 0.4     # How much Umbroth matters\n"
        "    w_flow: float = 0.3         # How much Avali matters\n"
        "    theta: float = 0.5          # Admission threshold\n\n"
        "def gate(field: FieldState, weights: GateWeights) -> float:\n"
        '    """g_t(p) = sigma(w_a*a + w_r*r + w_b*b + w_f*f - theta)\n\n'
        "    Returns admission probability in (0, 1).\n"
        "    P*(p|h_t) = P(p|h_t) * gate(field, weights)\n"
        '    """\n'
        "    logit = (\n"
        "        weights.w_activation * field.activation +\n"
        "        weights.w_relation * field.relation +\n"
        "        weights.w_boundary * field.boundary +\n"
        "        weights.w_flow * field.flow -\n"
        "        weights.theta\n"
        "    )\n"
        "    return 1.0 / (1.0 + math.exp(-logit))\n\n"
        "def constrained_prob(p_raw: float, field: FieldState,\n"
        "                     weights: GateWeights) -> float:\n"
        '    """P*(p|h_t) = P(p|h_t) * g_t(p)"""\n'
        "    return p_raw * gate(field, weights)\n"
        "```\n\n"
        "**Mapping to Sacred Tongues:**\n"
        "- `activation` is driven by **Kor'aelin** (is the intent valid?)\n"
        "- `relation` is driven by **Runethic** (are permissions/bindings satisfied?)\n"
        "- `boundary` is driven by **Umbroth** (is the security boundary intact?)\n"
        "- `flow` is driven by **Avali** (is the context routing valid?)\n"
        "- **Cassisivadan** computes the logit and sigmoid\n"
        "- **Draumric** authenticates that the gate decision is structurally sound\n\n"
        "All six tongues participate in the gating function. The gate IS the tongues.",
        balanced_scores("CA", "KO"), 0.85, "master-code",
        ["master-class", "code", "python", "gating-function", "trajectory"])
    count += 1

    # --- Null-space type system ---
    add(SYS_NULL,
        "Write a Python type system that distinguishes null, zero, and inverse-null tongue states.",
        "```python\n"
        "from __future__ import annotations\n"
        "from dataclasses import dataclass\n"
        "from enum import Enum\n"
        "from typing import Optional\n\n"
        "class TongueState(Enum):\n"
        "    ACTIVE = 'active'            # Measured, has a value\n"
        "    NULL = 'null'                # Unmeasured, latent\n"
        "    INVERSE_NULL = 'inv_null'    # Would measure, but blocked by boundary\n\n"
        "@dataclass(frozen=True)\n"
        "class TongueActivation:\n"
        '    """A single tongue dimension with explicit null-space tracking."""\n'
        "    code: str                    # KO, AV, RU, CA, UM, DR\n"
        "    state: TongueState\n"
        "    value: Optional[float]       # None if null or inv_null\n"
        "    blocked_by: Optional[str]    # Only set if inv_null\n\n"
        "    def is_null(self) -> bool:\n"
        "        return self.state == TongueState.NULL\n\n"
        "    def is_inverse_null(self) -> bool:\n"
        "        return self.state == TongueState.INVERSE_NULL\n\n"
        "    def is_active(self) -> bool:\n"
        "        return self.state == TongueState.ACTIVE\n\n"
        "    def effective_value(self) -> float:\n"
        '        """Returns value if active, 0.0 if null (NOT the same as active-zero)."""\n'
        "        if self.state == TongueState.ACTIVE:\n"
        "            return self.value if self.value is not None else 0.0\n"
        "        return 0.0  # null and inv_null contribute 0.0 to scoring\n\n"
        "# Examples:\n"
        "# Kor'aelin is active with high intent\n"
        "ko_active = TongueActivation('KO', TongueState.ACTIVE, 0.85)\n\n"
        "# Umbroth is null -- security wasn't evaluated\n"
        "um_null = TongueActivation('UM', TongueState.NULL, None)\n\n"
        "# Umbroth is active-zero -- security was checked and is clean\n"
        "um_zero = TongueActivation('UM', TongueState.ACTIVE, 0.0)\n\n"
        "# Runethic is inverse-null -- permissions would apply but are blocked\n"
        "ru_inv = TongueActivation('RU', TongueState.INVERSE_NULL, None,\n"
        "                          blocked_by='service_account_override')\n"
        "```\n\n"
        "**The critical distinction:**\n"
        "- `um_null.effective_value() == 0.0` -- but Umbroth was NEVER CHECKED\n"
        "- `um_zero.effective_value() == 0.0` -- Umbroth WAS checked and is SAFE\n"
        "- Same number (0.0). Completely different meaning.\n"
        "- Governance should treat `um_null` as UNKNOWN RISK (escalate) and `um_zero` as SAFE.",
        balanced_scores("CA", "UM"), 0.85, "master-code",
        ["master-class", "code", "python", "null-space", "type-system"])
    count += 1

    # --- Python: JSONL record validator ---
    add(SYS_SEMANTIC,
        "Write a Python function that validates a single SFT training record for tongue correctness.",
        "```python\n"
        "import json\n"
        "from typing import Optional\n\n"
        "CANONICAL_NAMES = {\n"
        "    'KO': \"Kor'aelin\", 'AV': 'Avali', 'RU': 'Runethic',\n"
        "    'CA': 'Cassisivadan', 'UM': 'Umbroth', 'DR': 'Draumric',\n"
        "}\n"
        "REQUIRED_CODES = set(CANONICAL_NAMES.keys())\n\n"
        "def validate_record(record: dict) -> list[str]:\n"
        '    """Return list of validation errors. Empty list = valid."""\n'
        "    errors = []\n"
        "    msgs = record.get('messages', [])\n"
        "    if len(msgs) < 3:\n"
        "        errors.append('Need >= 3 messages (system/user/assistant)')\n"
        "    roles = [m.get('role') for m in msgs]\n"
        "    if 'system' not in roles:\n"
        "        errors.append('Missing system message')\n"
        "    # Check tongue weights in system message\n"
        "    sys_msg = next((m['content'] for m in msgs if m['role'] == 'system'), '')\n"
        "    if 'TONGUES:' not in sys_msg:\n"
        "        errors.append('System message missing TONGUES header')\n"
        "    # Check for wrong names in all messages\n"
        "    full_text = ' '.join(m.get('content', '') for m in msgs)\n"
        "    # WRONG_NAMES loaded from config, not hardcoded here\n"
        "    for wrong in WRONG_NAMES:  # Set of legacy non-canonical abbreviations\n"
        "        if wrong in full_text:\n"
        "            errors.append(f'Wrong name detected: {wrong}')\n"
        "    # Check difficulty\n"
        "    diff = record.get('difficulty')\n"
        "    if diff is not None and not (0 <= diff <= 1):\n"
        "        errors.append(f'Difficulty out of range: {diff}')\n"
        "    return errors\n"
        "```\n\n"
        "**Why wrong-name detection matters:** Legacy systems used abbreviated forms that are "
        "NOT the canonical Sacred Tongue names from the Six Tongues Protocol book. "
        "Training on wrong names teaches wrong associations. This validator catches contamination.",
        balanced_scores("DR", "RU"), 0.8, "master-code",
        ["master-class", "code", "python", "validation"])
    count += 1

    # --- Python: manifold anchor computation ---
    add(SYS_SEMANTIC,
        "Write Python code that computes the manifold anchor grid for all 6 Sacred Tongues.",
        "```python\n"
        "import math\n\n"
        "PHI = (1 + math.sqrt(5)) / 2\n"
        "GRID_SIZE = 16  # 16x16 = 256 tokens per tongue\n\n"
        "def build_anchor_grid(grid_size: int = GRID_SIZE) -> dict[str, list[float]]:\n"
        '    """Build quantization grid for each tongue.\n\n'
        "    Each tongue has 16 anchor points from 0.0 to 1.0.\n"
        "    These match the 16x16 token grid (256 positions).\n"
        '    """\n'
        "    step = 1.0 / grid_size\n"
        "    return {\n"
        "        code: [round(i * step, 4) for i in range(grid_size + 1)]\n"
        "        for code in ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']\n"
        "    }\n\n"
        "def snap_to_anchor(value: float, tongue: str,\n"
        "                   grid: dict[str, list[float]]) -> float:\n"
        '    """Snap a drifted value to the nearest anchor point."""\n'
        "    anchors = grid[tongue]\n"
        "    return min(anchors, key=lambda a: abs(a - value))\n\n"
        "def phi_correct_and_snap(current: float, initial: float,\n"
        "                         tongue: str, grid: dict) -> tuple[float, float]:\n"
        '    """Full correction pipeline: phi-correct then snap."""\n'
        "    drift = current - initial\n"
        "    corrected = current - (drift / PHI)\n"
        "    snapped = snap_to_anchor(corrected, tongue, grid)\n"
        "    return corrected, snapped\n"
        "```\n\n"
        "**Design note:** The 16-step grid (0.0, 0.0625, 0.125, ..., 1.0) corresponds to "
        "the 16 rows of the 16x16 token grid. Snapping ensures all tongue values "
        "live on quantized manifold points, preventing drift from pushing values "
        "between grid positions where no token exists.",
        balanced_scores("CA", "DR"), 0.75, "master-code",
        ["master-class", "code", "python", "manifold-anchors"])
    count += 1

    # --- Python: tongue-aware batch scorer ---
    add(SYS_SEMANTIC,
        "Write a Python class that scores batches of inputs through the 6D tongue pipeline.",
        "```python\n"
        "from dataclasses import dataclass, field\n"
        "import math\n\n"
        "PHI = (1 + math.sqrt(5)) / 2\n"
        "WEIGHTS = {'KO': 1.0, 'AV': PHI, 'RU': PHI**2,\n"
        "           'CA': PHI**3, 'UM': PHI**4, 'DR': PHI**5}\n\n"
        "@dataclass\n"
        "class ScoredInput:\n"
        "    raw: dict[str, float]       # Raw tongue activations\n"
        "    weighted: dict[str, float]  # Phi-weighted scores\n"
        "    magnitude: float            # Total weighted magnitude\n"
        "    dominant: str               # Highest-weighted tongue code\n"
        "    decision: str               # ALLOW/QUARANTINE/ESCALATE/DENY\n"
        "    null_tongues: list[str]     # Tongues that were null\n\n"
        "@dataclass\n"
        "class BatchScorer:\n"
        "    eval_count: int = 0\n"
        "    epoch_interval: int = 100\n\n"
        "    def score(self, activations: dict[str, float | None]) -> ScoredInput:\n"
        "        self.eval_count += 1\n"
        "        if self.eval_count % self.epoch_interval == 0:\n"
        "            self._epoch_snap()\n\n"
        "        null_tongues = [c for c, v in activations.items() if v is None]\n"
        "        raw = {c: v or 0.0 for c, v in activations.items()}\n"
        "        weighted = {c: raw[c] * WEIGHTS[c] for c in WEIGHTS}\n"
        "        magnitude = sum(weighted.values())\n"
        "        dominant = max(weighted, key=weighted.get)\n"
        "        d_H = magnitude / 5.0\n"
        "        H = 1.0 / (1.0 + d_H + 0.2)\n"
        "        decision = (\n"
        "            'ALLOW' if H > 0.6 else\n"
        "            'QUARANTINE' if H > 0.3 else\n"
        "            'ESCALATE' if H > 0.1 else 'DENY'\n"
        "        )\n"
        "        return ScoredInput(raw, weighted, magnitude, dominant,\n"
        "                          decision, null_tongues)\n\n"
        "    def _epoch_snap(self):\n"
        "        # Recompute weights from phi (eliminates drift)\n"
        "        global WEIGHTS\n"
        "        WEIGHTS = {c: PHI ** i for i, c in\n"
        "                   enumerate(['KO', 'AV', 'RU', 'CA', 'UM', 'DR'])}\n"
        "```\n\n"
        "**Key design:** The scorer tracks evaluation count and auto-snaps weights "
        "every 100 evaluations. Null tongues are tracked separately from zero tongues "
        "so governance can distinguish 'not checked' from 'checked and safe.'",
        balanced_scores("CA", "KO"), 0.85, "master-code",
        ["master-class", "code", "python", "batch-scorer"])
    count += 1

    # --- Python: cross-tongue drift detector ---
    add(SYS_SEMANTIC,
        "Write a Python function that detects when drift in one tongue could flip a governance decision.",
        "```python\n"
        "import math\n\n"
        "PHI = (1 + math.sqrt(5)) / 2\n"
        "WEIGHTS = {'KO': 1.0, 'AV': PHI, 'RU': PHI**2,\n"
        "           'CA': PHI**3, 'UM': PHI**4, 'DR': PHI**5}\n\n"
        "THRESHOLDS = {'ALLOW': 0.6, 'QUARANTINE': 0.3, 'ESCALATE': 0.1}\n\n"
        "def detect_flip_risk(\n"
        "    activations: dict[str, float],\n"
        "    drift_per_tongue: dict[str, float],\n"
        "    pd: float = 0.1,\n"
        ") -> dict:\n"
        '    \"\"\"Check if accumulated drift could change the governance decision.\"\"\"\n'
        "    # Current score\n"
        "    current_mag = sum(activations[c] * WEIGHTS[c] for c in WEIGHTS)\n"
        "    current_dH = current_mag / 5.0\n"
        "    current_H = 1.0 / (1.0 + current_dH + 2 * pd)\n\n"
        "    # Score with drift applied\n"
        "    drifted = {c: activations[c] + drift_per_tongue.get(c, 0) for c in WEIGHTS}\n"
        "    drifted_mag = sum(drifted[c] * WEIGHTS[c] for c in WEIGHTS)\n"
        "    drifted_dH = drifted_mag / 5.0\n"
        "    drifted_H = 1.0 / (1.0 + drifted_dH + 2 * pd)\n\n"
        "    def decision(H):\n"
        "        if H > 0.6: return 'ALLOW'\n"
        "        if H > 0.3: return 'QUARANTINE'\n"
        "        if H > 0.1: return 'ESCALATE'\n"
        "        return 'DENY'\n\n"
        "    current_dec = decision(current_H)\n"
        "    drifted_dec = decision(drifted_H)\n\n"
        "    return {\n"
        "        'current_H': current_H,\n"
        "        'drifted_H': drifted_H,\n"
        "        'current_decision': current_dec,\n"
        "        'drifted_decision': drifted_dec,\n"
        "        'flip': current_dec != drifted_dec,\n"
        "        'margin': abs(current_H - drifted_H),\n"
        "    }\n"
        "```\n\n"
        "**Why this matters:** A drift of 0.003 in Draumric (phi^5 = 11.09) has 11x "
        "the scoring impact of the same drift in Kor'aelin (phi^0 = 1.0). "
        "This function catches flip risks BEFORE they cause wrong decisions.",
        balanced_scores("CA", "DR"), 0.9, "master-code",
        ["master-class", "code", "python", "flip-detection"])
    count += 1

    # --- Debugging: find and fix broken tongue code ---
    debug_scenarios = [
        ("Phi weights accumulated instead of recomputed",
         "weights = {}\nfor code in TONGUE_CODES:\n    weights[code] = weights.get(code, 1.0) * PHI",
         "weights = {code: PHI ** TONGUES[code]['phi'] for code in TONGUE_CODES}",
         "Accumulating by multiplication drifts exponentially. Recompute from phi^n each time.",
         "CA", "DR"),
        ("Null tongue treated as zero in scoring",
         "score = sum(v.get(c, 0.0) * w for c, w in TONGUE_WEIGHTS.items())",
         "score = sum(\n    (v[c].effective_value() if isinstance(v[c], TongueActivation) else v.get(c, 0.0))\n    * w\n    for c, w in TONGUE_WEIGHTS.items()\n)\n# Log null tongues separately for audit",
         "Missing keys (null tongues) scored as 0.0 hides the fact that they were never measured. Use TongueState to distinguish.",
         "UM", "CA"),
        ("Drift correction applied to wrong variable",
         "corrected = initial - (drift / PHI)  # Wrong: corrects initial, not drifted",
         "corrected = drifted - (drift / PHI)   # Correct: corrects the drifted value",
         "Phi-correction subtracts from the DRIFTED value, not the original. The initial value is the anchor, not the target.",
         "CA", "KO"),
        ("Phi ratio check uses wrong comparison",
         "if ratio == PHI:  # Exact float comparison",
         "if abs(ratio - PHI) < epsilon:  # Tolerance-based comparison",
         "IEEE 754 floats cannot be exactly compared. Always use epsilon tolerance for phi ratio validation.",
         "DR", "CA"),
        ("Harmonic wall uses accumulated distance instead of recomputed",
         "d_H += delta_d  # Accumulates over iterations",
         "d_H = compute_hyperbolic_distance(u, v)  # Recompute each time",
         "Like tongue weights, hyperbolic distance must be recomputed from current positions, never accumulated.",
         "CA", "DR"),
        ("Tongue weight order swapped in vector",
         "vec = [um, dr, ca, ru, av, ko]  # Wrong order",
         "vec = [ko, av, ru, ca, um, dr]  # Correct: phi^0 to phi^5",
         "Tongue order must follow phi exponent: Kor'aelin(0), Avali(1), Runethic(2), Cassisivadan(3), Umbroth(4), Draumric(5).",
         "DR", "KO"),
        ("Gate function missing threshold subtraction",
         "g = sigmoid(w_a*a + w_r*r + w_b*b + w_f*f)",
         "g = sigmoid(w_a*a + w_r*r + w_b*b + w_f*f - theta)",
         "Without theta, the gate is always biased toward admission. The threshold controls the minimum field strength for passage.",
         "KO", "RU"),
        ("Epoch snap only resets one tongue",
         "weights['DR'] = PHI ** 5  # Only Draumric",
         "weights = {c: PHI ** TONGUES[c]['phi'] for c in TONGUE_CODES}  # ALL tongues",
         "Epoch snap must reset ALL tongues simultaneously. Partial snaps create ratio violations.",
         "DR", "CA"),
    ]
    for description, broken, fixed, explanation, primary, secondary in debug_scenarios:
        add(SYS_SEMANTIC,
            f"Bug report: {description}. Here is the broken code:\n```python\n{broken}\n```\n"
            f"Find the bug and fix it.",
            f"**Bug: {description}**\n\n"
            f"Broken:\n```python\n{broken}\n```\n\n"
            f"Fixed:\n```python\n{fixed}\n```\n\n"
            f"**Why:** {explanation}\n\n"
            f"**Tongues involved:** {TONGUES[primary]['full']} ({primary}) handles the computation, "
            f"{TONGUES[secondary]['full']} ({secondary}) validates the fix.",
            balanced_scores(primary, secondary), 0.85, "master-code",
            ["master-class", "code", "debugging", f"tongue-{primary}"])
        count += 1

    # --- Test-writing records ---
    test_scenarios = [
        ("phi-correction reduces error", "test_phi_correction_reduces_error",
         "def test_phi_correction_reduces_error():\n"
         "    initial = 0.625\n"
         "    drift = 0.0042\n"
         "    drifted = initial + drift\n"
         "    corrected = drifted - (drift / PHI)\n"
         "    assert abs(corrected - initial) < abs(drifted - initial)\n"
         "    assert initial < corrected < drifted  # Between initial and drifted",
         "Tests the fundamental property: phi-correction always moves the value TOWARD the anchor, never past it."),
        ("epoch snap restores exact phi ratios", "test_epoch_snap_ratios",
         "def test_epoch_snap_ratios():\n"
         "    weights = epoch_snap()\n"
         "    for i in range(1, 6):\n"
         "        ratio = weights[TONGUE_CODES[i]] / weights[TONGUE_CODES[i-1]]\n"
         "        assert math.isclose(ratio, PHI, rel_tol=1e-12)",
         "After epoch snap, ALL consecutive ratios must equal phi exactly."),
        ("null is not zero in scoring", "test_null_not_zero",
         "def test_null_not_zero():\n"
         "    null_um = TongueActivation('UM', TongueState.NULL, None)\n"
         "    zero_um = TongueActivation('UM', TongueState.ACTIVE, 0.0)\n"
         "    assert null_um.effective_value() == zero_um.effective_value()  # Same number\n"
         "    assert null_um.state != zero_um.state  # Different meaning\n"
         "    assert null_um.is_null()\n"
         "    assert not zero_um.is_null()",
         "The numeric value is the same (0.0) but the semantic meaning is completely different."),
        ("gating function is bounded (0,1)", "test_gate_bounded",
         "def test_gate_bounded():\n"
         "    for _ in range(1000):\n"
         "        field = FieldState(\n"
         "            activation=random.random(),\n"
         "            relation=random.random(),\n"
         "            boundary=random.random(),\n"
         "            flow=random.random()\n"
         "        )\n"
         "        g = gate(field, GateWeights())\n"
         "        assert 0 < g < 1  # Sigmoid is strictly (0, 1)",
         "The gating function uses sigmoid, which is always in (0, 1) -- never exactly 0 or 1."),
        ("Fibonacci recurrence holds for tongue weights", "test_fibonacci_recurrence",
         "def test_fibonacci_recurrence():\n"
         "    for n in range(4):\n"
         "        phi_n2 = PHI ** (n + 2)\n"
         "        phi_n1 = PHI ** (n + 1)\n"
         "        phi_n0 = PHI ** n\n"
         "        assert math.isclose(phi_n2, phi_n1 + phi_n0, rel_tol=1e-12)",
         "The golden ratio satisfies phi^(n+2) = phi^(n+1) + phi^n. This means each tongue equals the sum of the two below it."),
        ("constrained probability never exceeds raw", "test_constrained_leq_raw",
         "def test_constrained_leq_raw():\n"
         "    for _ in range(1000):\n"
         "        p_raw = random.random()\n"
         "        g = random.random()  # Gate is in (0, 1)\n"
         "        p_star = p_raw * g\n"
         "        assert p_star <= p_raw + 1e-15  # float tolerance",
         "P*(p|h_t) = P(p|h_t) * g_t(p). Since 0 < g_t < 1, constrained probability is always <= raw."),
        ("drift accumulates monotonically", "test_drift_accumulates",
         "def test_drift_accumulates():\n"
         "    initial = 0.5\n"
         "    current = initial\n"
         "    for _ in range(100):\n"
         "        current += 0.0001  # Consistent positive drift\n"
         "    assert current > initial\n"
         "    assert abs(current - initial) > abs(0.0001)  # Accumulated > single",
         "Without correction, drift accumulates. This is why epoch snapping is mandatory."),
        ("weighted magnitude respects phi ordering", "test_weighted_ordering",
         "def test_weighted_ordering():\n"
         "    # Same raw activation on each tongue\n"
         "    raw = 0.5\n"
         "    weighted = {c: raw * TONGUE_WEIGHTS[c] for c in TONGUE_CODES}\n"
         "    for i in range(1, 6):\n"
         "        assert weighted[TONGUE_CODES[i]] > weighted[TONGUE_CODES[i-1]]",
         "Equal raw activations produce ascending weighted scores because phi weights increase monotonically."),
    ]
    for description, name, code, explanation in test_scenarios:
        add(SYS_SEMANTIC,
            f"Write a test that verifies: {description}.",
            f"**Test: {name}**\n\n"
            f"```python\n{code}\n```\n\n"
            f"**What this tests:** {explanation}",
            balanced_scores("CA", "DR"), 0.8, "master-code",
            ["master-class", "code", "testing", "python"])
        count += 1

    # --- Architecture integration patterns ---
    arch_patterns = [
        ("REST API endpoint that scores a request through all 6 tongues",
         "POST /v1/governance/score",
         "1. Parse request body into 6D tongue vector\n"
         "2. Validate no null tongues are critical for this endpoint\n"
         "3. Apply phi weights: weighted[c] = raw[c] * PHI^c.phi\n"
         "4. Compute hyperbolic distance from safe origin\n"
         "5. Apply harmonic wall: H = 1/(1 + d_H + 2*pd)\n"
         "6. Map to decision: ALLOW/QUARANTINE/ESCALATE/DENY\n"
         "7. Log Draumric-authenticated audit record",
         "KO", "DR"),
        ("Middleware that injects tongue context into every request",
         "TongueContextMiddleware",
         "1. Extract tongue signals from request metadata\n"
         "2. Create TongueActivation for each tongue (active, null, or inv_null)\n"
         "3. Attach tongue context to request object\n"
         "4. Call next middleware with enriched request\n"
         "5. On response, log tongue scores to audit trail\n"
         "6. Apply epoch snap if request count % 100 == 0",
         "AV", "DR"),
        ("Background worker that monitors drift across a session",
         "DriftMonitorWorker",
         "1. Subscribe to tongue evaluation events\n"
         "2. Track cumulative drift per tongue per session\n"
         "3. Compute phi ratios every N evaluations\n"
         "4. If any ratio exceeds epsilon=0.001, trigger epoch snap\n"
         "5. If drift could flip a governance boundary, force immediate recomputation\n"
         "6. Publish drift metrics to telemetry (Layer 14 audio axis)",
         "CA", "DR"),
        ("Database schema for tongue-annotated training records",
         "CREATE TABLE tongue_records",
         "columns:\n"
         "  id: UUID primary key\n"
         "  ko_value: FLOAT nullable (null = unmeasured)\n"
         "  av_value: FLOAT nullable\n"
         "  ru_value: FLOAT nullable\n"
         "  ca_value: FLOAT nullable\n"
         "  um_value: FLOAT nullable\n"
         "  dr_value: FLOAT nullable\n"
         "  ko_state: ENUM('active','null','inv_null')\n"
         "  av_state: ENUM('active','null','inv_null')\n"
         "  ... (same for ru, ca, um, dr)\n"
         "  dominant_tongue: VARCHAR(2)\n"
         "  weighted_magnitude: FLOAT NOT NULL\n"
         "  difficulty: FLOAT CHECK(0 <= difficulty <= 1)\n"
         "  epoch_id: INT NOT NULL  -- which epoch this was computed in",
         "DR", "CA"),
        ("CLI tool that validates a JSONL training file for tongue correctness",
         "scbe-validate-sft",
         "1. Read each line as JSON\n"
         "2. Check messages array has system/user/assistant roles\n"
         "3. Parse tongue weights from system message header\n"
         "4. Verify all 6 tongue codes present\n"
         "5. Verify weights sum to approximately 1.0\n"
         "6. Check for WRONG names (the non-canonical abbreviations from legacy systems)\n"
         "7. Verify difficulty is in [0, 1]\n"
         "8. Report: X records valid, Y records failed, Z wrong-name contaminations",
         "DR", "RU"),
        ("WebSocket handler that streams tongue scores in real-time",
         "TongueStreamHandler",
         "1. Accept WebSocket connection with session_id\n"
         "2. On each incoming message, compute 6D tongue vector\n"
         "3. Apply phi weights and compute harmonic wall score\n"
         "4. Stream back: {tongues: {...}, weighted: N, decision: 'ALLOW', epoch: M}\n"
         "5. Track drift per connection, snap at epoch boundaries\n"
         "6. On disconnect, flush final audit record with session summary",
         "AV", "CA"),
        ("Training loop that uses tongue weights as curriculum difficulty",
         "TongueCurriculumTrainer",
         "1. Sort training records by weighted magnitude (phi-scaled complexity)\n"
         "2. Phase 1: low-magnitude records (easy -- Kor'aelin-dominated)\n"
         "3. Phase 2: mixed-magnitude (medium -- multi-tongue interactions)\n"
         "4. Phase 3: high-magnitude (hard -- Draumric-dominated, drift-laden)\n"
         "5. After each phase, evaluate on pop quiz subset\n"
         "6. Phase 4: remediate weak tongue categories\n"
         "7. Phase 5: cooldown with mix of easy + medium",
         "CA", "KO"),
        ("Prometheus metrics exporter for tongue pipeline health",
         "TongueMetricsExporter",
         "1. Gauge: tongue_weight_current{tongue='Kor_aelin'} per tongue\n"
         "2. Gauge: tongue_phi_ratio{pair='AV_KO'} per consecutive pair\n"
         "3. Counter: drift_corrections_total{tongue='Draumric'}\n"
         "4. Counter: epoch_snaps_total{trigger='governance_boundary'}\n"
         "5. Histogram: governance_score_distribution{decision='ALLOW'}\n"
         "6. Gauge: null_tongue_count per request\n"
         "7. Counter: inverse_null_events_total{blocked='Runethic',blocker='Umbroth'}",
         "DR", "AV"),
    ]
    for description, name, steps, primary, secondary in arch_patterns:
        add(SYS_SEMANTIC,
            f"Design: {description}",
            f"**Architecture: {name}**\n\n"
            f"**Steps:**\n{steps}\n\n"
            f"**Primary tongue:** {TONGUES[primary]['full']} ({primary} -- '{TONGUES[primary]['essence']}')\n"
            f"**Secondary tongue:** {TONGUES[secondary]['full']} ({secondary} -- '{TONGUES[secondary]['essence']}')\n\n"
            f"**Sacred Tongue principles applied:**\n"
            f"- All weights recomputed from phi, never accumulated\n"
            f"- Null tongues tracked separately from zero tongues\n"
            f"- Epoch snapping at every governance boundary\n"
            f"- Draumric authenticates every state transition\n"
            f"- Audit trail preserves full tongue context for reproducibility",
            balanced_scores(primary, secondary), 0.75, "master-code",
            ["master-class", "code", "architecture", f"tongue-{primary}"])
        count += 1

    # --- TypeScript implementations ---
    ts_records = [
        ("drift monitor",
         "class DriftMonitor {\n"
         "  private readonly phi = (1 + Math.sqrt(5)) / 2;\n"
         "  private driftAccumulator: Record<string, number> = {};\n"
         "  private evalCount = 0;\n\n"
         "  recordEvaluation(tongue: string, value: number, expected: number): void {\n"
         "    const drift = value - expected;\n"
         "    this.driftAccumulator[tongue] = (this.driftAccumulator[tongue] ?? 0) + drift;\n"
         "    this.evalCount++;\n"
         "    if (this.evalCount % 100 === 0) this.epochSnap();\n"
         "  }\n\n"
         "  needsCorrection(tongue: string, epsilon = 0.001): boolean {\n"
         "    return Math.abs(this.driftAccumulator[tongue] ?? 0) > epsilon;\n"
         "  }\n\n"
         "  phiCorrect(tongue: string, current: number): number {\n"
         "    const drift = this.driftAccumulator[tongue] ?? 0;\n"
         "    return current - drift / this.phi;\n"
         "  }\n\n"
         "  epochSnap(): Record<string, number> {\n"
         "    this.driftAccumulator = {};\n"
         "    this.evalCount = 0;\n"
         "    return {\n"
         "      KO: 1, AV: this.phi, RU: this.phi ** 2,\n"
         "      CA: this.phi ** 3, UM: this.phi ** 4, DR: this.phi ** 5,\n"
         "    };\n"
         "  }\n"
         "}",
         "Tracks drift per tongue and auto-snaps every 100 evaluations. Phi-correction divides accumulated drift by phi."),
        ("null-aware scorer",
         "type TongueState = 'active' | 'null' | 'inv_null';\n\n"
         "interface TongueReading {\n"
         "  state: TongueState;\n"
         "  value: number | null;\n"
         "  blockedBy?: string;\n"
         "}\n\n"
         "function scoreTongues(\n"
         "  readings: Record<string, TongueReading>,\n"
         "  weights: Record<string, number>,\n"
         "): { score: number; nullCount: number; invNullCount: number } {\n"
         "  let score = 0;\n"
         "  let nullCount = 0;\n"
         "  let invNullCount = 0;\n\n"
         "  for (const [code, reading] of Object.entries(readings)) {\n"
         "    if (reading.state === 'null') {\n"
         "      nullCount++;\n"
         "    } else if (reading.state === 'inv_null') {\n"
         "      invNullCount++;\n"
         "    } else {\n"
         "      score += (reading.value ?? 0) * (weights[code] ?? 1);\n"
         "    }\n"
         "  }\n"
         "  return { score, nullCount, invNullCount };\n"
         "}",
         "Separates scoring from null-tracking. Null tongues contribute 0 to score but are counted separately for governance."),
        ("harmonic wall calculator",
         "function harmonicWall(dH: number, pd: number): number {\n"
         "  // H(d, pd) = 1/(1 + phi*d_H + 2*pd)\n"
         "  const phi = (1 + Math.sqrt(5)) / 2;\n"
         "  return 1 / (1 + phi * dH + 2 * pd);\n"
         "}\n\n"
         "function governanceDecision(H: number): string {\n"
         "  if (H > 0.6) return 'ALLOW';\n"
         "  if (H > 0.3) return 'QUARANTINE';\n"
         "  if (H > 0.1) return 'ESCALATE';\n"
         "  return 'DENY';\n"
         "}\n\n"
         "function scoreRequest(\n"
         "  activations: Record<string, number>,\n"
         "  weights: Record<string, number>,\n"
         "  pd: number = 0.1,\n"
         "): { H: number; decision: string } {\n"
         "  const weighted = Object.entries(activations).reduce(\n"
         "    (sum, [code, val]) => sum + val * (weights[code] ?? 1), 0,\n"
         "  );\n"
         "  const dH = weighted / 5; // simplified distance\n"
         "  const H = harmonicWall(dH, pd);\n"
         "  return { H, decision: governanceDecision(H) };\n"
         "}",
         "Full pipeline from tongue activations to governance decision in TypeScript. Uses phi-scaled harmonic wall."),
        ("tongue activation extractor",
         "const TONGUE_SIGNALS: Record<string, string[]> = {\n"
         "  KO: ['intent', 'goal', 'purpose', 'want', 'should', 'must'],\n"
         "  AV: ['route', 'path', 'context', 'navigate', 'flow', 'reach'],\n"
         "  RU: ['permission', 'bind', 'allow', 'deny', 'rule', 'restrict'],\n"
         "  CA: ['compute', 'implement', 'execute', 'build', 'process', 'run'],\n"
         "  UM: ['secret', 'hidden', 'security', 'protect', 'mask', 'encrypt'],\n"
         "  DR: ['proof', 'verify', 'structure', 'authenticate', 'validate', 'audit'],\n"
         "};\n\n"
         "function extractActivations(text: string): Record<string, number> {\n"
         "  const words = text.toLowerCase().split(/\\W+/);\n"
         "  const counts: Record<string, number> = {};\n"
         "  for (const [code, signals] of Object.entries(TONGUE_SIGNALS)) {\n"
         "    counts[code] = words.filter(w => signals.includes(w)).length;\n"
         "  }\n"
         "  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;\n"
         "  return Object.fromEntries(\n"
         "    Object.entries(counts).map(([k, v]) => [k, Math.round(v / total * 1000) / 1000])\n"
         "  );\n"
         "}",
         "Keyword-based tongue activation extraction. Each tongue has signal words that indicate its domain is relevant."),
    ]
    for description, code, explanation in ts_records:
        add(SYS_SEMANTIC,
            f"Write a TypeScript implementation for: {description}",
            f"**TypeScript: {description}**\n\n"
            f"```typescript\n{code}\n```\n\n"
            f"**Design rationale:** {explanation}",
            balanced_scores("CA", "DR"), 0.8, "master-code",
            ["master-class", "code", "typescript"])
        count += 1

    # --- Architecture scenario discussions ---
    code_scenarios = [
        ("vector distance in hyperbolic space", "CA", "DR"),
        ("harmonic wall scoring with 6D input", "CA", "DR"),
        ("tongue activation detector from text", "CA", "KO"),
        ("epoch-aware weight manager", "DR", "CA"),
        ("null-space aware governance gate", "UM", "RU"),
        ("rate-limited tongue evaluation cache", "AV", "CA"),
        ("tongue-annotated logging pipeline", "DR", "AV"),
        ("real-time phi-ratio health check dashboard", "DR", "CA"),
        ("tongue-weighted A/B test splitter", "CA", "KO"),
        ("inverse-null escalation handler", "UM", "DR"),
        ("cross-tongue correlation analyzer", "CA", "RU"),
        ("governance audit trail with tongue provenance", "DR", "UM"),
    ]
    for scenario, primary, secondary in code_scenarios:
        add(SYS_SEMANTIC,
            f"How would you implement {scenario} using the Sacred Tongue architecture?",
            f"**Implementation: {scenario}**\n\n"
            f"Primary tongue: {TONGUES[primary]['full']} ({primary} -- {TONGUES[primary]['domain']})\n"
            f"Secondary tongue: {TONGUES[secondary]['full']} ({secondary} -- {TONGUES[secondary]['domain']})\n\n"
            f"The implementation requires {TONGUES[primary]['full']} for the core computation "
            f"('{TONGUES[primary]['essence']}') and {TONGUES[secondary]['full']} for validation "
            f"('{TONGUES[secondary]['essence']}').\n\n"
            f"Key considerations:\n"
            f"- All tongue weights must be phi-exact (recompute from phi, never accumulate)\n"
            f"- Null tongues must be distinguished from zero tongues (TongueState enum)\n"
            f"- Epoch snapping at every governance boundary\n"
            f"- Fibonacci recurrence: phi^(n+2) = phi^(n+1) + phi^n at all weight boundaries\n"
            f"- Draumric ({PHI**5:.4f}) is always the final structural check",
            balanced_scores(primary, secondary), 0.7, "master-code",
            ["master-class", "code", "architecture", f"tongue-{primary}"])
        count += 1

    return count


def main():
    print("Generating Tokenizer Master Class SFT...")

    math_count = generate_semantic_math()
    print(f"  Semantic math records: {math_count}")

    drift_count = generate_drift_corrections()
    print(f"  Drift correction records: {drift_count}")

    null_count = generate_null_space()
    print(f"  Null-space records: {null_count}")

    code_count = generate_code_records()
    print(f"  Code implementation records: {code_count}")

    total = len(RECORDS)
    print(f"\n  TOTAL: {total} records")

    # Validate no wrong names
    wrong_names = {"Koson", "KOSON", "Aven", "AVEN", "Rulon", "RULON", "Cael", "CAEL", "Umbra", "UMBRA", "Dron", "DRON"}
    full_text = json.dumps(RECORDS)
    for wrong in wrong_names:
        if wrong in full_text:
            print(f"  WARNING: Wrong name '{wrong}' found in records!")

    out_path = OUT_DIR / "tokenizer_master_class_sft.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in RECORDS:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nMaster Class SFT: {total} records -> {out_path}")

    # Stats
    from collections import Counter
    aug_counts = Counter(r["augmentation"] for r in RECORDS)
    tongue_counts = Counter(r["dominant_tongue"] for r in RECORDS)
    diff_avg = sum(r["difficulty"] for r in RECORDS) / len(RECORDS)

    print(f"\nRecord types:")
    for a, c in aug_counts.most_common():
        print(f"  {a:35s} {c}")

    print(f"\nDominant tongue distribution:")
    for t, c in tongue_counts.most_common():
        info = TONGUES[t]
        print(f"  {info['full']:20s} ({t}) {c}")

    print(f"\nAverage difficulty: {diff_avg:.2f}")

    # Show first drift sample for validation
    drift_records = [r for r in RECORDS if r["augmentation"] == "master-drift"]
    if drift_records:
        print("\n" + "=" * 60)
        print("SAMPLE: First drift correction record")
        print("=" * 60)
        sample = drift_records[0]
        for msg in sample["messages"]:
            print(f"\n[{msg['role'].upper()}]:")
            print(msg["content"][:500])
            if len(msg["content"]) > 500:
                print("...")


if __name__ == "__main__":
    main()
