/**
 * @file semantic-workflow-thread.ts
 * @module tokenizer/semantic-workflow-thread
 * @layer L1, L14
 *
 * SemanticWorkflowThread — models workflow as a multi-lane highway.
 *
 * Structural primitives:
 *   Thread     = a directed workflow with multiple parallel lanes
 *   Pipe       = linear sequential flow, A→B→C
 *   Funnel     = N:1 convergence, many lanes merge to one
 *   Bifurcate  = 1:N split, one lane becomes many
 *   Merge      = bijective re-alignment of diverged branches via shared key
 *   Websocket  = bidirectional channel between two nodes
 *   Handoff    = agent-to-agent transfer, tongue/domain changes
 *   Tunnel     = hidden processing context (lanes go below grade)
 *   Ramp       = side-path entry/exit from main thread
 *
 * Sacred Tongue routing labels (labels only, no logic):
 *   KO = intent/origin
 *   AV = dispatch/motion
 *   RU = governance/rule-check
 *   CA = verify/harmony/convergence
 *   UM = scan/intake
 *   DR = receipt/lineage/record
 */

import { createHash } from 'crypto';
import type { TongueCode } from './ss1.js';
import type { SemanticDomain } from './semantic-atom.js';

// ============================================================================
// Types
// ============================================================================

export type ThreadEdgeKind =
  | 'pipe' // A→B linear, one-in one-out
  | 'funnel' // N→1 convergence
  | 'bifurcate' // 1→N split
  | 'websocket' // bidirectional A↔B
  | 'handoff' // agent-to-agent, tongue/domain changes
  | 'merge' // bijective re-alignment of diverged branches
  | 'ramp_in' // side path joins main thread
  | 'ramp_out' // lane exits to side path
  | 'tunnel_enter' // thread enters hidden processing context
  | 'tunnel_exit'; // thread emerges from processing context

export interface ThreadNode {
  id: string;
  label: string;
  semanticAtomId: string; // e.g. 'FLOW', 'GOVERNANCE', 'VERIFY'
  tongue: TongueCode;
  domain: SemanticDomain;
  laneIndex: number; // horizontal lane position (0-based)
  depth: number; // vertical level: 0=surface, negative=below grade (tunnel), positive=elevated
  carriedState: Record<string, unknown>;
}

export interface ThreadEdge {
  id: string;
  kind: ThreadEdgeKind;
  from: string; // source node id
  to: string | string[]; // target node id(s) — array for bifurcate/funnel
  bijectiveKey?: string; // shared key for bifurcate+merge pairs; used for re-alignment check
  ruleGuard?: string; // rule that must hold for this edge to fire
  metadata: Record<string, unknown>;
}

export interface TunnelSegment {
  id: string;
  label: string;
  depth: number; // how far below grade (negative depth)
  inboundNodes: string[]; // nodes entering the tunnel
  outboundNodes: string[]; // nodes exiting the tunnel
  sideExits: string[]; // nodes that leave via ramp_out inside the tunnel
  emergentNodes: string[]; // nodes that appear inside the tunnel without a corresponding inbound
  internalMerges: Array<{ fromNodes: string[]; toNode: string; bijectiveKey: string }>;
}

export interface WorkflowThreadReceipt {
  schema: 'scbe.workflow_thread.v1';
  threadId: string;
  label: string;
  tongue: TongueCode;
  nodeCount: number;
  edgeCount: number;
  tunnelCount: number;
  laneCount: number;
  depthRange: [number, number]; // [min depth, max depth]
  bijectiveKeys: string[];
  handoffCount: number;
  websocketCount: number;
  createdAt: string;
  threadSha256: string; // sha256 of canonical JSON of nodes+edges
}

/**
 * SemanticWorkflowThread (builder output form).
 *
 * NOTE: The name `SemanticWorkflowThread` is also exported from
 * `./semantic-atom.js` under schema `'scbe-semantic-workflow-thread-v1'`.
 * That is a different, simpler interface used for text-tokenization workflow
 * graphs. This interface (schema `'scbe-workflow-thread-v1'`) represents a
 * full multi-lane highway with tunnels, bijective merge verification, and
 * receipt generation. They coexist; when you import from index.ts this one
 * takes precedence.
 */
