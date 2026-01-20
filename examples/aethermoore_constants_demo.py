"""
Aethermoore Constants Interactive Demo
Demonstrates all four constants with visualizations

Author: Isaac Davis (@issdandavis)
Date: January 19, 2026
Patent: USPTO #63/961,403
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import matplotlib.pyplot as plt
from symphonic_cipher.core.harmonic_scaling_law import HarmonicScalingLaw
from symphonic_cipher.core.cymatic_voxel_storage import CymaticVoxelStorage, VoxelAccessVector
from symphonic_cipher.dynamics.flux_interaction import FluxInteractionFramework
from symphonic_cipher.audio.stellar_octave_mapping import StellarOctaveMapping


def demo_constant_1():
    """Constant 1: Harmonic Scaling Law"""
    print("\n" + "=" * 70)
    print("CONSTANT 1: HARMONIC SCALING LAW")
    print("H(d, R) = R^(d²)")
    print("=" * 70)
    
    hsl = HarmonicScalingLaw(R=1.5)
    
    # Growth table
    print("\n" + hsl.growth_table(d_max=6))
    
    # Cryptographic strength
    print("\n\nCryptographic Strength (Base: 128-bit AES):")
    for d in range(1, 7):
        strength = hsl.cryptographic_strength(d, base_bits=128)
        print(f"  d={d}: {strength:.1f} effective bits")
    
    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Growth curve
    dimensions = np.arange(1, 7)
    results = hsl.compute_range(1, 6)
    scaling_factors = [r.scaling_factor for r in results]
    
    ax1.semilogy(dimensions, scaling_factors, 'o-', linewidth=2, markersize=8)
    ax1.set_xlabel('Dimensions (d)', fontsize=12)
    ax1.set_ylabel('H(d, 1.5) [log scale]', fontsize=12)
    ax1.set_title('Constant 1: Super-Exponential Growth', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Security bits
    security_bits = [r.security_bits for r in results]
    ax2.plot(dimensions, security_bits, 's-', linewidth=2, markersize=8, color='green')
    ax2.set_xlabel('Dimensions (d)', fontsize=12)
    ax2.set_ylabel('Security Bits', fontsize=12)
    ax2.set_title('Cryptographic Security Scaling', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('constant_1_harmonic_scaling.png', dpi=150, bbox_inches='tight')
    print("\n✓ Visualization saved: constant_1_harmonic_scaling.png")
    plt.close()


def demo_constant_2():
    """Constant 2: Cymatic Voxel Storage"""
    print("\n" + "=" * 70)
    print("CONSTANT 2: CYMATIC VOXEL STORAGE")
    print("cos(n·π·x)·cos(m·π·y) - cos(m·π·x)·cos(n·π·y) = 0")
    print("=" * 70)
    
    cvs = CymaticVoxelStorage(resolution=100)
    
    # Access control demo
    data = np.random.rand(100, 100)
    correct_vector = VoxelAccessVector(3, 0, 0, 5, 0, 0)
    wrong_vector = VoxelAccessVector(2, 0, 0, 4, 0, 0)
    
    decoded_correct, decoded_wrong = cvs.access_control_demo(data, correct_vector, wrong_vector)
    
    error_correct = np.mean((data - decoded_correct) ** 2)
    error_wrong = np.mean((data - decoded_wrong) ** 2)
    
    print(f"\nAccess Control Test:")
    print(f"  Correct Vector (n=3, m=5): MSE = {error_correct:.6f}")
    print(f"  Wrong Vector (n=2, m=4):   MSE = {error_wrong:.6f}")
    print(f"  Error Ratio: {error_wrong / error_correct:.1f}x")
    
    # Security analysis
    security = cvs.security_analysis(n_correct=3, m_correct=5, n_attempts=100)
    print(f"\nSecurity Analysis (100 random attempts):")
    print(f"  Successful Decodes: {security['successful_decodes']}")
    print(f"  Security Rate: {security['security_rate']:.2%}")
    print(f"  Effective Bits: {security['effective_bits']:.1f} bits")
    
    # Visualization
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    # Row 1: Chladni patterns
    for i, (n, m) in enumerate([(2, 3), (3, 5), (4, 7)]):
        pattern = cvs.visualize_pattern(n, m)
        axes[0, i].imshow(pattern, cmap='RdBu', origin='lower')
        axes[0, i].set_title(f'Chladni Pattern (n={n}, m={m})', fontweight='bold')
        axes[0, i].axis('off')
    
    # Row 2: Access control
    axes[1, 0].imshow(data, cmap='viridis', origin='lower')
    axes[1, 0].set_title('Original Data', fontweight='bold')
    axes[1, 0].axis('off')
    
    axes[1, 1].imshow(decoded_correct, cmap='viridis', origin='lower')
    axes[1, 1].set_title(f'Correct Vector\nMSE={error_correct:.6f}', fontweight='bold')
    axes[1, 1].axis('off')
    
    axes[1, 2].imshow(decoded_wrong, cmap='viridis', origin='lower')
    axes[1, 2].set_title(f'Wrong Vector\nMSE={error_wrong:.6f}', fontweight='bold')
    axes[1, 2].axis('off')
    
    plt.tight_layout()
    plt.savefig('constant_2_cymatic_voxel.png', dpi=150, bbox_inches='tight')
    print("\n✓ Visualization saved: constant_2_cymatic_voxel.png")
    plt.close()


def demo_constant_3():
    """Constant 3: Flux Interaction Framework"""
    print("\n" + "=" * 70)
    print("CONSTANT 3: FLUX INTERACTION FRAMEWORK")
    print("R × (1/R) = 1 (phase cancellation)")
    print("=" * 70)
    
    fif = FluxInteractionFramework(R=1.5)
    
    # Duality table
    print("\n" + fif.duality_table(d_max=6, Base=100))
    
    # Energy redistribution
    print("\n\nEnergy Redistribution (d=3, Base=100):")
    zones = fif.energy_redistribution_zones(d=3, Base=100)
    print(f"  Concentration Ratio: {zones['concentration_ratio']:.2%}")
    print(f"  Peak Zone Fraction: {zones['peak_zone_fraction']:.2%}")
    print(f"  Energy Amplification: {zones['energy_amplification']:.2f}x")
    
    # Acoustic black hole
    print("\n\nAcoustic Black Hole Strength:")
    for d in range(1, 7):
        strength = fif.acoustic_black_hole_strength(d, Base=100)
        print(f"  d={d}: {strength:.2%} trapping efficiency")
    
    # Visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Duality verification
    dimensions = np.arange(1, 7)
    results = fif.compute_range(1, 6, Base=100)
    products = [r.product for r in results]
    
    axes[0, 0].plot(dimensions, products, 'o-', linewidth=2, markersize=8)
    axes[0, 0].axhline(y=1.0, color='r', linestyle='--', label='Unity')
    axes[0, 0].set_xlabel('Dimensions (d)')
    axes[0, 0].set_ylabel('f(x) × f⁻¹(x)')
    axes[0, 0].set_title('Duality Verification', fontweight='bold')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Energy ratio
    energy_ratios = [r.energy_ratio for r in results]
    axes[0, 1].semilogy(dimensions, energy_ratios, 's-', linewidth=2, markersize=8, color='orange')
    axes[0, 1].set_xlabel('Dimensions (d)')
    axes[0, 1].set_ylabel('Energy Ratio [log scale]')
    axes[0, 1].set_title('Constructive/Destructive Energy Ratio', fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: Interference pattern
    x = np.linspace(0, 1, 200)
    constructive, destructive, total = fif.interference_pattern(d=3, Base=100, x=x)
    
    axes[1, 0].plot(x, constructive, label='Constructive', linewidth=2)
    axes[1, 0].plot(x, destructive, label='Destructive', linewidth=2)
    axes[1, 0].set_xlabel('Position (x)')
    axes[1, 0].set_ylabel('Amplitude')
    axes[1, 0].set_title('Interference Pattern (d=3)', fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Trapping efficiency
    trapping = [fif.acoustic_black_hole_strength(d, Base=100) for d in dimensions]
    axes[1, 1].plot(dimensions, trapping, '^-', linewidth=2, markersize=8, color='purple')
    axes[1, 1].set_xlabel('Dimensions (d)')
    axes[1, 1].set_ylabel('Trapping Efficiency')
    axes[1, 1].set_title('Acoustic Black Hole Strength', fontweight='bold')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('constant_3_flux_interaction.png', dpi=150, bbox_inches='tight')
    print("\n✓ Visualization saved: constant_3_flux_interaction.png")
    plt.close()


def demo_constant_4():
    """Constant 4: Stellar Octave Mapping"""
    print("\n" + "=" * 70)
    print("CONSTANT 4: STELLAR-TO-HUMAN OCTAVE MAPPING")
    print("f_human = f_stellar × 2^n")
    print("=" * 70)
    
    som = StellarOctaveMapping()
    
    # Transposition table
    print("\n" + som.transposition_table())
    
    # Stellar Pulse Protocol
    print("\n\nStellar Pulse Protocol (Sun's p-mode):")
    protocol = som.stellar_pulse_protocol('sun_p_mode')
    for key, value in protocol.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    # Entropy regulation
    print("\n\nEntropy Regulation Sequence (60s):")
    sequence = som.entropy_regulation_sequence('sun_p_mode', duration_s=60.0)
    print(f"  Num Pulses: {sequence['num_pulses']}")
    print(f"  Pulse Frequency: {sequence['pulse_freq_Hz']:.2f} Hz")
    print(f"  Pulse Period: {sequence['pulse_period_ms']:.2f} ms")
    
    # Visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Octave transposition
    stellar_bodies = ['sun_p_mode', 'sun_g_mode', 'red_giant', 'white_dwarf']
    stellar_freqs = [som.STELLAR_FREQUENCIES[body] * 1000 for body in stellar_bodies]
    octaves = [som.transpose(som.STELLAR_FREQUENCIES[body]).octaves for body in stellar_bodies]
    
    axes[0, 0].barh(stellar_bodies, octaves, color='steelblue')
    axes[0, 0].set_xlabel('Octaves (n)')
    axes[0, 0].set_title('Octave Transposition by Stellar Body', fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3, axis='x')
    
    # Plot 2: Human frequencies
    human_freqs = [som.transpose(som.STELLAR_FREQUENCIES[body]).human_freq for body in stellar_bodies]
    axes[0, 1].barh(stellar_bodies, human_freqs, color='coral')
    axes[0, 1].set_xlabel('Human Frequency (Hz)')
    axes[0, 1].set_xscale('log')
    axes[0, 1].set_title('Transposed Human Frequencies', fontweight='bold')
    axes[0, 1].axvline(x=20, color='r', linestyle='--', alpha=0.5, label='Audible Min')
    axes[0, 1].axvline(x=20000, color='r', linestyle='--', alpha=0.5, label='Audible Max')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3, axis='x')
    
    # Plot 3: Pulse sequence
    t = sequence['pulse_times_s'][:50]  # First 50 pulses
    pulses = np.sin(2 * np.pi * sequence['pulse_freq_Hz'] * t)
    
    axes[1, 0].plot(t, pulses, linewidth=1.5)
    axes[1, 0].set_xlabel('Time (s)')
    axes[1, 0].set_ylabel('Amplitude')
    axes[1, 0].set_title('Entropy Regulation Pulse Sequence', fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Harmonics
    harmonics = som.stellar_camouflage_frequencies('sun_p_mode', num_harmonics=10)
    harmonic_nums = np.arange(1, len(harmonics) + 1)
    
    axes[1, 1].stem(harmonic_nums, harmonics, basefmt=' ')
    axes[1, 1].set_xlabel('Harmonic Number')
    axes[1, 1].set_ylabel('Frequency (Hz)')
    axes[1, 1].set_title('Stellar Camouflage Harmonics', fontweight='bold')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('constant_4_stellar_octave.png', dpi=150, bbox_inches='tight')
    print("\n✓ Visualization saved: constant_4_stellar_octave.png")
    plt.close()


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("AETHERMOORE CONSTANTS INTERACTIVE DEMO")
    print("USPTO Patent #63/961,403")
    print("Author: Isaac Davis (@issdandavis)")
    print("=" * 70)
    
    try:
        demo_constant_1()
        demo_constant_2()
        demo_constant_3()
        demo_constant_4()
        
        print("\n" + "=" * 70)
        print("✓ ALL DEMOS COMPLETE")
        print("=" * 70)
        print("\nGenerated Files:")
        print("  - constant_1_harmonic_scaling.png")
        print("  - constant_2_cymatic_voxel.png")
        print("  - constant_3_flux_interaction.png")
        print("  - constant_4_stellar_octave.png")
        print("\nNext Steps:")
        print("  1. Review visualizations")
        print("  2. Run test suite: pytest tests/aethermoore_constants/")
        print("  3. File provisional patents (deadline: Jan 31, 2026)")
        print()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
