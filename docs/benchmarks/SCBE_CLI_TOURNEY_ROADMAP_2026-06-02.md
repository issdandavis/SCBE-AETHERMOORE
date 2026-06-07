# SCBE CLI Tourney Roadmap

Generated: 2026-06-02

## Purpose

Build the SCBE CLI into a local-first agent console that matches the polish and ergonomics users expect from modern AI-native agent terminals (Claude Code, Codex CLI, Gemini CLI, and Warp-style terminals) while keeping SCBE's actual advantage: deterministic route control, GeoSeal permissions, audit receipts, semantic/token decomposition, and cross-model workflow orchestration.

This document is a product roadmap and benchmark ladder. It is not a public leaderboard claim.

## Competitive Baseline

| System | Publicly visible strengths | SCBE target response |
| --- | --- | --- |
| Hermes IDE | AI-native terminal/IDE, rich chat, tool-call cards, diff previews, persistent conversations, project scanning, command palette, token/cost dashboard. | Match the clarity of the UI and session persistence, then add GeoSeal route receipts, permission tiers, semantic token views, and deterministic reroute maps. |
| herm | Containerized coding agent, multi-provider, local models via Ollama, open prompts, host isolation by default. | Add an optional container lane, but keep SCBE's stronger route policy: user-selected permission levels, secret obfuscation, and governed receipts for every tool call. |
| Claude Code / Codex CLI / Gemini CLI | Strong model-backed coding loops, native terminal workflow, tool execution, git/code awareness. | Use them as callable drivers when useful, but wrap them in SCBE's route lattice, permission gates, context saving, and benchmark receipts. |
| Terminal-Bench 2.0 agents | Public score pressure on real terminal task completion; agent-model combinations matter more than raw model scores. | Compete as an agent harness, not a model. The model can change; the SCBE advantage should persist as route planning, fail-safe execution, and evidence logging. |

## Feature Target

The product shape is a governed route console:

```text
SCBE route console
observe -> shift -> execute -> verify -> reroute

[1] intent       semantic atoms, command objective, risk class
[2] map          route lattice, fallback coordinates, permission tier
[3] clutch       commit/hold/retry/abort transitions
[4] fire order   tetra-tree chain commands and multi-object command bursts
[5] receipt      GeoSeal decision, tool output, secret scrub, replay notes
```

The car-engine analogy is the right implementation model: workflows are not always linear. They are phase-ordered sequences where firing order changes the larger machine. The CLI should expose that order plainly.

## SCBE-Only Differentiators

| Layer | Build target | Why it matters |
| --- | --- | --- |
| GeoSeal route gate | `ALLOW`, `REVIEW`, `QUARANTINE`, `DENY` before execution, with user-chosen policy profiles. | Competes with permission prompts by making them inspectable and deterministic. |
| Atomic tokenizer | Break command/task text into semantic atoms before routing. | Lets the CLI detect connective leaks, hidden destructive intent, and malformed objectives before shell execution. |
| Chemical compiler | Map semantic atoms into executable compounds: safe command, tool call, workflow step, fallback, receipt. | Gives agents a structured "keyboard" instead of raw shell improvisation. |
| Semantic mirror tunnels | Relabel words by base composition and role: object, action, constraint, boundary, credential, destructive verb. | Makes prompt/command ambiguity visible to the user and to other agents. |
| Tetra-tree command builder | Multi-object command graph with numbered phase firing, not one long script. | Enables non-linear workflows such as test -> patch -> reroute -> verify -> package. |
| Clutch transitions | `observe`, `shift`, `execute`, `verify`, `reroute` state machine. | Prevents repeated loops and lets fallback coordinates fire when a command stalls or repeats. |
| Secret obfuscation | Scrub tokens, keys, SSNs, env values, and connector creds before logs or model calls. | Makes local use safer and makes audit receipts publishable. |
| Context compaction detection | Detect when a model/session lost working context and swap in saved route state. | Keeps long workflows alive across context loss. |
| Cross-model workflow bus | Delegate to Claude, Codex, Gemini, Ollama, or local tools through the same route console. | Makes SCBE a harness and control plane, not another single-model wrapper. |

## Command Surface Roadmap

| Command | Purpose | First useful behavior |
| --- | --- | --- |
| `scbe platform` | Already added readiness view. | Keep as the product landing command. |
| `scbe tourney` | Run the local benchmark suite and emit a proof packet. | Wrap `bench:shell`, `bench:corpus`, `bench:matrix`, `bench cli-competitive`, and adapter checks. |
| `scbe keyboard` | Show route hotkeys and phase controls. | Display numbered workflow states and available transitions for current task. |
| `scbe lattice` | Build and inspect chain-command graphs. | Compile intent into nodes: observe, read, patch, test, reroute, receipt. |
| `scbe permissions` | Manage user-selected risk profiles. | Profiles such as `solo-dev`, `research`, `client-safe`, `destructive-blocked`. |
| `scbe secrets` | Preflight and obfuscate sensitive text/files. | Scan proposed tool calls and receipts before model exposure or publish. |
| `scbe context` | Save, restore, and compact route state. | Snapshot active objective, files, command history, failures, and next coordinate. |
| `scbe semantic` | Show semantic-token and composition breakdown. | Render base atoms, roles, risk words, and route labels for a prompt/command. |
| `scbe fire` | Execute tetra-tree command phases. | Fire a numbered subset of nodes with policy gates and receipt output. |

