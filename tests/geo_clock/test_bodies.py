"""L4 deep-space bodies: Moon + Mars constants and EDE alignment."""

from __future__ import annotations

import pytest

from src.geo_clock import bodies
from src.symphonic_cipher.scbe_aethermoore.ede import spiral_ring as ede


def test_moon_state_distance_and_light_time():
    m = bodies.moon_state()
    assert m.name == "moon"
    assert m.distance_m == pytest.approx(bodies.MOON_DISTANCE_MEAN_M)
    # ~1.28 light-seconds one-way.
    assert 1.20 < m.one_way_light_s < 1.35
    assert m.rtt_s == pytest.approx(2 * m.one_way_light_s)
    assert m.source == "moon:mean"


def test_mars_default_is_ede_midpoint():
    m = bodies.mars_state()
    expected = (ede.MARS_DISTANCE_MIN + ede.MARS_DISTANCE_MAX) / 2.0
    assert m.distance_m == pytest.approx(expected)
    assert m.source == "ede:midpoint"


def test_mars_with_explicit_distance_marked_horizons():
    m = bodies.mars_state(distance_m=2.0e11)
    assert m.distance_m == pytest.approx(2.0e11)
    assert m.source == "horizons"


def test_mars_extremes_light_times_match_ede():
    closest, farthest = bodies.mars_extremes()
    assert closest.one_way_light_s == pytest.approx(ede.MARS_LIGHT_TIME_MIN, rel=1e-9)
    assert farthest.one_way_light_s == pytest.approx(ede.MARS_LIGHT_TIME_MAX, rel=1e-9)
    # And ordered.
    assert closest.distance_m < farthest.distance_m


def test_body_state_to_dict_keys():
    m = bodies.moon_state()
    d = m.to_dict()
    assert set(d.keys()) == {"name", "distance_m", "one_way_light_s", "rtt_s", "source"}


def test_horizons_fetch_offline_returns_none(monkeypatch):
    # Force the requests import to fail so we exercise the ImportError branch.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "requests":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert bodies.fetch_horizons_distance_m() is None
