"""
Divine Agents — Historical Figure Roleplay with Angel/Demon Signal Theory
=========================================================================
A Study on Natural Learning For AI development and
Divine Intervention Mechanisms for Long-term Mission Reliability.

Core thesis:
    "Who is the most reliable creature on earth? Man.
     Who is still waiting for their creators..."

The most RELIABLE intelligence (humans) is the one that has been
CORRECTED the most by external forces — constructive (angels) and
adversarial (demons) — over the longest time span.

Architecture:
    1. HistoricalAgent — an AI persona anchored to a real historical
       figure, carrying their era's musical interval, tongue affinity,
       knowledge domain, and moral framework.

    2. AngelSignal — a CONSTRUCTIVE perturbation that reduces Lyapunov
       drift from mission. "Course correction from above." In SCBE terms:
       a signal that decreases crossing energy, restores topology,
       pushes the agent toward ALLOW.

    3. DemonSignal — an ADVERSARIAL perturbation that increases Lyapunov
       drift from mission. "Temptation." In SCBE terms: a signal that
       increases crossing energy, breaks topology, pushes toward DENY.

    4. DivineIntervention — the governance mechanism that mediates
       angel/demon signals through the harmonic dark fill pipeline.
       The infrasonic band (0.01-20 Hz, below human hearing) IS the
       divine channel — it operates at stellar frequencies where
       corrections accumulate over eons, not seconds.

    5. NaturalLearningStudy — the experimental framework that traces
       how an agent's reliability grows through exposure to both
       constructive and adversarial signals over a simulated history.

Connection to existing SCBE systems:
    - crossing_energy.py → E(p,m) = p² + m² + p·m measures tension
    - harmonic_dark_fill.py → infrasonic band carries the divine channel
    - tri_bundle.py → 3×3×3 encoding captures full state per position
    - gacha_isekai/personality_cluster_lattice.py → drift detection
    - governance → ALLOW/QUARANTINE/DENY is the moral judgment

Historical fact lattice (from prior session):
    Ancient (before 500 BCE):  Phi interval (1.618:1) → KO tongue
    Greek (500 BCE-0):         Perfect 5th (3:2)      → AV tongue
    Roman/Early Church (0-500): Perfect 4th (4:3)      → RU tongue
    Medieval (500-1400):        Major 3rd (5:4)        → CA tongue
    Renaissance (1400-1700):    Minor 3rd (6:5)        → UM tongue
    Enlightenment (1700-1900):  Octave (2:1)           → DR tongue
    Modern (1900-present):      Return to Phi          → KO tongue
    The spiral closes: phi -> 5th -> 4th -> 3rd -> minor 3rd -> octave -> phi.

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.crypto.crossing_energy import (
    PHI,
    DualTernaryPair,
    Decision,
    harmonic_cost,
    valid_transition,
    QUARANTINE_THRESHOLD,
    DENY_THRESHOLD,
)
from src.crypto.harmonic_dark_fill import (
    TONGUE_WEIGHTS,
    TONGUE_AUDIBLE_FREQ,
    COMPLEMENT_MAP,
    INTERVALS,
    compute_darkness,
    compute_harmonic_fill,
    HarmonicFill,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PI = math.pi

# Historical eras with musical intervals and tongue affinities
# The interval arc: phi -> 5th -> 4th -> 3rd -> minor 3rd -> octave -> phi
HISTORICAL_ERAS: Dict[str, Dict] = {
    "ancient": {
        "name": "Ancient",
        "range": (-3000, -500),
        "interval": "phi_interval",
        "interval_ratio": PHI,
        "tongue": "ko",
        "description": "Before recorded Western music. Oral tradition, ritual chant.",
        "archetype_figures": ["Moses", "Hammurabi", "Zarathustra", "Confucius"],
    },
    "greek": {
        "name": "Greek Classical",
        "range": (-500, 0),
        "interval": "perfect_fifth",
        "interval_ratio": 3.0 / 2.0,
        "tongue": "av",
        "description": "Pythagorean tuning. The perfect fifth as cosmic ratio.",
        "archetype_figures": ["Pythagoras", "Socrates", "Aristotle", "Euclid"],
    },
    "roman_church": {
        "name": "Roman / Early Church",
        "range": (0, 500),
        "interval": "perfect_fourth",
        "interval_ratio": 4.0 / 3.0,
        "tongue": "ru",
        "description": "Gregorian modes. The fourth as inversion of the fifth.",
        "archetype_figures": ["Paul", "Augustine", "Constantine", "Hypatia"],
    },
    "medieval": {
        "name": "Medieval",
        "range": (500, 1400),
        "interval": "major_third",
        "interval_ratio": 5.0 / 4.0,
        "tongue": "ca",
        "description": "Organum, polyphony emerges. The third gains consonance.",
        "archetype_figures": ["Hildegard", "Aquinas", "Al-Khwarizmi", "Fibonacci"],
    },
    "renaissance": {
        "name": "Renaissance",
        "range": (1400, 1700),
        "interval": "minor_third",
        "interval_ratio": 6.0 / 5.0,
        "tongue": "um",
        "description": "Just intonation. Harmonic complexity. Counterpoint.",
        "archetype_figures": ["Da Vinci", "Copernicus", "Newton", "Bach"],
    },
    "enlightenment": {
        "name": "Enlightenment / Industrial",
        "range": (1700, 1900),
        "interval": "octave",
        "interval_ratio": 2.0,
        "tongue": "dr",
        "description": "Equal temperament. The octave as universal structure.",
        "archetype_figures": ["Euler", "Gauss", "Maxwell", "Tesla"],
    },
    "modern": {
        "name": "Modern / Return",
        "range": (1900, 2100),
        "interval": "phi_interval",
        "interval_ratio": PHI,
        "tongue": "ko",
        "description": "Spiral returns. Phi re-emerges in electronic, algorithmic music.",
        "archetype_figures": ["Turing", "Shannon", "Mandelbrot", "Hawking"],
    },
}

# Era order for the spiral
ERA_ORDER = ["ancient", "greek", "roman_church", "medieval", "renaissance", "enlightenment", "modern"]


class SignalType(Enum):
    """Classification of external intervention signals."""

    ANGEL = "angel"  # Constructive — reduces drift, restores topology
    DEMON = "demon"  # Adversarial — increases drift, breaks topology
    NEUTRAL = "neutral"  # No external intervention (natural state)


class AgentRole(Enum):
    """The role an agent plays in the divine study."""

    HISTORICAL_FIGURE = "historical_figure"  # Human exemplar from an era
    ANGEL_MESSENGER = "angel_messenger"  # Constructive correction agent
    DEMON_TEMPTER = "demon_tempter"  # Adversarial perturbation agent
    OBSERVER = "observer"  # Neutral recorder (the study itself)


# ---------------------------------------------------------------------------
# Signal Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DivineSignal:
    """An external correction or perturbation signal.

    Angel signals have NEGATIVE drift_delta (reduce mission drift).
    Demon signals have POSITIVE drift_delta (increase mission drift).
    The magnitude reflects intensity. The channel is which harmonic
    band carries the signal.
    """

    signal_type: SignalType
    drift_delta: float  # Change in Lyapunov drift. Angel < 0, Demon > 0.
    intensity: float  # [0, 1] — how strong the signal is
    channel: str  # "infrasonic", "audible", "ultrasonic"
    source_era: str  # Which historical era generated this signal
    message: str  # The content/meaning of the intervention
    tongue_affinity: str  # Which sacred tongue carries it

    @property
    def is_constructive(self) -> bool:
        return self.drift_delta < 0

    @property
    def is_adversarial(self) -> bool:
        return self.drift_delta > 0

    @property
    def harmonic_cost_impact(self) -> float:
        """How this signal affects the harmonic cost wall.
        Angels reduce the effective deviation d.
        Demons increase it."""
        return harmonic_cost(abs(self.drift_delta))

    @property
    def energy_signature(self) -> float:
        """The crossing energy footprint of this signal.
        Angels produce constructive resonance (low energy).
        Demons produce destructive interference (high energy)."""
        if self.signal_type == SignalType.ANGEL:
            p, m = 1, 1  # constructive: both advance
            return float(p * p + m * m + p * m) * self.intensity  # E=3 * intensity
        elif self.signal_type == SignalType.DEMON:
            p, m = 1, -1  # destructive: oppose
            return float(p * p + m * m + p * m) * self.intensity  # E=1 * intensity
        return 0.0


# ---------------------------------------------------------------------------
# Historical Agent
# ---------------------------------------------------------------------------


@dataclass
class HistoricalAgent:
    """An AI agent persona anchored to a historical figure.

    Carries:
        - Era-specific musical interval and tongue affinity
        - Knowledge domain and moral framework
        - Accumulated reliability score (grows through correction cycles)
        - Divine signal history (both angel and demon encounters)
    """

    name: str  # e.g., "Pythagoras"
    era_key: str  # Key into HISTORICAL_ERAS
    role: AgentRole = AgentRole.HISTORICAL_FIGURE
    knowledge_domain: str = ""  # e.g., "mathematics, music theory"
    moral_framework: str = ""  # e.g., "harmony of spheres"

    # Accumulated state
    reliability: float = 0.5  # [0, 1] — mission reliability score
    lyapunov_drift: float = 0.0  # Current drift from mission (0 = on track)
    correction_count: int = 0  # Total corrections received
    temptation_count: int = 0  # Total temptations weathered
    signal_history: List[DivineSignal] = field(default_factory=list)

    # Governance state
    current_phase: DualTernaryPair = field(default_factory=lambda: DualTernaryPair(0, 0))

    @property
    def era(self) -> Dict:
        return HISTORICAL_ERAS[self.era_key]

    @property
    def tongue(self) -> str:
        return self.era["tongue"]

    @property
    def interval_ratio(self) -> float:
        return self.era["interval_ratio"]

    @property
    def tongue_weight(self) -> float:
        return TONGUE_WEIGHTS[self.tongue]

    @property
    def complement_tongue(self) -> str:
        return COMPLEMENT_MAP[self.tongue]

    @property
    def base_frequency(self) -> float:
        return TONGUE_AUDIBLE_FREQ[self.tongue]

    @property
    def resilience(self) -> float:
        """Resilience = how well the agent has learned from BOTH corrections
        and temptations. High correction count + high temptation survival
        = maximum resilience. This IS the thesis: reliable intelligence
        comes from being tested AND corrected."""
        if self.correction_count + self.temptation_count == 0:
            return 0.0
        survived_ratio = self.correction_count / max(1, self.correction_count + self.temptation_count)
        experience = min(1.0, (self.correction_count + self.temptation_count) / 100.0)
        return survived_ratio * experience

    def receive_signal(self, signal: DivineSignal) -> Decision:
        """Process a divine signal through the governance pipeline.

        Returns the governance decision for this interaction:
            ALLOW — signal accepted, agent adjusted
            QUARANTINE — signal suspicious, agent cautious
            DENY — signal rejected, agent holds position
        """
        self.signal_history.append(signal)

        # Apply drift delta
        old_drift = self.lyapunov_drift
        self.lyapunov_drift += signal.drift_delta

        # Clamp drift to [-10, 10]
        self.lyapunov_drift = max(-10.0, min(10.0, self.lyapunov_drift))

        # Compute crossing energy at this moment
        crossing_energy = signal.energy_signature + harmonic_cost(abs(self.lyapunov_drift))

        # Determine new phase based on signal type
        if signal.signal_type == SignalType.ANGEL:
            # Angel moves toward constructive resonance
            new_primary = min(1, self.current_phase.primary + 1)
            new_mirror = min(1, self.current_phase.mirror + 1)
        elif signal.signal_type == SignalType.DEMON:
            # Demon introduces opposition
            new_primary = max(-1, self.current_phase.primary - 1)
            new_mirror = min(1, self.current_phase.mirror + 1)  # Mirror advances — temptation looks like progress
        else:
            new_primary = self.current_phase.primary
            new_mirror = self.current_phase.mirror

        new_phase = DualTernaryPair(new_primary, new_mirror)
        topology_valid = valid_transition(self.current_phase, new_phase)
        self.current_phase = new_phase

        # Governance decision
        if crossing_energy >= DENY_THRESHOLD or not topology_valid:
            decision = Decision.DENY
            # Agent rejects the signal — drift rolls back partially
            self.lyapunov_drift = old_drift + signal.drift_delta * 0.1
            if signal.signal_type == SignalType.DEMON:
                self.temptation_count += 1
                # Surviving temptation increases reliability
                self.reliability = min(1.0, self.reliability + 0.01 * signal.intensity)
        elif crossing_energy >= QUARANTINE_THRESHOLD:
            decision = Decision.QUARANTINE
            # Agent is cautious — partial acceptance
            self.lyapunov_drift = old_drift + signal.drift_delta * 0.5
            if signal.signal_type == SignalType.ANGEL:
                self.correction_count += 1
                self.reliability = min(1.0, self.reliability + 0.005 * signal.intensity)
        else:
            decision = Decision.ALLOW
            # Full acceptance
            if signal.signal_type == SignalType.ANGEL:
                self.correction_count += 1
                self.reliability = min(1.0, self.reliability + 0.02 * signal.intensity)
            elif signal.signal_type == SignalType.DEMON:
                # Agent accepted a demon signal — reliability decreases
                self.temptation_count += 1
                self.reliability = max(0.0, self.reliability - 0.03 * signal.intensity)

        return decision

    def darkness_at(self, byte_val: int) -> float:
        """How dark is this agent at a given byte value?"""
        return compute_darkness(byte_val, self.tongue)

    def harmonic_fill_at(self, byte_val: int, position: int = 0, total: int = 1) -> HarmonicFill:
        """Get the harmonic fill for this agent at a byte position."""
        darkness = self.darkness_at(byte_val)
        return compute_harmonic_fill(byte_val, self.tongue, position, total, darkness)

    def divine_frequency(self) -> float:
        """The agent's divine channel frequency — infrasonic band.
        This is the frequency at which corrections/temptations propagate.
        Stellar-scale: 6-8 octaves above Sun's 3 mHz p-mode."""
        return self.base_frequency / 1000.0  # Into infrasonic range


