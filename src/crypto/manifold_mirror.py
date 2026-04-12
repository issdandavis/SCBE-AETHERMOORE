"""
Manifold Mirror — Inverse-Orientation Geometric Experiment
==========================================================

Runs compression (vector quantization) and retrieval (needle search)
in INVERSE ORIENTATION on the Poincaré ball, then mirrors both onto
a middle geodesic surface to reveal the interference pattern.

The geometric idea:
    FORWARD  (compression): text -> tongue encoding -> Poincaré point P_fwd
    INVERSE  (retrieval):   text -> complement tongue -> NEGATE -> P_inv
    MIDDLE:  geodesic midpoint M = midpoint(P_fwd, P_inv)
    MIRROR:  project both onto the sphere at radius ||M||
    PATTERN: the angular/energy distribution on the middle surface

The complement tongue IS the inverse orientation in the lore:
    KO <-> DR (intent <-> structure)
    AV <-> UM (wisdom <-> security)
    RU <-> CA (truth  <-> creativity)

When you compress in one tongue and "retrieve" through its complement
in reverse orientation, the middle surface shows where meaning survives
the round trip — and where it doesn't.
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from src.crypto.tri_bundle import encode_bytes
from src.crypto.harmonic_dark_fill import (
    COMPLEMENT_MAP,
    TONGUE_AUDIBLE_FREQ,
)

ALL_TONGUES = list(TONGUE_AUDIBLE_FREQ.keys())  # ko, av, ru, ca, um, dr
from src.crypto.h_lwe import (
    exp_map_zero,
    log_map_zero,
    mobius_add,
    mobius_neg,
    project_to_ball,
)
from src.crypto.geo_seal import (
    hyperbolic_distance,
    hyperbolic_midpoint,
)


def _get_mirror_shift():
    """Lazy import to break circular dependency through scbe_aethermoore.__init__."""
    from src.symphonic_cipher.scbe_aethermoore.ai_brain.mirror_shift import mirror_shift

    return mirror_shift


# ---------------------------------------------------------------------------
# Log-normalize (shared with third_thread.py — same dynamic range problem)
# ---------------------------------------------------------------------------


def _log_normalize(vec: tuple) -> list:
    """Log-normalize to compress frequency magnitudes."""
    return [math.copysign(math.log1p(abs(x)), x) for x in vec]


# ---------------------------------------------------------------------------
# Core: encode text -> Poincaré ball point
# ---------------------------------------------------------------------------


def _tongue_baseline(tongue: str) -> np.ndarray:
    """Compute the tongue's baseline signature using a neutral reference text.

    The tongue signature (frequency, phi-weight) dominates the encoding.
    To see content-specific patterns, we need to subtract this baseline.
    """
    ref = b"aaaaaaaaaaaaaaaa"  # 16 neutral bytes
    clusters = encode_bytes(ref, tongue)
    vectors = [_log_normalize(c.sound.as_vector() + c.light.as_vector()) for c in clusters]
    return np.array([sum(v[d] for v in vectors) / len(vectors) for d in range(len(vectors[0]))])


# Cache baselines
_BASELINES: Dict[str, np.ndarray] = {}


def _get_baseline(tongue: str) -> np.ndarray:
    if tongue not in _BASELINES:
        _BASELINES[tongue] = _tongue_baseline(tongue)
    return _BASELINES[tongue]


def _encode_to_poincare(text: str, tongue: str) -> np.ndarray:
    """Encode text through a tongue and project into Poincare ball.

    Two-part vector:
    1. TONGUE SIGNATURE: the baseline direction (shared by all texts in this tongue)
    2. CONTENT RESIDUAL: deviation from baseline (unique to this specific text)

    The tongue signature sets the RADIUS (how far from origin = how much compression).
    The content residual sets the DIRECTION (where on the sphere = what the text says).

    This separation is key: TurboQuant's Stage 1 rotation redistributes the
    signature, and Stage 2 QJL corrects the residual. Our tongue IS the rotation,
    and the residual IS the content that needs to survive compression.
    """
    data = text.encode("utf-8")
    clusters = encode_bytes(data, tongue)

    if not clusters:
        return np.zeros(18)

    # Full cluster vectors: sound + light (18 dims)
    vectors = [np.array(_log_normalize(c.sound.as_vector() + c.light.as_vector())) for c in clusters]

    mean_vec = sum(vectors) / len(vectors)

    # Subtract tongue baseline to extract content residual
    baseline = _get_baseline(tongue)
    residual = mean_vec - baseline

    # The Poincare point encodes BOTH tongue and content:
    # - Direction: content residual (what the text says)
    # - Magnitude: tongue energy (how the tongue compresses)
    tongue_energy = float(np.linalg.norm(baseline))
    residual_norm = float(np.linalg.norm(residual))

    if residual_norm < 1e-15:
        # Degenerate: text matches baseline exactly, use small perturbation
        residual = np.random.RandomState(hash(text) % 2**31).randn(len(mean_vec)) * 0.01

    # Scale: residual direction, tongue-energy magnitude
    # Amplify residual to make content differences visible
    direction = residual / (np.linalg.norm(residual) + 1e-12)
    magnitude = min(tongue_energy / 20.0, 1.5)  # Poincare-friendly range

    tangent_vec = direction * magnitude
    return exp_map_zero(tangent_vec, c=1.0)


# ---------------------------------------------------------------------------
# Single tongue-pair mirror computation
# ---------------------------------------------------------------------------


@dataclass
class MirrorPoint:
    """A single point on the middle surface."""

    tongue_fwd: str
    tongue_inv: str
    p_fwd: np.ndarray  # Forward orientation (compression)
    p_inv: np.ndarray  # Inverse orientation (retrieval, negated)
    p_mid: np.ndarray  # Geodesic midpoint
    mid_radius: float  # ||p_mid|| — distance from origin to middle surface
    fwd_on_surface: np.ndarray  # Forward projected onto middle sphere
    inv_on_surface: np.ndarray  # Inverse projected onto middle sphere
    angular_gap: float  # Angular distance between projections on surface
    energy_fwd: float  # Energy of forward projection
    energy_inv: float  # Energy of inverse projection
    asymmetry: float  # Energy imbalance on the surface
    interference: float  # Constructive (+) vs destructive (-) interference


def compute_mirror_point(
    text: str,
    tongue_fwd: str,
    tongue_inv: str,
) -> MirrorPoint:
    """Run forward + inverse orientation and mirror onto middle surface."""

    # Forward: encode in tongue_fwd
    p_fwd = _encode_to_poincare(text, tongue_fwd)

    # Inverse: encode in tongue_inv, then NEGATE (flip orientation)
    p_inv_raw = _encode_to_poincare(text, tongue_inv)
    p_inv = mobius_neg(p_inv_raw)

    # Middle surface: geodesic midpoint
    p_mid = hyperbolic_midpoint(p_fwd, p_inv)
    mid_radius = float(np.linalg.norm(p_mid))

    # Mirror both onto the sphere at mid_radius
    # Project = normalize to unit direction, scale to mid_radius
    def _project_to_sphere(p: np.ndarray, r: float) -> np.ndarray:
        norm = np.linalg.norm(p)
        if norm < 1e-12:
            return np.zeros_like(p)
        return (p / norm) * min(r, 0.999)

    fwd_on_surface = _project_to_sphere(p_fwd, mid_radius)
    inv_on_surface = _project_to_sphere(p_inv, mid_radius)

    # Angular gap: angle between the two directions on the sphere
    dot = np.dot(fwd_on_surface, inv_on_surface)
    norms = np.linalg.norm(fwd_on_surface) * np.linalg.norm(inv_on_surface)
    if norms > 1e-12:
        cos_angle = np.clip(dot / norms, -1.0, 1.0)
        angular_gap = float(np.arccos(cos_angle))
    else:
        angular_gap = math.pi  # maximally separated

    # Energy on surface
    energy_fwd = float(np.sum(fwd_on_surface**2))
    energy_inv = float(np.sum(inv_on_surface**2))
    total_energy = energy_fwd + energy_inv + 1e-12
    asymmetry = abs(energy_fwd - energy_inv) / total_energy

    # Interference: dot product of surface projections normalized by energy
    # Positive = constructive (projections align), Negative = destructive (oppose)
    interference = float(dot) / (total_energy / 2 + 1e-12)

    return MirrorPoint(
        tongue_fwd=tongue_fwd,
        tongue_inv=tongue_inv,
        p_fwd=p_fwd,
        p_inv=p_inv,
        p_mid=p_mid,
        mid_radius=mid_radius,
        fwd_on_surface=fwd_on_surface,
        inv_on_surface=inv_on_surface,
        angular_gap=angular_gap,
        energy_fwd=energy_fwd,
        energy_inv=energy_inv,
        asymmetry=asymmetry,
        interference=interference,
    )


# ---------------------------------------------------------------------------
# Full experiment: all tongue pairs × test texts
# ---------------------------------------------------------------------------


@dataclass
class ManifoldMirrorResult:
    """Results of the full manifold mirror experiment."""

    points: List[MirrorPoint]
    complement_points: List[MirrorPoint]  # Only complement pairs
    non_complement_points: List[MirrorPoint]  # Non-complement pairs
    mean_complement_gap: float
    mean_non_complement_gap: float
    mean_complement_interference: float
    mean_non_complement_interference: float
    mean_complement_radius: float
    mean_non_complement_radius: float
    complement_asymmetry: float
    non_complement_asymmetry: float
    needle_retrieval: Dict[str, float]  # Per-tongue needle recovery score


# The needle for our haystack test
NEEDLE_TEXT = "The sacred frequency is hidden at the convergence of six tongues"

HAYSTACK_TEXTS = [
    "The morning light filtered through ancient windows",
    "Mathematical proofs require careful axiom verification",
    "Every living system breathes in cycles of expansion",
    "The distance between two points on a curved surface",
    "Consciousness emerges from the interaction of signals",
    "Rivers carve their paths through persistent pressure",
    "The harmonic series converges at the golden ratio",
    "Adversarial inputs test the boundaries of all systems",
]


def _needle_in_haystack_score(tongue: str, complement: str) -> float:
    """Encode needle and haystack in forward tongue, search via inverse complement.

    Returns cosine similarity between the needle's middle-surface projection
    and the haystack's middle-surface projection. Higher = needle is more
    distinguishable from noise (better retrieval).
    """
    # Needle on middle surface
    needle_mp = compute_mirror_point(NEEDLE_TEXT, tongue, complement)

    # Haystack items on middle surface
    hay_similarities = []
    for hay_text in HAYSTACK_TEXTS:
        hay_mp = compute_mirror_point(hay_text, tongue, complement)

        # Cosine between needle and hay on the middle surface
        dot = np.dot(needle_mp.fwd_on_surface, hay_mp.fwd_on_surface)
        n1 = np.linalg.norm(needle_mp.fwd_on_surface)
        n2 = np.linalg.norm(hay_mp.fwd_on_surface)
        if n1 > 1e-12 and n2 > 1e-12:
            hay_similarities.append(abs(float(dot / (n1 * n2))))
        else:
            hay_similarities.append(0.0)

    # Retrieval score: how much does the needle stand out from hay?
    # 1.0 = needle is orthogonal to all hay (perfectly distinguishable)
    # 0.0 = needle is identical to hay (lost in the crowd)
    mean_hay_sim = sum(hay_similarities) / max(len(hay_similarities), 1)
    return 1.0 - mean_hay_sim


def run_manifold_mirror(
    test_text: str = "In the beginning was the Word and the Word was with God",
) -> ManifoldMirrorResult:
    """Run the full manifold mirror experiment."""

    all_points = []
    complement_points = []
    non_complement_points = []

    tongues = list(ALL_TONGUES)

    # Run all tongue pairs (forward × inverse)
    for t_fwd in tongues:
        for t_inv in tongues:
            if t_fwd == t_inv:
                continue  # Same tongue = no inverse orientation

            mp = compute_mirror_point(test_text, t_fwd, t_inv)
            all_points.append(mp)

            is_complement = COMPLEMENT_MAP.get(t_fwd) == t_inv
            if is_complement:
                complement_points.append(mp)
            else:
                non_complement_points.append(mp)

    # Aggregate metrics
    def _mean(pts: List[MirrorPoint], attr: str) -> float:
        if not pts:
            return 0.0
        return sum(getattr(p, attr) for p in pts) / len(pts)

    # Needle-in-haystack per tongue
    needle_scores = {}
    for tongue in tongues:
        complement = COMPLEMENT_MAP[tongue]
        needle_scores[tongue] = _needle_in_haystack_score(tongue, complement)

    return ManifoldMirrorResult(
        points=all_points,
        complement_points=complement_points,
        non_complement_points=non_complement_points,
        mean_complement_gap=_mean(complement_points, "angular_gap"),
        mean_non_complement_gap=_mean(non_complement_points, "angular_gap"),
        mean_complement_interference=_mean(complement_points, "interference"),
        mean_non_complement_interference=_mean(non_complement_points, "interference"),
        mean_complement_radius=_mean(complement_points, "mid_radius"),
        mean_non_complement_radius=_mean(non_complement_points, "mid_radius"),
        complement_asymmetry=_mean(complement_points, "asymmetry"),
        non_complement_asymmetry=_mean(non_complement_points, "asymmetry"),
        needle_retrieval=needle_scores,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def format_mirror_report(result: ManifoldMirrorResult) -> str:
    """Format the manifold mirror experiment results."""
    lines = []
    lines.append("=" * 80)
    lines.append("MANIFOLD MIRROR: Inverse-Orientation Geometric Experiment")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Forward (compression) and inverse (retrieval) run on the Poincaré ball,")
    lines.append("mirrored onto a middle geodesic surface. The pattern reveals where")
    lines.append("meaning survives the round trip between tongue and complement.")
    lines.append("")

    # Key metrics comparison
    lines.append("-" * 80)
    lines.append("COMPLEMENT vs NON-COMPLEMENT PAIRS")
    lines.append("-" * 80)
    lines.append(f"                        {'Complement':>14}  {'Non-Complement':>14}  {'Ratio':>8}")
    lines.append(
        f"  Angular gap (rad):    {result.mean_complement_gap:>14.4f}  {result.mean_non_complement_gap:>14.4f}  {result.mean_complement_gap / (result.mean_non_complement_gap + 1e-12):>8.3f}"
    )
    lines.append(
        f"  Interference:         {result.mean_complement_interference:>14.4f}  {result.mean_non_complement_interference:>14.4f}  {result.mean_complement_interference / (result.mean_non_complement_interference + 1e-12):>8.3f}"
    )
    lines.append(
        f"  Mid-surface radius:   {result.mean_complement_radius:>14.4f}  {result.mean_non_complement_radius:>14.4f}  {result.mean_complement_radius / (result.mean_non_complement_radius + 1e-12):>8.3f}"
    )
    lines.append(
        f"  Energy asymmetry:     {result.complement_asymmetry:>14.4f}  {result.non_complement_asymmetry:>14.4f}"
    )
    lines.append("")

    # Individual complement pairs
    lines.append("-" * 80)
    lines.append("COMPLEMENT PAIR DETAIL")
    lines.append("-" * 80)
    for mp in result.complement_points:
        marker = "+" if mp.interference > 0 else "-"
        lines.append(
            f"  {mp.tongue_fwd}<->{mp.tongue_inv}  "
            f"gap={mp.angular_gap:.4f}  "
            f"interf={mp.interference:+.4f} [{marker}]  "
            f"r_mid={mp.mid_radius:.4f}  "
            f"asym={mp.asymmetry:.4f}"
        )
    lines.append("")

    # Needle-in-haystack results
    lines.append("-" * 80)
    lines.append("NEEDLE-IN-HAYSTACK (per tongue, via complement mirror)")
    lines.append("-" * 80)
    for tongue, score in sorted(result.needle_retrieval.items(), key=lambda x: -x[1]):
        bar = "█" * int(score * 40) + "░" * (40 - int(score * 40))
        lines.append(f"  {tongue}: {score:.4f}  {bar}")
    lines.append("")

    # All pairs matrix
    lines.append("-" * 80)
    lines.append("FULL INTERFERENCE MATRIX (forward tongue -> inverse tongue)")
    lines.append("-" * 80)
    tongues = sorted(set(mp.tongue_fwd for mp in result.points))
    header = "        " + "  ".join(f"{t:>6}" for t in tongues)
    lines.append(header)
    for t_fwd in tongues:
        row = f"  {t_fwd}  "
        for t_inv in tongues:
            if t_fwd == t_inv:
                row += "     ·"
            else:
                mp = next(
                    (p for p in result.points if p.tongue_fwd == t_fwd and p.tongue_inv == t_inv),
                    None,
                )
                if mp:
                    row += f"  {mp.interference:+.3f}"
                else:
                    row += "     ?"
        lines.append(row)
    lines.append("")

    # The pattern
    lines.append("=" * 80)
    lines.append("THE PATTERN")
    lines.append("=" * 80)

    # Determine what the data shows
    comp_gap = result.mean_complement_gap
    non_comp_gap = result.mean_non_complement_gap
    comp_interf = result.mean_complement_interference
    non_comp_interf = result.mean_non_complement_interference

    if comp_gap > non_comp_gap:
        lines.append("  Complement pairs show WIDER angular gap on the middle surface.")
        lines.append("  -> The inverse voices spread FURTHER apart, not closer.")
        lines.append("  -> Maximum information diversity at the complement boundary.")
    else:
        lines.append("  Complement pairs show NARROWER angular gap on the middle surface.")
        lines.append("  -> The inverse voices CONVERGE, creating resonance.")

    lines.append("")

    if comp_interf < 0 and non_comp_interf > 0:
        lines.append("  Complement pairs: DESTRUCTIVE interference (cancel on surface)")
        lines.append("  Non-complement:   CONSTRUCTIVE interference (reinforce)")
        lines.append("  -> Complements ANNIHILATE on the middle surface.")
        lines.append("  -> The void between them IS the structured absence.")
        lines.append("  -> This is the harmonic dark fill at the geometric level.")
    elif comp_interf > 0 and non_comp_interf < 0:
        lines.append("  Complement pairs: CONSTRUCTIVE interference")
        lines.append("  Non-complement:   DESTRUCTIVE interference")
        lines.append("  -> Complements REINFORCE on the middle surface.")
    elif comp_interf < non_comp_interf:
        lines.append(f"  Complement interference ({comp_interf:+.4f}) < non-complement ({non_comp_interf:+.4f})")
        lines.append("  -> Complements are more destructive / less constructive.")
        lines.append("  -> The complement relationship creates a geometric null zone.")
    else:
        lines.append(f"  Complement interference ({comp_interf:+.4f}) >= non-complement ({non_comp_interf:+.4f})")
        lines.append("  -> Complements maintain coherence through the mirror.")

    lines.append("")

    # Needle observation
    mean_needle = sum(result.needle_retrieval.values()) / max(len(result.needle_retrieval), 1)
    best_tongue = max(result.needle_retrieval, key=result.needle_retrieval.get)
    worst_tongue = min(result.needle_retrieval, key=result.needle_retrieval.get)
    lines.append(f"  Needle retrieval: mean={mean_needle:.4f} best={best_tongue} worst={worst_tongue}")
    lines.append(f"  -> The {best_tongue} tongue preserves needle distinguishability best")
    lines.append(f"    through the complement mirror ({best_tongue}<->{COMPLEMENT_MAP[best_tongue]}).")
    lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# COMBO 1: Multi-text interference — same tongue pair, different texts
# ---------------------------------------------------------------------------


@dataclass
class TextInterference:
    """How two different texts interfere on the same tongue mirror."""

    text_a: str
    text_b: str
    tongue_fwd: str
    tongue_inv: str
    angular_separation: float  # How far apart the texts land on the surface
    cross_interference: float  # Dot product of their surface projections
    radius_diff: float  # How different their mid-surface depths are
    fidelity: float  # Cosine between their forward encodings


def compute_text_interference(
    text_a: str,
    text_b: str,
    tongue_fwd: str,
    tongue_inv: str,
) -> TextInterference:
    """Mirror two different texts through the same tongue pair.
    Shows whether the tongue pair preserves or destroys their difference."""
    mp_a = compute_mirror_point(text_a, tongue_fwd, tongue_inv)
    mp_b = compute_mirror_point(text_b, tongue_fwd, tongue_inv)

    # Angular separation on the middle surface
    dot_surf = np.dot(mp_a.fwd_on_surface, mp_b.fwd_on_surface)
    n1 = np.linalg.norm(mp_a.fwd_on_surface)
    n2 = np.linalg.norm(mp_b.fwd_on_surface)
    if n1 > 1e-12 and n2 > 1e-12:
        cos_a = np.clip(dot_surf / (n1 * n2), -1.0, 1.0)
        angular_sep = float(np.arccos(cos_a))
    else:
        angular_sep = math.pi

    # Cross interference
    total_e = float(np.sum(mp_a.fwd_on_surface**2) + np.sum(mp_b.fwd_on_surface**2)) + 1e-12
    cross_interf = float(dot_surf) / (total_e / 2 + 1e-12)

    # Radius difference
    r_diff = abs(mp_a.mid_radius - mp_b.mid_radius)

    # Forward fidelity (do both texts encode similarly before mirroring?)
    dot_fwd = np.dot(mp_a.p_fwd, mp_b.p_fwd)
    n_fwd1 = np.linalg.norm(mp_a.p_fwd)
    n_fwd2 = np.linalg.norm(mp_b.p_fwd)
    if n_fwd1 > 1e-12 and n_fwd2 > 1e-12:
        fidelity = float(np.clip(dot_fwd / (n_fwd1 * n_fwd2), -1.0, 1.0))
    else:
        fidelity = 0.0

    return TextInterference(
        text_a=text_a,
        text_b=text_b,
        tongue_fwd=tongue_fwd,
        tongue_inv=tongue_inv,
        angular_separation=angular_sep,
        cross_interference=cross_interf,
        radius_diff=r_diff,
        fidelity=fidelity,
    )


# ---------------------------------------------------------------------------
# COMBO 2: Triple mirror — 3 tongues meet at a centroid
# ---------------------------------------------------------------------------


@dataclass
class TripleMirror:
    """Three tongues mirrored onto their centroid surface."""

    tongues: Tuple[str, str, str]
    points: Tuple[np.ndarray, np.ndarray, np.ndarray]  # 3 Poincare points
    centroid: np.ndarray  # Geodesic centroid of the 3 points
    centroid_radius: float
    triangle_area: float  # Hyperbolic triangle area (angular defect)
    pairwise_gaps: Tuple[float, float, float]  # 3 angular gaps between pairs
    total_interference: float  # Sum of all 3 pairwise interferences
    mode: str  # "convergent" / "divergent" / "mixed"


def _hyperbolic_triangle_area(p1, p2, p3) -> float:
    """Approximate hyperbolic triangle area via angular defect.
    In hyperbolic space: area = pi - (a1 + a2 + a3) where ai are interior angles."""

    # Use Euclidean angles as approximation for small triangles
    def _angle_at(vertex, a, b):
        va = a - vertex
        vb = b - vertex
        na, nb = np.linalg.norm(va), np.linalg.norm(vb)
        if na < 1e-12 or nb < 1e-12:
            return math.pi / 3
        cos_a = np.clip(np.dot(va, vb) / (na * nb), -1.0, 1.0)
        return float(np.arccos(cos_a))

    a1 = _angle_at(p1, p2, p3)
    a2 = _angle_at(p2, p1, p3)
    a3 = _angle_at(p3, p1, p2)
    defect = math.pi - (a1 + a2 + a3)
    return max(defect, 0.0)


def compute_triple_mirror(
    text: str,
    tongue_a: str,
    tongue_b: str,
    tongue_c: str,
) -> TripleMirror:
    """Encode text through 3 tongues and find where they meet."""
    pa = _encode_to_poincare(text, tongue_a)
    pb = _encode_to_poincare(text, tongue_b)
    pc = _encode_to_poincare(text, tongue_c)

    # Centroid: geodesic midpoint of midpoint(a,b) and c
    mid_ab = hyperbolic_midpoint(pa, pb)
    centroid = hyperbolic_midpoint(mid_ab, pc)
    centroid_radius = float(np.linalg.norm(centroid))

    # Triangle area
    area = _hyperbolic_triangle_area(pa, pb, pc)

    # Pairwise angular gaps (on unit sphere projections)
    def _angular_gap(p1, p2):
        n1, n2 = np.linalg.norm(p1), np.linalg.norm(p2)
        if n1 < 1e-12 or n2 < 1e-12:
            return math.pi
        cos_a = np.clip(np.dot(p1, p2) / (n1 * n2), -1.0, 1.0)
        return float(np.arccos(cos_a))

    gap_ab = _angular_gap(pa, pb)
    gap_bc = _angular_gap(pb, pc)
    gap_ac = _angular_gap(pa, pc)

    # Total interference: sum of pairwise dot products
    total_energy = float(np.sum(pa**2) + np.sum(pb**2) + np.sum(pc**2)) + 1e-12
    total_interf = float(np.dot(pa, pb) + np.dot(pb, pc) + np.dot(pa, pc))
    total_interf /= total_energy / 3 + 1e-12

    # Mode classification
    if total_interf > 0.3:
        mode = "convergent"
    elif total_interf < -0.3:
        mode = "divergent"
    else:
        mode = "mixed"

    return TripleMirror(
        tongues=(tongue_a, tongue_b, tongue_c),
        points=(pa, pb, pc),
        centroid=centroid,
        centroid_radius=centroid_radius,
        triangle_area=area,
        pairwise_gaps=(gap_ab, gap_bc, gap_ac),
        total_interference=total_interf,
        mode=mode,
    )


# ---------------------------------------------------------------------------
# COMBO 3: Chain mirror — round-trip A->B->C->A
# ---------------------------------------------------------------------------


@dataclass
class ChainMirror:
    """A round-trip chain through 3+ tongues."""

    chain: List[str]  # Tongue sequence
    legs: List[MirrorPoint]  # Mirror point per leg
    total_angular_drift: float  # Sum of angular gaps around the chain
    round_trip_distance: float  # Hyperbolic distance from start to end
    holonomy: float  # Angular rotation after full loop (geometric phase)
    is_closed: bool  # Did we return close to start?


def compute_chain_mirror(
    text: str,
    chain: List[str],
) -> ChainMirror:
    """Mirror text through a chain of tongues: A->B, B->C, C->A, etc."""
    if len(chain) < 2:
        raise ValueError("Chain needs at least 2 tongues")

    legs = []
    total_drift = 0.0

    # Close the loop: last element connects back to first
    full_chain = chain + [chain[0]]

    for i in range(len(full_chain) - 1):
        t_fwd = full_chain[i]
        t_inv = full_chain[i + 1]
        mp = compute_mirror_point(text, t_fwd, t_inv)
        legs.append(mp)
        total_drift += mp.angular_gap

    # Round-trip distance: how far is the last leg's midpoint from the first?
    start_mid = legs[0].p_mid
    end_mid = legs[-1].p_mid
    rt_dist = hyperbolic_distance(start_mid, end_mid)

    # Holonomy: the geometric phase accumulated around the loop
    # Use the angular difference between first forward and last inverse
    first_dir = legs[0].p_fwd / (np.linalg.norm(legs[0].p_fwd) + 1e-12)
    last_dir = legs[-1].p_inv / (np.linalg.norm(legs[-1].p_inv) + 1e-12)
    cos_holonomy = np.clip(float(np.dot(first_dir, last_dir)), -1.0, 1.0)
    holonomy = float(np.arccos(cos_holonomy))

    is_closed = rt_dist < 0.1  # Close enough to be a closed loop

    return ChainMirror(
        chain=chain,
        legs=legs,
        total_angular_drift=total_drift,
        round_trip_distance=float(rt_dist),
        holonomy=holonomy,
        is_closed=is_closed,
    )


# ---------------------------------------------------------------------------
# COMBO 4: Stacked mirrors — same text at multiple depths
# ---------------------------------------------------------------------------


@dataclass
class StackedMirror:
    """Same tongue pair, but encoding at different byte-depths of the text."""

    tongue_fwd: str
    tongue_inv: str
    depths: List[int]  # Byte counts used
    radii: List[float]  # Mid-surface radius at each depth
    interferences: List[float]  # Interference at each depth
    gaps: List[float]  # Angular gap at each depth
    convergence_depth: int  # Depth where interference stabilizes
    is_monotonic: bool  # Does radius grow monotonically with depth?


def compute_stacked_mirror(
    text: str,
    tongue_fwd: str,
    tongue_inv: str,
    depth_steps: int = 8,
) -> StackedMirror:
    """Slice text into increasing byte-depths and mirror each slice."""
    text_bytes = text.encode("utf-8")
    total = len(text_bytes)
    if total == 0:
        total = 1

    step = max(total // depth_steps, 1)
    depths = []
    radii = []
    interferences = []
    gaps = []

    for i in range(1, depth_steps + 1):
        n_bytes = min(i * step, total)
        slice_text = text_bytes[:n_bytes].decode("utf-8", errors="ignore")
        if not slice_text:
            slice_text = " "

        mp = compute_mirror_point(slice_text, tongue_fwd, tongue_inv)
        depths.append(n_bytes)
        radii.append(mp.mid_radius)
        interferences.append(mp.interference)
        gaps.append(mp.angular_gap)

    # Find convergence depth: where interference stops changing by >0.05
    conv_depth = depths[-1]
    for i in range(1, len(interferences)):
        if abs(interferences[i] - interferences[i - 1]) < 0.05:
            conv_depth = depths[i]
            break

    # Monotonicity check
    is_mono = all(radii[i] <= radii[i + 1] + 0.01 for i in range(len(radii) - 1))

    return StackedMirror(
        tongue_fwd=tongue_fwd,
        tongue_inv=tongue_inv,
        depths=depths,
        radii=radii,
        interferences=interferences,
        gaps=gaps,
        convergence_depth=conv_depth,
        is_monotonic=is_mono,
    )


# ---------------------------------------------------------------------------
# COMBO 5: Cross-text braid — N texts x M tongue pairs
# ---------------------------------------------------------------------------


@dataclass
class BraidCombo:
    """Full cross-product: multiple texts x multiple tongue pairs."""

    texts: List[str]
    tongue_pairs: List[Tuple[str, str]]
    # matrix[text_idx][pair_idx] = MirrorPoint
    matrix: List[List[MirrorPoint]]
    # Per-text: which tongue pair gives best retrieval?
    best_pair_per_text: List[Tuple[str, str]]
    # Per-pair: which text produces strongest interference?
    strongest_text_per_pair: List[str]
    # Global: mean interference by pair type
    pair_mean_interference: Dict[str, float]


TEXT_CORPUS = [
    # Lore
    "In the beginning was the Word and the Word was with God",
    "The raven carried the message across seven fractured realms",
    "Every pattern rune hums at its own frequency in the lattice",
    # Technical
    "The Poincare ball model maps hyperbolic space to a unit disk",
    "Post-quantum cryptography uses lattice-based assumptions",
    "Gradient descent follows the negative gradient of the loss",
    # Emotional
    "Love is the only force that transcends dimension and time",
    "Fear contracts the space around itself until nothing moves",
    "Joy expands like light filling every corner of a dark room",
    # Abstract
    "Zero is not nothing it is the boundary between positive and negative",
    "Infinity is not a number it is a direction",
    "The void between stars is not empty it is full of potential",
]


def compute_braid_combo(
    texts: Optional[List[str]] = None,
    tongue_pairs: Optional[List[Tuple[str, str]]] = None,
) -> BraidCombo:
    """Run every text through every tongue pair."""
    if texts is None:
        texts = TEXT_CORPUS

    if tongue_pairs is None:
        # All complement pairs + selected non-complement
        tongue_pairs = [
            ("ko", "dr"),
            ("dr", "ko"),  # complement
            ("av", "um"),
            ("um", "av"),  # complement
            ("ru", "ca"),
            ("ca", "ru"),  # complement
            ("ko", "av"),
            ("av", "dr"),  # non-complement: adjacent
            ("ko", "ca"),
            ("ru", "um"),  # non-complement: cross
        ]

    matrix: List[List[MirrorPoint]] = []
    for text in texts:
        row = []
        for t_fwd, t_inv in tongue_pairs:
            mp = compute_mirror_point(text, t_fwd, t_inv)
            row.append(mp)
        matrix.append(row)

    # Best pair per text: highest |interference|
    best_per_text = []
    for row in matrix:
        best = max(row, key=lambda mp: abs(mp.interference))
        best_per_text.append((best.tongue_fwd, best.tongue_inv))

    # Strongest text per pair: highest |interference|
    strongest_per_pair = []
    for j in range(len(tongue_pairs)):
        best_text_idx = max(range(len(texts)), key=lambda i: abs(matrix[i][j].interference))
        strongest_per_pair.append(texts[best_text_idx])

    # Mean interference by pair
    pair_means: Dict[str, float] = {}
    for j, (t_fwd, t_inv) in enumerate(tongue_pairs):
        key = f"{t_fwd}->{t_inv}"
        vals = [matrix[i][j].interference for i in range(len(texts))]
        pair_means[key] = sum(vals) / len(vals)

    return BraidCombo(
        texts=texts,
        tongue_pairs=tongue_pairs,
        matrix=matrix,
        best_pair_per_text=best_per_text,
        strongest_text_per_pair=strongest_per_pair,
        pair_mean_interference=pair_means,
    )


# ---------------------------------------------------------------------------
# Combined report for all combos
# ---------------------------------------------------------------------------


def format_combo_report(
    text_interfs: List[TextInterference],
    triples: List[TripleMirror],
    chains: List[ChainMirror],
    stacked: List[StackedMirror],
    braid: BraidCombo,
) -> str:
    """Format all combo experiments into one report."""
    lines = []
    lines.append("=" * 80)
    lines.append("MANIFOLD MIRROR: EXTENDED COMBOS")
    lines.append("=" * 80)

    # --- Text interference ---
    lines.append("")
    lines.append("-" * 80)
    lines.append("COMBO 1: TEXT-vs-TEXT INTERFERENCE (same tongue, different content)")
    lines.append("-" * 80)
    for ti in text_interfs:
        lines.append(
            f"  [{ti.tongue_fwd}->{ti.tongue_inv}] "
            f"ang={ti.angular_separation:.3f} "
            f"interf={ti.cross_interference:+.3f} "
            f"fidelity={ti.fidelity:+.3f} "
            f"r_diff={ti.radius_diff:.4f}"
        )
        lines.append(f"    A: {ti.text_a[:50]}")
        lines.append(f"    B: {ti.text_b[:50]}")

    # --- Triple mirrors ---
    lines.append("")
    lines.append("-" * 80)
    lines.append("COMBO 2: TRIPLE MIRRORS (3 tongues meet at centroid)")
    lines.append("-" * 80)
    for tm in triples:
        t_str = "/".join(tm.tongues)
        g_str = "/".join(f"{g:.2f}" for g in tm.pairwise_gaps)
        lines.append(
            f"  {t_str:12s}  mode={tm.mode:10s}  "
            f"area={tm.triangle_area:.4f}  "
            f"r_cent={tm.centroid_radius:.4f}  "
            f"interf={tm.total_interference:+.3f}  "
            f"gaps=[{g_str}]"
        )

    # --- Chain mirrors ---
    lines.append("")
    lines.append("-" * 80)
    lines.append("COMBO 3: CHAIN MIRRORS (round-trip loops)")
    lines.append("-" * 80)
    for cm in chains:
        chain_str = "->".join(cm.chain) + "->" + cm.chain[0]
        closed = "CLOSED" if cm.is_closed else "OPEN"
        lines.append(
            f"  {chain_str:30s}  "
            f"drift={cm.total_angular_drift:.3f}  "
            f"rt_dist={cm.round_trip_distance:.4f}  "
            f"holonomy={cm.holonomy:.3f}  "
            f"[{closed}]"
        )
        # Per-leg detail
        for leg in cm.legs:
            lines.append(
                f"    {leg.tongue_fwd}->{leg.tongue_inv}: "
                f"gap={leg.angular_gap:.3f} "
                f"interf={leg.interference:+.3f} "
                f"r_mid={leg.mid_radius:.3f}"
            )

    # --- Stacked mirrors ---
    lines.append("")
    lines.append("-" * 80)
    lines.append("COMBO 4: STACKED MIRRORS (depth slices)")
    lines.append("-" * 80)
    for sm in stacked:
        mono = "MONO" if sm.is_monotonic else "NON-MONO"
        lines.append(f"  {sm.tongue_fwd}->{sm.tongue_inv}  " f"conv_depth={sm.convergence_depth}  " f"[{mono}]")
        for i, d in enumerate(sm.depths):
            bar_len = int(abs(sm.interferences[i]) * 20)
            sign = "+" if sm.interferences[i] > 0 else "-"
            bar = sign * bar_len
            lines.append(
                f"    {d:>5}B: r={sm.radii[i]:.3f} "
                f"interf={sm.interferences[i]:+.3f} "
                f"gap={sm.gaps[i]:.3f}  {bar}"
            )

    # --- Braid combo ---
    lines.append("")
    lines.append("-" * 80)
    lines.append("COMBO 5: CROSS-TEXT BRAID (texts x tongue-pairs)")
    lines.append("-" * 80)

    # Header
    pair_labels = [f"{a}->{b}" for a, b in braid.tongue_pairs]
    lines.append("  Mean interference by pair:")
    for label, mean_i in sorted(braid.pair_mean_interference.items(), key=lambda x: -x[1]):
        sign = "+" if mean_i > 0 else ""
        lines.append(f"    {label:8s}: {sign}{mean_i:.3f}")

    lines.append("")
    lines.append("  Best tongue pair per text:")
    for i, text in enumerate(braid.texts):
        best = braid.best_pair_per_text[i]
        lines.append(f"    {best[0]}->{best[1]}  {text[:55]}")

    lines.append("")
    lines.append("  Heat map (interference):")
    # Compact header
    hdr = "  " + " " * 12
    for j, (a, b) in enumerate(braid.tongue_pairs[:8]):
        hdr += f" {a[:2]}{b[:2]:>2}"
    lines.append(hdr)
    for i, text in enumerate(braid.texts):
        row = f"  {text[:12]:12s}"
        for j in range(min(8, len(braid.tongue_pairs))):
            v = braid.matrix[i][j].interference
            if v > 0.5:
                row += "   ++"
            elif v > 0:
                row += "    +"
            elif v > -0.5:
                row += "    -"
            else:
                row += "   --"
        lines.append(row)

    # --- Summary ---
    lines.append("")
    lines.append("=" * 80)
    lines.append("COMBO SUMMARY")
    lines.append("=" * 80)

    # Triple modes
    mode_counts = {}
    for tm in triples:
        mode_counts[tm.mode] = mode_counts.get(tm.mode, 0) + 1
    lines.append(f"  Triple modes: {mode_counts}")

    # Chain closedness
    closed_count = sum(1 for cm in chains if cm.is_closed)
    lines.append(f"  Closed chains: {closed_count}/{len(chains)}")

    # Mean holonomy
    if chains:
        mean_hol = sum(cm.holonomy for cm in chains) / len(chains)
        lines.append(f"  Mean holonomy: {mean_hol:.4f} rad")

    # Stacked convergence
    if stacked:
        mean_conv = sum(sm.convergence_depth for sm in stacked) / len(stacked)
        lines.append(f"  Mean convergence depth: {mean_conv:.0f} bytes")

    lines.append("")
    lines.append("=" * 80)
    return "\n".join(lines)


def run_all_combos(
    text: str = "In the beginning was the Word and the Word was with God",
) -> str:
    """Run all combo experiments and return formatted report."""

    # COMBO 1: Text interference — same pair, different texts
    text_pairs = [
        (TEXT_CORPUS[0], TEXT_CORPUS[3]),  # lore vs technical
        (TEXT_CORPUS[0], TEXT_CORPUS[6]),  # lore vs emotional
        (TEXT_CORPUS[3], TEXT_CORPUS[9]),  # technical vs abstract
        (TEXT_CORPUS[6], TEXT_CORPUS[8]),  # emotional vs emotional
        (TEXT_CORPUS[1], TEXT_CORPUS[11]),  # lore vs abstract
    ]
    text_interfs = []
    for ta, tb in text_pairs:
        for pair in [("ko", "dr"), ("av", "um"), ("ru", "ca")]:
            text_interfs.append(compute_text_interference(ta, tb, pair[0], pair[1]))

    # COMBO 2: Triple mirrors — all C(6,3) = 20 triples
    from itertools import combinations

    triples = []
    for combo in combinations(ALL_TONGUES, 3):
        triples.append(compute_triple_mirror(text, combo[0], combo[1], combo[2]))

    # COMBO 3: Chain mirrors — complement cycles + arbitrary loops
    chains = [
        compute_chain_mirror(text, ["ko", "dr"]),  # 2-chain complement
        compute_chain_mirror(text, ["av", "um"]),  # 2-chain complement
        compute_chain_mirror(text, ["ru", "ca"]),  # 2-chain complement
        compute_chain_mirror(text, ["ko", "av", "ru"]),  # 3-chain: all left-side
        compute_chain_mirror(text, ["dr", "um", "ca"]),  # 3-chain: all right-side
        compute_chain_mirror(text, ["ko", "av", "ru", "ca", "um", "dr"]),  # full 6-chain
        compute_chain_mirror(text, ["ko", "ca", "av", "dr", "ru", "um"]),  # cross pattern
        compute_chain_mirror(text, ["ko", "um", "ru", "dr", "av", "ca"]),  # interleaved
    ]

    # COMBO 4: Stacked mirrors — depth slices through complement pairs
    stacked = [
        compute_stacked_mirror(text, "ko", "dr"),
        compute_stacked_mirror(text, "av", "um"),
        compute_stacked_mirror(text, "ru", "ca"),
    ]

    # COMBO 5: Cross-text braid
    braid = compute_braid_combo()

    return format_combo_report(text_interfs, triples, chains, stacked, braid)
