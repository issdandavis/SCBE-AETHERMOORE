# SCBE IDE - 90-Day Build Plan (V0)

**Document version**: 0.1.0
**Date**: 2026-02-19
**Status**: DRAFT
**Depends on**: [ARCH_OPTIONS.md](./ARCH_OPTIONS.md), [MVP_SPEC.md](./MVP_SPEC.md)

---

## 1. Overview

This document defines the week-by-week execution plan to deliver a functional V0 of the SCBE IDE in 90 calendar days (13 weeks).

**Architecture decision** (per ARCH_OPTIONS.md): Electron + Monaco + Node.js for V0, with a Tauri + CodeMirror 6 migration planned for V2. This stack scored 77.6% on the weighted decision matrix, winning on dev velocity (+20 points over Tauri) and SCBE integration ease (+15 points) -- the two highest-weighted criteria at weight 5 each.

**MVP scope** (per MVP_SPEC.md): Seven features (F1-F7) comprising the code editor, governance panel, connector manager, goal execution engine, Research-Task-Approve-Execute loop, secure vault, and AI agent integration. Twelve success criteria (SC-1 through SC-12) define the exit gate for V0.

**Goal**: A functional, installable desktop IDE for Windows 11 (primary) and macOS (secondary) that demonstrates governance-first development. Every file edit, terminal command, AI suggestion, and external integration flows through the SCBE 14-layer safety pipeline before execution.

---

## 2. Phase Structure

### Phase 1: Foundation (Weeks 1-3)

Objective: A working Electron shell with Monaco editor, file tree, integrated terminal, LSP completions for TypeScript and Python, and a CI pipeline that builds and tests on every push.

#### Week 1: Electron Shell + Project Scaffolding

**Deliverables**:
- Initialize `ide/` workspace with the following layout:
  ```
  ide/
  ├── package.json
  ├── tsconfig.json
  ├── electron.vite.config.ts
  ├── src/
  │   ├── main/              # Electron main process
  │   │   ├── index.ts       # App entry, window creation
  │   │   ├── ipc/           # IPC handler registration
  │   │   └── shell/         # IdeShell abstraction (ElectronShell impl)
  │   ├── renderer/          # Chromium renderer (React 19)
  │   │   ├── index.html
  │   │   ├── main.tsx
  │   │   ├── App.tsx
  │   │   ├── components/    # UI components
  │   │   ├── panels/        # Left, Center, Right, Bottom panels
  │   │   ├── stores/        # Zustand state stores
  │   │   └── hooks/         # Custom React hooks
  │   ├── preload/           # Context bridge (preload.ts)
  │   └── shared/            # Types shared between main and renderer
  │       ├── ipc-channels.ts
  │       └── types.ts
  ├── resources/             # Icons, assets
  ├── tests/                 # Vitest test files
  └── .github/workflows/     # CI pipeline
  ```
- Electron main process boots, creates a BrowserWindow with `contextIsolation: true`, `sandbox: true`, `nodeIntegration: false`.
- Preload script exposes a typed `window.api` bridge using `contextBridge.exposeInMainWorld`.
- React 19 renderer renders a placeholder layout matching the Information Architecture from MVP_SPEC (left panel 240px, center flex, right panel 320px, bottom panel 200px, status bar).
- Zustand stores initialized: `useEditorStore`, `useFileTreeStore`, `useLayoutStore`.
- Title bar shows "SCBE IDE -- [no project]".
- CI pipeline: GitHub Actions workflow that runs `npm ci`, `npm run build`, `npm test` on push to `main` and all PRs. Windows and macOS matrix.

**Testable verification**: `npm run dev` launches an Electron window with a four-panel layout. CI passes on first push.

#### Week 2: Monaco Editor + File Tree

**Deliverables**:
- Monaco Editor integrated in the center panel via `@monaco-editor/react` or direct `monaco-editor` package.
- Tab management: open, close, reorder tabs. Dirty-file indicator (dot on tab title).
- File open/save via IPC: renderer requests file read/write through preload bridge, main process performs `fs.readFile` / `fs.writeFile`.
- File tree component (left panel, top section):
  - Recursive directory listing via `fs.readdir`.
  - Collapsible tree with folder/file icons.
  - Single-click to preview file (italic tab title), double-click to pin.
  - Git status indicators: modified (M), untracked (U), staged (A) via `simple-git`.
- Project root detection: open folder dialog sets the project root. Persisted in `electron-store`.
- File tree respects `.gitignore` (hide ignored files by default, toggle to show).
- Multi-cursor editing (ctrl+D / cmd+D) works out-of-the-box via Monaco.
- Search and replace: file-local (ctrl+F) and project-wide (ctrl+shift+F) using Monaco's built-in search and a custom ripgrep subprocess for project-wide.
- Keyboard shortcut defaults: ctrl+S save, ctrl+P quick-open, ctrl+shift+P command palette stub (empty for now).

**Testable verification**: Open a real project folder (the SCBE-AETHERMOORE repo). Navigate file tree. Open `src/api/server.ts`. Edit with multi-cursor. Save. Confirm file written to disk.

#### Week 3: Terminal + LSP + CI Hardening

**Deliverables**:
- Integrated terminal (bottom panel, "Terminal" tab):
  - xterm.js with `node-pty` backend.
  - Shell auto-detection: PowerShell on Windows, zsh/bash on macOS/Linux.
  - Multiple terminal sessions (tabs within the terminal panel).
  - Resize handling (cols/rows update on panel resize).
- LSP integration:
  - TypeScript: spawn `typescript-language-server --stdio` as a child process. Connect via `vscode-languageserver-protocol` npm package. Wire diagnostics to Monaco markers. Wire completions to Monaco's `CompletionItemProvider`.
  - Python: spawn `pyright-langserver --stdio`. Same wiring.
  - LSP lifecycle: start on project open, restart on crash (3 retries), status shown in status bar (green dot = running, red dot = stopped).
- Status bar (bottom):
  - Current git branch (via `simple-git`).
  - LSP connection status per language.
  - Placeholder slots for governance stats and vault lock state.
- CI hardening:
  - Add ESLint + Prettier to the pipeline.
  - Add Vitest unit tests for IPC handlers, file tree data model, and tab management logic.
  - Test matrix: Windows (x64), macOS (ARM64).
  - Build produces an unsigned installable artifact (NSIS for Windows, DMG for macOS) via `electron-builder`.

