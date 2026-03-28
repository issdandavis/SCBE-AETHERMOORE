# AetherBrowser Multi-Model Parking System

**Concept**: Tiny models wait on tasks. Big models come in for heavy lifts. Nobody burns tokens waiting.

## The Problem

Right now: big expensive model ($0.01+/token) sits idle while waiting for:
- A web page to load
- A form to process
- An API to respond
- A build to complete
- A file to download

That's burning money on WAITING, not THINKING.

## The Solution: Model Parking

```
TINY MODEL (free/cheap) — parks on the task, watches, collects
  ↓ when ready
SUMMARY SHEET — chunks results into structured handoff
  ↓ when sheet is full
BIG MODEL (expensive) — comes in, reads the sheet, decides, acts
  ↓ done
TINY MODEL — takes over watching again
```

### Three Tiers

| Tier | Model | Cost | Role |
|------|-------|------|------|
| **Parker** | Qwen 0.5B / local GGUF / free HF inference | ~$0 | Wait, watch, collect, summarize |
| **Router** | Gemini Flash / GPT-4o-mini / Haiku | ~$0.001/call | Classify, route, decide if Big Model needed |
| **Heavy** | Claude Opus / GPT-4 / Gemini Ultra | ~$0.01+/call | Complex reasoning, code generation, decisions |

### How It Works

```
Task arrives
  → Router classifies: simple/medium/complex

SIMPLE → Parker handles entirely (free)
MEDIUM → Parker collects context, Router decides
COMPLEX → Parker collects, fills Summary Sheet, Heavy comes in

While waiting for external results:
  Parker watches (costs nothing)
  Parker logs checkpoints
  Parker fills the sheet line by line

When sheet is full OR external task completes:
  Heavy model reads the sheet (1 API call)
  Heavy decides + acts
  Heavy exits
  Parker resumes watching
```

## Summary Sheet Format

The sheet is what the tiny model fills out for the big model:

```json
{
  "task_id": "browse-research-arxiv-2026-03-27",
  "status": "ready_for_heavy",
  "context_chunks": [
    {"source": "arxiv.org/abs/2301.10226", "summary": "AI watermarking paper, 15 citations, relevant to SCBE L9", "tokens": 45},
    {"source": "page_2_results", "summary": "Found 3 related papers on hyperbolic embeddings", "tokens": 32},
    {"source": "form_status", "summary": "HuggingFace upload form ready, fields pre-filled", "tokens": 28}
  ],
  "total_context_tokens": 105,
  "decision_needed": "Should we cite paper 2301.10226 in our README and upload the new dataset?",
  "options": ["cite_and_upload", "cite_only", "skip"],
  "parker_recommendation": "cite_and_upload — paper directly describes our L9 technique",
  "time_waited": "4m 23s",
  "tokens_saved": "~12,000 (big model would have waited 4m at $0.01/token)"
}
```

## Free Compute Parking Spots

Places where a tiny model can "park" and wait for free:

| Spot | What It Does | Cost |
|------|-------------|------|
| HuggingFace Inference API (free tier) | Run small models | Free (rate limited) |
| Google Colab (free tier) | Run notebooks, wait on builds | Free (limited GPU) |
| Cloudflare Workers (free tier) | Edge compute, 100K req/day | Free |
| Local Ollama | Run GGUF models locally | Free (your hardware) |
| Replit free tier | Park a script, wait on webhooks | Free |
| GitHub Actions | Run on push/schedule | Free (2000 min/mo) |

## Narrow Entrance Architecture

The browser is a semi-closed network. Traffic routes through governed gates:

```
INTERNET
  ↓
TRUSTED SITES REGISTRY (config/security/trusted_external_sites.json)
  ↓ color-coded by tier
GOVERNANCE GATE (runtime_gate.py)
  ↓ ALLOW/QUARANTINE/DENY
MULTIPATH ROUTER
  ├── Direct (CORE sites — .gov, arxiv, GitHub)
  ├── Cached (frequently accessed, local mirror)
  ├── Tor (dark web research, .onion sites)
  └── Proxy (rate-limited sites, YouTube transcripts)
  ↓
CONTENT ARRIVES
  ↓
PARKER (tiny model) classifies + summarizes
  ↓ when needed
HEAVY (big model) decides + acts
```

### Multipath Traffic Optimization

Instead of one path to every site, the browser pre-routes:

| Destination | Path | Why |
|-------------|------|-----|
| GitHub API | Direct + cached | High frequency, auth'd |
| arXiv | Direct | CORE trust, no auth |
| HuggingFace | Direct + cached | Model/data operations |
| YouTube | Proxy + rate-limited | Transcript pulls get 429'd |
| .onion sites | Tor SOCKS5 | SpaceTor router |
| Unknown sites | Governance gate first | Classify before connecting |

## Credit-Saving Measures

| Technique | Savings |
|-----------|---------|
| Parker waits instead of Heavy | ~90% on idle time |
| Summary sheets compress context | ~70% fewer tokens for Heavy |
| Cached responses for repeated queries | ~50% on common operations |
| Local model for classification | 100% (no API cost) |
| Batch decisions (sheet fills up, one Heavy call) | ~80% vs per-item calls |
| Free compute parking spots | $0 for waiting |

## Pre-Prompting for Agentic Workflows

The browser pre-builds prompts based on the page context:

```
User navigates to github.com/issdandavis/SCBE-AETHERMOORE/pulls
  → Parker auto-generates: "There are 12 open PRs. 8 are dependabot.
     2 are feature branches. 2 are fix branches. Want me to review?"
  → User taps "review"
  → Parker fills Summary Sheet with each PR's diff stats
  → Heavy reads sheet, writes review for all 12 in one call
  → Cost: 1 Heavy call instead of 12
```

## Connection to Existing Systems

| Component | Role in Parking System |
|-----------|----------------------|
| Apollo email reader | Parker watches inbox, fills sheet when important email arrives |
| YouTube collector | Parker pulls transcripts (free API), sheets them for Heavy review |
| Tor sweeper | Parker crawls .onion sites, quarantines content, sheets for governance |
| Vault sync | Parker runs graph analysis, sheets orphan notes for Heavy to connect |
| Code governance gate | Router tier — classifies actions before they reach Heavy |
| Fibonacci trust | Parker builds trust over session, Heavy only called at TRUSTED+ level |

## Implementation Order

1. Summary Sheet format (JSON contract between Parker and Heavy)
2. Parker agent (local Ollama or free HF inference)
3. Router logic (when does Parker escalate to Heavy?)
4. Batch decision queue (collect sheets, one Heavy call per batch)
5. Free compute parking spot connectors
6. Multipath traffic router in AetherBrowser
