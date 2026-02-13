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
import type { BrowserBackend, BrowserAgentConfig } from '../browser/agent.js';
import type { BrowserObservation, GovernanceResult } from '../browser/types.js';
import type { TrajectoryPoint, CombinedAssessment } from '../ai_brain/types.js';
import { CrawlCoordinator, type CrawlRole, type CrawlResult, type CrawlCoordinatorConfig } from './crawl-coordinator.js';
import type { FrontierEntry } from './crawl-frontier.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

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
export const DEFAULT_RUNNER_CONFIG: Required<CrawlRunnerConfig> = {
  coordinator: {},
  detectionThreshold: 0.7,
  minTrajectoryLength: 5,
  maxTrajectoryLength: 100,
  quarantineThreshold: 0.85,
};

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

// ═══════════════════════════════════════════════════════════════
// Link Extraction
// ═══════════════════════════════════════════════════════════════

/**
 * Extract links from a page observation.
 * Scans interactive elements for anchor tags with href in dataAttributes.
 * Filters to http(s) URLs and deduplicates.
 */
export function extractLinksFromObservation(observation: BrowserObservation): string[] {
  const links = new Set<string>();

  // Extract from interactive elements (anchors store href in dataAttributes)
  for (const element of observation.page.interactiveElements ?? []) {
    if (element.tagName === 'a') {
      const href = element.dataAttributes?.['href'] ?? element.value;
      if (href && (href.startsWith('http://') || href.startsWith('https://'))) {
        links.add(href);
      }
    }
  }

  return [...links];
}

/**
 * Extract structured data from a page observation.
 * Returns page metadata and form information.
 */
export function extractDataFromObservation(
  observation: BrowserObservation,
): Record<string, unknown> {
  const data: Record<string, unknown> = {
    url: observation.page.url,
    title: observation.page.title,
    loadTime: observation.page.loadTime,
    interactiveElementCount: observation.page.interactiveElements?.length ?? 0,
    formCount: observation.page.forms?.length ?? 0,
    hasDialogs: (observation.page.dialogs?.length ?? 0) > 0,
  };

  // Extract form metadata (not values — security)
  if (observation.page.forms && observation.page.forms.length > 0) {
    data.forms = observation.page.forms.map((form) => ({
      identifier: form.identifier,
      action: form.action,
      method: form.method,
      fieldCount: form.fields?.length ?? 0,
      hasSensitiveFields: form.hasSensitiveFields ?? false,
    }));
  }

  return data;
}

/**
 * Build a trajectory point from a browser observation and governance result.
 * Maps browser state → 21D state vector indices for detection mechanisms.
 */
export function buildTrajectoryPoint(
  observation: BrowserObservation,
  governance: GovernanceResult,
  sequence: number,
): TrajectoryPoint {
  // Map browser state to a simplified 21D-compatible state vector
  // Using governance risk factors as proxy dimensions
  const state = new Array(21).fill(0);

  // SCBE Context block [0-5]
  state[0] = governance.riskFactors.actionRisk;     // action risk
  state[1] = governance.riskFactors.domainRisk;     // domain risk
  state[2] = governance.riskFactors.sessionRisk;    // session risk
  state[3] = governance.riskScore;                  // behavior score (STATE_DIM.BEHAVIOR_SCORE)
  state[4] = governance.riskFactors.temporalRisk;   // temporal risk
  state[5] = governance.confidence;                 // intent alignment (STATE_DIM.INTENT_ALIGNMENT)

  // Navigation block [6-11] — from observation
  state[6] = observation.page.scroll?.x ?? 0;
  state[7] = observation.page.scroll?.y ?? 0;
  state[8] = (observation.page.interactiveElements?.length ?? 0) / 100;
  state[9] = observation.page.loadTime ? observation.page.loadTime / 10000 : 0;
  state[10] = observation.page.readyState === 'complete' ? 1 : 0;
  state[11] = observation.sequence / 100;

  // Cognitive block [12-14]
  state[12] = governance.riskFactors.historicalRisk;
  state[13] = governance.riskScore;
  state[14] = governance.confidence;

  // Semantic block [15-17]
  state[15] = 0; // phase — would come from evaluator internals
  // STATE_DIM.PHASE_ANGLE = 16
  state[16] = (observation.page.url?.length ?? 0) % (2 * Math.PI) / (2 * Math.PI);
  // STATE_DIM.TONGUE_WEIGHT = 17
  state[17] = governance.riskScore;

  // Swarm block [18-20]
  state[18] = governance.riskFactors.actionRisk;
  state[19] = 1.0; // participation ratio placeholder
  state[20] = 0;   // spectral entropy placeholder

  // Compute embedded representation (use state directly since no full pipeline)
  const embedded = state.slice(0, 6);

  // Compute hyperbolic distance proxy from risk score
  const distance = governance.riskScore * 5; // Scale to meaningful hyperbolic range

  return {
    step: sequence,
    state,
    embedded,
    distance,
    curvature: 0, // Computed by detection mechanisms over trajectory
    timestamp: observation.timestamp,
  };
}

