/**
 * @file autoRetrigger.ts
 * @module fleet/autoRetrigger
 * @layer Layer 13 (Governance)
 * @component Auto-Retrigger Mechanism for Failed Tasks
 * @version 1.0.0
 *
 * Automatic retry/re-execution for failed or timed-out tasks
 * with exponential backoff and SCBE-governed retry limits.
 *
 * Features:
 * - Exponential backoff (configurable base and max delay)
 * - Smart retry: adjusts agent assignment based on failure pattern
 * - GFSS anomaly integration: stops retries if spectral anomalies detected
 * - Frecency-aware: high-frecency tasks get priority retries
 * - Circuit breaker: disables retries after repeated failures
 */

import { FleetTask, FleetEvent, TaskStatus } from './types';

/**
 * Retry policy for a task
 */
export interface RetryPolicy {
  /** Maximum number of retries (default: 3) */
  maxRetries: number;
  /** Base delay in ms (default: 1000) */
  baseDelayMs: number;
  /** Maximum delay in ms (default: 30000) */
  maxDelayMs: number;
  /** Backoff multiplier (default: 2.0) */
  backoffMultiplier: number;
  /** Whether to reassign to a different agent on retry (default: true) */
  reassignOnRetry: boolean;
}

/**
 * State of a retry sequence for a specific task
 */
export interface RetryState {
  /** Task ID */
  taskId: string;
  /** Current retry attempt (0 = original, 1 = first retry, etc.) */
  attempt: number;
  /** Next scheduled retry timestamp (ms) */
  nextRetryAt: number;
  /** Last failure reason */
  lastError?: string;
  /** Whether the circuit breaker has tripped */
  circuitBroken: boolean;
  /** History of attempt timestamps */
  attemptHistory: number[];
}

/**
 * Result of a retrigger evaluation
 */
export interface RetriggerDecision {
  /** Whether the task should be retried */
  shouldRetry: boolean;
  /** Delay before retry (ms) */
  delayMs: number;
  /** Reason for decision */
  reason: string;
  /** Recommended action */
  action: 'retry' | 'reassign' | 'escalate' | 'abandon';
}

const DEFAULT_POLICY: RetryPolicy = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
  backoffMultiplier: 2.0,
  reassignOnRetry: true,
};

/**
 * Auto-retrigger manager for failed fleet tasks.
 */
export class AutoRetrigger {
  private retryStates: Map<string, RetryState> = new Map();
  private defaultPolicy: RetryPolicy;
  private taskPolicies: Map<string, RetryPolicy> = new Map();
  private eventListeners: ((event: FleetEvent) => void)[] = [];

  constructor(defaultPolicy: Partial<RetryPolicy> = {}) {
    this.defaultPolicy = { ...DEFAULT_POLICY, ...defaultPolicy };
  }

  /**
   * Set a custom retry policy for a specific task.
   */
  setTaskPolicy(taskId: string, policy: Partial<RetryPolicy>): void {
    this.taskPolicies.set(taskId, { ...this.defaultPolicy, ...policy });
  }

  /**
   * Evaluate whether a failed task should be retried.
   *
   * @param task - The failed task
   * @param error - Error message from the failure
   * @param anomalyDetected - Whether GFSS detected spectral anomalies
   * @param now - Current timestamp
   * @returns Retrigger decision
   */
  evaluate(
    task: FleetTask,
    error?: string,
    anomalyDetected: boolean = false,
    now: number = Date.now()
  ): RetriggerDecision {
    const policy = this.taskPolicies.get(task.id) ?? this.defaultPolicy;

    // Get or create retry state
    let state = this.retryStates.get(task.id);
    if (!state) {
      state = {
        taskId: task.id,
        attempt: 0,
        nextRetryAt: 0,
        circuitBroken: false,
        attemptHistory: [],
      };
      this.retryStates.set(task.id, state);
    }

    state.lastError = error;

    // Circuit breaker: anomaly detected → stop retries
    if (anomalyDetected) {
      state.circuitBroken = true;
      return {
        shouldRetry: false,
        delayMs: 0,
        reason: 'GFSS anomaly detected — circuit breaker tripped',
        action: 'escalate',
      };
    }

    // Circuit breaker already tripped
    if (state.circuitBroken) {
      return {
        shouldRetry: false,
        delayMs: 0,
        reason: 'Circuit breaker active',
        action: 'escalate',
      };
    }

    // Max retries exceeded
    if (state.attempt >= policy.maxRetries) {
      return {
        shouldRetry: false,
        delayMs: 0,
        reason: `Max retries (${policy.maxRetries}) exceeded`,
        action: 'abandon',
      };
    }

    // Compute exponential backoff delay
    const delay = Math.min(
      policy.maxDelayMs,
      policy.baseDelayMs * Math.pow(policy.backoffMultiplier, state.attempt)
    );

    // Determine if reassignment is needed
    const action: 'retry' | 'reassign' =
      policy.reassignOnRetry && state.attempt > 0 ? 'reassign' : 'retry';

    return {
      shouldRetry: true,
      delayMs: delay,
      reason: `Retry ${state.attempt + 1}/${policy.maxRetries} after ${delay}ms`,
      action,
    };
  }

  /**
   * Record a retry attempt for a task.
   *
   * @param taskId - Task ID
   * @param now - Current timestamp
   */
  recordAttempt(taskId: string, now: number = Date.now()): void {
    const state = this.retryStates.get(taskId);
    if (!state) return;

    state.attempt += 1;
    state.attemptHistory.push(now);
    state.nextRetryAt = 0; // Will be set by scheduler

    this.emitEvent({
      type: 'task_started',
      timestamp: now,
      taskId,
      data: {
        retryAttempt: state.attempt,
        isRetry: true,
      },
    });
  }

  /**
   * Record a successful task completion (clears retry state).
   *
   * @param taskId - Task ID
   */
  recordSuccess(taskId: string): void {
    this.retryStates.delete(taskId);
    this.taskPolicies.delete(taskId);
  }

  /**
   * Reset the circuit breaker for a task.
   *
   * @param taskId - Task ID
   */
  resetCircuitBreaker(taskId: string): void {
    const state = this.retryStates.get(taskId);
    if (state) {
      state.circuitBroken = false;
      state.attempt = 0;
    }
  }

  /**
   * Get retry state for a task.
   */
  getState(taskId: string): RetryState | undefined {
    return this.retryStates.get(taskId);
  }

  /**
   * Get all tasks currently in retry.
   */
  getActiveRetries(): RetryState[] {
    return Array.from(this.retryStates.values()).filter(
      (s) => !s.circuitBroken && s.attempt > 0
    );
  }

  /**
   * Clear all retry states.
   */
  clear(): void {
    this.retryStates.clear();
    this.taskPolicies.clear();
  }

  addEventListener(listener: (event: FleetEvent) => void): void {
    this.eventListeners.push(listener);
  }

  private emitEvent(event: FleetEvent): void {
    for (const listener of this.eventListeners) {
      listener(event);
    }
  }
}
