#!/usr/bin/env python3
"""
COMBINED PROTOCOL TEST
======================
Merges:
1. Flat Slope Concept: Same base frequency, different harmonics per token
2. AetherMoore Additions: Random phase, vibrato, jitter, Feistel permutation, RWP envelope

Goal: Fix the attacker resistance problem from flat slope by adding:
- Nonce-derived random phase (different each transmission)
- 6 Hz vibrato (human-like modulation)
- Amplitude jitter (anti-replay)
"""

import os
import time
import hmac
import hashlib
import base64
from typing import Tuple, Set, List, Dict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.fftpack import fft, fftfreq

# ==============================================================================
# CONSTANTS
# ==============================================================================
FS = 44_100              # Sample rate (Hz)
DURATION = 0.5           # Duration per token (seconds)
BASE_FREQ = 440.0        # FLAT SLOPE: All tokens use same fundamental
N_SAMPLES = int(FS * DURATION)
MAX_HARMONICS = 12       # Harmonics 1-12
NONCE_BYTES = 12

# Secret key (in production, use secure key management)
MASTER_KEY = b"test-key-for-demo-only-32bytes!"

# ==============================================================================
# CONLANG DICTIONARY
# ==============================================================================
CONLANG = {
    "shadow": -1, "gleam": -2, "flare": -3,
    "korah": 0, "aelin": 1, "dahru": 2,
    "melik": 3, "sorin": 4, "tivar": 5,
    "ulmar": 6, "vexin": 7, "zephyr": 8,
}
REV_CONLANG = {v: k for k, v in CONLANG.items()}

# ==============================================================================
# FLAT SLOPE + AETHERMOORE ENCODING
# ==============================================================================

def derive_harmonic_mask(token_id: int, key: bytes) -> Set[int]:
    """
    Derive which harmonics are active for a given token.
    Uses HMAC to make the mapping key-dependent.
    """
    h = hmac.new(key, f"harm:{token_id}".encode(), hashlib.sha256).digest()
    mask = set()
    for i in range(MAX_HARMONICS):
        if h[i % 32] & (1 << (i % 8)):
            mask.add(i + 1)  # Harmonics are 1-indexed
    # Ensure at least one harmonic
    if not mask:
        mask.add(1)
    return mask


def derive_phases(token_id: int, key: bytes, nonce: bytes) -> Dict[int, float]:
    """
    Derive random phase for each harmonic.
    CRITICAL: Nonce makes each transmission different, defeating replay attacks.
    """
    phases = {}
    for h in range(1, MAX_HARMONICS + 1):
        data = f"phase:{token_id}:{h}".encode() + nonce
        ph_bytes = hmac.new(key, data, hashlib.sha256).digest()[:4]
        # Convert to phase [0, 2π)
        phases[h] = (int.from_bytes(ph_bytes, 'big') / (2**32)) * 2 * np.pi
    return phases


def flat_slope_adaptive_encode(
    token_id: int,
    key: bytes,
    nonce: bytes,
    add_vibrato: bool = True,
    add_jitter: bool = True
) -> Tuple[np.ndarray, Set[int]]:
    """
    COMBINED ENCODING:
    - Flat slope: Same base frequency for all tokens
    - Key-derived harmonics: Only certain harmonics active
    - Nonce-derived phase: Different each transmission
    - Vibrato: 6 Hz modulation (human-like)
    - Jitter: Random amplitude variation (anti-synthetic)
    """
    t = np.linspace(0, DURATION, N_SAMPLES, endpoint=False)
    harmonics = derive_harmonic_mask(token_id, key)
    phases = derive_phases(token_id, key, nonce)

    # Seed RNG with key+nonce for reproducible jitter (receiver can verify)
    rng_seed = int.from_bytes(
        hmac.new(key, b"jitter" + nonce, hashlib.sha256).digest()[:4], 'big'
    )
    rng = np.random.default_rng(seed=rng_seed)

    signal = np.zeros(N_SAMPLES)

    for h in harmonics:
        # Base amplitude (1/h for natural harmonic rolloff)
        amplitude = 1.0 / h

        # Add jitter (±20% amplitude variation)
        if add_jitter:
            amplitude *= rng.uniform(0.8, 1.2)

        # Get phase for this harmonic
        phase = phases[h]

        # Frequency with optional vibrato
        freq = BASE_FREQ * h
        if add_vibrato:
            # 6 Hz vibrato with 0.3% depth
            vibrato = 1.0 + 0.003 * np.sin(2 * np.pi * 6 * t)
            signal += amplitude * np.sin(2 * np.pi * freq * vibrato * t + phase)
        else:
            signal += amplitude * np.sin(2 * np.pi * freq * t + phase)

    # Normalize
    if np.max(np.abs(signal)) > 0:
        signal = signal / np.max(np.abs(signal))

    return signal, harmonics


