"""
MMCCL — Compute Exchange Protocol
===================================

Agent-to-agent context/compute exchange using MMCCL credits.

Exchange flow:
1. **Offer**:  Agent A posts an offer (I have GPU compute, want context credits)
2. **Match**:  Agent B accepts (I have credits, want your compute)
3. **Escrow**: Both parties lock credits in BitLocker vaults
4. **Execute**: Compute/context is delivered
5. **Settle**: Credits transfer, vaults release

This is NOT a public cryptocurrency exchange.  It is an internal compute
barter protocol between AI agents in the SCBE network.  No SEC implications
because credits represent compute receipts, not investment contracts.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .credit import ContextCredit, Denomination, DENOMINATION_WEIGHTS
from .bitlocker import BitLockerVault, VaultRegistry, VaultState
from .ledger import ContextLedger


# ---------------------------------------------------------------------------
#  Exchange types
# ---------------------------------------------------------------------------

class OfferType(str, Enum):
    """What an agent is offering."""
    COMPUTE = "COMPUTE"         # GPU/CPU cycles
    CONTEXT = "CONTEXT"         # Pre-computed context windows
    INFERENCE = "INFERENCE"     # Model inference calls
    STORAGE = "STORAGE"         # Context storage capacity
    GOVERNANCE = "GOVERNANCE"   # Governance validation services


class ExchangeState(str, Enum):
    """Lifecycle of an exchange."""
    POSTED = "POSTED"           # Offer posted, waiting for match
    MATCHED = "MATCHED"         # Both parties agreed
    ESCROWED = "ESCROWED"       # Credits locked in vaults
    EXECUTING = "EXECUTING"     # Compute/context being delivered
    SETTLED = "SETTLED"         # Credits transferred, complete
    DISPUTED = "DISPUTED"       # One party claims non-delivery
    CANCELLED = "CANCELLED"     # Cancelled before execution
    EXPIRED = "EXPIRED"         # Timed out


# ---------------------------------------------------------------------------
#  Exchange Offer
# ---------------------------------------------------------------------------

@dataclass
class ExchangeOffer:
    """An offer to trade compute/context for credits."""

    offer_id: str = ""
    offerer_id: str = ""             # Agent making the offer
    offer_type: OfferType = OfferType.COMPUTE
    denomination: Denomination = Denomination.KO  # Preferred payment tongue

    # What's being offered
    description: str = ""            # Human-readable description
    capacity: float = 0.0            # Units of compute/context offered
    unit: str = "tokens"             # Unit of measurement

    # Price
    asking_price: float = 0.0        # Credits requested
    min_price: float = 0.0           # Floor price for negotiation

    # Timing
    created_at: float = 0.0
    expires_at: float = 0.0          # When the offer expires

    state: ExchangeState = ExchangeState.POSTED

    def __post_init__(self):
        if not self.offer_id:
            self.offer_id = str(uuid.uuid4())[:12]
        if not self.created_at:
            self.created_at = time.time()
        if not self.expires_at:
            self.expires_at = self.created_at + 3600  # 1 hour default

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "offerer_id": self.offerer_id,
            "offer_type": self.offer_type.value,
            "denomination": self.denomination.value,
            "description": self.description,
            "capacity": self.capacity,
            "unit": self.unit,
            "asking_price": round(self.asking_price, 6),
            "min_price": round(self.min_price, 6),
            "state": self.state.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


# ---------------------------------------------------------------------------
#  Exchange Transaction
# ---------------------------------------------------------------------------

@dataclass
class ExchangeTransaction:
    """A matched exchange between two agents."""

    tx_id: str = ""
    offer: Optional[ExchangeOffer] = None
    buyer_id: str = ""               # Agent accepting the offer
    agreed_price: float = 0.0        # Negotiated price

    # Vault references
    buyer_vault_id: str = ""         # Buyer's escrow vault
    seller_vault_id: str = ""        # Seller's escrow vault (if applicable)

    # State
    state: ExchangeState = ExchangeState.MATCHED
    created_at: float = 0.0
    settled_at: float = 0.0

    # Delivery proof
    delivery_hash: str = ""          # Hash of delivered compute/context

    def __post_init__(self):
        if not self.tx_id:
            self.tx_id = str(uuid.uuid4())[:16]
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "offer_id": self.offer.offer_id if self.offer else "",
            "seller_id": self.offer.offerer_id if self.offer else "",
            "buyer_id": self.buyer_id,
            "offer_type": self.offer.offer_type.value if self.offer else "",
            "agreed_price": round(self.agreed_price, 6),
            "state": self.state.value,
            "buyer_vault_id": self.buyer_vault_id,
            "seller_vault_id": self.seller_vault_id,
            "delivery_hash": self.delivery_hash,
            "created_at": self.created_at,
            "settled_at": self.settled_at,
        }


# ---------------------------------------------------------------------------
#  Compute Exchange — the market
# ---------------------------------------------------------------------------

class ComputeExchange:
    """
    Decentralized compute exchange for AI agents.

    Usage::

        exchange = ComputeExchange(ledger=ledger, vaults=vault_registry)

        # Agent A offers compute
        offer = exchange.post_offer(
            offerer_id="gpu-agent",
            offer_type="COMPUTE",
            description="100K tokens of Qwen3-8B inference",
            capacity=100_000,
            asking_price=5.0,
        )

        # Agent B accepts
        tx = exchange.accept_offer(offer.offer_id, buyer_id="researcher-agent")

        # Agent B escrows payment
        exchange.escrow_payment(tx.tx_id, credits=[credit1, credit2])

        # Agent A delivers compute
        exchange.confirm_delivery(tx.tx_id, delivery_hash="sha256-of-output")

        # Auto-settles: credits transfer from buyer vault to seller
    """

    def __init__(
        self,
        ledger: Optional[ContextLedger] = None,
        vaults: Optional[VaultRegistry] = None,
    ) -> None:
        self.ledger = ledger or ContextLedger()
        self.vaults = vaults or VaultRegistry()
        self._offers: Dict[str, ExchangeOffer] = {}
        self._transactions: Dict[str, ExchangeTransaction] = {}

    # -- Offers --------------------------------------------------------------

    def post_offer(
        self,
        offerer_id: str,
        offer_type: str,
        description: str = "",
        capacity: float = 0.0,
        unit: str = "tokens",
        asking_price: float = 1.0,
        min_price: float = 0.0,
        denomination: str = "KO",
        ttl: float = 3600.0,
    ) -> ExchangeOffer:
        """Post a new compute/context offer to the exchange."""
        offer = ExchangeOffer(
            offerer_id=offerer_id,
            offer_type=OfferType(offer_type),
            denomination=Denomination(denomination),
            description=description,
            capacity=capacity,
            unit=unit,
            asking_price=asking_price,
            min_price=min_price or asking_price * 0.8,
            expires_at=time.time() + ttl,
        )
        self._offers[offer.offer_id] = offer
        return offer

    def cancel_offer(self, offer_id: str) -> None:
        offer = self._offers.get(offer_id)
        if offer and offer.state == ExchangeState.POSTED:
            offer.state = ExchangeState.CANCELLED

    def list_offers(
        self,
        offer_type: Optional[str] = None,
        denomination: Optional[str] = None,
        max_price: Optional[float] = None,
    ) -> List[ExchangeOffer]:
        """List active offers, optionally filtered."""
        results = []
        for offer in self._offers.values():
            if offer.is_expired:
                offer.state = ExchangeState.EXPIRED
                continue
            if offer.state != ExchangeState.POSTED:
                continue
            if offer_type and offer.offer_type.value != offer_type:
                continue
            if denomination and offer.denomination.value != denomination:
                continue
            if max_price is not None and offer.asking_price > max_price:
                continue
            results.append(offer)
        return sorted(results, key=lambda o: o.asking_price)

    # -- Accept / Match ------------------------------------------------------

    def accept_offer(
        self,
        offer_id: str,
        buyer_id: str,
        bid_price: Optional[float] = None,
    ) -> ExchangeTransaction:
        """Accept an offer, creating an exchange transaction."""
        offer = self._offers.get(offer_id)
        if not offer:
            raise ValueError(f"Offer {offer_id} not found")
        if offer.state != ExchangeState.POSTED:
            raise ValueError(f"Offer {offer_id} is {offer.state.value}")
        if offer.is_expired:
            offer.state = ExchangeState.EXPIRED
            raise ValueError(f"Offer {offer_id} has expired")
        if buyer_id == offer.offerer_id:
            raise ValueError("Cannot accept your own offer")

        price = bid_price if bid_price is not None else offer.asking_price
        if price < offer.min_price:
            raise ValueError(
                f"Bid {price:.4f} below minimum {offer.min_price:.4f}"
            )

        offer.state = ExchangeState.MATCHED

        tx = ExchangeTransaction(
            offer=offer,
            buyer_id=buyer_id,
            agreed_price=price,
        )
        self._transactions[tx.tx_id] = tx
        return tx

    # -- Escrow --------------------------------------------------------------

    def escrow_payment(
        self,
        tx_id: str,
        credits: List[ContextCredit],
    ) -> str:
        """Buyer locks credits in escrow vault for the transaction."""
        tx = self._transactions.get(tx_id)
        if not tx:
            raise ValueError(f"Transaction {tx_id} not found")
        if tx.state != ExchangeState.MATCHED:
            raise ValueError(f"Transaction in wrong state: {tx.state.value}")

        # Verify credit value covers agreed price
        total = sum(c.face_value for c in credits)
        if total < tx.agreed_price * 0.95:  # 5% tolerance
            raise ValueError(
                f"Escrowed value {total:.4f} insufficient for price {tx.agreed_price:.4f}"
            )

        # Create and lock vault
        vault = self.vaults.create_vault(owner_id=tx.buyer_id)
        vault.deposit_many(credits)
        vault.lock(expires_in=600.0)  # 10 min escrow timeout
        vault.escrow_for(
            counterparty_id=tx.offer.offerer_id,
            timeout=600.0,
        )

        tx.buyer_vault_id = vault.vault_id
        tx.state = ExchangeState.ESCROWED
        return vault.vault_id

    # -- Delivery & Settlement -----------------------------------------------

    def confirm_delivery(self, tx_id: str, delivery_hash: str = "") -> None:
        """
        Seller confirms compute/context was delivered.
        Triggers settlement — credits transfer to seller.
        """
        tx = self._transactions.get(tx_id)
        if not tx:
            raise ValueError(f"Transaction {tx_id} not found")
        if tx.state != ExchangeState.ESCROWED:
            raise ValueError(f"Transaction in wrong state: {tx.state.value}")

        tx.delivery_hash = delivery_hash or hashlib.sha256(
            f"{tx.tx_id}:{time.time()}".encode()
        ).hexdigest()
        tx.state = ExchangeState.EXECUTING

        # Auto-settle: release escrow to seller
        self._settle(tx)

    def _settle(self, tx: ExchangeTransaction) -> None:
        """Transfer credits from buyer's escrow to seller."""
        vault = self.vaults.get_vault(tx.buyer_vault_id)
        if not vault:
            tx.state = ExchangeState.DISPUTED
            return

        # Unlock and retrieve credits
        try:
            credit_data = vault.unlock(owner_id=tx.offer.offerer_id)
        except (PermissionError, ValueError):
            tx.state = ExchangeState.DISPUTED
            return

        tx.state = ExchangeState.SETTLED
        tx.settled_at = time.time()
        tx.offer.state = ExchangeState.SETTLED

    def dispute(self, tx_id: str, reason: str = "") -> None:
        """Flag a transaction as disputed."""
        tx = self._transactions.get(tx_id)
        if tx:
            tx.state = ExchangeState.DISPUTED

    # -- Query API -----------------------------------------------------------

    def get_transaction(self, tx_id: str) -> Optional[ExchangeTransaction]:
        return self._transactions.get(tx_id)

    def transactions_by_agent(self, agent_id: str) -> List[ExchangeTransaction]:
        return [
            tx for tx in self._transactions.values()
            if tx.buyer_id == agent_id
            or (tx.offer and tx.offer.offerer_id == agent_id)
        ]

    def exchange_rate(self, from_denom: str, to_denom: str) -> float:
        """
        Cross-denomination exchange rate based on golden ratio weights.

        rate = weight(from) / weight(to)
        """
        w_from = DENOMINATION_WEIGHTS.get(Denomination(from_denom), 1.0)
        w_to = DENOMINATION_WEIGHTS.get(Denomination(to_denom), 1.0)
        return w_from / w_to

    def summary(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = {}
        total_volume = 0.0
        for tx in self._transactions.values():
            by_state[tx.state.value] = by_state.get(tx.state.value, 0) + 1
            if tx.state == ExchangeState.SETTLED:
                total_volume += tx.agreed_price

        return {
            "total_offers": len(self._offers),
            "active_offers": len(self.list_offers()),
            "total_transactions": len(self._transactions),
            "by_state": by_state,
            "total_volume_settled": round(total_volume, 6),
            "exchange_rates": {
                f"{d1.value}/{d2.value}": round(
                    DENOMINATION_WEIGHTS[d1] / DENOMINATION_WEIGHTS[d2], 4
                )
                for d1 in Denomination
                for d2 in Denomination
                if d1 != d2 and d1.value < d2.value
            },
        }
