# SCBE IDE - MVP Specification (V0)

**Document version**: 0.1.0
**Date**: 2026-02-19
**Status**: DRAFT
**Patent reference**: USPTO Application #63/961,403

---

## 1. Product Vision

A governance-first integrated development environment where every file edit, terminal command, AI suggestion, and external integration flows through the SCBE 14-layer safety pipeline before execution. The IDE exists because no current tool treats AI governance as a first-class, embedded control plane -- they bolt it on after the fact. This IDE makes governance the substrate, not the afterthought.

---

## 2. Target User

**Primary**: Solo developers and small teams (2-8 people) building AI-powered products who need provable governance over what AI agents do in their codebase and to their external services.

**Why this over VS Code + Cursor**: VS Code extensions cannot enforce governance gates at the action level. Cursor runs agent actions without a cryptographic audit trail. Neither surfaces real-time risk scores, connector dispatch approval, or the Research-Task-Approve-Execute loop as a native workflow. If you need to prove to a regulator, investor, or enterprise customer that your AI agent never executed an unapproved high-risk action, this is the tool.

---

## 3. V0 Feature Set

### F1: Code Editor

The editor is functional infrastructure, not a differentiator. It must work well enough that users do not leave the IDE to write code.

| Capability | Implementation notes |
|---|---|
| Syntax highlighting | TextMate grammar support; ship with TS, Python, JSON, YAML, Markdown, TOML |
| Multi-cursor editing | Standard ctrl+D / cmd+D select-next behavior |
| Search and replace | File-local and project-wide; regex support |
| File tree | Collapsible tree with project root detection; show git status indicators |
| Integrated terminal | PTY-backed terminal panel; multiple sessions; shell auto-detection |
| LSP support | TypeScript (`typescript-language-server`) and Python (`pyright`) at launch |
| Tab management | Open, close, reorder, split horizontal/vertical; dirty-file indicators |
| Keyboard shortcuts | Ship a default keymap; no custom keymap editor in V0 |

Constraints:
- No vim/emacs mode in V0.
- No minimap.
- No inline diff view (use terminal `git diff`).

### F2: SCBE Governance Panel

The right-side panel that makes governance visible and actionable.

| Component | Behavior |
|---|---|
| **Decision feed** | Live-updating list of governance decisions (ALLOW, QUARANTINE, ESCALATE, DENY) with timestamps, actor, resource, risk score, and harmonic cost. Color-coded: green/yellow/orange/red. |
| **Action queue** | Pending operations awaiting execution or approval. Each entry shows: operation type, target resource, computed risk score (0.0-1.0), risk prime after harmonic amplification, and the originating actor (human or AI agent). |
| **Approve/Deny controls** | One-click approve or deny for ESCALATE and QUARANTINE items. Approve requires a confirmation dialog for risk > 0.6. Deny is immediate. |
| **Audit log viewer** | Scrollable, filterable log of all governance events. Each entry is hash-chained (SHA-256 linking to previous entry). Filter by: decision type, actor, time range, risk threshold. Export to JSON. |
| **Policy summary** | Read-only list of active governance policies (POL-001 through POL-005 and any user-defined). Shows policy name, priority, tongue code, and enabled state. |

Data source: WebSocket subscription to `localhost:8000` governance events and `localhost:8080/v1/audit` REST polling.

### F3: Connector Manager

Left-side panel (below file tree) for managing external service connectors.

| Capability | Detail |
|---|---|
| **Register connector** | Form-based creation. Fields: name, kind (enum: n8n, zapier, shopify, slack, notion, airtable, github_actions, linear, discord, generic_webhook), endpoint URL, HTTP method, timeout, payload mode, auth type, auth token, default headers. Maps directly to `POST /mobile/connectors`. |
| **Edit connector** | Modify any field except connector_id and owner. |
| **Delete connector** | Confirmation dialog, then `DELETE /mobile/connectors/{id}`. |
| **Health status** | Three-state indicator per connector: green (last dispatch succeeded, < 30s ago), yellow (no recent dispatch or last dispatch > 5 min ago), red (last dispatch failed). Health is derived from goal step dispatch results, not from polling the external service. |
| **Quick-connect templates** | Load from `GET /mobile/connectors/templates`. Pre-fill form with `zapier_catch_hook`, `n8n_webhook`, `shopify_admin_read`, or `generic_signed_webhook` template data. User fills in their specific URL and auth token. |
| **Auth material handling** | Auth tokens stored via Secure Vault (F6). UI displays masked value (`****...last4`). Copy-to-clipboard button. Never rendered in plain text in the DOM. |

