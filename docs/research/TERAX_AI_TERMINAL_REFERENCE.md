# Terax AI Terminal Reference Review

Date: 2026-05-10

Source reviewed:

- `https://github.com/crynta/terax-ai`
- `README.md`
- `TERAX.md`
- `package.json`
- `src-tauri/Cargo.toml`

## Executive Read

Terax is a credible reference implementation for the product shape SCBE should
study for **AetherDesk / offline coding-agent UX**.

It is not mainly a model breakthrough. Its strength is product integration:
native terminal sessions, editor, explorer, web preview, and AI tools live in
one small desktop shell. The important lesson is that users buy the operating
surface, not the abstract agent architecture.

## What Terax Is

Terax describes itself as a lightweight AI-native terminal emulator / ADE.
The stack is:

- Tauri 2 desktop shell
- Rust backend
- React 19 + TypeScript frontend
- xterm.js terminal rendering
- CodeMirror 6 editor
- Vercel AI SDK v6 provider layer
- BYOK provider setup
- local model support through OpenAI-compatible endpoints such as LM Studio

Observed public position as of this review:

- Apache-2.0 license
- v0.6.0 latest release, published 2026-05-09
- about 1k GitHub stars and 121 forks
- Windows, macOS, Linux target

## Architecture Pattern Worth Copying

### Two-Process Boundary

Terax keeps OS access in Rust. The webview calls registered Tauri commands.
That is the right model for an agent terminal because it gives a hard boundary:

- frontend coordinates UI state
- backend owns filesystem, process, shell, PTY, secrets, and background jobs
- AI tools cannot directly touch the machine without going through command
  gates

For SCBE, this maps cleanly to:

- Rust/Tauri shell as the local operator surface
- GeoSeal / RuntimeGate as the approval and provenance layer
- Agent Bus as the routing fabric
- Sacred Tongues / Aether-Lattice as the explanation and trace layer

### PTY + One-Shot Shell Split

Terax separates long-lived PTY terminals from one-shot shell commands used by
AI tools. That is important. Interactive user terminals and agent tool calls
should not be the same execution context.

SCBE should keep the same split:

- `user_terminal`: interactive, visible, user-controlled
- `agent_command`: bounded one-shot, policy checked, logged
- `agent_session`: persistent but isolated work session
- `background_task`: long-running dev server with bounded logs

### Approval-Gated Tools

Terax makes read/search auto-executable and write/delete/run-command
approval-gated. That is a practical default for a desktop AI terminal.

SCBE should refine this with risk tiers:

- `ALLOW`: read-only, list, grep, local status
- `CONFIRM`: writes, patch apply, command execution
- `QUARANTINE`: secrets-adjacent paths, broad deletes, network exfil patterns
- `DENY`: credential reads, destructive root actions, hidden persistence

### Project Memory File

Terax uses `TERAX.md` as project memory, similar to `AGENTS.md` / `CLAUDE.md`.
SCBE already has richer memory conventions, but the product should make this
visible and editable. A user should see what the coding agent thinks the
workspace rules are.

## Where Terax Is Ahead Of Us

| Area | Terax advantage | SCBE action |
| --- | --- | --- |
| Desktop UX | Integrated terminal/editor/explorer/preview | Build AetherDesk around existing Agent Bus, not a web-only chat |
| Local model UX | LM Studio/OpenAI-compatible endpoint is first-class | Add visible provider status and local-model readiness checks |
| Secret storage | OS keychain for API keys | Use keychain or local encrypted vault, never flat config for app users |
| Terminal lifecycle | PTY management, shell integration, background streaming | Port the concept into our agent bus runner |
| User trust | No telemetry, BYOK, Apache-2.0 | Match this positioning; SCBE adds governance traceability |

## Where SCBE Can Beat Terax

Terax appears strongest as a terminal-native agent app. SCBE can differentiate
by being a **governed coding-agent operating system**, not only an AI terminal.

SCBE advantages to productize:

- GeoSeal receipts for every proposed patch and command
- Agent Bus task routing across local tools, web, GitHub, Hugging Face, and
  deployment surfaces
- Aether-Lattice / pocket execution model for isolating agent failures
- training-capture loop from real agent work into SFT data
- CLI benchmark and public-evidence benchmark packet already wired
- commercial fulfillment and lead capture already deployed

## Product Implication

Do not try to clone Terax wholesale.

The right SCBE move is a thin **AetherDesk Operator Shell**:

1. Terminal pane
2. File explorer
3. Diff/patch pane
4. Agent Bus task pane
5. GeoSeal receipt panel
6. Local model/provider status panel

The first sellable version does not need full editor parity with Terax. It
needs reliable task routing, visible receipts, and one-click benchmark/test
execution.

## Benchmark Implication

Terax raises the bar for user experience. SCBE currently scores high on local
control-plane benchmarks, but the offline coding-agent functional benchmark is
blocked by harness failure. Before claiming product readiness against this
class of tool, SCBE needs:

- fixed `functional_coding_agent_benchmark.py` harness
- green baseline task execution
- one local model route that passes at least the simple repair tasks
- a screenshot/video of AetherDesk-style task flow

## Recommended Next Build Slice

Build `AetherDesk v0` as a repo-native desktop/operator surface, not a new
model:

- reuse existing `docs/agents.html` / Agent Bus recipe semantics
- expose a terminal-task runner backed by GeoSeal receipts
- add local-provider status for Ollama / LM Studio / HF Router
- show patch proposals as diffs before write
- run `npm run benchmark:cli`, `npm run research:aether-lattice`, and the
  functional coding benchmark from buttons

This is the shortest path from SCBE's current backend strength to a product
surface a buyer can understand.
