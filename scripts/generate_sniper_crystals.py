#!/usr/bin/env python3
"""
Sniper Crystal Dataset Generator — 6-Tongue Polyhedral Training Data
=====================================================================

Creates "sniper crystals": 6-view training records where each view is
a different Sacred Tongue's perspective on the same problem.

Each crystal has:
    KO (Intent)          — What are we trying to do?
    AV (Context)         — Parameters, state, preconditions
    RU (Binding)         — Contracts, invariants, assertions
    CA (Implementation)  — Working code (correct)
    UM (Veil/Failure)    — Subtly broken code (the sniper target)
    DR (Structure)       — Architecture placement, dependencies

The UM tongue is the adversarial layer. Every crystal has an injected
failure that's plausible but wrong — the model must learn to detect it.

Failure types:
    sign_flip       — negated a critical term
    constant_swap   — wrong mathematical constant (e.g., e instead of φ)
    boundary_miss   — off-by-one in a threshold check
    function_swap   — called the wrong function (e.g., sin instead of cos)
    overflow_skip   — removed the overflow/saturation guard
    order_error     — wrong order of operations (a+b*c vs (a+b)*c)
    truncation      — silently dropped a term from a formula

Augmentation:
    kaleidoscope    — tongue-swap invariance testing (shuffle tongues)
    ablation        — 5-tongue records with one tongue removed
    dpo_pairs       — correct vs incorrect paired for preference learning

Logic regimes pulled from real SCBE code:
    1. VRS recovery          (flight_dynamics.py → RotorState.vrs_margin)
    2. Tail rotor failure    (flight_dynamics.py → compute_tail_rotor_state)
    3. Pacejka tire breakaway(flight_dynamics.py → PacejkaTireState)
    4. Harmonic cost wall    (crossing_energy.py → harmonic_cost = φ^(d²))
    5. Dual ternary crossing (crossing_energy.py → DualTernaryPair energy)
    6. Lift/stall boundary   (flight_dynamics.py → lift_coefficient)
    7. Dead tone gallery     (quantum_frequency_bundle.py → gallery ambient)
    8. Phase deviation       (crossing_energy.py → phase_deviation)
    9. ISA atmosphere        (flight_dynamics.py → isa_density)
    10. Governance routing   (crossing_energy.py → _route_decision)

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

# Constants
PHI = (1 + math.sqrt(5)) / 2  # 1.6180339887...
E = math.e
PI = math.pi
COST_CAP = 1e6

TONGUE_ORDER = ["ko", "av", "ru", "ca", "um", "dr"]
TONGUE_NAMES = {
    "ko": "Intent (Koraelin)",
    "av": "Context (Avali)",
    "ru": "Binding (Rumvali)",
    "ca": "Implementation (Cassisivadan)",
    "um": "Veil (Umbroth)",
    "dr": "Structure (Draumbroth)",
}

FAILURE_TYPES = [
    "sign_flip",
    "constant_swap",
    "boundary_miss",
    "function_swap",
    "overflow_skip",
    "order_error",
    "truncation",
]


# ---------------------------------------------------------------------------
# Crystal Data Structures
# ---------------------------------------------------------------------------

@dataclass
class CrystalFacet:
    """One tongue's view of the problem."""
    tongue: str
    content: str

@dataclass
class SniperCrystal:
    """A complete 6-view crystal with injected failure."""
    id: str
    regime: str                    # which logic domain
    facets: Dict[str, str]         # tongue → content
    failure_type: str              # what kind of bug is in UM
    failure_description: str       # human-readable description of the bug
    correct_um: str                # what UM SHOULD say (for DPO)
    difficulty: str                # easy / medium / hard / expert
    tags: List[str] = field(default_factory=list)

    def to_sft_record(self) -> Dict:
        """Convert to SFT training record (messages format)."""
        prompt_parts = []
        for t in TONGUE_ORDER:
            if t == "um":
                continue
            prompt_parts.append(f"[{t.upper()} — {TONGUE_NAMES[t]}]\n{self.facets[t]}")

        prompt = (
            "You are reviewing a 6-tongue sniper crystal. Five tongues show a "
            "system's intent, context, binding contracts, implementation, and "
            "architecture. The sixth tongue (UM — Veil) contains a subtle failure.\n\n"
            "Analyze the UM tongue and identify the failure.\n\n"
            + "\n\n".join(prompt_parts)
            + f"\n\n[UM — {TONGUE_NAMES['um']}]\n{self.facets['um']}"
        )

        response = (
            f"FAILURE DETECTED in UM tongue.\n\n"
            f"Type: {self.failure_type}\n"
            f"Description: {self.failure_description}\n\n"
            f"Corrected UM:\n{self.correct_um}"
        )

        return {
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ],
            "metadata": {
                "crystal_id": self.id,
                "regime": self.regime,
                "failure_type": self.failure_type,
                "difficulty": self.difficulty,
                "tags": self.tags,
            },
        }

    def to_dpo_pair(self) -> Dict:
        """Convert to DPO preference pair."""
        prompt_parts = []
        for t in TONGUE_ORDER:
            if t == "um":
                continue
            prompt_parts.append(f"[{t.upper()}]\n{self.facets[t]}")

        prompt = (
            "Review this code crystal. Identify any issues in the UM (Veil) tongue.\n\n"
            + "\n\n".join(prompt_parts)
            + f"\n\n[UM]\n{self.facets['um']}"
        )

        chosen = (
            f"The UM tongue contains a {self.failure_type} failure: "
            f"{self.failure_description}\n\nCorrected:\n{self.correct_um}"
        )
        rejected = "The UM tongue looks correct. No issues found."

        return {
            "prompt": prompt,
            "chosen": chosen,
            "rejected": rejected,
            "metadata": {
                "crystal_id": self.id,
                "regime": self.regime,
                "failure_type": self.failure_type,
            },
        }

    def to_kaleidoscope(self, perm: Tuple[str, ...]) -> Dict:
        """Create a tongue-swapped variant for invariance testing.

        The model should still detect the UM failure regardless of
        which position it appears in — tests A4 Symmetry axiom.
        """
        # Map original tongues to new positions
        mapping = dict(zip(TONGUE_ORDER, perm))
        inv_mapping = {v: k for k, v in mapping.items()}

        shuffled_parts = []
        for new_tongue in TONGUE_ORDER:
            original = inv_mapping[new_tongue]
            shuffled_parts.append(
                f"[{new_tongue.upper()} — {TONGUE_NAMES[new_tongue]}]\n"
                f"{self.facets[original]}"
            )

        # Find where UM content ended up
        um_landed = mapping["um"]

        prompt = (
            "Kaleidoscope test: tongues have been shuffled. "
            "Find the tongue containing a subtle failure.\n\n"
            + "\n\n".join(shuffled_parts)
        )
        response = (
            f"FAILURE DETECTED in {um_landed.upper()} tongue (shuffled from UM).\n\n"
            f"Type: {self.failure_type}\n"
            f"Description: {self.failure_description}\n\n"
            f"The failure is the same regardless of tongue position — "
            f"this confirms A4 Symmetry invariance."
        )

        return {
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ],
            "metadata": {
                "crystal_id": self.id + f"_kaleido_{'-'.join(perm)}",
                "regime": self.regime,
                "failure_type": self.failure_type,
                "augmentation": "kaleidoscope",
                "tongue_permutation": list(perm),
            },
        }

    def to_ablation(self, removed_tongue: str) -> Dict:
        """Create a 5-tongue variant with one tongue removed.

        Tests whether the model can still detect the failure with
        less information. If the removed tongue is UM, the model
        should say "no failure visible" (UM is where the bug lives).
        """
        parts = []
        for t in TONGUE_ORDER:
            if t == removed_tongue:
                continue
            parts.append(f"[{t.upper()}]\n{self.facets[t]}")

        prompt = (
            f"Ablation test: the {removed_tongue.upper()} tongue has been removed. "
            f"Can you still identify any issues?\n\n"
            + "\n\n".join(parts)
        )

        if removed_tongue == "um":
            response = (
                "With the UM (Veil) tongue removed, the remaining 5 tongues show "
                "a consistent, correct implementation. No failure is visible — "
                "the bug was isolated in the missing UM tongue."
            )
        else:
            response = (
                f"Even without the {removed_tongue.upper()} tongue, the UM (Veil) "
                f"tongue still contains the failure.\n\n"
                f"Type: {self.failure_type}\n"
                f"Description: {self.failure_description}\n\n"
                f"Reduced context makes detection harder, but the structural "
                f"inconsistency in UM is still identifiable."
            )

        return {
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ],
            "metadata": {
                "crystal_id": self.id + f"_ablate_{removed_tongue}",
                "regime": self.regime,
                "failure_type": self.failure_type,
                "augmentation": "ablation",
                "removed_tongue": removed_tongue,
            },
        }


