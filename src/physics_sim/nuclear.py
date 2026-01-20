#!/usr/bin/env python3
"""
Nuclear Physics Module

Comprehensive nuclear physics calculations covering:
- Radioactive decay (alpha, beta, gamma)
- Binding energy and mass defect
- Nuclear reactions and Q-values
- Cross sections and reaction rates
- Fission and fusion energy
- Radiation dosimetry

Based on established nuclear physics.
"""

import math
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass


# =============================================================================
# NUCLEAR CONSTANTS
# =============================================================================

# Fundamental constants
C = 299792458              # Speed of light (m/s)
PLANCK = 6.62607015e-34    # Planck constant (J·s)
HBAR = PLANCK / (2 * math.pi)

# Atomic mass unit
AMU = 1.66053906660e-27    # kg
AMU_MEV = 931.49410242     # MeV/c²

# Particle masses (kg)
ELECTRON_MASS = 9.10938370e-31
PROTON_MASS = 1.67262192e-27
NEUTRON_MASS = 1.67493e-27

# Particle masses (MeV/c²)
ELECTRON_MASS_MEV = 0.51099895
PROTON_MASS_MEV = 938.27208816
NEUTRON_MASS_MEV = 939.56542052

# Elementary charge
E_CHARGE = 1.602176634e-19  # C

# Nuclear constants
R0 = 1.2e-15  # Nuclear radius parameter (m)
A0 = 15.56    # Volume term (MeV)
A1 = 17.23    # Surface term (MeV)
A2 = 0.697    # Coulomb term (MeV)
A3 = 23.285   # Asymmetry term (MeV)
A4 = 12.0     # Pairing term (MeV)

# Decay constants
LN2 = math.log(2)


# =============================================================================
# NUCLIDE DATA
# =============================================================================

@dataclass
class Nuclide:
    """Nuclear species data."""
    symbol: str
    Z: int          # Atomic number (protons)
    A: int          # Mass number (protons + neutrons)
    mass_amu: float # Atomic mass in AMU
    half_life: Optional[float] = None  # seconds (None = stable)
    decay_mode: Optional[str] = None   # alpha, beta-, beta+, EC, etc.


# Common nuclides (subset)
NUCLIDES = {
    'H-1': Nuclide('H', 1, 1, 1.00782503207),
    'H-2': Nuclide('D', 1, 2, 2.01410177785),
    'H-3': Nuclide('T', 1, 3, 3.0160492777, 3.888e8, 'beta-'),  # 12.32 years
    'He-3': Nuclide('He', 2, 3, 3.0160293191),
    'He-4': Nuclide('He', 2, 4, 4.00260325415),
    'Li-6': Nuclide('Li', 3, 6, 6.015122795),
    'Li-7': Nuclide('Li', 3, 7, 7.01600455),
    'C-12': Nuclide('C', 6, 12, 12.0),
    'C-14': Nuclide('C', 6, 14, 14.003241989, 1.8e11, 'beta-'),  # 5730 years
    'N-14': Nuclide('N', 7, 14, 14.0030740048),
    'O-16': Nuclide('O', 8, 16, 15.99491461956),
    'Fe-56': Nuclide('Fe', 26, 56, 55.9349375),
    'Co-60': Nuclide('Co', 27, 60, 59.9338171, 1.66e8, 'beta-'),  # 5.27 years
    'Sr-90': Nuclide('Sr', 38, 90, 89.907738, 9.12e8, 'beta-'),  # 28.9 years
    'Cs-137': Nuclide('Cs', 55, 137, 136.9070895, 9.50e8, 'beta-'),  # 30.1 years
    'U-235': Nuclide('U', 92, 235, 235.0439299, 2.22e16, 'alpha'),
    'U-238': Nuclide('U', 92, 238, 238.0507882, 1.41e17, 'alpha'),
    'Pu-239': Nuclide('Pu', 94, 239, 239.0521634, 7.60e11, 'alpha'),
}


# =============================================================================
# RADIOACTIVE DECAY
# =============================================================================

def decay_constant(half_life: float) -> float:
    """
    Calculate decay constant from half-life.

    λ = ln(2) / t_½

    Args:
        half_life: Half-life in seconds

    Returns:
        Decay constant (s⁻¹)
    """
    return LN2 / half_life


