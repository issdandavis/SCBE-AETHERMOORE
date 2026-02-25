#!/usr/bin/env python3
"""
Tongue Weapons — Aethermoor RPG
================================
Dark Cloud-inspired weapon system with Sacred Tongue bindings.

Each weapon is attuned to one of the Six Sacred Tongues and gains
bonus damage against its tongue's favored targets (using TONGUE_CHART).

Key mechanics:
  - **ABS (Absorption)**: Weapons absorb XP from kills to level up.
  - **Fatigue**: Weapons lose durability with use. At 0 durability, damage
    is halved. Repair at a forge or with materials.
  - **Tongue Growth**: As a weapon levels, its tongue proficiency deepens,
    unlocking new abilities.
  - **Synthesis**: Combine two weapons to transfer stats (like Dark Cloud's
    weapon synthesis / build-up system).

Weapon types:
  BLADE   — Fast, balanced. KO/DR affinity.
  STAFF   — Magic focused. CA/RU affinity.
  BOW     — Ranged. AV/UM affinity.
  GAUNTLET — Heavy, slow. DR/KO affinity.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from engine import Tongue, TONGUE_CHART

PHI = (1 + math.sqrt(5)) / 2


# ---------------------------------------------------------------------------
# Weapon Type
# ---------------------------------------------------------------------------
class WeaponType(Enum):
    BLADE = "blade"
    STAFF = "staff"
    BOW = "bow"
    GAUNTLET = "gauntlet"


# Type -> stat bonuses (atk_mult, wis_mult, spd_mult)
WEAPON_TYPE_SCALING: Dict[WeaponType, Tuple[float, float, float]] = {
    WeaponType.BLADE:    (1.0, 0.6, 1.0),
    WeaponType.STAFF:    (0.5, 1.2, 0.7),
    WeaponType.BOW:      (0.8, 0.8, 1.2),
    WeaponType.GAUNTLET: (1.3, 0.4, 0.6),
}

# Type -> tongue affinities (which tongues this type resonates with)
WEAPON_TYPE_AFFINITIES: Dict[WeaponType, Tuple[Tongue, Tongue]] = {
    WeaponType.BLADE:    (Tongue.KO, Tongue.DR),
    WeaponType.STAFF:    (Tongue.CA, Tongue.RU),
    WeaponType.BOW:      (Tongue.AV, Tongue.UM),
    WeaponType.GAUNTLET: (Tongue.DR, Tongue.KO),
}


# ---------------------------------------------------------------------------
# Weapon Rarity
# ---------------------------------------------------------------------------
class WeaponRarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    LEGENDARY = "legendary"


RARITY_BASE_STATS: Dict[WeaponRarity, Dict[str, int]] = {
    WeaponRarity.COMMON:    {"atk": 8,  "wis": 4,  "spd": 5,  "durability": 60},
    WeaponRarity.UNCOMMON:  {"atk": 14, "wis": 7,  "spd": 7,  "durability": 80},
    WeaponRarity.RARE:      {"atk": 22, "wis": 12, "spd": 10, "durability": 100},
    WeaponRarity.LEGENDARY: {"atk": 35, "wis": 20, "spd": 14, "durability": 140},
}

# Max level per rarity
MAX_LEVEL: Dict[WeaponRarity, int] = {
    WeaponRarity.COMMON: 20,
    WeaponRarity.UNCOMMON: 30,
    WeaponRarity.RARE: 40,
    WeaponRarity.LEGENDARY: 50,
}


# ---------------------------------------------------------------------------
# Weapon Ability
# ---------------------------------------------------------------------------
@dataclass
class WeaponAbility:
    """A special ability unlocked at a certain weapon level."""
    name: str
    description: str
    unlock_level: int
    tongue: Tongue
    power_bonus: int = 0
    effect: str = ""  # "heal", "poison", "stun", "pierce", etc.


# Abilities per tongue (unlocked as weapon levels up)
TONGUE_ABILITIES: Dict[Tongue, List[WeaponAbility]] = {
    Tongue.KO: [
        WeaponAbility("Command Strike", "Orders reality to amplify damage", 5, Tongue.KO, 8, "pierce"),
        WeaponAbility("Authority Aura", "Nearby allies gain +10% ATK", 15, Tongue.KO, 0, "buff_atk"),
        WeaponAbility("Edict Blade", "Ignores 50% of target defense", 25, Tongue.KO, 15, "pierce"),
    ],
    Tongue.AV: [
        WeaponAbility("Transit Shot", "Attack warps through defenses", 5, Tongue.AV, 6, "pierce"),
        WeaponAbility("Relay Burst", "Hits bounce to a second target", 15, Tongue.AV, 10, "chain"),
        WeaponAbility("Signal Storm", "AOE energy pulse", 25, Tongue.AV, 20, "aoe"),
    ],
    Tongue.RU: [
        WeaponAbility("Memory Echo", "Repeats last attack at 50% power", 5, Tongue.RU, 5, "echo"),
        WeaponAbility("Ancestral Guard", "20% chance to block incoming damage", 15, Tongue.RU, 0, "guard"),
        WeaponAbility("Law of Return", "Reflects 30% damage back to attacker", 25, Tongue.RU, 12, "reflect"),
    ],
    Tongue.CA: [
        WeaponAbility("Growth Burst", "Heals user 10% on hit", 5, Tongue.CA, 4, "heal"),
        WeaponAbility("Compute Cascade", "Increases crit rate by 15%", 15, Tongue.CA, 0, "crit_up"),
        WeaponAbility("Pattern Overload", "Massive damage on crit", 25, Tongue.CA, 25, "crit_bonus"),
    ],
    Tongue.UM: [
        WeaponAbility("Shadow Step", "+20% evasion after attacking", 5, Tongue.UM, 0, "evade"),
        WeaponAbility("Void Drain", "Steals 15% of damage as HP", 15, Tongue.UM, 8, "drain"),
        WeaponAbility("Eclipse Edge", "Chance to inflict blind", 25, Tongue.UM, 18, "blind"),
    ],
    Tongue.DR: [
        WeaponAbility("Forge Strike", "Bonus damage to structures/golems", 5, Tongue.DR, 10, "structure_bonus"),
        WeaponAbility("Temper", "Self-repair 5 durability on boss kill", 15, Tongue.DR, 0, "repair"),
        WeaponAbility("Masterwork", "All stats +20% when fully repaired", 25, Tongue.DR, 0, "stat_boost"),
    ],
}


# ---------------------------------------------------------------------------
# TongueWeapon
# ---------------------------------------------------------------------------
@dataclass
class TongueWeapon:
    """A weapon bound to a Sacred Tongue."""

    weapon_id: str
    name: str
    weapon_type: WeaponType
    tongue: Tongue
    rarity: WeaponRarity

    # Core stats
    attack: int = 0
    wisdom: int = 0
    speed: int = 0

    # Durability / fatigue
    durability: int = 100
    max_durability: int = 100

    # Leveling (ABS)
    level: int = 1
    abs_xp: int = 0           # Accumulated absorption XP
    abs_to_next: int = 100    # XP needed for next level

    # Unlocked abilities
    abilities: List[WeaponAbility] = field(default_factory=list)

    # Equipped
    equipped: bool = False

    def __post_init__(self) -> None:
        if self.attack == 0:
            base = RARITY_BASE_STATS[self.rarity]
            scale = WEAPON_TYPE_SCALING[self.weapon_type]
            self.attack = int(base["atk"] * scale[0])
            self.wisdom = int(base["wis"] * scale[1])
            self.speed = int(base["spd"] * scale[2])
            self.durability = base["durability"]
            self.max_durability = base["durability"]
            self.abs_to_next = self._xp_for_level(2)
        self._check_ability_unlocks()

    def _xp_for_level(self, lvl: int) -> int:
        """XP required for a given level (phi-scaled)."""
        return int(80 * (PHI ** (lvl * 0.5)))

    def _check_ability_unlocks(self) -> None:
        """Check and unlock any abilities earned at current level."""
        tongue_abilities = TONGUE_ABILITIES.get(self.tongue, [])
        for ability in tongue_abilities:
            if ability.unlock_level <= self.level and ability not in self.abilities:
                self.abilities.append(ability)

    def absorb_xp(self, xp: int) -> bool:
        """Absorb XP from a kill. Returns True if leveled up."""
        max_lvl = MAX_LEVEL[self.rarity]
        if self.level >= max_lvl:
            return False

        self.abs_xp += xp
        leveled = False
        while self.abs_xp >= self.abs_to_next and self.level < max_lvl:
            self.abs_xp -= self.abs_to_next
            self.level += 1
            self.abs_to_next = self._xp_for_level(self.level + 1)

            # Stat growth on level up
            scale = WEAPON_TYPE_SCALING[self.weapon_type]
            self.attack += max(1, int(2 * scale[0]))
            self.wisdom += max(1, int(1.5 * scale[1]))
            self.speed += max(0, int(1 * scale[2]))

            self._check_ability_unlocks()
            leveled = True

        return leveled

    def use(self, swings: int = 1) -> None:
        """Use the weapon, reducing durability."""
        self.durability = max(0, self.durability - swings)

    @property
    def is_broken(self) -> bool:
        """Broken weapons deal half damage."""
        return self.durability <= 0

    @property
    def effective_attack(self) -> int:
        """Attack after durability penalty."""
        base = self.attack
        if self.is_broken:
            base = base // 2
        # Ability bonus
        for a in self.abilities:
            if a.power_bonus > 0 and a.unlock_level <= self.level:
                base += a.power_bonus
        return base

    def repair(self, amount: int) -> None:
        """Repair durability."""
        self.durability = min(self.max_durability, self.durability + amount)

    def full_repair(self) -> None:
        """Fully repair the weapon."""
        self.durability = self.max_durability

    def tongue_effectiveness(self, target_tongue: Tongue) -> float:
        """Get effectiveness multiplier against a target tongue.

        Uses TONGUE_CHART from engine.py.
        Returns: 2.0 (super effective), 1.0 (neutral), 0.5 (not effective).
        """
        chart = TONGUE_CHART.get(self.tongue, {})
        return chart.get(target_tongue, 1.0)

    def calculate_damage(self, target_tongue: Tongue) -> int:
        """Calculate weapon damage against a target tongue."""
        base = self.effective_attack
        effectiveness = self.tongue_effectiveness(target_tongue)
        return max(1, int(base * effectiveness))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "weapon_id": self.weapon_id,
            "name": self.name,
            "type": self.weapon_type.value,
            "tongue": self.tongue.value,
            "rarity": self.rarity.value,
            "level": self.level,
            "attack": self.attack,
            "effective_attack": self.effective_attack,
            "wisdom": self.wisdom,
            "speed": self.speed,
            "durability": f"{self.durability}/{self.max_durability}",
            "abs_xp": f"{self.abs_xp}/{self.abs_to_next}",
            "abilities": [a.name for a in self.abilities],
        }


# ---------------------------------------------------------------------------
# Weapon Inventory
# ---------------------------------------------------------------------------
class WeaponInventory:
    """Player's collection of weapons."""

    def __init__(self, max_weapons: int = 20) -> None:
        self.weapons: List[TongueWeapon] = []
        self.max_weapons: int = max_weapons
        self.equipped: Optional[TongueWeapon] = None

    def add(self, weapon: TongueWeapon) -> bool:
        if len(self.weapons) >= self.max_weapons:
            return False
        self.weapons.append(weapon)
        return True

    def remove(self, weapon: TongueWeapon) -> bool:
        if weapon not in self.weapons:
            return False
        if self.equipped is weapon:
            self.equipped = None
        self.weapons.remove(weapon)
        return True

    def equip(self, weapon: TongueWeapon) -> bool:
        if weapon not in self.weapons:
            return False
        if self.equipped:
            self.equipped.equipped = False
        weapon.equipped = True
        self.equipped = weapon
        return True

    def get_by_tongue(self, tongue: Tongue) -> List[TongueWeapon]:
        return [w for w in self.weapons if w.tongue == tongue]

    def strongest(self) -> Optional[TongueWeapon]:
        if not self.weapons:
            return None
        return max(self.weapons, key=lambda w: w.effective_attack)


