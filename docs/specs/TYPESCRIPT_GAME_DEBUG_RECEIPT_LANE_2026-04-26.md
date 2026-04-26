# TypeScript Game Debug Receipt Lane

## Purpose

This lane evaluates model-proposed TypeScript as a bounded game turn. It records what happened instead of trusting the proposal text.

The receipt becomes training and evaluation evidence:

- compile or runtime status;
- returned result;
- logs;
- final state;
- exact state diffs;
- timeout or error message.

## Command

```powershell
npm run game:debug-ts -- --json '{"id":"score","source":"function evaluate(input, state) { state.score += input.points; return state.score; }","input":{"points":5},"initialState":{"score":8}}'
```

Expected receipt:

```json
{
  "scenarioId": "score",
  "status": "passed",
  "result": 13,
  "stateChanges": [
    {
      "path": "state.score",
      "before": 8,
      "after": 13
    }
  ]
}
```

## Scenario Contract

The submitted TypeScript must define:

```typescript
function evaluate(input, state) {
  // mutate state or return a value
}
```

`export function evaluate(...)` is also accepted.

## Status Meanings

- `passed`: the snippet compiled, ran, and returned a receipt.
- `runtime_error`: the snippet threw during execution.
- `timeout`: the snippet exceeded the VM turn budget.
- `compile_error`: TypeScript reported a compile diagnostic before execution.

## Training Use

The SFT builder converts receipts into approve/retry examples:

```powershell
node scripts\build_typescript_debug_harness_sft.cjs
```

Output:

- `training-data/sft/typescript_debug_harness_v1.sft.jsonl`
- `training-data/sft/typescript_debug_harness_v1_manifest.json`

This is now part of the future coding approval metrics lane in Kaggle and the future HF v7 file list.

## Boundary

This is deterministic execution evidence, not a hostile-code security sandbox. It runs in a Node VM with a timeout and can also be launched as a subprocess, but untrusted large-scale model code should eventually run inside a locked container or OS-level sandbox with CPU, memory, file, and network limits.
