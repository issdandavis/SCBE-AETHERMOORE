"""game_board: a task is a board game -- rules are the walls, moves are sealed, winning is the work.

One recursive Game protocol: TicTacToe proves the protocol on a real game; Task is a leaf whose win
fires a governed action; Field is a field of mini-games that is itself a Game, so fields nest into the
cube. These tests prove the rules hold (illegal moves refused), the work happens (files normalized),
every move is sealed + reversibly recorded, and the nesting (a Field of Fields) clears.
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.game_board import (  # noqa: E402
    Field,
    Task,
    TicTacToe,
    add_move_action,
    file_field,
    play_governed,
)
from python.scbe.level_slice import build_registry  # noqa: E402

FILES = ["Draft One.tmp", "report.tmp", "NOTES final.tmp"]


def _ok_task(name: str) -> Task:
    """A leaf whose win records an ALLOWED receipt without touching the filesystem."""
    return Task(name=name, target="go", on_solve=lambda mv: {"decision": "ALLOWED"})


def test_tictactoe_rules_and_win_detection():
    g = TicTacToe()
    assert set(g.legal_moves()) == {str(i) for i in range(9)}
    for m in ["0", "3", "1", "4", "2"]:  # X: 0,1,2 (top row) ; O: 3,4
        g.play(m)
    assert g.over() is True
    assert g.won() is True  # X completed the top row


def test_illegal_move_is_refused_by_the_referee():
    g = TicTacToe()
    assert g.play("0") is True
    assert g.play("0") is False  # occupied -> not a legal move
    assert g.play("9") is False  # off the board
    # play_governed stops honestly on an illegal move, never fakes a win
    res = play_governed(g, player=lambda _g: "9")
    assert any(t["status"] == "ILLEGAL" for t in res["transcript"])
    assert res["won"] is False


def test_governed_game_is_sealed_and_reversible():
    res = play_governed(TicTacToe())
    assert res["over"] is True
    assert res["sealed"] is True  # every committed move is tamper-evident
    assert res["reversible"] is True  # the move record replays losslessly off the cube


def test_task_leaf_wins_only_on_the_correct_move():
    fired = {}

    def record(mv):
        fired["mv"] = mv
        return {"decision": "ALLOWED"}

    t = Task(name="x", target="right", on_solve=record)
    assert t.play("wrong") is False  # outside the wall -> refused, no action
    assert "mv" not in fired
    assert t.play("right") is True
    assert fired["mv"] == "right"  # the winning move fired the governed action
    assert t.won() is True


def test_a_field_of_games_does_real_work_and_wins():
    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td)
        for f in FILES:
            (sandbox / f).write_text("x", encoding="utf-8")
        reg = add_move_action(build_registry(sandbox))
        fld = file_field(FILES, reg)
        res = play_governed(fld, reg=reg)
        assert res["over"] is True
        assert res["won"] is True  # every cell did its governed work
        assert sorted(p.name for p in sandbox.iterdir()) == ["draft-one.bak", "notes-final.bak", "report.bak"]
        assert res["sealed"] is True  # moves AND renames sealed in one transcript
        assert len(fld.addresses()) == 3  # cells addressed on the cube


def test_fields_nest_a_field_of_fields_clears():
    # the cube-face shape: a Field whose cells are themselves Fields of mini-games, one recursive loop
    inner_a = Field([_ok_task("a1"), _ok_task("a2")], name="face-a")
    inner_b = Field([_ok_task("b1")], name="face-b")
    cube = Field([inner_a, inner_b], name="cube")
    res = play_governed(cube)
    assert res["over"] is True
    assert res["won"] is True  # the whole nested structure cleared through one driver
    assert cube.won() is True


def test_a_field_is_a_game():
    # structural: Field exposes the same surface as TicTacToe (so it composes anywhere a Game is taken)
    fld = Field([_ok_task("x")])
    for attr in ("legal_moves", "play", "over", "won", "render"):
        assert hasattr(fld, attr)


def test_empty_field_is_not_won():
    assert Field([]).won() is False  # nothing cleared is not a win
