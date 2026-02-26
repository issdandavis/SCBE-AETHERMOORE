#!/usr/bin/env python3
"""
Aethermoor Procedural Tile Map System
======================================
Provides tile-based maps, a smooth-follow camera, and procedural map
generation for the Aethermoor RPG.  All tile graphics are generated at
startup as 16x16 Pygame surfaces -- no external assets required.

Maps
----
- guild_hub           40x30 outdoor town (paths, buildings, NPC spots, warps)
- avalon_academy      30x25 indoor academy with six tongue-tower entrances
- spiral_tower_entrance  20x20 dungeon antechamber with stairs

Palette matches the GBA-Sapphire-era colors defined in engine.py.
"""

from __future__ import annotations

import random
from enum import IntEnum
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pygame

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TILE_SIZE: int = 16

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
GRASS: Tuple[int, int, int] = (56, 128, 56)
WATER: Tuple[int, int, int] = (64, 108, 200)
FLOAT_ISL: Tuple[int, int, int] = (88, 68, 148)  # stone / floor
BG_EARTH: Tuple[int, int, int] = (42, 46, 58)     # wall
GOLD: Tuple[int, int, int] = (255, 215, 80)        # special / warp

# Sacred Tongue accent colours
KO_COLOR: Tuple[int, int, int] = (220, 60, 60)
AV_COLOR: Tuple[int, int, int] = (60, 180, 220)
RU_COLOR: Tuple[int, int, int] = (220, 180, 60)
CA_COLOR: Tuple[int, int, int] = (60, 220, 120)
UM_COLOR: Tuple[int, int, int] = (140, 60, 220)
DR_COLOR: Tuple[int, int, int] = (220, 120, 60)

TONGUE_COLORS: Dict[str, Tuple[int, int, int]] = {
    "KO": KO_COLOR,
    "AV": AV_COLOR,
    "RU": RU_COLOR,
    "CA": CA_COLOR,
    "UM": UM_COLOR,
    "DR": DR_COLOR,
}


# ---------------------------------------------------------------------------
# Tile Types
# ---------------------------------------------------------------------------
class TileType(IntEnum):
    """Enumeration of every tile kind the map system knows about."""
    EMPTY      = 0
    GRASS      = 1
    STONE      = 2
    WATER      = 3
    WALL       = 4
    WARP       = 5
    ENCOUNTER  = 6
    NPC_SPOT   = 7
    CHEST      = 8
    STAIR_UP   = 9
    STAIR_DOWN = 10


# Which tiles block movement
_SOLID_TILES: frozenset[int] = frozenset({
    TileType.WATER,
    TileType.WALL,
})


