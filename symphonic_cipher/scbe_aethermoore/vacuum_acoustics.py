"""
Vacuum-Acoustics Kernel
=======================
Models wave propagation in near-vacuum environments using harmonic scaling.

Core equations:
- Nodal Surface: N(x; n, m) = cos(nπx₁/L)cos(mπx₂/L) - cos(mπx₁/L)cos(nπx₂/L) = 0
- Bottle Beam: I(r) = I₀ · |Σₖ exp(i·k·r + φₖ)|²
- Flux Redistribution: E_corner = E_total / 4 after wave cancellation

Document ID: AETHER-SPEC-2026-001
Section: 5 (Vacuum-Acoustics Kernel)
"""

from __future__ import annotations

import math
import cmath
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, NamedTuple

from .constants import (
    PI, R_FIFTH, PHI, C_LIGHT,
    DEFAULT_L, DEFAULT_TOLERANCE, DEFAULT_R,
    harmonic_scale, harmonic_distance,
    CONSTANTS
)


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

Vector2D = Tuple[float, float]
Vector3D = Tuple[float, float, float]
Vector6D = Tuple[float, float, float, float, float, float]


class WaveSource(NamedTuple):
    """A point wave source."""
    position: Vector3D
    phase: float        # In radians
    amplitude: float = 1.0


@dataclass
class VacuumAcousticsConfig:
    """
    Vacuum-Acoustics kernel configuration.

    Attributes:
        L: Characteristic length (meters)
        c: Wave speed (m/s, default speed of light)
        gamma: Harmonic coupling constant
        R: Harmonic ratio (default 1.5)
        resolution: Grid resolution for field computations
        v_reference: Reference velocity for mode mapping
    """
    L: float = DEFAULT_L
    c: float = C_LIGHT
    gamma: float = 1.0
    R: float = R_FIFTH
    resolution: int = 100
    v_reference: float = 1.0  # Reference velocity for mode extraction


@dataclass
class FluxResult:
    """Result of flux redistribution computation."""
    canceled_energy: float              # Energy at cancellation point
    corner_energies: Tuple[float, float, float, float]  # 4 corners
    total_energy: float
    phase_offset: float


@dataclass
class BottleBeamResult:
    """Result of bottle beam computation."""
    core_intensity: float       # Intensity at center
    wall_intensity: float       # Maximum wall intensity
    trapping_depth: float       # ΔI = wall - core
    core_radius: float          # Calculated core radius
    is_valid_trap: bool         # True if trapping condition satisfied


# =============================================================================
# NODAL SURFACE EQUATIONS
# =============================================================================

def nodal_surface(
    x: Vector2D,
    n: float,
    m: float,
    L: float = DEFAULT_L
) -> float:
    """
    Compute nodal surface value at position.

    Definition 5.4.1 (Nodal Surface Equation):
        N(x; n, m) = cos(nπx₁/L)cos(mπx₂/L) - cos(mπx₁/L)cos(nπx₂/L)

    A point lies on a nodal line when N = 0.

    Args:
        x: Position (x₁, x₂) in resonant plane
        n: First mode parameter
        m: Second mode parameter
        L: Characteristic length

    Returns:
        Nodal value (0 = on nodal line)

    Example:
        >>> nodal_surface((0, 0), 1, 1, 1.0)
        0.0
        >>> nodal_surface((0.5, 0.5), 1, 1, 1.0)
        0.0
    """
    x1, x2 = x

    # Clamp mode parameters to prevent issues
    n = max(0.01, min(100, n))
    m = max(0.01, min(100, m))
    L = max(1, min(1e6, L))

    term1 = math.cos(n * PI * x1 / L) * math.cos(m * PI * x2 / L)
    term2 = math.cos(m * PI * x1 / L) * math.cos(n * PI * x2 / L)

    return term1 - term2


def is_on_nodal_line(
    x: Vector2D,
    n: float,
    m: float,
    L: float = DEFAULT_L,
    tolerance: float = DEFAULT_TOLERANCE
) -> bool:
    """
    Check if position is on a nodal line.

    Args:
        x: Position in resonant plane
        n: First mode parameter
        m: Second mode parameter
        L: Characteristic length
        tolerance: How close to zero counts as "on" the line

    Returns:
        True if position is on nodal line
    """
    return abs(nodal_surface(x, n, m, L)) < tolerance


def find_nodal_points(
    n: float,
    m: float,
    L: float = DEFAULT_L,
    resolution: int = 100
) -> List[Vector2D]:
    """
    Find all nodal intersection points in a grid.

    Args:
        n: First mode parameter
        m: Second mode parameter
        L: Characteristic length
        resolution: Grid resolution

    Returns:
        List of (x1, x2) points on nodal lines
    """
    points = []
    tolerance = L / resolution / 2

    for i in range(resolution + 1):
        for j in range(resolution + 1):
            x1 = i * L / resolution
            x2 = j * L / resolution
            if is_on_nodal_line((x1, x2), n, m, L, tolerance):
                points.append((x1, x2))

    return points


