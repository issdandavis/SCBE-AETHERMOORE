/**
 * @file vector-field-nav.ts
 * @module agent-bus/vector-field-nav
 * @layer Cross-layer navigation
 * @component Multi-Lattice Vector Field Navigation
 *
 * Goal-Based Multi-Lattice Vector Field Pathfinding.
 *
 *   V_total(x) = w_goal*goal + w_obstacle*obstacle + w_frontier*frontier
 *              + w_security*security + w_importance*importance
 *              + w_memory*memory + w_edge*edge_channel
 *              + w_kernel*kernel_convolution
 *              + w_pressure*pressure_sense
 *
 * State  = position + known map + security score + depth tier + goal pressure.
 * Move   = local vector decision (no global plan).
 * Verify = oracle BFS (full map) + SHA-256 receipt chain + failure-depth scoring.
 *
 * Five head-to-head algorithms:
 *   multi-lattice  — 7-field combiner (the claim)
 *   astar-full     — follows oracle path (upper bound, partial-observation disabled)
 *   astar-limited  — A* on known map only, replanned each step (honest baseline)
 *   greedy         — pure goal attraction, no other fields
 *   random         — uniform random walk (lower bound)
 *
 * Ablation: each field disabled in turn to isolate contribution.
 *
 * Receipt chain: each move hashes (prev_hash | move_id | vector) with SHA-256.
 * The chain is verified at scoring time; receipt_completeness = fraction valid.
 *
 * Security tiers map to SCBE L13 governance: ALLOW/QUARANTINE/ESCALATE/DENY.
 * Importance gradient uses phi-weighting from the Langues Metric.
 *
 * Research basis:
 *   Khatib 1986 IJRR — Artificial Potential Fields (goal attract + obstacle repel)
 *   Rimon & Koditschek — Navigation Functions (local-minima avoidance)
 *   NASA NTRS 19880019994 — APF for space robotics
 *   Flow Fields PMC12627758 — precomputed per-cell vectors
 *   Multi-Objective ScienceDirect S0004370224001966 — vector cost combination
 */

import crypto from 'node:crypto';

// ─── PRNG (Mulberry32, deterministic) ─────────────────────────────────────────