### F4: Goal Execution Engine

Bottom panel, alongside the terminal.

| Capability | Detail |
|---|---|
| **Create goal** | From editor context: right-click selected code, file tab, or terminal error to pre-populate goal description. Also manual creation via command palette. Fields map to `MobileGoalRequest`: goal text, channel (store_ops / web_research / content_ops / custom), priority, execution mode (simulate / hydra_headless / connector), targets, connector_id. |
| **Lifecycle visualization** | Horizontal stepper bar: `queued` -> `running` -> `review_required` -> `running` -> `completed` (or `failed`). Active step highlighted. Each step shows name, risk level, and status. |
| **Approval gates** | When a goal enters `review_required` status (high-risk step + `require_human_for_high_risk=true`), the stepper bar flashes and a toast notification appears. User clicks approve (calls `POST /mobile/goals/{id}/approve`) or does nothing (goal stays blocked). |
| **Step advancement** | Manual "Advance" button or auto-advance toggle. Each click calls `POST /mobile/goals/{id}/advance`. Connector dispatch results shown inline per step. |
| **Goal history** | Sidebar list of past goals with status badges. Click to view full event timeline. Events from the goal's `events[]` array rendered chronologically. |
| **Bind connector** | Attach a connector to an existing goal via `POST /mobile/goals/{id}/bind-connector`. |

### F5: Research -> Task -> Approve -> Execute Loop

This is the core differentiating workflow. It unifies F2, F4, and F7 into a single, auditable pipeline.

**Step 1 -- Research**

The user or AI agent investigates a problem. Research actions include:
- Web search (via configured search connector or built-in fetch)
- Codebase search (grep/glob across project files)
- Documentation lookup (read project docs, external API docs)
- Terminal command output (run a command, capture output)

Each research action is logged as a governance event with risk=low. The research phase produces a structured summary: findings, relevant files, proposed approach.

**Step 2 -- Task**

Research output is converted into a concrete task with discrete steps. Each step specifies:
- Action type: `file_edit`, `terminal_cmd`, `connector_dispatch`, `api_call`
- Target resource
- Risk level (low / medium / high) -- computed by SCBE pipeline, not self-reported
- Estimated impact description

The task is created as a Mobile Goal (`POST /mobile/goals`) with steps matching the action plan.

**Step 3 -- Approve**

The task enters the governance gate:
- Low-risk steps: auto-approved if user has enabled auto-approve for low risk.
- Medium-risk steps: shown in the action queue with a 10-second countdown before auto-execution (user can cancel).
- High-risk steps: blocked until explicit human approval. Goal enters `review_required` state.

The governance panel (F2) shows each step's risk score, the policy IDs that contributed to the decision, and the harmonic wall cost.

**Step 4 -- Execute**

Approved steps execute:
- `file_edit`: Applied to the editor buffer. Undo available.
- `terminal_cmd`: Executed in IDE terminal. Output captured.
- `connector_dispatch`: Dispatched via the bound connector. HTTP response captured.
- `api_call`: Direct HTTP call with SCBE-signed payload.

Execution results feed back into the goal step status (`done` or dispatch failure).

**Step 5 -- Audit**

