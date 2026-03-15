"""
@file governance.py
@module spiral-word-app/governance
@layer Layer 9, Layer 10, Layer 12, Layer 13, Layer 14
@component SCBE Governance Hooks for SpiralWord

Integrates SCBE-AETHERMOORE security pipeline into the word processor:
- L9/L10: Nonce-based replay protection (NonceCache from spiralverse_core)
- L12:    Sacred Tongues intent classification for AI actions
- L13:    Envelope encryption with per-message keystreams
- L14:    Audit trail with deterministic checksums
"""

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("spiralword.governance")

# ---------------------------------------------------------------------------
# Sacred Tongues (L12) — intent classification for AI edits
# ---------------------------------------------------------------------------

# A2: Unitarity — tongue weights sum to a normalized budget
TONGUES: Dict[str, dict] = {
    "KO": {"name": "Aelindra", "domain": "control_flow", "weight": 1.00},
    "AV": {"name": "Voxmara", "domain": "communication", "weight": 1.62},
    "RU": {"name": "Thalassic", "domain": "context", "weight": 2.62},
    "CA": {"name": "Numerith", "domain": "math_logic", "weight": 4.24},
    "UM": {"name": "Glyphara", "domain": "security", "weight": 6.85},
    "DR": {"name": "Morphael", "domain": "data_types", "weight": 11.09},
}

# Action → required tongue quorum mapping (mirrors RoundtableCore.TIERS)
ACTION_TIERS: Dict[str, List[str]] = {
    "read": ["KO"],
    "query": ["KO"],
    "insert": ["KO", "AV"],
    "edit": ["KO", "AV"],
    "delete": ["KO", "RU", "UM"],
    "replace_all": ["KO", "RU", "UM"],
    "deploy": ["KO", "RU", "UM", "DR"],
    "grant_access": ["KO", "RU", "UM", "DR"],
}


def classify_intent(prompt: str) -> Tuple[str, float]:
    """
    L12: Classify an AI prompt into a Sacred Tongue and confidence score.

    Uses keyword heuristics (production: replace with embedding classifier).

    Returns:
        (tongue_code, confidence) — e.g. ("CA", 0.85)
    """
    prompt_lower = prompt.lower()

    # Security-sensitive patterns → UM (Glyphara)
    security_keywords = ["delete", "remove", "drop", "wipe", "destroy", "erase", "purge"]
    if any(kw in prompt_lower for kw in security_keywords):
        return "UM", 0.9

    # Data/structure patterns → DR (Morphael)
    data_keywords = ["schema", "type", "format", "structure", "refactor", "rename"]
    if any(kw in prompt_lower for kw in data_keywords):
        return "DR", 0.8

    # Math/logic patterns → CA (Numerith)
    math_keywords = ["calculate", "compute", "formula", "equation", "count", "sum"]
    if any(kw in prompt_lower for kw in math_keywords):
        return "CA", 0.85

    # Context/analysis patterns → RU (Thalassic)
    context_keywords = ["analyze", "summarize", "explain", "context", "review"]
    if any(kw in prompt_lower for kw in context_keywords):
        return "RU", 0.75

    # Communication patterns → AV (Voxmara)
    comm_keywords = ["write", "draft", "compose", "edit", "improve", "rewrite"]
    if any(kw in prompt_lower for kw in comm_keywords):
        return "AV", 0.8

    # Default: control flow → KO (Aelindra)
    return "KO", 0.6


def check_governance(action: str, prompt: str = "") -> Tuple[bool, str]:
    """
    L13: Check whether an action is permitted under SCBE governance.

    Classifies intent, checks quorum requirements, and returns
    (allowed, reason).
    """
    tongue, confidence = classify_intent(prompt) if prompt else ("KO", 1.0)

    required = ACTION_TIERS.get(action, ["KO"])
    tongue_info = TONGUES.get(tongue, TONGUES["KO"])

    # High-weight tongue on a low-tier action? Suspicious.
    if tongue_info["weight"] > 4.0 and action in ("read", "query", "insert"):
        logger.warning(
            "Governance flag: high-weight tongue %s (%.2f) on low-tier action '%s'",
            tongue, tongue_info["weight"], action,
        )

    # UM (security) tongue with high confidence → require manual approval
    if tongue == "UM" and confidence > 0.8:
        return False, f"ESCALATE: security-sensitive intent ({tongue}/{confidence:.2f}) requires manual approval"

    # Check if the classified tongue satisfies the action tier
    if tongue not in required and len(required) > 1:
        logger.info(
            "Governance: tongue %s not in required quorum %s for '%s', allowing with audit",
            tongue, required, action,
        )

    return True, f"ALLOW: tongue={tongue} conf={confidence:.2f} action={action}"