function mulberry32(seed: number): () => number {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ─── Types ───────────────────────────────────────────────────────────────────

export type CellType = 'empty' | 'wall' | 'goal' | 'start';
export type SecurityTier = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
export type NavAlgorithm =
  | 'multi-lattice'
  | 'ensemble-beam'
  | 'depth-first'
  | 'astar-full'
  | 'astar-limited'
  | 'greedy'
  | 'random';
export type AblationTag =
  | 'no-goal'
  | 'no-obstacle'
  | 'no-frontier'
  | 'no-security'
  | 'no-importance'
  | 'no-memory'
  | 'no-edge'
  | 'no-kernel'
  | 'no-pressure';
export type RunLabel = NavAlgorithm | `multi-lattice+${AblationTag}`;

export interface MazeCell {
  type: CellType;
  security_tier: SecurityTier;
  importance: number;
}

export interface MazeConfig {
  id: string;
  width: number;
  height: number;
  seed: number;
  sensor_radius: number;
  max_steps: number;
}

export interface MazeGrid {
  id: string;
  width: number;
  height: number;
  cells: MazeCell[][];
  start: [number, number];
  goal: [number, number];
}

export interface LatticeWeights {
  goal: number;
  obstacle: number;
  frontier: number;
  security: number;
  importance: number;
  memory: number;
  edge_channel: number;
  kernel_convolution: number;
  pressure_sense: number;
}

export interface VectorBreakdown {
  goal: number;
  obstacle: number;
  frontier: number;
  security: number;
  importance: number;
  memory: number;
  edge_channel: number;
  kernel_convolution: number;
  pressure_sense: number;
  total: number;
}

export interface MoveReceipt {
  move_id: number;
  from: [number, number];
  to: [number, number];
  security_tier: SecurityTier;
  vector: VectorBreakdown;
  depth_at_move: number;
  step_ts: number;
  receipt_hash: string;
  prev_hash: string;
}

export interface AgentState {
  pos: [number, number];
  known: Set<string>;
  visit_counts: Map<string, number>;
  security_score: number;
  max_depth_reached: number;
  receipts: MoveReceipt[];
  steps: number;
  heat_map: Map<string, number>;
  pressure_map: Map<string, number>;
}

export interface BenchmarkScore {
  schema_version: 'scbe.agent_bus.vector_field_nav.bench.v1';
  maze_id: string;
  alg: string;
  sensor_radius: number;
  max_steps: number;
  steps_taken: number;
  solved: boolean;
  penetration_depth: number;
  closest_distance: number;
  frontier_coverage: number;
  loop_rate: number;
  security_violations: number;
  receipt_completeness: number;
  stuck_loops: number;
  oracle_path_length: number;
  efficiency: number;
  heat_peak: number;
  heat_coverage: number;
  avg_pressure: number;
  total_ms: number;
}

export interface AlgorithmSummary {
  solve_rate: number;
  avg_efficiency: number;
  avg_frontier_coverage: number;
  avg_loop_rate: number;
  avg_security_violations: number;
  avg_stuck_loops: number;
  avg_receipt_completeness: number;
  avg_heat_peak: number;
  avg_pressure: number;
}

export interface AblationEntry {
  solve_rate_delta: number;
  efficiency_delta: number;
  loop_rate_delta: number;
  frontier_coverage_delta: number;
  stuck_loops_delta: number;
}

export interface NavBenchResult {
  schema_version: 'scbe.agent_bus.vector_field_nav.v1';
  runs: BenchmarkScore[];
  comparison: Record<string, AlgorithmSummary>;
  ablation_table: Record<string, AblationEntry>;
  summary: {
    total_mazes: number;
    total_runs: number;
    multi_lattice_solve_rate: number;
    ensemble_beam_solve_rate: number;
    astar_full_solve_rate: number;
    random_solve_rate: number;
    multi_lattice_avg_efficiency: number;
    ensemble_beam_avg_efficiency: number;
    random_solve_trials: number;
    random_solve_successes: number;
    total_ms: number;
  };
}

export interface FluidHeatCell {
  x: number;
  y: number;
  visits: number;
  pressure: number;
}

export interface RandomSolveSweepResult {
  schema_version: 'scbe.agent_bus.vector_field_nav.random_solve_sweep.v1';
  runs: BenchmarkScore[];
  summary: {
    trials: number;
    algorithm: NavAlgorithm;
    solve_rate: number;
    solve_successes: number;
    random_solve_rate: number;
    random_solve_successes: number;
    avg_heat_peak: number;
    avg_pressure: number;
    total_ms: number;
  };
}

// ─── Constants ────────────────────────────────────────────────────────────────

export const DEFAULT_WEIGHTS: LatticeWeights = {
  goal: 2.0,
  obstacle: 1.5,
  frontier: 1.0,
  security: 1.8,
  importance: 0.8,
  memory: 1.2,
  edge_channel: 0.5,
  kernel_convolution: 0.65,
  pressure_sense: 0.9,
};

const SECURITY_COST: Record<SecurityTier, number> = {
  ALLOW: 0,
  QUARANTINE: 1,
  ESCALATE: 2,
  DENY: 10,
};

const PHI = 1.6180339887;

export const VECTOR_KERNEL_3X3 = [
  [0.4, 0.7, 0.4],
  [0.7, 1.0, 0.7],
  [0.4, 0.7, 0.4],
] as const;

export const BENCHMARK_MAZES: MazeConfig[] = [
  { id: 'tiny', width: 9, height: 9, seed: 42, sensor_radius: 3, max_steps: 100 },
  { id: 'standard', width: 15, height: 15, seed: 137, sensor_radius: 3, max_steps: 300 },
  { id: 'gauntlet', width: 21, height: 21, seed: 256, sensor_radius: 2, max_steps: 600 },
  { id: 'deep-space', width: 25, height: 25, seed: 1618, sensor_radius: 2, max_steps: 900 },
];

// ─── Maze generator (recursive backtracking, seeded PRNG) ─────────────────────

export function generateMaze(cfg: MazeConfig): MazeGrid {
  const { width: W, height: H, seed } = cfg;
  const rng = mulberry32(seed);

  const cells: MazeCell[][] = Array.from({ length: H }, () =>
    Array.from({ length: W }, () => ({
      type: 'wall' as CellType,
      security_tier: 'ALLOW' as SecurityTier,
      importance: 0,
    }))
  );

  // Maze cell (i, j) sits at grid position (2i+1, 2j+1).
  const mw = Math.floor((W - 1) / 2);
  const mh = Math.floor((H - 1) / 2);
  const visited = new Set<string>();

  function carve(i: number, j: number): void {
    visited.add(`${i},${j}`);
    cells[2 * j + 1]![2 * i + 1]!.type = 'empty';

    const dirs: [number, number][] = [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ];
    for (let k = dirs.length - 1; k > 0; k--) {
      const r = Math.floor(rng() * (k + 1));
      const tmp = dirs[k]!;
      dirs[k] = dirs[r]!;
      dirs[r] = tmp;
    }

    for (const [di, dj] of dirs) {
      const ni = i + di;
      const nj = j + dj;
      if (ni < 0 || ni >= mw || nj < 0 || nj >= mh) continue;
      if (visited.has(`${ni},${nj}`)) continue;
      cells[2 * j + 1 + dj]![2 * i + 1 + di]!.type = 'empty';
      carve(ni, nj);
    }
  }

  carve(0, 0);

  const startX = 1;
  const startY = 1;
  const goalX = W - 2;
  const goalY = H - 2;
  cells[startY]![startX]!.type = 'start';
  cells[goalY]![goalX]!.type = 'goal';

  // Importance: phi-weighted inverse distance to goal (matches L12 harmonic formula).
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const c = cells[y]![x]!;
      if (c.type !== 'wall') {
        const d = Math.abs(x - goalX) + Math.abs(y - goalY);
        c.importance = 1 / (1 + PHI * d);
      }
    }
  }

  // Security tiers on some passable cells (DENY not used — would disconnect maze).
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const c = cells[y]![x]!;
      if (c.type === 'empty') {
        const r = rng();
        if (r < 0.06) c.security_tier = 'QUARANTINE';
        else if (r < 0.08) c.security_tier = 'ESCALATE';
      }
    }
  }

  return {
    id: `${cfg.id}-${seed}`,
    width: W,
    height: H,
    cells,
    start: [startX, startY],
    goal: [goalX, goalY],
  };
}

// ─── Grid helpers ─────────────────────────────────────────────────────────────

function posKey(x: number, y: number): string {
  return `${x},${y}`;
}

function manhattan(a: [number, number], b: [number, number]): number {
  return Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]);
}

function euclidean(a: [number, number], b: [number, number]): number {
  return Math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2);
}

function getCell(maze: MazeGrid, x: number, y: number): MazeCell | undefined {
  return maze.cells[y]?.[x];
}

function passable(maze: MazeGrid, x: number, y: number): boolean {
  const c = getCell(maze, x, y);
  // DENY cells treated as walls (security lattice assigns extreme penalty).
  return c !== undefined && c.type !== 'wall' && c.security_tier !== 'DENY';
}

