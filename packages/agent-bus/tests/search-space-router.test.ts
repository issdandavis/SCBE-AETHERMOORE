import { describe, expect, it } from 'vitest';
import {
  allocateParallelSearchLanes,
  contractSearchSpace,
  createSearchNode,
  expandSearchNode,
  gradeSearchNode,
  mergeSearchResults,
  repositionSearchNode,
  reorderSearchQueries,
  type SearchSpaceNode,
} from '../src/index.js';

function node(
  id: string,
  overrides: Partial<Omit<SearchSpaceNode, 'id' | 'color'>> = {}
): SearchSpaceNode {
  return createSearchNode({
    id,
    parent_id: null,
    depth: 0,
    plane: 'repo',
    query: `query ${id}`,
    priority: 0.5,
    risk: 0.2,
    unknown_mass: 0.4,
    confidence: 0.5,
    owner: null,
    state: 'open',
    sector: { x: 0, y: 0, z: 0, width: 1, height: 1, depth: 1 },
    tags: [],
    ...overrides,
  });
}

describe('search-space-router', () => {
  it('grades nodes by risk, completion, shared ownership, and contraction state', () => {
    expect(gradeSearchNode(node('risk', { risk: 0.9 }))).toBe('red');
    expect(gradeSearchNode(node('done', { state: 'complete' }))).toBe('green');
    expect(gradeSearchNode(node('shared', { owner: 'shared' }))).toBe('purple');
    expect(gradeSearchNode(node('small', { state: 'contracted' }))).toBe('blue');
    expect(gradeSearchNode(node('urgent', { priority: 0.9 }))).toBe('orange');
  });

  it('reorders queries toward priority, unknown mass, confidence, and risk limits', () => {
    const ordered = reorderSearchQueries(
      [
        node('low', { priority: 0.1, unknown_mass: 0.1 }),
        node('blocked', { state: 'blocked', priority: 1 }),
        node('risky', { priority: 1, risk: 0.9 }),
        node('best', { priority: 0.8, unknown_mass: 0.7, confidence: 0.9 }),
      ],
      { risk_limit: 0.8 }
    );

    expect(ordered.map((item) => item.id)).toEqual(['best', 'low']);
  });

  it('expands a node into deterministic sparse octree children', () => {
    const root = node('root', {
      query: 'map unknown repo space',
      sector: { x: 0, y: 0, z: 0, width: 8, height: 8, depth: 8 },
    });

    const children = expandSearchNode(root);

    expect(children).toHaveLength(8);
    expect(children[0]!.id).toBe('root.0');
    expect(children[0]!.parent_id).toBe('root');
    expect(children[0]!.depth).toBe(1);
    expect(children[0]!.sector).toEqual({ x: 0, y: 0, z: 0, width: 4, height: 4, depth: 4 });
    expect(children[7]!.sector).toEqual({ x: 4, y: 4, z: 4, width: 4, height: 4, depth: 4 });
  });

  it('contracts low-signal deep nodes into abridgement anchors while preserving important nodes', () => {
    const root = node('root');
    const keep = node('root.important', { parent_id: 'root', depth: 2, priority: 0.95 });
    const sparseA = node('root.a', { parent_id: 'root', depth: 3, priority: 0.2 });
    const sparseB = node('root.b', { parent_id: 'root', depth: 3, priority: 0.3 });

    const result = contractSearchSpace([root, keep, sparseA, sparseB], { max_depth: 1 });

    expect(result.schema_version).toBe('scbe.agent_bus.search_space_contraction.v1');
    expect(result.nodes.map((item) => item.id)).toContain('root');
    expect(result.nodes.map((item) => item.id)).toContain('root.important');
    expect(result.contracted_node_ids).toEqual(['root.a', 'root.b']);
    expect(result.abridgements[0]!.summary).toBe('abridged 2 sparse sectors');
  });

  it('repositions nodes and recalculates descendant depths without losing hierarchy', () => {
    const root = node('root');
    const branch = node('branch', { parent_id: 'root', depth: 1 });
    const leaf = node('leaf', { parent_id: 'branch', depth: 2 });
    const newParent = node('new-parent', { parent_id: null, depth: 0 });

    const moved = repositionSearchNode([root, branch, leaf, newParent], 'branch', 'new-parent');
    const movedBranch = moved.find((item) => item.id === 'branch')!;
    const movedLeaf = moved.find((item) => item.id === 'leaf')!;

    expect(movedBranch.parent_id).toBe('new-parent');
    expect(movedBranch.depth).toBe(1);
    expect(movedLeaf.parent_id).toBe('branch');
    expect(movedLeaf.depth).toBe(2);
  });

  it('blocks cyclic repositioning', () => {
    const root = node('root');
    const child = node('child', { parent_id: 'root', depth: 1 });

    expect(() => repositionSearchNode([root, child], 'root', 'child')).toThrow(/descendant/);
  });

  it('allocates non-overlapping parallel lanes across two model agents', () => {
    const nodes = [
      node('repo-a', {
        sector: { x: 0, y: 0, z: 0, width: 1, height: 1, depth: 1 },
        priority: 0.9,
      }),
      node('repo-b', {
        sector: { x: 1, y: 0, z: 0, width: 1, height: 1, depth: 1 },
        priority: 0.8,
      }),
      node('overlap-a', {
        sector: { x: 0.5, y: 0, z: 0, width: 1, height: 1, depth: 1 },
        priority: 0.7,
      }),
      node('tool-a', {
        plane: 'tool',
        sector: { x: 3, y: 0, z: 0, width: 1, height: 1, depth: 1 },
        priority: 0.7,
      }),
    ];

    const allocation = allocateParallelSearchLanes(nodes, [
      { id: 'agent-a', model_lane: 'free', planes: ['repo'], max_nodes: 2 },
      { id: 'agent-b', model_lane: 'local', planes: ['tool', 'repo'], max_nodes: 2 },
    ]);
    const assigned = allocation.lanes.flatMap((lane) => lane.assigned_node_ids);

    expect(allocation.schema_version).toBe('scbe.agent_bus.parallel_search_lanes.v1');
    expect(new Set(assigned).size).toBe(assigned.length);
    expect(assigned).toContain('repo-a');
    expect(assigned).toContain('repo-b');
    expect(assigned).toContain('tool-a');
    expect(allocation.interference.map((item) => item.node_id)).toContain('overlap-a');
    expect(allocation.provenance_hash).toMatch(/^[a-f0-9]{64}$/);
  });

  it('merges shared search results by semantic title with provenance', () => {
    const merged = mergeSearchResults([
      { node_id: 'a', agent_id: 'agent-a', score: 0.6, title: 'Hydra notes' },
      { node_id: 'b', agent_id: 'agent-b', score: 0.9, title: 'hydra notes' },
      { node_id: 'c', agent_id: 'agent-b', score: 0.7, title: 'Polly pad source' },
    ]);

    expect(merged.schema_version).toBe('scbe.agent_bus.search_result_merge.v1');
    expect(merged.results).toHaveLength(2);
    expect(merged.results[0]!.title).toBe('hydra notes');
    expect(merged.results[0]!.agent_ids).toEqual(['agent-a', 'agent-b']);
    expect(merged.duplicate_groups).toBe(1);
    expect(merged.provenance_hash).toMatch(/^[a-f0-9]{64}$/);
  });
});
