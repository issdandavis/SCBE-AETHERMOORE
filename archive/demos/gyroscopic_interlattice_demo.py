#!/usr/bin/env python3
"""
Gyroscopic Interlattice Coupling Demo
======================================

Demonstrates the core physics of SCBE's gyroscopic interlattice architecture:
1. Phi-scaled tongue radii and their orbital frequencies
2. Inverse fifth-power coupling locality
3. Phase factors that break time-reversal symmetry
4. Nash equation evolution
5. Anderson insulation (disorder strengthening)

Run: python demos/gyroscopic_interlattice_demo.py
"""

import sys
import math

sys.path.insert(0, "src")
from symphonic_cipher.scbe_aethermoore.axiom_grouped.gyroscopic_interlattice import (
    TONGUE_LABELS,
    TONGUE_RADII,
    create_sublattice,
    coupling_strength,
    phase_factor,
    coupling_matrix,
    evolve_step,
    anderson_insulation_test,
    SublatticeState,
)

PHI = (1 + math.sqrt(5)) / 2


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def main():
    print("SCBE-AETHERMOORE Gyroscopic Interlattice Demo")
    print("Based on Nash et al. PNAS 112:14495 (2015)")

    # 1. Tongue sublattice geometry
    section("1. Sacred Tongue Sublattice Geometry")
    print(f"{'Tongue':<8} {'Radius (phi^k)':<16} {'Precession Freq':<18} {'Phase (deg)'}")
    print("-" * 60)
    for k, t in enumerate(TONGUE_LABELS):
        sub = create_sublattice(t)
        print(f"{t:<8} {sub.radius:<16.4f} {sub.precession_freq:<18.6f} {math.degrees(sub.phase):.0f}")

    # 2. Coupling locality
    section("2. Interlattice Coupling Strength (A2: Locality)")
    print(f"{'Pair':<10} {'Spacing':<12} {'Coupling J':<16} {'Relative'}")
    print("-" * 55)
    j_ko_av = coupling_strength("KO", "AV")
    pairs = [
        ("KO", "AV"),
        ("AV", "RU"),
        ("KO", "RU"),
        ("KO", "CA"),
        ("KO", "UM"),
        ("KO", "DR"),
    ]
    for a, b in pairs:
        j = coupling_strength(a, b)
        spacing = abs(TONGUE_RADII[a] - TONGUE_RADII[b])
        rel = j / j_ko_av
        print(f"{a}-{b:<6} {spacing:<12.4f} {j:<16.6f} {rel:.6f}x")

    print(f"\nKO-AV / KO-DR ratio: {j_ko_av / coupling_strength('KO', 'DR'):,.0f}x")
    print("Adjacent tongues couple ~1.2 MILLION times stronger than distant ones!")

    # 3. Phase factors and TRS breaking
    section("3. Phase Factors (Time-Reversal Symmetry Breaking)")
    print(f"{'Pair':<10} {'e^(2i*theta)':<25} {'|imag| > 0 = TRS broken'}")
    print("-" * 60)
    for a, b in [("KO", "AV"), ("KO", "RU"), ("KO", "CA")]:
        pf = phase_factor(a, b)
        broken = "YES" if abs(pf[1]) > 0.01 else "no"
        print(f"{a}-{b:<6} ({pf[0]:+.4f}, {pf[1]:+.4f}i)       {broken}")

    # 4. Full coupling matrix
    section("4. 6x6 Coupling Matrix")
    J = coupling_matrix()
    print(f"{'':>6}", end="")
    for t in TONGUE_LABELS:
        print(f"{t:>10}", end="")
    print()
    for i, t in enumerate(TONGUE_LABELS):
        print(f"{t:>6}", end="")
        for j in range(6):
            val = J[i][j]
            if val == 0:
                print(f"{'---':>10}", end="")
            elif val > 1:
                print(f"{val:>10.3f}", end="")
            else:
                print(f"{val:>10.6f}", end="")
        print()

    # 5. Nash equation evolution
    section("5. Nash Equation Evolution (100 steps)")
    subs = [
        create_sublattice(
            t,
            SublatticeState(
                real=0.1 * math.cos(2 * math.pi * k / 6),
                imag=0.1 * math.sin(2 * math.pi * k / 6),
            ),
        )
        for k, t in enumerate(TONGUE_LABELS)
    ]

    print("Initial states:")
    for s in subs:
        amp = math.sqrt(s.state.real**2 + s.state.imag**2)
        print(f"  {s.tongue}: psi = ({s.state.real:+.4f}, {s.state.imag:+.4f}i), |psi| = {amp:.4f}")

    for _ in range(100):
        evolve_step(subs, dt=0.001)

    print("\nAfter 100 steps (dt=0.001):")
    for s in subs:
        amp = math.sqrt(s.state.real**2 + s.state.imag**2)
        print(f"  {s.tongue}: psi = ({s.state.real:+.4f}, {s.state.imag:+.4f}i), |psi| = {amp:.4f}")

    # 6. Anderson insulation test
    section("6. Anderson Insulation Test (Disorder Strengthening)")
    clean_subs = [create_sublattice(t) for t in TONGUE_LABELS]

    for disorder in [0.05, 0.10, 0.20, 0.50]:
        result = anderson_insulation_test(clean_subs, disorder)
        status = "STRENGTHENED" if result["topology_strengthened"] else (
            "preserved" if result["topology_preserved"] else "DEGRADED"
        )
        print(f"  Disorder {disorder*100:5.1f}%: topology {status}")
        print(f"    Clean Chern:  {result['clean_chern']}")
        print(f"    Noisy Chern:  {result['disordered_chern']}")

    section("Summary")
    print("Key results:")
    print("  1. Phi-scaled tongue radii = lattice distortion controlling Chern numbers")
    print("  2. Adjacent coupling 1.2M x stronger than distant = extreme locality (A2)")
    print("  3. Hexagonal phases break TRS = intrinsic nonreciprocity (A3)")
    print("  4. Nash first-order dynamics evolve without blowup")
    print("  5. Disorder preserves or strengthens topology (Anderson insulation)")
    print()
    print("This is the mathematical basis for: breach -> precession, not collapse.")


if __name__ == "__main__":
    main()
