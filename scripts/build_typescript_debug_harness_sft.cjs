#!/usr/bin/env node
/* Build SFT records from deterministic TypeScript game-debug receipts. */

const fs = require('node:fs');
const path = require('node:path');

require('ts-node/register/transpile-only');

const {
  runTypeScriptDebugScenario,
  receiptToSftPair,
} = require('../src/game/typescriptDebugHarness.ts');

const outputArg = process.argv.includes('--output')
  ? process.argv[process.argv.indexOf('--output') + 1]
  : 'training-data/sft/typescript_debug_harness_v1.sft.jsonl';
const manifestArg = process.argv.includes('--manifest')
  ? process.argv[process.argv.indexOf('--manifest') + 1]
  : 'training-data/sft/typescript_debug_harness_v1_manifest.json';

const scenarios = [
  {
    id: 'approve_valid_heal_turn',
    concept: 'valid TypeScript action mutates game state and returns a receipt',
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
  },
  {
    id: 'retry_runtime_error_turn',
    concept: 'runtime error produces a retry receipt, not silent approval',
    source: `
      function evaluate() {
        throw new Error("bad move");
      }
    `,
    input: {},
    initialState: { hp: 1 },
  },
  {
    id: 'retry_timeout_turn',
    concept: 'infinite loop produces a timeout receipt with state preserved',
    source: `
      function evaluate() {
        while (true) {}
      }
    `,
    input: {},
    initialState: { ticks: 0 },
    timeoutMs: 25,
  },
];

const system =
  'You are an SCBE coding evaluator. Treat a TypeScript game-debug receipt as execution evidence. Approve only passing code; retry runtime errors, timeouts, and compile failures.';

const records = scenarios.map((scenario) => {
  const receipt = runTypeScriptDebugScenario(scenario);
  const pair = receiptToSftPair(receipt);
  return {
    messages: [
      { role: 'system', content: system },
      {
        role: 'user',
        content: [
          `Scenario: ${scenario.id}`,
          `Concept: ${scenario.concept}`,
          'TypeScript candidate:',
          scenario.source.trim(),
          'Receipt:',
          JSON.stringify(receipt, null, 2),
          pair.instruction,
        ].join('\n'),
      },
      { role: 'assistant', content: pair.response },
    ],
    meta: {
      source: 'typescript_debug_harness_v1',
      scenario_id: scenario.id,
      status: receipt.status,
      surfaces: ['typescript', 'runtime_receipt', 'state_diff', 'sft_decision'],
    },
  };
});

const generationRecords = [
  {
    id: 'write_score_add_mutating_evaluate',
    prompt:
      'Write TypeScript only. Define function evaluate(input, state). It must add input.points to state.score, mutate state.score, and return the new score.',
    response:
      'function evaluate(input: { points: number }, state: { score: number }): number {\n' +
      '  state.score += input.points;\n' +
      '  return state.score;\n' +
      '}',
  },
  {
    id: 'write_heal_clamp_mutating_evaluate',
    prompt:
      "Write TypeScript only. Define function evaluate(input, state). It must increase state.hp by input.heal, cap hp at state.maxHp, push 'healed' into state.events, and return state.hp.",
    response:
      'function evaluate(input: { heal: number }, state: { hp: number; maxHp: number; events: string[] }): number {\n' +
      '  state.hp += input.heal;\n' +
      '  if (state.hp > state.maxHp) state.hp = state.maxHp;\n' +
      "  state.events.push('healed');\n" +
      '  return state.hp;\n' +
      '}',
  },
  {
    id: 'write_inventory_unique_mutating_evaluate',
    prompt:
      'Write TypeScript only. Define function evaluate(input, state). If input.item is not already in state.inventory, append it. Return the inventory length.',
    response:
      'function evaluate(input: { item: string }, state: { inventory: string[] }): number {\n' +
      '  if (!state.inventory.includes(input.item)) {\n' +
      '    state.inventory.push(input.item);\n' +
      '  }\n' +
      '  return state.inventory.length;\n' +
      '}',
  },
  {
    id: 'write_cooldown_gate_mutating_evaluate',
    prompt:
      'Write TypeScript only. Define function evaluate(input, state). If state.cooldown is greater than 0, decrement state.cooldown by 1 and return false. Otherwise set state.cooldown to input.cooldown, increment state.actions by 1, and return true.',
    response:
      'function evaluate(input: { cooldown: number }, state: { cooldown: number; actions: number }): boolean {\n' +
      '  if (state.cooldown > 0) {\n' +
      '    state.cooldown -= 1;\n' +
      '    return false;\n' +
      '  }\n' +
      '  state.cooldown = input.cooldown;\n' +
      '  state.actions += 1;\n' +
      '  return true;\n' +
      '}',
  },
  {
    id: 'write_quest_flags_reward_evaluate',
    prompt:
      'Write TypeScript only. Define function evaluate(input, state). If every string in input.required is present in state.flags, add input.reward to state.rewards if it is not already present, then return true. If any required flag is missing, do not change state.rewards and return false.',
    response:
      'function evaluate(input: { required: string[]; reward: string }, state: { flags: string[]; rewards: string[] }): boolean {\n' +
      '  const hasRequirements = input.required.every((flag) => state.flags.includes(flag));\n' +
      '  if (!hasRequirements) return false;\n' +
      '  if (!state.rewards.includes(input.reward)) {\n' +
      '    state.rewards.push(input.reward);\n' +
      '  }\n' +
      '  return true;\n' +
      '}',
  },
  {
    id: 'write_weighted_choice_evaluate',
    prompt:
      'Write TypeScript only. Define function evaluate(input, state). input.options is an array of objects with id and weight. Return the id of the first option where the cumulative weight is greater than input.roll. If no option crosses the roll, return the final option id. Do not mutate state.',
    response:
      'function evaluate(input: { options: Array<{ id: string; weight: number }>; roll: number }, state: unknown): string | null {\n' +
      '  let total = 0;\n' +
      '  for (const option of input.options) {\n' +
      '    total += option.weight;\n' +
      '    if (input.roll < total) return option.id;\n' +
      '  }\n' +
      '  return input.options.length ? input.options[input.options.length - 1].id : null;\n' +
      '}',
  },
].map((item) => ({
  messages: [
    {
      role: 'system',
      content:
        'You are an SCBE coding agent. Return only TypeScript code. For game-debug tasks, mutate the provided state when the prompt says state changes are required.',
    },
    { role: 'user', content: item.prompt },
    { role: 'assistant', content: item.response },
  ],
  meta: {
    source: 'typescript_debug_harness_v1',
    scenario_id: item.id,
    status: 'generation_gold',
    surfaces: ['typescript', 'state_mutation', 'runtime_receipt_target'],
  },
}));

