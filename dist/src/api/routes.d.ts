/**
 * SCBE-AETHERMOORE API Routes
 * ===========================
 * Core API endpoints for the 14-layer security framework
 *
 * Endpoints:
 * 1. POST /api/authorize     - Run 14-layer authorization pipeline
 * 2. GET  /api/realms        - Get available realm centers
 * 3. POST /api/envelope      - Create RWP v3 envelope
 * 4. POST /api/verify        - Verify RWP v3 envelope
 * 5. GET  /api/status        - System health and metrics
 * 6. POST /api/fleet/task    - Submit task to fleet orchestrator
 *
 * @module api/routes
 * @version 1.0.0
 */
export interface AuthorizeRequest {
    /** Input features for 14-layer pipeline (12-dimensional) */
    features: number[];
    /** Agent identifier */
    agentId: string;
    /** Topic/context of the request */
    topic: string;
    /** Additional metadata */
    metadata?: Record<string, unknown>;
    /** Optional telemetry signal for spectral coherence */
    telemetrySignal?: number[];
    /** Optional audio frame for Layer 14 */
    audioFrame?: number[];
}
export interface AuthorizeResponse {
    /** Authorization decision: ALLOW, QUARANTINE, or DENY */
    decision: 'ALLOW' | 'QUARANTINE' | 'DENY';
    /** Base risk score before harmonic amplification */
    riskBase: number;
    /** Amplified risk score (risk_base * H) */
    riskPrime: number;
    /** Minimum distance to nearest realm center */
    dStar: number;
    /** Harmonic scaling factor H(d*, R) */
    harmonicFactor: number;
    /** Coherence metrics */
    coherence: {
        spin: number;
        spectral: number;
        temporal: number;
        audio: number;
    };
    /** Processing latency in milliseconds */
    latencyMs: number;
    /** Request tracking ID */
    requestId: string;
    /** Timestamp */
    timestamp: string;
}
export interface Realm {
    id: string;
    name: string;
    center: number[];
    description: string;
    trustLevel: 'high' | 'medium' | 'low';
}
export interface RealmsResponse {
    realms: Realm[];
    defaultRealm: string;
    totalRealms: number;
}
export interface EnvelopeRequest {
    /** Plaintext message to encrypt */
    plaintext: string;
    /** Password for key derivation */
    password: string;
    /** Additional authenticated data */
    aad?: Record<string, unknown>;
    /** Enable post-quantum encryption */
    pqcEnabled?: boolean;
    /** Enable ML-DSA signature */
    signEnabled?: boolean;
}
export interface EnvelopeResponse {
    /** Encrypted envelope in Sacred Tongue format */
    envelope: string;
    /** Protocol version */
    version: string;
    /** Encryption metadata */
    metadata: {
        algorithm: string;
        pqcEnabled: boolean;
        signed: boolean;
        timestamp: string;
    };
}
export interface VerifyRequest {
    /** Envelope to verify (Sacred Tongue format) */
    envelope: string;
    /** Password for decryption */
    password: string;
}
export interface VerifyResponse {
    /** Verification result */
    valid: boolean;
    /** Decrypted plaintext (if valid) */
    plaintext?: string;
    /** Verification details */
    details: {
        aadValid: boolean;
        macValid: boolean;
        signatureValid?: boolean;
        pqcUsed: boolean;
    };
    /** Error message (if invalid) */
    error?: string;
}
export interface StatusResponse {
    /** System status */
    status: 'healthy' | 'degraded' | 'unhealthy';
    /** Component health */
    components: {
        pipeline: ComponentStatus;
        crypto: ComponentStatus;
        fleet: ComponentStatus;
        redis: ComponentStatus;
    };
    /** System metrics */
    metrics: {
        requestsPerSecond: number;
        avgLatencyMs: number;
        p99LatencyMs: number;
        uptimeSeconds: number;
        memoryUsageMB: number;
    };
    /** Version info */
    version: {
        api: string;
        scbe: string;
        pqc: string;
    };
    /** Timestamp */
    timestamp: string;
}
export interface ComponentStatus {
    status: 'up' | 'down' | 'degraded';
    latencyMs?: number;
    message?: string;
}
export interface FleetTaskRequest {
    /** Task name/description */
    task: string;
    /** Task context/payload */
    context: Record<string, unknown>;
    /** Priority level */
    priority?: 'critical' | 'high' | 'normal' | 'low';
    /** Preferred agent role */
    assignTo?: string;
    /** Required capabilities */
    requiredCapabilities?: string[];
}
export interface FleetTaskResponse {
    /** Job ID */
    jobId: string;
    /** Job status */
    status: 'pending' | 'active' | 'completed' | 'failed';
    /** Assigned agent */
    assignedTo?: string;
    /** Estimated wait time */
    estimatedWaitMs?: number;
    /** Queue position */
    queuePosition?: number;
}
/**
 * POST /api/authorize
 * Run 14-layer authorization pipeline
 */
export declare function handleAuthorize(req: AuthorizeRequest): Promise<AuthorizeResponse>;
/**
 * GET /api/realms
 * Get available realm centers
 */
export declare function handleGetRealms(): Promise<RealmsResponse>;
/**
 * POST /api/envelope
 * Create RWP v3 envelope
 */
export declare function handleCreateEnvelope(req: EnvelopeRequest): Promise<EnvelopeResponse>;
/**
 * POST /api/verify
 * Verify RWP v3 envelope
 */
export declare function handleVerifyEnvelope(req: VerifyRequest): Promise<VerifyResponse>;
/**
 * GET /api/status
 * System health and metrics
 */
export declare function handleGetStatus(): Promise<StatusResponse>;
/**
 * POST /api/fleet/task
 * Submit task to fleet orchestrator
 */
export declare function handleFleetTask(req: FleetTaskRequest): Promise<FleetTaskResponse>;
export declare class ApiError extends Error {
    statusCode: number;
    constructor(statusCode: number, message: string);
}
export declare const api: {
    handleAuthorize: typeof handleAuthorize;
    handleGetRealms: typeof handleGetRealms;
    handleCreateEnvelope: typeof handleCreateEnvelope;
    handleVerifyEnvelope: typeof handleVerifyEnvelope;
    handleGetStatus: typeof handleGetStatus;
    handleFleetTask: typeof handleFleetTask;
    ApiError: typeof ApiError;
};
export default api;
//# sourceMappingURL=routes.d.ts.map