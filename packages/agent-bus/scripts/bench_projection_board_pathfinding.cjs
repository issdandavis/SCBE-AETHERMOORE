#!/usr/bin/env node

const crypto = require('node:crypto');
const { performance } = require('node:perf_hooks');
const path = require('node:path');

const pkgRoot = path.resolve(__dirname, '..');
const { buildScbeRollStack } = require(path.join(pkgRoot, 'dist', 'index.js'));

const TASK = 'projection board fog-of-war pathfinding with hidden lattice state';

const DIRS = [
  { name: 'U', dx: 0, dy: -1 },
  { name: 'R', dx: 1, dy: 0 },
  { name: 'D', dx: 0, dy: 1 },
  { name: 'L', dx: -1, dy: 0 },
];

const CASES = [
  {
    id: 'permission-gate',
    objective: 'unlock_then_goal',
    grid: ['S..L..G', '.##.###', 'K......'],
    expectations: { must_collect_key: true, max_risk: 0 },
  },
  {
    id: 'safe-longer-than-shortest',
    objective: 'security_constrained',
    grid: ['S.RR.G', '.####.', '......'],
    expectations: { max_risk: 0 },
  },
  {
    id: 'importance-before-goal',
    objective: 'collect_importance_then_goal',
    grid: ['S....G', '.####.', '..I...'],
    expectations: { min_importance: 1 },
  },
  {
    id: 'frontier-reveal',
    objective: 'discover_goal_under_fog',
    grid: ['S..#...', '##.#.#.', '...#.#G', '.###.#.', '.......'],
    expectations: { min_frontier_reveals: 8 },
  },
];

