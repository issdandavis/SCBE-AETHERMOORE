"""L0 localization fallback chain: env > file > ip-geo > default."""

from __future__ import annotations

import json
import os

import pytest

from src.geo_clock import agent_location


@pytest.fixture(autouse=True)
def _clear_geo_env(monkeypatch):
    for var in ("SCBE_GEO_LAT", "SCBE_GEO_LON", "SCBE_GEO_LABEL", "SCBE_GEO_FIX"):
        monkeypatch.delenv(var, raising=False)


def test_default_when_offline_and_no_env():
    loc = agent_location.resolve(allow_network=False)
    assert loc.source == "default"
    assert loc.confidence == pytest.approx(0.1)
    assert loc.lat == pytest.approx(agent_location.DEFAULT_LAT)
    assert loc.lon == pytest.approx(agent_location.DEFAULT_LON)


def test_env_pair_wins(monkeypatch):
    monkeypatch.setenv("SCBE_GEO_LAT", "47.6062")
    monkeypatch.setenv("SCBE_GEO_LON", "-122.3321")
    monkeypatch.setenv("SCBE_GEO_LABEL", "seattle")
    loc = agent_location.resolve(allow_network=False)
    assert loc.source == "env:SCBE_GEO_LAT/LON"
    assert loc.confidence == 1.0
    assert loc.label == "seattle"
    assert loc.lat == pytest.approx(47.6062)


def test_env_pair_invalid_falls_through(monkeypatch):
    monkeypatch.setenv("SCBE_GEO_LAT", "not-a-number")
    monkeypatch.setenv("SCBE_GEO_LON", "also-broken")
    loc = agent_location.resolve(allow_network=False)
    # Falls through to default since env is malformed.
    assert loc.source == "default"


def test_env_file_wins_over_default(tmp_path, monkeypatch):
    fix = tmp_path / "fix.json"
    fix.write_text(json.dumps({"lat": 35.6762, "lon": 139.6503, "label": "tokyo"}))
    monkeypatch.setenv("SCBE_GEO_FIX", str(fix))
    loc = agent_location.resolve(allow_network=False)
    assert loc.confidence == 1.0
    assert loc.label == "tokyo"
    assert loc.source.startswith("file:")


def test_env_pair_outranks_env_file(tmp_path, monkeypatch):
    fix = tmp_path / "fix.json"
    fix.write_text(json.dumps({"lat": 35.6762, "lon": 139.6503}))
    monkeypatch.setenv("SCBE_GEO_FIX", str(fix))
    monkeypatch.setenv("SCBE_GEO_LAT", "10.0")
    monkeypatch.setenv("SCBE_GEO_LON", "20.0")
    loc = agent_location.resolve(allow_network=False)
    assert loc.source == "env:SCBE_GEO_LAT/LON"
    assert loc.lat == pytest.approx(10.0)


def test_to_dict_round_trip():
    loc = agent_location.resolve(allow_network=False)
    d = loc.to_dict()
    assert set(d.keys()) >= {"lat", "lon", "confidence", "source", "resolved_at"}