**Testable verification**: Open SCBE-AETHERMOORE repo. Open `src/api/server.ts`, get Express type completions from TypeScript LSP. Open `src/api/main.py`, get FastAPI type completions from Pyright. Open terminal, run `git status`, see output. Status bar shows branch name and green LSP indicators. CI builds an installable artifact.

---

### Phase 2: SCBE Integration (Weeks 4-6)

Objective: Connect the IDE to the SCBE FastAPI backend (localhost:8000) and Express governance server (localhost:8080). Surface governance decisions, connector management, and goal execution as native IDE panels.

**Prerequisite**: SCBE FastAPI server running at localhost:8000. Express governance server running at localhost:8080. Both started manually or via a `docker-compose up` before launching the IDE. The IDE does NOT manage these server processes in V0.

#### Week 4: Governance Panel + WebSocket Feed

**Deliverables**:
- Governance Panel (right panel, per MVP_SPEC F2):
  - WebSocket connection to `localhost:8000` for live governance events.
  - REST polling fallback to `localhost:8080/v1/audit` every 5 seconds if WebSocket unavailable.
  - Decision feed: live-updating list of decisions (ALLOW, QUARANTINE, ESCALATE, DENY). Each entry shows: timestamp, actor, resource, risk score (0.0-1.0), harmonic cost, decision. Color-coded: green (ALLOW), yellow (QUARANTINE), orange (ESCALATE), red (DENY).
  - Action queue: pending operations awaiting approval. Each entry shows: operation type, target resource, risk score, risk prime (after harmonic amplification), originating actor.
- Connection manager service (main process):
  - `ScbeApiClient` class wrapping all HTTP calls to localhost:8000 and localhost:8080.
  - Automatic reconnection on WebSocket disconnect (exponential backoff, max 30s).
  - Health check on startup: `GET /health` to localhost:8000. If unreachable, show a banner in the IDE: "SCBE backend not detected. Governance features unavailable. Start the backend with `docker-compose up`."
- Zustand stores: `useGovernanceStore` (decision feed, action queue, connection status).

**Testable verification**: Start SCBE backend. Launch IDE. Trigger a governance check via curl to `/governance-check`. See the decision appear in the governance panel within 1 second.

#### Week 5: Connector Manager + Goal Basics

**Deliverables**:
- Connector Manager (left panel, below file tree, per MVP_SPEC F3):
  - List connectors: `GET /mobile/connectors` rendered as a scrollable list with name, kind icon, and health indicator (green/yellow/red).
  - Register connector: form-based creation dialog. Fields: name, kind (dropdown of 10 enum values), endpoint URL, HTTP method, timeout, payload mode, auth type, auth token (masked input), default headers (key-value editor). Submits to `POST /mobile/connectors`.
  - Edit connector: click to open pre-filled form. Submit updates via PUT (or re-POST per API).
  - Delete connector: confirmation dialog, then `DELETE /mobile/connectors/{id}`.
  - Quick-connect templates: `GET /mobile/connectors/templates`. Dropdown that pre-fills form fields.
  - Auth token field integrates with Secure Vault (F6, Week 6): on save, token is stored in vault; connector record references vault entry ID.
- Goal Execution basics (bottom panel, "Goals" tab, per MVP_SPEC F4):
  - Create goal: command palette entry "SCBE: Create Goal". Fields map to `MobileGoalRequest`: goal text, channel, priority, execution mode, targets.
  - Goal list: `GET /mobile/goals` rendered as a sidebar within the Goals tab. Status badges (queued, running, review_required, completed, failed).
  - Goal detail view: click a goal to see its step plan and event timeline.
- Right-click context menu on editor and file tabs: "Create Goal from Selection" / "Create Goal from File" pre-populates goal description.

**Testable verification**: Register a `generic_webhook` connector via the UI. See it appear in the connector list. Create a goal from right-clicking selected code. See it appear in the goal list with status "queued".

#### Week 6: Secure Vault + Goal Lifecycle

**Deliverables**:
- Secure Vault (per MVP_SPEC F6):
  - Master password prompt on first use. Password never stored; used to derive encryption key via HKDF-SHA256.
  - Vault storage: encrypted file on disk (`~/.scbe-ide/vault.enc`). Format: AES-256-GCM encrypted JSON blob per SCBE envelope encryption (`src/crypto/envelope.ts` patterns).
  - Secret CRUD via command palette (`Ctrl+Shift+V` / `Cmd+Shift+V`): add, view (masked `****...last4`), copy (30-second clipboard auto-clear), update, delete.
  - Connector auth tokens auto-stored in vault on connector creation (F3 integration from Week 5).
  - Auto-lock: vault locks after 15 minutes of inactivity. Unlock requires master password re-entry.
  - Vault lock state shown in status bar (locked/unlocked icon).
- Goal lifecycle (completing F4):
  - Lifecycle visualization: horizontal stepper bar (`queued -> running -> review_required -> running -> completed/failed`). Active step highlighted. Each step shows name, risk level, status.
  - Step advancement: "Advance" button calls `POST /mobile/goals/{id}/advance`. Result shown inline.
  - Approval gates: when goal enters `review_required`, stepper flashes + toast notification. Approve button calls `POST /mobile/goals/{id}/approve`. Deny does nothing (goal stays blocked).
  - Bind connector: `POST /mobile/goals/{id}/bind-connector` via a dropdown in the goal detail view.
  - Goal history: past goals with status badges. Click to view full event timeline.
- Governance panel additions:
  - Approve/Deny controls for ESCALATE and QUARANTINE items. Approve requires confirmation dialog when risk > 0.6. Deny is immediate.
  - Audit log viewer: scrollable, filterable log. Filter by decision type, actor, time range, risk threshold. Hash chain display (abbreviated SHA-256).
  - Policy summary: read-only list from `GET /v1/policies`.
  - Export audit log to JSON.

**Testable verification**: Store a secret in the vault. Close and reopen IDE -- vault is locked. Unlock with master password. Verify the secret's `****...last4` display. Create a goal, advance it, observe stepper progression. Create a high-risk goal step, confirm it blocks at `review_required`, approve it, confirm it proceeds. Export audit log JSON, verify hash chain integrity with a script.

---

### Phase 3: AI + Workflow Engine (Weeks 7-10)

Objective: Implement the AI chat panel, wire agent actions through governance gates, build the full Research-Task-Approve-Execute loop, and add multi-agent support with secret auto-redaction.

#### Week 7: AI Chat Panel + Basic Agent Actions

