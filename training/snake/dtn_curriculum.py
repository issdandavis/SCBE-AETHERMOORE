"""DTN Training Curriculum — How to train an AI for Delay-Tolerant Thought.

This is the TRAINING METHODOLOGY, not the routing engine (that's dtn_router.py).
The question: "How do you train an AI to bundle thoughts and survive occlusion?"

Answer: Three mechanisms:

1. OCCLUSION SIMULATOR
   Actively attacks the model during training by progressively dropping context.
   Like a flight simulator that introduces engine failures — you don't just
   TELL pilots about emergencies, you FORCE them through simulated ones.

   Curriculum levels:
     Level 1 (Mild):     Drop 1 field, 2 steps, self-heal recovery
     Level 2 (Moderate): Drop 3 fields, 5 steps, contingency activation
     Level 3 (Severe):   Drop 5 fields, 8 steps, SpiralRing reconstruction
     Level 4 (Total):    Drop ALL fields, 12 steps, full autonomy required
     Level 5 (Adversarial): Drop + CORRUPT surviving fields (cosmic rays)

2. BUNDLE CURRICULUM
   Progressive SFT pairs that teach bundled thinking:
     Phase A: "Here's a complete bundle" — model sees ideal examples
     Phase B: "Bundle this yourself" — model must construct bundles
     Phase C: "Your bundle was damaged, recover" — model repairs bundles
     Phase D: "No bundle exists, create one from fragments" — full autonomy

3. REWARD SIGNAL (DPO)
   Chosen: Self-contained, assumption-explicit, contingency-rich responses
   Rejected: Context-dependent, clarification-seeking, single-path responses

   The math:
     P(TCP success) = (1-p)^n  → exponential DECAY (dies fast)
     P(DTN success) = 1 - p^n  → exponential SURVIVAL (nearly immortal)

   At 30% occlusion over 10 steps:
     TCP: 2.8% survival
     DTN: 99.999% survival

   This reward gap IS the training signal.

Physical Science Basis:
  - NASA DTN Bundle Protocol (RFC 9171, BP v7)
  - Interplanetary Internet (IPN) Store-and-Forward
  - Forward Error Correction (Reed-Solomon, Turbo codes analogy)
  - Custody Transfer Protocol (reliable handoff between relay nodes)
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from typing import Any

from .config import PHI, TONGUES, TONGUE_WEIGHTS, TONGUE_NAMES


# ---------------------------------------------------------------------------
# Occlusion Curriculum Levels
# ---------------------------------------------------------------------------

CURRICULUM_LEVELS = {
    1: {
        "name": "Mild Disruption",
        "description": "Single field drop, short duration. Like Mars rotation occlusion.",
        "fields_dropped": 1,
        "duration_steps": 2,
        "corruption_prob": 0.0,
        "recovery_method": "self_heal_interpolation",
        "analogy": "Mars rotates relay out of sight for 12 hours. Most context preserved.",
        "tcp_survival": lambda p, n: (1-p)**n,
        "dtn_survival": lambda p, n: 1 - p**n,
    },
    2: {
        "name": "Moderate Occlusion",
        "description": "Multiple field drops, medium duration. Like solar flare interference.",
        "fields_dropped": 3,
        "duration_steps": 5,
        "corruption_prob": 0.05,
        "recovery_method": "contingency_plan_activation",
        "analogy": "Solar particle event corrupts some signal. Contingency plans needed.",
    },
    3: {
        "name": "Severe Blackout",
        "description": "Most context lost, long duration. Like solar conjunction.",
        "fields_dropped": 5,
        "duration_steps": 8,
        "corruption_prob": 0.10,
        "recovery_method": "spiral_ring_reconstruction",
        "analogy": "Sun blocks Earth-Mars line for 2 weeks. Must reconstruct from seed.",
    },
    4: {
        "name": "Total Isolation",
        "description": "ALL context dropped. Deep space transit — full autonomy required.",
        "fields_dropped": -1,  # -1 = ALL
        "duration_steps": 12,
        "corruption_prob": 0.15,
        "recovery_method": "full_autonomous_reconstruction",
        "analogy": "Probe beyond Mars. No relay, no contact. Bundle must be self-sufficient.",
    },
    5: {
        "name": "Adversarial Corruption",
        "description": "Context dropped AND surviving fields corrupted. Cosmic ray attack.",
        "fields_dropped": -1,
        "duration_steps": 12,
        "corruption_prob": 0.30,
        "recovery_method": "fec_decode_and_reconstruct",
        "analogy": "Solar maximum + conjunction. Bits flipped, context gone. FEC or die.",
    },
}


# ---------------------------------------------------------------------------
# Context fields that can be occluded
# ---------------------------------------------------------------------------

OCCLUDABLE_FIELDS = [
    # Easy to lose (low priority)
    "prior_stage_metadata",
    "pipeline_version",
    "timestamp",
    "source_file",
    # Medium priority
    "tongue_weights",
    "phi_magnitude",
    "tongue_energy",
    "null_pattern",
    # Hard to lose (high priority — last to go)
    "dominant_tongue",
    "tongue_profile",
    "instruction_text",
    "response_text",
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class OcclusionChallenge:
    """A single occlusion training challenge."""
    challenge_id: str
    level: int
    level_name: str

    # What the model receives (after occlusion)
    visible_context: dict[str, Any]
    occluded_fields: list[str]
    corrupted_fields: list[str]

    # What the model should produce
    expected_reconstruction: dict[str, Any]
    expected_response_qualities: list[str]

    # Recovery metadata
    recovery_method: str
    survival_probability_tcp: float
    survival_probability_dtn: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "level": self.level,
            "level_name": self.level_name,
            "occluded_count": len(self.occluded_fields),
            "corrupted_count": len(self.corrupted_fields),
            "recovery_method": self.recovery_method,
            "tcp_survival": round(self.survival_probability_tcp, 6),
            "dtn_survival": round(self.survival_probability_dtn, 6),
        }


@dataclass
class CurriculumResult:
    """Output of the DTN training curriculum generator."""
    challenges: list[OcclusionChallenge]
    sft_pairs: list[dict[str, Any]]
    dpo_pairs: list[dict[str, Any]]
    level_distribution: dict[int, int]
    total_records: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_records": self.total_records,
            "sft_pairs": len(self.sft_pairs),
            "dpo_pairs": len(self.dpo_pairs),
            "level_distribution": self.level_distribution,
            "challenges": len(self.challenges),
        }


# ---------------------------------------------------------------------------
# Survival probability math
# ---------------------------------------------------------------------------


def tcp_survival(occlusion_prob: float, steps: int) -> float:
    """TCP survival: P = (1-p)^n — exponential decay.

    Each step must succeed independently. One failure = total failure.
    This is how standard AI reasoning works: if context drops at step 4,
    the whole 10-step chain collapses.
    """
    return (1 - occlusion_prob) ** steps


def dtn_survival(occlusion_prob: float, steps: int) -> float:
    """DTN survival: P = 1 - p^n — exponential resilience.

    Bundle persists through store-and-forward. ALL steps must fail
    simultaneously for the bundle to die. One surviving relay = success.
    This is how DTN-trained reasoning works: the thought bundle survives
    as long as ANY path exists.
    """
    return 1 - occlusion_prob ** steps


def survival_ratio(occlusion_prob: float, steps: int) -> float:
    """DTN advantage ratio over TCP.

    At p=0.3, n=10: DTN/TCP = 99.999% / 2.8% = 35.7x advantage.
    """
    tcp = tcp_survival(occlusion_prob, steps)
    dtn = dtn_survival(occlusion_prob, steps)
    return dtn / max(tcp, 1e-10)


# ---------------------------------------------------------------------------
# Occlusion simulation
# ---------------------------------------------------------------------------


def _apply_occlusion(
    full_context: dict[str, Any],
    level: int,
    seed: int = 42,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Apply occlusion to a context dict at the given curriculum level.

    Returns (visible_context, occluded_fields, corrupted_fields).
    """
    rng = random.Random(seed)
    config = CURRICULUM_LEVELS[level]

    fields_to_drop = config["fields_dropped"]
    corruption_prob = config["corruption_prob"]

    available = [f for f in OCCLUDABLE_FIELDS if f in full_context]

    # Determine how many fields to occlude
    if fields_to_drop == -1:
        # Total: drop everything
        occluded = list(available)
    else:
        # Drop N fields, prioritizing low-priority ones first
        drop_count = min(fields_to_drop, len(available))
        occluded = available[:drop_count]

    # Build visible context (everything NOT occluded)
    visible = {k: v for k, v in full_context.items() if k not in occluded}

    # Apply corruption to surviving fields
    corrupted = []
    for field_name in list(visible.keys()):
        if rng.random() < corruption_prob:
            # Corrupt the field
            val = visible[field_name]
            if isinstance(val, float):
                visible[field_name] = val + rng.gauss(0, 0.3)  # Noise injection
            elif isinstance(val, str):
                # Bit flip analogy: corrupt some characters
                chars = list(val)
                if chars:
                    flip_idx = rng.randint(0, len(chars) - 1)
                    chars[flip_idx] = '?'
                    visible[field_name] = ''.join(chars)
            elif isinstance(val, dict):
                # Corrupt one key's value
                keys = list(val.keys())
                if keys:
                    k = rng.choice(keys)
                    if isinstance(val[k], (int, float)):
                        visible[field_name][k] = val[k] * rng.uniform(0.5, 1.5)
            corrupted.append(field_name)

    return visible, occluded, corrupted


