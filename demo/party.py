#!/usr/bin/env python3
"""
Party Management, Level-Up, and Evolution System
=================================================
Pokemon/Digimon-style party management with Six Sacred Tongues integration.

Subsystems:
  - PartyManager: 6-slot party + unlimited storage (PC box).
  - LevelUpSystem: XP curve, stat growth, move learning per tongue.
  - EvolutionManager: Fresh -> Rookie -> Champion -> Ultimate -> Mega -> Ultra.
  - PartyScreen: Pygame UI for party inspection.
  - EvolutionAnimation: Pygame evolution cutscene.
  - StorageScreen: Pygame PC-box grid view.

All evolution and leveling feed training-data through the engine's TrainingExporter.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    import pygame
except ImportError:
    pygame = None  # type: ignore[assignment]

from engine import (
    Character,
    EvoStage,
    Palette,
    Spell,
    Stats,
    Tongue,
    TONGUE_NAMES,
    TONGUE_WEIGHTS,
    PHI,
    generate_sprite,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_PARTY = 6
MAX_LEVEL = 50
STORAGE_BOX_COLS = 5
STORAGE_BOX_ROWS = 6
STORAGE_BOX_SIZE = STORAGE_BOX_COLS * STORAGE_BOX_ROWS  # 30 per box

SCREEN_W, SCREEN_H = 640, 480

# ---------------------------------------------------------------------------
# Level Thresholds (XP needed to reach each level, index 0 = lvl 1)
# Uses a quadratic + phi scaling: base * (level ^ 1.6) * phi_factor
# ---------------------------------------------------------------------------
def _build_level_thresholds() -> List[int]:
    """Generate XP required to reach each level (cumulative).

    Uses a quadratic-exponential curve with phi scaling.
    Slow early, ramps after 20, brutal after 35.
    Level 50 should be ~100k+ XP (endgame grind).
    """
    thresholds = [0]  # Level 1 = 0 XP
    for lvl in range(2, MAX_LEVEL + 1):
        base = 40
        scaling = base * (lvl ** 2.1)
        phi_factor = 1.0 + (PHI - 1.0) * (lvl / MAX_LEVEL)
        thresholds.append(int(scaling * phi_factor))
    return thresholds

LEVEL_THRESHOLDS: List[int] = _build_level_thresholds()
# XP needed to go FROM level N to level N+1
LEVEL_XP_DELTAS: List[int] = [
    (LEVEL_THRESHOLDS[i] - LEVEL_THRESHOLDS[i - 1]) if i > 0 else 0
    for i in range(len(LEVEL_THRESHOLDS))
]


# ---------------------------------------------------------------------------
# Tongue Growth Rates (stat multipliers per tongue affinity)
# ---------------------------------------------------------------------------
# Each tongue has a preferred growth pattern for HP/MP/ATK/DEF/SPD/WIS.
# Values are *bonus per level* (added to a flat base gain).
TONGUE_GROWTH_RATES: Dict[Tongue, Dict[str, float]] = {
    Tongue.KO: {"hp": 2.0, "mp": 4.0, "attack": 1.0, "defense": 1.0, "speed": 2.0, "wisdom": 4.0},
    Tongue.AV: {"hp": 2.5, "mp": 3.0, "attack": 1.5, "defense": 1.0, "speed": 4.0, "wisdom": 3.0},
    Tongue.RU: {"hp": 4.0, "mp": 1.5, "attack": 3.0, "defense": 4.0, "speed": 1.0, "wisdom": 2.0},
    Tongue.CA: {"hp": 3.0, "mp": 3.5, "attack": 1.5, "defense": 2.0, "speed": 2.0, "wisdom": 4.0},
    Tongue.UM: {"hp": 3.0, "mp": 2.5, "attack": 3.5, "defense": 2.0, "speed": 3.5, "wisdom": 2.0},
    Tongue.DR: {"hp": 2.5, "mp": 3.0, "attack": 3.0, "defense": 2.5, "speed": 2.5, "wisdom": 3.0},
}

# Base gain every character gets regardless of tongue
BASE_GROWTH: Dict[str, float] = {
    "hp": 3.0, "mp": 2.0, "attack": 1.0, "defense": 1.0, "speed": 1.0, "wisdom": 1.0,
}


# ---------------------------------------------------------------------------
# Learnable Moves per Tongue (at least 6 each, spread across levels 1-40)
# ---------------------------------------------------------------------------
LEARNABLE_MOVES: Dict[Tongue, List[Tuple[int, Spell]]] = {
    Tongue.KO: [
        (1,  Spell("Command Bark",       Tongue.KO, 10, 4,  "A sharp authoritative shout that stuns.")),
        (5,  Spell("Edict Pulse",        Tongue.KO, 16, 8,  "Wave of authoritative energy.")),
        (10, Spell("Wingscroll Blast",   Tongue.KO, 20, 10, "Unleash archived knowledge as a searing beam.")),
        (16, Spell("Cosmic Familiar Bond", Tongue.KO, 0, 5, "Share HP with bonded partner, heal 15% each.")),
        (22, Spell("Authority Seal",     Tongue.KO, 28, 16, "Stamp an edict onto the enemy -- locks one move.")),
        (30, Spell("Archive Recall",     Tongue.KO, 30, 20, "Recall an ancient technique -- random powerful effect.")),
        (37, Spell("Sovereign Decree",   Tongue.KO, 42, 28, "Absolute command -- massive damage, costs dearly.")),
    ],
    Tongue.AV: [
        (1,  Spell("Signal Ping",        Tongue.AV, 8,  3,  "Quick burst of transport energy.")),
        (4,  Spell("Ley Pulse",          Tongue.AV, 14, 7,  "Channel a ley line's energy.")),
        (10, Spell("Ley Line Pulse",     Tongue.AV, 22, 12, "Directed beam of ley energy.")),
        (15, Spell("Portal Step",        Tongue.AV, 0,  18, "Open a short-range portal -- escape or reposition.")),
        (20, Spell("Cartographic Scan",  Tongue.AV, 0,  6,  "Reveal enemy stats and weaknesses.")),
        (28, Spell("Transit Storm",      Tongue.AV, 32, 20, "Barrage of transport particles.")),
        (36, Spell("Dimensional Relay",  Tongue.AV, 45, 30, "Route an attack through a dimensional relay -- piercing.")),
    ],
    Tongue.RU: [
        (1,  Spell("Policy Jab",         Tongue.RU, 10, 4,  "A blunt constraint strike.")),
        (5,  Spell("Sand Wall",          Tongue.RU, 0,  8,  "Raise a defensive barrier -- +50% DEF for 2 turns.")),
        (11, Spell("Golem Slam",         Tongue.RU, 30, 12, "Crushing earth strike. Ignores 30% of enemy DEF.")),
        (17, Spell("Threshold Lock",     Tongue.RU, 0,  12, "Seal a portal or passage.")),
        (24, Spell("Guardian Strike",    Tongue.RU, 28, 16, "Heavy strike empowered by oath of protection.")),
        (32, Spell("Runethic Mandate",   Tongue.RU, 38, 22, "Inscribe a binding rule onto reality itself.")),
        (40, Spell("Absolute Constraint", Tongue.RU, 50, 32, "The ultimate policy -- nothing escapes.")),
    ],
    Tongue.CA: [
        (1,  Spell("Data Spark",         Tongue.CA, 9,  4,  "A crackling compute spark.")),
        (5,  Spell("Pocket Fold",        Tongue.CA, 15, 8,  "Store an enemy in a micro-dimension for 1 turn.")),
        (10, Spell("Equation Shield",    Tongue.CA, 0,  10, "Mathematical barrier -- reflects 25% of incoming.")),
        (15, Spell("Dimensional Shift",  Tongue.CA, 25, 15, "Phase through attacks by shifting planes.")),
        (22, Spell("Code Crack",         Tongue.CA, 20, 12, "Break through defenses by decrypting schema.")),
        (30, Spell("Cipher Cascade",     Tongue.CA, 36, 24, "Torrent of encrypted energy -- multi-hit.")),
        (38, Spell("Singularity Fold",   Tongue.CA, 52, 35, "Collapse a pocket dimension onto the enemy.")),
    ],
    Tongue.UM: [
        (1,  Spell("Shadow Nip",         Tongue.UM, 10, 4,  "A quick bite from the shadows.")),
        (5,  Spell("Shadow Step",        Tongue.UM, 18, 10, "Phase through obstacles using shadow.")),
        (12, Spell("Boundary Slash",     Tongue.UM, 28, 14, "Cut through dimensional boundaries.")),
        (18, Spell("Nightwhisper",       Tongue.UM, 30, 20, "Shadow whisper -- disrupts enemy focus.")),
        (25, Spell("Warrior's Theorem",  Tongue.UM, 35, 22, "Solve an equation to find the perfect strike angle.")),
        (33, Spell("Umbral Veil",        Tongue.UM, 0,  16, "Cloak in deep shadow -- next attack guaranteed crit.")),
        (40, Spell("Void Rend",          Tongue.UM, 55, 35, "Tear open the void itself -- ignores all defense.")),
    ],
    Tongue.DR: [
        (1,  Spell("Spark Script",       Tongue.DR, 8,  3,  "A tiny dragon-fire glyph.")),
        (5,  Spell("Scale Armor",        Tongue.DR, 0,  8,  "Dragon scales form protective circuit patterns.")),
        (10, Spell("Pattern Glimpse",    Tongue.DR, 12, 7,  "Read the underlying patterns of magic.")),
        (16, Spell("Dragonfire Compile", Tongue.DR, 32, 16, "Breathe schema-fire that authenticates and burns.")),
        (24, Spell("Aether Breath",      Tongue.DR, 35, 20, "Dragon fire infused with forge-tongue authority.")),
        (32, Spell("Forge Rune Seal",    Tongue.DR, 40, 24, "Brand the enemy with a schema seal -- DoT.")),
        (40, Spell("Draumric Genesis",   Tongue.DR, 56, 36, "Re-author reality from schema -- ultimate creation.")),
    ],
}


# ---------------------------------------------------------------------------
# Evolution Stat Multipliers
# ---------------------------------------------------------------------------
EVOLUTION_STAT_MULTIPLIERS: Dict[EvoStage, float] = {
    EvoStage.FRESH:    1.0,
    EvoStage.ROOKIE:   1.15,
    EvoStage.CHAMPION: 1.35,
    EvoStage.ULTIMATE: 1.60,
    EvoStage.MEGA:     1.90,
    EvoStage.ULTRA:    2.30,
}

# Ordered list for stage progression
_EVO_ORDER: List[EvoStage] = [
    EvoStage.FRESH,
    EvoStage.ROOKIE,
    EvoStage.CHAMPION,
    EvoStage.ULTIMATE,
    EvoStage.MEGA,
    EvoStage.ULTRA,
]

# Bonus moves granted upon evolution to each stage
EVOLUTION_BONUS_MOVES: Dict[EvoStage, Dict[Tongue, Spell]] = {
    EvoStage.ROOKIE: {
        Tongue.KO: Spell("Edict Pulse",       Tongue.KO, 16, 8,  "Wave of authoritative energy."),
        Tongue.AV: Spell("Ley Pulse",         Tongue.AV, 14, 7,  "Channel a ley line's energy."),
        Tongue.RU: Spell("Sand Wall",         Tongue.RU, 0,  8,  "Raise a defensive barrier."),
        Tongue.CA: Spell("Pocket Fold",        Tongue.CA, 15, 8,  "Store an enemy in a micro-dimension."),
        Tongue.UM: Spell("Shadow Step",        Tongue.UM, 18, 10, "Phase through using shadow."),
        Tongue.DR: Spell("Scale Armor",        Tongue.DR, 0,  8,  "Dragon scales form protective patterns."),
    },
    EvoStage.CHAMPION: {
        Tongue.KO: Spell("Authority Seal",     Tongue.KO, 28, 16, "Stamp an edict -- locks one move."),
        Tongue.AV: Spell("Transit Storm",      Tongue.AV, 32, 20, "Barrage of transport particles."),
        Tongue.RU: Spell("Runethic Mandate",   Tongue.RU, 38, 22, "Inscribe a binding rule."),
        Tongue.CA: Spell("Cipher Cascade",     Tongue.CA, 36, 24, "Torrent of encrypted energy."),
        Tongue.UM: Spell("Umbral Veil",        Tongue.UM, 0,  16, "Cloak in shadow -- next attack crits."),
        Tongue.DR: Spell("Forge Rune Seal",    Tongue.DR, 40, 24, "Brand with schema seal."),
    },
    EvoStage.ULTIMATE: {
        Tongue.KO: Spell("Sovereign Decree",   Tongue.KO, 42, 28, "Absolute command -- massive damage."),
        Tongue.AV: Spell("Dimensional Relay",  Tongue.AV, 45, 30, "Route attack through relay -- piercing."),
        Tongue.RU: Spell("Absolute Constraint", Tongue.RU, 50, 32, "The ultimate policy."),
        Tongue.CA: Spell("Singularity Fold",   Tongue.CA, 52, 35, "Collapse a pocket dimension."),
        Tongue.UM: Spell("Void Rend",          Tongue.UM, 55, 35, "Tear open the void -- ignores defense."),
        Tongue.DR: Spell("Draumric Genesis",   Tongue.DR, 56, 36, "Re-author reality from schema."),
    },
    EvoStage.MEGA: {
        Tongue.KO: Spell("Kor Protocol Override", Tongue.KO, 60, 38, "Override all governance -- one turn of godmode."),
        Tongue.AV: Spell("Avalon Gate",        Tongue.AV, 58, 36, "Open the Academy gate -- party-wide warp."),
        Tongue.RU: Spell("World Tree Anchor",  Tongue.RU, 62, 38, "Bind to the World Tree -- massive regen."),
        Tongue.CA: Spell("Dimension Collapse",  Tongue.CA, 65, 40, "Collapse all dimensions into a single point."),
        Tongue.UM: Spell("Nightwhisper Omega", Tongue.UM, 64, 38, "All shadows answer -- area devastation."),
        Tongue.DR: Spell("Dragon Genesis",     Tongue.DR, 66, 40, "Birth a schema dragon -- summon ally."),
    },
    EvoStage.ULTRA: {
        Tongue.KO: Spell("Six Tongue Convergence", Tongue.KO, 80, 50, "All tongues resonate as one -- transcendent."),
        Tongue.AV: Spell("Omnipresent Relay",  Tongue.AV, 75, 48, "Exist everywhere simultaneously."),
        Tongue.RU: Spell("Eternal Mandate",    Tongue.RU, 78, 50, "A rule that cannot be broken."),
        Tongue.CA: Spell("Infinite Fold",      Tongue.CA, 82, 52, "Infinite dimensional recursion."),
        Tongue.UM: Spell("Absolute Shadow",    Tongue.UM, 80, 50, "Become the shadow itself."),
        Tongue.DR: Spell("Aethermoore Rewrite", Tongue.DR, 85, 55, "Rewrite the world's schema."),
    },
}


# ---------------------------------------------------------------------------
# Extended Character Tracking (wraps engine.Character with level/XP)
# ---------------------------------------------------------------------------
@dataclass
class CharacterState:
    """Extended tracking for a Character in the party system.

    The engine's Character has stats.level as a property derived from
    tongue proficiency. This wrapper adds explicit integer level + XP
    for the traditional RPG loop, and tracks boss kills for evolution
    requirements.
    """
    character: Character
    level: int = 1
    xp: int = 0
    total_xp: int = 0
    bosses_defeated: int = 0
    quests_completed: int = 0

    @property
    def xp_for_next(self) -> int:
        """XP required to reach the next level."""
        if self.level >= MAX_LEVEL:
            return 0
        return LEVEL_THRESHOLDS[self.level] - self.total_xp

    @property
    def xp_progress(self) -> float:
        """Progress toward next level as 0.0 - 1.0."""
        if self.level >= MAX_LEVEL:
            return 1.0
        delta = LEVEL_XP_DELTAS[self.level] if self.level < len(LEVEL_XP_DELTAS) else 1
        if delta <= 0:
            return 1.0
        current_in_level = self.total_xp - LEVEL_THRESHOLDS[self.level - 1]
        return min(1.0, max(0.0, current_in_level / delta))


# ---------------------------------------------------------------------------
# LevelUpSystem
# ---------------------------------------------------------------------------
class LevelUpSystem:
    """Handles XP gain, level-ups, stat boosts, and move learning."""

    @staticmethod
    def check_level_up(cstate: CharacterState, xp_gained: int) -> List[str]:
        """Award XP and return a list of event strings.

        Events can be:
          - "Level 12!"
          - "Learned Ley Pulse!"
          - "Ready to evolve!"
        """
        events: List[str] = []
        cstate.xp += xp_gained
        cstate.total_xp += xp_gained

        # Level-up loop (can gain multiple levels at once)
        while cstate.level < MAX_LEVEL:
            needed = LEVEL_THRESHOLDS[cstate.level]  # XP to reach level+1
            if cstate.total_xp < needed:
                break

            cstate.level += 1
            events.append(f"Level {cstate.level}!")
            LevelUpSystem.apply_level_up(cstate)

            # Check for new moves
            tongue = cstate.character.tongue_affinity
            move_table = LEARNABLE_MOVES.get(tongue, [])
            for req_level, spell in move_table:
                if req_level == cstate.level:
                    # Don't add duplicates
                    existing_names = {s.name for s in cstate.character.spells}
                    if spell.name not in existing_names:
                        cstate.character.spells.append(spell)
                        events.append(f"Learned {spell.name}!")

            # Check evolution readiness
            evo_mgr = EvolutionManager()
            next_evo = evo_mgr.check_evolution(cstate)
            if next_evo is not None:
                events.append("Ready to evolve!")

        return events

    @staticmethod
    def apply_level_up(cstate: CharacterState) -> None:
        """Boost stats for a single level gain based on tongue growth rates."""
        char = cstate.character
        tongue = char.tongue_affinity
        growth = TONGUE_GROWTH_RATES.get(tongue, BASE_GROWTH)

        # Each stat gets: base + tongue-specific bonus, with a small random spread
        def _grow(stat_name: str) -> int:
            base = BASE_GROWTH[stat_name]
            bonus = growth.get(stat_name, 0.0)
            raw = base + bonus + random.uniform(-0.5, 0.5)
            return max(1, int(round(raw)))

        hp_gain = _grow("hp")
        mp_gain = _grow("mp")

        char.stats.max_hp += hp_gain
        char.stats.hp += hp_gain  # Heal the gained amount
        char.stats.max_mp += mp_gain
        char.stats.mp += mp_gain
        char.stats.attack += _grow("attack")
        char.stats.defense += _grow("defense")
        char.stats.speed += _grow("speed")
        char.stats.wisdom += _grow("wisdom")

        # Slight tongue proficiency bump on level up (primary tongue)
        key = tongue.value
        current = char.stats.tongue_prof.get(key, 0.0)
        char.stats.tongue_prof[key] = min(1.0, current + 0.015)


# ---------------------------------------------------------------------------
# EvolutionManager
# ---------------------------------------------------------------------------
class EvolutionManager:
    """Checks and applies Digimon-style evolution for characters."""

    @staticmethod
    def _next_stage(current: EvoStage) -> Optional[EvoStage]:
        """Return the next evolution stage, or None if at max."""
        idx = _EVO_ORDER.index(current)
        if idx + 1 < len(_EVO_ORDER):
            return _EVO_ORDER[idx + 1]
        return None

    @staticmethod
    def check_evolution(cstate: CharacterState) -> Optional[EvoStage]:
        """Check if the character can evolve.  Returns the target stage or None.

        Requirements:
          Fresh -> Rookie:     level >= 5
          Rookie -> Champion:  level >= 15, primary tongue prof >= 0.3
          Champion -> Ultimate: level >= 25, primary >= 0.6, any secondary >= 0.2
          Ultimate -> Mega:    level >= 35, primary >= 0.8, bosses_defeated >= 1
          Mega -> Ultra:       level >= 45, ALL tongues >= 0.3, quests_completed >= 1
        """
        char = cstate.character
        stage = char.evo_stage
        next_stage = EvolutionManager._next_stage(stage)
        if next_stage is None:
            return None

        primary_key = char.tongue_affinity.value
        primary_prof = char.stats.tongue_prof.get(primary_key, 0.0)

        if stage == EvoStage.FRESH:
            if cstate.level >= 5:
                return next_stage

        elif stage == EvoStage.ROOKIE:
            if cstate.level >= 15 and primary_prof >= 0.3:
                return next_stage

        elif stage == EvoStage.CHAMPION:
            if cstate.level >= 25 and primary_prof >= 0.6:
                # Need at least one secondary tongue >= 0.2
                for key, val in char.stats.tongue_prof.items():
                    if key != primary_key and val >= 0.2:
                        return next_stage

        elif stage == EvoStage.ULTIMATE:
            if cstate.level >= 35 and primary_prof >= 0.8 and cstate.bosses_defeated >= 1:
                return next_stage

        elif stage == EvoStage.MEGA:
            if cstate.level >= 45 and cstate.quests_completed >= 1:
                all_above = all(v >= 0.3 for v in char.stats.tongue_prof.values())
                if all_above:
                    return next_stage

        return None

    @staticmethod
    def apply_evolution(cstate: CharacterState, new_stage: EvoStage) -> List[str]:
        """Evolve the character to *new_stage*.

        - Applies stat multiplier (ratio between new and old stage multipliers).
        - Learns the evolution bonus move for the character's tongue.
        - Returns list of event strings.
        """
        char = cstate.character
        old_stage = char.evo_stage
        old_mult = EVOLUTION_STAT_MULTIPLIERS.get(old_stage, 1.0)
        new_mult = EVOLUTION_STAT_MULTIPLIERS.get(new_stage, 1.0)
        ratio = new_mult / old_mult if old_mult > 0 else new_mult

        events: List[str] = []

        # Boost all stats by the ratio
        char.stats.max_hp = int(char.stats.max_hp * ratio)
        char.stats.hp = char.stats.max_hp  # Full heal on evolution
        char.stats.max_mp = int(char.stats.max_mp * ratio)
        char.stats.mp = char.stats.max_mp
        char.stats.attack = int(char.stats.attack * ratio)
        char.stats.defense = int(char.stats.defense * ratio)
        char.stats.speed = int(char.stats.speed * ratio)
        char.stats.wisdom = int(char.stats.wisdom * ratio)

        char.evo_stage = new_stage
        events.append(f"{char.name} evolved into {new_stage.value}!")

        # Learn bonus move
        bonus_table = EVOLUTION_BONUS_MOVES.get(new_stage, {})
        bonus_spell = bonus_table.get(char.tongue_affinity)
        if bonus_spell:
            existing_names = {s.name for s in char.spells}
            if bonus_spell.name not in existing_names:
                char.spells.append(bonus_spell)
                events.append(f"Learned {bonus_spell.name}!")

        return events


# ---------------------------------------------------------------------------
# PartyManager
# ---------------------------------------------------------------------------
class PartyManager:
    """Manages 6-slot active party and unlimited storage boxes."""

    def __init__(self) -> None:
        self.party: List[CharacterState] = []
        self.storage: List[CharacterState] = []

    # -- Party operations ----------------------------------------------------

    def add_to_party(self, char: Character, level: int = 1) -> bool:
        """Add a character.  Returns True if added to party, False if sent to storage."""
        cstate = CharacterState(character=char, level=level)
        if len(self.party) < MAX_PARTY:
            self.party.append(cstate)
            return True
        self.storage.append(cstate)
        return False

    def add_cstate(self, cstate: CharacterState) -> bool:
        """Add an existing CharacterState.  Returns True if party, False if storage."""
        if len(self.party) < MAX_PARTY:
            self.party.append(cstate)
            return True
        self.storage.append(cstate)
        return False

    def swap(self, idx_a: int, idx_b: int) -> None:
        """Swap two party positions."""
        if 0 <= idx_a < len(self.party) and 0 <= idx_b < len(self.party):
            self.party[idx_a], self.party[idx_b] = self.party[idx_b], self.party[idx_a]

    def deposit(self, party_idx: int) -> bool:
        """Move a party member to storage.  Fails if party would be empty."""
        if party_idx < 0 or party_idx >= len(self.party):
            return False
        if len(self.party) <= 1:
            return False  # Must keep at least one member
        cstate = self.party.pop(party_idx)
        self.storage.append(cstate)
        return True

    def withdraw(self, storage_idx: int) -> bool:
        """Move from storage to party.  Fails if party is full."""
        if storage_idx < 0 or storage_idx >= len(self.storage):
            return False
        if len(self.party) >= MAX_PARTY:
            return False
        cstate = self.storage.pop(storage_idx)
        self.party.append(cstate)
        return True

    def heal_all(self) -> None:
        """Restore all HP and MP for all party members."""
        for cstate in self.party:
            cstate.character.stats.hp = cstate.character.stats.max_hp
            cstate.character.stats.mp = cstate.character.stats.max_mp

    def get_leader(self) -> Optional[CharacterState]:
        """Return the first alive party member, or None."""
        for cstate in self.party:
            if cstate.character.stats.hp > 0:
                return cstate
        return None

    def party_alive_count(self) -> int:
        """Number of party members with HP > 0."""
        return sum(1 for cs in self.party if cs.character.stats.hp > 0)

    def is_wiped(self) -> bool:
        """True if the entire party is KO'd."""
        return self.party_alive_count() == 0

    @property
    def storage_box_count(self) -> int:
        """How many storage boxes are in use (ceil)."""
        if not self.storage:
            return 1  # Always show at least one box
        return max(1, math.ceil(len(self.storage) / STORAGE_BOX_SIZE))


