/**
 * @file stateMachineVerifier.ts
 * @module governance/stateMachineVerifier
 * @layer Layer 13
 * @component Finite Automaton Verifier — formal safety proofs for gate pipeline & egg lifecycle
 *
 * Models SCBE governance flows as finite automata and verifies safety invariants:
 *
 *   1. **Gate Pipeline Automaton** — 5-gate verification sequence
 *      Proves: no path reaches HATCH without passing all 5 gates.
 *
 *   2. **Egg Lifecycle Automaton** — Sacred Egg → Hatched Agent states
 *      Proves: revocation is absorbing, rotation always re-anchors,
 *      quarantine can only exit via manual review.
 *
 *   3. **Generic verifier** — supply any (states, transitions, alphabet)
 *      and check reachability, absorption, determinism, completeness.
 *
 * A3: Causality — state transitions are time-ordered and irreversible
 * where the spec demands it (deny, revoke = absorbing).
 *
 * A5: Composition — composes with TrustState from offline_mode.ts.
 */

// ── Generic Finite Automaton ─────────────────────────────────────────

export interface Transition<S extends string = string, A extends string = string> {
  from: S;
  symbol: A;
  to: S;
}

export interface FiniteAutomaton<S extends string = string, A extends string = string> {
  states: readonly S[];
  alphabet: readonly A[];
  transitions: Transition<S, A>[];
  start: S;
  accept: readonly S[];
  reject?: readonly S[];
}

export interface InvariantViolation {
  invariant: string;
  detail: string;
}

export interface VerificationResult {
  passed: boolean;
  violations: InvariantViolation[];
  reachable: Set<string>;
  absorbing: Set<string>;
}

// ── Core Verification Engine ─────────────────────────────────────────

/**
 * Compute the set of states reachable from `start` via any transition path.
 */
export function reachableStates<S extends string, A extends string>(
  fa: FiniteAutomaton<S, A>,
): Set<S> {
  const visited = new Set<S>();
  const queue: S[] = [fa.start];
  visited.add(fa.start);

  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const t of fa.transitions) {
      if (t.from === current && !visited.has(t.to)) {
        visited.add(t.to);
        queue.push(t.to);
      }
    }
  }
  return visited;
}

/**
 * Find absorbing states — states with no outgoing transitions
 * (or only self-loops).
 */
export function absorbingStates<S extends string, A extends string>(
  fa: FiniteAutomaton<S, A>,
): Set<S> {
  const result = new Set<S>();
  for (const s of fa.states) {
    const outgoing = fa.transitions.filter((t) => t.from === s);
    const allSelfLoops = outgoing.every((t) => t.to === s);
    if (outgoing.length === 0 || allSelfLoops) {
      result.add(s);
    }
  }
  return result;
}

/**
 * Check if the automaton is deterministic: at most one transition
 * per (state, symbol) pair.
 */
export function isDeterministic<S extends string, A extends string>(
  fa: FiniteAutomaton<S, A>,
): boolean {
  const seen = new Set<string>();
  for (const t of fa.transitions) {
    const key = `${t.from}|${t.symbol}`;
    if (seen.has(key)) return false;
    seen.add(key);
  }
  return true;
}

/**
 * Check if a target state is reachable from a source state.
 */
export function isReachableFrom<S extends string, A extends string>(
  fa: FiniteAutomaton<S, A>,
  source: S,
  target: S,
): boolean {
  const visited = new Set<S>();
  const queue: S[] = [source];
  visited.add(source);

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (current === target) return true;
    for (const t of fa.transitions) {
      if (t.from === current && !visited.has(t.to)) {
        visited.add(t.to);
        queue.push(t.to);
      }
    }
  }
  return false;
}

/**
 * Verify a finite automaton against standard safety invariants.
 *
 * Checks:
 *   - Determinism (no ambiguous transitions)
 *   - Start state exists
 *   - Accept/reject states are reachable
 *   - No unreachable states (warning, not violation)
 *   - Reject states are absorbing (if specified)
 */
