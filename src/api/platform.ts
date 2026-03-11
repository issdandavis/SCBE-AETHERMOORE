/**
 * @file platform.ts
 * @module api/platform
 * @layer Layer 1-14 (full pipeline)
 * @component SCBE Platform API — Monetizable Browser-as-a-Service
 *
 * Headless API for the SCBE-governed browser platform.
 * Three core endpoints:
 *   POST /v1/session/open   — create governed browser session
 *   POST /v1/session/step   — execute governed action
 *   POST /v1/session/close  — terminate and archive audit log
 *
 * Plus:
 *   GET  /v1/session/:id    — session status and metrics
 *   GET  /v1/usage          — usage metering for billing
 *   POST /v1/swarm/execute  — fleet swarm browsing
 *
 * Designed for consumption-based billing:
 *   - API calls (trust evaluations, browser steps)
 *   - Compute minutes per session
 *   - Number of governed agents connected
 */

import { createHash, randomBytes } from 'crypto';
import {
  HyperbolicTrustBrowser,
  HyperbolicTrustScore,
  NavigationIntent,
} from '../browser/hyperbolicTrustBrowser.js';
import {
  SpiralSealSessionBrowser,
  EncryptedSession,
  SealedAction,
  SealedActionResult,
} from '../browser/spiralSealSession.js';
import type { BrowserActionType, BrowserDecision } from '../browser/types.js';
import { RedisStore, getRedisStore } from './redisStore.js';
import { scanForMaliciousContent, scanUrl } from './securityGuardrails.js';

// ============================================================================
// Types — Platform API
// ============================================================================

/** API key record */
export interface ApiKey {
  /** Key hash (we never store raw keys) */
  keyHash: string;
  /** Owner/org ID */
  ownerId: string;
  /** Tier */
  tier: PlatformTier;
  /** Created at */
  createdAt: number;
  /** Rate limit (requests per minute) */
  rateLimit: number;
  /** Monthly session budget */
  monthlySessionBudget: number;
}

/** Platform pricing tiers */
export type PlatformTier = 'developer' | 'startup' | 'enterprise';

/** Session open request */
export interface SessionOpenRequest {
  /** Starting URL */
  startUrl?: string;
  /** Agent ID (caller-defined) */
  agentId: string;
  /** Policy tier for governance */
  policy?: 'standard' | 'elevated' | 'critical';
  /** Custom tongue configuration */
  tongueConfig?: Partial<Record<string, boolean>>;
}

/** Session open response */
export interface SessionOpenResponse {
  /** Session ID */
  sessionId: string;
  /** Encrypted session metadata */
  sealMetadata: {
    keyVersion: number;
    noncePrefix: string;
    temporalChecksum: number;
  };
  /** Initial trust score */
  trustScore: HyperbolicTrustScore;
  /** Session TTL (ms) */
  ttlMs: number;
  /** Timestamp */
  createdAt: string;
}

/** Session step request */
export interface SessionStepRequest {
  /** Action to perform */
  action: BrowserActionType;
  /** Target URL or selector */
  target: string;
  /** Actor type */
  actorType?: 'human' | 'ai' | 'system';
  /** Trust score override (optional) */
  trustScore?: number;
  /** Action payload */
  payload?: Record<string, unknown>;
}

/** Session step response */
export interface SessionStepResponse {
  /** Step success */
  success: boolean;
  /** Governance decision */
  decision: BrowserDecision;
  /** Trust score from hyperbolic pipeline */
  trustScore: HyperbolicTrustScore;
  /** Seal verification */
  sealVerification: {
    newChecksum: number;
    tongueVerification: string[];
  };
  /** Step data */
  data?: unknown;
  /** Error */
  error?: string;
  /** Latency (ms) */
  latencyMs: number;
}