export interface SemanticWorkflowThread {
  schemaVersion: 'scbe-workflow-thread-v1';
  threadId: string;
  label: string;
  tongue: TongueCode;
  nodes: Map<string, ThreadNode>;
  edges: ThreadEdge[];
  tunnels: TunnelSegment[];
}

// ============================================================================
// Builder
// ============================================================================

export class WorkflowThreadBuilder {
  private thread: SemanticWorkflowThread;
  private nextLane: number = 0;
  private edgeCounter: number = 0;
  private nodeCounter: number = 0;

  // Track which bijectiveKey each node inherited (set by bifurcate, cleared by merge)
  private nodeKeyMap: Map<string, string> = new Map();

  // Track open tunnels: tunnelId -> { segment, baseDepth, trackedInboundSet }
  private openTunnels: Map<
    string,
    { segment: TunnelSegment; depth: number; inboundSet: Set<string> }
  > = new Map();

  // Track which nodes were created while a tunnel was open
  private tunnelCreatedNodes: Map<string, string> = new Map(); // nodeId -> tunnelId

  constructor(label: string, tongue: TongueCode) {
    this.thread = {
      schemaVersion: 'scbe-workflow-thread-v1',
      threadId: this._genId('thread'),
      label,
      tongue,
      nodes: new Map(),
      edges: [],
      tunnels: [],
    };
  }

  // --------------------------------------------------------------------------
  // Private helpers
  // --------------------------------------------------------------------------

  private _genId(prefix: string): string {
    return `${prefix}-${Date.now().toString(36)}-${(++this.nodeCounter).toString(36).padStart(4, '0')}`;
  }

  private _genEdgeId(): string {
    return `edge-${Date.now().toString(36)}-${(++this.edgeCounter).toString(36).padStart(4, '0')}`;
  }

  private _activeTunnelDepth(): number {
    if (this.openTunnels.size === 0) return 0;
    // Use the deepest open tunnel
    let minDepth = 0;
    for (const { depth } of this.openTunnels.values()) {
      if (depth < minDepth) minDepth = depth;
    }
    return minDepth;
  }

  private _registerInTunnel(nodeId: string): void {
    for (const [tunnelId, { inboundSet }] of this.openTunnels.entries()) {
      if (!inboundSet.has(nodeId)) {
        this.tunnelCreatedNodes.set(nodeId, tunnelId);
      }
    }
  }

  private addNode(opts: Omit<ThreadNode, 'id'>): string {
    const id = this._genId('node');
    const depth = this._activeTunnelDepth() !== 0 ? this._activeTunnelDepth() : opts.depth;
    const node: ThreadNode = { ...opts, id, depth };
    this.thread.nodes.set(id, node);
    this._registerInTunnel(id);
    return id;
  }

  private addEdge(opts: Omit<ThreadEdge, 'id'>): string {
    const id = this._genEdgeId();
    const edge: ThreadEdge = { ...opts, id };
    this.thread.edges.push(edge);
    return id;
  }

  // --------------------------------------------------------------------------
  // Public builder methods
  // --------------------------------------------------------------------------

  /**
   * Seed (create root node): adds the first node to the thread.
   * All other builder methods require a pre-existing node id; call this once
   * (or more) to establish root nodes before chaining.
   * Returns the new node id.
   */
  seed(
    atomId: string,
    opts?: {
      label?: string;
      tongue?: TongueCode;
      domain?: SemanticDomain;
      laneIndex?: number;
      state?: Record<string, unknown>;
    }
  ): string {
    return this.addNode({
      label: opts?.label ?? atomId,
      semanticAtomId: atomId,
      tongue: opts?.tongue ?? this.thread.tongue,
      domain: opts?.domain ?? 'workflow',
      laneIndex: opts?.laneIndex ?? this.nextLane++,
      depth: 0,
      carriedState: opts?.state ?? {},
    });
  }

