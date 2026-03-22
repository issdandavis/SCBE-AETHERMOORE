# AetherBrowser Persistent Configuration Spec

**Version**: 1.0.0
**Date**: 2026-03-17
**Author**: Issac Davis / Claude Code
**Status**: Draft

## Overview

This document defines how to configure the AetherBrowser (Playwright MCP + SCBE browser stack) as a persistent, reusable tool with saved logins, extensions, custom configuration, and automatic training data generation.

The AetherBrowser already has deep governance primitives (14-layer pipeline, ALLOW/QUARANTINE/ESCALATE/DENY decisions, HyperLane service mesh with GREEN/YELLOW/RED zones). This spec focuses on the **operational persistence layer** that makes it practical for daily revenue-critical work.

---

## 1. Persistent Profile Setup

### Problem

By default, Playwright MCP launches a fresh browser context every session. All logins, cookies, localStorage, and session tokens are lost. This forces re-authentication on every run and makes the browser useless for real operational work.

### Solution: Persistent User Data Directory

Playwright supports two persistence mechanisms. Use **both** depending on the backend.

#### 1a. Playwright `launchPersistentContext` (Recommended for Agent Runtime)

This creates a real Chrome user data directory that persists cookies, localStorage, IndexedDB, service workers, and extension state between sessions.

```python
# In aetherbrowse/worker/browser_worker.py
from playwright.sync_api import sync_playwright

PROFILE_DIR = "C:/Users/issda/.scbe-aetherbrowser/profiles/creator-main"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        viewport={"width": 1440, "height": 900},
        args=[
            "--disable-blink-features=AutomationControlled",
            "--enable-features=NetworkService,NetworkServiceInProcess",
        ],
    )
    page = context.pages[0] if context.pages else context.new_page()
```

#### 1b. Storage State Export/Import (For Playwright MCP Plugin)

When using the Playwright MCP plugin (`mcp__plugin_playwright_playwright__*`), configure storage state persistence:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--browser", "chromium",
        "--user-data-dir", "C:/Users/issda/.scbe-aetherbrowser/profiles/mcp-default",
        "--no-sandbox"
      ]
    }
  }
}
```

The `--user-data-dir` flag tells Playwright MCP to use a persistent Chrome profile directory instead of creating a temporary one.

#### 1c. CDP Backend (For Raw Chrome Control)

The existing CDP backend in `agents/browsers/cdp_backend.py` already supports persistent profiles via `get_chrome_launch_command()`:

```powershell
# Launch Chrome with persistent profile and remote debugging
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\Users\issda\.scbe-chrome-profile"
```

The CDP backend then connects to this running instance. Logins persist because it is a real Chrome profile.

### Profile Directory Structure

```
C:/Users/issda/.scbe-aetherbrowser/
  profiles/
    creator-main/           # Primary profile — all logins, extensions
      Default/
        Cookies
        Local Storage/
        IndexedDB/
        Extensions/
    mcp-default/            # Playwright MCP sessions
    ops-headless/           # Headless automation (no extensions)
    clean-sandbox/          # Disposable profile for untrusted sites
  storage-states/
    creator-main.json       # Portable storage state export
    ops-headless.json
  extensions/               # Unpacked extension source (shared)
    ublock-origin/
    dark-reader/
    json-viewer/
```

### Profile Management Commands

```bash
# Export storage state from active profile
python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        'C:/Users/issda/.scbe-aetherbrowser/profiles/creator-main',
        headless=True
    )
    ctx.storage_state(path='C:/Users/issda/.scbe-aetherbrowser/storage-states/creator-main.json')
    ctx.close()
"

# Switch profiles via AetherBrowse runtime
curl http://127.0.0.1:8400/api/profile/switch -d '{"profile_id": "creator-main"}'

