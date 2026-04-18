"""
Inverse Phase-Shifted Didactic Flow Modulations
================================================

A teaching sequence is not a static state. It FLOWS through the 27 trit-states
over time. The teacher emits a forward flow (increasing complexity). The learner
receives an inverse flow (decreasing confusion). The PHASE SHIFT between them
is the learning gap.

    Teacher flow:  build -> challenge -> verify -> build (forward breathing)
    Learner flow:  confused -> struggling -> understanding (inverse breathing)

Where they're IN PHASE = mastery (the student gets it as fast as the teacher gives it)
Where they're PHASE-SHIFTED = zone of proximal development (Vygotsky)
Where they're INVERSE = complete misunderstanding (need scaffold)

The modulation is how the flow rate CHANGES over time:
    - Constant modulation = lecture (fixed pace, no adaptation)
    - Breathing modulation = Socratic method (compress/expand based on response)
    - Phase-locked modulation = tutoring (teacher tracks student exactly)
    - Inverse phase = adversarial training (teacher goes opposite to student)

On the Poincare ball:
    - Breathing transform: beta < 1 pulls toward center (simplify)
                           beta > 1 pushes toward boundary (complexify)
    - Phase transform: theta rotates through trit-state space
    - Didactic flow: a trajectory through (beta(t), theta(t)) over time

The three complement pairs provide three independent phase channels:
    - KO/DR channel: structure phase (what is being built/challenged)
    - AV/UM channel: stability phase (how safe the learning environment is)
    - RU/CA channel: truth phase (how much verification vs creation)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum

from src.crypto.manifold_mirror import (
    _encode_to_poincare,
    compute_mirror_point,
    ALL_TONGUES,
)
from src.crypto.harmonic_dark_fill import COMPLEMENT_MAP
from src.crypto.h_lwe import exp_map_zero, log_map_zero, project_to_ball

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2  # 1.618...
PI = math.pi

# The three complement pair channels
CHANNELS = [
    ("ko", "dr"),  # structure channel
    ("av", "um"),  # stability channel
    ("ru", "ca"),  # truth channel
]

CHANNEL_NAMES = {
    ("ko", "dr"): "structure",
    ("av", "um"): "stability",
    ("ru", "ca"): "truth",
}


class FlowMode(str, Enum):
    """How the didactic flow modulates over time."""

    CONSTANT = "constant"  # Fixed pace lecture
    BREATHING = "breathing"  # Socratic compress/expand
    PHASE_LOCKED = "phase_locked"  # Tutor tracks student
    INVERSE = "inverse"  # Adversarial/challenge


# ---------------------------------------------------------------------------
# Core: Phase state at a point in time
# ---------------------------------------------------------------------------


@dataclass
class PhaseState:
    """The teaching/learning phase at a moment in time."""

    t: float  # Time parameter [0, 1]
    beta: float  # Breathing parameter (< 1 = simplify, > 1 = complexify)
    theta: Tuple[float, float, float]  # Phase angles per channel (KO/DR, AV/UM, RU/CA)
    trit: Tuple[int, int, int]  # Quantized trit state per channel
    radius: float  # Distance from origin (0 = simple, 1 = complex)
    energy: float  # Total flow energy at this point


@dataclass
class FlowPoint:
    """A single point in the didactic flow: teacher + learner + gap."""

    t: float
    teacher: PhaseState
    learner: PhaseState
    phase_gap: Tuple[float, float, float]  # Per-channel phase difference
    total_gap: float  # Combined gap magnitude
    zpd_score: float  # Zone of proximal development [0, 1]
    mastery: float  # How close to in-phase [0, 1]


@dataclass
class DidacticFlow:
    """Complete didactic flow trajectory."""

    mode: FlowMode
    steps: int
    points: List[FlowPoint]
    mean_gap: float
    mean_mastery: float
    mean_zpd: float
    trit_trajectory_teacher: List[Tuple[int, int, int]]
    trit_trajectory_learner: List[Tuple[int, int, int]]
    convergence_point: Optional[float]  # Time at which gap < threshold, or None
    channel_report: Dict[str, Dict[str, float]]  # Per-channel statistics


# ---------------------------------------------------------------------------
# Phase computation
# ---------------------------------------------------------------------------


def _trit_from_angle(theta: float) -> int:
    """Quantize a phase angle to trit {-1, 0, +1}.

    The circle is divided into three zones:
        [  -pi/3 to  pi/3 ] -> +1 (constructive)
        [  pi/3  to  pi   ] -> -1 (destructive)
        [ -pi    to -pi/3 ] -> -1 (destructive)
    The transition zones map to 0 (neutral).
    """
    # Normalize to [-pi, pi]
    theta = ((theta + PI) % (2 * PI)) - PI

    if abs(theta) < PI / 4:
        return 1  # constructive
    elif abs(theta) > 3 * PI / 4:
        return -1  # destructive
    else:
        return 0  # neutral


def _breathing_radius(t: float, beta: float) -> float:
    """Compute radial position under breathing transform.

    beta < 1: contracts toward center (simplification)
    beta = 1: identity
    beta > 1: expands toward boundary (complexification)
    """
    # Base radius increases with time (curriculum progression)
    r_base = 0.1 + 0.7 * t  # 0.1 to 0.8 over the flow
    # Breathing modulates
    r = math.tanh(beta * math.atanh(min(r_base, 0.999)))
    return max(0.0, min(r, 0.999))


def compute_teacher_phase(
    t: float,
    mode: FlowMode,
    base_beta: float = 1.2,
) -> PhaseState:
    """Compute teacher's phase state at time t.

    The teacher's flow is FORWARD: complexity increases with time,
    phase rotates through build -> challenge -> verify cycle.

    Each mode modulates BOTH the breathing (beta/radius) AND the
    phase rotation rates, so different teaching styles produce
    genuinely different phase trajectories.
    """
    # Base phase rates (phi-irrational so they never repeat)
    rate_structure = PHI
    rate_stability = PHI**2
    rate_truth = PHI + 1

    if mode == FlowMode.CONSTANT:
        beta = base_beta
        # Fixed rate — lecture proceeds at constant pace

    elif mode == FlowMode.BREATHING:
        # Socratic pulse: compress/expand complexity
        beta = base_beta + 0.3 * math.sin(2 * PI * t * 3)
        # Phase rates breathe too — slow down when compressing, speed up expanding
        breath = 1.0 + 0.4 * math.sin(2 * PI * t * 3)
        rate_structure *= breath
        rate_stability *= breath
        rate_truth *= breath

    elif mode == FlowMode.PHASE_LOCKED:
        beta = base_beta * 0.85  # Teacher deliberately under-drives
        # Slower rotation — teacher waits for student
        rate_structure *= 0.7
        rate_stability *= 0.7
        rate_truth *= 0.7

    elif mode == FlowMode.INVERSE:
        # Push harder over time
        beta = base_beta + 0.5 * t
        # Accelerating rotation — teacher keeps jumping ahead
        accel = 1.0 + 0.8 * t
        rate_structure *= accel
        rate_stability *= accel
        rate_truth *= accel

    else:
        beta = base_beta

    radius = _breathing_radius(t, beta)

    theta_structure = 2 * PI * t * rate_structure
    theta_stability = 2 * PI * t * rate_stability
    theta_truth = 2 * PI * t * rate_truth

    thetas = (theta_structure, theta_stability, theta_truth)
    trits = tuple(_trit_from_angle(th) for th in thetas)

    energy = radius**2 * sum(abs(th) for th in thetas) / (3 * PI)

    return PhaseState(
        t=t,
        beta=beta,
        theta=thetas,
        trit=trits,
        radius=radius,
        energy=energy,
    )


def compute_learner_phase(
    t: float,
    teacher: PhaseState,
    mode: FlowMode,
    learning_rate: float = 0.7,
    phase_delay: float = 0.15,
) -> PhaseState:
    """Compute learner's phase state at time t.

    The learner's flow is INVERSE: they receive the teacher's signal
    with a phase delay and breathing contraction. The learning rate
    controls how quickly they catch up.

    learning_rate: 0 = never learns, 1 = instant mastery
    phase_delay: temporal lag (how far behind the learner is)
    """
    # Learner's effective time is delayed
    t_eff = max(0.0, t - phase_delay)

    # Beta: learner simplifies (beta < 1) then gradually matches teacher
    base_beta = 0.6 + learning_rate * 0.6 * t_eff  # starts at 0.6, grows toward 1.2
    if mode == FlowMode.BREATHING:
        # Learner breathes in antiphase (compress when teacher expands)
        base_beta += 0.2 * math.sin(2 * PI * t_eff * 3 + PI)
    elif mode == FlowMode.PHASE_LOCKED:
        # Learner tracks teacher's beta with lag
        base_beta = 0.5 * base_beta + 0.5 * teacher.beta

    radius = _breathing_radius(t_eff, base_beta)

    # Learner's phases are INVERSE of teacher's, converging over time.
    # Each mode produces different convergence dynamics:
    if mode == FlowMode.CONSTANT:
        # Fixed learning rate — steady convergence
        convergence = learning_rate * t_eff
    elif mode == FlowMode.BREATHING:
        # Pulsed learning: faster when teacher compresses, slower when expanding
        # Accumulates over time via integral of breathing pulse
        breath_boost = 0.3 * (1 - math.cos(2 * PI * t_eff * 3)) / (2 * PI * 3)
        convergence = learning_rate * t_eff + breath_boost
    elif mode == FlowMode.PHASE_LOCKED:
        # Accelerated convergence — teacher adapts to student, so student learns faster
        convergence = min(1.0, learning_rate * 1.5 * t_eff)
    elif mode == FlowMode.INVERSE:
        # Teacher pushes AWAY — convergence is slower, may never reach 1.0
        convergence = learning_rate * 0.4 * t_eff
    else:
        convergence = learning_rate * t_eff

    inversion = max(0.0, 1.0 - convergence)  # 1.0 = fully inverse, 0.0 = matched

    theta_structure = teacher.theta[0] + PI * inversion  # inverse phase shift
    theta_stability = teacher.theta[1] + PI * inversion
    theta_truth = teacher.theta[2] + PI * inversion

    thetas = (theta_structure, theta_stability, theta_truth)
    trits = tuple(_trit_from_angle(th) for th in thetas)

    energy = radius**2 * sum(abs(th) for th in thetas) / (3 * PI)

    return PhaseState(
        t=t,
        beta=base_beta,
        theta=thetas,
        trit=trits,
        radius=radius,
        energy=energy,
    )


# ---------------------------------------------------------------------------
# Flow computation
# ---------------------------------------------------------------------------


def compute_flow_point(
    t: float,
    mode: FlowMode,
    learning_rate: float = 0.7,
    phase_delay: float = 0.15,
) -> FlowPoint:
    """Compute a single point in the didactic flow."""
    teacher = compute_teacher_phase(t, mode)
    learner = compute_learner_phase(t, teacher, mode, learning_rate, phase_delay)

    # Per-channel phase gap
    gaps = []
    for i in range(3):
        diff = abs(teacher.theta[i] - learner.theta[i])
        # Normalize to [0, pi]
        diff = min(diff % (2 * PI), 2 * PI - (diff % (2 * PI)))
        gaps.append(diff)

    phase_gap = tuple(gaps)
    total_gap = sum(gaps) / (3 * PI)  # Normalized to [0, 1]

    # Zone of proximal development: not too easy (gap~0), not too hard (gap~pi)
    # Peak ZPD at gap ~ pi/3 (one trit-width)
    zpd = 0.0
    for g in gaps:
        # Bell curve centered at pi/3
        zpd += math.exp(-((g - PI / 3) ** 2) / (2 * (PI / 6) ** 2))
    zpd /= 3.0

    # Mastery: how close the phases are (0 = opposite, 1 = matched)
    mastery = 1.0 - total_gap

    return FlowPoint(
        t=t,
        teacher=teacher,
        learner=learner,
        phase_gap=phase_gap,
        total_gap=total_gap,
        zpd_score=zpd,
        mastery=mastery,
    )


def run_didactic_flow(
    mode: FlowMode = FlowMode.BREATHING,
    steps: int = 48,
    learning_rate: float = 0.7,
    phase_delay: float = 0.15,
) -> DidacticFlow:
    """Run a complete didactic flow simulation."""
    points = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        fp = compute_flow_point(t, mode, learning_rate, phase_delay)
        points.append(fp)

    # Trajectories
    teacher_trits = [p.teacher.trit for p in points]
    learner_trits = [p.learner.trit for p in points]

    # Convergence: first time gap < 0.1
    convergence = None
    for p in points:
        if p.total_gap < 0.1:
            convergence = p.t
            break

    # Per-channel stats
    channel_names = ["structure", "stability", "truth"]
    channel_report = {}
    for ch_idx, ch_name in enumerate(channel_names):
        ch_gaps = [p.phase_gap[ch_idx] for p in points]
        ch_teacher_trits = [p.teacher.trit[ch_idx] for p in points]
        ch_learner_trits = [p.learner.trit[ch_idx] for p in points]
        agreement = sum(1 for t, l in zip(ch_teacher_trits, ch_learner_trits) if t == l) / len(points)
        channel_report[ch_name] = {
            "mean_gap": sum(ch_gaps) / len(ch_gaps),
            "min_gap": min(ch_gaps),
            "max_gap": max(ch_gaps),
            "trit_agreement": agreement,
        }

    mean_gap = sum(p.total_gap for p in points) / len(points)
    mean_mastery = sum(p.mastery for p in points) / len(points)
    mean_zpd = sum(p.zpd_score for p in points) / len(points)

    return DidacticFlow(
        mode=mode,
        steps=steps,
        points=points,
        mean_gap=mean_gap,
        mean_mastery=mean_mastery,
        mean_zpd=mean_zpd,
        trit_trajectory_teacher=teacher_trits,
        trit_trajectory_learner=learner_trits,
        convergence_point=convergence,
        channel_report=channel_report,
    )


# ---------------------------------------------------------------------------
# Compare all four flow modes
# ---------------------------------------------------------------------------


def run_all_modes(
    learning_rate: float = 0.7,
    steps: int = 48,
) -> Dict[str, DidacticFlow]:
    """Run all four didactic flow modes and return results."""
    results = {}
    for mode in FlowMode:
        results[mode.value] = run_didactic_flow(
            mode=mode,
            steps=steps,
            learning_rate=learning_rate,
        )
    return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def format_flow_report(flows: Dict[str, DidacticFlow]) -> str:
    """Format a comparative report of all flow modes."""
    lines = []
    lines.append("=" * 80)
    lines.append("INVERSE PHASE-SHIFTED DIDACTIC FLOW MODULATIONS")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Four modes of teaching, measured by how quickly teacher and learner")
    lines.append("phase-lock across three channels (structure, stability, truth).")
    lines.append("")

    # Comparison table
    lines.append("-" * 80)
    lines.append(f"  {'Mode':<16} {'Gap':>8} {'Mastery':>8} {'ZPD':>8} {'Converge':>10} {'Best Channel':<12}")
    lines.append("-" * 80)

    for name, flow in sorted(flows.items(), key=lambda x: x[1].mean_mastery, reverse=True):
        conv = f"t={flow.convergence_point:.2f}" if flow.convergence_point is not None else "never"
        best_ch = min(flow.channel_report.items(), key=lambda x: x[1]["mean_gap"])[0]
        lines.append(
            f"  {name:<16} {flow.mean_gap:>8.4f} {flow.mean_mastery:>8.4f} "
            f"{flow.mean_zpd:>8.4f} {conv:>10} {best_ch:<12}"
        )
    lines.append("")

    # Detailed per-mode
    for name, flow in flows.items():
        lines.append("-" * 80)
        lines.append(f"MODE: {name.upper()}")
        lines.append("-" * 80)

        # Trit trajectory visualization
        lines.append("  Teacher trit trajectory:")
        teacher_line = "    "
        for trit in flow.trit_trajectory_teacher:
            symbols = {1: "+", 0: ".", -1: "-"}
            teacher_line += "".join(symbols[t] for t in trit) + " "
        lines.append(teacher_line.rstrip())

        lines.append("  Learner trit trajectory:")
        learner_line = "    "
        for trit in flow.trit_trajectory_learner:
            symbols = {1: "+", 0: ".", -1: "-"}
            learner_line += "".join(symbols[t] for t in trit) + " "
        lines.append(learner_line.rstrip())

        # Phase gap over time (ASCII sparkline)
        lines.append("  Phase gap over time:")
        gap_line = "    "
        for p in flow.points:
            level = int(p.total_gap * 8)
            bars = " _.-=+*#@"
            gap_line += bars[min(level, 8)]
        lines.append(gap_line)

        # ZPD over time
        lines.append("  ZPD intensity:")
        zpd_line = "    "
        for p in flow.points:
            level = int(p.zpd_score * 8)
            bars = " _.-=+*#@"
            zpd_line += bars[min(level, 8)]
        lines.append(zpd_line)

        # Channel detail
        lines.append("  Channels:")
        for ch_name, ch_data in flow.channel_report.items():
            lines.append(
                f"    {ch_name:<12} gap={ch_data['mean_gap']:.3f} "
                f"[{ch_data['min_gap']:.3f}-{ch_data['max_gap']:.3f}] "
                f"agree={ch_data['trit_agreement']:.1%}"
            )
        lines.append("")

    # The finding
    lines.append("=" * 80)
    lines.append("THE FINDING")
    lines.append("=" * 80)

    best_mode = min(flows.items(), key=lambda x: x[1].mean_gap)
    best_zpd = max(flows.items(), key=lambda x: x[1].mean_zpd)
    fastest = min(
        ((n, f) for n, f in flows.items() if f.convergence_point is not None),
        key=lambda x: x[1].convergence_point,
        default=(None, None),
    )

    lines.append(f"  Lowest gap (highest mastery): {best_mode[0]}")
    lines.append(f"  Highest ZPD (best learning):  {best_zpd[0]}")
    if fastest[0]:
        lines.append(f"  Fastest convergence:          {fastest[0]} (t={fastest[1].convergence_point:.2f})")

    lines.append("")
    if best_mode[0] != best_zpd[0]:
        lines.append("  The mode with highest mastery is NOT the mode with best learning.")
        lines.append("  Mastery = matching the teacher. Learning = being in the ZPD.")
        lines.append("  The best teacher keeps the student slightly OUT of phase --")
        lines.append("  close enough to understand, far enough to grow.")
    else:
        lines.append("  Mastery and learning align in this configuration.")

    lines.append("")
    lines.append("=" * 80)
    return "\n".join(lines)
