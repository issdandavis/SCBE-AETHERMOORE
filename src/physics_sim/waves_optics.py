#!/usr/bin/env python3
"""
Waves and Optics Module

Comprehensive wave physics and optics calculations:
- Wave properties and interference
- Sound and acoustics
- Electromagnetic waves
- Geometric optics (reflection, refraction)
- Physical optics (diffraction, polarization)
- Fiber optics and waveguides

Based on established wave physics.
"""

import math
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass

# =============================================================================
# CONSTANTS
# =============================================================================

C = 299792458  # Speed of light in vacuum (m/s)
PLANCK = 6.62607015e-34  # Planck constant (J·s)
VACUUM_PERMITTIVITY = 8.8541878128e-12  # ε₀ (F/m)
VACUUM_PERMEABILITY = 1.25663706212e-6  # μ₀ (H/m)


# =============================================================================
# BASIC WAVE PROPERTIES
# =============================================================================


def wave_velocity(frequency: float, wavelength: float) -> float:
    """
    Calculate wave velocity.

    v = f * λ

    Args:
        frequency: Frequency (Hz)
        wavelength: Wavelength (m)

    Returns:
        Wave velocity (m/s)
    """
    return frequency * wavelength


def wavelength_from_velocity(velocity: float, frequency: float) -> float:
    """
    Calculate wavelength from velocity and frequency.

    λ = v / f

    Args:
        velocity: Wave velocity (m/s)
        frequency: Frequency (Hz)

    Returns:
        Wavelength (m)
    """
    return velocity / frequency


def frequency_from_period(period: float) -> float:
    """
    Calculate frequency from period.

    f = 1 / T

    Args:
        period: Wave period (s)

    Returns:
        Frequency (Hz)
    """
    return 1 / period


def angular_frequency(frequency: float) -> float:
    """
    Calculate angular frequency.

    ω = 2πf

    Args:
        frequency: Frequency (Hz)

    Returns:
        Angular frequency (rad/s)
    """
    return 2 * math.pi * frequency


def wave_number(wavelength: float) -> float:
    """
    Calculate wave number.

    k = 2π / λ

    Args:
        wavelength: Wavelength (m)

    Returns:
        Wave number (rad/m)
    """
    return 2 * math.pi / wavelength


def phase_velocity(omega: float, k: float) -> float:
    """
    Calculate phase velocity.

    v_p = ω / k

    Args:
        omega: Angular frequency (rad/s)
        k: Wave number (rad/m)

    Returns:
        Phase velocity (m/s)
    """
    return omega / k


def group_velocity(d_omega_dk: float) -> float:
    """
    Calculate group velocity (requires dispersion relation derivative).

    v_g = dω/dk

    Args:
        d_omega_dk: Derivative of omega with respect to k

    Returns:
        Group velocity (m/s)
    """
    return d_omega_dk


# =============================================================================
# WAVE AMPLITUDE AND INTENSITY
# =============================================================================


def wave_displacement(
    A: float, k: float, x: float, omega: float, t: float, phi: float = 0
) -> float:
    """
    Calculate wave displacement at position x and time t.

    y(x,t) = A * sin(kx - ωt + φ)

    Args:
        A: Amplitude
        k: Wave number (rad/m)
        x: Position (m)
        omega: Angular frequency (rad/s)
        t: Time (s)
        phi: Initial phase (rad)

    Returns:
        Displacement
    """
    return A * math.sin(k * x - omega * t + phi)


def wave_intensity(
    amplitude: float, velocity: float, density: float, omega: float
) -> float:
    """
    Calculate wave intensity (power per unit area).

    I = ½ρvω²A²

    Args:
        amplitude: Wave amplitude
        velocity: Wave velocity (m/s)
        density: Medium density (kg/m³)
        omega: Angular frequency (rad/s)

    Returns:
        Intensity (W/m²)
    """
    return 0.5 * density * velocity * omega**2 * amplitude**2


def intensity_ratio_db(I1: float, I2: float) -> float:
    """
    Calculate intensity ratio in decibels.

    dB = 10 * log₁₀(I1/I2)

    Args:
        I1: First intensity
        I2: Reference intensity

    Returns:
        Intensity ratio (dB)
    """
    return 10 * math.log10(I1 / I2)