# List available profiles
curl http://127.0.0.1:8400/api/profile/list
```

### Security Considerations

- The `creator-main` profile contains real login sessions. **Never commit profile directories to git.**
- Add to `.gitignore`:
  ```
  .scbe-aetherbrowser/
  aetherbrowse/profiles/
  ```
- Encrypt profile directories at rest using the Sacred Vault (`scripts/security/sacred_vault.py`) for backup to Dropbox.
- Each agent (Zara, Kael, Aria, Polly) should use **read-only access** to the shared profile. Only the human (Issac) or admin-tier agents can write new credentials.
- See `docs/security/2026-03-17-browser-sandbox-advisory.md` for the full threat model around persistent `userDataDir` security.

---

## 2. Recommended Extensions

Extensions load automatically when using `launchPersistentContext` with a real profile directory that has them installed. For headless or MCP mode, load unpacked extensions via Chrome args.

### Loading Extensions in Playwright

```python
context = p.chromium.launch_persistent_context(
    user_data_dir=PROFILE_DIR,
    headless=False,  # Extensions require headed mode
    args=[
        f"--disable-extensions-except={ext_dir}/ublock-origin,{ext_dir}/dark-reader,{ext_dir}/json-viewer",
        f"--load-extension={ext_dir}/ublock-origin,{ext_dir}/dark-reader,{ext_dir}/json-viewer",
    ],
)
```

**Note**: Chrome extensions do NOT work in headless mode. For headless automation (`ops-headless` profile), rely on Playwright's built-in `route()` method for ad blocking instead:

```python
await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", lambda route: route.abort())
await page.route("**/ads/**", lambda route: route.abort())
await page.route("**/analytics/**", lambda route: route.abort())
```

### Extension List

| Extension | Purpose | Chrome Web Store ID | Priority |
|-----------|---------|---------------------|----------|
| **uBlock Origin** | Ad/tracker blocking. Faster page loads, less noise for page perception. Reduces bandwidth and improves DOM observation quality. | `cjpalhdlnbpafiamejdnhcphjbkeiagm` | **Required** |
| **Dark Reader** | Dark mode on all sites. Reduces eye strain during long monitoring sessions. | `eimadpbcbfnmbkopoojfekhnkhdbieeh` | Recommended |
| **JSON Viewer** | Pretty-prints JSON API responses. Essential when monitoring HuggingFace API, Stripe webhooks, and GitHub API responses. | `gbmdgpbipfallnflgajpaliibnhdgobh` | Recommended |
| **Bitwarden** | Password management. Auto-fills credentials for revenue-critical sites without storing passwords in plaintext. | `nngceckbapebfimnlniiiahkandclblb` | Recommended |
| **Grammarly** | Writing assistance for composing posts on GitHub Discussions, Dev.to, HuggingFace, and X/Twitter. | `kbfnbcaeplbcioakkpcpgfkobkghlhen` | Optional |
| **Vimium** | Keyboard-driven navigation. Useful for agent-assisted browsing where selectors are complex. | `dbepggeogbaibhgnhhndojpepiihcmeb` | Optional |

### Extension Installation Workflow

1. **Manual first install** (one time): Open the `creator-main` profile in headed mode, install extensions from Chrome Web Store. They persist in the profile directory.
2. **Automated install** (for new profiles): Download `.crx` files to `~/.scbe-aetherbrowser/extensions/` and load them as unpacked extensions via `--load-extension`.
3. **Headless fallback**: For `ops-headless`, skip extensions entirely. Use Playwright route interception for ad blocking.

---

## 3. Developer Mode / Chrome DevTools Access

### Enabling DevTools in Playwright

```python
# Launch with DevTools auto-open
context = p.chromium.launch_persistent_context(
    user_data_dir=PROFILE_DIR,
    headless=False,
    devtools=True,   # Auto-opens DevTools panel
    args=[
        "--auto-open-devtools-for-tabs",
    ],
)
```

### CDP Backend DevTools Access

The `CDPBackend` in `src/browser/cdp-backend.ts` and `agents/browsers/cdp_backend.py` connects directly to Chrome DevTools Protocol. When Chrome is launched with `--remote-debugging-port=9222`, full DevTools access is available:

```powershell
# Launch Chrome with remote debugging + persistent profile
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\Users\issda\.scbe-aetherbrowser\profiles\creator-main" --auto-open-devtools-for-tabs
```

**Available CDP endpoints:**
- `http://127.0.0.1:9222/json` -- list open tabs
- `http://127.0.0.1:9222/json/version` -- browser version info
- `ws://127.0.0.1:9222/devtools/page/{id}` -- WebSocket connection to a tab

