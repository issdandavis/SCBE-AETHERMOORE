"""
Polyhedral Hamiltonian Defense Manifold (PHDM)

A curated family of 16 canonical polyhedra providing diverse topological
structures for cryptographic verification:

- Platonic Solids (5): Symmetric baseline for safe states
- Archimedean Solids (3): Mixed-face complexity for dynamic paths
- Kepler-Poinsot (2): Non-convex stars for attack surface detection
- Toroidal (2): Szilassi/Császár for skip-attack resistance
- Johnson Solids (2): Near-regular bridges to real CFGs
- Rhombic Variants (2): Space-filling tessellation potential

The Hamiltonian path visits each polyhedron exactly once, with sequential
HMAC chaining for cryptographic binding.
"""

import numpy as np
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Set
from enum import Enum
import hmac


# Golden Ratio for icosahedral/dodecahedral geometry
PHI = (1 + np.sqrt(5)) / 2


class PolyhedronType(Enum):
    """Classification of polyhedron types."""
    PLATONIC = "platonic"
    ARCHIMEDEAN = "archimedean"
    KEPLER_POINSOT = "kepler_poinsot"
    TOROIDAL = "toroidal"
    JOHNSON = "johnson"
    RHOMBIC = "rhombic"


@dataclass
class Polyhedron:
    """
    A polyhedron in the PHDM family.

    Attributes:
        name: Human-readable name
        poly_type: Classification type
        vertices: Number of vertices (V)
        edges: Number of edges (E)
        faces: Number of faces (F)
        face_types: Description of face types
        genus: Topological genus (0 for convex, 1 for toroidal)
        vertex_coords: Optional 3D vertex coordinates
        adjacency: Optional vertex adjacency list
        notes: Role in PHDM system
    """
    name: str
    poly_type: PolyhedronType
    vertices: int
    edges: int
    faces: int
    face_types: str
    genus: int = 0
    vertex_coords: Optional[np.ndarray] = None
    adjacency: Optional[List[List[int]]] = None
    notes: str = ""

    def euler_characteristic(self) -> int:
        """Compute Euler characteristic: V - E + F = 2 - 2g"""
        return self.vertices - self.edges + self.faces

    def expected_euler(self) -> int:
        """Expected Euler characteristic based on genus."""
        return 2 - 2 * self.genus

    def is_valid_topology(self) -> bool:
        """Check if V-E+F matches expected Euler characteristic."""
        return self.euler_characteristic() == self.expected_euler()

    def serialize(self) -> bytes:
        """Serialize polyhedron data for HMAC chaining."""
        data = (
            self.name.encode() + b"|" +
            self.poly_type.value.encode() + b"|" +
            str(self.vertices).encode() + b"|" +
            str(self.edges).encode() + b"|" +
            str(self.faces).encode() + b"|" +
            str(self.genus).encode()
        )
        if self.vertex_coords is not None:
            data += b"|" + self.vertex_coords.tobytes()
        return data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.poly_type.value,
            "V": self.vertices,
            "E": self.edges,
            "F": self.faces,
            "face_types": self.face_types,
            "genus": self.genus,
            "euler": self.euler_characteristic(),
            "notes": self.notes
        }


def create_tetrahedron_coords() -> np.ndarray:
    """Generate tetrahedron vertex coordinates."""
    return np.array([
        [1, 1, 1],
        [1, -1, -1],
        [-1, 1, -1],
        [-1, -1, 1]
    ], dtype=float) / np.sqrt(3)


def create_cube_coords() -> np.ndarray:
    """Generate cube vertex coordinates."""
    coords = []
    for x in [-1, 1]:
        for y in [-1, 1]:
            for z in [-1, 1]:
                coords.append([x, y, z])
    return np.array(coords, dtype=float)


def create_octahedron_coords() -> np.ndarray:
    """Generate octahedron vertex coordinates."""
    return np.array([
        [1, 0, 0], [-1, 0, 0],
        [0, 1, 0], [0, -1, 0],
        [0, 0, 1], [0, 0, -1]
    ], dtype=float)


def create_dodecahedron_coords() -> np.ndarray:
    """Generate dodecahedron vertex coordinates using golden ratio."""
    coords = []
    # Vertices from cube corners
    for x in [-1, 1]:
        for y in [-1, 1]:
            for z in [-1, 1]:
                coords.append([x, y, z])

    # Vertices on faces (using golden ratio)
    for x in [-1/PHI, 1/PHI]:
        for y in [-PHI, PHI]:
            coords.append([0, x, y])
            coords.append([x, y, 0])
            coords.append([y, 0, x])

    return np.array(coords, dtype=float)