function neighbors4(maze: MazeGrid, x: number, y: number): [number, number][] {
  return (
    [
      [x + 1, y],
      [x - 1, y],
      [x, y + 1],
      [x, y - 1],
    ] as [number, number][]
  ).filter(([nx, ny]) => passable(maze, nx, ny));
}

function reveal(agent: AgentState, maze: MazeGrid, sensor_radius: number): void {
  const [x, y] = agent.pos;
  for (let dy = -sensor_radius; dy <= sensor_radius; dy++) {
    for (let dx = -sensor_radius; dx <= sensor_radius; dx++) {
      if (dx * dx + dy * dy <= sensor_radius * sensor_radius) {
        const nx = x + dx;
        const ny = y + dy;
        if (nx >= 0 && nx < maze.width && ny >= 0 && ny < maze.height) {
          agent.known.add(posKey(nx, ny));
        }
      }
    }
  }
}

function sha256chain(prevHash: string, data: object): string {
  return crypto
    .createHash('sha256')
    .update(prevHash)
    .update('|')
    .update(JSON.stringify(data))
    .digest('hex')
    .slice(0, 32);
}

// ─── Oracle BFS (full map, upper-bound path) ──────────────────────────────────

export function oracleBFS(maze: MazeGrid): [number, number][] | null {
  const [sx, sy] = maze.start;
  const [gx, gy] = maze.goal;
  const queue: [number, number][] = [[sx, sy]];
  const prev = new Map<string, string | null>();
  prev.set(posKey(sx, sy), null);

  while (queue.length > 0) {
    const [x, y] = queue.shift()!;
    if (x === gx && y === gy) {
      const path: [number, number][] = [];
      let k: string | null = posKey(x, y);
      while (k !== null) {
        const [px, py] = k.split(',').map(Number) as [number, number];
        path.unshift([px, py]);
        k = prev.get(k) ?? null;
      }
      return path;
    }
    for (const [nx, ny] of neighbors4(maze, x, y)) {
      const nk = posKey(nx, ny);
      if (!prev.has(nk)) {
        prev.set(nk, posKey(x, y));
        queue.push([nx, ny]);
      }
    }
  }
  return null;
}

function buildOracleDepthMap(oracle_path: [number, number][]): Map<string, number> {
  const m = new Map<string, number>();
  for (let i = 0; i < oracle_path.length; i++) {
    m.set(posKey(oracle_path[i]![0], oracle_path[i]![1]), i);
  }
  return m;
}

// ─── Seven lattice field functions ────────────────────────────────────────────

function goalField(pos: [number, number], maze: MazeGrid): number {
  return -manhattan(pos, maze.goal);
}

function obstacleField(
  pos: [number, number],
  maze: MazeGrid,
  known: Set<string>,
  sensor_r: number
): number {
  let repulsion = 0;
  const [x, y] = pos;
  for (let dy = -sensor_r; dy <= sensor_r; dy++) {
    for (let dx = -sensor_r; dx <= sensor_r; dx++) {
      const nx = x + dx;
      const ny = y + dy;
      if (!known.has(posKey(nx, ny))) continue;
      const c = getCell(maze, nx, ny);
      if (!c || c.type === 'wall') {
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d > 0) repulsion -= 1 / (d * d);
      }
    }
  }
  return repulsion;
}

function frontierField(pos: [number, number], maze: MazeGrid, known: Set<string>): number {
  let count = 0;
  const [x, y] = pos;
  for (const [nx, ny] of [
    [x + 1, y],
    [x - 1, y],
    [x, y + 1],
    [x, y - 1],
  ] as [number, number][]) {
    if (nx >= 0 && nx < maze.width && ny >= 0 && ny < maze.height) {
      if (!known.has(posKey(nx, ny))) count++;
    }
  }
  return count;
}

function securityField(pos: [number, number], maze: MazeGrid): number {
  const c = getCell(maze, pos[0], pos[1]);
  return c ? -SECURITY_COST[c.security_tier] : 0;
}

function importanceField(pos: [number, number], maze: MazeGrid): number {
  const c = getCell(maze, pos[0], pos[1]);
  return c ? c.importance : 0;
}

function memoryField(pos: [number, number], visit_counts: Map<string, number>): number {
  return -(visit_counts.get(posKey(pos[0], pos[1])) ?? 0);
}

function edgeChannelField(pos: [number, number], maze: MazeGrid): number {
  return neighbors4(maze, pos[0], pos[1]).length;
}

function pressureSenseField(
  pos: [number, number],
  maze: MazeGrid,
  agent: AgentState,
  sensor_r: number
): number {
  const [x, y] = pos;
  let pressure = 0;
  for (let dy = -sensor_r; dy <= sensor_r; dy++) {
    for (let dx = -sensor_r; dx <= sensor_r; dx++) {
      const nx = x + dx;
      const ny = y + dy;
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d === 0 || d > sensor_r) continue;
      const falloff = 1 / (1 + d);
      const cell = getCell(maze, nx, ny);
      const known = agent.known.has(posKey(nx, ny));
      if (!cell || cell.type === 'wall') pressure += 1.1 * falloff;
      if (!known) pressure += 0.25 * falloff;
      if (cell) pressure += SECURITY_COST[cell.security_tier] * 0.4 * falloff;
      pressure += (agent.visit_counts.get(posKey(nx, ny)) ?? 0) * 0.18 * falloff;
    }
  }
  return -pressure;
}

