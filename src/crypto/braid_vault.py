"""
Braided key derivation experiment with authenticated vault entries.

Architecture:
  3 braid strands mapped to tongue pairs:
    Strand 0: KO x AV  (presence pair)
    Strand 1: RU x CA  (structure pair)
    Strand 2: UM x DR  (depth pair)

  Each strand carries two domain-separated PBKDF2-HMAC-SHA256 channels,
  at 120,000 and 160,000 iterations. They are not independent primitives.

  Braid-inspired operations (named after B_3 generators):
    sigma_1: cross strand 0 over strand 1  (mix with XOR + rotate)
    sigma_2: cross strand 1 over strand 2
    sigma_inv_1, sigma_inv_2: reverse-labelled mixing operations

  Key derivation = applying a braid word to the initial 3-strand state.
  Verification = applying the same braid word and checking equality.
  These rehashing operations are not a demonstrated B_3 group action: the
  reverse-labelled operations do not invert the state. No conjugacy-hardness,
  combined-hash-strength, or post-quantum reduction is claimed.

Version 2 entries use AES-256-GCM, binding entry identity and metadata. Legacy
unauthenticated XOR entries are rejected, not silently migrated. Key strength
still depends on secret entropy and the custom derivation needs external review.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ---------------------------------------------------------------------------
# Domain-separated derivation channels
# ---------------------------------------------------------------------------


def _h_a(data: bytes) -> bytes:
    """First PBKDF2-HMAC-SHA256 channel with a fixed domain label."""
    return hashlib.pbkdf2_hmac("sha256", data, b"braid-vault-h-a", 120_000, dklen=32)


def _h_b(data: bytes) -> bytes:
    """Second channel of the SAME primitive with a distinct domain label."""
    return hashlib.pbkdf2_hmac("sha256", data, b"braid-vault-h-b", 160_000, dklen=32)


def _dual_hash(data: bytes) -> Tuple[bytes, bytes]:
    """Derive through both domain-separated channels."""
    return _h_a(data), _h_b(data)


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    """XOR two equal-length byte strings."""
    return bytes(x ^ y for x, y in zip(a, b))


def _rotate_left(data: bytes, n: int) -> bytes:
    """Bitwise rotate left by n bits."""
    n = n % (len(data) * 8)
    byte_shift = n // 8
    bit_shift = n % 8
    result = bytearray(len(data))
    for i in range(len(data)):
        src = (i + byte_shift) % len(data)
        next_src = (src + 1) % len(data)
        result[i] = ((data[src] << bit_shift) | (data[next_src] >> (8 - bit_shift))) & 0xFF
    return bytes(result)


# ---------------------------------------------------------------------------
# Braid strand and crossing operations
# ---------------------------------------------------------------------------


@dataclass
class BraidStrand:
    """One strand carrying dual-hashed state."""

    h_a: bytes  # PBKDF2 domain a
    h_b: bytes  # PBKDF2 domain b

    def as_bytes(self) -> bytes:
        return self.h_a + self.h_b

    @classmethod
    def from_seed(cls, seed: bytes, context: bytes = b"") -> BraidStrand:
        keyed = seed + context
        return cls(h_a=_h_a(keyed), h_b=_h_b(keyed))

    def rehash(self) -> BraidStrand:
        """Feed each channel through the other domain's derivation."""
        return BraidStrand(
            h_a=_h_a(self.h_b),  # a-channel gets b's output through a
            h_b=_h_b(self.h_a),  # b-channel gets a's output through b
        )


class BraidCrossing(Enum):
    """Braid-inspired operation labels, not proven invertible generators."""

    SIGMA_1 = "s1"  # strand 0 over strand 1
    SIGMA_2 = "s2"  # strand 1 over strand 2
    SIGMA_1_INV = "s1i"  # strand 0 under strand 1
    SIGMA_2_INV = "s2i"  # strand 1 under strand 2


# Abstract B_3 satisfies the braid relation. This hash-based mixer does not
# establish that relation or inverse state operations; ordering is significant.


