"use strict";
/**
 * SCBE Symphonic Cipher - Symphonic Agent
 *
 * The Symphonic Agent handles "Audio Synthesis Simulation" - the transformation
 * of transaction intents into spectral fingerprints through signal processing.
 *
 * Pipeline:
 * 1. Intent Modulation (Feistel permutation) - scrambles input into pseudo-random signal
 * 2. Signal Generation - converts bytes to normalized floating-point samples
 * 3. Spectral Analysis (FFT) - transforms to frequency domain
 * 4. Fingerprint Extraction - samples magnitude spectrum
 *
 * @module symphonic/SymphonicAgent
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.createSymphonicAgent = exports.SymphonicAgent = void 0;
const FFT_js_1 = require("./FFT.js");
const Feistel_js_1 = require("./Feistel.js");
const DEFAULT_CONFIG = {
    feistel: { rounds: 6 },
    fingerprintSize: 32,
    highFreqThreshold: 0.5,
};
/**
 * Symphonic Agent - orchestrates intent-to-spectrum transformation
 */
class SymphonicAgent {
    feistel;
    config;
    /**
     * Creates a new Symphonic Agent.
     *
     * @param config Agent configuration
     */
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.feistel = new Feistel_js_1.Feistel(this.config.feistel);
    }
    /**
     * Synthesizes harmonics from an intent.
     *
     * 1. Modulates (Scrambles) the Intent using Feistel Cipher
     * 2. Converts the byte stream to normalized floating point signal
     * 3. Performs FFT to get the Harmonic Spectrum
     * 4. Extracts fingerprint and computes metrics
     *
     * @param intent The user's intent (e.g., "TRANSFER_500_AETHER")
     * @param secretKey The user's private key for modulation
     * @returns Complete synthesis result
     */
    synthesizeHarmonics(intent, secretKey) {
        // Step 1: Intent Modulation (Feistel Permutation)
        const rawData = new TextEncoder().encode(intent);
        const modulatedData = this.feistel.encrypt(rawData, secretKey);
        // Step 2: Signal Generation (Byte to Float -1.0 to 1.0)
        const signal = FFT_js_1.FFT.bufferToSignal(modulatedData);
        // Step 3: Spectral Analysis (FFT)
        const complexSignal = FFT_js_1.FFT.prepareSignal(signal);
        const spectrum = FFT_js_1.FFT.transform(complexSignal);
        // Step 4: Fingerprint Extraction
        const fingerprint = FFT_js_1.FFT.extractFingerprint(spectrum, this.config.fingerprintSize);
        // Step 5: Compute metrics
        const coherence = this.computeCoherence(spectrum);
        const dominantFrequency = this.findDominantFrequency(spectrum);
        return {
            modulatedData,
            signal,
            spectrum,
            fingerprint,
            coherence,
            dominantFrequency,
        };
    }
    /**
     * Extracts a compact fingerprint from spectrum magnitudes.
     *
     * @param spectrum Complex frequency spectrum
     * @returns Magnitude fingerprint array
     */
    extractFingerprint(spectrum) {
        return FFT_js_1.FFT.extractFingerprint(spectrum, this.config.fingerprintSize);
    }
    /**
     * Quantizes a fingerprint to bytes for encoding.
     *
     * @param fingerprint Floating-point fingerprint
     * @returns Quantized byte array
     */
    quantizeFingerprint(fingerprint) {
        const result = new Uint8Array(fingerprint.length);
        // Find max magnitude for normalization
        let maxMag = 0;
        for (const m of fingerprint) {
            if (m > maxMag)
                maxMag = m;
        }
        // Quantize to 0-255
        for (let i = 0; i < fingerprint.length; i++) {
            const normalized = maxMag > 0 ? fingerprint[i] / maxMag : 0;
            result[i] = Math.min(255, Math.max(0, Math.floor(normalized * 255)));
        }
        return result;
    }
    /**
     * Computes spectral coherence (low HF = high coherence).
     *
     * @param spectrum Complex frequency spectrum
     * @returns Coherence score in [0, 1]
     */
    computeCoherence(spectrum) {
        const n = spectrum.length;
        const halfN = Math.floor(n / 2);
        const cutoff = Math.floor(halfN * this.config.highFreqThreshold);
        let totalPower = 0;
        let highFreqPower = 0;
        for (let k = 0; k < halfN; k++) {
            const power = spectrum[k].magnitudeSquared;
            totalPower += power;
            if (k >= cutoff) {
                highFreqPower += power;
            }
        }
        if (totalPower === 0)
            return 1;
        return 1 - highFreqPower / totalPower;
    }
    /**
     * Finds the dominant frequency bin.
     *
     * @param spectrum Complex frequency spectrum
     * @returns Index of dominant frequency
     */
    findDominantFrequency(spectrum) {
        const halfN = Math.floor(spectrum.length / 2);
        let maxPower = 0;
        let maxIndex = 0;
        // Skip DC (k=0), search positive frequencies
        for (let k = 1; k < halfN; k++) {
            const power = spectrum[k].magnitudeSquared;
            if (power > maxPower) {
                maxPower = power;
                maxIndex = k;
            }
        }
        return maxIndex;
    }
    /**
     * Verifies that an intent produces the expected fingerprint.
     *
     * @param intent Original intent
     * @param secretKey Secret key
     * @param expectedFingerprint Expected fingerprint bytes
     * @param tolerance Comparison tolerance (default 5)
     * @returns True if fingerprints match within tolerance
     */
    verifyFingerprint(intent, secretKey, expectedFingerprint, tolerance = 5) {
        const result = this.synthesizeHarmonics(intent, secretKey);
        const actualFingerprint = this.quantizeFingerprint(result.fingerprint);
        if (actualFingerprint.length !== expectedFingerprint.length) {
            return false;
        }
        // Check each byte within tolerance
        for (let i = 0; i < actualFingerprint.length; i++) {
            if (Math.abs(actualFingerprint[i] - expectedFingerprint[i]) > tolerance) {
                return false;
            }
        }
        return true;
    }
    /**
     * Computes similarity between two fingerprints.
     *
     * @param fp1 First fingerprint
     * @param fp2 Second fingerprint
     * @returns Similarity score in [0, 1]
     */
    static fingerprintSimilarity(fp1, fp2) {
        if (fp1.length !== fp2.length) {
            throw new Error('Fingerprints must have same length');
        }
        // Cosine similarity
        let dotProduct = 0;
        let norm1 = 0;
        let norm2 = 0;
        for (let i = 0; i < fp1.length; i++) {
            dotProduct += fp1[i] * fp2[i];
            norm1 += fp1[i] * fp1[i];
            norm2 += fp2[i] * fp2[i];
        }
        const denom = Math.sqrt(norm1) * Math.sqrt(norm2);
        if (denom === 0)
            return 0;
        return dotProduct / denom;
    }
    /**
     * Analyzes spectral properties for debugging/visualization.
     *
     * @param spectrum Complex spectrum
     * @returns Analysis object with various metrics
     */
    static analyzeSpectrum(spectrum) {
        const n = spectrum.length;
        const halfN = Math.floor(n / 2);
        let totalEnergy = 0;
        let weightedSum = 0;
        let peakMag = 0;
        let peakFreq = 0;
        for (let k = 0; k < halfN; k++) {
            const mag = spectrum[k].magnitude;
            totalEnergy += mag * mag;
            weightedSum += k * mag;
            if (mag > peakMag) {
                peakMag = mag;
                peakFreq = k;
            }
        }
        const totalMag = Math.sqrt(totalEnergy);
        const meanMag = totalMag / halfN;
        const centroid = totalMag > 0 ? weightedSum / totalMag : 0;
        // Compute spectral spread
        let spreadSum = 0;
        for (let k = 0; k < halfN; k++) {
            const diff = k - centroid;
            spreadSum += diff * diff * spectrum[k].magnitude;
        }
        const spread = totalMag > 0 ? Math.sqrt(spreadSum / totalMag) : 0;
        return {
            totalEnergy,
            meanMagnitude: meanMag,
            peakMagnitude: peakMag,
            peakFrequency: peakFreq,
            spectralCentroid: centroid,
            spectralSpread: spread,
        };
    }
}
exports.SymphonicAgent = SymphonicAgent;
/**
 * Creates a Symphonic Agent with default settings.
 */
function createSymphonicAgent(config) {
    return new SymphonicAgent(config);
}
exports.createSymphonicAgent = createSymphonicAgent;
//# sourceMappingURL=SymphonicAgent.js.map