# tests/test_scbe_signed_chladni.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "src"):
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from scbe_signed_chladni import (  # noqa: E402
    SignedModeAddress,
    authorize_transition,
    derive_binding_token,
    derive_separator_token,
    seal_egg,
    transition_requires_separator,
    verify_egg,
)

SECRET = b"scbe-pytest-secret"
PAYLOAD = b"SacredEgg::payload"
MANIFOLD = (0.11, -0.07, 0.05, 0.09, -0.03, 0.04)
OTHER_MANIFOLD = (0.11, -0.07, 0.05, 0.09, -0.03, 0.045)


def test_raw_field_is_sign_invariant_for_cosine_modes() -> None:
    base = SignedModeAddress(3, 5)
    variants = (
        SignedModeAddress(-3, 5),
        SignedModeAddress(3, -5),
        SignedModeAddress(-3, -5),
    )
    points = ((0.13, 0.27), (0.41, 0.19), (0.73, 0.62))
    for x, y in points:
        expected = base.raw_field(x, y)
        for variant in variants:
            assert variant.raw_field(x, y) == pytest.approx(expected, abs=1e-12)


def test_absolute_readout_is_non_negative() -> None:
    mode = SignedModeAddress(-3, 5)
    for x, y in ((0.09, 0.21), (0.34, 0.66), (0.81, 0.17)):
        assert mode.readout(x, y) >= 0.0


def test_swapped_modes_collide_in_readout_but_not_binding() -> None:
    a = SignedModeAddress(3, 5)
    b = SignedModeAddress(5, 3)
    for x, y in ((0.13, 0.27), (0.41, 0.19), (0.73, 0.62)):
        assert a.raw_field(x, y) == pytest.approx(-b.raw_field(x, y), abs=1e-12)
        assert a.readout(x, y) == pytest.approx(b.readout(x, y), abs=1e-12)
    token_a = derive_binding_token(a, MANIFOLD, SECRET)
    token_b = derive_binding_token(b, MANIFOLD, SECRET)
    assert token_a != token_b


def test_all_four_sign_quadrants_get_distinct_binding_tokens() -> None:
    tokens = {
        derive_binding_token(SignedModeAddress(3, 5), MANIFOLD, SECRET),
        derive_binding_token(SignedModeAddress(-3, 5), MANIFOLD, SECRET),
        derive_binding_token(SignedModeAddress(3, -5), MANIFOLD, SECRET),
        derive_binding_token(SignedModeAddress(-3, -5), MANIFOLD, SECRET),
    }
    assert len(tokens) == 4


def test_zero_is_reserved_as_phase_separator() -> None:
    with pytest.raises(ValueError, match="phase separator"):
        SignedModeAddress(0, 5)
    with pytest.raises(ValueError, match="phase separator"):
        SignedModeAddress(5, 0)


def test_equal_magnitude_modes_are_rejected() -> None:
    with pytest.raises(ValueError, match="degenerate mode"):
        SignedModeAddress(4, -4)


def test_seal_verifies_for_exact_mode_and_manifold() -> None:
    mode = SignedModeAddress(-3, 5)
    egg_seal = seal_egg(PAYLOAD, mode, MANIFOLD, SECRET, realm="validation")
    assert verify_egg(egg_seal, PAYLOAD, mode, MANIFOLD, SECRET, realm="validation")


def test_seal_rejects_wrong_sign_quadrant() -> None:
    sealed_mode = SignedModeAddress(-3, 5)
    wrong_mode = SignedModeAddress(3, 5)
    egg_seal = seal_egg(PAYLOAD, sealed_mode, MANIFOLD, SECRET, realm="validation")
    assert not verify_egg(
        egg_seal, PAYLOAD, wrong_mode, MANIFOLD, SECRET, realm="validation"
    )


def test_seal_rejects_wrong_manifold() -> None:
    mode = SignedModeAddress(-3, 5)
    egg_seal = seal_egg(PAYLOAD, mode, MANIFOLD, SECRET)
    assert not verify_egg(egg_seal, PAYLOAD, mode, OTHER_MANIFOLD, SECRET)


def test_sign_change_requires_separator_token() -> None:
    source = SignedModeAddress(3, 5)
    target = SignedModeAddress(-3, 5)
    assert transition_requires_separator(source, target)
    assert not authorize_transition(source, target, MANIFOLD, SECRET)
    separator = derive_separator_token(source, target, MANIFOLD, SECRET)
    assert authorize_transition(
        source, target, MANIFOLD, SECRET, separator_token=separator
    )


def test_same_quadrant_no_separator_needed() -> None:
    source = SignedModeAddress(3, 5)
    target = SignedModeAddress(7, 9)
    assert not transition_requires_separator(source, target)
    assert authorize_transition(source, target, MANIFOLD, SECRET)


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
def test_manifold_binding_rejects_invalid_points(bad_manifold) -> None:
    mode = SignedModeAddress(3, 5)
    with pytest.raises(ValueError):
        derive_binding_token(mode, bad_manifold, SECRET)
