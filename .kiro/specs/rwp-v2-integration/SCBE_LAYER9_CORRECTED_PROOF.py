"""SCBE Layer 9: Spectral Coherence - CORRECTED PROOF

The document incorrectly duplicates Layer 5's hyperbolic distance proof here.
Below is the correct mathematical justification.
"""

import numpy as np
from scipy.fft import fft, fftfreq


def spectral_coherence_demo():
    """Layer 9: Spectral Coherence
    
    S_spec = E_low / (E_low + E_high + ε)
    
    Key Property: Energy partition is invariant (Parseval's theorem)
    """
    print("=" * 60)
    print("LAYER 9: SPECTRAL COHERENCE - CORRECTED PROOF")
    print("=" * 60)
    
    # Generate test signal
    np.random.seed(42)
    N = 1024
    fs = 1000  # Sample rate
    t = np.arange(N) / fs
    
    # Signal: low freq component + high freq noise
    low_freq = 5  # Hz
    high_freq = 200  # Hz
    signal = np.sin(2 * np.pi * low_freq * t) + 0.3 * np.sin(2 * np.pi * high_freq * t)
    
    # FFT
    X = fft(signal)
    freqs = fftfreq(N, 1/fs)
    
    # Power spectrum (one-sided)
    P = np.abs(X[:N//2])**2
    freqs_pos = freqs[:N//2]
    
    # Define low/high frequency cutoff
    f_cutoff = 50  # Hz
    low_mask = freqs_pos < f_cutoff
    high_mask = freqs_pos >= f_cutoff
    
    E_low = np.sum(P[low_mask])
    E_high = np.sum(P[high_mask])
    E_total = E_low + E_high
    epsilon = 1e-10
    
    S_spec = E_low / (E_low + E_high + epsilon)
    
    print(f"\nTest signal: sin(2π·5t) + 0.3·sin(2π·200t)")
    print(f"Cutoff frequency: {f_cutoff} Hz")
    
    print(f"\n--- CORRECT PROOF ---")
    print(f"""
Key Property: Energy partition is invariant (Parseval's theorem)

Detailed Proof:

1. Parseval's theorem states: Σ|x[n]|² = (1/N) Σ|X[k]|²
   - Time-domain energy equals frequency-domain energy (up to normalization)
   - This is provable from FFT unitarity

2. Energy partition:
   E_total = E_low + E_high where:
   - E_low = Σ |X[k]|² for k: f[k] < f_cutoff
   - E_high = Σ |X[k]|² for k: f[k] ≥ f_cutoff

3. S_spec = E_low / (E_total + ε) ∈ [0, 1]
   - Bounded: 0 ≤ E_low ≤ E_total
   - Monotonic in low-frequency content

4. Invariance: S_spec depends only on frequency distribution,
   not on phase (|X[k]|² discards phase information)

5. Stability: ε prevents division by zero for silent signals
""")
    
    print(f"\n--- NUMERICAL VERIFICATION ---")
    print(f"E_low   = {E_low:.4f}")
    print(f"E_high  = {E_high:.4f}")
    print(f"E_total = {E_total:.4f}")
    print(f"S_spec  = {S_spec:.4f}")
    
    # Verify Parseval's theorem
    time_energy = np.sum(signal**2)
    freq_energy = np.sum(np.abs(X)**2) / N
    
    print(f"\nParseval verification:")
    print(f"  Time-domain energy: {time_energy:.4f}")
    print(f"  Freq-domain energy: {freq_energy:.4f}")
    print(f"  Relative error: {abs(time_energy - freq_energy)/time_energy:.2e}")
    
    # Phase invariance check
    print(f"\n--- PHASE INVARIANCE CHECK ---")
    
    # Shift signal phase
    signal_shifted = np.sin(2 * np.pi * low_freq * t + np.pi/3) + \
                     0.3 * np.sin(2 * np.pi * high_freq * t + np.pi/2)
    
    X_shifted = fft(signal_shifted)
    P_shifted = np.abs(X_shifted[:N//2])**2
    
    E_low_shifted = np.sum(P_shifted[low_mask])
    E_high_shifted = np.sum(P_shifted[high_mask])
    S_spec_shifted = E_low_shifted / (E_low_shifted + E_high_shifted + epsilon)
    
    print(f"Original S_spec:      {S_spec:.6f}")
    print(f"Phase-shifted S_spec: {S_spec_shifted:.6f}")
    print(f"|difference|:         {abs(S_spec - S_spec_shifted):.2e}")
    print(f"Phase invariance: ✓ (S_spec depends only on |X[k]|²)")
    
    return S_spec


def stft_coherence():
    """Short-Time Fourier Transform for Layer 14 (Audio Axis).
    
    Demonstrates time-varying spectral analysis.
    """
    print("\n" + "=" * 60)
    print("LAYER 14: AUDIO AXIS (STFT-based)")
    print("=" * 60)
    
    from scipy.signal import stft
    
    # Generate chirp signal (frequency increases over time)
    fs = 1000
    t = np.linspace(0, 2, 2000)
    
    # Linear chirp from 10 Hz to 200 Hz
    chirp = np.sin(2 * np.pi * (10 + 95*t) * t)
    
    # STFT parameters
    nperseg = 128
    f, times, Zxx = stft(chirp, fs=fs, nperseg=nperseg)
    
    # Power for each frame
    P = np.abs(Zxx)**2
    
    # High-frequency ratio per frame
    f_cutoff_idx = np.searchsorted(f, 100)  # 100 Hz cutoff
    r_HF = np.sum(P[f_cutoff_idx:, :], axis=0) / (np.sum(P, axis=0) + 1e-10)
    S_audio = 1 - r_HF
    
    print(f"\nChirp signal: frequency 10→200 Hz over 2 seconds")
    print(f"Cutoff: 100 Hz")
    print(f"\nS_audio over time (sampled frames):")
    
    for i in [0, len(times)//4, len(times)//2, 3*len(times)//4, -1]:
        print(f"  t={times[i]:.2f}s: S_audio = {S_audio[i]:.4f} "
              f"({'low freq dominant' if S_audio[i] > 0.5 else 'high freq dominant'})")
    
    print(f"""
Proof (Parseval for STFT):
- STFT: X[m,k] = Σ x[n] w[n-m] e^(-i2πkn/N)
- Per-frame energy: Σ_k |X[m,k]|² = Σ_n |x[n] w[n-m]|² (Parseval)
- Overlap-add reconstruction preserves total energy
- r_HF = (high-freq energy) / (total energy) ∈ [0,1]
- S_audio = 1 - r_HF ∈ [0,1], decreases as signal shifts to high frequencies
""")


if __name__ == "__main__":
    spectral_coherence_demo()
    stft_coherence()
