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
  P                  - Open Poly Pad (phone / in-game PC)
  I                  - Open CodeLab IDE when at a terminal
  L                  - Open lore library when at a terminal
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
    Stats,
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
# Import new Phase 1-5 modules
# ---------------------------------------------------------------------------
from n8n_bridge import (
    GameEventBus, GameEventType, GameAction, GameActionType,
    set_shared_bus, create_bus_from_env, start_inbound_server,
)
from overworld import OverworldManager
from tilemap import TileType, TILE_SIZE
from player import Direction
from dungeon import TowerManager, DungeonFloor, generate_floor_enemies, generate_boss
from pivot_knowledge import (
    PivotKnowledge, SacredLanguages, TrainingDataGenerator,
    build_npc_knowledge,
)
from npc_brain import create_npc_brain, NPCBrain
from hf_trainer import RealTimeHFTrainer, TrainingEvent, load_dotenv
from headless import HeadlessDisplay, detect_environment, RuntimeEnv

# Load .env for HF_TOKEN / GOOGLE_AI_KEY
load_dotenv()

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

POLYPAD_APPS: List[str] = ["Home", "Contacts", "Messages", "Missions", "PC Box", "IDE"]

IDE_TERMINALS: Dict[str, List[Tuple[int, int, str]]] = {
    # Tile coordinates where Enter can open CodeLab directly from overworld.
    "guild_hub": [(20, 7, "Guild Hall Terminal")],
    "avalon_academy": [(15, 12, "Academy Terminal")],
    "spiral_tower_entrance": [(10, 8, "Tower Ops Console")],
}

IDE_TICKETS: List[Dict[str, Any]] = [
    {
        "id": "null_guard",
        "title": "Route Parser Null Guard",
        "brief": "Navigator crashes when waypoint metadata is missing during fast travel.",
        "tongue": "RU",
        "reward_gold": 40,
        "risk_penalty": 1,
        "actions": [
            {
                "label": "Add Guard Clause",
                "success": True,
                "outcome": "Parser stabilized. Missing waypoints are skipped with a warning.",
            },
            {
                "label": "Force Cast Waypoint",
                "success": False,
                "outcome": "Runtime panic. Route stack corrupts after two transitions.",
            },
            {
                "label": "Retry Until It Works",
                "success": False,
                "outcome": "Loop spikes CPU usage and blocks mission updates.",
            },
            {
                "label": "Write Regression Test First",
                "success": True,
                "outcome": "Test reproduces crash and validates the guard-clause fix.",
            },
        ],
    },
    {
        "id": "race_lock",
        "title": "Battle Event Race Condition",
        "brief": "Battle result and rewards fire twice when network latency is high.",
        "tongue": "KO",
        "reward_gold": 50,
        "risk_penalty": 1,
        "actions": [
            {
                "label": "Add Event Lock",
                "success": True,
                "outcome": "Single-writer lock prevents duplicate reward commits.",
            },
            {
                "label": "Increase Tick Rate",
                "success": False,
                "outcome": "Higher tick rate worsens desync and packet overlap.",
            },
            {
                "label": "Queue + Deduplicate IDs",
                "success": True,
                "outcome": "Event queue now ignores repeated battle IDs safely.",
            },
            {
                "label": "Ignore for Demo",
                "success": False,
                "outcome": "Players duplicate loot and progression stats drift.",
            },
        ],
    },
    {
        "id": "save_schema",
        "title": "Save Schema Migration",
        "brief": "Older save files fail because new fields are missing in profile data.",
        "tongue": "DR",
        "reward_gold": 45,
        "risk_penalty": 1,
        "actions": [
            {
                "label": "Add Default Migration Map",
                "success": True,
                "outcome": "Legacy saves load with stable defaults and version bump.",
            },
            {
                "label": "Delete Legacy Saves",
                "success": False,
                "outcome": "Player trust drops after data loss complaints.",
            },
            {
                "label": "Ship Hotfix Without Tests",
                "success": False,
                "outcome": "Migration passes locally but breaks cloud backup sync.",
            },
            {
                "label": "Add Compatibility Validator",
                "success": True,
                "outcome": "Validator blocks malformed saves before write time.",
            },
        ],
    },
    {
        "id": "shader_budget",
        "title": "Sapphire Palette Budget",
        "brief": "New effects reduce readability; keep Ruby/Sapphire clarity with better feel.",
        "tongue": "CA",
        "reward_gold": 35,
        "risk_penalty": 1,
        "actions": [
            {
                "label": "Tone-map UI Contrast",
                "success": True,
                "outcome": "HUD readability returns while preserving richer color depth.",
            },
            {
                "label": "Add More Bloom",
                "success": False,
                "outcome": "Bloom washes text edges and weakens battle readability.",
            },
            {
                "label": "Split FX into Mini-game Scenes",
                "success": True,
                "outcome": "Core loop stays clean; heavy FX run only inside mini-games.",
            },
            {
                "label": "Drop Back to Flat Colors",
                "success": False,
                "outcome": "Visual quality regresses below target baseline.",
            },
        ],
    },
]

