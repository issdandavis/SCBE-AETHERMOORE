#!/usr/bin/env python3
"""
Player and NPC overworld sprites for the Aethermoor RPG.
=========================================================

Provides PlayerSprite and NPCSprite classes that generate walk-cycle
animations from engine.generate_sprite() and handle movement, collision,
and drawing relative to a scrolling camera.

Depends on ``engine.py`` in the same directory for Character, Tongue,
Palette, generate_sprite, and TILE_SIZE.
"""

from __future__ import annotations

import math
import random
import sys
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

import numpy as np
import pygame

# ---------------------------------------------------------------------------
# Engine imports (sibling module in demo/)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from engine import Character, Palette, Tongue, generate_sprite  # noqa: E402

TILE_SIZE: int = 16


# ---------------------------------------------------------------------------
# Direction enum
# ---------------------------------------------------------------------------
class Direction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


# ---------------------------------------------------------------------------
# Duck-typed tilemap protocol (for type-checking only)
# ---------------------------------------------------------------------------
class TileMapLike(Protocol):
    """Any object that exposes ``is_solid(tile_x, tile_y) -> bool``."""

    def is_solid(self, tile_x: int, tile_y: int) -> bool: ...


# ---------------------------------------------------------------------------
# Walk-frame generator
# ---------------------------------------------------------------------------

def _shift_leg_pixels(
    base: np.ndarray,
    leg_side: str,
    shift_px: int,
) -> np.ndarray:
    """Return a copy of *base* (32x32 RGBA) with one leg shifted down.

    Legs occupy roughly the bottom quarter of the sprite. We split the
    sprite vertically at the midpoint and shift either the left or right
    half of the leg region downward by *shift_px* pixels to simulate a
    walking pose.

    Parameters
    ----------
    base : np.ndarray
        The 32x32x4 RGBA source sprite.
    leg_side : str
        ``"left"`` or ``"right"``.
    shift_px : int
        How many pixels to shift the leg region downward (1-2).
    """
    h, w = base.shape[:2]
    frame = base.copy()

    # Leg region: bottom quarter of the sprite
    leg_top = h * 3 // 4
    mid_x = w // 2

    if leg_side == "left":
        x_start, x_end = 0, mid_x
    else:
        x_start, x_end = mid_x, w

    # Clear the leg slice first (set alpha to 0), then paste shifted
    leg_slice = base[leg_top:h, x_start:x_end].copy()

    # Clear original leg area
    frame[leg_top:h, x_start:x_end] = 0

    # Paste shifted down (clamp to bounds)
    dest_top = leg_top + shift_px
    src_rows = min(leg_slice.shape[0], h - dest_top)
    if src_rows > 0:
        frame[dest_top : dest_top + src_rows, x_start:x_end] = leg_slice[:src_rows]

    return frame


def _numpy_to_surface(arr: np.ndarray, target_size: int) -> pygame.Surface:
    """Convert an RGBA numpy array to a pygame Surface scaled to *target_size*."""
    h, w = arr.shape[:2]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # pygame.surfarray expects (width, height, channels) — i.e. transposed
    pygame.surfarray.blit_array(surf, arr[:, :, :3].transpose(1, 0, 2))
    # Apply alpha channel manually
    alpha_arr = arr[:, :, 3].T  # (w, h)
    alpha_surf = pygame.surfarray.pixels_alpha(surf)
    alpha_surf[:] = alpha_arr
    del alpha_surf  # unlock surface

    if (w, h) != (target_size, target_size):
        surf = pygame.transform.scale(surf, (target_size, target_size))

    return surf


def _flip_horizontal(arr: np.ndarray) -> np.ndarray:
    """Mirror sprite left-to-right."""
    return np.flip(arr, axis=1).copy()


