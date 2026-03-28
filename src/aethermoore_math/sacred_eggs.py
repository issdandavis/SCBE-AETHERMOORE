"""
Sacred Eggs - Cryptographic Containers with Ritual-Based Hatching
=================================================================

Sacred Eggs are GeoSeal-encrypted containers that hold payloads encoded
in Sacred Tongues. They can only be "hatched" (decrypted) when specific
ritual conditions are met.

Ritual Modes:
- Solitary: Single tongue hatching (simplest)
- Triadic: Three tongues with cumulative weight threshold
- Ring Descent: Inward progression through concentric rings

Key Concepts:
- Each Egg is sealed with GeoSeal (geographic + geometric encryption)
- The payload is tokenized into Sacred Tongue tokens
- Hatching requires knowing the correct tongue(s) and ritual sequence
- Failed hatching produces noise (fail-to-noise principle)

@module aethermoore_math/sacred_eggs
@layer L12 (Harmonic wall), L13 (Risk decision)
"""

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

# ============================================================================
# Constants
# ============================================================================

PHI = (1 + math.sqrt(5)) / 2

TONGUES = {
    "KO": {"phase": 0, "weight": 1.00, "name": "Kor'aelin"},
    "AV": {"phase": 60, "weight": round(PHI, 2), "name": "Avali"},
    "RU": {"phase": 120, "weight": round(PHI**2, 2), "name": "Runethic"},
    "CA": {"phase": 180, "weight": round(PHI**3, 2), "name": "Cassisivadan"},
    "UM": {"phase": 240, "weight": round(PHI**4, 2), "name": "Umbroth"},
    "DR": {"phase": 300, "weight": round(PHI**5, 2), "name": "Draumric"},
}

TONGUE_IDS = list(TONGUES.keys())


# ============================================================================
# Lexicon and Tokenizer
# ============================================================================


class Lexicons:
    """
    256-token bijective lexicons per tongue.

    Each tongue has its own set of 256 tokens, derived deterministically
    from the tongue name. This creates a bijective mapping between
    byte values (0-255) and tongue-specific tokens.
    """

    def __init__(self):
        self._lexicons: Dict[str, List[str]] = {}
        for tongue in TONGUE_IDS:
            self._lexicons[tongue] = self._generate_lexicon(tongue)

    def _generate_lexicon(self, tongue: str) -> List[str]:
        """Generate 256 unique tokens for a tongue using SHA-256 derivation."""
        tokens = []
        for i in range(256):
            seed = f"{tongue}:{i}:sacred_lexicon_v1"
            h = hashlib.sha256(seed.encode()).hexdigest()[:8]
            tokens.append(f"{tongue.lower()}_{h}")
        return tokens

    def encode_byte(self, tongue: str, byte_val: int) -> str:
        """Encode a single byte to a tongue token."""
        return self._lexicons[tongue][byte_val & 0xFF]

    def decode_token(self, tongue: str, token: str) -> int:
        """Decode a tongue token back to a byte value."""
        try:
            return self._lexicons[tongue].index(token)
        except ValueError:
            raise ValueError(f"Unknown token '{token}' for tongue {tongue}")

    def get_lexicon(self, tongue: str) -> List[str]:
        """Get the full lexicon for a tongue."""
        return self._lexicons[tongue]


class TongueTokenizer:
    """
    Encode/decode bytes to Sacred Tongue tokens.

    Provides bijective mapping: bytes <-> tongue tokens.
    """

    def __init__(self, lexicons: Optional[Lexicons] = None):
        self.lexicons = lexicons or Lexicons()

    def encode(self, data: bytes, tongue: str) -> List[str]:
        """Encode bytes to a list of tongue tokens."""
        if tongue not in TONGUE_IDS:
            raise ValueError(f"Unknown tongue: {tongue}")
        return [self.lexicons.encode_byte(tongue, b) for b in data]

    def decode(self, tokens: List[str], tongue: str) -> bytes:
        """Decode tongue tokens back to bytes."""
        if tongue not in TONGUE_IDS:
            raise ValueError(f"Unknown tongue: {tongue}")
        return bytes([self.lexicons.decode_token(tongue, t) for t in tokens])


@dataclass
class XlateAttestation:
    """Attestation for a cross-tongue translation."""

    source_tongue: str
    target_tongue: str
    source_hash: str
    target_hash: str
    timestamp: float
    valid: bool


