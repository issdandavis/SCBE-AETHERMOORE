from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .arc_io import ARCExample, ARCTask
from .components import connected_components
from .family_corridor import ColorRemapCorridor, UpscaleCorridor, intersect_color_remap_corridors
from .family_lattice import FLAT_FAMILY_ORDER, rank_families_by_lattice, task_topology
from .structural_encode import encode_grid_structurally
from .ir import (
    IRStep,
    StraightLineProgram,
    make_color_remap_program,
    make_copy_color_program,
    make_connect_aligned_pairs_program,
    make_corner_legend_row_swap_program,
    make_crop_bbox_program,
    make_flip_x_program,
    make_flip_y_program,
    make_identity_program,
    make_multi_shift_color_program,
    make_orientation_color_remap_program,
    make_rotate_180_program,
    make_rotate_ccw_program,
    make_rotate_cw_program,
    make_rotation_color_remap_program,
    make_shift_color_program,
    make_shift_color_remap_program,
    make_shift_program,
    make_tile_mirror_2x2_program,
    make_tile_program,
    make_tile_rotate_2x2_program,
    make_crop_then_orient_program,
    make_gravity_program,
    make_panel_consensus_tile_program,
    make_sym_complete_program,
    make_tile_self_complement_program,
    make_tile_self_program,
    make_transpose_program,
    make_upscale_color_count_program,
    make_upscale_color_remap_program,
    make_upscale_program,
    make_fill_enclosed_program,
    make_paint_border_program,
    make_h_concat_flip_program,
    make_v_concat_flip_program,
    make_extract_panel_program,
    make_extract_half_longer_program,
    make_anchor_fill_brute_program,
    make_largest_zero_rect_fill_program,
    make_dihedral_template_match_program,
    make_panel_complement_fill_program,
    make_panel_boolean_op_program,
    make_sym_complete_180_frames_program,
    make_template_stamp_program,
    make_tile_marker_propagate_program,
    make_diagonal_project_program,
    make_diagonal_cross_connect_program,
    make_marker_erase_outside_program,
    make_panel_dihedral_complete_program,
    make_grid_select_min_colors_program,
    make_cc_unique_size_crop_program,
    make_cc_max_colors_crop_program,
    make_cc_min_minority_crop_program,
    make_downscale_max_program,
    make_tile_by_color_count_program,
    make_tile_self_simple_program,
    make_odd_one_out_crop_program,
    make_downscale_majority_program,
    make_border_repeat_edge_program,
    make_tile_mirror_2x2_v2_program,
    make_tile_rotate_ccw_2x2_program,
    make_invert_tile_2x2_program,
    make_downscale_all_nonzero_program,
    make_color_bbox_crop_program,
    make_quadrant_extract_program,
    make_max_solid_rect_crop_program,
    make_checkerboard_fill_program,
    make_majority_color_indicator_program,
    make_rotate_arm_cw_program,
    make_bg_cluster_fill_program,
    make_diagonal_fill_program,
    make_local_rule_3x3_program,
)


@dataclass(frozen=True)
class SynthesizedSolution:
    program: StraightLineProgram
    family: str


def _apply_color_remap(grid: np.ndarray, mapping: dict[int, int]) -> np.ndarray:
    out = np.asarray(grid, dtype=np.int64).copy()
    for src, dst in mapping.items():
        out[grid == src] = dst
    return out


def apply_shift(
    grid: np.ndarray,
    shift_x: int,
    shift_y: int,
    *,
    fill_value: int = 0,
) -> np.ndarray:
    """Shift a grid with fill.

    Positive `shift_x` moves content right. Positive `shift_y` moves content down.
    """

    h, w = grid.shape
    out = np.full_like(grid, fill_value)

    src_x0 = max(0, -shift_x)
    src_x1 = min(w, w - shift_x) if shift_x >= 0 else w
    dst_x0 = max(0, shift_x)
    dst_x1 = dst_x0 + max(0, src_x1 - src_x0)

    src_y0 = max(0, -shift_y)
    src_y1 = min(h, h - shift_y) if shift_y >= 0 else h
    dst_y0 = max(0, shift_y)
    dst_y1 = dst_y0 + max(0, src_y1 - src_y0)

    if src_x1 > src_x0 and src_y1 > src_y0:
        out[dst_y0:dst_y1, dst_x0:dst_x1] = grid[src_y0:src_y1, src_x0:src_x1]
    return out


def _execute_sym_complete_180_frames(grid_np: np.ndarray) -> np.ndarray:
    """Complete 180° point symmetry inside 8-bordered frames.

    For each connected component of 8-cells:
      1. Flood-fill from interior non-zero/non-8 cells to find the interior void.
      2. Compute bounding box of the interior.
      3. For each fill-color cell, compute its 180° rotated position and write it.
    """
    rows, cols = grid_np.shape
    out = grid_np.copy()
    visited_8 = np.zeros((rows, cols), dtype=bool)

    # Find connected components of 8-cells via BFS
    eight_mask = grid_np == 8
    frame_components: list[set[tuple[int, int]]] = []
    for r in range(rows):
        for c in range(cols):
            if eight_mask[r, c] and not visited_8[r, c]:
                comp: set[tuple[int, int]] = set()
                queue = [(r, c)]
                visited_8[r, c] = True
                while queue:
                    cr, cc = queue.pop()
                    comp.add((cr, cc))
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols and eight_mask[nr, nc] and not visited_8[nr, nc]:
                            visited_8[nr, nc] = True
                            queue.append((nr, nc))
                if len(comp) >= 4:
                    frame_components.append(comp)

    for frame in frame_components:
        # Find interior by flood-filling from non-8 cells adjacent to frame
        interior: set[tuple[int, int]] = set()
        # Seed: non-8 cells that are 4-adjacent to a frame cell and inside the frame bbox
        fr = [r for r, _ in frame]
        fc = [c for _, c in frame]
        r_min, r_max = min(fr), max(fr)
        c_min, c_max = min(fc), max(fc)

        seeds: list[tuple[int, int]] = []
        for r, c in frame:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if (
                    r_min <= nr <= r_max
                    and c_min <= nc <= c_max
                    and (nr, nc) not in frame
                    and grid_np[nr, nc] != 8
                ):
                    if (nr, nc) not in interior:
                        seeds.append((nr, nc))
                        interior.add((nr, nc))

        # BFS flood fill interior (stop at 8-cells and frame boundary)
        while seeds:
            cr, cc = seeds.pop()
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = cr + dr, cc + dc
                if (
                    r_min <= nr <= r_max
                    and c_min <= nc <= c_max
                    and (nr, nc) not in frame
                    and (nr, nc) not in interior
                    and grid_np[nr, nc] != 8
                ):
                    interior.add((nr, nc))
                    seeds.append((nr, nc))

        if not interior:
            continue

        # Bounding box of interior
        ir = [r for r, _ in interior]
        ic = [c for _, c in interior]
        ir_min, ir_max = min(ir), max(ir)
        ic_min, ic_max = min(ic), max(ic)

        center_r = (ir_min + ir_max) / 2.0
        center_c = (ic_min + ic_max) / 2.0

        # Find the fill color (non-zero, non-8 cells in interior)
        fill_color = 0
        for r, c in interior:
            v = grid_np[r, c]
            if v != 0 and v != 8:
                fill_color = int(v)
                break

        if fill_color == 0:
            continue

        # Apply 180° rotation to every fill-color cell
        fill_cells = [(r, c) for r, c in interior if grid_np[r, c] == fill_color]
        for r, c in fill_cells:
            rr = round(2 * center_r - r)
            rc = round(2 * center_c - c)
            if (rr, rc) in interior and out[rr, rc] == 0:
                out[rr, rc] = fill_color

    return out


def _execute_template_stamp(grid_np: np.ndarray) -> np.ndarray:
    """Find a template defined by 4-cells, scan for partial matches, stamp missing 4s.

    1. Locate all cells == 4, compute bounding box → template patch.
    2. Slide template-sized window across grid.
    3. A window is a partial match if: template==4 → window==0, template!=4 → window==same.
    4. Write 4 into matched window positions where template has 4.
    """
    rows, cols = grid_np.shape
    fours = list(zip(*np.where(grid_np == 4)))
    if not fours:
        return grid_np.copy()

    r_min = min(r for r, _ in fours)
    r_max = max(r for r, _ in fours)
    c_min = min(c for _, c in fours)
    c_max = max(c for _, c in fours)

    template = grid_np[r_min : r_max + 1, c_min : c_max + 1].copy()
    th, tw = template.shape

    out = grid_np.copy()

    for sr in range(rows - th + 1):
        for sc in range(cols - tw + 1):
            if sr == r_min and sc == c_min:
                continue  # skip the template itself
            patch = grid_np[sr : sr + th, sc : sc + tw]
            match = True
            for dr in range(th):
                for dc in range(tw):
                    tv = template[dr, dc]
                    pv = patch[dr, dc]
                    if tv == 4:
                        if pv != 0:
                            match = False
                            break
                    else:
                        if pv != tv:
                            match = False
                            break
                if not match:
                    break
            if match:
                for dr in range(th):
                    for dc in range(tw):
                        if template[dr, dc] == 4:
                            out[sr + dr, sc + dc] = 4

    return out


def _execute_diagonal_project(grid_np: np.ndarray) -> np.ndarray:
    """Continue a diagonal sequence of same-color cells with a new color.

    Find cells of the seed color, sort by position, detect the uniform step (dr, dc),
    then extend from the last cell until hitting the grid boundary.
    New color = seed_color + 1 if only one non-zero color exists.
    """
    rows, cols = grid_np.shape
    out = grid_np.copy()

    vals, counts = np.unique(grid_np[grid_np != 0], return_counts=True)
    if len(vals) < 1:
        return out

    # Seed = the non-zero color (or the one with most cells if multiple)
    order = np.argsort(-counts)
    seed_color = int(vals[order[0]])
    # New color: use second color if it exists, otherwise seed + 1
    if len(vals) >= 2:
        new_color = int(vals[order[1]])
    else:
        new_color = seed_color + 1
        if new_color > 9:
            new_color = 2

    seed_positions = sorted(zip(*np.where(grid_np == seed_color)))
    if len(seed_positions) < 2:
        return out

    dr = seed_positions[1][0] - seed_positions[0][0]
    dc = seed_positions[1][1] - seed_positions[0][1]

    if dr == 0 and dc == 0:
        return out

    for i in range(2, len(seed_positions)):
        if (
            seed_positions[i][0] - seed_positions[i - 1][0] != dr
            or seed_positions[i][1] - seed_positions[i - 1][1] != dc
        ):
            return out

    r, c = seed_positions[-1][0] + dr, seed_positions[-1][1] + dc
    while 0 <= r < rows and 0 <= c < cols:
        out[r, c] = new_color
        r += dr
        c += dc

    return out


def _execute_diagonal_cross_connect(grid_np: np.ndarray) -> np.ndarray:
    """Connect cross-shape (+) centers that lie on 45° diagonals with a connector color.

    Cross = a cell with the shape color in all 4 cardinal neighbors.
    Connector color = the non-zero color that isn't the shape color, or a new color.
    """
    rows, cols = grid_np.shape
    out = grid_np.copy()

    # Find the dominant non-zero color (cross body color)
    vals, counts = np.unique(grid_np[grid_np != 0], return_counts=True)
    if len(vals) < 1:
        return out

    order = np.argsort(-counts)
    shape_color = int(vals[order[0]])

    # Find the connector color (second color, or detect from output context)
    connector_color = 2  # default
    for v in vals:
        if int(v) != shape_color:
            connector_color = int(v)
            break

    # Find cross centers
    shape_mask = grid_np == shape_color
    centers = []
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if (
                shape_mask[r, c]
                and shape_mask[r - 1, c]
                and shape_mask[r + 1, c]
                and shape_mask[r, c - 1]
                and shape_mask[r, c + 1]
            ):
                centers.append((r, c))

    # Connect pairs on 45° diagonals
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            r1, c1 = centers[i]
            r2, c2 = centers[j]
            dr = r2 - r1
            dc = c2 - c1
            if abs(dr) == abs(dc) and dr != 0:
                sr = 1 if dr > 0 else -1
                sc = 1 if dc > 0 else -1
                r, c = r1 + sr, c1 + sc
                while (r, c) != (r2, c2):
                    if grid_np[r, c] == 0:
                        out[r, c] = connector_color
                    r += sr
                    c += sc

    return out


def _execute_marker_erase_outside(grid_np: np.ndarray) -> np.ndarray:
    """Erase a marker color outside a top-left 3x3 indicator region.

    The marker color is the value at position (1, 1). All occurrences of that color
    outside the top-left 3x3 block are set to 0.
    """
    rows, cols = grid_np.shape
    if rows < 3 or cols < 3:
        return grid_np.copy()

    target = int(grid_np[1, 1])
    if target == 0:
        return grid_np.copy()

    out = grid_np.copy()
    for r in range(rows):
        for c in range(cols):
            if out[r, c] == target and not (r < 3 and c < 3):
                out[r, c] = 0
    return out


def _execute_panel_dihedral_complete(grid_np: np.ndarray) -> np.ndarray:
    """Complete missing panels in 2x2 panel groups using dihedral symmetry.

    Grid is divided into panels by uniform-color separator rows/columns (not necessarily 0).
    Panels come in 2x2 groups: TL=identity, TR=hflip, BL=vflip, BR=rot180.
    If one panel in a group is empty (all zero), fill it with the correct transform.
    """
    rows, cols = grid_np.shape
    out = grid_np.copy()

    # Find separator rows: rows where all cells are the same non-zero value
    # OR rows that are all-zero
    def find_sep_rows() -> list[int]:
        seps = []
        for r in range(rows):
            row = grid_np[r, :]
            if np.all(row == row[0]) and row[0] != 0:
                seps.append(r)
            elif np.all(row == 0):
                seps.append(r)
        return seps

    def find_sep_cols() -> list[int]:
        seps = []
        for c in range(cols):
            col = grid_np[:, c]
            if np.all(col == col[0]) and col[0] != 0:
                seps.append(c)
            elif np.all(col == 0):
                seps.append(c)
        return seps

    row_seps = find_sep_rows()
    col_seps = find_sep_cols()

    if not row_seps or not col_seps:
        return out

    # Build panel bounds (between separators)
    def bounds_from_seps(seps: list[int], limit: int) -> list[tuple[int, int]]:
        panels = []
        prev = 0
        for s in seps:
            if s > prev:
                panels.append((prev, s))
            prev = s + 1
        if prev < limit:
            panels.append((prev, limit))
        return panels

    row_panels = bounds_from_seps(row_seps, rows)
    col_panels = bounds_from_seps(col_seps, cols)

    n_pr = len(row_panels)
    n_pc = len(col_panels)

    # Extract panels: (r0, c0, height, width, data)
    panels: dict[tuple[int, int], tuple[int, int, int, int, np.ndarray]] = {}
    for ri, (r0, r1) in enumerate(row_panels):
        for ci, (c0, c1) in enumerate(col_panels):
            panels[(ri, ci)] = (r0, c0, r1 - r0, c1 - c0, grid_np[r0:r1, c0:c1].copy())

    def is_empty(panel: np.ndarray) -> bool:
        return np.all(panel == 0)

    def nonzero_colors(panel: np.ndarray) -> frozenset[int]:
        return frozenset(int(v) for v in np.unique(panel) if v != 0)

    # Scan ALL possible 2x2 blocks of adjacent panels.
    # Only act when exactly 3 are non-empty with the same non-zero colors
    # and all 4 panels share the same dimensions.
    filled: set[tuple[int, int]] = set()
    for ri in range(n_pr - 1):
        for ci in range(n_pc - 1):
            group = [(ri, ci), (ri, ci + 1), (ri + 1, ci), (ri + 1, ci + 1)]
            if not all(k in panels for k in group):
                continue

            # All 4 panels must have the same shape
            shapes = set((panels[k][2], panels[k][3]) for k in group)
            if len(shapes) > 1:
                continue

            non_empty = [k for k in group if not is_empty(panels[k][4])]
            empty = [k for k in group if is_empty(panels[k][4])]

            if len(non_empty) != 3 or len(empty) != 1:
                continue

            # All non-empty panels must share the same non-zero color set
            color_sets = [nonzero_colors(panels[k][4]) for k in non_empty]
            if not all(cs == color_sets[0] for cs in color_sets):
                continue

            target_key = empty[0]
            if target_key in filled:
                continue

            source_key = non_empty[0]
            source_panel = panels[source_key][4]
            sdr, sdc = source_key[0] - ri, source_key[1] - ci
            tdr, tdc = target_key[0] - ri, target_key[1] - ci

            fill = source_panel.copy()
            if sdc != tdc:
                fill = np.fliplr(fill)
            if sdr != tdr:
                fill = np.flipud(fill)

            tr0, tc0 = panels[target_key][0], panels[target_key][1]
            out[tr0 : tr0 + fill.shape[0], tc0 : tc0 + fill.shape[1]] = fill
            filled.add(target_key)

    return out


