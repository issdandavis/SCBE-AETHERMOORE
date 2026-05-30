import { describe, it, expect } from 'vitest';
import {
  type ReactionChain,
  type ReactionChainState,
  startChain,
  getReadyReactions,
  advanceChain,
  renderTask,
  buildReactionEvent,
  runReactionChain,
} from '../src/reaction-chain.js';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function linearChain(): ReactionChain {
  return {
    schema_version: 'scbe_reaction_chain_v1',
    chain_id: 'linear',
    reactions: [
      { id: 'A', task_template: 'Do A' },
      { id: 'B', task_template: 'Do B', depends_on: ['A'] },
    ],
  };
}

function parallelChain(): ReactionChain {
  return {
    schema_version: 'scbe_reaction_chain_v1',
    chain_id: 'parallel',
    reactions: [
      { id: 'A', task_template: 'Do A' },
      { id: 'B', task_template: 'Do B' },
      { id: 'C', task_template: 'Do C', depends_on: ['A', 'B'] },
    ],
  };
}

function mockRunner(ok = true): import('../src/reaction-chain.js').ReactionRunnerFn {
  return async (_event) => ({ ok, result: { fired: _event.task } });
}

// ─── startChain ───────────────────────────────────────────────────────────────

describe('startChain', () => {
  it('initializes all steps as pending', () => {
    const { state } = startChain(linearChain());
    expect(state.steps['A']!.status).toBe('pending');
    expect(state.steps['B']!.status).toBe('pending');
  });

  it('sets status to running for non-empty chain', () => {
    const { state } = startChain(linearChain());
    expect(state.status).toBe('running');
  });

  it('sets status to complete for empty chain', () => {
    const empty: ReactionChain = {
      schema_version: 'scbe_reaction_chain_v1',
      chain_id: 'empty',
      reactions: [],
    };
    const { state, ready } = startChain(empty);
    expect(state.status).toBe('complete');
    expect(ready).toHaveLength(0);
  });

  it('returns only dep-free reactions as ready', () => {
    const { ready } = startChain(linearChain());
    expect(ready).toEqual(['A']);
  });

  it('returns all dep-free reactions when multiple have no deps', () => {
    const { ready } = startChain(parallelChain());
    expect(ready).toContain('A');
    expect(ready).toContain('B');
    expect(ready).not.toContain('C');
  });

  it('assigns a unique run_id each call', () => {
    const { state: s1 } = startChain(linearChain());
    const { state: s2 } = startChain(linearChain());
    expect(s1.run_id).not.toBe(s2.run_id);
  });

  it('carries the chain_id into state', () => {
    const { state } = startChain(linearChain());
    expect(state.chain_id).toBe('linear');
  });
});

// ─── getReadyReactions ────────────────────────────────────────────────────────

describe('getReadyReactions', () => {
  it('returns step once its dep is done', () => {
    const chain = linearChain();
    const { state } = startChain(chain);
    const withADone: ReactionChainState = {
      ...state,
      steps: { ...state.steps, A: { id: 'A', status: 'done' } },
    };
    expect(getReadyReactions(withADone, chain)).toEqual(['B']);
  });

  it('does not return a running step', () => {
    const chain = linearChain();
    const { state } = startChain(chain);
    const withARunning: ReactionChainState = {
      ...state,
      steps: { ...state.steps, A: { id: 'A', status: 'running' } },
    };
    expect(getReadyReactions(withARunning, chain)).toEqual([]);
  });

  it('does not return a step with an unmet dep', () => {
    const chain = linearChain();
    const { state } = startChain(chain);
    expect(getReadyReactions(state, chain)).not.toContain('B');
  });

  it('returns a step only when ALL deps are done', () => {
    const chain = parallelChain();
    const { state } = startChain(chain);
    const withADone: ReactionChainState = {
      ...state,
      steps: { ...state.steps, A: { id: 'A', status: 'done' } },
    };
    // C needs both A and B — B is still pending, so C is not ready
    expect(getReadyReactions(withADone, chain)).not.toContain('C');
  });
});

