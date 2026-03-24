"""
Earn Engine — Game Hooks
===========================
Connects game events (battles, catches, evolutions) to the earn engine.

These hooks are designed to be called from demo/battle.py, demo/party.py,
and demo/encounters.py without requiring those modules to import heavy
SCBE dependencies directly.

Usage from game code::

    from earn_engine.game_hooks import GameHooks

    hooks = GameHooks()

    # After a battle victory
    hooks.battle_victory(enemy_name="Hash Slime", enemy_level=12, tongue="CA",
                         xp_gained=120)

    # After catching a creature
    hooks.creature_caught(name="Packet Wraith", level=10, tongue="AV",
                          is_rare=False)

    # After evolution
    hooks.evolution(name="Polly", from_stage="Rookie", to_stage="Champion",
                    tongue="DR")

    # Check earnings
    print(hooks.engine.stats())
"""

from __future__ import annotations

import math
from typing import Dict, Optional

from ..context_credit_ledger.credit import Denomination
from .engine import EarnEngine, LedgerEntry
from .streams import (
    EarnEvent,
    GameEventType,
    GAME_EVENT_REWARDS,
    GAME_EVENT_TONGUE,
    StreamType,
)

PHI = (1 + math.sqrt(5)) / 2


# Tongue string -> Denomination mapping
_TONGUE_TO_DENOM: Dict[str, Denomination] = {
    "KO": Denomination.KO,
    "AV": Denomination.AV,
    "RU": Denomination.RU,
    "CA": Denomination.CA,
    "UM": Denomination.UM,
    "DR": Denomination.DR,
}


