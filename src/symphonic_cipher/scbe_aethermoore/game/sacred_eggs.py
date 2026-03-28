"""
Sacred Egg Hatching — Behavioral Selection in B^6 (Python reference).

Mirrors src/game/sacredEggs.ts.
Eggs hatch when player tongue experience hits specific regions in R^6.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from .types import BondType, EggType, TongueCode, TongueVector, TONGUE_CODES


def _tv(v: TongueVector, code: TongueCode) -> float:
    return v[TONGUE_CODES.index(code)]


@dataclass(frozen=True)
class HatchResult:
    egg_type: EggType
    egg_name: str
    bond_type: BondType
    dominant_tongue: Optional[TongueCode]
    description: str


@dataclass(frozen=True)
class _EggDef:
    egg_type: EggType
    name: str
    bond_type: BondType
    dominant_tongue: Optional[TongueCode]
    condition: Callable[[TongueVector], bool]
    description: str


# Mono-tongue eggs
_MONO_EGGS: List[_EggDef] = [
    _EggDef(
        "mono_KO",
        "Ember Egg",
        "amplifier",
        "KO",
        lambda v: _tv(v, "KO") >= 0.6 and _tv(v, "KO") > 2 * _tv(v, "DR"),
        "KO >= 0.6 AND KO > 2×DR",
    ),
    _EggDef(
        "mono_AV",
        "Gale Egg",
        "scout",
        "AV",
        lambda v: _tv(v, "AV") >= 0.5 and _tv(v, "AV") > 1.5 * _tv(v, "UM"),
        "AV >= 0.5 AND AV > 1.5×UM",
    ),
    _EggDef(
        "mono_RU",
        "Void Egg",
        "disruptor",
        "RU",
        lambda v: _tv(v, "RU") >= 0.5 and _tv(v, "RU") > 1.5 * _tv(v, "CA"),
        "RU >= 0.5 AND RU > 1.5×CA",
    ),
    _EggDef(
        "mono_CA",
        "Crystal Egg",
        "processor",
        "CA",
        lambda v: _tv(v, "CA") >= 0.5 and _tv(v, "CA") > 1.5 * _tv(v, "RU"),
        "CA >= 0.5 AND CA > 1.5×RU",
    ),
    _EggDef(
        "mono_UM",
        "Ward Egg",
        "guardian",
        "UM",
        lambda v: _tv(v, "UM") >= 0.5 and _tv(v, "UM") > 1.5 * _tv(v, "AV"),
        "UM >= 0.5 AND UM > 1.5×AV",
    ),
    _EggDef(
        "mono_DR",
        "Helix Egg",
        "architect",
        "DR",
        lambda v: _tv(v, "DR") >= 0.5 and _tv(v, "DR") > 1.5 * _tv(v, "KO"),
        "DR >= 0.5 AND DR > 1.5×KO",
    ),
]

# Hodge dual eggs
_HODGE_EGGS: List[_EggDef] = [
    _EggDef(
        "hodge_eclipse",
        "Eclipse Egg",
        "harmonizer",
        None,
        lambda v: _tv(v, "KO") >= 0.4 and _tv(v, "DR") >= 0.4 and abs(_tv(v, "KO") - _tv(v, "DR")) < 0.15,
        "KO >= 0.4 AND DR >= 0.4 AND |KO-DR| < 0.15",
    ),
    _EggDef(
        "hodge_storm",
        "Storm Egg",
        "balancer",
        None,
        lambda v: _tv(v, "AV") >= 0.4 and _tv(v, "UM") >= 0.4 and abs(_tv(v, "AV") - _tv(v, "UM")) < 0.15,
        "AV >= 0.4 AND UM >= 0.4 AND |AV-UM| < 0.15",
    ),
    _EggDef(
        "hodge_paradox",
        "Paradox Egg",
        "synthesizer",
        None,
        lambda v: _tv(v, "RU") >= 0.4 and _tv(v, "CA") >= 0.4 and abs(_tv(v, "RU") - _tv(v, "CA")) < 0.15,
        "RU >= 0.4 AND CA >= 0.4 AND |RU-CA| < 0.15",
    ),
]

# Omni egg
_OMNI_EGG = _EggDef(
    "omni_prism",
    "Prism Egg",
    "nexus",
    None,
    lambda v: all(x >= 0.35 for x in v),
    "Every tongue >= 0.35",
)

# Evaluation order: omni → hodge → mono (rarer first)
_ALL_EGGS: List[_EggDef] = [_OMNI_EGG] + _HODGE_EGGS + _MONO_EGGS


def check_hatchable_eggs(player_tongue: TongueVector) -> List[HatchResult]:
    """Check which eggs can hatch given player's tongue accumulation."""
    results: List[HatchResult] = []
    for egg in _ALL_EGGS:
        if egg.condition(player_tongue):
            results.append(
                HatchResult(
                    egg_type=egg.egg_type,
                    egg_name=egg.name,
                    bond_type=egg.bond_type,
                    dominant_tongue=egg.dominant_tongue,
                    description=egg.description,
                )
            )
    return results


def can_hatch_egg(player_tongue: TongueVector, egg_type: EggType) -> bool:
    """Check if a specific egg type can hatch."""
    for egg in _ALL_EGGS:
        if egg.egg_type == egg_type:
            return egg.condition(player_tongue)
    return False


def egg_starting_tongue(egg_type: EggType) -> TongueVector:
    """Get initial tongue position for a companion from this egg type."""
    mapping: dict[EggType, TongueVector] = {
        "mono_KO": (0.6, 0.1, 0.1, 0.1, 0.1, 0.1),
        "mono_AV": (0.1, 0.6, 0.1, 0.1, 0.1, 0.1),
        "mono_RU": (0.1, 0.1, 0.6, 0.1, 0.1, 0.1),
        "mono_CA": (0.1, 0.1, 0.1, 0.6, 0.1, 0.1),
        "mono_UM": (0.1, 0.1, 0.1, 0.1, 0.6, 0.1),
        "mono_DR": (0.1, 0.1, 0.1, 0.1, 0.1, 0.6),
        "hodge_eclipse": (0.4, 0.1, 0.1, 0.1, 0.1, 0.4),
        "hodge_storm": (0.1, 0.4, 0.1, 0.1, 0.4, 0.1),
        "hodge_paradox": (0.1, 0.1, 0.4, 0.4, 0.1, 0.1),
        "omni_prism": (0.35, 0.35, 0.35, 0.35, 0.35, 0.35),
    }
    return mapping[egg_type]
