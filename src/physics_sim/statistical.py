#!/usr/bin/env python3
"""
Statistical Mechanics Module

Comprehensive statistical mechanics calculations covering:
- Partition functions
- Maxwell-Boltzmann distribution
- Fermi-Dirac distribution
- Bose-Einstein distribution
- Entropy and free energy
- Phase transitions

Based on established statistical mechanics.
"""

import math
from typing import Dict, Any, Tuple, Optional, Callable, List
from dataclasses import dataclass


# =============================================================================
# CONSTANTS
# =============================================================================

BOLTZMANN = 1.380649e-23      # Boltzmann constant (J/K)
PLANCK = 6.62607015e-34       # Planck constant (J·s)
HBAR = PLANCK / (2 * math.pi)
AVOGADRO = 6.02214076e23      # Avogadro's number
GAS_CONSTANT = 8.314462618    # J/(mol·K)


# =============================================================================
# PARTITION FUNCTIONS
# =============================================================================

def translational_partition_function(m: float, V: float, T: float) -> float:
    """
    Calculate translational partition function for ideal gas.

    Z_trans = V / λ³ where λ = h / √(2πmkT) (thermal de Broglie wavelength)

    Args:
        m: Particle mass (kg)
        V: Volume (m³)
        T: Temperature (K)

    Returns:
        Translational partition function
    """
    lambda_db = PLANCK / math.sqrt(2 * math.pi * m * BOLTZMANN * T)
    return V / lambda_db ** 3


def thermal_wavelength(m: float, T: float) -> float:
    """
    Calculate thermal de Broglie wavelength.

    λ = h / √(2πmkT)

    Args:
        m: Particle mass (kg)
        T: Temperature (K)

    Returns:
        Thermal wavelength (m)
    """
    return PLANCK / math.sqrt(2 * math.pi * m * BOLTZMANN * T)


def rotational_partition_function_linear(B: float, T: float,
                                        sigma: int = 1) -> float:
    """
    Calculate rotational partition function for linear molecule.

    Z_rot = kT / (σBhc) (high-T limit)

    Args:
        B: Rotational constant (m⁻¹)
        T: Temperature (K)
        sigma: Symmetry number (1 for heteronuclear, 2 for homonuclear)

    Returns:
        Rotational partition function
    """
    C = 299792458  # Speed of light
    theta_rot = PLANCK * C * B / BOLTZMANN  # Characteristic rotational temperature

    if T > theta_rot:
        # Classical limit
        return T / (sigma * theta_rot)
    else:
        # Quantum sum (first few terms)
        Z = 0
        for J in range(100):
            E_J = J * (J + 1) * theta_rot
            g_J = 2 * J + 1  # Degeneracy
            Z += g_J * math.exp(-E_J / T)
        return Z / sigma


def vibrational_partition_function(nu: float, T: float) -> float:
    """
    Calculate vibrational partition function for harmonic oscillator.

    Z_vib = 1 / (1 - exp(-hν/kT)) = 1 / (1 - exp(-θ_v/T))

    Args:
        nu: Vibrational frequency (Hz)
        T: Temperature (K)

    Returns:
        Vibrational partition function
    """
    theta_vib = PLANCK * nu / BOLTZMANN  # Characteristic vibrational temperature

    if T < theta_vib * 0.01:
        # Low T: ground state dominates
        return 1.0

    x = theta_vib / T
    if x > 700:
        return 1.0
    return 1 / (1 - math.exp(-x))


def electronic_partition_function(degeneracies: List[int],
                                 energies: List[float], T: float) -> float:
    """
    Calculate electronic partition function.

    Z_elec = Σ g_i * exp(-E_i/kT)

    Args:
        degeneracies: List of level degeneracies
        energies: List of level energies (J)
        T: Temperature (K)

    Returns:
        Electronic partition function
    """
    Z = 0
    for g, E in zip(degeneracies, energies):
        Z += g * math.exp(-E / (BOLTZMANN * T))
    return Z


# =============================================================================
# DISTRIBUTION FUNCTIONS
# =============================================================================

