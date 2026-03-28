from __future__ import annotations

import json
import math
from pathlib import Path

import pytest


def poincare_distance(u: list[float], v: list[float]) -> float:
    if len(u) != len(v):
        raise ValueError("vectors must have the same dimension")

    norm_u_sq = sum(x * x for x in u)
    norm_v_sq = sum(x * x for x in v)
    if norm_u_sq >= 1.0 or norm_v_sq >= 1.0:
        raise ValueError("points must lie strictly inside the unit ball")

    diff_sq = sum((a - b) ** 2 for a, b in zip(u, v))
    denominator = (1.0 - norm_u_sq) * (1.0 - norm_v_sq)
    arg = 1.0 + (2.0 * diff_sq) / denominator
    return math.acosh(arg)


def _load_vectors() -> dict:
    root = Path(__file__).resolve().parents[2]
    vector_path = root / "tests" / "interop" / "polyglot_vectors" / "poincare_distance.v1.json"
    return json.loads(vector_path.read_text(encoding="utf-8"))


def test_vector_fixture_metadata() -> None:
    vectors = _load_vectors()
    assert vectors["metric"] == "poincare_distance"
    assert vectors["version"] == "1.0.0"
    assert len(vectors["cases"]) > 0


def test_python_matches_polyglot_vectors() -> None:
    vectors = _load_vectors()
    for entry in vectors["cases"]:
        actual = poincare_distance(entry["u"], entry["v"])
        assert actual == pytest.approx(entry["expected"], rel=0.0, abs=1e-12)
