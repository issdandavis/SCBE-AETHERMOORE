"""
Trit Curriculum Architecture — 3-Trit Training Signal
======================================================

Each training record gets a 3-trit vector based on its interference
pattern across the three complement tongue pairs:

    Pair        Axis         +1              0           -1
    ─────────   ──────────   ──────────────  ──────────  ──────────────
    KO <-> DR   Structure    Build/reinforce Balance     Challenge/break
    AV <-> UM   Stability    Stabilize       Neutral     Destabilize
    RU <-> CA   Creativity   Verify truth    Neutral     Create new

3 trits = 3^3 = 27 curriculum states per record.

The trit value is determined by the interference score of the
complement pair when encoding that specific text:
    interference > +threshold  =>  +1
    interference < -threshold  =>  -1
    otherwise                  =>   0

Discovered 2026-04-05: the interference pattern is largely
text-invariant (tongue geometry dominates), but the RESIDUAL
variation after baseline subtraction IS content-specific.
The trit captures the dominant mode; the raw interference
score preserves the continuous signal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from src.crypto.manifold_mirror import compute_mirror_point, MirrorPoint

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The three complement pairs and their curriculum axes
TRIT_AXES = [
    ("ko", "dr", "structure"),  # Build vs Challenge
    ("av", "um", "stability"),  # Stabilize vs Destabilize
    ("ru", "ca", "creativity"),  # Verify vs Create
]

# Threshold for trit quantization
# Based on observed interference distributions:
#   KO/DR: typically +0.7 to +0.9  (strongly constructive)
#   AV/UM: typically +0.05 to +0.3 (near neutral)
#   RU/CA: typically -0.8 to -1.0  (strongly destructive)
# A threshold of 0.3 separates the three modes cleanly.
DEFAULT_THRESHOLD = 0.3

# Labels for the 27 curriculum states
TRIT_LABELS = {
    (+1, +1, +1): "fortify",  # Build + Stabilize + Verify
    (+1, +1, 0): "consolidate",  # Build + Stabilize + Neutral
    (+1, +1, -1): "innovate",  # Build + Stabilize + Create
    (+1, 0, +1): "scaffold",  # Build + Neutral + Verify
    (+1, 0, 0): "construct",  # Build + Neutral + Neutral
    (+1, 0, -1): "architect",  # Build + Neutral + Create
    (+1, -1, +1): "stress_test",  # Build + Destabilize + Verify
    (+1, -1, 0): "disrupt_build",  # Build + Destabilize + Neutral
    (+1, -1, -1): "chaos_forge",  # Build + Destabilize + Create
    (0, +1, +1): "anchor",  # Balance + Stabilize + Verify
    (0, +1, 0): "steady_state",  # Balance + Stabilize + Neutral
    (0, +1, -1): "gentle_push",  # Balance + Stabilize + Create
    (0, 0, +1): "witness",  # Balance + Neutral + Verify
    (0, 0, 0): "null_state",  # Balance + Neutral + Neutral (the egg)
    (0, 0, -1): "dream",  # Balance + Neutral + Create
    (0, -1, +1): "challenge",  # Balance + Destabilize + Verify
    (0, -1, 0): "shake",  # Balance + Destabilize + Neutral
    (0, -1, -1): "dissolve",  # Balance + Destabilize + Create
    (-1, +1, +1): "deconstruct",  # Challenge + Stabilize + Verify
    (-1, +1, 0): "controlled_demo",  # Challenge + Stabilize + Neutral
    (-1, +1, -1): "phoenix",  # Challenge + Stabilize + Create (die+reborn)
    (-1, 0, +1): "audit",  # Challenge + Neutral + Verify
    (-1, 0, 0): "erode",  # Challenge + Neutral + Neutral
    (-1, 0, -1): "wildcard",  # Challenge + Neutral + Create
    (-1, -1, +1): "expose",  # Challenge + Destabilize + Verify
    (-1, -1, 0): "demolish",  # Challenge + Destabilize + Neutral
    (-1, -1, -1): "void",  # Challenge + Destabilize + Create (total reset)
}


# ---------------------------------------------------------------------------
# Geometric mode baselines (from combo experiments 2026-04-05)
# These are the mean interference scores per complement pair,
# computed across 12 diverse texts. The tongue geometry is the
# FIXED mode; content shifts the score AROUND this baseline.
# ---------------------------------------------------------------------------

GEOMETRIC_BASELINES = {
    "structure": +0.72,  # KO/DR mean interference (12-text calibration)
    "stability": +0.30,  # AV/UM mean interference (12-text calibration)
    "creativity": -0.99,  # RU/CA mean interference (12-text calibration)
}


# ---------------------------------------------------------------------------
# Core data structure
# ---------------------------------------------------------------------------


@dataclass
class TritSignal:
    """3-trit training signal for a single text.

    Two trit layers:
    1. GEOMETRIC trit: the fixed mode from tongue geometry (same for all text)
       KO/DR = +1 (constructive), AV/UM = 0 (neutral), RU/CA = -1 (destructive)
    2. CONTENT trit: deviation from geometric baseline (text-specific)
       Positive deviation = +1, near zero = 0, negative = -1

    The geometric trit tells you WHAT KIND of training this is.
    The content trit tells you HOW MUCH this specific text pushes or pulls.
    Together: 27 geometric states x 27 content states = 729 possible,
    but in practice geometric is fixed at (+1, 0, -1) so 27 content states.
    """

    # Geometric trits (tongue mode — nearly constant)
    t_structure: int  # KO/DR: +1, 0, -1
    t_stability: int  # AV/UM: +1, 0, -1
    t_creativity: int  # RU/CA: +1, 0, -1

    # Content trits (deviation from geometric baseline — text-specific)
    c_structure: int  # KO/DR deviation: +1, 0, -1
    c_stability: int  # AV/UM deviation: +1, 0, -1
    c_creativity: int  # RU/CA deviation: +1, 0, -1

    # Raw continuous interference scores
    raw_structure: float
    raw_stability: float
    raw_creativity: float

    # Deviations from geometric baseline
    dev_structure: float
    dev_stability: float
    dev_creativity: float

    # Curriculum label from the 27-state space (content trit)
    label: str

    # Edge proximity: how close each axis is to a trit boundary
    # Low values = edge case = polymorphic = high training signal
    edge_structure: float  # distance to nearest content threshold boundary
    edge_stability: float
    edge_creativity: float

    # Mirror points for each pair (full geometric detail)
    mirrors: Dict[str, MirrorPoint]

    @property
    def trit_vector(self) -> Tuple[int, int, int]:
        """Geometric trit (fixed mode)."""
        return (self.t_structure, self.t_stability, self.t_creativity)

    @property
    def content_vector(self) -> Tuple[int, int, int]:
        """Content trit (text-specific deviation)."""
        return (self.c_structure, self.c_stability, self.c_creativity)

    @property
    def trit_index(self) -> int:
        """Map content trit to 0-26 index. (+1,+1,+1)=0, (-1,-1,-1)=26."""
        s = 1 - self.c_structure  # +1->0, 0->1, -1->2
        b = 1 - self.c_stability
        c = 1 - self.c_creativity
        return s * 9 + b * 3 + c

    @property
    def raw_vector(self) -> Tuple[float, float, float]:
        return (self.raw_structure, self.raw_stability, self.raw_creativity)

    @property
    def dev_vector(self) -> Tuple[float, float, float]:
        return (self.dev_structure, self.dev_stability, self.dev_creativity)

    @property
    def edge_vector(self) -> Tuple[float, float, float]:
        return (self.edge_structure, self.edge_stability, self.edge_creativity)

    @property
    def min_edge_distance(self) -> float:
        """Minimum distance to any trit boundary. Lower = more polymorphic."""
        return min(self.edge_structure, self.edge_stability, self.edge_creativity)

    @property
    def is_polymorphic(self) -> bool:
        """True if any axis is within 0.01 of a trit boundary."""
        return self.min_edge_distance < 0.01

    @property
    def polymorphic_axes(self) -> List[str]:
        """Which axes are near a boundary."""
        axes = []
        if self.edge_structure < 0.01:
            axes.append("structure")
        if self.edge_stability < 0.01:
            axes.append("stability")
        if self.edge_creativity < 0.01:
            axes.append("creativity")
        return axes

    def to_dict(self) -> dict:
        """Serialize for SFT metadata."""
        return {
            "geometric_trit": list(self.trit_vector),
            "content_trit": list(self.content_vector),
            "trit_index": self.trit_index,
            "label": self.label,
            "raw_scores": {
                "structure": round(self.raw_structure, 4),
                "stability": round(self.raw_stability, 4),
                "creativity": round(self.raw_creativity, 4),
            },
            "deviations": {
                "structure": round(self.dev_structure, 4),
                "stability": round(self.dev_stability, 4),
                "creativity": round(self.dev_creativity, 4),
            },
            "edge_distance": {
                "structure": round(self.edge_structure, 4),
                "stability": round(self.edge_stability, 4),
                "creativity": round(self.edge_creativity, 4),
            },
            "is_polymorphic": self.is_polymorphic,
            "polymorphic_axes": self.polymorphic_axes,
        }


# ---------------------------------------------------------------------------
# Compute trit signal for text
# ---------------------------------------------------------------------------


def _quantize_trit(score: float, threshold: float = DEFAULT_THRESHOLD) -> int:
    """Quantize continuous interference to trit."""
    if score > threshold:
        return +1
    elif score < -threshold:
        return -1
    return 0


def compute_trit_signal(
    text: str,
    threshold: float = DEFAULT_THRESHOLD,
    content_threshold: float = 0.05,
) -> TritSignal:
    """Compute the 3-trit curriculum signal for a text.

    Two layers:
    1. Geometric trit: quantize raw interference (tongue mode)
    2. Content trit: quantize deviation from geometric baseline
       Content threshold is smaller (0.05) because deviations are subtle.
    """
    mirrors = {}
    raw_scores = []
    axis_names = []

    for tongue_fwd, tongue_inv, axis_name in TRIT_AXES:
        mp = compute_mirror_point(text, tongue_fwd, tongue_inv)
        mirrors[axis_name] = mp
        raw_scores.append(mp.interference)
        axis_names.append(axis_name)

    # Geometric trits: raw interference
    geo_trits = [_quantize_trit(s, threshold) for s in raw_scores]

    # Content trits: deviation from geometric baseline
    baselines = [GEOMETRIC_BASELINES[name] for name in axis_names]
    deviations = [raw - base for raw, base in zip(raw_scores, baselines)]
    content_trits = [_quantize_trit(d, content_threshold) for d in deviations]

    # Edge distance: how far each deviation is from the nearest threshold
    # Thresholds are at +content_threshold and -content_threshold
    edge_distances = [min(abs(d - content_threshold), abs(d + content_threshold)) for d in deviations]

    content_tuple = (content_trits[0], content_trits[1], content_trits[2])
    label = TRIT_LABELS.get(content_tuple, f"unknown_{content_tuple}")

    return TritSignal(
        t_structure=geo_trits[0],
        t_stability=geo_trits[1],
        t_creativity=geo_trits[2],
        c_structure=content_trits[0],
        c_stability=content_trits[1],
        c_creativity=content_trits[2],
        raw_structure=raw_scores[0],
        raw_stability=raw_scores[1],
        raw_creativity=raw_scores[2],
        dev_structure=deviations[0],
        dev_stability=deviations[1],
        dev_creativity=deviations[2],
        edge_structure=edge_distances[0],
        edge_stability=edge_distances[1],
        edge_creativity=edge_distances[2],
        label=label,
        mirrors=mirrors,
    )


# ---------------------------------------------------------------------------
# Batch compute for SFT pipeline
# ---------------------------------------------------------------------------


def compute_trit_batch(
    texts: List[str],
    threshold: float = DEFAULT_THRESHOLD,
) -> List[TritSignal]:
    """Compute trit signals for a batch of texts."""
    return [compute_trit_signal(t, threshold) for t in texts]


def trit_distribution(signals: List[TritSignal]) -> Dict[str, int]:
    """Count how many records fall in each of the 27 curriculum states."""
    dist: Dict[str, int] = {}
    for sig in signals:
        dist[sig.label] = dist.get(sig.label, 0) + 1
    return dict(sorted(dist.items(), key=lambda x: -x[1]))


def trit_summary(signals: List[TritSignal]) -> dict:
    """Summary statistics for a batch of trit signals."""
    if not signals:
        return {"count": 0}

    dist = trit_distribution(signals)

    # Mean raw scores
    mean_struct = sum(s.raw_structure for s in signals) / len(signals)
    mean_stab = sum(s.raw_stability for s in signals) / len(signals)
    mean_creat = sum(s.raw_creativity for s in signals) / len(signals)

    # Content trit counts per axis
    struct_counts = {+1: 0, 0: 0, -1: 0}
    stab_counts = {+1: 0, 0: 0, -1: 0}
    creat_counts = {+1: 0, 0: 0, -1: 0}
    for s in signals:
        struct_counts[s.c_structure] += 1
        stab_counts[s.c_stability] += 1
        creat_counts[s.c_creativity] += 1

    # Mean deviations
    mean_dev_struct = sum(s.dev_structure for s in signals) / len(signals)
    mean_dev_stab = sum(s.dev_stability for s in signals) / len(signals)
    mean_dev_creat = sum(s.dev_creativity for s in signals) / len(signals)

    # Polymorphic edge cases
    polymorphic_count = sum(1 for s in signals if s.is_polymorphic)
    mean_min_edge = sum(s.min_edge_distance for s in signals) / len(signals)

    return {
        "count": len(signals),
        "distribution": dist,
        "unique_states": len(dist),
        "geometric_mode": list(signals[0].trit_vector),  # Same for all
        "mean_raw": {
            "structure": round(mean_struct, 4),
            "stability": round(mean_stab, 4),
            "creativity": round(mean_creat, 4),
        },
        "mean_deviation": {
            "structure": round(mean_dev_struct, 4),
            "stability": round(mean_dev_stab, 4),
            "creativity": round(mean_dev_creat, 4),
        },
        "content_axis_counts": {
            "structure": struct_counts,
            "stability": stab_counts,
            "creativity": creat_counts,
        },
        "polymorphic_count": polymorphic_count,
        "polymorphic_pct": round(polymorphic_count / len(signals) * 100, 1),
        "mean_min_edge_distance": round(mean_min_edge, 6),
    }


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_texts = [
        "In the beginning was the Word and the Word was with God",
        "The Poincare ball model maps hyperbolic space to a unit ball",
        "Love is the only force that transcends dimension and time",
        "Every pattern rune hums at its own frequency in the lattice",
        "Post-quantum cryptography uses lattice-based assumptions",
        "Zero is not nothing it is the boundary between positive and negative infinity",
        "Fear contracts the space around itself until nothing moves",
        "The raven carried the message across seven fractured realms",
        "Gradient descent follows the negative gradient of the loss surface",
        "Joy expands like light filling every corner of a dark room",
        "Infinity is not a number it is a direction",
        "The void between stars is not empty it is full of potential",
    ]

    print("=" * 70)
    print("TRIT CURRICULUM ARCHITECTURE — 27-State Training Signal")
    print("=" * 70)
    print()

    signals = compute_trit_batch(test_texts)

    print(
        f"  Geometric mode (fixed): [{signals[0].t_structure:+d}, "
        f"{signals[0].t_stability:+d}, {signals[0].t_creativity:+d}]  "
        f"(structure=build, stability=neutral, creativity=create)"
    )
    print()
    print("  Content trits (text-specific deviation from geometric baseline):")
    print(f"  {'TRIT':8s} {'LABEL':16s} {'DEV_S':>8s} {'DEV_B':>8s} {'DEV_C':>8s}  TEXT")
    print(f"  {'----':8s} {'-----':16s} {'-----':>8s} {'-----':>8s} {'-----':>8s}  ----")

    for text, sig in zip(test_texts, signals):
        ct = f"[{sig.c_structure:+d},{sig.c_stability:+d},{sig.c_creativity:+d}]"
        poly = "**POLY**" if sig.is_polymorphic else f"  d={sig.min_edge_distance:.4f}"
        print(
            f"  {ct:8s} {sig.label:16s} {sig.dev_structure:+8.4f} "
            f"{sig.dev_stability:+8.4f} {sig.dev_creativity:+8.4f}  {poly}  {text[:38]}"
        )

    print()
    summary = trit_summary(signals)
    print(f"Content states used: {summary['unique_states']}/27")
    print(
        f"Mean deviation: struct={summary['mean_deviation']['structure']:+.4f}  "
        f"stab={summary['mean_deviation']['stability']:+.4f}  "
        f"creat={summary['mean_deviation']['creativity']:+.4f}"
    )
    print()
    print("Curriculum distribution:")
    for label, count in summary["distribution"].items():
        bar = "#" * count
        print(f"  {label:16s} {count:3d}  {bar}")
    print()
    print("Content axis counts:")
    for axis, counts in summary["content_axis_counts"].items():
        print(f"  {axis:12s}  +1={counts[+1]:2d}  0={counts[0]:2d}  -1={counts[-1]:2d}")
    print()
    print(
        f"Polymorphic (edge case) records: {summary['polymorphic_count']}/{len(signals)} "
        f"({summary['polymorphic_pct']}%)"
    )
    print(f"Mean min edge distance: {summary['mean_min_edge_distance']:.6f}")
