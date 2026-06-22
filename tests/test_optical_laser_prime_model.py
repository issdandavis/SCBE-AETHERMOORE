import math

import pytest

from scripts.research.fuse_thermal_optical import fused_anchor_score
from scripts.research.optical_laser_prime_model import (
    Transition,
    apply_optical_laser,
    compute_dual_wavelength_scores,
    compute_log_transitions,
    laser_mode,
    optical_depth,
    retention_boost,
)


def test_compute_log_transitions_tracks_ratio_and_curvature():
    transitions = compute_log_transitions([2, 4, 8, 4])

    assert len(transitions) == 2
    assert transitions[0].log_r == pytest.approx(math.log(2.0))
    assert transitions[0].log_q == pytest.approx(0.0)
    assert transitions[1].log_r == pytest.approx(math.log(2.0))
    assert transitions[1].log_q == pytest.approx(math.log(4.0))


def test_optical_depth_increases_with_gradient_and_curvature():
    calm = Transition(idx=0, log_r=0.1, log_q=0.05)
    curved = Transition(idx=1, log_r=0.1, log_q=0.8)

    shallow = optical_depth(calm, [calm], cold_spot=4.0, gradient_abs=1.0)
    deeper_gradient = optical_depth(calm, [calm], cold_spot=4.0, gradient_abs=6.0)
    deeper_curvature = optical_depth(curved, [calm, curved], cold_spot=4.0, gradient_abs=1.0)

    assert deeper_gradient > shallow
    assert deeper_curvature > shallow


def test_laser_mode_switches_from_penetration_to_retention():
    assert laser_mode(0.5, d_star=1.0) == ("penetration", 0.0)

    mode, strength = laser_mode(2.0, d_star=1.0, retention_weight=0.5)
    assert mode == "retention"
    assert 0.0 < strength <= 0.95


def test_dual_wavelength_scores_are_non_negative():
    transitions = compute_log_transitions([10, 14, 18, 22, 30, 42, 50])

    scores = compute_dual_wavelength_scores(transitions[-3:], transitions[:-3], k=3)

    assert set(scores) == {"ultra", "sub"}
    assert scores["ultra"] >= 0.0
    assert scores["sub"] >= 0.0


def test_retention_boost_rewards_nearby_historical_transition():
    current = Transition(idx=9, log_r=0.3, log_q=-0.2)
    near = Transition(idx=1, log_r=0.31, log_q=-0.21)
    far = Transition(idx=2, log_r=4.0, log_q=3.0)

    boost = retention_boost(current, [far, near], top_k=1)

    assert boost > 1.9


def test_apply_optical_laser_returns_bounded_score():
    transitions = compute_log_transitions([10, 14, 18, 22, 30, 42, 50, 58, 70, 90, 110])

    score = apply_optical_laser(
        window_trans=transitions[-4:],
        historical_trans=transitions[:-4],
        cold_spot=3.0,
        gradient_abs=5.0,
    )

    assert 0.01 <= score <= 0.99


def test_fused_anchor_score_respects_weight_extremes():
    recent_gaps = [12, 18, 14, 22, 30, 28, 18, 42, 50, 36, 70, 90]
    hist_gaps = [8, 10, 14, 12, 20, 18, 30, 24, 16, 36, 42, 50] * 2

    thermal_only = fused_anchor_score(
        recent_gaps,
        hist_gaps,
        thermal_score=0.62,
        optical_weight=0.0,
    )
    optical_only = fused_anchor_score(
        recent_gaps,
        hist_gaps,
        thermal_score=0.62,
        optical_weight=1.0,
    )
    blended = fused_anchor_score(
        recent_gaps,
        hist_gaps,
        thermal_score=0.62,
        optical_weight=0.35,
    )

    assert thermal_only == pytest.approx(0.62)
    assert 0.01 <= optical_only <= 0.99
    assert min(thermal_only, optical_only) <= blended <= max(thermal_only, optical_only)