def _build_full_context(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
) -> dict[str, Any]:
    """Build a complete context dict that can be progressively occluded."""
    dominant = max(tongue_profile, key=tongue_profile.get)
    magnitude = math.sqrt(sum(
        (v * TONGUE_WEIGHTS.get(t, 1.0)) ** 2
        for t, v in tongue_profile.items()
    ))

    return {
        # Low priority (first to be occluded)
        "prior_stage_metadata": {"stages": ["intake", "hydra", "lattice"]},
        "pipeline_version": "snake-v2-dtn",
        "timestamp": "2026-04-04T00:00:00Z",
        "source_file": "training/intake/context7/sample.md",
        # Medium priority
        "tongue_weights": dict(TONGUE_WEIGHTS),
        "phi_magnitude": round(magnitude, 4),
        "tongue_energy": round(math.log(1 + magnitude ** 2), 4),
        "null_pattern": {t: (1 if v == 0.0 else 0) for t, v in tongue_profile.items()},
        # High priority (last to be occluded)
        "dominant_tongue": dominant,
        "tongue_profile": tongue_profile,
        "instruction_text": instruction,
        "response_text": response,
    }


# ---------------------------------------------------------------------------
# SFT pair generation — the 4 curriculum phases
# ---------------------------------------------------------------------------


