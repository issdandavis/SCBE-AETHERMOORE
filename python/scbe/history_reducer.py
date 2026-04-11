"""
History Reducer + Fibonacci Trust Ladder (SCBE)
==============================================

Small runtime layer that sits on top of the canonical atomic tokenization,
chemical fusion, and rhombic bridge modules. It treats token streams as
path-dependent state transitions and adds a compact Fibonacci trust ladder for
session-aware governance modulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence

import numpy as np

from .atomic_tokenization import (
    AtomicTokenState,
    TONGUES,
    atomic_drift_scale,
    map_token_to_atomic_state,
)
from .chemical_fusion import FusionParams, FusionResult, fuse_atomic_states
from .rhombic_bridge import rhombic_fusion, rhombic_score
from .tongue_code_lanes import classify_code_lane_alignment


PHI = (1.0 + np.sqrt(5.0)) / 2.0


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    arr = np.asarray(vector, dtype=float).reshape(-1)
    norm = float(np.linalg.norm(arr))
    if norm <= 1e-12:
        return arr.copy()
    return arr / norm


def _periodic_view(states: Sequence[AtomicTokenState]) -> np.ndarray:
    rows = [
        np.array(
            [
                float(state.element.Z),
                float(state.element.group),
                float(state.element.period),
                float(state.element.valence),
                float(state.element.electronegativity),
                float(state.witness_state),
            ],
            dtype=float,
        )
        for state in states
    ]
    return np.mean(rows, axis=0)


def _negative_flags(states: Sequence[AtomicTokenState]) -> list[bool]:
    return [state.negative_state for state in states]


def _dual_state(states: Sequence[AtomicTokenState]) -> int:
    dual_values = {state.dual_state for state in states if state.dual_state is not None}
    if dual_values == {0, 1}:
        return 1
    return 0


def _deterministic_noise(token: str, axis: int) -> float:
    seed = sum(ord(ch) for ch in token) + (axis * 37)
    return float(np.sin(seed * 0.6180339887498948))


def _drift_components(
    states: Sequence[AtomicTokenState],
    *,
    trust_factor: float,
    base_noise: float = 0.005,
) -> tuple[list[dict], float]:
    rows: list[dict] = []
    total_sq = 0.0
    for state in states:
        scale = atomic_drift_scale(state, base_noise=base_noise, trust_factor=trust_factor)
        per_axis = [scale * _deterministic_noise(state.token, axis) for axis in range(6)]
        drift_norm = float(np.linalg.norm(np.asarray(per_axis, dtype=float)))
        total_sq += drift_norm**2
        rows.append(
            {
                "token": state.token,
                "negative_state": state.negative_state,
                "dual_state": state.dual_state,
                "drift_scale": scale,
                "drift_norm": drift_norm,
            }
        )
    return rows, float(np.sqrt(total_sq))


@dataclass(slots=True)
class FibonacciTrustLadder:
    values: list[float] = field(default_factory=lambda: [1.0, 1.0])
    betrayal_count: int = 0
    max_window: int = 12
    phi: float = PHI

    @property
    def current(self) -> float:
        return float(self.values[-1])

    def update(self, betrayal_delta: float = 0.0) -> float:
        prev1 = float(self.values[-1])
        prev2 = float(self.values[-2] if len(self.values) >= 2 else self.values[-1])
        if betrayal_delta > 0.0:
            new_value = prev1 - self.phi * abs(float(betrayal_delta))
            self.betrayal_count += 1
        else:
            new_value = prev1 + self.phi * prev2
        self.values.append(float(new_value))
        if len(self.values) > self.max_window:
            self.values.pop(0)
        return float(new_value)

    def factor(self) -> float:
        return float(max(0.3, min(1.8, self.current / 8.0)))


@dataclass(slots=True)
class HistoryReducerState:
    trust_ladder: FibonacciTrustLadder = field(default_factory=FibonacciTrustLadder)
    memory: list[dict] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class HistoryStepResult:
    states: list[AtomicTokenState]
    fusion: FusionResult
    rhombic_energy: float
    rhombic_score: float
    trust_level: float
    trust_factor: float
    betrayal_delta: float
    negative_ratio: float
    dual_state: int
    lane_alignment: dict
    drift_norm: float
    drift_components: list[dict]
    checkpoint: dict


def reduce_atomic_history(
    tokens: Optional[Sequence[str]] = None,
    *,
    atomic_states: Optional[Sequence[AtomicTokenState]] = None,
    state: Optional[HistoryReducerState] = None,
    language: Optional[str] = None,
    context_class: Optional[str] = "timeline",
    params: Optional[FusionParams] = None,
    governance_proto: Optional[np.ndarray] = None,
) -> tuple[HistoryReducerState, HistoryStepResult]:
    if atomic_states is None and not tokens:
        raise ValueError("reduce_atomic_history requires at least one token or atomic state")

    state = state or HistoryReducerState()
    if atomic_states is not None:
        states = list(atomic_states)
        packet_tokens = list(tokens) if tokens is not None else [state_item.token for state_item in states]
    else:
        packet_tokens = list(tokens or [])
        states = [
            map_token_to_atomic_state(token, language=language, context_class=context_class)
            for token in packet_tokens
        ]
    fusion = fuse_atomic_states(states, params=params or FusionParams(rho_default=0.08))

    tau_rows = np.array([state_item.tau.as_tuple() for state_item in states], dtype=float)
    x_vector = np.mean(tau_rows, axis=0)
    audio_vector = _normalize_vector(
        np.array([fusion.reconstruction_votes[tongue] for tongue in TONGUES], dtype=float)
    )
    vision_vector = _normalize_vector(_periodic_view(states))
    governance = np.asarray(
        governance_proto if governance_proto is not None else np.zeros_like(audio_vector),
        dtype=float,
    ).reshape(-1)
    if governance.shape != audio_vector.shape:
        governance = np.resize(governance, audio_vector.shape)

    rhombic_energy = rhombic_fusion(
        x=x_vector,
        audio=audio_vector,
        vision=vision_vector,
        governance=governance,
    )
    diamond_score = rhombic_score(rhombic_energy)

    negative_flags = _negative_flags(states)
    negative_ratio = float(sum(negative_flags) / len(negative_flags))
    mean_vote = float(np.mean(list(fusion.reconstruction_votes.values())))
    betrayal_delta = 1.0 if negative_ratio >= 0.5 or (negative_ratio > 0.0 and mean_vote < -0.25) else 0.0
    trust_level = state.trust_ladder.update(betrayal_delta=betrayal_delta)
    trust_factor = state.trust_ladder.factor()
    dual_state = _dual_state(states)
    lane_alignment = classify_code_lane_alignment(states, context_class=context_class)
    drift_components, drift_norm = _drift_components(
        states,
        trust_factor=trust_factor,
    )

    trust_weighted_votes = {
        tongue: float(value) * trust_factor for tongue, value in fusion.reconstruction_votes.items()
    }
    checkpoint = {
        "tokens": packet_tokens,
        "language": language,
        "context_class": context_class,
        "trust_level": trust_level,
        "trust_factor": trust_factor,
        "fib_step": len(state.trust_ladder.values),
        "betrayal_count": state.trust_ladder.betrayal_count,
        "negative_ratio": negative_ratio,
        "dual_state": dual_state,
        "lane_alignment": lane_alignment,
        "drift_norm": drift_norm,
        "drift_components": drift_components,
        "rhombic_score": diamond_score,
        "tau_hat": dict(fusion.tau_hat),
        "reconstruction_votes": trust_weighted_votes,
    }
    state.memory.append(checkpoint)

    return state, HistoryStepResult(
        states=states,
        fusion=fusion,
        rhombic_energy=rhombic_energy,
        rhombic_score=diamond_score,
        trust_level=trust_level,
        trust_factor=trust_factor,
        betrayal_delta=betrayal_delta,
        negative_ratio=negative_ratio,
        dual_state=dual_state,
        lane_alignment=lane_alignment,
        drift_norm=drift_norm,
        drift_components=drift_components,
        checkpoint=checkpoint,
    )


def reduce_years(
    yearly_token_streams: Sequence[Sequence[str]],
    *,
    language: Optional[str] = None,
    context_class: Optional[str] = "timeline",
    params: Optional[FusionParams] = None,
    governance_proto: Optional[np.ndarray] = None,
) -> HistoryReducerState:
    state = HistoryReducerState()
    for tokens in yearly_token_streams:
        state, _ = reduce_atomic_history(
            tokens,
            state=state,
            language=language,
            context_class=context_class,
            params=params,
            governance_proto=governance_proto,
        )
    return state
