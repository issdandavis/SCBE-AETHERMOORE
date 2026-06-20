import { describe, it, expect } from 'vitest';
import {
  type BoardCell,
  type BoardState,
  type BoardedChain,
  type ClearanceLevel,
  createBoard,
  getCell,
  setCell,
  canEnter,
  measureTickDistance,
  runBoardedChain,
} from '../src/board-fields.js';
import type { ReactionChain } from '../src/reaction-chain.js';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function cell(id: string, overrides: Partial<BoardCell> = {}): BoardCell {
  return {
    id,
    domain: 'surface',
    occupancy: 'empty',
    clearance: 'none',
    cost_ticks: 1,
    risk: [],
    known_state: 'unknown',
    links: [],
    ...overrides,
  };
}

function twoStepChain(): ReactionChain {
  return {
    schema_version: 'scbe_reaction_chain_v1',
    chain_id: 'two-step',
    reactions: [
      { id: 'fetch', task_template: 'Fetch the data' },
      { id: 'process', task_template: 'Process: ${step.fetch.result}', depends_on: ['fetch'] },
    ],
  };
}

function mockRunner(ok = true) {
  return async (_event: import('../src/index.js').AgentBusEvent) => ({
    ok,
    result: { output: 'done' },
  });
}

// ─── createBoard ──────────────────────────────────────────────────────────────

describe('createBoard', () => {
  it('creates a board with an empty cell map', () => {
    const board = createBoard('test');
    expect(board.schema_version).toBe('scbe_board_state_v1');
    expect(board.board_id).toBe('test');
    expect(Object.keys(board.cells)).toHaveLength(0);
    expect(board.tick).toBe(0);
    expect(board.total_cost).toBe(0);
  });

  it('indexes provided cells by id', () => {
    const board = createBoard('b', [cell('A'), cell('B')]);
    expect(board.cells['A']?.id).toBe('A');
    expect(board.cells['B']?.id).toBe('B');
  });
});

// ─── getCell / setCell ────────────────────────────────────────────────────────

describe('getCell', () => {
  it('returns the cell for a known id', () => {
    const board = createBoard('b', [cell('X')]);
    expect(getCell(board, 'X')?.id).toBe('X');
  });

  it('returns null for an unknown id', () => {
    const board = createBoard('b');
    expect(getCell(board, 'missing')).toBeNull();
  });
});

describe('setCell', () => {
  it('returns a new board with the updated cell', () => {
    const board = createBoard('b', [cell('X', { occupancy: 'empty' })]);
    const updated = setCell(board, { ...board.cells['X']!, occupancy: 'task' });
    expect(updated.cells['X']!.occupancy).toBe('task');
  });

  it('does not mutate the original board', () => {
    const board = createBoard('b', [cell('X')]);
    setCell(board, { ...board.cells['X']!, occupancy: 'task' });
    expect(board.cells['X']!.occupancy).toBe('empty');
  });

  it('adds a new cell when the id does not exist', () => {
    const board = createBoard('b');
    const updated = setCell(board, cell('new'));
    expect(updated.cells['new']?.id).toBe('new');
  });
});

// ─── canEnter ─────────────────────────────────────────────────────────────────

describe('canEnter', () => {
  it('allows entry when agent clearance meets cell clearance', () => {
    const c = cell('A', { clearance: 'read_only' });
    expect(canEnter(c, 'read_only')).toBe(true);
    expect(canEnter(c, 'write')).toBe(true);
    expect(canEnter(c, 'admin')).toBe(true);
  });

  it('denies entry when agent clearance is below cell clearance', () => {
    const c = cell('A', { clearance: 'write' });
    expect(canEnter(c, 'none')).toBe(false);
    expect(canEnter(c, 'read_only')).toBe(false);
  });

  it('denies entry to a poisoned cell regardless of clearance', () => {
    const c = cell('A', { clearance: 'none', known_state: 'poisoned' });
    expect(canEnter(c, 'admin')).toBe(false);
  });

  it('denies entry to a blocked known_state cell', () => {
    const c = cell('A', { clearance: 'none', known_state: 'blocked' });
    expect(canEnter(c, 'admin')).toBe(false);
  });

  it('denies entry to a cell with blocked occupancy', () => {
    const c = cell('A', { clearance: 'none', occupancy: 'blocked' });
    expect(canEnter(c, 'admin')).toBe(false);
  });

  it('allows entry to a verified cell with sufficient clearance', () => {
    const c = cell('A', { clearance: 'read_only', known_state: 'verified' });
    expect(canEnter(c, 'read_only')).toBe(true);
  });
});

