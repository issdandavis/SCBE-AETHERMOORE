#!/usr/bin/env python3
"""
HexForge — 6-Arm Zero-G Chemistry Assembly Game (SFT Generator)
================================================================

A cooperative game where 6 players each control ONE arm of a hexagonal
forge suspended in a spherical zero-gravity workspace. Each player sees
the workspace from a DIFFERENT viewpoint (their tongue's compass bearing).
Together they must assemble chemical compounds by grabbing, rotating, and
bonding elements — all under time pressure.

Think: 3D printer with 6 independent arms, no gravity, and every operator
looking at the build from a different angle. Miscommunication = collision.
Coordination = compound.

The "3D^6 printer" concept:
  - 3 spatial axes (x, y, z) visible to ALL players
  - 6 rotational perspectives (one per tongue, 60° apart)
  - Each arm can REACH elements in its tongue's sector of the sphere
  - To build a compound, arms must bring elements to the CENTER
  - Zero-G means nothing stays put — you grab it or it drifts

Game structure:
  - Forge (workspace): sphere grid, radius 1.0
  - Arms: 6, one per tongue, anchored at compass positions
  - Elements: 36 total (6 per tongue sector, tongue-colored)
  - Compounds: recipes requiring 2-6 elements from different sectors
  - Views: each player sees the forge from their tongue's bearing
  - Timer: 30-120 seconds per compound depending on difficulty

Difficulty tiers:
  - Apprentice (0.1-0.3): 2-element compounds, generous time, no drift
  - Journeyman (0.3-0.5): 3-4 elements, moderate time, slow drift
  - Master (0.5-0.7): 4-5 elements, tight time, fast drift + rotation
  - Grandmaster (0.7-0.9): 5-6 elements, minimal time, full physics + interference

Concepts taught:
  1. Multi-perspective coordination (same object, 6 views)
  2. Sector responsibility (each arm owns its zone)
  3. Handoff in 3D (passing elements across sectors)
  4. Collision avoidance (arms in shared space)
  5. Time-pressure prioritization (which bond first?)
  6. Zero-G physics (drift, spin, momentum conservation)
  7. Chemistry (valence, bonds, stability, reactions)
  8. Communication protocols (call-outs, confirmations)

Output: training-data/sft/hexforge_assembly_sft.jsonl

References:
  - docs/SWARM_FORMATIONS.md (hexagonal, collision avoidance)
  - docs/specs/COUNTERWEIGHT_PHYSICAL_MORAL_TRAINING.md (gravity, forces)
  - notes/sphere-grid/ (sphere grid geometry, tongue sectors)
  - GeoSeal Compass (compass bearings, tongue positions)
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
SEED = 137

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}
TONGUE_COLORS = {
    "KO": "red",
    "AV": "orange",
    "RU": "yellow",
    "CA": "green",
    "UM": "blue",
    "DR": "purple",
}

# Squad names (arm operators)
ARM_NAMES = {
    "KO": "Blaze",
    "AV": "Echo",
    "RU": "Spark",
    "CA": "Moss",
    "UM": "Frost",
    "DR": "Shadow",
}

# Compass bearings (degrees, for viewpoint descriptions)
BEARINGS = {"KO": 0, "AV": 60, "RU": 120, "CA": 180, "UM": 240, "DR": 300}

# Each tongue "sector" contains 6 elements (36 total across the forge)
# Named with tongue flavor + element-like names
ELEMENTS = {
    "KO": ["Ignis", "Pyrex", "Flaris", "Solare", "Embera", "Volca"],
    "AV": ["Zephyr", "Auris", "Ventis", "Lumina", "Prisa", "Ethera"],
    "RU": ["Ferris", "Gravis", "Terros", "Forgia", "Anvis", "Runis"],
    "CA": ["Aquis", "Floris", "Verdis", "Mossia", "Rootis", "Sporia"],
    "UM": ["Glacia", "Crysta", "Frostis", "Abyssa", "Tidalis", "Noctis"],
    "DR": ["Umbris", "Phantis", "Voidis", "Nebula", "Spectra", "Eclipsa"],
}

# Compound recipes: name, required elements (tongue: element_index), time_limit, tier
COMPOUNDS = [
    # Apprentice (2 elements)
    {"name": "Ember Crystal", "recipe": {"KO": 0, "UM": 1}, "time": 90, "tier": "apprentice",
     "desc": "A warm crystal that glows from within"},
    {"name": "Storm Glass", "recipe": {"AV": 0, "CA": 2}, "time": 90, "tier": "apprentice",
     "desc": "Transparent solid that clouds before rain"},
    {"name": "Iron Bloom", "recipe": {"RU": 0, "CA": 3}, "time": 90, "tier": "apprentice",
     "desc": "Metal flower that grows in soil"},
    {"name": "Shadow Ice", "recipe": {"DR": 0, "UM": 0}, "time": 90, "tier": "apprentice",
     "desc": "Ice that absorbs light instead of reflecting"},
    {"name": "Solar Wind", "recipe": {"KO": 3, "AV": 2}, "time": 90, "tier": "apprentice",
     "desc": "Breeze that carries warmth across voids"},
    {"name": "Void Root", "recipe": {"DR": 2, "CA": 4}, "time": 90, "tier": "apprentice",
     "desc": "Plant that grows in darkness"},

    # Journeyman (3 elements)
    {"name": "Prism Forge", "recipe": {"KO": 1, "AV": 3, "RU": 5}, "time": 75, "tier": "journeyman",
     "desc": "Anvil that splits light into workable threads"},
    {"name": "Tidal Ember", "recipe": {"KO": 4, "UM": 4, "CA": 0}, "time": 75, "tier": "journeyman",
     "desc": "Flame that pulses with ocean rhythm"},
    {"name": "Eclipse Moss", "recipe": {"DR": 5, "CA": 5, "AV": 1}, "time": 75, "tier": "journeyman",
     "desc": "Growth that thrives in shadow cycles"},
    {"name": "Rune Frost", "recipe": {"RU": 3, "UM": 2, "DR": 1}, "time": 75, "tier": "journeyman",
     "desc": "Ice inscribed with self-writing symbols"},

    # Master (4-5 elements)
    {"name": "Hexagonal Lattice", "recipe": {"KO": 0, "AV": 0, "RU": 0, "CA": 0}, "time": 60, "tier": "master",
     "desc": "Crystal structure requiring 4 sectors to seed"},
    {"name": "Aurora Engine", "recipe": {"KO": 5, "AV": 5, "UM": 5, "DR": 3}, "time": 60, "tier": "master",
     "desc": "Device that paints light across the void"},
    {"name": "Living Alloy", "recipe": {"RU": 1, "CA": 1, "UM": 3, "AV": 4, "KO": 2}, "time": 50, "tier": "master",
     "desc": "Metal that heals its own cracks"},

    # Grandmaster (5-6 elements)
    {"name": "Philosopher's Sphere", "recipe": {"KO": 0, "AV": 1, "RU": 2, "CA": 3, "UM": 4, "DR": 5},
     "time": 45, "tier": "grandmaster",
     "desc": "Perfect sphere requiring one element from every sector"},
    {"name": "Tongue of Creation", "recipe": {"KO": 3, "AV": 3, "RU": 3, "CA": 3, "UM": 3, "DR": 3},
     "time": 40, "tier": "grandmaster",
     "desc": "The word that shapes matter — all six tongues speaking at once"},
    {"name": "Poincare Seed", "recipe": {"KO": 5, "RU": 4, "CA": 2, "UM": 0, "DR": 4},
     "time": 50, "tier": "grandmaster",
     "desc": "Compressed universe-fragment, requires near-boundary precision"},
]

TIERS = ["apprentice", "journeyman", "master", "grandmaster"]
TIER_DIFF = {
    "apprentice": (0.10, 0.30),
    "journeyman": (0.30, 0.50),
    "master": (0.50, 0.70),
    "grandmaster": (0.70, 0.90),
}

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "training-data" / "sft" / "hexforge_assembly_sft.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _arm(t: str) -> str:
    return f"{ARM_NAMES[t]}'s {TONGUE_COLORS[t]} arm"


def _elem(tongue: str, idx: int) -> str:
    return f"{ELEMENTS[tongue][idx]} ({TONGUE_COLORS[tongue]})"


def _recipe_str(recipe: Dict[str, int]) -> str:
    parts = []
    for t, idx in recipe.items():
        parts.append(_elem(t, idx))
    return " + ".join(parts)


def _opposite(t: str) -> str:
    idx = TONGUES.index(t)
    return TONGUES[(idx + 3) % 6]


def _neighbor(t: str, offset: int = 1) -> str:
    idx = TONGUES.index(t)
    return TONGUES[(idx + offset) % 6]


def _view_description(t: str) -> str:
    bearing = BEARINGS[t]
    opp = _opposite(t)
    return (
        f"{ARM_NAMES[t]} sees the forge from {bearing} degrees "
        f"({TONGUE_NAMES[t]} bearing). "
        f"Their sector is closest, {TONGUE_NAMES[opp]}'s sector is farthest."
    )


def _tongue_weights(dominant: str) -> Dict[str, float]:
    idx = TONGUES.index(dominant)
    weights = {}
    for i, t in enumerate(TONGUES):
        dist = min(abs(idx - i), 6 - abs(idx - i))
        weights[t] = round(max(0.1, 1.0 - dist * 0.25), 3)
    return weights


def _tier_layers(tier: str) -> List[int]:
    return {
        "apprentice": [1, 2, 3],
        "journeyman": [1, 2, 3, 4, 5],
        "master": [1, 2, 3, 4, 5, 6, 9],
        "grandmaster": [1, 2, 3, 4, 5, 6, 9, 10, 12],
    }.get(tier, [1, 2, 3])


def _tier_axioms(tier: str) -> List[str]:
    return {
        "apprentice": ["A5_composition", "A2_locality"],
        "journeyman": ["A5_composition", "A2_locality", "A3_causality"],
        "master": ["A5_composition", "A2_locality", "A3_causality", "A4_symmetry"],
        "grandmaster": ["A5_composition", "A2_locality", "A3_causality", "A4_symmetry", "A1_unitarity"],
    }.get(tier, ["A5_composition"])


@dataclass
class ForgeRecord:
    category: str
    system: str
    user: str
    assistant: str
    tier: str
    tongue: str
    compound: Optional[str] = None
    tags: List[str] = field(default_factory=list)


def record_to_sft(rec: ForgeRecord) -> dict:
    lo, hi = TIER_DIFF.get(rec.tier, (0.1, 0.3))
    diff = round(random.uniform(lo, hi), 3)
    content = rec.user + rec.assistant
    source_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
    tags = ["phase0", "hexforge", rec.category, rec.tier] + rec.tags
    if rec.compound:
        tags.append(f"compound-{rec.compound.lower().replace(' ', '-')}")
    return {
        "messages": [
            {"role": "system", "content": rec.system},
            {"role": "user", "content": rec.user},
            {"role": "assistant", "content": rec.assistant},
        ],
        "tongue_weights": _tongue_weights(rec.tongue),
        "dominant_tongue": rec.tongue,
        "layers": _tier_layers(rec.tier),
        "axioms": _tier_axioms(rec.tier),
        "difficulty": diff,
        "augmentation": f"hexforge-{rec.category}",
        "tags": tags,
        "source_hash": source_hash,
        "curriculum_phase": 0,
        "tpdff_weights": {
            "P1_smooth": round(1.0, 3),
            "P2_pattern": round(PHI, 3),
            "P3_bind": round(PHI ** 2, 3),
        },
    }


# ---------------------------------------------------------------------------
# System messages
# ---------------------------------------------------------------------------

SYS_BASE = (
    "[HEXFORGE: 6-Arm Zero-G Assembly] [SPHERE-GRID: Poincare Ball]\n"
    "You are operating one arm of a hexagonal forge in zero gravity. "
    "6 arms, 6 operators, 6 viewpoints. The forge is a sphere — "
    "your sector is nearest to you, the opposite sector is farthest. "
    "Elements float freely. Grab them before they drift. "
    "Bond elements at the center to build compounds. "
    "Communicate with your team — they see the SAME space from DIFFERENT angles."
)

SYS_GRAB = SYS_BASE + "\n[TASK: Grab & Hold]"
SYS_PASS = SYS_BASE + "\n[TASK: Cross-Sector Handoff]"
SYS_BUILD = SYS_BASE + "\n[TASK: Compound Assembly]"
SYS_COLLISION = SYS_BASE + "\n[TASK: Collision Avoidance]"
SYS_DRIFT = SYS_BASE + "\n[TASK: Zero-G Drift Management]"
SYS_VIEW = SYS_BASE + "\n[TASK: Multi-Viewpoint Coordination]"
SYS_RUSH = SYS_BASE + "\n[TASK: Time-Pressure Assembly]"
SYS_CHEM = SYS_BASE + "\n[TASK: Chemistry & Bonding]"
SYS_RESEARCH = SYS_BASE + (
    "\n[TASK: Real-Time Research Agent]\n"
    "You have an autonomous web research agent available mid-forge. "
    "When the team encounters an unknown compound, reaction, or physics anomaly, "
    "the research agent can search, verify, and report back within the forge's time pressure. "
    "Research costs time — every query burns seconds off the clock."
)


# ---------------------------------------------------------------------------
# Category generators
# ---------------------------------------------------------------------------


def gen_grab_and_hold(count: int) -> List[ForgeRecord]:
    """Grabbing elements in zero-G — momentum, drift, grip."""
    records = []
    for _ in range(count):
        t = random.choice(TONGUES)
        elem_idx = random.randint(0, 5)
        elem_name = ELEMENTS[t][elem_idx]
        opposite = _opposite(t)

        # Apprentice: grab from own sector
        records.append(ForgeRecord(
            category="grab", system=SYS_GRAB,
            user=f"{_arm(t)} needs to grab {elem_name} floating in the {TONGUE_COLORS[t]} sector. "
                 f"It's drifting slowly to the right. How?",
            assistant=f"Reach to where it WILL BE, not where it is now. In zero-G, objects keep moving. "
                      f"Approach from the side — if you reach straight at it, you'll push it away. "
                      f"Close your grip gently. A hard grab sends vibrations that shake nearby elements loose. "
                      f"Once held, pull it toward center SLOWLY — fast pulls spin you both. "
                      f"If it slips free, reset with the {opposite} arm instead of lunging.",
            tier="apprentice", tongue=t,
            tags=["own-sector", "drift-prediction"],
        ))

        # Journeyman: grab from adjacent sector
        adj = _neighbor(t)
        adj_elem = random.randint(0, 5)
        records.append(ForgeRecord(
            category="grab", system=SYS_GRAB,
            user=f"{_arm(t)} needs {_elem(adj, adj_elem)} from {ARM_NAMES[adj]}'s sector. "
                 f"Can they reach it?",
            assistant=f"Barely! Adjacent sectors overlap at the boundary. "
                      f"{_arm(t)} can reach about 30%% into {ARM_NAMES[adj]}'s zone. "
                      f"But it's risky — the arm is at full extension, grip strength is weaker. "
                      f"Better: ask {ARM_NAMES[adj]} to push {_elem(adj, adj_elem)} toward the boundary, "
                      f"then {ARM_NAMES[t]} catches it in the overlap zone. "
                      f"Cooperative grab > solo overreach.",
            tier="journeyman", tongue=t,
            tags=["adjacent-sector", "boundary-grab"],
        ))

        # Master: grab spinning element
        spin_elem = random.randint(0, 5)
        records.append(ForgeRecord(
            category="grab", system=SYS_GRAB,
            user=f"{_elem(t, spin_elem)} is spinning fast (2 rotations per second) and drifting toward the boundary. "
                 f"If it hits the boundary, it bounces and scatters other elements. "
                 f"How does {ARM_NAMES[t]} catch it?",
            assistant=f"Match the spin first! Rotate the gripper at the same speed and direction. "
                      f"A stationary grip on a spinning object = TORQUE — it'll rip free or send the arm spinning. "
                      f"Approach from the spin AXIS (the still point). "
                      f"Grab the axis, then slow the spin gradually. "
                      f"Priority: catch before boundary hit. Even a wobbly grip is better than a scatter event. "
                      f"Call out: '{ARM_NAMES[t]} catching spinner, clear sector {TONGUE_COLORS[t]}!'",
            tier="master", tongue=t,
            tags=["spinning", "boundary-save"],
        ))

    return records


def gen_cross_handoff(count: int) -> List[ForgeRecord]:
    """Passing elements between arms across sectors."""
    records = []
    for _ in range(count):
        sender = random.choice(TONGUES)
        receiver = random.choice([t for t in TONGUES if t != sender])
        elem_idx = random.randint(0, 5)
        # Apprentice: neighbor handoff
        nbr = _neighbor(sender)
        records.append(ForgeRecord(
            category="handoff", system=SYS_PASS,
            user=f"{ARM_NAMES[sender]} has {_elem(sender, elem_idx)} and needs to pass it to {ARM_NAMES[nbr]}. "
                 f"They're neighbors (60 degrees apart). How?",
            assistant=f"Short pass! {ARM_NAMES[sender]} extends toward the boundary between their sectors. "
                      f"{ARM_NAMES[nbr]} reaches to meet. "
                      f"The handoff point is the MIDPOINT between their anchor positions. "
                      f"Release and grab must happen at the SAME moment — "
                      f"in zero-G, an uncaught element drifts immediately. "
                      f"Call: '{ARM_NAMES[sender]}: passing {ELEMENTS[sender][elem_idx]}, 3... 2... 1... release!' "
                      f"'{ARM_NAMES[nbr]}: caught!'",
            tier="apprentice", tongue=sender,
            tags=["neighbor-pass", "timing"],
        ))

        # Journeyman: cross-forge (opposite side)
        opp = _opposite(sender)
        records.append(ForgeRecord(
            category="handoff", system=SYS_PASS,
            user=f"{ARM_NAMES[sender]} has {_elem(sender, 0)} but it needs to reach {ARM_NAMES[opp]} "
                 f"on the OPPOSITE side of the forge. That's 180 degrees away. Strategy?",
            assistant=f"DON'T throw across the forge! A 180-degree throw crosses through the center "
                      f"where other arms are working — collision risk is maximum. "
                      f"Instead: RELAY CHAIN. Pass to neighbor, who passes to their neighbor, who passes to {ARM_NAMES[opp]}. "
                      f"3 short hops beats 1 long throw. "
                      f"Route: {ARM_NAMES[sender]} -> {ARM_NAMES[_neighbor(sender)]} -> "
                      f"{ARM_NAMES[_neighbor(sender, 2)]} -> {ARM_NAMES[opp]}. "
                      f"Each hop is 60 degrees — safe, short, reliable.",
            tier="journeyman", tongue=sender,
            tags=["relay-chain", "no-cross-throw"],
        ))

        # Master: handoff during drift
        records.append(ForgeRecord(
            category="handoff", system=SYS_PASS,
            user=f"The forge is rotating (the whole sphere is spinning slowly). "
                 f"All elements are drifting clockwise. "
                 f"{ARM_NAMES[sender]} needs to pass {_elem(sender, 3)} to {ARM_NAMES[_neighbor(sender)]}. "
                 f"How does rotation affect the handoff?",
            assistant=f"The Coriolis effect! In a rotating frame, objects curve. "
                      f"If {ARM_NAMES[sender]} releases straight toward {ARM_NAMES[_neighbor(sender)]}, "
                      f"the element will curve AWAY (deflected by rotation). "
                      f"Compensate: aim AHEAD of {ARM_NAMES[_neighbor(sender)]}'s current position. "
                      f"Lead the pass — like throwing a ball to where someone is RUNNING to, not where they are. "
                      f"The faster the forge spins, the more you lead. "
                      f"Call: '{ARM_NAMES[sender]}: passing with lead, compensating for spin!'",
            tier="master", tongue=sender,
            tags=["coriolis", "rotating-frame", "lead-pass"],
        ))

    return records


def gen_compound_assembly(count: int) -> List[ForgeRecord]:
    """Building compounds from recipes — the core game loop."""
    records = []
    for _ in range(count):
        compound = random.choice(COMPOUNDS)
        tongue = random.choice(list(compound["recipe"].keys()))
        recipe = compound["recipe"]
        n_elements = len(recipe)

        # Assembly planning
        records.append(ForgeRecord(
            category="assembly", system=SYS_BUILD,
            user=f"Recipe: {compound['name']} — {compound['desc']}. "
                 f"Required: {_recipe_str(recipe)}. "
                 f"Time limit: {compound['time']} seconds. "
                 f"Which arms move first?",
            assistant=_assembly_plan(compound),
            tier=compound["tier"], tongue=tongue, compound=compound["name"],
            tags=["planning", f"{n_elements}-element"],
        ))

        # Mid-assembly problem
        problem_tongue = random.choice(list(recipe.keys()))
        records.append(ForgeRecord(
            category="assembly", system=SYS_BUILD,
            user=f"Building {compound['name']}. {ARM_NAMES[problem_tongue]}'s element "
                 f"({_elem(problem_tongue, recipe[problem_tongue])}) is stuck to the sphere wall. "
                 f"It won't detach. {compound['time'] - 20} seconds left. Options?",
            assistant=_stuck_element_response(compound, problem_tongue),
            tier=compound["tier"], tongue=tongue, compound=compound["name"],
            tags=["stuck-element", "time-pressure"],
        ))

        # Bonding sequence
        records.append(ForgeRecord(
            category="assembly", system=SYS_BUILD,
            user=f"All elements for {compound['name']} are at the center. "
                 f"What order do we bond them?",
            assistant=_bonding_order(compound),
            tier=compound["tier"], tongue=tongue, compound=compound["name"],
            tags=["bonding-sequence", "chemistry"],
        ))

    return records


def _assembly_plan(compound: dict) -> str:
    recipe = compound["recipe"]
    tongues = list(recipe.keys())
    n = len(tongues)

    if n <= 2:
        return (
            f"Both arms move simultaneously! {ARM_NAMES[tongues[0]]} grabs {_elem(tongues[0], recipe[tongues[0]])} "
            f"and {ARM_NAMES[tongues[1]]} grabs {_elem(tongues[1], recipe[tongues[1]])}. "
            f"Meet at the center. With only 2 elements, coordination is simple — "
            f"just time the arrival so both reach center within 2 seconds of each other. "
            f"Bond on contact."
        )
    elif n <= 4:
        first_pair = tongues[:2]
        rest = tongues[2:]
        return (
            f"Stagger! First wave: {ARM_NAMES[first_pair[0]]} and {ARM_NAMES[first_pair[1]]} "
            f"grab their elements and bring to center. "
            f"Second wave ({', '.join(ARM_NAMES[t] for t in rest)}) starts grabbing WHILE first wave transits. "
            f"By the time wave 2 arrives at center, wave 1 has already formed the initial bond. "
            f"This is pipeline assembly — overlap grab and transit phases. "
            f"Never wait for ALL elements before starting the first bond."
        )
    else:
        return (
            f"Full forge activation! All 6 arms grab simultaneously. "
            f"The risk: 6 arms converging on center at once = collision city. "
            f"Use ALTITUDE LANES: {ARM_NAMES[tongues[0]]} and {ARM_NAMES[tongues[1]]} approach from above (z+), "
            f"{ARM_NAMES[tongues[2]]} and {ARM_NAMES[tongues[3]]} from the equator (z=0), "
            f"{ARM_NAMES[tongues[4]]} and {ARM_NAMES[tongues[5] if len(tongues) > 5 else tongues[-1]]} from below (z-). "
            f"3 altitude bands, 2 arms each, staggered by 5 seconds. "
            f"This is the 3D^6 pattern — 6 arms, 3 lanes, zero collisions."
        )


def _stuck_element_response(compound: dict, stuck_tongue: str) -> str:
    recipe = compound["recipe"]
    neighbors = [_neighbor(stuck_tongue, 1), _neighbor(stuck_tongue, -1)]
    [n for n in neighbors if n in recipe]

    return (
        f"Option 1: VIBRATE. {ARM_NAMES[stuck_tongue]} oscillates their grip rapidly — "
        f"micro-vibrations break the surface adhesion. Works 80%% of the time in zero-G. "
        f"Option 2: NEIGHBOR ASSIST. {ARM_NAMES[neighbors[0]]} pushes against the element from the side "
        f"while {ARM_NAMES[stuck_tongue]} pulls. Shear force > pull force for wall adhesion. "
        f"Option 3: SUBSTITUTE. If {ELEMENTS[stuck_tongue][recipe[stuck_tongue]]} won't come free, "
        f"check if another element in the {TONGUE_COLORS[stuck_tongue]} sector has similar valence. "
        f"Wrong element = unstable compound, but an unstable compound beats no compound with 20 seconds left. "
        f"Decision: try vibrate for 5 seconds. If no luck, go to neighbor assist. "
        f"Don't waste more than 10 seconds on a stuck element."
    )


def _bonding_order(compound: dict) -> str:
    recipe = compound["recipe"]
    tongues = list(recipe.keys())
    n = len(tongues)

    if n == 2:
        return (
            f"Direct bond! Press {_elem(tongues[0], recipe[tongues[0]])} "
            f"against {_elem(tongues[1], recipe[tongues[1]])}. "
            f"Hold for 3 seconds while the lattice forms. "
            f"Both arms must hold STILL — any wobble during bonding creates a crack. "
            f"The bond is strongest when elements are aligned along the axis between their tongue sectors."
        )
    elif n <= 4:
        return (
            f"Build a BACKBONE first. Bond the two elements from the most DIFFERENT sectors — "
            f"that's {_elem(tongues[0], recipe[tongues[0]])} and "
            f"{_elem(tongues[-1], recipe[tongues[-1]])} (farthest apart). "
            f"The backbone is the strongest bond because opposite elements have maximum contrast. "
            f"Then attach the middle elements one at a time. "
            f"Each new element bonds to the backbone at its natural position (closest to its sector). "
            f"Think of it like building a bridge from both ends, then filling the middle."
        )
    else:
        return (
            f"HEXAGONAL BONDING SEQUENCE — the signature move. "
            f"Step 1: Form a ring. Each element touches its two neighbors (by tongue compass order). "
            f"Step 2: All 6 arms push INWARD simultaneously — gentle, steady pressure. "
            f"Step 3: The ring collapses into a sphere as bonds form between ALL adjacent pairs. "
            f"Step 4: Hold for 5 full seconds. The compound crystallizes. "
            f"If ANY arm releases early, the sphere opens and elements scatter. "
            f"This requires PERFECT coordination — all 6 arms pushing with equal force. "
            f"Too much from one arm = lopsided, compound shatters. "
            f"Call: 'FORGE! 5... 4... 3... 2... 1... RELEASE!' All arms retract together."
        )


def gen_collision_avoidance(count: int) -> List[ForgeRecord]:
    """Arms in shared space — don't crash into each other."""
    records = []
    for _ in range(count):
        t1, t2 = random.sample(TONGUES, 2)
        tongue = t1

        # Apprentice: basic awareness
        records.append(ForgeRecord(
            category="collision", system=SYS_COLLISION,
            user=f"{_arm(t1)} and {_arm(t2)} are both reaching for the center at the same time. "
                 f"Their paths cross. What do they do?",
            assistant=f"RIGHT OF WAY rule: the arm from the LOWER compass bearing goes first. "
                      f"{TONGUE_NAMES[t1]} is at {BEARINGS[t1]} degrees, "
                      f"{TONGUE_NAMES[t2]} is at {BEARINGS[t2]} degrees. "
                      f"{'So ' + ARM_NAMES[t1] + ' goes first.' if BEARINGS[t1] < BEARINGS[t2] else 'So ' + ARM_NAMES[t2] + ' goes first.'} "
                      f"The other arm PAUSES at the boundary of the overlap zone until the first arm clears. "
                      f"Never trust that the other arm will dodge — always yield by protocol.",
            tier="apprentice", tongue=tongue,
            tags=["right-of-way"],
        ))

        # Journeyman: 3 arms converging
        t3 = random.choice([t for t in TONGUES if t not in [t1, t2]])
        records.append(ForgeRecord(
            category="collision", system=SYS_COLLISION,
            user=f"Three arms converging on center: {_arm(t1)}, {_arm(t2)}, and {_arm(t3)}. "
                 f"That's half the forge moving at once. How to avoid a 3-way collision?",
            assistant=f"ALTITUDE SEPARATION. Assign each arm a z-level: "
                      f"{ARM_NAMES[t1]} at z=+0.3 (high), "
                      f"{ARM_NAMES[t2]} at z=0.0 (equator), "
                      f"{ARM_NAMES[t3]} at z=-0.3 (low). "
                      f"All three approach center but at different heights — they can't collide. "
                      f"At center, they stack vertically, grab what they need, and retract at their altitude. "
                      f"Rule: more than 2 arms moving? Use altitude lanes. Always.",
            tier="journeyman", tongue=tongue,
            tags=["altitude-lanes", "three-way"],
        ))

        # Master: emergency dodge
        records.append(ForgeRecord(
            category="collision", system=SYS_COLLISION,
            user=f"A loose element bounces off the wall and tumbles toward the center "
                 f"where {_arm(t1)} is mid-bond. No time for protocol. What now?",
            assistant=f"EMERGENCY RETRACT! {ARM_NAMES[t1]} pulls back to their sector immediately. "
                      f"Yes, this breaks the current bond — but a collision would scatter EVERYTHING. "
                      f"Simultaneously, the arm NEAREST the loose element ({ARM_NAMES[_neighbor(t1)]}) "
                      f"catches or deflects it AWAY from center. "
                      f"After the save: re-approach, re-bond. Lost time: ~15 seconds. "
                      f"A collision would cost 30+ seconds and potentially damage the compound. "
                      f"Rule: ALWAYS sacrifice a bond to avoid a collision. Bonds rebuild. Shattered compounds don't.",
            tier="master", tongue=tongue,
            tags=["emergency-retract", "sacrifice-bond"],
        ))

    return records


