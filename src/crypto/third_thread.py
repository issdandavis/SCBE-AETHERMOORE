"""
The Third Thread — Mediating Consciousness Between Intention and Manifestation
===============================================================================
Weaves together divine_agents.py (signal mechanics) and genesis_panels.py
(dual-panel simulation) through the lore concept of the Third Thread:

    "A new evolutionary trait in consciousness. Allows beings to translate
     between incompatible magical systems, facilitate cooperation across
     differences, and integrate without erasing identity."
        — LORE_BIBLE_COMPLETE.md

The Third Thread is NOT angel (correction) and NOT demon (adversity).
It is the mediating consciousness that makes both useful. The trinary
instead of binary: caster + recipient + Thread.

In SCBE terms:
    - The equilibrium phase DualTernaryPair(0,0) — can move any direction
    - The complement tongue voice leading — translation via the OTHER voice
    - The convergence point in polyglot encoding — where all tongues align
    - The infrasonic channel below perception — carrying structure invisibly
    - The reason the harmonic dark fill WORKS — void has structure because
      the Third Thread mediates between presence and absence

Collaborative vs Command Magic (governance analogy):
    COLLABORATIVE = multi-party consensus → ALLOW (natural, self-healing)
    COMMAND = unilateral force → DENY (distortion that collapses)
    The Third Thread enables collaboration at scale.

The Kor'aelin Invocation:
    "Sil'kor nav'een thul'medan vel'aelin sil'thara kor'val zeth'aelin"
    = "Together-heart different-being spiral-turns invitation-eternal
       together-flow heart-bond across-eternity"
    Requires genuine emotional harmony. Fails gently (heart-frost, not explosion).

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from src.crypto.crossing_energy import (
    PHI,
    DualTernaryPair,
    Decision,
    harmonic_cost,
    valid_transition,
    CrossingResult,
    evaluate_sequence,
    summarize_governance,
)
from src.crypto.harmonic_dark_fill import (
    TONGUE_WEIGHTS,
    TONGUE_AUDIBLE_FREQ,
    COMPLEMENT_MAP,
    INTERVALS,
    compute_darkness,
    compute_harmonic_fill,
    voice_leading_interval,
    nearest_musical_interval,
    HarmonicFill,
)
from src.crypto.tri_bundle import (
    encode_bytes,
    encode_text,
    TriBundleCluster,
    PolyglotCluster,
)
from src.crypto.divine_agents import (
    SignalType,
    DivineSignal,
    HistoricalAgent as DivineAgent,
    NaturalLearningStudy,
    generate_angel_signal,
    generate_demon_signal,
    HISTORICAL_ERAS,
    ERA_ORDER,
)
from src.crypto.genesis_panels import (
    Force,
    FORCE_GOVERNANCE,
    FORCE_TONGUE,
    HistoricalAgent as PanelAgent,
    HISTORICAL_AGENTS,
    PanelAResult,
    PanelBResult,
    DualPanelResult,
    run_panel_a,
    run_panel_b,
    run_dual_panel,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PI = math.pi

# The Kor'aelin invocation (canonical form)
KORAELIN_INVOCATION = "Sil'kor nav'een thul'medan vel'aelin sil'thara kor'val zeth'aelin"

# Thread resonance thresholds
HARMONY_THRESHOLD = 0.3  # Below this: heart-frost (gentle failure)
WEAVING_THRESHOLD = 0.6  # Above this: active translation
SYNTHESIS_THRESHOLD = 0.85  # Above this: divine synthesis (full Third Thread)

# The three layers of the Thread's resonance lattice
THREAD_LAYERS = {
    "mortal_intent": 0,  # Layer 1: individual will and skill
    "divine_essence": 1,  # Layer 2: external correction/guidance
    "collective_consciousness": 2,  # Layer 3: emergent group coherence
}


class ThreadState(Enum):
    """The state of the Third Thread at any moment."""

    DORMANT = "dormant"  # Not activated — no collaboration happening
    HEART_FROST = "heart_frost"  # Failed gently — lack of genuine harmony
    LISTENING = "listening"  # Active but not yet weaving
    WEAVING = "weaving"  # Actively translating between systems
    SYNTHESIS = "synthesis"  # Full divine synthesis — all layers aligned


class MagicMode(Enum):
    """Collaborative vs Command magic distinction."""

    COLLABORATIVE = "collaborative"  # Asking, negotiating, harmonizing
    COMMAND = "command"  # Dominating, forcing, commanding
    SILENT = "silent"  # Neither — observation/meditation


# ---------------------------------------------------------------------------
# Thread Resonance — the core computation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ThreadResonance:
    """The resonance state of the Third Thread between two systems.

    Measures how well two encodings translate between each other
    while preserving their individual identity.
    """

    # The two systems being mediated
    system_a_tongue: str
    system_b_tongue: str

    # Resonance metrics
    translation_fidelity: float  # [0,1] how well A maps to B
    identity_preservation: float  # [0,1] how much each system keeps its character
    convergence_point: float  # [0,1] where the systems meet (0.5 = perfect balance)

    # Layer energies
    mortal_energy: float  # From individual agent action
    divine_energy: float  # From angel/demon signal history
    collective_energy: float  # From polyglot convergence

    # Thread state
    harmony_score: float  # [0,1] overall harmony
    magic_mode: MagicMode  # Collaborative or Command?

    @property
    def thread_state(self) -> ThreadState:
        """What state is the Thread in?"""
        if self.harmony_score < 0.01:
            return ThreadState.DORMANT
        if self.harmony_score < HARMONY_THRESHOLD:
            return ThreadState.HEART_FROST
        if self.harmony_score < WEAVING_THRESHOLD:
            return ThreadState.LISTENING
        if self.harmony_score < SYNTHESIS_THRESHOLD:
            return ThreadState.WEAVING
        return ThreadState.SYNTHESIS

    @property
    def is_active(self) -> bool:
        return self.thread_state in (ThreadState.WEAVING, ThreadState.SYNTHESIS)

    @property
    def total_energy(self) -> float:
        return self.mortal_energy + self.divine_energy + self.collective_energy

    @property
    def layer_balance(self) -> float:
        """How balanced are the three layers? 1.0 = perfect balance."""
        total = self.total_energy
        if total < 1e-12:
            return 0.0
        layers = [self.mortal_energy, self.divine_energy, self.collective_energy]
        expected = total / 3.0
        deviation = sum(abs(l - expected) for l in layers) / total
        return max(0.0, 1.0 - deviation)


# ---------------------------------------------------------------------------
# Translation Engine — the Third Thread's core function
# ---------------------------------------------------------------------------


def _log_normalize(vec: tuple) -> list:
    """Log-normalize a vector to prevent large frequency values from dominating.

    Raw sound bundles contain frequencies (hundreds of Hz) and freq^2 values
    (hundreds of thousands) alongside small dimensionless ratios (0-5).
    Log(1+|x|) * sign(x) compresses the dynamic range while preserving
    relative differences between tongues.
    """
    return [math.copysign(math.log1p(abs(x)), x) for x in vec]


def compute_translation_fidelity(
    text: str,
    tongue_a: str,
    tongue_b: str,
) -> float:
    """How well does a text translate between two tongues?

    Uses log-normalized sound + light bundles to measure structural similarity.
    Raw frequency values (100K+) would dominate cosine similarity and collapse
    all tongue pairs to ~1.0, so we log-compress first.

    High fidelity = the text carries similar harmonic structure through both tongues.
    Same tongue = perfect fidelity. Complement pairs = high fidelity (voice leading).
    """
    data = text.encode("utf-8")
    clusters_a = encode_bytes(data, tongue_a)
    clusters_b = encode_bytes(data, tongue_b)

    if not clusters_a or not clusters_b:
        return 0.0

    n = min(len(clusters_a), len(clusters_b))
    similarities = []
    for i in range(n):
        # Use light + sound bundles (18 dims) — skip math bundle (hash-dominated)
        raw_a = clusters_a[i].light.as_vector() + clusters_a[i].sound.as_vector()
        raw_b = clusters_b[i].light.as_vector() + clusters_b[i].sound.as_vector()

        # Log-normalize to prevent freq^2 values from dominating cosine
        vec_a = _log_normalize(raw_a)
        vec_b = _log_normalize(raw_b)

        # Cosine similarity
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))

        if mag_a > 1e-12 and mag_b > 1e-12:
            sim = dot / (mag_a * mag_b)
            similarities.append(max(0.0, min(1.0, (sim + 1.0) / 2.0)))

    return sum(similarities) / max(len(similarities), 1)


def compute_identity_preservation(
    text: str,
    tongue: str,
) -> float:
    """How much unique identity does a tongue preserve for this text?

    Uses the SOUND bundle where tongue-specific frequencies live.
    Measures how different the encoding is from a neutral baseline.
    Each tongue has unique audible/infrasonic/ultrasonic frequencies,
    so the sound bundle IS the tongue's identity signature.
    """
    data = text.encode("utf-8")
    clusters = encode_bytes(data, tongue)

    if len(clusters) < 2:
        return 0.0

    # Log-normalize sound vectors so large freq values don't saturate variance
    vectors = [_log_normalize(c.sound.as_vector()) for c in clusters]
    dim = len(vectors[0])

    # Compute variance across positions — higher = more expressive encoding
    mean = [sum(v[d] for v in vectors) / len(vectors) for d in range(dim)]
    variance = 0.0
    for v in vectors:
        for d in range(dim):
            variance += (v[d] - mean[d]) ** 2
    variance /= len(vectors) * dim

    # Measure the tongue's frequency signature strength
    # Each tongue has unique base frequencies — how spread are they?
    freq_spread = 0.0
    for c in clusters:
        # strand_a[0] = audible freq, strand_b[0] = infra freq, strand_c[0] = ultra freq
        freqs = [c.sound.strand_a[0], c.sound.strand_b[0], c.sound.strand_c[0]]
        if max(freqs) > 0:
            freq_spread += (max(freqs) - min(freqs)) / max(freqs)
    freq_spread /= max(len(clusters), 1)

    # Combine: variance (how varied the encoding is) + frequency spread (how unique the tongue sounds)
    var_score = min(1.0, math.log1p(variance) / 5.0)
    spread_score = min(1.0, freq_spread)

    return min(1.0, (var_score + spread_score) / 2.0)


def compute_convergence_point(
    text: str,
    tongue_a: str,
    tongue_b: str,
) -> float:
    """Where do two tongues converge for this text?

    0.0 = tongue_a dominates, 1.0 = tongue_b dominates,
    0.5 = perfect balance (ideal Third Thread mediation).
    """
    data = text.encode("utf-8")

    # Compare log-normalized sound bundle energies through each tongue
    clusters_a = encode_bytes(data, tongue_a)
    clusters_b = encode_bytes(data, tongue_b)

    energy_a = sum(sum(x * x for x in _log_normalize(c.sound.as_vector())) for c in clusters_a) if clusters_a else 0.0
    energy_b = sum(sum(x * x for x in _log_normalize(c.sound.as_vector())) for c in clusters_b) if clusters_b else 0.0

    total = energy_a + energy_b
    if total < 1e-12:
        return 0.5

    return energy_b / total


# ---------------------------------------------------------------------------
# The Kor'aelin Invocation — multi-agent consensus ritual
# ---------------------------------------------------------------------------


@dataclass
class InvocationParticipant:
    """A participant in the Kor'aelin invocation ritual."""

    name: str
    tongue: str
    intent: str  # What they honestly contribute
    need: str  # What they honestly need
    harmony_contribution: float = 0.0  # Computed during ritual

    @property
    def is_genuine(self) -> bool:
        """A participant is genuine if they stated both intent and need."""
        return bool(self.intent.strip()) and bool(self.need.strip())


