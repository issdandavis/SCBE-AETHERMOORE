"""
Physics Simulation Core

Real physics calculations using established formulas and constants.
No pseudoscience - only textbook physics.
"""

import json
import math
import cmath
from typing import Dict, Any, Optional

# =============================================================================
# PHYSICAL CONSTANTS (CODATA 2018 values)
# =============================================================================

PLANCK = 6.62607015e-34      # Planck's constant (J·s)
HBAR = PLANCK / (2 * math.pi) # Reduced Planck constant (J·s)
C = 299792458                 # Speed of light in vacuum (m/s)
G = 6.67430e-11              # Gravitational constant (m³/(kg·s²))
ELECTRON_MASS = 9.10938356e-31   # Electron mass (kg)
PROTON_MASS = 1.6726219e-27      # Proton mass (kg)
NEUTRON_MASS = 1.67493e-27       # Neutron mass (kg)
ELEMENTARY_CHARGE = 1.602176634e-19  # Elementary charge (C)
BOLTZMANN = 1.380649e-23     # Boltzmann constant (J/K)
AVOGADRO = 6.02214076e23     # Avogadro's number (mol⁻¹)
GAS_CONSTANT = 8.314462618   # Molar gas constant (J/(mol·K))
COULOMB_K = 8.9875517923e9   # Coulomb's constant (N·m²/C²)
VACUUM_PERMITTIVITY = 8.8541878128e-12  # ε₀ (F/m)
VACUUM_PERMEABILITY = 1.25663706212e-6  # μ₀ (H/m)
STEFAN_BOLTZMANN = 5.670374419e-8  # Stefan-Boltzmann constant (W/(m²·K⁴))
FINE_STRUCTURE = 7.2973525693e-3  # Fine-structure constant α
RYDBERG = 1.0973731568160e7  # Rydberg constant (m⁻¹)


# =============================================================================
# CLASSICAL MECHANICS
# =============================================================================

