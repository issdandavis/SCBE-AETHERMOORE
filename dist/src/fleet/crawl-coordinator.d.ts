/**
 * @file crawl-coordinator.ts
 * @module fleet/crawl-coordinator
 * @layer Layer 5, Layer 8, Layer 10, Layer 12, Layer 13
 * @component Multi-Agent Browser Crawl Coordinator
 * @version 1.0.0
 *
 * Orchestrates multi-agent browser crawling with:
 *
 * 1. Role-Based Crawling:
 *    SCOUT    — discovers URLs, maps site structure
 *    ANALYZER — extracts data, processes content
 *    SENTINEL — monitors safety, detects adversarial pages
 *    REPORTER — aggregates findings, produces summaries
 *
 * 2. Role Switching via Braid Governance:
 *    Agents switch roles through the AetherBraid 9-state phase diagram.
 *    Valid transitions must have Chebyshev distance ≤ 1 in the ternary grid.
 *    Role switches require BFT consensus when crossing trust boundaries.
 *
 * 3. Safety Verification:
 *    Every crawl action passes through the 14-layer SCBE pipeline.
 *    Sentinel agents monitor the swarm for anomalous behavior.
 *    Immune response system quarantines compromised agents.
 *
 * 4. Communication:
 *    CrawlMessageBus provides inter-agent pub/sub messaging.
 *    CrawlFrontier manages the shared URL queue.
 *
 * Integration points:
 *   - fleet/FleetManager → agent registration & task dispatch
 *   - browser/BrowserAgent → page interaction & governance
 *   - ai_brain/AetherBraid → role switching governance
 *   - ai_brain/BFTConsensus → consensus for critical decisions
 *   - ai_brain/ImmuneResponseSystem → anomaly quarantine
 */
import { CrawlMessageBus } from './crawl-message-bus.js';
import { CrawlFrontier, type FrontierEntry, type FrontierConfig } from './crawl-frontier.js';
/** Crawl agent roles — each maps to a braid governance state */
export type CrawlRole = 'scout' | 'analyzer' | 'sentinel' | 'reporter';
/** Braid ternary mapping for crawl roles:
 *  SCOUT    → (+1, 0)  FORWARD_THRUST   — exploring outward
 *  ANALYZER → (+1, +1) RESONANT_LOCK    — deep engagement
 *  SENTINEL → (0, +1)  PERPENDICULAR_POS — orthogonal monitor
 *  REPORTER → (0, 0)   ZERO_GRAVITY     — neutral aggregator
 */
export declare const ROLE_BRAID_MAP: Record<CrawlRole, {
    primary: -1 | 0 | 1;
    mirror: -1 | 0 | 1;
}>;
/** Valid role transitions (Chebyshev distance ≤ 1 in braid grid) */
export declare const VALID_ROLE_TRANSITIONS: Record<CrawlRole, CrawlRole[]>;
/** Crawl agent descriptor */
export interface CrawlAgent {
    /** Unique agent ID */
    readonly id: string;
    /** Current role */
    role: CrawlRole;
    /** Current status */
    status: 'idle' | 'crawling' | 'analyzing' | 'reporting' | 'quarantined';
    /** URLs completed */
    urlsCompleted: number;
    /** URLs failed */
    urlsFailed: number;
    /** Safety score (higher = more trusted) */
    safetyScore: number;
    /** Role switch count */
    roleSwitches: number;
    /** Current URL being processed */
    currentUrl?: string;
    /** Timestamp of last activity */
    lastActivity: number;
    /** Timestamp of registration */
    readonly registeredAt: number;
}
/** Role switch request */
export interface RoleSwitchRequest {
    readonly requestId: string;
    readonly agentId: string;
    readonly fromRole: CrawlRole;
    readonly toRole: CrawlRole;
    readonly reason: string;
    readonly timestamp: number;
    status: 'pending' | 'approved' | 'denied';
    votes: Array<{
        voterId: string;
        approve: boolean;
    }>;
}
/** Crawl result from an agent */
export interface CrawlResult {
    readonly url: string;
    readonly agentId: string;
    readonly role: CrawlRole;
    readonly discoveredUrls: string[];
    readonly extractedData: Record<string, unknown>;
    readonly safetyAssessment: {
        safe: boolean;
        riskScore: number;
        flags: string[];
    };
    readonly timestamp: number;
    readonly durationMs: number;
}
/** Coordinator configuration */
export interface CrawlCoordinatorConfig {
    /** Maximum concurrent crawling agents */
    maxConcurrent: number;
    /** Minimum safety score to continue crawling */
    minSafetyScore: number;
    /** BFT consensus required for role switches */
    requireConsensusForRoleSwitch: boolean;
    /** Minimum votes needed for role switch approval */
    roleSwitchQuorum: number;
    /** Safety score penalty for failed crawls */
    failurePenalty: number;
    /** Safety score recovery per successful crawl */
    successRecovery: number;
    /** Frontier configuration */
    frontier?: Partial<FrontierConfig>;
}
/** Default coordinator config */
export declare const DEFAULT_CRAWL_CONFIG: CrawlCoordinatorConfig;
/** Coordinator statistics */
export interface CrawlStats {
    totalAgents: number;
    activeAgents: number;
    quarantinedAgents: number;
    urlsCompleted: number;
    urlsFailed: number;
    urlsQueued: number;
    roleSwitchesApproved: number;
    roleSwitchesDenied: number;
    messagesExchanged: number;
    averageSafetyScore: number;
}
/**
 * Multi-agent browser crawl coordinator.
 *
 * Manages a pool of browser agents with role-based specialization,
 * braid-governed role switching, and continuous safety verification.
 *
 * Usage:
 * ```typescript
 * const coordinator = new CrawlCoordinator();
 *
 * // Register agents
 * coordinator.registerAgent('agent-1', 'scout');
 * coordinator.registerAgent('agent-2', 'analyzer');
 * coordinator.registerAgent('agent-3', 'sentinel');
 *
 * // Add seed URLs
 * coordinator.addSeedUrls(['https://example.com']);
 *
 * // Run crawl loop
 * while (coordinator.hasWork()) {
 *   const assignment = coordinator.assignNext('agent-1');
 *   if (assignment) {
 *     // ... crawl assignment.url ...
 *     coordinator.reportResult({ url: assignment.url, ... });
 *   }
 * }
 * ```
 */
