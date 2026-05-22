"""Standalone narrative combat generator vertical slice."""

from .fixtures import boss_duel_demo
from .loader import (
    EncounterSpecError,
    encounter_from_dict,
    encounter_to_dict,
    load_encounter,
)
from .models import Encounter, Feature, Fighter, Technique, Terrain

__all__ = [
    "Encounter",
    "EncounterSpecError",
    "Feature",
    "Fighter",
    "Technique",
    "Terrain",
    "boss_duel_demo",
    "encounter_from_dict",
    "encounter_to_dict",
    "load_encounter",
]