// ─── advanceChain ─────────────────────────────────────────────────────────────

describe('advanceChain', () => {
  it('marks a successful step as done', () => {
    const chain = linearChain();
    const { state } = startChain(chain);
    const { state: next } = advanceChain(state, chain, 'A', 'output', true);
    expect(next.steps['A']!.status).toBe('done');
    expect(next.steps['A']!.result).toBe('output');
  });

  it('returns newly ready steps after success', () => {
    const chain = linearChain();
    const { state } = startChain(chain);
    const { newly_ready } = advanceChain(state, chain, 'A', null, true);
    expect(newly_ready).toEqual(['B']);
  });

  it('marks a failed step as blocked', () => {
    const chain = linearChain();
    const { state } = startChain(chain);
    const { state: next } = advanceChain(state, chain, 'A', null, false);
    expect(next.steps['A']!.status).toBe('blocked');
  });

  it('returns no newly_ready steps when a step fails', () => {
    const chain = linearChain();
    const { state } = startChain(chain);
    const { newly_ready } = advanceChain(state, chain, 'A', null, false);
    expect(newly_ready).toHaveLength(0);
  });

  it('sets chain status to complete when all steps are done', () => {
    const chain = linearChain();
    const { state: s0 } = startChain(chain);
    const { state: s1 } = advanceChain(s0, chain, 'A', null, true);
    const { state: s2, done } = advanceChain(s1, chain, 'B', null, true);
    expect(s2.status).toBe('complete');
    expect(done).toBe(true);
  });

  it('sets chain status to blocked when a failure makes no steps reachable', () => {
    const chain = linearChain();
    const { state } = startChain(chain);
    // A fails → B depends on A → nothing reachable
    const { state: next } = advanceChain(state, chain, 'A', null, false);
    expect(next.status).toBe('blocked');
  });

  it('does NOT set blocked if other independent steps are still reachable', () => {
    // Chain: A (no deps), B (no deps), C (depends_on: [A, B])
    // A fails but B is still pending (no dep on A)
    const chain = parallelChain();
    const { state } = startChain(chain);
    const { state: next } = advanceChain(state, chain, 'A', null, false);
    // B is still pending and reachable → chain should still be 'running'
    expect(next.status).toBe('running');
  });

  it('sets chain to blocked when all remaining steps transitively depend on a blocked step', () => {
    // Parallel chain: A fails, then B succeeds, C depends on [A, B] so C can never run
    const chain = parallelChain();
    const { state: s0 } = startChain(chain);
    const { state: s1 } = advanceChain(s0, chain, 'A', null, false); // A blocked
    const { state: s2 } = advanceChain(s1, chain, 'B', null, true); // B done
    // C depends on A (blocked) and B (done) — C is permanently unreachable
    expect(s2.status).toBe('blocked');
  });

  it('attaches finished_at to the completed step', () => {
    const chain = linearChain();
    const { state } = startChain(chain);
    const { state: next } = advanceChain(state, chain, 'A', null, true);
    expect(typeof next.steps['A']!.finished_at).toBe('string');
  });
});

// ─── renderTask ───────────────────────────────────────────────────────────────

