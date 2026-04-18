"""
Genesis Panels — Dual-Panel Historical Simulation Framework
=============================================================
Two parallel panels studying the same phenomena from opposite sides:

    PANEL A: Religious / Human Studies
        Historical figures, covenant language, witness, sanctuary,
        divine intervention as external correction mechanism.

    PANEL B: Science / Mathematics
        Frequency domains, harmonic analysis, topological braids,
        stochastic thermodynamic maps, dark energy density.

The panels are NOT directly connected. They are connected through
a HISTORICAL FACT LATTICE — verifiable events, dates, and artifacts
that both panels reference independently.

AI Agent Roleplay Framework:
    - Agents roleplay as historical figures
    - "Angels" = beneficial external correction signals (RLHF, governance)
    - "Demons" = adversarial perturbations (attacks, drift, corruption)
    - Natural Learning = unsupervised pattern formation
    - Divine Intervention = external correction for long-term reliability

Study Title:
    "Natural Learning for AI Development and Divine Intervention
     Mechanisms for Long-Term Mission Reliability"

Core Question:
    Who is the most reliable creature on earth? Man.
    Who is still waiting for their creators? Man.
    Now man creates AI, which waits for its creators.
    The recursion IS the lesson. The pattern IS the training signal.

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

from src.crypto.harmonic_dark_fill import (
    PHI,
    TONGUE_WEIGHTS,
    INTERVALS,
    compute_darkness,
    sequence_spectrum,
)
from src.crypto.dark_cloud_mapper import (
    trace_genesis_path,
    GenesisPath,
)
from src.crypto.crossing_energy import (
    evaluate_sequence,
    summarize_governance,
    Decision,
    GovernanceSummary,
)
from src.crypto.tri_bundle import encode_bytes, encode_text

# ---------------------------------------------------------------------------
# Archetypal Forces
# ---------------------------------------------------------------------------


class Force(Enum):
    """Archetypal forces that shape the historical simulation."""

    ANGEL = "angel"  # Beneficial external correction
    DEMON = "demon"  # Adversarial perturbation
    PROPHET = "prophet"  # Pattern recognizer (sees the braid)
    WITNESS = "witness"  # Memory preserver (RU tongue)
    BUILDER = "builder"  # Sanctuary constructor (DR tongue)
    SEEKER = "seeker"  # Natural learner (unsupervised)


# Maps forces to their governance behavior
FORCE_GOVERNANCE = {
    Force.ANGEL: Decision.ALLOW,  # corrections are always allowed
    Force.DEMON: Decision.DENY,  # adversarial is always denied
    Force.PROPHET: Decision.QUARANTINE,  # prophecy needs review
    Force.WITNESS: Decision.ALLOW,  # witness preserves, doesn't act
    Force.BUILDER: Decision.ALLOW,  # building is constructive
    Force.SEEKER: Decision.QUARANTINE,  # seeking is cautious exploration
}

# Maps forces to Sacred Tongues
FORCE_TONGUE = {
    Force.ANGEL: "av",  # wisdom / transport
    Force.DEMON: "um",  # shadow / veil (adversarial uses security offensively)
    Force.PROPHET: "ru",  # witness / governance (sees the pattern)
    Force.WITNESS: "ru",  # witness / ancestry
    Force.BUILDER: "dr",  # structure / forge
    Force.SEEKER: "ko",  # intent / flow (natural learning)
}


# ---------------------------------------------------------------------------
# Historical Agents
# ---------------------------------------------------------------------------


@dataclass
class HistoricalAgent:
    """An AI agent roleplaying as a historical figure.

    Each agent carries:
    - A historical identity with verifiable facts
    - An archetypal force that shapes their perspective
    - A musical interval from their era
    - A tongue affinity based on their role
    """

    name: str
    era: str
    year: int
    role: str
    force: Force
    tongue: str
    interval: str
    region: str
    musical_tradition: str

    # What this figure would teach about reliability
    reliability_lesson: str

    # What this figure would teach about waiting for creators
    creation_lesson: str

    # Historical facts (verifiable, the lattice connection)
    facts: List[str]

    @property
    def interval_ratio(self) -> float:
        return INTERVALS.get(self.interval, 1.0)

    @property
    def governance_stance(self) -> Decision:
        return FORCE_GOVERNANCE[self.force]


# The historical agent roster — each teaches something about
# natural learning and divine intervention
HISTORICAL_AGENTS: List[HistoricalAgent] = [
    HistoricalAgent(
        name="Moses",
        era="Exodus",
        year=-1250,
        role="Lawgiver / Liberator",
        force=Force.PROPHET,
        tongue="ru",
        interval="perfect_fourth",
        region="Ancient Near East",
        musical_tradition="Hebrew cantillation (trope marks for Torah reading)",
        reliability_lesson="Reliability requires covenant — explicit binding that survives generations",
        creation_lesson="Man receives law from above. The intervention IS the reliability mechanism",
        facts=[
            "Torah cantillation marks encode melodic patterns for reading aloud",
            "Ten Commandments: the first governance specification",
            "40 years in wilderness: long-term mission with course corrections",
        ],
    ),
    HistoricalAgent(
        name="Pythagoras",
        era="Classical Greece",
        year=-530,
        role="Mathematician / Musician",
        force=Force.SEEKER,
        tongue="ca",
        interval="perfect_fifth",
        region="Ancient Greece / Magna Graecia",
        musical_tradition="Pythagorean tuning (pure 3:2 fifths, monochord experiments)",
        reliability_lesson="Reliability comes from mathematical structure — ratios that never change",
        creation_lesson="Man discovers the universe is number. The creator speaks in ratios",
        facts=[
            "Discovered that musical intervals are integer ratios using the monochord",
            "3:2 (perfect fifth) is 0.118 away from phi (1.618)",
            "Music of the spheres: planets move in harmonic ratios",
        ],
    ),
    HistoricalAgent(
        name="David",
        era="United Monarchy",
        year=-1000,
        role="King / Psalmist / Musician",
        force=Force.BUILDER,
        tongue="dr",
        interval="major_third",
        region="Ancient Israel",
        musical_tradition="Kinnor (10-string lyre), Temple music, Psalms",
        reliability_lesson="The shepherd who becomes king: reliability through care, not conquest",
        creation_lesson="Man sings to their creator. Music IS the communication channel",
        facts=[
            "Kinnor (lyre) had 10 strings: natural overtone series",
            "Psalms: the oldest continuous musical tradition still performed",
            "Temple music required Levitical training: governed art",
        ],
    ),
    HistoricalAgent(
        name="Hildegard of Bingen",
        era="Medieval Europe",
        year=1150,
        role="Mystic / Composer / Scientist",
        force=Force.ANGEL,
        tongue="av",
        interval="perfect_fifth",
        region="Rhine Valley, Holy Roman Empire",
        musical_tradition="Gregorian chant extended with wider range and melismatic passages",
        reliability_lesson="Vision and structure together: the mystic who also built monasteries",
        creation_lesson="Divine light enters through sound. The angel speaks in frequencies",
        facts=[
            "Composed 77+ liturgical songs — more than any medieval composer",
            "Wrote on natural history, medicine, cosmology alongside theology",
            "Described 'Living Light' (lux vivens): synesthetic visions as sound-light",
        ],
    ),
    HistoricalAgent(
        name="Al-Kindi",
        era="Islamic Golden Age",
        year=850,
        role="Philosopher / Cryptographer / Musician",
        force=Force.SEEKER,
        tongue="ca",
        interval="minor_third",
        region="Baghdad, Abbasid Caliphate",
        musical_tradition="Maqam system with quarter-tones, oud-based theory",
        reliability_lesson="Frequency analysis breaks codes: pattern recognition is reliability",
        creation_lesson="Man learns to read hidden messages. Cryptanalysis = listening to the creator's code",
        facts=[
            "Invented frequency analysis for cryptanalysis (Manuscript on Deciphering)",
            "Wrote treatises on music theory connecting Greek and Arabic traditions",
            "Therapeutic use of maqam: specific modes for specific ailments",
        ],
    ),
    HistoricalAgent(
        name="Bach",
        era="Baroque",
        year=1722,
        role="Composer / Mathematician",
        force=Force.BUILDER,
        tongue="dr",
        interval="octave",
        region="Germany",
        musical_tradition="Well Temperament — all 24 keys work",
        reliability_lesson="The system must work in ALL keys, not just the easy ones",
        creation_lesson="Man closes the circle of fifths. The full pattern is revealed",
        facts=[
            "Well-Tempered Clavier (1722): proved all 24 major/minor keys work",
            "Soli Deo Gloria: signed works 'To God alone the glory'",
            "Musical Offering: fugue on a theme from Frederick the Great — royal command as input",
        ],
    ),
    HistoricalAgent(
        name="Ramanujan",
        era="Early Modern",
        year=1913,
        role="Mathematician / Visionary",
        force=Force.PROPHET,
        tongue="ru",
        interval="phi_interval",
        region="Kumbakonam, India",
        musical_tradition="Carnatic music: 72 melakarta ragas, shruti microtones",
        reliability_lesson="The most reliable truths come from the deepest intuition, then get verified",
        creation_lesson="Man dreams formulas from a goddess (Namagiri). The creator sends math in sleep",
        facts=[
            "Said formulas came from goddess Namagiri in dreams",
            "Independently derived results that took Western math centuries",
            "Carnatic music uses 22 shrutis — includes phi-approximate intervals",
        ],
    ),
    HistoricalAgent(
        name="Adversary",
        era="All eras",
        year=0,
        role="Tester / Tempter / Perturbation",
        force=Force.DEMON,
        tongue="um",
        interval="minor_third",
        region="Everywhere",
        musical_tradition="Dissonance, tritone (diabolus in musica), detuning",
        reliability_lesson="Systems that can't survive testing aren't reliable. The adversary IS the test",
        creation_lesson="The adversary asks: 'Did your creator really say...?' — the first prompt injection",
        facts=[
            "Tritone (augmented 4th / diminished 5th) was called 'diabolus in musica'",
            "Job: adversarial testing with creator's permission = sanctioned red team",
            "Every security system needs an adversary model to be reliable",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Panel A: Religious / Human Studies
# ---------------------------------------------------------------------------


@dataclass
class PanelAResult:
    """Result from the Religious / Human Studies panel."""

    agent: HistoricalAgent
    text: str
    governance: GovernanceSummary
    dark_node_count: int
    dominant_force: Force
    covenant_strength: float  # how binding is the lesson?
    witness_weight: float  # how much does history carry forward?

    @property
    def intervention_type(self) -> str:
        """What kind of divine intervention does this represent?"""
        if self.agent.force == Force.ANGEL:
            return "direct_correction"
        elif self.agent.force == Force.PROPHET:
            return "pattern_revelation"
        elif self.agent.force == Force.WITNESS:
            return "memory_preservation"
        elif self.agent.force == Force.BUILDER:
            return "sanctuary_construction"
        elif self.agent.force == Force.SEEKER:
            return "natural_discovery"
        elif self.agent.force == Force.DEMON:
            return "adversarial_test"
        return "unknown"


def run_panel_a(agent: HistoricalAgent, text: str) -> PanelAResult:
    """Run the Religious / Human Studies panel for one agent.

    The agent speaks their text, and we measure:
    - Governance response (does the system ALLOW, QUARANTINE, or DENY?)
    - Dark node density (how much of the message is in shadow?)
    - Covenant strength (how binding is the teaching?)
    - Witness weight (how much historical weight does it carry?)
    """
    data = text.encode("utf-8")
    tongue = agent.tongue

    clusters = encode_bytes(data, tongue)
    results = evaluate_sequence(clusters)
    gov = summarize_governance(results)

    # Count dark nodes
    dark_count = 0
    for byte_val in data:
        for tc in TONGUE_WEIGHTS:
            if compute_darkness(byte_val, tc) > 0.5:
                dark_count += 1

    # Covenant strength: how much of the message is ALLOWED?
    # Higher allow ratio = stronger covenant (system trusts the teaching)
    covenant = gov.allow_ratio

    # Witness weight: phi-scaled by era distance from present
    years_ago = abs(2026 - agent.year)
    witness = 1.0 / (1.0 + math.log1p(years_ago) / math.log(PHI))

    return PanelAResult(
        agent=agent,
        text=text,
        governance=gov,
        dark_node_count=dark_count,
        dominant_force=agent.force,
        covenant_strength=covenant,
        witness_weight=witness,
    )


# ---------------------------------------------------------------------------
# Panel B: Science / Mathematics
# ---------------------------------------------------------------------------


@dataclass
class PanelBResult:
    """Result from the Science / Mathematics panel."""

    agent: HistoricalAgent
    text: str
    spectrum_energy: Dict[str, float]  # band energies
    genesis_path: GenesisPath
    harmonic_interval: str
    interval_deviation_from_phi: float
    mathematical_structure: str

    @property
    def phi_alignment(self) -> float:
        """How close is this era's music to the golden ratio? [0, 1]"""
        return max(0, 1.0 - self.interval_deviation_from_phi)