def classical_mechanics(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classical Newtonian mechanics calculations.

    Supported calculations:
    - Newton's second law: F = ma
    - Kinematics: v = v₀ + at, x = v₀t + ½at²
    - Gravitational force: F = Gm₁m₂/r²
    - Kinetic energy: KE = ½mv²
    - Potential energy: PE = mgh
    - Work: W = F·d
    - Momentum: p = mv
    - Circular motion: a = v²/r, F = mv²/r
    """
    results = {}

    # Newton's Second Law: F = ma
    if 'mass' in params and 'acceleration' in params:
        force = params['mass'] * params['acceleration']
        results['force'] = force
        results['force_unit'] = 'N'

    # Kinematics equations
    if 'initial_velocity' in params and 'acceleration' in params and 'time' in params:
        v0 = params['initial_velocity']
        a = params['acceleration']
        t = params['time']

        # v = v₀ + at
        velocity = v0 + a * t
        # x = v₀t + ½at²
        displacement = v0 * t + 0.5 * a * t**2
        # v² = v₀² + 2ax (solve for v)
        v_squared = v0**2 + 2 * a * displacement

        results['final_velocity'] = velocity
        results['displacement'] = displacement
        results['velocity_squared'] = v_squared

    # Gravitational Force: F = Gm₁m₂/r²
    if 'm1' in params and 'm2' in params and 'distance' in params:
        r = params['distance']
        if r > 0:
            F_grav = G * params['m1'] * params['m2'] / (r**2)
            # Gravitational potential energy: U = -Gm₁m₂/r
            U_grav = -G * params['m1'] * params['m2'] / r
            results['gravitational_force'] = F_grav
            results['gravitational_potential_energy'] = U_grav

    # Kinetic Energy: KE = ½mv²
    if 'mass' in params and 'velocity' in params:
        kinetic_energy = 0.5 * params['mass'] * params['velocity']**2
        momentum = params['mass'] * params['velocity']
        results['kinetic_energy'] = kinetic_energy
        results['momentum'] = momentum

    # Potential Energy: PE = mgh
    if 'mass' in params and 'height' in params:
        g = params.get('gravity', 9.80665)  # Standard gravity (m/s²)
        potential_energy = params['mass'] * g * params['height']
        results['potential_energy'] = potential_energy

    # Work: W = F·d·cos(θ)
    if 'force' in params and 'distance' in params:
        angle = params.get('angle', 0)  # Default: force parallel to motion
        work = params['force'] * params['distance'] * math.cos(angle)
        results['work'] = work

    # Circular Motion: a = v²/r, F = mv²/r
    if 'velocity' in params and 'radius' in params:
        v = params['velocity']
        r = params['radius']
        if r > 0:
            centripetal_acceleration = v**2 / r
            results['centripetal_acceleration'] = centripetal_acceleration
            if 'mass' in params:
                centripetal_force = params['mass'] * centripetal_acceleration
                results['centripetal_force'] = centripetal_force

    # Simple Harmonic Motion: ω = √(k/m), T = 2π√(m/k)
    if 'spring_constant' in params and 'mass' in params:
        k = params['spring_constant']
        m = params['mass']
        omega = math.sqrt(k / m)
        period = 2 * math.pi * math.sqrt(m / k)
        frequency = 1 / period
        results['angular_frequency'] = omega
        results['period'] = period
        results['frequency'] = frequency

    return results


# =============================================================================
# QUANTUM MECHANICS
# =============================================================================

def quantum_mechanics(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Quantum mechanics calculations (established theory only).

    Supported calculations:
    - Photon energy: E = hf = hc/λ
    - de Broglie wavelength: λ = h/p
    - Particle in a box energy levels
    - Hydrogen atom (Bohr model)
    - Heisenberg uncertainty principle
    - Compton scattering
    """
    results = {}

    # Photon energy: E = hf = hc/λ
    if 'frequency' in params:
        f = params['frequency']
        energy = PLANCK * f
        wavelength = C / f
        results['photon_energy_J'] = energy
        results['photon_energy_eV'] = energy / ELEMENTARY_CHARGE
        results['wavelength'] = wavelength

    if 'wavelength' in params and 'frequency' not in params:
        wavelength = params['wavelength']
        if wavelength > 0:
            energy = PLANCK * C / wavelength
            frequency = C / wavelength
            results['photon_energy_J'] = energy
            results['photon_energy_eV'] = energy / ELEMENTARY_CHARGE
            results['frequency'] = frequency

    # de Broglie wavelength: λ = h/p
    if 'momentum' in params:
        p = params['momentum']
        if p > 0:
            wavelength = PLANCK / p
            results['de_broglie_wavelength'] = wavelength

    # de Broglie for particle with mass and velocity
    if 'particle_mass' in params and 'particle_velocity' in params:
        m = params['particle_mass']
        v = params['particle_velocity']
        p = m * v
        wavelength = PLANCK / p
        results['de_broglie_wavelength'] = wavelength
        results['particle_momentum'] = p

    # Particle in 1D infinite square well (box)
    # E_n = n²h²/(8mL²)
    if 'box_length' in params and 'quantum_number' in params:
        L = params['box_length']
        n = params['quantum_number']
        mass = params.get('particle_mass', ELECTRON_MASS)

        if L > 0 and n > 0:
            E_n = (n**2 * PLANCK**2) / (8 * mass * L**2)
            results['energy_level_J'] = E_n
            results['energy_level_eV'] = E_n / ELEMENTARY_CHARGE

            # Wave function nodes
            results['nodes'] = n - 1

    # Hydrogen atom energy levels (Bohr model)
    # E_n = -13.6 eV / n²
    if 'principal_quantum_number' in params:
        n = params['principal_quantum_number']
        if n > 0:
            E_n_eV = -13.6 / (n**2)
            E_n_J = E_n_eV * ELEMENTARY_CHARGE

            # Bohr radius for this level: r_n = n²a₀
            a0 = 5.29177210903e-11  # Bohr radius (m)
            r_n = n**2 * a0

            results['hydrogen_energy_eV'] = E_n_eV
            results['hydrogen_energy_J'] = E_n_J
            results['orbital_radius'] = r_n

    # Energy transition between levels
    if 'n_initial' in params and 'n_final' in params:
        n_i = params['n_initial']
        n_f = params['n_final']
        if n_i > 0 and n_f > 0:
            E_i = -13.6 / (n_i**2)
            E_f = -13.6 / (n_f**2)
            delta_E = E_f - E_i  # Negative = emission

            wavelength = abs(PLANCK * C / (delta_E * ELEMENTARY_CHARGE))

            results['transition_energy_eV'] = delta_E
            results['photon_wavelength'] = wavelength
            results['transition_type'] = 'emission' if delta_E < 0 else 'absorption'

    # Heisenberg Uncertainty Principle: ΔxΔp ≥ ℏ/2
    if 'position_uncertainty' in params:
        delta_x = params['position_uncertainty']
        if delta_x > 0:
            delta_p_min = HBAR / (2 * delta_x)
            results['min_momentum_uncertainty'] = delta_p_min

    if 'momentum_uncertainty' in params:
        delta_p = params['momentum_uncertainty']
        if delta_p > 0:
            delta_x_min = HBAR / (2 * delta_p)
            results['min_position_uncertainty'] = delta_x_min

    # Compton scattering: Δλ = (h/m_e c)(1 - cos θ)
    if 'scattering_angle' in params:
        theta = params['scattering_angle']
        compton_shift = (PLANCK / (ELECTRON_MASS * C)) * (1 - math.cos(theta))
        results['compton_wavelength_shift'] = compton_shift
        results['compton_wavelength_electron'] = PLANCK / (ELECTRON_MASS * C)

    return results


# =============================================================================
# ELECTROMAGNETISM
# =============================================================================

def electromagnetism(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Electromagnetic theory calculations.

    Supported calculations:
    - Coulomb's law
    - Electric field
    - Electric potential
    - Magnetic force (Lorentz)
    - Magnetic field from wire
    - Electromagnetic waves
    """
    results = {}

    # Coulomb's Law: F = kq₁q₂/r²
    if 'charge1' in params and 'charge2' in params and 'distance' in params:
        q1 = params['charge1']
        q2 = params['charge2']
        r = params['distance']
        if r > 0:
            F = COULOMB_K * q1 * q2 / (r**2)
            results['coulomb_force'] = F
            results['force_direction'] = 'repulsive' if F > 0 else 'attractive'

    # Electric field from point charge: E = kq/r²
    if 'charge' in params and 'distance' in params:
        q = params['charge']
        r = params['distance']
        if r > 0:
            E = COULOMB_K * abs(q) / (r**2)
            V = COULOMB_K * q / r  # Electric potential
            results['electric_field'] = E
            results['electric_potential'] = V

    # Electric field energy density: u = ½ε₀E²
    if 'electric_field_strength' in params:
        E = params['electric_field_strength']
        energy_density = 0.5 * VACUUM_PERMITTIVITY * E**2
        results['electric_energy_density'] = energy_density

    # Magnetic force on moving charge: F = qv × B
    if 'charge' in params and 'velocity' in params and 'magnetic_field' in params:
        q = params['charge']
        v = params['velocity']
        B = params['magnetic_field']
        angle = params.get('angle', math.pi/2)  # Default: perpendicular

        F_mag = abs(q) * v * B * math.sin(angle)
        results['magnetic_force'] = F_mag

        # Cyclotron radius: r = mv/(qB)
        if 'mass' in params:
            m = params['mass']
            if q != 0 and B != 0:
                cyclotron_radius = m * v / (abs(q) * B)
                cyclotron_freq = abs(q) * B / (2 * math.pi * m)
                results['cyclotron_radius'] = cyclotron_radius
                results['cyclotron_frequency'] = cyclotron_freq

    # Magnetic field from long straight wire: B = μ₀I/(2πr)
    if 'current' in params and 'distance' in params:
        I = params['current']
        r = params['distance']
        if r > 0:
            B = VACUUM_PERMEABILITY * I / (2 * math.pi * r)
            results['magnetic_field_from_wire'] = B

    # Electromagnetic wave: c = fλ, E = cB
    if 'em_frequency' in params:
        f = params['em_frequency']
        wavelength = C / f
        results['em_wavelength'] = wavelength

        # Classify the wave
        if wavelength < 1e-11:
            wave_type = 'gamma_ray'
        elif wavelength < 1e-8:
            wave_type = 'x_ray'
        elif wavelength < 4e-7:
            wave_type = 'ultraviolet'
        elif wavelength < 7e-7:
            wave_type = 'visible_light'
        elif wavelength < 1e-3:
            wave_type = 'infrared'
        elif wavelength < 1:
            wave_type = 'microwave'
        else:
            wave_type = 'radio_wave'

        results['wave_type'] = wave_type

    # Capacitor: C = ε₀A/d, E = ½CV²
    if 'plate_area' in params and 'plate_separation' in params:
        A = params['plate_area']
        d = params['plate_separation']
        if d > 0:
            C = VACUUM_PERMITTIVITY * A / d
            results['capacitance'] = C

            if 'voltage' in params:
                V = params['voltage']
                energy = 0.5 * C * V**2
                charge = C * V
                results['stored_energy'] = energy
                results['stored_charge'] = charge

    return results


# =============================================================================
# THERMODYNAMICS
# =============================================================================

def thermodynamics(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Thermodynamics and statistical mechanics.

    Supported calculations:
    - Ideal gas law
    - Maxwell-Boltzmann distribution
    - Black body radiation
    - Heat transfer
    - Entropy
    """
    results = {}

    # Ideal Gas Law: PV = nRT
    if 'pressure' in params and 'volume' in params and 'moles' in params:
        P = params['pressure']
        V = params['volume']
        n = params['moles']
        T = (P * V) / (n * GAS_CONSTANT)
        results['temperature'] = T

    if 'pressure' in params and 'volume' in params and 'temperature' in params:
        P = params['pressure']
        V = params['volume']
        T = params['temperature']
        n = (P * V) / (GAS_CONSTANT * T)
        results['moles'] = n
        results['molecules'] = n * AVOGADRO

    # Maxwell-Boltzmann: average kinetic energy = (3/2)kT
    if 'temperature' in params:
        T = params['temperature']
        avg_KE = (3/2) * BOLTZMANN * T
        results['average_kinetic_energy'] = avg_KE

        # RMS speed of gas molecules: v_rms = √(3kT/m)
        if 'molecular_mass' in params:
            m = params['molecular_mass']
            v_rms = math.sqrt(3 * BOLTZMANN * T / m)
            v_avg = math.sqrt(8 * BOLTZMANN * T / (math.pi * m))
            v_most_probable = math.sqrt(2 * BOLTZMANN * T / m)
            results['rms_speed'] = v_rms
            results['average_speed'] = v_avg
            results['most_probable_speed'] = v_most_probable

    # Black body radiation (Stefan-Boltzmann): P = εσAT⁴
    if 'temperature' in params and 'surface_area' in params:
        T = params['temperature']
        A = params['surface_area']
        emissivity = params.get('emissivity', 1.0)

        power = emissivity * STEFAN_BOLTZMANN * A * (T**4)
        results['radiated_power'] = power

        # Wien's displacement law: λ_max = b/T
        wien_b = 2.897771955e-3  # Wien's displacement constant (m·K)
        lambda_max = wien_b / T
        results['peak_wavelength'] = lambda_max

    # Heat transfer: Q = mcΔT
    if 'mass' in params and 'specific_heat' in params and 'temperature_change' in params:
        m = params['mass']
        c = params['specific_heat']
        delta_T = params['temperature_change']
        Q = m * c * delta_T
        results['heat_transferred'] = Q

    # Entropy change: ΔS = Q/T (reversible)
    if 'heat' in params and 'temperature' in params:
        Q = params['heat']
        T = params['temperature']
        if T > 0:
            delta_S = Q / T
            results['entropy_change'] = delta_S

    # Carnot efficiency: η = 1 - T_cold/T_hot
    if 'hot_temperature' in params and 'cold_temperature' in params:
        T_hot = params['hot_temperature']
        T_cold = params['cold_temperature']
        if T_hot > T_cold and T_hot > 0:
            efficiency = 1 - T_cold / T_hot
            results['carnot_efficiency'] = efficiency
            results['carnot_efficiency_percent'] = efficiency * 100

    return results


# =============================================================================
# RELATIVITY
# =============================================================================

def relativity(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Special and General Relativity calculations.

    Supported calculations:
    - Lorentz factor
    - Time dilation
    - Length contraction
    - Relativistic mass and energy
    - Relativistic momentum
    - Doppler effect
    """
    results = {}

    # Lorentz factor: γ = 1/√(1 - v²/c²)
    if 'velocity' in params:
        v = params['velocity']
        if abs(v) < C:
            beta = v / C
            gamma = 1 / math.sqrt(1 - beta**2)
            results['beta'] = beta
            results['lorentz_factor'] = gamma

            # Time dilation: Δt' = γΔt
            if 'proper_time' in params:
                tau = params['proper_time']
                dilated_time = gamma * tau
                results['dilated_time'] = dilated_time

            # Length contraction: L' = L/γ
            if 'proper_length' in params:
                L = params['proper_length']
                contracted = L / gamma
                results['contracted_length'] = contracted
        else:
            results['error'] = 'Velocity must be less than speed of light'

    # Mass-energy equivalence: E = mc²
    if 'mass' in params:
        m = params['mass']
        E_rest = m * C**2
        results['rest_energy_J'] = E_rest
        results['rest_energy_MeV'] = E_rest / (1e6 * ELEMENTARY_CHARGE)

        # Relativistic energy: E = γmc²
        if 'velocity' in params and abs(params['velocity']) < C:
            v = params['velocity']
            gamma = 1 / math.sqrt(1 - (v/C)**2)
            E_total = gamma * m * C**2
            E_kinetic = E_total - E_rest
            p_relativistic = gamma * m * v

            results['total_energy_J'] = E_total
            results['kinetic_energy_J'] = E_kinetic
            results['relativistic_momentum'] = p_relativistic

    # Relativistic Doppler effect
    if 'source_frequency' in params and 'velocity' in params:
        f_s = params['source_frequency']
        v = params['velocity']

        if abs(v) < C:
            # Approaching: blue shift, receding: red shift
            # f_observed = f_source * √((1 + β)/(1 - β)) for approaching
            beta = v / C  # Positive = approaching

            if beta > 0:  # Approaching
                f_obs = f_s * math.sqrt((1 + beta) / (1 - beta))
                shift_type = 'blue_shift'
            else:  # Receding
                f_obs = f_s * math.sqrt((1 + beta) / (1 - beta))
                shift_type = 'red_shift'

            results['observed_frequency'] = f_obs
            results['frequency_shift_ratio'] = f_obs / f_s
            results['shift_type'] = shift_type

    # Schwarzschild radius (black hole event horizon): r_s = 2GM/c²
    if 'black_hole_mass' in params:
        M = params['black_hole_mass']
        r_s = 2 * G * M / (C**2)
        results['schwarzschild_radius'] = r_s

        # Surface gravity at event horizon
        g_surface = C**4 / (4 * G * M)
        results['surface_gravity'] = g_surface

    return results


# =============================================================================
# LAMBDA HANDLER
# =============================================================================

def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    AWS Lambda handler for physics simulations.

    Args:
        event: Contains 'simulation_type' and 'parameters'
        context: Lambda context (optional)

    Returns:
        Response with simulation results
    """
    try:
        # Parse input
        if isinstance(event, str):
            event = json.loads(event)

        simulation_type = event.get('simulation_type', 'classical')
        params = event.get('parameters', {})

        # Dispatch to appropriate simulation
        simulations = {
            'classical': classical_mechanics,
            'quantum': quantum_mechanics,
            'electromagnetism': electromagnetism,
            'thermodynamics': thermodynamics,
            'relativity': relativity,
        }

        if simulation_type not in simulations:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Invalid simulation type: {simulation_type}',
                    'valid_types': list(simulations.keys())
                })
            }

        # Run simulation
        results = simulations[simulation_type](params)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'simulation_type': simulation_type,
                'input_parameters': params,
                'results': results,
                'constants_used': {
                    'planck_constant': PLANCK,
                    'speed_of_light': C,
                    'gravitational_constant': G,
                    'boltzmann_constant': BOLTZMANN
                }
            }, indent=2)
        }

    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Invalid JSON: {str(e)}'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Simulation error: {str(e)}'})
        }