# ---------------------------------------------------------------------------
# TileMap
# ---------------------------------------------------------------------------
class TileMap:
    """A 2-D tile grid with collision and event layers.

    Parameters
    ----------
    width : int
        Number of tiles across (columns).
    height : int
        Number of tiles down (rows).
    name : str
        Human-readable map identifier.
    """

    def __init__(self, width: int, height: int, name: str) -> None:
        self.width: int = width
        self.height: int = height
        self.name: str = name
        self.tiles: np.ndarray = np.zeros((height, width), dtype=np.int8)
        self.collision: np.ndarray = np.zeros((height, width), dtype=bool)
        self.events: Dict[Tuple[int, int], str] = {}

    # -- mutators ----------------------------------------------------------

    def set_tile(self, x: int, y: int, tile_type: int) -> None:
        """Place *tile_type* at grid position (x, y).

        Automatically updates the collision mask based on the tile's
        inherent solidity.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y, x] = tile_type
            self.collision[y, x] = tile_type in _SOLID_TILES

    def fill_rect(self, x: int, y: int, w: int, h: int, tile_type: int) -> None:
        """Fill an axis-aligned rectangle with *tile_type*."""
        for ty in range(max(0, y), min(self.height, y + h)):
            for tx in range(max(0, x), min(self.width, x + w)):
                self.set_tile(tx, ty, tile_type)

    # -- queries -----------------------------------------------------------

    def get_tile(self, x: int, y: int) -> int:
        """Return the tile type at (x, y), or ``TileType.EMPTY`` if OOB."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return int(self.tiles[y, x])
        return TileType.EMPTY

    def is_solid(self, x: int, y: int) -> bool:
        """Return ``True`` if the tile at (x, y) blocks movement."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return bool(self.collision[y, x])
        return True  # out-of-bounds is impassable

    def get_event(self, x: int, y: int) -> Optional[str]:
        """Return the event tag string at (x, y), or ``None``."""
        return self.events.get((x, y))

    # -- rendering ---------------------------------------------------------

    def draw(
        self,
        surface: pygame.Surface,
        camera: "Camera",
        tile_surfaces: Dict[int, pygame.Surface],
    ) -> None:
        """Blit visible tiles onto *surface* using the current *camera*."""
        min_tx, min_ty, max_tx, max_ty = camera.get_visible_range()

        for ty in range(min_ty, max_ty + 1):
            for tx in range(min_tx, max_tx + 1):
                tid = self.get_tile(tx, ty)
                if tid == TileType.EMPTY:
                    continue
                ts = tile_surfaces.get(tid)
                if ts is None:
                    continue
                sx, sy = camera.world_to_screen(
                    tx * TILE_SIZE, ty * TILE_SIZE,
                )
                surface.blit(ts, (sx, sy))


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
class Camera:
    """Smooth-follow camera that tracks a world-space target position.

    Parameters
    ----------
    map_width, map_height : int
        Map dimensions **in tiles** (used for clamping).
    view_w, view_h : int
        Viewport dimensions in pixels (default 640x480).
    """

    def __init__(
        self,
        map_width: int,
        map_height: int,
        view_w: int = 640,
        view_h: int = 480,
    ) -> None:
        self.map_width: int = map_width
        self.map_height: int = map_height
        self.view_w: int = view_w
        self.view_h: int = view_h

        # Current camera offset (top-left corner, world pixels)
        self.x: float = 0.0
        self.y: float = 0.0

    # -- update ------------------------------------------------------------

    def follow(
        self,
        target_x: float,
        target_y: float,
        dt: float,
        lerp_speed: float = 8.0,
    ) -> None:
        """Smoothly interpolate toward *target* (world pixels).

        The camera centres on the target and is clamped so it never
        scrolls past the map edges.
        """
        # Desired camera position (target in centre of viewport)
        goal_x: float = target_x - self.view_w / 2.0
        goal_y: float = target_y - self.view_h / 2.0

        # Clamp to map bounds
        max_x: float = float(self.map_width * TILE_SIZE - self.view_w)
        max_y: float = float(self.map_height * TILE_SIZE - self.view_h)
        goal_x = max(0.0, min(goal_x, max_x))
        goal_y = max(0.0, min(goal_y, max_y))

        # Exponential lerp
        t: float = 1.0 - (2.0 ** (-lerp_speed * dt))
        self.x += (goal_x - self.x) * t
        self.y += (goal_y - self.y) * t

    # -- coordinate helpers ------------------------------------------------

    def world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        """Convert world-pixel coordinates to screen-pixel coordinates."""
        return (int(wx - self.x), int(wy - self.y))

    def get_visible_range(self) -> Tuple[int, int, int, int]:
        """Return the inclusive tile-index range visible through the viewport.

        Returns ``(min_tile_x, min_tile_y, max_tile_x, max_tile_y)``.
        """
        min_tx: int = max(0, int(self.x) // TILE_SIZE)
        min_ty: int = max(0, int(self.y) // TILE_SIZE)
        max_tx: int = min(
            self.map_width - 1,
            (int(self.x) + self.view_w) // TILE_SIZE,
        )
        max_ty: int = min(
            self.map_height - 1,
            (int(self.y) + self.view_h) // TILE_SIZE,
        )
        return min_tx, min_ty, max_tx, max_ty


# ---------------------------------------------------------------------------
# Tile surface generator (16x16 pixel-art, no external assets)
# ---------------------------------------------------------------------------

def _darken(
    color: Tuple[int, int, int], amount: int = 30,
) -> Tuple[int, int, int]:
    return (
        max(0, color[0] - amount),
        max(0, color[1] - amount),
        max(0, color[2] - amount),
    )


def _lighten(
    color: Tuple[int, int, int], amount: int = 40,
) -> Tuple[int, int, int]:
    return (
        min(255, color[0] + amount),
        min(255, color[1] + amount),
        min(255, color[2] + amount),
    )


def _make_grass() -> pygame.Surface:
    """Grass tile with a subtle dither pattern."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    surf.fill(GRASS)
    dark = _darken(GRASS, 20)
    light = _lighten(GRASS, 15)
    # Scattered blade highlights
    for px in range(0, TILE_SIZE, 3):
        for py in range(0, TILE_SIZE, 4):
            offset = (px * 7 + py * 13) % 5
            if offset == 0:
                surf.set_at((px, py), light)
            elif offset == 1:
                surf.set_at((px, py), dark)
    # Short blade accents
    for px in range(1, TILE_SIZE, 5):
        surf.set_at((px, 3), _lighten(GRASS, 25))
        surf.set_at((px, 10), _lighten(GRASS, 25))
    return surf


def _make_stone() -> pygame.Surface:
    """Stone / floating-island floor tile."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    surf.fill(FLOAT_ISL)
    dark = _darken(FLOAT_ISL, 18)
    light = _lighten(FLOAT_ISL, 18)
    # Cobblestone grid lines
    for px in range(TILE_SIZE):
        surf.set_at((px, 0), dark)
        surf.set_at((px, 7), dark)
        surf.set_at((px, 15), dark)
    for py in range(TILE_SIZE):
        surf.set_at((0, py), dark)
        surf.set_at((8, py), dark)
        surf.set_at((15, py), dark)
    # Inner highlights
    for dx in range(2, 7):
        surf.set_at((dx, 2), light)
        surf.set_at((dx + 8, 10), light)
    return surf


def _make_water() -> pygame.Surface:
    """Water tile with horizontal wave lines."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    surf.fill(WATER)
    light = _lighten(WATER, 35)
    dark = _darken(WATER, 25)
    # Horizontal wave rows
    for px in range(TILE_SIZE):
        phase = (px * 3 + 1) % TILE_SIZE
        surf.set_at((px, 4), light)
        surf.set_at((px, 11), light)
        if phase < 6:
            surf.set_at((px, 7), dark)
    # Specular dot
    surf.set_at((5, 3), (200, 220, 255))
    surf.set_at((12, 10), (200, 220, 255))
    return surf


