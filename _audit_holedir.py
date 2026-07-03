from python.scbe.squad_puzzle import Piece, assemble, placements, holes, rect
import itertools, random

# Direction check: non-empty holes  =>  must be unsolvable (docstring guarantee).
# Search random cases; if ever holes nonempty AND solver/brute say solvable -> docstring is FALSE.
LIB = [
    Piece("mono", ((0, 0),), 1),
    Piece("domino", ((0, 0), (0, 1)), 4),
    Piece("L3", ((0, 0), (1, 0), (1, 1)), 8),
    Piece("I3", ((0, 0), (0, 1), (0, 2)), 4),
    Piece("S4", ((0, 1), (0, 2), (1, 0), (1, 1)), 8),
    Piece("L4", ((0, 0), (1, 0), (2, 0), (2, 1)), 8),
]

def indep(region, pieces):
    region = frozenset(region)
    if sum(p.area for p in pieces) != len(region):
        return False
    pls = [placements(p, region) for p in pieces]
    if any(len(x) == 0 for x in pls):
        return False
    def rec(i, rem):
        if i == len(pieces):
            return not rem
        for pl in pls[i]:
            if pl <= rem and rec(i + 1, rem - pl):
                return True
        return False
    return rec(0, region)

random.seed(7)
viol = 0
checked = 0
for _ in range(6000):
    h = random.randint(1, 5); w = random.randint(1, 5)
    allc = [(r, c) for r in range(h) for c in range(w)]
    region = frozenset(random.sample(allc, random.randint(1, len(allc))))
    base = random.sample(LIB, random.randint(1, 3))
    pieces = []
    for b in base:
        for _ in range(random.randint(1, 2)):
            pieces.append(b)
    if not (1 <= len(pieces) <= 5):
        continue
    checked += 1
    h_set = holes(region, pieces)
    if h_set:  # non-empty holes claimed => unsolvable
        if indep(region, pieces) or assemble(region, pieces).solved:
            viol += 1
            print("HOLE-DIRECTION VIOLATION: holes nonempty but solvable", sorted(region), [p.name for p in pieces])
            if viol >= 5:
                break
print(f"non-empty-holes => unsolvable: checked={checked} violations={viol}")

# Also: dedup in placements must not drop a real placement. Compare placements() count to a naive recompute.
def naive_placements(piece, region):
    rs = [r for r, _ in region]; cs = [c for _, c in region]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
    res = set()
    for shape in piece.shapes():
        for dr in range(r0, r1 + 1):
            for dc in range(c0, c1 + 1):
                placed = frozenset((r + dr, c + dc) for r, c in shape)
                if placed <= region:
                    res.add(placed)
    return res

mism = 0
for p in LIB:
    for (hh, ww) in [(3, 3), (4, 4), (2, 5)]:
        reg = rect(hh, ww)
        a = set(placements(p, reg)); b = naive_placements(p, reg)
        if a != b:
            mism += 1
            print("PLACEMENT MISMATCH", p.name, hh, ww, "code=", len(a), "naive=", len(b))
print("placement dedup mismatches:", mism)