## Benchmark Circuit

### Tier 0: Local Product Harness

These are private/local scores. They are valid engineering signals, not public leaderboard claims.

| Lane | Current evidence | Claim allowed |
| --- | --- | --- |
| SCBE shell benchmark | 30/30 local shell-agentic cases passing. | Local shell protocol coverage is green. |
| SCBE task corpus | 12/12 offline scaffold corpus passing with 0 false-done and 0 ko-bans. | Route fallback and answer-file contracts work on this corpus. |
| CLI competitive harness | SCBE GeoSeal profile 11/11 in the local fixture. | SCBE local control plane covers more fixture features than the static profiles in that harness. |
| Harness matrix | Protocol harness, offline corpus, and missing-model control green. | Benchmark runner detects local success and controlled failure. |
| Local Terminal-Bench-style adapter | 3/3 adapter contract smoke passing. | Adapter contract works locally; this is not an official Terminal-Bench score. |

### Tier 1: Official Local Harnesses

| Suite | Why it matters | Next action |
| --- | --- | --- |
| Terminal-Bench 2.0 | Public terminal task benchmark where agent-model combinations are scored. | Install/run under a supported Python 3.12 environment and submit unchanged-harness artifacts. |
| SWE-bench Verified/Lite | Repository issue repair benchmark with official `% Resolved`. | Wrap patch generation in SCBE receipts after terminal lane is stable. |
| AgentDojo | Tool-use prompt-injection defense benchmark. | Add SCBE as a defense layer around every tool call and tool result. |
| tau-bench / tau2-bench | Multi-turn policy and tool-state benchmark. | Map GeoSeal policy decisions to customer-service tool calls. |
| OSWorld / WindowsWorld | Real computer/desktop workflows. | Treat as later-stage UI/desktop governance targets after browser/terminal lanes work. |
| WildClawBench | Long-horizon native-runtime CLI agent tasks that include Claude Code, Codex, OpenClaw, and Hermes Agent harnesses. | Track as a future circuit because it evaluates real tools and long workflows, not short mock tasks. |

### Tier 2: Public Leaderboards

The primary public tournament target is Terminal-Bench 2.0 because it evaluates end-to-end terminal work and reports agent-model combinations. The leaderboard page currently shows 144 entries and publishes accuracy with uncertainty. The top visible entries are above 80%, and Claude Code with Claude Opus 4.6 is listed at 58.0% plus/minus 2.9. That is the arena, but SCBE has no public row yet.

Public claim format after a valid run:

> SCBE governed agent scored X% on Terminal-Bench 2.0 using model Y at commit Z, with GeoSeal enabled for every proposed command. Raw per-task artifacts and governance receipts are published.

Forbidden until that happens:

> SCBE beats other agents and tools on Terminal-Bench.

## Tournament Loop

Every round should produce a loss map, not just a score.

1. Run: execute one benchmark lane with exact commit, model, env, command, and artifact path.
2. Classify: label every failure as model miss, route miss, permission miss, context-loss miss, syntax miss, timeout, benchmark-env issue, or secret/gate issue.
3. Extract: convert the failure into a reusable coordinate, not an ad hoc patch.
4. Patch: add the smallest route, tokenizer, permission, or context mechanism that addresses the class.
5. Test: add deterministic regression and one boundary case.
6. Rerun: same lane, same model if possible.
7. Publish: update local scoreboard with allowed claim boundary.

## Near-Term Build Order

1. `scbe tourney`: one command that runs the local benchmark suite and emits a Markdown/JSON proof packet.
2. `scbe keyboard`: improve the interactive shell look with phase cards, hotkeys, and route-state display.
3. `scbe semantic`: expose semantic atoms and word composition for prompts and shell commands.
4. `scbe permissions`: add named permission profiles that GeoSeal can load before execution.
5. `scbe lattice`: compile intent into a route graph with fallback coordinates.
6. `scbe secrets`: scrub receipts and model-visible context.
7. Official Terminal-Bench 2.0 run lane under Python 3.12/WSL or a clean Linux runner.

## Product Design Bar

The CLI should look like a premium terminal-native control surface:

- crisp banner, no noisy ASCII clutter;
- stable columns for route, gate, command, output, and receipt;
- color only for decision state and risk;
- plain English route hints;
- machine JSON for every important command;
- replayable receipts;
- no hidden destructive execution;
- no secret echoing;
- fallback and reroute visible before it fires.

## Sources

- Terminal-Bench 2.0 paper: https://arxiv.org/abs/2601.11868
- Terminal-Bench 2.0 leaderboard: https://www.tbench.ai/leaderboard/terminal-bench/2.0
- Epoch AI Terminal-Bench methodology notes: https://epoch.ai/benchmarks/terminal-bench
- SWE-bench official leaderboards: https://www.swebench.com/
- OSWorld paper: https://arxiv.org/abs/2404.07972
- WildClawBench paper: https://arxiv.org/abs/2605.10912
- Hermes IDE README: https://github.com/hermes-hq/hermes-ide
- herm agent site: https://hermagent.com/