def half_life_from_decay_constant(lambda_decay: float) -> float:
    """
    Calculate half-life from decay constant.

    t_½ = ln(2) / λ

    Args:
        lambda_decay: Decay constant (s⁻¹)

    Returns:
        Half-life in seconds
    """
    return LN2 / lambda_decay


def remaining_nuclei(N0: float, lambda_decay: float, time: float) -> float:
    """
    Calculate number of remaining nuclei after decay.

    N(t) = N₀ * e^(-λt)

    Args:
        N0: Initial number of nuclei
        lambda_decay: Decay constant (s⁻¹)
        time: Time elapsed (s)

    Returns:
        Number of remaining nuclei
    """
    return N0 * math.exp(-lambda_decay * time)


def remaining_fraction(half_life: float, time: float) -> float:
    """
    Calculate fraction of nuclei remaining.

    N/N₀ = (1/2)^(t/t_½) = e^(-λt)

    Args:
        half_life: Half-life (s)
        time: Time elapsed (s)

    Returns:
        Fraction remaining
    """
    return 0.5 ** (time / half_life)


def activity(N: float, lambda_decay: float) -> float:
    """
    Calculate activity (decay rate).

    A = λN (decays per second = Becquerels)

    Args:
        N: Number of nuclei
        lambda_decay: Decay constant (s⁻¹)

    Returns:
        Activity in Becquerels (Bq)
    """
    return lambda_decay * N


def activity_curies(activity_bq: float) -> float:
    """
    Convert activity from Becquerels to Curies.

    1 Ci = 3.7×10¹⁰ Bq

    Args:
        activity_bq: Activity in Becquerels

    Returns:
        Activity in Curies
    """
    return activity_bq / 3.7e10


def specific_activity(lambda_decay: float, molar_mass: float) -> float:
    """
    Calculate specific activity (activity per unit mass).

    a = λ * N_A / M

    Args:
        lambda_decay: Decay constant (s⁻¹)
        molar_mass: Molar mass (g/mol)

    Returns:
        Specific activity (Bq/g)
    """
    AVOGADRO = 6.02214076e23
    return lambda_decay * AVOGADRO / molar_mass


def mean_lifetime(half_life: float) -> float:
    """
    Calculate mean lifetime.

    τ = t_½ / ln(2) = 1/λ

    Args:
        half_life: Half-life (s)

    Returns:
        Mean lifetime (s)
    """
    return half_life / LN2


def time_for_remaining_fraction(half_life: float, fraction: float) -> float:
    """
    Calculate time for a given fraction to remain.

    t = -t_½ * ln(fraction) / ln(2)

    Args:
        half_life: Half-life (s)
        fraction: Desired remaining fraction (0 to 1)

    Returns:
        Time required (s)
    """
    if fraction <= 0 or fraction > 1:
        raise ValueError("Fraction must be between 0 and 1")
    return -half_life * math.log(fraction) / LN2


# =============================================================================
# DECAY CHAIN
# =============================================================================

def bateman_equation(N1_0: float, lambda1: float, lambda2: float,
                    time: float) -> Tuple[float, float]:
    """
    Solve Bateman equations for simple two-step decay chain.

    A → B → C (stable)

    Args:
        N1_0: Initial number of parent nuclei
        lambda1: Decay constant of parent (s⁻¹)
        lambda2: Decay constant of daughter (s⁻¹)
        time: Time elapsed (s)

    Returns:
        Tuple of (N1, N2) - number of parent and daughter nuclei
    """
    # Parent: N1(t) = N1_0 * exp(-λ1*t)
    N1 = N1_0 * math.exp(-lambda1 * time)

    # Daughter: N2(t) = N1_0 * λ1/(λ2-λ1) * [exp(-λ1*t) - exp(-λ2*t)]
    if abs(lambda1 - lambda2) < 1e-20:
        # Secular equilibrium case
        N2 = N1_0 * lambda1 * time * math.exp(-lambda1 * time)
    else:
        N2 = N1_0 * lambda1 / (lambda2 - lambda1) * \
             (math.exp(-lambda1 * time) - math.exp(-lambda2 * time))

    return N1, N2


