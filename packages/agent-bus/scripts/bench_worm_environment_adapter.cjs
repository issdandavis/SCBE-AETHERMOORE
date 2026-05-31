#!/usr/bin/env node

const crypto = require('node:crypto');
const { performance } = require('node:perf_hooks');
const path = require('node:path');

const pkgRoot = path.resolve(__dirname, '..');
const { buildScbeRollStack } = require(path.join(pkgRoot, 'dist', 'index.js'));

const TASK = 'worm environmental adapter pathfinding benchmark with depth-of-penetration scoring';

const DIRS = [
  { name: 'U', dx: 0, dy: -1 },
  { name: 'R', dx: 1, dy: 0 },
  { name: 'D', dx: 0, dy: 1 },
  { name: 'L', dx: -1, dy: 0 },
];

const CASES = [
  {
    id: 'u-trap-frontier',
    grid: ['S....#....', '####.#.###', '.....#...G', '.#######.#', '..........', '#########.'],
  },
  {
    id: 'edge-channel',
    grid: [
      'S########.',
      '.........#',
      '.#######.#',
      '.#.....#.#',
      '.#.###.#.#',
      '.#...#...G',
      '.#########',
      '..........',
    ],
  },
  {
    id: 'frontier-choice',
    grid: [
      'S...#.....',
      '###.#.###.',
      '....#...#.',
      '.######.#.',
      '.#......#G',
      '.#.######.',
      '..........',
    ],
  },
  {
    id: 'sealed-depth',
    grid: ['S....', '####.', 'G####', '.....'],
  },
];

