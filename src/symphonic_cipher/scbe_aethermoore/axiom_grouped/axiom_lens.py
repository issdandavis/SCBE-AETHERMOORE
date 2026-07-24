"""Five-axis diagnostic overlay for graph and neural node states.

``AxiomLens`` does not replace a graph, neural network, or governance gate. It
measures five explicitly supplied relationships and returns an overlay:

* unitarity: node-norm drift from a reference state,
* locality: edge-length expansion from a reference graph,
* causality: directed-edge timestamp violations,
* symmetry: disagreement with symmetry-aligned views, and
* composition: disagreement with an independently composed target.

Missing evidence remains unobserved instead of being scored as a pass. The
authoritative representation is the N x 5 residual field. The optional stereo
coordinates are only a deterministic, lossy projection for visualization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

AXIOM_ORDER: tuple[str, ...] = (
    "unitarity",
    "locality",
    "causality",
    "symmetry",
    "composition",
)
AXIOM_INDEX: Mapping[str, int] = {name: index for index, name in enumerate(AXIOM_ORDER)}

# Five deterministic lens directions. The first three form an equilateral
# horizontal frame; symmetry and composition provide the vertical opposition.
AXIOM_LENS_BASIS_3D = np.asarray(
    [
        [1.0, 0.0, 0.0],
        [-0.5, np.sqrt(3.0) / 2.0, 0.0],
        [-0.5, -np.sqrt(3.0) / 2.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, 0.0, -1.0],
    ],
    dtype=float,
)


@dataclass(frozen=True, slots=True)
class AxiomLensConfig:
    """Numerical and visualization settings for an axiom overlay."""

    weights: tuple[float, float, float, float, float] = (1.0, 1.0, 1.0, 1.0, 1.0)
    normalization_floor: float = 1.0
    locality_slack: float = 0.0
    causal_min_step: float = 0.0
    time_scale: float = 1.0
    stereo_separation: float = 0.03
    epsilon: float = 1e-12

    def __post_init__(self) -> None:
        weights = np.asarray(self.weights, dtype=float)
        if weights.shape != (len(AXIOM_ORDER),):
            raise ValueError(f"weights must contain {len(AXIOM_ORDER)} values")
        if not np.all(np.isfinite(weights)) or np.any(weights < 0.0):
            raise ValueError("weights must be finite and non-negative")
        scalars = np.asarray(
            [
                self.normalization_floor,
                self.locality_slack,
                self.causal_min_step,
                self.time_scale,
                self.stereo_separation,
                self.epsilon,
            ],
            dtype=float,
        )
        if not np.all(np.isfinite(scalars)):
            raise ValueError("configuration values must be finite")
        if self.normalization_floor <= 0.0:
            raise ValueError("normalization_floor must be positive")
        if self.locality_slack < 0.0:
            raise ValueError("locality_slack must be non-negative")
        if self.causal_min_step < 0.0:
            raise ValueError("causal_min_step must be non-negative")
        if self.time_scale <= 0.0:
            raise ValueError("time_scale must be positive")
        if self.stereo_separation < 0.0:
            raise ValueError("stereo_separation must be non-negative")
        if self.epsilon <= 0.0:
            raise ValueError("epsilon must be positive")


@dataclass(frozen=True, slots=True)
class AxiomLensResult:
    """Complete diagnostic field and its analytical gradients."""

    axiom_order: tuple[str, ...]
    node_residuals: np.ndarray
    node_observed: np.ndarray
    node_compliance: np.ndarray
    edge_residuals: np.ndarray
    edge_observed: np.ndarray
    edge_axiom_delta: np.ndarray
    state_gradients_by_axiom: np.ndarray
    time_gradients_by_axiom: np.ndarray
    state_gradient: np.ndarray
    time_gradient: np.ndarray
    loss_by_axiom: Mapping[str, float | None]
    total_loss: float
    coverage_by_axiom: Mapping[str, float]
    overall_coverage: float
    evidence_status: str
    depth: np.ndarray
    offset_xyz: np.ndarray
    left_offset_xyz: np.ndarray
    right_offset_xyz: np.ndarray
    dominant_axiom: tuple[str | None, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a strict-JSON-compatible receipt."""

        compliance = [
            [None if np.isnan(value) else float(value) for value in row]
            for row in self.node_compliance
        ]

        return {
            "schema": "scbe.axiom-lens.v1",
            "axiom_order": list(self.axiom_order),
            "node_residuals": self.node_residuals.tolist(),
            "node_observed": self.node_observed.tolist(),
            "node_compliance": compliance,
            "edge_residuals": self.edge_residuals.tolist(),
            "edge_observed": self.edge_observed.tolist(),
            "edge_axiom_delta": self.edge_axiom_delta.tolist(),
            "state_gradients_by_axiom": self.state_gradients_by_axiom.tolist(),
            "time_gradients_by_axiom": self.time_gradients_by_axiom.tolist(),
            "state_gradient": self.state_gradient.tolist(),
            "time_gradient": self.time_gradient.tolist(),
            "loss_by_axiom": dict(self.loss_by_axiom),
            "total_loss": self.total_loss,
            "coverage_by_axiom": dict(self.coverage_by_axiom),
            "overall_coverage": self.overall_coverage,
            "evidence_status": self.evidence_status,
            "depth": self.depth.tolist(),
            "offset_xyz": self.offset_xyz.tolist(),
            "left_offset_xyz": self.left_offset_xyz.tolist(),
            "right_offset_xyz": self.right_offset_xyz.tolist(),
            "dominant_axiom": list(self.dominant_axiom),
        }


