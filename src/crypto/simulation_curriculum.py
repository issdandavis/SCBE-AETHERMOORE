"""
Simulation Curriculum — Progressive 6-Level Training from Egg to Expert
=======================================================================

Fuses three independent physics engines into one unified curriculum:

    quantum_frequency_bundle.py → QHO states + visual + acoustic + governance
    flight_dynamics.py          → 6-DOF + rotor + VRS + recovery paths
    code_lattice.py             → coding patterns + anti-patterns ("swear words")

The AI learns in 6 progressive levels, exactly like a pilot moves from
basic hover to full VRS recovery in a real simulator:

    Level 0: Raw Observation (Ground State — The Egg)
        QHO n=0, no forks, no swear words, no VRS.
        Text → tongue frequency assignment. First taste of spell casting.

    Level 1: Single Excitation + Frequency Tagging (Low-n Stable)
        QHO n=1-2, visual shimmer + acoustic bands, clean airflow.
        First taste of spell casting as frequency control.

    Level 2: Boundary Detection + Polymorphic Forks (Monty Hall Gain)
        Forks appear, gain > 0, first swear words flagged.
        Rotor approaching VRS margin. Boundary = richest information.

    Level 3: QHO Excitation + VRS Entry (High-n Unstable)
        QHO n≥4, VRS onset, lift collapse, violent buffeting.
        Model must detect VRS, flag swear words, rank recovery paths.

    Level 4: Multi-Path Recovery + Code Lattice (Full Recovery)
        Real recovery paths (standard, Vuichard, autorotation).
        Cross-domain mappings: VRS → graceful error handling.

    Level 5: Full Lattice Generalization (Expert Level)
        Complete closed-loop: QHO → rotor → VRS → recovery → clean airflow.
        Physics = magic = code. Intent compounding at maximum.

Each level compounds system intent (physics + governance) with learner
intent (text semantics) — the QHO creation/annihilation mechanism.
Repetition is scaffolding. The lattice is the goal.

Wires into:
    - quantum_frequency_bundle.py: QHO + visual + acoustic
    - flight_dynamics.py: 6-DOF + VRS + recovery
    - code_lattice.py: anti-patterns + compound intent
    - qho_bundle.py: curriculum_difficulty baseline

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.crypto.quantum_frequency_bundle import (
    QuantumFrequencyBundle,
    generate_quantum_bundle,
    TONGUE_ORDER,
)
from src.crypto.flight_dynamics import (
    FlightDynamicsState,
    RecoveryPath,
    qho_to_flight_state,
)
from src.crypto.code_lattice import (
    CodeLatticeBundle,
    generate_code_lattice_bundle,
)
from src.crypto.physics_domains import (
    PhysicsDomainState,
    compute_physics_domain_state,
    flatten_physics_domain_for_sft,
    PHYSICS_FIELDS,
    COUPLING_CHANNELS,
    required_recovery_fields,
)
from src.crypto.tri_bundle import PHI

# ---------------------------------------------------------------------------
# Curriculum Level Classification
# ---------------------------------------------------------------------------

# Level boundaries (curriculum_difficulty ranges)
LEVEL_BOUNDARIES = {
    0: (0.0, 0.2),  # Ground State — The Egg
    1: (0.2, 0.4),  # Single Excitation
    2: (0.4, 0.6),  # Boundary Detection
    3: (0.6, 0.8),  # VRS Entry
    4: (0.8, 0.95),  # Multi-Path Recovery
    5: (0.95, 1.0),  # Full Lattice Generalization
}

LEVEL_NAMES = {
    0: "Raw Observation (Ground State — The Egg)",
    1: "Single Excitation + Frequency Tagging",
    2: "Boundary Detection + Polymorphic Forks",
    3: "QHO Excitation + VRS Entry",
    4: "Multi-Path Recovery + Code Lattice",
    5: "Full Lattice Generalization",
}

LEVEL_DESCRIPTIONS = {
    0: "QHO n=0, no forks, no swear words. Basic text → tongue assignment.",
    1: "QHO n=1-2, visual shimmer + acoustic bands. Frequency control begins.",
    2: "Forks appear, Monty Hall gain active, first swear words. Boundary = information.",
    3: "QHO n≥4, VRS onset, high severity swear words. Danger zone detection.",
    4: "Real recovery paths ranked. Cross-domain: VRS → error handling in code.",
    5: "Complete closed-loop. Physics = magic = code. Maximum intent compounding.",
}


def classify_curriculum_level(
    qho_max_n: int,
    has_forks: bool,
    monty_hall_gain: float,
    swear_word_count: int,
    in_vrs: bool,
    has_recovery_paths: bool,
    compound_intent: float,
) -> int:
    """Classify a bundle into curriculum level 0-5.

    Uses the actual physics state, not just a difficulty score.
    Each level has hard prerequisites — you can't reach Level 3
    without having the QHO excitation to get there.

    Level 0: n=0, no forks, no swear words
    Level 1: n=1-2, no forks or minor forks
    Level 2: forks present, gain > 0, possibly first swear words
    Level 3: n≥4, or VRS active, or high swear severity
    Level 4: recovery paths available + code lattice active
    Level 5: all systems active + high compound intent
    """
    # Level 5: everything active, high compound intent
    if in_vrs and has_recovery_paths and swear_word_count > 0 and compound_intent > 1.0 and qho_max_n >= 4:
        return 5

    # Level 4: recovery paths with code lattice
    if has_recovery_paths and swear_word_count > 0 and qho_max_n >= 3:
        return 4

    # Level 3: high excitation or VRS entry
    if qho_max_n >= 4 or in_vrs:
        return 3

    # Level 2: boundary detection (forks or swear words)
    if has_forks and monty_hall_gain > 0:
        return 2

    # Level 1: some excitation
    if qho_max_n >= 1:
        return 1

    # Level 0: ground state
    return 0


def curriculum_difficulty_from_level(level: int) -> float:
    """Map curriculum level to a normalized difficulty score.

    Uses the midpoint of each level's range.
    """
    lo, hi = LEVEL_BOUNDARIES[level]
    return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# Unified Simulation Bundle
# ---------------------------------------------------------------------------


@dataclass
class SimulationBundle:
    """A single text's complete simulation curriculum bundle.

    Fuses three engines:
        - Quantum frequency bundle (QHO + visual + acoustic + governance)
        - Flight dynamics (6-DOF + rotor + VRS + recovery)
        - Code lattice (patterns + anti-patterns + compound intent)

    Plus curriculum classification metadata.
    """

    text: str
    quantum: QuantumFrequencyBundle
    flight: FlightDynamicsState
    code: CodeLatticeBundle
    physics: PhysicsDomainState
    curriculum_level: int
    curriculum_difficulty: float

    # --- Derived properties ---

    @property
    def level_name(self) -> str:
        return LEVEL_NAMES[self.curriculum_level]

    @property
    def level_description(self) -> str:
        return LEVEL_DESCRIPTIONS[self.curriculum_level]

    @property
    def qho_max_n(self) -> int:
        return self.quantum.qho.max_excitation

    @property
    def is_ground_state(self) -> bool:
        return self.quantum.is_ground_state

    @property
    def has_forks(self) -> bool:
        return len(self.quantum.multipath.forks) > 0

    @property
    def monty_hall_gain(self) -> float:
        return self.quantum.multipath.monty_hall_advantage

    @property
    def swear_word_count(self) -> int:
        return self.code.swear_word_count

    @property
    def in_vrs(self) -> bool:
        return self.flight.is_in_vrs

    @property
    def has_recovery_paths(self) -> bool:
        return len(self.flight.recovery_paths) > 0

    @property
    def compound_intent(self) -> float:
        """Total compound intent from code lattice lessons."""
        return self.code.total_compound_intent

    @property
    def system_intent(self) -> float:
        """System intent = governance cost × QHO energy.

        The physics side: how much the universe is investing in this moment.
        """
        gov_cost = self.quantum.governance_cost()
        energy = self.quantum.phi_weighted_energy
        # Normalize energy to [0, ~10] range
        energy_norm = min(10.0, energy / 1e-32) if energy > 0 else 0.0
        return gov_cost * (1.0 + energy_norm)

    @property
    def learner_intent(self) -> float:
        """Learner intent = Monty Hall gain × lesson relevance.

        The learner side: how much the text is pushing toward understanding.
        """
        gain = self.monty_hall_gain
        # Mean relevance across lessons
        if self.code.lessons:
            mean_rel = sum(l.relevance for l in self.code.lessons) / len(self.code.lessons)
        else:
            mean_rel = 0.1  # baseline even with no lessons
        return gain * mean_rel + mean_rel  # always at least relevance

    @property
    def compounding_intent_score(self) -> float:
        """System intent × learner intent — multiplicative, not additive.

        This is THE metric: how much physics and understanding compound.
        Higher levels produce exponentially higher scores.
        """
        return self.system_intent * self.learner_intent

    @property
    def visual_vector(self) -> List[float]:
        return self.quantum.visual_vector

    @property
    def dominant_tongue(self) -> str:
        return self.quantum.qho.dominant_tongue

    @property
    def flight_regime(self) -> str:
        return self.flight.flight_regime

    @property
    def best_recovery(self) -> Optional[RecoveryPath]:
        return self.flight.best_recovery

    @property
    def physics_failure_count(self) -> int:
        return self.physics.failure_count

    @property
    def is_cascading(self) -> bool:
        return self.physics.is_cascading

    @property
    def active_phenomena(self) -> List[str]:
        return self.physics.active_phenomena

    @property
    def dominant_physics_field(self) -> str:
        return PHYSICS_FIELDS[self.physics.dominant_field].field_name

    def to_dict(self) -> dict:
        """Full serialization for SFT metadata."""
        result = {
            "curriculum": {
                "level": self.curriculum_level,
                "level_name": self.level_name,
                "difficulty": round(self.curriculum_difficulty, 4),
                "compounding_intent": round(self.compounding_intent_score, 6),
                "system_intent": round(self.system_intent, 6),
                "learner_intent": round(self.learner_intent, 6),
            },
            "quantum": self.quantum.to_dict(),
            "flight": self.flight.to_dict(),
            "physics": self.physics.to_dict(),
            "code_lattice": {
                "lesson_count": len(self.code.lessons),
                "swear_word_count": self.swear_word_count,
                "total_compound_intent": round(self.code.total_compound_intent, 4),
                "active_domains": list(self.code.active_domains),
                "lessons": [
                    {
                        "name": l.pattern.name,
                        "domain": l.pattern.domain,
                        "is_antipattern": l.pattern.is_antipattern,
                        "relevance": round(l.relevance, 4),
                        "compound_intent": round(l.compound_intent, 4),
                        "tongue": l.tongue,
                        "axis": l.axis,
                    }
                    for l in self.code.lessons
                ],
            },
        }
        return result


# ---------------------------------------------------------------------------
# Bundle Generator
# ---------------------------------------------------------------------------


def generate_simulation_bundle(
    text: str,
    is_rotorcraft: bool = True,
) -> SimulationBundle:
    """Generate a complete simulation curriculum bundle for a single text.

    Runs all three engines and classifies the curriculum level.

    text → trit → multipath → QHO → acoustic → flight → code lattice → level
    """
    # 1. Quantum frequency bundle (QHO + visual + acoustic + governance)
    quantum = generate_quantum_bundle(text)

    # 2. Flight dynamics (6-DOF + rotor + VRS + recovery)
    flight = qho_to_flight_state(
        trit=quantum.trit,
        multipath=quantum.multipath,
        mean_excitation=quantum.qho.mean_excitation,
        max_excitation=quantum.qho.max_excitation,
        acoustic_infra=quantum.acoustic.infrasonic_power,
        acoustic_audible=quantum.acoustic.audible_power,
        acoustic_ultra=quantum.acoustic.ultrasonic_power,
        is_rotorcraft=is_rotorcraft,
    )

    # 3. Code lattice (patterns + swear words + compound intent)
    code = generate_code_lattice_bundle(text)

    # 4. Physics domain state (6 fields + 15 couplings + cascades)
    physics = compute_physics_domain_state(quantum.trit)

    # 5. Classify curriculum level from combined state
    level = classify_curriculum_level(
        qho_max_n=quantum.qho.max_excitation,
        has_forks=len(quantum.multipath.forks) > 0,
        monty_hall_gain=quantum.multipath.monty_hall_advantage,
        swear_word_count=code.swear_word_count,
        in_vrs=flight.is_in_vrs,
        has_recovery_paths=len(flight.recovery_paths) > 0,
        compound_intent=code.total_compound_intent,
    )

    difficulty = curriculum_difficulty_from_level(level)

    return SimulationBundle(
        text=text,
        quantum=quantum,
        flight=flight,
        code=code,
        physics=physics,
        curriculum_level=level,
        curriculum_difficulty=difficulty,
    )


def generate_simulation_batch(
    texts: List[str],
    is_rotorcraft: bool = True,
) -> List[SimulationBundle]:
    """Batch generation of simulation curriculum bundles."""
    return [generate_simulation_bundle(t, is_rotorcraft) for t in texts]


# ---------------------------------------------------------------------------
# SFT Record Generation — Level-Appropriate Training Records
# ---------------------------------------------------------------------------


def _level_0_sft(bundle: SimulationBundle) -> str:
    """Level 0: Ground state observation. Just frequency assignment."""
    vis = bundle.visual_vector
    acous = bundle.quantum.acoustic
    return (
        f"Ground state. All tongues at n=0. "
        f"Dominant tongue: {bundle.dominant_tongue.upper()}. "
        f"Infrasonic dominant ({acous.infrasonic_power:.2f}). "
        f"No vortex risk. No anti-patterns. "
        f"Visual: [{', '.join(f'{v:.3f}' for v in vis)}]"
    )


def _level_1_sft(bundle: SimulationBundle) -> str:
    """Level 1: Excitation + frequency tagging."""
    qho = bundle.quantum.qho
    acous = bundle.quantum.acoustic
    dom = bundle.dominant_tongue
    n_max = bundle.qho_max_n

    tongue_states = ", ".join(f"{t.upper()}=n{qho.states[t].n}" for t in TONGUE_ORDER if qho.states[t].n > 0)
    if not tongue_states:
        tongue_states = "all ground"

    return (
        f"n={n_max}, dominant {dom.upper()} "
        f"(λ={qho.states[dom].wavelength_nm:.0f}nm). "
        f"Excited tongues: {tongue_states}. "
        f"Acoustic: infra={acous.infrasonic_power:.2f}, "
        f"audible={acous.audible_power:.2f}, ultra={acous.ultrasonic_power:.2f}. "
        f"Interval: {acous.dominant_interval}. "
        f"No VRS, no swear words."
    )


def _level_2_sft(bundle: SimulationBundle) -> str:
    """Level 2: Boundary detection + forks + first swear words."""
    mp = bundle.quantum.multipath
    n_forks = len(mp.forks)
    gain = mp.monty_hall_advantage
    swears = bundle.swear_word_count

    fork_detail = ""
    if mp.forks:
        axes = set(f.axis for f in mp.forks)
        fork_detail = f"Fork on {'/'.join(axes)} axis, gain={gain:.2f}, {n_forks} sibling paths. "

    swear_detail = ""
    if swears > 0:
        anti_lessons = [l for l in bundle.code.lessons if l.pattern.is_antipattern]
        if anti_lessons:
            worst = max(anti_lessons, key=lambda l: l.compound_intent)
            swear_detail = (
                f'Swear word detected: "{worst.pattern.name}" '
                f"(severity {worst.compound_intent:.2f}). "
                f"Recovery: {worst.pattern.code_good[:80]}... "
            )

    return (
        f"n={bundle.qho_max_n}, {fork_detail}"
        f"{swear_detail}"
        f"Flight regime: {bundle.flight_regime}. "
        f"Envelope margin: {bundle.flight.envelope_margin:.3f}."
    )


def _level_3_sft(bundle: SimulationBundle) -> str:
    """Level 3: High excitation + VRS entry."""
    flight = bundle.flight
    swears = bundle.swear_word_count

    vrs_text = ""
    if flight.is_in_vrs and flight.rotor:
        descent = max(0, -flight.sixdof.w)
        vi = flight.rotor.induced_velocity
        margin = flight.rotor.vrs_margin(descent)
        vrs_text = f"in_vrs=true, descent={descent:.1f}m/s, " f"v_i={vi:.1f}m/s, margin={margin:.2f}. "
    else:
        vrs_text = f"flight_regime={bundle.flight_regime}, "

    swear_text = ""
    if swears > 0:
        anti_lessons = [l for l in bundle.code.lessons if l.pattern.is_antipattern]
        names = [l.pattern.name for l in anti_lessons[:3]]
        swear_text = f"Swear words ({swears}): {', '.join(names)}. "

    recovery_count = len(flight.recovery_paths)
    recovery_text = f"{recovery_count} recovery paths available. " if recovery_count > 0 else ""

    # Physics domain state
    physics_text = ""
    if bundle.physics_failure_count > 0:
        failing = bundle.physics.failing_tongues
        physics_text = (
            f"Physics fields failing ({bundle.physics_failure_count}/6): "
            f"{', '.join(t.upper() + '=' + PHYSICS_FIELDS[t].failure_name for t in failing)}. "
        )

    return (
        f"n={bundle.qho_max_n}, {vrs_text}"
        f"{swear_text}{recovery_text}{physics_text}"
        f"Compound intent: {bundle.compound_intent:.3f}. "
        f"Compounding score: {bundle.compounding_intent_score:.4f}."
    )


def _level_4_sft(bundle: SimulationBundle) -> str:
    """Level 4: Multi-path recovery + full code lattice."""
    flight = bundle.flight
    paths = flight.recovery_paths
    _best = flight.best_recovery

    recovery_text = ""
    if paths:
        path_details = []
        for p in sorted(paths, key=lambda x: x.severity):
            mh = " [MONTY HALL SWITCH]" if p.monty_hall_selected else ""
            path_details.append(
                f"{p.recovery_type} (P={p.success_probability:.2f}, "
                f"{p.time_to_recover_s:.0f}s, "
                f"alt_loss={p.altitude_loss_m:.0f}m{mh})"
            )
        recovery_text = " > ".join(path_details) + ". "

    # Code lattice cross-domain mapping
    cross_text = ""
    if bundle.code.lessons:
        top_lesson = max(bundle.code.lessons, key=lambda l: l.compound_intent)
        cross_text = (
            f'Code lattice: "{top_lesson.pattern.name}" '
            f"({top_lesson.pattern.domain}) — "
            f"{top_lesson.pattern.cross_domain[:100]}. "
        )

    # Active coupling phenomena
    phenomena_text = ""
    if bundle.active_phenomena:
        phenomena_text = f"Active inter-field couplings: {', '.join(bundle.active_phenomena[:4])}. "

    return (
        f"n={bundle.qho_max_n}, {recovery_text}"
        f"{cross_text}{phenomena_text}"
        f"Compounding intent: {bundle.compounding_intent_score:.4f}."
    )


def _level_5_sft(bundle: SimulationBundle) -> str:
    """Level 5: Full lattice generalization — physics = magic = code."""
    _qho = bundle.quantum.qho
    flight = bundle.flight
    code = bundle.code

    # Tongue spell notation
    dom = bundle.dominant_tongue
    n = bundle.qho_max_n
    regime = bundle.flight_regime

    # Recovery summary
    recovery_text = ""
    if flight.recovery_paths:
        best = flight.best_recovery
        if best:
            recovery_text = f"{best.recovery_type} recovery " f"(P={best.success_probability:.2f}). "

    # Anti-pattern avoidance
    swear_text = ""
    if code.swear_word_count > 0:
        swear_text = f"Anti-patterns avoided ({code.swear_word_count}): " f"explicit recovery paths provided. "

    # Cross-domain transfer
    cross_text = ""
    if code.lessons:
        domains = list(code.active_domains)
        cross_text = f"Cross-domain transfer active across {len(domains)} domains " f"({', '.join(domains)}). "

    # Energy accounting
    energy_text = (
        f"System intent: {bundle.system_intent:.4f}, "
        f"learner intent: {bundle.learner_intent:.4f}. "
        f"Compounding: {bundle.compounding_intent_score:.6f}. "
    )

    # Physics domain cascade
    physics_text = ""
    if bundle.physics_failure_count > 0:
        physics_text = (
            f"Physics: {bundle.dominant_physics_field} dominant, " f"{bundle.physics_failure_count} fields failing"
        )
        if bundle.is_cascading:
            physics_text += f", cascade depth {bundle.physics.cascade_depth}"
        physics_text += ". "
        # Recovery fields (hybrid tongue invocations needed)
        rec_fields = required_recovery_fields(bundle.physics.failing_tongues)
        if rec_fields:
            channel_names = [COUPLING_CHANNELS[c].hybrid_name for c in rec_fields[:3]]
            physics_text += f"Recovery invocations: {', '.join(channel_names)}. "

    return (
        f"[{dom.upper()} n={n}] Regime: {regime}. "
        f"{recovery_text}{swear_text}{cross_text}{physics_text}{energy_text}"
        f"The lattice is complete. Physics = code = understanding."
    )


# Map level → SFT generator
_LEVEL_SFT_GENERATORS = {
    0: _level_0_sft,
    1: _level_1_sft,
    2: _level_2_sft,
    3: _level_3_sft,
    4: _level_4_sft,
    5: _level_5_sft,
}


def generate_curriculum_sft_records(
    bundles: List[SimulationBundle],
) -> List[dict]:
    """Generate SFT training records from simulation bundles.

    Each record teaches at the appropriate curriculum level.
    Level determines response complexity and which systems are active.
    """
    records = []

    for bundle in bundles:
        text_excerpt = bundle.text[:200]
        level = bundle.curriculum_level

        # User prompt scales with level
        if level <= 1:
            user_content = f"Analyze the quantum frequency profile of this text:\n\n" f'"{text_excerpt}"'
        elif level <= 3:
            user_content = (
                f"Analyze the quantum frequency profile and flight dynamics "
                f"of this text. Flag any anti-patterns:\n\n"
                f'"{text_excerpt}"'
            )
        else:
            user_content = (
                f"Full simulation analysis: quantum frequency, flight dynamics, "
                f"VRS status, code lattice anti-patterns, and recovery paths:\n\n"
                f'"{text_excerpt}"'
            )

        # Assistant response from level-appropriate generator
        generator = _LEVEL_SFT_GENERATORS[level]
        assistant_content = generator(bundle)

        records.append(
            {
                "messages": [
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content},
                ],
                "metadata": {
                    "source": "simulation_curriculum_generator",
                    "record_type": "simulation_curriculum",
                    "curriculum_level": level,
                    "curriculum_difficulty": round(bundle.curriculum_difficulty, 4),
                    "compounding_intent": round(bundle.compounding_intent_score, 6),
                    "simulation_bundle": bundle.to_dict(),
                    **flatten_physics_domain_for_sft(bundle.physics),
                },
            }
        )

    return records


# ---------------------------------------------------------------------------
# Batch Summary
# ---------------------------------------------------------------------------


def curriculum_summary(bundles: List[SimulationBundle]) -> dict:
    """Summary statistics for a batch of simulation bundles."""
    if not bundles:
        return {"count": 0}

    n = len(bundles)

    # Level distribution
    level_dist = {i: 0 for i in range(6)}
    for b in bundles:
        level_dist[b.curriculum_level] += 1

    # Compounding intent stats
    intents = [b.compounding_intent_score for b in bundles]
    mean_intent = sum(intents) / n
    max_intent = max(intents)

    # VRS count
    vrs_count = sum(1 for b in bundles if b.in_vrs)

    # Swear word stats
    total_swears = sum(b.swear_word_count for b in bundles)

    # Recovery path stats
    recovery_count = sum(1 for b in bundles if b.has_recovery_paths)

    # Fork stats
    fork_count = sum(1 for b in bundles if b.has_forks)

    # Domain activity
    domain_activity: Dict[str, int] = {}
    for b in bundles:
        for d in b.code.active_domains:
            domain_activity[d] = domain_activity.get(d, 0) + 1

    return {
        "count": n,
        "level_distribution": {f"L{k} ({LEVEL_NAMES[k][:30]})": v for k, v in sorted(level_dist.items())},
        "level_counts": level_dist,
        "compounding_intent": {
            "mean": round(mean_intent, 6),
            "max": round(max_intent, 6),
        },
        "vrs_entries": vrs_count,
        "vrs_pct": round(vrs_count / n * 100, 1),
        "total_swear_words": total_swears,
        "bundles_with_recovery": recovery_count,
        "bundles_with_forks": fork_count,
        "domain_activity": dict(sorted(domain_activity.items(), key=lambda x: -x[1])),
        "physics_failures": sum(b.physics_failure_count for b in bundles),
        "physics_cascading": sum(1 for b in bundles if b.is_cascading),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def format_curriculum_report(bundles: List[SimulationBundle]) -> str:
    """Human-readable curriculum report."""
    if not bundles:
        return "No bundles to report."

    summary = curriculum_summary(bundles)
    n = summary["count"]

    lines = [
        "=" * 70,
        "SIMULATION CURRICULUM REPORT",
        "Progressive 6-Level Training — Egg to Expert",
        "=" * 70,
        "",
        "THE PRINCIPLE:",
        "  Repetition is scaffolding. Understanding compounds.",
        "  System intent × learner intent = the lattice.",
        "  Physics = magic = code.",
        "",
        f"Total bundles: {n}",
        f"VRS entries: {summary['vrs_entries']} ({summary['vrs_pct']}%)",
        f"Swear words: {summary['total_swear_words']}",
        f"With recovery paths: {summary['bundles_with_recovery']}",
        f"With polymorphic forks: {summary['bundles_with_forks']}",
        f"Mean compounding intent: {summary['compounding_intent']['mean']:.6f}",
        f"Max compounding intent: {summary['compounding_intent']['max']:.6f}",
        "",
        "LEVEL DISTRIBUTION:",
    ]

    for k in range(6):
        count = summary["level_counts"][k]
        pct = round(count / n * 100, 1) if n > 0 else 0
        bar = "#" * int(pct / 2) + "." * (50 - int(pct / 2))
        lines.append(f"  L{k}: [{bar}] {count:>4} ({pct:>5.1f}%)  {LEVEL_NAMES[k]}")

    lines.append("")
    lines.append("DOMAIN ACTIVITY:")
    for domain, count in summary["domain_activity"].items():
        lines.append(f"  {domain:>15}: {count}")

    lines.append("")
    lines.append("PER-BUNDLE DETAIL:")
    for _i, b in enumerate(bundles[:20]):  # cap at 20 for readability
        regime = b.flight_regime
        n_max = b.qho_max_n
        swears = b.swear_word_count
        recovery = len(b.flight.recovery_paths)
        ci = b.compounding_intent_score

        bar = "#" * n_max + "." * (7 - n_max)
        lines.append(
            f"  [{bar}] L{b.curriculum_level}  {regime:>7}  "
            f"swears={swears}  recovery={recovery}  "
            f"CI={ci:.4f}  {b.text[:45]}"
        )

    if len(bundles) > 20:
        lines.append(f"  ... and {len(bundles) - 20} more bundles")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_texts = [
        # Level 0 candidates (simple, short)
        "Hello world",
        "The sun rises in the east",
        # Level 1 candidates (some structure)
        "Love is the only force that transcends dimension and time",
        "Gradient descent follows the negative gradient of the loss surface",
        # Level 2 candidates (boundary-crossing)
        "The Riemann zeta function spun in the complex plane reveals non-trivial zeros",
        "Post-quantum cryptography uses lattice-based assumptions for security",
        # Level 3+ candidates (high complexity)
        "Vortex ring state onset as the helicopter descended into its own downwash creating a toroidal recirculation pattern",
        "The void between stars is not empty it is full of potential energy waiting for the right perturbation to cascade",
        "Every pattern rune hums at its own frequency in the lattice binding structure to meaning across all six tongues simultaneously",
        "Entangled photons maintain quantum harmony across arbitrary distance until observation forces state collapse into one of the basis vectors",
        "Autorotation recovery from deep VRS requires immediate collective reduction plus forward cyclic displacement to exit the recirculation zone",
        "The toroidal box turns inward until every lane speaks the same harmonic truth binding physics to magic to code in a single breath",
    ]

    print("=" * 70)
    print("SIMULATION CURRICULUM — Progressive 6-Level Training")
    print("Egg to Expert: QHO + Flight + Code Lattice unified")
    print("=" * 70)
    print()

    bundles = generate_simulation_batch(test_texts)

    for b in bundles:
        n_max = b.qho_max_n
        bar = "#" * n_max + "." * (7 - n_max)
        regime = b.flight_regime
        swears = b.swear_word_count
        recovery = len(b.flight.recovery_paths)
        ci = b.compounding_intent_score

        print(
            f"  L{b.curriculum_level} [{bar}] {regime:>7}  "
            f"dom={b.dominant_tongue.upper()}  "
            f"swears={swears}  recovery={recovery}  "
            f"CI={ci:.6f}"
        )
        print(f"    {b.level_name}")
        print(f"    text: {b.text[:60]}")
        print()

    # Report
    report = format_curriculum_report(bundles)
    print(report)

    # SFT records
    records = generate_curriculum_sft_records(bundles)
    print(f"\nSFT records generated: {len(records)}")
    for rec in records[:3]:
        print(f"\n  Level {rec['metadata']['curriculum_level']}: " f"{rec['messages'][1]['content'][:100]}...")
