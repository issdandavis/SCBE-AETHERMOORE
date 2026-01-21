#!/usr/bin/env python3
"""
Orbital Mechanics Module

Comprehensive orbital mechanics calculations covering:
- Kepler's laws and orbital elements
- Two-body problem solutions
- Orbital maneuvers (Hohmann, bi-elliptic)
- Interplanetary trajectories
- Perturbations and precession
- Lagrange points

Based on established celestial mechanics.
"""

import math
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass
import numpy as np


# =============================================================================
# GRAVITATIONAL CONSTANTS
# =============================================================================

G = 6.67430e-11  # Gravitational constant (m³/(kg·s²))

# Standard gravitational parameters (μ = GM) in m³/s²
MU_SUN = 1.32712440018e20
MU_EARTH = 3.986004418e14
MU_MOON = 4.9048695e12
MU_MARS = 4.282837e13
MU_JUPITER = 1.26686534e17
MU_VENUS = 3.24859e14
MU_SATURN = 3.7931187e16

# Planetary radii (m)
RADIUS_EARTH = 6.371e6
RADIUS_MOON = 1.737e6
RADIUS_MARS = 3.3895e6
RADIUS_SUN = 6.96e8

# Astronomical unit
AU = 1.495978707e11  # m

# Earth's J2 perturbation coefficient
J2_EARTH = 1.08263e-3


# =============================================================================
# ORBITAL ELEMENTS
# =============================================================================

@dataclass
class OrbitalElements:
    """Classical Keplerian orbital elements."""
    a: float        # Semi-major axis (m)
    e: float        # Eccentricity
    i: float        # Inclination (rad)
    omega: float    # Argument of periapsis (rad)
    Omega: float    # Longitude of ascending node (rad)
    nu: float       # True anomaly (rad)

    @property
    def period(self) -> float:
        """Orbital period (s) - requires mu to be set externally."""
        raise NotImplementedError("Use orbital_period() function")

    def to_dict(self) -> Dict[str, float]:
        return {
            'semi_major_axis_m': self.a,
            'eccentricity': self.e,
            'inclination_rad': self.i,
            'inclination_deg': math.degrees(self.i),
            'argument_of_periapsis_rad': self.omega,
            'argument_of_periapsis_deg': math.degrees(self.omega),
            'longitude_ascending_node_rad': self.Omega,
            'longitude_ascending_node_deg': math.degrees(self.Omega),
            'true_anomaly_rad': self.nu,
            'true_anomaly_deg': math.degrees(self.nu),
        }


# =============================================================================
# BASIC ORBITAL MECHANICS
# =============================================================================

def orbital_period(a: float, mu: float) -> float:
    """
    Calculate orbital period (Kepler's 3rd law).

    T = 2π√(a³/μ)

    Args:
        a: Semi-major axis (m)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Orbital period (s)
    """
    return 2 * math.pi * math.sqrt(a ** 3 / mu)


def orbital_velocity(r: float, a: float, mu: float) -> float:
    """
    Calculate orbital velocity (vis-viva equation).

    v = √(μ(2/r - 1/a))

    Args:
        r: Current radius (m)
        a: Semi-major axis (m)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Orbital velocity (m/s)
    """
    return math.sqrt(mu * (2 / r - 1 / a))


def circular_velocity(r: float, mu: float) -> float:
    """
    Calculate circular orbital velocity.

    v_c = √(μ/r)

    Args:
        r: Orbital radius (m)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Circular velocity (m/s)
    """
    return math.sqrt(mu / r)


def escape_velocity(r: float, mu: float) -> float:
    """
    Calculate escape velocity.

    v_esc = √(2μ/r) = √2 * v_c

    Args:
        r: Distance from center (m)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Escape velocity (m/s)
    """
    return math.sqrt(2 * mu / r)


def specific_orbital_energy(r: float, v: float, mu: float) -> float:
    """
    Calculate specific orbital energy.

    ε = v²/2 - μ/r = -μ/(2a)

    Args:
        r: Current radius (m)
        v: Current velocity (m/s)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Specific orbital energy (J/kg)
    """
    return v ** 2 / 2 - mu / r


def semi_major_axis_from_energy(epsilon: float, mu: float) -> float:
    """
    Calculate semi-major axis from specific orbital energy.

    a = -μ/(2ε)

    Args:
        epsilon: Specific orbital energy (J/kg)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Semi-major axis (m)
    """
    if epsilon >= 0:
        return float('inf')  # Hyperbolic or parabolic
    return -mu / (2 * epsilon)


