"""
Agent Bus event signing — four-tier fallback chain for tamper-evident audit logs.

Tier order (strongest first; signer picks the highest available at init):

    1. ML-DSA-65 via liboqs C lib  — post-quantum, public-key-verifiable
    2. ML-DSA-65 via pure-Python   — same scheme, slower, still PQC
    3. Ed25519 via `cryptography`  — classical asymmetric, public-key-verifiable,
                                      fast (32-byte keys, 64-byte sigs).
                                      NOT post-quantum, but cross-agent verify still works.
    4. HMAC-SHA512 sim             — last resort, tamper-evident only.
                                      Cross-agent verify is impossible without
                                      sharing the secret. Self-verify works.

Every signature stores its algorithm in the event payload (`_sig_alg`), so a
verifier can pick the right tier without ambiguity. Keys persist per-algorithm
under `artifacts/agent-bus/identity/<agent_id>.<alg>.{sk,pk}` so different
deployments of the same agent don't collide.

Why Ed25519 in the chain: when neither PQC tier is installable (e.g., Windows
without liboqs C lib AND no `dilithium-py`), falling straight to HMAC sim
breaks cross-agent verification. Ed25519 closes that gap — you lose the
post-quantum claim, but you keep "anyone with my public key can verify
that this event is mine."
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("scbe.agent_bus.signing")

DEFAULT_KEY_DIR = Path("artifacts/agent-bus/identity")

# Algorithm identifiers as written into events
ALG_MLDSA65 = "ML-DSA-65"
ALG_ED25519 = "Ed25519"
ALG_HMAC_SIM = "HMAC-SHA512-sim"
ALG_UNSIGNED = "unsigned"


class _SignerImpl:
    """Internal sign/verify protocol. Each tier provides one."""

    algorithm: str = ALG_UNSIGNED
    public_key_bytes: bytes = b""
    secret_key_bytes: bytes = b""

    def sign(self, message: bytes) -> bytes:
        raise NotImplementedError

    def verify(self, message: bytes, signature: bytes) -> bool:
        raise NotImplementedError

    @staticmethod
    def verify_with_pubkey(message: bytes, signature: bytes, public_key: bytes) -> bool:
        raise NotImplementedError


# --- Tier 1+2: ML-DSA-65 (PQC) -------------------------------------------------


def _try_mldsa65(sk: Optional[bytes], pk: Optional[bytes]) -> Optional[_SignerImpl]:
    try:
        from src.crypto.pqc_liboqs import MLDSA65, LIBOQS_AVAILABLE, PURE_PQC_AVAILABLE

        if not (LIBOQS_AVAILABLE or PURE_PQC_AVAILABLE):
            return None
    except (ImportError, RuntimeError, OSError):
        return None

    impl = MLDSA65() if (sk is None or pk is None) else MLDSA65()
    if sk is not None and pk is not None:
        impl._secret_key = sk
        impl._public_key = pk

    class _MLDSA65Signer(_SignerImpl):
        algorithm = ALG_MLDSA65
        public_key_bytes = impl.public_key
        secret_key_bytes = impl.secret_key

        def sign(self, message: bytes) -> bytes:
            return impl.sign(message)

        def verify(self, message: bytes, signature: bytes) -> bool:
            return bool(impl.verify(message, signature))

        @staticmethod
        def verify_with_pubkey(message: bytes, signature: bytes, public_key: bytes) -> bool:
            from src.crypto.pqc_liboqs import MLDSA65 as _M

            verifier = _M()
            verifier._public_key = public_key
            return bool(verifier.verify(message, signature))

    return _MLDSA65Signer()


# --- Tier 3: Ed25519 (classical asymmetric) -----------------------------------


def _try_ed25519(sk: Optional[bytes], pk: Optional[bytes]) -> Optional[_SignerImpl]:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        return None

    if sk is not None:
        priv = Ed25519PrivateKey.from_private_bytes(sk)
    else:
        priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()

    sk_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pk_bytes = pub.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)

    class _Ed25519Signer(_SignerImpl):
        algorithm = ALG_ED25519
        public_key_bytes = pk_bytes
        secret_key_bytes = sk_bytes

        def sign(self, message: bytes) -> bytes:
            return priv.sign(message)

        def verify(self, message: bytes, signature: bytes) -> bool:
            try:
                pub.verify(signature, message)
                return True
            except Exception:  # noqa: BLE001 — InvalidSignature etc.
                return False

        @staticmethod
        def verify_with_pubkey(message: bytes, signature: bytes, public_key: bytes) -> bool:
            try:
                pk_obj = Ed25519PublicKey.from_public_bytes(public_key)
                pk_obj.verify(signature, message)
                return True
            except Exception:  # noqa: BLE001
                return False

    return _Ed25519Signer()


# --- Tier 4: HMAC-SHA512 sim --------------------------------------------------


def _try_hmac_sim(sk: Optional[bytes]) -> _SignerImpl:
    """Always returns a working impl — last resort fallback."""
    import hmac
    import hashlib
    import os as _os

    secret = sk if sk is not None else _os.urandom(64)

    class _HMACSimSigner(_SignerImpl):
        algorithm = ALG_HMAC_SIM
        public_key_bytes = hashlib.sha256(secret + b"pk").digest()  # opaque, NOT verifiable from this alone
        secret_key_bytes = secret

        def sign(self, message: bytes) -> bytes:
            return hmac.new(secret, message, hashlib.sha512).digest()

        def verify(self, message: bytes, signature: bytes) -> bool:
            expected = hmac.new(secret, message, hashlib.sha512).digest()
            return hmac.compare_digest(expected, signature)

        @staticmethod
        def verify_with_pubkey(message: bytes, signature: bytes, public_key: bytes) -> bool:
            # Symmetric scheme — public-key-only verify is fundamentally impossible.
            return False

    return _HMACSimSigner()


# --- Public API ---------------------------------------------------------------


class EventSigner:
    """Signs and verifies BusEvent payloads using the strongest tier available."""

    def __init__(self, agent_id: str, key_dir: Path = DEFAULT_KEY_DIR) -> None:
        self.agent_id = agent_id
        self.key_dir = Path(key_dir)
        self._impl: Optional[_SignerImpl] = None

    def initialize(self) -> bool:
        """Load existing identity or create a fresh one. Returns True if signing is active."""
        self.key_dir.mkdir(parents=True, exist_ok=True)

        # Try each tier in order; if a tier has stored keys, prefer that.
        tier_attempts = (
            (ALG_MLDSA65, lambda sk, pk: _try_mldsa65(sk, pk)),
            (ALG_ED25519, lambda sk, pk: _try_ed25519(sk, pk)),
            (ALG_HMAC_SIM, lambda sk, _pk: _try_hmac_sim(sk)),
        )

        for alg, builder in tier_attempts:
            sk_path = self.key_dir / f"{self.agent_id}.{alg}.sk"
            pk_path = self.key_dir / f"{self.agent_id}.{alg}.pk"
            sk = sk_path.read_bytes() if sk_path.exists() else None
            pk = pk_path.read_bytes() if pk_path.exists() else None
            impl = builder(sk, pk)
            if impl is None:
                continue
            self._impl = impl
            # Persist if newly generated
            if sk is None or pk is None:
                sk_path.write_bytes(impl.secret_key_bytes)
                pk_path.write_bytes(impl.public_key_bytes)
                try:
                    sk_path.chmod(0o600)
                except (OSError, NotImplementedError):
                    pass
                logger.info("created new %s identity for agent %s", alg, self.agent_id)
            else:
                logger.info("loaded existing %s identity for agent %s", alg, self.agent_id)
            return True

        # Should be unreachable — HMAC sim always returns an impl
        logger.error("no signing tier available — events will not be signed")
        return False

    @property
    def algorithm(self) -> str:
        return self._impl.algorithm if self._impl else ALG_UNSIGNED

    @property
    def public_key_b64(self) -> str:
        if self._impl is None:
            return ""
        return base64.b64encode(self._impl.public_key_bytes).decode()

    def sign(self, payload: Dict[str, Any]) -> Tuple[str, str, str]:
        """Return (signature_b64, public_key_b64, algorithm) for the canonical JSON of payload."""
        if self._impl is None:
            return ("", "", ALG_UNSIGNED)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        sig = self._impl.sign(canonical)
        return (base64.b64encode(sig).decode(), self.public_key_b64, self._impl.algorithm)

    def verify_own(self, payload: Dict[str, Any], signature_b64: str) -> bool:
        """Verify a signature against this signer's loaded identity. Works in all tiers."""
        if self._impl is None or not signature_b64:
            return False
        try:
            sig = base64.b64decode(signature_b64)
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            return bool(self._impl.verify(canonical, sig))
        except (ValueError, AttributeError) as exc:
            logger.warning("verify_own failed: %s", exc)
            return False

    @staticmethod
    def verify(
        payload: Dict[str, Any],
        signature_b64: str,
        public_key_b64: str,
        algorithm: str,
    ) -> bool:
        """Public-key-only verification. Caller supplies the algorithm written
        into the event's `_sig_alg` field. Returns False for HMAC sim (impossible
        without the secret) — call `verify_own` instead in that case.
        """
        if not signature_b64 or not public_key_b64:
            return False
        try:
            sig = base64.b64decode(signature_b64)
            pk = base64.b64decode(public_key_b64)
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        except (ValueError, AttributeError) as exc:
            logger.warning("verify decode failed: %s", exc)
            return False

        if algorithm == ALG_MLDSA65:
            try:
                from src.crypto.pqc_liboqs import MLDSA65, LIBOQS_AVAILABLE, PURE_PQC_AVAILABLE

                if not (LIBOQS_AVAILABLE or PURE_PQC_AVAILABLE):
                    return False
                v = MLDSA65()
                v._public_key = pk
                return bool(v.verify(canonical, sig))
            except (ImportError, RuntimeError, OSError, AttributeError):
                return False

        if algorithm == ALG_ED25519:
            try:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

                pk_obj = Ed25519PublicKey.from_public_bytes(pk)
                pk_obj.verify(sig, canonical)
                return True
            except Exception:  # noqa: BLE001
                return False

        # ALG_HMAC_SIM — public-key-only verify is impossible
        return False
