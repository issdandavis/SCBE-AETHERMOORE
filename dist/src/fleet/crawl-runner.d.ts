/**
 * @file crawl-runner.ts
 * @module fleet/crawl-runner
 * @layer Layer 1-14 (full pipeline), Layer 5 (hyperbolic), Layer 13 (risk decision)
 * @component CrawlRunner — Browser-backed multi-agent crawl executor
 * @version 1.0.0
 *
 * Integration layer that connects:
 *   CrawlCoordinator  →  task assignment, role switching, safety scoring
 *   BrowserAgent       →  page interaction, 14-layer governance
 *   Detection System   →  swarm-level anomaly detection (5 mechanisms)
 *
 * Each crawl agent is backed by a BrowserAgent with its own session.
 * Role-specific strategies:
 *   SCOUT    — navigate + extract links (discovery)
 *   ANALYZER — navigate + extract structured data
 *   SENTINEL — monitor swarm trajectories, flag anomalies
 *   REPORTER — aggregate and summarize results
 *
 * Safety flow per action:
 *   1. CrawlCoordinator assigns URL from frontier
 *   2. BrowserAgent.navigate() evaluates through 14-layer pipeline
 *   3. If ALLOW: execute, collect observation, extract role-specific data
 *   4. If DENY/ESCALATE: report failure, adjust safety score
 *   5. Sentinel agents run 5-mechanism detection on agent trajectories
 *   6. Anomalous agents are quarantined via CrawlCoordinator
 */
import type { TongueCode } from '../tokenizer/ss1.js';
import type { BrowserBackend } from '../browser/agent.js';
import type { BrowserObservation, GovernanceResult } from '../browser/types.js';
import type { TrajectoryPoint, CombinedAssessment } from '../ai_brain/types.js';
import { CrawlCoordinator, type CrawlRole, type CrawlResult, type CrawlCoordinatorConfig } from './crawl-coordinator.js';
/** Configuration for a single crawl agent's browser backend */
export interface CrawlAgentBrowserConfig {
    /** Agent ID (must match coordinator registration) */
    readonly agentId: string;
    /** Sacred Tongue tier for governance */
    readonly tongue: TongueCode;
    /** Browser backend implementation */
    readonly backend: BrowserBackend;
    /** Initial crawl role */
    readonly role: CrawlRole;
}
/** CrawlRunner configuration */
export interface CrawlRunnerConfig {
    /** Coordinator config overrides */
    coordinator?: Partial<CrawlCoordinatorConfig>;
    /** Detection threshold for sentinel anomaly checks */
    detectionThreshold?: number;
    /** Minimum trajectory length before sentinel checks run */
    minTrajectoryLength?: number;
    /** Maximum trajectory points to retain per agent */
    maxTrajectoryLength?: number;
    /** Auto-quarantine when combined detection score exceeds this */
    quarantineThreshold?: number;
}
/** Default runner configuration */
export declare const DEFAULT_RUNNER_CONFIG: Required<CrawlRunnerConfig>;
/** State for a managed crawl agent */
export interface ManagedAgent {
    /** Agent ID */
    readonly agentId: string;
    /** Sacred Tongue */
    readonly tongue: TongueCode;
    /** Browser backend */
    readonly backend: BrowserBackend;
    /** Whether the browser session is active */
    sessionActive: boolean;
    /** Trajectory points for detection */
    trajectory: TrajectoryPoint[];
    /** Governance results from browser actions */
    governanceLog: GovernanceResult[];
    /** Latest observation */
    lastObservation?: BrowserObservation;
    /** URLs successfully crawled */
    urlsCrawled: string[];
    /** Latest detection assessment (sentinel only) */
    lastAssessment?: CombinedAssessment;
}
/** Result of a single crawl step */
export interface CrawlStepResult {
    /** Agent that performed the step */
    readonly agentId: string;
    /** URL that was crawled */
    readonly url: string;
    /** Whether the crawl succeeded */
    readonly success: boolean;
    /** Governance decision for the navigation action */
    readonly governance: GovernanceResult | null;
    /** Discovered URLs (for scouts) */
    readonly discoveredUrls: string[];
    /** Extracted data (for analyzers) */
    readonly extractedData: Record<string, unknown>;
    /** Safety assessment */
    readonly safetyAssessment: {
        safe: boolean;
        riskScore: number;
        flags: string[];
    };
    /** Error message if failed */
    readonly error?: string;
    /** Duration in milliseconds */
    readonly durationMs: number;
}
/** Sentinel scan result */
export interface SentinelScanResult {
    /** Agent ID of the sentinel */
    readonly sentinelId: string;
    /** Agents scanned */
    readonly scannedAgents: string[];
    /** Agents flagged for anomalies */
    readonly flaggedAgents: Array<{
        agentId: string;
        combinedScore: number;
        decision: string;
        flagCount: number;
    }>;
    /** Agents quarantined as a result */
    readonly quarantinedAgents: string[];
    /** Timestamp */
    readonly timestamp: number;
}
/** Runner statistics */
export interface RunnerStats {
    /** Total crawl steps executed */
    totalSteps: number;
    /** Successful steps */
    successfulSteps: number;
    /** Failed steps (governance denied or error) */
    failedSteps: number;
    /** Steps denied by governance */
    governanceDenied: number;
    /** Sentinel scans performed */
    sentinelScans: number;
    /** Agents quarantined by sentinel */
    sentinelQuarantines: number;
    /** Total discovered URLs */
    totalDiscoveredUrls: number;
    /** Coordinator stats */
    coordinatorStats: ReturnType<CrawlCoordinator['getStats']>;
}
/**
 * Extract links from a page observation.
 * Scans interactive elements for anchor tags with href in dataAttributes.
 * Filters to http(s) URLs and deduplicates.
 */
