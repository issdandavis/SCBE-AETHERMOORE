#!/usr/bin/env python3
"""
Aethermoor: Six Tongues Protocol — Pygame Graphical Client
===========================================================
GBA Pokemon Sapphire-era visual style (240x160 native, 3x scaled to 720x480).

Controls:
  Arrow keys / WASD  — Navigate menus, move character
  Z / Enter          — Confirm / advance dialogue
  X / Backspace      — Cancel / back
  ESC                — Pause menu
  F11                — Toggle fullscreen

Requires: pygame-ce (pip install pygame-ce)
"""

from __future__ import annotations

import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure engine is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

try:
    import pygame
    import pygame.freetype
except ImportError:
    print("ERROR: pygame-ce required. Install with: pip install pygame-ce")
    sys.exit(1)

from engine import (
    GAME_TITLE, NATIVE_W, NATIVE_H, SCALE, SCREEN_W, SCREEN_H, FPS,
    TILE_SIZE, Palette, Tongue, TONGUE_NAMES, TONGUE_CHART, TONGUE_WEIGHTS,
    EvoStage, Character, Stats, Spell, GamePhase, GameState,
    TrainingExporter, create_cast, generate_sprite, calculate_damage,
    scene_earth_morning, scene_earth_work, scene_earth_evening,
    scene_earth_night, scene_transit, scene_aethermoor_arrival,
)


# ---------------------------------------------------------------------------
# Pygame initialization
# ---------------------------------------------------------------------------
os.environ["SDL_VIDEO_CENTERED"] = "1"
pygame.init()
pygame.display.set_caption(GAME_TITLE)

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
native_surf = pygame.Surface((NATIVE_W, NATIVE_H))
clock = pygame.time.Clock()

# Font — use pygame's built-in if no system font available
try:
    FONT_SM = pygame.freetype.SysFont("consolas", 8)
    FONT_MD = pygame.freetype.SysFont("consolas", 10)
    FONT_LG = pygame.freetype.SysFont("consolas", 14)
except Exception:
    FONT_SM = pygame.freetype.SysFont(None, 8)
    FONT_MD = pygame.freetype.SysFont(None, 10)
    FONT_LG = pygame.freetype.SysFont(None, 14)


# ---------------------------------------------------------------------------
# Sprite cache (convert numpy sprites to pygame surfaces)
# ---------------------------------------------------------------------------
_sprite_cache: Dict[str, pygame.Surface] = {}


def get_sprite(character: Character, size: int = 32) -> pygame.Surface:
    """Get or create a pygame surface from character sprite data."""
    key = f"{character.name}_{character.evo_stage.value}_{size}"
    if key not in _sprite_cache:
        arr = generate_sprite(character, size)
        # numpy (H, W, 4) RGBA -> pygame surface
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        # Blit pixel by pixel from numpy array
        for y in range(size):
            for x in range(size):
                r, g, b, a = arr[y, x]
                if a > 0:
                    surf.set_at((x, y), (int(r), int(g), int(b), int(a)))
        _sprite_cache[key] = surf
    return _sprite_cache[key]


# ---------------------------------------------------------------------------
# UI Drawing Helpers
# ---------------------------------------------------------------------------
def draw_box(surf: pygame.Surface, x: int, y: int, w: int, h: int,
             bg: Tuple = Palette.UI_BG, border: Tuple = Palette.UI_BORDER,
             alpha: int = 220):
    """Draw a GBA-style UI box with border."""
    box = pygame.Surface((w, h), pygame.SRCALPHA)
    box.fill((*bg, alpha))
    pygame.draw.rect(box, border, (0, 0, w, h), 1)
    # Inner highlight
    pygame.draw.line(box, (*border, 100), (1, 1), (w - 2, 1))
    pygame.draw.line(box, (*border, 100), (1, 1), (1, h - 2))
    surf.blit(box, (x, y))


def draw_text(surf: pygame.Surface, text: str, x: int, y: int,
              color: Tuple = Palette.UI_TEXT, font=None, max_width: int = 0):
    """Draw text with optional wrapping."""
    if font is None:
        font = FONT_SM
    if max_width <= 0:
        font.render_to(surf, (x, y), text, color)
        return
    # Word wrap
    words = text.split()
    line = ""
    line_y = y
    for word in words:
        test = f"{line} {word}".strip()
        rect = font.get_rect(test)
        if rect.width > max_width and line:
            font.render_to(surf, (x, line_y), line, color)
            line_y += rect.height + 2
            line = word
        else:
            line = test
    if line:
        font.render_to(surf, (x, line_y), line, color)


def draw_hp_bar(surf: pygame.Surface, x: int, y: int, w: int, h: int,
                current: int, maximum: int):
    """Draw an HP bar with color gradient."""
    ratio = max(0, min(1, current / max(1, maximum)))
    fill_w = int(w * ratio)
    if ratio > 0.5:
        color = Palette.HP_GREEN
    elif ratio > 0.25:
        color = Palette.HP_YELLOW
    else:
        color = Palette.HP_RED
    pygame.draw.rect(surf, (20, 20, 20), (x, y, w, h))
    if fill_w > 0:
        pygame.draw.rect(surf, color, (x, y, fill_w, h))
    pygame.draw.rect(surf, Palette.UI_BORDER, (x, y, w, h), 1)


