"""Layer 11: Squad Combat as Code Correction / Math-Monster Debugging.

Combat = debugging actions against digitized system bugs:
    ASSERT_STATE, SANITIZE_INPUT, LOCK_THREAD, FLUSH_CACHE,
    RECOMPILE, ROLLBACK, REFACTOR, ISOLATE_PROCESS

Squad battles validate Hamiltonian paths — squad members must maintain
ds² < threshold along their path. Broken paths = QUARANTINE.

Boss fights = advanced math problems digitized into combat:
    Quadratics, eigenvalues, recurrences, proofs.
    "Dungeon breaks" = adversarial variants (missing assumptions,
    poisoned premises).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

PHI = (1 + math.sqrt(5)) / 2


class DebugAction(Enum):
    """Combat actions = debugging operations."""
    ASSERT_STATE = "assert_state"
    SANITIZE_INPUT = "sanitize_input"
    LOCK_THREAD = "lock_thread"
    FLUSH_CACHE = "flush_cache"
    RECOMPILE = "recompile"
    ROLLBACK = "rollback"
    REFACTOR = "refactor"
    ISOLATE_PROCESS = "isolate_process"


# Debug action effectiveness vs bug types
# Higher = more effective (1.0 = neutral, 1.5 = strong, 0.5 = weak)
ACTION_VS_BUG: Dict[str, Dict[str, float]] = {
    "null_pointer": {
        "assert_state": 1.5, "sanitize_input": 1.2, "rollback": 0.8,
    },
    "float_precision": {
        "flush_cache": 1.5, "recompile": 1.3, "assert_state": 0.7,
    },
    "race_condition": {
        "lock_thread": 1.5, "isolate_process": 1.3, "recompile": 0.8,
    },
    "memory_leak": {
        "flush_cache": 1.5, "isolate_process": 1.2, "lock_thread": 0.7,
    },
    "forked_state": {
        "rollback": 1.5, "refactor": 1.3, "sanitize_input": 0.8,
    },
    "cross_boundary_exploit": {
        "sanitize_input": 1.5, "assert_state": 1.3, "flush_cache": 0.7,
    },
}


@dataclass
class MathMonster:
    """A monster = digitized system bug with math-problem combat.

    Boss fights are math problems: the quadratic coefficients (a, b, c)
    define the Hamiltonian path the bug traverses. Solving = winning.
    """
    name: str
    bug_type: str          # Key into MONSTER_BUG_MAP
    floor: int
    hp: int = 100
    max_hp: int = 100
    attack: int = 10
    # Quadratic coefficients for math-monster
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    is_boss: bool = False

    @property
    def is_defeated(self) -> bool:
        return self.hp <= 0

    @property
    def bug_dict(self) -> Dict[str, float]:
        return {"a": self.a, "b": self.b, "c": self.c, "type": self.bug_type}

    def discriminant(self) -> float:
        """Quadratic discriminant — determines solvability."""
        return self.b ** 2 - 4 * self.a * self.c


@dataclass
class CombatResult:
    """Result of a squad combat encounter."""
    victory: bool
    damage_dealt: int = 0
    damage_taken: int = 0
    math_solved: bool = False
    debug_action: Optional[str] = None
    effectiveness: float = 1.0
    training_pair: Optional[Dict] = None
    ds_squared: float = 0.0


class GachaSquadCombat:
    """Layer 11 combat system: squad battles as Hamiltonian path debugging.

    Squad members must maintain path integrity (ds² < threshold)
    while solving math-monsters. Broken paths trigger QUARANTINE.
    """

    DS_SQUARED_THRESHOLD = 5.0  # Path integrity limit

    def __init__(self):
        self.combat_log: List[Dict] = []

    def create_monster(
        self,
        floor: int,
        bug_type: str = "null_pointer",
        is_boss: bool = False,
    ) -> MathMonster:
        """Create a floor-appropriate monster."""
        # Scale with floor depth
        hp = 50 + floor * 10 + (200 if is_boss else 0)
        attack = 5 + floor * 2 + (15 if is_boss else 0)

        # Math problem coefficients — harder at higher floors
        a = 1.0 + floor * 0.1
        b = -2.0 * floor * 0.3
        c = floor * 0.2

        return MathMonster(
            name=f"{'BOSS: ' if is_boss else ''}{bug_type.replace('_', ' ').title()} Lv.{floor}",
            bug_type=bug_type,
            floor=floor,
            hp=hp,
            max_hp=hp,
            attack=attack,
            a=a,
            b=b,
            c=c,
            is_boss=is_boss,
        )

    def validate_squad_path(
        self,
        squad_states: List[np.ndarray],
    ) -> Tuple[bool, float]:
        """Layer 11: Validate squad Hamiltonian path integrity.

        Each consecutive pair of squad member states must have
        ds² < threshold. Broken path = QUARANTINE.
        """
        if len(squad_states) < 2:
            return True, 0.0

        max_ds2 = 0.0
        for i in range(1, len(squad_states)):
            diff = squad_states[i] - squad_states[i - 1]
            ds2 = float(np.sum(diff * diff))
            max_ds2 = max(max_ds2, ds2)
            if ds2 > self.DS_SQUARED_THRESHOLD:
                logger.warning(
                    "Layer 11 squad path broken: ds2=%.2f > threshold=%.2f",
                    ds2, self.DS_SQUARED_THRESHOLD,
                )
                return False, ds2

        return True, max_ds2

    def solve_math_bug(self, monster: MathMonster) -> bool:
        """Attempt to solve the math-monster's quadratic.

        Returns True if discriminant >= 0 (solvable).
        Boss fights with negative discriminant require special handling.
        """
        disc = monster.discriminant()
        if disc >= 0:
            # Real roots exist — standard solve
            return True
        elif monster.is_boss:
            # Boss with complex roots — need special debug action
            return False
        else:
            # Non-boss with complex roots — partial credit
            return disc > -10.0

    def execute_combat_round(
        self,
        squad_positions: List[np.ndarray],
        monster: MathMonster,
        action: DebugAction,
        attacker_combat_bonus: float = 1.0,
    ) -> CombatResult:
        """Execute one round of squad combat.

        1. Validate squad path integrity.
        2. Calculate debug action effectiveness vs bug type.
        3. Apply damage.
        4. Attempt math solve for bonus damage.
        5. Generate training pair.
        """
        # Step 1: Path integrity
        path_valid, max_ds2 = self.validate_squad_path(squad_positions)
        if not path_valid:
            return CombatResult(
                victory=False,
                ds_squared=max_ds2,
                training_pair={
                    "prompt": f"Squad path broken (ds2={max_ds2:.2f}) vs {monster.name}",
                    "response": "QUARANTINE — squad formation collapsed",
                    "provenance": "gacha_combat_v1",
                },
            )

        # Step 2: Debug action effectiveness
        bug_matchups = ACTION_VS_BUG.get(monster.bug_type, {})
        effectiveness = bug_matchups.get(action.value, 1.0)

        # Step 3: Calculate damage
        base_damage = int(15 * effectiveness * attacker_combat_bonus)
        damage = max(1, base_damage - monster.attack // 4)
        monster.hp -= damage

        # Counter-attack
        counter_damage = max(1, monster.attack - int(attacker_combat_bonus * 3))

        # Step 4: Math solve bonus
        math_solved = self.solve_math_bug(monster)
        if math_solved:
            bonus = int(damage * 0.5)
            monster.hp -= bonus
            damage += bonus

        # Step 5: Generate training pair
        training_pair = {
            "prompt": f"Floor {monster.floor}: {action.value} vs {monster.bug_type} "
                     f"(a={monster.a:.1f}, b={monster.b:.1f}, c={monster.c:.1f})",
            "response": f"Dealt {damage} damage (eff={effectiveness:.1f}, "
                       f"math={'solved' if math_solved else 'unsolved'}). "
                       f"Monster HP: {monster.hp}/{monster.max_hp}",
            "provenance": "gacha_combat_v1",
        }

        result = CombatResult(
            victory=monster.is_defeated,
            damage_dealt=damage,
            damage_taken=counter_damage,
            math_solved=math_solved,
            debug_action=action.value,
            effectiveness=effectiveness,
            training_pair=training_pair,
            ds_squared=max_ds2,
        )

        self.combat_log.append({
            "floor": monster.floor,
            "bug_type": monster.bug_type,
            "action": action.value,
            "damage": damage,
            "effectiveness": effectiveness,
            "victory": result.victory,
        })

        logger.info(
            "Layer 11 combat: %s vs %s — %d dmg (eff=%.1f, math=%s)",
            action.value, monster.name, damage, effectiveness,
            "solved" if math_solved else "unsolved",
        )
        return result
