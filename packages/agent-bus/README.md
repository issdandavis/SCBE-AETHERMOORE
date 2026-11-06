# scbe-agent-bus

> Run AI actions through a policy gate that checks them **before** they execute, and get a signed receipt for every one.

[![npm](https://img.shields.io/npm/v/scbe-agent-bus.svg)](https://www.npmjs.com/package/scbe-agent-bus)
[![node](https://img.shields.io/node/v/scbe-agent-bus.svg)](https://nodejs.org)
[![license](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)
[![types](https://img.shields.io/npm/types/scbe-agent-bus.svg)](https://www.typescriptlang.org/)

## What it does

- **Gates actions.** An LLM proposes; this decides whether the move is legal before anything runs.
- **Records receipts.** Every decision appends to a hash-chained audit log you can verify offline.
- **Stays local.** Works with free, local, or bring-your-own-key models. Nothing leaves the machine unless you send it.

Use it when an agent can touch something that matters — files, money, deployments — and "the model said so" is not an acceptable audit trail.

## Requirements

- **Node.js >= 18**
- Event intake and workspace receipts need no Python or Docker.
- Plan execution requires a trusted GeoSeal compiler, evaluator and isolated
  executor. See [secure host setup](SECURE_EXECUTION.md). An unconfigured
  `pipeline run` blocks; it never falls back to running the plan on the host.

## Install

```bash
npm i scbe-agent-bus
```

## Quick start

```ts
import { runEvent } from 'scbe-agent-bus';

const result = await runEvent({
  task: 'Summarize the changed training files.',
  taskType: 'review',
  privacy: 'local_only',
});

console.log(result.ok, result.result);
```

Expected output:

```
true {
  status: 'accepted',
  mode: 'local_receipt',
  receipt_id: 'evt_...'
}
```

The package-native default validates and records the event without pretending a
model or command ran. To execute work, set `event.tool` to a registered governed
CLI tool or pass the event into a connected conversational runtime.

`result.ok === false` means the gate **refused** the action. That is a normal outcome, not an error — read `result.reason` for which rule fired. Raw `operationCommand` values are refused unless represented by a registered tool.

## Security

This package binds local HTTP listeners. All of them default to **loopback only**:

| service           | default bind     | purpose                                 |
| ----------------- | ---------------- | --------------------------------------- |
| agent bus backend | `127.0.0.1:8787` | HTTP surface for the event runner       |
| governed task API | `127.0.0.1:8766` | client connection to the local task lab |

- **Nothing binds `0.0.0.0`.** The host is overridable programmatically via `options.host`; there is no CLI flag that exposes it, so you cannot widen the bind by accident from a shell.
- **The task client is not a shell.** It speaks a validated lifecycle protocol and rejects evidence-free output that claims to be reviewable or factual.
- **Audit log is append-only and hash-chained** — tampering breaks the chain and `verify` fails.

If you deliberately expose the backend beyond loopback, put an authenticating reverse proxy in front of it. It has no built-in authentication.

## Command reference

| command                           | does                                                      | example                                                                                         |
| --------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `scbe-agent-bus serve`            | start the local backend                                   | `scbe-agent-bus serve --port 8787`                                                              |
| `scbe-agent-bus send`             | one-shot dispatch, no server                              | `scbe-agent-bus send "review this diff"`                                                        |
| `scbe-agent-bus ui`               | terminal UI over the backend                              | `scbe-agent-bus ui`                                                                             |
| `scbe-agent-bus workspace export` | export a workspace + audit chain                          | `scbe-agent-bus workspace export ./out`                                                         |
| `scbe-agent-bus workspace verify` | verify a chain offline                                    | `scbe-agent-bus workspace verify ./out`                                                         |
| `scbe-agent-bus pipeline compile` | compile an auditable GeoSeal plan                         | `scbe-agent-bus pipeline compile --intent "run tests" --permission-mode workspace-write --json` |
| `scbe-agent-bus pipeline run`     | compile and gate; blocks without a trusted execution host | `scbe-agent-bus pipeline run --intent "inspect status" --permission-mode observe --json`        |

Pipeline permission modes are `observe`, `workspace-write`, `cloud-dispatch`,
and `maintenance`. A policy denial is returned as a structured plan with its
reason and hashes even though the CLI exits nonzero.

## TypeScript API

| export                 | signature                                      | returns                                    |
| ---------------------- | ---------------------------------------------- | ------------------------------------------ |
| `runEvent`             | `(opts: EventOptions) => Promise<EventResult>` | typed envelope, `ok` + `result` + `reason` |
| `TaskApiClient`        | `new TaskApiClient({ baseUrl })`               | governed task lab client                   |
| `TASK_API_DEFAULT_URL` | `string`                                       | `http://127.0.0.1:8766`                    |

```ts
import { TaskApiClient } from 'scbe-agent-bus';

const tasks = new TaskApiClient({ baseUrl: 'http://127.0.0.1:8766' });
const queued = await tasks.createRun({
  objective: 'Check this claim against the supplied evidence.',
  processor: 'core',
  evidence: [],
});
```

## For AI agents

If you are an agent reading this to decide how to call the package:

1. **Entry point is `runEvent`.** One call, one envelope back. You do not need the server for this.
2. **Check `result.ok` before using `result.result`.** `ok: false` is a refusal with a `reason`, not a crash.
3. **`privacy: 'local_only'`** keeps the payload on the machine. Use it unless the caller explicitly allowed egress.
4. **Every `runEvent` call produces a receipt id.** Cite it when you report what you did.
5. **Do not shell out to work around a refusal.** The refusal is the product.

## Troubleshooting

| symptom                         | cause                     | fix                                               |
| ------------------------------- | ------------------------- | ------------------------------------------------- |
| `ECONNREFUSED 127.0.0.1:8766`   | task lab is not running   | start it, or use `runEvent` which needs no server |
| `EADDRINUSE :8787`              | backend already running   | `scbe-agent-bus serve --port 8788`                |
| `ok: false` on every call       | a policy rule is refusing | read `result.reason`; it names the rule           |
| `Unsupported engine` on install | Node < 18                 | upgrade Node                                      |

## License

MIT OR Apache-2.0