### Connecting the SCBE CDPBackend

```typescript
import { CDPBackend } from './src/browser/cdp-backend';

const backend = new CDPBackend({
  host: '127.0.0.1',
  port: 9222,
  debug: true,  // Log CDP traffic
});
```

### Network Monitoring via DevTools

Enable network interception for governance audit:

```python
# CDP: Enable network monitoring
await backend.send("Network.enable", {})
await backend.send("Network.setRequestInterception", {
    "patterns": [{"urlPattern": "*"}]
})
```

This feeds into the `NetworkObservation` type already defined in `src/browser/types.ts`, providing `pendingRequests`, `recentRequests`, `blockedRequests`, and `bytesTransferred` to the 14-layer pipeline.

### Performance Profiling

```python
# CDP: Enable performance metrics
await backend.send("Performance.enable", {})
metrics = await backend.send("Performance.getMetrics", {})
# Feeds into PerformanceObservation: ttfb, fcp, lcp, tbt, memoryUsage
```

---

## 4. Training Data Generation

### Architecture

Every browser action already flows through the SCBE 14-layer governance pipeline (`BrowserActionEvaluator` in `src/browser/evaluator.ts`). The training data layer hooks into this existing audit trail to generate SFT/DPO pairs automatically.

```
User Command
    |
    v
PERCEIVE (Polly) --> PagePerception
    |
    v
PLAN (Zara) ---------> ActionPlan
    |
    v
GOVERN (Aria) -------> GovernanceResult {ALLOW|QUARANTINE|ESCALATE|DENY}
    |                        |
    v                        +---> training-data/aetherbrowse/governance_pairs.jsonl
EXECUTE (Kael)               +---> training-data/aetherbrowse/planning_pairs.jsonl
    |
    v
OBSERVE (Polly) --> PagePerception (after)
    |
    +---> training-data/aetherbrowse/action_traces.jsonl
```

### 4a. Navigation Traces

Every navigation action generates an SFT pair:

```jsonl
{"type": "navigation", "timestamp": "2026-03-17T14:30:00Z", "session_id": "abc-123", "input": {"intent": "Check book sales on KDP", "context": {"current_url": "about:blank", "session_state": "idle"}}, "output": {"url": "https://kdp.amazon.com/en_US/reports/", "action_sequence": [{"type": "navigate", "url": "https://kdp.amazon.com"}, {"type": "wait", "networkIdle": true}, {"type": "click", "selector": "#reports-tab"}], "governance_decision": "ALLOW", "risk_score": 0.3, "domain_category": "financial"}}
```

**Schema for navigation traces:**
| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"navigation"` |
| `input.intent` | string | Natural language description of what the user wanted |
| `input.context` | object | Current URL, session state, recent history |
| `output.url` | string | Final destination URL |
| `output.action_sequence` | array | Ordered list of `BrowserAction` objects executed |
| `output.governance_decision` | string | ALLOW/QUARANTINE/ESCALATE/DENY |
| `output.risk_score` | number | Combined risk score (0-1) |
| `output.domain_category` | string | From `DomainRiskCategory` in `src/browser/types.ts` |

### 4b. Form Fill Traces

Every form interaction generates an SFT pair:

```jsonl
{"type": "form_fill", "timestamp": "2026-03-17T14:35:00Z", "session_id": "abc-123", "input": {"field_description": "Search query input on HuggingFace", "form_context": {"form_id": "search-form", "action": "https://huggingface.co/search", "method": "GET"}, "page_context": {"url": "https://huggingface.co", "title": "Hugging Face"}}, "output": {"selector": "input[name='search']", "value": "scbe-aethermoore-training-data", "action": {"type": "type", "selector": "input[name='search']", "text": "scbe-aethermoore-training-data", "sensitive": false}, "governance_decision": "ALLOW", "risk_score": 0.15}}
```

**Schema for form fill traces:**
| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"form_fill"` |
| `input.field_description` | string | Human-readable description of the field |
| `input.form_context` | object | Form ID, action URL, method, sensitive field flags |
| `input.page_context` | object | Current URL, page title |
| `output.selector` | string | CSS selector used |
| `output.value` | string | Value entered (masked if `sensitive: true`) |
| `output.governance_decision` | string | Pipeline decision |

