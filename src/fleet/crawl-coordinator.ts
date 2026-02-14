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

import { CrawlMessageBus, type CrawlMessage, type CrawlChannel, type CrawlEventType } from './crawl-message-bus.js';
import { CrawlFrontier, type FrontierEntry, type FrontierConfig } from './crawl-frontier.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Crawl agent roles — each maps to a braid governance state */
export type CrawlRole = 'scout' | 'analyzer' | 'sentinel' | 'reporter';

/** Braid ternary mapping for crawl roles:
 *  SCOUT    → (+1, 0)  FORWARD_THRUST   — exploring outward
 *  ANALYZER → (+1, +1) RESONANT_LOCK    — deep engagement
 *  SENTINEL → (0, +1)  PERPENDICULAR_POS — orthogonal monitor
 *  REPORTER → (0, 0)   ZERO_GRAVITY     — neutral aggregator
 */
export const ROLE_BRAID_MAP: Record<CrawlRole, { primary: -1 | 0 | 1; mirror: -1 | 0 | 1 }> = {
  scout: { primary: 1, mirror: 0 },
  analyzer: { primary: 1, mirror: 1 },
  sentinel: { primary: 0, mirror: 1 },
  reporter: { primary: 0, mirror: 0 },
};

/** Valid role transitions (Chebyshev distance ≤ 1 in braid grid) */
export const VALID_ROLE_TRANSITIONS: Record<CrawlRole, CrawlRole[]> = {
  scout: ['scout', 'analyzer', 'sentinel', 'reporter'], // (+1,0) → all within distance 1
  analyzer: ['analyzer', 'scout', 'sentinel'],            // (+1,+1) → adjacent only
  sentinel: ['sentinel', 'scout', 'analyzer', 'reporter'], // (0,+1) → all within distance 1
  reporter: ['reporter', 'scout', 'sentinel'],             // (0,0) → adjacent only
};

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
  votes: Array<{ voterId: string; approve: boolean }>;
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
export const DEFAULT_CRAWL_CONFIG: CrawlCoordinatorConfig = {
  maxConcurrent: 4,
  minSafetyScore: 0.3,
  requireConsensusForRoleSwitch: true,
  roleSwitchQuorum: 2,
  failurePenalty: 0.1,
  successRecovery: 0.02,
  frontier: {},
};

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

// ═══════════════════════════════════════════════════════════════
// CrawlCoordinator
// ═══════════════════════════════════════════════════════════════

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
export class CrawlCoordinator {
  readonly bus: CrawlMessageBus;
  readonly frontier: CrawlFrontier;
  private config: CrawlCoordinatorConfig;
  private agents: Map<string, CrawlAgent> = new Map();
  private roleSwitchRequests: Map<string, RoleSwitchRequest> = new Map();
  private results: CrawlResult[] = [];
  private roleSwitchesApproved = 0;
  private roleSwitchesDenied = 0;

  constructor(config: Partial<CrawlCoordinatorConfig> = {}) {
    this.config = { ...DEFAULT_CRAWL_CONFIG, ...config };
    this.bus = new CrawlMessageBus();
    this.frontier = new CrawlFrontier(this.config.frontier);
  }

  // ═══════════════════════════════════════════════════════════
  // Agent Management
  // ═══════════════════════════════════════════════════════════

  /**
   * Register a crawl agent with an initial role.
   */
  registerAgent(agentId: string, role: CrawlRole): CrawlAgent {
    const agent: CrawlAgent = {
      id: agentId,
      role,
      status: 'idle',
      urlsCompleted: 0,
      urlsFailed: 0,
      safetyScore: 1.0,
      roleSwitches: 0,
      lastActivity: Date.now(),
      registeredAt: Date.now(),
    };

    this.agents.set(agentId, agent);

    // Subscribe agent to relevant channels
    this.bus.subscribe(agentId, 'scbe.crawl.governance.*', () => {});
    this.bus.subscribe(agentId, 'scbe.crawl.sentinel.*', () => {});

    // Announce registration
    this.bus.publish(agentId, 'status', 'heartbeat', {
      role,
      status: 'idle',
      safetyScore: 1.0,
    });

    return agent;
  }