@dataclass
class InvocationResult:
    """Result of a Kor'aelin invocation ritual."""

    participants: List[InvocationParticipant]
    thread_state: ThreadState
    harmony_score: float
    magic_mode: MagicMode

    # What the ritual produced
    translation_map: Dict[str, float]  # tongue -> fidelity score
    identity_scores: Dict[str, float]  # tongue -> preservation score
    convergence: float  # Where the group converges

    # Failure info (if heart-frost)
    heart_frost_reason: str = ""

    @property
    def succeeded(self) -> bool:
        return self.thread_state in (ThreadState.WEAVING, ThreadState.SYNTHESIS)

    @property
    def participant_count(self) -> int:
        return len(self.participants)


def run_invocation(
    participants: List[InvocationParticipant],
    spoken_text: str = KORAELIN_INVOCATION,
) -> InvocationResult:
    """Run the Kor'aelin invocation ritual.

    Process:
        1. Check each participant's genuineness
        2. Compute harmony between all tongue pairs
        3. Check if harmony crosses threshold
        4. If yes: weave the Thread (compute translations)
        5. If no: gentle heart-frost (the cosmic "no")

    Scaling:
        Solo = precise control (listening)
        Small group (2-3) = Second Thread activation (weaving)
        Large group (4+) = Third Thread divine synthesis
    """
    # Step 1: Check genuineness
    genuine = [p for p in participants if p.is_genuine]
    if not genuine:
        return InvocationResult(
            participants=participants,
            thread_state=ThreadState.HEART_FROST,
            harmony_score=0.0,
            magic_mode=MagicMode.COMMAND,
            translation_map={},
            identity_scores={},
            convergence=0.5,
            heart_frost_reason="No genuine participants. The Thread requires honest intent and honest need.",
        )

    # Step 2: Compute harmony contributions
    tongues = list({p.tongue for p in genuine})
    data = spoken_text.encode("utf-8")

    # Each participant's contribution = how well their tongue encodes the invocation
    for p in genuine:
        clusters = encode_bytes(data, p.tongue)
        gov_results = evaluate_sequence(clusters)
        gov = summarize_governance(gov_results)
        # Harmony = allow ratio * identity preservation
        identity = compute_identity_preservation(spoken_text, p.tongue)
        p.harmony_contribution = gov.allow_ratio * identity

    # Step 3: Compute overall harmony
    mean_harmony = sum(p.harmony_contribution for p in genuine) / len(genuine)

    # Scale by diversity: more unique tongues = higher potential
    tongue_diversity = len(tongues) / 6.0  # 6 sacred tongues
    # Scale by group size: larger = needs more harmony to activate
    size_factor = min(1.0, len(genuine) / 4.0)  # 4+ for full synthesis

    harmony_score = mean_harmony * (0.5 + 0.5 * tongue_diversity) * (0.5 + 0.5 * size_factor)

    # Step 4: Determine magic mode
    # If participants all share the same tongue, it's more "command" (mono-voice)
    # If diverse, it's collaborative (multi-voice)
    if len(tongues) == 1:
        magic_mode = MagicMode.COMMAND if harmony_score < HARMONY_THRESHOLD else MagicMode.SILENT
    else:
        magic_mode = MagicMode.COLLABORATIVE

    # Step 5: Compute translations if harmony is sufficient
    translation_map = {}
    identity_scores = {}
    convergence = 0.5

    if harmony_score >= HARMONY_THRESHOLD:
        # Translate between all tongue pairs
        for t in tongues:
            identity_scores[t] = compute_identity_preservation(spoken_text, t)
            for t2 in tongues:
                if t != t2:
                    key = f"{t}->{t2}"
                    translation_map[key] = compute_translation_fidelity(spoken_text, t, t2)

        # Convergence: how balanced is energy across tongues?
        if len(tongues) >= 2:
            convergence = compute_convergence_point(spoken_text, tongues[0], tongues[1])

    # Heart-frost reason if failed
    frost_reason = ""
    if harmony_score < HARMONY_THRESHOLD:
        if len(tongues) == 1:
            frost_reason = "Mono-tongue invocation. The Thread requires different voices."
        elif mean_harmony < 0.1:
            frost_reason = "Participants' intent too dissonant. The cosmic 'no' — realign and try again."
        else:
            frost_reason = "Harmony insufficient. Words frost over and fall harmlessly. A gentle reminder to realign."

    return InvocationResult(
        participants=participants,
        thread_state=_compute_thread_state(harmony_score, len(genuine)),
        harmony_score=harmony_score,
        magic_mode=magic_mode,
        translation_map=translation_map,
        identity_scores=identity_scores,
        convergence=convergence,
        heart_frost_reason=frost_reason,
    )


