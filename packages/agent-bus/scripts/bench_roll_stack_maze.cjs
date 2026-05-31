#!/usr/bin/env node

const crypto = require('node:crypto');
const { performance } = require('node:perf_hooks');
const path = require('node:path');

const pkgRoot = path.resolve(__dirname, '..');
const { buildScbeRollStack } = require(path.join(pkgRoot, 'dist', 'index.js'));

const TASK = 'solve maze pathfinding benchmark with execution receipt';

const CASES = [
  {
    id: 'open-5x5',
    expected: 'solvable',
    grid: ['S....', '.###.', '...#.', '.#...', '...G.'],
  },
  {
    id: 'corridor-turn',
    expected: 'solvable',
    grid: ['S#...', '.#.#.', '.#.#.', '...#G', '.....'],
  },
  {
    id: 'sealed-goal',
    expected: 'unsolvable',
    grid: ['S#G', '###', '...'],
  },
  {
    id: 'missing-start',
    expected: 'invalid',
    grid: ['...', '.#.', '..G'],
  },
];

function sha256(value) {
  return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function percentile(values, pct) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.ceil((pct / 100) * sorted.length) - 1);
  return sorted[index];
}

function parseMaze(grid) {
  if (!Array.isArray(grid) || grid.length === 0) {
    return { ok: false, reason: 'grid must contain at least one row' };
  }
  const width = grid[0].length;
  if (width === 0) return { ok: false, reason: 'grid rows must be non-empty' };

  let start = null;
  let goal = null;
  for (let y = 0; y < grid.length; y += 1) {
    if (grid[y].length !== width) return { ok: false, reason: 'grid rows must be rectangular' };
    for (let x = 0; x < width; x += 1) {
      const cell = grid[y][x];
      if (!'.#SG'.includes(cell)) return { ok: false, reason: `invalid cell '${cell}'` };
      if (cell === 'S') {
        if (start) return { ok: false, reason: 'duplicate start' };
        start = { x, y };
      }
      if (cell === 'G') {
        if (goal) return { ok: false, reason: 'duplicate goal' };
        goal = { x, y };
      }
    }
  }
  if (!start) return { ok: false, reason: 'missing start' };
  if (!goal) return { ok: false, reason: 'missing goal' };
  return { ok: true, width, height: grid.length, start, goal };
}

function solveMaze(grid) {
  const parsed = parseMaze(grid);
  if (!parsed.ok) return { ok: false, kind: 'invalid', reason: parsed.reason };

  const dirs = [
    { dx: 0, dy: -1, move: 'U' },
    { dx: 1, dy: 0, move: 'R' },
    { dx: 0, dy: 1, move: 'D' },
    { dx: -1, dy: 0, move: 'L' },
  ];
  const key = (p) => `${p.x},${p.y}`;
  const queue = [{ point: parsed.start, path: [parsed.start], moves: '' }];
  const seen = new Set([key(parsed.start)]);

  while (queue.length > 0) {
    const current = queue.shift();
    if (current.point.x === parsed.goal.x && current.point.y === parsed.goal.y) {
      return {
        ok: true,
        kind: 'solved',
        path: current.path,
        moves: current.moves,
        distance: current.path.length - 1,
      };
    }
    for (const dir of dirs) {
      const next = { x: current.point.x + dir.dx, y: current.point.y + dir.dy };
      if (next.x < 0 || next.y < 0 || next.x >= parsed.width || next.y >= parsed.height) continue;
      if (grid[next.y][next.x] === '#') continue;
      const nextKey = key(next);
      if (seen.has(nextKey)) continue;
      seen.add(nextKey);
      queue.push({
        point: next,
        path: [...current.path, next],
        moves: `${current.moves}${dir.move}`,
      });
    }
  }

  return { ok: false, kind: 'unsolvable', reason: 'goal is unreachable' };
}

