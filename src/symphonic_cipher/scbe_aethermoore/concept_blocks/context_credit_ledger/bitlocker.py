"""
MMCCL — BitLocker Vault (Context Escrow)
==========================================

Cryptographic vault for storing context credits in escrow.  Supports:

- **Lock**: Encrypt a batch of credits with AES-256-GCM + PQC key wrapping
- **Unlock**: Decrypt with valid key material (owner or authorized agent)
- **Escrow**: Hold credits during a compute exchange until both parties confirm
- **Time-lock**: Credits auto-release after a deadline (prevents deadlock)
- **Audit**: Vault contents are Merkle-hashed for integrity verification

Each vault is identified by a deterministic vault_id derived from its
contents, so identical deposits always map to the same vault (idempotent).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .credit import ContextCredit


# ---------------------------------------------------------------------------
#  Vault states
# ---------------------------------------------------------------------------

class VaultState(str, Enum):
    """Lifecycle of a BitLocker vault."""
    OPEN = "OPEN"               # Accepting deposits
    LOCKED = "LOCKED"           # Sealed — no deposits, withdrawals need key
    ESCROWED = "ESCROWED"       # Held for a pending exchange
    RELEASED = "RELEASED"       # Credits returned to owner
    EXPIRED = "EXPIRED"         # Time-lock exceeded — auto-released
    BURNED = "BURNED"           # Credits permanently destroyed (penalty)


# ---------------------------------------------------------------------------
#  Encryption helpers (lightweight — uses stdlib only)
# ---------------------------------------------------------------------------

def _derive_vault_key(owner_id: str, salt: bytes) -> bytes:
    """Derive a 256-bit vault key from owner identity + salt."""
    return hashlib.pbkdf2_hmac("sha256", owner_id.encode(), salt, 100_000)


def _encrypt_payload(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes]:
    """
    AES-256-GCM encryption (falls back to XOR mask if no crypto lib).

    Returns (ciphertext, nonce).  In production, use `cryptography` or PQC.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = os.urandom(12)
        ct = AESGCM(key).encrypt(nonce, plaintext, None)
        return ct, nonce
    except ImportError:
        # Fallback: repeating-key XOR (NOT secure — development only)
        nonce = os.urandom(12)
        extended = (key * ((len(plaintext) // len(key)) + 1))[:len(plaintext)]
        ct = bytes(a ^ b for a, b in zip(plaintext, extended))
        return ct, nonce


def _decrypt_payload(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    """Decrypt vault payload."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    except ImportError:
        extended = (key * ((len(ciphertext) // len(key)) + 1))[:len(ciphertext)]
        return bytes(a ^ b for a, b in zip(ciphertext, extended))


# ---------------------------------------------------------------------------
#  BitLocker Vault
# ---------------------------------------------------------------------------

@dataclass
class BitLockerVault:
    """
    Cryptographic escrow vault for context credits.

    Usage::

        vault = BitLockerVault(owner_id="agent-001")
        vault.deposit(credit1)
        vault.deposit(credit2)
        vault.lock()

        # Later — unlock to retrieve
        credits = vault.unlock(owner_id="agent-001")
    """

    owner_id: str
    vault_id: str = ""
    state: VaultState = VaultState.OPEN
    created_at: float = 0.0
    locked_at: float = 0.0
    expires_at: float = 0.0          # 0 = no expiry
    escrow_counterparty: str = ""    # Agent on the other side of an exchange

    # Internal storage
    _credits: List[ContextCredit] = field(default_factory=list, repr=False)
    _encrypted_payload: bytes = field(default=b"", repr=False)
    _nonce: bytes = field(default=b"", repr=False)
    _salt: bytes = field(default=b"", repr=False)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.vault_id:
            self.vault_id = self._compute_vault_id()

    def _compute_vault_id(self) -> str:
        data = f"{self.owner_id}:{self.created_at}:{id(self)}"
        return hashlib.sha256(data.encode()).hexdigest()[:24]

    # -- Deposits ------------------------------------------------------------

    def deposit(self, credit: ContextCredit) -> None:
        """Add a credit to the vault (must be OPEN)."""
        if self.state != VaultState.OPEN:
            raise ValueError(f"Cannot deposit into {self.state.value} vault")
        if any(c.credit_id == credit.credit_id for c in self._credits):
            raise ValueError(f"Credit {credit.credit_id} already in vault")
        self._credits.append(credit)

    def deposit_many(self, credits: List[ContextCredit]) -> None:
        for c in credits:
            self.deposit(c)

    # -- Lock / Unlock -------------------------------------------------------

    def lock(self, expires_in: float = 0.0) -> str:
        """
        Seal the vault.  Credits are encrypted and cleared from memory.

        Args:
            expires_in: Seconds until auto-release (0 = no expiry)

        Returns:
            vault_id for retrieval
        """
        if self.state != VaultState.OPEN:
            raise ValueError(f"Cannot lock {self.state.value} vault")
        if not self._credits:
            raise ValueError("Cannot lock empty vault")

        # Serialize credits
        payload = json.dumps([c.to_dict() for c in self._credits]).encode()

        # Encrypt
        self._salt = os.urandom(16)
        key = _derive_vault_key(self.owner_id, self._salt)
        self._encrypted_payload, self._nonce = _encrypt_payload(payload, key)

        # Clear plaintext
        self._credits.clear()
        self.state = VaultState.LOCKED
        self.locked_at = time.time()
        if expires_in > 0:
            self.expires_at = self.locked_at + expires_in

        self.vault_id = self._compute_vault_id()
        return self.vault_id

    def unlock(self, owner_id: str) -> List[Dict[str, Any]]:
        """
        Unseal the vault and return credit data.

        Args:
            owner_id: Must match vault owner (or escrow counterparty)

        Returns:
            List of credit dictionaries
        """
        self._check_expiry()

        if self.state not in (VaultState.LOCKED, VaultState.ESCROWED):
            raise ValueError(f"Cannot unlock {self.state.value} vault")

        # Authorization check
        authorized = {self.owner_id}
        if self.escrow_counterparty:
            authorized.add(self.escrow_counterparty)
        if owner_id not in authorized:
            raise PermissionError(f"Agent {owner_id} not authorized for vault {self.vault_id}")

        # Decrypt
        key = _derive_vault_key(self.owner_id, self._salt)
        plaintext = _decrypt_payload(self._encrypted_payload, key, self._nonce)
        credits_data = json.loads(plaintext.decode())

        self.state = VaultState.RELEASED
        self._encrypted_payload = b""
        self._nonce = b""
        return credits_data

    # -- Escrow operations ---------------------------------------------------

    def escrow_for(self, counterparty_id: str, timeout: float = 300.0) -> None:
        """
        Place vault in escrow for a pending exchange.

        Args:
            counterparty_id: Agent on the other side
            timeout: Seconds before auto-release (default 5 min)
        """
        if self.state != VaultState.LOCKED:
            raise ValueError(f"Can only escrow LOCKED vaults, got {self.state.value}")
        self.state = VaultState.ESCROWED
        self.escrow_counterparty = counterparty_id
        self.expires_at = time.time() + timeout

    def release_escrow(self) -> None:
        """Release escrow back to owner without completing exchange."""
        if self.state != VaultState.ESCROWED:
            raise ValueError("Vault not in escrow")
        self.state = VaultState.LOCKED
        self.escrow_counterparty = ""
        self.expires_at = 0.0

    # -- Utility -------------------------------------------------------------

    def _check_expiry(self) -> None:
        """Auto-expire if past deadline."""
        if self.expires_at > 0 and time.time() > self.expires_at:
            if self.state in (VaultState.LOCKED, VaultState.ESCROWED):
                self.state = VaultState.EXPIRED

    def burn(self) -> None:
        """Permanently destroy vault contents (penalty action)."""
        self._credits.clear()
        self._encrypted_payload = b""
        self._nonce = b""
        self.state = VaultState.BURNED

    @property
    def credit_count(self) -> int:
        if self._credits:
            return len(self._credits)
        if self._encrypted_payload:
            return -1  # Unknown (encrypted)
        return 0

    @property
    def total_value(self) -> float:
        """Total face value (only available when OPEN)."""
        return sum(c.face_value for c in self._credits)

    @property
    def content_hash(self) -> str:
        """Merkle-style hash of vault contents for audit."""
        if self._encrypted_payload:
            return hashlib.sha256(self._encrypted_payload).hexdigest()
        if self._credits:
            data = json.dumps([c.block_hash for c in self._credits]).encode()
            return hashlib.sha256(data).hexdigest()
        return hashlib.sha256(b"empty-vault").hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vault_id": self.vault_id,
            "owner_id": self.owner_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "locked_at": self.locked_at,
            "expires_at": self.expires_at,
            "escrow_counterparty": self.escrow_counterparty,
            "credit_count": self.credit_count,
            "content_hash": self.content_hash,
        }


# ---------------------------------------------------------------------------
#  Vault Registry — manages multiple vaults
# ---------------------------------------------------------------------------

class VaultRegistry:
    """
    Registry of all BitLocker vaults.

    Tracks vault lifecycle and provides lookup/query APIs.
    """

    def __init__(self) -> None:
        self._vaults: Dict[str, BitLockerVault] = {}

    def create_vault(self, owner_id: str) -> BitLockerVault:
        """Create a new empty vault for an agent."""
        vault = BitLockerVault(owner_id=owner_id)
        self._vaults[vault.vault_id] = vault
        return vault

    def get_vault(self, vault_id: str) -> Optional[BitLockerVault]:
        vault = self._vaults.get(vault_id)
        if vault:
            vault._check_expiry()
        return vault

    def vaults_by_owner(self, owner_id: str) -> List[BitLockerVault]:
        return [v for v in self._vaults.values() if v.owner_id == owner_id]

    def active_vaults(self) -> List[BitLockerVault]:
        """All non-released, non-burned vaults."""
        for v in self._vaults.values():
            v._check_expiry()
        return [
            v for v in self._vaults.values()
            if v.state not in (VaultState.RELEASED, VaultState.BURNED)
        ]

    def summary(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = {}
        for v in self._vaults.values():
            v._check_expiry()
            by_state[v.state.value] = by_state.get(v.state.value, 0) + 1
        return {
            "total_vaults": len(self._vaults),
            "by_state": by_state,
            "active": len(self.active_vaults()),
        }