  /**
   * Linear pipe: creates a new node downstream of fromId.
   * Returns the new node id.
   */
  pipe(
    fromId: string,
    atomId: string,
    opts?: {
      label?: string;
      tongue?: TongueCode;
      domain?: SemanticDomain;
      state?: Record<string, unknown>;
      ruleGuard?: string;
    }
  ): string {
    const from = this.thread.nodes.get(fromId);
    if (!from) throw new Error(`pipe: source node '${fromId}' not found`);

    const toId = this.addNode({
      label: opts?.label ?? atomId,
      semanticAtomId: atomId,
      tongue: opts?.tongue ?? from.tongue,
      domain: opts?.domain ?? from.domain,
      laneIndex: from.laneIndex,
      depth: from.depth,
      carriedState: opts?.state ?? {},
    });

    // Propagate bijectiveKey along pipe chains
    const inheritedKey = this.nodeKeyMap.get(fromId);
    if (inheritedKey) this.nodeKeyMap.set(toId, inheritedKey);

    this.addEdge({
      kind: 'pipe',
      from: fromId,
      to: toId,
      ruleGuard: opts?.ruleGuard,
      metadata: {},
    });

    return toId;
  }

  /**
   * Bifurcate: splits one node into N branches.
   * Each branch gets a new lane. All edges carry the bijectiveKey.
   * Returns array of new node ids (one per branch).
   */
  bifurcate(
    fromId: string,
    branches: Array<{
      atomId: string;
      label?: string;
      tongue?: TongueCode;
      domain?: SemanticDomain;
      state?: Record<string, unknown>;
    }>,
    bijectiveKey: string
  ): string[] {
    const from = this.thread.nodes.get(fromId);
    if (!from) throw new Error(`bifurcate: source node '${fromId}' not found`);

    const branchIds: string[] = [];

    for (const branch of branches) {
      const laneIndex = this.nextLane++;
      const toId = this.addNode({
        label: branch.label ?? branch.atomId,
        semanticAtomId: branch.atomId,
        tongue: branch.tongue ?? from.tongue,
        domain: branch.domain ?? from.domain,
        laneIndex,
        depth: from.depth,
        carriedState: branch.state ?? {},
      });

      this.nodeKeyMap.set(toId, bijectiveKey);
      branchIds.push(toId);
    }

    this.addEdge({
      kind: 'bifurcate',
      from: fromId,
      to: branchIds,
      bijectiveKey,
      metadata: {},
    });

    return branchIds;
  }

  /**
   * Funnel: N nodes converge into one new node.
   * Returns the new node id.
   */
  funnel(
    fromIds: string[],
    atomId: string,
    opts?: {
      label?: string;
      tongue?: TongueCode;
      domain?: SemanticDomain;
      bijectiveKey?: string;
    }
  ): string {
    if (fromIds.length === 0) throw new Error('funnel: fromIds must not be empty');

    const firstFrom = this.thread.nodes.get(fromIds[0]);
    if (!firstFrom) throw new Error(`funnel: source node '${fromIds[0]}' not found`);

    const toId = this.addNode({
      label: opts?.label ?? atomId,
      semanticAtomId: atomId,
      tongue: opts?.tongue ?? firstFrom.tongue,
      domain: opts?.domain ?? firstFrom.domain,
      laneIndex: firstFrom.laneIndex,
      depth: firstFrom.depth,
      carriedState: {},
    });

    // Add one funnel edge per source so every source node is connected.
    // The first edge carries the full sourceIds list in metadata; subsequent
    // edges carry role:'secondary' so validateThread doesn't report orphans.
    for (let i = 0; i < fromIds.length; i++) {
      const srcId = fromIds[i];
      if (!this.thread.nodes.has(srcId)) {
        throw new Error(`funnel: source node '${srcId}' not found`);
      }
      this.addEdge({
        kind: 'funnel',
        from: srcId,
        to: toId,
        bijectiveKey: opts?.bijectiveKey,
        metadata: i === 0 ? { sourceIds: fromIds } : { role: 'secondary', sourceIds: fromIds },
      });
    }

    if (opts?.bijectiveKey) this.nodeKeyMap.set(toId, opts.bijectiveKey);

    return toId;
  }

