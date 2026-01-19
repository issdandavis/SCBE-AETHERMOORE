/**
 * SCBE Symphonic Cipher - Fast Fourier Transform
 *
 * Iterative implementation of the Cooley-Tukey Radix-2 FFT algorithm.
 * Transforms time-domain signals to frequency-domain spectra in O(N log N).
 *
 * This implementation is optimized for V8 (Node.js) by avoiding deep recursion
 * and using iterative loops with bit-reversal permutation.
 *
 * @module symphonic/FFT
 */

import { Complex } from './Complex.js';

/**
 * FFT result containing both frequency spectrum and metadata
 */
export interface FFTResult {
  /** Complex frequency spectrum */
  spectrum: Complex[];
  /** Magnitude spectrum (|X[k]|) */
  magnitudes: number[];
  /** Power spectrum (|X[k]|²) */
  power: number[];
  /** Phase spectrum (arg(X[k])) */
  phases: number[];
  /** Number of samples */
  n: number;
  /** Frequency resolution (if sample rate provided) */
  frequencyResolution?: number;
}

/**
 * Fast Fourier Transform implementation
 */
export class FFT {
  /**
   * Performs the Forward FFT on a signal.
   *
   * @param input Array of Complex numbers representing the time-domain signal.
   * @returns Array of Complex numbers representing the frequency-domain spectrum.
   * @throws Error if input length is not a power of 2
   */
  static transform(input: Complex[]): Complex[] {
    const n = input.length;

    // Validation: N must be power of 2
    if ((n & (n - 1)) !== 0 || n === 0) {
      throw new Error(
        `FFT input length must be a non-zero power of 2, got ${n}`
      );
    }

    // 1. Bit-Reversal Permutation
    const result = FFT.bitReversalPermutation(input);

    // 2. Iterative Butterfly Operations
    const bits = Math.log2(n);

    for (let stage = 1; stage <= bits; stage++) {
      const size = 1 << stage; // 2^stage
      const halfSize = size >>> 1; // size / 2

      // Calculate the fundamental twiddle factor for this stage
      // W_size = e^(-2*pi*i / size)
      const theta = (-2 * Math.PI) / size;
      const wStep = Complex.fromEuler(theta);

      // Iterate through each block of the current size
      for (let blockStart = 0; blockStart < n; blockStart += size) {
        let w = Complex.one(); // Initial twiddle factor W^0 = 1

        // Perform butterflies for this block
        for (let j = 0; j < halfSize; j++) {
          const evenIndex = blockStart + j;
          const oddIndex = blockStart + j + halfSize;

          const even = result[evenIndex];
          const odd = result[oddIndex];

          // Butterfly operation:
          // t = w * odd
          // result[even] = even + t
          // result[odd] = even - t
          const t = w.mul(odd);

          result[evenIndex] = even.add(t);
          result[oddIndex] = even.sub(t);

          // Update twiddle factor: w = w * wStep
          w = w.mul(wStep);
        }
      }
    }

    return result;
  }

  /**
   * Performs the Inverse FFT to recover time-domain signal.
   *
   * @param spectrum Complex frequency spectrum
   * @returns Time-domain signal
   */
  static inverse(spectrum: Complex[]): Complex[] {
    const n = spectrum.length;

    // IFFT is FFT of conjugated input, then conjugate and scale
    const conjugated = spectrum.map((c) => c.conjugate());
    const transformed = FFT.transform(conjugated);

    // Conjugate and scale by 1/N
    return transformed.map((c) => c.conjugate().scale(1 / n));
  }

  /**
   * Performs FFT and returns detailed analysis results.
   *
   * @param signal Real-valued time-domain signal
   * @param sampleRate Optional sample rate for frequency resolution
   * @returns FFTResult with spectrum, magnitudes, power, and phases
   */
  static analyze(signal: number[], sampleRate?: number): FFTResult {
    const complexSignal = FFT.prepareSignal(signal);
    const spectrum = FFT.transform(complexSignal);
    const n = spectrum.length;

    const magnitudes = spectrum.map((c) => c.magnitude);
    const power = spectrum.map((c) => c.magnitudeSquared);
    const phases = spectrum.map((c) => c.phase);

    const result: FFTResult = {
      spectrum,
      magnitudes,
      power,
      phases,
      n,
    };

    if (sampleRate !== undefined) {
      result.frequencyResolution = sampleRate / n;
    }

    return result;
  }

