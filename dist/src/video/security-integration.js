"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.videoSecurity = void 0;
exports.generateFractalFingerprint = generateFractalFingerprint;
exports.verifyFractalFingerprint = verifyFractalFingerprint;
exports.embedTrajectoryState = embedTrajectoryState;
exports.extractJobTrajectory = extractJobTrajectory;
exports.generateAuditReel = generateAuditReel;
exports.streamAuditReelFrames = streamAuditReelFrames;
exports.createVisualProof = createVisualProof;
exports.verifyVisualProof = verifyVisualProof;
exports.renderVisualProof = renderVisualProof;
const types_js_1 = require("./types.js");
const generator_js_1 = require("./generator.js");
const fractal_js_1 = require("./fractal.js");
const watermark_js_1 = require("./watermark.js");
const trajectory_js_1 = require("./trajectory.js");
/**
 * Generate a fractal fingerprint from envelope AAD.
 * This creates a unique, reproducible visual identity for any envelope.
 *
 * @param aad - Envelope AAD (Additional Authenticated Data)
 * @param size - Image size (square, default 64)
 * @returns Fractal fingerprint with hash and image data
 */
function generateFractalFingerprint(aad, size = 64) {
    // Clamp size
    const clampedSize = Math.max(16, Math.min(512, Math.floor(size)));
    // Map AAD to Poincaré point
    const poincareState = (0, trajectory_js_1.contextToPoincarePoint)({
        time: aad.ts,
        entropy: parseInt(aad.canonical_body_hash.slice(0, 8), 16) / 0xffffffff,
        threatLevel: 0, // Fingerprints are neutral
        userId: parseInt(aad.request_id.slice(0, 8), 16),
        behavioralStability: 0.9, // High stability for consistent fingerprints
        audioPhase: (parseInt(aad.schema_hash.slice(0, 4), 16) / 0xffff) * Math.PI * 2,
    });
    // Determine tongue from provider_id hash
    const tongues = ['ko', 'av', 'ru', 'ca', 'um', 'dr'];
    const tongueIndex = hashStringToNumber(aad.provider_id) % tongues.length;
    const tongue = tongues[tongueIndex];
    const fractalConfig = types_js_1.TONGUE_FRACTAL_CONFIGS[tongue];
    // Render fractal frame
    const normalized = (0, fractal_js_1.renderFractalFrame)(clampedSize, clampedSize, fractalConfig, poincareState, 0.3, // Fixed chaos for consistency
    0, // No breathing for static fingerprint
    0 // Time = 0 for determinism
    );
    // Apply colormap
    const imageData = (0, fractal_js_1.applyColormap)(normalized, fractalConfig.colormap, clampedSize, clampedSize);
    // Generate hash from image data
    const hash = (0, watermark_js_1.hashFrameContent)(imageData, 0, aad.ts);
    return {
        hash,
        imageData,
        width: clampedSize,
        height: clampedSize,
        poincareState,
        tongue,
        timestamp: Date.now(),
    };
}
/**
 * Verify a fractal fingerprint matches an envelope.
 *
 * @param fingerprint - The fingerprint to verify
 * @param aad - The envelope AAD
 * @returns True if fingerprint matches the AAD
 */