def inverse_square_law(I0: float, r0: float, r: float) -> float:
    """
    Calculate intensity at distance r using inverse square law.

    I = I₀ * (r₀/r)²

    Args:
        I0: Initial intensity (W/m²)
        r0: Initial distance (m)
        r: Final distance (m)

    Returns:
        Intensity at distance r (W/m²)
    """
    return I0 * (r0 / r) ** 2


# =============================================================================
# INTERFERENCE
# =============================================================================


def two_source_interference(
    A1: float, A2: float, phi1: float, phi2: float
) -> Tuple[float, float]:
    """
    Calculate resultant amplitude from two-source interference.

    A = √(A1² + A2² + 2A1A2cos(Δφ))

    Args:
        A1, A2: Amplitudes of two sources
        phi1, phi2: Phases of two sources (rad)

    Returns:
        Tuple of (resultant_amplitude, resultant_phase)
    """
    delta_phi = phi2 - phi1

    # Resultant amplitude
    A_sq = A1**2 + A2**2 + 2 * A1 * A2 * math.cos(delta_phi)
    A = math.sqrt(A_sq)

    # Resultant phase
    y = A1 * math.sin(phi1) + A2 * math.sin(phi2)
    x = A1 * math.cos(phi1) + A2 * math.cos(phi2)
    phi = math.atan2(y, x)

    return A, phi


def path_difference_to_phase(path_diff: float, wavelength: float) -> float:
    """
    Convert path difference to phase difference.

    Δφ = 2π * Δx / λ

    Args:
        path_diff: Path difference (m)
        wavelength: Wavelength (m)

    Returns:
        Phase difference (rad)
    """
    return 2 * math.pi * path_diff / wavelength


def young_double_slit_maxima(wavelength: float, d: float, m: int) -> float:
    """
    Calculate angle for bright fringe in Young's double slit.

    d * sin(θ) = m * λ

    Args:
        wavelength: Light wavelength (m)
        d: Slit separation (m)
        m: Order of maximum (0, ±1, ±2, ...)

    Returns:
        Angle θ (rad)
    """
    sin_theta = m * wavelength / d
    if abs(sin_theta) > 1:
        raise ValueError(f"No maximum at order {m} for these parameters")
    return math.asin(sin_theta)


def young_fringe_spacing(wavelength: float, d: float, L: float) -> float:
    """
    Calculate fringe spacing in Young's double slit (small angle approximation).

    Δy = λL/d

    Args:
        wavelength: Light wavelength (m)
        d: Slit separation (m)
        L: Screen distance (m)

    Returns:
        Fringe spacing (m)
    """
    return wavelength * L / d


def thin_film_constructive(n: float, t: float, wavelength: float, m: int = 0) -> bool:
    """
    Check if thin film interference is constructive.

    For normal incidence with higher index film on lower index substrate:
    2nt = (m + ½)λ (constructive, with phase shift at one surface)

    Args:
        n: Refractive index of film
        t: Film thickness (m)
        wavelength: Light wavelength in vacuum (m)
        m: Order

    Returns:
        True if constructive
    """
    # Optical path difference = 2nt
    opd = 2 * n * t

    # With phase shift at one surface
    for order in range(-5, m + 6):
        if abs(opd - (order + 0.5) * wavelength) < wavelength * 0.01:
            return True

    return False


# =============================================================================
# DIFFRACTION
# =============================================================================


def single_slit_minima(wavelength: float, a: float, m: int) -> float:
    """
    Calculate angle for dark fringe in single slit diffraction.

    a * sin(θ) = m * λ (m = ±1, ±2, ...)

    Args:
        wavelength: Light wavelength (m)
        a: Slit width (m)
        m: Order of minimum (±1, ±2, ...)

    Returns:
        Angle θ (rad)
    """
    if m == 0:
        raise ValueError("No minimum at m=0")

    sin_theta = m * wavelength / a
    if abs(sin_theta) > 1:
        raise ValueError(f"No minimum at order {m}")
    return math.asin(sin_theta)