# ============================================================================
# PYGAME UI COMPONENTS
# ============================================================================
# Everything below requires pygame-ce.  Guarded by the import check at top.

def _ensure_pygame() -> None:
    if pygame is None:
        raise RuntimeError("pygame-ce is required for UI components. pip install pygame-ce")


def _tongue_color(tongue: Tongue) -> Tuple[int, int, int]:
    """Map a Tongue to its palette color."""
    return Palette.TONGUE_COLORS.get(tongue.value, Palette.WHITE)


def _draw_hp_bar(
    surface: pygame.Surface,
    x: int, y: int,
    w: int, h: int,
    current: int, maximum: int,
    bg: Tuple[int, int, int] = (40, 40, 40),
) -> None:
    """Draw an HP bar that changes color by percentage."""
    pygame.draw.rect(surface, bg, (x, y, w, h))
    if maximum <= 0:
        return
    ratio = max(0.0, min(1.0, current / maximum))
    if ratio > 0.5:
        color = Palette.HP_GREEN
    elif ratio > 0.25:
        color = Palette.HP_YELLOW
    else:
        color = Palette.HP_RED
    fill_w = int(w * ratio)
    if fill_w > 0:
        pygame.draw.rect(surface, color, (x, y, fill_w, h))
    pygame.draw.rect(surface, Palette.UI_BORDER, (x, y, w, h), 1)