export declare class CrawlCoordinator {
    readonly bus: CrawlMessageBus;
    readonly frontier: CrawlFrontier;
    private config;
    private agents;
    private roleSwitchRequests;
    private results;
    private roleSwitchesApproved;
    private roleSwitchesDenied;
    constructor(config?: Partial<CrawlCoordinatorConfig>);
    /**
     * Register a crawl agent with an initial role.
     */
    registerAgent(agentId: string, role: CrawlRole): CrawlAgent;
    /**
     * Get an agent by ID.
     */
    getAgent(agentId: string): CrawlAgent | undefined;
    /**
     * Get all agents.
     */
    getAllAgents(): CrawlAgent[];
    /**
     * Get agents by role.
     */
    getAgentsByRole(role: CrawlRole): CrawlAgent[];
    /**
     * Remove an agent.
     */
    removeAgent(agentId: string): boolean;
    /**
     * Add seed URLs to the frontier.
     */
    addSeedUrls(urls: string[]): number;
    /**
     * Check if there's work remaining.
     */
    hasWork(): boolean;
    /**
     * Assign the next URL to an agent based on their role.
     *
     * - Scouts get the highest-priority queued URL
     * - Analyzers get URLs that scouts have already visited (completed)
     * - Sentinels monitor all crawling agents (no URL assignment)
     * - Reporters aggregate results (no URL assignment)
     *
     * @param agentId - Agent requesting work
     * @returns FrontierEntry or null if no work available
     */
    assignNext(agentId: string): FrontierEntry | null;
    /**
     * Report a crawl result.
     */
    reportResult(result: CrawlResult): number;
    /**
     * Report a crawl failure.
     */
    reportFailure(url: string, agentId: string, error: string): void;
    /**
     * Request a role switch. Must be a valid braid transition.
     *
     * @param agentId - Agent requesting the switch
     * @param toRole - Target role
     * @param reason - Reason for the switch
     * @returns Request ID or null if invalid transition
     */
    requestRoleSwitch(agentId: string, toRole: CrawlRole, reason: string): string | null;
    /**
     * Vote on a role switch request.
     *
     * @param requestId - Request to vote on
     * @param voterId - Voting agent
     * @param approve - true to approve, false to deny
     * @returns 'approved' | 'denied' | 'pending' | 'not_found'
     */
    voteOnRoleSwitch(requestId: string, voterId: string, approve: boolean): 'approved' | 'denied' | 'pending' | 'not_found';
    /**
     * Get a role switch request by ID.
     */
    getRoleSwitchRequest(requestId: string): RoleSwitchRequest | undefined;
    /**
     * Quarantine an agent (sentinel action).
     */
    quarantineAgent(agentId: string, reason: string): boolean;
    /**
     * Release an agent from quarantine (requires safety score recovery).
     */
    releaseFromQuarantine(agentId: string): boolean;
    /**
     * Manually adjust an agent's safety score (for sentinel use).
     */
    adjustSafetyScore(agentId: string, delta: number): number;
    /**
     * Get all crawl results.
     */
    getResults(): CrawlResult[];
    /**
     * Get results by agent.
     */
    getResultsByAgent(agentId: string): CrawlResult[];
    /**
     * Get coordinator statistics.
     */
    getStats(): CrawlStats;
    private applyRoleSwitch;
}
//# sourceMappingURL=crawl-coordinator.d.ts.map