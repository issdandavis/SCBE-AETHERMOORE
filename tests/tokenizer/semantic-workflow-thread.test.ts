/**
 * @file semantic-workflow-thread.test.ts
 * Tests for the SemanticWorkflowThread builder system.
 */
import { describe, expect, it } from 'vitest';
import {
  createWorkflowThread,
  serializeThread,
  validateThread,
  type ThreadEdge,
} from '../../src/tokenizer/semantic-workflow-thread.js';

// ============================================================================
// Fixture helper: build a minimal single-node thread for validateThread tests
// (bypasses the builder by directly inserting into the returned Map)
// ============================================================================

function buildSingleNodeThread() {
  const b = createWorkflowThread('fixture', 'AV');
  const thread = b.build();
  const rootId = 'node-root-001';
  thread.nodes.set(rootId, {
    id: rootId,
    label: 'ROOT',
    semanticAtomId: 'FLOW',
    tongue: 'AV',
    domain: 'workflow',
    laneIndex: 0,
    depth: 0,
    carriedState: {},
  });
  return { thread, rootId };
}

// ============================================================================
// Test 1: createWorkflowThread produces correct schema
// ============================================================================

describe('createWorkflowThread', () => {
  it('produces a builder that yields the correct schema version and structure', () => {
    const builder = createWorkflowThread('test-thread', 'AV');
    const thread = builder.build();

    expect(thread.schemaVersion).toBe('scbe-workflow-thread-v1');
    expect(thread.label).toBe('test-thread');
    expect(thread.tongue).toBe('AV');
    expect(thread.threadId).toMatch(/^thread-/);
    expect(thread.nodes).toBeInstanceOf(Map);
    expect(thread.edges).toBeInstanceOf(Array);
    expect(thread.tunnels).toBeInstanceOf(Array);
  });
});

// ============================================================================
// Test 2: pipe adds node and edge correctly
// ============================================================================

describe('pipe', () => {
  it('adds a downstream node with pipe edge and correct properties', () => {
    const b = createWorkflowThread('pipe-test', 'KO');
    const rootId = b.seed('INTENT', { tongue: 'KO', domain: 'workflow' });

    const nextId = b.pipe(rootId, 'DISPATCH', {
      label: 'dispatch-step',
      tongue: 'AV',
      domain: 'workflow',
    });

    const thread = b.build();

    expect(thread.nodes.has(rootId)).toBe(true);
    expect(thread.nodes.has(nextId)).toBe(true);
    expect(thread.nodes.get(nextId)?.tongue).toBe('AV');
    expect(thread.nodes.get(nextId)?.label).toBe('dispatch-step');
    expect(thread.nodes.get(nextId)?.semanticAtomId).toBe('DISPATCH');

    expect(thread.edges).toHaveLength(1);
    expect(thread.edges[0].kind).toBe('pipe');
    expect(thread.edges[0].from).toBe(rootId);
    expect(thread.edges[0].to).toBe(nextId);
  });

  it('throws when source node id does not exist', () => {
    const b = createWorkflowThread('pipe-err', 'KO');
    expect(() => b.pipe('nonexistent-id', 'FLOW')).toThrow(
      "pipe: source node 'nonexistent-id' not found"
    );
  });
});

// ============================================================================
// Test 3: bifurcate creates N branches with correct bijectiveKey
// ============================================================================

describe('bifurcate', () => {
  it('creates N branches with bijectiveKey on the bifurcate edge', () => {
    const b = createWorkflowThread('bif-test', 'AV');
    const rootId = b.seed('FLOW', { tongue: 'AV', domain: 'workflow' });

    const branchIds = b.bifurcate(
      rootId,
      [
        { atomId: 'ALLOW', label: 'allow-path', tongue: 'CA' },
        { atomId: 'QUARANTINE', label: 'quarantine-path', tongue: 'RU' },
        { atomId: 'DENY', label: 'deny-path', tongue: 'UM' },
      ],
      'governance-split-key'
    );

    const thread = b.build();

    expect(branchIds).toHaveLength(3);
    for (const id of branchIds) {
      expect(thread.nodes.has(id)).toBe(true);
    }

    const bifEdge = thread.edges.find((e) => e.kind === 'bifurcate');
    expect(bifEdge).toBeDefined();
    expect(bifEdge?.bijectiveKey).toBe('governance-split-key');
    expect(Array.isArray(bifEdge?.to)).toBe(true);
    expect((bifEdge?.to as string[]).length).toBe(3);

    // Branches get distinct lane indices
    const laneIndices = branchIds.map((id) => thread.nodes.get(id)!.laneIndex);
    expect(new Set(laneIndices).size).toBe(3);
  });
});

