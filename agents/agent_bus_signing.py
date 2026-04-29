"""
Agent Bus event signing — wraps ML-DSA-65 (FIPS 204) for tamper-evident audit logs.

A bus instance has an identity (a long-lived ML-DSA-65 keypair). Every BusEvent
is signed with that key before being logged. The signature plus the agent's
public key go into the event payload, so verifiers years later can confirm:
- The event was produced by this specific agent.
- The event payload has not been altered since signing.

If liboqs / pure-python ML-DSA are unavailable, MLDSA65 falls back to an
HMAC-SHA512 simulation (still tamper-evident, just not quantum-resistant).
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("scbe.agent_bus.signing")

DEFAULT_KEY_DIR = Path("artifacts/agent-bus/identity")


class EventSigner:
    """Signs and verifies BusEvent payloads using ML-DSA-65."""

    def __init__(self, agent_id: str, key_dir: Path = DEFAULT_KEY_DIR) -> None:
        self.agent_id = agent_id
        self.key_dir = Path(key_dir)
        self._signer = None
        self._public_key_bytes: Optional[bytes] = None
        self._secret_key_bytes: Optional[bytes] = None
        self._algorithm: str = "unavailable"

    def initialize(self) -> bool:
        """Load existing identity or create a fresh one. Returns True if signing is active."""
        try:
            from src.crypto.pqc_liboqs import MLDSA65
        except ImportError as exc:
            logger.warning("ML-DSA-65 unavailable (%s) — events will not be signed", exc)
            return False

        self.key_dir.mkdir(parents=True, exist_ok=True)
        sk_path = self.key_dir / f"{self.agent_id}.sk"
        pk_path = self.key_dir / f"{self.agent_id}.pk"

        if sk_path.exists() and pk_path.exists():
            self._secret_key_bytes = sk_path.read_bytes()
            self._public_key_bytes = pk_path.read_bytes()
            self._signer = MLDSA65()
            self._signer._secret_key = self._secret_key_bytes
            self._signer._public_key = self._public_key_bytes
            logger.info("loaded identity for agent %s", self.agent_id)
        else:
            self._signer = MLDSA65()
            self._secret_key_bytes = self._signer.secret_key
            self._public_key_bytes = self._signer.public_key
            sk_path.write_bytes(self._secret_key_bytes)
            pk_path.write_bytes(self._public_key_bytes)
            try:
                sk_path.chmod(0o600)
            except (OSError, NotImplementedError):
                pass
            logger.info("created new identity for agent %s", self.agent_id)

        self._algorithm = getattr(self._signer, "_algorithm", None) or "ML-DSA-65"
        return True

    @property
    def public_key_b64(self) -> str:
        if self._public_key_bytes is None:
            return ""
        return base64.b64encode(self._public_key_bytes).decode()

    @property
    def algorithm(self) -> str:
        return self._algorithm

    def sign(self, payload: Dict[str, Any]) -> Tuple[str, str, str]:
        """Return (signature_b64, public_key_b64, algorithm) for the canonical JSON of payload."""
        if self._signer is None:
            return ("", "", "unsigned")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        sig = self._signer.sign(canonical)
        return (base64.b64encode(sig).decode(), self.public_key_b64, self._algorithm)

    def verify_own(self, payload: Dict[str, Any], signature_b64: str) -> bool:
        """Verify a signature against this signer's loaded identity. Works in all tiers."""
        if self._signer is None or not signature_b64:
            return False
        try:
            sig = base64.b64decode(signature_b64)
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            return bool(self._signer.verify(canonical, sig))
        except (ValueError, AttributeError) as exc:
            logger.warning("verify_own failed: %s", exc)
            return False

    @staticmethod
    def verify(payload: Dict[str, Any], signature_b64: str, public_key_b64: str) -> bool:
        """Public-key-only verification. Requires real ML-DSA-65 (liboqs or pure-python).

        In the HMAC-SHA512 simulation tier the verifier needs the secret key,
        so this method returns False there. Use `verify_own` on a signer that
        has the secret loaded for self-verification.
        """
        if not signature_b64 or not public_key_b64:
            return False
        try:
            from src.crypto.pqc_liboqs import MLDSA65, LIBOQS_AVAILABLE, PURE_PQC_AVAILABLE
        except ImportError:
            return False
        if not (LIBOQS_AVAILABLE or PURE_PQC_AVAILABLE):
            logger.debug("verify: tier-3 simulation does not support public-key-only verify")
            return False
        try:
            sig = base64.b64decode(signature_b64)
            pk = base64.b64decode(public_key_b64)
            verifier = MLDSA65()
            verifier._public_key = pk
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            return bool(verifier.verify(canonical, sig))
        except (ValueError, AttributeError) as exc:
            logger.warning("verify failed: %s", exc)
            return False
