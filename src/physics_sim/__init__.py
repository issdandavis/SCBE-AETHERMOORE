"""
Physics Simulation Module
=========================

A comprehensive, production-grade physics simulation engine.
Real physics calculations only - no pseudoscience.

Modules:
--------
- core: Classical mechanics, quantum mechanics, electromagnetism, thermodynamics, relativity
- atmosphere: ISA model, pressure/density profiles, Mach number, compressibility
- fluids: Fluid dynamics, Reynolds number, Bernoulli, drag, compressible flow, shocks
- orbital: Kepler's laws, orbital maneuvers, Hohmann transfers, perturbations
- nuclear: Radioactive decay, binding energy, fission/fusion, cross sections
- statistical: Partition functions, distributions (MB, FD, BE), phase transitions
- waves_optics: Wave physics, interference, diffraction, geometric/physical optics
- numerical: ODE solvers (Euler, RK4, Verlet), root finding, integration, optimization
- simulator: Unified time evolution engine with N-body, springs, drag, collisions

Example Usage:
--------------
    # Classical mechanics
    from physics_sim import classical_mechanics
    result = classical_mechanics({'mass': 10, 'velocity': 5})
    print(f"Kinetic energy: {result['kinetic_energy']} J")

    # Atmospheric properties at altitude
    from physics_sim import atmosphere
    atm = atmosphere({'altitude': 10000})
    print(f"Temperature at 10km: {atm['temperature_K']} K")

    # Orbital mechanics
    from physics_sim import orbital_mechanics
    orbit = orbital_mechanics({
        'central_body': 'earth',
        'altitude': 400000,  # 400 km (ISS)
    })
    print(f"Orbital period: {orbit['period_min']:.1f} minutes")

    # Run a simulation
    from physics_sim.simulator import create_projectile_simulation
    sim = create_projectile_simulation(v0=50, angle_deg=45, with_drag=True)
    history = sim.run()
    print(f"Flight time: {history[-1]['time']:.2f} s")
"""

# Core physics functions
from .core import (
    classical_mechanics,
    quantum_mechanics,
    electromagnetism,
    thermodynamics,
    relativity,
    lambda_handler,
    # Constants
    PLANCK,
    HBAR,
    C,
    G,
    ELECTRON_MASS,
    PROTON_MASS,
    NEUTRON_MASS,
    ELEMENTARY_CHARGE,
    BOLTZMANN,
    AVOGADRO,
    GAS_CONSTANT,
    COULOMB_K,
    VACUUM_PERMITTIVITY,
    VACUUM_PERMEABILITY,
    STEFAN_BOLTZMANN,
    FINE_STRUCTURE,
    RYDBERG,
)

# Atmospheric physics
from .atmosphere import (
    atmosphere,
    isa_temperature,
    isa_pressure,
    isa_density,
    speed_of_sound,
    dynamic_viscosity,
    mach_number,
    stagnation_temperature,
    stagnation_pressure,
    dynamic_pressure,
    pressure_altitude,
    density_altitude,
)

# Fluid dynamics
from .fluids import (
    fluid_dynamics,
    reynolds_number,
    froude_number,
    weber_number,
    bernoulli_velocity,
    drag_force,
    lift_force,
    terminal_velocity,
    pipe_pressure_drop,
    isentropic_pressure_ratio,
    normal_shock_mach,
    normal_shock_pressure_ratio,
    blasius_boundary_layer_thickness,
)

# Orbital mechanics
from .orbital import (
    orbital_mechanics,
    orbital_period,
    orbital_velocity,
    circular_velocity,
    escape_velocity,
    hohmann_transfer,
    sphere_of_influence,
    j2_nodal_precession,
    sun_synchronous_inclination,
    MU_EARTH,
    MU_SUN,
    MU_MOON,
    MU_MARS,
    AU,
)

# Nuclear physics
from .nuclear import (
    nuclear_physics,
    decay_constant,
    half_life_from_decay_constant,
    remaining_nuclei,
    activity,
    binding_energy_semi_empirical,
    binding_energy_per_nucleon,
    fission_energy_U235,
    fusion_energy_DT,
    lawson_criterion_DT,
)

# Statistical mechanics
from .statistical import (
    statistical_mechanics,
    maxwell_boltzmann_speed_distribution,
    fermi_dirac_distribution,
    bose_einstein_distribution,
    planck_distribution,
    fermi_energy_3d,
    bose_einstein_condensation_temperature,
    debye_heat_capacity,
    boltzmann_entropy,
)

