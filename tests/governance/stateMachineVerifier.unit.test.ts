/**
 * @file stateMachineVerifier.unit.test.ts
 * @module tests/governance/stateMachineVerifier
 * @layer Layer 13
 *
 * Unit tests for the StateMachineVerifier — gate pipeline and egg lifecycle.
 * Tier: L2-unit
 */

import { describe, it, expect } from 'vitest';
import {
  verify,
  reachableStates,
  absorbingStates,
  isDeterministic,
  isReachableFrom,
  createGatePipelineAutomaton,
  createEggLifecycleAutomaton,
  verifyGatePipeline,
  verifyEggLifecycle,
  type FiniteAutomaton,
} from '../../src/governance/stateMachineVerifier.js';

// ── Generic Verifier ─────────────────────────────────────────────────

describe('Generic Finite Automaton Verifier', () => {
  const trivial: FiniteAutomaton = {
    states: ['A', 'B', 'C'],
    alphabet: ['0', '1'],
    start: 'A',
    accept: ['C'],
    reject: [],
    transitions: [
      { from: 'A', symbol: '0', to: 'B' },
      { from: 'B', symbol: '1', to: 'C' },
    ],
  };

  it('computes reachable states', () => {
    const r = reachableStates(trivial);
    expect(r).toEqual(new Set(['A', 'B', 'C']));
  });

  it('finds absorbing states (no outgoing transitions)', () => {
    const a = absorbingStates(trivial);
    expect(a.has('C')).toBe(true);
    expect(a.has('A')).toBe(false);
  });

  it('detects deterministic automata', () => {
    expect(isDeterministic(trivial)).toBe(true);
  });

  it('detects non-deterministic automata', () => {
    const nfa: FiniteAutomaton = {
      ...trivial,
      transitions: [
        ...trivial.transitions,
        { from: 'A', symbol: '0', to: 'C' }, // duplicate (A, '0')
      ],
    };
    expect(isDeterministic(nfa)).toBe(false);
  });

  it('verifies a valid automaton', () => {
    const result = verify(trivial);
    expect(result.passed).toBe(true);
    expect(result.violations).toHaveLength(0);
  });

  it('reports unreachable accept states', () => {
    const fa: FiniteAutomaton = {
      states: ['A', 'B', 'ISLAND'],
      alphabet: ['x'],
      start: 'A',
      accept: ['ISLAND'], // unreachable
      transitions: [{ from: 'A', symbol: 'x', to: 'B' }],
    };
    const result = verify(fa);
    expect(result.passed).toBe(false);
    expect(result.violations.some((v) => v.invariant === 'accept_reachable')).toBe(true);
  });

  it('checks reachability between arbitrary states', () => {
    expect(isReachableFrom(trivial, 'A', 'C')).toBe(true);
    expect(isReachableFrom(trivial, 'C', 'A')).toBe(false);
  });
});

// ── Gate Pipeline ────────────────────────────────────────────────────

describe('Gate Pipeline Automaton', () => {
  const fa = createGatePipelineAutomaton();

  it('passes all safety invariants', () => {
    const result = verifyGatePipeline();
    expect(result.passed).toBe(true);
    expect(result.violations).toHaveLength(0);
  });

  it('is deterministic', () => {
    expect(isDeterministic(fa)).toBe(true);
  });

  it('DENY is absorbing', () => {
    const abs = absorbingStates(fa);
    expect(abs.has('DENY')).toBe(true);
  });

  it('HATCH is reachable from INIT', () => {
    expect(isReachableFrom(fa, 'INIT', 'HATCH')).toBe(true);
  });

  it('HATCH is NOT reachable directly from QUARANTINE', () => {
    // Must go through G5_POLICY first
    const direct = fa.transitions.some(
      (t) => t.from === 'QUARANTINE' && t.to === 'HATCH',
    );
    expect(direct).toBe(false);
  });

  it('all 5 gates must pass to reach HATCH (min path = 6 edges)', () => {
    // BFS shortest path: INIT→G1→G2→G3→G4→G5→HATCH = 6 edges
    const reached = reachableStates(fa);
    expect(reached.has('HATCH')).toBe(true);

    // Verify by checking states on the only pass path
    const passPath = ['INIT', 'G1_SYNTAX', 'G2_INTEGRITY', 'G3_QUORUM', 'G4_GEO_TIME', 'G5_POLICY', 'HATCH'];
    for (let i = 0; i < passPath.length - 1; i++) {
      const edge = fa.transitions.find(
        (t) => t.from === passPath[i] && t.symbol === 'pass' && t.to === passPath[i + 1],
      );
      expect(edge).toBeDefined();
    }
  });

  it('failure at any gate leads to DENY', () => {
    const gateStates = ['INIT', 'G1_SYNTAX', 'G2_INTEGRITY', 'G3_QUORUM', 'G4_GEO_TIME', 'G5_POLICY'];
    for (const gs of gateStates) {
      const failEdge = fa.transitions.find(
        (t) => t.from === gs && t.symbol === 'fail' && t.to === 'DENY',
      );
      expect(failEdge, `Missing fail→DENY from ${gs}`).toBeDefined();
    }
  });

  it('QUARANTINE can reach DENY via review_fail', () => {
    expect(isReachableFrom(fa, 'QUARANTINE', 'DENY')).toBe(true);
  });
});

// ── Egg Lifecycle ────────────────────────────────────────────────────

describe('Egg Lifecycle Automaton', () => {
  const fa = createEggLifecycleAutomaton();

  it('passes all safety invariants', () => {
    const result = verifyEggLifecycle();
    expect(result.passed).toBe(true);
    expect(result.violations).toHaveLength(0);
  });

  it('is deterministic', () => {
    expect(isDeterministic(fa)).toBe(true);
  });

  it('REVOKED and REJECTED are absorbing', () => {
    const abs = absorbingStates(fa);
    expect(abs.has('REVOKED')).toBe(true);
    expect(abs.has('REJECTED')).toBe(true);
  });

  it('RUNTIME is reachable from SEALED', () => {
    expect(isReachableFrom(fa, 'SEALED', 'RUNTIME')).toBe(true);
  });

  it('REVOKED is reachable from RUNTIME (policy breach)', () => {
    expect(isReachableFrom(fa, 'RUNTIME', 'REVOKED')).toBe(true);
  });

  it('ROTATING always returns to RUNTIME or REVOKED', () => {
    const rotOutgoing = fa.transitions.filter((t) => t.from === 'ROTATING');
    const targets = new Set(rotOutgoing.map((t) => t.to));
    expect(targets.has('RUNTIME')).toBe(true);
    expect(targets.has('REVOKED')).toBe(true);
    // No other targets
    expect(targets.size).toBe(2);
  });

  it('QUARANTINED can only exit via review_pass or review_deny', () => {
    const qOutgoing = fa.transitions.filter((t) => t.from === 'QUARANTINED');
    const symbols = new Set(qOutgoing.map((t) => t.symbol));
    expect(symbols).toEqual(new Set(['review_pass', 'review_deny']));
  });

  it('policy_breach from RUNTIME leads to REVOKED (not QUARANTINE)', () => {
    const edge = fa.transitions.find(
      (t) => t.from === 'RUNTIME' && t.symbol === 'policy_breach',
    );
    expect(edge?.to).toBe('REVOKED');
  });
});