def specific_angular_momentum(r: float, v: float, gamma: float = 0) -> float:
    """
    Calculate specific angular momentum.

    h = r * v * cos(γ)

    Args:
        r: Current radius (m)
        v: Current velocity (m/s)
        gamma: Flight path angle (rad), 0 for circular

    Returns:
        Specific angular momentum (m²/s)
    """
    return r * v * math.cos(gamma)


def eccentricity_from_apse(r_a: float, r_p: float) -> float:
    """
    Calculate eccentricity from apoapsis and periapsis.

    e = (r_a - r_p) / (r_a + r_p)

    Args:
        r_a: Apoapsis radius (m)
        r_p: Periapsis radius (m)

    Returns:
        Eccentricity
    """
    return (r_a - r_p) / (r_a + r_p)


def periapsis_radius(a: float, e: float) -> float:
    """
    Calculate periapsis radius.

    r_p = a(1 - e)

    Args:
        a: Semi-major axis (m)
        e: Eccentricity

    Returns:
        Periapsis radius (m)
    """
    return a * (1 - e)


def apoapsis_radius(a: float, e: float) -> float:
    """
    Calculate apoapsis radius.

    r_a = a(1 + e)

    Args:
        a: Semi-major axis (m)
        e: Eccentricity

    Returns:
        Apoapsis radius (m)
    """
    return a * (1 + e)


def radius_at_true_anomaly(a: float, e: float, nu: float) -> float:
    """
    Calculate orbital radius at given true anomaly.

    r = a(1 - e²) / (1 + e*cos(ν))

    Args:
        a: Semi-major axis (m)
        e: Eccentricity
        nu: True anomaly (rad)

    Returns:
        Radius (m)
    """
    return a * (1 - e ** 2) / (1 + e * math.cos(nu))


def velocity_at_true_anomaly(a: float, e: float, nu: float, mu: float) -> float:
    """
    Calculate velocity at given true anomaly.

    Args:
        a: Semi-major axis (m)
        e: Eccentricity
        nu: True anomaly (rad)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Velocity (m/s)
    """
    r = radius_at_true_anomaly(a, e, nu)
    return orbital_velocity(r, a, mu)


def flight_path_angle(e: float, nu: float) -> float:
    """
    Calculate flight path angle.

    γ = atan(e*sin(ν) / (1 + e*cos(ν)))

    Args:
        e: Eccentricity
        nu: True anomaly (rad)

    Returns:
        Flight path angle (rad)
    """
    return math.atan2(e * math.sin(nu), 1 + e * math.cos(nu))


# =============================================================================
# ANOMALY CONVERSIONS
# =============================================================================

def true_to_eccentric_anomaly(nu: float, e: float) -> float:
    """
    Convert true anomaly to eccentric anomaly.

    tan(E/2) = √((1-e)/(1+e)) * tan(ν/2)

    Args:
        nu: True anomaly (rad)
        e: Eccentricity

    Returns:
        Eccentric anomaly (rad)
    """
    return 2 * math.atan(math.sqrt((1 - e) / (1 + e)) * math.tan(nu / 2))


def eccentric_to_true_anomaly(E: float, e: float) -> float:
    """
    Convert eccentric anomaly to true anomaly.

    tan(ν/2) = √((1+e)/(1-e)) * tan(E/2)

    Args:
        E: Eccentric anomaly (rad)
        e: Eccentricity

    Returns:
        True anomaly (rad)
    """
    return 2 * math.atan(math.sqrt((1 + e) / (1 - e)) * math.tan(E / 2))


def mean_to_eccentric_anomaly(M: float, e: float, tol: float = 1e-12) -> float:
    """
    Convert mean anomaly to eccentric anomaly (Kepler's equation).

    M = E - e*sin(E) (solve for E)

    Uses Newton-Raphson iteration.

    Args:
        M: Mean anomaly (rad)
        e: Eccentricity
        tol: Convergence tolerance

    Returns:
        Eccentric anomaly (rad)
    """
    # Initial guess
    if e < 0.8:
        E = M
    else:
        E = math.pi

    # Newton-Raphson iteration
    for _ in range(50):
        f = E - e * math.sin(E) - M
        f_prime = 1 - e * math.cos(E)
        E_new = E - f / f_prime

        if abs(E_new - E) < tol:
            return E_new
        E = E_new

    return E


