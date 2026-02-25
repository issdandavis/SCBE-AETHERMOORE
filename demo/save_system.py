#!/usr/bin/env python3
"""
Save / Load System — Aethermoor RPG
====================================
JSON-based save system with 3 slots, metadata, and auto-save.

Serializes full game state including:
  - Player party (Characters with Stats, Spells, evolution)
  - Dungeon progress (tower floor, shard inventory)
  - Town (georama district placements)
  - Weapon inventory
  - Gold, materials, skill XP, game phase, scene

File layout:
  demo/saves/
    slot_1.json
    slot_2.json
    slot_3.json
    autosave.json
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent))

from engine import Tongue, EvoStage, Stats, Character, Spell
from atla import TongueShard, ShardType, ShardRarity, ShardInventory
from weapons import TongueWeapon, WeaponType, WeaponRarity, WeaponAbility, WeaponInventory, TONGUE_ABILITIES
from georama import Town, District, DISTRICT_NAMES
from aether_eggs import (
    SacredEgg, EggStage, EggLocation, EggIncubator,
    DataPoint, DataPointType, TriManifoldState,
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SAVE_DIR = Path(__file__).parent / "saves"
MAX_SLOTS = 3
AUTOSAVE_NAME = "autosave"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class SaveSlot:
    """Metadata for a save slot — shown in the load screen."""
    slot: int                    # 1, 2, 3  (0 = autosave)
    exists: bool = False
    player_name: str = ""
    player_class: str = ""
    floor_reached: int = 0
    gold: int = 0
    party_size: int = 0
    playtime_seconds: float = 0.0
    timestamp: str = ""          # ISO-8601

    @property
    def playtime_display(self) -> str:
        h = int(self.playtime_seconds // 3600)
        m = int((self.playtime_seconds % 3600) // 60)
        s = int(self.playtime_seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    @property
    def label(self) -> str:
        if not self.exists:
            return f"Slot {self.slot} — Empty"
        return (f"Slot {self.slot} — {self.player_name} "
                f"(Floor {self.floor_reached}) "
                f"{self.playtime_display}")


@dataclass
class GameSaveData:
    """Full serialized game state."""
    # Meta
    version: int = 1
    timestamp: str = ""
    playtime_seconds: float = 0.0

    # Player identity
    player_name: str = ""
    player_class: str = ""
    game_phase: str = "intro"
    scene_id: str = "starter_village"

    # Party
    party: List[Dict[str, Any]] = field(default_factory=list)

    # Dungeon progress
    tower_floor: int = 1
    shards: List[Dict[str, Any]] = field(default_factory=list)
    shard_found_names: List[str] = field(default_factory=list)

    # Town / georama
    town_name: str = "Starter Village"
    town_placements: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    # Weapons
    weapons: List[Dict[str, Any]] = field(default_factory=list)
    equipped_weapon_id: Optional[str] = None

    # Economy
    gold: int = 0
    materials: Dict[str, int] = field(default_factory=dict)
    skill_xp: Dict[str, float] = field(default_factory=dict)

    # AetherEggs
    eggs: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------
def _serialize_spell(spell: Spell) -> Dict[str, Any]:
    return {
        "name": spell.name,
        "tongue": spell.tongue.value,
        "power": spell.power,
        "mp_cost": spell.mp_cost,
        "description": spell.description,
        "min_proficiency": spell.min_proficiency,
    }


def _deserialize_spell(d: Dict[str, Any]) -> Spell:
    return Spell(
        name=d["name"],
        tongue=Tongue(d["tongue"]),
        power=d["power"],
        mp_cost=d["mp_cost"],
        description=d["description"],
        min_proficiency=d.get("min_proficiency", 0.0),
    )


def _serialize_stats(stats: Stats) -> Dict[str, Any]:
    return {
        "hp": stats.hp,
        "max_hp": stats.max_hp,
        "mp": stats.mp,
        "max_mp": stats.max_mp,
        "attack": stats.attack,
        "defense": stats.defense,
        "speed": stats.speed,
        "wisdom": stats.wisdom,
        "tongue_prof": dict(stats.tongue_prof),
    }


def _deserialize_stats(d: Dict[str, Any]) -> Stats:
    return Stats(
        hp=d["hp"],
        max_hp=d["max_hp"],
        mp=d["mp"],
        max_mp=d["max_mp"],
        attack=d["attack"],
        defense=d["defense"],
        speed=d["speed"],
        wisdom=d["wisdom"],
        tongue_prof=d.get("tongue_prof", {t.value: 0.0 for t in Tongue}),
    )


def _serialize_character(char: Character) -> Dict[str, Any]:
    return {
        "name": char.name,
        "title": char.title,
        "tongue_affinity": char.tongue_affinity.value,
        "evo_stage": char.evo_stage.value,
        "stats": _serialize_stats(char.stats),
        "spells": [_serialize_spell(s) for s in char.spells],
        "backstory": char.backstory,
        "is_party_member": char.is_party_member,
        "is_enemy": char.is_enemy,
    }


def _deserialize_character(d: Dict[str, Any]) -> Character:
    return Character(
        name=d["name"],
        title=d["title"],
        tongue_affinity=Tongue(d["tongue_affinity"]),
        evo_stage=EvoStage(d["evo_stage"]),
        stats=_deserialize_stats(d["stats"]),
        spells=[_deserialize_spell(s) for s in d.get("spells", [])],
        backstory=d.get("backstory", ""),
        is_party_member=d.get("is_party_member", False),
        is_enemy=d.get("is_enemy", False),
    )


def _serialize_shard(shard: TongueShard) -> Dict[str, Any]:
    return {
        "shard_id": shard.shard_id,
        "tongue": shard.tongue.value,
        "shard_type": shard.shard_type.value,
        "rarity": shard.rarity.value,
        "name": shard.name,
        "description": shard.description,
        "district": shard.district,
        "georama_slots": shard.georama_slots,
        "placed": shard.placed,
        "floor_found": shard.floor_found,
    }


def _deserialize_shard(d: Dict[str, Any]) -> TongueShard:
    return TongueShard(
        shard_id=d["shard_id"],
        tongue=Tongue(d["tongue"]),
        shard_type=ShardType(d["shard_type"]),
        rarity=ShardRarity(d["rarity"]),
        name=d["name"],
        description=d["description"],
        district=d["district"],
        georama_slots=d.get("georama_slots", 1),
        placed=d.get("placed", False),
        floor_found=d.get("floor_found", 0),
    )


def _serialize_weapon_ability(ability: WeaponAbility) -> Dict[str, Any]:
    return {
        "name": ability.name,
        "description": ability.description,
        "unlock_level": ability.unlock_level,
        "tongue": ability.tongue.value,
        "power_bonus": ability.power_bonus,
        "effect": ability.effect,
    }


def _serialize_weapon(weapon: TongueWeapon) -> Dict[str, Any]:
    return {
        "weapon_id": weapon.weapon_id,
        "name": weapon.name,
        "weapon_type": weapon.weapon_type.value,
        "tongue": weapon.tongue.value,
        "rarity": weapon.rarity.value,
        "attack": weapon.attack,
        "wisdom": weapon.wisdom,
        "speed": weapon.speed,
        "durability": weapon.durability,
        "max_durability": weapon.max_durability,
        "level": weapon.level,
        "abs_xp": weapon.abs_xp,
        "abs_to_next": weapon.abs_to_next,
        "abilities": [_serialize_weapon_ability(a) for a in weapon.abilities],
        "equipped": weapon.equipped,
    }


def _deserialize_weapon(d: Dict[str, Any]) -> TongueWeapon:
    tongue = Tongue(d["tongue"])
    weapon_type = WeaponType(d["weapon_type"])
    rarity = WeaponRarity(d["rarity"])

    # Reconstruct abilities from the canonical TONGUE_ABILITIES list
    # so object identity stays consistent with the game engine.
    ability_names = {a["name"] for a in d.get("abilities", [])}
    abilities: List[WeaponAbility] = []
    for a in TONGUE_ABILITIES.get(tongue, []):
        if a.name in ability_names:
            abilities.append(a)

    weapon = TongueWeapon.__new__(TongueWeapon)
    weapon.weapon_id = d["weapon_id"]
    weapon.name = d["name"]
    weapon.weapon_type = weapon_type
    weapon.tongue = tongue
    weapon.rarity = rarity
    weapon.attack = d["attack"]
    weapon.wisdom = d["wisdom"]
    weapon.speed = d["speed"]
    weapon.durability = d["durability"]
    weapon.max_durability = d["max_durability"]
    weapon.level = d["level"]
    weapon.abs_xp = d["abs_xp"]
    weapon.abs_to_next = d["abs_to_next"]
    weapon.abilities = abilities
    weapon.equipped = d.get("equipped", False)
    return weapon


def _serialize_town(town: Town) -> Dict[str, Any]:
    """Serialize the town's district placements (not the empty grid cells)."""
    placements: Dict[str, List[Dict[str, Any]]] = {}
    for tongue, district in town.districts.items():
        placed = []
        for shard in district.placed_shards:
            # Find the shard's grid position by scanning the grid
            pos_x, pos_y = 0, 0
            for y, row in enumerate(district.grid):
                for x, cell in enumerate(row):
                    if cell.shard is shard:
                        pos_x, pos_y = x, y
                        break
                else:
                    continue
                break
            placed.append({
                "shard": _serialize_shard(shard),
                "x": pos_x,
                "y": pos_y,
            })
        placements[tongue.value] = placed
    return {
        "name": town.name,
        "placements": placements,
    }