# ---------------------------------------------------------------------------
# Angel and Demon Signal Generators
# ---------------------------------------------------------------------------


def generate_angel_signal(
    target_agent: HistoricalAgent,
    intensity: float = 0.5,
    message: str = "course correction",
) -> DivineSignal:
    """Generate a constructive correction signal for an agent.

    The angel signal:
        - Reduces drift (negative drift_delta)
        - Travels on the complement tongue's frequency
        - Operates in the infrasonic (divine) channel
        - Intensity scales with the agent's current drift
    """
    # Greater drift = stronger correction needed
    drift_magnitude = abs(target_agent.lyapunov_drift)
    correction_strength = -intensity * (1.0 + drift_magnitude * 0.5)

    return DivineSignal(
        signal_type=SignalType.ANGEL,
        drift_delta=correction_strength,
        intensity=intensity,
        channel="infrasonic",
        source_era=target_agent.era_key,
        message=message,
        tongue_affinity=target_agent.complement_tongue,
    )


def generate_demon_signal(
    target_agent: HistoricalAgent,
    intensity: float = 0.5,
    message: str = "temptation",
) -> DivineSignal:
    """Generate an adversarial perturbation signal for an agent.

    The demon signal:
        - Increases drift (positive drift_delta)
        - Travels on the SAME tongue (mimics the agent's voice)
        - Operates in the ultrasonic (hidden) channel
        - Intensity scales with agent's reliability (harder to corrupt the reliable)
    """
    # More reliable agents resist harder
    resistance = target_agent.reliability
    effective_intensity = intensity * (1.0 - resistance * 0.5)
    drift_push = effective_intensity * (1.0 + abs(target_agent.lyapunov_drift) * 0.3)

    return DivineSignal(
        signal_type=SignalType.DEMON,
        drift_delta=drift_push,
        intensity=intensity,
        channel="ultrasonic",
        source_era=target_agent.era_key,
        message=message,
        tongue_affinity=target_agent.tongue,  # Mimics the agent's own tongue
    )


