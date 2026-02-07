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
/**
 * RGB color representation
 */
export interface RGB {
    r: number;
    g: number;
    b: number;
}
/**
 * HSL color representation (for easier manipulation)
 */
export interface HSL {
    h: number;
    s: number;
    l: number;
}
/**
 * Spectral band definition
 */
export interface SpectralBand {
    name: string;
    wavelengthMin: number;
    wavelengthMax: number;
    hueMin: number;
    hueMax: number;
    layers: number[];
    sacredTongue?: string;
}
/**
 * Complete spectral identity
 */
export interface SpectralIdentity {
    /** Unique identifier */
    entityId: string;
    /** Primary color (dominant band) */
    primaryColor: RGB;
    /** Secondary color (second strongest) */
    secondaryColor: RGB;
    /** Full 7-band spectrum intensities */
    spectrum: number[];
    /** 6-tongue chromatic signature */
    tongueSignature: RGB[];
    /** Combined hex color code */
    hexCode: string;
    /** Human-readable color name */
    colorName: string;
    /** Spectral hash (unique fingerprint) */
    spectralHash: string;
    /** Visual confidence indicator */
    confidence: 'HIGH' | 'MEDIUM' | 'LOW';
    /** Timestamp of generation */
    timestamp: number;
}
/**
 * The 7 spectral bands (ROYGBIV)
 */
export declare const SPECTRAL_BANDS: SpectralBand[];
/**
 * Sacred Tongue base colors
 */
export declare const TONGUE_COLORS: Record<string, RGB>;
/**
 * Spectral Identity Generator
 *
 * Creates unique chromatic fingerprints from multi-dimensional vectors.
 */
export declare class SpectralIdentityGenerator {
    private readonly goldenRatio;
    /**
     * Generate spectral identity from a 6D trust vector
     *
     * @param entityId - Unique entity identifier
     * @param trustVector - 6D trust vector (one per Sacred Tongue)
     * @param layerScores - Optional 14-layer scores
     * @returns Complete spectral identity
     */
    generateIdentity(entityId: string, trustVector: number[], layerScores?: number[]): SpectralIdentity;
    /**
     * Generate 7-band spectrum from trust vector
     */
    private generateSpectrum;
    /**
     * Generate Sacred Tongue color signature
     */
    private generateTongueSignature;
    /**
     * Compute dominant colors from spectrum
     */
    private computeDominantColors;
    /**
     * Convert spectral band to RGB
     */
    private bandToRGB;
    /**
     * Blend tongue colors weighted by trust vector
     */
    private blendColors;
    /**
     * Generate unique spectral hash
     */
    private generateSpectralHash;
    /**
     * Compute confidence based on vector variance
     */
    private computeConfidence;
    /**
     * Generate human-readable color name
     */
    private generateColorName;
    /**
     * Convert HSL to RGB
     */
    private hslToRgb;
    /**
     * Convert RGB to hex string
     */
    private rgbToHex;
    /**
     * Compare two spectral identities for similarity
     *
     * @returns Similarity score 0-1 (1 = identical)
     */
    compareIdentities(a: SpectralIdentity, b: SpectralIdentity): number;
    /**
     * Generate visual representation (ASCII art)
     */
    generateVisual(identity: SpectralIdentity): string;
}
export declare const spectralGenerator: SpectralIdentityGenerator;
//# sourceMappingURL=spectral-identity.d.ts.map