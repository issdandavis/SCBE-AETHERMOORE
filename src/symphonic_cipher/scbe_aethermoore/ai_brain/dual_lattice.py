"""
Dual Lattice Architecture - Python Reference

Both projection modes operate simultaneously:

  Static Lattice (6D -> 3D): Structure Generation
    Creates the aperiodic polyhedral mesh via cut-and-project.

  Dynamic Lattice (3D -> 6D -> 3D): Runtime Transform
    Lifts thought vectors through 6D, applies phason shifts,
    projects back with transformed aperiodic structure.

Key insight: Multiples of 2 and 1 -> 3 create interference patterns
at 3x frequencies, natural for icosahedral/phi-based symmetry.

@module ai_brain/dual_lattice
@layer Layer 4, Layer 5, Layer 9, Layer 12
@version 1.0.0
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .unified_state import PHI, BRAIN_EPSILON, POINCARE_MAX_NORM

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Lattice6D:
    """A point in the 6D hyperspace lattice."""
    components: Tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class Lattice3D:
    """A point in 3D projected space."""
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class PhasonShift:
    """A phason shift vector in 6D perpendicular space."""
    perp_shift: Tuple[float, float, float]
    magnitude: float
    phase: float


@dataclass
class StaticProjectionResult:
    """Result from static lattice projection (6D -> 3D)."""
    point_3d: Lattice3D
    perp_component: Tuple[float, float, float]
    accepted: bool
    boundary_distance: float
    tile_type: str  # 'thick' | 'thin'


@dataclass
class DynamicTransformResult:
    """Result from dynamic lattice transform (3D -> 6D -> 3D)."""
    lifted_6d: Lattice6D
    shifted_6d: Lattice6D
    projected_3d: Lattice3D
    displacement: float
    interference_value: float
    structure_preserved: bool


@dataclass
class DualLatticeResult:
    """Combined result from both lattice modes."""
    static: StaticProjectionResult
    dynamic: DynamicTransformResult
    coherence: float
    triple_frequency_interference: float
    validated: bool


@dataclass
class DualLatticeConfig:
    """Configuration for dual lattice system."""
    acceptance_radius: float = 1.0 / PHI
    phason_coupling: float = 0.1
    interference_threshold: float = 0.3
    max_phason_amplitude: float = 0.5
    coherence_threshold: float = 0.6


DEFAULT_DUAL_LATTICE_CONFIG = DualLatticeConfig()


# ---------------------------------------------------------------------------
# Icosahedral Projection Matrices (6x3)
# ---------------------------------------------------------------------------

def _build_parallel_projection() -> List[List[float]]:
    """Build the 6x3 physical projection matrix (E_parallel)."""
    angles = [2 * math.pi * k / 5 for k in range(5)]
    norm = math.sqrt(2.0 / 5)
    row_x = [norm * math.cos(a) for a in angles] + [0.0]
    row_y = [norm * math.sin(a) for a in angles] + [0.0]
    row_z = [norm / PHI] * 5 + [norm * PHI]
    return [row_x, row_y, row_z]


def _build_perp_projection() -> List[List[float]]:
    """Build the 6x3 perpendicular projection matrix (E_perp)."""
    angles = [4 * math.pi * k / 5 for k in range(5)]  # Doubled angles
    norm = math.sqrt(2.0 / 5)
    row_x = [norm * math.cos(a) for a in angles] + [0.0]
    row_y = [norm * math.sin(a) for a in angles] + [0.0]
    row_z = [norm * PHI] * 5 + [-norm / PHI]
    return [row_x, row_y, row_z]


E_PARALLEL = _build_parallel_projection()
E_PERP = _build_perp_projection()


# ---------------------------------------------------------------------------
# Projection Helpers
# ---------------------------------------------------------------------------

def _project_6d_to_3d(vec6: Tuple[float, ...], matrix: List[List[float]]) -> Lattice3D:
    """Project a 6D vector to 3D using projection matrix."""
    x = sum(matrix[0][j] * vec6[j] for j in range(6))
    y = sum(matrix[1][j] * vec6[j] for j in range(6))
    z = sum(matrix[2][j] * vec6[j] for j in range(6))
    return Lattice3D(x=x, y=y, z=z)


def _invert_3x3(m: List[List[float]]) -> List[List[float]]:
    """Invert a 3x3 matrix using Cramer's rule."""
    a, b, c = m[0][0], m[0][1], m[0][2]
    d, e, f = m[1][0], m[1][1], m[1][2]
    g, h, k = m[2][0], m[2][1], m[2][2]

    det = a * (e * k - f * h) - b * (d * k - f * g) + c * (d * h - e * g)
    if abs(det) < BRAIN_EPSILON:
        return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

    inv_det = 1.0 / det
    return [
        [(e * k - f * h) * inv_det, (c * h - b * k) * inv_det, (b * f - c * e) * inv_det],
        [(f * g - d * k) * inv_det, (a * k - c * g) * inv_det, (c * d - a * f) * inv_det],
        [(d * h - e * g) * inv_det, (b * g - a * h) * inv_det, (a * e - b * d) * inv_det],
    ]