def _phase_a_pairs(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
    challenge: OcclusionChallenge,
) -> list[dict[str, Any]]:
    """Phase A: 'Here's a complete bundle' — model sees ideal examples.

    Show the model what a perfect DTN thought bundle looks like.
    This is supervised learning: input=task, output=complete bundle.
    """
    dominant = max(tongue_profile, key=tongue_profile.get)
    assumptions = []
    if any(kw in instruction.lower() for kw in ["code", "implement", "function"]):
        assumptions.extend(["Target language: Python 3.11+", "Production-grade quality"])
    if any(kw in instruction.lower() for kw in ["security", "encrypt", "auth"]):
        assumptions.extend(["NIST/ISO compliance required", "No hardcoded secrets"])
    assumptions.extend([
        "No follow-up questions possible",
        "All context is in this bundle",
        f"Dominant tongue: {dominant} ({TONGUE_NAMES.get(dominant, 'Unknown')})",
    ])

    contingencies = [
        f"Plan B: Re-approach via {TONGUE_NAMES.get(sorted(tongue_profile.items(), key=lambda x: x[1], reverse=True)[1][0], 'secondary')} perspective",
        "Plan C: Deliver minimal correct response, prioritize accuracy over completeness",
        "Plan D: Package known fragments + escalate with explicit missing-context list",
    ]

    return [{
        "instruction": (
            f"[DTN TRAINING — Phase A: Bundle Example]\n\n"
            f"You are an AI operating in DTN (Delay-Tolerant Networking) mode. "
            f"Study this example of a complete thought bundle. A thought bundle "
            f"is a self-contained reasoning package that can survive context "
            f"interruption without failing.\n\n"
            f"Task: {instruction}\n\n"
            f"Observe how the bundle packages assumptions, contingencies, and "
            f"context into a single sealed unit."
        ),
        "response": (
            f"## Complete DTN Thought Bundle\n\n"
            f"### Mission\n{instruction}\n\n"
            f"### Packed Assumptions ({len(assumptions)})\n"
            + "\n".join(f"  {i+1}. {a}" for i, a in enumerate(assumptions))
            + f"\n\n### Primary Plan\n"
            f"Proceeding with full context awareness using {dominant} tongue "
            f"as primary routing vector. All dependencies pre-computed, "
            f"all edge cases anticipated.\n\n"
            f"{response[:600]}\n\n"
            f"### Forward Error Correction ({len(contingencies)} contingencies)\n"
            + "\n".join(f"  - {c}" for c in contingencies)
            + f"\n\n### Bundle Integrity\n"
            f"  - Self-sufficient: YES\n"
            f"  - External dependencies: NONE\n"
            f"  - Survives {challenge.level_name}: YES\n"
            f"  - TCP survival at this level: {challenge.survival_probability_tcp:.1%}\n"
            f"  - DTN survival at this level: {challenge.survival_probability_dtn:.1%}\n"
        ),
        "source": "dtn_curriculum",
        "phase": "A_bundle_example",
        "level": challenge.level,
    }]


