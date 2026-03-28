"""Gacha Squad — 6-Tongue squad with gravitational alignment in M4 manifold.

Squad Hierarchy (ternary):
    LEADER (+1,+1):  Player's custom-trained model, sets governance style.
    FOLLOWERS (+1,0) or (0,+1):  Specialize per tongue role.
    ENEMIES (-1,-1):  Blocked by Harmonic Wall.

Gravitational alignment pulls squad members toward leader's position
using phi^(-d^2) — closer = stronger bond.

Gacha pull rarity = distance from leader's ideal governance style:
    5-star Legendary  (d < 0.1)
    4-star Epic       (0.1 < d < 0.3)
    3-star Rare       (0.3 < d < 0.5)
    2-star Uncommon   (0.5 < d < 0.7)
    1-star Common     (d > 0.7)
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

PHI = (1 + math.sqrt(5)) / 2


class TernaryAlignment(Enum):
    """Ternary alignment state for squad members."""

    LEADER = (1, 1)
    FOLLOWER_ACTIVE = (1, 0)
    FOLLOWER_PASSIVE = (0, 1)
    NEUTRAL = (0, 0)
    ENEMY = (-1, -1)


class TongueRole(Enum):
    """6-Tongue squad roles mapped to combat style."""

    KO = "Scout"  # Navigation, map awareness, first strike
    AV = "Sniper"  # Long-range sensor, threat detection
    RU = "Support"  # Healing, buffs, resource routing
    CA = "Tank"  # Encryption shield, defense
    UM = "Assassin"  # Stealth, veil, ambush
    DR = "Adjutant"  # Validation, judgment, command relay


# Default follower states per tongue role
TONGUE_FOLLOWER_STATE: Dict[str, TernaryAlignment] = {
    "KO": TernaryAlignment.FOLLOWER_ACTIVE,
    "AV": TernaryAlignment.FOLLOWER_PASSIVE,
    "RU": TernaryAlignment.FOLLOWER_ACTIVE,
    "CA": TernaryAlignment.LEADER,  # Tank mirrors leader
    "UM": TernaryAlignment.FOLLOWER_PASSIVE,
    "DR": TernaryAlignment.LEADER,  # Adjutant mirrors leader
}


@dataclass
class SquadMember:
    """A squad member (follower model) orbiting the leader in M4 manifold."""

    name: str
    tongue: str  # KO, AV, RU, CA, UM, DR
    role: TongueRole
    position: np.ndarray  # 3D position in M4 manifold
    loyalty: float = 0.5  # 0.0 to 1.0
    alignment: TernaryAlignment = TernaryAlignment.FOLLOWER_ACTIVE
    rarity: int = 3  # 1-5 stars
    training_pairs: int = 0  # Accumulated training data

    @property
    def is_active(self) -> bool:
        return self.loyalty > 0.2

    @property
    def combat_bonus(self) -> float:
        """Combat effectiveness scales with loyalty and rarity."""
        return self.loyalty * (1.0 + 0.2 * self.rarity)


@dataclass
class GachaSquad:
    """Player's squad with gravitational alignment dynamics.

    The leader's manifold position attracts squad members — you don't
    train each member separately, the leader shapes the whole squad.
    """

    leader_name: str
    leader_position: np.ndarray = field(default_factory=lambda: np.array([0.5, 0.5, 0.5]))
    members: List[SquadMember] = field(default_factory=list)
    level: int = 1
    max_capacity: int = 6

    def add_member(self, member: SquadMember) -> bool:
        """Add a member to the squad if under capacity."""
        capacity = self._current_capacity()
        if len(self.members) >= capacity:
            logger.warning("Squad at capacity (%d/%d)", len(self.members), capacity)
            return False
        self.members.append(member)
        logger.info(
            "Squad member added: %s (%s, %d-star)",
            member.name,
            member.tongue,
            member.rarity,
        )
        return True

    def gacha_pull(self, seed: Optional[int] = None) -> SquadMember:
        """Perform a gacha pull — rarity based on distance from leader in M4.

        A "legendary" pull perfectly aligns with your governance style.
        A "common" pull needs training grind to catch up.
        """
        rng = random.Random(seed)

        # Random position in manifold
        pos = np.array([rng.gauss(0.5, 0.3) for _ in range(3)])
        pos = np.clip(pos, 0.0, 1.0)

        # Distance from leader determines rarity
        d = float(np.linalg.norm(pos - self.leader_position))
        if d < 0.1:
            rarity, stars = "Legendary", 5
        elif d < 0.3:
            rarity, stars = "Epic", 4
        elif d < 0.5:
            rarity, stars = "Rare", 3
        elif d < 0.7:
            rarity, stars = "Uncommon", 2
        else:
            rarity, stars = "Common", 1

        # Assign tongue role
        tongue_keys = list(TongueRole.__members__.keys())
        tongue = rng.choice(tongue_keys)
        role = TongueRole[tongue]

        # Initial loyalty from alignment proximity
        loyalty = max(0.1, 1.0 - d)

        member = SquadMember(
            name=f"{rarity}_{tongue}_{rng.randint(100,999)}",
            tongue=tongue,
            role=role,
            position=pos,
            loyalty=loyalty,
            alignment=TONGUE_FOLLOWER_STATE.get(tongue, TernaryAlignment.FOLLOWER_ACTIVE),
            rarity=stars,
        )

        logger.info(
            "Gacha pull: %s (%d-star %s, d=%.3f from leader)",
            member.name,
            stars,
            rarity,
            d,
        )
        return member

    def apply_gravitational_step(self) -> None:
        """Move all squad members toward the leader via phi^(-d^2) gravity.

        This is the core mechanic: the leader's governance style
        shapes the entire squad without training each member separately.
        """
        for member in self.members:
            direction = self.leader_position - member.position
            distance = float(np.linalg.norm(direction))
            if distance < 1e-6:
                continue

            # Gravitational strength: phi^(-d^2) — closer = stronger
            gravity = PHI ** (-(distance**2))

            # Move toward leader (bounded by loyalty)
            step = direction * gravity * member.loyalty
            member.position = member.position + step

            # Loyalty grows through alignment
            member.loyalty = min(1.0, member.loyalty + 0.01 * gravity)

        logger.debug("Gravitational step applied to %d members", len(self.members))

    def recruit_defeated(self, enemy_position: np.ndarray, enemy_tongue: str) -> Optional[SquadMember]:
        """Shadow Army mechanic: defeat enemy models -> recruit them.

        Enemy position shifts toward your manifold. Like Sung Jin-Woo's shadows.
        """
        capacity = self._current_capacity()
        if len(self.members) >= capacity:
            return None

        # Shift enemy position halfway toward leader
        new_pos = (enemy_position + self.leader_position) / 2.0
        d = float(np.linalg.norm(new_pos - self.leader_position))
        rarity = max(1, min(5, int(5 - d * 5)))

        role = TongueRole[enemy_tongue] if enemy_tongue in TongueRole.__members__ else TongueRole.KO
        recruit = SquadMember(
            name=f"Shadow_{enemy_tongue}_{random.randint(100,999)}",
            tongue=enemy_tongue,
            role=role,
            position=new_pos,
            loyalty=0.3,  # Low initial loyalty for recruits
            alignment=TernaryAlignment.FOLLOWER_ACTIVE,
            rarity=rarity,
        )
        self.members.append(recruit)
        logger.info("Shadow recruit: %s (%d-star, loyalty=0.3)", recruit.name, rarity)
        return recruit

    def get_formation(self) -> Dict[str, List[str]]:
        """Return squad formation grouped by tongue role."""
        formation: Dict[str, List[str]] = {}
        for m in self.members:
            formation.setdefault(m.tongue, []).append(f"{m.name} ({m.rarity}*)")
        return formation

    def _current_capacity(self) -> int:
        """Squad capacity = phi^(leader_training_pairs / 1000), min 6."""
        # For now use level-based scaling
        if self.level < 10:
            return 6
        elif self.level < 50:
            return 12
        else:
            return int(PHI ** (self.level / 20.0))
