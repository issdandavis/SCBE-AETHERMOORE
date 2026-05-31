/**
 * @file star-path.ts
 * @module agent-bus/star-path
 * @layer Cross-layer routing benchmark
 * @component StarPath — tool-graph mission planner
 *
 * The path IS the mission. Tools are spacecraft systems; Sacred Tongue domains
 * are sections of the ship. Pathfinding algorithms plan the trajectory.
 * Governance cost is delta-V: how much fuel a mission burns through security layers.
 * Hub tools are gravity assists — they bend trajectories across domains for free.
 */

import fs from 'node:fs';

// ─── Types ───────────────────────────────────────────────────────────────────

/** Sacred Tongue domain: the "section" of the spacecraft a tool belongs to. */
export type Tongue = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/**
 * How the trajectory moves between tools.
 * hyperspace: same domain (straight burn, minimum delta-V)
 * orbital:    cross-domain without a hub (high delta-V curve)
 * gravity-assist: cross-domain via hub tool (reduced cost)
 */
export type TraversalType = 'hyperspace' | 'orbital' | 'gravity-assist';

export type Algorithm = 'bfs' | 'dijkstra' | 'astar';

export interface StarNode {
  name: string;
  tongue: Tongue;
  command: 'node' | 'python';
  isHub: boolean;
  /** Extra cost on outgoing edges — governance layers that consume delta-V. */
  governanceCost: number;
}

export interface StarEdge {
  from: string;
  to: string;
  cost: number;
  traversal: TraversalType;
}

export interface StarGraph {
  nodes: Map<string, StarNode>;
  /** Adjacency list: tool name → outgoing edges. */
  edges: Map<string, StarEdge[]>;
}

export interface MissionPhase {
  tool: string;
  tongue: Tongue;
  traversal: TraversalType;
  cost: number;
  is_hub_assist: boolean;
}

export interface MissionTrajectory {
  algorithm: Algorithm;
  mission: string;
  start: string;
  goal: string;
  phases: MissionPhase[];
  total_delta_v: number;
  hops: number;
  governance_bends: number;
  traversal_dominant: TraversalType;
  abort_node?: string;
  ms: number;
}

export interface GalaxyMap {
  KO: string[];
  AV: string[];
  RU: string[];
  CA: string[];
  UM: string[];
  DR: string[];
}

export interface StarPathBenchResult {
  schema_version: 'scbe.agent_bus.star_path_bench.v1';
  tool_count: number;
  edge_count: number;
  galaxy_map: GalaxyMap;
  hub_tools: string[];
  /** Longest min-cost path (mission with highest minimum delta-V). */
  diameter: number;
  avg_delta_v: number;
  reachable_pairs: number;
  unreachable_pairs: number;
  traversal_distribution: {
    hyperspace: number;
    orbital: number;
    gravity_assist: number;
  };
  /** Canonical mission arcs, or a live-registry fallback arc, run through all three algorithms. */
  missions: MissionTrajectory[];
  all_pairs_summary: {
    bfs_avg_hops: number;
    dijkstra_avg_delta_v: number;
    astar_avg_delta_v: number;
  };
  total_ms: number;
}

// ─── Tongue distance (phi-ordered adjacency) ──────────────────────────────────

// KO(1.00) → AV(1.62) → RU(2.62) → CA(4.24) → UM(6.85) → DR(11.09)
const TONGUE_ORDER: Tongue[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];

function tongueDistance(a: Tongue, b: Tongue): number {
  return Math.abs(TONGUE_ORDER.indexOf(a) - TONGUE_ORDER.indexOf(b));
}

// ─── Tool classification ──────────────────────────────────────────────────────

const HUB_NAMES = new Set(['scbe-agentbus', 'scbe-compass', 'scbe-hermes']);
const GEOSEAL_RE = /^geoseal-/;
const RESEARCH_RE = /^research-/;
const RU_NAMES = new Set([
  'scbe-antivirus',
  'scbe-governance-fuse',
  'scbe-runtime',
  'scbe-flow',
  'scbe-tongues',
  'tokenizer-atomic-selfcheck',
]);
const DR_NAMES = new Set([
  'scbe-agentbus',
  'ai-router-health',
  'ai-router-call',
  'agentic-pazaak-board',
  'coding-board-trial',
  'chessboard-dev-stack',
]);
const UM_NAMES = new Set([
  'video-pocket-director',
  'youtube-video-review',
  'youtube-article-dry-run',
  'youtube-upload-unlisted',
  'writing-roundtable-review',
]);

interface RawTool {
  name: string;
  command: string;
  args: string[];
}