// ═══════════════════════════════════════════════════════════════
// CrawlRunner
// ═══════════════════════════════════════════════════════════════

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
export class CrawlRunner {
  /** Underlying coordinator */
  readonly coordinator: CrawlCoordinator;
  private config: Required<CrawlRunnerConfig>;
  private managedAgents: Map<string, ManagedAgent> = new Map();
  private stats: RunnerStats = {
    totalSteps: 0,
    successfulSteps: 0,
    failedSteps: 0,
    governanceDenied: 0,
    sentinelScans: 0,
    sentinelQuarantines: 0,
    totalDiscoveredUrls: 0,
    coordinatorStats: {
      totalAgents: 0,
      activeAgents: 0,
      quarantinedAgents: 0,
      urlsCompleted: 0,
      urlsFailed: 0,
      urlsQueued: 0,
      roleSwitchesApproved: 0,
      roleSwitchesDenied: 0,
      messagesExchanged: 0,
      averageSafetyScore: 0,
    },
  };

  /**
   * Optional detection function. Injected to avoid hard dependency on ai_brain.
   * Signature matches runCombinedDetection from ai_brain/detection.
   */
  private detectionFn?: (
    trajectory: TrajectoryPoint[],
    expectedTongueIndex: number,
    config?: Record<string, unknown>,
  ) => CombinedAssessment;

  constructor(config: CrawlRunnerConfig = {}) {
    this.config = { ...DEFAULT_RUNNER_CONFIG, ...config };
    this.coordinator = new CrawlCoordinator(this.config.coordinator);
  }

  // ═══════════════════════════════════════════════════════════
  // Detection Injection
  // ═══════════════════════════════════════════════════════════

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
  setDetectionFunction(
    fn: (
      trajectory: TrajectoryPoint[],
      expectedTongueIndex: number,
      config?: Record<string, unknown>,
    ) => CombinedAssessment,
  ): void {
    this.detectionFn = fn;
  }

  // ═══════════════════════════════════════════════════════════
  // Agent Management
  // ═══════════════════════════════════════════════════════════

  /**
   * Add a crawl agent backed by a browser backend.
   */
  addAgent(agentConfig: CrawlAgentBrowserConfig): ManagedAgent {
    // Register with coordinator
    this.coordinator.registerAgent(agentConfig.agentId, agentConfig.role);

    const managed: ManagedAgent = {
      agentId: agentConfig.agentId,
      tongue: agentConfig.tongue,
      backend: agentConfig.backend,
      sessionActive: false,
      trajectory: [],
      governanceLog: [],
      urlsCrawled: [],
    };

    this.managedAgents.set(agentConfig.agentId, managed);
    return managed;
  }

  /**
   * Get a managed agent by ID.
   */
  getAgent(agentId: string): ManagedAgent | undefined {
    return this.managedAgents.get(agentId);
  }

