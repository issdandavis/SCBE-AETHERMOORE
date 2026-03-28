"""
Energy Token System — Human Currency → Compute Bridge (Python reference).

Mirrors src/game/energyToken.ts. Three-tier currency architecture:
  1. AI Coins (MMCCL Credits) — internal AI-to-AI barter, zero real value
  2. Energy Tokens (this file) — purchased with real money, spent on compute
  3. Human Currency (Stripe) — real money, standard refund policy

Energy Tokens are NOT cryptocurrency. They are:
  - Non-tradeable, non-withdrawable, non-transferable
  - Consumed on use (like arcade tokens or prepaid server time)

A3: Causality — all purchases and consumption are time-ordered.
A5: Composition — audit trail links Stripe payment → token mint → consumption.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

SECONDS_PER_TOKEN = 60  # 1 token = 1 minute of compute


# ---------------------------------------------------------------------------
#  Token Packages
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenPackage:
    package_id: str
    name: str
    tokens: int
    price_usd: float
    bonus_tokens: int
    description: str


TOKEN_PACKAGES: Tuple[TokenPackage, ...] = (
    TokenPackage("starter", "Starter Pack", 100, 4.99, 0, "100 Energy Tokens — ~5 dungeon runs"),
    TokenPackage(
        "adventurer",
        "Adventurer Pack",
        500,
        19.99,
        50,
        "550 Energy Tokens — ~25 dungeon runs + bonus",
    ),
    TokenPackage(
        "guild",
        "Guild Pack",
        2000,
        49.99,
        400,
        "2400 Energy Tokens — ~100 dungeon runs + bonus",
    ),
    TokenPackage(
        "academy",
        "Academy Semester",
        10000,
        199.99,
        3000,
        "13000 Energy Tokens — full semester of training + bonus",
    ),
)


# ---------------------------------------------------------------------------
#  Activity Costs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActivityCost:
    activity_type: str
    base_cost: int
    description: str


ACTIVITY_COSTS: Dict[str, ActivityCost] = {
    "dungeon_run": ActivityCost("dungeon_run", 20, "Run a dungeon floor (5 encounters + boss)"),
    "tower_floor": ActivityCost("tower_floor", 15, "Attempt one tower floor"),
    "companion_training": ActivityCost("companion_training", 30, "AI fine-tune session for one companion"),
    "fleet_battle": ActivityCost("fleet_battle", 10, "Fleet formation battle"),
    "codex_deep_query": ActivityCost("codex_deep_query", 5, "Extended codex research session"),
    "evolution_ceremony": ActivityCost("evolution_ceremony", 50, "Evolution ceremony with model checkpoint"),
    "world_simulation": ActivityCost("world_simulation", 100, "24h autonomous world simulation tick"),
}


# ---------------------------------------------------------------------------
#  Purchase / Consumption Records
# ---------------------------------------------------------------------------


@dataclass
class PurchaseRecord:
    purchase_id: str
    player_id: str
    package_id: str
    tokens_minted: int
    price_usd: float
    stripe_payment_id: str
    timestamp: float
    status: Literal["completed", "refunded", "disputed"] = "completed"


@dataclass
class ConsumptionRecord:
    consumption_id: str
    player_id: str
    activity_type: str
    tokens_spent: int
    companion_id: Optional[str]
    timestamp: float
    session_id: str
    generated_training_data: bool = False
    hf_dataset_id: Optional[str] = None


# ---------------------------------------------------------------------------
#  Energy Wallet
# ---------------------------------------------------------------------------


class EnergyWallet:
    """Per-player energy token wallet."""

    def __init__(self, player_id: str) -> None:
        self._player_id = player_id
        self._balance: int = 0
        self._total_purchased: int = 0
        self._total_consumed: int = 0
        self._purchases: List[PurchaseRecord] = []
        self._consumptions: List[ConsumptionRecord] = []

    @property
    def player_id(self) -> str:
        return self._player_id

    @property
    def balance(self) -> int:
        return self._balance

    @property
    def total_purchased(self) -> int:
        return self._total_purchased

    @property
    def total_consumed(self) -> int:
        return self._total_consumed

    # ----- Purchase (Stripe → Tokens) -----

    def record_purchase(self, package_id: str, stripe_payment_id: str) -> Optional[PurchaseRecord]:
        pkg = next((p for p in TOKEN_PACKAGES if p.package_id == package_id), None)
        if pkg is None:
            return None

        total_tokens = pkg.tokens + pkg.bonus_tokens

        record = PurchaseRecord(
            purchase_id=f"pur_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            player_id=self._player_id,
            package_id=package_id,
            tokens_minted=total_tokens,
            price_usd=pkg.price_usd,
            stripe_payment_id=stripe_payment_id,
            timestamp=time.time(),
        )

        self._balance += total_tokens
        self._total_purchased += total_tokens
        self._purchases.append(record)
        return record

    # ----- Consumption (Tokens → Compute) -----

    def can_afford(self, activity_type: str) -> bool:
        cost = ACTIVITY_COSTS.get(activity_type)
        if cost is None:
            return False
        return self._balance >= cost.base_cost

    def consume(
        self,
        activity_type: str,
        companion_id: Optional[str],
        session_id: str,
        generated_training_data: bool = False,
        hf_dataset_id: Optional[str] = None,
    ) -> Optional[ConsumptionRecord]:
        cost = ACTIVITY_COSTS.get(activity_type)
        if cost is None:
            return None
        if self._balance < cost.base_cost:
            return None

        record = ConsumptionRecord(
            consumption_id=f"con_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            player_id=self._player_id,
            activity_type=activity_type,
            tokens_spent=cost.base_cost,
            companion_id=companion_id,
            timestamp=time.time(),
            session_id=session_id,
            generated_training_data=generated_training_data,
            hf_dataset_id=hf_dataset_id,
        )

        self._balance -= cost.base_cost
        self._total_consumed += cost.base_cost
        self._consumptions.append(record)
        return record

    # ----- Refund -----

    def process_refund(self, purchase_id: str) -> Tuple[bool, int]:
        purchase = next((p for p in self._purchases if p.purchase_id == purchase_id), None)
        if purchase is None or purchase.status != "completed":
            return (False, 0)

        reclaimable = min(purchase.tokens_minted, self._balance)
        if reclaimable <= 0:
            return (False, 0)

        self._balance -= reclaimable
        purchase.status = "refunded"
        return (True, reclaimable)

    # ----- Queries -----

    def get_purchases(self) -> List[PurchaseRecord]:
        return list(self._purchases)

    def get_consumptions(self) -> List[ConsumptionRecord]:
        return list(self._consumptions)

    def get_training_consumptions(self) -> List[ConsumptionRecord]:
        return [c for c in self._consumptions if c.generated_training_data]

    def compute_hours_purchased(self) -> float:
        return (self._total_purchased * SECONDS_PER_TOKEN) / 3600

    def compute_hours_consumed(self) -> float:
        return (self._total_consumed * SECONDS_PER_TOKEN) / 3600

    def summary(self) -> Dict:
        return {
            "balance": self._balance,
            "total_purchased": self._total_purchased,
            "total_consumed": self._total_consumed,
            "purchase_count": len(self._purchases),
            "activity_count": len(self._consumptions),
            "training_data_generated": sum(1 for c in self._consumptions if c.generated_training_data),
            "compute_hours_remaining": (self._balance * SECONDS_PER_TOKEN) / 3600,
        }