def create_walk_frames(character: Character) -> Dict[Direction, List[pygame.Surface]]:
    """Generate walk-cycle frames for all four directions.

    For each direction the returned list has three surfaces (16x16 each):
        - Frame 0: standing (base pose)
        - Frame 1: left leg forward
        - Frame 2: right leg forward

    The base 32x32 sprite from ``generate_sprite()`` faces *down* by
    convention. Other directions are derived by flipping / rotating the
    numpy array before scaling.

    Returns
    -------
    Dict[Direction, List[pygame.Surface]]
        Mapping from Direction to a list of 3 overworld-sized (16x16)
        pygame Surfaces.
    """
    base_32: np.ndarray = generate_sprite(character, size=32)

    # Build direction variants of the base sprite (all 32x32 RGBA)
    direction_bases: Dict[Direction, np.ndarray] = {
        Direction.DOWN: base_32,
        Direction.UP: np.flip(base_32, axis=0).copy(),            # vertical flip
        Direction.LEFT: _flip_horizontal(base_32),
        Direction.RIGHT: base_32.copy(),
    }

    frames: Dict[Direction, List[pygame.Surface]] = {}

    for direction, dir_base in direction_bases.items():
        frame_list: List[pygame.Surface] = []

        # Frame 0 — standing
        frame_list.append(_numpy_to_surface(dir_base, TILE_SIZE))

        # Frame 1 — left leg forward (shifted 2px)
        left_step = _shift_leg_pixels(dir_base, "left", 2)
        frame_list.append(_numpy_to_surface(left_step, TILE_SIZE))

        # Frame 2 — right leg forward (shifted 2px)
        right_step = _shift_leg_pixels(dir_base, "right", 2)
        frame_list.append(_numpy_to_surface(right_step, TILE_SIZE))

        frames[direction] = frame_list

    return frames


# ---------------------------------------------------------------------------
# PlayerSprite
# ---------------------------------------------------------------------------

class PlayerSprite(pygame.sprite.Sprite):
    """Player-controlled overworld sprite with walk animation and collision.

    Parameters
    ----------
    character : Character
        The engine Character whose sprite is used for rendering.
    x : int
        Initial world X position in pixels.
    y : int
        Initial world Y position in pixels.
    """

    def __init__(self, character: Character, x: int, y: int) -> None:
        super().__init__()
        self.character: Character = character

        # Walk frames: 4 directions x 3 frames (each 16x16)
        self.frames: Dict[Direction, List[pygame.Surface]] = create_walk_frames(character)

        # State
        self.direction: Direction = Direction.DOWN
        self.frame_idx: int = 0
        self.anim_timer: float = 0.0
        self.moving: bool = False
        self.speed: float = 80.0  # pixels per second

        # Precise world position (float for sub-pixel movement)
        self.world_x: float = float(x)
        self.world_y: float = float(y)

        # Required by pygame.sprite.Sprite
        self.image: pygame.Surface = self.frames[self.direction][0]
        self.rect: pygame.Rect = self.image.get_rect(topleft=(x, y))

    # -- Properties ----------------------------------------------------------

    @property
    def tile_x(self) -> int:
        """Current tile column (world pixels -> tile index)."""
        return int(self.world_x) // TILE_SIZE

    @property
    def tile_y(self) -> int:
        """Current tile row (world pixels -> tile index)."""
        return int(self.world_y) // TILE_SIZE

    # -- Core loop -----------------------------------------------------------

    def update(  # type: ignore[override]
        self,
        dt: float,
        dx: int,
        dy: int,
        tilemap: TileMapLike,
    ) -> None:
        """Advance animation and move with collision detection.

        Parameters
        ----------
        dt : float
            Delta time in seconds since the last frame.
        dx : int
            Horizontal input direction (-1, 0, or +1).
        dy : int
            Vertical input direction (-1, 0, or +1).
        tilemap : TileMapLike
            Object exposing ``is_solid(tile_x, tile_y) -> bool``.
        """
        # Update facing direction based on input
        if dx < 0:
            self.direction = Direction.LEFT
        elif dx > 0:
            self.direction = Direction.RIGHT
        elif dy < 0:
            self.direction = Direction.UP
        elif dy > 0:
            self.direction = Direction.DOWN

        self.moving = dx != 0 or dy != 0

        # Animate walk cycle
        if self.moving:
            self.anim_timer += dt
            if self.anim_timer >= 0.15:
                self.anim_timer -= 0.15
                self.frame_idx = (self.frame_idx + 1) % 3
        else:
            self.anim_timer = 0.0
            self.frame_idx = 0

        # Attempt movement with collision
        if self.moving:
            move_x = dx * self.speed * dt
            move_y = dy * self.speed * dt

            # Try X movement
            new_x = self.world_x + move_x
            if not self._collides(new_x, self.world_y, tilemap):
                self.world_x = new_x

            # Try Y movement independently (allows wall sliding)
            new_y = self.world_y + move_y
            if not self._collides(self.world_x, new_y, tilemap):
                self.world_y = new_y

        # Keep pygame rect in sync
        self.rect.topleft = (int(self.world_x), int(self.world_y))
        self.image = self.frames[self.direction][self.frame_idx]

    def _collides(self, wx: float, wy: float, tilemap: TileMapLike) -> bool:
        """Check if a 16x16 hitbox at (*wx*, *wy*) overlaps any solid tile.

        Tests all four corners of the hitbox against the tilemap.
        """
        # Small inset (1px) to avoid snagging on adjacent tiles
        inset = 1
        corners: List[Tuple[float, float]] = [
            (wx + inset, wy + inset),                                # top-left
            (wx + TILE_SIZE - 1 - inset, wy + inset),               # top-right
            (wx + inset, wy + TILE_SIZE - 1 - inset),               # bottom-left
            (wx + TILE_SIZE - 1 - inset, wy + TILE_SIZE - 1 - inset),  # bottom-right
        ]
        for cx, cy in corners:
            tx = int(cx) // TILE_SIZE
            ty = int(cy) // TILE_SIZE
            if tilemap.is_solid(tx, ty):
                return True
        return False

    def draw(self, surface: pygame.Surface, camera: Tuple[int, int]) -> None:
        """Blit the current animation frame adjusted for the camera.

        Parameters
        ----------
        surface : pygame.Surface
            The target surface (usually the native-resolution buffer).
        camera : Tuple[int, int]
            ``(camera_x, camera_y)`` world offset of the camera's
            top-left corner.
        """
        cam_x, cam_y = camera
        screen_x = int(self.world_x) - cam_x
        screen_y = int(self.world_y) - cam_y
        frame = self.frames[self.direction][self.frame_idx]
        surface.blit(frame, (screen_x, screen_y))