def gen_zero_g_drift(count: int) -> List[ForgeRecord]:
    """Managing objects and momentum in zero gravity."""
    records = []
    for _ in range(count):
        t = random.choice(TONGUES)
        elem_idx = random.randint(0, 5)

        # Apprentice: basics of drift
        records.append(ForgeRecord(
            category="drift", system=SYS_DRIFT,
            user=f"{ARM_NAMES[t]} releases {_elem(t, elem_idx)} at the center. "
                 f"What happens to it?",
            assistant=f"It keeps moving! In zero-G, there's no gravity to stop it. "
                      f"Whatever direction and speed it had when released — that's its new forever-path. "
                      f"If {ARM_NAMES[t]} released while moving their arm right, the element drifts right. "
                      f"To leave an element STATIONARY at center: "
                      f"bring it there, STOP your arm completely, THEN open the grip. "
                      f"Zero velocity at release = zero drift. This is the hardest basic skill.",
            tier="apprentice", tongue=t,
            tags=["momentum-conservation", "stationary-release"],
        ))

        # Journeyman: Newton's third law
        records.append(ForgeRecord(
            category="drift", system=SYS_DRIFT,
            user=f"{ARM_NAMES[t]} pushes a heavy element toward center. "
                 f"But the arm itself gets pushed BACKWARD. Why?",
            assistant=f"Newton's third law — every push has an equal push back. "
                      f"In zero-G, there's no floor to brace against. "
                      f"When {ARM_NAMES[t]} pushes the element forward, the arm moves backward. "
                      f"Fix: BRACE the arm against the sphere wall before pushing. "
                      f"Use the wall as your anchor. Push off the wall -> into the element. "
                      f"No bracing = both you and the element drift in opposite directions. "
                      f"This is why the forge has fixed anchor points for each arm.",
            tier="journeyman", tongue=t,
            tags=["newtons-third", "bracing"],
        ))

        # Master: chain reaction drift
        records.append(ForgeRecord(
            category="drift", system=SYS_DRIFT,
            user=f"During a {len(TONGUES)}-element assembly, {ARM_NAMES[t]} bumps one element, "
                 f"which bumps another, which bumps a third — a chain reaction of drifting elements. "
                 f"How to recover?",
            assistant=f"TRIAGE by distance from boundary. "
                      f"Elements closest to the sphere wall are in most danger (they'll bounce and scatter more). "
                      f"Elements near center are safer (more time before they reach anything). "
                      f"Step 1: NEAREST arm to each drifting element calls it out: "
                      f"'{ARM_NAMES[t]}: I've got the red one, heading wall-ward!' "
                      f"Step 2: Catch wall-bound elements FIRST. "
                      f"Step 3: Center elements can wait — they're slow and far from walls. "
                      f"Step 4: Once caught, HOLD in place. Don't try to re-assemble until ALL elements are secured. "
                      f"Rushing reassembly during a drift crisis = more collisions.",
            tier="master", tongue=t,
            tags=["chain-reaction", "triage"],
        ))

    return records