def _execute_tile_marker_propagate(grid_np: np.ndarray) -> np.ndarray:
    """Propagate marker cells along axis-aligned segments in a tiled grid layout.

    Structure: tiles of size 4x4 (1-cell border + 2x2 interior) with 1-cell separator (0).
    Tiles start at (1, 1) with stride 5. Most common interior = base tile.
    Markers are interior cells that differ from the base.
    For each marker type (color, intra_row, intra_col), draw axis-aligned segments
    between all pairs sharing the same tile-row or tile-column.
    """
    rows, cols = grid_np.shape
    # Detect tile grid dimensions
    n_tr = (rows - 1) // 5
    n_tc = (cols - 1) // 5

    if n_tr < 2 or n_tc < 2:
        return grid_np.copy()

    # Extract all tile interiors (2x2)
    interiors: dict[tuple[int, int], np.ndarray] = {}
    for tr in range(n_tr):
        for tc in range(n_tc):
            top = 1 + tr * 5
            left = 1 + tc * 5
            if top + 3 <= rows and left + 3 <= cols:
                interiors[(tr, tc)] = grid_np[top + 1 : top + 3, left + 1 : left + 3].copy()

    if not interiors:
        return grid_np.copy()

    # Find base tile (most common 2x2 interior pattern)
    from collections import Counter

    pattern_counts: Counter[bytes] = Counter()
    pattern_map: dict[bytes, np.ndarray] = {}
    for v in interiors.values():
        b = v.tobytes()
        pattern_counts[b] += 1
        if b not in pattern_map:
            pattern_map[b] = v
    base = pattern_map[pattern_counts.most_common(1)[0][0]]

    # Find markers: (color, intra_r, intra_c) -> list of (tile_r, tile_c)
    markers: dict[tuple[int, int, int], list[tuple[int, int]]] = {}
    for (tr, tc), tile in interiors.items():
        for dr in range(2):
            for dc in range(2):
                if tile[dr, dc] != base[dr, dc]:
                    key = (int(tile[dr, dc]), dr, dc)
                    markers.setdefault(key, []).append((tr, tc))

    out = grid_np.copy()

    # Propagate each marker type along axis-aligned segments
    for (color, ir, ic), positions in markers.items():
        # Horizontal segments: same tile-row
        row_groups: dict[int, list[int]] = {}
        for tr, tc in positions:
            row_groups.setdefault(tr, []).append(tc)
        for tr, tcs in row_groups.items():
            if len(tcs) >= 2:
                tc_min, tc_max = min(tcs), max(tcs)
                for tc in range(tc_min, tc_max + 1):
                    pixel_r = 1 + tr * 5 + 1 + ir
                    pixel_c = 1 + tc * 5 + 1 + ic
                    if 0 <= pixel_r < rows and 0 <= pixel_c < cols:
                        out[pixel_r, pixel_c] = color

        # Vertical segments: same tile-column
        col_groups: dict[int, list[int]] = {}
        for tr, tc in positions:
            col_groups.setdefault(tc, []).append(tr)
        for tc, trs in col_groups.items():
            if len(trs) >= 2:
                tr_min, tr_max = min(trs), max(trs)
                for tr in range(tr_min, tr_max + 1):
                    pixel_r = 1 + tr * 5 + 1 + ir
                    pixel_c = 1 + tc * 5 + 1 + ic
                    if 0 <= pixel_r < rows and 0 <= pixel_c < cols:
                        out[pixel_r, pixel_c] = color

    return out