def _make_wall() -> pygame.Surface:
    """Wall / BG_EARTH tile with brick pattern."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    surf.fill(BG_EARTH)
    dark = _darken(BG_EARTH, 14)
    light = _lighten(BG_EARTH, 12)
    # Brick rows
    for row in range(0, TILE_SIZE, 4):
        for px in range(TILE_SIZE):
            surf.set_at((px, row), dark)
        offset = 4 if (row // 4) % 2 else 0
        for py in range(row, min(row + 4, TILE_SIZE)):
            surf.set_at((offset, py), dark)
            col2 = (offset + 8) % TILE_SIZE
            surf.set_at((col2, py), dark)
    # Mortar highlight
    for px in range(1, TILE_SIZE, 8):
        surf.set_at((px, 2), light)
        surf.set_at((px, 6), light)
        surf.set_at((px, 10), light)
        surf.set_at((px, 14), light)
    return surf


def _make_warp() -> pygame.Surface:
    """Warp / special tile -- gold swirl pattern."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    surf.fill(_darken(GOLD, 80))
    mid = TILE_SIZE // 2
    # Concentric diamond
    for ring in range(1, mid + 1):
        c = _lighten(GOLD, ring * 6) if ring % 2 == 0 else _darken(GOLD, ring * 4)
        for d in range(-ring, ring + 1):
            rdist = ring - abs(d)
            if 0 <= mid + d < TILE_SIZE:
                if 0 <= mid - rdist < TILE_SIZE:
                    surf.set_at((mid + d, mid - rdist), c)
                if 0 <= mid + rdist < TILE_SIZE:
                    surf.set_at((mid + d, mid + rdist), c)
    # Centre bright pixel
    surf.set_at((mid, mid), (255, 255, 200))
    return surf


def _make_encounter() -> pygame.Surface:
    """Encounter zone -- tall grass with red-tinted tips."""
    surf = _make_grass()
    tip = (180, 80, 60)
    for px in range(0, TILE_SIZE, 2):
        surf.set_at((px, 0), tip)
        surf.set_at((px + 1, 1), tip)
    return surf


def _make_npc_spot() -> pygame.Surface:
    """NPC standing spot -- stone with a small golden diamond marker."""
    surf = _make_stone()
    mid = TILE_SIZE // 2
    pts = [
        (mid, mid - 2),
        (mid - 2, mid),
        (mid, mid + 2),
        (mid + 2, mid),
    ]
    pygame.draw.polygon(surf, GOLD, pts)
    return surf


def _make_chest() -> pygame.Surface:
    """Treasure chest tile -- stone floor with a small chest icon."""
    surf = _make_stone()
    # Chest body (brown)
    body_color = (140, 90, 40)
    clasp_color = GOLD
    cx, cy = TILE_SIZE // 2, TILE_SIZE // 2
    pygame.draw.rect(surf, body_color, (cx - 4, cy - 2, 8, 6))
    pygame.draw.rect(surf, _darken(body_color, 30), (cx - 4, cy - 2, 8, 6), 1)
    # Lid curve
    pygame.draw.rect(surf, _lighten(body_color, 20), (cx - 4, cy - 3, 8, 2))
    # Clasp
    surf.set_at((cx, cy), clasp_color)
    surf.set_at((cx - 1, cy), clasp_color)
    return surf


def _make_stair(direction: str) -> pygame.Surface:
    """Staircase tile (``'up'`` or ``'down'``).

    Draws diagonal lines on a stone base with an arrow hint.
    """
    surf = _make_stone()
    light = _lighten(FLOAT_ISL, 35)
    dark = _darken(FLOAT_ISL, 25)
    # Diagonal stair lines
    for i in range(0, TILE_SIZE, 3):
        for d in range(min(3, TILE_SIZE - i)):
            if 0 <= i + d < TILE_SIZE and 0 <= i + d < TILE_SIZE:
                surf.set_at((i + d, i + d), light)
                if i + d + 1 < TILE_SIZE:
                    surf.set_at((i + d + 1, i + d), dark)
    # Arrow indicator
    mid = TILE_SIZE // 2
    if direction == "up":
        # Upward-pointing arrow
        for dx in range(-2, 3):
            surf.set_at((mid + dx, mid + 1), GOLD)
        surf.set_at((mid, mid - 2), GOLD)
        surf.set_at((mid - 1, mid - 1), GOLD)
        surf.set_at((mid + 1, mid - 1), GOLD)
        surf.set_at((mid, mid), GOLD)
    else:
        # Downward-pointing arrow
        for dx in range(-2, 3):
            surf.set_at((mid + dx, mid - 1), GOLD)
        surf.set_at((mid, mid + 2), GOLD)
        surf.set_at((mid - 1, mid + 1), GOLD)
        surf.set_at((mid + 1, mid + 1), GOLD)
        surf.set_at((mid, mid), GOLD)
    return surf