/** Session close response */
export interface SessionCloseResponse {
  /** Session ID */
  sessionId: string;
  /** Total steps executed */
  stepsExecuted: number;
  /** Total session duration (ms) */
  durationMs: number;
  /** Final trust state */
  finalDecision: BrowserDecision;
  /** Audit trail summary */
  auditSummary: {
    totalActions: number;
    allowed: number;
    quarantined: number;
    escalated: number;
    denied: number;
  };
  /** Closed at */
  closedAt: string;
}

/** Session status */
export interface SessionStatusResponse {
  /** Session ID */
  sessionId: string;
  /** Active */
  active: boolean;
  /** Steps executed */
  stepsExecuted: number;
  /** Duration so far */
  durationMs: number;
  /** Current trust state */
  currentDecision: BrowserDecision;
  /** Remaining TTL */
  remainingTtlMs: number;
}

/** Usage metering response */
export interface UsageResponse {
  /** Owner ID */
  ownerId: string;
  /** Tier */
  tier: PlatformTier;
  /** Current period */
  period: string;
  /** Metrics */
  metrics: {
    sessionsOpened: number;
    sessionsActive: number;
    totalSteps: number;
    totalComputeMinutes: number;
    agentsConnected: number;
  };
  /** Budget remaining */
  budgetRemaining: {
    sessions: number;
    stepsEstimate: number;
  };
}

/** Swarm execute request */
export interface SwarmExecuteRequest {
  /** High-level objective */
  objective: string;
  /** Number of agents */
  agentCount: number;
  /** Consensus threshold */
  consensusThreshold?: number;
  /** Sub-tasks */
  subTasks: Array<{
    id: string;
    action: string;
    target: string;
    role: 'navigator' | 'extractor' | 'validator' | 'sentinel';
  }>;
}

// ============================================================================
// Platform State
// ============================================================================

interface PlatformSession {
  sessionId: string;
  ownerId: string;
  agentId: string;
  policy: string;
  sealSession: EncryptedSession;
  htb: HyperbolicTrustBrowser;
  stepsExecuted: number;
  decisions: Record<BrowserDecision, number>;
  startedAt: number;
  lastStepAt: number;
  active: boolean;
}

interface OwnerUsage {
  sessionsOpened: number;
  totalSteps: number;
  agentsConnected: Set<string>;
}

/** Serialisable subset of PlatformSession for Redis persistence */
interface SessionMeta {
  sessionId: string;
  ownerId: string;
  agentId: string;
  policy: string;
  stepsExecuted: number;
  decisions: Record<BrowserDecision, number>;
  startedAt: number;
  lastStepAt: number;
  active: boolean;
}

// ============================================================================
// Platform API Controller
// ============================================================================

/**
 * SCBE Platform API.
 *
 * Wraps HTB (trust scoring), SSSB (sealed sessions), and FSB (swarm)
 * into a monetizable headless browser API.
 */
export class SCBEPlatformAPI {
  private readonly sealBrowser: SpiralSealSessionBrowser;
  private readonly sessions: Map<string, PlatformSession> = new Map();
  private readonly apiKeys: Map<string, ApiKey> = new Map();
  private readonly usage: Map<string, OwnerUsage> = new Map();
  private readonly sessionTtlMs: number;
  private readonly store: RedisStore;

  constructor(options?: {
    masterKey?: string;
    sessionTtlMs?: number;
    redisUrl?: string;
  }) {
    const masterKey = options?.masterKey ?? randomBytes(32).toString('hex');
    this.sealBrowser = new SpiralSealSessionBrowser(masterKey);
    this.sessionTtlMs = options?.sessionTtlMs ?? 30 * 60 * 1000;
    this.store = getRedisStore({ url: options?.redisUrl });
  }

  /** Connect to Redis for persistence. Safe to skip — falls back to in-memory. */
  async connectStore(): Promise<boolean> {
    return this.store.connect();
  }

  // --------------------------------------------------------------------------
  // API Key Management
  // --------------------------------------------------------------------------

