"""
Polymorphic Multi-Path Generator — The Monty Hall of Trit Space
================================================================

LLMs traverse a single forward trajectory through high-dimensional space,
collapsing possibilities at each step. Training records scored with a
single trit vector suffer the same collapse: at trit boundaries, two
states are equally valid but only one is chosen.

This module turns that collapse into a training signal.

The Monty Hall Problem of Trit Space:
    - 3 doors (axes: structure, stability, creativity)
    - Each axis has a threshold boundary at +/-threshold
    - When a deviation is NEAR the boundary, the trit could go either way
    - Picking one trit = closing the door
    - Multi-path generation = opening the other door too

For polymorphic records (near trit boundaries), we generate SIBLING views:
the original record + alternatives with the boundary-adjacent trit flipped.
The model sees BOTH sides of the fork, learning the boundary itself
rather than just one arbitrary side.

    Single-path (standard):
        text -> score -> trit (0,+1,-1) -> one training record

    Multi-path (polymorphic):
        text -> score -> trit (0,+1,-1) -> primary record
                      -> boundary on axis 2 is close
                      -> flip axis 2: (0, 0,-1) -> sibling record
                      -> both records tagged as fork siblings

This is NOT data augmentation. Augmentation adds noise.
Multi-path generation adds INFORMATION — it teaches the model
where the decision boundary is and what the alternative looked like.

Number of sibling paths per record:
    0 polymorphic axes -> 1 path  (just the original)
    1 polymorphic axis -> 2 paths (original + 1 flip)
    2 polymorphic axes -> 4 paths (original + 3 flips: each axis + both)
    3 polymorphic axes -> 8 paths (all combinations)

This is 2^k where k = number of polymorphic axes.
Maximum 8 paths per record — and these are the MOST informative records
because they sit exactly where the model's decision is least certain.
"""

from __future__ import annotations

import math
import itertools
from dataclasses import dataclass
from typing import Dict, List

