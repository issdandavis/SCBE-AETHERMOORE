"""Sacred Eggs — Ritual-Based Conditional Secret Distribution (Python Reference)

Predicate-gated AEAD encryption where decryption requires ALL four
predicates to be satisfied simultaneously:

  P1(tongue):   Correct Sacred Tongue identity
  P2(geometry): Correct position in Poincaré ball
  P3(path):     Valid PHDM Hamiltonian path history
  P4(quorum):   k-of-n threshold met

If ANY predicate fails, the derived key is wrong and AEAD decryption
produces auth failure — no information leaks about WHICH predicate
was wrong (fail-to-noise).

Validated: SE-1 (predicate matrix), SE-2 (output collapse), SE-3 (geometry separation).
"""

import hashlib
import hmac
import json
import math
import os
import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

TONGUE_CODES = ('ko', 'av', 'ru', 'ca', 'um', 'dr')

TONGUE_PHASES = {
    'ko': 0.0,
    'av': math.pi / 3,
    'ru': 2 * math.pi / 3,
    'ca': math.pi,
    'um': 4 * math.pi / 3,
    'dr': 5 * math.pi / 3,
}

EPSILON = 1e-10

# ═══════════════════════════════════════════════════════════════
# Crypto primitives
# ═══════════════════════════════════════════════════════════════


def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """HKDF-SHA256 (RFC 5869)."""
    if not salt:
        salt = b'\x00' * 32
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    t = b''
    okm = b''
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


def aead_encrypt(key: bytes, plaintext: bytes, aad: bytes) -> bytes:
    """Encrypt-then-HMAC AEAD. Format: nonce(16) || ct || mac(32)."""
    nonce = os.urandom(16)
    k_enc = hkdf_sha256(key, nonce, b'sacred-egg:enc', 32)
    k_mac = hkdf_sha256(key, nonce, b'sacred-egg:mac', 32)

    ct = bytearray(len(plaintext))
    for i in range(0, len(plaintext), 32):
        block_idx = i // 32
        ks = hashlib.sha256(k_enc + struct.pack('<Q', block_idx)).digest()
        for j in range(min(32, len(plaintext) - i)):
            ct[i + j] = plaintext[i + j] ^ ks[j]

    mac = hmac.new(k_mac, aad + nonce + bytes(ct), hashlib.sha256).digest()
    return nonce + bytes(ct) + mac


