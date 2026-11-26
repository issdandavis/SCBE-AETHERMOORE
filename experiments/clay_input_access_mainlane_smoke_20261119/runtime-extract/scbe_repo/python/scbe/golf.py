"""golf: one jurisdiction, two clubs -- the honest control surface over non-inference solving.

A coding or grid task is a hole. You sink it in the fewest STROKES (cost) by picking the right CLUB and
reading the green. Two clubs are built, and BOTH run with no neural forward pass:

  - the PUTTER = analog_solve ([[analog-solve-library-lane]]): retrieval/interpolation over verified
    code neighbors -- the short game, for a hole near one you have already sunk;
  - the DRIVER = neurogolf (src/neurogolf): move-family composition searched under a cost gate and
    compiled to a tiny static program -- the long game, for NOVEL ARC grid structure the putter cannot
    reach (the putter scores 0% on genuinely novel problems; the driver is built for exactly that case).

This module is the JURISDICTION, not the club-picker (the router that selects a club by distance-to-hole
is owned elsewhere). Every shot is played the same way: the club produces a candidate, an UN-STEERED
proctor checks it -- it scores correctness it cannot see the held-out answer to (execution for code,
exact train-match for grids) -- and the result is SHA-256 forward-chain sealed into a scorecard that
records WHICH club sank it, in how many strokes, verified or not. The receipt credits the CLUB, never a
model's "understanding": the honest counterpart to the +24 that died crediting a model for the room's
answer-elimination (see [[tool-use-is-the-skill]]). The proctor is the un-steered referee; the club is
the candidate driving a tool. That separation is the whole point.

    card = GolfCard()
    play(card, putter(maze), code_hole("sum two numbers", ["assert total(2, 3) == 5"]))   # SUNK via putter
    play(card, driver(), grid_hole([([[1, 2]], [[3, 4]])], [[[2, 1]]]))                    # SUNK via driver
    card.verify()  # the scorecard chain holds
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from .desktop_access import _seal

_SRC = str(Path(__file__).resolve().parents[2] / "src")  # so `import neurogolf` resolves for the driver


# --- the scorecard: forward-chain sealed shots (the SAME seal AetherDesk uses) -----------------------


class GolfCard:
    """A sealed scorecard. Each shot is forward-chain sealed exactly like an AetherDesk receipt: rewrite
    any field and its hash breaks; reorder/insert/delete and the `_prev` linkage breaks. verify() walks
    the chain. (Same HONEST LIMIT as _seal: unkeyed hash on an in-memory nonce -- internal consistency +
    un-re-chained tamper, not host-tamper-evidence.)"""

    def __init__(self, nonce: str = "golf") -> None:
        self.nonce = nonce
        self.shots: List[dict] = []

    def record(self, club: str, domain: str, verified: Optional[bool], strokes: int, detail: str) -> dict:
        rec = {
            "hop": len(self.shots) + 1,
            "club": club,
            "domain": domain,
            "decision": "SUNK" if verified else ("UNSCORED" if verified is None else "MISSED"),
            "strokes": int(strokes),
            "detail": str(detail)[:200],
        }
        rec["_prev"] = self.shots[-1]["seal"] if self.shots else self.nonce
        rec["seal"] = _seal(rec)
        self.shots.append(rec)
        return rec

    def verify(self) -> bool:
        prev = self.nonce
        for r in self.shots:
            if r.get("seal") != _seal(r) or r.get("_prev") != prev:
                return False
            prev = r["seal"]
        return True

    def scorecard(self) -> List[dict]:
        return self.shots


# --- a hole: a task plus its UN-STEERED proctor (scores without seeing the held-out answer) ----------


@dataclass
class Hole:
    domain: str
    payload: Dict[str, Any]
    proctor: Callable[[Any], bool]  # candidate -> sank? (uses only the given spec, never a held-out label)


def code_hole(problem: str, checks: Sequence[str], imports: Sequence[str] = ()) -> Hole:
    """A code hole: the proctor runs the GIVEN tests by execution (it does not know any held-out answer)."""
    from python.helm import public_bench as pb

    checks, imports = list(checks), list(imports)

    def proctor(candidate: Optional[str]) -> bool:
        if not candidate:
            return False
        return bool(pb._verify(candidate, [], checks, imports)["hidden_passed"])

    return Hole("code", {"problem": problem, "checks": checks, "imports": imports}, proctor)


def grid_hole(train_pairs: Sequence, test_inputs: Sequence = ()) -> Hole:
    """A grid hole. `train_pairs` = [(input_grid, output_grid), ...] as nested int lists; these ARE the
    spec. The proctor sinks a program iff it reproduces EVERY train output exactly -- the held-out test
    inputs stay unseen, so the referee never holds the answer."""
    sys.path.insert(0, _SRC)
    import numpy as np
    from neurogolf.arc_io import ARCExample, ARCTask
    from neurogolf.solver import execute_program

    train = tuple(
        ARCExample(input=np.asarray(i, dtype=np.int64), output=np.asarray(o, dtype=np.int64)) for i, o in train_pairs
    )
    test = tuple(np.asarray(t, dtype=np.int64) for t in test_inputs)
    task = ARCTask(task_id="hole", train=train, test_inputs=test, source_path=Path("."))

    def proctor(program: Any) -> bool:
        if program is None:
            return False
        return all(np.array_equal(execute_program(ex.input, program), ex.output) for ex in train)

    return Hole("grid", {"task": task}, proctor)


# --- the clubs: non-inference solver lanes (a swing produces a candidate; it never scores itself) -----


@dataclass
class Club:
    name: str
    domain: str
    swing: Callable[[Dict[str, Any]], Dict[str, Any]]  # payload -> {"candidate", "strokes", maybe "family"}


def putter(maze: Any) -> Club:
    """The short game: analog_solve retrieves the best-aligned verified neighbor and grafts it. Strokes =
    graft attempts walked. Sinks a hole near a known one; abstains (no candidate) on novel structure."""

    def swing(payload: Dict[str, Any]) -> Dict[str, Any]:
        from python.scbe.analog_solve import analog_solve

        out = analog_solve(payload["problem"], payload["checks"], maze, imports=payload["imports"])
        return {"candidate": out["code"], "strokes": max(1, out["rounds_used"])}

    return Club("putter", "code", swing)


def driver() -> Club:
    """The long game: neurogolf synthesizes a straight-line move-family program from the train pairs.
    Strokes = ops in the program (the literal stroke count of the compiled micro-program)."""

    def swing(payload: Dict[str, Any]) -> Dict[str, Any]:
        sys.path.insert(0, _SRC)
        from neurogolf.solver import synthesize_program

        sol = synthesize_program(payload["task"])
        prog = getattr(sol, "program", None)
        strokes = len(prog.steps) if prog is not None else 0
        return {"candidate": prog, "strokes": max(1, strokes), "family": getattr(sol, "family", "?")}

    return Club("driver", "grid", swing)


def model_club(ask: Callable[[str], str], name: str = "model") -> Club:
    """The expensive club: a model generates code from the problem text. One stroke, highest club cost --
    used only where neither the putter nor a deterministic club reaches the hole."""

    def swing(payload: Dict[str, Any]) -> Dict[str, Any]:
        from python.helm.free_generator import strip_to_code

        return {"candidate": strip_to_code(ask(payload["problem"])), "strokes": 1}

    return Club(name, "code", swing)


# --- playing a hole: swing, let the un-steered proctor score it, seal the attributed shot -------------


def play(card: GolfCard, club: Club, hole: Hole) -> Dict[str, Any]:
    """Play one hole with one club, under the jurisdiction. The club only PRODUCES a candidate; the
    hole's proctor (the un-steered referee) scores it; the attributed shot is sealed into the card."""
    if club.domain != hole.domain:
        rec = card.record(club.name, club.domain, False, 0, "wrong club for a %s hole" % hole.domain)
        return {"club": club.name, "verified": False, "strokes": 0, "reason": "domain_mismatch", "seal": rec["seal"]}
    try:
        shot = club.swing(hole.payload)
    except Exception as exc:  # a club that blows up is a missed shot, recorded -- never hidden
        rec = card.record(club.name, club.domain, False, 0, "%s: %s" % (type(exc).__name__, exc))
        return {"club": club.name, "verified": False, "strokes": 0, "error": str(exc), "seal": rec["seal"]}
    candidate = shot.get("candidate")
    verified = bool(hole.proctor(candidate))
    detail = shot.get("family") or (str(candidate).splitlines()[0] if candidate else "no shot")
    strokes = shot.get("strokes", 1)
    rec = card.record(club.name, club.domain, verified, strokes, detail)
    return {"club": club.name, "domain": club.domain, "verified": verified, "strokes": strokes, "seal": rec["seal"]}


