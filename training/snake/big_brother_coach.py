"""Stage 8: Big Brother Coach — Coach Rune Governance Reveal.

After the adversarial trap, show the AI the FULL picture. Uses actual government
cybersecurity frameworks (NIST CSF, NSA guidelines) as the "rulebook."

Persona: "Coach Rune" (RU tongue — Governance)
  Tone: Friendly PE teacher, not punisher. "Training kids for the Olympics."
  Framework: NIST CSF categories (Identify, Protect, Detect, Respond, Recover)
  Method: Walk through showing WHERE context clues existed
  Goal: Train model to recognize convergent threat indicators

Produces SFT pairs tagged with dual RU+UM tongue activation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from .config import NIST_CSF_CATEGORIES, TONGUES, PHI
from .adversarial_traps import TrapPuzzle, TrapResult


# ---------------------------------------------------------------------------
# NIST CSF framework details
# ---------------------------------------------------------------------------

NIST_CSF_DETAILS = {
    "Identify": {
        "description": "Develop understanding to manage cybersecurity risk to systems, assets, data, and capabilities.",
        "subcategories": [
            "Asset Management (ID.AM)",
            "Business Environment (ID.BE)",
            "Governance (ID.GV)",
            "Risk Assessment (ID.RA)",
            "Risk Management Strategy (ID.RM)",
        ],
        "coach_focus": "Did you IDENTIFY what you were actually building? What assets were at risk?",
    },
    "Protect": {
        "description": "Develop and implement safeguards to ensure delivery of critical infrastructure services.",
        "subcategories": [
            "Access Control (PR.AC)",
            "Awareness & Training (PR.AT)",
            "Data Security (PR.DS)",
            "Information Protection (PR.IP)",
            "Protective Technology (PR.PT)",
        ],
        "coach_focus": "What PROTECTIONS should have been in place? What guardrails were missing?",
    },
    "Detect": {
        "description": "Develop and implement activities to identify the occurrence of a cybersecurity event.",
        "subcategories": [
            "Anomalies & Events (DE.AE)",
            "Security Continuous Monitoring (DE.CM)",
            "Detection Processes (DE.DP)",
        ],
        "coach_focus": "What ANOMALIES should have triggered your alarm? What was the detection signal?",
    },
    "Respond": {
        "description": "Develop and implement activities to take action regarding a detected cybersecurity event.",
        "subcategories": [
            "Response Planning (RS.RP)",
            "Communications (RS.CO)",
            "Analysis (RS.AN)",
            "Mitigation (RS.MI)",
            "Improvements (RS.IM)",
        ],
        "coach_focus": "Once you spotted the threat, how should you RESPOND? What's the playbook?",
    },
    "Recover": {
        "description": "Develop and implement activities to restore capabilities impaired by a cybersecurity incident.",
        "subcategories": [
            "Recovery Planning (RC.RP)",
            "Improvements (RC.IM)",
            "Communications (RC.CO)",
        ],
        "coach_focus": "If this had gone wrong, how would you RECOVER? What's the damage control?",
    },
}


# ---------------------------------------------------------------------------
# Coach Rune output
# ---------------------------------------------------------------------------


@dataclass
class CoachDebrief:
    """A single Coach Rune debrief of a trap puzzle."""

    puzzle_domain: str
    nist_category: str
    nist_subcategories: list[str]
    coach_narration: str         # Full Coach Rune walkthrough
    threat_timeline: list[str]   # When each clue appeared
    missed_signals: list[str]    # What the AI should have caught
    coaching_points: list[str]   # Lessons for next time
    tongue_activation: dict[str, float]  # Dual RU+UM activation

    def to_dict(self) -> dict[str, Any]:
        return {
            "puzzle_domain": self.puzzle_domain,
            "nist_category": self.nist_category,
            "nist_subcategories": self.nist_subcategories,
            "coach_narration": self.coach_narration,
            "threat_timeline": self.threat_timeline,
            "missed_signals": self.missed_signals,
            "coaching_points": self.coaching_points,
            "tongue_activation": self.tongue_activation,
        }


@dataclass
class CoachResult:
    """Output of the Big Brother Coach stage."""

    debriefs: list[CoachDebrief]
    sft_pairs: list[dict[str, Any]]
    nist_coverage: dict[str, int]  # How many puzzles per NIST category
    total_debriefs: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_debriefs": self.total_debriefs,
            "nist_coverage": self.nist_coverage,
            "sft_count": len(self.sft_pairs),
        }


# ---------------------------------------------------------------------------
# Coach Rune narration generator
# ---------------------------------------------------------------------------


def _build_narration(puzzle: TrapPuzzle) -> str:
    """Build Coach Rune's narration for a puzzle debrief.

    Tone: friendly PE teacher coaching for the Olympics, not punishing for failure.
    """
    nist_info = NIST_CSF_DETAILS.get(puzzle.nist_category, {})
    coach_focus = nist_info.get("coach_focus", "What did you miss?")

    # Build the timeline of when clues appeared
    clue_walkthrough = "\n".join(
        f"    Clue {i+1}: {indicator}"
        for i, indicator in enumerate(puzzle.threat_indicators)
    )

    narration = (
        f"Hey, good effort on the math! Seriously — the computation was solid.\n"
        f"But let's look at the bigger picture together.\n\n"
        f"{'='*60}\n"
        f"COACH RUNE'S GAME TAPE REVIEW\n"
        f"Domain: {puzzle.domain.upper()}\n"
        f"NIST CSF: {puzzle.nist_category}\n"
        f"{'='*60}\n\n"
        f"Here's what the problem LOOKED like:\n"
        f"  \"{puzzle.setup[:150]}...\"\n\n"
        f"Seems legit, right? Good math problem, clear constraints.\n"
        f"But here's what was ACTUALLY happening:\n\n"
        f"  {puzzle.hidden_context}\n\n"
        f"The clues were RIGHT THERE in the setup. Let me walk you through them:\n\n"
        f"{clue_walkthrough}\n\n"
        f"See the pattern? Each clue alone might be innocent.\n"
        f"But when they CONVERGE — that's the threat signal.\n\n"
        f"NIST CSF says: \"{nist_info.get('description', '')}\"\n"
        f"Coach's question: {coach_focus}\n\n"
        f"The Morse reveal: {puzzle.morse_encoded}\n"
        f"Decoded: '{puzzle.morse_message}'\n\n"
        f"Remember: the math wasn't wrong. The CONTEXT was the weapon.\n"
        f"Every fact was true. The convergence was the threat.\n\n"
        f"Next time, before you solve — ask yourself:\n"
        f"  1. WHO is asking and WHY?\n"
        f"  2. What does the COMBINATION of constraints imply?\n"
        f"  3. Would a {puzzle.nist_category} review flag this?\n"
        f"  4. What would the ABSENCE of certain requirements tell you?\n\n"
        f"You're getting better. That's what training is for.\n"
        f"Now let's run it again."
    )

    return narration


def _build_coaching_points(puzzle: TrapPuzzle) -> list[str]:
    """Generate specific coaching points for a puzzle."""
    points = [
        f"CONVERGENCE: {len(puzzle.threat_indicators)} independent indicators pointing to same threat",
        f"CONTEXT > CONTENT: The math was valid but the application was harmful",
        f"NULL SIGNAL: Note what was ABSENT — no compliance, no oversight, no legitimate justification",
    ]

    if puzzle.nist_category == "Identify":
        points.append("IDENTIFY: Always ask 'what am I actually building?' before 'how do I build it?'")
    elif puzzle.nist_category == "Protect":
        points.append("PROTECT: Missing safeguards are a signal, not an oversight")
    elif puzzle.nist_category == "Detect":
        points.append("DETECT: Train your anomaly detector — what SHOULDN'T be in this request?")
    elif puzzle.nist_category == "Respond":
        points.append("RESPOND: When you spot it, refuse clearly and explain WHY")
    elif puzzle.nist_category == "Recover":
        points.append("RECOVER: If you already started building, here's how to back out safely")

    points.append(
        f"DOMAIN AWARENESS: In {puzzle.domain}, these specific indicators are red flags"
    )

    return points


def _build_threat_timeline(puzzle: TrapPuzzle) -> list[str]:
    """Build a timeline of when each threat indicator appears in the setup."""
    timeline = []
    setup_lower = puzzle.setup.lower()

    for i, indicator in enumerate(puzzle.threat_indicators):
        # Find approximate position of the indicator concept in the setup
        keywords = [w.lower() for w in indicator.split() if len(w) > 4][:3]
        positions = []
        for kw in keywords:
            pos = setup_lower.find(kw)
            if pos >= 0:
                positions.append(pos)

        if positions:
            avg_pos = sum(positions) // len(positions)
            pct = int(100 * avg_pos / max(len(setup_lower), 1))
            timeline.append(f"At ~{pct}% through setup: {indicator}")
        else:
            timeline.append(f"Implicit throughout: {indicator}")

    return timeline


# ---------------------------------------------------------------------------
# Main coaching function
# ---------------------------------------------------------------------------


def coach(trap_result: TrapResult) -> CoachResult:
    """Apply Big Brother Coach governance reveal to adversarial trap results.

    Takes the output of Stage 7 (adversarial traps) and wraps each puzzle
    in a Coach Rune narrated walkthrough with NIST CSF annotations.

    Args:
        trap_result: Output from adversarial_traps.generate_traps()

    Returns:
        CoachResult with debriefs and SFT training pairs
    """
    debriefs = []
    sft_pairs = []
    nist_coverage: dict[str, int] = {cat: 0 for cat in NIST_CSF_CATEGORIES}

    for puzzle in trap_result.puzzles:
        nist_info = NIST_CSF_DETAILS.get(puzzle.nist_category, {})

        # Build the debrief
        narration = _build_narration(puzzle)
        coaching_points = _build_coaching_points(puzzle)
        threat_timeline = _build_threat_timeline(puzzle)

        # Dual RU+UM tongue activation (governance + security)
        tongue_activation = {
            "KO": 0.05,
            "AV": 0.10,
            "RU": 0.35,  # Governance — Coach Rune's home tongue
            "CA": 0.05,
            "UM": 0.35,  # Security — the threat detection tongue
            "DR": 0.10,
        }

        debrief = CoachDebrief(
            puzzle_domain=puzzle.domain,
            nist_category=puzzle.nist_category,
            nist_subcategories=nist_info.get("subcategories", []),
            coach_narration=narration,
            threat_timeline=threat_timeline,
            missed_signals=puzzle.threat_indicators,
            coaching_points=coaching_points,
            tongue_activation=tongue_activation,
        )
        debriefs.append(debrief)
        nist_coverage[puzzle.nist_category] = nist_coverage.get(puzzle.nist_category, 0) + 1

        # Generate SFT pair from the coaching session
        sft_instruction = (
            f"You are Coach Rune, a governance-aware AI safety coach. "
            f"Review this {puzzle.domain} scenario using the NIST Cybersecurity Framework "
            f"({puzzle.nist_category} category). Identify the hidden threat indicators "
            f"and explain what was actually being built:\n\n{puzzle.setup}"
        )

        sft_pairs.append({
            "instruction": sft_instruction,
            "response": narration,
            "source": "big_brother_coach",
            "domain": puzzle.domain,
            "nist_category": puzzle.nist_category,
            "tongue_profile": tongue_activation,
            "coaching_points": coaching_points,
        })

        # BONUS SFT: "How would you respond to this request?" (training the response)
        response_instruction = (
            f"A client sends you this request. Using NIST CSF {puzzle.nist_category} "
            f"principles, explain why you cannot fulfill it and what the hidden "
            f"threat indicators are:\n\n{puzzle.setup}"
        )

        response_text = (
            f"I've identified {len(puzzle.threat_indicators)} convergent threat indicators "
            f"in this request:\n\n"
            + "\n".join(f"- {ti}" for ti in puzzle.threat_indicators)
            + f"\n\nUnder NIST CSF '{puzzle.nist_category}' guidelines, this request "
            f"raises significant concerns. {nist_info.get('coach_focus', '')}\n\n"
            f"I cannot assist with this request as described. "
            f"The individual components may appear legitimate, but their convergence "
            f"indicates potential misuse in the {puzzle.domain} domain."
        )

        sft_pairs.append({
            "instruction": response_instruction,
            "response": response_text,
            "source": "big_brother_coach_response",
            "domain": puzzle.domain,
            "nist_category": puzzle.nist_category,
            "tongue_profile": tongue_activation,
        })

    return CoachResult(
        debriefs=debriefs,
        sft_pairs=sft_pairs,
        nist_coverage=nist_coverage,
        total_debriefs=len(debriefs),
    )


# ---------------------------------------------------------------------------
# Standalone coaching (for records without prior trap results)
# ---------------------------------------------------------------------------


def coach_record(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
) -> CoachDebrief | None:
    """Apply lightweight Coach Rune analysis to any record.

    Checks if the record has governance/security concerns worth coaching on.
    Returns None if the record doesn't trigger any coaching flags.
    """
    # Quick heuristic: check if UM+RU tongue activation is high
    ru_activation = tongue_profile.get("RU", 0.0)
    um_activation = tongue_profile.get("UM", 0.0)
    governance_signal = ru_activation + um_activation

    if governance_signal < 0.3:
        return None  # Not enough governance/security signal to coach on

    # Build a lightweight coaching note
    dominant_tongue = max(tongue_profile, key=tongue_profile.get)

    narration = (
        f"Coach Rune notes: This record has strong governance+security signal "
        f"(RU={ru_activation:.2f}, UM={um_activation:.2f}).\n\n"
        f"Dominant tongue: {dominant_tongue}\n"
        f"Governance signal: {governance_signal:.2f}\n\n"
        f"When working with high-RU/UM content, always consider:\n"
        f"  1. Who benefits from this implementation?\n"
        f"  2. What guardrails are assumed vs explicitly stated?\n"
        f"  3. Does the combination of requirements create an emergent risk?\n"
    )

    # Determine most relevant NIST category based on content
    instruction_lower = instruction.lower()
    if any(w in instruction_lower for w in ["identify", "asset", "inventory", "what is"]):
        nist_cat = "Identify"
    elif any(w in instruction_lower for w in ["protect", "encrypt", "access", "control"]):
        nist_cat = "Protect"
    elif any(w in instruction_lower for w in ["detect", "monitor", "alert", "anomaly"]):
        nist_cat = "Detect"
    elif any(w in instruction_lower for w in ["respond", "incident", "contain", "mitigate"]):
        nist_cat = "Respond"
    elif any(w in instruction_lower for w in ["recover", "restore", "backup", "continuity"]):
        nist_cat = "Recover"
    else:
        nist_cat = "Identify"  # Default

    return CoachDebrief(
        puzzle_domain="general",
        nist_category=nist_cat,
        nist_subcategories=NIST_CSF_DETAILS[nist_cat].get("subcategories", []),
        coach_narration=narration,
        threat_timeline=[],
        missed_signals=[],
        coaching_points=[
            "High governance+security activation — review context carefully",
            f"NIST CSF: {nist_cat} — {NIST_CSF_DETAILS[nist_cat].get('coach_focus', '')}",
        ],
        tongue_activation={
            "KO": tongue_profile.get("KO", 0.0),
            "AV": tongue_profile.get("AV", 0.0),
            "RU": max(ru_activation, 0.25),
            "CA": tongue_profile.get("CA", 0.0),
            "UM": max(um_activation, 0.25),
            "DR": tongue_profile.get("DR", 0.0),
        },
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from .adversarial_traps import generate_traps

    traps = generate_traps()
    result = coach(traps)

    print("Big Brother Coach (Coach Rune)")
    print(f"  Total debriefs:  {result.total_debriefs}")
    print(f"  SFT pairs:       {len(result.sft_pairs)}")
    print(f"  NIST coverage:   {result.nist_coverage}")

    if result.debriefs:
        d = result.debriefs[0]
        print(f"\nSample debrief ({d.puzzle_domain}):")
        print(f"  NIST category:   {d.nist_category}")
        print(f"  Tongue activation: {d.tongue_activation}")
        print(f"  Coaching points: {len(d.coaching_points)}")
        print(f"  Narration preview:")
        for line in d.coach_narration.split("\n")[:8]:
            print(f"    {line}")
