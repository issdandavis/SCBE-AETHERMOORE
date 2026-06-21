"""squad_puzzle: the squad's NON-STANDARD value -- each member contributes a GEOMETRIC PIECE (a polyomino)
instead of a scalar reading, and "triangulating the target" becomes ASSEMBLING it as an EXACT-COVER puzzle.

This is the weird-geometric-puzzle form of coding_squad's triangulate: there, a member's value is a number
(a projection r_i = <profile_i, target>) and the squad LOCALIZES the target by least-squares. Here a member's
value is a SHAPE, and the squad must TILE the target region with the pieces -- every cell covered exactly once,
no overlap, no gap (Knuth's exact cover / Algorithm X; polyomino packing, the canonical geometric puzzle).

The differentiation claim carries over, now geometric and provable by execution:
  * a squad of IDENTICAL pieces (clones) can only tile targets that decompose into that one shape -- it FAILS
    on a MATCHING-AREA target that a DIFFERENTIATED squad tiles, so shape-diversity (not area) is what makes
    the assembly possible -- the geometric echo of "a clone squad is rank-deficient and cannot triangulate".
  * a cell NO piece can reach is a HOLE -- an ANALOGOUS blind spot to the triangulation null space (the
    "absence is information" gap). Honest difference: a hole is region-dependent REACH, not the squad-only
    null space, so a single covering clone has zero holes; and a hole-free target can still be untileable for
    reasons beyond a single uncoverable cell -- a colour-PARITY obstruction (the mutilated chessboard), OR a
    piece that simply has no legal placement at all (e.g. a 1x5 bar in a 3-wide region).

HONEST: this is polyomino EXACT COVER with a small deterministic Algorithm-X-style solver (most-constrained
cell, backtracking). The "value" of a member is its piece shape + allowed orientations (1=fixed, 4=rotations,
8=dihedral incl. reflections), not a number. It assembles-to-localize; it adds no power beyond exact cover.
A solved tiling is verified by re-checking the cover (disjoint placements whose union == the region)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

Cell = Tuple[int, int]


def _normalize(cells: Sequence[Cell]) -> Tuple[Cell, ...]:
    """Translate a shape so its min row and min col are 0, and sort -- a canonical key for a polyomino."""
    mr = min(r for r, _c in cells)
    mc = min(c for _r, c in cells)
    return tuple(sorted((r - mr, c - mc) for r, c in cells))


def _rot90(cells: Sequence[Cell]) -> Tuple[Cell, ...]:
    return _normalize([(c, -r) for r, c in cells])  # (r,c) -> (c,-r): quarter turn


def _reflect(cells: Sequence[Cell]) -> Tuple[Cell, ...]:
    return _normalize([(r, -c) for r, c in cells])  # mirror across the vertical axis


@dataclass(frozen=True)
class Piece:
    """A geometric piece: a polyomino given by its cell offsets, plus how many orientations it may take
    (1 = fixed, 4 = rotations, 8 = rotations + reflections = the full dihedral group). The member's
    NON-STANDARD value -- a shape, not a scalar."""

    name: str
    cells: Tuple[Cell, ...]
    orientations: int = 1

    @property
    def area(self) -> int:
        return len(self.cells)

    def shapes(self) -> Tuple[Tuple[Cell, ...], ...]:
        """The distinct normalized orientations this piece may take (deduped; a symmetric piece has fewer)."""
        base = _normalize(self.cells)
        forms: List[Tuple[Cell, ...]] = [base]
        if self.orientations >= 4:
            s = base
            for _ in range(3):
                s = _rot90(s)
                forms.append(s)
        if self.orientations >= 8:
            rf = _reflect(base)
            forms.append(rf)
            s = rf
            for _ in range(3):
                s = _rot90(s)
                forms.append(s)
        out: List[Tuple[Cell, ...]] = []
        for f in forms:
            if f not in out:
                out.append(f)
        return tuple(out)


Region = FrozenSet[Cell]


def rect(h: int, w: int) -> Region:
    """An h x w rectangular region of cells."""
    return frozenset((r, c) for r in range(h) for c in range(w))


def placements(piece: Piece, region: Region) -> List[FrozenSet[Cell]]:
    """Every way to place the piece (any allowed orientation, any translation) so it lies fully inside the
    region. Returned sorted for determinism; duplicates (from a symmetric piece) collapse."""
    rs = [r for r, _c in region]
    cs = [c for _r, c in region]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
    seen: set = set()
    out: List[FrozenSet[Cell]] = []
    for shape in piece.shapes():
        for dr in range(r0, r1 + 1):
            for dc in range(c0, c1 + 1):
                placed = frozenset((r + dr, c + dc) for r, c in shape)
                if placed <= region and placed not in seen:
                    seen.add(placed)
                    out.append(placed)
    out.sort(key=lambda pl: tuple(sorted(pl)))
    return out


def coverable_cells(region: Region, pieces: Sequence[Piece]) -> Region:
    """The cells SOME piece can reach in some placement. region - this == the holes (unreachable cells)."""
    covered: set = set()
    for p in pieces:
        for placed in placements(p, region):
            covered |= placed
    return frozenset(covered)


def holes(region: Region, pieces: Sequence[Piece]) -> Tuple[Cell, ...]:
    """The region cells NO piece can cover -- an analogous blind spot (unreachable cells, the 'absence is
    information' gap). A non-empty holes set means no exact tiling can exist (something is structurally
    uncoverable); but the converse fails -- a hole-free region can still be untileable for other reasons
    (a colour-parity obstruction, or a piece with no legal placement anywhere)."""
    return tuple(sorted(set(region) - coverable_cells(region, pieces)))


def exact_cover(region: Region, pieces: Sequence[Piece]) -> Optional[Dict[str, FrozenSet[Cell]]]:
    """Tile the region using EACH piece exactly once, covering every cell exactly once (Algorithm X style:
    branch on the most-constrained remaining cell, backtrack). Deterministic. Returns {piece_name: placement}
    or None if no exact tiling exists. (Each piece used once -> the total piece area must equal the region.)"""
    region = frozenset(region)
    if sum(p.area for p in pieces) != len(region):
        return None  # each-piece-once tiling is impossible unless the areas match
    # all candidate placements, tagged by piece name, in a deterministic order
    options: List[Tuple[str, FrozenSet[Cell]]] = []
    for p in pieces:
        pls = placements(p, region)
        if not pls:
            return None  # a piece that fits nowhere -> no tiling
        for pl in pls:
            options.append((p.name, pl))
    # index name multiplicity: identical-named clones are distinct uses, tracked by remaining count
    from collections import Counter

    need: Counter = Counter(p.name for p in pieces)
    chosen: Dict[str, FrozenSet[Cell]] = {}

    def _opts(cell: Cell, remaining: FrozenSet[Cell], used: Counter) -> List[Tuple[str, FrozenSet[Cell]]]:
        out = []
        for name, pl in options:
            if cell in pl and pl <= remaining and used[name] < need[name]:
                out.append((name, pl))
        return out

    def solve(remaining: FrozenSet[Cell], used: Counter, slot: int) -> bool:
        if not remaining:
            return True
        # most-constrained cell: the one with the fewest covering options (Knuth's S heuristic)
        cell = min(remaining, key=lambda x: len(_opts(x, remaining, used)))
        for name, pl in _opts(cell, remaining, used):
            key = "%s#%d" % (name, used[name]) if need[name] > 1 else name
            chosen[key] = pl
            used[name] += 1
            if solve(remaining - pl, used, slot + 1):
                return True
            used[name] -= 1
            del chosen[key]
        return False

    if solve(region, Counter(), 0):
        return dict(chosen)
    return None


@dataclass
class PuzzleResult:
    solved: bool
    placement: Dict[str, Tuple[Cell, ...]]  # piece (name, or name#k for clones) -> the cells it occupies
    holes: Tuple[Cell, ...]  # region cells no piece can reach (the blind spots; absence is information)
    area_pieces: int
    area_region: int

    def verify(self, region: Region) -> bool:
        """Independently re-check a solved tiling: placements are disjoint and their union == the region."""
        if not self.solved:
            return False
        seen: set = set()
        for cells in self.placement.values():
            s = set(cells)
            if s & seen:
                return False  # overlap
            seen |= s
        return seen == set(region)


def assemble(region: Region, pieces: Sequence[Piece]) -> PuzzleResult:
    """Try to tile the region exactly with the pieces (each used once). Reports solved + the placement, and
    ALWAYS the holes (cells no piece can reach), so a failure tells you WHY -- a structural blind spot, an
    area mismatch, or an unsatisfiable packing. The geometric-puzzle form of triangulate()."""
    region = frozenset(region)
    cover = exact_cover(region, pieces)
    placement = {k: tuple(sorted(v)) for k, v in cover.items()} if cover else {}
    return PuzzleResult(
        solved=cover is not None,
        placement=placement,
        holes=holes(region, pieces),
        area_pieces=sum(p.area for p in pieces),
        area_region=len(region),
    )


# --- a small piece library (the non-standard "values") --------------------------------------------
MONO = Piece("mono", ((0, 0),), 1)
DOMINO = Piece("domino", ((0, 0), (0, 1)), 4)
L_TROMINO = Piece("L3", ((0, 0), (1, 0), (1, 1)), 8)
I_TROMINO = Piece("I3", ((0, 0), (0, 1), (0, 2)), 4)
T_TETRO = Piece("T4", ((0, 0), (0, 1), (0, 2), (1, 1)), 8)
SQUARE = Piece("O4", ((0, 0), (0, 1), (1, 0), (1, 1)), 1)


def demo() -> Dict[str, object]:
    # MATCHED-AREA isolation (so the variable under test is shape-diversity, not area): a bent-L target of
    # area 3. A homogeneous straight I-tromino (also area 3) CANNOT bend to fit it; a DIFFERENTIATED squad
    # (mono + domino, also area 3) tiles it. Same area -> differentiation is the only difference.
    bent_l = frozenset({(0, 0), (1, 0), (1, 1)})
    diff = assemble(bent_l, [MONO, DOMINO])
    clone = assemble(bent_l, [I_TROMINO])  # straight, area 3, but no placement bends into the L -> fails

    # a matched-area MULTI-clone failure by PARITY: the mutilated chessboard (14 cells). Seven dominoes can't
    # (8-vs-6 colour imbalance); swapping two dominoes for two monominoes (a differentiated squad, still 14)
    # tiles it -- shape-diversity defeats the parity wall.
    mutilated = frozenset(c for c in rect(4, 4) if c not in {(0, 0), (3, 3)})
    clone7 = assemble(mutilated, [DOMINO] * 7)
    diff_mut = assemble(mutilated, [DOMINO] * 6 + [MONO, MONO])

    # clones are not useless: two dominoes DO tile a 2x2 square (a target that decomposes into their shape)
    clones_ok = assemble(rect(2, 2), [DOMINO, DOMINO])

    # a HOLE: two isolated cells with only a domino available -> neither can be covered (the blind spots)
    scattered = frozenset({(0, 0), (5, 5)})
    gap = assemble(scattered, [DOMINO])

    return {
        "differentiated_tiles_matched_area_target": diff.solved and diff.verify(bent_l),
        "homogeneous_clone_fails_same_area_target": not clone.solved,
        "clone_parity_fails_differentiated_tiles": (not clone7.solved)
        and diff_mut.solved
        and diff_mut.verify(mutilated),
        "clones_still_tile_a_matching_target": clones_ok.solved and clones_ok.verify(rect(2, 2)),
        "isolated_cells_are_holes": gap.holes == ((0, 0), (5, 5)) and not gap.solved,
        "_diff": diff,
        "_diff_mut": diff_mut,
    }


def main() -> int:
    d = demo()
    print("SQUAD PUZZLE -- non-standard geometric value: each member is a PIECE, the squad TILES the target")
    print(
        "  differentiated squad (mono+domino) tiles a bent-L target     : %s"
        % d["differentiated_tiles_matched_area_target"]
    )
    print(
        "  SAME-AREA homogeneous clone (straight I-tromino) FAILS it     : %s"
        % d["homogeneous_clone_fails_same_area_target"]
    )
    print(
        "  matched-area parity: 7-domino clone fails, +2 monomino tiles  : %s"
        % d["clone_parity_fails_differentiated_tiles"]
    )
    print(
        "  ...but clones DO tile a target that fits their shape (2x2)    : %s"
        % d["clones_still_tile_a_matching_target"]
    )
    print("  isolated cells no piece can reach are reported as HOLES       : %s" % d["isolated_cells_are_holes"])
    print("  => shape-DIVERSITY (not area) makes the assembly possible; holes/parity = the blind spots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