// ============================================================================
// Test 4: funnel creates N:1 convergence
// ============================================================================

describe('funnel', () => {
  it('creates convergence edges from N sources to 1 target and validates cleanly', () => {
    const b = createWorkflowThread('funnel-test', 'CA');
    const r1 = b.seed('FLOW', { tongue: 'AV', domain: 'workflow' });
    const r2 = b.seed('BLOCK', { tongue: 'RU', domain: 'governance' });
    const r3 = b.seed('VERIFY', { tongue: 'CA', domain: 'governance' });

    const mergedId = b.funnel([r1, r2, r3], 'MERGED', {
      label: 'combined',
      bijectiveKey: 'funnel-key',
    });

    const thread = b.build();

    expect(thread.nodes.has(mergedId)).toBe(true);
    expect(thread.nodes.get(mergedId)?.label).toBe('combined');

    // One funnel edge per source node
    const funnelEdges = thread.edges.filter((e) => e.kind === 'funnel');
    expect(funnelEdges).toHaveLength(3);
    expect(funnelEdges.every((e) => e.to === mergedId)).toBe(true);

    // First edge carries sourceIds metadata
    const primaryEdge = funnelEdges.find((e) => !e.metadata['role']);
    expect(primaryEdge?.metadata['sourceIds']).toEqual([r1, r2, r3]);

    // All sources are connected — validateThread should report zero errors
    expect(validateThread(thread)).toEqual([]);
  });
});

// ============================================================================
// Test 5: websocket creates two edges (both directions)
// ============================================================================

describe('websocket', () => {
  it('creates exactly two edges in both directions', () => {
    const b = createWorkflowThread('ws-test', 'KO');
    const aId = b.seed('SENDER', { tongue: 'KO', domain: 'workflow' });
    const bId = b.seed('RECEIVER', { tongue: 'DR', domain: 'workflow' });

    b.websocket(aId, bId);
    const thread = b.build();

    const wsEdges = thread.edges.filter((e) => e.kind === 'websocket');
    expect(wsEdges).toHaveLength(2);

    expect(wsEdges.find((e) => e.from === aId && e.to === bId)).toBeDefined();
    expect(wsEdges.find((e) => e.from === bId && e.to === aId)).toBeDefined();
  });

  it('throws when either node does not exist', () => {
    const b = createWorkflowThread('ws-err', 'KO');
    expect(() => b.websocket('a', 'b')).toThrow("websocket: node 'a' not found");
  });
});

// ============================================================================
// Test 6: handoff changes tongue on the new node
// ============================================================================

describe('handoff', () => {
  it('creates a new node with a different tongue and a handoff edge', () => {
    const b = createWorkflowThread('handoff-test', 'AV');
    const sourceId = b.seed('DISPATCH', { tongue: 'AV', domain: 'workflow' });

    const targetId = b.handoff(sourceId, 'RU', 'GOVERNANCE_CHECK', {
      label: 'rule-check',
      domain: 'governance',
    });

    const thread = b.build();
    const sourceNode = thread.nodes.get(sourceId)!;
    const targetNode = thread.nodes.get(targetId)!;

    expect(sourceNode.tongue).toBe('AV');
    expect(targetNode.tongue).toBe('RU');
    expect(targetNode.label).toBe('rule-check');
    expect(targetNode.domain).toBe('governance');

    const handoffEdge = thread.edges.find((e) => e.kind === 'handoff');
    expect(handoffEdge).toBeDefined();
    expect(handoffEdge?.from).toBe(sourceId);
    expect(handoffEdge?.to).toBe(targetId);
    expect(handoffEdge?.metadata['fromTongue']).toBe('AV');
    expect(handoffEdge?.metadata['toTongue']).toBe('RU');
  });
});

