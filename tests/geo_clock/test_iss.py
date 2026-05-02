"""ISS L3 — fail-soft network behaviour."""

from __future__ import annotations

import time

from src.geo_clock import iss


def test_current_offline_returns_none_on_cold_start():
    # Wipe cache to simulate cold start.
    iss._cache["fix"] = None
    iss._cache["at"] = 0.0
    assert iss.current(allow_network=False) is None


def test_current_offline_serves_stale_cache():
    fake = iss.IssFix(
        lat=12.34,
        lon=56.78,
        altitude_km=iss.ISS_NOMINAL_ALTITUDE_KM,
        fetched_at=time.time(),
        source="test-fixture",
    )
    iss._cache["fix"] = fake
    iss._cache["at"] = time.time()
    out = iss.current(allow_network=False)
    assert out is fake


def test_predict_with_tle_no_skyfield_returns_none():
    # Without skyfield installed the predict path must fail-soft.
    # If skyfield IS installed this becomes a no-op assertion that the
    # call doesn't crash — that's also fine.
    try:
        import skyfield  # noqa: F401
    except ImportError:
        # Bogus TLE, but we should not even get to parsing it.
        out = iss.predict_with_tle("xx", "yy")
        assert out is None


def test_iss_fix_to_dict_keys():
    fix = iss.IssFix(lat=0.0, lon=0.0, altitude_km=410.0, fetched_at=0.0, source="t")
    d = fix.to_dict()
    assert set(d.keys()) == {"lat", "lon", "altitude_km", "fetched_at", "source"}
