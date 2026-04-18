from __future__ import annotations

from dataclasses import dataclass, field

ALLOWED_PRIMITIVES = frozenset(
    {
        "color_remap",
        "equal_mask",
        "boundary_mask",
        "neighbor_count",
        "shift",
        "shift_color",
        "copy_color",
        "flip_x",
        "flip_y",
        "transpose",
        "tile",
        "tile_self",
        "tile_self_complement",
        "tile_mirror_2x2",
        "tile_rotate_2x2",
        "connect_aligned_pairs",
        "corner_legend_row_swap",
        "panel_consensus_tile",
        "upscale",
        "upscale_color_count",
        "gravity_up",
        "gravity_down",
        "gravity_left",
        "gravity_right",
        "sym_complete_x",
        "sym_complete_y",
        "crop",
        "paste",
        "select",
        "reduce_sum",
        "identity",
        # New object-level primitives
        "fill_enclosed",
        "paint_border",
        "h_concat_flip",
        "v_concat_flip",
        "extract_panel",
        "extract_half_longer",
        "rotate_180_pivot",
        "panel_sym_complete_x",
        "panel_sym_complete_y",
        # Same-shape in-place transforms
        "sym_complete_180_frames",
        "template_stamp",
        "tile_marker_propagate",
        "diagonal_project",
        "diagonal_cross_connect",
        "marker_erase_outside",
        "panel_dihedral_complete",
        # Bespoke task-specific primitives
        "anchor_fill_brute",
        "largest_zero_rect_fill",
        "dihedral_template_match",
        "panel_complement_fill",
        "panel_boolean_op",
        "grid_select_min_colors",
        "cc_unique_size_crop",
        "cc_max_colors_crop",
        "cc_min_minority_crop",
        "downscale_max",
        "tile_by_color_count",
        "tile_self_simple",
        "odd_one_out_crop",
        "downscale_majority",
        "border_repeat_edge",
        "tile_mirror_2x2_v2",
        "tile_rotate_ccw_2x2",
        "invert_tile_2x2",
        "downscale_all_nonzero",
        "color_bbox_crop",
        "quadrant_extract",
        "max_solid_rect_crop",
        "checkerboard_fill",
        "majority_color_indicator",
        "rotate_arm_cw",
        "bg_cluster_fill",
        "diagonal_fill",
        "local_rule_3x3",
    }
)


@dataclass(frozen=True)
class IRStep:
    op: str
    args: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.op not in ALLOWED_PRIMITIVES:
            raise ValueError(f"Primitive '{self.op}' is not allowed in NeuroGolf IR")


@dataclass(frozen=True)
class StraightLineProgram:
    """Restricted IR for compile-time-selected ARC transforms."""

    name: str
    steps: tuple[IRStep, ...]

    def validate(self) -> None:
        for step in self.steps:
            if step.op not in ALLOWED_PRIMITIVES:
                raise ValueError(f"Unsupported op in straight-line program: {step.op}")


def make_color_remap_program(mapping: dict[int, int]) -> StraightLineProgram:
    return StraightLineProgram(
        name="color_remap",
        steps=(IRStep(op="color_remap", args={"mapping": dict(mapping)}),),
    )


def make_identity_program() -> StraightLineProgram:
    return StraightLineProgram(
        name="identity",
        steps=(IRStep(op="identity", args={}),),
    )


def make_shift_program(shift_x: int, shift_y: int) -> StraightLineProgram:
    return StraightLineProgram(
        name="shift",
        steps=(IRStep(op="shift", args={"shift_x": shift_x, "shift_y": shift_y}),),
    )


def make_shift_color_remap_program(shift_x: int, shift_y: int, mapping: dict[int, int]) -> StraightLineProgram:
    return StraightLineProgram(
        name="shift_then_color_remap",
        steps=(
            IRStep(op="shift", args={"shift_x": shift_x, "shift_y": shift_y}),
            IRStep(op="color_remap", args={"mapping": dict(mapping)}),
        ),
    )


def make_shift_color_program(color: int, shift_x: int, shift_y: int) -> StraightLineProgram:
    return StraightLineProgram(
        name="shift_color",
        steps=(
            IRStep(
                op="shift_color",
                args={"color": color, "shift_x": shift_x, "shift_y": shift_y},
            ),
        ),
    )