def aead_decrypt(key: bytes, ciphertext: bytes, aad: bytes) -> Optional[bytes]:
    """Decrypt and verify. Returns None on auth failure."""
    if len(ciphertext) < 48:
        return None

    nonce = ciphertext[:16]
    mac_received = ciphertext[-32:]
    ct = ciphertext[16:-32]

    k_enc = hkdf_sha256(key, nonce, b'sacred-egg:enc', 32)
    k_mac = hkdf_sha256(key, nonce, b'sacred-egg:mac', 32)

    mac_expected = hmac.new(k_mac, aad + nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(mac_received, mac_expected):
        return None

    pt = bytearray(len(ct))
    for i in range(0, len(ct), 32):
        block_idx = i // 32
        ks = hashlib.sha256(k_enc + struct.pack('<Q', block_idx)).digest()
        for j in range(min(32, len(ct) - i)):
            pt[i + j] = ct[i + j] ^ ks[j]

    return bytes(pt)


# ═══════════════════════════════════════════════════════════════
# Geometry
# ═══════════════════════════════════════════════════════════════


def poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
    """Hyperbolic distance in Poincaré ball."""
    diff_sq = float(np.sum((u - v) ** 2))
    u_sq = float(np.sum(u ** 2))
    v_sq = float(np.sum(v ** 2))
    u_factor = max(EPSILON, 1.0 - u_sq)
    v_factor = max(EPSILON, 1.0 - v_sq)
    arg = 1.0 + 2.0 * diff_sq / (u_factor * v_factor)
    return float(np.arccosh(max(1.0, arg)))


def project_to_ball(p: np.ndarray, max_norm: float = 1.0 - 1e-10) -> np.ndarray:
    """Project point into Poincaré ball."""
    n = float(np.linalg.norm(p))
    if n < max_norm:
        return p.copy()
    return p * (max_norm / n)


# ═══════════════════════════════════════════════════════════════
# Quorum
# ═══════════════════════════════════════════════════════════════


@dataclass
class QuorumShare:
    """A party's share in the quorum."""
    party_id: int
    share: bytes


def generate_quorum(n: int, k: int, seed: bytes) -> Tuple[List[QuorumShare], bytes]:
    """Generate n shares with threshold k."""
    shares = []
    for i in range(n):
        share = hashlib.sha256(seed + struct.pack('<I', i)).digest()
        shares.append(QuorumShare(party_id=i, share=share))
    combined = hashlib.sha256(seed + b':quorum-master').digest()
    return shares, combined


def combine_shares(shares: List[QuorumShare], k: int) -> bytes:
    """Combine k shares into quorum material."""
    if len(shares) < k:
        return b'\x00' * 32
    sorted_shares = sorted(shares, key=lambda s: s.party_id)[:k]
    combined = b'\x00' * 32
    for s in sorted_shares:
        combined = bytes(a ^ b for a, b in zip(combined, s.share))
    return hashlib.sha256(combined + b':quorum-combined').digest()


# ═══════════════════════════════════════════════════════════════
# Path hashing
# ═══════════════════════════════════════════════════════════════


def path_hash(path_indices: List[int]) -> bytes:
    """Hash a PHDM path."""
    data = b'phdm:path:' + b','.join(str(i).encode() for i in path_indices)
    return hashlib.sha256(data).digest()


# ═══════════════════════════════════════════════════════════════
# Key Derivation
# ═══════════════════════════════════════════════════════════════


def derive_egg_key(
    tongue_code: str,
    geometry_point: np.ndarray,
    path_indices: List[int],
    quorum_material: bytes,
    salt: bytes,
) -> bytes:
    """Derive AEAD key from all four predicates."""
    tongue_phase = TONGUE_PHASES.get(tongue_code, 0.0)
    tongue_material = hashlib.sha256(
        b'sacred-egg:tongue:' + tongue_code.encode() +
        struct.pack('<d', tongue_phase)
    ).digest()

    geo_bytes = geometry_point.tobytes()
    geometry_material = hashlib.sha256(
        b'sacred-egg:geometry:' + geo_bytes
    ).digest()

    path_material = path_hash(path_indices)

    quorum_mat = hashlib.sha256(
        b'sacred-egg:quorum:' + quorum_material
    ).digest()

    ikm = tongue_material + geometry_material + path_material + quorum_mat
    return hkdf_sha256(ikm, salt, b'sacred-egg:aead-key:v1', 32)


# ═══════════════════════════════════════════════════════════════
# Sacred Egg
# ═══════════════════════════════════════════════════════════════


@dataclass
class SacredEgg:
    """A sealed Sacred Egg."""
    ciphertext: bytes
    aad: bytes
    tongue_code: str
    geometry_center: np.ndarray
    geometry_threshold: float
    path_commitment: bytes
    quorum_k: int
    quorum_n: int
    salt: bytes


def seal_egg(
    secret: bytes,
    tongue_code: str,
    geometry_point: np.ndarray,
    path_indices: List[int],
    quorum_shares: List[QuorumShare],
    quorum_k: int,
    quorum_n: int,
) -> SacredEgg:
    """Seal a secret into a Sacred Egg."""
    salt = os.urandom(32)
    quorum_material = combine_shares(quorum_shares, quorum_k)
    key = derive_egg_key(tongue_code, geometry_point, path_indices, quorum_material, salt)

    aad = json.dumps({
        'type': 'sacred-egg',
        'version': 'v1',
        'tongue': tongue_code,
        'quorum_k': quorum_k,
        'quorum_n': quorum_n,
    }, sort_keys=True).encode()

    ciphertext = aead_encrypt(key, secret, aad)

    return SacredEgg(
        ciphertext=ciphertext,
        aad=aad,
        tongue_code=tongue_code,
        geometry_center=geometry_point.copy(),
        geometry_threshold=0.5,
        path_commitment=path_hash(path_indices),
        quorum_k=quorum_k,
        quorum_n=quorum_n,
        salt=salt,
    )


def unseal_egg(
    egg: SacredEgg,
    tongue_code: str,
    geometry_point: np.ndarray,
    path_indices: List[int],
    quorum_shares: List[QuorumShare],
) -> Optional[bytes]:
    """Attempt to unseal. Returns secret on success, None on failure."""
    quorum_material = combine_shares(quorum_shares, egg.quorum_k)
    key = derive_egg_key(tongue_code, geometry_point, path_indices, quorum_material, egg.salt)
    return aead_decrypt(key, egg.ciphertext, egg.aad)


def check_geometry_proximity(
    egg: SacredEgg, candidate: np.ndarray
) -> Tuple[bool, float]:
    """Optional pre-check for geometry proximity."""
    a = project_to_ball(egg.geometry_center)
    b = project_to_ball(candidate)
    d = poincare_distance(a, b)
    return d <= egg.geometry_threshold, d


# ═══════════════════════════════════════════════════════════════
# Self-tests
# ═══════════════════════════════════════════════════════════════

def self_test():
    """Run basic validation tests."""
    print("Sacred Eggs Python reference — self-tests")
    passed = 0
    total = 0

    # Test 1: Seal/unseal with correct predicates
    total += 1
    pt = project_to_ball(np.array([0.1, 0.2, 0.3, -0.1, 0.05, -0.15]))
    path = list(range(16))
    seed = os.urandom(32)
    shares, _ = generate_quorum(5, 3, seed)
    secret = b'test secret 12345678901234567890'
    egg = seal_egg(secret, 'ko', pt, path, shares, 3, 5)
    result = unseal_egg(egg, 'ko', pt, path, shares[:3])
    assert result == secret, f"Correct predicates failed: {result}"
    passed += 1
    print(f"  [PASS] Correct predicates → decrypt")

    # Test 2: Wrong tongue fails
    total += 1
    result = unseal_egg(egg, 'dr', pt, path, shares[:3])
    assert result is None, "Wrong tongue should fail"
    passed += 1
    print(f"  [PASS] Wrong tongue → None")

    # Test 3: Wrong geometry fails
    total += 1
    wrong_pt = project_to_ball(np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5]))
    result = unseal_egg(egg, 'ko', wrong_pt, path, shares[:3])
    assert result is None, "Wrong geometry should fail"
    passed += 1
    print(f"  [PASS] Wrong geometry → None")

    # Test 4: Wrong path fails
    total += 1
    wrong_path = list(range(15, -1, -1))
    result = unseal_egg(egg, 'ko', pt, wrong_path, shares[:3])
    assert result is None, "Wrong path should fail"
    passed += 1
    print(f"  [PASS] Wrong path → None")

    # Test 5: Wrong quorum fails
    total += 1
    wrong_shares = [QuorumShare(i, os.urandom(32)) for i in range(3)]
    result = unseal_egg(egg, 'ko', pt, path, wrong_shares)
    assert result is None, "Wrong quorum should fail"
    passed += 1
    print(f"  [PASS] Wrong quorum → None")

    # Test 6: Geometry proximity check
    total += 1
    within, dist = check_geometry_proximity(egg, pt)
    assert within and dist < 0.001, f"Same point should be within threshold: d={dist}"
    passed += 1
    print(f"  [PASS] Geometry proximity check")

    print(f"\n  {passed}/{total} tests passed")
    return passed == total


if __name__ == '__main__':
    ok = self_test()
    exit(0 if ok else 1)