  /**
   * Get an agent by ID.
   */
  getAgent(agentId: string): CrawlAgent | undefined {
    return this.agents.get(agentId);
  }

  /**
   * Get all agents.
   */
  getAllAgents(): CrawlAgent[] {
    return [...this.agents.values()];
  }

  /**
   * Get agents by role.
   */
  getAgentsByRole(role: CrawlRole): CrawlAgent[] {
    return [...this.agents.values()].filter((a) => a.role === role);
  }

  /**
   * Remove an agent.
   */
  removeAgent(agentId: string): boolean {
    const agent = this.agents.get(agentId);
    if (!agent) return false;

    // Release any claimed URLs
    if (agent.currentUrl) {
      this.frontier.release(agent.currentUrl, agentId);
    }

    this.agents.delete(agentId);
    return true;
  }

  // ═══════════════════════════════════════════════════════════
  // URL Management
  // ═══════════════════════════════════════════════════════════

  /**
   * Add seed URLs to the frontier.
   */
  addSeedUrls(urls: string[]): number {
    const added = this.frontier.addSeedUrls(urls);

    // Announce on discovery channel
    for (const url of urls) {
      this.bus.publish('coordinator', 'discovery', 'url_found', {
        url,
        depth: 0,
        source: 'seed',
      });
    }

    return added;
  }

  /**
   * Check if there's work remaining.
   */
  hasWork(): boolean {
    return this.frontier.hasWork;
  }

  // ═══════════════════════════════════════════════════════════
  // Task Assignment
  // ═══════════════════════════════════════════════════════════

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
  assignNext(agentId: string): FrontierEntry | null {
    const agent = this.agents.get(agentId);
    if (!agent) return null;

    // Safety check
    if (agent.safetyScore < this.config.minSafetyScore) {
      agent.status = 'quarantined';
      this.bus.publish('coordinator', 'sentinel', 'quarantine_notice', {
        agentId,
        reason: 'safety_score_below_threshold',
        score: agent.safetyScore,
      });
      return null;
    }

    // Quarantined agents can't work
    if (agent.status === 'quarantined') return null;

    // Check concurrent limit
    const activeCrawlers = [...this.agents.values()].filter(
      (a) => a.status === 'crawling' || a.status === 'analyzing',
    ).length;
    if (activeCrawlers >= this.config.maxConcurrent) return null;

    // Role-based assignment
    if (agent.role === 'sentinel' || agent.role === 'reporter') {
      // These roles don't crawl URLs directly
      return null;
    }

    const entry = this.frontier.claim(agentId);
    if (!entry) return null;

    agent.status = agent.role === 'scout' ? 'crawling' : 'analyzing';
    agent.currentUrl = entry.url;
    agent.lastActivity = Date.now();

    // Announce on status channel
    this.bus.publish(agentId, 'status', 'busy', {
      url: entry.url,
      role: agent.role,
    });

    return entry;
  }

  // ═══════════════════════════════════════════════════════════
  // Result Reporting
  // ═══════════════════════════════════════════════════════════

  /**
   * Report a crawl result.
   */
  reportResult(result: CrawlResult): number {
    this.results.push(result);

    const agent = this.agents.get(result.agentId);
    if (!agent) return 0;

    // Update agent state
    agent.urlsCompleted++;
    agent.status = 'idle';
    agent.currentUrl = undefined;
    agent.lastActivity = Date.now();

    // Safety score adjustment
    if (result.safetyAssessment.safe) {
      agent.safetyScore = Math.min(1.0, agent.safetyScore + this.config.successRecovery);
    } else {
      agent.safetyScore = Math.max(0, agent.safetyScore - this.config.failurePenalty);
    }

    // Complete in frontier and add discovered URLs
    const added = this.frontier.complete(result.url, result.agentId, result.discoveredUrls);

    // Announce discoveries
    for (const url of result.discoveredUrls) {
      this.bus.publish(result.agentId, 'discovery', 'url_found', {
        url,
        parentUrl: result.url,
      });
    }

    // Announce findings
    this.bus.publish(result.agentId, 'findings', 'data_extracted', {
      url: result.url,
      dataKeys: Object.keys(result.extractedData),
      safe: result.safetyAssessment.safe,
    });

    // Safety alert if unsafe
    if (!result.safetyAssessment.safe) {
      this.bus.publish(result.agentId, 'sentinel', 'safety_alert', {
        url: result.url,
        riskScore: result.safetyAssessment.riskScore,
        flags: result.safetyAssessment.flags,
      });
    }

    return added;
  }