def _lift_3d_to_6d(point: Lattice3D) -> Lattice6D:
    """Lift a 3D point to 6D using pseudoinverse of E_parallel."""
    x3 = [point.x, point.y, point.z]

    # E_par * E_par^T (3x3)
    eet = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k_idx in range(6):
                eet[i][j] += E_PARALLEL[i][k_idx] * E_PARALLEL[j][k_idx]

    inv = _invert_3x3(eet)

    # inv * x3
    temp = [0.0, 0.0, 0.0]
    for i in range(3):
        for j in range(3):
            temp[i] += inv[i][j] * x3[j]

    # E_par^T * temp
    result = [0.0] * 6
    for k_idx in range(6):
        for i in range(3):
            result[k_idx] += E_PARALLEL[i][k_idx] * temp[i]

    return Lattice6D(components=tuple(result))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Static Lattice (6D -> 3D)
# ---------------------------------------------------------------------------

def static_projection(
    point_6d: Lattice6D,
    config: Optional[DualLatticeConfig] = None,
) -> StaticProjectionResult:
    """Project from 6D to 3D using cut-and-project method."""
    config = config or DEFAULT_DUAL_LATTICE_CONFIG
    vec = point_6d.components

    point_3d = _project_6d_to_3d(vec, E_PARALLEL)
    perp = _project_6d_to_3d(vec, E_PERP)
    perp_component = (perp.x, perp.y, perp.z)

    perp_norm = math.sqrt(perp.x ** 2 + perp.y ** 2 + perp.z ** 2)
    accepted = perp_norm <= config.acceptance_radius
    boundary_distance = max(0.0, config.acceptance_radius - perp_norm)

    tile_type = "thick" if perp_norm < config.acceptance_radius / PHI else "thin"

    return StaticProjectionResult(
        point_3d=point_3d,
        perp_component=perp_component,
        accepted=accepted,
        boundary_distance=boundary_distance,
        tile_type=tile_type,
    )


def generate_aperiodic_mesh(
    radius: int = 3,
    config: Optional[DualLatticeConfig] = None,
) -> List[StaticProjectionResult]:
    """Generate aperiodic mesh by scanning 6D integer lattice."""
    config = config or DEFAULT_DUAL_LATTICE_CONFIG
    results: List[StaticProjectionResult] = []
    r = int(radius)

    for i in range(-r, r + 1):
        for j in range(-r, r + 1):
            for k in range(-r, r + 1):
                pt = Lattice6D(components=(float(i), float(j), float(k), 0.0, 0.0, 0.0))
                result = static_projection(pt, config)
                if result.accepted:
                    results.append(result)

    return results


# ---------------------------------------------------------------------------
# Dynamic Lattice (3D -> 6D -> 3D)
# ---------------------------------------------------------------------------