def _apply_crossing(strands: List[BraidStrand], crossing: BraidCrossing) -> List[BraidStrand]:
    """Apply a single braid crossing to the 3-strand state.

    Crossing mixes the two involved strands non-commutatively:
    - Over-strand gets XOR'd with under-strand's dual
    - Under-strand gets rotated by over-strand's entropy
    - Both get rehashed through the opposite channel
    """
    s = [BraidStrand(h_a=st.h_a, h_b=st.h_b) for st in strands]

    if crossing == BraidCrossing.SIGMA_1:
        # Strand 0 crosses over strand 1
        mixed_a = _xor_bytes(s[0].h_a, s[1].h_b)
        mixed_b = _xor_bytes(s[0].h_b, s[1].h_a)
        rotation = s[0].h_a[0] % 32 + 1
        s[0] = BraidStrand(h_a=_h_a(mixed_a), h_b=_h_b(mixed_b))
        s[1] = BraidStrand(
            h_a=_h_a(_rotate_left(s[1].h_a, rotation)),
            h_b=_h_b(_rotate_left(s[1].h_b, rotation)),
        )
        s[0], s[1] = s[1], s[0]  # topological swap

    elif crossing == BraidCrossing.SIGMA_2:
        # Strand 1 crosses over strand 2
        mixed_a = _xor_bytes(s[1].h_a, s[2].h_b)
        mixed_b = _xor_bytes(s[1].h_b, s[2].h_a)
        rotation = s[1].h_a[0] % 32 + 1
        s[1] = BraidStrand(h_a=_h_a(mixed_a), h_b=_h_b(mixed_b))
        s[2] = BraidStrand(
            h_a=_h_a(_rotate_left(s[2].h_a, rotation)),
            h_b=_h_b(_rotate_left(s[2].h_b, rotation)),
        )
        s[1], s[2] = s[2], s[1]

    elif crossing == BraidCrossing.SIGMA_1_INV:
        # Inverse: strand 0 under strand 1
        s[0], s[1] = s[1], s[0]
        mixed_a = _xor_bytes(s[0].h_b, s[1].h_a)
        mixed_b = _xor_bytes(s[0].h_a, s[1].h_b)
        rotation = s[1].h_b[0] % 32 + 1
        s[0] = BraidStrand(
            h_a=_h_a(_rotate_left(s[0].h_a, rotation)),
            h_b=_h_b(_rotate_left(s[0].h_b, rotation)),
        )
        s[1] = BraidStrand(h_a=_h_a(mixed_a), h_b=_h_b(mixed_b))

    elif crossing == BraidCrossing.SIGMA_2_INV:
        # Inverse: strand 1 under strand 2
        s[1], s[2] = s[2], s[1]
        mixed_a = _xor_bytes(s[1].h_b, s[2].h_a)
        mixed_b = _xor_bytes(s[1].h_a, s[2].h_b)
        rotation = s[2].h_b[0] % 32 + 1
        s[1] = BraidStrand(
            h_a=_h_a(_rotate_left(s[1].h_a, rotation)),
            h_b=_h_b(_rotate_left(s[1].h_b, rotation)),
        )
        s[2] = BraidStrand(h_a=_h_a(mixed_a), h_b=_h_b(mixed_b))

    return s


# ---------------------------------------------------------------------------
# Braid word — the topological key
# ---------------------------------------------------------------------------


