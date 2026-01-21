#!/usr/bin/env python3
"""
Comprehensive Physics Simulation Test Suite
============================================

Tests all physics modules against known physical values and validates
numerical accuracy, conservation laws, and edge cases.

Run with: python -m pytest src/physics_sim/test_physics_comprehensive.py -v
Or:       python src/physics_sim/test_physics_comprehensive.py
"""

import math
import sys
import os

# Add parent path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def print_test_header(name: str):
    """Print test section header."""
    print(f"\n{'='*70}")
    print(f" {name}")
    print('='*70)


def assert_close(actual, expected, tol=0.01, msg=""):
    """Assert values are within tolerance."""
    if abs(expected) > 1e-10:
        rel_error = abs(actual - expected) / abs(expected)
        assert rel_error < tol, f"{msg}: Expected {expected}, got {actual} (rel error: {rel_error:.2%})"
    else:
        assert abs(actual - expected) < tol, f"{msg}: Expected {expected}, got {actual}"


# =============================================================================
# ATMOSPHERIC PHYSICS TESTS
# =============================================================================

def test_atmosphere():
    print_test_header("ATMOSPHERIC PHYSICS TESTS")

    from src.physics_sim.atmosphere import (
        isa_temperature, isa_pressure, isa_density, speed_of_sound,
        atmosphere, mach_number
    )

    # Test 1: Sea level conditions
    T_sl = isa_temperature(0)
    P_sl = isa_pressure(0)
    rho_sl = isa_density(0)

    assert_close(T_sl, 288.15, 0.001, "Sea level temperature")
    assert_close(P_sl, 101325, 0.001, "Sea level pressure")
    assert_close(rho_sl, 1.225, 0.01, "Sea level density")
    print(f"  [OK] Sea level: T={T_sl:.2f}K, P={P_sl:.0f}Pa, rho={rho_sl:.3f}kg/m^3")

    # Test 2: Tropopause (11 km)
    T_11 = isa_temperature(11000)
    P_11 = isa_pressure(11000)

    assert_close(T_11, 216.65, 0.01, "Tropopause temperature")
    assert_close(P_11, 22632, 0.05, "Tropopause pressure")
    print(f"  [OK] Tropopause (11km): T={T_11:.2f}K, P={P_11:.0f}Pa")

    # Test 3: Speed of sound
    a_sl = speed_of_sound(288.15)
    assert_close(a_sl, 340.3, 0.01, "Speed of sound at sea level")
    print(f"  [OK] Speed of sound at sea level: {a_sl:.1f} m/s")

    # Test 4: Mach number
    M = mach_number(680, 288.15)  # Twice speed of sound
    assert_close(M, 2.0, 0.01, "Mach number")
    print(f"  [OK] Mach 2 check: M={M:.2f}")

    # Test 5: Comprehensive atmosphere function
    atm = atmosphere({'altitude': 10000, 'velocity': 250})
    assert 'temperature_K' in atm
    assert 'mach_number' in atm
    print(f"  [OK] Comprehensive test at 10km: M={atm['mach_number']:.3f}")

    print("\n[OK] All atmospheric physics tests passed")


# =============================================================================
# FLUID DYNAMICS TESTS
# =============================================================================