def single_slit_intensity(theta: float, wavelength: float, a: float) -> float:
    """
    Calculate relative intensity in single slit diffraction.

    I/I₀ = (sin(β)/β)² where β = πa sin(θ)/λ

    Args:
        theta: Angle from central maximum (rad)
        wavelength: Light wavelength (m)
        a: Slit width (m)

    Returns:
        Relative intensity (0 to 1)
    """
    beta = math.pi * a * math.sin(theta) / wavelength

    if abs(beta) < 1e-10:
        return 1.0  # Central maximum

    return (math.sin(beta) / beta) ** 2


def diffraction_grating_maxima(wavelength: float, d: float, m: int) -> float:
    """
    Calculate angle for bright line in diffraction grating.

    d * sin(θ) = m * λ

    Args:
        wavelength: Light wavelength (m)
        d: Grating spacing (m)
        m: Order of maximum

    Returns:
        Angle θ (rad)
    """
    sin_theta = m * wavelength / d
    if abs(sin_theta) > 1:
        raise ValueError(f"No maximum at order {m}")
    return math.asin(sin_theta)


def grating_resolving_power(N: int, m: int) -> float:
    """
    Calculate resolving power of diffraction grating.

    R = λ/Δλ = mN

    Args:
        N: Number of grating lines
        m: Order of diffraction

    Returns:
        Resolving power
    """
    return m * N


def rayleigh_criterion(wavelength: float, diameter: float) -> float:
    """
    Calculate angular resolution limit (Rayleigh criterion).

    θ_min = 1.22λ/D

    Args:
        wavelength: Light wavelength (m)
        diameter: Aperture diameter (m)

    Returns:
        Minimum resolvable angle (rad)
    """
    return 1.22 * wavelength / diameter


def airy_disk_radius(wavelength: float, f_number: float) -> float:
    """
    Calculate Airy disk radius.

    r = 1.22 * λ * f/D = 1.22 * λ * f#

    Args:
        wavelength: Light wavelength (m)
        f_number: f/D ratio of optical system

    Returns:
        Airy disk radius (m)
    """
    return 1.22 * wavelength * f_number


# =============================================================================
# GEOMETRIC OPTICS
# =============================================================================


def snells_law(n1: float, theta1: float, n2: float) -> float:
    """
    Calculate refracted angle using Snell's law.

    n₁ sin(θ₁) = n₂ sin(θ₂)

    Args:
        n1: Refractive index of medium 1
        theta1: Incident angle (rad)
        n2: Refractive index of medium 2

    Returns:
        Refracted angle (rad), or raises ValueError for total internal reflection
    """
    sin_theta2 = n1 * math.sin(theta1) / n2

    if abs(sin_theta2) > 1:
        raise ValueError("Total internal reflection")

    return math.asin(sin_theta2)


def critical_angle(n1: float, n2: float) -> float:
    """
    Calculate critical angle for total internal reflection.

    θ_c = arcsin(n₂/n₁)

    Args:
        n1: Refractive index of denser medium
        n2: Refractive index of less dense medium

    Returns:
        Critical angle (rad)
    """
    if n2 >= n1:
        raise ValueError("n1 must be greater than n2")
    return math.asin(n2 / n1)


def brewsters_angle(n1: float, n2: float) -> float:
    """
    Calculate Brewster's angle (angle for complete polarization).

    θ_B = arctan(n₂/n₁)

    Args:
        n1: Refractive index of incident medium
        n2: Refractive index of refracted medium

    Returns:
        Brewster's angle (rad)
    """
    return math.atan(n2 / n1)


