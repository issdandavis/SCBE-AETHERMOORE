# Rubix Browser Adapter

The Rubix browser adapter is an AI-native browser-control planning lane. It does not
replace Playwright or a normal browser yet. It wraps browser work in a permission-defined
cube/tesseract map so an agent can prove which faces of the browser it needs before any
side effect happens.

## Model

The adapter treats browser control as a set of faces:

| Face       | Axis      | Permission     | Purpose                             |
| ---------- | --------- | -------------- | ----------------------------------- |
| `viewport` | visual    | `visual.read`  | pixels, screenshots, visible text   |
| `dom`      | structure | `dom.read`     | elements, labels, forms, attributes |
| `network`  | transport | `network.read` | requests, responses, navigation     |
| `storage`  | state     | `storage.read` | cookies, local storage, cache       |
| `auth`     | identity  | `auth.read`    | login/session/account boundary      |
| `tool`     | execution | `tool.call`    | clicks, typing, upload/download     |
| `memory`   | memory    | `observe`      | deferred work, receipts, loop state |

Each face has a four-dimensional coordinate. A task becomes a route through those faces.
The route is allowed only when the required permissions are present. Missing permissions
do not crash the plan; they produce `HOLD` with blocked-move evidence.

## CLI

```powershell
node packages/agent-bus/bin/scbe-agent-bus.cjs rubix-browser plan `
  --task "inspect the pricing page and summarize visible labels" `
  --permissions observe,visual.read,dom.read `
  --json
```

Side-effectful tasks hold unless the execution face is explicitly opened:

```powershell
node packages/agent-bus/bin/scbe-agent-bus.cjs rubix-browser plan `
  --task "open the upload page, fill the form, and submit the video" `
  --permissions observe,visual.read,dom.read `
  --json
```

Run the CI-safe headless preflight benchmark:

```powershell
node packages/agent-bus/bin/scbe-agent-bus.cjs rubix-browser bench --headless --json
```

Use headed mode only for replay/debug labels over the same deterministic cases:

```powershell
node packages/agent-bus/bin/scbe-agent-bus.cjs rubix-browser bench --headed --json
```

## Bus Tool

`packages/agent-bus/tools.json` registers:

```json
{
  "name": "rubix-browser-plan",
  "description": "Plan a browser-control route as permission-defined Rubix/tesseract faces with blocked-move audit evidence"
}
```

and:

```json
{
  "name": "rubix-browser-bench",
  "description": "Run the headless Rubix browser permission-geometry benchmark for CI-safe browser-control preflight"
}
```

Any agent bus event can route to that tool before live browser execution.

## Next Benchmark Step

The next lane is a Playwright-backed benchmark adapter:

1. Convert a task into a Rubix browser plan.
2. Execute only `PASS` moves in Playwright.
3. Write screenshots, DOM snapshots, and route receipts.
4. Score browser-control pathfinding by completion, blocked moves, retries, and route hash.

This keeps the claim narrow: SCBE can prove browser-control permission geometry before
execution, then measure whether that geometry improves live browser automation.
