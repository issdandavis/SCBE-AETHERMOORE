"""Property tests for python/scbe/dsl/primitives.py.

Per L_dsl_synthesis Step 1: every line-emittable primitive must satisfy
`run_program(parse_program(emit(f, args)), s) == f(s, *args)`. Higher-order
primitives (compose, vote) are tested at the function level.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from python.scbe.brain import GOLDEN_RATIO, TONGUES
from python.scbe.dsl.primitives import (
    GRID_SIZE,
    GridState,
    Op,
    PRIMITIVE_TABLE,
    breath,
    compose,
    initial_state,
    mobius_phase,
    parse_program,
    phi_weight,
    run_program,
    seal,
    tongue_shift,
    vote,
    well_select,
)

TONGUE_KEYS = sorted(TONGUES.keys())


def _make_grid(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal((GRID_SIZE, GRID_SIZE)) * 0.1


def _state(seed: int = 0, tongue: str = "KO") -> GridState:
    return GridState(grid=_make_grid(seed), tongue=tongue)


# ---------------------------------------------------------------------------
# Catalog completeness
# ---------------------------------------------------------------------------


def test_primitive_table_has_eight():
    expected = {
        "tongue_shift",
        "phi_weight",
        "mobius_phase",
        "breath",
        "compose",
        "vote",
        "well_select",
        "seal",
    }
    assert set(PRIMITIVE_TABLE.keys()) == expected


# ---------------------------------------------------------------------------
# Parse roundtrip per primitive
# ---------------------------------------------------------------------------


@given(
    src=st.sampled_from(TONGUE_KEYS),
    dst=st.sampled_from(TONGUE_KEYS),
    seed=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=40, deadline=None)
def test_tongue_shift_parse_roundtrip(src, dst, seed):
    s = _state(seed=seed, tongue=src)
    direct = tongue_shift(s, src, dst)
    via = run_program(parse_program(f"tongue_shift({src} -> {dst})"), s)
    assert direct == via


@given(
    t=st.sampled_from(TONGUE_KEYS),
    k=st.integers(min_value=-3, max_value=3),
    seed=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=40, deadline=None)
def test_phi_weight_parse_roundtrip(t, k, seed):
    s = _state(seed=seed, tongue=t)
    direct = phi_weight(s, t, k)
    via = run_program(parse_program(f"phi_weight({t}, {k})"), s)
    assert direct == via


@given(
    theta=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    seed=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=40, deadline=None)
def test_mobius_phase_parse_roundtrip(theta, seed):
    s = _state(seed=seed)
    direct = mobius_phase(s, theta)
    via = run_program(parse_program(f"mobius_phase({theta})"), s)
    assert direct == via


@given(
    omega=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    seed=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=40, deadline=None)
def test_breath_parse_roundtrip(omega, seed):
    s = _state(seed=seed)
    direct = breath(s, omega)
    via = run_program(parse_program(f"breath({omega})"), s)
    assert direct == via


@given(
    realm=st.text(
        alphabet=st.characters(min_codepoint=ord("A"), max_codepoint=ord("z")),
        min_size=1,
        max_size=12,
    ).filter(lambda s: s.strip() and "(" not in s and ")" not in s and "," not in s and "#" not in s),
    seed=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=40, deadline=None)
def test_well_select_parse_roundtrip(realm, seed):
    s = _state(seed=seed)
    direct = well_select(s, realm)
    via = run_program(parse_program(f"well_select({realm})"), s)
    assert direct == via


@given(seed=st.integers(min_value=0, max_value=10_000))
@settings(max_examples=20, deadline=None)
def test_seal_parse_roundtrip(seed):
    s = _state(seed=seed)
    direct = seal(s)
    via = run_program(parse_program("seal()"), s)
    assert direct == via


# ---------------------------------------------------------------------------
# Algebraic properties
# ---------------------------------------------------------------------------


def test_seal_is_idempotent():
    s = _state(seed=42)
    once = seal(s)
    twice = seal(once)
    assert once == twice


@given(
    src=st.sampled_from(TONGUE_KEYS),
    dst=st.sampled_from(TONGUE_KEYS),
    seed=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=30, deadline=None)
def test_tongue_shift_round_trip_returns_phase(src, dst, seed):
    s = _state(seed=seed, tongue=src)
    out = tongue_shift(tongue_shift(s, src, dst), dst, src)
    assert out.tongue == src
    assert math.isclose(out.phase, s.phase, abs_tol=1e-9)


@given(
    t=st.sampled_from(TONGUE_KEYS),
    a=st.integers(min_value=-3, max_value=3),
    b=st.integers(min_value=-3, max_value=3),
    seed=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=30, deadline=None)
def test_phi_weight_stacks_additively(t, a, b, seed):
    s = _state(seed=seed, tongue=t)
    stacked = phi_weight(phi_weight(s, t, a), t, b)
    direct = phi_weight(s, t, a + b)
    assert stacked.phi_power == direct.phi_power
    np.testing.assert_allclose(stacked.grid, direct.grid, rtol=1e-9, atol=1e-12)


def test_compose_is_function_composition():
    s = _state(seed=7)
    f = lambda x: phi_weight(x, "KO", 1)
    g = lambda x: mobius_phase(x, 0.5)
    composed = compose(f, g)
    assert composed(s) == f(g(s))


def test_compose_is_associative():
    s = _state(seed=11)
    f = lambda x: phi_weight(x, "KO", 1)
    g = lambda x: mobius_phase(x, 0.3)
    h = lambda x: breath(x, 0.2)
    left = compose(f, compose(g, h))(s)
    right = compose(compose(f, g), h)(s)
    assert left == right


def test_vote_is_idempotent_for_single_state():
    s = _state(seed=3)
    assert vote(s) == s


def test_vote_picks_consensus_tongue():
    a = _state(seed=1, tongue="KO")
    b = _state(seed=2, tongue="KO")
    c = _state(seed=3, tongue="AV")
    out = vote(a, b, c)
    assert out.tongue == "KO"


def test_vote_rejects_empty():
    with pytest.raises(ValueError):
        vote()


def test_well_select_persists_until_overwritten():
    s = _state(seed=4)
    s1 = well_select(s, "WELL_A")
    s2 = mobius_phase(s1, 0.1)
    assert s2.well == "WELL_A"
    s3 = well_select(s2, "WELL_B")
    assert s3.well == "WELL_B"


def test_well_select_rejects_empty():
    with pytest.raises(ValueError):
        well_select(_state(), "")


# ---------------------------------------------------------------------------
# Multi-line programs
# ---------------------------------------------------------------------------


def test_canonical_three_line_program():
    """The example program from L_dsl_synthesis must parse and run cleanly."""
    src = "tongue_shift(KO -> AV)\nphi_weight(AV, 1)\nseal()\n# comment line"
    ops = parse_program(src)
    assert [op.name for op in ops] == ["tongue_shift", "phi_weight", "seal"]
    final = run_program(ops, initial_state("KO"))
    assert final.tongue == "AV"
    assert final.phi_power == 1
    assert final.well == "SEALED"


def test_unicode_arrow_accepted():
    ops = parse_program("tongue_shift(KO → AV)")
    assert ops[0].args == ("KO", "AV")


def test_unknown_primitive_rejected():
    with pytest.raises(ValueError):
        parse_program("not_a_primitive()")


def test_malformed_line_rejected():
    with pytest.raises(ValueError):
        parse_program("tongue_shift KO -> AV")  # missing parens