def gen_multi_viewpoint(count: int) -> List[ForgeRecord]:
    """Different operators seeing different things from different angles."""
    records = []
    for _ in range(count):
        t = random.choice(TONGUES)
        opp = _opposite(t)

        # Apprentice: basic perspective difference
        records.append(ForgeRecord(
            category="viewpoint", system=SYS_VIEW,
            user=f"{ARM_NAMES[t]} says an element is 'on the left.' "
                 f"But {ARM_NAMES[opp]} says it's 'on the right.' Who's correct?",
            assistant=f"BOTH! They're looking from opposite sides of the forge. "
                      f"{ARM_NAMES[t]}'s left IS {ARM_NAMES[opp]}'s right. "
                      f"This is the #1 mistake in multi-viewpoint forging. "
                      f"Fix: NEVER say left/right/up/down. Use TONGUE DIRECTIONS: "
                      f"'It's near the {TONGUE_COLORS[t]} sector' or 'drifting toward {TONGUE_NAMES[opp]} bearing.' "
                      f"Tongue bearings are absolute. Left/right are relative. "
                      f"Absolute coordinates save lives in zero-G.",
            tier="apprentice", tongue=t,
            tags=["perspective-flip", "absolute-coordinates"],
        ))

        # Journeyman: hidden element
        blocker = _neighbor(t)
        records.append(ForgeRecord(
            category="viewpoint", system=SYS_VIEW,
            user=f"{ARM_NAMES[t]} can't see {_elem(opp, 2)} because {_elem(blocker, 4)} is blocking the view. "
                 f"But {ARM_NAMES[_neighbor(t, 2)]} CAN see it. "
                 f"How do they coordinate?",
            assistant=f"{ARM_NAMES[_neighbor(t, 2)]} becomes {ARM_NAMES[t]}'s EYES for this element. "
                      f"They call out position updates in tongue bearings: "
                      f"'{_elem(opp, 2)} is at radius 0.4, bearing {BEARINGS[opp]} degrees, drifting toward {TONGUE_COLORS[blocker]}.' "
                      f"{ARM_NAMES[t]} moves their arm based on verbal guidance alone. "
                      f"This is BLIND OPERATION — one of the hardest skills. "
                      f"The guide must give CONTINUOUS updates, not just snapshots. "
                      f"'Still drifting... now stopped... you're 0.1 away... GRAB!' "
                      f"Trust your teammate's eyes when yours fail.",
            tier="journeyman", tongue=t,
            tags=["blind-operation", "verbal-guidance"],
        ))

        # Master: conflicting observations
        t1, t2, t3 = random.sample(TONGUES, 3)
        records.append(ForgeRecord(
            category="viewpoint", system=SYS_VIEW,
            user=f"Three operators report on the same element: "
                 f"{ARM_NAMES[t1]} says it's spinning clockwise. "
                 f"{ARM_NAMES[t2]} says it's spinning counterclockwise. "
                 f"{ARM_NAMES[t3]} says it's not spinning at all. "
                 f"How is this possible?",
            assistant=f"All three are correct! It depends on which AXIS you observe from. "
                      f"A spinning top looks clockwise from above, counterclockwise from below, "
                      f"and not spinning at all from the side (you just see it wobble). "
                      f"{ARM_NAMES[t1]} and {ARM_NAMES[t2]} are on opposite sides of the spin axis. "
                      f"{ARM_NAMES[t3]} is perpendicular to it. "
                      f"Resolution: report spin by AXIS, not direction. "
                      f"'Spinning around the {TONGUE_COLORS[t1]}-{TONGUE_COLORS[_opposite(t1)]} axis.' "
                      f"The axis is the same from every viewpoint. Direction depends on which side you're on.",
            tier="master", tongue=t1,
            tags=["spin-paradox", "axis-reporting"],
        ))

    return records


