"""Independent adversarial audit of squad_puzzle. Brute force is a SEPARATE recursive exact-cover
implementation (not the module's), so agreement is a genuine cross-check."""
import itertools
import random

from python.scbe.squad_puzzle import (
    Piece,
    assemble,
    exact_cover,
    placements,
    rect,
    holes,
    coverable_cells,
    DOMINO,
    MONO,
)


def indep_solvable(region, pieces):
    """Independent exact-cover: place pieces in given order, each piece chooses any of its placements
    that fits the remaining cells; clones of the same name are just additional pieces in the list.
    Returns True iff some assignment exactly covers the region with each piece used once."""
    region = frozenset(region)
    if sum(p.area for p in pieces) != len(region):
        return False
    pls = [placements(p, region) for p in pieces]
    if any(len(x) == 0 for x in pls):
        return False
    order = sorted(range(len(pieces)), key=lambda i: len(pls[i]))  # fewest-options first

    def rec(idx, remaining):
        if idx == len(order):
            return len(remaining) == 0
        pi = order[idx]
        for pl in pls[pi]:
            if pl <= remaining:
                if rec(idx + 1, remaining - pl):
                    return True
        return False

    return rec(0, region)


def check(region, pieces):
    region = frozenset(region)
    res = assemble(region, pieces)
    solver = res.solved
    bf = indep_solvable(region, pieces)
    problems = []
    if solver != bf:
        problems.append(f"DISAGREE solver={solver} brute={bf}")
    if solver:
        if not res.verify(region):
            problems.append("VERIFY_FAIL")
        flat = [c for v in res.placement.values() for c in v]
        if sorted(flat) != sorted(region):
            problems.append("UNION_NEQ_REGION")
        if len(flat) != len(set(flat)):
            problems.append("OVERLAP")
        if len(res.placement) != len(pieces):
            problems.append(f"USECOUNT keys={len(res.placement)} pieces={len(pieces)}")
    return problems, solver, bf


LIB = [
    Piece("mono", ((0, 0),), 1),
    Piece("domino", ((0, 0), (0, 1)), 4),
    Piece("L3", ((0, 0), (1, 0), (1, 1)), 8),
    Piece("I3", ((0, 0), (0, 1), (0, 2)), 4),
    Piece("T4", ((0, 0), (0, 1), (0, 2), (1, 1)), 8),
    Piece("O4", ((0, 0), (0, 1), (1, 0), (1, 1)), 1),
    Piece("S4", ((0, 1), (0, 2), (1, 0), (1, 1)), 8),
    Piece("L4", ((0, 0), (1, 0), (2, 0), (2, 1)), 8),
    Piece("Z4", ((0, 0), (0, 1), (1, 1), (1, 2)), 8),
]

# 1) Random differential, clone-heavy, larger boards (fresh seed/sizes)
random.seed(20260621)
fail = 0
checked = 0
for _ in range(8000):
    h = random.randint(1, 5)
    w = random.randint(1, 5)
    allc = [(r, c) for r in range(h) for c in range(w)]
    region = frozenset(random.sample(allc, random.randint(1, len(allc))))
    base = random.sample(LIB, random.randint(1, 3))
    pieces = []
    for b in base:
        for _ in range(random.randint(1, 3)):
            pieces.append(b)
    random.shuffle(pieces)
    if not (1 <= len(pieces) <= 6):
        continue
    checked += 1
    probs, s, b = check(region, pieces)
    if probs:
        fail += 1
        print("RANDOM FAIL", probs, "region=", sorted(region), "pieces=", [p.name for p in pieces])
        if fail >= 10:
            break
print(f"[1] random differential: checked={checked} failures={fail}")

# 2) Named parity / hole-free-untileable cases
T = Piece("T4", ((0, 0), (0, 1), (0, 2), (1, 1)), 8)
named = [
    ("mut4x4 7dom (parity untileable)", frozenset(c for c in rect(4, 4) if c not in {(0, 0), (3, 3)}), [DOMINO] * 7),
    ("mut4x4 6dom+2mono (tileable)", frozenset(c for c in rect(4, 4) if c not in {(0, 0), (3, 3)}), [DOMINO] * 6 + [MONO, MONO]),
    ("4x4 4T (T-coloring untileable)", rect(4, 4), [T] * 4),
    ("4x4 8dom (tileable)", rect(4, 4), [DOMINO] * 8),
    ("3x3-center 4dom (untileable)", frozenset(c for c in rect(3, 3) if c != (1, 1)), [DOMINO] * 4),
    ("6x6 18dom (tileable)", rect(6, 6), [DOMINO] * 18),
]
nf = 0
for name, region, pieces in named:
    probs, s, b = check(region, pieces)
    hole_free = len(holes(region, pieces)) == 0
    status = "OK" if not probs else "FAIL " + str(probs)
    print(f"[2] {name}: solver={s} brute={b} hole_free={hole_free} {status}")
    if probs:
        nf += 1
print(f"[2] named cases failures={nf}")

# 3) holes honesty: known true holes vs reported
scattered = frozenset({(0, 0), (5, 5)})
print("[3] holes(scattered,[DOMINO])==", holes(scattered, [DOMINO]), "coverable==", set(coverable_cells(scattered, [DOMINO])))
print("[3] holes(scattered,[MONO,MONO])==", holes(scattered, [MONO, MONO]))

print("AUDIT_DONE fail1=", fail, "fail2=", nf)
