# GeoSeal command shell — implementation map

The installed user shim currently starts `python -m src.geoseal_cli` after
changing directory to the repository. The packaged GeoSeal entry point delegates
to the core wrapper. `scbe shell --agent-json` is a model proposal/verifier
protocol, and its busy guard drops buffered input. It is not a command execution
session. The conversational agent and its existing tool permissions are separate.

## Bounded change

Provide a command execution session shared by a human terminal and NDJSON agents:
`describe`, `status`, `cd`, `geo`, `run`, and `bus`. Every JSON request gets one
correlated response in arrival order, including invalid requests. EOF drains
accepted work. Working directory and explicit geometric task context persist.
Native PowerShell syntax and pipelines execute through the existing command gate;
PowerShell variables/functions do not persist between native command processes.

| Existing component | Reuse and connection |
|---|---|
| `packages/agent-bus/src/hermes.ts` | Compass route, domain, tier, formation and context plan for a task; routing metadata, not an authorization grant. |
| `packages/agent-bus/src/index.ts:runEvent` | Existing event intake/registered tool execution and receipt identity. |
| `packages/cli/bin/scbe.js:runShellCommand` | Existing gate, native PowerShell execution, bounded capture and history. |
| `packages/cli/bin/geoseal.js` | Command shell front door; legacy specialist commands retain core delegation. |
| New bus command-session module | Typed requests, per-session cwd/geo state, FIFO ordering, predictable errors. |
| New CLI command-shell module | Terminal/NDJSON adapter over the shared session API. No provider call on startup. |

Input is a bounded request object with id, operation and operation-specific fields.
Output includes matching id, success/error, session identity/cwd/geo context and
operation result. Geo routing never changes permission or bypasses a gate.
Native output is bounded and truncation is explicit. Unknown fields/operations
fail before execution. Directory changes are resolved literally.

Validation: delayed executor FIFO/EOF cases, malformed and oversized input,
literal paths with spaces, failed cd preserving state, geo context carried into
actual execution, gate refusals and nonzero exits, real PowerShell pipelines,
legacy CLI compatibility, and clean packaged-module loading. Tests use disposable
local fixtures and offline bus intake; no actual agent/provider messages.

Budget: existing Node/TypeScript tools, CPU tests with file concurrency one;
small source/fixture outputs, no dependency install or model load. Clay continues
in its existing process. Preserve pending work before edits under
`artifacts/geoseal_agent_shell_20260905/before`. Rollback restores those exact
files, plus the saved user shim; no generated package publication is authorized
or needed. Missing runtime/invalid request/gate refusal returns an error.

## Delivered — 2026-09-05

Implemented the shared bus `CommandSession`, terminal/NDJSON adapter, packaged
GeoSeal entry routing, native output/error handling and EOF draining in the
existing model-proposal loop. The user `geoseal.cmd` now invokes the Node entry
without changing directory. Native history lives under the user's SCBE_HOME,
per starting workspace. Existing specialist help delegation still passes.

Validation: 14 bus tests passed; CLI regression run had 72 passed and 3 existing
optional desktop tests skipped. After the final history change, all 12 focused
command-shell tests passed again. TypeScript build, new-file formatting and
syntax checks passed. A separate consumer package layout and the real user
launcher both completed four structured requests and local bus intake.

The consumer check reused installed dependencies via NODE_PATH and current
package builds. It was not a clean registry install or release gate. npm dry-run
packing includes the new CLI and bus modules. Release coordination still needs
the CLI dependency floor/lock aligned with a published bus containing this API;
the existing >=0.4.1 range alone does not guarantee CommandSession availability.

No distributed dispatch, durable session resume or persistent PowerShell
variables are claimed. Geo is the existing Compass task context, not GPS or a
newly validated learned coordinator. See
`artifacts/geoseal_agent_shell_20260905/HANDOFF.md` at the repository root for
source hashes, commands, exact baseline patches and rollback locations.