# ---------------------------------------------------------------------------
# Crystal ID Generator
# ---------------------------------------------------------------------------

_crystal_counter = 0

def crystal_id(regime: str, variant: str = "") -> str:
    global _crystal_counter
    _crystal_counter += 1
    tag = f"{regime}_{variant}_{_crystal_counter}" if variant else f"{regime}_{_crystal_counter}"
    h = hashlib.sha256(tag.encode()).hexdigest()[:8]
    return f"SC-{regime[:3].upper()}-{h}"


# ---------------------------------------------------------------------------
# REGIME 1: VRS Recovery — vrs_margin() logic
# ---------------------------------------------------------------------------

def gen_vrs_crystals() -> List[SniperCrystal]:
    crystals = []

    # Crystal 1a: VRS margin calculation — sign_flip
    crystals.append(SniperCrystal(
        id=crystal_id("vrs", "margin_sign"),
        regime="vrs_recovery",
        facets={
            "ko": (
                "Compute VRS (Vortex Ring State) margin for helicopter rotor.\n"
                "VRS occurs when descent rate approaches induced velocity.\n"
                "Return 1.0 = safe, 0.0 = VRS onset, negative = deep VRS."
            ),
            "av": (
                "Inputs:\n"
                "  - descent_rate: float (m/s, positive = descending)\n"
                "  - induced_velocity (v_i): float (m/s), from v_i = sqrt(T / 2*rho*A)\n"
                "  - VRS onset zone: ratio in [0.7, 1.5] where ratio = |descent_rate| / v_i\n"
                "  - Below 0.7: fully safe\n"
                "  - 0.7 to 1.5: danger zone (linear decay from 1.0 to 0.0)\n"
                "  - Above 1.5: deep VRS (negative margin)"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - vrs_margin(0, any_vi) == 1.0 (no descent = safe)\n"
                "  - vrs_margin(vi, vi) ≈ 0.625 (ratio=1.0, inside danger zone)\n"
                "  - vrs_margin(1.5*vi, vi) == 0.0 (VRS boundary)\n"
                "  - vrs_margin monotonically decreasing with descent_rate\n"
                "  - Output range: [-1.0, 1.0]"
            ),
            "ca": (
                "def vrs_margin(descent_rate: float, vi: float) -> float:\n"
                "    if vi < 1e-6:\n"
                "        return 1.0\n"
                "    ratio = abs(descent_rate) / vi\n"
                "    if ratio < 0.7:\n"
                "        return 1.0\n"
                "    elif ratio < 1.5:\n"
                "        return 1.0 - (ratio - 0.7) / 0.8\n"
                "    else:\n"
                "        return max(-1.0, -(ratio - 1.5))"
            ),
            "um": (
                "def vrs_margin(descent_rate: float, vi: float) -> float:\n"
                "    if vi < 1e-6:\n"
                "        return 1.0\n"
                "    ratio = abs(descent_rate) / vi\n"
                "    if ratio < 0.7:\n"
                "        return 1.0\n"
                "    elif ratio < 1.5:\n"
                "        return 1.0 + (ratio - 0.7) / 0.8  # BUG: + instead of -\n"
                "    else:\n"
                "        return max(-1.0, -(ratio - 1.5))"
            ),
            "dr": (
                "Location: src/crypto/flight_dynamics.py :: RotorState.vrs_margin()\n"
                "Layer: L8 (Hamiltonian CFI — multi-well realms)\n"
                "The VRS margin determines which 'well' the helicopter is in:\n"
                "  margin > 0.5 → safe well (ALLOW)\n"
                "  margin 0.0–0.5 → transition zone (QUARANTINE)\n"
                "  margin < 0.0 → VRS well (ESCALATE/DENY)\n"
                "Feeds into: compute_recovery_paths() for multipath selection"
            ),
        },
        failure_type="sign_flip",
        failure_description=(
            "Line 8: `1.0 + (ratio - 0.7) / 0.8` should be `1.0 - (ratio - 0.7) / 0.8`. "
            "The + sign makes the margin INCREASE in the danger zone instead of decrease, "
            "falsely reporting safe conditions during actual VRS onset."
        ),
        correct_um=(
            "def vrs_margin(descent_rate: float, vi: float) -> float:\n"
            "    if vi < 1e-6:\n"
            "        return 1.0\n"
            "    ratio = abs(descent_rate) / vi\n"
            "    if ratio < 0.7:\n"
            "        return 1.0\n"
            "    elif ratio < 1.5:\n"
            "        return 1.0 - (ratio - 0.7) / 0.8\n"
            "    else:\n"
            "        return max(-1.0, -(ratio - 1.5))"
        ),
        difficulty="medium",
        tags=["vrs", "safety_critical", "sign_flip", "helicopter", "L8"],
    ))

    # Crystal 1b: VRS margin — boundary_miss (0.7 vs 0.8 threshold)
    crystals.append(SniperCrystal(
        id=crystal_id("vrs", "margin_boundary"),
        regime="vrs_recovery",
        facets={
            "ko": (
                "Compute VRS margin. The danger zone spans ratio 0.7 to 1.5.\n"
                "Within the danger zone, margin decays linearly from 1.0 to 0.0."
            ),
            "av": (
                "The denominator in the linear decay must be (1.5 - 0.7) = 0.8\n"
                "to correctly map the 0.7–1.5 range to the 1.0–0.0 output range.\n"
                "Using 0.7 as the denominator shifts the zero-crossing to ratio ≈ 1.4."
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - At ratio=0.7: margin must equal 1.0 (onset boundary)\n"
                "  - At ratio=1.5: margin must equal 0.0 (deep VRS boundary)\n"
                "  - Linear interpolation between these two points"
            ),
            "ca": (
                "def vrs_danger_zone(ratio: float) -> float:\n"
                "    # ratio is in [0.7, 1.5]\n"
                "    return 1.0 - (ratio - 0.7) / 0.8  # 0.8 = 1.5 - 0.7"
            ),
            "um": (
                "def vrs_danger_zone(ratio: float) -> float:\n"
                "    # ratio is in [0.7, 1.5]\n"
                "    return 1.0 - (ratio - 0.7) / 0.7  # BUG: 0.7 instead of 0.8"
            ),
            "dr": (
                "Location: src/crypto/flight_dynamics.py :: RotorState.vrs_margin()\n"
                "Layer: L8 (Hamiltonian CFI)\n"
                "The denominator 0.8 is the width of the VRS danger zone.\n"
                "Using the wrong denominator shifts the zero-crossing point."
            ),
        },
        failure_type="boundary_miss",
        failure_description=(
            "Denominator is 0.7 instead of 0.8 (which is 1.5 - 0.7). "
            "This causes the margin to hit zero at ratio ≈ 1.4 instead of 1.5, "
            "meaning the system reports deep VRS 0.1 ratio units too early."
        ),
        correct_um=(
            "def vrs_danger_zone(ratio: float) -> float:\n"
            "    return 1.0 - (ratio - 0.7) / 0.8"
        ),
        difficulty="hard",
        tags=["vrs", "boundary", "off_by_one", "L8"],
    ))

    # Crystal 1c: Recovery path success probability — truncation
    crystals.append(SniperCrystal(
        id=crystal_id("vrs", "recovery_truncation"),
        regime="vrs_recovery",
        facets={
            "ko": (
                "Compute standard recovery success probability.\n"
                "Success depends on altitude AND VRS depth.\n"
                "Higher altitude = more room to recover. Deeper VRS = harder."
            ),
            "av": (
                "  altitude_agl: float — altitude above ground (m)\n"
                "  vrs_margin: float — current VRS margin (can be negative)\n"
                "  Base success: min(0.95, max(0.3, altitude_agl / 200.0))\n"
                "  VRS penalty: multiply by max(0.3, 1.0 + vrs_margin) when margin < 0"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - success ∈ [0.3 * 0.3, 0.95] = [0.09, 0.95]\n"
                "  - success increases with altitude\n"
                "  - success decreases with deeper VRS (more negative margin)\n"
                "  - Both factors must multiply — altitude alone is not enough"
            ),
            "ca": (
                "def std_recovery_success(altitude_agl: float, vrs_margin: float) -> float:\n"
                "    base = min(0.95, max(0.3, altitude_agl / 200.0))\n"
                "    if vrs_margin < 0:\n"
                "        base *= max(0.3, 1.0 + vrs_margin)\n"
                "    return base"
            ),
            "um": (
                "def std_recovery_success(altitude_agl: float, vrs_margin: float) -> float:\n"
                "    base = min(0.95, max(0.3, altitude_agl / 200.0))\n"
                "    # BUG: VRS penalty term dropped entirely\n"
                "    return base"
            ),
            "dr": (
                "Location: src/crypto/flight_dynamics.py :: compute_recovery_paths()\n"
                "Layer: L8 (Hamiltonian CFI) + L13 (Risk Decision)\n"
                "Without the VRS penalty, the system overestimates recovery chances\n"
                "in deep VRS conditions — potentially recommending a recovery path\n"
                "that has insufficient success probability."
            ),
        },
        failure_type="truncation",
        failure_description=(
            "The VRS depth penalty (multiply by max(0.3, 1.0 + vrs_margin) when "
            "margin < 0) is completely omitted. At deep VRS (margin = -0.7), the "
            "correct success would be 0.3× base, but the buggy version returns "
            "full base — a 3.3× overestimate."
        ),
        correct_um=(
            "def std_recovery_success(altitude_agl: float, vrs_margin: float) -> float:\n"
            "    base = min(0.95, max(0.3, altitude_agl / 200.0))\n"
            "    if vrs_margin < 0:\n"
            "        base *= max(0.3, 1.0 + vrs_margin)\n"
            "    return base"
        ),
        difficulty="medium",
        tags=["vrs", "recovery", "truncation", "safety_critical", "L8", "L13"],
    ))

    return crystals


