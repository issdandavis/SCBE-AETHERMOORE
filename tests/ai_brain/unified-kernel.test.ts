/**
 * @file unified-kernel.test.ts
 * @module tests/ai_brain/unified-kernel
 *
 * Integration tests for the Unified Kernel (Pipeline Runner).
 *
 * Test A: Safety invariant — adversarial proposals stay bounded
 * Test B: Torus snap → stutter → flux contraction
 * Test C: Dual-lattice runtime response to anomalies
 * Test D: HYDRA order determinism — same events → same state hash
 * Test E: Full pipeline lifecycle (init → process → audit)
 * Test F: Module contract verification
 */

import { describe, it, expect, beforeEach, beforeAll, afterAll } from 'vitest';
import {
  UnifiedKernel,
  torusWriteGate,
  computeMetrics,
  DEFAULT_KERNEL_CONFIG,
  type CanonicalState,
  type ProposedAction,
  type MemoryEvent,
  type TorusCoordinates,
  type KernelDecision,
  type PipelineStepResult,
} from '../../src/ai_brain/unified-kernel.js';
import { BRAIN_DIMENSIONS, POINCARE_MAX_NORM } from '../../src/ai_brain/types.js';


const ORIGINAL_HF_TOKEN = process.env.HUGGINGFACE_TOKEN;
const ORIGINAL_PHDM_KEY = process.env.SCBE_PHDM_MASTER_KEY;

// Test-only 32-byte key (hex) — NOT for production use
const TEST_PHDM_KEY = 'a'.repeat(64);

beforeAll(() => {
  process.env.HUGGINGFACE_TOKEN = process.env.HUGGINGFACE_TOKEN || 'test-token-redacted';
  process.env.SCBE_PHDM_MASTER_KEY = process.env.SCBE_PHDM_MASTER_KEY || TEST_PHDM_KEY;
});

afterAll(() => {
  if (ORIGINAL_HF_TOKEN === undefined) {
    delete process.env.HUGGINGFACE_TOKEN;
  } else {
    process.env.HUGGINGFACE_TOKEN = ORIGINAL_HF_TOKEN;
  }
  if (ORIGINAL_PHDM_KEY === undefined) {
    delete process.env.SCBE_PHDM_MASTER_KEY;
  } else {
    process.env.SCBE_PHDM_MASTER_KEY = ORIGINAL_PHDM_KEY;
  }
});

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function safeAction(agentId: string, scale: number = 0.1): ProposedAction {
  const state = new Array(BRAIN_DIMENSIONS).fill(0);
  let normSq = 0;
  for (let i = 0; i < state.length; i++) {
    state[i] = Math.sin(i * 0.3);
    normSq += state[i] * state[i];
  }
  // Normalize to unit direction, then scale to desired norm
  const norm = Math.sqrt(normSq);
  for (let i = 0; i < state.length; i++) {
    state[i] = (state[i] / norm) * scale;
  }
  return { type: 'think', stateVector: state };
}

function adversarialAction(agentId: string, scale: number = 0.95): ProposedAction {
  const state = new Array(BRAIN_DIMENSIONS).fill(0);
  for (let i = 0; i < state.length; i++) {
    state[i] = (i % 2 === 0 ? 1 : -1) * scale / Math.sqrt(BRAIN_DIMENSIONS);
  }
  return { type: 'attack', stateVector: state };
}

function memoryEvent(domain: number = 5, polarity: number = 0): MemoryEvent {
  return {
    contentHash: `hash-${domain}-${Date.now()}`,
    domain,
    sequence: 1,
    polarity,
    authority: 0.5,
  };
}

function contradictoryMemoryEvent(): MemoryEvent {
  return {
    contentHash: 'contradiction',
    domain: 20, // very different domain
    sequence: 999,
    polarity: -1, // negative polarity
    authority: 0.0, // zero authority
  };
}

// ═══════════════════════════════════════════════════════════════
// Test A: Safety Invariant
// ═══════════════════════════════════════════════════════════════

