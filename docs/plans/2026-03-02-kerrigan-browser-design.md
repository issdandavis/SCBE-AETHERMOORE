# Kerrigan Browser — Design Doc

**Date**: 2026-03-02
**Status**: Building

## What It Is

Kerrigan = AetherBrowse upgraded from demo to daily driver. An Electron browser
where the AI system lives, works, and earns money.

Starcraft metaphor: Playwright Chromium (zergling) + SCBE injection (Zerg swarm) = Kerrigan.

## What It Does (MVP)

1. **Home Dashboard** — Opens to a status page showing:
   - Service health (runtime, n8n bridge, AetherNet)
   - Task queue with action buttons
   - Revenue summary
   - Agent status (Kael/Aria/Zara/Polly)
   - Quick actions: post content, run workflow, open Notion, open GitHub

2. **Working Browser** — Tabs, URL bar, navigation (already built)

3. **Command Bar** — Tell agents what to do in natural language (already built, needs wiring)

4. **Governance Log** — See what the system decided and why (already built)

## Stack

- **Shell**: Electron 34 (existing `aetherbrowse/`)
- **Runtime**: FastAPI on port 8400 (existing `aetherbrowse/runtime/server.py`)
- **Home**: Local HTML dashboard served by runtime
- **Services**: n8n bridge (8001), AetherNet (8300)

## What Changes

| File | Change |
|------|--------|
| `aetherbrowse/electron/main.js` | Home URL → `http://localhost:8400/home` |
| `aetherbrowse/runtime/server.py` | Add `/home` dashboard endpoint + `/api/status` |
| `aetherbrowse/runtime/dashboard.html` | NEW — Kerrigan home page |
| `aetherbrowse/runtime/tasks.py` | NEW — Task queue (post, research, outreach) |

## Architecture

```
[Electron Shell]
    ├── BrowserView (tabs — web pages)
    ├── Sidebar (agent cards — live status)
    ├── Bottom Panel (governance log + command bar)
    └── Home Tab → localhost:8400/home
            ├── Service Status (health checks)
            ├── Task Queue (things to do)
            ├── Quick Actions (buttons that do things)
            └── Revenue Dashboard (money tracking)

[FastAPI Runtime :8400]
    ├── /ws (WebSocket to Electron)
    ├── /ws/worker (WebSocket to Playwright)
    ├── /home (dashboard HTML)
    ├── /api/status (service health)
    ├── /api/tasks (task CRUD)
    └── /api/action/{name} (trigger workflows)
```

## Future (Not MVP)

- Monaco editor panel (IDE)
- xterm.js terminal
- Git UI + release wizard
- Firebase browser
- Perplexity-style research (Polly does invisible browsing)
- Ternary pocket dimension workspaces
- Polyhedral navigation graph