def thin_lens_equation(
    f: float, d_o: float = None, d_i: float = None
) -> Dict[str, float]:
    """
    Calculate image properties using thin lens equation.

    1/f = 1/d_o + 1/d_i

    Args:
        f: Focal length (m) (positive for converging)
        d_o: Object distance (m) (optional)
        d_i: Image distance (m) (optional)

    Returns:
        Dictionary with calculated values
    """
    results = {"focal_length_m": f}

    if d_o is not None:
        # Calculate image distance
        if abs(d_o - f) < 1e-15:
            d_i = float("inf")  # Object at focal point
        else:
            d_i = 1 / (1 / f - 1 / d_o)

        results["object_distance_m"] = d_o
        results["image_distance_m"] = d_i

        # Magnification
        m = -d_i / d_o if d_o != 0 else float("inf")
        results["magnification"] = m
        results["image_type"] = "real" if d_i > 0 else "virtual"
        results["image_orientation"] = "inverted" if m < 0 else "upright"

    elif d_i is not None:
        # Calculate object distance
        if abs(d_i - f) < 1e-15:
            d_o = float("inf")
        else:
            d_o = 1 / (1 / f - 1 / d_i)

        results["object_distance_m"] = d_o
        results["image_distance_m"] = d_i

        m = -d_i / d_o if d_o != 0 else float("inf")
        results["magnification"] = m

    return results


def lensmakers_equation(n: float, R1: float, R2: float, n_medium: float = 1.0) -> float:
    """
    Calculate lens focal length using lensmaker's equation.

    1/f = (n/n_m - 1) * (1/R₁ - 1/R₂)

    Sign convention: R > 0 if center of curvature is on output side

    Args:
        n: Lens refractive index
        R1: Radius of curvature of first surface (m)
        R2: Radius of curvature of second surface (m)
        n_medium: Medium refractive index (default air = 1.0)

    Returns:
        Focal length (m)
    """
    inv_f = (n / n_medium - 1) * (1 / R1 - 1 / R2)
    return 1 / inv_f


def spherical_mirror_equation(
    R: float, d_o: float = None, d_i: float = None
) -> Dict[str, float]:
    """
    Calculate image properties for spherical mirror.

    1/d_o + 1/d_i = 2/R = 1/f

    Args:
        R: Radius of curvature (m) (positive for concave)
        d_o: Object distance (m) (optional)
        d_i: Image distance (m) (optional)

    Returns:
        Dictionary with calculated values
    """
    f = R / 2
    return thin_lens_equation(f, d_o, d_i)


def optical_power(f: float) -> float:
    """
    Calculate optical power (diopters).

    P = 1/f (when f in meters)

    Args:
        f: Focal length (m)

    Returns:
        Optical power (diopters)
    """
    return 1 / f


def numerical_aperture(n: float, theta_max: float) -> float:
    """
    Calculate numerical aperture.

    NA = n * sin(θ_max)

    Args:
        n: Refractive index of medium
        theta_max: Maximum acceptance half-angle (rad)

    Returns:
        Numerical aperture
    """
    return n * math.sin(theta_max)


# =============================================================================
# SOUND AND ACOUSTICS
# =============================================================================


def sound_speed_air(T_celsius: float) -> float:
    """
    Calculate speed of sound in air.

    v ≈ 331.3 + 0.606*T (simplified formula)

    More accurate: v = 331.3 * √(1 + T/273.15)

    Args:
        T_celsius: Temperature in Celsius

    Returns:
        Speed of sound (m/s)
    """
    return 331.3 * math.sqrt(1 + T_celsius / 273.15)


def sound_speed_medium(bulk_modulus: float, density: float) -> float:
    """
    Calculate speed of sound in a medium.

    v = √(K/ρ) for fluids
    v = √(E/ρ) for solids (using Young's modulus)

    Args:
        bulk_modulus: Bulk modulus or Young's modulus (Pa)
        density: Density (kg/m³)

    Returns:
        Speed of sound (m/s)
    """
    return math.sqrt(bulk_modulus / density)


def doppler_shift_moving_source(
    f_source: float, v_source: float, v_sound: float, approaching: bool = True
) -> float:
    """
    Calculate Doppler shifted frequency (moving source).

    f' = f * v_sound / (v_sound ∓ v_source)

    Args:
        f_source: Source frequency (Hz)
        v_source: Source velocity (m/s)
        v_sound: Speed of sound (m/s)
        approaching: True if source approaching, False if receding

    Returns:
        Observed frequency (Hz)
    """
    if approaching:
        return f_source * v_sound / (v_sound - v_source)
    else:
        return f_source * v_sound / (v_sound + v_source)