  /**
   * Websocket: bidirectional channel between two nodes.
   * Adds two edges (A→B and B→A).
   */
  websocket(nodeA: string, nodeB: string, opts?: { ruleGuard?: string }): void {
    if (!this.thread.nodes.has(nodeA)) throw new Error(`websocket: node '${nodeA}' not found`);
    if (!this.thread.nodes.has(nodeB)) throw new Error(`websocket: node '${nodeB}' not found`);

    this.addEdge({
      kind: 'websocket',
      from: nodeA,
      to: nodeB,
      ruleGuard: opts?.ruleGuard,
      metadata: { direction: 'A->B' },
    });

    this.addEdge({
      kind: 'websocket',
      from: nodeB,
      to: nodeA,
      ruleGuard: opts?.ruleGuard,
      metadata: { direction: 'B->A' },
    });
  }

  /**
   * Handoff: passes work from one tongue/domain to another.
   * The new node gets the specified tongue, breaking tongue inheritance.
   * Returns the new node id.
   */
  handoff(
    fromId: string,
    toTongue: TongueCode,
    atomId: string,
    opts?: {
      label?: string;
      domain?: SemanticDomain;
      state?: Record<string, unknown>;
    }
  ): string {
    const from = this.thread.nodes.get(fromId);
    if (!from) throw new Error(`handoff: source node '${fromId}' not found`);

    const toId = this.addNode({
      label: opts?.label ?? atomId,
      semanticAtomId: atomId,
      tongue: toTongue,
      domain: opts?.domain ?? from.domain,
      laneIndex: from.laneIndex,
      depth: from.depth,
      carriedState: opts?.state ?? {},
    });

    this.addEdge({
      kind: 'handoff',
      from: fromId,
      to: toId,
      metadata: { fromTongue: from.tongue, toTongue },
    });

    return toId;
  }

  /**
   * Ramp out: a lane branches off to a side path.
   * The side-path node gets a fresh lane.
   * Returns the new side-path node id.
   */
  rampOut(
    fromId: string,
    atomId: string,
    opts?: {
      label?: string;
      tongue?: TongueCode;
      domain?: SemanticDomain;
    }
  ): string {
    const from = this.thread.nodes.get(fromId);
    if (!from) throw new Error(`rampOut: source node '${fromId}' not found`);

    const laneIndex = this.nextLane++;
    const toId = this.addNode({
      label: opts?.label ?? atomId,
      semanticAtomId: atomId,
      tongue: opts?.tongue ?? from.tongue,
      domain: opts?.domain ?? from.domain,
      laneIndex,
      depth: from.depth,
      carriedState: {},
    });

    this.addEdge({
      kind: 'ramp_out',
      from: fromId,
      to: toId,
      metadata: {},
    });

    // Register as side exit if inside tunnel
    for (const { segment, inboundSet } of this.openTunnels.values()) {
      if (inboundSet.has(fromId)) {
        if (!segment.sideExits.includes(toId)) segment.sideExits.push(toId);
      }
    }

    return toId;
  }

  /**
   * Ramp in: a side-path node merges back into the main thread.
   * Creates a convergence node at the main lane.
   * Returns the new merged node id.
   */
  rampIn(
    mainId: string,
    sideId: string,
    atomId: string,
    opts?: {
      label?: string;
      bijectiveKey?: string;
    }
  ): string {
    const main = this.thread.nodes.get(mainId);
    const side = this.thread.nodes.get(sideId);
    if (!main) throw new Error(`rampIn: main node '${mainId}' not found`);
    if (!side) throw new Error(`rampIn: side node '${sideId}' not found`);

    const toId = this.addNode({
      label: opts?.label ?? atomId,
      semanticAtomId: atomId,
      tongue: main.tongue,
      domain: main.domain,
      laneIndex: main.laneIndex,
      depth: main.depth,
      carriedState: {},
    });

    this.addEdge({
      kind: 'ramp_in',
      from: mainId,
      to: toId,
      bijectiveKey: opts?.bijectiveKey,
      metadata: { sideId },
    });

    this.addEdge({
      kind: 'ramp_in',
      from: sideId,
      to: toId,
      bijectiveKey: opts?.bijectiveKey,
      metadata: { role: 'side' },
    });

    return toId;
  }