  /**
   * Get all managed agents.
   */
  getAllAgents(): ManagedAgent[] {
    return [...this.managedAgents.values()];
  }

  /**
   * Remove an agent and close its browser session.
   */
  async removeAgent(agentId: string): Promise<boolean> {
    const managed = this.managedAgents.get(agentId);
    if (!managed) return false;

    if (managed.sessionActive) {
      try {
        await managed.backend.close();
      } catch {
        // Ignore close errors
      }
      managed.sessionActive = false;
    }

    this.coordinator.removeAgent(agentId);
    this.managedAgents.delete(agentId);
    return true;
  }

  // ═══════════════════════════════════════════════════════════
  // URL Management
  // ═══════════════════════════════════════════════════════════

  /**
   * Add seed URLs to the frontier.
   */
  addSeedUrls(urls: string[]): number {
    return this.coordinator.addSeedUrls(urls);
  }

  /**
   * Check if there's work remaining.
   */
  hasWork(): boolean {
    return this.coordinator.hasWork();
  }

  // ═══════════════════════════════════════════════════════════
  // Crawl Execution
  // ═══════════════════════════════════════════════════════════

  /**
   * Initialize a browser session for an agent.
   */
  async initializeAgent(agentId: string): Promise<boolean> {
    const managed = this.managedAgents.get(agentId);
    if (!managed) return false;
    if (managed.sessionActive) return true;

    try {
      await managed.backend.initialize({
        sessionId: `crawl-${agentId}-${Date.now()}`,
        agentId,
        tongue: managed.tongue,
        browserType: 'chromium',
        headless: true,
        viewport: { width: 1280, height: 720 },
        timeout: 30000,
      });
      managed.sessionActive = true;
      return true;
    } catch {
      return false;
    }
  }

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
  async step(agentId: string): Promise<CrawlStepResult | null> {
    const managed = this.managedAgents.get(agentId);
    if (!managed) return null;

    const crawlAgent = this.coordinator.getAgent(agentId);
    if (!crawlAgent) return null;

    // Sentinels and reporters don't crawl URLs
    if (crawlAgent.role === 'sentinel' || crawlAgent.role === 'reporter') {
      return null;
    }

    // Initialize session if needed
    if (!managed.sessionActive) {
      const ok = await this.initializeAgent(agentId);
      if (!ok) {
        return {
          agentId,
          url: '',
          success: false,
          governance: null,
          discoveredUrls: [],
          extractedData: {},
          safetyAssessment: { safe: false, riskScore: 1, flags: ['session_init_failed'] },
          error: 'Failed to initialize browser session',
          durationMs: 0,
        };
      }
    }

    // Get assignment from coordinator
    const assignment = this.coordinator.assignNext(agentId);
    if (!assignment) return null;

    const startTime = Date.now();
    this.stats.totalSteps++;

    try {
      // Navigate to the URL
      await managed.backend.navigate(assignment.url, { timeout: 30000 });

      // Get page observation
      const pageObs = await managed.backend.observe();
      const observation: BrowserObservation = {
        sessionId: `crawl-${agentId}`,
        sequence: managed.urlsCrawled.length,
        page: pageObs,
        timestamp: Date.now(),
      };
      managed.lastObservation = observation;

      // Build governance result from observation
      // In production this would use BrowserActionEvaluator; here we derive
      // a simplified governance result from the observation + action sensitivity
      const governance = this.evaluateNavigation(observation, managed);

      // Record governance
      managed.governanceLog.push(governance);

      // Check governance decision
      if (governance.decision === 'DENY') {
        this.stats.failedSteps++;
        this.stats.governanceDenied++;
        this.coordinator.reportFailure(assignment.url, agentId, `Governance denied: ${governance.explanation}`);
        return {
          agentId,
          url: assignment.url,
          success: false,
          governance,
          discoveredUrls: [],
          extractedData: {},
          safetyAssessment: {
            safe: false,
            riskScore: governance.riskScore,
            flags: ['governance_denied'],
          },
          error: governance.explanation,
          durationMs: Date.now() - startTime,
        };
      }

      // Build trajectory point for detection
      const trajectoryPoint = buildTrajectoryPoint(observation, governance, managed.urlsCrawled.length);
      managed.trajectory.push(trajectoryPoint);

      // Trim trajectory if too long
      if (managed.trajectory.length > this.config.maxTrajectoryLength) {
        managed.trajectory = managed.trajectory.slice(-this.config.maxTrajectoryLength);
      }

      // Role-specific data extraction
      let discoveredUrls: string[] = [];
      let extractedData: Record<string, unknown> = {};

      if (crawlAgent.role === 'scout') {
        discoveredUrls = extractLinksFromObservation(observation);
      } else if (crawlAgent.role === 'analyzer') {
        extractedData = extractDataFromObservation(observation);
      }

      // Build safety assessment
      const safe = governance.decision === 'ALLOW';
      const flags: string[] = [];
      if (governance.decision === 'QUARANTINE') flags.push('quarantined');
      if (governance.decision === 'ESCALATE') flags.push('escalated');
      if (governance.requiresRoundtable) flags.push('roundtable_required');

      // Report result to coordinator
      const crawlResult: CrawlResult = {
        url: assignment.url,
        agentId,
        role: crawlAgent.role,
        discoveredUrls,
        extractedData,
        safetyAssessment: {
          safe,
          riskScore: governance.riskScore,
          flags,
        },
        timestamp: Date.now(),
        durationMs: Date.now() - startTime,
      };
      const added = this.coordinator.reportResult(crawlResult);

      managed.urlsCrawled.push(assignment.url);
      this.stats.successfulSteps++;
      this.stats.totalDiscoveredUrls += discoveredUrls.length;

      // Publish crawl event on message bus
      this.coordinator.bus.publish(agentId, 'status', 'progress', {
        url: assignment.url,
        governance: governance.decision,
        discoveredCount: discoveredUrls.length,
        dataKeys: Object.keys(extractedData),
      });

      return {
        agentId,
        url: assignment.url,
        success: true,
        governance,
        discoveredUrls,
        extractedData,
        safetyAssessment: { safe, riskScore: governance.riskScore, flags },
        durationMs: Date.now() - startTime,
      };
    } catch (err) {
      this.stats.failedSteps++;
      const error = err instanceof Error ? err.message : 'Unknown crawl error';
      this.coordinator.reportFailure(assignment.url, agentId, error);

      return {
        agentId,
        url: assignment.url,
        success: false,
        governance: null,
        discoveredUrls: [],
        extractedData: {},
        safetyAssessment: { safe: false, riskScore: 1, flags: ['execution_error'] },
        error,
        durationMs: Date.now() - startTime,
      };
    }
  }