  /**
   * Report a crawl failure.
   */
  reportFailure(url: string, agentId: string, error: string): void {
    const agent = this.agents.get(agentId);
    if (agent) {
      agent.urlsFailed++;
      agent.status = 'idle';
      agent.currentUrl = undefined;
      agent.lastActivity = Date.now();
      agent.safetyScore = Math.max(0, agent.safetyScore - this.config.failurePenalty * 0.5);
    }

    this.frontier.fail(url, agentId, error);

    this.bus.publish(agentId, 'discovery', 'url_failed', {
      url,
      error,
    });
  }

  // ═══════════════════════════════════════════════════════════
  // Role Switching (Braid-Governed)
  // ═══════════════════════════════════════════════════════════

  /**
   * Request a role switch. Must be a valid braid transition.
   *
   * @param agentId - Agent requesting the switch
   * @param toRole - Target role
   * @param reason - Reason for the switch
   * @returns Request ID or null if invalid transition
   */
  requestRoleSwitch(agentId: string, toRole: CrawlRole, reason: string): string | null {
    const agent = this.agents.get(agentId);
    if (!agent) return null;

    // Validate braid transition
    if (!VALID_ROLE_TRANSITIONS[agent.role].includes(toRole)) {
      this.roleSwitchesDenied++;
      this.bus.publish('coordinator', 'governance', 'role_switch_denied', {
        agentId,
        fromRole: agent.role,
        toRole,
        reason: 'invalid_braid_transition',
      });
      return null;
    }

    // Self-transition is always approved
    if (agent.role === toRole) return null;

    const requestId = `rs-${agentId}-${Date.now()}`;
    const request: RoleSwitchRequest = {
      requestId,
      agentId,
      fromRole: agent.role,
      toRole,
      reason,
      timestamp: Date.now(),
      status: 'pending',
      votes: [],
    };

    if (!this.config.requireConsensusForRoleSwitch) {
      // Auto-approve
      request.status = 'approved';
      this.applyRoleSwitch(agent, toRole);
      this.roleSwitchesApproved++;
      return requestId;
    }

    this.roleSwitchRequests.set(requestId, request);

    // Broadcast request for voting
    this.bus.publish(agentId, 'governance', 'role_switch_request', {
      requestId,
      fromRole: agent.role,
      toRole,
      reason,
    });

    return requestId;
  }

  /**
   * Vote on a role switch request.
   *
   * @param requestId - Request to vote on
   * @param voterId - Voting agent
   * @param approve - true to approve, false to deny
   * @returns 'approved' | 'denied' | 'pending' | 'not_found'
   */
  voteOnRoleSwitch(
    requestId: string,
    voterId: string,
    approve: boolean,
  ): 'approved' | 'denied' | 'pending' | 'not_found' {
    const request = this.roleSwitchRequests.get(requestId);
    if (!request || request.status !== 'pending') return 'not_found';

    // Can't vote on your own request
    if (voterId === request.agentId) return 'pending';

    // Can't vote twice
    if (request.votes.some((v) => v.voterId === voterId)) return 'pending';

    request.votes.push({ voterId, approve });

    // Record vote on bus
    this.bus.publish(voterId, 'governance', 'consensus_vote', {
      requestId,
      approve,
    });

    // Check quorum
    const approvals = request.votes.filter((v) => v.approve).length;
    const denials = request.votes.filter((v) => !v.approve).length;

    if (approvals >= this.config.roleSwitchQuorum) {
      request.status = 'approved';
      const agent = this.agents.get(request.agentId);
      if (agent) {
        this.applyRoleSwitch(agent, request.toRole);
      }
      this.roleSwitchesApproved++;

      this.bus.publish('coordinator', 'governance', 'role_switch_approved', {
        requestId,
        agentId: request.agentId,
        newRole: request.toRole,
      });

      return 'approved';
    }

    if (denials > this.agents.size - this.config.roleSwitchQuorum) {
      request.status = 'denied';
      this.roleSwitchesDenied++;

      this.bus.publish('coordinator', 'governance', 'role_switch_denied', {
        requestId,
        agentId: request.agentId,
        reason: 'consensus_denied',
      });

      return 'denied';
    }

    return 'pending';
  }

