#!/usr/bin/env python3
"""
Aethermoor Battle System — Pokemon-Style Battle Renderer & Engine
=================================================================
A complete, self-contained battle module for the Six Tongues Protocol RPG.

Provides:
  - BattleState enum for the battle FSM
  - BattleRenderer for drawing the full Pokemon-style battle screen
  - BattleEngine for turn-based combat logic with tongue effectiveness
  - WildEncounter dataclass and random encounter generator
  - Catch system, XP/level-up, move learning, animations

Target surface: 640x480 (the GBA area of the main game window).
Uses only pygame-ce drawing primitives — no external images required.

Imports Character, Stats, Spell, Tongue, TONGUE_CHART, EvoStage,
Palette, and calculate_damage from the companion engine.py.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

import pygame

# ---------------------------------------------------------------------------
# Engine imports (same directory)
# ---------------------------------------------------------------------------
from engine import (
    Character,
    EvoStage,
    Palette,
    Spell,
    Stats,
    Tongue,
    TONGUE_CHART,
    TONGUE_NAMES,
    TONGUE_WEIGHTS,
    calculate_damage,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GAME_W: int = 640
GAME_H: int = 480
PHI: float = (1 + math.sqrt(5)) / 2

# Color aliases
_WHITE: Tuple[int, int, int] = (255, 255, 255)
_BLACK: Tuple[int, int, int] = (0, 0, 0)
_CREAM: Tuple[int, int, int] = (248, 248, 240)
_INK: Tuple[int, int, int] = (32, 32, 40)
_DARK_INK: Tuple[int, int, int] = (40, 40, 48)
_MID_GREY: Tuple[int, int, int] = (96, 96, 112)
_GOLD: Tuple[int, int, int] = (255, 215, 80)
_SHADOW: Tuple[int, int, int] = (24, 24, 32)

# Tongue color map (mirrors Palette but as plain tuples for direct use)
TONGUE_COLORS: Dict[str, Tuple[int, int, int]] = {
    "KO": (220, 60, 60),
    "AV": (60, 180, 220),
    "RU": (220, 180, 60),
    "CA": (60, 220, 120),
    "UM": (140, 60, 220),
    "DR": (220, 120, 60),
}

# Tongue short labels for UI
TONGUE_LABELS: Dict[str, str] = {
    "KO": "Authority",
    "AV": "Transport",
    "RU": "Policy",
    "CA": "Compute",
    "UM": "Security",
    "DR": "Schema",
}

# HP bar color thresholds
HP_GREEN: Tuple[int, int, int] = (80, 200, 72)
HP_YELLOW: Tuple[int, int, int] = (248, 184, 24)
HP_RED: Tuple[int, int, int] = (240, 64, 56)
HP_BG: Tuple[int, int, int] = (56, 56, 64)
XP_BLUE: Tuple[int, int, int] = (72, 136, 248)
XP_BG: Tuple[int, int, int] = (56, 56, 80)

# Timing constants (seconds)
TYPEWRITER_SPEED: float = 0.03          # per character
HP_DRAIN_SPEED: float = 120.0           # hp units per second
CATCH_BALL_DURATION: float = 2.0        # total catch animation
DAMAGE_POPUP_DURATION: float = 1.2      # damage number float time
INTRO_DURATION: float = 1.5
ENEMY_THINK_DELAY: float = 0.8
RESULT_HOLD: float = 1.0
XP_FILL_SPEED: float = 0.6             # fraction of bar per second


# ---------------------------------------------------------------------------
# Battle States
# ---------------------------------------------------------------------------
class BattleState(Enum):
    """Finite state machine for the battle flow."""
    INTRO = auto()
    PLAYER_TURN = auto()
    MOVE_SELECT = auto()
    ENEMY_TURN = auto()
    ANIMATION = auto()
    RESULT = auto()
    CATCH_ATTEMPT = auto()
    RUN = auto()
    VICTORY = auto()
    DEFEAT = auto()


# ---------------------------------------------------------------------------
# Action Menu Options
# ---------------------------------------------------------------------------
class MenuOption(Enum):
    FIGHT = "FIGHT"
    CATCH = "CATCH"
    ITEM = "ITEM"
    RUN = "RUN"


MENU_OPTIONS: List[MenuOption] = [
    MenuOption.FIGHT, MenuOption.CATCH,
    MenuOption.ITEM, MenuOption.RUN,
]


# ---------------------------------------------------------------------------
# Animation / Effect Data
# ---------------------------------------------------------------------------
@dataclass
class DamagePopup:
    """Floating damage number."""
    x: float
    y: float
    value: int
    is_crit: bool
    is_heal: bool
    color: Tuple[int, int, int]
    start_time: float
    duration: float = DAMAGE_POPUP_DURATION

    @property
    def alive(self) -> bool:
        return (time.time() - self.start_time) < self.duration

    @property
    def progress(self) -> float:
        return min(1.0, (time.time() - self.start_time) / self.duration)


@dataclass
class TypewriterText:
    """Typewriter effect for the text box."""
    full_text: str
    start_time: float
    speed: float = TYPEWRITER_SPEED

    @property
    def visible_chars(self) -> int:
        elapsed = time.time() - self.start_time
        return min(len(self.full_text), int(elapsed / self.speed))

    @property
    def current_text(self) -> str:
        return self.full_text[:self.visible_chars]

    @property
    def finished(self) -> bool:
        return self.visible_chars >= len(self.full_text)

    def skip(self) -> None:
        """Instantly finish the typewriter effect."""
        self.start_time = 0.0  # make elapsed huge


@dataclass
class CatchAnimation:
    """Ball-bounce catch animation state."""
    start_time: float
    success: bool
    target_x: float
    target_y: float
    duration: float = CATCH_BALL_DURATION

    @property
    def progress(self) -> float:
        return min(1.0, (time.time() - self.start_time) / self.duration)

    @property
    def finished(self) -> bool:
        return self.progress >= 1.0

    @property
    def ball_y(self) -> float:
        """Ball y-position with 3 bounces."""
        t = self.progress
        if t < 0.3:
            # Arc from bottom to enemy
            p = t / 0.3
            return self.target_y + 200 * (1 - p) - 80 * math.sin(p * math.pi)
        elif t < 0.5:
            # First bounce
            p = (t - 0.3) / 0.2
            return self.target_y - 30 * math.sin(p * math.pi)
        elif t < 0.65:
            # Second bounce
            p = (t - 0.5) / 0.15
            return self.target_y - 18 * math.sin(p * math.pi)
        elif t < 0.75:
            # Third bounce (small)
            p = (t - 0.65) / 0.1
            return self.target_y - 8 * math.sin(p * math.pi)
        else:
            return self.target_y

    @property
    def ball_x(self) -> float:
        t = self.progress
        start_x = 120.0
        if t < 0.3:
            p = t / 0.3
            return start_x + (self.target_x - start_x) * p
        return self.target_x


@dataclass
class HPDrainAnimation:
    """Smooth HP bar drain."""
    display_hp: float
    target_hp: float
    max_hp: float
    speed: float = HP_DRAIN_SPEED

    @property
    def finished(self) -> bool:
        return abs(self.display_hp - self.target_hp) < 0.5

    def update(self, dt: float) -> None:
        if self.display_hp > self.target_hp:
            self.display_hp = max(self.target_hp, self.display_hp - self.speed * dt)
        elif self.display_hp < self.target_hp:
            self.display_hp = min(self.target_hp, self.display_hp + self.speed * dt)

    @property
    def ratio(self) -> float:
        return self.display_hp / self.max_hp if self.max_hp > 0 else 0.0


@dataclass
class XPFillAnimation:
    """XP bar fill animation for victory screen."""
    display_ratio: float = 0.0
    target_ratio: float = 0.0
    speed: float = XP_FILL_SPEED
    level_ups: int = 0

    @property
    def finished(self) -> bool:
        return abs(self.display_ratio - self.target_ratio) < 0.005

    def update(self, dt: float) -> None:
        if self.display_ratio < self.target_ratio:
            self.display_ratio = min(
                self.target_ratio,
                self.display_ratio + self.speed * dt,
            )


# ---------------------------------------------------------------------------
# Wild Encounter
# ---------------------------------------------------------------------------
@dataclass
class WildEncounter:
    """A wild enemy encounter with metadata."""
    enemy: Character
    catch_rate: float       # 0.0 to 1.0 base catch rate
    xp_value: int           # base XP awarded on defeat
    tongue_zone: Tongue     # which zone this was encountered in


# ---------------------------------------------------------------------------
# Lore-Appropriate Enemy Rosters
# ---------------------------------------------------------------------------
_ZONE_ENEMIES: Dict[Tongue, List[Tuple[str, str]]] = {
    Tongue.KO: [
        ("Decree Wisp", "A floating wisp of absolute authority"),
        ("Command Phantom", "Ghostly enforcer of ancient decrees"),
        ("Edict Shade", "A shadow that enforces forgotten laws"),
        ("Herald Imp", "Tiny creature that screams royal commands"),
        ("Sovereign Mote", "Dust particle with delusions of grandeur"),
    ],
    Tongue.AV: [
        ("Relay Sprite", "A crackling sprite of pure signal"),
        ("Signal Hound", "A hound that tracks data across ley lines"),
        ("Packet Wraith", "Ghost of a lost message, seeking its destination"),
        ("Router Bug", "Tiny insect that redirects magical flows"),
        ("Carrier Wisp", "Glowing ball of compressed transit energy"),
    ],
    Tongue.RU: [
        ("Clause Golem", "A golem built from stacked legal clauses"),
        ("Mandate Crawler", "Caterpillar-like enforcer of policy rules"),
        ("Bylaw Beast", "Hulking creature bound by regulation armor"),
        ("Statute Sprite", "Fairy composed of tiny written rules"),
        ("Writ Worm", "Burrowing creature that eats loopholes"),
    ],
    Tongue.CA: [
        ("Hash Slime", "An amorphous blob that hashes everything it touches"),
        ("Thread Serpent", "Multi-headed snake, each head a compute thread"),
        ("Cipher Moth", "A moth with encryption patterns on its wings"),
        ("Bit Beetle", "Tiny beetle that flips between two states"),
        ("Stack Sprite", "Sprite that grows taller with each operation"),
    ],
    Tongue.UM: [
        ("Shadow Lurker", "A formless shadow that guards secret passages"),
        ("Null Guard", "Sentient void that protects hidden data"),
        ("Void Stalker", "Predator from the space between encryption layers"),
        ("Gloom Wraith", "Wraith cloaked in obscured intentions"),
        ("Cipher Shade", "A shade that speaks only in encrypted whispers"),
    ],
    Tongue.DR: [
        ("Data Djinn", "A djinn that grants wishes in structured formats"),
        ("Format Phantom", "Ghost trapped between schema versions"),
        ("Type Specter", "Haunting presence of a mismatched data type"),
        ("Schema Slime", "Jelly that reshapes into any data structure"),
        ("Token Sprite", "Sprite made of authentication tokens"),
    ],
}

# Spells for generated enemies (per tongue)
_ZONE_SPELLS: Dict[Tongue, List[Spell]] = {
    Tongue.KO: [
        Spell("Royal Decree", Tongue.KO, 18, 8, "Command a target to take damage"),
        Spell("Authority Pulse", Tongue.KO, 24, 12, "Blast of sovereign energy"),
        Spell("Edict Strike", Tongue.KO, 14, 6, "Quick strike of command"),
        Spell("Mandate Beam", Tongue.KO, 30, 16, "Concentrated authority ray"),
    ],
    Tongue.AV: [
        Spell("Signal Bolt", Tongue.AV, 16, 7, "A bolt of pure transit energy"),
        Spell("Relay Rush", Tongue.AV, 22, 11, "Rapid multi-hop attack"),
        Spell("Packet Storm", Tongue.AV, 28, 14, "Barrage of data packets"),
        Spell("Ley Surge", Tongue.AV, 12, 5, "Quick ley-line discharge"),
    ],
    Tongue.RU: [
        Spell("Policy Bind", Tongue.RU, 15, 7, "Bind target in red tape"),
        Spell("Bylaw Bash", Tongue.RU, 22, 11, "Heavy hit backed by regulation"),
        Spell("Clause Trap", Tongue.RU, 18, 9, "Ensnare in fine print"),
        Spell("Mandate Crush", Tongue.RU, 28, 15, "Crushing weight of policy"),
    ],
    Tongue.CA: [
        Spell("Hash Splash", Tongue.CA, 14, 6, "Corrosive hash residue"),
        Spell("Thread Fang", Tongue.CA, 20, 10, "Multi-threaded bite"),
        Spell("Cipher Blast", Tongue.CA, 26, 13, "Explosion of encrypted data"),
        Spell("Compute Spike", Tongue.CA, 32, 17, "Overloaded computation burst"),
    ],
    Tongue.UM: [
        Spell("Shadow Strike", Tongue.UM, 18, 8, "Attack from the dark"),
        Spell("Void Drain", Tongue.UM, 22, 11, "Siphon life through null space"),
        Spell("Gloom Burst", Tongue.UM, 26, 14, "Eruption of concentrated darkness"),
        Spell("Null Rend", Tongue.UM, 14, 6, "Quick tear in reality"),
    ],
    Tongue.DR: [
        Spell("Schema Shock", Tongue.DR, 16, 7, "Jolt of malformed data"),
        Spell("Format Crush", Tongue.DR, 24, 12, "Crush under schema weight"),
        Spell("Type Burn", Tongue.DR, 20, 10, "Burn with authentication fire"),
        Spell("Token Barrage", Tongue.DR, 30, 16, "Swarm of expired tokens"),
    ],
}

# Cross-tongue secondary spells (for variety)
_SECONDARY_SPELLS: List[Spell] = [
    Spell("Spark", Tongue.KO, 10, 4, "Tiny spark of authority"),
    Spell("Ping", Tongue.AV, 8, 3, "Quick signal ping"),
    Spell("Fine Print", Tongue.RU, 12, 5, "Snag in obscure rules"),
    Spell("Overflow", Tongue.CA, 14, 6, "Buffer overflow attack"),
    Spell("Whisper", Tongue.UM, 10, 4, "Unsettling shadow whisper"),
    Spell("Corrupt", Tongue.DR, 12, 5, "Minor data corruption"),
]


# ---------------------------------------------------------------------------
# Encounter Generator
# ---------------------------------------------------------------------------
def generate_wild_encounter(
    zone_tongue: Tongue,
    player_level: int,
) -> WildEncounter:
    """Create a random wild encounter themed to the zone's tongue.

    The enemy's level scales with the player's level (+/- 2), and its stats
    scale accordingly.  It receives 2-4 primary-tongue spells and 0-1
    secondary-tongue spells.

    Args:
        zone_tongue: The Tongue element of the current zone.
        player_level: The player character's current level.

    Returns:
        A fully constructed WildEncounter ready for battle.
    """
    roster = _ZONE_ENEMIES.get(zone_tongue, _ZONE_ENEMIES[Tongue.KO])
    name, backstory = random.choice(roster)

    # Level within +/- 2 of player, minimum 1
    enemy_level = max(1, player_level + random.randint(-2, 2))

    # Scale stats by level
    base_hp = 40 + enemy_level * 12 + random.randint(-5, 10)
    base_mp = 20 + enemy_level * 6 + random.randint(-3, 5)
    base_atk = 6 + enemy_level * 2 + random.randint(-1, 2)
    base_def = 5 + enemy_level * 2 + random.randint(-1, 2)
    base_spd = 5 + enemy_level + random.randint(-1, 3)
    base_wis = 5 + enemy_level + random.randint(-1, 3)

    # Build tongue proficiencies to match level
    prof: Dict[str, float] = {t.value: 0.0 for t in Tongue}
    # Give primary tongue proficiency proportional to level
    prof[zone_tongue.value] = min(1.0, enemy_level * 0.08 + random.uniform(0.0, 0.1))

    stats = Stats(
        hp=base_hp,
        max_hp=base_hp,
        mp=base_mp,
        max_mp=base_mp,
        attack=base_atk,
        defense=base_def,
        speed=base_spd,
        wisdom=base_wis,
        tongue_prof=prof,
    )

    # Assign 2-4 primary spells
    primary_spells = _ZONE_SPELLS.get(zone_tongue, _ZONE_SPELLS[Tongue.KO])
    num_primary = random.randint(2, min(4, len(primary_spells)))
    chosen_spells: List[Spell] = random.sample(primary_spells, num_primary)

    # Maybe add a secondary tongue spell (50% chance)
    if random.random() < 0.5:
        # Pick a secondary tongue that is NOT the zone tongue
        secondary_options = [s for s in _SECONDARY_SPELLS if s.tongue != zone_tongue]
        if secondary_options:
            chosen_spells.append(random.choice(secondary_options))

    # Determine evo stage by level
    if enemy_level <= 3:
        evo = EvoStage.FRESH
    elif enemy_level <= 8:
        evo = EvoStage.ROOKIE
    elif enemy_level <= 15:
        evo = EvoStage.CHAMPION
    elif enemy_level <= 25:
        evo = EvoStage.ULTIMATE
    else:
        evo = EvoStage.MEGA

    enemy = Character(
        name=name,
        title=f"Wild {TONGUE_LABELS.get(zone_tongue.value, 'Unknown')} Bug",
        tongue_affinity=zone_tongue,
        evo_stage=evo,
        stats=stats,
        spells=chosen_spells,
        backstory=backstory,
        is_enemy=True,
    )

    # Catch rate: weaker enemies are easier to catch
    catch_rate = max(0.05, min(0.8, 0.6 - enemy_level * 0.02 + random.uniform(-0.05, 0.05)))

    # XP value: scales with level and tongue weight
    tongue_weight = TONGUE_WEIGHTS.get(zone_tongue, 1.0)
    xp_value = int(10 + enemy_level * 5 * (1 + tongue_weight * 0.1))

    return WildEncounter(
        enemy=enemy,
        catch_rate=catch_rate,
        xp_value=xp_value,
        tongue_zone=zone_tongue,
    )


# ---------------------------------------------------------------------------
# Learnable Moves by Level (for level-up move learning)
# ---------------------------------------------------------------------------
_LEVEL_MOVES: Dict[Tongue, List[Tuple[int, Spell]]] = {
    Tongue.KO: [
        (3, Spell("Command Spark", Tongue.KO, 14, 6, "Quick burst of authority")),
        (6, Spell("Sovereign Pulse", Tongue.KO, 22, 10, "Pulse of royal power")),
        (10, Spell("Royal Decree", Tongue.KO, 28, 14, "Decree that damages and slows")),
        (15, Spell("Absolute Authority", Tongue.KO, 38, 20, "Overwhelming command strike")),
        (22, Spell("Kor'aelin Judgment", Tongue.KO, 50, 28, "Ultimate authority — judges and punishes")),
    ],
    Tongue.AV: [
        (3, Spell("Quick Relay", Tongue.AV, 12, 5, "Fast signal bounce")),
        (6, Spell("Transit Bolt", Tongue.AV, 20, 9, "Lightning-fast transit strike")),
        (10, Spell("Ley Line Surge", Tongue.AV, 26, 13, "Channel ley line for burst")),
        (15, Spell("Dimensional Relay", Tongue.AV, 34, 18, "Relay attack through dimensions")),
        (22, Spell("Avali Storm", Tongue.AV, 48, 26, "Storm of pure transport energy")),
    ],
    Tongue.RU: [
        (3, Spell("Red Tape", Tongue.RU, 13, 6, "Tangle in bureaucracy")),
        (6, Spell("Policy Shield", Tongue.RU, 0, 8, "Raise defense with regulations")),
        (10, Spell("Mandate Strike", Tongue.RU, 24, 12, "Heavy policy-backed blow")),
        (15, Spell("Regulatory Storm", Tongue.RU, 32, 17, "Storm of binding clauses")),
        (22, Spell("Runethic Decree", Tongue.RU, 46, 25, "Ultimate policy — immobilizes and damages")),
    ],
    Tongue.CA: [
        (3, Spell("Bit Flip", Tongue.CA, 11, 5, "Quick computational jab")),
        (6, Spell("Thread Weave", Tongue.CA, 19, 9, "Multi-threaded attack")),
        (10, Spell("Cipher Lock", Tongue.CA, 25, 13, "Lock down with encryption")),
        (15, Spell("Compile Burst", Tongue.CA, 33, 18, "Explosive compilation energy")),
        (22, Spell("Cassisivadan Overload", Tongue.CA, 48, 27, "Overload all compute channels")),
    ],
    Tongue.UM: [
        (3, Spell("Shadow Nip", Tongue.UM, 12, 5, "Quick shadow bite")),
        (6, Spell("Null Pulse", Tongue.UM, 20, 10, "Pulse of void energy")),
        (10, Spell("Void Rend", Tongue.UM, 26, 14, "Tear through shadow veil")),
        (15, Spell("Darkness Surge", Tongue.UM, 35, 19, "Surge of deep darkness")),
        (22, Spell("Umbroth Eclipse", Tongue.UM, 50, 28, "Total shadow eclipse")),
    ],
    Tongue.DR: [
        (3, Spell("Data Jab", Tongue.DR, 12, 5, "Quick schema poke")),
        (6, Spell("Format Strike", Tongue.DR, 20, 9, "Structured data blow")),
        (10, Spell("Auth Burn", Tongue.DR, 26, 13, "Authentication fire blast")),
        (15, Spell("Schema Shatter", Tongue.DR, 34, 18, "Break the data mold")),
        (22, Spell("Draumric Forge", Tongue.DR, 49, 27, "Forge of ultimate schema fire")),
    ],
}


# ---------------------------------------------------------------------------
# Battle Engine — Turn Logic and Mechanics
# ---------------------------------------------------------------------------
class BattleEngine:
    """Runs the turn-based battle logic: damage, catching, XP, level-up.

    This is a pure-logic class with no rendering.  The BattleRenderer
    calls methods here and reads results to drive animations.
    """

    def __init__(
        self,
        player: Character,
        encounter: WildEncounter,
    ) -> None:
        self.player: Character = player
        self.enemy: Character = encounter.enemy
        self.encounter: WildEncounter = encounter

        # Snapshot starting HP for animations
        self.player_display_hp: float = float(player.stats.hp)
        self.enemy_display_hp: float = float(encounter.enemy.stats.hp)

        # Battle outcome
        self.victory: bool = False
        self.defeat: bool = False
        self.fled: bool = False
        self.caught: bool = False

        # XP & level tracking
        self.xp_gained: int = 0
        self.levels_gained: int = 0
        self.learned_moves: List[Spell] = []
        self.old_level: int = player.stats.level

        # Log
        self.log: List[str] = []

    # ----- Damage -----
    def compute_damage(
        self,
        attacker: Character,
        defender: Character,
        spell: Optional[Spell] = None,
    ) -> Tuple[int, float, bool, str]:
        """Compute damage with full tongue effectiveness.

        Returns:
            (damage, type_multiplier, is_crit, effectiveness_text)
        """
        if spell:
            base_power = spell.power + attacker.stats.wisdom // 3
            tongue = spell.tongue
        else:
            base_power = attacker.stats.attack
            tongue = attacker.tongue_affinity

        # Type effectiveness from TONGUE_CHART
        type_mult: float = 1.0
        effectiveness_text: str = ""
        chart = TONGUE_CHART.get(tongue, {})
        if chart.get("strong") == defender.tongue_affinity:
            type_mult = 1.5
            effectiveness_text = "super effective"
        elif chart.get("weak") == defender.tongue_affinity:
            type_mult = 0.5
            effectiveness_text = "not very effective"
        else:
            effectiveness_text = "neutral"

        # Proficiency bonus
        prof = attacker.stats.tongue_prof.get(tongue.value, 0.0)
        prof_mult = 1.0 + prof * 0.5

        # Stat ratio
        atk_stat = attacker.stats.attack if not spell else attacker.stats.wisdom
        def_stat = defender.stats.defense
        stat_ratio = max(0.2, atk_stat / max(1, def_stat))

        # Random variance
        variance = random.uniform(0.85, 1.0)

        # Critical hit
        crit_chance = 0.05 + prof * 0.1
        is_crit = random.random() < crit_chance
        crit_mult = 1.5 if is_crit else 1.0

        raw = base_power * stat_ratio * type_mult * prof_mult * variance * crit_mult
        damage = max(1, int(raw))

        return damage, type_mult, is_crit, effectiveness_text

    def execute_player_attack(
        self,
        spell: Optional[Spell] = None,
    ) -> Tuple[int, float, bool, str]:
        """Execute a player attack against the enemy.

        Returns (damage, type_mult, is_crit, effectiveness_text).
        """
        if spell and self.player.stats.mp < spell.mp_cost:
            self.log.append(f"Not enough MP for {spell.name}!")
            return 0, 1.0, False, "neutral"

        if spell:
            self.player.stats.mp -= spell.mp_cost

        damage, type_mult, is_crit, eff_text = self.compute_damage(
            self.player, self.enemy, spell,
        )
        self.enemy.stats.hp = max(0, self.enemy.stats.hp - damage)

        # Build log message
        action_name = spell.name if spell else "Attack"
        msg = f"{self.player.name} used {action_name}! {damage} dmg!"
        if is_crit:
            msg += " Critical hit!"
        if type_mult > 1.0:
            msg += " Super effective!"
        elif type_mult < 1.0:
            msg += " Not very effective..."
        self.log.append(msg)

        if self.enemy.stats.hp <= 0:
            self.victory = True
            self.log.append(f"Wild {self.enemy.name} was defeated!")

        return damage, type_mult, is_crit, eff_text

    def execute_enemy_attack(self) -> Tuple[int, Optional[Spell], float, bool, str]:
        """Enemy AI picks a move and attacks.

        Returns (damage, spell_used, type_mult, is_crit, effectiveness_text).
        """
        # Pick a spell or basic attack
        spell: Optional[Spell] = None
        if self.enemy.spells and random.random() < 0.65:
            usable = [s for s in self.enemy.spells if self.enemy.stats.mp >= s.mp_cost]
            if usable:
                spell = random.choice(usable)
                self.enemy.stats.mp -= spell.mp_cost

        damage, type_mult, is_crit, eff_text = self.compute_damage(
            self.enemy, self.player, spell,
        )
        self.player.stats.hp = max(0, self.player.stats.hp - damage)

        action_name = spell.name if spell else "Attack"
        msg = f"Wild {self.enemy.name} used {action_name}! {damage} dmg!"
        if is_crit:
            msg += " Critical hit!"
        if type_mult > 1.0:
            msg += " Super effective!"
        elif type_mult < 1.0:
            msg += " Not very effective..."
        self.log.append(msg)

        if self.player.stats.hp <= 0:
            self.defeat = True
            self.log.append(f"{self.player.name} fainted!")

        return damage, spell, type_mult, is_crit, eff_text

    def player_goes_first(self) -> bool:
        """Determine turn order based on speed."""
        player_spd = self.player.stats.speed + random.randint(-1, 1)
        enemy_spd = self.enemy.stats.speed + random.randint(-1, 1)
        return player_spd >= enemy_spd

    # ----- Catching -----
    def attempt_catch(self) -> bool:
        """Attempt to catch the wild enemy.

        Catch success = base_rate * (1 - enemy_hp%) * alignment_bonus * random.
        """
        hp_ratio = self.enemy.stats.hp / max(1, self.enemy.stats.max_hp)
        hp_factor = 1.0 - hp_ratio * 0.6  # lower HP = easier catch

        # Tongue alignment bonus: matching tongue = easier catch
        alignment = 1.0
        if self.player.tongue_affinity == self.enemy.tongue_affinity:
            alignment = 1.3
        elif (TONGUE_CHART.get(self.player.tongue_affinity, {}).get("strong")
              == self.enemy.tongue_affinity):
            alignment = 1.15

        roll = random.uniform(0.0, 1.0)
        threshold = self.encounter.catch_rate * hp_factor * alignment

        success = roll < threshold
        self.caught = success
        if success:
            self.log.append(f"Gotcha! Wild {self.enemy.name} was caught!")
        else:
            self.log.append(f"Oh no! The wild {self.enemy.name} broke free!")
        return success

    # ----- Running -----
    def attempt_run(self) -> bool:
        """Attempt to flee. Faster player = higher chance."""
        speed_ratio = self.player.stats.speed / max(1, self.enemy.stats.speed)
        chance = min(0.95, 0.5 * speed_ratio + 0.2)
        success = random.random() < chance
        if success:
            self.fled = True
            self.log.append("Got away safely!")
        else:
            self.log.append("Can't escape!")
        return success

    # ----- XP & Level Up -----
    def award_xp(self) -> Tuple[int, int, List[Spell]]:
        """Award XP after victory, check for level ups and new moves.

        Returns:
            (xp_gained, levels_gained, list_of_new_moves_learned)
        """
        level_diff = max(1, self.enemy.stats.level - self.player.stats.level + 3)
        level_modifier = 0.5 + level_diff * 0.25
        xp = int(self.encounter.xp_value * level_modifier)
        self.xp_gained = xp

        old_level = self.player.stats.level

        # Apply XP as tongue proficiency in the enemy's tongue
        prof_gain = xp / 500.0
        current = self.player.stats.tongue_prof.get(
            self.encounter.tongue_zone.value, 0.0
        )
        self.player.stats.tongue_prof[self.encounter.tongue_zone.value] = min(
            1.0, current + prof_gain
        )

        # Also gain a bit in the player's own tongue
        own_key = self.player.tongue_affinity.value
        own_current = self.player.stats.tongue_prof.get(own_key, 0.0)
        self.player.stats.tongue_prof[own_key] = min(1.0, own_current + prof_gain * 0.3)

        new_level = self.player.stats.level
        self.levels_gained = max(0, new_level - old_level)

        # Check for new moves learned
        learned: List[Spell] = []
        tongue = self.player.tongue_affinity
        level_moves = _LEVEL_MOVES.get(tongue, [])
        existing_names = {s.name for s in self.player.spells}
        for req_level, spell in level_moves:
            if old_level < req_level <= new_level and spell.name not in existing_names:
                learned.append(spell)
                self.player.spells.append(spell)

        self.learned_moves = learned
        if self.levels_gained > 0:
            self.log.append(
                f"{self.player.name} grew to level {new_level}!"
            )
            # Stat boosts on level up
            for _ in range(self.levels_gained):
                self.player.stats.max_hp += random.randint(3, 8)
                self.player.stats.max_mp += random.randint(2, 5)
                self.player.stats.attack += random.randint(0, 2)
                self.player.stats.defense += random.randint(0, 2)
                self.player.stats.speed += random.randint(0, 1)
                self.player.stats.wisdom += random.randint(0, 2)
            self.player.stats.hp = self.player.stats.max_hp
            self.player.stats.mp = self.player.stats.max_mp

        for move in learned:
            self.log.append(f"{self.player.name} learned {move.name}!")

        return xp, self.levels_gained, learned

    # ----- Effectiveness query -----
    @staticmethod
    def get_effectiveness(
        spell_tongue: Tongue,
        defender_tongue: Tongue,
    ) -> Tuple[float, str]:
        """Return (multiplier, label) for a tongue vs. a defender tongue."""
        chart = TONGUE_CHART.get(spell_tongue, {})
        if chart.get("strong") == defender_tongue:
            return 1.5, "super effective"
        elif chart.get("weak") == defender_tongue:
            return 0.5, "not very effective"
        return 1.0, "neutral"


# ---------------------------------------------------------------------------
# Sprite Drawing Helpers (shape-based, no image files)
# ---------------------------------------------------------------------------
def _draw_creature_sprite(
    surface: pygame.Surface,
    x: int,
    y: int,
    size: int,
    tongue: Tongue,
    is_enemy: bool = False,
    alpha: int = 255,
    flash_white: bool = False,
) -> None:
    """Draw a placeholder creature sprite using geometric shapes.

    Each tongue type gets a distinct silhouette built from circles,
    rectangles, and polygons so they are visually distinguishable.
    """
    color = TONGUE_COLORS.get(tongue.value, (128, 128, 128))
    r, g, b = color
    dark = (max(0, r - 60), max(0, g - 60), max(0, b - 60))
    light = (min(255, r + 60), min(255, g + 60), min(255, b + 60))

    if flash_white:
        color = _WHITE
        dark = (220, 220, 220)
        light = _WHITE

    # Create a temporary surface for alpha support
    sprite_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    if tongue == Tongue.KO:
        # Authority: Crown-shaped — angular, commanding
        # Body
        pygame.draw.circle(sprite_surf, color, (cx, cy + 4), size // 3)
        # Crown points
        for i in range(5):
            angle = math.pi + (i / 4) * math.pi
            px = cx + int(math.cos(angle) * size * 0.35)
            py = cy - size // 4 + int(math.sin(angle) * size * 0.15)
            pygame.draw.circle(sprite_surf, light, (px, py), 4)
        # Crown base
        pygame.draw.rect(sprite_surf, dark, (cx - size // 3, cy - size // 4, size * 2 // 3, 6))
        # Eyes
        pygame.draw.circle(sprite_surf, _WHITE, (cx - 6, cy + 2), 3)
        pygame.draw.circle(sprite_surf, _WHITE, (cx + 6, cy + 2), 3)
        pygame.draw.circle(sprite_surf, (180, 30, 30), (cx - 6, cy + 2), 1)
        pygame.draw.circle(sprite_surf, (180, 30, 30), (cx + 6, cy + 2), 1)

    elif tongue == Tongue.AV:
        # Transport: Lightning bolt shape — fast, electric
        # Body — elongated oval
        pygame.draw.ellipse(sprite_surf, color, (cx - size // 4, cy - size // 5, size // 2, size * 2 // 5))
        # Lightning wings
        pts_l = [(cx - size // 4, cy), (cx - size // 3 - 6, cy - 8), (cx - size // 4 + 2, cy - 2)]
        pts_r = [(cx + size // 4, cy), (cx + size // 3 + 6, cy - 8), (cx + size // 4 - 2, cy - 2)]
        pygame.draw.polygon(sprite_surf, light, pts_l)
        pygame.draw.polygon(sprite_surf, light, pts_r)
        # Tail streak
        for i in range(5):
            pygame.draw.circle(sprite_surf, (*color, 180 - i * 30), (cx, cy + size // 5 + i * 4), max(1, 4 - i))
        # Eyes
        pygame.draw.circle(sprite_surf, _WHITE, (cx - 4, cy - 4), 3)
        pygame.draw.circle(sprite_surf, _WHITE, (cx + 4, cy - 4), 3)
        pygame.draw.circle(sprite_surf, (20, 80, 140), (cx - 4, cy - 4), 1)
        pygame.draw.circle(sprite_surf, (20, 80, 140), (cx + 4, cy - 4), 1)

    elif tongue == Tongue.RU:
        # Policy: Shield/golem — heavy, rectangular, armored
        # Body — boxy
        bw, bh = size * 2 // 5, size // 2
        pygame.draw.rect(sprite_surf, color, (cx - bw // 2, cy - bh // 4, bw, bh), border_radius=4)
        # Shield pattern
        pygame.draw.rect(sprite_surf, dark, (cx - bw // 2 + 3, cy - bh // 4 + 3, bw - 6, bh - 6), 2, border_radius=3)
        # Arms
        pygame.draw.rect(sprite_surf, dark, (cx - bw // 2 - 5, cy, 5, bh // 2))
        pygame.draw.rect(sprite_surf, dark, (cx + bw // 2, cy, 5, bh // 2))
        # Head
        pygame.draw.circle(sprite_surf, color, (cx, cy - bh // 4 - 4), size // 6)
        # Eyes
        pygame.draw.circle(sprite_surf, _WHITE, (cx - 3, cy - bh // 4 - 5), 2)
        pygame.draw.circle(sprite_surf, _WHITE, (cx + 3, cy - bh // 4 - 5), 2)
        pygame.draw.circle(sprite_surf, (140, 120, 20), (cx - 3, cy - bh // 4 - 5), 1)
        pygame.draw.circle(sprite_surf, (140, 120, 20), (cx + 3, cy - bh // 4 - 5), 1)

    elif tongue == Tongue.CA:
        # Compute: Slime / amorphous blob — fluid, glowing
        # Main blob
        pygame.draw.circle(sprite_surf, color, (cx, cy + 2), size // 3)
        # Smaller bubbles
        pygame.draw.circle(sprite_surf, light, (cx - 8, cy - 6), size // 6)
        pygame.draw.circle(sprite_surf, light, (cx + 10, cy - 2), size // 7)
        # Highlight
        pygame.draw.circle(sprite_surf, _WHITE, (cx - 4, cy - 4), 3)
        # Eyes
        pygame.draw.circle(sprite_surf, _WHITE, (cx - 5, cy), 3)
        pygame.draw.circle(sprite_surf, _WHITE, (cx + 5, cy), 3)
        pygame.draw.circle(sprite_surf, (20, 120, 60), (cx - 5, cy), 1)
        pygame.draw.circle(sprite_surf, (20, 120, 60), (cx + 5, cy), 1)
        # Drip
        for i in range(3):
            pygame.draw.circle(sprite_surf, (*color, 160), (cx - 6 + i * 6, cy + size // 3 + 2), 2)

    elif tongue == Tongue.UM:
        # Security: Phantom / wraith — wispy, dark, glowing eyes
        # Wispy body triangle
        pts = [
            (cx, cy - size // 3),
            (cx - size // 3, cy + size // 4),
            (cx + size // 3, cy + size // 4),
        ]
        pygame.draw.polygon(sprite_surf, color, pts)
        # Inner darkness
        inner = [
            (cx, cy - size // 5),
            (cx - size // 5, cy + size // 6),
            (cx + size // 5, cy + size // 6),
        ]
        pygame.draw.polygon(sprite_surf, dark, inner)
        # Wispy tail
        for i in range(4):
            tx = cx - 8 + i * 5 + int(math.sin(time.time() * 3 + i) * 3)
            ty = cy + size // 4 + i * 3
            pygame.draw.circle(sprite_surf, (*color, 160 - i * 30), (tx, ty), max(1, 3 - i))
        # Glowing eyes
        pygame.draw.circle(sprite_surf, (255, 100, 255), (cx - 5, cy - 4), 3)
        pygame.draw.circle(sprite_surf, (255, 100, 255), (cx + 5, cy - 4), 3)
        pygame.draw.circle(sprite_surf, _WHITE, (cx - 5, cy - 4), 1)
        pygame.draw.circle(sprite_surf, _WHITE, (cx + 5, cy - 4), 1)

    elif tongue == Tongue.DR:
        # Schema: Serpentine / dragon-ish — coiled, fire accents
        # Coiled body
        for i in range(8):
            angle = i * 0.8
            bx = cx + int(math.cos(angle) * size * 0.2)
            by = cy + int(math.sin(angle) * size * 0.15) + (i - 4) * 3
            pygame.draw.circle(sprite_surf, color, (bx, by), max(3, 7 - i // 2))
        # Head
        pygame.draw.circle(sprite_surf, light, (cx + size // 5, cy - size // 5), size // 6)
        # Eyes
        pygame.draw.circle(sprite_surf, _WHITE, (cx + size // 5 + 2, cy - size // 5 - 1), 2)
        pygame.draw.circle(sprite_surf, (160, 60, 20), (cx + size // 5 + 2, cy - size // 5 - 1), 1)
        # Fire breath particles
        for i in range(3):
            fx = cx + size // 5 + 8 + i * 4
            fy = cy - size // 5 + random.randint(-3, 3)
            pygame.draw.circle(sprite_surf, (255, 120 + i * 30, 40), (fx, fy), max(1, 3 - i))

    else:
        # Fallback: generic circle
        pygame.draw.circle(sprite_surf, color, (cx, cy), size // 3)
        pygame.draw.circle(sprite_surf, _WHITE, (cx - 4, cy - 2), 2)
        pygame.draw.circle(sprite_surf, _WHITE, (cx + 4, cy - 2), 2)

    if alpha < 255:
        sprite_surf.set_alpha(alpha)

    surface.blit(sprite_surf, (x, y))


def _draw_tongue_icon(
    surface: pygame.Surface,
    x: int,
    y: int,
    tongue: Tongue,
    size: int = 12,
) -> None:
    """Draw a small colored tongue-type icon (colored circle with letter)."""
    color = TONGUE_COLORS.get(tongue.value, (128, 128, 128))
    pygame.draw.circle(surface, color, (x + size // 2, y + size // 2), size // 2)
    pygame.draw.circle(surface, _WHITE, (x + size // 2, y + size // 2), size // 2, 1)
    # Letter
    font = pygame.font.SysFont("arial", max(8, size - 4), bold=True)
    letter = font.render(tongue.value[0], True, _WHITE)
    surface.blit(
        letter,
        (x + size // 2 - letter.get_width() // 2,
         y + size // 2 - letter.get_height() // 2),
    )


# ---------------------------------------------------------------------------
# Battle Renderer — Full Pokemon-Style Battle Screen
# ---------------------------------------------------------------------------
class BattleRenderer:
    """Renders a complete Pokemon-style 1v1 battle on a 640x480 surface.

    Usage:
        renderer = BattleRenderer(player_char, encounter)
        # In game loop:
        renderer.update(pygame_events, dt)
        renderer.draw(surface)
        if renderer.finished:
            result = renderer.result  # "victory" / "defeat" / "fled" / "caught"
    """

    def __init__(
        self,
        player: Character,
        encounter: WildEncounter,
    ) -> None:
        self.engine: BattleEngine = BattleEngine(player, encounter)
        self.player: Character = player
        self.enemy: Character = encounter.enemy
        self.encounter: WildEncounter = encounter

        # FSM
        self.state: BattleState = BattleState.INTRO
        self._state_timer: float = time.time()

        # Menu state
        self._menu_cursor: int = 0          # 0-3 for FIGHT/CATCH/ITEM/RUN
        self._move_cursor: int = 0          # 0-3 for spell selection
        self._in_move_select: bool = False

        # Animations
        self._player_hp_anim: HPDrainAnimation = HPDrainAnimation(
            float(player.stats.hp), float(player.stats.hp), float(player.stats.max_hp),
        )
        self._enemy_hp_anim: HPDrainAnimation = HPDrainAnimation(
            float(encounter.enemy.stats.hp), float(encounter.enemy.stats.hp),
            float(encounter.enemy.stats.max_hp),
        )
        self._damage_popups: List[DamagePopup] = []
        self._catch_anim: Optional[CatchAnimation] = None
        self._xp_anim: Optional[XPFillAnimation] = None

        # Text box
        self._text_lines: List[TypewriterText] = []
        self._push_text(f"A wild {self.enemy.name} appeared!")

        # Visual effects
        self._screen_shake: float = 0.0     # remaining shake time
        self._shake_intensity: int = 0
        self._enemy_flash: float = 0.0      # flash white timer
        self._player_flash: float = 0.0
        self._enemy_visible: bool = True
        self._slide_in_progress: float = 0.0  # intro slide timer

        # Result
        self.finished: bool = False
        self.result: str = ""  # "victory", "defeat", "fled", "caught"

        # Fonts (lazily initialized)
        self._fonts: Dict[str, pygame.font.Font] = {}

        # Track last frame time
        self._last_time: float = time.time()

        # Victory state substeps
        self._victory_phase: int = 0  # 0=msg, 1=xp, 2=moves, 3=done
        self._victory_timer: float = 0.0

    # ----- Font helpers -----
    def _font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = f"{size}_{bold}"
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont("arial", size, bold=bold)
        return self._fonts[key]

    # ----- Text box -----
    def _push_text(self, text: str) -> None:
        """Add a line to the text box with typewriter effect."""
        self._text_lines.append(TypewriterText(text, time.time()))
        # Keep only last 3 lines
        if len(self._text_lines) > 3:
            self._text_lines = self._text_lines[-3:]

    def _all_text_finished(self) -> bool:
        return all(t.finished for t in self._text_lines)

    def _skip_text(self) -> None:
        for t in self._text_lines:
            t.skip()

    # ----- State transitions -----
    def _enter_state(self, new_state: BattleState) -> None:
        self.state = new_state
        self._state_timer = time.time()

    def _state_elapsed(self) -> float:
        return time.time() - self._state_timer

    # ----- Main update (called every frame) -----
    def update(self, events: List[pygame.event.Event], dt: float = 0.0) -> None:
        """Process input events and advance the battle FSM.

        Args:
            events: pygame events for this frame.
            dt: delta time in seconds (if 0, computed from wall clock).
        """
        now = time.time()
        if dt <= 0:
            dt = now - self._last_time
        self._last_time = now

        # Update animations
        self._player_hp_anim.target_hp = float(self.player.stats.hp)
        self._enemy_hp_anim.target_hp = float(self.enemy.stats.hp)
        self._player_hp_anim.update(dt)
        self._enemy_hp_anim.update(dt)

        # Decay shake
        if self._screen_shake > 0:
            self._screen_shake = max(0, self._screen_shake - dt)

        # Decay flash
        if self._enemy_flash > 0:
            self._enemy_flash = max(0, self._enemy_flash - dt)
        if self._player_flash > 0:
            self._player_flash = max(0, self._player_flash - dt)

        # Clean dead popups
        self._damage_popups = [p for p in self._damage_popups if p.alive]

        # XP animation
        if self._xp_anim is not None:
            self._xp_anim.update(dt)

        # Dispatch based on state
        if self.state == BattleState.INTRO:
            self._update_intro(events, dt)
        elif self.state == BattleState.PLAYER_TURN:
            self._update_player_turn(events, dt)
        elif self.state == BattleState.MOVE_SELECT:
            self._update_move_select(events, dt)
        elif self.state == BattleState.ENEMY_TURN:
            self._update_enemy_turn(events, dt)
        elif self.state == BattleState.ANIMATION:
            self._update_animation(events, dt)
        elif self.state == BattleState.CATCH_ATTEMPT:
            self._update_catch(events, dt)
        elif self.state == BattleState.RUN:
            self._update_run(events, dt)
        elif self.state == BattleState.VICTORY:
            self._update_victory(events, dt)
        elif self.state == BattleState.DEFEAT:
            self._update_defeat(events, dt)
        elif self.state == BattleState.RESULT:
            self._update_result(events, dt)

    # ----- State handlers -----
    def _update_intro(self, events: List[pygame.event.Event], dt: float) -> None:
        self._slide_in_progress = min(1.0, self._state_elapsed() / INTRO_DURATION)
        # Allow skipping intro text
        for ev in events:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._skip_text()
        if self._state_elapsed() >= INTRO_DURATION and self._all_text_finished():
            self._enter_player_or_enemy_turn()

    def _enter_player_or_enemy_turn(self) -> None:
        """Decide who goes first based on speed."""
        if self.engine.player_goes_first():
            self._enter_state(BattleState.PLAYER_TURN)
            self._push_text(f"What will {self.player.name} do?")
            self._menu_cursor = 0
            self._in_move_select = False
        else:
            self._enter_state(BattleState.ENEMY_TURN)
            self._push_text(f"Wild {self.enemy.name} moves first!")

    def _update_player_turn(self, events: List[pygame.event.Event], dt: float) -> None:
        """Handle the top-level 4-option menu (FIGHT / CATCH / ITEM / RUN)."""
        for ev in events:
            if ev.type != pygame.KEYDOWN:
                continue
            key = ev.key

            # Navigate 2x2 grid
            if key in (pygame.K_LEFT, pygame.K_a):
                if self._menu_cursor % 2 == 1:
                    self._menu_cursor -= 1
            elif key in (pygame.K_RIGHT, pygame.K_d):
                if self._menu_cursor % 2 == 0:
                    self._menu_cursor += 1
            elif key in (pygame.K_UP, pygame.K_w):
                if self._menu_cursor >= 2:
                    self._menu_cursor -= 2
            elif key in (pygame.K_DOWN, pygame.K_s):
                if self._menu_cursor < 2:
                    self._menu_cursor += 2
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._select_menu_option(MENU_OPTIONS[self._menu_cursor])

    def _select_menu_option(self, option: MenuOption) -> None:
        if option == MenuOption.FIGHT:
            self._enter_state(BattleState.MOVE_SELECT)
            self._move_cursor = 0
            self._in_move_select = True
        elif option == MenuOption.CATCH:
            self._enter_state(BattleState.CATCH_ATTEMPT)
            self._start_catch_animation()
        elif option == MenuOption.ITEM:
            # No item system yet — show message and stay on player turn
            self._push_text("No items in the bag!")
            self._enter_state(BattleState.PLAYER_TURN)
        elif option == MenuOption.RUN:
            self._enter_state(BattleState.RUN)
            self._push_text(f"{self.player.name} tries to run...")

    def _update_move_select(self, events: List[pygame.event.Event], dt: float) -> None:
        """Handle spell selection in the 2x2 move grid."""
        moves = self.player.spells[:4]
        if not moves:
            # No spells — basic attack
            self._execute_player_move(None)
            return

        for ev in events:
            if ev.type != pygame.KEYDOWN:
                continue
            key = ev.key

            num_moves = len(moves)
            if key in (pygame.K_LEFT, pygame.K_a):
                if self._move_cursor % 2 == 1:
                    self._move_cursor -= 1
            elif key in (pygame.K_RIGHT, pygame.K_d):
                if self._move_cursor % 2 == 0 and self._move_cursor + 1 < num_moves:
                    self._move_cursor += 1
            elif key in (pygame.K_UP, pygame.K_w):
                if self._move_cursor >= 2:
                    self._move_cursor -= 2
            elif key in (pygame.K_DOWN, pygame.K_s):
                if self._move_cursor + 2 < num_moves:
                    self._move_cursor += 2
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                spell = moves[self._move_cursor]
                self._execute_player_move(spell)
            elif key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_b):
                # Go back to main menu
                self._enter_state(BattleState.PLAYER_TURN)
                self._in_move_select = False

    def _execute_player_move(self, spell: Optional[Spell]) -> None:
        """Execute the selected move and transition to animation."""
        self._in_move_select = False
        damage, type_mult, is_crit, eff_text = self.engine.execute_player_attack(spell)

        if damage > 0:
            # HP animation target already updated via engine
            self._enemy_flash = 0.3
            self._screen_shake = 0.2 if not is_crit else 0.5
            self._shake_intensity = 4 if not is_crit else 8

            # Damage popup on enemy
            popup_color = _WHITE
            if type_mult > 1.0:
                popup_color = (255, 80, 80)
            elif type_mult < 1.0:
                popup_color = (160, 160, 200)
            self._damage_popups.append(DamagePopup(
                x=GAME_W - 180 + random.randint(-10, 10),
                y=100 + random.randint(-10, 10),
                value=damage,
                is_crit=is_crit,
                is_heal=False,
                color=popup_color,
                start_time=time.time(),
            ))

        # Show text
        action_name = spell.name if spell else "Attack"
        msg = f"{self.player.name} used {action_name}!"
        self._push_text(msg)
        if type_mult > 1.0:
            self._push_text("It's super effective!")
        elif type_mult < 1.0:
            self._push_text("Not very effective...")
        if is_crit:
            self._push_text("A critical hit!")

        self._enter_state(BattleState.ANIMATION)

    def _update_enemy_turn(self, events: List[pygame.event.Event], dt: float) -> None:
        """AI acts after a short delay."""
        if self._state_elapsed() < ENEMY_THINK_DELAY:
            return

        damage, spell_used, type_mult, is_crit, eff_text = self.engine.execute_enemy_attack()

        if damage > 0:
            self._player_flash = 0.3
            self._screen_shake = 0.15 if not is_crit else 0.4
            self._shake_intensity = 3 if not is_crit else 7

            popup_color = _WHITE
            if type_mult > 1.0:
                popup_color = (255, 80, 80)
            elif type_mult < 1.0:
                popup_color = (160, 160, 200)
            self._damage_popups.append(DamagePopup(
                x=140 + random.randint(-10, 10),
                y=240 + random.randint(-10, 10),
                value=damage,
                is_crit=is_crit,
                is_heal=False,
                color=popup_color,
                start_time=time.time(),
            ))

        action_name = spell_used.name if spell_used else "Attack"
        self._push_text(f"Wild {self.enemy.name} used {action_name}!")
        if type_mult > 1.0:
            self._push_text("It's super effective!")
        elif type_mult < 1.0:
            self._push_text("Not very effective...")
        if is_crit:
            self._push_text("A critical hit!")

        self._enter_state(BattleState.ANIMATION)

    def _update_animation(self, events: List[pygame.event.Event], dt: float) -> None:
        """Wait for HP drain and text to finish, then check for battle end."""
        # Allow text skip
        for ev in events:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._skip_text()

        hp_done = self._player_hp_anim.finished and self._enemy_hp_anim.finished
        text_done = self._all_text_finished()
        min_time = self._state_elapsed() >= 0.5

        if hp_done and text_done and min_time:
            if self.engine.victory:
                self._enter_state(BattleState.VICTORY)
                self._push_text(f"Wild {self.enemy.name} was defeated!")
                self._victory_phase = 0
                self._victory_timer = time.time()
            elif self.engine.defeat:
                self._enter_state(BattleState.DEFEAT)
                self._push_text(f"{self.player.name} blacked out!")
            else:
                # Next turn
                if self.state == BattleState.ANIMATION:
                    # Determine who acts next
                    # If player just went, enemy goes; and vice versa
                    self._enter_player_or_enemy_turn()

    def _update_catch(self, events: List[pygame.event.Event], dt: float) -> None:
        """Process catch animation."""
        if self._catch_anim is None:
            return

        if self._catch_anim.finished:
            if self._catch_anim.success:
                self._push_text(f"Gotcha! {self.enemy.name} was caught!")
                self._enemy_visible = False
                self.result = "caught"
                self.finished = True
                self._enter_state(BattleState.RESULT)
            else:
                self._push_text(f"Oh no! {self.enemy.name} broke free!")
                # Enemy gets a turn
                self._catch_anim = None
                self._enter_state(BattleState.ENEMY_TURN)

    def _start_catch_animation(self) -> None:
        success = self.engine.attempt_catch()
        self._catch_anim = CatchAnimation(
            start_time=time.time(),
            success=success,
            target_x=GAME_W - 180,
            target_y=120,
        )
        self._push_text(f"{self.player.name} threw a Tongue Capsule!")

    def _update_run(self, events: List[pygame.event.Event], dt: float) -> None:
        if self._state_elapsed() < 0.8:
            return
        success = self.engine.attempt_run()
        if success:
            self._push_text("Got away safely!")
            self.result = "fled"
            self.finished = True
            self._enter_state(BattleState.RESULT)
        else:
            self._push_text("Can't escape!")
            self._enter_state(BattleState.ENEMY_TURN)

    def _update_victory(self, events: List[pygame.event.Event], dt: float) -> None:
        """Multi-phase victory: show XP gain, level ups, new moves."""
        elapsed = time.time() - self._victory_timer

        if self._victory_phase == 0:
            # Show "victory!" text, wait for confirm or timer
            if elapsed > 1.5 or self._key_pressed(events):
                xp, levels, moves = self.engine.award_xp()
                self._push_text(f"Gained {xp} XP!")
                self._victory_phase = 1
                self._victory_timer = time.time()

                # Start XP bar animation
                total_prof = sum(self.player.stats.tongue_prof.values())
                old_ratio = max(0, (total_prof - xp / 500.0)) % 1.0
                new_ratio = total_prof % 1.0
                if new_ratio < old_ratio:
                    new_ratio = 1.0  # wrapped around
                self._xp_anim = XPFillAnimation(
                    display_ratio=old_ratio,
                    target_ratio=new_ratio,
                )

        elif self._victory_phase == 1:
            # Show XP filling
            if (self._xp_anim is not None and self._xp_anim.finished) or elapsed > 3.0:
                if self.engine.levels_gained > 0:
                    self._push_text(
                        f"{self.player.name} grew to Lv{self.player.stats.level}!"
                    )
                self._victory_phase = 2
                self._victory_timer = time.time()

        elif self._victory_phase == 2:
            # Show learned moves
            if elapsed > 1.0 or self._key_pressed(events):
                if self.engine.learned_moves:
                    for move in self.engine.learned_moves:
                        self._push_text(f"Learned {move.name}!")
                self._victory_phase = 3
                self._victory_timer = time.time()

        elif self._victory_phase == 3:
            if elapsed > 1.0 or self._key_pressed(events):
                self.result = "victory"
                self.finished = True
                self._enter_state(BattleState.RESULT)

    def _update_defeat(self, events: List[pygame.event.Event], dt: float) -> None:
        if self._state_elapsed() > 2.0 or self._key_pressed(events):
            self.result = "defeat"
            self.finished = True
            self._enter_state(BattleState.RESULT)

    def _update_result(self, events: List[pygame.event.Event], dt: float) -> None:
        """Terminal state — the caller reads self.finished and self.result."""
        pass

    @staticmethod
    def _key_pressed(events: List[pygame.event.Event]) -> bool:
        for ev in events:
            if ev.type == pygame.KEYDOWN and ev.key in (
                pygame.K_RETURN, pygame.K_SPACE,
            ):
                return True
        return False

    # =====================================================================
    # DRAWING
    # =====================================================================
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the complete battle screen onto the given 640x480 surface."""
        # Apply screen shake
        shake_x, shake_y = 0, 0
        if self._screen_shake > 0:
            shake_x = random.randint(-self._shake_intensity, self._shake_intensity)
            shake_y = random.randint(-self._shake_intensity, self._shake_intensity)

        # Create a buffer for shake offset
        buf = pygame.Surface((GAME_W, GAME_H))

        self._draw_background(buf)
        self._draw_platforms(buf)
        self._draw_enemy_sprite(buf)
        self._draw_player_sprite(buf)
        self._draw_enemy_info_box(buf)
        self._draw_player_info_box(buf)
        self._draw_damage_popups(buf)
        self._draw_catch_ball(buf)

        # Text box and menus are drawn without shake
        surface.blit(buf, (shake_x, shake_y))

        self._draw_text_box(surface)

        if self.state == BattleState.PLAYER_TURN and not self._in_move_select:
            self._draw_main_menu(surface)
        elif self.state == BattleState.MOVE_SELECT or self._in_move_select:
            self._draw_move_menu(surface)

        # Victory / Defeat overlays
        if self.state == BattleState.VICTORY:
            self._draw_victory_overlay(surface)
        elif self.state == BattleState.DEFEAT:
            self._draw_defeat_overlay(surface)

    # ----- Background -----
    def _draw_background(self, surface: pygame.Surface) -> None:
        """Draw a sky-to-ground gradient background."""
        for y in range(GAME_H):
            ratio = y / GAME_H
            if ratio < 0.55:
                # Sky: muted blue-purple (Aethermoor palette)
                t = ratio / 0.55
                r = int(90 + t * 50)
                g = int(110 + t * 50)
                b = int(180 - t * 30)
            else:
                # Ground: greenish earth
                t = (ratio - 0.55) / 0.45
                r = int(80 + t * 50)
                g = int(130 + t * 30)
                b = int(65 + t * 25)
            pygame.draw.line(surface, (r, g, b), (0, y), (GAME_W, y))

    # ----- Platforms -----
    def _draw_platforms(self, surface: pygame.Surface) -> None:
        """Draw the two elliptical ground platforms (enemy top-right, player bottom-left)."""
        # Enemy platform (top-right)
        ecx, ecy = GAME_W - 160, 180
        pygame.draw.ellipse(surface, _SHADOW, (ecx - 80, ecy + 2, 160, 32))
        pygame.draw.ellipse(surface, (56, 112, 48), (ecx - 80, ecy, 160, 30))
        pygame.draw.ellipse(surface, (88, 160, 72), (ecx - 80, ecy - 2, 160, 26))

        # Player platform (bottom-left)
        pcx, pcy = 150, 320
        pygame.draw.ellipse(surface, _SHADOW, (pcx - 90, pcy + 2, 180, 36))
        pygame.draw.ellipse(surface, (120, 96, 64), (pcx - 90, pcy, 180, 34))
        pygame.draw.ellipse(surface, (168, 136, 96), (pcx - 90, pcy - 2, 180, 30))

    # ----- Enemy sprite -----
    def _draw_enemy_sprite(self, surface: pygame.Surface) -> None:
        if not self._enemy_visible:
            return

        # Intro slide: enemy slides in from right
        slide_offset = 0
        if self.state == BattleState.INTRO:
            slide_offset = int((1.0 - self._slide_in_progress) * 200)

        x = GAME_W - 210 + slide_offset
        y = 95
        size = 72

        flash = self._enemy_flash > 0
        alpha = 255
        if self.enemy.stats.hp <= 0:
            alpha = 80

        _draw_creature_sprite(
            surface, x, y, size,
            self.enemy.tongue_affinity,
            is_enemy=True,
            alpha=alpha,
            flash_white=flash,
        )

    # ----- Player sprite -----
    def _draw_player_sprite(self, surface: pygame.Surface) -> None:
        # Intro slide: player slides in from left
        slide_offset = 0
        if self.state == BattleState.INTRO:
            slide_offset = int((1.0 - self._slide_in_progress) * -200)

        x = 110 + slide_offset
        y = 230
        size = 80

        flash = self._player_flash > 0
        alpha = 255
        if self.player.stats.hp <= 0:
            alpha = 80

        _draw_creature_sprite(
            surface, x, y, size,
            self.player.tongue_affinity,
            is_enemy=False,
            alpha=alpha,
            flash_white=flash,
        )

    # ----- Enemy info box (top-left, Sapphire style) -----
    def _draw_enemy_info_box(self, surface: pygame.Surface) -> None:
        x, y, w = 10, 18, 220
        h = 48

        # Box background
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((248, 248, 240, 230))
        surface.blit(box, (x, y))
        pygame.draw.rect(surface, _DARK_INK, (x, y, w, h), 2, border_radius=4)

        # Name
        name_font = self._font(14, bold=True)
        name_surf = name_font.render(self.enemy.name, True, _INK)
        surface.blit(name_surf, (x + 8, y + 4))

        # Level
        lvl_font = self._font(11)
        lvl_surf = lvl_font.render(f"Lv{self.enemy.stats.level}", True, _MID_GREY)
        surface.blit(lvl_surf, (x + w - lvl_surf.get_width() - 8, y + 5))

        # Tongue icon
        _draw_tongue_icon(surface, x + w - 56, y + 4, self.enemy.tongue_affinity, 14)

        # HP label
        hp_label = self._font(9, bold=True)
        surface.blit(hp_label.render("HP", True, (255, 180, 40)), (x + 8, y + 24))

        # HP bar
        bar_x = x + 28
        bar_y = y + 26
        bar_w = w - 36
        bar_h = 6
        hp_ratio = self._enemy_hp_anim.ratio
        pygame.draw.rect(surface, HP_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        if hp_ratio > 0:
            fill_color = HP_GREEN if hp_ratio > 0.5 else (HP_YELLOW if hp_ratio > 0.25 else HP_RED)
            fill_w = max(1, int(bar_w * hp_ratio))
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

        # Tongue type label (small, below HP)
        type_font = self._font(9)
        tongue_name = TONGUE_LABELS.get(self.enemy.tongue_affinity.value, "???")
        type_surf = type_font.render(tongue_name, True, _MID_GREY)
        surface.blit(type_surf, (x + 8, y + 35))

    # ----- Player info box (bottom-right, Sapphire style) -----
    def _draw_player_info_box(self, surface: pygame.Surface) -> None:
        x, y, w = GAME_W - 240, 252, 230
        h = 68

        # Box background
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((248, 248, 240, 230))
        surface.blit(box, (x, y))
        pygame.draw.rect(surface, _DARK_INK, (x, y, w, h), 2, border_radius=4)

        # Name
        name_font = self._font(14, bold=True)
        name_surf = name_font.render(self.player.name, True, _INK)
        surface.blit(name_surf, (x + 8, y + 4))

        # Level
        lvl_font = self._font(11)
        lvl_surf = lvl_font.render(f"Lv{self.player.stats.level}", True, _MID_GREY)
        surface.blit(lvl_surf, (x + w - lvl_surf.get_width() - 8, y + 5))

        # Tongue icon
        _draw_tongue_icon(surface, x + w - 56, y + 4, self.player.tongue_affinity, 14)

        # HP label
        hp_label = self._font(9, bold=True)
        surface.blit(hp_label.render("HP", True, (255, 180, 40)), (x + 8, y + 24))

        # HP bar
        bar_x = x + 28
        bar_y = y + 26
        bar_w = w - 36
        bar_h = 6
        hp_ratio = self._player_hp_anim.ratio
        pygame.draw.rect(surface, HP_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        if hp_ratio > 0:
            fill_color = HP_GREEN if hp_ratio > 0.5 else (HP_YELLOW if hp_ratio > 0.25 else HP_RED)
            fill_w = max(1, int(bar_w * hp_ratio))
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

        # HP numbers
        hp_num_font = self._font(10)
        hp_text = f"{max(0, int(self._player_hp_anim.display_hp))}/{self.player.stats.max_hp}"
        hp_surf = hp_num_font.render(hp_text, True, _INK)
        surface.blit(hp_surf, (x + w - hp_surf.get_width() - 8, y + 34))

        # XP bar
        xp_y = y + h - 14
        xp_label = self._font(8)
        surface.blit(xp_label.render("EXP", True, (80, 96, 128)), (x + 6, xp_y - 1))
        xp_bar_x = x + 30
        xp_bar_w = w - 38
        pygame.draw.rect(surface, XP_BG, (xp_bar_x, xp_y, xp_bar_w, 5), border_radius=2)

        # XP fill
        if self._xp_anim is not None:
            xp_ratio = self._xp_anim.display_ratio
        else:
            total_prof = sum(self.player.stats.tongue_prof.values())
            xp_ratio = total_prof % 1.0 if total_prof > 0 else 0.0

        if xp_ratio > 0:
            xp_fill_w = max(1, int(xp_bar_w * xp_ratio))
            pygame.draw.rect(surface, XP_BLUE, (xp_bar_x, xp_y, xp_fill_w, 5), border_radius=2)

    # ----- Damage popups -----
    def _draw_damage_popups(self, surface: pygame.Surface) -> None:
        for popup in self._damage_popups:
            progress = popup.progress
            # Float upward
            draw_y = int(popup.y - progress * 40)
            # Fade out
            alpha = max(0, int(255 * (1.0 - progress * 0.7)))

            font = self._font(16 if popup.is_crit else 13, bold=popup.is_crit)
            text = f"-{popup.value}" if not popup.is_heal else f"+{popup.value}"
            if popup.is_crit:
                text += "!"

            # Shadow
            shadow_surf = font.render(text, True, _BLACK)
            shadow_surf.set_alpha(alpha)
            surface.blit(shadow_surf, (int(popup.x) + 1, draw_y + 1))

            # Main text
            text_surf = font.render(text, True, popup.color)
            text_surf.set_alpha(alpha)
            surface.blit(text_surf, (int(popup.x), draw_y))

    # ----- Catch ball -----
    def _draw_catch_ball(self, surface: pygame.Surface) -> None:
        if self._catch_anim is None:
            return

        bx = int(self._catch_anim.ball_x)
        by = int(self._catch_anim.ball_y)
        progress = self._catch_anim.progress

        # Ball colors: red top, white bottom (Poke Ball style but tongue-themed)
        tongue_color = TONGUE_COLORS.get(
            self.player.tongue_affinity.value, (200, 60, 60),
        )

        ball_radius = 10

        # Draw ball
        pygame.draw.circle(surface, tongue_color, (bx, by), ball_radius)
        pygame.draw.circle(surface, _WHITE, (bx, by + 2), ball_radius - 3)
        pygame.draw.line(surface, _BLACK, (bx - ball_radius, by), (bx + ball_radius, by), 2)
        pygame.draw.circle(surface, _WHITE, (bx, by), 3)
        pygame.draw.circle(surface, _BLACK, (bx, by), 3, 1)

        # Shake wiggle after bouncing
        if progress > 0.75 and not self._catch_anim.success:
            wiggle = int(math.sin(progress * 40) * 4)
            # Re-draw at offset
            pygame.draw.circle(surface, tongue_color, (bx + wiggle, by), ball_radius)
            pygame.draw.circle(surface, _WHITE, (bx + wiggle, by + 2), ball_radius - 3)
            pygame.draw.line(surface, _BLACK, (bx + wiggle - ball_radius, by), (bx + wiggle + ball_radius, by), 2)
            pygame.draw.circle(surface, _WHITE, (bx + wiggle, by), 3)
            pygame.draw.circle(surface, _BLACK, (bx + wiggle, by), 3, 1)

        # Sparkle on success
        if progress > 0.8 and self._catch_anim.success:
            for i in range(6):
                angle = i * math.pi / 3 + progress * 10
                sx = bx + int(math.cos(angle) * 18 * (progress - 0.8) * 5)
                sy = by + int(math.sin(angle) * 18 * (progress - 0.8) * 5)
                pygame.draw.circle(surface, _GOLD, (sx, sy), 2)

    # ----- Text box -----
    def _draw_text_box(self, surface: pygame.Surface) -> None:
        """Draw the bottom text box with typewriter text."""
        box_x = 8
        box_y = GAME_H - 100
        box_w = GAME_W - 16
        box_h = 80

        # If the main menu is showing, shrink text box to left side
        if self.state == BattleState.PLAYER_TURN and not self._in_move_select:
            box_w = GAME_W - 250

        if self.state == BattleState.MOVE_SELECT or self._in_move_select:
            box_w = GAME_W - 250

        # Box background
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((248, 248, 240, 240))
        surface.blit(bg, (box_x, box_y))
        pygame.draw.rect(surface, _DARK_INK, (box_x, box_y, box_w, box_h), 2, border_radius=4)

        # Draw text lines
        text_font = self._font(13)
        visible = self._text_lines[-3:]
        for i, tw in enumerate(visible):
            text = tw.current_text
            # Truncate to fit
            max_chars = (box_w - 20) // 8
            if len(text) > max_chars:
                text = text[:max_chars]
            text_surf = text_font.render(text, True, _INK)
            surface.blit(text_surf, (box_x + 12, box_y + 10 + i * 22))

        # Advance indicator (bouncing triangle)
        if self._all_text_finished() and self.state in (
            BattleState.ANIMATION, BattleState.INTRO,
        ):
            tri_x = box_x + box_w - 18
            tri_y = box_y + box_h - 16
            bounce = int(math.sin(time.time() * 4) * 3)
            pygame.draw.polygon(
                surface, _DARK_INK,
                [
                    (tri_x, tri_y + bounce),
                    (tri_x + 8, tri_y + bounce),
                    (tri_x + 4, tri_y + 6 + bounce),
                ],
            )

    # ----- Main menu (FIGHT / CATCH / ITEM / RUN) -----
    def _draw_main_menu(self, surface: pygame.Surface) -> None:
        menu_x = GAME_W - 234
        menu_y = GAME_H - 100
        menu_w = 226
        menu_h = 80

        # Background
        bg = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
        bg.fill((248, 248, 240, 240))
        surface.blit(bg, (menu_x, menu_y))
        pygame.draw.rect(surface, _DARK_INK, (menu_x, menu_y, menu_w, menu_h), 2, border_radius=4)

        # Title bar
        title_font = self._font(10, bold=True)
        title = title_font.render("What will you do?", True, _MID_GREY)
        surface.blit(title, (menu_x + menu_w // 2 - title.get_width() // 2, menu_y + 3))

        # 2x2 grid
        option_font = self._font(14, bold=True)
        col_w = menu_w // 2
        row_h = 28
        labels = ["FIGHT", "CATCH", "ITEM", "RUN"]
        colors = [
            (220, 80, 60),    # Fight — red
            (60, 180, 100),   # Catch — green
            (220, 180, 60),   # Item — gold
            (60, 120, 220),   # Run — blue
        ]

        for i, (label, lc) in enumerate(zip(labels, colors)):
            col = i % 2
            row = i // 2
            ox = menu_x + col * col_w + 12
            oy = menu_y + 18 + row * row_h + 4

            is_sel = (i == self._menu_cursor)

            # Selection cursor triangle
            if is_sel:
                pygame.draw.polygon(
                    surface, _INK,
                    [(ox - 4, oy + 4), (ox + 4, oy + 8), (ox - 4, oy + 12)],
                )

            # Label
            color = lc if is_sel else _MID_GREY
            text = option_font.render(label, True, color)
            surface.blit(text, (ox + 8, oy + 1))

    # ----- Move selection menu (2x2 spell grid) -----
    def _draw_move_menu(self, surface: pygame.Surface) -> None:
        menu_x = GAME_W - 234
        menu_y = GAME_H - 100
        menu_w = 226
        menu_h = 80

        moves = self.player.spells[:4]
        if not moves:
            return

        # Background
        bg = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
        bg.fill((248, 248, 240, 240))
        surface.blit(bg, (menu_x, menu_y))
        pygame.draw.rect(surface, _DARK_INK, (menu_x, menu_y, menu_w, menu_h), 2, border_radius=4)

        col_w = menu_w // 2
        row_h = menu_h // 2 - 2

        for i, spell in enumerate(moves):
            col = i % 2
            row = i // 2
            ox = menu_x + col * col_w + 4
            oy = menu_y + row * row_h + 4

            is_sel = (i == self._move_cursor)

            # Tongue color strip on left edge
            tc = TONGUE_COLORS.get(spell.tongue.value, _MID_GREY)
            pygame.draw.rect(surface, tc, (ox, oy, 3, row_h - 4), border_radius=1)

            # Selection highlight
            if is_sel:
                sel_bg = pygame.Surface((col_w - 8, row_h - 4), pygame.SRCALPHA)
                sel_bg.fill((*tc, 40))
                surface.blit(sel_bg, (ox + 4, oy))
                # Cursor triangle
                pygame.draw.polygon(
                    surface, _INK,
                    [(ox + 4, oy + 6), (ox + 10, oy + 10), (ox + 4, oy + 14)],
                )

            # Move name
            name_font = self._font(11, bold=is_sel)
            max_name_len = 12
            display_name = spell.name[:max_name_len]
            name_color = _INK if is_sel else _MID_GREY
            name_surf = name_font.render(display_name, True, name_color)
            surface.blit(name_surf, (ox + 12, oy + 2))

            # PP and type
            pp_font = self._font(9)
            pp_text = f"PP {spell.mp_cost}"
            pp_surf = pp_font.render(pp_text, True, _MID_GREY)
            surface.blit(pp_surf, (ox + 12, oy + 18))

            # Effectiveness indicator for selected move
            if is_sel:
                mult, eff_label = BattleEngine.get_effectiveness(
                    spell.tongue, self.enemy.tongue_affinity,
                )
                if mult > 1.0:
                    eff_color = (40, 200, 40)
                    eff_text = "SE"  # Super Effective
                elif mult < 1.0:
                    eff_color = (200, 80, 80)
                    eff_text = "NVE"  # Not Very Effective
                else:
                    eff_color = _MID_GREY
                    eff_text = "--"  # Neutral
                eff_font = self._font(8, bold=True)
                eff_surf = eff_font.render(eff_text, True, eff_color)
                surface.blit(eff_surf, (ox + col_w - 34, oy + 18))

        # "Back" hint
        back_font = self._font(9)
        back_surf = back_font.render("[ESC] Back", True, _MID_GREY)
        surface.blit(back_surf, (menu_x + 4, menu_y + menu_h - 14))

        # Show type effectiveness legend for currently selected move
        sel_move = moves[self._move_cursor] if self._move_cursor < len(moves) else None
        if sel_move is not None:
            self._draw_effectiveness_banner(surface, sel_move)

    def _draw_effectiveness_banner(
        self, surface: pygame.Surface, spell: Spell,
    ) -> None:
        """Draw a small effectiveness indicator above the move menu."""
        mult, label = BattleEngine.get_effectiveness(
            spell.tongue, self.enemy.tongue_affinity,
        )
        if label == "neutral":
            return  # only show for non-neutral

        banner_w = 180
        banner_h = 18
        banner_x = GAME_W - 234
        banner_y = GAME_H - 122

        if label == "super effective":
            bg_color = (40, 180, 40, 160)
            text = "Super effective!"
            text_color = _WHITE
        else:
            bg_color = (180, 60, 60, 160)
            text = "Not very effective..."
            text_color = (255, 220, 220)

        bg = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        bg.fill(bg_color)
        surface.blit(bg, (banner_x, banner_y))
        pygame.draw.rect(surface, _DARK_INK, (banner_x, banner_y, banner_w, banner_h), 1, border_radius=2)

        font = self._font(11, bold=True)
        text_surf = font.render(text, True, text_color)
        surface.blit(
            text_surf,
            (banner_x + banner_w // 2 - text_surf.get_width() // 2,
             banner_y + 1),
        )

    # ----- Victory overlay -----
    def _draw_victory_overlay(self, surface: pygame.Surface) -> None:
        # Semi-transparent overlay
        overlay = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 80))
        surface.blit(overlay, (0, 0))

        # "VICTORY!" text with shadow
        big_font = self._font(28, bold=True)
        shadow = big_font.render("VICTORY!", True, (40, 32, 0))
        main = big_font.render("VICTORY!", True, _GOLD)
        cx = GAME_W // 2
        cy = GAME_H // 2 - 60
        surface.blit(shadow, (cx - shadow.get_width() // 2 + 2, cy + 2))
        surface.blit(main, (cx - main.get_width() // 2, cy))

        # XP info
        if self._victory_phase >= 1:
            xp_font = self._font(14)
            xp_text = xp_font.render(
                f"+{self.engine.xp_gained} XP", True, (200, 255, 200),
            )
            surface.blit(xp_text, (cx - xp_text.get_width() // 2, cy + 38))

        # Level up
        if self._victory_phase >= 2 and self.engine.levels_gained > 0:
            lvl_font = self._font(16, bold=True)
            lvl_text = lvl_font.render(
                f"Level Up! Now Lv{self.player.stats.level}",
                True, (255, 255, 120),
            )
            surface.blit(lvl_text, (cx - lvl_text.get_width() // 2, cy + 60))

        # New moves
        if self._victory_phase >= 2 and self.engine.learned_moves:
            move_font = self._font(12)
            for i, move in enumerate(self.engine.learned_moves):
                tc = TONGUE_COLORS.get(move.tongue.value, _WHITE)
                move_text = move_font.render(
                    f"Learned: {move.name}", True, tc,
                )
                surface.blit(
                    move_text,
                    (cx - move_text.get_width() // 2, cy + 84 + i * 18),
                )

        # Continue prompt
        if self._victory_phase >= 3:
            cont_font = self._font(11)
            cont = cont_font.render("Press ENTER to continue", True, (200, 200, 210))
            bounce = int(math.sin(time.time() * 3) * 2)
            surface.blit(cont, (cx - cont.get_width() // 2, cy + 130 + bounce))

    # ----- Defeat overlay -----
    def _draw_defeat_overlay(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        big_font = self._font(28, bold=True)
        text = big_font.render("DEFEAT...", True, HP_RED)
        cx = GAME_W // 2
        cy = GAME_H // 2 - 30
        surface.blit(text, (cx - text.get_width() // 2, cy))

        sub_font = self._font(12)
        sub = sub_font.render(f"{self.player.name} blacked out!", True, (200, 160, 160))
        surface.blit(sub, (cx - sub.get_width() // 2, cy + 40))

        if self._state_elapsed() > 1.0:
            cont_font = self._font(11)
            cont = cont_font.render("Press ENTER to continue", True, (180, 180, 190))
            bounce = int(math.sin(time.time() * 3) * 2)
            surface.blit(cont, (cx - cont.get_width() // 2, cy + 70 + bounce))


# ---------------------------------------------------------------------------
# Convenience: Start a Battle (helper for the main game)
# ---------------------------------------------------------------------------
def start_battle(
    player: Character,
    zone_tongue: Tongue,
    player_level: Optional[int] = None,
) -> BattleRenderer:
    """Create a BattleRenderer for a random wild encounter.

    Args:
        player: The player's active character.
        zone_tongue: The tongue element of the current zone.
        player_level: Override level for encounter scaling (defaults to player's level).

    Returns:
        A BattleRenderer ready to be driven by update()/draw().
    """
    level = player_level if player_level is not None else player.stats.level
    encounter = generate_wild_encounter(zone_tongue, level)
    return BattleRenderer(player, encounter)


# ---------------------------------------------------------------------------
# Self-Test / Demo (run this file directly to see the battle screen)
# ---------------------------------------------------------------------------
def _demo() -> None:
    """Run a standalone demo of the battle system."""
    pygame.init()
    screen = pygame.display.set_mode((GAME_W, GAME_H))
    pygame.display.set_caption("Aethermoor Battle Demo — Six Tongues Protocol")
    clock = pygame.time.Clock()

    # Create a test player
    player = Character(
        name="Izack",
        title="Dimensional Scholar",
        tongue_affinity=Tongue.CA,
        evo_stage=EvoStage.ROOKIE,
        stats=Stats(
            hp=120, max_hp=120, mp=80, max_mp=80,
            attack=12, defense=10, speed=11, wisdom=15,
            tongue_prof={"KO": 0.1, "AV": 0.05, "RU": 0.05, "CA": 0.3, "UM": 0.0, "DR": 0.05},
        ),
        spells=[
            Spell("Pocket Fold", Tongue.CA, 18, 8, "Store enemy in micro-dimension"),
            Spell("Dim. Shift", Tongue.CA, 25, 15, "Phase between planes"),
            Spell("Cipher Lock", Tongue.CA, 22, 12, "Encrypt and bind"),
            Spell("Overflow", Tongue.CA, 30, 18, "Computation overflow"),
        ],
    )

    # Random encounter
    zone = random.choice(list(Tongue))
    renderer = start_battle(player, zone)

    running = True
    while running:
        dt = clock.tick(30) / 1000.0
        events = pygame.event.get()
        for ev in events:
            if ev.type == pygame.QUIT:
                running = False
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False

        renderer.update(events, dt)
        renderer.draw(screen)
        pygame.display.flip()

        if renderer.finished:
            # Show result for a moment then exit
            pygame.time.wait(1500)
            print(f"\nBattle result: {renderer.result}")
            print(f"Player HP: {player.stats.hp}/{player.stats.max_hp}")
            print(f"XP gained: {renderer.engine.xp_gained}")
            if renderer.engine.levels_gained > 0:
                print(f"Levels gained: {renderer.engine.levels_gained}")
            if renderer.engine.learned_moves:
                print(f"Moves learned: {[m.name for m in renderer.engine.learned_moves]}")
            running = False

    pygame.quit()


if __name__ == "__main__":
    _demo()