from src.crypto.trit_curriculum import (
    TritSignal,
    TRIT_LABELS,
    DEFAULT_THRESHOLD,
    compute_trit_signal,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Edge proximity threshold — how close a deviation must be to a boundary
# to count as polymorphic (eligible for multi-path generation).
# Default from TritSignal.is_polymorphic is 0.01 — we use a tunable version.
DEFAULT_EDGE_THRESHOLD = 0.01

# Maximum number of polymorphic axes to expand.
# 3 axes = 2^3 = 8 paths max. This is a hard limit.
MAX_POLY_AXES = 3

# Trit flip map: which trit value is "across the boundary"
# When near the +threshold boundary, the trit is either +1 or 0
# When near the -threshold boundary, the trit is either -1 or 0
# We always flip to the adjacent trit (not the opposite)
ADJACENT_TRIT = {
    (+1, "upper"): 0,  # near +threshold from above -> could be 0
    (0, "upper"): +1,  # near +threshold from below -> could be +1
    (0, "lower"): -1,  # near -threshold from above -> could be -1
    (-1, "lower"): 0,  # near -threshold from below -> could be 0
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TritFork:
    """A single alternative trit assignment for a polymorphic axis.

    Represents the "other door" in the Monty Hall analogy.
    """

    axis: str  # "structure", "stability", or "creativity"
    axis_index: int  # 0, 1, or 2
    original_trit: int  # the trit that was chosen
    flipped_trit: int  # the trit on the other side of the boundary
    deviation: float  # raw deviation value (how close to boundary)
    edge_distance: float  # distance to the threshold boundary
    boundary_side: str  # "upper" (+threshold) or "lower" (-threshold)


@dataclass
class MultipathRecord:
    """A training record with its multi-path siblings.

    The primary record is the original trit assignment.
    Siblings are alternative trit assignments for boundary-adjacent axes.
    Each sibling is a different "door" in the Monty Hall space.
    """

    text: str  # original text
    primary: TritSignal  # original trit signal
    forks: List[TritFork]  # which axes are polymorphic and how
    siblings: List[Dict]  # alternative trit + label combos
    path_count: int  # total number of paths (1 + len(siblings))
    fork_signature: str  # compact descriptor like "s:+1->0,c:-1->0"
    monty_hall_gain: float  # information gain from seeing alternatives


@dataclass
class MultipathBatch:
    """Results of multi-path generation on a batch of texts."""

    total_input: int  # number of input texts
    total_output: int  # total records after expansion
    expansion_ratio: float  # output / input
    polymorphic_count: int  # inputs that generated siblings
    records: List[MultipathRecord]  # all multipath records
    axis_fork_counts: Dict[str, int]  # how many forks per axis
    path_distribution: Dict[int, int]  # how many records have N paths


# ---------------------------------------------------------------------------
# Core: identify forks
# ---------------------------------------------------------------------------


def _identify_forks(
    signal: TritSignal,
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD,
    content_threshold: float = 0.05,
) -> List[TritFork]:
    """Identify which axes of a TritSignal are near a trit boundary.

    Returns a TritFork for each polymorphic axis, describing
    which trit the signal has and what it would be if the boundary
    fell on the other side.
    """
    forks = []

    axis_data = [
        ("structure", 0, signal.c_structure, signal.dev_structure, signal.edge_structure),
        ("stability", 1, signal.c_stability, signal.dev_stability, signal.edge_stability),
        ("creativity", 2, signal.c_creativity, signal.dev_creativity, signal.edge_creativity),
    ]

    for axis_name, axis_idx, trit_val, deviation, edge_dist in axis_data:
        if edge_dist >= edge_threshold:
            continue  # not near a boundary — skip

        # Determine which boundary we're near
        dist_upper = abs(deviation - content_threshold)
        dist_lower = abs(deviation + content_threshold)

        if dist_upper <= dist_lower:
            boundary_side = "upper"
        else:
            boundary_side = "lower"

        # What would the trit be on the other side?
        key = (trit_val, boundary_side)
        flipped = ADJACENT_TRIT.get(key)
        if flipped is None:
            # Edge case: trit is +1 near lower boundary or -1 near upper
            # This shouldn't happen with consistent thresholds, but handle it
            flipped = 0

        forks.append(
            TritFork(
                axis=axis_name,
                axis_index=axis_idx,
                original_trit=trit_val,
                flipped_trit=flipped,
                deviation=deviation,
                edge_distance=edge_dist,
                boundary_side=boundary_side,
            )
        )

    return forks


# ---------------------------------------------------------------------------
# Core: generate sibling paths
# ---------------------------------------------------------------------------


def _generate_siblings(
    signal: TritSignal,
    forks: List[TritFork],
) -> List[Dict]:
    """Generate all alternative trit assignments from a set of forks.

    For k forks, generates 2^k - 1 siblings (all combinations except
    the original, which is the primary signal).

    Each sibling is a dict with:
        - content_trit: the alternative trit vector
        - label: the 27-state label
        - flipped_axes: which axes were flipped
        - distance_from_primary: how many axes differ
    """
    if not forks:
        return []

    # Generate all non-empty subsets of forks
    siblings = []
    for r in range(1, len(forks) + 1):
        for combo in itertools.combinations(forks, r):
            # Start with original content trit
            new_trit = [signal.c_structure, signal.c_stability, signal.c_creativity]

            flipped_axes = []
            for fork in combo:
                new_trit[fork.axis_index] = fork.flipped_trit
                flipped_axes.append(fork.axis)

            new_tuple = (new_trit[0], new_trit[1], new_trit[2])
            label = TRIT_LABELS.get(new_tuple, f"unknown_{new_tuple}")

            siblings.append(
                {
                    "content_trit": new_tuple,
                    "label": label,
                    "flipped_axes": flipped_axes,
                    "distance_from_primary": len(combo),
                }
            )

    return siblings


def _fork_signature(forks: List[TritFork]) -> str:
    """Compact string describing which axes fork and how.

    Example: "s:+1->0,c:-1->0" means structure flips +1 to 0,
    creativity flips -1 to 0.
    """
    if not forks:
        return "none"

    parts = []
    for f in forks:
        axis_code = f.axis[0]  # s, s, c
        parts.append(f"{axis_code}:{f.original_trit:+d}->{f.flipped_trit:+d}")
    return ",".join(parts)


def _monty_hall_gain(forks: List[TritFork]) -> float:
    """Compute information gain from seeing alternative paths.

    Based on the Monty Hall insight: the closer to the boundary,
    the more information the alternative provides.

    At exact boundary (edge_distance=0): gain = 1.0 (maximum)
    At edge_threshold: gain ~= 0 (barely polymorphic)

    For multiple forks, gains are multiplicative:
    seeing 2 alternative axes is more than 2x as informative as one,
    because they interact (combinatorial information).
    """
    if not forks:
        return 0.0

    # Per-axis gain: inverse of edge distance, normalized
    per_axis_gains = []
    for f in forks:
        # Closer to boundary = higher gain
        # Use exponential decay from boundary
        gain = math.exp(-f.edge_distance * 100)  # sharp near boundary
        per_axis_gains.append(gain)

    # Multiplicative combination: product of (1 + gain_i) - 1
    # This gives superadditive information for multi-axis forks
    combined = 1.0
    for g in per_axis_gains:
        combined *= 1.0 + g
    combined -= 1.0

    return min(combined, 3.0)  # cap at 3.0 (3 axes max)


# ---------------------------------------------------------------------------
# Public API: score and expand a single text
# ---------------------------------------------------------------------------


def score_and_expand(
    text: str,
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD,
    content_threshold: float = 0.05,
    threshold: float = DEFAULT_THRESHOLD,
) -> MultipathRecord:
    """Score a text and generate multi-path siblings if polymorphic.

    This is the core function: it takes a single text, computes its
    trit signal, checks for boundary proximity, and generates all
    alternative paths that the single-path collapse would have discarded.

    Returns a MultipathRecord with the primary signal and any siblings.
    """
    signal = compute_trit_signal(text, threshold=threshold, content_threshold=content_threshold)
    forks = _identify_forks(signal, edge_threshold=edge_threshold, content_threshold=content_threshold)
    siblings = _generate_siblings(signal, forks)
    signature = _fork_signature(forks)
    gain = _monty_hall_gain(forks)

    return MultipathRecord(
        text=text,
        primary=signal,
        forks=forks,
        siblings=siblings,
        path_count=1 + len(siblings),
        fork_signature=signature,
        monty_hall_gain=gain,
    )


# ---------------------------------------------------------------------------
# Public API: batch processing
# ---------------------------------------------------------------------------


def score_and_expand_batch(
    texts: List[str],
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD,
    content_threshold: float = 0.05,
    threshold: float = DEFAULT_THRESHOLD,
) -> MultipathBatch:
    """Score a batch of texts and expand polymorphic records.

    Returns summary statistics and all expanded records.
    """
    records = [score_and_expand(t, edge_threshold, content_threshold, threshold) for t in texts]

    total_output = sum(r.path_count for r in records)
    poly_count = sum(1 for r in records if r.path_count > 1)

    # Axis fork counts
    axis_counts = {"structure": 0, "stability": 0, "creativity": 0}
    for r in records:
        for f in r.forks:
            axis_counts[f.axis] += 1

    # Path distribution
    path_dist: Dict[int, int] = {}
    for r in records:
        path_dist[r.path_count] = path_dist.get(r.path_count, 0) + 1

    return MultipathBatch(
        total_input=len(texts),
        total_output=total_output,
        expansion_ratio=total_output / max(len(texts), 1),
        polymorphic_count=poly_count,
        records=records,
        axis_fork_counts=axis_counts,
        path_distribution=dict(sorted(path_dist.items())),
    )


# ---------------------------------------------------------------------------
# SFT export: flatten multipath records for training
# ---------------------------------------------------------------------------


def flatten_for_sft(
    records: List[MultipathRecord],
) -> List[Dict]:
    """Flatten multipath records into individual SFT-ready dicts.

    Each output dict has:
        - text: the original text
        - content_trit: [s, b, c] trit vector
        - label: 27-state label
        - is_primary: True for original, False for siblings
        - fork_group: shared ID linking siblings to their primary
        - flipped_axes: [] for primary, list of flipped axes for siblings
        - monty_hall_gain: information gain from this expansion
        - path_count: total paths in this fork group
    """
    flat = []

    for rec in records:
        group_id = id(rec)  # unique per record in this batch

        # Primary record
        flat.append(
            {
                "text": rec.text,
                "content_trit": list(rec.primary.content_vector),
                "geometric_trit": list(rec.primary.trit_vector),
                "label": rec.primary.label,
                "is_primary": True,
                "fork_group": group_id,
                "flipped_axes": [],
                "monty_hall_gain": round(rec.monty_hall_gain, 4),
                "path_count": rec.path_count,
                "edge_distance": {
                    "structure": round(rec.primary.edge_structure, 6),
                    "stability": round(rec.primary.edge_stability, 6),
                    "creativity": round(rec.primary.edge_creativity, 6),
                },
                "raw_scores": {
                    "structure": round(rec.primary.raw_structure, 4),
                    "stability": round(rec.primary.raw_stability, 4),
                    "creativity": round(rec.primary.raw_creativity, 4),
                },
            }
        )

        # Sibling records
        for sib in rec.siblings:
            flat.append(
                {
                    "text": rec.text,
                    "content_trit": list(sib["content_trit"]),
                    "geometric_trit": list(rec.primary.trit_vector),
                    "label": sib["label"],
                    "is_primary": False,
                    "fork_group": group_id,
                    "flipped_axes": sib["flipped_axes"],
                    "monty_hall_gain": round(rec.monty_hall_gain, 4),
                    "path_count": rec.path_count,
                    "distance_from_primary": sib["distance_from_primary"],
                }
            )

    return flat


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def format_multipath_report(batch: MultipathBatch) -> str:
    """Human-readable report of multi-path generation results."""
    lines = []
    lines.append("=" * 72)
    lines.append("POLYMORPHIC MULTI-PATH GENERATOR — Monty Hall of Trit Space")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"  Input records:      {batch.total_input}")
    lines.append(f"  Output records:     {batch.total_output}")
    lines.append(f"  Expansion ratio:    {batch.expansion_ratio:.2f}x")
    lines.append(
        f"  Polymorphic inputs: {batch.polymorphic_count} "
        f"({batch.polymorphic_count / max(batch.total_input, 1) * 100:.1f}%)"
    )
    lines.append("")

    # Path distribution
    lines.append("  Path distribution:")
    for paths, count in batch.path_distribution.items():
        bar = "#" * count
        label = "single-path" if paths == 1 else f"{paths}-path fork"
        lines.append(f"    {paths} paths: {count:4d} records  ({label})  {bar}")
    lines.append("")

    # Axis fork counts
    lines.append("  Fork frequency by axis:")
    for axis, count in batch.axis_fork_counts.items():
        pct = count / max(batch.total_input, 1) * 100
        lines.append(f"    {axis:12s}: {count:4d} forks ({pct:.1f}%)")
    lines.append("")

    # Show details for polymorphic records
    poly_records = [r for r in batch.records if r.path_count > 1]
    if poly_records:
        lines.append("  POLYMORPHIC RECORDS (boundary crossers):")
        lines.append(f"  {'FORK':24s} {'PRIMARY':16s} {'SIBLINGS':24s} {'GAIN':>6s}  TEXT")
        lines.append(f"  {'----':24s} {'-------':16s} {'--------':24s} {'----':>6s}  ----")

        for rec in poly_records[:20]:  # Show first 20
            sib_labels = [s["label"] for s in rec.siblings]
            sib_str = ", ".join(sib_labels[:3])
            if len(sib_labels) > 3:
                sib_str += f" +{len(sib_labels) - 3}"
            lines.append(
                f"  {rec.fork_signature:24s} {rec.primary.label:16s} "
                f"{sib_str:24s} {rec.monty_hall_gain:6.3f}  {rec.text[:30]}"
            )

        if len(poly_records) > 20:
            lines.append(f"  ... and {len(poly_records) - 20} more polymorphic records")

    lines.append("")
    lines.append("  THE FINDING:")
    lines.append("  At trit boundaries, the model's choice is most uncertain.")
    lines.append("  Multi-path generation shows BOTH sides of the fork,")
    lines.append("  teaching the boundary itself — not just one arbitrary side.")
    lines.append("  This is the Monty Hall gain: switching doors has more information.")
    lines.append("")

    # Mean Monty Hall gain
    gains = [r.monty_hall_gain for r in batch.records]
    if gains:
        mean_gain = sum(gains) / len(gains)
        max_gain = max(gains)
        lines.append(f"  Mean Monty Hall gain:  {mean_gain:.4f}")
        lines.append(f"  Max Monty Hall gain:   {max_gain:.4f}")

    return "\n".join(lines)


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

    batch = score_and_expand_batch(test_texts)
    print(format_multipath_report(batch))
