/**
 * SCBE-AETHERMOORE Lattice Watermarking
 * ======================================
 *
 * Post-quantum safe watermarking using Ring-LWE lattice cryptography.
 * Embeds verifiable hashes into video frames that survive compression.
 *
 * Security: Learning-with-errors hardness, quantum-resistant, tamper-evident
 */
import type { WatermarkConfig, WatermarkVerification } from './types.js';
/**
 * Generate Ring-LWE public/secret key pair
 *
 * Public key: (a, b) where b = a·s + e
 * Secret key: s
 */
export declare function generateWatermarkKeys(config?: WatermarkConfig): {
    publicKey: number[][];
    secretKey: number[];
};
/**
 * Embed watermark into frame data
 * Uses additive embedding in least significant bits
 */
export declare function embedWatermark(frameData: Uint8ClampedArray | Float32Array, hash: string, publicKey: number[][], config?: WatermarkConfig): Uint8ClampedArray | Float32Array;
/**
 * Extract and verify watermark from frame data
 */
export declare function verifyWatermark(frameData: Uint8ClampedArray | Float32Array, expectedHash: string, secretKey: number[], config?: WatermarkConfig): WatermarkVerification;
/**
 * Generate hash for frame content
 */
export declare function hashFrameContent(frameData: Uint8ClampedArray | Float32Array, frameIndex: number, timestamp: number): string;
/**
 * Create a watermark chain for video integrity
 * Each frame's hash includes the previous frame's hash
 */
export declare function createWatermarkChain(frameHashes: string[]): {
    chainHash: string;
    merkleRoot: string;
};
//# sourceMappingURL=watermark.d.ts.map