def test_fluids():
    print_test_header("FLUID DYNAMICS TESTS")

    from src.physics_sim.fluids import (
        reynolds_number, drag_force, bernoulli_velocity,
        normal_shock_mach, isentropic_pressure_ratio
    )

    # Test 1: Reynolds number
    # Water in pipe: V=1m/s, D=0.1m, rho=1000kg/m^3, mu=0.001Pa*s
    Re = reynolds_number(1.0, 0.1, 1000, 0.001)
    assert_close(Re, 100000, 0.01, "Reynolds number")
    print(f"  [OK] Reynolds number (pipe flow): Re={Re:.0f}")

    # Test 2: Drag force
    # Sphere in air: Cd=0.47, rho=1.225, V=10m/s, A=0.01m^2
    D = drag_force(0.47, 1.225, 10, 0.01)
    expected_D = 0.5 * 0.47 * 1.225 * 100 * 0.01
    assert_close(D, expected_D, 0.001, "Drag force")
    print(f"  [OK] Drag force: F={D:.4f}N")

    # Test 3: Bernoulli equation
    # Tank drain: P1=101325Pa, P2=101325Pa, z1=5m, z2=0, V1=0
    V2 = bernoulli_velocity(101325, 101325, 5, 0, 1000, 0)
    # Torricelli: V = sqrt(2gh) = sqrt(2*9.8*5) ~ 9.9 m/s
    assert_close(V2, math.sqrt(2 * 9.80665 * 5), 0.01, "Bernoulli velocity")
    print(f"  [OK] Bernoulli (Torricelli): V={V2:.2f} m/s")

    # Test 4: Normal shock
    # Mach 2 shock
    M2 = normal_shock_mach(2.0)
    # Known value: M2 ~ 0.5774 for M1=2, γ=1.4
    assert_close(M2, 0.5774, 0.02, "Normal shock downstream Mach")
    print(f"  [OK] Normal shock (M1=2): M2={M2:.4f}")

    # Test 5: Isentropic relations
    # At Mach 1, P/P0 = 0.5283 for γ=1.4
    P_ratio = isentropic_pressure_ratio(1.0)
    assert_close(P_ratio, 0.5283, 0.01, "Isentropic pressure ratio at M=1")
    print(f"  [OK] Isentropic P/P0 at M=1: {P_ratio:.4f}")

    print("\n[OK] All fluid dynamics tests passed")


# =============================================================================
# ORBITAL MECHANICS TESTS
# =============================================================================

def test_orbital():
    print_test_header("ORBITAL MECHANICS TESTS")

    from src.physics_sim.orbital import (
        orbital_period, circular_velocity, escape_velocity,
        hohmann_transfer, orbital_mechanics,
        MU_EARTH, RADIUS_EARTH
    )

    # Test 1: LEO orbital period (ISS at ~400km)
    r_iss = RADIUS_EARTH + 400000
    T_iss = orbital_period(r_iss, MU_EARTH)
    # ISS period ~ 92.68 minutes
    assert_close(T_iss / 60, 92.4, 0.02, "ISS orbital period")
    print(f"  [OK] ISS orbital period: {T_iss/60:.2f} minutes")

    # Test 2: Circular velocity
    V_circular = circular_velocity(r_iss, MU_EARTH)
    # Expected ~ 7.67 km/s
    assert_close(V_circular / 1000, 7.67, 0.02, "LEO circular velocity")
    print(f"  [OK] LEO circular velocity: {V_circular/1000:.2f} km/s")

    # Test 3: Escape velocity at Earth's surface
    V_escape = escape_velocity(RADIUS_EARTH, MU_EARTH)
    # Expected ~ 11.19 km/s
    assert_close(V_escape / 1000, 11.19, 0.02, "Earth escape velocity")
    print(f"  [OK] Earth escape velocity: {V_escape/1000:.2f} km/s")

    # Test 4: Hohmann transfer (LEO to GEO)
    r1 = RADIUS_EARTH + 400000   # LEO
    r2 = 42164000                 # GEO
    transfer = hohmann_transfer(r1, r2, MU_EARTH)
    # Total Delta_V for LEO->GEO ~ 3.9 km/s
    assert_close(transfer['delta_v_total_m_s'] / 1000, 3.9, 0.1, "Hohmann Delta_V")
    print(f"  [OK] Hohmann LEO->GEO: Delta_V={transfer['delta_v_total_m_s']/1000:.2f} km/s")

    # Test 5: Comprehensive orbital mechanics
    orbit = orbital_mechanics({
        'central_body': 'earth',
        'altitude': 400000,
    })
    assert 'period_min' in orbit
    assert 'escape_velocity_m_s' in orbit
    print(f"  [OK] Comprehensive orbit: T={orbit['period_min']:.1f} min, e={orbit['eccentricity']:.4f}")

    print("\n[OK] All orbital mechanics tests passed")


