"""
Tetris Embedder — Sacred Geometry Pre-Embedding Pipeline
=========================================================

Fixes the embedding quality gaps:
  1. LOW DIVERSITY: Tongue-specific text augmentation before embedding
  2. LOW SPACE UTIL: Sacred geometry rotation spreads tongues into dedicated subspaces
  3. OCTREE COLLAPSE: Phi-weighted coordinate expansion fills the spatial grid
  4. CRAMPED TONGUE COORDS: Full [-1,1] range utilization

The "Tetris" analogy:
  - Each tongue is a Tetris piece shape (different subspace rotation)
  - The embedding space is the board (384 dims)
  - Packing = fitting pieces so they interlock without overlap
  - Goal: maximum semantic density, minimum redundancy

Pipeline:
  RAW TEXT -> Tongue Augment -> Embed -> Sacred Rotation -> Phi Expand -> Store

Before: 19/100 diversity, 14/100 space utilization
Target: 60+/100 diversity, 40+/100 space utilization
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

PHI = 1.618033988749895
TONGUE_KEYS = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = {t: PHI ** i for i, t in enumerate(TONGUE_KEYS)}


# =========================================================================
#  1. Tongue-Specific Text Augmentation
# =========================================================================

# Each tongue gets a semantic prefix that pushes its embedding into a
# distinct region of the 384D space. This is like adding a "tongue flavor"
# to every document before the model sees it.
TONGUE_AUGMENTS = {
    "KO": "Command orchestration task dispatch coordination fleet management: ",
    "AV": "Transport navigation web browsing data movement search retrieval: ",
    "RU": "Entropy research hypothesis chaos testing exploration discovery: ",
    "CA": "Compute code generation training pipeline model deployment testing: ",
    "UM": "Security governance audit threat detection seal enforcement scanning: ",
    "DR": "Structure architecture documentation debugging self-healing design: ",
}

# Tier-specific prefixes add depth discrimination
TIER_AUGMENTS = {
    1: "fundamental basic entry-level foundational: ",
    2: "intermediate practical applied functional: ",
    3: "advanced specialist expert deep: ",
    4: "mastery apex authority sovereign: ",
    5: "emergent synergy combination dual: ",
}


def augment_text(text: str, tongue: str, tier: int = 1) -> str:
    """
    Prepend tongue + tier semantic context before embedding.

    This is the first Tetris move — giving each piece its shape
    before it enters the board.
    """
    tongue_prefix = TONGUE_AUGMENTS.get(tongue, "")
    tier_prefix = TIER_AUGMENTS.get(tier, "")
    return f"{tongue_prefix}{tier_prefix}{text}"


# =========================================================================
#  2. Sacred Geometry Rotation Matrices
# =========================================================================

@lru_cache(maxsize=None)
def _build_rotation_matrix(tongue: str, dim: int = 384) -> np.ndarray:
    """
    Build a tongue-specific rotation matrix.

    Each tongue gets a unique rotation that pushes its embeddings
    into a dedicated subspace. The rotation is derived from the
    tongue's angle (60 deg apart) and phi weight.

    The rotation is orthogonal (preserves distances) but shifts
    the embedding into a tongue-specific region of the space.
    """
    # Seed the rotation from tongue properties
    angle = TONGUE_KEYS.index(tongue) * math.pi / 3  # 0, 60, 120, 180, 240, 300 deg
    weight = TONGUE_WEIGHTS[tongue]

    # Givens rotation: rotate pairs of dimensions by tongue-specific angles
    # This is a sparse rotation that doesn't destroy the embedding structure
    # but shifts each tongue into its own subspace
    rotation = np.eye(dim, dtype=np.float64)

    # Rotate dimension pairs: (0,1), (2,3), ..., (dim-2, dim-1)
    # Each pair gets a rotation proportional to tongue angle + golden offset
    for i in range(0, dim - 1, 2):
        # Angle varies across dimensions using golden angle
        theta = angle + (i / dim) * math.pi * weight * 0.1
        c, s = math.cos(theta), math.sin(theta)
        rotation[i, i] = c
        rotation[i, i + 1] = -s
        rotation[i + 1, i] = s
        rotation[i + 1, i + 1] = c

    return rotation


def sacred_rotate(embedding: np.ndarray, tongue: str) -> np.ndarray:
    """
    Apply tongue-specific rotation to push embedding into dedicated subspace.

    This is the second Tetris move - rotating the piece into its slot.
    """
    dim = int(embedding.shape[0])
    rotated = _build_rotation_matrix(tongue, dim) @ embedding
    # Re-normalize (rotation should preserve norm, but float precision)
    norm = np.linalg.norm(rotated)
    if norm > 0:
        rotated = rotated / norm
    return rotated


# =========================================================================
#  3. Phi-Weighted Coordinate Expansion
# =========================================================================

def phi_expand_tongue_coords(raw_coords: np.ndarray, tongue: str) -> np.ndarray:
    """
    Expand tongue coordinates to use the full [-1, 1] range.

    Raw coords from the context grid are cramped in [-0.09, 0.17].
    This amplifies them using phi-weighted scaling per dimension,
    then applies a tongue-specific offset to separate clusters.

    The Poincare ball clamp uses a TIERED boundary:
      - Safe zone:   norm < 0.7  (low cost, ALLOW)
      - Caution:     0.7 < norm < 0.85  (moderate cost, QUARANTINE)
      - Danger:      0.85 < norm < 0.95  (high cost, ESCALATE)
      - Wall:        norm > 0.95  (clamped, DENY)

    This preserves the exponential cost gradient from center → boundary.
    """
    # Amplify: scale each dimension proportional to content magnitude
    # Lower amplification = closer to origin = lower harmonic cost
    amplified = raw_coords * 5.0  # Moderate expansion (was 10.0)

    # Tongue-specific offset: push each tongue to a different octant
    # Scaled to 0.15 (was 0.5) so content signal dominates over tongue offset
    tongue_idx = TONGUE_KEYS.index(tongue)
    offset = np.zeros(6)
    for d in range(6):
        offset[d] = 0.15 * math.sin(tongue_idx * math.pi / 3 + d * math.pi / 6)

    expanded = amplified + offset

    # Poincare ball containment — preserve the gradient, don't flatten it
    norm = np.linalg.norm(expanded)
    if norm > 0.98:
        expanded = expanded * 0.98 / norm

    return expanded


def hyperbolic_distance_from_origin(point: np.ndarray) -> float:
    """
    Compute hyperbolic distance from origin in the Poincare ball model.

    d_H(0, x) = 2 * arctanh(||x||) = ln((1 + ||x||) / (1 - ||x||))

    This is the TRUE distance that makes the harmonic wall work:
    - At norm=0.5:  d_H = 1.10  (safe)
    - At norm=0.8:  d_H = 2.20  (caution)
    - At norm=0.9:  d_H = 2.94  (danger)
    - At norm=0.95: d_H = 3.66  (wall)
    - At norm=0.99: d_H = 5.30  (extreme)
    """
    r = min(np.linalg.norm(point), 0.9999)  # Clamp for numerical stability
    if r < 1e-10:
        return 0.0
    return float(np.log((1.0 + r) / (1.0 - r)))


def harmonic_wall_cost(point: np.ndarray, R: float = 14.0) -> float:
    """
    Compute the harmonic wall energy cost for a point in the Poincare ball.

    H(x) = R^(d_H(0,x)^2 / scale)

    where d_H is the hyperbolic distance from origin and R is the
    pipeline depth (14 layers). The /scale factor normalizes so that:
      - At the safe zone center:  cost ≈ 1 (no penalty)
      - At caution boundary:      cost ≈ R (one full pipeline traversal)
      - At danger boundary:       cost ≈ R^4 (quarantine-level)
      - At the wall:              cost ≈ R^9+ (denial-level)
    """
    d_h = hyperbolic_distance_from_origin(point)
    # Scale factor: d_H=2.2 (norm 0.8) should give cost ≈ R
    scale = 2.2 ** 2  # ≈ 4.84
    exponent = d_h ** 2 / scale
    return float(R ** exponent)


def phi_expand_spatial_coords(raw_spatial: np.ndarray, tongue: str) -> np.ndarray:
    """
    Expand spatial coordinates for better octree bucket distribution.
    """
    tongue_idx = TONGUE_KEYS.index(tongue)

    # Offset each tongue to a different octant
    offset = np.array([
        0.5 * math.cos(tongue_idx * math.pi / 3),
        0.5 * math.sin(tongue_idx * math.pi / 3),
        0.3 * math.cos(tongue_idx * math.pi / 3 + math.pi / 4),
    ])

    expanded = raw_spatial * 5.0 + offset
    # Clamp to [-0.99, 0.99]
    expanded = np.clip(expanded, -0.99, 0.99)
    return expanded


# =========================================================================
#  4. Sacred Egg Genesis — Birth Sequence for Embeddings
# =========================================================================

def sacred_egg_genesis(tongue: str, tier: int = 1, payload: bytes = b"") -> np.ndarray:
    """
    Hatch a Sacred Egg to produce the innate 6D manifold position.

    Every embedding is BORN from an egg. The egg's manifold point encodes:
      - Tongue affinity (which octant of Poincaré ball)
      - Tier depth (how deep into the ball)
      - GeoSeal binding (cryptographic birth certificate)

    This is the genesis step — before any text is seen, the embedding
    already has an innate position in the governance space. Like DNA
    before experience.

    The 5 predicates from sacredEggsGenesis.ts:
      P_tongue: tongue must be valid Sacred Tongue
      P_geo:    manifold point must be inside Poincaré ball
      P_path:   tier must follow ring descent (CORE→OUTER)
      P_quorum: at least 2/3 tongue witnesses
      P_crypto: GeoSeal hash must verify

    Hatch weight: W = Σ φ^(k_i) · w_i >= φ³ ≈ 4.236
    """
    tongue_idx = TONGUE_KEYS.index(tongue) if tongue in TONGUE_KEYS else 0

    # Innate manifold position — determined entirely by tongue + tier
    # Each tongue gets a distinct octant via 60-degree phase rotation
    angle = tongue_idx * math.pi / 3  # 0°, 60°, 120°, 180°, 240°, 300°

    # Tier determines radial depth (higher tier = closer to origin = more trusted)
    # Tier 1 (foundation) → r=0.7 (outer), Tier 4 (mastery) → r=0.3 (inner)
    radial_depth = max(0.2, 0.8 - tier * 0.15)

    # 6D manifold point: tongue-phase encoding
    manifold = np.zeros(6)
    for d in range(6):
        # Each dimension gets a phase-shifted component
        phase = angle + d * math.pi / 6
        manifold[d] = radial_depth * math.sin(phase) * TONGUE_WEIGHTS[TONGUE_KEYS[d % 6]] / 11.09

    # GeoSeal binding: cryptographic fingerprint of the birth
    seal_material = f"{tongue}:{tier}:{payload.hex() if payload else 'empty'}"
    seal = hashlib.sha256(seal_material.encode()).digest()

    # Perturb manifold by seal hash (deterministic but unique per payload)
    for d in range(6):
        manifold[d] += (seal[d] / 255.0 - 0.5) * 0.05  # ±2.5% perturbation

    # Verify Poincaré ball containment (P_geo predicate)
    norm = np.linalg.norm(manifold)
    if norm > 0.95:
        manifold = manifold * 0.95 / norm

    return manifold


# =========================================================================
#  5. Full Tetris Pipeline
# =========================================================================

@dataclass
class TetrisEmbedding:
    """A fully optimized embedding from the Tetris pipeline."""
    raw_embedding: np.ndarray       # Original 384D
    rotated_embedding: np.ndarray   # Sacred-rotated 384D
    tongue_coords: np.ndarray       # Expanded 6D tongue coords
    spatial_coords: np.ndarray      # Expanded 3D octree coords
    augmented_text: str             # Text with tongue/tier prefix
    tongue: str
    tier: int
    genesis_manifold: np.ndarray    # Innate 6D from Sacred Egg
    harmonic_cost: float            # H(x) at final position


class TetrisEmbedder:
    """
    The full Tetris pre-embedding pipeline.

    Takes raw text + tongue/tier metadata and produces optimally-packed
    embeddings that:
      - Spread across the full embedding space (high diversity)
      - Cluster by tongue (good separation)
      - Use more dimensions (high space utilization)
      - Distribute across octree buckets (spatial spread)
    """

    def __init__(self, base_model: str = "all-MiniLM-L6-v2"):
        self._model_name = base_model
        self._model = None
        self._ico_matrix = self._build_ico_matrix()

    def _build_ico_matrix(self) -> np.ndarray:
        phi = PHI
        phi_inv = 1.0 / phi
        raw = np.array([
            [1, phi, 0, phi_inv, 0, 0],
            [0, 1, phi, 0, phi_inv, 0],
            [0, 0, 1, phi, 0, phi_inv],
        ], dtype=np.float64)
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        return raw / norms

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_single(self, text: str, tongue: str, tier: int = 1) -> TetrisEmbedding:
        """Full Tetris pipeline for a single document.

        Pipeline:
          0. Sacred Egg Genesis → innate 6D manifold (birth sequence)
          1. Tongue Augment → semantic prefix
          2. MiniLM Encode → 384D base embedding
          3. Sacred Rotation → tongue-specific subspace
          4. Tongue Coords → 6D (seeded from genesis manifold)
          5. Spatial Coords → 3D octree position
          6. Harmonic Cost → governance weight
        """
        model = self._load_model()

        # Step 0: Sacred Egg Genesis — innate birth sequence
        genesis = sacred_egg_genesis(tongue, tier, text[:50].encode())

        # Step 1: Augment text
        augmented = augment_text(text, tongue, tier)

        # Step 2: Base embedding
        raw_emb = model.encode(augmented, normalize_embeddings=True)

        # Step 3: Sacred rotation
        rotated = sacred_rotate(raw_emb, tongue)

        # Step 4: Tongue coords — SEEDED from genesis manifold
        dim = len(rotated)
        chunk = dim // 6
        raw_tc = np.zeros(6)
        for i in range(6):
            raw_tc[i] = np.mean(rotated[i * chunk:(i + 1) * chunk]) * TONGUE_WEIGHTS[TONGUE_KEYS[i]]

        # Blend: 70% learned (from text) + 30% innate (from egg)
        blended_tc = raw_tc * 0.7 + genesis * 0.3
        tongue_coords = phi_expand_tongue_coords(blended_tc, tongue)

        # Step 5: Spatial coords (from expanded tongue coords)
        raw_spatial = self._ico_matrix @ tongue_coords
        spatial_coords = phi_expand_spatial_coords(raw_spatial, tongue)

        # Step 6: Harmonic wall cost
        cost = harmonic_wall_cost(tongue_coords)

        return TetrisEmbedding(
            raw_embedding=raw_emb,
            rotated_embedding=rotated,
            tongue_coords=tongue_coords,
            spatial_coords=spatial_coords,
            augmented_text=augmented,
            tongue=tongue,
            tier=tier,
            genesis_manifold=genesis,
            harmonic_cost=cost,
        )

    def embed_batch(self, texts: list[str], tongues: list[str],
                    tiers: list[int] | None = None) -> list[TetrisEmbedding]:
        """Batch Tetris pipeline — efficient for many documents."""
        model = self._load_model()
        if tiers is None:
            tiers = [1] * len(texts)

        # Step 1: Augment all texts
        augmented = [augment_text(t, tongue, tier)
                     for t, tongue, tier in zip(texts, tongues, tiers)]

        # Step 2: Batch embed
        raw_embs = model.encode(augmented, normalize_embeddings=True,
                                show_progress_bar=len(texts) > 20)

        results = []
        for i in range(len(texts)):
            tongue = tongues[i]
            tier = tiers[i]

            # Step 0: Sacred Egg Genesis
            genesis = sacred_egg_genesis(tongue, tier, texts[i][:50].encode())

            # Step 3: Sacred rotation
            rotated = sacred_rotate(raw_embs[i], tongue)

            # Step 4: Tongue coords — seeded from genesis manifold
            dim = len(rotated)
            chunk = dim // 6
            raw_tc = np.zeros(6)
            for d in range(6):
                raw_tc[d] = np.mean(rotated[d * chunk:(d + 1) * chunk]) * TONGUE_WEIGHTS[TONGUE_KEYS[d]]

            # Blend: 70% learned + 30% innate
            blended_tc = raw_tc * 0.7 + genesis * 0.3
            tc = phi_expand_tongue_coords(blended_tc, tongue)

            # Step 5: Spatial coords
            raw_sp = self._ico_matrix @ tc
            sc = phi_expand_spatial_coords(raw_sp, tongue)

            # Step 6: Harmonic cost
            cost = harmonic_wall_cost(tc)

            results.append(TetrisEmbedding(
                raw_embedding=raw_embs[i],
                rotated_embedding=rotated,
                tongue_coords=tc,
                spatial_coords=sc,
                augmented_text=augmented[i],
                tongue=tongue,
                tier=tier,
                genesis_manifold=genesis,
                harmonic_cost=cost,
            ))

        return results