def _deserialize_town(d: Dict[str, Any]) -> Town:
    """Reconstruct a Town from serialized data."""
    town = Town(name=d.get("name", "Starter Village"))
    placements = d.get("placements", {})
    for tongue_val, placed_list in placements.items():
        tongue = Tongue(tongue_val)
        for entry in placed_list:
            shard = _deserialize_shard(entry["shard"])
            x = entry["x"]
            y = entry["y"]
            town.place_shard(shard, tongue, x, y)
    return town


def _serialize_egg(egg: SacredEgg) -> Dict[str, Any]:
    """Serialize a Sacred Egg for save files."""
    return {
        "egg_id": egg.egg_id,
        "name": egg.name,
        "tongue": egg.tongue.value,
        "stage": egg.stage.value,
        "location": egg.location.value,
        "geo_district": egg.geo_district,
        "geo_floor": egg.geo_floor,
        "geo_map": egg.geo_map,
        "geo_seal_hash": egg.geo_seal_hash,
        "total_absorbed": egg.total_absorbed,
        "tongue_affinity_score": egg.tongue_affinity_score,
        "personality": dict(egg.personality),
        "manifold": egg.manifold.to_dict(),
        "created_at": egg.created_at,
        "hatched_at": egg.hatched_at,
        "glow_intensity": egg.glow_intensity,
        "export_ready": egg.export_ready,
    }


