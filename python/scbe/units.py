"""Exact, stdlib-only dimensional/unit engine for SCBE reaction-state checks.

This is the missing piece that makes ``ReactionRecalculation.unit_checks_ok`` a
REAL check instead of a hand-set boolean. Today callers set it to things like
``isfinite(moles)``, which cannot catch the failure that actually destroys
spacecraft: two quantities of the SAME dimension but a DIFFERENT unit, added
without conversion. That is the Mars Climate Orbiter loss (1999, $125M): impulse
in pound-force-seconds fed where newton-seconds were expected -- dimensionally
valid, numerically wrong by 4.448x.

Design:
  * Exact: unit scales are ``fractions.Fraction``; no float drift in conversions.
  * Stdlib-only: the shared reaction-state substrate stays dependency-free and
    runs anywhere (as ``reaction_cli.py`` promises).
  * Orbiter-safe: ``add``/``sub`` raise on a dimension mismatch AND on a
    same-dimension/different-unit mix unless the caller converts explicitly.
  * Optional Pint backend: if ``pint`` is installed, ``pint_agrees()`` cross-checks
    against the community-standard catalog -- the "real engine when available"
    pattern used elsewhere in this repo (RDKit, liboqs).

It does not (v1) model affine units (degC/degF offsets) -- temperature is treated
as kelvin-scaled only; that limitation is explicit, not silent.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Iterable

# SI base dimensions, in fixed order.
_BASE = ("kg", "m", "s", "A", "K", "mol", "cd")
Dimension = tuple  # tuple[Fraction, ...] of length 7


class UnitError(ValueError):
    """Raised when a dimensional or unit-consistency invariant is violated."""


def dim(**exponents: int) -> Dimension:
    """Build a dimension from base-unit exponents, e.g. ``dim(kg=1, m=1, s=-2)``."""
    return tuple(Fraction(exponents.get(b, 0)) for b in _BASE)


DIMENSIONLESS = dim()
MASS = dim(kg=1)
LENGTH = dim(m=1)
TIME = dim(s=1)
TEMPERATURE = dim(K=1)
AMOUNT = dim(mol=1)
VELOCITY = dim(m=1, s=-1)
ACCELERATION = dim(m=1, s=-2)
FORCE = dim(kg=1, m=1, s=-2)
ENERGY = dim(kg=1, m=2, s=-2)
IMPULSE = dim(kg=1, m=1, s=-1)
MOLAR_MASS = dim(kg=1, mol=-1)
VOLUME = dim(m=3)
CONCENTRATION = dim(mol=1, m=-3)


def dim_mul(a: Dimension, b: Dimension) -> Dimension:
    return tuple(x + y for x, y in zip(a, b))


def dim_div(a: Dimension, b: Dimension) -> Dimension:
    return tuple(x - y for x, y in zip(a, b))


def dim_pow(a: Dimension, n) -> Dimension:
    f = Fraction(n)
    return tuple(x * f for x in a)


def dim_name(d: Dimension) -> str:
    parts = [f"{b}^{x}" if x != 1 else b for b, x in zip(_BASE, d) if x != 0]
    return "·".join(parts) if parts else "1"


@dataclass(frozen=True)
class Unit:
    """A named unit: a dimension plus an EXACT multiplicative scale to SI base."""

    name: str
    dimension: Dimension
    to_si: Fraction  # SI_magnitude = magnitude * to_si

    def __mul__(self, other: "Unit") -> "Unit":
        return Unit(f"({self.name}*{other.name})", dim_mul(self.dimension, other.dimension), self.to_si * other.to_si)

    def __truediv__(self, other: "Unit") -> "Unit":
        return Unit(f"({self.name}/{other.name})", dim_div(self.dimension, other.dimension), self.to_si / other.to_si)


# ---- registry: SI + the two force/impulse units that demonstrate the catch --- #
KILOGRAM = Unit("kg", MASS, Fraction(1))
GRAM = Unit("g", MASS, Fraction(1, 1000))
METER = Unit("m", LENGTH, Fraction(1))
SECOND = Unit("s", TIME, Fraction(1))
KELVIN = Unit("K", TEMPERATURE, Fraction(1))
MOLE = Unit("mol", AMOUNT, Fraction(1))
PER_MOLE = Unit("1/mol", dim(mol=-1), Fraction(1))
DIMLESS = Unit("1", DIMENSIONLESS, Fraction(1))

NEWTON = Unit("N", FORCE, Fraction(1))
POUND_FORCE = Unit("lbf", FORCE, Fraction(444822, 100000))  # 4.44822 N (exact rational)
NEWTON_SECOND = Unit("N*s", IMPULSE, Fraction(1))
LBF_SECOND = Unit("lbf*s", IMPULSE, POUND_FORCE.to_si)  # same dimension, 4.448x scale

JOULE = Unit("J", ENERGY, Fraction(1))
G_PER_MOL = Unit("g/mol", MOLAR_MASS, Fraction(1, 1000))  # kg/mol = (g/mol)/1000
LITER = Unit("L", VOLUME, Fraction(1, 1000))
MOL_PER_L = Unit("mol/L", CONCENTRATION, Fraction(1000))  # mol/L = 1000 mol/m^3

AVOGADRO = Unit("1/mol", dim(mol=-1), Fraction(602214076, 1) * Fraction(10) ** 15)  # 6.02214076e23 /mol


@dataclass(frozen=True)
class Quantity:
    """A magnitude tagged with a unit. Magnitudes may be Fraction/int/float."""

    magnitude: object
    unit: Unit

    @property
    def dimension(self) -> Dimension:
        return self.unit.dimension

    def to_si(self) -> object:
        return self.magnitude * self.unit.to_si


def q(magnitude, unit: Unit) -> Quantity:
    return Quantity(magnitude, unit)


def same_dimension(a: Quantity, b: Quantity) -> bool:
    return a.unit.dimension == b.unit.dimension


def convert(value: Quantity, target: Unit) -> Quantity:
    """Convert to ``target`` (must share dimension). The ONLY sanctioned way to
    bring two same-dimension/different-unit quantities into one unit."""
    if value.unit.dimension != target.dimension:
        raise UnitError(
            f"cannot convert {value.unit.name} ({dim_name(value.unit.dimension)}) "
            f"-> {target.name} ({dim_name(target.dimension)}): different dimension"
        )
    return Quantity(value.to_si() / target.to_si, target)


def add(a: Quantity, b: Quantity) -> Quantity:
    """Add two quantities. Raises UnitError on a dimension mismatch, and on a
    same-dimension/DIFFERENT-unit mix (the Orbiter bug) -- convert first."""
    if a.unit.dimension != b.unit.dimension:
        raise UnitError(f"dimension mismatch: {a.unit.name} + {b.unit.name}")
    if a.unit.to_si != b.unit.to_si:
        raise UnitError(
            f"unit mismatch (same dimension '{dim_name(a.unit.dimension)}', different unit): "
            f"{a.unit.name} + {b.unit.name} -- convert() first "
            f"(this is the Mars Climate Orbiter class of error)"
        )
    return Quantity(a.magnitude + b.magnitude, a.unit)


def sub(a: Quantity, b: Quantity) -> Quantity:
    return add(a, Quantity(-b.magnitude, b.unit))


def mul(a: Quantity, b: Quantity) -> Quantity:
    return Quantity(a.magnitude * b.magnitude, a.unit * b.unit)


def div(a: Quantity, b: Quantity) -> Quantity:
    return Quantity(a.magnitude / b.magnitude, a.unit / b.unit)


def assert_dim(value: Quantity, expected: Dimension) -> Quantity:
    """Assert that ``value`` carries the expected dimension; return it unchanged."""
    if value.unit.dimension != expected:
        raise UnitError(
            f"dimension check failed: got {dim_name(value.unit.dimension)} "
            f"({value.unit.name}), expected {dim_name(expected)}"
        )
    return value


def check(fn: Callable[[], object]) -> tuple[bool, tuple[str, ...]]:
    """Run a units-bearing computation and report whether it stayed consistent.

    Callers express their computation in ``Quantity`` arithmetic (which raises
    ``UnitError`` on any inconsistency) and pass it as a thunk. The result is a
    ``(ok, problems)`` pair suitable for setting ``unit_checks_ok`` honestly::

        ok, problems = check(lambda: assert_dim(
            div(q(32.0, GRAM), q(32.0, G_PER_MOL)), AMOUNT))   # g / (g/mol) = mol
    """
    try:
        fn()
        return True, ()
    except UnitError as exc:
        return False, (str(exc),)


def pint_agrees(magnitude, unit_expr: str, expected_dim_expr: str) -> bool | None:
    """Optional cross-check against Pint, if installed. Returns None if Pint is
    absent (so callers can treat it as "not evaluated", never as a failure)."""
    try:
        import pint  # type: ignore
    except Exception:
        return None
    try:
        ureg = pint.UnitRegistry()
        quantity = magnitude * ureg(unit_expr)
        return bool(quantity.check(expected_dim_expr))
    except Exception:
        return False


def consistency_problems(steps: Iterable[Callable[[], object]]) -> tuple[str, ...]:
    """Run several units-bearing steps; collect all problems (empty == all ok)."""
    problems: list[str] = []
    for step in steps:
        ok, errs = check(step)
        if not ok:
            problems.extend(errs)
    return tuple(problems)