function classifyTool(raw: RawTool): StarNode {
  const name = raw.name;
  const command = raw.command === 'node' ? 'node' : 'python';
  const isHub = HUB_NAMES.has(name);

  let tongue: Tongue;
  if (command === 'node') tongue = 'KO';
  else if (GEOSEAL_RE.test(name)) tongue = 'CA';
  else if (RESEARCH_RE.test(name)) tongue = 'AV';
  else if (RU_NAMES.has(name)) tongue = 'RU';
  else if (DR_NAMES.has(name)) tongue = 'DR';
  else if (UM_NAMES.has(name)) tongue = 'UM';
  else tongue = 'RU';

  let governanceCost = 0;
  if (GEOSEAL_RE.test(name)) governanceCost = 2;
  else if (name.startsWith('scbe-governance') || name.startsWith('scbe-antivirus'))
    governanceCost = 1;
  else if (name.includes('upload') || name.includes('youtube-upload')) governanceCost = 1;

  return { name, tongue, command, isHub, governanceCost };
}

// ─── Graph builder ────────────────────────────────────────────────────────────

function baseEdgeCost(from: StarNode, to: StarNode): number {
  if (from.tongue === to.tongue) return 1;
  if (from.isHub || to.isHub) return 2;
  return Math.max(2, tongueDistance(from.tongue, to.tongue) + 1);
}

function edgeTraversal(from: StarNode, to: StarNode): TraversalType {
  if (from.tongue === to.tongue) return 'hyperspace';
  if (from.isHub || to.isHub) return 'gravity-assist';
  return 'orbital';
}

export function buildStarGraph(toolsJsonPath: string): StarGraph {
  const raw: RawTool[] = JSON.parse(fs.readFileSync(toolsJsonPath, 'utf8'));
  const nodes = new Map<string, StarNode>();
  const edges = new Map<string, StarEdge[]>();

  for (const t of raw) {
    const node = classifyTool(t);
    nodes.set(node.name, node);
    edges.set(node.name, []);
  }

  const nodeList = [...nodes.values()];
  for (const from of nodeList) {
    for (const to of nodeList) {
      if (from.name === to.name) continue;
      // Connect within same tongue, across hubs, or same runtime
      if (from.tongue === to.tongue || from.isHub || to.isHub || from.command === to.command) {
        const cost = baseEdgeCost(from, to) + from.governanceCost;
        const traversal = edgeTraversal(from, to);
        edges.get(from.name)!.push({ from: from.name, to: to.name, cost, traversal });
      }
    }
  }

  return { nodes, edges };
}

export function buildGalaxyMap(graph: StarGraph): GalaxyMap {
  const map: GalaxyMap = { KO: [], AV: [], RU: [], CA: [], UM: [], DR: [] };
  for (const node of graph.nodes.values()) map[node.tongue].push(node.name);
  return map;
}

// ─── Min-heap ─────────────────────────────────────────────────────────────────

class MinHeap<T> {
  private h: { k: number; v: T }[] = [];

  push(k: number, v: T): void {
    this.h.push({ k, v });
    this._up(this.h.length - 1);
  }

  pop(): T | undefined {
    if (!this.h.length) return undefined;
    const top = this.h[0]!.v;
    const last = this.h.pop()!;
    if (this.h.length) {
      this.h[0] = last;
      this._down(0);
    }
    return top;
  }

  get size() {
    return this.h.length;
  }

  private _up(i: number) {
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (this.h[p]!.k <= this.h[i]!.k) break;
      [this.h[p], this.h[i]] = [this.h[i]!, this.h[p]!];
      i = p;
    }
  }

  private _down(i: number) {
    const n = this.h.length;
    while (true) {
      let s = i,
        l = 2 * i + 1,
        r = 2 * i + 2;
      if (l < n && this.h[l]!.k < this.h[s]!.k) s = l;
      if (r < n && this.h[r]!.k < this.h[s]!.k) s = r;
      if (s === i) break;
      [this.h[i], this.h[s]] = [this.h[s]!, this.h[i]!];
      i = s;
    }
  }
}

// ─── Path reconstruction ──────────────────────────────────────────────────────

function reconstructPath(parent: Map<string, string>, start: string, goal: string): string[] {
  const path: string[] = [];
  let curr = goal;
  while (curr !== start) {
    path.unshift(curr);
    curr = parent.get(curr)!;
  }
  path.unshift(start);
  return path;
}

