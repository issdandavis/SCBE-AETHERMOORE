"""Domain-agnostic legality kernel for the SCBE Board Kernel.

A deterministic Go-derived graph lattice. Players are integers; points are ``(row, col)``.
The board decides legality; callers only *propose* moves. Tromp-Taylor-style backbone:
**positional superko** (no whole-board repeat) + **area scoring**. Deliberate v1 divergence:
**suicide is illegal** (mainstream convention) rather than T-T's legal self-removal.

No domain words (no parties / prose / qi) and no SCBE imports live here — this is the reusable
core that narrative, coding, writing, and workflow adapters all build on. The graph view (a
*string* of stones is a node; its liberties are edges) is exposed for lattice analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

Point = tuple[int, int]
Grid = list[list[Optional[int]]]


class IllegalMove(ValueError):
    """Raised when a proposed move violates board legality (occupied / suicide / superko)."""


@dataclass(frozen=True)
class Observation:
    """What a probe move *would* do, sampled without committing."""

    legal: bool
    reason: str  # "" when legal, else why it is rejected
    would_capture: tuple[Point, ...]  # opponent points that would be removed
    resulting_liberties: int  # liberties of the played group after captures (0 if illegal)


@dataclass(frozen=True)
class MoveResult:
    """The outcome of a committed legal move."""

    player: int
    point: Point
    captured: tuple[Point, ...]
    liberties: int  # liberties of the played group after captures


def _neighbors(pt: Point, size: int) -> list[Point]:
    r, c = pt
    out: list[Point] = []
    if r > 0:
        out.append((r - 1, c))
    if r < size - 1:
        out.append((r + 1, c))
    if c > 0:
        out.append((r, c - 1))
    if c < size - 1:
        out.append((r, c + 1))
    return out


def _group_and_liberties(grid: Grid, pt: Point, size: int) -> tuple[set[Point], set[Point]]:
    """Flood-fill the maximal same-player string containing ``pt`` and its liberty set."""
    player = grid[pt[0]][pt[1]]
    if player is None:
        return set(), set()
    group: set[Point] = set()
    liberties: set[Point] = set()
    stack = [pt]
    while stack:
        cur = stack.pop()
        if cur in group:
            continue
        group.add(cur)
        for nb in _neighbors(cur, size):
            occupant = grid[nb[0]][nb[1]]
            if occupant is None:
                liberties.add(nb)
            elif occupant == player and nb not in group:
                stack.append(nb)
    return group, liberties


class Board:
    """A square Go board. Default 9x9; smaller sizes are allowed for tests and small scenes."""

    def __init__(self, size: int = 9) -> None:
        self.size = size
        self._grid: Grid = [[None] * size for _ in range(size)]
        self._protected: set[Point] = set()  # stones here are immune from capture (e.g. treaty zones)
        self._history: set[tuple] = {self._snapshot()}

    # --- geometry / inspection ---

    def in_bounds(self, pt: Point) -> bool:
        r, c = pt
        return 0 <= r < self.size and 0 <= c < self.size

    def at(self, pt: Point) -> Optional[int]:
        return self._grid[pt[0]][pt[1]]

    def neighbors(self, pt: Point) -> list[Point]:
        return _neighbors(pt, self.size)

    def group_and_liberties(self, pt: Point) -> tuple[set[Point], set[Point]]:
        return _group_and_liberties(self._grid, pt, self.size)

    def liberties(self, pt: Point) -> int:
        return len(self.group_and_liberties(pt)[1])

    def set_protected(self, points: Iterable[Point]) -> None:
        """Mark points whose stones cannot be captured (the generic hook a treaty zone uses)."""
        self._protected = {pt for pt in points if self.in_bounds(pt)}

    # --- the one simulation both probe() and place() share ---

    def _simulate(self, player: int, pt: Point) -> tuple[bool, str, frozenset[Point], int, Optional[Grid]]:
        if not self.in_bounds(pt):
            return False, "out of bounds", frozenset(), 0, None
        if self._grid[pt[0]][pt[1]] is not None:
            return False, "point is occupied", frozenset(), 0, None

        grid: Grid = [row[:] for row in self._grid]
        grid[pt[0]][pt[1]] = player

        captured: set[Point] = set()
        for nb in _neighbors(pt, self.size):
            occupant = grid[nb[0]][nb[1]]
            if occupant is not None and occupant != player:
                group, libs = _group_and_liberties(grid, nb, self.size)
                if not libs and not (group & self._protected):
                    for gp in group:
                        grid[gp[0]][gp[1]] = None
                    captured |= group

        _, own_libs = _group_and_liberties(grid, pt, self.size)
        if not own_libs:
            return False, "suicide (own group would have no liberties)", frozenset(), 0, None

        snapshot = tuple(tuple(row) for row in grid)
        if snapshot in self._history:
            return False, "superko (repeats a previous board position)", frozenset(), 0, None

        return True, "", frozenset(captured), len(own_libs), grid

    # --- the two move classes ---

    def probe(self, player: int, pt: Point) -> Observation:
        """Sense the state space: report what the move would do without committing it."""
        legal, reason, captured, libs, _ = self._simulate(player, pt)
        return Observation(
            legal=legal,
            reason=reason,
            would_capture=tuple(sorted(captured)),
            resulting_liberties=libs,
        )

    def place(self, player: int, pt: Point) -> MoveResult:
        """Commit a legal move, or raise IllegalMove. The board, not the caller, decides."""
        legal, reason, captured, libs, grid = self._simulate(player, pt)
        if not legal or grid is None:
            raise IllegalMove(f"{pt}: {reason}")
        self._grid = grid
        self._history.add(tuple(tuple(row) for row in grid))
        return MoveResult(player=player, point=pt, captured=tuple(sorted(captured)), liberties=libs)

    def legal_placements(self, player: int) -> list[Point]:
        return [
            (r, c)
            for r in range(self.size)
            for c in range(self.size)
            if self._grid[r][c] is None and self.probe(player, (r, c)).legal
        ]

    # --- analysis ---

    def score(self) -> dict[int, int]:
        """Area score per player: stones + empty regions bordered by exactly one player."""
        stones: dict[int, int] = {}
        for r in range(self.size):
            for c in range(self.size):
                occupant = self._grid[r][c]
                if occupant is not None:
                    stones[occupant] = stones.get(occupant, 0) + 1

        territory: dict[int, int] = {}
        visited: set[Point] = set()
        for r in range(self.size):
            for c in range(self.size):
                if self._grid[r][c] is not None or (r, c) in visited:
                    continue
                region: set[Point] = set()
                borders: set[int] = set()
                stack = [(r, c)]
                while stack:
                    cur = stack.pop()
                    if cur in region:
                        continue
                    region.add(cur)
                    visited.add(cur)
                    for nb in _neighbors(cur, self.size):
                        occupant = self._grid[nb[0]][nb[1]]
                        if occupant is None and nb not in region:
                            stack.append(nb)
                        elif occupant is not None:
                            borders.add(occupant)
                if len(borders) == 1:
                    owner = next(iter(borders))
                    territory[owner] = territory.get(owner, 0) + len(region)

        return {p: stones.get(p, 0) + territory.get(p, 0) for p in set(stones) | set(territory)}

    def graph_view(self) -> list[dict]:
        """Strings as nodes, liberties as edge-count — the lattice view of the position."""
        seen: set[Point] = set()
        nodes: list[dict] = []
        for r in range(self.size):
            for c in range(self.size):
                if self._grid[r][c] is None or (r, c) in seen:
                    continue
                group, libs = _group_and_liberties(self._grid, (r, c), self.size)
                seen |= group
                nodes.append({"player": self._grid[r][c], "stones": tuple(sorted(group)), "liberties": len(libs)})
        return nodes

    # --- serialization ---

    def _snapshot(self) -> tuple:
        return tuple(tuple(row) for row in self._grid)

    def ascii(self, symbols: Optional[dict] = None) -> str:
        glyphs = symbols or {None: ".", 0: "X", 1: "O"}
        return "\n".join("".join(glyphs.get(self._grid[r][c], "?") for c in range(self.size)) for r in range(self.size))

    @classmethod
    def from_ascii(cls, text: str, mapping: Optional[dict] = None) -> "Board":
        """Build a board from rows of glyphs (spaces ignored), for tests and fixtures."""
        glyphs = mapping or {"X": 0, "O": 1, ".": None}
        rows = [line.replace(" ", "") for line in text.strip().splitlines() if line.strip()]
        size = len(rows)
        if any(len(row) != size for row in rows):
            raise ValueError("from_ascii expects a square board (every row as long as the row count)")
        board = cls(size=size)
        board._grid = [[glyphs[ch] for ch in row] for row in rows]
        board._history = {board._snapshot()}
        return board
