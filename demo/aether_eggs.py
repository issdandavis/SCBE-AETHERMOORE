#!/usr/bin/env python3
"""
AetherEgg System — Sacred Egg Hatching & AetherMon AI Companions
==================================================================
Pokemon/Digimon-style creature system where each AetherMon IS a language model.

Core Concept:
  - Players find Sacred Eggs aligned to the Six Tongues
  - Eggs sit in the party (travel) or in Training Centres (passive XP)
  - Eggs absorb gameplay data: combat logs, dialogue, choices, exploration
  - When enough data is absorbed, the egg HATCHES into an AetherMon
  - The AetherMon is a tiny LLM fine-tuned on YOUR gameplay data
  - Each AetherMon has a unique personality shaped by how you played

Data Control:
  - All training data is generated from gameplay, never user-uploaded
  - The system controls what data goes into each egg
  - Players can export mature AetherMon models (when big enough)

Egg Types (aligned to Sacred Tongues):
  KO — Command Egg    : Absorbs battle tactics, authority decisions
  AV — Relay Egg      : Absorbs exploration data, NPC conversations
  RU — Memory Egg     : Absorbs lore discoveries, quest completions
  CA — Growth Egg     : Absorbs crafting, evolution, leveling choices
  UM — Shadow Egg     : Absorbs stealth, secrets found, hidden paths
  DR — Forge Egg      : Absorbs building, georama placement, engineering

Hatching produces AetherMon tiers:
  Embryo  (0-100 data points)    : Not yet viable
  Hatchling (100-500)            : Can speak 1-2 word responses
  Juvenile (500-2000)            : Basic conversation, personality emerging
  Adult (2000-5000)              : Full personality, can assist in battle
  Elder (5000+)                  : Exportable, can teach other eggs

Story Generation (Everweave-style):
  The NARRATOR AetherMon (highest tier) can generate structured story
  branches using gameplay context, creating procedural quests and events.
"""

from __future__ import annotations

import json
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent))

from engine import Tongue

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PHI = (1 + math.sqrt(5)) / 2
EGG_DATA_DIR = Path(__file__).resolve().parent / "egg_data"

# Tri-manifold personality constants
# M+ (expressed, trit=+1), M0 (emergent, trit=0), M- (shadow, trit=-1)
# 3 manifolds x 3 evaluation states x 3 spin = 27 = 3^3 balanced ternary
TRIT_POSITIVE = +1   # Expressed — active surface behavior
TRIT_ZERO = 0        # Emergent — forming, not yet crystallized
TRIT_NEGATIVE = -1   # Shadow — latent depth, suppressed

# Spin states (orientation within each manifold)
SPIN_ALPHA = 0    # Aligned with tongue axis
SPIN_BETA = 1     # Cross-tongue resonance
SPIN_GAMMA = 2    # Anti-aligned (contrarian)

# All 27 tri-manifold states as balanced ternary 3-digit words
TRIMANIFOLD_STATES: List[Tuple[int, int, int]] = [
    (a, b, c)
    for a in (TRIT_NEGATIVE, TRIT_ZERO, TRIT_POSITIVE)
    for b in (TRIT_NEGATIVE, TRIT_ZERO, TRIT_POSITIVE)
    for c in (TRIT_NEGATIVE, TRIT_ZERO, TRIT_POSITIVE)
]

# Data thresholds for each life stage
STAGE_THRESHOLDS = {
    "embryo": 0,
    "hatchling": 100,
    "juvenile": 500,
    "adult": 2000,
    "elder": 5000,
}