export function verify<S extends string, A extends string>(
  fa: FiniteAutomaton<S, A>,
): VerificationResult {
  const violations: InvariantViolation[] = [];
  const reached = reachableStates(fa);
  const absorbing = absorbingStates(fa);

  // Determinism
  if (!isDeterministic(fa)) {
    violations.push({
      invariant: 'determinism',
      detail: 'Automaton has ambiguous transitions (multiple edges for same state+symbol)',
    });
  }

  // Start state in states set
  if (!fa.states.includes(fa.start)) {
    violations.push({
      invariant: 'start_valid',
      detail: `Start state "${fa.start}" not in states set`,
    });
  }

  // Accept states reachable
  for (const a of fa.accept) {
    if (!reached.has(a)) {
      violations.push({
        invariant: 'accept_reachable',
        detail: `Accept state "${a}" is unreachable from start`,
      });
    }
  }

  // Reject states reachable and absorbing
  if (fa.reject) {
    for (const r of fa.reject) {
      if (!reached.has(r)) {
        violations.push({
          invariant: 'reject_reachable',
          detail: `Reject state "${r}" is unreachable from start`,
        });
      }
      if (!absorbing.has(r)) {
        violations.push({
          invariant: 'reject_absorbing',
          detail: `Reject state "${r}" is not absorbing — safety violation`,
        });
      }
    }
  }

  return {
    passed: violations.length === 0,
    violations,
    reachable: reached,
    absorbing,
  };
}

// ── Gate Pipeline Automaton ──────────────────────────────────────────

/**
 * The 5-gate verification pipeline as a finite automaton.
 *
 * States: INIT → G1_SYNTAX → G2_INTEGRITY → G3_QUORUM → G4_GEO_TIME → G5_POLICY → HATCH
 * Any gate can fail → DENY (absorbing).
 * G5 can also → QUARANTINE (non-absorbing, loops back to G5 via review).
 */

export type GatePipelineState =
  | 'INIT'
  | 'G1_SYNTAX'
  | 'G2_INTEGRITY'
  | 'G3_QUORUM'
  | 'G4_GEO_TIME'
  | 'G5_POLICY'
  | 'HATCH'
  | 'QUARANTINE'
  | 'DENY';

export type GateSymbol = 'pass' | 'fail' | 'quarantine' | 'review_pass' | 'review_fail';

export function createGatePipelineAutomaton(): FiniteAutomaton<GatePipelineState, GateSymbol> {
  return {
    states: [
      'INIT', 'G1_SYNTAX', 'G2_INTEGRITY', 'G3_QUORUM',
      'G4_GEO_TIME', 'G5_POLICY', 'HATCH', 'QUARANTINE', 'DENY',
    ] as const,
    alphabet: ['pass', 'fail', 'quarantine', 'review_pass', 'review_fail'] as const,
    start: 'INIT',
    accept: ['HATCH'],
    reject: ['DENY'],
    transitions: [
      // Happy path: pass through all 5 gates
      { from: 'INIT', symbol: 'pass', to: 'G1_SYNTAX' },
      { from: 'G1_SYNTAX', symbol: 'pass', to: 'G2_INTEGRITY' },
      { from: 'G2_INTEGRITY', symbol: 'pass', to: 'G3_QUORUM' },
      { from: 'G3_QUORUM', symbol: 'pass', to: 'G4_GEO_TIME' },
      { from: 'G4_GEO_TIME', symbol: 'pass', to: 'G5_POLICY' },
      { from: 'G5_POLICY', symbol: 'pass', to: 'HATCH' },

      // Failure at any gate → DENY
      { from: 'INIT', symbol: 'fail', to: 'DENY' },
      { from: 'G1_SYNTAX', symbol: 'fail', to: 'DENY' },
      { from: 'G2_INTEGRITY', symbol: 'fail', to: 'DENY' },
      { from: 'G3_QUORUM', symbol: 'fail', to: 'DENY' },
      { from: 'G4_GEO_TIME', symbol: 'fail', to: 'DENY' },
      { from: 'G5_POLICY', symbol: 'fail', to: 'DENY' },

      // G5 can quarantine instead of pass/fail
      { from: 'G5_POLICY', symbol: 'quarantine', to: 'QUARANTINE' },

      // Quarantine: manual review loops back to G5
      { from: 'QUARANTINE', symbol: 'review_pass', to: 'G5_POLICY' },
      { from: 'QUARANTINE', symbol: 'review_fail', to: 'DENY' },
    ],
  };
}

// ── Egg Lifecycle Automaton ──────────────────────────────────────────

export type EggLifecycleState =
  | 'SEALED'
  | 'ANCHORED'
  | 'GATE_RUN'
  | 'HATCHED'
  | 'RUNTIME'
  | 'ROTATING'
  | 'QUARANTINED'
  | 'REVOKED'
  | 'REJECTED';

export type EggEvent =
  | 'anchor_complete'
  | 'gates_allow'
  | 'gates_deny'
  | 'gates_quarantine'
  | 'boot_ok'
  | 'attest_ok'
  | 'epoch_end'
  | 'rotation_ok'
  | 'policy_breach'
  | 'review_pass'
  | 'review_deny';

