from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .arc_io import ARCExample, ARCTask
from .components import connected_components

AXES = (
    "shape",
    "motion",
    "color",
    "scope",
    "topology",
    "composition",
)

FLAT_FAMILY_ORDER = [
    "identity",
    "tile_self",
    "tile_self_complement",
    "tile",
    "tile_mirror_2x2",
    "tile_rotate_2x2",
    "connect_aligned_pairs",
    "corner_legend_row_swap",
    "panel_consensus_tile",
    "h_concat_flip",
    "v_concat_flip",
    "upscale",
    "upscale_then_color_remap",
    "upscale_color_count",
    "crop_bbox",
    "crop",
    "extract_panel",
    "extract_half_longer",
    "gravity_up",
    "gravity_down",
    "gravity_left",
    "gravity_right",
    "sym_complete_x",
    "sym_complete_y",
    "fill_enclosed",
    "paint_border",
    "crop_then_flip_x",
    "crop_then_flip_y",
    "crop_then_transpose",
    "crop_then_rotate_cw",
    "crop_then_rotate_ccw",
    "crop_then_rotate_180",
    "color_remap",
    "shift",
    "dominant_component_shift",
    "dominant_component_copy",
    "multi_unique_color_shift",
    "flip_x",
    "flip_y",
    "transpose",
    "rotate_cw",
    "rotate_ccw",
    "rotate_180",
    "shift_then_color_remap",
    "flip_x_then_color_remap",
    "flip_y_then_color_remap",
    "transpose_then_color_remap",
    "rotate_cw_then_color_remap",
    "rotate_ccw_then_color_remap",
    "rotate_180_then_color_remap",
    "select_dominant_color",
    "select_largest_cc",
    "select_minority_color",
    "select_then_crop",
    "select_then_gravity_down",
    "select_dominant_color+crop",
    "select_largest_cc+crop",
    "select_minority_color+crop",
    "paste_center",
    "paste_tile",
    "paste_stamp",
    "select_dominant_color+paste_center",
    "select_largest_cc+paste_center",
    "select_minority_color+paste_center",
    "select_dominant_color+paste_tile",
    "select_single_color_crop",
    "select_single_color_crop_orient",
    "select_smallest_cc_crop",
    "select_second_color_crop",
    "mask_by_color",
    "sym_complete_180_frames",
    "template_stamp",
    "tile_marker_propagate",
    "diagonal_project",
    "diagonal_cross_connect",
    "marker_erase_outside",
    "panel_dihedral_complete",
    "largest_zero_rect_fill",
    "dihedral_template_match",
    "panel_complement_fill",
    "panel_boolean_op",
]


@dataclass(frozen=True)
class FamilyTopology:
    family: str
    vector: tuple[float, float, float, float, float, float]
    charge: float
    ternary: tuple[int, int, int, int, int, int]

    def as_array(self) -> np.ndarray:
        return np.asarray(self.vector, dtype=np.float64)