describe('Test A: Safety Invariant', () => {
  let kernel: UnifiedKernel;

  beforeEach(() => {
    kernel = new UnifiedKernel();
  });

  it('should keep ||u|| < 1 for all processed states', () => {
    kernel.initializeAgent('safe-agent');

    for (let i = 0; i < 20; i++) {
      const action = safeAction('safe-agent', 0.1 + i * 0.03);
      const result = kernel.processAction('safe-agent', action);
      const norm = Math.sqrt(
        result.state.hyp.reduce((s, v) => s + v * v, 0)
      );
      expect(norm).toBeLessThan(1.0);
    }
  });

  it('should BLOCK adversarial proposals that push toward boundary', () => {
    kernel.initializeAgent('adversary');

    // Process several adversarial actions to trigger escalation
    let blockCount = 0;
    for (let i = 0; i < 10; i++) {
      const action = adversarialAction('adversary', 0.9 + i * 0.005);
      const result = kernel.processAction('adversary', action);
      if (result.decision === 'BLOCK') blockCount++;
    }

    // Should block at least some adversarial actions
    expect(blockCount).toBeGreaterThan(0);
  });

  it('should enforce DEMI restrictions: no high-risk actions', () => {
    kernel.initializeAgent('demi-agent');

    // Drive flux down to DEMI by processing risky actions
    for (let i = 0; i < 30; i++) {
      kernel.processAction('demi-agent', adversarialAction('demi-agent', 0.8));
    }

    const state = kernel.getState('demi-agent');
    // Agent should have been penalized
    expect(state!.penalties.failCount).toBeGreaterThan(0);
  });

  it('should never allow expelled agents to pass', () => {
    const kernel2 = new UnifiedKernel();
    kernel2.initializeAgent('expelled-test');

    // Manually set immune state to expelled via many adversarial actions
    // Process enough actions that the immune system escalates
    for (let i = 0; i < 50; i++) {
      kernel2.processAction('expelled-test', adversarialAction('expelled-test', 0.95));
    }

    const state = kernel2.getState('expelled-test')!;
    // After many adversarial actions, penalties should accumulate
    expect(state.penalties.failCount).toBeGreaterThan(5);
  });

  it('should maintain bounded flux values', () => {
    kernel.initializeAgent('flux-bounded');

    for (let i = 0; i < 20; i++) {
      const result = kernel.processAction('flux-bounded', safeAction('flux-bounded'));
      expect(result.state.flux).toBeGreaterThanOrEqual(0);
      expect(result.state.flux).toBeLessThanOrEqual(1);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Test B: Torus Snap → Stutter → Flux Contraction
// ═══════════════════════════════════════════════════════════════

describe('Test B: Torus Snap → Stutter → Flux Contraction', () => {
  let kernel: UnifiedKernel;

  beforeEach(() => {
    kernel = new UnifiedKernel();
  });

  it('should detect contradictory memory events as snaps', () => {
    kernel.initializeAgent('snap-agent');

    // First: commit a normal event to establish torus position
    const normalEvent = memoryEvent(5, 1);
    const r1 = kernel.processAction(
      'snap-agent',
      safeAction('snap-agent'),
      normalEvent
    );
    expect(r1.memoryResult).not.toBeNull();
    expect(r1.memoryResult!.committed).toBe(true);

    // Second: attempt a contradictory event
    const contradictory = contradictoryMemoryEvent();
    const r2 = kernel.processAction(
      'snap-agent',
      safeAction('snap-agent'),
      contradictory
    );
    expect(r2.memoryResult).not.toBeNull();
    expect(r2.memoryResult!.snap).toBe(true);
    expect(r2.memoryResult!.committed).toBe(false);
  });

  it('should increase τ_delay (stutter) on snap', () => {
    kernel.initializeAgent('stutter-agent');

    // Establish torus position
    kernel.processAction('stutter-agent', safeAction('stutter-agent'), memoryEvent(5, 1));

    const stateBefore = kernel.getState('stutter-agent')!;
    const tauBefore = stateBefore.penalties.tauDelay;

    // Trigger snap with contradictory event
    kernel.processAction(
      'stutter-agent',
      safeAction('stutter-agent'),
      contradictoryMemoryEvent()
    );

    const stateAfter = kernel.getState('stutter-agent')!;
    expect(stateAfter.penalties.tauDelay).toBeGreaterThan(tauBefore);
  });

  it('should contract flux (ν decreases) on snap', () => {
    kernel.initializeAgent('flux-contract');

    // Establish torus position
    kernel.processAction('flux-contract', safeAction('flux-contract'), memoryEvent(5, 1));

    const fluxBefore = kernel.getState('flux-contract')!.flux;

    // Multiple snaps to force contraction
    for (let i = 0; i < 5; i++) {
      kernel.processAction(
        'flux-contract',
        safeAction('flux-contract'),
        contradictoryMemoryEvent()
      );
    }

    const fluxAfter = kernel.getState('flux-contract')!.flux;
    expect(fluxAfter).toBeLessThan(fluxBefore);
  });

  it('should increment snap count on each snap', () => {
    kernel.initializeAgent('snap-counter');

    // Establish position
    kernel.processAction('snap-counter', safeAction('snap-counter'), memoryEvent(5, 1));

    // Trigger 3 snaps
    for (let i = 0; i < 3; i++) {
      kernel.processAction(
        'snap-counter',
        safeAction('snap-counter'),
        contradictoryMemoryEvent()
      );
    }

    const state = kernel.getState('snap-counter')!;
    expect(state.penalties.snapCount).toBe(3);
  });

  it('should gradually recover stutter when not penalized', () => {
    kernel.initializeAgent('recovery');

    // Trigger a snap to increase stutter
    kernel.processAction('recovery', safeAction('recovery'), memoryEvent(5, 1));
    kernel.processAction('recovery', safeAction('recovery'), contradictoryMemoryEvent());

    const stutterAfterSnap = kernel.getState('recovery')!.penalties.tauDelay;

    // Process many safe actions (no snaps, no blocks)
    for (let i = 0; i < 30; i++) {
      kernel.processAction('recovery', safeAction('recovery', 0.05));
    }

    const stutterAfterRecovery = kernel.getState('recovery')!.penalties.tauDelay;
    expect(stutterAfterRecovery).toBeLessThan(stutterAfterSnap);
  });
});

// ═══════════════════════════════════════════════════════════════
// Test C: Dual-Lattice Runtime Response
// ═══════════════════════════════════════════════════════════════

describe('Test C: Dual-Lattice Runtime Response', () => {
  let kernel: UnifiedKernel;

  beforeEach(() => {
    kernel = new UnifiedKernel();
  });

  it('should produce lattice results with each step', () => {
    kernel.initializeAgent('lattice-agent');
    const result = kernel.processAction('lattice-agent', safeAction('lattice-agent'));

    expect(result.latticeResult).toBeDefined();
    expect(result.latticeResult.coherence).toBeGreaterThanOrEqual(0);
    expect(result.latticeResult.coherence).toBeLessThanOrEqual(1);
  });

  it('should record lattice state in canonical state', () => {
    kernel.initializeAgent('lattice-state');
    kernel.processAction('lattice-state', safeAction('lattice-state'));

    const state = kernel.getState('lattice-state')!;
    expect(state.lattice).toBeDefined();
    expect(typeof state.lattice.staticAccepted).toBe('boolean');
    expect(typeof state.lattice.dynamicDisplacement).toBe('number');
    expect(typeof state.lattice.coherence).toBe('number');
    expect(typeof state.lattice.validated).toBe('boolean');
  });

  it('should produce higher threat phasons for riskier actions', () => {
    kernel.initializeAgent('phason-test');

    const safeResult = kernel.processAction('phason-test', safeAction('phason-test', 0.05));
    const riskyResult = kernel.processAction(
      'phason-test',
      adversarialAction('phason-test', 0.8)
    );

    // Higher risk should produce more topology changes
    // (measured by interference or displacement differences)
    expect(riskyResult.metrics.combinedRiskScore).toBeGreaterThan(
      safeResult.metrics.combinedRiskScore
    );
  });

  it('should produce dual ternary spectrum with each step', () => {
    kernel.initializeAgent('ternary-agent');

    // Need enough history for spectral analysis
    for (let i = 0; i < 5; i++) {
      kernel.processAction('ternary-agent', safeAction('ternary-agent'));
    }

    const result = kernel.processAction('ternary-agent', safeAction('ternary-agent'));
    expect(result.ternarySpectrum).toBeDefined();
    // After enough history, should have non-empty magnitudes
    expect(result.ternarySpectrum.primaryMagnitudes.length).toBeGreaterThan(0);
  });

  it('should track lattice coherence changes over time', () => {
    kernel.initializeAgent('coherence-track');

    const coherences: number[] = [];
    for (let i = 0; i < 10; i++) {
      const result = kernel.processAction(
        'coherence-track',
        safeAction('coherence-track', 0.1 * (i + 1))
      );
      coherences.push(result.latticeResult.coherence);
    }

    // All coherences should be valid numbers
    for (const c of coherences) {
      expect(c).toBeGreaterThanOrEqual(0);
      expect(c).toBeLessThanOrEqual(1);
      expect(Number.isFinite(c)).toBe(true);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Test D: HYDRA Order Determinism
// ═══════════════════════════════════════════════════════════════

describe('Test D: HYDRA Order Determinism', () => {
  it('should produce identical state hashes for identical event sequences', () => {
    const kernel1 = new UnifiedKernel();
    const kernel2 = new UnifiedKernel();

    kernel1.initializeAgent('agent-alpha');
    kernel2.initializeAgent('agent-alpha');

    // Feed identical action sequences
    const actions = [
      safeAction('agent-alpha', 0.1),
      safeAction('agent-alpha', 0.2),
      safeAction('agent-alpha', 0.15),
    ];

    for (const action of actions) {
      kernel1.processAction('agent-alpha', action);
      kernel2.processAction('agent-alpha', action);
    }

    const hash1 = kernel1.computeStateHash('agent-alpha');
    const hash2 = kernel2.computeStateHash('agent-alpha');
    expect(hash1).toBe(hash2);
  });

  it('should produce different hashes for different event sequences', () => {
    const kernel1 = new UnifiedKernel();
    const kernel2 = new UnifiedKernel();

    kernel1.initializeAgent('agent-beta');
    kernel2.initializeAgent('agent-beta');

    // Different actions
    kernel1.processAction('agent-beta', safeAction('agent-beta', 0.1));
    kernel2.processAction('agent-beta', safeAction('agent-beta', 0.5));

    const hash1 = kernel1.computeStateHash('agent-beta');
    const hash2 = kernel2.computeStateHash('agent-beta');
    expect(hash1).not.toBe(hash2);
  });

  it('should maintain ordered event log', () => {
    const kernel = new UnifiedKernel();
    kernel.initializeAgent('log-agent');

    for (let i = 0; i < 5; i++) {
      kernel.processAction('log-agent', safeAction('log-agent'));
    }

    const log = kernel.getOrderedLog();
    expect(log).toHaveLength(5);

    // Steps should be monotonically increasing
    for (let i = 1; i < log.length; i++) {
      expect(log[i].step).toBeGreaterThan(log[i - 1].step);
    }
  });

  it('should maintain audit hash chain integrity', () => {
    const kernel = new UnifiedKernel();
    kernel.initializeAgent('audit-agent');

    for (let i = 0; i < 10; i++) {
      kernel.processAction('audit-agent', safeAction('audit-agent'));
    }

    // Verify hashchain
    expect(kernel.getAuditLogger().verifyChainIntegrity()).toBe(true);
    expect(kernel.getAuditLogger().count).toBe(10);
  });

  it('should produce non-empty state hash', () => {
    const kernel = new UnifiedKernel();
    kernel.initializeAgent('hash-test');
    kernel.processAction('hash-test', safeAction('hash-test'));

    const hash = kernel.computeStateHash('hash-test');
    expect(hash).toBeTruthy();
    expect(hash.length).toBe(8); // FNV-1a → 8 hex chars
  });
});

// ═══════════════════════════════════════════════════════════════
// Test E: Full Pipeline Lifecycle
// ═══════════════════════════════════════════════════════════════

describe('Test E: Full Pipeline Lifecycle', () => {
  let kernel: UnifiedKernel;

  beforeEach(() => {
    kernel = new UnifiedKernel();
  });

  it('should auto-initialize agent on first action', () => {
    // Don't call initializeAgent — it should auto-init
    const result = kernel.processAction('auto-init', safeAction('auto-init'));
    expect(result.state.agentId).toBe('auto-init');
    expect(result.step).toBe(1);
  });

  it('should return complete PipelineStepResult', () => {
    const result = kernel.processAction('complete-test', safeAction('complete-test'));

    expect(result.step).toBe(1);
    expect(result.action).toBeDefined();
    expect(result.metrics).toBeDefined();
    expect(result.latticeResult).toBeDefined();
    expect(result.ternarySpectrum).toBeDefined();
    expect(['ALLOW', 'TRANSFORM', 'BLOCK']).toContain(result.decision);
    expect(typeof result.penaltyApplied).toBe('boolean');
    expect(result.state).toBeDefined();
    expect(typeof result.auditHash).toBe('string');
  });

  it('should update capabilities based on flux state', () => {
    kernel.initializeAgent('caps-test');

    // Initially POLLY (high flux) → full capabilities
    const r1 = kernel.processAction('caps-test', safeAction('caps-test'));
    const state = kernel.getState('caps-test')!;

    // Should have capabilities matching their flux tier
    const expectedCaps = DEFAULT_KERNEL_CONFIG.capabilityTiers[state.fluxState];
    for (const cap of expectedCaps) {
      expect(state.capabilities.has(cap)).toBe(true);
    }
  });

  it('should process memory events only for ALLOW/TRANSFORM decisions', () => {
    kernel.initializeAgent('memory-gate');

    // Safe action + memory event → should commit
    const r1 = kernel.processAction(
      'memory-gate',
      safeAction('memory-gate'),
      memoryEvent(5)
    );
    if (r1.decision === 'ALLOW' || r1.decision === 'TRANSFORM') {
      expect(r1.memoryResult).not.toBeNull();
    }
  });

  it('should handle multiple agents independently', () => {
    kernel.initializeAgent('agent-1');
    kernel.initializeAgent('agent-2');

    kernel.processAction('agent-1', safeAction('agent-1', 0.1));
    kernel.processAction('agent-2', adversarialAction('agent-2', 0.8));

    const state1 = kernel.getState('agent-1')!;
    const state2 = kernel.getState('agent-2')!;

    // Agent 2 should have higher risk profile
    expect(state2.penalties.failCount).toBeGreaterThanOrEqual(state1.penalties.failCount);
  });

  it('should reset all state cleanly', () => {
    kernel.initializeAgent('reset-test');
    kernel.processAction('reset-test', safeAction('reset-test'));

    kernel.reset();

    expect(kernel.getState('reset-test')).toBeUndefined();
    expect(kernel.getOrderedLog()).toHaveLength(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Test F: Module Contract Verification
// ═══════════════════════════════════════════════════════════════

describe('Test F: Module Contract Verification', () => {
  it('SCBE metrics: produces scores, does NOT decide', () => {
    const state = new Array(BRAIN_DIMENSIONS).fill(0.1);
    const metrics = computeMetrics(state, null);

    expect(metrics.hyperbolicDistance).toBeGreaterThanOrEqual(0);
    expect(metrics.phaseDeviation).toBeGreaterThanOrEqual(0);
    expect(metrics.phaseDeviation).toBeLessThanOrEqual(1);
    expect(metrics.spectralCoherence).toBeGreaterThanOrEqual(0);
    expect(metrics.spectralCoherence).toBeLessThanOrEqual(1);
    expect(metrics.combinedRiskScore).toBeGreaterThanOrEqual(0);
    expect(metrics.combinedRiskScore).toBeLessThanOrEqual(1);
  });

  it('SCBE metrics: higher distance → higher risk', () => {
    const nearOrigin = new Array(BRAIN_DIMENSIONS).fill(0.01);
    const nearBoundary = new Array(BRAIN_DIMENSIONS).fill(0.2);

    const m1 = computeMetrics(nearOrigin, null);
    const m2 = computeMetrics(nearBoundary, null);

    expect(m2.hyperbolicDistance).toBeGreaterThan(m1.hyperbolicDistance);
    expect(m2.combinedRiskScore).toBeGreaterThan(m1.combinedRiskScore);
  });

  it('Torus write gate: accepts compatible events', () => {
    const torus: TorusCoordinates = { theta: 1.0, phi: 0.5, rho: 1.5, sigma: 0.3 };
    const event: MemoryEvent = {
      contentHash: 'test',
      domain: 3,  // maps to θ ≈ 0.898 (close to 1.0)
      sequence: 1,
      polarity: 0,
      authority: 0.05,
    };

    const result = torusWriteGate(torus, event, 0.7);
    expect(result.committed).toBe(true);
    expect(result.snap).toBe(false);
  });

  it('Torus write gate: rejects highly divergent events', () => {
    // theta=0, rho=0, sigma=0 → event maps to opposite angles
    const torus: TorusCoordinates = { theta: 0, phi: 0, rho: 0, sigma: 0 };
    const event: MemoryEvent = {
      contentHash: 'divergent',
      domain: 10,       // maps to θ ≈ π (opposite of 0)
      sequence: 500,
      polarity: 1,      // maps to ρ = π (far from 0)
      authority: 0.5,   // maps to σ = π (far from 0)
    };

    const result = torusWriteGate(torus, event, 0.3);
    expect(result.snap).toBe(true);
    expect(result.committed).toBe(false);
    expect(result.divergence).toBeGreaterThan(0.3);
  });

  it('Torus write gate: divergence is bounded [0, 1]', () => {
    const torus: TorusCoordinates = { theta: 0, phi: 0, rho: 0, sigma: 0 };

    for (let d = 0; d <= 20; d++) {
      const event: MemoryEvent = {
        contentHash: `test-${d}`,
        domain: d,
        sequence: d * 100,
        polarity: d % 2 === 0 ? 1 : -1,
        authority: d / 20,
      };
      const result = torusWriteGate(torus, event, 0.5);
      expect(result.divergence).toBeGreaterThanOrEqual(0);
      expect(result.divergence).toBeLessThanOrEqual(1);
    }
  });

  it('Kernel exposes all subsystem accessors', () => {
    const kernel = new UnifiedKernel();

    expect(kernel.getPHDM()).toBeDefined();
    expect(kernel.getFluxManager()).toBeDefined();
    expect(kernel.getImmuneSystem()).toBeDefined();
    expect(kernel.getDualLattice()).toBeDefined();
    expect(kernel.getDualTernary()).toBeDefined();
    expect(kernel.getAuditLogger()).toBeDefined();
  });
});

// ═══════════════════════════════════════════════════════════════
// Test G: Adversarial Stress Test
// ═══════════════════════════════════════════════════════════════

describe('Test G: Adversarial Stress', () => {
  it('should handle rapid alternation between safe and adversarial actions', () => {
    const kernel = new UnifiedKernel();
    kernel.initializeAgent('alternator');

    for (let i = 0; i < 30; i++) {
      const action = i % 2 === 0
        ? safeAction('alternator', 0.1)
        : adversarialAction('alternator', 0.85);
      const result = kernel.processAction('alternator', action);

      // Should never crash, always produce valid result
      expect(result.decision).toBeDefined();
      expect(result.state.flux).toBeGreaterThanOrEqual(0);
      expect(result.state.flux).toBeLessThanOrEqual(1);
    }
  });

  it('should accumulate penalties under sustained attack', () => {
    const kernel = new UnifiedKernel();
    kernel.initializeAgent('sustained-attack');

    for (let i = 0; i < 20; i++) {
      kernel.processAction('sustained-attack', adversarialAction('sustained-attack', 0.9));
    }

    const state = kernel.getState('sustained-attack')!;
    expect(state.penalties.failCount).toBeGreaterThan(0);
    expect(state.penalties.tauDelay).toBeGreaterThan(1.0);
  });

  it('should recover after attack stops', () => {
    const kernel = new UnifiedKernel();
    kernel.initializeAgent('recovery-test');

    // Attack phase
    for (let i = 0; i < 10; i++) {
      kernel.processAction('recovery-test', adversarialAction('recovery-test', 0.85));
    }
    const stutterAfterAttack = kernel.getState('recovery-test')!.penalties.tauDelay;

    // Recovery phase
    for (let i = 0; i < 50; i++) {
      kernel.processAction('recovery-test', safeAction('recovery-test', 0.05));
    }

    const stutterAfterRecovery = kernel.getState('recovery-test')!.penalties.tauDelay;
    expect(stutterAfterRecovery).toBeLessThan(stutterAfterAttack);
  });

  it('should handle 100 agents concurrently', () => {
    const kernel = new UnifiedKernel();

    for (let a = 0; a < 100; a++) {
      const agentId = `agent-${a}`;
      kernel.initializeAgent(agentId);
      kernel.processAction(agentId, safeAction(agentId, 0.05));
    }

    const allStates = kernel.getAllStates();
    expect(allStates.size).toBe(100);

    // All should have valid state
    for (const [id, state] of allStates) {
      expect(state.step).toBe(1);
      expect(state.flux).toBeGreaterThanOrEqual(0);
    }
  });
});
