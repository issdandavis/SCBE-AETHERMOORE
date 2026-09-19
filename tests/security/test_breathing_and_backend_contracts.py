"""Security boundary and numerical contracts, not cryptographic certification."""

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_file(tree, relative):
    name = "contract_" + (tree + relative).replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, ROOT / tree / "scbe_aethermoore" / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=["src/symphonic_cipher", "symphonic_cipher"])
def layers(request):
    return load_file(request.param, "layers/fourteen_layer_pipeline.py")


def test_positive_cycle_and_reciprocal_half_cycle(layers):
    for t in np.linspace(-120, 120, 481):
        b = layers.breathing_factor(t)
        assert 0.4 - 1e-14 <= b <= 2.5 + 1e-14
        assert b * layers.breathing_factor(t + 30) == pytest.approx(1)


def test_inverse_and_jacobian_against_independent_finite_differences(layers):
    rng = np.random.default_rng(7129)
    for t in (0, 15, 30, 45, 60):
        for radius in (0, 1e-14, 0.01, 0.4, 0.85):
            point = rng.normal(size=6)
            point *= radius / np.linalg.norm(point)
            result = layers.layer_6_breathing(point, t)
            assert np.linalg.norm(result) < 1
            np.testing.assert_allclose(layers.layer_6_inverse(result, t), point, atol=2e-12)
            jacobian = layers.layer_6_breathing_jacobian(point, t)
            assert np.linalg.eigvalsh(jacobian).min() > 0
            delta = 1e-6 * np.eye(6)
            numeric = np.column_stack(
                [
                    (layers.layer_6_breathing(point + d, t) - layers.layer_6_breathing(point - d, t)) / 2e-6
                    for d in delta
                ]
            )
            np.testing.assert_allclose(jacobian, numeric, atol=2e-8, rtol=2e-7)


def test_distance_changes_as_declared_without_collapsing_points(layers):
    a, b = np.zeros(2), np.array([0.25, 0])
    distance = layers.layer_5_hyperbolic_distance(a, b)
    for t in (15, 45):
        moved = layers.layer_6_breathing(b, t)
        assert not np.array_equal(moved, a)
        assert layers.layer_5_hyperbolic_distance(a, moved) == pytest.approx(layers.breathing_factor(t) * distance)


@pytest.mark.parametrize("point", [[math.nan, 0], [math.inf, 0], [1, 0], [2, 0], [], [[0.1, 0]]])
def test_invalid_ball_domain_rejected(layers, point):
    for operation in (layers.layer_6_breathing, layers.layer_6_inverse, layers.layer_6_breathing_jacobian):
        with pytest.raises(ValueError):
            operation(point, 0)


@pytest.mark.parametrize("args", [(math.nan,), (math.inf,), (True,), (0, -1), (0, 2), (0, 1, math.nan)])
def test_invalid_breathing_parameters_rejected(layers, args):
    with pytest.raises(ValueError):
        layers.breathing_factor(*args)


@pytest.fixture(params=["src/symphonic_cipher", "symphonic_cipher"])
def pqc(request, monkeypatch):
    monkeypatch.setenv("SCBE_FORCE_SKIP_LIBOQS", "1")
    monkeypatch.delenv("SCBE_ALLOW_MOCK_PQC", raising=False)
    monkeypatch.delenv("SCBE_ENV", raising=False)
    module = load_file(request.param, "pqc/pqc_core.py")
    assert module.get_backend() == module.PQCBackend.MOCK
    return module


@pytest.mark.parametrize(
    "mode,flag", [(None, None), ("production", "1"), ("test", None), (None, "1"), ("test", "true")]
)
def test_no_implicit_mock_crypto(pqc, monkeypatch, mode, flag):
    if mode is not None:
        monkeypatch.setenv("SCBE_ENV", mode)
    if flag is not None:
        monkeypatch.setenv("SCBE_ALLOW_MOCK_PQC", flag)
    for operation in (pqc.Kyber768.generate_keypair, pqc.Dilithium3.generate_keypair):
        with pytest.raises(RuntimeError, match="Real PQC backend unavailable"):
            operation()
    assert pqc.Dilithium3.verify(b"x", b"m", b"s") is False


def test_explicit_mock_fixture_can_be_revoked(pqc, monkeypatch):
    monkeypatch.setenv("SCBE_ENV", "test")
    monkeypatch.setenv("SCBE_ALLOW_MOCK_PQC", "1")
    kem = pqc.Kyber768.generate_keypair()
    exchange = pqc.Kyber768.encapsulate(kem.public_key)
    assert pqc.Kyber768.decapsulate(kem.secret_key, exchange.ciphertext) == exchange.shared_secret
    sig = pqc.Dilithium3.generate_keypair()
    signed = pqc.Dilithium3.sign(sig.secret_key, b"fixture")
    assert pqc.Dilithium3.verify(sig.public_key, b"fixture", signed)
    monkeypatch.delenv("SCBE_ALLOW_MOCK_PQC")
    assert not pqc.Dilithium3.verify(sig.public_key, b"fixture", signed)
    for operation in (
        lambda: pqc.Kyber768.encapsulate(kem.public_key),
        lambda: pqc.Kyber768.decapsulate(kem.secret_key, exchange.ciphertext),
        lambda: pqc.Dilithium3.sign(sig.secret_key, b"fixture"),
    ):
        with pytest.raises(RuntimeError):
            operation()
