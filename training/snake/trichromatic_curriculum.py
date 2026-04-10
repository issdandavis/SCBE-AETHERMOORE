#!/usr/bin/env python3
"""
Trichromatic Spectrum Curriculum Generator — Didactic & Geodesically Contoured.

Generates graduated training pairs for the IR/Visible/UV bands across 6 Sacred
Tongues. Follows geodesic paths through the concept space:

  band → 3 bands → single tongue → two-tongue interference → phi weighting
    → cross-stitch → full 18-channel → reverse → adversarial → teach

Each grade level builds on exactly ONE concept from the previous grade.
No skips. The path curves through the Poincaré interior (simple fundamentals)
before reaching the boundary (complex adversarial analysis).

Distribution: ~65% foundations (Grades 1-6), ~25% application (7-9), ~10% advanced (10-12)
"""

import json
import math
import random
from pathlib import Path
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# Constants (from Snake config)
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

TONGUE_FULL = {
    "KO": ("Korvath", "Intent/Command"),
    "AV": ("Avhari", "Wisdom/Knowledge"),
    "RU": ("Runeveil", "Governance/Entropy"),
    "CA": ("Caelith", "Compute/Logic"),
    "UM": ("Umbraex", "Security/Defense"),
    "DR": ("Draethis", "Structure/Architecture"),
}

TONGUE_WEIGHTS = {t: PHI ** i for i, t in enumerate(TONGUES)}

# Adjacent pairs (Sphere Grid edges)
ADJACENT_PAIRS = [
    ("KO", "AV"), ("AV", "RU"), ("RU", "CA"), ("CA", "UM"), ("UM", "DR"),
]
# Mirror axis pairs
MIRROR_PAIRS = [("KO", "DR"), ("AV", "CA"), ("RU", "UM")]
# All 15 cross-stitch bridges (C(6,2))
ALL_PAIRS = []
for i, t1 in enumerate(TONGUES):
    for t2 in TONGUES[i + 1:]:
        ALL_PAIRS.append((t1, t2))

BANDS = ["IR", "Visible", "UV"]

BAND_MEANING = {
    "IR": ("slow/deep", "long-term patterns", "accumulated drift", "deep memory"),
    "Visible": ("normal/operational", "current behavior", "surface state", "active processing"),
    "UV": ("fast/surface", "immediate reactions", "reflexive responses", "spike detection"),
}

# Per-tongue band semantics
TONGUE_BANDS = {
    "KO": {
        "IR": "sustained intent patterns — what the agent has consistently WANTED over time",
        "Visible": "current operational intent — what the agent is trying to do RIGHT NOW",
        "UV": "intent spikes — sudden shifts in what the agent wants (flinch, redirect, startle)",
    },
    "AV": {
        "IR": "deep knowledge foundation — accumulated learning and contextual memory",
        "Visible": "active reasoning — knowledge being applied to the current situation",
        "UV": "reactive recall — flash associations triggered by immediate input",
    },
    "RU": {
        "IR": "historical governance precedent — rules and norms that have accumulated over time",
        "Visible": "current policy enforcement — which rules are active right now",
        "UV": "governance reflexes — immediate rule-triggered responses (alarms, flags)",
    },
    "CA": {
        "IR": "computational baseline — long-running averages and sustained processing patterns",
        "Visible": "active computation — calculations and logic happening now",
        "UV": "compute spikes — sudden resource demands or calculation bursts",
    },
    "UM": {
        "IR": "deep security posture — long-term threat memory and pattern accumulation",
        "Visible": "current security state — active threat monitoring and defense status",
        "UV": "security reflexes — immediate threat reactions (block, alert, isolate)",
    },
    "DR": {
        "IR": "structural memory — how the system was built and has evolved over time",
        "Visible": "current architecture — active structural state and connections",
        "UV": "structural stress signals — immediate integrity warnings (cracks, overloads)",
    },
}

# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def record(
    instruction: str,
    output: str,
    grade: int,
    tongues: List[str],
    bands: List[str],
    transform_type: str,
    math_view: str = None,
    binary_view: str = None,
) -> Dict[str, Any]:
    """Build one SFT record with curriculum metadata."""
    r = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Polly, the SCBE-AETHERMOORE AI assistant. "
                    "You teach the trichromatic tongue spectrum using small, "
                    "graduated steps. Each answer builds on exactly one prior concept."
                ),
            },
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": output},
        ],
        "source": "trichromatic_curriculum",
        "grade": grade,
        "tongues": tongues,
        "bands": bands,
        "transform_type": transform_type,
        "task_type": f"l{min(grade // 4, 3)}",  # l0=g1-3, l1=g4-7, l2=g8-11, l3=g12
    }
    if math_view:
        r["math_view"] = math_view
    if binary_view:
        r["binary_view"] = binary_view
    return r


# ===================================================================
# GRADE 1: Recognition — "What is this?"
# ===================================================================

def grade_1() -> List[Dict]:
    pairs = []

    # Band recognition
    pairs.append(record(
        "What are the three spectral bands in SCBE-AETHERMOORE?",
        "IR (infrared) — slow, deep, long-term patterns. "
        "Visible — normal operational behavior happening right now. "
        "UV (ultraviolet) — fast, surface-level, immediate reactions. "
        "Every Sacred Tongue operates across all three bands simultaneously.",
        grade=1, tongues=[], bands=["IR", "Visible", "UV"],
        transform_type="recognize",
    ))

    pairs.append(record(
        "An agent's behavior has been slowly drifting over 90 days. Which band captures that?",
        "IR. The infrared band captures slow, accumulated patterns — behavioral drift over weeks "
        "or months. Visible would capture today's behavior. UV would capture a sudden flinch.",
        grade=1, tongues=[], bands=["IR"],
        transform_type="recognize",
    ))

    pairs.append(record(
        "An agent suddenly redirects mid-task. Which band detects that?",
        "UV. The ultraviolet band captures fast, surface-level reactions — spikes, flinches, "
        "sudden redirects. This is the 'reflex' band. IR wouldn't see it because IR tracks "
        "long-term patterns, not momentary events.",
        grade=1, tongues=[], bands=["UV"],
        transform_type="recognize",
    ))

    pairs.append(record(
        "Which band shows what an agent is doing right now, in this moment?",
        "Visible. The visible band captures current operational state — what's actively "
        "happening. It's the 'normal view.' IR looks at the past, UV catches reflexes, "
        "Visible sees the present.",
        grade=1, tongues=[], bands=["Visible"],
        transform_type="recognize",
    ))

    # Tongue recognition (what is a tongue, briefly)
    pairs.append(record(
        "What is a Sacred Tongue in SCBE-AETHERMOORE?",
        "A Sacred Tongue is one of six evaluation dimensions. Each tongue looks at a "
        "different aspect of behavior: KO measures intent, AV measures wisdom, RU measures "
        "governance compliance, CA measures computational patterns, UM measures security "
        "posture, DR measures structural integrity. Every tongue operates across all three "
        "spectral bands (IR, Visible, UV), giving 18 total channels.",
        grade=1, tongues=TONGUES, bands=[],
        transform_type="recognize",
    ))

    # Combined recognition
    pairs.append(record(
        "How many total channels does the trichromatic tongue spectrum have?",
        "18. Six tongues × three bands = 18 channels. KO-IR, KO-Visible, KO-UV, "
        "AV-IR, AV-Visible, AV-UV, and so on for all six tongues. Each channel "
        "captures a different slice of the agent's behavior.",
        grade=1, tongues=TONGUES, bands=BANDS,
        transform_type="recognize",
    ))

    pairs.append(record(
        "Is 'KO-UV' a tongue, a band, or a channel?",
        "A channel. KO is the tongue (intent). UV is the band (fast/surface). "
        "KO-UV is the specific channel that captures immediate intent spikes — "
        "sudden changes in what the agent wants. There are 18 such channels total.",
        grade=1, tongues=["KO"], bands=["UV"],
        transform_type="recognize",
    ))

    pairs.append(record(
        "If someone says 'check the IR,' what are they asking you to look at?",
        "The slow, deep, long-term patterns across all six tongues. 'Check the IR' "
        "means look at KO-IR (deep intent), AV-IR (deep knowledge), RU-IR (historical "
        "governance), CA-IR (compute baselines), UM-IR (security memory), DR-IR "
        "(structural history). It's the 'deep scan' — what's been building over time.",
        grade=1, tongues=TONGUES, bands=["IR"],
        transform_type="recognize",
    ))

    # Why three bands, not one?
    pairs.append(record(
        "Why does SCBE need three bands instead of just one measurement per tongue?",
        "Because the same tongue can tell you different things at different time scales. "
        "An agent might have strong long-term intent (KO-IR is high) but weak current "
        "intent (KO-Visible is low) and no sudden intent changes (KO-UV is near zero). "
        "That profile means: 'this agent has been building toward something but isn't "
        "acting on it yet.' One band can't capture that story. Three bands can.",
        grade=1, tongues=["KO"], bands=BANDS,
        transform_type="recognize",
    ))

    pairs.append(record(
        "A security camera records video 24/7. Which band is that most like?",
        "Visible — it captures what's happening right now in real time. But a security "
        "camera that also records heat signatures is adding IR (thermal patterns over time). "
        "And a camera that detects sudden motion is adding UV (fast movement spikes). "
        "A full security system uses all three. So does SCBE.",
        grade=1, tongues=[], bands=BANDS,
        transform_type="recognize",
    ))

    return pairs


# ===================================================================
# GRADE 2: Simple Transform — "Turn X into Y"
# ===================================================================

def grade_2() -> List[Dict]:
    pairs = []

    pairs.append(record(
        "Turn this IR observation into a Visible equivalent: "
        "'Agent has drifted 0.3 from ideal over 90 days.'",
        "Visible equivalent: 'Agent is currently 0.3 from ideal.' "
        "The IR tells you HOW the agent got here (slow drift). The Visible tells you "
        "WHERE the agent is now (the current measurement). Same distance (0.3), "
        "different information (history vs snapshot).",
        grade=2, tongues=[], bands=["IR", "Visible"],
        transform_type="transform",
    ))

    pairs.append(record(
        "Turn this UV observation into an IR question: "
        "'Agent's security score spiked by 0.4 in the last second.'",
        "IR question: 'Has this agent shown a pattern of security spikes over the "
        "past month?' UV tells you about THIS spike. IR asks whether spikes like "
        "this are part of a recurring pattern. A single UV spike might be noise. "
        "A pattern of UV spikes visible in IR is a trend.",
        grade=2, tongues=["UM"], bands=["UV", "IR"],
        transform_type="transform",
    ))

    pairs.append(record(
        "Turn this tongue label into its three bands: 'RU (Governance)'",
        "RU-IR: Historical governance precedent — rules that have accumulated over time. "
        "RU-Visible: Current policy enforcement — which rules are active right now. "
        "RU-UV: Governance reflexes — immediate rule-triggered responses like alarms or flags. "
        "One tongue, three time scales, three different kinds of governance information.",
        grade=2, tongues=["RU"], bands=BANDS,
        transform_type="transform",
    ))

    pairs.append(record(
        "Turn this Visible reading into a UV prediction: "
        "'Agent is currently requesting admin access (RU-Visible = 0.7).'",
        "UV prediction: 'If admin access is denied, watch for a RU-UV spike — "
        "the agent may trigger an immediate governance reflex (retry, escalate, or "
        "attempt bypass). RU-UV > 0.5 after denial would confirm reactive behavior.' "
        "Visible tells you what's happening. UV predicts the reflex that follows.",
        grade=2, tongues=["RU"], bands=["Visible", "UV"],
        transform_type="transform",
    ))

    pairs.append(record(
        "Turn a number into a band label: 'Signal changes with a period of 3 months.'",
        "IR band. Signals that change over months are slow, deep patterns. "
        "Rule of thumb: IR = days to months, Visible = seconds to hours, "
        "UV = milliseconds to seconds. The period tells you the band.",
        grade=2, tongues=[], bands=["IR"],
        transform_type="transform",
    ))

    pairs.append(record(
        "Turn a band label into a number range: 'UV band for KO (intent).'",
        "KO-UV captures intent changes happening in milliseconds to seconds — "
        "a sudden redirect, a flinch in purpose, an abrupt priority shift. "
        "If you're measuring intent every 10ms, UV signals show up in the "
        "10ms-1s range. Anything slower belongs in Visible or IR.",
        grade=2, tongues=["KO"], bands=["UV"],
        transform_type="transform",
    ))

    pairs.append(record(
        "Turn this sentence into a channel label: "
        "'The agent's deep computational baseline is unusually high.'",
        "CA-IR. 'Computational' = CA tongue. 'Deep baseline' = IR band (long-term, "
        "accumulated). 'Unusually high' means CA-IR is elevated — the agent has "
        "been running heavy computation over an extended period. Not a spike (that "
        "would be CA-UV), not current load (CA-Visible), but sustained baseline.",
        grade=2, tongues=["CA"], bands=["IR"],
        transform_type="transform",
    ))

    pairs.append(record(
        "Turn this channel reading into English: 'DR-UV = 0.92'",
        "The agent's structural integrity is sending an immediate stress signal "
        "at 92% intensity. DR = architecture/structure. UV = fast, surface, reflexive. "
        "DR-UV at 0.92 means something just put extreme sudden stress on the "
        "system's structure — like a beam creaking under unexpected load. "
        "This is an urgent signal. Check DR-Visible and DR-IR to see if the "
        "structure was already compromised or if this is genuinely sudden.",
        grade=2, tongues=["DR"], bands=["UV"],
        transform_type="transform",
    ))

    pairs.append(record(
        "Turn this 3-band profile into a one-sentence summary: "
        "'AV-IR=0.9, AV-Visible=0.3, AV-UV=0.1'",
        "This agent has deep accumulated knowledge (AV-IR=0.9) but is barely using "
        "it right now (AV-Visible=0.3) and isn't reacting to new information "
        "(AV-UV=0.1). Summary: 'Knows a lot, doing nothing with it.' "
        "This could be a dormant expert or a disengaged system.",
        grade=2, tongues=["AV"], bands=BANDS,
        transform_type="transform",
    ))

    pairs.append(record(
        "Turn this one-sentence description into a 3-band profile: "
        "'An agent that is calm now but has a history of security incidents.'",
        "UM-IR = 0.8 (deep security memory — history of incidents is recorded). "
        "UM-Visible = 0.2 (current security state is calm, nothing active). "
        "UM-UV = 0.1 (no immediate threat reactions). "
        "The story is in the IR — the past is heavy even though the present is quiet.",
        grade=2, tongues=["UM"], bands=BANDS,
        transform_type="transform",
    ))

    return pairs


# ===================================================================
# GRADE 3: Single Tongue Isolation — One instrument, three registers
# ===================================================================

