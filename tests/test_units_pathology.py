"""Unit-pathology locks, framed on the NIST TN 1943 failure taxonomy.

NIST Technical Note 1943 ("A Classification of Quantity Value Errors")
enumerates the ways a dimensional check can pass while the computation is still
wrong. This file pins, for each relevant class, EITHER the engine's catch OR --
honestly -- the limitation it does not yet cover, so a regression in either
direction is visible. The units engine is exact and stdlib-only; it is a
dimension+scale checker, not a full affine/quantity-kind system, and these tests
say exactly where that line falls.

Also pins the QUDT IRI surface added for receipt interop.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from python.scbe import units as U

# Units constructed only to demonstrate a pathology class (not part of the
# shipped registry).
RADIAN = U.Unit("rad", U.DIMENSIONLESS, Fraction(1))
STERADIAN = U.Unit("sr", U.DIMENSIONLESS, Fraction(1))
HERTZ = U.Unit("Hz", U.dim(s=-1), Fraction(1))
BECQUEREL = U.Unit("Bq", U.dim(s=-1), Fraction(1))
PERCENT = U.Unit("%", U.DIMENSIONLESS, Fraction(1, 100))
PPM = U.Unit("ppm", U.DIMENSIONLESS, Fraction(1, 1_000_000))


# --------------------------------------------------------------------------- #
# Class A: pathologies the engine CATCHES (the scale check earns its keep).
# --------------------------------------------------------------------------- #


def test_catch_same_dimension_different_scale_is_refused():
    """TN 1943 'wrong unit, right dimension' -- the Mars Climate Orbiter loss."""
    with pytest.raises(U.UnitError):
        U.add(U.q(100, U.NEWTON_SECOND), U.q(100, U.LBF_SECOND))


def test_catch_dimension_mismatch_is_refused():
    with pytest.raises(U.UnitError):
        U.add(U.q(1, U.KILOGRAM), U.q(1, U.METER))


def test_catch_unitized_scaling_factor_against_bare_ratio():
    """A '%' is a SCALED dimensionless: adding 50% to a bare 1 is refused
    because the SI scales differ (1/100 vs 1) even though both are
    dimensionless -- the 'unitized scaling factor' pathology."""
    with pytest.raises(U.UnitError):
        U.add(U.q(1, U.DIMLESS), U.q(50, PERCENT))
    with pytest.raises(U.UnitError):
        U.add(U.q(50, PERCENT), U.q(50, PPM))


def test_catch_count_density_vs_reciprocal_amount():
    """Avogadro's number (per mole, huge scale) and a bare 1/mol share the
    dimension mol^-1 but differ by ~6e23x -- refused."""
    with pytest.raises(U.UnitError):
        U.add(U.q(1, U.AVOGADRO), U.q(1, U.PER_MOLE))


def test_catch_is_exact_no_float_coercion():
    """Conversions ride Fraction scales: no float drift (TN 1943 'rounding /
    representation' class). 100 lbf*s -> N*s stays an exact rational."""
    converted = U.convert(U.q(100, U.LBF_SECOND), U.NEWTON_SECOND)
    assert converted.magnitude == Fraction(100) * Fraction(444822, 100000)
    assert isinstance(converted.magnitude, Fraction)


# --------------------------------------------------------------------------- #
# Class B: pathologies the engine does NOT cover -- documented limitations.
# These tests pin the CURRENT behavior so the gap is explicit, not silent.
# --------------------------------------------------------------------------- #


def test_limitation_dimensionless_collision_plane_vs_solid_angle():
    """Radian and steradian are both dimension-1 with scale 1, so the engine
    cannot tell a plane angle from a solid angle from a pure count. This is the
    TN 1943 'dimensionless collision' / 'angle erasure' class -- unmodeled."""
    total = U.add(U.q(1, RADIAN), U.q(1, STERADIAN))  # erroneously allowed
    assert total.magnitude == 2
    assert U.same_dimension(U.q(1, RADIAN), U.q(1, U.DIMLESS))  # angle erased to a number


def test_limitation_hertz_ambiguity_cycles_vs_events():
    """Hz (cycles/s) and Bq (events/s) are both s^-1 with scale 1; the engine
    treats them as identical. TN 1943 'same dimension, distinct quantity kind'
    -- a quantity-kind system would separate them; this engine does not."""
    total = U.add(U.q(1, HERTZ), U.q(1, BECQUEREL))  # erroneously allowed
    assert total.magnitude == 2


def test_limitation_temperature_is_interval_scaled_no_affine_zero_point():
    """Temperature is K-scaled only: the engine has no affine (offset) units, so
    it models temperature INTERVALS correctly but cannot express an absolute
    Celsius zero point (0 degC = 273.15 K). TN 1943 'interval vs ratio scale'."""
    # A 1 K interval and a 1 degC interval coincide (scale 1) -- this it gets right.
    assert U.KELVIN.to_si == Fraction(1)
    # There is deliberately no Celsius/Fahrenheit unit in the registry.
    assert not hasattr(U, "CELSIUS")
    assert not hasattr(U, "FAHRENHEIT")


# --------------------------------------------------------------------------- #
# QUDT IRI surface (receipt interop).
# --------------------------------------------------------------------------- #

_QUDT_PREFIX = "http://qudt.org/vocab/unit/"
# IRIs confirmed to resolve against the live QUDT vocabulary (CC BY 4.0).
_VERIFIED_QUDT = {
    U.KILOGRAM: "KiloGM",
    U.GRAM: "GM",
    U.METER: "M",
    U.SECOND: "SEC",
    U.KELVIN: "K",
    U.MOLE: "MOL",
    U.PER_MOLE: "PER-MOL",
    U.DIMLESS: "UNITLESS",
    U.NEWTON: "N",
    U.POUND_FORCE: "LB_F",
    U.NEWTON_SECOND: "N-SEC",
    U.JOULE: "J",
    U.G_PER_MOL: "GM-PER-MOL",
    U.LITER: "L",
    U.MOL_PER_L: "MOL-PER-L",
}


@pytest.mark.parametrize("unit,code", list(_VERIFIED_QUDT.items()), ids=lambda x: getattr(x, "name", x))
def test_named_units_carry_their_verified_qudt_iri(unit, code):
    assert unit.qudt == _QUDT_PREFIX + code


def test_orbiter_wrong_unit_has_no_invented_iri():
    """lbf*s has no canonical QUDT term (the IRI 404s), so it carries None
    rather than a fabricated code -- the honest half of the interop claim."""
    assert U.LBF_SECOND.qudt is None


def test_derived_units_carry_no_iri():
    """A unit composed by * or / has no single canonical QUDT term."""
    speed = U.METER / U.SECOND
    work = U.NEWTON * U.METER
    assert speed.qudt is None
    assert work.qudt is None


def test_unit_descriptor_is_packet_ready_and_exact():
    d = U.unit_descriptor(U.G_PER_MOL)
    assert d == {
        "symbol": "g/mol",
        "qudt": _QUDT_PREFIX + "GM-PER-MOL",
        "dimension": "kg·mol^-1",
        "si_scale": "1/1000",
    }
    # si_scale round-trips to the exact Fraction with no float drift.
    num, den = d["si_scale"].split("/")
    assert Fraction(int(num), int(den)) == U.G_PER_MOL.to_si
    # Derived units report a null IRI honestly.
    assert U.unit_descriptor(U.METER / U.SECOND)["qudt"] is None