LORE_BOOKS: List[Dict[str, str]] = [
    {
        "id": "six_tongues_primer",
        "title": "Six Tongues Integration Primer",
        "source": "Obsidian: Context Room/99 - Isekai Six Tongues Integration.md",
        "body": (
            "Dialogue layer by emotional intent: KO for bonding and oaths, AV for diplomacy "
            "and bridges, RU for legacy and archives, CA for invention and workshop scenes, "
            "UM for grief and threshold moments, DR for forge and defense. "
            "Scene cards should track Tongue used, emotional signature target, society present, "
            "song anchor, and canon citation. Treat derived affect as proposed until canon lock."
        ),
    },
    {
        "id": "shared_state_manual",
        "title": "Shared State Field Manual",
        "source": "Obsidian: AI Workspace/Context/Shared State.md",
        "body": (
            "SCBE runtime has 14 layers with governance outcomes ALLOW, DENY, or QUARANTINE. "
            "Game loop aligns to that model by recording choices, combat, and dialogue as "
            "training artifacts. Keep technical SCBE and story canon linked only through "
            "explicit source evidence."
        ),
    },
    {
        "id": "round_table_ops",
        "title": "Round Table Operations",
        "source": "Obsidian: AI Workspace/Round Table.md",
        "body": (
            "Agent workflow: read shared state, claim tasks, execute, write handoff, update status. "
            "Open task from coordination board: add Morrowind-style in-game books with lore lessons. "
            "Rule: coordinate, do not collide. Use explicit paths and preserve continuity."
        ),
    },
    {
        "id": "hybrid_patch_notes",
        "title": "Hybrid Patch Notes",
        "source": "Obsidian: Context Room/105 - Digimon Pokemon Hybrid Patch 2026-02-23.md",
        "body": (
            "Pokemon clarity plus Digimon identity progression: class loadouts, partner bond, "
            "reputation, branching story battles, and training payload upgrades. "
            "UI should surface class, partner, reputation, and bond without cluttering the core loop."
        ),
    },
]

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

    def __init__(self, headless: bool = False) -> None:
        # Headless display setup (must happen BEFORE pygame.init)
        self.headless_display: Optional[HeadlessDisplay] = None
        if headless:
            self.headless_display = HeadlessDisplay(
                width=GAME_W, height=GAME_H,
            )
            self.headless_display.start()

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

        # Phase 1-5 managers
        self.overworld = OverworldManager()
        self.tower = TowerManager()
        self.hf_trainer = RealTimeHFTrainer()
        self.dialogue_gen = TrainingDataGenerator()
        self.sacred_langs = SacredLanguages()
        self.npc_brains: Dict[str, NPCBrain] = {}
        self.npc_knowledge: Dict[str, PivotKnowledge] = {}

        # Dialogue state (Phase 3)
        self.dialogue_active: bool = False
        self.dialogue_npc_id: str = ""
        self.dialogue_response: str = ""
        self.dialogue_pivots: List[Tuple[str, str]] = []
        self.dialogue_pivot_cursor: int = 0
        self.dialogue_sacred_text: str = ""

        # Dungeon state (Phase 2)
        self.dungeon_active: bool = False
        self.dungeon_player_x: int = 1
        self.dungeon_player_y: int = 1
        self.dungeon_view_offset: Tuple[int, int] = (0, 0)

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
        # Poly Pad (cellphone / in-game PC) state.
        self.polypad_tab: int = 0
        self.polypad_cursor: int = 0
        self.polypad_return_phase: str = "overworld"
        self.polypad_contacts: List[Dict[str, Any]] = [
            {"name": "MOM", "status": "Home", "last_call": "Never"},
            {"name": "POLLY", "status": "On shoulder", "last_call": "Never"},
            {"name": "CLAY", "status": "Guild Hub", "last_call": "Never"},
            {"name": "MARCUS", "status": "Outer systems", "last_call": "Never"},
            {"name": "FLEET COMMS", "status": "Listening", "last_call": "Never"},
        ]
        self.polypad_messages: List[Dict[str, Any]] = [
            {
                "from": "SYSTEM",
                "subject": "Poly Pad Link",
                "body": "Pick up your Poly Pad to unlock calls, mission logs, and PC box ops.",
                "unread": True,
                "time": "Boot",
            },
            {
                "from": "POLLY",
                "subject": "Quick Tip",
                "body": "Core loop stays simple. Complex systems route through mini-game channels.",
                "unread": True,
                "time": "Boot",
            },
        ]
        self.polypad_call_log: List[str] = []
        self.polypad_missions: List[Dict[str, Any]] = [
            {
                "title": "Village Start",
                "desc": "Collect kit, talk to Mom, and head toward the shoreline.",
                "status": "active",
            },
            {
                "title": "Traveler Assist",
                "desc": "Help route the traveler and log goodwill for guild trust.",
                "status": "queued",
            },
            {
                "title": "Shoreline Threat",
                "desc": "Handle ripple-beast event. Battle or tame based on risk posture.",
                "status": "queued",
            },
        ]
        # CodeLab IDE state (in-game computer coding mini-game).
        self.ide_cursor: int = 0
        self.ide_ticket_index: int = 0
        self.ide_return_phase: str = "overworld"
        self.ide_resolved: int = 0
        self.ide_failures: int = 0
        self.ide_last_result: str = "No coding runs yet."
        self.ide_history: List[str] = []
        # In-game lore library (Morrowind-style readable books).
        self.library_index: int = 0
        self.library_scroll: int = 0
        self.library_return_phase: str = "ide"
        self.library_reads: int = 0
        self.library_read_books: Set[str] = set()
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

        # Initialize overworld + NPC brains
        self.overworld.initialize(self.cast["izack"], GAME_W, GAME_H)
        self._init_npc_systems()

        # Start HF trainer background thread
        self.hf_trainer.start()

        # Game screen surface (rendered separately)
        self.game_surface = pygame.Surface((GAME_W, GAME_H))

        # AetherNet bridge (n8n game event bus)
        self.n8n_bus = create_bus_from_env()
        if self.n8n_bus.enabled:
            self.n8n_bus.start()
        # Inbound HTTP server — n8n POSTs actions to localhost:9800/action
        start_inbound_server()
        # AetherNet announcement queue (overlay messages from n8n)
        self.aethernet_announcements: List[Tuple[str, float]] = []

        # Evolution screen state
        self._evo_char: Optional[Character] = None
        self._evo_from: str = ""
        self._evo_to: str = ""
        self._evo_timer: float = 0.0
        self._evo_phase: int = 0  # 0=glow, 1=transform, 2=reveal, 3=done
        self._evo_return_phase: str = "overworld"

        # Gacha screen state
        self._gacha_timer: float = 0.0
        self._gacha_phase: int = 0  # 0=swirl, 1=crack, 2=reveal, 3=done
        self._gacha_result: Optional[Character] = None
        self._gacha_rarity: int = 1  # 1-5 stars
        self._gacha_return_phase: str = "overworld"

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

    def _init_npc_systems(self) -> None:
        """Build PivotKnowledge and NPCBrain for each major NPC."""
        npc_defs = [
            ("polly", "Polly", "KO"),
            ("clay", "Clay", "RU"),
            ("eldrin", "Eldrin", "AV"),
            ("aria", "Aria Ravencrest", "UM"),
            ("zara", "Zara Millwright", "DR"),
            ("kael", "Kael Nightwhisper", "UM"),
        ]
        for npc_id, npc_name, tongue in npc_defs:
            char = self.cast.get(npc_id)
            backstory = char.backstory if char else ""
            self.npc_knowledge[npc_id] = build_npc_knowledge(
                npc_id, npc_name, tongue
            )
            self.npc_brains[npc_id] = create_npc_brain(
                npc_id, npc_name, tongue, backstory
            )

    def _polypad_has_device(self) -> bool:
        return bool(self.inventory.get("PollyPad", False))

    def _polypad_unread_count(self) -> int:
        return sum(1 for m in self.polypad_messages if m.get("unread", False))

    def _polypad_entries(self) -> List[str]:
        app = POLYPAD_APPS[self.polypad_tab]
        if app == "Home":
            return [
                "Open Contacts",
                "Open Messages",
                "Open Missions",
                "Open PC Box",
                "Open IDE",
                "Fleet Sync",
            ]
        if app == "Contacts":
            return [c["name"] for c in self.polypad_contacts]
        if app == "Messages":
            return [f"{m['from']}: {m['subject']}" for m in self.polypad_messages]
        if app == "Missions":
            return [f"{m['title']} [{m['status']}]" for m in self.polypad_missions]
        if app == "PC Box":
            rows = [
                "Sit at Guild Computer (CodeLab IDE)",
                "Open Lore Library (Morrowind-style books)",
            ]
            if not self.party:
                rows.append("No party members registered")
                return rows
            rows.extend(
                f"{c.name} Lv{c.stats.level}  HP {c.stats.hp}/{c.stats.max_hp}"
                for c in self.party[:6]
            )
            return rows
        if app == "IDE":
            return [
                "Launch CodeLab IDE",
                "Read Lore Books",
                "Review Last Build",
                "Sync Sidekick Memory",
            ]
        return []

    def _polypad_push_message(self, sender: str, subject: str, body: str, unread: bool = True) -> None:
        stamp = f"F{self.frame_count}"
        self.polypad_messages.insert(
            0,
            {
                "from": sender,
                "subject": subject[:42],
                "body": body,
                "unread": unread,
                "time": stamp,
            },
        )
        # Keep mailbox bounded for performance/readability.
        if len(self.polypad_messages) > 40:
            self.polypad_messages = self.polypad_messages[:40]

    def _polypad_update_missions(self, scene_id: str, action: str) -> None:
        """Keep Poly Pad mission cards aligned with story progression."""
        by_title = {m["title"]: m for m in self.polypad_missions}
        start = by_title.get("Village Start")
        traveler = by_title.get("Traveler Assist")
        shore = by_title.get("Shoreline Threat")

        if scene_id == "earth_morning" and action in {"take_full_kit", "check_pollypad", "promise_help"}:
            if start:
                start["status"] = "done"
            if traveler and traveler["status"] == "queued":
                traveler["status"] = "active"

        if scene_id == "earth_work" and action in {"help_traveler", "escort_traveler", "record_traveler"}:
            if traveler:
                traveler["status"] = "done"
            if shore and shore["status"] == "queued":
                shore["status"] = "active"

        if scene_id == "earth_evening" and action in {"fight_monster", "tame_monster"}:
            if shore:
                shore["status"] = "done"

    def _nearby_ide_terminal(self) -> Optional[str]:
        """Return terminal label if player is adjacent to an IDE terminal tile."""
        if not self.overworld.active:
            return None
        px, py = self.overworld.player_tile_pos
        terminals = IDE_TERMINALS.get(self.overworld.current_map_name, [])
        for tx, ty, label in terminals:
            if abs(px - tx) + abs(py - ty) <= 1:
                return label
        return None

    def _current_ide_ticket(self) -> Dict[str, Any]:
        if not IDE_TICKETS:
            return {
                "id": "none",
                "title": "No tickets",
                "brief": "No IDE tickets loaded.",
                "tongue": "CA",
                "reward_gold": 0,
                "risk_penalty": 0,
                "actions": [],
            }
        return IDE_TICKETS[self.ide_ticket_index % len(IDE_TICKETS)]

    def _ide_actions(self) -> List[str]:
        ticket = self._current_ide_ticket()
        options = [str(a.get("label", "Action")) for a in ticket.get("actions", [])]
        options.append("Read Lore Books")
        options.append("Next Ticket")
        options.append("Exit IDE")
        return options

    def _open_ide(self, return_phase: Optional[str] = None) -> None:
        """Open CodeLab IDE mini-game."""
        if self.battle.active:
            self.workshop_message = "CodeLab locked during battle."
            return
        self.ide_return_phase = return_phase or self.game_phase
        self.ide_cursor = 0
        self.game_phase = "ide"

    def _close_ide(self) -> None:
        fallback = "overworld"
        self.game_phase = self.ide_return_phase or fallback
        if self.game_phase == "ide":
            self.game_phase = fallback

    def _current_lore_book(self) -> Dict[str, str]:
        if not LORE_BOOKS:
            return {
                "id": "none",
                "title": "No books available",
                "source": "Local",
                "body": "No lore books have been loaded.",
            }
        return LORE_BOOKS[self.library_index % len(LORE_BOOKS)]

    def _open_library(self, return_phase: Optional[str] = None) -> None:
        self.library_return_phase = return_phase or self.game_phase
        self.library_scroll = 0
        self.game_phase = "library"

    def _close_library(self) -> None:
        fallback = "overworld"
        self.game_phase = self.library_return_phase or fallback
        if self.game_phase == "library":
            self.game_phase = fallback

    def _wrap_text_lines(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        words = text.split()
        if not words:
            return [""]
        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if font.size(trial)[0] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _mark_book_read(self, book_id: str, title: str) -> None:
        first_read = book_id not in self.library_read_books
        self.library_read_books.add(book_id)
        self.library_reads += 1

        self.hf_trainer.record_choice(
            context=f"Lore library: {title}",
            choice="Read Book",
            alternatives=["Close Book", "Switch Book"],
            outcome=f"Read lore source {book_id}",
            tongue="RU",
            layers=[3, 4, 5, 11],
        )
        self.sft_count += 1

        if first_read:
            self.inventory["Gold"] += 8
            self.reputation_points += 1
            self.partner_bond = min(1.0, self.partner_bond + 0.005)
            self.workshop_message = f"Read '{title}'. Lore retained (+8g)."
        else:
            self.workshop_message = f"Re-read '{title}'. Notes refreshed."

    def _handle_library_key(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_l):
            self._close_library()
            return

        if key in (pygame.K_LEFT, pygame.K_a):
            self.library_index = (self.library_index - 1) % max(1, len(LORE_BOOKS))
            self.library_scroll = 0
            return
        if key in (pygame.K_RIGHT, pygame.K_d):
            self.library_index = (self.library_index + 1) % max(1, len(LORE_BOOKS))
            self.library_scroll = 0
            return

        book = self._current_lore_book()
        preview_font = self.fonts.get(10)
        lines = self._wrap_text_lines(book.get("body", ""), preview_font, 360)
        max_lines = 16
        max_scroll = max(0, len(lines) - max_lines)

        if key in (pygame.K_UP, pygame.K_w):
            self.library_scroll = max(0, self.library_scroll - 1)
            return
        if key in (pygame.K_DOWN, pygame.K_s):
            self.library_scroll = min(max_scroll, self.library_scroll + 1)
            return
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            self._mark_book_read(book.get("id", "unknown"), book.get("title", "Lore Book"))
            return

    def _resolve_ide_action(self, choice: str) -> None:
        ticket = self._current_ide_ticket()
        if choice == "Read Lore Books":
            self._open_library(return_phase="ide")
            return
        if choice == "Next Ticket":
            self.ide_ticket_index = (self.ide_ticket_index + 1) % max(1, len(IDE_TICKETS))
            self.ide_cursor = 0
            self.workshop_message = "CodeLab switched to next ticket."
            return
        if choice == "Exit IDE":
            self._close_ide()
            return

        action_map = {str(a.get("label", "")): a for a in ticket.get("actions", [])}
        action_data = action_map.get(choice)
        if action_data is None:
            return

        success = bool(action_data.get("success", False))
        outcome = str(action_data.get("outcome", "No output."))
        reward = int(ticket.get("reward_gold", 0))
        penalty = int(ticket.get("risk_penalty", 1))
        tongue = str(ticket.get("tongue", "CA"))
        alternatives = [
            str(a.get("label", ""))
            for a in ticket.get("actions", [])
            if str(a.get("label", "")) != choice
        ]

        self.hf_trainer.record_choice(
            context=f"CodeLab ticket: {ticket.get('title', 'Unknown')}",
            choice=choice,
            alternatives=alternatives,
            outcome=outcome,
            tongue=tongue,
            layers=[5, 6, 7, 12, 13],
        )
        self.sft_count += 1

        if success:
            self.ide_resolved += 1
            self.inventory["Gold"] += reward
            self._grant_skill_xp("inscription", 1)
            self.reputation_points += 1
            self.partner_bond = min(1.0, self.partner_bond + 0.01)
            self.workshop_message = f"CodeLab resolved: {ticket.get('title', '')} (+{reward}g)."
            self.particles.emit(GAME_W // 2, GAME_H // 2, (96, 214, 255), count=16, spread=3.0)
            self._polypad_push_message(
                "CODELAB",
                f"{ticket.get('title', 'Ticket')} resolved",
                outcome,
                unread=True,
            )
        else:
            self.ide_failures += 1
            self.reputation_points -= penalty
            self.partner_bond = max(0.0, self.partner_bond - 0.01)
            self.workshop_message = f"CodeLab unstable: {ticket.get('title', '')} (-{penalty} rep)."
            self._polypad_push_message(
                "CODELAB",
                f"{ticket.get('title', 'Ticket')} warning",
                outcome,
                unread=True,
            )

        self.ide_last_result = outcome
        self.ide_history.insert(0, f"{ticket.get('id', 'ticket')}: {choice}")
        self.ide_history = self.ide_history[:20]
        self.ide_ticket_index = (self.ide_ticket_index + 1) % max(1, len(IDE_TICKETS))
        self.ide_cursor = 0

    def _handle_ide_key(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_i):
            self._close_ide()
            return
        if key == pygame.K_l:
            self._open_library(return_phase="ide")
            return

        if key in (pygame.K_LEFT, pygame.K_a):
            self.ide_ticket_index = (self.ide_ticket_index - 1) % max(1, len(IDE_TICKETS))
            self.ide_cursor = 0
            return
        if key in (pygame.K_RIGHT, pygame.K_d):
            self.ide_ticket_index = (self.ide_ticket_index + 1) % max(1, len(IDE_TICKETS))
            self.ide_cursor = 0
            return

        actions = self._ide_actions()
        if not actions:
            return

        if key in (pygame.K_UP, pygame.K_w):
            self.ide_cursor = (self.ide_cursor - 1) % len(actions)
            return
        if key in (pygame.K_DOWN, pygame.K_s):
            self.ide_cursor = (self.ide_cursor + 1) % len(actions)
            return
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            selected = actions[self.ide_cursor]
            self._resolve_ide_action(selected)
            return

    def _open_polypad(self) -> None:
        if not self._polypad_has_device():
            self.workshop_message = "No Poly Pad in inventory yet."
            return
        if self.battle.active:
            self.workshop_message = "Poly Pad disabled during active battle."
            return
        if self.game_phase == "polypad":
            return
        self.polypad_return_phase = self.game_phase
        self.polypad_cursor = 0
        self.game_phase = "polypad"

    def _close_polypad(self) -> None:
        fallback = "overworld"
        self.game_phase = self.polypad_return_phase or fallback
        if self.game_phase == "polypad":
            self.game_phase = fallback

    def _handle_polypad_key(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_p):
            self._close_polypad()
            return

        if key in (pygame.K_LEFT, pygame.K_a):
            self.polypad_tab = (self.polypad_tab - 1) % len(POLYPAD_APPS)
            self.polypad_cursor = 0
            return

        if key in (pygame.K_RIGHT, pygame.K_d):
            self.polypad_tab = (self.polypad_tab + 1) % len(POLYPAD_APPS)
            self.polypad_cursor = 0
            return

        quick_max = pygame.K_1 + min(len(POLYPAD_APPS), 9) - 1
        if pygame.K_1 <= key <= quick_max:
            self.polypad_tab = min(len(POLYPAD_APPS) - 1, key - pygame.K_1)
            self.polypad_cursor = 0
            return

        entries = self._polypad_entries()
        if not entries:
            return

        if key in (pygame.K_UP, pygame.K_w):
            self.polypad_cursor = (self.polypad_cursor - 1) % len(entries)
            return
        if key in (pygame.K_DOWN, pygame.K_s):
            self.polypad_cursor = (self.polypad_cursor + 1) % len(entries)
            return

        if key not in (pygame.K_RETURN, pygame.K_SPACE):
            return

        app = POLYPAD_APPS[self.polypad_tab]
        idx = max(0, min(self.polypad_cursor, len(entries) - 1))

        if app == "Home":
            if idx == 0:
                self.polypad_tab = POLYPAD_APPS.index("Contacts")
                self.polypad_cursor = 0
            elif idx == 1:
                self.polypad_tab = POLYPAD_APPS.index("Messages")
                self.polypad_cursor = 0
            elif idx == 2:
                self.polypad_tab = POLYPAD_APPS.index("Missions")
                self.polypad_cursor = 0
            elif idx == 3:
                self.polypad_tab = POLYPAD_APPS.index("PC Box")
                self.polypad_cursor = 0
            elif idx == 4:
                self.polypad_tab = POLYPAD_APPS.index("IDE")
                self.polypad_cursor = 0
            else:
                self.workshop_message = "Fleet sync complete. Mission graph refreshed."
                self._polypad_push_message(
                    "FLEET COMMS",
                    "Sync Report",
                    "Routing table synced. Keep core loop simple; route complexity via mini-games.",
                )
            return

        if app == "Contacts":
            contact = self.polypad_contacts[idx]
            name = contact["name"]
            contact["last_call"] = f"F{self.frame_count}"
            call_lines = {
                "MOM": "Keep your Wallet, Keys, and Poly Pad close. You'll need all three.",
                "POLLY": "Core loop first. Mini-games carry advanced tactics.",
                "CLAY": "Shield discipline beats panic. Guard first, strike second.",
                "MARCUS": "Proof before privilege. Keep your chain of decisions auditable.",
                "FLEET COMMS": "Signal green. Elite threat channels are monitoring your zone.",
            }
            line = call_lines.get(name, "Signal received.")
            self.workshop_message = f"Poly Pad call: {name}."
            self._polypad_push_message(name, "Call Transcript", line)
            self.polypad_call_log.insert(0, f"{name} @ F{self.frame_count}")
            self.polypad_call_log = self.polypad_call_log[:24]
            return

        if app == "Messages":
            msg = self.polypad_messages[idx]
            msg["unread"] = False
            self.workshop_message = f"Read: {msg['subject'][:34]}"
            return

        if app == "Missions":
            for i, mission in enumerate(self.polypad_missions):
                if i == idx:
                    mission["status"] = "active"
                elif mission["status"] == "active":
                    mission["status"] = "queued"
            self.workshop_message = f"Mission set: {self.polypad_missions[idx]['title']}"
            return

        if app == "PC Box":
            if idx == 0:
                terminal = self._nearby_ide_terminal() or "Guild Computer"
                self.workshop_message = f"{terminal} online. Launching CodeLab."
                self._open_ide(return_phase="polypad")
                return
            if idx == 1:
                self.workshop_message = "Opening lore library."
                self._open_library(return_phase="polypad")
                return
            party_idx = idx - 2
            if 0 <= party_idx < len(self.party):
                c = self.party[party_idx]
                self.workshop_message = (
                    f"PC Box: {c.name} Lv{c.stats.level} "
                    f"ATK {c.stats.attack} DEF {c.stats.defense}"
                )
            return

        if app == "IDE":
            if idx == 0:
                self._open_ide(return_phase="polypad")
            elif idx == 1:
                self._open_library(return_phase="polypad")
            elif idx == 2:
                self.workshop_message = f"Last build: {self.ide_last_result[:80]}"
            else:
                self.workshop_message = "Sidekick memory sync queued for cloud run."
                self._polypad_push_message(
                    "CODELAB",
                    "Sidekick Sync",
                    "Append-only sidekick memory sync queued for Firebase/HF pipeline.",
                    unread=False,
                )

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

        # AetherNet: broadcast class selection
        self.n8n_bus.emit(
            GameEventType.LEVEL_UP,
            class_name=str(config["name"]), partner=partner_key,
        )

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
                self._polypad_push_message(
                    "MOM",
                    "Starter Kit",
                    "Poly Pad online. Keep your field logs updated and your route clean.",
                )
            elif action == "check_wallet":
                self.inventory["Wallet"] = True
                self.inventory["Gold"] += 100
            elif action == "check_pollypad":
                self.inventory["PollyPad"] = True
                self.partner_bond = min(1.0, self.partner_bond + 0.04)
                self._polypad_push_message(
                    "POLLY",
                    "Pad Sync",
                    "Signal lock confirmed. You can now open Poly Pad with [P].",
                )
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
                self._polypad_push_message(
                    "FLEET COMMS",
                    "Trust Record",
                    "Traveler interaction logged. Guild trust vector increased.",
                )
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
                if action == "tame_monster":
                    self._polypad_push_message(
                        "POLLY",
                        "Tone Capture",
                        "Taming route succeeded. Harmonic resonance archived.",
                    )
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

            # Headless: capture frame from game_surface
            if self.headless_display is not None:
                self.headless_display.capture(self.game_surface)

            pygame.display.flip()
            self.frame_count += 1

        # Cleanup
        if self.headless_display is not None:
            self.headless_display.stop()
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
        if key == pygame.K_F9:
            state = self.n8n_bus.toggle()
            st = self.n8n_bus.status()
            self.workshop_message = (
                f"AetherNet {'ONLINE' if state else 'OFFLINE'} "
                f"({st['events_sent']} sent, {st['endpoints']} endpoints)"
            )
            return

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

        if self.game_phase == "ide":
            self._handle_ide_key(key)
            return

        if self.game_phase == "library":
            self._handle_library_key(key)
            return

        if self.game_phase == "polypad":
            self._handle_polypad_key(key)
            return

        if key == pygame.K_p:
            if self.paused:
                return
            if self._polypad_has_device():
                self._open_polypad()
            else:
                self.workshop_message = "No Poly Pad equipped yet."
            return

        if key == pygame.K_i and self.game_phase == "overworld":
            terminal = self._nearby_ide_terminal()
            if terminal:
                self.workshop_message = f"{terminal} online. Launching CodeLab."
                self._open_ide(return_phase="overworld")
            else:
                self.workshop_message = "Move next to a terminal to open CodeLab."
            return

        if key == pygame.K_l and self.game_phase == "overworld":
            terminal = self._nearby_ide_terminal()
            if terminal:
                self.workshop_message = f"{terminal} archive opened."
                self._open_library(return_phase="overworld")
            else:
                self.workshop_message = "Move next to a terminal to open the lore library."
            return

        # Global controls
        if key == pygame.K_ESCAPE:
            if self.paused:
                self.paused = False
                return
            elif self.game_phase == "title":
                self._save_and_quit()
                return
            elif self.game_phase in ("dialogue", "dungeon"):
                pass  # Let phase-specific handlers deal with ESC
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
        if self.game_phase == "evolution":
            if key in (pygame.K_RETURN, pygame.K_SPACE) and self._evo_phase >= 3:
                self.game_phase = self._evo_return_phase
                self._evo_char = None
            return
        elif self.game_phase == "gacha":
            if self._gacha_phase >= 3:
                if key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self._gacha_result and len(self.party) < 6:
                        self.party.append(self._gacha_result)
                        self.workshop_message = f"{self._gacha_result.name} joined the party!"
                    self.game_phase = self._gacha_return_phase
                    self._gacha_result = None
                elif key == pygame.K_ESCAPE:
                    self.game_phase = self._gacha_return_phase
                    self._gacha_result = None
            return
        elif self.game_phase == "title":
            self._handle_title_key(key)
        elif self.battle.active:
            self._handle_battle_key(key)
        elif self.game_phase == "overworld":
            # G key for gacha pull (overworld only)
            if key == pygame.K_g:
                self._start_gacha_pull()
                return
            self._handle_overworld_key(key)
        elif self.game_phase == "dungeon":
            self._handle_dungeon_key(key)
        elif self.game_phase == "dialogue":
            self._handle_dialogue_key(key)
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
                result = "victory" if self.battle.victory else "defeat"
                enemy_name = self.battle.enemies[0].name if self.battle.enemies else "Unknown"
                enemy_tongue = self.battle.enemies[0].tongue_affinity.value if self.battle.enemies else "KO"
                xp_gained = 10 if self.battle.victory else 0
                context = "dungeon" if self.dungeon_active else "overworld"
                self._polypad_push_message(
                    "SYSTEM",
                    f"Battle {result.title()}",
                    f"{enemy_name} resolved in {context}. XP +{xp_gained}.",
                    unread=False,
                )

                # HF trainer: battle result
                self.hf_trainer.record_battle(
                    self.party[0].name if self.party else "Player",
                    enemy_name, result, xp_gained, enemy_tongue, context
                )

                # AetherNet: broadcast battle result
                is_boss = any(
                    getattr(e, 'title', '') == 'Floor Boss'
                    for e in self.battle.enemies
                )
                self.n8n_bus.emit(
                    GameEventType.BATTLE_WON if result == "victory" else GameEventType.BATTLE_LOST,
                    enemy=enemy_name, tongue=enemy_tongue, xp=xp_gained,
                    context=context, player_class=self.player_class,
                )
                if is_boss and result == "victory":
                    self.n8n_bus.emit(
                        GameEventType.BOSS_DEFEATED,
                        boss=enemy_name, tongue=enemy_tongue,
                        floor=self.tower.current_floor,
                    )

                if self.battle.victory and self._story_battle_active:
                    self._grant_material("crystal_dust", 1)
                    self._grant_material("shell", 1)
                    self._grant_skill_xp("ecology", 1)
                    self._progress_band_quest("craft", 1)

                # Dungeon: track kills and tongue prof boost on victory
                if self.battle.victory and self.dungeon_active:
                    self.tower.floor_kills = getattr(self.tower, 'floor_kills', 0) + len(self.battle.enemies)
                    if self.party:
                        prof = self.party[0].stats.tongue_prof
                        current = prof.get(enemy_tongue, 0.0)
                        prof[enemy_tongue] = min(1.0, current + 0.01)

                self.battle.end_battle()
                # Heal party slightly after battle
                for c in self.party:
                    c.stats.hp = min(c.stats.max_hp, c.stats.hp + c.stats.max_hp // 4)
                    c.stats.mp = min(c.stats.max_mp, c.stats.mp + c.stats.max_mp // 4)
                self._story_battle_active = False

                # Check for evolution after victory
                if result == "victory":
                    self._check_evolution()

                if self._pending_scene_after_battle:
                    self.transitioning = True
                    self.transition_progress = 0.0
                    self._pending_scene = self._pending_scene_after_battle
                    self._pending_scene_after_battle = None
                elif self.dungeon_active:
                    self.game_phase = "dungeon"
                elif self.overworld.active:
                    self.game_phase = "overworld"
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
    # Overworld Key Handling
    # ------------------------------------------------------------------
    def _handle_overworld_key(self, key: int) -> None:
        """Handle keys during overworld exploration."""
        # B key for test battle
        if key == pygame.K_b:
            self._start_test_battle()
            return
        # Enter/Space for NPC interaction
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            nearby = self.overworld.get_nearby_npc()
            if nearby:
                self._start_npc_dialogue(nearby)
                return
            terminal = self._nearby_ide_terminal()
            if terminal:
                self.workshop_message = f"{terminal} connected. Entering CodeLab."
                self._open_ide(return_phase="overworld")

    def _handle_dungeon_key(self, key: int) -> None:
        """Handle keys during dungeon exploration."""
        floor = self.tower.get_current_floor()
        if not floor:
            return

        dx, dy = 0, 0
        if key in (pygame.K_UP, pygame.K_w):
            dy = -1
        elif key in (pygame.K_DOWN, pygame.K_s):
            dy = 1
        elif key in (pygame.K_LEFT, pygame.K_a):
            dx = -1
        elif key in (pygame.K_RIGHT, pygame.K_d):
            dx = 1
        elif key == pygame.K_ESCAPE:
            # Leave dungeon back to overworld
            self.dungeon_active = False
            self.game_phase = "overworld"
            self.overworld.enter("spiral_tower_entrance", 10, 10)
            return

        if dx != 0 or dy != 0:
            nx = self.dungeon_player_x + dx
            ny = self.dungeon_player_y + dy
            if floor.is_walkable(nx, ny):
                self.dungeon_player_x = nx
                self.dungeon_player_y = ny

                tile = floor.get_tile(nx, ny)
                # Monster spawn
                if tile == 3:  # monster_spawn
                    floor.tiles[ny, nx] = 1  # clear spawn
                    enemies = generate_floor_enemies(self.tower.current_floor, floor.theme)
                    if floor.is_boss_floor and not floor.cleared:
                        enemies = [generate_boss(self.tower.current_floor, floor.theme)]
                    self.battle.start_battle(
                        party=[c for c in self.party if c.stats.hp > 0],
                        enemies=enemies,
                    )
                    self.particles.emit(GAME_W // 2, GAME_H // 2, (255, 80, 80), count=25, spread=4.0)
                    self._pending_scene_after_battle = None
                    self._story_battle_active = True
                    # Record tower battle
                    self.hf_trainer.record_battle(
                        self.party[0].name if self.party else "Player",
                        enemies[0].name, "encounter",
                        0, enemies[0].tongue_affinity.value, "tower"
                    )
                # Exit stair
                elif tile == 4:  # exit_stair
                    floor.cleared = True
                    old_floor_num = self.tower.current_floor
                    self.tower.advance_floor()
                    self.tower.floor_kills = 0
                    new_floor = self.tower.get_current_floor()
                    if new_floor:
                        self.dungeon_player_x = 1
                        self.dungeon_player_y = 1
                        self.hf_trainer.record_tower_floor(
                            self.tower.current_floor,
                            self.tower.floor_kills,
                            new_floor.theme.name,
                            new_floor.is_boss_floor,
                        )
                    # AetherNet: broadcast floor cleared
                    self.n8n_bus.emit(
                        GameEventType.DUNGEON_FLOOR_CLEARED,
                        floor=old_floor_num,
                        next_floor=self.tower.current_floor,
                        theme=new_floor.theme.name if new_floor else "unknown",
                        is_boss_next=new_floor.is_boss_floor if new_floor else False,
                    )
                    self.particles.emit(GAME_W // 2, GAME_H // 2, (80, 200, 255), count=20, spread=3.0)

    def _handle_dialogue_key(self, key: int) -> None:
        """Handle keys during NPC dialogue."""
        if not self.dialogue_active:
            return

        if key in (pygame.K_ESCAPE,):
            # Exit dialogue — broadcast to AetherNet
            self.n8n_bus.emit(
                GameEventType.NPC_DIALOGUE_COMPLETE,
                npc=self.dialogue_npc_id,
                topics_discussed=len(getattr(self, 'dialogue_gen', None).pairs if hasattr(self, 'dialogue_gen') and self.dialogue_gen else []),
            )
            self.dialogue_active = False
            self.game_phase = "overworld"
            return

        if key in (pygame.K_UP, pygame.K_w):
            if self.dialogue_pivots:
                self.dialogue_pivot_cursor = (self.dialogue_pivot_cursor - 1) % len(self.dialogue_pivots)
        elif key in (pygame.K_DOWN, pygame.K_s):
            if self.dialogue_pivots:
                self.dialogue_pivot_cursor = (self.dialogue_pivot_cursor + 1) % len(self.dialogue_pivots)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.dialogue_pivots:
                topic_id, topic_name = self.dialogue_pivots[self.dialogue_pivot_cursor]
                npc_id = self.dialogue_npc_id

                # Pivot in knowledge graph
                pk = self.npc_knowledge.get(npc_id)
                brain = self.npc_brains.get(npc_id)
                if pk:
                    self.dialogue_response = pk.pivot(topic_id)
                    self.dialogue_pivots = pk.get_pivots()
                    self.dialogue_pivot_cursor = 0

                    # Sacred language encoding as flavor text
                    char = self.cast.get(npc_id)
                    tongue = char.tongue_affinity.value if char else "KO"
                    self.dialogue_sacred_text = self.sacred_langs.encode(
                        self.dialogue_response[:60], tongue
                    )

                    # Generate training data
                    pair = pk.generate_training_pair()
                    self.dialogue_gen.pairs.append(pair)
                    self.sft_count += 1

                    # HF trainer
                    self.hf_trainer.record_dialogue(
                        pk.npc_name, tongue,
                        topic_name, self.dialogue_response,
                        topic_id,
                    )

                    # Try AI brain response (optional)
                    if brain and brain.api_available:
                        ai_resp = brain.get_response(topic_name, topic_id)
                        if ai_resp:
                            self.dialogue_response = ai_resp
                            self.dialogue_sacred_text = self.sacred_langs.encode(
                                ai_resp[:60], tongue
                            )

    def _start_npc_dialogue(self, npc_id: str) -> None:
        """Start a PivotKnowledge dialogue with an NPC."""
        # Extract base npc_id from the placement id (e.g., "polly_hub" -> "polly")
        base_id = npc_id.split("_")[0] if "_" in npc_id else npc_id
        pk = self.npc_knowledge.get(base_id)
        if not pk:
            return

        self.dialogue_active = True
        self.dialogue_npc_id = base_id
        self.game_phase = "dialogue"
        self.dialogue_response = pk.get_response()
        self.dialogue_pivots = pk.get_pivots()
        self.dialogue_pivot_cursor = 0

        # Sacred text
        char = self.cast.get(base_id)
        tongue = char.tongue_affinity.value if char else "KO"
        self.dialogue_sacred_text = self.sacred_langs.encode(
            self.dialogue_response[:60], tongue
        )

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
        self._polypad_update_missions(scene_id, action)
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

        # HF trainer: real-time training event
        self.hf_trainer.record_choice(
            context=scene_id,
            choice=label,
            alternatives=[c[0] for c in self.scene.choices if c[0] != label],
            outcome=action,
            tongue=tongue,
            layers=layers,
        )

        # AetherNet: broadcast choice
        self.n8n_bus.emit(
            GameEventType.CHOICE_MADE,
            scene=scene_id, action=action, tongue=tongue,
            layers=layers, player_class=self.player_class,
            reputation=self.reputation_points,
        )

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
            self.n8n_bus.emit(
                GameEventType.SCENE_TRANSITION,
                from_scene=self.scene.current_scene_id,
                to_scene=next_id,
            )
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
            # All linear scenes done — transition to overworld
            self.transitioning = True
            self.transition_progress = 0.0
            self._pending_scene = "__overworld__"

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
        # Stop HF trainer daemon thread
        try:
            self.hf_trainer.stop()
        except Exception:
            pass
        # Stop AetherNet bridge
        try:
            self.n8n_bus.stop()
        except Exception:
            pass
        self.running = False

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def _process_n8n_action(self, action: GameAction) -> None:
        """Apply an action received from n8n (AetherNet inbound packet)."""
        atype = action.action_type
        data = action.data

        if atype == GameActionType.SEND_DIALOGUE:
            speaker = data.get("speaker", "AETHERNET")
            text = data.get("text", "...")
            self.scene.dialogue_lines.append((speaker, text))

        elif atype == GameActionType.GIVE_ITEM:
            item = data.get("item", "")
            amount = data.get("amount", 1)
            if item == "Gold":
                self.inventory["Gold"] = self.inventory.get("Gold", 0) + amount
            elif item in self.materials:
                self.materials[item] = self.materials.get(item, 0) + amount

        elif atype == GameActionType.MODIFY_STAT:
            stat = data.get("stat", "")
            delta = data.get("delta", 0)
            if stat == "reputation":
                self.reputation_points += delta
            elif stat == "bond":
                self.partner_bond = max(0.0, min(1.0, self.partner_bond + delta))
            elif stat in ("hp", "mp", "attack", "defense", "speed", "wisdom"):
                if self.party:
                    current = getattr(self.party[0].stats, stat, 0)
                    setattr(self.party[0].stats, stat, max(0, current + delta))

        elif atype == GameActionType.TRIGGER_SCENE:
            scene_id = data.get("scene_id", "")
            if scene_id in SCENE_DIALOGUES:
                self.transitioning = True
                self.transition_progress = 0.0
                self._pending_scene = scene_id

        elif atype == GameActionType.SPAWN_ENEMY:
            name = data.get("name", "AetherNet Construct")
            tongue_code = data.get("tongue", "UM")
            hp = data.get("hp", 50)
            atk = data.get("attack", 8)
            tongue_enum = Tongue[tongue_code] if tongue_code in Tongue.__members__ else Tongue.UM
            enemy = Character(
                name=name,
                title="AetherNet Summoned",
                tongue_affinity=tongue_enum,
                evo_stage=EvoStage.ROOKIE,
                stats=Stats(hp=hp, max_hp=hp, mp=20, max_mp=20,
                            attack=atk, defense=6, speed=8, wisdom=5),
                spells=[],
                is_enemy=True,
            )
            self.battle.start_battle(
                party=[c for c in self.party if c.stats.hp > 0],
                enemies=[enemy],
            )
            self.particles.emit(GAME_W // 2, GAME_H // 2, (255, 60, 255), count=25, spread=5.0)

        elif atype == GameActionType.TV_SHOW:
            self.n8n_bus.push_tv(
                show_name=data.get("show", "Unknown"),
                content=data.get("content", ""),
                channel=data.get("channel", "AetherTV"),
            )

        elif atype == GameActionType.TRAINING_RESULT:
            # Surface HF training metrics in the dashboard
            metrics = data.get("metrics", {})
            loss = metrics.get("loss", "?")
            self.workshop_message = f"HF Training: loss={loss}"

        elif atype == GameActionType.ANNOUNCE:
            text = data.get("text", "...")
            self.aethernet_announcements.append((text, time.time()))
            # Keep only last 5
            self.aethernet_announcements = self.aethernet_announcements[-5:]

        elif atype == GameActionType.BUFF_PARTY:
            stat = data.get("stat", "attack")
            delta = data.get("delta", 3)
            for c in self.party:
                if hasattr(c.stats, stat):
                    current = getattr(c.stats, stat, 0)
                    setattr(c.stats, stat, max(0, current + delta))
            self.workshop_message = f"AetherNet buff: {stat} +{delta} to party"
            self.particles.emit(GAME_W // 2, GAME_H // 2, (80, 255, 180), count=30, spread=4.0)

        elif atype == GameActionType.FORCE_GACHA:
            # Trigger a random gacha pull — add a new party member
            tongue_code = data.get("tongue", random.choice(["KO", "AV", "RU", "CA", "UM", "DR"]))
            tongue_enum = Tongue[tongue_code] if tongue_code in Tongue.__members__ else Tongue.KO
            name = data.get("name", f"Gacha-{tongue_code}-{random.randint(100,999)}")
            recruit = Character(
                name=name,
                title="AetherNet Recruit",
                tongue_affinity=tongue_enum,
                evo_stage=EvoStage.ROOKIE,
                stats=Stats(hp=40, max_hp=40, mp=20, max_mp=20,
                            attack=8, defense=6, speed=7, wisdom=6),
                spells=[],
                is_enemy=False,
            )
            if len(self.party) < 6:
                self.party.append(recruit)
                self.workshop_message = f"AetherNet gacha: {name} [{tongue_code}] joined!"
            else:
                self.workshop_message = f"Party full! {name} couldn't join."
            self.n8n_bus.emit(
                GameEventType.GACHA_PULL,
                name=name, tongue=tongue_code, party_size=len(self.party),
            )
            self.particles.emit(GAME_W // 2, GAME_H // 2, GOLD, count=40, spread=5.0)

        elif atype == GameActionType.DUNGEON_MODIFIER:
            modifier = data.get("modifier", "")
            if modifier == "harder":
                # Increase current floor enemy HP
                floor = self.tower.get_current_floor() if hasattr(self, 'tower') else None
                if floor:
                    self.workshop_message = "AetherNet: Dungeon difficulty increased!"
            elif modifier == "heal":
                for c in self.party:
                    c.stats.hp = c.stats.max_hp
                    c.stats.mp = c.stats.max_mp
                self.workshop_message = "AetherNet: Party fully healed!"
                self.particles.emit(GAME_W // 2, GAME_H // 2, (80, 255, 120), count=25, spread=4.0)

    def _update(self, dt: float) -> None:
        """Update game state."""
        if self.paused:
            return

        # Process AetherNet inbound actions
        for action in self.n8n_bus.drain_actions():
            self._process_n8n_action(action)

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
                if self._pending_scene == "__overworld__":
                    # Enter overworld after linear scenes complete
                    self.game_phase = "overworld"
                    self.overworld.enter("guild_hub")
                else:
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

        # Overworld continuous movement (held keys)
        if self.game_phase == "overworld" and not self.battle.active:
            keys = pygame.key.get_pressed()
            dx = (1 if keys[pygame.K_RIGHT] or keys[pygame.K_d] else 0) - \
                 (1 if keys[pygame.K_LEFT] or keys[pygame.K_a] else 0)
            dy = (1 if keys[pygame.K_DOWN] or keys[pygame.K_s] else 0) - \
                 (1 if keys[pygame.K_UP] or keys[pygame.K_w] else 0)
            self.overworld.update(dt, dx, dy, interact=False)

            # Consume pending events from overworld
            if self.overworld.encounter_pending:
                enemies = self.overworld.consume_encounter()
                if enemies:
                    self.battle.start_battle(
                        party=[c for c in self.party if c.stats.hp > 0],
                        enemies=enemies,
                    )
                    self._story_battle_active = False
                    self._pending_scene_after_battle = None
                    self.particles.emit(GAME_W // 2, GAME_H // 2, (255, 80, 80), count=25, spread=4.0)
                    self.hf_trainer.record_battle(
                        self.party[0].name if self.party else "Player",
                        enemies[0].name, "encounter",
                        0, enemies[0].tongue_affinity.value, "overworld"
                    )

            if self.overworld.warp_pending:
                warp = self.overworld.consume_warp()
                if warp:
                    self.overworld.enter(warp.map_name, warp.x, warp.y)
                    self.particles.emit(GAME_W // 2, GAME_H // 2, (80, 200, 255), count=20, spread=3.0)

            if self.overworld.npc_interaction_pending:
                npc_id = self.overworld.consume_npc_interaction()
                if npc_id:
                    self._start_npc_dialogue(npc_id)

            if self.overworld.dungeon_entry_pending:
                self.overworld.consume_dungeon_entry()
                self.dungeon_active = True
                self.game_phase = "dungeon"
                self.tower.enter_tower()
                self.dungeon_player_x = 1
                self.dungeon_player_y = 1
                self.n8n_bus.emit(
                    GameEventType.DUNGEON_ENTERED,
                    floor=self.tower.current_floor,
                    party_size=len(self.party),
                )
                self.particles.emit(GAME_W // 2, GAME_H // 2, (160, 80, 255), count=20, spread=3.0)

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
        elif self.game_phase == "evolution":
            self._draw_evolution_screen()
        elif self.game_phase == "gacha":
            self._draw_gacha_screen()
        elif self.workshop_open:
            self._draw_workshop_screen()
        elif self.game_phase == "ide":
            self._draw_ide_screen()
        elif self.game_phase == "library":
            self._draw_library_screen()
        elif self.game_phase == "polypad":
            self._draw_polypad_screen()
        elif self.battle.active:
            self._draw_battle_screen()
        elif self.game_phase == "overworld":
            self._draw_overworld_screen()
        elif self.game_phase == "dungeon":
            self._draw_dungeon_screen()
        elif self.game_phase == "dialogue":
            self._draw_dialogue_screen()
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
    # Overworld Screen
    # ------------------------------------------------------------------
    def _draw_overworld_screen(self) -> None:
        """Draw the tile-based overworld."""
        self.game_surface.fill((24, 32, 20))
        self.overworld.draw(self.game_surface)

        # Map name HUD
        map_name = self.overworld.current_map_name.replace("_", " ").title()
        hud_font = self.fonts.get(12, bold=True)
        name_surf = hud_font.render(map_name, True, GOLD)
        bg = pygame.Surface((name_surf.get_width() + 12, name_surf.get_height() + 6), pygame.SRCALPHA)
        bg.fill((10, 10, 26, 200))
        self.game_surface.blit(bg, (8, 6))
        self.game_surface.blit(name_surf, (14, 9))

        # Controls hint
        hint_font = self.fonts.get(9)
        hint_surf = hint_font.render("WASD:Move  Enter:Talk  I:IDE  L:Library  P:PolyPad  B:Battle  Esc:Pause", True, DIM_TEXT)
        self.game_surface.blit(hint_surf, (8, GAME_H - 16))

        terminal = self._nearby_ide_terminal()
        if terminal:
            prompt = hint_font.render(f"Enter: Use {terminal}", True, (255, 220, 120))
            self.game_surface.blit(prompt, (8, GAME_H - 30))

        # Draw terminal beacons to improve discoverability.
        if self.overworld.camera:
            beacons = IDE_TERMINALS.get(self.overworld.current_map_name, [])
            pulse = 0.5 + 0.5 * math.sin(self.frame_count * 0.15)
            glow = lerp_color((70, 120, 220), (255, 220, 120), pulse)
            for tx, ty, _label in beacons:
                sx = int(tx * TILE_SIZE - self.overworld.camera.x + self.overworld.camera.view_w // 2 + TILE_SIZE // 2)
                sy = int(ty * TILE_SIZE - self.overworld.camera.y + self.overworld.camera.view_h // 2 + TILE_SIZE // 2)
                if -8 <= sx <= GAME_W + 8 and -8 <= sy <= GAME_H + 8:
                    pygame.draw.circle(self.game_surface, glow, (sx, sy - 10), 5, 1)
                    pygame.draw.rect(self.game_surface, glow, (sx - 4, sy - 5, 8, 6), 1)

    # ------------------------------------------------------------------
    # Dungeon Screen
    # ------------------------------------------------------------------
    def _draw_dungeon_screen(self) -> None:
        """Draw the dungeon floor as a mini-map grid view."""
        self.game_surface.fill((14, 8, 24))
        floor = self.tower.get_current_floor()
        if not floor:
            font = self.fonts.get(16, bold=True)
            self.game_surface.blit(font.render("No dungeon floor loaded", True, TEXT_COLOR), (40, 200))
            return

        # Calculate tile render size to fit the floor in the game area
        max_tiles_w = floor.width
        max_tiles_h = floor.height
        tile_px = min((GAME_W - 40) // max_tiles_w, (GAME_H - 100) // max_tiles_h, 28)
        offset_x = (GAME_W - max_tiles_w * tile_px) // 2
        offset_y = 60

        # Theme colors
        from dungeon import FloorTheme, Tile as DTile
        theme_colors = {
            FloorTheme.CRYSTAL: (80, 140, 220),
            FloorTheme.SHADOW: (100, 60, 140),
            FloorTheme.FIRE: (200, 80, 40),
            FloorTheme.DATA: (60, 200, 160),
        }
        accent = theme_colors.get(floor.theme, (120, 120, 140))

        # Draw tiles
        for ty in range(max_tiles_h):
            for tx in range(max_tiles_w):
                rx = offset_x + tx * tile_px
                ry = offset_y + ty * tile_px
                tile = floor.get_tile(tx, ty)
                if tile == DTile.WALL:
                    pygame.draw.rect(self.game_surface, (30, 25, 40), (rx, ry, tile_px - 1, tile_px - 1))
                elif tile == DTile.FLOOR:
                    pygame.draw.rect(self.game_surface, (50, 45, 60), (rx, ry, tile_px - 1, tile_px - 1))
                elif tile == DTile.MONSTER_SPAWN:
                    pygame.draw.rect(self.game_surface, (50, 45, 60), (rx, ry, tile_px - 1, tile_px - 1))
                    pygame.draw.circle(self.game_surface, (200, 60, 60), (rx + tile_px // 2, ry + tile_px // 2), tile_px // 4)
                elif tile == DTile.EXIT_STAIR:
                    pygame.draw.rect(self.game_surface, (60, 180, 100), (rx, ry, tile_px - 1, tile_px - 1))
                elif tile == DTile.CHEST:
                    pygame.draw.rect(self.game_surface, (50, 45, 60), (rx, ry, tile_px - 1, tile_px - 1))
                    pygame.draw.rect(self.game_surface, (220, 180, 60), (rx + 2, ry + 2, tile_px - 5, tile_px - 5), 1)
                elif tile == DTile.TRAP:
                    pygame.draw.rect(self.game_surface, (50, 45, 60), (rx, ry, tile_px - 1, tile_px - 1))
                    pygame.draw.line(self.game_surface, (200, 60, 60), (rx + 2, ry + 2), (rx + tile_px - 3, ry + tile_px - 3))
                    pygame.draw.line(self.game_surface, (200, 60, 60), (rx + tile_px - 3, ry + 2), (rx + 2, ry + tile_px - 3))

        # Draw player
        px = offset_x + self.dungeon_player_x * tile_px
        py = offset_y + self.dungeon_player_y * tile_px
        pygame.draw.rect(self.game_surface, (80, 200, 255), (px + 1, py + 1, tile_px - 3, tile_px - 3))
        pygame.draw.rect(self.game_surface, (255, 255, 255), (px + 1, py + 1, tile_px - 3, tile_px - 3), 1)

        # HUD: floor info
        hud_font = self.fonts.get(12, bold=True)
        floor_text = f"FLOOR {self.tower.current_floor}"
        if floor.is_boss_floor:
            floor_text += "  [BOSS]"
        self.game_surface.blit(hud_font.render(floor_text, True, accent), (14, 10))

        theme_font = self.fonts.get(10)
        self.game_surface.blit(theme_font.render(f"Theme: {floor.theme.name}", True, DIM_TEXT), (14, 30))

        # Controls
        hint_font = self.fonts.get(9)
        self.game_surface.blit(
            hint_font.render("WASD:Move  P:PolyPad  Esc:Exit Tower", True, DIM_TEXT),
            (8, GAME_H - 16),
        )

    def _draw_ide_screen(self) -> None:
        """Draw the CodeLab IDE mini-game screen."""
        # Navy -> cyan gradient to keep Sapphire-era readability.
        top = (10, 24, 52)
        bottom = (6, 12, 28)
        for y in range(GAME_H):
            t = y / max(1, GAME_H - 1)
            col = lerp_color(top, bottom, t)
            pygame.draw.line(self.game_surface, col, (0, y), (GAME_W, y))

        shell = pygame.Rect(24, 20, GAME_W - 48, GAME_H - 40)
        draw_rounded_rect(
            self.game_surface,
            (10, 16, 28),
            shell,
            radius=14,
            border=2,
            border_color=(80, 120, 168),
        )

        ticket = self._current_ide_ticket()
        actions = self._ide_actions()
        self.ide_cursor = max(0, min(self.ide_cursor, max(0, len(actions) - 1)))

        title_font = self.fonts.get(14, bold=True)
        info_font = self.fonts.get(10)
        small_font = self.fonts.get(9)

        head = title_font.render("CODELAB IDE // TERMINAL OPS", True, GOLD)
        self.game_surface.blit(head, (shell.x + 14, shell.y + 10))

        right = info_font.render(
            f"Resolved {self.ide_resolved}  Failed {self.ide_failures}",
            True,
            (172, 210, 248),
        )
        self.game_surface.blit(right, (shell.right - right.get_width() - 14, shell.y + 14))

        body = pygame.Rect(shell.x + 10, shell.y + 38, shell.w - 20, shell.h - 62)
        list_rect = pygame.Rect(body.x, body.y, 220, body.h)
        detail_rect = pygame.Rect(list_rect.right + 10, body.y, body.w - list_rect.w - 10, body.h)
        draw_rounded_rect(self.game_surface, (14, 24, 40), list_rect, radius=8, border=1, border_color=(62, 98, 140))
        draw_rounded_rect(self.game_surface, (14, 24, 40), detail_rect, radius=8, border=1, border_color=(62, 98, 140))

        row_h = 20
        for i, item in enumerate(actions[:15]):
            ry = list_rect.y + 8 + i * row_h
            rr = pygame.Rect(list_rect.x + 6, ry, list_rect.w - 12, row_h - 2)
            active = i == self.ide_cursor
            if active:
                draw_rounded_rect(self.game_surface, (36, 74, 124), rr, radius=5, border=1, border_color=(124, 192, 255))
            label = item if len(item) <= 31 else (item[:28] + "...")
            tc = (244, 250, 255) if active else (166, 190, 222)
            self.game_surface.blit(info_font.render(label, True, tc), (rr.x + 7, rr.y + 4))

        x = detail_rect.x + 10
        y = detail_rect.y + 10
        t_title = str(ticket.get("title", "Unknown Ticket"))
        self.game_surface.blit(self.fonts.get(12, bold=True).render(t_title, True, (192, 238, 255)), (x, y))
        y += 18
        tongue = str(ticket.get("tongue", "CA"))
        reward = int(ticket.get("reward_gold", 0))
        self.game_surface.blit(
            small_font.render(f"Tongue {tongue}  Reward +{reward}g", True, (162, 196, 232)),
            (x, y),
        )
        y += 14

        y = draw_text_wrapped(
            self.game_surface,
            str(ticket.get("brief", "")),
            info_font,
            (188, 210, 236),
            pygame.Rect(x, y, detail_rect.w - 20, 70),
        ) + 6

        self.game_surface.blit(info_font.render("Last build result:", True, (154, 186, 220)), (x, y))
        y += 13
        y = draw_text_wrapped(
            self.game_surface,
            self.ide_last_result,
            small_font,
            (170, 202, 236),
            pygame.Rect(x, y, detail_rect.w - 20, 54),
        ) + 6

        self.game_surface.blit(info_font.render("Recent commands:", True, (154, 186, 220)), (x, y))
        y += 13
        if self.ide_history:
            for line in self.ide_history[:5]:
                clipped = line if len(line) <= 44 else line[:41] + "..."
                self.game_surface.blit(small_font.render(f"- {clipped}", True, (140, 174, 208)), (x + 2, y))
                y += 12
        else:
            self.game_surface.blit(small_font.render("- No command history yet", True, (140, 174, 208)), (x + 2, y))

        footer = small_font.render(
            "I/Esc:Close  L:Library  Left/Right:Ticket  Up/Down:Action  Enter:Run",
            True,
            (146, 170, 198),
        )
        self.game_surface.blit(footer, (shell.x + 12, shell.bottom - 14))

    def _draw_library_screen(self) -> None:
        """Draw Morrowind-style readable lore books."""
        top = (36, 28, 18)
        bottom = (20, 14, 8)
        for y in range(GAME_H):
            t = y / max(1, GAME_H - 1)
            col = lerp_color(top, bottom, t)
            pygame.draw.line(self.game_surface, col, (0, y), (GAME_W, y))

        panel = pygame.Rect(18, 14, GAME_W - 36, GAME_H - 28)
        draw_rounded_rect(
            self.game_surface,
            (34, 24, 14),
            panel,
            radius=10,
            border=2,
            border_color=(140, 112, 72),
        )

        title_font = self.fonts.get(14, bold=True)
        info_font = self.fonts.get(10)
        small_font = self.fonts.get(9)

        head = title_font.render("AETHERMOOR LIBRARY // LORE ARCHIVE", True, (255, 220, 150))
        self.game_surface.blit(head, (panel.x + 12, panel.y + 8))
        reads = info_font.render(f"Reads: {self.library_reads}", True, (214, 190, 150))
        self.game_surface.blit(reads, (panel.right - reads.get_width() - 12, panel.y + 14))

        left = pygame.Rect(panel.x + 10, panel.y + 34, 214, panel.h - 50)
        right = pygame.Rect(left.right + 10, left.y, panel.right - left.right - 20, left.h)
        draw_rounded_rect(self.game_surface, (44, 30, 18), left, radius=8, border=1, border_color=(122, 96, 60))
        draw_rounded_rect(self.game_surface, (54, 40, 26), right, radius=8, border=1, border_color=(140, 110, 72))

        # Left: book list.
        row_h = 20
        self.library_index = max(0, min(self.library_index, max(0, len(LORE_BOOKS) - 1)))
        for i, book in enumerate(LORE_BOOKS[:14]):
            ry = left.y + 8 + i * row_h
            rr = pygame.Rect(left.x + 6, ry, left.w - 12, row_h - 2)
            active = i == self.library_index
            if active:
                draw_rounded_rect(self.game_surface, (88, 62, 34), rr, radius=5, border=1, border_color=(210, 170, 110))
            title = book["title"] if len(book["title"]) <= 28 else (book["title"][:25] + "...")
            col = (252, 238, 214) if active else (206, 182, 142)
            self.game_surface.blit(small_font.render(title, True, col), (rr.x + 6, rr.y + 4))

        book = self._current_lore_book()
        x = right.x + 10
        y = right.y + 10
        self.game_surface.blit(self.fonts.get(12, bold=True).render(book.get("title", "Lore Book"), True, (255, 238, 202)), (x, y))
        y += 16
        source = small_font.render(book.get("source", "Source: Local"), True, (196, 168, 128))
        self.game_surface.blit(source, (x, y))
        y += 14

        lines = self._wrap_text_lines(book.get("body", ""), info_font, right.w - 20)
        max_lines = 16
        max_scroll = max(0, len(lines) - max_lines)
        self.library_scroll = max(0, min(self.library_scroll, max_scroll))

        body_y = y + 2
        for line in lines[self.library_scroll:self.library_scroll + max_lines]:
            self.game_surface.blit(info_font.render(line, True, (236, 220, 194)), (x, body_y))
            body_y += 14

        progress = f"Book {self.library_index + 1}/{max(1, len(LORE_BOOKS))}  Line {self.library_scroll + 1}/{max(1, len(lines))}"
        self.game_surface.blit(small_font.render(progress, True, (188, 160, 122)), (x, right.bottom - 28))

        read_state = "Read (Enter)" if book.get("id") in self.library_read_books else "Mark Read (Enter)"
        self.game_surface.blit(small_font.render(read_state, True, (255, 220, 120)), (x, right.bottom - 14))

        footer = small_font.render(
            "L/Esc:Close  Left/Right:Book  Up/Down:Scroll  Enter:Read/Log",
            True,
            (190, 166, 130),
        )
        self.game_surface.blit(footer, (panel.x + 12, panel.bottom - 12))

    def _draw_polypad_screen(self) -> None:
        """Draw the Poly Pad (cellphone / in-game PC) UI."""
        # Sapphire-style blue gradient background.
        top = (12, 26, 62)
        bottom = (8, 12, 28)
        for y in range(GAME_H):
            t = y / max(1, GAME_H - 1)
            col = lerp_color(top, bottom, t)
            pygame.draw.line(self.game_surface, col, (0, y), (GAME_W, y))

        # Device frame.
        outer = pygame.Rect(38, 18, GAME_W - 76, GAME_H - 36)
        draw_rounded_rect(self.game_surface, (18, 24, 38), outer, radius=16, border=2, border_color=(90, 112, 148))
        inner = pygame.Rect(outer.x + 10, outer.y + 10, outer.w - 20, outer.h - 20)
        draw_rounded_rect(self.game_surface, (10, 16, 26), inner, radius=12, border=1, border_color=(64, 88, 124))

        app = POLYPAD_APPS[self.polypad_tab]
        unread = self._polypad_unread_count()

        # Header.
        title_font = self.fonts.get(14, bold=True)
        sub_font = self.fonts.get(9)
        title = title_font.render("POLY PAD // FIELD LINK", True, GOLD)
        self.game_surface.blit(title, (inner.x + 14, inner.y + 10))
        right = sub_font.render(f"App: {app}   Unread: {unread}", True, (180, 205, 240))
        self.game_surface.blit(right, (inner.right - right.get_width() - 14, inner.y + 16))

        # Tabs.
        tab_y = inner.y + 36
        tab_w = (inner.w - 20) // len(POLYPAD_APPS)
        for i, name in enumerate(POLYPAD_APPS):
            tx = inner.x + 10 + i * tab_w
            tr = pygame.Rect(tx, tab_y, tab_w - 4, 22)
            active = i == self.polypad_tab
            fill = (34, 66, 108) if active else (20, 30, 48)
            border = (110, 180, 245) if active else (56, 74, 102)
            draw_rounded_rect(self.game_surface, fill, tr, radius=6, border=1, border_color=border)
            tc = (235, 245, 255) if active else (140, 162, 196)
            lbl = sub_font.render(name, True, tc)
            self.game_surface.blit(lbl, (tr.centerx - lbl.get_width() // 2, tr.y + 6))

        entries = self._polypad_entries()
        if entries:
            self.polypad_cursor = max(0, min(self.polypad_cursor, len(entries) - 1))
        else:
            self.polypad_cursor = 0

        # Left list panel.
        list_rect = pygame.Rect(inner.x + 12, inner.y + 64, 220, inner.h - 92)
        detail_rect = pygame.Rect(list_rect.right + 10, list_rect.y, inner.right - list_rect.right - 22, list_rect.h)
        draw_rounded_rect(self.game_surface, (14, 24, 40), list_rect, radius=8, border=1, border_color=(66, 96, 132))
        draw_rounded_rect(self.game_surface, (14, 24, 40), detail_rect, radius=8, border=1, border_color=(66, 96, 132))

        item_font = self.fonts.get(10)
        row_h = 20
        for i, line in enumerate(entries[:14]):
            ry = list_rect.y + 8 + i * row_h
            rr = pygame.Rect(list_rect.x + 6, ry - 1, list_rect.w - 12, row_h - 2)
            active = i == self.polypad_cursor
            if active:
                draw_rounded_rect(self.game_surface, (36, 74, 126), rr, radius=5, border=1, border_color=(128, 192, 255))
            txt = line if len(line) <= 30 else (line[:27] + "...")
            color = (244, 250, 255) if active else (164, 188, 220)
            self.game_surface.blit(item_font.render(txt, True, color), (rr.x + 8, rr.y + 4))

        # Right detail panel by app.
        info_font = self.fonts.get(10)
        x = detail_rect.x + 10
        y = detail_rect.y + 10

        if app == "Home":
            status_line = (
                f"Class {self.player_class} | Partner {self.partner_name} | "
                f"Rep {self.reputation_points:+d}"
            )
            self.game_surface.blit(self.fonts.get(11, bold=True).render("FIELD SUMMARY", True, (186, 230, 255)), (x, y))
            y += 18
            y = draw_text_wrapped(
                self.game_surface,
                status_line,
                info_font,
                (198, 214, 236),
                pygame.Rect(x, y, detail_rect.w - 20, 40),
            ) + 4
            y = draw_text_wrapped(
                self.game_surface,
                "Use Contacts for calls, Messages for intel, Missions for objectives, PC Box for party reviews, and IDE for coding mini-games.",
                info_font,
                (178, 198, 226),
                pygame.Rect(x, y, detail_rect.w - 20, 72),
            ) + 8
            self.game_surface.blit(info_font.render("Core Loop Mode: SIMPLE", True, (120, 255, 172)), (x, y))
            y += 14
            self.game_surface.blit(info_font.render("Advanced Systems: MINI-GAMES", True, (255, 214, 120)), (x, y))
            y += 16
            if self.polypad_call_log:
                self.game_surface.blit(info_font.render("Recent calls:", True, (160, 186, 220)), (x, y))
                y += 14
                for call in self.polypad_call_log[:4]:
                    self.game_surface.blit(info_font.render(f"- {call}", True, (140, 170, 206)), (x + 4, y))
                    y += 13

        elif app == "Contacts":
            if self.polypad_contacts:
                c = self.polypad_contacts[self.polypad_cursor]
                self.game_surface.blit(self.fonts.get(11, bold=True).render(c["name"], True, (194, 238, 255)), (x, y))
                y += 18
                self.game_surface.blit(info_font.render(f"Status: {c['status']}", True, (170, 200, 232)), (x, y))
                y += 14
                self.game_surface.blit(info_font.render(f"Last call: {c['last_call']}", True, (150, 182, 216)), (x, y))
                y += 18
                y = draw_text_wrapped(
                    self.game_surface,
                    "Press Enter to call. Calls add tactical hints to Messages without interrupting the core RPG flow.",
                    info_font,
                    (178, 198, 226),
                    pygame.Rect(x, y, detail_rect.w - 20, 70),
                ) + 4

        elif app == "Messages":
            if self.polypad_messages:
                m = self.polypad_messages[self.polypad_cursor]
                subject = f"{m['from']} // {m['subject']}"
                self.game_surface.blit(self.fonts.get(11, bold=True).render(subject[:34], True, (194, 238, 255)), (x, y))
                y += 18
                unread_tag = "UNREAD" if m.get("unread", False) else "READ"
                tag_color = (255, 224, 116) if m.get("unread", False) else (120, 206, 154)
                self.game_surface.blit(info_font.render(f"{unread_tag}  @ {m.get('time', '-')}", True, tag_color), (x, y))
                y += 16
                draw_text_wrapped(
                    self.game_surface,
                    m.get("body", ""),
                    info_font,
                    (186, 208, 236),
                    pygame.Rect(x, y, detail_rect.w - 20, detail_rect.h - 60),
                )

        elif app == "Missions":
            if self.polypad_missions:
                mission = self.polypad_missions[self.polypad_cursor]
                self.game_surface.blit(self.fonts.get(11, bold=True).render(mission["title"], True, (194, 238, 255)), (x, y))
                y += 18
                st = mission.get("status", "queued")
                st_color = (120, 255, 170) if st == "active" else ((255, 220, 120) if st == "queued" else (130, 160, 186))
                self.game_surface.blit(info_font.render(f"Status: {st.upper()}", True, st_color), (x, y))
                y += 16
                y = draw_text_wrapped(
                    self.game_surface,
                    mission.get("desc", ""),
                    info_font,
                    (186, 208, 236),
                    pygame.Rect(x, y, detail_rect.w - 20, 84),
                ) + 6
                active = sum(1 for m in self.polypad_missions if m.get("status") == "active")
                done = sum(1 for m in self.polypad_missions if m.get("status") == "done")
                total = max(1, len(self.polypad_missions))
                self.game_surface.blit(info_font.render("Mission Progress", True, (156, 188, 220)), (x, y))
                y += 12
                draw_bar(self.game_surface, x, y, detail_rect.w - 24, 10, done / total, (90, 220, 150))
                y += 14
                self.game_surface.blit(info_font.render(f"Active {active} / Done {done} / Total {total}", True, (144, 176, 206)), (x, y))

        elif app == "PC Box":
            if self.polypad_cursor == 0:
                self.game_surface.blit(
                    self.fonts.get(11, bold=True).render("Guild Computer", True, (194, 238, 255)),
                    (x, y),
                )
                y += 18
                y = draw_text_wrapped(
                    self.game_surface,
                    "Sit at the terminal to enter CodeLab IDE. Solve coding tickets for rewards and training data.",
                    info_font,
                    (186, 208, 236),
                    pygame.Rect(x, y, detail_rect.w - 20, 76),
                ) + 6
                self.game_surface.blit(info_font.render("Press Enter to launch IDE.", True, (255, 220, 120)), (x, y))
            elif self.polypad_cursor == 1:
                self.game_surface.blit(
                    self.fonts.get(11, bold=True).render("Lore Library", True, (194, 238, 255)),
                    (x, y),
                )
                y += 18
                y = draw_text_wrapped(
                    self.game_surface,
                    "Read long-form field books sourced from Obsidian canon notes. First read grants small rewards.",
                    info_font,
                    (186, 208, 236),
                    pygame.Rect(x, y, detail_rect.w - 20, 76),
                ) + 6
                self.game_surface.blit(info_font.render("Press Enter to open books.", True, (255, 220, 120)), (x, y))
            elif self.party and (self.polypad_cursor - 2) < len(self.party):
                c = self.party[self.polypad_cursor - 2]
                self.game_surface.blit(self.fonts.get(11, bold=True).render(c.name, True, (194, 238, 255)), (x, y))
                y += 18
                self.game_surface.blit(info_font.render(f"Lv {c.stats.level}  {c.tongue_affinity.value}", True, (172, 205, 236)), (x, y))
                y += 16
                hp_ratio = c.stats.hp / max(1, c.stats.max_hp)
                mp_ratio = c.stats.mp / max(1, c.stats.max_mp)
                self.game_surface.blit(info_font.render("HP", True, (160, 188, 220)), (x, y))
                y += 11
                draw_bar(self.game_surface, x, y, detail_rect.w - 24, 10, hp_ratio, (84, 226, 136))
                y += 16
                self.game_surface.blit(info_font.render("MP", True, (160, 188, 220)), (x, y))
                y += 11
                draw_bar(self.game_surface, x, y, detail_rect.w - 24, 8, mp_ratio, (96, 156, 246))
                y += 16
                at = c.stats.attack
                df = c.stats.defense
                sp = c.stats.speed
                ws = c.stats.wisdom
                self.game_surface.blit(info_font.render(f"ATK {at}  DEF {df}  SPD {sp}  WIS {ws}", True, (172, 205, 236)), (x, y))
                y += 16
                self.game_surface.blit(
                    info_font.render("PC Box mirrors Ruby/Sapphire quick-inspect flow.", True, (140, 176, 206)),
                    (x, y),
                )
            else:
                self.game_surface.blit(info_font.render("No party members in PC Box.", True, (172, 205, 236)), (x, y))

        elif app == "IDE":
            self.game_surface.blit(self.fonts.get(11, bold=True).render("CodeLab Bridge", True, (194, 238, 255)), (x, y))
            y += 18
            y = draw_text_wrapped(
                self.game_surface,
                "Run coding mini-game tickets from here. Keep overworld simple; send complex systems into IDE runs.",
                info_font,
                (186, 208, 236),
                pygame.Rect(x, y, detail_rect.w - 20, 74),
            ) + 8
            self.game_surface.blit(info_font.render(f"Resolved: {self.ide_resolved}  Failed: {self.ide_failures}", True, (166, 196, 228)), (x, y))
            y += 16
            self.game_surface.blit(info_font.render(f"Last build: {self.ide_last_result[:48]}", True, (140, 176, 206)), (x, y))
            y += 14
            self.game_surface.blit(info_font.render(f"Lore books read: {self.library_reads}", True, (140, 176, 206)), (x, y))

        # Footer controls.
        quick_tabs = min(len(POLYPAD_APPS), 9)
        footer = self.fonts.get(9).render(
            f"P/Esc:Close  Left/Right:App  Up/Down:Select  Enter:Action  1-{quick_tabs}:Quick Tab",
            True,
            (148, 172, 202),
        )
        self.game_surface.blit(footer, (inner.x + 12, inner.bottom - 16))

    # ------------------------------------------------------------------
    # Dialogue Screen (PivotKnowledge NPC)
    # ------------------------------------------------------------------
    def _draw_dialogue_screen(self) -> None:
        """Draw the NPC dialogue screen with PivotKnowledge pivots."""
        self.game_surface.fill(BG_COLORS.get("aethermoor", (32, 24, 72)))

        npc_id = self.dialogue_npc_id
        char = self.cast.get(npc_id)
        npc_name = char.name if char else npc_id.capitalize()
        tongue = char.tongue_affinity.value if char else "KO"
        tc = TONGUE_COLORS.get(tongue, (200, 200, 200))

        # NPC portrait (left side)
        if char:
            portrait = self.sprites.get_scaled(char, 96)
            self.game_surface.blit(portrait, (30, 40))

        # NPC name badge
        name_font = self.fonts.get(14, bold=True)
        name_surf = name_font.render(npc_name, True, tc)
        self.game_surface.blit(name_surf, (140, 40))

        tongue_font = self.fonts.get(10)
        tongue_name = TONGUE_FULL_NAMES.get(tongue, tongue)
        self.game_surface.blit(tongue_font.render(f"[{tongue_name}]", True, DIM_TEXT), (140, 60))

        # Response box
        resp_box = pygame.Surface((GAME_W - 30, 140), pygame.SRCALPHA)
        resp_box.fill((10, 10, 26, 220))
        self.game_surface.blit(resp_box, (15, 100))
        pygame.draw.rect(self.game_surface, tc, (15, 100, GAME_W - 30, 140), 1, border_radius=4)

        resp_font = self.fonts.get(12)
        # Word-wrap response
        words = self.dialogue_response.split()
        lines: List[str] = []
        current_line = ""
        for word in words:
            test = current_line + " " + word if current_line else word
            if resp_font.size(test)[0] < GAME_W - 60:
                current_line = test
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for i, line in enumerate(lines[:6]):
            self.game_surface.blit(resp_font.render(line, True, TEXT_COLOR), (25, 110 + i * 18))

        # Sacred language flavor text
        if self.dialogue_sacred_text:
            sacred_font = self.fonts.get(9)
            sacred_surf = sacred_font.render(f"[{tongue}] {self.dialogue_sacred_text}", True, tc)
            sacred_surf.set_alpha(140)
            self.game_surface.blit(sacred_surf, (25, 225))

        # Pivot choices
        pivot_y = 260
        pivot_font = self.fonts.get(12)
        header_font = self.fonts.get(11, bold=True)
        self.game_surface.blit(header_font.render("Topics:", True, GOLD), (20, pivot_y))
        pivot_y += 20

        for i, (topic_id, topic_name) in enumerate(self.dialogue_pivots[:6]):
            is_sel = (i == self.dialogue_pivot_cursor)
            color = CHOICE_HIGHLIGHT if is_sel else TEXT_COLOR
            prefix = "> " if is_sel else "  "
            self.game_surface.blit(
                pivot_font.render(f"{prefix}{topic_name}", True, color),
                (28, pivot_y + i * 22),
            )

        # Controls
        hint_font = self.fonts.get(9)
        self.game_surface.blit(
            hint_font.render("Up/Down:Select  Enter:Pivot  Esc:Leave", True, DIM_TEXT),
            (8, GAME_H - 16),
        )

    # ------------------------------------------------------------------
    # Battle Screen
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Evolution System
    # ------------------------------------------------------------------
    EVO_THRESHOLDS = {
        EvoStage.FRESH:    (0.5,  1, 0.0),   # (total_prof, tongues_needed, min_tongue)
        EvoStage.ROOKIE:   (2.0,  1, 0.4),
        EvoStage.CHAMPION: (3.5,  2, 0.6),
        EvoStage.ULTIMATE: (5.0,  3, 0.8),
        EvoStage.MEGA:     (999,  6, 1.0),    # Ultra — unreachable normally
    }
    EVO_ORDER = [EvoStage.FRESH, EvoStage.ROOKIE, EvoStage.CHAMPION,
                 EvoStage.ULTIMATE, EvoStage.MEGA, EvoStage.ULTRA]

    def _check_evolution(self) -> None:
        """Check if any party member is ready to evolve after battle."""
        for char in self.party:
            if char.is_enemy:
                continue
            stage_idx = self.EVO_ORDER.index(char.evo_stage) if char.evo_stage in self.EVO_ORDER else -1
            if stage_idx < 0 or stage_idx >= len(self.EVO_ORDER) - 1:
                continue
            threshold = self.EVO_THRESHOLDS.get(char.evo_stage)
            if not threshold:
                continue
            total_prof = sum(char.stats.tongue_prof.values())
            tongues_above = sum(1 for v in char.stats.tongue_prof.values() if v >= threshold[2])
            if total_prof >= threshold[0] and tongues_above >= threshold[1]:
                # Trigger evolution!
                old_stage = char.evo_stage
                new_stage = self.EVO_ORDER[stage_idx + 1]
                self._evo_char = char
                self._evo_from = old_stage.value
                self._evo_to = new_stage.value
                self._evo_timer = 0.0
                self._evo_phase = 0
                self._evo_return_phase = self.game_phase
                self.game_phase = "evolution"
                # Apply evolution
                char.evo_stage = new_stage
                # Stat boost on evolution
                boost = 1 + stage_idx * 0.15
                char.stats.max_hp = int(char.stats.max_hp * boost)
                char.stats.hp = char.stats.max_hp
                char.stats.max_mp = int(char.stats.max_mp * boost)
                char.stats.mp = char.stats.max_mp
                char.stats.attack = int(char.stats.attack * boost)
                char.stats.defense = int(char.stats.defense * boost)
                # Record training data
                self.exporter.record_evolution(
                    char.name, self._evo_from, self._evo_to, char.stats.tongue_prof
                )
                self.n8n_bus.emit(
                    GameEventType.COMPANION_EVOLVED,
                    name=char.name, from_stage=self._evo_from,
                    to_stage=self._evo_to,
                )
                break  # One evolution per battle

    def _draw_evolution_screen(self) -> None:
        """Draw Digimon-style evolution sequence."""
        self._evo_timer += 1.0 / FPS_CAP
        char = self._evo_char
        if not char:
            self.game_phase = self._evo_return_phase
            return

        tc = TONGUE_COLORS.get(char.tongue_affinity.value, GOLD)
        t = self._evo_timer

        # Dark background with pulsing energy
        self.game_surface.fill((8, 8, 16))

        # Phase 0: Glow buildup (0-2s)
        if t < 2.0:
            self._evo_phase = 0
            alpha = min(1.0, t / 2.0)
            # Pulsing concentric rings
            for ring in range(5):
                radius = int(40 + ring * 30 + math.sin(t * 4 + ring) * 10)
                ring_alpha = int(alpha * 120 * (1 - ring / 5))
                ring_surf = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (*tc, ring_alpha),
                                   (GAME_W // 2, GAME_H // 2 - 40), radius, 2)
                self.game_surface.blit(ring_surf, (0, 0))
            # Character sprite pulsing
            scale = int(64 + math.sin(t * 6) * 8)
            sprite = self.sprites.get_scaled(char, scale)
            sx = GAME_W // 2 - scale // 2
            sy = GAME_H // 2 - scale // 2 - 40
            self.game_surface.blit(sprite, (sx, sy))
            # "is evolving..." text
            evo_font = self.fonts.get(14, bold=True)
            text = evo_font.render(f"{char.name} is evolving...", True, TEXT_COLOR)
            self.game_surface.blit(text, (GAME_W // 2 - text.get_width() // 2, GAME_H // 2 + 60))

        # Phase 1: Transform flash (2-3s)
        elif t < 3.0:
            self._evo_phase = 1
            flash_alpha = int(255 * (1 - (t - 2.0)))
            flash = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            flash.fill((*tc, flash_alpha))
            self.game_surface.blit(flash, (0, 0))
            # Larger sprite emerging
            scale = int(80 + (t - 2.0) * 20)
            sprite = self.sprites.get_scaled(char, scale)
            sx = GAME_W // 2 - scale // 2
            sy = GAME_H // 2 - scale // 2 - 40
            self.game_surface.blit(sprite, (sx, sy))

        # Phase 2: Reveal (3-5s)
        elif t < 5.0:
            self._evo_phase = 2
            # Particle burst
            for _ in range(3):
                px = GAME_W // 2 + random.randint(-80, 80)
                py = GAME_H // 2 - 40 + random.randint(-60, 60)
                pygame.draw.circle(self.game_surface, tc, (px, py), random.randint(1, 4))
            # Final sprite
            sprite = self.sprites.get_scaled(char, 96)
            sx = GAME_W // 2 - 48
            sy = GAME_H // 2 - 88
            self.game_surface.blit(sprite, (sx, sy))
            # New stage name
            stage_font = self.fonts.get(18, bold=True)
            stage_text = stage_font.render(f"{self._evo_to}!", True, GOLD)
            self.game_surface.blit(stage_text, (GAME_W // 2 - stage_text.get_width() // 2, GAME_H // 2 + 40))
            # Congratulations
            cong_font = self.fonts.get(12)
            cong = cong_font.render(
                f"{char.name} evolved from {self._evo_from} to {self._evo_to}!",
                True, TEXT_COLOR,
            )
            self.game_surface.blit(cong, (GAME_W // 2 - cong.get_width() // 2, GAME_H // 2 + 70))

        # Phase 3: Done — wait for input
        else:
            self._evo_phase = 3
            sprite = self.sprites.get_scaled(char, 96)
            self.game_surface.blit(sprite, (GAME_W // 2 - 48, GAME_H // 2 - 88))
            stage_font = self.fonts.get(18, bold=True)
            stage_text = stage_font.render(f"{self._evo_to}!", True, GOLD)
            self.game_surface.blit(stage_text, (GAME_W // 2 - stage_text.get_width() // 2, GAME_H // 2 + 40))
            prompt = self.fonts.get(11)
            self.game_surface.blit(
                prompt.render("Press ENTER to continue", True, DIM_TEXT),
                (GAME_W // 2 - 70, GAME_H // 2 + 90),
            )

    # ------------------------------------------------------------------
    # Gacha Pull System
    # ------------------------------------------------------------------
    GACHA_RARITY_NAMES = {1: "Common", 2: "Uncommon", 3: "Rare", 4: "Epic", 5: "Legendary"}
    GACHA_RARITY_COLORS = {
        1: (180, 180, 180), 2: (80, 200, 80), 3: (80, 140, 255),
        4: (200, 80, 255), 5: (255, 215, 80),
    }

    def _start_gacha_pull(self) -> None:
        """Initiate a gacha pull sequence."""
        # Rarity roll (weighted)
        roll = random.random()
        if roll < 0.40:
            rarity = 1
        elif roll < 0.70:
            rarity = 2
        elif roll < 0.88:
            rarity = 3
        elif roll < 0.97:
            rarity = 4
        else:
            rarity = 5

        tongue = random.choice(list(Tongue))
        # Stats scale with rarity
        base_hp = 30 + rarity * 15
        base_atk = 5 + rarity * 3
        base_def = 4 + rarity * 2
        base_spd = 5 + rarity * 2
        base_wis = 4 + rarity * 3
        # Pick a random name
        prefixes = ["Aether", "Rune", "Spark", "Shadow", "Crystal", "Flux", "Void", "Nova"]
        suffixes = ["ling", "maw", "crest", "wisp", "fin", "talon", "shard", "core"]
        name = random.choice(prefixes) + random.choice(suffixes)

        evo = EvoStage.FRESH if rarity <= 2 else (EvoStage.ROOKIE if rarity <= 4 else EvoStage.CHAMPION)
        recruit = Character(
            name=name,
            title=f"{self.GACHA_RARITY_NAMES[rarity]} Summon",
            tongue_affinity=tongue,
            evo_stage=evo,
            stats=Stats(hp=base_hp, max_hp=base_hp, mp=base_hp // 2, max_mp=base_hp // 2,
                        attack=base_atk, defense=base_def, speed=base_spd, wisdom=base_wis),
            spells=[],
            is_enemy=False,
        )

        self._gacha_result = recruit
        self._gacha_rarity = rarity
        self._gacha_timer = 0.0
        self._gacha_phase = 0
        self._gacha_return_phase = self.game_phase
        self.game_phase = "gacha"

        self.n8n_bus.emit(
            GameEventType.GACHA_PULL,
            name=name, tongue=tongue.value, rarity=rarity, party_size=len(self.party),
        )
        self.sft_count += 1

    def _draw_gacha_screen(self) -> None:
        """Draw gacha pull animation."""
        self._gacha_timer += 1.0 / FPS_CAP
        t = self._gacha_timer
        recruit = self._gacha_result
        rarity = self._gacha_rarity

        self.game_surface.fill((8, 6, 18))
        rc = self.GACHA_RARITY_COLORS.get(rarity, (180, 180, 180))

        # Phase 0: Swirling energy (0-1.5s)
        if t < 1.5:
            self._gacha_phase = 0
            # Six tongue-colored particles swirling
            for i, tongue_code in enumerate(["KO", "AV", "RU", "CA", "UM", "DR"]):
                angle = t * 3 + i * (math.pi * 2 / 6)
                radius = 80 + math.sin(t * 5) * 20
                px = int(GAME_W // 2 + math.cos(angle) * radius)
                py = int(GAME_H // 2 - 20 + math.sin(angle) * radius * 0.6)
                tc = TONGUE_COLORS.get(tongue_code, (128, 128, 128))
                pygame.draw.circle(self.game_surface, tc, (px, py), 6)
                # Trail
                for j in range(3):
                    trail_angle = angle - j * 0.2
                    trail_r = radius - j * 8
                    tx = int(GAME_W // 2 + math.cos(trail_angle) * trail_r)
                    ty = int(GAME_H // 2 - 20 + math.sin(trail_angle) * trail_r * 0.6)
                    pygame.draw.circle(self.game_surface, tc, (tx, ty), 3 - j)
            # Central orb growing
            orb_size = int(10 + t * 20)
            orb_surf = pygame.Surface((orb_size * 2, orb_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(orb_surf, (*rc, 150), (orb_size, orb_size), orb_size)
            self.game_surface.blit(orb_surf, (GAME_W // 2 - orb_size, GAME_H // 2 - 20 - orb_size))
            # Title
            title = self.fonts.get(14, bold=True)
            self.game_surface.blit(
                title.render("Summoning...", True, TEXT_COLOR),
                (GAME_W // 2 - 50, GAME_H - 60),
            )

        # Phase 1: Crack + rarity flash (1.5-2.5s)
        elif t < 2.5:
            self._gacha_phase = 1
            flash_t = (t - 1.5) / 1.0
            # Screen flash for high rarity
            if rarity >= 4:
                flash_alpha = int(200 * (1 - flash_t))
                flash = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
                flash.fill((*rc, flash_alpha))
                self.game_surface.blit(flash, (0, 0))
            # Stars appearing one by one
            stars_shown = min(rarity, int(flash_t * rarity * 2) + 1)
            star_font = self.fonts.get(18, bold=True)
            star_w = rarity * 22
            start_x = GAME_W // 2 - star_w // 2
            for s in range(stars_shown):
                sx = start_x + s * 22
                self.game_surface.blit(
                    star_font.render("*", True, rc), (sx, GAME_H // 2 - 60)
                )
            # Rarity name
            rarity_name = self.GACHA_RARITY_NAMES.get(rarity, "?")
            rn_font = self.fonts.get(16, bold=True)
            rn_surf = rn_font.render(rarity_name, True, rc)
            self.game_surface.blit(rn_surf, (GAME_W // 2 - rn_surf.get_width() // 2, GAME_H // 2 - 30))

        # Phase 2: Character reveal (2.5-4s)
        elif t < 4.0:
            self._gacha_phase = 2
            if recruit:
                sprite = self.sprites.get_scaled(recruit, 80)
                self.game_surface.blit(sprite, (GAME_W // 2 - 40, GAME_H // 2 - 70))
                # Stars
                star_font = self.fonts.get(16, bold=True)
                star_str = "*" * rarity
                self.game_surface.blit(
                    star_font.render(star_str, True, rc),
                    (GAME_W // 2 - len(star_str) * 6, GAME_H // 2 - 90),
                )
                # Name + info
                nf = self.fonts.get(14, bold=True)
                name_surf = nf.render(recruit.name, True, TEXT_COLOR)
                self.game_surface.blit(name_surf, (GAME_W // 2 - name_surf.get_width() // 2, GAME_H // 2 + 20))
                info_font = self.fonts.get(11)
                tongue_name = TONGUE_NAMES.get(recruit.tongue_affinity, recruit.tongue_affinity.value)
                info = info_font.render(
                    f"[{recruit.evo_stage.value}] {tongue_name}  ATK:{recruit.stats.attack} DEF:{recruit.stats.defense}",
                    True, DIM_TEXT,
                )
                self.game_surface.blit(info, (GAME_W // 2 - info.get_width() // 2, GAME_H // 2 + 42))

        # Phase 3: Done — wait for input
        else:
            self._gacha_phase = 3
            if recruit:
                sprite = self.sprites.get_scaled(recruit, 80)
                self.game_surface.blit(sprite, (GAME_W // 2 - 40, GAME_H // 2 - 70))
                star_font = self.fonts.get(16, bold=True)
                self.game_surface.blit(
                    star_font.render("*" * rarity, True, rc),
                    (GAME_W // 2 - rarity * 6, GAME_H // 2 - 90),
                )
                nf = self.fonts.get(14, bold=True)
                name_surf = nf.render(recruit.name, True, TEXT_COLOR)
                self.game_surface.blit(name_surf, (GAME_W // 2 - name_surf.get_width() // 2, GAME_H // 2 + 20))
                # Add to party prompt
                prompt_font = self.fonts.get(12)
                if len(self.party) < 6:
                    self.game_surface.blit(
                        prompt_font.render("Press ENTER to add to party", True, (80, 255, 120)),
                        (GAME_W // 2 - 90, GAME_H // 2 + 70),
                    )
                else:
                    self.game_surface.blit(
                        prompt_font.render("Party full! Press ENTER to release", True, (255, 120, 80)),
                        (GAME_W // 2 - 110, GAME_H // 2 + 70),
                    )
                self.game_surface.blit(
                    self.fonts.get(10).render("Press ESC to skip", True, DIM_TEXT),
                    (GAME_W // 2 - 45, GAME_H // 2 + 90),
                )

    # ------------------------------------------------------------------
    # Pokemon Sapphire-style Battle UI helpers
    # ------------------------------------------------------------------
    def _draw_sapphire_hp_box(
        self, x: int, y: int, w: int, char: Character,
        show_hp_text: bool = False, show_xp: bool = False,
        is_enemy: bool = False,
    ) -> None:
        """Draw a Pokemon Sapphire-style info box for a character."""
        h = 42 if not show_xp else 52
        if show_hp_text:
            h += 12

        # Box background — Sapphire uses white/cream with dark border
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((248, 248, 240, 230))
        self.game_surface.blit(box, (x, y))
        pygame.draw.rect(self.game_surface, (40, 40, 48), (x, y, w, h), 2, border_radius=3)

        # Name and level
        nf = self.fonts.get(11, bold=True)
        name_surf = nf.render(char.name, True, (32, 32, 40))
        self.game_surface.blit(name_surf, (x + 6, y + 3))
        lvl = self.fonts.get(10)
        lv_surf = lvl.render(f"Lv{char.stats.level}", True, (80, 80, 96))
        self.game_surface.blit(lv_surf, (x + w - lv_surf.get_width() - 6, y + 4))

        # Tongue icon (colored dot)
        tc = TONGUE_COLORS.get(char.tongue_affinity.value, (128, 128, 128))
        pygame.draw.circle(self.game_surface, tc, (x + w - 50, y + 10), 4)

        # HP label
        hp_label = self.fonts.get(9, bold=True)
        self.game_surface.blit(hp_label.render("HP", True, (255, 180, 40)), (x + 6, y + 20))

        # Curved HP bar (Sapphire style — green/yellow/red)
        bar_x = x + 24
        bar_y = y + 22
        bar_w = w - 32
        bar_h = 6
        hp_ratio = char.stats.hp / char.stats.max_hp if char.stats.max_hp > 0 else 0
        # Background
        pygame.draw.rect(self.game_surface, (56, 56, 64), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        # Fill
        if hp_ratio > 0:
            if hp_ratio > 0.5:
                fill_color = (80, 200, 72)  # Sapphire green
            elif hp_ratio > 0.25:
                fill_color = (248, 184, 24)  # Sapphire yellow
            else:
                fill_color = (240, 64, 56)   # Sapphire red
            fill_w = max(1, int(bar_w * hp_ratio))
            pygame.draw.rect(self.game_surface, fill_color, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

        # HP numbers (player only)
        if show_hp_text:
            hp_num = self.fonts.get(10)
            hp_text = hp_num.render(f"{char.stats.hp}/{char.stats.max_hp}", True, (40, 40, 48))
            self.game_surface.blit(hp_text, (x + w - hp_text.get_width() - 6, y + 30))

        # XP bar (player only)
        if show_xp:
            xp_y = y + h - 10
            self.game_surface.blit(self.fonts.get(8).render("EXP", True, (80, 96, 128)), (x + 4, xp_y - 2))
            xp_bar_x = x + 28
            xp_bar_w = w - 36
            total_prof = sum(char.stats.tongue_prof.values())
            xp_ratio = (total_prof % 1.0) if total_prof > 0 else 0
            pygame.draw.rect(self.game_surface, (56, 56, 80), (xp_bar_x, xp_y, xp_bar_w, 4), border_radius=2)
            if xp_ratio > 0:
                pygame.draw.rect(self.game_surface, (72, 136, 248),
                                 (xp_bar_x, xp_y, max(1, int(xp_bar_w * xp_ratio)), 4), border_radius=2)

    def _draw_ground_platform(self, cx: int, cy: int, w: int, h: int, is_enemy: bool = False) -> None:
        """Draw a Pokemon Sapphire-style grass/ground ellipse platform."""
        if is_enemy:
            # Enemy platform — greenish grass
            color_top = (88, 160, 72)
            color_dark = (56, 112, 48)
        else:
            # Player platform — darker earth
            color_top = (168, 136, 96)
            color_dark = (120, 96, 64)
        # Shadow
        pygame.draw.ellipse(self.game_surface, (24, 24, 32), (cx - w // 2, cy + 2, w, h))
        # Main platform
        pygame.draw.ellipse(self.game_surface, color_dark, (cx - w // 2, cy, w, h))
        pygame.draw.ellipse(self.game_surface, color_top, (cx - w // 2, cy - 2, w, h - 4))

    def _draw_battle_screen(self) -> None:
        """Draw a Pokemon Sapphire-style battle screen."""
        # --- Background: sky gradient (Sapphire blue-grey) ---
        for y in range(GAME_H):
            ratio = y / GAME_H
            if ratio < 0.6:
                # Sky gradient
                r = int(120 + ratio * 40)
                g = int(152 + ratio * 30)
                b = int(200 - ratio * 20)
            else:
                # Ground gradient
                ground_r = (ratio - 0.6) / 0.4
                r = int(88 + ground_r * 40)
                g = int(136 + ground_r * 20)
                b = int(72 + ground_r * 20)
            pygame.draw.line(self.game_surface, (r, g, b), (0, y), (GAME_W, y))

        # --- Enemy platform (top-right) ---
        enemy_plat_cx = GAME_W - 160
        enemy_plat_cy = 170
        self._draw_ground_platform(enemy_plat_cx, enemy_plat_cy, 160, 32, is_enemy=True)

        # --- Player platform (bottom-left) ---
        player_plat_cx = 140
        player_plat_cy = 310
        self._draw_ground_platform(player_plat_cx, player_plat_cy, 180, 36, is_enemy=False)

        # --- Draw enemy sprites (on platform) ---
        for i, enemy in enumerate(self.battle.enemies):
            ex = enemy_plat_cx - 32 + i * 70
            ey = enemy_plat_cy - 72
            sprite = self.sprites.get_scaled(enemy, 64)
            if enemy.stats.hp > 0:
                self.game_surface.blit(sprite, (ex, ey))
            else:
                faded = sprite.copy()
                faded.set_alpha(60)
                self.game_surface.blit(faded, (ex, ey + 16))
            # Target indicator
            if self.battle.selecting_target and i == self.battle.selected_target:
                # Bouncing arrow above enemy
                bounce = int(math.sin(time.time() * 6) * 4)
                arrow_pts = [(ex + 28, ey - 12 + bounce), (ex + 20, ey - 4 + bounce), (ex + 36, ey - 4 + bounce)]
                pygame.draw.polygon(self.game_surface, CHOICE_HIGHLIGHT, arrow_pts)

        # --- Draw active party member sprite (on player platform) ---
        if self.battle.party:
            active_idx = min(self.battle.turn_index, len(self.battle.party) - 1)
            active_char = self.battle.party[active_idx]
            sprite = self.sprites.get_scaled(active_char, 80)
            if active_char.stats.hp > 0:
                self.game_surface.blit(sprite, (player_plat_cx - 40, player_plat_cy - 88))
            else:
                faded = sprite.copy()
                faded.set_alpha(60)
                self.game_surface.blit(faded, (player_plat_cx - 40, player_plat_cy - 70))

        # --- Enemy info box (top-left, Sapphire style) ---
        if self.battle.enemies:
            primary_enemy = self.battle.enemies[0]
            self._draw_sapphire_hp_box(10, 16, 200, primary_enemy, is_enemy=True)

        # --- Player info box (bottom-right, Sapphire style) ---
        if self.battle.party:
            active = self.battle.party[min(self.battle.turn_index, len(self.battle.party) - 1)]
            self._draw_sapphire_hp_box(
                GAME_W - 230, 260, 220, active,
                show_hp_text=True, show_xp=True,
            )

        # --- Party mini-portraits (bottom-left corner, small) ---
        mini_y = GAME_H - 64
        for i, char in enumerate(self.battle.party[:6]):
            mx = 8 + i * 28
            mini = self.sprites.get_scaled(char, 24)
            if char.stats.hp <= 0:
                mini.set_alpha(80)
            self.game_surface.blit(mini, (mx, mini_y))
            # Tiny HP pip
            pip_ratio = char.stats.hp / char.stats.max_hp if char.stats.max_hp > 0 else 0
            pip_color = (80, 200, 72) if pip_ratio > 0.5 else ((248, 184, 24) if pip_ratio > 0.25 else (240, 64, 56))
            pygame.draw.rect(self.game_surface, (40, 40, 48), (mx, mini_y + 26, 22, 3))
            if pip_ratio > 0:
                pygame.draw.rect(self.game_surface, pip_color, (mx, mini_y + 26, max(1, int(22 * pip_ratio)), 3))
            # Current turn highlight
            if i == self.battle.turn_index and self.battle.is_player_turn:
                pygame.draw.rect(self.game_surface, GOLD, (mx - 1, mini_y - 1, 26, 32), 1)

        # --- Action Menu (Sapphire 2x2 grid style) ---
        if self.battle.is_player_turn and not self.battle.victory and not self.battle.defeat:
            menu_x = GAME_W - 230
            menu_y = GAME_H - 84
            menu_w = 220
            menu_h = 76

            # Menu background
            menu_bg = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
            menu_bg.fill((248, 248, 240, 240))
            self.game_surface.blit(menu_bg, (menu_x, menu_y))
            pygame.draw.rect(self.game_surface, (40, 40, 48), (menu_x, menu_y, menu_w, menu_h), 2, border_radius=4)

            if not self.battle.selecting_target:
                actions = self.battle.get_actions()
                action_font = self.fonts.get(11, bold=True)
                # Arrange in 2-column grid
                cols = 2
                col_w = menu_w // cols
                row_h = 28
                for j, action in enumerate(actions[:4]):  # max 4 in grid
                    col = j % cols
                    row = j // cols
                    ax = menu_x + col * col_w + 8
                    ay = menu_y + row * row_h + 10
                    is_sel = (j == self.battle.selected_action)
                    if is_sel:
                        # Sapphire cursor triangle
                        pygame.draw.polygon(
                            self.game_surface, (40, 40, 48),
                            [(ax - 2, ay + 4), (ax + 6, ay + 8), (ax - 2, ay + 12)],
                        )
                    color = (32, 32, 40) if is_sel else (96, 96, 112)
                    txt = action_font.render(action[:14], True, color)
                    self.game_surface.blit(txt, (ax + 10, ay + 2))

                # Overflow actions (spells beyond 4) in a list below
                if len(actions) > 4:
                    for j, action in enumerate(actions[4:], start=4):
                        ay = menu_y + menu_h + 4 + (j - 4) * 18
                        is_sel = (j == self.battle.selected_action)
                        prefix = ">" if is_sel else " "
                        color = (32, 32, 40) if is_sel else (96, 96, 112)
                        overflow_bg = pygame.Surface((menu_w, 16), pygame.SRCALPHA)
                        overflow_bg.fill((248, 248, 240, 220))
                        self.game_surface.blit(overflow_bg, (menu_x, ay))
                        txt = self.fonts.get(10).render(f"{prefix} {action}", True, color)
                        self.game_surface.blit(txt, (menu_x + 8, ay))
            else:
                hint_font = self.fonts.get(11)
                hint = hint_font.render("Select target", True, (32, 32, 40))
                self.game_surface.blit(hint, (menu_x + 12, menu_y + 10))
                arrow_hint = self.fonts.get(10)
                self.game_surface.blit(
                    arrow_hint.render("UP/DOWN + ENTER", True, (96, 96, 112)),
                    (menu_x + 12, menu_y + 30),
                )

        # --- Message Box (Sapphire style — bottom of screen) ---
        msg_x = 8
        msg_y = GAME_H - 84
        msg_w = GAME_W - 240
        msg_h = 76
        msg_bg = pygame.Surface((msg_w, msg_h), pygame.SRCALPHA)
        msg_bg.fill((248, 248, 240, 240))
        self.game_surface.blit(msg_bg, (msg_x, msg_y))
        pygame.draw.rect(self.game_surface, (40, 40, 48), (msg_x, msg_y, msg_w, msg_h), 2, border_radius=4)

        log_font = self.fonts.get(11)
        visible_log = self.battle.battle_log[-3:]
        for i, msg in enumerate(visible_log):
            # Truncate to fit box
            display_msg = msg[:48] if len(msg) > 48 else msg
            log_surf = log_font.render(display_msg, True, (32, 32, 40))
            self.game_surface.blit(log_surf, (msg_x + 10, msg_y + 8 + i * 20))

        # Advance indicator (triangle)
        if visible_log:
            tri_x = msg_x + msg_w - 16
            tri_y = msg_y + msg_h - 14
            bounce = int(math.sin(time.time() * 4) * 2)
            pygame.draw.polygon(
                self.game_surface, (40, 40, 48),
                [(tri_x, tri_y + bounce), (tri_x + 8, tri_y + bounce), (tri_x + 4, tri_y + 6 + bounce)],
            )

        # --- Victory / Defeat overlay ---
        if self.battle.victory or self.battle.defeat:
            overlay = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            self.game_surface.blit(overlay, (0, 0))

            result_font = self.fonts.get(24, bold=True)
            if self.battle.victory:
                # Gold victory text with shadow
                shadow = result_font.render("VICTORY!", True, (40, 32, 0))
                self.game_surface.blit(shadow, (GAME_W // 2 - shadow.get_width() // 2 + 2, GAME_H // 2 - 22))
                result = result_font.render("VICTORY!", True, GOLD)
                # XP gained hint
                xp_font = self.fonts.get(12)
                xp_text = xp_font.render("+10 XP  +Tongue Proficiency", True, (255, 255, 200))
                self.game_surface.blit(xp_text, (GAME_W // 2 - xp_text.get_width() // 2, GAME_H // 2 + 16))
            else:
                result = result_font.render("DEFEAT...", True, (240, 64, 56))

            self.game_surface.blit(result,
                                  (GAME_W // 2 - result.get_width() // 2,
                                   GAME_H // 2 - result.get_height() // 2 - 20))
            cont_font = self.fonts.get(11)
            cont = cont_font.render("Press ENTER to continue", True, (200, 200, 210))
            self.game_surface.blit(cont,
                                  (GAME_W // 2 - cont.get_width() // 2,
                                   GAME_H // 2 + 36))

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
        pad_state = "ONLINE" if self._polypad_has_device() else "LOCKED"
        unread = self._polypad_unread_count() if self._polypad_has_device() else 0
        pad_color = (120, 250, 170) if self._polypad_has_device() else (180, 120, 120)
        self.screen.blit(
            id_font.render(f"Poly Pad: {pad_state}  Msg:{unread}  [P]", True, pad_color),
            (DASH_X + 12, y),
        )
        y += 14
        self.screen.blit(
            id_font.render(f"CodeLab IDE: {self.ide_resolved} solved / {self.ide_failures} failed  [I]", True, (140, 198, 246)),
            (DASH_X + 12, y),
        )
        y += 14
        self.screen.blit(
            id_font.render(f"Lore Library: {self.library_reads} reads  [L]", True, (194, 166, 124)),
            (DASH_X + 12, y),
        )
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

        # ---- HF Training (Live) ----
        if y < WINDOW_H - 100:
            hf_title = section_font.render("HF TRAINING (LIVE)", True, DIM_TEXT)
            self.screen.blit(hf_title, (DASH_X + 12, y))
            y += 18
            hf_font = self.fonts.get(10)
            hf_stats = self.hf_trainer.get_stats()
            status_text = "pushing..." if hf_stats.get("running") else "local"
            self.screen.blit(hf_font.render(f"Status: {status_text}", True, TEXT_COLOR), (DASH_X + 16, y))
            y += 14
            self.screen.blit(hf_font.render(f"Approved: {hf_stats.get('approved', 0)} pairs", True, DIM_TEXT), (DASH_X + 16, y))
            y += 14
            self.screen.blit(hf_font.render(f"Batches: {hf_stats.get('batches', 0)} pushed", True, DIM_TEXT), (DASH_X + 16, y))
            y += 14
            self.screen.blit(hf_font.render(f"Queue: {hf_stats.get('queue_size', 0)} pending", True, DIM_TEXT), (DASH_X + 16, y))
            y += 16
            pygame.draw.line(self.screen, DASH_BORDER, (DASH_X + 10, y), (WINDOW_W - 10, y), 1)
            y += 8

        # ---- AetherNet Status (n8n bridge) ----
        if y < WINDOW_H - 120:
            net_title = section_font.render("AETHERNET (n8n)", True, DIM_TEXT)
            self.screen.blit(net_title, (DASH_X + 12, y))
            y += 18
            net_font = self.fonts.get(10)
            st = self.n8n_bus.status()
            online_color = (80, 255, 120) if st["online"] else (255, 80, 80)
            online_text = "ONLINE" if st["online"] else "OFFLINE"
            self.screen.blit(
                net_font.render(f"Status: {online_text}  [F9]", True, online_color),
                (DASH_X + 16, y),
            )
            y += 14
            self.screen.blit(
                net_font.render(
                    f"Out: {st['events_sent']}  In: {st['actions_processed']}  Fail: {st['events_failed']}",
                    True, DIM_TEXT,
                ),
                (DASH_X + 16, y),
            )
            y += 14
            self.screen.blit(
                net_font.render(f"Endpoints: {st['endpoints']}  TV: {st['tv_broadcasts']}", True, DIM_TEXT),
                (DASH_X + 16, y),
            )
            y += 14
            # Latest TV broadcast
            tv = self.n8n_bus.latest_tv()
            if tv:
                tv_text = f"TV: [{tv['channel']}] {tv['show'][:20]}"
                self.screen.blit(net_font.render(tv_text, True, (200, 180, 255)), (DASH_X + 16, y))
                y += 14
            # Latest announcement
            if self.aethernet_announcements:
                ann_text, ann_time = self.aethernet_announcements[-1]
                age = time.time() - ann_time
                if age < 30:  # Show for 30 seconds
                    alpha = max(0.3, 1.0 - age / 30)
                    ann_color = (
                        int(255 * alpha), int(220 * alpha), int(80 * alpha)
                    )
                    self.screen.blit(
                        net_font.render(f">> {ann_text[:30]}", True, ann_color),
                        (DASH_X + 16, y),
                    )
                    y += 14
            y += 4
            pygame.draw.line(self.screen, DASH_BORDER, (DASH_X + 10, y), (WINDOW_W - 10, y), 1)
            y += 8

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


# Stats already imported at top of file


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

        if g.game_phase == "polypad":
            # Keep autopilot moving through core loop; do not linger in app UI.
            return pygame.K_ESCAPE

        if g.game_phase == "ide":
            if random.random() < 0.12:
                return pygame.K_ESCAPE
            if random.random() < 0.25:
                return random.choice([pygame.K_UP, pygame.K_DOWN])
            return pygame.K_RETURN

        if g.game_phase == "library":
            if random.random() < 0.2:
                return pygame.K_ESCAPE
            return random.choice([pygame.K_DOWN, pygame.K_RETURN])

        # Overworld — wander randomly
        if g.game_phase == "overworld":
            directions = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]
            if random.random() < 0.15:
                return pygame.K_RETURN  # try interact
            return random.choice(directions)

        # Dungeon — wander toward exit
        if g.game_phase == "dungeon":
            directions = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]
            return random.choice(directions)

        # Dialogue — pick a pivot or exit
        if g.game_phase == "dialogue":
            if random.random() < 0.2:
                return pygame.K_ESCAPE  # sometimes leave
            if random.random() < 0.4:
                return random.choice([pygame.K_UP, pygame.K_DOWN])
            return pygame.K_RETURN

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
    print("    Arrow Keys / WASD  -  Move / Navigate")
    print("    Enter / Space      -  Advance / Select / Talk to NPC")
    print("    1-7                -  Quick-select choice")
    print("    P                  -  Poly Pad (phone / in-game PC)")
    print("    I                  -  CodeLab IDE (at terminal)")
    print("    L                  -  Lore Library (at terminal)")
    print("    Tab                -  Dashboard detail")
    print("    Esc                -  Pause / Exit dialogue / Leave tower")
    print("    B                  -  Test battle")
    print("    F6                 -  Script Lab")
    print("    F7                 -  Companion free-will")
    print("    F8                 -  AI Autopilot")
    print()
    print("  Phases: Story -> Overworld -> Dungeon Tower -> Battle")
    print()

    ai_mode = "--ai" in sys.argv or "--autopilot" in sys.argv
    headless_mode = "--headless" in sys.argv
    headless_steps = 0
    if headless_mode:
        # Parse --headless-steps N (default 300)
        headless_steps = 300
        for i, arg in enumerate(sys.argv):
            if arg == "--headless-steps" and i + 1 < len(sys.argv):
                headless_steps = int(sys.argv[i + 1])
        print(f"  [HEADLESS MODE] {headless_steps} steps, env={detect_environment().name}")
        ai_mode = True  # Force AI pilot in headless mode

    game = AethermoorGame(headless=headless_mode)
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

    if headless_mode and headless_steps > 0:
        # Run fixed number of steps then exit
        dt = 1.0 / FPS_CAP
        hd = game.headless_display
        print(f"  Running {headless_steps} headless steps...")
        for step in range(headless_steps):
            game._handle_events()
            game._update(dt)
            game._draw()
            if hd:
                hd.capture(game.game_surface)
                if hd.env == RuntimeEnv.COLAB and step % 60 == 0:
                    hd.show()
            game.frame_count += 1
            if not game.running:
                break

        # Export results
        if hd and hd.stored_frames > 0:
            gif_path = hd.save_gif("headless_session.gif", fps=15, scale=0.5)
            if gif_path:
                print(f"  GIF saved: {gif_path} ({hd.stored_frames} frames)")
                if hd.env == RuntimeEnv.COLAB and hd._ipython_display:
                    from IPython.display import Image
                    hd._ipython_display(Image(filename=gif_path))
            vid_path = hd.save_video("headless_session.mp4", fps=30)
            if vid_path:
                print(f"  Video saved: {vid_path}")

        # Cleanup
        try:
            game.hf_trainer.stop()
        except Exception:
            pass
        if hd:
            hd.stop()
        pygame.quit()
        print(f"\n  Headless session complete. AI took {pilot.total_actions} actions.")
        print(f"  Training data: {game.sft_count} SFT + {game.dpo_count} DPO pairs")
    else:
        game.run()
        print(f"\n  Session complete. AI took {pilot.total_actions} actions.")

    print("  Aethermoor awaits your return.\n")


if __name__ == "__main__":
    main()
