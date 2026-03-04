#!/usr/bin/env python3
"""
Tongue Shard System (Atla) — Aethermoor RPG
=============================================
Inspired by Dark Cloud's Atla orb system. Dungeon floors drop Tongue
Shards — glowing orbs color-coded to the Six Sacred Tongues — that
contain fragments of the destroyed Starter Village.

Shard types:
  STRUCTURE  — buildings (Command Hall, Relay Hub, Forge, etc.)
  SPIRIT     — villager NPCs trapped in the tower
  NATURE     — trees, fountains, gardens, shrines
  RELIC      — unique items, lore fragments, weapon materials

Drop sources:
  - Chests on dungeon floors
  - Boss kills (guaranteed)
  - Hidden floor tiles (rare)
  - Quest rewards

The dungeon theme determines which tongues' shards appear:
  CRYSTAL → CA / DR
  SHADOW  → UM / KO
  FIRE    → DR / RU
  DATA    → AV / CA
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from engine import Tongue


# ---------------------------------------------------------------------------
# Shard Categories
# ---------------------------------------------------------------------------
class ShardType(Enum):
    STRUCTURE = "structure"   # Buildings
    SPIRIT = "spirit"         # Villager NPCs
    NATURE = "nature"         # Trees, gardens, shrines
    RELIC = "relic"           # Items, lore, materials


class ShardRarity(Enum):
    COMMON = "common"         # 60% — small decorations, basic materials
    UNCOMMON = "uncommon"     # 25% — houses, NPCs, gardens
    RARE = "rare"             # 12% — important buildings, key NPCs
    LEGENDARY = "legendary"   # 3%  — district centerpieces, unique relics


RARITY_WEIGHTS = {
    ShardRarity.COMMON: 60,
    ShardRarity.UNCOMMON: 25,
    ShardRarity.RARE: 12,
    ShardRarity.LEGENDARY: 3,
}


# ---------------------------------------------------------------------------
# Tongue Shard
# ---------------------------------------------------------------------------
@dataclass
class TongueShard:
    """A recoverable fragment of the destroyed Starter Village."""

    shard_id: str
    tongue: Tongue
    shard_type: ShardType
    rarity: ShardRarity
    name: str
    description: str
    district: str            # Which tongue district this belongs to
    georama_slots: int = 1   # How many grid slots it occupies
    placed: bool = False     # Whether it's been placed in the town
    floor_found: int = 0     # Which dungeon floor it was found on

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shard_id": self.shard_id,
            "tongue": self.tongue.value,
            "shard_type": self.shard_type.value,
            "rarity": self.rarity.value,
            "name": self.name,
            "description": self.description,
            "district": self.district,
            "georama_slots": self.georama_slots,
            "placed": self.placed,
            "floor_found": self.floor_found,
        }


# ---------------------------------------------------------------------------
# Shard Catalog — all recoverable fragments organized by tongue
# ---------------------------------------------------------------------------
SHARD_CATALOG: Dict[Tongue, List[Dict[str, Any]]] = {
    Tongue.KO: [
        # Structures
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.LEGENDARY,
         "name": "Command Hall", "desc": "The seat of KO authority. Unlocks governance buffs.",
         "slots": 4},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.RARE,
         "name": "Archive Tower", "desc": "Repository of edicts and decrees.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Familiar Den", "desc": "Where bonded creatures rest and train.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.COMMON,
         "name": "Guard Post", "desc": "A small watchtower for the district.",
         "slots": 1},
        # Spirits
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.RARE,
         "name": "Captain Maren", "desc": "Head of the KO guard. Gives authority quests.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.UNCOMMON,
         "name": "Archivist Lenn", "desc": "Keeper of old records. Sells lore scrolls.",
         "slots": 1},
        # Nature
        {"type": ShardType.NATURE, "rarity": ShardRarity.COMMON,
         "name": "KO Banner", "desc": "A crimson banner bearing the Authority seal.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Heart Shrine", "desc": "A shrine of collaborative love. Heals visitors.",
         "slots": 1},
        # Relics
        {"type": ShardType.RELIC, "rarity": ShardRarity.RARE,
         "name": "Edict Stone", "desc": "Ancient authority rune. Weapon material.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.COMMON,
         "name": "Crimson Ink", "desc": "Used for crafting KO scrolls.",
         "slots": 1},
    ],
    Tongue.AV: [
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.LEGENDARY,
         "name": "Relay Hub", "desc": "Central ley line nexus. Unlocks fast travel.",
         "slots": 4},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.RARE,
         "name": "Portal Gate", "desc": "Teleportation arch between districts.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Trade Post", "desc": "Merchant stall for exotic goods.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.COMMON,
         "name": "Signal Lamp", "desc": "A glowing ley-light for the path.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.RARE,
         "name": "Navigator Suli", "desc": "Cartographer. Opens new map regions.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.UNCOMMON,
         "name": "Courier Dash", "desc": "Message runner. Enables mail system.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.COMMON,
         "name": "Ley Crystal", "desc": "A softly humming blue crystal.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Wind Chime Tree", "desc": "A tree with crystal chimes. Calming.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.RARE,
         "name": "Transit Lens", "desc": "Reveals hidden paths. Weapon material.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.COMMON,
         "name": "Signal Dust", "desc": "Crafting material for AV items.",
         "slots": 1},
    ],
    Tongue.RU: [
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.LEGENDARY,
         "name": "Ancient Library", "desc": "Ancestral memory archive. Unlocks lore quests.",
         "slots": 4},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.RARE,
         "name": "Rune Forge", "desc": "Enchantment workshop for weapon upgrades.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Memory Garden", "desc": "Meditation space. Regen MP over time.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.COMMON,
         "name": "Standing Stone", "desc": "An ancient monolith. Marks territory.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.RARE,
         "name": "Elder Voss", "desc": "Village elder. Teaches ancient techniques.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.UNCOMMON,
         "name": "Scribe Haral", "desc": "Records history. Sells recipe scrolls.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.COMMON,
         "name": "Moss Lantern", "desc": "Ancient light powered by living moss.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.UNCOMMON,
         "name": "World Tree Sapling", "desc": "A cutting from the great tree.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.RARE,
         "name": "Ancestral Bone", "desc": "Resonates with ancient power. Weapon material.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.COMMON,
         "name": "Rune Chip", "desc": "Fragment of an old enchantment.",
         "slots": 1},
    ],
    Tongue.CA: [
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.LEGENDARY,
         "name": "Crystal Lab", "desc": "Compute and growth research. Unlocks crafting.",
         "slots": 4},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.RARE,
         "name": "Pattern Workshop", "desc": "Item synthesis workbench.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Growth Chamber", "desc": "Accelerates potion brewing.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.COMMON,
         "name": "Sprout Planter", "desc": "A small garden box for herbs.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.RARE,
         "name": "Alchemist Trin", "desc": "Potion master. Teaches brewing.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.UNCOMMON,
         "name": "Gardener Bloom", "desc": "Tends the growth chambers. Sells seeds.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.COMMON,
         "name": "Crystal Flower", "desc": "A flower that refracts light beautifully.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Living Fountain", "desc": "Water infused with growth energy.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.RARE,
         "name": "Compute Prism", "desc": "Focuses natural computation. Weapon material.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.COMMON,
         "name": "Growth Sap", "desc": "Sticky resin for CA crafting.",
         "slots": 1},
    ],
    Tongue.UM: [
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.LEGENDARY,
         "name": "Shadow Walk Gate", "desc": "Portal to hidden paths. Unlocks stealth skills.",
         "slots": 4},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.RARE,
         "name": "Night Market", "desc": "Black market for rare items.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Truth Well", "desc": "Reveals enemy weaknesses when visited.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.COMMON,
         "name": "Shadow Lamp", "desc": "A dim purple lantern. Marks hidden areas.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.RARE,
         "name": "Shadow Walker Nyx", "desc": "Scout master. Gives stealth quests.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.UNCOMMON,
         "name": "Grief Counselor Mira", "desc": "Healer of the spirit. Removes debuffs.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.COMMON,
         "name": "Dusk Fern", "desc": "A plant that thrives in shadow.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Echo Pool", "desc": "A still pool that whispers truths.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.RARE,
         "name": "Void Fragment", "desc": "A piece of pure shadow. Weapon material.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.COMMON,
         "name": "Shadow Thread", "desc": "Dark fiber for UM crafting.",
         "slots": 1},
    ],
    Tongue.DR: [
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.LEGENDARY,
         "name": "Grand Forge", "desc": "Master smithy. Unlocks weapon crafting.",
         "slots": 4},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.RARE,
         "name": "Schema Hall", "desc": "Blueprint library for inventions.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Builder's Den", "desc": "Construction planning room.",
         "slots": 2},
        {"type": ShardType.STRUCTURE, "rarity": ShardRarity.COMMON,
         "name": "Anvil Post", "desc": "A small repair station.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.RARE,
         "name": "Forge Master Gron", "desc": "Legendary smith. Forges tongue weapons.",
         "slots": 1},
        {"type": ShardType.SPIRIT, "rarity": ShardRarity.UNCOMMON,
         "name": "Builder Kaya", "desc": "Architect. Upgrades buildings.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.COMMON,
         "name": "Ember Brazier", "desc": "A warm forge-light. Never goes out.",
         "slots": 1},
        {"type": ShardType.NATURE, "rarity": ShardRarity.UNCOMMON,
         "name": "Iron Root Tree", "desc": "A tree with metallic bark. Sturdy.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.RARE,
         "name": "Forge Heart", "desc": "Core of creation energy. Weapon material.",
         "slots": 1},
        {"type": ShardType.RELIC, "rarity": ShardRarity.COMMON,
         "name": "Slag Chunk", "desc": "Raw forge material for DR crafting.",
         "slots": 1},
    ],
}

# Total unique shards per tongue: 10, total: 60


# ---------------------------------------------------------------------------
# Theme → Tongue mapping (which tongues drop from which dungeon theme)
# ---------------------------------------------------------------------------
THEME_TONGUE_DROPS: Dict[str, Tuple[Tongue, Tongue]] = {
    "Crystal": (Tongue.CA, Tongue.DR),
    "Shadow": (Tongue.UM, Tongue.KO),
    "Fire": (Tongue.DR, Tongue.RU),
    "Data": (Tongue.AV, Tongue.CA),
}


# ---------------------------------------------------------------------------
# Shard Inventory
# ---------------------------------------------------------------------------
class ShardInventory:
    """Player's collection of recovered Tongue Shards."""

    def __init__(self) -> None:
        self.shards: List[TongueShard] = []
        self._found_names: set = set()  # Track unique finds

    def add(self, shard: TongueShard) -> bool:
        """Add a shard. Returns False if duplicate (already found)."""
        key = f"{shard.tongue.value}:{shard.name}"
        if key in self._found_names:
            return False
        self._found_names.add(key)
        self.shards.append(shard)
        return True

    def get_by_tongue(self, tongue: Tongue) -> List[TongueShard]:
        return [s for s in self.shards if s.tongue == tongue]

    def get_by_type(self, shard_type: ShardType) -> List[TongueShard]:
        return [s for s in self.shards if s.shard_type == shard_type]

    def get_unplaced(self) -> List[TongueShard]:
        return [s for s in self.shards if not s.placed]

    def get_placed(self) -> List[TongueShard]:
        return [s for s in self.shards if s.placed]

    def mark_placed(self, shard_id: str) -> bool:
        for s in self.shards:
            if s.shard_id == shard_id:
                s.placed = True
                return True
        return False

    @property
    def total(self) -> int:
        return len(self.shards)

    @property
    def total_placed(self) -> int:
        return sum(1 for s in self.shards if s.placed)

    def completion_by_tongue(self) -> Dict[str, Tuple[int, int]]:
        """Returns {tongue: (found, total_possible)} for each tongue."""
        result = {}
        for tongue in Tongue:
            total_possible = len(SHARD_CATALOG.get(tongue, []))
            found = len(self.get_by_tongue(tongue))
            result[tongue.value] = (found, total_possible)
        return result

    def stats(self) -> Dict[str, Any]:
        return {
            "total_found": self.total,
            "total_placed": self.total_placed,
            "total_possible": sum(len(v) for v in SHARD_CATALOG.values()),
            "by_tongue": self.completion_by_tongue(),
            "by_type": {
                t.value: len(self.get_by_type(t))
                for t in ShardType
            },
        }


