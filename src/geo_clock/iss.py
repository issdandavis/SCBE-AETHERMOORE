"""L3 — ISS sub-point tracking.

Single source: open-notify.org/iss-now.json (no auth, public, returns
ISS sub-point lat/lon every second). Fail-soft: if the network is down
or the API misbehaves, return ``None`` and let the compass note that
the orbital layer is offline.

For higher-fidelity work (orbit prediction, AOS/LOS, antenna pointing)
swap in NORAD TLEs via ``skyfield`` — see ``predict_with_tle`` below.
That path is optional so the module loads cleanly without skyfield.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

# ISS orbits at ~400-420 km. The exact altitude varies with reboosts; for
# bearing/RTT floor the Earth-surface sub-point is what callers want.
ISS_NOMINAL_ALTITUDE_KM = 410.0

_CACHE_TTL_S = 5.0
_cache: dict[str, object] = {"at": 0.0, "fix": None}


@dataclass(frozen=True)
class IssFix:
    lat: float
    lon: float
    altitude_km: float
    fetched_at: float
    source: str

    def to_dict(self) -> dict:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "altitude_km": self.altitude_km,
            "fetched_at": self.fetched_at,
            "source": self.source,
        }


def _fetch_open_notify(timeout: float = 2.0) -> Optional[IssFix]:
    try:
        import requests  # noqa: WPS433 optional dep
    except ImportError:
        return None
    try:
        r = requests.get("http://api.open-notify.org/iss-now.json", timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("message") != "success":
            return None
        pos = data["iss_position"]
        return IssFix(
            lat=float(pos["latitude"]),
            lon=float(pos["longitude"]),
            altitude_km=ISS_NOMINAL_ALTITUDE_KM,
            fetched_at=float(data.get("timestamp", time.time())),
            source="open-notify.org",
        )
    except Exception:
        return None


def current(*, allow_network: bool = True, max_age_s: float = _CACHE_TTL_S) -> Optional[IssFix]:
    """Return the most recent ISS sub-point or ``None`` if unavailable.

    Result is cached for ``max_age_s`` so a compass call burst (one per
    anchor) only hits the network once. ``allow_network=False`` forces
    cache-only (returns ``None`` on cold start).
    """

    now = time.time()
    cached = _cache.get("fix")
    if isinstance(cached, IssFix) and (now - float(_cache["at"])) < max_age_s:  # type: ignore[arg-type]
        return cached
    if not allow_network:
        return cached if isinstance(cached, IssFix) else None
    fix = _fetch_open_notify()
    if fix is not None:
        _cache["at"] = now
        _cache["fix"] = fix
    return fix


def predict_with_tle(tle_line1: str, tle_line2: str, when: float | None = None) -> Optional[IssFix]:
    """Optional offline path: predict ISS sub-point from a NORAD TLE.

    Returns ``None`` if ``skyfield`` is not installed; that's intentional
    — the open-notify path covers the common case without a heavy dep.
    """
    try:
        from skyfield.api import EarthSatellite, load, wgs84  # noqa: WPS433
    except ImportError:
        return None
    ts = load.timescale()
    sat = EarthSatellite(tle_line1, tle_line2, "ISS", ts)
    when_ts = ts.from_datetime(_to_utc(when))
    geo = wgs84.subpoint_of(sat.at(when_ts))
    return IssFix(
        lat=float(geo.latitude.degrees),
        lon=float(geo.longitude.degrees),
        altitude_km=ISS_NOMINAL_ALTITUDE_KM,
        fetched_at=time.time() if when is None else float(when),
        source="skyfield-tle",
    )


def _to_utc(when: float | None):
    from datetime import datetime, timezone

    if when is None:
        return datetime.now(tz=timezone.utc)
    return datetime.fromtimestamp(when, tz=timezone.utc)