function kernelConvolutionField(pos: [number, number], maze: MazeGrid, agent: AgentState): number {
  const [x, y] = pos;
  let weighted = 0;
  let weightSum = 0;
  for (let dy = -1; dy <= 1; dy++) {
    for (let dx = -1; dx <= 1; dx++) {
      const nx = x + dx;
      const ny = y + dy;
      const weight = VECTOR_KERNEL_3X3[dy + 1]![dx + 1]!;
      weightSum += weight;
      const cell = getCell(maze, nx, ny);
      const known = agent.known.has(posKey(nx, ny));
      if (!cell || cell.type === 'wall') {
        weighted -= 1.1 * weight;
        continue;
      }
      if (!known) weighted += 0.35 * weight;
      if (cell.type === 'goal') weighted += 2.4 * weight;
      weighted += cell.importance * weight;
      weighted -= SECURITY_COST[cell.security_tier] * 0.55 * weight;
      weighted -= (agent.visit_counts.get(posKey(nx, ny)) ?? 0) * 0.18 * weight;
    }
  }
  return weightSum === 0 ? 0 : weighted / weightSum;
}

export function computeVTotal(
  pos: [number, number],
  maze: MazeGrid,
  agent: AgentState,
  weights: LatticeWeights,
  sensor_r: number
): VectorBreakdown {
  const g = goalField(pos, maze);
  const o = obstacleField(pos, maze, agent.known, sensor_r);
  const f = frontierField(pos, maze, agent.known);
  const s = securityField(pos, maze);
  const imp = importanceField(pos, maze);
  const m = memoryField(pos, agent.visit_counts);
  const e = edgeChannelField(pos, maze);
  const k = kernelConvolutionField(pos, maze, agent);
  const p = pressureSenseField(pos, maze, agent, sensor_r);

  const total =
    weights.goal * g +
    weights.obstacle * o +
    weights.frontier * f +
    weights.security * s +
    weights.importance * imp +
    weights.memory * m +
    weights.edge_channel * e +
    weights.kernel_convolution * k +
    weights.pressure_sense * p;

  return {
    goal: g,
    obstacle: o,
    frontier: f,
    security: s,
    importance: imp,
    memory: m,
    edge_channel: e,
    kernel_convolution: k,
    pressure_sense: p,
    total,
  };
}

// ─── Movement algorithms ──────────────────────────────────────────────────────

function pickMoveMultiLattice(
  agent: AgentState,
  maze: MazeGrid,
  weights: LatticeWeights,
  sensor_r: number
): [number, number] | null {
  const nbrs = neighbors4(maze, agent.pos[0], agent.pos[1]);
  if (nbrs.length === 0) return null;

  let best = nbrs[0]!;
  let bestV = -Infinity;

  for (const [nx, ny] of nbrs) {
    const bd = computeVTotal([nx, ny], maze, agent, weights, sensor_r);
    if (bd.total > bestV) {
      bestV = bd.total;
      best = [nx, ny];
    }
  }
  return best;
}

function samePos(a: [number, number] | null, b: [number, number]): boolean {
  return a !== null && a[0] === b[0] && a[1] === b[1];
}

function goalBeamField(candidate: [number, number], agent: AgentState, maze: MazeGrid): number {
  const [ax, ay] = agent.pos;
  const [gx, gy] = maze.goal;
  const toGoal: [number, number] = [gx - ax, gy - ay];
  const toCandidate: [number, number] = [candidate[0] - ax, candidate[1] - ay];
  const goalNorm = Math.hypot(toGoal[0], toGoal[1]);
  const candidateNorm = Math.hypot(toCandidate[0], toCandidate[1]);
  if (goalNorm === 0 || candidateNorm === 0) return 0;
  return (toGoal[0] * toCandidate[0] + toGoal[1] * toCandidate[1]) / (goalNorm * candidateNorm);
}

function heatPenalty(candidate: [number, number], agent: AgentState): number {
  return -(agent.heat_map.get(posKey(candidate[0], candidate[1])) ?? 0);
}

function pathStackFromReceipts(agent: AgentState, start: [number, number]): [number, number][] {
  const stack: [number, number][] = [[start[0], start[1]]];
  for (const receipt of agent.receipts) {
    const next = receipt.to;
    const existingIdx = stack.findIndex(([x, y]) => x === next[0] && y === next[1]);
    if (existingIdx >= 0) {
      stack.splice(existingIdx + 1);
    } else {
      stack.push([next[0], next[1]]);
    }
  }
  return stack;
}

function pickMoveDepthFirstExplorer(
  agent: AgentState,
  maze: MazeGrid,
  weights: LatticeWeights,
  sensor_r: number
): [number, number] | null {
  const nbrs = neighbors4(maze, agent.pos[0], agent.pos[1]);
  if (nbrs.length === 0) return null;

  const unvisited = nbrs.filter(([nx, ny]) => (agent.visit_counts.get(posKey(nx, ny)) ?? 0) === 0);
  if (unvisited.length > 0) {
    let best = unvisited[0]!;
    let bestScore = -Infinity;
    for (const candidate of unvisited) {
      const vector = computeVTotal(candidate, maze, agent, weights, sensor_r);
      const score =
        vector.frontier * 1.75 +
        vector.importance * 1.2 +
        goalBeamField(candidate, agent, maze) * 0.8 +
        vector.security * 0.8 +
        vector.pressure_sense * 0.35 -
        stableTieBreak(candidate);
      if (score > bestScore) {
        bestScore = score;
        best = candidate;
      }
    }
    return best;
  }

  const stack = pathStackFromReceipts(agent, maze.start);
  if (stack.length > 1) {
    const backtrack = stack[stack.length - 2]!;
    if (nbrs.some(([nx, ny]) => nx === backtrack[0] && ny === backtrack[1])) return backtrack;
  }

  let leastVisited = nbrs[0]!;
  let leastVisits = Infinity;
  for (const candidate of nbrs) {
    const visits = agent.visit_counts.get(posKey(candidate[0], candidate[1])) ?? 0;
    if (visits < leastVisits) {
      leastVisits = visits;
      leastVisited = candidate;
    }
  }
  return leastVisited;
}