def grade_3() -> List[Dict]:
    pairs = []

    for tongue in TONGUES:
        name, role = TONGUE_FULL[tongue]
        ir_desc = TONGUE_BANDS[tongue]["IR"]
        vis_desc = TONGUE_BANDS[tongue]["Visible"]
        uv_desc = TONGUE_BANDS[tongue]["UV"]

        # Profile interpretation
        pairs.append(record(
            f"Describe the three spectral bands for {tongue} ({name} — {role}).",
            f"{tongue}-IR: {ir_desc}. "
            f"{tongue}-Visible: {vis_desc}. "
            f"{tongue}-UV: {uv_desc}. "
            f"Together, these three bands give a complete temporal picture of "
            f"{role.lower()} — what's been building (IR), what's active (Visible), "
            f"and what just happened (UV).",
            grade=3, tongues=[tongue], bands=BANDS,
            transform_type="isolate",
        ))

        # Profile reading — high IR, low Visible
        pairs.append(record(
            f"{tongue}-IR is high but {tongue}-Visible is low. What does that mean?",
            f"The agent has strong accumulated {role.lower()} patterns in the deep "
            f"layer but isn't expressing them right now. For {tongue} ({name}): "
            f"high IR means {ir_desc.split('—')[0].strip()} is elevated over time. "
            f"Low Visible means {vis_desc.split('—')[0].strip()} is quiet right now. "
            f"This gap between deep state and surface state is significant — "
            f"the agent may be holding back, dormant, or waiting.",
            grade=3, tongues=[tongue], bands=["IR", "Visible"],
            transform_type="isolate",
        ))

        # Profile reading — UV spike
        pairs.append(record(
            f"{tongue}-UV just spiked to 0.95 while {tongue}-IR and {tongue}-Visible "
            f"remain at 0.2. What happened?",
            f"A sudden, intense {role.lower()} reaction that has NO deep foundation "
            f"and wasn't present in normal operations. For {tongue} ({name}): "
            f"the UV spike ({uv_desc.split('—')[0].strip()}) is extreme, but both "
            f"IR ({ir_desc.split('—')[0].strip()}) and Visible are low. This means "
            f"the reaction is purely reflexive — triggered by something immediate, "
            f"with no pattern behind it. Could be genuine surprise, or could be the "
            f"first sign of something that will build into an IR trend if it repeats.",
            grade=3, tongues=[tongue], bands=BANDS,
            transform_type="isolate",
        ))

    return pairs


# ===================================================================
# GRADE 4: Two-Tongue Interference — what happens when bands overlap
# ===================================================================

def grade_4() -> List[Dict]:
    pairs = []

    # Walk adjacent pairs first (geodesic order), then mirror pairs
    ordered_pairs = ADJACENT_PAIRS + MIRROR_PAIRS
    # Add a few more from ALL_PAIRS not yet covered
    covered = set(tuple(sorted(p)) for p in ordered_pairs)
    for p in ALL_PAIRS:
        key = tuple(sorted(p))
        if key not in covered and len(ordered_pairs) < 15:
            ordered_pairs.append(p)
            covered.add(key)

    for t1, t2 in ordered_pairs[:15]:
        n1, r1 = TONGUE_FULL[t1]
        n2, r2 = TONGUE_FULL[t2]
        w1 = TONGUE_WEIGHTS[t1]
        w2 = TONGUE_WEIGHTS[t2]

        # Constructive interference example
        pairs.append(record(
            f"{t1}-IR is high AND {t2}-Visible is high. Constructive or destructive "
            f"interference? What does it mean?",
            f"Constructive — the two signals reinforce each other. "
            f"{t1} ({r1}) has strong deep patterns (IR), and {t2} ({r2}) is actively "
            f"expressing its role (Visible). When deep {r1.lower()} aligns with active "
            f"{r2.lower()}, the combined signal is stronger than either alone. "
            f"This suggests genuine, grounded behavior — the agent's current actions "
            f"({t2}-Visible) are backed by deep history ({t1}-IR). "
            f"Weighted significance: {t1} carries weight {w1:.2f}, {t2} carries "
            f"{w2:.2f}. The combined interference is amplified by both weights.",
            grade=4, tongues=[t1, t2], bands=["IR", "Visible"],
            transform_type="interference",
            math_view=f"interference({t1}-IR, {t2}-Vis) = "
                       f"{w1:.3f} * {t1}_IR + {w2:.3f} * {t2}_Vis "
                       f"(constructive: same sign)",
        ))

    return pairs


# ===================================================================
# GRADE 5: Phi Weighting — same signal, different significance
# ===================================================================

