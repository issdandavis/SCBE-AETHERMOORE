#!/usr/bin/env python3
"""Pokemon Crystal Conversation Data Generator -- Rich SFT pairs from gameplay.

Compares consecutive PokemonState snapshots to detect meaningful events
(battle won, level up, new map, badge earned, pokemon caught, heal, faint)
and generates rich prompt/response conversation pairs suitable for
supervised fine-tuning.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Map ID -> Map name lookup (~50 locations)
# ---------------------------------------------------------------------------

# Key: (map_group, map_number) -> display name
# These are approximate group/number pairs from the pokecrystal disassembly.
MAP_NAMES: Dict[tuple, str] = {
    # New Bark Town area
    (24, 1): "New Bark Town",
    (24, 2): "Player's House 1F",
    (24, 3): "Player's House 2F",
    (24, 4): "Elm's Lab",
    (24, 5): "Elm's House",
    # Route 29
    (25, 1): "Route 29",
    # Cherrygrove City
    (26, 1): "Cherrygrove City",
    (26, 2): "Cherrygrove Pokemon Center",
    (26, 3): "Cherrygrove Mart",
    (26, 4): "Cherrygrove Guide Gent's House",
    # Route 30
    (27, 1): "Route 30",
    (27, 2): "Mr. Pokemon's House",
    # Route 31
    (28, 1): "Route 31",
    (28, 2): "Dark Cave (Route 31)",
    # Violet City
    (9, 1): "Violet City",
    (9, 2): "Violet Pokemon Center",
    (9, 3): "Violet Mart",
    (9, 4): "Sprout Tower 1F",
    (9, 5): "Sprout Tower 2F",
    (9, 6): "Sprout Tower 3F",
    (9, 7): "Violet Gym",
    (9, 8): "Earl's Academy",
    # Route 32
    (10, 1): "Route 32",
    (10, 2): "Union Cave 1F",
    (10, 3): "Union Cave B1F",
    (10, 4): "Union Cave B2F",
    # Azalea Town
    (11, 1): "Azalea Town",
    (11, 2): "Azalea Pokemon Center",
    (11, 3): "Azalea Gym",
    (11, 4): "Kurt's House",
    (11, 5): "Slowpoke Well B1F",
    (11, 6): "Slowpoke Well B2F",
    # Ilex Forest
    (12, 1): "Ilex Forest",
    # Route 34
    (13, 1): "Route 34",
    (13, 2): "Day Care",
    # Goldenrod City
    (14, 1): "Goldenrod City",
    (14, 2): "Goldenrod Pokemon Center",
    (14, 3): "Goldenrod Mart 1F",
    (14, 4): "Goldenrod Gym",
    (14, 5): "Game Corner",
    (14, 6): "Radio Tower 1F",
    (14, 7): "Goldenrod Dept Store 1F",
    (14, 8): "Name Rater",
    (14, 9): "Underground",
    # Route 35 / National Park
    (15, 1): "Route 35",
    (15, 2): "National Park",
    (15, 3): "National Park Bug Contest",
    # Route 36-37
    (16, 1): "Route 36",
    (16, 2): "Route 37",
    # Ecruteak City
    (17, 1): "Ecruteak City",
    (17, 2): "Ecruteak Pokemon Center",
    (17, 3): "Ecruteak Gym",
    (17, 4): "Burned Tower 1F",
    (17, 5): "Burned Tower B1F",
    (17, 6): "Tin Tower 1F",
    (17, 7): "Dance Theatre",
    # Route 38-39
    (18, 1): "Route 38",
    (18, 2): "Route 39",
    (18, 3): "Moomoo Farm",
    # Olivine City
    (19, 1): "Olivine City",
    (19, 2): "Olivine Pokemon Center",
    (19, 3): "Olivine Gym",
    (19, 4): "Olivine Lighthouse 1F",
    # Route 40-41
    (20, 1): "Route 40",
    (20, 2): "Route 41",
    # Cianwood City
    (21, 1): "Cianwood City",
    (21, 2): "Cianwood Pokemon Center",
    (21, 3): "Cianwood Gym",
    (21, 4): "Cianwood Pharmacy",
    # Route 42
    (22, 1): "Route 42",
    # Mahogany Town
    (23, 1): "Mahogany Town",
    (23, 2): "Mahogany Pokemon Center",
    (23, 3): "Mahogany Gym",
    (23, 4): "Team Rocket HQ B1F",
    # Route 43 / Lake of Rage
    (29, 1): "Route 43",
    (29, 2): "Lake of Rage",
    # Route 44
    (30, 1): "Route 44",
    (30, 2): "Ice Path 1F",
    (30, 3): "Ice Path B1F",
    (30, 4): "Ice Path B2F",
    (30, 5): "Ice Path B3F",
    # Blackthorn City
    (31, 1): "Blackthorn City",
    (31, 2): "Blackthorn Pokemon Center",
    (31, 3): "Blackthorn Gym",
    (31, 4): "Dragon's Den 1F",
    (31, 5): "Dragon's Den B1F",
    # Route 45-46
    (32, 1): "Route 45",
    (32, 2): "Route 46",
    (32, 3): "Dark Cave (Route 46)",
    # Victory Road / Indigo Plateau
    (33, 1): "Route 26",
    (33, 2): "Route 27",
    (33, 3): "Victory Road",
    (33, 4): "Indigo Plateau",
    (33, 5): "Pokemon League",
    # Kanto cities (selected)
    (1, 1): "Pallet Town",
    (2, 1): "Viridian City",
    (3, 1): "Pewter City",
    (4, 1): "Cerulean City",
    (5, 1): "Lavender Town",
    (6, 1): "Vermilion City",
    (7, 1): "Celadon City",
    (8, 1): "Saffron City",
    (34, 1): "Fuchsia City",
    (35, 1): "Cinnabar Island",
    # Mt. Silver
    (36, 1): "Mt. Silver Exterior",
    (36, 2): "Mt. Silver Interior",
    (36, 3): "Mt. Silver Summit",
}


def map_name(group: int, number: int) -> str:
    """Look up the human-readable map name."""
    name = MAP_NAMES.get((group, number))
    if name:
        return name
    return f"Map ({group},{number})"


# ---------------------------------------------------------------------------
# Badge name lists (imported from pokemon_memory for convenience)
# ---------------------------------------------------------------------------

JOHTO_BADGES = [
    "Zephyr", "Hive", "Plain", "Fog",
    "Storm", "Mineral", "Glacier", "Rising",
]
KANTO_BADGES = [
    "Boulder", "Cascade", "Thunder", "Rainbow",
    "Soul", "Marsh", "Volcano", "Earth",
]


def _badge_names_from_bits(bits: int, names: List[str]) -> List[str]:
    return [n for i, n in enumerate(names) if bits & (1 << i)]


def _badge_count(bits: int) -> int:
    return int(bits & 0xFF).bit_count()


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

EVENT_BATTLE_WON = "BATTLE_WON"
EVENT_LEVEL_UP = "LEVEL_UP"
EVENT_NEW_MAP = "NEW_MAP"
EVENT_BADGE_EARNED = "BADGE_EARNED"
EVENT_POKEMON_CAUGHT = "POKEMON_CAUGHT"
EVENT_HEAL = "HEAL"
EVENT_MON_FAINTED = "MON_FAINTED"


# ---------------------------------------------------------------------------
# Species name helper (imported lazily to avoid circular import)
# ---------------------------------------------------------------------------

def _species_name(sid: int) -> str:
    try:
        from pokemon_memory import species_name
        return species_name(sid)
    except ImportError:
        return f"Pokemon#{sid}"


def _move_name(mid: int) -> str:
    try:
        from pokemon_memory import move_name
        return move_name(mid)
    except ImportError:
        return f"Move#{mid}"


# ---------------------------------------------------------------------------
# PokemonConversationGenerator
# ---------------------------------------------------------------------------

class PokemonConversationGenerator:
    """Detect gameplay events and generate rich SFT conversation pairs."""

    def __init__(self) -> None:
        self._prev_battle_enemy_hp: int = 0
        self._event_count: int = 0

    # -- event detection --------------------------------------------------

    def detect_events(
        self,
        prev_state: Dict[str, Any],
        curr_state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Compare two consecutive snapshots and return detected events.

        Each event is a dict with at least {"type": "EVENT_TYPE", ...metadata}.
        """
        events: List[Dict[str, Any]] = []

        prev_battle = prev_state.get("battle", {})
        curr_battle = curr_state.get("battle", {})
        prev_party = prev_state.get("party", [])
        curr_party = curr_state.get("party", [])
        prev_badges = prev_state.get("badges", {})
        curr_badges = curr_state.get("badges", {})
        prev_map = prev_state.get("map", {})
        curr_map = curr_state.get("map", {})

        prev_battle_mode = int(prev_battle.get("mode", 0) or 0)
        curr_battle_mode = int(curr_battle.get("mode", 0) or 0)
        prev_enemy_hp = int(prev_battle.get("enemy_hp", 0) or 0)
        curr_enemy_hp = int(curr_battle.get("enemy_hp", 0) or 0)

        # BATTLE_WON: was in battle, now not, and enemy had HP before
        if prev_battle_mode > 0 and curr_battle_mode == 0 and prev_enemy_hp > 0:
            events.append({
                "type": EVENT_BATTLE_WON,
                "enemy_species": int(prev_battle.get("enemy_species", 0) or 0),
                "enemy_species_name": _species_name(
                    int(prev_battle.get("enemy_species", 0) or 0)
                ),
                "enemy_level": int(prev_battle.get("enemy_level", 0) or 0),
            })

        # LEVEL_UP: any party mon level increased
        for i, curr_mon in enumerate(curr_party):
            if i < len(prev_party):
                prev_lvl = int(prev_party[i].get("level", 0) or 0)
                curr_lvl = int(curr_mon.get("level", 0) or 0)
                if curr_lvl > prev_lvl and curr_lvl > 0:
                    events.append({
                        "type": EVENT_LEVEL_UP,
                        "slot": i + 1,
                        "species": int(curr_mon.get("species", 0) or 0),
                        "species_name": curr_mon.get(
                            "species_name", _species_name(int(curr_mon.get("species", 0) or 0))
                        ),
                        "old_level": prev_lvl,
                        "new_level": curr_lvl,
                    })

        # NEW_MAP: map group or number changed
        prev_g = int(prev_map.get("group", 0) or 0)
        prev_n = int(prev_map.get("number", 0) or 0)
        curr_g = int(curr_map.get("group", 0) or 0)
        curr_n = int(curr_map.get("number", 0) or 0)
        if (prev_g, prev_n) != (curr_g, curr_n) and (curr_g > 0 or curr_n > 0):
            events.append({
                "type": EVENT_NEW_MAP,
                "prev_map": map_name(prev_g, prev_n),
                "curr_map": map_name(curr_g, curr_n),
                "map_group": curr_g,
                "map_number": curr_n,
            })

        # BADGE_EARNED: badge count increased
        prev_total = int(prev_badges.get("total", 0) or 0)
        curr_total = int(curr_badges.get("total", 0) or 0)
        if curr_total > prev_total:
            # Figure out which badge was earned
            prev_johto = int(prev_badges.get("johto_bits", 0) or 0)
            curr_johto = int(curr_badges.get("johto_bits", 0) or 0)
            prev_kanto = int(prev_badges.get("kanto_bits", 0) or 0)
            curr_kanto = int(curr_badges.get("kanto_bits", 0) or 0)
            new_johto = _badge_names_from_bits(curr_johto & ~prev_johto, JOHTO_BADGES)
            new_kanto = _badge_names_from_bits(curr_kanto & ~prev_kanto, KANTO_BADGES)
            earned = new_johto + new_kanto
            events.append({
                "type": EVENT_BADGE_EARNED,
                "badges_earned": earned,
                "total_badges": curr_total,
            })

        # POKEMON_CAUGHT: party count increased
        prev_count = int(prev_state.get("party_count", 0) or 0)
        curr_count = int(curr_state.get("party_count", 0) or 0)
        if curr_count > prev_count:
            # The newest mon is the last in the party list
            new_mon = curr_party[-1] if curr_party else {}
            events.append({
                "type": EVENT_POKEMON_CAUGHT,
                "species": int(new_mon.get("species", 0) or 0),
                "species_name": new_mon.get(
                    "species_name",
                    _species_name(int(new_mon.get("species", 0) or 0)),
                ),
                "level": int(new_mon.get("level", 0) or 0),
                "party_count": curr_count,
            })

        # HEAL: party HP restored (all mons at or near full HP now, but weren't before)
        if curr_party and prev_party:
            prev_total_hp = sum(int(m.get("hp", 0) or 0) for m in prev_party)
            prev_total_max = sum(max(1, int(m.get("max_hp", 1) or 1)) for m in prev_party)
            curr_total_hp = sum(int(m.get("hp", 0) or 0) for m in curr_party)
            curr_total_max = sum(max(1, int(m.get("max_hp", 1) or 1)) for m in curr_party)
            prev_ratio = prev_total_hp / max(1, prev_total_max)
            curr_ratio = curr_total_hp / max(1, curr_total_max)
            # Heal detected when ratio jumps significantly to near-full
            if curr_ratio >= 0.95 and prev_ratio < 0.7:
                events.append({
                    "type": EVENT_HEAL,
                    "prev_hp_ratio": round(prev_ratio, 3),
                    "curr_hp_ratio": round(curr_ratio, 3),
                    "location": map_name(curr_g, curr_n),
                })

        # MON_FAINTED: any party mon HP went to 0 (but wasn't 0 before)
        for i, curr_mon in enumerate(curr_party):
            if i < len(prev_party):
                prev_hp = int(prev_party[i].get("hp", 0) or 0)
                curr_hp = int(curr_mon.get("hp", 0) or 0)
                if prev_hp > 0 and curr_hp <= 0:
                    events.append({
                        "type": EVENT_MON_FAINTED,
                        "slot": i + 1,
                        "species": int(curr_mon.get("species", 0) or 0),
                        "species_name": curr_mon.get(
                            "species_name",
                            _species_name(int(curr_mon.get("species", 0) or 0)),
                        ),
                        "level": int(curr_mon.get("level", 0) or 0),
                    })

        return events

    # -- conversation pair generation -------------------------------------

    def generate_pairs(
        self,
        events: List[Dict[str, Any]],
        curr_state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate rich SFT conversation pairs from detected events.

        Returns a list of dicts with keys: prompt, response, event_type, metadata.
        """
        pairs: List[Dict[str, Any]] = []
        for event in events:
            pair = self._generate_one_pair(event, curr_state)
            if pair:
                self._event_count += 1
                pairs.append(pair)
        return pairs

    def _generate_one_pair(
        self,
        event: Dict[str, Any],
        curr_state: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        etype = event["type"]
        handler = {
            EVENT_BATTLE_WON: self._pair_battle_won,
            EVENT_LEVEL_UP: self._pair_level_up,
            EVENT_NEW_MAP: self._pair_new_map,
            EVENT_BADGE_EARNED: self._pair_badge_earned,
            EVENT_POKEMON_CAUGHT: self._pair_pokemon_caught,
            EVENT_HEAL: self._pair_heal,
            EVENT_MON_FAINTED: self._pair_mon_fainted,
        }.get(etype)
        if handler:
            return handler(event, curr_state)
        return None

    # -- individual pair generators ---------------------------------------

    def _pair_battle_won(
        self, event: Dict[str, Any], state: Dict[str, Any]
    ) -> Dict[str, Any]:
        enemy = event.get("enemy_species_name", "unknown")
        enemy_lvl = event.get("enemy_level", 0)
        lead = self._lead_mon(state)
        lead_name = lead.get("species_name", "your Pokemon") if lead else "your Pokemon"
        lead_lvl = lead.get("level", 0) if lead else 0
        lead_hp = lead.get("hp", 0) if lead else 0
        lead_max = lead.get("max_hp", 1) if lead else 1

        prompt = (
            f"Wild {enemy} (Lv.{enemy_lvl}) defeated! "
            f"Your {lead_name} (Lv.{lead_lvl}) has {lead_hp}/{lead_max} HP remaining. "
            f"What made this fight efficient?"
        )

        response_parts = [
            f"Battle analysis: {lead_name} successfully defeated the wild {enemy} (Lv.{enemy_lvl}).",
        ]
        hp_ratio = lead_hp / max(1, lead_max)
        if hp_ratio > 0.8:
            response_parts.append(
                "Excellent outcome -- minimal HP lost, indicating a strong level/type advantage."
            )
        elif hp_ratio > 0.5:
            response_parts.append(
                "Decent outcome with moderate HP loss. Consider using super-effective moves "
                "to end fights faster."
            )
        else:
            response_parts.append(
                "Significant HP loss this fight. The enemy may have had a type advantage "
                "or comparable level. Consider healing before the next encounter."
            )

        if lead and lead.get("moves"):
            move_list = ", ".join(
                lead.get("move_names", [str(m) for m in lead["moves"]])
            )
            response_parts.append(f"Current moveset: {move_list}.")

        return self._make_pair(
            prompt=prompt,
            response=" ".join(response_parts),
            event_type=EVENT_BATTLE_WON,
            metadata={
                "enemy_species": event.get("enemy_species", 0),
                "enemy_species_name": enemy,
                "enemy_level": enemy_lvl,
                "lead_species_name": lead_name,
                "lead_level": lead_lvl,
                "lead_hp_remaining": lead_hp,
                "lead_max_hp": lead_max,
            },
        )

    def _pair_level_up(
        self, event: Dict[str, Any], state: Dict[str, Any]
    ) -> Dict[str, Any]:
        name = event.get("species_name", "your Pokemon")
        old_lvl = event.get("old_level", 0)
        new_lvl = event.get("new_level", 0)
        slot = event.get("slot", 1)

        # Get current moves
        party = state.get("party", [])
        mon = party[slot - 1] if slot <= len(party) else {}
        moves = mon.get("move_names", [])

        prompt = (
            f"{name} grew to level {new_lvl}! "
            f"Current moves: {', '.join(moves) if moves else 'unknown'}. "
            f"What new moves should it learn?"
        )

        response_parts = [
            f"Congratulations! {name} advanced from Lv.{old_lvl} to Lv.{new_lvl}.",
        ]
        if new_lvl < 15:
            response_parts.append(
                "At this early stage, prioritize STAB (Same Type Attack Bonus) moves "
                "that match its type. Keep coverage for type disadvantages."
            )
        elif new_lvl < 30:
            response_parts.append(
                "Mid-game evolution territory. Watch for evolution opportunities and "
                "consider replacing weaker moves with higher base-power alternatives."
            )
        else:
            response_parts.append(
                "Late-game level -- strong moves become available. Prioritize moves "
                "with high base power and good type coverage for upcoming gym leaders."
            )

        if moves:
            response_parts.append(
                f"Current moveset ({', '.join(moves)}) should be evaluated against "
                f"upcoming challenges."
            )

        return self._make_pair(
            prompt=prompt,
            response=" ".join(response_parts),
            event_type=EVENT_LEVEL_UP,
            metadata={
                "species_name": name,
                "old_level": old_lvl,
                "new_level": new_lvl,
                "slot": slot,
                "current_moves": moves,
            },
        )

    def _pair_new_map(
        self, event: Dict[str, Any], state: Dict[str, Any]
    ) -> Dict[str, Any]:
        prev = event.get("prev_map", "unknown")
        curr = event.get("curr_map", "unknown")
        group = event.get("map_group", 0)
        number = event.get("map_number", 0)
        badges = state.get("badges", {})
        badge_total = int(badges.get("total", 0) or 0)

        prompt = (
            f"You entered {curr} (from {prev}). "
            f"You have {badge_total} badges. "
            f"What should you explore first?"
        )

        response_parts = [
            f"Welcome to {curr}!",
        ]

        # Location-specific advice
        if "Pokemon Center" in curr:
            response_parts.append(
                "This is a Pokemon Center. Heal your team, access the PC to manage "
                "your party/boxes, and save your game."
            )
        elif "Gym" in curr:
            response_parts.append(
                "This is a Gym! Prepare your team -- make sure you have type advantages "
                "against the Gym Leader. Heal up and stock potions before challenging."
            )
        elif "Tower" in curr or "Cave" in curr or "Forest" in curr:
            response_parts.append(
                "This is a dungeon area. Expect wild encounters and trainer battles. "
                "Stock up on healing items and consider bringing Repels if underlevel."
            )
        elif "Route" in curr:
            response_parts.append(
                "New route ahead. Look for trainers to battle for experience, "
                "items on the ground, and new Pokemon species to catch."
            )
        elif "City" in curr or "Town" in curr:
            response_parts.append(
                "New town/city! Explore buildings, talk to NPCs for items and hints, "
                "visit the Pokemon Center, and check for a Gym."
            )
        else:
            response_parts.append(
                "Explore the area thoroughly. Talk to NPCs, check for items, "
                "and battle any trainers you find."
            )

        return self._make_pair(
            prompt=prompt,
            response=" ".join(response_parts),
            event_type=EVENT_NEW_MAP,
            metadata={
                "prev_map": prev,
                "curr_map": curr,
                "map_group": group,
                "map_number": number,
                "total_badges": badge_total,
            },
        )

    def _pair_badge_earned(
        self, event: Dict[str, Any], state: Dict[str, Any]
    ) -> Dict[str, Any]:
        earned = event.get("badges_earned", [])
        total = event.get("total_badges", 0)
        badge_str = ", ".join(earned) if earned else "a new badge"

        prompt = (
            f"You earned the {badge_str} Badge! "
            f"Total badges: {total}/16. What does this unlock?"
        )

        response_parts = [
            f"Congratulations on earning the {badge_str} Badge!",
        ]

        # Badge-specific unlocks
        for badge in earned:
            if badge == "Zephyr":
                response_parts.append(
                    "The Zephyr Badge lets you use Flash outside of battle and "
                    "traded Pokemon up to Lv.20 obey you."
                )
            elif badge == "Hive":
                response_parts.append(
                    "The Hive Badge lets you use Cut outside of battle and "
                    "Pokemon up to Lv.30 obey you."
                )
            elif badge == "Plain":
                response_parts.append(
                    "The Plain Badge boosts Speed and unlocks Strength outside of battle."
                )
            elif badge == "Fog":
                response_parts.append(
                    "The Fog Badge lets you use Surf outside of battle. "
                    "The seas of Johto are now open!"
                )
            elif badge == "Storm":
                response_parts.append(
                    "The Storm Badge lets you use Fly outside of battle. "
                    "Fast travel is now available!"
                )
            elif badge == "Mineral":
                response_parts.append(
                    "The Mineral Badge boosts Defense and unlocks Whirlpool."
                )
            elif badge == "Glacier":
                response_parts.append(
                    "The Glacier Badge lets you use Waterfall outside of battle. "
                    "This is key for reaching Blackthorn City."
                )
            elif badge == "Rising":
                response_parts.append(
                    "The Rising Badge makes all Pokemon obey you! "
                    "You can now challenge the Elite Four at Indigo Plateau."
                )
            else:
                response_parts.append(f"The {badge} Badge advances your trainer rank.")

        if total == 8:
            response_parts.append(
                "With 8 Johto badges, the path to the Pokemon League is open! "
                "Head east from New Bark Town to Route 27."
            )
        elif total == 16:
            response_parts.append(
                "All 16 badges collected! Mt. Silver is now accessible. "
                "Red awaits at the summit -- the ultimate challenge."
            )

        return self._make_pair(
            prompt=prompt,
            response=" ".join(response_parts),
            event_type=EVENT_BADGE_EARNED,
            metadata={
                "badges_earned": earned,
                "total_badges": total,
            },
        )

    def _pair_pokemon_caught(
        self, event: Dict[str, Any], state: Dict[str, Any]
    ) -> Dict[str, Any]:
        name = event.get("species_name", "a new Pokemon")
        level = event.get("level", 0)
        count = event.get("party_count", 0)

        prompt = (
            f"You caught a {name} (Lv.{level})! "
            f"Party size: {count}/6. How does it fit your team?"
        )

        # Get current party types for composition analysis
        party = state.get("party", [])
        party_info = []
        for mon in party:
            sname = mon.get("species_name", "?")
            slvl = mon.get("level", 0)
            party_info.append(f"{sname} (Lv.{slvl})")

        response_parts = [
            f"Great catch! {name} (Lv.{level}) has been added to your team.",
        ]

        if count >= 6:
            response_parts.append(
                "Your party is now full. Future catches will be sent to the PC. "
                "Consider which Pokemon best covers your team's weaknesses."
            )
        else:
            response_parts.append(
                f"You have {count}/6 party slots filled. "
                f"There's room for more team members."
            )

        if party_info:
            response_parts.append(f"Current team: {', '.join(party_info)}.")

        response_parts.append(
            "Evaluate type coverage -- a balanced team covers each other's weaknesses. "
            "Train the new member to match your team's average level."
        )

        return self._make_pair(
            prompt=prompt,
            response=" ".join(response_parts),
            event_type=EVENT_POKEMON_CAUGHT,
            metadata={
                "species_name": name,
                "level": level,
                "party_count": count,
                "party": [m.get("species_name", "?") for m in party],
            },
        )

    def _pair_heal(
        self, event: Dict[str, Any], state: Dict[str, Any]
    ) -> Dict[str, Any]:
        prev_ratio = event.get("prev_hp_ratio", 0)
        curr_ratio = event.get("curr_hp_ratio", 1.0)
        location = event.get("location", "a Pokemon Center")

        prompt = (
            f"Your team was healed at {location}! "
            f"HP restored from {prev_ratio:.0%} to {curr_ratio:.0%}. "
            f"What's the plan going forward?"
        )

        party = state.get("party", [])
        response_parts = [
            f"Team fully healed at {location}.",
        ]

        if party:
            avg_level = sum(int(m.get("level", 0) or 0) for m in party) / len(party)
            response_parts.append(f"Average team level: {avg_level:.1f}.")

        badges_total = int(state.get("badges", {}).get("total", 0) or 0)
        response_parts.append(
            f"With {badges_total} badges, continue exploring and training. "
            "Stock up on items from the Mart before heading out."
        )

        return self._make_pair(
            prompt=prompt,
            response=" ".join(response_parts),
            event_type=EVENT_HEAL,
            metadata={
                "prev_hp_ratio": prev_ratio,
                "curr_hp_ratio": curr_ratio,
                "location": location,
            },
        )

    def _pair_mon_fainted(
        self, event: Dict[str, Any], state: Dict[str, Any]
    ) -> Dict[str, Any]:
        name = event.get("species_name", "your Pokemon")
        level = event.get("level", 0)
        slot = event.get("slot", 1)

        # Check how many are still alive
        party = state.get("party", [])
        alive = sum(1 for m in party if int(m.get("hp", 0) or 0) > 0)

        prompt = (
            f"Your {name} (Lv.{level}) fainted! "
            f"{alive}/{len(party)} Pokemon remaining. What should you do?"
        )

        response_parts = [
            f"{name} (Lv.{level}) has fainted.",
        ]

        if alive == 0:
            response_parts.append(
                "All your Pokemon have fainted! You'll black out and return to the "
                "last Pokemon Center, losing some money. Next time, use healing items "
                "earlier or run from dangerous encounters."
            )
        elif alive == 1:
            response_parts.append(
                "Only one Pokemon left! Head to the nearest Pokemon Center immediately. "
                "Avoid wild encounters by using Repel if available."
            )
        else:
            response_parts.append(
                f"{alive} Pokemon still able to fight. Consider using a Revive if available, "
                "or head to a Pokemon Center soon. Switch to a Pokemon with a type advantage "
                "for the current area."
            )

        return self._make_pair(
            prompt=prompt,
            response=" ".join(response_parts),
            event_type=EVENT_MON_FAINTED,
            metadata={
                "species_name": name,
                "level": level,
                "slot": slot,
                "alive_count": alive,
                "total_party": len(party),
            },
        )

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _lead_mon(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        party = state.get("party", [])
        for mon in party:
            if int(mon.get("hp", 0) or 0) > 0:
                return mon
        return party[0] if party else None

    @staticmethod
    def _make_pair(
        prompt: str,
        response: str,
        event_type: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "prompt": prompt,
            "response": response,
            "event_type": event_type,
            "metadata": metadata,
            "timestamp": time.time(),
        }


# ---------------------------------------------------------------------------
# build_pair() -- backward-compatible free function for the bridge
# ---------------------------------------------------------------------------

def build_prompt(
    rom_title: str,
    step: int,
    snapshot: Dict[str, Any],
    ocr_text: str,
) -> str:
    """Build a prompt string from a snapshot dict."""
    map_data = snapshot.get("map", {})
    battle = snapshot.get("battle", {})
    badges = snapshot.get("badges", {})

    parts = [
        f"[ROM_STATE] {rom_title} step={step}",
        f"Map: {map_name(map_data.get('group', 0), map_data.get('number', 0))} "
        f"({map_data.get('x', 0)},{map_data.get('y', 0)})",
        f"Battle: mode={battle.get('mode', 0)} enemy={_species_name(battle.get('enemy_species', 0))} "
        f"Lv.{battle.get('enemy_level', 0)} HP={battle.get('enemy_hp', 0)}",
        f"Party: {snapshot.get('party_count', 0)} mons | "
        f"Badges: {badges.get('total', 0)} | "
        f"Pokedex: {snapshot.get('pokedex_owned', 0)}",
    ]
    if ocr_text.strip():
        parts.append(f'OCR dialogue: "{ocr_text.strip()}"')
    parts.append("Decide the next high-value action and justify it briefly.")
    return "\n".join(parts)


def build_response(button: str, reason: str) -> str:
    """Build a response string from a button choice and reasoning."""
    return f"Action: press {button}. Reason: {reason}"


def build_pair(
    rom_title: str,
    step: int,
    snapshot: Dict[str, Any],
    button: str,
    reason: str,
    ocr_text: str = "",
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a single JSONL-compatible training pair from a smart agent decision.

    This is the primary interface used by rom_emulator_bridge.py.
    """
    metadata: Dict[str, Any] = {
        "source": "pokemon_rom_bridge_smart",
        "rom_title": rom_title,
        "step": step,
        "button": button,
        "ocr_text": ocr_text.strip(),
        "battle_mode": snapshot.get("battle", {}).get("mode", 0),
        "map_name": map_name(
            snapshot.get("map", {}).get("group", 0),
            snapshot.get("map", {}).get("number", 0),
        ),
    }
    if confidence is not None:
        metadata["confidence"] = float(confidence)
    return {
        "prompt": build_prompt(rom_title, step, snapshot, ocr_text),
        "response": build_response(button, reason),
        "event_type": "rom_smart_decision",
        "metadata": metadata,
        "timestamp": time.time(),
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    gen = PokemonConversationGenerator()

    # Simulate a battle won
    prev = {
        "battle": {"mode": 1, "enemy_species": 19, "enemy_hp": 5, "enemy_max_hp": 14, "enemy_level": 3},
        "party": [{"species": 155, "species_name": "Cyndaquil", "level": 7,
                    "hp": 20, "max_hp": 25, "moves": [33, 52], "move_names": ["Tackle", "Ember"]}],
        "badges": {"total": 0, "johto_bits": 0, "kanto_bits": 0},
        "map": {"group": 25, "number": 1, "x": 10, "y": 5},
        "party_count": 1,
    }
    curr = {
        "battle": {"mode": 0, "enemy_species": 0, "enemy_hp": 0, "enemy_max_hp": 0, "enemy_level": 0},
        "party": [{"species": 155, "species_name": "Cyndaquil", "level": 8,
                    "hp": 18, "max_hp": 28, "moves": [33, 52], "move_names": ["Tackle", "Ember"]}],
        "badges": {"total": 0, "johto_bits": 0, "kanta_bits": 0},
        "map": {"group": 25, "number": 1, "x": 10, "y": 5},
        "party_count": 1,
    }

    events = gen.detect_events(prev, curr)
    assert any(e["type"] == EVENT_BATTLE_WON for e in events), "Should detect BATTLE_WON"
    assert any(e["type"] == EVENT_LEVEL_UP for e in events), "Should detect LEVEL_UP"

    pairs = gen.generate_pairs(events, curr)
    assert len(pairs) >= 2, f"Expected >= 2 pairs, got {len(pairs)}"
    for p in pairs:
        assert "prompt" in p
        assert "response" in p
        assert "event_type" in p
        assert "metadata" in p
        assert len(p["prompt"]) > 10
        assert len(p["response"]) > 10

    # Test NEW_MAP
    prev2 = dict(prev)
    prev2["map"] = {"group": 24, "number": 1, "x": 5, "y": 3}
    prev2["battle"] = {"mode": 0, "enemy_species": 0, "enemy_hp": 0, "enemy_max_hp": 0, "enemy_level": 0}
    curr2 = dict(curr)
    curr2["map"] = {"group": 26, "number": 1, "x": 1, "y": 1}
    events2 = gen.detect_events(prev2, curr2)
    assert any(e["type"] == EVENT_NEW_MAP for e in events2), "Should detect NEW_MAP"
    map_event = [e for e in events2 if e["type"] == EVENT_NEW_MAP][0]
    assert "Cherrygrove" in map_event["curr_map"]

    # Test BADGE_EARNED
    prev3 = {"battle": {"mode": 0, "enemy_hp": 0, "enemy_max_hp": 0, "enemy_level": 0},
             "badges": {"total": 0, "johto_bits": 0, "kanto_bits": 0},
             "map": {"group": 9, "number": 7, "x": 3, "y": 3},
             "party": [{"hp": 20, "max_hp": 25, "level": 12}], "party_count": 1}
    curr3 = {"battle": {"mode": 0, "enemy_hp": 0, "enemy_max_hp": 0, "enemy_level": 0},
             "badges": {"total": 1, "johto_bits": 1, "kanto_bits": 0},
             "map": {"group": 9, "number": 7, "x": 3, "y": 3},
             "party": [{"hp": 20, "max_hp": 25, "level": 12}], "party_count": 1}
    events3 = gen.detect_events(prev3, curr3)
    assert any(e["type"] == EVENT_BADGE_EARNED for e in events3), "Should detect BADGE_EARNED"

    # Test build_pair compat
    pair = build_pair("POKEMON CRYS", 100, curr, "A", "test reason", "", 0.9)
    assert pair["prompt"].startswith("[ROM_STATE]")
    assert "press A" in pair["response"]

    # Test map_name
    assert map_name(24, 1) == "New Bark Town"
    assert map_name(9, 7) == "Violet Gym"
    assert "99" in map_name(99, 99)  # fallback format: "Map (99,99)"

    print("pokemon_data_gen.py -- all tests PASSED")
    print(f"  Generated {len(pairs)} pairs from battle-won + level-up scenario")
    print(f"  Sample pair prompt: {pairs[0]['prompt'][:80]}...")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pokemon Crystal Conversation Data Generator -- generate SFT pairs from gameplay."
    )
    parser.add_argument("--test", action="store_true", help="Run self-tests.")
    parser.add_argument(
        "--snapshot-json", type=str, default="",
        help="Path to a snapshot JSON for building a single pair.",
    )
    parser.add_argument("--rom-title", type=str, default="POKEMON CRYS")
    parser.add_argument("--step", type=int, default=0)
    parser.add_argument("--button", type=str, default="A")
    parser.add_argument("--reason", type=str, default="")
    parser.add_argument("--ocr", type=str, default="")
    args = parser.parse_args()

    if args.test:
        _self_test()
        return 0

    if args.snapshot_json:
        with open(args.snapshot_json, "r", encoding="utf-8") as fh:
            snap = json.load(fh)
        row = build_pair(
            rom_title=args.rom_title,
            step=args.step,
            snapshot=snap,
            button=args.button,
            reason=args.reason,
            ocr_text=args.ocr,
        )
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0

    print("Pass --test or --snapshot-json <path>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
