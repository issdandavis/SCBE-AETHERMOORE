"""L5 composer — confidence propagation, anchor coverage, offline mode."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.geo_clock import anchors, iss
from src.geo_clock.agent_location import AgentLocation
from src.geo_clock.compass import compass


@pytest.fixture
def fixed_here():
    return AgentLocation(
        lat=48.1181,
        lon=-123.4307,
        confidence=0.85,
        source="test-fixture",
        resolved_at=0.0,
        label="port_angeles_test",
    )


@pytest.fixture(autouse=True)
def _wipe_iss_cache():
    iss._cache["fix"] = None
    iss._cache["at"] = 0.0
    yield
    iss._cache["fix"] = None
    iss._cache["at"] = 0.0


def test_compass_top_level_keys(fixed_here):
    view = compass(fixed_here, allow_network=False)
    assert set(view.keys()) >= {"here", "when", "confidence", "anchors", "orbital"}


def test_confidence_propagates_from_l0(fixed_here):
    view = compass(fixed_here, allow_network=False)
    assert view["confidence"] == pytest.approx(0.85)
    assert view["here"]["confidence"] == pytest.approx(0.85)


def test_anchor_count_matches_table(fixed_here):
    view = compass(fixed_here, allow_network=False)
    assert len(view["anchors"]) == len(anchors.all_anchors())


def test_each_anchor_has_required_fields(fixed_here):
    view = compass(fixed_here, allow_network=False)
    for a in view["anchors"]:
        assert {"label", "kind", "distance_km", "bearing_deg", "cardinal", "rtt"} <= set(a.keys())
        assert 0.0 <= a["bearing_deg"] < 360.0
        assert a["distance_km"] >= 0.0
        assert {"fiber_ms", "leo_ms", "vacuum_ms", "best_path"} <= set(a["rtt"].keys())


def test_self_distance_is_zero_when_anchor_equals_here():
    pa_anchor = next(a for a in anchors.KEY_LOCATIONS if a.label == "port_angeles_wa")
    here = AgentLocation(
        lat=pa_anchor.lat,
        lon=pa_anchor.lon,
        confidence=1.0,
        source="exact-match",
    )
    view = compass(here, allow_network=False)
    pa_view = next(a for a in view["anchors"] if a["label"] == "port_angeles_wa")
    assert pa_view["distance_km"] == pytest.approx(0.0, abs=1e-6)


def test_orbital_offline_iss_is_none(fixed_here):
    view = compass(fixed_here, allow_network=False)
    assert view["orbital"]["iss"] is None


def test_orbital_moon_always_present(fixed_here):
    view = compass(fixed_here, allow_network=False)
    moon = view["orbital"]["moon"]
    assert moon is not None
    assert moon["state"]["name"] == "moon"
    assert moon["rtt"]["best_path"] == "vacuum"


def test_orbital_mars_offline_uses_ede_midpoint(fixed_here):
    view = compass(fixed_here, allow_network=False)
    mars = view["orbital"]["mars"]
    assert mars["state"]["source"] == "ede:midpoint"
    assert "extremes" in mars
    assert mars["extremes"]["closest"]["distance_m"] < mars["extremes"]["farthest"]["distance_m"]


def test_when_override_is_honored(fixed_here):
    when = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    view = compass(fixed_here, allow_network=False, when=when)
    assert view["when"] == when.isoformat()


def test_iss_view_uses_cached_fix(fixed_here):
    fake = iss.IssFix(
        lat=0.0,
        lon=0.0,
        altitude_km=410.0,
        fetched_at=0.0,
        source="test-cache",
    )
    iss._cache["fix"] = fake
    iss._cache["at"] = 1e18  # Effectively never expires.
    view = compass(fixed_here, allow_network=False)
    iss_view = view["orbital"]["iss"]
    assert iss_view is not None
    assert iss_view["fix"]["source"] == "test-cache"
    assert iss_view["distance_km"] >= 0.0
