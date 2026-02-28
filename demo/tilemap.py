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
    """Pokemon RSE-style grass tile with multi-tone shading and blade clusters."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    # Base: warm mid-green like RSE routes
    base = (72, 160, 72)
    surf.fill(base)
    dark1 = (56, 136, 56)
    dark2 = (48, 120, 48)
    light1 = (88, 176, 80)
    light2 = (104, 192, 96)
    highlight = (128, 208, 112)

    # Checkerboard-ish two-tone base (like RSE grass)
    for py in range(TILE_SIZE):
        for px in range(TILE_SIZE):
            if (px + py) % 2 == 0:
                surf.set_at((px, py), dark1)

    # Blade cluster patterns (3 clusters per tile)
    clusters = [(3, 3), (10, 7), (5, 12)]
    for cx, cy in clusters:
        # Blade: 1px wide, 2-3px tall, lighter tip
        for bx, by, bh in [(-1, 0, 2), (0, -1, 3), (1, 0, 2)]:
            for h in range(bh):
                px_pos = cx + bx
                py_pos = cy + by - h
                if 0 <= px_pos < TILE_SIZE and 0 <= py_pos < TILE_SIZE:
                    c = light2 if h == bh - 1 else light1
                    surf.set_at((px_pos, py_pos), c)

    # Scattered highlight pixels (sun dappling)
    for px, py in [(1, 1), (7, 5), (14, 2), (9, 13), (2, 9)]:
        if px < TILE_SIZE and py < TILE_SIZE:
            surf.set_at((px, py), highlight)

    # Shadow pixels at bottom edge (depth cue)
    for px in range(TILE_SIZE):
        if (px * 5 + 3) % 7 < 3:
            surf.set_at((px, TILE_SIZE - 1), dark2)

    return surf


def _make_stone() -> pygame.Surface:
    """Pokemon RSE-style stone path / indoor floor with clean cobblestone."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    # Warm beige-grey like Pokemon Center floors
    base = (192, 184, 168)
    surf.fill(base)
    dark = (160, 152, 136)
    darker = (136, 128, 112)
    light = (216, 208, 196)
    highlight = (232, 224, 212)

    # Cobblestone grid: two rows of stones, offset
    # Top row: 0-7 (two stones side by side)
    for px in range(TILE_SIZE):
        surf.set_at((px, 0), darker)   # top edge
        surf.set_at((px, 7), darker)   # mid seam
        surf.set_at((px, 15), darker)  # bottom edge
    surf.set_at((7, 0), darker)        # vertical seam top row
    surf.set_at((7, 1), darker)
    surf.set_at((7, 2), darker)
    surf.set_at((7, 3), darker)
    surf.set_at((7, 4), darker)
    surf.set_at((7, 5), darker)
    surf.set_at((7, 6), darker)
    # Bottom row offset
    surf.set_at((3, 8), darker)
    surf.set_at((3, 9), darker)
    surf.set_at((3, 10), darker)
    surf.set_at((3, 11), darker)
    surf.set_at((3, 12), darker)
    surf.set_at((3, 13), darker)
    surf.set_at((3, 14), darker)
    surf.set_at((11, 8), darker)
    surf.set_at((11, 9), darker)
    surf.set_at((11, 10), darker)
    surf.set_at((11, 11), darker)
    surf.set_at((11, 12), darker)
    surf.set_at((11, 13), darker)
    surf.set_at((11, 14), darker)

    # Highlight: top-left inner corner of each stone
    for dx in range(1, 6):
        surf.set_at((dx, 1), light)
        surf.set_at((dx + 8, 1), light)
    for dx in range(1, 3):
        surf.set_at((dx, 8), light)
    for dx in range(4, 10):
        surf.set_at((dx, 8), light)
    for dx in range(12, 15):
        surf.set_at((dx, 8), light)

    # Subtle noise for texture
    for px in range(0, TILE_SIZE, 3):
        for py in range(0, TILE_SIZE, 3):
            if (px * 11 + py * 7) % 13 == 0:
                surf.set_at((px, py), dark)

    return surf


