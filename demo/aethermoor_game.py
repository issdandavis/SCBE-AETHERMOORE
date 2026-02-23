#!/usr/bin/env python3
"""
Aethermoor: Six Tongues Protocol -- Pilot Customer Demo
========================================================
A professional Pygame-CE demo showcasing the SCBE 14-layer governance
framework through an interactive RPG narrative.

Window: 1280x720 with a GameBoy-emulator-style bezel on the left
and a live dashboard panel on the right.

Controls:
  Arrow keys / WASD  - Navigate menus
  Enter / Space      - Advance dialogue / select
  1-7                - Quick-select choices
  Tab                - Toggle dashboard detail
  Escape             - Pause menu
  B                  - Toggle battle mode (testing)

Requires: pygame-ce >= 2.5, numpy
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pygame

# ---------------------------------------------------------------------------
# Import from the companion engine
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from engine import (
    GAME_TITLE,
    Character,
    EvoStage,
    GamePhase,
    GameState,
    Palette,
    Spell,
    Tongue,
    TONGUE_NAMES,
    TONGUE_WEIGHTS,
    TONGUE_CHART,
    TrainingExporter,
    calculate_damage,
    create_cast,
    generate_sprite,
    scene_earth_morning,
    scene_earth_work,
    scene_earth_evening,
    scene_earth_night,
    scene_transit,
    scene_aethermoor_arrival,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WINDOW_W, WINDOW_H = 1280, 720
GAME_W, GAME_H = 640, 480
DASH_X = 660  # Dashboard panel starts here
DASH_W = WINDOW_W - DASH_X
FPS_CAP = 30

GOLD = (255, 215, 80)
BEZEL_COLOR = (30, 30, 40)
BEZEL_HIGHLIGHT = (50, 50, 65)
SCREEN_BG = (16, 16, 24)
DASH_BG = (20, 20, 30)
DASH_BORDER = (55, 55, 75)
TEXT_COLOR = (230, 230, 245)
DIM_TEXT = (140, 140, 170)
CHOICE_HIGHLIGHT = (255, 220, 80)
DIALOGUE_BG = (16, 16, 32, 220)
PAUSE_OVERLAY = (0, 0, 0, 180)

# Tongue display colors keyed by two-letter code
TONGUE_COLORS: Dict[str, Tuple[int, int, int]] = {
    "KO": (220, 60, 60),
    "AV": (60, 180, 220),
    "RU": (220, 180, 60),
    "CA": (60, 220, 120),
    "UM": (140, 60, 220),
    "DR": (220, 120, 60),
}

TONGUE_FULL_NAMES: Dict[str, str] = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}

SCBE_LAYERS: List[Tuple[int, str, Tuple[int, int, int]]] = [
    (1, "Intent", (220, 60, 60)),
    (2, "Routing", (220, 60, 60)),
    (3, "Context", (60, 180, 220)),
    (4, "Memory", (60, 180, 220)),
    (5, "Constraints", (220, 180, 60)),
    (6, "Policy", (220, 180, 60)),
    (7, "Compute", (60, 220, 120)),
    (8, "Encrypt", (60, 220, 120)),
    (9, "Spectral", (140, 60, 220)),
    (10, "Quantum", (140, 60, 220)),
    (11, "Schema", (220, 120, 60)),
    (12, "Auth", (220, 120, 60)),
    (13, "Governance", (255, 220, 80)),
    (14, "Integration", (255, 220, 80)),
]

# Background colors per location mood
BG_COLORS: Dict[str, Tuple[int, int, int]] = {
    "earth": (42, 46, 58),
    "aethermoor": (68, 52, 120),
    "battle": (58, 28, 32),
    "academy": (72, 64, 52),
    "transit": (24, 16, 48),
    "title": (12, 8, 24),
}

# ---------------------------------------------------------------------------
# Enhanced choice definitions for each scene
# Each choice: (label, action_key, tongue_code, active_layers)
# ---------------------------------------------------------------------------
SCENE_CHOICES: Dict[str, List[Tuple[str, str, str, List[int]]]] = {
    "earth_morning": [
        ("Check the terminal -- trace those anomalous logs", "trace", "CA", [1, 7, 8]),
        ("Call the security team -- this needs escalation", "escalate", "KO", [1, 2, 13]),
        ("Get coffee first -- collect your thoughts", "coffee", "RU", [5, 6]),
        ("Message your research partner about the patterns", "message", "AV", [3, 4]),
        ("Check the apartment's security system", "security", "UM", [9, 10]),
        ("Document everything in your encrypted journal", "document", "DR", [11, 12]),
        ("Go back to sleep -- ignore the noise", "sleep", "RU", [5, 6, 13]),
    ],
    "earth_work": [
        ("Trace the anomaly deeper into the routing fabric", "trace_deep", "CA", [1, 7, 8]),
        ("Document and escalate to the security council", "escalate_sec", "KO", [1, 2, 13]),
        ("Run a spectral analysis on the folding patterns", "spectral", "UM", [9, 10]),
        ("Cross-reference with the dimensional theory papers", "research", "AV", [3, 4]),
        ("Write a containment script to isolate the anomaly", "contain", "DR", [11, 12]),
        ("Talk to your colleague about the 'dimensional' joke", "colleague", "RU", [5, 6]),
        ("Ignore it -- probably just clock drift", "ignore", "RU", [5, 6, 14]),
    ],
    "earth_evening": [
        ("Read the mysterious book immediately", "read_book", "DR", [11, 12, 3]),
        ("Check if someone broke into your apartment", "check_apt", "UM", [9, 10]),
        ("Call the police -- this is a break-in", "call_police", "KO", [1, 2, 13]),
        ("Photograph the book and send it to your team", "photo", "AV", [3, 4]),
        ("Run the book's title through your research database", "database", "CA", [7, 8]),
        ("Set up a surveillance camera and wait", "surveille", "UM", [9, 10, 14]),
        ("Just go to bed -- you are exhausted", "bed", "RU", [5, 6]),
    ],
    "earth_night": [
        ("'I intend to understand.' (Scholar's path)", "intent_understand", "CA", [1, 7, 8, 14]),
        ("'I intend to protect.' (Guardian's path)", "intent_protect", "KO", [1, 2, 13, 14]),
        ("'I intend to create.' (Architect's path)", "intent_create", "DR", [1, 11, 12, 14]),
        ("'I intend to explore.' (Navigator's path)", "intent_explore", "AV", [1, 3, 4, 14]),
        ("'I intend to endure.' (Sentinel's path)", "intent_endure", "RU", [1, 5, 6, 14]),
        ("'I intend to uncover.' (Shadow's path)", "intent_uncover", "UM", [1, 9, 10, 14]),
    ],
    "aethermoor_arrival": [
        ("'Teach me everything.' -- Embrace the Protocol", "learn_all", "CA", [1, 7, 8, 14]),
        ("'Where am I? What is this place?'", "ask_world", "AV", [3, 4]),
        ("'How do I get home?' -- Find an exit", "ask_home", "RU", [5, 6]),
        ("'Show me how to fight.' -- Learn combat", "learn_fight", "KO", [1, 2]),
        ("'What are the Six Sacred Tongues?'", "ask_tongues", "DR", [11, 12]),
        ("'Something feels wrong. Is this place safe?'", "sense_danger", "UM", [9, 10]),
        ("Pet Clay on the head", "pet_clay", "RU", [5, 6, 13]),
    ],
    "academy_entrance": [
        ("Enter through the main gate -- announce yourself", "main_gate", "KO", [1, 2, 13]),
        ("Search for a side entrance -- stay unnoticed", "side_entry", "UM", [9, 10]),
        ("Scan the building with dimensional sight", "scan_build", "CA", [7, 8]),
        ("Ask Polly about the Academy's history", "ask_polly", "AV", [3, 4]),
        ("Study the inscriptions on the entrance pillars", "inscriptions", "DR", [11, 12]),
        ("Wait and observe who comes and goes", "observe", "RU", [5, 6, 14]),
    ],
    "first_lesson": [
        ("Focus on Kor'aelin -- master authority first", "learn_ko", "KO", [1, 2]),
        ("Focus on Avali -- master transport first", "learn_av", "AV", [3, 4]),
        ("Focus on Runethic -- master policy first", "learn_ru", "RU", [5, 6]),
        ("Focus on Cassisivadan -- master compute first", "learn_ca", "CA", [7, 8]),
        ("Focus on Umbroth -- master security first", "learn_um", "UM", [9, 10]),
        ("Focus on Draumric -- master schema first", "learn_dr", "DR", [11, 12]),
        ("Try to learn all six at once", "learn_all_six", "CA", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]),
    ],
}

# Dialogue lines for each scene
SCENE_DIALOGUES: Dict[str, List[Tuple[str, str]]] = {
    # (speaker, line) -- empty speaker means narration
    "earth_morning": [
        ("", "Day 1. Your alarm goes off at 6:47 AM."),
        ("", "The apartment is small but functional. Terminal glowing in the corner."),
        ("", "You check your phone. Three missed messages from the research team."),
        ("", "The routing logs from last night are still scrolling on your screen."),
        ("", "Something in the data caught your eye before you fell asleep..."),
        ("", "Another day at the Systems Architecture division."),
    ],
    "earth_work": [
        ("", "The lab hums with server racks and the soft glow of monitors."),
        ("", "You're debugging an authentication anomaly in the routing logs."),
        ("", "Something feels off. The patterns don't match any known protocol."),
        ("COLLEAGUE", "Hey, the routing logs are doing that thing again."),
        ("COLLEAGUE", "Almost looks... dimensional. Ha. Wouldn't that be something."),
        ("", "But the routing patterns... they look like they are folding into themselves."),
        ("", "Like origami made of pure information."),
    ],
    "earth_evening": [
        ("", "Home. The apartment feels different tonight."),
        ("", "Your research notes are scattered across the desk."),
        ("", "The air smells faintly of ozone and old parchment."),
        ("", "A book on the shelf catches your eye:"),
        ("", "'An Introduction to Dimensional Magic: Storage Spaces'"),
        ("", "Wait -- that was not there before."),
        ("", "The spine glows faintly in the dark."),
    ],
    "earth_night": [
        ("", "The book is warm to the touch."),
        ("", "Pages filled with six languages you have never seen."),
        ("", "Six tongues of power: KO... AV... RU... CA... UM... DR..."),
        ("", "The words blur. The room darkens."),
        ("", "Symbols begin to orbit your vision like satellites."),
        ("VOICE", "What do you intend?"),
        ("", "Your eyes close. The spiral turns."),
    ],
    "transit": [
        ("", "..."),
        ("", "Reality collapses."),
        ("", "You feel yourself falling through protocol space."),
        ("", "Fourteen layers of governance cascade around you."),
        ("", "Intent... Routing... Context... Memory..."),
        ("", "Constraints... Policy... Compute... Encrypt..."),
        ("", "Spectral... Quantum... Schema... Auth..."),
        ("", "Governance... Integration."),
        ("", "Location is authorization-dependent here."),
        ("", "Existence is continuously verified."),
        ("", "..."),
        ("", "You wake on a floating island, bathed in purple light."),
        ("", "A raven perches on a crystalline branch, watching you."),
    ],
    "aethermoor_arrival": [
        ("POLLY", "CAW! Finally. You were expected by the Protocol."),
        ("POLLY", "I am Polly, Fifth Circle Keeper of the Archives."),
        ("POLLY", "And you, Izack, are late."),
        ("", "A sand golem shuffles toward you, eyes glowing warm gold."),
        ("CLAY", "*happy grinding noises*"),
        ("POLLY", "That is Clay. He is... enthusiastic."),
        ("POLLY", "Listen well. Survival here requires learning the"),
        ("POLLY", "Six Sacred Tongues. Magic here is protocol architecture,"),
        ("POLLY", "not folklore spellcraft."),
        ("POLLY", "Each tongue maps to layers of governance. Master them,"),
        ("POLLY", "and you can shape reality itself."),
        ("POLLY", "Let us begin."),
    ],
    "academy_entrance": [
        ("", "Avalon Academy rises from the floating island like a cathedral"),
        ("", "of crystal and ancient stone. Six towers, one for each tongue."),
        ("POLLY", "Avalon Academy. Where the Protocol is taught and tested."),
        ("POLLY", "Each tower focuses on one of the Sacred Tongues."),
        ("POLLY", "The red tower: Kor'aelin -- Authority."),
        ("POLLY", "Cyan: Avali -- Transport. Gold: Runethic -- Policy."),
        ("POLLY", "Green: Cassisivadan -- Compute. Purple: Umbroth -- Security."),
        ("POLLY", "Orange: Draumric -- Schema and Authentication."),
        ("CLAY", "*stares at the towers in awe*"),
        ("POLLY", "Choose your approach."),
    ],
    "first_lesson": [
        ("", "Inside the Academy, the air thrums with layered magic."),
        ("", "You can feel the fourteen governance layers pulsing around you."),
        ("POLLY", "Your first lesson. Each tongue governs specific layers."),
        ("POLLY", "Kor'aelin: Intent and Routing. The command tongue."),
        ("POLLY", "Avali: Context and Memory. The transport tongue."),
        ("POLLY", "Runethic: Constraints and Policy. The law tongue."),
        ("POLLY", "Cassisivadan: Compute and Encrypt. The cipher tongue."),
        ("POLLY", "Umbroth: Spectral and Quantum. The shadow tongue."),
        ("POLLY", "Draumric: Schema and Auth. The forge tongue."),
        ("POLLY", "Governance and Integration respond to all tongues combined."),
        ("POLLY", "Which tongue calls to you?"),
    ],
}

# Companion thoughts triggered by scene
COMPANION_THOUGHTS: Dict[str, List[Tuple[str, str]]] = {
    "earth_morning": [
        ("SYSTEM", "Intent Layer processing player awakening context..."),
        ("SYSTEM", "Routing Layer: Earth-side narrative branch active."),
    ],
    "earth_work": [
        ("SYSTEM", "Context Layer: Research lab environment loaded."),
        ("SYSTEM", "Anomaly detected in governance fabric -- flagging Spectral Layer."),
    ],
    "earth_evening": [
        ("SYSTEM", "Memory Layer: Dimensional artifact detected in environment."),
        ("SYSTEM", "Schema Layer: Book contents defy known classification."),
    ],
    "earth_night": [
        ("SYSTEM", "All 14 layers activating for transit sequence..."),
        ("SYSTEM", "Governance Layer: Intent verification required."),
    ],
    "transit": [
        ("SYSTEM", "FULL CASCADE: Layers 1-14 cycling."),
        ("SYSTEM", "Integration Layer: Cross-dimensional transfer in progress."),
        ("SYSTEM", "Auth Layer: Identity re-verified in target dimension."),
    ],
    "aethermoor_arrival": [
        ("POLLY", "He looks confused. Good. Confusion is the first teacher."),
        ("CLAY", "*thinking about naps and magic rocks*"),
        ("POLLY", "The Protocol chose him. The Protocol does not make mistakes."),
    ],
    "academy_entrance": [
        ("POLLY", "I wonder which tower he will gravitate toward..."),
        ("CLAY", "*wants to go to the Runethic tower because it is warm*"),
        ("POLLY", "The Academy has not had a new student in decades."),
    ],
    "first_lesson": [
        ("POLLY", "Most scholars start with their affinity tongue."),
        ("POLLY", "But the truly gifted try to bridge them all."),
        ("CLAY", "*already asleep on a desk*"),
    ],
}

# Scene flow order
SCENE_ORDER: List[str] = [
    "title",
    "earth_morning",
    "earth_work",
    "earth_evening",
    "earth_night",
    "transit",
    "aethermoor_arrival",
    "academy_entrance",
    "first_lesson",
]


# ---------------------------------------------------------------------------
# Scene Manager
# ---------------------------------------------------------------------------
class SceneManager:
    """Manages scene flow, dialogue, and choices."""

    def __init__(self) -> None:
        self.current_scene_id: str = "title"
        self.scene_index: int = 0
        self.dialogue_lines: List[Tuple[str, str]] = []  # (speaker, line)
        self.dialogue_index: int = 0
        self.choices: List[Tuple[str, str, str, List[int]]] = []
        self.selected_choice: int = 0
        self.active_layers: Set[int] = set()
        self.companion_thoughts: List[Tuple[str, str]] = []
        self.showing_choices: bool = False
        self.scene_finished: bool = False
        self.transition_timer: float = 0.0
        self.layer_pulse_timers: Dict[int, float] = {}

    def load_scene(self, scene_id: str) -> None:
        """Load a scene by ID."""
        self.current_scene_id = scene_id
        self.dialogue_lines = list(SCENE_DIALOGUES.get(scene_id, []))
        self.dialogue_index = 0
        self.choices = list(SCENE_CHOICES.get(scene_id, []))
        self.selected_choice = 0
        self.showing_choices = False
        self.scene_finished = False
        self.active_layers = set()
        self.companion_thoughts = list(COMPANION_THOUGHTS.get(scene_id, []))
        self.layer_pulse_timers = {}

    def advance_dialogue(self) -> bool:
        """Advance to the next dialogue line. Returns True if there is more."""
        if self.dialogue_index < len(self.dialogue_lines) - 1:
            self.dialogue_index += 1
            return True
        else:
            # All dialogue exhausted -- show choices
            if self.choices and not self.showing_choices:
                self.showing_choices = True
                return True
            self.scene_finished = True
            return False

    def select_choice(self, idx: int) -> Optional[str]:
        """Select a choice. Returns the action key."""
        if 0 <= idx < len(self.choices):
            label, action, tongue, layers = self.choices[idx]
            self.active_layers = set(layers)
            # Pulse the layers
            now = time.time()
            for layer_num in layers:
                self.layer_pulse_timers[layer_num] = now
            return action
        return None

    def get_current_line(self) -> Optional[Tuple[str, str]]:
        """Get the current dialogue line as (speaker, text)."""
        if 0 <= self.dialogue_index < len(self.dialogue_lines):
            return self.dialogue_lines[self.dialogue_index]
        return None

    def next_scene(self) -> Optional[str]:
        """Get the next scene ID in the flow."""
        try:
            cur = SCENE_ORDER.index(self.current_scene_id)
            if cur + 1 < len(SCENE_ORDER):
                return SCENE_ORDER[cur + 1]
        except ValueError:
            pass
        return None

    def get_bg_mood(self) -> str:
        """Return the background mood key for the current scene."""
        sid = self.current_scene_id
        if sid == "title":
            return "title"
        elif sid.startswith("earth"):
            return "earth"
        elif sid == "transit":
            return "transit"
        elif sid.startswith("battle"):
            return "battle"
        elif sid in ("academy_entrance", "first_lesson"):
            return "academy"
        else:
            return "aethermoor"


# ---------------------------------------------------------------------------
# Battle Manager
# ---------------------------------------------------------------------------
class BattleManager:
    """Turn-based battle system (Pokemon/Digimon style)."""

    def __init__(self) -> None:
        self.active: bool = False
        self.party: List[Character] = []
        self.enemies: List[Character] = []
        self.turn_index: int = 0
        self.is_player_turn: bool = True
        self.battle_log: List[str] = []
        self.selected_action: int = 0
        self.selecting_target: bool = False
        self.selected_target: int = 0
        self.animation_timer: float = 0.0
        self.shake_offset: Tuple[int, int] = (0, 0)
        self.victory: bool = False
        self.defeat: bool = False
        self.flash_timer: float = 0.0

    def start_battle(self, party: List[Character], enemies: List[Character]) -> None:
        """Initialize a battle."""
        self.active = True
        self.party = party
        self.enemies = enemies
        self.turn_index = 0
        self.is_player_turn = True
        self.battle_log = ["A wild encounter begins!"]
        self.selected_action = 0
        self.selecting_target = False
        self.selected_target = 0
        self.victory = False
        self.defeat = False

    def get_actions(self) -> List[str]:
        """Get available actions for the current party member."""
        if not self.is_player_turn or self.turn_index >= len(self.party):
            return []
        char = self.party[self.turn_index]
        actions = ["Attack"]
        for spell in char.spells:
            if char.stats.mp >= spell.mp_cost:
                actions.append(spell.name)
        actions.append("Defend")
        return actions

    def execute_player_action(self, action_idx: int, target_idx: int) -> None:
        """Execute a player action."""
        if self.turn_index >= len(self.party):
            return
        char = self.party[self.turn_index]
        target = self.enemies[target_idx] if target_idx < len(self.enemies) else None
        if target is None or target.stats.hp <= 0:
            return

        if action_idx == 0:
            # Basic attack
            dmg, msg, crit = calculate_damage(char, target)
            target.stats.hp = max(0, target.stats.hp - dmg)
            self.battle_log.append(msg)
            if crit:
                self.flash_timer = time.time()
        elif action_idx <= len(char.spells):
            spell = char.spells[action_idx - 1]
            if char.stats.mp >= spell.mp_cost:
                char.stats.mp -= spell.mp_cost
                dmg, msg, crit = calculate_damage(char, target, spell)
                target.stats.hp = max(0, target.stats.hp - dmg)
                self.battle_log.append(msg)
                if crit:
                    self.flash_timer = time.time()
        else:
            # Defend
            self.battle_log.append(f"{char.name} defends!")

        self._check_battle_end()
        self._advance_turn()

    def execute_enemy_turn(self) -> None:
        """Execute enemy AI turn."""
        alive_enemies = [e for e in self.enemies if e.stats.hp > 0]
        if not alive_enemies:
            return

        for enemy in alive_enemies:
            alive_party = [p for p in self.party if p.stats.hp > 0]
            if not alive_party:
                break
            target = random.choice(alive_party)

            # Enemies randomly use spells or basic attacks
            if enemy.spells and random.random() < 0.6:
                usable = [s for s in enemy.spells if enemy.stats.mp >= s.mp_cost]
                if usable:
                    spell = random.choice(usable)
                    enemy.stats.mp -= spell.mp_cost
                    dmg, msg, crit = calculate_damage(enemy, target, spell)
                    target.stats.hp = max(0, target.stats.hp - dmg)
                    self.battle_log.append(msg)
                    self.shake_offset = (random.randint(-3, 3), random.randint(-2, 2))
                    continue

            dmg, msg, crit = calculate_damage(enemy, target)
            target.stats.hp = max(0, target.stats.hp - dmg)
            self.battle_log.append(msg)
            self.shake_offset = (random.randint(-3, 3), random.randint(-2, 2))

        self._check_battle_end()
        self.is_player_turn = True
        self.turn_index = 0
        self.selected_action = 0

    def _advance_turn(self) -> None:
        """Move to next party member or enemy turn."""
        self.turn_index += 1
        if self.turn_index >= len(self.party):
            self.is_player_turn = False

    def _check_battle_end(self) -> None:
        """Check for victory or defeat."""
        if all(e.stats.hp <= 0 for e in self.enemies):
            self.victory = True
            self.battle_log.append("Victory! All enemies defeated!")
        elif all(p.stats.hp <= 0 for p in self.party):
            self.defeat = True
            self.battle_log.append("Defeat... The party has fallen.")

    def end_battle(self) -> None:
        """Clean up battle state."""
        self.active = False
        self.shake_offset = (0, 0)


# ---------------------------------------------------------------------------
# Particle System (for visual effects)
# ---------------------------------------------------------------------------
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "color", "life", "max_life", "size")

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: Tuple[int, int, int], life: float, size: int = 2):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size


class ParticleSystem:
    """Simple particle effects for tongue magic and transitions."""

    def __init__(self) -> None:
        self.particles: List[Particle] = []

    def emit(self, x: float, y: float, color: Tuple[int, int, int],
             count: int = 10, spread: float = 2.0, life: float = 1.0) -> None:
        """Emit particles at a position."""
        for _ in range(count):
            vx = random.uniform(-spread, spread)
            vy = random.uniform(-spread, spread)
            size = random.randint(1, 3)
            self.particles.append(Particle(x, y, vx, vy, color, life, size))

    def update(self, dt: float) -> None:
        """Update all particles."""
        alive: List[Particle] = []
        for p in self.particles:
            p.x += p.vx * dt * 60
            p.y += p.vy * dt * 60
            p.vy += 0.5 * dt * 60  # gravity
            p.life -= dt
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def draw(self, surface: pygame.Surface, offset_x: int = 0, offset_y: int = 0) -> None:
        """Draw all particles."""
        for p in self.particles:
            alpha = max(0, min(255, int(255 * (p.life / p.max_life))))
            r, g, b = p.color
            color = (r, g, b)
            px = int(p.x) + offset_x
            py = int(p.y) + offset_y
            if p.size <= 1:
                try:
                    surface.set_at((px, py), color)
                except IndexError:
                    pass
            else:
                pygame.draw.circle(surface, color, (px, py), p.size)


# ---------------------------------------------------------------------------
# Sprite Cache
# ---------------------------------------------------------------------------
class SpriteCache:
    """Cache character sprites as pygame surfaces."""

    def __init__(self) -> None:
        self._cache: Dict[str, pygame.Surface] = {}

    def get(self, character: Character, size: int = 32) -> pygame.Surface:
        """Get or create a cached sprite surface."""
        key = f"{character.name}_{size}"
        if key not in self._cache:
            arr = generate_sprite(character, size=size)
            # arr is (size, size, 4) RGBA; pygame needs (w, h, 3) with RGB
            rgb = arr[:, :, :3]
            alpha_mask = arr[:, :, 3]
            # Transpose from (row, col, ch) to (col, row, ch) for pygame
            rgb_t = np.transpose(rgb, (1, 0, 2)).copy()
            surface = pygame.surfarray.make_surface(rgb_t)
            # Build alpha from the original array
            alpha_t = np.transpose(alpha_mask, (1, 0)).copy()
            # Create per-pixel alpha surface
            final = surface.convert_alpha()
            # Set transparent pixels to colorkey approach: use black as transparent
            final.set_colorkey((0, 0, 0))
            self._cache[key] = final
        return self._cache[key]

    def get_scaled(self, character: Character, target_size: int = 64) -> pygame.Surface:
        """Get a sprite scaled to target size."""
        key = f"{character.name}_scaled_{target_size}"
        if key not in self._cache:
            base = self.get(character, size=32)
            scaled = pygame.transform.scale(base, (target_size, target_size))
            self._cache[key] = scaled
        return self._cache[key]


# ---------------------------------------------------------------------------
# Font Manager
# ---------------------------------------------------------------------------
class FontManager:
    """Manages fonts with fallbacks."""

    def __init__(self) -> None:
        self._fonts: Dict[str, pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False) -> pygame.font.Font:
        """Get a monospace font at the given size."""
        key = f"{size}_{bold}"
        if key not in self._fonts:
            font = None
            for name in ("consolas", "Consolas", "Courier New", "monospace",
                         "Lucida Console", "DejaVu Sans Mono"):
                try:
                    font = pygame.font.SysFont(name, size, bold=bold)
                    break
                except Exception:
                    continue
            if font is None:
                font = pygame.font.SysFont(None, size, bold=bold)
            self._fonts[key] = font
        return self._fonts[key]


# ---------------------------------------------------------------------------
# Drawing Helpers
# ---------------------------------------------------------------------------

def draw_rounded_rect(surface: pygame.Surface, color: Tuple[int, ...],
                      rect: pygame.Rect, radius: int = 10,
                      border: int = 0, border_color: Tuple[int, ...] = (0, 0, 0)) -> None:
    """Draw a filled rounded rectangle."""
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border > 0:
        pygame.draw.rect(surface, border_color, rect, width=border, border_radius=radius)


def draw_bar(surface: pygame.Surface, x: int, y: int, w: int, h: int,
             ratio: float, color: Tuple[int, int, int],
             bg_color: Tuple[int, int, int] = (40, 40, 50)) -> None:
    """Draw a progress bar."""
    ratio = max(0.0, min(1.0, ratio))
    pygame.draw.rect(surface, bg_color, (x, y, w, h))
    if ratio > 0:
        pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
    pygame.draw.rect(surface, (80, 80, 100), (x, y, w, h), 1)


def draw_text_wrapped(surface: pygame.Surface, text: str, font: pygame.font.Font,
                      color: Tuple[int, int, int], rect: pygame.Rect,
                      line_spacing: int = 2) -> int:
    """Draw wrapped text in a rectangle. Returns the y position after last line."""
    words = text.split(" ")
    lines: List[str] = []
    current = ""
    for word in words:
        test = current + (" " if current else "") + word
        tw, _ = font.size(test)
        if tw > rect.width - 8:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    y = rect.y
    for line in lines:
        if y + font.get_height() > rect.y + rect.height:
            break
        rendered = font.render(line, True, color)
        surface.blit(rendered, (rect.x + 4, y))
        y += font.get_height() + line_spacing
    return y


def lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    """Linearly interpolate between two colors."""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


# ---------------------------------------------------------------------------
# Main Game Class
# ---------------------------------------------------------------------------
class AethermoorGame:
    """Main game class -- single-file Pygame-CE pilot demo."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)

        self.screen = pygame.display.set_mode(
            (WINDOW_W, WINDOW_H), pygame.SCALED | pygame.RESIZABLE
        )
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False

        # Managers
        self.fonts = FontManager()
        self.sprites = SpriteCache()
        self.scene = SceneManager()
        self.battle = BattleManager()
        self.particles = ParticleSystem()
        self.exporter = TrainingExporter()

        # Game state
        self.cast = create_cast()
        self.party: List[Character] = [self.cast["izack"]]
        self.game_phase = "title"
        self.show_dashboard_detail = True
        self.frame_count = 0
        self.start_time = time.time()

        # Training data counters
        self.sft_count = 0
        self.dpo_count = 0

        # Visual state
        self.title_alpha = 0.0
        self.title_fade_in = True
        self.text_cursor_visible = True
        self.cursor_timer = 0.0
        self.screen_shake: Tuple[int, int] = (0, 0)
        self.transition_progress = 0.0
        self.transitioning = False
        self.bg_stars: List[Tuple[int, int, int]] = []
        self._generate_stars()

        # Game screen surface (rendered separately)
        self.game_surface = pygame.Surface((GAME_W, GAME_H))

        # Layer activity animation
        self.layer_activity: Dict[int, float] = {i: 0.0 for i in range(1, 15)}

    def _generate_stars(self) -> None:
        """Generate background star positions."""
        self.bg_stars = []
        for _ in range(80):
            x = random.randint(0, GAME_W)
            y = random.randint(0, GAME_H)
            brightness = random.randint(80, 255)
            self.bg_stars.append((x, y, brightness))

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS_CAP) / 1000.0
            dt = min(dt, 0.05)  # Cap delta to avoid spiral of death

            self._handle_events()
            self._update(dt)
            self._draw()

            pygame.display.flip()
            self.frame_count += 1

        pygame.quit()

    # ------------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------------
    def _handle_events(self) -> None:
        """Process all pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._save_and_quit()
                return

            if event.type == pygame.KEYDOWN:
                self._handle_key(event.key)

    def _handle_key(self, key: int) -> None:
        """Handle a key press."""
        # Global controls
        if key == pygame.K_ESCAPE:
            if self.paused:
                self.paused = False
            elif self.game_phase == "title":
                self._save_and_quit()
            else:
                self.paused = True
            return

        if self.paused:
            self._handle_pause_key(key)
            return

        if key == pygame.K_TAB:
            self.show_dashboard_detail = not self.show_dashboard_detail
            return

        # Phase-specific handling
        if self.game_phase == "title":
            self._handle_title_key(key)
        elif self.battle.active:
            self._handle_battle_key(key)
        else:
            self._handle_scene_key(key)

    def _handle_title_key(self, key: int) -> None:
        """Handle keys on the title screen."""
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            self.game_phase = "scene"
            self.scene.load_scene("earth_morning")
            self.particles.emit(GAME_W // 2, GAME_H // 2, GOLD, count=30, spread=4.0)

    def _handle_scene_key(self, key: int) -> None:
        """Handle keys during scene playback."""
        # B key to toggle battle for testing
        if key == pygame.K_b:
            self._start_test_battle()
            return

        if self.transitioning:
            return

        if self.scene.showing_choices:
            self._handle_choice_key(key)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if not self.scene.advance_dialogue():
                if self.scene.scene_finished:
                    self._advance_to_next_scene()

    def _handle_choice_key(self, key: int) -> None:
        """Handle keys when choices are displayed."""
        num_choices = len(self.scene.choices)
        if num_choices == 0:
            return

        # Arrow / WASD navigation
        if key in (pygame.K_UP, pygame.K_w):
            self.scene.selected_choice = (self.scene.selected_choice - 1) % num_choices
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.scene.selected_choice = (self.scene.selected_choice + 1) % num_choices
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._execute_choice(self.scene.selected_choice)
        # Number keys for quick select (1-7)
        elif pygame.K_1 <= key <= pygame.K_7:
            idx = key - pygame.K_1
            if idx < num_choices:
                self.scene.selected_choice = idx
                self._execute_choice(idx)

    def _handle_battle_key(self, key: int) -> None:
        """Handle keys during battle."""
        if self.battle.victory or self.battle.defeat:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.battle.end_battle()
                # Heal party slightly after battle
                for c in self.party:
                    c.stats.hp = min(c.stats.max_hp, c.stats.hp + c.stats.max_hp // 4)
                    c.stats.mp = min(c.stats.max_mp, c.stats.mp + c.stats.max_mp // 4)
            return

        if not self.battle.is_player_turn:
            return

        actions = self.battle.get_actions()
        if not actions:
            return

        if self.battle.selecting_target:
            alive = [i for i, e in enumerate(self.battle.enemies) if e.stats.hp > 0]
            if key in (pygame.K_UP, pygame.K_w):
                cur = alive.index(self.battle.selected_target) if self.battle.selected_target in alive else 0
                cur = (cur - 1) % len(alive)
                self.battle.selected_target = alive[cur]
            elif key in (pygame.K_DOWN, pygame.K_s):
                cur = alive.index(self.battle.selected_target) if self.battle.selected_target in alive else 0
                cur = (cur + 1) % len(alive)
                self.battle.selected_target = alive[cur]
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.battle.execute_player_action(
                    self.battle.selected_action, self.battle.selected_target
                )
                self.battle.selecting_target = False
                # Emit particles
                tc = TONGUE_COLORS.get(
                    self.party[min(self.battle.turn_index, len(self.party) - 1)].tongue_affinity.value, (200, 200, 200)
                )
                self.particles.emit(400, 200, tc, count=15, spread=3.0)
            elif key == pygame.K_ESCAPE:
                self.battle.selecting_target = False
        else:
            if key in (pygame.K_UP, pygame.K_w):
                self.battle.selected_action = (self.battle.selected_action - 1) % len(actions)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.battle.selected_action = (self.battle.selected_action + 1) % len(actions)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                # Select target
                alive = [i for i, e in enumerate(self.battle.enemies) if e.stats.hp > 0]
                if alive:
                    self.battle.selecting_target = True
                    self.battle.selected_target = alive[0]

    def _handle_pause_key(self, key: int) -> None:
        """Handle keys in the pause menu."""
        if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            self.paused = False
        elif key == pygame.K_q:
            self._save_and_quit()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _execute_choice(self, idx: int) -> None:
        """Execute a player choice and generate training data."""
        if idx >= len(self.scene.choices):
            return
        label, action, tongue, layers = self.scene.choices[idx]

        # Activate layers
        self.scene.active_layers = set(layers)
        now = time.time()
        for layer_num in layers:
            self.scene.layer_pulse_timers[layer_num] = now
            self.layer_activity[layer_num] = 1.0

        # Emit tongue-colored particles
        tc = TONGUE_COLORS.get(tongue, (200, 200, 200))
        self.particles.emit(GAME_W // 2, GAME_H // 2 - 40, tc, count=20, spread=3.5)

        # Record training data
        all_labels = [c[0] for c in self.scene.choices]
        self.exporter.record_choice(
            context=f"Scene: {self.scene.current_scene_id}. "
                    f"Dialogue context: {self.scene.get_current_line()}",
            choice_made=label,
            alternatives=[l for l in all_labels if l != label],
            outcome=f"Player chose {action} (Tongue: {tongue}, Layers: {layers})",
            category=f"scene_{self.scene.current_scene_id}",
        )
        self.sft_count += 1

        # Record DPO pair (chosen vs worst alternative)
        if len(self.scene.choices) > 1:
            worst_idx = (idx + len(self.scene.choices) // 2) % len(self.scene.choices)
            self.dpo_count += 1

        # Boost tongue proficiency for the protagonist
        if self.party:
            prof = self.party[0].stats.tongue_prof
            current = prof.get(tongue, 0.0)
            prof[tongue] = min(1.0, current + 0.02)

        # Advance to next scene
        self._advance_to_next_scene()

    def _advance_to_next_scene(self) -> None:
        """Transition to the next scene."""
        next_id = self.scene.next_scene()
        if next_id:
            self.transitioning = True
            self.transition_progress = 0.0
            self._pending_scene = next_id

            # Add party members at specific scenes
            if next_id == "aethermoor_arrival":
                polly = self.cast["polly"]
                clay = self.cast["clay"]
                if not any(c.name == "Polly" for c in self.party):
                    self.party.append(polly)
                if not any(c.name == "Clay" for c in self.party):
                    self.party.append(clay)
            elif next_id == "academy_entrance":
                eldrin = self.cast["eldrin"]
                if not any(c.name == "Eldrin" for c in self.party):
                    self.party.append(eldrin)
            elif next_id == "first_lesson":
                aria = self.cast["aria"]
                if not any(c.name == "Aria Ravencrest" for c in self.party):
                    self.party.append(aria)
        else:
            # Loop back or end: restart from first_lesson for demo purposes
            self.transitioning = True
            self.transition_progress = 0.0
            self._pending_scene = "first_lesson"

    def _start_test_battle(self) -> None:
        """Start a test battle encounter."""
        # Create wild enemies
        enemy1 = Character(
            name="Shadow Wisp",
            title="Wild Creature",
            tongue_affinity=Tongue.UM,
            evo_stage=EvoStage.ROOKIE,
            stats=Stats(hp=60, max_hp=60, mp=30, max_mp=30,
                       attack=8, defense=6, speed=12, wisdom=8),
            spells=[
                Spell("Shadow Bolt", Tongue.UM, 12, 6, "A bolt of shadow energy"),
            ],
            is_enemy=True,
        )
        enemy2 = Character(
            name="Rune Beetle",
            title="Wild Creature",
            tongue_affinity=Tongue.DR,
            evo_stage=EvoStage.FRESH,
            stats=Stats(hp=40, max_hp=40, mp=20, max_mp=20,
                       attack=10, defense=8, speed=6, wisdom=4),
            spells=[
                Spell("Shell Crack", Tongue.DR, 15, 8, "Crack open defenses"),
            ],
            is_enemy=True,
        )
        # Need local import for Stats since it's used above
        self.battle.start_battle(
            party=[c for c in self.party if c.stats.hp > 0],
            enemies=[enemy1, enemy2],
        )
        self.particles.emit(GAME_W // 2, GAME_H // 2, (255, 60, 60), count=25, spread=5.0)

    def _save_and_quit(self) -> None:
        """Save training data and quit."""
        if self.exporter.total_pairs > 0:
            try:
                path = self.exporter.save()
            except Exception:
                pass
        self.running = False

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def _update(self, dt: float) -> None:
        """Update game state."""
        if self.paused:
            return

        # Cursor blink
        self.cursor_timer += dt
        if self.cursor_timer > 0.5:
            self.cursor_timer = 0.0
            self.text_cursor_visible = not self.text_cursor_visible

        # Title fade
        if self.game_phase == "title":
            if self.title_fade_in:
                self.title_alpha = min(1.0, self.title_alpha + dt * 0.8)

        # Particles
        self.particles.update(dt)

        # Transition
        if self.transitioning:
            self.transition_progress += dt * 2.0
            if self.transition_progress >= 1.0:
                self.transitioning = False
                self.transition_progress = 0.0
                self.scene.load_scene(self._pending_scene)

        # Layer activity decay
        for layer_num in self.layer_activity:
            if layer_num in self.scene.active_layers:
                self.layer_activity[layer_num] = min(1.0, self.layer_activity[layer_num] + dt * 3)
            else:
                self.layer_activity[layer_num] = max(0.0, self.layer_activity[layer_num] - dt * 0.5)

        # Screen shake decay
        sx, sy = self.screen_shake
        self.screen_shake = (int(sx * 0.8), int(sy * 0.8))

        # Battle shake decay
        if self.battle.active:
            bx, by = self.battle.shake_offset
            self.battle.shake_offset = (int(bx * 0.85), int(by * 0.85))

        # Enemy AI turn
        if self.battle.active and not self.battle.is_player_turn:
            if not self.battle.victory and not self.battle.defeat:
                self.battle.execute_enemy_turn()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        """Draw everything."""
        self.screen.fill((12, 12, 18))

        # Draw bezel
        self._draw_bezel()

        # Draw game screen
        self.game_surface.fill(BG_COLORS.get(self.scene.get_bg_mood(), BG_COLORS["earth"]))

        if self.game_phase == "title":
            self._draw_title_screen()
        elif self.battle.active:
            self._draw_battle_screen()
        else:
            self._draw_scene_screen()

        # Draw particles on game surface
        self.particles.draw(self.game_surface)

        # Transition overlay
        if self.transitioning:
            self._draw_transition()

        # Blit game surface into bezel
        shake_x, shake_y = self.screen_shake
        if self.battle.active:
            bx, by = self.battle.shake_offset
            shake_x += bx
            shake_y += by
        self.screen.blit(self.game_surface, (20 + shake_x, 50 + shake_y))

        # Draw dashboard
        self._draw_dashboard()

        # Pause overlay
        if self.paused:
            self._draw_pause()

    # ------------------------------------------------------------------
    # Bezel (console frame)
    # ------------------------------------------------------------------
    def _draw_bezel(self) -> None:
        """Draw the GameBoy-style console bezel."""
        # Outer bezel
        bezel_rect = pygame.Rect(6, 6, 668, 708)
        draw_rounded_rect(self.screen, BEZEL_COLOR, bezel_rect, radius=18)
        draw_rounded_rect(self.screen, BEZEL_HIGHLIGHT, bezel_rect, radius=18,
                          border=2, border_color=BEZEL_HIGHLIGHT)

        # Inner screen border
        screen_border = pygame.Rect(16, 46, 648, 488)
        pygame.draw.rect(self.screen, (10, 10, 16), screen_border, border_radius=4)
        pygame.draw.rect(self.screen, (60, 60, 80), screen_border, width=1, border_radius=4)

        # "AETHERMOOR" title text on bezel
        title_font = self.fonts.get(16, bold=True)
        title_surf = title_font.render("AETHERMOOR", True, GOLD)
        title_x = 20 + (GAME_W - title_surf.get_width()) // 2
        self.screen.blit(title_surf, (title_x, 20))

        # Version badge
        ver_font = self.fonts.get(10)
        ver_surf = ver_font.render("SCBE v3.0", True, DIM_TEXT)
        self.screen.blit(ver_surf, (20, 24))

        # LED indicators (6 tongue dots below screen)
        led_y = 544
        led_start_x = 20 + (GAME_W - 6 * 28) // 2
        led_font = self.fonts.get(9)
        tongue_codes = ["KO", "AV", "RU", "CA", "UM", "DR"]
        for i, code in enumerate(tongue_codes):
            cx = led_start_x + i * 28 + 6
            color = TONGUE_COLORS[code]
            # Pulse based on activity
            active = any(
                l in self.scene.active_layers
                for l in range(1, 15)
                if self._tongue_for_layer(l) == code
            )
            if active:
                pulse = 0.5 + 0.5 * math.sin(time.time() * 6 + i)
                color = lerp_color((40, 40, 50), color, pulse)
                pygame.draw.circle(self.screen, color, (cx, led_y), 6)
                # Glow
                glow_surf = pygame.Surface((18, 18), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*color, 60), (9, 9), 9)
                self.screen.blit(glow_surf, (cx - 9, led_y - 9))
            else:
                dim = (color[0] // 4, color[1] // 4, color[2] // 4)
                pygame.draw.circle(self.screen, dim, (cx, led_y), 5)
            # Label
            lbl = led_font.render(code, True, DIM_TEXT)
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, led_y + 10))

        # D-pad graphic (decorative)
        dpad_x, dpad_y = 120, 610
        dpad_color = (50, 50, 65)
        dpad_highlight = (70, 70, 90)
        # Horizontal bar
        pygame.draw.rect(self.screen, dpad_color, (dpad_x - 24, dpad_y - 8, 48, 16), border_radius=2)
        # Vertical bar
        pygame.draw.rect(self.screen, dpad_color, (dpad_x - 8, dpad_y - 24, 16, 48), border_radius=2)
        # Center
        pygame.draw.circle(self.screen, dpad_highlight, (dpad_x, dpad_y), 5)
        # Arrow hints
        arrow_font = self.fonts.get(10)
        for dx, dy, char in [(-20, 0, "<"), (20, 0, ">"), (0, -20, "^"), (0, 18, "v")]:
            arr = arrow_font.render(char, True, (100, 100, 120))
            self.screen.blit(arr, (dpad_x + dx - arr.get_width() // 2, dpad_y + dy - arr.get_height() // 2))

        # A/B buttons
        btn_x = 500
        for i, (label, color) in enumerate([("A", (60, 160, 60)), ("B", (160, 60, 60))]):
            bx = btn_x + i * 60
            by = 620
            pygame.draw.circle(self.screen, color, (bx, by), 16)
            pygame.draw.circle(self.screen, (40, 40, 50), (bx, by), 16, 2)
            btn_label = self.fonts.get(14, bold=True).render(label, True, (220, 220, 220))
            self.screen.blit(btn_label, (bx - btn_label.get_width() // 2,
                                         by - btn_label.get_height() // 2))

        # Control hints
        hint_font = self.fonts.get(10)
        hints = ["ENTER: Select", "ESC: Pause", "TAB: Dashboard", "B: Battle"]
        for i, h in enumerate(hints):
            hs = hint_font.render(h, True, (80, 80, 100))
            self.screen.blit(hs, (230, 580 + i * 16))

    def _tongue_for_layer(self, layer_num: int) -> str:
        """Map a layer number to its tongue code."""
        mapping = {
            1: "KO", 2: "KO",
            3: "AV", 4: "AV",
            5: "RU", 6: "RU",
            7: "CA", 8: "CA",
            9: "UM", 10: "UM",
            11: "DR", 12: "DR",
            13: "KO", 14: "CA",  # Governance + Integration are cross-tongue
        }
        return mapping.get(layer_num, "CA")

    # ------------------------------------------------------------------
    # Title Screen
    # ------------------------------------------------------------------
    def _draw_title_screen(self) -> None:
        """Draw the title screen on the game surface."""
        # Starfield background
        for sx, sy, brightness in self.bg_stars:
            b = int(brightness * self.title_alpha)
            twinkle = 0.5 + 0.5 * math.sin(time.time() * 2 + sx * 0.1 + sy * 0.1)
            b = int(b * twinkle)
            if b > 20:
                self.game_surface.set_at((sx % GAME_W, sy % GAME_H), (b, b, min(255, b + 40)))

        # Central spiral effect
        t = time.time()
        cx, cy = GAME_W // 2, GAME_H // 2 - 40
        for i in range(60):
            angle = t * 0.5 + i * 0.3
            r = 20 + i * 2.2
            px = int(cx + math.cos(angle) * r)
            py = int(cy + math.sin(angle) * r)
            tongue_idx = i % 6
            tc_list = list(TONGUE_COLORS.values())
            color = tc_list[tongue_idx]
            alpha_val = max(0, 255 - i * 4)
            if 0 <= px < GAME_W and 0 <= py < GAME_H:
                blended = lerp_color((16, 16, 24), color, alpha_val / 255.0)
                pygame.draw.circle(self.game_surface, blended, (px, py), 2)

        # Title text
        title_font = self.fonts.get(28, bold=True)
        subtitle_font = self.fonts.get(14)
        alpha = int(255 * self.title_alpha)

        title1 = title_font.render("AETHERMOOR", True, GOLD)
        title2 = self.fonts.get(18).render("Six Tongues Protocol", True, TEXT_COLOR)
        subtitle = subtitle_font.render("An SCBE Governance RPG", True, DIM_TEXT)

        self.game_surface.blit(title1, (GAME_W // 2 - title1.get_width() // 2, 160))
        self.game_surface.blit(title2, (GAME_W // 2 - title2.get_width() // 2, 200))
        self.game_surface.blit(subtitle, (GAME_W // 2 - subtitle.get_width() // 2, 230))

        # Tongue names
        tongue_font = self.fonts.get(11)
        codes = ["KO", "AV", "RU", "CA", "UM", "DR"]
        names = ["Kor'aelin", "Avali", "Runethic", "Cassisivadan", "Umbroth", "Draumric"]
        for i, (code, name) in enumerate(zip(codes, names)):
            color = TONGUE_COLORS[code]
            txt = tongue_font.render(f"{code}: {name}", True, color)
            x = GAME_W // 2 - txt.get_width() // 2
            y = 270 + i * 18
            self.game_surface.blit(txt, (x, y))

        # Press Enter prompt
        if self.text_cursor_visible:
            prompt_font = self.fonts.get(14)
            prompt = prompt_font.render("Press ENTER to begin", True, CHOICE_HIGHLIGHT)
            self.game_surface.blit(prompt, (GAME_W // 2 - prompt.get_width() // 2, 420))

        # Copyright
        copy_font = self.fonts.get(10)
        copy_text = copy_font.render("(c) 2026 Issac Davis  |  USPTO #63/961,403", True, (80, 80, 100))
        self.game_surface.blit(copy_text, (GAME_W // 2 - copy_text.get_width() // 2, 460))

    # ------------------------------------------------------------------
    # Scene Screen
    # ------------------------------------------------------------------
    def _draw_scene_screen(self) -> None:
        """Draw the current scene on the game surface."""
        bg_color = BG_COLORS.get(self.scene.get_bg_mood(), BG_COLORS["earth"])
        self.game_surface.fill(bg_color)

        # Background elements based on scene
        self._draw_scene_background()

        # Characters on screen
        self._draw_scene_characters()

        # Location title
        loc_font = self.fonts.get(12)
        scene_name = self.scene.current_scene_id.replace("_", " ").title()
        loc_surf = loc_font.render(scene_name, True, DIM_TEXT)
        self.game_surface.blit(loc_surf, (10, 8))

        # Dialogue box
        if not self.scene.scene_finished:
            self._draw_dialogue_box()

        # Choices overlay
        if self.scene.showing_choices:
            self._draw_choices()

    def _draw_scene_background(self) -> None:
        """Draw scene-specific background elements."""
        sid = self.scene.current_scene_id
        t = time.time()

        if sid.startswith("earth"):
            # Urban / apartment background
            # Floor line
            pygame.draw.line(self.game_surface, (50, 54, 68), (0, 340), (GAME_W, 340), 1)
            # Window
            window_color = (60, 70, 100) if "night" not in sid else (20, 20, 40)
            pygame.draw.rect(self.game_surface, window_color, (440, 60, 150, 120))
            pygame.draw.rect(self.game_surface, (80, 80, 100), (440, 60, 150, 120), 2)
            # Window cross
            pygame.draw.line(self.game_surface, (80, 80, 100), (515, 60), (515, 180), 1)
            pygame.draw.line(self.game_surface, (80, 80, 100), (440, 120), (590, 120), 1)
            # Stars in window (if night/evening)
            if "evening" in sid or "night" in sid:
                for i in range(8):
                    sx = 450 + random.Random(i * 37).randint(0, 130)
                    sy = 70 + random.Random(i * 71).randint(0, 100)
                    twinkle = 0.5 + 0.5 * math.sin(t * 2 + i)
                    b = int(200 * twinkle)
                    self.game_surface.set_at((sx, sy), (b, b, min(255, b + 40)))
            # Terminal screen glow
            if "morning" in sid or "work" in sid:
                term_rect = pygame.Rect(50, 200, 120, 90)
                pygame.draw.rect(self.game_surface, (20, 40, 30), term_rect)
                pygame.draw.rect(self.game_surface, (40, 80, 60), term_rect, 1)
                # Fake text lines
                for line_y in range(6):
                    lw = random.Random(line_y * 13).randint(30, 100)
                    pygame.draw.line(self.game_surface, (40, 120, 60),
                                   (58, 210 + line_y * 12), (58 + lw, 210 + line_y * 12), 1)
            # Desk
            pygame.draw.rect(self.game_surface, (60, 50, 40), (30, 290, 180, 50))
            pygame.draw.rect(self.game_surface, (80, 65, 50), (30, 290, 180, 4))

        elif sid == "transit":
            # Swirling dimensional transit
            cx, cy = GAME_W // 2, GAME_H // 2
            for i in range(120):
                angle = t * 1.5 + i * 0.15
                r = 10 + i * 2.5
                px = int(cx + math.cos(angle) * r)
                py = int(cy + math.sin(angle) * r * 0.6)
                tc_list = list(TONGUE_COLORS.values())
                color = tc_list[i % 6]
                dim = lerp_color(BG_COLORS["transit"], color, max(0, 1.0 - i / 120.0))
                if 0 <= px < GAME_W and 0 <= py < GAME_H:
                    pygame.draw.circle(self.game_surface, dim, (px, py), max(1, 3 - i // 40))

            # Layer labels orbiting
            small_font = self.fonts.get(9)
            for layer_num, layer_name, layer_color in SCBE_LAYERS:
                angle = t * 0.8 + layer_num * (math.pi * 2 / 14)
                r = 100 + layer_num * 8
                px = int(cx + math.cos(angle) * r)
                py = int(cy + math.sin(angle) * r * 0.5)
                if 10 <= px < GAME_W - 40 and 10 <= py < GAME_H - 20:
                    lbl = small_font.render(layer_name, True, layer_color)
                    self.game_surface.blit(lbl, (px, py))

        elif sid in ("aethermoor_arrival", "academy_entrance", "first_lesson"):
            # Floating islands / Aethermoor sky
            # Stars
            for sx, sy, brightness in self.bg_stars:
                twinkle = 0.5 + 0.5 * math.sin(t * 1.5 + sx * 0.05)
                b = int(brightness * 0.4 * twinkle)
                if b > 10:
                    try:
                        self.game_surface.set_at((sx % GAME_W, (sy % (GAME_H - 100))), (b, b, min(255, b + 60)))
                    except IndexError:
                        pass

            # Floating island silhouettes
            for i in range(3):
                ix = 100 + i * 200
                iy = 80 + i * 30 + int(math.sin(t * 0.5 + i) * 5)
                iw = 120 + i * 20
                ih = 30
                island_color = lerp_color((50, 40, 80), (88, 68, 148), 0.5)
                # Draw elliptical island
                pygame.draw.ellipse(self.game_surface, island_color,
                                   (ix - iw // 2, iy, iw, ih))
                # Top detail
                pygame.draw.ellipse(self.game_surface,
                                   lerp_color(island_color, (120, 100, 180), 0.3),
                                   (ix - iw // 2 + 10, iy - 5, iw - 20, 12))

            # Ground platform
            pygame.draw.rect(self.game_surface, (60, 48, 100),
                           (0, 350, GAME_W, GAME_H - 350))
            # Crystal grass
            for gx in range(0, GAME_W, 12):
                gh = random.Random(gx).randint(4, 12)
                gc = lerp_color((60, 80, 140), (100, 120, 180), random.Random(gx * 7).random())
                pygame.draw.line(self.game_surface, gc,
                               (gx, 350), (gx + random.Random(gx * 3).randint(-3, 3), 350 - gh), 1)

            # Academy towers (for academy scenes)
            if sid in ("academy_entrance", "first_lesson"):
                tower_colors = list(TONGUE_COLORS.values())
                for i in range(6):
                    tx = 80 + i * 90
                    tw = 30
                    th = 80 + i * 10
                    ty = 180 - th
                    tc = tower_colors[i]
                    dim_tc = lerp_color((30, 20, 50), tc, 0.4)
                    pygame.draw.rect(self.game_surface, dim_tc, (tx, ty, tw, th))
                    # Tower top
                    pygame.draw.polygon(self.game_surface, tc,
                                       [(tx, ty), (tx + tw, ty), (tx + tw // 2, ty - 15)])
                    # Window glow
                    glow = lerp_color(tc, (255, 255, 255), 0.3 + 0.2 * math.sin(t * 2 + i))
                    pygame.draw.rect(self.game_surface, glow,
                                   (tx + tw // 2 - 3, ty + 10, 6, 8))

    def _draw_scene_characters(self) -> None:
        """Draw character sprites on the scene."""
        if not self.party:
            return

        # Position characters based on scene
        sid = self.scene.current_scene_id
        if sid == "transit":
            # Only show protagonist floating
            char = self.party[0]
            sprite = self.sprites.get_scaled(char, 96)
            bob = int(math.sin(time.time() * 2) * 8)
            self.game_surface.blit(sprite, (GAME_W // 2 - 48, 160 + bob))
            return

        # Show party members
        num = min(len(self.party), 5)
        spacing = min(120, (GAME_W - 100) // max(num, 1))
        start_x = (GAME_W - num * spacing) // 2
        for i in range(num):
            char = self.party[i]
            sprite = self.sprites.get_scaled(char, 64)
            x = start_x + i * spacing
            y = 260
            # Slight bob
            bob = int(math.sin(time.time() * 1.5 + i * 0.8) * 3)
            self.game_surface.blit(sprite, (x, y + bob))

            # Name label
            name_font = self.fonts.get(10)
            name_surf = name_font.render(char.name, True, TEXT_COLOR)
            self.game_surface.blit(name_surf, (x + 32 - name_surf.get_width() // 2, y + 68))

    def _draw_dialogue_box(self) -> None:
        """Draw the dialogue box at the bottom of the game screen."""
        line = self.scene.get_current_line()
        if line is None:
            return

        speaker, text = line

        # Semi-transparent dialogue box
        box_h = 120
        box_y = GAME_H - box_h - 10
        dialogue_surf = pygame.Surface((GAME_W - 20, box_h), pygame.SRCALPHA)
        dialogue_surf.fill(DIALOGUE_BG)
        self.game_surface.blit(dialogue_surf, (10, box_y))

        # Border
        pygame.draw.rect(self.game_surface, (80, 80, 120),
                        (10, box_y, GAME_W - 20, box_h), 1, border_radius=4)

        # Speaker name
        if speaker:
            name_font = self.fonts.get(13, bold=True)
            # Color based on character tongue
            name_color = TEXT_COLOR
            for c in self.party:
                if c.name.upper().startswith(speaker.upper()):
                    name_color = TONGUE_COLORS.get(c.tongue_affinity.value, TEXT_COLOR)
                    break
            if speaker == "POLLY":
                name_color = TONGUE_COLORS["KO"]
            elif speaker == "CLAY":
                name_color = TONGUE_COLORS["RU"]
            elif speaker == "VOICE":
                name_color = GOLD
            elif speaker == "COLLEAGUE":
                name_color = (150, 150, 180)

            name_surf = name_font.render(speaker, True, name_color)
            self.game_surface.blit(name_surf, (20, box_y + 8))
            text_y = box_y + 28
        else:
            text_y = box_y + 12

        # Dialogue text
        text_font = self.fonts.get(13)
        text_rect = pygame.Rect(20, text_y, GAME_W - 44, box_h - (text_y - box_y) - 8)
        draw_text_wrapped(self.game_surface, text, text_font, TEXT_COLOR, text_rect)

        # Advance indicator
        if self.text_cursor_visible:
            indicator = self.fonts.get(12).render(">>", True, CHOICE_HIGHLIGHT)
            self.game_surface.blit(indicator, (GAME_W - 44, box_y + box_h - 20))

    def _draw_choices(self) -> None:
        """Draw the choice menu overlay."""
        choices = self.scene.choices
        if not choices:
            return

        num = len(choices)
        item_h = 32
        padding = 12
        menu_h = num * item_h + padding * 2 + 24
        menu_w = 580
        menu_x = (GAME_W - menu_w) // 2
        menu_y = max(10, (GAME_H - menu_h) // 2 - 20)

        # Background
        menu_surf = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
        menu_surf.fill((12, 12, 24, 240))
        self.game_surface.blit(menu_surf, (menu_x, menu_y))
        pygame.draw.rect(self.game_surface, GOLD,
                        (menu_x, menu_y, menu_w, menu_h), 1, border_radius=6)

        # Header
        header_font = self.fonts.get(13, bold=True)
        header = header_font.render("Choose your action:", True, GOLD)
        self.game_surface.blit(header, (menu_x + padding, menu_y + 8))

        # Choices
        choice_font = self.fonts.get(12)
        layer_font = self.fonts.get(9)
        for i, (label, action, tongue, layers) in enumerate(choices):
            y = menu_y + 28 + i * item_h
            is_selected = (i == self.scene.selected_choice)

            # Highlight bar
            if is_selected:
                highlight_surf = pygame.Surface((menu_w - padding * 2, item_h - 2), pygame.SRCALPHA)
                highlight_surf.fill((255, 220, 80, 40))
                self.game_surface.blit(highlight_surf, (menu_x + padding, y))

            # Number
            num_color = CHOICE_HIGHLIGHT if is_selected else DIM_TEXT
            num_surf = choice_font.render(f"{i + 1}.", True, num_color)
            self.game_surface.blit(num_surf, (menu_x + padding + 4, y + 4))

            # Tongue color indicator (small square)
            tc = TONGUE_COLORS.get(tongue, (180, 180, 180))
            pygame.draw.rect(self.game_surface, tc,
                           (menu_x + padding + 28, y + 7, 12, 12))
            pygame.draw.rect(self.game_surface, (200, 200, 220),
                           (menu_x + padding + 28, y + 7, 12, 12), 1)

            # Label text
            text_color = TEXT_COLOR if is_selected else (180, 180, 200)
            label_surf = choice_font.render(label[:48], True, text_color)
            self.game_surface.blit(label_surf, (menu_x + padding + 46, y + 4))

            # Layer badges (small numbered circles at the right)
            badge_x = menu_x + menu_w - padding - len(layers) * 18 - 4
            for j, layer_num in enumerate(layers[:5]):  # Show max 5 badges
                lcolor = (100, 100, 120)
                for ln, lname, lc in SCBE_LAYERS:
                    if ln == layer_num:
                        lcolor = lc
                        break
                bx = badge_x + j * 18
                pygame.draw.circle(self.game_surface, lcolor, (bx + 7, y + 13), 7)
                lbl = layer_font.render(str(layer_num), True, (20, 20, 30))
                self.game_surface.blit(lbl, (bx + 7 - lbl.get_width() // 2,
                                             y + 13 - lbl.get_height() // 2))

        # Tongue legend at bottom
        legend_y = menu_y + menu_h - 2
        legend_font = self.fonts.get(9)
        sel_tongue = choices[self.scene.selected_choice][2] if choices else ""
        tongue_name = TONGUE_FULL_NAMES.get(sel_tongue, "")
        if tongue_name:
            tc = TONGUE_COLORS.get(sel_tongue, DIM_TEXT)
            legend = legend_font.render(f"Tongue: {sel_tongue} ({tongue_name})", True, tc)
            self.game_surface.blit(legend, (menu_x + padding, legend_y))

    # ------------------------------------------------------------------
    # Battle Screen
    # ------------------------------------------------------------------
    def _draw_battle_screen(self) -> None:
        """Draw the battle screen."""
        self.game_surface.fill(BG_COLORS["battle"])

        # Battle background
        # Dark battlefield gradient
        for y in range(GAME_H):
            ratio = y / GAME_H
            r = int(58 - ratio * 30)
            g = int(28 - ratio * 15)
            b = int(32 - ratio * 16)
            pygame.draw.line(self.game_surface, (max(0, r), max(0, g), max(0, b)),
                           (0, y), (GAME_W, y))

        # Ground line
        pygame.draw.line(self.game_surface, (80, 50, 55), (0, 300), (GAME_W, 300), 2)

        # Draw enemies (top right)
        alive_enemies = [e for e in self.battle.enemies if e.stats.hp > 0]
        for i, enemy in enumerate(self.battle.enemies):
            ex = 380 + i * 120
            ey = 80
            sprite = self.sprites.get_scaled(enemy, 64)
            if enemy.stats.hp > 0:
                self.game_surface.blit(sprite, (ex, ey))
            else:
                # Faded
                faded = sprite.copy()
                faded.set_alpha(80)
                self.game_surface.blit(faded, (ex, ey + 10))
            # Name and HP
            name_font = self.fonts.get(10)
            name_surf = name_font.render(enemy.name, True, TEXT_COLOR)
            self.game_surface.blit(name_surf, (ex, ey - 14))
            # HP bar
            hp_ratio = enemy.stats.hp / enemy.stats.max_hp
            hp_color = Palette.HP_GREEN if hp_ratio > 0.5 else (Palette.HP_YELLOW if hp_ratio > 0.25 else Palette.HP_RED)
            draw_bar(self.game_surface, ex, ey + 68, 60, 6, hp_ratio, hp_color)
            # Target indicator
            if self.battle.selecting_target and i == self.battle.selected_target:
                pygame.draw.rect(self.game_surface, CHOICE_HIGHLIGHT,
                               (ex - 4, ey - 4, 72, 80), 2)
                arrow = self.fonts.get(16).render(">", True, CHOICE_HIGHLIGHT)
                self.game_surface.blit(arrow, (ex - 18, ey + 20))

        # Draw party (bottom left)
        for i, char in enumerate(self.battle.party):
            px = 40 + i * 100
            py = 220
            sprite = self.sprites.get_scaled(char, 64)
            if char.stats.hp > 0:
                self.game_surface.blit(sprite, (px, py))
            else:
                faded = sprite.copy()
                faded.set_alpha(80)
                self.game_surface.blit(faded, (px, py + 10))
            # Name
            name_font = self.fonts.get(10)
            name_surf = name_font.render(char.name, True, TEXT_COLOR)
            self.game_surface.blit(name_surf, (px, py + 68))
            # HP bar
            hp_ratio = char.stats.hp / char.stats.max_hp
            hp_color = Palette.HP_GREEN if hp_ratio > 0.5 else (Palette.HP_YELLOW if hp_ratio > 0.25 else Palette.HP_RED)
            draw_bar(self.game_surface, px, py + 82, 60, 6, hp_ratio, hp_color)
            # MP bar
            mp_ratio = char.stats.mp / char.stats.max_mp if char.stats.max_mp > 0 else 0
            draw_bar(self.game_surface, px, py + 90, 60, 4, mp_ratio, Palette.XP_BLUE)
            # Current turn indicator
            if (self.battle.is_player_turn and i == self.battle.turn_index
                    and not self.battle.victory and not self.battle.defeat):
                pygame.draw.rect(self.game_surface, GOLD,
                               (px - 3, py - 3, 70, 100), 2)

        # Action menu (bottom)
        if self.battle.is_player_turn and not self.battle.victory and not self.battle.defeat:
            if not self.battle.selecting_target:
                actions = self.battle.get_actions()
                menu_x, menu_y = 20, 340
                menu_w = 200
                menu_h = len(actions) * 24 + 16
                menu_surf = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
                menu_surf.fill((12, 12, 24, 230))
                self.game_surface.blit(menu_surf, (menu_x, menu_y))
                pygame.draw.rect(self.game_surface, (80, 80, 120),
                               (menu_x, menu_y, menu_w, menu_h), 1)

                action_font = self.fonts.get(13)
                for j, action in enumerate(actions):
                    is_sel = (j == self.battle.selected_action)
                    color = CHOICE_HIGHLIGHT if is_sel else TEXT_COLOR
                    prefix = "> " if is_sel else "  "
                    txt = action_font.render(f"{prefix}{action}", True, color)
                    self.game_surface.blit(txt, (menu_x + 8, menu_y + 8 + j * 24))
            else:
                hint_font = self.fonts.get(12)
                hint = hint_font.render("Select target (UP/DOWN + ENTER)", True, CHOICE_HIGHLIGHT)
                self.game_surface.blit(hint, (20, 340))

        # Battle log (bottom area)
        log_font = self.fonts.get(11)
        visible_log = self.battle.battle_log[-4:]
        for i, msg in enumerate(visible_log):
            log_surf = log_font.render(msg, True, (200, 200, 220))
            self.game_surface.blit(log_surf, (20, GAME_H - 80 + i * 16))

        # Victory / Defeat overlay
        if self.battle.victory or self.battle.defeat:
            overlay = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.game_surface.blit(overlay, (0, 0))
            result_font = self.fonts.get(28, bold=True)
            if self.battle.victory:
                result = result_font.render("VICTORY!", True, GOLD)
            else:
                result = result_font.render("DEFEAT", True, Palette.HP_RED)
            self.game_surface.blit(result,
                                  (GAME_W // 2 - result.get_width() // 2,
                                   GAME_H // 2 - result.get_height() // 2 - 20))
            cont_font = self.fonts.get(13)
            cont = cont_font.render("Press ENTER to continue", True, TEXT_COLOR)
            self.game_surface.blit(cont,
                                  (GAME_W // 2 - cont.get_width() // 2,
                                   GAME_H // 2 + 20))

    # ------------------------------------------------------------------
    # Transition Effect
    # ------------------------------------------------------------------
    def _draw_transition(self) -> None:
        """Draw scene transition effect on the game surface."""
        progress = self.transition_progress
        if progress < 0.5:
            # Fade to black
            alpha = int(255 * (progress * 2))
        else:
            # Fade from black
            alpha = int(255 * (2 - progress * 2))
        alpha = max(0, min(255, alpha))
        overlay = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        self.game_surface.blit(overlay, (0, 0))

    # ------------------------------------------------------------------
    # Dashboard Panel
    # ------------------------------------------------------------------
    def _draw_dashboard(self) -> None:
        """Draw the right-side dashboard panel."""
        # Background
        dash_rect = pygame.Rect(DASH_X, 0, DASH_W, WINDOW_H)
        pygame.draw.rect(self.screen, DASH_BG, dash_rect)
        pygame.draw.line(self.screen, DASH_BORDER, (DASH_X, 0), (DASH_X, WINDOW_H), 2)

        # Title
        dash_title_font = self.fonts.get(14, bold=True)
        dash_title = dash_title_font.render("SCBE DASHBOARD", True, GOLD)
        self.screen.blit(dash_title, (DASH_X + 12, 10))

        # Separator
        pygame.draw.line(self.screen, DASH_BORDER, (DASH_X + 10, 32), (WINDOW_W - 10, 32), 1)

        y = 40

        # ---- Party Portraits ----
        section_font = self.fonts.get(11, bold=True)
        section_title = section_font.render("PARTY", True, DIM_TEXT)
        self.screen.blit(section_title, (DASH_X + 12, y))
        y += 20

        stat_font = self.fonts.get(10)
        for i, char in enumerate(self.party[:6]):
            portrait = self.sprites.get_scaled(char, 48)
            self.screen.blit(portrait, (DASH_X + 12, y))

            # Name and stage
            name_surf = stat_font.render(f"{char.name}", True, TEXT_COLOR)
            self.screen.blit(name_surf, (DASH_X + 66, y + 2))
            stage_color = TONGUE_COLORS.get(char.tongue_affinity.value, DIM_TEXT)
            stage_surf = self.fonts.get(9).render(f"[{char.evo_stage.value}]", True, stage_color)
            self.screen.blit(stage_surf, (DASH_X + 66, y + 14))

            # HP bar
            hp_ratio = char.stats.hp / char.stats.max_hp
            hp_color = Palette.HP_GREEN if hp_ratio > 0.5 else (Palette.HP_YELLOW if hp_ratio > 0.25 else Palette.HP_RED)
            draw_bar(self.screen, DASH_X + 66, y + 28, 100, 8, hp_ratio, hp_color)
            hp_text = stat_font.render(f"{char.stats.hp}/{char.stats.max_hp}", True, DIM_TEXT)
            self.screen.blit(hp_text, (DASH_X + 170, y + 26))

            # MP bar
            mp_ratio = char.stats.mp / char.stats.max_mp if char.stats.max_mp > 0 else 0
            draw_bar(self.screen, DASH_X + 66, y + 38, 100, 6, mp_ratio, Palette.XP_BLUE)
            mp_text = self.fonts.get(9).render(f"MP {char.stats.mp}/{char.stats.max_mp}", True, DIM_TEXT)
            self.screen.blit(mp_text, (DASH_X + 170, y + 36))

            y += 54

        # Separator
        pygame.draw.line(self.screen, DASH_BORDER, (DASH_X + 10, y + 4), (WINDOW_W - 10, y + 4), 1)
        y += 12

        # ---- AI Companion Thoughts ----
        thoughts_title = section_font.render("AI COMPANION THOUGHTS", True, DIM_TEXT)
        self.screen.blit(thoughts_title, (DASH_X + 12, y))
        y += 18

        thoughts = self.scene.companion_thoughts
        thought_font = self.fonts.get(10)
        visible_thoughts = thoughts[-4:] if thoughts else [("SYSTEM", "Awaiting scene data...")]
        for speaker, text in visible_thoughts:
            # Speaker colored
            if speaker == "POLLY":
                sc = TONGUE_COLORS["KO"]
            elif speaker == "CLAY":
                sc = TONGUE_COLORS["RU"]
            else:
                sc = (100, 180, 220)
            sp_surf = thought_font.render(f"{speaker}:", True, sc)
            self.screen.blit(sp_surf, (DASH_X + 16, y))
            y += 14

            # Thought text (wrapped)
            text_rect = pygame.Rect(DASH_X + 20, y, DASH_W - 36, 36)
            y = draw_text_wrapped(self.screen, text, thought_font, (160, 160, 190), text_rect)
            y += 4

        # Separator
        pygame.draw.line(self.screen, DASH_BORDER, (DASH_X + 10, y + 4), (WINDOW_W - 10, y + 4), 1)
        y += 12

        # ---- SCBE Layer Activity ----
        layer_title = section_font.render("SCBE LAYER ACTIVITY", True, DIM_TEXT)
        self.screen.blit(layer_title, (DASH_X + 12, y))
        y += 18

        layer_font = self.fonts.get(9)
        bar_w = 120
        bar_h = 10

        for layer_num, layer_name, layer_color in SCBE_LAYERS:
            activity = self.layer_activity.get(layer_num, 0.0)

            # Layer number
            num_surf = layer_font.render(f"L{layer_num:02d}", True, DIM_TEXT)
            self.screen.blit(num_surf, (DASH_X + 12, y))

            # Layer name
            name_color = layer_color if activity > 0.3 else DIM_TEXT
            name_surf = layer_font.render(layer_name, True, name_color)
            self.screen.blit(name_surf, (DASH_X + 42, y))

            # Activity bar
            bar_x = DASH_X + 110
            if activity > 0.1:
                # Pulsing glow effect
                pulse = 0.8 + 0.2 * math.sin(time.time() * 4 + layer_num)
                bar_color = lerp_color((30, 30, 40), layer_color, activity * pulse)
            else:
                bar_color = (30, 30, 40)
            draw_bar(self.screen, bar_x, y + 1, bar_w, bar_h, activity, bar_color)

            # Percentage
            pct = layer_font.render(f"{int(activity * 100)}%", True, DIM_TEXT)
            self.screen.blit(pct, (bar_x + bar_w + 6, y))

            y += bar_h + 4

        # Separator
        y += 4
        pygame.draw.line(self.screen, DASH_BORDER, (DASH_X + 10, y), (WINDOW_W - 10, y), 1)
        y += 8

        # ---- Tongue Proficiency ----
        if self.show_dashboard_detail and self.party:
            prof_title = section_font.render("TONGUE PROFICIENCY", True, DIM_TEXT)
            self.screen.blit(prof_title, (DASH_X + 12, y))
            y += 16

            char = self.party[0]
            prof_font = self.fonts.get(10)
            for code in ["KO", "AV", "RU", "CA", "UM", "DR"]:
                val = char.stats.tongue_prof.get(code, 0.0)
                tc = TONGUE_COLORS[code]
                lbl = prof_font.render(f"{code}", True, tc)
                self.screen.blit(lbl, (DASH_X + 16, y))
                draw_bar(self.screen, DASH_X + 44, y + 2, 80, 8, val, tc)
                pct = prof_font.render(f"{int(val * 100)}%", True, DIM_TEXT)
                self.screen.blit(pct, (DASH_X + 130, y))
                y += 16

        # ---- Training Data Counter (always at bottom) ----
        counter_y = WINDOW_H - 40
        pygame.draw.line(self.screen, DASH_BORDER, (DASH_X + 10, counter_y - 8), (WINDOW_W - 10, counter_y - 8), 1)
        counter_font = self.fonts.get(11, bold=True)
        total = self.sft_count + self.dpo_count
        counter_text = f"Training Pairs: {total} | SFT: {self.sft_count} | DPO: {self.dpo_count}"
        counter_surf = counter_font.render(counter_text, True, GOLD)
        self.screen.blit(counter_surf, (DASH_X + 12, counter_y))

        # Session info
        session_font = self.fonts.get(9)
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        session_text = f"Session: {self.exporter.session_id[:8]}  |  {minutes:02d}:{seconds:02d}"
        session_surf = session_font.render(session_text, True, (80, 80, 100))
        self.screen.blit(session_surf, (DASH_X + 12, counter_y + 18))

    # ------------------------------------------------------------------
    # Pause Menu
    # ------------------------------------------------------------------
    def _draw_pause(self) -> None:
        """Draw the pause overlay."""
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill(PAUSE_OVERLAY)
        self.screen.blit(overlay, (0, 0))

        pause_font = self.fonts.get(28, bold=True)
        pause_text = pause_font.render("PAUSED", True, GOLD)
        self.screen.blit(pause_text,
                        (WINDOW_W // 2 - pause_text.get_width() // 2, WINDOW_H // 2 - 60))

        menu_font = self.fonts.get(16)
        items = [
            ("Press ENTER or ESC to resume", TEXT_COLOR),
            ("Press Q to save & quit", DIM_TEXT),
            ("", DIM_TEXT),
            (f"Scene: {self.scene.current_scene_id}", DIM_TEXT),
            (f"Party: {len(self.party)} members", DIM_TEXT),
            (f"Training data: {self.exporter.total_pairs} pairs", DIM_TEXT),
        ]
        for i, (text, color) in enumerate(items):
            if text:
                surf = menu_font.render(text, True, color)
                self.screen.blit(surf,
                               (WINDOW_W // 2 - surf.get_width() // 2,
                                WINDOW_H // 2 + i * 28))


# ---------------------------------------------------------------------------
# We need Stats from engine; it was imported via GameState's field defaults
# but let's also make it available for _start_test_battle
# ---------------------------------------------------------------------------
from engine import Stats


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main() -> None:
    """Launch the Aethermoor pilot demo."""
    print(f"\n{'=' * 60}")
    print(f"  {GAME_TITLE}")
    print(f"  Pilot Customer Demo  |  SCBE v3.0")
    print(f"  USPTO #63/961,403")
    print(f"{'=' * 60}")
    print()
    print("  Controls:")
    print("    Arrow Keys / WASD  -  Navigate menus")
    print("    Enter / Space      -  Advance / Select")
    print("    1-7                -  Quick-select choice")
    print("    Tab                -  Toggle dashboard detail")
    print("    Escape             -  Pause menu")
    print("    B                  -  Test battle encounter")
    print()

    game = AethermoorGame()
    game.run()

    print("\n  Session complete. Aethermoor awaits your return.\n")


if __name__ == "__main__":
    main()