**Deliverables**:
- AI Chat Panel (floating panel, per MVP_SPEC F7):
  - Toggle via `Ctrl+Shift+A` / `Cmd+Shift+A`. Draggable, resizable, stays-on-top. Can be docked to right panel as additional tab.
  - Chat interface: message input, message history (persisted per session in memory, not on disk in V0).
  - Provider configuration: settings page for API keys (stored in vault). Support OpenAI, Anthropic, xAI, Perplexity.
  - Basic chat: send message to configured provider, display response. Streaming support (SSE/chunked).
  - Context display: show what context the agent receives (open file name, selected text). Token count displayed.
- Agent file read:
  - Agent can reference open files in its context window.
  - Agent can request to read any project file. Request logged as a governance event (risk=low, auto-approved).
- Agent terminal command proposal:
  - Agent can propose a terminal command in chat.
  - Proposed commands are displayed with a "Run" button (not auto-executed).
  - Risk assessment: commands classified by content (`rm -rf` = high, `ls` = low, `npm install` = medium). Risk shown next to the "Run" button.

**Testable verification**: Open AI chat. Configure an Anthropic API key (stored in vault). Send a message about the current file. Receive a streaming response. Agent proposes a terminal command -- see it displayed with risk score and "Run" button. Governance panel shows the agent's read action.

#### Week 8: Agent Edit Proposals + Governance Gating