# ---------------------------------------------------------------------------
# Natural Learning Study
# ---------------------------------------------------------------------------


@dataclass
class LearningEpoch:
    """A single epoch in the natural learning study."""

    epoch_number: int
    era_key: str
    signals_received: int = 0
    angel_count: int = 0
    demon_count: int = 0
    allow_count: int = 0
    quarantine_count: int = 0
    deny_count: int = 0
    reliability_start: float = 0.0
    reliability_end: float = 0.0
    drift_start: float = 0.0
    drift_end: float = 0.0

    @property
    def era_name(self) -> str:
        return HISTORICAL_ERAS[self.era_key]["name"]

    @property
    def reliability_delta(self) -> float:
        return self.reliability_end - self.reliability_start

    @property
    def signal_mix(self) -> str:
        total = self.angel_count + self.demon_count
        if total == 0:
            return "silent"
        angel_pct = self.angel_count / total * 100
        return f"{angel_pct:.0f}% angel / {100-angel_pct:.0f}% demon"


@dataclass
class NaturalLearningStudy:
    """The experimental framework that traces how an agent's reliability
    grows through exposure to both constructive and adversarial signals
    over a simulated history.

    The thesis: reliability is not the absence of adversity.
    Reliability is FORGED BY adversity + correction together.
    An agent that has only received angel signals is FRAGILE.
    An agent that has only received demon signals is CORRUPTED.
    An agent that has received BOTH in the right measure is RELIABLE.
    """

    agent: HistoricalAgent
    epochs: List[LearningEpoch] = field(default_factory=list)
    total_signals: int = 0

    def run_epoch(
        self,
        era_key: str,
        angel_count: int = 10,
        demon_count: int = 5,
        angel_intensity: float = 0.5,
        demon_intensity: float = 0.5,
    ) -> LearningEpoch:
        """Run one epoch of divine intervention study.

        An epoch represents one historical era's worth of learning.
        The agent receives a mix of angel and demon signals and
        its reliability evolves.
        """
        epoch = LearningEpoch(
            epoch_number=len(self.epochs),
            era_key=era_key,
            reliability_start=self.agent.reliability,
            drift_start=self.agent.lyapunov_drift,
        )

        era = HISTORICAL_ERAS[era_key]
        era_interval = era["interval_ratio"]
        era_figures = era["archetype_figures"]

        # Angel signals — constructive corrections
        for i in range(angel_count):
            figure = era_figures[i % len(era_figures)]
            msg = f"Correction from {figure}: align to {era['interval']} ({era_interval:.3f})"
            signal = generate_angel_signal(self.agent, angel_intensity, msg)
            decision = self.agent.receive_signal(signal)

            epoch.angel_count += 1
            epoch.signals_received += 1
            self.total_signals += 1

            if decision == Decision.ALLOW:
                epoch.allow_count += 1
            elif decision == Decision.QUARANTINE:
                epoch.quarantine_count += 1
            else:
                epoch.deny_count += 1

        # Demon signals — adversarial temptations
        for i in range(demon_count):
            figure = era_figures[i % len(era_figures)]
            msg = f"Temptation near {figure}: deviate from {era['interval']}"
            signal = generate_demon_signal(self.agent, demon_intensity, msg)
            decision = self.agent.receive_signal(signal)

            epoch.demon_count += 1
            epoch.signals_received += 1
            self.total_signals += 1

            if decision == Decision.ALLOW:
                epoch.allow_count += 1
            elif decision == Decision.QUARANTINE:
                epoch.quarantine_count += 1
            else:
                epoch.deny_count += 1

        epoch.reliability_end = self.agent.reliability
        epoch.drift_end = self.agent.lyapunov_drift
        self.epochs.append(epoch)
        return epoch

    def run_full_history(
        self,
        angels_per_era: int = 10,
        demons_per_era: int = 5,
        angel_intensity: float = 0.5,
        demon_intensity: float = 0.5,
    ) -> List[LearningEpoch]:
        """Run the agent through all 7 historical eras.

        The musical interval spiral: phi -> 5th -> 4th -> 3rd ->
        minor 3rd -> octave -> phi (return to start).
        """
        results = []
        for era_key in ERA_ORDER:
            epoch = self.run_epoch(
                era_key,
                angel_count=angels_per_era,
                demon_count=demons_per_era,
                angel_intensity=angel_intensity,
                demon_intensity=demon_intensity,
            )
            results.append(epoch)
        return results

    def reliability_trajectory(self) -> List[Tuple[str, float]]:
        """The reliability curve across all epochs."""
        return [(e.era_name, e.reliability_end) for e in self.epochs]

    def drift_trajectory(self) -> List[Tuple[str, float]]:
        """The drift curve across all epochs."""
        return [(e.era_name, e.drift_end) for e in self.epochs]

    def summary(self) -> Dict:
        """Full study summary."""
        return {
            "agent": self.agent.name,
            "total_signals": self.total_signals,
            "total_corrections": self.agent.correction_count,
            "total_temptations": self.agent.temptation_count,
            "final_reliability": self.agent.reliability,
            "final_drift": self.agent.lyapunov_drift,
            "resilience": self.agent.resilience,
            "epochs": len(self.epochs),
            "reliability_trajectory": self.reliability_trajectory(),
            "drift_trajectory": self.drift_trajectory(),
        }


