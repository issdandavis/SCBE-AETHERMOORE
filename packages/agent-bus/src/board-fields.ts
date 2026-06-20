/**
 * @file board-fields.ts
 * @module agent-bus/board-fields
 * @layer Cross-layer agentic board state
 * @component BoardFields — multi-domain governed map for agentic workflows
 *
 * Wraps a ReactionChain with a spatial/epistemic board so each step has a
 * declared domain, clearance requirement, tick cost, and known_state.
 *
 * Domains model the layers where work happens:
 *   surface    — files, tasks, docs, UI (everyday read/write)
 *   air        — model calls, summaries, fast routing
 *   sea        — long-running workflows, queues, pipelines
 *   subground  — secrets, provenance, dependency roots, poisoned inputs
 *   space      — high-level goals, mission state, global strategy
 *   personal   — each agent's private Polly Pad state
 *   shared     — squad board, leader state, shared memory
 *
 * Security invariant: cells tagged 'poisoned' are never entered — they block
 * the step immediately without calling the inner runner. This is the board-level
 * quarantine before the 14-layer promotion pipeline sees the content.
 *
 * Clearance levels form a total order: none < read_only < write < execute < admin.
 * An agent can only enter a cell if its clearance >= cell.clearance.
 *
 * Tick cost accumulates across the run and provides a cheap budget signal.
 * The board state is serializable — checkpoint it between runs.
 */

import type { AgentBusEvent } from './index.js';
import { enqueueEvent, processOneEvent, getEventStatus } from './queue.js';
import type {
  ReactionChain,
  ReactionRunnerFn,
  ReactionChainRunOptions,
  ReactionChainRunResult,
} from './reaction-chain.js';
import { runReactionChain } from './reaction-chain.js';

// ─── Core board types ─────────────────────────────────────────────────────────

export type BoardDomain = 'surface' | 'air' | 'sea' | 'subground' | 'space' | 'personal' | 'shared';

export type BoardOccupancy = 'empty' | 'agent' | 'task' | 'artifact' | 'blocked';

/**
 * Epistemic state of a cell from the agent's perspective.
 *
 * unknown   — never observed; contents are fog-of-war
 * observed  — a step is or was operating here; data not yet verified
 * verified  — a step completed successfully; output passed governance
 * poisoned  — malicious or tainted content detected; entry permanently blocked
 * blocked   — structurally inaccessible (topology constraint, not data quality)
 */
export type BoardKnownState = 'unknown' | 'observed' | 'verified' | 'poisoned' | 'blocked';

/**
 * Ordered clearance levels. Higher index = higher privilege.
 * An agent with clearance C can enter any cell requiring C or lower.
 */
export type ClearanceLevel = 'none' | 'read_only' | 'write' | 'execute' | 'admin';

const CLEARANCE_RANK: Record<ClearanceLevel, number> = {
  none: 0,
  read_only: 1,
  write: 2,
  execute: 3,
  admin: 4,
};

export interface BoardCell {
  id: string;
  domain: BoardDomain;
  occupancy: BoardOccupancy;
  /** Minimum clearance required to enter this cell. */
  clearance: ClearanceLevel;
  /** Tick cost to operate here. Adds to the run's total_cost. */
  cost_ticks: number;
  /** Risk tags (e.g. 'tainted_source', 'unverified', 'external_input'). */
  risk: string[];
  known_state: BoardKnownState;
  /** IDs of cells this cell is linked to (bidirectional traversal not implied). */
  links: string[];
}

export interface BoardState {
  schema_version: 'scbe_board_state_v1';
  board_id: string;
  cells: Record<string, BoardCell>;
  /** Current board clock tick. Advances by each step's cost_ticks. */
  tick: number;
  /** Cumulative tick cost across all steps run on this board. */
  total_cost: number;
}

// ─── Pure board operations ────────────────────────────────────────────────────

export function createBoard(board_id: string, cells: BoardCell[] = []): BoardState {
  const cellMap: Record<string, BoardCell> = {};
  for (const c of cells) {
    cellMap[c.id] = c;
  }
  return {
    schema_version: 'scbe_board_state_v1',
    board_id,
    cells: cellMap,
    tick: 0,
    total_cost: 0,
  };
}

