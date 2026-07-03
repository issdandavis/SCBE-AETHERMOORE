from python.scbe.squad_puzzle import Piece, assemble, placements, rect, exact_cover
import itertools

DOM = Piece("d", ((0, 0), (0, 1)), 4)
L = Piece("L3", ((0, 0), (1, 0), (1, 1)), 8)

# Force heavy backtracking with many identical clones; verify the returned cover is a TRUE exact cover
# (no key collision silently dropped a placement) for a range of solvable clone-heavy regions.
cases = [
    ("4x4 8 dominoes", rect(4, 4), [DOM] * 8),
    ("6x4 12 dominoes", rect(6, 4), [DOM] * 12),
    ("2x6 4 L-trominoes", rect(2, 6), [L] * 4),
    ("4x6 8 L-trominoes", rect(4, 6), [L] * 8),
    ("1x10 5 dominoes", rect(1, 10), [DOM] * 5),
]
bad = 0
for name, region, pieces in cases:
    region = frozenset(region)
    r = assemble(region, pieces)
    if not r.solved:
        print(name, "UNEXPECTEDLY UNSOLVED")
        bad += 1
        continue
    # exact-cover integrity from the returned dict
    flat = [c for v in r.placement.values() for c in v]
    keys = list(r.placement.keys())
    cond = (
        len(r.placement) == len(pieces)            # every clone placed (no key collision dropped one)
        and len(set(keys)) == len(keys)            # all keys distinct
        and sorted(flat) == sorted(region)         # union == region
        and len(flat) == len(set(flat))            # disjoint
        and r.verify(region)
    )
    print(f"{name}: keys={len(keys)}/{len(pieces)} union_ok={sorted(flat)==sorted(region)} disjoint={len(flat)==len(set(flat))} verify={r.verify(region)} -> {'OK' if cond else 'FAIL'}")
    if not cond:
        bad += 1
        print("   keys:", keys)
print("clone-key failures:", bad)