def _make_water() -> pygame.Surface:
    """Pokemon RSE-style water with rich blues and animated-look wave crests."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    # Deep Sapphire blue
    base = (48, 96, 192)
    surf.fill(base)
    mid = (56, 112, 208)
    light = (80, 144, 224)
    crest = (128, 184, 248)
    deep = (32, 72, 160)
    specular = (200, 224, 255)

    # Depth gradient: darker at top, lighter at bottom
    for py in range(TILE_SIZE):
        ratio = py / float(TILE_SIZE)
        r = int(base[0] + (mid[0] - base[0]) * ratio)
        g = int(base[1] + (mid[1] - base[1]) * ratio)
        b = int(base[2] + (mid[2] - base[2]) * ratio)
        for px in range(TILE_SIZE):
            surf.set_at((px, py), (r, g, b))

    # Wave crests (curved light lines, Pokemon style)
    # Wave 1 (row ~4)
    for px in range(TILE_SIZE):
        offset = 1 if px % 6 < 3 else 0
        surf.set_at((px, 3 + offset), light)
        if px % 3 == 1:
            surf.set_at((px, 2 + offset), crest)
    # Wave 2 (row ~10)
    for px in range(TILE_SIZE):
        offset = 1 if (px + 3) % 6 < 3 else 0
        surf.set_at((px, 10 + offset), light)
        if (px + 1) % 3 == 1:
            surf.set_at((px, 9 + offset), crest)

    # Dark troughs between waves
    for px in range(0, TILE_SIZE, 2):
        surf.set_at((px, 7), deep)

    # Specular highlights (bright sparkle dots)
    surf.set_at((4, 2), specular)
    surf.set_at((12, 9), specular)
    surf.set_at((8, 13), specular)

    return surf


def _make_wall() -> pygame.Surface:
    """Pokemon RSE-style building wall / cliff face with proper brick & shadow."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    # Dark grey-brown like Pokemon building exteriors
    base = (72, 64, 80)
    surf.fill(base)
    mortar = (56, 48, 64)
    face_light = (88, 80, 96)
    face_dark = (64, 56, 72)
    highlight = (104, 96, 112)
    shadow = (40, 32, 48)

    # Brick rows with offset pattern
    brick_h = 4
    for row_idx in range(4):
        y0 = row_idx * brick_h
        # Mortar line (horizontal seam)
        for px in range(TILE_SIZE):
            surf.set_at((px, y0), mortar)

        offset = 4 if row_idx % 2 else 0
        # Vertical mortar seams
        for seam_x in range(offset, TILE_SIZE, 8):
            for dy in range(1, brick_h):
                if y0 + dy < TILE_SIZE:
                    surf.set_at((seam_x, y0 + dy), mortar)

        # Brick faces: top highlight, bottom shadow
        for dy in range(1, brick_h):
            for px in range(TILE_SIZE):
                y = y0 + dy
                if y >= TILE_SIZE:
                    break
                # Skip mortar columns
                seam_x = offset
                is_mortar = False
                while seam_x < TILE_SIZE:
                    if px == seam_x:
                        is_mortar = True
                        break
                    seam_x += 8
                if is_mortar:
                    continue
                if dy == 1:
                    surf.set_at((px, y), face_light)   # top of brick = lit
                elif dy == brick_h - 1:
                    surf.set_at((px, y), face_dark)    # bottom = shadow
                else:
                    surf.set_at((px, y), base)

    # Top edge highlight (if wall has a cap)
    for px in range(TILE_SIZE):
        surf.set_at((px, 0), highlight)

    # Bottom shadow edge
    for px in range(TILE_SIZE):
        surf.set_at((px, TILE_SIZE - 1), shadow)

    return surf


def _make_warp() -> pygame.Surface:
    """Pokemon RSE-style warp pad / portal with concentric glow rings."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    # Dark base (like a teleport pad)
    surf.fill((24, 24, 48))
    mid = TILE_SIZE // 2
    # Concentric circles with alternating bright/dim
    for py in range(TILE_SIZE):
        for px in range(TILE_SIZE):
            dx = px - mid + 0.5
            dy = py - mid + 0.5
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < 2:
                surf.set_at((px, py), (255, 248, 200))  # bright center
            elif dist < 3.5:
                surf.set_at((px, py), (255, 220, 100))  # inner ring gold
            elif dist < 5:
                surf.set_at((px, py), (200, 160, 60))   # mid ring amber
            elif dist < 6.5:
                surf.set_at((px, py), (140, 100, 40))   # outer ring dim
            elif dist < 7.5:
                surf.set_at((px, py), (80, 56, 32))     # fade ring
    # Cardinal sparkle points
    for dx, dy in [(0, -6), (0, 6), (-6, 0), (6, 0)]:
        px, py = mid + dx, mid + dy
        if 0 <= px < TILE_SIZE and 0 <= py < TILE_SIZE:
            surf.set_at((px, py), (255, 255, 220))
    return surf


def _make_encounter() -> pygame.Surface:
    """Pokemon RSE-style tall grass with visible blade tops and darker tone."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    # Darker green base (clearly different from regular grass)
    base = (48, 128, 48)
    dark = (36, 104, 36)
    mid = (56, 144, 56)
    light_tip = (96, 192, 80)
    bright_tip = (128, 216, 104)

    surf.fill(base)

    # Checkerboard undertone
    for py in range(TILE_SIZE):
        for px in range(TILE_SIZE):
            if (px + py) % 2 == 0:
                surf.set_at((px, py), dark)

    # Tall grass blades (Pokemon style: V-shaped blade pairs)
    blade_positions = [(2, 0), (6, 1), (10, 0), (14, 1), (4, 7), (8, 8), (12, 7), (1, 8)]
    for bx, by in blade_positions:
        # Left blade
        if 0 <= bx - 1 < TILE_SIZE:
            for h in range(4):
                py_pos = by + 3 - h
                px_pos = bx - 1 if h > 1 else bx
                if 0 <= px_pos < TILE_SIZE and 0 <= py_pos < TILE_SIZE:
                    c = bright_tip if h == 0 else (light_tip if h == 1 else mid)
                    surf.set_at((px_pos, py_pos), c)
        # Right blade
        if 0 <= bx + 1 < TILE_SIZE:
            for h in range(4):
                py_pos = by + 3 - h
                px_pos = bx + 1 if h > 1 else bx
                if 0 <= px_pos < TILE_SIZE and 0 <= py_pos < TILE_SIZE:
                    c = bright_tip if h == 0 else (light_tip if h == 1 else mid)
                    surf.set_at((px_pos, py_pos), c)

    return surf


