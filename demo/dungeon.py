#!/usr/bin/env python3
"""
Tower Dungeon Manager — Aethermoor RPG
=======================================
Manhwa-style (Solo Leveling) tower climbing system.

Procedurally generated floors with boss gates every 10 floors,
mini-bosses every 5, and themed regions cycling every 20 floors.

Tongue affinities per theme:
  CRYSTAL -> CA / DR    SHADOW -> UM / KO
  FIRE    -> DR / RU    DATA   -> AV / CA
"""

from __future__ import annotations

import random
from enum import Enum, IntEnum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from engine import Character, EvoStage, Spell, Stats, Tongue, TONGUE_CHART

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TILE_SIZE = 16


# ---------------------------------------------------------------------------
# Tile types (int8 encoding for the grid)
# ---------------------------------------------------------------------------
class Tile(IntEnum):
    EMPTY = 0
    FLOOR = 1
    WALL = 2
    MONSTER_SPAWN = 3
    EXIT_STAIR = 4
    CHEST = 5
    TRAP = 6


# ---------------------------------------------------------------------------
# Floor theme — cycles every 20 floors
# ---------------------------------------------------------------------------
class FloorTheme(Enum):
    CRYSTAL = "Crystal"
    SHADOW = "Shadow"
    FIRE = "Fire"
    DATA = "Data"


# Theme -> tongue affinity pairs for enemies
THEME_TONGUES: Dict[FloorTheme, Tuple[Tongue, Tongue]] = {
    FloorTheme.CRYSTAL: (Tongue.CA, Tongue.DR),
    FloorTheme.SHADOW: (Tongue.UM, Tongue.KO),
    FloorTheme.FIRE: (Tongue.DR, Tongue.RU),
    FloorTheme.DATA: (Tongue.AV, Tongue.CA),
}


# ---------------------------------------------------------------------------
# Boss name tables (per theme)
# ---------------------------------------------------------------------------
BOSS_NAMES: Dict[FloorTheme, List[str]] = {
    FloorTheme.CRYSTAL: [
        "Crystal Sentinel",
        "Prism Warden",
        "Geode Colossus",
        "Lattice Archon",
        "Shard Empress",
    ],
    FloorTheme.SHADOW: [
        "Shadow Baron",
        "Umbral Stalker",
        "Void Wraith",
        "Penumbra Knight",
        "Eclipse Tyrant",
    ],
    FloorTheme.FIRE: [
        "Flame Warden",
        "Ember Titan",
        "Inferno Djinn",
        "Magma Serpent",
        "Pyre Overlord",
    ],
    FloorTheme.DATA: [
        "Data Wraith",
        "Cipher Golem",
        "Protocol Hydra",
        "Binary Phantom",
        "Core Overseer",
    ],
}

GATE_BOSS_NAMES: Dict[FloorTheme, List[str]] = {
    FloorTheme.CRYSTAL: [
        "Crystal Gate Keeper",
        "Diamond Sovereign",
    ],
    FloorTheme.SHADOW: [
        "Shadow Gate Keeper",
        "Abyssal Monarch",
    ],
    FloorTheme.FIRE: [
        "Flame Gate Keeper",
        "Infernal Sovereign",
    ],
    FloorTheme.DATA: [
        "Data Gate Keeper",
        "Singularity Core",
    ],
}

# Enemy name prefixes / suffixes for normal mobs
ENEMY_PREFIXES: Dict[FloorTheme, List[str]] = {
    FloorTheme.CRYSTAL: ["Crystal", "Quartz", "Gem", "Prism", "Facet"],
    FloorTheme.SHADOW: ["Shadow", "Dark", "Umbral", "Dusk", "Gloom"],
    FloorTheme.FIRE: ["Flame", "Ember", "Scorch", "Blaze", "Cinder"],
    FloorTheme.DATA: ["Data", "Byte", "Pixel", "Circuit", "Signal"],
}

ENEMY_TYPES: List[str] = [
    "Slime",
    "Golem",
    "Wisp",
    "Wolf",
    "Drone",
    "Crawler",
    "Imp",
    "Shade",
    "Construct",
    "Elemental",
]