def _draw_xp_bar(
    surface: pygame.Surface,
    x: int, y: int,
    w: int, h: int,
    progress: float,
) -> None:
    """Draw an XP progress bar."""
    pygame.draw.rect(surface, (20, 20, 40), (x, y, w, h))
    fill_w = int(w * max(0.0, min(1.0, progress)))
    if fill_w > 0:
        pygame.draw.rect(surface, Palette.XP_BLUE, (x, y, fill_w, h))
    pygame.draw.rect(surface, Palette.UI_BORDER, (x, y, w, h), 1)


def _render_text(
    surface: pygame.Surface,
    text: str,
    x: int, y: int,
    font: pygame.font.Font,
    color: Tuple[int, int, int] = Palette.UI_TEXT,
) -> None:
    """Render text onto a surface."""
    rendered = font.render(text, True, color)
    surface.blit(rendered, (x, y))


def _make_mini_sprite(
    cstate: CharacterState, size: int = 32
) -> pygame.Surface:
    """Generate a small pygame surface from the character's sprite data."""
    _ensure_pygame()
    import numpy as np
    arr = generate_sprite(cstate.character, size)
    # numpy RGBA -> pygame surface
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.surfarray.blit_array(surf, arr[:, :, :3].transpose(1, 0, 2))
    # Apply alpha
    alpha_arr = arr[:, :, 3].T
    for yy in range(size):
        for xx in range(size):
            r, g, b, _ = surf.get_at((xx, yy))
            surf.set_at((xx, yy), (r, g, b, int(alpha_arr[xx, yy])))
    return surf