  /**
   * Merge: re-aligns bijective branches created by bifurcate.
   * Verifies that all fromIds carry the same bijectiveKey.
   * Returns the merged node id.
   */
  merge(
    fromIds: string[],
    atomId: string,
    bijectiveKey: string,
    opts?: {
      label?: string;
      tongue?: TongueCode;
      domain?: SemanticDomain;
    }
  ): string {
    if (fromIds.length === 0) throw new Error('merge: fromIds must not be empty');

    for (const fromId of fromIds) {
      const node = this.thread.nodes.get(fromId);
      if (!node) throw new Error(`merge: node '${fromId}' not found`);
      const key = this.nodeKeyMap.get(fromId);
      if (key !== bijectiveKey) {
        throw new Error(
          `merge: node '${fromId}' has bijectiveKey '${key ?? '(none)'}' but expected '${bijectiveKey}'`
        );
      }
    }

    const firstFrom = this.thread.nodes.get(fromIds[0])!;

    const toId = this.addNode({
      label: opts?.label ?? atomId,
      semanticAtomId: atomId,
      tongue: opts?.tongue ?? firstFrom.tongue,
      domain: opts?.domain ?? firstFrom.domain,
      laneIndex: firstFrom.laneIndex,
      depth: firstFrom.depth,
      carriedState: {},
    });

    this.addEdge({
      kind: 'merge',
      from: fromIds[0],
      to: toId,
      bijectiveKey,
      metadata: { allFromIds: fromIds },
    });

    // Check if this merge is occurring inside a tunnel
    for (const { segment, inboundSet } of this.openTunnels.values()) {
      const allInside = fromIds.every((id) => {
        const tunnelId = this.tunnelCreatedNodes.get(id);
        return tunnelId !== undefined || inboundSet.has(id);
      });
      if (allInside) {
        segment.internalMerges.push({ fromNodes: fromIds, toNode: toId, bijectiveKey });
      }
    }

    return toId;
  }

  /**
   * Enter a tunnel segment. All nodes added while this tunnel is open
   * receive a negative depth. Returns the tunnel id.
   */
  enterTunnel(label: string, entryNodeIds: string[]): string {
    const tunnelId = this._genId('tunnel');
    const depth = -(this.openTunnels.size + 1);
    const segment: TunnelSegment = {
      id: tunnelId,
      label,
      depth,
      inboundNodes: [...entryNodeIds],
      outboundNodes: [],
      sideExits: [],
      emergentNodes: [],
      internalMerges: [],
    };
    this.openTunnels.set(tunnelId, { segment, depth, inboundSet: new Set(entryNodeIds) });
    return tunnelId;
  }

  /**
   * Close a tunnel segment. Nodes in exitNodeIds are registered as outbound.
   * Any nodes that were created inside the tunnel without a corresponding
   * inbound link are registered as emergent.
   */
  exitTunnel(tunnelId: string, exitNodeIds: string[]): void {
    const entry = this.openTunnels.get(tunnelId);
    if (!entry) throw new Error(`exitTunnel: tunnel '${tunnelId}' is not open`);

    const { segment, inboundSet } = entry;
    segment.outboundNodes = [...exitNodeIds];

    // Find emergent nodes: created inside the tunnel, not in inboundNodes, not reached by tunnel_enter edge
    const inboundNodeIds = new Set(segment.inboundNodes);
    for (const [nodeId, tId] of this.tunnelCreatedNodes.entries()) {
      if (tId === tunnelId && !inboundNodeIds.has(nodeId)) {
        // Check if this node has any inbound edge from an inbound node
        const hasInboundEdge = this.thread.edges.some(
          (e) => e.to === nodeId && inboundSet.has(e.from as string)
        );
        if (!hasInboundEdge && !segment.emergentNodes.includes(nodeId)) {
          segment.emergentNodes.push(nodeId);
        }
      }
    }

    this.thread.tunnels.push(segment);
    this.openTunnels.delete(tunnelId);
  }

  /**
   * Build and return the final thread.
   */
  build(): SemanticWorkflowThread {
    // Close any still-open tunnels automatically
    for (const [tunnelId, { segment }] of this.openTunnels.entries()) {
      this.thread.tunnels.push(segment);
      this.openTunnels.delete(tunnelId);
    }
    return this.thread;
  }