# ---------------------------------------------------------------------------
# Spell tables for enemies
# ---------------------------------------------------------------------------
THEME_SPELLS: Dict[FloorTheme, List[Spell]] = {
    FloorTheme.CRYSTAL: [
        Spell("Crystal Shard", Tongue.CA, 12, 6, "Fires a razor-sharp crystal fragment"),
        Spell("Prism Beam", Tongue.CA, 20, 10, "Focused light through crystal lattice"),
        Spell("Geode Crush", Tongue.DR, 18, 8, "Hurls a geode that shatters on impact"),
        Spell("Refraction", Tongue.DR, 15, 7, "Bends light to disorient the target"),
    ],
    FloorTheme.SHADOW: [
        Spell("Shadow Bolt", Tongue.UM, 14, 6, "A bolt of condensed shadow energy"),
        Spell("Umbral Drain", Tongue.UM, 22, 12, "Drains life force through darkness"),
        Spell("Dark Slash", Tongue.KO, 16, 7, "Blade wreathed in commanding shadow"),
        Spell("Night Veil", Tongue.KO, 10, 5, "Cloaks self in darkness, reducing accuracy"),
    ],
    FloorTheme.FIRE: [
        Spell("Fireball", Tongue.DR, 18, 8, "Classic ball of flame"),
        Spell("Magma Wave", Tongue.DR, 24, 12, "Sweeping wave of molten rock"),
        Spell("Ember Sting", Tongue.RU, 12, 5, "Quick burning jab"),
        Spell("Eruption", Tongue.RU, 28, 15, "Ground erupts beneath the target"),
    ],
    FloorTheme.DATA: [
        Spell("Packet Storm", Tongue.AV, 16, 7, "Rapid-fire data packets"),
        Spell("Buffer Overflow", Tongue.AV, 22, 11, "Overwhelms defenses with data"),
        Spell("Hash Collision", Tongue.CA, 20, 10, "Exploits compute weakness"),
        Spell("Defrag Pulse", Tongue.CA, 14, 6, "Reorganizes own data for a strike"),
    ],
}

BOSS_SPELLS: Dict[FloorTheme, List[Spell]] = {
    FloorTheme.CRYSTAL: [
        Spell("Diamond Storm", Tongue.CA, 35, 18, "Rain of diamond shards"),
        Spell("Lattice Prison", Tongue.DR, 28, 14, "Traps target in crystal lattice"),
        Spell("Resonance Shatter", Tongue.CA, 42, 22, "Devastating harmonic explosion"),
    ],
    FloorTheme.SHADOW: [
        Spell("Abyssal Gaze", Tongue.UM, 38, 18, "Paralyzing stare from the void"),
        Spell("Shadow Realm", Tongue.KO, 30, 15, "Drags target into shadow dimension"),
        Spell("Eclipse Burst", Tongue.UM, 45, 24, "Total darkness erupts outward"),
    ],
    FloorTheme.FIRE: [
        Spell("Inferno Breath", Tongue.DR, 40, 20, "Dragon-like breath of pure flame"),
        Spell("Pyroclasm", Tongue.RU, 34, 16, "Volcanic eruption centered on target"),
        Spell("Meltdown", Tongue.DR, 48, 25, "Nuclear-hot core detonation"),
    ],
    FloorTheme.DATA: [
        Spell("System Crash", Tongue.AV, 36, 18, "Forces catastrophic system failure"),
        Spell("Root Access", Tongue.CA, 32, 15, "Bypasses all defenses"),
        Spell("Zero-Day", Tongue.AV, 50, 26, "Exploits unknown vulnerability"),
    ],
}


# ---------------------------------------------------------------------------
# Floor difficulty formulas
# ---------------------------------------------------------------------------
def _base_hp(floor_num: int) -> int:
    """Base HP for enemies on a given floor."""
    return 30 + floor_num * 4


def _base_atk(floor_num: int) -> float:
    """Base attack stat for enemies on a given floor."""
    return 5.0 + floor_num * 1.5


def _evo_stage_for_floor(floor_num: int) -> EvoStage:
    """Determine evolution stage bracket based on floor number."""
    if floor_num <= 10:
        return EvoStage.FRESH
    elif floor_num <= 25:
        return EvoStage.ROOKIE
    elif floor_num <= 50:
        return EvoStage.CHAMPION
    elif floor_num <= 75:
        return EvoStage.ULTIMATE
    else:
        return EvoStage.MEGA


def _hp_range_for_floor(floor_num: int) -> Tuple[int, int]:
    """Return (min_hp, max_hp) for normal enemies on a given floor."""
    if floor_num <= 10:
        return (30, 60)
    elif floor_num <= 25:
        return (50, 100)
    elif floor_num <= 50:
        return (80, 150)
    else:
        return (120, 250)