@dataclass
class BraidWord:
    """A sequence of crossings forming the vault's combination.

    The word and master seed determine the final state. No reduction to
    a braid conjugacy problem has been established for this hash mixer.
    A generated word of length n has at most 2*n bits of selection entropy;
    it does not replace a high-entropy master secret.
    """

    crossings: List[BraidCrossing] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.crossings)

    def append(self, crossing: BraidCrossing) -> None:
        self.crossings.append(crossing)

    def encode(self) -> str:
        """Serialize to compact string: s1.s2.s1i.s2..."""
        return ".".join(c.value for c in self.crossings)

    @classmethod
    def decode(cls, encoded: str) -> BraidWord:
        """Deserialize from compact string."""
        lookup = {c.value: c for c in BraidCrossing}
        crossings = [lookup[tok] for tok in encoded.split(".") if tok]
        return cls(crossings=crossings)

    @classmethod
    def generate(cls, length: int = 12) -> BraidWord:
        """Generate a cryptographically random braid word."""
        options = list(BraidCrossing)
        entropy = os.urandom(length)
        crossings = [options[b % len(options)] for b in entropy]
        return cls(crossings=crossings)

    def inverse(self) -> BraidWord:
        """Reverse the symbolic word; this does NOT invert the hashed state."""
        inv_map = {
            BraidCrossing.SIGMA_1: BraidCrossing.SIGMA_1_INV,
            BraidCrossing.SIGMA_2: BraidCrossing.SIGMA_2_INV,
            BraidCrossing.SIGMA_1_INV: BraidCrossing.SIGMA_1,
            BraidCrossing.SIGMA_2_INV: BraidCrossing.SIGMA_2,
        }
        return BraidWord(crossings=[inv_map[c] for c in reversed(self.crossings)])


# ---------------------------------------------------------------------------
# Tongue-pair contexts for the three strands
# ---------------------------------------------------------------------------

TONGUE_PAIRS = [
    (b"KO", b"AV"),  # Strand 0: presence pair
    (b"RU", b"CA"),  # Strand 1: structure pair
    (b"UM", b"DR"),  # Strand 2: depth pair
]


def _init_strands(master_seed: bytes) -> List[BraidStrand]:
    """Initialize 3 strands from master seed, each keyed to a tongue pair."""
    strands = []
    for i, (t1, t2) in enumerate(TONGUE_PAIRS):
        context = t1 + b":" + t2 + struct.pack(">B", i)
        strands.append(BraidStrand.from_seed(master_seed, context))
    return strands


def _apply_braid(strands: List[BraidStrand], word: BraidWord) -> List[BraidStrand]:
    """Apply a complete braid word to a 3-strand state."""
    state = strands
    for crossing in word.crossings:
        state = _apply_crossing(state, crossing)
    return state


def _finalize(strands: List[BraidStrand]) -> bytes:
    """Collapse 3 strands into a single 32-byte vault key.

    Uses triadic mixing: hash all 6 channels (3 strands x 2 domains)
    through a final dual-hash round.
    """
    combined = b"".join(s.as_bytes() for s in strands)  # 192 bytes
    final_a = _h_a(combined)
    final_b = _h_b(combined)
    return _xor_bytes(final_a, final_b)


# ---------------------------------------------------------------------------
# Vault entry — what gets stored
# ---------------------------------------------------------------------------


@dataclass
class VaultEntry:
    """A single secret stored in the braid vault."""

    entry_id: str
    ciphertext: bytes  # AES-GCM ciphertext with authentication tag
    salt: bytes  # random salt mixed into derivation
    created_at: float
    expires_at: Optional[float] = None
    tongue_affinity: str = "KO"  # primary tongue for this entry
    metadata: Dict[str, Any] = field(default_factory=dict)
    nonce: bytes = b""  # Empty legacy nonces are explicitly rejected.
    format_version: int = 2

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at


# ---------------------------------------------------------------------------
# The Braid Vault
# ---------------------------------------------------------------------------


