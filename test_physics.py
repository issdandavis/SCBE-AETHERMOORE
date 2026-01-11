#!/usr/bin/env python3
"""
Quick Physics Test Script

Run: python test_physics.py
"""

from physics_sim.core import (
    classical_mechanics,
    quantum_mechanics,
    electromagnetism,
    thermodynamics,
    relativity,
    PLANCK, C, G, ELECTRON_MASS, ELEMENTARY_CHARGE, BOLTZMANN
)


def main():
    print("\n" + "="*60)
    print(" PHYSICS SIMULATION - QUICK TEST")
    print("="*60)

    # 1. Classical: Free fall
    print("\n[1] FREE FALL (10 seconds)")
    result = classical_mechanics({
        'initial_velocity': 0,
        'acceleration': 9.81,
        'time': 10
    })
    print(f"    Final velocity: {result['final_velocity']:.2f} m/s")
    print(f"    Distance fallen: {result['displacement']:.2f} m")

    # 2. Quantum: Photon energy
    print("\n[2] RED LASER (650 nm)")
    result = quantum_mechanics({'wavelength': 650e-9})
    print(f"    Photon energy: {result['photon_energy_eV']:.4f} eV")
    print(f"    Frequency: {result['frequency']:.2e} Hz")

    # 3. Quantum: Hydrogen
    print("\n[3] HYDROGEN ATOM")
    for n in [1, 2, 3]:
        result = quantum_mechanics({'principal_quantum_number': n})
        print(f"    n={n}: E = {result['hydrogen_energy_eV']:.2f} eV, r = {result['orbital_radius']*1e12:.1f} pm")

    # 4. Electromagnetism: Two protons
    print("\n[4] TWO PROTONS (1 femtometer apart)")
    result = electromagnetism({
        'charge1': ELEMENTARY_CHARGE,
        'charge2': ELEMENTARY_CHARGE,
        'distance': 1e-15
    })
    print(f"    Repulsive force: {result['coulomb_force']:.2f} N")

    # 5. Thermodynamics: Room temperature
    print("\n[5] AIR MOLECULES AT ROOM TEMP (300 K)")
    result = thermodynamics({
        'temperature': 300,
        'molecular_mass': 4.8e-26  # ~O₂
    })
    print(f"    Average KE: {result['average_kinetic_energy']:.2e} J")
    print(f"    RMS speed: {result['rms_speed']:.1f} m/s")

    # 6. Relativity: Fast spaceship
    print("\n[6] SPACESHIP AT 0.8c")
    result = relativity({
        'velocity': 0.8 * C,
        'proper_time': 1,  # 1 year proper time
        'proper_length': 100  # 100 m proper length
    })
    print(f"    Lorentz factor γ: {result['lorentz_factor']:.3f}")
    print(f"    Time dilation: 1 year → {result['dilated_time']:.2f} years (observer)")
    print(f"    Length contraction: 100 m → {result['contracted_length']:.1f} m (observer)")

    # 7. Relativity: E=mc²
    print("\n[7] E=mc² (1 gram of matter)")
    result = relativity({'mass': 0.001})
    print(f"    Energy: {result['rest_energy_J']:.2e} J")
    print(f"    That's {result['rest_energy_J'] / 4.184e9:.0f} tons of TNT!")

    # 8. Black hole
    print("\n[8] BLACK HOLE (10 solar masses)")
    result = relativity({'black_hole_mass': 10 * 1.989e30})
    print(f"    Schwarzschild radius: {result['schwarzschild_radius']/1000:.1f} km")

    print("\n" + "="*60)
    print(" All calculations use real physics constants")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
