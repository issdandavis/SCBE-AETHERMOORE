"""
Earn Engine — Stream Definitions
==================================
Each revenue source in the SCBE economy is modeled as an EarnStream.
Streams classify events by source, assign tongue denominations, and
carry governance parameters for credit minting.

Four stream types:
  GAME     — Battle victories, catches, evolutions, milestones
  CONTENT  — Published posts, articles, training data contributions
  SHOPIFY  — Product sales, digital downloads, subscriptions
  TRAINING — SFT/DPO pair generation, model fine-tuning runs
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..context_credit_ledger.credit import Denomination


# ---------------------------------------------------------------------------
#  Stream Types
# ---------------------------------------------------------------------------

class StreamType(str, Enum):
    GAME = "GAME"
    CONTENT = "CONTENT"
    SHOPIFY = "SHOPIFY"
    TRAINING = "TRAINING"


# ---------------------------------------------------------------------------
#  Governance Verdict (mirrors L13 decision gate)
# ---------------------------------------------------------------------------

class GovernanceVerdict(str, Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


# ---------------------------------------------------------------------------
#  Earn Event — a single thing that happened that can mint credits
# ---------------------------------------------------------------------------

@dataclass
class EarnEvent:
    """A raw event from any earn stream, before governance processing."""

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    stream_type: StreamType = StreamType.GAME
    event_name: str = ""              # e.g. "battle_victory", "post_published"
    denomination: Denomination = Denomination.KO
    base_reward: float = 10.0         # pre-governance reward amount
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    # Governance inputs (fed to harmonic wall)
    hamiltonian_d: float = 0.1        # deviation from safe center
    hamiltonian_pd: float = 0.05      # policy deviation

    # Agent that triggered the event
    agent_id: str = "player"
    model_name: str = "aethermoor-game"


# ---------------------------------------------------------------------------
#  Stream Configs — default parameters per stream type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StreamConfig:
    """Configuration for an earn stream."""
    stream_type: StreamType
    default_denomination: Denomination
    base_multiplier: float            # reward multiplier
    max_hamiltonian_d: float          # above this -> QUARANTINE
    max_hamiltonian_pd: float         # above this -> DENY
    description: str = ""


STREAM_CONFIGS: Dict[StreamType, StreamConfig] = {
    StreamType.GAME: StreamConfig(
        stream_type=StreamType.GAME,
        default_denomination=Denomination.KO,
        base_multiplier=1.0,
        max_hamiltonian_d=0.5,
        max_hamiltonian_pd=0.3,
        description="In-game events: battles, catches, evolutions",
    ),
    StreamType.CONTENT: StreamConfig(
        stream_type=StreamType.CONTENT,
        default_denomination=Denomination.AV,
        base_multiplier=2.0,
        max_hamiltonian_d=0.4,
        max_hamiltonian_pd=0.2,
        description="Published content across platforms",
    ),
    StreamType.SHOPIFY: StreamConfig(
        stream_type=StreamType.SHOPIFY,
        default_denomination=Denomination.CA,
        base_multiplier=5.0,
        max_hamiltonian_d=0.3,
        max_hamiltonian_pd=0.15,
        description="Shopify product sales and subscriptions",
    ),
    StreamType.TRAINING: StreamConfig(
        stream_type=StreamType.TRAINING,
        default_denomination=Denomination.DR,
        base_multiplier=3.0,
        max_hamiltonian_d=0.35,
        max_hamiltonian_pd=0.2,
        description="SFT/DPO training data contributions",
    ),
}


# ---------------------------------------------------------------------------
#  Game Event Subtypes — specific in-game actions
# ---------------------------------------------------------------------------

class GameEventType(str, Enum):
    BATTLE_VICTORY = "battle_victory"
    CREATURE_CAUGHT = "creature_caught"
    EVOLUTION = "evolution"
    LEVEL_UP = "level_up"
    MILESTONE = "milestone"
    BESTIARY_COMPLETE = "bestiary_complete"
    SHOPIFY_PURCHASE = "shopify_purchase"  # in-game Shopify buy


# Default rewards per game event
GAME_EVENT_REWARDS: Dict[GameEventType, float] = {
    GameEventType.BATTLE_VICTORY: 10.0,
    GameEventType.CREATURE_CAUGHT: 25.0,
    GameEventType.EVOLUTION: 50.0,
    GameEventType.LEVEL_UP: 15.0,
    GameEventType.MILESTONE: 100.0,
    GameEventType.BESTIARY_COMPLETE: 500.0,
    GameEventType.SHOPIFY_PURCHASE: 0.0,  # no credit mint — real money spent
}

# Tongue mapping for game events (which tongue denominates the credit)
GAME_EVENT_TONGUE: Dict[GameEventType, Denomination] = {
    GameEventType.BATTLE_VICTORY: Denomination.KO,
    GameEventType.CREATURE_CAUGHT: Denomination.AV,
    GameEventType.EVOLUTION: Denomination.DR,
    GameEventType.LEVEL_UP: Denomination.CA,
    GameEventType.MILESTONE: Denomination.UM,
    GameEventType.BESTIARY_COMPLETE: Denomination.DR,
    GameEventType.SHOPIFY_PURCHASE: Denomination.CA,
}
