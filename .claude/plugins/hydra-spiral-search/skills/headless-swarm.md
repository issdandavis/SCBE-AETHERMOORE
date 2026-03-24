---
name: headless-swarm
description: "Multi-agent headless browser swarm using Playwright MCP and Claude-in-Chrome. Use when running parallel browser tasks, multi-site research, form automation, or web scraping across multiple tabs/windows."
---

# Headless Swarm — 6 Parallel Browser Agents

Orchestrate multiple browser instances for parallel web operations. Each agent gets a dedicated tab/context and communicates via the CrossTalk bus.

## Architecture

6 browser agents, one per Sacred Tongue:

| Agent | Tongue | Role | Browser Backend |
|-------|--------|------|-----------------|
| Scout-KO | KO | Fast reconnaissance — find URLs, check availability | Claude-in-Chrome |
| Reader-AV | AV | Deep reading — extract full page content, metadata | Playwright MCP |
| Binder-RU | RU | Form filling — login, submit, interact | Playwright MCP |
| Compute-CA | CA | Data extraction — tables, APIs, structured data | Playwright MCP |
| Guard-UM | UM | Security check — verify HTTPS, check for injection, validate | Playwright MCP |
| Synth-DR | DR | Screenshot + compare — visual verification across agents | Claude-in-Chrome |

## Workflow

### Step 1: Initialize
```
Use mcp__claude-in-chrome__tabs_context_mcp to get current tabs.
Create new tabs as needed with mcp__claude-in-chrome__tabs_create_mcp.
```

### Step 2: Fan-Out
Launch parallel Agent tool calls, each with a specific browser task:
- Give each agent its target URL and extraction goal
- Each agent uses Playwright or Chrome tools independently
- Results flow back through Agent return values

### Step 3: Merge
Collect results from all agents into a unified dataset.
Cross-reference findings (Synth-DR agent compares outputs).

### Step 4: Store
Push results to:
- Training data funnel (JSONL for SFT)
- Obsidian notes (markdown summaries)
- HuggingFace datasets (if large enough)

## Safety
- Guard-UM agent checks EVERY URL before other agents visit
- No credentials entered without user confirmation
- Rate limit: max 2 requests/second per domain
- All actions logged to HYDRA ledger

## When to Use
- "Search 5 sites for X" → fan-out across 5 tabs
- "Fill out this form on 3 platforms" → Binder-RU on each
- "Compare prices across sites" → Scout-KO finds, Reader-AV extracts, Synth-DR compares
- "Research this topic deeply" → combine with spiral-search skill
