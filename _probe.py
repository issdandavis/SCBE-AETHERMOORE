import random
from python.helm.squad_bench import random_board
from python.scbe.coding_squad import solve_with_squad
from python.scbe.coding_board import Board, Operator, region_must_agree

rng = random.Random(8)
ov = []
un = 0
for _ in range(3000):
    b = random_board(rng, rng.randint(2, 6))
    res = solve_with_squad(b)
    if res.solved:
        ov.append(res.squad_energy.overwrites)
    else:
        un += 1
print("solved", len(ov), "unsolved", un)
print("distinct overwrites among solved:", sorted(set(ov)))
print("max overwrites among solved:", max(ov) if ov else None)

# Now: can ANY region_must_agree board (the benchmark's ONLY CSP class) ever backtrack & still solve?
# Construct an adversarial agree-board that forces a conflict then resolves.
b2 = Board([
    Operator("a", ("A", "B"), region="r"),
    Operator("b", ("B",), region="r", fixed="B"),
    Operator("c", ("A", "B"), region="r"),
], [region_must_agree])
r2 = solve_with_squad(b2)
print("adversarial agree-board solved:", r2.solved, "overwrites:", r2.squad_energy.overwrites, "jumps:", r2.jumps)
