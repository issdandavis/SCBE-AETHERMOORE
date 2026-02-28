#!/usr/bin/env python3
"""
Georama — Tongue District Town Builder (Aethermoor RPG)
========================================================
Inspired by Dark Cloud's Georama system. Players place recovered Tongue
Shards on a 6-district grid to rebuild the destroyed Starter Village.

Each district is aligned to one of the Six Sacred Tongues. Placing shards
in their matching district grants harmony bonuses; mismatched placement
still works but weakens the town's tongue resonance.

Districts:
  KO — Authority Quarter    (governance, command, order)
  AV — Relay District       (transport, trade, communication)
  RU — Policy Ward          (memory, tradition, law)
  CA — Compute Gardens      (growth, science, crafting)
  UM — Shadow Undercroft    (secrets, stealth, truth)
  DR — Forge Quarter        (creation, smithing, building)

Villager NPCs (SPIRIT shards) unlock shops, quests, and buffs when
placed in the correct district.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from engine import Tongue
from atla import TongueShard, ShardType, ShardRarity, ShardInventory, SHARD_CATALOG


# ---------------------------------------------------------------------------
# District Configuration
# ---------------------------------------------------------------------------
DISTRICT_NAMES: Dict[Tongue, str] = {
    Tongue.KO: "Authority Quarter",
    Tongue.AV: "Relay District",
    Tongue.RU: "Policy Ward",
    Tongue.CA: "Compute Gardens",
    Tongue.UM: "Shadow Undercroft",
    Tongue.DR: "Forge Quarter",
}

DISTRICT_GRID_SIZE = 8  # Each district is an 8x8 placement grid
PHI = (1 + math.sqrt(5)) / 2


# ---------------------------------------------------------------------------
# Grid Cell
# ---------------------------------------------------------------------------
@dataclass
class GridCell:
    """A single cell in a district's placement grid."""
    x: int
    y: int
    shard: Optional[TongueShard] = None

    @property
    def occupied(self) -> bool:
        return self.shard is not None


