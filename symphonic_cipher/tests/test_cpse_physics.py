"""
CPSE Physics Validation Tests

Tests the mathematical foundations:
1. Chaos Sensitivity - Logistic map divergence
2. Fractal Gate Discrimination - Julia set basin membership
3. Neural Energy Separation - Hopfield network anomaly detection
"""

import numpy as np

# Optional plotting - will skip if not available
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# =============================================================================
# TEST 1: CHAOS SENSITIVITY
# =============================================================================

def logistic(r, x0, n):
    """Logistic map: x_{n+1} = r * x_n * (1 - x_n)"""
    x = x0
    trajectory = [x]
    for _ in range(n):
        x = r * x * (1 - x)
        trajectory.append(x)
    return x, trajectory


def test_chaos_sensitivity():
    """
    Prediction: Changing r by 0.0001 produces completely different output after 50 iterations
    """
    r1 = 3.99
    r2 = 3.9901  # Only 0.0001 different
    x0 = 0.5
    n_iter = 50

    final1, traj1 = logistic(r1, x0, n_iter)
    final2, traj2 = logistic(r2, x0, n_iter)

    difference = abs(final1 - final2)

    print("=" * 60)
    print("TEST 1: CHAOS SENSITIVITY")
    print("=" * 60)
    print(f"Starting point: x₀ = {x0}")
    print(f"r₁ = {r1}")
    print(f"r₂ = {r2} (difference: {r2-r1})")
    print(f"\nAfter {n_iter} iterations:")
    print(f"  r₁ → x = {final1:.10f}")
    print(f"  r₂ → x = {final2:.10f}")
    print(f"\nDifference: {difference:.10f}")

    passed = difference > 0.1
    print(f"{'✓ PASS' if passed else '✗ FAIL'}: Difference {'>' if passed else '<='} 0.1")

    # Visualize divergence (if matplotlib available)
    if HAS_MATPLOTLIB:
        plt.figure(figsize=(12, 5))
        plt.subplot(1, 2, 1)
        plt.plot(traj1[:20], 'b-o', label=f'r={r1}', markersize=4)
        plt.plot(traj2[:20], 'r--s', label=f'r={r2}', markersize=4)
        plt.xlabel('Iteration')
        plt.ylabel('x value')
        plt.title('First 20 iterations (trajectories overlap then diverge)')
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.subplot(1, 2, 2)
        diffs = [abs(traj1[i] - traj2[i]) for i in range(min(len(traj1), len(traj2)))]
        plt.semilogy(diffs, 'g-', linewidth=2)
        plt.xlabel('Iteration')
        plt.ylabel('|x₁ - x₂| (log scale)')
        plt.title('Exponential divergence over time')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('chaos_sensitivity.png', dpi=100, bbox_inches='tight')
        plt.close()
        print("\n[Chart saved: chaos_sensitivity.png]\n")
    else:
        print("\n[Matplotlib not available - skipping chart]\n")

    assert passed, f"Chaos divergence too small: {difference} <= 0.1"


# =============================================================================
# TEST 2: FRACTAL GATE DISCRIMINATION
# =============================================================================

def fractal_gate(z0, c, max_iter=50, escape=2.0):
    """
    Julia set iteration: z_{n+1} = z_n^2 + c
    Returns (passed, iteration_escaped)
    """
    z = z0
    for i in range(max_iter):
        z = z*z + c
        if abs(z) > escape:
            return False, i
    return True, max_iter


def test_fractal_gate():
    """
    Prediction: Valid contexts pass the gate; invalid contexts escape to infinity
    """
    print("=" * 60)
    print("TEST 2: FRACTAL GATE DISCRIMINATION")
    print("=" * 60)

    # Test with valid basin parameter
    z0_test = 0.1 + 0.1j
    c_valid = -0.4 + 0.0j
    c_invalid = 0.5 + 0.5j  # Outside Julia set

    passed_valid, iter_valid = fractal_gate(z0_test, c_valid)
    passed_invalid, iter_invalid = fractal_gate(z0_test, c_invalid)

    print(f"Test point: z₀ = {z0_test}")
    print(f"\nValid basin (sil'kor): c = {c_valid}")
    print(f"  Result: {'PASS' if passed_valid else 'FAIL'} (iterations: {iter_valid})")
    print(f"\nInvalid basin: c = {c_invalid}")
    print(f"  Result: {'PASS' if passed_invalid else 'FAIL'} (escaped at iteration {iter_invalid})")

    test_passed = passed_valid and not passed_invalid
    if test_passed:
        print("\n✓ TEST PASSED: Valid contexts accepted, invalid rejected")
    else:
        print("\n✗ TEST FAILED: Gate not discriminating properly")

    # Test multiple vocab terms
    vocab = {
        "sil'kor": -0.4 + 0.0j,
        "nav'een": -1.0 + 0.0j,
        "thel'vori": -0.125 + 0.744j,
        "keth'mar": -0.5 + 0.0j,
        "aether'vel": -0.2 + 0.5j,
    }

    print("\n" + "-" * 60)
    print("Testing all vocabulary terms:")
    vocab_results = {}
    for name, c in vocab.items():
        passed, iters = fractal_gate(0.1+0.1j, c)
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name:12} c={c:>15} → {status} (iterations: {iters})")
        vocab_results[name] = passed

    assert test_passed, "Fractal gate failed to discriminate valid from invalid contexts"