// ============================================================================
// Test 7: merge creates re-alignment edge and validates bijectiveKey
// ============================================================================

describe('merge', () => {
  it('creates a merge edge after bifurcate+pipe chain with matching bijectiveKey', () => {
    const b = createWorkflowThread('merge-test', 'AV');
    const rootId = b.seed('ROOT', { tongue: 'AV', domain: 'workflow' });
    const biKey = 'split-merge-key';

    const [branch1, branch2] = b.bifurcate(
      rootId,
      [{ atomId: 'BRANCH_A' }, { atomId: 'BRANCH_B' }],
      biKey
    );

    // Pipe each branch forward — key is inherited
    const leaf1 = b.pipe(branch1, 'PROCESSED_A');
    const leaf2 = b.pipe(branch2, 'PROCESSED_B');

    // Merge the leaves via bijectiveKey
    const mergedId = b.merge([leaf1, leaf2], 'UNIFIED', biKey);

    const thread = b.build();
    expect(thread.nodes.has(mergedId)).toBe(true);

    const mergeEdge = thread.edges.find((e) => e.kind === 'merge');
    expect(mergeEdge).toBeDefined();
    expect(mergeEdge?.bijectiveKey).toBe(biKey);
    expect(mergeEdge?.to).toBe(mergedId);

    // Full thread should be structurally valid
    expect(validateThread(thread)).toEqual([]);
  });

  it('throws when bijectiveKey does not match node inheritance', () => {
    const b = createWorkflowThread('bad-merge', 'AV');
    const r1 = b.seed('A', { tongue: 'AV', domain: 'workflow' });
    expect(() => b.merge([r1], 'MERGED', 'some-key')).toThrow(
      "merge: node '" + r1 + "' has bijectiveKey '(none)' but expected 'some-key'"
    );
  });
});

// ============================================================================
// Test 8: validateThread catches missing node reference in an edge
// ============================================================================

describe('validateThread', () => {
  it('returns no errors for a valid single-node thread', () => {
    const { thread } = buildSingleNodeThread();
    expect(validateThread(thread)).toHaveLength(0);
  });

  it('catches edge referencing a non-existent source node', () => {
    const { thread } = buildSingleNodeThread();
    const badEdge: ThreadEdge = {
      id: 'edge-bad-001',
      kind: 'pipe',
      from: 'nonexistent-node',
      to: 'node-root-001',
      metadata: {},
    };
    thread.edges.push(badEdge);

    const errors = validateThread(thread);
    expect(errors.some((e) => e.includes('nonexistent-node'))).toBe(true);
  });

  it('catches edge referencing a non-existent target node', () => {
    const { thread } = buildSingleNodeThread();
    const badEdge: ThreadEdge = {
      id: 'edge-bad-002',
      kind: 'pipe',
      from: 'node-root-001',
      to: 'nonexistent-target',
      metadata: {},
    };
    thread.edges.push(badEdge);

    const errors = validateThread(thread);
    expect(errors.some((e) => e.includes('nonexistent-target'))).toBe(true);
  });

  it('catches bifurcate with no corresponding merge edge', () => {
    const { thread } = buildSingleNodeThread();

    const node2 = 'node-branch-001';
    thread.nodes.set(node2, {
      id: node2,
      label: 'BRANCH',
      semanticAtomId: 'BLOCK',
      tongue: 'RU',
      domain: 'governance',
      laneIndex: 1,
      depth: 0,
      carriedState: {},
    });

    thread.edges.push({
      id: 'edge-bif-001',
      kind: 'bifurcate',
      from: 'node-root-001',
      to: [node2],
      bijectiveKey: 'orphan-bk',
      metadata: {},
    });

    const errors = validateThread(thread);
    expect(errors.some((e) => e.includes('orphan-bk') && e.includes('bifurcate'))).toBe(true);
  });
});