export function getCell(state: BoardState, cellId: string): BoardCell | null {
  return state.cells[cellId] ?? null;
}

/** Immutable cell update — returns a new BoardState. */
export function setCell(state: BoardState, cell: BoardCell): BoardState {
  return { ...state, cells: { ...state.cells, [cell.id]: cell } };
}

/** True if an agent with the given clearance is permitted to enter the cell. */
export function canEnter(cell: BoardCell, agentClearance: ClearanceLevel): boolean {
  if (cell.known_state === 'poisoned' || cell.known_state === 'blocked') return false;
  if (cell.occupancy === 'blocked') return false;
  return CLEARANCE_RANK[agentClearance] >= CLEARANCE_RANK[cell.clearance];
}

/**
 * Minimum tick-distance between two cells via Dijkstra over the links graph.
 * Edge weight = destination cell's cost_ticks.
 * Returns null if toId is not reachable from fromId.
 */
export function measureTickDistance(
  state: BoardState,
  fromId: string,
  toId: string
): number | null {
  if (fromId === toId) return 0;
  const dist: Record<string, number> = { [fromId]: 0 };
  const visited = new Set<string>();
  // [cellId, accumulated_cost]
  const queue: Array<[string, number]> = [[fromId, 0]];

  while (queue.length > 0) {
    queue.sort((a, b) => a[1] - b[1]);
    const [current, cost] = queue.shift()!;
    if (visited.has(current)) continue;
    visited.add(current);
    if (current === toId) return cost;

    const cell = state.cells[current];
    if (!cell) continue;

    for (const linkId of cell.links) {
      if (visited.has(linkId)) continue;
      const linkCell = state.cells[linkId];
      if (!linkCell) continue;
      const newCost = cost + linkCell.cost_ticks;
      if (newCost < (dist[linkId] ?? Infinity)) {
        dist[linkId] = newCost;
        queue.push([linkId, newCost]);
      }
    }
  }
  return null;
}

// ─── Boarded chain integration ────────────────────────────────────────────────

/**
 * Board-placement metadata for one reaction step.
 * Steps without a placement entry run with no board constraints.
 */
export interface BoardPlacement {
  /** Cell this reaction operates on. */
  cell_id?: string;
  /** Required clearance. Defaults to cell.clearance if omitted. */
  requires_clearance?: ClearanceLevel;
  /** Override tick cost. Defaults to cell.cost_ticks if omitted. */
  cost_ticks?: number;
  /** Risk tags this step may produce (informational; stored on the result). */
  risk?: string[];
  /** Cell occupancy to set after a successful step. Default: 'artifact'. */
  result_occupancy?: BoardOccupancy;
}

/** A ReactionChain decorated with per-step board placements. */
export interface BoardedChain {
  schema_version: 'scbe_boarded_chain_v1';
  chain: ReactionChain;
  /** Keyed by reaction spec id. Steps with no entry run without board constraints. */
  placements: Record<string, BoardPlacement>;
  /** Clearance level of the agent running this chain. Default: 'none'. */
  agent_clearance?: ClearanceLevel;
}

export interface BoardedChainRunResult {
  schema_version: 'scbe_boarded_chain_run_v1';
  board_state: BoardState;
  chain_result: ReactionChainRunResult;
  tick_total: number;
  /** Reaction IDs that were blocked by insufficient clearance. */
  clearance_blocks: string[];
  /** Reaction IDs that were blocked because their target cell was poisoned. */
  poison_encounters: string[];
}

// Duplicated from reaction-chain.ts to avoid a circular import through the re-export in index.ts
function makeQueueRunner(options: ReactionChainRunOptions): ReactionRunnerFn {
  return async (event: AgentBusEvent) => {
    const runId = enqueueEvent(event, options);
    await processOneEvent();
    const queued = getEventStatus(runId);
    return { ok: queued?.result?.ok ?? false, result: queued?.result?.result ?? null };
  };
}

