from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "src"):
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from scbe_chiral_chladni import (  # noqa: E402
    ChiralModeAddress,
    authorize_transition,
    derive_binding_token,
    derive_separator_token,
    seal_egg,
    transition_requires_separator,
    verify_egg,
)

SECRET = b"scbe-chiral-secret"
PAYLOAD = b"SacredEgg::payload"
MANIFOLD = (0.11, -0.07, 0.05, 0.09, -0.03, 0.04)
OTHER_MANIFOLD = (0.11, -0.07, 0.05, 0.09, -0.03, 0.045)
SAMPLES = (
    (0.13, 0.27),
    (0.41, 0.19),
    (0.73, 0.62),
)


def test_zero_chiral_weight_recovers_standard_mirror_antisymmetry() -> None:
    mode = ChiralModeAddress(3, 5, handedness="R", chiral_weight=0.0)

    for x, y in SAMPLES:
        assert mode.raw_field(y, x) == pytest.approx(-mode.raw_field(x, y), abs=1e-12)
        assert mode.anti_mirror_residual(x, y) == pytest.approx(0.0, abs=1e-12)

    assert not mode.breaks_diagonal_mirror(SAMPLES, tol=1e-9)


def test_chiral_branch_breaks_diagonal_mirror_symmetry() -> None:
    mode = ChiralModeAddress(3, 5, handedness="R", chiral_weight=0.2)

    assert mode.breaks_diagonal_mirror(SAMPLES, tol=1e-6)

    residuals = [abs(mode.anti_mirror_residual(x, y)) for x, y in SAMPLES]
    assert max(residuals) > 1e-6


def test_left_and_right_handed_branches_are_distinct_in_the_field() -> None:
    left = ChiralModeAddress(3, 5, handedness="L", chiral_weight=0.2)
    right = ChiralModeAddress(3, 5, handedness="R", chiral_weight=0.2)

    diffs = [abs(left.raw_field(x, y) - right.raw_field(x, y)) for x, y in SAMPLES]
    assert max(diffs) > 1e-6


def test_readout_remains_non_negative() -> None:
    mode = ChiralModeAddress(-3, 5, handedness="L", chiral_weight=0.2)

    for x, y in SAMPLES:
        assert mode.readout(x, y) >= 0.0


def test_binding_token_changes_with_handedness() -> None:
    left = ChiralModeAddress(3, 5, handedness="L", chiral_weight=0.2)
    right = ChiralModeAddress(3, 5, handedness="R", chiral_weight=0.2)

    assert derive_binding_token(left, MANIFOLD, SECRET) != derive_binding_token(right, MANIFOLD, SECRET)


def test_binding_token_changes_with_sign_quadrant() -> None:
    tokens = {
        derive_binding_token(ChiralModeAddress(3, 5, "R", 0.2), MANIFOLD, SECRET),
        derive_binding_token(ChiralModeAddress(-3, 5, "R", 0.2), MANIFOLD, SECRET),
        derive_binding_token(ChiralModeAddress(3, -5, "R", 0.2), MANIFOLD, SECRET),
        derive_binding_token(ChiralModeAddress(-3, -5, "R", 0.2), MANIFOLD, SECRET),
    }
    assert len(tokens) == 4


def test_wrong_handedness_fails_egg_verification() -> None:
    sealed_mode = ChiralModeAddress(3, 5, handedness="R", chiral_weight=0.2)
    wrong_mode = ChiralModeAddress(3, 5, handedness="L", chiral_weight=0.2)

    egg = seal_egg(PAYLOAD, sealed_mode, MANIFOLD, SECRET, realm="validation")
    assert verify_egg(egg, PAYLOAD, sealed_mode, MANIFOLD, SECRET, realm="validation")
    assert not verify_egg(egg, PAYLOAD, wrong_mode, MANIFOLD, SECRET, realm="validation")


def test_wrong_manifold_fails_egg_verification() -> None:
    mode = ChiralModeAddress(-3, 5, handedness="L", chiral_weight=0.2)

    egg = seal_egg(PAYLOAD, mode, MANIFOLD, SECRET)
    assert verify_egg(egg, PAYLOAD, mode, MANIFOLD, SECRET)
    assert not verify_egg(egg, PAYLOAD, mode, OTHER_MANIFOLD, SECRET)


def test_handedness_change_requires_separator_token() -> None:
    source = ChiralModeAddress(3, 5, handedness="R", chiral_weight=0.2)
    target = ChiralModeAddress(3, 5, handedness="L", chiral_weight=0.2)

    assert transition_requires_separator(source, target)
    assert not authorize_transition(source, target, MANIFOLD, SECRET)

    token = derive_separator_token(source, target, MANIFOLD, SECRET)
    assert authorize_transition(source, target, MANIFOLD, SECRET, separator_token=token)


def test_sign_change_requires_separator_token() -> None:
    source = ChiralModeAddress(3, 5, handedness="R", chiral_weight=0.2)
    target = ChiralModeAddress(-3, 5, handedness="R", chiral_weight=0.2)

    assert transition_requires_separator(source, target)
    assert not authorize_transition(source, target, MANIFOLD, SECRET)

    token = derive_separator_token(source, target, MANIFOLD, SECRET)
    assert authorize_transition(source, target, MANIFOLD, SECRET, separator_token=token)


def test_same_quadrant_same_handedness_does_not_require_separator() -> None:
    source = ChiralModeAddress(3, 5, handedness="R", chiral_weight=0.2)
    target = ChiralModeAddress(7, 9, handedness="R", chiral_weight=0.2)

    assert not transition_requires_separator(source, target)
    assert authorize_transition(source, target, MANIFOLD, SECRET)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"n": 0, "m": 5},
        {"n": 5, "m": 0},
        {"n": 4, "m": -4},
        {"n": 3, "m": 5, "handedness": "X"},
        {"n": 3, "m": 5, "chiral_weight": -0.1},
        {"n": 3, "m": 5, "phase_offset": float("inf")},
    ],
)
def test_invalid_modes_are_rejected(kwargs) -> None:
    with pytest.raises((TypeError, ValueError)):
        ChiralModeAddress(**kwargs)


@pytest.mark.parametrize(
    "bad_manifold",
    [
        (1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        (1.01, 0.0, 0.0, 0.0, 0.0, 0.0),
        (0.1, 0.2, 0.3),
        (0.1, 0.2, float("inf"), 0.0, 0.0, 0.0),
        (0.1, 0.2, float("nan"), 0.0, 0.0, 0.0),
    ],
)
def test_invalid_manifold_is_rejected(bad_manifold) -> None:
    mode = ChiralModeAddress(3, 5, handedness="R", chiral_weight=0.2)
    with pytest.raises(ValueError):
        derive_binding_token(mode, bad_manifold, SECRET)
