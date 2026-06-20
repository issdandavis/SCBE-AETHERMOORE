"""
Agent Bus → HYDRA Ledger bridge.

Every BusEvent gets two persistence paths:
  1. Local JSONL (artifacts/agent-bus/events.jsonl) — fast, lossy-on-disk-corruption
  2. HYDRA central ledger (SQLite) — cross-session, queryable, signed at write time

If the HYDRA ledger isn't available in this deployment, the bridge silently
no-ops — JSONL is always written.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger("scbe.agent_bus.ledger")


class LedgerBridge:
    """Mirrors BusEvent records into the HYDRA ledger if available."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._ledger = None
        self._entry_type = None
        self._entry_class = None

    def initialize(self) -> bool:
        try:
            from hydra.ledger import Ledger, LedgerEntry, EntryType
        except ImportError as exc:
            logger.info("HYDRA ledger unavailable (%s) — JSONL only", exc)
            return False
        try:
            self._ledger = Ledger()
            self._entry_class = LedgerEntry
            self._entry_type = EntryType.ACTION
            logger.info("HYDRA ledger connected for agent %s", self.agent_id)
            return True
        except Exception as exc:  # noqa: BLE001 — broad on purpose: SQLite init can fail many ways
            logger.warning("ledger init failed: %s", exc)
            self._ledger = None
            return False

    def write_event(
        self,
        *,
        task_type: str,
        action: str,
        target: str,
        payload: Dict[str, Any],
        decision: Optional[str] = None,
        score: Optional[float] = None,
    ) -> Optional[str]:
        if self._ledger is None or self._entry_class is None:
            return None
        try:
            entry = self._entry_class(
                id=str(uuid.uuid4()),
                entry_type=self._entry_type.value if self._entry_type else "action",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                head_id=self.agent_id,
                limb_id=None,
                action=action,
                target=target,
                payload=payload,
                decision=decision,
                score=score,
            )
            return self._ledger.write(entry)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ledger write failed: %s", exc)
            return None