def make_copy_color_program(color: int, shift_x: int, shift_y: int) -> StraightLineProgram:
    return StraightLineProgram(
        name="copy_color",
        steps=(
            IRStep(
                op="copy_color",
                args={"color": color, "shift_x": shift_x, "shift_y": shift_y},
            ),
        ),
    )


def make_multi_shift_color_program(color_shifts: list[tuple[int, int, int]]) -> StraightLineProgram:
    return StraightLineProgram(
        name="multi_shift_color",
        steps=tuple(
            IRStep(
                op="shift_color",
                args={"color": color, "shift_x": shift_x, "shift_y": shift_y},
            )
            for color, shift_x, shift_y in color_shifts
        ),
    )


def make_flip_x_program() -> StraightLineProgram:
    return StraightLineProgram(
        name="flip_x",
        steps=(IRStep(op="flip_x", args={}),),
    )


def make_flip_y_program() -> StraightLineProgram:
    return StraightLineProgram(
        name="flip_y",
        steps=(IRStep(op="flip_y", args={}),),
    )


def make_transpose_program() -> StraightLineProgram:
    return StraightLineProgram(
        name="transpose",
        steps=(IRStep(op="transpose", args={}),),
    )


def make_tile_program(scale_y: int, scale_x: int) -> StraightLineProgram:
    return StraightLineProgram(
        name="tile",
        steps=(IRStep(op="tile", args={"scale_y": scale_y, "scale_x": scale_x}),),
    )


def make_tile_self_program() -> StraightLineProgram:
    """Fractal tile: each non-zero cell stamps a copy of the input."""
    return StraightLineProgram(
        name="tile_self",
        steps=(IRStep(op="tile_self", args={}),),
    )


def make_tile_self_complement_program() -> StraightLineProgram:
    """Complement fractal tile: each non-zero cell stamps the boolean complement of the input.

    For single-color binary inputs: complement = np.where(input == 0, color, 0).
    Zero cells produce zero blocks.
    """
    return StraightLineProgram(
        name="tile_self_complement",
        steps=(IRStep(op="tile_self_complement", args={}),),
    )


def make_upscale_program(scale_k: int) -> StraightLineProgram:
    """Each pixel → k×k uniform block (np.repeat in both axes)."""
    return StraightLineProgram(
        name="upscale",
        steps=(IRStep(op="upscale", args={"scale_k": scale_k}),),
    )


def make_upscale_color_count_program() -> StraightLineProgram:
    """Each pixel → k×k block where k = number of distinct non-zero colors in the grid."""
    return StraightLineProgram(
        name="upscale_color_count",
        steps=(IRStep(op="upscale_color_count", args={}),),
    )


def make_upscale_color_remap_program(scale_k: int, mapping: dict[int, int]) -> StraightLineProgram:
    """Upscale by scale_k (exact pixel repeat) then apply a global color remap."""
    return StraightLineProgram(
        name="upscale_then_color_remap",
        steps=(
            IRStep(op="upscale", args={"scale_k": scale_k}),
            IRStep(op="color_remap", args={"mapping": dict(mapping)}),
        ),
    )


def make_gravity_program(direction: str) -> StraightLineProgram:
    """Pull all non-zero pixels toward one edge, preserving relative order."""
    op = f"gravity_{direction}"
    if op not in ("gravity_up", "gravity_down", "gravity_left", "gravity_right"):
        raise ValueError(f"Unsupported gravity direction '{direction}'")
    return StraightLineProgram(
        name=op,
        steps=(IRStep(op=op, args={}),),
    )


def make_sym_complete_program(axis: str) -> StraightLineProgram:
    """Complete symmetry: output = where(input != 0, input, flip(input)).

    axis='x' uses fliplr (left-right), axis='y' uses flipud (up-down).
    """
    op = f"sym_complete_{axis}"
    if op not in ("sym_complete_x", "sym_complete_y"):
        raise ValueError(f"Unsupported sym_complete axis '{axis}'")
    return StraightLineProgram(
        name=op,
        steps=(IRStep(op=op, args={}),),
    )