// ============================================================================
// Test 9: receipt has correct nodeCount, edgeCount, bijectiveKeys
// ============================================================================

describe('receipt', () => {
  it('returns correct nodeCount, edgeCount, bijectiveKeys, and a valid sha256', () => {
    const b = createWorkflowThread('receipt-test', 'DR');
    const rootId = b.seed('ORIGIN', { tongue: 'DR', domain: 'workflow' });
    const biKey = 'receipt-bk';

    const [br1, br2] = b.bifurcate(rootId, [{ atomId: 'PATH_A' }, { atomId: 'PATH_B' }], biKey);
    b.merge([br1, br2], 'FINAL', biKey);

    const r = b.receipt();

    // 4 nodes: root + 2 branches + merged
    expect(r.nodeCount).toBe(4);
    // 2 edges: bifurcate + merge
    expect(r.edgeCount).toBe(2);
    expect(r.bijectiveKeys).toContain(biKey);
    expect(r.schema).toBe('scbe.workflow_thread.v1');
    expect(r.threadSha256).toMatch(/^[a-f0-9]{64}$/);
    expect(r.tongue).toBe('DR');
    expect(r.label).toBe('receipt-test');
    expect(typeof r.createdAt).toBe('string');
  });
});

// ============================================================================
// Test 10: render output contains the thread label and at least one node label
// ============================================================================

describe('render', () => {
  it('contains the thread label, tongue, and at least one node label', () => {
    const b = createWorkflowThread('render-test', 'KO');
    const rootId = b.seed('INTAKE', { tongue: 'KO', domain: 'workflow' });
    b.pipe(rootId, 'PROCESS', { label: 'process-step', tongue: 'AV' });

    const output = b.render();

    expect(output).toContain('render-test');
    expect(output).toContain('[KO]');
    expect(output).toContain('INTAKE');
  });
});

// ============================================================================
// serializeThread — Map to array conversion
// ============================================================================

describe('serializeThread', () => {
  it('converts Map nodes to an array in the serialized form', () => {
    const { thread } = buildSingleNodeThread();
    const serialized = serializeThread(thread) as Record<string, unknown>;

    expect(Array.isArray(serialized['nodes'])).toBe(true);
    expect(serialized['schemaVersion']).toBe('scbe-workflow-thread-v1');
    expect(serialized['threadId']).toBeDefined();
    expect(serialized['edges']).toBeInstanceOf(Array);
    expect(serialized['tunnels']).toBeInstanceOf(Array);
  });

  it('serialized nodes contain all ThreadNode fields', () => {
    const { thread } = buildSingleNodeThread();
    const serialized = serializeThread(thread) as { nodes: Array<Record<string, unknown>> };
    const rootNode = serialized.nodes.find((n) => n['id'] === 'node-root-001');
    expect(rootNode).toBeDefined();
    expect(rootNode?.['label']).toBe('ROOT');
    expect(rootNode?.['tongue']).toBe('AV');
    expect(rootNode?.['semanticAtomId']).toBe('FLOW');
  });
});

// ============================================================================
// seed() public API
// ============================================================================

describe('seed', () => {
  it('creates a root node accessible by the returned id', () => {
    const b = createWorkflowThread('seed-test', 'UM');
    const id = b.seed('SCAN_ENTRY', { tongue: 'UM', domain: 'workflow' });
    const thread = b.build();

    expect(thread.nodes.has(id)).toBe(true);
    expect(thread.nodes.get(id)?.tongue).toBe('UM');
    expect(thread.nodes.get(id)?.semanticAtomId).toBe('SCAN_ENTRY');
    expect(thread.nodes.get(id)?.label).toBe('SCAN_ENTRY');
  });

  it('defaults tongue to the thread tongue and domain to workflow', () => {
    const b = createWorkflowThread('seed-default', 'DR');
    const id = b.seed('RECEIPT');
    const thread = b.build();

    expect(thread.nodes.get(id)?.tongue).toBe('DR');
    expect(thread.nodes.get(id)?.domain).toBe('workflow');
  });
});
