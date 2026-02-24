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
BOOKS_OUT = Path(__file__).resolve().parent / "training_output" / "books"
BOOKS_OUT.mkdir(parents=True, exist_ok=True)

GOLD = (255, 215, 80)
BEZEL_COLOR = (22, 22, 34)
BEZEL_HIGHLIGHT = (40, 40, 58)
SCREEN_BG = (14, 14, 22)
DASH_BG = (16, 18, 28)
DASH_BORDER = (48, 52, 72)
TEXT_COLOR = (235, 235, 250)
DIM_TEXT = (130, 135, 165)
CHOICE_HIGHLIGHT = (255, 220, 80)
DIALOGUE_BG = (10, 10, 26, 235)
PAUSE_OVERLAY = (0, 0, 0, 200)

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
    "earth": (28, 34, 52),
    "aethermoor": (32, 24, 72),
    "battle": (42, 18, 24),
    "academy": (26, 28, 48),
    "transit": (12, 8, 36),
    "title": (8, 6, 18),
}

# ---------------------------------------------------------------------------
# Enhanced choice definitions for each scene
# Each choice: (label, action_key, tongue_code, active_layers)
# ---------------------------------------------------------------------------
SCENE_CHOICES: Dict[str, List[Tuple[str, str, str, List[int]]]] = {
    "earth_morning": [
        ("Take Mom's full kit: PollyPad, wallet, keys", "take_full_kit", "DR", [11, 12, 14]),
        ("Ask Mom about Dad at the shore", "ask_mom", "AV", [3, 4, 12]),
        ("Check PollyPad status window first", "check_pollypad", "CA", [1, 7, 11]),
        ("Count wallet cash and secure it", "check_wallet", "RU", [5, 6, 11]),
        ("Test the keyring rune on the front door", "test_keys", "UM", [8, 10, 12]),
        ("Promise Mom you'll help people on the path", "promise_help", "KO", [1, 13, 14]),
        ("Head out quietly, focused on the shore", "quiet_depart", "AV", [2, 3, 6]),
    ],
    "earth_work": [
        ("Help the lost traveler find the shore road", "help_traveler", "KO", [1, 2, 14]),
        ("Share your supplies and escort the traveler", "escort_traveler", "AV", [3, 4, 6]),
        ("Ask for rumors and map the forks in the path", "ask_directions", "CA", [2, 7, 11]),
        ("Ignore the traveler and keep moving", "ignore_traveler", "UM", [5, 8, 13]),
        ("Record the encounter in PollyPad for guild trust", "record_traveler", "DR", [3, 11, 12]),
        ("Offer prayer at the roadside shrine, then continue", "shrine_pause", "RU", [4, 5, 9]),
        ("Rush ahead before anyone can stop you", "rush_past", "CA", [1, 7, 10]),
    ],
    "earth_evening": [
        ("Battle the wild ripple-beast on the dunes", "fight_monster", "DR", [7, 8, 13]),
        ("Calm and tame the ripple-beast with PollyPad tones", "tame_monster", "KO", [1, 12, 14]),
        ("Talk with fishers: 'Marcus is running portals again'", "talk_gossip", "AV", [3, 4, 11]),
        ("Inspect shrine debris and accidentally break a vase", "break_vase", "UM", [5, 8, 10]),
        ("Help beach vendors repair a broken cart", "help_vendors", "CA", [6, 7, 14]),
        ("Document everything for guild reputation logs", "document_path", "DR", [3, 11, 12]),
        ("Keep moving and avoid all side events", "keep_moving", "RU", [2, 5, 6]),
    ],
    "earth_night": [
        ("Step through as Tamer class", "class_tamer", "CA", [1, 7, 10, 14]),
        ("Step through as Cipher class", "class_cipher", "DR", [8, 11, 12, 14]),
        ("Step through as Warden class", "class_warden", "KO", [1, 2, 13, 14]),
        ("Step through as Broker class", "class_broker", "AV", [2, 3, 4, 14]),
        ("Step through undecided and let the Tongues choose", "class_undecided", "RU", [4, 5, 6, 14]),
        ("Wait for Polly's signal, then enter", "class_polly", "UM", [9, 10, 12, 14]),
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
        ("", "INT. CHEN FAMILY HOME - MORNING."),
        ("", "Sunlight spills through rune-etched frames. A warm ocean breeze drifts in."),
        ("MOM", "Rise and shine, dear. Your dad is out at the shore again."),
        ("MOM", "Cellphone, Wallet, Keys. All a person needs to face the world."),
        ("", "She offers a gleaming keyring, a PollyPad, and a wallet."),
        ("MOM", "The PollyPad tracks your status window. The keys open more than doors."),
        ("SYSTEM", "[Player Level 1 | Class: Undecided | Reputation: Neutral]"),
    ],
    "earth_work": [
        ("", "EXT. COASTAL PATH - DAY."),
        ("", "You move through greenery and dunes toward the beach."),
        ("", "A traveler waves you down near a fork in the trail."),
        ("TRAVELER", "Please, I am turned around. Is the shattered shore this way?"),
        ("SYSTEM", "Choice here sets early guild impressions."),
        ("", "PollyPad hums softly, ready to log your decision."),
    ],
    "earth_evening": [
        ("", "Further down the path, the air turns electric."),
        ("", "A wild ripple-beast bursts from the dune grass."),
        ("POLLYPAD", "Advisor Hint: exploit weakness or stabilize before strike."),
        ("FISHER", "Heard Marcus Chen is trying portals again. Real crazy stuff."),
        ("", "A cracked shrine vase teeters beside the trail."),
        ("SYSTEM", "Actions here affect reputation and Marcus's reaction."),
    ],
    "earth_night": [
        ("", "EXT. SHATTERED SHORE - LATE MORNING."),
        ("", "Fractured masts and portal haze glitter across the sand."),
        ("", "Marcus Chen stands beside a swirling dimensional gate."),
        ("MARCUS CHEN", "There you are. This is the bridge experiment."),
        ("MARCUS CHEN", "Collaboration builds empires. Domination crumbles them."),
        ("MARCUS CHEN", "Step through. Choose your path. Guild Hub Town awaits."),
        ("", "Polly swoops down and lands on your shoulder."),
        ("POLLY", "Caw. The spiral turns. Choose with intent."),
    ],
    "transit": [
        ("", "The portal erupts with six-tone particles: KO, AV, RU, CA, UM, DR."),
        ("", "Sil'thara nav'een drifts like subtitles in the light."),
        ("", "You fall through layered protocol-space and hear the Tongues harmonize."),
        ("SYSTEM", "Layer Cascade: Intent -> Routing -> Context -> ... -> Integration."),
        ("", "For one breath, straight movement feels like a spiral."),
        ("", "Then gravity returns."),
    ],
    "aethermoor_arrival": [
        ("", "EXT. GUILD HUB TOWN - CONTINUOUS."),
        ("", "Adventurers crowd the square under floating banners and rune-signs."),
        ("POLLY", "No pet. Co-equal guide. I am Polly."),
        ("POLLY", "Class registered. Next: tongue shrine and guild alignment."),
        ("CLAY", "*happy grinding noises*"),
        ("SYSTEM", "New Arc Unlocked: Guild Registration"),
        ("SYSTEM", "Training data capture is active for every decision."),
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

# Digimon-like class identity: each class has an origin partner and growth bias.
CLASS_LOADOUTS: Dict[str, Dict[str, Any]] = {
    "class_tamer": {
        "name": "Tamer",
        "partner_key": "clay",
        "stat_boost": {"attack": 2, "speed": 1},
        "bond_bonus": 0.14,
    },
    "class_cipher": {
        "name": "Cipher",
        "partner_key": "zara",
        "stat_boost": {"wisdom": 2, "max_mp": 10},
        "bond_bonus": 0.12,
    },
    "class_warden": {
        "name": "Warden",
        "partner_key": "aria",
        "stat_boost": {"defense": 2, "max_hp": 18},
        "bond_bonus": 0.10,
    },
    "class_broker": {
        "name": "Broker",
        "partner_key": "eldrin",
        "stat_boost": {"speed": 2, "wisdom": 1},
        "bond_bonus": 0.08,
    },
    "class_undecided": {
        "name": "Undecided",
        "partner_key": "polly",
        "stat_boost": {},
        "bond_bonus": 0.05,
    },
    "class_polly": {
        "name": "Wildcard",
        "partner_key": "polly",
        "stat_boost": {"wisdom": 1},
        "bond_bonus": 0.16,
    },
}

# K-12-inspired zone progression: used as a quest and exploration guide.
EDUCATION_BANDS: List[Tuple[str, int, int]] = [
    ("K-2", 5, 7),
    ("3-5", 8, 10),
    ("6-8", 11, 13),
    ("9-12", 14, 18),
    ("Post-12", 19, 120),
]

SCENE_ZONE_MAP: Dict[str, str] = {
    "earth_morning": "Home Grove",
    "earth_work": "Coastal Path",
    "earth_evening": "Dune Edge",
    "earth_night": "Shattered Shore",
    "transit": "Spiral Transit",
    "aethermoor_arrival": "Guild Hub Commons",
    "academy_entrance": "Avalon Gate",
    "first_lesson": "Tongue Tower Commons",
}

BAND_QUESTS: Dict[str, Dict[str, Any]] = {
    "K-2": {
        "title": "Roots of Curiosity",
        "requirements": {"explore": 2, "help": 1, "craft": 0},
        "reward_gold": 20,
    },
    "3-5": {
        "title": "Hands-on Makers",
        "requirements": {"explore": 3, "help": 1, "craft": 1},
        "reward_gold": 35,
    },
    "6-8": {
        "title": "Steward of the Trail",
        "requirements": {"explore": 4, "help": 2, "craft": 2},
        "reward_gold": 55,
    },
    "9-12": {
        "title": "Guild Apprentice",
        "requirements": {"explore": 5, "help": 2, "craft": 3},
        "reward_gold": 85,
    },
    "Post-12": {
        "title": "Legacy Architect",
        "requirements": {"explore": 8, "help": 3, "craft": 5},
        "reward_gold": 140,
    },
}

CRAFTING_RECIPES: List[Dict[str, Any]] = [
    {
        "name": "Driftwood Keychain",
        "cost": {"driftwood": 2, "rune_ink": 1},
        "skill": "woodcraft",
        "reward_gold": 35,
    },
    {
        "name": "Field Journal",
        "cost": {"herb": 2, "shell": 1, "rune_ink": 2},
        "skill": "inscription",
        "reward_gold": 60,
    },
    {
        "name": "Resonance Charm",
        "cost": {"crystal_dust": 2, "driftwood": 1, "rune_ink": 1},
        "skill": "ecology",
        "reward_gold": 90,
    },
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

        # Digimon-style identity state (origin -> partner -> growth path)
        self.player_class: str = "Undecided"
        self.partner_key: str = "polly"
        self.partner_name: str = "Polly"
        self.partner_bond: float = 0.10
        self.reputation_points: int = 0
        self.generation: int = 1
        self.age_years: int = 14
        self.lifespan_years: int = random.randint(68, 84)
        self.years_per_choice: int = 1
        self.lineage_name: str = "Chen"
        self.lineage_history: List[Dict[str, Any]] = []
        self.legacy_relics: int = 0
        self.inventory: Dict[str, Any] = {
            "PollyPad": False,
            "Wallet": False,
            "Keys": False,
            "Gold": 0,
        }
        self.materials: Dict[str, int] = {
            "herb": 0,
            "driftwood": 0,
            "shell": 0,
            "rune_ink": 0,
            "crystal_dust": 0,
        }
        self.crafted_items: Dict[str, int] = {}
        self.nature_skills: Dict[str, int] = {
            "foraging": 0,
            "woodcraft": 0,
            "ecology": 0,
            "inscription": 0,
        }
        self.nature_skill_xp: Dict[str, int] = {
            "foraging": 0,
            "woodcraft": 0,
            "ecology": 0,
            "inscription": 0,
        }
        self.discovered_zones: Set[str] = set()
        self.band_quest_progress: Dict[str, Dict[str, int]] = {
            band: {"explore": 0, "help": 0, "craft": 0}
            for band, _, _ in EDUCATION_BANDS
        }
        self.completed_band_quests: Set[str] = set()
        self.story_flags: Dict[str, bool] = {
            "helped_someone": False,
            "caught_monster": False,
            "broke_something": False,
            "talked_to_everyone": False,
            "promise_help": False,
        }
        self._pending_scene: str = "earth_morning"
        self._pending_scene_after_battle: Optional[str] = None
        self._story_battle_active: bool = False
        self.workshop_open: bool = False
        self.workshop_cursor: int = 0
        self.workshop_message: str = "F6 toggles ChoiceScript Workshop."
        self.workshop_projects: List[Dict[str, Any]] = []
        self.workshop_active_index: int = -1
        self.autonomy_enabled: bool = True
        self.autonomy_timer: float = 0.0
        self.autonomy_interval: float = 12.0
        self.autonomy_log: List[str] = []

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

    def _reputation_label(self) -> str:
        """Map score to a compact reputation tier."""
        score = self.reputation_points
        if score >= 5:
            return "Trusted"
        if score >= 2:
            return "Warm"
        if score <= -3:
            return "Shaky"
        return "Neutral"

    def _bond_label(self) -> str:
        """Map partner bond value to human-readable tier."""
        b = self.partner_bond
        if b >= 0.80:
            return "Synced"
        if b >= 0.55:
            return "Linked"
        if b >= 0.30:
            return "Growing"
        return "Unstable"

    def _grade_band_for_age(self, age: int) -> str:
        """Resolve an age value to K-12-style band."""
        for band, min_age, max_age in EDUCATION_BANDS:
            if min_age <= age <= max_age:
                return band
        return "Post-12"

    def _current_grade_band(self) -> str:
        """Get current educational progression band."""
        return self._grade_band_for_age(self.age_years)

    def _zone_for_scene(self, scene_id: str) -> str:
        """Map scene to exploration zone."""
        return SCENE_ZONE_MAP.get(scene_id, "Unmapped Wilds")

    def _current_zone(self) -> str:
        """Get zone for current scene."""
        return self._zone_for_scene(self.scene.current_scene_id)

    def _active_band_quest(self) -> Dict[str, Any]:
        """Return quest definition for the current grade band."""
        return BAND_QUESTS[self._current_grade_band()]

    def _active_band_progress(self) -> Dict[str, int]:
        """Return mutable quest progress record for the current grade band."""
        return self.band_quest_progress[self._current_grade_band()]

    def _material_summary(self) -> str:
        """Compact material display string."""
        return (
            f"H{self.materials['herb']} D{self.materials['driftwood']} "
            f"S{self.materials['shell']} I{self.materials['rune_ink']} "
            f"C{self.materials['crystal_dust']}"
        )

    def _grant_skill_xp(self, skill: str, amount: int) -> None:
        """Grant skill XP and level-up when threshold reached."""
        if skill not in self.nature_skill_xp:
            return
        self.nature_skill_xp[skill] += amount
        threshold = 3 + self.nature_skills[skill] * 2
        while self.nature_skill_xp[skill] >= threshold:
            self.nature_skill_xp[skill] -= threshold
            self.nature_skills[skill] += 1
            self.reputation_points += 1
            self.partner_bond = min(1.0, self.partner_bond + 0.02)
            threshold = 3 + self.nature_skills[skill] * 2

    def _grant_material(self, material: str, amount: int) -> None:
        """Grant crafting materials safely."""
        if material not in self.materials:
            return
        self.materials[material] = max(0, self.materials[material] + amount)

    def _progress_band_quest(self, tag: str, amount: int = 1) -> None:
        """Track quest progression for current education band."""
        band = self._current_grade_band()
        if band in self.completed_band_quests:
            return
        if tag not in ("explore", "help", "craft"):
            return
        progress = self.band_quest_progress[band]
        progress[tag] += amount

        requirements = BAND_QUESTS[band]["requirements"]
        if all(progress[k] >= requirements[k] for k in requirements):
            self.completed_band_quests.add(band)
            self.inventory["Gold"] += int(BAND_QUESTS[band]["reward_gold"])
            self.partner_bond = min(1.0, self.partner_bond + 0.05)
            self.reputation_points += 2
            self.scene.companion_thoughts.append(
                ("POLLY", f"Quest complete: {BAND_QUESTS[band]['title']}. Legacy deepens.")
            )

    def _craft_available_items(self) -> List[str]:
        """Craft at most one available recipe per choice."""
        crafted: List[str] = []
        for recipe in CRAFTING_RECIPES:
            cost = recipe["cost"]
            if all(self.materials.get(mat, 0) >= qty for mat, qty in cost.items()):
                for mat, qty in cost.items():
                    self.materials[mat] -= qty
                name = str(recipe["name"])
                self.crafted_items[name] = self.crafted_items.get(name, 0) + 1
                self.inventory["Gold"] += int(recipe["reward_gold"])
                self._grant_skill_xp(str(recipe["skill"]), 1)
                self._progress_band_quest("craft", 1)
                crafted.append(name)
                break
        return crafted

    def _apply_progression_loop(self, scene_id: str, action: str) -> List[str]:
        """Apply exploration, quest, skill, and crafting progression from one choice."""
        zone = self._zone_for_scene(scene_id)
        first_visit = zone not in self.discovered_zones
        self.discovered_zones.add(zone)
        self._progress_band_quest("explore", 1)
        if first_visit:
            self.reputation_points += 1

        help_actions = {
            "help_traveler",
            "escort_traveler",
            "help_vendors",
            "promise_help",
        }
        if action in help_actions:
            self._progress_band_quest("help", 1)

        # Resource and skill gains by interaction style.
        if action in ("help_traveler", "escort_traveler"):
            self._grant_material("herb", 1)
            self._grant_material("driftwood", 1)
            self._grant_skill_xp("ecology", 1)
            self._grant_skill_xp("foraging", 1)
        elif action in ("ask_directions", "talk_gossip"):
            self._grant_skill_xp("ecology", 1)
        elif action in ("record_traveler", "document_path", "shrine_pause"):
            self._grant_material("rune_ink", 1)
            self._grant_skill_xp("inscription", 1)
        elif action == "help_vendors":
            self._grant_material("driftwood", 2)
            self._grant_skill_xp("woodcraft", 1)
        elif action == "break_vase":
            self._grant_material("shell", 1)
            self._grant_material("crystal_dust", 1)
            self._grant_skill_xp("woodcraft", 1)
        elif action in ("fight_monster", "tame_monster"):
            self._grant_material("crystal_dust", 1)
            self._grant_skill_xp("ecology", 2)
        elif action.startswith("class_"):
            self._grant_skill_xp("ecology", 1)
        elif action.startswith("learn_"):
            self._grant_material("rune_ink", 1)
            self._grant_skill_xp("inscription", 1)

        crafted = self._craft_available_items()
        return crafted

    def _advance_life_cycle(self) -> None:
        """Age the current protagonist and rotate generation when lifespan ends."""
        self.age_years += self.years_per_choice
        if self.age_years >= self.lifespan_years:
            self._trigger_generation_shift()

    def _trigger_generation_shift(self) -> None:
        """Retire current protagonist and continue as next generation heir."""
        legacy_crafts = sum(self.crafted_items.values())
        legacy_skills = sum(self.nature_skills.values())

        self.lineage_history.append(
            {
                "generation": self.generation,
                "age": self.age_years,
                "class": self.player_class,
                "reputation": self.reputation_points,
                "crafted_total": legacy_crafts,
                "skills_total": legacy_skills,
            }
        )

        self.legacy_relics += legacy_crafts
        self.generation += 1
        self.age_years = 12
        self.lifespan_years = random.randint(68, 84)
        self.player_class = "Undecided"
        self.partner_key = "polly"
        self.partner_name = "Polly"
        self.partner_bond = min(0.45, 0.15 + legacy_skills * 0.01)
        self.reputation_points = max(0, self.reputation_points // 2)
        self.materials = {k: max(0, v // 2) for k, v in self.materials.items()}
        self.crafted_items = {}
        self.story_flags = {k: False for k in self.story_flags}

        if self.party:
            heir = self.party[0]
            heir.name = f"{self.lineage_name} Heir G{self.generation}"
            heir.title = "Lineage Successor"
            heir.stats.attack += legacy_crafts // 5
            heir.stats.wisdom += legacy_skills // 6
            heir.stats.hp = heir.stats.max_hp
            heir.stats.mp = heir.stats.max_mp
            for code, val in list(heir.stats.tongue_prof.items()):
                heir.stats.tongue_prof[code] = min(1.0, val * 0.65 + 0.05)

        self.scene.companion_thoughts.append(
            ("POLLY", f"Generation shift complete. Dynasty rises to G{self.generation}.")
        )

    def _workshop_active_project(self) -> Optional[Dict[str, Any]]:
        """Return currently selected workshop project."""
        if 0 <= self.workshop_active_index < len(self.workshop_projects):
            return self.workshop_projects[self.workshop_active_index]
        return None

    def _workshop_create_project(self) -> None:
        """Create a new nested ChoiceScript book template."""
        title = f"Dynasty Book G{self.generation}-{len(self.workshop_projects) + 1}"
        script = [
            f"*title {title}",
            "*author Spiralverse Workshop",
            "*label start",
            "You wake inside the Scriptorium of the World Tree.",
            "*choice",
            "  #Seek allies first",
            "    *goto allies",
            "  #Walk alone into the unknown",
            "    *goto solo",
            "*label allies",
            "You gather companions and map the zone with care.",
            "*finish",
            "*label solo",
            "You test your resolve and face the dunes alone.",
            "*finish",
        ]
        self.workshop_projects.append(
            {
                "title": title,
                "script": script,
                "reads": 0,
                "playtests": 0,
                "exports": 0,
            }
        )
        self.workshop_active_index = len(self.workshop_projects) - 1
        self.workshop_message = f"Created {title}."

    def _workshop_add_branch_from_scene(self) -> None:
        """Append current scene choices as a branch in active ChoiceScript book."""
        project = self._workshop_active_project()
        if project is None:
            self._workshop_create_project()
            project = self._workshop_active_project()
        if project is None:
            return

        scene_id = self.scene.current_scene_id
        branch_label = f"scene_{scene_id}_{int(time.time()) % 10000}"
        project["script"].append(f"*label {branch_label}")
        project["script"].append(f"You enter {scene_id.replace('_', ' ')} and weigh your options.")
        project["script"].append("*choice")
        if not self.scene.choices:
            project["script"].append("  #Observe quietly")
            project["script"].append("    *finish")
        else:
            for label, action, tongue, _ in self.scene.choices[:3]:
                clean = label.replace("[", "").replace("]", "")
                option_label = f"opt_{action}"
                project["script"].append(f"  #{clean} [{tongue}]")
                project["script"].append(f"    *goto {option_label}")
                project["script"].append(f"*label {option_label}")
                project["script"].append(f"You committed to {action}.")
                project["script"].append("*finish")
        self.workshop_message = f"Added branch from {scene_id} to {project['title']}."

    def _workshop_ai_read(self) -> None:
        """Simulate AI companions reading authored books."""
        project = self._workshop_active_project()
        if project is None:
            self.workshop_message = "No book selected. Create one first."
            return
        project["reads"] += 1
        self.inventory["Gold"] += 18
        self.partner_bond = min(1.0, self.partner_bond + 0.03)
        self._grant_skill_xp("inscription", 1)
        self._progress_band_quest("craft", 1)
        self.exporter.record_choice(
            context=f"Workshop read in {project['title']}",
            choice_made="AI reading session",
            alternatives=["Skip reading"],
            outcome=(
                f"Companions read the book. Reads={project['reads']} "
                f"Bond={self.partner_bond:.2f} Gold={self.inventory['Gold']}"
            ),
            category="nested_choicescript_read",
        )
        self.sft_count += 1
        self.workshop_message = f"AI read {project['title']}. Insights increased."

    def _workshop_playtest(self) -> None:
        """Run a lightweight nested playtest pass."""
        project = self._workshop_active_project()
        if project is None:
            self.workshop_message = "No project available to playtest."
            return
        project["playtests"] += 1
        self.reputation_points += 1
        self._progress_band_quest("explore", 1)
        self.exporter.record_choice(
            context=f"Nested playtest for {project['title']}",
            choice_made="Run nested scenario",
            alternatives=["Do not run nested scenario"],
            outcome=(
                f"Playtest count={project['playtests']} Reputation={self.reputation_points} "
                f"Generation={self.generation}"
            ),
            category="nested_choicescript_playtest",
        )
        self.sft_count += 1
        self.workshop_message = f"Playtest complete for {project['title']}."

    def _workshop_export(self) -> None:
        """Export active ChoiceScript draft to disk."""
        project = self._workshop_active_project()
        if project is None:
            self.workshop_message = "No project to export."
            return

        stamp = int(time.time())
        safe_title = "".join(ch if ch.isalnum() else "_" for ch in project["title"]).strip("_")
        out_path = BOOKS_OUT / f"{safe_title}_{stamp}.txt"
        out_path.write_text("\n".join(project["script"]) + "\n", encoding="utf-8")
        project["exports"] += 1
        self.workshop_message = f"Exported {project['title']} to {out_path.name}."

    def _handle_workshop_key(self, key: int) -> None:
        """Handle keyboard input while workshop overlay is open."""
        options = 5
        if key in (pygame.K_ESCAPE, pygame.K_F6):
            self.workshop_open = False
            self.workshop_message = "Workshop closed."
            return
        if key in (pygame.K_UP, pygame.K_w):
            self.workshop_cursor = (self.workshop_cursor - 1) % options
            return
        if key in (pygame.K_DOWN, pygame.K_s):
            self.workshop_cursor = (self.workshop_cursor + 1) % options
            return
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.workshop_cursor == 0:
                self._workshop_create_project()
            elif self.workshop_cursor == 1:
                self._workshop_add_branch_from_scene()
            elif self.workshop_cursor == 2:
                self._workshop_ai_read()
            elif self.workshop_cursor == 3:
                self._workshop_playtest()
            elif self.workshop_cursor == 4:
                self._workshop_export()

    def _run_autonomy_tick(self) -> None:
        """Let companions perform autonomous side actions (Sims-like lite mode)."""
        if not self.autonomy_enabled:
            return
        if not self.party:
            return

        actor = random.choice(self.party[1:] if len(self.party) > 1 else self.party)
        roll = random.random()
        action_msg = ""
        if roll < 0.25:
            self._grant_material("herb", 1)
            self._grant_skill_xp("foraging", 1)
            action_msg = f"{actor.name} foraged herbs."
        elif roll < 0.50:
            self._grant_material("driftwood", 1)
            self._grant_skill_xp("woodcraft", 1)
            action_msg = f"{actor.name} salvaged driftwood."
        elif roll < 0.70:
            if not self.workshop_projects:
                self._workshop_create_project()
            self._workshop_ai_read()
            action_msg = f"{actor.name} read a workshop book."
        elif roll < 0.88:
            crafted = self._craft_available_items()
            if crafted:
                action_msg = f"{actor.name} crafted {crafted[0]}."
            else:
                self._grant_material("rune_ink", 1)
                action_msg = f"{actor.name} prepared rune ink."
        else:
            self.reputation_points += 1
            self.partner_bond = min(1.0, self.partner_bond + 0.02)
            action_msg = f"{actor.name} strengthened guild ties."

        if action_msg:
            self.autonomy_log.append(action_msg)
            self.autonomy_log = self.autonomy_log[-5:]
            self.scene.companion_thoughts.append(("SYSTEM", action_msg))
            self.scene.companion_thoughts = self.scene.companion_thoughts[-8:]

    def _load_scene(self, scene_id: str) -> None:
        """Load scene then inject dynamic narrative state."""
        self.scene.load_scene(scene_id)
        zone = self._zone_for_scene(scene_id)
        band = self._current_grade_band()
        quest = self._active_band_quest()["title"]

        if scene_id == "earth_morning":
            # Keep the status popup grounded in current run state.
            self.scene.dialogue_lines = [
                line for line in self.scene.dialogue_lines
                if not (
                    line[0] == "SYSTEM"
                    and "Player Level 1" in line[1]
                )
            ]
            self.scene.dialogue_lines.append(
                (
                    "SYSTEM",
                    (
                        f"[Player L1 | Gen {self.generation} | Age {self.age_years} | "
                        f"Class: {self.player_class} | Rep: {self._reputation_label()} | "
                        f"Bond: {self._bond_label()} | Stage: {band}]"
                    ),
                )
            )
        elif scene_id == "earth_night":
            self._inject_shore_reactivity()
        elif scene_id == "aethermoor_arrival":
            self.scene.dialogue_lines.insert(
                4,
                (
                    "SYSTEM",
                    (
                        f"[Class Locked: {self.player_class} | Partner: {self.partner_name} | "
                        f"Stage: {band} | Quest: {quest} | Gold: {self.inventory['Gold']}]"
                    ),
                ),
            )

        if scene_id != "title":
            self.scene.dialogue_lines.append(
                (
                    "SYSTEM",
                    (
                        f"[Zone: {zone} | Materials: {self._material_summary()} | "
                        f"Active Quest: {quest}]"
                    ),
                )
            )

    def _inject_shore_reactivity(self) -> None:
        """Inject Marcus reactions using path flags."""
        dynamic: List[Tuple[str, str]] = []
        if self.story_flags["helped_someone"]:
            dynamic.append(
                ("MARCUS CHEN", "Heard you helped people on the path. Good instinct.")
            )
        if self.story_flags["caught_monster"]:
            dynamic.append(
                ("MARCUS CHEN", "You handled the ripple-beast already? Strong field composure.")
            )
        if self.story_flags["broke_something"]:
            dynamic.append(
                ("MARCUS CHEN", "Breaking relics happens. Owning it is what matters.")
            )
        if self.story_flags["talked_to_everyone"]:
            dynamic.append(
                ("MARCUS CHEN", "You mapped the chatter on the road. Broker mindset.")
            )
        if dynamic:
            # Insert reactions right after Marcus appears.
            self.scene.dialogue_lines[4:4] = dynamic

    def _apply_class_loadout(self, action: str) -> None:
        """Set class identity and apply one-time stat boost."""
        config = CLASS_LOADOUTS.get(action)
        if not config:
            return

        self.player_class = str(config["name"])
        partner_key = str(config["partner_key"])
        self.partner_key = partner_key
        self.partner_name = self.cast.get(partner_key, self.cast["polly"]).name
        self.partner_bond = min(1.0, self.partner_bond + float(config["bond_bonus"]))

        if not self.party:
            return
        hero = self.party[0]
        boost = config.get("stat_boost", {})
        if "attack" in boost:
            hero.stats.attack += int(boost["attack"])
        if "defense" in boost:
            hero.stats.defense += int(boost["defense"])
        if "speed" in boost:
            hero.stats.speed += int(boost["speed"])
        if "wisdom" in boost:
            hero.stats.wisdom += int(boost["wisdom"])
        if "max_hp" in boost:
            bonus_hp = int(boost["max_hp"])
            hero.stats.max_hp += bonus_hp
            hero.stats.hp += bonus_hp
        if "max_mp" in boost:
            bonus_mp = int(boost["max_mp"])
            hero.stats.max_mp += bonus_mp
            hero.stats.mp += bonus_mp

    def _apply_story_action(self, scene_id: str, action: str) -> None:
        """Apply scene-specific state changes for reputation/flags/inventory."""
        if scene_id == "earth_morning":
            if action == "take_full_kit":
                self.inventory["PollyPad"] = True
                self.inventory["Wallet"] = True
                self.inventory["Keys"] = True
                self.inventory["Gold"] += 100
                self.reputation_points += 1
            elif action == "check_wallet":
                self.inventory["Wallet"] = True
                self.inventory["Gold"] += 100
            elif action == "check_pollypad":
                self.inventory["PollyPad"] = True
                self.partner_bond = min(1.0, self.partner_bond + 0.04)
            elif action == "test_keys":
                self.inventory["Keys"] = True
            elif action == "promise_help":
                self.story_flags["promise_help"] = True
                self.reputation_points += 1
                self.partner_bond = min(1.0, self.partner_bond + 0.05)
            elif action == "quiet_depart":
                self.reputation_points -= 1

        elif scene_id == "earth_work":
            if action in ("help_traveler", "escort_traveler"):
                self.story_flags["helped_someone"] = True
                self.reputation_points += 2
                self.partner_bond = min(1.0, self.partner_bond + 0.06)
            elif action in ("ask_directions", "record_traveler"):
                self.story_flags["talked_to_everyone"] = True
                self.reputation_points += 1
            elif action == "shrine_pause":
                self.reputation_points += 1
                self.partner_bond = min(1.0, self.partner_bond + 0.03)
            elif action in ("ignore_traveler", "rush_past"):
                self.reputation_points -= 2
                self.partner_bond = max(0.0, self.partner_bond - 0.04)

        elif scene_id == "earth_evening":
            if action in ("fight_monster", "tame_monster"):
                self.story_flags["caught_monster"] = True
                self.reputation_points += 1 if action == "fight_monster" else 2
            elif action in ("talk_gossip", "document_path"):
                self.story_flags["talked_to_everyone"] = True
                self.reputation_points += 1
            elif action == "help_vendors":
                self.story_flags["helped_someone"] = True
                self.reputation_points += 2
                self.partner_bond = min(1.0, self.partner_bond + 0.05)
            elif action == "break_vase":
                self.story_flags["broke_something"] = True
                self.reputation_points -= 2
                self.partner_bond = max(0.0, self.partner_bond - 0.03)

        elif scene_id == "earth_night":
            self._apply_class_loadout(action)

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
        if key == pygame.K_F7:
            self.autonomy_enabled = not self.autonomy_enabled
            state = "ON" if self.autonomy_enabled else "OFF"
            self.workshop_message = f"Companion autonomy {state}."
            return

        if key == pygame.K_F6:
            self.workshop_open = not self.workshop_open
            if self.workshop_open and not self.workshop_projects:
                self._workshop_create_project()
            self.workshop_message = (
                "Workshop opened. Build nested ChoiceScript stories."
                if self.workshop_open
                else "Workshop closed."
            )
            return

        if self.workshop_open:
            self._handle_workshop_key(key)
            return

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
            self._load_scene("earth_morning")
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
                if self.battle.victory and self._story_battle_active:
                    self._grant_material("crystal_dust", 1)
                    self._grant_material("shell", 1)
                    self._grant_skill_xp("ecology", 1)
                    self._progress_band_quest("craft", 1)
                self.battle.end_battle()
                # Heal party slightly after battle
                for c in self.party:
                    c.stats.hp = min(c.stats.max_hp, c.stats.hp + c.stats.max_hp // 4)
                    c.stats.mp = min(c.stats.max_mp, c.stats.mp + c.stats.max_mp // 4)
                self._story_battle_active = False
                if self._pending_scene_after_battle:
                    self.transitioning = True
                    self.transition_progress = 0.0
                    self._pending_scene = self._pending_scene_after_battle
                    self._pending_scene_after_battle = None
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
        scene_id = self.scene.current_scene_id

        # Activate layers
        self.scene.active_layers = set(layers)
        now = time.time()
        for layer_num in layers:
            self.scene.layer_pulse_timers[layer_num] = now
            self.layer_activity[layer_num] = 1.0

        # Emit tongue-colored particles
        tc = TONGUE_COLORS.get(tongue, (200, 200, 200))
        self.particles.emit(GAME_W // 2, GAME_H // 2 - 40, tc, count=20, spread=3.5)

        # Story-state update before logging/export.
        self._apply_story_action(scene_id, action)
        crafted_now = self._apply_progression_loop(scene_id, action)
        self._advance_life_cycle()

        # Record training data
        all_labels = [c[0] for c in self.scene.choices]
        active_flags = [k for k, v in self.story_flags.items() if v]
        band = self._current_grade_band()
        zone = self._zone_for_scene(scene_id)
        quest_progress = self._active_band_progress()
        self.exporter.record_choice(
            context=f"Scene: {scene_id}. "
                    f"Dialogue context: {self.scene.get_current_line()}",
            choice_made=label,
            alternatives=[l for l in all_labels if l != label],
            outcome=(
                f"Player chose {action} (Tongue: {tongue}, Layers: {layers}). "
                f"Class={self.player_class}, Partner={self.partner_name}, "
                f"Gen={self.generation}, Age={self.age_years}, Stage={band}, Zone={zone}, "
                f"Reputation={self._reputation_label()} ({self.reputation_points}), "
                f"Bond={self.partner_bond:.2f}, "
                f"Inventory={self.inventory}, Materials={self.materials}, "
                f"NatureSkills={self.nature_skills}, QuestProgress={quest_progress}, "
                f"CraftedNow={crafted_now or ['none']}, "
                f"ActiveFlags={active_flags or ['none']}."
            ),
            category=f"scene_{scene_id}",
        )
        self.sft_count += 1

        # Record DPO pair (chosen vs worst alternative)
        if len(self.scene.choices) > 1:
            self.dpo_count += 1

        # Boost tongue proficiency for the protagonist
        if self.party:
            prof = self.party[0].stats.tongue_prof
            current = prof.get(tongue, 0.0)
            prof[tongue] = min(1.0, current + 0.02)

        # Digimon-like encounter pacing: some choices enter battle first.
        if scene_id == "earth_evening" and action in {"fight_monster", "tame_monster"}:
            self._pending_scene_after_battle = self.scene.next_scene()
            self._start_story_battle(action)
            return

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
                # Guide + chosen partner (Digimon-like origin pair)
                polly = self.cast["polly"]
                if not any(c.name == polly.name for c in self.party):
                    self.party.append(polly)
                partner = self.cast.get(self.partner_key, self.cast["clay"])
                if not any(c.name == partner.name for c in self.party):
                    self.party.append(partner)
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

    def _start_story_battle(self, action: str) -> None:
        """Start contextual story battle for shoreline monster events."""
        self._story_battle_active = True
        if action == "tame_monster":
            enemy = Character(
                name="Ripple Beast",
                title="Agitated Familiar",
                tongue_affinity=Tongue.CA,
                evo_stage=EvoStage.FRESH,
                stats=Stats(
                    hp=55,
                    max_hp=55,
                    mp=28,
                    max_mp=28,
                    attack=7,
                    defense=7,
                    speed=8,
                    wisdom=6,
                ),
                spells=[
                    Spell("Wave Glint", Tongue.CA, 10, 6, "A nervous shimmer strike"),
                ],
                is_enemy=True,
            )
            self.battle.start_battle(
                party=[c for c in self.party if c.stats.hp > 0],
                enemies=[enemy],
            )
            self.battle.battle_log.append("PollyPad: Soften its stance, then bind with intent.")
            self.partner_bond = min(1.0, self.partner_bond + 0.04)
        else:
            enemy1 = Character(
                name="Ripple Beast",
                title="Wild Surge",
                tongue_affinity=Tongue.UM,
                evo_stage=EvoStage.ROOKIE,
                stats=Stats(
                    hp=80,
                    max_hp=80,
                    mp=34,
                    max_mp=34,
                    attack=11,
                    defense=8,
                    speed=10,
                    wisdom=8,
                ),
                spells=[
                    Spell("Static Gnash", Tongue.UM, 14, 8, "A crackling bite of shadow"),
                ],
                is_enemy=True,
            )
            enemy2 = Character(
                name="Shard Crab",
                title="Beach Hazard",
                tongue_affinity=Tongue.DR,
                evo_stage=EvoStage.FRESH,
                stats=Stats(
                    hp=45,
                    max_hp=45,
                    mp=18,
                    max_mp=18,
                    attack=9,
                    defense=9,
                    speed=5,
                    wisdom=4,
                ),
                spells=[
                    Spell("Shell Crack", Tongue.DR, 12, 7, "Break stance with heavy shell impact"),
                ],
                is_enemy=True,
            )
            self.battle.start_battle(
                party=[c for c in self.party if c.stats.hp > 0],
                enemies=[enemy1, enemy2],
            )
            self.battle.battle_log.append("PollyPad: Multi-target threat. Focus the fast unit first.")
            self.partner_bond = min(1.0, self.partner_bond + 0.02)

        self.particles.emit(GAME_W // 2, GAME_H // 2, (255, 80, 80), count=30, spread=4.8)

    def _start_test_battle(self) -> None:
        """Start a test battle encounter."""
        self._story_battle_active = False
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
                self._load_scene(self._pending_scene)

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

        # Autonomous companion side-actions (free-will lite).
        if self.game_phase != "title" and not self.workshop_open:
            self.autonomy_timer += dt
            if self.autonomy_timer >= self.autonomy_interval:
                self.autonomy_timer = 0.0
                self._run_autonomy_tick()

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
        elif self.workshop_open:
            self._draw_workshop_screen()
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
        """Draw a clean console-style frame around the game area."""
        # Outer frame — dark, sleek
        bezel_rect = pygame.Rect(4, 4, 656, 712)
        draw_rounded_rect(self.screen, BEZEL_COLOR, bezel_rect, radius=12)

        # Subtle inner border
        inner = pygame.Rect(14, 14, 636, 692)
        pygame.draw.rect(self.screen, BEZEL_HIGHLIGHT, inner, width=1, border_radius=8)

        # Inner screen border (where the game surface sits)
        screen_border = pygame.Rect(16, 44, 648, 490)
        pygame.draw.rect(self.screen, (8, 8, 14), screen_border, border_radius=4)
        pygame.draw.rect(self.screen, (50, 55, 75), screen_border, width=1, border_radius=4)

        # Title bar
        title_font = self.fonts.get(14, bold=True)
        title_surf = title_font.render("AETHERMOOR", True, GOLD)
        title_x = 20 + (GAME_W - title_surf.get_width()) // 2
        self.screen.blit(title_surf, (title_x, 22))

        ver_font = self.fonts.get(10)
        ver_surf = ver_font.render("SCBE v3.0", True, (60, 65, 85))
        self.screen.blit(ver_surf, (22, 26))

        # Tongue LED strip below screen — horizontal bar with glowing dots
        led_y = 542
        led_start_x = 20 + (GAME_W - 6 * 80) // 2
        led_font = self.fonts.get(10)
        tongue_codes = ["KO", "AV", "RU", "CA", "UM", "DR"]

        # Subtle LED bar background
        bar_rect = pygame.Rect(led_start_x - 16, led_y - 12, 6 * 80 + 32, 28)
        draw_rounded_rect(self.screen, (18, 18, 28), bar_rect, radius=6)

        for i, code in enumerate(tongue_codes):
            cx = led_start_x + i * 80 + 28
            color = TONGUE_COLORS[code]
            active = any(
                l in self.scene.active_layers
                for l in range(1, 15)
                if self._tongue_for_layer(l) == code
            )
            if active:
                pulse = 0.6 + 0.4 * math.sin(time.time() * 5 + i * 1.1)
                glow_color = lerp_color((30, 30, 40), color, pulse)
                # Outer glow
                glow_surf = pygame.Surface((28, 28), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*color, 50), (14, 14), 14)
                self.screen.blit(glow_surf, (cx - 14, led_y - 14))
                pygame.draw.circle(self.screen, glow_color, (cx, led_y), 7)
                pygame.draw.circle(self.screen, color, (cx, led_y), 4)
            else:
                dim = (color[0] // 5, color[1] // 5, color[2] // 5)
                pygame.draw.circle(self.screen, dim, (cx, led_y), 5)
                pygame.draw.circle(self.screen, (30, 30, 42), (cx, led_y), 5, 1)

            lbl = led_font.render(code, True, color if active else (60, 60, 80))
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, led_y + 12))

        # Bottom info bar — controls and session info
        info_y = 575
        info_font = self.fonts.get(11)
        controls = "WASD/Arrows: Move  |  Enter: Select  |  Tab: Detail  |  Esc: Pause  |  B: Battle"
        cs = info_font.render(controls, True, (55, 58, 78))
        self.screen.blit(cs, (20 + (GAME_W - cs.get_width()) // 2, info_y))

        extras = "F6: Script Lab  |  F7: Free Will  |  F8: AI Pilot"
        es = self.fonts.get(10).render(extras, True, (45, 48, 68))
        self.screen.blit(es, (20 + (GAME_W - es.get_width()) // 2, info_y + 18))

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
        loc_surf = loc_font.render(
            f"{scene_name} | Gen {self.generation} Age {self.age_years} | {self.player_class}/{self.partner_name}",
            True,
            DIM_TEXT,
        )
        self.game_surface.blit(loc_surf, (10, 8))
        self._draw_status_popup()

        # Dialogue box
        if not self.scene.scene_finished:
            self._draw_dialogue_box()

        # Choices overlay
        if self.scene.showing_choices:
            self._draw_choices()

    def _draw_workshop_screen(self) -> None:
        """Draw nested in-game ChoiceScript workshop overlay."""
        self.game_surface.fill((12, 16, 34))

        # Cyber grid background for Digimon-like vibe.
        for x in range(0, GAME_W, 24):
            pygame.draw.line(self.game_surface, (26, 40, 76), (x, 0), (x, GAME_H), 1)
        for y in range(0, GAME_H, 20):
            pygame.draw.line(self.game_surface, (24, 36, 70), (0, y), (GAME_W, y), 1)

        title = self.fonts.get(16, bold=True).render("CHOICESCRIPT WORKSHOP (NESTED)", True, GOLD)
        self.game_surface.blit(title, (12, 10))

        controls = self.fonts.get(10).render("UP/DOWN + ENTER, F6/ESC to close", True, DIM_TEXT)
        self.game_surface.blit(controls, (12, 30))

        project = self._workshop_active_project()
        if project:
            meta = (
                f"{project['title']}  |  Reads:{project['reads']}  "
                f"Playtests:{project['playtests']}  Exports:{project['exports']}"
            )
        else:
            meta = "No active script project."
        meta_surf = self.fonts.get(10).render(meta, True, TEXT_COLOR)
        self.game_surface.blit(meta_surf, (12, 50))

        menu = [
            "Create New Book Template",
            "Add Branch From Current Scene",
            "AI Read Current Book",
            "Playtest Nested Book",
            "Export Book to Files",
        ]
        menu_font = self.fonts.get(12)
        for i, item in enumerate(menu):
            is_sel = i == self.workshop_cursor
            color = CHOICE_HIGHLIGHT if is_sel else (190, 196, 220)
            prefix = "> " if is_sel else "  "
            surf = menu_font.render(prefix + item, True, color)
            self.game_surface.blit(surf, (18, 84 + i * 24))

        # Script preview window.
        preview_rect = pygame.Rect(12, 216, GAME_W - 24, GAME_H - 246)
        pygame.draw.rect(self.game_surface, (8, 12, 24), preview_rect, border_radius=4)
        pygame.draw.rect(self.game_surface, (86, 102, 150), preview_rect, 1, border_radius=4)

        preview_font = self.fonts.get(10)
        if project:
            lines = project["script"][-13:]
            py = preview_rect.y + 8
            for line in lines:
                txt = preview_font.render(line[:92], True, (178, 210, 245))
                self.game_surface.blit(txt, (preview_rect.x + 8, py))
                py += 14
        else:
            txt = preview_font.render("Create a project to start writing.", True, (178, 210, 245))
            self.game_surface.blit(txt, (preview_rect.x + 8, preview_rect.y + 8))

        message = self.fonts.get(10).render(self.workshop_message[:95], True, (140, 230, 180))
        self.game_surface.blit(message, (12, GAME_H - 18))

    def _draw_scene_background(self) -> None:
        """Draw scene-specific background elements with GBA-era depth."""
        sid = self.scene.current_scene_id
        t = time.time()

        if sid.startswith("earth"):
            bg = BG_COLORS["earth"]
            # Sky gradient (top third)
            is_night = "night" in sid or "evening" in sid
            sky_top = (8, 10, 28) if is_night else (48, 72, 120)
            sky_bot = (18, 24, 50) if is_night else (28, 42, 78)
            for row in range(180):
                ratio = row / 180.0
                c = lerp_color(sky_top, sky_bot, ratio)
                pygame.draw.line(self.game_surface, c, (0, row), (GAME_W, row))

            # Stars (night/evening only)
            if is_night:
                for i in range(25):
                    sx = random.Random(i * 37 + 1).randint(0, GAME_W - 1)
                    sy = random.Random(i * 71 + 2).randint(0, 160)
                    twinkle = 0.4 + 0.6 * math.sin(t * 1.8 + i * 0.9)
                    b = int(180 * twinkle)
                    if b > 20:
                        self.game_surface.set_at((sx, sy), (b, b, min(255, b + 50)))

            # Distant mountains/hills
            for hill_pass in range(3):
                points = [(0, 200 - hill_pass * 15)]
                depth = 0.3 + hill_pass * 0.2
                hill_color = lerp_color(bg, sky_bot, depth)
                for px in range(0, GAME_W + 40, 40):
                    h = random.Random(px * 7 + hill_pass * 99).randint(20, 50)
                    points.append((px, 200 - hill_pass * 15 - h))
                points.append((GAME_W, 200 - hill_pass * 15))
                points.append((GAME_W, 200))
                points.append((0, 200))
                pygame.draw.polygon(self.game_surface, hill_color, points)

            # Ground area
            ground_top = (38, 45, 58) if is_night else (44, 56, 42)
            ground_bot = (22, 28, 38) if is_night else (28, 36, 28)
            for row in range(200, GAME_H):
                ratio = (row - 200) / max(1, GAME_H - 200)
                c = lerp_color(ground_top, ground_bot, ratio)
                pygame.draw.line(self.game_surface, c, (0, row), (GAME_W, row))

            # Grass tufts on ground line
            for gx in range(0, GAME_W, 8):
                gh = random.Random(gx + 3).randint(3, 10)
                gc = lerp_color((40, 80, 45), (65, 110, 55), random.Random(gx * 5).random())
                if is_night:
                    gc = lerp_color(gc, (20, 30, 40), 0.6)
                lean = random.Random(gx * 3).randint(-2, 2)
                pygame.draw.line(self.game_surface, gc, (gx, 200), (gx + lean, 200 - gh), 1)

            # Scene-specific details
            if "morning" in sid:
                # Cozy house window with warm glow
                pygame.draw.rect(self.game_surface, (50, 44, 36), (420, 140, 170, 120))
                pygame.draw.rect(self.game_surface, (70, 60, 48), (420, 140, 170, 4))
                pygame.draw.rect(self.game_surface, (65, 75, 110), (440, 160, 60, 50))
                pygame.draw.rect(self.game_surface, (80, 90, 120), (440, 160, 60, 50), 1)
                pygame.draw.line(self.game_surface, (80, 90, 120), (470, 160), (470, 210), 1)
                pygame.draw.line(self.game_surface, (80, 90, 120), (440, 185), (500, 185), 1)
                # Warm light from window
                for gy in range(160, 210):
                    alpha = max(0, 40 - abs(gy - 185))
                    if alpha > 5:
                        pygame.draw.line(self.game_surface, (alpha + 40, alpha + 30, alpha // 2),
                                        (442, gy), (498, gy))
            elif "work" in sid:
                # Path through greenery
                for px in range(0, GAME_W, 3):
                    py = 210 + int(math.sin(px * 0.02) * 8)
                    pygame.draw.circle(self.game_surface, (52, 44, 36), (px, py), 4)

            elif "evening" in sid:
                # Beach dunes with orange horizon glow
                for row in range(170, 200):
                    ratio = (row - 170) / 30.0
                    c = lerp_color((60, 40, 30), (30, 24, 40), ratio)
                    pygame.draw.line(self.game_surface, c, (0, row), (GAME_W, row))
                # Ocean shimmer
                for row in range(130, 170):
                    shimmer = int(8 * math.sin(t * 2 + row * 0.3))
                    c = lerp_color((30, 50, 90), (20, 35, 70), (row - 130) / 40.0)
                    pygame.draw.line(self.game_surface, c, (shimmer, row), (GAME_W + shimmer, row))

            elif "night" in sid:
                # Portal glow at center
                portal_cx, portal_cy = GAME_W // 2, 160
                for ring in range(40, 0, -1):
                    alpha = max(0, int(80 - ring * 2))
                    tc_list = list(TONGUE_COLORS.values())
                    c = tc_list[ring % 6]
                    glow = lerp_color((12, 8, 36), c, alpha / 120.0)
                    r_phase = ring + int(math.sin(t * 3 + ring * 0.2) * 3)
                    pygame.draw.circle(self.game_surface, glow, (portal_cx, portal_cy), r_phase)

        elif sid == "transit":
            # Full-screen dimensional vortex with depth
            cx, cy = GAME_W // 2, GAME_H // 2
            # Radial gradient background
            for ring in range(min(GAME_W, GAME_H) // 2, 0, -4):
                ratio = ring / (min(GAME_W, GAME_H) // 2)
                c = lerp_color((40, 20, 80), (8, 4, 20), ratio)
                pygame.draw.circle(self.game_surface, c, (cx, cy), ring)

            # Spiral streams
            tc_list = list(TONGUE_COLORS.values())
            for i in range(200):
                angle = t * 1.2 + i * 0.12
                r = 8 + i * 1.8
                px = int(cx + math.cos(angle) * r)
                py = int(cy + math.sin(angle) * r * 0.55)
                color = tc_list[i % 6]
                brightness = max(0.1, 1.0 - i / 200.0)
                dim = lerp_color((12, 8, 36), color, brightness)
                if 0 <= px < GAME_W and 0 <= py < GAME_H:
                    size = max(1, int(4 * brightness))
                    pygame.draw.circle(self.game_surface, dim, (px, py), size)

            # Layer names spiraling
            small_font = self.fonts.get(11)
            for layer_num, layer_name, layer_color in SCBE_LAYERS:
                angle = t * 0.6 + layer_num * (math.pi * 2 / 14)
                r = 80 + layer_num * 10
                px = int(cx + math.cos(angle) * r)
                py = int(cy + math.sin(angle) * r * 0.45)
                if 10 <= px < GAME_W - 60 and 10 <= py < GAME_H - 20:
                    lbl = small_font.render(f"L{layer_num} {layer_name}", True, layer_color)
                    self.game_surface.blit(lbl, (px, py))

        elif sid in ("aethermoor_arrival", "academy_entrance", "first_lesson"):
            bg = BG_COLORS["aethermoor"]
            # Deep sky gradient
            for row in range(GAME_H):
                ratio = row / GAME_H
                c = lerp_color((12, 8, 42), (38, 28, 80), ratio * 0.6)
                pygame.draw.line(self.game_surface, c, (0, row), (GAME_W, row))

            # Stars
            for sx, sy, brightness in self.bg_stars:
                twinkle = 0.4 + 0.6 * math.sin(t * 1.2 + sx * 0.04 + sy * 0.03)
                b = int(brightness * 0.5 * twinkle)
                if b > 15:
                    x_pos = sx % GAME_W
                    y_pos = sy % (GAME_H - 140)
                    try:
                        self.game_surface.set_at((x_pos, y_pos), (b, b, min(255, b + 60)))
                        if b > 100:
                            self.game_surface.set_at((x_pos + 1, y_pos), (b // 2, b // 2, b // 2 + 30))
                    except IndexError:
                        pass

            # Floating islands with more depth
            for i in range(4):
                ix = 60 + i * 160
                bob = int(math.sin(t * 0.4 + i * 1.3) * 6)
                iy = 60 + i * 25 + bob
                iw = 100 + i * 25
                ih = 22 + i * 4
                # Shadow underneath
                shadow_c = (20, 14, 48)
                pygame.draw.ellipse(self.game_surface, shadow_c,
                                    (ix - iw // 2, iy + ih + 6, iw, ih // 2))
                # Island body
                island_dark = lerp_color((40, 32, 72), (60, 48, 100), i / 4.0)
                island_light = lerp_color((70, 56, 120), (100, 80, 160), i / 4.0)
                pygame.draw.ellipse(self.game_surface, island_dark,
                                    (ix - iw // 2, iy, iw, ih))
                pygame.draw.ellipse(self.game_surface, island_light,
                                    (ix - iw // 2 + 8, iy - 4, iw - 16, ih // 2))
                # Tiny trees/crystals on top
                for ci in range(3):
                    cx_tree = ix - iw // 4 + ci * (iw // 3)
                    cy_tree = iy - 4
                    tree_h = random.Random(i * 10 + ci).randint(6, 14)
                    tree_c = lerp_color((50, 90, 60), (80, 140, 100), random.Random(i + ci * 7).random())
                    pygame.draw.line(self.game_surface, tree_c, (cx_tree, cy_tree), (cx_tree, cy_tree - tree_h), 2)

            # Ground platform with gradient
            for row in range(340, GAME_H):
                ratio = (row - 340) / max(1, GAME_H - 340)
                c = lerp_color((48, 36, 88), (28, 20, 56), ratio)
                pygame.draw.line(self.game_surface, c, (0, row), (GAME_W, row))

            # Crystal grass
            for gx in range(0, GAME_W, 10):
                gh = random.Random(gx + 1).randint(4, 14)
                gc = lerp_color((60, 80, 140), (120, 140, 200), random.Random(gx * 7).random())
                lean = random.Random(gx * 3).randint(-3, 3)
                pygame.draw.line(self.game_surface, gc, (gx, 340), (gx + lean, 340 - gh), 1)

            # Academy towers
            if sid in ("academy_entrance", "first_lesson"):
                tower_colors = list(TONGUE_COLORS.values())
                for i in range(6):
                    tx = 60 + i * 95
                    tw = 36
                    th = 90 + i * 12
                    ty = 170 - th
                    tc = tower_colors[i]
                    dim_tc = lerp_color((24, 16, 42), tc, 0.35)
                    # Tower body with slight taper
                    points = [(tx, ty + th), (tx + tw, ty + th),
                              (tx + tw - 3, ty + 8), (tx + 3, ty + 8)]
                    pygame.draw.polygon(self.game_surface, dim_tc, points)
                    # Pointed roof
                    pygame.draw.polygon(self.game_surface, tc,
                                        [(tx + 2, ty + 8), (tx + tw - 2, ty + 8),
                                         (tx + tw // 2, ty - 18)])
                    # Windows with glow
                    for wy in range(2):
                        glow_pulse = 0.4 + 0.3 * math.sin(t * 1.8 + i * 0.8 + wy)
                        glow_c = lerp_color((30, 20, 50), tc, glow_pulse)
                        pygame.draw.rect(self.game_surface, glow_c,
                                         (tx + tw // 2 - 4, ty + 20 + wy * 30, 8, 12))

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

    def _draw_status_popup(self) -> None:
        """Draw a compact class/reputation/bond popup on scene screens."""
        panel_w, panel_h = 258, 122
        x = GAME_W - panel_w - 10
        y = 10

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((10, 10, 20, 208))
        self.game_surface.blit(panel, (x, y))
        pygame.draw.rect(self.game_surface, (98, 98, 130), (x, y, panel_w, panel_h), 1, border_radius=6)

        header = self.fonts.get(10, bold=True).render("STATUS", True, GOLD)
        self.game_surface.blit(header, (x + 8, y + 6))

        line_font = self.fonts.get(10)
        rep_text = f"Rep: {self._reputation_label()} ({self.reputation_points:+d})"
        bits_text = f"Bits: {self.inventory['Gold']}"
        class_text = f"Class: {self.player_class}"
        gen_text = f"Gen {self.generation}  Age {self.age_years}  Stage {self._current_grade_band()}"
        zone_text = f"Zone: {self._current_zone()}"
        self.game_surface.blit(line_font.render(class_text, True, TEXT_COLOR), (x + 8, y + 22))
        self.game_surface.blit(line_font.render(gen_text, True, (180, 200, 220)), (x + 8, y + 36))
        self.game_surface.blit(line_font.render(rep_text, True, (180, 200, 220)), (x + 8, y + 50))
        self.game_surface.blit(line_font.render(bits_text, True, (180, 200, 220)), (x + 8, y + 64))
        self.game_surface.blit(line_font.render(zone_text[:38], True, (160, 194, 226)), (x + 8, y + 78))
        mat_text = f"Mats {self._material_summary()}"
        self.game_surface.blit(self.fonts.get(9).render(mat_text, True, DIM_TEXT), (x + 8, y + 92))

        bond_val = max(0.0, min(1.0, self.partner_bond))
        bond_color = lerp_color((80, 90, 110), (120, 250, 170), bond_val)
        draw_bar(self.game_surface, x + 154, y + 104, 92, 9, bond_val, bond_color)
        bond_lbl = self.fonts.get(9).render(f"Bond: {self._bond_label()}", True, DIM_TEXT)
        self.game_surface.blit(bond_lbl, (x + 154, y + 90))

    def _draw_dialogue_box(self) -> None:
        """Draw a polished RPG dialogue box at the bottom of the game screen."""
        line = self.scene.get_current_line()
        if line is None:
            return

        speaker, text = line

        box_h = 130
        box_y = GAME_H - box_h - 8
        box_x = 8
        box_w = GAME_W - 16

        # Dialogue box with double border (GBA RPG style)
        dialogue_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        dialogue_surf.fill(DIALOGUE_BG)
        self.game_surface.blit(dialogue_surf, (box_x, box_y))

        # Outer border
        pygame.draw.rect(self.game_surface, (90, 90, 130),
                         (box_x, box_y, box_w, box_h), 2, border_radius=6)
        # Inner border highlight
        pygame.draw.rect(self.game_surface, (50, 50, 72),
                         (box_x + 3, box_y + 3, box_w - 6, box_h - 6), 1, border_radius=4)

        # Speaker name tag (raised above the box like classic RPGs)
        if speaker:
            name_font = self.fonts.get(14, bold=True)
            name_color = TEXT_COLOR
            for c in self.party:
                if c.name.upper().startswith(speaker.upper()):
                    name_color = TONGUE_COLORS.get(c.tongue_affinity.value, TEXT_COLOR)
                    break
            if speaker == "POLLY":
                name_color = TONGUE_COLORS["KO"]
            elif speaker == "CLAY":
                name_color = TONGUE_COLORS["RU"]
            elif speaker == "MARCUS CHEN":
                name_color = (180, 140, 220)
            elif speaker == "VOICE":
                name_color = GOLD
            elif speaker == "SYSTEM":
                name_color = (100, 180, 220)
            elif speaker in ("TRAVELER", "FISHER", "COLLEAGUE", "MOM", "POLLYPAD"):
                name_color = (160, 160, 190)

            # Name plate background
            name_surf = name_font.render(speaker, True, name_color)
            plate_w = name_surf.get_width() + 16
            plate_rect = pygame.Rect(box_x + 12, box_y - 10, plate_w, 22)
            plate_bg = pygame.Surface((plate_w, 22), pygame.SRCALPHA)
            plate_bg.fill((12, 12, 28, 240))
            self.game_surface.blit(plate_bg, (plate_rect.x, plate_rect.y))
            pygame.draw.rect(self.game_surface, name_color, plate_rect, 1, border_radius=3)
            self.game_surface.blit(name_surf, (box_x + 20, box_y - 8))
            text_y = box_y + 18
        else:
            text_y = box_y + 14

        # Dialogue text
        text_font = self.fonts.get(14)
        text_rect = pygame.Rect(box_x + 16, text_y, box_w - 36, box_h - (text_y - box_y) - 12)
        draw_text_wrapped(self.game_surface, text, text_font, TEXT_COLOR, text_rect)

        # Blinking advance triangle (bottom right)
        if self.text_cursor_visible:
            tri_x = box_x + box_w - 24
            tri_y = box_y + box_h - 18
            pygame.draw.polygon(self.game_surface, CHOICE_HIGHLIGHT,
                                [(tri_x, tri_y), (tri_x + 10, tri_y + 5), (tri_x, tri_y + 10)])

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

        # Digimon-like partner link panel
        hud = pygame.Surface((220, 46), pygame.SRCALPHA)
        hud.fill((14, 14, 24, 210))
        self.game_surface.blit(hud, (14, 12))
        pygame.draw.rect(self.game_surface, (88, 88, 120), (14, 12, 220, 46), 1, border_radius=4)
        hud_font = self.fonts.get(10)
        self.game_surface.blit(
            hud_font.render(f"Class: {self.player_class}  Partner: {self.partner_name}", True, TEXT_COLOR),
            (22, 18),
        )
        draw_bar(
            self.game_surface,
            22,
            34,
            176,
            8,
            self.partner_bond,
            lerp_color((70, 70, 90), (120, 240, 165), self.partner_bond),
        )
        self.game_surface.blit(
            self.fonts.get(9).render(self._bond_label(), True, DIM_TEXT),
            (202, 33),
        )

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

        # ---- Run Identity ----
        id_font = self.fonts.get(10)
        self.screen.blit(id_font.render(f"Class: {self.player_class}", True, TEXT_COLOR), (DASH_X + 12, y))
        y += 14
        self.screen.blit(
            id_font.render(
                f"Gen {self.generation}  Age {self.age_years}  LifeCap {self.lifespan_years}",
                True,
                DIM_TEXT,
            ),
            (DASH_X + 12, y),
        )
        y += 14
        self.screen.blit(
            id_font.render(f"Partner: {self.partner_name} ({self._bond_label()})", True, TEXT_COLOR),
            (DASH_X + 12, y),
        )
        y += 14
        self.screen.blit(
            id_font.render(
                f"Reputation: {self._reputation_label()} ({self.reputation_points:+d})", True, DIM_TEXT
            ),
            (DASH_X + 12, y),
        )
        y += 14
        self.screen.blit(
            id_font.render(f"Stage: {self._current_grade_band()}  Zone: {self._current_zone()[:16]}", True, DIM_TEXT),
            (DASH_X + 12, y),
        )
        y += 16
        draw_bar(
            self.screen,
            DASH_X + 12,
            y,
            140,
            8,
            self.partner_bond,
            lerp_color((70, 70, 90), (120, 240, 165), self.partner_bond),
        )
        y += 12
        self.screen.blit(id_font.render(f"Mats: {self._material_summary()}", True, DIM_TEXT), (DASH_X + 12, y))
        y += 14
        quest = self._active_band_quest()
        prog = self._active_band_progress()
        qline = (
            f"Quest: {quest['title'][:16]} "
            f"E{prog['explore']}/{quest['requirements']['explore']} "
            f"H{prog['help']}/{quest['requirements']['help']} "
            f"C{prog['craft']}/{quest['requirements']['craft']}"
        )
        self.screen.blit(self.fonts.get(9).render(qline, True, (150, 192, 225)), (DASH_X + 12, y))
        y += 16

        sk = self.nature_skills
        skills_line = f"Skills Fg{sk['foraging']} Wd{sk['woodcraft']} Ec{sk['ecology']} In{sk['inscription']}"
        self.screen.blit(self.fonts.get(9).render(skills_line, True, (170, 214, 186)), (DASH_X + 12, y))
        y += 12

        auto_state = "ON" if self.autonomy_enabled else "OFF"
        self.screen.blit(
            self.fonts.get(9).render(f"Companion Free-Will: {auto_state}", True, (170, 214, 186)),
            (DASH_X + 12, y),
        )
        y += 12
        if self.autonomy_log:
            last_auto = self.autonomy_log[-1][:34]
            self.screen.blit(self.fonts.get(9).render(f"Last Auto: {last_auto}", True, DIM_TEXT), (DASH_X + 12, y))
            y += 12

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
# AI Autopilot — Virtual Keyboard for Self-Play
# ---------------------------------------------------------------------------
class AIPilot:
    """AI autopilot that plays the game by injecting pygame key events.

    Maps game telemetry to decisions:
    - In dialogue: advance (Enter)
    - In choices: pick based on tongue proficiency bias + exploration
    - In battle: weighted action selection
    - Generates training data as a side effect

    Toggle with F8 in-game.
    """

    def __init__(self, game: AethermoorGame):
        self.game = game
        self.enabled = False
        self.action_cooldown = 0.0
        self.min_delay = 0.6      # Seconds between actions (readable pace)
        self.battle_delay = 0.4   # Faster in battle
        self.total_actions = 0
        self.strategy = "balanced"  # balanced | aggressive | cautious

    def toggle(self) -> str:
        """Toggle autopilot on/off."""
        self.enabled = not self.enabled
        return "ON" if self.enabled else "OFF"

    def tick(self, dt: float) -> None:
        """Called every frame. Decides whether to inject an action."""
        if not self.enabled:
            return

        self.action_cooldown -= dt
        if self.action_cooldown > 0:
            return

        key = self._decide_action()
        if key is not None:
            event = pygame.event.Event(pygame.KEYDOWN, key=key)
            pygame.event.post(event)
            self.total_actions += 1
            delay = self.battle_delay if self.game.battle.active else self.min_delay
            self.action_cooldown = delay

    def _decide_action(self) -> Optional[int]:
        """Pick the next key to press based on game state."""
        g = self.game

        # Title screen — just press Enter
        if g.game_phase == "title":
            return pygame.K_RETURN

        # Paused — resume
        if g.paused:
            return pygame.K_RETURN

        # Battle
        if g.battle.active:
            return self._decide_battle_action()

        # Transitioning — wait
        if g.transitioning:
            return None

        # Workshop open — close it
        if g.workshop_open:
            return pygame.K_ESCAPE

        # Choices showing — pick one
        if g.scene.showing_choices:
            return self._decide_choice()

        # Dialogue — advance
        return pygame.K_RETURN

    def _decide_choice(self) -> int:
        """Pick a choice based on tongue proficiency and exploration strategy."""
        g = self.game
        choices = g.scene.choices
        if not choices:
            return pygame.K_RETURN

        # Score each choice
        scores: List[float] = []
        for i, (label, action, tongue, layers) in enumerate(choices):
            score = 1.0

            # Bias toward tongues we're good at (exploitation)
            if g.party:
                prof = g.party[0].stats.tongue_prof.get(tongue, 0.0)
                score += prof * 0.5

            # Exploration bonus for varied tongues
            score += random.random() * 0.4

            # Strategy modifiers
            if self.strategy == "aggressive":
                if "fight" in action or "rush" in action:
                    score += 0.6
            elif self.strategy == "cautious":
                if "help" in action or "calm" in action or "promise" in action:
                    score += 0.5

            # Favor class-defining choices (earth_night)
            if action.startswith("class_") and tongue in ("CA", "DR", "KO"):
                score += 0.3

            scores.append(score)

        # Weighted random selection
        total = sum(scores)
        if total <= 0:
            best = 0
        else:
            r = random.random() * total
            cumulative = 0.0
            best = 0
            for i, s in enumerate(scores):
                cumulative += s
                if r <= cumulative:
                    best = i
                    break

        # Navigate to selected choice then confirm
        g.scene.selected_choice = best
        return pygame.K_RETURN

    def _decide_battle_action(self) -> Optional[int]:
        """Pick a battle action."""
        b = self.game.battle

        # Victory/defeat — continue
        if b.victory or b.defeat:
            return pygame.K_RETURN

        # Enemy turn — wait
        if not b.is_player_turn:
            return None

        # Target selection mode — pick first alive enemy
        if b.selecting_target:
            return pygame.K_RETURN

        # Pick action: prefer spells if MP available, otherwise attack
        actions = b.get_actions()
        if not actions:
            return None

        if len(actions) > 2 and random.random() < 0.5:
            # Use a spell
            spell_idx = random.randint(1, len(actions) - 2)
            b.selected_action = spell_idx
        else:
            b.selected_action = 0  # Attack

        return pygame.K_RETURN


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
    print("    Tab                -  Dashboard detail")
    print("    Esc                -  Pause menu")
    print("    B                  -  Test battle")
    print("    F6                 -  Script Lab")
    print("    F7                 -  Companion free-will")
    print("    F8                 -  AI Autopilot")
    print()

    ai_mode = "--ai" in sys.argv or "--autopilot" in sys.argv
    game = AethermoorGame()
    pilot = AIPilot(game)

    if ai_mode:
        pilot.enabled = True
        print("  [AI AUTOPILOT ENABLED]")
        print()

    # Patch the game to know about the pilot
    _original_update = game._update
    _original_handle_key = game._handle_key

    def _patched_update(dt: float) -> None:
        pilot.tick(dt)
        _original_update(dt)

    def _patched_handle_key(key: int) -> None:
        if key == pygame.K_F8:
            state = pilot.toggle()
            game.workshop_message = f"AI Autopilot: {state} ({pilot.total_actions} actions)"
            return
        _original_handle_key(key)

    game._update = _patched_update
    game._handle_key = _patched_handle_key
    game.run()

    print(f"\n  Session complete. AI took {pilot.total_actions} actions.")
    print("  Aethermoor awaits your return.\n")


if __name__ == "__main__":
    main()
