"""
GeoSeal Geometric Trust Manifold
Extracted from SCBE Production Pack demo_integrated_system.py

To use in GitHub repo:
1. Copy to: SCBE-AETHERMOORE/symphonic_cipher/geoseal/manifold.py
2. Create: SCBE-AETHERMOORE/symphonic_cipher/geoseal/__init__.py
3. Import: from symphonic_cipher.geoseal import GeoSealManifold
"""

import numpy as np
from typing import Dict


class GeoSealManifold:
    """
    GeoSeal Geometric Trust Manifold.

    Dual-space security using:
    - Sphere S^n for behavioral state
    - Hypercube [0,1]^m for policy state

    The distance between projections determines trust level:
    - Small distance → Interior path → Fast, trusted
    - Large distance → Exterior path → Slow, suspicious
    """

    def __init__(self, dimension: int = 6):
        """
        Initialize GeoSeal manifold.

        Args:
            dimension: Dimension of both sphere and hypercube
        """
        self.dim = dimension

    def project_to_sphere(self, context: np.ndarray) -> np.ndarray:
        """
        Project context vector to unit sphere S^n.

        This represents where the user/agent IS based on behavior.

        Args:
            context: Context vector (any norm)

        Returns:
            Unit vector on sphere (norm = 1)
        """
        norm = np.linalg.norm(context)
        if norm < 1e-12:
            return np.zeros_like(context)
        return context / norm

    def project_to_hypercube(self, features: Dict[str, float]) -> np.ndarray:
        """
        Project policy features to hypercube [0,1]^m.

        This represents where the user/agent SHOULD BE based on permissions.

        Args:
            features: Policy features (trust_score, uptime, etc.)

        Returns:
            Point in [0,1]^m hypercube
        """
        # Extract policy-relevant features (all already in [0,1])
        cube_point = np.array([
            features.get('trust_score', 0.5),
            features.get('uptime', 0.5),
            features.get('approval_rate', 0.5),
            features.get('coherence', 0.5),
            features.get('stability', 0.5),
            features.get('relationship_age', 0.5),
        ])
        # Clamp to [0,1] to be safe
        return np.clip(cube_point, 0, 1)

    def geometric_distance(self, sphere_pos: np.ndarray,
                          cube_pos: np.ndarray) -> float:
        """
        Compute geometric distance between sphere and cube positions.

        This measures behavioral vs policy alignment.

        Args:
            sphere_pos: Position on unit sphere (behavior)
            cube_pos: Position in hypercube (policy)

        Returns:
            Euclidean distance in normalized space
        """
        # Map sphere point to [0,1] range for comparison
        sphere_normalized = (sphere_pos + 1) / 2  # [-1,1] → [0,1]

        # Euclidean distance in normalized space
        distance = np.linalg.norm(sphere_normalized - cube_pos)

        return distance

    def classify_path(self, distance: float, threshold: float = 0.3) -> str:
        """
        Classify request path based on geometric distance.

        Args:
            distance: Geometric distance between sphere and cube
            threshold: Interior/exterior boundary

        Returns:
            'interior' (trusted) or 'exterior' (suspicious)
        """
        return 'interior' if distance < threshold else 'exterior'

    def time_dilation_factor(self, distance: float, gamma: float = 2.0) -> float:
        """
        Compute time dilation factor based on geometric distance.

        Formula: τ_allow = τ₀ · exp(-γ · r)

        This is the "security gravity well" - the farther you are from
        trusted space geometrically, the slower time runs for you.

        Args:
            distance: Geometric distance (radius from trusted space)
            gamma: Dilation strength parameter (default: 2.0)

        Returns:
            Time dilation factor in [0,1] (1 = no dilation, 0 = maximum)

        Examples:
            >>> manifold = GeoSealManifold()
            >>> manifold.time_dilation_factor(0.0)  # Interior path
            1.0
            >>> manifold.time_dilation_factor(1.0)  # Moderate exterior
            0.1353...
            >>> manifold.time_dilation_factor(2.0)  # Far exterior
            0.0183...
        """
        return np.exp(-gamma * distance)

    def compute_allowed_latency(self, distance: float, base_latency: float = 50.0,
                               max_latency: float = 2000.0, gamma: float = 2.0) -> float:
        """
        Compute allowed latency based on geometric distance.

        Args:
            distance: Geometric distance
            base_latency: Normal latency for interior path (ms)
            max_latency: Maximum latency for exterior path (ms)
            gamma: Dilation strength

        Returns:
            Allowed latency in milliseconds
        """
        dilation = self.time_dilation_factor(distance, gamma)

        if dilation > 0.5:  # Interior path
            return base_latency
        else:  # Exterior path - slow down
            return max_latency

    def compute_required_pow_bits(self, distance: float,
                                  min_bits: int = 0,
                                  max_bits: int = 24) -> int:
        """
        Compute required proof-of-work bits based on distance.

        The farther from trusted space, the more computational work required.

        Args:
            distance: Geometric distance
            min_bits: Minimum PoW bits (interior path)
            max_bits: Maximum PoW bits (exterior path)

        Returns:
            Required PoW difficulty bits
        """
        # Linear interpolation based on distance
        # distance=0 → min_bits, distance=2 → max_bits
        normalized_distance = min(distance / 2.0, 1.0)
        bits = int(min_bits + (max_bits - min_bits) * normalized_distance)
        return bits

    def get_telemetry(self, sphere_pos: np.ndarray, cube_pos: np.ndarray) -> Dict:
        """
        Get complete telemetry for monitoring and Sentinel rules.

        Args:
            sphere_pos: Sphere position
            cube_pos: Cube position

        Returns:
            Dictionary with all metrics
        """
        distance = self.geometric_distance(sphere_pos, cube_pos)
        path = self.classify_path(distance)
        dilation = self.time_dilation_factor(distance)
        latency = self.compute_allowed_latency(distance)
        pow_bits = self.compute_required_pow_bits(distance)

        return {
            'sphere_position': sphere_pos.tolist(),
            'cube_position': cube_pos.tolist(),
            'geometric_distance': distance,
            'path': path,
            'time_dilation': dilation,
            'allowed_latency_ms': latency,
            'required_pow_bits': pow_bits,
            'geometric_classification': 'trusted_interior' if path == 'interior' else 'exterior_governance'
        }


