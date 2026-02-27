#!/usr/bin/env python3
"""Pokemon Crystal Memory Reader -- Extract game state from PyBoy RAM.

Uses well-known memory addresses from the pokecrystal disassembly project
to read live game state (party, map, badges, battle info, money) from a
running PyBoy emulator instance.

Legal ROM workflow only. This module does NOT ship any copyrighted data.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# ROM helpers (kept from the original for backward compat)
# ---------------------------------------------------------------------------

def _safe_import_pyboy() -> Tuple[Any, Any]:
    try:
        from pyboy import PyBoy  # type: ignore
        from pyboy.utils import WindowEvent  # type: ignore
        return PyBoy, WindowEvent
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "PyBoy is required. Install: pip install pyboy"
        ) from exc


def infer_rom_system(rom_path: Path) -> str:
    ext = rom_path.suffix.lower()
    if ext == ".gb":
        return "gb"
    if ext == ".gbc":
        return "gbc"
    if ext == ".gba":
        return "gba"
    return "unknown"


def read_rom_title(rom_path: Path, system: str) -> str:
    try:
        blob = rom_path.read_bytes()
        if system in {"gb", "gbc"} and len(blob) > 0x143:
            raw = blob[0x134:0x144]
            title = raw.split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
            return title or rom_path.stem
    except OSError:
        pass
    return rom_path.stem


# ---------------------------------------------------------------------------
# Memory address map (from pokecrystal disassembly)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CrystalMemoryAddresses:
    """Well-known RAM addresses for Pokemon Crystal (US)."""

    # Player identity
    player_name: int = 0xD47D

    # Currency (3-byte BCD)
    money_bcd_3: int = 0xD84E

    # Badges (bitfields)
    johto_badges: int = 0xD857
    kanto_badges: int = 0xD858

    # Overworld position
    map_group: int = 0xDCB5
    map_number: int = 0xDCB6
    y_coord: int = 0xDCB7
    x_coord: int = 0xDCB8

    # Party structure
    party_count: int = 0xDCD7
    party_species: int = 0xDCD8
    party_mons: int = 0xDCDF
    party_mon_stride: int = 48

    # Offsets within a single party-mon struct
    mon_species_offset: int = 0x00
    mon_moves_offset: int = 0x02
    mon_level_offset: int = 0x1F
    mon_status_offset: int = 0x20
    mon_hp_offset: int = 0x22
    mon_max_hp_offset: int = 0x24

    # Battle state
    battle_mode: int = 0xD22D
    enemy_species: int = 0xD206
    enemy_level: int = 0xD213
    enemy_hp: int = 0xD214
    enemy_max_hp: int = 0xD218

    # Pokedex owned bitfield (32 bytes for 251 mons)
    pokedex_owned_start: int = 0xDE99
    pokedex_owned_len: int = 32


# Backward-compat alias used by existing bridge code
CrystalProfile = CrystalMemoryAddresses


# ---------------------------------------------------------------------------
# Species ID -> Name lookup (Gen 2, common species)
# ---------------------------------------------------------------------------

SPECIES_NAMES: Dict[int, str] = {
    1: "Bulbasaur", 2: "Ivysaur", 3: "Venusaur",
    4: "Charmander", 5: "Charmeleon", 6: "Charizard",
    7: "Squirtle", 8: "Wartortle", 9: "Blastoise",
    10: "Caterpie", 11: "Metapod", 12: "Butterfree",
    13: "Weedle", 14: "Kakuna", 15: "Beedrill",
    16: "Pidgey", 17: "Pidgeotto", 18: "Pidgeot",
    19: "Rattata", 20: "Raticate",
    21: "Spearow", 22: "Fearow",
    23: "Ekans", 24: "Arbok",
    25: "Pikachu", 26: "Raichu",
    27: "Sandshrew", 28: "Sandslash",
    35: "Clefairy", 36: "Clefable",
    39: "Jigglypuff", 40: "Wigglytuff",
    41: "Zubat", 42: "Golbat",
    43: "Oddish", 44: "Gloom", 45: "Vileplume",
    46: "Paras", 47: "Parasect",
    54: "Psyduck", 55: "Golduck",
    56: "Mankey", 57: "Primeape",
    58: "Growlithe", 59: "Arcanine",
    60: "Poliwag", 61: "Poliwhirl", 62: "Poliwrath",
    63: "Abra", 64: "Kadabra", 65: "Alakazam",
    66: "Machop", 67: "Machoke", 68: "Machamp",
    69: "Bellsprout", 70: "Weepinbell", 71: "Victreebel",
    72: "Tentacool", 73: "Tentacruel",
    74: "Geodude", 75: "Graveler", 76: "Golem",
    77: "Ponyta", 78: "Rapidash",
    79: "Slowpoke", 80: "Slowbro",
    81: "Magnemite", 82: "Magneton",
    92: "Gastly", 93: "Haunter", 94: "Gengar",
    95: "Onix",
    104: "Cubone", 105: "Marowak",
    111: "Rhyhorn", 112: "Rhydon",
    116: "Horsea", 117: "Seadra",
    118: "Goldeen", 119: "Seaking",
    120: "Staryu", 121: "Starmie",
    123: "Scyther", 124: "Jynx",
    125: "Electabuzz", 126: "Magmar", 127: "Pinsir",
    129: "Magikarp", 130: "Gyarados",
    131: "Lapras",
    133: "Eevee", 134: "Vaporeon", 135: "Jolteon", 136: "Flareon",
    143: "Snorlax",
    144: "Articuno", 145: "Zapdos", 146: "Moltres",
    147: "Dratini", 148: "Dragonair", 149: "Dragonite",
    150: "Mewtwo", 151: "Mew",
    152: "Chikorita", 153: "Bayleef", 154: "Meganium",
    155: "Cyndaquil", 156: "Quilava", 157: "Typhlosion",
    158: "Totodile", 159: "Croconaw", 160: "Feraligatr",
    161: "Sentret", 162: "Furret",
    163: "Hoothoot", 164: "Noctowl",
    165: "Ledyba", 166: "Ledian",
    167: "Spinarak", 168: "Ariados",
    169: "Crobat",
    170: "Chinchou", 171: "Lanturn",
    172: "Pichu", 173: "Cleffa", 174: "Igglybuff",
    175: "Togepi", 176: "Togetic",
    177: "Natu", 178: "Xatu",
    179: "Mareep", 180: "Flaaffy", 181: "Ampharos",
    183: "Marill", 184: "Azumarill",
    185: "Sudowoodo",
    187: "Hoppip", 188: "Skiploom", 189: "Jumpluff",
    190: "Aipom",
    194: "Wooper", 195: "Quagsire",
    196: "Espeon", 197: "Umbreon",
    198: "Murkrow", 200: "Misdreavus",
    201: "Unown", 202: "Wobbuffet", 203: "Girafarig",
    204: "Pineco", 205: "Forretress",
    206: "Dunsparce", 207: "Gligar",
    208: "Steelix",
    209: "Snubbull", 210: "Granbull",
    212: "Scizor", 214: "Heracross", 215: "Sneasel",
    216: "Teddiursa", 217: "Ursaring",
    218: "Slugma", 219: "Magcargo",
    220: "Swinub", 221: "Piloswine",
    222: "Corsola",
    223: "Remoraid", 224: "Octillery",
    225: "Delibird", 226: "Mantine", 227: "Skarmory",
    228: "Houndour", 229: "Houndoom",
    230: "Kingdra",
    231: "Phanpy", 232: "Donphan",
    234: "Stantler",
    236: "Tyrogue", 237: "Hitmontop",
    241: "Miltank",
    243: "Raikou", 244: "Entei", 245: "Suicune",
    246: "Larvitar", 247: "Pupitar", 248: "Tyranitar",
    249: "Lugia", 250: "Ho-Oh", 251: "Celebi",
}


def species_name(species_id: int) -> str:
    return SPECIES_NAMES.get(species_id, f"Pokemon#{species_id}")


# ---------------------------------------------------------------------------
# Move ID -> Name lookup (common moves)
# ---------------------------------------------------------------------------

MOVE_NAMES: Dict[int, str] = {
    0: "(none)",
    1: "Pound", 2: "Karate Chop", 3: "Double Slap",
    5: "Mega Punch", 7: "Fire Punch", 8: "Ice Punch",
    9: "Thunder Punch", 10: "Scratch", 13: "Razor Wind",
    14: "Swords Dance", 15: "Cut", 16: "Gust", 17: "Wing Attack",
    22: "Vine Whip", 29: "Headbutt",
    33: "Tackle", 34: "Body Slam", 36: "Take Down", 38: "Double-Edge",
    40: "Poison Sting", 45: "Growl", 47: "Sing",
    52: "Ember", 53: "Flamethrower", 55: "Water Gun",
    56: "Hydro Pump", 57: "Surf", 58: "Ice Beam", 59: "Blizzard",
    63: "Hyper Beam", 64: "Peck", 65: "Drill Peck",
    70: "Strength", 72: "Mega Drain", 76: "Solar Beam",
    84: "Thunder Shock", 85: "Thunderbolt", 86: "Thunder Wave",
    87: "Thunder", 89: "Earthquake", 91: "Dig",
    92: "Toxic", 93: "Confusion", 94: "Psychic", 95: "Hypnosis",
    98: "Quick Attack", 100: "Teleport", 104: "Double Team",
    105: "Recover", 126: "Fire Blast", 127: "Waterfall",
    129: "Swift", 156: "Rest", 157: "Rock Slide",
    168: "Thief", 172: "Flame Wheel", 174: "Curse",
    177: "Aeroblast", 181: "Powder Snow", 182: "Protect",
    183: "Mach Punch", 189: "Mud-Slap", 196: "Icy Wind",
    200: "Outrage", 202: "Giga Drain", 205: "Rollout",
    210: "Fury Cutter", 214: "Sleep Talk", 216: "Return",
    221: "Sacred Fire", 231: "Iron Tail", 237: "Hidden Power",
    240: "Rain Dance", 241: "Sunny Day", 242: "Crunch",
    245: "Extreme Speed", 247: "Shadow Ball", 249: "Rock Smash",
    250: "Whirlpool",
}


def move_name(move_id: int) -> str:
    return MOVE_NAMES.get(move_id, f"Move#{move_id}")


# ---------------------------------------------------------------------------
# Badge lists
# ---------------------------------------------------------------------------

JOHTO_BADGES: List[str] = [
    "Zephyr", "Hive", "Plain", "Fog",
    "Storm", "Mineral", "Glacier", "Rising",
]

KANTO_BADGES: List[str] = [
    "Boulder", "Cascade", "Thunder", "Rainbow",
    "Soul", "Marsh", "Volcano", "Earth",
]


def decode_badge_names(bitfield: int, badge_names: List[str]) -> List[str]:
    return [name for i, name in enumerate(badge_names) if bitfield & (1 << i)]


# ---------------------------------------------------------------------------
# BCD money decoder
# ---------------------------------------------------------------------------

def decode_bcd(raw: bytes) -> int:
    total = 0
    for b in raw:
        hi = (b >> 4) & 0x0F
        lo = b & 0x0F
        total = total * 100 + hi * 10 + lo
    return total


decode_bcd_money = decode_bcd
decode_bcd_3byte = decode_bcd  # backward compat alias


def bit_count(value: int) -> int:
    return int(value & 0xFF).bit_count()


# ---------------------------------------------------------------------------
# Gen 2 text decoder
# ---------------------------------------------------------------------------

def decode_gs_text(raw: bytes) -> str:
    mapped: List[str] = []
    for b in raw:
        if b in (0x00, 0x50):
            break
        if 0x80 <= b <= 0x99:
            mapped.append(chr(ord("A") + (b - 0x80)))
        elif 0xA0 <= b <= 0xB9:
            mapped.append(chr(ord("a") + (b - 0xA0)))
        elif 0xF6 <= b <= 0xFF:
            digit = b - 0xF6
            mapped.append(str(digit) if 0 <= digit <= 9 else "?")
        elif b == 0x7F:
            mapped.append(" ")
        else:
            mapped.append("?")
    return "".join(mapped).strip() or "(unknown)"


# ---------------------------------------------------------------------------
# Dataclasses for structured game state
# ---------------------------------------------------------------------------

@dataclass
class PartyMon:
    """A single party pokemon's vital stats."""
    species_id: int
    species_name: str
    level: int
    hp: int
    max_hp: int
    moves: List[int]
    move_names: List[str]
    status: int

    @property
    def hp_ratio(self) -> float:
        return self.hp / max(1, self.max_hp)

    @property
    def is_fainted(self) -> bool:
        return self.hp <= 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "species_id": self.species_id,
            "species_name": self.species_name,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "hp_ratio": round(self.hp_ratio, 3),
            "moves": self.moves,
            "move_names": self.move_names,
            "status": self.status,
            "is_fainted": self.is_fainted,
        }


