from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATHS = [
    ROOT / "src/symphonic_cipher/scbe_aethermoore/layers_9_12.py",
    ROOT / "symphonic_cipher/scbe_aethermoore/layers_9_12.py",
]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=list(enumerate(MODULE_PATHS)))
def layers(request):
    index, path = request.param
    return load(path, f"l03_l12_clean_{index}")


def test_bounded_score_domain_and_named_cost(layers):
    values = [layers.harmonic_scaling(d, phase_deviation=0.2) for d in (0.0, 0.5, 2.0)]
    assert 0.0 < values[2] < values[1] < values[0] <= 1.0
    with pytest.raises(ValueError):
        layers.harmonic_scaling(-1.0)
    assert layers.quadratic_exp_cost(2.0, base=math.e) == pytest.approx(math.exp(4.0))


def test_risk_increases_with_distance(layers):
    fixed = dict(s_spec=0.7, c_spin=0.6, d_tri_norm=0.3, tau=0.8, s_audio=0.9)
    values = [layers.compute_risk(**fixed, d_star=d).r_hat for d in (0.0, 0.5, 2.0)]
    assert values[0] < values[1] < values[2]


def test_live_gradient_matches_finite_difference(layers):
    args = dict(
        s_spec=0.7,
        c_spin=0.6,
        d_tri_norm=0.3,
        tau=0.8,
        s_audio=0.9,
        d_star=0.4,
        phase_deviation=0.13,
        rho=1.2,
    )
    analytical = layers.risk_gradient(**args)
    names = {
        "s_spec": "s_spec",
        "c_spin": "c_spin",
        "d_tri_norm": "d_tri",
        "tau": "tau",
        "s_audio": "s_audio",
        "d_star": "d_star",
        "phase_deviation": "phase_deviation",
    }
    step = 1e-6
    for parameter, result_key in names.items():
        plus, minus = dict(args), dict(args)
        plus[parameter] += step
        minus[parameter] -= step
        numerical = (layers.compute_risk(**plus).r_hat - layers.compute_risk(**minus).r_hat) / (2 * step)
        assert analytical[result_key] == pytest.approx(numerical, abs=1e-7)


def test_internal_contract_suite(layers):
    result = layers.self_test()
    assert result["passed"] == result["total"] == 10