# ---------------------------------------------------------------------------
# Drop Generator
# ---------------------------------------------------------------------------
def _pick_rarity(floor_num: int, is_boss: bool = False,
                 is_gate_boss: bool = False) -> ShardRarity:
    """Pick shard rarity based on floor depth and source."""
    weights = dict(RARITY_WEIGHTS)

    # Deeper floors shift rarity up
    depth_bonus = min(floor_num // 10, 5)
    weights[ShardRarity.UNCOMMON] += depth_bonus * 3
    weights[ShardRarity.RARE] += depth_bonus * 2
    weights[ShardRarity.LEGENDARY] += depth_bonus

    # Bosses guarantee at least uncommon
    if is_boss:
        weights[ShardRarity.COMMON] = 0
        weights[ShardRarity.UNCOMMON] += 15
        weights[ShardRarity.RARE] += 10
        weights[ShardRarity.LEGENDARY] += 5

    # Gate bosses guarantee rare+
    if is_gate_boss:
        weights[ShardRarity.COMMON] = 0
        weights[ShardRarity.UNCOMMON] = 0
        weights[ShardRarity.RARE] += 20
        weights[ShardRarity.LEGENDARY] += 15

    rarities = list(weights.keys())
    w = [weights[r] for r in rarities]
    return random.choices(rarities, weights=w, k=1)[0]


def generate_shard(
    floor_num: int,
    theme: str,
    is_boss: bool = False,
    is_gate_boss: bool = False,
    already_found: Optional[set] = None,
) -> Optional[TongueShard]:
    """Generate a Tongue Shard drop from a dungeon floor.

    Parameters
    ----------
    floor_num : int
        Current dungeon floor (affects rarity).
    theme : str
        Floor theme name ("Crystal", "Shadow", "Fire", "Data").
    is_boss : bool
        True if from a boss kill.
    is_gate_boss : bool
        True if from a gate boss (floor % 10 == 0).
    already_found : set, optional
        Set of "TONGUE:name" strings already found (to avoid duplicates).

    Returns
    -------
    TongueShard or None
        A new shard, or None if no valid shard available.
    """
    if already_found is None:
        already_found = set()

    # Determine which tongues this theme can drop
    tongue_pair = THEME_TONGUE_DROPS.get(theme)
    if tongue_pair is None:
        tongue_pair = (Tongue.KO, Tongue.AV)  # fallback

    # Pick target rarity
    rarity = _pick_rarity(floor_num, is_boss, is_gate_boss)

    # Pick a tongue (primary tongue slightly more likely)
    tongue = tongue_pair[0] if random.random() < 0.6 else tongue_pair[1]

    # Find matching catalog entries
    catalog = SHARD_CATALOG.get(tongue, [])
    matching = [
        entry for entry in catalog
        if entry["rarity"] == rarity
        and f"{tongue.value}:{entry['name']}" not in already_found
    ]

    # Fall back to any rarity if no match at target rarity
    if not matching:
        matching = [
            entry for entry in catalog
            if f"{tongue.value}:{entry['name']}" not in already_found
        ]

    # Try the other tongue if still nothing
    if not matching:
        tongue = tongue_pair[1] if tongue == tongue_pair[0] else tongue_pair[0]
        catalog = SHARD_CATALOG.get(tongue, [])
        matching = [
            entry for entry in catalog
            if f"{tongue.value}:{entry['name']}" not in already_found
        ]

    if not matching:
        return None  # All shards for these tongues already found

    entry = random.choice(matching)

    district_names = {
        Tongue.KO: "Authority Quarter",
        Tongue.AV: "Relay District",
        Tongue.RU: "Policy Ward",
        Tongue.CA: "Compute Gardens",
        Tongue.UM: "Shadow Undercroft",
        Tongue.DR: "Forge Quarter",
    }

    shard = TongueShard(
        shard_id=uuid.uuid4().hex[:12],
        tongue=tongue,
        shard_type=entry["type"],
        rarity=entry["rarity"],
        name=entry["name"],
        description=entry["desc"],
        district=district_names.get(tongue, "Unknown"),
        georama_slots=entry.get("slots", 1),
        floor_found=floor_num,
    )
    return shard


def generate_floor_drops(
    floor_num: int,
    theme: str,
    chest_count: int = 0,
    boss_killed: bool = False,
    gate_boss_killed: bool = False,
    already_found: Optional[set] = None,
) -> List[TongueShard]:
    """Generate all shard drops for completing a dungeon floor.

    Normal floors: 30% chance per chest.
    Boss floors: guaranteed 1 shard + chest chances.
    Gate boss: guaranteed 1-2 shards + chest chances.
    """
    if already_found is None:
        already_found = set()

    drops: List[TongueShard] = []

    # Use a local copy so callers' sets aren't mutated behind their back.
    # The caller is responsible for tracking found shards (e.g. via inv.add).
    seen = set(already_found)

    # Chest drops (30% chance each)
    for _ in range(chest_count):
        if random.random() < 0.30:
            shard = generate_shard(floor_num, theme,
                                   already_found=seen)
            if shard:
                seen.add(f"{shard.tongue.value}:{shard.name}")
                drops.append(shard)

    # Boss drops (guaranteed)
    if boss_killed:
        shard = generate_shard(floor_num, theme, is_boss=True,
                               already_found=seen)
        if shard:
            seen.add(f"{shard.tongue.value}:{shard.name}")
            drops.append(shard)

    # Gate boss drops (guaranteed 1-2)
    if gate_boss_killed:
        for _ in range(random.randint(1, 2)):
            shard = generate_shard(floor_num, theme, is_gate_boss=True,
                                   already_found=seen)
            if shard:
                seen.add(f"{shard.tongue.value}:{shard.name}")
                drops.append(shard)

    return drops


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def selftest() -> None:
    """Verify shard generation and inventory."""
    print(f"\n{'='*60}")
    print("  Tongue Shard System — Self-Test")
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

    # Catalog completeness
    total_shards = sum(len(v) for v in SHARD_CATALOG.values())
    check("Catalog has 60 unique shards", total_shards == 60,
          f"got {total_shards}")

    for tongue in Tongue:
        count = len(SHARD_CATALOG.get(tongue, []))
        check(f"  {tongue.value} has 10 shards", count == 10,
              f"got {count}")

    # Generation
    inv = ShardInventory()
    for floor in range(1, 51):
        theme = ["Crystal", "Shadow", "Fire", "Data"][(floor - 1) // 20 % 4]
        is_boss = floor % 5 == 0
        is_gate = floor % 10 == 0
        drops = generate_floor_drops(
            floor, theme,
            chest_count=2,
            boss_killed=is_boss,
            gate_boss_killed=is_gate,
            already_found=inv._found_names,
        )
        for d in drops:
            inv.add(d)

    check("Found shards after 50 floors", inv.total > 0,
          f"found {inv.total}")
    check("Multiple tongues represented",
          len(set(s.tongue for s in inv.shards)) >= 3)

    # Boss drops
    boss_shard = generate_shard(10, "Crystal", is_boss=True)
    check("Boss shard generated", boss_shard is not None)
    if boss_shard:
        check("Boss shard is uncommon+",
              boss_shard.rarity != ShardRarity.COMMON)

    gate_shard = generate_shard(20, "Shadow", is_gate_boss=True)
    check("Gate boss shard generated", gate_shard is not None)
    if gate_shard:
        check("Gate boss shard is rare+",
              gate_shard.rarity in (ShardRarity.RARE, ShardRarity.LEGENDARY))

    # Inventory
    stats = inv.stats()
    check("Stats computed", stats["total_found"] > 0)
    check("Completion tracking works",
          all(v[1] == 10 for v in stats["by_tongue"].values()))

    print(f"\n  Inventory: {inv.total} shards found across 50 floors")
    for tongue_val, (found, total) in stats["by_tongue"].items():
        pct = found / total * 100 if total > 0 else 0
        print(f"    {tongue_val}: {found}/{total} ({pct:.0f}%)")

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    selftest()
