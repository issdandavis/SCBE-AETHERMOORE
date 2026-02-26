"""
MMCCL — Merkle Tree Ledger (Blockchain)
=========================================

Immutable chain of context credit events.  Each block contains:
- A batch of ContextCredits minted/transferred/spent
- Merkle root of the credit hashes
- Previous block hash (chain integrity)
- Governance summary (aggregate H(d,pd) for the block)
- Timestamp + validator signature

The chain is append-only.  Forks are resolved by longest-chain + highest
aggregate Hamiltonian energy (proof-of-context > proof-of-work).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .credit import ContextCredit


# ---------------------------------------------------------------------------
#  Merkle Tree
# ---------------------------------------------------------------------------

def _merkle_hash(a: str, b: str) -> str:
    return hashlib.sha256((a + b).encode()).hexdigest()


def merkle_root(hashes: List[str]) -> str:
    """Compute Merkle root from a list of hashes."""
    if not hashes:
        return hashlib.sha256(b"empty").hexdigest()
    if len(hashes) == 1:
        return hashes[0]

    # Pad to even
    layer = list(hashes)
    if len(layer) % 2 != 0:
        layer.append(layer[-1])

    while len(layer) > 1:
        next_layer = []
        for i in range(0, len(layer), 2):
            next_layer.append(_merkle_hash(layer[i], layer[i + 1]))
        layer = next_layer

    return layer[0]


# ---------------------------------------------------------------------------
#  Block
# ---------------------------------------------------------------------------

@dataclass
class Block:
    """A block in the context credit blockchain."""

    index: int
    timestamp: float
    credits: List[ContextCredit]
    previous_hash: str
    merkle_root: str = ""
    nonce: int = 0
    validator_id: str = ""

    # Aggregate stats
    total_value: float = 0.0
    total_energy: float = 0.0
    credit_count: int = 0

    def __post_init__(self):
        credit_hashes = [c.block_hash for c in self.credits]
        self.merkle_root = merkle_root(credit_hashes)
        self.credit_count = len(self.credits)
        self.total_value = sum(c.face_value for c in self.credits)
        self.total_energy = sum(c.dna.energy_cost for c in self.credits)

    @property
    def block_hash(self) -> str:
        """Hash of this block (includes merkle root + previous hash)."""
        data = json.dumps({
            "index": self.index,
            "ts": self.timestamp,
            "merkle": self.merkle_root,
            "prev": self.previous_hash,
            "nonce": self.nonce,
            "validator": self.validator_id,
            "value": round(self.total_value, 8),
            "energy": round(self.total_energy, 8),
            "count": self.credit_count,
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "block_hash": self.block_hash,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
            "validator_id": self.validator_id,
            "credit_count": self.credit_count,
            "total_value": round(self.total_value, 8),
            "total_energy": round(self.total_energy, 8),
            "credits": [c.to_dict() for c in self.credits],
        }


# ---------------------------------------------------------------------------
#  Ledger (Blockchain)
# ---------------------------------------------------------------------------

GENESIS_HASH = hashlib.sha256(b"SCBE-AETHERMOORE-MMCCB-GENESIS").hexdigest()


class ContextLedger:
    """
    Append-only blockchain of context credit events.

    Usage::

        ledger = ContextLedger(validator_id="agent-001")
        ledger.add_credits([credit1, credit2])
        ledger.add_credits([credit3])

        assert ledger.verify_chain()
        print(ledger.total_supply())
    """

    def __init__(self, validator_id: str = "scbe-validator") -> None:
        self.validator_id = validator_id
        self._chain: List[Block] = []
        self._pending: List[ContextCredit] = []
        self._credit_index: Dict[str, ContextCredit] = {}  # id → credit

        # Create genesis block
        genesis = Block(
            index=0,
            timestamp=time.time(),
            credits=[],
            previous_hash=GENESIS_HASH,
            validator_id=validator_id,
        )
        self._chain.append(genesis)

    def add_credit(self, credit: ContextCredit) -> None:
        """Add a credit to the pending pool."""
        if credit.credit_id in self._credit_index:
            raise ValueError(f"Duplicate credit: {credit.credit_id}")
        self._pending.append(credit)
        self._credit_index[credit.credit_id] = credit

    def add_credits(self, credits: List[ContextCredit]) -> None:
        """Add multiple credits and mine a new block."""
        for c in credits:
            self.add_credit(c)
        self.mine_block()

    def mine_block(self, difficulty: int = 1) -> Optional[Block]:
        """Mine pending credits into a new block."""
        if not self._pending:
            return None

        prev = self._chain[-1]
        block = Block(
            index=len(self._chain),
            timestamp=time.time(),
            credits=list(self._pending),
            previous_hash=prev.block_hash,
            validator_id=self.validator_id,
        )

        # Simple proof-of-context: find nonce where block hash has prefix zeros
        prefix = "0" * difficulty
        nonce = 0
        while not block.block_hash.startswith(prefix):
            block.nonce = nonce
            nonce += 1
            if nonce > 100_000:
                break

        self._chain.append(block)
        self._pending.clear()
        return block

    def verify_chain(self) -> bool:
        """Verify the entire chain integrity."""
        for i in range(1, len(self._chain)):
            current = self._chain[i]
            previous = self._chain[i - 1]

            # Check previous hash linkage
            if current.previous_hash != previous.block_hash:
                return False

            # Verify merkle root
            credit_hashes = [c.block_hash for c in current.credits]
            expected_merkle = merkle_root(credit_hashes)
            if current.merkle_root != expected_merkle:
                return False

        return True

    def get_credit(self, credit_id: str) -> Optional[ContextCredit]:
        return self._credit_index.get(credit_id)

    def get_block(self, index: int) -> Optional[Block]:
        if 0 <= index < len(self._chain):
            return self._chain[index]
        return None

    # -- Query API -----------------------------------------------------------

    @property
    def chain_length(self) -> int:
        return len(self._chain)

    @property
    def latest_block(self) -> Block:
        return self._chain[-1]

    def total_supply(self) -> float:
        """Total face value of all credits in the chain."""
        return sum(
            c.face_value
            for block in self._chain
            for c in block.credits
        )

    def total_energy_spent(self) -> float:
        """Total Hamiltonian energy consumed across all credits."""
        return sum(
            c.dna.energy_cost
            for block in self._chain
            for c in block.credits
        )

    def credits_by_agent(self, agent_id: str) -> List[ContextCredit]:
        """All credits minted by a specific agent."""
        return [
            c for c in self._credit_index.values()
            if c.dna.agent_id == agent_id
        ]

    def credits_by_denomination(self, denom: str) -> List[ContextCredit]:
        """All credits of a specific denomination."""
        return [
            c for c in self._credit_index.values()
            if c.denomination.value == denom
        ]

    def balance(self, agent_id: str) -> float:
        """Total value of credits owned by an agent."""
        return sum(c.face_value for c in self.credits_by_agent(agent_id))

    def summary(self) -> Dict[str, Any]:
        by_denom: Dict[str, float] = {}
        by_agent: Dict[str, float] = {}
        for c in self._credit_index.values():
            by_denom[c.denomination.value] = by_denom.get(c.denomination.value, 0) + c.face_value
            by_agent[c.dna.agent_id] = by_agent.get(c.dna.agent_id, 0) + c.face_value

        return {
            "chain_length": self.chain_length,
            "total_credits": len(self._credit_index),
            "total_supply": round(self.total_supply(), 6),
            "total_energy": round(self.total_energy_spent(), 6),
            "pending": len(self._pending),
            "by_denomination": {k: round(v, 6) for k, v in by_denom.items()},
            "by_agent": {k: round(v, 6) for k, v in by_agent.items()},
            "chain_valid": self.verify_chain(),
        }
