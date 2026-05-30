#!/usr/bin/env node
'use strict';
/**
 * vector_field_bench.cjs — Multi-Lattice Vector Field Navigation benchmark CLI.
 *
 * Usage:
 *   node packages/agent-bus/scripts/vector_field_bench.cjs
 *       Run full benchmark (all mazes, all algorithms, ablation table).
 *
 *   node ... --maze tiny --alg multi-lattice
 *       Single maze + algorithm run.
 *
 *   node ... --list-mazes
 *       Print available maze configs.
 *
 *   node ... --show-comparison
 *       Output comparison table only (suppresses per-run details).
 *
 *   node ... --show-ablation
 *       Output ablation table only.
 *
 *   node ... --skip-ablation
 *       Run only the 5 algorithms (no ablation, faster).
 *
 *   node ... --random-solve-sweep --runs 24
 *       Run deterministic randomized mazes with the random policy.
 *
 *   node ... --maze tiny --alg multi-lattice --show-heat-map
 *       Include fluidic heat-map and pressure samples for a single run.
 */

const {
  runNavBench,
  generateMaze,
  oracleBFS,
  runMission,
  scoreRun,
  runRandomSolveSweep,
  buildFluidHeatMap,
  DEFAULT_WEIGHTS,
  BENCHMARK_MAZES,
} = require('../dist/index.js');

const args = process.argv.slice(2);

function flag(name) {
  return args.includes(`--${name}`);
}

function opt(name) {
  const idx = args.indexOf(`--${name}`);
  if (idx !== -1 && idx + 1 < args.length) return args[idx + 1];
  return null;
}

if (flag('list-mazes')) {
  console.log(JSON.stringify(BENCHMARK_MAZES, null, 2));
  process.exit(0);
}

const mazeName = opt('maze');
const algName = opt('alg');
const randomSweep = flag('random-solve-sweep');
const showHeatMap = flag('show-heat-map');

if (randomSweep) {
  const runs = Number.parseInt(opt('runs') ?? '24', 10);
  const seed = Number.parseInt(opt('seed') ?? '9001', 10);
  console.log(
    JSON.stringify(
      runRandomSolveSweep({
        trials: Number.isFinite(runs) ? runs : 24,
        seed: Number.isFinite(seed) ? seed : 9001,
      }),
      null,
      2
    )
  );
  process.exit(0);
}

if (mazeName && algName) {
  const cfg = BENCHMARK_MAZES.find((m) => m.id === mazeName);
  if (!cfg) {
    console.error(`Unknown maze: ${mazeName}. Use --list-mazes to see options.`);
    process.exit(1);
  }
  const maze = generateMaze(cfg);
  const oraclePath = oracleBFS(maze) ?? [];
  const t0 = Date.now();
  const agent = runMission(maze, cfg, algName, DEFAULT_WEIGHTS, oraclePath);
  const score = scoreRun(agent, maze, cfg, algName, oraclePath, Date.now() - t0);
  const output = showHeatMap
    ? { score, fluid_heat_map: buildFluidHeatMap(agent).slice(0, 32) }
    : score;
  console.log(JSON.stringify(output, null, 2));
  process.exit(0);
}

// Full benchmark.
const skipAblation = flag('skip-ablation');
const showComparison = flag('show-comparison');
const showAblation = flag('show-ablation');

const result = runNavBench({ skip_ablation: skipAblation });

if (showComparison) {
  console.log(JSON.stringify({ comparison: result.comparison }, null, 2));
} else if (showAblation) {
  console.log(JSON.stringify({ ablation_table: result.ablation_table }, null, 2));
} else {
  console.log(JSON.stringify(result, null, 2));
}