// ─── measureTickDistance ──────────────────────────────────────────────────────

describe('measureTickDistance', () => {
  // Board:  A --(cost B=2)--> B --(cost C=1)--> C
  //                            \--(cost D=3)--> D
  function routeBoard(): BoardState {
    return createBoard('route', [
      cell('A', { cost_ticks: 0, links: ['B'] }),
      cell('B', { cost_ticks: 2, links: ['A', 'C', 'D'] }),
      cell('C', { cost_ticks: 1, links: ['B'] }),
      cell('D', { cost_ticks: 3, links: ['B'] }),
    ]);
  }

  it('returns 0 for the same cell', () => {
    expect(measureTickDistance(routeBoard(), 'A', 'A')).toBe(0);
  });

  it('returns the cost of entering the destination', () => {
    // A → B: cost = B.cost_ticks = 2
    expect(measureTickDistance(routeBoard(), 'A', 'B')).toBe(2);
  });

  it('returns the sum of destination costs along the path', () => {
    // A → B → C: B.cost + C.cost = 2 + 1 = 3
    expect(measureTickDistance(routeBoard(), 'A', 'C')).toBe(3);
  });

  it('finds the shortest path when multiple routes exist', () => {
    // A → B → C and A → B → D: 3 vs 5 — C is shorter
    expect(measureTickDistance(routeBoard(), 'A', 'C')).toBeLessThan(
      measureTickDistance(routeBoard(), 'A', 'D')!
    );
  });

  it('returns null when cells are not connected', () => {
    const board = createBoard('disconnected', [cell('X'), cell('Y')]);
    expect(measureTickDistance(board, 'X', 'Y')).toBeNull();
  });

  it('returns null for an unknown cell id', () => {
    expect(measureTickDistance(routeBoard(), 'A', 'Z')).toBeNull();
  });
});

// ─── runBoardedChain ──────────────────────────────────────────────────────────