function sha256(value) {
  return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function pointKey(point) {
  return `${point.x},${point.y}`;
}

function parseMaze(grid) {
  const height = grid.length;
  const width = grid[0]?.length || 0;
  let start = null;
  let goal = null;
  if (height === 0 || width === 0) return { ok: false, reason: 'empty grid' };
  for (let y = 0; y < height; y += 1) {
    if (grid[y].length !== width) return { ok: false, reason: 'non-rectangular grid' };
    for (let x = 0; x < width; x += 1) {
      const cell = grid[y][x];
      if (!'.#SG'.includes(cell)) return { ok: false, reason: `invalid cell ${cell}` };
      if (cell === 'S') start = { x, y };
      if (cell === 'G') goal = { x, y };
    }
  }
  if (!start || !goal) return { ok: false, reason: 'missing start or goal' };
  return { ok: true, width, height, start, goal };
}

function inBounds(parsed, point) {
  return point.x >= 0 && point.y >= 0 && point.x < parsed.width && point.y < parsed.height;
}

function cellAt(grid, point) {
  return grid[point.y]?.[point.x];
}

function manhattan(a, b) {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

function oracleBfs(grid) {
  const parsed = parseMaze(grid);
  if (!parsed.ok) return { ok: false, kind: 'invalid', reason: parsed.reason };
  const queue = [{ point: parsed.start, path: [parsed.start], moves: '' }];
  const seen = new Set([pointKey(parsed.start)]);
  while (queue.length > 0) {
    const current = queue.shift();
    if (current.point.x === parsed.goal.x && current.point.y === parsed.goal.y) {
      return {
        ok: true,
        kind: 'solved',
        distance: current.path.length - 1,
        path: current.path,
        moves: current.moves,
        reachable_count: seen.size,
      };
    }
    for (const dir of DIRS) {
      const next = { x: current.point.x + dir.dx, y: current.point.y + dir.dy };
      if (!inBounds(parsed, next)) continue;
      if (cellAt(grid, next) === '#') continue;
      const key = pointKey(next);
      if (seen.has(key)) continue;
      seen.add(key);
      queue.push({
        point: next,
        path: [...current.path, next],
        moves: `${current.moves}${dir.name}`,
      });
    }
  }
  return {
    ok: false,
    kind: 'unsolvable',
    reason: 'goal unreachable',
    reachable_count: seen.size,
  };
}

class EnvironmentalAdapter {
  constructor(grid) {
    this.grid = grid;
    this.parsed = parseMaze(grid);
    if (!this.parsed.ok) throw new Error(this.parsed.reason);
    this.position = { ...this.parsed.start };
    this.discovered = new Map();
    this.visitCounts = new Map();
    this.observe(this.position);
    this.visitCounts.set(pointKey(this.position), 1);
  }

  observe(center) {
    for (let dy = -1; dy <= 1; dy += 1) {
      for (let dx = -1; dx <= 1; dx += 1) {
        const point = { x: center.x + dx, y: center.y + dy };
        if (!inBounds(this.parsed, point)) continue;
        this.discovered.set(pointKey(point), cellAt(this.grid, point));
      }
    }
  }

  sense() {
    this.observe(this.position);
    const currentDistance = manhattan(this.position, this.parsed.goal);
    const neighbors = DIRS.map((dir) => {
      const point = { x: this.position.x + dir.dx, y: this.position.y + dir.dy };
      const key = pointKey(point);
      const known = this.discovered.has(key);
      const cell = inBounds(this.parsed, point) ? cellAt(this.grid, point) : '#';
      const legal = inBounds(this.parsed, point) && cell !== '#';
      const adjacentUnknown = DIRS.some((look) => {
        const near = { x: point.x + look.dx, y: point.y + look.dy };
        return inBounds(this.parsed, near) && !this.discovered.has(pointKey(near));
      });
      return {
        dir,
        point,
        key,
        known,
        cell,
        legal,
        adjacentUnknown,
        visitCount: this.visitCounts.get(key) || 0,
        goalDistance: manhattan(point, this.parsed.goal),
        edgeChannel:
          point.x === 0 ||
          point.y === 0 ||
          point.x === this.parsed.width - 1 ||
          point.y === this.parsed.height - 1,
      };
    });
    return {
      position: { ...this.position },
      goal: { ...this.parsed.goal },
      currentDistance,
      neighbors,
      discovered_count: this.discovered.size,
    };
  }

  move(neighbor) {
    if (!neighbor.legal) return false;
    this.position = { ...neighbor.point };
    const key = pointKey(this.position);
    this.visitCounts.set(key, (this.visitCounts.get(key) || 0) + 1);
    this.observe(this.position);
    return true;
  }
}

function chooseWormMove(adapter, previousDirection) {
  const sense = adapter.sense();
  const candidates = sense.neighbors.filter((neighbor) => neighbor.legal);
  if (candidates.length === 0) return null;
  let best = null;
  for (const candidate of candidates) {
    const chemoGain = sense.currentDistance - candidate.goalDistance;
    const frontierBonus = candidate.adjacentUnknown ? 1.25 : 0;
    const edgeBonus = candidate.edgeChannel ? 0.4 : 0;
    const revisitPenalty = candidate.visitCount * 1.9;
    const turnPenalty = previousDirection && previousDirection !== candidate.dir.name ? 0.15 : 0;
    const wallPressure = sense.neighbors.filter((neighbor) => !neighbor.legal).length * 0.08;
    const score =
      chemoGain * 1.4 + frontierBonus + edgeBonus - revisitPenalty - turnPenalty + wallPressure;
    const ranked = {
      candidate,
      score,
      components: {
        chemoGain,
        frontierBonus,
        edgeBonus,
        revisitPenalty,
        turnPenalty,
        wallPressure,
      },
    };
    if (
      !best ||
      ranked.score > best.score ||
      (ranked.score === best.score && ranked.candidate.dir.name < best.candidate.dir.name)
    ) {
      best = ranked;
    }
  }
  return best;
}

function chooseGreedyMove(adapter) {
  const sense = adapter.sense();
  const candidates = sense.neighbors.filter((neighbor) => neighbor.legal);
  if (candidates.length === 0) return null;
  return candidates
    .map((candidate) => ({
      candidate,
      score: -candidate.goalDistance - candidate.visitCount * 3,
      components: { goalDistance: candidate.goalDistance, visitCount: candidate.visitCount },
    }))
    .sort(
      (a, b) => b.score - a.score || a.candidate.dir.name.localeCompare(b.candidate.dir.name)
    )[0];
}

function runPolicy(grid, policyName, chooseMove, maxSteps) {
  const adapter = new EnvironmentalAdapter(grid);
  const oracle = oracleBfs(grid);
  const reachableCount = oracle.reachable_count || 1;
  const trace = [];
  let previousDirection = null;
  let closestDistance = manhattan(adapter.position, adapter.parsed.goal);
  let solved = false;
  for (let step = 0; step < maxSteps; step += 1) {
    if (cellAt(grid, adapter.position) === 'G') {
      solved = true;
      break;
    }
    const picked = chooseMove(adapter, previousDirection);
    if (!picked) break;
    adapter.move(picked.candidate);
    previousDirection = picked.candidate.dir.name;
    closestDistance = Math.min(closestDistance, manhattan(adapter.position, adapter.parsed.goal));
    trace.push({
      step,
      move: previousDirection,
      position: { ...adapter.position },
      score: Number(picked.score.toFixed(3)),
      components: picked.components,
    });
    if (cellAt(grid, adapter.position) === 'G') {
      solved = true;
      break;
    }
  }
  const visits = Array.from(adapter.visitCounts.values());
  const revisits = visits.reduce((total, count) => total + Math.max(0, count - 1), 0);
  const uniqueVisited = adapter.visitCounts.size;
  const discoveredFree = Array.from(adapter.discovered.entries()).filter(
    ([, cell]) => cell !== '#'
  ).length;
  return {
    policy: policyName,
    solved,
    steps: trace.length,
    closest_distance: closestDistance,
    penetration_ratio: Number(Math.min(1, uniqueVisited / reachableCount).toFixed(4)),
    discovered_free_ratio: Number(Math.min(1, discoveredFree / reachableCount).toFixed(4)),
    loop_rate: trace.length === 0 ? 0 : Number((revisits / trace.length).toFixed(4)),
    trace_tail: trace.slice(-12),
  };
}

function runCase(testCase, stack) {
  const started = performance.now();
  const parsed = parseMaze(testCase.grid);
  if (!parsed.ok) {
    return {
      case_id: testCase.id,
      passed: false,
      reason: parsed.reason,
    };
  }
  const oracle = oracleBfs(testCase.grid);
  const maxSteps = parsed.width * parsed.height * 4;
  const worm = runPolicy(testCase.grid, 'worm-environment-adapter', chooseWormMove, maxSteps);
  const greedy = runPolicy(testCase.grid, 'greedy-goal-distance', chooseGreedyMove, maxSteps);
  const durationMs = performance.now() - started;
  const penetrationDelta = Number((worm.penetration_ratio - greedy.penetration_ratio).toFixed(4));
  const wormAdvantage =
    worm.discovered_free_ratio >= greedy.discovered_free_ratio &&
    worm.penetration_ratio >= greedy.penetration_ratio &&
    worm.loop_rate <= 0.75;
  const evidenceComplete =
    worm.trace_tail.length > 0 &&
    greedy.trace_tail.length > 0 &&
    Number.isFinite(worm.penetration_ratio) &&
    Number.isFinite(greedy.penetration_ratio);
  const execution = {
    tool: 'worm-environment-adapter-benchmark',
    exit_code: evidenceComplete ? 0 : 1,
    duration_ms: Number(durationMs.toFixed(3)),
    stdout: {
      case_id: testCase.id,
      oracle,
      worm,
      greedy,
      penetration_delta_vs_greedy: penetrationDelta,
      benchmark_contract: {
        evidence_ok: evidenceComplete,
        worm_advantage: wormAdvantage,
        acceptance:
          'record worm and greedy traces, receipts, penetration ratios, loop rates, and solved state',
      },
    },
    stderr_tail: evidenceComplete ? '' : 'missing worm/greedy evidence',
  };
  return {
    case_id: testCase.id,
    evidence_ok: evidenceComplete,
    worm_advantage: wormAdvantage,
    duration_ms: execution.duration_ms,
    oracle_kind: oracle.kind,
    solved_by_worm: worm.solved,
    solved_by_greedy: greedy.solved,
    penetration_delta_vs_greedy: penetrationDelta,
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

function percentile(values, pct) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.ceil((pct / 100) * sorted.length) - 1);
  return sorted[index];
}

function main() {
  const stack = buildScbeRollStack(TASK);
  const cases = CASES.map((testCase) => runCase(testCase, stack));
  const evidencePassed = cases.filter((testCase) => testCase.evidence_ok).length;
  const report = {
    schema_version: 'scbe.agent_bus.worm_environment_adapter_benchmark.v1',
    generated_at: new Date().toISOString(),
    task: TASK,
    stack: {
      schema_version: stack.schema_version,
      roll_ids: stack.steps.map((step) => step.roll_id),
      requires_execution_receipt: stack.acceptance.requires_execution_receipt,
    },
    sensors: [
      'touch: adjacent blocked/free cells',
      'chemo: goal-distance gradient',
      'frontier: adjacent unknown-space pressure',
      'edge: boundary/channel relation',
      'memory: revisit suppression',
    ],
    summary: {
      case_count: cases.length,
      evidence_passed: evidencePassed,
      evidence_failed: cases.length - evidencePassed,
      worm_advantage_cases: cases.filter((testCase) => testCase.worm_advantage).length,
      worm_solved: cases.filter((testCase) => testCase.solved_by_worm).length,
      greedy_solved: cases.filter((testCase) => testCase.solved_by_greedy).length,
      avg_penetration_delta_vs_greedy: Number(
        (
          cases.reduce((total, testCase) => total + testCase.penetration_delta_vs_greedy, 0) /
          cases.length
        ).toFixed(4)
      ),
      p95_ms: Number(
        percentile(
          cases.map((testCase) => testCase.duration_ms),
          95
        ).toFixed(3)
      ),
    },
    cases,
    note: 'This benchmark is intentionally failure-tolerant. It measures depth of penetration under local sensing, not guaranteed shortest-path solving.',
  };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  process.exitCode = report.summary.evidence_failed === 0 ? 0 : 1;
}

main();
