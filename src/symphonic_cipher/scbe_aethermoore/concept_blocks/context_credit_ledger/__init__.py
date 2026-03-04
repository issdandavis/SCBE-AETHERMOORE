"""
MMCCL — Multi-Model Contextual Credit Ledger
================================================

AI compute exchange protocol backed by context-energy credits.

Modules:
    credit      — ContextCredit, CreditDNA, Denomination, mint_credit
    ledger      — ContextLedger (Merkle-tree blockchain)
    bitlocker   — BitLockerVault, VaultRegistry (PQC-ready escrow)
    exchange    — ComputeExchange, ExchangeOffer, ExchangeTransaction
"""

from .credit import (
    ContextCredit,
    CreditDNA,
    Denomination,
    DENOMINATION_WEIGHTS,
    mint_credit,
)
from .ledger import (
    Block,
    ContextLedger,
    GENESIS_HASH,
    merkle_root,
)
from .bitlocker import (
    BitLockerVault,
    VaultRegistry,
    VaultState,
)
from .exchange import (
    ComputeExchange,
    ExchangeOffer,
    ExchangeTransaction,
    ExchangeState,
    OfferType,
)

__all__ = [
    # Credit
    "ContextCredit",
    "CreditDNA",
    "Denomination",
    "DENOMINATION_WEIGHTS",
    "mint_credit",
    # Ledger
    "Block",
    "ContextLedger",
    "GENESIS_HASH",
    "merkle_root",
    # BitLocker
    "BitLockerVault",
    "VaultRegistry",
    "VaultState",
    # Exchange
    "ComputeExchange",
    "ExchangeOffer",
    "ExchangeTransaction",
    "ExchangeState",
    "OfferType",
]
