from python.scbe.squad_puzzle import Piece, assemble, rect, holes, DOMINO, placements
import itertools


def brute(region, pieces):
    region = frozenset(region)
    if sum(p.area for p in pieces) != len(region):
        return False
    pp = [placements(p, region) for p in pieces]
    for combo in itertools.product(*pp):
        seen = set()
        ok = True
        for pl in combo:
            if pl & seen:
                ok = False
                break
            seen |= pl
        if ok and seen == set(region):
            return True
    return False


ring = frozenset(c for c in rect(3, 3) if c != (1, 1))
mut = frozenset(c for c in rect(4, 4) if c not in {(0, 0), (3, 3)})
T = Piece("T4", ((0, 0), (0, 1), (0, 2), (1, 1)), 8)
cases = [
    ("3x3-center 4dom", ring, [DOMINO] * 4),
    ("2x3 3dom", rect(2, 3), [DOMINO] * 3),
    ("mut4x4 7dom", mut, [DOMINO] * 7),
    ("4x4 4T", rect(4, 4), [T] * 4),
]
for name, region, pieces in cases:
    res = assemble(region, pieces)
    bf = brute(region, pieces)
    h = holes(region, pieces)
    vf = res.solved and not res.verify(region)
    print(name, "solver=", res.solved, "brute=", bf, "holes=", len(h), "AGREE=", res.solved == bf, "VERIFYFAIL=", vf)
