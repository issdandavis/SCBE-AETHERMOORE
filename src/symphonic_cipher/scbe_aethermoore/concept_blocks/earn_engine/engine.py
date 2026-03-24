"""
Earn Engine — Core
====================
Central engine that processes earn events through the governance gate,
mints MMCCL credits, and tracks the settlement ledger.

Pipeline:
  EarnEvent → governance_check() → mint_credit() → SettlementLedger

Settlement states:
  EARNED    — credit minted, not yet settled
  PENDING   — settlement in progress (e.g. Shopify payout processing)
  SETTLED   — real value received (payout complete)
  REJECTED  — governance DENY'd the event
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..context_credit_ledger.credit import (
    ContextCredit,
    DENOMINATION_WEIGHTS,
    mint_credit,
)
from .streams import (
    EarnEvent,
    GovernanceVerdict,
    StreamType,
    STREAM_CONFIGS,
)


# ---------------------------------------------------------------------------
#  Settlement States
# ---------------------------------------------------------------------------

class SettlementState(str, Enum):
    EARNED = "EARNED"
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
#  Ledger Entry
# ---------------------------------------------------------------------------

@dataclass
class LedgerEntry:
    """A single entry in the settlement ledger."""
    entry_id: str
    event: EarnEvent
    credit: Optional[ContextCredit]
    verdict: GovernanceVerdict
    state: SettlementState
    face_value: float
    settled_value: float              # real-world value (0 until settled)
    created_at: float
    settled_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "event_id": self.event.event_id,
            "stream_type": self.event.stream_type.value,
            "event_name": self.event.event_name,
            "denomination": self.event.denomination.value,
            "verdict": self.verdict.value,
            "state": self.state.value,
            "face_value": round(self.face_value, 6),
            "settled_value": round(self.settled_value, 6),
            "created_at": self.created_at,
            "settled_at": self.settled_at,
            "metadata": self.event.metadata,
        }


# ---------------------------------------------------------------------------
#  Earn Engine
# ---------------------------------------------------------------------------

class EarnEngine:
    """
    Core earn engine — governance-gated credit minting with settlement tracking.

    Usage::

        engine = EarnEngine(agent_id="player-1")

        # Game event
        event = EarnEvent(
            stream_type=StreamType.GAME,
            event_name="battle_victory",
            base_reward=10.0,
            denomination=Denomination.KO,
        )
        entry = engine.process(event)
        print(entry.face_value, entry.state)

        # Check totals
        print(engine.total_earned())
        print(engine.balance_by_denomination())
    """

    def __init__(
        self,
        agent_id: str = "player",
        model_name: str = "aethermoor-game",
        personality_vector: Optional[List[float]] = None,
        ledger_path: Optional[Path] = None,
    ):
        self.agent_id = agent_id
        self.model_name = model_name
        self.personality_vector = personality_vector or [0.5] * 21
        self.ledger: List[LedgerEntry] = []
        self.ledger_path = ledger_path

        # Callbacks for external integrations
        self._on_earn: List[Callable[[LedgerEntry], None]] = []
        self._on_reject: List[Callable[[LedgerEntry], None]] = []

    # --- Callback registration ---

    def on_earn(self, callback: Callable[[LedgerEntry], None]) -> None:
        """Register callback for successful earn events."""
        self._on_earn.append(callback)

    def on_reject(self, callback: Callable[[LedgerEntry], None]) -> None:
        """Register callback for rejected earn events."""
        self._on_reject.append(callback)

    # --- Governance Gate ---

    def _governance_check(self, event: EarnEvent) -> GovernanceVerdict:
        """
        L13 governance gate — check if the earn event is allowed.

        Uses harmonic wall: H(d,R) = R^(d^2)
        If H > threshold, QUARANTINE or DENY.
        """
        config = STREAM_CONFIGS.get(event.stream_type)
        if config is None:
            return GovernanceVerdict.DENY

        d = event.hamiltonian_d
        pd = event.hamiltonian_pd

        # Harmonic wall cost
        R = DENOMINATION_WEIGHTS.get(event.denomination, 1.0)
        h_cost = R ** (d ** 2)

        # Policy deviation check
        if pd > config.max_hamiltonian_pd:
            return GovernanceVerdict.DENY
        if d > config.max_hamiltonian_d:
            return GovernanceVerdict.QUARANTINE
        if h_cost > 100.0:
            return GovernanceVerdict.QUARANTINE

        return GovernanceVerdict.ALLOW

    # --- Credit Minting ---

    def _mint(self, event: EarnEvent) -> ContextCredit:
        """Mint an MMCCL credit from a governance-approved event."""
        config = STREAM_CONFIGS.get(event.stream_type, STREAM_CONFIGS[StreamType.GAME])
        reward = event.base_reward * config.base_multiplier

        context_payload = json.dumps({
            "event": event.event_name,
            "stream": event.stream_type.value,
            "reward": reward,
            "metadata": event.metadata,
        }).encode("utf-8")

        return mint_credit(
            agent_id=event.agent_id or self.agent_id,
            model_name=event.model_name or self.model_name,
            denomination=event.denomination.value,
            context_payload=context_payload,
            personality_vector=list(self.personality_vector),
            hamiltonian_d=event.hamiltonian_d,
            hamiltonian_pd=event.hamiltonian_pd,
            governance_verdict="ALLOW",
            context_summary=f"{event.stream_type.value}:{event.event_name}",
            difficulty=1,  # fast mint for game events
        )

    # --- Main Processing ---

    def process(self, event: EarnEvent) -> LedgerEntry:
        """
        Process an earn event through the full pipeline.

        1. Governance check
        2. If ALLOW: mint credit, record as EARNED
        3. If QUARANTINE: mint credit, record as PENDING
        4. If DENY: no credit, record as REJECTED
        """
        verdict = self._governance_check(event)
        credit = None
        face_value = 0.0

        if verdict == GovernanceVerdict.ALLOW:
            credit = self._mint(event)
            face_value = credit.face_value
            state = SettlementState.EARNED
        elif verdict == GovernanceVerdict.QUARANTINE:
            credit = self._mint(event)
            face_value = credit.face_value * 0.5  # half value until review
            state = SettlementState.PENDING
        else:
            state = SettlementState.REJECTED

        entry = LedgerEntry(
            entry_id=uuid.uuid4().hex[:16],
            event=event,
            credit=credit,
            verdict=verdict,
            state=state,
            face_value=face_value,
            settled_value=0.0,
            created_at=time.time(),
        )

        self.ledger.append(entry)

        # Fire callbacks
        if state in (SettlementState.EARNED, SettlementState.PENDING):
            for cb in self._on_earn:
                cb(entry)
        else:
            for cb in self._on_reject:
                cb(entry)

        return entry

    # --- Settlement ---

    def settle(self, entry_id: str, real_value: float) -> Optional[LedgerEntry]:
        """Mark a ledger entry as settled with real-world value."""
        for entry in self.ledger:
            if entry.entry_id == entry_id:
                entry.state = SettlementState.SETTLED
                entry.settled_value = real_value
                entry.settled_at = time.time()
                return entry
        return None

    # --- Queries ---

    def total_earned(self) -> float:
        """Total face value of all earned + pending credits."""
        return sum(
            e.face_value for e in self.ledger
            if e.state in (SettlementState.EARNED, SettlementState.PENDING)
        )

    def total_settled(self) -> float:
        """Total real-world value settled."""
        return sum(e.settled_value for e in self.ledger if e.state == SettlementState.SETTLED)

    def balance_by_denomination(self) -> Dict[str, float]:
        """Breakdown of earned value by tongue denomination."""
        balances: Dict[str, float] = {}
        for entry in self.ledger:
            if entry.state in (SettlementState.EARNED, SettlementState.PENDING):
                denom = entry.event.denomination.value
                balances[denom] = balances.get(denom, 0.0) + entry.face_value
        return balances

    def balance_by_stream(self) -> Dict[str, float]:
        """Breakdown of earned value by stream type."""
        balances: Dict[str, float] = {}
        for entry in self.ledger:
            if entry.state in (SettlementState.EARNED, SettlementState.PENDING):
                stream = entry.event.stream_type.value
                balances[stream] = balances.get(stream, 0.0) + entry.face_value
        return balances

    def recent(self, limit: int = 20) -> List[LedgerEntry]:
        """Most recent ledger entries."""
        return list(reversed(self.ledger[-limit:]))

    def stats(self) -> Dict[str, Any]:
        """Summary statistics."""
        earned_count = sum(1 for e in self.ledger if e.state == SettlementState.EARNED)
        pending_count = sum(1 for e in self.ledger if e.state == SettlementState.PENDING)
        rejected_count = sum(1 for e in self.ledger if e.state == SettlementState.REJECTED)
        settled_count = sum(1 for e in self.ledger if e.state == SettlementState.SETTLED)

        return {
            "total_events": len(self.ledger),
            "earned": earned_count,
            "pending": pending_count,
            "settled": settled_count,
            "rejected": rejected_count,
            "total_face_value": round(self.total_earned(), 4),
            "total_settled_value": round(self.total_settled(), 4),
            "by_denomination": self.balance_by_denomination(),
            "by_stream": self.balance_by_stream(),
        }

    # --- Persistence ---

    def save_ledger(self, path: Optional[Path] = None) -> str:
        """Save ledger to JSONL file."""
        out = path or self.ledger_path
        if out is None:
            out = Path("earn_ledger.jsonl")
        with open(out, "w", encoding="utf-8") as f:
            for entry in self.ledger:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        return str(out)

    def load_ledger(self, path: Optional[Path] = None) -> int:
        """Load ledger from JSONL file. Returns count of entries loaded."""
        src = path or self.ledger_path
        if src is None or not Path(src).exists():
            return 0
        count = 0
        with open(src, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
