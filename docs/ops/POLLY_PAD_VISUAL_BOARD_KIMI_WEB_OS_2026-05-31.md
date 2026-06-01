# Polly Pad Visual Board - Kimi Web OS Import Note

Date: 2026-05-31

Source archive:

`C:\Users\issda\OneDrive\SCBE_CLOUD_ARCHIVE\downloads-snapshot\20260524-090429\Downloads\Kimi_Agent_Web Linux OS Build.zip`

Archive size: `283442` bytes.

## What It Is

The archive is a Vite/React web OS source bundle under `app/`. It is not a Linux installer, AppImage, ISO, or `.deb` package.

Useful internal structure:

- `app/package.json`
- `app/src/App.tsx`
- `app/src/os/Desktop.tsx`
- `app/src/os/Window.tsx`
- `app/src/os/Taskbar.tsx`
- `app/src/os/StartMenu.tsx`
- `app/src/os/OSStore.tsx`
- `app/src/os/appRegistry.ts`
- `app/src/apps/Terminal.tsx`
- `app/src/apps/FileManager.tsx`
- `app/src/apps/GovernanceConsole.tsx`
- `app/src/apps/ExecutionTimeline.tsx`
- `app/src/apps/ApprovalGates.tsx`
- `app/src/apps/AuditLogs.tsx`
- `app/src/apps/MultiAgentTerminal.tsx`
- `app/src/apps/ModelRouter.tsx`

## Why It Fits Polly Pads

Polly Pads already exist as runtime/workspace concepts in:

- `src/polly_pads_runtime.py`
- `packages/polly-pad-cli/`
- `packages/polly-pad-py/`

The Kimi Web OS bundle can become the visual board layer for those runtimes:

- each Polly Pad becomes a desktop/workspace tile or window;
- active tasks become board cards;
- governance decisions become approval-gate panels;
- audit receipts become an audit-log app;
- agent messages and tool events become timeline rows;
- per-pad CLI/runtime calls become terminal or tool-console actions.

## Recommended Import Shape

Do not dump this into the MATHBAC proposal package. Keep it as SCBE product infrastructure.

Recommended target:

`apps/polly-pad-board/`

Recommended source import layout:

```text
apps/polly-pad-board/
  README.md
  package.json
  src/
    board/
      PadBoard.tsx
      PadWindow.tsx
      PadTaskCard.tsx
      PadAuditPanel.tsx
      PadApprovalPanel.tsx
    kimi-os-import/
      README.md
      copied-components.md
```

Keep provenance notes for copied/adapted Kimi files. The zip appears user-provided from the local archive; still mark it as imported source material until ownership/licensing is checked.

## First Useful Board

Build a quiet, dense operational board rather than a decorative fake OS.

Views:

- `Pads`: cards for active pad namespaces, mode, zone, tongue, current task, and governance state.
- `Timeline`: combined agent/tool/event stream.
- `Approvals`: REVIEW/ESCALATE/QUARANTINE actions needing user confirmation.
- `Audit`: receipts, hashes, run IDs, and export buttons.
- `Terminal`: scoped command surface for `polly-pad-cli`.

Data contract:

```ts
type PollyPadBoardState = {
  pads: Array<{
    id: string;
    name: string;
    mode: 'observe' | 'plan' | 'execute' | 'review';
    zone: 'private' | 'shared';
    tongue: string;
    status: 'idle' | 'running' | 'blocked' | 'review';
    activeTask?: string;
    lastReceipt?: string;
  }>;
  events: Array<{
    id: string;
    padId: string;
    ts: string;
    kind: 'message' | 'tool' | 'governance' | 'audit';
    summary: string;
    decision?: 'ALLOW' | 'REVIEW' | 'ESCALATE' | 'QUARANTINE' | 'DENY';
  }>;
};
```

## Integration Steps

1. Extract the zip into a scratch/import folder, not directly over existing app code.
2. Run `npm install` and `npm run build` inside extracted `app/` to confirm the source still builds.
3. Copy only the OS shell primitives needed for a board: desktop layout, window manager, taskbar/start menu if useful.
4. Replace toy app registry entries with Polly Pad apps: Pads, Timeline, Approvals, Audit, Terminal.
5. Wire local mock data first.
6. Add adapter calls to `packages/polly-pad-cli` / `packages/polly-pad-py` after the visual shell is stable.
7. Add a route from `apps/aether-desktop` only after the board has a working standalone build.

## Guardrails

- Do not include this in the MATHBAC BAAT zip.
- Do not wire live mail/OAuth/provider calls in the first board slice.
- Do not store secrets in board state.
- Keep all command execution scoped through existing Polly Pad governance/runtime surfaces.
- Keep imported Kimi files labeled until licensing/provenance is resolved.

## Next Engineering Move

Implemented first slice at:

`apps/polly-pad-board/`

This is now a standalone Vite/React app, not just an import plan. It does not copy the Kimi bundle over wholesale; it adapts the useful web-OS direction into a Polly Pad-specific operator board.

Current working surfaces:

- multi-screen board: Ops, Review, Build, Research;
- Polly Shell: visual command-line interface backed by real state mutations;
- Pads app: create/select pads, add/complete tasks, add notes;
- Approvals app: approve/deny gated route items;
- Virtual Files app: read/write/list browser-persisted files;
- Audit app: local receipt chain for state-changing actions;
- Timeline app: merged tasks, notes, and gate events;
- Route Builder app: stages workflow requests into review gates.
- Semantic Scanner app: local deterministic scan for injection, credential, shell, exfiltration, and governance-bypass language.

Current shell commands:

```text
help
screens
screen <ops|review|build|research>
pads
pad add <name>
pad use <id>
task add <text>
task done <id>
note add <text>
approval list
approval approve <id>
approval deny <id>
route <goal>
scan <text>
fs ls
fs read <path>
fs write <path> <text>
hash <text>
json <json>
calc <expr>
audit
export
```

Validation on 2026-06-01:

```text
npm --prefix apps/polly-pad-board install
npm --prefix apps/polly-pad-board run build
npm --prefix apps/polly-pad-board test
Invoke-WebRequest http://127.0.0.1:5198/ -> 200
Playwright desktop and mobile screenshots captured:
  polly-pad-board-desktop.png
  polly-pad-board-mobile.png
```

Local preview command:

```bash
npm --prefix apps/polly-pad-board run dev -- --host 127.0.0.1 --port 5198
```

Important boundary:

The browser board does not pretend to run host Linux shell commands. Host command execution needs a governed local bridge behind it, with explicit approvals, allowlisted operations, and audit receipts. The current Polly Shell is real for board state, VFS, approvals, route staging, hash, JSON, and arithmetic commands.
