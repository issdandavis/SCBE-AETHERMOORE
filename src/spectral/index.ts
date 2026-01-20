/**
 * SCBE Layer 9: Spectral Coherence Module
 *
 * Implements spectral coherence metrics based on Parseval's theorem.
 * S_spec = E_low / (E_low + E_high + epsilon)
 *
 * Key Properties:
 * - Energy partition is invariant (Parseval's theorem)
 * - Phase invariant (depends only on |X[k]|^2)
 * - Bounded to [0, 1]
 */

/**
 * Complex number representation for FFT
 */
export interface Complex {
  re: number;
  im: number;
}

/**
 * Spectral analysis result
 */
export interface SpectralAnalysis {
  /** Low-frequency energy (below cutoff) */
  E_low: number;
  /** High-frequency energy (at or above cutoff) */
  E_high: number;
  /** Total energy */
  E_total: number;
  /** Spectral coherence value [0, 1] */
  S_spec: number;
  /** Power spectrum array */
  powerSpectrum: number[];
  /** Frequency bins in Hz */
  frequencies: number[];
}

/**
 * STFT frame analysis result
 */
export interface STFTFrame {
  /** Time position in seconds */
  time: number;
  /** Spectral coherence for this frame */
  S_audio: number;
  /** High-frequency ratio */
  r_HF: number;
}

/**
 * Compute the Discrete Fourier Transform of a real signal
 * Uses Cooley-Tukey FFT algorithm for efficiency
 */
export function fft(signal: number[]): Complex[] {
  const N = signal.length;

  // Pad to power of 2 if necessary
  const paddedLength = Math.pow(2, Math.ceil(Math.log2(N)));
  const padded = new Array(paddedLength).fill(0);
  for (let i = 0; i < N; i++) {
    padded[i] = signal[i];
  }

  return fftRecursive(padded.map(x => ({ re: x, im: 0 })));
}

/**
 * Recursive FFT implementation (Cooley-Tukey)
 */
function fftRecursive(x: Complex[]): Complex[] {
  const N = x.length;

  if (N <= 1) return x;

  // Split into even and odd
  const even: Complex[] = [];
  const odd: Complex[] = [];
  for (let i = 0; i < N; i++) {
    if (i % 2 === 0) even.push(x[i]);
    else odd.push(x[i]);
  }

  // Recursive FFT
  const fftEven = fftRecursive(even);
  const fftOdd = fftRecursive(odd);

  // Combine
  const result: Complex[] = new Array(N);
  for (let k = 0; k < N / 2; k++) {
    const angle = -2 * Math.PI * k / N;
    const twiddle: Complex = {
      re: Math.cos(angle),
      im: Math.sin(angle)
    };

    // Complex multiplication: twiddle * fftOdd[k]
    const t: Complex = {
      re: twiddle.re * fftOdd[k].re - twiddle.im * fftOdd[k].im,
      im: twiddle.re * fftOdd[k].im + twiddle.im * fftOdd[k].re
    };

    result[k] = {
      re: fftEven[k].re + t.re,
      im: fftEven[k].im + t.im
    };
    result[k + N / 2] = {
      re: fftEven[k].re - t.re,
      im: fftEven[k].im - t.im
    };
  }

  return result;
}

/**
 * Compute magnitude squared of complex number
 */
export function magnitudeSquared(c: Complex): number {
  return c.re * c.re + c.im * c.im;
}

/**
 * Compute frequency bins for FFT result
 */
export function fftFrequencies(N: number, sampleRate: number): number[] {
  const freqs: number[] = [];
  for (let i = 0; i < N; i++) {
    if (i < N / 2) {
      freqs.push(i * sampleRate / N);
    } else {
      freqs.push((i - N) * sampleRate / N);
    }
  }
  return freqs;
}

/**
 * Compute spectral coherence for a signal
 *
 * S_spec = E_low / (E_low + E_high + epsilon)
 *
 * @param signal - Input signal array
 * @param sampleRate - Sample rate in Hz
 * @param cutoffFreq - Cutoff frequency in Hz
 * @param epsilon - Small constant to prevent division by zero
 * @returns SpectralAnalysis result
 */
export function computeSpectralCoherence(
  signal: number[],
  sampleRate: number,
  cutoffFreq: number,
  epsilon: number = 1e-10
): SpectralAnalysis {
  const N = signal.length;
  const X = fft(signal);
  const paddedN = X.length;

  // Compute power spectrum (one-sided)
  const halfN = Math.floor(paddedN / 2);
  const powerSpectrum: number[] = [];
  const frequencies: number[] = [];

  for (let i = 0; i < halfN; i++) {
    powerSpectrum.push(magnitudeSquared(X[i]));
    frequencies.push(i * sampleRate / paddedN);
  }

  // Partition energy by frequency
  let E_low = 0;
  let E_high = 0;

  for (let i = 0; i < halfN; i++) {
    if (frequencies[i] < cutoffFreq) {
      E_low += powerSpectrum[i];
    } else {
      E_high += powerSpectrum[i];
    }
  }

  const E_total = E_low + E_high;
  const S_spec = E_low / (E_total + epsilon);

  return {
    E_low,
    E_high,
    E_total,
    S_spec,
    powerSpectrum,
    frequencies
  };
}

/**
 * Verify Parseval's theorem: time-domain energy equals frequency-domain energy
 *
 * Sum|x[n]|^2 = (1/N) Sum|X[k]|^2
 *
 * @param signal - Input signal
 * @param X - FFT of signal
 * @returns Object with energies and relative error
 */