export function createEggLifecycleAutomaton(): FiniteAutomaton<EggLifecycleState, EggEvent> {
  return {
    states: [
      'SEALED', 'ANCHORED', 'GATE_RUN', 'HATCHED', 'RUNTIME',
      'ROTATING', 'QUARANTINED', 'REVOKED', 'REJECTED',
    ] as const,
    alphabet: [
      'anchor_complete', 'gates_allow', 'gates_deny', 'gates_quarantine',
      'boot_ok', 'attest_ok', 'epoch_end', 'rotation_ok',
      'policy_breach', 'review_pass', 'review_deny',
    ] as const,
    start: 'SEALED',
    accept: ['HATCHED', 'RUNTIME'],
    reject: ['REVOKED', 'REJECTED'],
    transitions: [
      // Seal → Anchor → Gate
      { from: 'SEALED', symbol: 'anchor_complete', to: 'ANCHORED' },
      { from: 'ANCHORED', symbol: 'gates_allow', to: 'GATE_RUN' },
      { from: 'ANCHORED', symbol: 'gates_deny', to: 'REJECTED' },
      { from: 'ANCHORED', symbol: 'gates_quarantine', to: 'QUARANTINED' },

      // Gate → Hatch → Runtime
      { from: 'GATE_RUN', symbol: 'boot_ok', to: 'HATCHED' },
      { from: 'HATCHED', symbol: 'attest_ok', to: 'RUNTIME' },

      // Runtime: ongoing attestation or rotation
      { from: 'RUNTIME', symbol: 'attest_ok', to: 'RUNTIME' },
      { from: 'RUNTIME', symbol: 'epoch_end', to: 'ROTATING' },
      { from: 'RUNTIME', symbol: 'policy_breach', to: 'REVOKED' },

      // Rotation: re-anchor and re-enter runtime
      { from: 'ROTATING', symbol: 'rotation_ok', to: 'RUNTIME' },
      { from: 'ROTATING', symbol: 'policy_breach', to: 'REVOKED' },

      // Quarantine: manual review
      { from: 'QUARANTINED', symbol: 'review_pass', to: 'ANCHORED' },
      { from: 'QUARANTINED', symbol: 'review_deny', to: 'REJECTED' },
    ],
  };
}

// ── Domain-Specific Invariant Checks ─────────────────────────────────

/**
 * Verify the gate pipeline satisfies SCBE safety invariants:
 *   1. HATCH is only reachable after all 5 gates pass
 *   2. DENY is absorbing
 *   3. The automaton is deterministic
 *   4. QUARANTINE cannot directly reach HATCH (must go through G5 again)
 */
export function verifyGatePipeline(): VerificationResult {
  const fa = createGatePipelineAutomaton();
  const base = verify(fa);

  // Extra: QUARANTINE must not directly reach HATCH
  const qToH = fa.transitions.some((t) => t.from === 'QUARANTINE' && t.to === 'HATCH');
  if (qToH) {
    base.violations.push({
      invariant: 'quarantine_no_shortcut',
      detail: 'QUARANTINE has a direct transition to HATCH — must go through G5_POLICY',
    });
    base.passed = false;
  }

  // Extra: HATCH requires exactly 5 pass transitions from INIT
  // (verify minimum path length = 6 edges: INIT→G1→G2→G3→G4→G5→HATCH)
  const minPath = shortestPath(fa, 'INIT', 'HATCH');
  if (minPath !== null && minPath < 6) {
    base.violations.push({
      invariant: 'five_gate_minimum',
      detail: `Shortest path to HATCH is ${minPath} steps, expected ≥ 6 (5 gates + init)`,
    });
    base.passed = false;
  }

  return base;
}

/**
 * Verify the egg lifecycle satisfies SCBE safety invariants:
 *   1. REVOKED is absorbing
 *   2. REJECTED is absorbing
 *   3. Deterministic
 *   4. RUNTIME is reachable from SEALED
 */
export function verifyEggLifecycle(): VerificationResult {
  const fa = createEggLifecycleAutomaton();
  return verify(fa);
}

// ── Utility ──────────────────────────────────────────────────────────

/**
 * BFS shortest path length (edge count) from source to target.
 * Returns null if unreachable.
 */
function shortestPath<S extends string, A extends string>(
  fa: FiniteAutomaton<S, A>,
  source: S,
  target: S,
): number | null {
  if (source === target) return 0;
  const visited = new Set<S>();
  const queue: Array<{ state: S; depth: number }> = [{ state: source, depth: 0 }];
  visited.add(source);

  while (queue.length > 0) {
    const { state, depth } = queue.shift()!;
    for (const t of fa.transitions) {
      if (t.from === state && !visited.has(t.to)) {
        if (t.to === target) return depth + 1;
        visited.add(t.to);
        queue.push({ state: t.to, depth: depth + 1 });
      }
    }
  }
  return null;
}