class GameHooks:
    """
    Bridge between game events and the earn engine.

    Each method creates an EarnEvent and processes it through
    the governance-gated credit minting pipeline.
    """

    def __init__(
        self,
        engine: Optional[EarnEngine] = None,
        agent_id: str = "player",
    ):
        self.engine = engine or EarnEngine(agent_id=agent_id)
        self._milestone_triggers: Dict[str, bool] = {}

    # --- Core Game Events ---

    def battle_victory(
        self,
        enemy_name: str,
        enemy_level: int,
        tongue: str,
        xp_gained: int = 0,
        player_hp_pct: float = 1.0,
    ) -> LedgerEntry:
        """Called after winning a battle."""
        denom = _TONGUE_TO_DENOM.get(tongue, Denomination.KO)
        base = GAME_EVENT_REWARDS[GameEventType.BATTLE_VICTORY]

        # Scale reward by enemy level and remaining HP
        level_bonus = 1.0 + (enemy_level / 50.0)
        hp_bonus = 0.5 + 0.5 * player_hp_pct  # full HP = 1.0x, half HP = 0.75x
        reward = base * level_bonus * hp_bonus

        event = EarnEvent(
            stream_type=StreamType.GAME,
            event_name=GameEventType.BATTLE_VICTORY.value,
            denomination=denom,
            base_reward=reward,
            hamiltonian_d=0.1,
            hamiltonian_pd=0.05,
            metadata={
                "enemy": enemy_name,
                "enemy_level": enemy_level,
                "tongue": tongue,
                "xp_gained": xp_gained,
                "hp_remaining_pct": round(player_hp_pct, 2),
            },
        )
        return self.engine.process(event)

    def creature_caught(
        self,
        name: str,
        level: int,
        tongue: str,
        is_rare: bool = False,
    ) -> LedgerEntry:
        """Called after catching a wild creature."""
        denom = _TONGUE_TO_DENOM.get(tongue, Denomination.AV)
        base = GAME_EVENT_REWARDS[GameEventType.CREATURE_CAUGHT]

        # Rare creatures are worth more
        rare_mult = PHI if is_rare else 1.0
        reward = base * rare_mult * (1.0 + level / 50.0)

        event = EarnEvent(
            stream_type=StreamType.GAME,
            event_name=GameEventType.CREATURE_CAUGHT.value,
            denomination=denom,
            base_reward=reward,
            hamiltonian_d=0.1,
            hamiltonian_pd=0.03,
            metadata={
                "creature": name,
                "level": level,
                "tongue": tongue,
                "is_rare": is_rare,
            },
        )
        return self.engine.process(event)

    def evolution(
        self,
        name: str,
        from_stage: str,
        to_stage: str,
        tongue: str,
    ) -> LedgerEntry:
        """Called after a creature evolves."""
        denom = _TONGUE_TO_DENOM.get(tongue, Denomination.DR)
        base = GAME_EVENT_REWARDS[GameEventType.EVOLUTION]

        # Higher evolutions are worth more
        stage_values = {
            "Rookie": 1.0,
            "Champion": PHI,
            "Ultimate": PHI**2,
            "Mega": PHI**3,
            "Ultra": PHI**4,
        }
        stage_mult = stage_values.get(to_stage, 1.0)
        reward = base * stage_mult

        event = EarnEvent(
            stream_type=StreamType.GAME,
            event_name=GameEventType.EVOLUTION.value,
            denomination=denom,
            base_reward=reward,
            hamiltonian_d=0.05,
            hamiltonian_pd=0.02,
            metadata={
                "creature": name,
                "from_stage": from_stage,
                "to_stage": to_stage,
                "tongue": tongue,
            },
        )
        return self.engine.process(event)

    def level_up(
        self,
        name: str,
        new_level: int,
        tongue: str,
    ) -> LedgerEntry:
        """Called after a creature levels up."""
        denom = _TONGUE_TO_DENOM.get(tongue, Denomination.CA)
        base = GAME_EVENT_REWARDS[GameEventType.LEVEL_UP]
        reward = base * (1.0 + new_level / 50.0)

        event = EarnEvent(
            stream_type=StreamType.GAME,
            event_name=GameEventType.LEVEL_UP.value,
            denomination=denom,
            base_reward=reward,
            hamiltonian_d=0.05,
            hamiltonian_pd=0.02,
            metadata={
                "creature": name,
                "new_level": new_level,
                "tongue": tongue,
            },
        )
        return self.engine.process(event)

    def milestone(
        self,
        milestone_name: str,
        description: str = "",
    ) -> Optional[LedgerEntry]:
        """Called when a milestone is reached. Each milestone only fires once."""
        if self._milestone_triggers.get(milestone_name):
            return None
        self._milestone_triggers[milestone_name] = True

        event = EarnEvent(
            stream_type=StreamType.GAME,
            event_name=GameEventType.MILESTONE.value,
            denomination=GAME_EVENT_TONGUE[GameEventType.MILESTONE],
            base_reward=GAME_EVENT_REWARDS[GameEventType.MILESTONE],
            hamiltonian_d=0.02,
            hamiltonian_pd=0.01,
            metadata={
                "milestone": milestone_name,
                "description": description,
            },
        )
        return self.engine.process(event)

    def bestiary_complete(self, total_caught: int, total_species: int) -> LedgerEntry:
        """Called when the bestiary is 100% complete."""
        event = EarnEvent(
            stream_type=StreamType.GAME,
            event_name=GameEventType.BESTIARY_COMPLETE.value,
            denomination=Denomination.DR,
            base_reward=GAME_EVENT_REWARDS[GameEventType.BESTIARY_COMPLETE],
            hamiltonian_d=0.01,
            hamiltonian_pd=0.01,
            metadata={
                "total_caught": total_caught,
                "total_species": total_species,
            },
        )
        return self.engine.process(event)

    # --- Shopify In-Game Purchase ---

    def shopify_purchase(
        self,
        product_id: str,
        product_name: str,
        price_cents: int,
        currency: str = "USD",
    ) -> LedgerEntry:
        """
        Called when a player buys a Shopify product from the in-game shop.

        This does NOT mint credits (the player is spending real money).
        Instead it records the purchase for settlement tracking.
        """
        event = EarnEvent(
            stream_type=StreamType.SHOPIFY,
            event_name=GameEventType.SHOPIFY_PURCHASE.value,
            denomination=Denomination.CA,
            base_reward=price_cents / 100.0,  # convert cents to dollars
            hamiltonian_d=0.05,
            hamiltonian_pd=0.02,
            metadata={
                "product_id": product_id,
                "product_name": product_name,
                "price_cents": price_cents,
                "currency": currency,
                "source": "in_game_shop",
            },
        )
        return self.engine.process(event)
