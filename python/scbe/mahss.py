"""MAHSS: Multi-Attention Holographic Search Space.

This module is a deterministic proof harness for binding several attention
mechanism outputs into one holographic vector, folding it through a bounded
Layer-7-style phase transform, and unbinding it into telemetry-visible peaks.

It is intentionally small: no neural model, no training loop, no external
runtime. The goal is to make the "transparent folded paper" idea measurable
before it becomes a model component.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import math
from typing import Mapping, Sequence

import numpy as np

PHI = (1.0 + math.sqrt(5.0)) / 2.0
EPS = 1e-12


class MAHSSError(ValueError):
    """Raised when a MAHSS packet is malformed."""


@dataclass(frozen=True)
class MAHSSConfig:
    """Configuration for the deterministic MAHSS harness."""

    dim: int = 64
    fold_strength: float = 1.0 / PHI
    router_temperature: float = 1.0
    normalize_roles: bool = True

    def __post_init__(self) -> None:
        if self.dim < 4:
            raise MAHSSError("dim must be >= 4")
        if not (0.0 <= self.fold_strength <= 0.95):
            raise MAHSSError("fold_strength must be in [0, 0.95]")
        if self.router_temperature <= 0:
            raise MAHSSError("router_temperature must be > 0")


@dataclass(frozen=True)
class MAHSSResult:
    """Full MAHSS receipt."""

    schema_version: str
    mechanism_names: tuple[str, ...]
    router_weights: dict[str, float]
    raw_superposition: tuple[float, ...]
    folded_vector: tuple[float, ...]
    illumination: dict[str, float]
    selected_mechanism: str
    peak_margin: float
    cross_manifold_strain: float
    telemetry: dict[str, float | str]


def _as_vector(values: Sequence[float], *, dim: int, name: str) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.shape != (dim,):
        raise MAHSSError(f"{name} must have shape ({dim},)")
    if not np.all(np.isfinite(vector)):
        raise MAHSSError(f"{name} contains non-finite values")
    return vector


def l2_normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm <= EPS:
        return np.zeros_like(vector, dtype=float)
    return vector / norm


@lru_cache(maxsize=512)
def _role_vector_tuple(name: str, dim: int, normalize: bool) -> tuple[float, ...]:
    if not name:
        raise MAHSSError("role name must not be empty")
    chunks: list[float] = []
    counter = 0
    while len(chunks) < dim:
        digest = hashlib.sha256(f"mahss-role:{name}:{counter}".encode("utf-8")).digest()
        chunks.extend((byte / 127.5) - 1.0 for byte in digest)
        counter += 1
    vector = np.asarray(chunks[:dim], dtype=float)
    if normalize:
        vector = l2_normalize(vector)
    return tuple(float(value) for value in vector)


def role_vector(name: str, dim: int, *, normalize: bool = True) -> np.ndarray:
    """Build a stable pseudo-random role vector from a mechanism name.

    Role vectors are deterministic and reused heavily across MAHSS candidate
    sweeps, so the hash-derived tuple is cached by (name, dim, normalize).
    A fresh ndarray is returned so callers cannot mutate the cache.
    """

    return np.asarray(_role_vector_tuple(name, dim, normalize), dtype=float)


def clear_role_vector_cache() -> None:
    """Clear deterministic role-vector cache for tests and benchmarks."""

    _role_vector_tuple.cache_clear()


def role_vector_cache_info() -> object:
    """Expose cache stats without leaking the private cached tuple helper."""

    return _role_vector_tuple.cache_info()


def circular_convolution(a: Sequence[float], b: Sequence[float]) -> np.ndarray:
    """HRR binding operation."""

    av = np.asarray(a, dtype=float)
    bv = np.asarray(b, dtype=float)
    if av.shape != bv.shape:
        raise MAHSSError("circular_convolution operands must have the same shape")
    return np.fft.ifft(np.fft.fft(av) * np.fft.fft(bv)).real


def circular_correlation(a: Sequence[float], b: Sequence[float]) -> np.ndarray:
    """HRR unbinding operation."""

    av = np.asarray(a, dtype=float)
    bv = np.asarray(b, dtype=float)
    if av.shape != bv.shape:
        raise MAHSSError("circular_correlation operands must have the same shape")
    return np.fft.ifft(np.conj(np.fft.fft(av)) * np.fft.fft(bv)).real


def softmax(scores: Mapping[str, float], *, temperature: float = 1.0) -> dict[str, float]:
    if not scores:
        raise MAHSSError("softmax requires at least one score")
    max_score = max(scores.values())
    exp_scores = {key: math.exp((float(value) - max_score) / temperature) for key, value in scores.items()}
    total = sum(exp_scores.values())
    return {key: value / total for key, value in exp_scores.items()}


def length_square_probabilities(
    vectors: Mapping[str, Sequence[float]],
    *,
    dim: int,
    power: float = 2.0,
) -> dict[str, float]:
    """Tang-style classical sampling probabilities over mechanism vectors.

    Quantum state measurement samples index i with probability proportional to
    |x_i|^2. Tang's dequantized recommender replaces that with a classical data
    structure that samples by squared length. In MAHSS this is the same bridge:
    attention mechanisms or candidate sketches can be routed by vector energy
    before the heavier fold/unbind step runs.

    ``power=2`` is the Tang/quantum-faithful baseline. Larger powers sharpen
    toward beam search; smaller powers preserve more exploration.
    """

    if not vectors:
        raise MAHSSError("length_square_probabilities requires at least one vector")
    if power <= 0:
        raise MAHSSError("power must be > 0")
    energies: dict[str, float] = {}
    for name, values in vectors.items():
        vector = _as_vector(values, dim=dim, name=name)
        energies[name] = float(np.linalg.norm(vector) ** power)
    total = sum(energies.values())
    if total <= EPS:
        uniform = 1.0 / len(energies)
        return {name: uniform for name in energies}
    return {name: energy / total for name, energy in energies.items()}


def length_square_router(
    attention_outputs: Mapping[str, Sequence[float]],
    *,
    config: MAHSSConfig = MAHSSConfig(),
) -> dict[str, float]:
    """Router using only Tang-style squared-length sampling weights."""

    return length_square_probabilities(attention_outputs, dim=config.dim)


def radial_power_profile(
    vectors: Mapping[str, Sequence[float]],
    query: Sequence[float],
    *,
    dim: int,
    path_history: Sequence[str] = (),
    base_power: float = 2.0,
    radial_gain: float = 0.125,
    novelty_gain: float = 0.125,
    quasicrystal_gain: float = 0.03125,
    min_power: float = 1.25,
    max_power: float = 3.0,
) -> dict[str, dict[str, float]]:
    """Adaptive radial exponent profile for path-aware MAHSS search.

    This turns the fixed Tang exponent into a dial:

    - query alignment pulls probability mass toward the current search
      direction;
    - path-history redundancy lowers repeated paths and boosts novelty;
    - a small phi/quasicrystal phase perturbs ties without becoming random.

    The function is still deterministic. It provides hint telemetry for early
    abort/triangulation before the full fold/unbind scoring pass.
    """

    if not vectors:
        raise MAHSSError("radial_power_profile requires at least one vector")
    if base_power <= 0:
        raise MAHSSError("base_power must be > 0")
    if min_power <= 0 or max_power < min_power:
        raise MAHSSError("invalid radial power bounds")

    names = tuple(vectors.keys())
    q = l2_normalize(_as_vector(query, dim=dim, name="query"))
    prepared = {name: _as_vector(values, dim=dim, name=name) for name, values in vectors.items()}
    history_vectors = [
        l2_normalize(prepared[name])
        for name in path_history
        if name in prepared and float(np.linalg.norm(prepared[name])) > EPS
    ]
    history_set = set(path_history)
    profile: dict[str, dict[str, float]] = {}
    weights: dict[str, float] = {}
    history_len = len(path_history)

    for idx, name in enumerate(names):
        vector = prepared[name]
        direction = l2_normalize(vector)
        norm = float(np.linalg.norm(vector))
        alignment = max(0.0, float(np.dot(direction, q)))
        redundancy = max((max(0.0, float(np.dot(direction, prior))) for prior in history_vectors), default=0.0)
        novelty = 1.0 - redundancy
        phase = 0.5 + 0.5 * math.cos(2.0 * math.pi * ((idx + 1) * PHI + history_len / PHI))
        revisit_penalty = 0.125 if name in history_set else 0.0
        power = (
            base_power
            + radial_gain * alignment
            + novelty_gain * (novelty - 0.5)
            + quasicrystal_gain * (phase - 0.5)
            - revisit_penalty
        )
        power = max(min_power, min(max_power, power))
        weight = float(norm**power) if norm > EPS else 0.0
        weights[name] = weight
        profile[name] = {
            "norm": norm,
            "alignment": alignment,
            "redundancy": redundancy,
            "novelty": novelty,
            "quasicrystal_phase": phase,
            "power": power,
            "weight": weight,
            "probability": 0.0,
        }

    total = sum(weights.values())
    if total <= EPS:
        uniform = 1.0 / len(profile)
        for name in profile:
            profile[name]["probability"] = uniform
    else:
        for name, weight in weights.items():
            profile[name]["probability"] = weight / total
    return profile


def radial_power_probabilities(
    vectors: Mapping[str, Sequence[float]],
    query: Sequence[float],
    *,
    dim: int,
    path_history: Sequence[str] = (),
    base_power: float = 2.0,
    radial_gain: float = 0.125,
) -> dict[str, float]:
    """Return adaptive radial-power probabilities only."""

    profile = radial_power_profile(
        vectors,
        query,
        dim=dim,
        path_history=path_history,
        base_power=base_power,
        radial_gain=radial_gain,
    )
    return {name: row["probability"] for name, row in profile.items()}


def asymmetric_positive_well(
    vector: Sequence[float],
    *,
    dim: int,
    beta: float = 0.25,
    negative_gain: float = 1.0,
    name: str = "vector",
) -> tuple[float, ...]:
    """Continuous third-state transform: negative allowed, positive preferred.

    Positive coordinates pass through unchanged. Negative coordinates remain
    computable but are compressed by an exponential well:

        f(x) = x                         if x >= 0
             = beta * (exp(g*x) - 1)     if x < 0

    This is useful for centered physical deviations where being above target is
    usually helpful, being below target is allowed, and a hard ReLU wall would
    destroy reversible path telemetry.
    """

    if beta <= 0:
        raise MAHSSError("beta must be > 0")
    if negative_gain <= 0:
        raise MAHSSError("negative_gain must be > 0")
    values = _as_vector(vector, dim=dim, name=name)
    transformed = np.where(values >= 0.0, values, beta * (np.exp(negative_gain * values) - 1.0))
    return tuple(float(x) for x in transformed)


def asymmetric_well_probabilities(
    vectors: Mapping[str, Sequence[float]],
    query: Sequence[float],
    *,
    dim: int,
    beta: float = 0.25,
    negative_gain: float = 1.0,
    power: float = 2.0,
) -> dict[str, dict[str, float]]:
    """Probability profile over target-centered asymmetric potential wells.

    The selection energy is surplus-over-target divided by below-target debt.
    The transformed norm remains telemetry for the continuous well shape.
    """

    if not vectors:
        raise MAHSSError("asymmetric_well_probabilities requires at least one vector")
    if power <= 0:
        raise MAHSSError("power must be > 0")
    q = _as_vector(query, dim=dim, name="query")
    weights: dict[str, float] = {}
    transformed_norms: dict[str, float] = {}
    positive_residuals: dict[str, float] = {}
    negative_residuals: dict[str, float] = {}
    for name, values in vectors.items():
        vector = _as_vector(values, dim=dim, name=name)
        residual = vector - q
        positive_residuals[name] = float(np.linalg.norm(np.maximum(residual, 0.0)))
        negative_residuals[name] = float(np.linalg.norm(np.maximum(-residual, 0.0)))
        transformed = np.asarray(
            asymmetric_positive_well(
                residual,
                dim=dim,
                beta=beta,
                negative_gain=negative_gain,
                name=name,
            ),
            dtype=float,
        )
        norm = float(np.linalg.norm(transformed))
        transformed_norms[name] = norm
        surplus = positive_residuals[name]
        debt = negative_residuals[name]
        weights[name] = float((surplus**power) / (1.0 + negative_gain * (debt**power))) if surplus > EPS else 0.0
    total = sum(weights.values())
    if total <= EPS:
        probabilities = {name: 1.0 / len(weights) for name in weights}
    else:
        probabilities = {name: value / total for name, value in weights.items()}
    return {
        name: {
            "probability": probabilities[name],
            "transformed_norm": transformed_norms[name],
            "positive_residual_norm": positive_residuals[name],
            "negative_residual_norm": negative_residuals[name],
        }
        for name in vectors
    }


def polar_vector_probabilities(
    vectors: Mapping[str, Sequence[float]],
    *,
    dim: int,
    power: float = 2.0,
) -> dict[str, dict[str, float]]:
    """Split vectors into positive and negative origin probability surfaces.

    This is the deterministic math form of a dual signed superposition: each
    candidate has a positive-origin magnitude and a negative-origin magnitude.
    The output is not a quantum sample; it is a signed probability receipt that
    exposes which candidates are supported by positive, negative, or mixed
    evidence.
    """

    if not vectors:
        raise MAHSSError("polar_vector_probabilities requires at least one vector")
    if power <= 0:
        raise MAHSSError("power must be > 0")
    positive_weights: dict[str, float] = {}
    negative_weights: dict[str, float] = {}
    for name, values in vectors.items():
        vector = _as_vector(values, dim=dim, name=name)
        positive = np.maximum(vector, 0.0)
        negative = np.maximum(-vector, 0.0)
        positive_weights[name] = float(np.linalg.norm(positive) ** power)
        negative_weights[name] = float(np.linalg.norm(negative) ** power)

    def normalize(weights: Mapping[str, float]) -> dict[str, float]:
        total = sum(weights.values())
        if total <= EPS:
            uniform = 1.0 / len(weights)
            return {name: uniform for name in weights}
        return {name: value / total for name, value in weights.items()}

    pos_probs = normalize(positive_weights)
    neg_probs = normalize(negative_weights)
    out: dict[str, dict[str, float]] = {}
    for name in vectors:
        total_weight = positive_weights[name] + negative_weights[name]
        if total_weight <= EPS:
            polarity = 0.0
        else:
            polarity = (positive_weights[name] - negative_weights[name]) / total_weight
        contrast = abs(pos_probs[name] - neg_probs[name])
        entropy = 0.0
        for value in (pos_probs[name], neg_probs[name]):
            if value > EPS:
                entropy -= value * math.log2(value)
        out[name] = {
            "positive_probability": pos_probs[name],
            "negative_probability": neg_probs[name],
            "polarity": polarity,
            "contrast": contrast,
            "dual_entropy": entropy,
        }
    return out


def polar_split(vector: Sequence[float], *, dim: int, name: str = "vector") -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Bijective signed split into positive and negative origin channels.

    Forward:
        x_pos = max(x, 0), x_neg = max(-x, 0)

    Reverse:
        x = x_pos - x_neg

    This split does not require symmetry. The in-between space is usable as
    long as both channels are retained. Probability summaries remain
    non-bijective projections because norms collapse coordinate detail.
    """

    values = _as_vector(vector, dim=dim, name=name)
    positive = np.maximum(values, 0.0)
    negative = np.maximum(-values, 0.0)
    return tuple(float(x) for x in positive), tuple(float(x) for x in negative)