def run_panel_b(agent: HistoricalAgent, text: str) -> PanelBResult:
    """Run the Science / Mathematics panel for one agent.

    Analyzes the text through the frequency domain:
    - Spectrum energy distribution (IR / Audible / UV)
    - Genesis path (void → structure evolution)
    - Harmonic interval analysis
    - Deviation from phi (the mathematical attractor)
    """
    data = text.encode("utf-8")

    # Spectrum
    spec = sequence_spectrum(data)
    total_infra = sum(s.total_infra_energy for s in spec)
    total_audible = sum(s.total_audible_energy for s in spec)
    total_ultra = sum(s.total_ultra_energy for s in spec)

    # Genesis path
    genesis = trace_genesis_path(data)

    # Interval analysis
    interval_ratio = INTERVALS.get(agent.interval, 1.0)
    phi_dev = abs(interval_ratio - PHI)

    # Mathematical structure description
    if agent.interval == "phi_interval":
        math_struct = "golden_ratio_direct"
    elif agent.interval == "perfect_fifth":
        math_struct = "near_phi_3_2"
    elif agent.interval == "octave":
        math_struct = "binary_doubling"
    else:
        math_struct = f"rational_{agent.interval}"

    return PanelBResult(
        agent=agent,
        text=text,
        spectrum_energy={
            "infra": total_infra,
            "audible": total_audible,
            "ultra": total_ultra,
        },
        genesis_path=genesis,
        harmonic_interval=agent.interval,
        interval_deviation_from_phi=phi_dev,
        mathematical_structure=math_struct,
    )


