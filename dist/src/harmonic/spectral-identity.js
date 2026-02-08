"use strict";
/**
 * Spectral Identity System - Rainbow Chromatic Fingerprinting
 *
 * Maps multi-dimensional trust/context vectors to unique color signatures.
 * Like light through a prism - each entity gets a unique spectral fingerprint
 * that humans can visually verify.
 *
 * Color Mapping to SCBE Layers:
 * - Red (620-750nm)    → Layer 1-2: Context/Metric (danger/identity)
 * - Orange (590-620nm) → Layer 3-4: Breath/Phase (temporal)
 * - Yellow (570-590nm) → Layer 5-6: Potential/Spectral (energy)
 * - Green (495-570nm)  → Layer 7-8: Spin/Triadic (verification)
 * - Blue (450-495nm)   → Layer 9-10: Harmonic/Decision (trust)
 * - Indigo (420-450nm) → Layer 11-12: Audio/Quantum (deep security)
 * - Violet (380-420nm) → Layer 13-14: Anti-Fragile/CFI (integrity)
 *
 * Sacred Tongue Color Associations:
 * - Koraelin (KO)     → Deep Red (#8B0000)
 * - Avali (AV)        → Amber (#FFBF00)
 * - Runethic (RU)     → Emerald (#50C878)
 * - Cassisivadan (CA) → Sapphire (#0F52BA)
 * - Umbroth (UM)      → Amethyst (#9966CC)
 * - Draumric (DR)     → Obsidian (#3D3D3D)
 *
 * @module harmonic/spectral-identity
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.spectralGenerator = exports.SpectralIdentityGenerator = exports.TONGUE_COLORS = exports.SPECTRAL_BANDS = void 0;
/**
 * The 7 spectral bands (ROYGBIV)
 */
exports.SPECTRAL_BANDS = [
    {
        name: 'Red',
        wavelengthMin: 620,
        wavelengthMax: 750,
        hueMin: 0,
        hueMax: 15,
        layers: [1, 2],
        sacredTongue: 'KO',
    },
    {
        name: 'Orange',
        wavelengthMin: 590,
        wavelengthMax: 620,
        hueMin: 15,
        hueMax: 45,
        layers: [3, 4],
        sacredTongue: 'AV',
    },
    {
        name: 'Yellow',
        wavelengthMin: 570,
        wavelengthMax: 590,
        hueMin: 45,
        hueMax: 65,
        layers: [5, 6],
        sacredTongue: 'RU',
    },
    {
        name: 'Green',
        wavelengthMin: 495,
        wavelengthMax: 570,
        hueMin: 65,
        hueMax: 165,
        layers: [7, 8],
        sacredTongue: 'CA',
    },
    {
        name: 'Blue',
        wavelengthMin: 450,
        wavelengthMax: 495,
        hueMin: 165,
        hueMax: 250,
        layers: [9, 10],
        sacredTongue: 'UM',
    },
    {
        name: 'Indigo',
        wavelengthMin: 420,
        wavelengthMax: 450,
        hueMin: 250,
        hueMax: 275,
        layers: [11, 12],
        sacredTongue: 'DR',
    },
    {
        name: 'Violet',
        wavelengthMin: 380,
        wavelengthMax: 420,
        hueMin: 275,
        hueMax: 300,
        layers: [13, 14],
    },
];
/**
 * Sacred Tongue base colors
 */
exports.TONGUE_COLORS = {
    KO: { r: 139, g: 0, b: 0 }, // Deep Red
    AV: { r: 255, g: 191, b: 0 }, // Amber
    RU: { r: 80, g: 200, b: 120 }, // Emerald
    CA: { r: 15, g: 82, b: 186 }, // Sapphire
    UM: { r: 153, g: 102, b: 204 }, // Amethyst
    DR: { r: 61, g: 61, b: 61 }, // Obsidian
};
/**
 * Spectral Identity Generator
 *
 * Creates unique chromatic fingerprints from multi-dimensional vectors.
 */