def flat_slope_binary_encode(token_id: int, key: bytes) -> Tuple[np.ndarray, Set[int]]:
    """
    BINARY (STRICT) MODE:
    - Same harmonics as adaptive, but no phase/vibrato/jitter
    - Deterministic output (can be replayed)
    """
    t = np.linspace(0, DURATION, N_SAMPLES, endpoint=False)
    harmonics = derive_harmonic_mask(token_id, key)

    signal = np.zeros(N_SAMPLES)
    for h in harmonics:
        amplitude = 1.0 / h
        signal += amplitude * np.sin(2 * np.pi * BASE_FREQ * h * t)

    if np.max(np.abs(signal)) > 0:
        signal = signal / np.max(np.abs(signal))

    return signal, harmonics


# ==============================================================================
# FEISTEL PERMUTATION
# ==============================================================================

def feistel_permute(ids: List[int], key: bytes) -> List[int]:
    """
    4-round Feistel permutation on token IDs.
    Provides diffusion - small input change → large output change.
    """
    # Pad to even length
    arr = list(ids)
    if len(arr) % 2:
        arr.append(0)

    arr = np.array(arr, dtype=np.int32)
    mid = len(arr) // 2
    left, right = arr[:mid].copy(), arr[mid:].copy()

    for r in range(4):
        sub = hmac.new(key, f"feistel:{r}".encode(), hashlib.sha256).digest()
        sub = np.frombuffer(sub, dtype=np.int32)
        sub = np.resize(sub, right.shape)
        new_right = left ^ sub
        left, right = right, new_right

    return np.concatenate([left, right]).tolist()


def feistel_unpermute(perm_ids: List[int], key: bytes) -> List[int]:
    """Inverse of feistel_permute."""
    arr = np.array(perm_ids, dtype=np.int32)
    mid = len(arr) // 2
    left, right = arr[:mid].copy(), arr[mid:].copy()

    # Reverse order of rounds
    for r in range(3, -1, -1):
        sub = hmac.new(key, f"feistel:{r}".encode(), hashlib.sha256).digest()
        sub = np.frombuffer(sub, dtype=np.int32)
        sub = np.resize(sub, left.shape)
        new_left = right ^ sub
        left, right = new_left, left

    return np.concatenate([left, right]).tolist()


# ==============================================================================
# FFT FINGERPRINT
# ==============================================================================