function buildTrajectory(
  algo: Algorithm,
  mission: string,
  graph: StarGraph,
  path: string[],
  ms: number
): MissionTrajectory {
  let totalDeltaV = 0;
  let governanceBends = 0;
  const phases: MissionPhase[] = [];
  const traversalCounts = { hyperspace: 0, orbital: 0, 'gravity-assist': 0 };

  for (let i = 0; i < path.length - 1; i++) {
    const fromNode = graph.nodes.get(path[i]!)!;
    const toNode = graph.nodes.get(path[i + 1]!)!;
    const edge = graph.edges.get(path[i]!)!.find((e) => e.to === path[i + 1]!)!;
    totalDeltaV += edge.cost;
    if (fromNode.governanceCost > 0) governanceBends++;
    traversalCounts[edge.traversal]++;
    phases.push({
      tool: path[i + 1]!,
      tongue: toNode.tongue,
      traversal: edge.traversal,
      cost: edge.cost,
      is_hub_assist: fromNode.isHub || toNode.isHub,
    });
  }

  let dominant: TraversalType = 'hyperspace';
  let maxCount = 0;
  for (const [t, c] of Object.entries(traversalCounts) as [TraversalType, number][]) {
    if (c > maxCount) {
      maxCount = c;
      dominant = t;
    }
  }

  // Abort node: nearest hub in the path (fallback routing point)
  const abortNode = path.slice(1, -1).find((n) => graph.nodes.get(n)?.isHub);

  return {
    algorithm: algo,
    mission,
    start: path[0]!,
    goal: path[path.length - 1]!,
    phases,
    total_delta_v: totalDeltaV,
    hops: path.length - 1,
    governance_bends: governanceBends,
    traversal_dominant: dominant,
    ...(abortNode !== undefined ? { abort_node: abortNode } : {}),
    ms: parseFloat(ms.toFixed(4)),
  };
}

// ─── Algorithms ───────────────────────────────────────────────────────────────

export function bfs(graph: StarGraph, start: string, goal: string): MissionTrajectory | null {
  const t0 = performance.now();
  if (!graph.nodes.has(start) || !graph.nodes.has(goal)) return null;

  const visited = new Set<string>([start]);
  const parent = new Map<string, string>();
  const queue: string[] = [start];

  while (queue.length) {
    const curr = queue.shift()!;
    if (curr === goal) {
      const path = reconstructPath(parent, start, goal);
      return buildTrajectory('bfs', `${start} → ${goal}`, graph, path, performance.now() - t0);
    }
    for (const edge of graph.edges.get(curr) ?? []) {
      if (!visited.has(edge.to)) {
        visited.add(edge.to);
        parent.set(edge.to, curr);
        queue.push(edge.to);
      }
    }
  }
  return null;
}

export function dijkstra(graph: StarGraph, start: string, goal: string): MissionTrajectory | null {
  const t0 = performance.now();
  if (!graph.nodes.has(start) || !graph.nodes.has(goal)) return null;

  const dist = new Map<string, number>();
  const parent = new Map<string, string>();
  const heap = new MinHeap<string>();

  for (const name of graph.nodes.keys()) dist.set(name, Infinity);
  dist.set(start, 0);
  heap.push(0, start);

  while (heap.size) {
    const curr = heap.pop()!;
    if (curr === goal) {
      const path = reconstructPath(parent, start, goal);
      return buildTrajectory('dijkstra', `${start} → ${goal}`, graph, path, performance.now() - t0);
    }
    const d = dist.get(curr)!;
    for (const edge of graph.edges.get(curr) ?? []) {
      const nd = d + edge.cost;
      if (nd < dist.get(edge.to)!) {
        dist.set(edge.to, nd);
        parent.set(edge.to, curr);
        heap.push(nd, edge.to);
      }
    }
  }
  return null;
}

export function aStar(graph: StarGraph, start: string, goal: string): MissionTrajectory | null {
  const t0 = performance.now();
  if (!graph.nodes.has(start) || !graph.nodes.has(goal)) return null;

  const goalTongue = graph.nodes.get(goal)!.tongue;
  // 0.4x multiplier keeps h admissible: max tongue distance (5) * 0.4 = 2.0,
  // which never exceeds the minimum hub edge cost of 2.
  const h = (name: string) => tongueDistance(graph.nodes.get(name)!.tongue, goalTongue) * 0.4;

  const g = new Map<string, number>();
  const parent = new Map<string, string>();
  const heap = new MinHeap<string>();

  for (const name of graph.nodes.keys()) g.set(name, Infinity);
  g.set(start, 0);
  heap.push(h(start), start);

  while (heap.size) {
    const curr = heap.pop()!;
    if (curr === goal) {
      const path = reconstructPath(parent, start, goal);
      return buildTrajectory('astar', `${start} → ${goal}`, graph, path, performance.now() - t0);
    }
    const gCurr = g.get(curr)!;
    for (const edge of graph.edges.get(curr) ?? []) {
      const ng = gCurr + edge.cost;
      if (ng < g.get(edge.to)!) {
        g.set(edge.to, ng);
        parent.set(edge.to, curr);
        heap.push(ng + h(edge.to), edge.to);
      }
    }
  }
  return null;
}

// ─── Canonical mission arcs ───────────────────────────────────────────────────

/**
 * Six missions where the path IS the mission arc — not just navigation,
 * but the complete activation sequence from launch to objective.
 */