Every action across steps 1-4 is logged with:
- SHA-256 hash chain (each entry references the previous entry's hash)
- Timestamp (Unix epoch)
- Actor ID (human user or AI agent identifier)
- Governance decision and risk score at time of execution
- Input/output summary (redacted of secrets via F6 auto-redaction)

The audit trail is viewable in the Governance Panel (F2) and exportable as JSON.

### F6: Secure Vault

Accessible via command palette (`Ctrl+Shift+V` / `Cmd+Shift+V`) and the connector manager.

| Capability | Detail |
|---|---|
| **Encrypted storage** | All secrets encrypted at rest using AES-256-GCM via SCBE envelope encryption (`src/crypto/envelope.ts`). Encryption key derived via HKDF from a user-supplied master password. |
| **Secret CRUD** | Add, view (masked), copy, update, delete secrets. Each secret has a name, value, and optional tags. |
| **Masked display** | UI never shows raw secret values. Display format: `****...{last4}`. Copy-to-clipboard writes the plaintext to the system clipboard and clears it after 30 seconds. |
| **Auto-redaction in AI context** | When building context windows for AI agents (F7), the vault scans outbound text for known secret values and replaces them with `[REDACTED:secret_name]`. This operates on exact string match against all stored secret values. |
| **Connector integration** | When registering a connector (F3), the auth token field stores to the vault automatically. The connector record references the vault entry ID, not the raw token. |

### F7: AI Agent Integration

Floating panel, togglable via `Ctrl+Shift+A` / `Cmd+Shift+A`.

| Capability | Detail |
|---|---|
| **Chat panel** | Conversational interface for AI interaction. Message history persisted per session. |
| **File read/edit** | Agent can read open files and propose edits. Proposed edits enter the governance gate (F5 step 3) before applying. |
| **Terminal commands** | Agent can propose terminal commands. Each command enters the governance gate with risk assessment based on command content (e.g., `rm -rf` = high risk, `ls` = low risk). |
| **Multi-agent routing** | Configuration for multiple AI providers (OpenAI, Anthropic, xAI, Perplexity). User assigns agent roles: "research agent" (uses Perplexity), "coding agent" (uses Claude/GPT), "review agent" (uses a different model). Agent selection is manual in V0 -- no automatic routing. |
| **Governance visibility** | Every agent action appears in the governance panel (F2). Agent-initiated actions are labeled with the agent's identifier. User can filter the governance feed to show only agent actions. |
| **Context window management** | User can see what context the agent receives (file contents, terminal output, research results). Secrets auto-redacted (F6). Context window token count displayed. |

---

## 4. Explicitly Out of Scope for V0

The following are NOT included in V0. Do not build, design, or plan infrastructure for these:

- **Marketplace / extension store** -- no third-party plugins
- **Multiplayer / real-time collaboration** -- single user per instance
- **Cloud deployment / hosted version** -- local desktop application only
- **Mobile app** -- desktop only
- **Custom themes** -- ship one dark theme, one light theme, that is all
- **Git UI** -- use the integrated terminal for all git operations
- **Debugger integration** -- no breakpoints, step-through, or debug console
- **Custom language servers** -- only TypeScript and Python LSP at launch
- **Video / audio features** -- no screen recording, voice, or video
- **Plugin API** -- no extensibility hooks for third parties
- **Telemetry / analytics dashboard** -- the audit log is the telemetry
- **SSO / OAuth login** -- local user, local master password
- **Database viewer** -- not an admin tool
- **Diff / merge conflict resolution UI** -- use terminal

---

## 5. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Cold startup to editor ready | < 3 seconds |
| Memory baseline (editor + terminal, no AI agent) | < 500 MB |
| Memory ceiling (editor + all panels + AI chat active) | < 1.2 GB |
| Offline capability | Full editor, file tree, terminal, vault, audit log viewer. Connector dispatch and AI chat require network. |
| Primary platform | Windows 11 (x64 and ARM64) |
| Secondary platform | macOS 13+ (Apple Silicon and Intel) |
| Tertiary platform (best-effort) | Linux x64 (Ubuntu 22.04+) |
| Secrets at rest | AES-256-GCM encrypted; no plaintext secrets on disk ever |
| Audit trail integrity | SHA-256 hash-chained; tamper-evident; any break in chain raises alert |
| Governance latency | < 50ms for local governance decisions (no network round-trip) |
| LSP response time | < 200ms for autocomplete suggestions |
| File tree indexing | < 2 seconds for projects up to 50,000 files |
| Connector dispatch timeout | Configurable 2-60 seconds per connector (default 8s) |

---

## 6. Information Architecture

```
+-----------------------------------------------------------------------+
|  Title Bar: SCBE IDE -- [project name] -- [active file]               |
+-----------------------------------------------------------------------+
|        |                                    |                          |
|  LEFT  |           CENTER                   |         RIGHT            |
|  240px |           flex                     |         320px            |
|        |                                    |                          |
| +----+ | +--------------------------------+ | +----------------------+ |
| |File| | |  Editor Tabs                   | | | Governance Panel     | |
| |Tree| | |  [main.py] [server.ts] [+]     | | |                      | |
| |    | | +--------------------------------+ | | Decision Feed:       | |
| |    | | |                                | | |  ALLOW  read file    | |
| |    | | |  Active Editor                 | | |  DENY   rm -rf /    | |
| |    | | |                                | | |  ESCAL. deploy prod  | |
| |    | | |  (Monaco-based or custom)      | | |                      | |
| |    | | |                                | | | Action Queue:        | |
| |    | | |                                | | |  [Approve] [Deny]    | |
| |    | | |                                | | |  risk: 0.72          | |
| +----+ | |                                | | |                      | |
| +----+ | |                                | | | Audit Log:           | |
| |Conn| | |                                | | |  #a3f2.. ALLOW 0.12 | |
| |ect | | |                                | | |  #b1c4.. DENY  0.91 | |
| |ors | | |                                | | |  #d7e8.. ESCAL 0.65 | |
| |    | | +--------------------------------+ | +----------------------+ |
| | G  | | |                                | |                          |
| | Y  | | |  Bottom Panel (tabbed)         | |                          |
| | R  | | |  [Terminal] [Goals] [Output]   | |                          |
| |    | | |                                | |                          |
| |    | | |  $ npm run build               | |                          |
| |    | | |  > tsc --noEmit                | |                          |
| |    | | |  > 0 errors                    | |                          |
| +----+ | |                                | |                          |
|        | |  Goal Stepper:                  | |                          |
|        | |  [queued]->[running]->[review]  | |                          |
|        | |   Step 2/4: "deploy" BLOCKED    | |                          |
|        | +--------------------------------+ |                          |
+-----------------------------------------------------------------------+
|  Status Bar: branch | LSP status | governance stats | vault locked    |
+-----------------------------------------------------------------------+

Floating Panel (toggle Ctrl+Shift+A):
+---------------------------+
| AI Chat                   |
|                           |
| User: Fix the auth bug    |
| Agent: I found 3 issues   |
|   in server.ts...         |
|                           |
| [Research] [Task] [Send]  |
| Context: 2,340 tokens     |
| Agent: claude-opus-4-6    |
+---------------------------+
```

**Panel behavior**:
- Left panel: collapsible, drag-resizable. File tree is top section, Connector panel is bottom section with a splitter.
- Center: occupies remaining horizontal space. Editor tabs on top, bottom panel below with a vertical splitter.
- Right panel: collapsible, drag-resizable. Fixed minimum width of 280px.
- Bottom panel: tabbed (Terminal, Goals, Output). Default height 200px, resizable.
- Floating AI chat: draggable, resizable, stays on top. Can be docked to the right panel as an additional tab.
- Status bar: always visible. Shows current git branch, LSP connection status, governance decision count (allow/deny/escalate today), and vault lock state.

---

## 7. API Dependencies

The IDE consumes these SCBE backend endpoints. The backend runs at `localhost:8000` (FastAPI/Python) and `localhost:8080` (Express/TypeScript governance server).

### 7.1 Goal Endpoints (FastAPI -- localhost:8000)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/mobile/goals` | Create a new goal with step plan |
| `GET` | `/mobile/goals` | List goals for authenticated user |
| `GET` | `/mobile/goals/{goal_id}` | Get full goal state and event history |
| `POST` | `/mobile/goals/{goal_id}/advance` | Execute next pending step |
| `POST` | `/mobile/goals/{goal_id}/approve` | Approve high-risk steps |
| `POST` | `/mobile/goals/{goal_id}/bind-connector` | Attach connector to goal |

### 7.2 Connector Endpoints (FastAPI -- localhost:8000)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/mobile/connectors` | Register new connector |
| `GET` | `/mobile/connectors` | List connectors for authenticated user |
| `GET` | `/mobile/connectors/{connector_id}` | Get connector details |
| `DELETE` | `/mobile/connectors/{connector_id}` | Delete connector |
| `GET` | `/mobile/connectors/templates` | Get quick-connect templates |

### 7.3 Governance Endpoints (FastAPI -- localhost:8000)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/governance-check` | Check governance decision (agent, topic, context) |
| `POST` | `/seal-memory` | Seal data with governance check |
| `POST` | `/retrieve-memory` | Retrieve data with governance verification |
| `POST` | `/simulate-attack` | Demo/test fail-to-noise protection |
| `GET` | `/health` | System health check |
| `GET` | `/metrics` | Usage metrics |

### 7.4 Governance Endpoints (Express -- localhost:8080)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/govern` | Request governance decision for an action |
| `POST` | `/v1/govern/batch` | Batch governance decisions |
| `GET` | `/v1/policies` | List active governance policies |
| `GET` | `/v1/audit` | Query audit log (filter by actor, decision, time) |
| `GET` | `/v1/audit/{id}` | Get specific audit entry |
| `GET` | `/v1/stats` | Governance statistics |

### 7.5 Vault Endpoints (to be implemented)

These endpoints do not exist yet and must be built as part of V0:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/vault/secrets` | Store encrypted secret |
| `GET` | `/vault/secrets` | List secret metadata (names, tags -- never values) |
| `GET` | `/vault/secrets/{name}` | Retrieve decrypted secret (requires master password) |
| `PUT` | `/vault/secrets/{name}` | Update secret value |
| `DELETE` | `/vault/secrets/{name}` | Delete secret |
| `POST` | `/vault/redact` | Scan text and return redacted version |

### 7.6 Authentication

All authenticated endpoints require `X-Api-Key` header. The IDE stores the API key in the Secure Vault and attaches it to every outbound request. The IDE must never log, display, or transmit the API key in plaintext outside of the HTTP header.

---

## 8. Success Criteria for V0

V0 is complete when ALL of the following are demonstrably true in a live session:

| # | Criterion | Verification method |
|---|---|---|
| SC-1 | User can open a TypeScript project, get autocomplete from `typescript-language-server`, and edit files with multi-cursor | Manual test: open SCBE-AETHERMOORE repo, edit `src/api/server.ts`, verify autocomplete for Express types |
| SC-2 | User can open a Python project and get autocomplete from `pyright` | Manual test: open `src/api/main.py`, verify autocomplete for FastAPI types |
| SC-3 | User can register a `generic_webhook` connector with auth token, and the token is stored encrypted (never in plaintext on disk or in UI) | Inspect vault storage file with hex editor; confirm AES-256-GCM envelope; confirm UI shows `****...last4` |
| SC-4 | User can create a goal from editor context (right-click selected code) and see the goal lifecycle stepper progress through `queued -> running -> completed` | Manual test: select code, create goal, advance steps, observe stepper |
| SC-5 | A goal with a high-risk step blocks at `review_required` until the user explicitly approves | Manual test: create `store_ops` goal, advance to step 3 (`execute_catalog_or_fulfillment_changes`, risk=high), confirm it blocks, approve, confirm it proceeds |
| SC-6 | Governance decisions appear in real-time in the governance panel when AI agent proposes a file edit | Manual test: ask AI to edit a file, observe ALLOW/ESCALATE/DENY in the panel before the edit applies |
| SC-7 | Full Research-Task-Approve-Execute loop completes end-to-end | Manual test: ask AI to research a topic, see task created with steps, approve high-risk steps, see execution results, verify audit trail |
| SC-8 | Audit log is hash-chained and tamper-evident | Automated test: export audit log JSON, verify each entry's hash chains to previous, tamper with one entry, verify chain break is detected |
| SC-9 | No raw API keys, tokens, or secrets appear in the IDE's log files, AI context windows, or rendered DOM | Automated scan: search all log files and DOM snapshots for known test secret values; zero matches required |
| SC-10 | IDE starts in under 3 seconds on Windows 11 with an SSD | Timed test: measure from process launch to editor-ready state on reference hardware |
| SC-11 | IDE uses less than 500 MB memory with one project open and no AI chat active | Measure via Task Manager after 5 minutes of idle with one project loaded |
| SC-12 | IDE works offline for all local operations (editing, terminal, vault, file tree, audit log viewing) | Disconnect network, verify all local features function, verify connector dispatch fails gracefully with user-visible error |

---

## Appendix A: Technology Candidates (not prescriptive)

These are starting-point recommendations. Final choices are implementation decisions.

| Component | Candidates |
|---|---|
| Application shell | Electron 33+ or Tauri 2.x |
| Editor core | Monaco Editor (VS Code's editor) or CodeMirror 6 |
| Frontend framework | React 19 or SolidJS |
| State management | Zustand or Jotai |
| IPC / backend communication | WebSocket for live governance feed; HTTP for REST calls |
| LSP integration | `vscode-languageserver-protocol` npm package |
| Terminal emulator | xterm.js |
| Cryptography | Node.js `crypto` module (AES-256-GCM, HKDF, SHA-256) + SCBE `src/crypto/` |

## Appendix B: Glossary

| Term | Definition |
|---|---|
| **SCBE** | Spectral Context-Bound Encryption -- the 14-layer security pipeline |
| **Governance decision** | ALLOW, QUARANTINE, ESCALATE, or DENY -- the four possible outcomes of the SCBE pipeline |
| **Harmonic wall** | `H(d) = exp(d^2)` -- exponential cost function that makes adversarial drift prohibitively expensive |
| **Connector** | A registered external service endpoint (Zapier, Shopify, n8n, etc.) that goals can dispatch work to |
| **Goal** | A user-defined objective with discrete steps, lifecycle state, and optional connector binding |
| **Vault** | Encrypted local storage for API keys, tokens, and secrets |
| **Sacred Tongues** | The six dimensions (KO, AV, RU, CA, UM, DR) of the Langues Metric used in the SCBE pipeline |
| **Risk prime** | The amplified risk score after harmonic wall scaling: `risk' = risk_base / max(H, 1e-10)` |
| **ML-KEM-768** | NIST FIPS 203 post-quantum key encapsulation mechanism |
| **ML-DSA-65** | NIST FIPS 204 post-quantum digital signature algorithm |
