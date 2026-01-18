#!/usr/bin/env python3
"""
SCBE System Interactive Demo
============================
Demonstrates the 14-layer SCBE pipeline with various scenarios.
"""

import sys
import os

# Set UTF-8 encoding for Windows compatibility
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import matplotlib.pyplot as plt
from scbe_14layer_reference import scbe_14layer_pipeline


def print_header(title):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_results(result, scenario_name):
    """Print formatted pipeline results."""
    print(f"\n{scenario_name}")
    print("-" * 80)
    print(f"Decision:      {result['decision']}")
    print(f"Risk (base):   {result['risk_base']:.6f}")
    print(f"Risk (prime):  {result['risk_prime']:.6f}")
    print(f"d*:            {result['d_star']:.6f}")
    print(f"H(d*):         {result['H']:.6f}")
    print(f"\nCoherence Metrics:")
    for k, v in result['coherence'].items():
        print(f"  {k:12s}: {v:.6f}")
    print(f"\nGeometry:")
    for k, v in result['geometry'].items():
        print(f"  {k:16s}: {v:.6f}")


def scenario_1_benign_traffic():
    """Scenario 1: Normal, benign traffic pattern."""
    print_header("Scenario 1: Benign Traffic")

    # High coherence, low-frequency signal
    amplitudes = np.array([0.8, 0.6, 0.5, 0.4, 0.3, 0.2])
    phases = np.linspace(0, np.pi/4, 6)  # Aligned phases
    t = np.concatenate([amplitudes, phases])

    # Clean telemetry
    telemetry = np.sin(np.linspace(0, 4*np.pi, 256))

    # Clean audio
    audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 512))

    result = scbe_14layer_pipeline(
        t=t,
        D=6,
        breathing_factor=1.0,
        telemetry_signal=telemetry,
        audio_frame=audio,
        w_d=0.20, w_c=0.20, w_s=0.20, w_tau=0.20, w_a=0.20
    )

    print_results(result, "Expected: ALLOW (high coherence, low risk)")
    return result


def scenario_2_suspicious_activity():
    """Scenario 2: Suspicious but not clearly malicious."""
    print_header("Scenario 2: Suspicious Activity")

    # Moderate coherence
    amplitudes = np.array([0.9, 0.3, 0.8, 0.2, 0.7, 0.4])
    phases = np.random.rand(6) * np.pi  # Semi-random phases
    t = np.concatenate([amplitudes, phases])

    # Noisy telemetry
    telemetry = np.sin(np.linspace(0, 4*np.pi, 256)) + 0.3 * np.random.randn(256)

    # Moderate audio noise
    audio = np.random.randn(512) * 0.5

    result = scbe_14layer_pipeline(
        t=t,
        D=6,
        breathing_factor=1.2,
        telemetry_signal=telemetry,
        audio_frame=audio,
        w_d=0.20, w_c=0.20, w_s=0.20, w_tau=0.20, w_a=0.20
    )

    print_results(result, "Expected: QUARANTINE (moderate risk)")
    return result


def scenario_3_malicious_attack():
    """Scenario 3: Clear attack pattern."""
    print_header("Scenario 3: Malicious Attack")

    # Low coherence, random patterns
    amplitudes = np.random.rand(6)
    phases = np.random.rand(6) * 2 * np.pi  # Random phases
    t = np.concatenate([amplitudes, phases])

    # High-frequency noise (suspicious)
    telemetry = np.random.randn(256)

    # Chaotic audio
    audio = np.random.randn(512)

    result = scbe_14layer_pipeline(
        t=t,
        D=6,
        breathing_factor=1.8,
        telemetry_signal=telemetry,
        audio_frame=audio,
        w_d=0.20, w_c=0.20, w_s=0.20, w_tau=0.20, w_a=0.20
    )

    print_results(result, "Expected: DENY (low coherence, high risk)")
    return result


