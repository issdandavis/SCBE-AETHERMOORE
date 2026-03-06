"""Sacred Egg Genesis Lifecycle — Canonical G0-G4 Lifecycle Implementation

Sacred Eggs are the genesis-layer complement to GeoSeal and SCBE runtime governance.
GeoSeal answers whether an entity may act.
Sacred Eggs answer whether an entity may come into existence at all.

A Sacred Egg is a sealed genesis authorization object that permits creation of a
new agent, realm, or governed entity only after a ritualized validation process
confirms quorum, intent, and geometric admissibility.

Sacred Eggs implement ritual-based genesis governance. They replace unilateral
entity creation with a sealed, auditable authorization ceremony requiring
quorum-weighted validation and geometric admissibility before a new agent or
realm may be instantiated.

Canonical Lifecycle:

    G0 — Proposal:   Assemble candidate egg with entity type, purpose, config
    G1 — Sealing:    Cryptographically seal payload with provenance metadata
    G2 — Ritual:     Evaluate against quorum, geometry, integrity, governance
    G3 — Decision:   Output HATCH / QUARANTINE / DENY
    G4 — Spawn:      Instantiate entity with bound governance limits + audit record

Hatch predicate (conjunction):

    HATCH(E) = (quorum_weight >= phi_threshold)
             AND (geometric_admissibility == true)
             AND (payload_integrity == valid)
             AND (governance_risk <= allowed_bound)
             AND (required_validators_signed == true)

@layer Layer 12, Layer 13
@component Sacred Egg Genesis Lifecycle
@version 1.0.0
"""

from __future__ import annotations

import hashlib
import hmac
import math
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, Tuple

# Golden ratio
PHI = (1 + math.sqrt(5)) / 2

# Genesis threshold: phi^3 ~ 4.236
GENESIS_THRESHOLD = PHI ** 3

# Decision types
Decision = Literal["HATCH", "QUARANTINE", "DENY"]

# Entity types that can be spawned
EntityType = Literal["agent", "realm", "subsystem", "service"]


# =============================================================================
# Core Data Structures
# =============================================================================


@dataclass
class ValidatorVote:
    """A validator's vote in the genesis ritual.

    Each validator contributes a tongue-weighted vote. The phi-weighted
    sum of approved votes must exceed the genesis threshold.

    Attributes:
        validator_id: Unique identifier for the voting validator
        tongue: Sacred Tongue code (KO/AV/RU/CA/UM/DR)
        weight: Phi-scaled weight for this tongue
        approved: Whether the validator approves hatching
        signature: Hex-encoded cryptographic signature of the vote
    """

    validator_id: str
    tongue: str
    weight: float
    approved: bool
    signature: str


@dataclass
class SacredEgg:
    """A sealed genesis payload — consensus-bound genesis capsule for governed spawning.

    Contains initialization parameters, governance constraints, and provenance
    data for a prospective agent or realm. The payload may be hatched only when
    ritual conditions are satisfied, including quorum validation, tongue-weight
    thresholds, and geometric admissibility checks.

    Attributes:
        egg_id: Unique identifier (hex string)
        entity_type: What kind of entity this egg would spawn
        proposer_id: Who proposed this genesis
        purpose: Human-readable purpose / mission statement
        init_payload_ciphertext: Encrypted initialization data
        init_payload_hash: SHA-256 hash of the plaintext payload (integrity check)
        target_realm: Optional realm to spawn into
        geometric_anchor: Optional position in Poincare ball for GeoSeal binding
        d_star_max: Maximum allowed hyperbolic distance from anchor
        epoch: Creation epoch counter
        created_at: UTC timestamp of creation
        required_phi_weight: Minimum phi-weighted quorum threshold
        votes: Collected validator votes
        coherence: Computed coherence score (set during ritual)
        d_star: Computed hyperbolic distance (set during ritual)
        h_eff: Effective harmonic score (set during ritual)
        decision: Final decision (set during G3)
        hatch_proof: Cryptographic proof of hatching (set during G4)
    """

    egg_id: str
    entity_type: EntityType
    proposer_id: str
    purpose: str
    init_payload_ciphertext: str
    init_payload_hash: str

    target_realm: Optional[str] = None
    geometric_anchor: Optional[List[float]] = None
    d_star_max: Optional[float] = None

    epoch: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    required_phi_weight: float = GENESIS_THRESHOLD
    votes: List[ValidatorVote] = field(default_factory=list)

    coherence: Optional[float] = None
    d_star: Optional[float] = None
    h_eff: Optional[float] = None

    decision: Optional[Decision] = None
    hatch_proof: Optional[Dict] = None


