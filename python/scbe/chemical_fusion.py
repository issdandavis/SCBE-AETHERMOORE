"""
Chemical Fusion Reconstruction Algebra (SCBE)
=============================================

Runtime reference implementation for the SCBE reconstruction vote:

  R_k = sum_i w_i * tau_{i,k}
      + sum_(i,j in E) lambda_{ij} * (chi_i - chi_j)
      - sum_(i,j in E) gamma * lambda_{ij} * abs(chi_i - chi_j)
      + sum_i rho_i * v_i

The implementation is deterministic and intentionally compact. It is suitable
for governance tests, feature generation, and future training-lane enrichment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from .atomic_tokenization import (
    AtomicTokenState,
    Element,
    Tongue,
    TONGUES,
    map_token_to_atomic_state,
)


@dataclass(frozen=True, slots=True)
class FusionParams:
    w_default: float = 1.0
    lambda_default: float = 0.10
    coherence_default: float = 0.10
    rho_default: float = 0.05
    theta_pos: Dict[Tongue, float] | None = None
    theta_neg: Dict[Tongue, float] | None = None

    def __post_init__(self) -> None:
        if self.theta_pos is None:
            object.__setattr__(self, "theta_pos", {tongue: 0.5 for tongue in TONGUES})
        if self.theta_neg is None:
            object.__setattr__(self, "theta_neg", {tongue: -0.5 for tongue in TONGUES})


@dataclass(frozen=True, slots=True)
class FusionResult:
    tau_hat: Dict[Tongue, int]
    reconstruction_votes: Dict[Tongue, float]
    states: list[AtomicTokenState]
    signed_edge_tension: float = 0.0
    coherence_penalty: float = 0.0
    valence_pressure: float = 0.0

    @property
    def elements(self) -> list[Element]:
        return [state.element for state in self.states]


def _normalize_weights(length: int, values: Optional[Sequence[float]], default: float) -> list[float]:
    if values is None:
        return [default] * length
    if len(values) != length:
        raise ValueError("weights length must match token length")
    return [float(value) for value in values]


def _normalize_edges(length: int, edges: Optional[Sequence[Tuple[int, int]]]) -> list[Tuple[int, int]]:
    if edges is None:
        return [(i, j) for i in range(length) for j in range(i + 1, length)]
    return [(int(i), int(j)) for i, j in edges]


def fuse_atomic_states(
    states: Sequence[AtomicTokenState],
    *,
    params: Optional[FusionParams] = None,
    weights: Optional[Sequence[float]] = None,
    edge_weights: Optional[Dict[Tuple[int, int], float]] = None,
    valence_weights: Optional[Sequence[float]] = None,
    edges: Optional[Sequence[Tuple[int, int]]] = None,
) -> FusionResult:
    params = params or FusionParams()
    state_list = list(states)
    n = len(state_list)

    if n == 0:
        raise ValueError("fuse_atomic_states requires at least one atomic state")

    weights_norm = _normalize_weights(n, weights, params.w_default)
    valence_weights_norm = _normalize_weights(n, valence_weights, params.rho_default)
    edges_norm = _normalize_edges(n, edges)
    edge_weights = edge_weights or {}

    votes: Dict[Tongue, float] = {tongue: 0.0 for tongue in TONGUES}
    signed_edge_tension = 0.0
    coherence_penalty = 0.0
    valence_pressure = 0.0

    for index, state in enumerate(state_list):
        wi = weights_norm[index]
        for tongue in TONGUES:
            votes[tongue] += wi * float(getattr(state.tau, tongue))

    for i, j in edges_norm:
        if i < 0 or j < 0 or i >= n or j >= n or i == j:
            continue
        edge_weight = float(
            edge_weights.get((i, j), edge_weights.get((j, i), params.lambda_default))
        )
        delta_chi = (
            state_list[i].element.electronegativity - state_list[j].element.electronegativity
        )
        signed_edge_tension += edge_weight * float(delta_chi)
        coherence_penalty += params.coherence_default * edge_weight * abs(float(delta_chi))
        for tongue in TONGUES:
            votes[tongue] += edge_weight * float(delta_chi)
            votes[tongue] -= params.coherence_default * edge_weight * abs(float(delta_chi))

    for index, state in enumerate(state_list):
        token_valence_pressure = valence_weights_norm[index] * float(state.element.valence)
        valence_pressure += token_valence_pressure
        for tongue in TONGUES:
            votes[tongue] += token_valence_pressure

    tau_hat: Dict[Tongue, int] = {}
    for tongue in TONGUES:
        if votes[tongue] > params.theta_pos[tongue]:
            tau_hat[tongue] = 1
        elif votes[tongue] < params.theta_neg[tongue]:
            tau_hat[tongue] = -1
        else:
            tau_hat[tongue] = 0

    return FusionResult(
        tau_hat=tau_hat,
        reconstruction_votes=votes,
        states=state_list,
        signed_edge_tension=signed_edge_tension,
        coherence_penalty=coherence_penalty,
        valence_pressure=valence_pressure,
    )


def fuse_tokens(
    tokens: Sequence[str],
    *,
    language: Optional[str] = None,
    context_class: Optional[str] = None,
    params: Optional[FusionParams] = None,
    weights: Optional[Sequence[float]] = None,
    edge_weights: Optional[Dict[Tuple[int, int], float]] = None,
    valence_weights: Optional[Sequence[float]] = None,
    edges: Optional[Sequence[Tuple[int, int]]] = None,
) -> Tuple[Dict[Tongue, int], Dict[Tongue, float], list[Element]]:
    states = [
        map_token_to_atomic_state(token, language=language, context_class=context_class)
        for token in tokens
    ]
    result = fuse_atomic_states(
        states,
        params=params,
        weights=weights,
        edge_weights=edge_weights,
        valence_weights=valence_weights,
        edges=edges,
    )
    return result.tau_hat, result.reconstruction_votes, result.elements
