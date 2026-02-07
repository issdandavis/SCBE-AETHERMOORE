/**
 * Dual-Channel Consensus: Type Definitions
 *
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */
export interface AudioProfile {
    SR: number;
    N: number;
    binResolution: number;
    f_min: number;
    f_max: number;
    k_min: number;
    k_max: number;
    b: number;
    delta_k_min: number;
    gamma: number;
    betaFactor: number;
    E_min: number;
    clipThreshold: number;
}
/**
 * Compute expected correlation for clean watermark
 */
export declare function expectedCorrelation(profile: AudioProfile): number;
/**
 * Compute beta threshold from profile
 */
export declare function computeBeta(profile: AudioProfile): number;
export interface BinSelection {
    bins: number[];
    phases: number[];
}
export interface WatermarkResult {
    waveform: Float32Array;
    bins: number[];
    phases: number[];
}
export interface VerificationResult {
    correlation: number;
    projections: number[];
    energy: number;
    clipped: boolean;
    passed: boolean;
}
export type DecisionOutcome = 'ALLOW' | 'QUARANTINE' | 'DENY';
/**
 * Predefined audio profiles for different use cases
 */
export declare const PROFILE_16K: AudioProfile;
export declare const PROFILE_44K: AudioProfile;
export declare const PROFILE_48K: AudioProfile;
//# sourceMappingURL=types.d.ts.map