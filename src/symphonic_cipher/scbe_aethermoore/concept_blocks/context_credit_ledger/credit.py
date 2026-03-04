"""
MMCCL — Context Credit & DNA Structure
=========================================

A ContextCredit is the fundamental unit of value in the Multi-Model
Contextual Credit Ledger.  Each credit encodes:

1. **Energy cost**  — Hamiltonian H(d,pd) that was spent to produce it
2. **DNA fingerprint** — 21D personality vector snapshot of the producing agent
3. **Tongue denomination** — which Sacred Tongue the context was expressed in
4. **Governance stamp** — the 14-layer pipeline verdict at creation time
5. **Provenance chain** — hash of parent credits (lineage)

Credits are immutable once minted.  They can be:
- Transferred between agents (exchange)
- Locked in a BitLocker vault
- Spent to purchase compute/context from other models
- Staked for governance voting weight
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


# ---------------------------------------------------------------------------
#  Tongue denominations — each tongue is a "currency" with different weight
# ---------------------------------------------------------------------------

class Denomination(str, Enum):
    """Sacred Tongue denominations — each has intrinsic weight from cross-talk."""
    KO = "KO"   # Kor'aelin — Flow/Intent     — weight 1.000  (base)
    AV = "AV"   # Avali     — Diplomacy        — weight 1.618  (phi)
    RU = "RU"   # Runethic  — Binding/Chaos    — weight 2.618  (phi^2)
    CA = "CA"   # Cassisivadan — Bitcraft/Math — weight 4.236  (phi^3)
    UM = "UM"   # Umbroth   — Veil/Mystery     — weight 6.854  (phi^4)
    DR = "DR"   # Draumric  — Structure/Order  — weight 11.090 (phi^5)


# Golden ratio weights — each tongue's value follows the Fibonacci spiral
DENOMINATION_WEIGHTS: Dict[Denomination, float] = {
    Denomination.KO: 1.000,
    Denomination.AV: 1.618,
    Denomination.RU: 2.618,
    Denomination.CA: 4.236,
    Denomination.UM: 6.854,
    Denomination.DR: 11.090,
}


# ---------------------------------------------------------------------------
#  Credit DNA — the genetic fingerprint of a credit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CreditDNA:
    """
    Genetic fingerprint embedded in every credit.

    Encodes the producing agent's identity, personality, and the
    conditions under which the credit was minted.
    """

    # Agent identity
    agent_id: str
    model_name: str                          # e.g. "qwen3-8b", "claude-opus"

    # 21D personality vector snapshot (7 categories x 3 dimensions)
    personality_vector: Tuple[float, ...]     # Frozen at mint time

    # SCBE layers that were active during production
    active_layers: FrozenSet[int]            # e.g. {1, 2, 5, 8, 10}

    # Hamiltonian energy signature
    hamiltonian_d: float                     # deviation at mint time
    hamiltonian_pd: float                    # policy deviation at mint time

    # Entropy at mint time (Layer 7)
    entropy: float

    # Governance verdict that authorized this credit
    governance_verdict: str                  # ALLOW / QUARANTINE

    @property
    def energy_cost(self) -> float:
        """H(d,pd) = 1/(1+d+2*pd) — the Hamiltonian energy spent."""
        return 1.0 / (1.0 + self.hamiltonian_d + 2.0 * self.hamiltonian_pd)

    @property
    def complexity(self) -> float:
        """How many layers were involved — more layers = rarer credit."""
        return len(self.active_layers) / 14.0

    @property
    def personality_hash(self) -> str:
        """Short hash of the personality vector — unique per agent state."""
        raw = ",".join(f"{v:.4f}" for v in self.personality_vector)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "model_name": self.model_name,
            "personality_vector": list(self.personality_vector),
            "active_layers": sorted(self.active_layers),
            "hamiltonian_d": self.hamiltonian_d,
            "hamiltonian_pd": self.hamiltonian_pd,
            "energy_cost": round(self.energy_cost, 6),
            "entropy": self.entropy,
            "governance_verdict": self.governance_verdict,
            "personality_hash": self.personality_hash,
            "complexity": round(self.complexity, 4),
        }


# ---------------------------------------------------------------------------
#  Context Credit — the immutable currency unit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContextCredit:
    """
    Immutable unit of context-currency.

    Value = denomination_weight * energy_cost * complexity * legibility
    """

    credit_id: str                           # UUID
    denomination: Denomination               # Sacred Tongue denomination
    dna: CreditDNA                           # Genetic fingerprint
    payload_hash: str                        # SHA-256 of the context payload
    parent_credits: Tuple[str, ...]          # IDs of credits that produced this one
    timestamp: float                         # Unix time of minting
    nonce: int                               # Proof-of-context nonce

    # Legibility score — how readable/verifiable the context is [0,1]
    legibility: float = 1.0

    # Optional: the actual context data (may be stripped for privacy)
    context_summary: str = ""

    @property
    def face_value(self) -> float:
        """
        Intrinsic value of the credit.

        value = weight * energy * complexity * legibility
        """
        weight = DENOMINATION_WEIGHTS.get(self.denomination, 1.0)
        energy = self.dna.energy_cost
        complexity = max(0.01, self.dna.complexity)
        return weight * energy * complexity * self.legibility

    @property
    def block_hash(self) -> str:
        """Hash of this credit for blockchain inclusion."""
        data = json.dumps({
            "id": self.credit_id,
            "denom": self.denomination.value,
            "payload": self.payload_hash,
            "parents": list(self.parent_credits),
            "ts": self.timestamp,
            "nonce": self.nonce,
            "dna_hash": self.dna.personality_hash,
            "value": round(self.face_value, 8),
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "credit_id": self.credit_id,
            "denomination": self.denomination.value,
            "dna": self.dna.to_dict(),
            "payload_hash": self.payload_hash,
            "parent_credits": list(self.parent_credits),
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "legibility": self.legibility,
            "face_value": round(self.face_value, 8),
            "block_hash": self.block_hash,
            "context_summary": self.context_summary,
        }


# ---------------------------------------------------------------------------
#  Credit Minting — produce new credits from context
# ---------------------------------------------------------------------------

def mint_credit(
    agent_id: str,
    model_name: str,
    denomination: str,
    context_payload: bytes,
    personality_vector: List[float],
    hamiltonian_d: float,
    hamiltonian_pd: float,
    entropy: float = 3.5,
    active_layers: Optional[List[int]] = None,
    governance_verdict: str = "ALLOW",
    parent_credit_ids: Optional[List[str]] = None,
    legibility: float = 1.0,
    context_summary: str = "",
    difficulty: int = 2,
) -> ContextCredit:
    """
    Mint a new ContextCredit from a context interaction.

    The minting process performs proof-of-context: finds a nonce such that
    the credit hash starts with `difficulty` zero-nibbles.

    Args:
        agent_id: Producing agent's ID
        model_name: Model that generated the context
        denomination: Sacred Tongue denomination (KO/AV/RU/CA/UM/DR)
        context_payload: Raw context bytes
        personality_vector: 21D personality vector
        hamiltonian_d: Deviation parameter
        hamiltonian_pd: Policy deviation parameter
        entropy: Shannon entropy of the context
        active_layers: Which SCBE layers were active
        governance_verdict: ALLOW or QUARANTINE
        parent_credit_ids: Credits that fed into this one
        legibility: How verifiable [0,1]
        context_summary: Human-readable summary
        difficulty: Proof-of-context difficulty (zero-nibbles required)

    Returns:
        Newly minted ContextCredit
    """
    denom = Denomination(denomination)
    payload_hash = hashlib.sha256(context_payload).hexdigest()

    pv = tuple(personality_vector) if personality_vector else tuple([0.0] * 21)
    if len(pv) < 21:
        pv = pv + (0.0,) * (21 - len(pv))

    dna = CreditDNA(
        agent_id=agent_id,
        model_name=model_name,
        personality_vector=pv[:21],
        active_layers=frozenset(active_layers or [1, 2, 5]),
        hamiltonian_d=hamiltonian_d,
        hamiltonian_pd=hamiltonian_pd,
        entropy=entropy,
        governance_verdict=governance_verdict,
    )

    credit_id = str(uuid.uuid4())
    parents = tuple(parent_credit_ids or [])
    ts = time.time()

    # Proof-of-context mining: find nonce where hash starts with zeros
    prefix = "0" * difficulty
    nonce = 0
    while True:
        candidate = ContextCredit(
            credit_id=credit_id,
            denomination=denom,
            dna=dna,
            payload_hash=payload_hash,
            parent_credits=parents,
            timestamp=ts,
            nonce=nonce,
            legibility=legibility,
            context_summary=context_summary,
        )
        if candidate.block_hash.startswith(prefix):
            return candidate
        nonce += 1
        if nonce > 1_000_000:
            # Safety valve — accept whatever we have
            return candidate