def mean_anomaly(E: float, e: float) -> float:
    """
    Calculate mean anomaly from eccentric anomaly.

    M = E - e*sin(E)

    Args:
        E: Eccentric anomaly (rad)
        e: Eccentricity

    Returns:
        Mean anomaly (rad)
    """
    return E - e * math.sin(E)


def time_of_flight(nu1: float, nu2: float, a: float, e: float, mu: float) -> float:
    """
    Calculate time of flight between two true anomalies.

    Args:
        nu1: Initial true anomaly (rad)
        nu2: Final true anomaly (rad)
        a: Semi-major axis (m)
        e: Eccentricity
        mu: Gravitational parameter (m³/s²)

    Returns:
        Time of flight (s)
    """
    E1 = true_to_eccentric_anomaly(nu1, e)
    E2 = true_to_eccentric_anomaly(nu2, e)

    M1 = mean_anomaly(E1, e)
    M2 = mean_anomaly(E2, e)

    n = math.sqrt(mu / a ** 3)  # Mean motion

    return (M2 - M1) / n


# =============================================================================
# ORBITAL MANEUVERS
# =============================================================================

def hohmann_transfer(r1: float, r2: float, mu: float) -> Dict[str, float]:
    """
    Calculate Hohmann transfer orbit parameters.

    Two-impulse transfer between circular orbits.

    Args:
        r1: Initial orbit radius (m)
        r2: Final orbit radius (m)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Dictionary with transfer parameters
    """
    # Transfer ellipse semi-major axis
    a_transfer = (r1 + r2) / 2

    # Velocities in circular orbits
    v1_circular = circular_velocity(r1, mu)
    v2_circular = circular_velocity(r2, mu)

    # Velocities in transfer orbit
    v1_transfer = orbital_velocity(r1, a_transfer, mu)
    v2_transfer = orbital_velocity(r2, a_transfer, mu)

    # Delta-v
    delta_v1 = abs(v1_transfer - v1_circular)
    delta_v2 = abs(v2_circular - v2_transfer)
    delta_v_total = delta_v1 + delta_v2

    # Transfer time
    T_transfer = orbital_period(a_transfer, mu) / 2

    return {
        'transfer_semi_major_axis_m': a_transfer,
        'delta_v1_m_s': delta_v1,
        'delta_v2_m_s': delta_v2,
        'delta_v_total_m_s': delta_v_total,
        'transfer_time_s': T_transfer,
        'transfer_time_days': T_transfer / 86400,
        'v1_circular_m_s': v1_circular,
        'v2_circular_m_s': v2_circular,
        'v1_transfer_m_s': v1_transfer,
        'v2_transfer_m_s': v2_transfer,
    }


def bi_elliptic_transfer(r1: float, r2: float, r_b: float,
                        mu: float) -> Dict[str, float]:
    """
    Calculate bi-elliptic transfer parameters.

    Three-impulse transfer via intermediate apoapsis.
    Can be more efficient than Hohmann for r2/r1 > 11.94.

    Args:
        r1: Initial orbit radius (m)
        r2: Final orbit radius (m)
        r_b: Intermediate apoapsis radius (m)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Dictionary with transfer parameters
    """
    # First transfer ellipse
    a1 = (r1 + r_b) / 2
    v1_circular = circular_velocity(r1, mu)
    v1_transfer = orbital_velocity(r1, a1, mu)
    delta_v1 = abs(v1_transfer - v1_circular)

    # Second transfer ellipse
    a2 = (r_b + r2) / 2
    v_b_first = orbital_velocity(r_b, a1, mu)
    v_b_second = orbital_velocity(r_b, a2, mu)
    delta_v2 = abs(v_b_second - v_b_first)

    # Final circularization
    v2_transfer = orbital_velocity(r2, a2, mu)
    v2_circular = circular_velocity(r2, mu)
    delta_v3 = abs(v2_circular - v2_transfer)

    # Total
    delta_v_total = delta_v1 + delta_v2 + delta_v3

    # Transfer time
    T1 = orbital_period(a1, mu) / 2
    T2 = orbital_period(a2, mu) / 2
    T_total = T1 + T2

    return {
        'delta_v1_m_s': delta_v1,
        'delta_v2_m_s': delta_v2,
        'delta_v3_m_s': delta_v3,
        'delta_v_total_m_s': delta_v_total,
        'transfer_time_s': T_total,
        'transfer_time_days': T_total / 86400,
        'a1_m': a1,
        'a2_m': a2,
    }