### 4c. File Upload Traces

```jsonl
{"type": "file_upload", "timestamp": "2026-03-17T15:00:00Z", "session_id": "abc-123", "input": {"target_site": "huggingface.co", "intent": "Upload training dataset", "page_context": {"url": "https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data/upload", "title": "Upload files"}}, "output": {"selector": "input[type='file']", "file_path": "training-data/funnel/sft_governed.jsonl", "document_type": "jsonl_dataset", "file_size_bytes": 2048576, "governance_decision": "ALLOW", "risk_score": 0.45}}
```

### 4d. Training Data Storage

| File | Content | Format |
|------|---------|--------|
| `training-data/aetherbrowse/governance_pairs.jsonl` | Governance decisions (existing) | JSONL |
| `training-data/aetherbrowse/planning_pairs.jsonl` | Planner decisions (existing) | JSONL |
| `training-data/aetherbrowse/action_traces.jsonl` | Full action traces (new) | JSONL |
| `training-data/aetherbrowse/navigation_traces.jsonl` | Navigation-only traces (new) | JSONL |
| `training-data/aetherbrowse/form_fill_traces.jsonl` | Form interaction traces (new) | JSONL |
| `training-data/aetherbrowse/upload_traces.jsonl` | File upload traces (new) | JSONL |

### 4e. Training Data Pipeline Integration

The training data flows into the existing SCBE training pipeline:

1. **Capture**: Browser actions are logged during execution by the agent runtime.
2. **Govern**: Each record passes through the 14-layer pipeline and gets a governance stamp.
3. **Filter**: Records with `DENY` decisions become DPO negative examples. `ALLOW` records become SFT positive examples.
4. **Export**: `python scripts/training/export_browser_sft.py --source aetherbrowse --output training-data/funnel/browser_sft.jsonl`
5. **Push**: `python scripts/training/push_to_hf.py --dataset issdandavis/scbe-aethermoore-training-data --split browser`

### 4f. Privacy and Sensitivity

- Fields flagged as `sensitive` in `FormFieldObservation` (password, credit_card, ssn, api_key, etc.) are **always masked** in training data as `"***"`.
- The `SensitiveFieldType` detection patterns in `src/browser/playwright-backend.ts` and `agents/browsers/cdp_backend.py` automatically detect and mask these fields.
- URLs containing auth tokens, session IDs, or API keys are stripped before logging.
- Training data is stored locally first, reviewed via the content pipeline QA gate, then pushed to HuggingFace.

---

## 5. Revenue-Critical Sites

### Pre-Configured Workflows

These sites are already registered in the HyperLane service mesh (`src/browser/hyperlane.ts`) with governance zones and rate limits. The persistent profile ensures logins stay active.

#### 5a. KDP (Amazon Kindle Direct Publishing)

| Field | Value |
|-------|-------|
| **URL** | `https://kdp.amazon.com` |
| **HyperLane Zone** | YELLOW (external commerce) |
| **Purpose** | Monitor book sales, royalties, reviews |
| **Login Method** | Amazon account (persisted in `creator-main` profile) |
| **Key Pages** | `/en_US/reports/` (sales), `/en_US/bookshelf` (books), `/en_US/title-setup/` (new books) |
| **Monitoring Cadence** | Daily check at 09:00 PT |
| **Training Value** | Navigation patterns for commerce dashboards |