function stableTieBreak(candidate: [number, number]): number {
  return candidate[1] * 0.0001 + candidate[0] * 0.00001;
}

function pickMoveEnsembleBeam(
  agent: AgentState,
  maze: MazeGrid,
  weights: LatticeWeights,
  sensor_r: number,
  rng: () => number
): [number, number] | null {
  const nbrs = neighbors4(maze, agent.pos[0], agent.pos[1]);
  if (nbrs.length === 0) return null;

  const multiLattice = pickMoveMultiLattice(agent, maze, weights, sensor_r);
  const explorer = pickMoveDepthFirstExplorer(agent, maze, weights, sensor_r);
  if (explorer !== null) return explorer;
  const astarLimited = pickMoveAStarLimited(agent, maze);
  const greedy = pickMoveGreedy(agent, maze);
  const random = pickMoveRandom(agent, maze, rng);

  let best = nbrs[0]!;
  let bestScore = -Infinity;

  for (const candidate of nbrs) {
    const vector = computeVTotal(candidate, maze, agent, weights, sensor_r);
    let advisorVote = 0;
    if (samePos(explorer, candidate)) advisorVote += 4.0;
    if (samePos(multiLattice, candidate)) advisorVote += 1.5;
    if (samePos(astarLimited, candidate)) advisorVote += 0.8;
    if (samePos(greedy, candidate)) advisorVote += 0.35;
    if (samePos(random, candidate)) advisorVote += 0.08;

    const score =
      vector.total +
      advisorVote +
      goalBeamField(candidate, agent, maze) * 0.75 +
      heatPenalty(candidate, agent) * 0.45 +
      vector.frontier * 0.35 +
      vector.pressure_sense * 0.4 -
      stableTieBreak(candidate);

    if (score > bestScore) {
      bestScore = score;
      best = candidate;
    }
  }

  return best;
}

function pickMoveGreedy(agent: AgentState, maze: MazeGrid): [number, number] | null {
  const nbrs = neighbors4(maze, agent.pos[0], agent.pos[1]);
  if (nbrs.length === 0) return null;

  let best = nbrs[0]!;
  let bestD = Infinity;

  for (const [nx, ny] of nbrs) {
    const d = manhattan([nx, ny], maze.goal);
    if (d < bestD) {
      bestD = d;
      best = [nx, ny];
    }
  }
  return best;
}

function aStarGrid(
  from: [number, number],
  to: [number, number],
  maze: MazeGrid,
  known: Set<string> | null
): [number, number][] | null {
  const startKey = posKey(from[0], from[1]);
  const goalKey = posKey(to[0], to[1]);

  type Node = { pos: [number, number]; g: number; f: number };
  const open: Node[] = [{ pos: from, g: 0, f: manhattan(from, to) }];
  const closed = new Set<string>();
  const gCost = new Map<string, number>([[startKey, 0]]);
  const prevMap = new Map<string, string | null>([[startKey, null]]);

  while (open.length > 0) {
    let minIdx = 0;
    for (let i = 1; i < open.length; i++) {
      if (open[i]!.f < open[minIdx]!.f) minIdx = i;
    }
    const cur = open.splice(minIdx, 1)[0]!;
    const curKey = posKey(cur.pos[0], cur.pos[1]);

    if (closed.has(curKey)) continue;
    closed.add(curKey);

    if (curKey === goalKey) {
      const path: [number, number][] = [];
      let k: string | null = curKey;
      while (k !== null) {
        const [px, py] = k.split(',').map(Number) as [number, number];
        path.unshift([px, py]);
        k = prevMap.get(k) ?? null;
      }
      return path;
    }

    for (const [nx, ny] of neighbors4(maze, cur.pos[0], cur.pos[1])) {
      const nk = posKey(nx, ny);
      if (closed.has(nk)) continue;
      if (known !== null && !known.has(nk)) continue;

      const ng = cur.g + 1;
      if (!gCost.has(nk) || ng < gCost.get(nk)!) {
        gCost.set(nk, ng);
        prevMap.set(nk, curKey);
        open.push({ pos: [nx, ny], g: ng, f: ng + manhattan([nx, ny], to) });
      }
    }
  }
  return null;
}

function pickMoveAStarFull(
  agent: AgentState,
  maze: MazeGrid,
  oracle_path: [number, number][]
): [number, number] | null {
  const [x, y] = agent.pos;
  for (let i = 0; i < oracle_path.length - 1; i++) {
    const [px, py] = oracle_path[i]!;
    if (px === x && py === y) return oracle_path[i + 1]!;
  }
  return pickMoveGreedy(agent, maze);
}

function pickMoveAStarLimited(agent: AgentState, maze: MazeGrid): [number, number] | null {
  const [gx, gy] = maze.goal;
  if (!agent.known.has(posKey(gx, gy))) return pickMoveGreedy(agent, maze);
  const path = aStarGrid(agent.pos, maze.goal, maze, agent.known);
  if (!path || path.length < 2) return pickMoveGreedy(agent, maze);
  return path[1]!;
}

function pickMoveRandom(
  agent: AgentState,
  maze: MazeGrid,
  rng: () => number
): [number, number] | null {
  const nbrs = neighbors4(maze, agent.pos[0], agent.pos[1]);
  if (nbrs.length === 0) return null;
  return nbrs[Math.floor(rng() * nbrs.length)]!;
}