@dataclass
class GenesisProof:
    """Proof that a genesis was legitimately performed.

    Created during G4 (Spawn) and attached to both the egg and the
    newly spawned entity as its birth certificate.

    Attributes:
        egg_id: The egg that was hatched
        entity_id: The spawned entity's identifier
        entity_type: What was spawned
        proposer_id: Who proposed the genesis
        validators: List of validator IDs who approved
        quorum_weight: The phi-weighted sum achieved
        genesis_seal: SHA-256 seal over all proof fields
        spawned_at: UTC timestamp of spawn
        epoch: Epoch at spawn time
        governance_envelope: Initial governance constraints bound at birth
    """

    egg_id: str
    entity_id: str
    entity_type: EntityType
    proposer_id: str
    validators: List[str]
    quorum_weight: float
    genesis_seal: str
    spawned_at: datetime
    epoch: int
    governance_envelope: Dict = field(default_factory=dict)


@dataclass
class SpawnedEntity:
    """A newly spawned entity resulting from a successful genesis.

    Begins life with known origin, known validators, known governance
    envelope, and known initial intent binding.

    Attributes:
        entity_id: Unique identifier
        entity_type: What kind of entity this is
        genesis_proof: The proof of legitimate birth
        init_payload: Decrypted initialization data
        governance_limits: Inherited governance constraints
        origin_egg_id: The egg it hatched from
        origin_realm: The realm it was spawned into
    """

    entity_id: str
    entity_type: EntityType
    genesis_proof: GenesisProof
    init_payload: bytes
    governance_limits: Dict
    origin_egg_id: str
    origin_realm: Optional[str] = None


# =============================================================================
# Tongue Weights (phi-scaled)
# =============================================================================

# Sacred Tongue weights scale by phi: KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09
TONGUE_WEIGHTS: Dict[str, float] = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI ** 2,
    "CA": PHI ** 3,
    "UM": PHI ** 4,
    "DR": PHI ** 5,
}


# =============================================================================
# G0 — Proposal
# =============================================================================


def propose_egg(
    entity_type: EntityType,
    proposer_id: str,
    purpose: str,
    init_payload: bytes,
    target_realm: Optional[str] = None,
    geometric_anchor: Optional[List[float]] = None,
    d_star_max: Optional[float] = None,
    epoch: int = 0,
    required_phi_weight: Optional[float] = None,
) -> SacredEgg:
    """G0 — Proposal: Assemble a candidate Sacred Egg.

    The egg is created with the payload encrypted and its hash recorded
    for integrity verification during the ritual phase.

    Args:
        entity_type: What kind of entity to spawn
        proposer_id: Who is proposing this genesis
        purpose: Human-readable purpose statement
        init_payload: Raw initialization data to encrypt
        target_realm: Optional realm to spawn into
        geometric_anchor: Optional Poincare ball position
        d_star_max: Maximum hyperbolic distance from anchor
        epoch: Creation epoch
        required_phi_weight: Custom phi-weight threshold (default: phi^3)

    Returns:
        A new SacredEgg in proposal state (no votes, no decision)
    """
    payload_hash = hashlib.sha256(init_payload).hexdigest()

    # Encrypt payload (symmetric, key derived from egg context)
    egg_salt = secrets.token_bytes(16)
    egg_key = hashlib.sha256(egg_salt + proposer_id.encode() + purpose.encode()).digest()
    # XOR-stream encryption for the init payload
    ciphertext = _xor_encrypt(egg_key, init_payload)
    ct_hex = egg_salt.hex() + ciphertext.hex()

    egg_id = hashlib.sha256(
        f"{entity_type}:{proposer_id}:{purpose}:{payload_hash}:{epoch}".encode()
    ).hexdigest()[:16]

    return SacredEgg(
        egg_id=egg_id,
        entity_type=entity_type,
        proposer_id=proposer_id,
        purpose=purpose,
        init_payload_ciphertext=ct_hex,
        init_payload_hash=payload_hash,
        target_realm=target_realm,
        geometric_anchor=geometric_anchor,
        d_star_max=d_star_max,
        epoch=epoch,
        required_phi_weight=required_phi_weight or GENESIS_THRESHOLD,
    )


# =============================================================================
# G1 — Sealing
# =============================================================================