def generate_tile_surfaces() -> Dict[int, pygame.Surface]:
    """Create a 16x16 ``pygame.Surface`` for every ``TileType`` value.

    Call this **after** ``pygame.display.set_mode()`` has been invoked so
    surfaces can be hardware-accelerated.

    Returns
    -------
    dict[int, pygame.Surface]
        Mapping from ``TileType`` integer to its rendered tile graphic.
    """
    return {
        TileType.GRASS:      _make_grass(),
        TileType.STONE:      _make_stone(),
        TileType.WATER:      _make_water(),
        TileType.WALL:       _make_wall(),
        TileType.WARP:       _make_warp(),
        TileType.ENCOUNTER:  _make_encounter(),
        TileType.NPC_SPOT:   _make_npc_spot(),
        TileType.CHEST:      _make_chest(),
        TileType.STAIR_UP:   _make_stair("up"),
        TileType.STAIR_DOWN: _make_stair("down"),
    }


# ---------------------------------------------------------------------------
# MAP DEFINITIONS -- procedural generators
# ---------------------------------------------------------------------------

def _border_walls(tm: TileMap) -> None:
    """Surround the map with a one-tile-wide wall border."""
    for x in range(tm.width):
        tm.set_tile(x, 0, TileType.WALL)
        tm.set_tile(x, tm.height - 1, TileType.WALL)
    for y in range(tm.height):
        tm.set_tile(0, y, TileType.WALL)
        tm.set_tile(tm.width - 1, y, TileType.WALL)