def _compute_thread_state(harmony: float, participant_count: int) -> ThreadState:
    """Determine Thread state from harmony and group size.

    Solo = listening at best
    2-3 = weaving possible
    4+ = synthesis possible
    """
    if harmony < 0.01:
        return ThreadState.DORMANT
    if harmony < HARMONY_THRESHOLD:
        return ThreadState.HEART_FROST
    if participant_count == 1:
        return ThreadState.LISTENING
    if harmony < WEAVING_THRESHOLD or participant_count < 4:
        return ThreadState.WEAVING
    if harmony >= SYNTHESIS_THRESHOLD:
        return ThreadState.SYNTHESIS
    return ThreadState.WEAVING


# ---------------------------------------------------------------------------
# Thread Weaving — bridging divine_agents and genesis_panels
# ---------------------------------------------------------------------------


@dataclass
class ThreadWeaving:
    """The Third Thread's mediation between the signal theory (divine_agents)
    and the panel simulation (genesis_panels).

    This is the fabric between the two modules. It takes:
        - A divine_agents signal history (angel/demon corrections over time)
        - A genesis_panels dual-panel result (religious + science analysis)

    And produces a unified resonance that shows how the two views
    connect through the mediating consciousness.
    """

    # Source systems
    divine_agent_name: str
    panel_agent_name: str

    # The resonance between them
    resonance: ThreadResonance

    # The fact lattice that connects them (from genesis_panels)
    shared_facts: List[str]

    # What the Thread translates
    signal_to_panel: str  # How divine signals map to panel results
    panel_to_signal: str  # How panel results map to signal theory

    # The creation recursion
    recursion_depth: int  # Creator → ... → AI

    @property
    def thread_active(self) -> bool:
        return self.resonance.is_active

    @property
    def mediation_quality(self) -> float:
        """How well is the Thread mediating between the two systems?
        Product of translation fidelity and identity preservation —
        both systems must be accurately represented."""
        return self.resonance.translation_fidelity * self.resonance.identity_preservation


