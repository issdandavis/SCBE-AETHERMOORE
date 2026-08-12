"""Keyed, replay-resistant state chain for the trichromatic governance overlay.

WHY THIS EXISTS, stated plainly. The trichromatic overlay computes 63 values (6 tongues x 3
spectral bands, plus 15 cross-tongue bridges x 3 bands) and previously sealed them with:

    hashlib.blake2s(state_str.encode(), digest_size=16).hexdigest()

That is an **unkeyed 128-bit digest**. Anyone holding the state can recompute it, so it
authenticates nothing -- it is an integrity checksum, not a tag. The accompanying material also
counted ``63 * 8 = 504`` "bits of state" as though the channels were independent. They are not:
the 15 bridges are computed FROM the 6 tongues, so 45 of the 63 channels are deterministic
functions of the other 18. Channel count is **dimensionality**, not entropy, and it is not a
security bound.

THE SPLIT. Two layers with two different jobs, and neither one borrows the other's units:

    detection      the 63 trichromatic values. Anomaly-detection FEATURES. Real, useful, and
                   worth reporting as dimensions -- never as bits of security.
    authentication this module. One 256-bit master key, a keyed 256-bit BLAKE2s tag bound to
                   the canonical state, session id, monotonic counter, random nonce, and the
                   PREVIOUS tag. The chain is what blocks replay and reordering.

KEY DERIVATION AND WHAT IT DOES NOT BUY. Six tongue-specific keys plus one chain key are
derived from the single master via HKDF-SHA256 (RFC 5869) with distinct ``info`` labels.
Derivation gives **domain separation**, so a tag minted for one tongue cannot be replayed as
another. It does NOT multiply entropy: total security remains **256 bits**, bounded by the
master key. Reporting 6 x 256 = 1536 bits would be false, and this module's
``security_report()`` says so in a field rather than leaving it to prose.

DEFENSIBLE CLAIM, and the only one this code supports:

    63-dimensional trichromatic detection overlay with a 256-bit authenticated,
    replay-resistant state chain.

Related: ``src/governance/trichromatic_governance.py`` (the detection layer, unchanged).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from src.crypto.h_lwe import hkdf_sha256

from .orientation import Orientation, label_space_bits

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MASTER_KEY_BYTES = 32  # 256-bit master; the whole scheme's security bound
TAG_BYTES = 32  # BLAKE2s maximum digest -- 256-bit tag
NONCE_BYTES = 16
COUNTER_BYTES = 8

GENESIS_PREV_TAG = b"\x00" * TAG_BYTES

#: The six governance tongues. Order is fixed -- it is part of the derivation labels.
TONGUES: Tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")

#: BLAKE2s personalisation is capped at 8 bytes; this separates our tags from any other
#: BLAKE2s use in the codebase even under an identical key.
_PERSON = b"scbetri1"

_HKDF_SALT = b"scbe-trichromatic-state-chain-v1"


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


def _length_prefixed(*fields: bytes) -> bytes:
    """Unambiguously concatenate fields.

    Plain concatenation is forgeable by re-splitting: ``("ab", "c")`` and ``("a", "bc")``
    produce identical bytes, so a tag over one is a valid tag over the other. An 8-byte
    big-endian length before every field removes that.

    Args:
        *fields: Byte strings to join.

    Returns:
        The length-prefixed concatenation.
    """
    out = bytearray()
    for f in fields:
        out += len(f).to_bytes(8, "big")
        out += f
    return bytes(out)


def canonicalize(state: Any) -> bytes:
    """Serialise a state to one deterministic byte string.

    Two structurally equal states must produce identical bytes on any platform and any run,
    or the tag is not reproducible and verification becomes a coin flip.

    Args:
        state: Any JSON-serialisable object, or ``bytes``/``str`` taken verbatim.

    Returns:
        Canonical UTF-8 bytes.
    """
    if isinstance(state, bytes):
        return state
    if isinstance(state, str):
        return state.encode("utf-8")
    return json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def state_digest(state: Any) -> bytes:
    """Collision-resistant 256-bit digest of a canonical state (unkeyed, by design).

    The chain MACs this digest rather than the whole state, so an entry stays small. The
    digest is unkeyed on purpose -- confidentiality is not its job, and the keyed tag over it
    supplies the authentication.

    Args:
        state: Any value accepted by :func:`canonicalize`.

    Returns:
        32 raw bytes.
    """
    return hashlib.blake2s(canonicalize(state), digest_size=32).digest()


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------


def _require_master(master_key: bytes) -> bytes:
    if not isinstance(master_key, (bytes, bytearray)):
        raise TypeError("master_key must be bytes")
    if len(master_key) != MASTER_KEY_BYTES:
        raise ValueError(f"master_key must be exactly {MASTER_KEY_BYTES} bytes ({MASTER_KEY_BYTES * 8}-bit)")
    return bytes(master_key)


def generate_master_key() -> bytes:
    """Fresh 256-bit master key from the OS CSPRNG."""
    return os.urandom(MASTER_KEY_BYTES)


def derive_chain_key(master_key: bytes, session_id: str) -> bytes:
    """Derive the session's chain key.

    Args:
        master_key: The 256-bit master.
        session_id: Session identifier, bound into the label so two sessions never share a key.

    Returns:
        A 32-byte key.
    """
    _require_master(master_key)
    info = _length_prefixed(b"chain", session_id.encode("utf-8"))
    return hkdf_sha256(master_key, salt=_HKDF_SALT, info=info, length=32)


def derive_tongue_keys(master_key: bytes, session_id: str) -> Dict[str, bytes]:
    """Derive one key per tongue, domain-separated.

    Domain separation is the entire benefit: a tag minted under ``KO`` will not verify under
    ``AV``. This adds **no entropy** -- see :meth:`TrichromaticStateChain.security_report`.

    Args:
        master_key: The 256-bit master.
        session_id: Session identifier bound into every label.

    Returns:
        Mapping of tongue code to 32-byte key.
    """
    _require_master(master_key)
    keys: Dict[str, bytes] = {}
    for tongue in TONGUES:
        info = _length_prefixed(b"tongue", tongue.encode("ascii"), session_id.encode("utf-8"))
        keys[tongue] = hkdf_sha256(master_key, salt=_HKDF_SALT, info=info, length=32)
    return keys


# ---------------------------------------------------------------------------
# Chain
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChainEntry:
    """One authenticated link. ``tag`` covers every other field plus the previous tag."""

    counter: int
    nonce: bytes
    digest: bytes
    prev_tag: bytes
    tag: bytes
    tongue: str = ""
    #: Canonical multi-sign signature, e.g. ``"+-+"``. Bound under the tag but NOT under
    #: ``digest`` -- so re-orienting a state changes the tag and leaves the value untouched.
    orientation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Hex-encoded form, safe to log or ship."""
        return {
            "counter": self.counter,
            "nonce": self.nonce.hex(),
            "digest": self.digest.hex(),
            "prev_tag": self.prev_tag.hex(),
            "tag": self.tag.hex(),
            "tongue": self.tongue,
            "orientation": self.orientation,
        }


