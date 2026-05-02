"""L0 — Localization. Resolve the agent's own (lat, lon, time, confidence).

Everything else in geo_clock builds on this. If localization is best-effort,
downstream bearings and RTTs inherit that uncertainty via the ``confidence``
field on AgentLocation.

Resolution order (highest confidence first):
    1. Explicit env vars  SCBE_GEO_LAT / SCBE_GEO_LON       confidence=1.0
    2. Explicit env file  SCBE_GEO_FIX (json: lat/lon/source) confidence=1.0
    3. IP geolocation     ipapi.co (no auth, fail-soft)     confidence=0.6
    4. Hard default       Port Angeles, WA                  confidence=0.1
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

DEFAULT_LAT = 48.1181  # Port Angeles, WA
DEFAULT_LON = -123.4307
DEFAULT_LABEL = "port_angeles_wa_default"


@dataclass(frozen=True)
class AgentLocation:
    lat: float
    lon: float
    confidence: float
    source: str
    resolved_at: float = field(default_factory=time.time)
    label: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "confidence": self.confidence,
            "source": self.source,
            "resolved_at": self.resolved_at,
            "label": self.label,
        }


def _try_env_pair() -> Optional[AgentLocation]:
    lat = os.environ.get("SCBE_GEO_LAT")
    lon = os.environ.get("SCBE_GEO_LON")
    if lat and lon:
        try:
            return AgentLocation(
                lat=float(lat),
                lon=float(lon),
                confidence=1.0,
                source="env:SCBE_GEO_LAT/LON",
                label=os.environ.get("SCBE_GEO_LABEL"),
            )
        except ValueError:
            return None
    return None


def _try_env_file() -> Optional[AgentLocation]:
    path = os.environ.get("SCBE_GEO_FIX")
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return AgentLocation(
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            confidence=1.0,
            source=f"file:{path}",
            label=data.get("label"),
        )
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def _try_ip_geo(timeout: float = 2.0) -> Optional[AgentLocation]:
    try:
        import requests  # noqa: WPS433  optional dep
    except ImportError:
        return None
    try:
        r = requests.get("https://ipapi.co/json/", timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json()
        lat = data.get("latitude")
        lon = data.get("longitude")
        if lat is None or lon is None:
            return None
        return AgentLocation(
            lat=float(lat),
            lon=float(lon),
            confidence=0.6,
            source="ipapi.co",
            label=f"{data.get('city','?')},{data.get('country_code','?')}",
        )
    except Exception:
        return None


def _hard_default() -> AgentLocation:
    return AgentLocation(
        lat=DEFAULT_LAT,
        lon=DEFAULT_LON,
        confidence=0.1,
        source="default",
        label=DEFAULT_LABEL,
    )


def resolve(*, allow_network: bool = True) -> AgentLocation:
    """Return best-available agent location.

    ``allow_network=False`` skips the IP-geo step (use in tests/offline runs).
    """

    for resolver in (_try_env_pair, _try_env_file):
        loc = resolver()
        if loc is not None:
            return loc
    if allow_network:
        loc = _try_ip_geo()
        if loc is not None:
            return loc
    return _hard_default()