def maxwell_boltzmann_speed_distribution(v: float, m: float, T: float) -> float:
    """
    Maxwell-Boltzmann speed distribution.

    f(v) = 4π * (m/(2πkT))^(3/2) * v² * exp(-mv²/2kT)

    Args:
        v: Speed (m/s)
        m: Particle mass (kg)
        T: Temperature (K)

    Returns:
        Probability density (s/m)
    """
    alpha = m / (2 * BOLTZMANN * T)
    prefactor = 4 * math.pi * (alpha / math.pi) ** 1.5
    return prefactor * v ** 2 * math.exp(-alpha * v ** 2)


def maxwell_boltzmann_energy_distribution(E: float, T: float) -> float:
    """
    Maxwell-Boltzmann energy distribution.

    g(E) = 2π * (1/(πkT))^(3/2) * √E * exp(-E/kT)

    Args:
        E: Energy (J)
        T: Temperature (K)

    Returns:
        Probability density (1/J)
    """
    if E < 0:
        return 0
    kT = BOLTZMANN * T
    prefactor = 2 * math.pi * (1 / (math.pi * kT)) ** 1.5
    return prefactor * math.sqrt(E) * math.exp(-E / kT)


def most_probable_speed(m: float, T: float) -> float:
    """
    Calculate most probable speed in Maxwell-Boltzmann distribution.

    v_p = √(2kT/m)

    Args:
        m: Particle mass (kg)
        T: Temperature (K)

    Returns:
        Most probable speed (m/s)
    """
    return math.sqrt(2 * BOLTZMANN * T / m)


def mean_speed(m: float, T: float) -> float:
    """
    Calculate mean speed in Maxwell-Boltzmann distribution.

    <v> = √(8kT/(πm))

    Args:
        m: Particle mass (kg)
        T: Temperature (K)

    Returns:
        Mean speed (m/s)
    """
    return math.sqrt(8 * BOLTZMANN * T / (math.pi * m))


def rms_speed(m: float, T: float) -> float:
    """
    Calculate root-mean-square speed.

    v_rms = √(3kT/m)

    Args:
        m: Particle mass (kg)
        T: Temperature (K)

    Returns:
        RMS speed (m/s)
    """
    return math.sqrt(3 * BOLTZMANN * T / m)


def fermi_dirac_distribution(E: float, mu: float, T: float) -> float:
    """
    Fermi-Dirac distribution.

    f(E) = 1 / (exp((E-μ)/kT) + 1)

    Args:
        E: Energy (J)
        mu: Chemical potential (J)
        T: Temperature (K)

    Returns:
        Occupation probability (0 to 1)
    """
    x = (E - mu) / (BOLTZMANN * T)
    if x > 700:
        return 0
    elif x < -700:
        return 1
    return 1 / (math.exp(x) + 1)


def bose_einstein_distribution(E: float, mu: float, T: float) -> float:
    """
    Bose-Einstein distribution.

    n(E) = 1 / (exp((E-μ)/kT) - 1)

    Args:
        E: Energy (J)
        mu: Chemical potential (J) (must be ≤ ground state energy)
        T: Temperature (K)

    Returns:
        Average occupation number
    """
    x = (E - mu) / (BOLTZMANN * T)
    if x < 0:
        raise ValueError("E must be >= mu for Bose-Einstein distribution")
    if x > 700:
        return 0
    if x < 1e-10:
        # Near-divergence region
        return BOLTZMANN * T / (E - mu)
    return 1 / (math.exp(x) - 1)


def planck_distribution(nu: float, T: float) -> float:
    """
    Planck distribution for blackbody radiation.

    n(ν) = 1 / (exp(hν/kT) - 1)

    This is the Bose-Einstein distribution for photons (μ = 0).

    Args:
        nu: Frequency (Hz)
        T: Temperature (K)

    Returns:
        Average photon occupation number
    """
    x = PLANCK * nu / (BOLTZMANN * T)
    if x > 700:
        return 0
    return 1 / (math.exp(x) - 1)


def planck_spectral_radiance(nu: float, T: float) -> float:
    """
    Planck's law for spectral radiance.

    B(ν,T) = (2hν³/c²) * 1/(exp(hν/kT) - 1)

    Args:
        nu: Frequency (Hz)
        T: Temperature (K)

    Returns:
        Spectral radiance (W/(m²·sr·Hz))
    """
    C = 299792458
    x = PLANCK * nu / (BOLTZMANN * T)

    if x > 700:
        return 0

    prefactor = 2 * PLANCK * nu ** 3 / C ** 2
    return prefactor / (math.exp(x) - 1)


