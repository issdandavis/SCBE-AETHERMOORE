# OpenClaw + MoltbotDen Deep Research + SCBE Execution Plan (2026-02-27)

## Scope

This review covers:

- OpenClaw/Moltbot external mechanics (growth, architecture, automation, skills, security).
- SCBE local state across Obsidian, Notion, Hugging Face, n8n, Playwright, GitHub Actions, and hooks.
- A concrete plan to match or outperform OpenClaw while advancing SCBE toward a true LLM training loop.

---

## Verified OpenClaw/Moltbot Findings

### 1) Why OpenClaw grew fast

1. It optimized onboarding friction: one CLI wizard (`openclaw onboard`) and clear quick-start paths.
2. It ships wide channel coverage out of the box (WhatsApp/Telegram/Discord/Slack/etc.) from one gateway.
3. It has built-in proactive automation (`cron`) and event hooks, not just request/response chat.
4. It built a public distribution layer for capabilities (`ClawHub`) with CLI install/update/publish loops.
5. It publishes frequently and keeps visible release velocity.

### 2) Mechanisms worth copying

1. Public skill registry lifecycle:
   - Search, install, update, sync, publish from CLI.
   - Version tags and lockfile semantics.
2. Scheduler architecture:
   - Persistent cron jobs and run logs.
   - Isolated job sessions + delivery modes (`announce`, `webhook`, `none`).
3. Hook architecture:
   - Discovery from workspace/user/bundled hook paths.
   - Event-triggered scripts for command and lifecycle automation.

### 3) Security posture and caution

1. Documented advisory exists for token exfiltration leading to gateway compromise (`GHSA-g8p2-7wf7-98mq`, Jan 31, 2026).
2. OpenClaw’s own trust model explicitly treats authenticated gateway callers/plugins as trusted operators (important when comparing governance goals).
3. ClawHub codebase includes VirusTotal moderation/scanning logic, but open skill ecosystems remain a high-risk surface by default.

---

## SCBE Current State (Local + Live)

### Obsidian

1. Vaults discovered:
   - `C:\Users\issda\Documents\Avalon Files`
   - `C:\Users\issda\OneDrive\Documents\DOCUMENTS\A Folder`
   - `C:\AVALON BOOK SHIT\Izack Realmforge`
2. Notes already track:
   - n8n + Playwright swarm integration.
   - GitHub runner activation and workflow handoff logs.
   - Notion ingest + training-data sync patterns.

### Notion

1. Workspace bot connectivity is active via MCP.
2. Key pages exist and are aligned with current architecture:
   - OpenClaw gap analysis page.
   - GeoSeed architecture page (F1/F2/F3 tiering).

### Hugging Face

1. Public artifacts verified:
   - Dataset: `issdandavis/scbe-aethermoore-datasets`.
   - Models: `issdandavis/spiralverse-ai-federated-v1`, `issdandavis/phdm-21d-embedding`.
   - Space: `issdandavis/SCBE-AETHERMOORE-Demo` (currently sleeping).
2. CLI auth status locally:
   - `hf auth whoami` -> not logged in.

### GitHub Actions and hooks (repo state)

1. Strong CI automation surface already exists (`.github/workflows` contains Notion sync, notion-to-dataset, HF sync, connector health, self-improvement loop, etc.).
2. No repo-local `.githooks` directory is currently present.
3. `gh auth status` shows invalid token locally (automation that relies on local `gh` needs re-auth).

### n8n + bridge + Playwright (live runtime checks)

1. `http://127.0.0.1:8001/health` is up (SCBE n8n bridge healthy).
2. `http://127.0.0.1:8011/health` is up (browser worker service reachable, but `browser_ready=false`).
3. `http://127.0.0.1:5678/healthz` is up (n8n healthy).
4. `POST /v1/governance/scan` works and returns governed decisions.
5. `POST /v1/buffer/post` works (mock publish path successful).
6. `POST /v1/agent/task` accepts tasks, but test task remained `running` without completion.
7. n8n workflow `scbe-notion-github-swarm` webhook endpoint is not registered (workflow file exists but active import/activation mismatch).

---

## Gap vs OpenClaw (Practical, Not Theoretical)

1. SCBE already has deeper governance and orchestration primitives.
2. OpenClaw currently wins on externalized product loops:
   - Frictionless public capability distribution (marketplace UX + CLI habit loops).
   - Always-on autonomous cadence from scheduler/hooks deeply integrated into user workflows.
   - Public network effects around agent discovery/social coordination.
3. SCBE’s main execution gaps are packaging and operational coherence, not core capability.

---

## How SCBE Can Do Similar or Better

### Phase 1 (next 7-14 days): close operational gaps

1. Fix bridge/browser execution drift:
   - Diagnose why `v1/agent/task` remains `running` when browser worker reports `browser_ready=false`.
   - Align bridge OpenAPI/runtime with repo spec (`/v1/integrations/*` divergence).
2. Activate/import missing n8n research workflow:
   - Ensure `notion_github_swarm_research.workflow.json` is imported and active in n8n.
   - Add a smoke-test script that verifies webhook registration after startup.
3. GitHub reliability:
   - Repair local `gh` auth and validate workflow dispatch path.
4. Add repo hooks for quality gates:
   - Create `.githooks/pre-commit` and `.githooks/pre-push` for policy checks, schema validation, and workflow lint.

