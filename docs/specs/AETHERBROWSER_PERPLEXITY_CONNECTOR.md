# AetherBrowser Search Connector — Perplexity Replacement

## Goal
Replace $396/month Perplexity Enterprise with AetherBrowser's own search + AI pipeline, governed by SCBE's 14-layer stack.

## Perplexity APIs to Replicate

### 1. Search API (raw web results)
- Endpoint: `POST https://api.perplexity.ai/search`
- Returns: ranked web results with titles, URLs, snippets, content
- Features: domain filtering, language filtering, region filtering, multi-query
- **Our equivalent**: AetherBrowser crawl runner + frontier + search mesh
- **What we need**: A local search endpoint that aggregates results from multiple sources

### 2. Agent API (LLM + search)
- Endpoint: `POST https://api.perplexity.ai/chat/completions` (OpenAI compatible)
- Models: sonar, sonar-pro, sonar-reasoning
- Returns: AI-generated answers with citations from web search
- **Our equivalent**: AetherBrowser router + Claude/GPT/Grok providers
- **What we need**: Wire search results into LLM context window, return citations

### 3. Embeddings API
- Endpoint: `POST https://api.perplexity.ai/embeddings`
- Returns: vector embeddings for semantic search
- **Our equivalent**: HuggingFace phdm-21d-embedding model
- **What we need**: Local embedding endpoint or use HF inference API

## Connector Architecture

```
User Query
    |
    v
AetherBrowser Router (src/aetherbrowser/router.py)
    |
    ├── Search Phase (parallel)
    │   ├── Playwright/CDP web scraper
    │   ├── Google Custom Search API (free tier: 100/day)
    │   ├── Brave Search API (free tier: 2000/month)
    │   └── DuckDuckGo (no API key needed)
    │
    ├── Governance Gate (14-layer SCBE pipeline)
    │   └── Zone classification: GREEN/YELLOW/RED
    │
    ├── AI Synthesis Phase
    │   ├── Claude (primary — already paying $200/month)
    │   ├── GPT (fallback)
    │   └── Grok (fallback)
    │
    └── Response with Citations
```

## Pre-built Connector Config File

```json
{
  "connectors": {
    "search": {
      "brave": {
        "api_key_env": "BRAVE_SEARCH_API_KEY",
        "endpoint": "https://api.search.brave.com/res/v1/web/search",
        "free_tier": "2000 queries/month",
        "cost": "free"
      },
      "duckduckgo": {
        "package": "duckduckgo-search",
        "endpoint": "local",
        "free_tier": "unlimited",
        "cost": "free"
      },
      "google_cse": {
        "api_key_env": "GOOGLE_CSE_API_KEY",
        "cx_env": "GOOGLE_CSE_CX",
        "endpoint": "https://www.googleapis.com/customsearch/v1",
        "free_tier": "100 queries/day",
        "cost": "free"
      },
      "playwright": {
        "type": "scraper",
        "endpoint": "local",
        "free_tier": "unlimited",
        "cost": "free"
      }
    },
    "ai": {
      "claude": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "model": "claude-sonnet-4-20250514",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "cost": "included in Claude Max $200/month"
      },
      "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "cost": "pay per token"
      },
      "xai": {
        "api_key_env": "XAI_API_KEY",
        "model": "grok-3-mini",
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "cost": "pay per token"
      }
    },
    "embeddings": {
      "huggingface": {
        "api_key_env": "HF_TOKEN",
        "model": "issdandavis/phdm-21d-embedding",
        "endpoint": "https://api-inference.huggingface.co/models/",
        "cost": "free tier"
      }
    }
  },
  "governance": {
    "pipeline": "14-layer SCBE",
    "zone_gating": true,
    "red_zone_requires_approval": true
  }
}
```

## Cost Comparison

| Service | Perplexity Enterprise | AetherBrowser DIY |
|---------|----------------------|-------------------|
| Web search | included | FREE (Brave/DDG/Playwright) |
| AI answers | included | Claude Max ($200/mo — already paying) |
| Embeddings | included | FREE (HuggingFace) |
| Governance | none | 14-layer SCBE (our moat) |
| **Total** | **$396/month** | **$0 extra** |

## Implementation Priority
1. Build `src/aetherbrowser/search_connector.py` — aggregates Brave + DDG + Playwright
2. Build `src/aetherbrowser/search_synthesizer.py` — feeds results to Claude for AI answers
3. Wire into existing router at `src/aetherbrowser/router.py`
4. Add search endpoint to `src/aetherbrowser/serve.py`
5. Connect to AetherBrowser sidepanel UI

## Standalone App (Phase 2)
- Electron or Tauri wrapper around the sidepanel UI
- Embeds Chromium for browsing
- Runs search connector + AI synthesis locally
- Installable .exe for Windows