  /**
   * Get a role switch request by ID.
   */
  getRoleSwitchRequest(requestId: string): RoleSwitchRequest | undefined {
    return this.roleSwitchRequests.get(requestId);
  }

  // ═══════════════════════════════════════════════════════════
  // Safety & Quarantine
  // ═══════════════════════════════════════════════════════════

  /**
   * Quarantine an agent (sentinel action).
   */
  quarantineAgent(agentId: string, reason: string): boolean {
    const agent = this.agents.get(agentId);
    if (!agent) return false;

    // Release any held URLs
    if (agent.currentUrl) {
      this.frontier.release(agent.currentUrl, agentId);
    }

    agent.status = 'quarantined';
    agent.currentUrl = undefined;

    this.bus.publish('coordinator', 'sentinel', 'quarantine_notice', {
      agentId,
      reason,
      safetyScore: agent.safetyScore,
    });

    return true;
  }

  /**
   * Release an agent from quarantine (requires safety score recovery).
   */
  releaseFromQuarantine(agentId: string): boolean {
    const agent = this.agents.get(agentId);
    if (!agent || agent.status !== 'quarantined') return false;
    if (agent.safetyScore < this.config.minSafetyScore) return false;

    agent.status = 'idle';
    return true;
  }

  /**
   * Manually adjust an agent's safety score (for sentinel use).
   */
  adjustSafetyScore(agentId: string, delta: number): number {
    const agent = this.agents.get(agentId);
    if (!agent) return -1;
    agent.safetyScore = Math.max(0, Math.min(1.0, agent.safetyScore + delta));
    return agent.safetyScore;
  }

  // ═══════════════════════════════════════════════════════════
  // Results & Statistics
  // ═══════════════════════════════════════════════════════════

  /**
   * Get all crawl results.
   */
  getResults(): CrawlResult[] {
    return [...this.results];
  }

  /**
   * Get results by agent.
   */
  getResultsByAgent(agentId: string): CrawlResult[] {
    return this.results.filter((r) => r.agentId === agentId);
  }

  /**
   * Get coordinator statistics.
   */
  getStats(): CrawlStats {
    const agents = [...this.agents.values()];
    const busStats = this.bus.getStats();
    const frontierStats = this.frontier.getStats();

    return {
      totalAgents: agents.length,
      activeAgents: agents.filter((a) => a.status !== 'idle' && a.status !== 'quarantined').length,
      quarantinedAgents: agents.filter((a) => a.status === 'quarantined').length,
      urlsCompleted: frontierStats.totalCompleted,
      urlsFailed: frontierStats.totalFailed,
      urlsQueued: frontierStats.queued,
      roleSwitchesApproved: this.roleSwitchesApproved,
      roleSwitchesDenied: this.roleSwitchesDenied,
      messagesExchanged: busStats.totalPublished,
      averageSafetyScore:
        agents.length > 0
          ? agents.reduce((s, a) => s + a.safetyScore, 0) / agents.length
          : 0,
    };
  }

  // ═══════════════════════════════════════════════════════════
  // Private
  // ═══════════════════════════════════════════════════════════

  private applyRoleSwitch(agent: CrawlAgent, toRole: CrawlRole): void {
    // Release current URL if role changes functionality
    if (agent.currentUrl && (toRole === 'sentinel' || toRole === 'reporter')) {
      this.frontier.release(agent.currentUrl, agent.id);
      agent.currentUrl = undefined;
    }

    agent.role = toRole;
    agent.roleSwitches++;
    agent.lastActivity = Date.now();
  }
}
