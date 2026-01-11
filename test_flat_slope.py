#!/usr/bin/env python3
"""
Flat Slope Harmonic Encoding - Test if the math makes sense

Test questions:
1. Can we encode different tokens at the same base frequency?
2. Can we decode them back correctly WITH the key?
3. Can an attacker WITHOUT the key distinguish tokens?
4. Does the interference pattern actually hide information?
"""

import numpy as np
import hmac
import hashlib
from typing import List, Tuple, Set
from collections import Counter

# Constants
BASE_FREQ = 440.0
SAMPLE_RATE = 44100
DURATION = 0.5
N_SAMPLES = int(SAMPLE_RATE * DURATION)


def get_harmonic_mask(token_id: int, secret_key: bytes, max_harmonics: int = 8) -> Set[int]:
    """
    Derive which harmonics are active for a given token.

    Returns set of harmonic indices (1-based).
    """
    mask_seed = hmac.new(
        secret_key,
        f"token:{token_id}".encode(),
        hashlib.sha256
    ).digest()

    harmonics = set()
    for h in range(1, max_harmonics + 1):
        # Use different bits for each harmonic decision
        if mask_seed[h % 32] > 128:  # ~50% chance
            harmonics.add(h)

    # Ensure at least one harmonic (fundamental)
    if not harmonics:
        harmonics.add(1)

    return harmonics


def flat_slope_encode(token_id: int, secret_key: bytes) -> Tuple[np.ndarray, Set[int]]:
    """
    Encode a token using flat slope (same base freq, different harmonics).
    """
    t = np.linspace(0, DURATION, N_SAMPLES, endpoint=False)
    harmonics = get_harmonic_mask(token_id, secret_key)

    signal = np.zeros(N_SAMPLES)
    for h in harmonics:
        amplitude = 1.0 / h  # Natural rolloff
        signal += amplitude * np.sin(2 * np.pi * BASE_FREQ * h * t)

    # Normalize
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal /= max_val

    return signal, harmonics


def analyze_spectrum(signal: np.ndarray) -> dict:
    """
    Analyze which harmonics are present in a signal.
    """
    # FFT
    spectrum = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), 1/SAMPLE_RATE)

    # Find peaks at harmonic frequencies
    detected_harmonics = {}
    for h in range(1, 17):
        target_freq = BASE_FREQ * h
        # Find closest bin
        idx = np.argmin(np.abs(freqs - target_freq))
        magnitude = spectrum[idx]

        # Normalize to max
        detected_harmonics[h] = magnitude / np.max(spectrum) if np.max(spectrum) > 0 else 0

    return detected_harmonics


def test_encoding_uniqueness():
    """
    Test 1: Do different tokens produce different harmonic signatures?
    """
    print("\n" + "="*60)
    print(" TEST 1: Encoding Uniqueness")
    print("="*60)

    secret_key = b"test_secret_key_12345"

    # Generate masks for tokens 0-7
    masks = {}
    for token_id in range(8):
        mask = get_harmonic_mask(token_id, secret_key)
        masks[token_id] = mask
        print(f"  Token {token_id}: harmonics {sorted(mask)}")

    # Check uniqueness
    mask_tuples = [tuple(sorted(m)) for m in masks.values()]
    unique_masks = len(set(mask_tuples))

    print(f"\n  Unique masks: {unique_masks}/8")

    if unique_masks == 8:
        print("  ✓ All tokens have unique harmonic signatures")
        return True
    else:
        print("  ✗ COLLISION: Some tokens have same signature!")
        # Find collisions
        counts = Counter(mask_tuples)
        for mask, count in counts.items():
            if count > 1:
                colliding = [t for t, m in masks.items() if tuple(sorted(m)) == mask]
                print(f"    Collision: tokens {colliding} both have {mask}")
        return False


