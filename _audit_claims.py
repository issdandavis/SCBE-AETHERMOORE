from python.scbe.squad_puzzle import (
    Piece, assemble, exact_cover, placements, rect, holes, demo,
    MONO, DOMINO, I_TROMINO, L_TROMINO, T_TETRO, SQUARE,
)

print("=== determinism: does placement depend on piece ORDER? ===")
region = rect(2, 4)
import itertools
pls = set()
for perm in itertools.permutations([T_TETRO, L_TROMINO, MONO]):
    r = assemble(region, list(perm))
    pls.add(frozenset((k, r.placement[k]) for k in r.placement))
print("distinct placements across orderings:", len(pls))  # determinism claim is only for fixed order

print()
print("=== claim: 'isolated cell -> hole' truly means NO exact tiling can exist ===")
# docstring (holes): 'A non-empty holes set means no exact tiling can exist'. Test it: hole present but
# area mismatch could ALSO give holes. Construct a case with holes but where naive reader thinks solvable.
scattered = frozenset({(0, 0), (5, 5)})
r = assemble(scattered, [DOMINO])
print("scattered/domino solved:", r.solved, "holes:", r.holes)

print()
print("=== overclaim probe: does a NON-empty holes set ALWAYS imply unsolvable? ===")
# holes() uses placements of EACH piece independently. But exact_cover needs ALL pieces placed once.
# Could a cell be 'coverable' by some piece yet the tiling still be impossible? (yes -> parity).
# Conversely: is it possible holes==() AND area matches AND yet a single piece has NO placement?
# That would make exact_cover return None at the 'fits nowhere' guard even though holes is empty.
big = Piece("big", tuple((0, c) for c in range(5)), 1)  # 1x5 bar, fixed
small = Piece("u", ((0, 0),), 1)
region = frozenset({(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)})  # 2x3, area 6
pieces = [big, small]  # area 5+1=6 matches; big (1x5) fits NOWHERE in a 3-wide region
r = assemble(region, pieces)
h = holes(region, pieces)
print("2x3 with 1x5-bar+mono: solved=", r.solved, "holes=", h, "area_match=", r.area_pieces == r.area_region)
# Here mono covers everything reachable, so holes may be empty, yet unsolvable because big fits nowhere.
print("coverable by union:", len(set(__import__('python.scbe.squad_puzzle', fromlist=['coverable_cells']).coverable_cells(region, pieces))))

print()
print("=== demo() honesty ===")
d = demo()
for k, v in d.items():
    if not k.startswith("_"):
        print(f"  {k} = {v}")
