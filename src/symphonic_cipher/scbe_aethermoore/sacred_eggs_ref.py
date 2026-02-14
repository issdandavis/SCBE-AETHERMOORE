"""
Sacred Eggs Reference Implementation (v4)
==========================================

Patent-hardened reference for the Sacred Eggs decrypt-or-noise gate.
Implements stateful predicates (geometric, oscillation, fractal) with
HKDF-based key derivation and fail-to-noise semantics.

Key patent-hardening decisions:
  - Fractal predicate uses "calibrated target dimension" (φ is one embodiment)
  - Fail-to-noise seeds from keyed PRF (not attacker-controlled state alone)
  - Canonical domain-separation tag for AEAD AAD
  - Ring bucketing matches Poincaré ball region model
  - Balanced ternary {T_FAIL=-1, T_HOLD=0, T_PASS=+1} for branchless aggregation

@layer Layer 8, Layer 13
@component Sacred Eggs Reference Gate (Python)
@version 4.0.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple
import hashlib
import hmac
import math
import struct


PHI = 1.61803398875

# Balanced ternary outputs
T_FAIL = -1
T_HOLD = 0
T_PASS = 1


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================


@dataclass(frozen=True)
class Policy:
    """Sacred Egg access policy — conjunction of predicates."""
    primary_tongue: str
    required_ring: int
    required_cell: str
    path_mode: str
    min_weight: float
    min_signatures: int
    req_oscillation_phase: int   # 0..5 or -1 for any valid current
    max_drift_variance: float
    require_phi_convergence: bool


@dataclass(frozen=True)
class SacredEgg:
    """Encrypted payload with policy-gated access."""
    id: str
    payload_cipher: bytes
    policy: Policy
    mac: bytes  # integrity tag for policy + cipher


@dataclass(frozen=True)
class StateSnapshot:
    """Historical navigation state at a point in time."""
    timestamp: int
    ring_index: int
    nav_vector: Tuple[float, float, float]


@dataclass
class StateVector:
    """21D brain state with trajectory history and attestations."""
    vector: Tuple[float, ...]   # length 21
    history: List[StateSnapshot]
    attestations: List[bytes]
    oscillation_state: int

    @property
    def nav_triad(self) -> Tuple[float, float, float]:
        return (self.vector[3], self.vector[4], self.vector[5])


# ==============================================================================
# HELPERS: HKDF + PRNG
# ==============================================================================


def hkdf_sha256(ikm: bytes, info: bytes, length: int = 32, salt: bytes = b"") -> bytes:
    """RFC 5869 HKDF with HMAC-SHA256."""
    if not salt:
        salt = b"\x00" * 32
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    out = b""
    t = b""
    c = 1
    while len(out) < length:
        t = hmac.new(prk, t + info + bytes([c]), hashlib.sha256).digest()
        out += t
        c += 1
    return out[:length]


def prng_stream(key: bytes, n: int) -> bytes:
    """Deterministic byte stream: HMAC(key, counter) blocks."""
    out = bytearray()
    counter = 0
    while len(out) < n:
        blk = hmac.new(key, struct.pack(">Q", counter), hashlib.sha256).digest()
        out.extend(blk)
        counter += 1
    return bytes(out[:n])


def hash_state(vec21: Sequence[float], osc: int) -> bytes:
    """Stable hash of the 21D state vector + oscillation phase."""
    m = hashlib.sha256()
    for x in vec21:
        m.update(struct.pack(">d", float(x)))
    m.update(struct.pack(">i", int(osc)))
    return m.digest()


def build_domain_separation_tag(policy: Policy, oscillation_state: int) -> bytes:
    """
    Canonical, byte-level domain separation tag.

    Format: SACRED_EGG_V4|tongue|ring|cell|path_mode|osc_phase
    """
    parts = [
        b"SACRED_EGG_V4",
        policy.primary_tongue.encode("utf-8"),
        str(policy.required_ring).encode("ascii"),
        policy.required_cell.encode("utf-8"),
        policy.path_mode.encode("utf-8"),
        str(int(oscillation_state)).encode("ascii"),
    ]
    return b"|".join(parts)


# ==============================================================================
# GEOMETRY + BUCKETING
# ==============================================================================


def norm3(v: Tuple[float, float, float]) -> float:
    """L2 norm of 3D vector."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def bucket_ring(radius: float) -> int:
    """
    Map Poincaré ball radius to ring index.

    Ring 0: core    r < 0.3   (safe center)
    Ring 1: inner   0.3 ≤ r < 0.7  (monitored)
    Ring 2: outer   0.7 ≤ r < 0.9  (high scrutiny)
    Ring 3: edge    0.9 ≤ r < 1.0  (harmonic wall)
    Ring 99: out-of-bounds  r ≥ 1.0
    """
    if radius < 0.3:
        return 0
    if radius < 0.7:
        return 1
    if radius < 0.9:
        return 2
    if radius < 1.0:
        return 3
    return 99  # out of bounds


