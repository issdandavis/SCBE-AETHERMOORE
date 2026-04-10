"""
Multi-Path Generator — Breaking the Single-Trajectory Limitation
================================================================

LLMs traverse a single forward path through high-dimensional space,
collapsing possibilities at each step. The polymorphic edge cases
(23% of our corpus) are points where this collapse is most lossy —
multiple paths were nearly equally valid, but the system committed
to one.

This module exploits those polymorphic zones by generating
CONTRASTIVE training pairs: for each edge-case record, produce
both sides of the trit boundary so the model learns the full
topology of the decision space, not just one collapsed path.

The key insight (2026-04-05):
    At a trit boundary, the interference score is ~threshold.
    A tiny content shift flips the state. That means:
    - The SAME text encodes to DIFFERENT curriculum states
      depending on which tongue pair you emphasize
    - Both states are "true" — the boundary IS the information
    - Training on both sides teaches the model WHERE decisions
      are fragile and HOW to navigate ambiguity

Architecture:
    1. Identify polymorphic records (edge_distance < threshold)
    2. For each polymorphic axis, compute the "mirror state" —
       what the trit WOULD be if the score were on the other side
    3. Generate contrastive pairs: (original, mirror) with
       explicit boundary metadata
    4. Weight these pairs higher in training (they're the most
       informative samples)

This is NOT data augmentation. We're not inventing new data.
We're making the model aware of its own decision fragility.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from src.crypto.trit_curriculum import (
    TritSignal,
    TRIT_LABELS,
    TRIT_AXES,
    GEOMETRIC_BASELINES,
    DEFAULT_THRESHOLD,
    compute_trit_signal,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Edge threshold for polymorphic detection
POLY_THRESHOLD = 0.01

# How much to perturb when generating mirror states
# This is conceptual — we don't change the TEXT, we record
# what the trit WOULD be on the other side of the boundary
BOUNDARY_EPSILON = 0.001


# ---------------------------------------------------------------------------
# Multi-path record
# ---------------------------------------------------------------------------

@dataclass
class PathFork:
    """A single axis where the path could have gone either way."""
    axis: str              # "structure", "stability", "creativity"
    actual_trit: int       # What the system chose: +1, 0, -1
    mirror_trit: int       # What it WOULD have been on the other side
    edge_distance: float   # How close to the boundary
    deviation: float       # Raw deviation from geometric baseline
    threshold: float       # The boundary location


@dataclass
class MultiPathRecord:
    """A training record augmented with multi-path information."""
    # Original trit signal
    original: TritSignal

    # Which axes are polymorphic (near boundary)
    forks: List[PathFork]

    # The mirror state: what the trit vector would be
    # if ALL polymorphic axes flipped
    mirror_vector: Tuple[int, int, int]
    mirror_label: str
    mirror_index: int

    # Number of possible paths at this point
    # 2^(number of polymorphic axes)
    path_count: int

    # Training weight multiplier
    # Higher = more informative = train harder on this
    weight: float

    # Monty Hall advantage: (2^N - 1) / 2^N
    # The fraction of information held by the UNEXPLORED paths.
    # With 1 fork (2 doors): 0.5  — switching is coin-flip
    # With 2 forks (4 doors): 0.75 — switching wins 75%
    # With 3 forks (8 doors): 0.875 — switching wins 87.5%
    # The more forks, the more the collapsed path MISSED.
    monty_hall_advantage: float

    # Weight for the mirror state specifically
    # mirror_weight = weight * monty_hall_advantage
    mirror_weight: float

    # All possible trit states this record could occupy
    reachable_states: List[Tuple[int, int, int]]
    reachable_labels: List[str]

    def to_dict(self) -> dict:
        """Serialize for SFT metadata."""
        return {
            "original_trit": self.original.to_dict(),
            "is_multipath": len(self.forks) > 0,
            "path_count": self.path_count,
            "forks": [
                {
                    "axis": f.axis,
                    "actual": f.actual_trit,
                    "mirror": f.mirror_trit,
                    "edge_distance": round(f.edge_distance, 6),
                    "deviation": round(f.deviation, 4),
                }
                for f in self.forks
            ],
            "mirror_vector": list(self.mirror_vector),
            "mirror_label": self.mirror_label,
            "reachable_states": [list(s) for s in self.reachable_states],
            "reachable_labels": self.reachable_labels,
            "weight": round(self.weight, 4),
            "monty_hall_advantage": round(self.monty_hall_advantage, 6),
            "mirror_weight": round(self.mirror_weight, 4),
        }


# ---------------------------------------------------------------------------
# Core: compute multi-path record from trit signal
# ---------------------------------------------------------------------------

def _flip_trit(trit: int, deviation: float, threshold: float) -> int:
    """Compute what the trit would be on the other side of the boundary."""
    if deviation > 0:
        # Currently above some boundary — mirror to below
        if trit == +1:
            return 0   # Was above +threshold, mirror to below
        elif trit == 0 and deviation > 0:
            return +1 if abs(deviation - threshold) < abs(deviation + threshold) else -1
        else:
            return 0
    else:
        # Currently below some boundary — mirror to above
        if trit == -1:
            return 0
        elif trit == 0 and deviation < 0:
            return -1 if abs(deviation + threshold) < abs(deviation - threshold) else +1
        else:
            return 0


def compute_multipath(
    trit: TritSignal,
    poly_threshold: float = POLY_THRESHOLD,
    content_threshold: float = 0.05,
) -> MultiPathRecord:
    """Compute multi-path information for a trit signal.

    For each polymorphic axis, determines the mirror trit and
    enumerates all reachable states.
    """
    forks = []
    content_trits = list(trit.content_vector)
    deviations = list(trit.dev_vector)
    edges = list(trit.edge_vector)
    axis_names = ["structure", "stability", "creativity"]

    for i, (axis, ct, dev, edge) in enumerate(
        zip(axis_names, content_trits, deviations, edges)
    ):
        if edge < poly_threshold:
            mirror = _flip_trit(ct, dev, content_threshold)
            forks.append(PathFork(
                axis=axis,
                actual_trit=ct,
                mirror_trit=mirror,
                edge_distance=edge,
                deviation=dev,
                threshold=content_threshold,
            ))

    # Compute mirror vector (all forks flipped)
    mirror_trits = list(content_trits)
    for fork in forks:
        idx = axis_names.index(fork.axis)
        mirror_trits[idx] = fork.mirror_trit

    mirror_tuple = tuple(mirror_trits)
    mirror_label = TRIT_LABELS.get(mirror_tuple, f"unknown_{mirror_tuple}")
    mirror_index = (1 - mirror_trits[0]) * 9 + (1 - mirror_trits[1]) * 3 + (1 - mirror_trits[2])

    # Enumerate all reachable states (2^n_forks combinations)
    fork_indices = [axis_names.index(f.axis) for f in forks]
    fork_options = [(f.actual_trit, f.mirror_trit) for f in forks]

    reachable = []
    n_forks = len(forks)
    for mask in range(2 ** n_forks):
        state = list(content_trits)
        for j in range(n_forks):
            if mask & (1 << j):
                state[fork_indices[j]] = fork_options[j][1]  # mirror
            # else: keep actual
        reachable.append(tuple(state))

    reachable_labels = [
        TRIT_LABELS.get(s, f"unknown_{s}") for s in reachable
    ]

    # Training weight: inversely proportional to min edge distance
    # Polymorphic records are MORE informative, so weight them higher
    if forks:
        min_edge = min(f.edge_distance for f in forks)
        # Weight: 1.0 for non-polymorphic, up to 5.0 for hyper-edge
        weight = 1.0 + 4.0 * max(0, 1.0 - min_edge / poly_threshold)
    else:
        weight = 1.0

    # Monty Hall advantage: the 3-door problem generalized to 2^N doors
    #
    # Classic Monty Hall: 3 doors, you pick 1, host opens 1 losing door.
    #   Switching wins 2/3 of the time. Advantage = (3-1)/3 = 0.667
    #
    # Generalized: 2^N doors (one per reachable state).
    #   You "picked" the collapsed observation (1 door).
    #   The remaining 2^N - 1 doors collectively hold the mirror states.
    #   Switching advantage = (2^N - 1) / 2^N
    #
    # N=0: 1 door, advantage = 0.0   (no polymorphism, no switching)
    # N=1: 2 doors, advantage = 0.5  (coin flip — switching is neutral)
    # N=2: 4 doors, advantage = 0.75 (switching wins 75%)
    # N=3: 8 doors, advantage = 0.875 (switching wins 87.5%)
    #
    # The MORE polymorphic the record, the MORE the collapsed path missed.
    # Mirror states should be weighted by this advantage.
    doors = 2 ** n_forks
    monty_hall_advantage = (doors - 1) / doors if doors > 1 else 0.0
    mirror_weight = weight * monty_hall_advantage

    return MultiPathRecord(
        original=trit,
        forks=forks,
        mirror_vector=mirror_tuple,
        mirror_label=mirror_label,
        mirror_index=mirror_index,
        path_count=doors,
        weight=weight,
        monty_hall_advantage=monty_hall_advantage,
        mirror_weight=mirror_weight,
        reachable_states=reachable,
        reachable_labels=reachable_labels,
    )


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def compute_multipath_batch(
    trits: List[TritSignal],
    poly_threshold: float = POLY_THRESHOLD,
) -> List[MultiPathRecord]:
    """Compute multi-path records for a batch of trit signals."""
    return [compute_multipath(t, poly_threshold) for t in trits]


def multipath_summary(records: List[MultiPathRecord]) -> dict:
    """Summary statistics for multi-path analysis."""
    if not records:
        return {"count": 0}

    n = len(records)
    multipath_count = sum(1 for r in records if r.forks)
    total_forks = sum(len(r.forks) for r in records)
    total_paths = sum(r.path_count for r in records)

    # Weight distribution
    weights = [r.weight for r in records]
    mean_weight = sum(weights) / n
    max_weight = max(weights)

    # Monty Hall stats
    mh_advantages = [r.monty_hall_advantage for r in records if r.forks]
    mean_mh = sum(mh_advantages) / len(mh_advantages) if mh_advantages else 0.0
    mirror_weights = [r.mirror_weight for r in records if r.forks]
    mean_mirror_w = sum(mirror_weights) / len(mirror_weights) if mirror_weights else 0.0

    # Fork axis distribution
    axis_counts = {"structure": 0, "stability": 0, "creativity": 0}
    for r in records:
        for f in r.forks:
            axis_counts[f.axis] += 1

    # State reachability
    all_reachable = set()
    for r in records:
        for s in r.reachable_states:
            all_reachable.add(s)

    # Mirror label distribution
    mirror_dist = {}
    for r in records:
        if r.forks:
            mirror_dist[r.mirror_label] = mirror_dist.get(r.mirror_label, 0) + 1

    # Path count distribution
    path_dist = {}
    for r in records:
        pc = r.path_count
        path_dist[pc] = path_dist.get(pc, 0) + 1

    return {
        "count": n,
        "multipath_count": multipath_count,
        "multipath_pct": round(multipath_count / n * 100, 1),
        "total_forks": total_forks,
        "total_reachable_paths": total_paths,
        "mean_paths_per_record": round(total_paths / n, 2),
        "unique_reachable_states": len(all_reachable),
        "fork_axis_distribution": axis_counts,
        "path_count_distribution": dict(sorted(path_dist.items())),
        "mirror_label_distribution": dict(sorted(mirror_dist.items(), key=lambda x: -x[1])),
        "weight_stats": {
            "mean": round(mean_weight, 4),
            "max": round(max_weight, 4),
        },
        "monty_hall": {
            "mean_advantage": round(mean_mh, 4),
            "mean_mirror_weight": round(mean_mirror_w, 4),
            "polymorphic_records": len(mh_advantages),
        },
    }


# ---------------------------------------------------------------------------
# Contrastive pair generation for SFT
# ---------------------------------------------------------------------------

def generate_contrastive_pairs(
    records: List[MultiPathRecord],
    texts: List[str],
) -> List[dict]:
    """Generate contrastive SFT training pairs from multi-path records.

    For each polymorphic record, creates a training pair that shows
    BOTH sides of the trit boundary:

    User: "This text sits at a trit boundary. What are the possible states?"
    Assistant: "State A (actual): [+1, 0, -1] = architect
               State B (mirror): [0, 0, -1] = dream
               The boundary is on the structure axis at distance 0.003.
               Both interpretations are valid — the text is polymorphic."

    This teaches the model to recognize and reason about ambiguity
    instead of collapsing to a single answer.
    """
    pairs = []

    for record, text in zip(records, texts):
        if not record.forks:
            continue  # Only multipath records get contrastive pairs

        # Build the contrastive description
        fork_descriptions = []
        for fork in record.forks:
            fork_descriptions.append(
                f"- {fork.axis} axis: actual={fork.actual_trit:+d}, "
                f"mirror={fork.mirror_trit:+d}, "
                f"edge_distance={fork.edge_distance:.6f}"
            )

        actual_label = record.original.label
        mirror_label = record.mirror_label
        actual_vec = list(record.original.content_vector)
        mirror_vec = list(record.mirror_vector)

        user_content = (
            f"Analyze the trit boundary state of this text:\n\n"
            f"\"{text[:200]}\"\n\n"
            f"This text has {len(record.forks)} polymorphic "
            f"{'axis' if len(record.forks) == 1 else 'axes'}. "
            f"What are all reachable curriculum states?"
        )

        assistant_content = (
            f"This text sits at {len(record.forks)} trit "
            f"{'boundary' if len(record.forks) == 1 else 'boundaries'}, "
            f"making it quasi-polymorphic with {record.path_count} reachable states.\n\n"
            f"**Actual state:** {actual_vec} = {actual_label}\n"
            f"**Mirror state:** {list(mirror_vec)} = {mirror_label}\n\n"
            f"Polymorphic axes:\n"
            + "\n".join(fork_descriptions) +
            f"\n\n**All reachable states:**\n"
            + "\n".join(
                f"- {list(s)} = {l}"
                for s, l in zip(record.reachable_states, record.reachable_labels)
            ) +
            f"\n\nThe boundary crossings represent points where the model's "
            f"interpretation can flip — these are the most informative "
            f"training samples because they expose decision fragility.\n\n"
            f"**Monty Hall analysis:** With {record.path_count} reachable states "
            f"(doors), the collapsed observation covers 1/{record.path_count} of "
            f"the possibility space. The mirror states collectively hold "
            f"{record.monty_hall_advantage:.1%} of the information — switching "
            f"(exploring mirrors) is {'strongly ' if record.monty_hall_advantage > 0.6 else ''}"
            f"favored.\n"
            f"Training weight: {record.weight:.2f}x (actual), "
            f"{record.mirror_weight:.2f}x (mirror)"
        )

        pairs.append({
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ],
            "metadata": {
                "source": "multipath_contrastive_generator",
                "record_type": "contrastive_boundary_pair",
                "multipath": record.to_dict(),
            },
        })

    return pairs


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from src.crypto.trit_curriculum import compute_trit_batch

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
    print("MULTI-PATH GENERATOR -- Breaking Single-Trajectory Collapse")
    print("=" * 70)
    print()

    # Compute trits
    trits = compute_trit_batch(test_texts)

    # Compute multipaths
    multipaths = compute_multipath_batch(trits)

    # Display
    for text, mp in zip(test_texts, multipaths):
        if mp.forks:
            actual = list(mp.original.content_vector)
            mirror = list(mp.mirror_vector)
            axes = [f.axis for f in mp.forks]
            print(f"  ** POLYMORPHIC ** paths={mp.path_count}  weight={mp.weight:.2f}x  "
                  f"monty_hall={mp.monty_hall_advantage:.1%}")
            print(f"     actual: {actual} = {mp.original.label}  (weight: {mp.weight:.2f}x)")
            print(f"     mirror: {mirror} = {mp.mirror_label}  (weight: {mp.mirror_weight:.2f}x)")
            print(f"     axes: {', '.join(axes)}")
            print(f"     reachable: {mp.reachable_labels}")
            print(f"     text: {text[:50]}")
            print()
        else:
            actual = list(mp.original.content_vector)
            print(f"  STABLE  {actual} = {mp.original.label:16s}  {text[:50]}")

    print()
    summary = multipath_summary(multipaths)
    print(f"Multi-path records: {summary['multipath_count']}/{summary['count']} "
          f"({summary['multipath_pct']}%)")
    print(f"Total reachable paths: {summary['total_reachable_paths']}")
    print(f"Unique reachable states: {summary['unique_reachable_states']}/27")
    print(f"Mean paths per record: {summary['mean_paths_per_record']}")
    print(f"Mean weight: {summary['weight_stats']['mean']:.2f}x  "
          f"Max weight: {summary['weight_stats']['max']:.2f}x")
    print()
    print("Fork axis distribution:")
    for axis, count in summary["fork_axis_distribution"].items():
        print(f"  {axis:12s}: {count}")
    print()
    print("Path count distribution:")
    for pc, count in summary["path_count_distribution"].items():
        print(f"  {pc} paths: {count} records")

    # Monty Hall stats
    print()
    print("Monty Hall Analysis (3-Door Problem of Max Paths):")
    mh = summary["monty_hall"]
    print(f"  Mean advantage: {mh['mean_advantage']:.1%}")
    print(f"  Mean mirror weight: {mh['mean_mirror_weight']:.2f}x")
    print(f"  Polymorphic records benefiting: {mh['polymorphic_records']}")
    print()
    print("  Interpretation:")
    print("    At each polymorphic boundary, the model COLLAPSED to one path.")
    print("    The mirror states collectively hold MORE information than")
    print("    the chosen path — just like switching doors in Monty Hall.")
    print("    The more forks, the more the collapse MISSED.")

    # Generate contrastive pairs
    pairs = generate_contrastive_pairs(multipaths, test_texts)
    print()
    print(f"Contrastive training pairs generated: {len(pairs)}")