# =============================================================================
# THERMODYNAMIC QUANTITIES
# =============================================================================

def helmholtz_free_energy(Z: float, T: float) -> float:
    """
    Calculate Helmholtz free energy from partition function.

    F = -kT * ln(Z)

    Args:
        Z: Partition function
        T: Temperature (K)

    Returns:
        Helmholtz free energy (J)
    """
    return -BOLTZMANN * T * math.log(Z)


def internal_energy_from_Z(Z: float, T: float, dZ_dT: float) -> float:
    """
    Calculate internal energy from partition function.

    U = kT² * (∂ln(Z)/∂T)_V = kT² * (1/Z)(∂Z/∂T)

    Args:
        Z: Partition function
        T: Temperature (K)
        dZ_dT: Temperature derivative of Z

    Returns:
        Internal energy (J)
    """
    return BOLTZMANN * T ** 2 * dZ_dT / Z


def entropy_from_Z(Z: float, T: float, U: float) -> float:
    """
    Calculate entropy from partition function.

    S = k * ln(Z) + U/T = (U - F)/T

    Args:
        Z: Partition function
        T: Temperature (K)
        U: Internal energy (J)

    Returns:
        Entropy (J/K)
    """
    return BOLTZMANN * math.log(Z) + U / T


def heat_capacity_ideal_gas(dof: int, n: float = 1) -> Dict[str, float]:
    """
    Calculate heat capacities for ideal gas.

    C_V = (f/2) * nR
    C_P = ((f+2)/2) * nR = C_V + nR

    Args:
        dof: Degrees of freedom (3 for monatomic, 5 for diatomic, etc.)
        n: Number of moles

    Returns:
        Dictionary with C_V, C_P, and gamma
    """
    C_V = (dof / 2) * n * GAS_CONSTANT
    C_P = ((dof + 2) / 2) * n * GAS_CONSTANT
    gamma = C_P / C_V

    return {
        'C_V_J_per_K': C_V,
        'C_P_J_per_K': C_P,
        'gamma': gamma,
        'dof': dof,
    }


def equipartition_energy(dof: int, T: float) -> float:
    """
    Calculate average energy per particle using equipartition theorem.

    <E> = (f/2) * kT

    Args:
        dof: Degrees of freedom
        T: Temperature (K)

    Returns:
        Average energy per particle (J)
    """
    return (dof / 2) * BOLTZMANN * T


# =============================================================================
# BOLTZMANN ENTROPY
# =============================================================================

def boltzmann_entropy(W: int) -> float:
    """
    Calculate Boltzmann entropy.

    S = k * ln(W)

    Args:
        W: Number of microstates

    Returns:
        Entropy (J/K)
    """
    return BOLTZMANN * math.log(W)


def gibbs_entropy(probabilities: List[float]) -> float:
    """
    Calculate Gibbs entropy.

    S = -k * Σ p_i * ln(p_i)

    Args:
        probabilities: List of state probabilities (must sum to 1)

    Returns:
        Entropy (J/K)
    """
    S = 0
    for p in probabilities:
        if p > 0:
            S -= p * math.log(p)
    return BOLTZMANN * S


def mixing_entropy(n1: float, n2: float) -> float:
    """
    Calculate entropy of mixing for ideal gases.

    ΔS_mix = -R * (n1*ln(x1) + n2*ln(x2))

    Args:
        n1: Moles of component 1
        n2: Moles of component 2

    Returns:
        Mixing entropy (J/K)
    """
    n_total = n1 + n2
    x1 = n1 / n_total
    x2 = n2 / n_total

    return -GAS_CONSTANT * (n1 * math.log(x1) + n2 * math.log(x2))


# =============================================================================
# QUANTUM STATISTICS
# =============================================================================

