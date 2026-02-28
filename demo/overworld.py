#!/usr/bin/env python3
"""
Overworld Manager — Tile-based exploration for Aethermoor.

Manages the overworld state: player movement on tile maps, NPC placement,
random encounters in grass zones, warp tile transitions, and NPC interaction.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pygame

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from engine import (
    Character, EvoStage, Palette, Spell, Stats, Tongue,
    TONGUE_CHART, TONGUE_NAMES, create_cast, generate_sprite,
)
from tilemap import (
    TileMap, Camera, TileType, TILE_SIZE,
    GEOGRAPHY_PACK_RETURN_TILE,
    MAP_DEFINITIONS,
    generate_tile_surfaces,
)
from player import PlayerSprite, NPCSprite, Direction


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ENCOUNTER_CHANCE = 0.08  # 8% per step on encounter tiles
INTERACTION_RANGE = 24   # pixels


# ---------------------------------------------------------------------------
# NPC Placement Data
# ---------------------------------------------------------------------------
@dataclass
class NPCPlacement:
    """Where to place an NPC on a specific map."""
    npc_id: str
    character_key: str
    tile_x: int
    tile_y: int
    facing: Direction = Direction.DOWN
    wander: bool = False
    dialogue_id: str = ""


# Default NPC placements per map
MAP_NPC_PLACEMENTS: Dict[str, List[NPCPlacement]] = {
    "guild_hub": [
        NPCPlacement("polly", "polly", 18, 8, Direction.DOWN, False, "polly_hub"),
        NPCPlacement("clay", "clay", 20, 12, Direction.LEFT, True, "clay_hub"),
        NPCPlacement("eldrin", "eldrin", 10, 6, Direction.RIGHT, False, "eldrin_hub"),
        NPCPlacement("aria", "aria", 28, 14, Direction.DOWN, False, "aria_hub"),
        NPCPlacement("zara", "zara", 14, 18, Direction.UP, True, "zara_hub"),
        NPCPlacement("kael", "kael", 32, 8, Direction.LEFT, False, "kael_hub"),
    ],
    "avalon_academy": [
        NPCPlacement("polly", "polly", 14, 6, Direction.DOWN, False, "polly_academy"),
        NPCPlacement("eldrin", "eldrin", 6, 12, Direction.RIGHT, False, "eldrin_academy"),
        NPCPlacement("aria", "aria", 22, 12, Direction.LEFT, False, "aria_academy"),
    ],
    "spiral_tower_entrance": [
        NPCPlacement("grey", "grey", 10, 8, Direction.DOWN, False, "grey_tower"),
    ],
}


# ---------------------------------------------------------------------------
# Encounter Table
# ---------------------------------------------------------------------------
_ZONE_ENCOUNTER_BALANCE: Dict[str, Dict[str, Any]] = {
    "guild_hub": {
        "danger": 1.0,
        "count_weights": (0.4, 0.4, 0.2),
        "variance": (0.8, 1.2),
    },
    "avalon_academy": {
        "danger": 1.05,
        "count_weights": (0.35, 0.4, 0.25),
        "variance": (0.85, 1.2),
    },
    "spiral_tower_entrance": {
        "danger": 1.15,
        "count_weights": (0.3, 0.4, 0.3),
        "variance": (0.9, 1.25),
    },
    "geography_pack_meadow": {
        "danger": 0.82,
        "count_weights": (0.7, 0.25, 0.05),
        "variance": (0.75, 1.05),
    },
    "geography_pack_wetlands": {
        "danger": 0.95,
        "count_weights": (0.5, 0.35, 0.15),
        "variance": (0.8, 1.15),
    },
    "geography_pack_highlands": {
        "danger": 1.25,
        "count_weights": (0.25, 0.45, 0.3),
        "variance": (0.95, 1.3),
    },
    "geography_pack_deepwood": {
        "danger": 1.12,
        "count_weights": (0.3, 0.45, 0.25),
        "variance": (0.9, 1.25),
    },
}


def _encounter_zone_key(map_name: str) -> str:
    """Resolve map name to an encounter balance/pool key."""
    if map_name in _ZONE_ENCOUNTER_BALANCE:
        return map_name
    if map_name.startswith("geography_pack_"):
        return "geography_pack_meadow"
    return "guild_hub"


def generate_wild_encounter(map_name: str, player_level: int) -> List[Character]:
    """Generate random wild enemies for a map encounter."""
    zone_key = _encounter_zone_key(map_name)
    zone_cfg = _ZONE_ENCOUNTER_BALANCE[zone_key]

    danger = float(zone_cfg["danger"])
    variance_min, variance_max = zone_cfg["variance"]
    base_hp = max(16, int((30 + player_level * 5) * danger))
    base_atk = max(4, int((5 + player_level) * danger))

    # Pick 1-3 enemies using zone tier weights
    count = random.choices([1, 2, 3], weights=zone_cfg["count_weights"])[0]

    enemies: List[Character] = []
    monster_pool = _MONSTER_POOL.get(map_name, _MONSTER_POOL[zone_key])

    for _ in range(count):
        template = random.choice(monster_pool)
        tongue = template["tongue"]
        variance = random.uniform(variance_min, variance_max)
        hp = int(base_hp * variance)
        enemy = Character(
            name=template["name"],
            title=template["title"],
            tongue_affinity=tongue,
            evo_stage=template.get("stage", EvoStage.FRESH),
            stats=Stats(
                hp=hp, max_hp=hp,
                mp=20 + player_level * 2,
                max_mp=20 + player_level * 2,
                attack=max(3, int(base_atk * variance)),
                defense=max(2, int((base_atk - 2) * variance)),
                speed=max(4, int(8 * variance)),
                wisdom=max(3, int(6 * variance)),
            ),
            spells=[Spell(
                template["spell_name"], tongue,
                max(8, int(12 * variance)), 6,
                template["spell_desc"],
            )],
            is_enemy=True,
        )
        enemies.append(enemy)

    return enemies


_MONSTER_POOL: Dict[str, List[Dict[str, Any]]] = {
    "guild_hub": [
        {"name": "Grass Wisp", "title": "Wild Creature", "tongue": Tongue.CA,
         "spell_name": "Spark Burst", "spell_desc": "A crackling green spark",
         "stage": EvoStage.FRESH},
        {"name": "Rune Beetle", "title": "Wild Creature", "tongue": Tongue.DR,
         "spell_name": "Shell Crack", "spell_desc": "Crack open defenses",
         "stage": EvoStage.FRESH},
        {"name": "Shadow Mote", "title": "Wild Creature", "tongue": Tongue.UM,
         "spell_name": "Dark Pulse", "spell_desc": "A pulse of shadow energy",
         "stage": EvoStage.FRESH},
        {"name": "Wind Sprite", "title": "Wild Creature", "tongue": Tongue.AV,
         "spell_name": "Gust Slice", "spell_desc": "A cutting wind blade",
         "stage": EvoStage.FRESH},
    ],
    "avalon_academy": [
        {"name": "Ink Phantom", "title": "Academy Pest", "tongue": Tongue.DR,
         "spell_name": "Blot Strike", "spell_desc": "Splatter of enchanted ink",
         "stage": EvoStage.ROOKIE},
        {"name": "Rune Golem", "title": "Academy Guardian", "tongue": Tongue.RU,
         "spell_name": "Stone Fist", "spell_desc": "A heavy runic punch",
         "stage": EvoStage.ROOKIE},
        {"name": "Spark Elemental", "title": "Escaped Experiment", "tongue": Tongue.CA,
         "spell_name": "Arc Bolt", "spell_desc": "Chain lightning between targets",
         "stage": EvoStage.ROOKIE},
    ],
    "spiral_tower_entrance": [
        {"name": "Gate Shade", "title": "Tower Guard", "tongue": Tongue.UM,
         "spell_name": "Void Touch", "spell_desc": "Drains life force on contact",
         "stage": EvoStage.ROOKIE},
        {"name": "Crystal Crawler", "title": "Tower Creature", "tongue": Tongue.CA,
         "spell_name": "Prism Beam", "spell_desc": "Refracted light attack",
         "stage": EvoStage.ROOKIE},
    ],
    "geography_pack_meadow": [
        {"name": "Sprout Cub", "title": "Field Forager", "tongue": Tongue.CA,
         "spell_name": "Leaf Flick", "spell_desc": "Whips a fan of sharp leaves",
         "stage": EvoStage.FRESH},
        {"name": "Pebble Hopper", "title": "Grassland Scout", "tongue": Tongue.RU,
         "spell_name": "Skip Stone", "spell_desc": "Ricocheting stones strike twice",
         "stage": EvoStage.FRESH},
        {"name": "Mist Finch", "title": "Morning Flier", "tongue": Tongue.AV,
         "spell_name": "Dew Gust", "spell_desc": "A cool gust laced with dew",
         "stage": EvoStage.FRESH},
    ],
    "geography_pack_wetlands": [
        {"name": "Reed Lurker", "title": "Bog Creature", "tongue": Tongue.UM,
         "spell_name": "Marsh Grasp", "spell_desc": "Shadows drag at your footing",
         "stage": EvoStage.FRESH},
        {"name": "Bog Toadlet", "title": "Fen Hunter", "tongue": Tongue.DR,
         "spell_name": "Mud Volley", "spell_desc": "Dense mud impacts in bursts",
         "stage": EvoStage.ROOKIE},
        {"name": "Ripple Serpent", "title": "Shallow Predator", "tongue": Tongue.AV,
         "spell_name": "Tide Lash", "spell_desc": "A water lash from nearby pools",
         "stage": EvoStage.ROOKIE},
    ],
    "geography_pack_highlands": [
        {"name": "Cliff Ram", "title": "Mountain Charger", "tongue": Tongue.RU,
         "spell_name": "Ridge Crush", "spell_desc": "A crushing downhill rush",
         "stage": EvoStage.ROOKIE},
        {"name": "Ember Roc", "title": "Crag Soarer", "tongue": Tongue.KO,
         "spell_name": "Searing Dive", "spell_desc": "A burning aerial strike",
         "stage": EvoStage.ROOKIE},
        {"name": "Granite Lynx", "title": "Pass Stalker", "tongue": Tongue.DR,
         "spell_name": "Fault Claw", "spell_desc": "Splits stone and armor alike",
         "stage": EvoStage.ROOKIE},
    ],
    "geography_pack_deepwood": [
        {"name": "Thorn Stalker", "title": "Forest Ambusher", "tongue": Tongue.CA,
         "spell_name": "Bramble Snare", "spell_desc": "Vines bind and bite",
         "stage": EvoStage.ROOKIE},
        {"name": "Dusk Howler", "title": "Canopy Predator", "tongue": Tongue.UM,
         "spell_name": "Echo Wail", "spell_desc": "A fearsome sonic burst",
         "stage": EvoStage.ROOKIE},
        {"name": "Hollow Treant", "title": "Ancient Sentinel", "tongue": Tongue.RU,
         "spell_name": "Root Breaker", "spell_desc": "Roots erupt from below",
         "stage": EvoStage.ROOKIE},
    ],
}


# ---------------------------------------------------------------------------
# Warp Definitions
# ---------------------------------------------------------------------------
@dataclass
class WarpTarget:
    """Destination when stepping on a warp tile."""
    target_map: str
    target_x: int
    target_y: int


MAP_WARPS: Dict[str, Dict[Tuple[int, int], WarpTarget]] = {
    "guild_hub": {
        (20, 2): WarpTarget("avalon_academy", 14, 22),
        (35, 15): WarpTarget("spiral_tower_entrance", 10, 16),
    },
    "avalon_academy": {
        (14, 23): WarpTarget("guild_hub", 20, 3),
    },
    "spiral_tower_entrance": {
        (10, 17): WarpTarget("guild_hub", 35, 14),
        # (10, 3) -> enters dungeon (handled separately)
    },
}

GEOGRAPHY_HUB_WARP_LINKS: Dict[str, Tuple[Tuple[int, int], Tuple[int, int]]] = {
    "geography_pack_meadow": ((22, 26), (22, 25)),
    "geography_pack_wetlands": ((26, 26), (26, 25)),
    "geography_pack_highlands": ((30, 26), (30, 25)),
    "geography_pack_deepwood": ((34, 26), (34, 25)),
}
for zone_name, (hub_tile, hub_return_tile) in GEOGRAPHY_HUB_WARP_LINKS.items():
    MAP_WARPS.setdefault("guild_hub", {})[hub_tile] = WarpTarget(
        zone_name,
        GEOGRAPHY_PACK_RETURN_TILE[0],
        GEOGRAPHY_PACK_RETURN_TILE[1],
    )
    MAP_WARPS.setdefault(zone_name, {})[GEOGRAPHY_PACK_RETURN_TILE] = WarpTarget(
        "guild_hub",
        hub_return_tile[0],
        hub_return_tile[1],
    )


# ---------------------------------------------------------------------------
# Overworld Manager
# ---------------------------------------------------------------------------
class OverworldManager:
    """Manages tile-based overworld exploration."""

    def __init__(self) -> None:
        self.active: bool = False
        self.current_map_name: str = "guild_hub"

        # Tile system
        self.tile_surfaces: Dict[int, pygame.Surface] = {}
        self.maps: Dict[str, TileMap] = {}
        self.camera: Optional[Camera] = None

        # Player
        self.player: Optional[PlayerSprite] = None
        self.player_character: Optional[Character] = None

        # NPCs
        self.npcs: List[NPCSprite] = []
        self.cast: Dict[str, Character] = {}

        # State
        self.step_counter: int = 0
        self.encounter_pending: bool = False
        self.pending_enemies: List[Character] = []
        self.warp_pending: bool = False
        self.pending_warp: Optional[WarpTarget] = None
        self.npc_interaction_pending: bool = False
        self.pending_npc_id: str = ""
        self.dungeon_entry_pending: bool = False

        # Visual
        self.initialized: bool = False

    def initialize(self, player_character: Character, view_w: int = 640, view_h: int = 480) -> None:
        """Initialize the overworld system. Call after pygame.init()."""
        self.cast = create_cast()
        self.player_character = player_character
        self.tile_surfaces = generate_tile_surfaces()

        # Build maps (static + procedural pack)
        self.maps = {name: builder() for name, builder in MAP_DEFINITIONS.items()}
        self._apply_geography_hub_warp_tiles()

        # Create player sprite
        start_map = self.maps[self.current_map_name]
        self.player = PlayerSprite(
            player_character,
            start_map.width // 2 * TILE_SIZE,
            start_map.height // 2 * TILE_SIZE,
        )

        # Create camera (takes tile counts, not pixels)
        self.camera = Camera(
            start_map.width,
            start_map.height,
            view_w, view_h,
        )

        # Place NPCs
        self._place_npcs(self.current_map_name)

        self.initialized = True

    def enter(self, map_name: str = "guild_hub", x: int = -1, y: int = -1) -> None:
        """Enter the overworld on a specific map."""
        self.active = True
        self.current_map_name = map_name
        self.encounter_pending = False
        self.warp_pending = False
        self.npc_interaction_pending = False
        self.dungeon_entry_pending = False

        if map_name not in self.maps:
            builder = MAP_DEFINITIONS.get(map_name, MAP_DEFINITIONS["guild_hub"])
            self.maps[map_name] = builder()  # fallback
            if map_name == "guild_hub":
                self._apply_geography_hub_warp_tiles()

        tilemap = self.maps[map_name]

        # Position player
        if self.player:
            if x >= 0 and y >= 0:
                self.player.world_x = float(x * TILE_SIZE)
                self.player.world_y = float(y * TILE_SIZE)
            else:
                self.player.world_x = float(tilemap.width // 2 * TILE_SIZE)
                self.player.world_y = float(tilemap.height // 2 * TILE_SIZE)

        # Update camera bounds (Camera uses tile dimensions internally)
        if self.camera:
            self.camera.map_width = tilemap.width
            self.camera.map_height = tilemap.height

        # Place NPCs
        self._place_npcs(map_name)

    def leave(self) -> None:
        """Leave the overworld."""
        self.active = False

    def update(self, dt: float, dx: int, dy: int, interact: bool) -> None:
        """Update the overworld state.

        Args:
            dt: Delta time in seconds.
            dx: Horizontal input (-1, 0, +1).
            dy: Vertical input (-1, 0, +1).
            interact: Whether the player pressed the interact button.
        """
        if not self.active or not self.player or not self.camera:
            return

        tilemap = self.maps.get(self.current_map_name)
        if not tilemap:
            return

        # Track previous tile position
        prev_tx = self.player.tile_x
        prev_ty = self.player.tile_y

        # Move player
        self.player.update(dt, dx, dy, tilemap)

        # Camera follow
        self.camera.follow(self.player.world_x, self.player.world_y, dt)

        # Update NPCs
        for npc in self.npcs:
            npc.update(dt)

        # Check if player moved to a new tile
        new_tx = self.player.tile_x
        new_ty = self.player.tile_y
        stepped_new_tile = (new_tx != prev_tx or new_ty != prev_ty) and (dx != 0 or dy != 0)

        if stepped_new_tile:
            self.step_counter += 1
            tile_type = tilemap.get_tile(new_tx, new_ty)

            # Check encounter zones
            if tile_type == TileType.ENCOUNTER:
                if random.random() < ENCOUNTER_CHANCE:
                    player_level = self.player_character.stats.level if self.player_character else 1
                    self.pending_enemies = generate_wild_encounter(
                        self.current_map_name, player_level
                    )
                    self.encounter_pending = True

            # Check warp tiles
            elif tile_type == TileType.WARP:
                warps = MAP_WARPS.get(self.current_map_name, {})
                warp = warps.get((new_tx, new_ty))
                if warp:
                    self.pending_warp = warp
                    self.warp_pending = True

            # Check stair tiles (dungeon entry)
            elif tile_type == TileType.STAIR_UP:
                self.dungeon_entry_pending = True

            # Check events
            event = tilemap.get_event(new_tx, new_ty)
            if event:
                pass  # Events handled by game controller

        # NPC interaction
        if interact and self.player:
            for npc in self.npcs:
                if npc.is_near(self.player.world_x, self.player.world_y, INTERACTION_RANGE):
                    self.pending_npc_id = npc.npc_id
                    self.npc_interaction_pending = True
                    # Face the NPC toward the player
                    pdx = self.player.world_x - npc.world_x
                    pdy = self.player.world_y - npc.world_y
                    if abs(pdx) > abs(pdy):
                        npc.facing = Direction.RIGHT if pdx > 0 else Direction.LEFT
                    else:
                        npc.facing = Direction.DOWN if pdy > 0 else Direction.UP
                    break

    def consume_encounter(self) -> List[Character]:
        """Consume and return a pending encounter."""
        enemies = self.pending_enemies
        self.pending_enemies = []
        self.encounter_pending = False
        return enemies

    def consume_warp(self) -> Optional[WarpTarget]:
        """Consume and return a pending warp."""
        warp = self.pending_warp
        self.pending_warp = None
        self.warp_pending = False
        return warp

    def consume_npc_interaction(self) -> str:
        """Consume and return a pending NPC interaction ID."""
        npc_id = self.pending_npc_id
        self.pending_npc_id = ""
        self.npc_interaction_pending = False
        return npc_id

    def consume_dungeon_entry(self) -> bool:
        """Consume dungeon entry flag."""
        result = self.dungeon_entry_pending
        self.dungeon_entry_pending = False
        return result

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the overworld onto the given surface."""
        if not self.active or not self.camera:
            return

        tilemap = self.maps.get(self.current_map_name)
        if not tilemap:
            return

        # Draw tile map
        tilemap.draw(surface, self.camera, self.tile_surfaces)

        # Camera offset as tuple for sprite draw methods
        cam_offset = (int(self.camera.x), int(self.camera.y))

        # Draw NPCs
        for npc in self.npcs:
            npc.draw(surface, cam_offset)

        # Draw player
        if self.player:
            self.player.draw(surface, cam_offset)

        # Draw interaction prompts
        self._draw_interaction_hints(surface)

    def _apply_geography_hub_warp_tiles(self) -> None:
        """Stamp geography-pack warp tiles onto the guild hub map."""
        hub = self.maps.get("guild_hub")
        if not hub:
            return
        for hub_tile, _hub_return_tile in GEOGRAPHY_HUB_WARP_LINKS.values():
            hub.set_tile(hub_tile[0], hub_tile[1], TileType.WARP)

    def _place_npcs(self, map_name: str) -> None:
        """Place NPC sprites on the current map."""
        self.npcs.clear()
        placements = MAP_NPC_PLACEMENTS.get(map_name, [])
        for p in placements:
            char = self.cast.get(p.character_key)
            if not char:
                continue
            npc = NPCSprite(
                char,
                p.tile_x * TILE_SIZE,
                p.tile_y * TILE_SIZE,
                npc_id=p.npc_id,
            )
            npc.facing = p.facing
            npc.wander = p.wander
            self.npcs.append(npc)

    def _draw_interaction_hints(self, surface: pygame.Surface) -> None:
        """Draw interaction indicators near interactable NPCs."""
        if not self.player or not self.camera:
            return

        for npc in self.npcs:
            if npc.is_near(self.player.world_x, self.player.world_y, INTERACTION_RANGE):
                # Draw a small indicator above the NPC
                sx = int(npc.world_x - self.camera.x + self.camera.view_w // 2)
                sy = int(npc.world_y - self.camera.y + self.camera.view_h // 2 - 20)
                # Bouncing arrow
                bob = int(math.sin(time.time() * 4) * 3)
                points = [
                    (sx + 4, sy + bob),
                    (sx + 8, sy + bob - 6),
                    (sx, sy + bob - 6),
                ]
                pygame.draw.polygon(surface, (255, 220, 80), points)

    def get_nearby_npc(self) -> Optional[str]:
        """Return the NPC ID of a nearby NPC, or None."""
        if not self.player:
            return None
        for npc in self.npcs:
            if npc.is_near(self.player.world_x, self.player.world_y, INTERACTION_RANGE):
                return npc.npc_id
        return None

    @property
    def player_tile_pos(self) -> Tuple[int, int]:
        """Get the player's current tile position."""
        if self.player:
            return (self.player.tile_x, self.player.tile_y)
        return (0, 0)
