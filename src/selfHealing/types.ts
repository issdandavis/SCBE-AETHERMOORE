/**
 * @file types.ts
 * @module selfHealing/types
 * @component Self-Healing type definitions
 */

/** Structured failure information for self-healing diagnostics */
export interface Failure {
  /** Failure category (e.g., 'runtime', 'network', 'governance', 'crypto') */
  type: string;
  /** Human-readable error message */
  message: string;
  /** Stack trace, if available */
  stack?: string;
  /** Additional context for diagnostics */
  context?: Record<string, unknown>;
  /** Timestamp of failure occurrence */
  timestamp?: number;
  /** Layer where the failure originated (1-14) */
  layer?: number;
  /** Severity: how critical the failure is */
  severity?: 'low' | 'medium' | 'high' | 'critical';
}
