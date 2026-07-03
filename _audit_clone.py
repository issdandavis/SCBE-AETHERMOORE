from python.scbe.squad_puzzle import Piece, assemble, rect, exact_cover, placements
import itertools


def brute_count_solutions_distinct(region, pieces):
    """Independent: is there ANY assignment of distinct disjoint placements (one per piece) covering region?"""
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


DOM = Piece("d", ((0, 0), (0, 1)), 4)
MONO = Piece("m", ((0, 0),), 1)

# Heavy clone scenarios where the right answer requires placing every clone with no loss.
cases = [
    ("1x8 4 dominoes", rect(1, 8), [DOM] * 4),
    ("2x4 4 dominoes", rect(2, 4), [DOM] * 4),
    ("4x4 8 dominoes", rect(4, 4), [DOM] * 8),
    ("3x4 6 dominoes", rect(3, 4), [DOM] * 6),
    ("2x3 3 dominoes", rect(2, 3), [DOM] * 3),
    ("4x4 6dom+4mono", rect(4, 4), [DOM] * 6 + [MONO] * 4),
]
allgood = True
for name, region, pieces in cases:
    res = assemble(region, pieces)
    bf = brute_count_solutions_distinct(region, pieces)
    n_keys = len(res.placement)
    keys_unique = len(set(res.placement.keys())) == n_keys
    # every cell covered exactly once
    flat = [c for v in res.placement.values() for c in v]
    exact_once = sorted(flat) == sorted(region) and len(flat) == len(set(flat)) if res.solved else True
    placed_all = (n_keys == len(pieces)) if res.solved else True
    ok = (res.solved == bf) and keys_unique and exact_once and placed_all and (res.verify(region) if res.solved else True)
    allgood = allgood and ok
    print(
        f"{name}: solved={res.solved} brute={bf} keys={n_keys}/{len(pieces)} uniq={keys_unique} "
        f"exact_once={exact_once} verify={res.verify(region) if res.solved else 'n/a'} OK={ok}"
    )
print("ALL_GOOD=", allgood)
