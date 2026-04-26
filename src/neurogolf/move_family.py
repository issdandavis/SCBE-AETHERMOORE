"""Rubik's cube move algebra for ARC-AGI solver.

Each primitive transform is a *move*: a typed operation with a forward function,
an optional inverse, a composition cost, a topology signature, and a ternary
direction tag.  Short move-sequences (depth 1 and 2) are searched before falling
back to the flat-family inference heuristics, using the topology lattice as a
beam prefilter.

Search strategy (hybrid):
  1. Lattice ranking narrows candidate moves to the top-k by cosine similarity.
  2. Depth-1 search: try every candidate move directly.
  3. Depth-2 search: try pairs of moves (compose_with whitelist restricts the fan).
  4. Direct family inference (existing solver._solve_family) as fallback.

This gives compositional power without exponential blowup: depth-2 over 12
candidates = 144 pairs max, which is faster than adding more named families.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from .arc_io import ARCTask
from .ir import IRStep, StraightLineProgram

# ---------------------------------------------------------------------------
# Move dataclass
# ---------------------------------------------------------------------------

Grid = np.ndarray


@dataclass(frozen=True)
class Move:
    """A single legal transform in the Rubik move algebra.

    Parameters
    ----------
    name:
        Unique identifier, matches an IR op name or compound family name.
    forward:
        Function (grid, **kwargs) -> grid.  Pure — does not modify in place.
    inverse_name:
        Name of the move that undoes this one (None = no closed-form inverse).
    cost:
        Relative search cost weight; lower = prefer in beam.  Range (0, 1].
    topology_vector:
        6D float vector (shape, motion, color, scope, topology, composition).
        Used by the lattice prefilter to rank moves against task topology.
    ternary:
        6D ternary tag {-1, 0, +1} encoding directional intent per axis.
    compose_with:
        Whitelist of move names that make sense *after* this move in depth-2
        search.  Empty = any move is allowed after this one.
    ir_steps:
        The IR steps this move maps to (used to emit a StraightLineProgram).
    """

    name: str
    forward: Callable[..., Grid]
    inverse_name: Optional[str]
    cost: float
    topology_vector: tuple[float, float, float, float, float, float]
    ternary: tuple[int, int, int, int, int, int]
    compose_with: tuple[str, ...] = field(default_factory=tuple)
    ir_steps: tuple[IRStep, ...] = field(default_factory=tuple)

    # --- helpers ---

    def apply(self, grid: Grid) -> Grid:
        return self.forward(grid)

    def as_topology(self) -> np.ndarray:
        return np.asarray(self.topology_vector, dtype=np.float64)

    def to_program(self, name_override: str | None = None) -> StraightLineProgram:
        return StraightLineProgram(
            name=name_override or self.name,
            steps=self.ir_steps,
        )


# ---------------------------------------------------------------------------
# Compound (depth-2) move
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompoundMove:
    """Two moves applied sequentially."""

    first: Move
    second: Move

    @property
    def name(self) -> str:
        return f"{self.first.name}+{self.second.name}"

    def apply(self, grid: Grid) -> Grid:
        return self.second.apply(self.first.apply(grid))

    @property
    def cost(self) -> float:
        return self.first.cost + self.second.cost

    def to_program(self) -> StraightLineProgram:
        return StraightLineProgram(
            name=self.name,
            steps=self.first.ir_steps + self.second.ir_steps,
        )


# ---------------------------------------------------------------------------
# Move registry
# ---------------------------------------------------------------------------


def _gravity(direction: str) -> Callable[[Grid], Grid]:
    def _apply(grid: Grid) -> Grid:
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

    return _apply


def _make_gravity_move(direction: str) -> Move:
    op = f"gravity_{direction}"
    inv_dir = {"up": "down", "down": "up", "left": "right", "right": "left"}[direction]
    return Move(
        name=op,
        forward=_gravity(direction),
        inverse_name=f"gravity_{inv_dir}",
        cost=0.3,
        topology_vector=(0.0, 1.0, 0.0, 0.1, 0.3, 0.0),
        ternary=(0, 1, 0, 0, 0, 0),
        compose_with=("color_remap",),
        ir_steps=(IRStep(op=op, args={}),),
    )


MOVE_REGISTRY: dict[str, Move] = {}


def _register(move: Move) -> Move:
    MOVE_REGISTRY[move.name] = move
    return move


# --- geometric moves ---

_register(
    Move(
        name="flip_x",
        forward=np.fliplr,
        inverse_name="flip_x",  # self-inverse
        cost=0.2,
        topology_vector=(0.0, 1.0, 0.0, 0.0, 0.2, 0.0),
        ternary=(0, 1, 0, 0, 0, 0),
        compose_with=("color_remap", "flip_y", "transpose"),
        ir_steps=(IRStep(op="flip_x", args={}),),
    )
)

_register(
    Move(
        name="flip_y",
        forward=np.flipud,
        inverse_name="flip_y",
        cost=0.2,
        topology_vector=(0.0, 1.0, 0.0, 0.0, 0.2, 0.0),
        ternary=(0, 1, 0, 0, 0, 0),
        compose_with=("color_remap", "flip_x", "transpose"),
        ir_steps=(IRStep(op="flip_y", args={}),),
    )
)

_register(
    Move(
        name="transpose",
        forward=lambda g: g.T,
        inverse_name="transpose",
        cost=0.2,
        topology_vector=(0.2, 1.0, 0.0, 0.0, 0.2, 0.0),
        ternary=(0, 1, 0, 0, 0, 0),
        compose_with=("flip_x", "flip_y", "color_remap"),
        ir_steps=(IRStep(op="transpose", args={}),),
    )
)

_register(
    Move(
        name="rotate_cw",
        forward=lambda g: np.fliplr(g.T),
        inverse_name="rotate_ccw",
        cost=0.3,
        topology_vector=(0.3, 1.0, 0.0, 0.0, 0.5, 0.0),
        ternary=(0, 1, 0, 0, 1, 0),
        compose_with=("color_remap", "rotate_cw"),
        ir_steps=(IRStep(op="transpose", args={}), IRStep(op="flip_x", args={})),
    )
)

_register(
    Move(
        name="rotate_ccw",
        forward=lambda g: np.flipud(g.T),
        inverse_name="rotate_cw",
        cost=0.3,
        topology_vector=(0.3, 1.0, 0.0, 0.0, 0.5, 0.0),
        ternary=(0, 1, 0, 0, 1, 0),
        compose_with=("color_remap", "rotate_ccw"),
        ir_steps=(IRStep(op="transpose", args={}), IRStep(op="flip_y", args={})),
    )
)

_register(
    Move(
        name="rotate_180",
        forward=lambda g: np.flipud(np.fliplr(g)),
        inverse_name="rotate_180",
        cost=0.3,
        topology_vector=(0.0, 1.0, 0.0, 0.0, 0.8, 0.0),
        ternary=(0, 1, 0, 0, 1, 0),
        compose_with=("color_remap",),
        ir_steps=(IRStep(op="flip_x", args={}), IRStep(op="flip_y", args={})),
    )
)

# --- scaling / tiling moves ---

_register(
    Move(
        name="crop",
        forward=lambda g: (
            g[
                int(np.where(g != 0)[0].min()) : int(np.where(g != 0)[0].max()) + 1,
                int(np.where(g != 0)[1].min()) : int(np.where(g != 0)[1].max()) + 1,
            ]
            if (g != 0).any()
            else g
        ),
        inverse_name=None,
        cost=0.4,
        topology_vector=(0.8, 0.0, 0.0, 0.9, 0.5, 0.0),
        ternary=(1, 0, 0, 1, 0, 0),
        compose_with=(
            "flip_x",
            "flip_y",
            "transpose",
            "rotate_cw",
            "rotate_ccw",
            "rotate_180",
            "tile_mirror_2x2",
            "tile_rotate_2x2",
        ),
        ir_steps=(IRStep(op="crop", args={}),),
    )
)

_register(
    Move(
        name="upscale_color_count",
        forward=lambda g: (
            np.repeat(
                np.repeat(g, max(1, len(set(int(v) for v in np.unique(g)) - {0})), axis=0),
                max(1, len(set(int(v) for v in np.unique(g)) - {0})),
                axis=1,
            )
            if len(set(int(v) for v in np.unique(g)) - {0}) >= 2
            else g
        ),
        inverse_name=None,
        cost=0.5,
        topology_vector=(1.0, 0.3, 0.5, 0.6, 0.7, 0.2),
        ternary=(1, 0, 1, 1, 1, 0),
        compose_with=(),
        ir_steps=(IRStep(op="upscale_color_count", args={}),),
    )
)

_register(
    Move(
        name="tile_mirror_2x2",
        forward=lambda g: np.concatenate(
            [
                np.concatenate([g, np.fliplr(g)], axis=1),
                np.concatenate([np.flipud(g), np.flipud(np.fliplr(g))], axis=1),
            ],
            axis=0,
        ),
        inverse_name=None,
        cost=0.6,
        topology_vector=(0.8, 1.0, 0.0, 0.9, 0.8, 0.3),
        ternary=(1, 1, 0, 1, 1, 0),
        compose_with=(),
        ir_steps=(IRStep(op="tile_mirror_2x2", args={}),),
    )
)

# --- gravity moves ---
for _dir in ("up", "down", "left", "right"):
    _register(_make_gravity_move(_dir))

# --- symmetry completion moves ---

_register(
    Move(
        name="sym_complete_x",
        forward=lambda g: np.where(g != 0, g, np.fliplr(g)),
        inverse_name=None,
        cost=0.4,
        topology_vector=(0.0, 1.0, 0.0, 0.0, 0.5, 0.4),
        ternary=(0, 1, 0, 0, 1, 1),
        compose_with=("color_remap",),
        ir_steps=(IRStep(op="sym_complete_x", args={}),),
    )
)

_register(
    Move(
        name="sym_complete_y",
        forward=lambda g: np.where(g != 0, g, np.flipud(g)),
        inverse_name=None,
        cost=0.4,
        topology_vector=(0.0, 1.0, 0.0, 0.0, 0.5, 0.4),
        ternary=(0, 1, 0, 0, 1, 1),
        compose_with=("color_remap",),
        ir_steps=(IRStep(op="sym_complete_y", args={}),),
    )
)

# --- panel-aware symmetry completion moves ---


def _find_separator_rows(grid: Grid) -> list[int]:
    """Find rows that are entirely one non-zero color (panel separators)."""
    seps = []
    h, w = grid.shape
    for r in range(h):
        row = grid[r, :]
        uniq = np.unique(row)
        if len(uniq) == 1 and uniq[0] != 0:
            seps.append(r)
    return seps


def _find_separator_cols(grid: Grid) -> list[int]:
    """Find columns that are entirely one non-zero color (panel separators)."""
    seps = []
    h, w = grid.shape
    for c in range(w):
        col = grid[:, c]
        uniq = np.unique(col)
        if len(uniq) == 1 and uniq[0] != 0:
            seps.append(c)
    return seps


def _panel_sym_complete_x(grid: Grid) -> Grid:
    """Symmetry-complete each panel (split by separator columns) along x-axis."""
    sep_cols = _find_separator_cols(grid)
    if not sep_cols:
        return np.where(grid != 0, grid, np.fliplr(grid))
    h, w = grid.shape
    out = grid.copy()
    boundaries = [0] + sep_cols + [w]
    for i in range(len(boundaries) - 1):
        c0, c1 = boundaries[i], boundaries[i + 1]
        if c0 in sep_cols:
            c0 += 1
        if c0 >= c1:
            continue
        panel = grid[:, c0:c1]
        filled = np.where(panel != 0, panel, np.fliplr(panel))
        out[:, c0:c1] = filled
    return out


def _panel_sym_complete_y(grid: Grid) -> Grid:
    """Symmetry-complete each panel (split by separator rows) along y-axis."""
    sep_rows = _find_separator_rows(grid)
    if not sep_rows:
        return np.where(grid != 0, grid, np.flipud(grid))
    h, w = grid.shape
    out = grid.copy()
    boundaries = [0] + sep_rows + [h]
    for i in range(len(boundaries) - 1):
        r0, r1 = boundaries[i], boundaries[i + 1]
        if r0 in sep_rows:
            r0 += 1
        if r0 >= r1:
            continue
        panel = grid[r0:r1, :]
        filled = np.where(panel != 0, panel, np.flipud(panel))
        out[r0:r1, :] = filled
    return out


_register(
    Move(
        name="panel_sym_complete_x",
        forward=_panel_sym_complete_x,
        inverse_name=None,
        cost=0.45,
        topology_vector=(0.0, 1.0, 0.3, 0.0, 0.6, 0.5),
        ternary=(0, 1, 0, 0, 1, 1),
        compose_with=("color_remap",),
        ir_steps=(IRStep(op="panel_sym_complete_x", args={}),),
    )
)

_register(
    Move(
        name="panel_sym_complete_y",
        forward=_panel_sym_complete_y,
        inverse_name=None,
        cost=0.45,
        topology_vector=(0.0, 1.0, 0.3, 0.0, 0.6, 0.5),
        ternary=(0, 1, 0, 0, 1, 1),
        compose_with=("color_remap",),
        ir_steps=(IRStep(op="panel_sym_complete_y", args={}),),
    )
)

# --- object selection moves ---
# All select moves are destructive masks: non-selected pixels become 0.
# This preserves single-array pipeline threading without a register model.


def _select_dominant_color(grid: Grid) -> Grid:
    """Keep only the most common non-zero color; zero the rest."""
    colors, counts = np.unique(grid[grid != 0], return_counts=True)
    if len(colors) == 0:
        return grid
    dominant = int(colors[np.argmax(counts)])
    return np.where(grid == dominant, grid, 0)


def _select_largest_cc(grid: Grid) -> Grid:
    """Keep only the largest connected component (by pixel count); zero the rest."""
    from .components import connected_components

    _, components = connected_components(grid, background=0, connectivity=4)
    if not components:
        return grid
    largest = max(components, key=lambda c: c.area)
    # Rebuild label map to isolate largest component
    _, all_comps = connected_components(grid, background=0, connectivity=4)
    label_map, _ = connected_components(grid, background=0, connectivity=4)
    out = np.zeros_like(grid)
    out[label_map == largest.label] = grid[label_map == largest.label]
    return out


def _select_minority_color(grid: Grid) -> Grid:
    """Keep only the least common non-zero color; zero the rest (often the marker)."""
    colors, counts = np.unique(grid[grid != 0], return_counts=True)
    if len(colors) == 0:
        return grid
    minority = int(colors[np.argmin(counts)])
    return np.where(grid == minority, grid, 0)


_register(
    Move(
        name="select_dominant_color",
        forward=_select_dominant_color,
        inverse_name=None,
        cost=0.5,
        topology_vector=(0.0, 0.0, 1.0, 0.7, 0.3, 0.0),
        ternary=(0, 0, 1, 1, 0, 0),
        compose_with=(
            "crop",
            "flip_x",
            "flip_y",
            "transpose",
            "rotate_cw",
            "rotate_ccw",
            "rotate_180",
            "gravity_up",
            "gravity_down",
            "gravity_left",
            "gravity_right",
            "paste_center",
            "paste_tile",
            "paste_stamp",
        ),
        ir_steps=(IRStep(op="select", args={"mode": "dominant_color"}),),
    )
)

_register(
    Move(
        name="select_largest_cc",
        forward=_select_largest_cc,
        inverse_name=None,
        cost=0.6,
        topology_vector=(0.5, 0.0, 0.5, 0.9, 0.4, 0.0),
        ternary=(1, 0, 1, 1, 0, 0),
        compose_with=(
            "crop",
            "flip_x",
            "flip_y",
            "transpose",
            "rotate_cw",
            "rotate_ccw",
            "rotate_180",
            "gravity_up",
            "gravity_down",
            "gravity_left",
            "gravity_right",
            "paste_center",
            "paste_tile",
            "paste_stamp",
        ),
        ir_steps=(IRStep(op="select", args={"mode": "largest_cc"}),),
    )
)

_register(
    Move(
        name="select_minority_color",
        forward=_select_minority_color,
        inverse_name=None,
        cost=0.5,
        topology_vector=(0.0, 0.0, 1.0, 0.6, 0.2, 0.0),
        ternary=(0, 0, 1, 1, 0, 0),
        compose_with=(
            "crop",
            "flip_x",
            "flip_y",
            "transpose",
            "rotate_cw",
            "rotate_ccw",
            "rotate_180",
            "gravity_up",
            "gravity_down",
            "gravity_left",
            "gravity_right",
            "paste_center",
            "paste_tile",
            "paste_stamp",
        ),
        ir_steps=(IRStep(op="select", args={"mode": "minority_color"}),),
    )
)


def _select_smallest_cc(grid: Grid) -> Grid:
    """Keep only the smallest connected component (by pixel count); zero the rest."""
    from .components import connected_components

    label_map, components = connected_components(grid, background=0, connectivity=4)
    if not components:
        return grid
    smallest = min(components, key=lambda c: c.area)
    out = np.zeros_like(grid)
    out[label_map == smallest.label] = grid[label_map == smallest.label]
    return out


def _select_second_color(grid: Grid) -> Grid:
    """Keep only the second most common non-zero color; zero the rest."""
    colors, counts = np.unique(grid[grid != 0], return_counts=True)
    if len(colors) < 2:
        return grid
    order = np.argsort(-counts)
    second = int(colors[order[1]])
    return np.where(grid == second, grid, 0)


def _foreground_objects(grid: Grid) -> tuple[np.ndarray, list[tuple[int, tuple[int, int, int, int]]]]:
    """Label 4-connected foreground objects regardless of color.

    Returns a label map plus a list of `(label, bbox)` entries where `bbox` is
    `(row_min, row_max, col_min, col_max)`.
    """
    h, w = grid.shape
    labels = np.zeros((h, w), dtype=np.int64)
    objects: list[tuple[int, tuple[int, int, int, int]]] = []
    next_label = 1

    for row in range(h):
        for col in range(w):
            if int(grid[row, col]) == 0 or labels[row, col] != 0:
                continue
            stack = [(row, col)]
            labels[row, col] = next_label
            coords: list[tuple[int, int]] = []
            while stack:
                rr, cc = stack.pop()
                coords.append((rr, cc))
                for nr, nc in ((rr - 1, cc), (rr + 1, cc), (rr, cc - 1), (rr, cc + 1)):
                    if 0 <= nr < h and 0 <= nc < w and int(grid[nr, nc]) != 0 and labels[nr, nc] == 0:
                        labels[nr, nc] = next_label
                        stack.append((nr, nc))
            rows = [r for r, _ in coords]
            cols = [c for _, c in coords]
            objects.append((next_label, (min(rows), max(rows), min(cols), max(cols))))
            next_label += 1

    return labels, objects


def _select_unique_object(grid: Grid) -> Grid:
    """Keep only the one foreground object whose cropped pattern is unique.

    Foreground objects are 4-connected regions over `grid != 0`, preserving
    original colors inside each object's bounding box. If there is not exactly
    one unique pattern, this selector leaves the grid unchanged.
    """
    label_map, objects = _foreground_objects(grid)
    if not objects:
        return grid

    signatures: dict[tuple[tuple[int, int], bytes], list[int]] = {}
    for label, (r0, r1, c0, c1) in objects:
        patch = grid[r0 : r1 + 1, c0 : c1 + 1]
        key = (patch.shape, patch.astype(np.int64, copy=False).tobytes())
        signatures.setdefault(key, []).append(label)

    unique_labels = [labels[0] for labels in signatures.values() if len(labels) == 1]
    if len(unique_labels) != 1:
        return grid

    out = np.zeros_like(grid)
    out[label_map == unique_labels[0]] = grid[label_map == unique_labels[0]]
    return out


_register(
    Move(
        name="select_smallest_cc",
        forward=_select_smallest_cc,
        inverse_name=None,
        cost=0.6,
        topology_vector=(0.5, 0.0, 0.5, 0.9, 0.4, 0.0),
        ternary=(1, 0, 1, 1, 0, 0),
        compose_with=(
            "crop",
            "flip_x",
            "flip_y",
            "transpose",
            "rotate_cw",
            "rotate_ccw",
            "rotate_180",
            "gravity_up",
            "gravity_down",
            "gravity_left",
            "gravity_right",
            "paste_center",
            "paste_tile",
            "paste_stamp",
        ),
        ir_steps=(IRStep(op="select", args={"mode": "smallest_cc"}),),
    )
)

_register(
    Move(
        name="select_second_color",
        forward=_select_second_color,
        inverse_name=None,
        cost=0.5,
        topology_vector=(0.0, 0.0, 1.0, 0.6, 0.3, 0.0),
        ternary=(0, 0, 1, 1, 0, 0),
        compose_with=(
            "crop",
            "flip_x",
            "flip_y",
            "transpose",
            "rotate_cw",
            "rotate_ccw",
            "rotate_180",
            "gravity_up",
            "gravity_down",
            "gravity_left",
            "gravity_right",
            "paste_center",
            "paste_tile",
            "paste_stamp",
        ),
        ir_steps=(IRStep(op="select", args={"mode": "second_color"}),),
    )
)

_register(
    Move(
        name="select_unique_object",
        forward=_select_unique_object,
        inverse_name=None,
        cost=0.7,
        topology_vector=(0.7, 0.0, 0.2, 1.0, 0.5, 0.0),
        ternary=(1, 0, 0, 1, 0, 0),
        compose_with=("crop", "flip_x", "flip_y", "transpose", "rotate_cw", "rotate_ccw", "rotate_180"),
        ir_steps=(IRStep(op="select", args={"mode": "unique_object"}),),
    )
)


# ---------------------------------------------------------------------------
# Pivot rotation moves (rotate 180 around a unique-color pixel)
# ---------------------------------------------------------------------------


def _rotate_180_around_pivot(grid: Grid, pivot_color: int) -> Grid:
    """Rotate grid content 180 degrees around the unique pixel of *pivot_color*.

    Raises ValueError when *pivot_color* does not appear exactly once so the
    solver records a non-match for this example.
    """
    locs = np.argwhere(grid == pivot_color)
    if len(locs) != 1:
        raise ValueError(f"color {pivot_color} appears {len(locs)} times, need exactly 1")
    pr, pc = int(locs[0, 0]), int(locs[0, 1])
    H, W = grid.shape
    out = np.zeros_like(grid)
    for r in range(H):
        for c in range(W):
            if grid[r, c] != 0:
                nr, nc = 2 * pr - r, 2 * pc - c
                if 0 <= nr < H and 0 <= nc < W:
                    out[nr, nc] = grid[r, c]
                else:
                    raise ValueError("rotated pixel out of bounds")
    return out


for _pc in range(1, 10):
    _register(
        Move(
            name=f"rotate_180_pivot_{_pc}",
            forward=(lambda c: lambda g: _rotate_180_around_pivot(g, c))(_pc),
            inverse_name=None,
            cost=0.5,
            topology_vector=(0.0, 0.0, 0.8, 0.0, 0.5, 0.0),
            ternary=(0, 0, 1, 0, 1, 0),
            compose_with=("crop",),
            ir_steps=(IRStep(op="rotate_180_pivot", args={"color": _pc}),),
        )
    )


# ---------------------------------------------------------------------------
# Paste primitives
# ---------------------------------------------------------------------------
# Paste operates on the CURRENT grid's coordinate space.  Because select uses
# a destructive mask (non-selected pixels → 0), the canvas size is preserved
# through select.  Paste then repositions or replicates the non-zero content
# within that same canvas.  This makes select+paste chains natural: the canvas
# stays the same size while the content moves.


def _paste_center(grid: Grid) -> Grid:
    """Center non-zero bbox content on a blank canvas of the same shape."""
    rows, cols = np.where(grid != 0)
    if len(rows) == 0:
        return grid
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    c0, c1 = int(cols.min()), int(cols.max()) + 1
    content = grid[r0:r1, c0:c1]
    h, w = grid.shape
    ch, cw = content.shape
    if ch == h and cw == w:
        return grid  # already fills canvas
    out = np.zeros_like(grid)
    top = (h - ch) // 2
    left = (w - cw) // 2
    out[top : top + ch, left : left + cw] = content
    return out


def _paste_tile(grid: Grid) -> Grid:
    """Tile the non-zero bounding box to fill the full canvas."""
    rows, cols = np.where(grid != 0)
    if len(rows) == 0:
        return grid
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    c0, c1 = int(cols.min()), int(cols.max()) + 1
    tile = grid[r0:r1, c0:c1]
    h, w = grid.shape
    th, tw = tile.shape
    if th == 0 or tw == 0:
        return grid
    reps_h = (h + th - 1) // th
    reps_w = (w + tw - 1) // tw
    tiled = np.tile(tile, (reps_h, reps_w))
    return tiled[:h, :w]


def _paste_stamp(grid: Grid) -> Grid:
    """Stamp the non-zero bbox at every cell of a regular grid implied by
    the background color.  Background positions are cells that are 0 AND
    adjacent to at least one non-zero cell (i.e. 'holes').  Falls back to
    paste_center when no clear stamp grid is detectable."""
    # Detect period: smallest repeat unit in row and column of non-zero content
    rows, cols = np.where(grid != 0)
    if len(rows) == 0:
        return grid
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    c0, c1 = int(cols.min()), int(cols.max()) + 1
    stamp = grid[r0:r1, c0:c1]
    h, w = grid.shape
    sh, sw = stamp.shape
    # Infer step: find next non-zero row/col block after the first one
    row_gaps = np.diff(np.where(np.any(grid != 0, axis=1))[0])
    col_gaps = np.diff(np.where(np.any(grid != 0, axis=0))[0])
    step_r = int(np.median(row_gaps)) if len(row_gaps) > 0 else sh
    step_c = int(np.median(col_gaps)) if len(col_gaps) > 0 else sw
    step_r = max(step_r, sh)
    step_c = max(step_c, sw)
    out = np.zeros_like(grid)
    for top in range(0, h, step_r):
        for left in range(0, w, step_c):
            br = min(top + sh, h)
            bc = min(left + sw, w)
            out[top:br, left:bc] = stamp[: br - top, : bc - left]
    return out


_register(
    Move(
        name="paste_center",
        forward=_paste_center,
        inverse_name=None,
        cost=0.5,
        topology_vector=(0.5, 0.5, 0.0, 0.9, 0.3, 0.7),
        ternary=(1, 1, 0, 1, 0, 1),
        compose_with=("color_remap",),
        ir_steps=(IRStep(op="paste", args={"mode": "center"}),),
    )
)

_register(
    Move(
        name="paste_tile",
        forward=_paste_tile,
        inverse_name=None,
        cost=0.6,
        topology_vector=(0.8, 0.2, 0.0, 0.7, 0.9, 0.8),
        ternary=(1, 0, 0, 1, 1, 1),
        compose_with=("color_remap",),
        ir_steps=(IRStep(op="paste", args={"mode": "tile"}),),
    )
)

_register(
    Move(
        name="paste_stamp",
        forward=_paste_stamp,
        inverse_name=None,
        cost=0.7,
        topology_vector=(0.6, 0.3, 0.0, 0.8, 0.8, 0.9),
        ternary=(1, 0, 0, 1, 1, 1),
        compose_with=("color_remap",),
        ir_steps=(IRStep(op="paste", args={"mode": "stamp"}),),
    )
)


# ---------------------------------------------------------------------------
# Lattice prefilter
# ---------------------------------------------------------------------------


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-9:
        return 0.0
    return float(np.dot(a, b)) / denom


def prefilter_moves(
    task_topology_vec: np.ndarray,
    top_k: int = 10,
    forced_move_names: tuple[str, ...] = (),
) -> list[Move]:
    """Return top-k moves ranked by cosine similarity to the task topology vector."""
    scored = [(move, _cosine(task_topology_vec, move.as_topology()) / move.cost) for move in MOVE_REGISTRY.values()]
    scored.sort(key=lambda x: -x[1])
    selected = [move for move, _ in scored[:top_k]]
    seen = {move.name for move in selected}
    for name in forced_move_names:
        move = MOVE_REGISTRY.get(name)
        if move is not None and move.name not in seen:
            selected.append(move)
            seen.add(move.name)
    return selected


def _task_is_shrink_like(task: ARCTask) -> bool:
    """Return True when outputs consistently shrink relative to inputs."""
    strict_smaller = False
    for example in task.train:
        ih, iw = example.input.shape
        oh, ow = example.output.shape
        if oh > ih or ow > iw:
            return False
        if oh < ih or ow < iw:
            strict_smaller = True
    return strict_smaller


def _task_has_pivot_candidate(task: ARCTask) -> list[str]:
    """Return pivot move names for colors that appear exactly once in ALL training inputs."""
    if not task.train:
        return []
    singleton_colors: set[int] | None = None
    for ex in task.train:
        grid = ex.input
        colors, counts = np.unique(grid[grid != 0], return_counts=True)
        singles = {int(c) for c, n in zip(colors, counts) if n == 1}
        singleton_colors = singles if singleton_colors is None else singleton_colors & singles
    if not singleton_colors:
        return []
    return [f"rotate_180_pivot_{c}" for c in sorted(singleton_colors) if 1 <= c <= 9]


# ---------------------------------------------------------------------------
# Move-sequence search
# ---------------------------------------------------------------------------


def _all_examples_match(task: ARCTask, candidate: Grid, example_idx: int = -1) -> bool:
    """Check is not needed at the task level — we check per-example and aggregate."""
    return True


def search_depth1(
    task: ARCTask,
    candidates: list[Move],
) -> Optional[StraightLineProgram]:
    """Try each move on every training example; return program if all match."""
    for move in sorted(candidates, key=lambda m: m.cost):
        matched = True
        for ex in task.train:
            try:
                predicted = move.apply(ex.input)
            except Exception:
                matched = False
                break
            if not np.array_equal(predicted, ex.output):
                matched = False
                break
        if matched:
            return move.to_program()
    return None


def search_depth2(
    task: ARCTask,
    candidates: list[Move],
) -> Optional[StraightLineProgram]:
    """Try depth-2 move pairs (first.compose_with restricts fan-out)."""
    move_map = MOVE_REGISTRY

    for first in sorted(candidates, key=lambda m: m.cost):
        allowed_seconds = first.compose_with or tuple(move_map.keys())
        for second_name in allowed_seconds:
            second = move_map.get(second_name)
            if second is None:
                continue
            compound = CompoundMove(first=first, second=second)
            matched = True
            for ex in task.train:
                try:
                    predicted = compound.apply(ex.input)
                except Exception:
                    matched = False
                    break
                if not np.array_equal(predicted, ex.output):
                    matched = False
                    break
            if matched:
                return compound.to_program()
    return None


def solve_by_move_algebra(
    task: ARCTask,
    task_topology_vec: np.ndarray,
    top_k: int = 12,
    max_depth: int = 2,
) -> Optional[StraightLineProgram]:
    """Main entry point for the move-algebra search.

    Returns a StraightLineProgram if a solution is found, else None.

    The program name will be the composed move name (e.g. "crop+flip_x").
    The steps are already in IR format and can be executed directly.
    """
    forced_move_names: tuple[str, ...] = ("crop",)
    if _task_is_shrink_like(task):
        forced_move_names = (
            "select_dominant_color",
            "select_largest_cc",
            "select_minority_color",
            "select_smallest_cc",
            "select_second_color",
            "select_unique_object",
            "crop",
        )

    pivot_names = _task_has_pivot_candidate(task)
    if pivot_names:
        forced_move_names = forced_move_names + tuple(pivot_names)

    candidates = prefilter_moves(task_topology_vec, top_k=top_k, forced_move_names=forced_move_names)

    program = search_depth1(task, candidates)
    if program is not None:
        return program

    if max_depth >= 2:
        program = search_depth2(task, candidates)
        if program is not None:
            return program

    return None


# ---------------------------------------------------------------------------
# Move group properties (for analysis / future depth-3+)
# ---------------------------------------------------------------------------


def get_inverse(move_name: str) -> Optional[Move]:
    """Return the inverse move if it exists in the registry."""
    move = MOVE_REGISTRY.get(move_name)
    if move is None or move.inverse_name is None:
        return None
    return MOVE_REGISTRY.get(move.inverse_name)


def move_distance(name_a: str, name_b: str) -> float:
    """Topology-space distance between two moves (cosine distance)."""
    a = MOVE_REGISTRY.get(name_a)
    b = MOVE_REGISTRY.get(name_b)
    if a is None or b is None:
        return 1.0
    return 1.0 - _cosine(a.as_topology(), b.as_topology())


def canonicalize_sequence(names: list[str]) -> list[str]:
    """Apply obvious algebraic reductions to a move sequence.

    Rules:
      - M followed by M^{-1} → remove both (identity)
      - self-inverse M followed by M → remove both
    """
    result = list(names)
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(result) - 1:
            a, b = result[i], result[i + 1]
            move_a = MOVE_REGISTRY.get(a)
            if move_a is not None and move_a.inverse_name == b:
                result.pop(i)
                result.pop(i)
                changed = True
            else:
                i += 1
    return result
