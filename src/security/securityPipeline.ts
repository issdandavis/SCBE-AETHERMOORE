/**
 * @file securityPipeline.ts
 * @module security/securityPipeline
 * @layer Layer 1-14
 * @component Unified 14-Layer Security Pipeline Orchestrator
 * @version 1.0.0
 *
 * Orchestrates the full SCBE 14-layer security pipeline with:
 * - Input validation & sanitization (system boundary)
 * - 14-layer hyperbolic risk assessment (L1-L14)
 * - 4-tier governance decisions (ALLOW / QUARANTINE / ESCALATE / DENY)
 * - Cryptographic audit trail (SHA-256 hash chain)
 * - Replay protection (Bloom filter)
 *
 * Core invariant: adversarial intent costs exponentially more the
 * further it drifts from the safe center of the Poincare ball.
 */

import crypto from 'node:crypto';
import {
  scbe14LayerPipeline,
  type Pipeline14Config,
  type Pipeline14Result,
} from '../harmonic/pipeline14.js';
import {
  validateInput,
  normalizeInputLength,
  type ValidatorConfig,
  type ValidationResult,
} from './inputValidator.js';
import {
  SecurityAuditTrail,
  type GovernanceDecision,
  type AuditEntry,
} from './auditTrail.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/**
 * Configuration for the security pipeline.
 */
export interface SecurityPipelineConfig {
  /** Pipeline configuration (dimension, thresholds, etc.) */
  pipeline?: Pipeline14Config;

  /** Input validation configuration */
  validator?: Partial<ValidatorConfig>;

  /** 4-tier governance thresholds (riskPrime boundaries) */
  thresholds?: {
    /** Below this: ALLOW (default: 0.25) */
    allow: number;
    /** Below this: QUARANTINE (default: 0.50) */
    quarantine: number;
    /** Below this: ESCALATE; above: DENY (default: 0.75) */
    escalate: number;
  };

  /** Enable replay protection (default: true) */
  enableReplayProtection?: boolean;

  /** Maximum audit trail entries in memory (default: 10000) */
  maxAuditEntries?: number;

  /** Enable HMAC integrity tag on results (default: true) */
  enableIntegrityTag?: boolean;
}

/**
 * Default security pipeline configuration.
 */
export const DEFAULT_SECURITY_CONFIG: Required<SecurityPipelineConfig> = {
  pipeline: {
    D: 6,
    alpha: 1.0,
    epsBall: 0.01,
    breathingFactor: 1.0,
    theta1: 0.33,
    theta2: 0.67,
    wD: 0.2,
    wC: 0.2,
    wS: 0.2,
    wTau: 0.2,
    wA: 0.2,
  },
  validator: {},
  thresholds: {
    allow: 0.25,
    quarantine: 0.50,
    escalate: 0.75,
  },
  enableReplayProtection: true,
  maxAuditEntries: 10000,
  enableIntegrityTag: true,
};

/**
 * Input context for a security pipeline request.
 */
export interface SecurityRequest {
  /** Context vector (time-dependent features) */
  input: number[];
  /** Unique request identifier (for replay protection) */
  requestId?: string;
  /** Provider identifier */
  providerId?: string;
  /** Additional metadata passed through to audit */
  metadata?: Record<string, unknown>;
}

/**
 * Full security pipeline execution result.
 */
export interface SecurityResult {
  /** 4-tier governance decision */
  decision: GovernanceDecision;
  /** Amplified risk score (riskBase / H) */
  riskPrime: number;
  /** Harmonic safety score H in (0, 1] */
  harmonicScore: number;
  /** Hyperbolic distance from safe center */
  hyperbolicDistance: number;
  /** Whether input validation passed */
  validationPassed: boolean;
  /** Validation errors (if any) */
  validationErrors: string[];
  /** Whether the request was flagged as a replay */
  replayDetected: boolean;
  /** Request identifier */
  requestId: string;
  /** Full 14-layer metrics (available when decision != validation_fail) */
  layers?: Pipeline14Result['layers'];
  /** HMAC-SHA256 integrity tag over the result (hex) */
  integrityTag?: string;
  /** Audit entry reference */
  auditSeq?: number;
}