def polar_reconstruct(
    positive: Sequence[float],
    negative: Sequence[float],
    *,
    dim: int,
) -> tuple[float, ...]:
    """Reconstruct a vector from its bijective polar split."""

    pos = _as_vector(positive, dim=dim, name="positive")
    neg = _as_vector(negative, dim=dim, name="negative")
    return tuple(float(x) for x in pos - neg)


def intention_router(
    query: Sequence[float],
    mechanism_names: Sequence[str],
    *,
    config: MAHSSConfig = MAHSSConfig(),
) -> dict[str, float]:
    """Map a query vector onto mechanism role vectors.

    NOTE: roles are content-free random hashes, so this router only carries
    mechanism affinity when the role vectors have been learned or when the
    query was explicitly projected into role-space. For content-aware
    routing without learned roles, use ``intention_router_via_outputs``.
    """

    q = l2_normalize(_as_vector(query, dim=config.dim, name="query"))
    scores = {
        name: float(np.dot(q, role_vector(name, config.dim, normalize=config.normalize_roles)))
        for name in mechanism_names
    }
    return softmax(scores, temperature=config.router_temperature)


def intention_router_via_outputs(
    query: Sequence[float],
    attention_outputs: Mapping[str, Sequence[float]],
    *,
    config: MAHSSConfig = MAHSSConfig(),
) -> dict[str, float]:
    """Content-aware router: project the query into role-space via the
    attention outputs that carry mechanism content.

    For each mechanism k, score the query by its similarity to the output
    vector v_k that mechanism k actually produced. This is the missing piece
    the random-role-hash auto-router lacks: the score depends on the
    mechanism's content, not just its name.

    Equivalent to a one-step query-projection: the query is first asked
    "which mechanism's output best matches my direction?" and the answer
    populates the router weights. Composes with the HRR fold/unbinding
    pipeline downstream because role vectors are still used for binding —
    only the routing decision uses output-similarity.
    """

    q = l2_normalize(_as_vector(query, dim=config.dim, name="query"))
    scores: dict[str, float] = {}
    for name, vector in attention_outputs.items():
        v = l2_normalize(_as_vector(vector, dim=config.dim, name=name))
        scores[name] = float(np.dot(q, v))
    return softmax(scores, temperature=config.router_temperature)