def _anchor_fill_find_clusters(grid_list: list[list[int]], val: int) -> list[frozenset[tuple[int, int]]]:
    """BFS connected-component finder for _execute_anchor_fill_brute."""
    rows, cols = len(grid_list), len(grid_list[0])
    seen: set[tuple[int, int]] = set()
    clusters: list[frozenset[tuple[int, int]]] = []
    for r in range(rows):
        for c in range(cols):
            if grid_list[r][c] == val and (r, c) not in seen:
                cl: set[tuple[int, int]] = set()
                q = [(r, c)]
                while q:
                    cr, cc = q.pop()
                    if (cr, cc) in cl:
                        continue
                    cl.add((cr, cc))
                    seen.add((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if (
                            0 <= nr < rows
                            and 0 <= nc < cols
                            and grid_list[nr][nc] == val
                            and (nr, nc) not in cl
                        ):
                            q.append((nr, nc))
                clusters.append(frozenset(cl))
    return clusters


def _anchor_fill_normalize(cells: frozenset[tuple[int, int]]) -> frozenset[tuple[int, int]]:
    lst = list(cells)
    mr = min(r for r, c in lst)
    mc = min(c for r, c in lst)
    return frozenset((r - mr, c - mc) for r, c in lst)


def _anchor_fill_apply_tr(
    cells: list[tuple[int, int]], flip: bool, rot: int
) -> list[tuple[int, int]]:
    cur = [(r, -c) for r, c in cells] if flip else list(cells)
    if rot == 0:
        return cur
    elif rot == 1:
        return [(c, -r) for r, c in cur]
    elif rot == 2:
        return [(-r, -c) for r, c in cur]
    else:  # rot == 3
        return [(-c, r) for r, c in cur]


def _execute_anchor_fill_brute(grid_np: np.ndarray) -> np.ndarray:
    """Execute the anchor-fill brute-force solver for ARC task 79369cc6.

    Rule:
      1. Find the 4-cluster (orig_4) and all multi-6 clusters.
      2. Find all multi-6 clusters adjacent to orig_4 (all_adjacent); use first as anchor.
      3. Combined shape = anchor | orig_4, normalized to bounding-box-relative form.
      4. Brute-force: for each rotation/flip and each top-left (tl_r, tl_c):
           a. Anchor cells must be in-grid 6-cells.
           b. Skip positions where anchor_placed equals any of all_adjacent (source zone).
           c. In-grid 4-part cells must be non-4 and non-6.
           d. At least one in-grid 4-part cell must exist.
           e. KEY: bounding-box cells NOT in the combined shape must all be in-grid 6-cells.
           f. Write 4 to the in-grid 4-part cells.
    """
    grid_list = grid_np.tolist()
    rows, cols = len(grid_list), len(grid_list[0])

    four_all = frozenset(
        (r, c) for r in range(rows) for c in range(cols) if grid_list[r][c] == 4
    )
    six_clusters = _anchor_fill_find_clusters(grid_list, 6)
    multi_6s = [cl for cl in six_clusters if len(cl) > 1]

    if not four_all:
        return grid_np.copy()

    anchor: frozenset[tuple[int, int]] | None = None
    all_adjacent: list[frozenset[tuple[int, int]]] = []
    for mc in multi_6s:
        adj = frozenset(
            (r + dr, c + dc)
            for r, c in mc
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
        )
        if adj & four_all:
            all_adjacent.append(mc)
            if anchor is None:
                anchor = mc

    if anchor is None:
        return grid_np.copy()

    combined = anchor | four_all
    combined_norm = _anchor_fill_normalize(combined)
    mr2 = min(r for r, c in combined)
    mc2 = min(c for r, c in combined)
    anchor_in_combined = frozenset((r - mr2, c - mc2) for r, c in anchor)

    out = grid_np.copy()

    for flip in [False, True]:
        for rot in range(4):
            tc = _anchor_fill_apply_tr(list(combined_norm), flip, rot)
            mr = min(r for r, c in tc)
            mc = min(c for r, c in tc)
            new_comb = frozenset((r - mr, c - mc) for r, c in tc)
            ta = _anchor_fill_apply_tr(list(anchor_in_combined), flip, rot)
            new_anch = frozenset((r - mr, c - mc) for r, c in ta)
            new_4 = new_comb - new_anch
            h = max(r for r, c in new_comb)
            w = max(c for r, c in new_comb)

            bbox = frozenset((r, c) for r in range(h + 1) for c in range(w + 1))
            missing_norm = bbox - new_comb

            for tl_r in range(-h, rows):
                for tl_c in range(-w, cols):
                    ap = frozenset((tl_r + dr, tl_c + dc) for dr, dc in new_anch)
                    fp = frozenset((tl_r + dr, tl_c + dc) for dr, dc in new_4)

                    if not all(
                        0 <= r < rows and 0 <= c < cols and grid_list[r][c] == 6
                        for r, c in ap
                    ):
                        continue

                    if any(ap == adj for adj in all_adjacent):
                        continue

                    fig = frozenset(
                        (r, c) for r, c in fp if 0 <= r < rows and 0 <= c < cols
                    )
                    if not all(grid_list[r][c] not in (4, 6) for r, c in fig):
                        continue

                    if not fig:
                        continue

                    miss_g = frozenset(
                        (tl_r + dr, tl_c + dc) for dr, dc in missing_norm
                    )
                    if not all(
                        0 <= r < rows and 0 <= c < cols and grid_list[r][c] == 6
                        for r, c in miss_g
                    ):
                        continue

                    for r, c in fig:
                        out[r, c] = 4

    return out


def _execute_largest_zero_rect_fill(grid_np: np.ndarray) -> np.ndarray:
    """Find the largest all-zero rectangle, shrink by 1 on each side, fill with 8."""
    rows, cols = grid_np.shape
    # Build histogram of consecutive zeros above each cell
    heights = np.zeros((rows, cols), dtype=int)
    for r in range(rows):
        for c in range(cols):
            if grid_np[r, c] == 0:
                heights[r, c] = (heights[r - 1, c] + 1) if r > 0 else 1
            else:
                heights[r, c] = 0

    best_area = 0
    best_rect = (0, 0, 0, 0)  # r0, c0, r1, c1 (inclusive)
    for r in range(rows):
        h = heights[r].tolist()
        stack: list[tuple[int, int]] = []
        for c in range(cols + 1):
            curr_h = h[c] if c < cols else 0
            start = c
            while stack and stack[-1][1] > curr_h:
                sc, sh = stack.pop()
                area = sh * (c - sc)
                if area > best_area:
                    best_area = area
                    best_rect = (r - sh + 1, sc, r, c - 1)
                start = sc
            stack.append((start, curr_h))

    r0, c0, r1, c1 = best_rect
    out = grid_np.copy()
    # Shrink by 1 on each side and fill with 8
    ir0, ic0, ir1, ic1 = r0 + 1, c0 + 1, r1 - 1, c1 - 1
    if ir0 <= ir1 and ic0 <= ic1:
        out[ir0 : ir1 + 1, ic0 : ic1 + 1] = 8
    return out


def _all_dihedrals(template: frozenset) -> set[frozenset]:
    """Generate all 8 dihedral symmetry variants (4 rotations x 2 flips)."""
    pts = list(template)
    variants: set[frozenset] = set()
    for _rot in range(4):
        variants.add(frozenset(sorted(pts)))
        # flip across vertical axis
        flipped = [(r, -c) for r, c in pts]
        min_r = min(r for r, c in flipped)
        min_c = min(c for r, c in flipped)
        variants.add(frozenset((r - min_r, c - min_c) for r, c in flipped))
        # rotate 90 CW: (r,c) -> (c, -r)
        pts = [(c, -r) for r, c in pts]
        min_r = min(r for r, c in pts)
        min_c = min(c for r, c in pts)
        pts = [(r - min_r, c - min_c) for r, c in pts]
    return variants


def _execute_dihedral_template_match(grid_np: np.ndarray, target_color: int) -> np.ndarray:
    """Find 8-template shape, replace all dihedral matches in target_color with 8."""
    eights = list(zip(*np.where(grid_np == 8)))
    if not eights:
        return grid_np
    min_r = min(r for r, c in eights)
    min_c = min(c for r, c in eights)
    template = frozenset((r - min_r, c - min_c) for r, c in eights)
    variants = _all_dihedrals(template)
    rows, cols = grid_np.shape

    # Collect ALL possible matches against the original grid
    all_matches: list[frozenset] = []
    for variant in variants:
        max_r = max(r for r, c in variant)
        max_c = max(c for r, c in variant)
        for dr in range(rows - max_r):
            for dc in range(cols - max_c):
                cells = frozenset((dr + r, dc + c) for r, c in variant)
                if all(grid_np[r, c] == target_color for r, c in cells):
                    all_matches.append(cells)

    # Greedy non-overlapping selection, top-left first
    all_matches.sort(key=lambda m: (min(r for r, c in m), min(c for r, c in m)))
    claimed: set = set()
    out = grid_np.copy()
    for match in all_matches:
        if not (match & claimed):
            claimed |= match
            for r, c in match:
                out[r, c] = 8
    return out


def _execute_panel_complement_fill(grid_np: np.ndarray) -> np.ndarray:
    """Split at divider column, merge panels if right complements left."""
    rows, cols = grid_np.shape
    # Find divider column: uniform non-zero column whose value appears ONLY in that column
    div_col = None
    for c in range(cols):
        col_vals = grid_np[:, c]
        if len(set(int(v) for v in col_vals)) != 1 or col_vals[0] == 0:
            continue
        div_val = int(col_vals[0])
        # Check this value doesn't appear in any other column
        other = np.delete(grid_np, c, axis=1)
        if div_val not in other:
            div_col = c
            break
    if div_col is None:
        return grid_np

    left = grid_np[:, :div_col]
    right = grid_np[:, div_col + 1 :]

    left_zeros = set(zip(*np.where(left == 0)))
    right_nonzero = set(zip(*np.where(right != 0)))

    if left_zeros == right_nonzero:
        out = left.copy()
        for r, c in right_nonzero:
            out[r, c] = right[r, c]
        return out
    return left.copy()


def _execute_grid_select_min_colors(grid_np: np.ndarray) -> np.ndarray:
    """Extract grid cells separated by uniform-color dividers, return cell with fewest non-bg colors."""
    from collections import Counter  # noqa: PLC0415

    h, w = grid_np.shape
    div_color = None
    div_rows = []
    for r in range(h):
        vals = set(int(grid_np[r, c]) for c in range(w))
        if len(vals) == 1:
            v = vals.pop()
            if v > 0:
                div_rows.append(r)
                if div_color is None:
                    div_color = v
    div_cols = []
    for c in range(w):
        vals = set(int(grid_np[r, c]) for r in range(h))
        if len(vals) == 1:
            v = vals.pop()
            if v > 0 and (div_color is None or v == div_color):
                div_cols.append(c)
    if not div_rows and not div_cols:
        return grid_np
    boundaries_r = [-1] + div_rows + [h]
    boundaries_c = [-1] + div_cols + [w]
    cells = []
    for i in range(len(boundaries_r) - 1):
        for j in range(len(boundaries_c) - 1):
            r0 = boundaries_r[i] + 1
            r1 = boundaries_r[i + 1]
            c0 = boundaries_c[j] + 1
            c1 = boundaries_c[j + 1]
            if r0 < r1 and c0 < c1:
                cells.append(grid_np[r0:r1, c0:c1])
    if not cells:
        return grid_np
    best = min(cells, key=lambda c: len(set(int(v) for v in c.flatten()) - {0}))
    return best


def _execute_cc_unique_size_crop(grid_np: np.ndarray) -> np.ndarray:
    """Find foreground CCs, select the one with unique pixel count, crop its bbox."""
    from scipy import ndimage  # noqa: PLC0415
    from collections import Counter  # noqa: PLC0415

    fg = (grid_np > 0).astype(np.int64)
    labeled, n = ndimage.label(fg)
    if n == 0:
        return grid_np
    sizes = {}
    for lbl in range(1, n + 1):
        sizes[lbl] = int((labeled == lbl).sum())
    size_counts = Counter(sizes.values())
    unique_lbls = [lbl for lbl, sz in sizes.items() if size_counts[sz] == 1]
    if len(unique_lbls) != 1:
        return grid_np
    mask = labeled == unique_lbls[0]
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    r0, r1 = np.where(rows)[0][[0, -1]]
    c0, c1 = np.where(cols)[0][[0, -1]]
    return grid_np[r0 : r1 + 1, c0 : c1 + 1]


def _execute_cc_max_colors_crop(grid_np: np.ndarray) -> np.ndarray:
    """Find foreground CCs, select the one with most distinct colors, crop its bbox."""
    from scipy import ndimage  # noqa: PLC0415

    fg = (grid_np > 0).astype(np.int64)
    labeled, n = ndimage.label(fg)
    if n == 0:
        return grid_np
    best_lbl = None
    best_count = -1
    for lbl in range(1, n + 1):
        mask = labeled == lbl
        colors = len(set(int(v) for v in grid_np[mask]))
        if colors > best_count:
            best_count = colors
            best_lbl = lbl
    mask = labeled == best_lbl
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    r0, r1 = np.where(rows)[0][[0, -1]]
    c0, c1 = np.where(cols)[0][[0, -1]]
    return grid_np[r0 : r1 + 1, c0 : c1 + 1]


def _execute_cc_min_minority_crop(grid_np: np.ndarray) -> np.ndarray:
    """Find foreground CCs, select the one with fewest non-dominant-color pixels, crop its bbox."""
    from scipy import ndimage  # noqa: PLC0415
    from collections import Counter  # noqa: PLC0415

    fg = (grid_np > 0).astype(np.int64)
    labeled, n = ndimage.label(fg)
    if n == 0:
        return grid_np
    all_colors = Counter(int(v) for v in grid_np.flat if v > 0)
    dominant = all_colors.most_common(1)[0][0]
    best_lbl = None
    best_minority = float("inf")
    for lbl in range(1, n + 1):
        mask = labeled == lbl
        minority = int(np.sum((grid_np[mask] != dominant) & (grid_np[mask] > 0)))
        if minority < best_minority:
            best_minority = minority
            best_lbl = lbl
    mask = labeled == best_lbl
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    r0, r1 = np.where(rows)[0][[0, -1]]
    c0, c1 = np.where(cols)[0][[0, -1]]
    return grid_np[r0 : r1 + 1, c0 : c1 + 1]


def _execute_downscale_max(grid_np: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Downscale input to (target_h, target_w) taking max of each block."""
    ih, iw = grid_np.shape
    if ih % target_h != 0 or iw % target_w != 0:
        return grid_np
    ky, kx = ih // target_h, iw // target_w
    result = np.zeros((target_h, target_w), dtype=grid_np.dtype)
    for r in range(target_h):
        for c in range(target_w):
            block = grid_np[r * ky : (r + 1) * ky, c * kx : (c + 1) * kx]
            result[r, c] = int(block.max())
    return result


def _execute_tile_by_color_count(grid_np: np.ndarray) -> np.ndarray:
    """Tile input NxN where N = number of distinct non-bg colors."""
    n_colors = len(set(int(v) for v in grid_np.flatten()) - {0})
    if n_colors < 1:
        return grid_np
    return np.tile(grid_np, (n_colors, n_colors))


def _execute_tile_self_simple(grid_np: np.ndarray) -> np.ndarray:
    """Tile input by (ih, iw) unconditionally."""
    ih, iw = grid_np.shape
    return np.tile(grid_np, (ih, iw))


def _execute_odd_one_out_crop(grid_np: np.ndarray) -> np.ndarray:
    """Find the shape that appears exactly once; all others appear in pairs. Crop it."""
    from scipy import ndimage

    fg = (grid_np > 0).astype(int)
    labeled, n = ndimage.label(fg)
    if n == 0:
        return grid_np
    # Extract bounding box crops for each CC
    crops = []
    for lbl in range(1, n + 1):
        mask = labeled == lbl
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        r0, r1 = np.where(rows)[0][[0, -1]]
        c0, c1 = np.where(cols)[0][[0, -1]]
        crop = grid_np[r0 : r1 + 1, c0 : c1 + 1]
        crops.append(crop)
    # Group by (shape, content) — find the singleton
    from collections import Counter

    keys = []
    for c in crops:
        keys.append((c.shape, c.tobytes()))
    counter = Counter(keys)
    for i, k in enumerate(keys):
        if counter[k] == 1:
            return crops[i]
    return grid_np


def _execute_downscale_majority(grid_np: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Downscale input to (target_h, target_w) taking majority non-bg color of each block."""
    from collections import Counter

    ih, iw = grid_np.shape
    if ih % target_h != 0 or iw % target_w != 0:
        return grid_np
    ky, kx = ih // target_h, iw // target_w
    result = np.zeros((target_h, target_w), dtype=grid_np.dtype)
    for r in range(target_h):
        for c in range(target_w):
            block = grid_np[r * ky : (r + 1) * ky, c * kx : (c + 1) * kx]
            vals = [int(v) for v in block.flatten() if v > 0]
            if vals:
                counter = Counter(vals)
                result[r, c] = counter.most_common(1)[0][0]
    return result


def _execute_border_repeat_edge(grid_np: np.ndarray, pad_n: int) -> np.ndarray:
    """Grow grid by repeating edge pixels outward pad_n times."""
    return np.pad(grid_np, pad_n, mode="edge")


def _execute_tile_mirror_2x2_v2(grid_np: np.ndarray) -> np.ndarray:
    """2x2 mirror: TL=rot180, TR=flipud, BL=fliplr, BR=inp."""
    tl = np.rot90(grid_np, 2)
    tr = np.flipud(grid_np)
    bl = np.fliplr(grid_np)
    br = grid_np
    return np.concatenate(
        [np.concatenate([tl, tr], axis=1), np.concatenate([bl, br], axis=1)], axis=0
    )


def _execute_tile_rotate_ccw_2x2(grid_np: np.ndarray) -> np.ndarray:
    """2x2 CCW rotation: TL=inp, TR=rot90, BL=rot180, BR=rot270. Square inputs only."""
    tl = grid_np
    tr = np.rot90(grid_np, 1)
    bl = np.rot90(grid_np, 2)
    br = np.rot90(grid_np, 3)
    return np.concatenate(
        [np.concatenate([tl, tr], axis=1), np.concatenate([bl, br], axis=1)], axis=0
    )


def _execute_invert_tile_2x2(grid_np: np.ndarray) -> np.ndarray:
    """Swap bg/fg (single non-bg color), then tile 2x2."""
    colors = set(int(v) for v in grid_np.flatten()) - {0}
    if len(colors) != 1:
        return grid_np
    fg_color = colors.pop()
    inverted = np.where(grid_np == 0, fg_color, 0).astype(grid_np.dtype)
    return np.tile(inverted, (2, 2))


def _execute_downscale_all_nonzero(grid_np: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Downscale: output = 0 if block has any zero, else the block's dominant non-bg color."""
    from collections import Counter  # noqa: PLC0415

    ih, iw = grid_np.shape
    if ih % target_h != 0 or iw % target_w != 0:
        return grid_np
    ky, kx = ih // target_h, iw // target_w
    result = np.zeros((target_h, target_w), dtype=grid_np.dtype)
    for r in range(target_h):
        for c in range(target_w):
            block = grid_np[r * ky : (r + 1) * ky, c * kx : (c + 1) * kx]
            if np.all(block > 0):
                vals = [int(v) for v in block.flatten() if v > 0]
                result[r, c] = Counter(vals).most_common(1)[0][0]
    return result


def _execute_color_bbox_crop(grid_np: np.ndarray, color: int) -> np.ndarray:
    """Crop input to bounding box of all pixels matching `color`."""
    mask = grid_np == color
    if not mask.any():
        return grid_np
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    r0, r1 = np.where(rows)[0][[0, -1]]
    c0, c1 = np.where(cols)[0][[0, -1]]
    return grid_np[r0 : r1 + 1, c0 : c1 + 1]


def _execute_quadrant_extract(grid_np: np.ndarray, quadrant: str) -> np.ndarray:
    """Extract one quadrant of the grid (TL, TR, BL, BR)."""
    h, w = grid_np.shape
    mh, mw = h // 2, w // 2
    if quadrant == "TL":
        return grid_np[:mh, :mw]
    elif quadrant == "TR":
        return grid_np[:mh, mw:]
    elif quadrant == "BL":
        return grid_np[mh:, :mw]
    elif quadrant == "BR":
        return grid_np[mh:, mw:]
    return grid_np


def _execute_max_solid_rect_crop(grid_np: np.ndarray, color: int) -> np.ndarray:
    """Find the largest axis-aligned solid rectangle of `color` and crop to it."""
    mask = (grid_np == color).astype(np.int32)
    h, w = mask.shape
    # DP: heights of consecutive color-pixels above each cell
    heights = np.zeros((h, w), dtype=np.int32)
    heights[0, :] = mask[0, :]
    for r in range(1, h):
        for c in range(w):
            heights[r, c] = (heights[r - 1, c] + 1) if mask[r, c] else 0
    best_area = 0
    best_rect = (0, 0, 0, 0)  # r0, c0, r1, c1
    for r in range(h):
        # Largest rectangle in histogram for row r
        stack: list[int] = []
        for c in range(w + 1):
            cur_h = int(heights[r, c]) if c < w else 0
            while stack and int(heights[r, stack[-1]]) > cur_h:
                height = int(heights[r, stack.pop()])
                width = c if not stack else c - stack[-1] - 1
                area = height * width
                if area > best_area:
                    best_area = area
                    c0 = stack[-1] + 1 if stack else 0
                    best_rect = (r - height + 1, c0, r, c0 + width - 1)
            stack.append(c)
    if best_area == 0:
        return grid_np
    r0, c0, r1, c1 = best_rect
    return grid_np[r0 : r1 + 1, c0 : c1 + 1]


def _execute_checkerboard_fill(grid_np: np.ndarray) -> np.ndarray:
    """Fill grid with grid-line pattern: even rows all 1, odd rows checkerboard."""
    h, w = grid_np.shape
    out = np.zeros_like(grid_np)
    for r in range(h):
        for c in range(w):
            if r % 2 == 0:
                out[r, c] = 1
            elif c % 2 == 0:
                out[r, c] = 1
    return out


def _execute_majority_color_indicator(grid_np: np.ndarray) -> np.ndarray:
    """Find 5-divider row, count colors above, place most common at bottom-center."""
    from collections import Counter

    h, w = grid_np.shape
    out = grid_np.copy()
    div_row = None
    for r in range(h):
        if np.all(grid_np[r, :] == 5):
            div_row = r
            break
    if div_row is None:
        return out
    above = grid_np[:div_row, :]
    counts = Counter(int(v) for v in above.flatten() if v != 5 and v != 0)
    if not counts:
        return out
    most_common_color = counts.most_common(1)[0][0]
    center_col = w // 2
    out[h - 1, center_col] = most_common_color
    return out


def _execute_rotate_arm_cw(grid_np: np.ndarray) -> np.ndarray:
    """Rotate color-2 arm CW around color-5 pivot, recolor old arm positions to 3."""
    pivots = np.argwhere(grid_np == 5)
    if len(pivots) == 0:
        return grid_np
    pr, pc = int(pivots[0, 0]), int(pivots[0, 1])
    arm_cells = np.argwhere(grid_np == 2)
    if len(arm_cells) == 0:
        return grid_np
    out = grid_np.copy()
    # Recolor old arm to 3
    for r, c in arm_cells:
        out[int(r), int(c)] = 3
    # Rotate each arm cell CW around pivot: (dr, dc) -> (dc, -dr)
    h, w = grid_np.shape
    for r, c in arm_cells:
        dr, dc = int(r) - pr, int(c) - pc
        nr, nc = pr + dc, pc - dr
        if 0 <= nr < h and 0 <= nc < w:
            out[nr, nc] = 2
    return out


def _execute_bg_cluster_fill(grid_np: np.ndarray, fg_color: int, fill_color: int) -> np.ndarray:
    """Fill bg-color (non-fg) CCs of size >= 2 with fill_color; isolated bg cells stay."""
    from collections import deque

    h, w = grid_np.shape
    bg_val = 0  # ARC background
    # Find CCs of bg_val cells
    visited = np.zeros((h, w), dtype=bool)
    out = grid_np.copy()
    for r in range(h):
        for c in range(w):
            if visited[r, c] or grid_np[r, c] != bg_val:
                continue
            # BFS to find this CC
            q = deque([(r, c)])
            visited[r, c] = True
            cells = [(r, c)]
            while q:
                cr, cc_ = q.popleft()
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc_ + dc
                    if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc] and grid_np[nr, nc] == bg_val:
                        visited[nr, nc] = True
                        q.append((nr, nc))
                        cells.append((nr, nc))
            if len(cells) >= 2:
                for cr, cc_ in cells:
                    out[cr, cc_] = fill_color
    return out


def _execute_diagonal_fill(grid_np: np.ndarray, fill_color: int) -> np.ndarray:
    """Fill the best-fit diagonal (any offset, slope +1 or -1) with fill_color on 0-cells only."""
    h, w = grid_np.shape
    best_cells: list[tuple[int, int]] = []
    best_count = 0
    best_abs_offset = h + w  # tiebreaker: prefer offset closest to 0
    # Try slope +1 diagonals: cells (r, r + offset)
    for offset in range(-(h - 1), w):
        cells = []
        for r in range(h):
            c = r + offset
            if 0 <= c < w and grid_np[r, c] == 0:
                cells.append((r, c))
        if len(cells) > best_count or (len(cells) == best_count and abs(offset) < best_abs_offset):
            best_count = len(cells)
            best_abs_offset = abs(offset)
            best_cells = cells
    # Try slope -1 diagonals: cells (r, w - 1 - r + offset)
    for offset in range(-(h - 1), w):
        cells = []
        for r in range(h):
            c = (w - 1 - r) + offset
            if 0 <= c < w and grid_np[r, c] == 0:
                cells.append((r, c))
        if len(cells) > best_count or (len(cells) == best_count and abs(offset) < best_abs_offset):
            best_count = len(cells)
            best_abs_offset = abs(offset)
            best_cells = cells
    out = grid_np.copy()
    for r, c in best_cells:
        out[r, c] = fill_color
    return out


def _execute_local_rule_3x3(grid_np: np.ndarray, rules_serialized: list) -> np.ndarray:
    """Apply a learned 3x3 cellular automaton rule. Border cells padded with -1."""
    h, w = grid_np.shape
    table: dict[tuple[int, ...], int] = {}
    for nbr_list, val in rules_serialized:
        table[tuple(nbr_list)] = val
    out = grid_np.copy()
    for r in range(h):
        for c in range(w):
            nbr: list[int] = []
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w:
                        nbr.append(int(grid_np[rr, cc]))
                    else:
                        nbr.append(-1)
            key = tuple(nbr)
            if key in table:
                out[r, c] = table[key]
    return out


def _find_divider(grid_np: np.ndarray) -> tuple[str, int, int] | None:
    """Find a column or row divider: uniform non-zero line whose value appears only there."""
    rows, cols = grid_np.shape
    for c in range(cols):
        col_vals = grid_np[:, c]
        if len(set(int(v) for v in col_vals)) != 1 or col_vals[0] == 0:
            continue
        dv = int(col_vals[0])
        other = np.delete(grid_np, c, axis=1)
        if dv not in other:
            return ("col", c, dv)
    for r in range(rows):
        row_vals = grid_np[r, :]
        if len(set(int(v) for v in row_vals)) != 1 or row_vals[0] == 0:
            continue
        dv = int(row_vals[0])
        other = np.delete(grid_np, r, axis=0)
        if dv not in other:
            return ("row", r, dv)
    return None


def _execute_panel_boolean_op(grid_np: np.ndarray, op: str, output_color: int) -> np.ndarray:
    """Split at divider, apply boolean op on binary masks, output single color."""
    div = _find_divider(grid_np)
    if div is None:
        return grid_np
    div_type, div_pos, _ = div
    if div_type == "col":
        left = grid_np[:, :div_pos]
        right = grid_np[:, div_pos + 1 :]
    else:
        left = grid_np[:div_pos, :]
        right = grid_np[div_pos + 1 :, :]
    if left.shape != right.shape:
        return grid_np
    L = (left != 0).astype(bool)
    R = (right != 0).astype(bool)
    if op == "AND":
        result = L & R
    elif op == "OR":
        result = L | R
    elif op == "XOR":
        result = L ^ R
    elif op == "NOR":
        result = ~L & ~R
    else:
        return grid_np
    out = np.zeros_like(left)
    out[result] = output_color
    return out


def execute_program(grid: np.ndarray, program: StraightLineProgram) -> np.ndarray:
    out = np.asarray(grid, dtype=np.int64)
    for step in program.steps:
        if step.op == "identity":
            continue
        if step.op == "color_remap":
            out = _apply_color_remap(out, dict(step.args["mapping"]))
            continue
        if step.op == "shift":
            out = apply_shift(
                out,
                int(step.args["shift_x"]),
                int(step.args["shift_y"]),
            )
            continue
        if step.op == "shift_color":
            color = int(step.args["color"])
            mask = (out == color).astype(np.int64)
            shifted_mask = apply_shift(
                mask,
                int(step.args["shift_x"]),
                int(step.args["shift_y"]),
                fill_value=0,
            )
            out = out.copy()
            out[mask == 1] = 0
            out[shifted_mask == 1] = color
            continue
        if step.op == "copy_color":
            color = int(step.args["color"])
            mask = (out == color).astype(np.int64)
            shifted_mask = apply_shift(
                mask,
                int(step.args["shift_x"]),
                int(step.args["shift_y"]),
                fill_value=0,
            )
            out = out.copy()
            out[shifted_mask == 1] = color
            continue
        if step.op == "flip_x":
            out = np.fliplr(out)
            continue
        if step.op == "flip_y":
            out = np.flipud(out)
            continue
        if step.op == "transpose":
            out = out.T
            continue
        if step.op == "tile":
            out = np.tile(out, (int(step.args["scale_y"]), int(step.args["scale_x"])))
            continue
        if step.op == "tile_self":
            ih, iw = out.shape
            result = np.zeros((ih * ih, iw * iw), dtype=out.dtype)
            for r in range(ih):
                for c in range(iw):
                    if out[r, c] != 0:
                        result[r * ih : (r + 1) * ih, c * iw : (c + 1) * iw] = out
            out = result
            continue
        if step.op == "tile_self_complement":
            ih, iw = out.shape
            nonzero_colors = np.unique(out[out != 0])
            if len(nonzero_colors) == 0:
                continue
            color_counts = [(int(c), int(np.count_nonzero(out == c))) for c in nonzero_colors]
            dominant_color = max(color_counts, key=lambda x: x[1])[0]
            complement = np.where(out == 0, dominant_color, 0).astype(out.dtype)
            result = np.zeros((ih * ih, iw * iw), dtype=out.dtype)
            for r in range(ih):
                for c in range(iw):
                    if out[r, c] != 0:
                        result[r * ih : (r + 1) * ih, c * iw : (c + 1) * iw] = complement
            out = result
            continue
        if step.op == "connect_aligned_pairs":
            out = _apply_connect_aligned_pairs(out)
            continue
        if step.op == "corner_legend_row_swap":
            out = _apply_corner_legend_row_swap(out)
            continue
        if step.op == "panel_consensus_tile":
            consensus = _apply_panel_consensus_tile(out)
            if consensus is not None:
                out = consensus
            continue
        if step.op == "upscale":
            k = int(step.args["scale_k"])
            out = np.repeat(np.repeat(out, k, axis=0), k, axis=1)
            continue
        if step.op == "upscale_color_count":
            k = len(set(int(v) for v in np.unique(out)) - {0})
            if k >= 2:
                out = np.repeat(np.repeat(out, k, axis=0), k, axis=1)
            continue
        if step.op == "crop":
            rows, cols = np.where(out != 0)
            if len(rows) > 0:
                out = out[rows.min() : rows.max() + 1, cols.min() : cols.max() + 1]
            continue
        if step.op == "tile_mirror_2x2":
            tl = out
            tr = np.fliplr(out)
            bl = np.flipud(out)
            br = np.flipud(np.fliplr(out))
            out = np.concatenate(
                [np.concatenate([tl, tr], axis=1), np.concatenate([bl, br], axis=1)], axis=0
            )
            continue
        if step.op in ("gravity_up", "gravity_down", "gravity_left", "gravity_right"):
            direction = step.op[len("gravity_"):]
            h, w = out.shape
            result = np.zeros_like(out)
            if direction == "up":
                for c in range(w):
                    col = out[:, c]
                    nz = col[col != 0]
                    result[: len(nz), c] = nz
            elif direction == "down":
                for c in range(w):
                    col = out[:, c]
                    nz = col[col != 0]
                    result[h - len(nz) :, c] = nz
            elif direction == "left":
                for r in range(h):
                    row = out[r, :]
                    nz = row[row != 0]
                    result[r, : len(nz)] = nz
            elif direction == "right":
                for r in range(h):
                    row = out[r, :]
                    nz = row[row != 0]
                    result[r, w - len(nz) :] = nz
            out = result
            continue
        if step.op == "sym_complete_x":
            out = np.where(out != 0, out, np.fliplr(out))
            continue
        if step.op == "sym_complete_y":
            out = np.where(out != 0, out, np.flipud(out))
            continue
        if step.op == "panel_sym_complete_x":
            from .move_family import _panel_sym_complete_x

            out = _panel_sym_complete_x(out)
            continue
        if step.op == "panel_sym_complete_y":
            from .move_family import _panel_sym_complete_y

            out = _panel_sym_complete_y(out)
            continue
        if step.op == "rotate_180_pivot":
            from .move_family import _rotate_180_around_pivot

            pivot_color = int(step.args.get("color", 0))
            out = _rotate_180_around_pivot(out, pivot_color)
            continue
        if step.op == "select":
            mode = str(step.args.get("mode", "dominant_color"))
            if mode == "dominant_color":
                colors, counts = np.unique(out[out != 0], return_counts=True)
                if len(colors) > 0:
                    dominant = int(colors[np.argmax(counts)])
                    out = np.where(out == dominant, out, 0)
            elif mode == "minority_color":
                colors, counts = np.unique(out[out != 0], return_counts=True)
                if len(colors) > 0:
                    minority = int(colors[np.argmin(counts)])
                    out = np.where(out == minority, out, 0)
            elif mode == "largest_cc":
                from .components import connected_components as _cc

                label_map, components = _cc(out, background=0, connectivity=4)
                if components:
                    largest = max(components, key=lambda c: c.area)
                    new_out = np.zeros_like(out)
                    new_out[label_map == largest.label] = out[label_map == largest.label]
                    out = new_out
            elif mode == "smallest_cc":
                from .components import connected_components as _cc

                label_map, components = _cc(out, background=0, connectivity=4)
                if components:
                    smallest = min(components, key=lambda c: c.area)
                    new_out = np.zeros_like(out)
                    new_out[label_map == smallest.label] = out[label_map == smallest.label]
                    out = new_out
            elif mode == "second_color":
                colors, counts = np.unique(out[out != 0], return_counts=True)
                if len(colors) >= 2:
                    order = np.argsort(-counts)
                    second = int(colors[order[1]])
                    out = np.where(out == second, out, 0)
            elif mode == "unique_object":
                from .move_family import _select_unique_object  # noqa: PLC0415

                out = _select_unique_object(out)
            elif mode == "single_color":
                color = int(step.args.get("color", 1))
                out = np.where(out == color, out, 0)
            elif mode == "mask_by_color":
                keep = int(step.args.get("keep", 1))
                mask_color = int(step.args.get("mask", 1))
                mask = out == mask_color
                out = np.where(mask, keep, 0)
            continue
        if step.op == "paste":
            mode = str(step.args.get("mode", "center"))
            rows, cols_nz = np.where(out != 0)
            if len(rows) > 0:
                r0, r1 = int(rows.min()), int(rows.max()) + 1
                c0, c1 = int(cols_nz.min()), int(cols_nz.max()) + 1
                content = out[r0:r1, c0:c1].copy()
                ch, cw = content.shape
                if mode == "center":
                    h, w = out.shape
                    if ch < h or cw < w:
                        new_out = np.zeros_like(out)
                        top = (h - ch) // 2
                        left = (w - cw) // 2
                        new_out[top : top + ch, left : left + cw] = content
                        out = new_out
                elif mode == "center_on_inp":
                    # Embed into the original input canvas — useful after crop
                    ih, iw = grid.shape
                    new_out = np.zeros_like(grid)
                    top = (ih - ch) // 2
                    left = (iw - cw) // 2
                    new_out[top : top + ch, left : left + cw] = content
                    out = new_out
                elif mode == "tile":
                    h, w = out.shape
                    th, tw = ch, cw
                    if th > 0 and tw > 0:
                        reps_h = (h + th - 1) // th
                        reps_w = (w + tw - 1) // tw
                        tiled = np.tile(content, (reps_h, reps_w))
                        out = tiled[:h, :w]
                elif mode == "stamp":
                    h, w = out.shape
                    row_gaps = np.diff(np.where(np.any(out != 0, axis=1))[0])
                    col_gaps = np.diff(np.where(np.any(out != 0, axis=0))[0])
                    step_r = int(np.median(row_gaps)) if len(row_gaps) > 0 else ch
                    step_c = int(np.median(col_gaps)) if len(col_gaps) > 0 else cw
                    step_r, step_c = max(step_r, ch), max(step_c, cw)
                    new_out = np.zeros_like(out)
                    for top in range(0, h, step_r):
                        for left in range(0, w, step_c):
                            br, bc = min(top + ch, h), min(left + cw, w)
                            new_out[top:br, left:bc] = content[: br - top, : bc - left]
                    out = new_out
            continue
        if step.op == "tile_rotate_2x2":
            tl = out
            tr = np.fliplr(out.T)  # rot90 CW
            bl = np.flipud(out.T)  # rot90 CCW
            br = np.flipud(np.fliplr(out))  # rot180
            out = np.concatenate(
                [np.concatenate([tl, tr], axis=1), np.concatenate([bl, br], axis=1)], axis=0
            )
            continue
        if step.op == "fill_enclosed":
            fill_color = int(step.args["fill_color"])
            reachable = _flood_reachable_background(out)
            result = out.copy()
            result[(out == 0) & ~reachable] = fill_color
            out = result
            continue
        if step.op == "paint_border":
            border_color = int(step.args["border_color"])
            result = out.copy()
            result[0, :] = border_color
            result[-1, :] = border_color
            result[:, 0] = border_color
            result[:, -1] = border_color
            out = result
            continue
        if step.op == "h_concat_flip":
            out = np.concatenate([out, np.fliplr(out)], axis=1)
            continue
        if step.op == "v_concat_flip":
            out = np.concatenate([out, np.flipud(out)], axis=0)
            continue
        if step.op == "extract_panel":
            rp = int(step.args["r_panels"])
            cp = int(step.args["c_panels"])
            ri = int(step.args["r_idx"])
            ci = int(step.args["c_idx"])
            h, w = out.shape
            ph, pw = h // rp, w // cp
            out = out[ri * ph : (ri + 1) * ph, ci * pw : (ci + 1) * pw]
            continue
        if step.op == "extract_half_longer":
            h, w = out.shape
            if h >= w:
                out = out[: h // 2, :]
            else:
                out = out[:, : w // 2]
            continue
        if step.op == "sym_complete_180_frames":
            out = _execute_sym_complete_180_frames(out)
            continue
        if step.op == "template_stamp":
            out = _execute_template_stamp(out)
            continue
        if step.op == "tile_marker_propagate":
            out = _execute_tile_marker_propagate(out)
            continue
        if step.op == "diagonal_project":
            out = _execute_diagonal_project(out)
            continue
        if step.op == "diagonal_cross_connect":
            out = _execute_diagonal_cross_connect(out)
            continue
        if step.op == "marker_erase_outside":
            out = _execute_marker_erase_outside(out)
            continue
        if step.op == "panel_dihedral_complete":
            out = _execute_panel_dihedral_complete(out)
            continue
        if step.op == "anchor_fill_brute":
            out = _execute_anchor_fill_brute(out)
            continue
        if step.op == "largest_zero_rect_fill":
            out = _execute_largest_zero_rect_fill(out)
            continue
        if step.op == "dihedral_template_match":
            out = _execute_dihedral_template_match(out, int(step.args["target_color"]))
            continue
        if step.op == "panel_complement_fill":
            out = _execute_panel_complement_fill(out)
            continue
        if step.op == "panel_boolean_op":
            out = _execute_panel_boolean_op(out, str(step.args["op"]), int(step.args["output_color"]))
            continue
        if step.op == "grid_select_min_colors":
            out = _execute_grid_select_min_colors(out)
            continue
        if step.op == "cc_unique_size_crop":
            out = _execute_cc_unique_size_crop(out)
            continue
        if step.op == "cc_max_colors_crop":
            out = _execute_cc_max_colors_crop(out)
            continue
        if step.op == "cc_min_minority_crop":
            out = _execute_cc_min_minority_crop(out)
            continue
        if step.op == "downscale_max":
            out = _execute_downscale_max(out, int(step.args["target_h"]), int(step.args["target_w"]))
            continue
        if step.op == "tile_by_color_count":
            out = _execute_tile_by_color_count(out)
            continue
        if step.op == "tile_self_simple":
            out = _execute_tile_self_simple(out)
            continue
        if step.op == "odd_one_out_crop":
            out = _execute_odd_one_out_crop(out)
            continue
        if step.op == "downscale_majority":
            out = _execute_downscale_majority(out, int(step.args["target_h"]), int(step.args["target_w"]))
            continue
        if step.op == "border_repeat_edge":
            out = _execute_border_repeat_edge(out, int(step.args["pad_n"]))
            continue
        if step.op == "tile_mirror_2x2_v2":
            out = _execute_tile_mirror_2x2_v2(out)
            continue
        if step.op == "tile_rotate_ccw_2x2":
            out = _execute_tile_rotate_ccw_2x2(out)
            continue
        if step.op == "invert_tile_2x2":
            out = _execute_invert_tile_2x2(out)
            continue
        if step.op == "downscale_all_nonzero":
            out = _execute_downscale_all_nonzero(out, int(step.args["target_h"]), int(step.args["target_w"]))
            continue
        if step.op == "color_bbox_crop":
            out = _execute_color_bbox_crop(out, int(step.args["color"]))
            continue
        if step.op == "quadrant_extract":
            out = _execute_quadrant_extract(out, str(step.args["quadrant"]))
            continue
        if step.op == "max_solid_rect_crop":
            out = _execute_max_solid_rect_crop(out, int(step.args["color"]))
            continue
        if step.op == "checkerboard_fill":
            out = _execute_checkerboard_fill(out)
            continue
        if step.op == "majority_color_indicator":
            out = _execute_majority_color_indicator(out)
            continue
        if step.op == "rotate_arm_cw":
            out = _execute_rotate_arm_cw(out)
            continue
        if step.op == "bg_cluster_fill":
            out = _execute_bg_cluster_fill(out, int(step.args["fg_color"]), int(step.args["fill_color"]))
            continue
        if step.op == "diagonal_fill":
            out = _execute_diagonal_fill(out, int(step.args["fill_color"]))
            continue
        if step.op == "local_rule_3x3":
            out = _execute_local_rule_3x3(out, step.args["rules"])
            continue
        raise NotImplementedError(f"Execution for primitive '{step.op}' is not implemented")
    return out


def _program_matches_train(task: ARCTask, program: StraightLineProgram) -> bool:
    """Return True when a synthesized program exactly matches every train pair."""
    for example in task.train:
        try:
            predicted = execute_program(example.input, program)
        except Exception:
            return False
        if not np.array_equal(predicted, example.output):
            return False
    return True


def _all_same_shape(examples: Iterable[ARCExample]) -> bool:
    return all(example.input.shape == example.output.shape for example in examples)


def _infer_color_mapping(src: np.ndarray, dst: np.ndarray) -> dict[int, int] | None:
    if src.shape != dst.shape:
        return None
    mapping: dict[int, int] = {}
    for color in np.unique(src):
        observed = np.unique(dst[src == color])
        if observed.size != 1:
            return None
        mapping[int(color)] = int(observed[0])
    return mapping


def _component_band_signature(
    grid: np.ndarray,
    label_map: np.ndarray,
    label: int,
) -> tuple[float, float, float]:
    """Return coarse IR / visible / UV means for one connected component."""

    encoding = encode_grid_structurally(grid)
    mask = encoding.component_labels == label
    if not mask.any():
        return (0.0, 0.0, 0.0)
    # Average over all six tongue lanes, then over masked cells.
    tri = encoding.trichromatic_tensor
    band_means = []
    for band in range(3):
        band_view = tri[:, band, :, :]
        band_means.append(float(band_view[:, mask].mean()))
    return tuple(band_means)


def _infer_trichromatic_component_color_mapping(
    src: np.ndarray,
    dst: np.ndarray,
    *,
    max_colors: int = 3,
    signature_tol: float = 0.18,
) -> dict[int, int] | None:
    """Infer up to three stable color correspondences from matched components.

    This is a broader top gate than the exact whole-grid remap. It follows the
    same object across the existing trichromatic bands and only proposes color
    pairs for components whose geometry and non-visible band signatures stay
    stable. The resulting mapping is still verified exactly by the caller.
    """

    if src.shape != dst.shape:
        return None

    src_labels, src_components = connected_components(src)
    dst_labels, dst_components = connected_components(dst)
    if not src_components or not dst_components:
        return None

    dst_by_shape: dict[tuple[int, tuple[int, int, int, int]], list] = {}
    for component in dst_components:
        key = (component.area, component.bbox)
        dst_by_shape.setdefault(key, []).append(component)

    inferred: dict[int, int] = {}
    used_dst_labels: set[int] = set()
    ranked_src = sorted(src_components, key=lambda c: (-c.area, c.label))
    for src_component in ranked_src:
        key = (src_component.area, src_component.bbox)
        candidates = [
            component
            for component in dst_by_shape.get(key, [])
            if component.label not in used_dst_labels
        ]
        if len(candidates) != 1:
            continue

        dst_component = candidates[0]
        src_sig = _component_band_signature(src, src_labels, src_component.label)
        dst_sig = _component_band_signature(dst, dst_labels, dst_component.label)
        # IR and UV should stay stable for the same object; visible may move with recolor.
        if abs(src_sig[0] - dst_sig[0]) > signature_tol:
            continue
        if abs(src_sig[2] - dst_sig[2]) > signature_tol:
            continue

        prev = inferred.get(src_component.color)
        if prev is not None and prev != dst_component.color:
            return None
        inferred[src_component.color] = dst_component.color
        used_dst_labels.add(dst_component.label)
        if len(inferred) >= max_colors:
            break

    return inferred or None


def _apply_corner_legend_row_swap(grid: np.ndarray) -> np.ndarray:
    """Apply row-wise swap pairs from the top-left 2x2 legend, keeping legend fixed."""
    h, w = grid.shape
    if h < 2 or w < 2:
        return np.asarray(grid, dtype=np.int64).copy()

    out = np.asarray(grid, dtype=np.int64).copy()
    legend = out[:2, :2].copy()
    a, b = int(legend[0, 0]), int(legend[0, 1])
    c, d = int(legend[1, 0]), int(legend[1, 1])
    mapping = {a: b, b: a, c: d, d: c}

    remapped = out.copy()
    for src, dst in mapping.items():
        remapped[out == src] = dst
    remapped[:2, :2] = legend
    return remapped


def _merge_mappings(mappings: Iterable[dict[int, int] | None]) -> dict[int, int] | None:
    merged: dict[int, int] = {}
    for mapping in mappings:
        if mapping is None:
            return None
        for src, dst in mapping.items():
            prev = merged.get(src)
            if prev is not None and prev != dst:
                return None
            merged[src] = dst
    return merged


def _infer_color_remap_corridor(task: ARCTask) -> ColorRemapCorridor | None:
    if not _all_same_shape(task.train):
        return None
    per_example_mappings = []
    for example in task.train:
        mapping = _infer_color_mapping(example.input, example.output)
        if mapping is None:
            mapping = _infer_trichromatic_component_color_mapping(example.input, example.output)
        per_example_mappings.append(mapping)

    corridor = intersect_color_remap_corridors(per_example_mappings)
    if corridor is None:
        return None

    exact_mapping = corridor.materialize(identity_for_free=True)
    if exact_mapping is None:
        return None
    if not all(
        np.array_equal(_apply_color_remap(example.input, exact_mapping), example.output)
        for example in task.train
    ):
        return None
    return corridor


def _infer_global_color_remap(task: ARCTask) -> dict[int, int] | None:
    corridor = _infer_color_remap_corridor(task)
    if corridor is None:
        return None
    return corridor.materialize()


def _infer_corner_legend_row_swap(task: ARCTask) -> bool:
    """True if the top-left 2x2 block defines two row-wise color swap pairs."""
    for example in task.train:
        inp = example.input
        if inp.shape[0] < 2 or inp.shape[1] < 2:
            return False
        legend = inp[:2, :2]
        if np.any(legend == 0):
            return False
        if len({int(v) for v in legend.ravel()}) != 4:
            return False
        expected = _apply_corner_legend_row_swap(inp)
        if not np.array_equal(expected, example.output):
            return False
    return True


def _candidate_shifts(example: ARCExample) -> Iterable[tuple[int, int]]:
    h, w = example.input.shape
    for shift_y in range(-(h - 1), h):
        for shift_x in range(-(w - 1), w):
            yield shift_x, shift_y


def _infer_global_shift(task: ARCTask) -> tuple[int, int] | None:
    if not _all_same_shape(task.train):
        return None
    first = task.train[0]
    for shift_x, shift_y in _candidate_shifts(first):
        if all(
            np.array_equal(
                apply_shift(example.input, shift_x, shift_y),
                example.output,
            )
            for example in task.train
        ):
            return shift_x, shift_y
    return None


def _infer_shift_then_color_remap(task: ARCTask) -> tuple[int, int, dict[int, int]] | None:
    if not _all_same_shape(task.train):
        return None
    first = task.train[0]
    for shift_x, shift_y in _candidate_shifts(first):
        shifted_pairs = [
            (apply_shift(example.input, shift_x, shift_y), example.output)
            for example in task.train
        ]
        mapping = _merge_mappings(_infer_color_mapping(src, dst) for src, dst in shifted_pairs)
        if mapping is None:
            continue
        if all(
            np.array_equal(_apply_color_remap(src, mapping), dst) for src, dst in shifted_pairs
        ):
            return shift_x, shift_y, mapping
    return None


def _count_components_for_color(grid: np.ndarray, color: int) -> int:
    _, components = connected_components(grid)
    return sum(1 for component in components if component.color == color)


def _infer_dominant_component_color(task: ARCTask) -> int | None:
    candidate_color: int | None = None
    for example in task.train:
        _, components = connected_components(example.input)
        if not components:
            return None
        dominant = max(components, key=lambda component: (component.area, -component.label))
        if _count_components_for_color(example.input, dominant.color) != 1:
            return None
        if candidate_color is None:
            candidate_color = dominant.color
        elif candidate_color != dominant.color:
            return None
    return candidate_color


def _apply_shift_color(
    grid: np.ndarray,
    color: int,
    shift_x: int,
    shift_y: int,
) -> np.ndarray:
    out = np.asarray(grid, dtype=np.int64).copy()
    mask = (out == color).astype(np.int64)
    shifted_mask = apply_shift(mask, shift_x, shift_y, fill_value=0)
    out[mask == 1] = 0
    out[shifted_mask == 1] = color
    return out


def _infer_dominant_component_shift(task: ARCTask) -> tuple[int, int, int] | None:
    if not _all_same_shape(task.train):
        return None
    color = _infer_dominant_component_color(task)
    if color is None:
        return None
    first = task.train[0]
    for shift_x, shift_y in _candidate_shifts(first):
        if all(
            np.array_equal(
                _apply_shift_color(example.input, color, shift_x, shift_y),
                example.output,
            )
            for example in task.train
        ):
            return color, shift_x, shift_y
    return None


def _apply_copy_color(
    grid: np.ndarray,
    color: int,
    shift_x: int,
    shift_y: int,
) -> np.ndarray:
    out = np.asarray(grid, dtype=np.int64).copy()
    mask = (out == color).astype(np.int64)
    shifted_mask = apply_shift(mask, shift_x, shift_y, fill_value=0)
    out[shifted_mask == 1] = color
    return out


def _infer_dominant_component_copy(task: ARCTask) -> tuple[int, int, int] | None:
    if not _all_same_shape(task.train):
        return None
    color = _infer_dominant_component_color(task)
    if color is None:
        return None
    first = task.train[0]
    for shift_x, shift_y in _candidate_shifts(first):
        if shift_x == 0 and shift_y == 0:
            continue
        if all(
            np.array_equal(
                _apply_copy_color(example.input, color, shift_x, shift_y),
                example.output,
            )
            for example in task.train
        ):
            return color, shift_x, shift_y
    return None


def _infer_unique_component_colors(task: ARCTask) -> list[int] | None:
    colors: list[int] | None = None
    for example in task.train:
        _, components = connected_components(example.input)
        if not components:
            return None
        unique_colors = sorted(
            {
                component.color
                for component in components
                if _count_components_for_color(example.input, component.color) == 1
            }
        )
        if colors is None:
            colors = unique_colors
        elif colors != unique_colors:
            return None
    return colors


def _infer_per_color_shift(
    src: np.ndarray,
    dst: np.ndarray,
    color: int,
) -> tuple[int, int] | None:
    src_mask = (src == color).astype(np.int64)
    dst_mask = (dst == color).astype(np.int64)
    if src_mask.sum() == 0 or dst_mask.sum() == 0 or src_mask.sum() != dst_mask.sum():
        return None
    rows_src, cols_src = np.where(src_mask == 1)
    rows_dst, cols_dst = np.where(dst_mask == 1)
    shift_y = int(rows_dst.min() - rows_src.min())
    shift_x = int(cols_dst.min() - cols_src.min())
    shifted = apply_shift(src_mask, shift_x, shift_y, fill_value=0)
    if np.array_equal(shifted, dst_mask):
        return shift_x, shift_y
    return None


def _infer_multi_unique_color_shift(task: ARCTask) -> list[tuple[int, int, int]] | None:
    if not _all_same_shape(task.train):
        return None
    colors = _infer_unique_component_colors(task)
    if not colors or len(colors) < 2:
        return None

    inferred: dict[int, tuple[int, int]] = {}
    for color in colors:
        color_shift: tuple[int, int] | None = None
        for example in task.train:
            candidate = _infer_per_color_shift(example.input, example.output, color)
            if candidate is None:
                return None
            if color_shift is None:
                color_shift = candidate
            elif color_shift != candidate:
                return None
        assert color_shift is not None
        inferred[color] = color_shift

    for example in task.train:
        predicted = np.asarray(example.input, dtype=np.int64).copy()
        for color, (shift_x, shift_y) in inferred.items():
            predicted = _apply_shift_color(predicted, color, shift_x, shift_y)
        if not np.array_equal(predicted, example.output):
            return None

    return [(color, shift_x, shift_y) for color, (shift_x, shift_y) in sorted(inferred.items())]


def _orientation_candidates() -> dict[str, callable]:
    """Same-shape orientations (input.shape == output.shape)."""
    return {
        "flip_x": np.fliplr,
        "flip_y": np.flipud,
        "transpose": np.transpose,
        "rotate_180": lambda g: np.fliplr(np.flipud(g)),
    }


def _rotation_candidates() -> dict[str, callable]:
    """Shape-changing rotations (transpose/rotate may change HxW to WxH)."""
    return {
        "transpose": np.transpose,
        "rotate_cw": lambda g: np.fliplr(g.T),
        "rotate_ccw": lambda g: np.flipud(g.T),
    }


def _all_rotated_shape(examples: Iterable[ARCExample], fn: callable) -> bool:
    """True if fn(input).shape == output.shape for all examples."""
    return all(fn(example.input).shape == example.output.shape for example in examples)


def _infer_global_orientation(task: ARCTask) -> str | None:
    # Same-shape orientations (including rotate_180)
    if _all_same_shape(task.train):
        for name, fn in _orientation_candidates().items():
            if all(np.array_equal(fn(example.input), example.output) for example in task.train):
                return name
    # Shape-changing rotations (transpose, rotate_cw, rotate_ccw)
    for name, fn in _rotation_candidates().items():
        if _all_rotated_shape(task.train, fn) and all(
            np.array_equal(fn(example.input), example.output) for example in task.train
        ):
            return name
    return None


def _infer_orientation_then_color_remap(task: ARCTask) -> tuple[str, dict[int, int]] | None:
    # Same-shape orientations
    if _all_same_shape(task.train):
        for name, fn in _orientation_candidates().items():
            oriented_pairs = [(fn(example.input), example.output) for example in task.train]
            mapping = _merge_mappings(_infer_color_mapping(src, dst) for src, dst in oriented_pairs)
            if mapping is None:
                continue
            if all(
                np.array_equal(_apply_color_remap(src, mapping), dst) for src, dst in oriented_pairs
            ):
                return name, mapping
    # Shape-changing rotations
    for name, fn in _rotation_candidates().items():
        if not _all_rotated_shape(task.train, fn):
            continue
        oriented_pairs = [(fn(example.input), example.output) for example in task.train]
        mapping = _merge_mappings(_infer_color_mapping(src, dst) for src, dst in oriented_pairs)
        if mapping is None:
            continue
        if all(
            np.array_equal(_apply_color_remap(src, mapping), dst) for src, dst in oriented_pairs
        ):
            return name, mapping
    return None


def _infer_upscale(task: ARCTask) -> int | None:
    """Return scale k if output = np.repeat(np.repeat(input, k, 0), k, 1) for all pairs."""
    first_in = task.train[0].input
    first_out = task.train[0].output
    ih, iw = first_in.shape
    oh, ow = first_out.shape
    if oh < ih or ow < iw or oh % ih != 0 or ow % iw != 0 or oh // ih != ow // iw:
        return None
    k = oh // ih
    if k <= 1:
        return None
    for example in task.train:
        eih, eiw = example.input.shape
        eoh, eow = example.output.shape
        if eoh != eih * k or eow != eiw * k:
            return None
        expected = np.repeat(np.repeat(example.input, k, axis=0), k, axis=1)
        if not np.array_equal(expected, example.output):
            return None
    return k


def _infer_upscale_corridor(task: ARCTask) -> UpscaleCorridor | None:
    """Return an UpscaleCorridor if all examples share a consistent scale_k.

    The corridor captures the full admissible space: scale factor is always
    pinned; the post-upscale color remap is either absent (pure pixel repeat)
    or encoded as a ColorRemapCorridor (consistent recolor across all examples).
    """
    if not task.train:
        return None
    first = task.train[0]
    ih, iw = first.input.shape
    oh, ow = first.output.shape
    if oh < ih or ow < iw or oh % ih != 0 or ow % iw != 0 or oh // ih != ow // iw:
        return None
    k = oh // ih
    if k <= 1:
        return None

    per_example_mappings: list[dict[int, int]] = []
    exact_count = 0
    for ex in task.train:
        eih, eiw = ex.input.shape
        eoh, eow = ex.output.shape
        if eoh % eih != 0 or eow % eiw != 0:
            return None
        if eoh // eih != k or eow // eiw != k:
            return None
        upscaled = np.repeat(np.repeat(ex.input, k, axis=0), k, axis=1)
        if np.array_equal(upscaled, ex.output):
            exact_count += 1
            # Treat as identity remap for every observed color so the
            # corridor intersection can still detect conflicts.
            per_example_mappings.append({int(c): int(c) for c in np.unique(upscaled)})
        else:
            mapping = _infer_color_mapping(upscaled, ex.output)
            if mapping is None:
                return None
            per_example_mappings.append(mapping)

    if exact_count == len(task.train):
        return UpscaleCorridor(scale_k=k, color_remap_corridor=None)

    corridor = intersect_color_remap_corridors(per_example_mappings)
    if corridor is None:
        return None
    return UpscaleCorridor(scale_k=k, color_remap_corridor=corridor)


def _infer_upscale_color_count(task: ARCTask) -> bool:
    """True if output = np.repeat(input, k, 0/1) where k = distinct non-zero colors per example."""
    for example in task.train:
        ih, iw = example.input.shape
        oh, ow = example.output.shape
        k = len(set(int(v) for v in np.unique(example.input)) - {0})
        if k <= 1:
            return False
        if oh != ih * k or ow != iw * k:
            return False
        expected = np.repeat(np.repeat(example.input, k, axis=0), k, axis=1)
        if not np.array_equal(expected, example.output):
            return False
    return True


def _infer_tile_mirror_2x2(task: ARCTask) -> bool:
    """True if output is 2x2 mirror tiling: TL=id, TR=fliplr, BL=flipud, BR=rot180."""
    for example in task.train:
        ih, iw = example.input.shape
        oh, ow = example.output.shape
        if oh != ih * 2 or ow != iw * 2:
            return False
        tl = example.output[:ih, :iw]
        tr = example.output[:ih, iw:]
        bl = example.output[ih:, :iw]
        br = example.output[ih:, iw:]
        if not np.array_equal(tl, example.input):
            return False
        if not np.array_equal(tr, np.fliplr(example.input)):
            return False
        if not np.array_equal(bl, np.flipud(example.input)):
            return False
        if not np.array_equal(br, np.flipud(np.fliplr(example.input))):
            return False
    return True


def _infer_tile_rotate_2x2(task: ARCTask) -> bool:
    """True if output is 2x2 rotational tiling (square inputs only): TL=id, TR=cw, BL=ccw, BR=rot180."""
    for example in task.train:
        ih, iw = example.input.shape
        if ih != iw:
            return False
        oh, ow = example.output.shape
        if oh != ih * 2 or ow != iw * 2:
            return False
        tl = example.output[:ih, :iw]
        tr = example.output[:ih, iw:]
        bl = example.output[ih:, :iw]
        br = example.output[ih:, iw:]
        if not np.array_equal(tl, example.input):
            return False
        if not np.array_equal(tr, np.fliplr(example.input.T)):
            return False
        if not np.array_equal(bl, np.flipud(example.input.T)):
            return False
        if not np.array_equal(br, np.flipud(np.fliplr(example.input))):
            return False
    return True


def _infer_crop_to_bbox(task: ARCTask) -> bool:
    """True if output equals the bounding-box crop of non-zero pixels in input."""
    for example in task.train:
        rows, cols = np.where(example.input != 0)
        if len(rows) == 0:
            return False
        r0, r1 = int(rows.min()), int(rows.max()) + 1
        c0, c1 = int(cols.min()), int(cols.max()) + 1
        expected = example.input[r0:r1, c0:c1]
        if not np.array_equal(expected, example.output):
            return False
    return True


def _infer_crop_then_orient(task: ARCTask) -> str | None:
    """Return orientation name if output = orient(crop_bbox(input)) for all examples."""
    _ORIENT_FNS: dict[str, callable] = {
        "flip_x": np.fliplr,
        "flip_y": np.flipud,
        "transpose": np.transpose,
        "rotate_cw": lambda g: np.fliplr(g.T),
        "rotate_ccw": lambda g: np.flipud(g.T),
        "rotate_180": lambda g: np.flipud(np.fliplr(g)),
    }
    for name, fn in _ORIENT_FNS.items():
        ok = True
        for ex in task.train:
            rows, cols = np.where(ex.input != 0)
            if len(rows) == 0:
                ok = False
                break
            r0, r1 = int(rows.min()), int(rows.max()) + 1
            c0, c1 = int(cols.min()), int(cols.max()) + 1
            cropped = ex.input[r0:r1, c0:c1]
            try:
                transformed = fn(cropped)
            except Exception:
                ok = False
                break
            if not np.array_equal(transformed, ex.output):
                ok = False
                break
        if ok:
            return name
    return None


def _apply_gravity(grid: np.ndarray, direction: str) -> np.ndarray:
    h, w = grid.shape
    result = np.zeros_like(grid)
    if direction == "up":
        for c in range(w):
            col = grid[:, c]
            nz = col[col != 0]
            result[: len(nz), c] = nz
    elif direction == "down":
        for c in range(w):
            col = grid[:, c]
            nz = col[col != 0]
            result[h - len(nz) :, c] = nz
    elif direction == "left":
        for r in range(h):
            row = grid[r, :]
            nz = row[row != 0]
            result[r, : len(nz)] = nz
    elif direction == "right":
        for r in range(h):
            row = grid[r, :]
            nz = row[row != 0]
            result[r, w - len(nz) :] = nz
    return result


def _infer_gravity(task: ARCTask) -> str | None:
    """Return gravity direction ('up','down','left','right') if all examples match."""
    if not _all_same_shape(task.train):
        return None
    for direction in ("up", "down", "left", "right"):
        if all(
            np.array_equal(_apply_gravity(example.input, direction), example.output)
            for example in task.train
        ):
            return direction
    return None


def _infer_sym_complete(task: ARCTask) -> str | None:
    """Return 'x' or 'y' if output = where(input != 0, input, flip(input))."""
    if not _all_same_shape(task.train):
        return None
    for axis, flip_fn in (("x", np.fliplr), ("y", np.flipud)):
        if all(
            np.array_equal(np.where(ex.input != 0, ex.input, flip_fn(ex.input)), ex.output)
            for ex in task.train
        ):
            return axis
    return None


def _infer_tile_self(task: ARCTask) -> bool:
    """Return True if every training pair follows the fractal-tile (tile_self) rule.

    Rule: output[r*ih:(r+1)*ih, c*iw:(c+1)*iw] == input if input[r,c] != 0 else zeros.
    Requires: output.shape == (ih*ih, iw*iw).
    """
    for example in task.train:
        ih, iw = example.input.shape
        oh, ow = example.output.shape
        if oh != ih * ih or ow != iw * iw:
            return False
        for r in range(ih):
            for c in range(iw):
                blk = example.output[r * ih : (r + 1) * ih, c * iw : (c + 1) * iw]
                if example.input[r, c] != 0:
                    if not np.array_equal(blk, example.input):
                        return False
                else:
                    if not np.all(blk == 0):
                        return False
    return True


def _infer_tile_self_complement(task: ARCTask) -> bool:
    """Return True if every training pair follows the tile_self_complement rule.

    Rule: output[r*ih:(r+1)*ih, c*iw:(c+1)*iw] == complement if input[r,c] != 0 else zeros,
    where complement = np.where(input == 0, dominant_color, 0).
    Requires: output.shape == (ih*ih, iw*iw) and input uses a single non-zero color.
    """
    for example in task.train:
        ih, iw = example.input.shape
        oh, ow = example.output.shape
        if oh != ih * ih or ow != iw * iw:
            return False
        nonzero_colors = np.unique(example.input[example.input != 0])
        if len(nonzero_colors) == 0:
            return False
        color_counts = [(int(c), int(np.count_nonzero(example.input == c))) for c in nonzero_colors]
        dominant_color = max(color_counts, key=lambda x: x[1])[0]
        complement = np.where(example.input == 0, dominant_color, 0).astype(example.input.dtype)
        for r in range(ih):
            for c in range(iw):
                blk = example.output[r * ih : (r + 1) * ih, c * iw : (c + 1) * iw]
                if example.input[r, c] != 0:
                    if not np.array_equal(blk, complement):
                        return False
                else:
                    if not np.all(blk == 0):
                        return False
    return True


def _apply_connect_aligned_pairs(grid: np.ndarray) -> np.ndarray:
    """Connect colors that appear exactly twice and are row/column aligned.

    Horizontal segments are painted first and vertical segments second so
    vertical connectors win at crossings.
    """
    out = np.asarray(grid, dtype=np.int64).copy()
    colors = [int(c) for c in np.unique(out) if int(c) != 0]
    horizontal: list[tuple[int, int, int, int]] = []
    vertical: list[tuple[int, int, int, int]] = []
    for color in colors:
        coords = np.argwhere(out == color)
        if coords.shape[0] != 2:
            continue
        (r0, c0), (r1, c1) = coords
        r0, c0, r1, c1 = int(r0), int(c0), int(r1), int(c1)
        if r0 == r1:
            horizontal.append((color, r0, min(c0, c1), max(c0, c1)))
        elif c0 == c1:
            vertical.append((color, c0, min(r0, r1), max(r0, r1)))

    for color, row, c0, c1 in horizontal:
        out[row, c0 : c1 + 1] = color
    for color, col, r0, r1 in vertical:
        out[r0 : r1 + 1, col] = color
    return out


def _dense_band_groups(counts: np.ndarray) -> list[tuple[int, int]]:
    """Return contiguous index groups for rows/cols that are densely populated."""
    if counts.size == 0:
        return []
    max_count = int(counts.max())
    if max_count <= 0:
        return []
    threshold = max(1, int(np.ceil(max_count * 0.6)))
    idx = np.flatnonzero(counts >= threshold)
    if idx.size == 0:
        return []
    groups: list[tuple[int, int]] = []
    start = int(idx[0])
    prev = int(idx[0])
    for value in idx[1:]:
        value = int(value)
        if value == prev + 1:
            prev = value
            continue
        groups.append((start, prev))
        start = value
        prev = value
    groups.append((start, prev))
    return groups


def _panel_groups_with_common_span(groups: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Keep the most common non-unit span to stabilize repeated panel bands."""
    if not groups:
        return []
    spans = [end - start + 1 for start, end in groups]
    non_unit = [span for span in spans if span > 1]
    if not non_unit:
        return groups
    target_span = max(set(non_unit), key=non_unit.count)
    filtered = [group for group in groups if (group[1] - group[0] + 1) == target_span]
    return filtered or groups


def _majority_vote_panel(panels: list[np.ndarray]) -> np.ndarray:
    """Build the canonical panel by per-cell majority, preferring non-zero on ties."""
    stack = np.stack(panels, axis=0)
    h, w = panels[0].shape
    result = np.zeros((h, w), dtype=panels[0].dtype)
    for r in range(h):
        for c in range(w):
            values = stack[:, r, c]
            colors, counts = np.unique(values, return_counts=True)
            max_count = int(counts.max())
            winners = colors[counts == max_count]
            chosen = next((int(color) for color in winners if int(color) != 0), int(winners[0]))
            result[r, c] = chosen
    return result


def _apply_panel_consensus_tile(grid: np.ndarray) -> np.ndarray | None:
    """Regularize repeated panel layouts by stamping a majority-vote canonical tile."""
    row_groups = _panel_groups_with_common_span(_dense_band_groups(np.count_nonzero(grid, axis=1)))
    col_groups = _panel_groups_with_common_span(_dense_band_groups(np.count_nonzero(grid, axis=0)))
    if len(row_groups) < 2 or len(col_groups) < 2:
        return None

    panel_h = row_groups[0][1] - row_groups[0][0] + 1
    panel_w = col_groups[0][1] - col_groups[0][0] + 1
    if panel_h <= 1 or panel_w <= 1:
        return None

    panels = [
        grid[r0 : r1 + 1, c0 : c1 + 1]
        for r0, r1 in row_groups
        for c0, c1 in col_groups
    ]
    if not panels:
        return None
    if any(panel.shape != (panel_h, panel_w) for panel in panels):
        return None

    canonical = _majority_vote_panel(panels)
    result = np.zeros_like(grid)
    for r0, r1 in row_groups:
        for c0, c1 in col_groups:
            result[r0 : r1 + 1, c0 : c1 + 1] = canonical
    return result


def _infer_connect_aligned_pairs(task: ARCTask) -> bool:
    """True if outputs arise from connecting aligned same-color endpoint pairs."""
    if not _all_same_shape(task.train):
        return False
    return all(np.array_equal(_apply_connect_aligned_pairs(ex.input), ex.output) for ex in task.train)


def _infer_tile_scale(task: ARCTask) -> tuple[int, int] | None:
    """Return (scale_y, scale_x) if every training pair is np.tile(input, (sy, sx))."""
    first_in = task.train[0].input
    first_out = task.train[0].output
    ih, iw = first_in.shape
    oh, ow = first_out.shape
    if oh < ih or ow < iw or oh % ih != 0 or ow % iw != 0:
        return None
    sy, sx = oh // ih, ow // iw
    for example in task.train:
        eih, eiw = example.input.shape
        eoh, eow = example.output.shape
        if eoh != eih * sy or eow != eiw * sx:
            return None
        if not np.array_equal(np.tile(example.input, (sy, sx)), example.output):
            return None
    return sy, sx


def _infer_panel_consensus_tile(task: ARCTask) -> bool:
    """True if each output is the repeated-panel consensus regularization of the input."""
    if not _all_same_shape(task.train):
        return False
    for example in task.train:
        predicted = _apply_panel_consensus_tile(example.input)
        if predicted is None or not np.array_equal(predicted, example.output):
            return False
    return True


def _flood_reachable_background(grid: np.ndarray) -> np.ndarray:
    """Boolean mask: True for background (0) cells reachable from the grid border."""
    h, w = grid.shape
    visited = np.zeros((h, w), dtype=bool)
    queue: list[tuple[int, int]] = []
    for r in range(h):
        for c in [0, w - 1]:
            if grid[r, c] == 0 and not visited[r, c]:
                visited[r, c] = True
                queue.append((r, c))
    for c in range(1, w - 1):
        for r in [0, h - 1]:
            if grid[r, c] == 0 and not visited[r, c]:
                visited[r, c] = True
                queue.append((r, c))
    head = 0
    while head < len(queue):
        r, c = queue[head]
        head += 1
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc] and grid[nr, nc] == 0:
                visited[nr, nc] = True
                queue.append((nr, nc))
    return visited


def _infer_fill_enclosed(task: ARCTask) -> int | None:
    """Return fill_color if input→output fills enclosed background cells."""
    fill_color: int | None = None
    for example in task.train:
        inp = example.input
        out = example.output
        if inp.shape != out.shape:
            return None
        reachable = _flood_reachable_background(inp)
        enclosed = (inp == 0) & ~reachable
        if not enclosed.any():
            return None
        changed_out_colors = np.unique(out[enclosed])
        if len(changed_out_colors) != 1:
            return None
        fc = int(changed_out_colors[0])
        if fill_color is None:
            fill_color = fc
        elif fill_color != fc:
            return None
        # Non-enclosed cells must be unchanged
        if not np.array_equal(out[~enclosed], inp[~enclosed]):
            return None
    return fill_color


def _candidate_fill_enclosed_colors(task: ARCTask) -> list[int]:
    """Return plausible fill colors, ordered from strongest evidence to weakest.

    This deliberately allows a wider top gate than `_infer_fill_enclosed`: some
    examples may have no enclosed cells, and the final decision is deferred to
    exact program execution across all train pairs.
    """
    counts: dict[int, int] = {}

    def _bump(color: int) -> None:
        counts[color] = counts.get(color, 0) + 1

    for example in task.train:
        inp = example.input
        out = example.output
        if inp.shape != out.shape:
            continue

        reachable = _flood_reachable_background(inp)
        enclosed = (inp == 0) & ~reachable
        if enclosed.any():
            for color in np.unique(out[enclosed]):
                _bump(int(color))

        nonzero = inp[inp != 0]
        if nonzero.size:
            colors, freqs = np.unique(nonzero, return_counts=True)
            _bump(int(colors[int(np.argmax(freqs))]))

        border = np.concatenate(
            [
                inp[0, :].ravel(),
                inp[-1, :].ravel(),
                inp[1:-1, 0].ravel(),
                inp[1:-1, -1].ravel(),
            ]
        )
        border = border[border != 0]
        if border.size:
            colors, freqs = np.unique(border, return_counts=True)
            _bump(int(colors[int(np.argmax(freqs))]))

    return [color for color, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _infer_paint_border(task: ARCTask) -> int | None:
    """Return border_color if input→output paints the 1px outer border uniformly."""
    border_color: int | None = None
    for example in task.train:
        inp = example.input
        out = example.output
        if inp.shape != out.shape:
            return None
        h, w = inp.shape
        if h < 3 or w < 3:
            return None
        # Inner cells must be unchanged
        if not np.array_equal(inp[1:-1, 1:-1], out[1:-1, 1:-1]):
            return None
        # All border cells in output must share the same color
        border_out = np.concatenate([
            out[0, :].ravel(),
            out[-1, :].ravel(),
            out[1:-1, 0].ravel(),
            out[1:-1, -1].ravel(),
        ])
        colors = np.unique(border_out)
        if len(colors) != 1:
            return None
        bc = int(colors[0])
        if border_color is None:
            border_color = bc
        elif border_color != bc:
            return None
        # Guard: at least one border cell must have changed (rule out identity)
        border_inp = np.concatenate([
            inp[0, :].ravel(),
            inp[-1, :].ravel(),
            inp[1:-1, 0].ravel(),
            inp[1:-1, -1].ravel(),
        ])
        if np.array_equal(border_inp, border_out):
            return None
    return border_color


def _infer_h_concat_flip(task: ARCTask) -> bool:
    """True if output = [input | fliplr(input)] for every training example."""
    for example in task.train:
        inp = example.input
        out = example.output
        ih, iw = inp.shape
        if out.shape != (ih, iw * 2):
            return False
        if not np.array_equal(np.concatenate([inp, np.fliplr(inp)], axis=1), out):
            return False
    return True


def _infer_v_concat_flip(task: ARCTask) -> bool:
    """True if output = [input / flipud(input)] for every training example."""
    for example in task.train:
        inp = example.input
        out = example.output
        ih, iw = inp.shape
        if out.shape != (ih * 2, iw):
            return False
        if not np.array_equal(np.concatenate([inp, np.flipud(inp)], axis=0), out):
            return False
    return True


def _infer_extract_panel(task: ARCTask) -> tuple[int, int, int, int] | None:
    """Return (r_panels, c_panels, r_idx, c_idx) if input is a regular panel grid."""
    if not task.train:
        return None
    first = task.train[0]
    ih, iw = first.input.shape
    oh, ow = first.output.shape

    candidates: list[tuple[int, int, int, int]] = []
    for rp in range(1, 11):  # up to 10 panels per dimension (ARC grids ≤ 30×30)
        for cp in range(1, 11):
            if rp == 1 and cp == 1:
                continue
            if ih % rp != 0 or iw % cp != 0:
                continue
            ph, pw = ih // rp, iw // cp
            if ph != oh or pw != ow:
                continue
            for ri in range(rp):
                for ci in range(cp):
                    panel = first.input[ri * ph : (ri + 1) * ph, ci * pw : (ci + 1) * pw]
                    if np.array_equal(panel, first.output):
                        candidates.append((rp, cp, ri, ci))

    for rp, cp, ri, ci in candidates:
        valid = True
        for example in task.train:
            eih, eiw = example.input.shape
            eoh, eow = example.output.shape
            if eih % rp != 0 or eiw % cp != 0:
                valid = False
                break
            ph, pw = eih // rp, eiw // cp
            if ph != eoh or pw != eow:
                valid = False
                break
            panel = example.input[ri * ph : (ri + 1) * ph, ci * pw : (ci + 1) * pw]
            if not np.array_equal(panel, example.output):
                valid = False
                break
        if valid:
            return (rp, cp, ri, ci)
    return None


def _infer_extract_half_longer(task: ARCTask) -> bool:
    """True if output is the first half along the longer input dimension.

    Tie-breaking for square grids (h == w): takes the top half (rows).
    Tasks where the correct split is the left half of a square grid will
    not be matched by this family.
    """
    for example in task.train:
        inp = example.input
        out = example.output
        h, w = inp.shape
        if h >= w:
            expected = inp[: h // 2, :]
        else:
            expected = inp[:, : w // 2]
        if not np.array_equal(expected, out):
            return False
    return True


def _infer_select_single_color_crop(task: ARCTask) -> SynthesizedSolution | None:
    """Try selecting each individual non-zero color and cropping to its bbox."""
    # Narrow candidates: only colors present in ALL outputs
    candidate_colors: set[int] | None = None
    for ex in task.train:
        out_colors = set(int(c) for c in np.unique(ex.output)) - {0}
        if candidate_colors is None:
            candidate_colors = out_colors
        else:
            candidate_colors &= out_colors
    if not candidate_colors:
        return None

    for color in sorted(candidate_colors):
        program = StraightLineProgram(
            name=f"select_color_{color}_crop",
            steps=(
                IRStep(op="select", args={"mode": "single_color", "color": color}),
                IRStep(op="crop", args={}),
            ),
        )
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="select_single_color_crop")
    return None


def _infer_select_single_color_crop_orient(task: ARCTask) -> SynthesizedSolution | None:
    """Select single color + crop + orientation transform."""
    candidate_colors: set[int] | None = None
    for ex in task.train:
        out_colors = set(int(c) for c in np.unique(ex.output)) - {0}
        if candidate_colors is None:
            candidate_colors = out_colors
        else:
            candidate_colors &= out_colors
    if not candidate_colors:
        return None

    orient_ops = [
        ("flip_x", (IRStep(op="flip_x", args={}),)),
        ("flip_y", (IRStep(op="flip_y", args={}),)),
        ("transpose", (IRStep(op="transpose", args={}),)),
        ("rotate_cw", (IRStep(op="transpose", args={}), IRStep(op="flip_x", args={}))),
        ("rotate_ccw", (IRStep(op="transpose", args={}), IRStep(op="flip_y", args={}))),
        ("rotate_180", (IRStep(op="flip_x", args={}), IRStep(op="flip_y", args={}))),
    ]
    for color in sorted(candidate_colors):
        for orient_name, orient_steps in orient_ops:
            program = StraightLineProgram(
                name=f"select_color_{color}_crop_{orient_name}",
                steps=(
                    IRStep(op="select", args={"mode": "single_color", "color": color}),
                    IRStep(op="crop", args={}),
                ) + orient_steps,
            )
            if _program_matches_train(task, program):
                return SynthesizedSolution(
                    program=program, family="select_single_color_crop_orient"
                )
    return None


def _infer_mask_by_color(task: ARCTask) -> SynthesizedSolution | None:
    """Boolean AND mask: keep cells of color A only where color B is also present.

    For same-shape tasks where the output is a filtered version of the input.
    """
    if not all(ex.input.shape == ex.output.shape for ex in task.train):
        return None

    # Gather all non-zero colors across train inputs
    all_colors: set[int] = set()
    for ex in task.train:
        all_colors.update(int(c) for c in np.unique(ex.input) if c != 0)

    for keep_color in sorted(all_colors):
        for mask_color in sorted(all_colors):
            if keep_color == mask_color:
                continue
            matched = True
            for ex in task.train:
                mask = ex.input == mask_color
                result = np.where(mask, keep_color, 0)
                if not np.array_equal(result, ex.output):
                    matched = False
                    break
            if matched:
                program = StraightLineProgram(
                    name=f"mask_color_{keep_color}_by_{mask_color}",
                    steps=(
                        IRStep(
                            op="select",
                            args={"mode": "mask_by_color", "keep": keep_color, "mask": mask_color},
                        ),
                    ),
                )
                return SynthesizedSolution(program=program, family="mask_by_color")
    return None


def _solve_family(
    task: ARCTask,
    family: str,
    cache: dict[str, object],
) -> SynthesizedSolution | None:
    if family == "identity":
        if all(np.array_equal(example.input, example.output) for example in task.train):
            return SynthesizedSolution(program=make_identity_program(), family="identity")
        return None

    if family == "tile_self":
        if _infer_tile_self(task):
            return SynthesizedSolution(program=make_tile_self_program(), family="tile_self")
        return None

    if family == "tile_self_complement":
        if _infer_tile_self_complement(task):
            return SynthesizedSolution(
                program=make_tile_self_complement_program(), family="tile_self_complement"
            )
        return None

    if family == "tile_mirror_2x2":
        tile_mirror = cache.get("tile_mirror_2x2")
        if tile_mirror is None:
            tile_mirror = _infer_tile_mirror_2x2(task)
            cache["tile_mirror_2x2"] = tile_mirror
        if tile_mirror:
            program = make_tile_mirror_2x2_program()
            if _program_matches_train(task, program):
                return SynthesizedSolution(program=program, family="tile_mirror_2x2")
        return None

    if family == "tile_rotate_2x2":
        tile_rotate = cache.get("tile_rotate_2x2")
        if tile_rotate is None:
            tile_rotate = _infer_tile_rotate_2x2(task)
            cache["tile_rotate_2x2"] = tile_rotate
        if tile_rotate:
            return SynthesizedSolution(program=make_tile_rotate_2x2_program(), family="tile_rotate_2x2")
        return None

    if family == "tile":
        tile_scale = cache.get("tile_scale")
        if tile_scale is None:
            tile_scale = _infer_tile_scale(task)
            cache["tile_scale"] = tile_scale
        if tile_scale is not None:
            sy, sx = tile_scale
            return SynthesizedSolution(program=make_tile_program(sy, sx), family="tile")
        return None

    if family == "connect_aligned_pairs":
        connect_pairs = cache.get("connect_aligned_pairs")
        if connect_pairs is None:
            connect_pairs = _infer_connect_aligned_pairs(task)
            cache["connect_aligned_pairs"] = connect_pairs
        if connect_pairs:
            return SynthesizedSolution(
                program=make_connect_aligned_pairs_program(),
                family="connect_aligned_pairs",
            )
        return None

    if family == "corner_legend_row_swap":
        legend_swap = cache.get("corner_legend_row_swap")
        if legend_swap is None:
            legend_swap = _infer_corner_legend_row_swap(task)
            cache["corner_legend_row_swap"] = legend_swap
        if legend_swap:
            return SynthesizedSolution(
                program=make_corner_legend_row_swap_program(),
                family="corner_legend_row_swap",
            )
        return None

    if family == "panel_consensus_tile":
        panel_consensus = cache.get("panel_consensus_tile")
        if panel_consensus is None:
            panel_consensus = _infer_panel_consensus_tile(task)
            cache["panel_consensus_tile"] = panel_consensus
        if panel_consensus:
            program = make_panel_consensus_tile_program()
            if _program_matches_train(task, program):
                return SynthesizedSolution(program=program, family="panel_consensus_tile")
        return None

    if family == "color_remap":
        mapping = cache.get("color_remap")
        if mapping is None:
            mapping = _infer_global_color_remap(task)
            cache["color_remap"] = mapping
        if mapping is not None:
            return SynthesizedSolution(program=make_color_remap_program(mapping), family="color_remap")
        return None

    if family == "shift":
        shift = cache.get("shift")
        if shift is None:
            shift = _infer_global_shift(task)
            cache["shift"] = shift
        if shift is not None:
            return SynthesizedSolution(program=make_shift_program(*shift), family="shift")
        return None

    if family == "dominant_component_shift":
        dominant_component_shift = cache.get("dominant_component_shift")
        if dominant_component_shift is None:
            dominant_component_shift = _infer_dominant_component_shift(task)
            cache["dominant_component_shift"] = dominant_component_shift
        if dominant_component_shift is not None:
            color, shift_x, shift_y = dominant_component_shift
            return SynthesizedSolution(
                program=make_shift_color_program(color, shift_x, shift_y),
                family="dominant_component_shift",
            )
        return None

    if family == "dominant_component_copy":
        dominant_component_copy = cache.get("dominant_component_copy")
        if dominant_component_copy is None:
            dominant_component_copy = _infer_dominant_component_copy(task)
            cache["dominant_component_copy"] = dominant_component_copy
        if dominant_component_copy is not None:
            color, shift_x, shift_y = dominant_component_copy
            return SynthesizedSolution(
                program=make_copy_color_program(color, shift_x, shift_y),
                family="dominant_component_copy",
            )
        return None

    if family == "multi_unique_color_shift":
        multi_color_shift = cache.get("multi_unique_color_shift")
        if multi_color_shift is None:
            multi_color_shift = _infer_multi_unique_color_shift(task)
            cache["multi_unique_color_shift"] = multi_color_shift
        if multi_color_shift is not None:
            return SynthesizedSolution(
                program=make_multi_shift_color_program(multi_color_shift),
                family="multi_unique_color_shift",
            )
        return None

    if family == "upscale":
        upscale_k = cache.get("upscale")
        if upscale_k is None:
            upscale_k = _infer_upscale(task)
            cache["upscale"] = upscale_k
        if upscale_k is not None:
            return SynthesizedSolution(program=make_upscale_program(upscale_k), family="upscale")
        return None

    if family == "upscale_then_color_remap":
        upscale_corridor = cache.get("upscale_corridor", "unset")
        if upscale_corridor == "unset":
            upscale_corridor = _infer_upscale_corridor(task)
            cache["upscale_corridor"] = upscale_corridor
        if upscale_corridor is not None and not upscale_corridor.is_pure_upscale():
            mapping = upscale_corridor.materialize_color_remap()
            if mapping is not None:
                return SynthesizedSolution(
                    program=make_upscale_color_remap_program(upscale_corridor.scale_k, mapping),
                    family="upscale_then_color_remap",
                )
        return None

    if family == "upscale_color_count":
        upscale_cc = cache.get("upscale_color_count")
        if upscale_cc is None:
            upscale_cc = _infer_upscale_color_count(task)
            cache["upscale_color_count"] = upscale_cc
        if upscale_cc:
            return SynthesizedSolution(
                program=make_upscale_color_count_program(), family="upscale_color_count"
            )
        return None

    if family == "crop_bbox":
        crop_bbox = cache.get("crop_bbox")
        if crop_bbox is None:
            crop_bbox = _infer_crop_to_bbox(task)
            cache["crop_bbox"] = crop_bbox
        if crop_bbox:
            return SynthesizedSolution(program=make_crop_bbox_program(), family="crop_bbox")
        return None

    if family.startswith("crop_then_") and family != "crop_bbox":
        orient_name = cache.get("crop_then_orient")
        if orient_name is None:
            orient_name = _infer_crop_then_orient(task)
            cache["crop_then_orient"] = orient_name
        if orient_name is not None and f"crop_then_{orient_name}" == family:
            return SynthesizedSolution(
                program=make_crop_then_orient_program(orient_name), family=family
            )
        return None

    if family in {"gravity_up", "gravity_down", "gravity_left", "gravity_right"}:
        gravity_dir = cache.get("gravity")
        if gravity_dir is None:
            gravity_dir = _infer_gravity(task)
            cache["gravity"] = gravity_dir
        if gravity_dir is not None and f"gravity_{gravity_dir}" == family:
            return SynthesizedSolution(program=make_gravity_program(gravity_dir), family=family)
        return None

    if family in {"sym_complete_x", "sym_complete_y"}:
        sym_axis = cache.get("sym_complete")
        if sym_axis is None:
            sym_axis = _infer_sym_complete(task)
            cache["sym_complete"] = sym_axis
        if sym_axis is not None and f"sym_complete_{sym_axis}" == family:
            return SynthesizedSolution(program=make_sym_complete_program(sym_axis), family=family)
        return None

    if family in {"flip_x", "flip_y", "transpose", "rotate_cw", "rotate_ccw", "rotate_180"}:
        orientation = cache.get("orientation")
        if orientation is None:
            orientation = _infer_global_orientation(task)
            cache["orientation"] = orientation
        if orientation == family:
            orientation_factories = {
                "flip_x": make_flip_x_program,
                "flip_y": make_flip_y_program,
                "transpose": make_transpose_program,
                "rotate_cw": make_rotate_cw_program,
                "rotate_ccw": make_rotate_ccw_program,
                "rotate_180": make_rotate_180_program,
            }
            return SynthesizedSolution(
                program=orientation_factories[family](),
                family=family,
            )
        return None

    if family == "shift_then_color_remap":
        shift_and_mapping = cache.get("shift_then_color_remap")
        if shift_and_mapping is None:
            shift_and_mapping = _infer_shift_then_color_remap(task)
            cache["shift_then_color_remap"] = shift_and_mapping
        if shift_and_mapping is not None:
            shift_x, shift_y, shift_mapping = shift_and_mapping
            return SynthesizedSolution(
                program=make_shift_color_remap_program(shift_x, shift_y, shift_mapping),
                family="shift_then_color_remap",
            )
        return None

    if family.endswith("_then_color_remap"):
        orientation_and_mapping = cache.get("orientation_then_color_remap")
        if orientation_and_mapping is None:
            orientation_and_mapping = _infer_orientation_then_color_remap(task)
            cache["orientation_then_color_remap"] = orientation_and_mapping
        if orientation_and_mapping is None:
            return None

        orientation_name, orientation_mapping = orientation_and_mapping
        expected_family = f"{orientation_name}_then_color_remap"
        if expected_family != family:
            return None

        rotations = {"rotate_cw", "rotate_ccw", "rotate_180"}
        if orientation_name in rotations:
            return SynthesizedSolution(
                program=make_rotation_color_remap_program(orientation_name, orientation_mapping),
                family=family,
            )
        return SynthesizedSolution(
            program=make_orientation_color_remap_program(orientation_name, orientation_mapping),
            family=family,
        )

    if family == "fill_enclosed":
        candidates = cache.get("fill_enclosed_candidates")
        if candidates is None:
            strict = _infer_fill_enclosed(task)
            ordered: list[int] = []
            if strict is not None:
                ordered.append(strict)
            for color in _candidate_fill_enclosed_colors(task):
                if color not in ordered:
                    ordered.append(color)
            candidates = tuple(ordered)
            cache["fill_enclosed_candidates"] = candidates
        for fc in candidates:
            program = make_fill_enclosed_program(int(fc))
            if _program_matches_train(task, program):
                return SynthesizedSolution(program=program, family="fill_enclosed")
        return None

    if family == "paint_border":
        bc = cache.get("paint_border")
        if bc is None:
            bc = _infer_paint_border(task)
            cache["paint_border"] = bc
        if bc is not None:
            return SynthesizedSolution(program=make_paint_border_program(bc), family="paint_border")
        return None

    if family == "h_concat_flip":
        hcf = cache.get("h_concat_flip")
        if hcf is None:
            hcf = _infer_h_concat_flip(task)
            cache["h_concat_flip"] = hcf
        if hcf:
            return SynthesizedSolution(program=make_h_concat_flip_program(), family="h_concat_flip")
        return None

    if family == "v_concat_flip":
        vcf = cache.get("v_concat_flip")
        if vcf is None:
            vcf = _infer_v_concat_flip(task)
            cache["v_concat_flip"] = vcf
        if vcf:
            return SynthesizedSolution(program=make_v_concat_flip_program(), family="v_concat_flip")
        return None

    if family == "extract_panel":
        ep = cache.get("extract_panel", "unset")
        if ep == "unset":
            ep = _infer_extract_panel(task)
            cache["extract_panel"] = ep
        if ep is not None:
            rp, cp, ri, ci = ep
            return SynthesizedSolution(
                program=make_extract_panel_program(rp, cp, ri, ci), family="extract_panel"
            )
        return None

    if family == "extract_half_longer":
        ehl = cache.get("extract_half_longer")
        if ehl is None:
            ehl = _infer_extract_half_longer(task)
            cache["extract_half_longer"] = ehl
        if ehl:
            return SynthesizedSolution(
                program=make_extract_half_longer_program(), family="extract_half_longer"
            )
        return None

    if family == "select_single_color_crop":
        result = cache.get("select_single_color_crop")
        if result is None:
            result = _infer_select_single_color_crop(task)
            cache["select_single_color_crop"] = result if result else False
        if result and result is not False:
            return result
        return None

    if family == "select_single_color_crop_orient":
        result = cache.get("select_single_color_crop_orient")
        if result is None:
            result = _infer_select_single_color_crop_orient(task)
            cache["select_single_color_crop_orient"] = result if result else False
        if result and result is not False:
            return result
        return None

    if family == "select_smallest_cc_crop":
        program = StraightLineProgram(
            name="select_smallest_cc_crop",
            steps=(
                IRStep(op="select", args={"mode": "smallest_cc"}),
                IRStep(op="crop", args={}),
            ),
        )
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="select_smallest_cc_crop")
        return None

    if family == "select_second_color_crop":
        program = StraightLineProgram(
            name="select_second_color_crop",
            steps=(
                IRStep(op="select", args={"mode": "second_color"}),
                IRStep(op="crop", args={}),
            ),
        )
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="select_second_color_crop")
        return None

    if family == "mask_by_color":
        result = cache.get("mask_by_color")
        if result is None:
            result = _infer_mask_by_color(task)
            cache["mask_by_color"] = result if result else False
        if result and result is not False:
            return result
        return None

    if family == "sym_complete_180_frames":
        program = make_sym_complete_180_frames_program()
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="sym_complete_180_frames")
        return None

    if family == "template_stamp":
        # Only try if 4-cells exist in all training inputs
        if all(np.any(ex.input == 4) for ex in task.train):
            program = make_template_stamp_program()
            if _program_matches_train(task, program):
                return SynthesizedSolution(program=program, family="template_stamp")
        return None

    if family == "tile_marker_propagate":
        # Only try for same-shape tasks with tiled structure (dims = 1 + n*5)
        if all(ex.input.shape == ex.output.shape for ex in task.train):
            r, c = task.train[0].input.shape
            if (r - 1) % 5 == 0 and (c - 1) % 5 == 0 and r >= 11 and c >= 11:
                program = make_tile_marker_propagate_program()
                if _program_matches_train(task, program):
                    return SynthesizedSolution(program=program, family="tile_marker_propagate")
        return None

    if family == "diagonal_project":
        program = make_diagonal_project_program()
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="diagonal_project")
        return None

    if family == "diagonal_cross_connect":
        program = make_diagonal_cross_connect_program()
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="diagonal_cross_connect")
        return None

    if family == "marker_erase_outside":
        program = make_marker_erase_outside_program()
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="marker_erase_outside")
        return None

    if family == "panel_dihedral_complete":
        program = make_panel_dihedral_complete_program()
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="panel_dihedral_complete")
        return None

    return None


def _apply_family_precedence(ordered_families: list[str]) -> list[str]:
    """Apply narrow semantic precedence rules on top of topology ranking.

    The lattice rank is useful, but some broader families can subsume more
    specific object-level transforms. Keep those specific families ahead of
    their broader alternatives.
    """

    precedence_pairs = [
        ("dominant_component_shift", "multi_unique_color_shift"),
        ("dominant_component_copy", "multi_unique_color_shift"),
    ]

    reordered = list(ordered_families)
    for earlier, later in precedence_pairs:
        if earlier not in reordered or later not in reordered:
            continue
        earlier_idx = reordered.index(earlier)
        later_idx = reordered.index(later)
        if earlier_idx > later_idx:
            reordered.pop(earlier_idx)
            later_idx = reordered.index(later)
            reordered.insert(later_idx, earlier)
    return reordered


def _solve_bespoke_79369cc6(task: ARCTask) -> SynthesizedSolution | None:
    """Return a bespoke anchor-fill solution when the task is 79369cc6 (or matches its pattern).

    Validates on training examples before returning, so this is safe to call for any task.
    """
    from .ir import make_anchor_fill_brute_program  # noqa: PLC0415

    program = make_anchor_fill_brute_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="anchor_fill_brute")
    return None


def _solve_bespoke_e88171ec(task: ARCTask) -> SynthesizedSolution | None:
    """Largest all-zero rectangle → shrink by 1 → fill with 8."""
    program = make_largest_zero_rect_fill_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="largest_zero_rect_fill")
    return None


def _solve_bespoke_dihedral_template_match(task: ARCTask) -> SynthesizedSolution | None:
    """Find 8-template, replace dihedral matches in a single target color with 8."""
    # Auto-detect which color changes to 8 across training examples
    target_color = None
    for ex in task.train:
        inp = np.asarray(ex.input)
        out = np.asarray(ex.output)
        if inp.shape != out.shape:
            return None
        changed_to_8 = (inp != out) & (out == 8)
        if not np.any(changed_to_8):
            continue
        colors = set(int(inp[r, c]) for r, c in zip(*np.where(changed_to_8)))
        if len(colors) != 1:
            return None
        c = colors.pop()
        if target_color is None:
            target_color = c
        elif target_color != c:
            return None
    if target_color is None:
        return None
    # Must have 8s already in input
    if not np.any(np.asarray(task.train[0].input) == 8):
        return None
    program = make_dihedral_template_match_program(target_color)
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="dihedral_template_match")
    return None


def _solve_bespoke_panel_complement_fill(task: ARCTask) -> SynthesizedSolution | None:
    """Split at unique-color divider column, merge if right complements left's zeros."""
    # Quick check: first example must have a divider column
    inp0 = np.asarray(task.train[0].input)
    found = False
    for c in range(inp0.shape[1]):
        col_vals = inp0[:, c]
        if len(set(int(v) for v in col_vals)) != 1 or col_vals[0] == 0:
            continue
        div_val = int(col_vals[0])
        other = np.delete(inp0, c, axis=1)
        if div_val not in other:
            found = True
            break
    if not found:
        return None
    program = make_panel_complement_fill_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="panel_complement_fill")
    return None


def _solve_bespoke_panel_boolean_op(task: ARCTask) -> SynthesizedSolution | None:
    """Split at divider, detect AND/OR/XOR/NOR between equal panels, output single color."""
    inp0 = np.asarray(task.train[0].input)
    out0 = np.asarray(task.train[0].output)
    div = _find_divider(inp0)
    if div is None:
        return None
    div_type, div_pos, _ = div
    if div_type == "col":
        left = inp0[:, :div_pos]
        right = inp0[:, div_pos + 1 :]
    else:
        left = inp0[:div_pos, :]
        right = inp0[div_pos + 1 :, :]
    if left.shape != right.shape:
        return None
    if out0.shape != left.shape:
        return None
    # Output must be single-color (plus zero)
    out_colors = set(int(v) for v in out0.flat if v != 0)
    if len(out_colors) != 1:
        return None
    output_color = out_colors.pop()
    # Try each boolean op
    for op in ("AND", "OR", "XOR", "NOR"):
        program = make_panel_boolean_op_program(op, output_color)
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="panel_boolean_op")
    return None


def _solve_bespoke_grid_select_min_colors(task: ARCTask) -> SynthesizedSolution | None:
    """Grid-divided input: select the cell with fewest distinct non-bg colors."""
    program = make_grid_select_min_colors_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="grid_select_min_colors")
    return None


def _solve_bespoke_cc_unique_size_crop(task: ARCTask) -> SynthesizedSolution | None:
    """Foreground CCs: select the one with unique pixel count, crop bbox."""
    program = make_cc_unique_size_crop_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="cc_unique_size_crop")
    return None


def _solve_bespoke_cc_max_colors_crop(task: ARCTask) -> SynthesizedSolution | None:
    """Foreground CCs: select the one with most distinct colors, crop bbox."""
    program = make_cc_max_colors_crop_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="cc_max_colors_crop")
    return None


def _solve_bespoke_cc_min_minority_crop(task: ARCTask) -> SynthesizedSolution | None:
    """Foreground CCs: select the one with fewest non-dominant-color pixels, crop bbox."""
    program = make_cc_min_minority_crop_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="cc_min_minority_crop")
    return None