def doppler_shift_moving_observer(
    f_source: float, v_observer: float, v_sound: float, approaching: bool = True
) -> float:
    """
    Calculate Doppler shifted frequency (moving observer).

    f' = f * (v_sound ± v_observer) / v_sound

    Args:
        f_source: Source frequency (Hz)
        v_observer: Observer velocity (m/s)
        v_sound: Speed of sound (m/s)
        approaching: True if observer approaching, False if receding

    Returns:
        Observed frequency (Hz)
    """
    if approaching:
        return f_source * (v_sound + v_observer) / v_sound
    else:
        return f_source * (v_sound - v_observer) / v_sound


def sound_intensity_level(I: float, I_ref: float = 1e-12) -> float:
    """
    Calculate sound intensity level in decibels.

    β = 10 * log₁₀(I/I₀)

    Args:
        I: Sound intensity (W/m²)
        I_ref: Reference intensity (default 1e-12 W/m², threshold of hearing)

    Returns:
        Sound level (dB)
    """
    return 10 * math.log10(I / I_ref)


def beat_frequency(f1: float, f2: float) -> float:
    """
    Calculate beat frequency from two interfering waves.

    f_beat = |f₁ - f₂|

    Args:
        f1: First frequency (Hz)
        f2: Second frequency (Hz)

    Returns:
        Beat frequency (Hz)
    """
    return abs(f1 - f2)


def resonance_tube_open(L: float, v: float, n: int = 1) -> float:
    """
    Calculate resonant frequency for open tube (both ends open).

    f_n = nv/(2L), n = 1, 2, 3, ...

    Args:
        L: Tube length (m)
        v: Speed of sound (m/s)
        n: Harmonic number

    Returns:
        Resonant frequency (Hz)
    """
    return n * v / (2 * L)


def resonance_tube_closed(L: float, v: float, n: int = 1) -> float:
    """
    Calculate resonant frequency for closed tube (one end closed).

    f_n = (2n-1)v/(4L), n = 1, 2, 3, ... (odd harmonics only)

    Args:
        L: Tube length (m)
        v: Speed of sound (m/s)
        n: Harmonic number

    Returns:
        Resonant frequency (Hz)
    """
    return (2 * n - 1) * v / (4 * L)


# =============================================================================
# ELECTROMAGNETIC WAVES
# =============================================================================


def em_wave_speed(epsilon_r: float = 1, mu_r: float = 1) -> float:
    """
    Calculate EM wave speed in medium.

    v = c / √(ε_r * μ_r)

    Args:
        epsilon_r: Relative permittivity
        mu_r: Relative permeability

    Returns:
        Wave speed (m/s)
    """
    return C / math.sqrt(epsilon_r * mu_r)


def refractive_index(epsilon_r: float, mu_r: float = 1) -> float:
    """
    Calculate refractive index.

    n = √(ε_r * μ_r)

    Args:
        epsilon_r: Relative permittivity
        mu_r: Relative permeability

    Returns:
        Refractive index
    """
    return math.sqrt(epsilon_r * mu_r)


def poynting_vector_magnitude(E: float, B: float) -> float:
    """
    Calculate Poynting vector magnitude (intensity).

    S = EB/μ₀ = E²/(μ₀c) = cε₀E²

    Args:
        E: Electric field amplitude (V/m)
        B: Magnetic field amplitude (T)

    Returns:
        Intensity (W/m²)
    """
    return E * B / VACUUM_PERMEABILITY


def em_field_ratio(n: float = 1) -> float:
    """
    Calculate E/B ratio for EM wave.

    E/B = c/n

    Args:
        n: Refractive index

    Returns:
        E/B ratio (m/s)
    """
    return C / n


def radiation_pressure(I: float, reflectivity: float = 0) -> float:
    """
    Calculate radiation pressure.

    P = I/c (absorbed) or P = 2I/c (reflected)

    Args:
        I: Intensity (W/m²)
        reflectivity: Fraction reflected (0 to 1)

    Returns:
        Radiation pressure (Pa)
    """
    return I / C * (1 + reflectivity)