class SpectralIdentityGenerator {
    goldenRatio = 1.618033988749895;
    /**
     * Generate spectral identity from a 6D trust vector
     *
     * @param entityId - Unique entity identifier
     * @param trustVector - 6D trust vector (one per Sacred Tongue)
     * @param layerScores - Optional 14-layer scores
     * @returns Complete spectral identity
     */
    generateIdentity(entityId, trustVector, layerScores) {
        if (trustVector.length !== 6) {
            throw new Error('Trust vector must have 6 dimensions (one per Sacred Tongue)');
        }
        // Normalize trust vector to [0, 1]
        const normalized = trustVector.map((v) => Math.max(0, Math.min(1, v)));
        // Generate 7-band spectrum from trust vector + layer scores
        const spectrum = this.generateSpectrum(normalized, layerScores);
        // Generate tongue-specific colors
        const tongueSignature = this.generateTongueSignature(normalized);
        // Compute primary and secondary colors
        const { primary, secondary } = this.computeDominantColors(spectrum);
        // Generate combined color
        const combined = this.blendColors(tongueSignature, normalized);
        // Generate spectral hash
        const spectralHash = this.generateSpectralHash(entityId, normalized, spectrum);
        // Determine confidence based on vector variance
        const confidence = this.computeConfidence(normalized);
        return {
            entityId,
            primaryColor: primary,
            secondaryColor: secondary,
            spectrum,
            tongueSignature,
            hexCode: this.rgbToHex(combined),
            colorName: this.generateColorName(combined, spectrum),
            spectralHash,
            confidence,
            timestamp: Date.now(),
        };
    }
    /**
     * Generate 7-band spectrum from trust vector
     */
    generateSpectrum(trustVector, layerScores) {
        const spectrum = [];
        for (let band = 0; band < 7; band++) {
            let intensity = 0;
            // Map trust vector dimensions to bands
            if (band < 6) {
                // First 6 bands map to Sacred Tongues
                intensity = trustVector[band];
            }
            else {
                // 7th band (Violet) is average of all
                intensity = trustVector.reduce((a, b) => a + b, 0) / 6;
            }
            // Modulate with layer scores if available
            if (layerScores && layerScores.length >= 14) {
                const bandLayers = exports.SPECTRAL_BANDS[band].layers;
                const layerAvg = bandLayers.reduce((sum, l) => sum + (layerScores[l - 1] || 0), 0) / bandLayers.length;
                intensity = (intensity + layerAvg) / 2;
            }
            // Apply golden ratio modulation for uniqueness
            intensity = intensity * (1 + 0.1 * Math.sin(band * this.goldenRatio * Math.PI));
            spectrum.push(Math.max(0, Math.min(1, intensity)));
        }
        return spectrum;
    }
    /**
     * Generate Sacred Tongue color signature
     */
    generateTongueSignature(trustVector) {
        const tongues = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
        return tongues.map((tongue, i) => {
            const base = exports.TONGUE_COLORS[tongue];
            const intensity = trustVector[i];
            // Modulate base color by trust intensity
            return {
                r: Math.round(base.r * (0.3 + 0.7 * intensity)),
                g: Math.round(base.g * (0.3 + 0.7 * intensity)),
                b: Math.round(base.b * (0.3 + 0.7 * intensity)),
            };
        });
    }
    /**
     * Compute dominant colors from spectrum
     */
    computeDominantColors(spectrum) {
        // Find top 2 bands
        const indexed = spectrum.map((v, i) => ({ value: v, index: i }));
        indexed.sort((a, b) => b.value - a.value);
        const primaryBand = exports.SPECTRAL_BANDS[indexed[0].index];
        const secondaryBand = exports.SPECTRAL_BANDS[indexed[1].index];
        return {
            primary: this.bandToRGB(primaryBand, indexed[0].value),
            secondary: this.bandToRGB(secondaryBand, indexed[1].value),
        };
    }
    /**
     * Convert spectral band to RGB
     */
    bandToRGB(band, intensity) {
        const hue = (band.hueMin + band.hueMax) / 2;
        const saturation = 70 + 30 * intensity;
        const lightness = 30 + 40 * intensity;
        return this.hslToRgb({ h: hue, s: saturation, l: lightness });
    }
    /**
     * Blend tongue colors weighted by trust vector
     */
    blendColors(tongueSignature, weights) {
        let r = 0, g = 0, b = 0;
        let totalWeight = 0;
        for (let i = 0; i < 6; i++) {
            const weight = weights[i] + 0.1; // Minimum weight to include all tongues
            r += tongueSignature[i].r * weight;
            g += tongueSignature[i].g * weight;
            b += tongueSignature[i].b * weight;
            totalWeight += weight;
        }
        return {
            r: Math.round(r / totalWeight),
            g: Math.round(g / totalWeight),
            b: Math.round(b / totalWeight),
        };
    }
    /**
     * Generate unique spectral hash
     */
    generateSpectralHash(entityId, trustVector, spectrum) {
        // Create deterministic hash from all inputs
        const data = [
            entityId,
            ...trustVector.map((v) => v.toFixed(6)),
            ...spectrum.map((v) => v.toFixed(6)),
        ].join(':');
        // Simple hash function (in production, use crypto)
        let hash = 0;
        for (let i = 0; i < data.length; i++) {
            const char = data.charCodeAt(i);
            hash = (hash << 5) - hash + char;
            hash = hash & hash;
        }
        // Convert to hex and pad
        const hexHash = Math.abs(hash).toString(16).padStart(8, '0');
        // Format as spectral code: SP-XXXX-XXXX
        return `SP-${hexHash.slice(0, 4).toUpperCase()}-${hexHash.slice(4, 8).toUpperCase()}`;
    }
    /**
     * Compute confidence based on vector variance
     */
    computeConfidence(trustVector) {
        const mean = trustVector.reduce((a, b) => a + b, 0) / 6;
        const variance = trustVector.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / 6;
        // Higher variance = more distinct = higher confidence
        if (variance > 0.1)
            return 'HIGH';
        if (variance > 0.05)
            return 'MEDIUM';
        return 'LOW';
    }
    /**
     * Generate human-readable color name
     */
    generateColorName(color, spectrum) {
        // Find dominant band
        const maxIndex = spectrum.indexOf(Math.max(...spectrum));
        const bandName = exports.SPECTRAL_BANDS[maxIndex].name;
        // Determine intensity modifier
        const brightness = (color.r + color.g + color.b) / 3;
        let modifier = '';
        if (brightness > 200)
            modifier = 'Bright ';
        else if (brightness > 150)
            modifier = 'Light ';
        else if (brightness < 80)
            modifier = 'Dark ';
        else if (brightness < 120)
            modifier = 'Deep ';
        // Determine saturation modifier
        const max = Math.max(color.r, color.g, color.b);
        const min = Math.min(color.r, color.g, color.b);
        const saturation = max === 0 ? 0 : (max - min) / max;
        if (saturation < 0.2)
            return `${modifier}Gray-${bandName}`;
        if (saturation > 0.8)
            return `${modifier}Vivid ${bandName}`;
        return `${modifier}${bandName}`;
    }
    /**
     * Convert HSL to RGB
     */
    hslToRgb(hsl) {
        const h = hsl.h / 360;
        const s = hsl.s / 100;
        const l = hsl.l / 100;
        let r, g, b;
        if (s === 0) {
            r = g = b = l;
        }
        else {
            const hue2rgb = (p, q, t) => {
                if (t < 0)
                    t += 1;
                if (t > 1)
                    t -= 1;
                if (t < 1 / 6)
                    return p + (q - p) * 6 * t;
                if (t < 1 / 2)
                    return q;
                if (t < 2 / 3)
                    return p + (q - p) * (2 / 3 - t) * 6;
                return p;
            };
            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;
            r = hue2rgb(p, q, h + 1 / 3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1 / 3);
        }
        return {
            r: Math.round(r * 255),
            g: Math.round(g * 255),
            b: Math.round(b * 255),
        };
    }
    /**
     * Convert RGB to hex string
     */
    rgbToHex(rgb) {
        const toHex = (n) => n.toString(16).padStart(2, '0');
        return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`.toUpperCase();
    }
    /**
     * Compare two spectral identities for similarity
     *
     * @returns Similarity score 0-1 (1 = identical)
     */
    compareIdentities(a, b) {
        // Compare spectrums
        let spectrumDiff = 0;
        for (let i = 0; i < 7; i++) {
            spectrumDiff += Math.abs(a.spectrum[i] - b.spectrum[i]);
        }
        const spectrumSimilarity = 1 - spectrumDiff / 7;
        // Compare tongue signatures
        let tongueDiff = 0;
        for (let i = 0; i < 6; i++) {
            const colorDiff = (Math.abs(a.tongueSignature[i].r - b.tongueSignature[i].r) +
                Math.abs(a.tongueSignature[i].g - b.tongueSignature[i].g) +
                Math.abs(a.tongueSignature[i].b - b.tongueSignature[i].b)) /
                (255 * 3);
            tongueDiff += colorDiff;
        }
        const tongueSimilarity = 1 - tongueDiff / 6;
        // Weighted average
        return 0.6 * spectrumSimilarity + 0.4 * tongueSimilarity;
    }
    /**
     * Generate visual representation (ASCII art)
     */
    generateVisual(identity) {
        const bars = identity.spectrum.map((intensity, i) => {
            const band = exports.SPECTRAL_BANDS[i];
            const barLength = Math.round(intensity * 20);
            const bar = '█'.repeat(barLength) + '░'.repeat(20 - barLength);
            return `${band.name.padEnd(7)} ${bar} ${(intensity * 100).toFixed(1)}%`;
        });
        return [
            `╔══════════════════════════════════════════╗`,
            `║  SPECTRAL IDENTITY: ${identity.entityId.slice(0, 18).padEnd(18)} ║`,
            `╠══════════════════════════════════════════╣`,
            `║  Color: ${identity.hexCode} (${identity.colorName.slice(0, 20).padEnd(20)}) ║`,
            `║  Hash:  ${identity.spectralHash.padEnd(30)} ║`,
            `║  Confidence: ${identity.confidence.padEnd(26)} ║`,
            `╠══════════════════════════════════════════╣`,
            ...bars.map((b) => `║  ${b.padEnd(38)} ║`),
            `╚══════════════════════════════════════════╝`,
        ].join('\n');
    }
}
exports.SpectralIdentityGenerator = SpectralIdentityGenerator;
// Export singleton instance
exports.spectralGenerator = new SpectralIdentityGenerator();
//# sourceMappingURL=spectral-identity.js.map