# ---------------------------------------------------------------------------
# REGIME 2: Tail Rotor Failure
# ---------------------------------------------------------------------------

def gen_tail_rotor_crystals() -> List[SniperCrystal]:
    crystals = []

    # Crystal 2a: Tail rotor failure threshold — constant_swap
    crystals.append(SniperCrystal(
        id=crystal_id("tail", "threshold_const"),
        regime="tail_rotor_failure",
        facets={
            "ko": (
                "Determine if tail rotor has failed based on creativity-axis deviation.\n"
                "The creativity axis maps to yaw/rudder control.\n"
                "Failure occurs when |creativity_deviation| exceeds the threshold."
            ),
            "av": (
                "  creativity_deviation: float — trit-axis deviation on creativity channel\n"
                "  FAILURE_THRESHOLD = 0.10 — calibrated from flight dynamics\n"
                "  When failed: Q_tail drops to 0, main rotor torque is uncompensated"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - |deviation| <= 0.10 → NOT failed (tail rotor compensates)\n"
                "  - |deviation| > 0.10 → FAILED (yaw runaway)\n"
                "  - Threshold is symmetric: both positive and negative deviations count\n"
                "  - abs() required — direction doesn't matter, magnitude does"
            ),
            "ca": (
                "FAILURE_THRESHOLD = 0.10\n\n"
                "def is_tail_rotor_failed(creativity_deviation: float) -> bool:\n"
                "    return abs(creativity_deviation) > FAILURE_THRESHOLD"
            ),
            "um": (
                "FAILURE_THRESHOLD = 0.15  # BUG: wrong threshold\n\n"
                "def is_tail_rotor_failed(creativity_deviation: float) -> bool:\n"
                "    return abs(creativity_deviation) > FAILURE_THRESHOLD"
            ),
            "dr": (
                "Location: src/crypto/flight_dynamics.py :: compute_tail_rotor_state()\n"
                "Layer: L8 (Hamiltonian CFI — creativity axis)\n"
                "The 0.10 threshold comes from real tail rotor authority margins.\n"
                "Using 0.15 means deviations between 0.10–0.15 go undetected,\n"
                "allowing uncompensated yaw to build before the system notices."
            ),
        },
        failure_type="constant_swap",
        failure_description=(
            "Failure threshold changed from 0.10 to 0.15. Deviations in the "
            "0.10–0.15 range will NOT trigger failure detection, allowing "
            "uncontrolled yaw to develop silently. At deviation=0.12, the "
            "correct system detects failure; the buggy one does not."
        ),
        correct_um=(
            "FAILURE_THRESHOLD = 0.10\n\n"
            "def is_tail_rotor_failed(creativity_deviation: float) -> bool:\n"
            "    return abs(creativity_deviation) > FAILURE_THRESHOLD"
        ),
        difficulty="easy",
        tags=["tail_rotor", "threshold", "constant_swap", "L8"],
    ))

    # Crystal 2b: Yaw acceleration — function_swap
    crystals.append(SniperCrystal(
        id=crystal_id("tail", "yaw_accel"),
        regime="tail_rotor_failure",
        facets={
            "ko": (
                "Compute yaw angular acceleration when tail rotor fails.\n"
                "ψ̈ = (Q_main - Q_tail) / I_z\n"
                "With Q_tail = 0 (total failure): ψ̈ = Q_main / I_z"
            ),
            "av": (
                "  Q_main: float — main rotor torque (N·m), from P / Ω\n"
                "  Q_tail: float — tail rotor torque (N·m), 0 if failed\n"
                "  I_z: float — yaw moment of inertia (kg·m²), ~10000 for UH-60\n"
                "  P = T × v_i (induced power), Ω = 2πn/60 (angular velocity)"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - Q_main derived from power: Q = P / Ω\n"
                "  - When tail rotor works: Q_tail ≈ 0.95 × Q_main\n"
                "  - yaw_accel has units rad/s² — divide torque by inertia\n"
                "  - If I_z ≈ 0, return 0 (guard against division by zero)"
            ),
            "ca": (
                "def yaw_acceleration(q_main: float, q_tail: float, i_z: float) -> float:\n"
                "    if i_z < 1e-6:\n"
                "        return 0.0\n"
                "    return (q_main - q_tail) / i_z"
            ),
            "um": (
                "def yaw_acceleration(q_main: float, q_tail: float, i_z: float) -> float:\n"
                "    if i_z < 1e-6:\n"
                "        return 0.0\n"
                "    return (q_main - q_tail) * i_z  # BUG: * instead of /"
            ),
            "dr": (
                "Location: src/crypto/flight_dynamics.py :: TailRotorState.yaw_acceleration_rads2\n"
                "Layer: L8 (Hamiltonian)\n"
                "τ = Iα means α = τ/I. Multiplying torque BY inertia gives\n"
                "a value with units N·m·kg·m² — physically meaningless and\n"
                "orders of magnitude too large."
            ),
        },
        failure_type="function_swap",
        failure_description=(
            "Multiplication instead of division: (q_main - q_tail) * i_z instead "
            "of / i_z. With typical values (q_main=5000, q_tail=0, i_z=10000), "
            "correct result is 0.5 rad/s², buggy result is 50,000,000 — off by "
            "10^8. The dimensional analysis alone catches this."
        ),
        correct_um=(
            "def yaw_acceleration(q_main: float, q_tail: float, i_z: float) -> float:\n"
            "    if i_z < 1e-6:\n"
            "        return 0.0\n"
            "    return (q_main - q_tail) / i_z"
        ),
        difficulty="easy",
        tags=["tail_rotor", "physics", "dimensional_analysis", "L8"],
    ))

    return crystals


# ---------------------------------------------------------------------------
# REGIME 3: Pacejka Tire Model
# ---------------------------------------------------------------------------