def plane_change_delta_v(v: float, delta_i: float) -> float:
    """
    Calculate delta-v for simple plane change.

    Δv = 2v*sin(Δi/2)

    Args:
        v: Orbital velocity (m/s)
        delta_i: Inclination change (rad)

    Returns:
        Required delta-v (m/s)
    """
    return 2 * v * math.sin(delta_i / 2)


def combined_plane_change(v1: float, v2: float, delta_i: float) -> float:
    """
    Calculate optimal delta-v for combined plane change and velocity change.

    Δv = √(v1² + v2² - 2*v1*v2*cos(Δi))

    Args:
        v1: Initial velocity (m/s)
        v2: Final velocity (m/s)
        delta_i: Inclination change (rad)

    Returns:
        Required delta-v (m/s)
    """
    return math.sqrt(v1 ** 2 + v2 ** 2 - 2 * v1 * v2 * math.cos(delta_i))


# =============================================================================
# SPHERE OF INFLUENCE
# =============================================================================

def sphere_of_influence(a: float, m_body: float, m_primary: float) -> float:
    """
    Calculate sphere of influence radius (Laplace).

    r_SOI = a * (m_body / m_primary)^(2/5)

    Args:
        a: Semi-major axis of body's orbit (m)
        m_body: Mass of body (kg)
        m_primary: Mass of primary (kg)

    Returns:
        Sphere of influence radius (m)
    """
    return a * (m_body / m_primary) ** 0.4


# Pre-calculated SOI values (m)
SOI_EARTH = 9.24e8  # From Sun
SOI_MOON = 6.62e7   # From Earth
SOI_MARS = 5.77e8
SOI_JUPITER = 4.82e10


# =============================================================================
# HYPERBOLIC TRAJECTORIES
# =============================================================================

def hyperbolic_excess_velocity(v_inf: float, r_p: float, mu: float) -> float:
    """
    Calculate periapsis velocity for hyperbolic trajectory.

    v_p = √(v_∞² + 2μ/r_p)

    Args:
        v_inf: Hyperbolic excess velocity (m/s)
        r_p: Periapsis radius (m)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Periapsis velocity (m/s)
    """
    return math.sqrt(v_inf ** 2 + 2 * mu / r_p)


def hyperbolic_eccentricity(v_inf: float, r_p: float, mu: float) -> float:
    """
    Calculate eccentricity of hyperbolic trajectory.

    e = 1 + r_p * v_∞² / μ

    Args:
        v_inf: Hyperbolic excess velocity (m/s)
        r_p: Periapsis radius (m)
        mu: Gravitational parameter (m³/s²)

    Returns:
        Eccentricity (> 1 for hyperbola)
    """
    return 1 + r_p * v_inf ** 2 / mu


def turn_angle(e: float) -> float:
    """
    Calculate turn angle for hyperbolic flyby.

    δ = 2 * arcsin(1/e)

    Args:
        e: Eccentricity (must be > 1)

    Returns:
        Turn angle (rad)
    """
    if e <= 1:
        raise ValueError("Eccentricity must be > 1 for hyperbolic trajectory")
    return 2 * math.asin(1 / e)


def gravity_assist_delta_v(v_inf: float, turn_angle: float) -> float:
    """
    Calculate velocity change from gravity assist.

    |Δv| = 2 * v_∞ * sin(δ/2)

    Args:
        v_inf: Hyperbolic excess velocity (m/s)
        turn_angle: Turn angle (rad)

    Returns:
        Magnitude of velocity change (m/s)
    """
    return 2 * v_inf * math.sin(turn_angle / 2)


# =============================================================================
# PERTURBATIONS
# =============================================================================

def j2_nodal_precession(a: float, e: float, i: float, mu: float = MU_EARTH,
                       J2: float = J2_EARTH, R: float = RADIUS_EARTH) -> float:
    """
    Calculate nodal precession rate due to J2.

    dΩ/dt = -3/2 * n * J2 * (R/p)² * cos(i)

    Args:
        a: Semi-major axis (m)
        e: Eccentricity
        i: Inclination (rad)
        mu: Gravitational parameter (m³/s²)
        J2: J2 coefficient
        R: Body equatorial radius (m)

    Returns:
        Nodal precession rate (rad/s)
    """
    n = math.sqrt(mu / a ** 3)  # Mean motion
    p = a * (1 - e ** 2)  # Semi-latus rectum

    return -1.5 * n * J2 * (R / p) ** 2 * math.cos(i)


