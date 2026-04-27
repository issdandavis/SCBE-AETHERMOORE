# AetherBrowser Pack

Multi-lane governed browser automation for agentic browsing.

## What ships

### TypeScript (`scbe-aethermoore/browser`)

```ts
import {
  BrowserAgent,
  CDPBackend,
  PlaywrightBackend,
  MockBrowserBackend,
  BrowserActionEvaluator,
  BrowserSession,
  WSClient,
} from 'scbe-aethermoore/browser';
```

| Module | What it does |
|--------|-------------|
| **BrowserAgent** | Orchestrator — routes every action through 14-layer governance pipeline |
| **CDPBackend** | Zero-dependency Chrome DevTools Protocol automation (raw WebSocket) |
| **PlaywrightBackend** | Playwright wrapper with graceful fallback if not installed |
| **MockBrowserBackend** | Testing backend — no real browser needed |
| **BrowserActionEvaluator** | 14-layer governance: semantic encoding → Poincare embedding → hyperbolic distance → harmonic scaling → risk decision |
| **BrowserSession** | Session state: risk accumulation, action history, escalation queue |
| **WSClient** | RFC 6455 WebSocket client for extension ↔ server communication |

### Chrome Extension (`src/extension/`)

Manifest V3 sidePanel extension connecting to the Python WebSocket server:

- **Side panel UI**: agent grid, conversation feed, zone approval prompts, topology canvas
- **Content script**: DOM observation on all pages
- **Background worker**: WebSocket connection management
- Load via `chrome://extensions` → Developer mode → Load unpacked → select `src/extension/`

### Python Server (`src/aetherbrowser/`)

```bash
python -m uvicorn src.aetherbrowser.serve:app --host 127.0.0.1 --port 8002
```

| Module | What it does |
|--------|-------------|
| **serve.py** | FastAPI WebSocket server handling COMMAND, PAGE_CONTEXT, ZONE_RESPONSE |
| **router.py** | OctoArmorRouter — 7-provider model selection with cost tiers and rate limiting |
| **command_planner.py** | Risk inference, zone assignment (RED/YELLOW/GREEN), intent classification |
| **provider_executor.py** | Async LLM execution: Anthropic, OpenAI, xAI, HuggingFace, local fallback |
| **page_analyzer.py** | Heuristic page analysis (topic detection, auth/payment/destructive field classification) |
| **ws_feed.py** | WebSocket message protocol factory |

### Python Agents (`agents/`)

| Agent | Architecture | What it does |
|-------|-------------|-------------|
| **browser_agent.py** | Single-agent + SCBE API | Every action → governance gate → execute if approved. 4-tier escalation (ALLOW/QUARANTINE/ESCALATE/DENY). |
| **swarm_browser.py** | 6-agent Byzantine consensus | Six Sacred Tongue agents (Scout/Vision/Reader/Clicker/Typer/Judge). 4/6 majority vote. HMAC-signed messages. JSONL audit hub. |
| **playwright_runtime.py** | Browser backend | Async Playwright wrapper. Pass to browser_agent or swarm_browser for real browser control. |

## Multi-lane controls

### Zone gates (hard-enforced)

| Zone | Trigger | Behavior |
|------|---------|----------|
| **RED** | High-risk action (banking, auth, side-effects) | Blocks execution until explicit user approval via extension UI |
| **YELLOW** | Medium-risk action (mixed analysis + action) | Requires approval; auto-allowed for low-risk domains |
| **GREEN** | Low-risk action (read-only, analysis) | Passes through without gate |

Safety net: any `risk_tier == "high"` action is forced to RED even if keyword heuristics missed it.

Quarantine enforcement: quarantined actions only auto-execute when domain risk < 0.5. Banking (0.95), healthcare (0.8), government (0.75) domains are blocked in quarantine.

### Sacred Tongues routing

Each action is assigned to a Sacred Tongue agent based on type:

| Action | Tongue | Default Provider |
|--------|--------|-----------------|
| navigate | KO (Knowledge) | OPUS |
| click | AV (Analysis) | FLASH |
| type | RU (Runtime) | LOCAL |
| scroll | CA (Cascade) | SONNET |
| execute_script | DR (Diagnosis) | HAIKU |
| screenshot | UM (Uncertainty) | GROK |

### Provider cascade

OctoArmorRouter scores task complexity (LOW/MEDIUM/HIGH) and selects provider by cost tier:

- Tier 0: LOCAL (free, immediate)
- Tier 1: HAIKU (fast, cheap)
- Tier 2: FLASH, GROK (balanced)
- Tier 3: SONNET (capable)
- Tier 4: OPUS (best, expensive)

Auto-cascade: if the selected provider fails, falls back through the chain.

## What does NOT ship

- Training data, SFT pairs, model weights
- Research pipeline or news feed
- API keys or credentials
- Basin river paths (Dropbox, OneDrive, etc.) — config only
- HYDRA orchestrator (separate repo: `issdandavis/scbe-agents`)

## Quick start

```bash
# TypeScript
npm install scbe-aethermoore
```

```ts
import { BrowserAgent, PlaywrightBackend } from 'scbe-aethermoore/browser';

const backend = new PlaywrightBackend();
await backend.initialize({ headless: false });

const agent = new BrowserAgent({ backend });
await agent.startSession();

// Every action goes through 14-layer governance
const result = await agent.navigate('https://example.com');
console.log(result.decision); // ALLOW | QUARANTINE | ESCALATE | DENY
```

```bash
# Python (governed single-agent)
pip install playwright && python -m playwright install chromium

python -c "
import asyncio
from agents.playwright_runtime import PlaywrightRuntime
from agents.browser_agent import SCBEBrowserAgent

async def main():
    rt = PlaywrightRuntime()
    await rt.launch(headless=False)
    agent = SCBEBrowserAgent(runtime=rt)
    agent.navigate('https://example.com')  # governed
    await rt.close()

asyncio.run(main())
"
```

```bash
# Python (6-agent Byzantine swarm)
python -c "
import asyncio
from agents.playwright_runtime import PlaywrightRuntime
from agents.swarm_browser import SwarmBrowser

async def main():
    rt = PlaywrightRuntime()
    await rt.launch(headless=False)
    swarm = SwarmBrowser(browser_backend=rt)
    await swarm.initialize()
    await swarm.navigate('https://example.com')  # consensus-governed
    await rt.close()

asyncio.run(main())
"
```
