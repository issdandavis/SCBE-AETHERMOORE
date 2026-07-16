/**
 * Constructive topological linearization for control-flow integrity.
 *
 * The base graph is not claimed to become Hamiltonian. Instead, an additional
 * phase coordinate distinguishes repeated visits to a base vertex. A
 * topology-preserving covering walk then becomes a Hamiltonian path through
 * the unique lifted states `(baseVertex, phase)`.
 */

import type { CFIResult } from './hamiltonianCFI.js';
import { ControlFlowGraph } from './hamiltonianCFI.js';

export interface LiftedControlState {
  /** Original CFG vertex. */
  baseVertex: number;
  /** Extra linearization coordinate. */
  phase: number;
}

export interface LinearizationProof {
  /** Every projected lifted transition is an edge in the base topology. */
  topologyPreserved: boolean;
  /** Phase makes every lifted state unique, even when base vertices repeat. */
  uniqueLiftedStates: boolean;
  /** Every base vertex appears at least once in the lifted path. */
  projectionCoversBase: boolean;
  /** Consecutive lifted states form one path visiting all lifted states once. */
  liftHasHamiltonianPath: boolean;
}

export interface TopologicalLift {
  schema: 'scbe.topological-linearization.v1';
  baseVertices: number[];
  states: LiftedControlState[];
  liftedEdges: Array<readonly [number, number]>;
  proof: LinearizationProof;
}

function sortedUnique(values: number[]): number[] {
  return [...new Set(values)].sort((left, right) => left - right);
}

/**
 * Lift one authorized trace into phase space.
 *
 * This is the directed-CFG primitive: callers supply the actual transition
 * predicate, so the lift cannot invent a base transition.
 */
export function liftAuthorizedTrace(
  baseVertices: number[],
  trace: number[],
  hasTransition: (from: number, to: number) => boolean,
  requireCoverage = false
): TopologicalLift {
  const base = sortedUnique(baseVertices);
  const known = new Set(base);
  if (trace.some((vertex) => !known.has(vertex))) {
    throw new Error('TRACE_VERTEX_OUTSIDE_BASE_TOPOLOGY');
  }
  for (let phase = 1; phase < trace.length; phase++) {
    if (!hasTransition(trace[phase - 1], trace[phase])) {
      throw new Error(`TRACE_INVENTS_BASE_TRANSITION:${trace[phase - 1]}->${trace[phase]}`);
    }
  }

  const states = trace.map((baseVertex, phase) => ({ baseVertex, phase }));
  const liftedEdges = states.slice(1).map((state) => [state.phase - 1, state.phase] as const);
  const projected = new Set(trace);
  const projectionCoversBase = base.every((vertex) => projected.has(vertex));
  if (requireCoverage && !projectionCoversBase) {
    throw new Error('TRACE_DOES_NOT_COVER_BASE_TOPOLOGY');
  }
  const stateKeys = states.map((state) => `${state.baseVertex}@${state.phase}`);

  return {
    schema: 'scbe.topological-linearization.v1',
    baseVertices: base,
    states,
    liftedEdges,
    proof: {
      topologyPreserved: true,
      uniqueLiftedStates: new Set(stateKeys).size === states.length,
      projectionCoversBase,
      liftHasHamiltonianPath:
        states.length === 0 || liftedEdges.length === Math.max(0, states.length - 1),
    },
  };
}

/**
 * Build a topology-preserving covering walk for a connected undirected CFG.
 *
 * DFS backtracking may revisit a base vertex. The phase coordinate makes each
 * occurrence a distinct lifted state. Disconnected graphs fail closed because
 * joining components would invent a transition.
 */
export function linearizeConnectedTopology(
  graph: ControlFlowGraph,
  entry?: number
): TopologicalLift {
  const vertices = sortedUnique(graph.getVertexIds());
  if (vertices.length === 0) {
    return liftAuthorizedTrace([], [], () => false, true);
  }
  const start = entry ?? vertices[0];
  if (!vertices.includes(start)) {
    throw new Error('ENTRY_VERTEX_OUTSIDE_BASE_TOPOLOGY');
  }

  const visited = new Set<number>();
  const walk: number[] = [];
  const visit = (vertex: number): void => {
    visited.add(vertex);
    walk.push(vertex);
    const neighbors = sortedUnique(graph.getNeighbors(vertex));
    for (const neighbor of neighbors) {
      if (visited.has(neighbor)) continue;
      visit(neighbor);
      walk.push(vertex);
    }
  };
  visit(start);
  if (visited.size !== vertices.length) {
    throw new Error('DISCONNECTED_BASE_TOPOLOGY');
  }
  return liftAuthorizedTrace(vertices, walk, (from, to) => graph.hasEdge(from, to), true);
}

/** Stateful integrity monitor for a previously receipted lift. */
export class TopologicalLinearCFI {
  private readonly lift: TopologicalLift;
  private readonly base: Set<number>;
  private cursor = 0;

  constructor(lift: TopologicalLift) {
    if (
      !lift.proof.topologyPreserved ||
      !lift.proof.uniqueLiftedStates ||
      !lift.proof.liftHasHamiltonianPath
    ) {
      throw new Error('UNPROVEN_TOPOLOGICAL_LIFT');
    }
    this.lift = lift;
    this.base = new Set(lift.baseVertices);
  }

  checkState(state: LiftedControlState): CFIResult {
    if (!Number.isInteger(state.phase) || !this.base.has(state.baseVertex)) {
      return 'ATTACK';
    }
    if (this.cursor >= this.lift.states.length) {
      return 'ATTACK'; // replay after the authorized path completed
    }
    const expected = this.lift.states[this.cursor];
    if (state.phase !== expected.phase) {
      return state.phase >= 0 && state.phase < this.lift.states.length ? 'DEVIATION' : 'ATTACK';
    }
    if (state.baseVertex !== expected.baseVertex) {
      return 'DEVIATION';
    }
    this.cursor += 1;
    return 'VALID';
  }

  get isComplete(): boolean {
    return this.cursor === this.lift.states.length;
  }

  reset(): void {
    this.cursor = 0;
  }
}