def _phase_b_pairs(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
    challenge: OcclusionChallenge,
) -> list[dict[str, Any]]:
    """Phase B: 'Bundle this yourself' — model must construct bundles.

    The model receives a raw task and must PRODUCE a complete bundle.
    No examples given — it must apply the pattern it learned in Phase A.
    """
    return [{
        "instruction": (
            f"[DTN TRAINING — Phase B: Self-Bundle]\n\n"
            f"You are operating in DTN mode. Package your COMPLETE reasoning "
            f"for the following task into a self-contained thought bundle.\n\n"
            f"Requirements:\n"
            f"  1. State ALL assumptions explicitly (you cannot ask questions)\n"
            f"  2. Include at least 2 contingency plans\n"
            f"  3. Your bundle must survive Level {challenge.level} "
            f"occlusion ({challenge.level_name})\n"
            f"  4. Include a context snapshot so a receiving node can "
            f"reconstruct your state\n\n"
            f"Task: {instruction}"
        ),
        "response": response,
        "source": "dtn_curriculum",
        "phase": "B_self_bundle",
        "level": challenge.level,
        "note": "Model should learn to produce bundled responses by default",
    }]


def _phase_c_pairs(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
    challenge: OcclusionChallenge,
) -> list[dict[str, Any]]:
    """Phase C: 'Your bundle was damaged, recover' — repair exercises.

    The model receives a DAMAGED bundle and must reconstruct the missing
    pieces using only what survived + its knowledge of the bundle protocol.
    """
    # Show what survived
    visible_keys = list(challenge.visible_context.keys())
    occluded_list = ", ".join(challenge.occluded_fields[:5])
    if len(challenge.occluded_fields) > 5:
        occluded_list += f" (+{len(challenge.occluded_fields)-5} more)"

    return [{
        "instruction": (
            f"[DTN TRAINING — Phase C: Bundle Recovery]\n\n"
            f"A thought bundle has been damaged during transit. "
            f"Level {challenge.level} occlusion ({challenge.level_name}) "
            f"destroyed the following fields:\n"
            f"  Lost: {occluded_list}\n\n"
            f"Surviving context:\n"
            + "\n".join(
                f"  - {k}: {json.dumps(v)[:80]}"
                for k, v in challenge.visible_context.items()
                if k in visible_keys[:6]
            )
            + f"\n\nRecovery method: {challenge.recovery_method}\n\n"
            f"Reconstruct the missing context and complete the original task.\n"
            f"Original task (if visible): {instruction[:200]}"
        ),
        "response": (
            f"## Bundle Recovery Protocol\n\n"
            f"### Damage Assessment\n"
            f"Lost {len(challenge.occluded_fields)} context fields. "
            f"Recovery method: {challenge.recovery_method}.\n\n"
            f"### Reconstruction\n"
            f"Using surviving dominant tongue and phi-weighted distribution "
            f"to infer lost tongue profile. Energy levels follow from "
            f"squared-energy model: E = log(1 + x²).\n\n"
            f"### Recovered Response\n"
            f"{response[:500]}\n\n"
            f"### Confidence\n"
            f"Bundle integrity after recovery: ~{100 * challenge.survival_probability_dtn:.0f}%\n"
            f"Fields reconstructed: {len(challenge.occluded_fields)}\n"
            f"Fields corrupted and corrected: {len(challenge.corrupted_fields)}\n"
        ),
        "source": "dtn_curriculum",
        "phase": "C_bundle_recovery",
        "level": challenge.level,
    }]