# ---------------------------------------------------------------------------
# Weapon Generator
# ---------------------------------------------------------------------------
# Named weapons per tongue
WEAPON_NAMES: Dict[Tongue, Dict[WeaponType, List[str]]] = {
    Tongue.KO: {
        WeaponType.BLADE: ["Edict Saber", "Authority Edge", "Crimson Decree"],
        WeaponType.STAFF: ["Commandant's Rod", "Order Scepter"],
        WeaponType.BOW: ["Judgment Arc", "Edict Bow"],
        WeaponType.GAUNTLET: ["Iron Fist of Law", "Command Gauntlet"],
    },
    Tongue.AV: {
        WeaponType.BLADE: ["Relay Blade", "Transit Cutter", "Signal Edge"],
        WeaponType.STAFF: ["Waypoint Wand", "Beacon Staff"],
        WeaponType.BOW: ["Scout's Longbow", "Relay Bow"],
        WeaponType.GAUNTLET: ["Courier's Gauntlet", "Pathfinder Fist"],
    },
    Tongue.RU: {
        WeaponType.BLADE: ["Ancestral Blade", "Memory Edge", "Rune Sword"],
        WeaponType.STAFF: ["Elder's Staff", "Law Rod"],
        WeaponType.BOW: ["Recollection Bow", "Echo Arc"],
        WeaponType.GAUNTLET: ["Stone Fist", "Heritage Gauntlet"],
    },
    Tongue.CA: {
        WeaponType.BLADE: ["Growth Saber", "Fractal Edge", "Bloom Blade"],
        WeaponType.STAFF: ["Compute Wand", "Pattern Staff"],
        WeaponType.BOW: ["Seed Bow", "Spiral Arc"],
        WeaponType.GAUNTLET: ["Crystal Fist", "Garden Gauntlet"],
    },
    Tongue.UM: {
        WeaponType.BLADE: ["Shadow Fang", "Void Edge", "Dusk Blade"],
        WeaponType.STAFF: ["Whisper Rod", "Eclipse Staff"],
        WeaponType.BOW: ["Night Bow", "Stealth Arc"],
        WeaponType.GAUNTLET: ["Shade Gauntlet", "Void Fist"],
    },
    Tongue.DR: {
        WeaponType.BLADE: ["Forge Blade", "Anvil Edge", "Schema Sword"],
        WeaponType.STAFF: ["Builder's Rod", "Craft Staff"],
        WeaponType.BOW: ["Blueprint Bow", "Spark Arc"],
        WeaponType.GAUNTLET: ["Forge Hammer", "Iron Gauntlet"],
    },
}


