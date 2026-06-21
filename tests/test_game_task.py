"""game_task: a coding task IS a game; the function returns ONLY when the game is won (= verified done).

These pin the load-bearing property -- a move that merely CLAIMS done cannot make play_until_won return,
because completion is bound to opponent.is_defeated() -- plus both opponent kinds (static siege and the
adversarial "task fights back"), legal-move governance, and the sealed game record.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.game_task import (  # noqa: E402
    AdversarialOpponent,
    StaticOpponent,
    demo,
    play_until_won,
    scripted,
)


def test_siege_static_opponent_returns_only_on_the_fix():
    out = play_until_won(
        "add",
        scripted(["def add(a, b):\n    return a - b", "def add(a, b):\n    return a + b"]),
        StaticOpponent(["assert add(2, 3) == 5", "assert add(0, 0) == 0"]),
    )
    assert out["won"] is True and out["moves"] == 2  # lost move 1 (a-b), won move 2 (a+b)
    assert "a + b" in out["solution"] and out["sealed"] is True


def test_duel_adversarial_opponent_makes_the_task_fight_back():
    # "n > 0" passes a naive eye but the adversary finds a counterexample; "n % 2 == 0" survives a sweep.
    out = play_until_won(
        "is_even",
        scripted(["def is_even(n):\n    return n > 0", "def is_even(n):\n    return n % 2 == 0"]),
        AdversarialOpponent(reference=lambda n: n % 2 == 0, gen_input=lambda i: i - 15, fn_name="is_even"),
    )
    assert out["won"] is True and "n % 2 == 0" in out["solution"]


def test_a_move_that_only_CLAIMS_done_cannot_make_it_return():
    # the whole point: a wrong candidate that "claims" done never defeats the opponent -> no return of done
    out = play_until_won(
        "add",
        scripted(["def add(a, b):\n    return 999  # done!"]),
        StaticOpponent(["assert add(2, 3) == 5"]),
        max_moves=5,
    )
    assert out["won"] is False and out["solution"] is None  # completion cannot escape the win-check


def test_adversarial_opponent_rejects_a_plausible_but_wrong_solution_forever():
    # a solution that's wrong only on inputs the adversary will probe (negatives) never wins
    out = play_until_won(
        "is_even",
        scripted(["def is_even(n):\n    return n > 0"]),  # only ever offers the wrong one
        AdversarialOpponent(reference=lambda n: n % 2 == 0, gen_input=lambda i: i - 15, fn_name="is_even"),
        max_moves=4,
    )
    assert out["won"] is False and out["solution"] is None


def test_empty_oracle_cannot_certify_a_win():
    # the vacuous-pass hole the adversarial review found: an EMPTY StaticOpponent must never certify code
    out = play_until_won("add", scripted(["def add(a, b):\n    return 0  # anything"]), StaticOpponent([]), max_moves=3)
    assert out["won"] is False and out["solution"] is None


def test_illegal_destructive_move_is_refused_not_run():
    # a destructive candidate is not a legal move -> refused, recorded, never executed; the game continues
    out = play_until_won(
        "x",
        scripted(["import shutil\nshutil.rmtree('/x')\ndef add(a, b):\n    return a + b"]),
        StaticOpponent(["assert add(2, 3) == 5"]),
        max_moves=3,
    )
    assert out["won"] is False  # the only move offered was illegal, so the task was never solved
    assert any("ILLEGAL" in s["detail"] for s in out["card"].scorecard())


def test_demo_shows_both_modes_and_the_fake_done_block():
    out = demo()
    assert out["siege_won"] is True
    assert out["duel_won"] is True
    assert out["fake_done_blocked"] is True
    assert out["all_sealed"] is True