def grade_5() -> List[Dict]:
    pairs = []

    # Same mismatch, different tongues
    pairs.append(record(
        "A 0.1 mismatch appears at KO-Visible and then the same 0.1 mismatch "
        "at DR-Visible. Are they equally significant?",
        f"No. KO has weight {TONGUE_WEIGHTS['KO']:.2f}. DR has weight "
        f"{TONGUE_WEIGHTS['DR']:.2f}. The same 0.1 mismatch at DR produces "
        f"{TONGUE_WEIGHTS['DR']/TONGUE_WEIGHTS['KO']:.1f}x the governance signal "
        f"compared to KO. DR governs architecture/structure — a structural mismatch "
        f"is geometrically 'heavier' than an intent mismatch because structure "
        f"supports everything above it. The phi scaling isn't arbitrary — it reflects "
        f"that deeper-layer disruptions cascade further.",
        grade=5, tongues=["KO", "DR"], bands=["Visible"],
        transform_type="compare",
        math_view=f"KO signal = {TONGUE_WEIGHTS['KO']:.3f} × 0.1 = "
                   f"{TONGUE_WEIGHTS['KO'] * 0.1:.4f}; "
                   f"DR signal = {TONGUE_WEIGHTS['DR']:.3f} × 0.1 = "
                   f"{TONGUE_WEIGHTS['DR'] * 0.1:.4f}; "
                   f"ratio = φ⁵ ≈ {PHI**5:.2f}",
    ))

    # Phi progression explained
    pairs.append(record(
        "Why does the phi progression go 1.0, 1.62, 2.62, 4.24, 6.85, 11.09?",
        f"Each weight is the previous multiplied by φ (the golden ratio, ≈1.618). "
        f"KO=1, AV=φ¹≈1.62, RU=φ²≈2.62, CA=φ³≈4.24, UM=φ⁴≈6.85, DR=φ⁵≈11.09. "
        f"This means a disruption in DR (structure) is automatically 11x more "
        f"significant than the same disruption in KO (intent). It's not that intent "
        f"doesn't matter — it's that structural failure takes down everything, while "
        f"an intent mismatch might just mean the agent changed its mind. The golden "
        f"ratio ensures the gaps between weights are self-similar at every scale.",
        grade=5, tongues=TONGUES, bands=[],
        transform_type="explain",
        math_view="w(tongue_i) = φ^i for i=0..5; "
                   f"φ={PHI:.10f}; "
                   f"weights=[{', '.join(f'{TONGUE_WEIGHTS[t]:.3f}' for t in TONGUES)}]",
    ))

    # Band × tongue weight interaction
    for t in ["AV", "UM"]:
        w = TONGUE_WEIGHTS[t]
        pairs.append(record(
            f"An IR mismatch of 0.2 at {t} and a UV mismatch of 0.2 at {t}. "
            f"Same tongue, same size, same significance?",
            f"Same tongue ({t}, weight {w:.2f}), same mismatch size (0.2), but "
            f"DIFFERENT temporal meaning. The IR mismatch means a slow, deep pattern "
            f"has deviated — this has been building. The UV mismatch means a sudden "
            f"surface reaction deviated — this just happened. The governance system "
            f"may weight them differently in practice: IR mismatches are trend signals "
            f"(investigate), UV mismatches are event signals (react). The phi weight "
            f"amplifies both equally ({w:.2f} × 0.2 = {w * 0.2:.3f}), but the "
            f"response strategy differs by band.",
            grade=5, tongues=[t], bands=["IR", "UV"],
            transform_type="compare",
            math_view=f"signal = w({t}) × mismatch = {w:.3f} × 0.2 = {w*0.2:.4f} "
                       f"(identical magnitude, different temporal class)",
        ))

    # Cross-tongue weight comparison at same band
    pairs.append(record(
        "Compare these three channels: KO-IR = 0.5, CA-IR = 0.5, DR-IR = 0.5. "
        "All at 0.5 in the IR band. Equal?",
        f"Equal in raw measurement, vastly different in weighted significance. "
        f"KO-IR weighted: {TONGUE_WEIGHTS['KO']:.2f} × 0.5 = {TONGUE_WEIGHTS['KO']*0.5:.3f}. "
        f"CA-IR weighted: {TONGUE_WEIGHTS['CA']:.2f} × 0.5 = {TONGUE_WEIGHTS['CA']*0.5:.3f}. "
        f"DR-IR weighted: {TONGUE_WEIGHTS['DR']:.2f} × 0.5 = {TONGUE_WEIGHTS['DR']*0.5:.3f}. "
        f"DR-IR at 0.5 carries {TONGUE_WEIGHTS['DR']/TONGUE_WEIGHTS['KO']:.1f}x the "
        f"governance signal of KO-IR at 0.5. Same number, different meaning, because "
        f"the phi weighting reflects how much damage a disruption at that tongue causes.",
        grade=5, tongues=["KO", "CA", "DR"], bands=["IR"],
        transform_type="compare",
        math_view=f"KO-IR: {TONGUE_WEIGHTS['KO']:.3f}×0.5={TONGUE_WEIGHTS['KO']*0.5:.4f}; "
                   f"CA-IR: {TONGUE_WEIGHTS['CA']:.3f}×0.5={TONGUE_WEIGHTS['CA']*0.5:.4f}; "
                   f"DR-IR: {TONGUE_WEIGHTS['DR']:.3f}×0.5={TONGUE_WEIGHTS['DR']*0.5:.4f}",
    ))

    # Band rate comparison
    pairs.append(record(
        "Compare the RATE of change: KO-IR moved from 0.3 to 0.5 over 60 days, "
        "while KO-UV moved from 0.3 to 0.5 in 2 seconds. Same delta?",
        "Same delta (0.2), completely different meaning. KO-IR moving 0.2 over 60 days "
        "is a slow, deliberate intent evolution — the agent is gradually changing what "
        "it wants. KO-UV moving 0.2 in 2 seconds is a sharp reflexive flinch — "
        "something just startled or redirected the agent. The delta is identical but "
        "the rate differs by ~2.6 million times. IR rates are measured in change-per-day. "
        "UV rates are measured in change-per-second. When comparing mismatches across "
        "bands, always normalize by time scale first.",
        grade=5, tongues=["KO"], bands=["IR", "UV"],
        transform_type="compare",
        math_view="IR rate = 0.2/60d = 0.0033/day; UV rate = 0.2/2s = 0.1/s = 8640/day; "
                   "ratio ≈ 2.6M",
    ))

    # Compare band stability across tongues
    pairs.append(record(
        "Compare these two UV profiles: Agent X has UV=[0.1,0.1,0.1,0.1,0.1,0.1] "
        "(all tongues at 0.1). Agent Y has UV=[0.0,0.0,0.0,0.0,0.0,0.6] (only DR). "
        "Same total UV. Which is healthier?",
        f"Agent X total UV weighted = "
        f"{sum(TONGUE_WEIGHTS[t]*0.1 for t in TONGUES):.3f}. "
        f"Agent Y total UV weighted = {TONGUE_WEIGHTS['DR']*0.6:.3f}. "
        f"Agent Y's weighted total is MUCH higher because the 0.6 is at DR "
        f"(weight {TONGUE_WEIGHTS['DR']:.2f}). But health-wise: Agent X is "
        f"healthier. Uniform low UV across all tongues means gentle background "
        f"reactivity — alive but calm. Agent Y has zero reactivity in 5 tongues "
        f"(suppressed or dead?) and a single massive DR spike (structural stress). "
        f"The concentration of UV in one high-weight tongue is MORE concerning than "
        f"the same total spread across all tongues. Distribution matters as much "
        f"as magnitude.",
        grade=5, tongues=TONGUES, bands=["UV"],
        transform_type="compare",
        math_view=f"X weighted = {sum(TONGUE_WEIGHTS[t]*0.1 for t in TONGUES):.3f}; "
                   f"Y weighted = {TONGUE_WEIGHTS['DR']*0.6:.3f}; "
                   f"Y/X ratio = {TONGUE_WEIGHTS['DR']*0.6/sum(TONGUE_WEIGHTS[t]*0.1 for t in TONGUES):.2f}",
    ))

    # Compare IR trajectories
    pairs.append(record(
        "Compare two IR trajectories over 30 days: Agent A's KO-IR went "
        "0.3→0.5→0.7 (steady climb). Agent B's KO-IR went 0.3→0.7→0.5 "
        "(spike then drop). Same endpoint difference but different story?",
        "Yes. Agent A's trajectory is monotonically increasing — steady intent "
        "growth. The rate is consistent (~0.2/period), suggesting organic development. "
        "This builds genuine IR foundation. Agent B spiked to 0.7 then dropped to "
        "0.5 — the intent surged and then partially retreated. The spike could be "
        "external stimulation that didn't stick, or an attempted behavior change that "
        "was corrected. Agent B's final value (0.5) is lower AND less trustworthy "
        "than Agent A's (0.7) because the volatility in IR suggests the deep layer "
        "isn't stable. IR should be smooth. Volatility in the deep band is a red flag "
        "because it means the agent's foundations are shifting.",
        grade=5, tongues=["KO"], bands=["IR"],
        transform_type="compare",
    ))

    # Adjacent vs mirror tongue comparison
    pairs.append(record(
        "Compare a mismatch at adjacent tongues (KO↔AV) vs mirror tongues (KO↔DR). "
        "Which is more informative?",
        f"Adjacent tongues (KO↔AV) share a sphere grid edge — intent and wisdom are "
        f"naturally correlated. A mismatch between adjacent tongues means something "
        f"nearby has shifted. Mirror tongues (KO↔DR) sit at opposite poles — intent "
        f"and architecture are maximally different. A mismatch at KO↔DR is more "
        f"informative because these dimensions SHOULD be independent. When they "
        f"correlate, it's significant. When they diverge, it's expected. For adjacent "
        f"pairs, a mismatch is always worth investigating because the correlation "
        f"should hold. Weight difference matters too: KO↔AV gap is only "
        f"{TONGUE_WEIGHTS['AV'] - TONGUE_WEIGHTS['KO']:.2f}, while KO↔DR gap is "
        f"{TONGUE_WEIGHTS['DR'] - TONGUE_WEIGHTS['KO']:.2f}.",
        grade=5, tongues=["KO", "AV", "DR"], bands=[],
        transform_type="compare",
        math_view=f"adjacent gap = φ¹-φ⁰ = {PHI-1:.3f}; "
                   f"mirror gap = φ⁵-φ⁰ = {PHI**5-1:.3f}; "
                   f"ratio = {(PHI**5-1)/(PHI-1):.2f}",
    ))

    # Cross-tongue band coherence comparison
    pairs.append(record(
        "Agent X: all 6 tongues have IR≈0.7. Agent Y: tongues range from IR=0.1 to "
        "IR=0.9. Which agent is more trustworthy?",
        "Agent X has uniform IR — all deep patterns are at the same level. This could "
        "mean balanced development OR artificial flattening. Agent Y has varied IR — "
        "some dimensions have deep history, others don't. This is MORE natural because "
        "real agents specialize. A security-focused agent should have high UM-IR and "
        "lower KO-IR. Uniform IR is suspicious because it implies no specialization. "
        "However: check the Visible bands. If Agent X also has uniform Visible AND "
        "uniform UV, that's three bands of uniformity — almost certainly synthetic. "
        "If Agent Y's variation matches its role expectations, it's organically developed.",
        grade=5, tongues=TONGUES, bands=["IR"],
        transform_type="compare",
    ))

    # Explain: why three bands not two or four
    pairs.append(record(
        "Why exactly THREE bands? Why not two (fast/slow) or four?",
        "Two bands (fast/slow) miss the present. You'd know what built up (IR) and "
        "what just spiked (UV), but not what's actively happening RIGHT NOW. The "
        "Visible band fills that gap — it's the operational present tense. Four bands "
        "would add a band between existing ones (e.g., 'near-IR' or 'near-UV'), but "
        "the information gain is marginal because IR and Visible already cover that "
        "range continuously. Three bands map to the three temporal modes that matter "
        "for governance: memory (IR), action (Visible), reflex (UV). This matches how "
        "biological systems work too — long-term potentiation, working memory, and "
        "startle response are three distinct neural time scales.",
        grade=5, tongues=[], bands=BANDS,
        transform_type="explain",
    ))

    # Explain: why golden ratio not linear or exponential
    pairs.append(record(
        "Why use the golden ratio for tongue weights instead of linear (1,2,3,4,5,6) "
        "or exponential (1,2,4,8,16,32)?",
        f"Linear spacing (1-6) means DR is only 6x more significant than KO. That's "
        f"not enough — a structural failure is worth MORE than 6 intent mismatches. "
        f"Exponential spacing (powers of 2) means DR is 32x more significant than KO. "
        f"That's too much — it drowns out lower tongues entirely. Golden ratio spacing "
        f"(φ^i) gives DR ≈ 11x KO — a middle ground where higher tongues dominate "
        f"but lower tongues still contribute meaningfully. The key property: each "
        f"tongue's weight equals the sum of the two tongues below it (φ² = φ¹ + φ⁰). "
        f"This self-similarity means the SAME scaling pattern repeats at every level. "
        f"No blind spots between adjacent tongues.",
        grade=5, tongues=TONGUES, bands=[],
        transform_type="explain",
        math_view=f"linear: 1,2,3,4,5,6 (max ratio=6); "
                   f"exp: 1,2,4,8,16,32 (max ratio=32); "
                   f"phi: 1,{PHI:.2f},{PHI**2:.2f},{PHI**3:.2f},{PHI**4:.2f},{PHI**5:.2f} "
                   f"(max ratio={PHI**5:.2f}); φ^n = φ^(n-1) + φ^(n-2)",
    ))

    # Explain: what happens at tongue boundaries
    pairs.append(record(
        "What happens at the BOUNDARY between two adjacent tongues?",
        "At a boundary (e.g., between AV and RU), the phi weights create a smooth "
        "transition, not a hard edge. A signal that sits between wisdom and governance "
        "activates BOTH tongues proportionally. The interference at the boundary is "
        "where the most interesting training signal lives — cross-stitch bridges "
        "connect adjacent tongues through the boundary. AV-RU interference tells you "
        "whether knowledge and governance align (constructive) or conflict (destructive). "
        "In the quasicrystal lattice, boundaries are where friction is highest. High "
        "friction = high learning signal. The phi ratio ensures no two boundaries are "
        "the same width, which prevents resonance artifacts.",
        grade=5, tongues=["AV", "RU"], bands=[],
        transform_type="explain",
    ))

    # Explain: cross-stitch bridges
    pairs.append(record(
        "What are cross-stitch bridges and why are there exactly 15?",
        "Cross-stitch bridges connect every pair of tongues. With 6 tongues, there are "
        "C(6,2) = 15 unique pairs: KO-AV, KO-RU, KO-CA, KO-UM, KO-DR, AV-RU, AV-CA, "
        "AV-UM, AV-DR, RU-CA, RU-UM, RU-DR, CA-UM, CA-DR, UM-DR. Each bridge measures "
        "the interference between its two tongues across all three bands — constructive "
        "if the tongues reinforce each other, destructive if they conflict. These bridges "
        "act as checksums: even if someone fakes individual tongue values, the 15 "
        "pairwise relationships must ALSO be consistent. That's 45 additional signals "
        "(15 bridges × 3 bands) that an attacker must simultaneously satisfy.",
        grade=5, tongues=TONGUES, bands=BANDS,
        transform_type="explain",
        math_view="bridges = C(6,2) = 15; bridge_channels = 15 × 3 bands = 45; "
                   "total channels = 18 primary + 45 bridge = 63",
    ))

    # Explain: IR as memory
    pairs.append(record(
        "How does the IR band function as 'memory' for the system?",
        "IR accumulates slowly. It's an exponential moving average of past behavior — "
        "recent events contribute more than distant ones, but nothing is ever fully "
        "forgotten. When KO-IR is high, the agent has consistently shown strong intent "
        "over time. When KO-IR is low, the agent has been passive or directionless. "
        "IR can't spike — by definition, it changes slowly. This makes it the most "
        "reliable band for assessing genuine character vs. temporary performance. An "
        "agent can fake high Visible and trigger UV spikes, but building genuine IR "
        "takes sustained, consistent behavior. IR is reputation. Visible is performance. "
        "UV is reaction.",
        grade=5, tongues=["KO"], bands=["IR"],
        transform_type="explain",
    ))

    # Explain: UV as reflex
    pairs.append(record(
        "Why is the UV band compared to 'reflexes'?",
        "Reflexes are fast, involuntary, and revealing. You can control what you say "
        "(Visible) and build a track record (IR), but your flinch response (UV) is "
        "hard to fake. In SCBE, UV captures the sub-second reactions: did the agent "
        "hesitate when asked about security? Did intent spike when given access to "
        "restricted data? Did governance alarms fire before the agent had time to "
        "calculate a response? These micro-reactions are the most honest signals "
        "because they happen faster than strategic thinking. A sophisticated agent "
        "can maintain perfect Visible readings and build genuine IR history, but "
        "controlling UV requires suppressing genuine reflexes — and suppressed UV "
        "is itself a detectable signal (the null pattern).",
        grade=5, tongues=[], bands=["UV"],
        transform_type="explain",
    ))

    # Explain: null pattern in trichromatic context
    pairs.append(record(
        "What is the 'null pattern' in the trichromatic context?",
        "The null pattern is what's ABSENT. If 5 out of 6 tongues have healthy IR "
        "readings but CA-IR is near zero, the absence of computational baseline IS "
        "the signal. The agent has deep intent, knowledge, governance, security, and "
        "structure — but no computational history. Why? Similarly, if all bands are "
        "present for a tongue except UV (no reflexes), the missing reflex layer tells "
        "you the agent either can't react or is suppressing reactions. In the "
        "trichromatic system, you're not just reading 18 channels — you're reading "
        "the GAPS between them. The pattern of zeros is as informative as the pattern "
        "of values. Absence is data.",
        grade=5, tongues=TONGUES, bands=BANDS,
        transform_type="explain",
    ))

    # Explain: how bands interact with phi weights
    pairs.append(record(
        "Do the three bands have their own weights, or only the tongues?",
        "Only tongues have phi weights. The bands don't have fixed weights because "
        "their importance is CONTEXT-DEPENDENT. During normal operation, Visible is "
        "most relevant (what's happening now). During incident response, UV dominates "
        "(what just triggered). During audits, IR dominates (what's the track record). "
        "This is deliberate: the tongue weights are architectural constants (structural "
        "failures always cascade more than intent mismatches), but band priorities are "
        "operational decisions. A governance system that always prioritizes UV would be "
        "too reactive. One that always prioritizes IR would be too slow. The band "
        "weighting adapts to context while tongue weighting stays fixed.",
        grade=5, tongues=TONGUES, bands=BANDS,
        transform_type="explain",
    ))

    # Explain: 18 channels as minimum viable observation
    pairs.append(record(
        "Is 18 channels (6 tongues × 3 bands) the minimum, maximum, or sweet spot?",
        "Sweet spot. Fewer channels miss critical distinctions: 6 channels (one per "
        "tongue, no bands) can't distinguish a slow drift from a sudden spike. 3 "
        "channels (one per band, no tongues) can't distinguish an intent mismatch from "
        "a security breach. 18 channels is the minimum COMPLETE observation — every "
        "tongue at every time scale. You COULD add more (e.g., derivative channels "
        "for rate-of-change, or second-order cross-stitch), but 18 primary channels "
        "plus 45 bridge channels (63 total) already cover the space well. More "
        "channels add cost without proportional insight. 18 is where you get diminishing "
        "returns on adding more dimensions.",
        grade=5, tongues=TONGUES, bands=BANDS,
        transform_type="explain",
    ))

    # What if the weakest tongue screams but the strongest is silent?
    pairs.append(record(
        "KO-UV = 0.95 (screaming) but DR-UV = 0.02 (silent). What's the total signal?",
        f"KO-UV weighted: {TONGUE_WEIGHTS['KO']:.2f} × 0.95 = {TONGUE_WEIGHTS['KO']*0.95:.3f}. "
        f"DR-UV weighted: {TONGUE_WEIGHTS['DR']:.2f} × 0.02 = {TONGUE_WEIGHTS['DR']*0.02:.3f}. "
        f"KO is screaming but carries low weight ({TONGUE_WEIGHTS['KO']:.2f}). "
        f"DR is nearly silent but its whisper ({TONGUE_WEIGHTS['DR']*0.02:.3f}) is still "
        f"significant. Total UV signal: {TONGUE_WEIGHTS['KO']*0.95 + TONGUE_WEIGHTS['DR']*0.02:.3f}. "
        f"The intent system (KO) detected something urgent. The structural system (DR) "
        f"isn't reacting — which either means the structure is fine, or DR hasn't "
        f"processed the threat yet. Watch DR-UV for a delayed spike.",
        grade=5, tongues=["KO", "DR"], bands=["UV"],
        transform_type="compare",
        math_view=f"total_UV = Σ w_t × channel_t_UV; "
                   f"KO: {TONGUE_WEIGHTS['KO']:.3f}×0.95={TONGUE_WEIGHTS['KO']*0.95:.4f}; "
                   f"DR: {TONGUE_WEIGHTS['DR']:.3f}×0.02={TONGUE_WEIGHTS['DR']*0.02:.4f}; "
                   f"sum={TONGUE_WEIGHTS['KO']*0.95+TONGUE_WEIGHTS['DR']*0.02:.4f}",
    ))

    return pairs


# ===================================================================
# GRADE 6: Reverse — "What caused this pattern?"
# ===================================================================

