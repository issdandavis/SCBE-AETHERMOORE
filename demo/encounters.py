#!/usr/bin/env python3
"""
Wild Encounter & Route System for Aethermoor
=============================================

Defines RouteZones (areas with encounter tables), creature pools per Sacred
Tongue, a step-based encounter check, and a Bestiary for tracking seen/caught
creatures.  This module is the content backbone of the overworld RPG loop.

Every creature is themed to one of the Six Sacred Tongues and carries
lore-appropriate names, base stats, growth rates, and learnable moves
compatible with the engine.Spell format.

Usage from the main game loop::

    from encounters import step_encounter_check, Bestiary

    bestiary = Bestiary()
    # Each time the player takes a step on an encounter tile:
    result = step_encounter_check("avali_relay_forest", steps_since_last=12)
    if result is not None:
        # result is a dict with enemy data — spawn into combat
        bestiary.register_seen(result["name"])
        ...
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from engine import Tongue, TONGUE_NAMES, EvoStage  # noqa: E402

# ---------------------------------------------------------------------------
# Golden ratio — used for catch-rate scaling
# ---------------------------------------------------------------------------
PHI: float = (1 + math.sqrt(5)) / 2


# ---------------------------------------------------------------------------
# RouteZone dataclass
# ---------------------------------------------------------------------------
@dataclass
class RouteZone:
    """A named area in Aethermoor with wild encounter properties.

    Attributes
    ----------
    name : str
        Internal zone key (e.g. ``"avali_relay_forest"``).
    tongue_type : Tongue | None
        Dominant Sacred Tongue of this zone.  ``None`` means mixed.
    encounter_rate : float
        Base probability of encounter per step (0.0-1.0).
    level_range : Tuple[int, int]
        ``(min_level, max_level)`` for wild creatures in this zone.
    rare_chance : float
        Probability [0.0-1.0] that an encounter is a rare creature.
    description : str
        Lore flavour text shown on the map UI.
    """
    name: str
    tongue_type: Optional[Tongue]
    encounter_rate: float
    level_range: Tuple[int, int]
    rare_chance: float = 0.05
    description: str = ""


# ---------------------------------------------------------------------------
# AETHERMOOR_ROUTES — 10 canonical zones
# ---------------------------------------------------------------------------
AETHERMOOR_ROUTES: Dict[str, RouteZone] = {
    "starter_village": RouteZone(
        name="starter_village",
        tongue_type=None,
        encounter_rate=0.05,
        level_range=(1, 4),
        rare_chance=0.03,
        description=(
            "The gentle outskirts of the Guild Hub.  Weak creatures drift "
            "through the tall grass, drawn by the warmth of the hearthfires."
        ),
    ),
    "kor_authority_road": RouteZone(
        name="kor_authority_road",
        tongue_type=Tongue.KO,
        encounter_rate=0.12,
        level_range=(3, 7),
        rare_chance=0.05,
        description=(
            "A crimson-flagged highway enforced by Kor'aelin decree.  "
            "Creatures here bow to hierarchy or strike without warning."
        ),
    ),
    "avali_relay_forest": RouteZone(
        name="avali_relay_forest",
        tongue_type=Tongue.AV,
        encounter_rate=0.15,
        level_range=(5, 10),
        rare_chance=0.06,
        description=(
            "A dense canopy of signal-threaded trees where Avali messengers "
            "once strung relay lines.  The wildlife crackles with static."
        ),
    ),
    "runethic_policy_plains": RouteZone(
        name="runethic_policy_plains",
        tongue_type=Tongue.RU,
        encounter_rate=0.10,
        level_range=(8, 12),
        rare_chance=0.05,
        description=(
            "Flat golden grasslands where Runethic edicts are carved into "
            "standing stones.  The creatures enforce territorial law."
        ),
    ),
    "cassivadan_compute_mines": RouteZone(
        name="cassivadan_compute_mines",
        tongue_type=Tongue.CA,
        encounter_rate=0.18,
        level_range=(10, 15),
        rare_chance=0.07,
        description=(
            "Crystalline mine shafts humming with Cassisivadan compute cycles. "
            "Creatures feed on raw cipher-energy leaking from the walls."
        ),
    ),
    "umbroth_shadow_marsh": RouteZone(
        name="umbroth_shadow_marsh",
        tongue_type=Tongue.UM,
        encounter_rate=0.15,
        level_range=(12, 18),
        rare_chance=0.06,
        description=(
            "A perpetually twilit bog where Umbroth secrets pool like dark "
            "water.  Creatures here vanish at will and strike from nothing."
        ),
    ),
    "draumric_schema_peaks": RouteZone(
        name="draumric_schema_peaks",
        tongue_type=Tongue.DR,
        encounter_rate=0.12,
        level_range=(15, 22),
        rare_chance=0.06,
        description=(
            "Jagged mountain ridges inscribed with Draumric authentication "
            "glyphs.  Only the correctly-formatted survive the climb."
        ),
    ),
    "spiral_spire": RouteZone(
        name="spiral_spire",
        tongue_type=None,
        encounter_rate=0.20,
        level_range=(20, 30),
        rare_chance=0.08,
        description=(
            "The infamous boss tower at the heart of Aethermoor.  Every floor "
            "shifts tongue affinity, and the Spiral King waits at the apex."
        ),
    ),
    "timeless_observatory": RouteZone(
        name="timeless_observatory",
        tongue_type=None,
        encounter_rate=0.08,
        level_range=(25, 35),
        rare_chance=0.15,
        description=(
            "An ancient star-gazing platform outside time.  Encounters are "
            "rare but extraordinarily powerful — and extraordinarily rare."
        ),
    ),
    "world_tree_roots": RouteZone(
        name="world_tree_roots",
        tongue_type=None,
        encounter_rate=0.25,
        level_range=(30, 50),
        rare_chance=0.10,
        description=(
            "The root system of the World Tree Pollyoneth.  All six Tongues "
            "converge here.  The strongest creatures in Aethermoor dwell below."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Creature Template
# ---------------------------------------------------------------------------
@dataclass
class CreatureTemplate:
    """Blueprint for a wild creature species.

    Attributes
    ----------
    name : str
        Display name (e.g. ``"Decree Wisp"``).
    tongue : Tongue
        Native tongue affinity.
    base_hp : int
        Base hit points before level scaling.
    base_atk : int
        Base attack stat.
    base_def : int
        Base defense stat.
    base_spd : int
        Base speed stat.
    base_wis : int
        Base wisdom stat.
    growth_rates : Dict[str, float]
        Per-level multipliers for each stat (``hp``, ``atk``, ``def``,
        ``spd``, ``wis``).  A rate of 1.0 means +100% of base per level.
    native_moves : List[Dict[str, Any]]
        List of Spell-compatible dicts with keys ``name``, ``tongue``,
        ``power``, ``mp_cost``, ``description``.
    catch_difficulty : float
        0.0 (trivial) to 1.0 (legendary).  Lower = easier to catch.
    is_rare : bool
        If True this creature only appears on rare rolls.
    evo_stage : EvoStage
        Default evolution stage when encountered in the wild.
    lore : str
        Short flavour text for the Bestiary.
    """
    name: str
    tongue: Tongue
    base_hp: int
    base_atk: int
    base_def: int
    base_spd: int
    base_wis: int
    growth_rates: Dict[str, float] = field(default_factory=lambda: {
        "hp": 0.12, "atk": 0.10, "def": 0.10, "spd": 0.08, "wis": 0.08,
    })
    native_moves: List[Dict[str, Any]] = field(default_factory=list)
    catch_difficulty: float = 0.3
    is_rare: bool = False
    evo_stage: EvoStage = EvoStage.FRESH
    lore: str = ""


# ---------------------------------------------------------------------------
# Helper — build a move dict (Spell-compatible)
# ---------------------------------------------------------------------------
def _mv(
    name: str,
    tongue: Tongue,
    power: int,
    mp_cost: int,
    desc: str,
) -> Dict[str, Any]:
    """Convenience constructor for a Spell-compatible move dictionary."""
    return {
        "name": name,
        "tongue": tongue,
        "power": power,
        "mp_cost": mp_cost,
        "description": desc,
    }


# ===================================================================
# CREATURE POOLS — 6+ creatures per tongue
# ===================================================================

# ---------------------------------------------------------------------------
# KO — Kor'aelin (Authority / Control)
# ---------------------------------------------------------------------------
KO_CREATURES: List[CreatureTemplate] = [
    CreatureTemplate(
        name="Decree Wisp",
        tongue=Tongue.KO,
        base_hp=28, base_atk=9, base_def=6, base_spd=12, base_wis=10,
        growth_rates={"hp": 0.10, "atk": 0.09, "def": 0.06, "spd": 0.12, "wis": 0.10},
        native_moves=[
            _mv("Royal Flare", Tongue.KO, 10, 4, "A spark of authoritative flame"),
            _mv("Edict Pulse", Tongue.KO, 16, 7, "A shockwave backed by sovereign will"),
        ],
        catch_difficulty=0.20,
        evo_stage=EvoStage.FRESH,
        lore="A flickering mote of crimson light that enforces minor decrees. "
             "Often seen near roadside proclamation stones.",
    ),
    CreatureTemplate(
        name="Command Phantom",
        tongue=Tongue.KO,
        base_hp=40, base_atk=14, base_def=8, base_spd=10, base_wis=12,
        growth_rates={"hp": 0.12, "atk": 0.12, "def": 0.08, "spd": 0.09, "wis": 0.11},
        native_moves=[
            _mv("Order Strike", Tongue.KO, 14, 6, "A phantom blade of command"),
            _mv("Subjugate", Tongue.KO, 20, 10, "Forces the target to hesitate for a turn"),
        ],
        catch_difficulty=0.35,
        evo_stage=EvoStage.ROOKIE,
        lore="An armoured spectre that appears when laws are broken. "
             "Its translucent crown glows brighter the more authority it channels.",
    ),
    CreatureTemplate(
        name="Edict Shade",
        tongue=Tongue.KO,
        base_hp=34, base_atk=11, base_def=10, base_spd=8, base_wis=14,
        growth_rates={"hp": 0.11, "atk": 0.10, "def": 0.10, "spd": 0.07, "wis": 0.13},
        native_moves=[
            _mv("Binding Word", Tongue.KO, 12, 5, "A spoken command that constricts"),
            _mv("Mandate Shield", Tongue.KO, 0, 8, "Raises a barrier of raw authority"),
        ],
        catch_difficulty=0.30,
        evo_stage=EvoStage.FRESH,
        lore="A dark silhouette that recites forgotten edicts. "
             "Those who hear it feel compelled to obey.",
    ),
    CreatureTemplate(
        name="Authority Lynx",
        tongue=Tongue.KO,
        base_hp=48, base_atk=16, base_def=11, base_spd=14, base_wis=9,
        growth_rates={"hp": 0.13, "atk": 0.14, "def": 0.10, "spd": 0.13, "wis": 0.08},
        native_moves=[
            _mv("Sovereign Pounce", Tongue.KO, 18, 8, "A crushing leap backed by regal power"),
            _mv("Crimson Fang", Tongue.KO, 22, 10, "Fangs imbued with Kor'aelin authority"),
            _mv("Territorial Roar", Tongue.KO, 8, 4, "A roar that lowers enemy morale"),
        ],
        catch_difficulty=0.45,
        evo_stage=EvoStage.ROOKIE,
        lore="A sleek crimson feline that patrols the Authority Road. "
             "It considers itself judge, jury, and enforcer.",
    ),
    CreatureTemplate(
        name="Sovereign Owl",
        tongue=Tongue.KO,
        base_hp=38, base_atk=10, base_def=9, base_spd=11, base_wis=18,
        growth_rates={"hp": 0.10, "atk": 0.08, "def": 0.09, "spd": 0.10, "wis": 0.15},
        native_moves=[
            _mv("Watchful Gaze", Tongue.KO, 14, 6, "An unblinking stare that reveals weakness"),
            _mv("Decree Storm", Tongue.KO, 24, 12, "A storm of feathers carrying royal edicts"),
        ],
        catch_difficulty=0.40,
        evo_stage=EvoStage.ROOKIE,
        lore="A great horned owl draped in red regalia.  It circles above "
             "courtrooms and battlefields, judging from on high.",
    ),
    CreatureTemplate(
        name="Crown Serpent",
        tongue=Tongue.KO,
        base_hp=55, base_atk=18, base_def=14, base_spd=9, base_wis=16,
        growth_rates={"hp": 0.14, "atk": 0.14, "def": 0.12, "spd": 0.08, "wis": 0.13},
        native_moves=[
            _mv("Regal Constrict", Tongue.KO, 20, 9, "Wraps the foe in sovereign coils"),
            _mv("Tyrant's Venom", Tongue.KO, 26, 14, "Injects authority-dissolving toxin"),
            _mv("Crown Flash", Tongue.KO, 30, 16, "The crown jewel on its head detonates with light"),
        ],
        catch_difficulty=0.55,
        is_rare=True,
        evo_stage=EvoStage.CHAMPION,
        lore="A colossal serpent wearing a crown of solidified authority.  "
             "Legends say it was the first creature to speak Kor'aelin.",
    ),
]

# ---------------------------------------------------------------------------
# AV — Avali (Transport / Messaging)
# ---------------------------------------------------------------------------
AV_CREATURES: List[CreatureTemplate] = [
    CreatureTemplate(
        name="Relay Sprite",
        tongue=Tongue.AV,
        base_hp=24, base_atk=7, base_def=5, base_spd=16, base_wis=8,
        growth_rates={"hp": 0.08, "atk": 0.07, "def": 0.05, "spd": 0.15, "wis": 0.08},
        native_moves=[
            _mv("Spark Relay", Tongue.AV, 8, 3, "A tiny bolt that bounces between targets"),
            _mv("Quick Pulse", Tongue.AV, 12, 5, "A rapid energy burst"),
        ],
        catch_difficulty=0.18,
        evo_stage=EvoStage.FRESH,
        lore="A hyperactive ball of cyan light that carries messages "
             "between relay stations.  Impossible to keep still.",
    ),
    CreatureTemplate(
        name="Signal Hound",
        tongue=Tongue.AV,
        base_hp=42, base_atk=13, base_def=9, base_spd=15, base_wis=7,
        growth_rates={"hp": 0.12, "atk": 0.12, "def": 0.08, "spd": 0.14, "wis": 0.06},
        native_moves=[
            _mv("Frequency Bite", Tongue.AV, 14, 6, "Jaws resonate at a harmful frequency"),
            _mv("Doppler Dash", Tongue.AV, 18, 8, "A blurring charge that shifts pitch mid-strike"),
        ],
        catch_difficulty=0.35,
        evo_stage=EvoStage.ROOKIE,
        lore="A lean hound with antenna-like ears that can intercept "
             "messages travelling through the Avali network.",
    ),
    CreatureTemplate(
        name="Packet Wraith",
        tongue=Tongue.AV,
        base_hp=36, base_atk=12, base_def=7, base_spd=13, base_wis=11,
        growth_rates={"hp": 0.10, "atk": 0.10, "def": 0.07, "spd": 0.12, "wis": 0.10},
        native_moves=[
            _mv("Fragment Storm", Tongue.AV, 16, 7, "Hurls a barrage of broken data packets"),
            _mv("Ghost Route", Tongue.AV, 10, 5, "Phases through an attack via relay shortcut"),
        ],
        catch_difficulty=0.30,
        evo_stage=EvoStage.FRESH,
        lore="The remnant of a message that never reached its destination. "
             "It wanders the forest, endlessly seeking its recipient.",
    ),
    CreatureTemplate(
        name="Transit Falcon",
        tongue=Tongue.AV,
        base_hp=38, base_atk=15, base_def=8, base_spd=18, base_wis=9,
        growth_rates={"hp": 0.10, "atk": 0.13, "def": 0.07, "spd": 0.16, "wis": 0.08},
        native_moves=[
            _mv("Sonic Dive", Tongue.AV, 20, 9, "A supersonic aerial strike"),
            _mv("Relay Wing", Tongue.AV, 14, 6, "Wings leave a trail of signal energy"),
            _mv("Tail Wind", Tongue.AV, 0, 4, "Boosts party speed for three turns"),
        ],
        catch_difficulty=0.40,
        evo_stage=EvoStage.ROOKIE,
        lore="The fastest courier in Aethermoor.  A Transit Falcon can "
             "deliver a message across three islands in a single heartbeat.",
    ),
    CreatureTemplate(
        name="Message Fox",
        tongue=Tongue.AV,
        base_hp=32, base_atk=10, base_def=8, base_spd=14, base_wis=13,
        growth_rates={"hp": 0.09, "atk": 0.09, "def": 0.08, "spd": 0.13, "wis": 0.12},
        native_moves=[
            _mv("Cipher Yip", Tongue.AV, 12, 5, "A coded bark that confuses the target"),
            _mv("Encrypted Pounce", Tongue.AV, 16, 7, "An attack wrapped in signal noise"),
        ],
        catch_difficulty=0.28,
        evo_stage=EvoStage.FRESH,
        lore="A clever fox that steals messages and hides them in its "
             "burrow.  Researchers study its caching algorithms.",
    ),
    CreatureTemplate(
        name="Carrier Dove",
        tongue=Tongue.AV,
        base_hp=30, base_atk=8, base_def=6, base_spd=17, base_wis=14,
        growth_rates={"hp": 0.08, "atk": 0.07, "def": 0.06, "spd": 0.15, "wis": 0.13},
        native_moves=[
            _mv("Peace Pulse", Tongue.AV, 0, 6, "A calming wave that reduces enemy aggression"),
            _mv("Feathered Signal", Tongue.AV, 14, 6, "Signal-threaded feathers strike true"),
            _mv("Delivery Burst", Tongue.AV, 22, 11, "Releases all stored messages as raw energy"),
        ],
        catch_difficulty=0.22,
        evo_stage=EvoStage.FRESH,
        lore="A gentle dove that faithfully carries scrolls.  Its cooing "
             "is actually compressed Avali routing data.",
    ),
    # Rare
    CreatureTemplate(
        name="Bandwidth Leviathan",
        tongue=Tongue.AV,
        base_hp=60, base_atk=16, base_def=12, base_spd=20, base_wis=14,
        growth_rates={"hp": 0.14, "atk": 0.12, "def": 0.10, "spd": 0.16, "wis": 0.12},
        native_moves=[
            _mv("Cascade Torrent", Tongue.AV, 28, 14, "A tidal wave of compressed data"),
            _mv("Overload Beam", Tongue.AV, 32, 18, "Floods the target with impossible bandwidth"),
            _mv("Network Surge", Tongue.AV, 20, 10, "A pulse that heals allies near relay points"),
        ],
        catch_difficulty=0.60,
        is_rare=True,
        evo_stage=EvoStage.CHAMPION,
        lore="An ancient sea-serpent that IS the Avali relay network.  "
             "Harming it disrupts communications across the continent.",
    ),
]

# ---------------------------------------------------------------------------
# RU — Runethic (Policy / Constraints)
# ---------------------------------------------------------------------------
RU_CREATURES: List[CreatureTemplate] = [
    CreatureTemplate(
        name="Clause Golem",
        tongue=Tongue.RU,
        base_hp=52, base_atk=12, base_def=16, base_spd=4, base_wis=8,
        growth_rates={"hp": 0.14, "atk": 0.10, "def": 0.15, "spd": 0.03, "wis": 0.07},
        native_moves=[
            _mv("Stone Clause", Tongue.RU, 14, 6, "A fist of inscribed stone"),
            _mv("Binding Contract", Tongue.RU, 0, 8, "Locks the target's strongest move for 2 turns"),
        ],
        catch_difficulty=0.30,
        evo_stage=EvoStage.FRESH,
        lore="A squat golem made of stacked legal tablets.  It moves "
             "slowly but its rulings are absolute.",
    ),
    CreatureTemplate(
        name="Mandate Crawler",
        tongue=Tongue.RU,
        base_hp=44, base_atk=10, base_def=14, base_spd=6, base_wis=10,
        growth_rates={"hp": 0.12, "atk": 0.09, "def": 0.13, "spd": 0.05, "wis": 0.09},
        native_moves=[
            _mv("Policy Grind", Tongue.RU, 12, 5, "Grinds forward enforcing local mandates"),
            _mv("Red Tape Snare", Tongue.RU, 8, 4, "Tangles the foe in bureaucratic thread"),
        ],
        catch_difficulty=0.25,
        evo_stage=EvoStage.FRESH,
        lore="A many-legged insect armoured in golden parchment. "
             "It eats expired policies and excretes new ones.",
    ),
    CreatureTemplate(
        name="Bylaw Beast",
        tongue=Tongue.RU,
        base_hp=56, base_atk=14, base_def=18, base_spd=5, base_wis=9,
        growth_rates={"hp": 0.14, "atk": 0.11, "def": 0.16, "spd": 0.04, "wis": 0.08},
        native_moves=[
            _mv("Regulation Slam", Tongue.RU, 18, 8, "A body-check enforced by local bylaws"),
            _mv("Amendment Heal", Tongue.RU, 0, 10, "Rewrites injury clauses — heals 25% HP"),
            _mv("Veto Stomp", Tongue.RU, 22, 11, "A devastating stomp that overrules all defence"),
        ],
        catch_difficulty=0.40,
        evo_stage=EvoStage.ROOKIE,
        lore="A massive bovine creature whose hide is covered in "
             "shifting golden text.  It can rewrite reality's fine print.",
    ),
    CreatureTemplate(
        name="Rule Bear",
        tongue=Tongue.RU,
        base_hp=64, base_atk=16, base_def=15, base_spd=5, base_wis=7,
        growth_rates={"hp": 0.15, "atk": 0.13, "def": 0.14, "spd": 0.04, "wis": 0.06},
        native_moves=[
            _mv("Constraint Maul", Tongue.RU, 20, 9, "A clawed swipe that constrains movement"),
            _mv("Precedent Charge", Tongue.RU, 24, 12, "Charges with the weight of every past ruling"),
        ],
        catch_difficulty=0.42,
        evo_stage=EvoStage.ROOKIE,
        lore="A towering bear carved from standing stones.  Its growl "
             "sounds like a gavel striking.  Do not violate its territory.",
    ),
    CreatureTemplate(
        name="Statute Wolf",
        tongue=Tongue.RU,
        base_hp=46, base_atk=15, base_def=12, base_spd=10, base_wis=10,
        growth_rates={"hp": 0.12, "atk": 0.13, "def": 0.11, "spd": 0.09, "wis": 0.09},
        native_moves=[
            _mv("Pack Decree", Tongue.RU, 16, 7, "Howls a coordinated enforcement order"),
            _mv("Law Fang", Tongue.RU, 20, 9, "Bites with teeth engraved with statutes"),
        ],
        catch_difficulty=0.35,
        evo_stage=EvoStage.ROOKIE,
        lore="A wolf whose fur gleams like burnished gold parchment. "
             "It hunts in packs, each member enforcing a different clause.",
    ),
    CreatureTemplate(
        name="Policy Hawk",
        tongue=Tongue.RU,
        base_hp=36, base_atk=13, base_def=9, base_spd=14, base_wis=12,
        growth_rates={"hp": 0.10, "atk": 0.12, "def": 0.08, "spd": 0.13, "wis": 0.11},
        native_moves=[
            _mv("Enforcement Dive", Tongue.RU, 18, 8, "A diving strike that enforces compliance"),
            _mv("Audit Screech", Tongue.RU, 12, 5, "A piercing cry that reveals hidden stats"),
        ],
        catch_difficulty=0.32,
        evo_stage=EvoStage.FRESH,
        lore="A hawk with quill-like feathers.  It circles policy "
             "violations and strikes with precision audits.",
    ),
    # Rare
    CreatureTemplate(
        name="Constitution Titan",
        tongue=Tongue.RU,
        base_hp=80, base_atk=18, base_def=24, base_spd=3, base_wis=14,
        growth_rates={"hp": 0.16, "atk": 0.12, "def": 0.18, "spd": 0.02, "wis": 0.12},
        native_moves=[
            _mv("Supreme Verdict", Tongue.RU, 30, 16, "An unchallengeable legal ruling made manifest"),
            _mv("Foundation Quake", Tongue.RU, 26, 14, "Shakes the very constitutional bedrock"),
            _mv("Grand Amendment", Tongue.RU, 0, 18, "Fully heals and removes all debuffs"),
        ],
        catch_difficulty=0.65,
        is_rare=True,
        evo_stage=EvoStage.CHAMPION,
        lore="A mountain-sized golem of golden tablets that IS the "
             "constitution of Aethermoor.  To defeat it is to rewrite law.",
    ),
]

# ---------------------------------------------------------------------------
# CA — Cassisivadan (Compute / Encryption)
# ---------------------------------------------------------------------------
CA_CREATURES: List[CreatureTemplate] = [
    CreatureTemplate(
        name="Hash Slime",
        tongue=Tongue.CA,
        base_hp=30, base_atk=8, base_def=10, base_spd=6, base_wis=12,
        growth_rates={"hp": 0.10, "atk": 0.07, "def": 0.09, "spd": 0.05, "wis": 0.12},
        native_moves=[
            _mv("Digest Splash", Tongue.CA, 10, 4, "A splash of corrosive hash solution"),
            _mv("Collision Burst", Tongue.CA, 16, 7, "Two hash values collide in an explosion"),
        ],
        catch_difficulty=0.20,
        evo_stage=EvoStage.FRESH,
        lore="A translucent green blob that absorbs data and excretes "
             "irreversible hashes.  Surprisingly friendly once caught.",
    ),
    CreatureTemplate(
        name="Thread Serpent",
        tongue=Tongue.CA,
        base_hp=38, base_atk=14, base_def=8, base_spd=12, base_wis=10,
        growth_rates={"hp": 0.11, "atk": 0.13, "def": 0.07, "spd": 0.11, "wis": 0.09},
        native_moves=[
            _mv("Fork Strike", Tongue.CA, 14, 6, "Splits into two simultaneous attacks"),
            _mv("Deadlock Coil", Tongue.CA, 18, 8, "Binds the enemy in an unresolvable hold"),
        ],
        catch_difficulty=0.32,
        evo_stage=EvoStage.ROOKIE,
        lore="A serpent made of intertwined computational threads. "
             "It can execute multiple attacks simultaneously.",
    ),
    CreatureTemplate(
        name="Cipher Moth",
        tongue=Tongue.CA,
        base_hp=26, base_atk=9, base_def=6, base_spd=14, base_wis=16,
        growth_rates={"hp": 0.08, "atk": 0.08, "def": 0.05, "spd": 0.13, "wis": 0.15},
        native_moves=[
            _mv("Encrypted Dust", Tongue.CA, 12, 5, "Wings scatter indecipherable pollen"),
            _mv("Key Exchange", Tongue.CA, 0, 8, "Swaps a stat with the enemy — unpredictable"),
        ],
        catch_difficulty=0.28,
        evo_stage=EvoStage.FRESH,
        lore="A luminous moth whose wing patterns are valid encryption "
             "keys.  Scholars capture them to study cryptography.",
    ),
    CreatureTemplate(
        name="Compute Crab",
        tongue=Tongue.CA,
        base_hp=50, base_atk=11, base_def=18, base_spd=4, base_wis=11,
        growth_rates={"hp": 0.13, "atk": 0.09, "def": 0.16, "spd": 0.03, "wis": 0.10},
        native_moves=[
            _mv("Cache Pinch", Tongue.CA, 14, 6, "Pinches with data-hardened claws"),
            _mv("Overflow Shell", Tongue.CA, 0, 10, "Hardens shell with buffered energy — +50% def"),
            _mv("Stack Smash", Tongue.CA, 22, 11, "Crashes through defences by overflowing the stack"),
        ],
        catch_difficulty=0.38,
        evo_stage=EvoStage.ROOKIE,
        lore="A hermit crab whose shell is a living processor.  It caches "
             "attacks and replays them when threatened.",
    ),
    CreatureTemplate(
        name="Logic Beetle",
        tongue=Tongue.CA,
        base_hp=34, base_atk=12, base_def=12, base_spd=8, base_wis=13,
        growth_rates={"hp": 0.10, "atk": 0.10, "def": 0.10, "spd": 0.07, "wis": 0.12},
        native_moves=[
            _mv("Boolean Bash", Tongue.CA, 14, 6, "True or false — this hit always resolves to TRUE"),
            _mv("Gate Pulse", Tongue.CA, 10, 4, "A pulse from the beetle's logic gate antennae"),
        ],
        catch_difficulty=0.26,
        evo_stage=EvoStage.FRESH,
        lore="A shiny beetle with binary patterns on its carapace. "
             "It clicks its mandibles in ones and zeros.",
    ),
    CreatureTemplate(
        name="Data Wyrm",
        tongue=Tongue.CA,
        base_hp=58, base_atk=17, base_def=13, base_spd=10, base_wis=15,
        growth_rates={"hp": 0.14, "atk": 0.14, "def": 0.11, "spd": 0.09, "wis": 0.13},
        native_moves=[
            _mv("Byte Stream", Tongue.CA, 20, 9, "A torrent of raw binary data"),
            _mv("Recursive Fang", Tongue.CA, 26, 13, "Each bite calls itself — damage escalates"),
            _mv("Compile Breath", Tongue.CA, 30, 16, "Compiles all stored data into a devastating beam"),
        ],
        catch_difficulty=0.50,
        is_rare=True,
        evo_stage=EvoStage.CHAMPION,
        lore="A dragon composed of streaming data.  It compiles entire "
             "libraries into weaponized output.  Handle with care.",
    ),
]

# ---------------------------------------------------------------------------
# UM — Umbroth (Security / Secrets)
# ---------------------------------------------------------------------------
UM_CREATURES: List[CreatureTemplate] = [
    CreatureTemplate(
        name="Shadow Lurker",
        tongue=Tongue.UM,
        base_hp=32, base_atk=11, base_def=8, base_spd=13, base_wis=10,
        growth_rates={"hp": 0.10, "atk": 0.10, "def": 0.07, "spd": 0.12, "wis": 0.09},
        native_moves=[
            _mv("Shade Stab", Tongue.UM, 12, 5, "A sudden strike from the darkness"),
            _mv("Vanish Step", Tongue.UM, 0, 4, "Disappears briefly — raises evasion"),
        ],
        catch_difficulty=0.25,
        evo_stage=EvoStage.FRESH,
        lore="A formless shadow that clings to the underside of things. "
             "You never see it approach — only its aftermath.",
    ),
    CreatureTemplate(
        name="Null Guard",
        tongue=Tongue.UM,
        base_hp=48, base_atk=10, base_def=16, base_spd=6, base_wis=14,
        growth_rates={"hp": 0.13, "atk": 0.08, "def": 0.15, "spd": 0.05, "wis": 0.12},
        native_moves=[
            _mv("Null Check", Tongue.UM, 14, 6, "Checks the target for vulnerabilities"),
            _mv("Deny Access", Tongue.UM, 0, 8, "Blocks the next attack completely"),
            _mv("Void Slam", Tongue.UM, 18, 9, "A heavy blow from the null dimension"),
        ],
        catch_difficulty=0.38,
        evo_stage=EvoStage.ROOKIE,
        lore="An eyeless sentinel that guards the boundary between known "
             "and unknown.  Its shield nullifies anything unauthorised.",
    ),
    CreatureTemplate(
        name="Void Stalker",
        tongue=Tongue.UM,
        base_hp=40, base_atk=15, base_def=9, base_spd=14, base_wis=11,
        growth_rates={"hp": 0.11, "atk": 0.13, "def": 0.08, "spd": 0.13, "wis": 0.10},
        native_moves=[
            _mv("Entropy Claw", Tongue.UM, 16, 7, "Claws that dissolve order on contact"),
            _mv("Phase Ambush", Tongue.UM, 20, 9, "Steps through the void and strikes from behind"),
        ],
        catch_difficulty=0.36,
        evo_stage=EvoStage.ROOKIE,
        lore="A predator from the space between dimensions.  It hunts "
             "by sensing the heat of secrets kept too long.",
    ),
    CreatureTemplate(
        name="Secret Bat",
        tongue=Tongue.UM,
        base_hp=28, base_atk=9, base_def=6, base_spd=16, base_wis=13,
        growth_rates={"hp": 0.08, "atk": 0.08, "def": 0.05, "spd": 0.15, "wis": 0.12},
        native_moves=[
            _mv("Whisper Bite", Tongue.UM, 10, 4, "Bites while whispering stolen secrets"),
            _mv("Echoleak", Tongue.UM, 14, 6, "Sonar reveals hidden enemy information"),
        ],
        catch_difficulty=0.22,
        evo_stage=EvoStage.FRESH,
        lore="A bat that feeds on whispered secrets.  Its squeaks contain "
             "fragments of overheard conversations.",
    ),
    CreatureTemplate(
        name="Crypt Spider",
        tongue=Tongue.UM,
        base_hp=36, base_atk=13, base_def=11, base_spd=10, base_wis=12,
        growth_rates={"hp": 0.10, "atk": 0.12, "def": 0.10, "spd": 0.09, "wis": 0.11},
        native_moves=[
            _mv("Web of Secrets", Tongue.UM, 14, 6, "A sticky web that traps and reveals"),
            _mv("Poison Cipher", Tongue.UM, 18, 8, "Injects encrypted venom"),
        ],
        catch_difficulty=0.30,
        evo_stage=EvoStage.FRESH,
        lore="A spider that spins webs of encrypted silk.  Its prey "
             "cannot escape without the decryption key.",
    ),
    CreatureTemplate(
        name="Gloom Panther",
        tongue=Tongue.UM,
        base_hp=52, base_atk=18, base_def=12, base_spd=15, base_wis=13,
        growth_rates={"hp": 0.13, "atk": 0.15, "def": 0.10, "spd": 0.13, "wis": 0.11},
        native_moves=[
            _mv("Shadow Maul", Tongue.UM, 22, 10, "A devastating pounce from perfect darkness"),
            _mv("Secret Eater", Tongue.UM, 18, 8, "Devours the target's buffs"),
            _mv("Midnight Roar", Tongue.UM, 26, 13, "A roar that plunges the battlefield into darkness"),
        ],
        catch_difficulty=0.48,
        evo_stage=EvoStage.ROOKIE,
        lore="A panther made of living shadow.  It can devour light "
             "itself.  The last thing its prey sees is nothing at all.",
    ),
    # Rare
    CreatureTemplate(
        name="Oblivion Sphinx",
        tongue=Tongue.UM,
        base_hp=62, base_atk=16, base_def=18, base_spd=10, base_wis=22,
        growth_rates={"hp": 0.14, "atk": 0.12, "def": 0.14, "spd": 0.08, "wis": 0.18},
        native_moves=[
            _mv("Riddle of Void", Tongue.UM, 28, 14, "A question that damages the mind if unanswered"),
            _mv("Memory Seal", Tongue.UM, 0, 16, "Seals one of the enemy's moves permanently"),
            _mv("Absolute Zero Trust", Tongue.UM, 34, 20, "Trust nothing — annihilate everything"),
        ],
        catch_difficulty=0.70,
        is_rare=True,
        evo_stage=EvoStage.CHAMPION,
        lore="An ancient sphinx that guards the deepest Umbroth vault. "
             "Answer its riddle wrong and you forget you ever existed.",
    ),
]

# ---------------------------------------------------------------------------
# DR — Draumric (Schema / Authentication)
# ---------------------------------------------------------------------------
DR_CREATURES: List[CreatureTemplate] = [
    CreatureTemplate(
        name="Data Djinn",
        tongue=Tongue.DR,
        base_hp=34, base_atk=10, base_def=8, base_spd=11, base_wis=14,
        growth_rates={"hp": 0.10, "atk": 0.09, "def": 0.07, "spd": 0.10, "wis": 0.13},
        native_moves=[
            _mv("Wish Parse", Tongue.DR, 12, 5, "Parses a wish into harmful output"),
            _mv("Format Flame", Tongue.DR, 16, 7, "An orange flame that reformats on contact"),
        ],
        catch_difficulty=0.28,
        evo_stage=EvoStage.FRESH,
        lore="A small djinn born from malformed schema definitions.  "
             "It grants wishes, but only in valid JSON.",
    ),
    CreatureTemplate(
        name="Format Phantom",
        tongue=Tongue.DR,
        base_hp=38, base_atk=12, base_def=10, base_spd=10, base_wis=13,
        growth_rates={"hp": 0.11, "atk": 0.10, "def": 0.09, "spd": 0.09, "wis": 0.12},
        native_moves=[
            _mv("Schema Slash", Tongue.DR, 14, 6, "Slices with a blade of rigid formatting"),
            _mv("Validate Strike", Tongue.DR, 18, 8, "Only hits if the target fails validation"),
        ],
        catch_difficulty=0.32,
        evo_stage=EvoStage.ROOKIE,
        lore="A ghostly figure wrapped in scrolling orange runes. "
             "It phases through anything that fails its schema check.",
    ),
    CreatureTemplate(
        name="Type Specter",
        tongue=Tongue.DR,
        base_hp=30, base_atk=9, base_def=7, base_spd=12, base_wis=16,
        growth_rates={"hp": 0.09, "atk": 0.08, "def": 0.06, "spd": 0.11, "wis": 0.15},
        native_moves=[
            _mv("Type Error", Tongue.DR, 14, 6, "Forces a type mismatch — chaos ensues"),
            _mv("Cast Ray", Tongue.DR, 10, 4, "A beam of strictly typed energy"),
        ],
        catch_difficulty=0.26,
        evo_stage=EvoStage.FRESH,
        lore="A flickering ghost that haunts poorly typed codebases. "
             "It screams whenever it finds an implicit any.",
    ),
    CreatureTemplate(
        name="Schema Drake",
        tongue=Tongue.DR,
        base_hp=54, base_atk=16, base_def=14, base_spd=9, base_wis=15,
        growth_rates={"hp": 0.14, "atk": 0.13, "def": 0.12, "spd": 0.08, "wis": 0.13},
        native_moves=[
            _mv("Definition Breath", Tongue.DR, 22, 10, "Breathes a stream of rigid schema fire"),
            _mv("Auth Claw", Tongue.DR, 18, 8, "Claws that demand authentication on contact"),
            _mv("Migration Roar", Tongue.DR, 26, 13, "A roar that forces all fields to migrate"),
        ],
        catch_difficulty=0.45,
        evo_stage=EvoStage.ROOKIE,
        lore="A small dragon whose scales are validation rules.  "
             "It breathes schema definitions that rewrite reality.",
    ),
    CreatureTemplate(
        name="Parse Raven",
        tongue=Tongue.DR,
        base_hp=32, base_atk=11, base_def=7, base_spd=14, base_wis=15,
        growth_rates={"hp": 0.09, "atk": 0.10, "def": 0.06, "spd": 0.13, "wis": 0.14},
        native_moves=[
            _mv("Token Peck", Tongue.DR, 12, 5, "Pecks apart syntax one token at a time"),
            _mv("AST Dive", Tongue.DR, 18, 8, "Dives through the abstract syntax tree"),
        ],
        catch_difficulty=0.30,
        evo_stage=EvoStage.FRESH,
        lore="A raven whose feathers are syntax tokens.  It can "
             "disassemble any sentence into its parse tree by cawing.",
    ),
    CreatureTemplate(
        name="Token Imp",
        tongue=Tongue.DR,
        base_hp=24, base_atk=8, base_def=5, base_spd=15, base_wis=11,
        growth_rates={"hp": 0.07, "atk": 0.07, "def": 0.04, "spd": 0.14, "wis": 0.10},
        native_moves=[
            _mv("Token Toss", Tongue.DR, 8, 3, "Hurls a handful of authentication tokens"),
            _mv("Expiry Curse", Tongue.DR, 14, 6, "Curses the target — their buffs expire sooner"),
        ],
        catch_difficulty=0.18,
        evo_stage=EvoStage.FRESH,
        lore="A mischievous imp that steals authentication tokens and "
             "hides them in expired sessions.  Annoying but harmless.",
    ),
    # Rare
    CreatureTemplate(
        name="Archetype Oracle",
        tongue=Tongue.DR,
        base_hp=58, base_atk=14, base_def=16, base_spd=8, base_wis=24,
        growth_rates={"hp": 0.13, "atk": 0.10, "def": 0.13, "spd": 0.07, "wis": 0.20},
        native_moves=[
            _mv("Schema Genesis", Tongue.DR, 30, 16, "Defines a new schema that damages all non-compliant foes"),
            _mv("Root Auth", Tongue.DR, 0, 14, "Grants root authentication — heals and boosts all stats"),
            _mv("Final Validation", Tongue.DR, 34, 20, "The ultimate check — massive damage to the unworthy"),
        ],
        catch_difficulty=0.68,
        is_rare=True,
        evo_stage=EvoStage.CHAMPION,
        lore="The primordial schema from which all Draumric definitions "
             "descend.  It speaks in type declarations.",
    ),
]


# ===================================================================
# Aggregated pool registry
# ===================================================================
CREATURE_POOLS: Dict[Tongue, List[CreatureTemplate]] = {
    Tongue.KO: KO_CREATURES,
    Tongue.AV: AV_CREATURES,
    Tongue.RU: RU_CREATURES,
    Tongue.CA: CA_CREATURES,
    Tongue.UM: UM_CREATURES,
    Tongue.DR: DR_CREATURES,
}

# Flat lookup by creature name (for Bestiary / roster)
ALL_CREATURES: Dict[str, CreatureTemplate] = {}
for _pool in CREATURE_POOLS.values():
    for _ct in _pool:
        ALL_CREATURES[_ct.name] = _ct


# ===================================================================
# EncounterTable — main encounter logic
# ===================================================================
class EncounterTable:
    """Handles encounter chance rolls and creature generation.

    Usage::

        table = EncounterTable()
        zone = AETHERMOOR_ROUTES["avali_relay_forest"]
        if table.check_encounter("avali_relay_forest", steps_since_last=15):
            enemy = table.generate_encounter(zone, player_level=8)
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()

    # -----------------------------------------------------------------
    # Encounter check
    # -----------------------------------------------------------------
    def check_encounter(self, zone_name: str, steps_since_last: int) -> bool:
        """Roll for a wild encounter.

        The effective probability scales with the number of steps since
        the last encounter, following a soft-cap curve::

            effective_rate = base_rate * (1 - e^(-steps / 20))

        This guarantees that after many steps the player will almost
        certainly encounter something, while keeping early steps low.

        Parameters
        ----------
        zone_name : str
            Key into ``AETHERMOOR_ROUTES``.
        steps_since_last : int
            Steps the player has taken since the previous encounter
            (or since entering the zone).

        Returns
        -------
        bool
            ``True`` if an encounter should trigger.
        """
        zone = AETHERMOOR_ROUTES.get(zone_name)
        if zone is None:
            return False

        # Soft-cap step scaling: approaches 1.0 as steps grow
        step_factor = 1.0 - math.exp(-steps_since_last / 20.0)
        effective_rate = zone.encounter_rate * step_factor

        return self._rng.random() < effective_rate

    # -----------------------------------------------------------------
    # Generate encounter data
    # -----------------------------------------------------------------
    def generate_encounter(
        self,
        zone: RouteZone,
        player_level: int,
    ) -> Dict[str, Any]:
        """Generate a single wild creature encounter.

        Returns a dictionary containing all data needed to construct a
        battle: creature name, tongue affinity, level, stats, moves,
        catch rate, and rarity flag.

        Parameters
        ----------
        zone : RouteZone
            The zone definition (provides tongue, level range, rare chance).
        player_level : int
            Current player level, used to bias the encounter level.

        Returns
        -------
        Dict[str, Any]
            Keys: ``name``, ``tongue``, ``level``, ``stats``, ``moves``,
            ``catch_rate``, ``is_rare``, ``evo_stage``, ``lore``.
        """
        # Determine whether this is a rare encounter
        is_rare_roll = self._rng.random() < zone.rare_chance

        # Pick the tongue pool
        if zone.tongue_type is not None:
            pool = CREATURE_POOLS[zone.tongue_type]
        else:
            # Mixed zone — pick a random tongue
            tongue_key = self._rng.choice(list(CREATURE_POOLS.keys()))
            pool = CREATURE_POOLS[tongue_key]

        # Separate common and rare creatures
        rares = [c for c in pool if c.is_rare]
        commons = [c for c in pool if not c.is_rare]

        if is_rare_roll and rares:
            template = self._rng.choice(rares)
        elif commons:
            template = self._rng.choice(commons)
        else:
            template = self._rng.choice(pool)

        # Determine level — biased toward player level but clamped to zone
        min_lv, max_lv = zone.level_range
        # Centre around player level, add noise
        base_lv = player_level + self._rng.randint(-2, 2)
        creature_level = max(min_lv, min(max_lv, base_lv))

        # Scale stats by level
        level_factor = creature_level / 10.0  # normalise so level 10 = 1x growth
        scaled_hp = max(1, int(template.base_hp * (1.0 + template.growth_rates["hp"] * creature_level)))
        scaled_atk = max(1, int(template.base_atk * (1.0 + template.growth_rates["atk"] * creature_level)))
        scaled_def = max(1, int(template.base_def * (1.0 + template.growth_rates["def"] * creature_level)))
        scaled_spd = max(1, int(template.base_spd * (1.0 + template.growth_rates["spd"] * creature_level)))
        scaled_wis = max(1, int(template.base_wis * (1.0 + template.growth_rates["wis"] * creature_level)))

        # Add slight random variance (+/- 10%)
        def _vary(val: int) -> int:
            factor = self._rng.uniform(0.90, 1.10)
            return max(1, int(val * factor))

        stats = {
            "hp": _vary(scaled_hp),
            "max_hp": _vary(scaled_hp),
            "atk": _vary(scaled_atk),
            "defense": _vary(scaled_def),
            "spd": _vary(scaled_spd),
            "wis": _vary(scaled_wis),
            "mp": max(10, int(20 + creature_level * 2.5)),
            "max_mp": max(10, int(20 + creature_level * 2.5)),
        }
        # Sync hp and max_hp
        stats["max_hp"] = max(stats["hp"], stats["max_hp"])
        stats["hp"] = stats["max_hp"]

        # Build move list — unlock more moves at higher levels
        available_moves = []
        for i, move in enumerate(template.native_moves):
            # First move always available; others unlock every 5 levels
            unlock_level = i * 5
            if creature_level >= unlock_level:
                available_moves.append(move)
        if not available_moves:
            available_moves = [template.native_moves[0]]

        # Catch rate — harder creatures get lower rates, higher levels too
        # Base formula: (1 - catch_difficulty) * (1 / (1 + level/20))
        raw_catch = (1.0 - template.catch_difficulty) * (1.0 / (1.0 + creature_level / 20.0))
        catch_rate = max(0.02, min(0.95, raw_catch))

        # Determine evo stage based on level
        evo_stage = template.evo_stage
        if creature_level >= 30:
            evo_stage = EvoStage.ULTIMATE
        elif creature_level >= 20:
            evo_stage = EvoStage.CHAMPION
        elif creature_level >= 10:
            evo_stage = EvoStage.ROOKIE

        return {
            "name": template.name,
            "tongue": template.tongue,
            "tongue_name": TONGUE_NAMES[template.tongue],
            "level": creature_level,
            "stats": stats,
            "moves": available_moves,
            "catch_rate": round(catch_rate, 4),
            "is_rare": template.is_rare,
            "evo_stage": evo_stage,
            "lore": template.lore,
            "base_template": template.name,
        }