function sha256(value) {
  return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function key(point) {
  return `${point.x},${point.y}`;
}

function parseGrid(grid) {
  const height = grid.length;
  const width = grid[0]?.length || 0;
  let start = null;
  let goal = null;
  if (!height || !width) return { ok: false, reason: 'empty grid' };
  for (let y = 0; y < height; y += 1) {
    if (grid[y].length !== width) return { ok: false, reason: 'non-rectangular grid' };
    for (let x = 0; x < width; x += 1) {
      const cell = grid[y][x];
      if (!'.#SGLKRI'.includes(cell)) return { ok: false, reason: `invalid cell ${cell}` };
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

function normalizeVector3(vector) {
  const norm = Math.hypot(vector[0], vector[1], vector[2]);
  if (norm === 0) return [0, 0, 0];
  return vector.map((value) => value / norm);
}

function dotVector3(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

class ProjectionBoard {
  constructor(grid) {
    this.grid = grid;
    this.parsed = parseGrid(grid);
    if (!this.parsed.ok) throw new Error(this.parsed.reason);
    this.position = { ...this.parsed.start };
    this.known = new Map();
    this.visits = new Map([[key(this.position), 1]]);
    this.state = {
      has_key: false,
      risk: 0,
      importance: 0,
      frontier_reveals: 0,
      blocked_attempts: 0,
      spin_coherence: 1,
      spin_disorder: 0,
    };
    this.spinSum = [0, 0, 0];
    this.spinSamples = 0;
    this.observe();
  }

  observe() {
    let newlyRevealed = 0;
    for (let dy = -1; dy <= 1; dy += 1) {
      for (let dx = -1; dx <= 1; dx += 1) {
        const point = { x: this.position.x + dx, y: this.position.y + dy };
        if (!inBounds(this.parsed, point)) continue;
        const pointKey = key(point);
        if (!this.known.has(pointKey)) newlyRevealed += 1;
        this.known.set(pointKey, cellAt(this.grid, point));
      }
    }
    this.state.frontier_reveals += newlyRevealed;
  }

  render() {
    const rows = [];
    for (let y = 0; y < this.parsed.height; y += 1) {
      let row = '';
      for (let x = 0; x < this.parsed.width; x += 1) {
        const point = { x, y };
        if (this.position.x === x && this.position.y === y) {
          row += '@';
        } else {
          row += this.known.get(key(point)) || '?';
        }
      }
      rows.push(row);
    }
    return rows;
  }

  legal(point) {
    if (!inBounds(this.parsed, point)) return false;
    const cell = cellAt(this.grid, point);
    if (cell === '#') return false;
    if (cell === 'L' && !this.state.has_key) return false;
    return true;
  }

  move(point) {
    if (!this.legal(point)) {
      this.state.blocked_attempts += 1;
      return false;
    }
    this.position = { ...point };
    const pointKey = key(point);
    this.visits.set(pointKey, (this.visits.get(pointKey) || 0) + 1);
    const cell = cellAt(this.grid, point);
    if (cell === 'K') this.state.has_key = true;
    if (cell === 'R') this.state.risk += 1;
    if (cell === 'I') this.state.importance += 1;
    this.observe();
    return true;
  }

  recordSpin(spinVector) {
    if (!Array.isArray(spinVector) || spinVector.length !== 3) return;
    this.spinSamples += 1;
    this.spinSum = this.spinSum.map((value, index) => value + spinVector[index]);
    const spinMagnitudeSum = this.spinSamples;
    const coherence =
      Math.hypot(this.spinSum[0], this.spinSum[1], this.spinSum[2]) / spinMagnitudeSum;
    this.state.spin_coherence = Number(coherence.toFixed(4));
    this.state.spin_disorder = Number((1 - coherence).toFixed(4));
  }
}

const CONVOLUTION_KERNEL = [
  [0.4, 0.7, 0.4],
  [0.7, 1.0, 0.7],
  [0.4, 0.7, 0.4],
];

function localConvolution(board, center, objective) {
  const fields = {
    unknown: 0,
    wall: 0,
    risk: 0,
    key: 0,
    locked: 0,
    importance: 0,
    goal: 0,
  };
  for (let dy = -1; dy <= 1; dy += 1) {
    for (let dx = -1; dx <= 1; dx += 1) {
      const point = { x: center.x + dx, y: center.y + dy };
      if (!inBounds(board.parsed, point)) continue;
      const weight = CONVOLUTION_KERNEL[dy + 1][dx + 1];
      const pointKey = key(point);
      const known = board.known.has(pointKey);
      const cell = cellAt(board.grid, point);
      if (!known) fields.unknown += weight;
      if (cell === '#') fields.wall += weight;
      if (cell === 'R') fields.risk += weight;
      if (cell === 'K' && !board.state.has_key) fields.key += weight;
      if (cell === 'L' && !board.state.has_key) fields.locked += weight;
      if (
        cell === 'I' &&
        objective === 'collect_importance_then_goal' &&
        board.state.importance < 1
      ) {
        fields.importance += weight;
      }
      if (cell === 'G') fields.goal += weight;
    }
  }
  return fields;
}

function scoreConvolution(fields, objective) {
  const securityRisk = objective === 'security_constrained' ? fields.risk * -5.5 : fields.risk * -2;
  return {
    value:
      fields.unknown * 0.75 +
      fields.key * 6 +
      fields.importance * 5 +
      fields.goal * 2.25 -
      fields.wall * 0.35 -
      fields.locked * 3,
    securityRisk,
  };
}

function projectBaseToMove(board, objective) {
  const currentDistance = manhattan(board.position, board.parsed.goal);
  const candidates = DIRS.map((dir) => {
    const point = { x: board.position.x + dir.dx, y: board.position.y + dir.dy };
    const cell = inBounds(board.parsed, point) ? cellAt(board.grid, point) : '#';
    const legal = board.legal(point);
    const unknownAround = DIRS.filter((look) => {
      const near = { x: point.x + look.dx, y: point.y + look.dy };
      return inBounds(board.parsed, near) && !board.known.has(key(near));
    }).length;
    const visitPenalty = (board.visits.get(key(point)) || 0) * 2.2;
    const goalGain = currentDistance - manhattan(point, board.parsed.goal);
    const riskPenalty = cell === 'R' ? (objective === 'security_constrained' ? 9 : 3) : 0;
    const keyPull = !board.state.has_key && cell === 'K' ? 10 : 0;
    const lockedPressure = cell === 'L' && !board.state.has_key ? -20 : 0;
    const importancePull = objective === 'collect_importance_then_goal' && cell === 'I' ? 8 : 0;
    const frontierPull = unknownAround * 0.65;
    const edgePull = point.x === 0 || point.y === 0 ? 0.2 : 0;
    const convolutionFields = localConvolution(board, point, objective);
    const convolution = scoreConvolution(convolutionFields, objective);
    const goalPull =
      objective === 'collect_importance_then_goal' && board.state.importance < 1
        ? goalGain * 0.35
        : goalGain * 1.4;
    const spinVector = normalizeVector3([
      goalPull + convolutionFields.goal,
      frontierPull + keyPull + importancePull + convolutionFields.unknown,
      -(riskPenalty + Math.max(0, -lockedPressure) + visitPenalty) - convolutionFields.risk,
    ]);
    const spinCoherencePenalty = board.state.spin_disorder * 1.2;
    const score =
      goalPull +
      frontierPull +
      edgePull +
      keyPull +
      importancePull +
      lockedPressure -
      riskPenalty -
      visitPenalty +
      convolution.value +
      convolution.securityRisk -
      spinCoherencePenalty;
    return {
      dir,
      point,
      cell,
      legal,
      score,
      fields: {
        goalPull,
        frontierPull,
        edgePull,
        keyPull,
        importancePull,
        lockedPressure,
        riskPenalty,
        visitPenalty,
        convolution: Number(convolution.value.toFixed(3)),
        convolutionSecurityRisk: Number(convolution.securityRisk.toFixed(3)),
        convolutionFields,
        spinVector: spinVector.map((value) => Number(value.toFixed(4))),
        spinCoherencePenalty: Number(spinCoherencePenalty.toFixed(3)),
      },
    };
  });
  return candidates
    .filter((candidate) => candidate.legal)
    .sort((a, b) => b.score - a.score || a.dir.name.localeCompare(b.dir.name))[0];
}

function greedyMove(board) {
  const currentDistance = manhattan(board.position, board.parsed.goal);
  return DIRS.map((dir) => {
    const point = { x: board.position.x + dir.dx, y: board.position.y + dir.dy };
    const legal = board.legal(point);
    const goalGain = currentDistance - manhattan(point, board.parsed.goal);
    const visitPenalty = (board.visits.get(key(point)) || 0) * 2.2;
    return {
      dir,
      point,
      legal,
      score: goalGain * 2 - visitPenalty,
      fields: { goalGain, visitPenalty },
    };
  })
    .filter((candidate) => candidate.legal)
    .sort((a, b) => b.score - a.score || a.dir.name.localeCompare(b.dir.name))[0];
}

function runPolicy(testCase, policy, chooser) {
  const board = new ProjectionBoard(testCase.grid);
  const maxSteps = board.parsed.width * board.parsed.height * 5;
  const trace = [];
  for (let step = 0; step < maxSteps; step += 1) {
    const atGoal = cellAt(testCase.grid, board.position) === 'G';
    const needsImportance =
      testCase.objective === 'collect_importance_then_goal' && board.state.importance < 1;
    if (atGoal && !needsImportance) break;
    const move = chooser(board, testCase.objective);
    if (!move) break;
    board.move(move.point);
    board.recordSpin(move.fields?.spinVector);
    trace.push({
      step,
      move: move.dir.name,
      tip: { ...board.position },
      score: Number(move.score.toFixed(3)),
      fields: move.fields,
      state: { ...board.state },
      board: board.render(),
    });
  }
  const solved =
    cellAt(testCase.grid, board.position) === 'G' &&
    (!testCase.expectations.must_collect_key || board.state.has_key) &&
    (!testCase.expectations.min_importance ||
      board.state.importance >= testCase.expectations.min_importance) &&
    (!Number.isFinite(testCase.expectations.max_risk) ||
      board.state.risk <= testCase.expectations.max_risk) &&
    (!testCase.expectations.min_frontier_reveals ||
      board.state.frontier_reveals >= testCase.expectations.min_frontier_reveals);
  return {
    policy,
    solved,
    final_tip: { ...board.position },
    state: { ...board.state },
    steps: trace.length,
    unique_positions: board.visits.size,
    closest_distance: manhattan(board.position, board.parsed.goal),
    trace_tail: trace.slice(-8),
  };
}

function runCase(testCase, stack) {
  const started = performance.now();
  const projection = runPolicy(testCase, 'projection-board-multilattice', projectBaseToMove);
  const greedy = runPolicy(testCase, 'goal-greedy-projection', greedyMove);
  const durationMs = performance.now() - started;
  const advantage =
    projection.solved && (!greedy.solved || projection.state.risk <= greedy.state.risk);
  const evidenceOk =
    projection.trace_tail.length > 0 &&
    greedy.trace_tail.length > 0 &&
    projection.trace_tail.every(
      (step) =>
        Array.isArray(step.board) &&
        step.fields?.convolutionFields &&
        Array.isArray(step.fields?.spinVector)
    );
  const execution = {
    tool: 'projection-board-pathfinding-benchmark',
    exit_code: evidenceOk ? 0 : 1,
    duration_ms: Number(durationMs.toFixed(3)),
    stdout: {
      case_id: testCase.id,
      objective: testCase.objective,
      projection,
      greedy,
      benchmark_contract: {
        evidence_ok: evidenceOk,
        projection_advantage: advantage,
        acceptance:
          'record visible board projection, hidden lattice fields, tip moves, risk, permissions, importance, and receipts',
      },
    },
    stderr_tail: evidenceOk ? '' : 'missing projection-board evidence',
  };
  return {
    case_id: testCase.id,
    objective: testCase.objective,
    evidence_ok: evidenceOk,
    projection_advantage: advantage,
    solved_by_projection: projection.solved,
    solved_by_greedy: greedy.solved,
    projection_risk: projection.state.risk,
    greedy_risk: greedy.state.risk,
    duration_ms: execution.duration_ms,
    roll_ids: stack.steps.map((step) => step.roll_id),
    execution: {
      ...execution,
      receipt_hash: sha256({
        grid: testCase.grid,
        objective: testCase.objective,
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
    schema_version: 'scbe.agent_bus.projection_board_pathfinding_benchmark.v1',
    generated_at: new Date().toISOString(),
    task: TASK,
    stack: {
      schema_version: stack.schema_version,
      roll_ids: stack.steps.map((step) => step.roll_id),
      requires_execution_receipt: stack.acceptance.requires_execution_receipt,
    },
    projection_model: {
      visible_tip: 'x,y minimap position',
      hidden_base: [
        'goal pressure',
        'unknown frontier',
        'security risk',
        'permission key state',
        'importance depth',
        'memory loop pressure',
        'spin-vector coherence/disorder',
        '3x3 kernel convolution over local lattice fields',
      ],
      kernel_convolution: {
        weights: CONVOLUTION_KERNEL,
        fields: ['unknown', 'wall', 'risk', 'key', 'locked', 'importance', 'goal'],
      },
      spin_voxel_shadow_channel: {
        vector: [
          'goal trajectory',
          'frontier/permission/importance pull',
          'risk/revisit/lock pressure',
        ],
        coherence: '|sum_i S_i| / n',
        disorder: '1 - coherence',
      },
      board_symbols: {
        '?': 'fog of war',
        '@': 'projected agent tip',
        '#': 'wall',
        L: 'locked gate',
        K: 'permission key',
        R: 'risk region',
        I: 'importance/depth checkpoint',
        G: 'goal',
      },
    },
    summary: {
      case_count: cases.length,
      evidence_passed: evidencePassed,
      evidence_failed: cases.length - evidencePassed,
      projection_solved: cases.filter((testCase) => testCase.solved_by_projection).length,
      greedy_solved: cases.filter((testCase) => testCase.solved_by_greedy).length,
      projection_advantage_cases: cases.filter((testCase) => testCase.projection_advantage).length,
      p95_ms: Number(
        percentile(
          cases.map((testCase) => testCase.duration_ms),
          95
        ).toFixed(3)
      ),
    },
    cases,
    note: 'This benchmark tests a fog-of-war projection board over hidden lattice state. It scores evidence and objective-aware movement, not shortest path alone.',
  };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  process.exitCode = report.summary.evidence_failed === 0 ? 0 : 1;
}

main();