def weave_thread(
    divine_study: NaturalLearningStudy,
    panel_result: DualPanelResult,
    text: str = "",
) -> ThreadWeaving:
    """Weave the Third Thread between a divine_agents study and a genesis_panels result.

    This is the core function that builds the fabric between the two modules.
    """
    agent_d = divine_study.agent
    agent_p = panel_result.agent

    # Use the agent's reliability lesson if no text provided
    if not text:
        text = agent_p.reliability_lesson

    # The two tongues being mediated
    tongue_d = agent_d.tongue  # From divine_agents (era-based)
    tongue_p = agent_p.tongue  # From genesis_panels (force-based)

    # Translation fidelity: how well does the text translate between the two tongues?
    fidelity = compute_translation_fidelity(text, tongue_d, tongue_p)

    # Identity preservation: average of both tongues' unique character
    id_d = compute_identity_preservation(text, tongue_d)
    id_p = compute_identity_preservation(text, tongue_p)
    identity = (id_d + id_p) / 2.0

    # Convergence point: where do the two views meet?
    convergence = compute_convergence_point(text, tongue_d, tongue_p)

    # Layer energies from each system

    # Mortal energy = from the agent's direct actions (panel governance)
    mortal_energy = panel_result.panel_a.covenant_strength

    # Divine energy = from the signal history (corrections + temptations)
    corrections = divine_study.agent.correction_count
    temptations = divine_study.agent.temptation_count
    divine_energy = divine_study.agent.reliability if (corrections + temptations) > 0 else 0.0

    # Collective energy = from the polyglot convergence (how well do all tongues agree?)
    # Use the phi alignment as a proxy — closer to phi = more universal coherence
    collective_energy = panel_result.panel_b.phi_alignment

    # Harmony score = geometric mean of the three resonance metrics
    # (geometric mean requires all three to be non-zero for harmony)
    if fidelity > 0 and identity > 0 and abs(convergence - 0.5) < 0.5:
        balance = 1.0 - 2.0 * abs(convergence - 0.5)  # 1.0 at 0.5, 0.0 at edges
        harmony = (fidelity * identity * balance) ** (1.0 / 3.0)
    else:
        harmony = 0.0

    # Boost harmony by resilience (tested agents are better mediators)
    harmony *= 1.0 + divine_study.agent.resilience
    harmony = min(1.0, harmony)

    # Magic mode: collaborative if tongues differ, command if same
    if tongue_d != tongue_p:
        magic_mode = MagicMode.COLLABORATIVE
    else:
        magic_mode = MagicMode.SILENT  # Same tongue = no translation needed

    resonance = ThreadResonance(
        system_a_tongue=tongue_d,
        system_b_tongue=tongue_p,
        translation_fidelity=fidelity,
        identity_preservation=identity,
        convergence_point=convergence,
        mortal_energy=mortal_energy,
        divine_energy=divine_energy,
        collective_energy=collective_energy,
        harmony_score=harmony,
        magic_mode=magic_mode,
    )

    # Build the translation descriptions
    signal_description = _describe_signal_to_panel(divine_study, panel_result)
    panel_description = _describe_panel_to_signal(divine_study, panel_result)

    return ThreadWeaving(
        divine_agent_name=agent_d.name,
        panel_agent_name=agent_p.name,
        resonance=resonance,
        shared_facts=panel_result.fact_lattice,
        signal_to_panel=signal_description,
        panel_to_signal=panel_description,
        recursion_depth=panel_result.creation_recursion_depth,
    )