@dataclass
class PokemonState:
    """Full game state snapshot from Pokemon Crystal RAM."""
    player_name: str
    party_count: int
    party: List[PartyMon]
    map_group: int
    map_number: int
    player_x: int
    player_y: int
    johto_badges: int
    kanto_badges: int
    johto_badge_names: List[str]
    kanto_badge_names: List[str]
    johto_badge_count: int
    kanto_badge_count: int
    money: int
    in_battle: bool
    enemy_species: int
    enemy_species_name: str
    enemy_level: int
    enemy_hp: int
    enemy_max_hp: int
    pokedex_owned: int
    timestamp: float = field(default_factory=time.time)

    @property
    def total_badges(self) -> int:
        return self.johto_badge_count + self.kanto_badge_count

    @property
    def party_hp_ratio(self) -> float:
        if not self.party:
            return 1.0
        total_hp = sum(m.hp for m in self.party)
        total_max = sum(m.max_hp for m in self.party)
        return total_hp / max(1, total_max)

    @property
    def enemy_hp_ratio(self) -> float:
        if self.enemy_max_hp <= 0:
            return 0.0
        return self.enemy_hp / self.enemy_max_hp

    def lead_mon(self) -> Optional[PartyMon]:
        for mon in self.party:
            if not mon.is_fainted:
                return mon
        return self.party[0] if self.party else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "player_name": self.player_name,
            "party_count": self.party_count,
            "party": [m.to_dict() for m in self.party],
            "party_hp_ratio": round(self.party_hp_ratio, 3),
            "map": {"group": self.map_group, "number": self.map_number,
                     "x": self.player_x, "y": self.player_y},
            "johto_badges": self.johto_badge_names,
            "kanto_badges": self.kanto_badge_names,
            "total_badges": self.total_badges,
            "money": self.money,
            "in_battle": self.in_battle,
            "pokedex_owned": self.pokedex_owned,
        }

    def to_snapshot_dict(self) -> Dict[str, Any]:
        """Backward-compatible dict for bridge/agent code."""
        return {
            "timestamp": self.timestamp,
            "player_name": self.player_name,
            "money": self.money,
            "badges": {
                "johto_bits": self.johto_badges,
                "kanto_bits": self.kanto_badges,
                "johto_count": self.johto_badge_count,
                "kanto_count": self.kanto_badge_count,
                "total": self.total_badges,
            },
            "map": {
                "group": self.map_group,
                "number": self.map_number,
                "x": self.player_x,
                "y": self.player_y,
            },
            "party_count": self.party_count,
            "party": [
                {
                    "slot": i + 1,
                    "species": m.species_id,
                    "species_name": m.species_name,
                    "level": m.level,
                    "hp": m.hp,
                    "max_hp": m.max_hp,
                    "moves": m.moves,
                    "move_names": m.move_names,
                    "status": m.status,
                }
                for i, m in enumerate(self.party)
            ],
            "battle": {
                "mode": 1 if self.in_battle else 0,
                "enemy_species": self.enemy_species,
                "enemy_species_name": self.enemy_species_name,
                "enemy_level": self.enemy_level,
                "enemy_hp": self.enemy_hp,
                "enemy_max_hp": self.enemy_max_hp,
                "enemy_hp_ratio": round(self.enemy_hp_ratio, 3),
            },
            "pokedex_owned": self.pokedex_owned,
        }