  /**
   * Generate a WorkflowThreadReceipt for the thread.
   * Call after build() or on the builder directly.
   */
  receipt(): WorkflowThreadReceipt {
    const nodes = [...this.thread.nodes.values()];
    const edges = this.thread.edges;

    const depths = nodes.map((n) => n.depth);
    const minDepth = depths.length ? Math.min(...depths) : 0;
    const maxDepth = depths.length ? Math.max(...depths) : 0;

    const lanes = new Set(nodes.map((n) => n.laneIndex));

    const bijectiveKeySet = new Set<string>();
    for (const e of edges) {
      if (e.bijectiveKey) bijectiveKeySet.add(e.bijectiveKey);
    }

    const handoffCount = edges.filter((e) => e.kind === 'handoff').length;
    const websocketCount = edges.filter((e) => e.kind === 'websocket').length;

    // threadSha256: canonical JSON of sorted nodes+edges
    const canonicalNodes = [...this.thread.nodes.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([, node]) => node);
    const canonicalEdges = [...edges].sort((a, b) => a.id.localeCompare(b.id));
    const canonicalJson = JSON.stringify({ nodes: canonicalNodes, edges: canonicalEdges });
    const threadSha256 = createHash('sha256').update(canonicalJson).digest('hex');

    return {
      schema: 'scbe.workflow_thread.v1',
      threadId: this.thread.threadId,
      label: this.thread.label,
      tongue: this.thread.tongue,
      nodeCount: nodes.length,
      edgeCount: edges.length,
      tunnelCount: this.thread.tunnels.length,
      laneCount: lanes.size,
      depthRange: [minDepth, maxDepth],
      bijectiveKeys: [...bijectiveKeySet],
      handoffCount,
      websocketCount,
      createdAt: new Date().toISOString(),
      threadSha256,
    };
  }

  /**
   * Render an ASCII highway diagram of the thread.
   * Safe ASCII only: uses ->, |, +, -- only.
   */
  render(): string {
    const t = this.thread;
    const sep = '='.repeat(60);
    const divider = '-'.repeat(60);
    const lines: string[] = [];

    lines.push(sep);
    lines.push(`THREAD: ${t.label}  [${t.tongue}]`);
    lines.push(sep);

    // Group nodes by depth: surface (0+) first, then tunnels
    const surfaceNodes = [...t.nodes.values()].filter((n) => n.depth >= 0);
    const tunnelNodes = [...t.nodes.values()].filter((n) => n.depth < 0);

    // Helper: get outgoing edges for a node
    const outEdges = (nodeId: string): ThreadEdge[] => t.edges.filter((e) => e.from === nodeId);

    // Simple surface rendering: iterate surface nodes in insertion order
    if (surfaceNodes.length > 0) {
      // Group by lane
      const byLane = new Map<number, ThreadNode[]>();
      for (const n of surfaceNodes) {
        if (!byLane.has(n.laneIndex)) byLane.set(n.laneIndex, []);
        byLane.get(n.laneIndex)!.push(n);
      }

      for (const [lane, laneNodes] of [...byLane.entries()].sort(([a], [b]) => a - b)) {
        let row = `Lane ${lane}  |  `;
        for (let i = 0; i < laneNodes.length; i++) {
          const node = laneNodes[i];
          row += `${node.label} [${node.tongue}]`;
          const edges = outEdges(node.id);
          if (edges.length > 0) {
            const kind = edges[0].kind;
            row += ` --${kind}--> `;
          }
        }
        lines.push(row);
      }
    }

    // Render tunnels
    for (const tunnel of t.tunnels) {
      lines.push(divider);
      lines.push(`[TUNNEL: ${tunnel.label}]`);

      const tNodes = tunnelNodes.filter(
        (n) =>
          tunnel.inboundNodes.includes(n.id) ||
          tunnel.outboundNodes.includes(n.id) ||
          tunnel.emergentNodes.includes(n.id) ||
          tunnel.sideExits.includes(n.id)
      );

      if (tNodes.length === 0) {
        lines.push('  (empty)');
      } else {
        const byLane = new Map<number, ThreadNode[]>();
        for (const n of tNodes) {
          if (!byLane.has(n.laneIndex)) byLane.set(n.laneIndex, []);
          byLane.get(n.laneIndex)!.push(n);
        }
        for (const [lane, laneNodes] of [...byLane.entries()].sort(([a], [b]) => a - b)) {
          let row = `  Lane ${lane}  |  `;
          for (let i = 0; i < laneNodes.length; i++) {
            const node = laneNodes[i];
            const prefix = tunnel.emergentNodes.includes(node.id) ? '(emergent) ' : '';
            const suffix = tunnel.sideExits.includes(node.id) ? ' (exits tunnel)' : '';
            row += `${prefix}${node.label} [${node.tongue}]${suffix}`;
            if (i < laneNodes.length - 1) row += ' -> ';
          }
          lines.push(row);
        }
      }
      lines.push(divider);
    }

    lines.push(sep);
    return lines.join('\n');
  }
}