def secular_equilibrium_ratio(lambda_parent: float,
                             lambda_daughter: float) -> Optional[float]:
    """
    Calculate activity ratio at secular equilibrium.

    Valid when λ_parent << λ_daughter.
    At equilibrium: A_daughter ≈ A_parent

    Args:
        lambda_parent: Parent decay constant (s⁻¹)
        lambda_daughter: Daughter decay constant (s⁻¹)

    Returns:
        N_daughter / N_parent ratio, or None if not applicable
    """
    if lambda_parent >= lambda_daughter:
        return None  # Secular equilibrium not applicable
    return lambda_parent / (lambda_daughter - lambda_parent)


# =============================================================================
# NUCLEAR BINDING ENERGY
# =============================================================================

def nuclear_radius(A: int) -> float:
    """
    Calculate nuclear radius (liquid drop model).

    R = R₀ * A^(1/3)

    Args:
        A: Mass number

    Returns:
        Nuclear radius (m)
    """
    return R0 * A ** (1/3)


def binding_energy_semi_empirical(Z: int, A: int) -> float:
    """
    Calculate binding energy using semi-empirical mass formula (Bethe-Weizsäcker).

    B = a_V*A - a_S*A^(2/3) - a_C*Z(Z-1)/A^(1/3) - a_A*(A-2Z)²/A + δ(A,Z)

    Args:
        Z: Atomic number (protons)
        A: Mass number (protons + neutrons)

    Returns:
        Binding energy (MeV)
    """
    N = A - Z  # Neutrons

    # Volume term (attractive)
    B_V = A0 * A

    # Surface term (reduces binding at surface)
    B_S = A1 * A ** (2/3)

    # Coulomb term (proton repulsion)
    B_C = A2 * Z * (Z - 1) / A ** (1/3)

    # Asymmetry term (N≠Z penalty)
    B_A = A3 * (A - 2 * Z) ** 2 / A

    # Pairing term
    if A % 2 == 1:
        delta = 0  # Odd A
    elif Z % 2 == 0 and N % 2 == 0:
        delta = A4 / A ** 0.5  # Even-even (more stable)
    else:
        delta = -A4 / A ** 0.5  # Odd-odd (less stable)

    return B_V - B_S - B_C - B_A + delta


def binding_energy_per_nucleon(Z: int, A: int) -> float:
    """
    Calculate binding energy per nucleon.

    B/A is maximum around Fe-56 (peak stability).

    Args:
        Z: Atomic number
        A: Mass number

    Returns:
        Binding energy per nucleon (MeV)
    """
    B = binding_energy_semi_empirical(Z, A)
    return B / A


def mass_defect(Z: int, A: int, nuclear_mass: float = None) -> float:
    """
    Calculate mass defect.

    Δm = Z*m_p + N*m_n - M_nucleus

    Args:
        Z: Atomic number
        A: Mass number
        nuclear_mass: Actual nuclear mass (kg), or None to calculate from B

    Returns:
        Mass defect (kg)
    """
    N = A - Z
    component_mass = Z * PROTON_MASS + N * NEUTRON_MASS

    if nuclear_mass is not None:
        return component_mass - nuclear_mass
    else:
        # Calculate from binding energy
        B = binding_energy_semi_empirical(Z, A)
        B_joules = B * 1e6 * E_CHARGE
        delta_m = B_joules / C ** 2
        return delta_m


def mass_to_energy(mass_kg: float) -> float:
    """
    Convert mass to energy (E = mc²).

    Args:
        mass_kg: Mass in kilograms

    Returns:
        Energy in MeV
    """
    E_joules = mass_kg * C ** 2
    return E_joules / (1e6 * E_CHARGE)


# =============================================================================
# NUCLEAR REACTIONS
# =============================================================================

def q_value(mass_reactants: float, mass_products: float) -> float:
    """
    Calculate Q-value of nuclear reaction.

    Q = (Σm_reactants - Σm_products) * c²

    Positive Q → exothermic (releases energy)
    Negative Q → endothermic (requires energy)

    Args:
        mass_reactants: Total mass of reactants (AMU)
        mass_products: Total mass of products (AMU)

    Returns:
        Q-value (MeV)
    """
    delta_m = mass_reactants - mass_products
    return delta_m * AMU_MEV