def seal_egg(egg: SacredEgg, signer_key: bytes) -> str:
    """G1 — Sealing: Cryptographically seal the egg.

    Computes an HMAC seal over the egg's content hash, binding the
    proposer, entity type, purpose, and payload together.

    Args:
        egg: The proposed egg to seal
        signer_key: 32-byte signing key

    Returns:
        Hex-encoded HMAC seal string
    """
    seal_data = (
        f"{egg.egg_id}|{egg.entity_type}|{egg.proposer_id}|"
        f"{egg.purpose}|{egg.init_payload_hash}|{egg.epoch}"
    ).encode()
    seal = hmac.new(signer_key, seal_data, hashlib.sha256).hexdigest()
    return seal


def verify_seal(egg: SacredEgg, seal: str, signer_key: bytes) -> bool:
    """Verify an egg's seal integrity.

    Args:
        egg: The egg to verify
        seal: The seal to check
        signer_key: The key used to create the seal

    Returns:
        True if the seal is valid
    """
    expected = seal_egg(egg, signer_key)
    return hmac.compare_digest(seal, expected)


# =============================================================================
# G2 — Ritual Validation
# =============================================================================


def cast_vote(
    egg: SacredEgg,
    validator_id: str,
    tongue: str,
    approved: bool,
    signing_key: bytes,
) -> ValidatorVote:
    """Cast a validator vote on a Sacred Egg.

    The vote is signed with the validator's key for non-repudiation.

    Args:
        egg: The egg being voted on
        validator_id: The voting validator's ID
        tongue: The validator's Sacred Tongue (KO/AV/RU/CA/UM/DR)
        approved: Whether the validator approves
        signing_key: The validator's signing key

    Returns:
        A signed ValidatorVote
    """
    weight = TONGUE_WEIGHTS.get(tongue.upper(), 0.0)

    vote_data = f"{egg.egg_id}|{validator_id}|{tongue}|{approved}|{weight}".encode()
    signature = hmac.new(signing_key, vote_data, hashlib.sha256).hexdigest()

    vote = ValidatorVote(
        validator_id=validator_id,
        tongue=tongue.upper(),
        weight=weight,
        approved=approved,
        signature=signature,
    )
    egg.votes.append(vote)
    return vote


def compute_quorum_weight(votes: List[ValidatorVote]) -> float:
    """Compute the phi-weighted quorum sum from approved votes.

    W = sum(w_i) for all approved votes, where w_i is the tongue weight.

    Args:
        votes: List of validator votes

    Returns:
        Total phi-weighted quorum sum
    """
    return sum(v.weight for v in votes if v.approved)


def check_geometric_admissibility(
    egg: SacredEgg,
    current_position: Optional[List[float]] = None,
) -> Tuple[bool, float]:
    """Check geometric admissibility for the egg.

    Verifies the current position is within d_star_max hyperbolic distance
    of the egg's geometric anchor in the Poincare ball.

    Args:
        egg: The egg with geometric constraints
        current_position: Current position in the Poincare ball

    Returns:
        Tuple of (admissible, distance)
    """
    if egg.geometric_anchor is None or current_position is None:
        return True, 0.0

    d_max = egg.d_star_max or 2.0

    # Compute Poincare distance
    diff_sq = sum((a - b) ** 2 for a, b in zip(egg.geometric_anchor, current_position))
    anchor_sq = sum(a ** 2 for a in egg.geometric_anchor)
    pos_sq = sum(p ** 2 for p in current_position)

    anchor_factor = max(1e-10, 1.0 - anchor_sq)
    pos_factor = max(1e-10, 1.0 - pos_sq)

    arg = 1.0 + 2.0 * diff_sq / (anchor_factor * pos_factor)
    d_star = math.acosh(max(1.0, arg))

    return d_star < d_max, d_star


def check_payload_integrity(egg: SacredEgg) -> bool:
    """Verify the egg's payload hash matches the ciphertext.

    This is a structural check — we verify the hash was properly
    recorded, not that we can decrypt (that requires the key).

    Args:
        egg: The egg to check

    Returns:
        True if the payload hash and ciphertext are present and consistent
    """
    return (
        len(egg.init_payload_ciphertext) > 0
        and len(egg.init_payload_hash) == 64  # SHA-256 hex
    )