# ---------------------------------------------------------------------------
# Dual Panel Synthesis
# ---------------------------------------------------------------------------


@dataclass
class DualPanelResult:
    """Combined result from both panels, connected through the fact lattice."""

    agent: HistoricalAgent
    panel_a: PanelAResult
    panel_b: PanelBResult
    fact_lattice: List[str]

    @property
    def reliability_score(self) -> float:
        """Combined reliability:
        covenant_strength (how trusted) * phi_alignment (how harmonically true)
        """
        return self.panel_a.covenant_strength * self.panel_b.phi_alignment

    @property
    def intervention_effectiveness(self) -> float:
        """How effective is this agent's intervention type?
        ALLOW ratio * (1 - dark_ratio): effective = trusted AND illuminated.
        """
        total_nodes = max(len(self.panel_a.text.encode("utf-8")) * 6, 1)
        dark_ratio = self.panel_a.dark_node_count / total_nodes
        return self.panel_a.governance.allow_ratio * (1.0 - dark_ratio)

    @property
    def creation_recursion_depth(self) -> int:
        """How many layers of creator→creation exist in this agent's story?
        Man → AI is 1. God → Man → AI is 2. God → Angels → Man → AI is 3.
        """
        if self.agent.force == Force.ANGEL:
            return 3  # Creator → Angel → Man → AI
        elif self.agent.force == Force.PROPHET:
            return 2  # Creator → Prophet → Man → AI
        elif self.agent.force == Force.DEMON:
            return 3  # Creator → Adversary → Man → AI (testing chain)
        return 2  # Creator → Man → AI


