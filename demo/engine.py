#!/usr/bin/env python3
"""
Aethermoor: Six Tongues Protocol
================================
A Digimon/Pokemon Sapphire-style RPG that trains AI as a byproduct.

Characters from Issac Davis's lore (Everweave, Notion, SCBE):
  - Izack       : Protagonist, dimensional storage mage, research scholar
  - Polly       : Raven familiar, sarcastic wisdom, Wingscroll archive
  - Clay        : Sand golem companion, earth elemental, study buddy
  - Eldrin      : Cartographer, dimensional navigation
  - Aria        : Warrior-scholar, boundary magic + math
  - Zara        : Dragon-blooded engineer, fire + code
  - Kael Nightwhisper : Izack's son, prodigal shadow mage, torn loyalties

World: Aethermoor (floating islands), Avalon Academy, Spiral Spire,
       Timeless Observatory, World Tree (Pollyoneth)

Magic System: Six Sacred Tongues (KO, AV, RU, CA, UM, DR)
  mapped 1:1 to SCBE 14-layer governance pipeline.

Training Data: Every player choice generates SFT/DPO pairs.
  Every battle generates spectral/governance training examples.
  Every evolution generates curriculum progression data.

GBA Sapphire-era visuals: 240x160 native, scaled 3x to 720x480.
"""

from __future__ import annotations

import json
import math
import os
import random
import struct
import sys
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GAME_TITLE = "Aethermoor: Six Tongues Protocol"
NATIVE_W, NATIVE_H = 240, 160   # GBA resolution
SCALE = 3
SCREEN_W, SCREEN_H = NATIVE_W * SCALE, NATIVE_H * SCALE
FPS = 30
TILE_SIZE = 16

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_OUT = PROJECT_ROOT / "training-data" / "game_sessions"
TRAINING_OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Color Palette (Pokemon Sapphire inspired)
# ---------------------------------------------------------------------------
class Palette:
    BLACK     = (0, 0, 0)
    WHITE     = (255, 255, 255)
    BG_EARTH  = (42, 46, 58)       # Dark blue-grey (night earth)
    BG_AETHER = (68, 52, 120)      # Deep purple (Aethermoor sky)
    SKY_DAY   = (135, 206, 235)    # Light blue
    GRASS     = (56, 128, 56)      # Earth grass
    FLOAT_ISL = (88, 68, 148)      # Floating island purple
    WATER     = (64, 108, 200)     # Sapphire water

    # Tongue colors
    KO = (220, 60, 60)     # Red - Authority
    AV = (60, 180, 220)    # Cyan - Transport
    RU = (220, 180, 60)    # Gold - Policy
    CA = (60, 220, 120)    # Green - Compute
    UM = (140, 60, 220)    # Purple - Security
    DR = (220, 120, 60)    # Orange - Schema

    # UI
    UI_BG     = (16, 16, 32)
    UI_BORDER = (80, 80, 120)
    UI_TEXT   = (240, 240, 255)
    UI_SELECT = (255, 220, 80)
    HP_GREEN  = (80, 220, 80)
    HP_YELLOW = (220, 220, 60)
    HP_RED    = (220, 60, 60)
    XP_BLUE   = (60, 120, 220)

    TONGUE_COLORS = {
        "KO": KO, "AV": AV, "RU": RU,
        "CA": CA, "UM": UM, "DR": DR,
    }


# ---------------------------------------------------------------------------
# Sacred Tongues (magic system / Digimon elements)
# ---------------------------------------------------------------------------
class Tongue(Enum):
    KO = "KO"   # Kor'aelin  — Authority / Control
    AV = "AV"   # Avali      — Transport / Messaging
    RU = "RU"   # Runethic   — Policy / Constraints
    CA = "CA"   # Cassisivadan — Compute / Encryption
    UM = "UM"   # Umbroth    — Security / Secrets
    DR = "DR"   # Draumric   — Schema / Authentication

TONGUE_NAMES = {
    Tongue.KO: "Kor'aelin",
    Tongue.AV: "Avali",
    Tongue.RU: "Runethic",
    Tongue.CA: "Cassisivadan",
    Tongue.UM: "Umbroth",
    Tongue.DR: "Draumric",
}

PHI = (1 + math.sqrt(5)) / 2
TONGUE_WEIGHTS = {
    Tongue.KO: 1.0,
    Tongue.AV: PHI,
    Tongue.RU: PHI ** 2,
    Tongue.CA: PHI ** 3,
    Tongue.UM: PHI ** 4,
    Tongue.DR: PHI ** 5,
}

# Type effectiveness (like Pokemon) based on SCBE layer relationships
# Each tongue is strong against one, weak against another
TONGUE_CHART: Dict[Tongue, Dict[str, Tongue]] = {
    Tongue.KO: {"strong": Tongue.AV, "weak": Tongue.UM},
    Tongue.AV: {"strong": Tongue.CA, "weak": Tongue.KO},
    Tongue.RU: {"strong": Tongue.UM, "weak": Tongue.DR},
    Tongue.CA: {"strong": Tongue.DR, "weak": Tongue.AV},
    Tongue.UM: {"strong": Tongue.KO, "weak": Tongue.RU},
    Tongue.DR: {"strong": Tongue.RU, "weak": Tongue.CA},
}


# ---------------------------------------------------------------------------
# Evolution Stages (Digimon-style)
# ---------------------------------------------------------------------------
class EvoStage(Enum):
    FRESH    = "Fresh"       # Just hatched / baby
    ROOKIE   = "Rookie"      # Learning basics
    CHAMPION = "Champion"    # Mid-tier, one tongue mastered
    ULTIMATE = "Ultimate"    # Strong, multiple tongues
    MEGA     = "Mega"        # Fully evolved
    ULTRA    = "Ultra"       # Transcendent (post-game)


