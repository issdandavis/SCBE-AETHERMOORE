/**
 * Unified SCBE Gateway API
 *
 * Central entry point that integrates:
 * - SCBE 14-layer authorization pipeline
 * - Spiralverse Six Sacred Tongues encoding
 * - Swarm coordination and fleet management
 * - Contact graph routing
 * - Trust vector computation
 *
 * @module gateway/unified-api
 */
import { type ContactPath } from '../network/contact-graph.js';
export interface AuthorizationRequest {
    agentId: string;
    action: string;
    target: string;
    context?: Record<string, unknown>;
    tongues?: TongueID[];
}
export interface AuthorizationResponse {
    decision: 'ALLOW' | 'QUARANTINE' | 'DENY';
    decisionId: string;
    score: number;
    riskFactors: RiskFactors;
    token?: string;
    expiresAt?: string;
    explanation?: LayerExplanation;
}
export interface RiskFactors {
    hyperbolicDistance: number;
    spectralCoherence: number;
    spinCoherence: number;
    triadicDistance: number;
    audioStability: number;
    harmonicMagnification: number;
    compositeRisk: number;
}
export interface LayerExplanation {
    layers: Record<string, LayerResult>;
    dominantFactor: string;
    recommendation: string;
}
export interface LayerResult {
    name: string;
    value: number;
    contribution: number;
    status: 'pass' | 'warn' | 'fail';
}
export type TongueID = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
export interface RWPEnvelope {
    ver: '2.1' | '3.0';
    primaryTongue: TongueID;
    payload: string;
    signatures: Record<TongueID, string>;
    nonce: string;
    timestamp: number;
    aad?: string;
}
export interface SwarmState {
    swarmId: string;
    agents: AgentState[];
    coherenceScore: number;
    dominantState: 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';
    trustMatrix: number[][];
    contactGraph: ContactGraphData;
}
export interface AgentState {
    id: string;
    position6D: number[];
    trustScore: number;
    trustLevel: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL';
    trustVector: number[];
    dimensionalState: 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';
    nu: number;
    swarmId?: string;
}
export interface ContactGraphData {
    nodes: Array<{
        id: string;
        type: string;
        position: number[];
        trust: number;
    }>;
    edges: Array<{
        source: string;
        target: string;
        latency: number;
        capacity: number;
    }>;
}
export interface QuantumKeyExchange {
    sessionId: string;
    publicKey: string;
    algorithm: 'ML-KEM-768' | 'ML-KEM-1024';
    timestamp: number;
}
export interface GatewayConfig {
    scbeEndpoint?: string;
    quantumEndpoint?: string;
    spiralverseEndpoint?: string;
    redisUrl?: string;
    defaultTongues?: TongueID[];
    riskThresholds?: {
        allow: number;
        deny: number;
    };
}
/**
 * Unified SCBE Gateway
 *
 * Provides a single API for all SCBE ecosystem services:
 * - Authorization (14-layer pipeline)
 * - Protocol encoding (Six Sacred Tongues)
 * - Quantum key exchange (ML-KEM)
 * - Swarm coordination
 * - Contact graph routing
 */
export declare class UnifiedSCBEGateway {
    private config;
    private contactGraph;
    private agentRegistry;
    private swarmRegistry;
    constructor(config?: GatewayConfig);
    /**
     * Process authorization request through 14-layer SCBE pipeline
     */
    authorize(request: AuthorizationRequest): Promise<AuthorizationResponse>;
    /**
     * Encode message using Spiralverse protocol
     */
    encodeRWP(payload: unknown, tongues?: TongueID[]): Promise<RWPEnvelope>;
    /**
     * Verify and decode RWP envelope
     */
    decodeRWP(envelope: RWPEnvelope): Promise<{
        valid: boolean;
        payload?: unknown;
        error?: string;
    }>;
    /**
     * Get current state of a swarm
     */
    getSwarmState(swarmId: string): Promise<SwarmState>;
    /**
     * Register an agent with a swarm
     */
    registerAgent(agent: AgentState, swarmId?: string): void;
    /**
     * Update agent state
     */
    updateAgent(agentId: string, updates: Partial<AgentState>): boolean;
    /**
     * Find optimal path between two agents
     */
    findPath(source: string, target: string): ContactPath | null;
    /**
     * Find k-redundant paths for fault tolerance
     */
    findRedundantPaths(source: string, target: string, k?: number): ContactPath[];
    /**
     * Rebuild contact graph from current agents
     */
    rebuildContactGraph(): void;
    /**
     * Initiate quantum key exchange
     */
    initiateQuantumKeyExchange(peerId: string, algorithm?: 'ML-KEM-768' | 'ML-KEM-1024'): Promise<QuantumKeyExchange>;
    private encodeContext;
    private embedToPoincareBall;
    private computeHyperbolicDistance;
    private applyBreathingTransform;
    private applyPhaseTransform;
    private computeRealmDistance;
    private computeSpectralCoherence;
    private computeSpinCoherence;
    private computeTriadicDistance;
    private computeAudioStability;
    private computeHarmonicScaling;
    private computeCompositeRisk;
    private makeDecision;
    private generateToken;
    private generateNonce;
    private signWithTongue;
    private verifyTongueSignature;
    private hashString;
    private computeSwarmCoherence;
    private computeDominantState;
    private computeTrustMatrix;
    private buildLayerExplanation;
    private findDominantFactor;
    private generateRecommendation;
}
export default UnifiedSCBEGateway;
//# sourceMappingURL=unified-api.d.ts.map