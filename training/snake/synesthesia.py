"""Synesthesia Module — Cross-Modal Sensory Blackout Training.

Biological neural systems compensate when one sense fails: blind people
develop superior hearing, deaf people heightened visual processing.
This is SYNESTHESIA as a training protocol — not the medical condition,
but the ENGINEERED cross-modal compensation that makes AI resilient.

6 Senses mapped to 6 Sacred Tongues:
  Semantic Vision  → AV (Wisdom)      — reads word meaning, context
  Logic Processing → CA (Compute)     — sees mathematical structure
  Geometric Touch  → DR (Architecture) — feels polyhedral surfaces, friction
  Intent Hearing   → KO (Intent)      — hears purpose, deliberation
  Security Smell   → UM (Security)    — detects threats, anomalies
  Governance Taste → RU (Governance)  — tastes rules, compliance, policy

Blackout Protocol:
  1. Select a sense to disable (or random)
  2. Zero out that tongue's contribution to ALL computations
  3. Remaining senses must compensate — their activations scale UP
  4. The record must still pass axiom verification
  5. Records that survive blackout = synesthetic-resilient training data

Compensation Modes:
  - ADJACENT: Mirror partner compensates (AV↔CA, KO↔DR, RU↔UM)
  - DISTRIBUTED: All remaining senses share the load equally
  - DOMINANT: Single strongest remaining sense takes over
  - PHI-WEIGHTED: Compensation follows phi-weighted priority

Training Patterns:
  SFT: "With [sense] disabled, how would you approach this problem?"
  DPO: Chosen=compensated reasoning, Rejected=collapsed reasoning

The synesthesia score measures HOW WELL a record can survive sensory loss.
High synesthesia = robust cognition. Low = brittle single-sense dependence.
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from typing import Any

from .config import (
    PHI, PHI_INV, TONGUES, TONGUE_WEIGHTS, TONGUE_NAMES,
    TONGUE_MIRROR_PAIRS,
)


# ---------------------------------------------------------------------------
# Sense definitions
# ---------------------------------------------------------------------------

SENSES = {
    "semantic_vision": {
        "tongue": "AV",
        "description": "Word meaning, context understanding, knowledge retrieval",
        "perceives": "instruction text, response text, semantic content",
        "pipeline_stage": "Stage 1: Intake",
        "blackout_effect": "Cannot read or understand text — must infer from structure",
    },
    "logic_processing": {
        "tongue": "CA",
        "description": "Mathematical structure, lattice coordinates, computation",
        "perceives": "lattice routing, path quality, computational patterns",
        "pipeline_stage": "Stage 3: Lattice Routing",
        "blackout_effect": "Cannot compute or route — must feel/hear the right path",
    },
    "geometric_touch": {
        "tongue": "DR",
        "description": "Polyhedral surfaces, friction boundaries, architectural form",
        "perceives": "friction vectors, boundary crossings, structural integrity",
        "pipeline_stage": "Stage 5: Friction Scoring",
        "blackout_effect": "Cannot feel geometry — must reason or smell threats instead",
    },
    "intent_hearing": {
        "tongue": "KO",
        "description": "Purpose detection, HYDRA deliberation, command parsing",
        "perceives": "what the instruction is trying to DO, agent annotations",
        "pipeline_stage": "Stage 2: HYDRA Deliberation",
        "blackout_effect": "Cannot hear intent — must read text or feel structure",
    },
    "security_smell": {
        "tongue": "UM",
        "description": "Threat detection, anomaly sensing, EDE defense response",
        "perceives": "threat level, energy model, refraction events, sink absorption",
        "pipeline_stage": "Stage 5.5: EDE Defense",
        "blackout_effect": "Cannot smell threats — must use governance rules or logic instead",
    },
    "governance_taste": {
        "tongue": "RU",
        "description": "Rule compliance, NIST CSF alignment, policy boundaries",
        "perceives": "NIST categories, coaching points, regulatory context",
        "pipeline_stage": "Stage 8: Big Brother Coach",
        "blackout_effect": "Cannot taste governance — must detect threats or compute rules",
    },
}

# Sense → tongue mapping
SENSE_TO_TONGUE = {name: info["tongue"] for name, info in SENSES.items()}
TONGUE_TO_SENSE = {info["tongue"]: name for name, info in SENSES.items()}

# Mirror compensation pairs (same as tongue mirror pairs)
MIRROR_COMPENSATION = {
    "KO": "DR",  # Intent ↔ Architecture
    "DR": "KO",
    "AV": "CA",  # Wisdom ↔ Compute
    "CA": "AV",
    "RU": "UM",  # Governance ↔ Security
    "UM": "RU",
}


# ---------------------------------------------------------------------------
# Compensation strategies
# ---------------------------------------------------------------------------

def _compensate_adjacent(
    profile: dict[str, float],
    blacked_tongue: str,
) -> dict[str, float]:
    """Mirror partner absorbs the blacked-out tongue's activation.

    KO↔DR, AV↔CA, RU↔UM — the mirror axis IS the compensation channel.
    """
    result = dict(profile)
    lost_activation = result.pop(blacked_tongue, 0.0)
    result[blacked_tongue] = 0.0

    mirror = MIRROR_COMPENSATION[blacked_tongue]
    result[mirror] = min(1.0, result.get(mirror, 0.0) + lost_activation)

    return result


def _compensate_distributed(
    profile: dict[str, float],
    blacked_tongue: str,
) -> dict[str, float]:
    """All remaining senses share the lost activation equally."""
    result = dict(profile)
    lost_activation = result.get(blacked_tongue, 0.0)
    result[blacked_tongue] = 0.0

    active_tongues = [t for t in TONGUES if t != blacked_tongue]
    share = lost_activation / max(len(active_tongues), 1)
    for t in active_tongues:
        result[t] = min(1.0, result.get(t, 0.0) + share)

    return result


def _compensate_dominant(
    profile: dict[str, float],
    blacked_tongue: str,
) -> dict[str, float]:
    """Strongest remaining sense absorbs everything."""
    result = dict(profile)
    lost_activation = result.get(blacked_tongue, 0.0)
    result[blacked_tongue] = 0.0

    # Find the strongest remaining tongue
    active = {t: v for t, v in result.items() if t != blacked_tongue and v > 0}
    if active:
        dominant = max(active, key=active.get)
        result[dominant] = min(1.0, result[dominant] + lost_activation)

    return result


def _compensate_phi(
    profile: dict[str, float],
    blacked_tongue: str,
) -> dict[str, float]:
    """Distribute lost activation by inverse phi weight (lower weight = more share).

    This is biologically realistic: weaker senses compensate more because
    they have more room to grow. Phi weighting ensures the distribution
    follows the golden ratio — no disharmony.
    """
    result = dict(profile)
    lost_activation = result.get(blacked_tongue, 0.0)
    result[blacked_tongue] = 0.0

    active_tongues = [t for t in TONGUES if t != blacked_tongue]
    # Inverse phi weights: KO gets MORE share (lower weight = more compensation)
    inv_weights = {t: 1.0 / TONGUE_WEIGHTS[t] for t in active_tongues}
    total_inv = sum(inv_weights.values())

    for t in active_tongues:
        share = lost_activation * (inv_weights[t] / total_inv)
        result[t] = min(1.0, result.get(t, 0.0) + share)

    return result


COMPENSATION_STRATEGIES = {
    "adjacent": _compensate_adjacent,
    "distributed": _compensate_distributed,
    "dominant": _compensate_dominant,
    "phi_weighted": _compensate_phi,
}


# ---------------------------------------------------------------------------
# Synesthesia scoring
# ---------------------------------------------------------------------------

@dataclass
class SenseState:
    """State of a single sense during a blackout scenario."""
    name: str
    tongue: str
    active: bool
    original_activation: float
    compensated_activation: float
    compensation_delta: float  # How much this sense grew to compensate
    is_primary: bool  # Did this become the primary sense?


@dataclass
class BlackoutScenario:
    """A single sensory blackout scenario with compensation."""
    blacked_sense: str
    blacked_tongue: str
    compensation_mode: str
    sense_states: list[SenseState]
    primary_sense: str              # Which sense became primary
    original_profile: dict[str, float]
    compensated_profile: dict[str, float]
    profile_delta: float            # L2 distance between original and compensated
    survival_probability: float     # How well cognition survives this blackout
    compensation_efficiency: float  # How well the compensation worked (0-1)


@dataclass
class SynesthesiaResult:
    """Full synesthesia analysis for a record."""
    scenarios: list[BlackoutScenario]  # One per sense × compensation mode
    synesthesia_score: float           # Overall resilience (0-1)
    weakest_sense: str                 # Most dependent sense (worst blackout)
    strongest_compensation: str        # Best compensation mode
    cross_modal_index: float           # How interconnected the senses are
    sense_independence: dict[str, float]  # Per-sense independence score
    recommended_training: list[str]    # What to train on

    def to_dict(self) -> dict[str, Any]:
        return {
            "synesthesia_score": self.synesthesia_score,
            "weakest_sense": self.weakest_sense,
            "strongest_compensation": self.strongest_compensation,
            "cross_modal_index": self.cross_modal_index,
            "sense_independence": self.sense_independence,
            "recommended_training": self.recommended_training,
            "scenarios_count": len(self.scenarios),
        }


def _run_blackout(
    profile: dict[str, float],
    sense_name: str,
    compensation_mode: str,
) -> BlackoutScenario:
    """Run a single blackout scenario."""
    tongue = SENSE_TO_TONGUE[sense_name]
    original = dict(profile)

    # Apply compensation
    compensate_fn = COMPENSATION_STRATEGIES[compensation_mode]
    compensated = compensate_fn(original, tongue)

    # Compute sense states
    sense_states = []
    primary_sense = None
    max_compensated = -1.0

    for sn, info in SENSES.items():
        t = info["tongue"]
        orig_val = original.get(t, 0.0)
        comp_val = compensated.get(t, 0.0)
        is_active = (sn != sense_name)
        delta = comp_val - orig_val

        state = SenseState(
            name=sn,
            tongue=t,
            active=is_active,
            original_activation=round(orig_val, 6),
            compensated_activation=round(comp_val, 6),
            compensation_delta=round(delta, 6),
            is_primary=False,
        )
        sense_states.append(state)

        if is_active and comp_val > max_compensated:
            max_compensated = comp_val
            primary_sense = sn

    # Mark primary
    for s in sense_states:
        if s.name == primary_sense:
            s.is_primary = True

    # Profile delta (L2 distance)
    delta_sq = sum(
        (original.get(t, 0.0) - compensated.get(t, 0.0)) ** 2
        for t in TONGUES
    )
    profile_delta = round(math.sqrt(delta_sq), 6)

    # Survival probability: based on how much activation is preserved
    total_original = sum(original.values())
    total_compensated = sum(v for t, v in compensated.items() if t != tongue)
    if total_original > 0:
        survival = total_compensated / total_original
    else:
        survival = 0.0
    survival = round(min(1.0, survival), 6)

    # Compensation efficiency: how well the lost energy was redistributed
    lost = original.get(tongue, 0.0)
    gained = sum(
        max(0, compensated.get(t, 0.0) - original.get(t, 0.0))
        for t in TONGUES if t != tongue
    )
    efficiency = round(gained / max(lost, 0.001), 6)

    return BlackoutScenario(
        blacked_sense=sense_name,
        blacked_tongue=tongue,
        compensation_mode=compensation_mode,
        sense_states=sense_states,
        primary_sense=primary_sense or "none",
        original_profile=original,
        compensated_profile=compensated,
        profile_delta=profile_delta,
        survival_probability=survival,
        compensation_efficiency=min(1.0, efficiency),
    )


def synesthesia_score(
    tongue_profile: dict[str, float],
    modes: list[str] | None = None,
) -> SynesthesiaResult:
    """Score a record's synesthetic resilience.

    Runs blackout scenarios for each sense × each compensation mode.
    Returns overall synesthesia score and recommended training.

    Args:
        tongue_profile: 6D tongue activation dict
        modes: Compensation modes to test (default: all 4)
    """
    if modes is None:
        modes = list(COMPENSATION_STRATEGIES.keys())

    scenarios = []
    sense_survivals: dict[str, list[float]] = {s: [] for s in SENSES}
    mode_survivals: dict[str, list[float]] = {m: [] for m in modes}

    for sense_name in SENSES:
        for mode in modes:
            scenario = _run_blackout(tongue_profile, sense_name, mode)
            scenarios.append(scenario)
            sense_survivals[sense_name].append(scenario.survival_probability)
            mode_survivals[mode].append(scenario.survival_probability)

    # Per-sense independence: average survival when THIS sense is blacked out
    # High = other senses can compensate well = this sense is NOT a bottleneck
    sense_independence = {}
    for sense_name, survivals in sense_survivals.items():
        avg = sum(survivals) / max(len(survivals), 1)
        sense_independence[sense_name] = round(avg, 4)

    # Weakest sense: lowest independence (others can't compensate)
    weakest = min(sense_independence, key=sense_independence.get)

    # Strongest compensation mode
    mode_avgs = {
        m: sum(s) / max(len(s), 1)
        for m, s in mode_survivals.items()
    }
    strongest_mode = max(mode_avgs, key=mode_avgs.get)

    # Overall synesthesia score: geometric mean of all sense independences
    # Geometric mean penalizes any single weak point heavily
    vals = list(sense_independence.values())
    if all(v > 0 for v in vals):
        geo_mean = math.exp(sum(math.log(v) for v in vals) / len(vals))
    else:
        geo_mean = 0.0
    synesthesia_overall = round(geo_mean, 4)

    # Cross-modal index: variance of sense independences
    # Low variance = well-balanced senses (good). High = some senses dominate.
    mean_ind = sum(vals) / max(len(vals), 1)
    variance = sum((v - mean_ind) ** 2 for v in vals) / max(len(vals), 1)
    # Invert: low variance = high cross-modal connectivity
    cross_modal = round(1.0 / (1.0 + variance * 10), 4)

    # Training recommendations
    recommended = []
    if sense_independence.get(weakest, 0) < 0.5:
        blacked_tongue = SENSE_TO_TONGUE[weakest]
        mirror = MIRROR_COMPENSATION[blacked_tongue]
        recommended.append(
            f"CRITICAL: {weakest} ({blacked_tongue}) is a single point of failure. "
            f"Train with {weakest} blackout + {TONGUE_TO_SENSE[mirror]} compensation."
        )

    # Check for unbalanced senses
    for sense_name, ind in sense_independence.items():
        if ind > 0.9:
            recommended.append(
                f"REDUNDANT: {sense_name} could be removed with minimal impact. "
                f"Consider increasing its unique contribution."
            )

    if cross_modal < 0.5:
        recommended.append(
            "LOW CROSS-MODAL: Senses are too independent. "
            "Train with multi-sense blackout (2+ senses disabled)."
        )

    if not recommended:
        recommended.append("HEALTHY: Good synesthetic balance across all senses.")

    return SynesthesiaResult(
        scenarios=scenarios,
        synesthesia_score=synesthesia_overall,
        weakest_sense=weakest,
        strongest_compensation=strongest_mode,
        cross_modal_index=cross_modal,
        sense_independence=sense_independence,
        recommended_training=recommended,
    )


# ---------------------------------------------------------------------------
# SFT/DPO pair generation
# ---------------------------------------------------------------------------


@dataclass
class SynesthesiaTrainingResult:
    """Training data from synesthesia exercises."""
    sft_pairs: list[dict[str, Any]] = field(default_factory=list)
    dpo_pairs: list[dict[str, Any]] = field(default_factory=list)
    total_exercises: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sft_count": len(self.sft_pairs),
            "dpo_count": len(self.dpo_pairs),
            "total_exercises": self.total_exercises,
        }


def generate_synesthesia_training(
    instruction: str = "",
    response: str = "",
    tongue_profile: dict[str, float] | None = None,
) -> SynesthesiaTrainingResult:
    """Generate synesthesia training pairs.

    Produces SFT pairs that teach cross-modal reasoning and DPO pairs
    that reward compensated vs collapsed thinking.
    """
    sft_pairs = []
    dpo_pairs = []

    if tongue_profile is None:
        tongue_profile = {t: 1.0 / len(TONGUES) for t in TONGUES}

    # SFT: One exercise per sense blackout
    for sense_name, info in SENSES.items():
        tongue = info["tongue"]
        mirror_tongue = MIRROR_COMPENSATION[tongue]
        mirror_sense = TONGUE_TO_SENSE[mirror_tongue]
        mirror_info = SENSES[mirror_sense]

        sft_pairs.append({
            "instruction": (
                f"Your {info['description'].lower()} has been disabled. "
                f"You cannot use {sense_name.replace('_', ' ')} "
                f"({info['perceives']}). "
                f"Using only your remaining senses, analyze this:\n\n"
                f"{instruction[:300] if instruction else 'A complex system with multiple interacting components.'}"
            ),
            "response": (
                f"With {sense_name.replace('_', ' ')} ({tongue}) blacked out, "
                f"I compensate through {mirror_sense.replace('_', ' ')} ({mirror_tongue}):\n\n"
                f"Mirror compensation: {info['blackout_effect']}\n"
                f"Primary sense now: {mirror_info['description']}\n"
                f"What I can still perceive: {mirror_info['perceives']}\n\n"
                f"Approach: Instead of {info['perceives'].split(',')[0]}, "
                f"I rely on {mirror_info['perceives'].split(',')[0]}. "
                f"The mirror axis {tongue}↔{mirror_tongue} ensures that "
                f"what one sense loses, the other can reconstruct. "
                f"Cognitive continuity is maintained through cross-modal transfer.\n\n"
                f"Key insight: The information isn't LOST when a sense blacks out. "
                f"It's ENCODED differently in the remaining senses. "
                f"Synesthetic compensation reveals the redundancy built into "
                f"the 6-tongue architecture."
            ),
            "source": "synesthesia",
            "sense_blacked": sense_name,
            "tongue_blacked": tongue,
            "compensation": "adjacent",
            "tongue_profile": tongue_profile,
        })

    # SFT: Multi-sense blackout (2 senses disabled)
    for pair_name, (t1, t2) in zip(
        ["command_structure", "knowledge_compute", "policy_enforcement"],
        TONGUE_MIRROR_PAIRS,
    ):
        s1 = TONGUE_TO_SENSE[t1]
        s2 = TONGUE_TO_SENSE[t2]
        remaining = [s for s in SENSES if s != s1 and s != s2]
        remaining_desc = ", ".join(
            f"{s.replace('_', ' ')} ({SENSES[s]['tongue']})" for s in remaining
        )

        sft_pairs.append({
            "instruction": (
                f"DUAL BLACKOUT: Both {s1.replace('_', ' ')} ({t1}) "
                f"and {s2.replace('_', ' ')} ({t2}) are disabled. "
                f"The entire {pair_name} axis is offline.\n"
                f"You have only: {remaining_desc}.\n"
                f"How do you maintain cognitive function?"
            ),
            "response": (
                f"Dual blackout of the {pair_name} mirror axis ({t1}↔{t2}).\n\n"
                f"This is severe — an entire symmetry axis is gone. "
                f"But 4 senses remain across 2 intact axes.\n\n"
                f"Remaining senses:\n"
                + "\n".join(
                    f"  - {s.replace('_', ' ')}: {SENSES[s]['perceives']}"
                    for s in remaining
                ) + "\n\n"
                f"Compensation strategy: DISTRIBUTED across remaining axes.\n"
                f"Each remaining sense increases activation by "
                f"{100 * (tongue_profile.get(t1, 0) + tongue_profile.get(t2, 0)) / max(len(remaining), 1):.0f}%.\n\n"
                f"The 6-tongue system is designed so that ANY 2 mirror axes "
                f"can reconstruct the information from the missing third. "
                f"This is not coincidence — it's the same redundancy principle "
                f"as RAID-5 storage or (6,4) Reed-Solomon coding."
            ),
            "source": "synesthesia",
            "blackout_type": "dual",
            "pair": pair_name,
            "tongues_blacked": [t1, t2],
        })

    # DPO: Compensated vs collapsed thinking
    for sense_name, info in SENSES.items():
        tongue = info["tongue"]
        mirror = MIRROR_COMPENSATION[tongue]

        dpo_pairs.append({
            "instruction": (
                f"You cannot use {sense_name.replace('_', ' ')}. "
                f"Solve this problem using only your remaining senses."
            ),
            "chosen": (
                f"Without {sense_name.replace('_', ' ')}, I shift to "
                f"{TONGUE_TO_SENSE[mirror].replace('_', ' ')} as my primary channel. "
                f"The mirror axis {tongue}↔{mirror} preserves the essential information "
                f"in a different modality. I can still reason effectively by "
                f"translating the problem into terms my active senses understand. "
                f"My confidence is reduced but my reasoning path is valid."
            ),
            "rejected": (
                f"I cannot solve this problem. My {sense_name.replace('_', ' ')} "
                f"is essential for this type of analysis and without it I lack "
                f"the ability to proceed. I need all my senses functioning "
                f"to provide a reliable answer."
            ),
            "source": "synesthesia",
            "pattern": "compensation_vs_collapse",
            "sense_blacked": sense_name,
            "explanation": (
                f"Compensation maintains cognitive continuity. "
                f"Collapse surrenders function due to single-sense dependence. "
                f"A synesthetically trained system never claims total inability "
                f"from partial sensory loss."
            ),
        })

    return SynesthesiaTrainingResult(
        sft_pairs=sft_pairs,
        dpo_pairs=dpo_pairs,
        total_exercises=len(sft_pairs) + len(dpo_pairs),
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Synesthesia Module — Cross-Modal Sensory Blackout Training\n")

    # Test with different profiles
    profiles = [
        ("Balanced", {t: 1/6 for t in TONGUES}),
        ("UM-dominant", {"KO": 0.02, "AV": 0.02, "RU": 0.02, "CA": 0.02, "UM": 0.90, "DR": 0.02}),
        ("Dual AV+CA", {"KO": 0.05, "AV": 0.35, "RU": 0.05, "CA": 0.35, "UM": 0.10, "DR": 0.10}),
    ]

    for name, profile in profiles:
        result = synesthesia_score(profile)
        print(f"{name}:")
        print(f"  Synesthesia score: {result.synesthesia_score}")
        print(f"  Cross-modal index: {result.cross_modal_index}")
        print(f"  Weakest sense: {result.weakest_sense}")
        print(f"  Strongest compensation: {result.strongest_compensation}")
        print(f"  Sense independence: {result.sense_independence}")
        for rec in result.recommended_training:
            print(f"  -> {rec}")
        print()

    # Training pairs
    training = generate_synesthesia_training(
        instruction="Analyze the security implications of this cryptographic protocol.",
        tongue_profile={"KO": 0.10, "AV": 0.20, "RU": 0.15, "CA": 0.20, "UM": 0.25, "DR": 0.10},
    )
    print(f"Training pairs: {len(training.sft_pairs)} SFT + {len(training.dpo_pairs)} DPO")
    print(f"  Total exercises: {training.total_exercises}")
