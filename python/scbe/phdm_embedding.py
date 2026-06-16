"""PHDM 21D Embedding Model

Custom embedding model for the SCBE-AETHERMOORE framework.
Maps text inputs into a 21-dimensional Poincare Ball manifold
for hyperbolic AI safety governance.

Architecture:
- Embedding Dimension: 21D (6D hyperbolic + 6D phase + 3D flux + 6D audit)
- Geometry: Poincare Ball B^n with Harmonic Wall containment
- Polyhedral Lattice: 16 cognitive polyhedra
- Neurotransmitter Weights: Six Sacred Tongues

Author: Issac Davis
Version: 3.0.0
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Sequence
from enum import Enum
import hashlib
import json
import os

# Golden Ratio constant
PHI = 1.618033988749895

# Six Sacred Tongues weights (neurotransmitter analogs)
TONGUES = {
    "KO": {"name": "Kor'aelin", "weight": 1.00, "analog": "Dopamine", "function": "Motivation/Intent"},
    "AV": {"name": "Avali", "weight": 1.62, "analog": "Acetylcholine", "function": "Attention/Context"},
    "RU": {"name": "Runethic", "weight": 2.62, "analog": "Serotonin", "function": "Memory Consolidation"},
    "CA": {"name": "Cassisivadan", "weight": 4.24, "analog": "Glutamate", "function": "Execution"},
    "UM": {"name": "Umbroth", "weight": 6.85, "analog": "GABA", "function": "Suppression"},
    "DR": {"name": "Draumric", "weight": 11.09, "analog": "Cortisol", "function": "Lock/Seal"},
}


class FluxState(Enum):
    """Dimensional breathing states"""

    POLLY = 1.0  # Full cognitive capability
    QUASI = 0.5  # Defensive thinking
    DEMI = 0.1  # Survival mode only


@dataclass
class PHDM21DConfig:
    """Configuration for the 21D PHDM embedding model"""

    hyperbolic_dim: int = 6
    phase_dim: int = 6
    flux_dim: int = 3
    audit_dim: int = 6
    total_dim: int = 21
    poincare_radius: float = 1.0
    tube_radius: float = 0.15
    base_frequency: float = 440.0  # Hz (A4 note)

    def __post_init__(self):
        assert self.total_dim == (self.hyperbolic_dim + self.phase_dim + self.flux_dim + self.audit_dim)


@dataclass(frozen=True)
class InverseEmbeddingMatch:
    """Nearest-token witness for a geometric address.

    A continuous embedding is not globally invertible by itself. This records
    the bounded inverse that is actually useful for GeoSeal: resolve a point
    against a known token vocabulary and return the closest token plus the
    distance proof.
    """

    token: str
    distance: float
    rank: int
    exact: bool


class PoincareBall:
    """Poincare Ball manifold for hyperbolic geometry"""

    def __init__(self, radius: float = 1.0):
        self.radius = radius
        self.origin = np.zeros(6)

    def embed(self, vector: np.ndarray) -> np.ndarray:
        """Project vector into Poincare Ball"""
        norm = np.linalg.norm(vector)
        if norm >= self.radius:
            # Clamp to ball boundary with small margin
            vector = vector * (self.radius - 1e-5) / norm
        return vector

    def hyperbolic_distance(self, u: np.ndarray, v: np.ndarray) -> float:
        """Calculate hyperbolic distance in Poincare Ball"""
        u_norm_sq = np.sum(u**2)
        v_norm_sq = np.sum(v**2)
        diff_norm_sq = np.sum((u - v) ** 2)

        numerator = 2 * diff_norm_sq
        denominator = (1 - u_norm_sq) * (1 - v_norm_sq) + 1e-10

        return np.arccosh(1 + numerator / denominator)

    def harmonic_wall_cost(self, r: float, d: int = 14) -> float:
        """Calculate energy cost at radial distance r (Harmonic Wall)"""
        return r ** (d**2)


class PHDMEmbedder:
    """Main PHDM 21D Embedding class compatible with HuggingFace"""

    def __init__(self, config: Optional[PHDM21DConfig] = None):
        self.config = config or PHDM21DConfig()
        self.skull = PoincareBall(radius=self.config.poincare_radius)
        self._text_encoder = None  # Lazy load base encoder

    @classmethod
    def from_pretrained(cls, model_name: str) -> "PHDMEmbedder":
        """Load pretrained model from HuggingFace Hub"""
        embedder = cls()
        # In production, load weights from HF Hub
        # For now, initialize with default config
        return embedder

    def encode(self, text: str, context: Optional[Dict] = None) -> np.ndarray:
        """Encode text into 21D Poincare Ball coordinates"""
        context = context or {}

        # 1. Get base text embedding (using hash as placeholder)
        base_vector = self._hash_to_vector(text, dim=self.config.hyperbolic_dim)

        # 2. Embed into hyperbolic space (6D)
        hyperbolic = self.skull.embed(base_vector)

        # 3. Calculate phase components (6D Sacred Tongues)
        phase = self._calculate_phase(text, context)

        # 4. Calculate flux state (3D)
        flux = self._calculate_flux(context)

        # 5. Calculate audit metadata (6D)
        audit = self._calculate_audit(text, context)

        # Concatenate all components
        embedding = np.concatenate([hyperbolic, phase, flux, audit])

        assert len(embedding) == self.config.total_dim
        return embedding

    def geometric_address(self, token: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Encode one token as a portable Poincare address packet."""
        embedding = self.encode(token, context=context)
        hyperbolic = embedding[: self.config.hyperbolic_dim]
        return {
            "schema_version": "scbe_poincare_token_address_v1",
            "token": token,
            "hyperbolic_dim": self.config.hyperbolic_dim,
            "position": hyperbolic.tolist(),
            "radial_norm": float(np.linalg.norm(hyperbolic)),
            "trust_ring": self.get_trust_ring(embedding),
        }

    def inverse_embedding(
        self,
        embedding_or_position: np.ndarray | Sequence[float],
        candidates: Sequence[str],
        *,
        context: Optional[Dict] = None,
        top_k: int = 1,
        exact_tolerance: float = 1e-12,
    ) -> List[InverseEmbeddingMatch]:
        """Resolve a Poincare position back to the nearest token candidates.

        This is a bounded inverse: it is exact when the point came from one of
        the supplied candidates under this embedder, and honest otherwise by
        returning ranked distances instead of pretending the full hash is
        reversible from geometry alone.
        """
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        if not candidates:
            raise ValueError("candidates must not be empty")

        point = np.asarray(embedding_or_position, dtype=float)
        if point.ndim != 1:
            raise ValueError("embedding_or_position must be a 1D vector")
        if len(point) == self.config.total_dim:
            point = point[: self.config.hyperbolic_dim]
        if len(point) != self.config.hyperbolic_dim:
            raise ValueError(
                "position must have %d or %d dimensions" % (self.config.hyperbolic_dim, self.config.total_dim)
            )
        if np.linalg.norm(point) >= self.config.poincare_radius:
            raise ValueError("position is outside the open Poincare ball")

        ranked: List[Tuple[float, str]] = []
        for token in candidates:
            candidate = self.encode(token, context=context)[: self.config.hyperbolic_dim]
            dist = float(self.skull.hyperbolic_distance(point, candidate))
            ranked.append((dist, token))
        ranked.sort(key=lambda item: (item[0], item[1]))

        return [
            InverseEmbeddingMatch(
                token=token,
                distance=dist,
                rank=i + 1,
                exact=dist <= exact_tolerance,
            )
            for i, (dist, token) in enumerate(ranked[:top_k])
        ]

    def inverse_geometric_address(
        self,
        address: Dict[str, Any],
        candidates: Sequence[str],
        *,
        context: Optional[Dict] = None,
        top_k: int = 1,
    ) -> Dict[str, Any]:
        """Resolve a ``geometric_address`` packet back through a candidate table."""
        if address.get("schema_version") != "scbe_poincare_token_address_v1":
            raise ValueError("unknown geometric address schema")
        matches = self.inverse_embedding(
            address["position"],
            candidates,
            context=context,
            top_k=top_k,
        )
        return {
            "schema_version": "scbe_poincare_token_inverse_v1",
            "source_schema_version": address["schema_version"],
            "match": matches[0].__dict__,
            "matches": [m.__dict__ for m in matches],
        }

    def _hash_to_vector(self, text: str, dim: int) -> np.ndarray:
        """Convert text to vector using cryptographic hash"""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Use first dim*4 bytes, convert to floats in [-1, 1]
        values = []
        for i in range(dim):
            byte_val = hash_bytes[i % len(hash_bytes)]
            values.append((byte_val / 255.0) * 2 - 1)
        return np.array(values) * 0.5  # Scale to safe region

    def _calculate_phase(self, text: str, context: Dict) -> np.ndarray:
        """Calculate 6D phase vector from Sacred Tongues"""
        phases = []
        for tongue_code in ["KO", "AV", "RU", "CA", "UM", "DR"]:
            tongue = TONGUES[tongue_code]
            # Weight determines phase position
            weight = tongue["weight"]
            # Normalize by max weight (DR = 11.09)
            normalized = weight / 11.09
            phases.append(normalized * 0.8)  # Keep in safe region
        return np.array(phases)

    def _calculate_flux(self, context: Dict) -> np.ndarray:
        """Calculate 3D flux state (nu per dimension)"""
        flux_state = context.get("flux_state", FluxState.POLLY)
        if isinstance(flux_state, FluxState):
            nu = flux_state.value
        else:
            nu = float(flux_state)
        # Distribute across 3 dimensions
        return np.array([nu, nu, nu]) * 0.9

    def _calculate_audit(self, text: str, context: Dict) -> np.ndarray:
        """Calculate 6D audit metadata"""
        import time

        # Timestamp component
        timestamp = context.get("timestamp", time.time())
        ts_normalized = (timestamp % 86400) / 86400  # Normalize to [0,1]

        # User ID hash component
        user_id = context.get("user_id", "anonymous")
        user_hash = int(hashlib.sha256(user_id.encode()).hexdigest()[:8], 16)
        user_normalized = (user_hash % 1000) / 1000

        # Session component
        session_id = context.get("session_id", str(time.time()))
        session_hash = int(hashlib.sha256(session_id.encode()).hexdigest()[:8], 16)
        session_normalized = (session_hash % 1000) / 1000

        return np.array(
            [
                ts_normalized * 0.5,
                user_normalized * 0.5,
                session_normalized * 0.5,
                0.0,  # Reserved for layer traversal
                0.0,  # Reserved for decimal drift
                0.0,  # Reserved for provenance
            ]
        )

    def get_trust_ring(self, embedding: np.ndarray) -> str:
        """Determine trust ring based on radial distance"""
        hyperbolic = embedding[: self.config.hyperbolic_dim]
        dist = np.linalg.norm(hyperbolic)

        if dist < 0.3:
            return "CORE"  # 5ms latency
        elif dist < 0.7:
            return "INNER"  # 30ms latency
        elif dist < 0.9:
            return "OUTER"  # 200ms latency
        else:
            return "WALL"  # Blocked

    def calculate_energy_cost(self, embedding: np.ndarray) -> float:
        """Calculate Harmonic Wall energy cost"""
        hyperbolic = embedding[: self.config.hyperbolic_dim]
        dist = np.linalg.norm(hyperbolic)
        return self.skull.harmonic_wall_cost(dist)

    def to_dict(self) -> Dict:
        """Export model configuration"""
        return {
            "model_type": "phdm-21d-embedding",
            "version": "3.0.0",
            "config": {
                "hyperbolic_dim": self.config.hyperbolic_dim,
                "phase_dim": self.config.phase_dim,
                "flux_dim": self.config.flux_dim,
                "audit_dim": self.config.audit_dim,
                "total_dim": self.config.total_dim,
                "poincare_radius": self.config.poincare_radius,
            },
            "tongues": TONGUES,
        }

    def save_pretrained(self, save_directory: str):
        """Save model to directory"""
        os.makedirs(save_directory, exist_ok=True)
        config_path = os.path.join(save_directory, "config.json")
        with open(config_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# Example usage
if __name__ == "__main__":
    embedder = PHDMEmbedder()

    # Example text
    text = "Book a flight from SFO to NYC"

    # Get 21D embedding
    embedding = embedder.encode(text, context={"user_id": "user_123"})

    print(f"Input: {text}")
    print(f"Embedding shape: {embedding.shape}")
    print(f"Trust ring: {embedder.get_trust_ring(embedding)}")
    print(f"Energy cost: {embedder.calculate_energy_cost(embedding):.2e}")
    print(f"Embedding (first 10 dims): {embedding[:10]}")
