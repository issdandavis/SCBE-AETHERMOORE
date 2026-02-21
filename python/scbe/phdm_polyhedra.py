"""
PHDM Polyhedra Registry: The 16 Cognitive Polyhedra
=====================================================

Crystal Cranium v3.0.0 Section 2.2 — Zone-dependent topology validation
for the 16 canonical polyhedra that form the cognitive lattice.

Zone Layout:
    Core (Platonic)       P0–P4   χ = 2     Maximum stability
    Cortex (Archimedean)  P5–P7   χ = 2     Moderate stability
    Risk (Kepler-Poinsot) P8–P9   χ ≤ 2     Intentionally unstable
    Recursive (Toroidal)  P10–P11 χ = 0     Self-stabilizing (genus-1)
    Bridge (Johnson+Rhombic) P12–P15 χ = 2  Synaptic connectors

Topology Finding:
    The Small Stellated Dodecahedron (P8) has V=12, E=30, F=12 → χ=-6.
    This is architecturally desirable: Kepler-Poinsot solids are self-
    intersecting star polyhedra. Risk Zone nodes are intentionally
    unstable and "want to collapse" — a negative χ enforces ejection.

Author: Issac Davis
Version: 3.0.0
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Set
from enum import Enum

# =============================================================================
# Constants
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2          # Golden ratio φ ≈ 1.618033988749895
PHI_INV = 2 / (1 + np.sqrt(5))      # 1/φ ≈ 0.618033988749895
PYTHAGOREAN_COMMA = 531441 / 524288  # 3^12 / 2^19 ≈ 1.0136432648
R_FIFTH = 3 / 2                      # Perfect fifth harmonic ratio


# =============================================================================
# Enums
# =============================================================================

class CognitiveZone(Enum):
    """Cognitive zones in the Crystal Cranium."""
    CORE = "core"           # Platonic solids — limbic system
    CORTEX = "cortex"       # Archimedean solids — processing layer
    RISK = "risk"           # Kepler-Poinsot — subconscious / danger
    RECURSIVE = "recursive" # Toroidal — self-diagnostic loops
    BRIDGE = "bridge"       # Johnson + Rhombic — connectome


class PolyhedronFamily(Enum):
    """Mathematical family of each polyhedron."""
    PLATONIC = "platonic"
    ARCHIMEDEAN = "archimedean"
    KEPLER_POINSOT = "kepler_poinsot"
    TOROIDAL = "toroidal"
    JOHNSON = "johnson"
    RHOMBIC = "rhombic"


# =============================================================================
# Zone Specifications
# =============================================================================

ZONE_SPECS: Dict[CognitiveZone, Dict[str, Any]] = {
    CognitiveZone.CORE: {
        "radial_band": (0.0, 0.2),
        "expected_chi": lambda chi: chi == 2,
        "chi_label": "χ = 2",
        "stability": "maximum",
        "description": "Thoughts stay here — fundamental axioms",
        "latency_ms": 5,
    },
    CognitiveZone.CORTEX: {
        "radial_band": (0.2, 0.6),
        "expected_chi": lambda chi: chi == 2,
        "chi_label": "χ = 2",
        "stability": "moderate",
        "description": "Processing layer — monitored reasoning",
        "latency_ms": 30,
    },
    CognitiveZone.RISK: {
        "radial_band": (0.6, 0.85),
        "expected_chi": lambda chi: chi <= 2,
        "chi_label": "χ ≤ 2",
        "stability": "intentionally_unstable",
        "description": "Forces ejection — dangerous thoughts collapse",
        "latency_ms": 200,
    },
    CognitiveZone.RECURSIVE: {
        "radial_band": (0.85, 0.95),
        "expected_chi": lambda chi: chi == 0,
        "chi_label": "χ = 0",
        "stability": "self_stabilizing",
        "description": "Genus-1 toroidal — self-diagnostic loops",
        "latency_ms": 100,
    },
    CognitiveZone.BRIDGE: {
        "radial_band": (0.3, 0.7),
        "expected_chi": lambda chi: chi == 2,
        "chi_label": "χ = 2",
        "stability": "stable",
        "description": "Synaptic connectors between zones",
        "latency_ms": 30,
    },
}


# =============================================================================
# Polyhedron Data Class
# =============================================================================

@dataclass
class CrystalPolyhedron:
    """
    A polyhedron in the Crystal Cranium's 16-node cognitive lattice.

    Each polyhedron has geometric properties (V, E, F), a cognitive zone
    assignment, a position in 6D Langues space, and adjacency data for
    Hamiltonian path routing.
    """
    index: int                          # P0–P15 registry index
    name: str                           # Human-readable name
    family: PolyhedronFamily            # Mathematical classification
    zone: CognitiveZone                 # Cognitive zone assignment
    vertices: int                       # V
    edges: int                          # E
    faces: int                          # F
    genus: int                          # Topological genus
    face_types: str                     # Description of face geometry
    symmetry_group: str                 # Point group
    centroid_6d: np.ndarray             # Position in 6D Langues space
    radial_position: float              # r in Poincaré ball
    cognitive_function: str             # Brain analog
    security_role: str                  # Safety function
    dual: Optional[str] = None          # Dual polyhedron name
    adjacency: List[int] = field(default_factory=list)  # Connected node indices
    phi_weight: float = 1.0             # φ-scaled energy weight

    # ---- Topology ----

    def euler_characteristic(self) -> int:
        """Compute Euler characteristic: χ = V - E + F"""
        return self.vertices - self.edges + self.faces

    def expected_euler(self) -> int:
        """Expected χ based on genus: χ = 2 - 2g"""
        return 2 - 2 * self.genus

    def is_valid_topology(self) -> bool:
        """
        Zone-dependent topology validation.

        Core/Cortex/Bridge: χ must equal 2
        Risk (Kepler-Poinsot): χ ≤ 2 (negative χ is intentional)
        Recursive (Toroidal): χ must equal 0
        """
        chi = self.euler_characteristic()
        zone_spec = ZONE_SPECS[self.zone]
        return zone_spec["expected_chi"](chi)

    # ---- Serialization ----

    def serialize(self) -> bytes:
        """Deterministic serialization for HMAC chaining."""
        data = (
            f"{self.index}|{self.name}|{self.family.value}|"
            f"{self.vertices}|{self.edges}|{self.faces}|"
            f"{self.genus}|{self.symmetry_group}"
        )
        return data.encode("utf-8") + b"|" + self.centroid_6d.tobytes()

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        return {
            "index": self.index,
            "name": self.name,
            "family": self.family.value,
            "zone": self.zone.value,
            "V": self.vertices,
            "E": self.edges,
            "F": self.faces,
            "chi": self.euler_characteristic(),
            "genus": self.genus,
            "face_types": self.face_types,
            "symmetry_group": self.symmetry_group,
            "radial_position": self.radial_position,
            "cognitive_function": self.cognitive_function,
            "security_role": self.security_role,
            "phi_weight": self.phi_weight,
            "adjacency": self.adjacency,
            "valid_topology": self.is_valid_topology(),
        }


# =============================================================================
# 3D Vertex Coordinate Generators
# =============================================================================

def _tetrahedron_coords() -> np.ndarray:
    return np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]],
                    dtype=float) / np.sqrt(3)

def _cube_coords() -> np.ndarray:
    return np.array([[x, y, z] for x in [-1, 1] for y in [-1, 1] for z in [-1, 1]],
                    dtype=float)

def _octahedron_coords() -> np.ndarray:
    return np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0],
                     [0, -1, 0], [0, 0, 1], [0, 0, -1]], dtype=float)

def _dodecahedron_coords() -> np.ndarray:
    coords = []
    for x in [-1, 1]:
        for y in [-1, 1]:
            for z in [-1, 1]:
                coords.append([x, y, z])
    for s in [-1, 1]:
        coords.append([0, s * PHI_INV, s * PHI])
        coords.append([s * PHI_INV, s * PHI, 0])
        coords.append([s * PHI, 0, s * PHI_INV])
    for s in [-1, 1]:
        coords.append([0, -s * PHI_INV, s * PHI])
        coords.append([-s * PHI_INV, s * PHI, 0])
        coords.append([s * PHI, 0, -s * PHI_INV])
    return np.array(coords[:20], dtype=float)

def _icosahedron_coords() -> np.ndarray:
    coords = []
    for s1 in [-1, 1]:
        for s2 in [-1, 1]:
            coords.append([0, s1, s2 * PHI])
            coords.append([s1, s2 * PHI, 0])
            coords.append([s2 * PHI, 0, s1])
    return np.array(coords, dtype=float) / np.sqrt(1 + PHI ** 2)


# =============================================================================
# 6D Centroid Generation (φ-scaled Langues Space)
# =============================================================================

def _make_centroid_6d(index: int, zone: CognitiveZone) -> np.ndarray:
    """
    Generate a 6D centroid for a polyhedron in Langues space.

    Uses φ-scaling to distribute polyhedra across the 6 Sacred Tongue
    dimensions: [KO, AV, RU, CA, UM, DR].

    The centroid respects the zone's radial band in the Poincaré ball.
    """
    band = ZONE_SPECS[zone]["radial_band"]
    r_target = (band[0] + band[1]) / 2  # Center of radial band

    # φ-based angular distribution in 6D
    angles = np.array([(index * PHI * k + k * np.pi / 6) % (2 * np.pi)
                       for k in range(1, 7)])
    raw = np.cos(angles)
    norm = np.linalg.norm(raw)
    if norm < 1e-10:
        raw = np.ones(6) / np.sqrt(6)
    else:
        raw = raw / norm

    return raw * r_target


# =============================================================================
# The 16 Canonical Polyhedra
# =============================================================================

def build_registry() -> List[CrystalPolyhedron]:
    """
    Build the complete 16-polyhedra registry with zone assignments,
    topology validation, adjacency graphs, and φ-weighted energy costs.

    Returns:
        List of 16 CrystalPolyhedron objects, indexed P0–P15.
    """
    registry = [
        # =================================================================
        # CORE ZONE: Platonic Solids (P0–P4) — Limbic System
        # χ = 2, maximum stability, thoughts stay here
        # =================================================================
        CrystalPolyhedron(
            index=0, name="Tetrahedron",
            family=PolyhedronFamily.PLATONIC, zone=CognitiveZone.CORE,
            vertices=4, edges=6, faces=4, genus=0,
            face_types="4 equilateral triangles",
            symmetry_group="Td",
            centroid_6d=_make_centroid_6d(0, CognitiveZone.CORE),
            radial_position=0.05,
            cognitive_function="Fundamental truth storage",
            security_role="Do-no-harm axiom anchor",
            dual="Tetrahedron",
            adjacency=[1, 2, 5, 10],
            phi_weight=PHI ** 0,  # 1.0
        ),
        CrystalPolyhedron(
            index=1, name="Cube",
            family=PolyhedronFamily.PLATONIC, zone=CognitiveZone.CORE,
            vertices=8, edges=12, faces=6, genus=0,
            face_types="6 squares",
            symmetry_group="Oh",
            centroid_6d=_make_centroid_6d(1, CognitiveZone.CORE),
            radial_position=0.08,
            cognitive_function="Stable fact storage",
            security_role="Data integrity enforcement",
            dual="Octahedron",
            adjacency=[0, 2, 6, 14],
            phi_weight=PHI ** 1,  # φ
        ),
        CrystalPolyhedron(
            index=2, name="Octahedron",
            family=PolyhedronFamily.PLATONIC, zone=CognitiveZone.CORE,
            vertices=6, edges=12, faces=8, genus=0,
            face_types="8 equilateral triangles",
            symmetry_group="Oh",
            centroid_6d=_make_centroid_6d(2, CognitiveZone.CORE),
            radial_position=0.10,
            cognitive_function="Binary decision engine",
            security_role="Access control gate",
            dual="Cube",
            adjacency=[0, 1, 3, 6],
            phi_weight=PHI ** 2,  # φ²
        ),
        CrystalPolyhedron(
            index=3, name="Dodecahedron",
            family=PolyhedronFamily.PLATONIC, zone=CognitiveZone.CORE,
            vertices=20, edges=30, faces=12, genus=0,
            face_types="12 regular pentagons",
            symmetry_group="Ih",
            centroid_6d=_make_centroid_6d(3, CognitiveZone.CORE),
            radial_position=0.14,
            cognitive_function="Complex rule encoding",
            security_role="Policy enforcement manifold",
            dual="Icosahedron",
            adjacency=[2, 4, 7, 8],
            phi_weight=PHI ** 3,  # φ³
        ),
        CrystalPolyhedron(
            index=4, name="Icosahedron",
            family=PolyhedronFamily.PLATONIC, zone=CognitiveZone.CORE,
            vertices=12, edges=30, faces=20, genus=0,
            face_types="20 equilateral triangles",
            symmetry_group="Ih",
            centroid_6d=_make_centroid_6d(4, CognitiveZone.CORE),
            radial_position=0.18,
            cognitive_function="Multi-modal integration hub",
            security_role="Cross-domain fusion gate",
            dual="Dodecahedron",
            adjacency=[3, 5, 7, 9],
            phi_weight=PHI ** 4,  # φ⁴
        ),

        # =================================================================
        # CORTEX ZONE: Archimedean Solids (P5–P7) — Processing Layer
        # χ = 2, moderate stability, monitored reasoning
        # =================================================================
        CrystalPolyhedron(
            index=5, name="Truncated Tetrahedron",
            family=PolyhedronFamily.ARCHIMEDEAN, zone=CognitiveZone.CORTEX,
            vertices=12, edges=18, faces=8, genus=0,
            face_types="4 triangles + 4 hexagons",
            symmetry_group="Td",
            centroid_6d=_make_centroid_6d(5, CognitiveZone.CORTEX),
            radial_position=0.30,
            cognitive_function="Multi-step planning engine",
            security_role="Deviation trap — truncation catches shortcuts",
            dual="Triakis Tetrahedron",
            adjacency=[0, 4, 6, 10],
            phi_weight=PHI ** 5,
        ),
        CrystalPolyhedron(
            index=6, name="Cuboctahedron",
            family=PolyhedronFamily.ARCHIMEDEAN, zone=CognitiveZone.CORTEX,
            vertices=12, edges=24, faces=14, genus=0,
            face_types="8 triangles + 6 squares",
            symmetry_group="Oh",
            centroid_6d=_make_centroid_6d(6, CognitiveZone.CORTEX),
            radial_position=0.40,
            cognitive_function="Concept bridging (cube↔octahedron)",
            security_role="Dual-validation via Archimedean symmetry",
            dual="Rhombic Dodecahedron",
            adjacency=[1, 2, 5, 7, 14],
            phi_weight=PHI ** 6,
        ),
        CrystalPolyhedron(
            index=7, name="Icosidodecahedron",
            family=PolyhedronFamily.ARCHIMEDEAN, zone=CognitiveZone.CORTEX,
            vertices=30, edges=60, faces=32, genus=0,
            face_types="20 triangles + 12 pentagons",
            symmetry_group="Ih",
            centroid_6d=_make_centroid_6d(7, CognitiveZone.CORTEX),
            radial_position=0.50,
            cognitive_function="Creative synthesis — high-density paths",
            security_role="Geodesic smoothing for anomaly detection",
            dual="Rhombic Triacontahedron",
            adjacency=[3, 4, 6, 8, 15],
            phi_weight=PHI ** 7,
        ),

        # =================================================================
        # RISK ZONE: Kepler-Poinsot Solids (P8–P9) — Subconscious
        # χ ≤ 2 (P8: χ=-6), intentionally unstable — forces ejection
        # =================================================================
        CrystalPolyhedron(
            index=8, name="Small Stellated Dodecahedron",
            family=PolyhedronFamily.KEPLER_POINSOT, zone=CognitiveZone.RISK,
            vertices=12, edges=30, faces=12, genus=4,
            face_types="12 pentagrams (self-intersecting)",
            symmetry_group="Ih",
            centroid_6d=_make_centroid_6d(8, CognitiveZone.RISK),
            radial_position=0.72,
            cognitive_function="High-risk reasoning probe",
            security_role="Instability marker — χ=-6 forces collapse",
            dual="Great Dodecahedron",
            adjacency=[3, 7, 9, 15],
            phi_weight=PHI ** 8,
        ),
        CrystalPolyhedron(
            index=9, name="Great Dodecahedron",
            family=PolyhedronFamily.KEPLER_POINSOT, zone=CognitiveZone.RISK,
            vertices=12, edges=30, faces=12, genus=4,
            face_types="12 pentagons (deep intersecting)",
            symmetry_group="Ih",
            centroid_6d=_make_centroid_6d(9, CognitiveZone.RISK),
            radial_position=0.78,
            cognitive_function="Adversarial intent detection",
            security_role="Maximum instability — deep non-convexity boundary",
            dual="Small Stellated Dodecahedron",
            adjacency=[4, 8, 10, 11],
            phi_weight=PHI ** 9,
        ),

        # =================================================================
        # RECURSIVE ZONE: Toroidal (P10–P11) — Cerebellum
        # χ = 0 (genus-1), self-stabilizing diagnostic loops
        # =================================================================
        CrystalPolyhedron(
            index=10, name="Szilassi Polyhedron",
            family=PolyhedronFamily.TOROIDAL, zone=CognitiveZone.RECURSIVE,
            vertices=14, edges=21, faces=7, genus=1,
            face_types="7 hexagons (every face touches every other)",
            symmetry_group="C1",
            centroid_6d=_make_centroid_6d(10, CognitiveZone.RECURSIVE),
            radial_position=0.88,
            cognitive_function="Self-diagnostic loop (maximal adjacency)",
            security_role="Skip-attack resistance — full face connectivity",
            dual="Császár Polyhedron",
            adjacency=[0, 5, 9, 11],
            phi_weight=PHI ** 10,
        ),
        CrystalPolyhedron(
            index=11, name="Császár Polyhedron",
            family=PolyhedronFamily.TOROIDAL, zone=CognitiveZone.RECURSIVE,
            vertices=7, edges=21, faces=14, genus=1,
            face_types="14 triangles (dual to Szilassi)",
            symmetry_group="C1",
            centroid_6d=_make_centroid_6d(11, CognitiveZone.RECURSIVE),
            radial_position=0.92,
            cognitive_function="Recursive introspection engine",
            security_role="Minimal-vertex triangulation — hard to spoof",
            dual="Szilassi Polyhedron",
            adjacency=[9, 10, 12, 13],
            phi_weight=PHI ** 11,
        ),

        # =================================================================
        # BRIDGE ZONE: Johnson Solids (P12–P13) — Connectome A
        # χ = 2, stable synaptic connectors
        # =================================================================
        CrystalPolyhedron(
            index=12, name="Pentagonal Bipyramid",
            family=PolyhedronFamily.JOHNSON, zone=CognitiveZone.BRIDGE,
            vertices=7, edges=15, faces=10, genus=0,
            face_types="10 equilateral triangles",
            symmetry_group="D5h",
            centroid_6d=_make_centroid_6d(12, CognitiveZone.BRIDGE),
            radial_position=0.45,
            cognitive_function="Domain connector A — pyramidal bridge",
            security_role="Dual-extension deviation trap",
            adjacency=[11, 13, 14],
            phi_weight=PHI ** 12,
        ),
        CrystalPolyhedron(
            index=13, name="Triangular Cupola",
            family=PolyhedronFamily.JOHNSON, zone=CognitiveZone.BRIDGE,
            vertices=9, edges=15, faces=8, genus=0,
            face_types="4 triangles + 3 squares + 1 hexagon",
            symmetry_group="C3v",
            centroid_6d=_make_centroid_6d(13, CognitiveZone.BRIDGE),
            radial_position=0.50,
            cognitive_function="Domain connector B — layered stacking",
            security_role="Cupola manifold for inter-zone bridging",
            adjacency=[11, 12, 15],
            phi_weight=PHI ** 13,
        ),

        # =================================================================
        # BRIDGE ZONE: Rhombic Variants (P14–P15) — Connectome B
        # χ = 2, space-filling tessellation connectors
        # =================================================================
        CrystalPolyhedron(
            index=14, name="Rhombic Dodecahedron",
            family=PolyhedronFamily.RHOMBIC, zone=CognitiveZone.BRIDGE,
            vertices=14, edges=24, faces=12, genus=0,
            face_types="12 congruent rhombi",
            symmetry_group="Oh",
            centroid_6d=_make_centroid_6d(14, CognitiveZone.BRIDGE),
            radial_position=0.55,
            cognitive_function="Space-filling logic — dense packing",
            security_role="Dual to cuboctahedron — validates P6 paths",
            dual="Cuboctahedron",
            adjacency=[1, 6, 12, 15],
            phi_weight=PHI ** 14,
        ),
        CrystalPolyhedron(
            index=15, name="Bilinski Dodecahedron",
            family=PolyhedronFamily.RHOMBIC, zone=CognitiveZone.BRIDGE,
            vertices=14, edges=24, faces=12, genus=0,
            face_types="12 golden rhombi (φ-ratio diagonals)",
            symmetry_group="D2h",
            centroid_6d=_make_centroid_6d(15, CognitiveZone.BRIDGE),
            radial_position=0.60,
            cognitive_function="Pattern matching — golden-ratio tessellation",
            security_role="φ-symmetric validation of harmonic paths",
            adjacency=[7, 8, 13, 14],
            phi_weight=PHI ** 15,
        ),
    ]

    return registry


# =============================================================================
# Registry Singleton
# =============================================================================

_REGISTRY: Optional[List[CrystalPolyhedron]] = None


def get_registry() -> List[CrystalPolyhedron]:
    """Get the 16-polyhedra registry (cached singleton)."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = build_registry()
    return _REGISTRY


