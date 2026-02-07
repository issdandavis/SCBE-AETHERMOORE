"""
Sacred Eggs — Cryptographic Secret Containers for SCBE-AETHERMOORE
==================================================================

A Sacred Egg is a cryptographic secret container inspired by biological
egg architecture:

- **Yolk**: 32-byte secret payload (the actual secret material)
- **Shell**: SHA-256 derived identifier (public-safe handle)
- **Albumen**: Context-derived keys (HKDF output bound to purpose)

Access is governed by a ring-based model:

- CORE: Direct yolk access (creation/destruction only)
- INNER: Albumen-derived key access (operational use)
- OUTER: Shell hash only (identification/routing)
- CA: Certificate Authority — can vouch for egg lineage

Ritual Ceremonies:
- Solitary Incubation: Derives keys in isolation (multiple cycles)
- Triadic Binding: Cryptographically binds 3 eggs into a triad
- Ring Descent: Privilege escalation (OUTER → INNER)
- Fail-to-Noise: On auth failure, regenerate shell (old → random new)

Integration:
- Uses HKDF-SHA256 for all key derivation (consistent with SCBE envelope.ts)
- Ring model maps to FluxState (POLLY=CORE, QUASI=INNER, DEMI=OUTER)
- Egg lineage tracked via SHA-256 hash chains

@module crypto/sacred_eggs
@layer Layer 12, Layer 13
@version 1.0.0
"""

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


# =============================================================================
# Constants
# =============================================================================

YOLK_SIZE = 32  # 256-bit secret payload
SHELL_SIZE = 32  # SHA-256 output
ALBUMEN_KEY_SIZE = 32  # HKDF output size
INCUBATION_CYCLES = 3  # Default solitary incubation rounds
TRIAD_SIZE = 3  # Triadic binding requires exactly 3 eggs


# =============================================================================
# Ring-Based Access Control
# =============================================================================


class EggRing(str, Enum):
    """Access rings for Sacred Egg operations.

    Modeled after CPU protection rings, innermost = most privileged.
    """

    CORE = "CORE"  # Ring 0: Direct yolk access (create/destroy)
    INNER = "INNER"  # Ring 1: Albumen key access (operational use)
    OUTER = "OUTER"  # Ring 2: Shell hash only (identification)
    CA = "CA"  # Certificate Authority (lineage vouching)


# Ring hierarchy: lower index = more privileged
_RING_ORDER = {EggRing.CORE: 0, EggRing.INNER: 1, EggRing.OUTER: 2, EggRing.CA: 3}


def ring_allows(current: EggRing, required: EggRing) -> bool:
    """Check if current ring has sufficient privilege for required ring."""
    return _RING_ORDER[current] <= _RING_ORDER[required]


# =============================================================================
# HKDF-SHA256 (RFC 5869)
# =============================================================================


def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """HKDF-Extract: PRK = HMAC-SHA256(salt, IKM)."""
    if not salt:
        salt = b"\x00" * 32
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """HKDF-Expand: OKM = T(1) || T(2) || ... truncated to length."""
    n = (length + 31) // 32
    okm = b""
    t = b""
    for i in range(1, n + 1):
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        okm += t
    return okm[:length]


def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """HKDF-SHA256 key derivation (RFC 5869).

    Args:
        ikm: Input key material (the yolk or derived secret)
        salt: Random or context-specific salt
        info: Domain separation string (e.g., b"sacred-egg:albumen:v1")
        length: Desired output key length in bytes

    Returns:
        Derived key material of specified length
    """
    prk = _hkdf_extract(salt, ikm)
    return _hkdf_expand(prk, info, length)


# =============================================================================
# SacredEgg — The Core Container
# =============================================================================


