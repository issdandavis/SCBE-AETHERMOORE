"""
Illuminate — agentic mass-generation curated by the bicameral gap.
==================================================================

Procedural generation -> AGENTIC generation -> a meta-AI "over-creation" curator.
This is the FunSearch / MAP-Elites loop (DeepMind), but the evaluator every other
system has to bolt on externally is already here: the bicameral reconciler.

For each generated cube program, think() gives logic, intuition, relation, and
confidence. That single signal is, at once:
  * a SAFETY GATE       — 'incomplete' (stack under/overflow) kills malformed programs
  * a FITNESS function  — confidence = 1 - rel_error
  * a NOVELTY compass    — 'diverged' = the program leans on hard nonlinearity (sqrt/pow)

We keep the best ELITE per niche (MAP-Elites quality-diversity), where a niche is
(which nonlinear ops it uses, how logic vs intuition relate). So instead of one
winner we illuminate a diverse archive: the 'exact match' niches are cheap, robust,
ship-ready cubes; the 'diverged' niches are where the interesting novelty lives.
The logic/intuition divergence IS the over-creation selection pressure.
"""

from __future__ import annotations

import random
from typing import Dict, List, Sequence, Tuple

from . import bicameral as B
from . import polyglot as P

_BIN = sorted(o for o in P.SCALAR_OPS if B.EXACT[o][0] == 2)
_UN = sorted(o for o in P.SCALAR_OPS if B.EXACT[o][0] == 1)
_RELATIONS = ("exact match", "close", "diverged", "sign flip")


def random_program(length: int, rng: random.Random) -> List[str]:
    """A stack-valid program (so it mostly runs rather than underflowing)."""
    depth, ops = 3, []
    for _ in range(length):
        if depth >= 2 and rng.random() < 0.6:
            ops.append(rng.choice(_BIN)); depth -= 1
        else:
            ops.append(rng.choice(_UN))
        depth = max(depth, 1)
    return ops


def mutate(ops: Sequence[str], rng: random.Random) -> List[str]:
    """One small edit to an elite — substitute, delete, or insert an op."""
    ops = list(ops)
    if not ops:
        return random_program(3, rng)
    k = rng.randrange(len(ops))
    r = rng.random()
    if r < 0.4:
        ops[k] = rng.choice(_BIN + _UN)
    elif r < 0.7 and len(ops) > 2:
        del ops[k]
    else:
        ops.insert(k, rng.choice(_BIN + _UN))
    return ops


Niche = Tuple[Tuple[str, ...], str]


def illuminate(generations: int = 4, batch: int = 250, seed: int = 7) -> Dict[Niche, dict]:
    """Generate-and-curate loop. Returns the MAP-Elites archive: niche -> elite."""
    rng = random.Random(seed)
    archive: Dict[Niche, dict] = {}

    def consider(ops: List[str]) -> None:
        t = B.think(P.program_bytes(*ops))
        if t["relation"] == "incomplete":         # the safety gate
            return
        key: Niche = (tuple(t["nonlinear_ops"]), str(t["relation"]))
        conf = float(t.get("confidence", 0.0))
        cur = archive.get(key)
        if cur is None or conf > cur["confidence"]:    # keep the best elite per niche
            archive[key] = {"ops": ops, "confidence": conf,
                            "logic": t["logic"], "intuition": t["intuition"]}

    for g in range(generations):
        for _ in range(batch):
            if g == 0 or not archive:
                ops = random_program(rng.randint(2, 8), rng)
            else:                                 # evolve: mutate a surviving elite
                ops = mutate(rng.choice(list(archive.values()))["ops"], rng)
            consider(ops)
    return archive


def render_archive(archive: Dict[Niche, dict]) -> str:
    rows = []
    for (sig, rel), e in archive.items():
        label = "+".join(sig) if sig else "(linear)"
        rows.append((label, rel, e))
    rows.sort(key=lambda r: (_RELATIONS.index(r[1]) if r[1] in _RELATIONS else 9, r[0]))
    out = ["MAP-Elites archive — %d niches (logic vs intuition = fitness)" % len(archive),
           "  %-16s %-12s %-26s %8s %5s" % ("nonlinear", "relation", "elite program", "logic", "conf")]
    for label, rel, e in rows:
        out.append("  %-16s %-12s %-26s %8s %4.0f%%" % (
            label, rel, " ".join(e["ops"])[:26], B._fmt(e["logic"]), 100 * e["confidence"]))
    n_exact = sum(1 for (_s, r) in archive if r == "exact match")
    n_div = sum(1 for (_s, r) in archive if r in ("diverged", "sign flip"))
    out.append("  -> %d intuitive (ship-ready) · %d divergent (novelty to mine)" % (n_exact, n_div))
    return "\n".join(out)


def _demo() -> None:
    print("Illuminate — mass-generate cube programs, curate by the bicameral gap\n")
    print(render_archive(illuminate()))


if __name__ == "__main__":
    _demo()