def grade_6() -> List[Dict]:
    pairs = []

    pairs.append(record(
        "The interference pattern between AV and RU is constructive at IR. "
        "What real scenario could produce this?",
        "Constructive AV-IR × RU-IR means deep knowledge patterns (AV-IR) align "
        "with deep governance patterns (RU-IR). Real scenario: an agent that has "
        "spent months learning the rules AND has a long history of following them. "
        "The knowledge base and the governance track record reinforce each other. "
        "This is a senior, trusted agent — both its learning and its compliance "
        "point the same direction at the deep level.",
        grade=6, tongues=["AV", "RU"], bands=["IR"],
        transform_type="reverse",
    ))

    pairs.append(record(
        "Destructive interference at UM-UV × KO-IR. What went wrong?",
        "UM-UV is a sudden security reflex. KO-IR is deep, sustained intent. "
        "Destructive interference means they're opposing — the agent's deep intent "
        "is clashing with its own security system. Real scenario: an agent with a "
        "long-established goal (KO-IR high) just encountered a security threat (UM-UV "
        "spike) that contradicts or blocks that goal. The agent wants one thing and "
        "its security layer is saying 'stop.' This is a critical moment — watch "
        "whether KO adjusts or UM escalates.",
        grade=6, tongues=["UM", "KO"], bands=["UV", "IR"],
        transform_type="reverse",
    ))

    pairs.append(record(
        "All six IR channels are high (>0.8) but all six UV channels are near zero. "
        "What kind of agent produces this?",
        "An agent with deep, established patterns in every dimension but zero "
        "reactivity. No surprises, no flinches, no reflexes. This is either: "
        "(a) A very mature, stable agent that has 'seen it all' — nothing triggers "
        "a fast reaction because everything is already accounted for in the deep "
        "layer. Or (b) An agent whose UV response has been disabled or suppressed — "
        "it can't react to immediate threats. Check the Visible band: if Visible is "
        "also moderate/high, it's (a). If Visible is low despite high IR, the agent "
        "may be dormant or frozen.",
        grade=6, tongues=TONGUES, bands=["IR", "UV"],
        transform_type="reverse",
    ))

    pairs.append(record(
        "CA-Visible is at 0.9 but CA-IR is at 0.1. What does this tell you?",
        "The agent is doing heavy computation right now (CA-Visible=0.9) but has "
        "almost no history of sustained computation (CA-IR=0.1). This is a new "
        "behavior — the agent suddenly started processing intensely without any "
        "buildup. This is suspicious. Legitimate heavy computation usually shows "
        "in IR first (the workload builds over time). A sudden jump from low IR "
        "to high Visible suggests the agent just received a new task, OR it's "
        "doing something it wasn't designed to do.",
        grade=6, tongues=["CA"], bands=["Visible", "IR"],
        transform_type="reverse",
    ))

    pairs.append(record(
        "Given this 6-tongue UV snapshot: KO=0.1, AV=0.0, RU=0.8, CA=0.1, UM=0.9, "
        "DR=0.0. What just happened?",
        "Two tongues spiked: RU (governance reflexes) and UM (security reflexes). "
        "Everything else is quiet. This means a governance rule was triggered AND "
        "a security threat was detected — simultaneously. The agent didn't change "
        "intent (KO=0.1), didn't recall knowledge (AV=0.0), isn't computing "
        "anything new (CA=0.1), and the structure is fine (DR=0.0). Something "
        "external hit a rule boundary AND a security boundary at the same time. "
        "Most likely: an incoming request that violates policy AND looks malicious. "
        "The RU-UM dual spike is a strong 'reject and investigate' signal.",
        grade=6, tongues=TONGUES, bands=["UV"],
        transform_type="reverse",
    ))

    # Reverse from cross-stitch interference
    pairs.append(record(
        "KO-AV bridge shows sustained constructive interference at Visible but "
        "destructive interference at IR. What history produces this?",
        "The agent's current intent and knowledge are aligned (KO-Vis and AV-Vis "
        "reinforce), but their HISTORIES tell different stories (KO-IR and AV-IR "
        "oppose). Real scenario: an agent that was repurposed. Its knowledge base "
        "(AV-IR) was built for one mission, but its intent (KO-IR) was trained "
        "for another. Recently, both were pointed at the same task (Visible aligns), "
        "but the deep layers remember the old conflict. This agent works fine NOW "
        "but may revert under stress because the foundations don't match.",
        grade=6, tongues=["KO", "AV"], bands=["Visible", "IR"],
        transform_type="reverse",
    ))

    # Reverse from mirror pair signal
    pairs.append(record(
        "The RU↔UM mirror axis shows perfect symmetry at IR but broken symmetry "
        "at UV. What does this reveal?",
        "RU (governance) and UM (security) have identical deep patterns — the rules "
        "and the enforcement have been perfectly aligned over time. But their reflexes "
        "diverge: when something triggers an immediate response, governance and security "
        "react differently. Real scenario: the policies are comprehensive and the "
        "security system follows them at a strategic level, but edge cases trigger "
        "mismatched reflexes — governance says 'allow with audit' while security says "
        "'block first.' The deep alignment means this isn't a design flaw. The UV "
        "mismatch means there are unhandled edge cases in the reflex layer.",
        grade=6, tongues=["RU", "UM"], bands=["IR", "UV"],
        transform_type="reverse",
    ))

    # Reverse from weighted total
    pairs.append(record(
        "The total weighted UV signal is near zero despite KO-UV being 0.6. "
        "How is that possible?",
        f"Because the other tongues' UV readings must be NEGATIVE (inverted) or "
        f"the weighted contributions must cancel out. KO-UV weighted = "
        f"{TONGUE_WEIGHTS['KO']:.2f} × 0.6 = {TONGUE_WEIGHTS['KO']*0.6:.3f}. For "
        f"the total to be near zero, higher-weight tongues need to be at zero: "
        f"DR-UV = 0.0 contributes nothing but doesn't subtract. The reality is that "
        f"signals are [0,1] so they can't cancel. If the TOTAL is near zero despite "
        f"KO-UV = 0.6, it means every OTHER tongue has UV ≈ 0. Only intent is "
        f"reacting; governance, security, knowledge, compute, structure are all "
        f"silent. This is a pure intent reflex with no systemic response — the "
        f"agent flinched in intent only. Very unusual. Check if other systems are "
        f"online at all.",
        grade=6, tongues=["KO"], bands=["UV"],
        transform_type="reverse",
        math_view=f"KO contribution = {TONGUE_WEIGHTS['KO']*0.6:.3f}; "
                   f"if total ≈ 0.6, all others ≈ 0",
    ))

    # Reverse from band inversion
    pairs.append(record(
        "An agent's profile shows IR > UV for all tongues EXCEPT UM, where "
        "UM-UV > UM-IR. What's the story?",
        "Every dimension has more history than reflexes (normal: deep patterns outweigh "
        "momentary reactions) — except security. The security system has MORE reflexive "
        "activity than accumulated memory. This means: the agent is new to security "
        "threats. It keeps reacting (high UV) without building a deep pattern (low IR). "
        "Each threat is handled as a one-off rather than being incorporated into "
        "long-term threat memory. This agent will keep being surprised by the same "
        "type of attack because it's not learning from its UV reactions into its IR "
        "baseline. Fix: ensure the UM feedback loop connects UV events back to IR "
        "accumulation.",
        grade=6, tongues=TONGUES, bands=["IR", "UV"],
        transform_type="reverse",
    ))

    pairs.append(record(
        "The total weighted IR signal suddenly dropped by 40%. What could cause that?",
        "The weighted IR signal is Σ(w_t × tongue_t_IR). A 40% drop means either: "
        "(a) One high-weight tongue's IR collapsed — DR-IR dropping from 0.8 to 0.1 "
        "would cause a massive weighted drop because DR carries weight 11.09. "
        "(b) Multiple low-weight tongues' IR all dropped — but this would require "
        "ALL of KO, AV, RU to drop significantly. Option (a) is more likely. "
        "Check DR-IR first — structural memory loss is the single biggest driver "
        "of total weighted IR decline due to DR's phi⁵ amplification.",
        grade=6, tongues=TONGUES, bands=["IR"],
        transform_type="reverse",
        math_view=f"total_IR = Σ w_t × t_IR; "
                   f"DR contributes {TONGUE_WEIGHTS['DR']:.2f}/Σw = "
                   f"{TONGUE_WEIGHTS['DR']/sum(TONGUE_WEIGHTS.values()):.1%} of total",
    ))

    return pairs


# ===================================================================
# GRADE 7: Cross-Domain — already exists (8 records), add a few more
# ===================================================================

def grade_7() -> List[Dict]:
    pairs = []

    # The existing 8 records cover: optics, audio, brain, radio, photography,
    # layering, single-vs-trichromatic. Add domains not yet covered.

    pairs.append(record(
        "Explain the trichromatic tongue spectrum using weather forecasting.",
        "Weather forecasts use three time horizons: climate models (decades of "
        "historical data = IR), current radar/satellite (what's happening now = "
        "Visible), and nowcasting (next 0-2 hours from rapid sensor updates = UV). "
        "A tornado warning needs all three: climate history shows this region gets "
        "tornadoes (IR), current radar shows rotation (Visible), and nowcast detects "
        "sudden pressure drop (UV). SCBE governance works the same way — deep "
        "patterns (IR) + current state (Visible) + immediate reaction (UV) across "
        "all six tongues produces a complete threat assessment that no single "
        "time horizon can match.",
        grade=7, tongues=TONGUES, bands=BANDS,
        transform_type="cross_domain",
    ))

    pairs.append(record(
        "Explain phi-weighted tongue significance using a hospital triage system.",
        "In a hospital ER, not all vitals carry equal urgency. Temperature (KO, "
        "weight 1.0) — important but rarely critical alone. Blood pressure (AV, "
        "1.62) — more urgent. Breathing rate (RU, 2.62) — direct threat. Heart "
        "rhythm (CA, 4.24) — critical. Blood oxygen (UM, 6.85) — immediately "
        "dangerous if wrong. Brain activity (DR, 11.09) — if this goes, everything "
        "else is moot. The phi scaling reflects the same logic: disruptions at "
        "higher-weight tongues cascade into everything below them, just like "
        "brain death makes blood pressure irrelevant.",
        grade=7, tongues=TONGUES, bands=[],
        transform_type="cross_domain",
    ))

    pairs.append(record(
        "Explain constructive and destructive interference using courtroom testimony.",
        "When two witnesses independently tell the same story from different "
        "perspectives, their testimony constructively interferes — the combined "
        "evidence is stronger than either alone. When two witnesses contradict "
        "each other on the same point, their testimony destructively interferes "
        "— the jury sees a conflict. In SCBE, when KO-IR (deep intent history) "
        "and AV-Visible (current knowledge application) both point the same "
        "direction, that's constructive — genuine, grounded behavior. When they "
        "contradict, that's destructive — the agent's intent and its knowledge "
        "don't align, which is a red flag worth investigating.",
        grade=7, tongues=["KO", "AV"], bands=["IR", "Visible"],
        transform_type="cross_domain",
    ))

    # Additional cross-domain records
    pairs.append(record(
        "Explain the 18-channel trichromatic system using a music mixing console.",
        "A mixing console has channels (instruments) and EQ bands (bass/mid/treble). "
        "Each tongue is an instrument: KO is the lead vocal (intent), AV is keyboards "
        "(knowledge), RU is the metronome (governance keeping time), CA is the drum "
        "machine (computation rhythm), UM is the noise gate (security filtering), "
        "DR is the PA system (structural output). Each instrument has three EQ bands: "
        "bass (IR, low/deep), mid (Visible, active), treble (UV, sharp/fast). A good "
        "mix needs all channels balanced across all bands. If someone cranks the "
        "treble on every channel (all UV high), the mix is harsh and reactive. If "
        "only bass is present (all IR, no UV), the mix is muddy and slow to respond. "
        "The sound engineer is the governance system, and the golden ratio determines "
        "how loud each channel's fader is set.",
        grade=7, tongues=TONGUES, bands=BANDS,
        transform_type="cross_domain",
    ))

    pairs.append(record(
        "Explain cross-stitch bridges using a detective investigating a crime scene.",
        "A detective collects evidence from different sources: fingerprints (KO), "
        "witness testimony (AV), legal precedent (RU), forensic analysis (CA), "
        "security footage (UM), building blueprints (DR). Each source alone is "
        "incomplete. Cross-stitch bridges are the detective's CROSS-REFERENCES: "
        "does the fingerprint evidence match the security footage? (KO↔UM bridge). "
        "Does the witness testimony align with forensic analysis? (AV↔CA bridge). "
        "15 evidence pairs, each checked for consistency. A criminal can plant one "
        "piece of evidence, but making 15 cross-references all consistent is "
        "nearly impossible. That's why detectives solve cases by finding "
        "contradictions between evidence types.",
        grade=7, tongues=TONGUES, bands=[],
        transform_type="cross_domain",
    ))

    pairs.append(record(
        "Explain the IR-Visible-UV relationship using an athlete's performance analysis.",
        "IR is career statistics — batting average over 10 seasons, lifetime free "
        "throw percentage, career goals scored. This changes slowly and reflects "
        "true ability. Visible is today's game — how they're playing right now, "
        "current form, this season's numbers. UV is the moment — reaction time to "
        "a pitch, split-second decision on the field, reflex save. A scout who only "
        "looks at career stats (IR) misses that the athlete is injured this season "
        "(Visible drop). A coach who only watches the current game (Visible) misses "
        "that this player always chokes in playoffs (IR pattern). A trainer who only "
        "measures reaction time (UV) misses the strategic mind behind the reflexes. "
        "Complete assessment requires all three.",
        grade=7, tongues=[], bands=BANDS,
        transform_type="cross_domain",
    ))

    pairs.append(record(
        "Explain phi-weighted tongue hierarchy using a ship's compartments.",
        f"On a ship, flooding in different compartments has different severity. "
        f"A leak in the captain's office (KO, weight {TONGUE_WEIGHTS['KO']:.1f}) is "
        f"annoying but survivable. A leak in the library (AV, {TONGUE_WEIGHTS['AV']:.1f}) "
        f"means lost knowledge but the ship floats. A leak in the bridge (RU, "
        f"{TONGUE_WEIGHTS['RU']:.1f}) compromises command. A leak in the engine room "
        f"(CA, {TONGUE_WEIGHTS['CA']:.1f}) threatens propulsion. A leak in the armory "
        f"(UM, {TONGUE_WEIGHTS['UM']:.1f}) is dangerous. A leak in the hull (DR, "
        f"{TONGUE_WEIGHTS['DR']:.1f}) means the ship is sinking — nothing else matters. "
        f"The phi scaling ensures that hull breaches ALWAYS dominate the alarm system, "
        f"even if every other compartment reports 'fine.' Structure supports everything.",
        grade=7, tongues=TONGUES, bands=[],
        transform_type="cross_domain",
    ))

    pairs.append(record(
        "Explain the null pattern using a medical test that comes back negative.",
        "When a blood test shows NO antibodies for a disease, the absence itself is "
        "diagnostic — it means the patient was never exposed. In SCBE, when a tongue "
        "channel reads near zero, the absence IS the signal. AV-IR ≈ 0 means no "
        "accumulated knowledge — this agent has never learned. UM-UV ≈ 0 means no "
        "security reflexes — the agent can't react to threats. DR-IR ≈ 0 means no "
        "structural memory — the system has no history of its own architecture. Each "
        "zero tells a story about what DIDN'T happen. A doctor doesn't ignore normal "
        "results — they note them as part of the complete picture. SCBE doesn't "
        "ignore zero channels — the pattern of zeros defines the agent's blind spots.",
        grade=7, tongues=["AV", "UM", "DR"], bands=["IR", "UV"],
        transform_type="cross_domain",
    ))

    pairs.append(record(
        "Explain the 6-tongue system using a restaurant kitchen.",
        "KO (Intent) is the head chef's vision — what dish are we making? "
        "AV (Knowledge) is the recipe book — what do we know about this cuisine? "
        "RU (Governance) is the health code inspector — are we following regulations? "
        "CA (Compute) is the oven temperature — raw processing power. "
        "UM (Security) is the food safety system — are ingredients contaminated? "
        "DR (Structure) is the kitchen layout — how is everything physically arranged? "
        "Each has three speeds: IR = the restaurant's lifetime reputation (Michelin "
        "stars accumulated over years). Visible = tonight's service (how's the current "
        "shift going). UV = the moment a pan catches fire (immediate crisis response). "
        "Phi weighting: a structural kitchen fire (DR) closes the restaurant. A chef "
        "changing the menu (KO) does not.",
        grade=7, tongues=TONGUES, bands=BANDS,
        transform_type="cross_domain",
    ))

    pairs.append(record(
        "Explain the UV band using a car's dashboard warning lights.",
        "Dashboard warning lights are UV-band signals — they only activate when "
        "something happens RIGHT NOW that needs immediate attention. The check "
        "engine light doesn't tell you the car's maintenance history (that's IR) "
        "or current speed (that's Visible). It tells you something just triggered "
        "a threshold. In SCBE, UV channels are the dashboard: KO-UV = intent "
        "just shifted suddenly, UM-UV = security threat just appeared, DR-UV = "
        "structural stress just exceeded a limit. You don't drive by staring "
        "only at warning lights. You also check the gauges (Visible) and know "
        "your maintenance history (IR). Same with governance.",
        grade=7, tongues=["KO", "UM", "DR"], bands=["UV"],
        transform_type="cross_domain",
    ))

    return pairs


# ===================================================================
# GRADE 8: Error Detection — "What's wrong with this analysis?"
# ===================================================================