def compute_chladni_pattern(
    n: float,
    m: float,
    L: float = DEFAULT_L,
    resolution: int = 100
) -> List[List[float]]:
    """
    Compute full Chladni pattern (nodal surface values over grid).

    Args:
        n: First mode parameter
        m: Second mode parameter
        L: Characteristic length
        resolution: Grid resolution

    Returns:
        2D grid of nodal values
    """
    pattern = []
    for i in range(resolution):
        row = []
        for j in range(resolution):
            x1 = i * L / resolution
            x2 = j * L / resolution
            row.append(nodal_surface((x1, x2), n, m, L))
        pattern.append(row)
    return pattern


# =============================================================================
# CYMATIC RESONANCE
# =============================================================================

def extract_mode_parameters(
    agent_vector: Vector6D,
    config: Optional[VacuumAcousticsConfig] = None
) -> Tuple[float, float]:
    """
    Extract Chladni mode parameters (n, m) from agent's 6D state vector.

    Mode mapping from 6D vector v = (x, y, z, vel, pri, sec):
        n = |vel| / v_reference  (velocity → frequency mode)
        m = sec                   (security dimension → mode)

    Args:
        agent_vector: 6D state vector (x, y, z, velocity, priority, security)
        config: Vacuum acoustics configuration

    Returns:
        Tuple (n, m) of mode parameters
    """
    if config is None:
        config = VacuumAcousticsConfig()

    _, _, _, velocity, _, security = agent_vector

    # Mode n from velocity
    n = abs(velocity) / config.v_reference
    n = max(0.01, min(100, n))  # Clamp to valid range

    # Mode m from security dimension
    m = max(0.01, min(100, security))

    return (n, m)


def check_cymatic_resonance(
    agent_vector: Vector6D,
    target_position: Vector2D,
    tolerance: float = DEFAULT_TOLERANCE,
    config: Optional[VacuumAcousticsConfig] = None
) -> bool:
    """
    Determine if a 6D vector produces cymatic resonance at position.

    Algorithm 6.3.1 (Voxel Retrieval):
        1. Extract mode parameters n, m from agent vector
        2. Compute nodal value N at target position
        3. Return True if |N| < tolerance

    Args:
        agent_vector: 6D agent state vector
        target_position: Target position (x, y) in storage plane
        tolerance: Resonance tolerance (default 0.01)
        config: Vacuum acoustics configuration

    Returns:
        True if resonance condition satisfied (data accessible)

    Example:
        >>> agent = (0, 0, 0, 1.0, 0.5, 1.0)  # velocity=1, security=1
        >>> check_cymatic_resonance(agent, (0, 0))
        True  # Origin is always on nodal line for equal modes
    """
    if config is None:
        config = VacuumAcousticsConfig()

    n, m = extract_mode_parameters(agent_vector, config)

    return is_on_nodal_line(target_position, n, m, config.L, tolerance)


def resonance_strength(
    agent_vector: Vector6D,
    target_position: Vector2D,
    config: Optional[VacuumAcousticsConfig] = None
) -> float:
    """
    Compute resonance strength (inverse of nodal distance).

    Higher values indicate stronger resonance (closer to nodal line).

    Args:
        agent_vector: 6D agent state vector
        target_position: Target position in storage plane
        config: Vacuum acoustics configuration

    Returns:
        Resonance strength (0 to 1, where 1 = perfect resonance)
    """
    if config is None:
        config = VacuumAcousticsConfig()

    n, m = extract_mode_parameters(agent_vector, config)
    nodal_value = abs(nodal_surface(target_position, n, m, config.L))

    # Convert to strength: closer to 0 = higher strength
    # Use exponential decay
    return math.exp(-nodal_value * 10)


# =============================================================================
# BOTTLE BEAM TRAPPING
# =============================================================================

def bottle_beam_intensity(
    position: Vector3D,
    sources: List[WaveSource],
    wavelength: float,
    config: Optional[VacuumAcousticsConfig] = None
) -> float:
    """
    Compute bottle beam field intensity at position.

    Definition 5.5.1 (Acoustic Bottle Beam):
        I(r) = I₀ · |Σₖ exp(i·k·r + φₖ)|²

    Args:
        position: 3D position vector
        sources: Array of source positions and phases
        wavelength: Operating wavelength
        config: Vacuum acoustics configuration

    Returns:
        Field intensity at position
    """
    if not sources:
        return 0.0

    # Wave number
    k = 2 * PI / wavelength

    # Sum complex amplitudes from all sources
    total_amplitude = complex(0, 0)

    for source in sources:
        # Distance from source to position
        dx = position[0] - source.position[0]
        dy = position[1] - source.position[1]
        dz = position[2] - source.position[2]
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)

        # Avoid division by zero
        if distance < wavelength / 1000:
            distance = wavelength / 1000

        # Phase contribution: k·r + φ
        phase = k * distance + source.phase

        # Amplitude with 1/r falloff
        amplitude = source.amplitude / distance

        # Add to total (complex exponential)
        total_amplitude += amplitude * cmath.exp(1j * phase)

    # Intensity is |amplitude|²
    return abs(total_amplitude) ** 2