**Workflow:**
1. Navigate to `https://kdp.amazon.com/en_US/reports/`
2. Wait for dashboard to load (networkidle)
3. Screenshot the sales summary
4. Extract royalty numbers from the report table
5. Log to `artifacts/revenue/kdp_daily.jsonl`

#### 5b. Patent Center (USPTO)

| Field | Value |
|-------|-------|
| **URL** | `https://patentcenter.uspto.gov` |
| **HyperLane Zone** | YELLOW (government) |
| **Purpose** | Monitor application 63/961,403 status |
| **Login Method** | USPTO account (persisted in `creator-main` profile) |
| **Key Pages** | `/applications/63961403` (application detail) |
| **Monitoring Cadence** | Weekly check on Monday |
| **Training Value** | Government site navigation patterns |

**Known Issue:** The Patent Center API returns 400 errors when querying by application number with slashes (as seen in `.playwright-mcp/console-2026-03-18T04-19-53-404Z.log`). Use the format `63961403` without the slash.

**Workflow:**
1. Navigate to `https://patentcenter.uspto.gov`
2. Enter application number `63961403` in search
3. Check filing status, office actions, deadlines
4. Screenshot status page
5. Log to `artifacts/legal/patent_status.jsonl`

#### 5c. HuggingFace

| Field | Value |
|-------|-------|
| **URL** | `https://huggingface.co` |
| **HyperLane Zone** | GREEN (owned service) |
| **HyperLane ID** | `huggingface` |
| **Purpose** | Model/dataset management, community engagement |
| **Login Method** | HF token (persisted in profile + env `HF_TOKEN`) |
| **Key Pages** | `/issdandavis` (profile), `/issdandavis/scbe-aethermoore-training-data` (dataset), `/settings/tokens` (API tokens) |
| **Monitoring Cadence** | Daily |
| **Training Value** | ML platform workflows, dataset upload patterns |

**Workflow:**
1. Check model download stats at `/issdandavis`
2. Verify dataset freshness at `/datasets/issdandavis/scbe-aethermoore-training-data`
3. Review community discussions
4. Push updated datasets via API or web upload
5. Log to `artifacts/ml/hf_daily.jsonl`

#### 5d. Shopify (Aethermoore Works)

| Field | Value |
|-------|-------|
| **URL** | `https://aethermore-works.myshopify.com/admin` |
| **HyperLane Zone** | GREEN (owned service) |
| **HyperLane ID** | `shopify` |
| **Purpose** | Store management, product updates, order tracking |
| **Login Method** | Shopify account (persisted in `creator-main` profile) |
| **Key Pages** | `/admin/products` (products), `/admin/orders` (orders), `/admin/analytics` (analytics) |
| **Monitoring Cadence** | Daily |
| **Training Value** | E-commerce admin patterns |

**Workflow:**
1. Navigate to `/admin/analytics/dashboards`
2. Check daily revenue and visitor stats
3. Review pending orders at `/admin/orders`
4. Update product listings if needed
5. Log to `artifacts/revenue/shopify_daily.jsonl`

#### 5e. GitHub (issdandavis)

| Field | Value |
|-------|-------|
| **URL** | `https://github.com/issdandavis` |
| **HyperLane Zone** | GREEN (owned service) |
| **HyperLane ID** | `github` |
| **Purpose** | Repo management, PR reviews, Discussions publishing, Gist management |
| **Login Method** | GitHub account + PAT (persisted in profile + env `GITHUB_TOKEN`) |
| **Key Pages** | `/issdandavis/SCBE-AETHERMOORE` (main repo), `/issdandavis/SCBE-AETHERMOORE/discussions` (content), `/issdandavis?tab=repositories` (all repos) |
| **Monitoring Cadence** | Continuous (agent loop) |
| **Training Value** | Developer workflow patterns, PR review, issue triage |

#### 5f. Google Colab

