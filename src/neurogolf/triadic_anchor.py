"""Triadic Anchor Extractor for NeuroGolf ARC tasks.

Architecture (per the 3-layer design):
  1. SS1 tokenizer  — bijective identity spine (via token_braid.py)
  2. Tri-braid DNA  — local coupled-state layer (3 tongues per codon)
  3. Triadic anchor — find stable 3-variable couplings across examples;
                       these become the inward minimization target.

A triadic anchor is a triplet of (axis_i, axis_j, axis_k) indices from
the 6D topology vector where the ternary state stays *coupled and stable*
across all training examples of a task.  Stability means the triad's sign
pattern does not change between examples AND the three axes remain
mutually non-zero (no degenerate zero coupling).

Anchor quality score (Jaccard-style stability):
    Q = (stable_triplets / total_triplets) * mean_coupling_strength

Use as:
  anchors = extract_anchors(task)
  ranked  = rank_families_by_anchor(task, anchors)
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

import numpy as np

from .arc_io import ARCTask
from .family_lattice import AXES, FAMILY_TOPOLOGIES, FLAT_FAMILY_ORDER, task_topology
from .token_braid import BRAID_TONGUES, task_triad

PHI = (1 + math.sqrt(5)) / 2

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TriadicAnchor:
    """A stable 3-axis coupling extracted from task examples.

    axes:      3-tuple of axis index in the 6D topology vector.
    sign_pattern: ternary state of those axes — the stable signature.
    strength:  mean absolute value of the axes across examples (0–1).
               Higher = more active coupling (non-degenerate).
    stability: fraction of examples where this sign pattern held.
    """

    axes: tuple[int, int, int]
    sign_pattern: tuple[int, int, int]
    strength: float
    stability: float

    @property
    def axis_names(self) -> tuple[str, str, str]:
        return (AXES[self.axes[0]], AXES[self.axes[1]], AXES[self.axes[2]])

    @property
    def quality(self) -> float:
        """Combined quality score for ranking."""
        return self.stability * self.strength


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ALL_TRIPLETS: tuple[tuple[int, int, int], ...] = tuple(
    (i, j, k) for i, j, k in itertools.combinations(range(6), 3)
)


def _topology_per_example(task: ARCTask) -> list[np.ndarray]:
    """Return per-example topology vectors (shape 6,) using input grids."""
    from .arc_io import ARCTask as _Task  # local to avoid circular at module level

    vecs = []
    for ex in task.train:
        # Build a single-example pseudo-task for topology extraction
        pseudo = _Task(
            task_id=task.task_id,
            train=(ex,),
            test_inputs=(),
            source_path=task.source_path,
        )
        vecs.append(task_topology(pseudo))
    return vecs


def _ternary_sign(value: float) -> int:
    """Map a float to {-1, 0, +1} with dead-band around zero."""
    if value > 0.3:
        return 1
    if value < -0.3:
        return -1
    return 0


def _extract_sign_vectors(topology_vecs: list[np.ndarray]) -> list[tuple[int, ...]]:
    return [tuple(_ternary_sign(float(v)) for v in vec) for vec in topology_vecs]


# ---------------------------------------------------------------------------
# Core extractor
# ---------------------------------------------------------------------------


def extract_anchors(task: ARCTask, min_stability: float = 0.8) -> list[TriadicAnchor]:
    """Extract stable triadic anchors from a task's training examples.

    Parameters
    ----------
    task:            ARC task.
    min_stability:   Minimum fraction of examples where the sign pattern
                     must be consistent.  Default 0.8 (4/5 examples).

    Returns
    -------
    List of TriadicAnchor sorted by quality (descending).
    Empty list if the task has only one training example (no cross-example
    comparison possible).
    """
    topo_vecs = _topology_per_example(task)
    if len(topo_vecs) < 2:
        # Single example: use overall task topology as a degenerate anchor
        overall = task_topology(task)
        sign_vec = tuple(_ternary_sign(float(v)) for v in overall)
        anchors = []
        for axes in _ALL_TRIPLETS:
            pattern = (sign_vec[axes[0]], sign_vec[axes[1]], sign_vec[axes[2]])
            if all(s != 0 for s in pattern):  # non-degenerate
                strength = float(np.mean([abs(overall[a]) for a in axes]))
                anchors.append(
                    TriadicAnchor(
                        axes=axes,
                        sign_pattern=pattern,
                        strength=strength,
                        stability=1.0,
                    )
                )
        anchors.sort(key=lambda a: -a.quality)
        return anchors

    sign_vecs = _extract_sign_vectors(topo_vecs)
    n = len(sign_vecs)

    anchors: list[TriadicAnchor] = []
    for axes in _ALL_TRIPLETS:
        i, j, k = axes

        # Collect the sign pattern for this triplet across all examples
        patterns = [(sv[i], sv[j], sv[k]) for sv in sign_vecs]

        # Count the most common pattern (modal)
        from collections import Counter

        modal_pattern, modal_count = Counter(patterns).most_common(1)[0]
        stability = modal_count / n

        if stability < min_stability:
            continue

        # Require all three axes non-zero in the modal pattern (active coupling)
        if any(s == 0 for s in modal_pattern):
            continue

        # Coupling strength: mean absolute value across examples
        strength = float(
            np.mean([abs(float(topo_vecs[e][a])) for e in range(n) for a in axes])
        )

        anchors.append(
            TriadicAnchor(
                axes=axes,
                sign_pattern=modal_pattern,
                strength=strength,
                stability=stability,
            )
        )

    anchors.sort(key=lambda a: -a.quality)
    return anchors


# ---------------------------------------------------------------------------
# Family ranker using anchors
# ---------------------------------------------------------------------------


def _family_sign_pattern(family: str, axes: tuple[int, int, int]) -> tuple[int, int, int]:
    topo = FAMILY_TOPOLOGIES[family]
    return (topo.ternary[axes[0]], topo.ternary[axes[1]], topo.ternary[axes[2]])


def _anchor_match_score(family: str, anchors: list[TriadicAnchor]) -> float:
    """Score how well a family's ternary topology matches the task anchors."""
    if not anchors:
        return 0.0

    score = 0.0
    weight_sum = 0.0

    for anchor in anchors:
        family_pattern = _family_sign_pattern(family, anchor.axes)
        task_pattern = anchor.sign_pattern
        weight = anchor.quality  # stability * strength

        # Exact sign match
        exact = sum(1 for a, b in zip(family_pattern, task_pattern) if a == b)
        # Partial: at least same non-zero polarity on active axes
        partial = sum(
            1
            for a, b in zip(family_pattern, task_pattern)
            if a != 0 and b != 0 and a == b
        )

        match_ratio = (exact * 1.0 + partial * 0.5) / 3.0
        score += weight * match_ratio
        weight_sum += weight

    return score / weight_sum if weight_sum > 0 else 0.0