/**
 * Extract the reaction ID from a seriesId produced by buildReactionEvent.
 * Format: "${12-hex-runId}-${reactionId}" — the runId is pure hex so the
 * first '-' is always the separator, even if reactionId contains dashes.
 */
function extractReactionId(event: AgentBusEvent): string | null {
  const sid = event.seriesId;
  if (!sid) return null;
  const idx = sid.indexOf('-');
  return idx === -1 ? null : sid.slice(idx + 1);
}

function meetsClearance(agent: ClearanceLevel, required: ClearanceLevel): boolean {
  return CLEARANCE_RANK[agent] >= CLEARANCE_RANK[required];
}

/**
 * Run a ReactionChain with board-field governance.
 *
 * Before each step with a cell_id placement:
 *   1. Block immediately if the cell is poisoned (poison_encounters logged).
 *   2. Block immediately if agent clearance < required clearance (clearance_blocks logged).
 *   3. Mark cell occupancy='task', known_state='observed' (if unknown).
 *
 * After each step completes:
 *   - ok=true  → cell occupancy set to result_occupancy (default 'artifact'), known_state='verified'
 *   - ok=false → cell occupancy reset to 'empty', known_state unchanged
 *   - Board tick advances by step's cost_ticks.
 *
 * Steps with no placement entry are passed through to the inner runner unchanged.
 */
export async function runBoardedChain(
  boardedChain: BoardedChain,
  boardState: BoardState,
  options: ReactionChainRunOptions = {}
): Promise<BoardedChainRunResult> {
  let board = boardState;
  const clearance_blocks: string[] = [];
  const poison_encounters: string[] = [];
  const agentClearance: ClearanceLevel = boardedChain.agent_clearance ?? 'none';
  const baseRunner: ReactionRunnerFn = options.runEvent ?? makeQueueRunner(options);

  const boardRunner: ReactionRunnerFn = async (event: AgentBusEvent) => {
    const reactionId = extractReactionId(event);
    const placement = reactionId != null ? boardedChain.placements[reactionId] : undefined;

    if (placement?.cell_id) {
      const cell = getCell(board, placement.cell_id);
      if (cell) {
        // Poison blocks before clearance — even admins cannot enter poisoned cells
        if (cell.known_state === 'poisoned') {
          if (reactionId != null) poison_encounters.push(reactionId);
          return {
            ok: false,
            result: { blocked: true, reason: 'poisoned_cell', cell_id: placement.cell_id },
          };
        }

        const requiredClearance = placement.requires_clearance ?? cell.clearance;
        if (!meetsClearance(agentClearance, requiredClearance)) {
          if (reactionId != null) clearance_blocks.push(reactionId);
          return {
            ok: false,
            result: {
              blocked: true,
              reason: 'clearance_denied',
              cell_id: placement.cell_id,
              required: requiredClearance,
              agent: agentClearance,
            },
          };
        }

        // Mark cell as being operated on
        board = setCell(board, {
          ...cell,
          occupancy: 'task',
          known_state: cell.known_state === 'unknown' ? 'observed' : cell.known_state,
        });
      }
    }

    const stepResult = await baseRunner(event);

    if (placement?.cell_id) {
      const cell = getCell(board, placement.cell_id);
      if (cell) {
        const costTicks = placement.cost_ticks ?? cell.cost_ticks;
        board = {
          ...setCell(board, {
            ...cell,
            occupancy: stepResult.ok ? (placement.result_occupancy ?? 'artifact') : 'empty',
            known_state: stepResult.ok ? 'verified' : cell.known_state,
          }),
          tick: board.tick + costTicks,
          total_cost: board.total_cost + costTicks,
        };
      }
    }

    return stepResult;
  };

  const chain_result = await runReactionChain(boardedChain.chain, {
    ...options,
    runEvent: boardRunner,
  });

  return {
    schema_version: 'scbe_boarded_chain_run_v1',
    board_state: board,
    chain_result,
    tick_total: board.tick,
    clearance_blocks,
    poison_encounters,
  };
}