| Field | Value |
|-------|-------|
| **URL** | `https://colab.research.google.com` |
| **HyperLane Zone** | YELLOW (external compute) |
| **Purpose** | GPU compute for training, notebook execution |
| **Login Method** | Google account (persisted in `creator-main` profile) |
| **Key Pages** | `/drive` (notebooks in Drive), `/notebook` (active notebook) |
| **Monitoring Cadence** | On-demand during training runs |
| **Training Value** | Notebook execution patterns, compute provisioning |

**Workflow:**
1. Navigate to `https://colab.research.google.com`
2. Open notebook from Drive (`notebooks/scbe_pivot_training_v2.ipynb`)
3. Connect to runtime (GPU if available)
4. Execute training cells
5. Download results and log to `artifacts/training/colab_runs.jsonl`

#### 5g. Stripe

| Field | Value |
|-------|-------|
| **URL** | `https://dashboard.stripe.com` |
| **HyperLane Zone** | GREEN (owned service) |
| **HyperLane ID** | `stripe` |
| **Purpose** | Payment monitoring, revenue tracking |
| **Login Method** | Stripe account (persisted in `creator-main` profile) |
| **Key Pages** | `/dashboard` (overview), `/payments` (transactions), `/balance` (current balance) |
| **Monitoring Cadence** | Daily |
| **Training Value** | Financial dashboard navigation patterns |

**Workflow:**
1. Navigate to `https://dashboard.stripe.com/dashboard`
2. Check pending balance (last known: $97.74)
3. Review recent payments
4. Screenshot dashboard
5. Log to `artifacts/revenue/stripe_daily.jsonl`

### Bookmark File

Export a bookmarks HTML file to the `creator-main` profile:

```
SCBE Revenue
  +-- KDP Reports: https://kdp.amazon.com/en_US/reports/
  +-- Patent 63/961,403: https://patentcenter.uspto.gov
  +-- HuggingFace: https://huggingface.co/issdandavis
  +-- Shopify Admin: https://aethermore-works.myshopify.com/admin
  +-- Stripe Dashboard: https://dashboard.stripe.com/dashboard
  +-- Gumroad: https://app.gumroad.com/dashboard

SCBE Dev
  +-- GitHub Repo: https://github.com/issdandavis/SCBE-AETHERMOORE
  +-- GitHub Discussions: https://github.com/issdandavis/SCBE-AETHERMOORE/discussions
  +-- Colab: https://colab.research.google.com
  +-- npm Package: https://www.npmjs.com/package/scbe-aethermoore
  +-- PyPI Package: https://pypi.org/project/scbe-aethermoore/

SCBE Content
  +-- Dev.to: https://dev.to/dashboard
  +-- X/Twitter: https://x.com/issdandavis
  +-- YouTube Studio: https://studio.youtube.com
  +-- World Anvil: https://www.worldanvil.com/dashboard
```

---

## 6. Integration with Existing Infrastructure

### Playwright MCP Plugin (Claude Code)

The Playwright MCP plugin is already authorized in `.claude/settings.local.json` (`mcp__plugin_playwright_playwright__*`). To use the persistent profile:

1. Configure the MCP server to use `--user-data-dir` (see Section 1b).
2. The plugin's `browser_navigate`, `browser_click`, `browser_fill_form` tools will operate within the persistent context.
3. Console logs are already captured to `.playwright-mcp/console-*.log`.

### AetherBrowse Agent Runtime

The 4-agent loop (Zara/Kael/Aria/Polly) defined in `plugins/aetherbrowse/skills/aetherbrowse-dev/SKILL.md` connects to the persistent profile through the Playwright worker:

1. Worker launches with `launch_persistent_context(user_data_dir=PROFILE_DIR)`.
2. Agent runtime at port 8400 orchestrates the PERCEIVE/PLAN/GOVERN/EXECUTE loop.
3. All actions flow through governance and generate training data.

### HyperLane Service Mesh

The HyperLane router (`src/browser/hyperlane.ts`) already defines service connectors for all revenue-critical sites with zone assignments, rate limits, and access policies. The persistent profile ensures the browser has valid session cookies for each service.