def _solve_bespoke_downscale_max(task: ARCTask) -> SynthesizedSolution | None:
    """Downscale by integer factor, each block → max value.  Fixed output size across examples."""
    target_shapes = set(ex.output.shape for ex in task.train)
    if len(target_shapes) != 1:
        return None
    (target_h, target_w) = target_shapes.pop()
    for ex in task.train:
        ih, iw = ex.input.shape
        if ih <= target_h or iw <= target_w:
            return None
        if ih % target_h != 0 or iw % target_w != 0:
            return None
    program = make_downscale_max_program(target_h, target_w)
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="downscale_max")
    return None


def _solve_bespoke_tile_by_color_count(task: ARCTask) -> SynthesizedSolution | None:
    """Tile input NxN where N = count of distinct non-bg colors."""
    for ex in task.train:
        ih, iw = ex.input.shape
        oh, ow = ex.output.shape
        if oh <= ih or ow <= iw:
            return None
        n_colors = len(set(int(v) for v in ex.input.flatten()) - {0})
        if n_colors < 1 or oh != ih * n_colors or ow != iw * n_colors:
            return None
    program = make_tile_by_color_count_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="tile_by_color_count")
    return None


def _solve_bespoke_tile_self_simple(task: ARCTask) -> SynthesizedSolution | None:
    """Tile input by (ih, iw) unconditionally."""
    for ex in task.train:
        ih, iw = ex.input.shape
        oh, ow = ex.output.shape
        if oh != ih * ih or ow != iw * iw:
            return None
    program = make_tile_self_simple_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="tile_self_simple")
    return None


