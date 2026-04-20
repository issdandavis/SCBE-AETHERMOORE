from __future__ import annotations

from typing import Literal

RealmName = Literal["objectness", "numbers", "geometry", "agent"]
StratumName = Literal["direct", "relational", "structural", "compositional"]

REALM_NAMES: tuple[RealmName, ...] = ("objectness", "numbers", "geometry", "agent")
STRATUM_NAMES: tuple[StratumName, ...] = ("direct", "relational", "structural", "compositional")
ROTATIONS: tuple[int, ...] = (0, 45, 90, 135)

REALM_PRIMITIVES: dict[RealmName, tuple[str, ...]] = {
    "objectness": (
        "connected_components",
        "select_largest_cc",
        "select_minority_color",
        "crop_bbox",
        "extract_panel",
    ),
    "numbers": (
        "count_colors",
        "component_count",
        "select_by_rank",
        "single_cell_output",
        "upscale_color_count",
    ),
    "geometry": (
        "flip_x",
        "flip_y",
        "rotate_cw",
        "rotate_ccw",
        "transpose",
        "sym_complete_x",
        "sym_complete_y",
    ),
    "agent": (
        "shift",
        "gravity_up",
        "gravity_down",
        "gravity_left",
        "gravity_right",
        "connect_aligned_pairs",
        "vertical_motif_extend",
    ),
}
