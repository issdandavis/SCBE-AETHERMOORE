"""Correctness and integrity tests for the fixed untrained canvas probe."""

from __future__ import annotations

from dataclasses import replace

import pytest

from src.crypto import frozen_neural_canvas as C


def basis(width: int) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(index == active) for index in range(width)) for active in range(width))


def test_canvas_is_deterministic_frozen_and_seed_separated() -> None:
    first = C.build_canvas(8, (12, 10), seed=17)
    second = C.build_canvas(8, (12, 10), seed=17)
    other = C.build_canvas(8, (12, 10), seed=18)
    assert first == second
    assert first != other
    assert first.weight_sha256 == second.weight_sha256
    assert first.weight_sha256 != other.weight_sha256
    assert all(value in C.TRITS for layer in first.layers for row in layer.weights for value in row)
    assert all(value in C.TRITS for layer in first.layers for value in layer.biases)


def test_identity_and_clipped_canvases_share_weights_but_not_response_contract() -> None:
    linear = C.build_canvas(5, (7, 6), seed=8, activation="identity")
    clipped = C.build_canvas(5, (7, 6), seed=8, activation="clip", clip_limit=3)
    assert linear.layers == clipped.layers
    assert linear.weight_sha256 == clipped.weight_sha256
    assert linear.canvas_sha256 != clipped.canvas_sha256
    assert C.forward(linear, (9, -8, 7, -6, 5)) != C.forward(clipped, (9, -8, 7, -6, 5))


def test_projection_returns_every_exact_integer_layer() -> None:
    canvas = C.build_canvas(4, (6, 5, 3), seed=91, clip_limit=11)
    response = C.forward(canvas, (8, -5, 3, 1))
    assert tuple(len(layer) for layer in response) == canvas.layer_widths
    assert all(type(value) is int for layer in response for value in layer)
    assert all(abs(value) <= canvas.clip_limit for layer in response for value in layer)


@pytest.mark.parametrize("activation", ["identity", "clip"])
def test_trajectory_records_every_affine_interaction_and_bounded_state(
    activation: str,
) -> None:
    canvas = C.build_canvas(4, (6, 3), seed=92, activation=activation, clip_limit=4)
    origin = (8, -5, 3, 1)
    trajectory = C.trace_forward(canvas, origin)
    assert trajectory.origin == origin
    assert trajectory.states == C.forward(canvas, origin)
    assert trajectory.terminal == trajectory.states[-1]

    current = origin
    for layer_index, transition in enumerate(trajectory.transitions):
        layer = canvas.layers[layer_index]
        affine = tuple(
            bias + sum(weight * value for weight, value in zip(row, current, strict=True))
            for row, bias in zip(layer.weights, layer.biases, strict=True)
        )
        state = (
            tuple(max(-canvas.clip_limit, min(canvas.clip_limit, value)) for value in affine)
            if activation == "clip"
            else affine
        )
        assert transition.layer == layer_index
        assert transition.source == current
        assert transition.affine == affine
        assert transition.state == state
        assert transition.clipped_nodes == sum(left != right for left, right in zip(affine, state, strict=True))
        current = state


def test_fixed_probe_evaluates_every_declared_direction_once() -> None:
    canvas = C.build_canvas(6, (9, 8), seed=23, clip_limit=7)
    directions = basis(6)
    receipt = C.probe_offsets(canvas, (3, -2, 1, 0, 4, -1), directions)
    assert receipt.mode == "fixed-complete-probe-bank"
    assert receipt.directions == directions
    assert receipt.forward_calls == 1 + 2 * len(directions)
    assert len(receipt.responses) == len(directions)
    assert receipt.schema == "scbe.frozen-neural-canvas-probe.v2"
    assert receipt.baseline_trajectory.origin == (3, -2, 1, 0, 4, -1)
    assert all(
        response.positive_trajectory.origin != response.negative_trajectory.origin for response in receipt.responses
    )
    assert C.verify_receipt(receipt)


def test_dual_trits_are_exact_signs_of_slope_and_curvature() -> None:
    canvas = C.build_canvas(4, (8, 7), seed=29, clip_limit=5)
    receipt = C.probe_offsets(canvas, (4, -3, 2, 1), basis(4))
    for response in receipt.responses:
        for slopes, curvatures, states in zip(
            response.first_differences,
            response.second_differences,
            response.dual_trit_states,
            strict=True,
        ):
            expected = tuple(
                ((slope > 0) - (slope < 0), (curve > 0) - (curve < 0))
                for slope, curve in zip(slopes, curvatures, strict=True)
            )
            assert states == expected
            assert all(state in C.DUAL_TRIT_STATES for state in states)


def test_linear_canvas_has_zero_central_curvature() -> None:
    canvas = C.build_canvas(5, (9, 7, 6), seed=31, activation="identity")
    receipt = C.probe_offsets(canvas, (5, -4, 3, -2, 1), basis(5))
    assert all(summary.curvature_rank == 0 for summary in receipt.layer_summaries)
    assert all(summary.nonzero_curvature_values == 0 for summary in receipt.layer_summaries)


def test_saturating_canvas_exposes_nonlinear_node_response() -> None:
    canvas = C.build_canvas(5, (9, 7, 6), seed=31, activation="clip", clip_limit=5)
    receipt = C.probe_offsets(canvas, (5, -4, 3, -2, 1), basis(5))
    assert any(summary.curvature_rank > 0 for summary in receipt.layer_summaries)
    assert any(summary.nonzero_curvature_values > 0 for summary in receipt.layer_summaries)


