#!/usr/bin/env python3
"""Pokemon Crystal Smart AI Agent -- Makes decisions based on game memory state.

Uses PokemonState (from pokemon_memory.py) to choose contextually appropriate
button presses: battle strategy, healing navigation, and smart exploration
with tile-visit tracking.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Pokemon type effectiveness chart
# ---------------------------------------------------------------------------

# Indices: 0=Normal 1=Fire 2=Water 3=Electric 4=Grass 5=Ice 6=Fighting
# 7=Poison 8=Ground 9=Flying 10=Psychic 11=Bug 12=Rock 13=Ghost
# 14=Dragon 15=Dark 16=Steel

TYPE_NAMES: List[str] = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
    "Rock", "Ghost", "Dragon", "Dark", "Steel",
]

TYPE_INDEX: Dict[str, int] = {name: i for i, name in enumerate(TYPE_NAMES)}

# Effectiveness multipliers: _CHART[attacker_type][defender_type]
# 1.0 = neutral, 2.0 = super effective, 0.5 = not very effective, 0.0 = immune
_CHART: Dict[Tuple[int, int], float] = {}

def _se(atk: str, defn: str, mult: float) -> None:
    _CHART[(TYPE_INDEX[atk], TYPE_INDEX[defn])] = mult

# Fire
_se("Fire", "Grass", 2.0); _se("Fire", "Ice", 2.0); _se("Fire", "Bug", 2.0)
_se("Fire", "Steel", 2.0); _se("Fire", "Water", 0.5); _se("Fire", "Rock", 0.5)
_se("Fire", "Fire", 0.5); _se("Fire", "Dragon", 0.5)

# Water
_se("Water", "Fire", 2.0); _se("Water", "Ground", 2.0); _se("Water", "Rock", 2.0)
_se("Water", "Water", 0.5); _se("Water", "Grass", 0.5); _se("Water", "Dragon", 0.5)

# Grass
_se("Grass", "Water", 2.0); _se("Grass", "Ground", 2.0); _se("Grass", "Rock", 2.0)
_se("Grass", "Fire", 0.5); _se("Grass", "Grass", 0.5); _se("Grass", "Poison", 0.5)
_se("Grass", "Flying", 0.5); _se("Grass", "Bug", 0.5); _se("Grass", "Dragon", 0.5)
_se("Grass", "Steel", 0.5)

# Electric
_se("Electric", "Water", 2.0); _se("Electric", "Flying", 2.0)
_se("Electric", "Electric", 0.5); _se("Electric", "Grass", 0.5)
_se("Electric", "Dragon", 0.5); _se("Electric", "Ground", 0.0)

# Ice
_se("Ice", "Grass", 2.0); _se("Ice", "Ground", 2.0); _se("Ice", "Flying", 2.0)
_se("Ice", "Dragon", 2.0); _se("Ice", "Fire", 0.5); _se("Ice", "Water", 0.5)
_se("Ice", "Ice", 0.5); _se("Ice", "Steel", 0.5)

# Fighting
_se("Fighting", "Normal", 2.0); _se("Fighting", "Ice", 2.0); _se("Fighting", "Rock", 2.0)
_se("Fighting", "Dark", 2.0); _se("Fighting", "Steel", 2.0)
_se("Fighting", "Poison", 0.5); _se("Fighting", "Flying", 0.5); _se("Fighting", "Psychic", 0.5)
_se("Fighting", "Bug", 0.5); _se("Fighting", "Ghost", 0.0)

# Poison
_se("Poison", "Grass", 2.0); _se("Poison", "Poison", 0.5)
_se("Poison", "Ground", 0.5); _se("Poison", "Rock", 0.5)
_se("Poison", "Ghost", 0.5); _se("Poison", "Steel", 0.0)

# Ground
_se("Ground", "Fire", 2.0); _se("Ground", "Electric", 2.0); _se("Ground", "Poison", 2.0)
_se("Ground", "Rock", 2.0); _se("Ground", "Steel", 2.0)
_se("Ground", "Grass", 0.5); _se("Ground", "Bug", 0.5); _se("Ground", "Flying", 0.0)

# Flying
_se("Flying", "Grass", 2.0); _se("Flying", "Fighting", 2.0); _se("Flying", "Bug", 2.0)
_se("Flying", "Electric", 0.5); _se("Flying", "Rock", 0.5); _se("Flying", "Steel", 0.5)

# Psychic
_se("Psychic", "Fighting", 2.0); _se("Psychic", "Poison", 2.0)
_se("Psychic", "Psychic", 0.5); _se("Psychic", "Steel", 0.5)
_se("Psychic", "Dark", 0.0)

# Bug
_se("Bug", "Grass", 2.0); _se("Bug", "Psychic", 2.0); _se("Bug", "Dark", 2.0)
_se("Bug", "Fire", 0.5); _se("Bug", "Fighting", 0.5); _se("Bug", "Poison", 0.5)
_se("Bug", "Flying", 0.5); _se("Bug", "Ghost", 0.5); _se("Bug", "Steel", 0.5)

# Rock
_se("Rock", "Fire", 2.0); _se("Rock", "Ice", 2.0); _se("Rock", "Flying", 2.0)
_se("Rock", "Bug", 2.0); _se("Rock", "Fighting", 0.5); _se("Rock", "Ground", 0.5)
_se("Rock", "Steel", 0.5)

# Ghost
_se("Ghost", "Psychic", 2.0); _se("Ghost", "Ghost", 2.0)
_se("Ghost", "Dark", 0.5); _se("Ghost", "Steel", 0.5); _se("Ghost", "Normal", 0.0)

# Dragon
_se("Dragon", "Dragon", 2.0); _se("Dragon", "Steel", 0.5)

# Dark
_se("Dark", "Psychic", 2.0); _se("Dark", "Ghost", 2.0)
_se("Dark", "Fighting", 0.5); _se("Dark", "Dark", 0.5); _se("Dark", "Steel", 0.5)

# Steel
_se("Steel", "Ice", 2.0); _se("Steel", "Rock", 2.0)
_se("Steel", "Fire", 0.5); _se("Steel", "Water", 0.5); _se("Steel", "Electric", 0.5)
_se("Steel", "Steel", 0.5)

# Normal
_se("Normal", "Rock", 0.5); _se("Normal", "Steel", 0.5); _se("Normal", "Ghost", 0.0)


def type_effectiveness(atk_type: str, def_type: str) -> float:
    """Return the effectiveness multiplier for attacker type vs defender type."""
    ai = TYPE_INDEX.get(atk_type, -1)
    di = TYPE_INDEX.get(def_type, -1)
    if ai < 0 or di < 0:
        return 1.0
    return _CHART.get((ai, di), 1.0)


# ---------------------------------------------------------------------------
# Rough move -> type mapping for common Crystal moves
# (move_id -> type name)
# ---------------------------------------------------------------------------

MOVE_TYPE: Dict[int, str] = {
    # Normal
    1: "Normal", 3: "Normal", 4: "Normal", 5: "Normal",
    10: "Normal", 11: "Normal", 29: "Normal", 33: "Normal",
    34: "Normal", 36: "Normal", 38: "Normal", 45: "Normal",
    63: "Normal", 98: "Normal", 99: "Normal", 104: "Normal",
    117: "Normal", 129: "Normal", 156: "Normal", 173: "Normal",
    203: "Normal", 205: "Normal", 213: "Normal", 214: "Normal",
    216: "Normal", 218: "Normal", 245: "Normal",
    # Fire
    7: "Fire", 52: "Fire", 53: "Fire", 126: "Fire",
    172: "Fire", 221: "Fire",
    # Water
    55: "Water", 56: "Water", 57: "Water", 127: "Water", 250: "Water",
    # Electric
    9: "Electric", 84: "Electric", 85: "Electric",
    86: "Electric", 87: "Electric",
    # Grass
    22: "Grass", 72: "Grass", 76: "Grass", 202: "Grass",
    # Ice
    8: "Ice", 58: "Ice", 59: "Ice", 181: "Ice", 196: "Ice",
    # Fighting
    2: "Fighting", 6: "Normal", 12: "Normal",  # Guillotine is Normal
    183: "Fighting", 179: "Fighting",
    # Poison
    40: "Poison", 92: "Poison",
    # Ground
    89: "Ground", 91: "Ground", 189: "Ground",
    # Flying
    16: "Flying", 17: "Flying", 64: "Flying", 65: "Flying",
    143: "Flying", 177: "Flying", 239: "Dragon",
    # Psychic
    93: "Psychic", 94: "Psychic", 95: "Psychic", 100: "Psychic",
    # Bug
    210: "Bug",
    # Rock
    157: "Rock", 249: "Fighting",  # Rock Smash is Fighting
    # Ghost
    171: "Ghost", 247: "Ghost",
    # Dragon
    200: "Dragon",
    # Dark
    168: "Dark", 174: "Ghost",  # Curse is Ghost in Gen 2
    242: "Dark",
    # Steel
    231: "Steel",
    # Status / misc
    14: "Normal", 15: "Normal", 47: "Normal", 70: "Normal",
    105: "Normal", 110: "Water", 111: "Normal", 113: "Psychic",
    115: "Psychic", 116: "Normal", 135: "Normal", 182: "Normal",
    197: "Fighting", 237: "Normal", 240: "Water", 241: "Fire",
}


def get_move_type(move_id: int) -> str:
    """Return the type of a move, defaulting to Normal if unknown."""
    return MOVE_TYPE.get(move_id, "Normal")


# ---------------------------------------------------------------------------
# Rough species -> primary type mapping (common Gen 2 pokemon)
# ---------------------------------------------------------------------------

SPECIES_TYPE: Dict[int, str] = {
    # Gen 1
    1: "Grass", 2: "Grass", 3: "Grass",
    4: "Fire", 5: "Fire", 6: "Fire",
    7: "Water", 8: "Water", 9: "Water",
    10: "Bug", 11: "Bug", 12: "Bug",
    13: "Bug", 14: "Bug", 15: "Bug",
    16: "Normal", 17: "Normal", 18: "Normal",
    19: "Normal", 20: "Normal",
    21: "Normal", 22: "Normal",
    23: "Poison", 24: "Poison",
    25: "Electric", 26: "Electric",
    27: "Ground", 28: "Ground",
    35: "Normal", 36: "Normal",
    39: "Normal", 40: "Normal",
    41: "Poison", 42: "Poison",
    43: "Grass", 44: "Grass", 45: "Grass",
    46: "Bug", 47: "Bug",
    54: "Water", 55: "Water",
    56: "Fighting", 57: "Fighting",
    58: "Fire", 59: "Fire",
    60: "Water", 61: "Water", 62: "Water",
    63: "Psychic", 64: "Psychic", 65: "Psychic",
    66: "Fighting", 67: "Fighting", 68: "Fighting",
    69: "Grass", 70: "Grass", 71: "Grass",
    72: "Water", 73: "Water",
    74: "Rock", 75: "Rock", 76: "Rock",
    77: "Fire", 78: "Fire",
    79: "Water", 80: "Water",
    81: "Electric", 82: "Electric",
    92: "Ghost", 93: "Ghost", 94: "Ghost",
    95: "Rock",
    104: "Ground", 105: "Ground",
    111: "Ground", 112: "Ground",
    116: "Water", 117: "Water",
    118: "Water", 119: "Water",
    120: "Water", 121: "Water",
    123: "Bug", 124: "Ice",
    125: "Electric", 126: "Fire", 127: "Bug",
    129: "Water", 130: "Water",
    131: "Water",
    133: "Normal", 134: "Water", 135: "Electric", 136: "Fire",
    143: "Normal",
    144: "Ice", 145: "Electric", 146: "Fire",
    147: "Dragon", 148: "Dragon", 149: "Dragon",
    150: "Psychic", 151: "Psychic",
    # Gen 2
    152: "Grass", 153: "Grass", 154: "Grass",
    155: "Fire", 156: "Fire", 157: "Fire",
    158: "Water", 159: "Water", 160: "Water",
    161: "Normal", 162: "Normal",
    163: "Normal", 164: "Normal",
    165: "Bug", 166: "Bug",
    167: "Bug", 168: "Bug",
    169: "Poison",
    170: "Water", 171: "Water",
    172: "Electric", 173: "Normal", 174: "Normal",
    175: "Normal", 176: "Normal",
    177: "Psychic", 178: "Psychic",
    179: "Electric", 180: "Electric", 181: "Electric",
    183: "Water", 184: "Water",
    185: "Rock",
    187: "Grass", 188: "Grass", 189: "Grass",
    190: "Normal",
    194: "Water", 195: "Water",
    196: "Psychic", 197: "Dark",
    198: "Dark", 200: "Ghost",
    201: "Psychic", 202: "Psychic", 203: "Normal",
    204: "Bug", 205: "Bug",
    206: "Normal", 207: "Ground",
    208: "Steel",
    209: "Normal", 210: "Normal",
    212: "Bug", 214: "Bug",
    215: "Dark",
    216: "Normal", 217: "Normal",
    218: "Fire", 219: "Fire",
    220: "Ice", 221: "Ice",
    222: "Water", 223: "Water", 224: "Water",
    225: "Ice", 226: "Water", 227: "Steel",
    228: "Dark", 229: "Dark",
    230: "Water",
    231: "Ground", 232: "Ground",
    234: "Normal",
    236: "Fighting", 237: "Fighting",
    241: "Normal",
    243: "Electric", 244: "Fire", 245: "Water",
    246: "Rock", 247: "Rock", 248: "Rock",
    249: "Psychic", 250: "Fire", 251: "Psychic",
}


def get_species_type(species_id: int) -> str:
    """Return the primary type of a species, defaulting to Normal."""
    return SPECIES_TYPE.get(species_id, "Normal")


# ---------------------------------------------------------------------------
# Valid buttons (matching rom_emulator_bridge.py)
# ---------------------------------------------------------------------------

VALID_BUTTONS = ("A", "B", "UP", "DOWN", "LEFT", "RIGHT", "START")
DIRECTION_BUTTONS = ("UP", "DOWN", "LEFT", "RIGHT")

# Direction vectors for tile tracking
DIRECTION_DELTA: Dict[str, Tuple[int, int]] = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}


# ---------------------------------------------------------------------------
# Agent decision dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgentDecision:
    button: str
    reason: str
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# Agent stats tracking
# ---------------------------------------------------------------------------

@dataclass
class AgentStats:
    total_decisions: int = 0
    battle_decisions: int = 0
    heal_decisions: int = 0
    explore_decisions: int = 0
    tiles_visited: int = 0
    run_attempts: int = 0
    catch_attempts: int = 0

    def __str__(self) -> str:
        return (
            f"decisions={self.total_decisions} "
            f"(battle={self.battle_decisions}, heal={self.heal_decisions}, "
            f"explore={self.explore_decisions}) "
            f"tiles={self.tiles_visited} "
            f"runs={self.run_attempts} catches={self.catch_attempts}"
        )


# ---------------------------------------------------------------------------
# PokemonSmartAgent
# ---------------------------------------------------------------------------

class PokemonSmartAgent:
    """Game-aware AI agent for Pokemon Crystal.

    Reads PokemonState (or equivalent snapshot dict) and produces button
    decisions with reasoning.  Tracks visited tiles for exploration bias.
    """

    def __init__(
        self,
        heal_threshold: float = 0.3,
        explore_bias: float = 0.7,
        seed: int = 42,
    ) -> None:
        self.heal_threshold = heal_threshold
        self.explore_bias = explore_bias
        self.visited: Set[Tuple[int, int, int, int]] = set()  # (group, number, x, y)
        self._rng = random.Random(seed)
        self._stats = AgentStats()
        self._interact_counter = 0

    # -- public API -------------------------------------------------------

    def decide(
        self,
        state: Dict[str, Any],
        prev_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """Choose the next button press based on game state.

        Parameters
        ----------
        state : dict
            Snapshot dict from PokemonCrystalMemoryReader.read_snapshot()
            or PokemonState.to_snapshot_dict().
        prev_state : dict, optional
            Previous frame's snapshot for delta detection.

        Returns
        -------
        (button, reasoning) : tuple of str
        """
        self._stats.total_decisions += 1

        battle = state.get("battle", {})
        battle_mode = int(battle.get("mode", 0) or 0)

        # 1. In battle?
        if battle_mode > 0:
            return self._battle_action(state)

        # 2. Party needs healing?
        if self._party_needs_heal(state):
            return self._heal_navigate(state)

        # 3. Explore the world
        return self._explore(state)

    def choose(
        self,
        snapshot: Dict[str, Any],
        ocr_text: str = "",
    ) -> AgentDecision:
        """Backward-compatible interface returning an AgentDecision dataclass.

        The bridge's existing code calls agent.choose(snapshot, ocr_text).
        """
        # If there is OCR dialogue, press A to advance
        if ocr_text.strip():
            self._stats.total_decisions += 1
            return AgentDecision(
                button="A",
                reason="Dialogue detected via OCR; advance text safely.",
                confidence=0.93,
            )

        button, reason = self.decide(snapshot)
        # Estimate confidence heuristically
        battle_mode = int(snapshot.get("battle", {}).get("mode", 0) or 0)
        if battle_mode > 0:
            conf = 0.82
        elif self._party_needs_heal(snapshot):
            conf = 0.75
        else:
            conf = 0.68
        return AgentDecision(button=button, reason=reason, confidence=conf)

    def get_stats(self) -> AgentStats:
        """Return cumulative agent statistics."""
        self._stats.tiles_visited = len(self.visited)
        return self._stats

    # -- battle logic -----------------------------------------------------

    def _battle_action(self, state: Dict[str, Any]) -> Tuple[str, str]:
        """Decide an action during battle."""
        self._stats.battle_decisions += 1
        battle = state.get("battle", {})
        party = state.get("party", [])

        enemy_hp = int(battle.get("enemy_hp", 0) or 0)
        enemy_max_hp = int(battle.get("enemy_max_hp", 0) or 0)
        enemy_hp_ratio = (enemy_hp / max(1, enemy_max_hp))
        enemy_species = int(battle.get("enemy_species", 0) or 0)
        enemy_level = int(battle.get("enemy_level", 0) or 0)
        enemy_type = get_species_type(enemy_species)

        # Lead pokemon info
        lead = self._get_lead(party)
        lead_hp_ratio = self._mon_hp_ratio(lead) if lead else 0.0

        # If lead is critical, try to run
        if lead and lead_hp_ratio < 0.15:
            self._stats.run_attempts += 1
            # In Crystal battle menu: DOWN moves to Run, then A selects
            return ("DOWN", f"Lead {lead.get('species_name', '?')} HP critical "
                    f"({lead_hp_ratio:.0%}); attempt to flee.")

        # If enemy HP is very low, consider catching
        if enemy_hp_ratio > 0 and enemy_hp_ratio < 0.2 and enemy_level <= 20:
            self._stats.catch_attempts += 1
            # Navigate to BAG -> Poke Ball: RIGHT to move to BAG in menu
            return ("RIGHT", f"Wild {self._species_name(enemy_species)} "
                    f"(Lv.{enemy_level}) HP low ({enemy_hp_ratio:.0%}); "
                    f"attempt catch via Bag menu.")

        # Pick best move based on type effectiveness
        best_slot, best_reason = self._pick_best_move(lead, enemy_type)
        if best_slot >= 0:
            # Move selection: slot 0 = top-left (A), slot 1 = top-right (RIGHT+A)
            # slot 2 = bottom-left (DOWN+A), slot 3 = bottom-right (DOWN+RIGHT+A)
            # Simplification: press A to select FIGHT, then navigate to move slot
            if best_slot == 0:
                button = "A"
            elif best_slot == 1:
                button = "RIGHT"
            elif best_slot == 2:
                button = "DOWN"
            else:
                button = "DOWN"  # DOWN then RIGHT, but single-button simplification
            return (button, best_reason)

        # Fallback: press A to use first move
        return ("A", "Battle: using first available move (no type advantage computed).")

    def _pick_best_move(
        self,
        lead: Optional[Dict[str, Any]],
        enemy_type: str,
    ) -> Tuple[int, str]:
        """Return (move_slot_index, reasoning) for the best offensive move.

        Returns (-1, "") if no move data available.
        """
        if not lead:
            return (-1, "")

        moves = lead.get("moves", [])
        move_names = lead.get("move_names", [])
        if not moves:
            return (-1, "")

        best_idx = 0
        best_eff = 0.0
        best_name = move_names[0] if move_names else "?"

        for i, mid in enumerate(moves):
            if mid == 0:
                continue
            mtype = get_move_type(mid)
            eff = type_effectiveness(mtype, enemy_type)
            if eff > best_eff:
                best_eff = eff
                best_idx = i
                best_name = move_names[i] if i < len(move_names) else f"Move#{mid}"

        reason_parts = [f"Battle: selecting {best_name} (slot {best_idx + 1})"]
        if best_eff >= 2.0:
            reason_parts.append(f"super effective vs {enemy_type}")
        elif best_eff <= 0.5 and best_eff > 0:
            reason_parts.append(f"not very effective vs {enemy_type}, but best available")
        elif best_eff == 0.0:
            reason_parts.append(f"immune ({enemy_type}), but best available")
        else:
            reason_parts.append(f"neutral vs {enemy_type}")
        return (best_idx, "; ".join(reason_parts) + ".")

    # -- healing navigation -----------------------------------------------

    def _heal_navigate(self, state: Dict[str, Any]) -> Tuple[str, str]:
        """Navigate toward healing when party HP is low.

        Strategy: move around and press A to enter buildings (hoping for
        a Pokemon Center).  This is a simple heuristic.
        """
        self._stats.heal_decisions += 1
        map_data = state.get("map", {})
        x = int(map_data.get("x", 0) or 0)
        y = int(map_data.get("y", 0) or 0)

        # Alternate between movement and interaction
        self._interact_counter += 1
        if self._interact_counter % 5 == 0:
            return ("A", "Party HP low; pressing A to interact (seek Pokemon Center).")

        # Move toward map center-ish (heuristic: centers tend to have
        # Pokemon Centers in early-game towns)
        if y > 8:
            return ("UP", "Party HP low; moving UP to search for Pokemon Center.")
        if y < 4:
            return ("DOWN", "Party HP low; moving DOWN to search for Pokemon Center.")
        if x > 8:
            return ("LEFT", "Party HP low; moving LEFT to search for Pokemon Center.")
        return ("RIGHT", "Party HP low; moving RIGHT to search for Pokemon Center.")

    # -- exploration logic ------------------------------------------------

    def _explore(self, state: Dict[str, Any]) -> Tuple[str, str]:
        """Explore the overworld, preferring unvisited tiles."""
        self._stats.explore_decisions += 1
        map_data = state.get("map", {})
        x = int(map_data.get("x", 0) or 0)
        y = int(map_data.get("y", 0) or 0)
        group = int(map_data.get("group", 0) or 0)
        number = int(map_data.get("number", 0) or 0)

        current_tile = (group, number, x, y)
        self.visited.add(current_tile)

        # Periodically press A to interact with NPCs / pick up items
        self._interact_counter += 1
        if self._interact_counter % 8 == 0:
            return ("A", f"Exploration: periodic NPC/item interaction at ({x},{y}).")

        # Check which adjacent tiles are unvisited
        unvisited_dirs: List[str] = []
        visited_dirs: List[str] = []
        for direction, (dx, dy) in DIRECTION_DELTA.items():
            neighbor = (group, number, x + dx, y + dy)
            if neighbor not in self.visited:
                unvisited_dirs.append(direction)
            else:
                visited_dirs.append(direction)

        # Prefer unvisited tiles with explore_bias probability
        if unvisited_dirs and self._rng.random() < self.explore_bias:
            chosen = self._rng.choice(unvisited_dirs)
            return (chosen, f"Exploring unvisited tile {chosen} from ({x},{y}); "
                    f"{len(self.visited)} tiles visited so far.")

        # Fallback: random direction (including visited ones)
        all_dirs = unvisited_dirs + visited_dirs
        if not all_dirs:
            all_dirs = list(DIRECTION_BUTTONS)
        chosen = self._rng.choice(all_dirs)
        return (chosen, f"Exploration: moving {chosen} from ({x},{y}); "
                f"{len(self.visited)} tiles total.")

    # -- helpers ----------------------------------------------------------

    def _party_needs_heal(self, state: Dict[str, Any]) -> bool:
        """Return True if any party mon is below the heal threshold."""
        party = state.get("party", [])
        if not party:
            return False
        for mon in party:
            hp = int(mon.get("hp", 0) or 0)
            max_hp = max(1, int(mon.get("max_hp", 1) or 1))
            if hp / max_hp < self.heal_threshold:
                return True
        return False

    @staticmethod
    def _mon_hp_ratio(mon: Optional[Dict[str, Any]]) -> float:
        if not mon:
            return 1.0
        hp = int(mon.get("hp", 0) or 0)
        max_hp = max(1, int(mon.get("max_hp", 1) or 1))
        return hp / max_hp

    @staticmethod
    def _get_lead(party: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Return the first non-fainted party mon, or the first mon."""
        for mon in party:
            if int(mon.get("hp", 0) or 0) > 0:
                return mon
        return party[0] if party else None

    @staticmethod
    def _species_name(sid: int) -> str:
        from pokemon_memory import species_name as _sn
        return _sn(sid)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    agent = PokemonSmartAgent(seed=123)

    # Test 1: Dialogue via OCR
    dec = agent.choose(
        {"battle": {"mode": 0, "enemy_hp": 0}, "party": [], "map": {}},
        ocr_text="HELLO TRAINER",
    )
    assert dec.button == "A", f"Expected A for dialogue, got {dec.button}"

    # Test 2: Battle with low party HP -> retreat
    dec = agent.choose({
        "battle": {"mode": 1, "enemy_hp": 24, "enemy_max_hp": 30,
                   "enemy_species": 19, "enemy_level": 3},
        "party": [{"hp": 3, "max_hp": 80, "species_name": "Cyndaquil",
                   "moves": [33], "move_names": ["Tackle"]}],
        "map": {"x": 5, "y": 5, "group": 1, "number": 1},
    })
    assert dec.button == "DOWN", f"Expected DOWN (flee) for critical HP, got {dec.button}"

    # Test 3: Battle with good HP -> attack
    dec = agent.choose({
        "battle": {"mode": 1, "enemy_hp": 20, "enemy_max_hp": 30,
                   "enemy_species": 43, "enemy_level": 5},
        "party": [{"hp": 70, "max_hp": 80, "species_name": "Cyndaquil",
                   "moves": [52, 33, 0, 0], "move_names": ["Ember", "Tackle", "(none)", "(none)"]}],
        "map": {"x": 5, "y": 5, "group": 1, "number": 1},
    })
    # Ember is super effective vs Grass (Oddish) -> should pick slot 0 -> button A
    assert dec.button == "A", f"Expected A (Ember super effective vs Grass), got {dec.button}"

    # Test 4: Overworld exploration
    dec = agent.choose({
        "battle": {"mode": 0, "enemy_hp": 0, "enemy_max_hp": 0},
        "party": [{"hp": 70, "max_hp": 80}],
        "map": {"x": 3, "y": 4, "group": 2, "number": 1},
    })
    assert dec.button in VALID_BUTTONS, f"Invalid button: {dec.button}"

    # Test 5: decide() returns tuple
    btn, reason = agent.decide({
        "battle": {"mode": 0, "enemy_hp": 0},
        "party": [{"hp": 70, "max_hp": 80}],
        "map": {"x": 5, "y": 5, "group": 1, "number": 2},
    })
    assert btn in VALID_BUTTONS
    assert isinstance(reason, str) and len(reason) > 0

    # Test 6: Type effectiveness
    assert type_effectiveness("Fire", "Grass") == 2.0
    assert type_effectiveness("Water", "Fire") == 2.0
    assert type_effectiveness("Electric", "Ground") == 0.0
    assert type_effectiveness("Normal", "Ghost") == 0.0
    assert type_effectiveness("Normal", "Normal") == 1.0

    # Test 7: Stats tracking
    stats = agent.get_stats()
    assert stats.total_decisions >= 5
    assert stats.tiles_visited >= 0

    print("pokemon_ai_agent.py -- all tests PASSED")
    print(f"  Agent stats: {stats}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pokemon Crystal Smart AI Agent -- game-aware button decisions."
    )
    parser.add_argument("--test", action="store_true", help="Run agent tests.")
    parser.add_argument(
        "--snapshot-json", type=str, default="",
        help="Path to a snapshot JSON for a one-shot decision.",
    )
    parser.add_argument("--ocr", type=str, default="", help="Optional OCR text.")
    args = parser.parse_args()

    if args.test:
        _self_test()
        return 0

    if args.snapshot_json:
        with open(args.snapshot_json, "r", encoding="utf-8") as fh:
            snap = json.load(fh)
        dec = PokemonSmartAgent().choose(snap, args.ocr)
        print(json.dumps(asdict(dec), indent=2))
        return 0

    print("Pass --test or --snapshot-json <path>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