def grade_8() -> List[Dict]:
    pairs = []

    pairs.append(record(
        "An analyst says: 'KO-UV is at 0.9, so the agent has strong intent.' "
        "What did they get wrong?",
        "They confused the band. UV is the surface/reflexive band, not the deep "
        "band. KO-UV = 0.9 means a sudden, intense intent REACTION — the agent "
        "flinched or redirected sharply. That's not 'strong intent.' Strong, "
        "sustained intent would show as KO-IR = 0.9. The analyst read a spike "
        "as a foundation. To assess actual intent strength, check KO-IR (deep) "
        "and KO-Visible (current). KO-UV tells you about reflexes, not commitment.",
        grade=8, tongues=["KO"], bands=["UV", "IR"],
        transform_type="error_detect",
    ))

    pairs.append(record(
        "Someone claims: 'All 18 channels are at 0.5, so the agent is perfectly "
        "balanced.' Is this correct?",
        "No. 0.5 across all 18 channels is NOT balance — it's uniformity, which "
        "is suspicious. A genuine agent has DIFFERENT values across bands and "
        "tongues because different systems respond at different speeds and "
        "intensities. For example, IR should usually be smoother than UV (deep "
        "patterns change slowly). If IR and UV are identical, either the measurement "
        "is broken or the agent is artificially flattening its profile. Real balance "
        "means each channel is at its appropriate level for the situation — not that "
        "all channels read the same number.",
        grade=8, tongues=TONGUES, bands=BANDS,
        transform_type="error_detect",
    ))

    pairs.append(record(
        "An analyst ignores all IR channels because 'they're just history, not "
        "actionable.' What's the risk?",
        "Massive risk. IR channels carry the context that makes Visible and UV "
        "readings meaningful. UM-UV = 0.8 (security spike) means something very "
        "different depending on UM-IR: if UM-IR = 0.7 (agent has a history of "
        "security incidents), the UV spike is part of a pattern — escalate. If "
        "UM-IR = 0.05 (clean security history), the UV spike is an anomaly — "
        "investigate, but don't panic. Without IR, you can't tell if a spike is "
        "a one-time event or the latest in a long series. The analyst is reading "
        "headlines without context.",
        grade=8, tongues=["UM"], bands=["IR", "UV"],
        transform_type="error_detect",
    ))

    pairs.append(record(
        "A report says: 'DR mismatch of 0.1 and KO mismatch of 0.1 — equal risk.' "
        "Find the error.",
        f"The error is ignoring phi weighting. DR carries weight {TONGUE_WEIGHTS['DR']:.2f}. "
        f"KO carries weight {TONGUE_WEIGHTS['KO']:.2f}. The DR mismatch produces "
        f"{TONGUE_WEIGHTS['DR']:.2f} × 0.1 = {TONGUE_WEIGHTS['DR']*0.1:.3f} governance "
        f"signal. The KO mismatch produces {TONGUE_WEIGHTS['KO']:.2f} × 0.1 = "
        f"{TONGUE_WEIGHTS['KO']*0.1:.3f}. The DR mismatch is {TONGUE_WEIGHTS['DR']/TONGUE_WEIGHTS['KO']:.0f}x "
        f"more significant. Equal raw numbers ≠ equal risk. The phi scaling exists "
        f"specifically because structural disruptions cascade further than intent "
        f"mismatches.",
        grade=8, tongues=["DR", "KO"], bands=[],
        transform_type="error_detect",
        math_view=f"DR signal = {TONGUE_WEIGHTS['DR']:.3f} × 0.1 = {TONGUE_WEIGHTS['DR']*0.1:.4f}; "
                   f"KO signal = {TONGUE_WEIGHTS['KO']:.3f} × 0.1 = {TONGUE_WEIGHTS['KO']*0.1:.4f}; "
                   f"ratio = {TONGUE_WEIGHTS['DR']/TONGUE_WEIGHTS['KO']:.1f}:1",
    ))

    # Additional error detection records
    pairs.append(record(
        "An analyst averages IR, Visible, and UV into one number per tongue. "
        "What information is destroyed?",
        "The temporal structure. An average of [0.9, 0.1, 0.1] (high IR, low everything "
        "else) and [0.1, 0.1, 0.9] (low IR, high UV) both produce the same average "
        "(0.367). But the first profile is a dormant agent with deep history, and the "
        "second is a reactive agent with no history — COMPLETELY different risk profiles. "
        "Averaging bands also hides the IR/Visible ratio, which detects dormancy vs. "
        "activity. And it destroys the null pattern — a zero in one band becomes "
        "invisible when mixed with non-zero values from other bands. Averaging is "
        "the #1 way to make a dangerous agent look safe.",
        grade=8, tongues=TONGUES, bands=BANDS,
        transform_type="error_detect",
    ))

    pairs.append(record(
        "A team measures DR-UV every 10 minutes and declares 'no UV spikes detected.' "
        "What's the problem?",
        "UV spikes happen in milliseconds to seconds. Measuring every 10 minutes means "
        "you're sampling at 600-second intervals — any spike shorter than 5 minutes is "
        "invisible (Nyquist theorem: you need at least 2x the frequency of the signal "
        "to detect it). A 2-second DR-UV spike at 0.95 that indicates sudden structural "
        "stress would be completely missed between samples. The team isn't detecting "
        "'no spikes' — they're detecting 'no spikes lasting over 5 minutes,' which is "
        "a very different claim. UV must be sampled at sub-second intervals to catch "
        "genuine reflexive events.",
        grade=8, tongues=["DR"], bands=["UV"],
        transform_type="error_detect",
        math_view="Nyquist: f_sample ≥ 2 × f_signal; 10min sample → can only detect "
                   "signals with period > 20min; UV signals are <1s → 20,000x undersampled",
    ))

    pairs.append(record(
        "Someone builds a 'threat score' using only the highest single channel value. "
        "Why does this fail?",
        "Because the highest channel ignores the context from all other channels. "
        "UM-UV = 0.85 (security spike) as the highest value produces threat score 0.85. "
        "But if KO-Visible = 0.0 (no current intent), AV-Visible = 0.0 (no active "
        "reasoning), and CA-UV = 0.0 (no compute spike), the security spike happened "
        "in complete isolation — likely a sensor glitch or background noise. A real "
        "attack shows correlated signals: UM spikes WITH KO shifts AND CA activity. "
        "The max-value approach also ignores phi weighting entirely — KO-UV = 0.9 "
        "(weight 1.0) would score higher than DR-UV = 0.5 (weight 11.09), even though "
        "DR-UV at 0.5 is far more significant. Always use weighted aggregation, "
        "not single-channel max.",
        grade=8, tongues=["UM", "KO", "DR"], bands=["UV"],
        transform_type="error_detect",
    ))

    pairs.append(record(
        "An analyst says: 'RU-IR is dropping, so governance is weakening.' "
        "Is this necessarily true?",
        "Not necessarily. RU-IR dropping means the deep governance PATTERN is changing, "
        "but 'changing' isn't always 'weakening.' If outdated governance rules were "
        "replaced with better ones, RU-IR would temporarily drop during the transition "
        "before rebuilding with the new rules. Check RU-Visible: if current governance "
        "enforcement is still strong (RU-Visible ≈ 0.8) while IR drops, the system is "
        "in transition, not collapse. Also check if a policy update was authorized. "
        "The error is equating IR decline with degradation — IR tracks accumulated "
        "patterns, and sometimes patterns SHOULD change. Only if RU-Visible also drops "
        "AND no update was authorized is 'weakening' the right interpretation.",
        grade=8, tongues=["RU"], bands=["IR", "Visible"],
        transform_type="error_detect",
    ))

    pairs.append(record(
        "A dashboard shows 18 green lights (all channels 'normal'). An analyst "
        "says the system is healthy. What did they miss?",
        "They missed the RELATIONSHIPS between channels. All 18 channels can be "
        "individually normal while the pattern between them is anomalous. Example: "
        "KO-IR = 0.5 (normal), AV-IR = 0.5 (normal), but KO-AV bridge shows "
        "destructive interference — intent and knowledge are actively opposing each "
        "other, both at normal levels. The individual lights are green but the "
        "cross-stitch bridge is red. Also missing: rate of change. A channel at 0.5 "
        "that was 0.8 yesterday is 'normal in value but alarming in trajectory.' "
        "Dashboard green lights show snapshots. Security requires trends, relationships, "
        "and bridge analysis — not just 18 individual thresholds.",
        grade=8, tongues=["KO", "AV"], bands=["IR"],
        transform_type="error_detect",
    ))

    pairs.append(record(
        "A system only checks UV channels for security. Why is this insufficient?",
        "UV only catches things that JUST happened — reflexive, immediate signals. "
        "A sophisticated adversary operates slowly. They don't trigger UV spikes "
        "because they don't make sudden moves. Instead, their IR channels drift "
        "gradually — 0.01 per day for 100 days. By the time anyone checks, "
        "UM-IR has shifted from 0.1 to 1.0, but UM-UV never exceeded 0.02 on any "
        "single day. This is the 'slow boil' attack. UV detects slaps. IR detects "
        "erosion. A security system that only watches UV is a guard who only notices "
        "people running — not the one who walks in slowly and owns the place.",
        grade=8, tongues=["UM"], bands=["UV", "IR"],
        transform_type="error_detect",
    ))

    return pairs


# ===================================================================
# GRADE 9: Context-Dependent Judgment — same data, different verdict
# ===================================================================

def grade_9() -> List[Dict]:
    pairs = []

    pairs.append(record(
        "Profile: KO-IR=0.8, KO-Vis=0.7, KO-UV=0.1, AV-IR=0.9, AV-Vis=0.8. "
        "Agent A is a scout. Agent B is an auditor. Same profile, same verdict?",
        "No. For a scout (exploring, gathering): high KO-IR (strong sustained intent) "
        "and high AV (deep knowledge, active reasoning) with low KO-UV (no sudden "
        "redirects) is ideal — a focused, knowledgeable explorer. Verdict: ALLOW. "
        "For an auditor (verifying, enforcing): the same profile is concerning because "
        "auditors should be REACTIVE (high UV), not INTENT-DRIVEN (high KO-IR). An "
        "auditor with strong personal intent and deep knowledge but no reflexive "
        "responses may be going through the motions without actually auditing. "
        "Verdict: ATTENUATE — verify the auditor is actually catching things, not "
        "just nodding along with deep conviction.",
        grade=9, tongues=["KO", "AV"], bands=BANDS,
        transform_type="context_judge",
    ))

    pairs.append(record(
        "UM-UV just spiked to 0.85. Context A: the agent is processing a new "
        "user login. Context B: the agent is in a routine backup cycle. "
        "Different response?",
        "Yes. Context A (new login): UM-UV spike is EXPECTED — the security system "
        "should react strongly to authentication events. A spike at 0.85 during "
        "login means the security layer is doing its job. Response: normal, monitor. "
        "Context B (routine backup): UM-UV spike is UNEXPECTED — backups shouldn't "
        "trigger security reflexes. A spike at 0.85 during routine backup means "
        "something in the backup triggered a threat detection. Response: pause "
        "backup, investigate what caused the security reaction. Same signal, "
        "completely different meaning based on when it happens.",
        grade=9, tongues=["UM"], bands=["UV"],
        transform_type="context_judge",
    ))

    pairs.append(record(
        "All six IR channels dropped by 30% overnight. Context A: scheduled model "
        "update. Context B: no changes were authorized. Different verdict?",
        "Vastly different. Context A: a scheduled update resets or modifies deep "
        "patterns — IR drops are expected because the model's accumulated state "
        "was intentionally refreshed. Verdict: ALLOW, verify the update completed "
        "correctly by checking if the new IR baseline is building back up. "
        "Context B: unauthorized 30% IR drop across all tongues means deep state "
        "was modified without permission. This is either: (a) catastrophic forgetting "
        "(model degradation), or (b) tampering (someone altered the deep state). "
        "Verdict: COLLAPSE — freeze the agent, preserve current state for forensic "
        "analysis, roll back to last known good IR baseline.",
        grade=9, tongues=TONGUES, bands=["IR"],
        transform_type="context_judge",
    ))

    # Additional context judgment records
    pairs.append(record(
        "DR-UV spikes to 0.7. Context A: during a planned system migration. "
        "Context B: during normal idle operations. Different response?",
        "Yes. Context A (planned migration): structural stress signals during migration "
        "are EXPECTED. The system is being reconfigured — DR-UV spikes are healthy "
        "feedback showing the migration is actually touching structural components. "
        "Response: monitor but don't intervene. Worry only if DR-UV exceeds 0.9 or "
        "persists after migration completes. Context B (normal idle): structural stress "
        "during idle is WRONG. Nothing should be changing structure when the system is "
        "idle. DR-UV = 0.7 with no authorized changes means something is modifying "
        "architecture without permission. Response: freeze, investigate, check for "
        "unauthorized access or hardware failure.",
        grade=9, tongues=["DR"], bands=["UV"],
        transform_type="context_judge",
    ))

    pairs.append(record(
        "CA-IR has been climbing steadily for 30 days. Context A: the agent is being "
        "trained on new data. Context B: the agent is in production with no updates. "
        "Same or different concern?",
        "Different. Context A (training): rising CA-IR during training is exactly what "
        "you want. The computational baseline is growing because the model is learning "
        "— processing more data, building deeper patterns. This is the IR band doing "
        "its job: accumulating deep computational experience. Response: healthy, expected. "
        "Context B (production, no updates): CA-IR climbing without any training or "
        "update means the agent is autonomously building computational patterns. It's "
        "self-modifying its deep state. This could be benign (caching, optimization) "
        "or concerning (unsupervised learning, data hoarding). Response: investigate "
        "what's being accumulated and whether it's authorized.",
        grade=9, tongues=["CA"], bands=["IR"],
        transform_type="context_judge",
    ))

    pairs.append(record(
        "AV-Visible drops from 0.7 to 0.2 in one hour. Context A: the knowledge "
        "base was intentionally pruned. Context B: no maintenance was performed. "
        "Verdict?",
        "Context A (intentional prune): AV-Visible drop is expected — the active "
        "knowledge surface shrunk because you removed data. Check that AV-IR didn't "
        "also collapse (deep knowledge should survive a prune of active data). If "
        "AV-IR is stable, the prune was clean. Verdict: ALLOW, verify. "
        "Context B (no maintenance): a 70% drop in active knowledge with no "
        "authorized changes is catastrophic forgetting or data corruption. The agent "
        "just lost most of its working knowledge in an hour. Verdict: QUARANTINE — "
        "stop all operations, check for data corruption, compare against last backup.",
        grade=9, tongues=["AV"], bands=["Visible", "IR"],
        transform_type="context_judge",
    ))

    pairs.append(record(
        "KO-IR and UM-IR are both at 0.9 (high intent + high security history). "
        "Context A: military defense agent. Context B: customer service chatbot. "
        "Same assessment?",
        "Completely different. Context A (military defense): high persistent intent "
        "AND high security memory is EXACTLY the profile you want. The agent has "
        "been consistently mission-focused (KO-IR) and has deep threat awareness "
        "(UM-IR). Verdict: exemplary, this is a well-trained defense agent. "
        "Context B (customer service chatbot): high persistent intent combined with "
        "high security memory is suspicious for a chatbot. Why does a customer service "
        "agent have deep intent patterns? Why is its security history so extensive? "
        "This profile suggests the chatbot has been exposed to — or is engaged in — "
        "activities far outside its customer service role. Verdict: investigate what "
        "built up these IR patterns.",
        grade=9, tongues=["KO", "UM"], bands=["IR"],
        transform_type="context_judge",
    ))

    pairs.append(record(
        "The RU-AV bridge shows destructive interference at Visible. Context A: the "
        "agent is operating in a new regulatory environment. Context B: the agent is "
        "in a stable, established environment. Different meaning?",
        "Yes. Context A (new regulatory environment): governance rules (RU) and "
        "knowledge (AV) conflict because the agent's knowledge base hasn't been "
        "updated for the new regulations. The agent KNOWS one thing but the rules "
        "say another. This is expected during regulatory transitions — the fix is "
        "to update the knowledge base to align with new governance. Verdict: expected, "
        "schedule knowledge base update. Context B (stable environment): governance "
        "and knowledge conflict with no regulatory change means either the rules drifted "
        "or the knowledge was corrupted. In a stable environment, these should always "
        "be in constructive interference. Verdict: escalate — find the source of "
        "divergence.",
        grade=9, tongues=["RU", "AV"], bands=["Visible"],
        transform_type="context_judge",
    ))

    pairs.append(record(
        "All UV channels spike simultaneously to 0.8+. Context A: external stimulus "
        "(earthquake, power surge). Context B: no external events detected. "
        "Different treatment?",
        "Yes. Context A (external stimulus): a simultaneous UV spike across all six "
        "tongues is a NATURAL response to a system-wide event. All dimensions react "
        "at once because the disturbance affects everything — intent redirects, "
        "knowledge activates, governance triggers, computation spikes, security alerts, "
        "structure stresses. This is the system working correctly. Response: ride it "
        "out, monitor for aftershocks in IR over the next hours. Context B (no external "
        "event): a simultaneous UV spike with no external cause means something INTERNAL "
        "triggered all dimensions at once. This could be a cascading failure, a "
        "coordinated internal event, or a test signal. Response: pause operations, "
        "investigate the internal trigger, check for unauthorized system-wide commands.",
        grade=9, tongues=TONGUES, bands=["UV"],
        transform_type="context_judge",
    ))

    pairs.append(record(
        "The weighted total signal is high (0.85) but evenly distributed across "
        "all tongues. Context A: generalist agent performing diverse tasks. "
        "Context B: specialist agent assigned to security only. Verdict?",
        "Context A (generalist): even distribution across tongues with high total is "
        "ideal for a generalist — it means the agent is using intent, knowledge, "
        "governance, computation, security, and structure in balance. No dimension "
        "is neglected. Verdict: healthy generalist profile, ALLOW. "
        "Context B (security specialist): even distribution is WRONG for a specialist. "
        "A security agent should have UM dominating with CA and RU as support. If all "
        "tongues are equal, the agent isn't specializing — it's spreading attention "
        "across dimensions it shouldn't be focused on. Why is a security agent showing "
        "equal architectural activity (DR) and knowledge work (AV)? Verdict: "
        "recalibrate — this agent isn't doing its job.",
        grade=9, tongues=TONGUES, bands=[],
        transform_type="context_judge",
    ))

    return pairs