def apply_phason_shift(point_6d: Lattice6D, phason: PhasonShift) -> Lattice6D:
    """Apply a phason shift to a 6D lattice point."""
    vec = list(point_6d.components)
    shift = phason.perp_shift
    for k_idx in range(6):
        for i in range(3):
            vec[k_idx] += E_PERP[i][k_idx] * shift[i] * phason.magnitude
    return Lattice6D(components=tuple(vec))  # type: ignore[arg-type]


def _compute_triple_frequency_interference(
    original_6d: Lattice6D,
    shifted_6d: Lattice6D,
    anchor_3d: Lattice3D,
) -> float:
    """Compute 3x frequency interference pattern."""
    dot_prod = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for i in range(6):
        dot_prod += original_6d.components[i] * shifted_6d.components[i]
        norm_a += original_6d.components[i] ** 2
        norm_b += shifted_6d.components[i] ** 2

    norm_product = math.sqrt(norm_a * norm_b)
    if norm_product < BRAIN_EPSILON:
        return 0.0

    correlation = dot_prod / norm_product
    anchor_phase = anchor_3d.x * PHI + anchor_3d.y * PHI * PHI + anchor_3d.z / PHI
    return correlation * math.cos(3 * anchor_phase)


def dynamic_transform(
    point_3d: Lattice3D,
    phason: PhasonShift,
    config: Optional[DualLatticeConfig] = None,
) -> DynamicTransformResult:
    """Execute the full dynamic lattice transform: 3D -> 6D -> 3D."""
    config = config or DEFAULT_DUAL_LATTICE_CONFIG

    lifted_6d = _lift_3d_to_6d(point_3d)
    shifted_6d = apply_phason_shift(lifted_6d, phason)
    projected_3d = _project_6d_to_3d(shifted_6d.components, E_PARALLEL)

    dx = projected_3d.x - point_3d.x
    dy = projected_3d.y - point_3d.y
    dz = projected_3d.z - point_3d.z
    displacement = math.sqrt(dx * dx + dy * dy + dz * dz)

    interference_value = _compute_triple_frequency_interference(
        lifted_6d, shifted_6d, point_3d
    )
    structure_preserved = phason.magnitude <= config.max_phason_amplitude

    return DynamicTransformResult(
        lifted_6d=lifted_6d,
        shifted_6d=shifted_6d,
        projected_3d=projected_3d,
        displacement=displacement,
        interference_value=interference_value,
        structure_preserved=structure_preserved,
    )


# ---------------------------------------------------------------------------
# Fractal Dimension (Box-counting)
# ---------------------------------------------------------------------------

def estimate_fractal_dimension(
    points: List[Lattice3D],
    scales: Optional[List[float]] = None,
) -> float:
    """Estimate Hausdorff dimension via box-counting."""
    if len(points) < 2:
        return 0.0

    scales = scales or [1.0, 0.5, 0.25, 0.125]
    log_n: List[float] = []
    log_inv_eps: List[float] = []

    for eps in scales:
        boxes = set()
        for p in points:
            bx = int(math.floor(p.x / eps))
            by = int(math.floor(p.y / eps))
            bz = int(math.floor(p.z / eps))
            boxes.add((bx, by, bz))
        if boxes:
            log_n.append(math.log(len(boxes)))
            log_inv_eps.append(math.log(1.0 / eps))

    if len(log_n) < 2:
        return 0.0

    # Linear regression
    n = len(log_n)
    sum_x = sum(log_inv_eps)
    sum_y = sum(log_n)
    sum_xy = sum(log_inv_eps[i] * log_n[i] for i in range(n))
    sum_x2 = sum(v * v for v in log_inv_eps)

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < BRAIN_EPSILON:
        return 0.0

    return (n * sum_xy - sum_x * sum_y) / denom


def lattice_norm_6d(point: Lattice6D) -> float:
    """Compute L2 norm of a 6D lattice vector."""
    return math.sqrt(sum(c * c for c in point.components))


def lattice_distance_3d(a: Lattice3D, b: Lattice3D) -> float:
    """Compute Euclidean distance between two 3D points."""
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