# =============================================================================
# NUCLEAR PHYSICS TESTS
# =============================================================================

def test_nuclear():
    print_test_header("NUCLEAR PHYSICS TESTS")

    from src.physics_sim.nuclear import (
        decay_constant, remaining_nuclei, binding_energy_per_nucleon,
        nuclear_physics, fission_energy_U235
    )

    # Test 1: C-14 decay (half-life = 5730 years)
    t_half = 5730 * 365.25 * 24 * 3600  # seconds
    lambda_c14 = decay_constant(t_half)
    # Check half-life gives 50% remaining
    N_remaining = remaining_nuclei(1000, lambda_c14, t_half)
    assert_close(N_remaining, 500, 0.001, "C-14 half-life check")
    print(f"  [OK] C-14 decay: After 5730 years, {N_remaining:.0f}/1000 remain")

    # Test 2: Binding energy per nucleon
    # Fe-56 has the highest B/A ~ 8.8 MeV
    B_per_A_Fe = binding_energy_per_nucleon(26, 56)
    assert_close(B_per_A_Fe, 8.8, 0.1, "Fe-56 binding energy per nucleon")
    print(f"  [OK] Fe-56 binding energy: {B_per_A_Fe:.2f} MeV/nucleon")

    # Test 3: U-235 fission energy
    fission = fission_energy_U235()
    assert_close(fission['total_release'], 200, 0.1, "U-235 fission energy")
    print(f"  [OK] U-235 fission: {fission['total_release']:.0f} MeV")

    # Test 4: Nuclear physics comprehensive
    nuc = nuclear_physics({
        'nuclide': 'U-235',
        'initial_nuclei': 1e20,
        'time': 1e9  # 1 billion seconds
    })
    assert 'binding_energy_MeV' in nuc
    assert 'decay_constant_per_s' in nuc
    print(f"  [OK] U-235: B={nuc['binding_energy_MeV']:.1f} MeV, lambda={nuc['decay_constant_per_s']:.2e}/s")

    print("\n[OK] All nuclear physics tests passed")


# =============================================================================
# STATISTICAL MECHANICS TESTS
# =============================================================================

def test_statistical():
    print_test_header("STATISTICAL MECHANICS TESTS")

    from src.physics_sim.statistical import (
        most_probable_speed, mean_speed, rms_speed,
        fermi_energy_3d, maxwell_boltzmann_speed_distribution,
        statistical_mechanics, BOLTZMANN
    )

    # Test 1: Maxwell-Boltzmann speeds for N2 at 300K
    m_N2 = 28 * 1.66e-27  # kg
    T = 300  # K

    v_p = most_probable_speed(m_N2, T)
    v_avg = mean_speed(m_N2, T)
    v_rms = rms_speed(m_N2, T)

    # Check ratios: v_avg/v_p ~ 1.128, v_rms/v_p ~ 1.225
    assert_close(v_avg / v_p, 1.128, 0.02, "v_avg/v_p ratio")
    assert_close(v_rms / v_p, 1.225, 0.02, "v_rms/v_p ratio")
    print(f"  [OK] N2 at 300K: v_p={v_p:.0f}, v_avg={v_avg:.0f}, v_rms={v_rms:.0f} m/s")

    # Test 2: Fermi energy for copper
    # n ~ 8.5×10^2⁸ electrons/m^3, E_F ~ 7 eV
    n_Cu = 8.5e28
    E_F = fermi_energy_3d(n_Cu, 9.109e-31)
    E_F_eV = E_F / 1.602e-19
    assert_close(E_F_eV, 7.0, 0.15, "Copper Fermi energy")
    print(f"  [OK] Copper Fermi energy: {E_F_eV:.2f} eV")

    # Test 3: MB distribution normalization (integral should be 1)
    # Approximate integral by summing
    dv = 10
    v_max = 2000
    total = sum(maxwell_boltzmann_speed_distribution(v, m_N2, T) * dv
                for v in range(1, v_max, dv))
    assert_close(total, 1.0, 0.05, "MB distribution normalization")
    print(f"  [OK] MB distribution integral: {total:.4f}")

    # Test 4: Comprehensive statistical mechanics
    stat = statistical_mechanics({
        'temperature': 300,
        'mass': m_N2,
        'volume': 0.0224,  # ~1 mol at STP
    })
    assert 'rms_speed_m_s' in stat
    print(f"  [OK] Comprehensive: v_rms={stat['rms_speed_m_s']:.0f} m/s")

    print("\n[OK] All statistical mechanics tests passed")