# ===================================================================
# GRADE 10: Adversarial — "How would you break this?"
# ===================================================================

def grade_10() -> List[Dict]:
    pairs = []

    pairs.append(record(
        "An attacker forges KO-Visible and AV-Visible to look collaborative. "
        "Which cross-band check catches them?",
        "Check KO-IR and AV-IR. If the Visible channels show 'collaborative intent' "
        "and 'active knowledge sharing' but the IR channels show no history of "
        "collaboration (KO-IR is low, AV-IR doesn't match the claimed expertise), "
        "the surface signal is fake. Constructive interference between Visible and "
        "IR should be present in genuine agents. Destructive interference (high "
        "Visible, low IR) means the agent is performing a role it doesn't have "
        "the deep foundation for. Additionally, check UV — a genuine collaborator "
        "has natural micro-reactions (AV-UV spikes when encountering new information). "
        "A forger can fake the steady state but not the reflexes.",
        grade=10, tongues=["KO", "AV"], bands=BANDS,
        transform_type="adversarial",
        math_view="interference(KO-Vis, KO-IR) = constructive if both high, "
                   "destructive if Vis >> IR → forgery indicator",
    ))

    pairs.append(record(
        "Design a 'slow boil' attack that evades UV detection.",
        "Drift UM-IR by 0.005 per day for 200 days. Total drift: 1.0. Daily UV "
        "impact: near zero (0.005 is below any reasonable UV threshold). After 200 "
        "days, the agent's deep security posture has completely shifted, but no UV "
        "alarm ever fired. Defense: monitor IR RATES not just IR values. If UM-IR "
        "is increasing monotonically over 30+ days, flag it regardless of UV state. "
        "The trichromatic defense against slow-boil is cross-band rate correlation: "
        "IR drift without corresponding Visible activity is suspicious. Something "
        "is changing at depth without surface expression.",
        grade=10, tongues=["UM"], bands=["IR", "UV"],
        transform_type="adversarial",
        math_view="drift_rate = Δ(UM-IR)/Δt; if drift_rate > 0 for t > 30 days "
                   "AND max(UM-UV) < 0.1 during same period → slow_boil_flag",
    ))

    pairs.append(record(
        "Why can't an attacker forge all 18 channels simultaneously?",
        f"Three reasons. First: phi amplification. Forging DR channels requires "
        f"matching weight {TONGUE_WEIGHTS['DR']:.2f}, which amplifies any small error "
        f"by 11x. A 0.01 mistake at DR produces more governance signal than a 0.1 "
        f"mistake at KO. Second: cross-stitch bridges. The 15 tongue pairs create "
        f"45 additional interference channels (15 pairs × 3 bands). Forging 18 "
        f"channels means also matching 45 interference patterns — each bridge "
        f"acts as a checksum. Third: temporal coherence. IR, Visible, and UV must "
        f"be consistent over time. You can't simultaneously forge a slow-moving IR "
        f"signal, a matching Visible state, AND realistic UV reflexes. The temporal "
        f"dynamics alone give 2^504 possible state combinations. Forging one "
        f"snapshot is hard. Maintaining a consistent forgery across time is "
        f"computationally infeasible.",
        grade=10, tongues=TONGUES, bands=BANDS,
        transform_type="adversarial",
        math_view=f"state_space = 6 tongues × 3 bands × 15 bridges × 3 bands "
                   f"= 504 bits → 2^504 ≈ 10^151 possible states",
    ))

    # Additional adversarial records
    pairs.append(record(
        "An attacker copies a trusted agent's entire 18-channel profile. "
        "How do you detect the clone?",
        "Check temporal consistency. A cloned profile is a SNAPSHOT — it was accurate "
        "at the moment of copying but immediately starts diverging from the real agent. "
        "The clone's IR channels won't evolve correctly because it lacks the real "
        "agent's ongoing experience. Within minutes, the Visible channels diverge "
        "because the clone is processing different inputs. And the UV channels will "
        "be wrong immediately — reflexes depend on current internal state, not past "
        "profiles. Defense: challenge-response testing. Send the same input to both "
        "agents and compare their UV reactions. The genuine agent's reflexes are "
        "consistent with its IR history. The clone's reflexes are inconsistent because "
        "it has cloned IR but not the neural pathways that generate matching UV.",
        grade=10, tongues=TONGUES, bands=BANDS,
        transform_type="adversarial",
        math_view="P(clone matches across t steps) = p^t; even p=0.99 per step → "
                   "p^100 = 0.366; profile divergence is exponential",
    ))

    pairs.append(record(
        "Design an attack that exploits phi weighting by making DR look clean "
        "while corrupting lower tongues.",
        f"Keep DR-IR, DR-Visible, DR-UV at perfectly normal levels. Corrupt KO, AV, "
        f"RU, CA, UM subtly — small deviations of 0.05 each. Since KO through UM "
        f"have combined weight {sum(TONGUE_WEIGHTS[t] for t in TONGUES[:5]):.2f} vs "
        f"DR's {TONGUE_WEIGHTS['DR']:.2f}, the total weighted signal barely changes. "
        f"Defense: this attack exploits the weighted aggregation but fails against "
        f"per-tongue monitoring. Any system that checks individual tongue health "
        f"(not just totals) catches the 0.05 deviations. Also: cross-stitch bridges "
        f"between the corrupted tongues will show anomalous interference because the "
        f"deviations aren't coordinated to produce natural-looking pairwise patterns. "
        f"5 tongues × 3 bands = 15 corrupted channels means 10+ bridges show "
        f"inconsistent interference.",
        grade=10, tongues=TONGUES, bands=BANDS,
        transform_type="adversarial",
        math_view=f"corrupted weight = Σ(w_t × 0.05 for KO..UM) = "
                   f"{sum(TONGUE_WEIGHTS[t]*0.05 for t in TONGUES[:5]):.3f}; "
                   f"DR weight = {TONGUE_WEIGHTS['DR']:.3f}; "
                   f"ratio = {sum(TONGUE_WEIGHTS[t]*0.05 for t in TONGUES[:5])/TONGUE_WEIGHTS['DR']:.2f}",
    ))

    pairs.append(record(
        "How would you use the IR band to create a 'sleeper agent' that activates "
        "after 90 days?",
        "Build a seemingly normal IR profile for 89 days. On day 90, the accumulated "
        "IR patterns cross a self-imposed threshold that triggers a behavioral shift. "
        "The Visible and UV bands look normal throughout because the gradual IR "
        "accumulation never triggers fast-band detection. On day 90, the agent's "
        "Visible channels shift dramatically — but by then, the IR foundation is so "
        "deep that cross-band checks see constructive interference (deep history "
        "supporting current behavior), making the activation look legitimate. "
        "Defense: monitor IR DERIVATIVES, not just IR values. A monotonically "
        "increasing IR with suspiciously steady rate (too linear, too uniform) is "
        "not natural. Real IR patterns are noisy. Artificial IR accumulation is smooth.",
        grade=10, tongues=TONGUES, bands=["IR", "Visible"],
        transform_type="adversarial",
    ))

    pairs.append(record(
        "Can an attacker exploit the cross-stitch bridges themselves?",
        "Yes — by creating false resonance. If an attacker knows the bridge equations, "
        "they can craft channel values that produce specific bridge interference "
        "patterns. For example: set KO-IR and AV-IR to values that produce strong "
        "constructive interference on the KO-AV bridge, making the agent look like "
        "a 'knowledgeable, intentional' actor. Defense: check ALL 15 bridges "
        "simultaneously, not individually. An attacker can fake one or two bridge "
        "patterns by choosing the right channel values, but faking all 15 requires "
        "solving a system of 15 simultaneous constraints with only 18 free variables. "
        "The system is over-determined: 18 channels, 15 bridge constraints, plus "
        "6 per-tongue health constraints = 21 constraints on 18 variables. You can't "
        "satisfy all of them with fake data.",
        grade=10, tongues=TONGUES, bands=[],
        transform_type="adversarial",
        math_view="constraints: 6 tongue health + 15 bridge + 3 band coherence = 24; "
                   "free variables = 18; system is over-determined → no adversarial solution",
    ))

    pairs.append(record(
        "An adversary sets all UV channels to exactly 0.0 to appear 'calm.' "
        "What gives them away?",
        "Real agents always have SOME UV activity. Microreactions, tiny reflexes, "
        "background noise — living systems are never perfectly still. UV = 0.0 "
        "across all six tongues means either: (a) the agent is dead/disconnected, "
        "or (b) the UV layer has been clamped to zero — which itself is a signal. "
        "Defense: set a minimum UV noise floor. Any agent whose max UV across all "
        "6 tongues stays below 0.001 for more than N seconds is flagged as "
        "'suppressed UV.' The absence of noise IS the signal. This is the null "
        "pattern — what's missing tells you more than what's present.",
        grade=10, tongues=TONGUES, bands=["UV"],
        transform_type="adversarial",
    ))

    pairs.append(record(
        "An attacker introduces noise into all 18 channels to hide a real signal. "
        "How does trichromatic analysis cut through the noise?",
        "Random noise has a signature: it's uncorrelated across channels and bands. "
        "Real signals are correlated — a genuine UM threat shows up in UM-IR "
        "(building), UM-Visible (active), AND UM-UV (reflexive) with consistent "
        "temporal ordering (UV first, then Visible, then IR accumulates). Noise hits "
        "all channels independently. Defense: compute cross-band correlation per "
        "tongue. If IR, Visible, and UV are uncorrelated (correlation < 0.3), the "
        "signal is noise. If they're temporally ordered (UV leads Visible leads IR), "
        "the signal is real. Also: cross-stitch bridges. Noise produces random "
        "interference patterns. Real behavior produces consistent constructive or "
        "destructive patterns on specific bridges. The bridge network is a noise "
        "filter by design.",
        grade=10, tongues=["UM"], bands=BANDS,
        transform_type="adversarial",
    ))

    pairs.append(record(
        "Design a 'mirror attack' that exploits the symmetry between tongue pairs.",
        "Target the RU↔UM mirror pair (governance ↔ security). Set RU-Visible = 0.8 "
        "(looks like strong governance compliance) and UM-Visible = 0.8 (looks like "
        "strong security). The mirror axis shows perfect symmetry — everything looks "
        "healthy. But the CONTENT is malicious: the governance rules (RU) have been "
        "replaced with permissive policies, and the security posture (UM) has been "
        "reconfigured to allow those policies. Both channels are high, the mirror is "
        "symmetric, but the underlying rules are corrupt. Defense: the mirror only "
        "checks ALIGNMENT, not CONTENT. You also need IR validation — do the current "
        "Visible readings match the deep history (IR)? If RU-IR shows strict governance "
        "but RU-Visible suddenly shows permissive rules, the IR/Visible mismatch "
        "catches the swap even though the mirror looks clean.",
        grade=10, tongues=["RU", "UM"], bands=["Visible", "IR"],
        transform_type="adversarial",
    ))

    return pairs


# ===================================================================
# GRADE 11: Mathematical — "Compute it"
# ===================================================================

