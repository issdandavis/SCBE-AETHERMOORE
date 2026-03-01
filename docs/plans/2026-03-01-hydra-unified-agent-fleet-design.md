# HYDRA Unified Agent Fleet — Design Document

**Date**: 2026-03-01
**Status**: Approved
**Scope**: Full browser interaction + multi-agent orchestration + connector bridge

## Problem

We have three disconnected browser/agent layers:
1. `headless.py` — read-only research browser (httpx + Playwright fetch)
2. `browser_agent.py` — governance skeleton with stub actions (no real browser)
3. `hydra_hand.py` — 6-finger Playwright squad, navigate/extract only (no click/type/fill)

And a connector system (10 kinds in `main.py`) that doesn't talk to the browser layer.

**Result**: AI can read the web but can't interact with it. Connectors and browser work independently.

## Solution: Two-Sided Unified Agent

### Principle
Every task gets attacked from both sides:
- **Connector side** (API): Fast, structured, reliable for supported services
- **Browser side** (Playwright): Universal fallback, handles anything a human can

Both run simultaneously. The orchestrator merges results.

## Architecture

```
                    ┌──────────────────────────┐
                    │      AgentFleet          │
                    │   (orchestrator)          │
                    ├──────────────────────────┤
                    │  Task Queue (deduped)     │
                    │  Session Pool (cookies)   │
                    │  Credit Ledger (MMCCL)    │
                    └─────────┬────────────────┘
                              │
                 ┌────────────┼────────────────┐
                 ▼            ▼                ▼
          ┌───────────┐ ┌───────────┐  ┌───────────┐
          │  Agent 1  │ │  Agent 2  │  │  Agent 3  │
          │  (Issues) │ │   (PRs)   │  │ (Ops/CI)  │
          └─────┬─────┘ └─────┬─────┘  └─────┬─────┘
                │             │               │
         ┌──────┴──────┐     │         ┌──────┴──────┐
         ▼             ▼     ▼         ▼             ▼
    ┌─────────┐  ┌──────────┐   ┌─────────┐  ┌──────────┐
    │Connector│  │ Browser  │   │Connector│  │ Browser  │
    │ (gh API)│  │(Playwrt) │   │(Shopify)│  │(Playwrt) │
    └─────────┘  └──────────┘   └─────────┘  └──────────┘
```

## Component 1: Finger Interaction Upgrade

**File**: `src/browser/hydra_hand.py` (extend existing `Finger` class)

New methods on `Finger`:
- `click(selector)` — click element, governance-checked
- `type_text(selector, text)` — type into input, masks sensitive data in logs
- `fill_form(fields: dict)` — fill multiple form fields at once
- `select_option(selector, value)` — dropdown selection
- `upload_file(selector, file_path)` — file upload
- `download(url) -> Path` — download to governed temp directory
- `wait_for(selector, timeout)` — wait for element to appear
- `scroll_to(selector_or_position)` — scroll to element or coordinates
- `get_attribute(selector, attr)` — read element attributes
- `handle_dialog(action)` — accept/dismiss browser dialogs