# Example usage
if __name__ == '__main__':
    # Initialize manifold
    manifold = GeoSealManifold(dimension=6)

    # Example 1: Trusted user
    context_trusted = np.array([0.1, 0.2, 0.15, 0.1, 0.12, 0.18])
    features_trusted = {
        'trust_score': 0.9,
        'uptime': 0.95,
        'approval_rate': 0.88,
        'coherence': 0.92,
        'stability': 0.90,
        'relationship_age': 0.85
    }

    sphere_pos = manifold.project_to_sphere(context_trusted)
    cube_pos = manifold.project_to_hypercube(features_trusted)
    telemetry = manifold.get_telemetry(sphere_pos, cube_pos)

    print("Trusted User:")
    print(f"  Geometric Distance: {telemetry['geometric_distance']:.4f}")
    print(f"  Path: {telemetry['path']}")
    print(f"  Allowed Latency: {telemetry['allowed_latency_ms']:.0f}ms")
    print()

    # Example 2: Suspicious user (stolen credentials)
    context_suspicious = np.array([5.2, 4.8, 6.1, 5.5, 4.9, 5.3])
    features_suspicious = {
        'trust_score': 0.1,
        'uptime': 0.2,
        'approval_rate': 0.05,
        'coherence': 0.15,
        'stability': 0.1,
        'relationship_age': 0.0
    }

    sphere_pos2 = manifold.project_to_sphere(context_suspicious)
    cube_pos2 = manifold.project_to_hypercube(features_suspicious)
    telemetry2 = manifold.get_telemetry(sphere_pos2, cube_pos2)

    print("Suspicious User (Stolen Credentials):")
    print(f"  Geometric Distance: {telemetry2['geometric_distance']:.4f}")
    print(f"  Path: {telemetry2['path']}")
    print(f"  Allowed Latency: {telemetry2['allowed_latency_ms']:.0f}ms")
    print(f"  Time Dilation: {telemetry2['time_dilation']:.4f} (95% slowdown!)")
