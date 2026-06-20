/**
 * @file star-path.test.ts
 * Tests for the StarPath tool-graph mission planner.
 * Covers graph construction, all three algorithms, galaxy map, and full bench.
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  buildStarGraph,
  buildGalaxyMap,
  bfs,
  dijkstra,
  aStar,
  runStarPathBench,
  type StarGraph,
  type MissionTrajectory,
} from '../src/index.js';

// ─── Fixture ─────────────────────────────────────────────────────────────────

interface MinTool {
  name: string;
  command: string;
  args: string[];
}

function tempGraph(tools: MinTool[]): { dir: string; file: string; graph: StarGraph } {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-star-path-'));
  const file = path.join(dir, 'tools.json');
  fs.writeFileSync(file, JSON.stringify(tools, null, 2) + '\n', 'utf8');
  const graph = buildStarGraph(file);
  return { dir, file, graph };
}

function cleanup(dir: string) {
  fs.rmSync(dir, { recursive: true, force: true });
}

const MINIMAL_TOOLS: MinTool[] = [
  // KO (node)
  { name: 'ko-alpha', command: 'node', args: ['a.cjs', '{task}'] },
  { name: 'ko-beta', command: 'node', args: ['b.cjs', '{task}'] },
  // KO hub
  { name: 'scbe-compass', command: 'node', args: ['compass.cjs', '{task}'] },
  // CA (geoseal)
  { name: 'geoseal-compile', command: 'python', args: ['-m', 'src.geoseal', 'compile', '{task}'] },
  { name: 'geoseal-exec', command: 'python', args: ['-m', 'src.geoseal', 'exec', '{task}'] },
  // AV (research)
  {
    name: 'research-arxiv',
    command: 'python',
    args: ['scripts/research.py', '--api', 'arxiv', '{task}'],
  },
  // DR (oracle)
  { name: 'scbe-agentbus', command: 'python', args: ['scripts/bus.py', '--task', '{task}'] },
];

// ─── buildStarGraph ───────────────────────────────────────────────────────────

describe('buildStarGraph', () => {
  it('creates a node for every tool in the registry', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      expect(graph.nodes.size).toBe(MINIMAL_TOOLS.length);
    } finally {
      cleanup(dir);
    }
  });

  it('marks scbe-compass and scbe-agentbus as hubs', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      expect(graph.nodes.get('scbe-compass')?.isHub).toBe(true);
      expect(graph.nodes.get('scbe-agentbus')?.isHub).toBe(true);
    } finally {
      cleanup(dir);
    }
  });

  it('assigns KO tongue to node-command tools', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      expect(graph.nodes.get('ko-alpha')?.tongue).toBe('KO');
      expect(graph.nodes.get('ko-beta')?.tongue).toBe('KO');
    } finally {
      cleanup(dir);
    }
  });

  it('assigns CA tongue to geoseal-* tools', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      expect(graph.nodes.get('geoseal-compile')?.tongue).toBe('CA');
      expect(graph.nodes.get('geoseal-exec')?.tongue).toBe('CA');
    } finally {
      cleanup(dir);
    }
  });

  it('assigns AV tongue to research-* tools', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      expect(graph.nodes.get('research-arxiv')?.tongue).toBe('AV');
    } finally {
      cleanup(dir);
    }
  });

  it('assigns higher governance cost to geoseal tools', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      expect(graph.nodes.get('geoseal-compile')!.governanceCost).toBe(2);
      expect(graph.nodes.get('ko-alpha')!.governanceCost).toBe(0);
    } finally {
      cleanup(dir);
    }
  });

  it('builds at least one edge per node', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      for (const [name, edges] of graph.edges) {
        expect(edges.length).toBeGreaterThan(0);
      }
    } finally {
      cleanup(dir);
    }
  });

  it('no self-loops in edge list', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      for (const [from, edges] of graph.edges) {
        for (const edge of edges) {
          expect(edge.from).not.toBe(edge.to);
        }
      }
    } finally {
      cleanup(dir);
    }
  });
});

// ─── BFS ──────────────────────────────────────────────────────────────────────

describe('bfs', () => {
  it('finds a same-tongue path in 1 hop', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const r = bfs(graph, 'ko-alpha', 'ko-beta');
      expect(r).not.toBeNull();
      expect(r!.hops).toBe(1);
    } finally {
      cleanup(dir);
    }
  });

  it('path always starts at start and ends at goal', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const r = bfs(graph, 'ko-alpha', 'geoseal-compile');
      expect(r).not.toBeNull();
      expect(r!.start).toBe('ko-alpha');
      expect(r!.goal).toBe('geoseal-compile');
    } finally {
      cleanup(dir);
    }
  });

  it('returns null for nonexistent start', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      expect(bfs(graph, 'phantom-tool', 'ko-alpha')).toBeNull();
    } finally {
      cleanup(dir);
    }
  });

  it('returns null for nonexistent goal', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      expect(bfs(graph, 'ko-alpha', 'phantom-tool')).toBeNull();
    } finally {
      cleanup(dir);
    }
  });

  it('path phases length equals hops', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const r = bfs(graph, 'ko-alpha', 'research-arxiv');
      expect(r).not.toBeNull();
      expect(r!.phases.length).toBe(r!.hops);
    } finally {
      cleanup(dir);
    }
  });
});

// ─── Dijkstra ─────────────────────────────────────────────────────────────────

describe('dijkstra', () => {
  it('finds minimum cost path between two tools', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const r = dijkstra(graph, 'ko-alpha', 'geoseal-compile');
      expect(r).not.toBeNull();
      expect(r!.total_delta_v).toBeGreaterThan(0);
    } finally {
      cleanup(dir);
    }
  });

  it('same-tongue path has lower delta-V than cross-tongue direct path', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const same = dijkstra(graph, 'ko-alpha', 'ko-beta');
      const cross = dijkstra(graph, 'ko-alpha', 'geoseal-compile');
      expect(same).not.toBeNull();
      expect(cross).not.toBeNull();
      expect(same!.total_delta_v).toBeLessThanOrEqual(cross!.total_delta_v);
    } finally {
      cleanup(dir);
    }
  });

  it('returns null for nonexistent nodes', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      expect(dijkstra(graph, 'ghost', 'ko-alpha')).toBeNull();
    } finally {
      cleanup(dir);
    }
  });

  it('total_delta_v equals sum of phase costs', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const r = dijkstra(graph, 'research-arxiv', 'geoseal-compile');
      if (!r) return;
      const sumCost = r.phases.reduce((s, p) => s + p.cost, 0);
      expect(r.total_delta_v).toBe(sumCost);
    } finally {
      cleanup(dir);
    }
  });
});

// ─── A* ───────────────────────────────────────────────────────────────────────

describe('aStar', () => {
  it('returns same or lower delta-V as BFS (admissible heuristic)', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const bfsR = bfs(graph, 'ko-alpha', 'research-arxiv');
      const asR = aStar(graph, 'ko-alpha', 'research-arxiv');
      expect(bfsR).not.toBeNull();
      expect(asR).not.toBeNull();
      // A* with admissible heuristic finds optimal cost (≤ BFS delta-V)
      expect(asR!.total_delta_v).toBeLessThanOrEqual(bfsR!.total_delta_v);
    } finally {
      cleanup(dir);
    }
  });

  it('A* and Dijkstra delta-V are equal (both optimal)', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const dijR = dijkstra(graph, 'ko-alpha', 'geoseal-exec');
      const asR = aStar(graph, 'ko-alpha', 'geoseal-exec');
      if (!dijR || !asR) return;
      expect(asR.total_delta_v).toBe(dijR.total_delta_v);
    } finally {
      cleanup(dir);
    }
  });

  it('path is consistent with start and goal', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const r = aStar(graph, 'ko-alpha', 'scbe-agentbus');
      expect(r).not.toBeNull();
      expect(r!.start).toBe('ko-alpha');
      expect(r!.goal).toBe('scbe-agentbus');
    } finally {
      cleanup(dir);
    }
  });
});

// ─── buildGalaxyMap ───────────────────────────────────────────────────────────

describe('buildGalaxyMap', () => {
  it('every tool appears in exactly one tongue bucket', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const map = buildGalaxyMap(graph);
      const all = [...Object.values(map)].flat();
      expect(all.length).toBe(MINIMAL_TOOLS.length);
      const unique = new Set(all);
      expect(unique.size).toBe(MINIMAL_TOOLS.length);
    } finally {
      cleanup(dir);
    }
  });

  it('KO bucket contains all node-command tools', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const map = buildGalaxyMap(graph);
      expect(map.KO).toContain('ko-alpha');
      expect(map.KO).toContain('ko-beta');
      expect(map.KO).toContain('scbe-compass');
    } finally {
      cleanup(dir);
    }
  });

  it('CA bucket contains geoseal tools', () => {
    const { dir, graph } = tempGraph(MINIMAL_TOOLS);
    try {
      const map = buildGalaxyMap(graph);
      expect(map.CA).toContain('geoseal-compile');
      expect(map.CA).toContain('geoseal-exec');
    } finally {
      cleanup(dir);
    }
  });
});

// ─── runStarPathBench ─────────────────────────────────────────────────────────

describe('runStarPathBench', () => {
  const repoRoot = path.resolve(__dirname, '..', '..', '..');
  const realToolsJson = path.join(repoRoot, 'packages', 'agent-bus', 'tools.json');

  it('runs against real tools.json without throwing', () => {
    const result = runStarPathBench(realToolsJson);
    expect(result.schema_version).toBe('scbe.agent_bus.star_path_bench.v1');
    expect(result.tool_count).toBeGreaterThan(0);
  });

  it('reachable + unreachable = n*(n-1)', () => {
    const result = runStarPathBench(realToolsJson);
    const n = result.tool_count;
    expect(result.reachable_pairs + result.unreachable_pairs).toBe(n * (n - 1));
  });

  it('hub_tools contains scbe-agentbus', () => {
    const result = runStarPathBench(realToolsJson);
    expect(result.hub_tools).toContain('scbe-agentbus');
  });

  it('missions array is non-empty', () => {
    const result = runStarPathBench(realToolsJson);
    expect(result.missions.length).toBeGreaterThan(0);
  });

  it('diameter is positive', () => {
    const result = runStarPathBench(realToolsJson);
    expect(result.diameter).toBeGreaterThan(0);
  });

  it('every galaxy bucket is an array', () => {
    const result = runStarPathBench(realToolsJson);
    for (const bucket of Object.values(result.galaxy_map)) {
      expect(Array.isArray(bucket)).toBe(true);
    }
  });

  it('total_ms is positive', () => {
    const result = runStarPathBench(realToolsJson);
    expect(result.total_ms).toBeGreaterThan(0);
  });
});
