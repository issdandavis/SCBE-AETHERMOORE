# AetherBrowser Mobile V1 Spec

Date: 2026-03-27
Status: Draft
Owner: Codex

## 1. Product Definition

AetherBrowser Mobile V1 is a browser-first mobile command center for the SCBE stack.

It is not a generic chatbot.

It is:

1. a normal mobile browser shell first
2. an AI sidecar and command surface second
3. a governed operator for web tasks third
4. a mobile control room for model panels, vault notes, and ops lanes fourth

The goal is to let Issac operate, inspect, and build the system from a phone without collapsing the product into a cluttered research dump.

## 2. Product Goal

Deliver a mobile app where a user can:

1. browse a live page
2. ask the sidecar about that page
3. get a structured plan
4. approve or reject risky actions
5. execute governed browser work
6. save results into vault, GitHub, or system artifacts

This follows the existing desktop AetherBrowser product definition:

- browser competence
- research competence
- action competence
- governance competence
- orchestration competence

## 3. V1 User

Primary user:

- Issac, as operator, builder, reviewer, and mobile admin

Secondary user later:

- trusted testers in internal or closed beta

V1 is not a public consumer browser.

## 4. Core V1 Principles

1. Browser first
- no landing directly into a blank chatbot

2. Sidecar centered
- chat is always aware of current page, session, and task

3. Governance visible
- risky actions must be legible and held when needed

4. Mobile-fast
- fast capture, fast inspect, fast act

5. Stable and canary split from day one
- public-safe lane and experimental lane must be separate

6. Small top-level IA
- 5 primary destinations max on phone

## 5. V1 Information Architecture

Use five top-level destinations.

### 1. Browse
- mobile browser shell
- tabs
- address bar
- current-page summary
- current-page evidence snapshot
- open in sidecar

### 2. Chat
- AI sidecar conversations
- page-aware chat
- repo-aware chat
- vault-aware chat
- provider/runtime indicator

### 3. Rooms
- model panel show / season engine
- host, analyst, skeptic, operator, judge roles
- transcript view
- scorecards
- export run

### 4. Vault
- notes
- manuals
- research packets
- saved transcripts
- evidence cards

### 5. Ops
- connectors
- provider health
- release lane switch
- profile and session controls
- export/sync actions

## 6. Navigation Pattern

Phone:

- top app bar
- bottom navigation with 5 items

Tablet / larger surfaces later:

- nav rail adaptation

Initial bottom tabs:

1. Browse
2. Chat
3. Rooms
4. Vault
5. Ops

## 7. V1 Screen Set

### Browse
- tab switcher
- address/search field
- page card with title, URL, trust/risk badge
- quick actions:
  - summarize
  - extract
  - snapshot
  - save to vault
  - open in room

### Chat
- conversation list
- current context chip:
  - page
  - repo
  - vault
  - none
- model/provider chip
- structured answer cards:
  - answer
  - evidence
  - action plan
  - approval required

### Rooms
- season list
- episode/run list
- role cards:
  - host
  - analyst
  - skeptic
  - operator
  - judge
- transcript timeline
- score and export actions

### Vault
- recent notes
- linked manuals
- saved browser evidence
- saved room transcripts
- search

### Ops
- runtime health
- connector states
- active profile
- stable/canary label
- sync status
- export buttons

## 8. AetherBrowser Runtime Mapping

V1 should not invent a separate browser brain.

It should map to the current repo surfaces:

- `agents/aetherbrowse_cli.py`
- `agents/browser/action_validator.py`
- `agents/browser/session_manager.py`
- `agents/browser/dom_snapshot.py`
- `scripts/system/browser_chain_dispatcher.py`
- `scripts/system/playwriter_lane_runner.py`

Mobile shell responsibilities:

1. call browser lane
2. render structured result
3. show governance decision
4. request approval when needed
5. persist artifacts

## 9. Chat Layer

The chat layer is not generic chat history.

It must support context modes:

1. page-aware chat
2. vault-aware chat
3. repo-aware chat
4. room-aware chat

Minimum response structure:

1. answer
2. evidence or source card
3. provider/runtime card
4. action card if applicable

## 10. Rooms Layer

