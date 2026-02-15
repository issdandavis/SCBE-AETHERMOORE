/**
 * @file auditTrail.ts
 * @module security/auditTrail
 * @layer Layer 13, Layer 14
 * @component Security Audit Trail
 * @version 1.0.0
 *
 * SHA-256 hash-chained audit logger for the security pipeline.
 * Every pipeline execution, decision, and anomaly is recorded
 * with cryptographic integrity guarantees.
 */

import crypto from 'node:crypto';

/**
 * 4-tier governance decisions (L13).
 */
export type GovernanceDecision = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';

/**
 * A single audit entry in the hash-chained log.
 */
export interface AuditEntry {
  /** Monotonic sequence number */
  seq: number;
  /** ISO-8601 timestamp */
  timestamp: string;
  /** SHA-256 hash of the previous entry (hex) */
  prevHash: string;
  /** SHA-256 hash of this entry (hex) */
  hash: string;
  /** Event type */
  eventType: 'pipeline_execution' | 'decision' | 'anomaly' | 'replay_blocked' | 'validation_fail';
  /** Pipeline decision */
  decision?: GovernanceDecision;
  /** Amplified risk score */
  riskPrime?: number;
  /** Harmonic safety score H */
  harmonicScore?: number;
  /** Hyperbolic distance from safe center */
  hyperbolicDistance?: number;
  /** Request identifier */
  requestId?: string;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Audit trail statistics.
 */
export interface AuditStats {
  totalEntries: number;
  decisions: Record<GovernanceDecision, number>;
  anomalyCount: number;
  replayBlockedCount: number;
  validationFailCount: number;
  chainIntact: boolean;
}

/**
 * SHA-256 hash-chained security audit trail.
 *
 * Provides tamper-evident logging for all security pipeline operations.
 * Each entry is hashed with the previous entry's hash to create an
 * immutable chain, following the same pattern as the BrainAuditLogger
 * but specialized for security pipeline events.
 */
export class SecurityAuditTrail {
  private entries: AuditEntry[] = [];
  private readonly maxEntries: number;
  private seq = 0;

  /**
   * @param maxEntries - Maximum entries to retain in memory (default: 10000)
   */
  constructor(maxEntries: number = 10000) {
    this.maxEntries = maxEntries;
  }

  /**
   * Compute SHA-256 hash of an audit entry's content (excluding its own hash).
   */
  private computeHash(entry: Omit<AuditEntry, 'hash'>): string {
    const content = JSON.stringify({
      seq: entry.seq,
      timestamp: entry.timestamp,
      prevHash: entry.prevHash,
      eventType: entry.eventType,
      decision: entry.decision,
      riskPrime: entry.riskPrime,
      harmonicScore: entry.harmonicScore,
      hyperbolicDistance: entry.hyperbolicDistance,
      requestId: entry.requestId,
    });
    return crypto.createHash('sha256').update(content).digest('hex');
  }

  /**
   * Get the hash of the last entry in the chain (genesis hash if empty).
   */
  private lastHash(): string {
    if (this.entries.length === 0) {
      // Genesis hash: SHA-256 of the SCBE patent number
      return crypto
        .createHash('sha256')
        .update('USPTO #63/961,403')
        .digest('hex');
    }
    return this.entries[this.entries.length - 1].hash;
  }

  /**
   * Append a new entry to the audit trail.
   */
  private append(
    partial: Omit<AuditEntry, 'seq' | 'timestamp' | 'prevHash' | 'hash'>
  ): AuditEntry {
    const entry: Omit<AuditEntry, 'hash'> = {
      seq: this.seq++,
      timestamp: new Date().toISOString(),
      prevHash: this.lastHash(),
      ...partial,
    };

    const hash = this.computeHash(entry);
    const fullEntry: AuditEntry = { ...entry, hash };

    this.entries.push(fullEntry);

    // Evict oldest entries if over limit
    if (this.entries.length > this.maxEntries) {
      this.entries.shift();
    }

    return fullEntry;
  }

  /**
   * Log a pipeline execution result.
   */
  logPipelineExecution(params: {
    decision: GovernanceDecision;
    riskPrime: number;
    harmonicScore: number;
    hyperbolicDistance: number;
    requestId?: string;
    metadata?: Record<string, unknown>;
  }): AuditEntry {
    return this.append({
      eventType: 'pipeline_execution',
      decision: params.decision,
      riskPrime: params.riskPrime,
      harmonicScore: params.harmonicScore,
      hyperbolicDistance: params.hyperbolicDistance,
      requestId: params.requestId,
      metadata: params.metadata,
    });
  }

  /**
   * Log an anomaly detection.
   */
  logAnomaly(params: {
    description: string;
    riskPrime?: number;
    requestId?: string;
    metadata?: Record<string, unknown>;
  }): AuditEntry {
    return this.append({
      eventType: 'anomaly',
      riskPrime: params.riskPrime,
      requestId: params.requestId,
      metadata: { description: params.description, ...params.metadata },
    });
  }

  /**
   * Log a blocked replay attempt.
   */
  logReplayBlocked(requestId: string, providerId?: string): AuditEntry {
    return this.append({
      eventType: 'replay_blocked',
      requestId,
      metadata: { providerId },
    });
  }

  /**
   * Log a validation failure.
   */
  logValidationFail(errors: string[], requestId?: string): AuditEntry {
    return this.append({
      eventType: 'validation_fail',
      requestId,
      metadata: { errors },
    });
  }

  /**
   * Verify the integrity of the hash chain.
   *
   * @returns true if the chain is intact, false if tampered
   */
  verifyChain(): boolean {
    for (let i = 0; i < this.entries.length; i++) {
      const entry = this.entries[i];

      // Verify hash
      const { hash: _stored, ...rest } = entry;
      const computed = this.computeHash(rest);
      if (computed !== entry.hash) {
        return false;
      }

      // Verify chain linkage (skip first entry in memory — it may have been evicted)
      if (i > 0 && entry.prevHash !== this.entries[i - 1].hash) {
        return false;
      }
    }

    return true;
  }

  /**
   * Get audit trail statistics.
   */
  getStats(): AuditStats {
    const decisions: Record<GovernanceDecision, number> = {
      ALLOW: 0,
      QUARANTINE: 0,
      ESCALATE: 0,
      DENY: 0,
    };

    let anomalyCount = 0;
    let replayBlockedCount = 0;
    let validationFailCount = 0;

    for (const entry of this.entries) {
      if (entry.decision) {
        decisions[entry.decision]++;
      }
      if (entry.eventType === 'anomaly') anomalyCount++;
      if (entry.eventType === 'replay_blocked') replayBlockedCount++;
      if (entry.eventType === 'validation_fail') validationFailCount++;
    }

    return {
      totalEntries: this.entries.length,
      decisions,
      anomalyCount,
      replayBlockedCount,
      validationFailCount,
      chainIntact: this.verifyChain(),
    };
  }

  /**
   * Get recent entries (most recent first).
   */
  getRecent(count: number = 10): AuditEntry[] {
    return this.entries.slice(-count).reverse();
  }

  /**
   * Get all entries.
   */
  getAll(): ReadonlyArray<AuditEntry> {
    return this.entries;
  }

  /**
   * Get the total number of entries logged (including evicted).
   */
  getTotalLogged(): number {
    return this.seq;
  }
}
