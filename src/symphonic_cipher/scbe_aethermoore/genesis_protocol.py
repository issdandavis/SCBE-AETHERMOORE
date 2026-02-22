"""Genesis Protocol — AI Identity Cube + Hatchling Birth Ceremony

Every AI hatchling is born with a unique Identity Cube — a geometric
fingerprint derived from:
  1. A Sacred Egg (GeoSeal-encrypted initialization payload)
  2. A batch offset vector (sacred geometry, non-duplicable)
  3. A tongue affinity (primary Sacred Tongue)
  4. A context seed (6D position in the Poincare ball)

The Identity Cube ensures:
  - No two AIs have the same geometric identity
  - Malicious clones can't copy a valid cube (needs the egg + batch offset)
  - Internal consistency across a batch (offsets form a pattern)
  - Each AI can be verified by its cube hash

Lifecycle:
  GenesisField (intent) → Sacred Egg hatch → Identity Cube mint → Hatchling

@layer Layer 12, Layer 13
@component Genesis Protocol
@version 1.0.0
@patent USPTO #63/961,403
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import time
from typing import Dict, List, Optional, Tuple

from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (
    TONGUES,
    CrossTokenizer,
    TongueTokenizer,
    Lexicons,
    project_to_sphere,
    project_to_cube,
    healpix_id,
    morton_id,
)
from src.symphonic_cipher.scbe_aethermoore.sacred_egg_integrator import (
    SacredEgg,
    SacredEggIntegrator,
    HatchResult,
    context_radius,
)

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio


# =============================================================================
# Identity Cube
# =============================================================================


@dataclasses.dataclass(frozen=True)
class IdentityCube:
    """Unique geometric identity for an AI hatchling.

    The cube is a 6D vector derived from the egg + batch offset + context.
    No two cubes are identical. The cube_hash is the public identifier.

    Attributes:
        cube_id:        SHA-256 hash of the full cube (first 16 hex chars)
        tongue_affinity: Primary Sacred Tongue this AI "speaks"
        cube_vector:    6D identity vector (the geometric fingerprint)
        batch_id:       Which batch this AI belongs to
        batch_index:    Position within the batch
        healpix_cell:   S2 cell on the Poincare ball boundary
        morton_cell:    Cube-projected lattice cell
        egg_id:         The Sacred Egg this AI hatched from
        born_at:        Unix timestamp of birth
    """
    cube_id: str
    tongue_affinity: str
    cube_vector: Tuple[float, ...]
    batch_id: str
    batch_index: int
    healpix_cell: int
    morton_cell: int
    egg_id: str
    born_at: float


@dataclasses.dataclass
class GenesisField:
    """Pre-birth intent field. Multiple agents declare intent to spawn.

    The coherence_score measures how aligned the intents are.
    Must reach threshold before crystallization can proceed.
    """
    intent_vectors: List[List[float]]
    tongue_weights: Dict[str, float]
    coherence_score: float = 0.0
    centroid: Optional[List[float]] = None

    def compute_coherence(self):
        """Compute coherence as normalized dot-product agreement."""
        if len(self.intent_vectors) < 2:
            self.coherence_score = 1.0
            return
        # Average pairwise cosine similarity
        n = len(self.intent_vectors)
        total = 0.0
        pairs = 0
        for i in range(n):
            for j in range(i + 1, n):
                a = self.intent_vectors[i]
                b = self.intent_vectors[j]
                dot = sum(x * y for x, y in zip(a, b))
                mag_a = math.sqrt(sum(x * x for x in a)) or 1e-12
                mag_b = math.sqrt(sum(x * x for x in b)) or 1e-12
                total += dot / (mag_a * mag_b)
                pairs += 1
        self.coherence_score = total / pairs if pairs > 0 else 0.0

    def compute_centroid(self):
        """Compute geometric centroid of all intent vectors."""
        if not self.intent_vectors:
            self.centroid = [0.0] * 6
            return
        n = len(self.intent_vectors)
        dim = len(self.intent_vectors[0])
        self.centroid = [
            sum(v[d] for v in self.intent_vectors) / n
            for d in range(dim)
        ]


# =============================================================================
# Batch Offset Generator (Sacred Geometry)
# =============================================================================


def generate_batch_offsets(
    batch_size: int,
    batch_seed: bytes,
    dimensions: int = 6,
) -> List[Tuple[float, ...]]:
    """Generate non-duplicable geometric offsets for a batch of AIs.

    Uses phi-spiral spacing on a 6D hypersphere to ensure:
    - No two offsets are identical
    - Offsets form a recognizable sacred geometry pattern
    - Pattern is deterministic from seed (reproducible for verification)
    - Cannot be guessed without the seed

    Args:
        batch_size: Number of AIs in this batch
        batch_seed: Random seed for this batch
        dimensions: Dimensionality (default 6 for our manifold)

    Returns:
        List of 6D offset tuples, one per AI
    """
    offsets = []
    for i in range(batch_size):
        # Derive per-AI seed from batch seed + index
        h = hashlib.sha256(batch_seed + i.to_bytes(4, "big")).digest()

        # Convert to 6 floats in [-1, 1] using phi-spiral spacing
        vals = []
        for d in range(dimensions):
            # Extract 4 bytes per dimension
            raw = int.from_bytes(h[d * 4:(d + 1) * 4], "big")
            # Map to [-1, 1] with phi-modulated spacing
            angle = (raw / (2**32)) * 2 * math.pi
            # Phi-spiral: each dimension gets a golden-angle offset
            phi_offset = (i * PHI * (d + 1)) % (2 * math.pi)
            val = math.cos(angle + phi_offset) * (1 - (i / (batch_size + 1)))
            vals.append(round(val, 8))

        offsets.append(tuple(vals))
    return offsets


# =============================================================================
# Genesis Crystallization
# =============================================================================


def mint_identity_cube(
    egg: SacredEgg,
    hatch_result: HatchResult,
    batch_id: str,
    batch_index: int,
    batch_offset: Tuple[float, ...],
    context: List[float],
) -> IdentityCube:
    """Mint an Identity Cube for a newly hatched AI.

    Combines the egg's geometric context with the batch offset
    to produce a unique 6D identity vector.

    Args:
        egg: The Sacred Egg that was hatched
        hatch_result: The successful hatch result
        batch_id: Batch identifier
        batch_index: Index within batch
        batch_offset: 6D offset from generate_batch_offsets()
        context: The 6D context vector used during hatch

    Returns:
        A unique IdentityCube for this AI
    """
    # Combine context + batch offset to create the identity vector
    cube_vector = tuple(
        round(c + o, 8)
        for c, o in zip(context, batch_offset)
    )

    # Project to geometric cells
    u = project_to_sphere(list(cube_vector))
    v = project_to_cube(list(cube_vector))
    h = healpix_id(u, 2)
    z = morton_id(v, 2)

    # Compute cube hash
    cube_data = json.dumps({
        "egg_id": egg.egg_id,
        "batch_id": batch_id,
        "batch_index": batch_index,
        "cube_vector": list(cube_vector),
    }, sort_keys=True)
    cube_id = hashlib.sha256(cube_data.encode()).hexdigest()[:16]

    return IdentityCube(
        cube_id=cube_id,
        tongue_affinity=egg.primary_tongue,
        cube_vector=cube_vector,
        batch_id=batch_id,
        batch_index=batch_index,
        healpix_cell=h,
        morton_cell=z,
        egg_id=egg.egg_id,
        born_at=time.time(),
    )


class GenesisProtocol:
    """Orchestrates AI birth from Sacred Eggs.

    Usage:
        proto = GenesisProtocol(integrator)

        # Create a batch of eggs
        eggs = proto.create_batch(
            payloads=[b"init_data_1", b"init_data_2", ...],
            tongue="KO", batch_size=6, context=ctx,
            pk_kem_b64=pk, sk_dsa_b64=sk
        )

        # Hatch the batch → Identity Cubes
        cubes = proto.hatch_batch(
            eggs, context=ctx, tongue="KO",
            sk_kem_b64=sk, pk_dsa_b64=pk
        )
    """

    def __init__(self, integrator: SacredEggIntegrator):
        self.integrator = integrator

    def create_batch(
        self,
        payloads: List[bytes],
        tongue: str,
        context: List[float],
        pk_kem_b64: str,
        sk_dsa_b64: str,
        glyph: str = "hatchling",
        hatch_condition: Optional[dict] = None,
    ) -> Tuple[str, List[SacredEgg]]:
        """Create a batch of Sacred Eggs for AI spawning.

        Args:
            payloads: Initialization data for each AI
            tongue: Primary tongue for the batch
            context: 6D context vector
            pk_kem_b64: KEM public key
            sk_dsa_b64: DSA signing key
            glyph: Visual symbol for this batch
            hatch_condition: Ritual requirements (default: interior path)

        Returns:
            (batch_id, list of SacredEggs)
        """
        batch_id = hashlib.sha256(
            os.urandom(16) + str(time.time()).encode()
        ).hexdigest()[:12]

        cond = hatch_condition or {"path": "interior"}
        eggs = []
        for payload in payloads:
            egg = self.integrator.create_egg(
                payload, tongue, glyph, cond, context,
                pk_kem_b64, sk_dsa_b64,
            )
            eggs.append(egg)

        return batch_id, eggs

    def hatch_batch(
        self,
        batch_id: str,
        eggs: List[SacredEgg],
        context: List[float],
        agent_tongue: str,
        sk_kem_b64: str,
        pk_dsa_b64: str,
        ritual_mode: str = "solitary",
        batch_seed: Optional[bytes] = None,
    ) -> List[Optional[IdentityCube]]:
        """Hatch a batch of eggs and mint Identity Cubes.

        Args:
            batch_id: The batch identifier
            eggs: List of Sacred Eggs to hatch
            context: 6D context vector for hatching
            agent_tongue: Agent's active tongue
            sk_kem_b64: KEM secret key
            pk_dsa_b64: DSA verification key
            ritual_mode: Ritual type
            batch_seed: Seed for batch offsets (random if None)

        Returns:
            List of IdentityCubes (None for failed hatches)
        """
        seed = batch_seed or os.urandom(32)
        offsets = generate_batch_offsets(len(eggs), seed)
        cubes = []

        for i, egg in enumerate(eggs):
            result = self.integrator.hatch_egg(
                egg, context, agent_tongue,
                sk_kem_b64, pk_dsa_b64,
                ritual_mode=ritual_mode,
            )
            if result.success:
                cube = mint_identity_cube(
                    egg, result, batch_id, i, offsets[i], context,
                )
                cubes.append(cube)
            else:
                cubes.append(None)

        return cubes

    def verify_cube(self, cube: IdentityCube) -> bool:
        """Verify an Identity Cube's hash matches its data."""
        cube_data = json.dumps({
            "egg_id": cube.egg_id,
            "batch_id": cube.batch_id,
            "batch_index": cube.batch_index,
            "cube_vector": list(cube.cube_vector),
        }, sort_keys=True)
        expected = hashlib.sha256(cube_data.encode()).hexdigest()[:16]
        return cube.cube_id == expected

    def cubes_in_same_batch(self, cubes: List[IdentityCube]) -> bool:
        """Check if all cubes belong to the same batch."""
        if not cubes:
            return True
        batch_id = cubes[0].batch_id
        return all(c.batch_id == batch_id for c in cubes)
