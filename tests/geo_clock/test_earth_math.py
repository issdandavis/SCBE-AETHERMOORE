"""Pure math invariants for haversine + bearing + cardinal + solar time."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from src.geo_clock import earth_math


PORT_ANGELES = (48.1181, -123.4307)
GREENWICH = (51.4779, -0.0015)
SHANGHAI = (31.2304, 121.4737)


def test_haversine_zero_distance():
    assert earth_math.haversine_km(*PORT_ANGELES, *PORT_ANGELES) == pytest.approx(0.0, abs=1e-6)


def test_haversine_symmetry():
    a = earth_math.haversine_km(*PORT_ANGELES, *GREENWICH)
    b = earth_math.haversine_km(*GREENWICH, *PORT_ANGELES)
    assert a == pytest.approx(b, rel=1e-9)


def test_haversine_known_distance_pa_to_greenwich():
    # Reference: ~7700 km great-circle, well-known geodesy result.
    d = earth_math.haversine_km(*PORT_ANGELES, *GREENWICH)
    assert 7600.0 < d < 7900.0


def test_haversine_max_antipode_bound():
    # Half the Earth's circumference at the WGS-84 mean radius.
    d = earth_math.haversine_km(0.0, 0.0, 0.0, 180.0)
    expected = math.pi * earth_math.EARTH_RADIUS_KM
    assert d == pytest.approx(expected, rel=1e-6)


def test_initial_bearing_range():
    b = earth_math.initial_bearing_deg(*PORT_ANGELES, *SHANGHAI)
    assert 0.0 <= b < 360.0


def test_initial_bearing_north_pole_is_zero():
    # Bearing from equator straight up to the north pole should be 0 deg (N).
    b = earth_math.initial_bearing_deg(0.0, 0.0, 89.0, 0.0)
    assert b == pytest.approx(0.0, abs=1e-6)


def test_initial_bearing_east_along_equator():
    b = earth_math.initial_bearing_deg(0.0, 0.0, 0.0, 1.0)
    assert b == pytest.approx(90.0, abs=1e-6)


def test_cardinal_for_bearing_extremes():
    assert earth_math.cardinal_for_bearing(0.0) == "N"
    assert earth_math.cardinal_for_bearing(90.0) == "E"
    assert earth_math.cardinal_for_bearing(180.0) == "S"
    assert earth_math.cardinal_for_bearing(270.0) == "W"
    # Wrap-around: 360 should also read N.
    assert earth_math.cardinal_for_bearing(359.99) == "N"


def test_longitude_to_utc_offset_solar_mean():
    assert earth_math.longitude_to_utc_offset_hours(0.0) == pytest.approx(0.0)
    assert earth_math.longitude_to_utc_offset_hours(15.0) == pytest.approx(1.0)
    assert earth_math.longitude_to_utc_offset_hours(-180.0) == pytest.approx(-12.0)


def test_local_time_solar_uses_longitude_offset():
    when = datetime(2026, 5, 2, 12, 0, 0, tzinfo=timezone.utc)
    # +30 lon -> +2h solar offset -> 14:00.
    t = earth_math.local_time_solar(30.0, when)
    assert t.hour == 14
    assert t.minute == 0