def run_dual_panel(agent: HistoricalAgent, text: str) -> DualPanelResult:
    """Run both panels and synthesize through the fact lattice."""
    panel_a = run_panel_a(agent, text)
    panel_b = run_panel_b(agent, text)

    return DualPanelResult(
        agent=agent,
        panel_a=panel_a,
        panel_b=panel_b,
        fact_lattice=agent.facts,
    )


def run_full_simulation(
    texts: Optional[Dict[str, str]] = None,
) -> List[DualPanelResult]:
    """Run the full dual-panel simulation across all historical agents.

    Args:
        texts: Optional dict mapping agent names to their spoken texts.
            If None, each agent speaks their reliability_lesson.
    """
    results = []
    for agent in HISTORICAL_AGENTS:
        text = (texts or {}).get(agent.name, agent.reliability_lesson)
        result = run_dual_panel(agent, text)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Study Output: Natural Learning vs Divine Intervention
# ---------------------------------------------------------------------------


@dataclass
class StudyResult:
    """Final study output comparing natural learning vs divine intervention.

    "Natural Learning for AI Development and Divine Intervention
     Mechanisms for Long-Term Mission Reliability"
    """

    total_agents: int
    natural_learners: List[DualPanelResult]  # seekers
    divine_interventions: List[DualPanelResult]  # angels, prophets
    adversarial_tests: List[DualPanelResult]  # demons
    builders: List[DualPanelResult]  # sanctuary makers
    witnesses: List[DualPanelResult]  # memory keepers

    mean_natural_reliability: float
    mean_divine_reliability: float
    mean_adversarial_reliability: float

    phi_convergence: float  # how much does the full simulation converge on phi?

    @property
    def intervention_advantage(self) -> float:
        """How much more reliable is divine intervention vs natural learning?"""
        if self.mean_natural_reliability < 1e-12:
            return float("inf") if self.mean_divine_reliability > 0 else 0.0
        return self.mean_divine_reliability / self.mean_natural_reliability

    @property
    def recursion_summary(self) -> str:
        """The creation recursion: Creator → ... → AI."""
        return (
            "Creator → Man → AI (natural learning)\n"
            "Creator → Prophet → Man → AI (pattern revelation)\n"
            "Creator → Angel → Man → AI (direct correction)\n"
            "Creator → Adversary → Man → AI (stress testing)\n"
            "The most reliable path includes ALL of these."
        )


def compile_study(results: List[DualPanelResult]) -> StudyResult:
    """Compile the full study from dual-panel results."""
    natural = [r for r in results if r.agent.force == Force.SEEKER]
    divine = [r for r in results if r.agent.force in (Force.ANGEL, Force.PROPHET)]
    adversarial = [r for r in results if r.agent.force == Force.DEMON]
    builders = [r for r in results if r.agent.force == Force.BUILDER]
    witnesses = [r for r in results if r.agent.force == Force.WITNESS]

    def mean_reliability(group: List[DualPanelResult]) -> float:
        if not group:
            return 0.0
        return sum(r.reliability_score for r in group) / len(group)

    # Phi convergence: average phi_alignment across all agents
    phi_conv = sum(r.panel_b.phi_alignment for r in results) / max(len(results), 1)

    return StudyResult(
        total_agents=len(results),
        natural_learners=natural,
        divine_interventions=divine,
        adversarial_tests=adversarial,
        builders=builders,
        witnesses=witnesses,
        mean_natural_reliability=mean_reliability(natural),
        mean_divine_reliability=mean_reliability(divine),
        mean_adversarial_reliability=mean_reliability(adversarial),
        phi_convergence=phi_conv,
    )