# ---------------------------------------------------------------------------
# PartyScreen
# ---------------------------------------------------------------------------
class PartyScreen:
    """Full-screen party overview -- shows 6 slots like the Pokemon party menu.

    Controls:
      Up/Down  : Navigate slots
      Enter    : Toggle detail panel
      S        : Enter swap mode (select two slots)
      D        : Deposit selected member to storage
      Escape   : Close screen
    """

    SLOT_HEIGHT = 64
    DETAIL_W = 260
    SLOT_W = 360

    def __init__(self, manager: PartyManager) -> None:
        _ensure_pygame()
        self.manager = manager
        self.selected = 0
        self.show_detail = False
        self.swap_mode = False
        self.swap_first: Optional[int] = None
        self.font: Optional[pygame.font.Font] = None
        self.small_font: Optional[pygame.font.Font] = None
        self._sprite_cache: Dict[str, pygame.Surface] = {}

    def _init_fonts(self) -> None:
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.SysFont("consolas", 16)
            self.small_font = pygame.font.SysFont("consolas", 12)

    def _get_sprite(self, cstate: CharacterState) -> pygame.Surface:
        key = cstate.character.name
        if key not in self._sprite_cache:
            self._sprite_cache[key] = _make_mini_sprite(cstate, 32)
        return self._sprite_cache[key]

    def handle_input(self, event: pygame.event.Event) -> Optional[str]:
        """Process a pygame event.  Returns 'close' to exit the screen."""
        if event.type != pygame.KEYDOWN:
            return None

        party_len = len(self.manager.party)

        if event.key == pygame.K_ESCAPE:
            if self.swap_mode:
                self.swap_mode = False
                self.swap_first = None
            elif self.show_detail:
                self.show_detail = False
            else:
                return "close"

        elif event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % max(1, party_len)
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % max(1, party_len)

        elif event.key == pygame.K_RETURN:
            if self.swap_mode:
                if self.swap_first is None:
                    self.swap_first = self.selected
                else:
                    self.manager.swap(self.swap_first, self.selected)
                    self.swap_mode = False
                    self.swap_first = None
            else:
                self.show_detail = not self.show_detail

        elif event.key == pygame.K_s:
            self.swap_mode = not self.swap_mode
            self.swap_first = None

        elif event.key == pygame.K_d:
            if party_len > 1:
                self.manager.deposit(self.selected)
                if self.selected >= len(self.manager.party):
                    self.selected = max(0, len(self.manager.party) - 1)

        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Render the party screen onto *surface* (expected 640x480)."""
        self._init_fonts()
        assert self.font is not None and self.small_font is not None

        surface.fill(Palette.UI_BG)

        # Title bar
        pygame.draw.rect(surface, Palette.BG_AETHER, (0, 0, SCREEN_W, 32))
        title = "SWAP MODE -- Select two slots" if self.swap_mode else "PARTY"
        _render_text(surface, title, 10, 6, self.font, Palette.UI_SELECT if self.swap_mode else Palette.WHITE)

        # Draw slots
        for i in range(MAX_PARTY):
            slot_y = 40 + i * self.SLOT_HEIGHT
            self._draw_slot(surface, i, slot_y)

        # Detail panel (right side)
        if self.show_detail and 0 <= self.selected < len(self.manager.party):
            self._draw_detail(surface, self.manager.party[self.selected])

        # Controls hint
        hint = "[Up/Down] Move  [Enter] Detail  [S] Swap  [D] Deposit  [Esc] Back"
        _render_text(surface, hint, 10, SCREEN_H - 20, self.small_font, Palette.UI_BORDER)

    def _draw_slot(self, surface: pygame.Surface, idx: int, y: int) -> None:
        """Draw a single party slot."""
        assert self.font is not None and self.small_font is not None

        is_selected = (idx == self.selected)
        is_swap_source = (self.swap_mode and self.swap_first == idx)
        border_color = Palette.UI_SELECT if is_selected else Palette.UI_BORDER
        if is_swap_source:
            border_color = (255, 100, 100)

        slot_rect = pygame.Rect(8, y, self.SLOT_W, self.SLOT_HEIGHT - 4)
        pygame.draw.rect(surface, (24, 24, 48), slot_rect)
        pygame.draw.rect(surface, border_color, slot_rect, 2)

        if idx >= len(self.manager.party):
            # Empty slot
            _render_text(surface, f"  Slot {idx + 1}  -- empty --", 50, y + 22, self.font, (80, 80, 100))
            return

        cstate = self.manager.party[idx]
        char = cstate.character

        # Mini sprite
        sprite_surf = self._get_sprite(cstate)
        surface.blit(sprite_surf, (14, y + 16))

        # Tongue color stripe
        tc = _tongue_color(char.tongue_affinity)
        pygame.draw.rect(surface, tc, (48, y + 2, 4, self.SLOT_HEIGHT - 8))

        # Name and level
        name_str = f"{char.name}"
        _render_text(surface, name_str, 58, y + 4, self.font)
        lv_str = f"Lv {cstate.level}"
        _render_text(surface, lv_str, 58, y + 22, self.small_font, Palette.UI_SELECT)

        # Evo stage badge
        badge_str = f"[{char.evo_stage.value}]"
        _render_text(surface, badge_str, 120, y + 22, self.small_font, tc)

        # HP bar
        hp_bar_x = 200
        hp_bar_y = y + 8
        _draw_hp_bar(surface, hp_bar_x, hp_bar_y, 120, 10, char.stats.hp, char.stats.max_hp)
        hp_text = f"HP {char.stats.hp}/{char.stats.max_hp}"
        _render_text(surface, hp_text, hp_bar_x, hp_bar_y + 12, self.small_font)

        # MP display
        mp_text = f"MP {char.stats.mp}/{char.stats.max_mp}"
        _render_text(surface, mp_text, hp_bar_x, hp_bar_y + 26, self.small_font, (120, 140, 220))

        # XP bar
        _draw_xp_bar(surface, hp_bar_x + 130, hp_bar_y, 40, 10, cstate.xp_progress)

    def _draw_detail(self, surface: pygame.Surface, cstate: CharacterState) -> None:
        """Draw the detailed stat panel on the right side."""
        assert self.font is not None and self.small_font is not None
        char = cstate.character

        panel_x = SCREEN_W - self.DETAIL_W - 8
        panel_y = 40
        panel_h = SCREEN_H - 80

        pygame.draw.rect(surface, (20, 16, 36), (panel_x, panel_y, self.DETAIL_W, panel_h))
        pygame.draw.rect(surface, Palette.UI_SELECT, (panel_x, panel_y, self.DETAIL_W, panel_h), 2)

        x = panel_x + 10
        y = panel_y + 8

        # Name + title
        _render_text(surface, char.display_name, x, y, self.font, Palette.WHITE)
        y += 20
        _render_text(surface, char.title, x, y, self.small_font, (180, 180, 200))
        y += 16

        # Level + XP
        _render_text(surface, f"Level: {cstate.level}  XP: {cstate.total_xp}", x, y, self.small_font)
        y += 14
        xp_next = cstate.xp_for_next
        _render_text(surface, f"Next level: {xp_next} XP", x, y, self.small_font, Palette.XP_BLUE)
        y += 20

        # Stats
        stats_list = [
            ("HP",      f"{char.stats.hp}/{char.stats.max_hp}"),
            ("MP",      f"{char.stats.mp}/{char.stats.max_mp}"),
            ("ATK",     str(char.stats.attack)),
            ("DEF",     str(char.stats.defense)),
            ("SPD",     str(char.stats.speed)),
            ("WIS",     str(char.stats.wisdom)),
        ]
        _render_text(surface, "-- Stats --", x, y, self.small_font, Palette.UI_SELECT)
        y += 14
        for label, val in stats_list:
            _render_text(surface, f"  {label:4s} {val}", x, y, self.small_font)
            y += 14
        y += 6

        # Tongue proficiencies
        _render_text(surface, "-- Tongues --", x, y, self.small_font, Palette.UI_SELECT)
        y += 14
        for t in Tongue:
            prof = char.stats.tongue_prof.get(t.value, 0.0)
            tc = _tongue_color(t)
            bar_w = int(100 * prof)
            _render_text(surface, f"  {t.value}", x, y, self.small_font, tc)
            pygame.draw.rect(surface, (40, 40, 40), (x + 40, y + 2, 100, 8))
            if bar_w > 0:
                pygame.draw.rect(surface, tc, (x + 40, y + 2, bar_w, 8))
            prof_str = f"{prof:.0%}"
            _render_text(surface, prof_str, x + 148, y, self.small_font, tc)
            y += 14
        y += 6

        # Moves
        _render_text(surface, "-- Moves --", x, y, self.small_font, Palette.UI_SELECT)
        y += 14
        for spell in char.spells[:8]:  # Show up to 8
            tc = _tongue_color(spell.tongue)
            move_str = f"  {spell.name} ({spell.tongue.value}) Pw:{spell.power} Mp:{spell.mp_cost}"
            _render_text(surface, move_str, x, y, self.small_font, tc)
            y += 12
            if y > panel_y + panel_h - 20:
                _render_text(surface, "  ...", x, y, self.small_font, Palette.UI_BORDER)
                break


# ---------------------------------------------------------------------------
# EvolutionAnimation
# ---------------------------------------------------------------------------
class EvolutionAnimation:
    """Plays a Digimon-style evolution cutscene.

    Phases:
      0. Fade-in + old sprite displayed           (0.0 - 0.5s)
      1. Screen flashes white                      (0.5 - 1.0s)
      2. Old sprite pulses and grows               (1.0 - 2.5s)
      3. Particle burst in tongue color            (2.5 - 3.5s)
      4. New sprite appears (bigger, brighter)     (3.5 - 4.5s)
      5. Text: "X evolved into Y!"                 (4.5 - 6.0s)
      6. Done

    Usage:
      anim = EvolutionAnimation(cstate, EvoStage.CHAMPION)
      while not done:
          done = anim.update(dt)
          anim.draw(screen)
    """

    TOTAL_DURATION = 6.0
    PHASE_TIMES = [0.0, 0.5, 1.0, 2.5, 3.5, 4.5, 6.0]

    def __init__(self, cstate: CharacterState, new_stage: EvoStage) -> None:
        _ensure_pygame()
        self.cstate = cstate
        self.char = cstate.character
        self.old_stage = cstate.character.evo_stage
        self.new_stage = new_stage
        self.elapsed = 0.0
        self.done = False
        self.font: Optional[pygame.font.Font] = None
        self.big_font: Optional[pygame.font.Font] = None

        # Particle system
        self.particles: List[Dict[str, Any]] = []
        self._particles_spawned = False

        # Cache sprites
        self._old_sprite: Optional[pygame.Surface] = None
        self._new_sprite: Optional[pygame.Surface] = None

    def _init_fonts(self) -> None:
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.SysFont("consolas", 16)
            self.big_font = pygame.font.SysFont("consolas", 24)

    def _get_old_sprite(self) -> pygame.Surface:
        if self._old_sprite is None:
            self._old_sprite = _make_mini_sprite(self.cstate, 48)
        return self._old_sprite

    def _get_new_sprite(self) -> pygame.Surface:
        if self._new_sprite is None:
            self._new_sprite = _make_mini_sprite(self.cstate, 64)
        return self._new_sprite

    def _phase(self) -> int:
        """Return current phase index (0-6)."""
        for i in range(len(self.PHASE_TIMES) - 1):
            if self.elapsed < self.PHASE_TIMES[i + 1]:
                return i
        return len(self.PHASE_TIMES) - 1

    def _spawn_particles(self) -> None:
        """Create burst particles in tongue color."""
        if self._particles_spawned:
            return
        self._particles_spawned = True
        tc = _tongue_color(self.char.tongue_affinity)
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        for _ in range(60):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 200)
            self.particles.append({
                "x": float(cx),
                "y": float(cy),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": random.uniform(0.5, 1.5),
                "color": (
                    min(255, tc[0] + random.randint(-30, 30)),
                    min(255, tc[1] + random.randint(-30, 30)),
                    min(255, tc[2] + random.randint(-30, 30)),
                ),
                "size": random.randint(2, 6),
            })

    def update(self, dt: float) -> bool:
        """Advance the animation.  Returns True when complete."""
        self.elapsed += dt
        if self.elapsed >= self.TOTAL_DURATION:
            self.done = True
            return True

        # Update particles
        alive: List[Dict[str, Any]] = []
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
            p["vy"] += 60 * dt  # gravity
            if p["life"] > 0:
                alive.append(p)
        self.particles = alive

        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Render the current animation frame."""
        _ensure_pygame()
        self._init_fonts()
        assert self.font is not None and self.big_font is not None

        phase = self._phase()
        cx, cy = SCREEN_W // 2, SCREEN_H // 2

        # Background
        surface.fill(Palette.BG_AETHER)

        # Phase 0: Fade in with old sprite
        if phase == 0:
            alpha = min(255, int(255 * (self.elapsed / 0.5)))
            old_spr = self._get_old_sprite()
            old_spr.set_alpha(alpha)
            surface.blit(old_spr, (cx - 24, cy - 24))

        # Phase 1: White flash
        elif phase == 1:
            flash_progress = (self.elapsed - 0.5) / 0.5
            flash_alpha = int(255 * (1.0 - abs(flash_progress - 0.5) * 2))
            flash_surf = pygame.Surface((SCREEN_W, SCREEN_H))
            flash_surf.fill(Palette.WHITE)
            flash_surf.set_alpha(flash_alpha)
            surface.blit(self._get_old_sprite(), (cx - 24, cy - 24))
            surface.blit(flash_surf, (0, 0))

        # Phase 2: Pulse and grow
        elif phase == 2:
            progress = (self.elapsed - 1.0) / 1.5
            pulse = 1.0 + 0.3 * math.sin(progress * math.pi * 6)
            size = int(48 * pulse)
            old_spr = self._get_old_sprite()
            scaled = pygame.transform.scale(old_spr, (size, size))
            surface.blit(scaled, (cx - size // 2, cy - size // 2))
            # Glow ring
            tc = _tongue_color(self.char.tongue_affinity)
            ring_radius = int(30 + 20 * progress)
            ring_alpha = int(180 * (1.0 - progress))
            glow_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*tc, ring_alpha), (cx, cy), ring_radius, 3)
            surface.blit(glow_surf, (0, 0))

        # Phase 3: Particle burst
        elif phase == 3:
            self._spawn_particles()
            # Draw particles
            for p in self.particles:
                alpha = max(0, min(255, int(255 * (p["life"] / 1.5))))
                part_surf = pygame.Surface((p["size"], p["size"]), pygame.SRCALPHA)
                part_surf.fill((*p["color"], alpha))
                surface.blit(part_surf, (int(p["x"]), int(p["y"])))

        # Phase 4: New sprite
        elif phase == 4:
            progress = (self.elapsed - 3.5) / 1.0
            alpha = min(255, int(255 * progress))
            new_spr = self._get_new_sprite()
            new_spr.set_alpha(alpha)
            surface.blit(new_spr, (cx - 32, cy - 32))
            # Bright halo
            tc = _tongue_color(self.char.tongue_affinity)
            halo_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            halo_alpha = int(120 * (1.0 - progress))
            pygame.draw.circle(halo_surf, (*tc, halo_alpha), (cx, cy), 50, 4)
            surface.blit(halo_surf, (0, 0))

        # Phase 5: Text announcement
        elif phase >= 5:
            new_spr = self._get_new_sprite()
            surface.blit(new_spr, (cx - 32, cy - 48))
            text = f"{self.char.name} evolved into {self.new_stage.value}!"
            rendered = self.big_font.render(text, True, Palette.UI_SELECT)
            text_rect = rendered.get_rect(center=(cx, cy + 48))
            surface.blit(rendered, text_rect)
            # Tongue name subtitle
            tongue_name = TONGUE_NAMES.get(self.char.tongue_affinity, "")
            sub = self.font.render(f"Tongue of {tongue_name}", True, _tongue_color(self.char.tongue_affinity))
            sub_rect = sub.get_rect(center=(cx, cy + 72))
            surface.blit(sub, sub_rect)

        # Draw lingering particles on top (phases 3-5)
        if phase >= 3:
            for p in self.particles:
                alpha = max(0, min(255, int(255 * (p["life"] / 1.5))))
                if alpha > 10:
                    part_surf = pygame.Surface((p["size"], p["size"]), pygame.SRCALPHA)
                    part_surf.fill((*p["color"], alpha))
                    surface.blit(part_surf, (int(p["x"]), int(p["y"])))


