from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Sequence

import numpy as np

from src.harmonic.state21_product_metric import STATE21_DIM, hyperbolic_distance_poincare, parse_state21_v1


EPSILON = 1e-10


class OverlayAction(str, Enum):
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    QUARANTINE = "QUARANTINE"


NEG_ZERO_FREEZE = "NEG_ZERO_FREEZE"


@dataclass(frozen=True)
class BallSpec:
    name: str
    indices: tuple[int, ...]
    angle_indices: tuple[int, ...] = ()
    alpha: float = 0.15
    trust_radius: float = 1.5
    loop_step_scale: float = 0.08
    loop_displacement_max: float = 0.35
    center: tuple[float, ...] | None = None

    def resolved_center(self) -> np.ndarray:
        dim = len(self.indices)
        if self.center is None:
            return np.zeros(dim, dtype=float)
        center = np.asarray(self.center, dtype=float)
        if center.shape != (dim,):
            raise ValueError(f"Center for {self.name} must have shape ({dim},)")
        return _project_embedding_to_ball(center, alpha=1.0)


@dataclass(frozen=True)
class DualOverlayConfig:
    ball_a: BallSpec = BallSpec(
        name="governance_geo",
        indices=(0, 1, 2, 3, 4, 5),
        trust_radius=1.5,
    )
    ball_b: BallSpec = BallSpec(
        name="semantic_spectral",
        indices=(6, 7, 8, 9, 10, 11),
        angle_indices=(6, 7, 8, 9, 10, 11),
        alpha=0.15,
        trust_radius=1.5,
    )
    delta_match_tolerance: float = 0.2
    freeze_symbol: str = NEG_ZERO_FREEZE


@dataclass(frozen=True)
class BallProjection:
    name: str
    point: tuple[float, ...]
    center: tuple[float, ...]
    trust_distance: float
    in_trust_region: bool


@dataclass(frozen=True)
class LoopMetrics:
    displacement: float
    endpoint: tuple[float, ...]
    passed: bool


@dataclass(frozen=True)
class DualVerificationResult:
    ball_a: BallProjection
    ball_b: BallProjection
    loop_a: LoopMetrics
    loop_b: LoopMetrics
    delta_match_abs: float
    dual_loop_match: bool
    accepted: bool
    action: OverlayAction
    control_symbol: str | None = None
    requires_quorum_exit: bool = False


def _norm_sq(v: np.ndarray) -> float:
    return float(np.dot(v, v))


def _project_embedding_to_ball(x: np.ndarray, alpha: float = 0.15, eps: float = 1e-6) -> np.ndarray:
    n = float(np.linalg.norm(x))
    if n < 1e-12:
        return np.zeros_like(x)
    r = min(math.tanh(alpha * n), 1.0 - eps)
    return (r / n) * x