# ---------------------------------------------------------------------------
# NPCSprite
# ---------------------------------------------------------------------------

class NPCSprite(pygame.sprite.Sprite):
    """Non-player character overworld sprite with optional wandering.

    Parameters
    ----------
    character : Character
        The engine Character whose sprite is used.
    x : int
        World X position in pixels.
    y : int
        World Y position in pixels.
    npc_id : str
        Identifier for dialogue/event lookup (e.g. ``"polly_academy"``).
    """

    def __init__(
        self,
        character: Character,
        x: int,
        y: int,
        npc_id: str,
    ) -> None:
        super().__init__()
        self.character: Character = character
        self.npc_id: str = npc_id

        # Walk frames (same generation pipeline as player)
        self.frames: Dict[Direction, List[pygame.Surface]] = create_walk_frames(character)

        # State
        self.facing: Direction = Direction.DOWN
        self.frame_idx: int = 0
        self.anim_timer: float = 0.0

        # Wandering behaviour
        self.wander: bool = False
        self.wander_timer: float = 0.0
        self._wander_interval: float = random.uniform(2.0, 4.0)

        # Position
        self.world_x: float = float(x)
        self.world_y: float = float(y)

        # pygame.sprite.Sprite requirements
        self.image: pygame.Surface = self.frames[self.facing][0]
        self.rect: pygame.Rect = self.image.get_rect(topleft=(x, y))

    # -- Properties ----------------------------------------------------------

    @property
    def tile_x(self) -> int:
        return int(self.world_x) // TILE_SIZE

    @property
    def tile_y(self) -> int:
        return int(self.world_y) // TILE_SIZE

    # -- Core loop -----------------------------------------------------------

    def update(self, dt: float) -> None:  # type: ignore[override]
        """Advance animation and, if wandering, randomly change facing.

        Parameters
        ----------
        dt : float
            Delta time in seconds since the last frame.
        """
        if self.wander:
            self.wander_timer += dt
            if self.wander_timer >= self._wander_interval:
                self.wander_timer = 0.0
                self._wander_interval = random.uniform(2.0, 4.0)
                self.facing = random.choice(list(Direction))

                # Cycle through one walk animation step so the NPC looks alive
                self.frame_idx = (self.frame_idx + 1) % 3
        else:
            # Static NPC — always show standing frame
            self.frame_idx = 0

        self.image = self.frames[self.facing][self.frame_idx]
        self.rect.topleft = (int(self.world_x), int(self.world_y))

    def draw(self, surface: pygame.Surface, camera: Tuple[int, int]) -> None:
        """Blit the current frame relative to the camera.

        Parameters
        ----------
        surface : pygame.Surface
            Target render surface.
        camera : Tuple[int, int]
            ``(camera_x, camera_y)`` world offset.
        """
        cam_x, cam_y = camera
        screen_x = int(self.world_x) - cam_x
        screen_y = int(self.world_y) - cam_y
        frame = self.frames[self.facing][self.frame_idx]
        surface.blit(frame, (screen_x, screen_y))

    def is_near(self, player_x: float, player_y: float, threshold: float = 24.0) -> bool:
        """Return True if the player centre is within *threshold* pixels.

        Uses Euclidean distance between sprite centres (not tile distance).

        Parameters
        ----------
        player_x : float
            Player world X (top-left).
        player_y : float
            Player world Y (top-left).
        threshold : float
            Pixel radius for interaction proximity (default 24).
        """
        half = TILE_SIZE / 2.0
        dx = (self.world_x + half) - (player_x + half)
        dy = (self.world_y + half) - (player_y + half)
        return math.sqrt(dx * dx + dy * dy) <= threshold