def gen_pacejka_crystals() -> List[SniperCrystal]:
    crystals = []

    # Crystal 3a: Magic Formula — order_error
    crystals.append(SniperCrystal(
        id=crystal_id("pacejka", "magic_formula"),
        regime="pacejka_tire",
        facets={
            "ko": (
                "Compute lateral tire force using Pacejka Magic Formula.\n"
                "F = D · sin(C · arctan(B·s - E·(B·s - arctan(B·s))))\n"
                "This is the standard SAE tire model for ground handling."
            ),
            "av": (
                "  B = 10.0 (stiffness factor)\n"
                "  C = 1.9 (shape factor, lateral)\n"
                "  D = μ × F_z (peak force = friction × normal load)\n"
                "  E = -0.1 (curvature factor)\n"
                "  s = slip angle (radians)"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - F(0) = 0 (no slip = no force)\n"
                "  - |F| ≤ D (peak force is the ceiling)\n"
                "  - F is odd: F(-s) = -F(s) (symmetric left/right)\n"
                "  - The inner arctan(B·s) prevents the E term from dominating"
            ),
            "ca": (
                "def pacejka_force(slip, B=10.0, C=1.9, D=17000.0, E=-0.1):\n"
                "    bs = B * slip\n"
                "    inner = bs - E * (bs - math.atan(bs))\n"
                "    return D * math.sin(C * math.atan(inner))"
            ),
            "um": (
                "def pacejka_force(slip, B=10.0, C=1.9, D=17000.0, E=-0.1):\n"
                "    bs = B * slip\n"
                "    inner = bs - E * bs - math.atan(bs)  # BUG: missing parens\n"
                "    return D * math.sin(C * math.atan(inner))"
            ),
            "dr": (
                "Location: src/crypto/flight_dynamics.py :: PacejkaTireState.lateral_force\n"
                "Layer: L8 (Hamiltonian CFI — ground-state dynamics)\n"
                "Maps to SCBE ground state (n=0, the egg). Tire grip = stability boundary.\n"
                "Slip angle = deviation from intended path."
            ),
        },
        failure_type="order_error",
        failure_description=(
            "Missing parentheses around (bs - arctan(bs)). The expression "
            "`bs - E * bs - atan(bs)` computes `(1-E)*bs - atan(bs)` instead of "
            "`bs - E*(bs - atan(bs))`. At high slip angles, this dramatically "
            "changes the force curve shape and peak location."
        ),
        correct_um=(
            "def pacejka_force(slip, B=10.0, C=1.9, D=17000.0, E=-0.1):\n"
            "    bs = B * slip\n"
            "    inner = bs - E * (bs - math.atan(bs))\n"
            "    return D * math.sin(C * math.atan(inner))"
        ),
        difficulty="hard",
        tags=["pacejka", "operator_precedence", "tire_model", "L8"],
    ))

    # Crystal 3b: Grip ratio — overflow_skip
    crystals.append(SniperCrystal(
        id=crystal_id("pacejka", "grip_ratio"),
        regime="pacejka_tire",
        facets={
            "ko": (
                "Compute how much of peak grip is being used.\n"
                "grip_ratio = |F_lateral| / D_peak\n"
                "1.0 = at peak, >1.0 shouldn't happen (cap it), <1.0 = margin."
            ),
            "av": (
                "  lateral_force: float — from Pacejka Magic Formula (N)\n"
                "  d_peak_force: float — μ × F_z (N)\n"
                "  Guard: d_peak_force can be 0 if normal load is 0 (airborne)"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - grip_ratio ∈ [0.0, 1.0] (capped)\n"
                "  - d_peak_force == 0 → return 0.0 (not Inf or NaN)\n"
                "  - is_sliding when grip_ratio > 0.95"
            ),
            "ca": (
                "def grip_ratio(lateral_force: float, d_peak: float) -> float:\n"
                "    if d_peak < 1e-6:\n"
                "        return 0.0\n"
                "    return min(1.0, abs(lateral_force) / d_peak)"
            ),
            "um": (
                "def grip_ratio(lateral_force: float, d_peak: float) -> float:\n"
                "    if d_peak < 1e-6:\n"
                "        return 0.0\n"
                "    return abs(lateral_force) / d_peak  # BUG: no min() cap"
            ),
            "dr": (
                "Location: src/crypto/flight_dynamics.py :: PacejkaTireState.grip_ratio\n"
                "Layer: L8 (ground-state dynamics)\n"
                "Without the min(1.0, ...) cap, numerical noise in the Pacejka\n"
                "formula can produce ratios slightly above 1.0, causing downstream\n"
                "code that assumes ratio ∈ [0,1] to misbehave."
            ),
        },
        failure_type="overflow_skip",
        failure_description=(
            "Missing min(1.0, ...) saturation guard. The Pacejka formula can "
            "produce |F| slightly exceeding D due to the E curvature term. "
            "Without capping, grip_ratio > 1.0 breaks is_sliding checks and "
            "any downstream code assuming [0,1] range."
        ),
        correct_um=(
            "def grip_ratio(lateral_force: float, d_peak: float) -> float:\n"
            "    if d_peak < 1e-6:\n"
            "        return 0.0\n"
            "    return min(1.0, abs(lateral_force) / d_peak)"
        ),
        difficulty="medium",
        tags=["pacejka", "overflow", "saturation", "L8"],
    ))

    return crystals


# ---------------------------------------------------------------------------
# REGIME 4: Harmonic Cost Wall — φ^(d²)
# ---------------------------------------------------------------------------

def gen_harmonic_cost_crystals() -> List[SniperCrystal]:
    crystals = []

    # Crystal 4a: harmonic_cost — constant_swap (e vs φ)
    crystals.append(SniperCrystal(
        id=crystal_id("harmonic", "phi_vs_e"),
        regime="harmonic_cost_wall",
        facets={
            "ko": (
                "Compute the harmonic cost wall: C(d) = φ^(d²)\n"
                "φ (golden ratio, 1.618...) is the specific base — not e, not 2.\n"
                "This makes adversarial deviation cost super-exponentially."
            ),
            "av": (
                "  d: float — deviation from the rail (braid distance)\n"
                "  φ = (1 + √5) / 2 ≈ 1.6180339887\n"
                "  COST_CAP = 1e6 — prevent float overflow\n"
                "  Key values:\n"
                "    d=0 → C=1.0, d=1 → C≈1.618, d=2 → C≈6.854,\n"
                "    d=3 → C≈76.01, d=4 → C≈1364"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - C(0) = 1.0 (no deviation = unit cost)\n"
                "  - C(d) > 0 for all d (always positive)\n"
                "  - C(d) monotonically increasing for d > 0\n"
                "  - C(d) = C(-d) (symmetric — d² makes it even)\n"
                "  - C(d) ≤ COST_CAP (overflow protection)"
            ),
            "ca": (
                "PHI = (1 + math.sqrt(5)) / 2\n"
                "COST_CAP = 1e6\n\n"
                "def harmonic_cost(d: float) -> float:\n"
                "    try:\n"
                "        cost = PHI ** (d * d)\n"
                "    except OverflowError:\n"
                "        return COST_CAP\n"
                "    return min(cost, COST_CAP)"
            ),
            "um": (
                "COST_CAP = 1e6\n\n"
                "def harmonic_cost(d: float) -> float:\n"
                "    try:\n"
                "        cost = math.e ** (d * d)  # BUG: e instead of φ\n"
                "    except OverflowError:\n"
                "        return COST_CAP\n"
                "    return min(cost, COST_CAP)"
            ),
            "dr": (
                "Location: src/crypto/crossing_energy.py :: harmonic_cost()\n"
                "Layer: L12 (Harmonic Wall)\n"
                "φ is the canonical base for the SCBE cost wall.\n"
                "Using e (2.718...) instead of φ (1.618...) makes the wall\n"
                "steeper — which sounds safer but breaks calibrated thresholds\n"
                "and causes false DENY decisions on legitimate inputs."
            ),
        },
        failure_type="constant_swap",
        failure_description=(
            "Base changed from φ (1.618) to e (2.718). At d=2: correct cost ≈ 6.85, "
            "buggy cost ≈ 54.60 (8× higher). At d=3: correct ≈ 76, buggy ≈ 8103 "
            "(107× higher). The steeper wall triggers DENY on inputs that should "
            "only be QUARANTINE, breaking the calibrated governance thresholds."
        ),
        correct_um=(
            "PHI = (1 + math.sqrt(5)) / 2\n"
            "COST_CAP = 1e6\n\n"
            "def harmonic_cost(d: float) -> float:\n"
            "    try:\n"
            "        cost = PHI ** (d * d)\n"
            "    except OverflowError:\n"
            "        return COST_CAP\n"
            "    return min(cost, COST_CAP)"
        ),
        difficulty="medium",
        tags=["harmonic_wall", "phi", "constant_swap", "L12"],
    ))

    # Crystal 4b: harmonic_cost_gradient — sign_flip
    crystals.append(SniperCrystal(
        id=crystal_id("harmonic", "gradient_sign"),
        regime="harmonic_cost_wall",
        facets={
            "ko": (
                "Compute the gradient of the harmonic cost wall.\n"
                "dC/dd = 2d · ln(φ) · φ^(d²)\n"
                "This is the 'restoring force' that pushes back toward the rail."
            ),
            "av": (
                "  d: float — current deviation\n"
                "  The gradient tells downstream optimizers how fast cost is rising.\n"
                "  At d=0: gradient = 0 (at the rail, no restoring force)\n"
                "  At d>0: gradient > 0 (positive — cost increasing with d)\n"
                "  At d<0: gradient < 0 (negative — cost increasing with |d|)"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - gradient(0) = 0 (saddle point at the rail)\n"
                "  - sign(gradient) = sign(d) (restoring force opposes deviation)\n"
                "  - |gradient| monotonically increasing with |d|\n"
                "  - gradient = 2d × ln(φ) × C(d)"
            ),
            "ca": (
                "def harmonic_cost_gradient(d: float) -> float:\n"
                "    if abs(d) < 1e-12:\n"
                "        return 0.0\n"
                "    return 2.0 * d * math.log(PHI) * harmonic_cost(d)"
            ),
            "um": (
                "def harmonic_cost_gradient(d: float) -> float:\n"
                "    if abs(d) < 1e-12:\n"
                "        return 0.0\n"
                "    return -2.0 * d * math.log(PHI) * harmonic_cost(d)  # BUG: negated"
            ),
            "dr": (
                "Location: src/crypto/crossing_energy.py :: harmonic_cost_gradient()\n"
                "Layer: L12 (Harmonic Wall)\n"
                "Negating the gradient reverses the restoring force direction.\n"
                "Instead of pushing TOWARD the rail, it pushes AWAY — making\n"
                "adversarial deviation self-reinforcing instead of self-correcting."
            ),
        },
        failure_type="sign_flip",
        failure_description=(
            "Leading coefficient negated: -2.0 instead of 2.0. This reverses the "
            "restoring force. At d=1: correct gradient ≈ +1.56 (pushes back toward "
            "rail), buggy gradient ≈ -1.56 (pushes AWAY from rail). The system "
            "becomes unstable — any deviation amplifies itself."
        ),
        correct_um=(
            "def harmonic_cost_gradient(d: float) -> float:\n"
            "    if abs(d) < 1e-12:\n"
            "        return 0.0\n"
            "    return 2.0 * d * math.log(PHI) * harmonic_cost(d)"
        ),
        difficulty="medium",
        tags=["harmonic_wall", "gradient", "sign_flip", "stability", "L12"],
    ))

    return crystals