// ============================================================================
// Helper functions
// ============================================================================

/**
 * Create a new WorkflowThreadBuilder.
 */
export function createWorkflowThread(label: string, tongue: TongueCode): WorkflowThreadBuilder {
  return new WorkflowThreadBuilder(label, tongue);
}

/**
 * Serialize a SemanticWorkflowThread to a JSON-serializable object.
 * Converts Maps to arrays.
 */
export function serializeThread(thread: SemanticWorkflowThread): object {
  return {
    schemaVersion: thread.schemaVersion,
    threadId: thread.threadId,
    label: thread.label,
    tongue: thread.tongue,
    nodes: [...thread.nodes.values()],
    edges: thread.edges,
    tunnels: thread.tunnels,
  };
}

/**
 * Validate a SemanticWorkflowThread.
 * Checks:
 * - Every edge references existing node ids
 * - bifurcate+merge pairs have matching bijectiveKeys (via edge inspection)
 * - No orphan nodes (nodes with no edge in or out, except the very first node)
 *
 * Returns an array of error strings. Empty array = valid.
 */
export function validateThread(thread: SemanticWorkflowThread): string[] {
  const errors: string[] = [];
  const nodeIds = new Set(thread.nodes.keys());

  // Check all edge node references exist
  for (const edge of thread.edges) {
    if (!nodeIds.has(edge.from)) {
      errors.push(`Edge '${edge.id}' references unknown source node '${edge.from}'`);
    }
    const targets = Array.isArray(edge.to) ? edge.to : [edge.to];
    for (const t of targets) {
      if (!nodeIds.has(t)) {
        errors.push(`Edge '${edge.id}' references unknown target node '${t}'`);
      }
    }
  }

  // Check bijective key consistency: every bifurcate edge should have a corresponding merge edge with the same key
  const bifurcateKeys = new Map<string, string>(); // bijectiveKey -> bifurcate edge id
  const mergeKeys = new Map<string, string>(); // bijectiveKey -> merge edge id

  for (const edge of thread.edges) {
    if (edge.kind === 'bifurcate' && edge.bijectiveKey) {
      bifurcateKeys.set(edge.bijectiveKey, edge.id);
    }
    if (edge.kind === 'merge' && edge.bijectiveKey) {
      mergeKeys.set(edge.bijectiveKey, edge.id);
    }
  }

  for (const [key] of bifurcateKeys) {
    if (!mergeKeys.has(key)) {
      errors.push(`bijectiveKey '${key}' has a bifurcate but no corresponding merge edge`);
    }
  }
  for (const [key] of mergeKeys) {
    if (!bifurcateKeys.has(key)) {
      errors.push(`bijectiveKey '${key}' has a merge but no corresponding bifurcate edge`);
    }
  }

  // Check orphan nodes (skip if only one node or zero edges)
  if (thread.nodes.size > 1 && thread.edges.length > 0) {
    const connectedNodes = new Set<string>();
    for (const edge of thread.edges) {
      connectedNodes.add(edge.from);
      const targets = Array.isArray(edge.to) ? edge.to : [edge.to];
      for (const t of targets) connectedNodes.add(t);
    }
    for (const nodeId of nodeIds) {
      if (!connectedNodes.has(nodeId)) {
        errors.push(`Node '${nodeId}' is an orphan (no edges connect to it)`);
      }
    }
  }

  return errors;
}