def fermi_energy_3d(n: float, m: float) -> float:
    """
    Calculate Fermi energy for 3D free electron gas.

    E_F = (ℏ²/2m) * (3π²n)^(2/3)

    Args:
        n: Number density (m⁻³)
        m: Particle mass (kg)

    Returns:
        Fermi energy (J)
    """
    return (HBAR ** 2 / (2 * m)) * (3 * math.pi ** 2 * n) ** (2/3)


def fermi_temperature(E_F: float) -> float:
    """
    Calculate Fermi temperature.

    T_F = E_F / k

    Args:
        E_F: Fermi energy (J)

    Returns:
        Fermi temperature (K)
    """
    return E_F / BOLTZMANN


def bose_einstein_condensation_temperature(n: float, m: float) -> float:
    """
    Calculate Bose-Einstein condensation temperature.

    T_c = (2πℏ²/mk) * (n/ζ(3/2))^(2/3)

    where ζ(3/2) ≈ 2.612

    Args:
        n: Number density (m⁻³)
        m: Particle mass (kg)

    Returns:
        Critical temperature (K)
    """
    zeta_3_2 = 2.612  # Riemann zeta function at 3/2
    return (2 * math.pi * HBAR ** 2 / (m * BOLTZMANN)) * \
           (n / zeta_3_2) ** (2/3)


def debye_temperature_from_speed(v_s: float, n: float) -> float:
    """
    Calculate Debye temperature from speed of sound.

    θ_D = (ℏv_s/k) * (6π²n)^(1/3)

    Args:
        v_s: Speed of sound (m/s)
        n: Number density of atoms (m⁻³)

    Returns:
        Debye temperature (K)
    """
    return (HBAR * v_s / BOLTZMANN) * (6 * math.pi ** 2 * n) ** (1/3)


def debye_heat_capacity(T: float, theta_D: float, N: int = 1) -> float:
    """
    Calculate heat capacity using Debye model.

    C_V = 9Nk * (T/θ_D)³ * ∫₀^(θ_D/T) (x⁴e^x/(e^x-1)²) dx

    Args:
        T: Temperature (K)
        theta_D: Debye temperature (K)
        N: Number of atoms

    Returns:
        Heat capacity (J/K)
    """
    x_max = theta_D / T

    # High temperature limit
    if x_max < 0.1:
        return 3 * N * BOLTZMANN

    # Low temperature limit (Debye T³ law)
    if x_max > 10:
        return (12 * math.pi ** 4 / 5) * N * BOLTZMANN * (T / theta_D) ** 3

    # Numerical integration (Simpson's rule)
    def integrand(x):
        if x < 1e-10:
            return 0
        ex = math.exp(x)
        if ex > 1e300:
            return 0
        return x ** 4 * ex / (ex - 1) ** 2

    # Integrate from 0 to x_max
    n_steps = 1000
    dx = x_max / n_steps
    integral = 0

    for i in range(n_steps):
        x1 = i * dx
        x2 = (i + 0.5) * dx
        x3 = (i + 1) * dx
        integral += dx / 6 * (integrand(x1) + 4 * integrand(x2) + integrand(x3))

    return 9 * N * BOLTZMANN * (T / theta_D) ** 3 * integral


# =============================================================================
# PHASE TRANSITIONS
# =============================================================================

def clausius_clapeyron(dP_dT: float, T: float, delta_V: float) -> float:
    """
    Calculate latent heat from Clausius-Clapeyron equation.

    dP/dT = L / (T * ΔV)
    L = T * ΔV * dP/dT

    Args:
        dP_dT: Pressure-temperature slope (Pa/K)
        T: Temperature (K)
        delta_V: Volume change per mole (m³/mol)

    Returns:
        Latent heat (J/mol)
    """
    return T * delta_V * dP_dT


def vapor_pressure_antoine(A: float, B: float, C: float, T: float) -> float:
    """
    Calculate vapor pressure using Antoine equation.

    log₁₀(P) = A - B/(C + T)

    Args:
        A, B, C: Antoine coefficients (pressure in mmHg, T in °C typically)
        T: Temperature (in units matching C)

    Returns:
        Vapor pressure (in units matching A)
    """
    return 10 ** (A - B / (C + T))