def scenario_4_temporal_analysis():
    """Scenario 4: Temporal pattern evolution."""
    print_header("Scenario 4: Temporal Pattern Analysis")

    # Simulate evolving threat
    d_star_history = []
    decisions = []

    print("\nSimulating 10 time steps with degrading coherence:\n")

    for t_step in range(10):
        # Gradually degrade coherence
        noise_level = t_step * 0.1
        amplitudes = np.array([0.8, 0.6, 0.5, 0.4, 0.3, 0.2])
        phases = np.linspace(0, np.pi/4, 6) + noise_level * np.random.randn(6)
        t = np.concatenate([amplitudes, phases])

        telemetry = np.sin(np.linspace(0, 4*np.pi, 256)) + noise_level * np.random.randn(256)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 512)) + noise_level * np.random.randn(512)

        result = scbe_14layer_pipeline(
            t=t,
            D=6,
            breathing_factor=1.0 + noise_level,
            telemetry_signal=telemetry,
            audio_frame=audio,
            d_star_history=d_star_history.copy() if d_star_history else None
        )

        d_star_history.append(result['d_star'])
        decisions.append(result['decision'])

        print(f"Step {t_step:2d}: d*={result['d_star']:.4f}, "
              f"Risk'={result['risk_prime']:.4f}, "
              f"Decision={result['decision']}")

    print(f"\nDecision evolution: {' → '.join(decisions)}")
    return d_star_history


def scenario_5_custom_weights():
    """Scenario 5: Custom risk weighting strategies."""
    print_header("Scenario 5: Custom Risk Weights")

    # Standard input
    amplitudes = np.array([0.6, 0.5, 0.4, 0.3, 0.2, 0.1])
    phases = np.linspace(0, np.pi/2, 6)
    t = np.concatenate([amplitudes, phases])

    telemetry = np.sin(np.linspace(0, 4*np.pi, 256))
    audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 512))

    # Strategy 1: Prioritize geometric distance
    print("\nStrategy 1: Geometric-focused (high w_d)")
    result1 = scbe_14layer_pipeline(
        t=t, D=6, telemetry_signal=telemetry, audio_frame=audio,
        w_d=0.60, w_c=0.10, w_s=0.10, w_tau=0.10, w_a=0.10
    )
    print(f"  Risk': {result1['risk_prime']:.6f}, Decision: {result1['decision']}")

    # Strategy 2: Prioritize coherence
    print("\nStrategy 2: Coherence-focused (high w_c, w_s)")
    result2 = scbe_14layer_pipeline(
        t=t, D=6, telemetry_signal=telemetry, audio_frame=audio,
        w_d=0.10, w_c=0.35, w_s=0.35, w_tau=0.10, w_a=0.10
    )
    print(f"  Risk': {result2['risk_prime']:.6f}, Decision: {result2['decision']}")

    # Strategy 3: Audio-focused (surveillance)
    print("\nStrategy 3: Audio-focused (high w_a)")
    result3 = scbe_14layer_pipeline(
        t=t, D=6, telemetry_signal=telemetry, audio_frame=audio,
        w_d=0.10, w_c=0.10, w_s=0.10, w_tau=0.10, w_a=0.60
    )
    print(f"  Risk': {result3['risk_prime']:.6f}, Decision: {result3['decision']}")

    # Strategy 4: Balanced (default)
    print("\nStrategy 4: Balanced (equal weights)")
    result4 = scbe_14layer_pipeline(
        t=t, D=6, telemetry_signal=telemetry, audio_frame=audio,
        w_d=0.20, w_c=0.20, w_s=0.20, w_tau=0.20, w_a=0.20
    )
    print(f"  Risk': {result4['risk_prime']:.6f}, Decision: {result4['decision']}")


def scenario_6_breathing_effects():
    """Scenario 6: Breathing parameter effects."""
    print_header("Scenario 6: Breathing Transform Effects")

    amplitudes = np.array([0.5, 0.4, 0.3, 0.2, 0.1, 0.05])
    phases = np.zeros(6)
    t = np.concatenate([amplitudes, phases])

    print("\nBreathing factor effects on geometry:")
    print(f"{'b':6s} {'||u||':10s} {'||u_breath||':14s} {'d*':10s} {'Decision':12s}")
    print("-" * 60)

    for b in [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]:
        result = scbe_14layer_pipeline(
            t=t, D=6, breathing_factor=b,
            telemetry_signal=np.sin(np.linspace(0, 4*np.pi, 256)),
            audio_frame=np.sin(2 * np.pi * 440 * np.linspace(0, 1, 512))
        )
        print(f"{b:6.2f} {result['geometry']['u_norm']:10.6f} "
              f"{result['geometry']['u_breath_norm']:14.6f} "
              f"{result['d_star']:10.6f} {result['decision']:12s}")