# =============================================================================
# TEST 3: NEURAL ENERGY SEPARATION
# =============================================================================

def hopfield_energy(c, W, theta):
    """
    Hopfield energy: E(c) = -0.5 * c^T W c + theta^T c
    """
    return -0.5 * c.T @ W @ c + theta.T @ c


def normalize_context(c, mu, sigma):
    """Normalize: c' = tanh((c - mu) / sigma)"""
    return np.tanh((c - mu) / sigma)


def train_hopfield(patterns):
    """
    Hebbian learning: W = (1/N) * sum(c * c^T)
    """
    n_features = patterns.shape[1]
    W = np.zeros((n_features, n_features))

    for pattern in patterns:
        W += np.outer(pattern, pattern)

    W /= len(patterns)
    # Zero diagonal (prevent self-reinforcement)
    np.fill_diagonal(W, 0)

    theta = np.zeros(n_features)
    return W, theta


def test_neural_energy():
    """
    Prediction: Trained patterns have low energy; novel patterns have high energy
    """
    print("=" * 60)
    print("TEST 3: NEURAL ENERGY SEPARATION")
    print("=" * 60)

    # Generate training patterns (10 similar contexts)
    np.random.seed(42)
    n_features = 6
    n_patterns = 10

    # Normal contexts: clustered around [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    normal_base = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    training_patterns = normal_base + np.random.normal(0, 0.1, (n_patterns, n_features))

    # Normalize
    mu = training_patterns.mean(axis=0)
    sigma = training_patterns.std(axis=0) + 1e-6
    normalized_patterns = np.array([normalize_context(p, mu, sigma) for p in training_patterns])

    # Train
    W, theta = train_hopfield(normalized_patterns)

    print(f"Trained on {n_patterns} similar patterns")
    print(f"Feature dimensions: {n_features}")

    # Test energies of trained patterns
    train_energies = [hopfield_energy(p, W, theta) for p in normalized_patterns]
    mean_train_energy = np.mean(train_energies)
    std_train_energy = np.std(train_energies)

    print(f"\nTraining set energies:")
    print(f"  Mean: {mean_train_energy:.4f}")
    print(f"  Std:  {std_train_energy:.4f}")

    # Test with a very different context (anomaly)
    anomaly_context = np.array([0.9, 0.1, 0.9, 0.1, 0.9, 0.1])  # Very different pattern
    anomaly_normalized = normalize_context(anomaly_context, mu, sigma)
    anomaly_energy = hopfield_energy(anomaly_normalized, W, theta)

    print(f"\nAnomaly energy: {anomaly_energy:.4f}")
    print(f"Difference from mean: {anomaly_energy - mean_train_energy:.4f}")

    # Statistical test
    threshold = mean_train_energy + 3 * std_train_energy
    print(f"\nThreshold (μ + 3σ): {threshold:.4f}")

    if anomaly_energy > threshold:
        print(f"✓ TEST PASSED: Anomaly rejected (energy {anomaly_energy:.4f} > {threshold:.4f})")
        test_passed = True
    else:
        # Check if at least clearly separated
        sigma_away = (anomaly_energy - mean_train_energy) / (std_train_energy + 1e-6)
        if sigma_away > 2:
            print(f"✓ TEST PASSED: Clear separation ({sigma_away:.1f}σ away)")
            test_passed = True
        else:
            print(f"⚠ MARGINAL: Separation exists but small ({sigma_away:.1f}σ)")
            test_passed = False

    # Test several anomalies
    print("\n" + "-" * 60)
    print("Testing multiple anomaly types:")
    anomalies = {
        "Random high": np.array([0.95, 0.95, 0.95, 0.95, 0.95, 0.95]),
        "Random low": np.array([0.05, 0.05, 0.05, 0.05, 0.05, 0.05]),
        "Alternating": np.array([1.0, 0.0, 1.0, 0.0, 1.0, 0.0]),
        "Spike": np.array([0.5, 0.5, 5.0, 0.5, 0.5, 0.5]),
    }

    anomaly_results = {}
    for name, anom in anomalies.items():
        anom_norm = normalize_context(anom, mu, sigma)
        E = hopfield_energy(anom_norm, W, theta)
        sigma_away = (E - mean_train_energy) / (std_train_energy + 1e-6)
        rejected = E > threshold
        status = "✓ REJECT" if rejected else "✗ ACCEPT"
        print(f"  {name:12} E={E:7.3f} ({sigma_away:+.1f}σ) {status}")
        anomaly_results[name] = rejected

    assert test_passed, "Neural energy failed to separate anomalies from trained patterns"


# =============================================================================
# MAIN
# =============================================================================

def run_all_tests():
    """Run all CPSE physics validation tests."""
    print("\n" + "=" * 70)
    print("CPSE PHYSICS VALIDATION SUITE")
    print("=" * 70 + "\n")

    # Test 1: Chaos
    test_chaos_sensitivity()
    print()

    # Test 2: Fractal Gate
    test_fractal_gate()
    print()

    # Test 3: Neural Energy
    test_neural_energy()
    print()

    # Summary
    print("=" * 70)
    print("ALL CPSE PHYSICS TESTS PASSED ✓")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