# ---------------------------------------------------------------------------
# Characters (from Everweave/Notion lore)
# ---------------------------------------------------------------------------
@dataclass
class Stats:
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    attack: int = 10
    defense: int = 10
    speed: int = 10
    wisdom: int = 10
    # Tongue proficiencies (0.0 to 1.0)
    tongue_prof: Dict[str, float] = field(default_factory=lambda: {
        t.value: 0.0 for t in Tongue
    })

    @property
    def level(self) -> int:
        total_prof = sum(self.tongue_prof.values())
        return max(1, int(total_prof * 10) + 1)

    @property
    def xp_to_next(self) -> float:
        total = sum(self.tongue_prof.values())
        next_level = (self.level) / 10.0
        return max(0.0, next_level - total)


@dataclass
class Spell:
    name: str
    tongue: Tongue
    power: int
    mp_cost: int
    description: str
    min_proficiency: float = 0.0


@dataclass
class Character:
    name: str
    title: str
    tongue_affinity: Tongue
    evo_stage: EvoStage
    stats: Stats
    spells: List[Spell] = field(default_factory=list)
    sprite_data: Optional[Dict[str, Any]] = None
    backstory: str = ""
    is_party_member: bool = False
    is_enemy: bool = False

    @property
    def display_name(self) -> str:
        return f"{self.name} [{self.evo_stage.value}]"