def _make_npc_spot() -> pygame.Surface:
    """Pokemon RSE-style NPC standing spot: clean stone with subtle marker."""
    surf = _make_stone()
    mid = TILE_SIZE // 2
    # Small decorative diamond (gold)
    pts = [
        (mid, mid - 2),
        (mid - 2, mid),
        (mid, mid + 2),
        (mid + 2, mid),
    ]
    pygame.draw.polygon(surf, (248, 208, 80), pts)
    # Inner bright pixel
    surf.set_at((mid, mid), (255, 240, 160))
    return surf


def _make_chest() -> pygame.Surface:
    """Pokemon RSE-style treasure chest on stone floor."""
    surf = _make_stone()
    cx, cy = TILE_SIZE // 2, TILE_SIZE // 2
    # Shadow under chest
    pygame.draw.rect(surf, (120, 112, 100), (cx - 5, cy + 3, 10, 2))
    # Chest body (warm brown)
    body = (168, 104, 48)
    body_dark = (128, 80, 32)
    body_light = (200, 136, 72)
    pygame.draw.rect(surf, body, (cx - 4, cy - 1, 8, 5))
    # Bottom edge shadow
    pygame.draw.rect(surf, body_dark, (cx - 4, cy + 3, 8, 1))
    # Lid (slightly wider, lighter)
    pygame.draw.rect(surf, body_light, (cx - 5, cy - 3, 10, 3))
    # Lid top highlight
    for px in range(cx - 4, cx + 5):
        surf.set_at((px, cy - 3), (224, 168, 96))
    # Outline
    pygame.draw.rect(surf, (64, 40, 16), (cx - 5, cy - 3, 10, 7), 1)
    # Gold clasp (center)
    surf.set_at((cx, cy), (255, 220, 80))
    surf.set_at((cx - 1, cy), (255, 220, 80))
    surf.set_at((cx, cy - 1), (255, 220, 80))
    # Clasp highlight
    surf.set_at((cx, cy - 1), (255, 248, 160))
    return surf


def _make_stair(direction: str) -> pygame.Surface:
    """Pokemon RSE-style staircase tile with clear step pattern and arrow.

    Parameters
    ----------
    direction : str
        ``'up'`` or ``'down'``.
    """
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    # Stone base
    base = (176, 168, 152)
    step_light = (208, 200, 184)
    step_dark = (144, 136, 120)
    edge = (112, 104, 88)
    arrow_color = (255, 220, 80)

    surf.fill(base)

    # Draw 4 visible stair steps (horizontal bands)
    step_h = TILE_SIZE // 4
    for i in range(4):
        y0 = i * step_h
        # Step face
        for py in range(y0, min(y0 + step_h, TILE_SIZE)):
            for px in range(TILE_SIZE):
                surf.set_at((px, py), base)
        # Top edge of step (highlight)
        for px in range(TILE_SIZE):
            if y0 < TILE_SIZE:
                surf.set_at((px, y0), step_light)
        # Bottom edge of step (shadow)
        if y0 + step_h - 1 < TILE_SIZE:
            for px in range(TILE_SIZE):
                surf.set_at((px, y0 + step_h - 1), step_dark)
        # Left & right wall edges
        for py in range(y0, min(y0 + step_h, TILE_SIZE)):
            surf.set_at((0, py), edge)
            surf.set_at((TILE_SIZE - 1, py), edge)

    # Arrow indicator
    mid = TILE_SIZE // 2
    if direction == "up":
        # Upward triangle
        for row in range(4):
            for dx in range(-row, row + 1):
                px = mid + dx
                py = mid + row - 1
                if 0 <= px < TILE_SIZE and 0 <= py < TILE_SIZE:
                    surf.set_at((px, py), arrow_color)
    else:
        # Downward triangle
        for row in range(4):
            for dx in range(-row, row + 1):
                px = mid + dx
                py = mid - row + 1
                if 0 <= px < TILE_SIZE and 0 <= py < TILE_SIZE:
                    surf.set_at((px, py), arrow_color)

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
    # Provide a fallback surface for EMPTY tiles so they don't render as
    # black holes if the camera overshoots or a tile is left unset.
    empty_surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    empty_surf.fill((24, 28, 20))  # dark earth tone (matches game_surface.fill)

    return {
        TileType.EMPTY:      empty_surf,
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