class ChainVerificationError(Exception):
    """Raised when a chain fails verification. Carries the reason, never the key."""


@dataclass
class TrichromaticStateChain:
    """A keyed, monotonic, replay-resistant chain of governance states.

    Each :meth:`append` binds the state digest to the session id, a strictly increasing
    counter, a fresh nonce, and the previous tag. Changing any of those changes the tag, so
    tampering, replay, reordering, and cross-session splicing all fail verification.
    """

    master_key: bytes
    session_id: str
    _chain_key: bytes = field(init=False, repr=False)
    _tongue_keys: Dict[str, bytes] = field(init=False, repr=False)
    _entries: List[ChainEntry] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        _require_master(self.master_key)
        if not self.session_id:
            raise ValueError("session_id must be non-empty -- it is bound into every tag")
        self._chain_key = derive_chain_key(self.master_key, self.session_id)
        self._tongue_keys = derive_tongue_keys(self.master_key, self.session_id)

    # -- internals ---------------------------------------------------------

    def _key_for(self, tongue: str) -> bytes:
        if not tongue:
            return self._chain_key
        if tongue not in self._tongue_keys:
            raise ValueError(f"unknown tongue {tongue!r}; expected one of {TONGUES}")
        return self._tongue_keys[tongue]

    def _compute_tag(
        self, *, counter: int, nonce: bytes, digest: bytes, prev_tag: bytes, tongue: str, orientation: str
    ) -> bytes:
        message = _length_prefixed(
            self.session_id.encode("utf-8"),
            counter.to_bytes(COUNTER_BYTES, "big"),
            nonce,
            digest,
            prev_tag,
            tongue.encode("ascii"),
            orientation.encode("ascii"),
        )
        return hashlib.blake2s(message, key=self._key_for(tongue), digest_size=TAG_BYTES, person=_PERSON).digest()

    # -- public API --------------------------------------------------------

    @property
    def entries(self) -> Tuple[ChainEntry, ...]:
        """The chain so far, oldest first."""
        return tuple(self._entries)

    @property
    def head_tag(self) -> bytes:
        """Tag of the most recent entry, or the genesis tag if empty."""
        return self._entries[-1].tag if self._entries else GENESIS_PREV_TAG

    def append(
        self,
        state: Any,
        *,
        tongue: str = "",
        orientation: Orientation | str | None = None,
        nonce: bytes | None = None,
    ) -> ChainEntry:
        """Authenticate a state and extend the chain.

        Args:
            state: Any value accepted by :func:`canonicalize`.
            tongue: Optional tongue code for domain separation; empty uses the chain key.
            orientation: Optional multi-sign orientation -- an :class:`Orientation` or a
                signature string like ``"+-+"``. Bound under the tag but deliberately kept out
                of the state digest, so re-orienting is a discrete change with no value change.
            nonce: Override the random nonce. For tests only -- production must let it default.

        Returns:
            The new :class:`ChainEntry`.
        """
        if nonce is None:
            nonce = os.urandom(NONCE_BYTES)
        elif len(nonce) != NONCE_BYTES:
            raise ValueError(f"nonce must be {NONCE_BYTES} bytes")

        if orientation is None:
            orient_str = ""
        elif isinstance(orientation, Orientation):
            orient_str = orientation.canonical
        else:
            orient_str = Orientation.parse(orientation).canonical  # validate, then canonicalise

        counter = len(self._entries) + 1
        prev_tag = self.head_tag
        digest = state_digest(state)
        tag = self._compute_tag(
            counter=counter, nonce=nonce, digest=digest, prev_tag=prev_tag, tongue=tongue, orientation=orient_str
        )

        entry = ChainEntry(
            counter=counter,
            nonce=nonce,
            digest=digest,
            prev_tag=prev_tag,
            tag=tag,
            tongue=tongue,
            orientation=orient_str,
        )
        self._entries.append(entry)
        return entry

    def verify_entry(self, entry: ChainEntry, *, expected_prev_tag: bytes, expected_counter: int) -> bool:
        """Constant-time check of one entry against its expected position.

        Args:
            entry: The entry to check.
            expected_prev_tag: The tag this entry must chain onto.
            expected_counter: The counter value this entry must carry.

        Returns:
            ``True`` only if the tag, the link, and the position all hold.
        """
        if entry.counter != expected_counter:
            return False
        if not hmac.compare_digest(entry.prev_tag, expected_prev_tag):
            return False
        try:
            expected = self._compute_tag(
                counter=entry.counter,
                nonce=entry.nonce,
                digest=entry.digest,
                prev_tag=entry.prev_tag,
                tongue=entry.tongue,
                orientation=entry.orientation,
            )
        except ValueError:
            return False
        return hmac.compare_digest(entry.tag, expected)

    def verify_chain(self, entries: Sequence[ChainEntry] | None = None) -> Tuple[bool, str]:
        """Verify a whole chain: every tag, every link, and strict counter monotonicity.

        Args:
            entries: Chain to check; defaults to this instance's own entries.

        Returns:
            ``(ok, reason)``. ``reason`` is ``"ok"`` on success, else a short diagnostic that
            never contains key material.
        """
        seq = list(self._entries if entries is None else entries)
        prev = GENESIS_PREV_TAG
        for i, entry in enumerate(seq):
            expected_counter = i + 1
            if entry.counter != expected_counter:
                return False, f"counter break at index {i}: got {entry.counter}, expected {expected_counter}"
            if not hmac.compare_digest(entry.prev_tag, prev):
                return False, f"broken link at index {i}: prev_tag does not match previous entry"
            if not self.verify_entry(entry, expected_prev_tag=prev, expected_counter=expected_counter):
                return False, f"bad tag at index {i}"
            prev = entry.tag
        return True, "ok"

    def verify_state(self, entry: ChainEntry, state: Any) -> bool:
        """Check that ``entry`` authenticates exactly ``state`` (catches substitution).

        Args:
            entry: A previously issued entry.
            state: The state it is claimed to cover.

        Returns:
            ``True`` if the digest matches and the tag is valid at that entry's position.
        """
        if not hmac.compare_digest(entry.digest, state_digest(state)):
            return False
        return self.verify_entry(entry, expected_prev_tag=entry.prev_tag, expected_counter=entry.counter)

    # -- honest accounting -------------------------------------------------

    @staticmethod
    def security_report(detection_dimensions: int = 63, *, orientation_arity: int = 6) -> Dict[str, Any]:
        """The security accounting, with the tempting overstatements explicitly denied.

        Args:
            detection_dimensions: Number of trichromatic detection features (default 63).
            orientation_arity: Axes in the multi-sign orientation (default 6, one per tongue).

        Returns:
            A dict whose keys name both what IS claimed and what is NOT.
        """
        return {
            "orientation_arity": orientation_arity,
            "orientation_states": 3**orientation_arity,
            "orientation_label_bits": label_space_bits(orientation_arity, allow_zero=True),
            "orientation_adds_security_bits": False,
            "orientation_note": (
                "orientation is a discrete direction label bound under the tag but outside the state "
                "digest; it distinguishes readings, it does not resist forgery"
            ),
            "tag_bits": TAG_BYTES * 8,
            "master_key_bits": MASTER_KEY_BYTES * 8,
            "security_bits": MASTER_KEY_BYTES * 8,
            "derived_keys": len(TONGUES) + 1,
            "derived_keys_add_entropy": False,
            "derived_keys_purpose": "domain separation only; security stays bounded by the master key",
            "claimed_security_bits_if_naively_summed": (len(TONGUES) + 1) * MASTER_KEY_BYTES * 8,
            "naive_sum_is_false": True,
            "forgery_probability_per_attempt": 2.0 ** -(TAG_BYTES * 8),
            "detection_dimensions": detection_dimensions,
            "detection_dimensions_are_entropy": False,
            "detection_dimensions_note": (
                "15 of the bridges are computed from the 6 tongues, so 45 of 63 channels are "
                "deterministic functions of the other 18; channel count is dimensionality, not entropy"
            ),
            "replay_resistant": True,
            "replay_mechanism": "monotonic counter + random nonce + previous-tag chaining, all under the tag",
            "defensible_claim": (
                f"{detection_dimensions}-dimensional trichromatic detection overlay with a "
                f"{TAG_BYTES * 8}-bit authenticated, replay-resistant state chain"
            ),
        }


def chain_from_entries(master_key: bytes, session_id: str, entries: Sequence[Mapping[str, Any]]) -> List[ChainEntry]:
    """Rebuild entries from their hex ``to_dict()`` form, for offline verification.

    Args:
        master_key: Unused here but required by callers that immediately verify; kept for a
            symmetric call signature.
        session_id: Unused here for the same reason.
        entries: Sequence of dicts as produced by :meth:`ChainEntry.to_dict`.

    Returns:
        Reconstructed entries in the given order.
    """
    del master_key, session_id  # reconstruction needs no secret; verification does
    out: List[ChainEntry] = []
    for e in entries:
        out.append(
            ChainEntry(
                counter=int(e["counter"]),
                nonce=bytes.fromhex(e["nonce"]),
                digest=bytes.fromhex(e["digest"]),
                prev_tag=bytes.fromhex(e["prev_tag"]),
                tag=bytes.fromhex(e["tag"]),
                tongue=e.get("tongue", ""),
                orientation=e.get("orientation", ""),
            )
        )
    return out