def create_bottle_beam_sources(
    center: Vector3D,
    radius: float,
    n_sources: int = 8,
    wavelength: float = 1.0
) -> List[WaveSource]:
    """
    Create source array for bottle beam trap.

    Sources arranged in a ring with phases set for constructive
    interference at the wall and destructive at the center.

    Args:
        center: Center of bottle beam
        radius: Radius of source ring
        n_sources: Number of sources
        wavelength: Operating wavelength

    Returns:
        List of WaveSource objects
    """
    sources = []

    for i in range(n_sources):
        angle = 2 * PI * i / n_sources

        # Position on ring
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        z = center[2]

        # Phase set for bottle effect
        # Alternate phase by π/2 between adjacent sources
        phase = (PI / 2) * i

        sources.append(WaveSource(
            position=(x, y, z),
            phase=phase,
            amplitude=1.0
        ))

    return sources


def analyze_bottle_beam(
    sources: List[WaveSource],
    wavelength: float,
    center: Vector3D,
    d: int = 3,
    R: float = R_FIFTH
) -> BottleBeamResult:
    """
    Analyze bottle beam trap properties.

    Bottle parameters (from spec):
        - Wall thickness: λ/4 (quarter wavelength)
        - Core radius: R_core = λ · H(d,R)^(-1/3)
        - Trapping depth: ΔI = I_wall - I_core

    Args:
        sources: Source array
        wavelength: Operating wavelength
        center: Bottle center
        d: Dimension count for harmonic scaling
        R: Harmonic ratio

    Returns:
        BottleBeamResult with trap analysis
    """
    # Calculate expected core radius using harmonic scaling
    H = harmonic_scale(d, R)
    core_radius = wavelength * (H ** (-1/3))

    # Sample intensities
    core_intensity = bottle_beam_intensity(center, sources, wavelength)

    # Sample wall intensity (at core_radius distance)
    wall_pos = (center[0] + core_radius, center[1], center[2])
    wall_intensity = bottle_beam_intensity(wall_pos, sources, wavelength)

    # Trapping depth
    trapping_depth = wall_intensity - core_intensity

    # Valid trap if wall intensity > core intensity
    is_valid = trapping_depth > 0 and wall_intensity > core_intensity * 1.5

    return BottleBeamResult(
        core_intensity=core_intensity,
        wall_intensity=wall_intensity,
        trapping_depth=trapping_depth,
        core_radius=core_radius,
        is_valid_trap=is_valid
    )


# =============================================================================
# FLUX REDISTRIBUTION
# =============================================================================

def flux_redistribution(
    primary_amplitude: float,
    phase_offset: float = PI
) -> FluxResult:
    """
    Compute flux redistribution after wave cancellation.

    Definition 5.6.1 (Flux Cancellation):
        Primary wave: W₁ = A · exp(i·ω·t)
        Inverse wave: W₂ = A · exp(i·ω·t + π) = -W₁
        Superposition: W_total = W₁ + W₂ = 0 (destructive)

    Energy conservation:
        E_total = E₁ + E₂ = 2A² (energy doesn't disappear)
        Redistribution to 4× nodal corners:
        E_corner = E_total / 4 = A²/2 each

    Args:
        primary_amplitude: Amplitude of primary wave (A)
        phase_offset: Phase difference (π for full cancellation)

    Returns:
        FluxResult with energy distribution

    Example:
        >>> result = flux_redistribution(1.0, math.pi)
        >>> result.canceled_energy
        0.0
        >>> sum(result.corner_energies)  # Total redistributed
        2.0
    """
    A = primary_amplitude

    # Energy in each wave
    E_primary = A ** 2
    E_inverse = A ** 2
    E_total = E_primary + E_inverse

    # Superposition amplitude
    # W_total = A·exp(iωt) + A·exp(i(ωt + φ))
    #         = A·exp(iωt)·(1 + exp(iφ))
    interference_factor = abs(1 + cmath.exp(1j * phase_offset))
    superposition_amplitude = A * interference_factor

    # Energy at cancellation point
    canceled_energy = superposition_amplitude ** 2

    # Energy redistributed to corners
    redistributed = E_total - canceled_energy
    E_corner = redistributed / 4

    return FluxResult(
        canceled_energy=canceled_energy,
        corner_energies=(E_corner, E_corner, E_corner, E_corner),
        total_energy=E_total,
        phase_offset=phase_offset
    )