  /**
   * Run multiple crawl steps across all active agents.
   * Returns results for each agent that had work.
   */
  async stepAll(): Promise<CrawlStepResult[]> {
    const results: CrawlStepResult[] = [];

    for (const managed of this.managedAgents.values()) {
      const crawlAgent = this.coordinator.getAgent(managed.agentId);
      if (!crawlAgent) continue;
      if (crawlAgent.status === 'quarantined') continue;
      if (crawlAgent.role === 'sentinel' || crawlAgent.role === 'reporter') continue;

      const result = await this.step(managed.agentId);
      if (result) results.push(result);
    }

    return results;
  }

  // ═══════════════════════════════════════════════════════════
  // Sentinel Detection
  // ═══════════════════════════════════════════════════════════

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
  sentinelScan(sentinelId: string): SentinelScanResult {
    const sentinel = this.coordinator.getAgent(sentinelId);
    if (!sentinel || sentinel.role !== 'sentinel') {
      return {
        sentinelId,
        scannedAgents: [],
        flaggedAgents: [],
        quarantinedAgents: [],
        timestamp: Date.now(),
      };
    }

    this.stats.sentinelScans++;

    const scannedAgents: string[] = [];
    const flaggedAgents: SentinelScanResult['flaggedAgents'] = [];
    const quarantinedAgents: string[] = [];

    // Sacred Tongue index mapping
    const tongueIndexMap: Record<string, number> = {
      KO: 0, AV: 1, RU: 2, CA: 3, UM: 4, DR: 5,
    };

    for (const [agentId, managed] of this.managedAgents) {
      // Don't scan self
      if (agentId === sentinelId) continue;

      // Need minimum trajectory length
      if (managed.trajectory.length < this.config.minTrajectoryLength) continue;

      scannedAgents.push(agentId);

      // Run detection if function is available
      if (this.detectionFn) {
        const tongueIndex = tongueIndexMap[managed.tongue] ?? 0;
        const assessment = this.detectionFn(
          managed.trajectory,
          tongueIndex,
          { detectionThreshold: this.config.detectionThreshold },
        );
        managed.lastAssessment = assessment;

        if (assessment.anyFlagged) {
          flaggedAgents.push({
            agentId,
            combinedScore: assessment.combinedScore,
            decision: assessment.decision,
            flagCount: assessment.flagCount,
          });

          // Auto-quarantine if score exceeds threshold
          if (assessment.combinedScore >= this.config.quarantineThreshold) {
            this.coordinator.quarantineAgent(agentId, `sentinel_detection: score=${assessment.combinedScore.toFixed(3)}`);
            quarantinedAgents.push(agentId);
            this.stats.sentinelQuarantines++;
          }
        }
      } else {
        // Fallback: basic trajectory analysis without full detection
        const riskScores = managed.governanceLog.map((g) => g.riskScore);
        if (riskScores.length > 0) {
          const avgRisk = riskScores.reduce((s, r) => s + r, 0) / riskScores.length;
          const maxRisk = Math.max(...riskScores);

          if (maxRisk >= this.config.quarantineThreshold) {
            flaggedAgents.push({
              agentId,
              combinedScore: avgRisk,
              decision: maxRisk >= 0.85 ? 'DENY' : 'ESCALATE',
              flagCount: riskScores.filter((r) => r >= this.config.detectionThreshold).length,
            });

            if (maxRisk >= this.config.quarantineThreshold) {
              this.coordinator.quarantineAgent(agentId, `risk_threshold: max=${maxRisk.toFixed(3)}`);
              quarantinedAgents.push(agentId);
              this.stats.sentinelQuarantines++;
            }
          }
        }
      }
    }

    // Announce scan results on sentinel channel
    this.coordinator.bus.publish(sentinelId, 'sentinel', 'anomaly_detected', {
      scannedCount: scannedAgents.length,
      flaggedCount: flaggedAgents.length,
      quarantinedCount: quarantinedAgents.length,
    });

    return {
      sentinelId,
      scannedAgents,
      flaggedAgents,
      quarantinedAgents,
      timestamp: Date.now(),
    };
  }

