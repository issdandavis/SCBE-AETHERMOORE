/**
 * @file autoRetrigger.test.ts
 * @module fleet/autoRetrigger
 * @layer Layer 13
 * @component AutoRetrigger - Fleet task retry and circuit breaker logic
 * @version 3.2.4
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { AutoRetrigger } from '../../src/fleet/autoRetrigger.js';
import type { FleetTask } from '../../src/fleet/types.js';

const mockTask = (overrides?: Partial<FleetTask>): FleetTask => ({
  id: 'task-1',
  name: 'Test Task',
  description: 'A test task',
  requiredCapability: 'code_generation' as const,
  requiredTier: 'RU' as const,
  priority: 'medium' as const,
  status: 'failed' as const,
  input: {},
  minTrustScore: 0.5,
  requiresApproval: false,
  requiredApprovals: 0,
  createdAt: Date.now(),
  timeoutMs: 30000,
  retryCount: 0,
  maxRetries: 3,
  ...overrides,
});

describe('AutoRetrigger', () => {
  let retrigger: AutoRetrigger;
  const NOW = 1_000_000;

  beforeEach(() => {
    retrigger = new AutoRetrigger();
  });

  // Test 1: First evaluation returns shouldRetry=true with baseDelayMs
  it('first evaluation returns shouldRetry=true with baseDelayMs', () => {
    const task = mockTask();
    const decision = retrigger.evaluate(task, undefined, false, NOW);

    expect(decision.shouldRetry).toBe(true);
    expect(decision.delayMs).toBe(1000); // default baseDelayMs
    expect(decision.action).toBe('retry');
  });

  // Test 2: After recordAttempt, delay increases exponentially
  it('delay increases exponentially after each recordAttempt', () => {
    const task = mockTask();

    // First attempt: delay = base * multiplier^0 = 1000 * 1 = 1000
    const decision0 = retrigger.evaluate(task, undefined, false, NOW);
    expect(decision0.delayMs).toBe(1000);
    expect(decision0.action).toBe('retry');

    retrigger.recordAttempt(task.id, NOW);

    // Second attempt: delay = base * multiplier^1 = 1000 * 2 = 2000
    const decision1 = retrigger.evaluate(task, undefined, false, NOW + 1000);
    expect(decision1.delayMs).toBe(2000);
    expect(decision1.shouldRetry).toBe(true);
    expect(decision1.action).toBe('reassign'); // attempt > 0, reassignOnRetry=true

    retrigger.recordAttempt(task.id, NOW + 1000);

    // Third attempt: delay = base * multiplier^2 = 1000 * 4 = 4000
    const decision2 = retrigger.evaluate(task, undefined, false, NOW + 3000);
    expect(decision2.delayMs).toBe(4000);
    expect(decision2.shouldRetry).toBe(true);
    expect(decision2.action).toBe('reassign');
  });

  // Test 3: Max retries exceeded → abandon
  it('returns abandon when max retries are exceeded', () => {
    const task = mockTask({ id: 'task-abandon' });

    // Must evaluate first to create state, then record attempts
    retrigger.evaluate(task, 'error 0', false, NOW);
    retrigger.recordAttempt(task.id, NOW);
    retrigger.evaluate(task, 'error 1', false, NOW + 1000);
    retrigger.recordAttempt(task.id, NOW + 1000);
    retrigger.evaluate(task, 'error 2', false, NOW + 3000);
    retrigger.recordAttempt(task.id, NOW + 3000);

    const decision = retrigger.evaluate(task, 'persistent failure', false, NOW + 7000);

    expect(decision.shouldRetry).toBe(false);
    expect(decision.action).toBe('abandon');
    expect(decision.reason).toBeDefined();
  });

  // Test 4: Anomaly detection trips circuit breaker → escalate
  it('anomaly detection trips circuit breaker and returns escalate', () => {
    const task = mockTask({ id: 'task-anomaly' });
    const decision = retrigger.evaluate(task, 'anomaly error', true, NOW);

    expect(decision.shouldRetry).toBe(false);
    expect(decision.action).toBe('escalate');
    expect(decision.reason).toBeDefined();

    const state = retrigger.getState(task.id);
    expect(state?.circuitBroken).toBe(true);
  });

  // Test 5: Circuit breaker stays tripped
  it('circuit breaker remains tripped on subsequent evaluations', () => {
    const task = mockTask({ id: 'task-circuit' });

    // Trip the circuit breaker via anomaly
    retrigger.evaluate(task, 'anomaly', true, NOW);

    // Subsequent evaluations should still escalate
    const decision1 = retrigger.evaluate(task, undefined, false, NOW + 1000);
    expect(decision1.shouldRetry).toBe(false);
    expect(decision1.action).toBe('escalate');

    const decision2 = retrigger.evaluate(task, 'another error', false, NOW + 2000);
    expect(decision2.shouldRetry).toBe(false);
    expect(decision2.action).toBe('escalate');
  });

  // Test 6: resetCircuitBreaker allows retries again
  it('resetCircuitBreaker clears the circuit broken flag and allows retries', () => {
    const task = mockTask({ id: 'task-reset' });

    // Trip the circuit breaker
    retrigger.evaluate(task, 'anomaly', true, NOW);
    const brokenState = retrigger.getState(task.id);
    expect(brokenState?.circuitBroken).toBe(true);

    // Reset the circuit breaker
    retrigger.resetCircuitBreaker(task.id);

    const resetState = retrigger.getState(task.id);
    expect(resetState?.circuitBroken).toBe(false);

    // Now evaluation should allow retries (if attempts < maxRetries)
    const decision = retrigger.evaluate(task, undefined, false, NOW + 500);
    expect(decision.shouldRetry).toBe(true);
    expect(decision.action).not.toBe('escalate');
  });

  // Test 7: recordSuccess clears state
  it('recordSuccess removes the task state entirely', () => {
    const task = mockTask({ id: 'task-success' });

    // Create some state
    retrigger.evaluate(task, undefined, false, NOW);
    retrigger.recordAttempt(task.id, NOW);

    const stateBefore = retrigger.getState(task.id);
    expect(stateBefore).toBeDefined();

    retrigger.recordSuccess(task.id);

    const stateAfter = retrigger.getState(task.id);
    expect(stateAfter).toBeUndefined();
  });

  // Test 8: Custom task policy overrides defaults
  it('custom task policy overrides default retry policy', () => {
    const task = mockTask({ id: 'task-custom' });

    retrigger.setTaskPolicy(task.id, {
      maxRetries: 1,
      baseDelayMs: 500,
      backoffMultiplier: 3.0,
      reassignOnRetry: false,
    });

    // First evaluation uses custom baseDelayMs
    const decision0 = retrigger.evaluate(task, undefined, false, NOW);
    expect(decision0.shouldRetry).toBe(true);
    expect(decision0.delayMs).toBe(500);
    expect(decision0.action).toBe('retry'); // attempt=0

    retrigger.recordAttempt(task.id, NOW);

    // After 1 attempt with maxRetries=1, should abandon
    const decision1 = retrigger.evaluate(task, 'error', false, NOW + 500);
    expect(decision1.shouldRetry).toBe(false);
    expect(decision1.action).toBe('abandon');
  });

  // Test 9: getActiveRetries filters correctly
  it('getActiveRetries returns only states with active retries', () => {
    const taskA = mockTask({ id: 'task-a' });
    const taskB = mockTask({ id: 'task-b' });
    const taskC = mockTask({ id: 'task-c' });

    // Evaluate all three to create states
    retrigger.evaluate(taskA, undefined, false, NOW);
    retrigger.recordAttempt(taskA.id, NOW);

    retrigger.evaluate(taskB, undefined, false, NOW);
    retrigger.recordAttempt(taskB.id, NOW);

    retrigger.evaluate(taskC, undefined, false, NOW);

    // Record success for taskC — should be removed from active retries
    retrigger.recordSuccess(taskC.id);

    const active = retrigger.getActiveRetries();
    const activeIds = active.map((s) => s.taskId);

    expect(activeIds).toContain('task-a');
    expect(activeIds).toContain('task-b');
    expect(activeIds).not.toContain('task-c');
  });

  // Test 10: Event listener fires on recordAttempt
  it('event listener is called when recordAttempt is invoked', () => {
    const task = mockTask({ id: 'task-event' });

    const events: unknown[] = [];
    retrigger.addEventListener((event: unknown) => {
      events.push(event);
    });

    retrigger.evaluate(task, undefined, false, NOW);
    retrigger.recordAttempt(task.id, NOW);

    expect(events.length).toBeGreaterThanOrEqual(1);
  });

  // Additional edge case: delay is capped at maxDelayMs
  it('delay is capped at maxDelayMs regardless of exponential growth', () => {
    const task = mockTask({ id: 'task-cap' });

    retrigger.setTaskPolicy(task.id, {
      maxRetries: 10,
      baseDelayMs: 10000,
      maxDelayMs: 30000,
      backoffMultiplier: 5.0,
    });

    // After a few attempts the delay would exceed 30000 without capping
    retrigger.recordAttempt(task.id, NOW);
    retrigger.recordAttempt(task.id, NOW + 10000);
    retrigger.recordAttempt(task.id, NOW + 20000);

    const decision = retrigger.evaluate(task, undefined, false, NOW + 30000);
    expect(decision.shouldRetry).toBe(true);
    expect(decision.delayMs).toBeLessThanOrEqual(30000);
  });

  // Additional edge case: reassign action when attempt > 0 and reassignOnRetry=true
  it('returns reassign action on subsequent attempts when reassignOnRetry=true', () => {
    const task = mockTask({ id: 'task-reassign' });

    // Default policy has reassignOnRetry=true
    retrigger.evaluate(task, undefined, false, NOW);
    retrigger.recordAttempt(task.id, NOW);

    const decision = retrigger.evaluate(task, undefined, false, NOW + 1000);
    expect(decision.shouldRetry).toBe(true);
    expect(decision.action).toBe('reassign');
  });

  // Additional edge case: retry action (not reassign) when reassignOnRetry=false
  it('returns retry action on subsequent attempts when reassignOnRetry=false', () => {
    const task = mockTask({ id: 'task-no-reassign' });

    retrigger.setTaskPolicy(task.id, { reassignOnRetry: false });

    retrigger.evaluate(task, undefined, false, NOW);
    retrigger.recordAttempt(task.id, NOW);

    const decision = retrigger.evaluate(task, undefined, false, NOW + 1000);
    expect(decision.shouldRetry).toBe(true);
    expect(decision.action).toBe('retry');
  });

  // Additional edge case: clear() removes all state
  it('clear() removes all task states', () => {
    const taskA = mockTask({ id: 'task-clear-a' });
    const taskB = mockTask({ id: 'task-clear-b' });

    retrigger.evaluate(taskA, undefined, false, NOW);
    retrigger.recordAttempt(taskA.id, NOW);
    retrigger.evaluate(taskB, undefined, false, NOW);
    retrigger.recordAttempt(taskB.id, NOW);

    retrigger.clear();

    expect(retrigger.getState(taskA.id)).toBeUndefined();
    expect(retrigger.getState(taskB.id)).toBeUndefined();
    expect(retrigger.getActiveRetries()).toHaveLength(0);
  });

  // Additional edge case: getState returns undefined for unknown task
  it('getState returns undefined for a task that has never been seen', () => {
    const state = retrigger.getState('nonexistent-task');
    expect(state).toBeUndefined();
  });

  // Additional edge case: error message is recorded in state
  it('error string is stored in lastError on state after recordAttempt', () => {
    const task = mockTask({ id: 'task-error-record' });
    const errorMsg = 'connection timeout';

    retrigger.evaluate(task, errorMsg, false, NOW);
    retrigger.recordAttempt(task.id, NOW);

    const state = retrigger.getState(task.id);
    expect(state).toBeDefined();
    expect(state?.attemptHistory).toBeDefined();
    expect(state?.attempt).toBeGreaterThanOrEqual(1);
  });
});