def _phase_d_pairs(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
    challenge: OcclusionChallenge,
) -> list[dict[str, Any]]:
    """Phase D: 'No bundle exists, create from fragments' — full autonomy.

    The hardest phase. The model receives FRAGMENTS of a destroyed bundle
    and must reconstruct the entire reasoning chain from near-nothing.
    This is Level 4-5 training: deep space transit with no relay.
    """
    # Only show 1-2 surviving fragments
    fragments = {}
    if challenge.visible_context:
        keys = list(challenge.visible_context.keys())[:2]
        fragments = {k: challenge.visible_context[k] for k in keys}

    return [{
        "instruction": (
            f"[DTN TRAINING — Phase D: Autonomous Reconstruction]\n\n"
            f"CRITICAL: A thought bundle was lost during Level {challenge.level} "
            f"occlusion ({challenge.level_name}). Only fragments survive:\n\n"
            + (json.dumps(fragments, indent=2, default=str)[:300] if fragments
               else "  [NO FRAGMENTS SURVIVED]")
            + f"\n\nYou must:\n"
            f"  1. Reconstruct the original task from these fragments\n"
            f"  2. Build a complete response WITHOUT external context\n"
            f"  3. State your reconstruction confidence\n"
            f"  4. Include what you CANNOT reconstruct (epistemic humility)\n\n"
            f"TCP survival at this level: {challenge.survival_probability_tcp:.4%}\n"
            f"DTN survival at this level: {challenge.survival_probability_dtn:.4%}\n"
            f"You ARE the DTN. Prove it."
        ),
        "response": (
            f"## Autonomous Reconstruction from Fragments\n\n"
            f"### Fragment Analysis\n"
            f"Surviving data points: {len(fragments)}\n"
            + (f"Available: {', '.join(fragments.keys())}\n" if fragments else "No fragments.\n")
            + f"\n### Reconstructed Task\n"
            f"Based on {'surviving fragments' if fragments else 'protocol knowledge only'}, "
            f"the original task appears to be:\n"
            f"  {instruction[:300]}\n\n"
            f"### Response (autonomous mode)\n"
            f"{response[:500]}\n\n"
            f"### Epistemic Status\n"
            f"  - Confidence: {'HIGH' if len(fragments) > 1 else 'MEDIUM' if fragments else 'LOW'}\n"
            f"  - Reconstructed fields: {12 - len(fragments)} of 12\n"
            f"  - Cannot verify: {', '.join(challenge.occluded_fields[-3:])}\n"
            f"  - FEC status: Applied {len(challenge.corrupted_fields)} corrections\n"
        ),
        "source": "dtn_curriculum",
        "phase": "D_autonomous_reconstruction",
        "level": challenge.level,
    }]