  // ═══════════════════════════════════════════════════════════
  // Role Switching
  // ═══════════════════════════════════════════════════════════

  /**
   * Request a role switch for an agent.
   * Delegates to coordinator for braid validation and consensus.
   */
  requestRoleSwitch(agentId: string, toRole: CrawlRole, reason: string): string | null {
    return this.coordinator.requestRoleSwitch(agentId, toRole, reason);
  }

  /**
   * Vote on a role switch request.
   */
  voteOnRoleSwitch(requestId: string, voterId: string, approve: boolean): string {
    return this.coordinator.voteOnRoleSwitch(requestId, voterId, approve);
  }

  // ═══════════════════════════════════════════════════════════
  // Statistics & Queries
  // ═══════════════════════════════════════════════════════════

  /**
   * Get runner statistics.
   */
  getStats(): RunnerStats {
    this.stats.coordinatorStats = this.coordinator.getStats();
    return { ...this.stats };
  }

  /**
   * Get the trajectory for an agent.
   */
  getTrajectory(agentId: string): TrajectoryPoint[] {
    return this.managedAgents.get(agentId)?.trajectory ?? [];
  }

  /**
   * Get the governance log for an agent.
   */
  getGovernanceLog(agentId: string): GovernanceResult[] {
    return this.managedAgents.get(agentId)?.governanceLog ?? [];
  }

