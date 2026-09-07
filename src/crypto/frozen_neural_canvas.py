"""Fixed-probe response map for an untrained exact-integer neural canvas.

The canvas is instrumentation, not an agent and not a cryptographic primitive.
Its weights are deterministically initialized, then frozen.  A caller supplies
the complete probe bank before execution.  Every baseline, positive probe, and
negative probe is evaluated exactly once and retained in the receipt.

For each node and probe direction, the response stores a dual trit:

* first trit: sign of the central first difference (slope);
* second trit: sign of the central second difference (curvature).

The exact integer differences remain available beside their signs.  No
optimizer, learned readout, callback, or adaptive probe selector exists here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from fractions import Fraction
import hashlib
import json
from typing import Sequence

from src.symphonic_cipher.scbe_aethermoore.ai_brain.dual_ternary import FULL_STATE_SPACE

DOMAIN = b"SCBE/FROZEN-NEURAL-CANVAS/v1"
TRITS = (-1, 0, 1)
DUAL_TRIT_STATES = tuple((state.primary, state.mirror) for state in FULL_STATE_SPACE)
MAX_TOTAL_WEIGHTS = 1_000_000

Vector = tuple[int, ...]
Matrix = tuple[Vector, ...]
DualTrit = tuple[int, int]


@dataclass(frozen=True)
class CanvasLayer:
    weights: Matrix
    biases: Vector


@dataclass(frozen=True)
class FrozenCanvas:
    seed: int
    input_width: int
    layer_widths: tuple[int, ...]
    activation: str
    clip_limit: int
    layers: tuple[CanvasLayer, ...]
    weight_sha256: str
    canvas_sha256: str


@dataclass(frozen=True)
class CanvasLayerTransition:
    """One typed segment of a response path through the frozen canvas."""

    layer: int
    source: Vector
    affine: Vector
    state: Vector
    clipped_nodes: int


@dataclass(frozen=True)
class CanvasTrajectory:
    """Ordered origin-to-terminal path; each transition keeps its own width."""

    origin: Vector
    transitions: tuple[CanvasLayerTransition, ...]
    terminal: Vector

    @property
    def states(self) -> tuple[Vector, ...]:
        return tuple(transition.state for transition in self.transitions)


@dataclass(frozen=True)
class DirectionResponse:
    direction: Vector
    positive_trajectory: CanvasTrajectory
    negative_trajectory: CanvasTrajectory
    first_differences: tuple[Vector, ...]
    second_differences: tuple[Vector, ...]
    dual_trit_states: tuple[tuple[DualTrit, ...], ...]

    @property
    def positive_layers(self) -> tuple[Vector, ...]:
        return self.positive_trajectory.states

    @property
    def negative_layers(self) -> tuple[Vector, ...]:
        return self.negative_trajectory.states


@dataclass(frozen=True)
class LayerProbeSummary:
    layer: int
    nodes: int
    slope_rank: int
    curvature_rank: int
    nonzero_slope_values: int
    nonzero_curvature_values: int
    dead_nodes: int
    state_counts: tuple[tuple[DualTrit, int], ...]


@dataclass(frozen=True)
class CanvasProbeReceipt:
    schema: str
    mode: str
    canvas_sha256: str
    base_input: Vector
    directions: tuple[Vector, ...]
    baseline_trajectory: CanvasTrajectory
    responses: tuple[DirectionResponse, ...]
    layer_summaries: tuple[LayerProbeSummary, ...]
    forward_calls: int
    receipt_sha256: str

    @property
    def baseline_layers(self) -> tuple[Vector, ...]:
        return self.baseline_trajectory.states


@dataclass(frozen=True)
class GoalLayerArrow:
    """Exact response arrow induced by fixed coefficients over probe rays."""

    layer: int
    nodes: int
    slope: Vector
    curvature: Vector
    slope_squared_length: int
    curvature_squared_length: int


@dataclass(frozen=True)
class GoalResponseReceipt:
    """Goal-referenced view of a previously completed fixed probe receipt."""

    schema: str
    mode: str
    probe_receipt_sha256: str
    goal_coefficients: Vector
    layer_arrows: tuple[GoalLayerArrow, ...]
    terminal_slope: Vector
    terminal_curvature: Vector
    receipt_sha256: str


def _plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _validate_vector(value: Sequence[int], width: int, name: str) -> Vector:
    result = tuple(value)
    if len(result) != width or any(not _plain_int(item) for item in result):
        raise ValueError(f"{name} must contain exactly {width} integers")
    return result


def _derived_trit(seed: int, kind: bytes, layer: int, row: int, column: int) -> int:
    payload = b"|".join(
        (
            DOMAIN,
            seed.to_bytes(16, "big"),
            kind,
            layer.to_bytes(4, "big"),
            row.to_bytes(4, "big"),
            column.to_bytes(4, "big"),
        )
    )
    # Rejection makes the three residues exactly balanced over accepted bytes.
    for value in hashlib.shake_256(payload).digest(64):
        if value < 255:
            return TRITS[value % 3]
    raise RuntimeError("SHAKE output did not yield a trit")


def _weight_payload(layers: tuple[CanvasLayer, ...]) -> list[dict[str, object]]:
    return [{"weights": layer.weights, "biases": layer.biases} for layer in layers]


def build_canvas(
    input_width: int,
    layer_widths: Sequence[int],
    *,
    seed: int,
    activation: str = "clip",
    clip_limit: int = 97,
) -> FrozenCanvas:
    """Create one deterministic canvas without training or mutable parameters."""

    widths = tuple(layer_widths)
    if not _plain_int(input_width) or input_width < 1:
        raise ValueError("input width must be a positive integer")
    if not widths or any(not _plain_int(width) or width < 1 for width in widths):
        raise ValueError("layer widths must be positive integers")
    if len(widths) > 16:
        raise ValueError("canvas depth exceeds the bounded research surface")
    if not _plain_int(seed) or not 0 <= seed < 2**128:
        raise ValueError("seed must be a nonnegative integer below 2**128")
    if activation not in ("identity", "clip"):
        raise ValueError("activation must be identity or clip")
    if not _plain_int(clip_limit) or clip_limit < 1:
        raise ValueError("clip limit must be a positive integer")

    total_weights = 0
    previous = input_width
    layers: list[CanvasLayer] = []
    for layer_index, width in enumerate(widths):
        total_weights += previous * width
        if total_weights > MAX_TOTAL_WEIGHTS:
            raise ValueError("canvas exceeds the bounded weight count")
        weights = tuple(
            tuple(_derived_trit(seed, b"weight", layer_index, row, column) for column in range(previous))
            for row in range(width)
        )
        biases = tuple(_derived_trit(seed, b"bias", layer_index, row, 0) for row in range(width))
        layers.append(CanvasLayer(weights=weights, biases=biases))
        previous = width

    frozen_layers = tuple(layers)
    weight_sha256 = hashlib.sha256(_canonical(_weight_payload(frozen_layers))).hexdigest()
    canvas_payload = {
        "schema": "scbe.frozen-neural-canvas.v1",
        "seed": seed,
        "input_width": input_width,
        "layer_widths": widths,
        "activation": activation,
        "clip_limit": clip_limit,
        "weight_sha256": weight_sha256,
    }
    return FrozenCanvas(
        seed=seed,
        input_width=input_width,
        layer_widths=widths,
        activation=activation,
        clip_limit=clip_limit,
        layers=frozen_layers,
        weight_sha256=weight_sha256,
        canvas_sha256=hashlib.sha256(_canonical(canvas_payload)).hexdigest(),
    )


def trace_forward(canvas: FrozenCanvas, value: Sequence[int]) -> CanvasTrajectory:
    """Project one vector and retain every affine and bounded path segment."""

    current = _validate_vector(value, canvas.input_width, "canvas input")
    origin = current
    transitions: list[CanvasLayerTransition] = []
    expected_input = canvas.input_width
    if len(canvas.layers) != len(canvas.layer_widths):
        raise ValueError("canvas layer metadata is inconsistent")

    for layer_index, (layer, expected_output) in enumerate(zip(canvas.layers, canvas.layer_widths, strict=True)):
        if len(layer.weights) != expected_output or len(layer.biases) != expected_output:
            raise ValueError(f"canvas layer {layer_index} output shape is inconsistent")
        if any(len(row) != expected_input for row in layer.weights):
            raise ValueError(f"canvas layer {layer_index} input shape is inconsistent")
        affine = tuple(
            bias + sum(weight * item for weight, item in zip(row, current, strict=True))
            for row, bias in zip(layer.weights, layer.biases, strict=True)
        )
        if canvas.activation == "clip":
            limit = canvas.clip_limit
            state = tuple(max(-limit, min(limit, item)) for item in affine)
        elif canvas.activation != "identity":
            raise ValueError("canvas activation changed after construction")
        else:
            state = affine
        transitions.append(
            CanvasLayerTransition(
                layer=layer_index,
                source=current,
                affine=affine,
                state=state,
                clipped_nodes=sum(left != right for left, right in zip(affine, state, strict=True)),
            )
        )
        current = state
        expected_input = expected_output
    return CanvasTrajectory(origin=origin, transitions=tuple(transitions), terminal=current)


def forward(canvas: FrozenCanvas, value: Sequence[int]) -> tuple[Vector, ...]:
    """Project one exact integer vector and return every bounded layer state."""

    return trace_forward(canvas, value).states


def exact_rank(rows: Sequence[Sequence[int]]) -> int:
    """Return matrix rank over the rationals with no floating-point threshold."""

    values = [list(row) for row in rows]
    if not values:
        return 0
    width = len(values[0])
    if width == 0 or any(len(row) != width for row in values):
        raise ValueError("rank input must be a nonempty rectangular matrix")
    if any(not _plain_int(item) for row in values for item in row):
        raise ValueError("exact rank requires integer entries")

    matrix = [[Fraction(item) for item in row] for row in values]
    pivot_row = 0
    for column in range(width):
        pivot = next((row for row in range(pivot_row, len(matrix)) if matrix[row][column]), None)
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        scale = matrix[pivot_row][column]
        matrix[pivot_row] = [item / scale for item in matrix[pivot_row]]
        for row in range(len(matrix)):
            if row == pivot_row or not matrix[row][column]:
                continue
            factor = matrix[row][column]
            matrix[row] = [left - factor * right for left, right in zip(matrix[row], matrix[pivot_row], strict=True)]
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return pivot_row


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def _receipt_payload(receipt: CanvasProbeReceipt) -> dict[str, object]:
    payload = asdict(receipt)
    payload.pop("receipt_sha256")
    return payload


def verify_receipt(receipt: CanvasProbeReceipt) -> bool:
    expected = hashlib.sha256(_canonical(_receipt_payload(receipt))).hexdigest()
    return receipt.mode == "fixed-complete-probe-bank" and receipt.receipt_sha256 == expected


def _goal_receipt_payload(receipt: GoalResponseReceipt) -> dict[str, object]:
    payload = asdict(receipt)
    payload.pop("receipt_sha256")
    return payload


def verify_goal_receipt(receipt: GoalResponseReceipt) -> bool:
    expected = hashlib.sha256(_canonical(_goal_receipt_payload(receipt))).hexdigest()
    return receipt.mode == "fixed-goal-projection" and receipt.receipt_sha256 == expected


def project_goal_response(
    receipt: CanvasProbeReceipt,
    goal_coefficients: Sequence[int],
) -> GoalResponseReceipt:
    """Project a declared goal over complete response rays without new probes.

    A coefficient belongs to one ordered direction in ``receipt.directions``.
    Every layer arrow remains in that layer's node coordinates.  This function
    deliberately does not subtract arrows from layers of different widths; an
    explicit transport map is required before such a comparison is meaningful.
    """

    if not verify_receipt(receipt):
        raise ValueError("goal projection requires an intact fixed probe receipt")
    goal = _validate_vector(goal_coefficients, len(receipt.responses), "goal coefficients")
    if not any(goal):
        raise ValueError("goal coefficients must contain a direction")
    if len(receipt.layer_summaries) == 0:
        raise ValueError("probe receipt contains no measured layers")

    arrows: list[GoalLayerArrow] = []
    for layer_index, summary in enumerate(receipt.layer_summaries):
        slopes = tuple(response.first_differences[layer_index] for response in receipt.responses)
        curvatures = tuple(response.second_differences[layer_index] for response in receipt.responses)
        if any(len(row) != summary.nodes for row in slopes + curvatures):
            raise ValueError("probe response width disagrees with its layer summary")
        slope = tuple(
            sum(coefficient * slopes[direction][node] for direction, coefficient in enumerate(goal))
            for node in range(summary.nodes)
        )
        curvature = tuple(
            sum(coefficient * curvatures[direction][node] for direction, coefficient in enumerate(goal))
            for node in range(summary.nodes)
        )
        arrows.append(
            GoalLayerArrow(
                layer=layer_index,
                nodes=summary.nodes,
                slope=slope,
                curvature=curvature,
                slope_squared_length=sum(value * value for value in slope),
                curvature_squared_length=sum(value * value for value in curvature),
            )
        )

    value = GoalResponseReceipt(
        schema="scbe.frozen-neural-canvas-goal-response.v1",
        mode="fixed-goal-projection",
        probe_receipt_sha256=receipt.receipt_sha256,
        goal_coefficients=goal,
        layer_arrows=tuple(arrows),
        terminal_slope=arrows[-1].slope,
        terminal_curvature=arrows[-1].curvature,
        receipt_sha256="",
    )
    digest = hashlib.sha256(_canonical(_goal_receipt_payload(value))).hexdigest()
    return replace(value, receipt_sha256=digest)


def probe_triplets(
    canvas: FrozenCanvas,
    base_input: Sequence[int],
    directions: Sequence[Sequence[int]],
    positive_inputs: Sequence[Sequence[int]],
    negative_inputs: Sequence[Sequence[int]],
) -> CanvasProbeReceipt:
    """Measure a fixed central-difference bank without selecting probes.

    ``directions`` are immutable labels in the caller's mathematical space.
    Positive and negative inputs are their already-projected canvas inputs.
    This permits a modular or otherwise nonlinear input map while keeping the
    neural response calculation explicit.
    """

    base = _validate_vector(base_input, canvas.input_width, "base input")
    labels = tuple(tuple(direction) for direction in directions)
    positives = tuple(tuple(value) for value in positive_inputs)
    negatives = tuple(tuple(value) for value in negative_inputs)
    if not labels or len(labels) != len(positives) or len(labels) != len(negatives):
        raise ValueError("probe labels and positive/negative inputs must have the same nonzero length")
    label_width = len(labels[0])
    if label_width < 1 or any(
        len(label) != label_width or any(not _plain_int(item) for item in label) or not any(label) for label in labels
    ):
        raise ValueError("probe directions must be nonzero equal-width integer vectors")
    if len(labels) != len(set(labels)):
        raise ValueError("probe directions must be unique")

    baseline_trajectory = trace_forward(canvas, base)
    baseline_layers = baseline_trajectory.states
    responses: list[DirectionResponse] = []
    for index, direction in enumerate(labels):
        positive_trajectory = trace_forward(
            canvas,
            _validate_vector(positives[index], canvas.input_width, "positive input"),
        )
        negative_trajectory = trace_forward(
            canvas,
            _validate_vector(negatives[index], canvas.input_width, "negative input"),
        )
        positive = positive_trajectory.states
        negative = negative_trajectory.states
        first = tuple(
            tuple(right - left for right, left in zip(plus_layer, minus_layer, strict=True))
            for plus_layer, minus_layer in zip(positive, negative, strict=True)
        )
        second = tuple(
            tuple(
                plus_item - 2 * base_item + minus_item
                for plus_item, base_item, minus_item in zip(plus_layer, base_layer, minus_layer, strict=True)
            )
            for plus_layer, base_layer, minus_layer in zip(positive, baseline_layers, negative, strict=True)
        )
        states = tuple(
            tuple((_sign(slope), _sign(curvature)) for slope, curvature in zip(slope_layer, curve_layer, strict=True))
            for slope_layer, curve_layer in zip(first, second, strict=True)
        )
        if any(state not in DUAL_TRIT_STATES for layer in states for state in layer):
            raise RuntimeError("response escaped the existing dual-trit state space")
        responses.append(
            DirectionResponse(
                direction=direction,
                positive_trajectory=positive_trajectory,
                negative_trajectory=negative_trajectory,
                first_differences=first,
                second_differences=second,
                dual_trit_states=states,
            )
        )

    summaries: list[LayerProbeSummary] = []
    for layer_index, nodes in enumerate(canvas.layer_widths):
        slopes = tuple(response.first_differences[layer_index] for response in responses)
        curvatures = tuple(response.second_differences[layer_index] for response in responses)
        states = tuple(state for response in responses for state in response.dual_trit_states[layer_index])
        dead_nodes = sum(
            all(slopes[direction][node] == 0 and curvatures[direction][node] == 0 for direction in range(len(labels)))
            for node in range(nodes)
        )
        summaries.append(
            LayerProbeSummary(
                layer=layer_index,
                nodes=nodes,
                slope_rank=exact_rank(slopes),
                curvature_rank=exact_rank(curvatures),
                nonzero_slope_values=sum(item != 0 for row in slopes for item in row),
                nonzero_curvature_values=sum(item != 0 for row in curvatures for item in row),
                dead_nodes=dead_nodes,
                state_counts=tuple((state, states.count(state)) for state in DUAL_TRIT_STATES),
            )
        )

    receipt = CanvasProbeReceipt(
        schema="scbe.frozen-neural-canvas-probe.v2",
        mode="fixed-complete-probe-bank",
        canvas_sha256=canvas.canvas_sha256,
        base_input=base,
        directions=labels,
        baseline_trajectory=baseline_trajectory,
        responses=tuple(responses),
        layer_summaries=tuple(summaries),
        forward_calls=1 + 2 * len(labels),
        receipt_sha256="",
    )
    digest = hashlib.sha256(_canonical(_receipt_payload(receipt))).hexdigest()
    return replace(receipt, receipt_sha256=digest)


def probe_offsets(
    canvas: FrozenCanvas,
    base_input: Sequence[int],
    directions: Sequence[Sequence[int]],
) -> CanvasProbeReceipt:
    """Convenience form for ordinary integer ``base +/- direction`` probes."""

    base = _validate_vector(base_input, canvas.input_width, "base input")
    labels = tuple(_validate_vector(direction, canvas.input_width, "probe direction") for direction in directions)
    positives = tuple(tuple(left + right for left, right in zip(base, direction, strict=True)) for direction in labels)
    negatives = tuple(tuple(left - right for left, right in zip(base, direction, strict=True)) for direction in labels)
    return probe_triplets(canvas, base, labels, positives, negatives)