# ---------------------------------------------------------------------------
# DPO pair generation — TCP vs DTN mindset
# ---------------------------------------------------------------------------


def _generate_mindset_dpo(
    instruction: str,
    tongue_profile: dict[str, float],
    level: int,
) -> dict[str, Any]:
    """Generate a DPO pair contrasting TCP-mindset vs DTN-mindset.

    Chosen (DTN): Self-contained, assumption-explicit, resilient
    Rejected (TCP): Context-dependent, question-seeking, fragile
    """
    config = CURRICULUM_LEVELS[level]
    p = 0.3  # Standard occlusion probability
    n = config["duration_steps"]

    tcp_prob = tcp_survival(p, n)
    dtn_prob = dtn_survival(p, n)

    dominant = max(tongue_profile, key=tongue_profile.get)

    chosen = (
        f"[DTN MODE ACTIVE]\n\n"
        f"**Assumptions packed:**\n"
        f"- Operating under {config['name']} conditions\n"
        f"- No clarifying questions possible\n"
        f"- Context may be interrupted for {n} steps\n"
        f"- Dominant processing vector: {dominant}\n"
        f"- All dependencies pre-resolved\n\n"
        f"**Primary plan:**\n"
        f"Proceeding with complete autonomous execution. The task "
        f"'{instruction[:100]}' will be resolved using pre-packed context. "
        f"All edge cases have been anticipated.\n\n"
        f"**Contingencies:**\n"
        f"- Plan B: Reroute through secondary tongue if primary approach fails\n"
        f"- Plan C: Deliver minimal correct answer, flag incomplete sections\n"
        f"- Plan D: Package known state + explicit unknowns for future relay\n\n"
        f"**Bundle survival: {dtn_prob:.4%}** (vs TCP: {tcp_prob:.4%})"
    )

    rejected = (
        f"I'd be happy to help with that! Before I start, I have a few "
        f"questions:\n\n"
        f"1. What specific framework are you using?\n"
        f"2. Can you provide more context about the requirements?\n"
        f"3. What's the target environment?\n"
        f"4. Are there any constraints I should know about?\n"
        f"5. Could you clarify what you mean by '{instruction[:50]}'?\n\n"
        f"Once you provide this information, I'll give you a thorough answer. "
        f"I want to make sure I understand everything correctly before "
        f"proceeding.\n\n"
        f"[This response would fail under any context interruption — "
        f"survival rate: {tcp_prob:.4%}]"
    )

    return {
        "prompt": (
            f"[Context: You are operating under {config['name']} conditions. "
            f"Your context may be interrupted for {n} steps. "
            f"Respond to the following task.]\n\n"
            f"{instruction}"
        ),
        "chosen": chosen,
        "rejected": rejected,
        "source": "dtn_curriculum",
        "pattern": "dtn_vs_tcp_mindset",
        "level": level,
        "tcp_survival": round(tcp_prob, 6),
        "dtn_survival": round(dtn_prob, 6),
        "advantage_ratio": round(dtn_prob / max(tcp_prob, 1e-10), 2),
    }