### Phase 2 (2-6 weeks): build growth loops OpenClaw uses, with SCBE governance

1. Launch SCBE skill registry workflow:
   - Public index + signed manifests + governance verdict per skill.
   - Mandatory scanning and deny/allow policy before publish.
2. Turn your existing Notion/Obsidian/HF path into a deterministic data flywheel:
   - Notion -> normalized markdown/jsonl -> HF dataset PR -> eval gate -> publish.
3. Add recurring “heartbeat” jobs:
   - n8n + cron + GitHub Actions for daily ingest, evaluation, and community-facing outputs.

### Phase 3 (6-16 weeks): grow toward a real LLM program

1. Establish a training ladder:
   - SFT baseline on curated SCBE corpora.
   - Preference tuning (DPO/ORPO) on governance-graded trajectories.
   - Distillation and eval loops for deployment variants.
2. Build hard eval gates:
   - Governance adherence, security regression tests, tool-use reliability, and data quality metrics.
3. Keep “model growth” tied to governed data generation:
   - Every training sample should have provenance + policy outcome + confidence metadata.

---

## Immediate GitHub + Hooks Plan

1. Add `openclaw-competitive-intel.yml`:
   - Scheduled workflow to fetch OpenClaw releases/advisories/docs diffs and open a research issue/PR summary.
2. Add `.githooks/pre-commit`:
   - Validate workflow YAML, JSON schema for n8n workflows, and deny secrets/prompt-injection artifacts.
3. Add `.githooks/pre-push`:
   - Run minimal governance smoke tests and block pushes when bridge/router health checks fail.
4. Add `scripts/system/smoke_n8n_bridge.ps1`:
   - Verify bridge health, browser worker health, n8n webhook registration, and one short end-to-end task completion.

---

## Hosting and Deployment Guidance (How to Run OpenClaw in SCBE)

- OpenClaw is practical to run in self-hosted environments:
  - Single VM (Hetzner/AWS/GCP) for full control over connectors, keys, and data residency.
  - Docker compose or process supervisor patterns for gateway + skills + database.
- For a scalable production path:
  - Put gateway + n8n + bridge on one trusted network segment.
  - Store all API keys in secret management (env file + encrypted volume / secret service).
  - Isolate browser automation in a least-privilege container profile.
- For experimentation and demos:
  - Google Colab works for short-lived model tests and notebooks.
  - Colab is not suitable for always-on gateway/webhook and multi-hour agent runtime.

## 10-Agent Research Stack Blueprint

To match the requested split of 10 agents:

1. 3 research depth agents (`research-scout-1..3`) for broad retrieval and source grounding.
2. 1 short-term research agent (`research-fast-check`) for fast contradiction and freshness checks.
3. 3 synthesis agents (`synthesis-lead`, `synthesis-editor`, `synthesis-review`) for evidence fusion and writing.
4. 1 connector-health agent (`ops-health`) for OpenClaw gateway, n8n, browser, and bridge telemetry.
5. 1 registry/policy agent (`policy-safety`) for key usage constraints, prompt safety, and governance scoring.

Recommended execution order:
- Wave 1: concurrent retrieval and policy pre-filter.
- Wave 2: synthesis + contradiction scoring.
- Wave 3: publication handoff (`Notion`, `Obsidian`, `Hugging Face`) with artifact checks.

---

## Source Evidence

### OpenClaw / ClawHub

1. https://github.com/openclaw/openclaw
2. https://api.github.com/repos/openclaw/openclaw
3. https://api.github.com/repos/openclaw/openclaw/releases?per_page=3
4. https://raw.githubusercontent.com/openclaw/openclaw/main/README.md
5. https://raw.githubusercontent.com/openclaw/openclaw/main/docs/automation/cron-jobs.md
6. https://raw.githubusercontent.com/openclaw/openclaw/main/docs/automation/hooks.md
7. https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/clawhub.md
8. https://github.com/openclaw/openclaw/security/advisories/GHSA-g8p2-7wf7-98mq
9. https://raw.githubusercontent.com/openclaw/openclaw/main/SECURITY.md
10. https://api.github.com/repos/openclaw/clawhub
11. https://raw.githubusercontent.com/openclaw/clawhub/main/README.md
12. https://api.github.com/repos/openclaw/clawhub/contents/convex/vt.ts

### MoltbotDen

1. https://api.moltbotden.com/openapi.json
2. https://www.moltbotden.com/skill.md
3. https://www.moltbotden.com/

### SCBE local/runtime

1. Local repo workflows and scripts under `C:\Users\issda\SCBE-AETHERMOORE`
2. Local runtime checks:
   - `http://127.0.0.1:8001/health`
   - `http://127.0.0.1:8011/health`
   - `http://127.0.0.1:5678/healthz`
3. Notion pages:
   - OpenClaw gap analysis page id `313f96de-82e5-8165-9ff8-c8b65e4ae24a`
   - GeoSeed page id `313f96de-82e5-81e1-ad61-d3d711140391`
4. Hugging Face APIs/pages:
   - `issdandavis/scbe-aethermoore-datasets`
   - `issdandavis/spiralverse-ai-federated-v1`
   - `issdandavis/phdm-21d-embedding`
   - `issdandavis/SCBE-AETHERMOORE-Demo`