def compute_interference_pattern(
    amplitude: float,
    phases: List[float],
    positions: List[Vector2D],
    wavelength: float,
    grid_size: int = 50,
    grid_extent: float = 10.0
) -> List[List[float]]:
    """
    Compute 2D interference pattern from multiple point sources.

    Args:
        amplitude: Wave amplitude
        phases: Initial phases for each source
        positions: Source positions
        wavelength: Operating wavelength
        grid_size: Resolution of output grid
        grid_extent: Physical extent of grid

    Returns:
        2D intensity grid
    """
    k = 2 * PI / wavelength
    pattern = []

    for i in range(grid_size):
        row = []
        for j in range(grid_size):
            # Grid position
            x = (i - grid_size/2) * grid_extent / grid_size
            y = (j - grid_size/2) * grid_extent / grid_size

            # Sum contributions from all sources
            total = complex(0, 0)
            for pos, phase in zip(positions, phases):
                dx = x - pos[0]
                dy = y - pos[1]
                r = math.sqrt(dx*dx + dy*dy)
                if r < wavelength / 100:
                    r = wavelength / 100
                total += (amplitude / r) * cmath.exp(1j * (k * r + phase))

            row.append(abs(total) ** 2)
        pattern.append(row)

    return pattern


# =============================================================================
# HARMONIC PRESSURE FIELD
# =============================================================================

def harmonic_pressure_field(
    position: Vector3D,
    t: float,
    d: int,
    config: Optional[VacuumAcousticsConfig] = None
) -> float:
    """
    Compute harmonic pressure field value.

    Definition 5.3.1 (Harmonic Pressure Field):
        ∂²Ψ/∂t² = c² ∇²Ψ + γ · H(d, R) · Ψ

    This is a simplified steady-state evaluation.

    Args:
        position: 3D position
        t: Time
        d: Dimensional complexity
        config: Vacuum acoustics configuration

    Returns:
        Field amplitude at position and time
    """
    if config is None:
        config = VacuumAcousticsConfig()

    x, y, z = position
    c = config.c
    gamma = config.gamma
    R = config.R
    L = config.L

    # Harmonic scaling factor
    H = harmonic_scale(d, R)

    # Simplified standing wave solution
    # Ψ = cos(kx)cos(ky)cos(kz)cos(ωt) with harmonic modulation
    k = PI / L
    omega = c * k * math.sqrt(1 + gamma * H)

    spatial = math.cos(k * x) * math.cos(k * y) * math.cos(k * z)
    temporal = math.cos(omega * t)

    return spatial * temporal


# =============================================================================
# UTILITIES
# =============================================================================

def visualize_chladni_pattern(
    n: float,
    m: float,
    L: float = DEFAULT_L,
    resolution: int = 40
) -> str:
    """
    Create ASCII visualization of Chladni pattern.

    Args:
        n: First mode parameter
        m: Second mode parameter
        L: Characteristic length
        resolution: Display resolution

    Returns:
        ASCII art string
    """
    pattern = compute_chladni_pattern(n, m, L, resolution)

    # Find range
    flat = [v for row in pattern for v in row]
    min_val = min(flat)
    max_val = max(flat)

    # ASCII gradient (dark = nodal line)
    gradient = "█▓▒░ ░▒▓█"
    mid = len(gradient) // 2

    lines = [f"Chladni Pattern (n={n:.1f}, m={m:.1f})"]
    lines.append("┌" + "─" * resolution + "┐")

    for row in pattern:
        line = "│"
        for val in row:
            if max_val == min_val:
                idx = mid
            else:
                # Map value to gradient index
                normalized = (val - min_val) / (max_val - min_val)
                idx = int(normalized * (len(gradient) - 1))
            line += gradient[idx]
        line += "│"
        lines.append(line)

    lines.append("└" + "─" * resolution + "┘")

    return "\n".join(lines)


def get_vacuum_acoustics_stats(config: Optional[VacuumAcousticsConfig] = None) -> Dict[str, Any]:
    """Get vacuum acoustics module statistics."""
    if config is None:
        config = VacuumAcousticsConfig()

    return {
        'config': {
            'L': config.L,
            'c': config.c,
            'gamma': config.gamma,
            'R': config.R,
            'resolution': config.resolution,
            'v_reference': config.v_reference,
        },
        'harmonic_scales': {
            f'd={d}': harmonic_scale(d, config.R)
            for d in range(1, 7)
        },
        'constants': {
            'PI': PI,
            'PHI': PHI,
            'C_LIGHT': C_LIGHT,
            'R_FIFTH': R_FIFTH,
        }
    }