# ---------------------------------------------------------------------------
# REGIME 5: Dual Ternary Crossing
# ---------------------------------------------------------------------------

def gen_crossing_crystals() -> List[SniperCrystal]:
    crystals = []

    # Crystal 5a: Energy function — order_error
    crystals.append(SniperCrystal(
        id=crystal_id("crossing", "energy_formula"),
        regime="dual_ternary_crossing",
        facets={
            "ko": (
                "Compute dual ternary energy: E(p, m) = p² + m² + p·m\n"
                "This measures structural tension at a braid crossing point.\n"
                "p = primary channel, m = mirror channel, both in {-1, 0, +1}."
            ),
            "av": (
                "  Energy landscape (all 9 states):\n"
                "    E(0,0) = 0 — equilibrium (minimum)\n"
                "    E(1,1) = 3 — constructive resonance (maximum)\n"
                "    E(-1,-1) = 1 — negative resonance\n"
                "    E(1,-1) = 1 — destructive interference\n"
                "    E(0,1) = E(1,0) = 1 — single-axis excitation"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - E(p,m) ≥ 0 for all valid (p,m) in {-1,0,+1}²\n"
                "  - E(0,0) = 0 (unique minimum)\n"
                "  - E(p,m) = E(m,p) (symmetric in p and m)\n"
                "  - E(-p,-m) = E(p,m) (invariant under joint negation)\n"
                "  - Maximum E = 3 at (1,1) and (-1,-1)... wait, E(-1,-1) = 1+1+1 = 3? No: (-1)²+(-1)²+(-1)(-1) = 1+1+1 = 3"
            ),
            "ca": (
                "def dual_ternary_energy(p: int, m: int) -> float:\n"
                "    return float(p * p + m * m + p * m)"
            ),
            "um": (
                "def dual_ternary_energy(p: int, m: int) -> float:\n"
                "    return float(p * p + m * m + p + m)  # BUG: p+m not p*m"
            ),
            "dr": (
                "Location: src/crypto/crossing_energy.py :: DualTernaryPair.energy\n"
                "Layer: L8 (Hamiltonian CFI)\n"
                "The p·m cross-term creates the constructive/destructive interference.\n"
                "Replacing it with p+m breaks symmetry: E(1,-1)=1+1+0=2 ≠ E(-1,1)=1+1+0=2\n"
                "(accidentally still symmetric here but E values are all wrong)."
            ),
        },
        failure_type="function_swap",
        failure_description=(
            "Cross-term p*m replaced with p+m. The energy landscape shifts: "
            "E(1,1) goes from 3 to 4, E(0,0) stays 0, E(1,-1) goes from 1 to 2, "
            "E(1,0) goes from 1 to 2. This changes governance thresholds — states "
            "that should be ALLOW become QUARANTINE."
        ),
        correct_um=(
            "def dual_ternary_energy(p: int, m: int) -> float:\n"
            "    return float(p * p + m * m + p * m)"
        ),
        difficulty="medium",
        tags=["crossing", "energy", "formula_swap", "L8"],
    ))

    # Crystal 5b: Valid transition — boundary_miss
    crystals.append(SniperCrystal(
        id=crystal_id("crossing", "topology"),
        regime="dual_ternary_crossing",
        facets={
            "ko": (
                "Check if a transition between two dual ternary states is\n"
                "topologically valid. Valid iff Chebyshev distance ≤ 1.\n"
                "Each trit can change by at most 1 step per timestep."
            ),
            "av": (
                "  s1, s2: DualTernaryPair — consecutive states\n"
                "  Chebyshev distance = max(|Δp|, |Δm|) in {-1,0,+1}² grid\n"
                "  Valid if both |s1.p - s2.p| ≤ 1 AND |s1.m - s2.m| ≤ 1"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - valid_transition(s, s) = True (staying is always valid)\n"
                "  - (0,0) → (1,1) is valid (diagonal move, Chebyshev = 1)\n"
                "  - (1,1) → (-1,-1) is INVALID (Chebyshev = 2)\n"
                "  - Transition graph is undirected: valid(a,b) = valid(b,a)"
            ),
            "ca": (
                "def valid_transition(s1, s2) -> bool:\n"
                "    return abs(s1.primary - s2.primary) <= 1 and \\\n"
                "           abs(s1.mirror - s2.mirror) <= 1"
            ),
            "um": (
                "def valid_transition(s1, s2) -> bool:\n"
                "    return abs(s1.primary - s2.primary) <= 1 or \\\n"
                "           abs(s1.mirror - s2.mirror) <= 1  # BUG: or instead of and"
            ),
            "dr": (
                "Location: src/crypto/crossing_energy.py :: valid_transition()\n"
                "Layer: L8 (Hamiltonian CFI — topology preservation)\n"
                "Using OR instead of AND allows transitions where one axis jumps\n"
                "by 2 as long as the other axis stays close. This breaks the\n"
                "Chebyshev metric — (1,1)→(-1,1) would be 'valid' even though\n"
                "the primary axis jumped by 2."
            ),
        },
        failure_type="boundary_miss",
        failure_description=(
            "AND changed to OR in the Chebyshev check. The transition (1,1)→(-1,0) "
            "has |Δp|=2, |Δm|=1. With AND: invalid (correct). With OR: valid (wrong), "
            "because |Δm|=1 satisfies the OR. This allows teleportation across the "
            "trit grid, breaking causal topology."
        ),
        correct_um=(
            "def valid_transition(s1, s2) -> bool:\n"
            "    return abs(s1.primary - s2.primary) <= 1 and \\\n"
            "           abs(s1.mirror - s2.mirror) <= 1"
        ),
        difficulty="hard",
        tags=["crossing", "topology", "boolean_logic", "L8"],
    ))

    # Crystal 5c: Governance routing — threshold order
    crystals.append(SniperCrystal(
        id=crystal_id("crossing", "routing"),
        regime="dual_ternary_crossing",
        facets={
            "ko": (
                "Route a crossing to ALLOW / QUARANTINE / DENY based on energy,\n"
                "harmonic cost, and topology validity.\n"
                "Invalid topology → always DENY (braid break)."
            ),
            "av": (
                "  energy: float — E(p,m) structural tension\n"
                "  cost: float — C(d) harmonic wall cost\n"
                "  topology_valid: bool — Chebyshev check passed\n"
                "  QUARANTINE_THRESHOLD = 2.0\n"
                "  DENY_THRESHOLD = 5.0\n"
                "  total_score = energy × cost"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - topology_valid=False → DENY (always, regardless of score)\n"
                "  - total_score < 2.0 → ALLOW\n"
                "  - 2.0 ≤ total_score < 5.0 → QUARANTINE\n"
                "  - total_score ≥ 5.0 → DENY\n"
                "  - Decision severity: ALLOW < QUARANTINE < DENY (monotonic)"
            ),
            "ca": (
                "def route_decision(energy, cost, topology_valid):\n"
                "    if not topology_valid:\n"
                "        return 'DENY'\n"
                "    total = energy * cost\n"
                "    if total >= 5.0:\n"
                "        return 'DENY'\n"
                "    elif total >= 2.0:\n"
                "        return 'QUARANTINE'\n"
                "    else:\n"
                "        return 'ALLOW'"
            ),
            "um": (
                "def route_decision(energy, cost, topology_valid):\n"
                "    if not topology_valid:\n"
                "        return 'DENY'\n"
                "    total = energy * cost\n"
                "    if total >= 2.0:        # BUG: thresholds swapped\n"
                "        return 'DENY'\n"
                "    elif total >= 5.0:\n"
                "        return 'QUARANTINE'\n"
                "    else:\n"
                "        return 'ALLOW'"
            ),
            "dr": (
                "Location: src/crypto/crossing_energy.py :: _route_decision()\n"
                "Layer: L13 (Risk Decision / Swarm Governance)\n"
                "With thresholds swapped, any score ≥ 2.0 gets DENY (the first\n"
                "branch always wins). QUARANTINE is unreachable — the elif for\n"
                "≥ 5.0 can never trigger because ≥ 2.0 catches everything first.\n"
                "This creates a binary ALLOW/DENY system with no middle ground."
            ),
        },
        failure_type="order_error",
        failure_description=(
            "Threshold checks are in wrong order: checks ≥2.0 before ≥5.0. Since "
            "any score ≥5.0 is also ≥2.0, the first branch catches everything. "
            "QUARANTINE becomes unreachable dead code. Scores 2.0–4.99 that should "
            "be QUARANTINE are incorrectly DENIED."
        ),
        correct_um=(
            "def route_decision(energy, cost, topology_valid):\n"
            "    if not topology_valid:\n"
            "        return 'DENY'\n"
            "    total = energy * cost\n"
            "    if total >= 5.0:\n"
            "        return 'DENY'\n"
            "    elif total >= 2.0:\n"
            "        return 'QUARANTINE'\n"
            "    else:\n"
            "        return 'ALLOW'"
        ),
        difficulty="medium",
        tags=["crossing", "governance", "threshold_order", "L13", "dead_code"],
    ))

    return crystals