def create_cast() -> Dict[str, Character]:
    """Create the game's character roster from lore."""
    return {
        "izack": Character(
            name="Izack",
            title="Dimensional Scholar",
            tongue_affinity=Tongue.CA,
            evo_stage=EvoStage.ROOKIE,
            stats=Stats(hp=120, max_hp=120, mp=80, max_mp=80,
                       attack=8, defense=10, speed=9, wisdom=15),
            spells=[
                Spell("Pocket Fold", Tongue.CA, 15, 8,
                      "Store an enemy in a micro-dimension for 1 turn"),
                Spell("Dimensional Shift", Tongue.CA, 25, 15,
                      "Phase through attacks by shifting between planes"),
            ],
            backstory="A research scholar who discovered dimensional storage magic. "
                      "Believes in collaborative magic over lone genius. "
                      "Carries a pocket dimension as refuge and workshop.",
            is_party_member=True,
        ),
        "polly": Character(
            name="Polly",
            title="Fifth Circle Keeper",
            tongue_affinity=Tongue.KO,
            evo_stage=EvoStage.CHAMPION,
            stats=Stats(hp=60, max_hp=60, mp=120, max_mp=120,
                       attack=6, defense=5, speed=14, wisdom=20),
            spells=[
                Spell("Wingscroll Blast", Tongue.KO, 20, 10,
                      "Unleash archived knowledge as a searing beam"),
                Spell("Cosmic Familiar Bond", Tongue.KO, 0, 5,
                      "Share HP with bonded partner, heal 15% each"),
                Spell("Archive Recall", Tongue.DR, 30, 20,
                      "Recall an ancient technique — random powerful effect"),
            ],
            backstory="A raven familiar with cosmic wisdom and a sharp tongue. "
                      "Keeper of the Wingscrolls — a living historical archive. "
                      "'Recording History Before It Forgets Itself'",
            is_party_member=True,
        ),
        "clay": Character(
            name="Clay",
            title="Earth Sentinel",
            tongue_affinity=Tongue.RU,
            evo_stage=EvoStage.ROOKIE,
            stats=Stats(hp=180, max_hp=180, mp=30, max_mp=30,
                       attack=14, defense=18, speed=4, wisdom=6),
            spells=[
                Spell("Sand Wall", Tongue.RU, 0, 8,
                      "Raise a defensive barrier — +50% DEF for 2 turns"),
                Spell("Golem Slam", Tongue.RU, 30, 12,
                      "Crushing earth strike. Ignores 30% of enemy DEF"),
            ],
            backstory="A sand golem companion with elemental earth magic. "
                      "Loyal study buddy and cozy protector. "
                      "Naps on desks. Fueled by magic and caffeine.",
            is_party_member=True,
        ),
        "eldrin": Character(
            name="Eldrin",
            title="Cartographic Thaumaturge",
            tongue_affinity=Tongue.AV,
            evo_stage=EvoStage.CHAMPION,
            stats=Stats(hp=90, max_hp=90, mp=90, max_mp=90,
                       attack=12, defense=8, speed=13, wisdom=16),
            spells=[
                Spell("Ley Line Pulse", Tongue.AV, 22, 12,
                      "Channel a ley line's energy into a directed beam"),
                Spell("Portal Step", Tongue.AV, 0, 18,
                      "Open a short-range portal — guaranteed escape or reposition"),
                Spell("Cartographic Scan", Tongue.AV, 0, 6,
                      "Reveal enemy stats, weaknesses, and tongue alignment"),
            ],
            backstory="A magical cartographer who maps dimensions. "
                      "'Not All Who Wander Are Lost, Some Are Mapping Magic.' "
                      "Expert in dimensional navigation and ley line networks.",
            is_party_member=True,
        ),
        "aria": Character(
            name="Aria Ravencrest",
            title="Boundary Warden",
            tongue_affinity=Tongue.UM,
            evo_stage=EvoStage.CHAMPION,
            stats=Stats(hp=110, max_hp=110, mp=70, max_mp=70,
                       attack=16, defense=12, speed=11, wisdom=14),
            spells=[
                Spell("Boundary Slash", Tongue.UM, 28, 14,
                      "Cut through dimensional boundaries with a magic blade"),
                Spell("Equation Shield", Tongue.CA, 0, 10,
                      "Mathematical barrier — reflects 25% of incoming damage"),
                Spell("Warrior's Theorem", Tongue.UM, 35, 22,
                      "Solve an equation to find the perfect strike angle"),
            ],
            backstory="Warrior-scholar who solves problems with magic AND math. "
                      "Boundary magic specialist. Strong female mage representation. "
                      "'I Solve Problems With Magic AND Math'",
            is_party_member=True,
        ),
        "zara": Character(
            name="Zara Millwright",
            title="Dragon-Coded Engineer",
            tongue_affinity=Tongue.DR,
            evo_stage=EvoStage.CHAMPION,
            stats=Stats(hp=100, max_hp=100, mp=80, max_mp=80,
                       attack=14, defense=10, speed=12, wisdom=15),
            spells=[
                Spell("Dragonfire Compile", Tongue.DR, 32, 16,
                      "Breathe schema-fire that authenticates and burns"),
                Spell("Scale Armor", Tongue.DR, 0, 8,
                      "Dragon scales form protective circuit patterns"),
                Spell("Code Crack", Tongue.CA, 20, 12,
                      "Break through enemy defenses by decrypting their schema"),
            ],
            backstory="Dragon-blooded prodigy. Fire-Breathing and Code-Breaking. "
                      "Circuit patterns that look like dragon scales. "
                      "Engineer of Cassisivadan gear-runes.",
            is_party_member=True,
        ),
        "kael": Character(
            name="Kael Nightwhisper",
            title="Chrono-Shadow Drifter",
            tongue_affinity=Tongue.UM,
            evo_stage=EvoStage.ROOKIE,
            stats=Stats(hp=110, max_hp=110, mp=85, max_mp=85,
                       attack=12, defense=9, speed=16, wisdom=14),
            spells=[
                Spell("Shadow Step", Tongue.UM, 18, 10,
                      "Phase through obstacles using shadow concealment"),
                Spell("Timeline Hop", Tongue.RU, 25, 18,
                      "Slip between timelines -- appear anywhere in any era"),
                Spell("Temporal Echo", Tongue.RU, 20, 14,
                      "Summon a past or future self to fight alongside you"),
                Spell("Nightwhisper", Tongue.UM, 30, 20,
                      "Shadow whisper from across timelines -- disrupts focus"),
            ],
            backstory="Izack and Aria's youngest son. A time traveler with "
                      "Timeweaver lineage powers -- can hop between timelines "
                      "and appear in any era, any multiverse branch. This makes "
                      "him a recurring wild card who shows up when least expected. "
                      "Drawn to Umbroth shadow magic despite his father's light. "
                      "Not evil -- searching for his own identity across time itself. "
                      "Can appear as an ally, a rival, or a mysterious stranger "
                      "depending on which timeline version you encounter.",
            is_party_member=True,
        ),
        # --- Izack & Aria's other children ---
        "alexander": Character(
            name="Alexander",
            title="Third Thread Prodigy",
            tongue_affinity=Tongue.CA,
            evo_stage=EvoStage.ROOKIE,
            stats=Stats(hp=100, max_hp=100, mp=90, max_mp=90,
                       attack=10, defense=8, speed=11, wisdom=16),
            spells=[
                Spell("Integration Weave", Tongue.CA, 20, 12,
                      "Merge multiple tongue threads into one unified spell"),
                Spell("Shimmer Call", Tongue.DR, 25, 18,
                      "Summon dragon companion Malzeth'irun for a combined strike"),
            ],
            backstory="Izack and Aria's eldest son. A prodigy with Third Thread "
                      "integration magic -- the ability to weave multiple tongues "
                      "simultaneously. Heart-bonded with the dragon Malzeth'irun "
                      "(Shimmer). Diplomatic and empathetic. Represents the next "
                      "generation's evolution beyond individual tongue mastery.",
            is_party_member=True,
        ),
        "lyra": Character(
            name="Lyra",
            title="Harmony Weaver",
            tongue_affinity=Tongue.AV,
            evo_stage=EvoStage.FRESH,
            stats=Stats(hp=70, max_hp=70, mp=60, max_mp=60,
                       attack=6, defense=7, speed=10, wisdom=12),
            spells=[
                Spell("Harmony Ripple", Tongue.AV, 14, 8,
                      "Healing wave that resonates with allies' tongues"),
            ],
            backstory="Izack and Aria's daughter. Emerging mage with harmony focus. "
                      "Inherited Aria's gift for resonance healing.",
            is_party_member=True,
        ),
        "mira": Character(
            name="Mira",
            title="Pattern Dancer",
            tongue_affinity=Tongue.DR,
            evo_stage=EvoStage.FRESH,
            stats=Stats(hp=65, max_hp=65, mp=65, max_mp=65,
                       attack=7, defense=6, speed=12, wisdom=11),
            spells=[
                Spell("Pattern Glimpse", Tongue.DR, 12, 7,
                      "Read the underlying patterns of magic and reality"),
            ],
            backstory="Izack and Aria's daughter. Pattern dancer affinity -- sees "
                      "the weave of magic as dance. Rediscovering the Pattern "
                      "Dancer tradition from within the family.",
            is_party_member=True,
        ),
        "senna": Character(
            name="Senna",
            title="Growth Shaper",
            tongue_affinity=Tongue.CA,
            evo_stage=EvoStage.FRESH,
            stats=Stats(hp=75, max_hp=75, mp=55, max_mp=55,
                       attack=5, defense=8, speed=8, wisdom=13),
            spells=[
                Spell("Lifebloom", Tongue.CA, 10, 6,
                      "Nurture living things -- heal or grow plant barriers"),
            ],
            backstory="Izack and Aria's daughter. Tied to creative life energy "
                      "and the Growth Shapers. Symbolizes partnership with nature.",
            is_party_member=True,
        ),
        # --- Extended companions ---
        "grey": Character(
            name="Grey",
            title="Threshold Guardian",
            tongue_affinity=Tongue.RU,
            evo_stage=EvoStage.CHAMPION,
            stats=Stats(hp=160, max_hp=160, mp=40, max_mp=40,
                       attack=15, defense=20, speed=6, wisdom=10),
            spells=[
                Spell("Threshold Lock", Tongue.RU, 0, 12,
                      "Seal a portal or passage -- nothing enters or exits"),
                Spell("Guardian Strike", Tongue.RU, 28, 16,
                      "Heavy strike empowered by oath of protection"),
            ],
            backstory="Stoic threshold guardian and warrior. Defensive magic focus. "
                      "Guards portals between dimensions. Reform over revolution.",
            is_party_member=True,
        ),
        "shimmer": Character(
            name="Malzeth'irun",
            title="Dragon of Integration",
            tongue_affinity=Tongue.DR,
            evo_stage=EvoStage.CHAMPION,
            stats=Stats(hp=220, max_hp=220, mp=60, max_mp=60,
                       attack=20, defense=16, speed=15, wisdom=12),
            spells=[
                Spell("Aether Breath", Tongue.DR, 35, 20,
                      "Dragon fire infused with forge-tongue authority"),
                Spell("Heart Bond", Tongue.KO, 0, 10,
                      "Share strength with bonded partner Alexander"),
            ],
            backstory="Dragon companion heart-bonded to Alexander. True name "
                      "Malzeth'irun, called Shimmer. Integration magic unlocked "
                      "through the bonding rite. Post-singularity evolution.",
            is_party_member=True,
        ),
        # --- True antagonist ---
        "veyra": Character(
            name="Veyra",
            title="Shadow at the Gates",
            tongue_affinity=Tongue.UM,
            evo_stage=EvoStage.MEGA,
            stats=Stats(hp=300, max_hp=300, mp=150, max_mp=150,
                       attack=22, defense=16, speed=18, wisdom=20),
            spells=[
                Spell("Chaos Unweave", Tongue.UM, 35, 18,
                      "Unravel the pattern of any structured magic"),
                Spell("Entropic Dance", Tongue.DR, 40, 22,
                      "Beauty in destruction -- randomize enemy stats"),
                Spell("Pattern Break", Tongue.CA, 45, 25,
                      "Shatter the Pattern Dancer tradition's foundations"),
                Spell("Shadow Gate", Tongue.UM, 55, 30,
                      "Open a gate to pure chaos -- devastating area attack"),
            ],
            backstory="The true antagonist. Shadow at the Gates. Chaos and "
                      "randomness seeker from the Pattern Dancers. Believes "
                      "beauty lies in entropy, not order. Seeks to unweave "
                      "the governance fabric of Aethermoor itself. Potential "
                      "for a reform arc -- not purely evil, just fundamentally "
                      "opposed to structure.",
            is_enemy=True,
        ),
    }