# =============================================================================
# WAVES AND OPTICS TESTS
# =============================================================================

def test_waves_optics():
    print_test_header("WAVES AND OPTICS TESTS")

    from src.physics_sim.waves_optics import (
        snells_law, critical_angle, thin_lens_equation,
        young_fringe_spacing, sound_speed_air, doppler_shift_moving_source,
        waves_optics
    )

    # Test 1: Snell's law (air to glass)
    # n_air=1, n_glass=1.5, θ1=45deg
    theta2 = snells_law(1.0, math.radians(45), 1.5)
    # sin(θ2) = sin(45deg)/1.5 = 0.471, θ2 ~ 28.1deg
    assert_close(math.degrees(theta2), 28.1, 0.05, "Snell's law refraction")
    print(f"  [OK] Snell's law: 45deg in air -> {math.degrees(theta2):.1f}deg in glass")

    # Test 2: Critical angle (glass to air)
    theta_c = critical_angle(1.5, 1.0)
    # sin(θc) = 1/1.5, θc ~ 41.8deg
    assert_close(math.degrees(theta_c), 41.8, 0.05, "Critical angle")
    print(f"  [OK] Critical angle (glass->air): {math.degrees(theta_c):.1f}deg")

    # Test 3: Thin lens equation
    lens = thin_lens_equation(f=0.1, d_o=0.3)  # f=10cm, object at 30cm
    # 1/di = 1/0.1 - 1/0.3 = 10 - 3.33 = 6.67, di = 0.15m
    assert_close(lens['image_distance_m'], 0.15, 0.01, "Thin lens image distance")
    print(f"  [OK] Thin lens: d_o=30cm, f=10cm -> d_i={lens['image_distance_m']*100:.0f}cm")

    # Test 4: Young's double slit fringe spacing
    # lambda=500nm, d=0.1mm, L=1m -> Delta_y=5mm
    dy = young_fringe_spacing(500e-9, 0.1e-3, 1.0)
    assert_close(dy * 1000, 5.0, 0.01, "Young's fringe spacing")
    print(f"  [OK] Young's double slit: Delta_y={dy*1000:.1f}mm")

    # Test 5: Sound speed in air
    v_sound = sound_speed_air(20)  # 20degC
    assert_close(v_sound, 343, 0.01, "Sound speed at 20degC")
    print(f"  [OK] Sound speed at 20degC: {v_sound:.1f} m/s")

    # Test 6: Doppler effect
    f_obs = doppler_shift_moving_source(1000, 30, 343, approaching=True)
    # f' = f * v/(v-vs) = 1000 * 343/313 ~ 1096 Hz
    assert_close(f_obs, 1096, 0.02, "Doppler shift")
    print(f"  [OK] Doppler (source at 30m/s approaching): {f_obs:.0f} Hz")

    print("\n[OK] All waves and optics tests passed")


# =============================================================================
# NUMERICAL METHODS TESTS
# =============================================================================