def _solve_bespoke_odd_one_out_crop(task: ARCTask) -> SynthesizedSolution | None:
    """Find the shape that appears exactly once (all others paired). Crop its bounding box."""
    from scipy import ndimage
    from collections import Counter

    for ex in task.train:
        inp, out = ex.input, ex.output
        if inp.shape == out.shape:
            return None
        fg = (inp > 0).astype(int)
        labeled, n = ndimage.label(fg)
        if n < 3:
            return None
        crops = []
        for lbl in range(1, n + 1):
            mask = labeled == lbl
            rows = np.any(mask, axis=1)
            cols = np.any(mask, axis=0)
            r0, r1 = np.where(rows)[0][[0, -1]]
            c0, c1 = np.where(cols)[0][[0, -1]]
            crop = inp[r0 : r1 + 1, c0 : c1 + 1]
            crops.append(crop)
        keys = [(c.shape, c.tobytes()) for c in crops]
        counter = Counter(keys)
        singletons = [i for i, k in enumerate(keys) if counter[k] == 1]
        if len(singletons) != 1:
            return None
        if crops[singletons[0]].shape != out.shape or not np.array_equal(crops[singletons[0]], out):
            return None
    program = make_odd_one_out_crop_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="odd_one_out_crop")
    return None


def _solve_bespoke_downscale_majority(task: ARCTask) -> SynthesizedSolution | None:
    """Downscale by integer factor, each block -> majority non-bg color."""
    target_shapes = set(ex.output.shape for ex in task.train)
    if len(target_shapes) != 1:
        return None
    (target_h, target_w) = target_shapes.pop()
    for ex in task.train:
        ih, iw = ex.input.shape
        if ih <= target_h or iw <= target_w:
            return None
        if ih % target_h != 0 or iw % target_w != 0:
            return None
    program = make_downscale_majority_program(target_h, target_w)
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="downscale_majority")
    return None


