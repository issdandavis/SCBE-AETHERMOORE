"""Test the 'vibration = integers' review's load-bearing claims on actual waves.

Each claim is reproducible with an FFT in milliseconds; verify, don't restate.

A. "composite = chord" — does the chord of modes 2 and 3 contain a 6?  (claim: NO)
B. nonlinearity on that chord — does it produce the additive SUMSET {1,4,5,6}? (claim: YES)
C. cascaded harmonic generation — does 2nd-harmonic-of-3rd-harmonic land on 6? (claim: YES = 2x3)
D. lcm vs gcd — does the joint waveform of modes 30 and 42 realign at T0/gcd=T0/6,
   with fundamental gcd*f0 = 6f0 (missing fundamental), NOT lcm=210?  (claim: gcd, not lcm)
E. "modulo = phase wrapping" — does a tone at n*f0 strobed at 30f0 alias to (n mod 30)*f0,
   and does REAL sampling fold the 8 wheel lanes to 4 conjugate pairs?  (claim: YES, 8->4)
F. "integer = mode number" — is it 1D-only? circular-membrane (drum) ratios = Bessel zeros
   1 : 1.59 : 2.14, not integers.  (claim: integers are a 1D fact)
"""

from __future__ import annotations

import numpy as np

N = 6000  # samples per unit window [0,1): FFT bin k == frequency k cycles/window


def spectrum(signal: np.ndarray) -> np.ndarray:
    """Magnitude of rfft, bin k = k cycles per window."""
    return np.abs(np.fft.rfft(signal)) * (2.0 / len(signal))


def peaks(mag: np.ndarray, thresh: float = 0.05) -> list[int]:
    return [k for k in range(len(mag)) if mag[k] > thresh]


def main() -> None:
    t = np.arange(N) / N  # one window of the fundamental, f0 = 1 cycle/window

    print("A. CHORD 2+3 — superposition keeps frequencies separate")
    chord = np.sin(2 * np.pi * 2 * t) + np.sin(2 * np.pi * 3 * t)
    m = spectrum(chord)
    print(f"   peaks: {peaks(m)}   |   magnitude at bin 6 = {m[6]:.2e}")
    print(f"   -> 6 present? {'YES' if m[6] > 0.05 else 'NO'}  (claim: NO)")

    print("\nB. NONLINEARITY on the chord — additive sumset, no primality")
    m2 = spectrum(chord**2)
    pk = peaks(m2)
    print(f"   peaks of (chord)^2 (excl DC bin 0): {[k for k in pk if k != 0]}")
    print("   labels: 3-2=1, 2+2=4, 2+3=5, 3+3=6  (sumset; 6 = 3+3 additively, not 2x3)")

    print("\nC. CASCADE — 2nd harmonic of the 3rd harmonic = 6 (multiplicative)")
    third = np.sin(2 * np.pi * 3 * t)  # 3rd harmonic of the fundamental
    cascaded = third**2  # 2nd-harmonic generation acting on the 3f tone
    mc = spectrum(cascaded)
    top = sorted(peaks(mc), key=lambda k: -mc[k])[:3]
    print(f"   strongest bins of (3f)^2: {sorted(top)}  -> lands on 6 = 2x3? {'YES' if mc[6] > 0.05 else 'NO'}")

    print("\nD. lcm vs gcd — joint waveform of modes 30 and 42")
    a, b = 30, 42
    g = np.gcd(a, b)
    joint = np.sin(2 * np.pi * a * t) + np.sin(2 * np.pi * b * t)
    # realignment period via autocorrelation: first lag (>0) where signal repeats
    ac = np.correlate(joint, joint, mode="full")[N - 1 :]
    ac /= ac[0]
    # first strong recurrence after a guard band
    guard = N // (b + 5)
    rec = guard + int(np.argmax(ac[guard:]))
    print(f"   gcd(30,42)={g}, lcm(30,42)={np.lcm(a,b)}")
    print(f"   waveform first realigns at lag {rec/N:.5f} * T0  (T0/gcd = {1/g:.5f})  match={abs(rec/N - 1/g) < 1e-3}")
    print(f"   implied joint fundamental (missing fundamental) = gcd*f0 = {g}f0  (lcm 210 is NOT here)")

    print("\nE. ALIASING = mod — strobe at 30 f0, wheel lanes fold 8 -> 4")
    fs = 30  # strobe rate (samples per window)
    ts = np.arange(fs) / fs
    lanes = [1, 7, 11, 13, 17, 19, 23, 29]
    folded = {}
    for n in lanes:
        sampled = np.sin(2 * np.pi * n * ts)
        mm = np.abs(np.fft.rfft(sampled))
        alias = int(np.argmax(mm))  # bin where energy lands after strobing
        folded.setdefault(alias, []).append(n)
    print(f"   alias bin -> source lanes: {dict(sorted(folded.items()))}")
    print(f"   distinct alias bins (real sampling) = {len(folded)}  (claim: 8 lanes fold to 4)")

    print("\nF. integer = mode number is 1D-only — drum (circular membrane) ratios")
    try:
        import mpmath as mp

        z = [float(mp.besseljzero(0, 1)), float(mp.besseljzero(1, 1)), float(mp.besseljzero(2, 1))]
        ratios = [zz / z[0] for zz in z]
        print(f"   first membrane modes (Bessel zeros): {[round(zz,3) for zz in z]}")
        print(f"   ratios to fundamental: {[round(r,3) for r in ratios]}  (claim: 1 : 1.59 : 2.14)")
    except Exception as e:  # pragma: no cover
        print(f"   (mpmath unavailable: {e})")
    print("   stiff string goes inharmonic: f_n = n*f0*sqrt(1+B n^2) -> not integer ratios")


if __name__ == "__main__":
    main()