describe('renderTask', () => {
  function stateWithDoneStep(id: string, result: unknown): ReactionChainState {
    return {
      schema_version: 'scbe_reaction_chain_state_v1',
      chain_id: 'test',
      run_id: 'r1',
      started_at: new Date().toISOString(),
      status: 'running',
      steps: { [id]: { id, status: 'done', result } },
    };
  }

  it('replaces ${step.<id>.result} with string values', () => {
    const state = stateWithDoneStep('fetch', 'some content');
    expect(renderTask('Process: ${step.fetch.result}', state)).toBe('Process: some content');
  });

  it('JSON-serializes non-string result values', () => {
    const state = stateWithDoneStep('fetch', { data: [1, 2] });
    expect(renderTask('Got: ${step.fetch.result}', state)).toBe('Got: {"data":[1,2]}');
  });

  it('replaces ${step.<id>.status}', () => {
    const state = stateWithDoneStep('step1', null);
    expect(renderTask('Status: ${step.step1.status}', state)).toBe('Status: done');
  });

  it('replaces ${step.<id>.ok} with true when step is done', () => {
    const state = stateWithDoneStep('step1', null);
    expect(renderTask('${step.step1.ok}', state)).toBe('true');
  });

  it('replaces ${step.<id>.ok} with false for non-done status', () => {
    const state: ReactionChainState = {
      schema_version: 'scbe_reaction_chain_state_v1',
      chain_id: 'test',
      run_id: 'r1',
      started_at: new Date().toISOString(),
      status: 'running',
      steps: { s: { id: 's', status: 'blocked' } },
    };
    expect(renderTask('${step.s.ok}', state)).toBe('false');
  });

  it('leaves unknown step references unchanged', () => {
    const state: ReactionChainState = {
      schema_version: 'scbe_reaction_chain_state_v1',
      chain_id: 'test',
      run_id: 'r1',
      started_at: new Date().toISOString(),
      status: 'running',
      steps: {},
    };
    const template = 'Missing: ${step.unknown.result}';
    expect(renderTask(template, state)).toBe(template);
  });

  it('handles multiple references in one template', () => {
    const state: ReactionChainState = {
      schema_version: 'scbe_reaction_chain_state_v1',
      chain_id: 'test',
      run_id: 'r1',
      started_at: new Date().toISOString(),
      status: 'running',
      steps: {
        a: { id: 'a', status: 'done', result: 'hello' },
        b: { id: 'b', status: 'done', result: 'world' },
      },
    };
    expect(renderTask('${step.a.result} ${step.b.result}', state)).toBe('hello world');
  });
});

// ─── buildReactionEvent ───────────────────────────────────────────────────────

describe('buildReactionEvent', () => {
  function emptyRunState(): ReactionChainState {
    return {
      schema_version: 'scbe_reaction_chain_state_v1',
      chain_id: 'test',
      run_id: 'run-abc',
      started_at: new Date().toISOString(),
      status: 'running',
      steps: {},
    };
  }

  it('sets task from rendered task_template', () => {
    const event = buildReactionEvent(
      { id: 'step1', task_template: 'Do the thing' },
      emptyRunState(),
      'run-abc'
    );
    expect(event.task).toBe('Do the thing');
  });

  it('encodes seriesId as chainRunId-reactionId', () => {
    const event = buildReactionEvent(
      { id: 'step1', task_template: 'x' },
      emptyRunState(),
      'run-abc'
    );
    expect(event.seriesId).toBe('run-abc-step1');
  });

  it('maps model_tier local to ollama dispatchProvider', () => {
    const event = buildReactionEvent(
      { id: 's', task_template: 'x', model_tier: 'local' },
      emptyRunState(),
      'r'
    );
    expect(event.dispatchProvider).toBe('ollama');
  });

  it('maps model_tier free to cerebras dispatchProvider', () => {
    const event = buildReactionEvent(
      { id: 's', task_template: 'x', model_tier: 'free' },
      emptyRunState(),
      'r'
    );
    expect(event.dispatchProvider).toBe('cerebras');
  });

  it('maps model_tier paid to anthropic dispatchProvider', () => {
    const event = buildReactionEvent(
      { id: 's', task_template: 'x', model_tier: 'paid' },
      emptyRunState(),
      'r'
    );
    expect(event.dispatchProvider).toBe('anthropic');
  });

  it('omits dispatchProvider when model_tier is not set', () => {
    const event = buildReactionEvent({ id: 's', task_template: 'x' }, emptyRunState(), 'r');
    expect(event.dispatchProvider).toBeUndefined();
  });

  it('NEVER interpolates operation_command (security invariant)', () => {
    const state: ReactionChainState = {
      schema_version: 'scbe_reaction_chain_state_v1',
      chain_id: 'test',
      run_id: 'run-abc',
      started_at: new Date().toISOString(),
      status: 'running',
      steps: { prior: { id: 'prior', status: 'done', result: 'injected-value' } },
    };
    const event = buildReactionEvent(
      {
        id: 'step1',
        task_template: 'Use ${step.prior.result}',
        operation_command: 'node ${step.prior.result}',
      },
      state,
      'run-abc'
    );
    // task IS interpolated (NL context)
    expect(event.task).toBe('Use injected-value');
    // operationCommand is NEVER interpolated
    expect(event.operationCommand).toBe('node ${step.prior.result}');
  });
});

