import { describe, expect, it } from 'vitest';
import {
  ControlFlowGraph,
  HamiltonianCFI,
  createVertex,
} from '../../src/harmonic/hamiltonianCFI.js';
import {
  TopologicalLinearCFI,
  liftAuthorizedTrace,
  linearizeConnectedTopology,
} from '../../src/harmonic/topologicalLinearization.js';

function starGraph(): ControlFlowGraph {
  const graph = new ControlFlowGraph();
  for (let vertex = 0; vertex < 5; vertex++) {
    graph.addVertex(createVertex(vertex, `v${vertex}`, 0x1000 + vertex * 0x10));
  }
  for (let leaf = 1; leaf < 5; leaf++) graph.addEdge(0, leaf);
  return graph;
}

describe('constructive topological linearization', () => {
  it('lifts a non-Hamiltonian base graph into a topology-preserving Hamiltonian path', () => {
    const graph = starGraph();
    const basePath = new HamiltonianCFI(graph).findHamiltonianPath();
    expect(basePath).toBeNull();

    const lift = linearizeConnectedTopology(graph, 0);
    expect(lift.states.map((state) => state.baseVertex)).toEqual([0, 1, 0, 2, 0, 3, 0, 4, 0]);
    expect(lift.proof).toEqual({
      topologyPreserved: true,
      uniqueLiftedStates: true,
      projectionCoversBase: true,
      liftHasHamiltonianPath: true,
    });
    expect(new Set(lift.states.map((state) => state.phase)).size).toBe(lift.states.length);
    for (let index = 1; index < lift.states.length; index++) {
      expect(graph.hasEdge(lift.states[index - 1].baseVertex, lift.states[index].baseVertex)).toBe(
        true
      );
    }
  });

  it('fails closed rather than inventing an edge between disconnected components', () => {
    const graph = new ControlFlowGraph();
    graph.addVertex(createVertex(1, 'left', 0x1000));
    graph.addVertex(createVertex(2, 'right', 0x2000));
    expect(() => linearizeConnectedTopology(graph)).toThrow('DISCONNECTED_BASE_TOPOLOGY');
  });

  it('validates directed authorized traces without adding transitions', () => {
    const directed = new Set(['1->2', '2->3', '2->4', '4->5']);
    const lift = liftAuthorizedTrace([1, 2, 3, 4, 5], [1, 2, 4, 5], (from, to) =>
      directed.has(`${from}->${to}`)
    );
    expect(lift.proof.topologyPreserved).toBe(true);
    expect(lift.proof.projectionCoversBase).toBe(false);
    const monitor = new TopologicalLinearCFI(lift);
    for (const state of lift.states) expect(monitor.checkState(state)).toBe('VALID');
    expect(monitor.isComplete).toBe(true);
    expect(() =>
      liftAuthorizedTrace([1, 2, 3], [1, 3], (from, to) => directed.has(`${from}->${to}`))
    ).toThrow('TRACE_INVENTS_BASE_TRANSITION:1->3');
  });
});

describe('lifted control-flow integrity', () => {
  it('accepts the exact lifted path and detects a replay', () => {
    const lift = linearizeConnectedTopology(starGraph(), 0);
    const monitor = new TopologicalLinearCFI(lift);
    for (const state of lift.states) expect(monitor.checkState(state)).toBe('VALID');
    expect(monitor.isComplete).toBe(true);
    expect(monitor.checkState(lift.states[0])).toBe('ATTACK');
  });

  it('detects phase skips and vertex substitutions', () => {
    const lift = linearizeConnectedTopology(starGraph(), 0);
    const skipped = new TopologicalLinearCFI(lift);
    expect(skipped.checkState(lift.states[0])).toBe('VALID');
    expect(skipped.checkState(lift.states[2])).toBe('DEVIATION');

    const substituted = new TopologicalLinearCFI(lift);
    expect(substituted.checkState({ baseVertex: 4, phase: 0 })).toBe('DEVIATION');
    expect(substituted.checkState({ baseVertex: 999, phase: 0 })).toBe('ATTACK');
  });

  it('detects every single-state substitution in the lifted star corpus', () => {
    const lift = linearizeConnectedTopology(starGraph(), 0);
    let attacks = 0;
    let detected = 0;
    for (let phase = 0; phase < lift.states.length; phase++) {
      for (const replacement of lift.baseVertices) {
        if (replacement === lift.states[phase].baseVertex) continue;
        attacks += 1;
        const monitor = new TopologicalLinearCFI(lift);
        for (let prefix = 0; prefix < phase; prefix++) {
          expect(monitor.checkState(lift.states[prefix])).toBe('VALID');
        }
        if (monitor.checkState({ baseVertex: replacement, phase }) !== 'VALID') {
          detected += 1;
        }
      }
    }
    expect(attacks).toBeGreaterThan(0);
    expect(detected).toBe(attacks);
  });
});