Rooms are a first-class feature, not a gimmick.

### V1 Room Types

1. Research Desk
- host
- analyst
- skeptic
- operator
- judge

2. Red Team
- host
- attacker
- defender
- judge

3. Build Room
- host
- architect
- coder
- reviewer

### V1 Output

Each run should produce:

1. transcript
2. scorecard
3. winning summary
4. saved artifact

## 11. Vault Layer

V1 Vault should expose:

1. Obsidian/Avalon notes
2. manuals
3. research pages
4. saved browser evidence
5. saved room transcripts

V1 is read-first.

Write actions allowed:

1. save transcript
2. save browser snapshot
3. append note packet

## 12. Ops Layer

Ops must show state clearly.

Minimum cards:

1. active model provider lane
2. browser lane health
3. GitHub lane health
4. YouTube lane health
5. vault/sync health
6. build flavor:
  - stable
  - canary

## 13. Stable and Canary Strategy

This is mandatory in V1.

### Stable
- safer connector set
- fewer experimental flows
- internal release candidate path

### Canary
- experimental browser actions
- model-room experiments
- new connectors
- volatile UI

Recommended package IDs:

- `com.issdandavis.aetherbrowser`
- `com.issdandavis.aetherbrowser.canary`

If final naming uses `AetherCode`, preserve the same split.

## 14. Packaging Base

Use `kindle-app` as packaging base.

Why:

1. Capacitor already exists
2. Android build scripts already exist
3. AAB/APK lanes already exist
4. mobile packaging is already partially operational

Use `Omni-Heal-` as UI shell reference only.

Why:

1. it is a real AI Studio React/Vite app shell
2. it is not the authoritative product definition
3. AetherBrowser specs are the authoritative product definition

## 15. Backend and Connector Strategy

Do not use Proton Mail as the main runtime backend.

Use Proton for:

1. support
2. recovery
3. communications

Use system/backend lanes for:

1. browser actions
2. model routing
3. room orchestration
4. GitHub integration
5. vault/search access

Priority connectors for V1:

1. GitHub
2. Vault / local notes
3. browser lane
4. Ollama
5. Hugging Face
6. YouTube later in V1.x

## 16. Governance Requirements

Every state-changing action must show:

1. target
2. action
3. risk tier
4. governance result
5. approval requirement

V1 action decisions:

1. allow
2. hold
3. deny
4. reroute

## 17. Training and Feedback Hooks

V1 should generate reusable artifacts from:

1. browser actions
2. room transcripts
3. approved action plans
4. rejected risky steps

This must connect to:

- browser training traces
- vault exports
- eval packets

But V1 UI should not expose the full training pipeline complexity.

## 18. Out of Scope for V1

Do not include:

1. full public audience platform
2. custom user-uploaded model rooms
3. full enterprise policy administration
4. universal connector coverage
5. complex payments/subscriptions inside the app
6. desktop browser replacement claims

## 19. V1 Success Test

V1 succeeds when Issac can:

1. open the app on phone
2. browse to a live page
3. ask the sidecar for structured help
4. get a governed action plan
5. approve a safe step
6. save useful output to the vault
7. switch between stable and canary builds

## 20. Recommended Build Order

### Phase 1
- mobile IA
- bottom-nav shell
- Browse screen
- Chat screen shell

### Phase 2
- governed page summary
- browser evidence card
- action approval card

### Phase 3
- Rooms engine UI
- first season: Research Desk

### Phase 4
- Vault integration
- saved transcripts and evidence

### Phase 5
- Ops screen
- stable/canary packaging
- internal test release

## 21. Parallel Work Packet for Claude

While Codex owns product shape and app spec, Claude should produce the dependency packet:

1. Apollo integration brief
- what inbox, YouTube, and transcript surfaces belong in V1, V1.x, or later

2. Security brief
- which governance cards and approval states must be visible in mobile UI

3. Training brief
- which action traces and room transcripts should be exported in V1

4. Release brief
- what can safely ship in stable versus canary

Output target:

- `docs/specs/AETHERBROWSER_MOBILE_V1_INTEGRATION_PACKET.md`

This keeps the spec clean and keeps Claude from reshaping the product while Codex is doing the product architecture.
