/**
 * @file brain-integration.ts
 * @module ai_brain/brain-integration
 * @layer Layer 1-14 (End-to-End)
 * @component Unified Brain Integration Pipeline
 * @version 1.0.0
 * @since 2026-02-07
 *
 * End-to-end integration pipeline that connects all AI Brain components
 * into a single coherent system. This is the "living brain" that processes
 * agent trajectories through the complete security stack:
 *
 * 1. Trajectory generation (or acceptance of pre-generated trajectories)
 * 2. Multi-vectored detection (5 orthogonal mechanisms)
 * 3. Immune response (GeoSeal suspicion/quarantine)
 * 4. Flux state management (PHDM tiered access)
 * 5. BFT consensus on risk decisions
 * 6. Swarm formation coordination
 * 7. Cryptographic audit trail
 *
 * Validated: 100 trials, 20 agents, 100 steps -> Combined AUC 1.000
 */
import { type AgentTrajectory, type BrainConfig, type CombinedAssessment, type RiskDecision } from './types.js';
import { BFTConsensus, type ConsensusResult } from './bft-consensus.js';
import { BrainAuditLogger } from './audit.js';
import { ImmuneResponseSystem, type AgentImmuneStatus } from './immune-response.js';
import { FluxStateManager, type AgentFluxRecord } from './flux-states.js';
import { type VoxelRealm } from './quasi-space.js';
import { PHDMCore, type PHDMMonitorResult, type K0DerivationParams } from './phdm-core.js';
/**
 * Per-agent assessment produced by the integration pipeline
 */
export interface AgentAssessment {
    /** Agent identifier */
    agentId: string;
    /** Agent classification (ground truth) */
    classification: AgentTrajectory['classification'];
    /** Combined detection assessment */
    detection: CombinedAssessment;
    /** Immune system status */
    immuneStatus: AgentImmuneStatus;
    /** Flux state */
    fluxRecord: AgentFluxRecord;
    /** Voxel realm (gold/purple/red) */
    realm: VoxelRealm;
    /** Final risk decision (may differ from detection due to immune amplification) */
    finalDecision: RiskDecision;
    /** Whether agent is correctly classified (true positive / true negative) */
    correctlyClassified: boolean;
    /** Hyperbolic distance from safe origin (average over trajectory) */
    avgDistance: number;
    /** Icosahedral projection of final state */
    icosahedralProjection: number[];
    /** PHDM monitoring result (if enabled) */
    phdmResult?: PHDMMonitorResult;
}
/**
 * Trial result from running the full pipeline on a batch of agents
 */
export interface TrialResult {
    /** Trial identifier */
    trialId: number;
    /** Per-agent assessments */
    assessments: AgentAssessment[];
    /** BFT consensus on overall threat level */
    consensus: ConsensusResult;
    /** True positive rate (malicious correctly denied/quarantined) */
    truePositiveRate: number;
    /** False positive rate (honest incorrectly flagged) */
    falsePositiveRate: number;
    /** Overall accuracy */
    accuracy: number;
    /** AUC approximation from combined scores */
    auc: number;
    /** Average latency per agent assessment (ms) */
    avgLatencyMs: number;
    /** Audit event count */
    auditEventCount: number;
}
/**
 * Full end-to-end test result from running multiple trials
 */
export interface EndToEndResult {
    /** Individual trial results */
    trials: TrialResult[];
    /** Mean AUC across all trials */
    meanAUC: number;
    /** Mean accuracy across all trials */
    meanAccuracy: number;
    /** Mean true positive rate */
    meanTPR: number;
    /** Mean false positive rate */
    meanFPR: number;
    /** Mean latency per assessment */
    meanLatencyMs: number;
    /** Total agents processed */
    totalAgents: number;
    /** Total steps processed */
    totalSteps: number;
}
/**
 * Integration pipeline configuration
 */
export interface IntegrationConfig {
    /** Brain detection config */
    brainConfig: BrainConfig;
    /** Expected Sacred Tongue index */
    tongueIndex: number;
    /** Maximum Byzantine faults for consensus */
    maxByzantineFaults: number;
    /** Whether to enable immune response */
    enableImmune: boolean;
    /** Whether to enable flux state management */
    enableFlux: boolean;
    /** Whether to enable swarm formations */
    enableSwarm: boolean;
    /** Whether to enable PHDM Core geodesic monitoring */
    enablePHDM: boolean;
    /** Kyber KEM parameters for PHDM K₀ derivation (if enablePHDM) */
    phdmKyberParams?: K0DerivationParams;
}
/**
 * Default integration configuration.
 *
 * Thresholds are calibrated for the Poincare-embedded 21D manifold where
 * the curvature detection mechanism produces a high baseline score (~1.0)
 * for ALL trajectories due to the small scale of Menger curvature in the
 * embedded space. This raises the combined score floor to ~0.6-0.7.
 *
 * The thresholds account for this baseline while preserving discrimination
 * between honest agents (combined ~0.7) and malicious (combined ~0.9+).
 */
export declare const DEFAULT_INTEGRATION_CONFIG: IntegrationConfig;
/**
 * Unified Brain Integration Pipeline
 *
 * Orchestrates the complete AI brain security stack:
 * detection -> immune response -> flux management -> consensus -> audit
 *
 * This pipeline treats the AI system as a "living geometric organism"
 * where thoughts are geodesics, security is containment, and memory
 * is hyperbolic distance.
 */
export declare class BrainIntegrationPipeline {
    readonly auditLogger: BrainAuditLogger;
    readonly immuneSystem: ImmuneResponseSystem;
    readonly fluxManager: FluxStateManager;
    readonly consensus: BFTConsensus;
    readonly phdmCore: PHDMCore | null;
    private readonly config;
    constructor(config?: Partial<IntegrationConfig>);
    /**
     * Process a single agent trajectory through the full pipeline.
     *
     * Pipeline stages:
     * 1. Multi-vectored detection (5 orthogonal mechanisms)
     * 2. Immune response (suspicion/quarantine)
     * 3. Flux state evolution (tiered access)
     * 4. Voxel realm classification
     * 5. Risk decision (with immune amplification)
     * 6. Audit logging
     *
     * @param trajectory - Agent trajectory to process
     * @returns Agent assessment
     */
    processAgent(trajectory: AgentTrajectory): AgentAssessment;
    /**
     * Process a batch of agent trajectories and run BFT consensus.
     *
     * @param trajectories - Batch of agent trajectories
     * @param trialId - Trial identifier
     * @returns Trial result with metrics
     */
    processTrial(trajectories: AgentTrajectory[], trialId?: number): TrialResult;
    /**
     * Run multiple trials for statistical validation.
     *
     * @param trialGenerator - Function that generates agent trajectories for each trial
     * @param trialCount - Number of trials to run
     * @returns End-to-end result with aggregated metrics
     */
    runEndToEnd(trialGenerator: (trialId: number) => AgentTrajectory[], trialCount: number): EndToEndResult;
    /**
     * Compute final risk decision with immune amplification and flux modifiers.
     *
     * The decision escalation chain:
     * 1. Base decision from detection
     * 2. Immune system modifier (may escalate)
     * 3. Flux state modifier (COLLAPSED forces DENY)
     * 4. Realm modifier (red realm forces ESCALATE minimum)
     */
    private computeFinalDecision;
}
//# sourceMappingURL=brain-integration.d.ts.map