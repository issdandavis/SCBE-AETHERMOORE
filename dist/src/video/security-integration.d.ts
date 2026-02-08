/**
 * Video-Security Integration Layer
 * =================================
 *
 * Weaves hyperbolic video generation into the SCBE security/governance layer.
 *
 * Integration Points:
 * 1. Fractal Fingerprinting - Unique visual identity per envelope/session
 * 2. Agent Trajectories - Poincaré state embedded in job context
 * 3. Audit Reels - Lattice-watermarked video from envelope history
 * 4. Harmonic Heartbeats - Audio tied to Sacred Tongue masks
 * 5. Visual Proofs - Trajectory replay for verification
 *
 * Change Notes (2026-02-01):
 * - Created integration layer connecting video module to envelope.ts
 * - Added FractalFingerprint for session-unique visual identities
 * - Added trajectory embedding for FleetJob context
 * - Added generateAuditVideo for governance visualization
 * - Uses Ring-LWE watermarking for post-quantum tamper evidence
 */
import type { PoincarePoint, VideoConfig, VideoGenerationResult } from './types.js';
import type { TongueID } from '../spiralverse/types.js';
export type Tongue = TongueID;
import { ProgressCallback } from './generator.js';
import type { AAD, Envelope } from '../crypto/envelope.js';
import type { JobData, AgentRole } from '../fleet/redis-orchestrator.js';
/**
 * Fractal fingerprint - unique visual identity derived from session context
 */
export interface FractalFingerprint {
    /** 64-char hex hash of the fingerprint */
    hash: string;
    /** The fractal frame data (RGBA) */
    imageData: Uint8ClampedArray;
    /** Width of fingerprint image */
    width: number;
    /** Height of fingerprint image */
    height: number;
    /** Poincaré state used to generate */
    poincareState: PoincarePoint;
    /** Tongue used */
    tongue: Tongue;
    /** Timestamp of generation */
    timestamp: number;
}
/**
 * Generate a fractal fingerprint from envelope AAD.
 * This creates a unique, reproducible visual identity for any envelope.
 *
 * @param aad - Envelope AAD (Additional Authenticated Data)
 * @param size - Image size (square, default 64)
 * @returns Fractal fingerprint with hash and image data
 */
export declare function generateFractalFingerprint(aad: AAD, size?: number): FractalFingerprint;
/**
 * Verify a fractal fingerprint matches an envelope.
 *
 * @param fingerprint - The fingerprint to verify
 * @param aad - The envelope AAD
 * @returns True if fingerprint matches the AAD
 */
export declare function verifyFractalFingerprint(fingerprint: FractalFingerprint, aad: AAD): boolean;
/**
 * Extended job data with Poincaré trajectory state
 */
export interface TrajectoryJobData extends JobData {
    /** Current Poincaré state for the agent */
    poincareState?: PoincarePoint;
    /** Trajectory history (last N states) */
    trajectoryHistory?: PoincarePoint[];
    /** Maximum history length */
    maxHistoryLength?: number;
}
/**
 * Create trajectory-enhanced job data for an agent.
 * Embeds the current Poincaré state into the job context.
 *
 * @param job - Base job data
 * @param agentRole - The agent role processing this job
 * @param timestamp - Current timestamp
 * @returns Enhanced job data with trajectory state
 */
export declare function embedTrajectoryState(job: JobData, agentRole: AgentRole, timestamp: number): TrajectoryJobData;
/**
 * Extract trajectory visualization from job history.
 *
 * @param jobs - Array of trajectory-enhanced jobs
 * @returns Combined trajectory points
 */
export declare function extractJobTrajectory(jobs: TrajectoryJobData[]): PoincarePoint[];
/**
 * Audit reel configuration
 */
export interface AuditReelConfig {
    /** Video width (default 256) */
    width?: number;
    /** Video height (default 256) */
    height?: number;
    /** Frames per second (default 15) */
    fps?: number;
    /** Duration in seconds (auto-calculated from history length if not specified) */
    duration?: number;
    /** Enable lattice watermarking (default true) */
    enableWatermark?: boolean;
    /** Enable audio track (default true) */
    enableAudio?: boolean;
    /** Chaos strength (default 0.4) */
    chaosStrength?: number;
    /** Breathing amplitude (default 0.03) */
    breathingAmplitude?: number;
}
/**
 * Audit reel result
 */
export interface AuditReelResult extends VideoGenerationResult {
    /** Envelope hashes included in the audit */
    envelopeHashes: string[];
    /** Fractal fingerprints for each envelope */
    fingerprints: FractalFingerprint[];
    /** Chain of custody hash */
    chainOfCustodyHash: string;
}
/**
 * Generate an audit reel from envelope history.
 * Creates a lattice-watermarked video visualizing the decision path.
 *
 * @param envelopes - Array of envelopes to visualize
 * @param config - Audit reel configuration
 * @param onProgress - Progress callback
 * @returns Audit reel result with watermarked video
 */
export declare function generateAuditReel(envelopes: Envelope[], config?: AuditReelConfig, onProgress?: ProgressCallback): Promise<AuditReelResult>;
/**
 * Stream audit reel frames for memory-efficient processing.
 *
 * @param envelopes - Array of envelopes to visualize
 * @param config - Audit reel configuration
 * @yields Video frames one at a time
 */
export declare function streamAuditReelFrames(envelopes: Envelope[], config?: AuditReelConfig): AsyncGenerator<{
    frame: Uint8ClampedArray;
    index: number;
    timestamp: number;
    poincareState: PoincarePoint;
}, void, unknown>;
/**
 * Visual proof - trajectory replay for verification
 */
export interface VisualProof {
    /** The trajectory points */
    trajectory: PoincarePoint[];
    /** Tongue used */
    tongue: Tongue;
    /** Start timestamp */
    startTime: number;
    /** End timestamp */
    endTime: number;
    /** Hash of the proof */
    proofHash: string;
}
/**
 * Create a visual proof from a job trajectory.
 *
 * @param jobs - Array of trajectory-enhanced jobs
 * @param tongue - Tongue to use (default auto-detected)
 * @returns Visual proof for verification
 */
export declare function createVisualProof(jobs: TrajectoryJobData[], tongue?: Tongue): VisualProof;
/**
 * Verify a visual proof by replaying the trajectory.
 *
 * @param proof - The visual proof to verify
 * @param tolerance - Maximum allowed deviation (default 1e-6)
 * @returns True if proof is valid
 */
export declare function verifyVisualProof(proof: VisualProof, tolerance?: number): boolean;
/**
 * Render a visual proof to video.
 *
 * @param proof - The visual proof
 * @param config - Video configuration
 * @param onProgress - Progress callback
 * @returns Video generation result
 */
export declare function renderVisualProof(proof: VisualProof, config?: Partial<VideoConfig>, onProgress?: ProgressCallback): Promise<VideoGenerationResult>;
export declare const videoSecurity: {
    generateFractalFingerprint: typeof generateFractalFingerprint;
    verifyFractalFingerprint: typeof verifyFractalFingerprint;
    embedTrajectoryState: typeof embedTrajectoryState;
    extractJobTrajectory: typeof extractJobTrajectory;
    generateAuditReel: typeof generateAuditReel;
    streamAuditReelFrames: typeof streamAuditReelFrames;
    createVisualProof: typeof createVisualProof;
    verifyVisualProof: typeof verifyVisualProof;
    renderVisualProof: typeof renderVisualProof;
};
export default videoSecurity;
//# sourceMappingURL=security-integration.d.ts.map