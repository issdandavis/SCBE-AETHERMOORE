"""L4 — Deep-space body distances and light-time.

Reuses the canonical EDE constants
(``src/symphonic_cipher/scbe_aethermoore/ede``) so the geo-clock and the
Entropic Defense Engine agree on Earth-Mars geometry. The ede module
ships ``LIGHT_SPEED``, ``MARS_DISTANCE_MIN/MAX``, and
``MARS_LIGHT_TIME_MIN/MAX`` — we don't redefine them here, we import.

Mission-state for a Mars-deployed agent (terrain mapping, code patches,
return-home routing) is *not* this module's job — that's
``src/geoseal_mission_compass.py``. ``bodies.py`` only answers "where is
body X right now and what is the comm RTT floor."
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.symphonic_cipher.scbe_aethermoore.ede.spiral_ring import (
    LIGHT_SPEED,  # m/s
    MARS_DISTANCE_MAX,  # m  (~401e9)
    MARS_DISTANCE_MIN,  # m  (~54.6e9)
    MARS_LIGHT_TIME_MAX,  # s  (~1338)
    MARS_LIGHT_TIME_MIN,  # s  (~182)
)

# Moon mean Earth-center to Moon-center distance. We don't have a
# canonical EDE constant for this yet; the IAU mean is widely cited.
MOON_DISTANCE_MEAN_M = 384_400_000.0  # ~1.28 light-seconds one-way


@dataclass(frozen=True)
class BodyState:
    name: str
    distance_m: float
    one_way_light_s: float
    rtt_s: float
    source: str  # "ede:constant" | "ede:midpoint" | "horizons" | "moon:mean"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "distance_m": self.distance_m,
            "one_way_light_s": self.one_way_light_s,
            "rtt_s": self.rtt_s,
            "source": self.source,
        }


def _state(name: str, distance_m: float, source: str) -> BodyState:
    one_way = distance_m / LIGHT_SPEED
    return BodyState(
        name=name,
        distance_m=distance_m,
        one_way_light_s=one_way,
        rtt_s=2.0 * one_way,
        source=source,
    )


def moon_state() -> BodyState:
    """Mean Moon distance/light-time. Sufficient for compass display.

    Replace with an ephemeris call (Skyfield / SPICE) if a deployed
    lunar agent needs sub-second comm-window precision.
    """
    return _state("moon", MOON_DISTANCE_MEAN_M, "moon:mean")


def mars_state(*, distance_m: Optional[float] = None) -> BodyState:
    """Mars distance/light-time. Default to mid-range conjunction average.

    Pass ``distance_m`` from a real ephemeris (NASA Horizons, SPICE) to
    get the live value. Without it we return the EDE midpoint, which is
    what the EDE protocol uses by default.
    """
    if distance_m is None:
        distance_m = (MARS_DISTANCE_MIN + MARS_DISTANCE_MAX) / 2.0
        source = "ede:midpoint"
    else:
        source = "horizons"
    return _state("mars", distance_m, source)


def mars_extremes() -> tuple[BodyState, BodyState]:
    """Return (closest, farthest) Mars states for compass min/max display."""
    return (
        _state("mars_closest", MARS_DISTANCE_MIN, "ede:constant"),
        _state("mars_farthest", MARS_DISTANCE_MAX, "ede:constant"),
    )


def fetch_horizons_distance_m(body: str = "499", timeout: float = 4.0) -> Optional[float]:
    """Optional: pull live Earth-Mars distance from NASA Horizons.

    Returns metres or ``None`` on any failure. Body code 499 = Mars
    barycenter. Network call kept narrow so the module loads cleanly
    without ``requests``; callers that want live ephemeris ask for it.
    """
    try:
        import requests  # noqa: WPS433 optional dep
    except ImportError:
        return None
    params = {
        "format": "text",
        "COMMAND": f"'{body}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'500@399'",  # geocentric
        "QUANTITIES": "'20'",  # observer range
        "STEP_SIZE": "'1'",
    }
    try:
        r = requests.get("https://ssd.jpl.nasa.gov/api/horizons.api", params=params, timeout=timeout)
        if r.status_code != 200:
            return None
        text = r.text
        # Look for an AU range value between $$SOE and $$EOE.
        soe = text.find("$$SOE")
        eoe = text.find("$$EOE")
        if soe < 0 or eoe < 0 or eoe < soe:
            return None
        block = text[soe + 5 : eoe].strip().splitlines()
        if not block:
            return None
        # Format: "<date> <range_AU> <delta-dot>"
        parts = block[0].split()
        # Last column is range-rate; the column before that is range_AU.
        # Be defensive — Horizons formatting varies.
        for token in reversed(parts):
            try:
                au = float(token)
                # AU = 1.495978707e11 m. Sanity gate: 0.3..2.7 AU for Mars.
                if 0.2 < au < 3.0:
                    return au * 1.495978707e11
            except ValueError:
                continue
        return None
    except Exception:
        return None