export function verifyParseval(
  signal: number[],
  X: Complex[]
): { timeEnergy: number; freqEnergy: number; relativeError: number } {
  const N = X.length;

  // Time-domain energy
  const timeEnergy = signal.reduce((sum, x) => sum + x * x, 0);

  // Frequency-domain energy (with normalization)
  const freqEnergy = X.reduce((sum, c) => sum + magnitudeSquared(c), 0) / N;

  const relativeError = Math.abs(timeEnergy - freqEnergy) / (timeEnergy + 1e-10);

  return { timeEnergy, freqEnergy, relativeError };
}

/**
 * Generate a test signal: sum of sinusoids
 *
 * @param sampleRate - Sample rate in Hz
 * @param duration - Duration in seconds
 * @param components - Array of {freq, amplitude} for each sinusoid
 * @returns Signal array
 */
export function generateTestSignal(
  sampleRate: number,
  duration: number,
  components: Array<{ freq: number; amplitude: number; phase?: number }>
): number[] {
  const N = Math.floor(sampleRate * duration);
  const signal: number[] = new Array(N);

  for (let i = 0; i < N; i++) {
    const t = i / sampleRate;
    signal[i] = 0;
    for (const comp of components) {
      const phase = comp.phase ?? 0;
      signal[i] += comp.amplitude * Math.sin(2 * Math.PI * comp.freq * t + phase);
    }
  }

  return signal;
}

/**
 * Simple Short-Time Fourier Transform
 *
 * @param signal - Input signal
 * @param sampleRate - Sample rate in Hz
 * @param windowSize - Window size in samples
 * @param hopSize - Hop size in samples
 * @param cutoffFreq - Cutoff frequency for S_audio calculation
 * @returns Array of STFT frame results
 */
export function stft(
  signal: number[],
  sampleRate: number,
  windowSize: number,
  hopSize: number,
  cutoffFreq: number
): STFTFrame[] {
  const frames: STFTFrame[] = [];
  const epsilon = 1e-10;

  for (let start = 0; start + windowSize <= signal.length; start += hopSize) {
    // Extract window
    const window = signal.slice(start, start + windowSize);

    // Apply Hann window
    const windowed = window.map((x, i) =>
      x * 0.5 * (1 - Math.cos(2 * Math.PI * i / (windowSize - 1)))
    );

    // FFT
    const X = fft(windowed);
    const halfN = Math.floor(X.length / 2);

    // Power spectrum
    let E_low = 0;
    let E_high = 0;

    for (let i = 0; i < halfN; i++) {
      const freq = i * sampleRate / X.length;
      const power = magnitudeSquared(X[i]);

      if (freq < cutoffFreq) {
        E_low += power;
      } else {
        E_high += power;
      }
    }

    const E_total = E_low + E_high;
    const r_HF = E_high / (E_total + epsilon);
    const S_audio = 1 - r_HF;

    frames.push({
      time: (start + windowSize / 2) / sampleRate,
      S_audio,
      r_HF
    });
  }

  return frames;
}

/**
 * Generate a linear chirp signal (frequency increases linearly over time)
 *
 * @param sampleRate - Sample rate in Hz
 * @param duration - Duration in seconds
 * @param startFreq - Starting frequency in Hz
 * @param endFreq - Ending frequency in Hz
 * @returns Chirp signal array
 */
export function generateChirp(
  sampleRate: number,
  duration: number,
  startFreq: number,
  endFreq: number
): number[] {
  const N = Math.floor(sampleRate * duration);
  const signal: number[] = new Array(N);
  const k = (endFreq - startFreq) / duration;

  for (let i = 0; i < N; i++) {
    const t = i / sampleRate;
    // Instantaneous frequency: f(t) = startFreq + k*t
    // Phase: integral of 2*pi*f(t) = 2*pi*(startFreq*t + k*t^2/2)
    const phase = 2 * Math.PI * (startFreq * t + k * t * t / 2);
    signal[i] = Math.sin(phase);
  }

  return signal;
}

/**
 * Layer 9 Spectral Coherence bounds check
 *
 * Verifies that S_spec is always in [0, 1]
 */
export function verifySpectralCoherenceBounds(S_spec: number): boolean {
  return S_spec >= 0 && S_spec <= 1;
}

/**
 * Check phase invariance: S_spec should not depend on signal phase
 *
 * @param sampleRate - Sample rate
 * @param duration - Duration
 * @param components - Signal components
 * @param cutoffFreq - Cutoff frequency
 * @param tolerance - Maximum allowed difference
 * @returns Whether phase invariance holds
 */
export function checkPhaseInvariance(
  sampleRate: number,
  duration: number,
  components: Array<{ freq: number; amplitude: number }>,
  cutoffFreq: number,
  tolerance: number = 1e-6
): { invariant: boolean; maxDifference: number } {
  // Original signal
  const signal1 = generateTestSignal(sampleRate, duration, components);
  const result1 = computeSpectralCoherence(signal1, sampleRate, cutoffFreq);

  // Phase-shifted signal
  const shiftedComponents = components.map(c => ({
    ...c,
    phase: Math.PI / 3 // Arbitrary phase shift
  }));
  const signal2 = generateTestSignal(sampleRate, duration, shiftedComponents);
  const result2 = computeSpectralCoherence(signal2, sampleRate, cutoffFreq);

  const difference = Math.abs(result1.S_spec - result2.S_spec);

  return {
    invariant: difference < tolerance,
    maxDifference: difference
  };
}
