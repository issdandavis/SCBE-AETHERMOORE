#!/usr/bin/env python3
"""
Pokemon Trainer Hooks — Game-mechanic training data triggers.
=============================================================

Detects in-game location visits and interactions (Pokemon Center,
Day Care, Mart, Gym, save events) and converts them into SFT
training pairs that feed HuggingFace.

In-world lore: The AetherNet captures every meaningful player action
as protocol-layer training signal. The Pokemon Center is a "save
checkpoint" in governance space; the Day Care is a "mutation nursery";
Gyms are "authorization escalation gates."

Architecture:
    ROM emulator (PyBoy) -> PokemonCrystalMemoryReader -> TrainerHooks
      -> JSONL training pairs -> HuggingFace Hub (batch push)
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pokemon_memory import (
    PokemonState,
    PartyMon,
    species_name,
    move_name,
    JOHTO_BADGES,
    KANTO_BADGES,
)


# ---------------------------------------------------------------------------
# Pokemon Crystal map location database
# (map_group, map_number) -> location metadata
# From pokecrystal disassembly: maps/
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MapLocation:
    name: str
    location_type: str  # pokecenter, daycare, mart, gym, route, town, cave, etc.
    town: str = ""
    notes: str = ""


# Map IDs sourced from pokecrystal/constants/map_constants.asm
# Format: (group, number): MapLocation
CRYSTAL_MAP_DB: Dict[Tuple[int, int], MapLocation] = {
    # Pokemon Centers (Johto)
    (3, 1): MapLocation("New Bark Pokemon Center", "pokecenter", "New Bark Town"),
    (3, 5): MapLocation("Cherrygrove Pokemon Center", "pokecenter", "Cherrygrove City"),
    (3, 11): MapLocation("Violet Pokemon Center", "pokecenter", "Violet City"),
    (3, 19): MapLocation("Azalea Pokemon Center", "pokecenter", "Azalea Town"),
    (3, 25): MapLocation("Goldenrod Pokemon Center", "pokecenter", "Goldenrod City"),
    (3, 33): MapLocation("Ecruteak Pokemon Center", "pokecenter", "Ecruteak City"),
    (3, 39): MapLocation("Olivine Pokemon Center", "pokecenter", "Olivine City"),
    (3, 44): MapLocation("Cianwood Pokemon Center", "pokecenter", "Cianwood City"),
    (3, 49): MapLocation("Mahogany Pokemon Center", "pokecenter", "Mahogany Town"),
    (3, 55): MapLocation("Blackthorn Pokemon Center", "pokecenter", "Blackthorn City"),
    # Pokemon Centers (Kanto)
    (5, 1): MapLocation("Vermilion Pokemon Center", "pokecenter", "Vermilion City"),
    (5, 5): MapLocation("Saffron Pokemon Center", "pokecenter", "Saffron City"),
    (5, 10): MapLocation("Cerulean Pokemon Center", "pokecenter", "Cerulean City"),
    (5, 15): MapLocation("Lavender Pokemon Center", "pokecenter", "Lavender Town"),
    (5, 19): MapLocation("Celadon Pokemon Center", "pokecenter", "Celadon City"),
    (5, 25): MapLocation("Fuchsia Pokemon Center", "pokecenter", "Fuchsia City"),
    (5, 30): MapLocation("Pewter Pokemon Center", "pokecenter", "Pewter City"),
    (5, 35): MapLocation("Viridian Pokemon Center", "pokecenter", "Viridian City"),
    (5, 39): MapLocation("Pallet Pokemon Center", "pokecenter", "Pallet Town"),

    # Day Care
    (6, 2): MapLocation("Day Care", "daycare", "Route 34",
                         "Leave/retrieve Pokemon for leveling"),

    # Marts
    (3, 3): MapLocation("Cherrygrove Mart", "mart", "Cherrygrove City"),
    (3, 13): MapLocation("Violet Mart", "mart", "Violet City"),
    (3, 21): MapLocation("Azalea Mart", "mart", "Azalea Town"),
    (3, 27): MapLocation("Goldenrod Dept Store", "mart", "Goldenrod City",
                          "Multi-floor department store"),
    (3, 35): MapLocation("Ecruteak Mart", "mart", "Ecruteak City"),
    (3, 41): MapLocation("Olivine Mart", "mart", "Olivine City"),
    (3, 46): MapLocation("Cianwood Mart", "mart", "Cianwood City"),
    (3, 51): MapLocation("Mahogany Mart", "mart", "Mahogany Town"),
    (3, 57): MapLocation("Blackthorn Mart", "mart", "Blackthorn City"),

    # Gyms (Johto)
    (3, 9): MapLocation("Violet Gym", "gym", "Violet City",
                         "Falkner — Flying type"),
    (3, 17): MapLocation("Azalea Gym", "gym", "Azalea Town",
                          "Bugsy — Bug type"),
    (3, 23): MapLocation("Goldenrod Gym", "gym", "Goldenrod City",
                          "Whitney — Normal type"),
    (3, 31): MapLocation("Ecruteak Gym", "gym", "Ecruteak City",
                          "Morty — Ghost type"),
    (3, 37): MapLocation("Olivine Gym", "gym", "Olivine City",
                          "Jasmine — Steel type"),
    (3, 42): MapLocation("Cianwood Gym", "gym", "Cianwood City",
                          "Chuck — Fighting type"),
    (3, 47): MapLocation("Mahogany Gym", "gym", "Mahogany Town",
                          "Pryce — Ice type"),
    (3, 53): MapLocation("Blackthorn Gym", "gym", "Blackthorn City",
                          "Clair — Dragon type"),

    # Gyms (Kanto)
    (5, 7): MapLocation("Saffron Gym", "gym", "Saffron City",
                         "Sabrina — Psychic type"),
    (5, 12): MapLocation("Cerulean Gym", "gym", "Cerulean City",
                          "Misty — Water type"),
    (5, 21): MapLocation("Celadon Gym", "gym", "Celadon City",
                          "Erika — Grass type"),
    (5, 27): MapLocation("Fuchsia Gym", "gym", "Fuchsia City",
                          "Janine — Poison type"),
    (5, 32): MapLocation("Pewter Gym", "gym", "Pewter City",
                          "Brock — Rock type"),
    (5, 37): MapLocation("Viridian Gym", "gym", "Viridian City",
                          "Blue — Mixed types"),

    # Special locations
    (7, 1): MapLocation("Pokemon League Gate", "elite4", "Indigo Plateau"),
    (7, 2): MapLocation("Will's Room", "elite4", "Indigo Plateau",
                         "E4 #1 — Psychic"),
    (7, 3): MapLocation("Koga's Room", "elite4", "Indigo Plateau",
                         "E4 #2 — Poison"),
    (7, 4): MapLocation("Bruno's Room", "elite4", "Indigo Plateau",
                         "E4 #3 — Fighting"),
    (7, 5): MapLocation("Karen's Room", "elite4", "Indigo Plateau",
                         "E4 #4 — Dark"),
    (7, 6): MapLocation("Lance's Room", "elite4", "Indigo Plateau",
                         "Champion — Dragon"),

    # Towers / Dungeons
    (10, 1): MapLocation("Sprout Tower 1F", "dungeon", "Violet City"),
    (10, 2): MapLocation("Sprout Tower 2F", "dungeon", "Violet City"),
    (10, 3): MapLocation("Sprout Tower 3F", "dungeon", "Violet City"),
    (11, 1): MapLocation("Burned Tower 1F", "dungeon", "Ecruteak City"),
    (11, 2): MapLocation("Burned Tower B1F", "dungeon", "Ecruteak City"),
    (12, 1): MapLocation("Tin Tower 1F", "dungeon", "Ecruteak City"),
    (13, 1): MapLocation("Whirl Islands", "dungeon", "Route 41"),
    (14, 1): MapLocation("Mt. Mortar", "dungeon", "Route 42"),
    (15, 1): MapLocation("Ice Path 1F", "dungeon", "Route 44"),
    (16, 1): MapLocation("Dark Cave", "dungeon", "Route 31/46"),
    (24, 1): MapLocation("Mt. Silver", "dungeon", "Route 28",
                          "Final dungeon — Red at summit"),
}


def lookup_location(group: int, number: int) -> Optional[MapLocation]:
    """Look up a map location by group and number."""
    return CRYSTAL_MAP_DB.get((group, number))


def infer_location_type(group: int, number: int) -> str:
    """Infer location type, falling back to heuristics if not in DB."""
    loc = lookup_location(group, number)
    if loc:
        return loc.location_type
    # Heuristic: group 3 tends to be Johto interiors, group 5 Kanto
    return "unknown"


# ---------------------------------------------------------------------------
# Training pair dataclass
# ---------------------------------------------------------------------------

@dataclass
class TrainingHookPair:
    """A training pair generated by a game-mechanic hook."""
    instruction: str
    response: str
    category: str  # pokecenter_heal, daycare_deposit, gym_battle, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_jsonl_dict(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "response": self.response,
            "event_type": f"hook_{self.category}",
            "metadata": {
                "source": "pokemon_trainer_hooks",
                "category": self.category,
                **self.metadata,
            },
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Trainer Hooks — detect game mechanics and generate training data
# ---------------------------------------------------------------------------

class TrainerHooks:
    """Monitors game state transitions and generates training pairs
    when the player interacts with key game mechanics.

    Hooks:
        - Pokemon Center heal (party HP restored)
        - Day Care deposit/retrieve
        - Mart visits (item purchases)
        - Gym entry/badge earn
        - Save events (full state snapshot)
        - Evolution (species change)
        - Elite Four progression
        - Dungeon exploration
        - New Pokemon caught
        - Money changes
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        hf_repo_id: str = "",
        hf_token: str = "",
        batch_size: int = 50,
    ) -> None:
        self.output_dir = output_dir or Path("training-data/hook_sessions")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.hf_repo_id = hf_repo_id or os.environ.get(
            "HF_POKEMON_REPO", "SCBE-AETHER/pokemon-crystal-sft-v1"
        )
        self.hf_token = hf_token or os.environ.get("HF_TOKEN", "")
        self.batch_size = batch_size

        # State tracking
        self._prev_state: Optional[PokemonState] = None
        self._prev_location: Optional[MapLocation] = None
        self._in_pokecenter: bool = False
        self._in_daycare: bool = False
        self._in_gym: bool = False
        self._in_dungeon: bool = False
        self._daycare_party_snapshot: List[int] = []  # species IDs when entering

        # Pair buffer
        self._pairs: List[TrainingHookPair] = []
        self._total_emitted: int = 0
        self._session_id: str = uuid.uuid4().hex[:10]
        self._step: int = 0

        # Save detection
        self._save_cooldown: int = 0  # frames since last save-like event

    # -- Public API -------------------------------------------------------

    def tick(self, state: PokemonState, step: int = 0) -> List[TrainingHookPair]:
        """Process one frame of game state. Returns any new training pairs."""
        self._step = step
        new_pairs: List[TrainingHookPair] = []

        if self._prev_state is None:
            self._prev_state = state
            self._update_location_flags(state)
            return new_pairs

        # Location transition detection
        location_changed = self._check_location_change(state)
        if location_changed:
            new_pairs.extend(self._on_location_change(state))

        # Pokemon Center healing detection
        new_pairs.extend(self._check_pokecenter_heal(state))

        # Day Care deposit/retrieve detection
        new_pairs.extend(self._check_daycare(state))

        # Gym badge detection
        new_pairs.extend(self._check_badge_earned(state))

        # Evolution detection (species changed in party slot)
        new_pairs.extend(self._check_evolution(state))

        # New Pokemon caught
        new_pairs.extend(self._check_pokemon_caught(state))

        # Level up
        new_pairs.extend(self._check_level_up(state))

        # Money change (Mart/item interaction proxy)
        new_pairs.extend(self._check_money_change(state))

        # Save detection (cooldown-based)
        if self._save_cooldown > 0:
            self._save_cooldown -= 1

        # Buffer pairs
        self._pairs.extend(new_pairs)
        self._total_emitted += len(new_pairs)

        # Auto-flush when batch is full
        if len(self._pairs) >= self.batch_size:
            self.flush()

        self._prev_state = state
        return new_pairs

    def generate_save_pairs(self, state: PokemonState) -> List[TrainingHookPair]:
        """Explicitly called when a save event is detected.
        Generates a comprehensive state snapshot as training data."""
        if self._save_cooldown > 0:
            return []
        self._save_cooldown = 300  # ~10 seconds at 30fps

        pairs = []

        # Full party snapshot
        party_desc = self._describe_party(state)
        pairs.append(TrainingHookPair(
            instruction=(
                f"Pokemon Center Save Point: The trainer {state.player_name} saves their game. "
                f"Party: {party_desc}. "
                f"Badges: {state.total_badges} ({', '.join(state.johto_badge_names + state.kanto_badge_names) or 'none'}). "
                f"Money: ${state.money:,}. "
                f"Pokedex: {state.pokedex_owned} owned. "
                f"Location: map ({state.map_group},{state.map_number}) at ({state.player_x},{state.player_y}). "
                f"Evaluate this trainer's progress and suggest next steps."
            ),
            response=self._generate_progress_advice(state),
            category="save_checkpoint",
            metadata={
                "player_name": state.player_name,
                "party_count": state.party_count,
                "total_badges": state.total_badges,
                "money": state.money,
                "pokedex_owned": state.pokedex_owned,
                "map": f"{state.map_group}:{state.map_number}",
                "step": self._step,
            },
        ))

        # Individual Pokemon snapshots (one per party member)
        for i, mon in enumerate(state.party):
            pairs.append(TrainingHookPair(
                instruction=(
                    f"Save checkpoint: Describe the status of party slot {i+1}. "
                    f"Species: {mon.species_name} (#{mon.species_id}), Level {mon.level}, "
                    f"HP: {mon.hp}/{mon.max_hp}, "
                    f"Moves: {', '.join(n for n in mon.move_names if n != '(none)')}. "
                    f"Status: {'healthy' if mon.status == 0 else f'condition {mon.status}'}."
                ),
                response=(
                    f"{mon.species_name} is {'in great shape' if mon.hp_ratio > 0.8 else 'injured and needs healing' if mon.hp_ratio < 0.3 else 'moderately healthy'}. "
                    f"At level {mon.level}, it knows {sum(1 for m in mon.moves if m > 0)} moves. "
                    f"{'Consider visiting a Pokemon Center.' if mon.hp_ratio < 0.5 else 'Ready for battle.'}"
                ),
                category="save_pokemon_status",
                metadata={
                    "slot": i + 1,
                    "species_id": mon.species_id,
                    "level": mon.level,
                    "hp_ratio": round(mon.hp_ratio, 3),
                    "step": self._step,
                },
            ))

        self._pairs.extend(pairs)
        self._total_emitted += len(pairs)
        return pairs

    def flush(self) -> Optional[str]:
        """Write buffered pairs to JSONL and optionally push to HuggingFace."""
        if not self._pairs:
            return None

        filename = f"hooks_{self._session_id}_{self._step:06d}.jsonl"
        path = self.output_dir / filename

        with open(path, "w", encoding="utf-8") as f:
            for pair in self._pairs:
                f.write(json.dumps(pair.to_jsonl_dict(), ensure_ascii=False) + "\n")

        count = len(self._pairs)
        self._pairs.clear()

        # Push to HuggingFace if configured
        if self.hf_repo_id and self.hf_token:
            self._push_to_hf(path)

        return str(path)

    def stats(self) -> Dict[str, Any]:
        """Return hook statistics."""
        return {
            "session_id": self._session_id,
            "total_emitted": self._total_emitted,
            "buffered": len(self._pairs),
            "step": self._step,
            "hf_repo": self.hf_repo_id if self.hf_token else "(not configured)",
        }

    # -- Location detection ------------------------------------------------

    def _check_location_change(self, state: PokemonState) -> bool:
        prev = self._prev_state
        if prev is None:
            return True
        return (state.map_group != prev.map_group or
                state.map_number != prev.map_number)

    def _update_location_flags(self, state: PokemonState) -> None:
        loc = lookup_location(state.map_group, state.map_number)
        self._prev_location = loc
        if loc:
            self._in_pokecenter = loc.location_type == "pokecenter"
            self._in_daycare = loc.location_type == "daycare"
            self._in_gym = loc.location_type == "gym"
            self._in_dungeon = loc.location_type in ("dungeon", "elite4")
        else:
            self._in_pokecenter = False
            self._in_daycare = False
            self._in_gym = False
            self._in_dungeon = False

    def _on_location_change(self, state: PokemonState) -> List[TrainingHookPair]:
        pairs = []
        new_loc = lookup_location(state.map_group, state.map_number)

        # Snapshot party when entering Day Care
        if new_loc and new_loc.location_type == "daycare":
            self._daycare_party_snapshot = [m.species_id for m in state.party]

        self._update_location_flags(state)

        if new_loc:
            # Entering a notable location
            pairs.append(TrainingHookPair(
                instruction=(
                    f"The trainer enters {new_loc.name} in {new_loc.town}. "
                    f"{'(' + new_loc.notes + ') ' if new_loc.notes else ''}"
                    f"Party has {state.party_count} Pokemon, average HP "
                    f"{state.party_hp_ratio:.0%}. "
                    f"What should the trainer do here?"
                ),
                response=self._location_entry_advice(new_loc, state),
                category=f"enter_{new_loc.location_type}",
                metadata={
                    "location_name": new_loc.name,
                    "location_type": new_loc.location_type,
                    "town": new_loc.town,
                    "party_hp": round(state.party_hp_ratio, 3),
                    "step": self._step,
                },
            ))

        return pairs

    # -- Pokemon Center healing --------------------------------------------

    def _check_pokecenter_heal(self, state: PokemonState) -> List[TrainingHookPair]:
        if not self._in_pokecenter or self._prev_state is None:
            return []

        prev = self._prev_state
        pairs = []

        # Detect healing: party HP ratio jumped significantly
        prev_ratio = prev.party_hp_ratio
        curr_ratio = state.party_hp_ratio
        healed = (curr_ratio - prev_ratio) > 0.3 and curr_ratio > 0.95

        if healed:
            party_desc = self._describe_party(state)
            loc = lookup_location(state.map_group, state.map_number)
            loc_name = loc.name if loc else "Pokemon Center"

            pairs.append(TrainingHookPair(
                instruction=(
                    f"The trainer healed their Pokemon at {loc_name}. "
                    f"Party was at {prev_ratio:.0%} HP, now fully restored. "
                    f"Team: {party_desc}. "
                    f"Badges: {state.total_badges}. "
                    f"What should the trainer do after healing?"
                ),
                response=self._post_heal_advice(state),
                category="pokecenter_heal",
                metadata={
                    "location": loc_name,
                    "prev_hp_ratio": round(prev_ratio, 3),
                    "curr_hp_ratio": round(curr_ratio, 3),
                    "party_count": state.party_count,
                    "total_badges": state.total_badges,
                    "step": self._step,
                },
            ))

            # Also generate a save-like snapshot on heal
            pairs.extend(self.generate_save_pairs(state))

        return pairs

    # -- Day Care ----------------------------------------------------------

    def _check_daycare(self, state: PokemonState) -> List[TrainingHookPair]:
        if not self._in_daycare or self._prev_state is None:
            return []

        prev = self._prev_state
        pairs = []

        # Detect deposit: party count decreased
        if state.party_count < prev.party_count:
            # Figure out which Pokemon was deposited
            curr_species = {m.species_id for m in state.party}
            prev_species = [m for m in prev.party]
            deposited = [m for m in prev_species if m.species_id not in curr_species]
            dep_name = deposited[0].species_name if deposited else "a Pokemon"
            dep_level = deposited[0].level if deposited else 0

            pairs.append(TrainingHookPair(
                instruction=(
                    f"The trainer left {dep_name} (Lv.{dep_level}) at the Day Care on Route 34. "
                    f"Party is now {state.party_count}/6. "
                    f"Why would a trainer use the Day Care?"
                ),
                response=(
                    f"The Day Care raises Pokemon by 1 XP per step walked. "
                    f"Leaving {dep_name} here will level it up passively while "
                    f"the trainer explores. It's ideal for Pokemon that need levels "
                    f"but aren't in the active battle rotation. Come back later "
                    f"to retrieve a stronger {dep_name}."
                ),
                category="daycare_deposit",
                metadata={
                    "deposited": dep_name,
                    "deposited_level": dep_level,
                    "party_count_after": state.party_count,
                    "step": self._step,
                },
            ))

        # Detect retrieve: party count increased while in Day Care
        if state.party_count > prev.party_count and self._in_daycare:
            curr_species = {m.species_id for m in state.party}
            prev_species = {m.species_id for m in prev.party}
            new_ids = curr_species - prev_species
            if new_ids:
                retrieved = [m for m in state.party if m.species_id in new_ids]
                ret_name = retrieved[0].species_name if retrieved else "a Pokemon"
                ret_level = retrieved[0].level if retrieved else 0

                pairs.append(TrainingHookPair(
                    instruction=(
                        f"The trainer retrieved {ret_name} (Lv.{ret_level}) from the Day Care. "
                        f"Party is now {state.party_count}/6. "
                        f"Assess the retrieved Pokemon's battle readiness."
                    ),
                    response=(
                        f"{ret_name} has been leveled up at the Day Care to level {ret_level}. "
                        f"Check its move set — the Day Care may have replaced moves with "
                        f"ones learned by leveling. Make sure to review and adjust moves "
                        f"before heading into battle."
                    ),
                    category="daycare_retrieve",
                    metadata={
                        "retrieved": ret_name,
                        "retrieved_level": ret_level,
                        "party_count_after": state.party_count,
                        "step": self._step,
                    },
                ))

        return pairs

    # -- Gym / Badge -------------------------------------------------------

    def _check_badge_earned(self, state: PokemonState) -> List[TrainingHookPair]:
        if self._prev_state is None:
            return []

        prev = self._prev_state
        pairs = []

        if state.total_badges > prev.total_badges:
            new_count = state.total_badges
            # Determine which badge was earned
            new_johto = [b for b in state.johto_badge_names
                         if b not in prev.johto_badge_names]
            new_kanto = [b for b in state.kanto_badge_names
                         if b not in prev.kanto_badge_names]
            badge_name = (new_johto + new_kanto)[0] if (new_johto + new_kanto) else f"Badge #{new_count}"

            loc = lookup_location(state.map_group, state.map_number)
            gym_name = loc.name if loc and loc.location_type == "gym" else "the Gym"

            pairs.append(TrainingHookPair(
                instruction=(
                    f"The trainer earned the {badge_name} Badge at {gym_name}! "
                    f"Total badges: {new_count}/16. "
                    f"Team: {self._describe_party(state)}. "
                    f"Money: ${state.money:,}. "
                    f"What's the next milestone?"
                ),
                response=self._badge_milestone_advice(new_count, badge_name, state),
                category="badge_earned",
                metadata={
                    "badge_name": badge_name,
                    "total_badges": new_count,
                    "party_levels": [m.level for m in state.party],
                    "step": self._step,
                },
            ))

            # Badge = major milestone, also save
            pairs.extend(self.generate_save_pairs(state))

        return pairs

    # -- Evolution ---------------------------------------------------------

    def _check_evolution(self, state: PokemonState) -> List[TrainingHookPair]:
        if self._prev_state is None:
            return []

        prev = self._prev_state
        pairs = []

        for i, (pm, cm) in enumerate(zip(prev.party, state.party)):
            if cm.species_id != pm.species_id and cm.species_id > 0 and pm.species_id > 0:
                pairs.append(TrainingHookPair(
                    instruction=(
                        f"Party slot {i+1}: {pm.species_name} evolved into {cm.species_name}! "
                        f"Level: {cm.level}. "
                        f"New moves: {', '.join(n for n in cm.move_names if n != '(none)')}. "
                        f"Describe the significance of this evolution."
                    ),
                    response=(
                        f"Congratulations! {pm.species_name} has evolved into {cm.species_name} "
                        f"at level {cm.level}. This evolution brings stat increases across the board. "
                        f"Check the new move set — {cm.species_name} may have access to stronger "
                        f"moves now. This is a great milestone in the trainer's journey."
                    ),
                    category="evolution",
                    metadata={
                        "slot": i + 1,
                        "from_species": pm.species_name,
                        "to_species": cm.species_name,
                        "level": cm.level,
                        "step": self._step,
                    },
                ))

        return pairs

    # -- Pokemon caught ----------------------------------------------------

    def _check_pokemon_caught(self, state: PokemonState) -> List[TrainingHookPair]:
        if self._prev_state is None:
            return []

        prev = self._prev_state
        pairs = []

        if state.party_count > prev.party_count and not self._in_daycare:
            # New party member
            if state.party:
                new_mon = state.party[-1]
                pairs.append(TrainingHookPair(
                    instruction=(
                        f"The trainer caught {new_mon.species_name} (Lv.{new_mon.level})! "
                        f"Party is now {state.party_count}/6. "
                        f"Pokedex: {state.pokedex_owned} owned. "
                        f"Assess this new team member and how it fits the party."
                    ),
                    response=self._catch_assessment(new_mon, state),
                    category="pokemon_caught",
                    metadata={
                        "species_id": new_mon.species_id,
                        "species_name": new_mon.species_name,
                        "level": new_mon.level,
                        "party_count": state.party_count,
                        "pokedex_owned": state.pokedex_owned,
                        "step": self._step,
                    },
                ))

        return pairs

    # -- Level up ----------------------------------------------------------

    def _check_level_up(self, state: PokemonState) -> List[TrainingHookPair]:
        if self._prev_state is None:
            return []

        prev = self._prev_state
        pairs = []

        for i, (pm, cm) in enumerate(zip(prev.party, state.party)):
            if cm.level > pm.level and cm.species_id == pm.species_id:
                pairs.append(TrainingHookPair(
                    instruction=(
                        f"{cm.species_name} leveled up from {pm.level} to {cm.level}! "
                        f"HP: {cm.hp}/{cm.max_hp}. "
                        f"Moves: {', '.join(n for n in cm.move_names if n != '(none)')}. "
                        f"Any advice for this level?"
                    ),
                    response=(
                        f"{cm.species_name} grows stronger at level {cm.level}. "
                        f"{'It may learn a new move soon — check the summary screen.' if cm.level % 4 == 0 else 'Keep training for more power.'} "
                        f"{'Consider evolving soon!' if cm.level >= 16 and cm.level <= 36 else ''}"
                    ).strip(),
                    category="level_up",
                    metadata={
                        "species_name": cm.species_name,
                        "from_level": pm.level,
                        "to_level": cm.level,
                        "slot": i + 1,
                        "step": self._step,
                    },
                ))

        return pairs

    # -- Money change (Mart proxy) -----------------------------------------

    def _check_money_change(self, state: PokemonState) -> List[TrainingHookPair]:
        if self._prev_state is None:
            return []

        prev = self._prev_state
        pairs = []
        delta = state.money - prev.money

        # Only trigger on significant spending while in a mart
        if self._in_pokecenter or not self._prev_location:
            return pairs

        loc = lookup_location(state.map_group, state.map_number)
        is_mart = loc and loc.location_type == "mart"

        if is_mart and delta < -100:
            # Player spent money at a mart
            pairs.append(TrainingHookPair(
                instruction=(
                    f"The trainer spent ${abs(delta):,} at {loc.name if loc else 'a Poke Mart'}. "
                    f"Remaining money: ${state.money:,}. "
                    f"Badges: {state.total_badges}. "
                    f"What items should a trainer prioritize buying?"
                ),
                response=(
                    f"Smart purchases for a trainer with {state.total_badges} badges: "
                    f"Potions (heal in dungeons), Poke Balls (catch new Pokemon), "
                    f"and status healers (Antidotes, Awakenings). "
                    f"{'Save money for Ultra Balls later.' if state.total_badges < 4 else 'Consider Full Restores and Ultra Balls at this stage.'} "
                    f"Budget remaining: ${state.money:,}."
                ),
                category="mart_purchase",
                metadata={
                    "spent": abs(delta),
                    "remaining": state.money,
                    "location": loc.name if loc else "mart",
                    "step": self._step,
                },
            ))

        return pairs

    # -- Response generators -----------------------------------------------

    def _describe_party(self, state: PokemonState) -> str:
        if not state.party:
            return "empty party"
        parts = []
        for m in state.party:
            hp_pct = f"{m.hp_ratio:.0%}" if m.max_hp > 0 else "?"
            parts.append(f"{m.species_name} Lv.{m.level} ({hp_pct} HP)")
        return ", ".join(parts)

    def _generate_progress_advice(self, state: PokemonState) -> str:
        badges = state.total_badges
        avg_level = (sum(m.level for m in state.party) / max(1, len(state.party))
                     if state.party else 0)

        if badges == 0:
            return (
                "Just starting out! Head to the first Gym in Violet City. "
                "Train your starter to at least level 10 before challenging Falkner. "
                f"Current team average: Lv.{avg_level:.0f}."
            )
        elif badges < 4:
            return (
                f"Making progress with {badges} badges. "
                f"Team average is Lv.{avg_level:.0f}. "
                "Continue exploring routes for wild Pokemon to round out the team. "
                "Make sure to stock up on Potions before the next Gym."
            )
        elif badges < 8:
            return (
                f"Strong progress at {badges} badges! "
                f"Team average is Lv.{avg_level:.0f}. "
                "Focus on type coverage — make sure the team can handle the "
                "remaining Gym types. Consider using TMs for stronger moves."
            )
        elif badges == 8:
            return (
                "All 8 Johto badges earned! Time for Victory Road and the Elite Four. "
                f"Team average is Lv.{avg_level:.0f} — "
                f"{'train to at least Lv.40 before the E4.' if avg_level < 40 else 'the team is ready!'}"
            )
        else:
            return (
                f"Deep into Kanto with {badges} total badges! "
                f"Team average is Lv.{avg_level:.0f}. "
                "Keep challenging Kanto Gyms. The ultimate goal: Mt. Silver and Red."
            )

    def _post_heal_advice(self, state: PokemonState) -> str:
        loc = lookup_location(state.map_group, state.map_number)
        town = loc.town if loc else "town"

        if self._in_gym or state.total_badges < 8:
            return (
                f"Team fully healed at {town}. "
                "Now's a good time to challenge the local Gym if you haven't yet, "
                "or explore nearby routes for wild encounters and trainer battles. "
                "Make sure you have enough Potions in your bag before heading out."
            )
        return (
            f"Healed up at {town}. With {state.total_badges} badges, "
            "focus on your next objective. Check the Town Map for guidance."
        )

    def _location_entry_advice(self, loc: MapLocation, state: PokemonState) -> str:
        if loc.location_type == "pokecenter":
            return (
                f"Welcome to {loc.name}. "
                f"{'Your team needs healing!' if state.party_hp_ratio < 0.7 else 'Team is healthy, but you can save here.'} "
                "Talk to Nurse Joy to heal, use the PC to manage your boxes, "
                "or access the trade/battle center upstairs."
            )
        elif loc.location_type == "daycare":
            return (
                "The Day Care on Route 34 raises Pokemon by walking. "
                "Leave a Pokemon here to level it passively. "
                "If you leave two compatible Pokemon, they may produce an Egg! "
                f"Your party has {state.party_count}/6 Pokemon."
            )
        elif loc.location_type == "mart":
            return (
                f"Stock up at {loc.name}. "
                f"You have ${state.money:,} to spend. "
                "Priority items: Potions, Poke Balls, and status healers."
            )
        elif loc.location_type == "gym":
            return (
                f"Entering {loc.name}! {loc.notes or ''} "
                f"Your team: {self._describe_party(state)}. "
                "Make sure your team is prepared for this type matchup."
            )
        elif loc.location_type in ("dungeon", "elite4"):
            return (
                f"Entering {loc.name}. "
                f"{'This is a challenging area — make sure you have healing items.' if loc.location_type == 'dungeon' else 'The Elite Four awaits!'} "
                f"Party HP: {state.party_hp_ratio:.0%}."
            )
        return f"Arrived at {loc.name} in {loc.town}. Explore and interact with NPCs."

    def _badge_milestone_advice(
        self, count: int, badge_name: str, state: PokemonState
    ) -> str:
        avg_level = (sum(m.level for m in state.party) / max(1, len(state.party))
                     if state.party else 0)
        if count <= 3:
            return (
                f"The {badge_name} Badge is earned! {count}/8 Johto badges. "
                f"Team average: Lv.{avg_level:.0f}. "
                "Head to the next city and train along the way. "
                "Talk to NPCs for hints about the next Gym Leader's type."
            )
        elif count <= 7:
            return (
                f"Excellent! {badge_name} Badge obtained — {count}/8 Johto badges. "
                f"Team average: Lv.{avg_level:.0f}. "
                "The remaining Gyms get tougher. Focus on type coverage and leveling."
            )
        elif count == 8:
            return (
                f"All 8 Johto badges with the {badge_name} Badge! "
                f"Team average: Lv.{avg_level:.0f}. "
                "Victory Road opens — prepare for the Elite Four. "
                "Stock up on Full Restores and Revives."
            )
        else:
            return (
                f"Kanto badge #{count - 8} ({badge_name}) earned! "
                f"Total: {count}/16. Team average: Lv.{avg_level:.0f}. "
                "Keep pushing through Kanto. Mt. Silver awaits."
            )

    def _catch_assessment(self, mon: PartyMon, state: PokemonState) -> str:
        from pokemon_ai_agent import get_species_type
        mon_type = get_species_type(mon.species_id)
        party_types = set()
        for m in state.party:
            party_types.add(get_species_type(m.species_id))

        if mon_type not in party_types:
            type_note = f"Great catch! {mon.species_name} adds {mon_type}-type coverage the team was missing."
        else:
            type_note = f"{mon.species_name} is {mon_type}-type, which the team already has. Consider box management."

        return (
            f"{type_note} "
            f"At Lv.{mon.level}, {'it can contribute to battles right away' if mon.level >= 15 else 'it will need some training to catch up'}. "
            f"Pokedex progress: {state.pokedex_owned} Pokemon owned."
        )

    # -- HuggingFace push --------------------------------------------------

    def _push_to_hf(self, local_path: Path) -> None:
        """Push a JSONL file to HuggingFace Hub."""
        try:
            from huggingface_hub import HfApi
            api = HfApi(token=self.hf_token)
            api.upload_file(
                path_or_fileobj=str(local_path),
                path_in_repo=f"data/hooks/{local_path.name}",
                repo_id=self.hf_repo_id,
                repo_type="dataset",
            )
        except ImportError:
            pass  # huggingface_hub not installed
        except Exception as exc:
            print(f"[hooks] HF push failed: {exc}")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Validate hooks with mock state transitions."""
    hooks = TrainerHooks(output_dir=Path("/tmp/hook_test"))

    # Build mock states
    def _make_mon(species: int, level: int, hp: int, max_hp: int) -> PartyMon:
        return PartyMon(
            species_id=species,
            species_name=species_name(species),
            level=level, hp=hp, max_hp=max_hp,
            moves=[33, 52, 0, 0],
            move_names=[move_name(33), move_name(52), "(none)", "(none)"],
            status=0,
        )

    state1 = PokemonState(
        player_name="ASH",
        party_count=2,
        party=[_make_mon(155, 8, 15, 30), _make_mon(16, 5, 12, 20)],
        map_group=3, map_number=5,  # Cherrygrove Pokemon Center
        player_x=5, player_y=3,
        johto_badges=0x01, kanto_badges=0,
        johto_badge_names=["Zephyr"],
        kanto_badge_names=[],
        johto_badge_count=1, kanto_badge_count=0,
        money=5000, in_battle=False,
        enemy_species=0, enemy_species_name="",
        enemy_level=0, enemy_hp=0, enemy_max_hp=0,
        pokedex_owned=8,
    )

    # Tick 1: enter Pokemon Center
    pairs1 = hooks.tick(state1, step=100)
    # First tick just stores prev_state
    assert isinstance(pairs1, list)

    # State 2: healed at Pokemon Center
    state2 = PokemonState(
        player_name="ASH",
        party_count=2,
        party=[_make_mon(155, 8, 30, 30), _make_mon(16, 5, 20, 20)],
        map_group=3, map_number=5,
        player_x=5, player_y=3,
        johto_badges=0x01, kanto_badges=0,
        johto_badge_names=["Zephyr"],
        kanto_badge_names=[],
        johto_badge_count=1, kanto_badge_count=0,
        money=5000, in_battle=False,
        enemy_species=0, enemy_species_name="",
        enemy_level=0, enemy_hp=0, enemy_max_hp=0,
        pokedex_owned=8,
    )
    pairs2 = hooks.tick(state2, step=200)
    heal_pairs = [p for p in pairs2 if p.category == "pokecenter_heal"]
    assert len(heal_pairs) >= 1, f"Expected heal pair, got {len(heal_pairs)}"
    assert "healed" in heal_pairs[0].instruction.lower()

    # State 3: move to Day Care
    state3 = PokemonState(
        player_name="ASH",
        party_count=2,
        party=[_make_mon(155, 8, 30, 30), _make_mon(16, 5, 20, 20)],
        map_group=6, map_number=2,  # Day Care
        player_x=3, player_y=4,
        johto_badges=0x01, kanto_badges=0,
        johto_badge_names=["Zephyr"],
        kanto_badge_names=[],
        johto_badge_count=1, kanto_badge_count=0,
        money=5000, in_battle=False,
        enemy_species=0, enemy_species_name="",
        enemy_level=0, enemy_hp=0, enemy_max_hp=0,
        pokedex_owned=8,
    )
    pairs3 = hooks.tick(state3, step=300)
    enter_pairs = [p for p in pairs3 if "daycare" in p.category]
    assert len(enter_pairs) >= 1, f"Expected daycare entry pair, got {len(enter_pairs)}"

    # State 4: deposit a Pokemon at Day Care
    state4 = PokemonState(
        player_name="ASH",
        party_count=1,
        party=[_make_mon(155, 8, 30, 30)],
        map_group=6, map_number=2,
        player_x=3, player_y=4,
        johto_badges=0x01, kanto_badges=0,
        johto_badge_names=["Zephyr"],
        kanto_badge_names=[],
        johto_badge_count=1, kanto_badge_count=0,
        money=5000, in_battle=False,
        enemy_species=0, enemy_species_name="",
        enemy_level=0, enemy_hp=0, enemy_max_hp=0,
        pokedex_owned=8,
    )
    pairs4 = hooks.tick(state4, step=400)
    deposit_pairs = [p for p in pairs4 if p.category == "daycare_deposit"]
    assert len(deposit_pairs) >= 1, f"Expected deposit pair, got {len(deposit_pairs)}"

    # State 5: level up + evolution
    state5 = PokemonState(
        player_name="ASH",
        party_count=1,
        party=[_make_mon(156, 14, 40, 40)],  # Cyndaquil -> Quilava at 14
        map_group=4, map_number=1,  # Some route
        player_x=8, player_y=6,
        johto_badges=0x01, kanto_badges=0,
        johto_badge_names=["Zephyr"],
        kanto_badge_names=[],
        johto_badge_count=1, kanto_badge_count=0,
        money=5000, in_battle=False,
        enemy_species=0, enemy_species_name="",
        enemy_level=0, enemy_hp=0, enemy_max_hp=0,
        pokedex_owned=8,
    )
    pairs5 = hooks.tick(state5, step=500)
    evo_pairs = [p for p in pairs5 if p.category == "evolution"]
    assert len(evo_pairs) >= 1, f"Expected evolution pair, got {len(evo_pairs)}"
    assert "Cyndaquil" in evo_pairs[0].instruction
    assert "Quilava" in evo_pairs[0].instruction

    # Test save pair generation (reset cooldown from earlier heal)
    hooks._save_cooldown = 0
    save_pairs = hooks.generate_save_pairs(state5)
    assert len(save_pairs) >= 2, f"Expected >= 2 save pairs, got {len(save_pairs)}"
    assert save_pairs[0].category == "save_checkpoint"

    # Test stats
    stats = hooks.stats()
    assert stats["total_emitted"] > 0

    # Test flush
    path = hooks.flush()
    assert path is not None
    assert Path(path).exists()

    print("pokemon_trainer_hooks.py -- all tests PASSED")
    print(f"  Stats: {stats}")
    print(f"  JSONL written to: {path}")


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        _self_test()
    else:
        print("Usage: python pokemon_trainer_hooks.py --test")
