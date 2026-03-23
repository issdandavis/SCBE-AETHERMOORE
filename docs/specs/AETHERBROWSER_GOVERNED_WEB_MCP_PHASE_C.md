# AetherBrowser Governed Web MCP Phase C

## Goal

Ship useful governed web tools this week by exposing existing SCBE browser primitives through the MCP orchestrator first, then build the full browser shell on top of the same contracts.

This is Phase C:

1. MCP server first
2. Browser shell second
3. Training flywheel from accepted governed traces only

## Existing Seams Reused

- `mcp/orchestrator.py`
  Unified FastMCP surface with SFT logging on every tool call.
- `src/aetherbrowser/hyperlane_py.py`
  Python HyperLane zone classifier and ALLOW/DENY/QUARANTINE gate.
- `agents/antivirus_membrane.py`
  Prompt-injection and malware-style membrane scan with deterministic browser actions.
- `src/browser/toolkit.py`
  Cheap `httpx` search, extract, diff, and JS-detection primitives.
- `scripts/agentic_web_tool.py`
  HTTP plus Playwright capture helper with artifact emission.
- `src/browser/research_funnel.py`
  Existing research-to-intake/HF/Notion deposit lane.
- `src/browser/hydra_hand.py` and swarm browser lanes
  Browser-heavy phase 2 path when deterministic fetch is no longer enough.

## Phase C Tool Surface

Expose four cheap governed tools from the orchestrator:

- `web_search(query, num_results=8, agent_id="KO")`
- `web_fetch(url, engine="auto", agent_id="AV")`
- `web_extract(url, pattern, agent_id="AV")`
- `web_needs_js(url, agent_id="AV")`

These are deliberately read-only. They are meant to replace dead fetch/search lanes without immediately mixing in click or form-mutation behavior.

## Routing Rules

### 1. Governance First

Every tool call must pass HyperLane before any network work:

- `GREEN`
  Auto-allow read/search.
- `YELLOW`
  Auto-allow read/search, quarantine writes.
- `RED`
  Quarantine all operations in phase C.

Search engines are explicitly treated as `YELLOW`, not `GREEN`.

### 2. Cheapest Backend First

Use heuristics before model calls:

- search and simple extraction: `src/browser/toolkit.py`
- page capture: `scripts/agentic_web_tool.py`
- only route to full browser automation in later phases when:
  - JS dependency is detected
  - a login/session flow is required
  - a click/scroll/form path is required

### 3. Membrane Second

After content comes back:

- scan with `agents/antivirus_membrane.py`
- map threat score into browser turnstile action
- release content only if membrane action is `ALLOW`
- keep quarantined artifacts on disk, but do not release them into model context automatically

## Data Capture Policy

Allowed to capture for SFT:

- task
- chosen tool
- backend used
- zone decision
- membrane verdict
- success/failure
- accepted result preview

Do not capture automatically:

- credentials
- cookies
- auth headers
- bank/account pages
- quarantined raw content
- arbitrary sensitive HTML dumps

## Phase 2

Once the MCP primitives are stable:

- add `web_browse` over Playwright/CDP/HYDRA
- keep the same governance contract
- feed accepted research traces to `src/browser/research_funnel.py`
- render the browser shell over the same backend contracts instead of creating a separate stack

## Acceptance Criteria

- MCP orchestrator exposes the four governed web tools.
- Tool calls log into existing SFT flow.
- RED-zone fetches are blocked or quarantined.
- Search results include per-result zone annotation.
- Capture artifacts land under `artifacts/`.
- Targeted tests cover registration and basic governance behavior.