def _deserialize_egg(d: Dict[str, Any]) -> SacredEgg:
    """Reconstruct a Sacred Egg from serialized data."""
    egg = SacredEgg.__new__(SacredEgg)
    egg.egg_id = d["egg_id"]
    egg.name = d["name"]
    egg.tongue = Tongue(d["tongue"])
    egg.stage = EggStage(d["stage"])
    egg.location = EggLocation(d["location"])
    egg.geo_district = d.get("geo_district", "")
    egg.geo_floor = d.get("geo_floor", 0)
    egg.geo_map = d.get("geo_map", "")
    egg.geo_seal_hash = d.get("geo_seal_hash", "")
    egg.data_points = []  # Don't persist raw data points (training data is exported separately)
    egg.total_absorbed = d.get("total_absorbed", 0)
    egg.tongue_affinity_score = d.get("tongue_affinity_score", 0.0)
    egg.personality = d.get("personality", {
        "aggressive": 0.5, "curious": 0.5, "cautious": 0.5,
        "creative": 0.5, "loyal": 0.5, "mysterious": 0.5,
    })
    egg.manifold = TriManifoldState.from_dict(d.get("manifold", {}))
    egg.created_at = d.get("created_at", 0.0)
    egg.hatched_at = d.get("hatched_at", 0.0)
    egg.model_path = None
    egg.export_ready = d.get("export_ready", False)
    egg.glow_intensity = d.get("glow_intensity", 0.0)
    # Set color based on tongue
    tongue_colors = {
        Tongue.KO: (220, 60, 60), Tongue.AV: (60, 180, 220),
        Tongue.RU: (220, 180, 60), Tongue.CA: (60, 220, 120),
        Tongue.UM: (140, 60, 220), Tongue.DR: (220, 120, 60),
    }
    egg.color = tongue_colors.get(egg.tongue, (200, 200, 200))
    return egg


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------
def _slot_path(slot: int) -> Path:
    """Path for a numbered slot (1-3) or autosave (0)."""
    if slot == 0:
        return SAVE_DIR / f"{AUTOSAVE_NAME}.json"
    return SAVE_DIR / f"slot_{slot}.json"