def _place_building(
    tm: TileMap,
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    door_side: str = "south",
    interior: int = TileType.STONE,
) -> None:
    """Stamp a rectangular building with a one-tile door."""
    # Walls
    tm.fill_rect(x, y, w, h, TileType.WALL)
    # Interior
    tm.fill_rect(x + 1, y + 1, w - 2, h - 2, interior)
    # Door
    mid = w // 2
    if door_side == "south":
        tm.set_tile(x + mid, y + h - 1, TileType.STONE)
    elif door_side == "north":
        tm.set_tile(x + mid, y, TileType.STONE)
    elif door_side == "east":
        tm.set_tile(x + w - 1, y + h // 2, TileType.STONE)
    elif door_side == "west":
        tm.set_tile(x, y + h // 2, TileType.STONE)


def _place_path_h(tm: TileMap, y: int, x0: int, x1: int) -> None:
    """Lay a horizontal stone path from *x0* to *x1* (inclusive)."""
    for x in range(min(x0, x1), max(x0, x1) + 1):
        tm.set_tile(x, y, TileType.STONE)
        if y + 1 < tm.height:
            tm.set_tile(x, y + 1, TileType.STONE)


def _place_path_v(tm: TileMap, x: int, y0: int, y1: int) -> None:
    """Lay a vertical stone path from *y0* to *y1* (inclusive)."""
    for y in range(min(y0, y1), max(y0, y1) + 1):
        tm.set_tile(x, y, TileType.STONE)
        if x + 1 < tm.width:
            tm.set_tile(x + 1, y, TileType.STONE)


# ---- guild_hub -----------------------------------------------------------

def build_guild_hub() -> TileMap:
    """40x30 outdoor Guild Hub town.

    Layout
    ------
    - Grass base with scattered encounter zones around the edges.
    - Central crossroads of stone paths.
    - Guild hall (large building, north-centre).
    - Shops & houses (small buildings on east/west).
    - NPC spots at path intersections.
    - Warp tile in the south-east corner leading to the Spiral Tower.
    - Water pond in the south-west.
    """
    W, H = 40, 30
    tm = TileMap(W, H, "guild_hub")

    # 1. Fill with grass
    tm.fill_rect(0, 0, W, H, TileType.GRASS)

    # 2. Border walls
    _border_walls(tm)

    # 3. Encounter tall-grass zones (edges)
    tm.fill_rect(2, 2, 6, 4, TileType.ENCOUNTER)
    tm.fill_rect(32, 2, 6, 4, TileType.ENCOUNTER)
    tm.fill_rect(2, 24, 6, 4, TileType.ENCOUNTER)
    tm.fill_rect(32, 24, 6, 4, TileType.ENCOUNTER)

    # 4. Stone path cross (+) through the centre
    mid_x, mid_y = W // 2, H // 2
    _place_path_h(tm, mid_y, 2, W - 3)
    _place_path_v(tm, mid_x, 2, H - 3)

    # 5. Guild Hall (north-centre, 10x6)
    guild_x, guild_y = mid_x - 5, 2
    _place_building(tm, guild_x, guild_y, 10, 6, door_side="south")
    tm.events[(guild_x + 5, guild_y + 5)] = "enter_guild_hall"

    # 6. Item shop (west side, 6x5)
    _place_building(tm, 3, mid_y - 6, 6, 5, door_side="east")
    tm.set_tile(9, mid_y - 4, TileType.NPC_SPOT)
    tm.events[(9, mid_y - 4)] = "npc_shopkeeper"

    # 7. Inn (east side, 6x5)
    _place_building(tm, W - 9, mid_y - 6, 6, 5, door_side="west")
    tm.set_tile(W - 10, mid_y - 4, TileType.NPC_SPOT)
    tm.events[(W - 10, mid_y - 4)] = "npc_innkeeper"

    # 8. Healer cottage (west side, 5x4)
    _place_building(tm, 3, mid_y + 3, 5, 4, door_side="east")
    tm.set_tile(8, mid_y + 5, TileType.NPC_SPOT)
    tm.events[(8, mid_y + 5)] = "npc_healer"

    # 9. Blacksmith (east side, 5x4)
    _place_building(tm, W - 8, mid_y + 3, 5, 4, door_side="west")
    tm.set_tile(W - 9, mid_y + 5, TileType.NPC_SPOT)
    tm.events[(W - 9, mid_y + 5)] = "npc_blacksmith"

    # 10. NPC spots at the crossroads
    tm.set_tile(mid_x - 2, mid_y - 2, TileType.NPC_SPOT)
    tm.events[(mid_x - 2, mid_y - 2)] = "npc_elder"
    tm.set_tile(mid_x + 3, mid_y + 3, TileType.NPC_SPOT)
    tm.events[(mid_x + 3, mid_y + 3)] = "npc_wanderer"

    # 11. Treasure chest near guild hall
    tm.set_tile(guild_x + 8, guild_y + 3, TileType.CHEST)
    tm.events[(guild_x + 8, guild_y + 3)] = "chest_starter_kit"

    # 12. Water pond (south-west)
    for py in range(H - 7, H - 3):
        for px in range(3, 9):
            dist = ((px - 6) ** 2 + (py - (H - 5)) ** 2)
            if dist <= 9:
                tm.set_tile(px, py, TileType.WATER)

    # 13. Warp tile to Spiral Tower (south-east path endpoint)
    warp_x, warp_y = W - 4, H - 4
    tm.set_tile(warp_x, warp_y, TileType.WARP)
    tm.events[(warp_x, warp_y)] = "warp_spiral_tower"

    # 14. Path spurs to warp and pond
    _place_path_h(tm, H - 4, mid_x, W - 4)
    _place_path_v(tm, 6, mid_y, H - 7)

    return tm


# ---- avalon_academy -------------------------------------------------------

def build_avalon_academy() -> TileMap:
    """30x25 indoor Avalon Academy.

    Layout
    ------
    - Stone floor base.
    - Central atrium / grand hall.
    - Six tongue-tower entrances (one per tongue) arranged in a hex-like ring,
      each marked with its tongue colour via NPC spots.
    - Corridors connecting the towers to the atrium.
    - NPC spots for instructors.
    """
    W, H = 30, 25
    tm = TileMap(W, H, "avalon_academy")

    # 1. Base floor
    tm.fill_rect(0, 0, W, H, TileType.STONE)

    # 2. Outer walls
    _border_walls(tm)

    # 3. Central atrium (open area)
    atrium_x, atrium_y = W // 2 - 4, H // 2 - 3
    tm.fill_rect(atrium_x, atrium_y, 8, 6, TileType.STONE)

    # 4. Tongue tower alcoves -- positioned around the atrium
    #    Each is a small 4x4 walled room with a warp entrance
    tongue_order: List[str] = ["KO", "AV", "RU", "CA", "UM", "DR"]
    tower_positions: List[Tuple[int, int, str]] = [
        # (x, y, corridor_direction)
        (3,  2,  "south"),   # KO -- top-left
        (W - 7, 2, "south"), # AV -- top-right
        (3,  H - 6, "north"), # RU -- bottom-left
        (W - 7, H - 6, "north"), # CA -- bottom-right
        (3,  H // 2 - 2, "east"),  # UM -- mid-left
        (W - 7, H // 2 - 2, "west"), # DR -- mid-right
    ]

    for idx, (tx, ty, door) in enumerate(tower_positions):
        tongue = tongue_order[idx]
        # Build the tower room
        _place_building(tm, tx, ty, 4, 4, door_side=door)

        # Warp tile inside the tower
        inner_x = tx + 2
        inner_y = ty + 2
        tm.set_tile(inner_x, inner_y, TileType.WARP)
        tm.events[(inner_x, inner_y)] = f"warp_tower_{tongue.lower()}"

        # NPC instructor outside the door
        if door == "south":
            npc_x, npc_y = tx + 2, ty + 4
        elif door == "north":
            npc_x, npc_y = tx + 2, ty - 1
        elif door == "east":
            npc_x, npc_y = tx + 4, ty + 2
        else:  # west
            npc_x, npc_y = tx - 1, ty + 2

        if 0 < npc_x < W - 1 and 0 < npc_y < H - 1:
            tm.set_tile(npc_x, npc_y, TileType.NPC_SPOT)
            tm.events[(npc_x, npc_y)] = f"npc_instructor_{tongue.lower()}"

    # 5. Corridors from towers to atrium
    #    Horizontal corridors from left/right towers to atrium
    atrium_cx = W // 2
    atrium_cy = H // 2
    # Top corridor
    _place_path_h(tm, 5, 7, atrium_cx - 1)
    _place_path_h(tm, 5, atrium_cx + 1, W - 8)
    # Bottom corridor
    _place_path_h(tm, H - 6, 7, atrium_cx - 1)
    _place_path_h(tm, H - 6, atrium_cx + 1, W - 8)
    # Left vertical corridor
    _place_path_v(tm, 6, 6, H - 7)
    # Right vertical corridor
    _place_path_v(tm, W - 7, 6, H - 7)
    # Central vertical corridor
    _place_path_v(tm, atrium_cx, 3, H - 4)

    # 6. Headmaster NPC in the atrium centre
    hm_x, hm_y = atrium_cx, atrium_cy
    tm.set_tile(hm_x, hm_y, TileType.NPC_SPOT)
    tm.events[(hm_x, hm_y)] = "npc_headmaster"

    # 7. Chest in the atrium
    tm.set_tile(atrium_cx + 3, atrium_cy, TileType.CHEST)
    tm.events[(atrium_cx + 3, atrium_cy)] = "chest_academy_scroll"

    return tm


# ---- spiral_tower_entrance ------------------------------------------------

def build_spiral_tower_entrance() -> TileMap:
    """20x20 entry area for the Spiral Tower dungeon.

    Layout
    ------
    - Stone floor within thick walls.
    - Central spiral staircase (stair_down) leading into the dungeon.
    - Decorative pillars (wall tiles) in a ring.
    - A warp tile at the south for returning to town.
    - NPC spot for a guardian.
    """
    W, H = 20, 20
    tm = TileMap(W, H, "spiral_tower_entrance")

    # 1. Fill with stone
    tm.fill_rect(0, 0, W, H, TileType.STONE)

    # 2. Thick outer walls (2 tiles)
    for x in range(W):
        for y in range(H):
            if x < 2 or x >= W - 2 or y < 2 or y >= H - 2:
                tm.set_tile(x, y, TileType.WALL)

    # 3. Central stair down
    mid_x, mid_y = W // 2, H // 2
    tm.set_tile(mid_x, mid_y, TileType.STAIR_DOWN)
    tm.events[(mid_x, mid_y)] = "descend_spiral_tower"
    # Secondary stair tile for a wider landing
    tm.set_tile(mid_x - 1, mid_y, TileType.STAIR_DOWN)
    tm.set_tile(mid_x + 1, mid_y, TileType.STAIR_DOWN)
    tm.set_tile(mid_x, mid_y - 1, TileType.STAIR_DOWN)
    tm.set_tile(mid_x, mid_y + 1, TileType.STAIR_DOWN)

    # 4. Decorative pillar ring (8 pillars at radius ~4 tiles)
    pillar_offsets: List[Tuple[int, int]] = [
        (-4, -4), (0, -5), (4, -4),
        (-5, 0),           (5, 0),
        (-4, 4),  (0, 5),  (4, 4),
    ]
    for dx, dy in pillar_offsets:
        px, py = mid_x + dx, mid_y + dy
        if 2 <= px < W - 2 and 2 <= py < H - 2:
            tm.set_tile(px, py, TileType.WALL)

    # 5. Return warp at the south entrance
    warp_x, warp_y = mid_x, H - 3
    tm.set_tile(warp_x, warp_y, TileType.WARP)
    tm.events[(warp_x, warp_y)] = "warp_guild_hub"

    # 6. Guardian NPC
    tm.set_tile(mid_x + 2, mid_y + 3, TileType.NPC_SPOT)
    tm.events[(mid_x + 2, mid_y + 3)] = "npc_tower_guardian"

    # 7. Chest with dungeon supplies
    tm.set_tile(mid_x - 3, mid_y - 3, TileType.CHEST)
    tm.events[(mid_x - 3, mid_y - 3)] = "chest_tower_supplies"

    return tm


# ---------------------------------------------------------------------------
# Geography Pack -- deterministic procedural exploration zones
# ---------------------------------------------------------------------------

GEOGRAPHY_PACK_SIZE: Tuple[int, int] = (48, 34)
GEOGRAPHY_PACK_RETURN_TILE: Tuple[int, int] = (
    GEOGRAPHY_PACK_SIZE[0] // 2,
    GEOGRAPHY_PACK_SIZE[1] - 3,
)

GEOGRAPHY_PACK_SPECS: Dict[str, Dict[str, object]] = {
    "geography_pack_meadow": {
        "theme": "meadow",
        "seed": 1103,
        "water_pools": 2,
        "ridge_clusters": 2,
    },
    "geography_pack_wetlands": {
        "theme": "wetlands",
        "seed": 2111,
        "water_pools": 5,
        "ridge_clusters": 2,
    },
    "geography_pack_highlands": {
        "theme": "highlands",
        "seed": 3191,
        "water_pools": 1,
        "ridge_clusters": 6,
    },
    "geography_pack_deepwood": {
        "theme": "deepwood",
        "seed": 4219,
        "water_pools": 2,
        "ridge_clusters": 5,
    },
}


def get_geography_pack_names() -> List[str]:
    """Return registered procedural geography zone names."""
    return list(GEOGRAPHY_PACK_SPECS.keys())


def _stable_seed(name: str, seed: int) -> int:
    """Stable 32-bit seed from a map name + seed value."""
    value = (seed + 0x9E3779B9) & 0xFFFFFFFF
    for ch in name:
        value = (value * 131 + ord(ch)) & 0xFFFFFFFF
    return value


def _paint_ellipse(
    tm: TileMap,
    cx: int,
    cy: int,
    rx: int,
    ry: int,
    tile_type: int,
    *,
    protect: Tuple[int, ...] = (),
) -> None:
    """Paint an ellipse of *tile_type*, skipping any tiles in *protect*."""
    if rx <= 0 or ry <= 0:
        return
    x0, x1 = max(1, cx - rx), min(tm.width - 2, cx + rx)
    y0, y1 = max(1, cy - ry), min(tm.height - 2, cy + ry)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            nx = (x - cx) / float(rx)
            ny = (y - cy) / float(ry)
            if nx * nx + ny * ny <= 1.0:
                if tm.get_tile(x, y) in protect:
                    continue
                tm.set_tile(x, y, tile_type)


def _adjacent_count(tm: TileMap, x: int, y: int, tile_type: int) -> int:
    """Count matching tiles in an 8-neighbourhood around (x, y)."""
    total = 0
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            if ox == 0 and oy == 0:
                continue
            if tm.get_tile(x + ox, y + oy) == tile_type:
                total += 1
    return total


def build_geography_pack_zone(map_name: str) -> TileMap:
    """Build a deterministic procedural exploration zone by map name."""
    spec = GEOGRAPHY_PACK_SPECS.get(map_name)
    if spec is None:
        raise KeyError(
            f"Unknown geography pack map '{map_name}'. "
            f"Available: {get_geography_pack_names()}"
        )

    w, h = GEOGRAPHY_PACK_SIZE
    tm = TileMap(w, h, map_name)
    rng = random.Random(_stable_seed(map_name, int(spec["seed"])))

    # Base terrain + border
    tm.fill_rect(0, 0, w, h, TileType.GRASS)
    _border_walls(tm)

    # Core traversable stone routes
    trunk_x = w // 2 + rng.randint(-4, 4)
    branch_y = max(5, min(h - 8, h // 2 + rng.randint(-3, 2)))
    _place_path_v(tm, trunk_x, 2, h - 3)
    _place_path_h(tm, branch_y, 2, w - 3)

    # South return gate to guild hub
    return_x, return_y = GEOGRAPHY_PACK_RETURN_TILE
    _place_path_h(
        tm,
        return_y,
        min(trunk_x, return_x),
        max(trunk_x, return_x),
    )
    tm.set_tile(return_x, return_y, TileType.WARP)
    tm.events[(return_x, return_y)] = "warp_guild_hub"

    # Biome sculpting: water pools + ridge/forest walls
    water_pools = int(spec["water_pools"])
    ridge_clusters = int(spec["ridge_clusters"])

    for _ in range(water_pools):
        cx = rng.randint(5, w - 6)
        cy = rng.randint(4, h - 8)
        rx = rng.randint(2, 5)
        ry = rng.randint(2, 4)
        _paint_ellipse(
            tm,
            cx,
            cy,
            rx,
            ry,
            TileType.WATER,
            protect=(TileType.STONE, TileType.WARP),
        )

    for _ in range(ridge_clusters):
        cx = rng.randint(4, w - 5)
        cy = rng.randint(3, h - 9)
        rx = rng.randint(2, 4)
        ry = rng.randint(2, 4)
        _paint_ellipse(
            tm,
            cx,
            cy,
            rx,
            ry,
            TileType.WALL,
            protect=(TileType.STONE, TileType.WATER, TileType.WARP),
        )

    # Encounter placement by theme (grass-only logical regions)
    theme = str(spec["theme"])
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            if tm.get_tile(x, y) != TileType.GRASS:
                continue
            if abs(x - return_x) + abs(y - return_y) <= 9:
                continue  # safer starter landing area

            near_water = _adjacent_count(tm, x, y, TileType.WATER)
            near_wall = _adjacent_count(tm, x, y, TileType.WALL)
            edge_bonus = 0.04 if (x < 8 or y < 6 or x > w - 9 or y > h - 9) else 0.0

            if theme == "wetlands":
                chance = 0.02 + near_water * 0.09 + edge_bonus * 0.4
            elif theme == "highlands":
                chance = 0.02 + near_wall * 0.08 + near_water * 0.01
            elif theme == "deepwood":
                chance = 0.04 + near_wall * 0.05 + edge_bonus
            else:  # meadow
                chance = 0.018 + near_wall * 0.02 + near_water * 0.02 + edge_bonus

            if rng.random() < min(0.62, chance):
                tm.set_tile(x, y, TileType.ENCOUNTER)

    # Optional minor reward pickup
    chest_x = max(3, min(w - 4, trunk_x + rng.randint(-5, 5)))
    chest_y = max(3, branch_y - 3)
    if tm.get_tile(chest_x, chest_y) in (TileType.GRASS, TileType.STONE):
        tm.set_tile(chest_x, chest_y, TileType.CHEST)
        tm.events[(chest_x, chest_y)] = f"chest_{map_name}_cache"

    return tm


# ---------------------------------------------------------------------------
# Public map registry
# ---------------------------------------------------------------------------

MapBuilder = Callable[[], TileMap]


def _make_geography_builder(map_name: str) -> MapBuilder:
    """Return a no-arg builder bound to *map_name*."""
    def _builder() -> TileMap:
        return build_geography_pack_zone(map_name)
    return _builder


def get_map(name: str) -> TileMap:
    """Build and return a map by name.

    Supported names include ``guild_hub``, ``avalon_academy``,
    ``spiral_tower_entrance``, and all ``geography_pack_*`` zones.

    Raises
    ------
    KeyError
        If *name* is not a recognised map.
    """
    builder = MAP_DEFINITIONS.get(name)
    if builder is None:
        raise KeyError(
            f"Unknown map '{name}'. Available: {list(MAP_DEFINITIONS.keys())}"
        )
    return builder()


# Re-export as dict of callables for external inspection
MAP_DEFINITIONS: Dict[str, MapBuilder] = {
    "guild_hub": build_guild_hub,
    "avalon_academy": build_avalon_academy,
    "spiral_tower_entrance": build_spiral_tower_entrance,
}
for geography_name in get_geography_pack_names():
    MAP_DEFINITIONS[geography_name] = _make_geography_builder(geography_name)


# ---------------------------------------------------------------------------
# Self-test (runs without a display by using a hidden pygame driver)
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Validate every map, camera, and tile surface without a visible window."""
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    # A tiny hidden display so Surface creation works
    pygame.display.set_mode((1, 1))

    print(f"\n{'=' * 56}")
    print("  tilemap.py -- self-test")
    print(f"{'=' * 56}\n")

    passed = 0
    failed = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failed += 1
            print(f"  FAIL  {label}  {detail}")

    # 1. Tile surface generation
    surfs = generate_tile_surfaces()
    check("Tile surfaces count", len(surfs) == 10, f"got {len(surfs)}")
    for tid, surf in surfs.items():
        check(
            f"Surface TileType={tid} size",
            surf.get_size() == (TILE_SIZE, TILE_SIZE),
            f"got {surf.get_size()}",
        )

    # 2. TileType enum coverage
    check(
        "TileType enum has 11 members",
        len(TileType) == 11,
        f"got {len(TileType)}",
    )

    # 3. Build each map
    for name, builder in MAP_DEFINITIONS.items():
        tm = builder()
        check(f"Map '{name}' built", tm is not None)
        check(
            f"Map '{name}' name",
            tm.name == name,
            f"got '{tm.name}'",
        )
        # At least one walkable tile
        walkable = int(np.sum(~tm.collision))
        check(f"Map '{name}' has walkable tiles", walkable > 0, f"{walkable}")
        # Has events
        check(f"Map '{name}' has events", len(tm.events) > 0)
        # set_tile / get_tile round-trip
        tm.set_tile(1, 1, TileType.GRASS)
        check(f"Map '{name}' get_tile(1,1)", tm.get_tile(1, 1) == TileType.GRASS)
        # OOB returns EMPTY
        check(f"Map '{name}' OOB get_tile", tm.get_tile(-1, -1) == TileType.EMPTY)
        # OOB is solid
        check(f"Map '{name}' OOB is_solid", tm.is_solid(-1, -1) is True)

    # 4. Camera
    tm = build_guild_hub()
    cam = Camera(tm.width, tm.height, 640, 480)
    cam.follow(320.0, 240.0, 0.016)
    sx, sy = cam.world_to_screen(320, 240)
    check("Camera world_to_screen sanity", isinstance(sx, int) and isinstance(sy, int))
    vr = cam.get_visible_range()
    check("Camera visible_range tuple len", len(vr) == 4)
    min_tx, min_ty, max_tx, max_ty = vr
    check("Camera visible_range bounds", min_tx >= 0 and min_ty >= 0)
    check("Camera visible_range max", max_tx < tm.width and max_ty < tm.height)

    # 5. Draw smoke test (render to an off-screen surface)
    test_surf = pygame.Surface((640, 480))
    tm.draw(test_surf, cam, surfs)
    check("TileMap.draw() did not crash", True)

    # 6. get_map helper
    try:
        m = get_map("guild_hub")
        check("get_map('guild_hub')", m.name == "guild_hub")
    except Exception as exc:
        check("get_map('guild_hub')", False, str(exc))

    try:
        get_map("nonexistent")
        check("get_map unknown raises KeyError", False)
    except KeyError:
        check("get_map unknown raises KeyError", True)

    pygame.quit()

    print(f"\n{'=' * 56}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 56}\n")
    if failed == 0:
        print("  All tile-map systems operational.\n")


if __name__ == "__main__":
    selftest()