def gen_time_pressure(count: int) -> List[ForgeRecord]:
    """Decision-making under time constraints."""
    records = []
    for _ in range(count):
        compound = random.choice(COMPOUNDS)
        tongue = random.choice(list(compound["recipe"].keys()))
        recipe = compound["recipe"]

        # Apprentice: prioritization
        records.append(ForgeRecord(
            category="rush", system=SYS_RUSH,
            user=f"Building {compound['name']}. {compound['time']} second timer. "
                 f"{len(recipe)} elements needed. What's the biggest time sink?",
            assistant=f"TRANSIT, not grabbing. Grabbing an element takes ~3 seconds. "
                      f"Moving it to center takes ~8-12 seconds (longer for far sectors). "
                      f"Bonding takes ~3-5 seconds per pair. "
                      f"So for {len(recipe)} elements: grab = {len(recipe) * 3}s, "
                      f"transit = {len(recipe) * 10}s, bond = {(len(recipe) - 1) * 4}s. "
                      f"Total if sequential: ~{len(recipe) * 3 + len(recipe) * 10 + (len(recipe) - 1) * 4}s. "
                      f"But you have {len(recipe)} arms! Parallelize the grabs and transits. "
                      f"All arms grab at once = grab phase drops to 3s total. "
                      f"All arms transit at once = transit drops to ~12s total. "
                      f"Parallel forging turns {len(recipe) * 13}s into ~20s. That's the 3D^6 advantage.",
            tier=compound["tier"], tongue=tongue, compound=compound["name"],
            tags=["time-analysis", "parallelization"],
        ))

        # Journeyman: abort or commit
        records.append(ForgeRecord(
            category="rush", system=SYS_RUSH,
            user=f"15 seconds left. {compound['name']} is 70%% bonded but missing one element. "
                 f"{ARM_NAMES[tongue]} is still grabbing it. Finish or abort?",
            assistant=f"COMMIT if the missing element is already in hand and transit time is under 10 seconds. "
                      f"ABORT if it's still stuck on the wall or in a far sector. "
                      f"A 70%% bonded compound CAN be saved — partially bonded structures are stable for ~30 seconds. "
                      f"But a 70%% compound with a rushed final bond = unstable, might shatter. "
                      f"Decision framework: "
                      f"(time remaining) > (transit time + 5 seconds for clean bond) = COMMIT. "
                      f"Otherwise = ABORT, save the partial, try next round.",
            tier=compound["tier"], tongue=tongue, compound=compound["name"],
            tags=["abort-commit", "decision-framework"],
        ))

    return records