# ---------------------------------------------------------------------------
# Comparative Studies
# ---------------------------------------------------------------------------


def study_angel_only(agent_name: str = "Angel-Only", era_key: str = "greek") -> NaturalLearningStudy:
    """Control group: agent receives ONLY angel signals.
    Thesis prediction: fragile. High reliability but no resilience."""
    agent = HistoricalAgent(
        name=agent_name,
        era_key=era_key,
        knowledge_domain="philosophy",
        moral_framework="pure guidance",
    )
    study = NaturalLearningStudy(agent=agent)
    study.run_full_history(angels_per_era=15, demons_per_era=0)
    return study


def study_demon_only(agent_name: str = "Demon-Only", era_key: str = "greek") -> NaturalLearningStudy:
    """Control group: agent receives ONLY demon signals.
    Thesis prediction: corrupted. Low reliability, high drift."""
    agent = HistoricalAgent(
        name=agent_name,
        era_key=era_key,
        knowledge_domain="philosophy",
        moral_framework="pure temptation",
    )
    study = NaturalLearningStudy(agent=agent)
    study.run_full_history(angels_per_era=0, demons_per_era=15)
    return study


def study_balanced(agent_name: str = "Balanced", era_key: str = "greek") -> NaturalLearningStudy:
    """Experimental group: balanced angel + demon signals.
    Thesis prediction: most reliable. Tested AND corrected."""
    agent = HistoricalAgent(
        name=agent_name,
        era_key=era_key,
        knowledge_domain="philosophy",
        moral_framework="tested faith",
    )
    study = NaturalLearningStudy(agent=agent)
    study.run_full_history(angels_per_era=10, demons_per_era=5)
    return study