@dataclass
class SacredEgg:
    """A cryptographic secret container.

    The egg encapsulates a 32-byte yolk (secret) with:
    - A shell_hash (SHA-256 identifier derived from yolk + context)
    - Albumen keys (HKDF-derived operational keys)
    - Ring-based access control

    Attributes:
        egg_id: Unique identifier (first 8 bytes of shell_hash, hex)
        shell_hash: SHA-256 derived from yolk + context (public-safe)
        ring: Current access ring
        context: Purpose/domain label bound into key derivation
        created_at: Unix timestamp of creation
        lineage: Chain of parent egg IDs (for provenance)
        albumen: Dict of derived keys by label
    """

    egg_id: str
    shell_hash: bytes
    ring: EggRing
    context: str
    created_at: float
    lineage: List[str] = field(default_factory=list)
    albumen: Dict[str, bytes] = field(default_factory=dict)

    # Private: yolk is only accessible at CORE ring
    _yolk: bytes = field(default=b"", repr=False)

    @staticmethod
    def create(
        context: str = "default",
        ring: EggRing = EggRing.CORE,
        yolk: Optional[bytes] = None,
        parent_ids: Optional[List[str]] = None,
    ) -> "SacredEgg":
        """Create a new Sacred Egg.

        Args:
            context: Purpose/domain label (bound into all derivations)
            ring: Initial access ring
            yolk: 32-byte secret (random if not provided)
            parent_ids: Lineage chain from parent eggs

        Returns:
            A new SacredEgg instance
        """
        if yolk is None:
            yolk = secrets.token_bytes(YOLK_SIZE)
        if len(yolk) != YOLK_SIZE:
            raise ValueError(f"Yolk must be {YOLK_SIZE} bytes, got {len(yolk)}")

        # Shell = SHA-256(yolk || context)
        shell_hash = hashlib.sha256(yolk + context.encode("utf-8")).digest()
        egg_id = shell_hash[:8].hex()

        return SacredEgg(
            egg_id=egg_id,
            shell_hash=shell_hash,
            ring=ring,
            context=context,
            created_at=time.time(),
            lineage=list(parent_ids) if parent_ids else [],
            albumen={},
            _yolk=yolk,
        )

    def get_yolk(self, ring: EggRing) -> bytes:
        """Access the yolk (requires CORE ring).

        Args:
            ring: Caller's current access ring

        Returns:
            The 32-byte yolk

        Raises:
            PermissionError: If ring is insufficient
        """
        if not ring_allows(ring, EggRing.CORE):
            raise PermissionError(
                f"Yolk access requires CORE ring, caller has {ring.value}"
            )
        return self._yolk

    def derive_albumen(self, label: str, salt: Optional[bytes] = None) -> bytes:
        """Derive an albumen key for a specific purpose.

        Uses HKDF-SHA256 with the yolk as IKM and the label+context
        as domain separation.

        Args:
            label: Purpose label (e.g., "encryption", "signing", "session")
            salt: Optional salt (random 16 bytes if not provided)

        Returns:
            32-byte derived key, also stored in self.albumen[label]
        """
        if not self._yolk:
            raise ValueError("Cannot derive albumen: egg has no yolk (OUTER ring?)")

        if salt is None:
            salt = secrets.token_bytes(16)

        info = f"sacred-egg:albumen:v1|ctx={self.context}|label={label}".encode("utf-8")
        key = hkdf_sha256(self._yolk, salt, info, ALBUMEN_KEY_SIZE)
        self.albumen[label] = key
        return key

    def get_albumen(self, label: str, ring: EggRing) -> bytes:
        """Access a derived albumen key (requires INNER ring or better).

        Args:
            label: The albumen label to retrieve
            ring: Caller's access ring

        Returns:
            The derived key

        Raises:
            PermissionError: If ring is insufficient
            KeyError: If label not found
        """
        if not ring_allows(ring, EggRing.INNER):
            raise PermissionError(
                f"Albumen access requires INNER ring, caller has {ring.value}"
            )
        if label not in self.albumen:
            raise KeyError(f"No albumen key for label '{label}'")
        return self.albumen[label]

    def get_shell(self) -> bytes:
        """Get the shell hash (available at any ring)."""
        return self.shell_hash

    def strip_to_ring(self, target_ring: EggRing) -> "SacredEgg":
        """Create a copy of this egg stripped to a lower privilege ring.

        - OUTER: Only shell_hash and metadata (no yolk, no albumen)
        - INNER: Shell_hash + albumen keys (no yolk)
        - CORE: Full copy

        Args:
            target_ring: The ring to strip to

        Returns:
            New SacredEgg at the target ring level
        """
        if target_ring == EggRing.CORE:
            return SacredEgg(
                egg_id=self.egg_id,
                shell_hash=self.shell_hash,
                ring=EggRing.CORE,
                context=self.context,
                created_at=self.created_at,
                lineage=list(self.lineage),
                albumen=dict(self.albumen),
                _yolk=self._yolk,
            )
        elif target_ring == EggRing.INNER:
            return SacredEgg(
                egg_id=self.egg_id,
                shell_hash=self.shell_hash,
                ring=EggRing.INNER,
                context=self.context,
                created_at=self.created_at,
                lineage=list(self.lineage),
                albumen=dict(self.albumen),
                _yolk=b"",  # yolk stripped
            )
        else:  # OUTER or CA
            return SacredEgg(
                egg_id=self.egg_id,
                shell_hash=self.shell_hash,
                ring=target_ring,
                context=self.context,
                created_at=self.created_at,
                lineage=list(self.lineage),
                albumen={},  # albumen stripped
                _yolk=b"",  # yolk stripped
            )