def test_key_dependency():
    """
    Test 2: Do different keys produce different signatures for same token?
    """
    print("\n" + "="*60)
    print(" TEST 2: Key Dependency")
    print("="*60)

    key1 = b"secret_key_alpha"
    key2 = b"secret_key_beta"

    token_id = 3

    mask1 = get_harmonic_mask(token_id, key1)
    mask2 = get_harmonic_mask(token_id, key2)

    print(f"  Token {token_id} with key1: harmonics {sorted(mask1)}")
    print(f"  Token {token_id} with key2: harmonics {sorted(mask2)}")

    if mask1 != mask2:
        print("  ✓ Different keys produce different signatures")
        return True
    else:
        print("  ✗ PROBLEM: Same signature with different keys!")
        return False


def test_spectrum_analysis():
    """
    Test 3: Can we recover harmonics from the generated signal?
    """
    print("\n" + "="*60)
    print(" TEST 3: Spectrum Analysis (Encode → FFT → Decode)")
    print("="*60)

    secret_key = b"spectrum_test_key"

    all_correct = True
    for token_id in range(4):
        signal, expected_harmonics = flat_slope_encode(token_id, secret_key)
        detected = analyze_spectrum(signal)

        # Which harmonics are "present" (magnitude > 0.1)?
        threshold = 0.1
        detected_set = {h for h, mag in detected.items() if mag > threshold}

        print(f"\n  Token {token_id}:")
        print(f"    Expected: {sorted(expected_harmonics)}")
        print(f"    Detected: {sorted(detected_set)}")

        if detected_set == expected_harmonics:
            print(f"    ✓ Match!")
        else:
            print(f"    ✗ Mismatch!")
            all_correct = False

    return all_correct


def test_attacker_without_key():
    """
    Test 4: Can an attacker distinguish tokens without knowing the key?

    Attack: Collect multiple signals, try to cluster by spectrum similarity.
    """
    print("\n" + "="*60)
    print(" TEST 4: Attacker Without Key")
    print("="*60)

    secret_key = b"victim_secret_key"

    # Attacker intercepts 100 signals (unknown tokens)
    np.random.seed(42)
    intercepted = []
    true_labels = []

    for _ in range(100):
        token_id = np.random.randint(0, 8)
        signal, _ = flat_slope_encode(token_id, secret_key)
        spectrum = analyze_spectrum(signal)

        # Attacker only sees spectrum, not token_id
        feature_vector = [spectrum[h] for h in range(1, 9)]
        intercepted.append(feature_vector)
        true_labels.append(token_id)

    intercepted = np.array(intercepted)

    # Attacker tries k-means clustering
    from scipy.cluster.hierarchy import fcluster, linkage

    # Hierarchical clustering
    Z = linkage(intercepted, method='ward')
    predicted_clusters = fcluster(Z, t=8, criterion='maxclust')

    # How well do clusters match true labels?
    # (Adjusted Rand Index or simple purity)
    from collections import defaultdict

    cluster_contents = defaultdict(list)
    for i, cluster in enumerate(predicted_clusters):
        cluster_contents[cluster].append(true_labels[i])

    # Purity: fraction of samples in majority class per cluster
    total_correct = 0
    for cluster, labels in cluster_contents.items():
        majority = Counter(labels).most_common(1)[0][1]
        total_correct += majority

    purity = total_correct / len(true_labels)

    print(f"  Attacker clustering purity: {purity:.2%}")
    print(f"  (Random guess = 12.5%, Perfect = 100%)")

    if purity < 0.3:
        print("  ✓ Attacker cannot reliably distinguish tokens")
        return True
    elif purity < 0.6:
        print("  ⚠ Attacker has some ability to distinguish")
        return False
    else:
        print("  ✗ PROBLEM: Attacker can easily distinguish tokens!")
        return False