def _mobius_add(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    uv = float(np.dot(u, v))
    u_norm_sq = _norm_sq(u)
    v_norm_sq = _norm_sq(v)
    numerator = (1.0 + 2.0 * uv + v_norm_sq) * u + (1.0 - u_norm_sq) * v
    denominator = max(1.0 + 2.0 * uv + u_norm_sq * v_norm_sq, EPSILON)
    return _project_embedding_to_ball(numerator / denominator, alpha=1.0)


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        out = np.zeros_like(v)
        out[0] = 1.0
        return out
    return v / n


def _extract_ball_vector(state21: Sequence[float], spec: BallSpec) -> np.ndarray:
    parsed = parse_state21_v1(state21)
    raw = parsed.raw
    if len(raw) != STATE21_DIM:
        raise ValueError(f"Expected {STATE21_DIM} state dimensions")

    transformed = []
    angle_index_set = set(spec.angle_indices)
    for index in spec.indices:
        value = float(raw[index])
        transformed.append(math.sin(value) if index in angle_index_set else value)
    return np.asarray(transformed, dtype=float)


def _project_ball(state21: Sequence[float], spec: BallSpec) -> BallProjection:
    vector = _extract_ball_vector(state21, spec)
    point = _project_embedding_to_ball(vector, alpha=spec.alpha)
    center = spec.resolved_center()
    trust_distance = hyperbolic_distance_poincare(point, center)
    in_trust = trust_distance <= spec.trust_radius
    return BallProjection(
        name=spec.name,
        point=tuple(float(x) for x in point),
        center=tuple(float(x) for x in center),
        trust_distance=trust_distance,
        in_trust_region=in_trust,
    )


def _small_step(seed_vector: np.ndarray, scale: float, roll: int) -> np.ndarray:
    direction = np.roll(seed_vector, roll)
    direction = _normalize(direction)
    return _project_embedding_to_ball(direction * scale, alpha=1.0)


def _commutator_loop(point: np.ndarray, seed_vector: np.ndarray, spec: BallSpec) -> LoopMetrics:
    a = _small_step(seed_vector, spec.loop_step_scale, 0)
    b = _small_step(seed_vector, spec.loop_step_scale, 1)

    u1 = _mobius_add(point, a)
    u2 = _mobius_add(u1, b)
    u3 = _mobius_add(u2, -a)
    u4 = _mobius_add(u3, -b)

    displacement = hyperbolic_distance_poincare(point, u4)
    return LoopMetrics(
        displacement=displacement,
        endpoint=tuple(float(x) for x in u4),
        passed=displacement <= spec.loop_displacement_max,
    )


def _project_into_trust_region(point: np.ndarray, center: np.ndarray, trust_radius: float) -> np.ndarray:
    translated = _mobius_add(-center, point)
    translated_norm = float(np.linalg.norm(translated))
    max_norm = math.tanh(trust_radius / 2.0)
    if translated_norm <= max_norm:
        return point
    clamped = translated * (max_norm / max(translated_norm, EPSILON))
    return _mobius_add(center, clamped)


def project_dual_state(
    state21: Sequence[float],
    config: DualOverlayConfig = DualOverlayConfig(),
) -> tuple[BallProjection, BallProjection]:
    return _project_ball(state21, config.ball_a), _project_ball(state21, config.ball_b)


def verify_dual_overlay(
    state21: Sequence[float],
    config: DualOverlayConfig = DualOverlayConfig(),
    control_symbol: str | None = None,
) -> DualVerificationResult:
    ball_a = _project_ball(state21, config.ball_a)
    ball_b = _project_ball(state21, config.ball_b)

    point_a = np.asarray(ball_a.point, dtype=float)
    point_b = np.asarray(ball_b.point, dtype=float)
    center_a = np.asarray(ball_a.center, dtype=float)
    center_b = np.asarray(ball_b.center, dtype=float)

    requires_quorum_exit = False
    action = OverlayAction.QUARANTINE
    if control_symbol == config.freeze_symbol:
        point_a = _project_into_trust_region(point_a, center_a, config.ball_a.trust_radius)
        point_b = _project_into_trust_region(point_b, center_b, config.ball_b.trust_radius)
        ball_a = BallProjection(
            name=ball_a.name,
            point=tuple(float(x) for x in point_a),
            center=ball_a.center,
            trust_distance=hyperbolic_distance_poincare(point_a, center_a),
            in_trust_region=True,
        )
        ball_b = BallProjection(
            name=ball_b.name,
            point=tuple(float(x) for x in point_b),
            center=ball_b.center,
            trust_distance=hyperbolic_distance_poincare(point_b, center_b),
            in_trust_region=True,
        )
        requires_quorum_exit = True
        action = OverlayAction.HOLD

    seed_a = _extract_ball_vector(state21, config.ball_a)
    seed_b = _extract_ball_vector(state21, config.ball_b)
    loop_a = _commutator_loop(point_a, seed_a, config.ball_a)
    loop_b = _commutator_loop(point_b, seed_b, config.ball_b)

    delta_match_abs = abs(loop_a.displacement - loop_b.displacement)
    dual_loop_match = delta_match_abs <= config.delta_match_tolerance
    accepted = (
        ball_a.in_trust_region
        and ball_b.in_trust_region
        and loop_a.passed
        and loop_b.passed
        and dual_loop_match
        and action is not OverlayAction.HOLD
    )
    if accepted:
        action = OverlayAction.ALLOW
    elif action is not OverlayAction.HOLD:
        action = OverlayAction.QUARANTINE

    return DualVerificationResult(
        ball_a=ball_a,
        ball_b=ball_b,
        loop_a=loop_a,
        loop_b=loop_b,
        delta_match_abs=delta_match_abs,
        dual_loop_match=dual_loop_match,
        accepted=accepted,
        action=action,
        control_symbol=control_symbol,
        requires_quorum_exit=requires_quorum_exit,
    )


__all__ = [
    "BallProjection",
    "BallSpec",
    "DualOverlayConfig",
    "DualVerificationResult",
    "LoopMetrics",
    "NEG_ZERO_FREEZE",
    "OverlayAction",
    "project_dual_state",
    "verify_dual_overlay",
]