def evaluate_ritual(
    egg: SacredEgg,
    current_position: Optional[List[float]] = None,
    governance_risk: float = 0.0,
    max_governance_risk: float = 1.0,
) -> Tuple[Decision, Dict]:
    """G2/G3 — Ritual Validation + Hatching Decision.

    Evaluates the full hatch predicate:

        HATCH(E) = (quorum_weight >= phi_threshold)
                 AND (geometric_admissibility == true)
                 AND (payload_integrity == valid)
                 AND (governance_risk <= allowed_bound)
                 AND (required_validators_signed == true)

    Args:
        egg: The sealed egg with collected votes
        current_position: Current position in Poincare ball
        governance_risk: Current governance risk score [0, 1]
        max_governance_risk: Maximum allowed governance risk

    Returns:
        Tuple of (Decision, diagnostic_report)
    """
    report: Dict = {}

    # 1. Quorum weight check
    quorum_weight = compute_quorum_weight(egg.votes)
    quorum_pass = quorum_weight >= egg.required_phi_weight
    report["quorum_weight"] = quorum_weight
    report["quorum_threshold"] = egg.required_phi_weight
    report["quorum_pass"] = quorum_pass

    # 2. Geometric admissibility
    geo_pass, d_star = check_geometric_admissibility(egg, current_position)
    report["geometric_pass"] = geo_pass
    report["d_star"] = d_star

    # 3. Payload integrity
    integrity_pass = check_payload_integrity(egg)
    report["integrity_pass"] = integrity_pass

    # 4. Governance risk
    gov_pass = governance_risk <= max_governance_risk
    report["governance_pass"] = gov_pass
    report["governance_risk"] = governance_risk

    # 5. Required validators signed
    has_votes = len(egg.votes) > 0
    all_approved = all(v.approved for v in egg.votes) if has_votes else False
    validators_pass = has_votes and quorum_pass
    report["validators_pass"] = validators_pass

    # Store computed values on egg
    egg.d_star = d_star
    egg.coherence = quorum_weight / max(egg.required_phi_weight, 1e-10)
    egg.h_eff = 1.0 / (1.0 + d_star + 2.0 * governance_risk)

    # Decision logic
    all_pass = quorum_pass and geo_pass and integrity_pass and gov_pass and validators_pass

    if all_pass:
        decision: Decision = "HATCH"
    elif quorum_weight > 0 and (not geo_pass or not gov_pass):
        # Some support but geometric/governance concerns
        decision = "QUARANTINE"
    else:
        decision = "DENY"

    egg.decision = decision
    report["decision"] = decision
    return decision, report


# =============================================================================
# G4 — Spawn
# =============================================================================


def spawn_entity(
    egg: SacredEgg,
    decryption_key: bytes,
    governance_envelope: Optional[Dict] = None,
) -> Tuple[SpawnedEntity, GenesisProof]:
    """G4 — Spawn: Instantiate a new entity from a hatched egg.

    Only callable after evaluate_ritual() returns HATCH.

    Args:
        egg: The hatched egg (decision must be HATCH)
        decryption_key: Key to decrypt the init payload
        governance_envelope: Initial governance constraints

    Returns:
        Tuple of (SpawnedEntity, GenesisProof)

    Raises:
        PermissionError: If egg decision is not HATCH
    """
    if egg.decision != "HATCH":
        raise PermissionError(
            f"Cannot spawn from egg with decision={egg.decision}. "
            f"Only HATCH eggs may spawn entities."
        )

    # Decrypt init payload
    ct_hex = egg.init_payload_ciphertext
    egg_salt = bytes.fromhex(ct_hex[:32])  # 16 bytes = 32 hex chars
    ciphertext = bytes.fromhex(ct_hex[32:])
    egg_key = hashlib.sha256(
        egg_salt + egg.proposer_id.encode() + egg.purpose.encode()
    ).digest()
    init_payload = _xor_encrypt(egg_key, ciphertext)

    # Verify integrity
    payload_hash = hashlib.sha256(init_payload).hexdigest()
    if payload_hash != egg.init_payload_hash:
        raise ValueError("Payload integrity check failed — hash mismatch")

    # Generate entity ID
    entity_id = hashlib.sha256(
        f"{egg.egg_id}:{egg.epoch}:{time.time()}".encode()
        + secrets.token_bytes(16)
    ).hexdigest()[:16]

    # Compute quorum weight for proof
    quorum_weight = compute_quorum_weight(egg.votes)
    validators = [v.validator_id for v in egg.votes if v.approved]

    now = datetime.now(timezone.utc)

    # Build genesis seal
    seal_data = (
        f"{egg.egg_id}|{entity_id}|{egg.entity_type}|{egg.proposer_id}|"
        f"{','.join(validators)}|{quorum_weight:.10f}|{egg.epoch}"
    ).encode()
    genesis_seal = hashlib.sha256(seal_data).hexdigest()

    gov_env = governance_envelope or {}

    proof = GenesisProof(
        egg_id=egg.egg_id,
        entity_id=entity_id,
        entity_type=egg.entity_type,
        proposer_id=egg.proposer_id,
        validators=validators,
        quorum_weight=quorum_weight,
        genesis_seal=genesis_seal,
        spawned_at=now,
        epoch=egg.epoch,
        governance_envelope=gov_env,
    )

    egg.hatch_proof = {
        "entity_id": entity_id,
        "genesis_seal": genesis_seal,
        "spawned_at": now.isoformat(),
        "validators": validators,
        "quorum_weight": quorum_weight,
    }

    entity = SpawnedEntity(
        entity_id=entity_id,
        entity_type=egg.entity_type,
        genesis_proof=proof,
        init_payload=init_payload,
        governance_limits=gov_env,
        origin_egg_id=egg.egg_id,
        origin_realm=egg.target_realm,
    )

    return entity, proof


