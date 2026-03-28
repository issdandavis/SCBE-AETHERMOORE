#!/usr/bin/env python3
"""
SCBE Spaceflight Module -- Deep-Space Protocol Analogies
=========================================================

Maps core SCBE-AETHERMOORE cryptographic and governance concepts onto
physically-grounded spaceflight metaphors.  Every class in this module has
a 1:1 correspondence with an SCBE architectural element:

    DelayTolerantBundle  ->  Store-and-forward relay (custody transfer)
    HyperbolicTrajectory ->  Hyperbolic geometry in 6D harmonic space (L5-L7)
    DockingProtocol      ->  Mutual authentication state machine (RWP handshake)
    ReentryShield        ->  Ablative one-time-token boundary crossing (L12 wall)
    StarTracker          ->  Certificate authority / star-catalog verification
    ConstellationFleet   ->  BFT consensus across a multi-vessel formation

Mathematical constants and formulas are taken directly from the
AETHERMOORE constants registry (PHI, R_FIFTH, harmonic scaling H(d, R)).

Dependencies: Python stdlib only (math, hashlib, dataclasses, typing, enum).

Author : SCBE-AETHERMOORE project
Date   : 2026-02-16
"""

from __future__ import annotations

import hashlib
import math
import time as _time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Universal constants (mirrors AETHERMOORE constants.py)
# ---------------------------------------------------------------------------

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0  # Golden ratio
PI: float = math.pi
R_FIFTH: float = 1.5  # 3:2 perfect fifth
EPSILON: float = 1e-12  # Numerical safety


# =========================================================================
# 1. DelayTolerantBundle
# =========================================================================


@dataclass
class CustodyEntry:
    """A single relay hop in the custody chain.

    Attributes:
        relay_id:       Identifier of the relay node.
        signature_hash: SHA-256 hex digest proving the relay handled the bundle.
        order_index:    Monotonically increasing sequence number.
    """

    relay_id: str
    signature_hash: str
    order_index: int


@dataclass
class DelayTolerantBundle:
    """Store-and-forward message bundle for deep-space communication.

    Models the Bundle Protocol (RFC 5050 / RFC 9171) concept where messages
    traverse a chain of relays with custody transfer.  Each relay signs the
    bundle; the receiver can verify the full custody chain.

    SCBE analogy: every governance decision passes through multiple pipeline
    layers (L1-L14), each adding its own cryptographic attestation.

    Attributes:
        payload:       The application-level data (bytes or string).
        sender_id:     Originator node identifier.
        receiver_id:   Destination node identifier.
        custody_chain: Ordered list of relay attestations.
        ttl:           Time-to-live in seconds.
        created_epoch: Unix epoch when the bundle was created.
    """

    payload: bytes
    sender_id: str
    receiver_id: str
    custody_chain: List[CustodyEntry] = field(default_factory=list)
    ttl: float = 3600.0
    created_epoch: float = field(default_factory=_time.time)

    # -- public API --------------------------------------------------------

    def add_custody(self, relay_id: str, signature_hash: str) -> None:
        """Add a relay attestation to the custody chain.

        Args:
            relay_id:       Unique identifier of the forwarding relay.
            signature_hash: Hex-encoded SHA-256 digest proving relay custody.

        Raises:
            ValueError: If *relay_id* is empty or *signature_hash* is not a
                        valid 64-character hex string.
        """
        if not relay_id:
            raise ValueError("relay_id must be non-empty")
        if len(signature_hash) != 64 or not all(
            c in "0123456789abcdef" for c in signature_hash.lower()
        ):
            raise ValueError(
                "signature_hash must be a 64-character lowercase hex SHA-256 digest"
            )
        order = len(self.custody_chain)
        self.custody_chain.append(
            CustodyEntry(
                relay_id=relay_id,
                signature_hash=signature_hash.lower(),
                order_index=order,
            )
        )

    def verify_custody_chain(self) -> bool:
        """Validate that the custody chain is well-formed.

        Checks performed:
          1. Chain is non-empty.
          2. Order indices are strictly sequential starting from 0.
          3. Every signature hash is a valid 64-char hex SHA-256 digest.
          4. No duplicate relay IDs (simple loop detection).

        Returns:
            ``True`` if the chain passes all checks; ``False`` otherwise.
        """
        if not self.custody_chain:
            return False

        seen_relays: set[str] = set()
        for idx, entry in enumerate(self.custody_chain):
            # Sequential ordering
            if entry.order_index != idx:
                return False
            # Valid hex digest
            if len(entry.signature_hash) != 64:
                return False
            if not all(c in "0123456789abcdef" for c in entry.signature_hash):
                return False
            # No loops
            if entry.relay_id in seen_relays:
                return False
            seen_relays.add(entry.relay_id)

        return True

    def compute_bundle_hash(self) -> str:
        """Compute a SHA-256 digest over the entire bundle for integrity.

        Returns:
            Hex-encoded SHA-256 digest.
        """
        h = hashlib.sha256()
        h.update(
            self.payload if isinstance(self.payload, bytes) else self.payload.encode()
        )
        h.update(self.sender_id.encode())
        h.update(self.receiver_id.encode())
        for entry in self.custody_chain:
            h.update(entry.relay_id.encode())
            h.update(entry.signature_hash.encode())
        return h.hexdigest()

    def is_expired(self, now: Optional[float] = None) -> bool:
        """Check whether the bundle's TTL has been exceeded.

        Args:
            now: Current epoch time.  Defaults to ``time.time()``.

        Returns:
            ``True`` if the bundle is expired.
        """
        if now is None:
            now = _time.time()
        return (now - self.created_epoch) > self.ttl