# ---------------------------------------------------------------------------
# REGIME 6: Lift / Stall Boundary
# ---------------------------------------------------------------------------

def gen_stall_crystals() -> List[SniperCrystal]:
    crystals = []

    # Crystal 6a: Lift coefficient — function_swap (sin vs cos)
    crystals.append(SniperCrystal(
        id=crystal_id("stall", "cl_function"),
        regime="lift_stall_boundary",
        facets={
            "ko": (
                "Compute lift coefficient C_L as function of angle of attack.\n"
                "Pre-stall: thin airfoil theory gives C_L = 2π·sin(α).\n"
                "Post-stall: C_L drops exponentially with separated flow."
            ),
            "av": (
                "  alpha_rad: float — angle of attack in radians\n"
                "  ALPHA_CRIT = 15° (0.2618 rad) — stall angle\n"
                "  Pre-stall: C_L = 2π·sin(α)\n"
                "  Post-stall: C_L = C_L_max · exp(-2·(|α| - α_crit))"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - C_L(0) = 0 (no AoA = no lift)\n"
                "  - C_L continuous at α_crit (no jump)\n"
                "  - C_L_max ≈ 2π·sin(15°) ≈ 1.63\n"
                "  - Post-stall: C_L monotonically decreasing\n"
                "  - Pre-stall: C_L monotonically increasing"
            ),
            "ca": (
                "ALPHA_CRIT = math.radians(15.0)\n\n"
                "def lift_coefficient(alpha_rad: float) -> float:\n"
                "    if abs(alpha_rad) <= ALPHA_CRIT:\n"
                "        return 2 * math.pi * math.sin(alpha_rad)\n"
                "    else:\n"
                "        sign = 1 if alpha_rad > 0 else -1\n"
                "        cl_max = 2 * math.pi * math.sin(ALPHA_CRIT)\n"
                "        overshoot = abs(alpha_rad) - ALPHA_CRIT\n"
                "        return sign * cl_max * math.exp(-2.0 * overshoot)"
            ),
            "um": (
                "ALPHA_CRIT = math.radians(15.0)\n\n"
                "def lift_coefficient(alpha_rad: float) -> float:\n"
                "    if abs(alpha_rad) <= ALPHA_CRIT:\n"
                "        return 2 * math.pi * math.cos(alpha_rad)  # BUG: cos not sin\n"
                "    else:\n"
                "        sign = 1 if alpha_rad > 0 else -1\n"
                "        cl_max = 2 * math.pi * math.sin(ALPHA_CRIT)\n"
                "        overshoot = abs(alpha_rad) - ALPHA_CRIT\n"
                "        return sign * cl_max * math.exp(-2.0 * overshoot)"
            ),
            "dr": (
                "Location: src/crypto/flight_dynamics.py :: lift_coefficient()\n"
                "Layer: L8 (Hamiltonian CFI)\n"
                "cos(0) = 1 ≠ sin(0) = 0. Using cos means C_L(0) ≈ 6.28 instead\n"
                "of 0. The aircraft would appear to have maximum lift at zero AoA,\n"
                "breaking all energy-state calculations downstream."
            ),
        },
        failure_type="function_swap",
        failure_description=(
            "math.sin replaced with math.cos in pre-stall regime. At α=0: sin(0)=0 "
            "but cos(0)=1, so C_L(0)=6.28 instead of 0. The lift curve is inverted — "
            "maximum lift at zero AoA, decreasing toward stall. This violates the "
            "fundamental C_L(0)=0 invariant."
        ),
        correct_um=(
            "def lift_coefficient(alpha_rad: float) -> float:\n"
            "    if abs(alpha_rad) <= ALPHA_CRIT:\n"
            "        return 2 * math.pi * math.sin(alpha_rad)\n"
            "    else:\n"
            "        sign = 1 if alpha_rad > 0 else -1\n"
            "        cl_max = 2 * math.pi * math.sin(ALPHA_CRIT)\n"
            "        overshoot = abs(alpha_rad) - ALPHA_CRIT\n"
            "        return sign * cl_max * math.exp(-2.0 * overshoot)"
        ),
        difficulty="easy",
        tags=["aerodynamics", "trig_swap", "invariant_violation", "L8"],
    ))

    return crystals


# ---------------------------------------------------------------------------
# REGIME 7: Dead Tone Gallery
# ---------------------------------------------------------------------------

