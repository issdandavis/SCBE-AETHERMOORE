"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.checkPhaseInvariance = exports.verifySpectralCoherenceBounds = exports.generateChirp = exports.stft = exports.generateTestSignal = exports.verifyParseval = exports.computeSpectralCoherence = exports.fftFrequencies = exports.magnitudeSquared = exports.fft = void 0;
/**
 * Compute the Discrete Fourier Transform of a real signal
 * Uses Cooley-Tukey FFT algorithm for efficiency
 */
function fft(signal) {
    const N = signal.length;
    // Pad to power of 2 if necessary
    const paddedLength = Math.pow(2, Math.ceil(Math.log2(N)));
    const padded = new Array(paddedLength).fill(0);
    for (let i = 0; i < N; i++) {
        padded[i] = signal[i];
    }
    return fftRecursive(padded.map((x) => ({ re: x, im: 0 })));
}
exports.fft = fft;
/**
 * Recursive FFT implementation (Cooley-Tukey)
 */
function fftRecursive(x) {
    const N = x.length;
    if (N <= 1)
        return x;
    // Split into even and odd
    const even = [];
    const odd = [];
    for (let i = 0; i < N; i++) {
        if (i % 2 === 0)
            even.push(x[i]);
        else
            odd.push(x[i]);
    }
    // Recursive FFT
    const fftEven = fftRecursive(even);
    const fftOdd = fftRecursive(odd);
    // Combine
    const result = new Array(N);
    for (let k = 0; k < N / 2; k++) {
        const angle = (-2 * Math.PI * k) / N;
        const twiddle = {
            re: Math.cos(angle),
            im: Math.sin(angle),
        };
        // Complex multiplication: twiddle * fftOdd[k]
        const t = {
            re: twiddle.re * fftOdd[k].re - twiddle.im * fftOdd[k].im,
            im: twiddle.re * fftOdd[k].im + twiddle.im * fftOdd[k].re,
        };
        result[k] = {
            re: fftEven[k].re + t.re,
            im: fftEven[k].im + t.im,
        };
        result[k + N / 2] = {
            re: fftEven[k].re - t.re,
            im: fftEven[k].im - t.im,
        };
    }
    return result;
}
/**
 * Compute magnitude squared of complex number
 */
function magnitudeSquared(c) {
    return c.re * c.re + c.im * c.im;
}
exports.magnitudeSquared = magnitudeSquared;
/**
 * Compute frequency bins for FFT result
 */