def _ensure_save_dir() -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def save_game(slot: int, game_state: Dict[str, Any]) -> bool:
    """Save game state to a slot (1-3) or autosave (0).

    Parameters
    ----------
    slot : int
        Save slot number (1-3) or 0 for autosave.
    game_state : dict
        Dictionary with game state fields. Expected keys:
            player_name, player_class, game_phase, scene_id,
            party (list of Character), tower_floor, shard_inventory (ShardInventory),
            town (Town), weapon_inventory (WeaponInventory),
            gold, materials, skill_xp, playtime_seconds

    Returns
    -------
    bool
        True on success, False on failure.
    """
    if slot < 0 or slot > MAX_SLOTS:
        return False

    _ensure_save_dir()

    try:
        # Build the save data
        party_chars: List[Character] = game_state.get("party", [])
        shard_inv: Optional[ShardInventory] = game_state.get("shard_inventory")
        town: Optional[Town] = game_state.get("town")
        weapon_inv: Optional[WeaponInventory] = game_state.get("weapon_inventory")

        save = GameSaveData(
            version=1,
            timestamp=datetime.now(timezone.utc).isoformat(),
            playtime_seconds=game_state.get("playtime_seconds", 0.0),
            player_name=game_state.get("player_name", ""),
            player_class=game_state.get("player_class", ""),
            game_phase=game_state.get("game_phase", "intro"),
            scene_id=game_state.get("scene_id", "starter_village"),
            party=[_serialize_character(c) for c in party_chars],
            tower_floor=game_state.get("tower_floor", 1),
            gold=game_state.get("gold", 0),
            materials=game_state.get("materials", {}),
            skill_xp=game_state.get("skill_xp", {}),
        )

        # Shard inventory
        if shard_inv is not None:
            save.shards = [_serialize_shard(s) for s in shard_inv.shards]
            save.shard_found_names = list(shard_inv._found_names)

        # Town
        if town is not None:
            town_data = _serialize_town(town)
            save.town_name = town_data["name"]
            save.town_placements = town_data["placements"]

        # Weapons
        if weapon_inv is not None:
            save.weapons = [_serialize_weapon(w) for w in weapon_inv.weapons]
            if weapon_inv.equipped is not None:
                save.equipped_weapon_id = weapon_inv.equipped.weapon_id

        # AetherEggs
        egg_incubator: Optional[EggIncubator] = game_state.get("egg_incubator")
        if egg_incubator is not None:
            save.eggs = [_serialize_egg(e) for e in egg_incubator.eggs]

        # Write to disk
        path = _slot_path(slot)
        data = {
            "version": save.version,
            "timestamp": save.timestamp,
            "playtime_seconds": save.playtime_seconds,
            "player_name": save.player_name,
            "player_class": save.player_class,
            "game_phase": save.game_phase,
            "scene_id": save.scene_id,
            "party": save.party,
            "tower_floor": save.tower_floor,
            "shards": save.shards,
            "shard_found_names": save.shard_found_names,
            "town_name": save.town_name,
            "town_placements": save.town_placements,
            "weapons": save.weapons,
            "equipped_weapon_id": save.equipped_weapon_id,
            "gold": save.gold,
            "materials": save.materials,
            "skill_xp": save.skill_xp,
            "eggs": save.eggs,
        }

        # Atomic write: write to temp then rename
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # On Windows, os.replace handles overwriting
        os.replace(str(tmp_path), str(path))
        return True

    except Exception as e:
        print(f"  [SaveSystem] Error saving to slot {slot}: {e}")
        return False