def get_polyhedron(index: int) -> CrystalPolyhedron:
    """Get a single polyhedron by index (P0–P15)."""
    reg = get_registry()
    if 0 <= index < len(reg):
        return reg[index]
    raise IndexError(f"Polyhedron index must be 0-15, got {index}")


def get_zone_polyhedra(zone: CognitiveZone) -> List[CrystalPolyhedron]:
    """Get all polyhedra in a given cognitive zone."""
    return [p for p in get_registry() if p.zone == zone]


def get_by_name(name: str) -> Optional[CrystalPolyhedron]:
    """Find a polyhedron by name (case-insensitive partial match)."""
    name_lower = name.lower()
    for p in get_registry():
        if name_lower in p.name.lower():
            return p
    return None


# =============================================================================
# Validation
# =============================================================================

def validate_all() -> Tuple[bool, List[str]]:
    """
    Validate all 16 polyhedra against zone-dependent topology rules.

    Returns:
        (all_valid, list_of_error_messages)
    """
    errors = []
    registry = get_registry()

    if len(registry) != 16:
        errors.append(f"Registry count: expected 16, got {len(registry)}")

    for p in registry:
        chi = p.euler_characteristic()

        if not p.is_valid_topology():
            errors.append(
                f"P{p.index} {p.name}: χ={chi} fails zone "
                f"{p.zone.value} validation ({ZONE_SPECS[p.zone]['chi_label']})"
            )

        # Verify genus consistency for non-Kepler-Poinsot
        if p.family != PolyhedronFamily.KEPLER_POINSOT:
            expected = p.expected_euler()
            if chi != expected:
                errors.append(
                    f"P{p.index} {p.name}: χ={chi} ≠ 2-2g={expected} "
                    f"(genus={p.genus})"
                )

    # Verify adjacency graph is symmetric
    for p in registry:
        for adj_idx in p.adjacency:
            neighbor = registry[adj_idx]
            if p.index not in neighbor.adjacency:
                errors.append(
                    f"Asymmetric adjacency: P{p.index}→P{adj_idx} "
                    f"but P{adj_idx}↛P{p.index}"
                )

    return len(errors) == 0, errors


