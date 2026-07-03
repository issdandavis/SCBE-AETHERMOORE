from python.scbe.squad_puzzle import Piece, assemble, rect, placements

# A chiral L-tetromino. With orientations=8 it can reflect; with =4 it cannot.
# Region engineered so ONLY the reflected form tiles -> orientations must be load-bearing.
Lc = ((0, 0), (1, 0), (2, 0), (2, 1))  # J/L shape, chiral

p8 = Piece("L8", Lc, 8)
p4 = Piece("L4", Lc, 4)
print("orientations: 8 ->", len(p8.shapes()), " 4 ->", len(p4.shapes()))
# The 8 set should strictly contain the 4 set
s8 = set(p8.shapes()); s4 = set(p4.shapes())
print("4-set subset of 8-set:", s4 <= s8, " 8 has reflections not in 4:", len(s8 - s4))

# Build a region that is exactly one placement of the REFLECTED form, plus fill with monos so areas match.
MONO = Piece("m", ((0, 0),), 1)
refl = sorted(s8 - s4)[0] if (s8 - s4) else None
print("a reflection-only form:", refl)
if refl:
    region = frozenset(refl)
    r8 = assemble(region, [p8])
    r4 = assemble(region, [p4])
    print("region == reflected form alone:")
    print("  orientations=8 solves:", r8.solved, "(should be True - can reflect)")
    print("  orientations=4 solves:", r4.solved, "(should be False - cannot reflect)")
    print("  => orientations field is load-bearing:", r8.solved and not r4.solved)