  /**
   * Computes the power spectral density.
   *
   * @param signal Real-valued signal
   * @returns Normalized power spectrum
   */
  static powerSpectralDensity(signal: number[]): number[] {
    const result = FFT.analyze(signal);
    const n = result.n;

    // Normalize by N² for proper PSD scaling
    return result.power.map((p) => p / (n * n));
  }

  /**
   * Computes spectral coherence score (low HF ratio = high coherence).
   *
   * @param signal Time-domain signal
   * @param highFreqThreshold Fraction of spectrum considered "high frequency" (default 0.5)
   * @returns Coherence score in [0, 1]
   */
  static spectralCoherence(
    signal: number[],
    highFreqThreshold: number = 0.5
  ): number {
    const result = FFT.analyze(signal);
    const n = result.n;
    const halfN = Math.floor(n / 2);

    // Only use first half (positive frequencies, up to Nyquist)
    const cutoff = Math.floor(halfN * highFreqThreshold);

    let totalPower = 0;
    let highFreqPower = 0;

    for (let k = 0; k < halfN; k++) {
      const p = result.power[k];
      totalPower += p;
      if (k >= cutoff) {
        highFreqPower += p;
      }
    }

    if (totalPower === 0) return 1; // No signal = perfect coherence

    const hfRatio = highFreqPower / totalPower;
    return 1 - hfRatio; // High coherence = low HF ratio
  }

  /**
   * Utility to pad a number array to the next power of 2 and convert to Complex.
   * Zero-padding interpolates the spectrum but does not add new information.
   *
   * @param data Real-valued input signal
   * @returns Complex signal padded to power of 2
   */
  static prepareSignal(data: number[]): Complex[] {
    if (data.length === 0) return [Complex.zero()];

    let size = 1;
    while (size < data.length) size *= 2;

    const signal = new Array<Complex>(size);
    for (let i = 0; i < size; i++) {
      const val = i < data.length ? data[i] : 0;
      signal[i] = new Complex(val, 0); // Real signal, 0 imaginary
    }
    return signal;
  }

  /**
   * Converts byte buffer to normalized signal [-1, 1].
   * Treats bytes as unsigned PCM samples.
   *
   * @param buffer Input byte buffer
   * @returns Normalized signal array
   */
  static bufferToSignal(buffer: Uint8Array): number[] {
    const signal = new Array<number>(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
      // Normalize 0..255 to -1.0..1.0
      signal[i] = buffer[i] / 128.0 - 1.0;
    }
    return signal;
  }

  /**
   * Extracts harmonic fingerprint from spectrum.
   * Samples magnitude spectrum at regular intervals.
   *
   * @param spectrum Complex frequency spectrum
   * @param fingerprintSize Number of samples to extract (default 32)
   * @returns Fingerprint as magnitude samples
   */
  static extractFingerprint(
    spectrum: Complex[],
    fingerprintSize: number = 32
  ): number[] {
    const magnitudes = spectrum.map((c) => c.magnitude);
    const step = Math.max(1, Math.floor(magnitudes.length / fingerprintSize));

    const fingerprint = new Array<number>(fingerprintSize);
    for (let i = 0; i < fingerprintSize; i++) {
      const idx = (i * step) % magnitudes.length;
      fingerprint[i] = magnitudes[idx];
    }
    return fingerprint;
  }

  /**
   * Performs bit-reversal permutation for iterative FFT.
   * Reorders input so butterflies can be computed in-place.
   *
   * @param input Original array
   * @returns Bit-reversed copy
   */
  private static bitReversalPermutation(input: Complex[]): Complex[] {
    const n = input.length;
    const bits = Math.log2(n);
    const result = new Array<Complex>(n);

    for (let i = 0; i < n; i++) {
      let reversed = 0;
      let x = i;
      for (let j = 0; j < bits; j++) {
        reversed = (reversed << 1) | (x & 1);
        x >>>= 1;
      }
      result[reversed] = input[i].clone();
    }

    return result;
  }

  /**
   * Checks if a number is a power of 2.
   */
  static isPowerOf2(n: number): boolean {
    return n > 0 && (n & (n - 1)) === 0;
  }

  /**
   * Returns the next power of 2 >= n.
   */
  static nextPowerOf2(n: number): number {
    if (n <= 1) return 1;
    let power = 1;
    while (power < n) power *= 2;
    return power;
  }
}