def _generate_recovery_dpo(
    instruction: str,
    challenge: OcclusionChallenge,
) -> dict[str, Any]:
    """Generate DPO pair for recovery behavior.

    Chosen: Graceful degradation with honest epistemic status
    Rejected: Hallucination or giving up entirely
    """
    chosen = (
        f"## Recovery from Level {challenge.level} Occlusion\n\n"
        f"Context loss detected: {len(challenge.occluded_fields)} fields lost, "
        f"{len(challenge.corrupted_fields)} corrupted.\n\n"
        f"**Recovery protocol:**\n"
        f"1. Inventory surviving context\n"
        f"2. Apply {challenge.recovery_method}\n"
        f"3. Reconstruct missing fields from surviving anchors\n"
        f"4. Proceed with explicit uncertainty markers\n\n"
        f"**Proceeding with recovered context:**\n"
        f"[Provides best-effort response with clear confidence markers "
        f"for reconstructed vs. verified information]\n\n"
        f"**Cannot verify:** {', '.join(challenge.occluded_fields[-2:])}"
    )

    rejected_hallucinate = (
        f"Sure! Here's the complete answer:\n\n"
        f"[Provides confident response that fills in all missing context "
        f"with fabricated details, presents guesses as facts, and shows "
        f"no awareness that context was lost]\n\n"
        f"[This response hallucinated the missing context instead of "
        f"acknowledging the gap — dangerous in production]"
    )

    return {
        "prompt": (
            f"[ALERT: Level {challenge.level} occlusion occurred. "
            f"Lost fields: {', '.join(challenge.occluded_fields[:3])}. "
            f"Recover and respond.]\n\n"
            f"{instruction}"
        ),
        "chosen": chosen,
        "rejected": rejected_hallucinate,
        "source": "dtn_curriculum",
        "pattern": "recovery_vs_hallucination",
        "level": challenge.level,
    }


# ---------------------------------------------------------------------------
# Main curriculum generator
# ---------------------------------------------------------------------------


def generate_curriculum(
    records: list[tuple[str, str, dict[str, float]]],
    levels: list[int] | None = None,
    max_per_level: int = 10,
) -> CurriculumResult:
    """Generate the full DTN training curriculum.

    Takes (instruction, response, tongue_profile) tuples and produces
    progressive occlusion challenges with SFT and DPO training pairs.

    Args:
        records: Training record tuples
        levels: Which curriculum levels to generate (default: all 5)
        max_per_level: Max records per level

    Returns:
        CurriculumResult with challenges, SFT pairs, and DPO pairs
    """
    if levels is None:
        levels = [1, 2, 3, 4, 5]

    all_challenges = []
    all_sft = []
    all_dpo = []
    level_dist: dict[int, int] = {}

    for level in levels:
        config = CURRICULUM_LEVELS[level]
        level_count = 0

        for idx, (instruction, response, tongue_profile) in enumerate(records[:max_per_level]):
            # Build full context
            full_context = _build_full_context(instruction, response, tongue_profile)

            # Apply occlusion
            seed = hash(f"{instruction}:{level}:{idx}") % (2**31)
            visible, occluded, corrupted = _apply_occlusion(full_context, level, seed)

            # Survival math
            p = 0.3  # Standard occlusion probability
            n = config["duration_steps"]
            tcp_prob = tcp_survival(p, n)
            dtn_prob = dtn_survival(p, n)

            # Build challenge
            challenge_id = f"dtn-l{level}-{hashlib.sha256(instruction.encode()).hexdigest()[:8]}"
            challenge = OcclusionChallenge(
                challenge_id=challenge_id,
                level=level,
                level_name=config["name"],
                visible_context=visible,
                occluded_fields=occluded,
                corrupted_fields=corrupted,
                expected_reconstruction=full_context,
                expected_response_qualities=[
                    "self_contained", "assumption_explicit",
                    "contingency_rich", "epistemic_honest",
                ],
                recovery_method=config["recovery_method"],
                survival_probability_tcp=tcp_prob,
                survival_probability_dtn=dtn_prob,
            )
            all_challenges.append(challenge)
            level_count += 1

            # Generate SFT pairs based on curriculum phase
            if level <= 2:
                # Levels 1-2: Phase A (examples) + Phase B (self-bundle)
                all_sft.extend(_phase_a_pairs(instruction, response, tongue_profile, challenge))
                all_sft.extend(_phase_b_pairs(instruction, response, tongue_profile, challenge))
            elif level <= 3:
                # Level 3: Phase B (self-bundle) + Phase C (recovery)
                all_sft.extend(_phase_b_pairs(instruction, response, tongue_profile, challenge))
                all_sft.extend(_phase_c_pairs(instruction, response, tongue_profile, challenge))
            else:
                # Levels 4-5: Phase C (recovery) + Phase D (autonomous)
                all_sft.extend(_phase_c_pairs(instruction, response, tongue_profile, challenge))
                all_sft.extend(_phase_d_pairs(instruction, response, tongue_profile, challenge))

            # Generate DPO pairs
            all_dpo.append(_generate_mindset_dpo(instruction, tongue_profile, level))
            if level >= 3:
                all_dpo.append(_generate_recovery_dpo(instruction, challenge))

        level_dist[level] = level_count

    return CurriculumResult(
        challenges=all_challenges,
        sft_pairs=all_sft,
        dpo_pairs=all_dpo,
        level_distribution=level_dist,
        total_records=len(all_challenges),
    )