# ---------------------------------------------------------------------------
# Dual Lattice System
# ---------------------------------------------------------------------------

class DualLatticeSystem:
    """Dual Lattice System - both projection modes operating simultaneously."""

    def __init__(self, config: Optional[DualLatticeConfig] = None):
        self.config = config or DualLatticeConfig()
        self._static_mesh: Optional[List[StaticProjectionResult]] = None
        self._step_counter = 0

    def initialize_mesh(self, radius: int = 3) -> List[StaticProjectionResult]:
        """Initialize the static mesh (one-time topology generation)."""
        self._static_mesh = generate_aperiodic_mesh(radius, self.config)
        return self._static_mesh

    @property
    def mesh(self) -> Optional[List[StaticProjectionResult]]:
        return self._static_mesh

    def process(self, state_21d: List[float], phason: PhasonShift) -> DualLatticeResult:
        """Process a 21D brain state through the dual lattice system."""
        self._step_counter += 1

        if len(state_21d) < 6:
            raise ValueError(f"Expected at least 6D state, got {len(state_21d)}D")

        # Extract 6D subspace (navigation dimensions 6-11 or fallback to 0-5)
        nav = []
        for idx in range(6):
            real_idx = idx + 6 if len(state_21d) > idx + 6 else idx
            nav.append(state_21d[real_idx])
        nav_6d = Lattice6D(components=tuple(nav))  # type: ignore[arg-type]

        static_result = static_projection(nav_6d, self.config)
        dynamic_result = dynamic_transform(static_result.point_3d, phason, self.config)

        coherence = self._compute_coherence(static_result, dynamic_result)
        triple_freq = dynamic_result.interference_value

        validated = (
            static_result.accepted
            and dynamic_result.structure_preserved
            and coherence >= self.config.coherence_threshold
        )

        return DualLatticeResult(
            static=static_result,
            dynamic=dynamic_result,
            coherence=coherence,
            triple_frequency_interference=triple_freq,
            validated=validated,
        )

    def create_threat_phason(
        self, threat_level: float, anomaly_dimensions: Optional[List[int]] = None
    ) -> PhasonShift:
        """Create a security-responsive phason shift based on threat level."""
        clamped = max(0.0, min(1.0, threat_level))
        magnitude = clamped * self.config.max_phason_amplitude * self.config.phason_coupling

        px, py, pz = 0.0, 0.0, 0.0
        if anomaly_dimensions:
            for dim in anomaly_dimensions:
                angle = 2 * math.pi * dim / 21
                px += math.cos(angle)
                py += math.sin(angle)
                pz += math.cos(angle * PHI)
            norm = math.sqrt(px * px + py * py + pz * pz)
            if norm > BRAIN_EPSILON:
                px /= norm
                py /= norm
                pz /= norm
        else:
            angle = self._step_counter * 2 * math.pi / PHI
            px = math.cos(angle)
            py = math.sin(angle)
            pz = math.cos(angle / PHI)

        return PhasonShift(
            perp_shift=(px, py, pz),
            magnitude=magnitude,
            phase=math.atan2(py, px),
        )

    def _compute_coherence(
        self,
        static_result: StaticProjectionResult,
        dynamic_result: DynamicTransformResult,
    ) -> float:
        """Cross-verification coherence between static and dynamic results."""
        displacement_score = 1.0 / (1.0 + dynamic_result.displacement * 5)
        structure_score = 1.0 if dynamic_result.structure_preserved else 0.0
        acceptance_score = 1.0 if static_result.accepted else 0.3
        interference_score = 1.0 - abs(dynamic_result.interference_value) * 0.5

        return (
            displacement_score * 0.35
            + structure_score * 0.25
            + acceptance_score * 0.25
            + interference_score * 0.15
        )

    @property
    def step(self) -> int:
        return self._step_counter

    def reset(self) -> None:
        self._step_counter = 0

    def full_reset(self) -> None:
        self._step_counter = 0
        self._static_mesh = None