**Deliverables**:
- Agent file edit proposals:
  - Agent can propose edits to the current file or any project file.
  - Proposed edits displayed as a diff view (Monaco's built-in diff editor) in a modal or inline panel.
  - Each proposed edit enters the governance gate before applying:
    - Low risk: auto-applied if user has enabled auto-approve for low risk (off by default).
    - Medium risk: shown in action queue with 10-second countdown.
    - High risk: blocked until explicit human approval.
  - Governance panel shows the edit proposal with risk score, affected file, and diff summary.
  - Accept: apply edit to buffer. Undo available (ctrl+Z).
  - Reject: dismiss edit. Logged as DENY in audit trail.
- Governance gating for all agent actions:
  - Every agent action (file read, file edit, terminal command, connector dispatch) routed through `POST /v1/govern` before execution.
  - Governance response determines action: ALLOW (execute), QUARANTINE (show warning, require confirm), ESCALATE (require explicit approval), DENY (block with explanation).
  - Agent-initiated actions labeled with agent identifier in governance panel. Filter toggle: "Show only agent actions".
- Auto-redaction of secrets in AI context (F6 integration):
  - Before sending any context to an AI provider, scan outbound text for exact matches against all stored vault secret values.
  - Replace matches with `[REDACTED:secret_name]`.
  - Display redacted context in the "Context" section of the chat panel so the user can verify what the agent sees.

**Testable verification**: Ask the AI to edit a file. See the diff view with risk score. Approve a medium-risk edit -- see the 10-second countdown, then auto-apply. Reject a high-risk edit -- confirm it does not apply. Check governance panel shows all agent actions. Store an API key in vault, include it in a file, ask the agent about the file -- verify `[REDACTED:...]` in the context display.

#### Week 9: Research-Task-Approve-Execute Loop

**Deliverables**:
- Full F5 implementation (per MVP_SPEC):
  - **Research phase**:
    - Agent can perform: codebase search (grep/glob via main process), documentation lookup (read project files), terminal command execution (capture output).
    - Web search via configured search connector (Perplexity or generic webhook) or built-in fetch to a search API.
    - Each research action logged as a governance event (risk=low).
    - Research phase produces a structured summary: findings (list), relevant files (paths), proposed approach (text).
    - Summary displayed in the chat panel with a "Convert to Task" button.
  - **Task phase**:
    - "Convert to Task" parses the research summary into discrete steps.
    - Each step specifies: action type (`file_edit`, `terminal_cmd`, `connector_dispatch`, `api_call`), target resource, risk level (computed by SCBE pipeline, not self-reported), estimated impact description.
    - Task created as a Mobile Goal (`POST /mobile/goals`) with steps matching the action plan.
    - Goal appears in the Goals tab with the stepper bar.
  - **Approve phase**:
    - Each step enters the governance gate per its risk level (same rules as Week 8).
    - Governance panel shows each step's risk score, contributing policy IDs, and harmonic wall cost.
  - **Execute phase**:
    - Approved steps execute by type:
      - `file_edit`: Applied to editor buffer. Undo available.
      - `terminal_cmd`: Executed in IDE terminal. Output captured and displayed in goal step detail.
      - `connector_dispatch`: Dispatched via bound connector. HTTP response captured.
      - `api_call`: Direct HTTP call with SCBE-signed payload.
    - Execution results feed back into goal step status (`done` or failure).
  - **Audit phase**:
    - Every action across all phases logged with: SHA-256 hash chain, timestamp, actor ID, governance decision, risk score, input/output summary (secrets auto-redacted).
    - Viewable in governance panel audit log. Exportable as JSON.

**Testable verification**: In the AI chat, ask the agent to "research and fix the authentication bug in server.ts". Observe: (1) research actions logged in governance panel, (2) structured summary appears, (3) click "Convert to Task", (4) goal created with steps in Goals tab, (5) low-risk steps auto-advance, (6) high-risk step blocks for approval, (7) approve and see execution, (8) audit trail has complete hash-chained record. This is the SC-7 success criterion.

#### Week 10: Multi-Agent Support + Loop Refinement

**Deliverables**:
- Multi-agent routing (per MVP_SPEC F7):
  - Configuration page for agent roles: "research agent" (default: Perplexity), "coding agent" (default: Claude), "review agent" (configurable). Each role maps to a provider + model.
  - Manual agent selection in chat panel: dropdown to choose which agent role handles the current conversation.
  - Agent identity propagated to governance panel (e.g., "Agent: claude-opus-4-6" or "Agent: perplexity-sonar").
  - Research phase automatically uses the research agent; task/execute phases use the coding agent. User can override.
- Context window management:
  - Expandable "Context" panel in AI chat showing: included files, terminal output excerpts, research results, and total token count.
  - User can add/remove context items manually.
  - Token budget display: current tokens / provider's context window limit.
  - Automatic context trimming: if tokens exceed 80% of limit, oldest context items are summarized or dropped with a warning.
- Loop refinement:
  - Handle partial failures gracefully: if a step fails mid-execution, goal enters `failed` state with error details. User can retry the failed step or skip it.
  - Connector dispatch timeout handling: configurable 2-60 seconds (default 8s per MVP_SPEC). Timeout shows error in step detail, not a hard crash.
  - Goal cancellation: user can cancel a running goal. All pending steps marked as `cancelled`. Running step allowed to complete.
- End-to-end integration tests:
  - Automated test that runs the full Research-Task-Approve-Execute loop against a mock SCBE backend.
  - Verify audit trail hash chain integrity programmatically.

**Testable verification**: Configure a research agent (Perplexity) and coding agent (Claude). Start a research task -- observe research agent handles it. Convert to task -- observe coding agent proposes edits. Governance panel shows different agent identifiers. Cancel a running goal -- confirm pending steps cancelled. Verify token count display updates as context changes.

---

### Phase 4: Hardening + Launch Prep (Weeks 11-13)

Objective: Security audit, performance optimization, cross-platform testing, offline validation, documentation, and success criteria verification.

#### Week 11: Security Audit + Performance Optimization

**Deliverables**:
- Security audit (against THREAT_MODEL.md findings and Electron best practices):
  - Verify `contextIsolation: true` on all BrowserWindows.
  - Verify `sandbox: true` on all renderers.
  - Verify `nodeIntegration: false` everywhere.
  - Verify no `shell.openExternal` calls with unsanitized URLs.
  - Verify CSP headers on all loaded content (`Content-Security-Policy` meta tag or header).
  - Verify preload script exposes minimal API surface.
  - Verify vault encryption: AES-256-GCM with proper IV generation (12 bytes, random), HKDF key derivation with unique salt per encryption.
  - Verify no secrets in log files: scan all log output paths for vault secret values.
  - Verify no secrets in rendered DOM: automated test that stores test secrets, interacts with all panels, then searches DOM innerHTML for raw secret values (SC-9).
  - Verify audit trail hash chain: automated test that exports audit log, tampers with one entry, confirms chain break detection (SC-8).
  - Verify IPC channel whitelist: only declared channels are accessible from renderer.
  - Dependency audit: `npm audit` with zero critical/high vulnerabilities. Address or document any remaining.
- Performance optimization:
  - Startup time target: < 3 seconds cold start on Windows 11 SSD (SC-10).
  - Profiling: measure startup with Electron's `--trace-startup` flag. Identify and defer non-critical initialization (LSP startup, WebSocket connection, file tree full indexing).
  - Lazy-load panels: governance panel, connector manager, AI chat panel loaded on first open, not at startup.
  - Monaco worker optimization: load Monaco web workers from local bundle, not CDN. Defer non-essential language workers.
  - Memory target: < 500 MB with one project open and no AI chat (SC-11). Profile with Chrome DevTools Memory tab. Identify and fix leaks in file tree watchers, WebSocket handlers, and terminal instances.
  - File tree indexing: target < 2 seconds for projects up to 50,000 files. Use `chokidar` with `ignoreInitial: false` and `.gitignore` filter.
  - Governance latency: target < 50ms for local decisions. Profile HTTP round-trip to localhost:8000/8080. If latency exceeds target, implement in-process governance cache for repeated identical decisions.

**Testable verification**: Run security checklist (all items pass). Measure cold start time (< 3 seconds). Measure memory after 5-minute idle with one project (< 500 MB). File tree indexes SCBE-AETHERMOORE repo in < 2 seconds.

#### Week 12: Cross-Platform Testing + Offline Mode

**Deliverables**:
- Windows 11 comprehensive testing (primary platform):
  - Test on x64 and ARM64 Windows 11.
  - Verify NSIS installer works: install, launch, uninstall.
  - Verify node-pty terminal works with PowerShell and Git Bash.
  - Verify file paths with spaces and Unicode characters.
  - Verify LSP servers start correctly (typescript-language-server, pyright).
  - Test at 100%, 125%, and 150% display scaling.
  - Test with Windows Defender real-time scanning enabled (no false positives).
- macOS testing (secondary platform):
  - Test on Apple Silicon (M-series) macOS 13+.
  - Verify DMG installer works: mount, drag to Applications, launch, eject.
  - Verify node-pty terminal works with zsh.
  - Verify code signing (ad-hoc for V0, proper signing deferred to V1).
  - Test Retina display rendering.
- Offline mode validation (SC-12):
  - Disconnect network (disable adapter).
  - Verify: file tree loads and navigates, editor opens/edits/saves files, terminal executes local commands, vault unlock/lock/CRUD works, audit log viewer shows cached entries.
  - Verify: connector dispatch fails gracefully with user-visible error message (not a crash or hang).
  - Verify: AI chat shows "Offline -- AI features unavailable" message.
  - Verify: governance panel shows "Backend disconnected" banner but cached decisions remain visible.
  - Reconnect network: verify WebSocket reconnects automatically, governance feed resumes.
- Accessibility baseline:
  - Keyboard navigation through all panels (Tab, Shift+Tab, Enter, Escape).
  - Screen reader compatibility: ARIA labels on panels, buttons, and interactive elements.
  - High contrast: verify both dark and light themes are readable.

**Testable verification**: Install on a clean Windows 11 x64 machine -- full workflow passes. Install on macOS ARM64 -- full workflow passes. Disconnect network -- all local features work. Reconnect -- live features resume within 30 seconds.

#### Week 13: Documentation + Success Criteria Verification + Release

**Deliverables**:
- Documentation:
  - `README.md` for the `ide/` workspace: setup instructions, build commands, architecture overview.
  - `GETTING_STARTED.md`: first-run guide for new users (install, first project, vault setup, connector registration, first goal).
  - `KEYBOARD_SHORTCUTS.md`: complete keymap reference.
  - API dependency documentation: which SCBE endpoints the IDE consumes, how to start the backend.
  - Developer documentation: how to build from source, run tests, contribute.
- Success criteria verification (all 12 from MVP_SPEC):

  | # | Criterion | Test | Owner |
  |---|---|---|---|
  | SC-1 | TypeScript LSP autocomplete | Open SCBE repo, edit `src/api/server.ts`, verify Express type completions | Manual |
  | SC-2 | Python LSP autocomplete | Open `src/api/main.py`, verify FastAPI type completions | Manual |
  | SC-3 | Encrypted connector auth tokens | Register webhook connector, inspect `vault.enc` with hex editor, verify AES-256-GCM, verify UI shows `****...last4` | Manual + automated |
  | SC-4 | Goal lifecycle from editor context | Right-click selected code, create goal, advance steps, observe stepper | Manual |
  | SC-5 | High-risk step blocks for approval | Create `store_ops` goal, advance to high-risk step, confirm block, approve, confirm proceed | Manual |
  | SC-6 | Real-time governance for AI edits | Ask AI to edit a file, observe ALLOW/ESCALATE/DENY in panel before edit applies | Manual |
  | SC-7 | End-to-end RTAE loop | Full Research-Task-Approve-Execute with audit trail | Manual |
  | SC-8 | Tamper-evident audit log | Export JSON, verify hash chain, tamper one entry, verify break detected | Automated |
  | SC-9 | No raw secrets in logs/DOM/AI context | Store test secrets, scan all outputs for raw values, zero matches | Automated |
  | SC-10 | < 3 second startup | Timed measurement on Windows 11 SSD | Automated |
  | SC-11 | < 500 MB memory baseline | Task Manager measurement after 5-minute idle | Manual |
  | SC-12 | Full offline capability | Disconnect network, verify all local features function | Manual |

- Release preparation:
  - Version tag: `v0.1.0`.
  - Signed builds (ad-hoc for V0).
  - GitHub Release with Windows installer (.exe) and macOS disk image (.dmg).
  - Known issues list.
  - Changelog.

**Testable verification**: All 12 success criteria pass. Release artifacts are downloadable and installable on clean machines.

---

## 3. Weekly Milestone Table

| Week | Phase | Milestone | Deliverable | Go/No-Go Gate |
|------|-------|-----------|-------------|---------------|
| 1 | Foundation | Electron shell boots | Four-panel layout renders, CI pipeline green | -- |
| 2 | Foundation | Editor functional | Monaco opens/edits/saves files, file tree navigates project, multi-cursor works | -- |
| 3 | Foundation | Terminal + LSP live | Terminal runs commands, TypeScript + Python autocomplete works, installable artifact builds | **Phase 1 Gate** |
| 4 | SCBE Integration | Governance panel live | Decision feed shows real-time SCBE decisions via WebSocket, action queue populated | -- |
| 5 | SCBE Integration | Connectors + Goals basic | Connector CRUD via UI, goal creation from editor context, goal list renders | -- |
| 6 | SCBE Integration | Vault + Goal lifecycle | AES-256-GCM vault stores secrets, goal stepper shows full lifecycle, approval gates block high-risk steps | **Phase 2 Gate** |
| 7 | AI + Workflow | AI chat functional | Chat panel sends/receives AI messages, agent proposes commands with risk scores | -- |
| 8 | AI + Workflow | Governance-gated AI edits | Agent edit proposals show as diffs, governance gates enforce ALLOW/DENY, secrets auto-redacted | -- |
| 9 | AI + Workflow | RTAE loop end-to-end | Research-Task-Approve-Execute completes with hash-chained audit trail | -- |
| 10 | AI + Workflow | Multi-agent + refinement | Multiple agent roles configured, context management works, partial failure handling | **Phase 3 Gate** |
| 11 | Hardening | Security + performance | Security audit passes, startup < 3s, memory < 500 MB, governance latency < 50ms | -- |
| 12 | Hardening | Cross-platform + offline | Windows 11 + macOS tested, offline mode fully functional, graceful network recovery | -- |
| 13 | Hardening | Documentation + release | All 12 SC pass, release artifacts published, docs complete | **Phase 4 Gate (Launch)** |

---

## 4. Dependencies

### 4.1 External Dependencies

| Dependency | Version | Purpose | Risk |
|---|---|---|---|
| Electron | 33+ (Chromium 130+) | Application shell | Stable; monthly releases |
| Monaco Editor | 0.52+ | Code editor engine | Stable; Microsoft-maintained |
| React | 19.x | UI framework | Stable |
| xterm.js | 5.x | Terminal emulator | Stable; widely used |
| node-pty | 1.x | PTY backend for terminal | Platform-sensitive; test on Windows ARM64 |
| vscode-languageserver-protocol | 3.17+ | LSP client | Stable |
| typescript-language-server | latest | TypeScript LSP | Stable |
| pyright | latest | Python LSP | Stable; Microsoft-maintained |
| simple-git | 3.x | Git operations for file tree | Stable |
| chokidar | 4.x | File system watching | Stable |
| electron-builder | 25+ | Build installers | Stable |
| electron-store | 10+ | Persistent config storage | Stable |
| zustand | 5.x | State management | Stable; lightweight |
| SCBE FastAPI backend | localhost:8000 | Governance, goals, connectors API | **Must be running**; team-controlled |
| SCBE Express governance server | localhost:8080 | Governance decisions, audit log | **Must be running**; team-controlled |

### 4.2 Internal Dependencies (What Blocks What)

| Blocked Item | Depends On | Phase |
|---|---|---|
| File tree git status | simple-git integration | Phase 1 |
| Governance panel | SCBE backend WebSocket / REST | Phase 2 |
| Connector manager | SCBE backend `/mobile/connectors` endpoints | Phase 2 |
| Goal execution | SCBE backend `/mobile/goals` endpoints | Phase 2 |
| Vault-backed connector auth | Secure vault implementation | Phase 2 (Week 6 depends on Week 5) |
| AI governance gating | Governance panel + `POST /v1/govern` | Phase 3 (Week 8 depends on Week 4) |
| Secret auto-redaction in AI context | Secure vault | Phase 3 (Week 8 depends on Week 6) |
| RTAE loop | AI chat + governance gating + goal execution + connectors | Phase 3 (Week 9 depends on Weeks 7-8) |
| Multi-agent routing | AI chat panel | Phase 3 (Week 10 depends on Week 7) |
| Security audit | All features implemented | Phase 4 (Week 11 depends on Week 10) |
| Offline mode validation | All panels + vault + editor | Phase 4 (Week 12 depends on Weeks 1-10) |
| Success criteria verification | All features + hardening | Phase 4 (Week 13 depends on Weeks 11-12) |

### 4.3 Dependency Graph

```
Week 1: Electron Shell
  |
  v
Week 2: Monaco + File Tree
  |
  v
Week 3: Terminal + LSP ---------> [Phase 1 Gate]
  |                                     |
  v                                     v
Week 4: Governance Panel          Week 5: Connectors + Goals
  |         |                           |
  |         v                           v
  |    Week 6: Vault + Goal Lifecycle -> [Phase 2 Gate]
  |         |         |
  v         v         v
Week 7: AI Chat Panel
  |
  v
Week 8: AI Governance Gating + Redaction
  |
  v
Week 9: RTAE Loop End-to-End
  |
  v
Week 10: Multi-Agent + Refinement -> [Phase 3 Gate]
  |
  v
Week 11: Security Audit + Performance
  |
  v
Week 12: Cross-Platform + Offline
  |
  v
Week 13: Docs + SC Verification -> [Phase 4 Gate / LAUNCH]
```

---

## 5. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Monaco integration complexity** -- Monaco's monolithic API and web worker model cause unexpected issues in Electron's renderer process (CSP conflicts, worker loading failures, memory bloat) | Medium | High | Start Monaco integration in Week 2 (early). Use `@monaco-editor/react` wrapper for faster bootstrapping. Maintain a fallback branch with a plain textarea editor for worst-case. Budget 2 extra days in Week 2 for Monaco-specific debugging. |
| R2 | **SCBE API changes** -- The FastAPI and Express governance endpoints change signature, add required fields, or change response formats during the 13-week build, breaking IDE integration | Medium | High | Pin SCBE backend to a specific commit/tag at Phase 2 start. Define an API contract (OpenAPI spec) and test against it. Use adapter/wrapper layer (`ScbeApiClient`) so API changes require updating one file, not every panel. |
| R3 | **Electron security CVEs** -- A critical Chromium or Electron vulnerability is disclosed during the build, requiring an urgent version bump that may break existing functionality | Medium | Medium | Subscribe to Electron security advisories. Pin to a specific Electron version. Budget 1-2 days per phase for Electron version bumps. Maintain `contextIsolation`, `sandbox`, and CSP from day one so the attack surface is minimal regardless. |
| R4 | **Performance targets missed** -- Electron + Monaco + React + governance panel exceeds the 500 MB memory target or 3-second startup target, especially on Windows ARM64 | High | High | Profile early (Week 3, not Week 11). Implement lazy loading for all non-editor panels from the start. Defer Monaco language workers for unused languages. If 500 MB is unachievable, document the measured baseline and adjust the target with justification. Keep the governance panel lightweight (virtual scrolling for decision feed, limit rendered entries to 200). |
| R5 | **AI provider rate limits** -- OpenAI, Anthropic, or Perplexity API rate limits cause degraded AI experience during development and testing, especially during the RTAE loop (Week 9) where multiple sequential API calls are required | Medium | Medium | Use mock AI responses for automated testing. Implement request queuing with backoff in the AI service layer. Cache research results to avoid redundant API calls. Support local model providers (Ollama) as a rate-limit-free development fallback (stretch goal, not required for V0). |
| R6 | **Vault crypto implementation errors** -- Incorrect IV reuse, HKDF salt mismanagement, or envelope format bugs compromise the security of stored secrets, undermining a core differentiator | Low | Critical | Follow SCBE's existing `src/crypto/envelope.ts` patterns exactly. Use Node.js `crypto.randomBytes(12)` for every IV -- never reuse. Write property-based tests (fast-check) for encrypt/decrypt round-trip with random payloads. Security review the vault implementation specifically in Week 11 with fresh eyes. |
| R7 | **Cross-platform node-pty issues** -- node-pty (native C++ addon) fails to compile or behaves differently on Windows ARM64, causing terminal functionality to break on a primary target platform | Medium | High | Test node-pty on Windows ARM64 in Week 1 (before building the full terminal). If it fails, evaluate alternatives: `@xterm/addon-attach` with a WebSocket PTY server, or `child_process.spawn` with a raw shell (degraded but functional). Keep terminal implementation behind an abstraction (`ITerminalBackend`) so the backend can be swapped. |
| R8 | **Scope creep** -- Feature requests and "just one more thing" additions during the 13-week build push the timeline past 90 days, delaying launch and increasing complexity | High | High | The MVP_SPEC's "Explicitly Out of Scope" list (Section 4) is the contract. Any feature not in F1-F7 is deferred to V1. Weekly milestone reviews enforce accountability: if a week's deliverable is not met, the following week absorbs it by cutting scope from a later week (never by extending the timeline). The Go/No-Go gates are hard stops -- if a gate fails, the plan is re-scoped, not extended. |
| R9 | **LSP server stability** -- TypeScript or Python language servers crash under heavy use, leak memory over long sessions, or produce incorrect diagnostics that erode trust in the editor | Low | Medium | Implement LSP lifecycle management: automatic restart on crash (3 retries, then disable with user notification). Monitor LSP process memory and restart if it exceeds 300 MB. Use well-tested LSP servers (typescript-language-server and pyright are both battle-proven). Log LSP crashes for post-mortem. |
| R10 | **WebSocket reliability** -- The governance WebSocket connection to localhost:8000 drops frequently, causing the decision feed to miss events and the governance panel to show stale data | Medium | Medium | Implement exponential backoff reconnection (1s, 2s, 4s, 8s, max 30s). On reconnect, fetch the last N governance events via REST to fill gaps. Display connection status prominently in the governance panel header (green dot / red dot). Fall back to REST polling (every 5 seconds) if WebSocket is unavailable for > 60 seconds. |

---

## 6. Go/No-Go Checkpoints

### Phase 1 -> Phase 2 (End of Week 3)

All of the following must be true to proceed to Phase 2:

| # | Criterion | Verification |
|---|---|---|
| G1.1 | Electron app launches on Windows 11 and macOS | Manual test on both platforms |
| G1.2 | Monaco editor opens files from the file tree | Open 5+ files of different types (TS, PY, JSON, MD, YAML) |
| G1.3 | File save writes to disk correctly | Edit a file, save, verify on disk with external tool |
| G1.4 | Multi-cursor editing works | Select-next (ctrl+D) adds cursors, edits apply to all |
| G1.5 | Terminal runs commands and displays output | Run `echo hello`, `git status`, `python --version` |
| G1.6 | TypeScript LSP provides completions | Open a `.ts` file with Express imports, verify type completions appear |
| G1.7 | Python LSP provides completions | Open a `.py` file with FastAPI imports, verify type completions appear |
| G1.8 | CI pipeline builds and tests on push | Last 3 CI runs are green |
| G1.9 | Installable artifact builds successfully | NSIS installer (Windows) and DMG (macOS) can be installed and launched on clean machines |

**If gate fails**: Identify blocking issue. If LSP-related, proceed with LSP as a known gap and fix in Week 4. If Electron shell or Monaco core is broken, do not proceed -- extend Phase 1 by 1 week and compress Phase 4 by 1 week.

### Phase 2 -> Phase 3 (End of Week 6)

All of the following must be true to proceed to Phase 3:

| # | Criterion | Verification |
|---|---|---|
| G2.1 | Governance panel shows live decisions from SCBE backend | Trigger 3+ governance checks via API, see all appear in panel within 2 seconds |
| G2.2 | Action queue displays pending operations | Queue at least 1 ESCALATE operation, see it in the queue with risk score |
| G2.3 | Connector CRUD works end-to-end | Create, edit, and delete a connector via the UI. Verify via API list call. |
| G2.4 | Quick-connect templates load and pre-fill form | Select a template, verify fields are pre-populated |
| G2.5 | Goal can be created from editor context | Right-click selected code, create a goal, verify it appears in goal list |
| G2.6 | Goal lifecycle stepper progresses | Create goal, advance steps, see stepper update through at least 3 states |
| G2.7 | High-risk step blocks for approval | Advance to a high-risk step, confirm it blocks, approve, confirm it proceeds |
| G2.8 | Secure vault stores and retrieves secrets | Store a secret, lock vault, unlock, retrieve -- verify masked display and clipboard copy |
| G2.9 | Connector auth token stored in vault | Create connector with auth token, verify vault contains the token, connector references vault entry |
| G2.10 | Audit log export produces valid hash-chained JSON | Export, run hash verification script, confirm chain integrity |

**If gate fails**: If vault crypto is the blocker, proceed to Phase 3 with vault storing in plaintext (file permission-protected) and fix crypto in Week 7 -- this is a temporary compromise, not acceptable for launch. If governance panel WebSocket is broken, proceed with REST polling and fix WebSocket in parallel during Week 7. All other failures are hard blockers -- do not proceed.

### Phase 3 -> Phase 4 (End of Week 10)

All of the following must be true to proceed to Phase 4:

| # | Criterion | Verification |
|---|---|---|
| G3.1 | AI chat sends and receives messages with at least one provider | Send 5 messages, receive streaming responses, verify message history |
| G3.2 | Agent can propose file edits shown as diffs | Ask agent to modify a file, see diff view with accept/reject |
| G3.3 | Agent actions routed through governance gate | Agent proposes a high-risk action, governance panel shows ESCALATE/DENY before execution |
| G3.4 | Secrets auto-redacted in AI context | Store a test secret, include it in a file, send to AI -- verify `[REDACTED:...]` in context display |
| G3.5 | Full RTAE loop completes end-to-end | Research -> Task creation -> Approval gates -> Execution -> Audit trail |
| G3.6 | Audit trail for RTAE loop is hash-chained | Export and verify hash chain for a complete RTAE session |
| G3.7 | Multi-agent routing works | Configure 2 agents, verify correct agent handles research vs. coding tasks |
| G3.8 | Partial failure handling works | Simulate a step failure mid-goal, verify goal enters failed state, retry is available |

**If gate fails**: If AI chat is functional but RTAE loop has bugs, proceed to Phase 4 and fix RTAE in Week 11. If AI chat itself is non-functional (no messages send/receive), do not proceed -- extend Phase 3 by 1 week and compress Phase 4's documentation to the minimum. Multi-agent routing (G3.7) is a soft gate -- if single-agent works, proceed with multi-agent as a known gap.

### Phase 4 -> Launch (End of Week 13)

All 12 MVP_SPEC success criteria (SC-1 through SC-12) must pass:

| # | SC | Status Required |
|---|---|---|
| 1 | SC-1: TypeScript LSP autocomplete | PASS |
| 2 | SC-2: Python LSP autocomplete | PASS |
| 3 | SC-3: Encrypted connector auth tokens | PASS |
| 4 | SC-4: Goal lifecycle from editor context | PASS |
| 5 | SC-5: High-risk step blocks for approval | PASS |
| 6 | SC-6: Real-time governance for AI edits | PASS |
| 7 | SC-7: End-to-end RTAE loop | PASS |
| 8 | SC-8: Tamper-evident audit log | PASS |
| 9 | SC-9: No raw secrets in logs/DOM/AI context | PASS |
| 10 | SC-10: < 3 second startup | PASS |
| 11 | SC-11: < 500 MB memory baseline | PASS |
| 12 | SC-12: Full offline capability | PASS |

**If gate fails**: If 10+ SC pass and the failures are minor (e.g., startup is 3.5s instead of 3.0s), launch as V0 with known issues documented. If fewer than 10 SC pass, do not launch -- the product is not ready. Identify the critical path to fixing the failures and estimate the additional time required.

---

## 7. Team/Resource Assumptions

### Primary Resourcing

- **Solo developer + Claude Code as AI pair**: The plan assumes one full-time developer using Claude Code for code generation, debugging, architecture review, and test writing. This is not a limitation -- it is the intended development model for the SCBE IDE, which is itself a governance-first AI-paired development tool.

### Time Allocation

| Activity | Hours/Week | Notes |
|---|---|---|
| Feature development | 30 | Core coding and integration |
| Testing (manual + automated) | 6 | Writing and running tests |
| Code review / AI pair review | 2 | Reviewing Claude Code output |
| Documentation | 2 | Inline docs, README updates |
| **Total** | **40** | Standard work week |

### Where Additional Help Would Accelerate

| Area | Phase | Impact of Additional Person | Skills Needed |
|---|---|---|---|
| **UI/UX design** | Phase 1-2 | Panel layouts, connector form design, governance panel visual design. Currently developer-designed, which risks poor UX. A designer for 2-3 weeks in Phase 1-2 would significantly improve the first impression. | Figma, desktop app design, dark theme design |
| **Security review** | Phase 2, 4 | Vault crypto implementation review (Week 6) and full security audit (Week 11). A second pair of eyes on crypto code is always valuable. | Node.js crypto, AES-GCM, HKDF, Electron security model |
| **QA / cross-platform testing** | Phase 4 | Testing on multiple Windows 11 configurations, macOS versions, and edge cases. Solo developer can only test on their own machines. | Windows 11, macOS, systematic testing, accessibility |
| **SCBE backend stabilization** | Phase 2-3 | If the SCBE backend endpoints change during Phase 2-3, a backend developer maintaining API stability would prevent integration churn. | FastAPI, Express, SCBE architecture |

### Parallelizable Work Streams

If a second developer were available, these streams can run in parallel:

| Stream A (Primary Developer) | Stream B (Second Developer) | Weeks |
|---|---|---|
| Electron shell + Monaco (Weeks 1-3) | CI pipeline + build system + installer configuration | 1-3 |
| Governance panel + WebSocket (Week 4) | Connector manager UI (Week 5) | 4-5 |
| AI chat panel (Week 7) | Multi-agent configuration UI (Week 10) | 7, 10 |
| RTAE loop (Week 9) | Automated test suite for SC-1 through SC-12 (Weeks 9-10) | 9-10 |
| Security audit (Week 11) | Cross-platform testing (Week 12) | 11-12 |

---

## 8. Tech Debt Budget

### Acceptable Shortcuts in V0

These are deliberate trade-offs to meet the 90-day timeline. Each has a documented remediation plan for V1.

| Shortcut | Rationale | V1 Remediation |
|---|---|---|
| **No extension/plugin API** | V0 is a closed system. Extension governance (Safe Extension Gate) is a differentiator but building the full extension host, sandboxing, and manifest system is 4-6 weeks of work. | V1: Build extension host with SCBE governance gates. Extension manifest format, signed manifests, turnstile resolution. |
| **No custom keymap editor** | Ship one default keymap. Custom keymaps are a polish feature. | V1: JSON-based keymap configuration with UI editor. |
| **No vim/emacs mode** | Nice-to-have, not core value prop. | V1: Monaco vim/emacs extension integration. |
| **No minimap** | Monaco supports it but it adds visual complexity. | V1: Toggle-able minimap. |
| **No inline diff view** | Use terminal `git diff`. Building a diff UI takes 1-2 weeks. | V1: Monaco inline diff for file comparison and git changes. |
| **No Git UI** | Terminal is sufficient. Git UI (staging, commit, branch) is 2-3 weeks. | V1: Git panel with staging, commit, branch, push/pull. |
| **No debugger** | Out of scope per MVP_SPEC. DAP integration is 3-4 weeks. | V2: Debug Adapter Protocol integration. |
| **Single-window only** | No multi-window, no detachable panels. | V1: Detachable panels. V2: Multi-window. |
| **Ad-hoc code signing** | Proper code signing certificates cost money and take time to acquire. | V1: EV code signing certificate for Windows, Apple Developer ID for macOS. |
| **No auto-updater** | Manual download for V0. Auto-update is 1 week but requires code signing. | V1: electron-updater with differential updates. |
| **REST polling fallback for governance** | If WebSocket is unreliable, fall back to 5-second polling. Polling at 5s is not "real-time" but is acceptable for V0. | V1: Robust WebSocket with message queuing, guaranteed delivery, and offline buffer. |
| **In-memory chat history** | AI chat history lost on restart. Persistence requires encrypted storage design. | V1: Encrypted chat history persisted to disk, searchable. |
| **Manual agent selection** | No automatic routing of queries to the best agent. User picks from dropdown. | V1: Intent classification that auto-routes to the appropriate agent. |
| **No workspace settings sync** | Settings are per-machine only. | V2: Encrypted settings sync via SCBE sealed envelopes. |

### MUST Be Done Right the First Time

These items have no acceptable shortcut. Getting them wrong in V0 creates security vulnerabilities, data corruption, or trust erosion that cannot be patched retroactively.

| Item | Rationale | Standard |
|---|---|---|
| **Vault encryption (AES-256-GCM)** | Secrets stored incorrectly are a CVE. There is no "temporary plaintext" option. IV must be random per encryption. HKDF must use unique salt. Key must be derived from master password, never stored. | Follow SCBE `src/crypto/envelope.ts` patterns. Property-based tests for round-trip correctness. Manual security review. |
| **Audit trail hash chain (SHA-256)** | A broken hash chain makes the audit trail worthless. If V0 ships with a broken chain, all early audit data is unverifiable and trust is permanently damaged. | Each entry references previous entry's hash. Tamper detection on every read. Automated test for chain integrity on every CI run. |
| **Governance gate enforcement** | If agent actions bypass the governance gate even once, the entire value proposition collapses. "Governance-first" means governance-always. | Every agent action (file read, file edit, terminal command, connector dispatch) MUST go through `POST /v1/govern` before execution. No exceptions. No "fast path" that skips governance. |
| **Secret redaction in AI context** | If a raw API key is sent to an AI provider, it is compromised permanently. There is no "oops, let me fix that" for leaked secrets. | Exact-match scan against all vault values before every AI API call. Automated test (SC-9) that stores known test values and verifies zero leakage. |
| **Electron security configuration** | `contextIsolation: false` or `nodeIntegration: true` is a remote code execution vulnerability. These must be correct from the first commit. | `contextIsolation: true`, `sandbox: true`, `nodeIntegration: false` in every BrowserWindow. Enforced by a unit test that reads the window creation code and asserts these values. |
| **IPC channel whitelist** | An open IPC channel in Electron is equivalent to an open port. The renderer must only access declared channels. | Define all IPC channels in `src/shared/ipc-channels.ts`. Preload script only exposes these channels. Main process validates incoming channel names. |

### Deferred to V1 or V2

| Item | Target Version | Estimated Effort | Dependency |
|---|---|---|---|
| Tauri + CodeMirror 6 migration | V2 | 12-16 weeks | V1 stable, product-market fit validated |
| Extension marketplace | V2 | 8-10 weeks | Extension API (V1), signed manifests, Safe Extension Gate |
| Extension API / plugin system | V1 | 4-6 weeks | V0 stable |
| Real-time collaboration | V2 | 8-12 weeks | CRDT/OT engine, WebSocket infrastructure |
| Custom themes | V1 | 1-2 weeks | Theme engine abstraction |
| SSO / OAuth | V1 | 2-3 weeks | Auth service, enterprise requirements |
| Cloud deployment / hosted version | V2 | 12-16 weeks | Tauri migration, WebSocket infrastructure |
| Mobile companion | V2+ | 8-12 weeks | Responsive UI, mobile auth |
| Debugger (DAP) | V2 | 3-4 weeks | Debug Adapter Protocol integration |
| Post-quantum sealed envelopes (ML-KEM-768) for vault | V1 | 2-3 weeks | liboqs bindings or pqcrypto npm package |
| Automatic agent routing (intent classification) | V1 | 2-3 weeks | Multi-agent framework, intent classifier model |
| Telemetry dashboard | V1 | 2 weeks | Opt-in telemetry framework, privacy policy |
| Database viewer | Never (out of scope) | -- | Not an admin tool |

---

*This plan should be reviewed at each Go/No-Go gate. If a gate fails, re-scope before proceeding. The 90-day timeline is a constraint, not a suggestion -- if the plan cannot be met, reduce scope (cut features from F7 multi-agent first, then F5 web research, then F3 quick-connect templates), never extend the timeline.*