Each action:
1. Checks governance (RU finger's domain safety + SCBE 4-tier)
2. Executes via Playwright
3. Logs to audit trail
4. Mints MMCCL credit for the work done

## Component 2: AgentFleet Orchestrator

**File**: `src/fleet/agent_fleet.py` (new)

```python
class AgentFleet:
    """Manages N concurrent agents with shared state."""

    def __init__(self, max_agents=3):
        self.agents: Dict[str, FleetAgent] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.session_pool: SessionPool = SessionPool()
        self.ledger: ContextLedger = ContextLedger("fleet-validator")
        self.dedup: Set[str] = set()  # task fingerprints

    async def spawn_agent(self, role: str, platform: str) -> FleetAgent
    async def submit_task(self, task: FleetTask) -> str
    async def run_until_empty(self) -> FleetReport
    async def shutdown(self)
```

**FleetAgent** wraps a HydraHand + ConnectorClient:
```python
class FleetAgent:
    role: str              # "issues", "prs", "ops"
    platform: str          # "github", "shopify", "notion"
    hand: HydraHand        # Browser (6 fingers)
    connector: Optional[ConnectorClient]  # API side
    session: SharedSession # Cookies/tokens from pool

    async def execute_task(self, task: FleetTask) -> TaskResult
```

**FleetTask** describes work:
```python
@dataclass
class FleetTask:
    task_id: str
    task_type: str         # github_issue, github_pr, shopify_order, research, content_publish
    platform: str          # github, shopify, notion, airtable, generic
    target: str            # URL, issue number, order ID
    action: str            # triage, fix, review, create, update, close
    params: Dict[str, Any]
    priority: int = 5      # 1=urgent, 10=background
    prefer: str = "connector"  # connector, browser, both
```

**Task routing logic**:
1. If `prefer=connector` and connector exists for platform → use connector
2. If `prefer=browser` or no connector → use browser
3. If `prefer=both` → run connector + browser in parallel, merge results
4. If connector fails → auto-fallback to browser

## Component 3: Session Pool

**File**: `src/fleet/session_pool.py` (new)

Manages shared authentication across agents:
- GitHub: PAT token shared across 3 agents (respects 5000 req/hr)
- Shopify: Admin API token + storefront token
- Notion: Integration token
- Generic: Cookie jar per domain

```python
class SessionPool:
    async def get_session(self, platform: str) -> SharedSession
    async def refresh_token(self, platform: str)
    def rate_limiter(self, platform: str) -> RateLimiter
```

Rate limiting per platform:
- GitHub: 5000/hr shared across 3 agents (~27 req/min each)
- Shopify: 40 req/sec (Admin), 100 req/sec (Storefront)
- Notion: 3 req/sec
- Airtable: 5 req/sec

## Component 4: Connector Bridge

**File**: `src/fleet/connector_bridge.py` (new)

Unifies the existing 10 connector kinds into a callable interface:

```python
class ConnectorBridge:
    """Unified interface to all connectors."""

    async def execute(self, connector_id: str, action: str, payload: dict) -> ConnectorResult
    async def list_connectors() -> List[ConnectorInfo]
    async def health_check(connector_id: str) -> bool
```

Maps connector kinds to capabilities:
| Connector | Read | Write | Webhook | Revenue |
|-----------|------|-------|---------|---------|
| GitHub    | issues, PRs, repos | create/update issues, PRs | push events | CI/CD automation |
| Shopify   | orders, products, inventory | create products, update inventory | order webhooks | Direct sales |
| Zapier    | — | trigger zaps | catch hooks | Workflow automation |
| n8n       | workflow status | trigger workflows | webhook trigger | Self-hosted automation |
| Notion    | pages, databases | create/update pages | — | Knowledge base |
| Airtable  | records | create/update records | — | Project tracking |
| Slack     | messages | send messages | events | Team notifications |
| Discord   | messages | send messages | — | Community |
| Linear    | issues | create/update | — | Project management |
| Webhook   | — | POST payloads | — | Generic integration |

## Component 5: GitHub Multi-Agent Strategy

3 agents, specialized roles:

### Agent 1: Issue Triage
- Reads new/open issues via `gh` CLI (connector)
- Labels, assigns, and comments
- For complex issues: opens browser to read linked resources
- Creates branches for approved issues

### Agent 2: PR Builder
- Takes assigned issues, writes code (via Claude Code)
- Creates PRs via `gh` CLI
- Responds to review comments
- Browser: previews deploy previews, checks CI output pages

### Agent 3: Ops & Releases
- Monitors CI status via GitHub API
- Handles release notes, changelogs
- Closes stale issues/PRs
- Browser: checks deployment health, external service status

Deduplication: task fingerprint = `{platform}:{target}:{action}` — if already in-flight, skip.

## Revenue Integration

Every agent action produces value:
1. **MMCCL credits** minted per task completion (tied to Hamiltonian energy cost)
2. **Training data** — every browser interaction generates SFT pairs
3. **Connector usage** logged to Airtable revenue tracker
4. **Content generation** — research results feed content spin pipeline

Profitable connector flows:
- Shopify: automated inventory management, product descriptions, order triage
- Zapier/n8n: sell workflow templates powered by SCBE governance
- GitHub: automated issue resolution as a service

## File Plan

| File | Type | Purpose |
|------|------|---------|
| `src/browser/hydra_hand.py` | EDIT | Add click/type/fill/select/upload/download to Finger |
| `src/fleet/agent_fleet.py` | NEW | Fleet orchestrator with task queue |
| `src/fleet/session_pool.py` | NEW | Shared auth + rate limiting |
| `src/fleet/connector_bridge.py` | NEW | Unified connector interface |
| `tests/test_agent_fleet.py` | NEW | Fleet orchestration tests |

## Implementation Order

1. Upgrade Finger with interaction methods (enables everything else)
2. Build SessionPool (auth sharing)
3. Build ConnectorBridge (unified connector calls)
4. Build AgentFleet orchestrator (ties it all together)
5. Write tests
6. Wire GitHub 3-agent strategy as first deployment
7. Close issue #64