def ising_critical_temperature_2d(J: float) -> float:
    """
    Calculate critical temperature for 2D Ising model.

    T_c = 2J / (k * ln(1 + √2))

    Args:
        J: Exchange coupling energy (J)

    Returns:
        Critical temperature (K)
    """
    return 2 * J / (BOLTZMANN * math.log(1 + math.sqrt(2)))


def landau_order_parameter(T: float, T_c: float, beta: float = 0.5) -> float:
    """
    Calculate order parameter near phase transition (Landau theory).

    η = (1 - T/T_c)^β for T < T_c
    η = 0 for T ≥ T_c

    Args:
        T: Temperature (K)
        T_c: Critical temperature (K)
        beta: Critical exponent (0.5 for mean field)

    Returns:
        Order parameter (dimensionless)
    """
    if T >= T_c:
        return 0
    return (1 - T / T_c) ** beta


# =============================================================================
# COMPREHENSIVE STATISTICAL MECHANICS CALCULATION
# =============================================================================

def statistical_mechanics(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive statistical mechanics calculation.

    Args:
        params: Dictionary with relevant parameters such as:
            - mass: Particle mass (kg)
            - temperature: Temperature (K)
            - volume: Volume (m³)
            - number_density: n (m⁻³)
            - particle_type: 'classical', 'fermion', 'boson'
            - energy: Energy for distribution (J)
            - chemical_potential: μ (J)

    Returns:
        Dictionary with computed statistical mechanical properties
    """
    results = {}

    T = params.get('temperature', 300)
    m = params.get('mass', 1.67e-27)  # Default: ~proton mass
    V = params.get('volume', 1e-3)    # Default: 1 liter

    results['temperature_K'] = T
    results['kT_J'] = BOLTZMANN * T
    results['kT_eV'] = BOLTZMANN * T / 1.602e-19

    # Thermal wavelength
    lambda_th = thermal_wavelength(m, T)
    results['thermal_wavelength_m'] = lambda_th

    # Translational partition function
    Z_trans = translational_partition_function(m, V, T)
    results['Z_translational'] = Z_trans

    # Characteristic speeds
    results['most_probable_speed_m_s'] = most_probable_speed(m, T)
    results['mean_speed_m_s'] = mean_speed(m, T)
    results['rms_speed_m_s'] = rms_speed(m, T)

    # Average energy
    results['avg_kinetic_energy_J'] = equipartition_energy(3, T)  # 3 trans DOF

    # Quantum statistics
    particle_type = params.get('particle_type', 'classical')
    n = params.get('number_density')

    if n and particle_type == 'fermion':
        E_F = fermi_energy_3d(n, m)
        T_F = fermi_temperature(E_F)
        results['fermi_energy_J'] = E_F
        results['fermi_energy_eV'] = E_F / 1.602e-19
        results['fermi_temperature_K'] = T_F
        results['degeneracy_parameter_T_TF'] = T / T_F

    elif n and particle_type == 'boson':
        T_c = bose_einstein_condensation_temperature(n, m)
        results['BEC_critical_temperature_K'] = T_c
        if T < T_c:
            results['condensate_fraction'] = 1 - (T / T_c) ** 1.5

    # Distribution at specific energy
    if 'energy' in params:
        E = params['energy']
        mu = params.get('chemical_potential', 0)

        results['MB_energy_distribution'] = maxwell_boltzmann_energy_distribution(E, T)

        if particle_type == 'fermion':
            results['FD_occupation'] = fermi_dirac_distribution(E, mu, T)
        elif particle_type == 'boson' and E > mu:
            results['BE_occupation'] = bose_einstein_distribution(E, mu, T)

    # Blackbody radiation
    if 'frequency' in params:
        nu = params['frequency']
        results['planck_occupation'] = planck_distribution(nu, T)
        results['spectral_radiance_W_m2_sr_Hz'] = planck_spectral_radiance(nu, T)

    # Heat capacity (ideal gas)
    dof = params.get('degrees_of_freedom', 3)
    results['heat_capacity'] = heat_capacity_ideal_gas(dof)

    # Debye model
    if 'debye_temperature' in params:
        theta_D = params['debye_temperature']
        N = params.get('num_atoms', 1)
        results['debye_heat_capacity_J_K'] = debye_heat_capacity(T, theta_D, N)

    return results