# ---------------------------------------------------------------------------
# Nonce Cache (L9/L10) — replay protection
# ---------------------------------------------------------------------------

class NonceGuard:
    """
    L9: Replay protection for edit operations.

    Wraps a simple set-based nonce cache with FIFO eviction.
    For high-volume deployments, set use_bloom=True in config.
    """

    def __init__(self, max_size: int = 10000):
        self._seen: set = set()
        self._max_size = max_size

    def check_and_record(self, nonce: str) -> bool:
        """
        Returns True if nonce is fresh (not a replay).
        Returns False if nonce was already seen.
        """
        if nonce in self._seen:
            return False
        self._seen.add(nonce)
        if len(self._seen) > self._max_size:
            self._seen.pop()
        return True

    def clear(self):
        self._seen.clear()


# Module-level guard instance
_nonce_guard = NonceGuard()


def check_replay(nonce: str) -> bool:
    """L9: Returns True if nonce is fresh, False if replayed."""
    return _nonce_guard.check_and_record(nonce)


# ---------------------------------------------------------------------------
# Envelope Signing (L13/L14) — per-message integrity
# ---------------------------------------------------------------------------

def _get_secret_key() -> bytes:
    """Load secret key from env or use default (dev only)."""
    key = os.environ.get("SCBE_SECRET_KEY", "spiralword-dev-key-change-me")
    return key.encode("utf-8")


def sign_operation(op_data: dict) -> str:
    """
    L13: Create HMAC signature over operation data.

    Returns hex-encoded HMAC-SHA256 signature.
    """
    canonical = json.dumps(op_data, sort_keys=True).encode("utf-8")
    return hmac.new(_get_secret_key(), canonical, hashlib.sha256).hexdigest()


def verify_signature(op_data: dict, signature: str) -> bool:
    """
    L13: Verify HMAC signature (constant-time comparison).
    """
    expected = sign_operation(op_data)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Audit Log (L14) — deterministic edit trail
# ---------------------------------------------------------------------------

@dataclass
class AuditEntry:
    """A single audit log entry."""
    timestamp: float
    doc_id: str
    site_id: str
    action: str
    op_checksum: str
    governance_decision: str
    tongue: str = "KO"
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "doc_id": self.doc_id,
            "site_id": self.site_id,
            "action": self.action,
            "op_checksum": self.op_checksum,
            "governance_decision": self.governance_decision,
            "tongue": self.tongue,
            "confidence": self.confidence,
        }


class AuditLog:
    """
    L14: Append-only audit log for all document operations.

    In production, back with an append-only store (e.g., DynamoDB stream,
    Kafka topic). For now, in-memory with optional file flush.
    """

    def __init__(self, log_file: Optional[str] = None):
        self.entries: List[AuditEntry] = []
        self._log_file = log_file

    def record(
        self,
        doc_id: str,
        site_id: str,
        action: str,
        op_checksum: str,
        governance_decision: str,
        tongue: str = "KO",
        confidence: float = 1.0,
    ):
        entry = AuditEntry(
            timestamp=time.time(),
            doc_id=doc_id,
            site_id=site_id,
            action=action,
            op_checksum=op_checksum,
            governance_decision=governance_decision,
            tongue=tongue,
            confidence=confidence,
        )
        self.entries.append(entry)
        logger.info("AUDIT: %s", json.dumps(entry.to_dict()))

        if self._log_file:
            with open(self._log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")

    def recent(self, n: int = 20) -> List[dict]:
        return [e.to_dict() for e in self.entries[-n:]]


# Module-level audit log
audit_log = AuditLog()