def _theme_for_floor(floor_num: int) -> FloorTheme:
    """Determine floor theme based on floor number (cycles every 20)."""
    themes = list(FloorTheme)
    idx = ((floor_num - 1) // 20) % 4
    return themes[idx]


# ---------------------------------------------------------------------------
# Enemy generation
# ---------------------------------------------------------------------------
def generate_floor_enemies(floor_num: int, theme: FloorTheme) -> List[Character]:
    """Generate 2-5 enemy Characters scaled to floor difficulty.

    Parameters
    ----------
    floor_num : int
        Current floor number (1-indexed).
    theme : FloorTheme
        The theme of the current floor.

    Returns
    -------
    List[Character]
        A list of enemy characters for this floor.
    """
    hp_lo, hp_hi = _hp_range_for_floor(floor_num)
    evo = _evo_stage_for_floor(floor_num)
    base_hp = _base_hp(floor_num)
    base_atk = _base_atk(floor_num)
    tongue_a, tongue_b = THEME_TONGUES[theme]
    available_spells = THEME_SPELLS[theme]

    # Scale enemy count with floor depth
    min_enemies = 2
    max_enemies = min(5, 2 + floor_num // 10)
    count = random.randint(min_enemies, max_enemies)

    enemies: List[Character] = []
    prefixes = ENEMY_PREFIXES[theme]

    for i in range(count):
        tongue = tongue_a if i % 2 == 0 else tongue_b
        prefix = random.choice(prefixes)
        etype = random.choice(ENEMY_TYPES)
        name = f"{prefix} {etype}"

        hp = random.randint(hp_lo, hp_hi)
        hp = max(hp, base_hp)  # floor formula as minimum

        atk = int(base_atk + random.randint(-2, 4))
        defense = int(base_atk * 0.7 + random.randint(-1, 3))
        speed = random.randint(5, 8 + floor_num // 10)
        wisdom = random.randint(4, 7 + floor_num // 15)

        # Pick 1-2 spells matching this enemy's tongue
        matching = [s for s in available_spells if s.tongue == tongue]
        if not matching:
            matching = available_spells[:2]
        num_spells = random.randint(1, min(2, len(matching)))
        spells = random.sample(matching, num_spells)

        # Scale spell power with floor
        scaled_spells: List[Spell] = []
        for sp in spells:
            power_bonus = floor_num // 5
            scaled_spells.append(Spell(
                name=sp.name,
                tongue=sp.tongue,
                power=sp.power + power_bonus,
                mp_cost=sp.mp_cost,
                description=sp.description,
            ))

        enemy = Character(
            name=name,
            title=f"Floor {floor_num} {etype}",
            tongue_affinity=tongue,
            evo_stage=evo,
            stats=Stats(
                hp=hp,
                max_hp=hp,
                mp=30 + floor_num * 2,
                max_mp=30 + floor_num * 2,
                attack=atk,
                defense=defense,
                speed=speed,
                wisdom=wisdom,
            ),
            spells=scaled_spells,
            is_enemy=True,
        )
        enemies.append(enemy)

    return enemies


def generate_boss(floor_num: int, theme: FloorTheme) -> Character:
    """Generate a boss Character for the given floor.

    Every 5th floor spawns a boss. Every 10th floor is a gate boss
    with even higher stats and unique spells.

    Parameters
    ----------
    floor_num : int
        Current floor number (1-indexed).
    theme : FloorTheme
        The theme of the current floor.

    Returns
    -------
    Character
        A boss enemy character.
    """
    is_gate = (floor_num % 10 == 0)

    # Pick name
    if is_gate:
        names = GATE_BOSS_NAMES[theme]
    else:
        names = BOSS_NAMES[theme]
    name = names[(floor_num // 5 - 1) % len(names)]

    # Base stats scaled to floor
    base_hp = _base_hp(floor_num)
    base_atk = _base_atk(floor_num)

    hp_lo, hp_hi = _hp_range_for_floor(floor_num)
    normal_hp = max(random.randint(hp_lo, hp_hi), base_hp)

    # Bosses get 2-3x normal HP; gate bosses are stronger
    if is_gate:
        boss_hp = int(normal_hp * 3.0 + floor_num * 5)
        atk_mult = 2.5
        def_mult = 2.0
        title = f"Gate Boss — Floor {floor_num}"
    else:
        boss_hp = int(normal_hp * 2.0 + floor_num * 3)
        atk_mult = 1.8
        def_mult = 1.5
        title = f"Boss — Floor {floor_num}"

    atk = int(base_atk * atk_mult + floor_num * 0.5)
    defense = int(base_atk * def_mult)
    speed = 8 + floor_num // 8
    wisdom = 10 + floor_num // 5

    # Evolution stage (bosses run one tier higher)
    evo = _evo_stage_for_floor(floor_num)
    evo_order = [EvoStage.FRESH, EvoStage.ROOKIE, EvoStage.CHAMPION,
                 EvoStage.ULTIMATE, EvoStage.MEGA, EvoStage.ULTRA]
    evo_idx = evo_order.index(evo)
    boss_evo = evo_order[min(evo_idx + 1, len(evo_order) - 1)]

    # Tongue: primary of the theme
    tongue_a, tongue_b = THEME_TONGUES[theme]
    tongue = tongue_a

    # Spells: 2-3 powerful boss spells
    available = BOSS_SPELLS[theme]
    num_spells = random.randint(2, min(3, len(available)))
    spells_chosen = random.sample(available, num_spells)

    # Scale boss spell power with floor
    scaled_spells: List[Spell] = []
    for sp in spells_chosen:
        power_bonus = floor_num // 3
        scaled_spells.append(Spell(
            name=sp.name,
            tongue=sp.tongue,
            power=sp.power + power_bonus,
            mp_cost=sp.mp_cost,
            description=sp.description,
        ))

    # Gate bosses get an additional unique spell
    if is_gate and len(scaled_spells) < 3:
        gate_spell = Spell(
            name=f"{name}'s Wrath",
            tongue=tongue_b,
            power=40 + floor_num,
            mp_cost=20 + floor_num // 2,
            description=f"The gate boss unleashes devastating {tongue_b.value} energy",
        )
        scaled_spells.append(gate_spell)

    boss = Character(
        name=name,
        title=title,
        tongue_affinity=tongue,
        evo_stage=boss_evo,
        stats=Stats(
            hp=boss_hp,
            max_hp=boss_hp,
            mp=60 + floor_num * 3,
            max_mp=60 + floor_num * 3,
            attack=atk,
            defense=defense,
            speed=speed,
            wisdom=wisdom,
        ),
        spells=scaled_spells,
        is_enemy=True,
    )
    return boss


# ---------------------------------------------------------------------------
# DungeonFloor — procedurally generated floor layout
# ---------------------------------------------------------------------------
class DungeonFloor:
    """A single procedurally generated floor of the tower dungeon.

    Attributes
    ----------
    floor_num : int
        The floor number (1-indexed).
    width : int
        Grid width in tiles.
    height : int
        Grid height in tiles.
    tiles : np.ndarray
        int8 grid encoding tile types (see ``Tile`` enum).
    theme : FloorTheme
        Visual/elemental theme for this floor.
    is_boss_floor : bool
        True every 5th floor.
    is_gate_boss : bool
        True every 10th floor (harder boss).
    monsters : List[Dict[str, Any]]
        Monster spawn definitions with position and character template.
    cleared : bool
        Whether all monsters on this floor have been defeated.
    """

    def __init__(self, floor_num: int, width: int = 15, height: int = 15) -> None:
        self.floor_num: int = floor_num
        self.width: int = width
        self.height: int = height
        self.tiles: np.ndarray = np.zeros((height, width), dtype=np.int8)
        self.theme: FloorTheme = _theme_for_floor(floor_num)
        self.is_boss_floor: bool = (floor_num % 5 == 0)
        self.is_gate_boss: bool = (floor_num % 10 == 0)
        self.monsters: List[Dict[str, Any]] = []
        self.cleared: bool = False

    # ----- public API -----

    def generate(self) -> None:
        """Procedurally generate the floor layout.

        Algorithm:
          1. Fill entire grid with walls.
          2. Random-walk corridor from (1,1) carving floor tiles.
          3. Guarantee a path to the far corner for exit stair placement.
          4. Place border walls.
          5. Place monster spawn points.
          6. Place exit stair at the far end.
          7. Optionally place a chest (30% chance).
          8. On boss floors, carve a 5x5 open boss room.
        """
        # Step 1: fill with walls
        self.tiles.fill(Tile.WALL)

        # Step 2: random-walk corridor from (1,1)
        cx, cy = 1, 1
        self.tiles[cy, cx] = Tile.FLOOR
        steps = self.width * self.height * 2  # generous step count
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        for _ in range(steps):
            dx, dy = random.choice(directions)
            nx, ny = cx + dx, cy + dy
            if 1 <= nx < self.width - 1 and 1 <= ny < self.height - 1:
                self.tiles[ny, nx] = Tile.FLOOR
                cx, cy = nx, ny

        # Step 3: guarantee path to far corner (bottom-right region)
        target_x = self.width - 2
        target_y = self.height - 2
        px, py = cx, cy
        while px != target_x:
            px += 1 if px < target_x else -1
            if 1 <= px < self.width - 1 and 1 <= py < self.height - 1:
                self.tiles[py, px] = Tile.FLOOR
        while py != target_y:
            py += 1 if py < target_y else -1
            if 1 <= px < self.width - 1 and 1 <= py < self.height - 1:
                self.tiles[py, px] = Tile.FLOOR

        # Step 4: enforce border walls
        self.tiles[0, :] = Tile.WALL
        self.tiles[self.height - 1, :] = Tile.WALL
        self.tiles[:, 0] = Tile.WALL
        self.tiles[:, self.width - 1] = Tile.WALL

        # Step 5: place monster spawns
        self._place_monster_spawns()

        # Step 6: place exit stair at far end
        self.tiles[target_y, target_x] = Tile.EXIT_STAIR

        # Step 7: optional chest (30% chance)
        if random.random() < 0.30:
            self._place_chest()

        # Step 8: boss room on boss floors
        if self.is_boss_floor:
            self._carve_boss_room()

        # Step 9: generate enemy characters
        self._generate_monsters()

    def get_tile(self, x: int, y: int) -> int:
        """Return the tile type at (x, y). Out-of-bounds returns WALL."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return int(self.tiles[y, x])
        return int(Tile.WALL)

    def is_walkable(self, x: int, y: int) -> bool:
        """Return True if a character can walk on tile (x, y)."""
        tile = self.get_tile(x, y)
        return tile in (Tile.FLOOR, Tile.MONSTER_SPAWN, Tile.EXIT_STAIR,
                        Tile.CHEST, Tile.TRAP)

    # ----- private helpers -----

    def _floor_tiles(self) -> List[Tuple[int, int]]:
        """Return list of (x, y) coordinates that are floor tiles."""
        coords: List[Tuple[int, int]] = []
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.tiles[y, x] == Tile.FLOOR:
                    coords.append((x, y))
        return coords

    def _place_monster_spawns(self) -> None:
        """Place 2-5 monster spawn tiles on open floor spaces."""
        floor_coords = self._floor_tiles()
        if not floor_coords:
            return

        min_spawns = 2
        max_spawns = min(5, 2 + self.floor_num // 10)
        count = random.randint(min_spawns, max_spawns)
        count = min(count, len(floor_coords))

        # Prefer spawns away from start (1,1)
        floor_coords.sort(key=lambda c: (c[0] - 1) ** 2 + (c[1] - 1) ** 2,
                          reverse=True)
        # Take from the farther half, then shuffle for variety
        far_half = floor_coords[: len(floor_coords) // 2] or floor_coords
        random.shuffle(far_half)

        for x, y in far_half[:count]:
            self.tiles[y, x] = Tile.MONSTER_SPAWN

    def _place_chest(self) -> None:
        """Place a single chest tile on an open floor space."""
        floor_coords = self._floor_tiles()
        if floor_coords:
            x, y = random.choice(floor_coords)
            self.tiles[y, x] = Tile.CHEST

    def _carve_boss_room(self) -> None:
        """Carve a 5x5 open boss arena near the exit stair."""
        # Center the boss room near the bottom-right
        room_cx = min(self.width - 4, self.width - 2 - 2)
        room_cy = min(self.height - 4, self.height - 2 - 2)
        room_cx = max(3, room_cx)
        room_cy = max(3, room_cy)

        for dy in range(-2, 3):
            for dx in range(-2, 3):
                rx, ry = room_cx + dx, room_cy + dy
                if 1 <= rx < self.width - 1 and 1 <= ry < self.height - 1:
                    # Only overwrite walls / floor, preserve exit stair
                    if self.tiles[ry, rx] != Tile.EXIT_STAIR:
                        self.tiles[ry, rx] = Tile.FLOOR

        # Place a monster spawn in the center of the boss room
        if self.tiles[room_cy, room_cx] == Tile.FLOOR:
            self.tiles[room_cy, room_cx] = Tile.MONSTER_SPAWN

    def _generate_monsters(self) -> None:
        """Populate self.monsters from spawn tiles + floor enemies."""
        spawn_positions: List[Tuple[int, int]] = []
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y, x] == Tile.MONSTER_SPAWN:
                    spawn_positions.append((x, y))

        if self.is_boss_floor:
            # Boss floor: single boss (or gate boss)
            boss = generate_boss(self.floor_num, self.theme)
            # Place boss at first spawn point (or center of boss room)
            bx, by = spawn_positions[0] if spawn_positions else (
                self.width // 2, self.height // 2
            )
            self.monsters.append({
                "x": bx,
                "y": by,
                "character": boss,
                "alive": True,
                "is_boss": True,
            })
            # Gate bosses also get a couple of minions
            if self.is_gate_boss and len(spawn_positions) > 1:
                minions = generate_floor_enemies(self.floor_num, self.theme)
                for idx, (sx, sy) in enumerate(spawn_positions[1:]):
                    if idx < len(minions):
                        self.monsters.append({
                            "x": sx,
                            "y": sy,
                            "character": minions[idx],
                            "alive": True,
                            "is_boss": False,
                        })
        else:
            # Normal floor: distribute enemies across spawn points
            enemies = generate_floor_enemies(self.floor_num, self.theme)
            for idx, (sx, sy) in enumerate(spawn_positions):
                if idx < len(enemies):
                    self.monsters.append({
                        "x": sx,
                        "y": sy,
                        "character": enemies[idx],
                        "alive": True,
                        "is_boss": False,
                    })

    def __repr__(self) -> str:
        theme_str = self.theme.value
        boss_tag = " [GATE BOSS]" if self.is_gate_boss else (
            " [BOSS]" if self.is_boss_floor else ""
        )
        return (
            f"DungeonFloor(floor={self.floor_num}, theme={theme_str}, "
            f"{self.width}x{self.height}{boss_tag}, "
            f"monsters={len(self.monsters)}, cleared={self.cleared})"
        )


# ---------------------------------------------------------------------------
# TowerManager — manages the dungeon climbing session
# ---------------------------------------------------------------------------
class TowerManager:
    """Manages the player's progress through the tower dungeon.

    Attributes
    ----------
    current_floor : int
        The floor the player is currently on (0 = not in tower).
    highest_floor : int
        The highest floor the player has reached.
    floors : Dict[int, DungeonFloor]
        Cache of generated dungeon floors.
    floor_kills : int
        Number of monsters killed on the current floor.
    total_kills : int
        Total monsters killed across all floors this session.
    """

    def __init__(self) -> None:
        self.current_floor: int = 0
        self.highest_floor: int = 0
        self.floors: Dict[int, DungeonFloor] = {}
        self.floor_kills: int = 0
        self.total_kills: int = 0

    def enter_tower(self) -> DungeonFloor:
        """Enter the tower at floor 1.

        Returns
        -------
        DungeonFloor
            The generated (or cached) first floor.
        """
        self.current_floor = 1
        self.floor_kills = 0
        if self.current_floor > self.highest_floor:
            self.highest_floor = self.current_floor
        return self.generate_floor(1)

    def advance_floor(self) -> DungeonFloor:
        """Advance to the next floor.

        Returns
        -------
        DungeonFloor
            The generated (or cached) next floor.
        """
        self.current_floor += 1
        self.floor_kills = 0
        if self.current_floor > self.highest_floor:
            self.highest_floor = self.current_floor
        return self.generate_floor(self.current_floor)

    def retreat(self) -> Optional[DungeonFloor]:
        """Retreat to the previous floor (minimum floor 1).

        Returns
        -------
        Optional[DungeonFloor]
            The previous floor, or None if already at floor 1.
        """
        if self.current_floor <= 1:
            return self.get_current_floor()
        self.current_floor -= 1
        self.floor_kills = 0
        return self.generate_floor(self.current_floor)

    def get_current_floor(self) -> Optional[DungeonFloor]:
        """Get the current floor object.

        Returns
        -------
        Optional[DungeonFloor]
            The current floor, or None if not in the tower.
        """
        if self.current_floor <= 0:
            return None
        return self.floors.get(self.current_floor)

    def generate_floor(self, floor_num: int) -> DungeonFloor:
        """Generate and cache a dungeon floor.

        If the floor has already been generated, return the cached version.

        Parameters
        ----------
        floor_num : int
            Floor number to generate.

        Returns
        -------
        DungeonFloor
            The generated dungeon floor.
        """
        if floor_num not in self.floors:
            floor = DungeonFloor(floor_num)
            floor.generate()
            self.floors[floor_num] = floor
        return self.floors[floor_num]

    def record_kill(self) -> None:
        """Record a monster kill on the current floor."""
        self.floor_kills += 1
        self.total_kills += 1

    def is_floor_cleared(self) -> bool:
        """Check if all monsters on the current floor are defeated."""
        floor = self.get_current_floor()
        if floor is None:
            return False
        all_dead = all(not m["alive"] for m in floor.monsters)
        if all_dead:
            floor.cleared = True
        return all_dead

    def __repr__(self) -> str:
        return (
            f"TowerManager(current={self.current_floor}, "
            f"highest={self.highest_floor}, "
            f"kills={self.total_kills}, "
            f"cached_floors={len(self.floors)})"
        )


# ---------------------------------------------------------------------------
# Selftest / demo
# ---------------------------------------------------------------------------
def selftest() -> None:
    """Run a self-test of the dungeon system."""
    print(f"\n{'=' * 60}")
    print("  Aethermoor Tower Dungeon — Self-Test")
    print(f"{'=' * 60}\n")

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name} {detail}")

    # 1. Theme cycling
    check("Floor 1 -> CRYSTAL", _theme_for_floor(1) == FloorTheme.CRYSTAL)
    check("Floor 20 -> CRYSTAL", _theme_for_floor(20) == FloorTheme.CRYSTAL)
    check("Floor 21 -> SHADOW", _theme_for_floor(21) == FloorTheme.SHADOW)
    check("Floor 41 -> FIRE", _theme_for_floor(41) == FloorTheme.FIRE)
    check("Floor 61 -> DATA", _theme_for_floor(61) == FloorTheme.DATA)
    check("Floor 81 -> CRYSTAL (cycle)", _theme_for_floor(81) == FloorTheme.CRYSTAL)

    # 2. Floor generation
    floor1 = DungeonFloor(1)
    floor1.generate()
    check("Floor 1 created", floor1.floor_num == 1)
    check("Floor 1 has tiles", floor1.tiles.shape == (15, 15))
    check("Floor 1 not boss", not floor1.is_boss_floor)
    check("Floor 1 has monsters", len(floor1.monsters) > 0)
    check("Floor 1 theme is CRYSTAL", floor1.theme == FloorTheme.CRYSTAL)

    # Check border walls
    all_border_walls = True
    for x in range(floor1.width):
        if floor1.tiles[0, x] != Tile.WALL or floor1.tiles[floor1.height - 1, x] != Tile.WALL:
            all_border_walls = False
    for y in range(floor1.height):
        if floor1.tiles[y, 0] != Tile.WALL or floor1.tiles[y, floor1.width - 1] != Tile.WALL:
            all_border_walls = False
    check("Border walls intact", all_border_walls)

    # Check exit stair exists
    has_exit = np.any(floor1.tiles == Tile.EXIT_STAIR)
    check("Exit stair placed", has_exit)

    # Check walkability
    check("Wall not walkable", not floor1.is_walkable(0, 0))
    check("Out-of-bounds not walkable", not floor1.is_walkable(-1, -1))
    check("Start area walkable", floor1.is_walkable(1, 1))

    # 3. Boss floor
    floor5 = DungeonFloor(5)
    floor5.generate()
    check("Floor 5 is boss floor", floor5.is_boss_floor)
    check("Floor 5 not gate boss", not floor5.is_gate_boss)
    has_boss = any(m["is_boss"] for m in floor5.monsters)
    check("Floor 5 has a boss", has_boss)

    # 4. Gate boss floor
    floor10 = DungeonFloor(10)
    floor10.generate()
    check("Floor 10 is boss floor", floor10.is_boss_floor)
    check("Floor 10 is gate boss", floor10.is_gate_boss)
    has_gate_boss = any(m["is_boss"] for m in floor10.monsters)
    check("Floor 10 has gate boss", has_gate_boss)

    # 5. Enemy generation scaling
    enemies_f1 = generate_floor_enemies(1, FloorTheme.CRYSTAL)
    enemies_f50 = generate_floor_enemies(50, FloorTheme.FIRE)
    check("Floor 1 enemies 2-5", 2 <= len(enemies_f1) <= 5)
    check("Floor 50 enemies 2-5", 2 <= len(enemies_f50) <= 5)
    avg_hp_1 = sum(e.stats.hp for e in enemies_f1) / len(enemies_f1)
    avg_hp_50 = sum(e.stats.hp for e in enemies_f50) / len(enemies_f50)
    check("Floor 50 enemies stronger than Floor 1", avg_hp_50 > avg_hp_1,
          f"F1 avg HP={avg_hp_1:.0f}, F50 avg HP={avg_hp_50:.0f}")

    # 6. Boss generation
    boss_f5 = generate_boss(5, FloorTheme.CRYSTAL)
    boss_f10 = generate_boss(10, FloorTheme.CRYSTAL)
    check("Boss has name", len(boss_f5.name) > 0)
    check("Boss is enemy", boss_f5.is_enemy)
    check("Boss has spells", len(boss_f5.spells) >= 2)
    check("Gate boss HP > normal boss HP", boss_f10.stats.hp > boss_f5.stats.hp,
          f"Gate={boss_f10.stats.hp}, Normal={boss_f5.stats.hp}")

    # 7. TowerManager
    tower = TowerManager()
    check("Tower starts at floor 0", tower.current_floor == 0)

    f = tower.enter_tower()
    check("Enter tower -> floor 1", tower.current_floor == 1)
    check("Enter returns DungeonFloor", isinstance(f, DungeonFloor))

    f2 = tower.advance_floor()
    check("Advance -> floor 2", tower.current_floor == 2)
    check("Highest floor updated", tower.highest_floor == 2)

    tower.retreat()
    check("Retreat -> floor 1", tower.current_floor == 1)

    tower.retreat()
    check("Retreat at floor 1 stays 1", tower.current_floor == 1)

    tower.record_kill()
    tower.record_kill()
    check("Kills tracked", tower.total_kills == 2)
    check("Floor kills tracked", tower.floor_kills == 2)

    check("Get current floor works", tower.get_current_floor() is not None)

    # 8. Floor cache
    tower.generate_floor(3)
    tower.generate_floor(3)  # should return cached
    check("Floor caching works", 3 in tower.floors)
    check("Total cached floors", len(tower.floors) >= 3)

    # 9. Evo stage scaling
    check("Floor 1 -> FRESH", _evo_stage_for_floor(1) == EvoStage.FRESH)
    check("Floor 15 -> ROOKIE", _evo_stage_for_floor(15) == EvoStage.ROOKIE)
    check("Floor 30 -> CHAMPION", _evo_stage_for_floor(30) == EvoStage.CHAMPION)
    check("Floor 55 -> ULTIMATE", _evo_stage_for_floor(55) == EvoStage.ULTIMATE)
    check("Floor 80 -> MEGA", _evo_stage_for_floor(80) == EvoStage.MEGA)

    # 10. Tile repr
    check("Tile repr", repr(floor1).startswith("DungeonFloor("))

    # 11. Stress test: generate many floors
    for fn in [1, 5, 10, 20, 25, 40, 50, 60, 75, 100]:
        df = DungeonFloor(fn)
        df.generate()
        has_monsters = len(df.monsters) > 0
        check(f"Floor {fn:>3d} generates OK ({df.theme.value:>7s})", has_monsters,
              f"monsters={len(df.monsters)}")

    # ASCII preview of floor 1
    print(f"\n  Floor 1 ASCII preview ({floor1.width}x{floor1.height}):")
    tile_chars = {
        Tile.EMPTY: " ",
        Tile.FLOOR: ".",
        Tile.WALL: "#",
        Tile.MONSTER_SPAWN: "M",
        Tile.EXIT_STAIR: ">",
        Tile.CHEST: "$",
        Tile.TRAP: "^",
    }
    for y in range(floor1.height):
        row = "  "
        for x in range(floor1.width):
            t = floor1.tiles[y, x]
            row += tile_chars.get(Tile(t), "?")
        print(row)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}\n")
    if failed == 0:
        print("  Tower dungeon systems operational. Ascend when ready.\n")


if __name__ == "__main__":
    selftest()
