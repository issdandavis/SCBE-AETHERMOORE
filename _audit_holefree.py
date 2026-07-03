from python.scbe.squad_puzzle import Piece, assemble, placements, holes, coverable_cells
import itertools

# Hole-free yet untileable, NOT by parity: 2x3 region, pieces = [1x5 bar, mono].
# area 5+1 = 6 = area(region). mono can reach every cell -> coverable union == region -> holes == ().
# But the 1x5 bar has NO placement in a 3-wide-by-2-tall region -> no tiling. Obstruction is
# 'a piece fits nowhere', which is neither a per-cell hole NOR a colour-parity argument.

big = Piece("big", tuple((0, c) for c in range(5)), 1)
mono = Piece("u", ((0, 0),), 1)
region = frozenset({(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)})
pieces = [big, mono]

# independent brute (separate impl)
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

r = assemble(region, pieces)
print("solved        :", r.solved)
print("brute solvable:", indep(region, pieces))
print("holes         :", r.holes, "(empty => hole-free)")
print("area match    :", r.area_pieces, "==", r.area_region)
print("big placements:", len(placements(big, region)), "(0 => bar fits nowhere)")
print("coverable==region:", set(coverable_cells(region, pieces)) == region)
# Is it a PARITY obstruction? Checkerboard colour count of a 2x3 = 3 black, 3 white; a 1x5 covers 3/2 or 2/3,
# mono covers 1 -> 5+1 colour split is achievable; so colour parity does NOT forbid it. The only obstruction
# is that the bar cannot be placed at all.
def colour(region):
    b = sum(1 for (r, c) in region if (r + c) % 2 == 0)
    return b, len(region) - b
print("region colours (b,w):", colour(region), "-> balanced, so NOT a parity wall")