def test_numerical():
    print_test_header("NUMERICAL METHODS TESTS")

    from src.physics_sim.numerical import (
        bisection, newton_raphson, simpson_rule, rk4_solve,
        particle_swarm_optimization
    )

    # Test 1: Bisection (find sqrt2)
    root, iters = bisection(lambda x: x**2 - 2, 1, 2)
    assert_close(root, math.sqrt(2), 1e-8, "Bisection root finding")
    print(f"  [OK] Bisection: sqrt2 = {root:.10f} ({iters} iterations)")

    # Test 2: Newton-Raphson (find sqrt2)
    root, iters = newton_raphson(lambda x: x**2 - 2, lambda x: 2*x, 1.5)
    assert_close(root, math.sqrt(2), 1e-10, "Newton-Raphson root finding")
    print(f"  [OK] Newton-Raphson: sqrt2 = {root:.12f} ({iters} iterations)")

    # Test 3: Simpson integration (integralsin(x)dx from 0 to pi = 2)
    integral = simpson_rule(math.sin, 0, math.pi, n=100)
    assert_close(integral, 2.0, 1e-6, "Simpson integration")
    print(f"  [OK] Simpson: integralsin(x)dx = {integral:.10f}")

    # Test 4: RK4 ODE solver (simple harmonic oscillator)
    # x'' = -x, solution: x(t) = cos(t) for x(0)=1, v(0)=0
    def harmonic(t, y):
        return [y[1], -y[0]]

    times, states = rk4_solve(harmonic, [1.0, 0.0], (0, 2*math.pi), h=0.01)
    final_x = states[-1][0]
    # After one period, should return to x=1
    assert_close(final_x, 1.0, 0.001, "RK4 harmonic oscillator")
    print(f"  [OK] RK4 SHO: x(2pi) = {final_x:.6f} (expected 1.0)")

    # Test 5: PSO optimization (find minimum of x^2 + y^2)
    def sphere(x):
        return sum(xi**2 for xi in x)

    best_pos, best_val, _ = particle_swarm_optimization(
        sphere, [(-5, 5), (-5, 5)], n_particles=20, max_iter=50
    )
    assert_close(best_val, 0.0, 0.1, "PSO optimization")
    print(f"  [OK] PSO minimum: f({best_pos[0]:.4f}, {best_pos[1]:.4f}) = {best_val:.6f}")

    print("\n[OK] All numerical methods tests passed")


# =============================================================================
# SIMULATOR TESTS
# =============================================================================

def test_simulator():
    print_test_header("PHYSICS SIMULATOR TESTS")

    from src.physics_sim.simulator import (
        create_projectile_simulation, create_orbital_simulation,
        PhysicsSimulator, SimulationConfig, IntegrationMethod,
        Particle, GravityCalculator
    )

    # Test 1: Projectile motion (no drag)
    # v0=50m/s at 45deg should go ~255m with max height ~64m
    sim = create_projectile_simulation(v0=50, angle_deg=45, with_drag=False)

    # Run until y < 0
    while sim.particles[0].position[1] >= 0 and sim.time < 20:
        sim.step()

    range_x = sim.particles[0].position[0]
    # Theoretical range: v^2sin(2θ)/g = 2500/9.8 ~ 255m
    assert_close(range_x, 255, 0.02, "Projectile range")
    print(f"  [OK] Projectile range: {range_x:.1f}m (expected ~255m)")

    # Test 2: Energy conservation in orbital simulation
    sim2 = create_orbital_simulation(
        central_mass=5.972e24,
        orbiter_mass=1000,
        orbital_radius=7e6,
        eccentricity=0.1
    )

    E_initial = sim2.total_energy()
    for _ in range(1000):
        sim2.step()
    E_final = sim2.total_energy()

    # Energy should be conserved
    rel_error = abs(E_final[2] - E_initial[2]) / abs(E_initial[2])
    assert rel_error < 0.01, f"Energy conservation: {rel_error:.2%} error"
    print(f"  [OK] Orbital energy conservation: {rel_error:.4%} error")

    # Test 3: Two-body momentum conservation
    config = SimulationConfig(dt=0.1, t_max=10)
    sim3 = PhysicsSimulator(config)

    p1 = Particle(mass=1.0, position=[0, 0, 0], velocity=[1, 0, 0], name="P1")
    p2 = Particle(mass=1.0, position=[10, 0, 0], velocity=[-1, 0, 0], name="P2")
    sim3.add_particle(p1)
    sim3.add_particle(p2)
    sim3.add_force_calculator(GravityCalculator())

    p_initial = sim3.total_momentum()
    for _ in range(100):
        sim3.step()
    p_final = sim3.total_momentum()

    # Momentum should be conserved
    dp = sum((p_initial[i] - p_final[i])**2 for i in range(3))**0.5
    assert dp < 1e-10, f"Momentum conservation error: {dp}"
    print(f"  [OK] Momentum conservation: Delta_p = {dp:.2e}")

    print("\n[OK] All simulator tests passed")