def _solve_bespoke_border_repeat_edge(task: ARCTask) -> SynthesizedSolution | None:
    """Grow grid by repeating edge pixels outward N times."""
    for ex in task.train:
        ih, iw = ex.input.shape
        oh, ow = ex.output.shape
        if oh <= ih or ow <= iw:
            return None
        pad_h = (oh - ih)
        pad_w = (ow - iw)
        if pad_h % 2 != 0 or pad_w % 2 != 0:
            return None
        if pad_h != pad_w:
            return None
    pad_n = (task.train[0].output.shape[0] - task.train[0].input.shape[0]) // 2
    program = make_border_repeat_edge_program(pad_n)
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="border_repeat_edge")
    return None


def _solve_bespoke_tile_mirror_2x2_direct(task: ARCTask) -> SynthesizedSolution | None:
    """Direct bespoke check for 2x2 mirror tiling (bypasses family classifier)."""
    if _infer_tile_mirror_2x2(task):
        program = make_tile_mirror_2x2_program()
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="tile_mirror_2x2")
    return None


def _solve_bespoke_tile_rotate_2x2_direct(task: ARCTask) -> SynthesizedSolution | None:
    """Direct bespoke check for 2x2 rotational tiling (bypasses family classifier)."""
    if _infer_tile_rotate_2x2(task):
        program = make_tile_rotate_2x2_program()
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="tile_rotate_2x2")
    return None