def render(card: GolfCard) -> str:
    lines = ["GOLF SCORECARD (one jurisdiction, every club)"]
    for s in card.scorecard():
        lines.append(
            "  %-7s %-5s %-8s strokes=%d  %s" % (s["club"], s["domain"], s["decision"], s["strokes"], s["detail"])
        )
    lines.append("  scorecard sealed: %s" % card.verify())
    return "\n".join(lines)


def demo() -> Dict[str, Any]:
    """Both clubs, one jurisdiction, honest attribution -- no model's understanding is ever credited:
    1. the PUTTER sinks a code hole near a known one (retrieval, 0 model calls);
    2. a MODEL club MISSES the same hole with wrong code -> recorded MISSED, not hidden (un-steered proctor);
    3. the DRIVER sinks a NOVEL grid hole the putter can't (neurogolf composition);
    and the whole scorecard stays sealed.
    """
    from python.scbe.analog_solve import Maze

    card = GolfCard()
    maze = Maze.from_solved(
        [
            ("add two numbers a and b", "def add(a, b):\n    return a + b", ["assert add(2, 3) == 5"]),
            ("multiply a and b", "def mul(a, b):\n    return a * b", ["assert mul(2, 3) == 6"]),
        ]
    )
    code = code_hole("sum / total of two numbers a and b", ["assert total(2, 3) == 5"])
    putt = play(card, putter(maze), code)
    miss = play(card, model_club(lambda p: "def total(a, b):\n    return a - b"), code)  # wrong on purpose
    grid = grid_hole([([[1, 2], [2, 1]], [[3, 4], [4, 3]]), ([[2, 1]], [[4, 3]])], [[[1, 2]]])
    drive = play(card, driver(), grid)
    return {
        "putter_sank_code": putt["verified"],
        "model_missed_code": not miss["verified"],
        "driver_sank_grid": drive["verified"],
        "scorecard_sealed": card.verify(),
        "card": card,
    }


def main(argv: Optional[List[str]] = None) -> int:
    out = demo()
    print(render(out["card"]))
    print()
    print(
        "putter sank code: %s | model missed (recorded): %s | driver sank novel grid: %s"
        % (out["putter_sank_code"], out["model_missed_code"], out["driver_sank_grid"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