def load_game(slot: int) -> Optional[Dict[str, Any]]:
    """Load game state from a slot.

    Parameters
    ----------
    slot : int
        Save slot number (1-3) or 0 for autosave.

    Returns
    -------
    dict or None
        Reconstructed game state with live objects:
            player_name, player_class, game_phase, scene_id,
            party (list of Character), tower_floor,
            shard_inventory (ShardInventory), town (Town),
            weapon_inventory (WeaponInventory),
            gold, materials, skill_xp, playtime_seconds
        Returns None if slot is empty or corrupt.
    """
    path = _slot_path(slot)
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Reconstruct party
        party = [_deserialize_character(cd) for cd in data.get("party", [])]

        # Reconstruct shard inventory
        shard_inv = ShardInventory()
        for sd in data.get("shards", []):
            shard = _deserialize_shard(sd)
            shard_inv.shards.append(shard)
        shard_inv._found_names = set(data.get("shard_found_names", []))

        # Reconstruct town
        town_data = {
            "name": data.get("town_name", "Starter Village"),
            "placements": data.get("town_placements", {}),
        }
        town = _deserialize_town(town_data)

        # Reconstruct weapon inventory
        weapon_inv = WeaponInventory()
        equipped_id = data.get("equipped_weapon_id")
        for wd in data.get("weapons", []):
            weapon = _deserialize_weapon(wd)
            weapon_inv.weapons.append(weapon)
            if equipped_id and weapon.weapon_id == equipped_id:
                weapon.equipped = True
                weapon_inv.equipped = weapon

        # Reconstruct egg incubator
        egg_incubator = EggIncubator()
        for ed in data.get("eggs", []):
            egg = _deserialize_egg(ed)
            egg_incubator.eggs.append(egg)
            if egg.location == EggLocation.HATCHED:
                egg_incubator.hatched.append(egg)

        return {
            "player_name": data.get("player_name", ""),
            "player_class": data.get("player_class", ""),
            "game_phase": data.get("game_phase", "intro"),
            "scene_id": data.get("scene_id", "starter_village"),
            "party": party,
            "tower_floor": data.get("tower_floor", 1),
            "shard_inventory": shard_inv,
            "town": town,
            "weapon_inventory": weapon_inv,
            "egg_incubator": egg_incubator,
            "gold": data.get("gold", 0),
            "materials": data.get("materials", {}),
            "skill_xp": data.get("skill_xp", {}),
            "playtime_seconds": data.get("playtime_seconds", 0.0),
        }

    except Exception as e:
        print(f"  [SaveSystem] Error loading slot {slot}: {e}")
        return None


def list_saves() -> List[SaveSlot]:
    """List all save slots with metadata.

    Returns
    -------
    list of SaveSlot
        Slots 0 (autosave), 1, 2, 3 with metadata if they exist.
    """
    slots: List[SaveSlot] = []
    for slot_num in range(0, MAX_SLOTS + 1):
        path = _slot_path(slot_num)
        info = SaveSlot(slot=slot_num)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                info.exists = True
                info.player_name = data.get("player_name", "???")
                info.player_class = data.get("player_class", "")
                info.floor_reached = data.get("tower_floor", 1)
                info.gold = data.get("gold", 0)
                info.party_size = len(data.get("party", []))
                info.playtime_seconds = data.get("playtime_seconds", 0.0)
                info.timestamp = data.get("timestamp", "")
            except Exception:
                pass
        slots.append(info)
    return slots


def delete_save(slot: int) -> bool:
    """Delete a save file.

    Parameters
    ----------
    slot : int
        Save slot number (0-3).

    Returns
    -------
    bool
        True if deleted, False if not found or error.
    """
    path = _slot_path(slot)
    if not path.exists():
        return False
    try:
        path.unlink()
        return True
    except Exception as e:
        print(f"  [SaveSystem] Error deleting slot {slot}: {e}")
        return False


