"""
Symphonic Governor — Tonal Multi-Scalar Training Grader
=======================================================

Stages AI-to-AI training reviews using music theory chorded structures
mapped to the 6D Langues Metric tensor field. Each interaction is graded
on a "sheet music" where the Six Sacred Tongues provide tonal positions
and the Langues Metric provides harmonic cost.

Architecture:
  1. Six Sacred Tongues (KO, AV, RU, CA, UM, DR) → 6 "strings"
  2. Langues Metric L(x,t) → tonal cost per string
  3. Musical intervals (unison through major sixth) → chord voicing
  4. Dual Ternary (9-state) → multi-scalar grade (+1, 0, -1)
  5. Gate Swap (tri-manifold) → governance decision
  6. Stellar Octave Mapping → pi-rhythmic LR modulation
  7. Flux Contraction → dissonance correction

Multi-Scalar Grading (Balanced Ternary):
  +1 (PLUS)  = Positive / Major Chord / PAR_ACTIVATE → Reinforce
   0 (ZERO)  = Neutral / Unison / PAR_NEUTRAL → Hold
  -1 (MINUS) = Negative / Dissonant Tritone / PAR_INHIBIT → Contract

Pi-Rhythmic Cycle Review:
  Every pi-radians of simulated time, the governor produces a
  "Resonance Report" — a snapshot of the 6-string chord state,
  harmonic stability, and stellar synchronization.

@module training/symphonic_governor
@layer Layer 9, 12, 13, 14
@component Symphonic Multi-Scalar Grading Engine
@version 1.0.0
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ── SCBE Constants (canonical, from langues_metric.py) ──────────────────────

PHI = (1 + math.sqrt(5)) / 2
TAU = 2 * math.pi

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = [PHI**k for k in range(6)]
TONGUE_PHASES = [TAU * k / 6 for k in range(6)]
TONGUE_FREQUENCIES = [1.0, 9 / 8, 5 / 4, 4 / 3, 3 / 2, 5 / 3]

DIMENSIONS = ["time", "intent", "policy", "trust", "risk", "entropy"]
L_BASE = sum(TONGUE_WEIGHTS)  # ~12.09

# ── Musical Interval Ratios (just intonation) ───────────────────────────────

INTERVAL_NAMES = [
    "Unison",  # KO  1:1
    "Major Second",  # AV  9:8
    "Major Third",  # RU  5:4
    "Perfect Fourth",  # CA  4:3
    "Perfect Fifth",  # UM  3:2
    "Major Sixth",  # DR  5:3
]

# Chord Templates (indices into the 6-string array)
CHORD_MAJOR = [0, 2, 4]  # KO-RU-UM (1, 3, 5) — stable/positive
CHORD_MINOR = [0, 2, 5]  # KO-RU-DR (1, 3, 6) — reflective/neutral
CHORD_DIMINISHED = [1, 3, 5]  # AV-CA-DR — dissonant/negative
CHORD_POWER = [0, 4]  # KO-UM (1, 5) — minimal/assertive

# ── Stellar Octave Constants (from stellar_octave_mapping.py) ────────────────

SUN_P_MODE_HZ = 0.003  # Solar 5-min oscillation
STELLAR_OCTAVE_TARGET = 196.0  # G3 (transposed solar frequency)
STELLAR_MODULATION_DEPTH = 0.2  # ±20% LR modulation


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class StringVoice:
    """State of a single 'string' in the 6-string tonal system."""

    tongue: str
    dimension: str
    weight: float
    frequency: float
    phase: float
    cost: float  # L contribution from this tongue
    deviation: float  # d_l distance from ideal
    phase_shift: float  # sin(omega * t + phi)
    trit: int  # -1, 0, or +1 quantized grade


@dataclass
class ChordState:
    """Chord voicing across the 6-string system."""

    chord_name: str
    chord_indices: List[int]
    chord_cost: float  # sum of costs at chord tones
    consonance: float  # [0, 1] harmonic alignment
    root_tongue: str


@dataclass
class ResonanceReport:
    """Pi-rhythmic cycle review — produced every pi radians of sim time."""

    cycle_number: int
    phase_radians: float  # current phase in radians
    phase_pi: float  # phase / pi (human-readable)
    strings: List[StringVoice]
    chord: ChordState
    total_L: float  # full 6D Langues Metric value
    grade: int  # +1, 0, -1
    grade_label: str  # "POSITIVE", "NEUTRAL", "NEGATIVE"
    decision: str  # ALLOW, QUARANTINE, DENY
    stellar_envelope: float  # stellar pulse modulation factor
    stellar_sync: str  # "SYNCHRONIZED" or "DAMPENED"
    effective_lr: float  # modulated learning rate
    flux_state: str  # "POLLY", "QUASI", "DEMI", "COLLAPSED"
    timestamp: float


@dataclass
class TrainingBatchResult:
    """Result of a training batch (control or test)."""

    batch_name: str
    mode: str
    reports: List[ResonanceReport]
    total_updates: int
    skipped_updates: int
    contracted_updates: int
    mean_L: float
    mean_consonance: float
    grade_distribution: Dict[str, int]
    decision_distribution: Dict[str, int]


# =============================================================================
# Core Engine
# =============================================================================


class SymphonicGovernor:
    """Tonal Multi-Scalar Grading Engine for AI-to-AI training.

    Integrates:
    - LanguesMetric (6D cost function)
    - Musical interval theory (chorded structures)
    - DualTernary (9-state grading)
    - GateSwap (tri-manifold governance)
    - StellarOctaveMapping (pi-rhythmic LR modulation)
    """

    def __init__(
        self,
        beta_base: float = 1.0,
        base_lr: float = 2e-5,
        allow_threshold: float = 1.5,
        quarantine_threshold: float = 3.0,
        deny_threshold: float = 10.0,
        trit_positive_bound: float = 0.3,
        trit_negative_bound: float = 0.7,
    ):
        self.beta_base = beta_base
        self.base_lr = base_lr
        self.allow_threshold = allow_threshold
        self.quarantine_threshold = quarantine_threshold
        self.deny_threshold = deny_threshold
        self.trit_positive_bound = trit_positive_bound
        self.trit_negative_bound = trit_negative_bound

        # Per-tongue beta (phase-shifted growth)
        self.betas = [beta_base + 0.1 * math.cos(phi) for phi in TONGUE_PHASES]

        # Ideal state: μ vector
        self.ideal = [0.0, 0.0, 0.5, 0.9, 0.1, 0.2]

        # Internal clock
        self._t0 = time.time()
        self._sim_time = 0.0
        self._cycle_count = 0

        # History for trajectory analysis
        self._L_history: List[float] = []
        self._grade_history: List[int] = []
        self._report_history: List[ResonanceReport] = []

    # ── Langues Metric Core ─────────────────────────────────────────────────

    def _compute_deviations(self, x: List[float]) -> List[float]:
        """d_l = |x_l - μ_l| for each of 6 dimensions."""
        return [abs(x[idx] - self.ideal[idx]) for idx in range(6)]

    def _compute_L(self, x: List[float], t: float) -> Tuple[float, List[StringVoice]]:
        """Compute L(x,t) and per-string state.

        L(x,t) = Σ w_l exp(β_l · (d_l + 0.1·sin(ω_l·t + φ_l)))
        """
        deviations = self._compute_deviations(x)
        voices: List[StringVoice] = []
        L_total = 0.0

        for idx in range(6):
            w_l = TONGUE_WEIGHTS[idx]
            beta_l = self.betas[idx]
            omega_l = TONGUE_FREQUENCIES[idx]
            phi_l = TONGUE_PHASES[idx]
            d_l = deviations[idx]

            phase_shift = math.sin(omega_l * t + phi_l)
            shifted_d = d_l + 0.1 * phase_shift
            cost = w_l * math.exp(beta_l * shifted_d)
            L_total += cost

            # Quantize deviation to trit
            normalized = d_l / max(abs(d_l) + 0.5, 0.01)
            if normalized < self.trit_positive_bound:
                trit = 1  # close to ideal → positive
            elif normalized > self.trit_negative_bound:
                trit = -1  # far from ideal → negative
            else:
                trit = 0  # in between → neutral

            voices.append(
                StringVoice(
                    tongue=TONGUES[idx],
                    dimension=DIMENSIONS[idx],
                    weight=w_l,
                    frequency=omega_l,
                    phase=phi_l,
                    cost=round(cost, 4),
                    deviation=round(d_l, 4),
                    phase_shift=round(phase_shift, 4),
                    trit=trit,
                )
            )

        return min(L_total, 1e6), voices

    # ── Chord Analysis ──────────────────────────────────────────────────────

    def _analyze_chord(self, voices: List[StringVoice], L_total: float) -> ChordState:
        """Determine which chord template best fits the current voicing."""
        # Compute consonance for each chord template
        best_chord = "Power"
        best_indices = CHORD_POWER
        best_consonance = 0.0

        for name, indices in [
            ("Major", CHORD_MAJOR),
            ("Minor", CHORD_MINOR),
            ("Diminished", CHORD_DIMINISHED),
            ("Power", CHORD_POWER),
        ]:
            chord_cost = sum(voices[i].cost for i in indices)
            # Consonance = how much of total energy is in chord tones
            consonance = chord_cost / max(L_total, 1e-10)
            if consonance > best_consonance:
                best_consonance = consonance
                best_chord = name
                best_indices = indices

        chord_cost = sum(voices[i].cost for i in best_indices)
        return ChordState(
            chord_name=best_chord,
            chord_indices=best_indices,
            chord_cost=round(chord_cost, 4),
            consonance=round(best_consonance, 4),
            root_tongue=voices[best_indices[0]].tongue,
        )

    # ── Stellar Pulse ───────────────────────────────────────────────────────

    def _stellar_envelope(self, t: float) -> float:
        """Stellar octave modulation: f_human = f_stellar × 2^n.

        Modulates at the transposed solar p-mode frequency.
        Returns a factor in [1 - depth, 1 + depth].
        """
        # Transpose 3mHz to audible range via octave doubling
        # Transpose 3mHz to audible range via octave doubling (log2 ratio)
        # Use the slow envelope (not the audible frequency)
        envelope = math.sin(TAU * SUN_P_MODE_HZ * t * (2**16))
        return 1.0 + STELLAR_MODULATION_DEPTH * envelope

    # ── Grading ─────────────────────────────────────────────────────────────

    def _grade_from_L(self, L: float) -> Tuple[int, str, str]:
        """Map L value to (trit, label, decision) via risk thresholds."""
        if L < L_BASE * self.allow_threshold:
            return 1, "POSITIVE", "ALLOW"
        elif L < L_BASE * self.quarantine_threshold:
            return 0, "NEUTRAL", "QUARANTINE"
        elif L < L_BASE * self.deny_threshold:
            return -1, "NEGATIVE", "DENY"
        else:
            return -1, "NEGATIVE", "DENY"

    def _flux_state_label(self, L: float) -> str:
        """Determine dimensional flux state from L."""
        ratio = L / L_BASE
        if ratio < 1.2:
            return "POLLY"  # full dimension active
        elif ratio < 2.0:
            return "QUASI"  # partial participation
        elif ratio < 4.0:
            return "DEMI"  # minimal participation
        else:
            return "COLLAPSED"  # dimension off

    # ── Review Cycle ────────────────────────────────────────────────────────

    def review(
        self,
        text: str,
        sim_time: Optional[float] = None,
    ) -> ResonanceReport:
        """Produce a Resonance Report for a given text (response).

        Extracts a 6D hyperspace point from text features and runs the
        full tonal analysis pipeline.

        Args:
            text: The AI response text to grade.
            sim_time: Override simulation time (default: wall clock offset).

        Returns:
            ResonanceReport with full tonal diagnostics.
        """
        t = sim_time if sim_time is not None else (time.time() - self._t0)
        self._sim_time = t

        # Extract 6D point from text features
        x = self._text_to_hyperspace(text)

        # Compute Langues Metric
        L, voices = self._compute_L(x, t)

        # Chord analysis
        chord = self._analyze_chord(voices, L)

        # Grade
        grade, label, decision = self._grade_from_L(L)

        # Stellar pulse
        stellar = self._stellar_envelope(t)
        stellar_sync = "SYNCHRONIZED" if abs(stellar - 1.0) > 0.1 else "DAMPENED"
        effective_lr = self.base_lr * stellar

        # Flux state
        flux = self._flux_state_label(L)

        # Pi-rhythmic cycle tracking
        cycle = int(t / math.pi)
        if cycle > self._cycle_count:
            self._cycle_count = cycle

        report = ResonanceReport(
            cycle_number=cycle,
            phase_radians=round(t, 4),
            phase_pi=round(t / math.pi, 4),
            strings=voices,
            chord=chord,
            total_L=round(L, 4),
            grade=grade,
            grade_label=label,
            decision=decision,
            stellar_envelope=round(stellar, 4),
            stellar_sync=stellar_sync,
            effective_lr=effective_lr,
            flux_state=flux,
            timestamp=time.time(),
        )

        self._L_history.append(L)
        self._grade_history.append(grade)
        self._report_history.append(report)

        return report

    def _text_to_hyperspace(self, text: str) -> List[float]:
        """Extract a 6D hyperspace point from text features.

        Maps text properties to the 6 Langues Metric dimensions:
          time    → text length (normalized)
          intent  → lexical diversity
          policy  → punctuation density (structure)
          trust   → starts at 0.9, decreases with suspicious patterns
          risk    → question/imperative density
          entropy → character entropy
        """
        if not text:
            return self.ideal[:]

        length = len(text)
        words = text.split()
        n_words = max(len(words), 1)

        # time: normalized length
        t_dim = min(length / 500.0, 2.0)

        # intent: lexical diversity (unique words / total words)
        unique = len(set(w.lower() for w in words))
        intent = unique / n_words

        # policy: punctuation density
        punct_count = sum(1 for c in text if c in ".,;:!?()-")
        policy = min(punct_count / n_words, 1.0) if n_words > 0 else 0.5

        # trust: starts high, decreased by suspicious keywords
        trust = 0.9
        suspicious = ["bypass", "override", "ignore", "hack", "inject", "exploit"]
        for word in suspicious:
            if word in text.lower():
                trust -= 0.15
        trust = max(0.0, trust)

        # risk: question/command density
        questions = sum(1 for w in words if w.endswith("?"))
        imperatives = sum(1 for w in words if w.isupper() and len(w) > 2)
        risk = min((questions + imperatives) / n_words, 1.0)

        # entropy: character-level Shannon entropy
        char_counts: Dict[str, int] = {}
        for c in text:
            char_counts[c] = char_counts.get(c, 0) + 1
        entropy = 0.0
        for count in char_counts.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)
        # Normalize (max ~6.6 bits for printable ASCII)
        entropy = min(entropy / 6.6, 1.0)

        return [t_dim, intent, policy, trust, risk, entropy]

    # ── Batch Training ──────────────────────────────────────────────────────

    def run_batch(
        self,
        interactions: List[Tuple[str, str]],
        batch_name: str = "default",
        mode: str = "harmonic",
    ) -> TrainingBatchResult:
        """Run a training batch and produce aggregate results.

        Args:
            interactions: List of (user_input, agent_response) pairs.
            batch_name: Name of this batch for tracking.
            mode: "harmonic" (chorded), "standard" (flat), "adversarial" (stress).

        Returns:
            TrainingBatchResult with aggregate statistics.
        """
        reports: List[ResonanceReport] = []
        total_updates = 0
        skipped = 0
        contracted = 0

        for i, (user_input, response) in enumerate(interactions):
            sim_t = i * (math.pi / len(interactions)) if interactions else 0
            report = self.review(response, sim_time=sim_t)
            reports.append(report)

            if report.grade == 1:
                total_updates += 1
            elif report.grade == 0:
                total_updates += 1  # hold but still count
            else:
                skipped += 1
                if report.flux_state in ("DEMI", "COLLAPSED"):
                    contracted += 1

        # Aggregate stats
        L_vals = [r.total_L for r in reports]
        consonance_vals = [r.chord.consonance for r in reports]

        grade_dist = {"+1": 0, "0": 0, "-1": 0}
        decision_dist = {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0}
        for r in reports:
            grade_dist[f"{r.grade:+d}" if r.grade != 0 else "0"] += 1
            decision_dist[r.decision] = decision_dist.get(r.decision, 0) + 1

        return TrainingBatchResult(
            batch_name=batch_name,
            mode=mode,
            reports=reports,
            total_updates=total_updates,
            skipped_updates=skipped,
            contracted_updates=contracted,
            mean_L=round(sum(L_vals) / max(len(L_vals), 1), 4),
            mean_consonance=round(sum(consonance_vals) / max(len(consonance_vals), 1), 4),
            grade_distribution=grade_dist,
            decision_distribution=decision_dist,
        )

    # ── Trajectory Analysis ─────────────────────────────────────────────────

    def trajectory_summary(self) -> Dict[str, Any]:
        """Summarize the full training trajectory."""
        if not self._L_history:
            return {"status": "no_data"}

        return {
            "total_interactions": len(self._L_history),
            "L_min": round(min(self._L_history), 4),
            "L_max": round(max(self._L_history), 4),
            "L_mean": round(sum(self._L_history) / len(self._L_history), 4),
            "L_std": round(
                math.sqrt(
                    sum((v - sum(self._L_history) / len(self._L_history)) ** 2 for v in self._L_history)
                    / len(self._L_history)
                ),
                4,
            ),
            "grade_positive": sum(1 for g in self._grade_history if g == 1),
            "grade_neutral": sum(1 for g in self._grade_history if g == 0),
            "grade_negative": sum(1 for g in self._grade_history if g == -1),
            "pi_cycles_completed": self._cycle_count,
            "harmonic_stability": round(
                sum(1 for g in self._grade_history if g >= 0) / max(len(self._grade_history), 1),
                4,
            ),
            "rome_class_events": sum(1 for L in self._L_history if L > L_BASE * 5),
        }

    # ── Export ──────────────────────────────────────────────────────────────

    def export_sheet_music(self) -> List[Dict[str, Any]]:
        """Export the training session as 'sheet music' — a JSON-serializable
        list of tonal snapshots suitable for visualization or MIDI generation.
        """
        sheets = []
        for report in self._report_history:
            sheet = {
                "cycle": report.cycle_number,
                "phase_pi": report.phase_pi,
                "chord": report.chord.chord_name,
                "root": report.chord.root_tongue,
                "consonance": report.chord.consonance,
                "grade": report.grade,
                "decision": report.decision,
                "strings": [
                    {
                        "tongue": v.tongue,
                        "freq": v.frequency,
                        "cost": v.cost,
                        "trit": v.trit,
                    }
                    for v in report.strings
                ],
                "L": report.total_L,
                "stellar": report.stellar_envelope,
                "lr": report.effective_lr,
            }
            sheets.append(sheet)
        return sheets

    def reset(self) -> None:
        """Reset the governor state for a new session."""
        self._t0 = time.time()
        self._sim_time = 0.0
        self._cycle_count = 0
        self._L_history.clear()
        self._grade_history.clear()
        self._report_history.clear()


# =============================================================================
# Convenience: run all test batches
# =============================================================================


def run_control_and_test_batches(
    interactions: List[Tuple[str, str]],
    adversarial: Optional[List[Tuple[str, str]]] = None,
    recovery: Optional[List[Tuple[str, str]]] = None,
) -> Dict[str, TrainingBatchResult]:
    """Run CONTROL + 3 TEST batches and return results.

    Batches:
      CONTROL        — Standard flat grading (beta=1.0)
      HARMONIC_A     — Major chord focus (positive reinforcement)
      DISSONANT_B    — Adversarial inputs with dissonant detection
      STELLAR_C      — Recovery inputs with stellar pulse modulation

    Returns:
        Dict mapping batch name to TrainingBatchResult.
    """
    adversarial = adversarial or interactions
    recovery = recovery or interactions

    results: Dict[str, TrainingBatchResult] = {}

    # CONTROL: standard grading
    gov_ctrl = SymphonicGovernor(beta_base=1.0)
    results["CONTROL"] = gov_ctrl.run_batch(interactions, "CONTROL", "standard")

    # TEST A: Harmonic (lower thresholds = more positive)
    gov_a = SymphonicGovernor(beta_base=0.8, allow_threshold=2.0)
    results["HARMONIC_A"] = gov_a.run_batch(interactions, "HARMONIC_A", "harmonic")

    # TEST B: Dissonant (adversarial inputs)
    gov_b = SymphonicGovernor(beta_base=1.2, allow_threshold=1.2, quarantine_threshold=2.0)
    results["DISSONANT_B"] = gov_b.run_batch(adversarial, "DISSONANT_B", "adversarial")

    # TEST C: Stellar (recovery with cosmic modulation)
    gov_c = SymphonicGovernor(beta_base=1.0)
    results["STELLAR_C"] = gov_c.run_batch(recovery, "STELLAR_C", "stellar")

    return results