def _state_matrix(
    name: str, values: np.ndarray | Sequence[Sequence[float]]
) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError(f"{name} must have shape (nodes, features)")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must contain only finite values")
    return matrix


def _matching_state_matrix(
    name: str,
    values: np.ndarray | Sequence[Sequence[float]] | None,
    shape: tuple[int, int],
) -> np.ndarray | None:
    if values is None:
        return None
    matrix = _state_matrix(name, values)
    if matrix.shape != shape:
        raise ValueError(f"{name} must have shape {shape}")
    return matrix


def _edge_matrix(
    edges: np.ndarray | Sequence[Sequence[int]] | None, node_count: int
) -> np.ndarray:
    if edges is None:
        return np.empty((0, 2), dtype=np.int64)
    raw = np.asarray(edges)
    if raw.size == 0:
        return np.empty((0, 2), dtype=np.int64)
    if raw.ndim != 2 or raw.shape[1] != 2:
        raise ValueError("edges must have shape (edges, 2)")
    if not np.issubdtype(raw.dtype, np.integer):
        if not np.all(np.equal(raw, np.floor(raw))):
            raise ValueError("edge indices must be integers")
    edge_matrix = raw.astype(np.int64)
    if np.any(edge_matrix < 0) or np.any(edge_matrix >= node_count):
        raise ValueError("edge index is outside the node range")
    if np.any(edge_matrix[:, 0] == edge_matrix[:, 1]):
        raise ValueError("self edges are not supported")
    return edge_matrix


def _symmetry_views(
    values: (
        np.ndarray
        | Sequence[Sequence[float]]
        | Sequence[Sequence[Sequence[float]]]
        | None
    ),
    shape: tuple[int, int],
) -> np.ndarray | None:
    if values is None:
        return None
    views = np.asarray(values, dtype=float)
    if views.ndim == 2:
        views = views[np.newaxis, ...]
    if views.ndim != 3 or views.shape[1:] != shape or views.shape[0] == 0:
        raise ValueError(
            f"symmetry_states must have shape {shape} or (views, {shape[0]}, {shape[1]})"
        )
    if not np.all(np.isfinite(views)):
        raise ValueError("symmetry_states must contain only finite values")
    return views