# Waves and optics
from .waves_optics import (
    waves_optics,
    wave_velocity,
    wavelength_from_velocity,
    snells_law,
    critical_angle,
    brewsters_angle,
    thin_lens_equation,
    young_fringe_spacing,
    single_slit_intensity,
    rayleigh_criterion,
    doppler_shift_moving_source,
    sound_speed_air,
)

# planck_spectral_radiance is in statistical module
from .statistical import planck_spectral_radiance

# Numerical methods
from .numerical import (
    numerical_methods,
    euler_step,
    euler_solve,
    rk4_step,
    rk4_solve,
    verlet_step,
    leapfrog_step,
    bisection,
    newton_raphson,
    simpson_rule,
    gauss_legendre_5,
    gradient_descent,
    particle_swarm_optimization,
    golden_section_search,
)

# Simulator
from .simulator import (
    PhysicsSimulator,
    SimulationConfig,
    IntegrationMethod,
    Particle,
    Spring,
    GravityCalculator,
    UniformGravityCalculator,
    DragCalculator,
    SpringCalculator,
    ElectrostaticCalculator,
    CentralForceCalculator,
    create_projectile_simulation,
    create_orbital_simulation,
    create_spring_pendulum_simulation,
    create_n_body_simulation,
)


__all__ = [
    # Core
    "classical_mechanics",
    "quantum_mechanics",
    "electromagnetism",
    "thermodynamics",
    "relativity",
    "lambda_handler",
    # Core constants
    "PLANCK", "HBAR", "C", "G",
    "ELECTRON_MASS", "PROTON_MASS", "NEUTRON_MASS",
    "ELEMENTARY_CHARGE", "BOLTZMANN", "AVOGADRO", "GAS_CONSTANT",
    "COULOMB_K", "VACUUM_PERMITTIVITY", "VACUUM_PERMEABILITY",
    "STEFAN_BOLTZMANN", "FINE_STRUCTURE", "RYDBERG",
    # Atmosphere
    "atmosphere",
    "isa_temperature", "isa_pressure", "isa_density",
    "speed_of_sound", "dynamic_viscosity", "mach_number",
    "stagnation_temperature", "stagnation_pressure", "dynamic_pressure",
    "pressure_altitude", "density_altitude",
    # Fluids
    "fluid_dynamics",
    "reynolds_number", "froude_number", "weber_number",
    "bernoulli_velocity", "drag_force", "lift_force", "terminal_velocity",
    "pipe_pressure_drop", "isentropic_pressure_ratio",
    "normal_shock_mach", "normal_shock_pressure_ratio",
    "blasius_boundary_layer_thickness",
    # Orbital
    "orbital_mechanics",
    "orbital_period", "orbital_velocity", "circular_velocity", "escape_velocity",
    "hohmann_transfer", "sphere_of_influence",
    "j2_nodal_precession", "sun_synchronous_inclination",
    "MU_EARTH", "MU_SUN", "MU_MOON", "MU_MARS", "AU",
    # Nuclear
    "nuclear_physics",
    "decay_constant", "half_life_from_decay_constant", "remaining_nuclei", "activity",
    "binding_energy_semi_empirical", "binding_energy_per_nucleon",
    "fission_energy_U235", "fusion_energy_DT", "lawson_criterion_DT",
    # Statistical
    "statistical_mechanics",
    "maxwell_boltzmann_speed_distribution",
    "fermi_dirac_distribution", "bose_einstein_distribution", "planck_distribution",
    "fermi_energy_3d", "bose_einstein_condensation_temperature", "debye_heat_capacity",
    "boltzmann_entropy",
    # Waves/Optics
    "waves_optics",
    "wave_velocity", "wavelength_from_velocity",
    "snells_law", "critical_angle", "brewsters_angle", "thin_lens_equation",
    "young_fringe_spacing", "single_slit_intensity", "rayleigh_criterion",
    "doppler_shift_moving_source", "sound_speed_air", "planck_spectral_radiance",
    # Numerical
    "numerical_methods",
    "euler_step", "euler_solve", "rk4_step", "rk4_solve",
    "verlet_step", "leapfrog_step",
    "bisection", "newton_raphson",
    "simpson_rule", "gauss_legendre_5",
    "gradient_descent", "particle_swarm_optimization", "golden_section_search",
    # Simulator
    "PhysicsSimulator", "SimulationConfig", "IntegrationMethod",
    "Particle", "Spring",
    "GravityCalculator", "UniformGravityCalculator", "DragCalculator",
    "SpringCalculator", "ElectrostaticCalculator", "CentralForceCalculator",
    "create_projectile_simulation", "create_orbital_simulation",
    "create_spring_pendulum_simulation", "create_n_body_simulation",
]

__version__ = "2.0.0"
__author__ = "SCBE-AETHERMOORE Physics Team"
