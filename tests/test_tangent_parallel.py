"""Tests for tangential parallelism — bounded divergence around the prime line."""

import pytest

from python.scbe import geometric_router as gr
from python.scbe import tangent_parallel as tp


def _line():
    return tp.prime_line({"KO": 1.0, "AV": 0.5}, {"DR": 1.0})


def test_prime_line_endpoints():
    line = _line()
    # the keel's last sample is essentially the goal point in the ball
    goal_ball = gr.to_ball(gr.to_vec({"DR": 1.0}))
    assert gr.poincare_distance(line.samples[-1], goal_ball) < 1e-3
    assert len(line.samples) == 25  # steps=24 -> 25 samples


def test_divergence_goal_is_on_keel_offaxis_is_not():
    line = _line()
    d_goal = tp.divergence({"DR": 1.0}, line)
    d_off = tp.divergence({"CA": 1.0}, line)
    assert d_goal < 1e-3  # the goal sits on the keel
    assert d_off > d_goal  # an orthogonal tongue drifts off it


def test_grain_alignment_with_and_against_the_keel():
    line = _line()
    # a point further along the goal direction runs with the grain (~1)
    assert tp.grain_alignment({"DR": 1.0}, line) > 0.9
    # an off-axis tongue is less aligned than the goal direction
    assert tp.grain_alignment({"CA": 1.0}, line) < tp.grain_alignment({"DR": 1.0}, line)
    assert -1.0 <= tp.grain_alignment({"UM": 1.0}, line) <= 1.0


def test_reproject_pulls_strayed_point_within_bound():
    line = _line()
    res = tp.reproject({"CA": 1.0, "UM": 1.0}, line, max_divergence=0.05)
    assert res["reprojected"] is True
    assert res["after"] <= 0.05 + 1e-3
    assert res["after"] < res["before"]


def test_reproject_leaves_aligned_point_untouched():
    line = _line()
    res = tp.reproject({"DR": 1.0}, line, max_divergence=1.0)
    assert res["reprojected"] is False
    assert res["before"] == res["after"]


def test_plan_bounds_divergence_and_assigns_all_tasks():
    agents = [gr.Agent("a-ko", {"KO": 1.0}), gr.Agent("a-av", {"AV": 1.0})]
    tasks = [
        gr.Task("t1", {"DR": 1.0}),
        gr.Task("t2", {"CA": 1.0, "UM": 1.0}),
        gr.Task("t3", {"KO": 1.0}),
    ]
    p = tp.plan(agents, tasks, {"DR": 1.0}, max_divergence=0.3, nodes=2)
    assert len(p.tracks) == 2
    assert -1.0 <= p.grain_alignment <= 1.0
    assert p.max_divergence <= 0.3 + 1e-3  # every drift planed back to the bound
    assert len(p.node_points) == 3  # nodes=2 -> 3 keel checkpoints (incl. bow + stern)
    assigned = sorted(t for tr in p.tracks for t in tr.tasks)
    assert assigned == ["t1", "t2", "t3"]


def test_plan_records_reprojections_when_bound_is_tight():
    agents = [gr.Agent("solo", {"KO": 1.0})]
    tasks = [gr.Task("far", {"CA": 1.0, "UM": 1.0}), gr.Task("near", {"DR": 1.0})]
    p = tp.plan(agents, tasks, {"DR": 1.0}, max_divergence=0.02, nodes=1)
    assert p.tracks[0].reprojected >= 1  # the far task had to be planed back
    assert p.tracks[0].raw_divergence >= p.tracks[0].divergence


def test_plan_rejects_empty_fleet():
    with pytest.raises(ValueError):
        tp.plan([], [gr.Task("t", {"DR": 1.0})], {"DR": 1.0})


def test_node_points_scale_with_node_count():
    line = _line()
    assert len(tp._node_points(line, 1)) == 2
    assert len(tp._node_points(line, 4)) == 5