def gen_chemistry(count: int) -> List[ForgeRecord]:
    """Chemical bonding and reaction logic in the forge."""
    records = []
    for _ in range(count):
        t = random.choice(TONGUES)
        opp = _opposite(t)

        # Apprentice: why elements combine
        records.append(ForgeRecord(
            category="chemistry", system=SYS_CHEM,
            user=f"Why does {_elem(t, 0)} bond with {_elem(opp, 0)} but NOT with {_elem(t, 1)}?",
            assistant=f"OPPOSITE ATTRACTION. Elements from opposite sectors have complementary valence — "
                      f"{TONGUE_COLORS[t]} and {TONGUE_COLORS[opp]} are on opposite sides of the compass. "
                      f"They 'want' to combine because they fill each other's gaps. "
                      f"Elements from the SAME sector are too similar — "
                      f"putting {_elem(t, 0)} next to {_elem(t, 1)} is like pushing same-pole magnets together. "
                      f"Forge rule: bonds are STRONGEST between opposite sectors, "
                      f"MEDIUM between adjacent sectors, and WEAKEST within the same sector.",
            tier="apprentice", tongue=t,
            tags=["valence", "opposite-bonding"],
        ))

        # Journeyman: stability
        records.append(ForgeRecord(
            category="chemistry", system=SYS_CHEM,
            user=f"A 3-element compound was built with elements from {TONGUE_NAMES[t]}, "
                 f"{TONGUE_NAMES[_neighbor(t)]}, and {TONGUE_NAMES[_neighbor(t, 2)]}. "
                 f"All three are from the SAME HALF of the compass. Is it stable?",
            assistant=f"UNSTABLE. A compound needs BALANCE — elements from both halves of the compass. "
                      f"All three from the same half means the compound's 'center of charge' is off-center. "
                      f"It'll slowly drift toward the opposite wall and eventually shatter. "
                      f"Fix: add a 4th element from the opposite half "
                      f"({TONGUE_NAMES[_opposite(t)]} or neighbors). "
                      f"A balanced compound floats in the center. An unbalanced one always drifts. "
                      f"Chemistry rule: compounds want SYMMETRY across the compass.",
            tier="journeyman", tongue=t,
            tags=["stability", "charge-balance"],
        ))

        # Master: chain reaction
        records.append(ForgeRecord(
            category="chemistry", system=SYS_CHEM,
            user=f"If {_elem(t, 2)} and {_elem(opp, 3)} bond, they release energy (exothermic). "
                 f"That energy pulse could knock nearby elements loose. "
                 f"How to do a safe bond?",
            assistant=f"SHIELDED BONDING. Before pressing the elements together: "
                      f"Step 1: Clear the center — all other elements pulled to their home sectors. "
                      f"Step 2: Only the 2 bonding arms in the center. "
                      f"Step 3: The other 4 arms form a CONTAINMENT RING around the bond point. "
                      f"Step 4: Bond. The energy pulse radiates outward — the containment arms absorb it. "
                      f"Step 5: Once the pulse settles (~2 seconds), safe to bring other elements back. "
                      f"Exothermic bonds are POWERFUL but dangerous. "
                      f"The energy follows the inverse-square law — containment arms at radius 0.3 "
                      f"feel 1/9th the force of an arm at radius 0.1. Distance is safety.",
            tier="master", tongue=t,
            tags=["exothermic", "containment-ring", "energy-management"],
        ))

    return records