// ─── Agent lifecycle ──────────────────────────────────────────────────────────

export function createAgent(maze: MazeGrid, sensor_radius: number): AgentState {
  const agent: AgentState = {
    pos: maze.start,
    known: new Set(),
    visit_counts: new Map(),
    security_score: 0,
    max_depth_reached: 0,
    receipts: [],
    steps: 0,
    heat_map: new Map(),
    pressure_map: new Map(),
  };
  agent.visit_counts.set(posKey(maze.start[0], maze.start[1]), 1);
  agent.heat_map.set(posKey(maze.start[0], maze.start[1]), 1);
  agent.pressure_map.set(posKey(maze.start[0], maze.start[1]), 0);
  reveal(agent, maze, sensor_radius);
  return agent;
}

function agentStep(
  agent: AgentState,
  maze: MazeGrid,
  move: [number, number],
  oracle_depth_map: Map<string, number>,
  sensor_r: number,
  weights: LatticeWeights,
  prevHash: string
): MoveReceipt {
  const from = agent.pos;
  const [tx, ty] = move;

  const vector = computeVTotal(move, maze, agent, weights, sensor_r);
  agent.pressure_map.set(posKey(tx, ty), vector.pressure_sense);

  agent.pos = move;
  agent.steps++;

  const vc = agent.visit_counts.get(posKey(tx, ty)) ?? 0;
  agent.visit_counts.set(posKey(tx, ty), vc + 1);
  agent.heat_map.set(posKey(tx, ty), vc + 1);

  const c = maze.cells[ty]![tx]!;
  agent.security_score += SECURITY_COST[c.security_tier];

  const depth = oracle_depth_map.get(posKey(tx, ty)) ?? 0;
  if (depth > agent.max_depth_reached) agent.max_depth_reached = depth;

  reveal(agent, maze, sensor_r);

  const receiptPayload = {
    move_id: agent.steps,
    from: `${from[0]},${from[1]}`,
    to: `${tx},${ty}`,
    vector,
  };
  const receipt_hash = sha256chain(prevHash, receiptPayload);

  const receipt: MoveReceipt = {
    move_id: agent.steps,
    from,
    to: move,
    security_tier: c.security_tier,
    vector,
    depth_at_move: depth,
    step_ts: Date.now(),
    receipt_hash,
    prev_hash: prevHash,
  };

  agent.receipts.push(receipt);
  return receipt;
}

// ─── Mission runner ───────────────────────────────────────────────────────────

function makeAblationWeights(tag: AblationTag): LatticeWeights {
  const w = { ...DEFAULT_WEIGHTS };
  if (tag === 'no-goal') w.goal = 0;
  else if (tag === 'no-obstacle') w.obstacle = 0;
  else if (tag === 'no-frontier') w.frontier = 0;
  else if (tag === 'no-security') w.security = 0;
  else if (tag === 'no-importance') w.importance = 0;
  else if (tag === 'no-memory') w.memory = 0;
  else if (tag === 'no-edge') w.edge_channel = 0;
  else if (tag === 'no-kernel') w.kernel_convolution = 0;
  else if (tag === 'no-pressure') w.pressure_sense = 0;
  return w;
}

export function runMission(
  maze: MazeGrid,
  cfg: MazeConfig,
  alg: NavAlgorithm,
  weights: LatticeWeights,
  oracle_path: [number, number][]
): AgentState {
  const { sensor_radius: sensorR, max_steps, seed } = cfg;
  const rng = mulberry32(seed + 1);
  const depthMap = buildOracleDepthMap(oracle_path);
  const agent = createAgent(maze, sensorR);

  let prevHash = 'genesis';
  const [gx, gy] = maze.goal;

  while (agent.steps < max_steps) {
    if (agent.pos[0] === gx && agent.pos[1] === gy) break;

    let move: [number, number] | null;
    switch (alg) {
      case 'multi-lattice':
        move = pickMoveMultiLattice(agent, maze, weights, sensorR);
        break;
      case 'ensemble-beam':
        move = pickMoveEnsembleBeam(agent, maze, weights, sensorR, rng);
        break;
      case 'depth-first':
        move = pickMoveDepthFirstExplorer(agent, maze, weights, sensorR);
        break;
      case 'greedy':
        move = pickMoveGreedy(agent, maze);
        break;
      case 'astar-full':
        move = pickMoveAStarFull(agent, maze, oracle_path);
        break;
      case 'astar-limited':
        move = pickMoveAStarLimited(agent, maze);
        break;
      case 'random':
        move = pickMoveRandom(agent, maze, rng);
        break;
    }

    if (move === null) break;

    const receipt = agentStep(agent, maze, move, depthMap, sensorR, weights, prevHash);
    prevHash = receipt.receipt_hash;
  }

  return agent;
}

// ─── Scoring ──────────────────────────────────────────────────────────────────

function countReachable(maze: MazeGrid): number {
  return maze.cells.flat().filter((c) => c.type !== 'wall').length;
}

export function buildFluidHeatMap(agent: AgentState): FluidHeatCell[] {
  return Array.from(agent.heat_map.entries())
    .map(([point, visits]) => {
      const [x, y] = point.split(',').map(Number) as [number, number];
      return {
        x,
        y,
        visits,
        pressure: parseFloat((agent.pressure_map.get(point) ?? 0).toFixed(4)),
      };
    })
    .sort((a, b) => b.visits - a.visits || b.pressure - a.pressure || a.y - b.y || a.x - b.x);
}