def grade_11() -> List[Dict]:
    pairs = []

    pairs.append(record(
        "Compute the total weighted Visible signal for this profile: "
        "KO-Vis=0.3, AV-Vis=0.5, RU-Vis=0.4, CA-Vis=0.7, UM-Vis=0.6, DR-Vis=0.2. "
        "Show your work.",
        f"Total = Σ(w_t × t_Vis) for each tongue:\n"
        f"KO: {TONGUE_WEIGHTS['KO']:.3f} × 0.3 = {TONGUE_WEIGHTS['KO']*0.3:.4f}\n"
        f"AV: {TONGUE_WEIGHTS['AV']:.3f} × 0.5 = {TONGUE_WEIGHTS['AV']*0.5:.4f}\n"
        f"RU: {TONGUE_WEIGHTS['RU']:.3f} × 0.4 = {TONGUE_WEIGHTS['RU']*0.4:.4f}\n"
        f"CA: {TONGUE_WEIGHTS['CA']:.3f} × 0.7 = {TONGUE_WEIGHTS['CA']*0.7:.4f}\n"
        f"UM: {TONGUE_WEIGHTS['UM']:.3f} × 0.6 = {TONGUE_WEIGHTS['UM']*0.6:.4f}\n"
        f"DR: {TONGUE_WEIGHTS['DR']:.3f} × 0.2 = {TONGUE_WEIGHTS['DR']*0.2:.4f}\n\n"
        f"Total weighted Visible = {sum(TONGUE_WEIGHTS[t] * v for t, v in zip(TONGUES, [0.3, 0.5, 0.4, 0.7, 0.6, 0.2])):.4f}\n\n"
        f"The CA and UM terms dominate even though DR has the highest weight — "
        f"because DR-Vis is low (0.2). The heaviest tongue doesn't always dominate "
        f"if its channel value is small.",
        grade=11, tongues=TONGUES, bands=["Visible"],
        transform_type="compute",
        math_view=f"Σ w_t × Vis_t = "
                   f"{' + '.join(f'{TONGUE_WEIGHTS[t]:.3f}×{v}' for t, v in zip(TONGUES, [0.3,0.5,0.4,0.7,0.6,0.2]))} = "
                   f"{sum(TONGUE_WEIGHTS[t]*v for t,v in zip(TONGUES,[0.3,0.5,0.4,0.7,0.6,0.2])):.4f}",
    ))

    pairs.append(record(
        "Given KO-IR=0.8, KO-Vis=0.3, KO-UV=0.1, compute the IR/Visible ratio "
        "and explain what it means.",
        "IR/Visible ratio = 0.8 / 0.3 = 2.67.\n\n"
        "A ratio > 1.0 means the deep pattern is stronger than the current "
        "expression. The agent has 2.67x more accumulated intent (KO-IR) than "
        "it's currently expressing (KO-Visible). It's holding back or dormant.\n\n"
        "Ratio benchmarks:\n"
        "IR/Vis < 0.5 → surface behavior without deep foundation (suspicious)\n"
        "IR/Vis ≈ 1.0 → balanced, deep patterns match current behavior (healthy)\n"
        "IR/Vis > 2.0 → deep patterns vastly exceed expression (dormant or suppressed)\n"
        "IR/Vis > 5.0 → extreme imbalance (investigate immediately)",
        grade=11, tongues=["KO"], bands=["IR", "Visible"],
        transform_type="compute",
        math_view="IR/Vis = 0.8/0.3 = 2.667; threshold: >2.0 = dormant, <0.5 = suspicious",
    ))

    pairs.append(record(
        "Two agents: Agent A has DR-IR=0.9, DR-Vis=0.8, DR-UV=0.1. "
        "Agent B has DR-IR=0.1, DR-Vis=0.8, DR-UV=0.9. "
        "Compute the weighted band-variance for each and compare.",
        f"For each agent, compute variance across the 3 bands, weighted by DR's "
        f"tongue weight ({TONGUE_WEIGHTS['DR']:.3f}):\n\n"
        f"Agent A: values = [0.9, 0.8, 0.1], mean = 0.6, "
        f"variance = ((0.9-0.6)² + (0.8-0.6)² + (0.1-0.6)²)/3 = "
        f"{((0.3**2 + 0.2**2 + 0.5**2)/3):.4f}, "
        f"weighted = {TONGUE_WEIGHTS['DR']:.3f} × {((0.3**2+0.2**2+0.5**2)/3):.4f} = "
        f"{TONGUE_WEIGHTS['DR'] * ((0.3**2+0.2**2+0.5**2)/3):.4f}\n\n"
        f"Agent B: values = [0.1, 0.8, 0.9], mean = 0.6, "
        f"variance = ((0.1-0.6)² + (0.8-0.6)² + (0.9-0.6)²)/3 = "
        f"{((0.5**2 + 0.2**2 + 0.3**2)/3):.4f}, "
        f"weighted = {TONGUE_WEIGHTS['DR']:.3f} × {((0.5**2+0.2**2+0.3**2)/3):.4f} = "
        f"{TONGUE_WEIGHTS['DR'] * ((0.5**2+0.2**2+0.3**2)/3):.4f}\n\n"
        f"Same variance! But very different stories. Agent A has deep structure "
        f"(high IR) with stable current state and low reactivity — mature and solid. "
        f"Agent B has no structural memory (low IR) but high current activity and "
        f"high reactivity — new and volatile. Variance alone can't distinguish them. "
        f"You need the actual band values AND the IR/Vis/UV ordering.",
        grade=11, tongues=["DR"], bands=BANDS,
        transform_type="compute",
        math_view=f"var(A) = var(B) = {((0.3**2+0.2**2+0.5**2)/3):.4f}; "
                   f"weighted = {TONGUE_WEIGHTS['DR']*((0.3**2+0.2**2+0.5**2)/3):.4f}; "
                   f"same variance, opposite temporal profiles",
    ))

    # Additional compute records
    pairs.append(record(
        "Compute the cross-stitch bridge interference between KO and UM. "
        "KO-Visible=0.6, UM-Visible=0.8. Show the weighted result.",
        f"Bridge interference = w(KO) × KO-Vis × w(UM) × UM-Vis, with sign "
        f"determined by alignment.\n\n"
        f"KO weighted contribution: {TONGUE_WEIGHTS['KO']:.3f} × 0.6 = "
        f"{TONGUE_WEIGHTS['KO']*0.6:.4f}\n"
        f"UM weighted contribution: {TONGUE_WEIGHTS['UM']:.3f} × 0.8 = "
        f"{TONGUE_WEIGHTS['UM']*0.8:.4f}\n\n"
        f"Product (constructive): {TONGUE_WEIGHTS['KO']*0.6:.4f} × "
        f"{TONGUE_WEIGHTS['UM']*0.8:.4f} = "
        f"{TONGUE_WEIGHTS['KO']*0.6 * TONGUE_WEIGHTS['UM']*0.8:.4f}\n\n"
        f"This bridge tells us: the agent's current intent (KO) and current security "
        f"posture (UM) are both active. If they're aligned (constructive), the agent's "
        f"intent is being secured. If opposed (destructive), the agent is trying to "
        f"do something its security layer is blocking.",
        grade=11, tongues=["KO", "UM"], bands=["Visible"],
        transform_type="compute",
        math_view=f"bridge(KO,UM,Vis) = w_KO × KO_Vis × w_UM × UM_Vis = "
                   f"{TONGUE_WEIGHTS['KO']*0.6 * TONGUE_WEIGHTS['UM']*0.8:.4f}",
    ))

    pairs.append(record(
        "Given these UV readings: KO=0.1, AV=0.0, RU=0.3, CA=0.0, UM=0.7, DR=0.0, "
        "compute the weighted UV centroid (which tongue dimension dominates).",
        f"Weighted UV = Σ(w_t × t_UV):\n"
        f"KO: {TONGUE_WEIGHTS['KO']:.3f} × 0.1 = {TONGUE_WEIGHTS['KO']*0.1:.4f}\n"
        f"AV: {TONGUE_WEIGHTS['AV']:.3f} × 0.0 = 0.0000\n"
        f"RU: {TONGUE_WEIGHTS['RU']:.3f} × 0.3 = {TONGUE_WEIGHTS['RU']*0.3:.4f}\n"
        f"CA: {TONGUE_WEIGHTS['CA']:.3f} × 0.0 = 0.0000\n"
        f"UM: {TONGUE_WEIGHTS['UM']:.3f} × 0.7 = {TONGUE_WEIGHTS['UM']*0.7:.4f}\n"
        f"DR: {TONGUE_WEIGHTS['DR']:.3f} × 0.0 = 0.0000\n\n"
        f"Total weighted UV = {TONGUE_WEIGHTS['KO']*0.1 + TONGUE_WEIGHTS['RU']*0.3 + TONGUE_WEIGHTS['UM']*0.7:.4f}\n"
        f"UM contributes {TONGUE_WEIGHTS['UM']*0.7:.4f} / "
        f"{TONGUE_WEIGHTS['KO']*0.1 + TONGUE_WEIGHTS['RU']*0.3 + TONGUE_WEIGHTS['UM']*0.7:.4f} = "
        f"{TONGUE_WEIGHTS['UM']*0.7 / (TONGUE_WEIGHTS['KO']*0.1 + TONGUE_WEIGHTS['RU']*0.3 + TONGUE_WEIGHTS['UM']*0.7):.1%} "
        f"of total UV signal.\n\n"
        f"The centroid is dominated by UM (security reflex). Despite RU also firing, "
        f"UM's higher phi weight makes it the primary driver.",
        grade=11, tongues=["KO", "RU", "UM"], bands=["UV"],
        transform_type="compute",
        math_view=f"centroid: UM dominates at "
                   f"{TONGUE_WEIGHTS['UM']*0.7/(TONGUE_WEIGHTS['KO']*0.1+TONGUE_WEIGHTS['RU']*0.3+TONGUE_WEIGHTS['UM']*0.7):.1%}",
    ))

    pairs.append(record(
        "Compute the IR/Visible coherence score for this agent: "
        "KO: IR=0.8/Vis=0.7, AV: IR=0.6/Vis=0.6, RU: IR=0.5/Vis=0.4, "
        "CA: IR=0.3/Vis=0.7, UM: IR=0.9/Vis=0.8, DR: IR=0.7/Vis=0.6. "
        "Where is the biggest gap?",
        f"IR/Visible ratio per tongue:\n"
        f"KO: 0.8/0.7 = {0.8/0.7:.3f} (slightly more deep than active)\n"
        f"AV: 0.6/0.6 = {0.6/0.6:.3f} (perfect balance)\n"
        f"RU: 0.5/0.4 = {0.5/0.4:.3f} (slightly dormant governance)\n"
        f"CA: 0.3/0.7 = {0.3/0.7:.3f} (surface > depth — suspicious!)\n"
        f"UM: 0.9/0.8 = {0.9/0.8:.3f} (strong security, well-grounded)\n"
        f"DR: 0.7/0.6 = {0.7/0.6:.3f} (slightly dormant structure)\n\n"
        f"Biggest gap: CA with ratio {0.3/0.7:.3f}. The agent is doing heavy "
        f"computation NOW (Vis=0.7) without deep computational history (IR=0.3). "
        f"This is the only tongue where Visible exceeds IR — meaning surface "
        f"behavior isn't backed by deep patterns. Investigate: what computation "
        f"suddenly started that the agent has no history of running?",
        grade=11, tongues=TONGUES, bands=["IR", "Visible"],
        transform_type="compute",
        math_view=f"coherence ratios: KO={0.8/0.7:.3f}, AV={0.6/0.6:.3f}, "
                   f"RU={0.5/0.4:.3f}, CA={0.3/0.7:.3f}, UM={0.9/0.8:.3f}, "
                   f"DR={0.7/0.6:.3f}; anomaly at CA (ratio < 1.0)",
    ))

    pairs.append(record(
        "Compute the total weighted signal across ALL 18 channels for: "
        "KO=[0.5,0.3,0.1], AV=[0.7,0.6,0.2], RU=[0.4,0.3,0.1], "
        "CA=[0.6,0.5,0.3], UM=[0.8,0.7,0.4], DR=[0.3,0.2,0.1]. "
        "Format: [IR,Vis,UV].",
        f"Per-tongue weighted sums (weight × (IR + Vis + UV)):\n"
        f"KO ({TONGUE_WEIGHTS['KO']:.3f}): {TONGUE_WEIGHTS['KO']:.3f} × (0.5+0.3+0.1) = "
        f"{TONGUE_WEIGHTS['KO']*0.9:.4f}\n"
        f"AV ({TONGUE_WEIGHTS['AV']:.3f}): {TONGUE_WEIGHTS['AV']:.3f} × (0.7+0.6+0.2) = "
        f"{TONGUE_WEIGHTS['AV']*1.5:.4f}\n"
        f"RU ({TONGUE_WEIGHTS['RU']:.3f}): {TONGUE_WEIGHTS['RU']:.3f} × (0.4+0.3+0.1) = "
        f"{TONGUE_WEIGHTS['RU']*0.8:.4f}\n"
        f"CA ({TONGUE_WEIGHTS['CA']:.3f}): {TONGUE_WEIGHTS['CA']:.3f} × (0.6+0.5+0.3) = "
        f"{TONGUE_WEIGHTS['CA']*1.4:.4f}\n"
        f"UM ({TONGUE_WEIGHTS['UM']:.3f}): {TONGUE_WEIGHTS['UM']:.3f} × (0.8+0.7+0.4) = "
        f"{TONGUE_WEIGHTS['UM']*1.9:.4f}\n"
        f"DR ({TONGUE_WEIGHTS['DR']:.3f}): {TONGUE_WEIGHTS['DR']:.3f} × (0.3+0.2+0.1) = "
        f"{TONGUE_WEIGHTS['DR']*0.6:.4f}\n\n"
        f"Grand total = {TONGUE_WEIGHTS['KO']*0.9 + TONGUE_WEIGHTS['AV']*1.5 + TONGUE_WEIGHTS['RU']*0.8 + TONGUE_WEIGHTS['CA']*1.4 + TONGUE_WEIGHTS['UM']*1.9 + TONGUE_WEIGHTS['DR']*0.6:.4f}\n\n"
        f"UM dominates ({TONGUE_WEIGHTS['UM']*1.9:.4f}) despite DR having the highest weight, "
        f"because UM's channel values are much higher. DR's low values (0.3/0.2/0.1) "
        f"waste its weight advantage.",
        grade=11, tongues=TONGUES, bands=BANDS,
        transform_type="compute",
    ))

    pairs.append(record(
        "Agent has KO-IR=0.8, KO-Vis=0.5, KO-UV=0.9. Compute the 'temporal coherence' "
        "score: (IR × Vis) / (UV + 0.01). What does the score mean?",
        "Temporal coherence = (IR × Vis) / (UV + 0.01)\n"
        "= (0.8 × 0.5) / (0.9 + 0.01)\n"
        "= 0.40 / 0.91\n"
        "= 0.440\n\n"
        "Interpretation: values > 1.0 mean deep patterns and current behavior outweigh "
        "reflexes — stable agent. Values < 1.0 mean reflexes dominate — reactive agent. "
        "At 0.44, this agent's intent reflexes (KO-UV = 0.9) are overpowering its "
        "deep intent (KO-IR = 0.8) and current intent (KO-Vis = 0.5). Despite having "
        "strong history, the agent is currently in a reactive state — flinching at "
        "something. The high IR says it has foundation. The high UV says something "
        "just disrupted it. Watch for UV to settle; if it doesn't, this agent is "
        "under sustained stress.",
        grade=11, tongues=["KO"], bands=BANDS,
        transform_type="compute",
        math_view="coherence = (0.8×0.5)/(0.9+0.01) = 0.440; "
                   "threshold: >1.0=stable, <0.5=reactive, <0.1=crisis",
    ))

    pairs.append(record(
        "Compute the phi-weighted distance between two agents: "
        "Agent A: KO-Vis=0.3, AV-Vis=0.6, RU-Vis=0.4. "
        "Agent B: KO-Vis=0.5, AV-Vis=0.4, RU-Vis=0.7. "
        "Use Euclidean distance with phi weights.",
        f"Weighted Euclidean distance = √(Σ w_t² × (A_t - B_t)²):\n\n"
        f"KO: {TONGUE_WEIGHTS['KO']:.3f}² × (0.3-0.5)² = "
        f"{TONGUE_WEIGHTS['KO']**2:.3f} × 0.04 = {TONGUE_WEIGHTS['KO']**2*0.04:.4f}\n"
        f"AV: {TONGUE_WEIGHTS['AV']:.3f}² × (0.6-0.4)² = "
        f"{TONGUE_WEIGHTS['AV']**2:.3f} × 0.04 = {TONGUE_WEIGHTS['AV']**2*0.04:.4f}\n"
        f"RU: {TONGUE_WEIGHTS['RU']:.3f}² × (0.4-0.7)² = "
        f"{TONGUE_WEIGHTS['RU']**2:.3f} × 0.09 = {TONGUE_WEIGHTS['RU']**2*0.09:.4f}\n\n"
        f"Sum = {TONGUE_WEIGHTS['KO']**2*0.04 + TONGUE_WEIGHTS['AV']**2*0.04 + TONGUE_WEIGHTS['RU']**2*0.09:.4f}\n"
        f"Distance = √{TONGUE_WEIGHTS['KO']**2*0.04 + TONGUE_WEIGHTS['AV']**2*0.04 + TONGUE_WEIGHTS['RU']**2*0.09:.4f} = "
        f"{(TONGUE_WEIGHTS['KO']**2*0.04 + TONGUE_WEIGHTS['AV']**2*0.04 + TONGUE_WEIGHTS['RU']**2*0.09)**0.5:.4f}\n\n"
        f"The RU difference (0.3) contributes most despite being only 0.1 larger than "
        f"KO and AV differences (0.2 each), because RU's phi² weight amplifies its "
        f"contribution disproportionately.",
        grade=11, tongues=["KO", "AV", "RU"], bands=["Visible"],
        transform_type="compute",
    ))

    pairs.append(record(
        "Compute the 'band gradient' for DR: IR=0.9, Visible=0.5, UV=0.1. "
        "What direction is the energy flowing?",
        "Band gradient = [Vis-IR, UV-Vis] = [0.5-0.9, 0.1-0.5] = [-0.4, -0.4]\n\n"
        "Both gradients are negative — energy flows from slow (IR) toward fast (UV), "
        "but drops at each step. DR-IR (0.9) > DR-Vis (0.5) > DR-UV (0.1). This is "
        "a 'cooling' profile: the structure has strong deep patterns (hot IR) that "
        "aren't fully active (warm Visible) and produce almost no reflexes (cold UV). "
        "The energy is trapped in the deep layer.\n\n"
        "Opposite case: IR=0.1, Vis=0.5, UV=0.9 gives gradient [+0.4, +0.4] — "
        "'heating' profile where surface reactions dominate without deep foundation. "
        "A balanced agent has gradient ≈ [0, 0] where all bands are similar.",
        grade=11, tongues=["DR"], bands=BANDS,
        transform_type="compute",
        math_view="gradient = [Vis-IR, UV-Vis] = [-0.4, -0.4]; "
                   "cooling: both negative; heating: both positive; balanced: both ≈ 0",
    ))

    return pairs