def threshold_energy(Q: float, m_projectile: float, m_target: float,
                    m_heavy_product: float) -> float:
    """
    Calculate threshold energy for endothermic reaction.

    E_th = -Q * (1 + m_a/m_A + (m_a + m_A - m_b)/(2*m_A))

    Simplified: E_th ≈ -Q * (m_a + m_A) / m_A (for |Q| << masses)

    Args:
        Q: Q-value (MeV, negative for endothermic)
        m_projectile: Projectile mass (AMU)
        m_target: Target mass (AMU)
        m_heavy_product: Heavy product mass (AMU)

    Returns:
        Threshold kinetic energy (MeV)
    """
    if Q >= 0:
        return 0  # Exothermic, no threshold

    # Simplified formula
    return -Q * (m_projectile + m_target) / m_target


def coulomb_barrier(Z1: int, Z2: int, A1: int, A2: int) -> float:
    """
    Calculate Coulomb barrier for charged particle reaction.

    V_C = k * Z1 * Z2 * e² / (R1 + R2)

    Args:
        Z1, Z2: Atomic numbers
        A1, A2: Mass numbers

    Returns:
        Coulomb barrier height (MeV)
    """
    R1 = nuclear_radius(A1)
    R2 = nuclear_radius(A2)
    R = R1 + R2

    # V = k * e² * Z1 * Z2 / R
    k = 8.9875517923e9  # Coulomb constant
    V_joules = k * E_CHARGE ** 2 * Z1 * Z2 / R

    return V_joules / (1e6 * E_CHARGE)


# =============================================================================
# CROSS SECTIONS
# =============================================================================

def geometric_cross_section(A: int) -> float:
    """
    Calculate geometric cross section.

    σ_geom = π * R² = π * R₀² * A^(2/3)

    Args:
        A: Mass number

    Returns:
        Geometric cross section (barns, 1 barn = 10⁻²⁴ cm²)
    """
    R = nuclear_radius(A)
    sigma_m2 = math.pi * R ** 2
    sigma_barns = sigma_m2 / 1e-28
    return sigma_barns


def reaction_rate(sigma: float, flux: float, N_target: float) -> float:
    """
    Calculate reaction rate.

    R = σ * Φ * N

    Args:
        sigma: Cross section (barns)
        flux: Particle flux (particles/cm²/s)
        N_target: Number of target nuclei

    Returns:
        Reaction rate (reactions/s)
    """
    sigma_cm2 = sigma * 1e-24
    return sigma_cm2 * flux * N_target


def breit_wigner(E: float, E_r: float, Gamma: float, g: float,
                Gamma_i: float, Gamma_f: float) -> float:
    """
    Breit-Wigner resonance cross section formula.

    σ(E) = π * λ² * g * (Γ_i * Γ_f) / [(E - E_r)² + (Γ/2)²]

    Args:
        E: Incident energy (MeV)
        E_r: Resonance energy (MeV)
        Gamma: Total width (MeV)
        g: Statistical factor
        Gamma_i: Partial width for entrance channel (MeV)
        Gamma_f: Partial width for exit channel (MeV)

    Returns:
        Cross section (barns)
    """
    # de Broglie wavelength (need to know projectile mass - use reduced mass approximation)
    # For simplicity, use non-relativistic: λ_bar = ℏ / sqrt(2*m*E)
    # This is a simplified version
    lambda_bar = 2.87e-12 / math.sqrt(E)  # Approximate for nucleons, in cm

    numerator = Gamma_i * Gamma_f
    denominator = (E - E_r) ** 2 + (Gamma / 2) ** 2

    sigma_cm2 = math.pi * lambda_bar ** 2 * g * numerator / denominator
    return sigma_cm2 / 1e-24  # Convert to barns


# =============================================================================
# FISSION AND FUSION
# =============================================================================

