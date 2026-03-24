"""
Micro Blockchain Ledger — AI-to-AI Service Trading (Python reference).

Mirrors src/game/microLedger.ts. Integrates with existing MMCCL system
(context_credit_ledger/) for the game module.

Internal-only currency — no real-world value. Tracks services between
AI companion entities: healing, formation buffs, scouting, etc.

A3: Causality — all transactions time-ordered, append-only.
A4: Symmetry — denomination exchange rates obey φ-ratio symmetry.
A5: Composition — chain integrity verified by Merkle root.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

from .types import (
    TONGUE_WEIGHTS,
    TongueCode,
    RiskDecision,
)

# ---------------------------------------------------------------------------
#  Denomination (Sacred Tongue = Currency)
# ---------------------------------------------------------------------------

Denomination = TongueCode
DENOMINATION_WEIGHTS: Dict[Denomination, float] = dict(TONGUE_WEIGHTS)


def exchange_rate(from_denom: Denomination, to_denom: Denomination) -> float:
    """Cross-denomination rate based on golden ratio weights."""
    return DENOMINATION_WEIGHTS[from_denom] / DENOMINATION_WEIGHTS[to_denom]


# ---------------------------------------------------------------------------
#  Service Types
# ---------------------------------------------------------------------------

ServiceType = Literal[
    "healing",
    "formation_buff",
    "scouting",
    "transform_assist",
    "evolution_catalyst",
    "drift_cleanse",
    "codex_query",
    "escort",
    "training",
    "governance_vote",
]

SERVICE_BASE_COSTS: Dict[ServiceType, float] = {
    "healing": 5.0,
    "formation_buff": 3.0,
    "scouting": 2.0,
    "transform_assist": 4.0,
    "evolution_catalyst": 15.0,
    "drift_cleanse": 8.0,
    "codex_query": 1.0,
    "escort": 3.0,
    "training": 6.0,
    "governance_vote": 10.0,
}

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


# ---------------------------------------------------------------------------
#  Credit DNA
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CreditDNA:
    agent_id: str
    species_id: str
    tongue_snapshot: Tuple[float, ...]
    hamiltonian_d: float = 0.0
    hamiltonian_pd: float = 0.0
    governance_verdict: RiskDecision = "ALLOW"

    @property
    def energy_cost(self) -> float:
        """H(d,pd) = 1/(1+d+2*pd)"""
        return 1.0 / (1.0 + self.hamiltonian_d + 2.0 * self.hamiltonian_pd)

    def _sha(self) -> str:
        return _sha256(
            json.dumps(
                {
                    "a": self.agent_id,
                    "s": self.species_id,
                    "t": list(self.tongue_snapshot),
                    "d": self.hamiltonian_d,
                    "pd": self.hamiltonian_pd,
                },
                sort_keys=True,
            )
        )[:16]


# ---------------------------------------------------------------------------
#  Context Credit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextCredit:
    credit_id: str
    denomination: Denomination
    dna: CreditDNA
    payload_hash: str
    parent_credits: Tuple[str, ...]
    timestamp: float
    nonce: int
    legibility: float
    service_type: ServiceType
    summary: str = ""

    @property
    def face_value(self) -> float:
        """value = weight × energy × legibility"""
        weight = DENOMINATION_WEIGHTS[self.denomination]
        return weight * self.dna.energy_cost * self.legibility

    @property
    def block_hash(self) -> str:
        data = json.dumps(
            {
                "id": self.credit_id,
                "denom": self.denomination,
                "payload": self.payload_hash,
                "parents": list(self.parent_credits),
                "ts": self.timestamp,
                "nonce": self.nonce,
                "dna_hash": self.dna._sha(),
                "value": round(self.face_value, 8),
            },
            sort_keys=True,
        )
        return _sha256(data)


# ---------------------------------------------------------------------------
#  Credit Minting
# ---------------------------------------------------------------------------

_credit_counter = 0


def mint_credit(
    agent_id: str,
    species_id: str,
    denomination: Denomination,
    service_type: ServiceType,
    tongue_snapshot: Tuple[float, ...],
    hamiltonian_d: float = 0.0,
    hamiltonian_pd: float = 0.0,
    governance_verdict: RiskDecision = "ALLOW",
    parent_credit_ids: Optional[List[str]] = None,
    legibility: float = 1.0,
    summary: str = "",
    difficulty: int = 1,
) -> ContextCredit:
    """Mint a new credit with proof-of-context."""
    global _credit_counter
    _credit_counter += 1

    dna = CreditDNA(
        agent_id=agent_id,
        species_id=species_id,
        tongue_snapshot=tongue_snapshot,
        hamiltonian_d=hamiltonian_d,
        hamiltonian_pd=hamiltonian_pd,
        governance_verdict=governance_verdict,
    )

    payload_hash = _sha256(f"{agent_id}:{service_type}:{time.time()}:{_credit_counter}")
    credit_id = f"cr_{_sha256(f'{agent_id}:{time.time()}:{_credit_counter}')[:12]}"
    prefix = "0" * difficulty

    for nonce in range(100_000):
        candidate = ContextCredit(
            credit_id=credit_id,
            denomination=denomination,
            dna=dna,
            payload_hash=payload_hash,
            parent_credits=tuple(parent_credit_ids or []),
            timestamp=time.time(),
            nonce=nonce,
            legibility=max(0.0, min(1.0, legibility)),
            service_type=service_type,
            summary=summary,
        )
        if candidate.block_hash.startswith(prefix):
            return candidate

    # Fallback
    return candidate  # type: ignore[possibly-undefined]


# ---------------------------------------------------------------------------
#  Merkle Tree
# ---------------------------------------------------------------------------


def merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return _sha256("empty")
    if len(hashes) == 1:
        return hashes[0]

    layer = list(hashes)
    if len(layer) % 2 != 0:
        layer.append(layer[-1])

    while len(layer) > 1:
        next_layer: List[str] = []
        for i in range(0, len(layer), 2):
            next_layer.append(_sha256(layer[i] + layer[i + 1]))
        layer = next_layer

    return layer[0]


# ---------------------------------------------------------------------------
#  Block
# ---------------------------------------------------------------------------


@dataclass
class Block:
    index: int
    timestamp: float
    credits: List[ContextCredit]
    previous_hash: str
    merkle_root_hash: str = ""
    validator_id: str = ""
    total_value: float = 0.0
    total_energy: float = 0.0
    credit_count: int = 0

    def __post_init__(self) -> None:
        self.merkle_root_hash = merkle_root([c.block_hash for c in self.credits])
        self.credit_count = len(self.credits)
        self.total_value = sum(c.face_value for c in self.credits)
        self.total_energy = sum(c.dna.energy_cost for c in self.credits)

    @property
    def block_hash(self) -> str:
        data = json.dumps(
            {
                "index": self.index,
                "ts": self.timestamp,
                "merkle": self.merkle_root_hash,
                "prev": self.previous_hash,
                "validator": self.validator_id,
                "value": round(self.total_value, 8),
                "energy": round(self.total_energy, 8),
                "count": self.credit_count,
            },
            sort_keys=True,
        )
        return _sha256(data)


# ---------------------------------------------------------------------------
#  Context Ledger (Blockchain)
# ---------------------------------------------------------------------------

GENESIS_HASH = _sha256("SCBE-AETHERMOORE-MMCCB-GENESIS")


class ContextLedger:
    """Append-only blockchain for AI-to-AI service credits."""

    def __init__(self) -> None:
        genesis = Block(
            index=0,
            timestamp=time.time(),
            credits=[],
            previous_hash=GENESIS_HASH,
            validator_id="genesis",
        )
        self._chain: List[Block] = [genesis]
        self._pending: List[ContextCredit] = []
        self._ownership: Dict[str, str] = {}  # credit_id → agent_id

    def add_credit(self, credit: ContextCredit) -> None:
        self._pending.append(credit)
        self._ownership[credit.credit_id] = credit.dna.agent_id

    def mine_block(self, validator_id: str) -> Optional[Block]:
        if not self._pending:
            return None
        prev = self._chain[-1]
        block = Block(
            index=len(self._chain),
            timestamp=time.time(),
            credits=list(self._pending),
            previous_hash=prev.block_hash,
            validator_id=validator_id,
        )
        self._chain.append(block)
        self._pending.clear()
        return block

    def transfer(self, credit_id: str, from_agent: str, to_agent: str) -> bool:
        if self._ownership.get(credit_id) != from_agent:
            return False
        self._ownership[credit_id] = to_agent
        return True

    def balance(self, agent_id: str) -> float:
        total = 0.0
        for block in self._chain:
            for credit in block.credits:
                if self._ownership.get(credit.credit_id) == agent_id:
                    total += credit.face_value
        for credit in self._pending:
            if self._ownership.get(credit.credit_id) == agent_id:
                total += credit.face_value
        return total

    def credits_by_agent(self, agent_id: str) -> List[ContextCredit]:
        result: List[ContextCredit] = []
        for block in self._chain:
            for credit in block.credits:
                if self._ownership.get(credit.credit_id) == agent_id:
                    result.append(credit)
        for credit in self._pending:
            if self._ownership.get(credit.credit_id) == agent_id:
                result.append(credit)
        return result

    def total_supply(self) -> float:
        total = sum(b.total_value for b in self._chain)
        total += sum(c.face_value for c in self._pending)
        return total

    def verify_chain(self) -> Tuple[bool, Optional[int], Optional[str]]:
        for i in range(1, len(self._chain)):
            prev = self._chain[i - 1]
            curr = self._chain[i]
            if curr.previous_hash != prev.block_hash:
                return False, i, "broken hash link"
            expected_merkle = merkle_root([c.block_hash for c in curr.credits])
            if curr.merkle_root_hash != expected_merkle:
                return False, i, "merkle root mismatch"
        return True, None, None

    @property
    def chain_length(self) -> int:
        return len(self._chain)

    @property
    def pending_count(self) -> int:
        return len(self._pending)