# ===================================================================
# Convenience function — called per player step
# ===================================================================

# Module-level default encounter table instance
_DEFAULT_TABLE = EncounterTable()


def step_encounter_check(
    zone_name: str,
    steps: int,
    player_level: int = 1,
) -> Optional[Dict[str, Any]]:
    """Check for and optionally generate an encounter on each step.

    This is the main entry point the game loop should call every time the
    player takes a step on an encounter tile.

    Parameters
    ----------
    zone_name : str
        Key into ``AETHERMOOR_ROUTES`` (e.g. ``"avali_relay_forest"``).
    steps : int
        Steps since the last encounter (resets on encounter).
    player_level : int
        The player's current level.

    Returns
    -------
    Optional[Dict[str, Any]]
        A creature encounter dict if triggered, else ``None``.
    """
    zone = AETHERMOOR_ROUTES.get(zone_name)
    if zone is None:
        return None

    if _DEFAULT_TABLE.check_encounter(zone_name, steps):
        return _DEFAULT_TABLE.generate_encounter(zone, player_level)

    return None


# ===================================================================
# Bestiary — creature tracking
# ===================================================================
class Bestiary:
    """Tracks which creatures the player has seen and caught.

    Provides methods for registration, querying completion percentage,
    and serialisation for save/load.

    Usage::

        bestiary = Bestiary()
        bestiary.register_seen("Hash Slime")
        bestiary.register_caught("Hash Slime")
        print(bestiary.completion_pct())  # e.g. 2.3
    """

    def __init__(self) -> None:
        # name -> {"seen": bool, "caught": bool, "seen_count": int, "caught_count": int}
        self._entries: Dict[str, Dict[str, Any]] = {}

    def register_seen(self, creature_name: str) -> None:
        """Record that the player has encountered (seen) a creature."""
        entry = self._entries.setdefault(creature_name, {
            "seen": False,
            "caught": False,
            "seen_count": 0,
            "caught_count": 0,
        })
        entry["seen"] = True
        entry["seen_count"] = entry.get("seen_count", 0) + 1

    def register_caught(self, creature_name: str) -> None:
        """Record that the player has caught a creature.

        Automatically marks the creature as seen as well.
        """
        self.register_seen(creature_name)
        entry = self._entries[creature_name]
        entry["caught"] = True
        entry["caught_count"] = entry.get("caught_count", 0) + 1

    def get_entry(self, creature_name: str) -> Optional[Dict[str, Any]]:
        """Return the bestiary entry for a creature, or None if unseen.

        The returned dict includes both tracking data and the creature's
        template data (stats, lore, etc.) if the creature exists in
        ``ALL_CREATURES``.
        """
        entry = self._entries.get(creature_name)
        if entry is None:
            return None

        result = dict(entry)
        # Attach template data if available
        template = ALL_CREATURES.get(creature_name)
        if template is not None:
            result["tongue"] = template.tongue.value
            result["tongue_name"] = TONGUE_NAMES[template.tongue]
            result["base_hp"] = template.base_hp
            result["base_atk"] = template.base_atk
            result["base_def"] = template.base_def
            result["base_spd"] = template.base_spd
            result["base_wis"] = template.base_wis
            result["is_rare"] = template.is_rare
            result["lore"] = template.lore
            result["evo_stage"] = template.evo_stage.value
        return result

    def completion_pct(self) -> float:
        """Return the percentage of all creatures that have been caught.

        Based on the total count in ``ALL_CREATURES``.

        Returns
        -------
        float
            0.0 to 100.0.
        """
        total = len(ALL_CREATURES)
        if total == 0:
            return 100.0
        caught = sum(
            1 for e in self._entries.values() if e.get("caught", False)
        )
        return round((caught / total) * 100.0, 2)

    def seen_pct(self) -> float:
        """Return the percentage of all creatures that have been seen."""
        total = len(ALL_CREATURES)
        if total == 0:
            return 100.0
        seen = sum(
            1 for e in self._entries.values() if e.get("seen", False)
        )
        return round((seen / total) * 100.0, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the bestiary to a plain dict (for save files).

        Returns
        -------
        Dict[str, Any]
            A JSON-serialisable dictionary.
        """
        return {
            "entries": {
                name: {
                    "seen": e["seen"],
                    "caught": e["caught"],
                    "seen_count": e["seen_count"],
                    "caught_count": e["caught_count"],
                }
                for name, e in self._entries.items()
            },
            "total_species": len(ALL_CREATURES),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Bestiary":
        """Deserialise a bestiary from a save-file dict.

        Parameters
        ----------
        data : Dict[str, Any]
            Output of ``to_dict()``.

        Returns
        -------
        Bestiary
            A restored Bestiary instance.
        """
        bestiary = cls()
        entries = data.get("entries", {})
        for name, entry_data in entries.items():
            bestiary._entries[name] = {
                "seen": entry_data.get("seen", False),
                "caught": entry_data.get("caught", False),
                "seen_count": entry_data.get("seen_count", 0),
                "caught_count": entry_data.get("caught_count", 0),
            }
        return bestiary

    def __repr__(self) -> str:
        seen = sum(1 for e in self._entries.values() if e.get("seen"))
        caught = sum(1 for e in self._entries.values() if e.get("caught"))
        total = len(ALL_CREATURES)
        return f"<Bestiary seen={seen}/{total} caught={caught}/{total}>"


# ===================================================================
# Self-test
# ===================================================================
def _selftest() -> None:
    """Validate encounters module without pygame."""
    print(f"\n{'=' * 60}")
    print("  encounters.py -- self-test")
    print(f"{'=' * 60}\n")

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

    # 1. Route definitions
    check("10 routes defined", len(AETHERMOOR_ROUTES) == 10,
          f"got {len(AETHERMOOR_ROUTES)}")
    for name, zone in AETHERMOOR_ROUTES.items():
        check(f"Route '{name}' encounter_rate in [0,1]",
              0.0 <= zone.encounter_rate <= 1.0,
              f"rate={zone.encounter_rate}")
        check(f"Route '{name}' level_range valid",
              zone.level_range[0] <= zone.level_range[1],
              f"range={zone.level_range}")

    # 2. Creature pools
    for tongue, pool in CREATURE_POOLS.items():
        check(f"Tongue {tongue.value} has >= 6 creatures",
              len(pool) >= 6,
              f"got {len(pool)}")
        rares = [c for c in pool if c.is_rare]
        commons = [c for c in pool if not c.is_rare]
        check(f"Tongue {tongue.value} has rare(s)",
              len(rares) >= 1,
              f"rares={len(rares)}")
        check(f"Tongue {tongue.value} has common(s)",
              len(commons) >= 5,
              f"commons={len(commons)}")
        for c in pool:
            check(f"  Creature '{c.name}' has moves",
                  len(c.native_moves) >= 1,
                  f"moves={len(c.native_moves)}")
            check(f"  Creature '{c.name}' tongue matches pool",
                  c.tongue == tongue,
                  f"expected {tongue.value}, got {c.tongue.value}")

    # 3. Total creature count
    total = len(ALL_CREATURES)
    check(f"Total unique creatures: {total} >= 36",
          total >= 36,
          f"got {total}")

    # 4. Encounter check mechanics
    table = EncounterTable(rng=random.Random(42))

    # With 0 steps, effective rate should be ~0 regardless of zone rate
    triggered_at_0 = sum(
        1 for _ in range(1000)
        if EncounterTable(rng=random.Random(_)).check_encounter("starter_village", 0)
    )
    check("Near-zero encounters at step 0",
          triggered_at_0 < 10,
          f"got {triggered_at_0}/1000")

    # With 100 steps on a high-rate zone, should be very likely
    triggered_at_100 = sum(
        1 for _ in range(1000)
        if EncounterTable(rng=random.Random(_)).check_encounter("world_tree_roots", 100)
    )
    check("High encounter rate at step 100",
          triggered_at_100 > 200,
          f"got {triggered_at_100}/1000")

    # 5. Encounter generation
    zone = AETHERMOOR_ROUTES["cassivadan_compute_mines"]
    enc = table.generate_encounter(zone, player_level=12)
    check("Encounter has 'name'", "name" in enc)
    check("Encounter has 'tongue'", "tongue" in enc)
    check("Encounter has 'level'", "level" in enc)
    check("Encounter has 'stats'", "stats" in enc)
    check("Encounter has 'moves'", "moves" in enc and len(enc["moves"]) >= 1)
    check("Encounter has 'catch_rate'", "catch_rate" in enc and 0.0 < enc["catch_rate"] < 1.0,
          f"catch_rate={enc.get('catch_rate')}")
    check("Encounter tongue is CA", enc["tongue"] == Tongue.CA,
          f"got {enc.get('tongue')}")
    check("Encounter level in zone range",
          zone.level_range[0] <= enc["level"] <= zone.level_range[1],
          f"level={enc['level']}")

    # 6. Mixed-tongue zone
    mixed_zone = AETHERMOOR_ROUTES["spiral_spire"]
    tongues_seen = set()
    for seed in range(200):
        t = EncounterTable(rng=random.Random(seed))
        e = t.generate_encounter(mixed_zone, player_level=25)
        tongues_seen.add(e["tongue"])
    check("Mixed zone produces multiple tongues",
          len(tongues_seen) >= 3,
          f"saw {len(tongues_seen)} tongues")

    # 7. step_encounter_check convenience function
    result = step_encounter_check("starter_village", steps=0, player_level=1)
    # May or may not trigger — just check it returns correct type
    check("step_encounter_check returns None or dict",
          result is None or isinstance(result, dict))
    check("step_encounter_check with invalid zone returns None",
          step_encounter_check("nonexistent_zone", 10) is None)

    # 8. Bestiary
    bestiary = Bestiary()
    bestiary.register_seen("Hash Slime")
    bestiary.register_seen("Hash Slime")  # double-see
    bestiary.register_caught("Decree Wisp")

    entry_slime = bestiary.get_entry("Hash Slime")
    check("Bestiary: Hash Slime seen", entry_slime is not None and entry_slime["seen"])
    check("Bestiary: Hash Slime seen_count=2",
          entry_slime is not None and entry_slime["seen_count"] == 2)
    check("Bestiary: Hash Slime not caught",
          entry_slime is not None and not entry_slime["caught"])

    entry_wisp = bestiary.get_entry("Decree Wisp")
    check("Bestiary: Decree Wisp caught",
          entry_wisp is not None and entry_wisp["caught"])
    check("Bestiary: Decree Wisp also seen",
          entry_wisp is not None and entry_wisp["seen"])

    check("Bestiary: unseen returns None",
          bestiary.get_entry("Nonexistent") is None)

    pct = bestiary.completion_pct()
    check(f"Bestiary: completion_pct > 0 ({pct}%)", pct > 0.0)
    check(f"Bestiary: completion_pct < 100 ({pct}%)", pct < 100.0)

    # Serialisation round-trip
    serialised = bestiary.to_dict()
    check("Bestiary: to_dict has 'entries'", "entries" in serialised)
    restored = Bestiary.from_dict(serialised)
    check("Bestiary: from_dict round-trip",
          restored.get_entry("Hash Slime") is not None)
    check("Bestiary: from_dict preserves caught",
          restored.get_entry("Decree Wisp")["caught"] is True)
    check("Bestiary: from_dict preserves seen_count",
          restored.get_entry("Hash Slime")["seen_count"] == 2)

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}\n")
    if failed == 0:
        print("  All encounter systems operational.\n")
    else:
        print(f"  WARNING: {failed} test(s) failed!\n")


if __name__ == "__main__":
    _selftest()
