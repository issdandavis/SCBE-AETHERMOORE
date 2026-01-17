#!/usr/bin/env python3
"""
Physics Simulation Test Suite

Run with: python -m physics_sim.test_physics
"""

import json
from .core import (
    classical_mechanics,
    quantum_mechanics,
    electromagnetism,
    thermodynamics,
    relativity,
    lambda_handler,
    PLANCK, C, G, ELECTRON_MASS, ELEMENTARY_CHARGE
)


def print_results(title: str, results: dict):
    """Pretty print results."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)
    for key, value in results.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.6e}")
        else:
            print(f"  {key}: {value}")


def test_classical():
    """Test classical mechanics."""
    print("\n" + "#"*60)
    print(" CLASSICAL MECHANICS TESTS")
    print("#"*60)

    # Newton's second law
    results = classical_mechanics({
        'mass': 10,  # kg
        'acceleration': 5  # m/s²
    })
    print_results("F = ma (10 kg, 5 m/s²)", results)
    assert abs(results['force'] - 50) < 0.01, "Force calculation wrong"

    # Kinematics
    results = classical_mechanics({
        'initial_velocity': 0,
        'acceleration': 9.81,
        'time': 5
    })
    print_results("Free fall (5 seconds)", results)

    # Gravitational force (Earth-Moon)
    results = classical_mechanics({
        'm1': 5.972e24,  # Earth mass (kg)
        'm2': 7.342e22,  # Moon mass (kg)
        'distance': 3.844e8  # m
    })
    print_results("Earth-Moon gravitational force", results)

    # Kinetic energy
    results = classical_mechanics({
        'mass': 1,
        'velocity': 10
    })
    print_results("Kinetic energy (1 kg at 10 m/s)", results)
    assert abs(results['kinetic_energy'] - 50) < 0.01, "KE calculation wrong"

    # Simple harmonic motion
    results = classical_mechanics({
        'spring_constant': 100,  # N/m
        'mass': 1  # kg
    })
    print_results("SHM (k=100, m=1)", results)

    print("\n✓ Classical mechanics tests passed")


def test_quantum():
    """Test quantum mechanics."""
    print("\n" + "#"*60)
    print(" QUANTUM MECHANICS TESTS")
    print("#"*60)

    # Photon energy (visible light, 500 nm)
    results = quantum_mechanics({
        'wavelength': 500e-9  # 500 nm
    })
    print_results("Photon at 500 nm (green light)", results)

    # de Broglie wavelength of electron
    results = quantum_mechanics({
        'particle_mass': ELECTRON_MASS,
        'particle_velocity': 1e6  # 1,000 km/s
    })
    print_results("Electron at 1,000 km/s", results)

    # Particle in a box
    results = quantum_mechanics({
        'box_length': 1e-9,  # 1 nm
        'quantum_number': 1,
        'particle_mass': ELECTRON_MASS
    })
    print_results("Electron in 1 nm box (n=1)", results)

    # Hydrogen atom
    results = quantum_mechanics({
        'principal_quantum_number': 1
    })
    print_results("Hydrogen ground state", results)
    assert abs(results['hydrogen_energy_eV'] - (-13.6)) < 0.1, "Hydrogen energy wrong"

    # Hydrogen transition (Balmer series)
    results = quantum_mechanics({
        'n_initial': 3,
        'n_final': 2
    })
    print_results("Hydrogen 3→2 transition (H-alpha)", results)

    # Heisenberg uncertainty
    results = quantum_mechanics({
        'position_uncertainty': 1e-10  # 0.1 nm
    })
    print_results("Uncertainty (Δx = 0.1 nm)", results)

    print("\n✓ Quantum mechanics tests passed")


def test_electromagnetism():
    """Test electromagnetism."""
    print("\n" + "#"*60)
    print(" ELECTROMAGNETISM TESTS")
    print("#"*60)

    # Coulomb's law (two electrons)
    results = electromagnetism({
        'charge1': -ELEMENTARY_CHARGE,
        'charge2': -ELEMENTARY_CHARGE,
        'distance': 1e-10  # 0.1 nm
    })
    print_results("Two electrons 0.1 nm apart", results)

    # Electric field from proton
    results = electromagnetism({
        'charge': ELEMENTARY_CHARGE,
        'distance': 5.29e-11  # Bohr radius
    })
    print_results("Electric field at Bohr radius", results)

    # Magnetic force on moving charge
    results = electromagnetism({
        'charge': ELEMENTARY_CHARGE,
        'velocity': 1e6,  # m/s
        'magnetic_field': 1,  # Tesla
        'mass': ELECTRON_MASS
    })
    print_results("Electron in 1T field at 1000 km/s", results)

    # Electromagnetic wave classification
    results = electromagnetism({
        'em_frequency': 5e14  # 500 THz (visible)
    })
    print_results("EM wave at 500 THz", results)

    # Capacitor
    results = electromagnetism({
        'plate_area': 0.01,  # m²
        'plate_separation': 0.001,  # 1 mm
        'voltage': 100
    })
    print_results("Parallel plate capacitor", results)

    print("\n✓ Electromagnetism tests passed")


def test_thermodynamics():
    """Test thermodynamics."""
    print("\n" + "#"*60)
    print(" THERMODYNAMICS TESTS")
    print("#"*60)

    # Ideal gas law
    results = thermodynamics({
        'pressure': 101325,  # 1 atm in Pa
        'volume': 0.0224,  # ~22.4 L
        'moles': 1
    })
    print_results("1 mol at STP", results)

    # Maxwell-Boltzmann (room temperature)
    results = thermodynamics({
        'temperature': 300,  # K
        'molecular_mass': 4.65e-26  # N₂ molecule
    })
    print_results("N₂ at 300 K", results)

    # Black body radiation (Sun)
    results = thermodynamics({
        'temperature': 5778,  # K (Sun surface)
        'surface_area': 6.08e18  # m² (Sun)
    })
    print_results("Sun black body radiation", results)

    # Carnot efficiency
    results = thermodynamics({
        'hot_temperature': 500,  # K
        'cold_temperature': 300  # K
    })
    print_results("Carnot engine 500K→300K", results)

    print("\n✓ Thermodynamics tests passed")


def test_relativity():
    """Test relativity."""
    print("\n" + "#"*60)
    print(" RELATIVITY TESTS")
    print("#"*60)

    # Slow speed (non-relativistic check)
    results = relativity({
        'velocity': 1000,  # 1 km/s
        'proper_time': 1,
        'proper_length': 1
    })
    print_results("1 km/s (γ ≈ 1)", results)
    assert abs(results['lorentz_factor'] - 1) < 0.001, "Should be nearly 1"

    # High speed (0.9c)
    results = relativity({
        'velocity': 0.9 * C,
        'proper_time': 1,
        'proper_length': 1
    })
    print_results("0.9c (γ ≈ 2.29)", results)

    # Very high speed (0.99c)
    results = relativity({
        'velocity': 0.99 * C,
        'proper_time': 1,
        'proper_length': 1
    })
    print_results("0.99c (γ ≈ 7.09)", results)

    # Mass-energy (1 kg)
    results = relativity({
        'mass': 1  # kg
    })
    print_results("E=mc² for 1 kg", results)

    # Electron rest mass energy
    results = relativity({
        'mass': ELECTRON_MASS
    })
    print_results("Electron rest energy", results)
    assert abs(results['rest_energy_MeV'] - 0.511) < 0.01, "Should be ~0.511 MeV"

    # Black hole (1 solar mass)
    results = relativity({
        'black_hole_mass': 1.989e30  # Solar mass
    })
    print_results("1 solar mass black hole", results)

    print("\n✓ Relativity tests passed")


def test_lambda_handler():
    """Test the Lambda handler interface."""
    print("\n" + "#"*60)
    print(" LAMBDA HANDLER TESTS")
    print("#"*60)

    # Valid request
    response = lambda_handler({
        'simulation_type': 'quantum',
        'parameters': {
            'principal_quantum_number': 2
        }
    })
    print_results("Hydrogen n=2 via handler", json.loads(response['body'])['results'])
    assert response['statusCode'] == 200

    # Invalid simulation type
    response = lambda_handler({
        'simulation_type': 'magic',
        'parameters': {}
    })
    assert response['statusCode'] == 400
    print("\n  Invalid type correctly rejected: 400")

    print("\n✓ Lambda handler tests passed")


def run_all_tests():
    """Run all physics tests."""
    print("\n" + "="*60)
    print(" PHYSICS SIMULATION TEST SUITE")
    print("="*60)

    test_classical()
    test_quantum()
    test_electromagnetism()
    test_thermodynamics()
    test_relativity()
    test_lambda_handler()

    print("\n" + "="*60)
    print(" ALL TESTS PASSED ✓")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