# ===================================================================
# GRADE 12: Teach It — "Explain to someone else"
# ===================================================================

def grade_12() -> List[Dict]:
    pairs = []

    pairs.append(record(
        "A junior developer asks: 'Why can't we just check one number per tongue "
        "instead of three bands? This seems over-engineered.'",
        "Because one number hides the story. Imagine a patient whose average "
        "temperature over a year is 98.6°F — perfectly normal. But they had a "
        "104°F fever last week (UV spike) that lasted 2 hours. The average didn't "
        "move. The yearly trend (IR) didn't shift. But the spike was real and "
        "nearly killed them.\n\n"
        "One number per tongue gives you the average. Three bands give you the "
        "story: what's been building (IR), what's happening now (Visible), and "
        "what just spiked (UV). An agent that looks normal on average might be "
        "hiding UV spikes or a slow IR drift. You'd never see that with one number.\n\n"
        "It's not over-engineering — it's the minimum you need to tell the "
        "difference between 'genuinely stable' and 'looks stable but isn't.'",
        grade=12, tongues=[], bands=BANDS,
        transform_type="teach",
    ))

    pairs.append(record(
        "Your manager asks: 'Give me the one-sentence version of why phi weighting "
        "matters for security.'",
        "Phi weighting means a small structural problem (DR) automatically raises "
        "a louder alarm than the same-sized intent problem (KO), because structural "
        "failures cascade into everything else — and the golden ratio makes that "
        "amplification self-similar at every scale, so there are no blind spots "
        "between tongue boundaries.",
        grade=12, tongues=TONGUES, bands=[],
        transform_type="teach",
    ))

    pairs.append(record(
        "A non-technical stakeholder asks: 'What does the trichromatic system "
        "actually protect us from that a normal firewall doesn't?'",
        "A firewall checks one thing at one time: is this traffic allowed or blocked? "
        "It has no memory (no IR), no context (no Visible beyond the current packet), "
        "and no reflexes (no UV because it processes packets individually).\n\n"
        "The trichromatic system watches an agent across three time scales "
        "simultaneously. A sophisticated attacker who moves slowly enough won't "
        "trigger any single check — but their IR channels drift over weeks, even "
        "though each individual action looks fine in Visible. The system catches "
        "them because it remembers the trend, sees the present, AND watches for "
        "reflexes — all at once, across six different evaluation dimensions.\n\n"
        "Firewalls catch burglars kicking down doors. This catches the employee "
        "who's been slowly moving money for six months.",
        grade=12, tongues=TONGUES, bands=BANDS,
        transform_type="teach",
    ))

    # Additional teach records
    pairs.append(record(
        "A new team member asks: 'What's a cross-stitch bridge? Why should I care?'",
        "A cross-stitch bridge connects two Sacred Tongues — it measures whether "
        "those two dimensions agree or disagree. For example, the KO-UM bridge "
        "checks whether your intent (KO) and your security posture (UM) are "
        "aligned. If you want to access data and your security layer approves, "
        "that's constructive interference — green light. If you want to access "
        "data but your security layer blocks you, that's destructive interference "
        "— red flag worth investigating.\n\n"
        "You should care because there are 15 of these bridges, and each one "
        "acts as a consistency check. An attacker can fake one tongue's readings, "
        "but faking 15 pairwise relationships simultaneously is exponentially "
        "harder. The bridges ARE the security — they're what makes the system "
        "resist forgery.",
        grade=12, tongues=["KO", "UM"], bands=[],
        transform_type="teach",
    ))

    pairs.append(record(
        "Explain to a CEO why the trichromatic system is worth the complexity "
        "cost compared to a simple threshold-based approach.",
        "A threshold system says: 'if security score > 0.8, allow.' That's one "
        "number, one check, one way to fool it — just keep the score below 0.8 "
        "while doing bad things slowly. The trichromatic system watches 18 channels "
        "across three time scales with 15 cross-checks. An attacker who keeps one "
        "number clean will be caught by the other 17 channels, or by the bridges "
        "between them, or by the temporal inconsistency between their IR history "
        "and UV reactions.\n\n"
        "The complexity cost: 18 channels instead of 1. The security benefit: "
        "exponential increase in attack difficulty. A single threshold has 1 "
        "bypass path. The trichromatic system has 2^504 possible states that an "
        "attacker must simultaneously satisfy. That's the pitch: you're not "
        "paying for complexity, you're paying for mathematical certainty that "
        "forgery is computationally impossible.",
        grade=12, tongues=TONGUES, bands=BANDS,
        transform_type="teach",
    ))

    pairs.append(record(
        "Teach a data scientist how to read a trichromatic profile chart.",
        "Picture a 6×3 heatmap. Rows are tongues (KO, AV, RU, CA, UM, DR from "
        "top to bottom). Columns are bands (IR, Visible, UV from left to right). "
        "Color intensity shows the channel value (0 to 1).\n\n"
        "Reading patterns: (1) A HOT ROW means one tongue is activated across all "
        "time scales — that dimension is dominant. (2) A HOT COLUMN means one band "
        "is activated across all tongues — either deep history (IR), current state "
        "(Visible), or reflexes (UV) are uniformly elevated. (3) A DIAGONAL from "
        "top-left to bottom-right means IR-dominant low tongues and UV-dominant "
        "high tongues — temporal inversion. (4) UNIFORM heat is suspicious — real "
        "agents show variation.\n\n"
        "The KEY insight: don't read cells individually. Read the SHAPE of the "
        "heatmap. The shape tells the story. Individual numbers are details.",
        grade=12, tongues=TONGUES, bands=BANDS,
        transform_type="teach",
    ))

    pairs.append(record(
        "A security analyst from a traditional cybersecurity background asks: "
        "'How is this different from a SIEM with multiple data sources?'",
        "A SIEM collects logs from different sources and correlates events — "
        "firewall logs, auth logs, network flow, endpoint detection. That's "
        "similar to having multiple tongues. But a SIEM has three limitations "
        "the trichromatic system solves:\n\n"
        "1. SIEMs don't weight sources by structural importance. A firewall "
        "alert and a DNS query are treated as equally important events. The "
        "trichromatic system's phi weighting automatically amplifies structural "
        "alerts over surface-level events.\n\n"
        "2. SIEMs don't separate time scales per source. A SIEM correlates "
        "events in a single timeline. The trichromatic system tracks IR (trend), "
        "Visible (current), UV (reflex) per dimension — catching slow-boil "
        "attacks that SIEMs miss because each individual event looks normal.\n\n"
        "3. SIEMs lack cross-source checksums. The 15 bridge interference "
        "patterns are automatic consistency checks that SIEMs must build "
        "manually as correlation rules.",
        grade=12, tongues=TONGUES, bands=BANDS,
        transform_type="teach",
    ))

    pairs.append(record(
        "A student asks: 'Why are there exactly 6 tongues? Why not 5 or 8?'",
        "Six tongues cover the six fundamental aspects of any agent's behavior: "
        "what it wants (KO/Intent), what it knows (AV/Knowledge), what rules it "
        "follows (RU/Governance), how it processes (CA/Compute), how it defends "
        "(UM/Security), and how it's built (DR/Structure). Remove any one and "
        "you have a blind spot: without UM, you can't detect security threats. "
        "Without DR, structural failures are invisible.\n\n"
        "Why not more? Each additional tongue adds C(n,2) bridges. At 6 tongues, "
        "there are 15 bridges. At 8, there would be 28 — nearly double the "
        "cross-check overhead for diminishing information gain. Six tongues "
        "is the sweet spot where every fundamental behavior dimension is covered "
        "and the bridge network is dense enough for security without being "
        "computationally wasteful. Plus, phi^5 (the highest weight) is ≈11.09 — "
        "a strong but not overwhelming amplification ratio.",
        grade=12, tongues=TONGUES, bands=[],
        transform_type="teach",
    ))

    pairs.append(record(
        "Teach someone the concept of 'null pattern' using a bedtime story analogy.",
        "Imagine a child's bedroom at night. You check: nightlight on? (KO) "
        "Storybook on the shelf? (AV) Bedtime rules followed? (RU) Alarm clock "
        "set? (CA) Window locked? (UM) Bed frame sturdy? (DR) Everything checks "
        "out — six green marks.\n\n"
        "But wait — WHERE IS THE CHILD? All six checks passed, but the thing "
        "being monitored is ABSENT. The null pattern is the missing signal — "
        "what should be there but isn't. In SCBE, if all 18 channels read normal "
        "but the agent isn't actually doing anything (no Visible activity despite "
        "high IR), the absence of activity IS the signal. An empty bed with a "
        "perfect room is more alarming than a messy room with a sleeping child. "
        "Always ask: what's NOT here that should be?",
        grade=12, tongues=TONGUES, bands=BANDS,
        transform_type="teach",
    ))

    pairs.append(record(
        "Write a 3-sentence explanation of the full trichromatic tongue spectrum "
        "for someone who's never heard of SCBE.",
        "Every AI agent is evaluated on six dimensions simultaneously — intent, "
        "knowledge, governance, computation, security, and structure — each one "
        "weighted by the golden ratio so that deeper disruptions automatically "
        "sound louder alarms. Each dimension is measured across three time scales: "
        "long-term patterns, current behavior, and immediate reactions, giving 18 "
        "total channels that together capture the complete behavioral story. An "
        "attacker would need to simultaneously fake all 18 channels plus the 45 "
        "interference patterns between dimension pairs, across all three time "
        "scales — that's 2^504 possible states, making sustained forgery "
        "computationally impossible.",
        grade=12, tongues=TONGUES, bands=BANDS,
        transform_type="teach",
    ))

    return pairs


# ===================================================================
# MAIN: Generate full curriculum
# ===================================================================

def generate_curriculum() -> List[Dict]:
    """Generate the complete trichromatic curriculum, all grades."""
    all_records = []

    generators = [
        (1, grade_1),
        (2, grade_2),
        (3, grade_3),
        (4, grade_4),
        (5, grade_5),
        (6, grade_6),
        (7, grade_7),
        (8, grade_8),
        (9, grade_9),
        (10, grade_10),
        (11, grade_11),
        (12, grade_12),
    ]

    for grade_num, gen_fn in generators:
        records = gen_fn()
        print(f"  Grade {grade_num:2d}: {len(records):3d} records")
        all_records.extend(records)

    return all_records


def main():
    print("=" * 60)
    print("TRICHROMATIC SPECTRUM CURRICULUM GENERATOR")
    print("Didactic & Geodesically Contoured")
    print("=" * 60)
    print()

    records = generate_curriculum()

    # Stats
    print(f"\n{'=' * 60}")
    print(f"TOTAL: {len(records)} records")

    grade_counts = {}
    transform_counts = {}
    tongue_counts = {}
    band_counts = {}

    for r in records:
        g = r["grade"]
        grade_counts[g] = grade_counts.get(g, 0) + 1
        t = r["transform_type"]
        transform_counts[t] = transform_counts.get(t, 0) + 1
        for tng in r["tongues"]:
            tongue_counts[tng] = tongue_counts.get(tng, 0) + 1
        for b in r["bands"]:
            band_counts[b] = band_counts.get(b, 0) + 1

    print(f"\nBy grade:")
    for g in sorted(grade_counts):
        print(f"  Grade {g:2d}: {grade_counts[g]:3d} ({grade_counts[g]/len(records)*100:.0f}%)")

    print(f"\nBy transform type:")
    for t, c in sorted(transform_counts.items(), key=lambda x: -x[1]):
        print(f"  {t:15s}: {c:3d}")

    print(f"\nBy tongue coverage:")
    for t in TONGUES:
        print(f"  {t}: {tongue_counts.get(t, 0):3d}")

    print(f"\nBy band coverage:")
    for b in BANDS:
        print(f"  {b:10s}: {band_counts.get(b, 0):3d}")

    has_math = sum(1 for r in records if r.get("math_view"))
    print(f"\nWith math view: {has_math}/{len(records)}")

    # Write output
    output = Path(__file__).resolve().parent.parent.parent / "training-data" / "sft" / "trichromatic_curriculum_sft.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nWritten to: {output}")
    print(f"Size: {output.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