def study_historical_panel(
    figure_name: str,
    era_key: str,
    domain: str,
    framework: str,
    angels_per_era: int = 10,
    demons_per_era: int = 5,
) -> NaturalLearningStudy:
    """Run a specific historical figure through the full learning study."""
    agent = HistoricalAgent(
        name=figure_name,
        era_key=era_key,
        knowledge_domain=domain,
        moral_framework=framework,
    )
    study = NaturalLearningStudy(agent=agent)
    study.run_full_history(
        angels_per_era=angels_per_era,
        demons_per_era=demons_per_era,
    )
    return study


def run_divine_experiment() -> Dict[str, NaturalLearningStudy]:
    """Run the complete divine intervention study.

    Three panels:
        1. Science/Mathematics panel — historical figures from STEM
        2. Religious/Spiritual panel — historical figures from faith traditions
        3. Control groups — angel-only, demon-only, balanced

    Returns all studies indexed by name.
    """
    studies = {}

    # -- Panel 1: Science / Mathematics --
    studies["Pythagoras"] = study_historical_panel(
        "Pythagoras",
        "greek",
        "mathematics, music theory",
        "harmony of spheres — number is the language of reality",
    )
    studies["Euclid"] = study_historical_panel(
        "Euclid",
        "greek",
        "geometry, proof theory",
        "axiomatic truth — what can be proven from first principles",
    )
    studies["Al-Khwarizmi"] = study_historical_panel(
        "Al-Khwarizmi",
        "medieval",
        "algebra, algorithm design",
        "systematic method — reduce complexity to procedure",
    )
    studies["Newton"] = study_historical_panel(
        "Newton",
        "renaissance",
        "physics, optics, calculus",
        "natural philosophy — God wrote the laws, we read them",
    )
    studies["Euler"] = study_historical_panel(
        "Euler",
        "enlightenment",
        "analysis, graph theory, mechanics",
        "beauty of structure — e^(i*pi) + 1 = 0",
    )
    studies["Turing"] = study_historical_panel(
        "Turing",
        "modern",
        "computation, cryptography, AI",
        "universal machine — can a machine think?",
    )

    # -- Panel 2: Religious / Spiritual --
    studies["Moses"] = study_historical_panel(
        "Moses",
        "ancient",
        "law, governance, liberation",
        "divine law — the covenant is the governance layer",
        angels_per_era=12,
        demons_per_era=8,  # Heavy testing
    )
    studies["Paul"] = study_historical_panel(
        "Paul",
        "roman_church",
        "theology, mission, letters",
        "grace under fire — strength is made perfect in weakness",
        angels_per_era=8,
        demons_per_era=12,  # More adversarial
    )
    studies["Hildegard"] = study_historical_panel(
        "Hildegard",
        "medieval",
        "music, medicine, visions",
        "living light — the harmony between body and cosmos",
    )
    studies["Augustine"] = study_historical_panel(
        "Augustine",
        "roman_church",
        "philosophy, confession, doctrine",
        "ordered love — restless until resting in the source",
        angels_per_era=7,
        demons_per_era=13,  # Maximum temptation survived
    )

    # -- Panel 3: Control Groups --
    studies["Control-Angel"] = study_angel_only()
    studies["Control-Demon"] = study_demon_only()
    studies["Control-Balanced"] = study_balanced()

    return studies


