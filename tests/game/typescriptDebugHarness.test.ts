import { describe, expect, it } from 'vitest';
import {
  receiptToSftPair,
  runTypeScriptDebugScenario,
} from '../../src/game/typescriptDebugHarness.js';

describe('TypeScript game debug harness', () => {
  it('runs a valid snippet and reports state changes', () => {
    const receipt = runTypeScriptDebugScenario({
      id: 'heal-turn',
      source: `
        export function evaluate(input: { heal: number }, state: { hp: number; events: string[] }) {
          state.hp += input.heal;
          state.events.push("healed");
          console.log("heal", input.heal);
          return state.hp;
        }
      `,
      input: { heal: 4 },
      initialState: { hp: 6, events: [] },
    });

    expect(receipt.status).toBe('passed');
    expect(receipt.result).toBe(10);
    expect(receipt.logs).toEqual(['heal 4']);
    expect(receipt.stateChanges).toContainEqual({ path: 'state.hp', before: 6, after: 10 });
    expect(receipt.stateChanges).toContainEqual({ path: 'state.events.0', before: undefined, after: 'healed' });
  });

  it('captures runtime errors as retry receipts', () => {
    const receipt = runTypeScriptDebugScenario({
      id: 'broken-turn',
      source: `
        function evaluate() {
          throw new Error("bad move");
        }
      `,
      input: {},
      initialState: { hp: 1 },
    });

    expect(receipt.status).toBe('runtime_error');
    expect(receipt.error).toContain('bad move');
    expect(receipt.stateChanges).toEqual([]);
  });

  it('times out looping snippets without losing the receipt shape', () => {
    const receipt = runTypeScriptDebugScenario({
      id: 'loop-turn',
      source: `
        function evaluate() {
          while (true) {}
        }
      `,
      input: {},
      initialState: { ticks: 0 },
      timeoutMs: 25,
    });

    expect(receipt.status).toBe('timeout');
    expect(receipt.error).toContain('timed out');
  });

  it('turns receipts into SFT pairs', () => {
    const receipt = runTypeScriptDebugScenario({
      id: 'score-turn',
      source: `
        function evaluate(input: { points: number }, state: { score: number }) {
          state.score += input.points;
          return state.score;
        }
      `,
      input: { points: 2 },
      initialState: { score: 3 },
    });

    const pair = receiptToSftPair(receipt);

    expect(pair.instruction).toContain('score-turn');
    expect(pair.response).toContain('"decision": "approve"');
    expect(pair.response).toContain('state.score');
  });
});