  /**
   * Register an API key.
   */
  registerApiKey(ownerId: string, tier: PlatformTier): string {
    const raw = randomBytes(32).toString('hex');
    const keyHash = createHash('sha256').update(raw).digest('hex');

    const limits: Record<PlatformTier, { rate: number; sessions: number }> = {
      developer: { rate: 60, sessions: 100 },
      startup: { rate: 300, sessions: 1000 },
      enterprise: { rate: 3000, sessions: 50000 },
    };

    const limit = limits[tier];

    const apiKey: ApiKey = {
      keyHash,
      ownerId,
      tier,
      createdAt: Date.now(),
      rateLimit: limit.rate,
      monthlySessionBudget: limit.sessions,
    };

    this.apiKeys.set(keyHash, apiKey);

    // Persist to Redis (fire-and-forget, in-memory is authoritative for hot path)
    this.store.set('apikey:' + keyHash, apiKey).catch(() => {});

    return raw;
  }

  /**
   * Validate an API key and return the owner context.
   */
  validateApiKey(rawKey: string): ApiKey | null {
    const keyHash = createHash('sha256').update(rawKey).digest('hex');
    return this.apiKeys.get(keyHash) ?? null;
  }

  /**
   * Validate API key with async Redis fallback.
   * Checks in-memory first, then Redis if miss.
   */
  async validateApiKeyAsync(rawKey: string): Promise<ApiKey | null> {
    const keyHash = createHash('sha256').update(rawKey).digest('hex');

    // Hot path: check in-memory
    const cached = this.apiKeys.get(keyHash);
    if (cached) return cached;

    // Cold path: check Redis
    const stored = await this.store.get<ApiKey>('apikey:' + keyHash);
    if (stored) {
      this.apiKeys.set(keyHash, stored); // Warm the cache
    }
    return stored;
  }

  // --------------------------------------------------------------------------
  // Session Lifecycle
  // --------------------------------------------------------------------------

  /**
   * POST /v1/session/open
   */
  openSession(ownerId: string, req: SessionOpenRequest): SessionOpenResponse {
    // Create sealed session
    const sealSession = this.sealBrowser.createSession(req.agentId, req.startUrl);

    // Create HTB for trust scoring
    const htb = new HyperbolicTrustBrowser();

    // Initial trust evaluation
    const intent: NavigationIntent = {
      url: req.startUrl ?? 'about:blank',
      action: 'navigate',
      agentId: req.agentId,
      actorType: 'ai',
      trustScore: 0.7,
    };
    const trustScore = htb.evaluate(intent);

    const platformSession: PlatformSession = {
      sessionId: sealSession.sessionId,
      ownerId,
      agentId: req.agentId,
      policy: req.policy ?? 'standard',
      sealSession,
      htb,
      stepsExecuted: 0,
      decisions: { ALLOW: 0, QUARANTINE: 0, ESCALATE: 0, DENY: 0 },
      startedAt: Date.now(),
      lastStepAt: Date.now(),
      active: true,
    };

    this.sessions.set(sealSession.sessionId, platformSession);

    // Track usage
    this._trackUsage(ownerId, req.agentId, 'session_open');

    // Persist session metadata to Redis (TTL = session TTL)
    const meta: SessionMeta = {
      sessionId: platformSession.sessionId,
      ownerId: platformSession.ownerId,
      agentId: platformSession.agentId,
      policy: platformSession.policy,
      stepsExecuted: platformSession.stepsExecuted,
      decisions: platformSession.decisions,
      startedAt: platformSession.startedAt,
      lastStepAt: platformSession.lastStepAt,
      active: platformSession.active,
    };
    this.store.set('session:' + sealSession.sessionId, meta, this.sessionTtlMs / 1000).catch(() => {});

    return {
      sessionId: sealSession.sessionId,
      sealMetadata: {
        keyVersion: sealSession.keyVersion,
        noncePrefix: sealSession.noncePrefix,
        temporalChecksum: sealSession.temporalChecksum,
      },
      trustScore,
      ttlMs: this.sessionTtlMs,
      createdAt: new Date().toISOString(),
    };
  }

