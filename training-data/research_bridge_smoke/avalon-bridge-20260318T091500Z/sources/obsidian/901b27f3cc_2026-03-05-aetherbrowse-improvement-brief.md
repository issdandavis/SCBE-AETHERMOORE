# AetherBrowse Improvement Brief (Research + Local Context)

Date: 2026-03-05
Target: Local AetherBrowse stack in this repo (`src/browser`, `kindle-app`, `scripts/system`)

## Primary Inputs

- arXiv: Treating Web Navigation as a Branching Process for LLM-based Agents (MCTS framing)
  - https://arxiv.org/abs/2402.13718
- arXiv: Efficient LLM Web-Agent with Agentic Workflow
  - https://arxiv.org/abs/2402.05930
- arXiv: Agent S2 (computer-use/web-agent execution emphasis)
  - https://arxiv.org/abs/2508.05572
- Notion context page:
  - `313f96de-82e5-810c-895c-e2c44a8e0b18`
  - "AI Operator README — System Context for Claude & ChatGPT"
  - Key local constraints: branch-first workflow, audited artifacts, governance-first execution

## Upgrade Targets For Local Browser

1. Planner quality for multi-step navigation
- Add explicit branch scoring on candidate action paths before execution.
- Integrate bounded lookahead for ambiguous pages (2-3 step horizon).

2. Sidepanel assistance quality
- Add a deterministic sidepanel output contract:
  - page_summary
  - intent
  - next_actions (ranked)
  - risk tier
  - required approvals

3. Governance precision
- Keep low-risk read actions in fast lane.
- Escalate write/side-effect actions to deliberate lane with explicit reason.

4. Packaging reliability
- Remove hidden build assumptions (missing source path, missing TypeScript, shell incompatibility).
- Fail fast with actionable preflight checks.

## Applied In This Session

- Added AetherBrowse variant packaging support in `kindle-app/capacitor.config.ts`.
- Added AetherBrowse build scripts in `kindle-app/package.json`.
- Hardened `kindle-app/scripts/copy-pwa-assets.js` with source-root fallback.
- Added one-command packaging script:
  - `scripts/system/package_aetherbrowse_appstore.ps1`
  - includes artifact + SHA256 release manifest output.

## Remaining Blocker

- Local environment needs JDK configured:
  - `JAVA_HOME` must point to a valid JDK (`bin/java.exe`).

Once set, rerun:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/package_aetherbrowse_appstore.ps1 -Format aab -Store play -SkipInstall
```

## Recommendation

- Ship first as Android AAB (Play internal test track), then Amazon APK.
- Keep one codebase and one release manifest schema for both stores.