def plot_risk_landscape():
    """Generate risk landscape visualization."""
    print_header("Scenario 7: Risk Landscape Visualization")

    print("\nGenerating risk landscape across coherence space...")

    # Sweep coherence parameters
    n_points = 20
    C_spin_range = np.linspace(0, 1, n_points)
    S_spec_range = np.linspace(0, 1, n_points)

    risk_grid = np.zeros((n_points, n_points))
    decision_grid = np.zeros((n_points, n_points))

    base_t = np.concatenate([np.array([0.5]*6), np.array([0.0]*6)])

    for i, C_spin_target in enumerate(C_spin_range):
        for j, S_spec_target in enumerate(S_spec_range):
            # Construct phases to match target C_spin
            if C_spin_target > 0.5:
                phases = np.zeros(6) + (1 - C_spin_target) * np.random.randn(6) * 0.5
            else:
                phases = np.random.rand(6) * 2 * np.pi

            # Construct telemetry to match target S_spec
            if S_spec_target > 0.5:
                telemetry = np.sin(np.linspace(0, 4*np.pi, 256))
            else:
                telemetry = np.random.randn(256)

            t = np.concatenate([np.array([0.5]*6), phases])

            result = scbe_14layer_pipeline(
                t=t, D=6,
                telemetry_signal=telemetry,
                audio_frame=np.sin(2 * np.pi * 440 * np.linspace(0, 1, 512))
            )

            risk_grid[i, j] = result['risk_prime']
            decision_grid[i, j] = {'ALLOW': 0, 'QUARANTINE': 1, 'DENY': 2}[result['decision']]

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Risk surface
    im1 = axes[0].imshow(risk_grid, origin='lower', extent=[0, 1, 0, 1],
                         cmap='YlOrRd', aspect='auto')
    axes[0].set_xlabel('S_spec (Spectral Coherence)')
    axes[0].set_ylabel('C_spin (Spin Coherence)')
    axes[0].set_title('Risk Prime Landscape')
    plt.colorbar(im1, ax=axes[0], label="Risk'")

    # Decision regions
    im2 = axes[1].imshow(decision_grid, origin='lower', extent=[0, 1, 0, 1],
                         cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=2)
    axes[1].set_xlabel('S_spec (Spectral Coherence)')
    axes[1].set_ylabel('C_spin (Spin Coherence)')
    axes[1].set_title('Decision Regions')
    cbar = plt.colorbar(im2, ax=axes[1], ticks=[0, 1, 2])
    cbar.ax.set_yticklabels(['ALLOW', 'QUARANTINE', 'DENY'])

    plt.tight_layout()
    output_path = os.path.join(os.path.dirname(__file__), 'risk_landscape.png')
    plt.savefig(output_path, dpi=150)
    print(f"\nVisualization saved to: {output_path}")
    plt.close()


def main():
    """Run all demo scenarios."""
    print("=" * 80)
    print("  SCBE 14-Layer System - Interactive Demo")
    print("=" * 80)
    print("\nThis demo showcases the complete SCBE pipeline with various scenarios.")

    np.random.seed(42)  # Reproducibility

    # Run scenarios
    scenario_1_benign_traffic()
    scenario_2_suspicious_activity()
    scenario_3_malicious_attack()
    scenario_4_temporal_analysis()
    scenario_5_custom_weights()
    scenario_6_breathing_effects()

    # Visualization
    try:
        plot_risk_landscape()
    except Exception as e:
        print(f"\nVisualization skipped (matplotlib issue): {e}")

    print_header("Demo Complete")
    print("\nAll 14 layers have been demonstrated:")
    print("  L1:  Complex State")
    print("  L2:  Realification")
    print("  L3:  Weighted Transform")
    print("  L4:  Poincaré Embedding")
    print("  L5:  Hyperbolic Distance")
    print("  L6:  Breathing Transform")
    print("  L7:  Phase Transform")
    print("  L8:  Realm Distance")
    print("  L9:  Spectral Coherence")
    print("  L10: Spin Coherence")
    print("  L11: Triadic Temporal")
    print("  L12: Harmonic Scaling")
    print("  L13: Risk Decision")
    print("  L14: Audio Axis")
    print("\nSystem ready for production testing!")


if __name__ == "__main__":
    main()