function verifyFractalFingerprint(fingerprint, aad) {
    const regenerated = generateFractalFingerprint(aad, fingerprint.width);
    // Compare hashes
    if (regenerated.hash !== fingerprint.hash) {
        return false;
    }
    // Compare Poincaré states (should be identical for same AAD)
    for (let i = 0; i < 6; i++) {
        if (Math.abs(regenerated.poincareState[i] - fingerprint.poincareState[i]) > 1e-10) {
            return false;
        }
    }
    return true;
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
function embedTrajectoryState(job, agentRole, timestamp) {
    // Map agent role to tongue
    const roleTongueMap = {
        captain: 'ko', // Korean - orchestration
        architect: 'av', // Avar - design
        researcher: 'ru', // Russian - analysis
        developer: 'ca', // Catalan - implementation
        qa: 'um', // Umbrian - validation
        security: 'dr', // Druidic - protection
        reviewer: 'av', // Avar - review
        documenter: 'ru', // Russian - documentation
        deployer: 'ca', // Catalan - deployment
        monitor: 'um', // Umbrian - monitoring
    };
    const tongue = roleTongueMap[agentRole] || 'av';
    // Create context vector from job
    const entropy = job.metadata ? Object.keys(job.metadata).length / 10 : 0.5;
    const threatLevel = job.requiredCapabilities?.includes('security') ? 0.7 : 0.2;
    const poincareState = (0, trajectory_js_1.contextToPoincarePoint)({
        time: timestamp,
        entropy: Math.min(1, entropy),
        threatLevel,
        userId: hashStringToNumber(job.task),
        behavioralStability: 0.8,
        audioPhase: (timestamp / 1000) % (Math.PI * 2),
    });
    // Get existing history or create new
    const existingData = job;
    const maxHistory = existingData.maxHistoryLength || 30;
    const history = existingData.trajectoryHistory || [];
    // Add current state to history
    history.push(poincareState);
    if (history.length > maxHistory) {
        history.shift();
    }
    return {
        ...job,
        poincareState,
        trajectoryHistory: history,
        maxHistoryLength: maxHistory,
        metadata: {
            ...job.metadata,
            tongue,
            trajectoryEmbeddedAt: timestamp,
        },
    };
}
/**
 * Extract trajectory visualization from job history.
 *
 * @param jobs - Array of trajectory-enhanced jobs
 * @returns Combined trajectory points
 */
function extractJobTrajectory(jobs) {
    const trajectory = [];
    for (const job of jobs) {
        if (job.poincareState) {
            trajectory.push(job.poincareState);
        }
        if (job.trajectoryHistory) {
            // Add any states not already in trajectory
            for (const state of job.trajectoryHistory) {
                if (!trajectory.some((t) => arraysEqual(t, state))) {
                    trajectory.push(state);
                }
            }
        }
    }
    return trajectory;
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
async function generateAuditReel(envelopes, config = {}, onProgress) {
    if (envelopes.length === 0) {
        throw new Error('Cannot generate audit reel from empty envelope history');
    }
    // Configure video parameters
    const width = config.width || 256;
    const height = config.height || 256;
    const fps = config.fps || 15;
    // Auto-calculate duration: 0.5 seconds per envelope, minimum 2 seconds
    const duration = config.duration || Math.max(2, envelopes.length * 0.5);
    // Generate fingerprints for each envelope
    const fingerprints = [];
    const envelopeHashes = [];
    for (const envelope of envelopes) {
        const fingerprint = generateFractalFingerprint(envelope.aad, 64);
        fingerprints.push(fingerprint);
        envelopeHashes.push(envelope.aad.canonical_body_hash);
    }
    // Determine dominant tongue from envelopes
    const tongueCount = new Map();
    for (const fp of fingerprints) {
        tongueCount.set(fp.tongue, (tongueCount.get(fp.tongue) || 0) + 1);
    }
    let dominantTongue = 'av';
    let maxCount = 0;
    for (const [tongue, count] of tongueCount) {
        if (count > maxCount) {
            maxCount = count;
            dominantTongue = tongue;
        }
    }
    // Create seed from envelope chain
    const seedStr = envelopeHashes.join(':');
    const seed = hashStringToNumber(seedStr);
    // Generate video
    const videoConfig = {
        width,
        height,
        fps,
        duration,
        tongue: dominantTongue,
        fractalMode: 'hybrid', // Use hybrid for audit visualization
        chaosStrength: config.chaosStrength ?? 0.4,
        breathingAmplitude: config.breathingAmplitude ?? 0.03,
        enableWatermark: config.enableWatermark ?? true,
        enableAudio: config.enableAudio ?? true,
        outputFormat: 'frames',
    };
    const videoResult = await (0, generator_js_1.generateVideo)(videoConfig, {
        dimension: 32,
        modulus: 127,
        errorBound: 2,
    }, {
        sampleRate: 22050,
        harmonicCount: 4,
    }, seed, onProgress);
    // Create chain of custody hash
    const chainOfCustodyHash = (0, watermark_js_1.hashFrameContent)(new Uint8ClampedArray(envelopeHashes
        .join('')
        .split('')
        .map((c) => c.charCodeAt(0))), envelopes.length, Date.now());
    return {
        ...videoResult,
        envelopeHashes,
        fingerprints,
        chainOfCustodyHash,
    };
}
/**
 * Stream audit reel frames for memory-efficient processing.
 *
 * @param envelopes - Array of envelopes to visualize
 * @param config - Audit reel configuration
 * @yields Video frames one at a time
 */
async function* streamAuditReelFrames(envelopes, config = {}) {
    if (envelopes.length === 0) {
        return;
    }
    const width = config.width || 256;
    const height = config.height || 256;
    const fps = config.fps || 15;
    const duration = config.duration || Math.max(2, envelopes.length * 0.5);
    // Generate fingerprints and determine tongue
    const fingerprints = envelopes.map((e) => generateFractalFingerprint(e.aad, 64));
    const tongueCount = new Map();
    for (const fp of fingerprints) {
        tongueCount.set(fp.tongue, (tongueCount.get(fp.tongue) || 0) + 1);
    }
    let dominantTongue = 'av';
    let maxCount = 0;
    for (const [tongue, count] of tongueCount) {
        if (count > maxCount) {
            maxCount = count;
            dominantTongue = tongue;
        }
    }
    // Create seed
    const seedStr = envelopes.map((e) => e.aad.canonical_body_hash).join(':');
    const seed = hashStringToNumber(seedStr);
    // Stream frames
    for await (const frame of (0, generator_js_1.streamVideoFrames)({
        width,
        height,
        fps,
        duration,
        tongue: dominantTongue,
        fractalMode: 'hybrid',
        chaosStrength: config.chaosStrength ?? 0.4,
        breathingAmplitude: config.breathingAmplitude ?? 0.03,
        enableWatermark: config.enableWatermark ?? true,
    }, {}, seed)) {
        yield {
            frame: frame.data,
            index: frame.index,
            timestamp: frame.timestamp,
            poincareState: frame.poincareState,
        };
    }
}
/**
 * Create a visual proof from a job trajectory.
 *
 * @param jobs - Array of trajectory-enhanced jobs
 * @param tongue - Tongue to use (default auto-detected)
 * @returns Visual proof for verification
 */
function createVisualProof(jobs, tongue) {
    const trajectory = extractJobTrajectory(jobs);
    if (trajectory.length === 0) {
        throw new Error('Cannot create visual proof from empty trajectory');
    }
    // Auto-detect tongue from job metadata
    if (!tongue) {
        for (const job of jobs) {
            if (job.metadata?.tongue) {
                tongue = job.metadata.tongue;
                break;
            }
        }
        tongue = tongue || 'av';
    }
    // Get time bounds
    const times = jobs
        .filter((j) => j.metadata?.trajectoryEmbeddedAt)
        .map((j) => j.metadata.trajectoryEmbeddedAt);
    const startTime = times.length > 0 ? Math.min(...times) : Date.now();
    const endTime = times.length > 0 ? Math.max(...times) : Date.now();
    // Create proof hash
    const proofData = trajectory
        .flat()
        .map((v) => v.toString())
        .join(':');
    const proofHash = (0, watermark_js_1.hashFrameContent)(new Uint8ClampedArray(proofData.split('').map((c) => c.charCodeAt(0))), trajectory.length, startTime);
    return {
        trajectory,
        tongue,
        startTime,
        endTime,
        proofHash,
    };
}
/**
 * Verify a visual proof by replaying the trajectory.
 *
 * @param proof - The visual proof to verify
 * @param tolerance - Maximum allowed deviation (default 1e-6)
 * @returns True if proof is valid
 */
function verifyVisualProof(proof, tolerance = 1e-6) {
    // Verify all points are inside Poincaré ball
    for (const point of proof.trajectory) {
        if (point.length !== 6)
            return false;
        let normSq = 0;
        for (const v of point) {
            if (!Number.isFinite(v))
                return false;
            normSq += v * v;
        }
        if (normSq >= 1)
            return false;
    }
    // Verify proof hash
    const proofData = proof.trajectory
        .flat()
        .map((v) => v.toString())
        .join(':');
    const expectedHash = (0, watermark_js_1.hashFrameContent)(new Uint8ClampedArray(proofData.split('').map((c) => c.charCodeAt(0))), proof.trajectory.length, proof.startTime);
    return expectedHash === proof.proofHash;
}
/**
 * Render a visual proof to video.
 *
 * @param proof - The visual proof
 * @param config - Video configuration
 * @param onProgress - Progress callback
 * @returns Video generation result
 */
async function renderVisualProof(proof, config = {}, onProgress) {
    // Calculate duration based on trajectory length
    const fps = config.fps || 30;
    const duration = config.duration || Math.max(2, proof.trajectory.length / fps);
    return (0, generator_js_1.generateVideo)({
        width: config.width || 256,
        height: config.height || 256,
        fps,
        duration,
        tongue: proof.tongue,
        fractalMode: config.fractalMode || 'julia',
        chaosStrength: config.chaosStrength ?? 0.5,
        breathingAmplitude: config.breathingAmplitude ?? 0.04,
        enableWatermark: config.enableWatermark ?? true,
        enableAudio: config.enableAudio ?? true,
        outputFormat: config.outputFormat || 'frames',
    }, {}, {}, proof.startTime, // Use proof start time as seed for determinism
    onProgress);
}
// ============================================================
// HELPER FUNCTIONS
// ============================================================
/**
 * Hash a string to a number for seeding.
 */
function hashStringToNumber(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = (hash << 5) - hash + char;
        hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash);
}
/**
 * Check if two PoincarePoint arrays are equal.
 */
function arraysEqual(a, b) {
    if (a.length !== b.length)
        return false;
    for (let i = 0; i < a.length; i++) {
        if (Math.abs(a[i] - b[i]) > 1e-10)
            return false;
    }
    return true;
}
// ============================================================
// EXPORTS
// ============================================================
exports.videoSecurity = {
    // Fractal Fingerprinting
    generateFractalFingerprint,
    verifyFractalFingerprint,
    // Agent Trajectory Embedding
    embedTrajectoryState,
    extractJobTrajectory,
    // Audit Reel Generation
    generateAuditReel,
    streamAuditReelFrames,
    // Visual Proof Verification
    createVisualProof,
    verifyVisualProof,
    renderVisualProof,
};
exports.default = exports.videoSecurity;
//# sourceMappingURL=security-integration.js.map