def rank_families_by_anchor(
    task: ARCTask,
    anchors: list[TriadicAnchor] | None = None,
) -> list[str]:
    """Rank solver families by triadic anchor match.

    If anchors is None, they are extracted from the task on the fly.
    """
    if anchors is None:
        anchors = extract_anchors(task)

    # Also pull the task's overall triad for a secondary signal
    task_triad_vec = task_triad(task)

    scored: list[tuple[str, float]] = []
    for family, topology in FAMILY_TOPOLOGIES.items():
        anchor_score = _anchor_match_score(family, anchors)

        # Secondary: overall triad alignment (reuse token_braid logic inline)
        triad_score = 0.0
        for idx, task_state in enumerate(task_triad_vec):
            family_state = topology.ternary[idx]
            if task_state == family_state:
                triad_score += 1.0
            elif task_state == 0 or family_state == 0:
                triad_score += 0.25
            else:
                triad_score -= 0.5
        triad_score /= max(len(task_triad_vec), 1)

        # Phi-weighted blend: anchor is primary, triad is secondary
        combined = (PHI / (PHI + 1)) * anchor_score + (1.0 / (PHI + 1)) * triad_score
        scored.append((family, combined))

    scored.sort(
        key=lambda item: (
            -item[1],
            FLAT_FAMILY_ORDER.index(item[0]) if item[0] in FLAT_FAMILY_ORDER else 999,
        )
    )
    return [family for family, _ in scored]


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def explain_anchors(task: ARCTask) -> dict[str, object]:
    """Return a human-readable anchor report for a task."""
    anchors = extract_anchors(task)
    topo = task_topology(task)
    return {
        "overall_topology": {axis: round(float(topo[i]), 3) for i, axis in enumerate(AXES)},
        "n_anchors": len(anchors),
        "top_anchors": [
            {
                "axes": anchor.axis_names,
                "sign_pattern": anchor.sign_pattern,
                "strength": round(anchor.strength, 3),
                "stability": round(anchor.stability, 3),
                "quality": round(anchor.quality, 3),
            }
            for anchor in anchors[:5]
        ],
    }