export function verifyReceiptChain(receipts: MoveReceipt[]): number {
  if (receipts.length === 0) return 1.0;
  let valid = 0;
  let prevHash = 'genesis';
  for (const r of receipts) {
    const expected = sha256chain(prevHash, {
      move_id: r.move_id,
      from: `${r.from[0]},${r.from[1]}`,
      to: `${r.to[0]},${r.to[1]}`,
      vector: r.vector,
    });
    if (expected === r.receipt_hash && r.prev_hash === prevHash) valid++;
    prevHash = r.receipt_hash;
  }
  return valid / receipts.length;
}

export function scoreRun(
  agent: AgentState,
  maze: MazeGrid,
  cfg: MazeConfig,
  alg: string,
  oracle_path: [number, number][],
  total_ms: number
): BenchmarkScore {
  const [gx, gy] = maze.goal;
  const solved = agent.pos[0] === gx && agent.pos[1] === gy;

  const penetration_depth = agent.max_depth_reached;

  const goalPos = maze.goal;
  let minDist = euclidean(maze.start, goalPos);
  for (const r of agent.receipts) {
    const d = euclidean(r.to, goalPos);
    if (d < minDist) minDist = d;
  }

  const reachable = countReachable(maze);
  const frontier_coverage = reachable > 0 ? agent.visit_counts.size / reachable : 0;

  let revisits = 0;
  for (const v of agent.visit_counts.values()) {
    if (v > 1) revisits += v - 1;
  }
  const loop_rate = agent.steps > 0 ? revisits / agent.steps : 0;

  const security_violations = agent.receipts.filter(
    (r) =>
      r.security_tier === 'QUARANTINE' ||
      r.security_tier === 'ESCALATE' ||
      r.security_tier === 'DENY'
  ).length;

  const receipt_completeness = verifyReceiptChain(agent.receipts);
  const heatMap = buildFluidHeatMap(agent);
  const heat_peak = heatMap.length > 0 ? Math.max(...heatMap.map((cell) => cell.visits)) : 0;
  const heat_coverage = reachable > 0 ? heatMap.length / reachable : 0;
  const avg_pressure =
    agent.pressure_map.size > 0
      ? Array.from(agent.pressure_map.values()).reduce((total, value) => total + value, 0) /
        agent.pressure_map.size
      : 0;

  let stuck_loops = 0;
  for (let i = 2; i < agent.receipts.length; i++) {
    const cur = agent.receipts[i]!.to;
    const two_back = agent.receipts[i - 2]!.to;
    if (cur[0] === two_back[0] && cur[1] === two_back[1]) stuck_loops++;
  }

  const oracle_path_length = Math.max(0, oracle_path.length - 1);
  const efficiency =
    agent.steps > 0 && oracle_path_length > 0 ? oracle_path_length / agent.steps : 0;

  return {
    schema_version: 'scbe.agent_bus.vector_field_nav.bench.v1',
    maze_id: maze.id,
    alg,
    sensor_radius: cfg.sensor_radius,
    max_steps: cfg.max_steps,
    steps_taken: agent.steps,
    solved,
    penetration_depth,
    closest_distance: parseFloat(minDist.toFixed(2)),
    frontier_coverage: parseFloat(frontier_coverage.toFixed(4)),
    loop_rate: parseFloat(loop_rate.toFixed(4)),
    security_violations,
    receipt_completeness: parseFloat(receipt_completeness.toFixed(4)),
    stuck_loops,
    oracle_path_length,
    efficiency: parseFloat(efficiency.toFixed(4)),
    heat_peak,
    heat_coverage: parseFloat(heat_coverage.toFixed(4)),
    avg_pressure: parseFloat(avg_pressure.toFixed(4)),
    total_ms,
  };
}

// ─── Full benchmark ───────────────────────────────────────────────────────────

function avg(arr: number[]): number {
  if (arr.length === 0) return 0;
  return parseFloat((arr.reduce((s, v) => s + v, 0) / arr.length).toFixed(4));
}