# ---------------------------------------------------------------------------
# StorageScreen
# ---------------------------------------------------------------------------
class StorageScreen:
    """PC-box style storage grid (5 columns x 6 rows = 30 per box).

    Controls:
      Arrow keys : Navigate grid
      Enter      : Withdraw selected creature to party
      Tab        : Next/Previous box
      Escape     : Close
    """

    CELL_SIZE = 64
    GRID_X_OFFSET = 40
    GRID_Y_OFFSET = 60
    INFO_X = 380
    INFO_Y = 60

    def __init__(self, manager: PartyManager) -> None:
        _ensure_pygame()
        self.manager = manager
        self.current_box = 0
        self.cursor_col = 0
        self.cursor_row = 0
        self.font: Optional[pygame.font.Font] = None
        self.small_font: Optional[pygame.font.Font] = None
        self._sprite_cache: Dict[str, pygame.Surface] = {}

    def _init_fonts(self) -> None:
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.SysFont("consolas", 16)
            self.small_font = pygame.font.SysFont("consolas", 12)

    @property
    def _box_start(self) -> int:
        return self.current_box * STORAGE_BOX_SIZE

    @property
    def _box_items(self) -> List[CharacterState]:
        start = self._box_start
        end = start + STORAGE_BOX_SIZE
        return self.manager.storage[start:end]

    @property
    def _cursor_index(self) -> int:
        """Index within the current box."""
        return self.cursor_row * STORAGE_BOX_COLS + self.cursor_col

    @property
    def _storage_index(self) -> int:
        """Absolute index into manager.storage."""
        return self._box_start + self._cursor_index

    def _get_sprite(self, cstate: CharacterState) -> pygame.Surface:
        key = cstate.character.name
        if key not in self._sprite_cache:
            self._sprite_cache[key] = _make_mini_sprite(cstate, 24)
        return self._sprite_cache[key]

    def handle_input(self, event: pygame.event.Event) -> Optional[str]:
        """Process input.  Returns 'close' to exit."""
        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_ESCAPE:
            return "close"

        elif event.key == pygame.K_LEFT:
            self.cursor_col = (self.cursor_col - 1) % STORAGE_BOX_COLS
        elif event.key == pygame.K_RIGHT:
            self.cursor_col = (self.cursor_col + 1) % STORAGE_BOX_COLS
        elif event.key == pygame.K_UP:
            self.cursor_row = (self.cursor_row - 1) % STORAGE_BOX_ROWS
        elif event.key == pygame.K_DOWN:
            self.cursor_row = (self.cursor_row + 1) % STORAGE_BOX_ROWS

        elif event.key == pygame.K_TAB:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                self.current_box = max(0, self.current_box - 1)
            else:
                max_box = self.manager.storage_box_count - 1
                self.current_box = min(max_box, self.current_box + 1)
            self.cursor_col = 0
            self.cursor_row = 0

        elif event.key == pygame.K_RETURN:
            idx = self._storage_index
            if 0 <= idx < len(self.manager.storage):
                self.manager.withdraw(idx)

        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Render the storage screen."""
        self._init_fonts()
        assert self.font is not None and self.small_font is not None

        surface.fill(Palette.UI_BG)

        # Title
        box_label = f"BOX {self.current_box + 1} / {self.manager.storage_box_count}"
        pygame.draw.rect(surface, Palette.BG_AETHER, (0, 0, SCREEN_W, 40))
        _render_text(surface, f"STORAGE  {box_label}", 10, 10, self.font, Palette.WHITE)
        _render_text(
            surface,
            f"Total stored: {len(self.manager.storage)}",
            SCREEN_W - 200, 10, self.small_font, Palette.UI_BORDER,
        )

        # Grid
        items = self._box_items
        for row in range(STORAGE_BOX_ROWS):
            for col in range(STORAGE_BOX_COLS):
                idx = row * STORAGE_BOX_COLS + col
                x = self.GRID_X_OFFSET + col * self.CELL_SIZE
                y = self.GRID_Y_OFFSET + row * self.CELL_SIZE
                cell_rect = pygame.Rect(x, y, self.CELL_SIZE - 4, self.CELL_SIZE - 4)

                is_cursor = (row == self.cursor_row and col == self.cursor_col)
                border = Palette.UI_SELECT if is_cursor else Palette.UI_BORDER

                pygame.draw.rect(surface, (24, 24, 48), cell_rect)
                pygame.draw.rect(surface, border, cell_rect, 2 if is_cursor else 1)

                if idx < len(items):
                    cstate = items[idx]
                    tc = _tongue_color(cstate.character.tongue_affinity)

                    # Mini creature icon: colored dot with tongue border
                    dot_cx = x + self.CELL_SIZE // 2 - 2
                    dot_cy = y + 18
                    pygame.draw.circle(surface, tc, (dot_cx, dot_cy), 10, 2)
                    # Inner dot in a lighter shade
                    inner = (min(255, tc[0] + 60), min(255, tc[1] + 60), min(255, tc[2] + 60))
                    pygame.draw.circle(surface, inner, (dot_cx, dot_cy), 6)

                    # Name (truncated)
                    name = cstate.character.name[:6]
                    _render_text(surface, name, x + 4, y + 36, self.small_font, Palette.UI_TEXT)

                    # Level
                    lv_str = f"Lv{cstate.level}"
                    _render_text(surface, lv_str, x + 4, y + 48, self.small_font, Palette.UI_BORDER)

        # Info panel for cursor selection
        abs_idx = self._cursor_index
        if abs_idx < len(items):
            self._draw_info_panel(surface, items[abs_idx])

        # Party count display
        party_text = f"Party: {len(self.manager.party)}/{MAX_PARTY}"
        _render_text(surface, party_text, self.INFO_X, SCREEN_H - 50, self.font, Palette.UI_TEXT)

        # Controls hint
        hint = "[Arrows] Move  [Enter] Withdraw  [Tab] Box  [Esc] Back"
        _render_text(surface, hint, 10, SCREEN_H - 20, self.small_font, Palette.UI_BORDER)

    def _draw_info_panel(self, surface: pygame.Surface, cstate: CharacterState) -> None:
        """Draw creature info on the right side."""
        assert self.font is not None and self.small_font is not None
        char = cstate.character

        x = self.INFO_X
        y = self.INFO_Y
        panel_w = SCREEN_W - self.INFO_X - 10
        panel_h = 340

        pygame.draw.rect(surface, (20, 16, 36), (x, y, panel_w, panel_h))
        pygame.draw.rect(surface, Palette.UI_BORDER, (x, y, panel_w, panel_h), 1)

        ix = x + 8
        iy = y + 8

        # Sprite
        sprite = self._get_sprite(cstate)
        surface.blit(sprite, (ix, iy))
        iy += 30

        # Name
        _render_text(surface, char.display_name, ix, iy, self.font, Palette.WHITE)
        iy += 18
        _render_text(surface, char.title, ix, iy, self.small_font, (180, 180, 200))
        iy += 16
        _render_text(surface, f"Level {cstate.level}", ix, iy, self.small_font, Palette.UI_SELECT)
        iy += 18

        # HP/MP bars
        _draw_hp_bar(surface, ix, iy, 140, 10, char.stats.hp, char.stats.max_hp)
        _render_text(surface, f"HP {char.stats.hp}/{char.stats.max_hp}", ix + 148, iy, self.small_font)
        iy += 16
        pygame.draw.rect(surface, (20, 20, 50), (ix, iy, 140, 10))
        mp_ratio = char.stats.mp / max(1, char.stats.max_mp)
        mp_fill = int(140 * mp_ratio)
        if mp_fill > 0:
            pygame.draw.rect(surface, (60, 100, 200), (ix, iy, mp_fill, 10))
        pygame.draw.rect(surface, Palette.UI_BORDER, (ix, iy, 140, 10), 1)
        _render_text(surface, f"MP {char.stats.mp}/{char.stats.max_mp}", ix + 148, iy, self.small_font, (120, 140, 220))
        iy += 18

        # Stats
        for label, val in [("ATK", char.stats.attack), ("DEF", char.stats.defense),
                           ("SPD", char.stats.speed), ("WIS", char.stats.wisdom)]:
            _render_text(surface, f"{label}: {val}", ix, iy, self.small_font)
            iy += 14

        iy += 6
        # Tongue proficiencies (compact)
        for t in Tongue:
            prof = char.stats.tongue_prof.get(t.value, 0.0)
            tc = _tongue_color(t)
            bar_w = int(80 * prof)
            _render_text(surface, t.value, ix, iy, self.small_font, tc)
            pygame.draw.rect(surface, (40, 40, 40), (ix + 30, iy + 2, 80, 6))
            if bar_w > 0:
                pygame.draw.rect(surface, tc, (ix + 30, iy + 2, bar_w, 6))
            iy += 12

        # Withdraw hint
        if len(self.manager.party) < MAX_PARTY:
            _render_text(surface, "Press Enter to withdraw", ix, iy + 8, self.small_font, Palette.HP_GREEN)
        else:
            _render_text(surface, "Party is full!", ix, iy + 8, self.small_font, Palette.HP_RED)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def selftest() -> None:
    """Validate all party subsystems without pygame."""
    print(f"\n{'=' * 60}")
    print("  Party System -- Self-Test")
    print(f"{'=' * 60}\n")

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}  {detail}")

    # -- Level thresholds --
    check("Level thresholds count", len(LEVEL_THRESHOLDS) == MAX_LEVEL,
          f"Got {len(LEVEL_THRESHOLDS)}")
    check("Level 1 = 0 XP", LEVEL_THRESHOLDS[0] == 0)
    check("Monotonically increasing",
          all(LEVEL_THRESHOLDS[i] < LEVEL_THRESHOLDS[i + 1] for i in range(MAX_LEVEL - 1)))
    check("Level 50 XP is large", LEVEL_THRESHOLDS[-1] > 50000,
          f"Got {LEVEL_THRESHOLDS[-1]}")
    print(f"  INFO  XP curve sample: L5={LEVEL_THRESHOLDS[4]}, L15={LEVEL_THRESHOLDS[14]}, "
          f"L25={LEVEL_THRESHOLDS[24]}, L35={LEVEL_THRESHOLDS[34]}, L50={LEVEL_THRESHOLDS[49]}")

    # -- Learnable moves --
    for tongue in Tongue:
        moves = LEARNABLE_MOVES.get(tongue, [])
        check(f"Tongue {tongue.value} has >= 6 moves", len(moves) >= 6, f"Got {len(moves)}")
        levels = [lv for lv, _ in moves]
        check(f"Tongue {tongue.value} moves sorted", levels == sorted(levels))

    # -- Evolution multipliers --
    for stage in _EVO_ORDER:
        check(f"Evo mult {stage.value}", stage in EVOLUTION_STAT_MULTIPLIERS)
    check("Ultra > Mega", EVOLUTION_STAT_MULTIPLIERS[EvoStage.ULTRA] > EVOLUTION_STAT_MULTIPLIERS[EvoStage.MEGA])

    # -- PartyManager --
    from engine import create_cast
    cast = create_cast()

    mgr = PartyManager()
    for key in ["izack", "polly", "clay", "eldrin", "aria", "zara"]:
        result = mgr.add_to_party(cast[key])
        check(f"Add {key} to party", result is True)

    check("Party full (6)", len(mgr.party) == 6)

    overflow = mgr.add_to_party(cast["kael"])
    check("Overflow to storage", overflow is False)
    check("Storage has 1", len(mgr.storage) == 1)

    mgr.swap(0, 5)
    check("Swap: leader is now Zara", "Zara" in mgr.party[0].character.name)

    mgr.deposit(5)
    check("Deposit: party = 5", len(mgr.party) == 5)
    check("Deposit: storage = 2", len(mgr.storage) == 2)

    mgr.withdraw(0)
    check("Withdraw: party = 6", len(mgr.party) == 6)
    check("Withdraw: storage = 1", len(mgr.storage) == 1)

    leader = mgr.get_leader()
    check("Leader alive", leader is not None and leader.character.stats.hp > 0)

    mgr.party[0].character.stats.hp = 0
    leader2 = mgr.get_leader()
    check("Leader skip dead", leader2 is not None and leader2.character.stats.hp > 0)

    mgr.heal_all()
    check("Heal all restores HP", mgr.party[0].character.stats.hp == mgr.party[0].character.stats.max_hp)

    # -- LevelUpSystem --
    cstate = CharacterState(character=cast["izack"], level=1, xp=0, total_xp=0)
    old_hp = cstate.character.stats.max_hp
    events = LevelUpSystem.check_level_up(cstate, LEVEL_THRESHOLDS[4] + 10)  # enough for level 5
    check("Level up to >= 5", cstate.level >= 5, f"Level: {cstate.level}")
    check("Level up events", len(events) > 0, f"Events: {events}")
    check("HP increased", cstate.character.stats.max_hp > old_hp,
          f"Old: {old_hp}, New: {cstate.character.stats.max_hp}")
    has_level_event = any("Level" in e for e in events)
    check("Level event present", has_level_event)

    # -- EvolutionManager --
    # Fresh -> Rookie at level 5
    fresh_char = Character(
        name="TestFresh", title="Test", tongue_affinity=Tongue.CA,
        evo_stage=EvoStage.FRESH,
        stats=Stats(hp=50, max_hp=50, mp=30, max_mp=30, attack=5, defense=5, speed=5, wisdom=5),
    )
    fresh_cs = CharacterState(character=fresh_char, level=5)
    evo_mgr = EvolutionManager()
    target = evo_mgr.check_evolution(fresh_cs)
    check("Fresh -> Rookie at lv5", target == EvoStage.ROOKIE)

    evo_events = evo_mgr.apply_evolution(fresh_cs, EvoStage.ROOKIE)
    check("Evolution applied", fresh_char.evo_stage == EvoStage.ROOKIE)
    check("Evolution events", len(evo_events) > 0)
    check("Stats boosted", fresh_char.stats.max_hp > 50,
          f"HP: {fresh_char.stats.max_hp}")

    # Rookie -> Champion requires level 15 + prof 0.3
    fresh_char.stats.tongue_prof["CA"] = 0.35
    fresh_cs.level = 15
    target2 = evo_mgr.check_evolution(fresh_cs)
    check("Rookie -> Champion at lv15 + prof", target2 == EvoStage.CHAMPION)

    # Champion -> Ultimate requires secondary tongue
    evo_mgr.apply_evolution(fresh_cs, EvoStage.CHAMPION)
    fresh_cs.level = 25
    fresh_char.stats.tongue_prof["CA"] = 0.65
    target3_no = evo_mgr.check_evolution(fresh_cs)
    check("Champion no evo without secondary", target3_no is None)
    fresh_char.stats.tongue_prof["KO"] = 0.25
    target3_yes = evo_mgr.check_evolution(fresh_cs)
    check("Champion -> Ultimate with secondary", target3_yes == EvoStage.ULTIMATE)

    # Ultimate -> Mega requires boss kill
    evo_mgr.apply_evolution(fresh_cs, EvoStage.ULTIMATE)
    fresh_cs.level = 35
    fresh_char.stats.tongue_prof["CA"] = 0.85
    target4_no = evo_mgr.check_evolution(fresh_cs)
    check("Ultimate no evo without boss", target4_no is None)
    fresh_cs.bosses_defeated = 1
    target4_yes = evo_mgr.check_evolution(fresh_cs)
    check("Ultimate -> Mega with boss kill", target4_yes == EvoStage.MEGA)

    # Mega -> Ultra requires all tongues + quest
    evo_mgr.apply_evolution(fresh_cs, EvoStage.MEGA)
    fresh_cs.level = 45
    for t in Tongue:
        fresh_char.stats.tongue_prof[t.value] = 0.35
    target5_no = evo_mgr.check_evolution(fresh_cs)
    check("Mega no evo without quest", target5_no is None)
    fresh_cs.quests_completed = 1
    target5_yes = evo_mgr.check_evolution(fresh_cs)
    check("Mega -> Ultra with quest", target5_yes == EvoStage.ULTRA)

    # Ultra is max
    evo_mgr.apply_evolution(fresh_cs, EvoStage.ULTRA)
    target6 = evo_mgr.check_evolution(fresh_cs)
    check("Ultra is max stage", target6 is None)

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}\n")

    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    selftest()