def autosave(game_state: Dict[str, Any]) -> bool:
    """Convenience wrapper: save to slot 0 (autosave)."""
    return save_game(0, game_state)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def selftest() -> None:
    """Verify save/load round-trip with reconstructed objects."""
    import uuid
    from weapons import generate_weapon

    print(f"\n{'='*60}")
    print("  Save System — Self-Test")
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
            print(f"  FAIL  {name} {detail}")

    # ── Build a test game state ──────────────────────────────────────

    # Party
    izack = Character(
        name="Izack", title="Dimensional Scholar",
        tongue_affinity=Tongue.CA, evo_stage=EvoStage.ROOKIE,
        stats=Stats(hp=95, max_hp=120, mp=60, max_mp=80,
                    attack=8, defense=10, speed=9, wisdom=15,
                    tongue_prof={"KO": 0.1, "AV": 0.0, "RU": 0.2,
                                 "CA": 0.5, "UM": 0.0, "DR": 0.05}),
        spells=[
            Spell("Pocket Fold", Tongue.CA, 15, 8,
                  "Store an enemy in a micro-dimension for 1 turn"),
            Spell("Dimensional Shift", Tongue.CA, 25, 15,
                  "Phase through attacks"),
        ],
        backstory="Scholar of dimensions.",
        is_party_member=True,
    )

    polly = Character(
        name="Polly", title="Fifth Circle Keeper",
        tongue_affinity=Tongue.KO, evo_stage=EvoStage.CHAMPION,
        stats=Stats(hp=50, max_hp=60, mp=100, max_mp=120,
                    attack=6, defense=5, speed=14, wisdom=20,
                    tongue_prof={"KO": 0.7, "AV": 0.1, "RU": 0.3,
                                 "CA": 0.0, "UM": 0.2, "DR": 0.4}),
        spells=[
            Spell("Wingscroll Blast", Tongue.KO, 20, 10,
                  "Archived knowledge beam"),
        ],
        backstory="Sarcastic raven familiar.",
        is_party_member=True,
    )

    party = [izack, polly]

    # Shard inventory
    shard_inv = ShardInventory()
    shard1 = TongueShard(
        shard_id="abc123", tongue=Tongue.KO,
        shard_type=ShardType.STRUCTURE, rarity=ShardRarity.RARE,
        name="Archive Tower", description="Repository of edicts.",
        district="Authority Quarter", georama_slots=2, floor_found=7,
    )
    shard2 = TongueShard(
        shard_id="def456", tongue=Tongue.DR,
        shard_type=ShardType.SPIRIT, rarity=ShardRarity.UNCOMMON,
        name="Builder Kaya", description="Architect.",
        district="Forge Quarter", georama_slots=1, floor_found=12,
    )
    shard_inv.add(shard1)
    shard_inv.add(shard2)

    # Town with one placed shard
    town = Town("Rebuilt Village")
    placed_shard = TongueShard(
        shard_id="ghi789", tongue=Tongue.CA,
        shard_type=ShardType.NATURE, rarity=ShardRarity.COMMON,
        name="Crystal Flower", description="Refracts light.",
        district="Compute Gardens", georama_slots=1, floor_found=3,
    )
    town.place_shard(placed_shard, Tongue.CA, 2, 3)

    # Weapon inventory
    weapon_inv = WeaponInventory()
    sword = generate_weapon(Tongue.KO, WeaponType.BLADE, WeaponRarity.RARE)
    sword.absorb_xp(500)  # level it up a bit
    sword.use(10)          # wear some durability
    staff = generate_weapon(Tongue.CA, WeaponType.STAFF, WeaponRarity.UNCOMMON)
    weapon_inv.add(sword)
    weapon_inv.add(staff)
    weapon_inv.equip(sword)

    game_state = {
        "player_name": "Izack",
        "player_class": "Dimensional Scholar",
        "game_phase": "dungeon",
        "scene_id": "crystal_spire_f7",
        "party": party,
        "tower_floor": 7,
        "shard_inventory": shard_inv,
        "town": town,
        "weapon_inventory": weapon_inv,
        "gold": 1250,
        "materials": {"Crimson Ink": 3, "Growth Sap": 1, "Slag Chunk": 5},
        "skill_xp": {"alchemy": 42.5, "smithing": 18.0, "cartography": 7.5},
        "playtime_seconds": 3723.5,  # ~1h 2m
    }

    # ── Test save ────────────────────────────────────────────────────

    check("Save to slot 1", save_game(1, game_state))
    check("Save to slot 2", save_game(2, game_state))
    check("Autosave", autosave(game_state))
    check("Save file exists", _slot_path(1).exists())
    check("Autosave file exists", _slot_path(0).exists())
    check("Reject invalid slot", not save_game(5, game_state))

    # ── Test list_saves ──────────────────────────────────────────────

    slots = list_saves()
    check("list_saves returns 4 entries", len(slots) == 4)

    slot1_info = [s for s in slots if s.slot == 1][0]
    check("Slot 1 exists", slot1_info.exists)
    check("Slot 1 player name", slot1_info.player_name == "Izack")
    check("Slot 1 floor", slot1_info.floor_reached == 7)
    check("Slot 1 gold", slot1_info.gold == 1250)
    check("Slot 1 party size", slot1_info.party_size == 2)
    check("Slot 1 playtime > 0", slot1_info.playtime_seconds > 3000)
    check("Slot 1 label readable", "Izack" in slot1_info.label)

    slot3_info = [s for s in slots if s.slot == 3][0]
    check("Slot 3 empty", not slot3_info.exists)
    check("Slot 3 label says Empty", "Empty" in slot3_info.label)

    auto_info = [s for s in slots if s.slot == 0][0]
    check("Autosave detected", auto_info.exists)

    # ── Test load ────────────────────────────────────────────────────

    loaded = load_game(1)
    check("Load returns data", loaded is not None)

    if loaded:
        check("Player name round-trip", loaded["player_name"] == "Izack")
        check("Player class round-trip", loaded["player_class"] == "Dimensional Scholar")
        check("Game phase round-trip", loaded["game_phase"] == "dungeon")
        check("Scene id round-trip", loaded["scene_id"] == "crystal_spire_f7")
        check("Tower floor round-trip", loaded["tower_floor"] == 7)
        check("Gold round-trip", loaded["gold"] == 1250)
        check("Playtime round-trip", loaded["playtime_seconds"] == 3723.5)

        # Materials
        check("Materials round-trip",
              loaded["materials"].get("Crimson Ink") == 3)

        # Skill XP
        check("Skill XP round-trip",
              loaded["skill_xp"].get("alchemy") == 42.5)

        # Party
        loaded_party = loaded["party"]
        check("Party size round-trip", len(loaded_party) == 2)

        loaded_izack = loaded_party[0]
        check("Character name", loaded_izack.name == "Izack")
        check("Character title", loaded_izack.title == "Dimensional Scholar")
        check("Character tongue affinity",
              loaded_izack.tongue_affinity == Tongue.CA)
        check("Character evo stage",
              loaded_izack.evo_stage == EvoStage.ROOKIE)
        check("Character HP", loaded_izack.stats.hp == 95)
        check("Character max HP", loaded_izack.stats.max_hp == 120)
        check("Character tongue_prof CA=0.5",
              abs(loaded_izack.stats.tongue_prof["CA"] - 0.5) < 0.001)
        check("Character spells count", len(loaded_izack.spells) == 2)
        check("Spell name", loaded_izack.spells[0].name == "Pocket Fold")
        check("Spell tongue", loaded_izack.spells[0].tongue == Tongue.CA)
        check("Character is_party_member", loaded_izack.is_party_member)

        loaded_polly = loaded_party[1]
        check("Polly evo stage", loaded_polly.evo_stage == EvoStage.CHAMPION)

        # Shard inventory
        loaded_inv: ShardInventory = loaded["shard_inventory"]
        check("Shard count round-trip", loaded_inv.total == 2)
        check("Shard found_names set",
              "KO:Archive Tower" in loaded_inv._found_names)
        s1 = loaded_inv.shards[0]
        check("Shard tongue", s1.tongue == Tongue.KO)
        check("Shard type", s1.shard_type == ShardType.STRUCTURE)
        check("Shard rarity", s1.rarity == ShardRarity.RARE)
        check("Shard floor_found", s1.floor_found == 7)

        # Town
        loaded_town: Town = loaded["town"]
        check("Town name", loaded_town.name == "Rebuilt Village")
        check("Town has placed shard", loaded_town.total_placed == 1)
        ca_district = loaded_town.districts[Tongue.CA]
        check("CA district has 1 shard", len(ca_district.placed_shards) == 1)
        placed = ca_district.placed_shards[0]
        check("Placed shard name", placed.name == "Crystal Flower")
        check("Placed shard marked placed", placed.placed)

        # Weapons
        loaded_weapons: WeaponInventory = loaded["weapon_inventory"]
        check("Weapon count round-trip", len(loaded_weapons.weapons) == 2)
        check("Equipped weapon exists", loaded_weapons.equipped is not None)

        loaded_sword = loaded_weapons.weapons[0]
        check("Weapon name round-trip", loaded_sword.name == sword.name)
        check("Weapon type round-trip",
              loaded_sword.weapon_type == WeaponType.BLADE)
        check("Weapon tongue round-trip", loaded_sword.tongue == Tongue.KO)
        check("Weapon rarity round-trip",
              loaded_sword.rarity == WeaponRarity.RARE)
        check("Weapon level round-trip", loaded_sword.level == sword.level)
        check("Weapon attack round-trip", loaded_sword.attack == sword.attack)
        check("Weapon durability round-trip",
              loaded_sword.durability == sword.durability)
        check("Weapon max_durability round-trip",
              loaded_sword.max_durability == sword.max_durability)
        check("Weapon abs_xp round-trip", loaded_sword.abs_xp == sword.abs_xp)
        check("Weapon equipped flag", loaded_sword.equipped)
        check("Weapon abilities restored",
              len(loaded_sword.abilities) == len(sword.abilities))

    # ── Test load empty slot ─────────────────────────────────────────

    check("Load empty slot returns None", load_game(3) is None)

    # ── Test delete ──────────────────────────────────────────────────

    check("Delete slot 2", delete_save(2))
    check("Slot 2 gone", not _slot_path(2).exists())
    check("Delete nonexistent slot", not delete_save(2))

    # ── Test overwrite ───────────────────────────────────────────────

    game_state["gold"] = 9999
    game_state["tower_floor"] = 25
    check("Overwrite slot 1", save_game(1, game_state))
    reloaded = load_game(1)
    check("Overwritten gold", reloaded is not None and reloaded["gold"] == 9999)
    check("Overwritten floor",
          reloaded is not None and reloaded["tower_floor"] == 25)

    # ── Verify JSON file is human-readable ───────────────────────────

    with open(_slot_path(1), "r", encoding="utf-8") as f:
        raw = f.read()
    check("JSON is indented", "\n  " in raw)
    check("JSON contains player_name", '"player_name"' in raw)

    # ── Egg round-trip ──────────────────────────────────────────────

    egg_inc = EggIncubator()
    ko_egg = egg_inc.create_egg(Tongue.KO, "Test Crimson Shell")
    from aether_eggs import DataPoint as EggDP
    for _ in range(10):
        egg_inc.create_data_point(DataPointType.BATTLE_WIN, "Defeated enemy", "dungeon", floor=3, quality=0.9)

    egg_state = dict(game_state)
    egg_state["egg_incubator"] = egg_inc
    check("Save with eggs", save_game(3, egg_state))

    egg_loaded = load_game(3)
    check("Load with eggs", egg_loaded is not None)
    if egg_loaded:
        loaded_inc: EggIncubator = egg_loaded["egg_incubator"]
        check("Egg count round-trip", len(loaded_inc.eggs) == 1)
        loaded_egg = loaded_inc.eggs[0]
        check("Egg name round-trip", loaded_egg.name == "Test Crimson Shell")
        check("Egg tongue round-trip", loaded_egg.tongue == Tongue.KO)
        check("Egg absorbed round-trip", loaded_egg.total_absorbed == ko_egg.total_absorbed)
        check("Egg personality round-trip", loaded_egg.personality.get("aggressive", 0) > 0.5)
        check("Egg manifold round-trip", loaded_egg.manifold.energy_positive > 0)
        check("Egg geo_seal round-trip", loaded_egg.geo_seal_hash == ko_egg.geo_seal_hash)
    delete_save(3)

    # ── Cleanup test files ───────────────────────────────────────────

    for s in range(0, MAX_SLOTS + 1):
        delete_save(s)
    # Remove save dir if empty
    try:
        SAVE_DIR.rmdir()
    except OSError:
        pass

    # ── Summary ──────────────────────────────────────────────────────

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    selftest()