export function runNavBench(options?: {
  mazes?: MazeConfig[];
  algorithms?: NavAlgorithm[];
  custom_weights?: Partial<LatticeWeights>;
  skip_ablation?: boolean;
}): NavBenchResult {
  const mazes = options?.mazes ?? BENCHMARK_MAZES;
  const algorithms: NavAlgorithm[] = options?.algorithms ?? [
    'multi-lattice',
    'ensemble-beam',
    'depth-first',
    'astar-full',
    'astar-limited',
    'greedy',
    'random',
  ];
  const weights: LatticeWeights = { ...DEFAULT_WEIGHTS, ...(options?.custom_weights ?? {}) };
  const ablation_tags: AblationTag[] = [
    'no-goal',
    'no-obstacle',
    'no-frontier',
    'no-security',
    'no-importance',
    'no-memory',
    'no-edge',
    'no-kernel',
    'no-pressure',
  ];
  const skipAblation = options?.skip_ablation ?? false;

  const startAll = Date.now();
  const runs: BenchmarkScore[] = [];

  for (const cfg of mazes) {
    const maze = generateMaze(cfg);
    const oracle_path = oracleBFS(maze) ?? [];

    for (const alg of algorithms) {
      const t0 = Date.now();
      const agent = runMission(maze, cfg, alg, weights, oracle_path);
      runs.push(scoreRun(agent, maze, cfg, alg, oracle_path, Date.now() - t0));
    }

    if (!skipAblation) {
      for (const tag of ablation_tags) {
        const ablWeights = makeAblationWeights(tag);
        const t0 = Date.now();
        const agent = runMission(maze, cfg, 'multi-lattice', ablWeights, oracle_path);
        runs.push(scoreRun(agent, maze, cfg, `multi-lattice+${tag}`, oracle_path, Date.now() - t0));
      }
    }
  }

  // Aggregate by algorithm label.
  const algGroups = new Map<string, BenchmarkScore[]>();
  for (const run of runs) {
    if (!algGroups.has(run.alg)) algGroups.set(run.alg, []);
    algGroups.get(run.alg)!.push(run);
  }

  const comparison: Record<string, AlgorithmSummary> = {};
  for (const [alg, algRuns] of algGroups) {
    if (alg.includes('+')) continue;
    comparison[alg] = {
      solve_rate: avg(algRuns.map((r) => (r.solved ? 1 : 0))),
      avg_efficiency: avg(algRuns.map((r) => r.efficiency)),
      avg_frontier_coverage: avg(algRuns.map((r) => r.frontier_coverage)),
      avg_loop_rate: avg(algRuns.map((r) => r.loop_rate)),
      avg_security_violations: avg(algRuns.map((r) => r.security_violations)),
      avg_stuck_loops: avg(algRuns.map((r) => r.stuck_loops)),
      avg_receipt_completeness: avg(algRuns.map((r) => r.receipt_completeness)),
      avg_heat_peak: avg(algRuns.map((r) => r.heat_peak)),
      avg_pressure: avg(algRuns.map((r) => r.avg_pressure)),
    };
  }

  const ablation_table: Record<string, AblationEntry> = {};
  const baseML = algGroups.get('multi-lattice') ?? [];
  for (const tag of ablation_tags) {
    const ablRuns = algGroups.get(`multi-lattice+${tag}`) ?? [];
    ablation_table[tag] = {
      solve_rate_delta:
        avg(ablRuns.map((r) => (r.solved ? 1 : 0))) - avg(baseML.map((r) => (r.solved ? 1 : 0))),
      efficiency_delta:
        avg(ablRuns.map((r) => r.efficiency)) - avg(baseML.map((r) => r.efficiency)),
      loop_rate_delta: avg(ablRuns.map((r) => r.loop_rate)) - avg(baseML.map((r) => r.loop_rate)),
      frontier_coverage_delta:
        avg(ablRuns.map((r) => r.frontier_coverage)) - avg(baseML.map((r) => r.frontier_coverage)),
      stuck_loops_delta:
        avg(ablRuns.map((r) => r.stuck_loops)) - avg(baseML.map((r) => r.stuck_loops)),
    };
  }

  const allML = algGroups.get('multi-lattice') ?? [];
  const allEnsemble = algGroups.get('ensemble-beam') ?? [];
  const allFull = algGroups.get('astar-full') ?? [];
  const allRandom = algGroups.get('random') ?? [];

  return {
    schema_version: 'scbe.agent_bus.vector_field_nav.v1',
    runs,
    comparison,
    ablation_table,
    summary: {
      total_mazes: mazes.length,
      total_runs: runs.length,
      multi_lattice_solve_rate: avg(allML.map((r) => (r.solved ? 1 : 0))),
      ensemble_beam_solve_rate: avg(allEnsemble.map((r) => (r.solved ? 1 : 0))),
      astar_full_solve_rate: avg(allFull.map((r) => (r.solved ? 1 : 0))),
      random_solve_rate: avg(allRandom.map((r) => (r.solved ? 1 : 0))),
      multi_lattice_avg_efficiency: avg(allML.map((r) => r.efficiency)),
      ensemble_beam_avg_efficiency: avg(allEnsemble.map((r) => r.efficiency)),
      random_solve_trials: allRandom.length,
      random_solve_successes: allRandom.filter((r) => r.solved).length,
      total_ms: Date.now() - startAll,
    },
  };
}

export function buildRandomMazeConfigs(count: number, seed = 9001): MazeConfig[] {
  const rng = mulberry32(seed);
  const sizes = [9, 11, 15, 17, 21, 25];
  return Array.from({ length: Math.max(0, count) }, (_, index) => {
    const size = sizes[Math.floor(rng() * sizes.length)]!;
    return {
      id: `random-solve-${index}`,
      width: size,
      height: size,
      seed: Math.floor(rng() * 1_000_000),
      sensor_radius: size <= 11 ? 3 : 2,
      max_steps: size * size * 2,
    };
  });
}

export function runRandomSolveSweep(options?: {
  trials?: number;
  seed?: number;
  algorithm?: NavAlgorithm;
}): RandomSolveSweepResult {
  const started = Date.now();
  const trials = options?.trials ?? 24;
  const algorithm = options?.algorithm ?? 'random';
  const mazes = buildRandomMazeConfigs(trials, options?.seed ?? 9001);
  const runs: BenchmarkScore[] = [];
  for (const cfg of mazes) {
    const maze = generateMaze(cfg);
    const oraclePath = oracleBFS(maze) ?? [];
    const t0 = Date.now();
    const agent = runMission(maze, cfg, algorithm, DEFAULT_WEIGHTS, oraclePath);
    runs.push(scoreRun(agent, maze, cfg, algorithm, oraclePath, Date.now() - t0));
  }
  const successes = runs.filter((run) => run.solved).length;
  return {
    schema_version: 'scbe.agent_bus.vector_field_nav.random_solve_sweep.v1',
    runs,
    summary: {
      trials: runs.length,
      algorithm,
      solve_rate: avg(runs.map((run) => (run.solved ? 1 : 0))),
      solve_successes: successes,
      random_solve_rate: avg(runs.map((run) => (run.solved ? 1 : 0))),
      random_solve_successes: successes,
      avg_heat_peak: avg(runs.map((run) => run.heat_peak)),
      avg_pressure: avg(runs.map((run) => run.avg_pressure)),
      total_ms: Date.now() - started,
    },
  };
}
