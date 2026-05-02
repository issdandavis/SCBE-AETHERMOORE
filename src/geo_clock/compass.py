"""L5 — Compass composer.

Top-level surface for the geo-clock. Given an ``AgentLocation`` (from L0),
return a single dict that bundles, for every Earth anchor and every
orbital body of interest:

  * great-circle bearing + distance from here
  * solar local time at the anchor's longitude
  * RTT floor for fiber + LEO + (deep-space only) vacuum

Confidence flows downstream: the L0 resolver's ``confidence`` field is
copied into the result so callers know how trustworthy the bearings are.
A bearing computed from a 0.1-confidence default position is *not* the
same answer as one computed from a 1.0-confidence GNSS fix.

Network surfaces (ISS, Mars-Horizons) are opt-in via ``allow_network``.
With ``allow_network=False`` the result still resolves — orbital fields
just carry ``None`` where the network would have filled them.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from . import bodies, earth_math, iss, latency
from .agent_location import AgentLocation, resolve
from .anchors import Anchor, all_anchors


def _anchor_view(here: AgentLocation, anchor: Anchor, when: datetime) -> dict:
    distance_km = earth_math.haversine_km(here.lat, here.lon, anchor.lat, anchor.lon)
    bearing = earth_math.initial_bearing_deg(here.lat, here.lon, anchor.lat, anchor.lon)
    return {
        "label": anchor.label,
        "kind": anchor.kind,
        "lat": anchor.lat,
        "lon": anchor.lon,
        "notes": anchor.notes,
        "distance_km": distance_km,
        "bearing_deg": bearing,
        "cardinal": earth_math.cardinal_for_bearing(bearing),
        "solar_local_time": earth_math.local_time_solar(anchor.lon, when).isoformat(),
        "rtt": latency.quote(distance_km).to_dict(),
    }


def _iss_view(here: AgentLocation, *, allow_network: bool) -> Optional[dict]:
    fix = iss.current(allow_network=allow_network)
    if fix is None:
        return None
    distance_km = earth_math.haversine_km(here.lat, here.lon, fix.lat, fix.lon)
    bearing = earth_math.initial_bearing_deg(here.lat, here.lon, fix.lat, fix.lon)
    return {
        "fix": fix.to_dict(),
        "distance_km": distance_km,
        "bearing_deg": bearing,
        "cardinal": earth_math.cardinal_for_bearing(bearing),
        "rtt": latency.quote(distance_km).to_dict(),
    }


def _moon_view() -> dict:
    state = bodies.moon_state()
    return {
        "state": state.to_dict(),
        "rtt": latency.quote(state.distance_m / 1000.0, vacuum_ok=True).to_dict(),
    }


def _mars_view(*, allow_network: bool) -> dict:
    distance_m: Optional[float] = None
    if allow_network:
        distance_m = bodies.fetch_horizons_distance_m()
    state = bodies.mars_state(distance_m=distance_m)
    closest, farthest = bodies.mars_extremes()
    return {
        "state": state.to_dict(),
        "extremes": {
            "closest": closest.to_dict(),
            "farthest": farthest.to_dict(),
        },
        "rtt": latency.quote(state.distance_m / 1000.0, vacuum_ok=True).to_dict(),
    }


def compass(
    here: Optional[AgentLocation] = None,
    *,
    allow_network: bool = True,
    when: Optional[datetime] = None,
) -> dict:
    """Return the full compass view from ``here`` (defaults to ``resolve()``).

    The result is a JSON-friendly dict with these top-level keys:

      * ``here``           — the L0 location used (incl. confidence)
      * ``when``           — UTC ISO timestamp the view was computed at
      * ``confidence``     — copied from ``here.confidence`` (downstream gate)
      * ``anchors``        — list of anchor views (one per Earth anchor)
      * ``orbital``        — dict with ``iss`` (or None), ``moon``, ``mars``

    Set ``allow_network=False`` to keep this strictly offline — orbital
    surfaces that need the network return ``None`` rather than blocking.
    """

    if here is None:
        here = resolve(allow_network=allow_network)
    if when is None:
        when = datetime.now(tz=timezone.utc)

    anchors_view = [_anchor_view(here, a, when) for a in all_anchors()]

    orbital = {
        "iss": _iss_view(here, allow_network=allow_network),
        "moon": _moon_view(),
        "mars": _mars_view(allow_network=allow_network),
    }

    return {
        "here": here.to_dict(),
        "when": when.isoformat(),
        "confidence": here.confidence,
        "anchors": anchors_view,
        "orbital": orbital,
    }