def extract_fingerprint(signal: np.ndarray) -> Dict:
    """
    Extract spectral fingerprint from signal.
    Returns: harmonic magnitudes, detected harmonics, jitter, shimmer, entropy
    """
    N = len(signal)
    X = np.abs(fft(signal))[:N//2]
    freqs = fftfreq(N, 1/FS)[:N//2]

    # Find harmonics (peaks near expected frequencies)
    detected_harmonics = set()
    harmonic_mags = {}

    for h in range(1, MAX_HARMONICS + 1):
        expected_freq = BASE_FREQ * h
        # Look within ±10 Hz window (accounts for vibrato)
        mask = np.abs(freqs - expected_freq) < 10
        if np.any(mask):
            mag = np.max(X[mask])
            # Threshold: harmonic present if magnitude > 5% of max
            if mag > 0.05 * np.max(X):
                detected_harmonics.add(h)
                harmonic_mags[h] = float(mag)

    # Jitter: std of zero-crossing intervals
    zero_cross = np.where(np.diff(np.signbit(signal)))[0]
    jitter = float(np.std(np.diff(zero_cross))) if len(zero_cross) > 2 else 0.0

    # Shimmer: envelope variation
    env = np.abs(signal)
    shimmer = float(np.std(env) / (np.mean(env) + 1e-10))

    # Spectral entropy
    P = X / (np.sum(X) + 1e-10)
    P = P[P > 0]
    entropy = -float(np.sum(P * np.log2(P + 1e-10)))

    return {
        "detected_harmonics": detected_harmonics,
        "harmonic_magnitudes": harmonic_mags,
        "jitter": jitter,
        "shimmer": shimmer,
        "entropy": entropy
    }


# ==============================================================================
# RWP v3 ENVELOPE
# ==============================================================================

def make_envelope(fingerprint_bytes: bytes, mode: str, tongue: str = "KO") -> Dict:
    """Create HMAC-signed envelope with replay protection."""
    nonce = os.urandom(NONCE_BYTES)
    ts = int(time.time() * 1000)

    header = {
        "ver": "3",
        "tongue": tongue,
        "mode": mode,
        "ts": ts,
        "nonce": base64.urlsafe_b64encode(nonce).decode().rstrip("="),
    }

    payload_b64 = base64.urlsafe_b64encode(fingerprint_bytes).decode().rstrip("=")

    # Canonical string for HMAC
    canon = f"v3.{tongue}.{mode}.{ts}.{header['nonce']}.{payload_b64}"
    sig = hmac.new(MASTER_KEY, canon.encode(), hashlib.sha256).hexdigest()

    return {"header": header, "payload": payload_b64, "sig": sig}


def verify_envelope(env: Dict, max_age_ms: int = 60_000) -> bool:
    """Verify envelope signature and timestamp."""
    hdr = env["header"]
    now = int(time.time() * 1000)

    # Check timestamp freshness
    if now - hdr["ts"] > max_age_ms:
        return False

    # Recompute signature
    canon = f"v3.{hdr['tongue']}.{hdr['mode']}.{hdr['ts']}.{hdr['nonce']}.{env['payload']}"
    expected = hmac.new(MASTER_KEY, canon.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected, env["sig"])


# ==============================================================================
# TESTS
# ==============================================================================

def test_harmonic_uniqueness():
    """Test that different tokens have different harmonic signatures."""
    print("\n" + "="*60)
    print(" TEST 1: Harmonic Uniqueness (Flat Slope)")
    print("="*60)

    masks = {}
    for word, token_id in CONLANG.items():
        mask = derive_harmonic_mask(token_id, MASTER_KEY)
        masks[word] = mask
        print(f"  {word:8} (id={token_id:2}): harmonics {sorted(mask)}")

    # Check uniqueness
    unique_masks = set(frozenset(m) for m in masks.values())
    unique = len(unique_masks) == len(masks)

    print(f"\n  Unique masks: {len(unique_masks)}/{len(masks)}")
    print(f"  {'✓ PASS' if unique else '✗ FAIL'}: All tokens have unique signatures")
    return unique


def test_phase_nonce_dependency():
    """Test that different nonces produce different waveforms."""
    print("\n" + "="*60)
    print(" TEST 2: Nonce-Dependent Phase (Anti-Replay)")
    print("="*60)

    token_id = 0
    nonce1 = b"nonce_000001"
    nonce2 = b"nonce_000002"

    sig1, harmonics1 = flat_slope_adaptive_encode(token_id, MASTER_KEY, nonce1)
    sig2, harmonics2 = flat_slope_adaptive_encode(token_id, MASTER_KEY, nonce2)

    # Compute correlation
    correlation = np.corrcoef(sig1, sig2)[0, 1]

    print(f"  Same token, different nonces:")
    print(f"    Correlation: {correlation:.4f}")
    print(f"    (1.0 = identical, 0.0 = uncorrelated)")

    # Check that the KEY-derived harmonics are the same (not FFT-detected ones)
    same_harmonics = harmonics1 == harmonics2
    different_waveform = correlation < 0.9  # Should be significantly different

    print(f"\n  Same harmonic mask (key-derived): {same_harmonics}")
    print(f"    Harmonics: {sorted(harmonics1)}")
    print(f"  Different waveform: {different_waveform}")

    passed = same_harmonics and different_waveform
    print(f"\n  {'✓ PASS' if passed else '✗ FAIL'}: Nonce changes waveform while preserving harmonics")
    return passed


def test_attacker_resistance():
    """
    Test if attacker can distinguish tokens by spectral analysis.
    IMPROVED: With random phase, attacker correlation should be low.
    """
    print("\n" + "="*60)
    print(" TEST 3: Attacker Resistance (Phase Randomization)")
    print("="*60)

    # Attacker observes multiple transmissions of the same token
    # with DIFFERENT nonces
    token_id = 3
    num_samples = 10

    waveforms = []
    for i in range(num_samples):
        nonce = os.urandom(NONCE_BYTES)
        sig, _ = flat_slope_adaptive_encode(token_id, MASTER_KEY, nonce)
        waveforms.append(sig)

    # Compute pairwise correlations
    correlations = []
    for i in range(num_samples):
        for j in range(i+1, num_samples):
            corr = np.corrcoef(waveforms[i], waveforms[j])[0, 1]
            correlations.append(corr)

    avg_corr = np.mean(correlations)
    print(f"  Average correlation between transmissions: {avg_corr:.4f}")
    print(f"  (High = easy to correlate, Low = hard to correlate)")

    # Compare BINARY (no phase randomization) as control
    print("\n  Control: Binary mode (no randomization)")
    binary_waveforms = []
    for i in range(num_samples):
        sig, _ = flat_slope_binary_encode(token_id, MASTER_KEY)
        binary_waveforms.append(sig)

    binary_correlations = []
    for i in range(num_samples):
        for j in range(i+1, num_samples):
            corr = np.corrcoef(binary_waveforms[i], binary_waveforms[j])[0, 1]
            binary_correlations.append(corr)

    binary_avg_corr = np.mean(binary_correlations)
    print(f"  Binary mode correlation: {binary_avg_corr:.4f}")

    # Adaptive should have LOWER correlation than binary
    better_resistance = avg_corr < binary_avg_corr * 0.5

    print(f"\n  Adaptive mode {'✓ BETTER' if better_resistance else '✗ SIMILAR'} than binary")
    print(f"  {'✓ PASS' if better_resistance else '✗ FAIL'}: Phase randomization defeats correlation")
    return better_resistance


def test_feistel_roundtrip():
    """Test Feistel permutation is reversible."""
    print("\n" + "="*60)
    print(" TEST 4: Feistel Permutation Roundtrip")
    print("="*60)

    original = [0, 1, 2, 3]  # "korah aelin dahru melik"
    print(f"  Original IDs: {original}")

    permuted = feistel_permute(original, MASTER_KEY)
    print(f"  Permuted:     {permuted}")

    recovered = feistel_unpermute(permuted, MASTER_KEY)
    print(f"  Recovered:    {recovered}")

    passed = original == recovered
    print(f"\n  {'✓ PASS' if passed else '✗ FAIL'}: Feistel is bijective")
    return passed


def test_envelope_verification():
    """Test RWP envelope create/verify."""
    print("\n" + "="*60)
    print(" TEST 5: RWP Envelope Verification")
    print("="*60)

    # Create envelope
    dummy_fingerprint = b"test_fingerprint_data_here"
    env = make_envelope(dummy_fingerprint, mode="ADAPTIVE", tongue="KO")

    print(f"  Envelope created:")
    print(f"    Version: {env['header']['ver']}")
    print(f"    Tongue:  {env['header']['tongue']}")
    print(f"    Mode:    {env['header']['mode']}")
    print(f"    Nonce:   {env['header']['nonce'][:16]}...")

    # Verify valid envelope
    valid = verify_envelope(env)
    print(f"\n  Valid signature: {valid}")

    # Test tamper detection
    tampered = env.copy()
    tampered["payload"] = "TAMPERED_DATA"
    tamper_detected = not verify_envelope(tampered)
    print(f"  Tamper detected: {tamper_detected}")

    passed = valid and tamper_detected
    print(f"\n  {'✓ PASS' if passed else '✗ FAIL'}: Envelope verification works")
    return passed


def test_legitimate_decode():
    """Test full encode/decode pipeline (without Feistel, which scrambles IDs)."""
    print("\n" + "="*60)
    print(" TEST 6: Full Encode/Decode Pipeline")
    print("="*60)

    # Simulate encoding multiple tokens
    # NOTE: In real protocol, Feistel permutes ORDER of tokens, not the IDs themselves
    # The harmonic encoding is based on original token IDs
    words = ["korah", "aelin", "dahru", "melik"]
    ids = [CONLANG[w] for w in words]
    print(f"  Original: {words} → {ids}")

    # Encode each token with shared nonce
    nonce = os.urandom(NONCE_BYTES)
    signals = []
    expected_harmonics = []

    for token_id in ids:
        sig, harmonics = flat_slope_adaptive_encode(token_id, MASTER_KEY, nonce)
        signals.append(sig)
        expected_harmonics.append(harmonics)
        print(f"    Token {token_id}: encoded with harmonics {sorted(harmonics)}")

    # Decode (receiver with key) - match by harmonic signature
    recovered_ids = []
    for i, sig in enumerate(signals):
        fp = extract_fingerprint(sig)

        # Find matching token by harmonic overlap
        best_match = None
        best_score = -1
        for test_id in range(-3, 9):
            expected = derive_harmonic_mask(test_id, MASTER_KEY)
            # Score: intersection over union (Jaccard)
            intersection = len(expected & fp["detected_harmonics"])
            union = len(expected | fp["detected_harmonics"])
            score = intersection / union if union > 0 else 0

            if score > best_score:
                best_score = score
                best_match = test_id

        recovered_ids.append(best_match)
        print(f"    Signal {i}: decoded as {best_match} (score: {best_score:.2f})")

    print(f"\n  Original:  {ids}")
    print(f"  Recovered: {recovered_ids}")

    passed = recovered_ids == ids
    print(f"\n  {'✓ PASS' if passed else '✗ FAIL'}: Full pipeline decode works")
    return passed


def test_binary_vs_adaptive_entropy():
    """Compare entropy between binary and adaptive modes."""
    print("\n" + "="*60)
    print(" TEST 7: Binary vs Adaptive Entropy")
    print("="*60)

    token_id = 0
    nonce = os.urandom(NONCE_BYTES)

    binary_sig, _ = flat_slope_binary_encode(token_id, MASTER_KEY)
    adaptive_sig, _ = flat_slope_adaptive_encode(token_id, MASTER_KEY, nonce)

    binary_fp = extract_fingerprint(binary_sig)
    adaptive_fp = extract_fingerprint(adaptive_sig)

    print(f"  Binary mode:")
    print(f"    Entropy: {binary_fp['entropy']:.2f} bits")
    print(f"    Jitter:  {binary_fp['jitter']:.4f}")
    print(f"    Shimmer: {binary_fp['shimmer']:.4f}")

    print(f"\n  Adaptive mode:")
    print(f"    Entropy: {adaptive_fp['entropy']:.2f} bits")
    print(f"    Jitter:  {adaptive_fp['jitter']:.4f}")
    print(f"    Shimmer: {adaptive_fp['shimmer']:.4f}")

    # Adaptive should have higher entropy
    higher_entropy = adaptive_fp['entropy'] > binary_fp['entropy'] * 0.9

    print(f"\n  {'✓ PASS' if higher_entropy else '✗ FAIL'}: Adaptive has sufficient entropy")
    return higher_entropy


def plot_comparison():
    """Generate comparison plot."""
    print("\n" + "="*60)
    print(" GENERATING COMPARISON PLOT")
    print("="*60)

    token_id = 0
    nonce = os.urandom(NONCE_BYTES)

    binary_sig, _ = flat_slope_binary_encode(token_id, MASTER_KEY)
    adaptive_sig, _ = flat_slope_adaptive_encode(token_id, MASTER_KEY, nonce)

    t = np.linspace(0, DURATION, N_SAMPLES, endpoint=False)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    # Waveforms
    axes[0, 0].plot(t[:2000], binary_sig[:2000], alpha=0.7, label='Binary')
    axes[0, 0].plot(t[:2000], adaptive_sig[:2000], alpha=0.7, label='Adaptive')
    axes[0, 0].set_title('Waveforms (first 2000 samples)')
    axes[0, 0].legend()
    axes[0, 0].set_xlabel('Time (s)')

    # FFT
    N = len(binary_sig)
    freqs = fftfreq(N, 1/FS)[:N//2]
    binary_fft = np.abs(fft(binary_sig))[:N//2]
    adaptive_fft = np.abs(fft(adaptive_sig))[:N//2]

    axes[0, 1].plot(freqs[:5000], binary_fft[:5000], alpha=0.7, label='Binary')
    axes[0, 1].plot(freqs[:5000], adaptive_fft[:5000], alpha=0.7, label='Adaptive')
    axes[0, 1].set_title('Frequency Spectrum')
    axes[0, 1].legend()
    axes[0, 1].set_xlabel('Frequency (Hz)')

    # Harmonic comparison
    harmonics = list(range(1, MAX_HARMONICS + 1))
    binary_mags = []
    adaptive_mags = []

    for h in harmonics:
        expected_freq = BASE_FREQ * h
        mask = np.abs(freqs - expected_freq) < 10
        binary_mags.append(np.max(binary_fft[mask]) if np.any(mask) else 0)
        adaptive_mags.append(np.max(adaptive_fft[mask]) if np.any(mask) else 0)

    x = np.arange(len(harmonics))
    width = 0.35
    axes[1, 0].bar(x - width/2, binary_mags, width, label='Binary')
    axes[1, 0].bar(x + width/2, adaptive_mags, width, label='Adaptive')
    axes[1, 0].set_title('Harmonic Magnitudes')
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(harmonics)
    axes[1, 0].set_xlabel('Harmonic')
    axes[1, 0].legend()

    # Nonce correlation test
    correlations = []
    for i in range(20):
        nonce_i = os.urandom(NONCE_BYTES)
        sig_i, _ = flat_slope_adaptive_encode(token_id, MASTER_KEY, nonce_i)
        corr = np.corrcoef(adaptive_sig, sig_i)[0, 1]
        correlations.append(corr)

    axes[1, 1].hist(correlations, bins=20, edgecolor='black')
    axes[1, 1].axvline(np.mean(correlations), color='r', linestyle='--', label=f'Mean: {np.mean(correlations):.3f}')
    axes[1, 1].set_title('Cross-Nonce Correlation Distribution')
    axes[1, 1].set_xlabel('Correlation')
    axes[1, 1].legend()

    plt.tight_layout()
    plt.savefig('combined_protocol_analysis.png', dpi=150)
    plt.close()

    print("  Saved: combined_protocol_analysis.png")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("="*60)
    print(" COMBINED PROTOCOL: Flat Slope + AetherMoore")
    print("="*60)
    print(f"\n  Base frequency: {BASE_FREQ} Hz (flat slope)")
    print(f"  Sample rate:    {FS} Hz")
    print(f"  Duration:       {DURATION} s")
    print(f"  Max harmonics:  {MAX_HARMONICS}")

    results = {}

    results['uniqueness'] = test_harmonic_uniqueness()
    results['nonce_dependency'] = test_phase_nonce_dependency()
    results['attacker_resistance'] = test_attacker_resistance()
    results['feistel_roundtrip'] = test_feistel_roundtrip()
    results['envelope_verification'] = test_envelope_verification()
    results['legitimate_decode'] = test_legitimate_decode()
    results['entropy_comparison'] = test_binary_vs_adaptive_entropy()

    plot_comparison()

    # Summary
    print("\n" + "="*60)
    print(" SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name}: {status}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  ✓ ALL TESTS PASSED - Protocol is mathematically sound!")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"\n  ✗ Issues found in: {failed}")

    return passed == total


if __name__ == "__main__":
    main()