# ---------------------------------------------------------------------------
# Memory reader class
# ---------------------------------------------------------------------------

class PokemonCrystalMemoryReader:
    """Read Pokemon Crystal game state from a PyBoy emulator instance."""

    def __init__(
        self,
        memory_accessor: Any,
        addresses: Optional[CrystalMemoryAddresses] = None,
    ) -> None:
        self.mem = memory_accessor
        self.addr = addresses or CrystalMemoryAddresses()

    @classmethod
    def from_pyboy(
        cls,
        pyboy: Any,
        addresses: Optional[CrystalMemoryAddresses] = None,
    ) -> "PokemonCrystalMemoryReader":
        return cls(pyboy, addresses)

    def _read_u8(self, address: int) -> int:
        if hasattr(self.mem, "get_memory_value"):
            return int(self.mem.get_memory_value(address)) & 0xFF
        if hasattr(self.mem, "memory"):
            return int(self.mem.memory[address]) & 0xFF
        raise AttributeError(
            "memory accessor must expose get_memory_value(addr) or memory[addr]"
        )

    def _read_u16_be(self, address: int) -> int:
        return (self._read_u8(address) << 8) | self._read_u8(address + 1)

    def _read_bytes(self, address: int, length: int) -> bytes:
        return bytes(self._read_u8(address + i) for i in range(length))

    def read_party(self) -> List[PartyMon]:
        count = min(max(self._read_u8(self.addr.party_count), 0), 6)
        party: List[PartyMon] = []
        for i in range(count):
            base = self.addr.party_mons + i * self.addr.party_mon_stride
            sid = self._read_u8(base + self.addr.mon_species_offset)
            level = self._read_u8(base + self.addr.mon_level_offset)
            hp = self._read_u16_be(base + self.addr.mon_hp_offset)
            max_hp = self._read_u16_be(base + self.addr.mon_max_hp_offset)
            moves = [
                self._read_u8(base + self.addr.mon_moves_offset + j)
                for j in range(4)
            ]
            status = self._read_u8(base + self.addr.mon_status_offset)
            party.append(PartyMon(
                species_id=sid,
                species_name=species_name(sid),
                level=level, hp=hp, max_hp=max_hp,
                moves=moves,
                move_names=[move_name(m) for m in moves],
                status=status,
            ))
        return party

    def read_badges(self) -> Tuple[int, int]:
        johto = self._read_u8(self.addr.johto_badges)
        kanto = self._read_u8(self.addr.kanto_badges)
        return johto, kanto

    def read_money(self) -> int:
        return decode_bcd(self._read_bytes(self.addr.money_bcd_3, 3))

    def read_pokedex_owned(self) -> int:
        buf = self._read_bytes(
            self.addr.pokedex_owned_start, self.addr.pokedex_owned_len
        )
        return sum(bit_count(b) for b in buf)

    def read_pokemon_state(self) -> PokemonState:
        party = self.read_party()
        johto_bits, kanto_bits = self.read_badges()
        battle_mode = self._read_u8(self.addr.battle_mode)
        enemy_sid = self._read_u8(self.addr.enemy_species)
        enemy_lvl = self._read_u8(self.addr.enemy_level)
        enemy_hp = self._read_u16_be(self.addr.enemy_hp)
        enemy_max_hp = self._read_u16_be(self.addr.enemy_max_hp)

        return PokemonState(
            player_name=decode_gs_text(self._read_bytes(self.addr.player_name, 11)),
            party_count=len(party),
            party=party,
            map_group=self._read_u8(self.addr.map_group),
            map_number=self._read_u8(self.addr.map_number),
            player_x=self._read_u8(self.addr.x_coord),
            player_y=self._read_u8(self.addr.y_coord),
            johto_badges=johto_bits,
            kanto_badges=kanto_bits,
            johto_badge_names=decode_badge_names(johto_bits, JOHTO_BADGES),
            kanto_badge_names=decode_badge_names(kanto_bits, KANTO_BADGES),
            johto_badge_count=bit_count(johto_bits),
            kanto_badge_count=bit_count(kanto_bits),
            money=self.read_money(),
            in_battle=battle_mode != 0,
            enemy_species=enemy_sid,
            enemy_species_name=species_name(enemy_sid),
            enemy_level=enemy_lvl,
            enemy_hp=enemy_hp,
            enemy_max_hp=enemy_max_hp,
            pokedex_owned=self.read_pokedex_owned(),
        )

    def read_snapshot(self) -> Dict[str, Any]:
        """Backward-compatible dict snapshot for bridge/agent."""
        state = self.read_pokemon_state()
        return state.to_snapshot_dict()

    @staticmethod
    def compact_key(snapshot: Dict[str, Any]) -> str:
        """Compact key for dedup (backward compat)."""
        m = snapshot.get("map", {})
        b = snapshot.get("badges", {})
        key = {
            "mg": m.get("group", 0),
            "mn": m.get("number", 0),
            "x": m.get("x", 0),
            "y": m.get("y", 0),
            "pc": snapshot.get("party_count", 0),
            "money": snapshot.get("money", 0),
            "badges": b.get("total", 0),
        }
        return json.dumps(key, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Convenience free function
# ---------------------------------------------------------------------------

def read_pokemon_state(pyboy: Any) -> PokemonState:
    """Read the full PokemonState from a live PyBoy instance."""
    reader = PokemonCrystalMemoryReader.from_pyboy(pyboy)
    return reader.read_pokemon_state()


# ---------------------------------------------------------------------------
# Self-test with mock memory
# ---------------------------------------------------------------------------

def _self_test() -> None:
    addr = CrystalMemoryAddresses()

    # BCD decoder
    assert decode_bcd(bytes([0x12, 0x34, 0x56])) == 123456
    assert decode_bcd(bytes([0x00, 0x00, 0x00])) == 0

    # Bit count
    assert bit_count(0xFF) == 8
    assert bit_count(0x00) == 0

    # Text decoder
    assert decode_gs_text(bytes([0x80, 0x81, 0x82, 0x50])) == "ABC"

    # Badge decoder
    assert decode_badge_names(0b00000001, JOHTO_BADGES) == ["Zephyr"]
    assert decode_badge_names(0xFF, KANTO_BADGES) == KANTO_BADGES

    # Species / move lookups
    assert species_name(25) == "Pikachu"
    assert move_name(85) == "Thunderbolt"

    # Build fake memory and read a PokemonState
    fake: Dict[int, int] = {}

    def _set_u16_be(base: int, val: int) -> None:
        fake[base] = (val >> 8) & 0xFF
        fake[base + 1] = val & 0xFF

    fake[addr.player_name] = 0x80
    fake[addr.player_name + 1] = 0x81
    fake[addr.player_name + 2] = 0x50
    fake[addr.money_bcd_3] = 0x00
    fake[addr.money_bcd_3 + 1] = 0x12
    fake[addr.money_bcd_3 + 2] = 0x34
    fake[addr.johto_badges] = 0x03
    fake[addr.kanto_badges] = 0x00
    fake[addr.map_group] = 3
    fake[addr.map_number] = 2
    fake[addr.x_coord] = 10
    fake[addr.y_coord] = 5
    fake[addr.party_count] = 1
    fake[addr.party_species] = 155
    base0 = addr.party_mons
    fake[base0 + addr.mon_species_offset] = 155
    fake[base0 + addr.mon_moves_offset] = 33
    fake[base0 + addr.mon_moves_offset + 1] = 52
    fake[base0 + addr.mon_moves_offset + 2] = 0
    fake[base0 + addr.mon_moves_offset + 3] = 0
    fake[base0 + addr.mon_level_offset] = 8
    fake[base0 + addr.mon_status_offset] = 0
    _set_u16_be(base0 + addr.mon_hp_offset, 25)
    _set_u16_be(base0 + addr.mon_max_hp_offset, 30)
    fake[addr.battle_mode] = 0
    fake[addr.enemy_species] = 0
    fake[addr.enemy_level] = 0
    _set_u16_be(addr.enemy_hp, 0)
    _set_u16_be(addr.enemy_max_hp, 0)

    class FakeMem:
        def __init__(self, d: Dict[int, int]) -> None:
            self.d = d
        def get_memory_value(self, i: int) -> int:
            return self.d.get(i, 0)

    reader = PokemonCrystalMemoryReader(FakeMem(fake), addr)
    state = reader.read_pokemon_state()

    assert state.player_name == "AB"
    assert state.money == 1234
    assert state.party_count == 1
    assert state.party[0].species_name == "Cyndaquil"
    assert state.party[0].level == 8
    assert state.party[0].hp == 25
    assert state.johto_badge_names == ["Zephyr", "Hive"]
    assert state.total_badges == 2
    assert not state.in_battle

    snap = reader.read_snapshot()
    assert snap["party_count"] == 1
    assert snap["badges"]["total"] == 2

    print("pokemon_memory.py -- all tests PASSED")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pokemon Crystal Memory Reader"
    )
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    parser.add_argument("--rom", type=str, default="", help="ROM path for live snapshot")
    parser.add_argument("--steps", type=int, default=0, help="Ticks before snapshot")
    parser.add_argument(
        "--i-own-this-rom", action="store_true",
        help="Required legal acknowledgement",
    )
    args = parser.parse_args(argv)

    if args.test:
        _self_test()
        return 0

    if args.rom:
        if not args.i_own_this_rom:
            print("Pass --i-own-this-rom")
            return 2
        rom_path = Path(args.rom).expanduser().resolve()
        if not rom_path.is_file():
            print(f"ROM not found: {rom_path}")
            return 2
        PyBoy, _ = _safe_import_pyboy()
        pyboy = PyBoy(str(rom_path), window_type="headless", sound=False)
        pyboy.set_emulation_speed(0)
        try:
            for _ in range(max(0, args.steps)):
                pyboy.tick()
            reader = PokemonCrystalMemoryReader.from_pyboy(pyboy)
            snap = reader.read_snapshot()
            print(json.dumps(snap, ensure_ascii=False, indent=2))
        finally:
            pyboy.stop()
        return 0

    print(json.dumps(asdict(CrystalMemoryAddresses()), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