def make_crop_then_orient_program(orientation: str) -> StraightLineProgram:
    """Crop to bounding box then apply an orientation transform."""
    _ORIENTATION_STEPS: dict[str, tuple[IRStep, ...]] = {
        "flip_x": (IRStep(op="flip_x", args={}),),
        "flip_y": (IRStep(op="flip_y", args={}),),
        "transpose": (IRStep(op="transpose", args={}),),
        "rotate_cw": (IRStep(op="transpose", args={}), IRStep(op="flip_x", args={})),
        "rotate_ccw": (IRStep(op="transpose", args={}), IRStep(op="flip_y", args={})),
        "rotate_180": (IRStep(op="flip_x", args={}), IRStep(op="flip_y", args={})),
    }
    if orientation not in _ORIENTATION_STEPS:
        raise ValueError(f"Unsupported orientation '{orientation}'")
    return StraightLineProgram(
        name=f"crop_then_{orientation}",
        steps=(IRStep(op="crop", args={}),) + _ORIENTATION_STEPS[orientation],
    )


def make_crop_bbox_program() -> StraightLineProgram:
    """Crop grid to bounding box of non-zero pixels."""
    return StraightLineProgram(
        name="crop_bbox",
        steps=(IRStep(op="crop", args={}),),
    )


def make_tile_mirror_2x2_program() -> StraightLineProgram:
    """2x2 tiling: TL=id, TR=fliplr, BL=flipud, BR=rot180."""
    return StraightLineProgram(
        name="tile_mirror_2x2",
        steps=(IRStep(op="tile_mirror_2x2", args={}),),
    )


def make_tile_rotate_2x2_program() -> StraightLineProgram:
    """2x2 tiling: TL=id, TR=rot90cw, BL=rot90ccw, BR=rot180 (square inputs only)."""
    return StraightLineProgram(
        name="tile_rotate_2x2",
        steps=(IRStep(op="tile_rotate_2x2", args={}),),
    )


def make_connect_aligned_pairs_program() -> StraightLineProgram:
    """Connect aligned same-color endpoint pairs with axis-aligned segments."""
    return StraightLineProgram(
        name="connect_aligned_pairs",
        steps=(IRStep(op="connect_aligned_pairs", args={}),),
    )


def make_corner_legend_row_swap_program() -> StraightLineProgram:
    """Use the top-left 2x2 block as two row-wise color-swap pairs."""
    return StraightLineProgram(
        name="corner_legend_row_swap",
        steps=(IRStep(op="corner_legend_row_swap", args={}),),
    )


def make_panel_consensus_tile_program() -> StraightLineProgram:
    """Regularize repeated panel layouts by stamping a majority-vote canonical tile."""
    return StraightLineProgram(
        name="panel_consensus_tile",
        steps=(IRStep(op="panel_consensus_tile", args={}),),
    )


def make_rotate_cw_program() -> StraightLineProgram:
    """90° clockwise: transpose then flip_x."""
    return StraightLineProgram(
        name="rotate_cw",
        steps=(IRStep(op="transpose", args={}), IRStep(op="flip_x", args={})),
    )


def make_rotate_ccw_program() -> StraightLineProgram:
    """90° counter-clockwise: transpose then flip_y."""
    return StraightLineProgram(
        name="rotate_ccw",
        steps=(IRStep(op="transpose", args={}), IRStep(op="flip_y", args={})),
    )


def make_rotate_180_program() -> StraightLineProgram:
    """180° rotation: flip_x then flip_y."""
    return StraightLineProgram(
        name="rotate_180",
        steps=(IRStep(op="flip_x", args={}), IRStep(op="flip_y", args={})),
    )


def make_rotation_color_remap_program(rotation: str, mapping: dict[int, int]) -> StraightLineProgram:
    """Rotation followed by color remap."""
    _ROTATION_STEPS = {
        "rotate_cw": (IRStep(op="transpose", args={}), IRStep(op="flip_x", args={})),
        "rotate_ccw": (IRStep(op="transpose", args={}), IRStep(op="flip_y", args={})),
        "rotate_180": (IRStep(op="flip_x", args={}), IRStep(op="flip_y", args={})),
    }
    if rotation not in _ROTATION_STEPS:
        raise ValueError(f"Unsupported rotation '{rotation}'")
    return StraightLineProgram(
        name=f"{rotation}_then_color_remap",
        steps=_ROTATION_STEPS[rotation] + (IRStep(op="color_remap", args={"mapping": dict(mapping)}),),
    )


def make_orientation_color_remap_program(orientation: str, mapping: dict[int, int]) -> StraightLineProgram:
    if orientation not in {"flip_x", "flip_y", "transpose"}:
        raise ValueError(f"Unsupported orientation primitive '{orientation}'")
    return StraightLineProgram(
        name=f"{orientation}_then_color_remap",
        steps=(
            IRStep(op=orientation, args={}),
            IRStep(op="color_remap", args={"mapping": dict(mapping)}),
        ),
    )