  /**
   * POST /v1/session/step
   */
  executeStep(sessionId: string, req: SessionStepRequest): SessionStepResponse {
    const start = Date.now();
    const session = this.sessions.get(sessionId);

    if (!session || !session.active) {
      return {
        success: false,
        decision: 'DENY',
        trustScore: this._emptyTrustScore(),
        sealVerification: { newChecksum: 0, tongueVerification: ['SESSION_NOT_FOUND'] },
        error: 'Session not found or inactive',
        latencyMs: Date.now() - start,
      };
    }

    // Security guardrail scan — blocks credit card scams, phishing, code injection
    const urlScan = scanUrl(req.target);
    if (urlScan.recommendation === 'DENY') {
      session.decisions['DENY']++;
      this._persistSession(session);
      return {
        success: false,
        decision: 'DENY',
        trustScore: this._emptyTrustScore(),
        sealVerification: { newChecksum: session.sealSession.temporalChecksum, tongueVerification: ['GUARDRAIL_DENY'] },
        error: `Security guardrail: ${urlScan.hits.map((h) => h.description).join('; ')}`,
        latencyMs: Date.now() - start,
      };
    }

    const payloadScan = scanForMaliciousContent(JSON.stringify(req.payload ?? {}));
    if (payloadScan.recommendation === 'DENY') {
      session.decisions['DENY']++;
      this._persistSession(session);
      return {
        success: false,
        decision: 'DENY',
        trustScore: this._emptyTrustScore(),
        sealVerification: { newChecksum: session.sealSession.temporalChecksum, tongueVerification: ['GUARDRAIL_DENY'] },
        error: `Security guardrail: ${payloadScan.hits.map((h) => h.description).join('; ')}`,
        latencyMs: Date.now() - start,
      };
    }

    // HTB trust evaluation
    const intent: NavigationIntent = {
      url: req.target,
      action: req.action,
      agentId: session.agentId,
      actorType: req.actorType ?? 'ai',
      trustScore: req.trustScore ?? 0.7,
    };
    const trustScore = session.htb.evaluate(intent);

    // If DENY, don't execute
    if (trustScore.decision === 'DENY') {
      session.decisions['DENY']++;
      return {
        success: false,
        decision: 'DENY',
        trustScore,
        sealVerification: { newChecksum: session.sealSession.temporalChecksum, tongueVerification: ['DENIED'] },
        error: trustScore.explanation,
        latencyMs: Date.now() - start,
      };
    }

    // Execute through sealed session
    const sealAction: SealedAction = {
      type: req.action,
      payload: { url: req.target, ...req.payload },
      nonce: randomBytes(16).toString('hex'),
      timestamp: Date.now(),
    };

    const sealResult = this.sealBrowser.executeAction(sessionId, sealAction);

    session.stepsExecuted++;
    session.lastStepAt = Date.now();
    session.decisions[trustScore.decision]++;

    // Track usage
    this._trackUsage(session.ownerId, session.agentId, 'step');

    // Persist updated session metadata
    this._persistSession(session);

    return {
      success: sealResult.success,
      decision: trustScore.decision,
      trustScore,
      sealVerification: {
        newChecksum: sealResult.newChecksum,
        tongueVerification: sealResult.tongueVerification,
      },
      data: sealResult.data,
      error: sealResult.error,
      latencyMs: Date.now() - start,
    };
  }

  /**
   * POST /v1/session/close
   */
  closeSession(sessionId: string): SessionCloseResponse | null {
    const session = this.sessions.get(sessionId);
    if (!session) return null;

    session.active = false;
    this.sealBrowser.terminateSession(sessionId);
    this._persistSession(session);

    const durationMs = Date.now() - session.startedAt;

    return {
      sessionId,
      stepsExecuted: session.stepsExecuted,
      durationMs,
      finalDecision: this._dominantDecision(session.decisions),
      auditSummary: {
        totalActions: session.stepsExecuted,
        allowed: session.decisions['ALLOW'],
        quarantined: session.decisions['QUARANTINE'],
        escalated: session.decisions['ESCALATE'],
        denied: session.decisions['DENY'],
      },
      closedAt: new Date().toISOString(),
    };
  }