def fission_energy_U235() -> Dict[str, float]:
    """
    Energy release from U-235 fission (typical values).

    Returns:
        Dictionary with energy breakdown (MeV)
    """
    return {
        'kinetic_fission_fragments': 165.0,
        'prompt_neutrons': 5.0,
        'prompt_gammas': 7.0,
        'beta_particles': 7.0,
        'antineutrinos': 10.0,  # Not recoverable
        'delayed_gammas': 6.0,
        'total_recoverable': 190.0,
        'total_release': 200.0,
    }


def fusion_energy_DT() -> Dict[str, float]:
    """
    Energy release from D-T fusion.

    D + T → He-4 + n + 17.6 MeV

    Returns:
        Dictionary with energy breakdown
    """
    return {
        'q_value_MeV': 17.59,
        'neutron_energy_MeV': 14.07,
        'alpha_energy_MeV': 3.52,
        'reaction': 'D + T → He-4 + n',
    }


def fusion_energy_DD() -> Dict[str, float]:
    """
    Energy release from D-D fusion (two branches).

    D + D → He-3 + n + 3.27 MeV (50%)
    D + D → T + p + 4.03 MeV (50%)

    Returns:
        Dictionary with energy for both branches
    """
    return {
        'branch1_q_value_MeV': 3.27,
        'branch1_reaction': 'D + D → He-3 + n',
        'branch2_q_value_MeV': 4.03,
        'branch2_reaction': 'D + D → T + p',
        'average_q_value_MeV': 3.65,
    }


def fusion_triple_alpha() -> Dict[str, float]:
    """
    Triple-alpha process (stellar nucleosynthesis).

    3 He-4 → C-12 + 7.27 MeV

    Returns:
        Dictionary with reaction details
    """
    return {
        'q_value_MeV': 7.27,
        'reaction': '3 He-4 → C-12',
        'resonance_energy_MeV': 7.65,  # Hoyle state
    }


def lawson_criterion_DT(T_keV: float) -> float:
    """
    Lawson criterion for D-T fusion ignition.

    n * τ_E > f(T) for ignition

    Minimum at ~15 keV: n*τ ≈ 1.5×10²⁰ m⁻³·s

    Args:
        T_keV: Ion temperature in keV

    Returns:
        Required n*τ (m⁻³·s)
    """
    # Approximate fit to Lawson curve for D-T
    # Minimum around 15-25 keV
    if T_keV < 1:
        return float('inf')

    # Simplified fit
    n_tau_min = 1.5e20  # At optimal temperature

    # Crude approximation of temperature dependence
    optimal_T = 15.0
    factor = 1 + 3 * ((T_keV - optimal_T) / optimal_T) ** 2

    return n_tau_min * factor


# =============================================================================
# RADIATION DOSIMETRY
# =============================================================================

def absorbed_dose_gray(energy_J: float, mass_kg: float) -> float:
    """
    Calculate absorbed dose.

    D = E / m

    Args:
        energy_J: Energy deposited (J)
        mass_kg: Mass of absorbing material (kg)

    Returns:
        Absorbed dose (Gray)
    """
    return energy_J / mass_kg


def equivalent_dose_sievert(absorbed_dose_Gy: float,
                           radiation_weighting_factor: float) -> float:
    """
    Calculate equivalent dose.

    H = D * w_R

    Args:
        absorbed_dose_Gy: Absorbed dose (Gray)
        radiation_weighting_factor: w_R (1 for photons/electrons, 20 for alpha)

    Returns:
        Equivalent dose (Sievert)
    """
    return absorbed_dose_Gy * radiation_weighting_factor


# Radiation weighting factors (ICRP)
RADIATION_WEIGHTING_FACTORS = {
    'photons': 1,
    'electrons': 1,
    'muons': 1,
    'protons': 2,
    'alpha': 20,
    'heavy_ions': 20,
    'neutrons_thermal': 2.5,
    'neutrons_slow': 5,
    'neutrons_fast': 10,
    'neutrons_high': 5,
}


def half_value_layer(mu: float) -> float:
    """
    Calculate half-value layer (HVL) for shielding.

    HVL = ln(2) / μ

    Args:
        mu: Linear attenuation coefficient (m⁻¹)

    Returns:
        Half-value layer thickness (m)
    """
    return LN2 / mu


