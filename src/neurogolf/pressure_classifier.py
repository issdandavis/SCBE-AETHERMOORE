"""Pressure-axis classifier for ARC tasks.

Identifies whether a task is primarily shape-led, phase-led, or growth-led by
computing dot products against the three deterministic injection axes from the
14-layer pressure probe (arc_14layer_pressure_probe.py).

This classifier is a lightweight prefilter that reorders solver family candidates
so that families aligned with the dominant pressure axis are tried first. It uses
only per-example grid statistics — no 14-layer pipeline overhead.
"""
from __future__ import annotations

from typing import Literal

import numpy as np

from .arc_io import ARCTask


# ---------------------------------------------------------------------------
# Axis vectors from arc_14layer_pressure_probe.py — 12D, aligned with the
# task_packet_12 feature layout:
#   [0] input_density  [1] output_density  [2] growth/10
#   [3] sym_x          [4] sym_y           [5] bbox_fill
#   [6] in_entropy/4   [7] out_entropy/4   [8] tanh(color_delta/3)
#   [9] tanh(comp_delta/4)  [10] n_train/10  [11] n_test/10
# ---------------------------------------------------------------------------

_SHAPE_AXIS = np.array(
    [0.20, 0.00, 0.00, 0.15, 0.15, 0.10, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    dtype=np.float64,
)
_PHASE_AXIS = np.array(
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.12, 0.12, 0.00, 0.18, 0.00, 0.00],
    dtype=np.float64,
)
_GROWTH_AXIS = np.array(
    [0.00, 0.10, 0.25, 0.00, 0.00, 0.10, 0.00, 0.00, 0.08, 0.00, 0.00, 0.00],
    dtype=np.float64,
)

_AXES = np.stack([_SHAPE_AXIS, _PHASE_AXIS, _GROWTH_AXIS])  # (3, 12)
_AXIS_NORMS = np.maximum(np.linalg.norm(_AXES, axis=1), 1e-8)  # (3,)
_AXIS_LABELS: tuple[str, str, str] = ("shape-led", "phase-led", "growth-led")


# ---------------------------------------------------------------------------
# Solver family groupings per axis
# ---------------------------------------------------------------------------

_SHAPE_FAMILIES: frozenset[str] = frozenset({
    "flip_x",
    "flip_y",
    "transpose",
    "rotate_cw",
    "rotate_ccw",
    "rotate_180",
    "sym_complete_x",
    "sym_complete_y",
    "crop_then_flip_x",
    "crop_then_flip_y",
    "crop_then_transpose",
    "crop_then_rotate_cw",
    "crop_then_rotate_ccw",
    "crop_then_rotate_180",
    "tile_mirror_2x2",
    "tile_rotate_2x2",
    "h_concat_flip",
    "v_concat_flip",
    "connect_aligned_pairs",
})

_PHASE_FAMILIES: frozenset[str] = frozenset({
    "color_remap",
    "corner_legend_row_swap",
    "shift_then_color_remap",
    "flip_x_then_color_remap",
    "flip_y_then_color_remap",
    "transpose_then_color_remap",
    "rotate_cw_then_color_remap",
    "rotate_ccw_then_color_remap",
    "rotate_180_then_color_remap",
    "upscale_then_color_remap",
})

_GROWTH_FAMILIES: frozenset[str] = frozenset({
    "tile",
    "tile_self",
    "tile_self_complement",
    "panel_consensus_tile",
    "upscale",
    "upscale_color_count",
    "extract_panel",
    "extract_half_longer",
    "crop_bbox",
    "fill_enclosed",
    "paint_border",
})


# ---------------------------------------------------------------------------
# Feature extraction (mirrors task_packet_12 in arc_14layer_trace.py)
# ---------------------------------------------------------------------------


def _grid_density(grid: np.ndarray) -> float:
    return float(np.count_nonzero(grid)) / float(grid.size) if grid.size > 0 else 0.0


def _color_entropy(grid: np.ndarray) -> float:
    counts = np.bincount(grid.ravel(), minlength=10).astype(np.float64)
    total = counts.sum()
    if total == 0:
        return 0.0
    probs = counts / total
    nz = probs[probs > 0]
    return float(-(nz * np.log2(nz)).sum())


def _symmetry_score(grid: np.ndarray, axis: str) -> float:
    target = np.flipud(grid) if axis == "y" else np.fliplr(grid)
    return float(np.mean(grid == target))


def _bbox_fill_ratio(grid: np.ndarray) -> float:
    coords = np.argwhere(grid != 0)
    if coords.size == 0:
        return 0.0
    (r0, c0), (r1, c1) = coords.min(axis=0), coords.max(axis=0)
    area = float((r1 - r0 + 1) * (c1 - c0 + 1))
    return float(coords.shape[0]) / max(area, 1.0)


def _color_count(grid: np.ndarray) -> float:
    return float(len(np.unique(grid)))