def wavelength_to_frequency(wavelength: float) -> float:
    """Convert wavelength to frequency for EM waves."""
    return C / wavelength


def frequency_to_wavelength(frequency: float) -> float:
    """Convert frequency to wavelength for EM waves."""
    return C / frequency


def classify_em_wave(wavelength: float) -> str:
    """
    Classify electromagnetic wave by wavelength.

    Args:
        wavelength: Wavelength (m)

    Returns:
        Wave type classification
    """
    if wavelength < 1e-12:
        return "gamma_ray"
    elif wavelength < 1e-8:
        return "x_ray"
    elif wavelength < 4e-7:
        return "ultraviolet"
    elif wavelength < 7e-7:
        return "visible_light"
    elif wavelength < 1e-3:
        return "infrared"
    elif wavelength < 1:
        return "microwave"
    else:
        return "radio_wave"


# =============================================================================
# COMPREHENSIVE WAVES AND OPTICS CALCULATION
# =============================================================================


def waves_optics(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive waves and optics calculation.

    Args:
        params: Dictionary with relevant parameters

    Returns:
        Dictionary with computed wave/optical properties
    """
    results = {}

    # Basic wave properties
    if "frequency" in params and "wavelength" in params:
        f = params["frequency"]
        lam = params["wavelength"]
        v = wave_velocity(f, lam)
        results["wave_velocity_m_s"] = v
        results["angular_frequency_rad_s"] = angular_frequency(f)
        results["wave_number_rad_m"] = wave_number(lam)
        results["period_s"] = 1 / f

    # EM wave classification
    if "wavelength" in params:
        lam = params["wavelength"]
        results["em_wave_type"] = classify_em_wave(lam)
        results["em_frequency_Hz"] = wavelength_to_frequency(lam)

    # Snell's law
    if "n1" in params and "n2" in params and "angle_incident" in params:
        n1 = params["n1"]
        n2 = params["n2"]
        theta1 = params["angle_incident"]

        try:
            theta2 = snells_law(n1, theta1, n2)
            results["refracted_angle_rad"] = theta2
            results["refracted_angle_deg"] = math.degrees(theta2)
        except ValueError:
            results["total_internal_reflection"] = True

        # Critical angle (if applicable)
        if n1 > n2:
            theta_c = critical_angle(n1, n2)
            results["critical_angle_rad"] = theta_c
            results["critical_angle_deg"] = math.degrees(theta_c)

        # Brewster's angle
        theta_B = brewsters_angle(n1, n2)
        results["brewster_angle_rad"] = theta_B
        results["brewster_angle_deg"] = math.degrees(theta_B)

    # Thin lens
    if "focal_length" in params:
        f = params["focal_length"]
        d_o = params.get("object_distance")
        lens_results = thin_lens_equation(f, d_o)
        results["lens"] = lens_results

    # Diffraction
    if "slit_width" in params and "wavelength" in params:
        a = params["slit_width"]
        lam = params["wavelength"]

        results["first_minimum_angle_rad"] = single_slit_minima(lam, a, 1)
        results["first_minimum_angle_deg"] = math.degrees(
            results["first_minimum_angle_rad"]
        )

    # Double slit
    if "slit_separation" in params and "wavelength" in params:
        d = params["slit_separation"]
        lam = params["wavelength"]
        L = params.get("screen_distance", 1.0)

        results["fringe_spacing_m"] = young_fringe_spacing(lam, d, L)
        results["first_maximum_angle_rad"] = young_double_slit_maxima(lam, d, 1)

    # Sound
    if "temperature_celsius" in params:
        T = params["temperature_celsius"]
        v_sound = sound_speed_air(T)
        results["sound_speed_m_s"] = v_sound

    # Doppler effect
    if "source_frequency" in params and "source_velocity" in params:
        f_s = params["source_frequency"]
        v_s = params["source_velocity"]
        v_sound = params.get("sound_speed", 343)
        approaching = params.get("approaching", True)

        f_obs = doppler_shift_moving_source(f_s, v_s, v_sound, approaching)
        results["observed_frequency_Hz"] = f_obs
        results["frequency_shift_Hz"] = f_obs - f_s

    return results
