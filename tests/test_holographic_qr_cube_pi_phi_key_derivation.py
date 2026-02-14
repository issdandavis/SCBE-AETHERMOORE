import hashlib
import importlib
import math
import random

import pytest

PHI_SPEC = 1.618033988749895


# -----------------------------
# Discovery: locate derivation fn
# -----------------------------

def _load_pi_phi_deriver():
    """
    Attempts to locate a callable pi^phi derivation function across likely modules.
    """
    candidates = [
        ("src.polly_pads_runtime", ["harmonic_cost", "access_cost", "pi_phi_key_derivation", "derive_pi_phi_key"]),
        ("src.scbe_14layer_reference", ["pi_phi_key_derivation", "derive_pi_phi_key", "pi_phi_wall", "harmonic_wall"]),
        ("src.holographic_qr_cube", ["pi_phi_key_derivation", "derive_pi_phi_key", "pi_phi_wall", "harmonic_wall"]),
        ("src.qr_cube", ["pi_phi_key_derivation", "derive_pi_phi_key", "pi_phi_wall", "harmonic_wall"]),
        ("src.layer12_harmonic_scaling", ["pi_phi_key_derivation", "derive_pi_phi_key", "pi_phi_wall", "harmonic_wall"]),
        ("src.kernel.harmonic_scaling", ["pi_phi_key_derivation", "derive_pi_phi_key", "pi_phi_wall", "harmonic_wall"]),
    ]

    last_err = None
    for module_name, fn_names in candidates:
        try:
            mod = importlib.import_module(module_name)
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue

        for fn_name in fn_names:
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                return module_name, fn_name, fn, mod

    raise ImportError(
        "Could not locate a callable pi^phi key-derivation function.\n"
        "Tried modules/functions:\n"
        + "\n".join([f"- {m}: {', '.join(fns)}" for m, fns in candidates])
        + (f"\nLast import error: {last_err!r}" if last_err else "")
    )


@pytest.fixture(scope="session")
def pi_phi_deriver():
    return _load_pi_phi_deriver()


# -----------------------------
# Helpers
# -----------------------------

def _expected_scalar(R: float, d_star: float, phi: float = PHI_SPEC) -> float:
    # Spec: H(d*,R) = R * pi^(phi*d*)
    return float(R) * (math.pi ** (phi * float(d_star)))


def _call_deriver(fn, R: float, d_star: float):
    """
    Supports typical signature conventions:
      - fn(d_star, R)
      - fn(R, d_star)
      - fn(d_star=d_star, R=R)
      - fn(R=R, d_star=d_star)
      - fn(d_star=d_star, r=R)  # common lowercase radius naming
    """
    kw_trials = [
        {"d_star": d_star, "R": R},
        {"d": d_star, "R": R},
        {"distance_star": d_star, "R": R},
        {"R": R, "d_star": d_star},
        {"R": R, "d": d_star},
        {"d_star": d_star, "r": R},
        {"r": R, "d_star": d_star},
    ]
    for kwargs in kw_trials:
        try:
            return fn(**kwargs)
        except TypeError:
            pass

    try:
        return fn(d_star, R)
    except TypeError:
        return fn(R, d_star)


def _as_scalar_or_bytes(out):
    if isinstance(out, (float, int)):
        return float(out)
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    if isinstance(out, dict):
        if "H" in out:
            h = out["H"]
            if isinstance(h, (float, int)):
                return float(h)
        if "key" in out:
            k = out["key"]
            if isinstance(k, (bytes, bytearray)):
                return bytes(k)
    raise TypeError(f"Unsupported return type from pi^phi derivation: {type(out)}")


def _hash_bytes(x: bytes) -> bytes:
    return hashlib.sha256(x).digest()


# -----------------------------
# Tests
# -----------------------------

def test_phi_constant_if_exposed_matches_spec(pi_phi_deriver):
    _, _, _, mod = pi_phi_deriver
    phi = getattr(mod, "PHI", None)
    if phi is not None:
        assert math.isfinite(float(phi))
        assert float(phi) == pytest.approx(PHI_SPEC, rel=0.0, abs=1e-12)


def test_d_star_zero_returns_R_for_scalar_impl(pi_phi_deriver):
    _, _, fn, _ = pi_phi_deriver
    for R in [0.0, 1.0, 2.5, 10.0, 1e-9, 1e6]:
        out = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=0.0))
        if isinstance(out, float):
            assert out == pytest.approx(R, rel=0.0, abs=1e-12)


