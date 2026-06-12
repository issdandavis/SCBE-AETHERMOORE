"""Regression locks for the exact units engine (python/scbe/units.py).

These freeze the behaviour that makes ``unit_checks_ok`` a real check: the
Mars-Climate-Orbiter catch (same dimension, different unit, no conversion), exact
conversion, and chemistry dimensional consistency (g / (g/mol) = mol).
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from python.scbe import units as U
from python.scbe.reaction_state import unit_check


def test_orbiter_catch_same_dimension_different_unit_raises():
    # N*s and lbf*s share the IMPULSE dimension but differ by 4.448x.
    with pytest.raises(U.UnitError):
        U.add(U.q(100, U.NEWTON_SECOND), U.q(100, U.LBF_SECOND))


def test_explicit_conversion_is_exact_then_add_ok():
    converted = U.convert(U.q(100, U.LBF_SECOND), U.NEWTON_SECOND)
    # exact rational: 100 lbf*s = 100 * 4.44822 N*s
    assert converted.magnitude == Fraction(100) * Fraction(444822, 100000)
    total = U.add(U.q(100, U.NEWTON_SECOND), converted)
    assert total.unit is U.NEWTON_SECOND
    assert total.magnitude == Fraction(100) + Fraction(100) * Fraction(444822, 100000)


def test_dimension_mismatch_raises():
    with pytest.raises(U.UnitError):
        U.add(U.q(1, U.NEWTON), U.q(1, U.JOULE))  # force + energy


def test_chemistry_dimensional_consistency_grams_over_molar_mass_is_moles():
    # 32.0 g / (32.0 g/mol) = 1 mol, then * Avogadro/mol = dimensionless count.
    def computation():
        moles = U.div(U.q(Fraction(32), U.GRAM), U.q(Fraction(32), U.G_PER_MOL))
        U.assert_dim(moles, U.AMOUNT)
        count = U.mul(moles, U.q(1, U.AVOGADRO))
        U.assert_dim(count, U.DIMENSIONLESS)
        return count

    ok, problems = U.check(computation)
    assert ok and problems == ()


def test_null_scrambled_computation_is_flagged():
    # grams + seconds is nonsense; check() must report not-ok rather than raise.
    ok, problems = U.check(lambda: U.add(U.q(1, U.GRAM), U.q(1, U.SECOND)))
    assert not ok and problems


def test_reaction_state_unit_check_wrapper_flags_orbiter_and_passes_valid():
    bad_ok, bad_problems = unit_check(lambda: U.add(U.q(100, U.NEWTON_SECOND), U.q(100, U.LBF_SECOND)))
    assert not bad_ok and bad_problems

    good_ok, good_problems = unit_check(
        lambda: U.assert_dim(U.div(U.q(Fraction(46), U.GRAM), U.q(Fraction(46), U.G_PER_MOL)), U.AMOUNT)
    )
    assert good_ok and good_problems == ()


def test_pint_backend_is_optional_never_a_hard_failure():
    # Returns None when pint is absent; True/False when present. Never raises.
    result = U.pint_agrees(100, "newton * second", "[mass] * [length] / [time]")
    assert result in (None, True, False)


def test_unit_compose_dimensions_are_exact():
    # (kg/s) * (m/s) has the dimension of force.
    mdot = U.Unit("kg/s", U.dim(kg=1, s=-1), Fraction(1))
    v = U.Unit("m/s", U.VELOCITY, Fraction(1))
    thrust = mdot * v
    assert thrust.dimension == U.FORCE