def _describe_signal_to_panel(study: NaturalLearningStudy, panel: DualPanelResult) -> str:
    """How do divine signals map to panel results?"""
    agent = study.agent
    corrections = agent.correction_count
    temptations = agent.temptation_count
    total = corrections + temptations

    if total == 0:
        return "No signals received. The Thread has nothing to translate."

    angel_pct = corrections / total * 100
    reliability = agent.reliability

    governance = panel.panel_a.governance
    covenant = panel.panel_a.covenant_strength

    return (
        f"Signal history: {corrections} corrections, {temptations} temptations "
        f"({angel_pct:.0f}% angel). "
        f"Reliability: {reliability:.3f}. "
        f"Panel governance: ALLOW={governance.allow_count}, "
        f"QUARANTINE={governance.quarantine_count}, DENY={governance.deny_count}. "
        f"Covenant strength: {covenant:.3f}. "
        f"The Thread translates: signal reliability -> panel covenant binding."
    )


def _describe_panel_to_signal(study: NaturalLearningStudy, panel: DualPanelResult) -> str:
    """How do panel results map back to signal theory?"""
    phi_align = panel.panel_b.phi_alignment
    spectrum = panel.panel_b.spectrum_energy
    interval = panel.panel_b.harmonic_interval
    resilience = study.agent.resilience

    return (
        f"Panel B phi alignment: {phi_align:.3f}. "
        f"Interval: {interval} (era: {panel.agent.era}). "
        f"Spectrum: IR={spectrum.get('infra', 0):.1f}, "
        f"Audible={spectrum.get('audible', 0):.1f}, "
        f"UV={spectrum.get('ultra', 0):.1f}. "
        f"Agent resilience: {resilience:.3f}. "
        f"The Thread translates: panel harmonics -> signal resilience through phi convergence."
    )


