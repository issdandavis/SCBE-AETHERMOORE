"""L1 — Earth anchor table.

Two surfaces:
  * ZONE_MERIDIANS — 12 equidistant longitudes (30 deg apart) used as
    timekeeping anchors. Latitude pinned to a representative city near
    each meridian where one exists.
  * KEY_LOCATIONS — named places that matter operationally (user home,
    PNNL, NZ for the deployed-agent example, Greenwich, DSN sites).

Adding a new anchor: just append a tuple. Tests assert that the meridian
spacing stays at 30 deg and that every key location has a non-empty label.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Anchor:
    label: str
    lat: float
    lon: float
    kind: str  # "zone_meridian" | "key_location" | "ground_station"
    notes: str = ""


# 12 meridians at 30 deg spacing, anchored to representative cities at
# mid-latitudes. UTC offset shown as a hint; not authoritative.
ZONE_MERIDIANS: tuple[Anchor, ...] = (
    Anchor("anadyr_ru", 64.7333, 177.5, "zone_meridian", "UTC+12"),
    Anchor("anchorage_us", 61.2181, -149.9003, "zone_meridian", "UTC-9"),
    Anchor("los_angeles_us", 34.0522, -118.2437, "zone_meridian", "UTC-8"),
    Anchor("mexico_city_mx", 19.4326, -99.1332, "zone_meridian", "UTC-6"),
    Anchor("caracas_ve", 10.4806, -66.9036, "zone_meridian", "UTC-4"),
    Anchor("reykjavik_is", 64.1466, -21.9426, "zone_meridian", "UTC+0 near 30W"),
    Anchor("greenwich_uk", 51.4779, -0.0015, "zone_meridian", "UTC+0"),
    Anchor("cairo_eg", 30.0444, 31.2357, "zone_meridian", "UTC+2"),
    Anchor("tehran_ir", 35.6892, 51.389, "zone_meridian", "UTC+3:30"),
    Anchor("dhaka_bd", 23.8103, 90.4125, "zone_meridian", "UTC+6"),
    Anchor("shanghai_cn", 31.2304, 121.4737, "zone_meridian", "UTC+8"),
    Anchor("vladivostok_ru", 43.1198, 131.8869, "zone_meridian", "UTC+10"),
)

KEY_LOCATIONS: tuple[Anchor, ...] = (
    Anchor("port_angeles_wa", 48.1181, -123.4307, "key_location", "user home"),
    Anchor("sequim_pnnl", 48.0813, -123.0426, "key_location", "PNNL marine campus"),
    Anchor("auckland_nz", -36.8485, 174.7633, "key_location", "deployed-agent example"),
    Anchor("cape_canaveral", 28.4889, -80.5778, "key_location", "launch reference"),
    # Deep Space Network sites — used as Mars-comm anchors at L4.
    Anchor("dsn_goldstone", 35.4267, -116.89, "ground_station", "DSN-10"),
    Anchor("dsn_madrid", 40.4314, -4.2481, "ground_station", "DSN-60"),
    Anchor("dsn_canberra", -35.4014, 148.9817, "ground_station", "DSN-40"),
)


def all_anchors() -> tuple[Anchor, ...]:
    return ZONE_MERIDIANS + KEY_LOCATIONS