def _distribute_edge_values(
    values: np.ndarray,
    edges: np.ndarray,
    node_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    totals = np.zeros(node_count, dtype=float)
    counts = np.zeros(node_count, dtype=np.int64)
    for edge_index, (source, target) in enumerate(edges):
        totals[source] += values[edge_index]
        totals[target] += values[edge_index]
        counts[source] += 1
        counts[target] += 1
    observed = counts > 0
    node_values = np.zeros(node_count, dtype=float)
    node_values[observed] = totals[observed] / counts[observed]
    return node_values, observed


def _target_residual_and_gradient(
    node_states: np.ndarray,
    targets: np.ndarray,
    normalization_floor: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Relative squared error and d(mean(error))/d(node_states)."""

    node_count = node_states.shape[0]
    view_count = targets.shape[0]
    residuals = np.zeros(node_count, dtype=float)
    gradient = np.zeros_like(node_states)
    floor_squared = normalization_floor**2

    for target in targets:
        delta = node_states - target
        denominator = np.maximum(np.sum(target * target, axis=1), floor_squared)
        residuals += np.sum(delta * delta, axis=1) / denominator
        gradient += (2.0 * delta / denominator[:, np.newaxis]) / (
            node_count * view_count
        )

    return residuals / view_count, gradient


def build_axiom_lens(
    node_states: np.ndarray | Sequence[Sequence[float]],
    *,
    edges: np.ndarray | Sequence[Sequence[int]] | None = None,
    reference_states: np.ndarray | Sequence[Sequence[float]] | None = None,
    timestamps: np.ndarray | Sequence[float] | None = None,
    symmetry_states: (
        np.ndarray
        | Sequence[Sequence[float]]
        | Sequence[Sequence[Sequence[float]]]
        | None
    ) = None,
    composed_states: np.ndarray | Sequence[Sequence[float]] | None = None,
    config: AxiomLensConfig | None = None,
) -> AxiomLensResult:
    """Build a five-axiom residual and gradient overlay.

    ``edges`` are undirected for locality and directed ``source -> target`` for
    causality. ``symmetry_states`` must already be mapped back into the node
    state's coordinate frame. No axis is inferred from another axis: if the
    required evidence is absent, that axis is marked unobserved.
    """

    config = config or AxiomLensConfig()
    states = _state_matrix("node_states", node_states)
    node_count, feature_count = states.shape
    edge_array = _edge_matrix(edges, node_count)
    edge_count = edge_array.shape[0]
    references = _matching_state_matrix(
        "reference_states", reference_states, states.shape
    )
    compositions = _matching_state_matrix(
        "composed_states", composed_states, states.shape
    )
    symmetries = _symmetry_views(symmetry_states, states.shape)

    time_values: np.ndarray | None = None
    if timestamps is not None:
        time_values = np.asarray(timestamps, dtype=float)
        if time_values.shape != (node_count,):
            raise ValueError(f"timestamps must have shape ({node_count},)")
        if not np.all(np.isfinite(time_values)):
            raise ValueError("timestamps must contain only finite values")

    axis_count = len(AXIOM_ORDER)
    node_residuals = np.zeros((node_count, axis_count), dtype=float)
    node_observed = np.zeros((node_count, axis_count), dtype=bool)
    edge_residuals = np.zeros((edge_count, axis_count), dtype=float)
    edge_observed = np.zeros((edge_count, axis_count), dtype=bool)
    state_gradients = np.zeros((axis_count, node_count, feature_count), dtype=float)
    time_gradients = np.zeros((axis_count, node_count), dtype=float)
    losses = np.zeros(axis_count, dtype=float)
    floor = config.normalization_floor

    unitarity_index = AXIOM_INDEX["unitarity"]
    locality_index = AXIOM_INDEX["locality"]
    causality_index = AXIOM_INDEX["causality"]
    symmetry_index = AXIOM_INDEX["symmetry"]
    composition_index = AXIOM_INDEX["composition"]

    if references is not None:
        current_norms = np.linalg.norm(states, axis=1)
        reference_norms = np.linalg.norm(references, axis=1)
        scales = np.maximum(reference_norms, floor)
        norm_delta = current_norms - reference_norms
        residuals = (norm_delta / scales) ** 2
        node_residuals[:, unitarity_index] = residuals
        node_observed[:, unitarity_index] = True
        losses[unitarity_index] = float(np.mean(residuals))

        safe_norms = np.maximum(current_norms, config.epsilon)
        state_gradients[unitarity_index] = (
            (2.0 * norm_delta / (scales**2 * node_count))[:, np.newaxis]
            * states
            / safe_norms[:, np.newaxis]
        )

    if references is not None and edge_count:
        locality_values = np.zeros(edge_count, dtype=float)
        locality_gradient = state_gradients[locality_index]
        for edge_index, (source, target) in enumerate(edge_array):
            current_delta = states[source] - states[target]
            reference_delta = references[source] - references[target]
            current_distance = float(np.linalg.norm(current_delta))
            reference_distance = float(np.linalg.norm(reference_delta))
            excess = max(
                0.0, current_distance - reference_distance - config.locality_slack
            )
            scale = max(reference_distance, floor)
            locality_values[edge_index] = (excess / scale) ** 2

            if excess > 0.0 and current_distance > config.epsilon:
                factor = 2.0 * excess / (scale**2 * current_distance * edge_count)
                contribution = factor * current_delta
                locality_gradient[source] += contribution
                locality_gradient[target] -= contribution

        node_values, observed = _distribute_edge_values(
            locality_values, edge_array, node_count
        )
        node_residuals[:, locality_index] = node_values
        node_observed[:, locality_index] = observed
        edge_residuals[:, locality_index] = locality_values
        edge_observed[:, locality_index] = True
        losses[locality_index] = float(np.mean(locality_values))

    if time_values is not None and edge_count:
        causal_values = np.zeros(edge_count, dtype=float)
        causal_gradient = time_gradients[causality_index]
        scale_squared = config.time_scale**2
        for edge_index, (source, target) in enumerate(edge_array):
            violation = max(
                0.0,
                float(
                    time_values[source] + config.causal_min_step - time_values[target]
                ),
            )
            causal_values[edge_index] = violation**2 / scale_squared
            if violation > 0.0:
                derivative = 2.0 * violation / (scale_squared * edge_count)
                causal_gradient[source] += derivative
                causal_gradient[target] -= derivative

        node_values, observed = _distribute_edge_values(
            causal_values, edge_array, node_count
        )
        node_residuals[:, causality_index] = node_values
        node_observed[:, causality_index] = observed
        edge_residuals[:, causality_index] = causal_values
        edge_observed[:, causality_index] = True
        losses[causality_index] = float(np.mean(causal_values))

    if symmetries is not None:
        residuals, gradient = _target_residual_and_gradient(states, symmetries, floor)
        node_residuals[:, symmetry_index] = residuals
        node_observed[:, symmetry_index] = True
        state_gradients[symmetry_index] = gradient
        losses[symmetry_index] = float(np.mean(residuals))

    if compositions is not None:
        residuals, gradient = _target_residual_and_gradient(
            states,
            compositions[np.newaxis, ...],
            floor,
        )
        node_residuals[:, composition_index] = residuals
        node_observed[:, composition_index] = True
        state_gradients[composition_index] = gradient
        losses[composition_index] = float(np.mean(residuals))

    # Endpoint summaries for axes that are not intrinsically edge-valued.
    for edge_index, (source, target) in enumerate(edge_array):
        for axis_index in (unitarity_index, symmetry_index, composition_index):
            if node_observed[source, axis_index] and node_observed[target, axis_index]:
                edge_residuals[edge_index, axis_index] = 0.5 * (
                    node_residuals[source, axis_index]
                    + node_residuals[target, axis_index]
                )
                edge_observed[edge_index, axis_index] = True

    edge_axiom_delta = np.zeros_like(edge_residuals)
    for edge_index, (source, target) in enumerate(edge_array):
        jointly_observed = node_observed[source] & node_observed[target]
        edge_axiom_delta[edge_index, jointly_observed] = (
            node_residuals[target, jointly_observed]
            - node_residuals[source, jointly_observed]
        )

    node_compliance = np.full_like(node_residuals, np.nan)
    node_compliance[node_observed] = np.exp(-node_residuals[node_observed])

    weights = np.asarray(config.weights, dtype=float)
    state_gradient = np.tensordot(weights, state_gradients, axes=(0, 0))
    time_gradient = np.tensordot(weights, time_gradients, axes=(0, 0))
    total_loss = float(np.dot(weights, losses))
    coverage = np.mean(node_observed, axis=0)
    overall_coverage = float(np.mean(node_observed))
    if np.all(node_observed):
        evidence_status = "complete"
    elif np.any(node_observed):
        evidence_status = "partial"
    else:
        evidence_status = "unobserved"

    severity = np.zeros_like(node_residuals)
    severity[node_observed] = 1.0 - np.exp(-node_residuals[node_observed])
    weighted_severity = severity * weights[np.newaxis, :]
    depth = np.linalg.norm(weighted_severity, axis=1)
    offset_xyz = weighted_severity @ AXIOM_LENS_BASIS_3D
    parallax = config.stereo_separation * depth
    left_offset_xyz = offset_xyz.copy()
    right_offset_xyz = offset_xyz.copy()
    left_offset_xyz[:, 0] -= parallax
    right_offset_xyz[:, 0] += parallax

    dominant: list[str | None] = []
    for node_index in range(node_count):
        if not np.any(node_observed[node_index]):
            dominant.append(None)
            continue
        axis_index = int(np.argmax(weighted_severity[node_index]))
        if weighted_severity[node_index, axis_index] <= config.epsilon:
            dominant.append(None)
        else:
            dominant.append(AXIOM_ORDER[axis_index])

    return AxiomLensResult(
        axiom_order=AXIOM_ORDER,
        node_residuals=node_residuals,
        node_observed=node_observed,
        node_compliance=node_compliance,
        edge_residuals=edge_residuals,
        edge_observed=edge_observed,
        edge_axiom_delta=edge_axiom_delta,
        state_gradients_by_axiom=state_gradients,
        time_gradients_by_axiom=time_gradients,
        state_gradient=state_gradient,
        time_gradient=time_gradient,
        loss_by_axiom={
            name: (float(losses[index]) if np.any(node_observed[:, index]) else None)
            for index, name in enumerate(AXIOM_ORDER)
        },
        total_loss=total_loss,
        coverage_by_axiom={
            name: float(coverage[index]) for index, name in enumerate(AXIOM_ORDER)
        },
        overall_coverage=overall_coverage,
        evidence_status=evidence_status,
        depth=depth,
        offset_xyz=offset_xyz,
        left_offset_xyz=left_offset_xyz,
        right_offset_xyz=right_offset_xyz,
        dominant_axiom=tuple(dominant),
    )


__all__ = [
    "AXIOM_ORDER",
    "AXIOM_INDEX",
    "AXIOM_LENS_BASIS_3D",
    "AxiomLensConfig",
    "AxiomLensResult",
    "build_axiom_lens",
]