def make_fill_enclosed_program(fill_color: int) -> StraightLineProgram:
    """Fill background (0) cells that are enclosed by non-zero pixels."""
    return StraightLineProgram(
        name="fill_enclosed",
        steps=(IRStep(op="fill_enclosed", args={"fill_color": fill_color}),),
    )


def make_paint_border_program(border_color: int) -> StraightLineProgram:
    """Paint the 1px outer border of the grid with border_color."""
    return StraightLineProgram(
        name="paint_border",
        steps=(IRStep(op="paint_border", args={"border_color": border_color}),),
    )


def make_h_concat_flip_program() -> StraightLineProgram:
    """Horizontal mirror concatenation: output = [grid | fliplr(grid)]."""
    return StraightLineProgram(
        name="h_concat_flip",
        steps=(IRStep(op="h_concat_flip", args={}),),
    )


def make_v_concat_flip_program() -> StraightLineProgram:
    """Vertical mirror concatenation: output = [grid / flipud(grid)]."""
    return StraightLineProgram(
        name="v_concat_flip",
        steps=(IRStep(op="v_concat_flip", args={}),),
    )


def make_extract_panel_program(r_panels: int, c_panels: int, r_idx: int, c_idx: int) -> StraightLineProgram:
    """Extract one panel from a regular panel-grid layout."""
    return StraightLineProgram(
        name="extract_panel",
        steps=(
            IRStep(
                op="extract_panel",
                args={
                    "r_panels": r_panels,
                    "c_panels": c_panels,
                    "r_idx": r_idx,
                    "c_idx": c_idx,
                },
            ),
        ),
    )


def make_extract_half_longer_program() -> StraightLineProgram:
    """Extract the first half of the grid along its longer dimension."""
    return StraightLineProgram(
        name="extract_half_longer",
        steps=(IRStep(op="extract_half_longer", args={}),),
    )


def make_sym_complete_180_frames_program() -> StraightLineProgram:
    """Complete 180° point symmetry inside 8-bordered frames."""
    return StraightLineProgram(
        name="sym_complete_180_frames",
        steps=(IRStep(op="sym_complete_180_frames", args={}),),
    )


def make_template_stamp_program() -> StraightLineProgram:
    """Find a template from 4-cells, scan for partial matches, stamp missing 4s."""
    return StraightLineProgram(
        name="template_stamp",
        steps=(IRStep(op="template_stamp", args={}),),
    )


def make_diagonal_project_program() -> StraightLineProgram:
    """Continue a diagonal sequence of same-color cells with a new color."""
    return StraightLineProgram(
        name="diagonal_project",
        steps=(IRStep(op="diagonal_project", args={}),),
    )


def make_diagonal_cross_connect_program() -> StraightLineProgram:
    """Connect cross-shape centers on 45° diagonals with a connector color."""
    return StraightLineProgram(
        name="diagonal_cross_connect",
        steps=(IRStep(op="diagonal_cross_connect", args={}),),
    )


def make_marker_erase_outside_program() -> StraightLineProgram:
    """Erase a marker color everywhere outside a top-left indicator region."""
    return StraightLineProgram(
        name="marker_erase_outside",
        steps=(IRStep(op="marker_erase_outside", args={}),),
    )


def make_panel_dihedral_complete_program() -> StraightLineProgram:
    """Complete missing panels in 2x2 panel groups using dihedral symmetry."""
    return StraightLineProgram(
        name="panel_dihedral_complete",
        steps=(IRStep(op="panel_dihedral_complete", args={}),),
    )


def make_tile_marker_propagate_program() -> StraightLineProgram:
    """Propagate marker cells along axis-aligned segments in a tiled grid layout."""
    return StraightLineProgram(
        name="tile_marker_propagate",
        steps=(IRStep(op="tile_marker_propagate", args={}),),
    )


def make_anchor_fill_brute_program() -> StraightLineProgram:
    """Bespoke anchor-fill solver for ARC task 79369cc6.

    Finds the 4-cluster (orig_4) and multi-6 anchor cluster adjacent to it,
    then brute-force scans all rotation/flip placements of the combined shape
    to fill target 4-cells. Uses a bounding-box missing-cell constraint to
    suppress false positives.
    """
    return StraightLineProgram(
        name="anchor_fill_brute",
        steps=(IRStep(op="anchor_fill_brute", args={}),),
    )


