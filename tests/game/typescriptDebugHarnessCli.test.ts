import { describe, expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';

describe('TypeScript debug harness CLI', () => {
  it('runs a scenario as a subprocess and returns a JSON receipt', () => {
    const scenario = {
      id: 'cli-heal-turn',
      source: `
        function evaluate(input: { heal: number }, state: { hp: number }) {
          state.hp += input.heal;
          return state.hp;
        }
      `,
      input: { heal: 3 },
      initialState: { hp: 7 },
    };

    const result = spawnSync(
      process.execPath,
      ['scripts/run_typescript_debug_scenario.cjs', '--json', JSON.stringify(scenario)],
      {
        cwd: process.cwd(),
        encoding: 'utf8',
        timeout: 5000,
      }
    );

    expect(result.status).toBe(0);
    const receipt = JSON.parse(result.stdout);
    expect(receipt.status).toBe('passed');
    expect(receipt.result).toBe(10);
    expect(receipt.stateChanges).toContainEqual({
      path: 'state.hp',
      before: 7,
      after: 10,
    });
  });

  it('exits non-zero for invalid scenario JSON', () => {
    const result = spawnSync(
      process.execPath,
      ['scripts/run_typescript_debug_scenario.cjs', '--json', '{bad'],
      {
        cwd: process.cwd(),
        encoding: 'utf8',
        timeout: 5000,
      }
    );

    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain('SyntaxError');
  });
});