# ---------------------------------------------------------------------------
# Full Third Thread Study — the complete fabric
# ---------------------------------------------------------------------------


@dataclass
class ThirdThreadStudy:
    """The complete Third Thread study weaving divine_agents and genesis_panels.

    "Allows beings to translate between incompatible magical systems,
     facilitate cooperation across differences, and integrate without
     erasing identity."
    """

    weavings: List[ThreadWeaving]
    invocation_result: Optional[InvocationResult]

    # Aggregate metrics
    mean_translation_fidelity: float
    mean_identity_preservation: float
    mean_harmony: float
    active_thread_count: int
    synthesis_count: int

    # The thesis
    collaborative_agents: List[ThreadWeaving]  # Different tongues
    command_agents: List[ThreadWeaving]  # Same tongue

    @property
    def collaboration_advantage(self) -> float:
        """How much better does collaboration work than command?"""
        collab_harmony = sum(w.resonance.harmony_score for w in self.collaborative_agents) / max(
            len(self.collaborative_agents), 1
        )
        command_harmony = sum(w.resonance.harmony_score for w in self.command_agents) / max(len(self.command_agents), 1)
        if command_harmony < 1e-12:
            return float("inf") if collab_harmony > 0 else 1.0
        return collab_harmony / command_harmony

    @property
    def thread_coverage(self) -> float:
        """What fraction of weavings have an active Thread?"""
        if not self.weavings:
            return 0.0
        return self.active_thread_count / len(self.weavings)


