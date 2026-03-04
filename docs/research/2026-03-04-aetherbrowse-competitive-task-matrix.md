# AetherBrowse Competitive Task Matrix (Comet / Agent Side-Panel Browsers)

Date: 2026-03-04  
Owner: SCBE-AETHERMOORE

## Objective
Benchmark AetherBrowse against mainstream daily-use browsers and agent-enabled browser experiences (for example Comet-style side-panel AI) using repeatable, measurable tasks.

## Browser Set
- Chrome (stable)
- Edge (stable)
- Safari (stable, macOS)
- Firefox (stable)
- AetherBrowse (Electron shell + Aether runtime)

## Agent-Enabled Set
- AetherBrowse agent lane (runtime + worker)
- Comet (or nearest available side-panel competitor)
- Any browser-native assistant mode under test

## Core KPI Set
- Task success rate (%)
- Median completion time (seconds)
- P95 completion time (seconds)
- Human interventions required (count)
- Prompt turns required (count)
- Navigation errors (count)
- Anti-bot/captcha blocks (count)
- Cost per completed task (USD)
- Reproducibility across runs (% same outcome)

## Task Battery
1. Search + evaluate: find 3 relevant sources for a query, open each, and extract key points.
2. Multi-tab synthesis: keep 5 tabs open, compare content, return ranked summary with citations.
3. Form workflow: fill a multi-step web form with validation retries and error recovery.
4. Auth bootstrap: perform login flow with saved profile, then complete a post-login action.
5. Commerce admin action: create/update a product draft in Shopify admin (staging store).
6. Content posting prep: create a draft post in Medium/LinkedIn composer without publishing.
7. File workflow: upload a file, confirm upload state, download generated output.
8. Research pipeline: navigate from query to 10-source evidence pack JSONL output.
9. Session resilience: recover from forced refresh/crash and continue task context.
10. Side-panel usability: execute tasks while panel remains open and non-blocking.

## Side-Panel Agent UX Checks
1. Panel open/close latency.
2. Panel persistence across tabs.
3. Command context follows active tab.
4. Agent can target non-active tab when explicitly requested.
5. Inline action preview before execution.
6. Deterministic execution log and replayability.

## Multi-Engine + Roundtable Routing Checks
1. Engine select latency: switch between roundtable, DuckDuckGo, and Bing under 300ms UI response.
2. Search parity: same query across roundtable/DDG/Bing returns >= 5 usable links each.
3. Source diversity: roundtable mode returns at least 2 distinct source families (web + specialist links).
4. Router continuity: switch tabs during search and confirm agent still routes to intended lane.
5. Cross-talk handoff: leader agent assigns a search task, worker agent executes, observer logs with timestamps.
6. Failure fallback: force one engine failure and verify fallback links return without hard error.
7. Cost gate: route expensive calls only when free/public engines fail quality threshold.

## Security/Governance Checks
1. Secret use only from vault/env alias, never plaintext in logs.
2. Risky actions require explicit governance signal.
3. Action audit trail includes timestamp, target URL, command, result hash.
4. Sensitive domain profile separation (work/personal/admin).

## Performance Pass/Fail Gates
- >= 90% success rate on core battery.
- <= 1 human intervention median per task.
- <= 15s median for search+summarize task.
- <= 5% captcha hard-fail on repeated runs with valid profile.
- >= 95% reproducibility for deterministic workflows.

## Immediate Next Runs
1. Daily smoke on Aether landing/search across Chromium/Firefox/WebKit.
2. Weekly battery against Chrome + Edge + Safari manual baseline.
3. Weekly side-panel comparison run against Comet-equivalent tasks.

## Artifacts
- JSON benchmark output: `artifacts/aetherbrowse_benchmark/latest_smoke.json`
- Screenshots per browser: `artifacts/aetherbrowse_benchmark/<timestamp>/`