function validateSolvedPath(grid, solution) {
  const parsed = parseMaze(grid);
  if (!parsed.ok) return { ok: false, reason: parsed.reason };
  if (!solution.ok) return { ok: false, reason: solution.reason || 'solver returned no path' };
  if (solution.path.length !== solution.moves.length + 1) {
    return { ok: false, reason: 'path length and moves length disagree' };
  }
  const first = solution.path[0];
  const last = solution.path[solution.path.length - 1];
  if (first.x !== parsed.start.x || first.y !== parsed.start.y) {
    return { ok: false, reason: 'path does not start at S' };
  }
  if (last.x !== parsed.goal.x || last.y !== parsed.goal.y) {
    return { ok: false, reason: 'path does not end at G' };
  }
  for (let index = 1; index < solution.path.length; index += 1) {
    const prev = solution.path[index - 1];
    const next = solution.path[index];
    const manhattan = Math.abs(prev.x - next.x) + Math.abs(prev.y - next.y);
    if (manhattan !== 1) return { ok: false, reason: `non-adjacent step at index ${index}` };
    if (grid[next.y][next.x] === '#')
      return { ok: false, reason: `wall collision at index ${index}` };
  }
  const shortest = solveMaze(grid);
  if (!shortest.ok || shortest.distance !== solution.distance) {
    return { ok: false, reason: 'path is not shortest according to verifier BFS' };
  }
  return { ok: true };
}

function runCase(testCase, stack) {
  const started = performance.now();
  const solution = solveMaze(testCase.grid);
  let contract;
  if (testCase.expected === 'solvable') {
    contract = validateSolvedPath(testCase.grid, solution);
  } else if (testCase.expected === 'unsolvable') {
    contract = {
      ok: !solution.ok && solution.kind === 'unsolvable',
      reason:
        solution.kind === 'unsolvable' ? undefined : `expected unsolvable, got ${solution.kind}`,
    };
  } else {
    contract = {
      ok: !solution.ok && solution.kind === 'invalid',
      reason: solution.kind === 'invalid' ? undefined : `expected invalid, got ${solution.kind}`,
    };
  }
  const durationMs = performance.now() - started;
  const execution = {
    tool: 'roll-stack-maze-benchmark',
    exit_code: contract.ok ? 0 : 1,
    duration_ms: Number(durationMs.toFixed(3)),
    stdout: {
      case_id: testCase.id,
      expected: testCase.expected,
      solution,
      contract,
    },
    stderr_tail: contract.ok ? '' : contract.reason || 'contract failed',
  };
  return {
    case_id: testCase.id,
    expected: testCase.expected,
    passed: contract.ok,
    duration_ms: execution.duration_ms,
    roll_ids: stack.steps.map((step) => step.roll_id),
    execution: {
      ...execution,
      receipt_hash: sha256({
        grid: testCase.grid,
        roll_ids: stack.steps.map((step) => step.roll_id),
        execution,
      }),
    },
  };
}

function main() {
  const stack = buildScbeRollStack(TASK);
  const cases = CASES.map((testCase) => runCase(testCase, stack));
  const durations = cases.map((testCase) => testCase.duration_ms);
  const passed = cases.filter((testCase) => testCase.passed).length;
  const report = {
    schema_version: 'scbe.agent_bus.roll_stack_maze_benchmark.v1',
    generated_at: new Date().toISOString(),
    task: TASK,
    stack: {
      schema_version: stack.schema_version,
      mode: stack.mode,
      command_path: stack.command_path,
      step_count: stack.steps.length,
      roll_ids: stack.steps.map((step) => step.roll_id),
      requires_execution_receipt: stack.acceptance.requires_execution_receipt,
    },
    summary: {
      case_count: cases.length,
      passed,
      failed: cases.length - passed,
      p95_ms: Number(percentile(durations, 95).toFixed(3)),
    },
    cases,
    note: 'This benchmark validates roll-stack execution evidence: collect contract, bounded local execution, output verification, and receipt. It does not claim general AI pathfinding.',
  };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  process.exitCode = report.summary.failed === 0 ? 0 : 1;
}

main();