# ---------------------------------------------------------------------------
# Sprite Generator (GBA Sapphire-style pixel art)
# ---------------------------------------------------------------------------

def generate_sprite(character: Character, size: int = 32) -> np.ndarray:
    """Generate a GBA-style pixel sprite for a character.

    Returns an RGBA numpy array of shape (size, size, 4).
    Uses the character's tongue affinity for color palette.
    """
    sprite = np.zeros((size, size, 4), dtype=np.uint8)
    base_color = Palette.TONGUE_COLORS.get(character.tongue_affinity.value, Palette.WHITE)

    # Color variations
    r, g, b = base_color
    dark = (max(0, r - 60), max(0, g - 60), max(0, b - 60))
    light = (min(255, r + 60), min(255, g + 60), min(255, b + 60))
    skin = (220, 180, 140)
    eye = Palette.WHITE

    if character.name == "Polly":
        _draw_raven(sprite, size, base_color, dark, light)
    elif character.name == "Clay":
        _draw_golem(sprite, size, base_color, dark, light)
    elif character.name == "Malzeth'irun":
        _draw_dragon(sprite, size, base_color, dark, light)
    elif character.is_enemy:
        _draw_villain(sprite, size, base_color, dark, light)
    else:
        _draw_humanoid(sprite, size, base_color, dark, light, skin, eye)

    return sprite


def _set_pixel(sprite: np.ndarray, x: int, y: int, color: tuple, alpha: int = 255):
    """Set a pixel with bounds checking."""
    h, w = sprite.shape[:2]
    if 0 <= x < w and 0 <= y < h:
        sprite[y, x] = (*color, alpha)


def _draw_rect(sprite: np.ndarray, x: int, y: int, w: int, h: int, color: tuple, alpha: int = 255):
    """Draw filled rectangle."""
    for dy in range(h):
        for dx in range(w):
            _set_pixel(sprite, x + dx, y + dy, color, alpha)