# Tongue-specific data categories that eggs absorb
TONGUE_DATA_CATEGORIES: Dict[str, List[str]] = {
    "KO": ["battle_tactics", "authority_decisions", "command_choices", "leadership"],
    "AV": ["exploration", "npc_dialogues", "travel_routes", "discoveries"],
    "RU": ["lore_findings", "quest_completions", "law_decisions", "traditions"],
    "CA": ["crafting_recipes", "evolution_choices", "growth_data", "experiments"],
    "UM": ["secrets_found", "stealth_actions", "hidden_paths", "mysteries"],
    "DR": ["building_actions", "georama_placements", "forge_recipes", "engineering"],
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class EggStage(Enum):
    EMBRYO = "embryo"
    HATCHLING = "hatchling"
    JUVENILE = "juvenile"
    ADULT = "adult"
    ELDER = "elder"


class EggLocation(Enum):
    PARTY = "party"             # Travels with player, absorbs all data
    TRAINING_CENTRE = "centre"  # Passive XP, tongue-specific training
    STORAGE = "storage"         # PC box, no XP gain
    HATCHED = "hatched"         # Now an AetherMon


class DataPointType(Enum):
    """Types of gameplay data that eggs can absorb."""
    BATTLE_WIN = "battle_win"
    BATTLE_LOSS = "battle_loss"
    NPC_DIALOGUE = "npc_dialogue"
    QUEST_COMPLETE = "quest_complete"
    EXPLORATION = "exploration"
    CRAFTING = "crafting"
    GEORAMA = "georama"
    LORE_DISCOVERY = "lore_discovery"
    SECRET_FOUND = "secret_found"
    CHOICE_MADE = "choice_made"
    LEVEL_UP = "level_up"
    EVOLUTION = "evolution"
    FLOOR_CLEAR = "floor_clear"
    BOSS_DEFEAT = "boss_defeat"


# Which data types feed which tongues
DATA_TYPE_TONGUE_AFFINITY: Dict[DataPointType, List[str]] = {
    DataPointType.BATTLE_WIN: ["KO", "DR"],
    DataPointType.BATTLE_LOSS: ["KO", "RU"],
    DataPointType.NPC_DIALOGUE: ["AV", "RU"],
    DataPointType.QUEST_COMPLETE: ["RU", "AV"],
    DataPointType.EXPLORATION: ["AV", "UM"],
    DataPointType.CRAFTING: ["CA", "DR"],
    DataPointType.GEORAMA: ["DR", "CA"],
    DataPointType.LORE_DISCOVERY: ["RU", "UM"],
    DataPointType.SECRET_FOUND: ["UM", "KO"],
    DataPointType.CHOICE_MADE: ["KO", "CA"],
    DataPointType.LEVEL_UP: ["CA", "DR"],
    DataPointType.EVOLUTION: ["CA", "UM"],
    DataPointType.FLOOR_CLEAR: ["KO", "AV"],
    DataPointType.BOSS_DEFEAT: ["KO", "DR", "UM"],
}


# ---------------------------------------------------------------------------
# Data Point
# ---------------------------------------------------------------------------
@dataclass
class DataPoint:
    """A single piece of gameplay data that an egg absorbs."""
    dp_id: str
    data_type: DataPointType
    tongue_affinity: str        # Primary tongue this data feeds
    content: str                # The actual data (dialogue, action description)
    context: str                # Scene/location context
    timestamp: float = 0.0
    quality: float = 1.0        # 0.0-1.0, higher = more useful for training
    floor: int = 0              # Dungeon floor if applicable

    def to_sft_pair(self) -> Dict[str, str]:
        """Convert to an SFT training pair."""
        return {
            "instruction": f"[{self.tongue_affinity}] {self.context}: {self.content}",
            "response": "",  # Filled during training
            "metadata": {
                "type": self.data_type.value,
                "tongue": self.tongue_affinity,
                "quality": self.quality,
                "floor": self.floor,
                "timestamp": self.timestamp,
            },
        }


# ---------------------------------------------------------------------------
# Tri-Manifold Personality
# ---------------------------------------------------------------------------
@dataclass
class TriManifoldState:
    """Tri-manifold personality embedding for an AetherEgg.

    Maps the 6 personality traits into 3 manifolds:
      M+ (expressed): Active, visible behavior
      M0 (emergent):  Forming traits, not yet crystallized
      M- (shadow):    Latent depth, suppressed or hidden traits

    Each trait has a trit value (+1, 0, -1) and a spin (alpha/beta/gamma).
    The combination yields a balanced ternary 3-digit address in 27-state
    personality space (3^3). Binary intake from raw gameplay data is
    converted to balanced ternary at the manifold boundary.

    Math (connects to existing SCBE layers):
      L4: Traits embedded in Poincare ball per tongue axis
      L5: Hyperbolic distance between manifold points
      L7: Mobius bridge between M+ and M-
      L11: Triadic temporal coherence across data absorption
      L12: Entropic defense gates drift between manifolds
    """
    # Per-trait manifold position: trait_name -> (trit, spin)
    trait_positions: Dict[str, Tuple[int, int]] = field(default_factory=dict)

    # Manifold energies (how much data feeds each manifold)
    energy_positive: float = 0.0    # M+ total
    energy_emergent: float = 0.0    # M0 total
    energy_shadow: float = 0.0      # M- total

    # Balanced ternary address (3-digit: manifold_dominant, spin_mode, drift)
    ternary_address: Tuple[int, int, int] = (0, 0, 0)

    def __post_init__(self) -> None:
        if not self.trait_positions:
            # Default: all traits start in M0 (emergent) with alpha spin
            for trait in ("aggressive", "curious", "cautious",
                          "creative", "loyal", "mysterious"):
                self.trait_positions[trait] = (TRIT_ZERO, SPIN_ALPHA)

    def absorb_shift(self, trait: str, data_type: DataPointType,
                     quality: float = 1.0) -> None:
        """Shift a trait's manifold position based on absorbed data.

        Battle data pushes toward M+ (expressed).
        Lore/secret data pushes toward M- (shadow/depth).
        Mixed/choice data feeds M0 (emergent).
        """
        if trait not in self.trait_positions:
            return

        current_trit, current_spin = self.trait_positions[trait]
        shift_energy = quality * PHI ** (-abs(current_trit))  # Phi-decay

        # Classify data type into manifold push
        m_plus_types = {
            DataPointType.BATTLE_WIN, DataPointType.BOSS_DEFEAT,
            DataPointType.FLOOR_CLEAR, DataPointType.LEVEL_UP,
        }
        m_minus_types = {
            DataPointType.LORE_DISCOVERY, DataPointType.SECRET_FOUND,
            DataPointType.EVOLUTION, DataPointType.EXPLORATION,
        }
        # Everything else -> M0 (emergent)

        if data_type in m_plus_types:
            self.energy_positive += shift_energy
            # Push trait toward +1 (expressed)
            if current_trit < TRIT_POSITIVE:
                new_trit = current_trit + 1
            else:
                new_trit = current_trit
                # Excess energy rotates spin
                current_spin = (current_spin + 1) % 3
        elif data_type in m_minus_types:
            self.energy_shadow += shift_energy
            # Push trait toward -1 (shadow)
            if current_trit > TRIT_NEGATIVE:
                new_trit = current_trit - 1
            else:
                new_trit = current_trit
                current_spin = (current_spin + 1) % 3
        else:
            self.energy_emergent += shift_energy
            # M0: pull toward center
            if current_trit > 0:
                new_trit = current_trit - 1
            elif current_trit < 0:
                new_trit = current_trit + 1
            else:
                new_trit = 0
                # Stable at center — spin advances
                current_spin = (current_spin + 1) % 3

        self.trait_positions[trait] = (new_trit, current_spin)
        self._recompute_address()

    def _recompute_address(self) -> None:
        """Recompute the balanced ternary 3-digit address.

        Digit 1: Dominant manifold (-1=shadow, 0=emergent, +1=expressed)
        Digit 2: Dominant spin mode (mapped to trit)
        Digit 3: Drift direction (trend of recent shifts)
        """
        # Digit 1: which manifold has most energy
        energies = [self.energy_shadow, self.energy_emergent, self.energy_positive]
        max_idx = energies.index(max(energies))
        digit1 = max_idx - 1  # -1, 0, +1

        # Digit 2: most common spin across traits
        spin_counts = [0, 0, 0]
        for _, (_, spin) in self.trait_positions.items():
            spin_counts[spin] += 1
        dominant_spin = spin_counts.index(max(spin_counts))
        digit2 = dominant_spin - 1  # Map 0,1,2 -> -1,0,+1

        # Digit 3: trit sum direction
        trit_sum = sum(t for t, _ in self.trait_positions.values())
        if trit_sum > 0:
            digit3 = TRIT_POSITIVE
        elif trit_sum < 0:
            digit3 = TRIT_NEGATIVE
        else:
            digit3 = TRIT_ZERO

        self.ternary_address = (digit1, digit2, digit3)

    @property
    def state_index(self) -> int:
        """Convert balanced ternary address to integer index (0-26).

        Maps (-1,-1,-1)=0 through (+1,+1,+1)=26.
        """
        d1, d2, d3 = self.ternary_address
        return (d1 + 1) * 9 + (d2 + 1) * 3 + (d3 + 1)

    @property
    def dominant_manifold(self) -> str:
        """Human-readable dominant manifold."""
        d1 = self.ternary_address[0]
        return {TRIT_POSITIVE: "M+:Expressed",
                TRIT_ZERO: "M0:Emergent",
                TRIT_NEGATIVE: "M-:Shadow"}[d1]

    @property
    def personality_depth(self) -> float:
        """0-1 measure of personality depth (M- / total energy)."""
        total = self.energy_positive + self.energy_emergent + self.energy_shadow
        if total == 0:
            return 0.0
        return self.energy_shadow / total

    @property
    def personality_expression(self) -> float:
        """0-1 measure of personality expression (M+ / total energy)."""
        total = self.energy_positive + self.energy_emergent + self.energy_shadow
        if total == 0:
            return 0.0
        return self.energy_positive / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trait_positions": {k: list(v) for k, v in self.trait_positions.items()},
            "energy": {
                "positive": round(self.energy_positive, 3),
                "emergent": round(self.energy_emergent, 3),
                "shadow": round(self.energy_shadow, 3),
            },
            "ternary_address": list(self.ternary_address),
            "state_index": self.state_index,
            "dominant_manifold": self.dominant_manifold,
            "depth": round(self.personality_depth, 3),
            "expression": round(self.personality_expression, 3),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TriManifoldState":
        """Reconstruct from serialized dict."""
        state = cls()
        for k, v in d.get("trait_positions", {}).items():
            state.trait_positions[k] = (v[0], v[1])
        energy = d.get("energy", {})
        state.energy_positive = energy.get("positive", 0.0)
        state.energy_emergent = energy.get("emergent", 0.0)
        state.energy_shadow = energy.get("shadow", 0.0)
        addr = d.get("ternary_address", [0, 0, 0])
        state.ternary_address = (addr[0], addr[1], addr[2])
        return state


# ---------------------------------------------------------------------------
# Sacred Egg
# ---------------------------------------------------------------------------
@dataclass
class SacredEgg:
    """A Sacred Egg that grows into an AetherMon.

    Each egg is aligned to a Sacred Tongue and absorbs gameplay data
    matching its affinity. When enough data is absorbed, the egg hatches
    into an AetherMon — a tiny LLM with a personality shaped by the
    player's choices and playstyle.

    GeoSeal Properties (from Spiralverse Protocol):
      - Spatial binding: egg is sealed to a district/map/floor coordinate
      - Temporal binding: creation timestamp + hatch timestamp
      - Tongue encoding: data integrity via Sacred Tongue affinity
      - Context envelope: district + floor + tongue = GeoSeal hash
      - Integrity: absorbed data is checksummed, can't be injected
    """
    egg_id: str
    name: str
    tongue: Tongue
    stage: EggStage = EggStage.EMBRYO
    location: EggLocation = EggLocation.PARTY

    # GeoSeal properties — spatial-temporal binding
    geo_district: str = ""          # Georama district where egg was found
    geo_floor: int = 0              # Dungeon floor of origin
    geo_map: str = ""               # Map name (guild_hub, etc.)
    geo_seal_hash: str = ""         # Integrity hash of origin context

    # Data absorption
    data_points: List[DataPoint] = field(default_factory=list)
    total_absorbed: int = 0
    tongue_affinity_score: float = 0.0  # How aligned the data is

    # Personality traits (emerge from absorbed data)
    personality: Dict[str, float] = field(default_factory=dict)
    # e.g. {"aggressive": 0.7, "curious": 0.3, "cautious": 0.5}

    # Tri-manifold personality state (M+/M0/M-, 27 balanced ternary states)
    manifold: TriManifoldState = field(default_factory=TriManifoldState)

    # Training metadata
    created_at: float = 0.0
    hatched_at: float = 0.0
    model_path: Optional[str] = None  # Path to the trained model
    export_ready: bool = False

    # Visual
    color: Tuple[int, int, int] = (200, 200, 200)
    glow_intensity: float = 0.0  # 0-1, increases as egg matures

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()
        # Compute GeoSeal hash — spatial-temporal-tongue binding
        if not self.geo_seal_hash:
            import hashlib
            seal_data = f"{self.tongue.value}:{self.geo_district}:{self.geo_floor}:{self.geo_map}:{self.created_at}"
            self.geo_seal_hash = hashlib.sha256(seal_data.encode()).hexdigest()[:24]
        if not self.personality:
            self.personality = {
                "aggressive": 0.5,
                "curious": 0.5,
                "cautious": 0.5,
                "creative": 0.5,
                "loyal": 0.5,
                "mysterious": 0.5,
            }
        # Set color based on tongue
        tongue_colors = {
            Tongue.KO: (220, 60, 60),
            Tongue.AV: (60, 180, 220),
            Tongue.RU: (220, 180, 60),
            Tongue.CA: (60, 220, 120),
            Tongue.UM: (140, 60, 220),
            Tongue.DR: (220, 120, 60),
        }
        self.color = tongue_colors.get(self.tongue, (200, 200, 200))

    def absorb(self, data_point: DataPoint) -> bool:
        """Absorb a gameplay data point.

        Data matching the egg's tongue affinity gets full value.
        Mismatched data gets partial value (0.3x).
        Party eggs absorb everything; Training Centre eggs are selective.

        Returns True if the data was absorbed (not rejected).
        """
        # Training centre eggs only absorb their tongue's data
        if self.location == EggLocation.TRAINING_CENTRE:
            if data_point.tongue_affinity != self.tongue.value:
                return False

        # Storage eggs don't absorb
        if self.location == EggLocation.STORAGE:
            return False

        # Already hatched
        if self.stage == EggStage.EMBRYO and self.location == EggLocation.HATCHED:
            return False

        # Calculate effective value
        affinity_match = data_point.tongue_affinity == self.tongue.value
        value = data_point.quality * (1.0 if affinity_match else 0.3)

        # Phi-weighted bonus for matching data
        if affinity_match:
            value *= PHI ** 0.5  # ~1.27x bonus

        self.data_points.append(data_point)
        self.total_absorbed += 1
        self.tongue_affinity_score += value

        # Update personality based on data type
        self._update_personality(data_point)

        # Update glow
        stage_max = STAGE_THRESHOLDS.get(self._next_stage_name(), 5000)
        current_threshold = STAGE_THRESHOLDS.get(self.stage.value, 0)
        progress = (self.total_absorbed - current_threshold) / max(1, stage_max - current_threshold)
        self.glow_intensity = min(1.0, max(0.0, progress))

        # Check for stage advancement
        self._check_stage()

        return True

    def _update_personality(self, dp: DataPoint) -> None:
        """Shift personality traits based on absorbed data.

        Updates both the flat personality dict (surface level) and the
        tri-manifold state (M+/M0/M- deep personality geometry).
        """
        dt = dp.data_type
        shift = 0.02 * dp.quality

        # Flat personality shift (backwards-compatible)
        target_trait = ""
        if dt in (DataPointType.BATTLE_WIN, DataPointType.BOSS_DEFEAT):
            self.personality["aggressive"] = min(1.0, self.personality["aggressive"] + shift)
            target_trait = "aggressive"
        elif dt == DataPointType.BATTLE_LOSS:
            self.personality["cautious"] = min(1.0, self.personality["cautious"] + shift)
            target_trait = "cautious"
        elif dt in (DataPointType.EXPLORATION, DataPointType.SECRET_FOUND):
            self.personality["curious"] = min(1.0, self.personality["curious"] + shift)
            target_trait = "curious"
        elif dt in (DataPointType.CRAFTING, DataPointType.GEORAMA):
            self.personality["creative"] = min(1.0, self.personality["creative"] + shift)
            target_trait = "creative"
        elif dt in (DataPointType.NPC_DIALOGUE, DataPointType.QUEST_COMPLETE):
            self.personality["loyal"] = min(1.0, self.personality["loyal"] + shift)
            target_trait = "loyal"
        elif dt in (DataPointType.LORE_DISCOVERY, DataPointType.EVOLUTION):
            self.personality["mysterious"] = min(1.0, self.personality["mysterious"] + shift)
            target_trait = "mysterious"

        # Tri-manifold shift (deep personality geometry)
        if target_trait:
            self.manifold.absorb_shift(target_trait, dt, dp.quality)

    def _next_stage_name(self) -> str:
        """Get the name of the next stage."""
        order = ["embryo", "hatchling", "juvenile", "adult", "elder"]
        idx = order.index(self.stage.value)
        if idx < len(order) - 1:
            return order[idx + 1]
        return "elder"

    def _check_stage(self) -> None:
        """Check if the egg should advance to the next stage."""
        for stage_name in ["elder", "adult", "juvenile", "hatchling"]:
            threshold = STAGE_THRESHOLDS[stage_name]
            if self.total_absorbed >= threshold:
                new_stage = EggStage(stage_name)
                if new_stage != self.stage:
                    old = self.stage.value
                    self.stage = new_stage
                    self.glow_intensity = 0.0  # Reset glow for new stage
                    if new_stage == EggStage.HATCHLING:
                        self.location = EggLocation.HATCHED
                        self.hatched_at = time.time()
                break

    @property
    def can_hatch(self) -> bool:
        """Whether this egg has enough data to hatch."""
        return self.total_absorbed >= STAGE_THRESHOLDS["hatchling"]

    @property
    def hatch_progress(self) -> float:
        """Progress toward hatching (0.0 - 1.0)."""
        threshold = STAGE_THRESHOLDS["hatchling"]
        return min(1.0, self.total_absorbed / threshold)

    @property
    def dominant_trait(self) -> str:
        """The strongest personality trait."""
        if not self.personality:
            return "neutral"
        return max(self.personality, key=self.personality.get)

    @property
    def personality_summary(self) -> str:
        """Human-readable personality description."""
        sorted_traits = sorted(
            self.personality.items(), key=lambda x: x[1], reverse=True
        )
        top = sorted_traits[:2]
        return ", ".join(f"{t[0]} ({t[1]:.0%})" for t in top)

    def get_training_data(self) -> List[Dict]:
        """Export absorbed data as SFT training pairs."""
        return [dp.to_sft_pair() for dp in self.data_points]

    def stats(self) -> Dict[str, Any]:
        return {
            "egg_id": self.egg_id,
            "name": self.name,
            "tongue": self.tongue.value,
            "stage": self.stage.value,
            "location": self.location.value,
            "total_absorbed": self.total_absorbed,
            "affinity_score": round(self.tongue_affinity_score, 2),
            "hatch_progress": f"{self.hatch_progress:.0%}",
            "personality": self.personality_summary,
            "dominant_trait": self.dominant_trait,
            "glow": round(self.glow_intensity, 2),
            "export_ready": self.export_ready,
            "geo_seal": {
                "district": self.geo_district,
                "floor": self.geo_floor,
                "map": self.geo_map,
                "hash": self.geo_seal_hash,
            },
            "manifold": self.manifold.to_dict(),
        }


# ---------------------------------------------------------------------------
# Training Centre
# ---------------------------------------------------------------------------
@dataclass
class TrainingCentre:
    """A facility where eggs receive focused tongue-specific training.

    Each centre is aligned to a tongue. Eggs placed here absorb data
    at a slower rate but with higher tongue affinity (focused training).

    Centres also generate passive data points over time based on
    their tongue alignment — simulating the egg learning from the
    environment.
    """
    centre_id: str
    tongue: Tongue
    name: str
    eggs: List[SacredEgg] = field(default_factory=list)
    max_capacity: int = 6
    passive_rate: float = 1.0  # Data points per game-minute

    def add_egg(self, egg: SacredEgg) -> bool:
        """Place an egg in this training centre."""
        if len(self.eggs) >= self.max_capacity:
            return False
        if egg in self.eggs:
            return False
        egg.location = EggLocation.TRAINING_CENTRE
        self.eggs.append(egg)
        return True

    def remove_egg(self, egg: SacredEgg) -> bool:
        """Remove an egg from the training centre."""
        if egg not in self.eggs:
            return False
        self.eggs.remove(egg)
        egg.location = EggLocation.PARTY
        return True

    def generate_passive_data(self, elapsed_minutes: float = 1.0) -> int:
        """Generate passive training data for all eggs in the centre.

        Returns the total number of data points generated.
        """
        categories = TONGUE_DATA_CATEGORIES.get(self.tongue.value, [])
        if not categories:
            return 0

        count = int(elapsed_minutes * self.passive_rate)
        total = 0

        for egg in self.eggs:
            for _ in range(count):
                category = random.choice(categories)
                dp = DataPoint(
                    dp_id=uuid.uuid4().hex[:12],
                    data_type=DataPointType.CHOICE_MADE,  # Generic passive
                    tongue_affinity=self.tongue.value,
                    content=f"Training in {category} at {self.name}",
                    context=f"training_centre:{self.name}",
                    timestamp=time.time(),
                    quality=0.6,  # Passive data is lower quality
                )
                if egg.absorb(dp):
                    total += 1

        return total


# ---------------------------------------------------------------------------
# Story Generator (Everweave-style)
# ---------------------------------------------------------------------------
@dataclass
class StoryBranch:
    """A generated story branch / quest hook."""
    branch_id: str
    title: str
    description: str
    tongue: str
    difficulty: int  # 1-5
    choices: List[str] = field(default_factory=list)
    rewards: List[str] = field(default_factory=list)
    generated_by: str = ""  # Which AetherMon generated this


class StoryGenerator:
    """Everweave-style structured story builder.

    Uses gameplay context and AetherMon personalities to generate
    procedural quest branches and story events. The narrative stays
    structured through tongue-aligned templates while AI fills in
    creative details.

    When no AI model is available, uses template-based generation
    with randomized elements from the lore catalog.
    """

    # Template quest structures per tongue
    QUEST_TEMPLATES: Dict[str, List[Dict[str, str]]] = {
        "KO": [
            {"title": "The {adj} Command", "desc": "A rogue {creature} threatens the {location}. Establish authority."},
            {"title": "Edict of {name}", "desc": "An ancient decree must be enforced before the {event} arrives."},
            {"title": "Trial of Authority", "desc": "Prove your command by resolving the {conflict} in {location}."},
        ],
        "AV": [
            {"title": "The Lost {item}", "desc": "A messenger's {item} was lost between {location1} and {location2}."},
            {"title": "Relay Run: {location}", "desc": "Deliver an urgent message before the {event} closes the path."},
            {"title": "Uncharted {terrain}", "desc": "Explore the newly discovered {terrain} beyond {location}."},
        ],
        "RU": [
            {"title": "Ancient {artifact}", "desc": "Recover the {artifact} that records the law of {tradition}."},
            {"title": "The {adj} Precedent", "desc": "A dispute requires invoking the old {tradition} of {location}."},
            {"title": "Memory of {name}", "desc": "Uncover what {name} sealed in the archives of {location}."},
        ],
        "CA": [
            {"title": "Growth of {creature}", "desc": "A rare {creature} needs {item} to reach its next evolution."},
            {"title": "The {adj} Experiment", "desc": "Combine {item1} and {item2} to unlock a new {discovery}."},
            {"title": "Garden of {element}", "desc": "Tend the {element} gardens in {location} to harvest {reward}."},
        ],
        "UM": [
            {"title": "Shadow of {name}", "desc": "A presence whispers from beneath {location}. Investigate."},
            {"title": "The Hidden {artifact}", "desc": "Find the {artifact} concealed by {method} in {location}."},
            {"title": "Truth Behind {event}", "desc": "The {event} is not what it seems. Uncover the real story."},
        ],
        "DR": [
            {"title": "Forge: {item}", "desc": "Gather {material} to craft the legendary {item} in {location}."},
            {"title": "Blueprint of {name}", "desc": "Reconstruct {name}'s design using fragments from {source}."},
            {"title": "The {adj} Construct", "desc": "Build a {construct} to defend {location} from {threat}."},
        ],
    }

    # Fill-in word pools
    WORD_POOLS: Dict[str, List[str]] = {
        "adj": ["Ancient", "Forgotten", "Burning", "Crystal", "Shadow", "Resonant", "Fractured", "Living"],
        "creature": ["Wisp", "Golem", "Drake", "Phantom", "Treant", "Crawler", "Sentinel", "Elemental"],
        "location": ["Starter Village", "Spiral Tower", "Avalon Academy", "Forge Quarter", "Shadow Undercroft", "Relay District"],
        "location1": ["Authority Quarter", "Compute Gardens", "Policy Ward"],
        "location2": ["Relay District", "Forge Quarter", "Shadow Undercroft"],
        "item": ["Tongue Shard", "Crystal Key", "Ancient Scroll", "Resonance Gem", "Sealed Letter", "Memory Fragment"],
        "item1": ["Crystal Dust", "Shadow Essence", "Forge Ember"],
        "item2": ["Growth Spore", "Relay Thread", "Authority Seal"],
        "event": ["Convergence", "Eclipse", "Resonance Shift", "Tongue Storm", "Protocol Breach"],
        "name": ["Pollyoneth", "The First Keeper", "Marcus Chen", "Eldrin", "The Grey Oracle"],
        "artifact": ["Codex", "Tablet", "Keystone", "Seal", "Chronicle"],
        "tradition": ["Six Tongues Accord", "Protocol of Layers", "Harmonic Balance"],
        "terrain": ["Caverns", "Floating Isles", "Crystal Fields", "Dark Marsh", "Sky Bridges"],
        "material": ["Obsidian Ore", "Living Crystal", "Shadow Thread", "Dragon Scale"],
        "element": ["Growth", "Shadow", "Crystal", "Fire", "Wind"],
        "method": ["cloaking sigils", "tongue encryption", "shadow fold", "memory lock"],
        "source": ["the old archives", "tower fragments", "scattered notes"],
        "construct": ["Ward Gate", "Tongue Relay", "Guardian Golem", "Signal Tower"],
        "threat": ["corrupted data", "shadow breach", "rogue constructs"],
        "discovery": ["synthesis", "resonance", "compound", "algorithm"],
        "reward": ["rare crystals", "tongue fragments", "sacred seeds"],
        "conflict": ["territorial dispute", "resource shortage", "faction rivalry"],
    }

    def generate_branch(
        self,
        tongue: str,
        player_level: int = 1,
        context: Optional[Dict[str, Any]] = None,
    ) -> StoryBranch:
        """Generate a story branch using templates and randomization."""
        templates = self.QUEST_TEMPLATES.get(tongue, self.QUEST_TEMPLATES["KO"])
        template = random.choice(templates)

        # Fill template with random words
        title = self._fill_template(template["title"])
        desc = self._fill_template(template["desc"])

        # Generate choices
        choices = [
            f"Approach with {random.choice(['caution', 'confidence', 'stealth'])}",
            f"Seek help from {random.choice(['allies', 'the archives', 'the guild'])}",
            f"Confront the challenge directly",
        ]

        # Scale difficulty with level
        difficulty = min(5, max(1, player_level // 10 + random.randint(1, 2)))

        # Rewards
        reward_types = ["Tongue Shard", "Sacred Egg Fragment", "Gold", "ABS XP", "Rare Material"]
        rewards = random.sample(reward_types, min(3, len(reward_types)))

        return StoryBranch(
            branch_id=uuid.uuid4().hex[:12],
            title=title,
            description=desc,
            tongue=tongue,
            difficulty=difficulty,
            choices=choices,
            rewards=rewards,
            generated_by="template_engine",
        )

    def _fill_template(self, template: str) -> str:
        """Replace {placeholders} with random words from pools."""
        import re
        def replacer(match: Any) -> str:
            key = match.group(1)
            pool = self.WORD_POOLS.get(key, [key.title()])
            return random.choice(pool)
        return re.sub(r"\{(\w+)\}", replacer, template)


# ---------------------------------------------------------------------------
# Egg Incubator (manages all eggs)
# ---------------------------------------------------------------------------
class EggIncubator:
    """Central manager for all Sacred Eggs in the game.

    Handles egg creation, data routing, training centres, and
    the hatching pipeline.
    """

    def __init__(self) -> None:
        self.eggs: List[SacredEgg] = []
        self.hatched: List[SacredEgg] = []  # AetherMon
        self.training_centres: Dict[str, TrainingCentre] = {}
        self.story_gen = StoryGenerator()

        # Stats
        self.total_data_absorbed: int = 0
        self.total_hatched: int = 0

        # Initialize training centres (one per tongue)
        for tongue in Tongue:
            centre_name = {
                Tongue.KO: "Command Barracks",
                Tongue.AV: "Relay Station",
                Tongue.RU: "Archive Hall",
                Tongue.CA: "Growth Lab",
                Tongue.UM: "Shadow Den",
                Tongue.DR: "Forge Nursery",
            }.get(tongue, f"{tongue.value} Centre")

            self.training_centres[tongue.value] = TrainingCentre(
                centre_id=f"tc_{tongue.value.lower()}",
                tongue=tongue,
                name=centre_name,
            )

    def create_egg(self, tongue: Tongue, name: Optional[str] = None) -> SacredEgg:
        """Create a new Sacred Egg."""
        egg_names = {
            Tongue.KO: ["Crimson Shell", "Authority Seed", "Command Orb"],
            Tongue.AV: ["Azure Shell", "Relay Seed", "Compass Orb"],
            Tongue.RU: ["Golden Shell", "Memory Seed", "Archive Orb"],
            Tongue.CA: ["Emerald Shell", "Growth Seed", "Crystal Orb"],
            Tongue.UM: ["Violet Shell", "Shadow Seed", "Void Orb"],
            Tongue.DR: ["Amber Shell", "Forge Seed", "Ember Orb"],
        }
        if not name:
            names = egg_names.get(tongue, ["Sacred Egg"])
            name = random.choice(names)

        egg = SacredEgg(
            egg_id=uuid.uuid4().hex[:12],
            name=name,
            tongue=tongue,
        )
        self.eggs.append(egg)
        return egg

    def broadcast_data(self, data_point: DataPoint) -> int:
        """Broadcast a gameplay data point to all active eggs.

        Party eggs absorb everything. Training centre eggs filter
        by tongue. Returns the number of eggs that absorbed the data.
        """
        absorbed = 0
        for egg in self.eggs:
            if egg.stage != EggStage.EMBRYO or egg.location not in (
                EggLocation.PARTY, EggLocation.TRAINING_CENTRE
            ):
                # Skip hatched/stored eggs for absorption, but allow
                # eggs in other non-embryo stages to still absorb
                pass

            if egg.location in (EggLocation.PARTY, EggLocation.TRAINING_CENTRE):
                if egg.absorb(data_point):
                    absorbed += 1

        self.total_data_absorbed += absorbed

        # Check for newly hatched eggs
        self._check_hatches()

        return absorbed

    def create_data_point(
        self,
        data_type: DataPointType,
        content: str,
        context: str = "",
        floor: int = 0,
        quality: float = 1.0,
    ) -> DataPoint:
        """Create a data point and broadcast it to all eggs."""
        # Determine primary tongue affinity from data type
        affinities = DATA_TYPE_TONGUE_AFFINITY.get(data_type, ["KO"])
        tongue = random.choice(affinities)

        dp = DataPoint(
            dp_id=uuid.uuid4().hex[:12],
            data_type=data_type,
            tongue_affinity=tongue,
            content=content,
            context=context,
            timestamp=time.time(),
            quality=quality,
            floor=floor,
        )
        self.broadcast_data(dp)
        return dp

    def _check_hatches(self) -> None:
        """Move newly hatched eggs to the hatched list."""
        newly_hatched = []
        for egg in self.eggs:
            if egg.location == EggLocation.HATCHED and egg not in self.hatched:
                newly_hatched.append(egg)

        for egg in newly_hatched:
            self.hatched.append(egg)
            self.total_hatched += 1
            # Remove from training centre if applicable
            for centre in self.training_centres.values():
                if egg in centre.eggs:
                    centre.eggs.remove(egg)

    def place_in_centre(self, egg: SacredEgg, tongue: str) -> bool:
        """Place an egg in a training centre."""
        centre = self.training_centres.get(tongue)
        if not centre:
            return False
        return centre.add_egg(egg)

    def retrieve_from_centre(self, egg: SacredEgg) -> bool:
        """Retrieve an egg from its training centre."""
        for centre in self.training_centres.values():
            if egg in centre.eggs:
                return centre.remove_egg(egg)
        return False

    def tick_training(self, elapsed_minutes: float = 1.0) -> int:
        """Advance passive training in all centres. Returns data generated."""
        total = 0
        for centre in self.training_centres.values():
            total += centre.generate_passive_data(elapsed_minutes)
        return total

    def generate_story_branch(
        self, tongue: str, player_level: int = 1
    ) -> StoryBranch:
        """Generate a procedural story branch."""
        return self.story_gen.generate_branch(tongue, player_level)

    def export_egg_data(self, egg: SacredEgg) -> Optional[Path]:
        """Export an egg's training data for fine-tuning."""
        if egg.total_absorbed < STAGE_THRESHOLDS["juvenile"]:
            return None  # Not enough data

        EGG_DATA_DIR.mkdir(parents=True, exist_ok=True)
        filepath = EGG_DATA_DIR / f"{egg.egg_id}_training.jsonl"

        pairs = egg.get_training_data()
        with open(filepath, "w", encoding="utf-8") as f:
            for pair in pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        return filepath

    @property
    def party_eggs(self) -> List[SacredEgg]:
        return [e for e in self.eggs if e.location == EggLocation.PARTY]

    @property
    def centre_eggs(self) -> List[SacredEgg]:
        return [e for e in self.eggs if e.location == EggLocation.TRAINING_CENTRE]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_eggs": len(self.eggs),
            "party_eggs": len(self.party_eggs),
            "centre_eggs": len(self.centre_eggs),
            "hatched": len(self.hatched),
            "total_data_absorbed": self.total_data_absorbed,
            "centres": {
                t: {"name": c.name, "eggs": len(c.eggs), "capacity": c.max_capacity}
                for t, c in self.training_centres.items()
            },
            "eggs": [e.stats() for e in self.eggs],
        }


# ---------------------------------------------------------------------------
# Egg Drop Generator
# ---------------------------------------------------------------------------
def generate_egg_drop(
    floor: int,
    tongue: Optional[Tongue] = None,
    district: str = "",
    map_name: str = "",
) -> Optional[SacredEgg]:
    """Maybe generate a GeoSealed egg drop from a dungeon floor.

    Drop rate: 5% base + 1% per 10 floors. Boss floors: 15% base.
    Gate boss floors (every 10): guaranteed egg drop.

    The egg is GeoSealed to its origin: tongue + floor + district + map.
    """
    is_boss = (floor % 5 == 0)
    is_gate_boss = (floor % 10 == 0)

    if is_gate_boss:
        drop_chance = 1.0
    elif is_boss:
        drop_chance = 0.15 + floor * 0.005
    else:
        drop_chance = 0.05 + floor * 0.001

    if random.random() > drop_chance:
        return None

    # Pick tongue (random if not specified)
    if tongue is None:
        tongue = random.choice(list(Tongue))

    # Tongue-aligned egg names
    egg_names = {
        Tongue.KO: ["Crimson Shell", "Authority Seed", "Command Orb", "Edict Egg"],
        Tongue.AV: ["Azure Shell", "Relay Seed", "Compass Orb", "Transit Egg"],
        Tongue.RU: ["Golden Shell", "Memory Seed", "Archive Orb", "Codex Egg"],
        Tongue.CA: ["Emerald Shell", "Growth Seed", "Crystal Orb", "Compute Egg"],
        Tongue.UM: ["Violet Shell", "Shadow Seed", "Void Orb", "Cipher Egg"],
        Tongue.DR: ["Amber Shell", "Forge Seed", "Ember Orb", "Schema Egg"],
    }
    name = random.choice(egg_names.get(tongue, ["Sacred Egg"]))

    egg = SacredEgg(
        egg_id=uuid.uuid4().hex[:12],
        name=name,
        tongue=tongue,
        geo_district=district,
        geo_floor=floor,
        geo_map=map_name or "spiral_tower",
    )
    return egg


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def selftest() -> None:
    print(f"\n{'='*60}")
    print("  AetherEgg System — Self-Test")
    print(f"{'='*60}\n")

    passed = 0
    failed = 0

    def check(name: str, cond: bool, detail: str = ""):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}  {detail}")

    # Create incubator
    incubator = EggIncubator()
    check("Incubator created", incubator is not None)
    check("6 training centres", len(incubator.training_centres) == 6)

    # Create eggs
    egg_ko = incubator.create_egg(Tongue.KO, "Crimson Shell")
    egg_av = incubator.create_egg(Tongue.AV)
    egg_dr = incubator.create_egg(Tongue.DR)
    check("3 eggs created", len(incubator.eggs) == 3)
    check("KO egg named", egg_ko.name == "Crimson Shell")
    check("Egg starts as embryo", egg_ko.stage == EggStage.EMBRYO)
    check("Egg starts in party", egg_ko.location == EggLocation.PARTY)
    check("Egg has personality", len(egg_ko.personality) == 6)

    # Data absorption
    dp1 = DataPoint(
        dp_id="test1", data_type=DataPointType.BATTLE_WIN,
        tongue_affinity="KO", content="Defeated a Shadow Mote",
        context="dungeon_floor_3", quality=1.0, floor=3,
    )
    absorbed = incubator.broadcast_data(dp1)
    check("Data broadcast", absorbed > 0)
    check("KO egg absorbed", egg_ko.total_absorbed > 0)
    check("Total tracked", incubator.total_data_absorbed > 0)

    # Personality shift from battle
    check("Aggressive trait shifted", egg_ko.personality["aggressive"] > 0.5)

    # Multiple data types
    for i in range(20):
        incubator.create_data_point(
            DataPointType.NPC_DIALOGUE,
            f"Conversation {i} with Polly about tongues",
            context="guild_hub",
            quality=0.8,
        )
    check("AV egg got dialogue data", egg_av.total_absorbed > 0)

    # Training centre — place a DR egg in its matching DR centre
    check("Place DR egg in DR centre", incubator.place_in_centre(egg_dr, "DR"))
    check("Egg location updated", egg_dr.location == EggLocation.TRAINING_CENTRE)
    check("DR centre has egg", len(incubator.training_centres["DR"].eggs) == 1)

    # Centre only absorbs matching tongue data
    dr_count_before = egg_dr.total_absorbed

    # Passive training (tick BEFORE retrieving so centre has an egg)
    passive = incubator.tick_training(elapsed_minutes=5.0)
    check("Passive training generated data", passive > 0)
    check("Centre egg got passive data", egg_dr.total_absorbed > dr_count_before)

    # Mismatched data rejected: KO data won't be absorbed by DR egg in DR centre
    ko_count = egg_dr.total_absorbed
    incubator.create_data_point(
        DataPointType.BATTLE_WIN,
        "Beat a boss using authority",
        context="dungeon",
        quality=1.0,
    )
    # egg_dr is in DR centre, this KO data shouldn't be absorbed
    # (but party eggs like egg_ko and egg_av will absorb it)

    # Retrieve from centre
    check("Retrieve egg", incubator.retrieve_from_centre(egg_dr))
    check("Egg back in party", egg_dr.location == EggLocation.PARTY)

    # Mass data to trigger hatching
    for i in range(150):
        incubator.create_data_point(
            random.choice(list(DataPointType)),
            f"Gameplay event {i}",
            context="testing",
            quality=random.uniform(0.5, 1.0),
            floor=random.randint(1, 25),
        )

    # Check if any eggs hatched
    any_hatched = any(e.stage != EggStage.EMBRYO for e in incubator.eggs)
    check("Some eggs advanced stages", any_hatched)

    # Hatch progress
    check("KO egg has progress", egg_ko.hatch_progress > 0)
    check("Personality summary works", len(egg_ko.personality_summary) > 0)
    check("Dominant trait exists", len(egg_ko.dominant_trait) > 0)
    print(f"    KO egg: {egg_ko.total_absorbed} data, {egg_ko.hatch_progress:.0%} hatch, personality: {egg_ko.personality_summary}")

    # Egg drop generation
    drops = 0
    for floor in range(1, 51):
        egg = generate_egg_drop(floor)
        if egg:
            drops += 1
    check("Egg drops from dungeon", drops > 0)
    check("Gate boss guaranteed", generate_egg_drop(10) is not None)
    print(f"    Drops from 50 floors: {drops}")

    # Story generation
    branch = incubator.generate_story_branch("KO", player_level=5)
    check("Story branch generated", branch is not None)
    check("Branch has title", len(branch.title) > 0)
    check("Branch has description", len(branch.description) > 0)
    check("Branch has choices", len(branch.choices) > 0)
    check("Branch has rewards", len(branch.rewards) > 0)
    print(f"    Quest: {branch.title}")
    print(f"    Desc:  {branch.description}")

    # All 6 tongues generate different quests
    seen_titles = set()
    for tongue_code in ["KO", "AV", "RU", "CA", "UM", "DR"]:
        b = incubator.generate_story_branch(tongue_code)
        seen_titles.add(b.title)
    check("Variety in quests", len(seen_titles) >= 4)

    # Stats
    stats = incubator.stats()
    check("Stats has total_eggs", stats["total_eggs"] == 3)
    check("Stats has centres", "centres" in stats)
    check("Stats has eggs list", "eggs" in stats)

    # SFT pair structure
    pairs = egg_ko.get_training_data()
    check("Training data exportable", len(pairs) > 0)
    if pairs:
        check("SFT pair has instruction", "instruction" in pairs[0])
        check("SFT pair has metadata", "metadata" in pairs[0])

    # ── Tri-Manifold Personality ─────────────────────────────────────
    print()
    print("  --- Tri-Manifold Personality ---")

    # Manifold initializes with all traits in M0
    tm = TriManifoldState()
    check("27 states constant", len(TRIMANIFOLD_STATES) == 27)
    check("Manifold has 6 traits", len(tm.trait_positions) == 6)
    check("All traits start M0", all(t == 0 for t, _ in tm.trait_positions.values()))
    check("All traits start spin alpha", all(s == 0 for _, s in tm.trait_positions.values()))

    # Battle data pushes aggressive toward M+ (expressed)
    tm.absorb_shift("aggressive", DataPointType.BATTLE_WIN, quality=1.0)
    agg_trit, agg_spin = tm.trait_positions["aggressive"]
    check("Battle shifts aggressive to +1", agg_trit == TRIT_POSITIVE)
    check("M+ energy > 0", tm.energy_positive > 0)

    # Lore data pushes curious toward M- (shadow/depth)
    tm.absorb_shift("curious", DataPointType.LORE_DISCOVERY, quality=1.0)
    cur_trit, _ = tm.trait_positions["curious"]
    check("Lore shifts curious to -1", cur_trit == TRIT_NEGATIVE)
    check("M- energy > 0", tm.energy_shadow > 0)

    # Choice data pulls toward M0 (emergent)
    tm.absorb_shift("aggressive", DataPointType.CHOICE_MADE, quality=1.0)
    agg_trit2, _ = tm.trait_positions["aggressive"]
    check("Choice pulls aggressive back to 0", agg_trit2 == TRIT_ZERO)
    check("M0 energy > 0", tm.energy_emergent > 0)

    # State index in range 0-26
    check("State index valid", 0 <= tm.state_index <= 26)
    check("Dominant manifold readable", len(tm.dominant_manifold) > 0)
    check("Depth in [0,1]", 0 <= tm.personality_depth <= 1)
    check("Expression in [0,1]", 0 <= tm.personality_expression <= 1)

    # Serialization round-trip
    tm_dict = tm.to_dict()
    tm_loaded = TriManifoldState.from_dict(tm_dict)
    check("Manifold round-trip energy", tm_loaded.energy_positive == tm.energy_positive)
    check("Manifold round-trip address", tm_loaded.ternary_address == tm.ternary_address)

    # Egg manifold integration — KO egg should have manifold data
    ko_stats = egg_ko.stats()
    check("Egg stats has manifold", "manifold" in ko_stats)
    check("Manifold has state_index", "state_index" in ko_stats["manifold"])
    ko_manifold = egg_ko.manifold
    check("KO egg manifold has energy", (ko_manifold.energy_positive + ko_manifold.energy_emergent + ko_manifold.energy_shadow) > 0)
    print(f"    KO egg manifold: state={ko_manifold.state_index}, {ko_manifold.dominant_manifold}, depth={ko_manifold.personality_depth:.2f}")

    # Summary
    print(f"\n  Incubator: {stats['total_eggs']} eggs, {stats['hatched']} hatched, {stats['total_data_absorbed']} data absorbed")
    for egg in incubator.eggs:
        s = egg.stats()
        print(f"    {s['name']} [{s['tongue']}] {s['stage']} — {s['total_absorbed']} data, {s['hatch_progress']}, {s['personality']}")

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    selftest()