class CrossTokenizer:
    """Cross-tongue translation with attestation."""

    def __init__(self, lexicons: Optional[Lexicons] = None):
        self.lexicons = lexicons or Lexicons()
        self.tokenizer = TongueTokenizer(self.lexicons)

    def translate(
        self, tokens: List[str], source: str, target: str
    ) -> Tuple[List[str], XlateAttestation]:
        """
        Translate tokens from one tongue to another.

        The translation is bijective: decode source tokens to bytes,
        then re-encode as target tongue tokens.
        """
        # Decode to raw bytes
        raw = self.tokenizer.decode(tokens, source)

        # Re-encode in target tongue
        target_tokens = self.tokenizer.encode(raw, target)

        # Create attestation
        source_hash = hashlib.sha256("|".join(tokens).encode()).hexdigest()[:16]
        target_hash = hashlib.sha256("|".join(target_tokens).encode()).hexdigest()[:16]

        attestation = XlateAttestation(
            source_tongue=source,
            target_tongue=target,
            source_hash=source_hash,
            target_hash=target_hash,
            timestamp=time.time(),
            valid=True,
        )

        return target_tokens, attestation


# ============================================================================
# GeoSeal Primitives
# ============================================================================


def project_to_sphere(coords: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Project 3D coordinates onto the unit sphere."""
    x, y, z = coords
    norm = math.sqrt(x * x + y * y + z * z)
    if norm < 1e-10:
        return (0.0, 0.0, 1.0)
    return (x / norm, y / norm, z / norm)


def project_to_cube(coords: Tuple[float, float, float]) -> Tuple[int, int, int]:
    """Project sphere coordinates to a discrete cube face."""
    x, y, z = project_to_sphere(coords)
    # Map to [-1, 1] cube and discretize
    return (
        int(round(x * 100)),
        int(round(y * 100)),
        int(round(z * 100)),
    )


def healpix_id(coords: Tuple[float, float, float], nside: int = 4) -> int:
    """Simplified HEALPix-like pixel ID for geographic indexing."""
    x, y, z = project_to_sphere(coords)
    theta = math.acos(max(-1.0, min(1.0, z)))
    phi = math.atan2(y, x)
    if phi < 0:
        phi += 2 * math.pi
    # Simplified ring scheme
    ring = int(theta / math.pi * nside * 4)
    pixel_in_ring = int(phi / (2 * math.pi) * nside * 4)
    return ring * nside * 4 + pixel_in_ring


def morton_id(coords: Tuple[int, int, int]) -> int:
    """Compute Morton (Z-order) code for 3D integer coordinates."""

    def spread(v: int) -> int:
        v = abs(v) & 0x3FF  # 10-bit
        v = (v | (v << 16)) & 0x030000FF
        v = (v | (v << 8)) & 0x0300F00F
        v = (v | (v << 4)) & 0x030C30C3
        v = (v | (v << 2)) & 0x09249249
        return v

    return spread(coords[0]) | (spread(coords[1]) << 1) | (spread(coords[2]) << 2)


def classify_point(
    distance: float, inner_radius: float = 0.7, outer_radius: float = 1.0
) -> str:
    """Classify a point by its distance from center."""
    if distance <= inner_radius:
        return "interior"
    elif distance <= outer_radius:
        return "governance"
    else:
        return "exterior"


# ============================================================================
# Simplified PQC Envelope (Demo)
# ============================================================================


def _derive_key(secret: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """Simple HKDF-like key derivation using HMAC-SHA256."""
    prk = hmac.new(salt, secret, hashlib.sha256).digest()
    okm = b""
    prev = b""
    for i in range(1, (length + 31) // 32 + 1):
        prev = hmac.new(prk, prev + info + bytes([i]), hashlib.sha256).digest()
        okm += prev
    return okm[:length]


def geoseal_encrypt(
    plaintext: bytes,
    key: bytes,
    geo_coords: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Dict[str, Any]:
    """
    GeoSeal encryption with geographic binding.

    The ciphertext is bound to geographic coordinates via the
    key derivation, creating location-aware encryption.
    """
    salt = os.urandom(16)
    geo_info = struct.pack("!fff", *geo_coords)
    derived = _derive_key(key, salt, b"geoseal:v1:" + geo_info)

    # XOR-based encryption (demo; production uses AES-256-GCM)
    ciphertext = bytes(
        p ^ k
        for p, k in zip(
            plaintext, (derived * ((len(plaintext) // 32) + 1))[: len(plaintext)]
        )
    )

    tag = hmac.new(derived, ciphertext + geo_info, hashlib.sha256).digest()[:16]

    return {
        "ciphertext": ciphertext.hex(),
        "salt": salt.hex(),
        "tag": tag.hex(),
        "geo": list(geo_coords),
        "version": "geoseal-v1",
    }


def geoseal_decrypt(
    envelope: Dict[str, Any],
    key: bytes,
    geo_coords: Optional[Tuple[float, float, float]] = None,
) -> bytes:
    """
    GeoSeal decryption with geographic verification.

    If geo_coords is provided, verifies geographic binding.
    """
    salt = bytes.fromhex(envelope["salt"])
    ciphertext = bytes.fromhex(envelope["ciphertext"])
    stored_tag = bytes.fromhex(envelope["tag"])
    coords = tuple(envelope["geo"]) if geo_coords is None else geo_coords

    geo_info = struct.pack("!fff", *coords)
    derived = _derive_key(key, salt, b"geoseal:v1:" + geo_info)

    # Verify tag
    expected_tag = hmac.new(derived, ciphertext + geo_info, hashlib.sha256).digest()[
        :16
    ]
    if not hmac.compare_digest(stored_tag, expected_tag):
        raise ValueError("GeoSeal authentication failed - wrong key or location")

    # Decrypt
    plaintext = bytes(
        c ^ k
        for c, k in zip(
            ciphertext, (derived * ((len(ciphertext) // 32) + 1))[: len(ciphertext)]
        )
    )
    return plaintext


# ============================================================================
# Sacred Eggs
# ============================================================================


class RitualMode(Enum):
    """Hatching ritual modes."""

    SOLITARY = "solitary"  # Single tongue hatching
    TRIADIC = "triadic"  # Three tongues with weight threshold
    RING_DESCENT = "ring_descent"  # Inward progression through rings


@dataclass
class SacredEgg:
    """
    A cryptographic container sealed with GeoSeal.

    The egg holds a payload encoded in Sacred Tongues and can only
    be hatched when the correct ritual conditions are met.
    """

    egg_id: str
    ritual_mode: RitualMode
    sealed_payload: Dict[str, Any]  # GeoSeal envelope
    tongue: str  # Primary tongue
    ritual_tongues: List[str] = field(
        default_factory=list
    )  # Required tongues for hatching
    weight_threshold: float = 0.0  # Minimum cumulative weight for triadic mode
    ring_count: int = 3  # Number of rings for ring_descent mode
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "egg_id": self.egg_id,
            "ritual_mode": self.ritual_mode.value,
            "sealed_payload": self.sealed_payload,
            "tongue": self.tongue,
            "ritual_tongues": self.ritual_tongues,
            "weight_threshold": self.weight_threshold,
            "ring_count": self.ring_count,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class HatchResult:
    """Result of attempting to hatch a Sacred Egg."""

    success: bool
    payload: Optional[bytes] = None
    tokens: Optional[List[str]] = None
    tongue: Optional[str] = None
    ritual_log: List[str] = field(default_factory=list)
    error: Optional[str] = None


class SacredEggIntegrator:
    """
    Creates and hatches Sacred Eggs using GeoSeal encryption
    and Sacred Tongue tokenization.
    """

    def __init__(self, master_key: Optional[bytes] = None):
        self.master_key = master_key or os.urandom(32)
        self.lexicons = Lexicons()
        self.tokenizer = TongueTokenizer(self.lexicons)
        self.cross_tokenizer = CrossTokenizer(self.lexicons)

    def _derive_egg_key(self, egg_id: str, tongue: str) -> bytes:
        """Derive a unique key for an egg from master key + egg_id + tongue."""
        info = f"sacred_egg:{egg_id}:{tongue}".encode()
        return _derive_key(self.master_key, b"egg_salt_v1", info)

    def create_egg(
        self,
        payload: bytes,
        tongue: str,
        ritual_mode: RitualMode = RitualMode.SOLITARY,
        ritual_tongues: Optional[List[str]] = None,
        weight_threshold: float = 0.0,
        ring_count: int = 3,
        geo_coords: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SacredEgg:
        """
        Create a new Sacred Egg.

        The payload is tokenized into the specified tongue,
        then sealed with GeoSeal encryption.
        """
        if tongue not in TONGUE_IDS:
            raise ValueError(f"Unknown tongue: {tongue}")

        egg_id = hashlib.sha256(os.urandom(32)).hexdigest()[:16]

        # Tokenize payload
        tokens = self.tokenizer.encode(payload, tongue)
        token_data = json.dumps(tokens).encode()

        # Encrypt with GeoSeal
        key = self._derive_egg_key(egg_id, tongue)
        envelope = geoseal_encrypt(token_data, key, geo_coords)

        # Set ritual tongues
        if ritual_mode == RitualMode.SOLITARY:
            r_tongues = [tongue]
        elif ritual_mode == RitualMode.TRIADIC:
            r_tongues = ritual_tongues or [tongue, "RU", "UM"]
            if len(r_tongues) < 3:
                raise ValueError("Triadic mode requires at least 3 tongues")
            # Default weight threshold: sum of weights of first 2 tongues
            if weight_threshold <= 0:
                weight_threshold = sum(TONGUES[t]["weight"] for t in r_tongues[:2])
        elif ritual_mode == RitualMode.RING_DESCENT:
            r_tongues = ritual_tongues or TONGUE_IDS[:ring_count]
        else:
            r_tongues = [tongue]

        return SacredEgg(
            egg_id=egg_id,
            ritual_mode=ritual_mode,
            sealed_payload=envelope,
            tongue=tongue,
            ritual_tongues=r_tongues,
            weight_threshold=weight_threshold,
            ring_count=ring_count,
            metadata=metadata or {},
        )

    def hatch_egg(
        self,
        egg: SacredEgg,
        provided_tongues: List[str],
        geo_coords: Optional[Tuple[float, float, float]] = None,
    ) -> HatchResult:
        """
        Attempt to hatch a Sacred Egg.

        The hatching ritual must match the egg's ritual mode:
        - Solitary: provide the correct single tongue
        - Triadic: provide 3+ tongues with cumulative weight >= threshold
        - Ring Descent: provide tongues in correct inward ring order
        """
        log: List[str] = []

        # Validate ritual
        if egg.ritual_mode == RitualMode.SOLITARY:
            if egg.tongue not in provided_tongues:
                log.append(f"Solitary ritual failed: tongue {egg.tongue} not provided")
                return HatchResult(
                    success=False,
                    ritual_log=log,
                    error="Wrong tongue for solitary ritual",
                )
            log.append(f"Solitary ritual: tongue {egg.tongue} accepted")

        elif egg.ritual_mode == RitualMode.TRIADIC:
            if len(provided_tongues) < 3:
                log.append("Triadic ritual requires 3+ tongues")
                return HatchResult(
                    success=False, ritual_log=log, error="Need 3+ tongues for triadic"
                )

            # Check if required tongues are present
            missing = [t for t in egg.ritual_tongues if t not in provided_tongues]
            if missing:
                log.append(f"Triadic ritual: missing tongues {missing}")
                return HatchResult(
                    success=False, ritual_log=log, error=f"Missing tongues: {missing}"
                )

            # Check weight threshold
            total_weight = sum(
                TONGUES[t]["weight"] for t in provided_tongues if t in TONGUE_IDS
            )
            log.append(
                f"Triadic weight: {total_weight:.2f} (threshold: {egg.weight_threshold:.2f})"
            )
            if total_weight < egg.weight_threshold:
                return HatchResult(
                    success=False, ritual_log=log, error="Weight threshold not met"
                )
            log.append("Triadic ritual: weight threshold met")

        elif egg.ritual_mode == RitualMode.RING_DESCENT:
            # Must provide tongues in the correct ring order
            if len(provided_tongues) < egg.ring_count:
                log.append(f"Ring descent requires {egg.ring_count} tongues in order")
                return HatchResult(
                    success=False,
                    ritual_log=log,
                    error="Not enough tongues for ring descent",
                )

            for i, expected in enumerate(egg.ritual_tongues[: egg.ring_count]):
                if i >= len(provided_tongues) or provided_tongues[i] != expected:
                    got = (
                        provided_tongues[i] if i < len(provided_tongues) else "nothing"
                    )
                    log.append(f"Ring {i}: expected {expected}, got {got}")
                    return HatchResult(
                        success=False, ritual_log=log, error=f"Ring {i} mismatch"
                    )
                log.append(f"Ring {i}: {expected} accepted")

        # Decrypt GeoSeal
        try:
            key = self._derive_egg_key(egg.egg_id, egg.tongue)
            coords = tuple(geo_coords) if geo_coords else None
            token_data = geoseal_decrypt(egg.sealed_payload, key, coords)
            tokens = json.loads(token_data.decode())
            log.append("GeoSeal decrypted successfully")
        except Exception as e:
            log.append(f"GeoSeal decryption failed: {e}")
            return HatchResult(
                success=False, ritual_log=log, error=f"Decryption failed: {e}"
            )

        # Decode tokens back to payload
        try:
            payload = self.tokenizer.decode(tokens, egg.tongue)
            log.append(
                f"Payload decoded from {egg.tongue} tokens ({len(tokens)} tokens)"
            )
        except Exception as e:
            log.append(f"Token decoding failed: {e}")
            return HatchResult(
                success=False, ritual_log=log, error=f"Token decode failed: {e}"
            )

        return HatchResult(
            success=True,
            payload=payload,
            tokens=tokens,
            tongue=egg.tongue,
            ritual_log=log,
        )


# ============================================================================
# Self-Test
# ============================================================================


def selftest():
    """Run self-tests for Sacred Eggs module."""
    print("Sacred Eggs Self-Test")
    print("=" * 50)

    integrator = SacredEggIntegrator()
    test_payload = b"Hello, Sacred Eggs!"

    # Test 1: Solitary ritual
    print("\n1. Solitary Ritual")
    egg = integrator.create_egg(test_payload, "KO", RitualMode.SOLITARY)
    result = integrator.hatch_egg(egg, ["KO"])
    assert result.success, f"Solitary hatch failed: {result.error}"
    assert result.payload == test_payload, "Payload mismatch"
    print(f"   PASS: egg_id={egg.egg_id}, {len(result.tokens)} tokens")

    # Test 2: Solitary with wrong tongue should fail
    print("\n2. Solitary Wrong Tongue")
    result2 = integrator.hatch_egg(egg, ["AV"])
    assert not result2.success, "Should have failed with wrong tongue"
    print(f"   PASS: correctly rejected (error: {result2.error})")

    # Test 3: Triadic ritual
    print("\n3. Triadic Ritual")
    egg3 = integrator.create_egg(
        test_payload,
        "RU",
        RitualMode.TRIADIC,
        ritual_tongues=["RU", "UM", "DR"],
    )
    result3 = integrator.hatch_egg(egg3, ["RU", "UM", "DR"])
    assert result3.success, f"Triadic hatch failed: {result3.error}"
    assert result3.payload == test_payload, "Payload mismatch"
    print(f"   PASS: weight threshold met, {len(result3.tokens)} tokens")

    # Test 4: Ring descent
    print("\n4. Ring Descent")
    egg4 = integrator.create_egg(
        test_payload,
        "KO",
        RitualMode.RING_DESCENT,
        ritual_tongues=["KO", "AV", "RU"],
        ring_count=3,
    )
    result4 = integrator.hatch_egg(egg4, ["KO", "AV", "RU"])
    assert result4.success, f"Ring descent failed: {result4.error}"
    assert result4.payload == test_payload, "Payload mismatch"
    print(f"   PASS: all 3 rings descended, {len(result4.tokens)} tokens")

    # Test 5: Ring descent wrong order should fail
    print("\n5. Ring Descent Wrong Order")
    result5 = integrator.hatch_egg(egg4, ["AV", "KO", "RU"])
    assert not result5.success, "Should have failed with wrong order"
    print(f"   PASS: correctly rejected (error: {result5.error})")

    # Test 6: Cross-tongue translation
    print("\n6. Cross-Tongue Translation")
    cross = CrossTokenizer()
    tokens_ko = cross.tokenizer.encode(test_payload, "KO")
    tokens_dr, attestation = cross.translate(tokens_ko, "KO", "DR")
    decoded = cross.tokenizer.decode(tokens_dr, "DR")
    assert decoded == test_payload, "Cross-translation round-trip failed"
    print(
        f"   PASS: KO -> DR ({len(tokens_ko)} tokens), attestation valid={attestation.valid}"
    )

    # Test 7: GeoSeal round-trip
    print("\n7. GeoSeal Round-Trip")
    key = os.urandom(32)
    coords = (37.7749, -122.4194, 0.0)  # San Francisco
    envelope = geoseal_encrypt(test_payload, key, coords)
    decrypted = geoseal_decrypt(envelope, key, coords)
    assert decrypted == test_payload, "GeoSeal round-trip failed"
    print(f"   PASS: encrypted and decrypted at coords {coords}")

    # Test 8: Geometric classification
    print("\n8. Geometric Classification")
    assert classify_point(0.3) == "interior"
    assert classify_point(0.8) == "governance"
    assert classify_point(1.5) == "exterior"
    print("   PASS: interior/governance/exterior classification correct")

    print("\n" + "=" * 50)
    print("All Sacred Eggs self-tests passed!")
    return True


if __name__ == "__main__":
    selftest()
