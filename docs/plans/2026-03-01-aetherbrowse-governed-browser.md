# AetherBrowse — SCBE-Governed AI Browser

**Date:** 2026-03-01
**Status:** Architecture Design
**Goal:** Build a Comet/Atlas-class AI browser with SCBE governance at half the price

## Product Vision

AetherBrowse is an Electron desktop app embedding a real Chromium view, driven by SCBE-governed AI agents. Every click, navigation, and form fill passes through the 14-layer security pipeline. Multiple AI agents collaborate via the DM protocol to complete complex multi-step tasks.

**Target pricing:** $29-199/month (vs Perplexity Computer at $200/month)
**Key differentiator:** Governance is a first-class feature, not an afterthought.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  AetherBrowse (Electron + React)                        │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Tab Bar      │  │  Agent Panel │  │  SCBE Log    │  │
│  │  (Chromium)   │  │  (Sidebar)   │  │  (Bottom)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │          │
│         ▼                  ▼                  ▼          │
│  ┌─────────────────────────────────────────────────────┐│
│  │              IPC Bridge (Electron Main)              ││
│  └──────────────────────┬──────────────────────────────┘│
└─────────────────────────┼───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              SCBE Agent Runtime (Python)                 │
│                                                         │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────────┐ │
│  │ Perceiver │  │  Planner  │  │  Governance Gate     │ │
│  │ (DOM→LLM) │  │  (LLM)   │  │  (14-layer pipeline) │ │
│  └────┬─────┘  └─────┬─────┘  └──────────┬───────────┘ │
│       │               │                    │             │
│       ▼               ▼                    ▼             │
│  ┌──────────────────────────────────────────────────┐   │
│  │            OctoArmor Router (11+ LLMs)            │   │
│  │   Perception→Gemini  Planning→Claude  Speed→Grok  │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│                          ▼                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Browser Worker (Playwright/Pydoll)        │   │
│  │   navigate, click, type, upload, screenshot       │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Process Architecture

### 1. Electron Main Process
- Window management (tabs, sidebar, bottom panel)
- IPC bridge between React renderer and Python agent runtime
- Local file access for DM threads, governance logs, training data

### 2. React Renderer (UI)
- **Main pane**: BrowserView/WebView — real Chromium rendering
- **Left sidebar**: Tab list + active agents + status indicators
- **Bottom panel**: SCBE event log + step plan viewer
- **Command bar**: Natural language input ("search for X", "fill this form", "buy the cheapest one")

### 3. Python Agent Runtime (FastAPI WebSocket)
- Runs as a local subprocess or sidecar
- Communicates with Electron via WebSocket on localhost
- Hosts: Perceiver, Planner, Executor, Governance Gate, OctoArmor Router
- Manages DM threads for multi-agent collaboration

### 4. Browser Worker (Playwright)
- Controlled by the Agent Runtime
- Drives the embedded Chromium view via CDP (Chrome DevTools Protocol)
- Sends DOM snapshots to Perceiver, receives action commands from Executor

## Agent Loop (Core Runtime)

```
┌──────────────────────────────────────────────────────┐
│                    Agent Loop                         │
│                                                      │
│  1. PERCEIVE                                         │
│     └─ DOM snapshot → extract elements + state       │
│     └─ Route to perception model (Gemini Flash)      │
│     └─ Output: structured page understanding         │
│                                                      │
│  2. PLAN                                             │
│     └─ Page understanding + user goal → next steps   │
│     └─ Route to planning model (Claude Opus)         │
│     └─ Output: ordered list of actions               │
│                                                      │
│  3. GOVERN                                           │
│     └─ Each planned action → SCBE 14-layer check     │
│     └─ Sacred Tongue classification                  │
│     └─ Output: ALLOW / QUARANTINE / DENY per action  │
│                                                      │
│  4. EXECUTE                                          │
│     └─ Allowed actions → Playwright commands         │
│     └─ Each execution → audit log + training pair    │
│     └─ Output: action results + updated DOM          │
│                                                      │
│  5. REPEAT until goal complete or governance halts   │
└──────────────────────────────────────────────────────┘
```

## Module Map

```
aetherbrowse/
├── package.json                    # Electron + React deps
├── electron/
│   ├── main.ts                     # Electron main process
│   ├── preload.ts                  # IPC bridge
│   └── ipc.ts                      # WebSocket ↔ IPC adapter
├── renderer/
│   ├── App.tsx                     # Root React component
│   ├── components/
│   │   ├── TabBar.tsx              # Browser tab management
│   │   ├── BrowserPane.tsx         # Embedded Chromium view
│   │   ├── AgentSidebar.tsx        # Agent status + controls
│   │   ├── CommandBar.tsx          # Natural language input
│   │   ├── GovernanceLog.tsx       # SCBE event stream
│   │   └── StepPlanViewer.tsx      # Current plan visualization
│   └── styles/
├── runtime/                        # Python agent runtime
│   ├── server.py                   # FastAPI WebSocket server
│   ├── agent_loop.py               # PERCEIVE → PLAN → GOVERN → EXECUTE
│   ├── perceiver.py                # DOM snapshot → structured understanding
│   ├── planner.py                  # Goal + context → action plan
│   ├── executor.py                 # Plan → Playwright commands
│   ├── governance.py               # SCBE 14-layer gate wrapper
│   └── dm_thread.py                # Multi-agent DM protocol
├── worker/
│   ├── browser_worker.py           # Playwright browser control
│   ├── dom_extractor.py            # a11y tree + visual extraction
│   └── action_executor.py          # Click, type, navigate, upload
└── config/
    ├── governance_policies.yaml    # Default governance rules
    └── model_routing.yaml          # OctoArmor model assignments
```