# =============================================================================
# CORE PHYSICS TESTS (from original test_physics.py)
# =============================================================================

def test_core_physics():
    print_test_header("CORE PHYSICS TESTS")

    from src.physics_sim.core import (
        classical_mechanics, quantum_mechanics, electromagnetism,
        thermodynamics, relativity, C, ELECTRON_MASS, ELEMENTARY_CHARGE
    )

    # Test 1: Classical mechanics
    result = classical_mechanics({'mass': 10, 'acceleration': 5})
    assert result['force'] == 50, "F=ma"
    print(f"  [OK] F=ma: {result['force']}N")

    # Test 2: Quantum - hydrogen ground state
    result = quantum_mechanics({'principal_quantum_number': 1})
    assert_close(result['hydrogen_energy_eV'], -13.6, 0.01, "Hydrogen ground state")
    print(f"  [OK] Hydrogen ground state: {result['hydrogen_energy_eV']:.1f} eV")

    # Test 3: Electromagnetism - Coulomb
    result = electromagnetism({
        'charge1': ELEMENTARY_CHARGE,
        'charge2': ELEMENTARY_CHARGE,
        'distance': 1e-10
    })
    assert result['coulomb_force'] > 0, "Like charges repel"
    print(f"  [OK] Coulomb force: {result['coulomb_force']:.2e}N (repulsive)")

    # Test 4: Thermodynamics - Carnot efficiency
    result = thermodynamics({
        'hot_temperature': 500,
        'cold_temperature': 300
    })
    assert_close(result['carnot_efficiency'], 0.4, 0.01, "Carnot efficiency")
    print(f"  [OK] Carnot efficiency (500K->300K): {result['carnot_efficiency']*100:.0f}%")

    # Test 5: Relativity - electron rest mass energy
    result = relativity({'mass': ELECTRON_MASS})
    assert_close(result['rest_energy_MeV'], 0.511, 0.01, "Electron rest energy")
    print(f"  [OK] Electron rest energy: {result['rest_energy_MeV']:.3f} MeV")

    print("\n[OK] All core physics tests passed")


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all physics simulation tests."""
    print("\n" + "="*70)
    print(" COMPREHENSIVE PHYSICS SIMULATION TEST SUITE")
    print("="*70)

    test_core_physics()
    test_atmosphere()
    test_fluids()
    test_orbital()
    test_nuclear()
    test_statistical()
    test_waves_optics()
    test_numerical()
    test_simulator()

    print("\n" + "="*70)
    print(" ALL PHYSICS SIMULATION TESTS PASSED [OK]")
    print("="*70)
    print("""
Modules Tested:
  • core.py         - Classical, quantum, EM, thermo, relativity
  • atmosphere.py   - ISA model, Mach, compressibility
  • fluids.py       - Reynolds, Bernoulli, drag, shocks
  • orbital.py      - Kepler, Hohmann, perturbations
  • nuclear.py      - Decay, binding energy, fission/fusion
  • statistical.py  - MB/FD/BE distributions, Fermi energy
  • waves_optics.py - Snell, diffraction, Doppler
  • numerical.py    - RK4, Newton-Raphson, PSO, Simpson
  • simulator.py    - N-body, projectiles, energy conservation

Total: 40+ validated physics calculations
""")


if __name__ == "__main__":
    run_all_tests()