// ─── runReactionChain ─────────────────────────────────────────────────────────

describe('runReactionChain', () => {
  it('runs a linear chain to completion', async () => {
    const result = await runReactionChain(linearChain(), { runEvent: mockRunner() });
    expect(result.ok).toBe(true);
    expect(result.state.status).toBe('complete');
    expect(result.steps_completed).toBe(2);
    expect(result.steps_blocked).toBe(0);
  });

  it('returns correct schema_version', async () => {
    const result = await runReactionChain(linearChain(), { runEvent: mockRunner() });
    expect(result.schema_version).toBe('scbe_reaction_chain_run_v1');
  });

  it('stops when first step fails and marks chain blocked', async () => {
    const result = await runReactionChain(linearChain(), { runEvent: mockRunner(false) });
    expect(result.ok).toBe(false);
    expect(result.state.status).toBe('blocked');
    expect(result.steps_completed).toBe(0);
    expect(result.steps_blocked).toBe(1);
  });

  it('runs parallel reactions then the join step', async () => {
    const fired: string[] = [];
    const runner = async (event: import('../src/index.js').AgentBusEvent) => {
      fired.push(event.seriesId ?? '');
      return { ok: true, result: null };
    };
    const result = await runReactionChain(parallelChain(), { runEvent: runner });
    expect(result.ok).toBe(true);
    expect(result.steps_completed).toBe(3);
    // A and B fire before C
    const cIdx = fired.findIndex((s) => s.endsWith('-C'));
    const aIdx = fired.findIndex((s) => s.endsWith('-A'));
    const bIdx = fired.findIndex((s) => s.endsWith('-B'));
    expect(cIdx).toBeGreaterThan(aIdx);
    expect(cIdx).toBeGreaterThan(bIdx);
  });

  it('completes an empty chain immediately', async () => {
    const empty: ReactionChain = {
      schema_version: 'scbe_reaction_chain_v1',
      chain_id: 'empty',
      reactions: [],
    };
    const result = await runReactionChain(empty);
    expect(result.ok).toBe(true);
    expect(result.state.status).toBe('complete');
    expect(result.steps_completed).toBe(0);
  });

  it('passes prior step results forward via task_template interpolation', async () => {
    const received: string[] = [];
    const runner = async (event: import('../src/index.js').AgentBusEvent) => {
      received.push(event.task);
      return { ok: true, result: 'step-output' };
    };
    const chain: ReactionChain = {
      schema_version: 'scbe_reaction_chain_v1',
      chain_id: 'passthrough',
      reactions: [
        { id: 'fetch', task_template: 'Fetch the data' },
        { id: 'process', task_template: 'Process: ${step.fetch.result}', depends_on: ['fetch'] },
      ],
    };
    await runReactionChain(chain, { runEvent: runner });
    expect(received[1]).toBe('Process: step-output');
  });

  it('marks the run_id consistently between state and result', async () => {
    const result = await runReactionChain(linearChain(), { runEvent: mockRunner() });
    expect(result.run_id).toBe(result.state.run_id);
  });

  it('carries the chain_id into the result', async () => {
    const result = await runReactionChain(linearChain(), { runEvent: mockRunner() });
    expect(result.chain_id).toBe('linear');
  });
});