const CANONICAL_MISSIONS: { name: string; start: string; goal: string }[] = [
  { name: 'Spec Forge', start: 'tool-validate', goal: 'geoseal-compile' },
  { name: 'Deep Survey', start: 'research-arxiv', goal: 'scbe-agentbus' },
  { name: 'Signal Relay', start: 'binary-hex-compiler', goal: 'ai-router-call' },
  { name: 'Governance Transit', start: 'geoseal-exec', goal: 'writing-roundtable-review' },
  { name: 'Star Charts', start: 'scbe-compass', goal: 'research-pubmed' },
  { name: 'Supply Run', start: 'tool-list', goal: 'youtube-upload-unlisted' },
];

// ─── Full benchmark ───────────────────────────────────────────────────────────

export function runStarPathBench(toolsJsonPath: string): StarPathBenchResult {
  const t0 = performance.now();
  const graph = buildStarGraph(toolsJsonPath);
  const nodeNames = [...graph.nodes.keys()];
  const n = nodeNames.length;

  let edgeCount = 0;
  for (const edges of graph.edges.values()) edgeCount += edges.length;

  // All-pairs stats via BFS + Dijkstra
  let bfsTotalHops = 0,
    dijkTotalCost = 0,
    astarTotalCost = 0;
  let reachable = 0,
    unreachable = 0;
  let diameter = 0;
  let fallbackMission: { start: string; goal: string; cost: number } | undefined;
  const travDistrib: StarPathBenchResult['traversal_distribution'] = {
    hyperspace: 0,
    orbital: 0,
    gravity_assist: 0,
  };

  for (const start of nodeNames) {
    for (const goal of nodeNames) {
      if (start === goal) continue;
      const bfsR = bfs(graph, start, goal);
      if (bfsR) {
        reachable++;
        bfsTotalHops += bfsR.hops;
        const dijR = dijkstra(graph, start, goal);
        const asR = aStar(graph, start, goal);
        if (dijR) {
          dijkTotalCost += dijR.total_delta_v;
          diameter = Math.max(diameter, dijR.total_delta_v);
          if (!fallbackMission || dijR.total_delta_v > fallbackMission.cost) {
            fallbackMission = { start, goal, cost: dijR.total_delta_v };
          }
        }
        if (asR) astarTotalCost += asR.total_delta_v;
        const key = (
          bfsR.traversal_dominant === 'gravity-assist' ? 'gravity_assist' : bfsR.traversal_dominant
        ) as keyof typeof travDistrib;
        if (key in travDistrib) travDistrib[key]++;
      } else {
        unreachable++;
      }
    }
  }

  // Canonical mission trajectories (all three algorithms)
  const missions: MissionTrajectory[] = [];
  for (const m of CANONICAL_MISSIONS) {
    if (graph.nodes.has(m.start) && graph.nodes.has(m.goal)) {
      for (const algo of ['bfs', 'dijkstra', 'astar'] as Algorithm[]) {
        const fn = algo === 'bfs' ? bfs : algo === 'dijkstra' ? dijkstra : aStar;
        const r = fn(graph, m.start, m.goal);
        if (r) missions.push({ ...r, mission: m.name });
      }
    }
  }
  if (missions.length === 0 && fallbackMission) {
    for (const algo of ['bfs', 'dijkstra', 'astar'] as Algorithm[]) {
      const fn = algo === 'bfs' ? bfs : algo === 'dijkstra' ? dijkstra : aStar;
      const r = fn(graph, fallbackMission.start, fallbackMission.goal);
      if (r) missions.push({ ...r, mission: 'Live Registry Fallback' });
    }
  }

  const hubTools = [...graph.nodes.values()].filter((nd) => nd.isHub).map((nd) => nd.name);

  return {
    schema_version: 'scbe.agent_bus.star_path_bench.v1',
    tool_count: n,
    edge_count: edgeCount,
    galaxy_map: buildGalaxyMap(graph),
    hub_tools: hubTools,
    diameter,
    avg_delta_v: reachable > 0 ? parseFloat((dijkTotalCost / reachable).toFixed(3)) : 0,
    reachable_pairs: reachable,
    unreachable_pairs: unreachable,
    traversal_distribution: travDistrib,
    missions,
    all_pairs_summary: {
      bfs_avg_hops: reachable > 0 ? parseFloat((bfsTotalHops / reachable).toFixed(3)) : 0,
      dijkstra_avg_delta_v: reachable > 0 ? parseFloat((dijkTotalCost / reachable).toFixed(3)) : 0,
      astar_avg_delta_v: reachable > 0 ? parseFloat((astarTotalCost / reachable).toFixed(3)) : 0,
    },
    total_ms: parseFloat((performance.now() - t0).toFixed(2)),
  };
}
