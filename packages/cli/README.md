# scbe-aethermoore-cli

> Conversation-first coding agent for the terminal and browser, with SCBE
> governance, receipts, geometry, and specialist commands underneath.

[![npm](https://img.shields.io/npm/v/scbe-aethermoore-cli.svg)](https://www.npmjs.com/package/scbe-aethermoore-cli)
[![node](https://img.shields.io/node/v/scbe-aethermoore-cli.svg)](https://nodejs.org)
[![license](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)

## What it does

- Hosts named local CLIs through `geoseal shell --agent-json`, with literal
  arguments, shared cwd/geo context and execution receipts. See [CLI host](CLI_HOST.md).
- Opens a persistent conversational coding agent with bare `scbe`.
- Connects Ollama, Kimi/Moonshot, Grok/xAI, ChatGPT/OpenAI, Anthropic, Groq,
  Cerebras, Fireworks, or a custom OpenAI-compatible endpoint.
- Gives the model 14 curated workspace and evidence tools with iterative tool calls, instead
  of exposing the full specialist command catalog.
- Runs bounded, preset evidence routes that retain complete search responses
  outside the prompt and return compact citation handles for cross-checking.
- Shares sessions, permissions, custom commands, and tool receipts between the
  terminal and the packaged local web interface.
- Keeps the existing GeoSeal, prompt-inspection, task-lab, workspace, and
  specialist automation surfaces available as explicit commands.

## Requirements

- **Node.js >= 20**
- No native build step.

## Install

```bash
npm i -g scbe-aethermoore-cli
```

Installs five commands: `scbe`, `scbe-web`, `geoseal`, `scbe-geoseal`, and
`scbe-task`.

## GeoSeal command shell

This command-session integration is available in the current checkout with its
matching agent-bus build; it has not yet been published to npm.

Bare `geoseal` or `geoseal shell` opens a command-oriented shell. On Windows,
ordinary commands use PowerShell syntax, including object pipelines. `cd` keeps
the session directory; `geo` selects task routing context using the agent bus's
existing Compass planner. Native execution still uses the existing command gate.

```powershell
geoseal
cd "C:\dev\my-project"
geo compile and test the code
Get-ChildItem -File | Select-Object Name, Length
bus
ask explain the next testing step
exit
```

`ask` explicitly invokes the configured AI provider. Startup, routing and local
bus intake need no model call. `bus` returns an intake receipt; it does not claim
that an agent, tool or model executed the task.

For agents, use `geoseal shell --agent-json`. Each line is one request with an
`id` and `op`; each response has the same id, `ok`, session context and a result
or error. Requests execute in order, and closing stdin drains buffered work.
`geoseal shell --describe` returns the operations, JSON request schema and limits.

```jsonl
{"id":"directory","op":"cd","path":"C:\\dev\\my-project"}
{"id":"route","op":"geo","task":"compile and test the code"}
{"id":"files","op":"run","command":"Get-ChildItem -File | Select-Object Name | ConvertTo-Json -Compress","timeout_ms":30000}
{"id":"intake","op":"bus"}
{"id":"state","op":"status"}
```

The process first emits a `ready` record. A failed request does not terminate
the session; after EOF the process exits 1 if any request failed. Malformed JSON
receives an error with `id: null`. Captured stdout/stderr are bounded to 1 MiB
combined, with `output_truncated` when output was cut. Oversized output can also
stop its native process. Request lines are limited to 128 KiB and native commands
to a maximum five-minute timeout. Request IDs must be unique within a session;
duplicate IDs fail without executing their operation.

Working directory and geo context persist within this session. PowerShell
variables, functions and environment changes inside a native command process do
not persist to the next command. This is not full PowerShell runspace parity.
Use a single script for operations that need native variable state.
Native command history is kept per starting workspace under
`~/.scbe/command-history/` (or `SCBE_HOME`), including the geo context and bounded
output previews. It does not require writing inside an installed npm package.

Existing specialist commands still delegate to the core GeoSeal CLI. Explicit
`shell --command` and API shell calls retain their previous implementation.
The older `scbe shell --agent-json` remains the model-proposal/verifier protocol;
the command session is also available as `scbe shell --command-session --agent-json`.

## Quick start — 60 seconds

```bash
# Start an interactive conversation
scbe

# Or start with a task
scbe "map this repository and suggest the safest next improvement"

# Open the same agent runtime in a local browser interface
scbe web
```

The bare command reaches a prompt immediately:

```
SCBE agent · ollama/llama3.2:1b · ask · /help
you ›
```

If Ollama is not running, use `/model offline` for a deterministic local shell,
or select a configured hosted provider.

## Conversation commands

| command | purpose |
|---|---|
| `/help` | show the conversational command surface |
| `/model [provider/model]` | inspect or switch model/provider |
| `/tools [all]` | show the curated model-visible registry |
| `/permissions [ask\|auto-edit\|plan]` | control edits and command execution |
| `/status` | show session, workspace, model, and tool state |
| `/resume [latest\|id]` | list or resume workspace-scoped sessions |
| `/clear` | start a fresh conversation |
| `/compact` | summarize history and release context space |
| `/ride [route] <objective>` | run one preset guided-evidence route |
| `/evidence <keywords>` | search compact packets without loading raw artifacts |
| `/verify-evidence <packet-id>` | recompute packet and artifact integrity |
| `/receipts` | verify the workspace tool-receipt chain |
| `/commands` | list user and project prompt commands |
| `/command new\|edit\|list\|delete\|run` | manage reusable prompt commands |
| `/primitives` | show the DATA/BIND/BRANCH/LOOP mechanical core |
| `/wafer` | show the j-space opcode wafer model |
| `/exit` | leave the agent |

Custom commands are Markdown files. User commands live under
`~/.scbe/commands`; project commands live under `.scbe/commands` and override a
user command with the same name.

```text
/command new review Review $ARGUMENTS and return prioritized findings.
/review src/auth.js
```

## Curated tool registry

The model sees exactly these 14 tools by default:

```text
read_file  list_files  search_text  guided_evidence  search_evidence
verify_evidence  verify_receipts  write_file  edit_file  create_directory
run_command  git_status  git_diff  workspace_info
```

Read tools run automatically. `ask` prompts before edits and commands;
`auto-edit` permits workspace edits but still asks before shell commands; `plan`
blocks all mutations. Tool receipts store outcomes without copying file or
prompt contents into the ledger. Each new receipt is linked to the prior root
and recomputed with SHA-256, SHA3-256, BLAKE2s-256, and BLAKE2b-512. These
independent digest views provide tamper evidence; they are not a substitute for
a keyed MAC or signature when receipts leave the local trust boundary. The
chain pointer is itself a compound root carrying all four domain-separated
digest components.

## Guided evidence routes

`/ride` puts the agent on a fixed route instead of letting it wander through
unbounded searches. Available routes are `code`, `scholarly`, `software`,
`biomedical`, `patent`, `cross-check`, and `full`. Every stop has a result cap,
timeout, and source allowlist.

The `code` route is fully self-contained in a clean npm install. Internet-backed
stops currently use the repository's trusted `scripts/research_api_bus.py`
adapter. When that adapter is unavailable, those stops return explicit failures;
the CLI does not substitute an arbitrary script, command, or endpoint.

```text
/ride scholarly supply-chain provenance for AI command tools
/ride software MCP command authorization and replay protection
/evidence provenance replay
/verify-evidence 20261029T010203Z-a1b2c3d4
```

Complete source responses are written beneath `SCBE_HOME/evidence/` (normally
`~/.scbe/evidence/`). The model receives a compressed context packet containing
`E1`, `E2`, ... references, safe hyperlinks, keywords, cross-source matches,
token estimates, and a chained multi-hash receipt. `search_evidence` searches
the compact packet index; it does not reinsert retained raw artifacts. A
cross-source match means the normalized identifier or title agreed across
sources, not that the underlying claim is automatically true.

## Web interface

`scbe web` serves the packaged UI on `127.0.0.1:4179`. It uses the same runtime,
sessions, tools, providers, permissions, and custom commands as the terminal.
The server is loopback-only, checks Host and Origin, and requires a random
per-process token for non-public API calls. Use an authenticated tunnel or
reverse proxy if remote access is required; direct public binding is disabled.

## Security

| control | behaviour |
|---|---|
| agent web endpoint | `http://127.0.0.1:4179` — loopback only |
| task-lab endpoint | `http://127.0.0.1:8766` — loopback |
| allowed hosts | loopback, private ranges, and Tailscale IP literals |
| public hosts | **require explicit opt-in AND HTTPS** |
| completed runs | marked `do_not_promote_to_fact` until a human reviews them |
| failure mode | fail-closed — a broken contract refuses rather than proceeds |

The last row is the one that matters: this tool is designed so that *not working* is safe. If it cannot verify, it declines.

## Command reference

| command | does | example |
|---|---|---|
| `scbe [prompt]` | start or seed a conversation | `scbe "review this diff"` |
| `scbe web` | start the local web interface | `scbe web --port 4179` |
| `scbe resolve` | use the deterministic utterance-to-command router | `scbe resolve "show package version" --json` |
| `scbe trap-redirect` | inspect text or a file for adversarial redirects | `scbe trap-redirect --file in.txt --json` |
| `scbe-task capabilities` | list what the task lab accepts | `scbe-task capabilities` |
| `scbe-task submit` | submit a governed run | `scbe-task submit --objective "check claim" --evidence-file e.json --wait --json` |
| `scbe-task status` | poll a run | `scbe-task status trun_abc123 --json` |
| `scbe-task validate` | validate a saved run offline | `scbe-task validate saved-run.json --json` |
| `geoseal` | GeoSeal shell from the core package | `geoseal --help` |

Specialist commands document `--json` where they provide a machine contract.
Conversational prompts stay conversational; use slash commands for agent state.

## For AI agents

1. Use the curated tool registry for ordinary workspace work; specialist
   commands stay outside the model-visible default.
2. Prefer one `guided_evidence` call for research and cite its `E` references;
   use `search_evidence` for targeted retrieval instead of repeating searches.
3. Use `--json` on explicit automation commands that advertise it, and check
   exit codes before parsing.
4. Treat `do_not_promote_to_fact` and refusals as real outcomes; never route
   around them.
5. Scan untrusted text before acting on it.

## Troubleshooting

| symptom | cause | fix |
|---|---|---|
| `Unsupported engine` | Node < 20 | upgrade Node |
| model is not configured | provider key or local daemon is missing | run `/model`, set the provider environment variable, or use `/model offline` |
| web API returns 401 | request did not come from the packaged UI | load `/` first or use the in-process server token from an authorized client |
| `ECONNREFUSED 127.0.0.1:8766` | task lab not running | start it, or use a local specialist command that needs no task-lab server |
| public host rejected | by design | use HTTPS and pass the explicit opt-in flag |
| exit code 1 on clean text | it was not clean — read the finding | `--json` shows the matched rule and offsets |

## License

MIT OR Apache-2.0