// ═══════════════════════════════════════════════════════════════
// Security Pipeline
// ═══════════════════════════════════════════════════════════════

/**
 * SCBE 14-Layer Security Pipeline.
 *
 * Orchestrates input validation, the full 14-layer hyperbolic risk
 * assessment, 4-tier governance decisions, replay protection, and
 * cryptographic audit logging.
 *
 * Usage:
 * ```typescript
 * const pipeline = new SecurityPipeline();
 * const result = pipeline.execute({
 *   input: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0, 0, 0, 0, 0, 0],
 *   requestId: 'req-001',
 * });
 * console.log(result.decision); // 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY'
 * ```
 */
export class SecurityPipeline {
  private readonly config: Required<SecurityPipelineConfig>;
  private readonly audit: SecurityAuditTrail;
  private readonly seenRequests: Set<string>;
  private readonly integrityKey: Buffer;

  constructor(config: SecurityPipelineConfig = {}) {
    this.config = {
      pipeline: config.pipeline ?? DEFAULT_SECURITY_CONFIG.pipeline,
      validator: config.validator ?? DEFAULT_SECURITY_CONFIG.validator,
      thresholds: config.thresholds ?? DEFAULT_SECURITY_CONFIG.thresholds,
      enableReplayProtection:
        config.enableReplayProtection ?? DEFAULT_SECURITY_CONFIG.enableReplayProtection,
      maxAuditEntries: config.maxAuditEntries ?? DEFAULT_SECURITY_CONFIG.maxAuditEntries,
      enableIntegrityTag:
        config.enableIntegrityTag ?? DEFAULT_SECURITY_CONFIG.enableIntegrityTag,
    };

    this.audit = new SecurityAuditTrail(this.config.maxAuditEntries);
    this.seenRequests = new Set();
    // Per-instance HMAC key for integrity tags
    this.integrityKey = crypto.randomBytes(32);
  }

  /**
   * Execute the full 14-layer security pipeline.
   *
   * Flow:
   * 1. Generate request ID if missing
   * 2. Validate & sanitize input (system boundary)
   * 3. Check for replay attacks
   * 4. Run 14-layer hyperbolic risk assessment
   * 5. Map to 4-tier governance decision
   * 6. Compute integrity tag
   * 7. Log to audit trail
   *
   * @param request - Security pipeline request
   * @returns Full security result with decision and metrics
   */
  execute(request: SecurityRequest): SecurityResult {
    const requestId = request.requestId ?? crypto.randomUUID();

    // === Step 1: Input Validation ===
    const validation = validateInput(request.input, this.config.validator);

    if (!validation.valid) {
      this.audit.logValidationFail(validation.errors, requestId);

      return {
        decision: 'DENY',
        riskPrime: Infinity,
        harmonicScore: 0,
        hyperbolicDistance: Infinity,
        validationPassed: false,
        validationErrors: validation.errors,
        replayDetected: false,
        requestId,
      };
    }

    // === Step 2: Replay Protection ===
    if (this.config.enableReplayProtection) {
      const replayKey = request.providerId
        ? `${request.providerId}::${requestId}`
        : requestId;

      if (this.seenRequests.has(replayKey)) {
        this.audit.logReplayBlocked(requestId, request.providerId);

        return {
          decision: 'DENY',
          riskPrime: Infinity,
          harmonicScore: 0,
          hyperbolicDistance: Infinity,
          validationPassed: true,
          validationErrors: [],
          replayDetected: true,
          requestId,
        };
      }

      this.seenRequests.add(replayKey);
    }

    // === Step 3: Normalize input for pipeline ===
    const D = this.config.pipeline.D ?? 6;
    const targetLength = 2 * D;
    const normalized = normalizeInputLength(validation.sanitized!, targetLength);

    // === Step 4: Execute 14-Layer Pipeline ===
    const pipelineResult = scbe14LayerPipeline(normalized, this.config.pipeline);

    // === Step 5: Map to 4-Tier Governance Decision ===
    const decision = this.mapToGovernanceDecision(pipelineResult.riskPrime);

    // === Step 6: Build Result ===
    const result: SecurityResult = {
      decision,
      riskPrime: pipelineResult.riskPrime,
      harmonicScore: pipelineResult.riskComponents.H,
      hyperbolicDistance: pipelineResult.layers.l5_distance,
      validationPassed: true,
      validationErrors: [],
      replayDetected: false,
      requestId,
      layers: pipelineResult.layers,
    };

    // === Step 7: Integrity Tag ===
    if (this.config.enableIntegrityTag) {
      result.integrityTag = this.computeIntegrityTag(result);
    }

    // === Step 8: Audit Log ===
    const auditEntry = this.audit.logPipelineExecution({
      decision,
      riskPrime: pipelineResult.riskPrime,
      harmonicScore: pipelineResult.riskComponents.H,
      hyperbolicDistance: pipelineResult.layers.l5_distance,
      requestId,
      metadata: request.metadata,
    });

    result.auditSeq = auditEntry.seq;

    // Log anomaly if risk is high
    if (decision === 'ESCALATE' || decision === 'DENY') {
      this.audit.logAnomaly({
        description: `High-risk request: decision=${decision}, riskPrime=${pipelineResult.riskPrime.toFixed(4)}`,
        riskPrime: pipelineResult.riskPrime,
        requestId,
      });
    }

    return result;
  }