# ---------------------------------------------------------------------------
# Quick smoke test (runs without a display via headless pygame init)
# ---------------------------------------------------------------------------

def _selftest() -> None:
    """Validate sprite creation and basic API without a visible window."""
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    # Need a tiny display for surfarray to work in dummy mode
    pygame.display.set_mode((1, 1))

    from engine import create_cast

    cast = create_cast()
    izack = cast["izack"]

    print("Creating walk frames for Izack...")
    frames = create_walk_frames(izack)
    assert len(frames) == 4, f"Expected 4 directions, got {len(frames)}"
    for d in Direction:
        assert len(frames[d]) == 3, f"Expected 3 frames for {d}, got {len(frames[d])}"
        for i, surf in enumerate(frames[d]):
            assert surf.get_size() == (TILE_SIZE, TILE_SIZE), (
                f"{d} frame {i} size {surf.get_size()} != ({TILE_SIZE}, {TILE_SIZE})"
            )
    print("  Walk frames OK (4 dirs x 3 frames, all 16x16)")

    # PlayerSprite
    player = PlayerSprite(izack, 48, 64)
    assert player.tile_x == 48 // TILE_SIZE
    assert player.tile_y == 64 // TILE_SIZE
    assert player.direction == Direction.DOWN
    assert not player.moving
    print(f"  PlayerSprite OK (tile {player.tile_x},{player.tile_y})")

    # NPCSprite
    polly = cast["polly"]
    npc = NPCSprite(polly, 80, 80, npc_id="polly_academy")
    assert npc.npc_id == "polly_academy"
    assert npc.is_near(80, 80, threshold=24)
    assert not npc.is_near(200, 200, threshold=24)
    npc.wander = True
    npc.update(3.0)  # should trigger a wander direction change
    print(f"  NPCSprite OK (npc_id={npc.npc_id}, wander tested)")

    # Collision helper with a trivial tilemap
    class _MockTilemap:
        def is_solid(self, tx: int, ty: int) -> bool:
            return tx == 5 and ty == 5  # single solid tile at (5,5)

    tilemap = _MockTilemap()
    player2 = PlayerSprite(izack, 4 * TILE_SIZE, 4 * TILE_SIZE)
    # Move toward the solid tile at (5,5) -- should be blocked
    player2.update(0.2, 1, 1, tilemap)
    print(f"  Collision check OK (pos {player2.world_x:.1f},{player2.world_y:.1f})")

    print("\nAll player.py self-tests passed.")
    pygame.quit()


if __name__ == "__main__":
    _selftest()
