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
 */

const {
  runNavBench,
  generateMaze,
  oracleBFS,
  runMission,
  scoreRun,
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
  console.log(JSON.stringify(score, null, 2));
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
