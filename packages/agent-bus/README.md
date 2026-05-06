# scbe-agent-bus

Typed Node surface over the SCBE governed event runner.

This package routes AI, human, and automation events through the existing
`scripts/system/agentbus_pipe.mjs` runner and returns typed result envelopes for
Node callers.

## Install

```bash
npm i scbe-agent-bus
```

## Usage

```ts
import { runEvent } from 'scbe-agent-bus';

const result = await runEvent({
  task: 'Summarize the changed training files.',
  taskType: 'review',
  privacy: 'local_only',
});

console.log(result.ok, result.result);
```

## Notes

- The repo-local runner remains the source of truth.
- `privacy: "local_only"` should be used for sensitive data.
- Remote dispatch should be explicit with budget and provider fields.