def j2_apsidal_precession(a: float, e: float, i: float, mu: float = MU_EARTH,
                         J2: float = J2_EARTH, R: float = RADIUS_EARTH) -> float:
    """
    Calculate apsidal precession rate due to J2.

    dω/dt = 3/4 * n * J2 * (R/p)² * (5*cos²(i) - 1)

    Args:
        a: Semi-major axis (m)
        e: Eccentricity
        i: Inclination (rad)
        mu: Gravitational parameter (m³/s²)
        J2: J2 coefficient
        R: Body equatorial radius (m)

    Returns:
        Apsidal precession rate (rad/s)
    """
    n = math.sqrt(mu / a ** 3)
    p = a * (1 - e ** 2)

    return 0.75 * n * J2 * (R / p) ** 2 * (5 * math.cos(i) ** 2 - 1)


def sun_synchronous_inclination(a: float, e: float = 0, mu: float = MU_EARTH,
                                J2: float = J2_EARTH,
                                R: float = RADIUS_EARTH) -> float:
    """
    Calculate inclination for sun-synchronous orbit.

    The nodal precession rate must equal 2π/year ≈ 1.991×10⁻⁷ rad/s

    Args:
        a: Semi-major axis (m)
        e: Eccentricity
        mu: Gravitational parameter (m³/s²)
        J2: J2 coefficient
        R: Body equatorial radius (m)

    Returns:
        Required inclination (rad)
    """
    # Target precession rate (1 revolution per year)
    target_rate = 2 * math.pi / (365.25 * 86400)

    n = math.sqrt(mu / a ** 3)
    p = a * (1 - e ** 2)

    # -3/2 * n * J2 * (R/p)² * cos(i) = target_rate
    # cos(i) = -target_rate / (3/2 * n * J2 * (R/p)²)

    cos_i = -target_rate / (1.5 * n * J2 * (R / p) ** 2)

    if abs(cos_i) > 1:
        raise ValueError("Sun-synchronous orbit not possible at this altitude")

    return math.acos(cos_i)


# =============================================================================
# LAGRANGE POINTS
# =============================================================================

def lagrange_l1_distance(a: float, m1: float, m2: float) -> float:
    """
    Calculate approximate L1 distance from smaller body.

    r_L1 ≈ a * (m2 / (3*m1))^(1/3)

    Args:
        a: Semi-major axis of system (m)
        m1: Mass of primary (kg)
        m2: Mass of secondary (kg)

    Returns:
        Distance from secondary to L1 (m)
    """
    return a * (m2 / (3 * m1)) ** (1 / 3)


def lagrange_l2_distance(a: float, m1: float, m2: float) -> float:
    """
    Calculate approximate L2 distance from smaller body.

    r_L2 ≈ a * (m2 / (3*m1))^(1/3)

    Args:
        a: Semi-major axis of system (m)
        m1: Mass of primary (kg)
        m2: Mass of secondary (kg)

    Returns:
        Distance from secondary to L2 (m)
    """
    return a * (m2 / (3 * m1)) ** (1 / 3)


# =============================================================================
# COMPREHENSIVE ORBITAL MECHANICS CALCULATION
# =============================================================================

