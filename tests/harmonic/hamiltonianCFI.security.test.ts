import { describe, expect, it } from 'vitest';
import {
  ControlFlowGraph,
  HamiltonianCFI,
  createVertex,
} from '../../src/harmonic/hamiltonianCFI.js';

function chain() {
  const cfg = new ControlFlowGraph();
  for (let i = 0; i < 4; i++) cfg.addVertex(createVertex(i, String(i), i));
  cfg.addEdge(0, 1);
  cfg.addEdge(1, 2);
  cfg.addEdge(2, 3);
  return cfg;
}

describe('directed CFI security boundary', () => {
  it('rejects every illegal known-block transition, including reverse and self jumps', () => {
    const cfg = chain();
    for (let a = 0; a < 4; a++) {
      for (let b = 0; b < 4; b++) {
        const cfi = new HamiltonianCFI(cfg);
        expect(cfi.checkState([a])).toBe('VALID');
        expect(cfi.checkState([b]) === 'VALID').toBe(b === a + 1);
      }
    }
  });
  it('does not let a golden path grant an illegal edge', () => {
    expect(() => new HamiltonianCFI(chain()).setGoldenPath([0, 2])).toThrow();
  });
  it('cannot wrap a golden path without an explicit return edge', () => {
    const cfi = new HamiltonianCFI(chain());
    cfi.setGoldenPath([0, 1, 2, 3]);
    for (const v of [0, 1, 2, 3]) expect(cfi.checkState([v])).toBe('VALID');
    expect(cfi.checkState([0])).toBe('ATTACK');
  });
  it('freezes original policy and copies caller-owned golden paths', () => {
    const cfg = chain();
    const cfi = new HamiltonianCFI(cfg);
    const path = [0, 1, 2, 3];
    cfi.setGoldenPath(path);
    path[1] = 2;
    cfg.addEdge(0, 2);
    expect(cfi.checkState([0])).toBe('VALID');
    expect(cfi.checkState([2])).toBe('ATTACK');
  });
  it('preserves explicitly declared cycles', () => {
    const cfg = chain();
    cfg.addEdge(3, 0);
    const cfi = new HamiltonianCFI(cfg);
    for (const v of [0, 1, 2, 3, 0, 1]) expect(cfi.checkState([v])).toBe('VALID');
  });
  it('rejects malformed states and latches failure until explicit reset', () => {
    const cfi = new HamiltonianCFI(chain());
    expect(cfi.checkState([0])).toBe('VALID');
    expect(cfi.checkState([Number.NaN])).toBe('ATTACK');
    expect(cfi.checkState([1])).toBe('ATTACK');
    cfi.reset();
    expect(cfi.checkState([0])).toBe('VALID');
  });
  it('does not search backwards along an undirected analysis edge', () => {
    const cfg = chain();
    cfg.addEdge(0, 3);
    const path = new HamiltonianCFI(cfg).findHamiltonianPath();
    expect(path).toEqual([0, 1, 2, 3]);
  });
  it('searches the frozen policy even after the caller mutates its graph', () => {
    const cfg = chain();
    const cfi = new HamiltonianCFI(cfg);
    cfg.addVertex(createVertex(4, 'late', 4));
    cfg.addEdge(3, 4);
    expect(cfi.findHamiltonianPath()).toEqual([0, 1, 2, 3]);
  });
  it('does not continue from a deviation without an explicit reset', () => {
    const cfg = chain();
    cfg.addEdge(0, 2);
    const cfi = new HamiltonianCFI(cfg, 2);
    cfi.setGoldenPath([0, 1, 2, 3]);
    expect(cfi.checkState([0])).toBe('VALID');
    expect(cfi.checkState([2])).toBe('DEVIATION');
    expect(cfi.checkState([1])).toBe('ATTACK');
  });
  it('rejects undeclared endpoints and invalid thresholds', () => {
    expect(() => chain().addEdge(0, 99)).toThrow();
    expect(() => new HamiltonianCFI(chain(), Number.NaN)).toThrow();
  });
  it('rejects sparse golden paths and revokes the prior traversal', () => {
    const cfi = new HamiltonianCFI(chain());
    cfi.setGoldenPath([0, 1, 2, 3]);
    const sparse = [0, 1, 2, 3];
    delete sparse[1];
    expect(() => cfi.setGoldenPath(sparse)).toThrow();
    expect(cfi.checkState([0])).toBe('ATTACK');
  });
});