def mobius_add(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Möbius addition in the unit Poincare ball."""

    u2 = float(np.dot(u, u))
    v2 = float(np.dot(v, v))
    uv = float(np.dot(u, v))
    denom = 1.0 + 2.0 * uv + u2 * v2
    if abs(denom) <= EPS:
        raise MAHSSError("Möbius denominator collapsed")
    out = ((1.0 + 2.0 * uv + v2) * u + (1.0 - u2) * v) / denom
    norm = float(np.linalg.norm(out))
    if norm >= 1.0:
        out = out / (norm + EPS) * (1.0 - 1e-9)
    return out


def mobius_phase_fold(vector: Sequence[float], *, config: MAHSSConfig = MAHSSConfig()) -> np.ndarray:
    """Bounded Layer-7-style fold used as an isometric phase proxy.

    The vector is projected inside the unit ball, rotated by one index, then
    Möbius-translated by a small phi-scaled phase vector. This preserves the
    "same graph, denser chart" contract without requiring a learned manifold.
    """

    raw = _as_vector(vector, dim=config.dim, name="vector")
    inside = l2_normalize(raw) * min(0.85, float(np.linalg.norm(raw)) / (float(np.linalg.norm(raw)) + 1.0))
    rotated = np.roll(inside, 1)
    phase = np.zeros(config.dim, dtype=float)
    phase[0] = config.fold_strength / PHI
    folded = mobius_add(rotated, phase)
    return folded


def build_mahss(
    attention_outputs: Mapping[str, Sequence[float]],
    query: Sequence[float],
    *,
    config: MAHSSConfig | None = None,
    router_weights: Mapping[str, float] | None = None,
) -> MAHSSResult:
    """Bind, superpose, fold, unbind, and score attention outputs."""

    cfg = config or MAHSSConfig()
    if not attention_outputs:
        raise MAHSSError("attention_outputs must not be empty")
    names = tuple(attention_outputs.keys())
    vectors = {name: _as_vector(value, dim=cfg.dim, name=name) for name, value in attention_outputs.items()}
    q = _as_vector(query, dim=cfg.dim, name="query")

    weights = dict(router_weights) if router_weights is not None else intention_router(q, names, config=cfg)
    missing = set(names).difference(weights)
    extra = set(weights).difference(names)
    if missing or extra:
        raise MAHSSError(f"router weight keys must match mechanisms; missing={missing}, extra={extra}")
    weight_total = sum(float(value) for value in weights.values())
    if weight_total <= EPS:
        raise MAHSSError("router weights must sum to a positive value")
    weights = {name: float(value) / weight_total for name, value in weights.items()}

    bound_vectors = []
    for name in names:
        role = role_vector(name, cfg.dim, normalize=cfg.normalize_roles)
        bound_vectors.append(weights[name] * circular_convolution(role, vectors[name]))
    superposition = np.sum(np.vstack(bound_vectors), axis=0)
    folded = mobius_phase_fold(superposition, config=cfg)

    illumination: dict[str, float] = {}
    for name in names:
        role = role_vector(name, cfg.dim, normalize=cfg.normalize_roles)
        unbound = circular_correlation(role, folded)
        illumination[name] = float(np.dot(l2_normalize(unbound), l2_normalize(q)))

    ranked = sorted(illumination.items(), key=lambda item: item[1], reverse=True)
    selected = ranked[0][0]
    peak_margin = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0)
    raw_norm = float(np.linalg.norm(superposition))
    folded_norm = float(np.linalg.norm(folded))
    cross_manifold_strain = abs(folded_norm - min(0.85, raw_norm / (raw_norm + 1.0)))

    telemetry = {
        "selected_mechanism": selected,
        "peak_margin": float(peak_margin),
        "cross_manifold_strain": float(cross_manifold_strain),
        "router_entropy": float(-sum(w * math.log2(max(w, EPS)) for w in weights.values())),
        "folded_norm": folded_norm,
    }

    return MAHSSResult(
        schema_version="scbe_mahss_v1",
        mechanism_names=names,
        router_weights={name: round(weights[name], 12) for name in names},
        raw_superposition=tuple(float(x) for x in superposition),
        folded_vector=tuple(float(x) for x in folded),
        illumination={name: round(illumination[name], 12) for name in names},
        selected_mechanism=selected,
        peak_margin=float(peak_margin),
        cross_manifold_strain=float(cross_manifold_strain),
        telemetry=telemetry,
    )


def toy_attention_outputs(dim: int = 64) -> dict[str, tuple[float, ...]]:
    """Small deterministic toy board for demonstrations and tests."""

    if dim < 8:
        raise MAHSSError("toy dim must be >= 8")
    dense = np.zeros(dim, dtype=float)
    sparse = np.zeros(dim, dtype=float)
    state = np.zeros(dim, dtype=float)
    dense[0:4] = [1.0, 0.8, 0.6, 0.4]
    sparse[dim // 2 : dim // 2 + 4] = [0.5, 1.0, 0.5, 1.0]
    state[-4:] = [0.25, 0.5, 0.75, 1.0]
    return {
        "dense_global": tuple(dense),
        "sparse_local": tuple(sparse),
        "state_space": tuple(state),
    }


__all__ = [
    "MAHSSConfig",
    "MAHSSError",
    "MAHSSResult",
    "build_mahss",
    "asymmetric_positive_well",
    "asymmetric_well_probabilities",
    "clear_role_vector_cache",
    "circular_convolution",
    "circular_correlation",
    "intention_router",
    "intention_router_via_outputs",
    "l2_normalize",
    "length_square_probabilities",
    "length_square_router",
    "mobius_add",
    "mobius_phase_fold",
    "polar_reconstruct",
    "polar_split",
    "polar_vector_probabilities",
    "radial_power_probabilities",
    "radial_power_profile",
    "role_vector",
    "role_vector_cache_info",
    "softmax",
    "toy_attention_outputs",
]