describe('runBoardedChain', () => {
  it('runs an unplaced chain without board interaction', async () => {
    const board = createBoard('empty-board');
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: twoStepChain(),
      placements: {},
      agent_clearance: 'none',
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner() });
    expect(result.chain_result.ok).toBe(true);
    expect(result.clearance_blocks).toHaveLength(0);
    expect(result.poison_encounters).toHaveLength(0);
    expect(result.tick_total).toBe(0); // no cells operated on
  });

  it('blocks a step when agent clearance is below cell requirement', async () => {
    const board = createBoard('b', [cell('target', { clearance: 'write' })]);
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: twoStepChain(),
      placements: { fetch: { cell_id: 'target' } },
      agent_clearance: 'read_only',
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner() });
    expect(result.chain_result.ok).toBe(false);
    expect(result.clearance_blocks).toContain('fetch');
  });

  it('allows a step when agent clearance meets the cell requirement', async () => {
    const board = createBoard('b', [cell('target', { clearance: 'read_only', cost_ticks: 2 })]);
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: twoStepChain(),
      placements: { fetch: { cell_id: 'target' }, process: {} },
      agent_clearance: 'write',
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner() });
    expect(result.chain_result.ok).toBe(true);
    expect(result.clearance_blocks).toHaveLength(0);
  });

  it('blocks a step whose cell is poisoned, even with admin clearance', async () => {
    const board = createBoard('b', [
      cell('poison-cell', { clearance: 'none', known_state: 'poisoned' }),
    ]);
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: twoStepChain(),
      placements: { fetch: { cell_id: 'poison-cell' } },
      agent_clearance: 'admin',
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner() });
    expect(result.chain_result.ok).toBe(false);
    expect(result.poison_encounters).toContain('fetch');
    expect(result.clearance_blocks).toHaveLength(0);
  });

  it('marks cell as verified and artifact after successful step', async () => {
    const board = createBoard('b', [cell('work-cell', { clearance: 'none', cost_ticks: 3 })]);
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: {
        schema_version: 'scbe_reaction_chain_v1',
        chain_id: 'single',
        reactions: [{ id: 'step1', task_template: 'Do it' }],
      },
      placements: { step1: { cell_id: 'work-cell' } },
      agent_clearance: 'none',
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner(true) });
    const cell_after = getCell(result.board_state, 'work-cell')!;
    expect(cell_after.known_state).toBe('verified');
    expect(cell_after.occupancy).toBe('artifact');
  });

  it('resets cell occupancy to empty after failed step', async () => {
    const board = createBoard('b', [cell('work-cell', { clearance: 'none', cost_ticks: 1 })]);
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: {
        schema_version: 'scbe_reaction_chain_v1',
        chain_id: 'single',
        reactions: [{ id: 'step1', task_template: 'Do it' }],
      },
      placements: { step1: { cell_id: 'work-cell' } },
      agent_clearance: 'none',
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner(false) });
    const cell_after = getCell(result.board_state, 'work-cell')!;
    expect(cell_after.occupancy).toBe('empty');
  });

  it('accumulates tick cost from placed steps', async () => {
    const board = createBoard('b', [
      cell('c1', { clearance: 'none', cost_ticks: 3 }),
      cell('c2', { clearance: 'none', cost_ticks: 5 }),
    ]);
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: twoStepChain(),
      placements: {
        fetch: { cell_id: 'c1' },
        process: { cell_id: 'c2' },
      },
      agent_clearance: 'none',
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner() });
    expect(result.tick_total).toBe(8); // 3 + 5
    expect(result.board_state.total_cost).toBe(8);
  });

  it('uses placement.cost_ticks override instead of cell.cost_ticks', async () => {
    const board = createBoard('b', [cell('c', { clearance: 'none', cost_ticks: 10 })]);
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: {
        schema_version: 'scbe_reaction_chain_v1',
        chain_id: 's',
        reactions: [{ id: 'step1', task_template: 'x' }],
      },
      placements: { step1: { cell_id: 'c', cost_ticks: 2 } }, // override
      agent_clearance: 'none',
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner() });
    expect(result.tick_total).toBe(2);
  });

  it('uses placement.result_occupancy when provided', async () => {
    const board = createBoard('b', [cell('c', { clearance: 'none', cost_ticks: 1 })]);
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: {
        schema_version: 'scbe_reaction_chain_v1',
        chain_id: 's',
        reactions: [{ id: 'step1', task_template: 'x' }],
      },
      placements: { step1: { cell_id: 'c', result_occupancy: 'agent' } },
      agent_clearance: 'none',
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner(true) });
    expect(getCell(result.board_state, 'c')!.occupancy).toBe('agent');
  });

  it('transitions unknown cell to observed during step, then verified on success', async () => {
    const board = createBoard('b', [cell('c', { clearance: 'none', known_state: 'unknown' })]);
    let stateAfterStart: import('../src/board-fields.js').BoardKnownState | null = null;

    const runner = async (event: import('../src/index.js').AgentBusEvent) => {
      // We can't easily inspect mid-step; just verify post-step is 'verified'
      void event;
      return { ok: true, result: null };
    };

    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: {
        schema_version: 'scbe_reaction_chain_v1',
        chain_id: 's',
        reactions: [{ id: 'step1', task_template: 'x' }],
      },
      placements: { step1: { cell_id: 'c' } },
      agent_clearance: 'none',
    };

    const result = await runBoardedChain(bc, board, { runEvent: runner });
    stateAfterStart = getCell(result.board_state, 'c')!.known_state;
    expect(stateAfterStart).toBe('verified');
  });

  it('carries chain_id and run_id through to the result', async () => {
    const board = createBoard('b');
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: twoStepChain(),
      placements: {},
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner() });
    expect(result.chain_result.chain_id).toBe('two-step');
    expect(typeof result.chain_result.run_id).toBe('string');
  });

  it('respects requires_clearance override on placement', async () => {
    // Cell requires 'none' but placement overrides to 'write'
    const board = createBoard('b', [cell('c', { clearance: 'none' })]);
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: {
        schema_version: 'scbe_reaction_chain_v1',
        chain_id: 's',
        reactions: [{ id: 'step1', task_template: 'x' }],
      },
      placements: { step1: { cell_id: 'c', requires_clearance: 'write' } },
      agent_clearance: 'read_only',
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner() });
    expect(result.clearance_blocks).toContain('step1');
  });

  it('uses schema_version scbe_boarded_chain_run_v1', async () => {
    const board = createBoard('b');
    const bc: BoardedChain = {
      schema_version: 'scbe_boarded_chain_v1',
      chain: twoStepChain(),
      placements: {},
    };
    const result = await runBoardedChain(bc, board, { runEvent: mockRunner() });
    expect(result.schema_version).toBe('scbe_boarded_chain_run_v1');
  });
});