def draw_xp_bar(surf: pygame.Surface, x: int, y: int, w: int, h: int,
                prof: float):
    """Draw tongue proficiency bar."""
    fill_w = int(w * min(1, prof))
    pygame.draw.rect(surf, (20, 20, 20), (x, y, w, h))
    if fill_w > 0:
        pygame.draw.rect(surf, Palette.XP_BLUE, (x, y, fill_w, h))
    pygame.draw.rect(surf, Palette.UI_BORDER, (x, y, w, h), 1)


# ---------------------------------------------------------------------------
# Background generators
# ---------------------------------------------------------------------------
def gen_bg_earth(time_of_day: str) -> pygame.Surface:
    """Generate an Earth background."""
    bg = pygame.Surface((NATIVE_W, NATIVE_H))
    if time_of_day == "morning":
        # Sunrise gradient
        for y in range(NATIVE_H):
            r = int(135 + (255 - 135) * (1 - y / NATIVE_H) * 0.3)
            g = int(160 + (200 - 160) * (1 - y / NATIVE_H) * 0.3)
            b = int(200 + (235 - 200) * (y / NATIVE_H))
            bg.set_at((0, y), (r, g, b))
            pygame.draw.line(bg, (r, g, b), (0, y), (NATIVE_W, y))
    elif time_of_day == "afternoon":
        for y in range(NATIVE_H):
            t = y / NATIVE_H
            bg.set_at((0, y), (int(180 - 60 * t), int(200 - 80 * t), int(220 - 40 * t)))
            pygame.draw.line(bg, (int(180 - 60 * t), int(200 - 80 * t), int(220 - 40 * t)),
                           (0, y), (NATIVE_W, y))
    elif time_of_day == "evening":
        for y in range(NATIVE_H):
            t = y / NATIVE_H
            bg.set_at((0, y), (int(120 - 80 * t), int(80 - 40 * t), int(100 - 30 * t)))
            pygame.draw.line(bg, (int(120 - 80 * t), int(80 - 40 * t), int(100 - 30 * t)),
                           (0, y), (NATIVE_W, y))
    else:  # night
        bg.fill(Palette.BG_EARTH)
        # Stars
        for _ in range(40):
            sx = random.randint(0, NATIVE_W - 1)
            sy = random.randint(0, NATIVE_H // 2)
            brightness = random.randint(150, 255)
            bg.set_at((sx, sy), (brightness, brightness, brightness))

    # Ground
    ground_y = NATIVE_H - 20
    pygame.draw.rect(bg, Palette.GRASS if time_of_day != "night" else (30, 50, 30),
                     (0, ground_y, NATIVE_W, 20))
    return bg


def gen_bg_aethermoor() -> pygame.Surface:
    """Generate Aethermoor floating island background."""
    bg = pygame.Surface((NATIVE_W, NATIVE_H))
    # Purple sky gradient
    for y in range(NATIVE_H):
        t = y / NATIVE_H
        r = int(68 - 30 * t)
        g = int(52 - 20 * t)
        b = int(120 + 40 * t)
        pygame.draw.line(bg, (max(0, r), max(0, g), min(255, b)), (0, y), (NATIVE_W, y))

    # Floating islands
    for _ in range(5):
        ix = random.randint(20, NATIVE_W - 40)
        iy = random.randint(40, NATIVE_H - 40)
        iw = random.randint(20, 50)
        ih = random.randint(8, 14)
        # Island top (grass-purple)
        pygame.draw.ellipse(bg, Palette.FLOAT_ISL, (ix, iy, iw, ih))
        # Dangling rocks
        for d in range(3):
            dx = ix + iw // 2 + random.randint(-5, 5)
            dy = iy + ih + d * 4
            pygame.draw.circle(bg, (60, 50, 100), (dx, dy), 2)

    # Stars/sparkles
    for _ in range(30):
        sx = random.randint(0, NATIVE_W - 1)
        sy = random.randint(0, NATIVE_H - 1)
        color = random.choice([Palette.KO, Palette.AV, Palette.CA, Palette.UM])
        bg.set_at((sx, sy), color)

    return bg


def gen_bg_battle() -> pygame.Surface:
    """Generate battle arena background."""
    bg = pygame.Surface((NATIVE_W, NATIVE_H))
    # Dark gradient
    for y in range(NATIVE_H):
        t = y / NATIVE_H
        r = int(20 + 30 * t)
        g = int(15 + 20 * t)
        b = int(40 + 50 * (1 - t))
        pygame.draw.line(bg, (r, g, b), (0, y), (NATIVE_W, y))
    # Hexagonal arena floor
    cx, cy = NATIVE_W // 2, NATIVE_H - 30
    for i in range(6):
        angle = math.pi / 3 * i
        next_angle = math.pi / 3 * (i + 1)
        x1 = cx + int(60 * math.cos(angle))
        y1 = cy + int(20 * math.sin(angle))
        x2 = cx + int(60 * math.cos(next_angle))
        y2 = cy + int(20 * math.sin(next_angle))
        tongue = list(Palette.TONGUE_COLORS.values())[i]
        pygame.draw.line(bg, tongue, (x1, y1), (x2, y2), 1)
        pygame.draw.line(bg, tongue, (cx, cy), (x1, y1), 1)
    return bg


# Pre-generate backgrounds (with fixed random seed for consistency)
random.seed(42)
BG_CACHE = {
    "morning": gen_bg_earth("morning"),
    "afternoon": gen_bg_earth("afternoon"),
    "evening": gen_bg_earth("evening"),
    "night": gen_bg_earth("night"),
    "aethermoor": gen_bg_aethermoor(),
    "battle": gen_bg_battle(),
}
random.seed()


# ---------------------------------------------------------------------------
# Scene Renderer
# ---------------------------------------------------------------------------
class SceneRenderer:
    """Renders the current game scene to the native surface."""

    def __init__(self):
        self.dialogue_visible = True
        self.choice_visible = False
        self.text_scroll = 0
        self.text_timer = 0.0
        self.char_index = 0  # For typewriter effect
        self.current_text = ""
        self.flash_timer = 0.0
        self.particles: List[Dict] = []

    def render(self, state: GameState, dt: float):
        """Render current state to native_surf."""
        native_surf.fill(Palette.BLACK)

        if state.phase == GamePhase.BATTLE:
            self._render_battle(state, dt)
        elif state.phase == GamePhase.EVOLUTION:
            self._render_evolution(state, dt)
        elif state.phase == GamePhase.MENU:
            self._render_menu(state)
        elif state.phase == GamePhase.TRANSIT:
            self._render_transit(state, dt)
        else:
            self._render_scene(state, dt)

    def _render_scene(self, state: GameState, dt: float):
        """Render exploration/dialogue scene."""
        # Background
        bg_key = state.time_of_day
        if state.phase in (GamePhase.AETHERMOOR,):
            bg_key = "aethermoor"
        bg = BG_CACHE.get(bg_key, BG_CACHE["night"])
        native_surf.blit(bg, (0, 0))

        # Location text
        draw_text(native_surf, state.location, 4, 2, Palette.UI_SELECT, FONT_SM)

        # Party sprites (bottom-left area)
        sx = 8
        for i, member in enumerate(state.party[:4]):
            sprite = get_sprite(member, 32)
            # Bob animation
            bob = int(2 * math.sin(time.time() * 2 + i * 0.8))
            native_surf.blit(sprite, (sx, NATIVE_H - 70 + bob))
            # Name tag
            draw_text(native_surf, member.name[:6], sx, NATIVE_H - 36,
                     Palette.TONGUE_COLORS.get(member.tongue_affinity.value, Palette.WHITE),
                     FONT_SM)
            sx += 36

        # Dialogue box
        if state.dialogue_queue:
            self._render_dialogue(state, dt)

        # Choice menu
        if state.choices and not state.dialogue_queue:
            self._render_choices(state)

    def _render_dialogue(self, state: GameState, dt: float):
        """Render dialogue box with typewriter effect."""
        box_h = 40
        box_y = NATIVE_H - box_h - 2
        draw_box(native_surf, 2, box_y, NATIVE_W - 4, box_h)

        if state.current_dialogue_idx < len(state.dialogue_queue):
            full_text = state.dialogue_queue[state.current_dialogue_idx]

            # Typewriter effect
            self.text_timer += dt * 60  # chars per second
            visible_chars = min(len(full_text), int(self.text_timer))
            display_text = full_text[:visible_chars]

            draw_text(native_surf, display_text, 6, box_y + 4,
                     Palette.UI_TEXT, FONT_SM, max_width=NATIVE_W - 14)

            # Advance indicator
            if visible_chars >= len(full_text):
                blink = int(time.time() * 3) % 2
                if blink:
                    draw_text(native_surf, "v", NATIVE_W - 12, box_y + box_h - 10,
                             Palette.UI_SELECT, FONT_SM)

    def _render_choices(self, state: GameState):
        """Render choice menu."""
        n = len(state.choices)
        box_h = 10 + n * 12
        box_y = NATIVE_H - box_h - 2
        draw_box(native_surf, 2, box_y, NATIVE_W - 4, box_h)

        for i, (label, _) in enumerate(state.choices):
            color = Palette.UI_SELECT if i == state.selected_choice else Palette.UI_TEXT
            prefix = "> " if i == state.selected_choice else "  "
            draw_text(native_surf, f"{prefix}{label}", 6, box_y + 4 + i * 12,
                     color, FONT_SM)

    def _render_battle(self, state: GameState, dt: float):
        """Render battle screen."""
        native_surf.blit(BG_CACHE["battle"], (0, 0))

        # Title
        draw_text(native_surf, "-- BATTLE --", NATIVE_W // 2 - 30, 2,
                 Palette.HP_RED, FONT_MD)

        if not state.battle_enemies:
            return

        enemy = state.battle_enemies[0]
        player = state.party[0] if state.party else None

        # Enemy sprite (top right, larger)
        enemy_sprite = get_sprite(enemy, 32)
        enemy_sprite_big = pygame.transform.scale(enemy_sprite, (48, 48))
        native_surf.blit(enemy_sprite_big, (NATIVE_W - 60, 15))

        # Enemy info box
        draw_box(native_surf, NATIVE_W - 110, 10, 48, 20)
        draw_text(native_surf, enemy.name[:8], NATIVE_W - 108, 12,
                 Palette.HP_RED, FONT_SM)
        draw_hp_bar(native_surf, NATIVE_W - 108, 22, 44, 4,
                   enemy.stats.hp, enemy.stats.max_hp)

        # Player sprite (bottom left, larger)
        if player:
            player_sprite = get_sprite(player, 32)
            player_sprite_big = pygame.transform.scale(player_sprite, (48, 48))
            native_surf.blit(player_sprite_big, (12, 60))

            # Player info box
            draw_box(native_surf, 2, 112, 80, 30)
            draw_text(native_surf, player.name[:8], 4, 114,
                     Palette.UI_TEXT, FONT_SM)
            draw_text(native_surf, f"Lv.{player.stats.level}", 50, 114,
                     Palette.UI_SELECT, FONT_SM)
            draw_hp_bar(native_surf, 4, 124, 74, 4,
                       player.stats.hp, player.stats.max_hp)
            # MP bar
            draw_text(native_surf, "MP", 4, 131, Palette.AV, FONT_SM)
            draw_xp_bar(native_surf, 16, 132, 62, 3,
                       player.stats.mp / max(1, player.stats.max_mp))

        # Dialogue (battle log)
        if state.dialogue_queue:
            self._render_dialogue(state, dt)
        elif state.choices:
            self._render_choices(state)

        # Particles
        self._update_particles(dt)

    def _render_transit(self, state: GameState, dt: float):
        """Render the isekai transition sequence."""
        # Swirling void effect
        t = time.time()
        for y in range(NATIVE_H):
            for x in range(0, NATIVE_W, 2):
                wave = math.sin(x * 0.05 + t * 3) * math.cos(y * 0.03 + t * 2)
                r = int(40 + 30 * wave)
                g = int(20 + 20 * abs(wave))
                b = int(80 + 60 * wave)
                native_surf.set_at((x, y), (max(0, min(255, r)),
                                             max(0, min(255, g)),
                                             max(0, min(255, b))))

        # Spiral particles
        for i in range(20):
            angle = t * 2 + i * math.pi / 10
            radius = 30 + 20 * math.sin(t + i)
            px = int(NATIVE_W // 2 + radius * math.cos(angle))
            py = int(NATIVE_H // 2 + radius * math.sin(angle))
            tongue_colors = list(Palette.TONGUE_COLORS.values())
            color = tongue_colors[i % 6]
            if 0 <= px < NATIVE_W and 0 <= py < NATIVE_H:
                pygame.draw.circle(native_surf, color, (px, py), 2)

        # Dialogue on top
        if state.dialogue_queue:
            self._render_dialogue(state, dt)

    def _render_evolution(self, state: GameState, dt: float):
        """Render evolution animation."""
        native_surf.fill((10, 5, 30))

        t = time.time()
        # Pulsing light
        radius = int(20 + 15 * abs(math.sin(t * 4)))
        cx, cy = NATIVE_W // 2, NATIVE_H // 2 - 10
        for r in range(radius, 0, -2):
            alpha = int(200 * (r / radius))
            color = (min(255, 200 + alpha // 4), min(255, 180 + alpha // 3), 255)
            pygame.draw.circle(native_surf, color, (cx, cy), r)

        # Character sprite in center
        if state.party:
            sprite = get_sprite(state.party[0], 32)
            sprite_big = pygame.transform.scale(sprite, (48, 48))
            native_surf.blit(sprite_big, (cx - 24, cy - 24))

        draw_text(native_surf, "EVOLUTION!", cx - 25, 8, Palette.UI_SELECT, FONT_MD)

        if state.dialogue_queue:
            self._render_dialogue(state, dt)

    def _render_menu(self, state: GameState):
        """Render pause menu."""
        native_surf.fill((10, 10, 20))
        draw_box(native_surf, 20, 10, NATIVE_W - 40, NATIVE_H - 20)

        draw_text(native_surf, GAME_TITLE, 30, 16, Palette.UI_SELECT, FONT_MD)
        draw_text(native_surf, f"Day {state.day}", 30, 30, Palette.UI_TEXT, FONT_SM)
        draw_text(native_surf, f"Location: {state.location}", 30, 40,
                 Palette.UI_TEXT, FONT_SM)

        # Party stats
        y = 55
        for member in state.party[:6]:
            tongue_color = Palette.TONGUE_COLORS.get(
                member.tongue_affinity.value, Palette.WHITE)
            draw_text(native_surf, f"{member.name[:8]} [{member.evo_stage.value}]",
                     30, y, tongue_color, FONT_SM)
            draw_hp_bar(native_surf, 120, y + 1, 60, 4,
                       member.stats.hp, member.stats.max_hp)
            draw_text(native_surf, f"Lv.{member.stats.level}", 185, y,
                     Palette.UI_TEXT, FONT_SM)
            y += 12

        # Tongue proficiencies
        if state.party:
            player = state.party[0]
            y += 5
            draw_text(native_surf, "Tongue Proficiency:", 30, y,
                     Palette.UI_SELECT, FONT_SM)
            y += 10
            for tongue in Tongue:
                prof = player.stats.tongue_prof.get(tongue.value, 0.0)
                tcolor = Palette.TONGUE_COLORS.get(tongue.value, Palette.WHITE)
                draw_text(native_surf, f"{tongue.value}", 30, y, tcolor, FONT_SM)
                draw_xp_bar(native_surf, 50, y + 1, 60, 4, prof)
                draw_text(native_surf, f"{int(prof * 100)}%", 115, y,
                         Palette.UI_TEXT, FONT_SM)
                y += 9

        # Training data counter
        draw_text(native_surf, f"Training pairs: {state.exporter.total_pairs}",
                 30, NATIVE_H - 22, Palette.AV, FONT_SM)
        draw_text(native_surf, "ESC to resume", NATIVE_W - 70, NATIVE_H - 22,
                 Palette.UI_BORDER, FONT_SM)

    def _update_particles(self, dt: float):
        """Update and draw floating particles."""
        # Remove dead particles
        self.particles = [p for p in self.particles if p["life"] > 0]
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
            alpha = int(255 * (p["life"] / p["max_life"]))
            if 0 <= int(p["x"]) < NATIVE_W and 0 <= int(p["y"]) < NATIVE_H:
                color = (*p["color"][:3], max(0, alpha))
                native_surf.set_at((int(p["x"]), int(p["y"])), p["color"])

    def spawn_hit_particles(self, x: int, y: int, color: Tuple, count: int = 8):
        """Spawn particles at a hit location."""
        for _ in range(count):
            self.particles.append({
                "x": float(x), "y": float(y),
                "vx": random.uniform(-30, 30), "vy": random.uniform(-40, 10),
                "life": random.uniform(0.3, 0.8), "max_life": 0.8,
                "color": color,
            })

    def reset_typewriter(self):
        """Reset typewriter effect for new dialogue."""
        self.text_timer = 0.0


# ---------------------------------------------------------------------------
# Game Controller
# ---------------------------------------------------------------------------
class GameController:
    """Main game loop and input handling."""

    def __init__(self):
        self.state = GameState()
        self.renderer = SceneRenderer()
        self.cast = create_cast()
        self.running = True
        self.fullscreen = False
        self.battle_turn = "player"
        self.battle_spell_menu = False
        self.battle_spell_idx = 0

        # Initialize party with Izack
        self.state.party.append(self.cast["izack"])
        # Start the game
        scene_earth_morning(self.state)

    def run(self):
        """Main game loop."""
        while self.running:
            dt = clock.tick(FPS) / 1000.0
            self.handle_input()
            self.update(dt)
            self.render(dt)
        # Save training data on exit
        if self.state.exporter.total_pairs > 0:
            path = self.state.exporter.save()
            print(f"Training data saved: {path} ({self.state.exporter.total_pairs} pairs)")
        pygame.quit()

    def handle_input(self):
        """Process input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                self._handle_key(event.key)

    def _handle_key(self, key: int):
        """Handle a keypress."""
        # Global keys
        if key == pygame.K_ESCAPE:
            if self.state.phase == GamePhase.MENU:
                self.state.phase = self._prev_phase
            else:
                self._prev_phase = self.state.phase
                self.state.phase = GamePhase.MENU
            return

        if key == pygame.K_F11:
            self.fullscreen = not self.fullscreen
            if self.fullscreen:
                pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
            else:
                pygame.display.set_mode((SCREEN_W, SCREEN_H))
            return

        # Phase-specific input
        if self.state.phase == GamePhase.MENU:
            return  # ESC handled above

        if self.state.phase == GamePhase.BATTLE:
            self._handle_battle_input(key)
            return

        # Dialogue / choice navigation
        if self.state.dialogue_queue:
            if key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                self._advance_dialogue()
        elif self.state.choices:
            if key in (pygame.K_UP, pygame.K_w):
                self.state.selected_choice = max(0, self.state.selected_choice - 1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.state.selected_choice = min(
                    len(self.state.choices) - 1, self.state.selected_choice + 1)
            elif key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                self._select_choice()

    def _advance_dialogue(self):
        """Advance to next dialogue line or show choices."""
        # If typewriter hasn't finished, skip to end
        if self.state.current_dialogue_idx < len(self.state.dialogue_queue):
            full_text = self.state.dialogue_queue[self.state.current_dialogue_idx]
            if self.renderer.text_timer < len(full_text):
                self.renderer.text_timer = len(full_text) + 1
                return

        self.state.current_dialogue_idx += 1
        self.renderer.reset_typewriter()

        if self.state.current_dialogue_idx >= len(self.state.dialogue_queue):
            self.state.dialogue_queue.clear()
            self.state.current_dialogue_idx = 0

    def _select_choice(self):
        """Handle choice selection."""
        if not self.state.choices:
            return

        label, action = self.state.choices[self.state.selected_choice]
        alternatives = [l for l, _ in self.state.choices if l != label]

        # Record training data
        self.state.exporter.record_choice(
            f"In {self.state.location}, day {self.state.day}",
            label, alternatives,
            f"Player chose '{label}' (action: {action})",
        )

        self.state.clear()
        self._advance_game(action)

    def _advance_game(self, action: str):
        """Advance game state based on action."""
        phase = self.state.phase

        if phase == GamePhase.EARTH_MORNING:
            self.state.phase = GamePhase.EARTH_WORK
            scene_earth_work(self.state)

        elif phase == GamePhase.EARTH_WORK:
            self.state.phase = GamePhase.EARTH_EVENING
            scene_earth_evening(self.state)

        elif phase == GamePhase.EARTH_EVENING:
            if action == "read_book":
                self.state.phase = GamePhase.EARTH_NIGHT
                scene_earth_night(self.state)
            else:
                self.state.phase = GamePhase.EARTH_NIGHT
                scene_earth_night(self.state)

        elif phase == GamePhase.EARTH_NIGHT:
            self.state.phase = GamePhase.TRANSIT
            scene_transit(self.state)

        elif phase == GamePhase.TRANSIT:
            self.state.phase = GamePhase.AETHERMOOR
            scene_aethermoor_arrival(self.state)

        elif phase == GamePhase.AETHERMOOR:
            if action in ("learn_tongues", "ask_about_world", "ask_go_home"):
                self._start_exploration()
            elif action == "explore":
                self._start_exploration()
            elif action == "battle":
                self._start_wild_battle()
            elif action == "rest":
                self._rest()
            elif action == "train":
                self._train_tongues()
            else:
                self._start_exploration()

    def _start_exploration(self):
        """Enter Aethermoor exploration mode."""
        self.state.location = random.choice([
            "Aethermoor - Spiral Spire",
            "Aethermoor - Avalon Academy",
            "Aethermoor - Crystal Archives",
            "Aethermoor - Floating Gardens",
            "Aethermoor - World Tree (Pollyoneth)",
            "Aethermoor - Timeless Observatory",
        ])

        events = [
            "The air hums with Protocol energy. Echoes drift past like fireflies.",
            "A tongue crystal glows nearby, pulsing with " + random.choice(
                ["KO", "AV", "RU", "CA", "UM", "DR"]) + " energy.",
            "You hear distant thunder -- another dimension shifting.",
            "Polly perches on a crystal branch: 'Pay attention. The Protocol teaches.'",
            "Clay shuffles beside you, his runes glowing contentedly.",
        ]
        self.state.add_dialogue(random.choice(events))

        # Random tongue proficiency gain
        tongue = random.choice(list(Tongue))
        gain = random.uniform(0.01, 0.05)
        player = self.state.party[0]
        old_prof = player.stats.tongue_prof.get(tongue.value, 0.0)
        player.stats.tongue_prof[tongue.value] = min(1.0, old_prof + gain)
        self.state.add_dialogue(
            f"  +{gain:.2f} {tongue.value} ({TONGUE_NAMES[tongue]}) proficiency!"
        )

        # Random encounter chance
        if random.random() < 0.4:
            self.state.set_choices([
                ("A wild presence appears! Fight it", "battle"),
                ("Explore further", "explore"),
                ("Rest and meditate", "rest"),
            ])
        else:
            self.state.set_choices([
                ("Continue exploring", "explore"),
                ("Train tongue proficiency", "train"),
                ("Rest and meditate", "rest"),
            ])

    def _start_wild_battle(self):
        """Start a random battle encounter."""
        self.state.phase = GamePhase.BATTLE
        self.battle_turn = "player"
        self.battle_spell_menu = False

        # Generate wild enemy based on game day
        day = self.state.day
        hp_scale = 80 + day * 15
        atk_scale = 8 + day * 2
        tongue = random.choice(list(Tongue))
        wild_names = [
            "Rogue Echo", "Void Shard", "Drift Phantom",
            "Phase Wraith", "Corrupt Token", "Shadow Fragment",
            "Entropy Sprite", "Null Whisper",
        ]

        enemy = Character(
            name=random.choice(wild_names),
            title="Wild",
            tongue_affinity=tongue,
            evo_stage=EvoStage.ROOKIE if day < 5 else EvoStage.CHAMPION,
            stats=Stats(
                hp=hp_scale, max_hp=hp_scale,
                mp=40, max_mp=40,
                attack=atk_scale, defense=atk_scale - 2,
                speed=8 + day, wisdom=6 + day,
            ),
            spells=[
                Spell("Wild Strike", tongue, 15 + day * 3, 8,
                      f"A {tongue.value}-infused attack"),
            ],
            is_enemy=True,
        )
        self.state.battle_enemies = [enemy]

        self.state.add_dialogue(
            f"A wild {enemy.name} appears! [{tongue.value} type]"
        )
        self.state.set_choices([
            ("Fight", "fight"),
            ("Spells", "spells"),
            ("Run", "run"),
        ])

    def _handle_battle_input(self, key: int):
        """Handle input during battle."""
        if self.state.dialogue_queue:
            if key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                self._advance_dialogue()
                # After dialogue clears, check battle state
                if not self.state.dialogue_queue and not self.state.choices:
                    self._check_battle_end()
            return

        if self.battle_spell_menu:
            # Spell selection
            player = self.state.party[0]
            spells = [s for s in player.spells if s.mp_cost <= player.stats.mp]
            if not spells:
                self.battle_spell_menu = False
                return

            if key in (pygame.K_UP, pygame.K_w):
                self.battle_spell_idx = max(0, self.battle_spell_idx - 1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.battle_spell_idx = min(len(spells) - 1, self.battle_spell_idx + 1)
            elif key in (pygame.K_z, pygame.K_RETURN):
                spell = spells[self.battle_spell_idx]
                self._execute_player_spell(spell)
                self.battle_spell_menu = False
            elif key in (pygame.K_x, pygame.K_BACKSPACE):
                self.battle_spell_menu = False
                self.state.set_choices([
                    ("Fight", "fight"),
                    ("Spells", "spells"),
                    ("Run", "run"),
                ])
            # Update choices display for spell menu
            self.state.choices = [(s.name + f" ({s.mp_cost}MP)", s.name) for s in spells]
            self.state.selected_choice = self.battle_spell_idx
            return

        if self.state.choices:
            if key in (pygame.K_UP, pygame.K_w):
                self.state.selected_choice = max(0, self.state.selected_choice - 1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.state.selected_choice = min(
                    len(self.state.choices) - 1, self.state.selected_choice + 1)
            elif key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                label, action = self.state.choices[self.state.selected_choice]
                self.state.clear()

                if action == "fight":
                    self._execute_player_attack()
                elif action == "spells":
                    self.battle_spell_menu = True
                    self.battle_spell_idx = 0
                    player = self.state.party[0]
                    spells = [s for s in player.spells if s.mp_cost <= player.stats.mp]
                    if spells:
                        self.state.choices = [
                            (s.name + f" ({s.mp_cost}MP)", s.name) for s in spells
                        ]
                        self.state.selected_choice = 0
                    else:
                        self.state.add_dialogue("No MP remaining!")
                        self.battle_spell_menu = False
                        self.state.set_choices([
                            ("Fight", "fight"),
                            ("Spells", "spells"),
                            ("Run", "run"),
                        ])
                elif action == "run":
                    if random.random() < 0.6:
                        self.state.add_dialogue("Got away safely!")
                        self.state.phase = GamePhase.AETHERMOOR
                        self._start_exploration()
                    else:
                        self.state.add_dialogue("Couldn't escape!")
                        self._execute_enemy_turn()

    def _execute_player_attack(self):
        """Player uses basic attack."""
        player = self.state.party[0]
        enemy = self.state.battle_enemies[0]
        dmg, msg, crit = calculate_damage(player, enemy)
        enemy.stats.hp = max(0, enemy.stats.hp - dmg)
        self.state.add_dialogue(msg)
        self.renderer.spawn_hit_particles(NATIVE_W - 36, 40,
                                          Palette.TONGUE_COLORS.get(
                                              player.tongue_affinity.value, Palette.WHITE))

        self.state.exporter.record_battle(
            player.name, enemy.name, "Attack", dmg,
            player.tongue_affinity.value,
            "critical" if crit else "normal",
        )

        if enemy.stats.hp <= 0:
            self.state.add_dialogue(f"{enemy.name} defeated!")
        else:
            self._execute_enemy_turn()

    def _execute_player_spell(self, spell: Spell):
        """Player uses a spell."""
        player = self.state.party[0]
        enemy = self.state.battle_enemies[0]
        player.stats.mp -= spell.mp_cost
        dmg, msg, crit = calculate_damage(player, enemy, spell)
        enemy.stats.hp = max(0, enemy.stats.hp - dmg)
        self.state.add_dialogue(msg)

        # Gain proficiency
        gain = 0.02 + (0.01 if crit else 0)
        old = player.stats.tongue_prof.get(spell.tongue.value, 0.0)
        player.stats.tongue_prof[spell.tongue.value] = min(1.0, old + gain)
        self.state.add_dialogue(
            f"  +{gain:.2f} {spell.tongue.value} proficiency!"
        )

        self.renderer.spawn_hit_particles(
            NATIVE_W - 36, 40,
            Palette.TONGUE_COLORS.get(spell.tongue.value, Palette.WHITE), 12)

        self.state.exporter.record_battle(
            player.name, enemy.name, spell.name, dmg,
            spell.tongue.value,
            "critical" if crit else "super" if dmg > 30 else "normal",
        )

        if enemy.stats.hp <= 0:
            self.state.add_dialogue(f"{enemy.name} defeated!")
        else:
            self._execute_enemy_turn()

    def _execute_enemy_turn(self):
        """Enemy attacks."""
        enemy = self.state.battle_enemies[0]
        player = self.state.party[0]

        if enemy.spells and enemy.stats.mp >= enemy.spells[0].mp_cost:
            spell = enemy.spells[0]
            enemy.stats.mp -= spell.mp_cost
            dmg, msg, crit = calculate_damage(enemy, player, spell)
        else:
            dmg, msg, crit = calculate_damage(enemy, player)

        player.stats.hp = max(0, player.stats.hp - dmg)
        self.state.add_dialogue(msg)
        self.renderer.spawn_hit_particles(36, 80, Palette.HP_RED)

        if player.stats.hp <= 0:
            self.state.add_dialogue("You blacked out...")
            self.state.add_dialogue("The Protocol restores you. -1 day.")

    def _check_battle_end(self):
        """Check if battle is over."""
        if not self.state.battle_enemies:
            return

        enemy = self.state.battle_enemies[0]
        player = self.state.party[0]

        if enemy.stats.hp <= 0:
            # Victory
            self.state.phase = GamePhase.AETHERMOOR
            self.state.battle_enemies.clear()
            # Restore some MP
            player.stats.mp = min(player.stats.max_mp,
                                  player.stats.mp + player.stats.max_mp // 4)
            self._check_evolution()
            self._start_exploration()

        elif player.stats.hp <= 0:
            # Defeat — restore and penalize
            player.stats.hp = player.stats.max_hp // 2
            player.stats.mp = player.stats.max_mp // 2
            self.state.day = max(1, self.state.day - 1)
            self.state.phase = GamePhase.AETHERMOOR
            self.state.battle_enemies.clear()
            self._start_exploration()

        else:
            # Battle continues
            self.state.set_choices([
                ("Fight", "fight"),
                ("Spells", "spells"),
                ("Run", "run"),
            ])

    def _check_evolution(self):
        """Check if any party member should evolve."""
        for member in self.state.party:
            total_prof = sum(member.stats.tongue_prof.values())
            thresholds = {
                EvoStage.FRESH: 0.3,
                EvoStage.ROOKIE: 1.0,
                EvoStage.CHAMPION: 2.5,
                EvoStage.ULTIMATE: 4.0,
                EvoStage.MEGA: 5.5,
            }
            threshold = thresholds.get(member.evo_stage)
            if threshold and total_prof >= threshold:
                stages = list(EvoStage)
                current_idx = stages.index(member.evo_stage)
                if current_idx < len(stages) - 1:
                    old_stage = member.evo_stage
                    member.evo_stage = stages[current_idx + 1]
                    # Stat boost
                    member.stats.max_hp += 20
                    member.stats.hp = member.stats.max_hp
                    member.stats.max_mp += 10
                    member.stats.mp = member.stats.max_mp
                    member.stats.attack += 3
                    member.stats.defense += 3
                    member.stats.wisdom += 3

                    self.state.exporter.record_evolution(
                        member.name, old_stage.value,
                        member.evo_stage.value,
                        dict(member.stats.tongue_prof),
                    )
                    # Clear sprite cache for this character
                    keys_to_remove = [k for k in _sprite_cache if k.startswith(member.name)]
                    for k in keys_to_remove:
                        del _sprite_cache[k]

    def _rest(self):
        """Rest and recover."""
        player = self.state.party[0]
        player.stats.hp = player.stats.max_hp
        player.stats.mp = player.stats.max_mp
        self.state.day += 1
        self.state.add_dialogue("You rest at the Archives. HP and MP restored.")
        self.state.add_dialogue(f"Day {self.state.day} begins.")
        self._start_exploration()

    def _train_tongues(self):
        """Dedicated tongue training."""
        tongue = random.choice(list(Tongue))
        gain = random.uniform(0.03, 0.08)
        player = self.state.party[0]
        old = player.stats.tongue_prof.get(tongue.value, 0.0)
        player.stats.tongue_prof[tongue.value] = min(1.0, old + gain)
        self.state.add_dialogue(
            f"Polly trains you in {TONGUE_NAMES[tongue]}..."
        )
        self.state.add_dialogue(
            f"  +{gain:.2f} {tongue.value} proficiency! (now {player.stats.tongue_prof[tongue.value]:.1%})"
        )
        self.state.set_choices([
            ("Continue training", "train"),
            ("Explore", "explore"),
            ("Rest", "rest"),
        ])

    def update(self, dt: float):
        """Update game logic."""
        pass  # Most logic is event-driven via input

    def render(self, dt: float):
        """Render frame."""
        self.renderer.render(self.state, dt)
        # Scale native to screen
        scaled = pygame.transform.scale(native_surf, (SCREEN_W, SCREEN_H))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()

    _prev_phase: GamePhase = GamePhase.EARTH_MORNING


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    print(f"\n  {GAME_TITLE}")
    print(f"  {'='*40}")
    print(f"  Resolution: {SCREEN_W}x{SCREEN_H} (native {NATIVE_W}x{NATIVE_H})")
    print(f"  Controls: Arrow/WASD=move, Z/Enter=confirm, X/Back=cancel, ESC=menu")
    print(f"  Every choice generates AI training data.")
    print(f"  {'='*40}\n")

    game = GameController()
    game.run()


if __name__ == "__main__":
    main()