def _solve_bespoke_tile_mirror_2x2_v2(task: ARCTask) -> SynthesizedSolution | None:
    """2x2 mirror variant: TL=inp, TR=flipud, BL=fliplr, BR=inp."""
    for ex in task.train:
        ih, iw = ex.input.shape
        oh, ow = ex.output.shape
        if oh != ih * 2 or ow != iw * 2:
            return None
    program = make_tile_mirror_2x2_v2_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="tile_mirror_2x2_v2")
    return None


def _solve_bespoke_tile_rotate_ccw_2x2(task: ARCTask) -> SynthesizedSolution | None:
    """2x2 CCW rotation: TL=inp, TR=rot90, BL=rot180, BR=rot270. Square inputs only."""
    for ex in task.train:
        ih, iw = ex.input.shape
        if ih != iw:
            return None
        oh, ow = ex.output.shape
        if oh != ih * 2 or ow != iw * 2:
            return None
    program = make_tile_rotate_ccw_2x2_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="tile_rotate_ccw_2x2")
    return None


def _solve_bespoke_invert_tile_2x2(task: ARCTask) -> SynthesizedSolution | None:
    """Swap bg/fg (single non-bg color), then tile 2x2."""
    for ex in task.train:
        ih, iw = ex.input.shape
        oh, ow = ex.output.shape
        if oh != ih * 2 or ow != iw * 2:
            return None
        colors = set(int(v) for v in ex.input.flatten()) - {0}
        if len(colors) != 1:
            return None
    program = make_invert_tile_2x2_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="invert_tile_2x2")
    return None