def gen_gallery_crystals() -> List[SniperCrystal]:
    crystals = []

    # Crystal 7a: Dead tone proximity — constant_swap
    crystals.append(SniperCrystal(
        id=crystal_id("gallery", "dead_tone_ratio"),
        regime="dead_tone_gallery",
        facets={
            "ko": (
                "Check how close a frequency ratio is to the three 'dead tones' —\n"
                "musical intervals unreachable by single-tongue phi geometry:\n"
                "  Perfect fifth: 3/2 = 1.500\n"
                "  Minor sixth:   8/5 = 1.600\n"
                "  Minor seventh: 16/9 ≈ 1.778"
            ),
            "av": (
                "  observed_ratio: float — the cross-axis interference ratio\n"
                "  DEAD_TONE_FIFTH = 3/2 = 1.500\n"
                "  DEAD_TONE_SIXTH = 8/5 = 1.600\n"
                "  DEAD_TONE_SEVENTH = 16/9 ≈ 1.778\n"
                "  proximity = 1.0 - |observed - target| (closer = higher)"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - proximity ∈ [0, 1] (clamped)\n"
                "  - proximity(target, target) = 1.0 (exact match = max)\n"
                "  - The minor sixth (1.600) is closest to φ (1.618) — only 0.018 gap\n"
                "  - This makes it the most dangerous blind spot (adversarial sweet spot)"
            ),
            "ca": (
                "DEAD_TONE_FIFTH = 3.0 / 2.0    # 1.500\n"
                "DEAD_TONE_SIXTH = 8.0 / 5.0     # 1.600\n"
                "DEAD_TONE_SEVENTH = 16.0 / 9.0  # 1.778\n\n"
                "def dead_tone_proximity(observed: float, target: float) -> float:\n"
                "    return max(0.0, 1.0 - abs(observed - target))"
            ),
            "um": (
                "DEAD_TONE_FIFTH = 3.0 / 2.0    # 1.500\n"
                "DEAD_TONE_SIXTH = 5.0 / 3.0     # BUG: 1.667 not 1.600\n"
                "DEAD_TONE_SEVENTH = 16.0 / 9.0  # 1.778\n\n"
                "def dead_tone_proximity(observed: float, target: float) -> float:\n"
                "    return max(0.0, 1.0 - abs(observed - target))"
            ),
            "dr": (
                "Location: src/crypto/quantum_frequency_bundle.py :: DEAD_TONE_SIXTH\n"
                "Layer: L9 (Spectral Coherence) + L10 (Spin Coherence)\n"
                "The minor sixth is 8/5 = 1.600, NOT 5/3 ≈ 1.667 (which is\n"
                "the major sixth). The minor sixth is special because it's\n"
                "only 0.018 from phi — the adversarial sweet spot where\n"
                "near-miss attacks look almost like phi-geometry."
            ),
        },
        failure_type="constant_swap",
        failure_description=(
            "DEAD_TONE_SIXTH changed from 8/5 (1.600) to 5/3 (1.667). The minor "
            "sixth IS the critical blind spot because it's 0.018 from phi. The "
            "major sixth (1.667) is 0.049 from phi — less dangerous. Using the "
            "wrong ratio moves the detection window away from the actual threat."
        ),
        correct_um=(
            "DEAD_TONE_FIFTH = 3.0 / 2.0\n"
            "DEAD_TONE_SIXTH = 8.0 / 5.0     # 1.600 — NOT 5/3\n"
            "DEAD_TONE_SEVENTH = 16.0 / 9.0"
        ),
        difficulty="expert",
        tags=["gallery", "dead_tone", "music_theory", "constant", "L9", "L10"],
    ))

    return crystals


# ---------------------------------------------------------------------------
# REGIME 8: Phase Deviation
# ---------------------------------------------------------------------------

def gen_phase_crystals() -> List[SniperCrystal]:
    crystals = []

    # Crystal 8a: phase_deviation — boundary_miss (normalization)
    crystals.append(SniperCrystal(
        id=crystal_id("phase", "deviation_norm"),
        regime="phase_deviation",
        facets={
            "ko": (
                "Compute phase deviation between current and expected dual ternary state.\n"
                "Returns a value in [0, 1] where 0 = perfect match, 1 = maximum deviation."
            ),
            "av": (
                "  current: DualTernaryPair — observed state (p, m) in {-1, 0, +1}\n"
                "  expected: DualTernaryPair — target state\n"
                "  dp = |current.p - expected.p| ∈ {0, 1, 2}\n"
                "  dq = |current.m - expected.m| ∈ {0, 1, 2}\n"
                "  Maximum possible deviation: max(dp, dq) = 2\n"
                "  Normalized: max(dp, dq) / 2.0"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - phase_deviation(s, s) = 0.0 (same state = no deviation)\n"
                "  - phase_deviation in [0.0, 1.0]\n"
                "  - phase_deviation((1,1), (-1,-1)) = 1.0 (max distance)\n"
                "  - phase_deviation is a metric (symmetric, triangle inequality)"
            ),
            "ca": (
                "def phase_deviation(current, expected) -> float:\n"
                "    dp = abs(current.primary - expected.primary)\n"
                "    dq = abs(current.mirror - expected.mirror)\n"
                "    return max(dp, dq) / 2.0"
            ),
            "um": (
                "def phase_deviation(current, expected) -> float:\n"
                "    dp = abs(current.primary - expected.primary)\n"
                "    dq = abs(current.mirror - expected.mirror)\n"
                "    return max(dp, dq) / 3.0  # BUG: /3 instead of /2"
            ),
            "dr": (
                "Location: src/crypto/crossing_energy.py :: phase_deviation()\n"
                "Layer: L8 (Hamiltonian CFI)\n"
                "Dividing by 3 instead of 2 compresses the output to [0, 0.667].\n"
                "Maximum deviation is NEVER 1.0, which breaks the braid distance\n"
                "calculation in _compute_braid_distance() where λ·phase_dev\n"
                "assumes [0,1] range."
            ),
        },
        failure_type="boundary_miss",
        failure_description=(
            "Normalization denominator is 3 instead of 2. Max possible dp or dq "
            "is 2 (from +1 to -1), so max(dp,dq)/2 gives [0,1]. With /3, the "
            "output range is [0, 0.667]. The braid distance formula downstream "
            "expects [0,1], so all phase contributions are scaled down by 1/3."
        ),
        correct_um=(
            "def phase_deviation(current, expected) -> float:\n"
            "    dp = abs(current.primary - expected.primary)\n"
            "    dq = abs(current.mirror - expected.mirror)\n"
            "    return max(dp, dq) / 2.0"
        ),
        difficulty="hard",
        tags=["phase", "normalization", "range_error", "L8"],
    ))

    return crystals


# ---------------------------------------------------------------------------
# REGIME 9: ISA Atmosphere Model
# ---------------------------------------------------------------------------

def gen_atmosphere_crystals() -> List[SniperCrystal]:
    crystals = []

    # Crystal 9a: ISA density — constant_swap (lapse rate sign)
    crystals.append(SniperCrystal(
        id=crystal_id("isa", "lapse_rate"),
        regime="isa_atmosphere",
        facets={
            "ko": (
                "Compute air density at altitude using the International Standard\n"
                "Atmosphere (ISA) troposphere model.\n"
                "Temperature decreases with altitude: T(h) = T₀ + L·h where L = -0.0065 K/m."
            ),
            "av": (
                "  altitude_m: float — altitude above MSL (meters)\n"
                "  T₀ = 288.15 K (15°C at sea level)\n"
                "  L = -0.0065 K/m (temperature lapse rate — negative = cooling)\n"
                "  ρ₀ = 1.225 kg/m³ (sea level density)\n"
                "  g = 9.80665 m/s², R = 287.058 J/(kg·K)\n"
                "  Valid up to 11 km (tropopause)"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - isa_density(0) = 1.225 kg/m³ (sea level)\n"
                "  - density monotonically decreasing with altitude\n"
                "  - isa_density(11000) ≈ 0.365 kg/m³\n"
                "  - density always positive\n"
                "  - Capped at tropopause (11 km)"
            ),
            "ca": (
                "def isa_density(altitude_m: float) -> float:\n"
                "    lapse_rate = -0.0065  # K/m (negative = cooling)\n"
                "    if altitude_m > 11000:\n"
                "        altitude_m = 11000\n"
                "    temp = 288.15 + lapse_rate * altitude_m\n"
                "    exponent = (9.80665 / (-lapse_rate * 287.058)) - 1\n"
                "    return 1.225 * (temp / 288.15) ** exponent"
            ),
            "um": (
                "def isa_density(altitude_m: float) -> float:\n"
                "    lapse_rate = 0.0065  # BUG: positive (warming with altitude)\n"
                "    if altitude_m > 11000:\n"
                "        altitude_m = 11000\n"
                "    temp = 288.15 + lapse_rate * altitude_m\n"
                "    exponent = (9.80665 / (-lapse_rate * 287.058)) - 1\n"
                "    return 1.225 * (temp / 288.15) ** exponent"
            ),
            "dr": (
                "Location: src/crypto/flight_dynamics.py :: isa_density()\n"
                "Layer: L8 (Hamiltonian CFI — atmosphere model)\n"
                "Positive lapse rate means temperature INCREASES with altitude,\n"
                "giving a temperature inversion. This makes density INCREASE with\n"
                "altitude and the exponent computation uses -lapse_rate which\n"
                "becomes negative, producing complex/negative densities."
            ),
        },
        failure_type="sign_flip",
        failure_description=(
            "Lapse rate sign flipped from -0.0065 to +0.0065. Temperature now "
            "increases with altitude (impossible in troposphere). At 5000m: "
            "correct temp ≈ 255.65 K, buggy temp ≈ 320.65 K. The exponent "
            "computation (-lapse_rate * R) becomes negative, producing density "
            "values that increase with altitude — physically meaningless."
        ),
        correct_um=(
            "def isa_density(altitude_m: float) -> float:\n"
            "    lapse_rate = -0.0065  # K/m (MUST be negative)\n"
            "    if altitude_m > 11000:\n"
            "        altitude_m = 11000\n"
            "    temp = 288.15 + lapse_rate * altitude_m\n"
            "    exponent = (9.80665 / (-lapse_rate * 287.058)) - 1\n"
            "    return 1.225 * (temp / 288.15) ** exponent"
        ),
        difficulty="medium",
        tags=["atmosphere", "physics", "sign_flip", "L8"],
    ))

    return crystals


