import math

import numpy as np

from src.polly_pump.dual_overlay import (
    BallSpec,
    DualOverlayConfig,
    NEG_ZERO_FREEZE,
    OverlayAction,
    project_dual_state,
    verify_dual_overlay,
)


def _state_with_caches(seed: int = 123) -> np.ndarray:
    rng = np.random.default_rng(seed)

    u = rng.normal(0.0, 0.08, size=6)
    u = u / max(1.0, np.linalg.norm(u) / 0.45)
    theta = rng.uniform(-math.pi, math.pi, size=6)
    telemetry = np.array([0.3, 0.91, 0.88, 0.86, 0.22, 0.15, 0.74], dtype=float)
    radial = float(np.linalg.norm(u))
    harmonic = float((1.0 / max(1e-12, 1.0 - radial)) ** 36)
    return np.concatenate([u, theta, telemetry, np.array([radial, harmonic], dtype=float)])


def test_project_dual_state_returns_ball_points_inside_unit_ball():
    state = _state_with_caches()
    a, b = project_dual_state(state)
    assert np.linalg.norm(a.point) < 1.0
    assert np.linalg.norm(b.point) < 1.0
    assert a.in_trust_region is True
    assert b.in_trust_region is True


def test_verify_dual_overlay_accepts_stable_state():
    state = _state_with_caches()
    result = verify_dual_overlay(state)
    assert result.accepted is True
    assert result.action is OverlayAction.ALLOW
    assert result.loop_a.passed is True
    assert result.loop_b.passed is True
    assert result.dual_loop_match is True


def test_verify_dual_overlay_quarantines_when_one_ball_misses_trust_region():
    state = _state_with_caches()
    config = DualOverlayConfig(
        ball_a=BallSpec(name="governance_geo", indices=(0, 1, 2, 3, 4, 5), trust_radius=1.5),
        ball_b=BallSpec(
            name="semantic_spectral",
            indices=(6, 7, 8, 9, 10, 11),
            angle_indices=(6, 7, 8, 9, 10, 11),
            alpha=0.35,
            trust_radius=0.1,
        ),
        delta_match_tolerance=0.2,
    )
    result = verify_dual_overlay(state, config=config)
    assert result.accepted is False
    assert result.action is OverlayAction.QUARANTINE
    assert result.ball_b.in_trust_region is False


def test_neg_zero_freeze_projects_and_holds():
    state = _state_with_caches()
    config = DualOverlayConfig(
        ball_a=BallSpec(name="governance_geo", indices=(0, 1, 2, 3, 4, 5), trust_radius=0.2),
        ball_b=BallSpec(
            name="semantic_spectral",
            indices=(6, 7, 8, 9, 10, 11),
            angle_indices=(6, 7, 8, 9, 10, 11),
            alpha=0.35,
            trust_radius=0.2,
        ),
    )
    result = verify_dual_overlay(state, config=config, control_symbol=NEG_ZERO_FREEZE)
    assert result.action is OverlayAction.HOLD
    assert result.requires_quorum_exit is True
    assert result.ball_a.in_trust_region is True
    assert result.ball_b.in_trust_region is True