def create_icosahedron_coords() -> np.ndarray:
    """Generate icosahedron vertex coordinates."""
    coords = []
    for x in [-1, 1]:
        for y in [-PHI, PHI]:
            coords.append([0, x, y])
            coords.append([x, y, 0])
            coords.append([y, 0, x])

    return np.array(coords, dtype=float) / np.sqrt(1 + PHI**2)


# =============================================================================
# The 16 Canonical PHDM Polyhedra
# =============================================================================

def get_phdm_family() -> List[Polyhedron]:
    """
    Return the complete PHDM family of 16 canonical polyhedra.

    Ordered for optimal Hamiltonian traversal.
    """
    return [
        # =====================================================================
        # PLATONIC SOLIDS (5) - Symmetric baseline for safe states
        # =====================================================================
        Polyhedron(
            name="Tetrahedron",
            poly_type=PolyhedronType.PLATONIC,
            vertices=4, edges=6, faces=4,
            face_types="4 triangles",
            vertex_coords=create_tetrahedron_coords(),
            notes="Minimal convex - ideal for origin anchoring"
        ),
        Polyhedron(
            name="Cube",
            poly_type=PolyhedronType.PLATONIC,
            vertices=8, edges=12, faces=6,
            face_types="6 squares",
            vertex_coords=create_cube_coords(),
            notes="Orthogonal structure for grid-like embeddings"
        ),
        Polyhedron(
            name="Octahedron",
            poly_type=PolyhedronType.PLATONIC,
            vertices=6, edges=12, faces=8,
            face_types="8 triangles",
            vertex_coords=create_octahedron_coords(),
            notes="Dual to cube - high coordination"
        ),
        Polyhedron(
            name="Dodecahedron",
            poly_type=PolyhedronType.PLATONIC,
            vertices=20, edges=30, faces=12,
            face_types="12 pentagons",
            vertex_coords=create_dodecahedron_coords(),
            notes="Golden ratio symmetry for harmonic scaling"
        ),
        Polyhedron(
            name="Icosahedron",
            poly_type=PolyhedronType.PLATONIC,
            vertices=12, edges=30, faces=20,
            face_types="20 triangles",
            vertex_coords=create_icosahedron_coords(),
            notes="Maximal vertices for Platonic - dense connectivity"
        ),

        # =====================================================================
        # ARCHIMEDEAN SOLIDS (3) - Mixed-face complexity for dynamic paths
        # =====================================================================
        Polyhedron(
            name="Truncated Tetrahedron",
            poly_type=PolyhedronType.ARCHIMEDEAN,
            vertices=12, edges=18, faces=8,
            face_types="4 triangles + 4 hexagons",
            notes="Truncation introduces higher faces for deviation traps"
        ),
        Polyhedron(
            name="Cuboctahedron",
            poly_type=PolyhedronType.ARCHIMEDEAN,
            vertices=12, edges=24, faces=14,
            face_types="8 triangles + 6 squares",
            notes="Archimedean 'bridge' between cube/octahedron"
        ),
        Polyhedron(
            name="Icosidodecahedron",
            poly_type=PolyhedronType.ARCHIMEDEAN,
            vertices=30, edges=60, faces=32,
            face_types="20 triangles + 12 pentagons",
            notes="High-density for geodesic smoothing"
        ),

        # =====================================================================
        # KEPLER-POINSOT (2) - Non-convex stars for attack surfaces
        # =====================================================================
        Polyhedron(
            name="Small Stellated Dodecahedron",
            poly_type=PolyhedronType.KEPLER_POINSOT,
            vertices=12, edges=30, faces=12,
            face_types="12 pentagrams",
            notes="Star density for sharp curvature spikes"
        ),
        Polyhedron(
            name="Great Dodecahedron",
            poly_type=PolyhedronType.KEPLER_POINSOT,
            vertices=12, edges=30, faces=12,
            face_types="12 pentagons (intersecting)",
            notes="Deeper non-convexity for intrusion boundaries"
        ),

        # =====================================================================
        # TOROIDAL (2) - Genus > 0 for topological robustness
        # =====================================================================
        Polyhedron(
            name="Szilassi Polyhedron",
            poly_type=PolyhedronType.TOROIDAL,
            vertices=14, edges=21, faces=7,
            face_types="7 hexagons",
            genus=1,
            notes="Genus 1 torus - every face touches every other; maximal adjacency"
        ),
        Polyhedron(
            name="Császár Polyhedron",
            poly_type=PolyhedronType.TOROIDAL,
            vertices=7, edges=21, faces=14,
            face_types="14 triangles",
            genus=1,
            notes="Dual to Szilassi - minimal vertices with full triangulation"
        ),

        # =====================================================================
        # JOHNSON SOLIDS (2) - Near-regular bridges to real CFGs
        # =====================================================================
        Polyhedron(
            name="Pentagonal Bipyramid",
            poly_type=PolyhedronType.JOHNSON,
            vertices=7, edges=15, faces=10,
            face_types="10 triangles",
            notes="Dual-like extension for pyramidal deviations"
        ),
        Polyhedron(
            name="Triangular Cupola",
            poly_type=PolyhedronType.JOHNSON,
            vertices=9, edges=15, faces=8,
            face_types="4 triangles + 3 squares + 1 hexagon",
            notes="Cupola for layered manifold stacking"
        ),

        # =====================================================================
        # RHOMBIC VARIANTS (2) - Space-filling tessellation
        # =====================================================================
        Polyhedron(
            name="Rhombic Dodecahedron",
            poly_type=PolyhedronType.RHOMBIC,
            vertices=14, edges=24, faces=12,
            face_types="12 rhombi",
            notes="Space-filling dual to cuboctahedron - dense packing"
        ),
        Polyhedron(
            name="Bilinski Dodecahedron",
            poly_type=PolyhedronType.RHOMBIC,
            vertices=14, edges=24, faces=12,
            face_types="12 rhombi (golden ratio variant)",
            notes="Alternative rhombic symmetry with golden proportions"
        ),
    ]


