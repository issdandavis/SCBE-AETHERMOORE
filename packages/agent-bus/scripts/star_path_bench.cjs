#!/usr/bin/env node
'use strict';
/**
 * Star Path Benchmark CLI
 * Runs BFS, Dijkstra, and A* over the tool graph and reports mission trajectories.
 *
 * Usage:
 *   node packages/agent-bus/scripts/star_path_bench.cjs
 *   node packages/agent-bus/scripts/star_path_bench.cjs --tools-json path/to/tools.json
 *   node packages/agent-bus/scripts/star_path_bench.cjs --start tool-validate --goal geoseal-compile
 *   node packages/agent-bus/scripts/star_path_bench.cjs --galaxy-only
 */

const path = require('node:path');

const pkgRoot = path.resolve(__dirname, '..');
const { runStarPathBench, buildStarGraph, buildGalaxyMap, bfs, dijkstra, aStar } = require(
  path.join(pkgRoot, 'dist', 'index.js')
);

function parseArgs(argv) {
  const flags = {};
  for (let i = 2; i < argv.length; i++) {
    const tok = argv[i];
    if (!tok.startsWith('--')) continue;
    const key = tok.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      flags[key] = true;
    } else {
      flags[key] = next;
      i++;
    }
  }
  return flags;
}

function printJson(obj) {
  process.stdout.write(JSON.stringify(obj, null, 2) + '\n');
}

function main() {
  const flags = parseArgs(process.argv);
  const toolsJson = String(flags['tools-json'] || path.join(pkgRoot, 'tools.json'));

  // Point-to-point mode: single trajectory
  if (flags.start && flags.goal) {
    const graph = buildStarGraph(toolsJson);
    const start = String(flags.start);
    const goal = String(flags.goal);
    const results = {
      schema_version: 'scbe.agent_bus.star_path_bench.v1',
      mode: 'point_to_point',
      start,
      goal,
      trajectories: [
        bfs(graph, start, goal),
        dijkstra(graph, start, goal),
        aStar(graph, start, goal),
      ].filter(Boolean),
    };
    printJson(results);
    return;
  }

  // Galaxy map only
  if (flags['galaxy-only']) {
    const graph = buildStarGraph(toolsJson);
    printJson({
      schema_version: 'scbe.agent_bus.star_path_bench.v1',
      mode: 'galaxy_map',
      galaxy_map: buildGalaxyMap(graph),
      hub_tools: [...graph.nodes.values()].filter((n) => n.isHub).map((n) => n.name),
    });
    return;
  }

  // Full benchmark
  const result = runStarPathBench(toolsJson);
  printJson(result);
}

try {
  main();
} catch (err) {
  process.stderr.write(`${err instanceof Error ? err.message : String(err)}\n`);
  process.exitCode = 1;
}