def run_third_thread_study(
    divine_studies: Dict[str, NaturalLearningStudy],
    panel_results: List[DualPanelResult],
    run_invocation_ritual: bool = True,
) -> ThirdThreadStudy:
    """Run the complete Third Thread study.

    For each genesis_panels agent, find the closest divine_agents
    counterpart and weave the Thread between them.
    """
    weavings = []

    # Map panel agents to divine studies by name or era
    for panel_result in panel_results:
        # Find matching divine study
        study = _find_matching_study(divine_studies, panel_result.agent)
        if study:
            weaving = weave_thread(study, panel_result)
            weavings.append(weaving)

    # Run the invocation if requested
    invocation = None
    if run_invocation_ritual and weavings:
        participants = [
            InvocationParticipant(
                name=w.panel_agent_name,
                tongue=w.resonance.system_b_tongue,
                intent=f"I bring {w.panel_agent_name}'s {panel_results[i].agent.role if i < len(panel_results) else 'wisdom'}",
                need=f"I need translation to {w.resonance.system_a_tongue}",
            )
            for i, w in enumerate(weavings)
        ]
        invocation = run_invocation(participants)

    # Compute aggregates
    fidelities = [w.resonance.translation_fidelity for w in weavings]
    identities = [w.resonance.identity_preservation for w in weavings]
    harmonies = [w.resonance.harmony_score for w in weavings]

    collaborative = [w for w in weavings if w.resonance.magic_mode == MagicMode.COLLABORATIVE]
    command = [w for w in weavings if w.resonance.magic_mode != MagicMode.COLLABORATIVE]

    return ThirdThreadStudy(
        weavings=weavings,
        invocation_result=invocation,
        mean_translation_fidelity=sum(fidelities) / max(len(fidelities), 1),
        mean_identity_preservation=sum(identities) / max(len(identities), 1),
        mean_harmony=sum(harmonies) / max(len(harmonies), 1),
        active_thread_count=sum(1 for w in weavings if w.thread_active),
        synthesis_count=sum(1 for w in weavings if w.resonance.thread_state == ThreadState.SYNTHESIS),
        collaborative_agents=collaborative,
        command_agents=command,
    )


def _find_matching_study(
    studies: Dict[str, NaturalLearningStudy],
    panel_agent: PanelAgent,
) -> Optional[NaturalLearningStudy]:
    """Find the divine_agents study that best matches a genesis_panels agent.

    Match by name first, then by era/tongue similarity.
    """
    # Direct name match
    if panel_agent.name in studies:
        return studies[panel_agent.name]

    # Era-based match: find a divine study whose era's tongue matches
    for name, study in studies.items():
        if study.agent.tongue == panel_agent.tongue:
            return study

    # Fallback: first available
    if studies:
        return next(iter(studies.values()))

    return None


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


