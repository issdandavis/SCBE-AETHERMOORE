"""Pure math: great-circle distance, initial bearing, local time offset.

WGS-84 mean radius is used for distance. Bearing is the initial bearing of
the great-circle path from (lat1, lon1) to (lat2, lon2), in degrees from
true north [0, 360).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing 0..360 from true north."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    y = math.sin(dlam) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlam)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def cardinal_for_bearing(bearing_deg: float) -> str:
    """16-point compass label."""
    points = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    return points[int((bearing_deg / 22.5) + 0.5) % 16]


def longitude_to_utc_offset_hours(lon: float) -> float:
    """Solar-mean offset = lon / 15. Note: NOT politically-defined tz."""
    return lon / 15.0


def local_time_solar(lon: float, when: datetime | None = None) -> datetime:
    """Solar local time at this longitude (mean-sun, no DST/political tz)."""
    if when is None:
        when = datetime.now(tz=timezone.utc)
    elif when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    offset = timedelta(hours=longitude_to_utc_offset_hours(lon))
    return (when + offset).replace(tzinfo=None)