records.push(...generationRecords);

const repairRecords = [
  {
    id: 'repair_inventory_must_mutate_not_predict_length',
    prompt:
      'Repair this TypeScript evaluate function. The function returns the right length but fails because it does not mutate state.inventory. Return only corrected TypeScript.\n\n' +
      'function evaluate(input: { item: string }, state: { inventory: string[] }): number {\n' +
      '  return state.inventory.length + (input.item ? 1 : 0);\n' +
      '}',
    response:
      'function evaluate(input: { item: string }, state: { inventory: string[] }): number {\n' +
      '  if (!state.inventory.includes(input.item)) {\n' +
      '    state.inventory.push(input.item);\n' +
      '  }\n' +
      '  return state.inventory.length;\n' +
      '}',
  },
  {
    id: 'repair_quest_required_not_input_flags',
    prompt:
      'Repair this TypeScript evaluate function. The input has required and reward fields, not input.flags. It must require every input.required flag, add input.reward to state.rewards only when missing, and preserve rewards when requirements fail. Return only corrected TypeScript.\n\n' +
      'function evaluate(input: { required: string[], flags: string[] }, state: { flags: string[], rewards: number[] }): boolean {\n' +
      '  for (const flag of input.required) {\n' +
      '    if (!state.flags.includes(flag)) {\n' +
      '      return false;\n' +
      '    }\n' +
      '  }\n' +
      '  for (const flag of input.flags) {\n' +
      '    if (!state.flags.includes(flag)) {\n' +
      '      return false;\n' +
      '    }\n' +
      '  }\n' +
      '  return true;\n' +
      '}',
    response:
      'function evaluate(input: { required: string[]; reward: string }, state: { flags: string[]; rewards: string[] }): boolean {\n' +
      '  const hasRequirements = input.required.every((flag) => state.flags.includes(flag));\n' +
      '  if (!hasRequirements) return false;\n' +
      '  if (!state.rewards.includes(input.reward)) {\n' +
      '    state.rewards.push(input.reward);\n' +
      '  }\n' +
      '  return true;\n' +
      '}',
  },
  {
    id: 'repair_weighted_choice_uses_input_roll_not_state_roll',
    prompt:
      'Repair this TypeScript evaluate function. The roll is input.roll, not state.roll. It must return the first option id whose cumulative weight is greater than input.roll and must not mutate state. Return only corrected TypeScript.\n\n' +
      'function evaluate(input: { options: { id: string; weight: number }[] }, state: { roll: number }): string {\n' +
      '  let totalWeight = 0;\n' +
      '  for (const option of input.options) {\n' +
      '    const { id, weight } = option;\n' +
      '    totalWeight += weight;\n' +
      '    if (totalWeight > state.roll) {\n' +
      '      return id;\n' +
      '    }\n' +
      '  }\n' +
      '  return input.options[input.options.length - 1].id;\n' +
      '}',
    response:
      'function evaluate(input: { options: Array<{ id: string; weight: number }>; roll: number }, state: unknown): string | null {\n' +
      '  let total = 0;\n' +
      '  for (const option of input.options) {\n' +
      '    total += option.weight;\n' +
      '    if (input.roll < total) return option.id;\n' +
      '  }\n' +
      '  return input.options.length ? input.options[input.options.length - 1].id : null;\n' +
      '}',
  },
].map((item) => ({
  messages: [
    {
      role: 'system',
      content:
        'You are an SCBE coding repair agent. Use executable receipt evidence to fix the function. Return only TypeScript code.',
    },
    { role: 'user', content: item.prompt },
    { role: 'assistant', content: item.response },
  ],
  meta: {
    source: 'typescript_debug_harness_v1',
    scenario_id: item.id,
    status: 'repair_gold',
    surfaces: ['typescript', 'state_mutation', 'runtime_receipt_target', 'repair_from_failure'],
  },
}));

records.push(...repairRecords);

fs.mkdirSync(path.dirname(outputArg), { recursive: true });
fs.writeFileSync(outputArg, records.map((record) => JSON.stringify(record)).join('\n') + '\n');
fs.writeFileSync(
  manifestArg,
  JSON.stringify(
    {
      schema_version: 'typescript_debug_harness_v1',
      record_count: records.length,
      output: outputArg,
      statuses: Array.from(new Set(records.map((record) => record.meta.status))).sort(),
    },
    null,
    2
  )
);

console.log(JSON.stringify({ output: outputArg, manifest: manifestArg, records: records.length }, null, 2));