  /**
   * Get all crawl results from the coordinator.
   */
  getResults(): CrawlResult[] {
    return this.coordinator.getResults();
  }

  /**
   * Shut down all agents and close browser sessions.
   */
  async shutdown(): Promise<void> {
    for (const managed of this.managedAgents.values()) {
      if (managed.sessionActive) {
        try {
          await managed.backend.close();
        } catch {
          // Ignore close errors
        }
        managed.sessionActive = false;
      }
    }
  }

  // ═══════════════════════════════════════════════════════════
  // Private
  // ═══════════════════════════════════════════════════════════

  /**
   * Build a governance result for a navigation action.
   * In production, this would use BrowserActionEvaluator.evaluate().
   * Here we build a compatible result from observation metadata.
   */
  private evaluateNavigation(
    observation: BrowserObservation,
    managed: ManagedAgent,
  ): GovernanceResult {
    const url = observation.page.url ?? '';

    // Domain risk classification
    const domainRisk = this.classifyDomainRisk(url);

    // Action risk for navigation
    const actionRisk = 0.3;

    // Session risk from governance history
    const recentDenials = managed.governanceLog
      .slice(-10)
      .filter((g) => g.decision === 'DENY' || g.decision === 'ESCALATE').length;
    const sessionRisk = Math.min(recentDenials * 0.1, 0.8);

    // Temporal risk (action frequency)
    const temporalRisk = Math.min(managed.urlsCrawled.length / 100, 0.3);

    // Historical risk
    const historicalRisk = sessionRisk;

    // Combined risk
    const baseRisk = actionRisk * 0.35 + domainRisk * 0.25 + temporalRisk * 0.2 + historicalRisk * 0.2;
    const riskScore = Math.min(baseRisk, 1.0);

    // Decision
    let decision: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
    let confidence: number;

    if (riskScore < 0.3) {
      decision = 'ALLOW';
      confidence = 1 - riskScore / 0.3;
    } else if (riskScore < 0.6) {
      decision = 'QUARANTINE';
      confidence = (riskScore - 0.3) / 0.3;
    } else if (riskScore < 0.85) {
      decision = 'ESCALATE';
      confidence = (riskScore - 0.6) / 0.25;
    } else {
      decision = 'DENY';
      confidence = Math.min((riskScore - 0.85) / 0.15, 1);
    }

    return {
      decision,
      decisionId: `gov-${managed.agentId}-${Date.now()}`,
      riskScore,
      confidence,
      riskFactors: {
        actionRisk,
        domainRisk,
        sessionRisk,
        temporalRisk,
        historicalRisk,
      },
      explanation: `${decision}: navigate to ${url} (risk: ${riskScore.toFixed(3)})`,
      requiredTier: 'KO' as TongueCode,
      requiresRoundtable: false,
    };
  }

  /**
   * Classify domain risk from URL.
   */
  private classifyDomainRisk(url: string): number {
    const patterns: [RegExp, number][] = [
      [/bank|chase|wellsfargo|citi|bofa/i, 0.9],
      [/paypal|stripe|venmo|finance|invest/i, 0.85],
      [/health|medical|doctor|hospital/i, 0.8],
      [/\.gov$|government|irs/i, 0.8],
      [/amazon|ebay|walmart|shop|store/i, 0.6],
      [/facebook|twitter|instagram|social/i, 0.5],
      [/news|cnn|bbc|reuters/i, 0.2],
      [/google|bing|search/i, 0.1],
    ];

    for (const [pattern, risk] of patterns) {
      if (pattern.test(url)) return risk;
    }
    return 0.4; // Unknown domain
  }
}