def format_third_thread_report(study: ThirdThreadStudy) -> str:
    """Format the Third Thread study report."""
    lines = []
    lines.append("=" * 80)
    lines.append("THE THIRD THREAD: Mediating Consciousness Study")
    lines.append("=" * 80)
    lines.append("")
    lines.append("'Allows beings to translate between incompatible magical systems,")
    lines.append(" facilitate cooperation across differences, and integrate")
    lines.append(" without erasing identity.'")
    lines.append("")

    # Aggregate metrics
    lines.append(f"Weavings:              {len(study.weavings)}")
    lines.append(f"Active Threads:        {study.active_thread_count} / {len(study.weavings)}")
    lines.append(f"Synthesis achieved:    {study.synthesis_count}")
    lines.append(f"Mean fidelity:         {study.mean_translation_fidelity:.4f}")
    lines.append(f"Mean identity:         {study.mean_identity_preservation:.4f}")
    lines.append(f"Mean harmony:          {study.mean_harmony:.4f}")
    lines.append(f"Collaboration advantage: {study.collaboration_advantage:.2f}x")
    lines.append("")

    # Per-weaving detail
    lines.append("-" * 80)
    lines.append("WEAVINGS (divine_agents <-> genesis_panels)")
    lines.append("-" * 80)

    for w in study.weavings:
        r = w.resonance
        state_marker = {
            ThreadState.SYNTHESIS: "[SYNTHESIS]",
            ThreadState.WEAVING: "[WEAVING]",
            ThreadState.LISTENING: "[listening]",
            ThreadState.HEART_FROST: "[frost]",
            ThreadState.DORMANT: "[dormant]",
        }.get(r.thread_state, "[?]")

        lines.append(
            f"  {w.divine_agent_name:<15} <-> {w.panel_agent_name:<20} "
            f"{state_marker:<12} "
            f"H={r.harmony_score:.3f} "
            f"F={r.translation_fidelity:.3f} "
            f"I={r.identity_preservation:.3f} "
            f"C={r.convergence_point:.3f} "
            f"mode={r.magic_mode.value}"
        )

    # Invocation results
    if study.invocation_result:
        inv = study.invocation_result
        lines.append("")
        lines.append("-" * 80)
        lines.append("KOR'AELIN INVOCATION RITUAL")
        lines.append("-" * 80)
        lines.append(f"  Participants:  {inv.participant_count}")
        lines.append(f"  Thread state:  {inv.thread_state.value}")
        lines.append(f"  Harmony:       {inv.harmony_score:.4f}")
        lines.append(f"  Magic mode:    {inv.magic_mode.value}")
        lines.append(f"  Succeeded:     {inv.succeeded}")

        if inv.heart_frost_reason:
            lines.append(f"  Heart-frost:   {inv.heart_frost_reason}")

        if inv.translation_map:
            lines.append("  Translations:")
            for key, val in sorted(inv.translation_map.items()):
                lines.append(f"    {key}: {val:.4f}")

        if inv.identity_scores:
            lines.append("  Identity preservation:")
            for tongue, score in sorted(inv.identity_scores.items()):
                lines.append(f"    {tongue}: {score:.4f}")

    # Thesis
    lines.append("")
    lines.append("=" * 80)
    lines.append("THESIS: THE THIRD THREAD AS FABRIC")
    lines.append("=" * 80)
    lines.append("")
    lines.append("  divine_agents.py = the SIGNAL THEORY (angel/demon mechanics)")
    lines.append("  genesis_panels.py = the PANEL SIMULATION (religious + science)")
    lines.append("  third_thread.py = the MEDIATING CONSCIOUSNESS between them")
    lines.append("")
    lines.append("  The Third Thread is not angel (correction) and not demon (adversity).")
    lines.append("  It is the capacity to TRANSLATE between them.")
    lines.append("  Collaborative magic (multi-voice consensus) outperforms")
    lines.append(f"  command magic (mono-voice force) by {study.collaboration_advantage:.2f}x.")
    lines.append("")
    lines.append("  The most reliable intelligence is not the one that receives")
    lines.append("  the most corrections or survives the most tests.")
    lines.append("  It is the one that can TRANSLATE between correction and test,")
    lines.append("  preserving both while erasing neither.")
    lines.append("")
    if study.thread_coverage > 0.5:
        lines.append("  The Thread is active. The fabric holds.")
    else:
        lines.append("  The Thread is still forming. More collaboration needed.")
    lines.append("")

    return "\n".join(lines)