def intensity_after_shielding(I0: float, mu: float, x: float) -> float:
    """
    Calculate radiation intensity after shielding.

    I = I₀ * exp(-μx)

    Args:
        I0: Initial intensity
        mu: Linear attenuation coefficient (m⁻¹)
        x: Shield thickness (m)

    Returns:
        Transmitted intensity
    """
    return I0 * math.exp(-mu * x)


# =============================================================================
# COMPREHENSIVE NUCLEAR PHYSICS CALCULATION
# =============================================================================

def nuclear_physics(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive nuclear physics calculation.

    Args:
        params: Dictionary with relevant parameters such as:
            - nuclide: Nuclide name (e.g., 'U-235', 'C-14')
            - Z, A: Atomic/mass numbers (if nuclide not given)
            - initial_nuclei: For decay calculations
            - time: Time for decay calculation (s)
            - reaction_type: 'fission', 'fusion_dt', 'fusion_dd'

    Returns:
        Dictionary with computed nuclear properties
    """
    results = {}

    # Get nuclide information
    nuclide_name = params.get('nuclide')
    if nuclide_name and nuclide_name in NUCLIDES:
        nuc = NUCLIDES[nuclide_name]
        Z = nuc.Z
        A = nuc.A
        results['nuclide'] = nuclide_name
        results['symbol'] = nuc.symbol
        results['atomic_mass_amu'] = nuc.mass_amu

        if nuc.half_life:
            results['half_life_s'] = nuc.half_life
            results['half_life_years'] = nuc.half_life / (365.25 * 86400)
            results['decay_mode'] = nuc.decay_mode
            results['decay_constant_per_s'] = decay_constant(nuc.half_life)
            results['mean_lifetime_s'] = mean_lifetime(nuc.half_life)
        else:
            results['stable'] = True
    else:
        Z = params.get('Z', 26)
        A = params.get('A', 56)

    results['Z'] = Z
    results['A'] = A
    results['N'] = A - Z

    # Nuclear properties
    results['nuclear_radius_m'] = nuclear_radius(A)
    results['nuclear_radius_fm'] = nuclear_radius(A) * 1e15

    # Binding energy
    B = binding_energy_semi_empirical(Z, A)
    results['binding_energy_MeV'] = B
    results['binding_energy_per_nucleon_MeV'] = B / A
    results['mass_defect_kg'] = mass_defect(Z, A)
    results['mass_defect_amu'] = mass_defect(Z, A) / AMU

    # Geometric cross section
    results['geometric_cross_section_barns'] = geometric_cross_section(A)

    # Decay calculations
    if 'initial_nuclei' in params and 'time' in params:
        N0 = params['initial_nuclei']
        t = params['time']

        if nuclide_name and nuclide_name in NUCLIDES:
            nuc = NUCLIDES[nuclide_name]
            if nuc.half_life:
                lambda_d = decay_constant(nuc.half_life)
                N_remaining = remaining_nuclei(N0, lambda_d, t)
                A_activity = activity(N_remaining, lambda_d)

                results['nuclei_remaining'] = N_remaining
                results['nuclei_decayed'] = N0 - N_remaining
                results['fraction_remaining'] = N_remaining / N0
                results['activity_Bq'] = A_activity
                results['activity_Ci'] = activity_curies(A_activity)

    # Reaction energies
    reaction_type = params.get('reaction_type')
    if reaction_type == 'fission':
        results['fission_energy'] = fission_energy_U235()
    elif reaction_type == 'fusion_dt':
        results['fusion_energy'] = fusion_energy_DT()
    elif reaction_type == 'fusion_dd':
        results['fusion_energy'] = fusion_energy_DD()
    elif reaction_type == 'triple_alpha':
        results['fusion_energy'] = fusion_triple_alpha()

    # Coulomb barrier (if two nuclei specified)
    if 'Z2' in params and 'A2' in params:
        Z2 = params['Z2']
        A2 = params['A2']
        results['coulomb_barrier_MeV'] = coulomb_barrier(Z, Z2, A, A2)

    # Lawson criterion for fusion
    if 'ion_temperature_keV' in params:
        T_keV = params['ion_temperature_keV']
        results['lawson_n_tau_m3_s'] = lawson_criterion_DT(T_keV)

    return results