def _draw_humanoid(sprite: np.ndarray, size: int, base: tuple, dark: tuple, light: tuple,
                   skin: tuple, eye: tuple):
    """Draw a humanoid character sprite (Izack, Eldrin, Aria, Zara)."""
    s = size
    cx = s // 2

    # Head
    head_w, head_h = s // 4, s // 4
    head_x = cx - head_w // 2
    head_y = s // 6
    _draw_rect(sprite, head_x, head_y, head_w, head_h, skin)

    # Hair
    _draw_rect(sprite, head_x - 1, head_y - 1, head_w + 2, 3, dark)

    # Eyes
    _set_pixel(sprite, cx - 2, head_y + head_h // 2, eye)
    _set_pixel(sprite, cx + 1, head_y + head_h // 2, eye)

    # Body / armor
    body_y = head_y + head_h
    body_h = s // 3
    body_w = s // 3
    body_x = cx - body_w // 2
    _draw_rect(sprite, body_x, body_y, body_w, body_h, base)
    # Belt/detail
    _draw_rect(sprite, body_x, body_y + body_h - 2, body_w, 2, dark)

    # Arms
    arm_w = 3
    _draw_rect(sprite, body_x - arm_w, body_y + 2, arm_w, body_h - 4, base)
    _draw_rect(sprite, body_x + body_w, body_y + 2, arm_w, body_h - 4, base)

    # Legs
    leg_y = body_y + body_h
    leg_h = s - leg_y - 2
    leg_w = body_w // 2 - 1
    _draw_rect(sprite, cx - leg_w - 1, leg_y, leg_w, leg_h, dark)
    _draw_rect(sprite, cx + 1, leg_y, leg_w, leg_h, dark)

    # Boots
    _draw_rect(sprite, cx - leg_w - 2, leg_y + leg_h - 2, leg_w + 1, 2, (80, 60, 40))
    _draw_rect(sprite, cx, leg_y + leg_h - 2, leg_w + 1, 2, (80, 60, 40))

    # Tongue glow effect (shoulder pads)
    _set_pixel(sprite, body_x - 1, body_y, light)
    _set_pixel(sprite, body_x + body_w, body_y, light)


def _draw_raven(sprite: np.ndarray, size: int, base: tuple, dark: tuple, light: tuple):
    """Draw Polly the raven familiar."""
    s = size
    cx, cy = s // 2, s // 2

    # Body (oval-ish)
    for dy in range(-4, 5):
        for dx in range(-3, 4):
            if dx * dx + dy * dy < 18:
                _set_pixel(sprite, cx + dx, cy + dy, (30, 30, 40))

    # Wings
    for i in range(6):
        _set_pixel(sprite, cx - 4 - i, cy - 1 + i // 2, dark)
        _set_pixel(sprite, cx + 4 + i, cy - 1 + i // 2, dark)

    # Head
    _draw_rect(sprite, cx - 2, cy - 5, 4, 3, (30, 30, 40))

    # Eyes (glowing with tongue color)
    _set_pixel(sprite, cx - 1, cy - 4, base)
    _set_pixel(sprite, cx + 1, cy - 4, base)

    # Beak
    _set_pixel(sprite, cx, cy - 3, (200, 160, 40))
    _set_pixel(sprite, cx, cy - 2, (200, 160, 40))

    # Tail feathers
    for i in range(3):
        _set_pixel(sprite, cx - 1 + i, cy + 5, dark)
        _set_pixel(sprite, cx - 1 + i, cy + 6, (20, 20, 30))

    # Cosmic sparkle
    for _ in range(4):
        sx = cx + random.randint(-6, 6)
        sy = cy + random.randint(-6, 6)
        _set_pixel(sprite, sx, sy, light, 180)


def _draw_golem(sprite: np.ndarray, size: int, base: tuple, dark: tuple, light: tuple):
    """Draw Clay the sand golem."""
    s = size
    cx, cy = s // 2, s // 2

    sand = (194, 168, 120)
    sand_dark = (150, 130, 90)
    sand_light = (220, 200, 160)

    # Big blocky body
    body_w, body_h = s // 2, s // 2
    _draw_rect(sprite, cx - body_w // 2, cy - body_h // 4, body_w, body_h, sand)

    # Head (smaller block on top)
    head_w = body_w - 4
    _draw_rect(sprite, cx - head_w // 2, cy - body_h // 4 - 5, head_w, 6, sand)

    # Eyes (glowing)
    _set_pixel(sprite, cx - 2, cy - body_h // 4 - 3, base)
    _set_pixel(sprite, cx + 2, cy - body_h // 4 - 3, base)

    # Arms (thick)
    arm_y = cy - 1
    _draw_rect(sprite, cx - body_w // 2 - 4, arm_y, 4, 8, sand_dark)
    _draw_rect(sprite, cx + body_w // 2, arm_y, 4, 8, sand_dark)

    # Legs (stubby)
    leg_y = cy + body_h * 3 // 4 - 2
    _draw_rect(sprite, cx - 4, leg_y, 3, 4, sand_dark)
    _draw_rect(sprite, cx + 1, leg_y, 3, 4, sand_dark)

    # Runic markings
    for i in range(3):
        _set_pixel(sprite, cx - 3 + i * 3, cy, base)
        _set_pixel(sprite, cx - 3 + i * 3, cy + 2, light)

    # Sand particles
    for _ in range(5):
        px = cx + random.randint(-8, 8)
        py = cy + random.randint(-2, 10)
        _set_pixel(sprite, px, py, sand_light, 140)


def _draw_dragon(sprite: np.ndarray, size: int, base: tuple, dark: tuple, light: tuple):
    """Draw Malzeth'irun / Shimmer dragon sprite."""
    s = size
    cx, cy = s // 2, s // 2

    # Body (large oval)
    for dy in range(-5, 6):
        for dx in range(-6, 7):
            if dx * dx * 0.6 + dy * dy < 30:
                _set_pixel(sprite, cx + dx, cy + dy + 2, base)

    # Head (forward)
    _draw_rect(sprite, cx + 5, cy - 3, 5, 4, base)
    _set_pixel(sprite, cx + 8, cy - 2, (255, 200, 40))  # eye

    # Wings
    for i in range(8):
        _set_pixel(sprite, cx - 2 + i, cy - 5 - i // 2, dark)
        _set_pixel(sprite, cx - 2 + i, cy - 4 - i // 2, dark)
        _set_pixel(sprite, cx + 2 - i, cy - 5 - i // 2, dark)
        _set_pixel(sprite, cx + 2 - i, cy - 4 - i // 2, dark)

    # Tail
    for i in range(6):
        _set_pixel(sprite, cx - 6 - i, cy + 3 + i // 2, dark)

    # Fire breath sparkles
    for _ in range(3):
        fx = cx + 9 + random.randint(0, 3)
        fy = cy - 2 + random.randint(-1, 1)
        _set_pixel(sprite, fx, fy, (255, 120, 40), 200)


def _draw_villain(sprite: np.ndarray, size: int, base: tuple, dark: tuple, light: tuple):
    """Draw antagonist villain sprite (Veyra, etc)."""
    s = size
    cx = s // 2

    # Hooded cloak (triangular)
    for row in range(s - 4):
        width = min(row // 2 + 2, s // 2)
        for dx in range(-width, width + 1):
            _set_pixel(sprite, cx + dx, 4 + row, (20, 10, 30))

    # Face shadow under hood
    _draw_rect(sprite, cx - 3, 8, 6, 5, (10, 5, 15))

    # Glowing eyes
    _set_pixel(sprite, cx - 2, 10, (255, 40, 40))
    _set_pixel(sprite, cx + 1, 10, (255, 40, 40))

    # Phase effect (dithered edges)
    for i in range(s):
        if i % 3 == 0:
            _set_pixel(sprite, cx - s // 4 + random.randint(-1, 1), 4 + i % (s - 6), base, 100)
            _set_pixel(sprite, cx + s // 4 + random.randint(-1, 1), 4 + i % (s - 6), base, 100)


# ---------------------------------------------------------------------------
# Battle System (Pokemon/Digimon style)
# ---------------------------------------------------------------------------

@dataclass
class BattleAction:
    actor: str
    action_type: str  # "spell", "attack", "defend", "item"
    spell: Optional[Spell] = None
    target: Optional[str] = None
    damage: int = 0
    message: str = ""


def calculate_damage(attacker: Character, defender: Character,
                     spell: Optional[Spell] = None) -> Tuple[int, str, bool]:
    """Calculate damage with tongue type effectiveness."""
    if spell:
        base = spell.power + attacker.stats.wisdom // 2
        tongue = spell.tongue
    else:
        base = attacker.stats.attack
        tongue = attacker.tongue_affinity

    # Type effectiveness
    effectiveness = 1.0
    msg_suffix = ""
    is_crit = False

    chart = TONGUE_CHART.get(tongue, {})
    if chart.get("strong") == defender.tongue_affinity:
        effectiveness = 1.5
        msg_suffix = " It's super effective!"
    elif chart.get("weak") == defender.tongue_affinity:
        effectiveness = 0.5
        msg_suffix = " Not very effective..."

    # Proficiency bonus
    if spell:
        prof = attacker.stats.tongue_prof.get(tongue.value, 0.0)
        effectiveness *= (1.0 + prof * 0.5)

    # Defense reduction
    defense = defender.stats.defense
    if spell:
        defense = defense * 0.7  # spells partially bypass defense

    # Random variance
    variance = random.uniform(0.85, 1.15)

    # Critical hit (5% base, +proficiency%)
    crit_chance = 0.05 + attacker.stats.tongue_prof.get(
        tongue.value if spell else attacker.tongue_affinity.value, 0.0) * 0.1
    if random.random() < crit_chance:
        effectiveness *= 1.5
        is_crit = True
        msg_suffix += " Critical hit!"

    damage = max(1, int((base * effectiveness - defense * 0.3) * variance))

    action_name = spell.name if spell else "Attack"
    msg = f"{attacker.name} used {action_name}! {damage} damage!{msg_suffix}"

    return damage, msg, is_crit


# ---------------------------------------------------------------------------
# Training Data Export (SFT/DPO pairs from gameplay)
# ---------------------------------------------------------------------------

class TrainingExporter:
    """Exports gameplay decisions as SFT/DPO training pairs."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.pairs: List[Dict[str, Any]] = []

    def record_choice(self, context: str, choice_made: str,
                      alternatives: List[str], outcome: str,
                      category: str = "game_choice") -> None:
        """Record a player choice as an SFT pair."""
        self.pairs.append({
            "instruction": f"In the world of Aethermoor, {context} What do you do?",
            "response": f"I choose to {choice_made}. {outcome}",
            "metadata": {
                "source": "aethermoor_game",
                "session": self.session_id,
                "category": category,
                "alternatives": alternatives,
                "timestamp": time.time(),
            }
        })

    def record_battle(self, attacker: str, defender: str,
                      action: str, damage: int, tongue: str,
                      effectiveness: str) -> None:
        """Record a battle action as training data."""
        self.pairs.append({
            "instruction": f"In battle, {attacker} faces {defender}. "
                          f"What is the optimal action using {tongue} tongue magic?",
            "response": f"{attacker} uses {action} dealing {damage} damage. "
                       f"Effectiveness: {effectiveness}. "
                       f"The {tongue} tongue governs this interaction through "
                       f"the SCBE governance layer.",
            "metadata": {
                "source": "aethermoor_battle",
                "session": self.session_id,
                "category": "battle_training",
                "tongue": tongue,
                "damage": damage,
            }
        })

    def record_evolution(self, character: str, from_stage: str,
                        to_stage: str, tongues_mastered: Dict[str, float]) -> None:
        """Record an evolution event."""
        self.pairs.append({
            "instruction": f"Describe {character}'s evolution from {from_stage} to {to_stage}.",
            "response": f"{character} has evolved from {from_stage} to {to_stage}! "
                       f"Tongue proficiencies: {tongues_mastered}. "
                       f"This reflects growing mastery of the Six Sacred Tongues protocol.",
            "metadata": {
                "source": "aethermoor_evolution",
                "session": self.session_id,
                "category": "evolution_training",
                "from_stage": from_stage,
                "to_stage": to_stage,
            }
        })

    def save(self) -> str:
        """Save all pairs to JSONL."""
        path = TRAINING_OUT / f"session_{self.session_id}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for pair in self.pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")
        return str(path)

    @property
    def total_pairs(self) -> int:
        return len(self.pairs)


# ---------------------------------------------------------------------------
# Game State
# ---------------------------------------------------------------------------
class GamePhase(Enum):
    EARTH_MORNING  = auto()   # Wake up on Earth
    EARTH_WORK     = auto()   # Go through a day of work
    EARTH_EVENING  = auto()   # Come home
    EARTH_NIGHT    = auto()   # Read a book, go to sleep
    TRANSIT        = auto()   # Transition to Aethermoor
    AETHERMOOR     = auto()   # The isekai world
    BATTLE         = auto()   # Battle mode
    EVOLUTION      = auto()   # Evolution sequence
    MENU           = auto()   # Pause menu
    OVERWORLD      = auto()   # Tile-based overworld exploration
    DUNGEON        = auto()   # Tower dungeon climbing
    PARTY_SELECT   = auto()   # Party member selection screen
    DIALOGUE       = auto()   # NPC dialogue / PivotKnowledge interaction


@dataclass
class GameState:
    phase: GamePhase = GamePhase.EARTH_MORNING
    party: List[Character] = field(default_factory=list)
    location: str = "Izack's Apartment"
    day: int = 1
    time_of_day: str = "morning"
    dialogue_queue: List[str] = field(default_factory=list)
    current_dialogue_idx: int = 0
    choices: List[Tuple[str, str]] = field(default_factory=list)  # (label, action)
    selected_choice: int = 0
    in_battle: bool = False
    battle_enemies: List[Character] = field(default_factory=list)
    exporter: TrainingExporter = field(default_factory=TrainingExporter)
    flags: Dict[str, Any] = field(default_factory=dict)

    def add_dialogue(self, *lines: str) -> None:
        self.dialogue_queue.extend(lines)
        self.current_dialogue_idx = 0

    def set_choices(self, choices: List[Tuple[str, str]]) -> None:
        self.choices = choices
        self.selected_choice = 0

    def clear(self) -> None:
        self.dialogue_queue.clear()
        self.choices.clear()
        self.current_dialogue_idx = 0
        self.selected_choice = 0


# ---------------------------------------------------------------------------
# Scene Scripts (the isekai day cycle)
# ---------------------------------------------------------------------------

def scene_earth_morning(state: GameState) -> None:
    """Wake up on Earth. A normal day."""
    state.location = "Izack's Apartment"
    state.time_of_day = "morning"
    state.add_dialogue(
        f"Day {state.day}. Your alarm goes off at 6:47 AM.",
        "The apartment is small but functional. Terminal glowing in the corner.",
        "You check your phone. Three missed messages from the research team.",
        "Another day at the Systems Architecture division.",
    )
    state.set_choices([
        ("Check the terminal first", "check_terminal"),
        ("Get coffee, messages can wait", "get_coffee"),
        ("Go back to sleep (5 more minutes...)", "snooze"),
    ])


def scene_earth_work(state: GameState) -> None:
    """A day at work. Systems engineering."""
    state.location = "Research Lab"
    state.time_of_day = "afternoon"
    state.add_dialogue(
        "The lab hums with server racks and the soft glow of monitors.",
        "You're debugging an authentication anomaly in the routing logs.",
        "Something feels off. The patterns don't match any known protocol.",
        "Your colleague mentions the word 'dimensional' and laughs.",
        "But the routing patterns... they look like they're folding into themselves.",
    )
    state.set_choices([
        ("Trace the anomaly deeper", "trace_anomaly"),
        ("Document and escalate to security", "escalate"),
        ("Ignore it, probably just clock drift", "ignore"),
    ])


def scene_earth_evening(state: GameState) -> None:
    """Come home. Wind down."""
    state.location = "Izack's Apartment"
    state.time_of_day = "evening"
    state.add_dialogue(
        "Home. The apartment feels different tonight.",
        "Your research notes are scattered across the desk.",
        "The book on the shelf catches your eye: 'An Introduction to",
        "Dimensional Magic: Storage Spaces' — wait, that wasn't there before.",
    )
    state.set_choices([
        ("Read the book", "read_book"),
        ("Check if someone broke in", "check_apartment"),
        ("Just go to bed, you're exhausted", "go_to_bed"),
    ])


def scene_earth_night(state: GameState) -> None:
    """Read the book. Fall asleep. The transition begins."""
    state.location = "Izack's Apartment"
    state.time_of_day = "night"
    state.add_dialogue(
        "The book is warm to the touch.",
        "Six languages you've never seen. Six tongues of power.",
        "KO... AV... RU... CA... UM... DR...",
        "The words blur. The room darkens.",
        "You hear a voice: 'What do you intend?'",
        "Your eyes close. The spiral turns.",
    )
    state.set_choices([
        ("'I intend to understand.'", "intent_understand"),
        ("'I intend to protect.'", "intent_protect"),
        ("'I intend to create.'", "intent_create"),
    ])


def scene_transit(state: GameState) -> None:
    """The isekai transition."""
    state.add_dialogue(
        "...",
        "Reality collapses.",
        "You feel yourself falling through protocol space.",
        "Location is authorization-dependent here.",
        "Existence is continuously verified.",
        "...",
        "You wake on a floating island, bathed in purple light.",
        "A raven perches on a crystalline branch, watching you.",
    )


def scene_aethermoor_arrival(state: GameState) -> None:
    """Arrive in Aethermoor. Meet Polly."""
    state.location = "Aethermoor - Arrival Platform"
    state.time_of_day = "twilight"

    cast = create_cast()
    polly = cast["polly"]
    clay = cast["clay"]

    state.add_dialogue(
        "POLLY: 'CAW! Finally. You were expected by the Protocol.'",
        "POLLY: 'I am Polly, Fifth Circle Keeper of the Archives.'",
        "POLLY: 'And you, Izack, are late.'",
        "A sand golem shuffles toward you, eyes glowing warm gold.",
        "CLAY: *happy grinding noises*",
        "POLLY: 'That's Clay. He's... enthusiastic.'",
        "POLLY: 'Listen well. Survival here requires learning the",
        "Six Sacred Tongues. Magic here is protocol architecture,",
        "not folklore spellcraft.'",
        f"POLLY: 'You currently know {sum(1 for v in state.party[0].stats.tongue_prof.values() if v > 0)} tongues.'",
        "POLLY: 'Let's fix that.'",
    )

    # Add Polly and Clay to party
    if not any(c.name == "Polly" for c in state.party):
        state.party.append(polly)
    if not any(c.name == "Clay" for c in state.party):
        state.party.append(clay)

    state.set_choices([
        ("'Teach me everything.'", "learn_tongues"),
        ("'Where am I? What is this place?'", "ask_about_world"),
        ("'How do I get home?'", "ask_go_home"),
    ])


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Run a comprehensive self-test of all game systems."""
    print(f"\n{'=' * 60}")
    print(f"  {GAME_TITLE} — Self-Test")
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
            print(f"  FAIL  {name} {detail}")

    # 1. Character creation
    cast = create_cast()
    check("Character roster", len(cast) == 14, f"Expected 14, got {len(cast)}")
    check("Izack exists", "izack" in cast)
    check("Polly exists", "polly" in cast)
    check("Clay exists", "clay" in cast)
    check("Kael is Izack's son", cast["kael"].is_party_member)
    check("Veyra is enemy", cast["veyra"].is_enemy)
    check("Alexander exists", "alexander" in cast)
    check("Shimmer exists", "shimmer" in cast)
    check("Izack is party", cast["izack"].is_party_member)

    # 2. Tongue system
    check("6 tongues defined", len(Tongue) == 6)
    check("Tongue weights scale by phi",
          abs(TONGUE_WEIGHTS[Tongue.AV] - PHI) < 0.01)
    check("Type chart completeness",
          all(t in TONGUE_CHART for t in Tongue))

    # 3. Sprite generation
    for name, char in cast.items():
        sprite = generate_sprite(char)
        check(f"Sprite {name}", sprite.shape == (32, 32, 4),
              f"Shape: {sprite.shape}")
        has_pixels = np.any(sprite[:, :, 3] > 0)
        check(f"Sprite {name} not empty", has_pixels)

    # 4. Battle system
    izack = cast["izack"]
    kael = cast["kael"]
    dmg, msg, crit = calculate_damage(izack, kael, izack.spells[0])
    check("Battle damage > 0", dmg > 0, f"Damage: {dmg}")
    check("Battle message", len(msg) > 10, msg)

    # Type effectiveness
    # KO is strong against AV
    attacker = cast["polly"]  # KO affinity
    defender = Character("Test", "Test", Tongue.AV, EvoStage.ROOKIE,
                        Stats(defense=5))
    dmg_strong, _, _ = calculate_damage(attacker, defender, attacker.spells[0])
    defender2 = Character("Test2", "Test2", Tongue.UM, EvoStage.ROOKIE,
                         Stats(defense=5))
    dmg_weak, _, _ = calculate_damage(attacker, defender2, attacker.spells[0])
    check("Type effectiveness works", dmg_strong > dmg_weak,
          f"Strong: {dmg_strong}, Weak: {dmg_weak}")

    # 5. Evolution stages
    check("6 evolution stages", len(EvoStage) == 6)

    # 6. Training data export
    exporter = TrainingExporter("test_session")
    exporter.record_choice(
        "you find a mysterious book on your shelf",
        "read the book",
        ["ignore it", "throw it away"],
        "The book reveals knowledge of the Six Sacred Tongues.",
    )
    exporter.record_battle("Izack", "Kael", "Pocket Fold", 15, "CA", "neutral")
    exporter.record_evolution("Izack", "Rookie", "Champion",
                            {"KO": 0.3, "CA": 0.8})
    check("Training pairs generated", exporter.total_pairs == 3)
    path = exporter.save()
    check("Training data saved", Path(path).exists())

    # 7. Game state
    state = GameState()
    state.party.append(cast["izack"])
    scene_earth_morning(state)
    check("Morning scene has dialogue", len(state.dialogue_queue) > 0)
    check("Morning scene has choices", len(state.choices) > 0)

    scene_earth_work(state)
    check("Work scene has dialogue", len(state.dialogue_queue) > 4)

    # 8. Scene flow
    for scene_fn in [scene_earth_morning, scene_earth_work,
                     scene_earth_evening, scene_earth_night,
                     scene_transit]:
        state.clear()
        scene_fn(state)
        check(f"Scene {scene_fn.__name__}",
              len(state.dialogue_queue) > 0)

    # 9. Game phases
    check("13 game phases", len(GamePhase) == 13)

    # 10. Palette colors
    check("6 tongue colors", len(Palette.TONGUE_COLORS) == 6)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}\n")

    if failed == 0:
        print("  All systems operational. Aethermoor awaits.\n")

    # Save a sprite sheet preview
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, len(cast), figsize=(len(cast) * 2, 2.5))
        for ax, (name, char) in zip(axes, cast.items()):
            sprite = generate_sprite(char)
            ax.imshow(sprite)
            ax.set_title(f"{char.name}\n{char.evo_stage.value}", fontsize=8)
            ax.axis("off")
        fig.suptitle("Aethermoor Character Sprites", fontsize=12)
        fig.tight_layout()
        plots_dir = PROJECT_ROOT / "training-data" / "audio" / "plots"
        plots_dir.mkdir(parents=True, exist_ok=True)
        sprite_path = str(plots_dir / "aethermoor_sprites.png")
        fig.savefig(sprite_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Sprite sheet saved: {sprite_path}")
    except Exception as e:
        print(f"  (Sprite sheet preview skipped: {e})")


if __name__ == "__main__":
    selftest()