# ---------------------------------------------------------------------------
# District
# ---------------------------------------------------------------------------
@dataclass
class District:
    """A tongue-aligned district of the rebuilt town."""
    tongue: Tongue
    name: str
    grid: List[List[GridCell]] = field(default_factory=list)
    placed_shards: List[TongueShard] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.grid:
            self.grid = [
                [GridCell(x, y) for x in range(DISTRICT_GRID_SIZE)]
                for y in range(DISTRICT_GRID_SIZE)
            ]

    def place_shard(self, shard: TongueShard, x: int, y: int) -> bool:
        """Place a shard on the grid. Returns True on success."""
        # Validate bounds
        slots = shard.georama_slots
        if slots == 1:
            cells = [(x, y)]
        elif slots == 2:
            cells = [(x, y), (x + 1, y)]
        elif slots == 4:
            cells = [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
        else:
            cells = [(x, y)]

        # Check all cells are in bounds and unoccupied
        for cx, cy in cells:
            if cx < 0 or cx >= DISTRICT_GRID_SIZE or cy < 0 or cy >= DISTRICT_GRID_SIZE:
                return False
            if self.grid[cy][cx].occupied:
                return False

        # Place
        for cx, cy in cells:
            self.grid[cy][cx].shard = shard
        shard.placed = True
        shard.district = self.name
        self.placed_shards.append(shard)
        return True

    def remove_shard(self, shard: TongueShard) -> bool:
        """Remove a placed shard from the grid."""
        if shard not in self.placed_shards:
            return False
        for row in self.grid:
            for cell in row:
                if cell.shard is shard:
                    cell.shard = None
        shard.placed = False
        self.placed_shards.remove(shard)
        return True

    @property
    def harmony(self) -> float:
        """Calculate tongue harmony score for this district.

        Matching tongue shards give full weight (1.0).
        Mismatched shards give partial weight (0.4).
        Score = sum(weights) / max_possible, range [0.0, 1.0].
        """
        if not self.placed_shards:
            return 0.0

        total_possible = len(SHARD_CATALOG.get(self.tongue, []))
        if total_possible == 0:
            return 0.0

        score = 0.0
        for s in self.placed_shards:
            if s.tongue == self.tongue:
                score += 1.0
            else:
                score += 0.4
        return min(score / total_possible, 1.0)

    @property
    def structures(self) -> List[TongueShard]:
        return [s for s in self.placed_shards if s.shard_type == ShardType.STRUCTURE]

    @property
    def spirits(self) -> List[TongueShard]:
        return [s for s in self.placed_shards if s.shard_type == ShardType.SPIRIT]

    @property
    def nature(self) -> List[TongueShard]:
        return [s for s in self.placed_shards if s.shard_type == ShardType.NATURE]

    @property
    def relics(self) -> List[TongueShard]:
        return [s for s in self.placed_shards if s.shard_type == ShardType.RELIC]

    @property
    def occupied_cells(self) -> int:
        count = 0
        for row in self.grid:
            for cell in row:
                if cell.occupied:
                    count += 1
        return count

    @property
    def total_cells(self) -> int:
        return DISTRICT_GRID_SIZE * DISTRICT_GRID_SIZE

    def stats(self) -> Dict[str, Any]:
        return {
            "tongue": self.tongue.value,
            "name": self.name,
            "harmony": round(self.harmony, 3),
            "placed": len(self.placed_shards),
            "structures": len(self.structures),
            "spirits": len(self.spirits),
            "nature": len(self.nature),
            "relics": len(self.relics),
            "grid_usage": f"{self.occupied_cells}/{self.total_cells}",
        }


# ---------------------------------------------------------------------------
# Town (all 6 districts)
# ---------------------------------------------------------------------------
class Town:
    """The full town grid — 6 tongue districts arranged in a hex-inspired layout."""

    def __init__(self, name: str = "Starter Village") -> None:
        self.name: str = name
        self.districts: Dict[Tongue, District] = {
            tongue: District(tongue=tongue, name=dname)
            for tongue, dname in DISTRICT_NAMES.items()
        }

    def place_shard(self, shard: TongueShard, tongue: Tongue,
                    x: int, y: int) -> bool:
        """Place a shard in a specific district at (x, y)."""
        district = self.districts.get(tongue)
        if district is None:
            return False
        return district.place_shard(shard, x, y)

    def auto_place(self, shard: TongueShard) -> bool:
        """Auto-place a shard in its matching district at the first open spot."""
        target_tongue = shard.tongue
        district = self.districts[target_tongue]

        slots = shard.georama_slots
        for y in range(DISTRICT_GRID_SIZE):
            for x in range(DISTRICT_GRID_SIZE):
                if district.place_shard(shard, x, y):
                    return True
        return False

    def remove_shard(self, shard: TongueShard) -> bool:
        """Remove a shard from whichever district it's placed in."""
        for district in self.districts.values():
            if shard in district.placed_shards:
                return district.remove_shard(shard)
        return False

    @property
    def total_harmony(self) -> float:
        """Overall town harmony — average of all district harmonies."""
        harmonies = [d.harmony for d in self.districts.values()]
        return sum(harmonies) / len(harmonies) if harmonies else 0.0

    @property
    def total_placed(self) -> int:
        return sum(len(d.placed_shards) for d in self.districts.values())

    @property
    def total_spirits(self) -> int:
        return sum(len(d.spirits) for d in self.districts.values())

    @property
    def unlocked_shops(self) -> List[str]:
        """Shops unlocked by placing SPIRIT shards."""
        shops = []
        for d in self.districts.values():
            for spirit in d.spirits:
                shops.append(f"{spirit.name} ({d.name})")
        return shops

    @property
    def unlocked_buffs(self) -> List[str]:
        """Buffs from LEGENDARY structures placed correctly."""
        buffs = []
        for d in self.districts.values():
            for s in d.structures:
                if s.rarity == ShardRarity.LEGENDARY and s.tongue == d.tongue:
                    buffs.append(f"{s.name} Aura ({d.name})")
        return buffs

    def stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total_harmony": round(self.total_harmony, 3),
            "total_placed": self.total_placed,
            "total_spirits": self.total_spirits,
            "shops": self.unlocked_shops,
            "buffs": self.unlocked_buffs,
            "districts": {
                tongue.value: d.stats()
                for tongue, d in self.districts.items()
            },
        }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def selftest() -> None:
    print(f"\n{'='*60}")
    print("  Georama Town Builder — Self-Test")
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

    # Create town
    town = Town("Test Village")
    check("Town created", town.name == "Test Village")
    check("6 districts", len(town.districts) == 6)
    check("Initial harmony 0.0", town.total_harmony == 0.0)

    # Create some test shards
    from atla import TongueShard, ShardType, ShardRarity
    import uuid

    shard_ko = TongueShard(
        shard_id=uuid.uuid4().hex[:12], tongue=Tongue.KO,
        shard_type=ShardType.STRUCTURE, rarity=ShardRarity.COMMON,
        name="Guard Post", description="A small watchtower.",
        district="Authority Quarter", georama_slots=1,
    )
    shard_ko_legend = TongueShard(
        shard_id=uuid.uuid4().hex[:12], tongue=Tongue.KO,
        shard_type=ShardType.STRUCTURE, rarity=ShardRarity.LEGENDARY,
        name="Command Hall", description="Seat of KO authority.",
        district="Authority Quarter", georama_slots=4,
    )
    shard_spirit = TongueShard(
        shard_id=uuid.uuid4().hex[:12], tongue=Tongue.KO,
        shard_type=ShardType.SPIRIT, rarity=ShardRarity.RARE,
        name="Captain Maren", description="Head of KO guard.",
        district="Authority Quarter", georama_slots=1,
    )
    shard_dr = TongueShard(
        shard_id=uuid.uuid4().hex[:12], tongue=Tongue.DR,
        shard_type=ShardType.STRUCTURE, rarity=ShardRarity.COMMON,
        name="Anvil Post", description="A small repair station.",
        district="Forge Quarter", georama_slots=1,
    )

    # Place shards
    check("Place KO shard in KO district", town.place_shard(shard_ko, Tongue.KO, 0, 0))
    check("Shard marked placed", shard_ko.placed)
    check("Total placed = 1", town.total_placed == 1)

    # Place legendary (4-slot)
    check("Place legendary 4-slot", town.place_shard(shard_ko_legend, Tongue.KO, 2, 0))
    check("Legendary occupies 4 cells",
          town.districts[Tongue.KO].occupied_cells == 5)  # 1 + 4

    # Can't overlap
    check("Can't overlap placed shard",
          not town.place_shard(shard_dr, Tongue.KO, 0, 0))

    # Place spirit -> unlocks shop
    check("Place spirit NPC", town.place_shard(shard_spirit, Tongue.KO, 4, 0))
    check("Shop unlocked", len(town.unlocked_shops) == 1)
    check("Spirit count", town.total_spirits == 1)

    # Legendary in matching district -> buff
    check("Buff from legendary", len(town.unlocked_buffs) == 1)

    # Harmony > 0 after placing matching shards
    check("KO district harmony > 0", town.districts[Tongue.KO].harmony > 0)

    # Place mismatched shard (DR shard in KO district)
    shard_dr_mismatch = TongueShard(
        shard_id=uuid.uuid4().hex[:12], tongue=Tongue.DR,
        shard_type=ShardType.NATURE, rarity=ShardRarity.COMMON,
        name="Ember Brazier", description="A warm forge-light.",
        district="Forge Quarter", georama_slots=1,
    )
    check("Place mismatched shard", town.place_shard(shard_dr_mismatch, Tongue.KO, 6, 0))
    # Mismatched shards count as 0.4 instead of 1.0

    # Auto-place
    shard_dr2 = TongueShard(
        shard_id=uuid.uuid4().hex[:12], tongue=Tongue.DR,
        shard_type=ShardType.STRUCTURE, rarity=ShardRarity.COMMON,
        name="Anvil Post", description="A small repair station.",
        district="Forge Quarter", georama_slots=1,
    )
    check("Auto-place DR shard", town.auto_place(shard_dr2))
    check("DR district has 1 shard", len(town.districts[Tongue.DR].placed_shards) == 1)

    # Remove shard
    check("Remove shard", town.remove_shard(shard_dr_mismatch))
    check("Shard unmarked", not shard_dr_mismatch.placed)

    # Stats
    stats = town.stats()
    check("Stats computed", stats["total_placed"] > 0)
    check("Total harmony > 0", stats["total_harmony"] > 0)

    # Out of bounds
    bad_shard = TongueShard(
        shard_id=uuid.uuid4().hex[:12], tongue=Tongue.CA,
        shard_type=ShardType.STRUCTURE, rarity=ShardRarity.LEGENDARY,
        name="Crystal Lab", description="Lab.",
        district="Compute Gardens", georama_slots=4,
    )
    check("Can't place 4-slot at edge", not town.place_shard(bad_shard, Tongue.CA, 7, 7))
    check("Can place 4-slot at valid spot", town.place_shard(bad_shard, Tongue.CA, 0, 0))

    # Town overview
    print(f"\n  Town: {town.name}")
    print(f"  Total Harmony: {town.total_harmony:.1%}")
    print(f"  Total Placed: {town.total_placed}")
    print(f"  Shops: {town.unlocked_shops}")
    print(f"  Buffs: {town.unlocked_buffs}")
    for tongue, d in town.districts.items():
        s = d.stats()
        print(f"    {s['name']}: harmony={s['harmony']:.1%}, "
              f"placed={s['placed']}, grid={s['grid_usage']}")

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    selftest()
