"""golf: one jurisdiction over two non-inference clubs (putter=analog_solve, driver=neurogolf).

These prove the keystone: a hole is sunk by a CLUB, scored by an UN-STEERED proctor (execution for code,
exact train-match for grids -- never a held-out label), and sealed into a scorecard that credits the
club, not a model. The putter sinks a near hole; a wrong model MISSES and is recorded (not hidden); the
driver sinks a NOVEL grid the putter can't reach; the chain stays sealed and is tamper-evident.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))  # so the driver's `import neurogolf` resolves

from python.scbe.analog_solve import Maze  # noqa: E402
from python.scbe.golf import (  # noqa: E402
    GolfCard,
    code_hole,
    demo,
    driver,
    grid_hole,
    model_club,
    play,
    putter,
)


def _code_maze():
    return Maze.from_solved(
        [("add two numbers a and b", "def add(a, b):\n    return a + b", ["assert add(2, 3) == 5"])]
    )


def test_putter_sinks_a_near_code_hole_and_is_attributed():
    card = GolfCard()
    r = play(card, putter(_code_maze()), code_hole("sum / total of two numbers a and b", ["assert total(2, 3) == 5"]))
    assert r["verified"] is True and r["club"] == "putter"
    assert card.scorecard()[-1]["decision"] == "SUNK" and card.verify() is True


def test_wrong_model_misses_and_is_recorded_not_hidden():
    card = GolfCard()
    hole = code_hole("total of two numbers", ["assert total(2, 3) == 5"])
    r = play(card, model_club(lambda p: "def total(a, b):\n    return a - b"), hole)  # wrong code
    assert r["verified"] is False
    assert card.scorecard()[-1]["decision"] == "MISSED" and card.verify() is True  # caught by the proctor, sealed


def test_driver_sinks_a_novel_grid_hole_via_neurogolf():
    card = GolfCard()
    # a color-remap ARC hole: 1->3, 2->4. The putter (code retrieval) could never reach this; the driver does.
    hole = grid_hole([([[1, 2], [2, 1]], [[3, 4], [4, 3]]), ([[2, 1]], [[4, 3]])], [[[1, 2]]])
    r = play(card, driver(), hole)
    assert r["verified"] is True and r["club"] == "driver" and r["domain"] == "grid"
    assert r["strokes"] >= 1 and card.verify() is True


def test_wrong_club_for_the_domain_is_a_recorded_miss():
    card = GolfCard()
    grid = grid_hole([([[1, 2]], [[3, 4]])], [[[2, 1]]])
    r = play(card, putter(_code_maze()), grid)  # a putter on a grid hole
    assert r["verified"] is False and r["reason"] == "domain_mismatch"
    assert card.scorecard()[-1]["decision"] == "MISSED"


def test_scorecard_is_tamper_evident():
    card = GolfCard()
    play(card, putter(_code_maze()), code_hole("total two numbers", ["assert total(2, 3) == 5"]))
    assert card.verify() is True
    card.scorecard()[0]["club"] = "forged"
    assert card.verify() is False


def test_demo_runs_both_clubs_under_one_seal():
    out = demo()
    assert out["putter_sank_code"] is True
    assert out["model_missed_code"] is True
    assert out["driver_sank_grid"] is True
    assert out["scorecard_sealed"] is True