class BraidVault:
    """Custom ordered derivation followed by standard authenticated encryption.

    The vault derives encryption keys by applying a braid word (the master key)
    to a 3-strand state initialized from a seed. Each entry gets its own salt,
    producing a unique derived key per entry.

    Three strands are derived from the SAME master secret, not three independent
    secrets. Their 192-byte intermediate state is not 1536 bits of entropy.
    Integrity covers the ciphertext and entry metadata; replay of an entire old
    valid entry needs external freshness state. This in-memory class does not
    provide concurrent transactions, persistence protection or secure erasure.
    """

    def __init__(self, master_seed: bytes, braid_key: BraidWord) -> None:
        self._master_seed = master_seed
        self._braid_key = BraidWord(crossings=list(braid_key.crossings))
        self._entries: Dict[str, VaultEntry] = {}
        self._audit_log: List[Dict[str, Any]] = []

        # Derive the vault's master derived state
        init = _init_strands(master_seed)
        self._derived_strands = _apply_braid(init, braid_key)
        self._vault_key = _finalize(self._derived_strands)

    def _derive_entry_key(self, entry_id: str, salt: bytes, vault_key: Optional[bytes] = None) -> bytes:
        """Derive a per-entry encryption key from the vault key."""
        encoded_id = entry_id.encode("utf-8")
        material = b"scbe:braid-entry:v2\0" + (self._vault_key if vault_key is None else vault_key)
        material += struct.pack(">I", len(encoded_id)) + encoded_id + salt
        return _h_a(material)

    @staticmethod
    def _entry_aad(entry: VaultEntry) -> bytes:
        if (
            type(entry.format_version) is not int
            or entry.format_version != 2
            or not isinstance(entry.entry_id, str)
            or not entry.entry_id
            or not isinstance(entry.nonce, bytes)
            or len(entry.nonce) != 12
            or not isinstance(entry.salt, bytes)
            or len(entry.salt) != 32
            or not isinstance(entry.tongue_affinity, str)
            or not isinstance(entry.metadata, dict)
        ):
            raise ValueError("Unsupported or malformed authenticated vault entry")
        for stamp in (entry.created_at, entry.expires_at):
            if stamp is not None and (type(stamp) not in (int, float) or not math.isfinite(stamp)):
                raise ValueError("Invalid vault time")
        return json.dumps(
            {
                "domain": "scbe:braid-entry:v2",
                "version": entry.format_version,
                "entry_id": entry.entry_id,
                "salt": entry.salt.hex(),
                "created_at": entry.created_at,
                "expires_at": entry.expires_at,
                "tongue_affinity": entry.tongue_affinity,
                "metadata": entry.metadata,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    def _seal_entry(self, entry_id, secret, created_at, expires_at, tongue_affinity, metadata, vault_key=None):
        # Copy JSON metadata so later changes to the caller's dict cannot alter
        # the stored authenticated header. Non-JSON or nonfinite data rejects.
        metadata_copy = json.loads(json.dumps(metadata, allow_nan=False))
        entry = VaultEntry(
            entry_id, b"", os.urandom(32), created_at, expires_at, tongue_affinity, metadata_copy, os.urandom(12)
        )
        aad = self._entry_aad(entry)
        key = self._derive_entry_key(entry_id, entry.salt, vault_key)
        entry.ciphertext = AESGCM(key).encrypt(entry.nonce, secret, aad)
        return entry

    def _decrypt_entry(self, entry_id: str, entry: VaultEntry) -> bytes:
        try:
            if entry.entry_id != entry_id:
                raise ValueError("Entry identity mismatch")
            aad = self._entry_aad(entry)
            key = self._derive_entry_key(entry_id, entry.salt)
            return AESGCM(key).decrypt(entry.nonce, entry.ciphertext, aad)
        except (InvalidTag, ValueError, TypeError, OverflowError, AttributeError):
            raise ValueError("Vault entry authentication failed") from None

    def store(
        self,
        entry_id: str,
        secret: bytes,
        ttl_seconds: Optional[float] = None,
        tongue_affinity: str = "KO",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VaultEntry:
        """Store a secret in the vault."""
        if ttl_seconds is not None and (type(ttl_seconds) not in (int, float) or not math.isfinite(ttl_seconds)):
            raise ValueError("TTL must be finite")
        now = time.time()
        entry = self._seal_entry(
            entry_id,
            secret,
            now,
            now + ttl_seconds if ttl_seconds is not None else None,
            tongue_affinity,
            {} if metadata is None else metadata,
        )
        self._entries[entry_id] = entry
        self._log("store", entry_id)
        return entry

    def retrieve(self, entry_id: str) -> Optional[bytes]:
        """Retrieve and decrypt a secret from the vault."""
        entry = self._entries.get(entry_id)
        if entry is None:
            self._log("retrieve_miss", entry_id)
            return None

        plaintext = self._decrypt_entry(entry_id, entry)
        if entry.is_expired:
            self._log("retrieve_expired", entry_id)
            del self._entries[entry_id]
            return None

        self._log("retrieve", entry_id)
        return plaintext

    def rotate(self, entry_id: str, new_braid_key: BraidWord) -> Optional[VaultEntry]:
        """Rotate an entry's encryption under a new braid key.

        Decrypts ALL entries with the current key, re-derives the vault key
        from the new braid, then re-encrypts everything. This is necessary
        because all entries share a single vault key.
        """
        if entry_id not in self._entries:
            return None

        # Validate ALL records before changing the key or the entry map.
        decrypted = {}
        for eid, entry in self._entries.items():
            val = self._decrypt_entry(eid, entry)
            if not entry.is_expired:
                decrypted[eid] = (val, entry)

        # Re-derive vault state with new braid key
        init = _init_strands(self._master_seed)
        new_strands = _apply_braid(init, new_braid_key)
        new_vault_key = _finalize(new_strands)

        # Stage fresh ciphertext, keeping original authenticated lifetime.
        staged = {}
        for eid, (secret, old_entry) in decrypted.items():
            staged[eid] = self._seal_entry(
                eid,
                secret,
                old_entry.created_at,
                old_entry.expires_at,
                old_entry.tongue_affinity,
                old_entry.metadata,
                new_vault_key,
            )

        self._braid_key = BraidWord(crossings=list(new_braid_key.crossings))
        self._derived_strands = new_strands
        self._vault_key = new_vault_key
        self._entries = staged

        self._log("rotate", entry_id)
        return self._entries.get(entry_id)

    def revoke(self, entry_id: str) -> bool:
        """Revoke and destroy a vault entry."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            self._log("revoke", entry_id)
            return True
        return False

    def list_entries(self) -> List[str]:
        """List all non-expired entry IDs."""
        self._purge_expired()
        return list(self._entries.keys())

    def verify_braid(self, candidate: BraidWord) -> bool:
        """Verify a braid word matches the vault's key without exposing it."""
        init = _init_strands(self._master_seed)
        candidate_strands = _apply_braid(init, candidate)
        candidate_key = _finalize(candidate_strands)
        return hmac.compare_digest(candidate_key, self._vault_key)

    def strand_fingerprints(self) -> List[str]:
        """Return hex fingerprints of the 3 derived strands (for audit)."""
        return [hashlib.sha3_256(s.as_bytes()).hexdigest()[:16] for s in self._derived_strands]

    @property
    def braid_length(self) -> int:
        return len(self._braid_key)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def _expand_key(self, key: bytes, length: int) -> bytes:
        """Expand a 32-byte key to arbitrary length via HMAC-based KDF."""
        blocks = []
        counter = 0
        while len(b"".join(blocks)) < length:
            block = hmac.new(key, struct.pack(">I", counter), hashlib.sha3_256).digest()
            blocks.append(block)
            counter += 1
        return b"".join(blocks)[:length]

    def _purge_expired(self) -> None:
        expired = []
        for eid, entry in self._entries.items():
            self._decrypt_entry(eid, entry)
            if entry.is_expired:
                expired.append(eid)
        for eid in expired:
            del self._entries[eid]
            self._log("auto_purge", eid)

    def _log(self, action: str, entry_id: str) -> None:
        self._audit_log.append(
            {
                "action": action,
                "entry_id": entry_id,
                "timestamp": time.time(),
                "braid_len": len(self._braid_key),
                "entry_count": len(self._entries),
            }
        )


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def create_vault(passphrase: str, braid_length: int = 12) -> BraidVault:
    """Create a new vault from a passphrase with random braid key."""
    master_seed = _h_a(passphrase.encode("utf-8"))
    braid_key = BraidWord.generate(braid_length)
    return BraidVault(master_seed=master_seed, braid_key=braid_key)


def create_vault_deterministic(passphrase: str, braid_word: str) -> BraidVault:
    """Create a vault with a known braid word (for testing/recovery)."""
    master_seed = _h_a(passphrase.encode("utf-8"))
    braid_key = BraidWord.decode(braid_word)
    return BraidVault(master_seed=master_seed, braid_key=braid_key)