def test_with_key_decoding():
    """
    Test 5: Can legitimate receiver decode with the key?
    """
    print("\n" + "="*60)
    print(" TEST 5: Legitimate Decoding (with key)")
    print("="*60)

    secret_key = b"shared_secret_key"

    # Pre-compute all token signatures
    known_signatures = {}
    for token_id in range(8):
        mask = get_harmonic_mask(token_id, secret_key)
        known_signatures[tuple(sorted(mask))] = token_id

    # Receive and decode 20 random messages
    correct = 0
    total = 20

    np.random.seed(123)
    for _ in range(total):
        # Sender encodes
        true_token = np.random.randint(0, 8)
        signal, _ = flat_slope_encode(true_token, secret_key)

        # Receiver decodes
        detected = analyze_spectrum(signal)
        threshold = 0.1
        detected_set = frozenset(h for h, mag in detected.items() if mag > threshold)

        # Match to known signature
        decoded_token = None
        for sig, token_id in known_signatures.items():
            if set(sig) == detected_set:
                decoded_token = token_id
                break

        if decoded_token == true_token:
            correct += 1

    accuracy = correct / total
    print(f"  Decoding accuracy: {accuracy:.0%} ({correct}/{total})")

    if accuracy >= 0.95:
        print("  ✓ Legitimate receiver can decode reliably")
        return True
    else:
        print("  ✗ PROBLEM: Decoding is unreliable!")
        return False


def test_interference_multiple_tokens():
    """
    Test 6: What happens when multiple tokens are encoded simultaneously?
    (The "resonance refractoring" idea)
    """
    print("\n" + "="*60)
    print(" TEST 6: Multiple Token Interference")
    print("="*60)

    secret_key = b"interference_test"

    # Encode tokens 0, 1, 2 separately
    signal_0, mask_0 = flat_slope_encode(0, secret_key)
    signal_1, mask_1 = flat_slope_encode(1, secret_key)
    signal_2, mask_2 = flat_slope_encode(2, secret_key)

    print(f"  Token 0 harmonics: {sorted(mask_0)}")
    print(f"  Token 1 harmonics: {sorted(mask_1)}")
    print(f"  Token 2 harmonics: {sorted(mask_2)}")

    # Combined signal (all three at once)
    combined = signal_0 + signal_1 + signal_2
    combined /= np.max(np.abs(combined))

    # What harmonics are in the combined signal?
    combined_spectrum = analyze_spectrum(combined)
    threshold = 0.1
    combined_harmonics = {h for h, mag in combined_spectrum.items() if mag > threshold}

    expected_union = mask_0 | mask_1 | mask_2

    print(f"\n  Combined harmonics detected: {sorted(combined_harmonics)}")
    print(f"  Expected (union): {sorted(expected_union)}")

    # Problem: We can't separate them!
    print(f"\n  Can we separate which harmonic came from which token?")

    # Check for overlaps
    overlap_01 = mask_0 & mask_1
    overlap_02 = mask_0 & mask_2
    overlap_12 = mask_1 & mask_2

    if overlap_01 or overlap_02 or overlap_12:
        print(f"  ✗ PROBLEM: Harmonics overlap!")
        print(f"    Token 0 ∩ Token 1: {sorted(overlap_01) if overlap_01 else 'none'}")
        print(f"    Token 0 ∩ Token 2: {sorted(overlap_02) if overlap_02 else 'none'}")
        print(f"    Token 1 ∩ Token 2: {sorted(overlap_12) if overlap_12 else 'none'}")
        print(f"  → Cannot decode multiple tokens from single signal!")
        return False
    else:
        print(f"  ✓ No overlap - tokens have disjoint harmonics")
        print(f"  → Could potentially separate them")
        return True


def run_all_tests():
    """Run all tests and summarize."""
    print("\n" + "#"*60)
    print(" FLAT SLOPE HARMONIC ENCODING - VALIDATION")
    print("#"*60)

    results = {}

    results['uniqueness'] = test_encoding_uniqueness()
    results['key_dependency'] = test_key_dependency()
    results['spectrum_recovery'] = test_spectrum_analysis()
    results['attacker_resistance'] = test_attacker_without_key()
    results['legitimate_decoding'] = test_with_key_decoding()
    results['interference'] = test_interference_multiple_tokens()

    print("\n" + "="*60)
    print(" SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(results.values())

    print("\n" + "="*60)
    if all_passed:
        print(" VERDICT: Math checks out! ✓")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f" VERDICT: Issues found in: {failed}")
    print("="*60 + "\n")

    return all_passed


if __name__ == "__main__":
    run_all_tests()