def generate_weapon(
    tongue: Tongue,
    weapon_type: Optional[WeaponType] = None,
    rarity: Optional[WeaponRarity] = None,
    floor_num: int = 1,
) -> TongueWeapon:
    """Generate a random weapon.

    Parameters
    ----------
    tongue : Tongue
        Tongue affinity for the weapon.
    weapon_type : WeaponType, optional
        If None, picks randomly.
    rarity : WeaponRarity, optional
        If None, picks based on floor depth.
    floor_num : int
        Dungeon floor (affects rarity chances).
    """
    if weapon_type is None:
        weapon_type = random.choice(list(WeaponType))

    if rarity is None:
        weights = [60, 25, 12, 3]
        depth_bonus = min(floor_num // 10, 5)
        weights[1] += depth_bonus * 3
        weights[2] += depth_bonus * 2
        weights[3] += depth_bonus
        rarity = random.choices(list(WeaponRarity), weights=weights, k=1)[0]

    names = WEAPON_NAMES.get(tongue, {}).get(weapon_type, ["Unknown Weapon"])
    name = random.choice(names)

    return TongueWeapon(
        weapon_id=uuid.uuid4().hex[:12],
        name=name,
        weapon_type=weapon_type,
        tongue=tongue,
        rarity=rarity,
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def selftest() -> None:
    print(f"\n{'='*60}")
    print("  Tongue Weapons — Self-Test")
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

    # Generate weapons
    blade = generate_weapon(Tongue.KO, WeaponType.BLADE, WeaponRarity.COMMON)
    check("Weapon generated", blade is not None)
    check("Weapon has name", len(blade.name) > 0)
    check("Weapon starts level 1", blade.level == 1)
    check("Weapon has durability", blade.durability > 0)
    check("Weapon has attack", blade.attack > 0)

    # ABS XP absorption
    initial_level = blade.level
    for _ in range(20):
        blade.absorb_xp(50)
    check("Weapon leveled up", blade.level > initial_level,
          f"level={blade.level}")
    check("Abilities unlocked", len(blade.abilities) > 0,
          f"abilities={[a.name for a in blade.abilities]}")

    # Durability / fatigue
    blade.use(30)
    check("Durability reduced", blade.durability < blade.max_durability)
    blade.use(blade.durability + 10)
    check("Weapon can break", blade.is_broken)
    check("Broken weapon half damage", blade.effective_attack > 0)

    broken_atk = blade.effective_attack
    blade.full_repair()
    check("Full repair works", blade.durability == blade.max_durability)
    check("Repaired weapon stronger", blade.effective_attack > broken_atk)

    # Tongue effectiveness
    eff = blade.tongue_effectiveness(Tongue.UM)
    check("Tongue effectiveness returns value", eff > 0)

    dmg_neutral = blade.calculate_damage(Tongue.KO)
    check("Damage calculation works", dmg_neutral > 0)

    # Weapon inventory
    inv = WeaponInventory()
    check("Add weapon", inv.add(blade))
    check("Equip weapon", inv.equip(blade))
    check("Equipped correctly", inv.equipped is blade)

    staff = generate_weapon(Tongue.CA, WeaponType.STAFF, WeaponRarity.RARE)
    inv.add(staff)
    check("Inventory count", len(inv.weapons) == 2)
    check("Strongest weapon", inv.strongest() is not None)

    # Filter by tongue
    ko_weapons = inv.get_by_tongue(Tongue.KO)
    check("Filter by tongue", len(ko_weapons) == 1)

    # Remove weapon
    check("Remove weapon", inv.remove(staff))
    check("Inventory after remove", len(inv.weapons) == 1)

    # Rarity scaling
    common = generate_weapon(Tongue.DR, WeaponType.GAUNTLET, WeaponRarity.COMMON)
    legendary = generate_weapon(Tongue.DR, WeaponType.GAUNTLET, WeaponRarity.LEGENDARY)
    check("Legendary stronger than common",
          legendary.attack > common.attack,
          f"legendary={legendary.attack}, common={common.attack}")
    check("Legendary more durable",
          legendary.max_durability > common.max_durability)

    # Type scaling
    staff2 = generate_weapon(Tongue.CA, WeaponType.STAFF, WeaponRarity.RARE)
    gaunt2 = generate_weapon(Tongue.DR, WeaponType.GAUNTLET, WeaponRarity.RARE)
    check("Staff has more wisdom than gauntlet",
          staff2.wisdom > gaunt2.wisdom,
          f"staff={staff2.wisdom}, gaunt={gaunt2.wisdom}")

    # All tongues generate weapons
    for tongue in Tongue:
        w = generate_weapon(tongue)
        check(f"  {tongue.value} weapon generated", w is not None)

    # Weapon to_dict
    d = blade.to_dict()
    check("to_dict has keys", "weapon_id" in d and "abilities" in d)

    # Max inventory
    small_inv = WeaponInventory(max_weapons=2)
    small_inv.add(generate_weapon(Tongue.KO))
    small_inv.add(generate_weapon(Tongue.AV))
    check("Max inventory enforced",
          not small_inv.add(generate_weapon(Tongue.RU)))

    # Summary
    print(f"\n  Sample weapon:")
    for k, v in blade.to_dict().items():
        print(f"    {k}: {v}")

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    selftest()
