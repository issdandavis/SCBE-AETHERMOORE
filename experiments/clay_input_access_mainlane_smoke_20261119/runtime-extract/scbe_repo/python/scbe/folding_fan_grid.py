"""Folding-fan grid: custom cell relationships across fan shapes.

A *folding fan* is a hinge with blades (angular sectors) and rings (radial
depth). Cells sit at (blade, ring[, slot]). Built-in shapes:

  - semicircle      half-disk of blades
  - full_circle     closed circular fan
  - accordion       mountain/valley linear fold fan (parallel creases)
  - nested_rings    concentric fan shells around one hinge
  - half_board      mirror half-board (Connect-X style fold reuse)
  - sector_grid     rectangular blade x ring lattice (plain polar grid)
  - multi_hinge     several fans sharing hinge cells as a graph

Default edges: adjacent_blade, adjacent_ring, fold_mirror, same_ray,
hinge_shared. Call ``add_relation`` for any custom relation kinds/weights.

This is geometry + relation graph only — not a game engine. Connect-X can map
its windows onto a HalfBoardMirrorFan; origami accordion creases map onto
AccordionFan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Set, Tuple

import math


class RelationKind(str, Enum):
    """Named edge kinds. CUSTOM is free-form; use ``meta['name']`` to subtype."""

    ADJACENT_BLADE = "adjacent_blade"
    ADJACENT_RING = "adjacent_ring"
    FOLD_MIRROR = "fold_mirror"
    SAME_RAY = "same_ray"
    HINGE_SHARED = "hinge_shared"
    DIAGONAL = "diagonal"
    CUSTOM = "custom"


@dataclass(frozen=True, order=True)
class FanCell:
    """One cell in a folding-fan coordinate system.

    ``blade`` — angular index around the hinge (0 .. blades-1)
    ``ring``  — radial depth from the hinge (0 is nearest the hinge)
    ``slot``  — optional subdivision along the blade arc
    ``hinge`` — multi-hinge fans place cells on different hinges
    """

    blade: int
    ring: int
    slot: int = 0
    hinge: int = 0

    def key(self) -> Tuple[int, int, int, int]:
        return (self.hinge, self.blade, self.ring, self.slot)

    def label(self) -> str:
        base = f"b{self.blade}r{self.ring}"
        if self.slot:
            base += f"s{self.slot}"
        if self.hinge:
            base = f"h{self.hinge}." + base
        return base


@dataclass(frozen=True)
class CellEdge:
    """Undirected relation between two cells (stored once, queried both ways)."""

    a: FanCell
    b: FanCell
    kind: RelationKind
    weight: float = 1.0
    meta: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.a == self.b:
            raise ValueError("self-loop edges are not allowed")
        # canonicalize endpoint order for undirected equality
        if self.a.key() > self.b.key():
            left, right = self.b, self.a
            object.__setattr__(self, "a", left)
            object.__setattr__(self, "b", right)
        if not math.isfinite(self.weight):
            raise ValueError("weight must be finite")

    def other(self, cell: FanCell) -> FanCell:
        if cell == self.a:
            return self.b
        if cell == self.b:
            return self.a
        raise KeyError(f"{cell.label()} not on edge")

    def touches(self, cell: FanCell) -> bool:
        return cell == self.a or cell == self.b


# ---------------------------------------------------------------------------
# Shape generators
# ---------------------------------------------------------------------------


def _sector_cells(
    blades: int,
    rings: int,
    *,
    slots: int = 1,
    hinge: int = 0,
) -> List[FanCell]:
    if blades < 1 or rings < 1 or slots < 1:
        raise ValueError("blades, rings, and slots must be >= 1")
    cells: List[FanCell] = []
    for blade in range(blades):
        for ring in range(rings):
            for slot in range(slots):
                cells.append(FanCell(blade=blade, ring=ring, slot=slot, hinge=hinge))
    return cells


def _adjacent_blade_edges(
    cells: Sequence[FanCell],
    blades: int,
    *,
    wrap: bool,
) -> List[CellEdge]:
    by_key = {(c.blade, c.ring, c.slot, c.hinge): c for c in cells}
    edges: List[CellEdge] = []
    for c in cells:
        nxt = (c.blade + 1) % blades if wrap else c.blade + 1
        if not wrap and nxt >= blades:
            continue
        partner = by_key.get((nxt, c.ring, c.slot, c.hinge))
        if partner is not None:
            edges.append(CellEdge(c, partner, RelationKind.ADJACENT_BLADE))
    return edges


def _adjacent_ring_edges(cells: Sequence[FanCell]) -> List[CellEdge]:
    by_key = {(c.blade, c.ring, c.slot, c.hinge): c for c in cells}
    edges: List[CellEdge] = []
    for c in cells:
        partner = by_key.get((c.blade, c.ring + 1, c.slot, c.hinge))
        if partner is not None:
            edges.append(CellEdge(c, partner, RelationKind.ADJACENT_RING))
            edges.append(
                CellEdge(c, partner, RelationKind.SAME_RAY, weight=1.0, meta={"ray": c.blade})
            )
    return edges


def _diagonal_edges(cells: Sequence[FanCell], blades: int, *, wrap: bool) -> List[CellEdge]:
    by_key = {(c.blade, c.ring, c.slot, c.hinge): c for c in cells}
    edges: List[CellEdge] = []
    for c in cells:
        for db in (-1, 1):
            b2 = c.blade + db
            if wrap:
                b2 %= blades
            elif b2 < 0 or b2 >= blades:
                continue
            partner = by_key.get((b2, c.ring + 1, c.slot, c.hinge))
            if partner is not None:
                edges.append(CellEdge(c, partner, RelationKind.DIAGONAL, weight=0.5))
    return edges


def _mirror_edges(cells: Sequence[FanCell], blades: int) -> List[CellEdge]:
    """Pair blade i with blade (blades-1-i) at the same ring/slot (fold crease)."""
    by_key = {(c.blade, c.ring, c.slot, c.hinge): c for c in cells}
    edges: List[CellEdge] = []
    seen: Set[Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]] = set()
    for c in cells:
        mirror_blade = blades - 1 - c.blade
        if mirror_blade == c.blade:
            continue  # on the fold crease itself
        partner = by_key.get((mirror_blade, c.ring, c.slot, c.hinge))
        if partner is None:
            continue
        pair = tuple(sorted((c.key(), partner.key())))
        if pair in seen:
            continue
        seen.add(pair)
        edges.append(
            CellEdge(
                c,
                partner,
                RelationKind.FOLD_MIRROR,
                weight=1.0,
                meta={"crease": "blade_mirror"},
            )
        )
    return edges


def _hinge_edges(cells: Sequence[FanCell]) -> List[CellEdge]:
    """Ring-0 cells share the hinge — fully connect them as HINGE_SHARED."""
    hinges: Dict[int, List[FanCell]] = {}
    for c in cells:
        if c.ring == 0:
            hinges.setdefault(c.hinge, []).append(c)
    edges: List[CellEdge] = []
    for group in hinges.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                edges.append(CellEdge(a, b, RelationKind.HINGE_SHARED, weight=1.0))
    return edges


@dataclass(frozen=True)
class FanShapeSpec:
    """Declarative shape: cells + default edges."""

    name: str
    blades: int
    rings: int
    slots: int = 1
    wrap_blades: bool = False
    mirror: bool = False
    diagonals: bool = False
    hinge_links: bool = True
    hinges: int = 1

    def build_cells(self) -> List[FanCell]:
        cells: List[FanCell] = []
        for h in range(self.hinges):
            cells.extend(
                _sector_cells(self.blades, self.rings, slots=self.slots, hinge=h)
            )
        return cells

    def build_default_edges(self, cells: Sequence[FanCell]) -> List[CellEdge]:
        edges: List[CellEdge] = []
        # per-hinge topology
        for h in range(self.hinges):
            subset = [c for c in cells if c.hinge == h]
            edges.extend(_adjacent_blade_edges(subset, self.blades, wrap=self.wrap_blades))
            edges.extend(_adjacent_ring_edges(subset))
            if self.mirror:
                edges.extend(_mirror_edges(subset, self.blades))
            if self.diagonals:
                edges.extend(_diagonal_edges(subset, self.blades, wrap=self.wrap_blades))
            if self.hinge_links:
                edges.extend(_hinge_edges(subset))
        # multi-hinge: link same (blade,ring,slot) across adjacent hinges
        if self.hinges > 1:
            by = {(c.hinge, c.blade, c.ring, c.slot): c for c in cells}
            for h in range(self.hinges - 1):
                for c in cells:
                    if c.hinge != h:
                        continue
                    partner = by.get((h + 1, c.blade, c.ring, c.slot))
                    if partner is not None:
                        edges.append(
                            CellEdge(
                                c,
                                partner,
                                RelationKind.CUSTOM,
                                weight=1.0,
                                meta={"name": "hinge_chain"},
                            )
                        )
        return edges


# Catalog of named folding-fan shapes
FAN_SHAPES: Dict[str, FanShapeSpec] = {
    "semicircle": FanShapeSpec(
        name="semicircle",
        blades=8,
        rings=4,
        wrap_blades=False,
        mirror=True,
        diagonals=True,
        hinge_links=True,
    ),
    "full_circle": FanShapeSpec(
        name="full_circle",
        blades=12,
        rings=3,
        wrap_blades=True,
        mirror=True,
        diagonals=True,
        hinge_links=True,
    ),
    "accordion": FanShapeSpec(
        name="accordion",
        blades=1,  # one long strip; blades re-used as fold panels via slots=1, rings=fold count
        rings=8,
        wrap_blades=False,
        mirror=False,
        diagonals=False,
        hinge_links=False,
    ),
    "nested_rings": FanShapeSpec(
        name="nested_rings",
        blades=6,
        rings=5,
        wrap_blades=True,
        mirror=False,
        diagonals=False,
        hinge_links=True,
    ),
    "half_board": FanShapeSpec(
        name="half_board",
        blades=7,  # Connect-X columns as blades
        rings=6,  # rows as rings from bottom hinge
        wrap_blades=False,
        mirror=True,
        diagonals=True,
        hinge_links=False,
    ),
    "sector_grid": FanShapeSpec(
        name="sector_grid",
        blades=5,
        rings=5,
        slots=1,
        wrap_blades=False,
        mirror=False,
        diagonals=True,
        hinge_links=True,
    ),
    "multi_hinge": FanShapeSpec(
        name="multi_hinge",
        blades=4,
        rings=3,
        wrap_blades=False,
        mirror=True,
        diagonals=False,
        hinge_links=True,
        hinges=3,
    ),
}


def list_fan_shapes() -> Tuple[str, ...]:
    return tuple(sorted(FAN_SHAPES))


# ---------------------------------------------------------------------------
# Grid system
# ---------------------------------------------------------------------------


class FoldingFanGrid:
    """Relational grid over one folding-fan shape, plus custom cell relationships."""

    def __init__(
        self,
        shape: str | FanShapeSpec = "semicircle",
        *,
        blades: int | None = None,
        rings: int | None = None,
        slots: int | None = None,
    ) -> None:
        if isinstance(shape, FanShapeSpec):
            spec = shape
        else:
            if shape not in FAN_SHAPES:
                raise KeyError(
                    f"unknown fan shape {shape!r}; known: {', '.join(list_fan_shapes())}"
                )
            base = FAN_SHAPES[shape]
            spec = FanShapeSpec(
                name=base.name,
                blades=blades if blades is not None else base.blades,
                rings=rings if rings is not None else base.rings,
                slots=slots if slots is not None else base.slots,
                wrap_blades=base.wrap_blades,
                mirror=base.mirror,
                diagonals=base.diagonals,
                hinge_links=base.hinge_links,
                hinges=base.hinges,
            )
        # accordion special-case: treat rings as fold panels on a single blade strip
        self.spec = spec
        self.cells: Tuple[FanCell, ...] = tuple(spec.build_cells())
        self._cell_index: Dict[Tuple[int, int, int, int], FanCell] = {
            c.key(): c for c in self.cells
        }
        self._adj: Dict[FanCell, List[CellEdge]] = {c: [] for c in self.cells}
        self._edges: List[CellEdge] = []
        self._edge_set: Set[Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int], str, str]] = set()
        for edge in spec.build_default_edges(self.cells):
            self._register_edge(edge)
        # accordion mountain/valley meta on ring chain
        if spec.name == "accordion":
            self._tag_accordion_folds()

    # -- construction helpers -------------------------------------------------

    def _edge_identity(self, edge: CellEdge) -> Tuple:
        custom_name = str(edge.meta.get("name", "")) if edge.kind is RelationKind.CUSTOM else ""
        return (edge.a.key(), edge.b.key(), edge.kind.value, custom_name)

    def _register_edge(self, edge: CellEdge) -> bool:
        ident = self._edge_identity(edge)
        if ident in self._edge_set:
            return False
        if edge.a not in self._adj or edge.b not in self._adj:
            raise KeyError("edge endpoints must be grid cells")
        self._edge_set.add(ident)
        self._edges.append(edge)
        self._adj[edge.a].append(edge)
        self._adj[edge.b].append(edge)
        return True

    def _tag_accordion_folds(self) -> None:
        """Mountain/valley alternate along the ring chain (origami accordion)."""
        for edge in list(self._edges):
            if edge.kind is not RelationKind.ADJACENT_RING:
                continue
            # ring index of the inner cell
            inner = edge.a if edge.a.ring < edge.b.ring else edge.b
            fold = "M" if inner.ring % 2 == 0 else "V"
            # replace with annotated edge
            self._remove_edge(edge)
            self._register_edge(
                CellEdge(
                    edge.a,
                    edge.b,
                    RelationKind.ADJACENT_RING,
                    weight=edge.weight,
                    meta={"fold": fold, "name": "accordion_crease"},
                )
            )

    def _remove_edge(self, edge: CellEdge) -> None:
        ident = self._edge_identity(edge)
        self._edge_set.discard(ident)
        self._edges = [e for e in self._edges if self._edge_identity(e) != ident]
        self._adj[edge.a] = [e for e in self._adj[edge.a] if self._edge_identity(e) != ident]
        self._adj[edge.b] = [e for e in self._adj[edge.b] if self._edge_identity(e) != ident]

    # -- public API -----------------------------------------------------------

    @property
    def shape_name(self) -> str:
        return self.spec.name

    def get_cell(
        self,
        blade: int,
        ring: int,
        slot: int = 0,
        hinge: int = 0,
    ) -> FanCell:
        key = (hinge, blade, ring, slot)
        if key not in self._cell_index:
            raise KeyError(f"no cell at hinge={hinge} blade={blade} ring={ring} slot={slot}")
        return self._cell_index[key]

    def add_relation(
        self,
        a: FanCell | Tuple[int, int] | Tuple[int, int, int] | Tuple[int, int, int, int],
        b: FanCell | Tuple[int, int] | Tuple[int, int, int] | Tuple[int, int, int, int],
        kind: RelationKind | str = RelationKind.CUSTOM,
        *,
        weight: float = 1.0,
        name: str | None = None,
        meta: Mapping[str, object] | None = None,
    ) -> CellEdge:
        """Add a custom (or named) relationship between two cells."""
        ca = self._coerce_cell(a)
        cb = self._coerce_cell(b)
        if isinstance(kind, str):
            try:
                kind_e = RelationKind(kind)
            except ValueError:
                kind_e = RelationKind.CUSTOM
                name = name or kind
        else:
            kind_e = kind
        md: Dict[str, object] = dict(meta or {})
        if name is not None:
            md["name"] = name
        edge = CellEdge(ca, cb, kind_e, weight=weight, meta=md)
        if not self._register_edge(edge):
            # already present — return existing
            for e in self._adj[ca]:
                if self._edge_identity(e) == self._edge_identity(edge):
                    return e
        return edge

    def _coerce_cell(
        self,
        value: FanCell | Tuple[int, ...],
    ) -> FanCell:
        if isinstance(value, FanCell):
            if value.key() not in self._cell_index:
                raise KeyError(f"cell {value.label()} not in grid")
            return self._cell_index[value.key()]
        if len(value) == 2:
            blade, ring = value
            return self.get_cell(blade, ring)
        if len(value) == 3:
            blade, ring, slot = value
            return self.get_cell(blade, ring, slot)
        if len(value) == 4:
            hinge, blade, ring, slot = value
            return self.get_cell(blade, ring, slot, hinge)
        raise TypeError("cell must be FanCell or (blade, ring[, slot[, hinge]])")

    def neighbors(
        self,
        cell: FanCell | Tuple[int, ...],
        kinds: Iterable[RelationKind | str] | None = None,
    ) -> List[Tuple[FanCell, CellEdge]]:
        c = self._coerce_cell(cell)
        kind_set: Optional[Set[str]] = None
        if kinds is not None:
            kind_set = {k.value if isinstance(k, RelationKind) else str(k) for k in kinds}
        out: List[Tuple[FanCell, CellEdge]] = []
        for edge in self._adj[c]:
            if kind_set is not None:
                label = edge.kind.value
                custom = str(edge.meta.get("name", ""))
                if label not in kind_set and custom not in kind_set:
                    continue
            out.append((edge.other(c), edge))
        return out

    def relations_between(
        self,
        a: FanCell | Tuple[int, ...],
        b: FanCell | Tuple[int, ...],
    ) -> List[CellEdge]:
        ca, cb = self._coerce_cell(a), self._coerce_cell(b)
        return [e for e in self._adj[ca] if e.touches(cb)]

    def edges(
        self,
        kinds: Iterable[RelationKind | str] | None = None,
    ) -> List[CellEdge]:
        if kinds is None:
            return list(self._edges)
        kind_set = {k.value if isinstance(k, RelationKind) else str(k) for k in kinds}
        return [
            e
            for e in self._edges
            if e.kind.value in kind_set or str(e.meta.get("name", "")) in kind_set
        ]

    def degree(self, cell: FanCell | Tuple[int, ...]) -> int:
        return len(self.neighbors(cell))

    def fold_pairs(self) -> List[Tuple[FanCell, FanCell]]:
        pairs: List[Tuple[FanCell, FanCell]] = []
        for e in self.edges(kinds=[RelationKind.FOLD_MIRROR]):
            pairs.append((e.a, e.b))
        return pairs

    def incidence(
        self,
        kinds: Iterable[RelationKind | str] | None = None,
    ) -> Tuple[Tuple[FanCell, ...], Tuple[CellEdge, ...], List[List[int]]]:
        """Cell x edge incidence matrix (1 if cell touches edge)."""
        cells = self.cells
        edges = tuple(self.edges(kinds=kinds))
        index = {c: i for i, c in enumerate(cells)}
        matrix = [[0 for _ in edges] for _ in cells]
        for j, edge in enumerate(edges):
            matrix[index[edge.a]][j] = 1
            matrix[index[edge.b]][j] = 1
        return cells, edges, matrix

    def polar(
        self,
        cell: FanCell | Tuple[int, ...],
        *,
        radius_step: float = 1.0,
    ) -> Tuple[float, float]:
        """Map cell to (x, y) with hinge at origin; +x is blade 0."""
        c = self._coerce_cell(cell)
        blades = max(1, self.spec.blades)
        if self.spec.wrap_blades:
            angle = 2.0 * math.pi * c.blade / blades
        else:
            # semicircle / open fan: span pi (or less if few blades)
            span = math.pi if blades > 1 else 0.0
            angle = -span / 2.0 + (span * c.blade / max(1, blades - 1) if blades > 1 else 0.0)
        r = (c.ring + 0.5 + 0.15 * c.slot) * radius_step
        # offset multi-hinge along x
        ox = c.hinge * (self.spec.rings + 1) * radius_step * 1.5
        return (ox + r * math.cos(angle), r * math.sin(angle))

    def shortest_path(
        self,
        a: FanCell | Tuple[int, ...],
        b: FanCell | Tuple[int, ...],
        kinds: Iterable[RelationKind | str] | None = None,
    ) -> Optional[List[FanCell]]:
        """BFS path under the chosen relation kinds (default: all)."""
        start, goal = self._coerce_cell(a), self._coerce_cell(b)
        if start == goal:
            return [start]
        prev: Dict[FanCell, Optional[FanCell]] = {start: None}
        queue: List[FanCell] = [start]
        head = 0
        while head < len(queue):
            cur = queue[head]
            head += 1
            for nxt, _ in self.neighbors(cur, kinds=kinds):
                if nxt in prev:
                    continue
                prev[nxt] = cur
                if nxt == goal:
                    path = [goal]
                    while path[-1] is not start:
                        path.append(prev[path[-1]])  # type: ignore[arg-type]
                    path.reverse()
                    return path
                queue.append(nxt)
        return None

    def filter_cells(self, pred: Callable[[FanCell], bool]) -> List[FanCell]:
        return [c for c in self.cells if pred(c)]

    def subgraph_edges(
        self,
        keep_cells: Iterable[FanCell],
        kinds: Iterable[RelationKind | str] | None = None,
    ) -> List[CellEdge]:
        keep = set(keep_cells)
        return [e for e in self.edges(kinds=kinds) if e.a in keep and e.b in keep]

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema": "folding_fan_grid_v1",
            "shape": self.spec.name,
            "blades": self.spec.blades,
            "rings": self.spec.rings,
            "slots": self.spec.slots,
            "hinges": self.spec.hinges,
            "wrap_blades": self.spec.wrap_blades,
            "cell_count": len(self.cells),
            "edge_count": len(self._edges),
            "cells": [list(c.key()) for c in self.cells],
            "edges": [
                {
                    "a": list(e.a.key()),
                    "b": list(e.b.key()),
                    "kind": e.kind.value,
                    "weight": e.weight,
                    "meta": dict(e.meta),
                }
                for e in self._edges
            ],
        }

    def summary(self) -> str:
        kind_counts: Dict[str, int] = {}
        for e in self._edges:
            label = e.kind.value
            if e.kind is RelationKind.CUSTOM and e.meta.get("name"):
                label = f"custom:{e.meta['name']}"
            kind_counts[label] = kind_counts.get(label, 0) + 1
        parts = [f"{k}={v}" for k, v in sorted(kind_counts.items())]
        return (
            f"FoldingFanGrid(shape={self.spec.name!r}, cells={len(self.cells)}, "
            f"edges={len(self._edges)}, " + ", ".join(parts) + ")"
        )

    def __repr__(self) -> str:
        return self.summary()

    def __iter__(self) -> Iterator[FanCell]:
        return iter(self.cells)

    def __len__(self) -> int:
        return len(self.cells)


def build_all_shapes(
    **overrides: int,
) -> Dict[str, FoldingFanGrid]:
    """Instantiate every catalog shape (optional blades/rings overrides ignored per-shape)."""
    return {name: FoldingFanGrid(name) for name in list_fan_shapes()}


__all__ = [
    "RelationKind",
    "FanCell",
    "CellEdge",
    "FanShapeSpec",
    "FAN_SHAPES",
    "list_fan_shapes",
    "FoldingFanGrid",
    "build_all_shapes",
]