export declare function extractLinksFromObservation(observation: BrowserObservation): string[];
/**
 * Extract structured data from a page observation.
 * Returns page metadata and form information.
 */
export declare function extractDataFromObservation(observation: BrowserObservation): Record<string, unknown>;
/**
 * Build a trajectory point from a browser observation and governance result.
 * Maps browser state → 21D state vector indices for detection mechanisms.
 */
export declare function buildTrajectoryPoint(observation: BrowserObservation, governance: GovernanceResult, sequence: number): TrajectoryPoint;
/**
 * Multi-agent browser crawl executor.
 *
 * Connects the CrawlCoordinator (task assignment, role switching, safety)
 * with BrowserAgent instances (page interaction, 14-layer governance).
 *
 * Usage:
 * ```typescript
 * const runner = new CrawlRunner();
 *
 * // Register agents with browser backends
 * runner.addAgent({ agentId: 'scout-1', tongue: 'KO', backend: myBackend, role: 'scout' });
 * runner.addAgent({ agentId: 'analyzer-1', tongue: 'RU', backend: myBackend2, role: 'analyzer' });
 * runner.addAgent({ agentId: 'sentinel-1', tongue: 'CA', backend: myBackend3, role: 'sentinel' });
 *
 * // Seed URLs
 * runner.addSeedUrls(['https://example.com']);
 *
 * // Run crawl steps
 * const result = await runner.step('scout-1');
 *
 * // Sentinel scan
 * const scan = runner.sentinelScan('sentinel-1');
 * ```
 */
export declare class CrawlRunner {
    /** Underlying coordinator */
    readonly coordinator: CrawlCoordinator;
    private config;
    private managedAgents;
    private stats;
    /**
     * Optional detection function. Injected to avoid hard dependency on ai_brain.
     * Signature matches runCombinedDetection from ai_brain/detection.
     */
    private detectionFn?;
    constructor(config?: CrawlRunnerConfig);
    /**
     * Set the detection function for sentinel scans.
     * This allows injecting runCombinedDetection without a hard import.
     *
     * @example
     * ```typescript
     * import { runCombinedDetection } from '../ai_brain/detection';
     * runner.setDetectionFunction(runCombinedDetection);
     * ```
     */
    setDetectionFunction(fn: (trajectory: TrajectoryPoint[], expectedTongueIndex: number, config?: Record<string, unknown>) => CombinedAssessment): void;
    /**
     * Add a crawl agent backed by a browser backend.
     */
    addAgent(agentConfig: CrawlAgentBrowserConfig): ManagedAgent;
    /**
     * Get a managed agent by ID.
     */
    getAgent(agentId: string): ManagedAgent | undefined;
    /**
     * Get all managed agents.
     */
    getAllAgents(): ManagedAgent[];
    /**
     * Remove an agent and close its browser session.
     */
    removeAgent(agentId: string): Promise<boolean>;
    /**
     * Add seed URLs to the frontier.
     */
    addSeedUrls(urls: string[]): number;
    /**
     * Check if there's work remaining.
     */
    hasWork(): boolean;
    /**
     * Initialize a browser session for an agent.
     */
    initializeAgent(agentId: string): Promise<boolean>;
    /**
     * Execute a single crawl step for an agent.
     *
     * Flow:
     * 1. Assign URL from coordinator/frontier
     * 2. Navigate via browser backend
     * 3. Evaluate governance (the backend.observe + pipeline)
     * 4. Extract role-specific data
     * 5. Report result to coordinator
     *
     * @param agentId - Agent to execute step for
     * @returns Step result or null if no work available
     */
    step(agentId: string): Promise<CrawlStepResult | null>;
    /**
     * Run multiple crawl steps across all active agents.
     * Returns results for each agent that had work.
     */
    stepAll(): Promise<CrawlStepResult[]>;
    /**
     * Run a sentinel scan using the 5-mechanism detection system.
     *
     * The sentinel agent examines the trajectory of every other agent.
     * If combined detection score exceeds the quarantine threshold,
     * the agent is quarantined.
     *
     * @param sentinelId - ID of the sentinel agent performing the scan
     * @returns Scan result with flagged and quarantined agents
     */
    sentinelScan(sentinelId: string): SentinelScanResult;
    /**
     * Request a role switch for an agent.
     * Delegates to coordinator for braid validation and consensus.
     */
    requestRoleSwitch(agentId: string, toRole: CrawlRole, reason: string): string | null;
    /**
     * Vote on a role switch request.
     */
    voteOnRoleSwitch(requestId: string, voterId: string, approve: boolean): string;
    /**
     * Get runner statistics.
     */
    getStats(): RunnerStats;
    /**
     * Get the trajectory for an agent.
     */
    getTrajectory(agentId: string): TrajectoryPoint[];
    /**
     * Get the governance log for an agent.
     */
    getGovernanceLog(agentId: string): GovernanceResult[];
    /**
     * Get all crawl results from the coordinator.
     */
    getResults(): CrawlResult[];
    /**
     * Shut down all agents and close browser sessions.
     */
    shutdown(): Promise<void>;
    /**
     * Build a governance result for a navigation action.
     * In production, this would use BrowserActionEvaluator.evaluate().
     * Here we build a compatible result from observation metadata.
     */
    private evaluateNavigation;
    /**
     * Classify domain risk from URL.
     */
    private classifyDomainRisk;
}
//# sourceMappingURL=crawl-runner.d.ts.map