def make_largest_zero_rect_fill_program() -> StraightLineProgram:
    """Find largest all-zero rectangle, shrink by 1, fill interior with 8."""
    return StraightLineProgram(
        name="largest_zero_rect_fill",
        steps=(IRStep(op="largest_zero_rect_fill", args={}),),
    )


def make_dihedral_template_match_program(target_color: int) -> StraightLineProgram:
    """Find 8-template, replace matching shapes in target_color under dihedral symmetry."""
    return StraightLineProgram(
        name="dihedral_template_match",
        steps=(IRStep(op="dihedral_template_match", args={"target_color": target_color}),),
    )


def make_panel_complement_fill_program() -> StraightLineProgram:
    """Split at divider column, merge panels if right's non-zeros match left's zeros."""
    return StraightLineProgram(
        name="panel_complement_fill",
        steps=(IRStep(op="panel_complement_fill", args={}),),
    )


def make_panel_boolean_op_program(op: str, output_color: int) -> StraightLineProgram:
    """Split at divider, apply boolean op (AND/OR/XOR/NOR) on panels, output single color."""
    return StraightLineProgram(
        name="panel_boolean_op",
        steps=(IRStep(op="panel_boolean_op", args={"op": op, "output_color": output_color}),),
    )


def make_grid_select_min_colors_program() -> StraightLineProgram:
    """Extract grid cells and select the one with fewest distinct non-bg colors."""
    return StraightLineProgram(
        name="grid_select_min_colors",
        steps=(IRStep(op="grid_select_min_colors", args={}),),
    )


def make_cc_unique_size_crop_program() -> StraightLineProgram:
    """Find foreground CCs, select the one with unique pixel count, crop its bbox."""
    return StraightLineProgram(
        name="cc_unique_size_crop",
        steps=(IRStep(op="cc_unique_size_crop", args={}),),
    )


def make_cc_max_colors_crop_program() -> StraightLineProgram:
    """Find foreground CCs, select the one with most distinct colors, crop its bbox."""
    return StraightLineProgram(
        name="cc_max_colors_crop",
        steps=(IRStep(op="cc_max_colors_crop", args={}),),
    )


def make_cc_min_minority_crop_program() -> StraightLineProgram:
    """Find foreground CCs, select the one with fewest non-dominant-color pixels, crop its bbox."""
    return StraightLineProgram(
        name="cc_min_minority_crop",
        steps=(IRStep(op="cc_min_minority_crop", args={}),),
    )


def make_downscale_max_program(target_h: int, target_w: int) -> StraightLineProgram:
    """Downscale input to (target_h, target_w) taking max of each block."""
    return StraightLineProgram(
        name="downscale_max",
        steps=(IRStep(op="downscale_max", args={"target_h": target_h, "target_w": target_w}),),
    )


def make_tile_by_color_count_program() -> StraightLineProgram:
    """Tile input NxN where N = number of distinct non-bg colors."""
    return StraightLineProgram(
        name="tile_by_color_count",
        steps=(IRStep(op="tile_by_color_count", args={}),),
    )


def make_tile_self_simple_program() -> StraightLineProgram:
    """Tile input by (ih, iw) unconditionally."""
    return StraightLineProgram(
        name="tile_self_simple",
        steps=(IRStep(op="tile_self_simple", args={}),),
    )


def make_odd_one_out_crop_program() -> StraightLineProgram:
    """Find the shape that appears exactly once (all others appear in pairs), crop it."""
    return StraightLineProgram(
        name="odd_one_out_crop",
        steps=(IRStep(op="odd_one_out_crop", args={}),),
    )


def make_downscale_majority_program(target_h: int, target_w: int) -> StraightLineProgram:
    """Downscale input to (target_h, target_w) taking majority non-bg color of each block."""
    return StraightLineProgram(
        name="downscale_majority",
        steps=(IRStep(op="downscale_majority", args={"target_h": target_h, "target_w": target_w}),),
    )


def make_border_repeat_edge_program(pad_n: int) -> StraightLineProgram:
    """Grow grid by repeating edge pixels outward pad_n times."""
    return StraightLineProgram(
        name="border_repeat_edge",
        steps=(IRStep(op="border_repeat_edge", args={"pad_n": pad_n}),),
    )