def gen_web_research(count: int) -> List[ForgeRecord]:
    """Autonomous web agent: real-time research mid-forge to solve unknowns."""
    records = []

    # Research scenarios — unknowns that require looking things up mid-task
    RESEARCH_QUERIES = [
        {
            "unknown": "crystal lattice angles for hexagonal bonding",
            "context": "Forge team is building a Hexagonal Lattice but disagrees on the bond angle (60 or 120 degrees)",
            "finding": "Hexagonal close-packing uses 60-degree inter-atomic angles within a layer, "
                       "120 degrees between alternating vertices. For the forge, this means: "
                       "adjacent elements bond at 60 degrees, skip-one elements at 120 degrees. "
                       "The team was BOTH right — different layers of the same structure.",
            "tier": "journeyman",
        },
        {
            "unknown": "exothermic reaction containment in microgravity",
            "context": "An opposite-sector bond released a heat pulse that scattered 3 elements. "
                       "Team wants to know if there's a better containment geometry than a ring",
            "finding": "NASA ISS experiments show TETRAHEDRAL containment outperforms ring containment "
                       "in microgravity — 4 points of contact absorb energy in 3 axes, not just 2. "
                       "Adapt for forge: 4 idle arms form a tetrahedron around the bonding pair. "
                       "The 2 bonding arms are inside, 4 containment arms outside. "
                       "Energy absorption is ~3x better than the flat ring.",
            "tier": "master",
        },
        {
            "unknown": "Coriolis compensation formula for rotating frames",
            "context": "Forge is spinning at 0.5 rad/s. Handoffs keep missing because nobody can "
                       "calculate the lead angle fast enough",
            "finding": "For a rotating frame at angular velocity omega, the deflection angle is "
                       "approximately 2*omega*t*sin(latitude), where t is transit time and latitude "
                       "is the angle from the rotation axis. "
                       "At 0.5 rad/s with 2-second transit: deflection is about 30 degrees. "
                       "Rule of thumb: lead by one tongue-sector per 0.5 rad/s of spin.",
            "tier": "master",
        },
        {
            "unknown": "chemical valence in a 6-element symmetric compound",
            "context": "Trying to build the Philosopher's Sphere (all 6 sectors). "
                       "Does element ordering matter for a symmetric compound?",
            "finding": "In crystallography, symmetric compounds follow Pauling's rules — "
                       "highest-valence elements form the core, lower-valence elements wrap outside. "
                       "For the forge: the element from the HEAVIEST tongue (Draumric, phi^5 weight) "
                       "should be the seed at center. Build outward by descending tongue weight. "
                       "This follows the Langues Weighting System — heavier tongues = deeper roles.",
            "tier": "grandmaster",
        },
        {
            "unknown": "momentum transfer efficiency in relay chains",
            "context": "A 3-hop relay chain loses ~30% element velocity per handoff. "
                       "Is there a way to reduce loss?",
            "finding": "Each handoff has a grip-loss window (release to catch) where the element "
                       "is uncontrolled. Shorter windows = less drift error. "
                       "Reduce loss by OVERLAPPING grips: the catcher grabs BEFORE the sender releases. "
                       "Both hold simultaneously for 0.5 seconds, then sender opens. "
                       "This 'overlap relay' cuts velocity loss to ~5% per hop. "
                       "The cost: both arms are occupied during overlap.",
            "tier": "journeyman",
        },
        {
            "unknown": "surface adhesion forces in zero-gravity sphere grids",
            "context": "Elements keep sticking to the sphere wall. Why is adhesion stronger in 0g?",
            "finding": "Without gravity pulling objects away from surfaces, even weak forces "
                       "(van der Waals, electrostatic) dominate. In 1g, gravity overcomes adhesion "
                       "for objects heavier than ~1mg. In 0g, there's no competing force. "
                       "Forge solution: coat the sphere wall with a repulsive field (electrostatic) "
                       "that gently pushes elements toward center. Or vibrate the wall — ISS uses "
                       "this technique to prevent equipment drift.",
            "tier": "apprentice",
        },
        {
            "unknown": "phase transition during bonding under time pressure",
            "context": "The bond between two elements is taking twice as long as usual. "
                       "Temperature in the forge zone dropped. Is it related?",
            "finding": "Cold slows molecular bonding — reaction rates follow the Arrhenius equation: "
                       "rate = A * exp(-Ea/RT). Lower T = exponentially slower bonding. "
                       "The forge center cooled because the last exothermic reaction exhausted local energy. "
                       "Fix: pre-warm the bond site. Use a neighboring arm to bring a warm element NEAR "
                       "(not touching) the bond point. Radiant heat from a hot element acts as a catalyst. "
                       "Do NOT rush the bond — a cold bond is a weak bond.",
            "tier": "master",
        },
        {
            "unknown": "optimal arm reach angles for blind operation",
            "context": "Guiding a blind arm via verbal commands. What grip angle minimizes drops?",
            "finding": "Ergonomics research shows grip strength peaks at 15-degree wrist flexion. "
                       "In the forge: the guide should direct the blind arm to approach elements "
                       "at a 15-degree offset from perpendicular. Not straight-on (0 degrees, "
                       "requires perfect alignment) and not from the side (90 degrees, weakest grip). "
                       "Call out: 'approach from your 2 o'clock, 15 degrees off center.'",
            "tier": "journeyman",
        },
    ]

    RESEARCH_ACTIONS = [
        "search", "verify", "calculate", "compare", "look-up", "cross-reference",
    ]

    for _ in range(count):
        scenario = random.choice(RESEARCH_QUERIES)
        t = random.choice(TONGUES)
        action = random.choice(RESEARCH_ACTIONS)

        # Apprentice: basic "should we research or just do it?"
        records.append(ForgeRecord(
            category="research", system=SYS_RESEARCH,
            user=f"Unknown situation in the forge: {scenario['context']}. "
                 f"Should {ARM_NAMES[t]} pause to research, or just try something?",
            assistant=f"RESEARCH COST-BENEFIT: a search takes ~5 seconds of forge time. "
                      f"If more than 30 seconds remain, RESEARCH — 5 seconds for knowledge "
                      f"saves 15+ seconds of trial-and-error. "
                      f"If under 15 seconds, JUST ACT — use best guess, fix later. "
                      f"Between 15-30 seconds: research ONLY if the unknown could cause a catastrophic failure "
                      f"(scatter event, compound shatter, arm collision). "
                      f"Right now this is a {scenario['tier']}-level situation. "
                      f"My recommendation: {'research it' if scenario['tier'] != 'apprentice' else 'act first, it is basic enough to handle by instinct'}.",
            tier="apprentice", tongue=t,
            tags=["research-decision", "cost-benefit"],
        ))

        # Journeyman: actual research mid-forge
        records.append(ForgeRecord(
            category="research", system=SYS_RESEARCH,
            user=f"RESEARCH REQUEST during active forge: {action} '{scenario['unknown']}'. "
                 f"Context: {scenario['context']}. "
                 f"Team needs an answer within 5 seconds.",
            assistant=f"[RESEARCH AGENT: searching...]\n"
                      f"[Query: {scenario['unknown']}]\n"
                      f"[Sources: physics reference, ISS microgravity data, Langues Weighting System]\n"
                      f"[Time: 3.2 seconds]\n\n"
                      f"RESULT: {scenario['finding']}\n\n"
                      f"[RESEARCH AGENT: returning to forge. Time spent: 3.2s of 5.0s budget.]",
            tier="journeyman" if scenario["tier"] in ["apprentice", "journeyman"] else scenario["tier"],
            tongue=t,
            tags=["active-research", action],
        ))

        # Master: research with conflicting sources
        _opposite(t)
        records.append(ForgeRecord(
            category="research", system=SYS_RESEARCH,
            user=f"Research agent found TWO conflicting answers about '{scenario['unknown']}': "
                 f"Source A says one approach, Source B says the opposite. "
                 f"Both seem credible. 20 seconds on the clock. What does the team do?",
            assistant=f"CONFLICT RESOLUTION under time pressure: "
                      f"Step 1: Check which source is closer to our specific situation "
                      f"(zero-G sphere forge, not general lab conditions). "
                      f"Step 2: If both apply, go with the SAFER option — the one with lower catastrophic risk. "
                      f"Step 3: {ARM_NAMES[t]} tests the chosen approach on one element first (sacrificial test). "
                      f"If it works: apply to all. If it fails: switch to Source B immediately. "
                      f"Step 4: After the forge round, research BOTH answers thoroughly for next time. "
                      f"The research agent logs the conflict for post-forge review. "
                      f"In time pressure, SAFETY > OPTIMALITY. A safe suboptimal bond beats a risky perfect one.",
            tier="master", tongue=t,
            tags=["conflicting-sources", "safety-first"],
        ))

    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    random.seed(SEED)

    generators = [
        ("grab", gen_grab_and_hold, 150),
        ("handoff", gen_cross_handoff, 150),
        ("assembly", gen_compound_assembly, 200),
        ("collision", gen_collision_avoidance, 150),
        ("drift", gen_zero_g_drift, 150),
        ("viewpoint", gen_multi_viewpoint, 150),
        ("rush", gen_time_pressure, 150),
        ("chemistry", gen_chemistry, 150),
        ("research", gen_web_research, 150),
    ]

    print("=" * 70)
    print("HexForge: 6-Arm Zero-G Assembly -- SFT Generator")
    print("=" * 70)
    print()

    all_records = []
    for name, gen_fn, count in generators:
        recs = gen_fn(count)
        sft_recs = [record_to_sft(r) for r in recs]
        all_records.extend(sft_recs)
        print(f"  {name:.<25s} {len(sft_recs):>5,d} records")

    random.shuffle(all_records)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    file_size = OUTPUT_PATH.stat().st_size

    from collections import Counter
    tongue_dist = Counter(r["dominant_tongue"] for r in all_records)
    tier_dist = Counter()
    for r in all_records:
        for tag in r["tags"]:
            if tag in TIERS:
                tier_dist[tag] += 1

    print(f"\n  Total: {len(all_records):,d} records ({file_size / 1024 / 1024:.1f} MB)")
    print(f"\n  Tongue distribution:")
    for t in TONGUES:
        ct = tongue_dist[t]
        pct = ct / len(all_records) * 100
        print(f"    {t} ({TONGUE_NAMES[t]:.<15s}) {ct:>5,d} ({pct:5.1f}%)")
    print(f"\n  Tier distribution:")
    for tier in TIERS:
        ct = tier_dist.get(tier, 0)
        pct = ct / len(all_records) * 100
        print(f"    {tier:.<15s} {ct:>5,d} ({pct:5.1f}%)")
    print(f"\n  Compounds referenced:")
    compound_ct = Counter()
    for r in all_records:
        for tag in r["tags"]:
            if tag.startswith("compound-"):
                compound_ct[tag.replace("compound-", "")] += 1
    for name, ct in compound_ct.most_common():
        print(f"    {name:.<30s} {ct:>3d}")


if __name__ == "__main__":
    main()