def orbital_mechanics(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive orbital mechanics calculation.

    Args:
        params: Dictionary with relevant parameters such as:
            - central_body: 'earth', 'sun', 'moon', 'mars', 'jupiter'
            - altitude: Orbital altitude (m) [for circular orbits]
            - r_periapsis, r_apoapsis: Apse radii (m)
            - semi_major_axis: Semi-major axis (m)
            - eccentricity: Eccentricity
            - inclination: Inclination (deg or rad)
            - true_anomaly: True anomaly (deg or rad)
            - transfer_to: Target radius for Hohmann transfer (m)

    Returns:
        Dictionary with computed orbital parameters
    """
    results = {}

    # Get central body parameters
    body = params.get('central_body', 'earth').lower()
    body_params = {
        'earth': {'mu': MU_EARTH, 'R': RADIUS_EARTH, 'J2': J2_EARTH},
        'sun': {'mu': MU_SUN, 'R': RADIUS_SUN, 'J2': 0},
        'moon': {'mu': MU_MOON, 'R': RADIUS_MOON, 'J2': 0},
        'mars': {'mu': MU_MARS, 'R': RADIUS_MARS, 'J2': 1.96e-3},
        'jupiter': {'mu': MU_JUPITER, 'R': 6.9911e7, 'J2': 0.01475},
    }

    if body in body_params:
        mu = body_params[body]['mu']
        R_body = body_params[body]['R']
        J2 = body_params[body]['J2']
    else:
        mu = params.get('mu', MU_EARTH)
        R_body = params.get('body_radius', RADIUS_EARTH)
        J2 = params.get('J2', 0)

    results['central_body'] = body
    results['mu_m3_s2'] = mu
    results['body_radius_m'] = R_body

    # Determine orbital elements
    if 'altitude' in params:
        # Circular orbit from altitude
        r = R_body + params['altitude']
        a = r
        e = 0.0
    elif 'r_periapsis' in params and 'r_apoapsis' in params:
        r_p = params['r_periapsis']
        r_a = params['r_apoapsis']
        a = (r_p + r_a) / 2
        e = eccentricity_from_apse(r_a, r_p)
    elif 'semi_major_axis' in params:
        a = params['semi_major_axis']
        e = params.get('eccentricity', 0.0)
    else:
        # Default: LEO
        a = R_body + 400000  # 400 km altitude
        e = 0.0

    # Inclination
    i = params.get('inclination', 0.0)
    if params.get('inclination_unit', 'deg') == 'deg':
        i = math.radians(i)

    # True anomaly
    nu = params.get('true_anomaly', 0.0)
    if params.get('anomaly_unit', 'deg') == 'deg':
        nu = math.radians(nu)

    # Basic orbital properties
    r_p = periapsis_radius(a, e)
    r_a = apoapsis_radius(a, e) if e < 1 else float('inf')
    T = orbital_period(a, mu) if e < 1 else float('inf')

    results['semi_major_axis_m'] = a
    results['eccentricity'] = e
    results['inclination_deg'] = math.degrees(i)
    results['periapsis_radius_m'] = r_p
    results['periapsis_altitude_m'] = r_p - R_body
    results['apoapsis_radius_m'] = r_a
    results['apoapsis_altitude_m'] = r_a - R_body if e < 1 else float('inf')
    results['period_s'] = T
    results['period_min'] = T / 60 if T < float('inf') else float('inf')
    results['period_hours'] = T / 3600 if T < float('inf') else float('inf')

    # Velocities
    v_p = orbital_velocity(r_p, a, mu)
    v_a = orbital_velocity(r_a, a, mu) if e < 1 and r_a > 0 else 0
    v_circular = circular_velocity(r_p, mu)
    v_escape = escape_velocity(r_p, mu)

    results['periapsis_velocity_m_s'] = v_p
    results['apoapsis_velocity_m_s'] = v_a
    results['circular_velocity_m_s'] = v_circular
    results['escape_velocity_m_s'] = v_escape

    # At current true anomaly
    r_current = radius_at_true_anomaly(a, e, nu)
    v_current = velocity_at_true_anomaly(a, e, nu, mu)
    gamma = flight_path_angle(e, nu)

    results['current_radius_m'] = r_current
    results['current_velocity_m_s'] = v_current
    results['flight_path_angle_deg'] = math.degrees(gamma)

    # Energy and angular momentum
    epsilon = specific_orbital_energy(r_current, v_current, mu)
    h = specific_angular_momentum(r_current, v_current, gamma)

    results['specific_orbital_energy_J_kg'] = epsilon
    results['specific_angular_momentum_m2_s'] = h

    # Orbit classification
    if e == 0:
        orbit_type = 'circular'
    elif e < 1:
        orbit_type = 'elliptical'
    elif e == 1:
        orbit_type = 'parabolic'
    else:
        orbit_type = 'hyperbolic'
    results['orbit_type'] = orbit_type

    # J2 perturbations (if applicable)
    if J2 > 0 and e < 1:
        omega_dot = j2_apsidal_precession(a, e, i, mu, J2, R_body)
        Omega_dot = j2_nodal_precession(a, e, i, mu, J2, R_body)

        results['nodal_precession_deg_day'] = math.degrees(Omega_dot) * 86400
        results['apsidal_precession_deg_day'] = math.degrees(omega_dot) * 86400

        # Check sun-synchronous
        if body == 'earth' and e < 0.2:
            try:
                i_ss = sun_synchronous_inclination(a, e, mu, J2, R_body)
                results['sun_sync_inclination_deg'] = math.degrees(i_ss)
            except ValueError:
                results['sun_sync_inclination_deg'] = None

    # Hohmann transfer (if target given)
    if 'transfer_to' in params:
        r_target = params['transfer_to']
        if r_target != r_p:  # Only if different orbit
            hohmann = hohmann_transfer(r_p, r_target, mu)
            results['hohmann_transfer'] = hohmann

    return results
