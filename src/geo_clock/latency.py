"""L2 — Latency floors.

Three physically-grounded round-trip-time models so an agent can answer
"which path is fastest from here to there" without phoning home:

  * fiber_rtt_ms           — terrestrial fiber, c * 0.67 velocity factor
  * leo_starlink_rtt_ms    — 4-leg LEO bounce at 550 km altitude
  * vacuum_rtt_ms          — speed-of-light floor (deep-space comms)

These are *floors*. Real RTT is always >= the floor (queueing, peering,
beam-switching). A measured-RTT plug-in can replace the floor when a
RIPE Atlas / Cloudflare Radar probe is available; ``measured_rtt_ms``
falls back to the floor on any failure.

Crossover note: LEO beats fiber when the great-circle distance exceeds
~2200 km. Below that, fiber wins. The compass uses both numbers so the
caller picks the path, not the model.
"""

from __future__ import annotations

from dataclasses import dataclass

# Speed of light in vacuum, km/s.
C_KMPS = 299792.458

# Effective fiber velocity ~ 0.67 c (typical single-mode silica VoP).
FIBER_VOP = 0.67

# Starlink shell altitude (km). Other LEO providers (Kuiper, OneWeb) sit
# in the 600..1200 km band; using 550 keeps the floor representative
# rather than provider-specific.
LEO_ALTITUDE_KM = 550.0


@dataclass(frozen=True)
class RttQuote:
    """Bundle of floors so the caller can compare paths."""

    distance_km: float
    fiber_ms: float
    leo_ms: float
    vacuum_ms: float
    best_path: str  # "fiber" | "leo" | "vacuum"

    def to_dict(self) -> dict:
        return {
            "distance_km": self.distance_km,
            "fiber_ms": self.fiber_ms,
            "leo_ms": self.leo_ms,
            "vacuum_ms": self.vacuum_ms,
            "best_path": self.best_path,
        }


def vacuum_rtt_ms(distance_km: float) -> float:
    """Round-trip time at exactly c. Floor for any link, terrestrial or not."""
    return 2.0 * distance_km / C_KMPS * 1000.0


def fiber_rtt_ms(distance_km: float) -> float:
    """Terrestrial fiber RTT floor.

    Approx 0.01 ms per km (0.0099 to be exact at VoP=0.67). Doesn't model
    the great-circle vs cable-route discrepancy — real fiber is ~1.3x
    longer than the geodesic — but the floor is honest.
    """
    return 2.0 * distance_km / (C_KMPS * FIBER_VOP) * 1000.0


def leo_starlink_rtt_ms(distance_km: float, altitude_km: float = LEO_ALTITUDE_KM) -> float:
    """4-leg LEO RTT: ground -> sat -> sat -> ground -> sat -> ground.

    For the floor we use the simple 2-bounce model (up, lateral, down,
    then symmetric back) at vacuum c. Real Starlink adds inter-sat hops
    and ground-station relays, so the floor under-estimates short routes
    and over-estimates very long ones — both bounded by a few ms.
    """
    # Up + down legs (each direction): 2 * altitude * 2 = 4 * altitude.
    vertical_km = 4.0 * altitude_km
    # Lateral path along the constellation, both directions.
    lateral_km = 2.0 * distance_km
    return (vertical_km + lateral_km) / C_KMPS * 1000.0


def crossover_km() -> float:
    """Distance at which LEO floor matches fiber floor.

    Solve: (4*alt + 2*d)/c = 2*d/(0.67*c)
       =>  4*alt = 2*d*(1/0.67 - 1) = 2*d*(0.4925)
       =>  d = 4*alt / (2*0.4925) ~ 4.06 * alt
    For alt=550 km that's ~2235 km.
    """
    factor_gain = (1.0 / FIBER_VOP) - 1.0
    return 4.0 * LEO_ALTITUDE_KM / (2.0 * factor_gain)


def best_path(distance_km: float, *, vacuum_ok: bool = False) -> str:
    """Pick the fastest *floor* model for this distance.

    ``vacuum_ok=True`` lets deep-space links pick the vacuum floor; for
    Earth-to-Earth links vacuum is unreachable so it's hidden.
    """
    fib = fiber_rtt_ms(distance_km)
    leo = leo_starlink_rtt_ms(distance_km)
    if vacuum_ok:
        vac = vacuum_rtt_ms(distance_km)
        return min(("fiber", fib), ("leo", leo), ("vacuum", vac), key=lambda kv: kv[1])[0]
    return "fiber" if fib <= leo else "leo"


def quote(distance_km: float, *, vacuum_ok: bool = False) -> RttQuote:
    """Bundle all three floors plus the winner."""
    return RttQuote(
        distance_km=distance_km,
        fiber_ms=fiber_rtt_ms(distance_km),
        leo_ms=leo_starlink_rtt_ms(distance_km),
        vacuum_ms=vacuum_rtt_ms(distance_km),
        best_path=best_path(distance_km, vacuum_ok=vacuum_ok),
    )


def measured_rtt_ms(
    distance_km: float,
    *,
    probe: str | None = None,
    timeout_s: float = 2.0,
) -> float:
    """Return measured RTT if a probe is available, else the fiber floor.

    The hook is intentionally narrow: it does not import any probe SDK at
    module load. A future RIPE Atlas / Cloudflare Radar wrapper can swap
    itself in by passing ``probe="ripe-atlas:<id>"`` etc. Until then we
    return the deterministic floor so callers can rely on the interface.
    """
    del probe, timeout_s  # placeholder for the plug-in surface
    return fiber_rtt_ms(distance_km)
