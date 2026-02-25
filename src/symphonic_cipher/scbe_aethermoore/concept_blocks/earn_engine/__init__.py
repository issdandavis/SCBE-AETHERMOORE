"""
Earn Engine — SCBE Revenue Pipeline
=======================================
Governance-gated credit minting from four revenue streams:
  GAME     — Battle victories, catches, evolutions, milestones
  CONTENT  — Published posts across platforms
  SHOPIFY  — Product sales (real + digital) via in-game shop
  TRAINING — SFT/DPO training data contributions

Pipeline:
  Event → Stream → Governance Gate (L13) → MMCCL Credit Mint → Settlement Ledger
"""

from .engine import EarnEngine, LedgerEntry, SettlementState
from .streams import (
    EarnEvent,
    GameEventType,
    GovernanceVerdict,
    StreamConfig,
    StreamType,
    GAME_EVENT_REWARDS,
    GAME_EVENT_TONGUE,
    STREAM_CONFIGS,
)
from .game_hooks import GameHooks
from .shopify_bridge import ShopifyBridge, ShopProduct, CheckoutSession, MOCK_CATALOG
from .publisher_bridge import PublisherBridge, PublishResult

__all__ = [
    # Core
    "EarnEngine",
    "LedgerEntry",
    "SettlementState",
    # Streams
    "EarnEvent",
    "GameEventType",
    "GovernanceVerdict",
    "StreamConfig",
    "StreamType",
    "GAME_EVENT_REWARDS",
    "GAME_EVENT_TONGUE",
    "STREAM_CONFIGS",
    # Game hooks
    "GameHooks",
    # Shopify
    "ShopifyBridge",
    "ShopProduct",
    "CheckoutSession",
    "MOCK_CATALOG",
    # Publisher
    "PublisherBridge",
    "PublishResult",
]