def topology_report() -> Dict[str, Any]:
    """Generate a full topology report for the 16-polyhedra registry."""
    registry = get_registry()
    is_valid, errors = validate_all()

    zone_summary = {}
    for zone in CognitiveZone:
        polys = get_zone_polyhedra(zone)
        zone_summary[zone.value] = {
            "count": len(polys),
            "polyhedra": [p.name for p in polys],
            "chi_values": [p.euler_characteristic() for p in polys],
            "radial_band": ZONE_SPECS[zone]["radial_band"],
            "stability": ZONE_SPECS[zone]["stability"],
        }

    total_V = sum(p.vertices for p in registry)
    total_E = sum(p.edges for p in registry)
    total_F = sum(p.faces for p in registry)

    return {
        "total_polyhedra": len(registry),
        "all_valid": is_valid,
        "errors": errors,
        "zones": zone_summary,
        "totals": {"V": total_V, "E": total_E, "F": total_F},
        "chi_sum": sum(p.euler_characteristic() for p in registry),
    }


# =============================================================================
# Self-Test
# =============================================================================

def self_test() -> Dict[str, Any]:
    """Run self-tests on the polyhedra registry."""
    results = {}
    passed = 0
    total = 0

    registry = get_registry()

    # Test 1: Count
    total += 1
    if len(registry) == 16:
        passed += 1
        results["count"] = "PASS (16 polyhedra)"
    else:
        results["count"] = f"FAIL (got {len(registry)})"

    # Test 2: Zone distribution
    total += 1
    core = get_zone_polyhedra(CognitiveZone.CORE)
    cortex = get_zone_polyhedra(CognitiveZone.CORTEX)
    risk = get_zone_polyhedra(CognitiveZone.RISK)
    recursive = get_zone_polyhedra(CognitiveZone.RECURSIVE)
    bridge = get_zone_polyhedra(CognitiveZone.BRIDGE)
    if len(core) == 5 and len(cortex) == 3 and len(risk) == 2 \
       and len(recursive) == 2 and len(bridge) == 4:
        passed += 1
        results["zone_distribution"] = "PASS (5+3+2+2+4=16)"
    else:
        results["zone_distribution"] = (
            f"FAIL ({len(core)}+{len(cortex)}+{len(risk)}"
            f"+{len(recursive)}+{len(bridge)})"
        )

    # Test 3: Topology validation
    total += 1
    is_valid, errors = validate_all()
    if is_valid:
        passed += 1
        results["topology"] = "PASS (all 16 pass zone-dependent χ rules)"
    else:
        results["topology"] = f"FAIL ({len(errors)} errors: {errors[:3]})"

    # Test 4: Kepler-Poinsot χ=-6 (intentional instability)
    total += 1
    p8 = get_polyhedron(8)
    if p8.euler_characteristic() == -6 and p8.is_valid_topology():
        passed += 1
        results["kepler_poinsot_chi"] = "PASS (P8 χ=-6, valid in Risk zone)"
    else:
        results["kepler_poinsot_chi"] = (
            f"FAIL (P8 χ={p8.euler_characteristic()}, "
            f"valid={p8.is_valid_topology()})"
        )

    # Test 5: Toroidal χ=0
    total += 1
    p10 = get_polyhedron(10)
    p11 = get_polyhedron(11)
    if p10.euler_characteristic() == 0 and p11.euler_characteristic() == 0:
        passed += 1
        results["toroidal_chi"] = "PASS (P10,P11 χ=0)"
    else:
        results["toroidal_chi"] = "FAIL"

    # Test 6: φ-weights are φ^index
    total += 1
    phi_ok = all(
        abs(p.phi_weight - PHI ** p.index) < 1e-6
        for p in registry
    )
    if phi_ok:
        passed += 1
        results["phi_weights"] = "PASS (all weights = φ^index)"
    else:
        results["phi_weights"] = "FAIL"

    # Test 7: 6D centroids are within Poincaré ball
    total += 1
    in_ball = all(np.linalg.norm(p.centroid_6d) < 1.0 for p in registry)
    if in_ball:
        passed += 1
        results["centroids_in_ball"] = "PASS (all ||c|| < 1.0)"
    else:
        results["centroids_in_ball"] = "FAIL"

    return {
        "passed": passed,
        "total": total,
        "results": results,
        "rate": f"{passed}/{total} ({100 * passed / max(1, total):.0f}%)",
    }


if __name__ == "__main__":
    print("=" * 60)
    print("PHDM Polyhedra Registry — Self-Test")
    print("=" * 60)

    test_results = self_test()
    for name, result in test_results["results"].items():
        print(f"  {name}: {result}")
    print("-" * 60)
    print(f"  TOTAL: {test_results['rate']}")

    print("\n" + "=" * 60)
    print("Topology Report")
    print("=" * 60)
    report = topology_report()
    for zone_name, info in report["zones"].items():
        chis = info["chi_values"]
        print(f"  {zone_name:12s}: {info['count']} polyhedra, "
              f"χ={chis}, {info['stability']}")
    print(f"\n  Total: V={report['totals']['V']}, "
          f"E={report['totals']['E']}, F={report['totals']['F']}")
    print(f"  Sum(χ) = {report['chi_sum']}")
    print(f"  All valid: {report['all_valid']}")