def test_probe_triplets_supports_a_different_mathematical_label_width() -> None:
    canvas = C.build_canvas(7, (8,), seed=44)
    labels = basis(3)
    positives = ((1, 2, 3, 4, 5, 6, 7), (2, 3, 4, 5, 6, 7, 8), (3, 4, 5, 6, 7, 8, 9))
    negatives = tuple(tuple(-value for value in row) for row in positives)
    receipt = C.probe_triplets(canvas, (0,) * 7, labels, positives, negatives)
    assert receipt.directions == labels
    assert receipt.forward_calls == 7


def test_exact_rank_has_no_tolerance_or_floating_point_decision() -> None:
    assert C.exact_rank([]) == 0
    assert C.exact_rank(((1, 2, 3), (2, 4, 6), (0, 1, 0))) == 2
    assert C.exact_rank(((10**30, 1), (10**30 + 1, 1))) == 2


def test_receipt_hash_detects_response_or_mode_changes() -> None:
    canvas = C.build_canvas(4, (7,), seed=51)
    receipt = C.probe_offsets(canvas, (1, 2, 3, 4), basis(4))
    assert C.verify_receipt(receipt)
    assert not C.verify_receipt(replace(receipt, forward_calls=receipt.forward_calls + 1))
    assert not C.verify_receipt(replace(receipt, mode="adaptive"))


def test_declared_goal_projects_over_all_fixed_rays_at_every_layer() -> None:
    canvas = C.build_canvas(4, (7, 3), seed=52, clip_limit=5)
    receipt = C.probe_offsets(canvas, (4, -3, 2, 1), basis(4))
    coefficients = (2, -1, 0, 3)
    goal = C.project_goal_response(receipt, coefficients)

    assert goal.goal_coefficients == coefficients
    assert goal.probe_receipt_sha256 == receipt.receipt_sha256
    assert tuple(arrow.nodes for arrow in goal.layer_arrows) == canvas.layer_widths
    for layer_index, arrow in enumerate(goal.layer_arrows):
        expected_slope = tuple(
            sum(
                coefficients[direction] * receipt.responses[direction].first_differences[layer_index][node]
                for direction in range(len(coefficients))
            )
            for node in range(arrow.nodes)
        )
        expected_curvature = tuple(
            sum(
                coefficients[direction] * receipt.responses[direction].second_differences[layer_index][node]
                for direction in range(len(coefficients))
            )
            for node in range(arrow.nodes)
        )
        assert arrow.slope == expected_slope
        assert arrow.curvature == expected_curvature
        assert arrow.slope_squared_length == sum(value * value for value in expected_slope)
        assert arrow.curvature_squared_length == sum(value * value for value in expected_curvature)
    assert goal.terminal_slope == goal.layer_arrows[-1].slope
    assert goal.terminal_curvature == goal.layer_arrows[-1].curvature
    assert C.verify_goal_receipt(goal)
    assert not C.verify_goal_receipt(replace(goal, terminal_slope=goal.terminal_slope[:-1]))


def test_goal_projection_rejects_a_missing_goal_or_tampered_probe_receipt() -> None:
    canvas = C.build_canvas(3, (5,), seed=53)
    receipt = C.probe_offsets(canvas, (1, 2, 3), basis(3))
    with pytest.raises(ValueError, match="contain a direction"):
        C.project_goal_response(receipt, (0, 0, 0))
    with pytest.raises(ValueError, match="exactly 3 integers"):
        C.project_goal_response(receipt, (1, 0))
    with pytest.raises(ValueError, match="intact"):
        C.project_goal_response(replace(receipt, forward_calls=0), (1, 0, 0))


def test_bounded_canvas_rejects_excessive_depth_or_weight_count() -> None:
    with pytest.raises(ValueError, match="depth"):
        C.build_canvas(1, (1,) * 17, seed=1)
    with pytest.raises(ValueError, match="weight count"):
        C.build_canvas(1_001, (1_000,), seed=1)


def test_forward_rejects_tampered_frozen_canvas_shapes_or_activation() -> None:
    canvas = C.build_canvas(3, (4,), seed=72)
    layer = canvas.layers[0]
    malformed = (
        replace(canvas, layers=()),
        replace(canvas, layers=(replace(layer, biases=layer.biases[:-1]),)),
        replace(
            canvas,
            layers=(replace(layer, weights=(layer.weights[0][:-1], *layer.weights[1:])),),
        ),
        replace(canvas, activation="changed-after-construction"),
    )
    for item in malformed:
        with pytest.raises(ValueError):
            C.forward(item, (1, 2, 3))


@pytest.mark.parametrize(
    "call",
    [
        lambda: C.build_canvas(0, (3,), seed=1),
        lambda: C.build_canvas(3, (), seed=1),
        lambda: C.build_canvas(3, (2,), seed=-1),
        lambda: C.build_canvas(3, (2,), seed=1, activation="relu"),
        lambda: C.build_canvas(3, (2,), seed=1, clip_limit=0),
        lambda: C.exact_rank(((1, 2), (3,))),
        lambda: C.exact_rank(((1, 2.0),)),
    ],
)
def test_invalid_canvas_or_rank_inputs_fail_closed(call) -> None:
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize(
    "directions",
    [
        (),
        ((0, 0, 0),),
        ((1, 0, 0), (1, 0, 0)),
        ((1, 0), (0, 1, 0)),
    ],
)
def test_invalid_probe_banks_are_rejected_before_a_receipt(directions) -> None:
    canvas = C.build_canvas(3, (5,), seed=62)
    values = tuple((1, 2, 3) for _ in directions)
    with pytest.raises(ValueError):
        C.probe_triplets(canvas, (0, 0, 0), directions, values, values)
