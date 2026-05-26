/**
 * @file resilience.ts
 * @module agent-bus/resilience
 *
 * Circuit breaker and retry resilience patterns for the SCBE Agent Bus.
 *
 * Research-backed: 2026 orchestration frameworks (LangGraph, AutoGen v0.4+)
 * all implement circuit breakers to prevent cascade failures when a provider
 * or model becomes unhealthy.
 *
 * Each provider gets its own circuit breaker state machine:
 *   closed   → normal operation
 *   open     → fast-fail all requests
 *   half_open → allow one probe request
 */

export type CircuitState = 'closed' | 'open' | 'half_open';

export interface CircuitBreakerOptions {
  /** Consecutive failures before opening. Default: 5 */
  failureThreshold?: number;
  /** Milliseconds to wait before attempting half-open. Default: 30000 */
  resetTimeoutMs?: number;
  /** Successes in half-open to close. Default: 2 */
  halfOpenSuccesses?: number;
}

interface CircuitBreakerRecord {
  state: CircuitState;
  failures: number;
  successes: number;
  lastFailureTime: number;
  options: Required<CircuitBreakerOptions>;
}

const DEFAULT_OPTIONS: Required<CircuitBreakerOptions> = {
  failureThreshold: 5,
  resetTimeoutMs: 30000,
  halfOpenSuccesses: 2,
};

const circuits = new Map<string, CircuitBreakerRecord>();

function getCircuit(provider: string): CircuitBreakerRecord {
  if (!circuits.has(provider)) {
    circuits.set(provider, {
      state: 'closed',
      failures: 0,
      successes: 0,
      lastFailureTime: 0,
      options: { ...DEFAULT_OPTIONS },
    });
  }
  return circuits.get(provider)!;
}

/** Configure circuit breaker thresholds for a provider. */
export function configureCircuitBreaker(provider: string, options: CircuitBreakerOptions): void {
  const existing = getCircuit(provider);
  existing.options = { ...DEFAULT_OPTIONS, ...options };
}

/** Reset a provider's circuit to closed manually. */
export function resetCircuitBreaker(provider: string): void {
  circuits.delete(provider);
}

/** Get current state for all providers. */
export function getCircuitStates(): Record<string, CircuitState> {
  const out: Record<string, CircuitState> = {};
  for (const [provider, record] of circuits) {
    out[provider] = record.state;
  }
  return out;
}

/**
 * Check whether a request should be allowed for this provider.
 * Returns true if allowed. If OPEN, returns false (caller should fast-fail).
 */
export function checkCircuit(provider: string): boolean {
  const c = getCircuit(provider);
  if (c.state === 'open') {
    const elapsed = Date.now() - c.lastFailureTime;
    if (elapsed >= c.options.resetTimeoutMs) {
      c.state = 'half_open';
      c.successes = 0;
      return true;
    }
    return false;
  }
  return true;
}

/** Record a successful call for a provider. */
export function recordSuccess(provider: string): void {
  const c = getCircuit(provider);
  if (c.state === 'half_open') {
    c.successes++;
    if (c.successes >= c.options.halfOpenSuccesses) {
      c.state = 'closed';
      c.failures = 0;
      c.successes = 0;
    }
  } else if (c.state === 'closed') {
    c.failures = 0;
  }
}

/** Record a failed call for a provider. */
export function recordFailure(provider: string): void {
  const c = getCircuit(provider);
  c.failures++;
  c.lastFailureTime = Date.now();
  if (c.state === 'half_open') {
    c.state = 'open';
  } else if (c.state === 'closed' && c.failures >= c.options.failureThreshold) {
    c.state = 'open';
  }
}

/**
 * Execute a function under circuit breaker protection.
 * Throws if the circuit is OPEN.
 */
export async function withCircuitBreaker<T>(provider: string, fn: () => Promise<T>): Promise<T> {
  if (!checkCircuit(provider)) {
    throw new Error(`circuit ${provider} OPEN`);
  }
  try {
    const result = await fn();
    recordSuccess(provider);
    return result;
  } catch (err) {
    recordFailure(provider);
    throw err;
  }
}