def make_tile_mirror_2x2_v2_program() -> StraightLineProgram:
    """2x2 mirror: TL=inp, TR=flipud, BL=fliplr, BR=inp."""
    return StraightLineProgram(
        name="tile_mirror_2x2_v2",
        steps=(IRStep(op="tile_mirror_2x2_v2", args={}),),
    )


def make_tile_rotate_ccw_2x2_program() -> StraightLineProgram:
    """2x2 CCW rotation: TL=inp, TR=rot90, BL=rot180, BR=rot270."""
    return StraightLineProgram(
        name="tile_rotate_ccw_2x2",
        steps=(IRStep(op="tile_rotate_ccw_2x2", args={}),),
    )


def make_invert_tile_2x2_program() -> StraightLineProgram:
    """Swap bg/fg color (single non-bg color assumed), then tile 2x2."""
    return StraightLineProgram(
        name="invert_tile_2x2",
        steps=(IRStep(op="invert_tile_2x2", args={}),),
    )


def make_downscale_all_nonzero_program(target_h: int, target_w: int) -> StraightLineProgram:
    """Downscale: output = 0 if block has any zero, else block's color."""
    return StraightLineProgram(
        name="downscale_all_nonzero",
        steps=(IRStep(op="downscale_all_nonzero", args={"target_h": target_h, "target_w": target_w}),),
    )


def make_color_bbox_crop_program(color: int) -> StraightLineProgram:
    """Crop input to bounding box of all pixels with the given color."""
    return StraightLineProgram(
        name="color_bbox_crop",
        steps=(IRStep(op="color_bbox_crop", args={"color": color}),),
    )


def make_quadrant_extract_program(quadrant: str) -> StraightLineProgram:
    """Extract one quadrant: TL, TR, BL, BR."""
    return StraightLineProgram(
        name="quadrant_extract",
        steps=(IRStep(op="quadrant_extract", args={"quadrant": quadrant}),),
    )


def make_max_solid_rect_crop_program(color: int) -> StraightLineProgram:
    """Crop the largest solid rectangle of a specific color from input."""
    return StraightLineProgram(
        name="max_solid_rect_crop",
        steps=(IRStep(op="max_solid_rect_crop", args={"color": color}),),
    )


def make_checkerboard_fill_program() -> StraightLineProgram:
    """Fill grid with checkerboard: 1 where (r+c)%2==0 on even rows, all 1s on odd."""
    return StraightLineProgram(
        name="checkerboard_fill",
        steps=(IRStep(op="checkerboard_fill", args={}),),
    )


def make_majority_color_indicator_program() -> StraightLineProgram:
    """Place most common non-divider color at bottom-center below a 5-divider."""
    return StraightLineProgram(
        name="majority_color_indicator",
        steps=(IRStep(op="majority_color_indicator", args={}),),
    )


def make_rotate_arm_cw_program() -> StraightLineProgram:
    """Rotate color-2 arm CW around color-5 pivot, recolor old arm to 3."""
    return StraightLineProgram(
        name="rotate_arm_cw",
        steps=(IRStep(op="rotate_arm_cw", args={}),),
    )


def make_bg_cluster_fill_program(fg_color: int, fill_color: int) -> StraightLineProgram:
    """Fill bg-color CCs of size >= 2 with fill_color; isolated bg cells stay."""
    return StraightLineProgram(
        name="bg_cluster_fill",
        steps=(IRStep(op="bg_cluster_fill", args={"fg_color": fg_color, "fill_color": fill_color}),),
    )


def make_diagonal_fill_program(fill_color: int) -> StraightLineProgram:
    """Fill the best-fit diagonal (main or anti) of a bordered grid with fill_color."""
    return StraightLineProgram(
        name="diagonal_fill",
        steps=(IRStep(op="diagonal_fill", args={"fill_color": fill_color}),),
    )


def make_local_rule_3x3_program(rules: list) -> StraightLineProgram:
    """Cellular automaton with learned 3x3 neighborhood -> output mapping.

    rules: list of [[nbr0..nbr8], output_value] pairs (only changing cells).
    Border cells padded with -1 during extraction.
    """
    return StraightLineProgram(
        name="local_rule_3x3",
        steps=(IRStep(op="local_rule_3x3", args={"rules": rules}),),
    )
