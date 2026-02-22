"""
Heart Vault — Heart Credit System
====================================

Extension of the MMCCL (Multi-Model Contextual Credit Ledger) for the
Heart Vault.  Agents earn Heart Credits by contributing verified,
high-quality cultural data; they consume credits when querying the
vault for "emotional intelligence."

Credit flow:
    CONTRIBUTE  — Agent adds a verified literary/emotion/proverb node
                  → Earns credits proportional to quality_score × tongue_weight
    QUERY       — Agent queries the vault for emotional context
                  → Spends a fixed query cost
    VALIDATE    — Agent verifies another agent's contribution (peer review)
                  → Earns a validation bonus
    PENALTY     — Contribution is flagged as toxic/biased by Runethic gate
                  → Agent loses credits

Tongue weight follows the golden ratio scale from MMCCL:
    KO=1.000, AV=1.618, RU=2.618, CA=4.236, UM=6.854, DR=11.090

Higher-tongue contributions are worth more because they require
deeper structural/mystical understanding.

Integrates with:
    - MMCCL ``mint_credit()`` for bridging Heart Credits to the main ledger
    - Heart Vault graph ``hv_heart_credits`` table for local accounting
    - Flock Shepherd ``Sheep.coherence`` for credit-weighted task assignment
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .graph import HeartVaultGraph, TongueAffinity


# ---------------------------------------------------------------------------
#  Constants — mirror MMCCL denomination weights
# ---------------------------------------------------------------------------

TONGUE_WEIGHTS: Dict[TongueAffinity, float] = {
    TongueAffinity.KO: 1.000,
    TongueAffinity.AV: 1.618,
    TongueAffinity.RU: 2.618,
    TongueAffinity.CA: 4.236,
    TongueAffinity.UM: 6.854,
    TongueAffinity.DR: 11.090,
}

# Credit economics
BASE_CONTRIBUTE_REWARD = 10.0
BASE_QUERY_COST = 1.0
VALIDATION_BONUS = 3.0
PENALTY_AMOUNT = 15.0


# ---------------------------------------------------------------------------
#  Credit action types
# ---------------------------------------------------------------------------

class CreditAction(str, Enum):
    CONTRIBUTE = "CONTRIBUTE"
    QUERY = "QUERY"
    VALIDATE = "VALIDATE"
    PENALTY = "PENALTY"


# ---------------------------------------------------------------------------
#  Heart Credit record
# ---------------------------------------------------------------------------

@dataclass
class HeartCreditEntry:
    """A single credit transaction in the Heart Vault."""
    id: str
    agent_id: str
    action: CreditAction
    node_id: Optional[str]
    amount: float
    denomination: TongueAffinity
    timestamp: float


# ---------------------------------------------------------------------------
#  Heart Credit Ledger
# ---------------------------------------------------------------------------

class HeartCreditLedger:
    """
    Manages Heart Credit accounting on top of a HeartVaultGraph.

    Usage::

        vault = HeartVaultGraph("vault.db")
        ledger = HeartCreditLedger(vault)

        # Agent contributes a node
        node = vault.add_node(NodeType.PROVERB, "A stitch in time saves nine",
                              tongue=TongueAffinity.DR, quality_score=0.85)
        ledger.contribute("agent-1", node.id, TongueAffinity.DR, quality_score=0.85)

        # Agent queries the vault
        ledger.query("agent-2", TongueAffinity.KO)

        # Check balances
        print(ledger.balance("agent-1"))  # +8.5 * 11.09 = ...
        print(ledger.balance("agent-2"))  # -1.0
    """

    def __init__(self, graph: HeartVaultGraph):
        self._graph = graph

    def _record(
        self,
        agent_id: str,
        action: CreditAction,
        amount: float,
        denomination: TongueAffinity,
        node_id: Optional[str] = None,
    ) -> HeartCreditEntry:
        """Record a credit transaction in the SQLite table."""
        entry = HeartCreditEntry(
            id=uuid.uuid4().hex[:16],
            agent_id=agent_id,
            action=action,
            node_id=node_id,
            amount=amount,
            denomination=denomination,
            timestamp=time.time(),
        )
        with self._graph._tx() as cur:
            cur.execute(
                """INSERT INTO hv_heart_credits
                   (id, agent_id, action, node_id, amount, denomination, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.id,
                    entry.agent_id,
                    entry.action.value,
                    entry.node_id,
                    entry.amount,
                    entry.denomination.value,
                    entry.timestamp,
                ),
            )
        return entry

    def contribute(
        self,
        agent_id: str,
        node_id: str,
        tongue: TongueAffinity,
        quality_score: float = 0.5,
    ) -> HeartCreditEntry:
        """
        Reward an agent for contributing a node to the Heart Vault.

        Reward = BASE_CONTRIBUTE_REWARD × quality_score × tongue_weight
        """
        weight = TONGUE_WEIGHTS.get(tongue, 1.0)
        amount = BASE_CONTRIBUTE_REWARD * quality_score * weight
        return self._record(agent_id, CreditAction.CONTRIBUTE, amount, tongue, node_id)

    def query(
        self,
        agent_id: str,
        tongue: TongueAffinity = TongueAffinity.KO,
    ) -> HeartCreditEntry:
        """
        Charge an agent for querying the Heart Vault.

        Cost = BASE_QUERY_COST (flat, tongue-independent)
        """
        return self._record(agent_id, CreditAction.QUERY, -BASE_QUERY_COST, tongue)

    def validate(
        self,
        agent_id: str,
        node_id: str,
        tongue: TongueAffinity,
    ) -> HeartCreditEntry:
        """
        Reward an agent for validating another agent's contribution.

        Reward = VALIDATION_BONUS × tongue_weight
        """
        weight = TONGUE_WEIGHTS.get(tongue, 1.0)
        amount = VALIDATION_BONUS * weight
        return self._record(agent_id, CreditAction.VALIDATE, amount, tongue, node_id)

    def penalize(
        self,
        agent_id: str,
        node_id: str,
        tongue: TongueAffinity,
    ) -> HeartCreditEntry:
        """
        Penalize an agent for a contribution that failed quality gates.

        Penalty = -PENALTY_AMOUNT (flat)
        """
        return self._record(
            agent_id, CreditAction.PENALTY, -PENALTY_AMOUNT, tongue, node_id
        )

    def balance(self, agent_id: str) -> float:
        """Get the net credit balance for an agent."""
        row = self._graph._conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM hv_heart_credits WHERE agent_id=?",
            (agent_id,),
        ).fetchone()
        return float(row[0]) if row else 0.0

    def history(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[HeartCreditEntry]:
        """Get recent credit transactions for an agent."""
        rows = self._graph._conn.execute(
            """SELECT id, agent_id, action, node_id, amount, denomination, timestamp
               FROM hv_heart_credits
               WHERE agent_id=?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (agent_id, limit),
        ).fetchall()
        return [
            HeartCreditEntry(
                id=r[0],
                agent_id=r[1],
                action=CreditAction(r[2]),
                node_id=r[3],
                amount=r[4],
                denomination=TongueAffinity(r[5]),
                timestamp=r[6],
            )
            for r in rows
        ]

    def leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Top agents by Heart Credit balance."""
        rows = self._graph._conn.execute(
            """SELECT agent_id, SUM(amount) as balance, COUNT(*) as txns
               FROM hv_heart_credits
               GROUP BY agent_id
               ORDER BY balance DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            {"agent_id": r[0], "balance": r[1], "transactions": r[2]}
            for r in rows
        ]

    def stats(self) -> Dict[str, Any]:
        """Summary statistics for the Heart Credit economy."""
        row = self._graph._conn.execute(
            """SELECT
                 COUNT(*) as total_txns,
                 COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as total_earned,
                 COALESCE(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) as total_spent,
                 COUNT(DISTINCT agent_id) as unique_agents
               FROM hv_heart_credits"""
        ).fetchone()
        return {
            "total_transactions": row[0],
            "total_earned": row[1],
            "total_spent": row[2],
            "net_supply": row[1] + row[2],
            "unique_agents": row[3],
        }