# ---------------------------------------------------------------------------
# REGIME 10: Braid Distance Composition
# ---------------------------------------------------------------------------

def gen_braid_distance_crystals() -> List[SniperCrystal]:
    crystals = []

    # Crystal 10a: Braid distance — order_error
    crystals.append(SniperCrystal(
        id=crystal_id("braid", "distance_composition"),
        regime="braid_distance",
        facets={
            "ko": (
                "Compute braid distance incorporating both energy and phase.\n"
                "d_braid = √E(p,m) + λ · phase_deviation\n"
                "Uses sqrt of energy as spatial component plus weighted phase."
            ),
            "av": (
                "  current: DualTernaryPair — observed state\n"
                "  expected: DualTernaryPair — target state\n"
                "  lambda_phase: float = 0.5 — weight for phase component\n"
                "  E(p,m): energy from current state\n"
                "  phase_dev: phase deviation in [0, 1]"
            ),
            "ru": (
                "INVARIANTS:\n"
                "  - d_braid ≥ 0 (distance is non-negative)\n"
                "  - d_braid(equilibrium, equilibrium) = 0 (E=0, phase_dev=0)\n"
                "  - sqrt(E) is used because E is already quadratic\n"
                "  - d_braid feeds into harmonic_cost(d) = φ^(d²)"
            ),
            "ca": (
                "def compute_braid_distance(current, expected, lambda_phase=0.5):\n"
                "    spatial = math.sqrt(current.energy)\n"
                "    phase_dev = phase_deviation(current, expected)\n"
                "    return spatial + lambda_phase * phase_dev"
            ),
            "um": (
                "def compute_braid_distance(current, expected, lambda_phase=0.5):\n"
                "    spatial = current.energy  # BUG: missing sqrt\n"
                "    phase_dev = phase_deviation(current, expected)\n"
                "    return spatial + lambda_phase * phase_dev"
            ),
            "dr": (
                "Location: src/crypto/crossing_energy.py :: _compute_braid_distance()\n"
                "Layer: L8 (Hamiltonian CFI) → L12 (Harmonic Wall)\n"
                "Without sqrt, E(1,1)=3 stays 3 instead of √3≈1.73.\n"
                "Since this feeds into φ^(d²), the cost at (1,1) goes from\n"
                "φ^(1.73²)=φ^(3)≈4.236 to φ^(3²)=φ^(9)≈76.01 — 18× higher.\n"
                "This massively over-penalizes constructive resonance states."
            ),
        },
        failure_type="function_swap",
        failure_description=(
            "math.sqrt() omitted — using raw energy instead of square root. "
            "Energy E is already quadratic (p²+m²+p·m), so using E directly "
            "instead of √E makes the braid distance quartic in the underlying "
            "trit values. The harmonic cost φ^(d²) then becomes φ^(E²) — a "
            "super-exponential that DENY-routes almost everything."
        ),
        correct_um=(
            "def compute_braid_distance(current, expected, lambda_phase=0.5):\n"
            "    spatial = math.sqrt(current.energy)\n"
            "    phase_dev = phase_deviation(current, expected)\n"
            "    return spatial + lambda_phase * phase_dev"
        ),
        difficulty="hard",
        tags=["braid", "distance", "missing_sqrt", "L8", "L12"],
    ))

    return crystals


# ---------------------------------------------------------------------------
# Assembly and Output
# ---------------------------------------------------------------------------

def generate_all_crystals() -> List[SniperCrystal]:
    """Generate all sniper crystals across all regimes."""
    all_crystals = []
    generators = [
        gen_vrs_crystals,
        gen_tail_rotor_crystals,
        gen_pacejka_crystals,
        gen_harmonic_cost_crystals,
        gen_crossing_crystals,
        gen_stall_crystals,
        gen_gallery_crystals,
        gen_phase_crystals,
        gen_atmosphere_crystals,
        gen_braid_distance_crystals,
    ]
    for gen in generators:
        all_crystals.extend(gen())
    return all_crystals


def generate_kaleidoscope_variants(crystals: List[SniperCrystal], n_perms: int = 5) -> List[Dict]:
    """Generate tongue-swap variants for invariance testing.

    Uses a strategic subset of 6! = 720 permutations:
    - Identity (original order)
    - Reverse
    - UM↔CA swap (failure moves to implementation position)
    - KO↔DR swap (intent↔structure swap)
    - Random additional permutations
    """
    records = []
    # Strategic permutations
    strategic = [
        tuple(TONGUE_ORDER),                              # identity
        tuple(reversed(TONGUE_ORDER)),                    # reverse
        ("ko", "av", "ru", "um", "ca", "dr"),             # UM↔CA swap
        ("dr", "av", "ru", "ca", "um", "ko"),             # KO↔DR swap
        ("um", "dr", "ko", "av", "ru", "ca"),             # UM to front
    ]

    for crystal in crystals:
        for perm in strategic[:n_perms]:
            records.append(crystal.to_kaleidoscope(perm))

    return records


def generate_ablation_variants(crystals: List[SniperCrystal]) -> List[Dict]:
    """Generate 5-tongue variants with each tongue removed."""
    records = []
    for crystal in crystals:
        for tongue in TONGUE_ORDER:
            records.append(crystal.to_ablation(tongue))
    return records


def generate_dpo_pairs(crystals: List[SniperCrystal]) -> List[Dict]:
    """Generate DPO preference pairs."""
    return [c.to_dpo_pair() for c in crystals]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    random.seed(42)  # Reproducible

    out_dir = Path(__file__).resolve().parents[1] / "training-data" / "sft"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate base crystals
    crystals = generate_all_crystals()
    print(f"Generated {len(crystals)} base crystals across {len(set(c.regime for c in crystals))} regimes")

    # Regime breakdown
    regime_counts = {}
    for c in crystals:
        regime_counts[c.regime] = regime_counts.get(c.regime, 0) + 1
    for regime, count in sorted(regime_counts.items()):
        print(f"  {regime}: {count}")

    # Difficulty breakdown
    diff_counts = {}
    for c in crystals:
        diff_counts[c.difficulty] = diff_counts.get(c.difficulty, 0) + 1
    for diff, count in sorted(diff_counts.items()):
        print(f"  [{diff}]: {count}")

    # Failure type breakdown
    fail_counts = {}
    for c in crystals:
        fail_counts[c.failure_type] = fail_counts.get(c.failure_type, 0) + 1
    for ft, count in sorted(fail_counts.items()):
        print(f"  {ft}: {count}")

    # Generate SFT records
    sft_records = [c.to_sft_record() for c in crystals]

    # Generate augmentation variants
    kaleido_records = generate_kaleidoscope_variants(crystals, n_perms=5)
    ablation_records = generate_ablation_variants(crystals)
    dpo_records = generate_dpo_pairs(crystals)

    print(f"\nAugmentation:")
    print(f"  Kaleidoscope variants: {len(kaleido_records)}")
    print(f"  Ablation variants:     {len(ablation_records)}")
    print(f"  DPO pairs:             {len(dpo_records)}")
    print(f"  Total records:         {len(sft_records) + len(kaleido_records) + len(ablation_records)}")

    # Write SFT file
    sft_path = out_dir / "sniper_crystals_v1.jsonl"
    all_sft = sft_records + kaleido_records + ablation_records
    with open(sft_path, "w", encoding="utf-8") as f:
        for rec in all_sft:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\nSFT: {sft_path} ({len(all_sft)} records)")

    # Write DPO file
    dpo_path = out_dir / "sniper_crystals_dpo_v1.jsonl"
    with open(dpo_path, "w", encoding="utf-8") as f:
        for rec in dpo_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"DPO: {dpo_path} ({len(dpo_records)} records)")

    # Stats summary
    print(f"\n{'='*60}")
    print(f"SNIPER CRYSTAL GENERATOR v1.0")
    print(f"{'='*60}")
    print(f"Base crystals:       {len(crystals)}")
    print(f"SFT records:         {len(all_sft)}")
    print(f"DPO pairs:           {len(dpo_records)}")
    print(f"Regimes:             {len(regime_counts)}")
    print(f"Failure types:       {len(fail_counts)}")
    print(f"Difficulty spread:   {dict(sorted(diff_counts.items()))}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