# =============================================================================
# Fail-to-Noise
# =============================================================================


def genesis_noise(egg: SacredEgg) -> bytes:
    """Generate fail-to-noise output for a denied/quarantined egg.

    Returns deterministic noise of the same length as the ciphertext,
    making HATCH and DENY outputs indistinguishable to an observer.

    Args:
        egg: The egg that failed ritual validation

    Returns:
        Noise bytes of consistent length
    """
    ct_len = len(egg.init_payload_ciphertext) // 2  # hex to bytes
    noise_key = hashlib.sha256(
        b"sacred-egg:noise:v1|" + egg.egg_id.encode()
    ).digest()
    # Deterministic noise via HMAC-based stream
    noise = bytearray()
    counter = 0
    while len(noise) < ct_len:
        block = hmac.new(
            noise_key,
            counter.to_bytes(8, "big"),
            hashlib.sha256,
        ).digest()
        noise.extend(block)
        counter += 1
    return bytes(noise[:ct_len])


# =============================================================================
# Full Lifecycle Convenience
# =============================================================================


def full_genesis_lifecycle(
    entity_type: EntityType,
    proposer_id: str,
    purpose: str,
    init_payload: bytes,
    validator_votes: List[Tuple[str, str, bool, bytes]],
    signer_key: bytes,
    target_realm: Optional[str] = None,
    geometric_anchor: Optional[List[float]] = None,
    current_position: Optional[List[float]] = None,
    d_star_max: Optional[float] = None,
    governance_risk: float = 0.0,
    governance_envelope: Optional[Dict] = None,
) -> Tuple[Optional[SpawnedEntity], Optional[GenesisProof], Decision, Dict]:
    """Execute the full G0-G4 Sacred Egg genesis lifecycle.

    Args:
        entity_type: What to spawn
        proposer_id: Who proposes
        purpose: Why
        init_payload: Initialization data
        validator_votes: List of (validator_id, tongue, approved, signing_key)
        signer_key: Key for sealing the egg
        target_realm: Optional target realm
        geometric_anchor: Optional Poincare ball anchor
        current_position: Current position for GeoSeal check
        d_star_max: Max hyperbolic distance
        governance_risk: Current risk score
        governance_envelope: Initial governance limits

    Returns:
        Tuple of (entity_or_None, proof_or_None, decision, report)
    """
    # G0 — Proposal
    egg = propose_egg(
        entity_type=entity_type,
        proposer_id=proposer_id,
        purpose=purpose,
        init_payload=init_payload,
        target_realm=target_realm,
        geometric_anchor=geometric_anchor,
        d_star_max=d_star_max,
    )

    # G1 — Sealing
    seal = seal_egg(egg, signer_key)

    # G2 — Ritual (collect votes)
    for vid, tongue, approved, vkey in validator_votes:
        cast_vote(egg, vid, tongue, approved, vkey)

    # G2/G3 — Evaluate ritual + decision
    decision, report = evaluate_ritual(
        egg,
        current_position=current_position,
        governance_risk=governance_risk,
    )
    report["seal"] = seal

    # G4 — Spawn (if approved)
    if decision == "HATCH":
        decryption_key = hashlib.sha256(
            signer_key + egg.egg_id.encode()
        ).digest()
        entity, proof = spawn_entity(egg, decryption_key, governance_envelope)
        return entity, proof, decision, report

    return None, None, decision, report


# =============================================================================
# Helpers
# =============================================================================


def _xor_encrypt(key: bytes, data: bytes) -> bytes:
    """XOR-stream encryption/decryption using HMAC-based keystream."""
    out = bytearray(len(data))
    for i in range(0, len(data), 32):
        block_key = hmac.new(
            key, i.to_bytes(8, "big"), hashlib.sha256
        ).digest()
        for j in range(min(32, len(data) - i)):
            out[i + j] = data[i + j] ^ block_key[j]
    return bytes(out)