def sphere_quantize(nav: Tuple[float, float, float]) -> str:
    """
    Quantize a 3D navigation vector to a discrete cell ID.

    Toy quantizer: maps [-1,1]³ to a grid of 64³ cells.
    Production: swap to HEALPix / octree / S2 geometry.
    """
    x, y, z = nav
    ix = int((x + 1.0) * 32)
    iy = int((y + 1.0) * 32)
    iz = int((z + 1.0) * 32)
    return f"S2:{ix:02d}{iy:02d}{iz:02d}"


def check_geometric_predicate(policy: Policy, state: StateVector) -> int:
    """
    Geometric predicate: radius ≤ required_ring AND cell matches.

    Returns T_PASS, T_HOLD, or T_FAIL.
    """
    r = norm3(state.nav_triad)
    if not math.isfinite(r) or r >= 1.0:
        return T_FAIL
    ring = bucket_ring(r)
    if ring > policy.required_ring:
        return T_FAIL
    cell = sphere_quantize(state.nav_triad)
    if cell != policy.required_cell:
        return T_FAIL
    return T_PASS


# ==============================================================================
# OSCILLATION PREDICATE
# ==============================================================================


def check_oscillation_predicate(
    policy: Policy,
    state: StateVector,
    now_fn: Callable[[], int],
    phase_window: int = 10,
) -> int:
    """
    Oscillation phase predicate: current phase must match state.

    Phase = (now // window) % 6, matching the 6 Sacred Tongue cycle.
    Detects replay attacks where oscillation_state is stale.
    """
    current_phase = (now_fn() // phase_window) % 6
    if policy.req_oscillation_phase != -1 and policy.req_oscillation_phase != current_phase:
        return T_FAIL
    return T_PASS if state.oscillation_state == current_phase else T_FAIL


# ==============================================================================
# FRACTAL PREDICATE (BOX COUNTING)
# ==============================================================================


def _normalize_points(
    points: Sequence[Tuple[float, float, float]],
) -> List[Tuple[float, float, float]]:
    """Normalize points to [0,1]³ for box counting."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    minz, maxz = min(zs), max(zs)

    rx = max(maxx - minx, 1e-12)
    ry = max(maxy - miny, 1e-12)
    rz = max(maxz - minz, 1e-12)

    return [((x - minx) / rx, (y - miny) / ry, (z - minz) / rz) for x, y, z in points]


def compute_box_counting_dimension(
    points: Sequence[Tuple[float, float, float]],
    scales: Sequence[int] = (2, 4, 8, 16),
    offsets: Sequence[Tuple[float, float, float]] = ((0.0, 0.0, 0.0), (0.5, 0.5, 0.5)),
) -> float:
    """
    3D box-counting fractal dimension with grid-offset optimization.

    For each scale s, counts occupied boxes across offset grids and
    takes the minimum (reduces grid-alignment artifacts). Returns
    the slope of log(N) vs log(s) via linear regression.

    Patent note: φ is one calibrated target; the predicate accepts
    any "predetermined target fractal dimension within a tolerance band."
    """
    if len(points) < 2:
        return 0.0

    pts = _normalize_points(points)
    logN: List[float] = []
    logS: List[float] = []

    for s in scales:
        best: Optional[int] = None
        for ox, oy, oz in offsets:
            occ = set()
            for x, y, z in pts:
                gx = int(math.floor((x + ox / s) * s))
                gy = int(math.floor((y + oy / s) * s))
                gz = int(math.floor((z + oz / s) * s))
                occ.add((gx, gy, gz))
            c = len(occ)
            best = c if best is None else min(best, c)
        best = max(best, 1)  # avoid log(0)
        logN.append(math.log(best))
        logS.append(math.log(float(s)))

    # Linear regression: slope of log(N) vs log(s)
    n = len(scales)
    mx = sum(logS) / n
    my = sum(logN) / n
    cov = sum((logS[i] - mx) * (logN[i] - my) for i in range(n))
    var = sum((logS[i] - mx) ** 2 for i in range(n))
    return cov / var if var > 0 else 0.0


def check_fractal_predicate(
    policy: Policy,
    state: StateVector,
    phi: float = PHI,
    eps: float = 0.05,
) -> int:
    """
    Fractal dimension predicate: trajectory must converge to target.

    Target dimension is φ by default (one embodiment). The predicate
    accepts any calibrated target within tolerance band eps.

    Returns:
      T_PASS  if |d - target| < eps
      T_HOLD  if |d - target| < 2*eps
      T_FAIL  otherwise or insufficient history
    """
    if not policy.require_phi_convergence:
        return T_PASS
    if len(state.history) < 10:
        return T_FAIL

    traj = [snap.nav_vector for snap in state.history]
    d = compute_box_counting_dimension(traj)
    dev = abs(d - phi)
    if dev < eps:
        return T_PASS
    if dev < (2 * eps):
        return T_HOLD
    return T_FAIL


# ==============================================================================
# HATCH CORE (decrypt-or-noise gate)
# ==============================================================================


class DecryptionError(Exception):
    """AEAD decryption failure."""
    pass


def toy_aead_decrypt(key: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    """
    TEST-ONLY toy AEAD.

    Format: body || tag (last 16 bytes)
    Tag = HMAC(key, aad || body)[:16]
    Plaintext = body XOR PRNG(key, len(body))
    """
    if len(ciphertext) < 16:
        raise DecryptionError("too short")
    body, tag = ciphertext[:-16], ciphertext[-16:]
    want = hmac.new(key, aad + body, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, want):
        raise DecryptionError("bad tag")
    keystream = prng_stream(key, len(body))
    return bytes(b ^ k for b, k in zip(body, keystream))


def hatch_ref(
    egg: SacredEgg,
    state: StateVector,
    shared_secret: bytes,
    *,
    now_fn: Callable[[], int],
) -> bytes:
    """
    Sacred Eggs HATCH gate: decrypt-or-noise.

    Evaluates geometric, oscillation, and fractal predicates.
    If all pass → derives decryption key from shared_secret + DST.
    If any fail → derives noise key from shared_secret + "NOISE" + state hash.

    Patent hardening (E): noise seed uses keyed PRF under shared_secret,
    not the attacker-controlled state vector alone. This prevents
    state oracles / distinguishers.

    Returns plaintext on success, deterministic noise on failure.
    Output is always body_length bytes (ciphertext minus 16-byte tag).
    """
    t_geo = check_geometric_predicate(egg.policy, state)
    t_osc = check_oscillation_predicate(egg.policy, state, now_fn=now_fn)
    t_drift = check_fractal_predicate(egg.policy, state)

    access_score = min(t_geo, t_osc, t_drift)
    can_unlock = access_score == T_PASS

    dst = build_domain_separation_tag(egg.policy, state.oscillation_state)
    aad = dst  # canonical AAD

    if can_unlock:
        key = hkdf_sha256(shared_secret, info=dst, length=32)
    else:
        # IMPORTANT: keyed noise seed — attacker cannot predict
        seed_material = hkdf_sha256(
            shared_secret,
            info=b"NOISE|" + dst + hash_state(state.vector, state.oscillation_state),
            length=32,
        )
        key = hkdf_sha256(seed_material, info=b"NOISE_FAIL", length=32)

    try:
        return toy_aead_decrypt(key, egg.payload_cipher, aad=aad)
    except DecryptionError:
        # Return deterministic noise of body length (not ciphertext length)
        body_len = max(len(egg.payload_cipher) - 16, 0)
        return prng_stream(key, body_len)