function fftFrequencies(N, sampleRate) {
    const freqs = [];
    for (let i = 0; i < N; i++) {
        if (i < N / 2) {
            freqs.push((i * sampleRate) / N);
        }
        else {
            freqs.push(((i - N) * sampleRate) / N);
        }
    }
    return freqs;
}
exports.fftFrequencies = fftFrequencies;
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
function computeSpectralCoherence(signal, sampleRate, cutoffFreq, epsilon = 1e-10) {
    const N = signal.length;
    const X = fft(signal);
    const paddedN = X.length;
    // Compute power spectrum (one-sided)
    const halfN = Math.floor(paddedN / 2);
    const powerSpectrum = [];
    const frequencies = [];
    for (let i = 0; i < halfN; i++) {
        powerSpectrum.push(magnitudeSquared(X[i]));
        frequencies.push((i * sampleRate) / paddedN);
    }
    // Partition energy by frequency
    let E_low = 0;
    let E_high = 0;
    for (let i = 0; i < halfN; i++) {
        if (frequencies[i] < cutoffFreq) {
            E_low += powerSpectrum[i];
        }
        else {
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
        frequencies,
    };
}
exports.computeSpectralCoherence = computeSpectralCoherence;
/**
 * Verify Parseval's theorem: time-domain energy equals frequency-domain energy
 *
 * Sum|x[n]|^2 = (1/N) Sum|X[k]|^2
 *
 * @param signal - Input signal
 * @param X - FFT of signal
 * @returns Object with energies and relative error
 */
function verifyParseval(signal, X) {
    const N = X.length;
    // Time-domain energy
    const timeEnergy = signal.reduce((sum, x) => sum + x * x, 0);
    // Frequency-domain energy (with normalization)
    const freqEnergy = X.reduce((sum, c) => sum + magnitudeSquared(c), 0) / N;
    const relativeError = Math.abs(timeEnergy - freqEnergy) / (timeEnergy + 1e-10);
    return { timeEnergy, freqEnergy, relativeError };
}
exports.verifyParseval = verifyParseval;
/**
 * Generate a test signal: sum of sinusoids
 *
 * @param sampleRate - Sample rate in Hz
 * @param duration - Duration in seconds
 * @param components - Array of {freq, amplitude} for each sinusoid
 * @returns Signal array
 */
function generateTestSignal(sampleRate, duration, components) {
    const N = Math.floor(sampleRate * duration);
    const signal = new Array(N);
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
exports.generateTestSignal = generateTestSignal;
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
function stft(signal, sampleRate, windowSize, hopSize, cutoffFreq) {
    const frames = [];
    const epsilon = 1e-10;
    for (let start = 0; start + windowSize <= signal.length; start += hopSize) {
        // Extract window
        const window = signal.slice(start, start + windowSize);
        // Apply Hann window
        const windowed = window.map((x, i) => x * 0.5 * (1 - Math.cos((2 * Math.PI * i) / (windowSize - 1))));
        // FFT
        const X = fft(windowed);
        const halfN = Math.floor(X.length / 2);
        // Power spectrum
        let E_low = 0;
        let E_high = 0;
        for (let i = 0; i < halfN; i++) {
            const freq = (i * sampleRate) / X.length;
            const power = magnitudeSquared(X[i]);
            if (freq < cutoffFreq) {
                E_low += power;
            }
            else {
                E_high += power;
            }
        }
        const E_total = E_low + E_high;
        const r_HF = E_high / (E_total + epsilon);
        const S_audio = 1 - r_HF;
        frames.push({
            time: (start + windowSize / 2) / sampleRate,
            S_audio,
            r_HF,
        });
    }
    return frames;
}
exports.stft = stft;
/**
 * Generate a linear chirp signal (frequency increases linearly over time)
 *
 * @param sampleRate - Sample rate in Hz
 * @param duration - Duration in seconds
 * @param startFreq - Starting frequency in Hz
 * @param endFreq - Ending frequency in Hz
 * @returns Chirp signal array
 */
function generateChirp(sampleRate, duration, startFreq, endFreq) {
    const N = Math.floor(sampleRate * duration);
    const signal = new Array(N);
    const k = (endFreq - startFreq) / duration;
    for (let i = 0; i < N; i++) {
        const t = i / sampleRate;
        // Instantaneous frequency: f(t) = startFreq + k*t
        // Phase: integral of 2*pi*f(t) = 2*pi*(startFreq*t + k*t^2/2)
        const phase = 2 * Math.PI * (startFreq * t + (k * t * t) / 2);
        signal[i] = Math.sin(phase);
    }
    return signal;
}
exports.generateChirp = generateChirp;
/**
 * Layer 9 Spectral Coherence bounds check
 *
 * Verifies that S_spec is always in [0, 1]
 */
function verifySpectralCoherenceBounds(S_spec) {
    return S_spec >= 0 && S_spec <= 1;
}
exports.verifySpectralCoherenceBounds = verifySpectralCoherenceBounds;
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
function checkPhaseInvariance(sampleRate, duration, components, cutoffFreq, tolerance = 1e-6) {
    // Original signal
    const signal1 = generateTestSignal(sampleRate, duration, components);
    const result1 = computeSpectralCoherence(signal1, sampleRate, cutoffFreq);
    // Phase-shifted signal
    const shiftedComponents = components.map((c) => ({
        ...c,
        phase: Math.PI / 3, // Arbitrary phase shift
    }));
    const signal2 = generateTestSignal(sampleRate, duration, shiftedComponents);
    const result2 = computeSpectralCoherence(signal2, sampleRate, cutoffFreq);
    const difference = Math.abs(result1.S_spec - result2.S_spec);
    return {
        invariant: difference < tolerance,
        maxDifference: difference,
    };
}
exports.checkPhaseInvariance = checkPhaseInvariance;
//# sourceMappingURL=index.js.map