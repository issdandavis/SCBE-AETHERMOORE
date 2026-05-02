"""Anchor-table invariants: 12 zone meridians, no orphan labels."""

from __future__ import annotations

from src.geo_clock import anchors


def test_twelve_zone_meridians():
    assert len(anchors.ZONE_MERIDIANS) == 12


def test_zone_meridians_are_zone_kind():
    for a in anchors.ZONE_MERIDIANS:
        assert a.kind == "zone_meridian"


def test_zone_meridians_span_global_longitude_range():
    # Anchors are representative cities near the major time meridians,
    # not strict 30-deg points — but they must still span the globe so
    # the compass shows a useful bearing in every direction.
    lons = sorted(a.lon for a in anchors.ZONE_MERIDIANS)
    assert lons[0] < -90.0 and lons[-1] > 90.0
    # Each adjacent pair stays within roughly one extra time zone of gap;
    # if any gap exceeds 60 deg we have a hole in coverage.
    gaps = [b - a for a, b in zip(lons, lons[1:])]
    assert max(gaps) <= 60.0


def test_all_anchors_have_non_empty_labels():
    for a in anchors.all_anchors():
        assert a.label
        assert isinstance(a.label, str)


def test_dsn_sites_present():
    labels = {a.label for a in anchors.KEY_LOCATIONS}
    assert {"dsn_goldstone", "dsn_madrid", "dsn_canberra"}.issubset(labels)


def test_ground_stations_classified():
    for a in anchors.KEY_LOCATIONS:
        if a.label.startswith("dsn_"):
            assert a.kind == "ground_station"


def test_lat_lon_within_valid_range():
    for a in anchors.all_anchors():
        assert -90.0 <= a.lat <= 90.0
        assert -180.0 <= a.lon <= 180.0