# =============================================================================
# Hamiltonian Path and HMAC Chaining
# =============================================================================

@dataclass
class HamiltonianNode:
    """A node in the Hamiltonian path through the PHDM."""
    polyhedron: Polyhedron
    position: int
    hmac_tag: bytes
    prev_tag: bytes


class PHDMHamiltonianPath:
    """
    Manages Hamiltonian path traversal through the PHDM polyhedra family.

    The path visits each of the 16 polyhedra exactly once, with HMAC
    chaining providing cryptographic binding between nodes.
    """

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize the PHDM path.

        Args:
            key: HMAC key (generated if not provided)
        """
        self.family = get_phdm_family()
        self.key = key or hashlib.sha256(b"phdm_default_key").digest()
        self._path: List[HamiltonianNode] = []
        self._iv = b'\x00' * 32

    def compute_path(self) -> List[HamiltonianNode]:
        """
        Compute the Hamiltonian path with HMAC chaining.

        Returns:
            List of HamiltonianNode objects forming the complete path
        """
        self._path = []
        prev_tag = self._iv

        for i, poly in enumerate(self.family):
            # Compute HMAC tag: H_k(poly_data || position || prev_tag)
            data = poly.serialize() + str(i).encode() + prev_tag
            tag = hmac.new(self.key, data, hashlib.sha256).digest()

            node = HamiltonianNode(
                polyhedron=poly,
                position=i,
                hmac_tag=tag,
                prev_tag=prev_tag
            )
            self._path.append(node)
            prev_tag = tag

        return self._path

    def verify_path(self) -> Tuple[bool, Optional[int]]:
        """
        Verify the integrity of the Hamiltonian path.

        Returns:
            Tuple of (is_valid, first_invalid_position or None)
        """
        if not self._path:
            return True, None

        prev_tag = self._iv

        for node in self._path:
            # Recompute expected tag
            data = node.polyhedron.serialize() + str(node.position).encode() + prev_tag
            expected_tag = hmac.new(self.key, data, hashlib.sha256).digest()

            if not hmac.compare_digest(node.hmac_tag, expected_tag):
                return False, node.position

            if node.prev_tag != prev_tag:
                return False, node.position

            prev_tag = node.hmac_tag

        return True, None

    def get_path_digest(self) -> bytes:
        """Get a digest of the complete path for comparison."""
        if not self._path:
            self.compute_path()

        chain_data = b""
        for node in self._path:
            chain_data += node.hmac_tag

        return hashlib.sha256(chain_data).digest()

    def find_polyhedron(self, name: str) -> Optional[HamiltonianNode]:
        """Find a polyhedron in the path by name."""
        if not self._path:
            self.compute_path()

        for node in self._path:
            if node.polyhedron.name.lower() == name.lower():
                return node
        return None

    def get_geodesic_distance(self, name1: str, name2: str) -> Optional[int]:
        """
        Get the geodesic distance (path length) between two polyhedra.

        Args:
            name1: First polyhedron name
            name2: Second polyhedron name

        Returns:
            Number of steps between them, or None if not found
        """
        node1 = self.find_polyhedron(name1)
        node2 = self.find_polyhedron(name2)

        if node1 is None or node2 is None:
            return None

        return abs(node1.position - node2.position)

    def export_state(self) -> Dict[str, Any]:
        """Export path state for serialization."""
        if not self._path:
            self.compute_path()

        return {
            "path_length": len(self._path),
            "path_digest": self.get_path_digest().hex(),
            "polyhedra": [node.polyhedron.to_dict() for node in self._path],
            "hmac_tags": [node.hmac_tag.hex() for node in self._path]
        }


# =============================================================================
# Deviation Detection
# =============================================================================

class PHDMDeviationDetector:
    """
    Detects deviations from expected PHDM manifold structure.

    Uses geodesic and curvature analysis in embedded space to identify
    anomalous behavior that may indicate attacks.
    """

    def __init__(self, phdm_path: PHDMHamiltonianPath):
        """
        Initialize detector with a PHDM path.

        Args:
            phdm_path: Computed Hamiltonian path
        """
        self.path = phdm_path
        if not self.path._path:
            self.path.compute_path()

        # Build expected metrics
        self._expected_euler_sum = sum(
            node.polyhedron.euler_characteristic()
            for node in self.path._path
        )
        self._expected_vertex_total = sum(
            node.polyhedron.vertices
            for node in self.path._path
        )

    def check_topological_integrity(self) -> Tuple[bool, List[str]]:
        """
        Check that all polyhedra satisfy their expected topology.

        Returns:
            Tuple of (all_valid, list of error messages)
        """
        errors = []

        for node in self.path._path:
            poly = node.polyhedron
            if not poly.is_valid_topology():
                errors.append(
                    f"{poly.name}: Euler χ={poly.euler_characteristic()} "
                    f"expected {poly.expected_euler()}"
                )

        return len(errors) == 0, errors

    def detect_manifold_deviation(self, observed_vertices: int,
                                  observed_euler: int) -> float:
        """
        Detect deviation from expected manifold structure.

        Args:
            observed_vertices: Total vertices observed
            observed_euler: Total Euler characteristic observed

        Returns:
            Deviation score (0.0 = perfect, higher = more deviation)
        """
        vertex_deviation = abs(observed_vertices - self._expected_vertex_total)
        euler_deviation = abs(observed_euler - self._expected_euler_sum)

        # Normalize by expected values
        vertex_score = vertex_deviation / max(1, self._expected_vertex_total)
        euler_score = euler_deviation / max(1, abs(self._expected_euler_sum))

        return (vertex_score + euler_score) / 2

    def compute_curvature_at_node(self, position: int) -> float:
        """
        Compute local curvature at a path position.

        Uses discrete curvature based on vertex density.

        Args:
            position: Position in path (0-15)

        Returns:
            Curvature value (higher = more curved)
        """
        if position < 0 or position >= len(self.path._path):
            return 0.0

        node = self.path._path[position]
        poly = node.polyhedron

        # Discrete curvature: vertex defect / vertex count
        # For convex polyhedra: 4π distributed over vertices
        if poly.vertices > 0:
            return (4 * np.pi - poly.euler_characteristic() * 2 * np.pi) / poly.vertices
        return 0.0

    def get_curvature_profile(self) -> np.ndarray:
        """Get curvature values along the entire path."""
        return np.array([
            self.compute_curvature_at_node(i)
            for i in range(len(self.path._path))
        ])


# =============================================================================
# Utility Functions
# =============================================================================

def get_family_summary() -> Dict[str, Any]:
    """Get a summary of the PHDM family."""
    family = get_phdm_family()

    by_type = {}
    for poly in family:
        t = poly.poly_type.value
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(poly.name)

    total_v = sum(p.vertices for p in family)
    total_e = sum(p.edges for p in family)
    total_f = sum(p.faces for p in family)

    return {
        "total_polyhedra": len(family),
        "by_type": by_type,
        "total_vertices": total_v,
        "total_edges": total_e,
        "total_faces": total_f,
        "types": list(by_type.keys())
    }


def validate_all_polyhedra() -> Tuple[bool, List[str]]:
    """Validate all polyhedra in the PHDM family."""
    family = get_phdm_family()
    errors = []

    for poly in family:
        if not poly.is_valid_topology():
            errors.append(
                f"{poly.name}: Invalid topology "
                f"(V={poly.vertices}, E={poly.edges}, F={poly.faces}, "
                f"χ={poly.euler_characteristic()}, expected {poly.expected_euler()})"
            )

    return len(errors) == 0, errors
