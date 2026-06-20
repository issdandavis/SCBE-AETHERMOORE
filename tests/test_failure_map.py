"""failure_map: aggregate stepwise runs into the capability basement -- WHERE a model drifts
(point 1 -> point F) and, across models, WHICH step is the wall. Pass/fail becomes where-and-why."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.failure_map import clears_through, localize, render_map, run_map, seq_task  # noqa: E402


def test_localize_finds_the_drift_point():
    task = seq_task("t", ["a1", "a2", "a3", "a4"])
    r = localize(task, clears_through(2))  # correct through s2, drifts at s3
    assert r["cleared"] is False
    assert r["stuck_at"] == "s3" and r["stuck_index"] == 2 and r["total"] == 4


def test_clearing_model_reaches_the_end():
    task = seq_task("t", ["a1", "a2", "a3"])
    r = localize(task, clears_through(9))
    assert r["cleared"] is True and r["stuck_index"] == r["total"] == 3


def test_cross_model_who_clears_what():
    tasks = [seq_task("alpha", ["a1", "a2", "a3"]), seq_task("beta", ["b1", "b2"])]
    m = run_map(tasks, {"strong": clears_through(9), "mid": clears_through(2), "weak": clears_through(0)})
    assert m["per_task"]["alpha"]["clearers"] == ["strong"]  # only strong clears the 3-step task
    assert sorted(m["per_task"]["beta"]["clearers"]) == ["mid", "strong"]  # mid clears the 2-step one
    assert m["cells"][("mid", "alpha")]["stuck_at"] == "s3"  # mid's edge sits at alpha.s3
    assert m["cells"][("weak", "beta")]["stuck_at"] == "s1"


def test_universal_fail_names_the_wall():
    # a task whose correct answer is never in the options -> no model can clear it; the wall is s1
    impossible = seq_task("impossible", ["a1", "a2"])
    impossible.steps[0].check = lambda st, v: v == "unreachable"  # never legal+correct
    m = run_map([impossible], {"strong": clears_through(9), "weak": clears_through(0)})
    assert m["universal_fail"] == ["impossible"]
    assert m["per_task"]["impossible"]["wall"] == "s1"
    assert m["per_task"]["impossible"]["no_clearers"] is True


def test_render_shows_drift_markers_and_universal_fail():
    tasks = [seq_task("alpha", ["a1", "a2"])]
    out = render_map(run_map(tasks, {"weak": clears_through(0)}))
    assert "FAILURE MAP" in out
    assert "@s1" in out  # weak drifts at the first step