  /**
   * Map an amplified risk score to a 4-tier governance decision.
   *
   * ALLOW:      riskPrime < thresholds.allow
   * QUARANTINE: thresholds.allow <= riskPrime < thresholds.quarantine
   * ESCALATE:   thresholds.quarantine <= riskPrime < thresholds.escalate
   * DENY:       riskPrime >= thresholds.escalate
   */
  private mapToGovernanceDecision(riskPrime: number): GovernanceDecision {
    const { allow, quarantine, escalate } = this.config.thresholds;

    if (riskPrime < allow) return 'ALLOW';
    if (riskPrime < quarantine) return 'QUARANTINE';
    if (riskPrime < escalate) return 'ESCALATE';
    return 'DENY';
  }

  /**
   * Compute HMAC-SHA256 integrity tag over a security result.
   */
  private computeIntegrityTag(result: Omit<SecurityResult, 'integrityTag' | 'auditSeq'>): string {
    const payload = JSON.stringify({
      decision: result.decision,
      riskPrime: result.riskPrime,
      harmonicScore: result.harmonicScore,
      hyperbolicDistance: result.hyperbolicDistance,
      requestId: result.requestId,
    });

    return crypto
      .createHmac('sha256', this.integrityKey)
      .update(payload)
      .digest('hex');
  }

  /**
   * Verify an integrity tag on a security result.
   *
   * @param result - The result to verify
   * @returns true if the tag is valid
   */
  verifyIntegrity(result: SecurityResult): boolean {
    if (!result.integrityTag) return false;

    const expected = this.computeIntegrityTag(result);

    // Constant-time comparison
    const a = Buffer.from(result.integrityTag, 'hex');
    const b = Buffer.from(expected, 'hex');
    if (a.length !== b.length) return false;

    return crypto.timingSafeEqual(a, b);
  }

  /**
   * Get the audit trail instance.
   */
  getAuditTrail(): SecurityAuditTrail {
    return this.audit;
  }

  /**
   * Get audit trail statistics.
   */
  getAuditStats() {
    return this.audit.getStats();
  }

  /**
   * Verify audit trail integrity.
   */
  verifyAuditChain(): boolean {
    return this.audit.verifyChain();
  }
}

/**
 * Create a security pipeline with default configuration.
 */
export function createSecurityPipeline(
  config: SecurityPipelineConfig = {}
): SecurityPipeline {
  return new SecurityPipeline(config);
}
