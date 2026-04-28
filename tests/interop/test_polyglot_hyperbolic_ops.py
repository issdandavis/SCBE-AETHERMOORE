from __future__ import annotations

import json
import math
from pathlib import Path

import pytest


PHI = (1.0 + math.sqrt(5.0)) / 2.0
EPS = 1e-15


def _dot(u: list[float], v: list[float]) -> float:
    return sum(a * b for a, b in zip(u, v))


def _norm_sq(u: list[float]) -> float:
    return sum(a * a for a in u)


def _norm(u: list[float]) -> float:
    return math.sqrt(_norm_sq(u))


def _scale(u: list[float], s: float) -> list[float]:
    return [a * s for a in u]


def _neg(u: list[float]) -> list[float]:
    return [-a for a in u]


def mobius_addition(u: list[float], v: list[float]) -> list[float]:
    if len(u) != len(v):
        raise ValueError("vectors must have the same dimension")
    uv = _dot(u, v)
    nu_sq = _norm_sq(u)
    nv_sq = _norm_sq(v)
    coef_u = 1.0 + 2.0 * uv + nv_sq
    coef_v = 1.0 - nu_sq
    denom = 1.0 + 2.0 * uv + nu_sq * nv_sq
    return [(coef_u * a + coef_v * b) / denom for a, b in zip(u, v)]


def exponential_map(p: list[float], v: list[float]) -> list[float]:
    if len(p) != len(v):
        raise ValueError("base and tangent must have the same dimension")
    n_v = _norm(v)
    if n_v < EPS:
        return list(p)
    np_sq = _norm_sq(p)
    if np_sq >= 1.0:
        raise ValueError("base point must lie strictly inside the unit ball")
    lam_p = 2.0 / (1.0 - np_sq)
    factor = math.tanh(lam_p * n_v / 2.0)
    direction = _scale(v, 1.0 / n_v)
    delta = _scale(direction, factor)
    return mobius_addition(p, delta)


def logarithmic_map(p: list[float], q: list[float]) -> list[float]:
    if len(p) != len(q):
        raise ValueError("base and target must have the same dimension")
    np_sq = _norm_sq(p)
    nq_sq = _norm_sq(q)
    if np_sq >= 1.0 or nq_sq >= 1.0:
        raise ValueError("points must lie strictly inside the unit ball")
    diff = mobius_addition(_neg(p), q)
    n_diff = _norm(diff)
    if n_diff < EPS:
        return [0.0] * len(p)
    lam_p = 2.0 / (1.0 - np_sq)
    z = max(min(n_diff, 1.0 - EPS), -1.0 + EPS)
    artanh_z = 0.5 * math.log((1.0 + z) / (1.0 - z))
    factor = (2.0 / lam_p) * artanh_z
    direction = _scale(diff, 1.0 / n_diff)
    return _scale(direction, factor)


def harmonic_wall_phi(d: float, phase_deviation: float = 0.0) -> float:
    if d < 0.0:
        raise ValueError("d must be >= 0")
    if phase_deviation < 0.0:
        raise ValueError("phase_deviation must be >= 0")
    return 1.0 / (1.0 + PHI * d + 2.0 * phase_deviation)


def _load(name: str) -> dict:
    root = Path(__file__).resolve().parents[2]
    return json.loads(
        (root / "tests" / "interop" / "polyglot_vectors" / name).read_text(encoding="utf-8")
    )


def _approx_vector(actual: list[float], expected: list[float]) -> None:
    assert len(actual) == len(expected)
    for a, e in zip(actual, expected):
        assert a == pytest.approx(e, rel=0.0, abs=1e-12)


def test_mobius_addition_metadata_and_parity() -> None:
    fixture = _load("mobius_addition.v1.json")
    assert fixture["metric"] == "mobius_addition"
    assert fixture["version"] == "1.0.0"
    assert len(fixture["cases"]) > 0
    for case in fixture["cases"]:
        actual = mobius_addition(case["u"], case["v"])
        _approx_vector(actual, case["expected"])


def test_exponential_map_metadata_and_parity() -> None:
    fixture = _load("exponential_map.v1.json")
    assert fixture["metric"] == "exponential_map"
    assert fixture["version"] == "1.0.0"
    assert len(fixture["cases"]) > 0
    for case in fixture["cases"]:
        actual = exponential_map(case["p"], case["v"])
        _approx_vector(actual, case["expected"])


def test_logarithmic_map_metadata_and_parity() -> None:
    fixture = _load("logarithmic_map.v1.json")
    assert fixture["metric"] == "logarithmic_map"
    assert fixture["version"] == "1.0.0"
    assert len(fixture["cases"]) > 0
    for case in fixture["cases"]:
        actual = logarithmic_map(case["p"], case["q"])
        _approx_vector(actual, case["expected"])


def test_harmonic_wall_metadata_and_parity() -> None:
    fixture = _load("harmonic_wall.v1.json")
    assert fixture["metric"] == "harmonic_wall_phi"
    assert fixture["version"] == "1.0.0"
    assert fixture["phi"] == pytest.approx(PHI, rel=0.0, abs=1e-15)
    assert len(fixture["cases"]) > 0
    for case in fixture["cases"]:
        actual = harmonic_wall_phi(case["d"], case["pd"])
        assert actual == pytest.approx(case["expected"], rel=0.0, abs=1e-12)


def test_log_then_exp_round_trip() -> None:
    """log_p ∘ exp_p = identity (within tolerance) on the tangent vector."""
    fixture = _load("logarithmic_map.v1.json")
    for case in fixture["cases"]:
        p, q = case["p"], case["q"]
        v = logarithmic_map(p, q)
        q_hat = exponential_map(p, v)
        _approx_vector(q_hat, q)