def _solve_bespoke_downscale_all_nonzero(task: ARCTask) -> SynthesizedSolution | None:
    """Downscale by integer factor: 0 if block has any zero, else block's color."""
    target_shapes = set(ex.output.shape for ex in task.train)
    if len(target_shapes) != 1:
        return None
    (target_h, target_w) = target_shapes.pop()
    for ex in task.train:
        ih, iw = ex.input.shape
        if ih <= target_h or iw <= target_w:
            return None
        if ih % target_h != 0 or iw % target_w != 0:
            return None
    program = make_downscale_all_nonzero_program(target_h, target_w)
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="downscale_all_nonzero")
    return None


def _solve_bespoke_color_bbox_crop(task: ARCTask) -> SynthesizedSolution | None:
    """Crop input to bounding box of a specific color. Try all colors 1-9."""
    for ex in task.train:
        if ex.input.shape == ex.output.shape:
            return None
    for color in range(1, 10):
        program = make_color_bbox_crop_program(color)
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="color_bbox_crop")
    return None


def _solve_bespoke_quadrant_extract(task: ARCTask) -> SynthesizedSolution | None:
    """Extract one quadrant of the input grid."""
    for ex in task.train:
        ih, iw = ex.input.shape
        oh, ow = ex.output.shape
        if oh >= ih or ow >= iw:
            return None
    for quadrant in ("TL", "TR", "BL", "BR"):
        program = make_quadrant_extract_program(quadrant)
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="quadrant_extract")
    return None


def _solve_bespoke_max_solid_rect_crop(task: ARCTask) -> SynthesizedSolution | None:
    """Crop largest solid rectangle of a specific color. Try all colors 1-9."""
    for ex in task.train:
        if ex.input.shape == ex.output.shape:
            return None
    for color in range(1, 10):
        program = make_max_solid_rect_crop_program(color)
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="max_solid_rect_crop")
    return None


def _solve_bespoke_checkerboard_fill(task: ARCTask) -> SynthesizedSolution | None:
    """All-zero input → grid-line checkerboard fill with 1s."""
    for ex in task.train:
        if ex.input.shape != ex.output.shape:
            return None
        if not (ex.input == 0).all():
            return None
    program = make_checkerboard_fill_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="checkerboard_fill")
    return None


def _solve_bespoke_majority_color_indicator(task: ARCTask) -> SynthesizedSolution | None:
    """Most common non-5 color above 5-divider → place at (last_row, center_col)."""
    for ex in task.train:
        if ex.input.shape != ex.output.shape:
            return None
        # Must have a row of all 5s
        has_div = False
        for r in range(ex.input.shape[0]):
            if np.all(ex.input[r, :] == 5):
                has_div = True
                break
        if not has_div:
            return None
    program = make_majority_color_indicator_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="majority_color_indicator")
    return None


def _solve_bespoke_rotate_arm_cw(task: ARCTask) -> SynthesizedSolution | None:
    """Rotate color-2 arm CW around color-5 pivot, recolor old arm to 3."""
    for ex in task.train:
        if ex.input.shape != ex.output.shape:
            return None
        # Must have exactly one color-5 pivot and some color-2 arm pixels
        if not (ex.input == 5).any() or not (ex.input == 2).any():
            return None
    program = make_rotate_arm_cw_program()
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="rotate_arm_cw")
    return None


def _solve_bespoke_bg_cluster_fill(task: ARCTask) -> SynthesizedSolution | None:
    """Fill background CCs of size >= 2 with a single fill color."""
    if not _all_same_shape(task.train):
        return None
    # Need consistent fg and fill colors across examples
    for fg_color in range(1, 10):
        for fill_color in range(1, 10):
            if fg_color == fill_color:
                continue
            program = make_bg_cluster_fill_program(fg_color, fill_color)
            if _program_matches_train(task, program):
                return SynthesizedSolution(program=program, family="bg_cluster_fill")
    return None


def _solve_bespoke_diagonal_fill(task: ARCTask) -> SynthesizedSolution | None:
    """Fill the best-fit diagonal of a bordered grid with a single color."""
    if not _all_same_shape(task.train):
        return None
    for ex in task.train:
        if ex.input.shape[0] != ex.input.shape[1]:
            return None  # must be square
    for fill_color in range(1, 10):
        program = make_diagonal_fill_program(fill_color)
        if _program_matches_train(task, program):
            return SynthesizedSolution(program=program, family="diagonal_fill")
    return None


def _solve_bespoke_local_rule_3x3(task: ARCTask) -> SynthesizedSolution | None:
    """Learn a deterministic 3x3 cellular automaton rule from training examples."""
    if not _all_same_shape(task.train):
        return None
    # Build lookup table: 3x3 neighborhood (9 ints) -> output cell value
    table: dict[tuple[int, ...], int] = {}
    for ex in task.train:
        inp = np.asarray(ex.input, dtype=np.int64)
        outp = np.asarray(ex.output, dtype=np.int64)
        h, w = inp.shape
        for r in range(h):
            for c in range(w):
                nbr: list[int] = []
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            nbr.append(int(inp[rr, cc]))
                        else:
                            nbr.append(-1)  # border padding
                key = tuple(nbr)
                val = int(outp[r, c])
                if key in table and table[key] != val:
                    return None  # inconsistent — not a simple CA
                table[key] = val
    # Only store rules where output differs from center (key[4])
    changing = [[list(k), v] for k, v in table.items() if v != k[4]]
    if not changing:
        return None  # identity transform, already handled
    program = make_local_rule_3x3_program(changing)
    if _program_matches_train(task, program):
        return SynthesizedSolution(program=program, family="local_rule_3x3")
    return None


def synthesize_program(task: ARCTask) -> SynthesizedSolution:
    # --- Phase -1: bespoke task-specific solvers (fastest, checked first) ---
    bespoke = _solve_bespoke_79369cc6(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_e88171ec(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_panel_complement_fill(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_panel_boolean_op(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_dihedral_template_match(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_grid_select_min_colors(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_cc_unique_size_crop(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_cc_max_colors_crop(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_cc_min_minority_crop(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_downscale_max(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_tile_by_color_count(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_tile_self_simple(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_odd_one_out_crop(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_downscale_majority(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_border_repeat_edge(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_tile_mirror_2x2_direct(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_tile_rotate_2x2_direct(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_tile_mirror_2x2_v2(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_tile_rotate_ccw_2x2(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_invert_tile_2x2(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_downscale_all_nonzero(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_color_bbox_crop(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_quadrant_extract(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_max_solid_rect_crop(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_checkerboard_fill(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_majority_color_indicator(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_rotate_arm_cw(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_bg_cluster_fill(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_diagonal_fill(task)
    if bespoke is not None:
        return bespoke

    bespoke = _solve_bespoke_local_rule_3x3(task)
    if bespoke is not None:
        return bespoke

    # --- Phase 0: move-algebra search (depth 1 then 2) ---
    # Import here to avoid circular dependency at module load time
    from .move_family import solve_by_move_algebra  # noqa: PLC0415

    topo_vec = task_topology(task)
    move_program = solve_by_move_algebra(task, topo_vec, top_k=12, max_depth=2)
    if move_program is not None:
        return SynthesizedSolution(program=move_program, family=move_program.name)

    # --- Phase 1: named-family inference (original strategy) ---
    ordered_families = rank_families_by_lattice(task)
    remaining = [family for family in FLAT_FAMILY_ORDER if family not in ordered_families]
    candidate_order = _apply_family_precedence(ordered_families + remaining)
    from .pressure_classifier import classify_pressure_axis, reorder_families_by_pressure  # noqa: PLC0415

    pressure_axis = classify_pressure_axis(task)
    candidate_order = reorder_families_by_pressure(candidate_order, pressure_axis)
    cache: dict[str, object] = {}

    for family in candidate_order:
        solution = _solve_family(task, family, cache)
        if solution is not None:
            return solution

    raise ValueError(
        f"Could not synthesize a restricted straight-line program for task '{task.task_id}'"
    )