def test_matches_spec_formula_for_reasonable_ranges_scalar(pi_phi_deriver):
    _, _, fn, mod = pi_phi_deriver
    phi = float(getattr(mod, "PHI", PHI_SPEC))

    test_points = [
        (1.0, 0.1),
        (2.0, 0.5),
        (0.5, 1.0),
        (10.0, 2.0),
        (3.14159, -0.25),
    ]

    for R, d_star in test_points:
        out = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d_star))
        if not isinstance(out, float):
            pytest.skip("pi^phi derivation returns bytes; scalar formula test not applicable")
        exp = _expected_scalar(R=R, d_star=d_star, phi=phi)
        assert out == pytest.approx(exp, rel=1e-12, abs=1e-12)


def test_monotonic_increasing_in_d_star_for_positive_R_scalar(pi_phi_deriver):
    _, _, fn, _ = pi_phi_deriver
    R = 1.0
    d_values = [-1.0, -0.5, 0.0, 0.25, 0.5, 1.0, 1.5]

    outs = []
    for d in d_values:
        out = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d))
        if not isinstance(out, float):
            pytest.skip("pi^phi derivation returns bytes; monotonic scalar test not applicable")
        outs.append(out)

    for a, b in zip(outs, outs[1:]):
        assert b > a


def test_ratio_property_scalar(pi_phi_deriver):
    _, _, fn, mod = pi_phi_deriver
    phi = float(getattr(mod, "PHI", PHI_SPEC))
    R = 1.7
    d1, d2 = 0.3, 1.8

    out1 = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d1))
    out2 = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d2))
    if not (isinstance(out1, float) and isinstance(out2, float)):
        pytest.skip("pi^phi derivation returns bytes; scalar ratio test not applicable")

    ratio = out2 / out1
    expected_ratio = math.pi ** (phi * (d2 - d1))
    assert ratio == pytest.approx(expected_ratio, rel=1e-12, abs=1e-12)


def test_log_identity_scalar(pi_phi_deriver):
    _, _, fn, mod = pi_phi_deriver
    phi = float(getattr(mod, "PHI", PHI_SPEC))
    R = 4.2

    for d_star in [-0.75, -0.1, 0.2, 0.9, 1.3]:
        out = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d_star))
        if not isinstance(out, float):
            pytest.skip("pi^phi derivation returns bytes; scalar log identity test not applicable")
        if out <= 0 or R <= 0:
            continue
        lhs = math.log(out / R) / math.log(math.pi)
        rhs = phi * d_star
        assert lhs == pytest.approx(rhs, rel=1e-12, abs=1e-12)


def test_small_delta_in_d_star_changes_output_smoothly_scalar(pi_phi_deriver):
    _, _, fn, _ = pi_phi_deriver
    R = 1.0
    d = 0.8
    eps = 1e-9

    base = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d))
    shifted = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d + eps))

    if not (isinstance(base, float) and isinstance(shifted, float)):
        pytest.skip("pi^phi derivation returns bytes; scalar smoothness test not applicable")

    assert shifted != base
    assert math.isfinite(shifted)
    assert abs(shifted - base) / abs(base) < 1e-6


def test_large_d_star_overflow_behavior_scalar(pi_phi_deriver):
    _, _, fn, _ = pi_phi_deriver
    R = 1.0
    huge = 1e6

    try:
        out = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=huge))
    except (OverflowError, ValueError):
        return

    if isinstance(out, float):
        assert not math.isfinite(out) or out == float("inf")
    else:
        assert isinstance(out, (bytes, bytearray))


def test_bytes_kdf_determinism_if_bytes(pi_phi_deriver):
    _, _, fn, _ = pi_phi_deriver

    R = 1.5
    d1 = 0.25
    d2 = 0.30

    out1 = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d1))
    if isinstance(out1, float):
        pytest.skip("pi^phi derivation returns scalar; bytes determinism test not applicable")

    out1b = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d1))
    assert out1 == out1b

    out2 = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d2))
    assert _hash_bytes(out1) != _hash_bytes(out2)


def test_randomized_regression_against_spec_scalar(pi_phi_deriver):
    _, _, fn, mod = pi_phi_deriver
    phi = float(getattr(mod, "PHI", PHI_SPEC))

    rng = random.Random(1337)
    for _ in range(100):
        R = 10 ** rng.uniform(-3, 3)
        d_star = rng.uniform(-2.0, 2.0)
        out = _as_scalar_or_bytes(_call_deriver(fn, R=R, d_star=d_star))
        if not isinstance(out, float):
            pytest.skip("pi^phi derivation returns bytes; scalar randomized test not applicable")
        exp = _expected_scalar(R=R, d_star=d_star, phi=phi)
        assert out == pytest.approx(exp, rel=1e-11, abs=1e-12)