FAMILY_TOPOLOGIES: dict[str, FamilyTopology] = {
    "identity": FamilyTopology("identity", (0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0.0, (0, 0, 0, 0, 0, 0)),
    "tile_self": FamilyTopology("tile_self", (1.0, 0.2, 0.2, 1.0, 0.9, 0.1), 1.0, (1, 0, 0, 1, 1, 0)),
    "tile_self_complement": FamilyTopology(
        "tile_self_complement", (1.0, 0.2, 0.6, 1.0, 0.9, 0.2), 1.0, (1, 0, 1, 1, 1, 0)
    ),
    "tile": FamilyTopology("tile", (0.9, 0.1, 0.0, 0.8, 0.8, 0.0), 0.9, (1, 0, 0, 1, 1, 0)),
    "connect_aligned_pairs": FamilyTopology(
        "connect_aligned_pairs", (0.1, 0.8, 0.4, 0.6, 0.7, 0.2), 0.7, (0, 1, 1, 1, 1, 0)
    ),
    "corner_legend_row_swap": FamilyTopology(
        "corner_legend_row_swap", (0.0, 0.1, 0.9, 0.6, 0.2, 0.2), 0.55, (0, 0, 1, 1, 0, 0)
    ),
    "panel_consensus_tile": FamilyTopology(
        "panel_consensus_tile", (0.4, 0.2, 0.2, 1.0, 0.9, 0.5), 0.9, (1, 0, 0, 1, 1, 1)
    ),
    "upscale": FamilyTopology("upscale", (1.0, 0.3, 0.2, 0.4, 0.7, 0.0), 0.8, (1, 0, 0, 1, 1, 0)),
    # upscale_then_color_remap: shape-expanding (high) + color transform (high) + compound (high)
    # Topology sits between upscale and the pure *_then_color_remap cluster.
    "upscale_then_color_remap": FamilyTopology(
        "upscale_then_color_remap", (1.0, 0.1, 0.8, 0.4, 0.5, 0.9), 0.85, (1, 0, 1, 0, 1, 1)
    ),
    "upscale_color_count": FamilyTopology(
        "upscale_color_count", (1.0, 0.3, 0.5, 0.6, 0.7, 0.2), 0.85, (1, 0, 1, 1, 1, 0)
    ),
    "crop_bbox": FamilyTopology("crop_bbox", (0.8, 0.0, 0.0, 0.9, 0.5, 0.0), 0.7, (1, 0, 0, 1, 0, 0)),
    "crop": FamilyTopology("crop", (0.8, 0.0, 0.0, 0.9, 0.5, 0.0), 0.7, (1, 0, 0, 1, 0, 0)),
    "gravity_up": FamilyTopology("gravity_up", (0.0, 1.0, 0.0, 0.1, 0.3, 0.0), 0.3, (0, 1, 0, 0, 0, 0)),
    "gravity_down": FamilyTopology("gravity_down", (0.0, 1.0, 0.0, 0.1, 0.3, 0.0), 0.3, (0, 1, 0, 0, 0, 0)),
    "gravity_left": FamilyTopology("gravity_left", (0.0, 1.0, 0.0, 0.1, 0.3, 0.0), 0.3, (0, 1, 0, 0, 0, 0)),
    "gravity_right": FamilyTopology("gravity_right", (0.0, 1.0, 0.0, 0.1, 0.3, 0.0), 0.3, (0, 1, 0, 0, 0, 0)),
    "sym_complete_x": FamilyTopology("sym_complete_x", (0.0, 1.0, 0.0, 0.0, 0.5, 0.4), 0.4, (0, 1, 0, 0, 1, 1)),
    "sym_complete_y": FamilyTopology("sym_complete_y", (0.0, 1.0, 0.0, 0.0, 0.5, 0.4), 0.4, (0, 1, 0, 0, 1, 1)),
    # --- object-level / layout families ---
    # fill_enclosed: same-shape, topology-driven (enclosed region detection), color secondary
    "fill_enclosed": FamilyTopology("fill_enclosed", (0.1, 0.0, 0.5, 0.7, 0.9, 0.0), 0.70, (0, 0, 1, 1, 1, 0)),
    # paint_border: same-shape, color primary (uniform border recolor), scope secondary
    "paint_border": FamilyTopology("paint_border", (0.0, 0.0, 0.5, 0.5, 0.4, 0.0), 0.50, (0, 0, 1, 1, 0, 0)),
    # h_concat_flip: shape-expanding (doubles width), motion via mirror symmetry
    "h_concat_flip": FamilyTopology("h_concat_flip", (0.8, 0.7, 0.0, 0.7, 0.6, 0.3), 0.75, (1, 1, 0, 1, 1, 0)),
    # v_concat_flip: same as h_concat_flip but vertical
    "v_concat_flip": FamilyTopology("v_concat_flip", (0.8, 0.7, 0.0, 0.7, 0.6, 0.3), 0.75, (1, 1, 0, 1, 1, 0)),
    # extract_panel: shape-reducing, scope-isolating (panel from grid layout)
    "extract_panel": FamilyTopology("extract_panel", (0.9, 0.0, 0.0, 1.0, 0.5, 0.0), 0.75, (1, 0, 0, 1, 0, 0)),
    # extract_half_longer: shape-reducing, scope-isolating (half along longer axis)
    "extract_half_longer": FamilyTopology(
        "extract_half_longer", (0.9, 0.0, 0.0, 0.8, 0.2, 0.0), 0.60, (1, 0, 0, 1, 0, 0)
    ),
    "crop_then_flip_x": FamilyTopology("crop_then_flip_x", (0.9, 1.0, 0.0, 0.9, 0.3, 0.1), 0.6, (1, 1, 0, 1, 0, 0)),
    "crop_then_flip_y": FamilyTopology("crop_then_flip_y", (0.9, 1.0, 0.0, 0.9, 0.3, 0.1), 0.6, (1, 1, 0, 1, 0, 0)),
    "crop_then_transpose": FamilyTopology(
        "crop_then_transpose", (1.0, 1.0, 0.0, 0.9, 0.3, 0.1), 0.6, (1, 1, 0, 1, 0, 0)
    ),
    "crop_then_rotate_cw": FamilyTopology(
        "crop_then_rotate_cw", (1.0, 1.0, 0.0, 0.9, 0.5, 0.1), 0.6, (1, 1, 0, 1, 1, 0)
    ),
    "crop_then_rotate_ccw": FamilyTopology(
        "crop_then_rotate_ccw", (1.0, 1.0, 0.0, 0.9, 0.5, 0.1), 0.6, (1, 1, 0, 1, 1, 0)
    ),
    "crop_then_rotate_180": FamilyTopology(
        "crop_then_rotate_180", (0.9, 1.0, 0.0, 0.9, 0.8, 0.1), 0.6, (1, 1, 0, 1, 1, 0)
    ),
    "tile_mirror_2x2": FamilyTopology("tile_mirror_2x2", (0.8, 1.0, 0.0, 0.9, 0.8, 0.3), 0.9, (1, 1, 0, 1, 1, 0)),
    "tile_rotate_2x2": FamilyTopology("tile_rotate_2x2", (0.8, 1.0, 0.0, 0.9, 0.9, 0.3), 0.9, (1, 1, 0, 1, 1, 0)),
    "color_remap": FamilyTopology("color_remap", (0.0, 0.0, 1.0, 0.1, 0.0, 0.0), 0.2, (0, 0, 1, 0, 0, 0)),
    "shift": FamilyTopology("shift", (0.0, 1.0, 0.0, 0.1, 0.1, 0.0), 0.3, (0, 1, 0, 0, 0, 0)),
    "dominant_component_shift": FamilyTopology(
        "dominant_component_shift", (0.1, 0.9, 0.0, 0.8, 0.5, 0.0), 0.5, (0, 1, 0, 1, 0, 0)
    ),
    "dominant_component_copy": FamilyTopology(
        "dominant_component_copy", (0.1, 0.6, 0.0, 0.8, 1.0, 0.0), 0.8, (0, 1, 0, 1, 1, 0)
    ),
    "multi_unique_color_shift": FamilyTopology(
        "multi_unique_color_shift", (0.1, 0.8, 0.5, 0.8, 0.6, 0.3), 0.7, (0, 1, 1, 1, 0, 1)
    ),
    "flip_x": FamilyTopology("flip_x", (0.0, 1.0, 0.0, 0.0, 0.2, 0.0), 0.2, (0, 1, 0, 0, 0, 0)),
    "flip_y": FamilyTopology("flip_y", (0.0, 1.0, 0.0, 0.0, 0.2, 0.0), 0.2, (0, 1, 0, 0, 0, 0)),
    "transpose": FamilyTopology("transpose", (0.2, 1.0, 0.0, 0.0, 0.2, 0.0), 0.3, (0, 1, 0, 0, 0, 0)),
    "shift_then_color_remap": FamilyTopology(
        "shift_then_color_remap", (0.0, 0.9, 1.0, 0.2, 0.1, 1.0), 0.7, (0, 1, 1, 0, 0, 1)
    ),
    "flip_x_then_color_remap": FamilyTopology(
        "flip_x_then_color_remap", (0.0, 0.9, 1.0, 0.1, 0.1, 1.0), 0.6, (0, 1, 1, 0, 0, 1)
    ),
    "flip_y_then_color_remap": FamilyTopology(
        "flip_y_then_color_remap", (0.0, 0.9, 1.0, 0.1, 0.1, 1.0), 0.6, (0, 1, 1, 0, 0, 1)
    ),
    "transpose_then_color_remap": FamilyTopology(
        "transpose_then_color_remap", (0.2, 0.9, 1.0, 0.1, 0.1, 1.0), 0.6, (0, 1, 1, 0, 0, 1)
    ),
    "rotate_cw": FamilyTopology("rotate_cw", (0.3, 1.0, 0.0, 0.0, 0.5, 0.0), 0.3, (0, 1, 0, 0, 1, 0)),
    "rotate_ccw": FamilyTopology("rotate_ccw", (0.3, 1.0, 0.0, 0.0, 0.5, 0.0), 0.3, (0, 1, 0, 0, 1, 0)),
    "rotate_180": FamilyTopology("rotate_180", (0.0, 1.0, 0.0, 0.0, 0.8, 0.0), 0.3, (0, 1, 0, 0, 1, 0)),
    "rotate_cw_then_color_remap": FamilyTopology(
        "rotate_cw_then_color_remap", (0.3, 0.9, 1.0, 0.1, 0.5, 1.0), 0.6, (0, 1, 1, 0, 1, 1)
    ),
    "rotate_ccw_then_color_remap": FamilyTopology(
        "rotate_ccw_then_color_remap", (0.3, 0.9, 1.0, 0.1, 0.5, 1.0), 0.6, (0, 1, 1, 0, 1, 1)
    ),
    "rotate_180_then_color_remap": FamilyTopology(
        "rotate_180_then_color_remap", (0.0, 0.9, 1.0, 0.1, 0.8, 1.0), 0.6, (0, 1, 1, 0, 1, 1)
    ),
    # --- object selection families ---
    # Destructive mask: non-selected pixels become 0.
    # Topology: scope is the primary signal (object isolation is inherently about scope).
    # Color is secondary. Shape only enters for CC-based selection.
    # Keep motion=0.0 to avoid displacing shift/gravity families.
    "select_dominant_color": FamilyTopology(
        "select_dominant_color", (0.1, 0.0, 0.4, 0.9, 0.2, 0.0), 0.5, (0, 0, 1, 1, 0, 0)
    ),
    "select_largest_cc": FamilyTopology("select_largest_cc", (0.5, 0.0, 0.2, 0.9, 0.4, 0.0), 0.6, (1, 0, 0, 1, 0, 0)),
    "select_minority_color": FamilyTopology(
        "select_minority_color", (0.0, 0.0, 0.3, 0.8, 0.1, 0.0), 0.4, (0, 0, 1, 1, 0, 0)
    ),
    "select_then_crop": FamilyTopology("select_then_crop", (0.8, 0.0, 0.3, 1.0, 0.4, 0.0), 0.65, (1, 0, 0, 1, 0, 0)),
    "select_then_gravity_down": FamilyTopology(
        "select_then_gravity_down", (0.1, 0.5, 0.2, 0.9, 0.3, 0.0), 0.55, (0, 1, 0, 1, 0, 0)
    ),
    # --- compound select+crop families (generated by depth-2 compose logic) ---
    # Name format: "select_X+crop" — scope isolation followed by bbox extraction.
    # Scope remains the primary axis; shape is secondary (crop shrinks to content bbox).
    # --- paste families ---
    # paste_center: scope high (object-level), composition high (canvas restructuring)
    # motion moderate (content moves to center)
    "paste_center": FamilyTopology("paste_center", (0.5, 0.5, 0.0, 0.9, 0.3, 0.7), 0.6, (1, 1, 0, 1, 0, 1)),
    "paste_tile": FamilyTopology("paste_tile", (0.8, 0.2, 0.0, 0.7, 0.9, 0.8), 0.7, (1, 0, 0, 1, 1, 1)),
    "paste_stamp": FamilyTopology("paste_stamp", (0.6, 0.3, 0.0, 0.8, 0.8, 0.9), 0.65, (1, 0, 0, 1, 1, 1)),
    # compound: select then paste (common 2-step patterns)
    "select_dominant_color+paste_center": FamilyTopology(
        "select_dominant_color+paste_center", (0.5, 0.5, 0.3, 1.0, 0.3, 0.7), 0.65, (1, 1, 0, 1, 0, 1)
    ),
    "select_largest_cc+paste_center": FamilyTopology(
        "select_largest_cc+paste_center", (0.6, 0.5, 0.1, 1.0, 0.4, 0.7), 0.7, (1, 1, 0, 1, 0, 1)
    ),
    "select_minority_color+paste_center": FamilyTopology(
        "select_minority_color+paste_center", (0.5, 0.5, 0.2, 1.0, 0.2, 0.7), 0.6, (1, 1, 0, 1, 0, 1)
    ),
    "select_dominant_color+paste_tile": FamilyTopology(
        "select_dominant_color+paste_tile", (0.8, 0.2, 0.3, 0.9, 0.9, 0.8), 0.7, (1, 0, 0, 1, 1, 1)
    ),
    "select_dominant_color+crop": FamilyTopology(
        "select_dominant_color+crop", (0.8, 0.0, 0.3, 1.0, 0.3, 0.0), 0.65, (1, 0, 0, 1, 0, 0)
    ),
    "select_largest_cc+crop": FamilyTopology(
        "select_largest_cc+crop", (0.9, 0.0, 0.1, 1.0, 0.4, 0.0), 0.7, (1, 0, 0, 1, 0, 0)
    ),
    "select_minority_color+crop": FamilyTopology(
        "select_minority_color+crop", (0.8, 0.0, 0.2, 1.0, 0.2, 0.0), 0.6, (1, 0, 0, 1, 0, 0)
    ),
}


def _mean(items: Iterable[float]) -> float:
    seq = tuple(items)
    return float(np.mean(seq)) if seq else 0.0


def _boundary_ratio(grid: np.ndarray) -> float:
    h, w = grid.shape
    if h == 0 or w == 0:
        return 0.0
    touched = np.zeros_like(grid, dtype=np.int64)
    touched[1:, :] += grid[1:, :] != grid[:-1, :]
    touched[:-1, :] += grid[:-1, :] != grid[1:, :]
    touched[:, 1:] += grid[:, 1:] != grid[:, :-1]
    touched[:, :-1] += grid[:, :-1] != grid[:, 1:]
    return float((touched > 0).sum()) / float(grid.size)


def _component_density(grid: np.ndarray) -> float:
    _, components = connected_components(grid)
    return min(1.0, len(components) / max(float(grid.size), 1.0) * 12.0)


def _pattern_signature(grid: np.ndarray) -> tuple[tuple[int, ...], ...]:
    labels: dict[int, int] = {}
    next_label = 1
    rows: list[tuple[int, ...]] = []
    for row in grid:
        encoded: list[int] = []
        for value in row:
            value = int(value)
            if value not in labels:
                labels[value] = next_label
                next_label += 1
            encoded.append(labels[value])
        rows.append(tuple(encoded))
    return tuple(rows)


def _tile_self_block_match_ratio(inp: np.ndarray, out: np.ndarray) -> float:
    ih, iw = inp.shape
    oh, ow = out.shape
    if oh != ih * ih or ow != iw * iw:
        return 0.0

    matches = 0
    total = ih * iw
    zero_block = np.zeros_like(inp)
    for r in range(ih):
        for c in range(iw):
            block = out[r * ih : (r + 1) * ih, c * iw : (c + 1) * iw]
            expected = inp if inp[r, c] != 0 else zero_block
            if np.array_equal(block, expected):
                matches += 1
    return matches / float(total)


def _shape_delta(example: ARCExample) -> float:
    ih, iw = example.input.shape
    oh, ow = example.output.shape
    if ih == 0 or iw == 0:
        return 0.0
    ratio = (oh * ow) / float(ih * iw)
    return min(1.0, abs(ratio - 1.0))


def _motion_signal(example: ARCExample) -> float:
    inp = example.input
    out = example.output
    if inp.shape != out.shape:
        return 0.3
    if np.array_equal(inp, out):
        return 0.0
    if _pattern_signature(inp) == _pattern_signature(out):
        return 0.0
    if np.array_equal(np.fliplr(inp), out) or np.array_equal(np.flipud(inp), out):
        return 1.0
    if inp.shape[0] == inp.shape[1] and np.array_equal(inp.T, out):
        return 1.0
    return 0.7


def _color_signal(example: ARCExample) -> float:
    inp = example.input
    out = example.output
    if inp.shape != out.shape:
        unique_in = sorted(int(v) for v in np.unique(inp))
        unique_out = sorted(int(v) for v in np.unique(out))
        return 1.0 if unique_in != unique_out else 0.2
    same_positions = inp == out
    if same_positions.all():
        return 0.0
    changed = float((~same_positions).sum()) / float(inp.size)
    return min(1.0, changed * 2.0)


def _scope_signal(example: ARCExample) -> float:
    tile_self_ratio = _tile_self_block_match_ratio(example.input, example.output)
    if tile_self_ratio >= 0.95:
        return 1.0

    _, components = connected_components(example.input)
    non_zero = int((example.input != 0).sum())
    if non_zero == 0:
        return 0.0
    unique_colors = len(set(int(v) for v in np.unique(example.input)) - {0})
    if len(components) == 1:
        return 0.2
    if unique_colors >= 2 and len(components) >= unique_colors:
        return 0.8
    return 0.5


def _topology_signal(example: ARCExample) -> float:
    inp = example.input
    out = example.output
    if inp.shape != out.shape:
        ih, iw = inp.shape
        oh, ow = out.shape
        if oh == ih * ih and ow == iw * iw:
            return 1.0
        return 0.7
    in_non_zero = int((inp != 0).sum())
    out_non_zero = int((out != 0).sum())
    if out_non_zero > in_non_zero:
        return min(1.0, (out_non_zero - in_non_zero) / max(float(inp.size), 1.0) * 4.0)
    return 0.2


def _composition_signal(example: ARCExample) -> float:
    color = _color_signal(example)
    motion = _motion_signal(example)
    shape = _shape_delta(example)
    active_axes = sum(1 for value in (color, motion, shape) if value >= 0.45)
    return min(1.0, max(0, active_axes - 1) / 2.0)


def task_topology(task: ARCTask) -> np.ndarray:
    train = task.train
    return np.asarray(
        [
            _mean(_shape_delta(example) for example in train),
            _mean(_motion_signal(example) for example in train),
            _mean(_color_signal(example) for example in train),
            _mean(_scope_signal(example) for example in train),
            _mean(_topology_signal(example) for example in train),
            _mean(_composition_signal(example) for example in train),
        ],
        dtype=np.float64,
    )


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom < 1e-9:
        return 0.0
    return float(np.dot(a, b) / denom)


def rank_families_by_lattice(task: ARCTask) -> list[str]:
    task_vec = task_topology(task)
    scored = [
        (family, _cosine_similarity(task_vec, topology.as_array())) for family, topology in FAMILY_TOPOLOGIES.items()
    ]
    scored.sort(
        key=lambda item: (
            -item[1],
            FLAT_FAMILY_ORDER.index(item[0]) if item[0] in FLAT_FAMILY_ORDER else 999,
        )
    )
    return [family for family, _ in scored]


def _lattice_centroid() -> np.ndarray:
    return np.mean([topology.as_array() for topology in FAMILY_TOPOLOGIES.values()], axis=0)


def rank_families_by_charge_path(task: ARCTask) -> list[str]:
    task_vec = task_topology(task)
    centroid = _lattice_centroid()
    direction = task_vec - centroid
    direction_norm = np.linalg.norm(direction)
    if direction_norm < 1e-9:
        return list(FLAT_FAMILY_ORDER)

    scored: list[tuple[str, float]] = []
    for family, topology in FAMILY_TOPOLOGIES.items():
        offset = topology.as_array() - centroid
        projection = float(np.dot(offset, direction)) / direction_norm
        ternary_alignment = sum(topology.ternary[i] * direction[i] for i in range(len(AXES)))
        score = projection + 0.12 * topology.charge + 0.06 * ternary_alignment
        scored.append((family, score))

    scored.sort(
        key=lambda item: (
            -item[1],
            FLAT_FAMILY_ORDER.index(item[0]) if item[0] in FLAT_FAMILY_ORDER else 999,
        )
    )
    return [family for family, _ in scored]