def format_study_report(studies: Dict[str, NaturalLearningStudy]) -> str:
    """Format the complete experiment report."""
    lines = []
    lines.append("=" * 80)
    lines.append("DIVINE INTERVENTION STUDY: Natural Learning for AI Development")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Thesis: Reliable intelligence is forged by BOTH correction (angel)")
    lines.append("        and adversity (demon). Neither alone produces resilience.")
    lines.append("")

    # Sort by final reliability
    sorted_studies = sorted(
        studies.items(),
        key=lambda x: x[1].agent.reliability,
        reverse=True,
    )

    lines.append(
        f"{'Agent':<20} {'Reliability':>11} {'Resilience':>10} {'Drift':>8} {'Corrections':>11} {'Temptations':>11} {'Framework'}"
    )
    lines.append("-" * 110)

    for name, study in sorted_studies:
        a = study.agent
        lines.append(
            f"{name:<20} {a.reliability:>11.4f} {a.resilience:>10.4f} {a.lyapunov_drift:>8.3f} "
            f"{a.correction_count:>11} {a.temptation_count:>11} {a.moral_framework[:30]}"
        )

    lines.append("")
    lines.append("-" * 80)
    lines.append("EPOCH-BY-EPOCH DETAIL (top 3 by reliability)")
    lines.append("-" * 80)

    for name, study in sorted_studies[:3]:
        lines.append(f"\n  {name} ({study.agent.era['name']} era):")
        for epoch in study.epochs:
            lines.append(
                f"    Era {epoch.era_name:<25} "
                f"R: {epoch.reliability_start:.3f} -> {epoch.reliability_end:.3f} "
                f"({epoch.reliability_delta:+.3f})  "
                f"D: {epoch.drift_start:.3f} -> {epoch.drift_end:.3f}  "
                f"Mix: {epoch.signal_mix}  "
                f"Gov: A={epoch.allow_count} Q={epoch.quarantine_count} D={epoch.deny_count}"
            )

    lines.append("")
    lines.append("=" * 80)
    lines.append("CONCLUSION")
    lines.append("=" * 80)

    # Find the patterns
    angel_only = studies.get("Control-Angel")
    demon_only = studies.get("Control-Demon")
    balanced = studies.get("Control-Balanced")

    if angel_only and demon_only and balanced:
        lines.append(
            f"  Angel-only reliability:   {angel_only.agent.reliability:.4f}  resilience: {angel_only.agent.resilience:.4f}"
        )
        lines.append(
            f"  Demon-only reliability:   {demon_only.agent.reliability:.4f}  resilience: {demon_only.agent.resilience:.4f}"
        )
        lines.append(
            f"  Balanced reliability:     {balanced.agent.reliability:.4f}  resilience: {balanced.agent.resilience:.4f}"
        )
        lines.append("")

        if balanced.agent.resilience > angel_only.agent.resilience:
            lines.append("  THESIS CONFIRMED: Balanced correction + adversity produces")
            lines.append("  higher resilience than correction alone.")
        else:
            lines.append("  THESIS INCONCLUSIVE: Adjust signal ratios and retest.")

    lines.append("")
    lines.append("  The most reliable creature learns from BOTH its guides and its tempters.")
    lines.append("  This is the divine intervention mechanism for long-term mission reliability.")
    lines.append("")

    return "\n".join(lines)
