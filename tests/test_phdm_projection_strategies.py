from __future__ import annotations

import json

import numpy as np
import pytest

from python.scbe.phdm_embedding import PoincareBall


def test_primary_clamp_behavior_remains_unchanged() -> None:
    ball = PoincareBall()
    projected = ball.embed(np.array([2.0, 0.0, 0.0, 0.0, 0.0, 0.0]))

    assert projected.tolist() == [0.99999, 0.0, 0.0, 0.0, 0.0, 0.0]


@pytest.mark.parametrize("depth", [0.0, 1.0, 2.0, 3.0, 4.0, 10.0, 20.0])
def test_n_bounded_projection_recovers_representable_depth(depth: float) -> None:
    ball = PoincareBall()
    projected, record = ball.project(
        np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
        strategy="n_bounded",
        depth=depth,
    )

    expected_radius = np.tanh(depth / 2.0)
    assert np.linalg.norm(projected) == pytest.approx(expected_radius, abs=2e-15)
    assert record["hyperbolic_distance_from_origin"] == pytest.approx(depth, abs=1e-7)
    assert record["depth_requested"] == depth
    assert record["depth_applied"] is True
    assert record["strategy_fired"] == "n_bounded"
    assert record["is_primary"] is False


def test_n_bounded_origin_is_valid_only_at_zero_depth() -> None:
    ball = PoincareBall()

    projected = ball.embed_n_bounded(np.zeros(6), depth=0.0)
    assert np.array_equal(projected, np.zeros(6))

    with pytest.raises(ValueError, match="non-zero direction"):
        ball.embed_n_bounded(np.zeros(6), depth=1.0)


@pytest.mark.parametrize("depth", [-1.0, np.nan, np.inf, -np.inf, None])
def test_n_bounded_rejects_invalid_depth(depth: float | None) -> None:
    ball = PoincareBall()

    with pytest.raises(ValueError, match="depth"):
        ball.embed_n_bounded(np.ones(6), depth=depth)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "vector",
    [
        np.array([np.nan, 0.0, 0.0, 0.0, 0.0, 0.0]),
        np.array([np.inf, 0.0, 0.0, 0.0, 0.0, 0.0]),
    ],
)
def test_n_bounded_rejects_non_finite_vectors(vector: np.ndarray) -> None:
    ball = PoincareBall()

    with pytest.raises(ValueError, match="finite"):
        ball.embed_n_bounded(vector, depth=2.0)


def test_n_bounded_rejects_depth_that_rounds_to_boundary() -> None:
    ball = PoincareBall()

    with pytest.raises(ValueError, match="not representable"):
        ball.embed_n_bounded(np.ones(6), depth=38.0)


def test_projection_receipts_are_json_serializable_and_label_legacy_gate() -> None:
    ball = PoincareBall()
    _, primary = ball.project(np.ones(6), strategy="clamp")
    _, alternative = ball.project(np.ones(6), strategy="n_bounded", depth=4.0)

    json.dumps(primary, allow_nan=False)
    json.dumps(alternative, allow_nan=False)

    assert primary["clamped_at_boundary"] is True
    assert primary["depth_requested"] is None
    assert primary["depth_applied"] is False
    assert (
        alternative["harmonic_profile"] == "PHDM_LEGACY_RADIAL_POWER_GATE_UNREGISTERED"
    )


def test_unknown_projection_strategy_fails_closed() -> None:
    ball = PoincareBall()

    with pytest.raises(ValueError, match="primary='clamp'.*n_bounded"):
        ball.project(np.ones(6), strategy="not-a-strategy")
