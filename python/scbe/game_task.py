"""game_task: a coding task IS a game -- and the function does not finish until the game is WON.

The frame (Issac's): map a coding task onto a game.
  * the RULES are the legal moves -- GOVERNANCE. You can only make allowed moves (a destructive move is
    refused, never run -- reuses the never-delete screen).
  * your MOVES are the AI's real sub-functions / tool calls -- play your STRENGTHS, route the rest.
  * the OPPONENT is the TASK ITSELF, pushing back. You WIN -- and only then does the runner return --
    when the opponent is defeated, i.e. the task is execution-verified DONE.

The load-bearing property: a function's `return` is BOUND to `opponent.is_defeated()`. You cannot report
"done" while the game isn't won -- a move that merely CLAIMS completion can't make play_until_won return;
the win-check is the gate, not trust. (This is "you don't finish until the game is done," made structural.)

Two kinds of opponent -- depends on the game:
  * STATIC -- besiege a fixed objective (build X to spec). Win = the fixed checks pass. Generalizes
    level_slice (clear the level; win checked by READING reality, not by trusting the model).
  * ADVERSARIAL -- the task FIGHTS BACK: a differential/property tester that tries to break your solution
    every turn (generate inputs, compare to a reference). Win = it runs out of breaks. The strongest
    un-fakeable "done": completion = an adversary that exhausted its attacks.

Every move is SHA-256 sealed into a golf scorecard (reuses [[analog-solve-library-lane]]'s golf.GolfCard)
-- a replayable game record. Sits on golf (hole=win=verified), run_step, and level_slice (the file-level
slice is one instance of this). See GAME_SHAPES: the game you pick IS the strength-routing decision.

    out = play_until_won("add", scripted(["def add(a,b): return a-b", "def add(a,b): return a+b"]),
                         StaticOpponent(["assert add(2, 3) == 5"]))
    out["won"], out["solution"]   # True, the winning code -- returned ONLY because the opponent was beaten
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from .desktop_access import _DESTRUCTIVE
from .golf import GolfCard

# The game you pick = the task's SHAPE = the strength-routing decision ("depends on the game").
GAME_SHAPES = {
    "go": "territory / exploration -- sparse strategic placement (architecture, layout, claim-space)",
    "chess": "one critical objective + supporting pieces (a single must-hit goal, defended)",
    "tetris": "pack / fit / commit under arrival pressure (scheduling, packing, streaming)",
    "sudoku": "pure constraint satisfaction (fill so every rule holds at once)",
    "pazaak": "value / risk counting against a target (budgets, thresholds, stop-or-push)",
    "siege": "besiege a FIXED objective -> StaticOpponent (build X to spec)",
    "duel": "the task FIGHTS BACK -> AdversarialOpponent (must survive counterexamples)",
}


def _illegal(candidate: Optional[str]) -> Optional[str]:
    """Governance: only legal moves. An empty or destructive candidate is not a legal move -- it is
    refused and never executed (reuses the canonical never-delete screen)."""
    if not candidate or not candidate.strip():
        return "empty move"
    if _DESTRUCTIVE.search(candidate):
        return "destructive op (never-delete screen)"
    return None


def _load_fn(code: str, name: str) -> Optional[Callable[..., Any]]:
    """Execute a candidate and return its named function -- screened first, so a destructive candidate is
    never run (defense in depth alongside _illegal)."""
    if _illegal(code):
        return None
    ns: Dict[str, Any] = {}
    try:
        exec(code, ns)  # noqa: S102 -- candidate is screened; controlled differential-testing surface
    except Exception:
        return None
    fn = ns.get(name)
    return fn if callable(fn) else None


# --- the opponent = the task, pushing back ----------------------------------------------------------


class StaticOpponent:
    """A fixed objective you besiege. It "attacks" by running the fixed checks; defeated when none fail."""

    def __init__(self, checks: Sequence[str], imports: Sequence[str] = ()) -> None:
        self.checks = list(checks)
        self.imports = list(imports)
        self._clean = False

    def attack(self, candidate: Optional[str]) -> Optional[str]:
        from python.helm import public_bench as pb

        if _illegal(candidate):
            self._clean = False
            return "no legal candidate"
        v = pb._verify(candidate, [], self.checks, self.imports)
        self._clean = bool(v["hidden_passed"])
        return None if self._clean else "failed the fixed checks"

    def is_defeated(self) -> bool:
        return self._clean


class AdversarialOpponent:
    """The task fights back. Each turn it generates inputs and looks for ONE where the candidate disagrees
    with a reference (differential testing) or crashes. Defeated only after a full clean sweep -- it could
    not find a single break. `gen_input(i)` returns the i-th probe input; `reference(x)` is the oracle."""

    def __init__(
        self,
        reference: Callable[[Any], Any],
        gen_input: Callable[[int], Any],
        fn_name: str = "f",
        rounds: int = 30,
    ) -> None:
        self.reference = reference
        self.gen = gen_input
        self.fn = fn_name
        self.rounds = rounds
        self._won = False

    def attack(self, candidate: Optional[str]) -> Optional[str]:
        self._won = False
        fn = _load_fn(candidate or "", self.fn)
        if fn is None:
            return "candidate did not define a legal %s" % self.fn
        for i in range(self.rounds):
            x = self.gen(i)
            try:
                got, exp = fn(x), self.reference(x)
            except Exception as exc:  # noqa: BLE001 -- a crash is the opponent finding a break
                return "crash on %r: %s: %s" % (x, type(exc).__name__, exc)
            if got != exp:
                return "counterexample %r: got %r, expected %r" % (x, got, exp)
        self._won = True  # a full sweep with no break = the adversary is defeated
        return None

    def is_defeated(self) -> bool:
        return self._won


Move = Callable[[Optional[str]], str]  # move(feedback from the opponent's last attack) -> a candidate


def scripted(attempts: Sequence[str]) -> Move:
    """A deterministic move source for demos/tests: yields the next attempt each turn (repeats the last)."""
    state = {"i": 0}

    def move(_feedback: Optional[str]) -> str:
        i = min(state["i"], len(attempts) - 1)
        state["i"] += 1
        return attempts[i]

    return move


def play_until_won(
    name: str,
    move: Move,
    opponent: Any,
    max_moves: int = 12,
    card: Optional[GolfCard] = None,
) -> Dict[str, Any]:
    """Play a task as a game. `move(feedback)` produces the AI's candidate (a real sub-function / tool /
    model output) given the opponent's last attack as feedback. Apply moves until the OPPONENT IS DEFEATED
    -- and return ONLY then. A move that claims "done" while the opponent is not defeated CANNOT make this
    return: completion is bound to opponent.is_defeated(). Every move is sealed into the scorecard."""
    card = card or GolfCard()
    feedback: Optional[str] = None
    for turn in range(1, max_moves + 1):
        candidate = move(feedback)
        bad = _illegal(candidate)
        if bad:  # an illegal move is refused, recorded, and the game continues (the move didn't happen)
            card.record(name, "task", False, turn, "ILLEGAL: " + bad)
            feedback = "illegal move: " + bad
            continue
        attack = opponent.attack(candidate)  # the opponent (the task) pushes back
        won = opponent.is_defeated()
        card.record(name, "task", won, turn, (attack or "no break found")[:120])
        if won:
            return {"won": True, "moves": turn, "solution": candidate, "card": card, "sealed": card.verify()}
        feedback = attack
    # exhausted the move budget without winning -> the function does NOT report done (solution is None)
    return {"won": False, "moves": max_moves, "solution": None, "card": card, "sealed": card.verify()}


def render(out: Dict[str, Any]) -> str:
    lines = ["GAME-TASK  (%s)" % ("WON -> done" if out["won"] else "not won -> NOT done")]
    for s in out["card"].scorecard():
        mark = "WON " if s["decision"] == "SUNK" else "...."
        lines.append("  move %d  %s  %s" % (s["strokes"], mark, s["detail"]))
    if out["won"]:
        lines.append("  solution: %s" % out["solution"].splitlines()[0])
    return "\n".join(lines)


def demo() -> Dict[str, Any]:
    """Both opponent modes, plus the load-bearing property: a 'fake done' move cannot make the runner
    return. No model -- scripted moves prove the loop."""
    # 1. SIEGE (static): besiege a fixed spec. Wrong first move, then the fix -> win on move 2.
    siege = play_until_won(
        "add",
        scripted(["def add(a, b):\n    return a - b", "def add(a, b):\n    return a + b"]),
        StaticOpponent(["assert add(2, 3) == 5", "assert add(0, 0) == 0"]),
    )
    # 2. DUEL (adversarial): the task fights back. "n > 0" looks right but the adversary finds n=-2 / n=3;
    #    the real "n % 2 == 0" survives a full sweep -> win.
    duel = play_until_won(
        "is_even",
        scripted(["def is_even(n):\n    return n > 0", "def is_even(n):\n    return n % 2 == 0"]),
        AdversarialOpponent(reference=lambda n: n % 2 == 0, gen_input=lambda i: i - 15, fn_name="is_even"),
    )
    # 3. FAKE DONE: a move that always returns wrong code "claiming" done -> the opponent is never defeated
    #    -> won=False, solution=None. Completion cannot escape the win-check.
    fake = play_until_won(
        "add",
        scripted(["def add(a, b):\n    return 999  # done!"]),
        StaticOpponent(["assert add(2, 3) == 5"]),
        max_moves=4,
    )
    return {
        "siege_won": siege["won"],
        "duel_won": duel["won"],
        "fake_done_blocked": fake["won"] is False and fake["solution"] is None,
        "all_sealed": siege["sealed"] and duel["sealed"] and fake["sealed"],
        "siege": siege,
        "duel": duel,
    }


def main(argv: Optional[List[str]] = None) -> int:
    out = demo()
    print(render(out["siege"]))
    print()
    print(render(out["duel"]))
    print()
    print(
        "siege won: %s | duel (task fought back) won: %s | fake-done blocked: %s | all sealed: %s"
        % (out["siege_won"], out["duel_won"], out["fake_done_blocked"], out["all_sealed"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
