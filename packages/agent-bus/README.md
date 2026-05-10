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

## Backend

```bash
scbe-agent-bus serve --port 8787
```

Routes:

- `GET /health`
- `POST /v1/events`
- `POST /v1/batch`

## Frontend

```bash
scbe-agent-bus ui --base-url http://127.0.0.1:8787
```

The terminal frontend can health-check the backend and send governed local-only
tasks through the bus. It does not expose shell execution.

## Notes

- The repo-local runner remains the source of truth.
- `privacy: "local_only"` should be used for sensitive data.
- Remote dispatch should be explicit with budget and provider fields.