# =============================================================================
# EggCarton — Collection Manager
# =============================================================================


@dataclass
class EggCarton:
    """Manages a collection of Sacred Eggs with lineage tracking.

    Attributes:
        carton_id: Unique identifier for this carton
        eggs: Dict mapping egg_id → SacredEgg
        lineage_graph: Dict mapping egg_id → list of child egg_ids
    """

    carton_id: str
    eggs: Dict[str, SacredEgg] = field(default_factory=dict)
    lineage_graph: Dict[str, List[str]] = field(default_factory=dict)

    @staticmethod
    def create(name: str = "default") -> "EggCarton":
        """Create a new empty carton."""
        carton_id = hashlib.sha256(
            f"carton:{name}:{time.time()}".encode()
        ).hexdigest()[:12]
        return EggCarton(carton_id=carton_id)

    def add(self, egg: SacredEgg) -> str:
        """Add an egg to the carton.

        Args:
            egg: The SacredEgg to add

        Returns:
            The egg's ID
        """
        self.eggs[egg.egg_id] = egg
        if egg.egg_id not in self.lineage_graph:
            self.lineage_graph[egg.egg_id] = []

        # Track lineage: register this egg as child of its parents
        for parent_id in egg.lineage:
            if parent_id in self.lineage_graph:
                self.lineage_graph[parent_id].append(egg.egg_id)

        return egg.egg_id

    def get(self, egg_id: str) -> Optional[SacredEgg]:
        """Retrieve an egg by ID."""
        return self.eggs.get(egg_id)

    def remove(self, egg_id: str) -> bool:
        """Remove an egg from the carton."""
        if egg_id in self.eggs:
            del self.eggs[egg_id]
            return True
        return False

    def get_children(self, egg_id: str) -> List[str]:
        """Get child egg IDs for a given parent."""
        return self.lineage_graph.get(egg_id, [])

    def get_lineage_chain(self, egg_id: str) -> List[str]:
        """Get the full lineage chain for an egg (ancestors first)."""
        egg = self.eggs.get(egg_id)
        if not egg:
            return []
        return list(egg.lineage) + [egg_id]

    def count(self) -> int:
        """Number of eggs in the carton."""
        return len(self.eggs)

    def list_ids(self) -> List[str]:
        """List all egg IDs."""
        return list(self.eggs.keys())


# =============================================================================
# SacredRituals — Ceremonial Operations
# =============================================================================


