"""
Tongue Regions & Tower Floors (Python reference).

Mirrors src/game/regions.ts. Six tongue regions + 100-floor manhwa tower.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .types import TongueCode


@dataclass(frozen=True)
class TongueRegion:
    id: str
    name: str
    tongue: TongueCode
    palette: Tuple[str, str, str]  # primary, secondary, accent
    architecture_style: str
    floor_range: Tuple[int, int]
    description: str


@dataclass(frozen=True)
class TowerFloor:
    floor: int
    math_domain: str
    rank: str
    encounters: int
    mini_boss: bool
    boss: bool
    region: str


REGIONS: Tuple[TongueRegion, ...] = (
    TongueRegion(
        "ember_reach", "Ember Reach", "KO",
        ("#DC503C", "#E8963C", "#FFD080"),
        "Spiral-roof shrines, war temples, forge halls",
        (1, 20),
        "The command heartland. Where the first Tongue was spoken.",
    ),
    TongueRegion(
        "aerial_expanse", "Aerial Expanse", "AV",
        ("#5CB8E0", "#3C9090", "#E0F0FF"),
        "Wind-bridges, sky platforms, transit hubs",
        (11, 30),
        "The transport network. Wind carries the Tongue.",
    ),
    TongueRegion(
        "null_vale", "Null Vale", "RU",
        ("#8040C0", "#606080", "#C0A0E0"),
        "Broken symmetry ruins, glitch terrain, entropy vents",
        (21, 50),
        "Where order breaks down. The bold find power here.",
    ),
    TongueRegion(
        "glass_drift", "Glass Drift", "CA",
        ("#3CD8D8", "#D8C040", "#FFFFFF"),
        "Geometric lattice cities, crystal processors, data towers",
        (31, 60),
        "The compute core. Logic made manifest.",
    ),
    TongueRegion(
        "ward_sanctum", "Ward Sanctum", "UM",
        ("#40B870", "#F0F0E0", "#006830"),
        "Crystal ward pylons, sealed vaults, cleansing pools",
        (41, 80),
        "The security bastion. Nothing corrupted survives.",
    ),
    TongueRegion(
        "bastion_fields", "Bastion Fields", "DR",
        ("#909080", "#D89898", "#C0C0D0"),
        "Floating fractal towers, verification gates",
        (51, 100),
        "The structure pinnacle. Only the proven may enter.",
    ),
)

_RANKS = [
    (10, "F"), (20, "E"), (30, "D"), (40, "C"), (50, "B"),
    (60, "A"), (70, "S"), (80, "SS"), (90, "SSS"),
    (99, "Transcendent"), (100, "Millennium"),
]

_DOMAINS = [
    (10, "Arithmetic, basic algebra"),
    (20, "Quadratics, systems of equations"),
    (30, "Functions, graphing, transformations"),
    (40, "Limits, sequences, convergence"),
    (50, "Proofs, formal logic"),
    (60, "Linear algebra, matrix theory"),
    (70, "Discrete mathematics, combinatorics"),
    (80, "Real analysis, topology"),
    (90, "Optimization, variational methods"),
    (99, "Open research problems"),
    (100, "Millennium Prize problems"),
]

_FLOOR_REGIONS = [
    (15, "ember_reach"), (25, "aerial_expanse"), (40, "null_vale"),
    (55, "glass_drift"), (75, "ward_sanctum"), (100, "bastion_fields"),
]


def _lookup(lst: list, floor: int) -> object:
    for max_f, val in lst:
        if floor <= max_f:
            return val
    return lst[-1][1]


def get_tower_floor(floor: int) -> TowerFloor:
    if floor < 1 or floor > 100:
        raise ValueError(f"Floor must be 1-100, got {floor}")
    return TowerFloor(
        floor=floor,
        math_domain=str(_lookup(_DOMAINS, floor)),
        rank=str(_lookup(_RANKS, floor)),
        encounters=5,
        mini_boss=(floor % 5 == 0),
        boss=(floor % 10 == 0),
        region=str(_lookup(_FLOOR_REGIONS, floor)),
    )


def get_rank(floor: int) -> str:
    return str(_lookup(_RANKS, max(1, min(100, floor))))


def get_region_by_tongue(tongue: TongueCode) -> Optional[TongueRegion]:
    for r in REGIONS:
        if r.tongue == tongue:
            return r
    return None