def _component_count_fast(grid: np.ndarray) -> int:
    """4-connected components of non-zero pixels (same color, fast BFS)."""
    h, w = grid.shape
    visited = np.zeros((h, w), dtype=bool)
    count = 0
    for r in range(h):
        for c in range(w):
            if grid[r, c] == 0 or visited[r, c]:
                continue
            count += 1
            color = int(grid[r, c])
            stack = [(r, c)]
            visited[r, c] = True
            while stack:
                rr, cc = stack.pop()
                for nr, nc in ((rr - 1, cc), (rr + 1, cc), (rr, cc - 1), (rr, cc + 1)):
                    if (
                        0 <= nr < h
                        and 0 <= nc < w
                        and not visited[nr, nc]
                        and int(grid[nr, nc]) == color
                    ):
                        visited[nr, nc] = True
                        stack.append((nr, nc))
    return count


def _shape_growth(inp: np.ndarray, out: np.ndarray) -> float:
    return float(out.shape[0] * out.shape[1]) / max(float(inp.shape[0] * inp.shape[1]), 1.0)


def compute_task_features(task: ARCTask) -> np.ndarray:
    """12-value feature vector for a task (mirrors task_packet_12).

    Returns zeros if the task has no training examples.
    """
    in_dens: list[float] = []
    out_dens: list[float] = []
    growths: list[float] = []
    in_ent: list[float] = []
    out_ent: list[float] = []
    col_deltas: list[float] = []
    comp_deltas: list[float] = []
    sym_x_vals: list[float] = []
    sym_y_vals: list[float] = []
    bbox_fills: list[float] = []

    for ex in task.train:
        inp, out = ex.input, ex.output
        in_dens.append(_grid_density(inp))
        out_dens.append(_grid_density(out))
        in_ent.append(_color_entropy(inp))
        out_ent.append(_color_entropy(out))
        growths.append(_shape_growth(inp, out))
        col_deltas.append(_color_count(out) - _color_count(inp))
        comp_deltas.append(float(_component_count_fast(out) - _component_count_fast(inp)))
        sym_x_vals.append((_symmetry_score(inp, "x") + _symmetry_score(out, "x")) * 0.5)
        sym_y_vals.append((_symmetry_score(inp, "y") + _symmetry_score(out, "y")) * 0.5)
        bbox_fills.append((_bbox_fill_ratio(inp) + _bbox_fill_ratio(out)) * 0.5)

    if not in_dens:
        return np.zeros(12, dtype=np.float64)

    amp = np.array(
        [
            float(np.mean(in_dens)),
            float(np.mean(out_dens)),
            float(np.mean(growths)) / 10.0,
            float(np.mean(sym_x_vals)),
            float(np.mean(sym_y_vals)),
            float(np.mean(bbox_fills)),
        ],
        dtype=np.float64,
    )
    phase = np.array(
        [
            float(np.mean(in_ent)) / 4.0,
            float(np.mean(out_ent)) / 4.0,
            float(np.tanh(np.mean(col_deltas) / 3.0)),
            float(np.tanh(np.mean(comp_deltas) / 4.0)),
            float(len(task.train)) / 10.0,
            float(len(task.test_inputs)) / 10.0,
        ],
        dtype=np.float64,
    )
    return np.concatenate([amp, phase])


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def classify_pressure_axis(
    task: ARCTask,
    *,
    mix_threshold: float = 0.15,
) -> Literal["phase-led", "shape-led", "growth-led", "mixed"]:
    """Classify the dominant structural axis of an ARC task.

    Uses normalized dot products against the three deterministic injection
    axes from the 14-layer pressure probe. The dominant axis indicates which
    solver families to prioritize.

    Args:
        task: ARC task to classify.
        mix_threshold: If the gap between top and second score is below this
                       value, returns "mixed".

    Returns:
        "shape-led", "phase-led", "growth-led", or "mixed".
    """
    features = compute_task_features(task)
    scores = np.abs(_AXES @ features) / _AXIS_NORMS  # (3,)
    sorted_idx = np.argsort(scores)
    top_idx = int(sorted_idx[-1])
    second_idx = int(sorted_idx[-2])
    if float(scores[top_idx] - scores[second_idx]) < mix_threshold:
        return "mixed"
    return _AXIS_LABELS[top_idx]  # type: ignore[return-value]


def reorder_families_by_pressure(
    families: list[str],
    axis: Literal["phase-led", "shape-led", "growth-led", "mixed"],
) -> list[str]:
    """Reorder families so those matching the dominant axis come first.

    Preserves the relative order within each group. Returns the original list
    unchanged when axis is "mixed".
    """
    if axis == "mixed":
        return families
    axis_set = {
        "shape-led": _SHAPE_FAMILIES,
        "phase-led": _PHASE_FAMILIES,
        "growth-led": _GROWTH_FAMILIES,
    }[axis]
    promoted = [f for f in families if f in axis_set]
    others = [f for f in families if f not in axis_set]
    return promoted + others