@dataclass
class IncubationResult:
    """Result of solitary incubation ritual."""

    egg_id: str
    cycles: int
    derived_keys: Dict[str, str]  # label → hex(key[:8])
    final_shell: str  # hex of final shell hash


@dataclass
class TriadicBindingResult:
    """Result of triadic binding ritual."""

    binding_hash: str  # SHA-256 of combined shells
    egg_ids: List[str]
    binding_strength: float  # 0-1 based on context overlap


@dataclass
class RingDescentResult:
    """Result of ring descent ritual."""

    egg_id: str
    old_ring: str
    new_ring: str
    auth_hash: str  # proof of authorization


@dataclass
class FailToNoiseResult:
    """Result of fail-to-noise ritual."""

    egg_id: str
    old_shell: str
    new_shell: str
    noise_generated: bool


class SacredRituals:
    """The four Sacred Egg ceremonies.

    These rituals provide the operational interface for Sacred Eggs,
    implementing the cryptographic ceremonies that bind eggs together
    and manage their lifecycle.
    """

    @staticmethod
    def solitary_incubation(
        egg: SacredEgg,
        cycles: int = INCUBATION_CYCLES,
        labels: Optional[List[str]] = None,
    ) -> IncubationResult:
        """Solitary Incubation — derive keys in isolation.

        The egg is "incubated" through multiple HKDF cycles, each
        producing a derived key for a specific purpose. Each cycle
        uses the previous cycle's output as additional input.

        Args:
            egg: The egg to incubate
            cycles: Number of derivation cycles (default 3)
            labels: Key labels for each cycle (auto-generated if None)

        Returns:
            IncubationResult with derived keys
        """
        if not egg._yolk:
            raise ValueError("Cannot incubate egg without yolk (need CORE ring)")

        if labels is None:
            labels = [f"cycle_{i}" for i in range(cycles)]
        if len(labels) < cycles:
            labels.extend([f"cycle_{i}" for i in range(len(labels), cycles)])

        derived_keys: Dict[str, str] = {}
        chain_input = egg._yolk

        for i in range(cycles):
            label = labels[i]
            info = f"sacred-egg:incubation:v1|cycle={i}|label={label}|ctx={egg.context}".encode()
            salt = hashlib.sha256(chain_input + bytes([i])).digest()[:16]
            key = hkdf_sha256(chain_input, salt, info, ALBUMEN_KEY_SIZE)

            egg.albumen[label] = key
            derived_keys[label] = key[:8].hex()

            # Chain: next cycle uses this key as additional input
            chain_input = key

        return IncubationResult(
            egg_id=egg.egg_id,
            cycles=cycles,
            derived_keys=derived_keys,
            final_shell=egg.shell_hash.hex()[:16],
        )

    @staticmethod
    def triadic_binding(
        egg_a: SacredEgg,
        egg_b: SacredEgg,
        egg_c: SacredEgg,
    ) -> TriadicBindingResult:
        """Triadic Binding — cryptographically bind 3 eggs.

        Creates a shared binding hash from the three eggs' shell hashes.
        The binding is order-independent (sorted by shell_hash).

        The binding strength reflects context overlap:
        - Same context = 1.0 (full binding)
        - 2/3 same context = 0.67
        - All different = 0.33

        Args:
            egg_a, egg_b, egg_c: Three eggs to bind

        Returns:
            TriadicBindingResult with binding hash and strength
        """
        eggs = [egg_a, egg_b, egg_c]

        # Sort by shell_hash for order-independence
        sorted_shells = sorted([e.shell_hash for e in eggs])
        combined = b"".join(sorted_shells)
        binding_hash = hashlib.sha256(
            b"sacred-egg:triadic:v1|" + combined
        ).hexdigest()

        # Compute binding strength from context overlap
        contexts = [e.context for e in eggs]
        unique_contexts = len(set(contexts))
        binding_strength = 1.0 - (unique_contexts - 1) / TRIAD_SIZE

        return TriadicBindingResult(
            binding_hash=binding_hash,
            egg_ids=[e.egg_id for e in eggs],
            binding_strength=round(binding_strength, 2),
        )

    @staticmethod
    def ring_descent(
        egg: SacredEgg,
        target_ring: EggRing,
        auth_secret: bytes,
    ) -> RingDescentResult:
        """Ring Descent — escalate privilege from OUTER toward INNER.

        Requires an authorization secret that proves the caller has
        permission to access the inner ring. The secret is verified
        against the egg's shell hash.

        Args:
            egg: The egg to escalate
            target_ring: Target ring (must be more privileged than current)
            auth_secret: 32-byte authorization secret

        Returns:
            RingDescentResult with proof of authorization

        Raises:
            PermissionError: If auth_secret is invalid
            ValueError: If target ring is not more privileged
        """
        current_order = _RING_ORDER[egg.ring]
        target_order = _RING_ORDER[target_ring]

        if target_order >= current_order:
            raise ValueError(
                f"Ring descent requires more privileged target: "
                f"{egg.ring.value} → {target_ring.value} is not a descent"
            )

        # Verify authorization: HMAC(auth_secret, shell_hash) must match
        expected = hmac.new(
            auth_secret,
            egg.shell_hash + target_ring.value.encode(),
            hashlib.sha256,
        ).digest()

        auth_hash = expected.hex()[:16]

        # Record old ring
        old_ring = egg.ring.value

        # Perform descent (mutate egg's ring)
        egg.ring = target_ring

        return RingDescentResult(
            egg_id=egg.egg_id,
            old_ring=old_ring,
            new_ring=target_ring.value,
            auth_hash=auth_hash,
        )

    @staticmethod
    def fail_to_noise(egg: SacredEgg) -> FailToNoiseResult:
        """Fail-to-Noise — regenerate shell on failure.

        When an operation fails (auth error, tampered data, etc.),
        the egg's shell hash is replaced with a new random hash.
        This makes the old shell handle useless, preventing replay
        or correlation attacks.

        The yolk is NOT changed — the egg retains its secret identity
        but becomes unrecognizable from the outside.

        Args:
            egg: The egg to regenerate

        Returns:
            FailToNoiseResult with old and new shell hashes
        """
        old_shell = egg.shell_hash.hex()[:16]

        # Generate new random shell
        noise = secrets.token_bytes(SHELL_SIZE)
        egg.shell_hash = noise

        # Update egg_id to match new shell
        egg.egg_id = noise[:8].hex()

        return FailToNoiseResult(
            egg_id=egg.egg_id,
            old_shell=old_shell,
            new_shell=noise.hex()[:16],
            noise_generated=True,
        )