  /**
   * GET /v1/session/:id
   */
  getSessionStatus(sessionId: string): SessionStatusResponse | null {
    const session = this.sessions.get(sessionId);
    if (!session) return null;

    const elapsed = Date.now() - session.startedAt;

    return {
      sessionId,
      active: session.active,
      stepsExecuted: session.stepsExecuted,
      durationMs: elapsed,
      currentDecision: this._dominantDecision(session.decisions),
      remainingTtlMs: Math.max(0, this.sessionTtlMs - elapsed),
    };
  }

  /**
   * GET /v1/usage
   */
  getUsage(ownerId: string, tier: PlatformTier): UsageResponse {
    const u = this.usage.get(ownerId);

    const limits: Record<PlatformTier, number> = {
      developer: 100,
      startup: 1000,
      enterprise: 50000,
    };

    const activeSessions = Array.from(this.sessions.values()).filter(
      (s) => s.ownerId === ownerId && s.active
    ).length;

    return {
      ownerId,
      tier,
      period: new Date().toISOString().slice(0, 7), // YYYY-MM
      metrics: {
        sessionsOpened: u?.sessionsOpened ?? 0,
        sessionsActive: activeSessions,
        totalSteps: u?.totalSteps ?? 0,
        totalComputeMinutes: Math.ceil((u?.totalSteps ?? 0) * 0.02), // ~1.2s per step
        agentsConnected: u?.agentsConnected.size ?? 0,
      },
      budgetRemaining: {
        sessions: limits[tier] - (u?.sessionsOpened ?? 0),
        stepsEstimate: (limits[tier] - (u?.sessionsOpened ?? 0)) * 100,
      },
    };
  }

  // --------------------------------------------------------------------------
  // Internal
  // --------------------------------------------------------------------------

  private _trackUsage(ownerId: string, agentId: string, event: 'session_open' | 'step'): void {
    let u = this.usage.get(ownerId);
    if (!u) {
      u = { sessionsOpened: 0, totalSteps: 0, agentsConnected: new Set() };
      this.usage.set(ownerId, u);
    }

    u.agentsConnected.add(agentId);

    if (event === 'session_open') {
      u.sessionsOpened++;
    } else {
      u.totalSteps++;
    }

    // Persist usage counters to Redis
    const usageKey = 'usage:' + ownerId;
    this.store.incr(usageKey, event === 'session_open' ? 'sessionsOpened' : 'totalSteps').catch(() => {});
    this.store.sadd('usage:agents:' + ownerId, agentId).catch(() => {});
  }

  /** Persist session metadata to Redis (fire-and-forget). */
  private _persistSession(session: PlatformSession): void {
    const meta: SessionMeta = {
      sessionId: session.sessionId,
      ownerId: session.ownerId,
      agentId: session.agentId,
      policy: session.policy,
      stepsExecuted: session.stepsExecuted,
      decisions: session.decisions,
      startedAt: session.startedAt,
      lastStepAt: session.lastStepAt,
      active: session.active,
    };
    const remainingTtl = Math.max(1, (this.sessionTtlMs - (Date.now() - session.startedAt)) / 1000);
    this.store.set('session:' + session.sessionId, meta, remainingTtl).catch(() => {});
  }

  private _dominantDecision(decisions: Record<BrowserDecision, number>): BrowserDecision {
    let best: BrowserDecision = 'ALLOW';
    let bestCount = -1;
    for (const [decision, count] of Object.entries(decisions) as Array<[BrowserDecision, number]>) {
      if (count > bestCount) {
        best = decision;
        bestCount = count;
      }
    }
    return best;
  }

  private _emptyTrustScore(): HyperbolicTrustScore {
    return {
      hyperbolicDistance: Infinity,
      layerScores: new Array(14).fill(1),
      tongueResonance: [false, false, false, false, false, false],
      decision: 'DENY',
      breathingPhase: 0,
      harmonicCost: 0,
      riskScore: 1,
      explanation: 'No session',
    };
  }
}