### Basin Data Lake

All browser-captured data flows into the Basin (`src/browser/basin.ts`) through defined rivers. Training data goes to `training/intake/`, revenue data goes to `artifacts/revenue/`, and operational logs go to `artifacts/aetherbrowse/`.

---

## 7. Quick Start

```powershell
# 1. Create the profile directory structure
mkdir -p C:\Users\issda\.scbe-aetherbrowser\profiles\creator-main
mkdir -p C:\Users\issda\.scbe-aetherbrowser\profiles\mcp-default
mkdir -p C:\Users\issda\.scbe-aetherbrowser\profiles\ops-headless
mkdir -p C:\Users\issda\.scbe-aetherbrowser\storage-states
mkdir -p C:\Users\issda\.scbe-aetherbrowser\extensions

# 2. First run: launch headed browser to log in manually
python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        'C:/Users/issda/.scbe-aetherbrowser/profiles/creator-main',
        headless=False,
        viewport={'width': 1440, 'height': 900}
    )
    input('Log into all revenue-critical sites, then press Enter to save and close...')
    ctx.storage_state(path='C:/Users/issda/.scbe-aetherbrowser/storage-states/creator-main.json')
    ctx.close()
"

# 3. Subsequent runs use the persisted profile automatically
# Via AetherBrowse runtime:
python -m uvicorn aetherbrowse.runtime.server:app --host 127.0.0.1 --port 8400

# Via CDP backend:
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\Users\issda\.scbe-aetherbrowser\profiles\creator-main"
```

---

## Appendix A: Existing Code References

| File | Relevance |
|------|-----------|
| `src/browser/agent.ts` | BrowserAgent with 14-layer governance, BrowserBackend interface |
| `src/browser/session.ts` | Session management, risk tracking, Hive Memory export |
| `src/browser/types.ts` | All browser action/observation types, sensitivity detection |
| `src/browser/playwright-backend.ts` | Playwright backend implementation |
| `src/browser/cdp-backend.ts` | CDP backend implementation (zero-dependency) |
| `src/browser/hyperlane.ts` | HyperLane service mesh with 17+ service connectors |
| `src/browser/basin.ts` | Basin data lake with river policies |
| `agents/browsers/cdp_backend.py` | Python CDP backend with `get_chrome_launch_command()` |
| `agents/aetherbrowse_cli.py` | CLI for AetherBrowse with backend selection |
| `aetherbrowse/config/ai_privileges.yaml` | Agent privilege tiers (observer/scout/operator/architect/admin) |
| `aetherbrowse/config/governance_policies.yaml` | Governance rules and agent permissions |
| `plugins/aetherbrowse/skills/aetherbrowse-ops/SKILL.md` | Operations guide with profile management |
| `plugins/aetherbrowse/skills/aetherbrowse-dev/SKILL.md` | Development guide with architecture details |
| `docs/security/2026-03-17-browser-sandbox-advisory.md` | Security advisory for persistent browser profiles |
| `.claude/settings.local.json` | MCP plugin permissions (Playwright MCP authorized) |
| `.playwright-mcp/` | Playwright MCP console logs and downloaded files |

## Appendix B: Governance Zone Map for Revenue Sites

```
GREEN (owned, full trust)
  +-- github (rate: 30/min)
  +-- huggingface (rate: 20/min)
  +-- shopify (rate: 20/min)
  +-- stripe (rate: 25/min)
  +-- gumroad (rate: 15/min)
  +-- notion (rate: 30/min)
  +-- airtable (rate: 30/min)

YELLOW (external, elevated caution)
  +-- kdp.amazon.com (commerce)
  +-- patentcenter.uspto.gov (government)
  +-- colab.research.google.com (compute)
  +-- dev.to (publishing)
  +-- x.com (social)

RED (untrusted, requires explicit approval)
  +-- Unknown domains
  +-- Sites not in SERVICE_REGISTRY
```
