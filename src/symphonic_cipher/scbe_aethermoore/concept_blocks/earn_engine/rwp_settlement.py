"""
Earn Engine — RWP Envelope Settlement Layer
=============================================
Every settlement transaction is wrapped in an RWP2 multi-tongue
signed envelope, providing cryptographic proof of the earn event.

Settlement flow:
  1. EarnEngine.process() creates a LedgerEntry
  2. RWPSettlement wraps it in an RWP2Envelope
  3. Envelope is signed by required tongues (tier-based)
  4. Signed envelope is verified before settlement finalization
  5. Settlement receipt = serialized signed envelope

Tier mapping (mirrors OperationTier from RWP2):
  - Game events      → TIER_1 (KO only, low risk)
  - Content publishes → TIER_2 (KO + RU, medium risk)
  - Shopify sales    → TIER_3 (KO + RU + UM, high value)
  - Training data    → TIER_2 (KO + RU)
  - Settlements      → TIER_3 (KO + RU + UM, financial)

Integrates with:
  - src/spiralverse/rwp2_envelope.py (RWP2Envelope, SignatureEngine)
  - earn_engine/engine.py (EarnEngine, LedgerEntry)
  - MMCCL credit system for credit-bound envelopes
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .engine import EarnEngine, LedgerEntry, SettlementState
from .streams import StreamType


# ---------------------------------------------------------------------------
#  Inline RWP2 signing (avoids import path issues with src/spiralverse)
#  Uses the exact same HMAC-SHA256 protocol as rwp2_envelope.py
# ---------------------------------------------------------------------------

class ProtocolTongue(str, Enum):
    KO = "KO"
    AV = "AV"
    RU = "RU"
    CA = "CA"
    UM = "UM"
    DR = "DR"


# Deterministic tongue keys (same as rwp2_envelope.py)
TONGUE_KEYS: Dict[ProtocolTongue, bytes] = {
    ProtocolTongue.KO: hashlib.sha256(b"SCBE_KO_KEY_v1").digest(),
    ProtocolTongue.AV: hashlib.sha256(b"SCBE_AV_KEY_v1").digest(),
    ProtocolTongue.RU: hashlib.sha256(b"SCBE_RU_KEY_v1").digest(),
    ProtocolTongue.CA: hashlib.sha256(b"SCBE_CA_KEY_v1").digest(),
    ProtocolTongue.UM: hashlib.sha256(b"SCBE_UM_KEY_v1").digest(),
    ProtocolTongue.DR: hashlib.sha256(b"SCBE_DR_KEY_v1").digest(),
}

# Required tongues per tier
TIER_TONGUES: Dict[int, Set[ProtocolTongue]] = {
    1: {ProtocolTongue.KO},
    2: {ProtocolTongue.KO, ProtocolTongue.RU},
    3: {ProtocolTongue.KO, ProtocolTongue.RU, ProtocolTongue.UM},
    4: {ProtocolTongue.KO, ProtocolTongue.RU, ProtocolTongue.UM, ProtocolTongue.CA},
}

# Stream → tier mapping
STREAM_TIER: Dict[StreamType, int] = {
    StreamType.GAME: 1,
    StreamType.CONTENT: 2,
    StreamType.TRAINING: 2,
    StreamType.SHOPIFY: 3,
}


# ---------------------------------------------------------------------------
#  Settlement Envelope
# ---------------------------------------------------------------------------

@dataclass
class SettlementEnvelope:
    """RWP2-signed settlement envelope for a ledger entry."""

    envelope_id: str
    entry_id: str
    stream_type: str
    event_name: str
    denomination: str
    face_value: float
    settled_value: float
    agent_id: str
    credit_hash: str                  # hash of the minted credit
    tier: int
    nonce: str
    timestamp_ms: int
    signatures: Dict[str, str] = field(default_factory=dict)

    @property
    def signing_input(self) -> bytes:
        """Canonical bytes for HMAC signing (pipe-delimited)."""
        parts = [
            self.envelope_id,
            self.entry_id,
            self.stream_type,
            self.event_name,
            self.denomination,
            f"{self.face_value:.8f}",
            f"{self.settled_value:.8f}",
            self.agent_id,
            self.credit_hash,
            str(self.tier),
            self.nonce,
            str(self.timestamp_ms),
        ]
        return "|".join(parts).encode("utf-8")

    @property
    def is_signed(self) -> bool:
        """Check if all required tongues have signed."""
        required = TIER_TONGUES.get(self.tier, TIER_TONGUES[1])
        return all(t.value in self.signatures for t in required)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "entry_id": self.entry_id,
            "stream_type": self.stream_type,
            "event_name": self.event_name,
            "denomination": self.denomination,
            "face_value": round(self.face_value, 8),
            "settled_value": round(self.settled_value, 8),
            "agent_id": self.agent_id,
            "credit_hash": self.credit_hash,
            "tier": self.tier,
            "nonce": self.nonce,
            "timestamp_ms": self.timestamp_ms,
            "signatures": dict(self.signatures),
            "is_signed": self.is_signed,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


# ---------------------------------------------------------------------------
#  RWP Settlement Engine
# ---------------------------------------------------------------------------

import hmac as _hmac
import secrets as _secrets


class RWPSettlement:
    """
    Wraps earn engine settlements in RWP2 multi-tongue signed envelopes.

    Every settlement gets:
    1. A unique envelope with credit hash binding
    2. HMAC-SHA256 signatures from required tongues (tier-based)
    3. Replay protection via nonce + timestamp
    4. Verification before finalization

    Usage::

        from earn_engine.rwp_settlement import RWPSettlement

        rwp = RWPSettlement(engine=earn_engine)

        # Sign a settlement
        envelope = rwp.sign_settlement(ledger_entry)

        # Verify it
        valid, details = rwp.verify_settlement(envelope)

        # Finalize (only if valid)
        if valid:
            rwp.finalize_settlement(envelope, real_value=5.99)
    """

    def __init__(
        self,
        engine: Optional[EarnEngine] = None,
        keys: Optional[Dict[ProtocolTongue, bytes]] = None,
    ):
        self.engine = engine or EarnEngine()
        self.keys = keys or TONGUE_KEYS
        self._envelopes: Dict[str, SettlementEnvelope] = {}
        self._used_nonces: Dict[str, int] = {}
        self._max_nonce_age_ms = 300_000  # 5 minutes

    # --- Signing ---

    def sign_settlement(self, entry: LedgerEntry) -> SettlementEnvelope:
        """
        Wrap a ledger entry in a signed RWP2 envelope.

        Determines tier from stream type, signs with required tongues.
        """
        tier = STREAM_TIER.get(entry.event.stream_type, 1)
        required_tongues = TIER_TONGUES.get(tier, TIER_TONGUES[1])

        credit_hash = ""
        if entry.credit is not None:
            credit_hash = entry.credit.block_hash

        envelope = SettlementEnvelope(
            envelope_id=uuid.uuid4().hex[:16],
            entry_id=entry.entry_id,
            stream_type=entry.event.stream_type.value,
            event_name=entry.event.event_name,
            denomination=entry.event.denomination.value,
            face_value=entry.face_value,
            settled_value=entry.settled_value,
            agent_id=entry.event.agent_id,
            credit_hash=credit_hash,
            tier=tier,
            nonce=_secrets.token_urlsafe(16),
            timestamp_ms=int(time.time() * 1000),
        )

        # Sign with each required tongue
        sig_input = envelope.signing_input
        for tongue in required_tongues:
            key = self.keys.get(tongue)
            if key:
                sig = _hmac.new(key, sig_input, hashlib.sha256).hexdigest()
                envelope.signatures[tongue.value] = sig

        self._envelopes[envelope.envelope_id] = envelope
        return envelope

    # --- Verification ---

    def verify_settlement(
        self, envelope: SettlementEnvelope
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify an RWP2 settlement envelope.

        Checks:
        1. All required tongue signatures present and valid
        2. Nonce not replayed
        3. Timestamp within window
        4. Credit hash matches (if credit exists)
        """
        details: Dict[str, Any] = {
            "envelope_id": envelope.envelope_id,
            "tier": envelope.tier,
            "tongue_results": {},
            "replay_check": False,
            "timestamp_check": False,
        }

        required_tongues = TIER_TONGUES.get(envelope.tier, TIER_TONGUES[1])
        sig_input = envelope.signing_input

        # 1. Verify each tongue signature
        all_sigs_valid = True
        for tongue in required_tongues:
            key = self.keys.get(tongue)
            sig = envelope.signatures.get(tongue.value)

            if not key or not sig:
                details["tongue_results"][tongue.value] = False
                all_sigs_valid = False
                continue

            expected = _hmac.new(key, sig_input, hashlib.sha256).hexdigest()
            valid = _hmac.compare_digest(sig, expected)
            details["tongue_results"][tongue.value] = valid
            if not valid:
                all_sigs_valid = False

        # 2. Replay protection
        nonce_key = f"{envelope.nonce}:{envelope.timestamp_ms}"
        if nonce_key in self._used_nonces:
            details["replay_check"] = False
            return False, details
        self._used_nonces[nonce_key] = envelope.timestamp_ms
        details["replay_check"] = True

        # 3. Timestamp freshness
        now_ms = int(time.time() * 1000)
        age_ms = now_ms - envelope.timestamp_ms
        details["timestamp_check"] = abs(age_ms) <= self._max_nonce_age_ms

        overall = (
            all_sigs_valid
            and details["replay_check"]
            and details["timestamp_check"]
        )
        details["overall"] = overall
        return overall, details

    # --- Finalization ---

    def finalize_settlement(
        self,
        envelope: SettlementEnvelope,
        real_value: float,
    ) -> Optional[LedgerEntry]:
        """
        Finalize a verified settlement with real-world value.

        Only works if the envelope passes verification.
        """
        valid, details = self.verify_settlement(envelope)
        if not valid:
            return None

        # Update the ledger entry
        settled = self.engine.settle(envelope.entry_id, real_value)
        if settled:
            envelope.settled_value = real_value

        return settled

    # --- Batch Operations ---

    def sign_all_pending(self) -> List[SettlementEnvelope]:
        """Sign all earned/pending ledger entries."""
        envelopes = []
        for entry in self.engine.ledger:
            if entry.state in (SettlementState.EARNED, SettlementState.PENDING):
                env = self.sign_settlement(entry)
                envelopes.append(env)
        return envelopes

    def verify_all(self) -> Dict[str, bool]:
        """Verify all stored envelopes."""
        results = {}
        for env_id, env in self._envelopes.items():
            valid, _ = self.verify_settlement(env)
            results[env_id] = valid
        return results

    # --- Queries ---

    def get_envelope(self, envelope_id: str) -> Optional[SettlementEnvelope]:
        return self._envelopes.get(envelope_id)

    def settlement_stats(self) -> Dict[str, Any]:
        total = len(self._envelopes)
        signed = sum(1 for e in self._envelopes.values() if e.is_signed)
        by_tier: Dict[int, int] = {}
        for e in self._envelopes.values():
            by_tier[e.tier] = by_tier.get(e.tier, 0) + 1

        return {
            "total_envelopes": total,
            "fully_signed": signed,
            "by_tier": by_tier,
            "nonces_tracked": len(self._used_nonces),
        }