# =========================================================================
# 2. HyperbolicTrajectory
# =========================================================================


def _vec6_distance(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
    """Euclidean distance between two 6D points."""
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


@dataclass
class HyperbolicTrajectory:
    """Orbital path through 6D protocol space on a hyperbolic trajectory.

    In SCBE, the 6D harmonic vector space V6 has dimensions
    (x, y, z, velocity, priority, security).  A *hyperbolic* trajectory
    models how a message or agent moves through this space -- analogous
    to an object with excess energy escaping a gravity well.

    The eccentricity *e > 1* parameterises the openness of the hyperbola.

    SCBE analogy: Layers L5-L7 perform Poincare-ball operations that use
    hyperbolic distance; trajectories through that space represent
    governance state transitions.

    Attributes:
        origin:       Starting 6D coordinate.
        destination:  Target 6D coordinate.
        eccentricity: Eccentricity of the hyperbola (must be > 1).
    """

    origin: Tuple[float, float, float, float, float, float]
    destination: Tuple[float, float, float, float, float, float]
    eccentricity: float

    def __post_init__(self) -> None:
        if len(self.origin) != 6 or len(self.destination) != 6:
            raise ValueError("Origin and destination must be 6-dimensional tuples")
        if self.eccentricity <= 1.0:
            raise ValueError("Eccentricity must be > 1 for a hyperbolic trajectory")

    # -- public API --------------------------------------------------------

    def compute_path(self, steps: int = 100) -> List[Tuple[float, ...]]:
        """Compute waypoints along the hyperbolic trajectory.

        The trajectory is parameterised by the *true anomaly* theta in
        (-theta_max, +theta_max) where theta_max = arccos(-1/e).  The
        radial distance follows the conic equation r(theta) = a(e^2 - 1)
        / (1 + e*cos(theta)), and the 6D waypoint is obtained by
        interpolating between *origin* and *destination* with a radial
        modulation.

        Args:
            steps: Number of waypoints to produce (>= 2).

        Returns:
            List of 6D tuples representing waypoints.
        """
        if steps < 2:
            raise ValueError("steps must be >= 2")

        e = self.eccentricity
        # Use a conservative angular sweep (pi/2 each side of periapsis)
        # to avoid the asymptotic blow-up near theta_asym = arccos(-1/e).
        theta_asym = math.acos(-1.0 / e)
        theta_max = min(theta_asym * 0.5, PI / 2.0)

        # Semi-latus rectum (normalised to unit)
        semi_latus = e * e - 1.0
        # Periapsis distance (minimum r)
        r_periapsis = semi_latus / (1.0 + e)
        # Maximum r along the chosen sweep
        r_at_max = semi_latus / (1.0 + e * math.cos(theta_max))

        waypoints: List[Tuple[float, ...]] = []
        for i in range(steps):
            t = i / (steps - 1)  # 0 .. 1
            theta = -theta_max + 2.0 * theta_max * t
            r = semi_latus / (1.0 + e * math.cos(theta))

            # Normalise r into [0, 1] range for modulation
            r_norm = (r - r_periapsis) / (r_at_max - r_periapsis + EPSILON)

            # Interpolated direction in 6D with bounded hyperbolic modulation
            point = tuple(
                o + (d - o) * t + r_norm * (d - o) * 0.05
                for o, d in zip(self.origin, self.destination)
            )
            waypoints.append(point)

        return waypoints

    def gravity_assist(
        self,
        body_position: Tuple[float, float, float, float, float, float],
        body_mass: float,
    ) -> "HyperbolicTrajectory":
        """Compute a modified trajectory after a gravity assist.

        The assist deflects the destination toward the assisting body,
        weighted by mass.  This is the spaceflight analogue of the
        SCBE *trapdoor function*: easy to compute forward, hard to invert.

        Args:
            body_position: 6D position of the assisting body.
            body_mass:     Scalar mass/influence of the body (> 0).

        Returns:
            A new ``HyperbolicTrajectory`` with a deflected destination.
        """
        if body_mass <= 0:
            raise ValueError("body_mass must be > 0")

        dist = _vec6_distance(self.destination, body_position) + EPSILON
        influence = body_mass / (dist * dist)  # inverse-square

        new_dest = tuple(
            d + influence * (bp - d) for d, bp in zip(self.destination, body_position)
        )
        # Gravity assists tend to reduce eccentricity toward parabolic
        new_e = max(1.001, self.eccentricity - influence * 0.1)

        return HyperbolicTrajectory(
            origin=self.origin,
            destination=new_dest,
            eccentricity=new_e,
        )

    def fuel_cost(self) -> float:
        """Compute fuel cost using the AETHERMOORE harmonic formula.

        H(d, R) = R * pi^(phi * d)

        where *d* is the total Euclidean distance of the trajectory path
        and *R* is the harmonic ratio R_FIFTH (3:2 perfect fifth).

        To avoid floating-point overflow the exponent is clamped to a
        safe maximum (approximately 700 / ln(pi) ~ 611).

        Returns:
            Scalar fuel cost (always finite and positive).
        """
        path = self.compute_path(steps=50)
        total_dist = 0.0
        for i in range(1, len(path)):
            total_dist += _vec6_distance(path[i - 1], path[i])

        exponent = PHI * total_dist
        # Clamp to avoid overflow -- ln(float_max) ~ 709
        max_exp = 700.0 / math.log(PI)
        exponent = min(exponent, max_exp)
        return R_FIFTH * (PI**exponent)

    def path_length(self, steps: int = 50) -> float:
        """Total arc-length of the trajectory in 6D space.

        Args:
            steps: Sampling resolution.

        Returns:
            Scalar arc-length.
        """
        path = self.compute_path(steps=steps)
        total = 0.0
        for i in range(1, len(path)):
            total += _vec6_distance(path[i - 1], path[i])
        return total


# =========================================================================
# 3. DockingProtocol
# =========================================================================


class DockingState(Enum):
    """States of the docking (authentication) handshake."""

    DISCOVERY = auto()
    NEGOTIATION = auto()
    KEY_EXCHANGE = auto()
    VERIFICATION = auto()
    DOCKED = auto()
    FAILED = auto()


# Allowed transitions (state machine edges)
_DOCKING_TRANSITIONS: Dict[DockingState, List[DockingState]] = {
    DockingState.DISCOVERY: [DockingState.NEGOTIATION, DockingState.FAILED],
    DockingState.NEGOTIATION: [DockingState.KEY_EXCHANGE, DockingState.FAILED],
    DockingState.KEY_EXCHANGE: [DockingState.VERIFICATION, DockingState.FAILED],
    DockingState.VERIFICATION: [DockingState.DOCKED, DockingState.FAILED],
    DockingState.DOCKED: [],
    DockingState.FAILED: [],
}


class DockingProtocol:
    """Mutual authentication handshake between two nodes.

    Models the Roundtable Witness Protocol (RWP) handshake as a docking
    manoeuvre between spacecraft.  The protocol walks through the states:

        DISCOVERY -> NEGOTIATION -> KEY_EXCHANGE -> VERIFICATION -> DOCKED

    Any step may transition to FAILED.

    SCBE analogy: RWP multi-signature handshake with Six Sacred Tongues,
    requiring mutual attestation before a governance action is approved.

    Attributes:
        state:         Current handshake state.
        local_id:      Identifier of the local node (set on ``initiate``).
        remote_id:     Identifier of the remote node.
        cipher_suite:  Negotiated cipher suite name (set on ``negotiate``).
        shared_secret: Derived shared secret (set on ``exchange_keys``).
    """

    def __init__(self) -> None:
        self.state: DockingState = DockingState.DISCOVERY
        self.local_id: Optional[str] = None
        self.remote_id: Optional[str] = None
        self.cipher_suite: Optional[str] = None
        self.shared_secret: Optional[bytes] = None
        self._history: List[DockingState] = [DockingState.DISCOVERY]

    # -- helpers -----------------------------------------------------------

    def _transition(self, target: DockingState) -> None:
        allowed = _DOCKING_TRANSITIONS.get(self.state, [])
        if target not in allowed:
            raise RuntimeError(
                f"Invalid transition {self.state.name} -> {target.name}; "
                f"allowed: {[s.name for s in allowed]}"
            )
        self.state = target
        self._history.append(target)

    # -- public API --------------------------------------------------------

    def initiate(self, local_id: str, remote_id: str) -> DockingState:
        """Begin the docking handshake (DISCOVERY -> NEGOTIATION).

        Args:
            local_id:  Identifier for this node.
            remote_id: Identifier for the peer node.

        Returns:
            The new state after initiation (NEGOTIATION or FAILED).

        Raises:
            RuntimeError: If the state machine is not in DISCOVERY.
        """
        if not local_id or not remote_id:
            self._transition(DockingState.FAILED)
            return self.state
        self.local_id = local_id
        self.remote_id = remote_id
        self._transition(DockingState.NEGOTIATION)
        return self.state

    def negotiate_cipher_suite(
        self,
        local_suites: List[str],
        remote_suites: List[str],
    ) -> Optional[str]:
        """Select a common cipher suite (NEGOTIATION -> KEY_EXCHANGE).

        The first suite appearing in both lists (order determined by the
        local preference) is chosen.

        Args:
            local_suites:  Suites supported by the local node (preference order).
            remote_suites: Suites supported by the remote node.

        Returns:
            The chosen cipher suite name, or ``None`` if no common suite
            exists (which also sets the state to FAILED).
        """
        common = [s for s in local_suites if s in remote_suites]
        if not common:
            self._transition(DockingState.FAILED)
            return None
        self.cipher_suite = common[0]
        self._transition(DockingState.KEY_EXCHANGE)
        return self.cipher_suite

    def exchange_keys(
        self,
        local_pubkey: int,
        remote_pubkey: int,
        prime: int = 23,
    ) -> bytes:
        """Compute a shared secret via simplified Diffie-Hellman.

        shared = SHA-256( (remote_pubkey ^ local_secret) mod prime )

        In this simplified model *local_pubkey* is used directly as the
        private exponent (real DH would keep the private key separate).

        Args:
            local_pubkey:  Local public key (integer).
            remote_pubkey: Remote public key (integer).
            prime:         Shared prime modulus.

        Returns:
            32-byte shared secret (SHA-256 digest).
        """
        raw = pow(remote_pubkey, local_pubkey, prime)
        self.shared_secret = hashlib.sha256(str(raw).encode()).digest()
        self._transition(DockingState.VERIFICATION)
        return self.shared_secret

    def verify_and_dock(self, challenge: bytes, response: bytes) -> bool:
        """Final verification step (VERIFICATION -> DOCKED | FAILED).

        The expected response is ``HMAC-SHA256(shared_secret, challenge)``.

        Args:
            challenge: Arbitrary challenge bytes.
            response:  Claimed HMAC response.

        Returns:
            ``True`` if verification succeeds and state moves to DOCKED.
        """
        if self.shared_secret is None:
            self._transition(DockingState.FAILED)
            return False

        import hmac as _hmac

        expected = _hmac.new(self.shared_secret, challenge, hashlib.sha256).digest()
        if _hmac.compare_digest(expected, response):
            self._transition(DockingState.DOCKED)
            return True
        else:
            self._transition(DockingState.FAILED)
            return False

    @property
    def history(self) -> List[str]:
        """Return the sequence of states traversed so far."""
        return [s.name for s in self._history]


# =========================================================================
# 4. ReentryShield
# =========================================================================


class ReentryResult(Enum):
    """Outcome of a boundary crossing attempt."""

    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    CATASTROPHIC_FAILURE = "CATASTROPHIC_FAILURE"


@dataclass
class ReentryShield:
    """Ablative shield that consumes one-time tokens to cross trust boundaries.

    Each trust-zone boundary costs tokens proportional to the *heat flux*
    (computational cost).  If tokens are exhausted mid-crossing, the result
    is CATASTROPHIC_FAILURE -- analogous to a spacecraft burning up on
    re-entry.

    SCBE analogy: Layer 12 *harmonic wall* where risk amplification grows
    super-exponentially.  Crossing from one security domain to another
    consumes single-use cryptographic tokens (nonces), and running out
    mid-operation is an unrecoverable fault.

    Attributes:
        token_count:      Initial (and remaining) number of one-time tokens.
        target_trust_zone: The trust zone this shield is configured for.
    """

    token_count: int
    target_trust_zone: str
    _initial_tokens: int = field(init=False, repr=False)
    _crossing_log: List[Dict[str, Any]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.token_count < 0:
            raise ValueError("token_count must be >= 0")
        self._initial_tokens = self.token_count

    # -- public API --------------------------------------------------------

    def cross_boundary(
        self,
        current_zone: str,
        heat_flux: float,
    ) -> Tuple[ReentryResult, str]:
        """Attempt to cross from *current_zone* into *target_trust_zone*.

        Token cost = ceil(heat_flux).  If insufficient tokens remain when
        the crossing is attempted, the result is CATASTROPHIC_FAILURE.

        Args:
            current_zone: The zone the entity is currently in.
            heat_flux:    Non-negative scalar representing computational
                          cost of the crossing.

        Returns:
            A tuple of (result, zone_after_crossing).
              - On SUCCESS: (SUCCESS, target_trust_zone)
              - On FAIL (same zone): (FAIL, current_zone)
              - On CATASTROPHIC_FAILURE: (CATASTROPHIC_FAILURE, "DESTROYED")
        """
        if heat_flux < 0:
            raise ValueError("heat_flux must be >= 0")

        cost = math.ceil(heat_flux)

        if cost == 0:
            # Zero-cost crossing always succeeds (same-zone passthrough)
            self._crossing_log.append(
                {
                    "from": current_zone,
                    "to": self.target_trust_zone,
                    "cost": 0,
                    "result": ReentryResult.SUCCESS.value,
                }
            )
            return (ReentryResult.SUCCESS, self.target_trust_zone)

        if self.token_count <= 0:
            # Already out of tokens -- immediate failure
            self._crossing_log.append(
                {
                    "from": current_zone,
                    "to": "DESTROYED",
                    "cost": cost,
                    "result": ReentryResult.CATASTROPHIC_FAILURE.value,
                }
            )
            return (ReentryResult.CATASTROPHIC_FAILURE, "DESTROYED")

        if cost > self.token_count:
            # Tokens exhausted mid-crossing -- catastrophic
            self.token_count = 0
            self._crossing_log.append(
                {
                    "from": current_zone,
                    "to": "DESTROYED",
                    "cost": cost,
                    "result": ReentryResult.CATASTROPHIC_FAILURE.value,
                }
            )
            return (ReentryResult.CATASTROPHIC_FAILURE, "DESTROYED")

        # Successful crossing
        self.token_count -= cost
        self._crossing_log.append(
            {
                "from": current_zone,
                "to": self.target_trust_zone,
                "cost": cost,
                "result": ReentryResult.SUCCESS.value,
            }
        )
        return (ReentryResult.SUCCESS, self.target_trust_zone)

    def remaining_tokens(self) -> int:
        """Return the number of tokens still available."""
        return self.token_count

    @property
    def crossing_log(self) -> List[Dict[str, Any]]:
        """Return a copy of the crossing audit log."""
        return list(self._crossing_log)


# =========================================================================
# 5. StarTracker
# =========================================================================


def _vec6_sq_distance(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
    """Squared Euclidean distance in 6D (avoids sqrt for comparisons)."""
    return sum((ai - bi) ** 2 for ai, bi in zip(a, b))


@dataclass
class StarMatch:
    """A matched observation-to-catalog entry."""

    star_id: str
    catalog_position: Tuple[float, ...]
    observed_position: Tuple[float, ...]
    distance: float


class StarTracker:
    """Certificate authority verification via a star catalog.

    Given a catalog of known star positions in 6D space, the tracker can:
      - match observed positions to catalog entries (nearest-neighbour);
      - compute an attitude quaternion from matched pairs;
      - verify a claimed position against the star-derived attitude.

    SCBE analogy: The star catalog is a trusted root certificate store.
    Observed positions are presented credentials.  Matching and attitude
    computation correspond to certificate chain validation and key
    verification.

    Attributes:
        catalog: Mapping of star_id to known 6D position.
    """

    def __init__(
        self,
        catalog: Dict[str, Tuple[float, float, float, float, float, float]],
    ) -> None:
        if not catalog:
            raise ValueError("Catalog must contain at least one entry")
        self.catalog = dict(catalog)

    # -- public API --------------------------------------------------------

    def identify_stars(
        self,
        observed_positions: List[Tuple[float, float, float, float, float, float]],
    ) -> List[StarMatch]:
        """Match observed positions to catalog entries (nearest-neighbour).

        Each observed position is matched to the closest catalog star.
        Duplicate matches are allowed (two observations may map to the
        same catalog star).

        Args:
            observed_positions: List of 6D observed positions.

        Returns:
            List of ``StarMatch`` objects, one per observation.
        """
        matches: List[StarMatch] = []
        for obs in observed_positions:
            best_id: Optional[str] = None
            best_dist_sq: float = math.inf
            for sid, cpos in self.catalog.items():
                dsq = _vec6_sq_distance(obs, cpos)
                if dsq < best_dist_sq:
                    best_dist_sq = dsq
                    best_id = sid
            assert best_id is not None
            matches.append(
                StarMatch(
                    star_id=best_id,
                    catalog_position=self.catalog[best_id],
                    observed_position=obs,
                    distance=math.sqrt(best_dist_sq),
                )
            )
        return matches

    def compute_attitude(
        self,
        matches: List[StarMatch],
    ) -> Tuple[float, float, float, float]:
        """Compute a quaternion representing attitude from star matches.

        A simplified Wahba-problem solver: the quaternion encodes the
        rotation that best aligns observed positions with catalog
        positions.  Here we compute the mean residual vector and convert
        it to a unit quaternion (scalar-last convention: x, y, z, w).

        Args:
            matches: List of ``StarMatch`` objects (need >= 1).

        Returns:
            Unit quaternion (x, y, z, w) with ||q|| = 1.

        Raises:
            ValueError: If *matches* is empty.
        """
        if not matches:
            raise ValueError("Need at least one match to compute attitude")

        # Accumulate residual across the first 3 spatial dimensions
        rx, ry, rz = 0.0, 0.0, 0.0
        for m in matches:
            rx += m.observed_position[0] - m.catalog_position[0]
            ry += m.observed_position[1] - m.catalog_position[1]
            rz += m.observed_position[2] - m.catalog_position[2]
        n = len(matches)
        rx /= n
        ry /= n
        rz /= n

        # Convert residual to a small-angle quaternion (Rodrigues approx)
        half_angle = math.sqrt(rx * rx + ry * ry + rz * rz) / 2.0
        if half_angle < EPSILON:
            return (0.0, 0.0, 0.0, 1.0)  # identity

        s = math.sin(half_angle) / (2.0 * half_angle)
        w = math.cos(half_angle)
        qx, qy, qz = rx * s, ry * s, rz * s

        # Normalise
        norm = math.sqrt(qx * qx + qy * qy + qz * qz + w * w)
        return (qx / norm, qy / norm, qz / norm, w / norm)

    def verify_position(
        self,
        claimed_position: Tuple[float, float, float, float, float, float],
        tolerance: float,
        observed_positions: Optional[
            List[Tuple[float, float, float, float, float, float]]
        ] = None,
    ) -> bool:
        """Verify a claimed position against star-derived observations.

        If *observed_positions* is provided, match them to the catalog
        and compute the mean observed centroid.  The claim is accepted
        if the distance between the centroid and the claimed position is
        within *tolerance*.

        If no observations are provided, fall back to checking whether
        the claimed position is within *tolerance* of any catalog entry.

        Args:
            claimed_position:   6D position the node claims to occupy.
            tolerance:          Maximum allowable distance.
            observed_positions: Optional recent observations.

        Returns:
            ``True`` if the position is verified.
        """
        if tolerance < 0:
            raise ValueError("tolerance must be >= 0")

        if observed_positions:
            matches = self.identify_stars(observed_positions)
            # Compute mean observed centroid
            dims = len(claimed_position)
            centroid = tuple(
                sum(m.observed_position[d] for m in matches) / len(matches)
                for d in range(dims)
            )
            return _vec6_distance(claimed_position, centroid) <= tolerance

        # Fallback: check against catalog directly
        for cpos in self.catalog.values():
            if _vec6_distance(claimed_position, cpos) <= tolerance:
                return True
        return False


# =========================================================================
# 6. ConstellationFleet
# =========================================================================

VALID_FORMATIONS = frozenset(
    {
        "PHALANX",
        "LANCE",
        "WEB",
        "STORM",
        "CONSTELLATION",
    }
)


class ConstellationFleet:
    """Multi-vessel formation with distributed BFT consensus.

    The fleet is split into two *squads* of equal size.  Formation
    changes require a supermajority (>= 2/3 of total vessels) to agree
    via a Byzantine Fault Tolerant vote.

    SCBE analogy: the BFT consensus engine in ``ai_brain/bft-consensus.ts``
    and the fleet manager in ``fleet/fleet-manager.ts``.  The two squads
    mirror the *dual lattice* consensus (primal + dual must agree).

    Attributes:
        fleet_size: Total number of vessels (must be even).
        squad_size: Vessels per squad (fleet_size // 2).
    """

    def __init__(
        self,
        fleet_size: int = 12,
        squad_size: int = 6,
    ) -> None:
        if fleet_size < 2:
            raise ValueError("fleet_size must be >= 2")
        if squad_size < 1:
            raise ValueError("squad_size must be >= 1")
        if squad_size * 2 != fleet_size:
            raise ValueError("fleet_size must be exactly 2 * squad_size")

        self.fleet_size: int = fleet_size
        self.squad_size: int = squad_size

        # Vessel identifiers: "V-00" .. "V-{fleet_size-1}"
        self._vessels: List[str] = [f"V-{i:02d}" for i in range(fleet_size)]
        self._squad_a: List[str] = self._vessels[:squad_size]
        self._squad_b: List[str] = self._vessels[squad_size:]

        self._current_formation: Optional[str] = None

        # Voting state
        self._proposal: Optional[str] = None
        self._votes: Dict[str, bool] = {}

    # -- public API --------------------------------------------------------

    @property
    def current_formation(self) -> Optional[str]:
        """The fleet's current formation, or ``None`` if none has been set."""
        return self._current_formation

    @property
    def vessels(self) -> List[str]:
        """List of all vessel identifiers."""
        return list(self._vessels)

    @property
    def squad_a(self) -> List[str]:
        """Vessels in squad A (first half)."""
        return list(self._squad_a)

    @property
    def squad_b(self) -> List[str]:
        """Vessels in squad B (second half)."""
        return list(self._squad_b)

    def propose_formation(self, formation_type: str) -> str:
        """Initiate a BFT vote on a new formation.

        Clears any in-progress vote and starts a fresh ballot.

        Args:
            formation_type: One of the valid formations
                (PHALANX, LANCE, WEB, STORM, CONSTELLATION).

        Returns:
            The proposed formation name.

        Raises:
            ValueError: If *formation_type* is not recognised.
        """
        if formation_type not in VALID_FORMATIONS:
            raise ValueError(
                f"Unknown formation '{formation_type}'; "
                f"must be one of {sorted(VALID_FORMATIONS)}"
            )
        self._proposal = formation_type
        self._votes = {}
        return formation_type

    def vote(self, vessel_id: str, approve: bool) -> None:
        """Register a vessel's vote on the current proposal.

        Args:
            vessel_id: Identifier of the voting vessel.
            approve:   ``True`` to approve, ``False`` to reject.

        Raises:
            ValueError: If there is no active proposal or the vessel is
                        not part of the fleet.
        """
        if self._proposal is None:
            raise ValueError("No active proposal to vote on")
        if vessel_id not in self._vessels:
            raise ValueError(f"Unknown vessel '{vessel_id}'")
        self._votes[vessel_id] = approve

    def check_consensus(self) -> Optional[str]:
        """Check whether the BFT supermajority threshold is met.

        Consensus requires at least ceil(2/3 * fleet_size) approvals.

        Returns:
            The agreed formation name if consensus is reached, or
            ``None`` if not enough approvals exist yet.
        """
        if self._proposal is None:
            return None
        threshold = math.ceil(2.0 * self.fleet_size / 3.0)
        approvals = sum(1 for v in self._votes.values() if v)
        if approvals >= threshold:
            return self._proposal
        return None

    def shift_formation(self, new_formation: str) -> bool:
        """Atomically change formation if consensus has been reached.

        If the consensus check passes for *new_formation*, the fleet's
        current formation is updated and the vote is cleared.

        Args:
            new_formation: Formation to shift to (must match active proposal).

        Returns:
            ``True`` if the formation was changed; ``False`` otherwise.
        """
        if self._proposal is None or self._proposal != new_formation:
            return False
        agreed = self.check_consensus()
        if agreed is None:
            return False
        self._current_formation = agreed
        # Clear the ballot
        self._proposal = None
        self._votes = {}
        return True

    def vote_count(self) -> Dict[str, int]:
        """Return current vote tallies.

        Returns:
            Dict with keys ``"approve"`` and ``"reject"``.
        """
        approve = sum(1 for v in self._votes.values() if v)
        reject = sum(1 for v in self._votes.values() if not v)
        return {"approve": approve, "reject": reject}