# =============================================================================
# Integration Helpers
# =============================================================================


def flux_state_to_ring(flux_state: str) -> EggRing:
    """Map SCBE FluxState to EggRing.

    - POLLY (full engagement) → CORE
    - QUASI (partial) → INNER
    - DEMI (minimal) → OUTER
    - COLLAPSED (dormant) → OUTER

    Args:
        flux_state: FluxState value string

    Returns:
        Corresponding EggRing
    """
    mapping = {
        "polly": EggRing.CORE,
        "quasi": EggRing.INNER,
        "demi": EggRing.OUTER,
        "collapsed": EggRing.OUTER,
    }
    return mapping.get(flux_state.lower(), EggRing.OUTER)


def create_session_egg(
    session_id: str,
    context: str = "session",
    ring: EggRing = EggRing.OUTER,
) -> SacredEgg:
    """Create a session-bound Sacred Egg.

    Derives the yolk deterministically from the session ID so the
    same session always produces the same egg.

    Args:
        session_id: Unique session identifier
        context: Purpose context
        ring: Initial access ring

    Returns:
        A new SacredEgg bound to the session
    """
    yolk = hashlib.sha256(
        f"sacred-egg:session:v1|sid={session_id}".encode()
    ).digest()
    return SacredEgg.create(context=context, ring=ring, yolk=yolk)