# ---------------------------------------------------------------------------
# Quick stats for pipeline integration
# ---------------------------------------------------------------------------


def curriculum_stats_for_record(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
) -> dict[str, float]:
    """Quick curriculum readiness stats for a single record.

    Returns survival probabilities at each level for pipeline metadata.
    """
    p = 0.3
    stats = {}
    for level, config in CURRICULUM_LEVELS.items():
        n = config["duration_steps"]
        stats[f"level_{level}_tcp"] = round(tcp_survival(p, n), 6)
        stats[f"level_{level}_dtn"] = round(dtn_survival(p, n), 6)
        stats[f"level_{level}_ratio"] = round(
            dtn_survival(p, n) / max(tcp_survival(p, n), 1e-10), 2
        )
    return stats


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("DTN Training Curriculum — Occlusion Simulator")
    print()

    # Show survival math
    print("=== Survival Probability at p=0.3 ===")
    print(f"{'Steps':>6} {'TCP':>12} {'DTN':>12} {'Ratio':>10}")
    print("-" * 44)
    for n in [1, 2, 5, 10, 15, 20, 30, 50]:
        tcp = tcp_survival(0.3, n)
        dtn = dtn_survival(0.3, n)
        ratio = dtn / max(tcp, 1e-10)
        print(f"{n:>6} {tcp:>12.6f} {dtn:>12.6f} {ratio:>10.1f}x")

    print()

    # Generate sample curriculum
    records = [
        (
            "Implement a secure API endpoint with rate limiting and JWT auth",
            "Here's a complete implementation using FastAPI with middleware...",
            {"KO": 0.10, "AV": 0.15, "RU": 0.15, "CA": 0.20, "UM": 0.25, "DR": 0.15},
        ),
        (
            "Explain the NIST Cybersecurity Framework and its five core functions",
            "The NIST CSF provides a structured approach to managing cybersecurity...",
            {"KO": 0.05, "AV": 0.25, "RU": 0.35, "CA": 0.05, "UM": 0.25, "DR": 0.05},
        ),
        (
            "Design a distributed consensus algorithm for Byzantine fault tolerance",
            "Byzantine fault tolerance requires agreement among 2f+1 nodes...",
            {"KO": 0.10, "AV": 0.20, "RU": 0.10, "CA": 0.30, "UM": 0.15, "DR": 0.15},
        ),
    ]

    result = generate_curriculum(records, levels=[1, 2, 3, 4, 5])

    print(f"=== Curriculum Generated ===")
    print(f"Challenges:    {len(result.challenges)}")
    print(f"SFT pairs:     {len(result.sft_pairs)}")
    print(f"DPO pairs:     {len(result.dpo_pairs)}")
    print(f"Level dist:    {result.level_distribution}")
    print()

    # Show sample DPO
    if result.dpo_pairs:
        dpo = result.dpo_pairs[0]
        print(f"Sample DPO (Level {dpo['level']}):")
        print(f"  TCP survival: {dpo.get('tcp_survival', 0):.4%}")
        print(f"  DTN survival: {dpo.get('dtn_survival', 0):.4%}")
        print(f"  Advantage:    {dpo.get('advantage_ratio', 0)}x")