## Key Integration Points

### OctoArmor (already built: src/fleet/octo_armor.py)
- 11 providers ready (Groq, Cerebras, Google AI, OpenRouter, Claude, xAI, GitHub Models, HuggingFace, Ollama, Google Vertex, Cloudflare)
- Route by task type: perception → fast/cheap, planning → smart/expensive, critique → different model
- FREE first routing already implemented

### SCBE Governance (already built: src/symphonic_cipher/)
- 14-layer pipeline, 5 quantum axioms, Sacred Tongue tokenizer
- Wrap every browser action: `governance_gate.evaluate(action) → ALLOW/DENY`
- Harmonic wall ensures adversarial actions cost exponentially more

### DM Protocol (newly designed: references/dm-protocol.md)
- Multi-agent sequenced collaboration on single tasks
- JSONL thread files as audit trail + training data source
- Governance gate on every handoff between agents

### NoticeBoard (already built: src/fleet/switchboard.py)
- Broadcast channel for agent status and availability
- Complements DM threads for discovery/coordination

### HydraHand (already built: src/browser/hydra_hand.py)
- 6-tongue Sacred Tongue browser squad
- Already has multi_action() and swarm_research()
- Becomes the browser_worker.py backend

### PollyVision (already built: src/browser/polly_vision.py)
- 3-tier observation: a11y tree, screenshots, Set-of-Marks
- Becomes the perceiver.py backend

## Build Timeline

### Week 1-2: Electron Shell + Basic Worker
- [ ] `npm init` Electron + React project in `aetherbrowse/`
- [ ] Embedded BrowserView showing real web pages
- [ ] Tab management (new tab, close tab, switch)
- [ ] Command bar: type URL → navigate
- [ ] Playwright worker: `go_to(url)`, `click(selector)`, `type(text)`
- [ ] IPC bridge: renderer ↔ main ↔ worker

### Week 3-4: SCBE Governance + Single LLM
- [ ] FastAPI WebSocket server (runtime/server.py)
- [ ] Perceiver: DOM snapshot → structured JSON via LLM
- [ ] Planner: "given this page + goal, what next?" via LLM
- [ ] Governance wrapper: log every action, basic allow/deny
- [ ] Bottom panel: governance event stream
- [ ] Agent sidebar: show active agent + current plan

### Week 5-6: Multi-Model + Multi-Agent
- [ ] OctoArmor integration: route perception/planning/critique to different models
- [ ] DM protocol: multiple agents collaborate on single task
- [ ] Background tasks: queue tasks, execute while user browses
- [ ] Saved workflows: record + replay browser macros
- [ ] Training data flywheel: every action → SFT pair

### Week 7-8: Polish + Ship
- [ ] Installer (electron-builder for Windows)
- [ ] Settings panel (API keys, governance policies, model preferences)
- [ ] Shopify/Gumroad product listing
- [ ] Landing page with competitive positioning
- [ ] Demo video: side-by-side vs Comet doing same task

## Competitive Comparison

| Feature | Comet (Free) | Perplexity Computer ($200/mo) | AetherBrowse ($99/mo) |
|---------|-------------|------------------------------|----------------------|
| Browser automation | Yes | Yes (sandboxed) | Yes (full Chromium) |
| Multi-model | Perplexity only | 19 models (their choice) | 11+ (your choice) |
| Governance per action | No | No | Yes (14-layer SCBE) |
| Audit trail | Basic | Basic | Immutable JSONL + hash chain |
| Privacy | All → Perplexity | All → Perplexity | Local-first |
| Multi-agent collab | Opaque sub-agents | Opaque sub-agents | Transparent DM protocol |
| Custom policies | No | No | YAML governance rules |
| Training data gen | No | No | Every action → SFT pair |
| Headless / CI mode | No | Background only | Full headless |
| File upload | Limited | Via sandbox | Full Playwright |
| Open source core | No | No | npm: scbe-aethermoore |
| Patent protection | No | Perplexity IP | USPTO #63/961,403 |

## Revenue Model

| Tier | Price | Features |
|------|-------|---------|
| **Free** | $0 | Single agent, 50 actions/day, local model only |
| **Pro** | $29/mo | Multi-agent, unlimited actions, 3 cloud models |
| **Team** | $99/mo | Full OctoArmor fleet, DM protocol, saved workflows |
| **Enterprise** | $199/mo | Custom governance, SSO, audit export, priority support |

## What Already Exists (Reusable)

| Component | Location | Status |
|-----------|----------|--------|
| OctoArmor (11 LLMs) | `src/fleet/octo_armor.py` | Ready |
| Switchboard + NoticeBoard | `src/fleet/switchboard.py` | Ready |
| HydraHand browser squad | `src/browser/hydra_hand.py` | Ready |
| PollyVision perception | `src/browser/polly_vision.py` | Ready |
| Fleet Coordinator | `agents/browser/fleet_coordinator.py` | Ready |
| SCBE Governance | `src/symphonic_cipher/` | Ready |
| AetherNet service | `src/aaoe/aethernet_service.py` | Ready |
| DM Protocol spec | `skills/hydra-clawbot-synthesis/references/dm-protocol.md` | Designed |
| Training pipeline | `scripts/` + `training-data/` | Ready |

**~70% of the backend is already built.** The main new work is the Electron UI shell and the agent loop glue code.
