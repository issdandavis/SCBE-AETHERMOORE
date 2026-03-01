# Revenue Ops Plugin Design

**Date**: 2026-02-28
**Status**: Approved
**Plugin name**: `revenue-ops`
**Author**: Issac Davis (MoeShaun)

## Problem

The revenue pipeline from "product built" to "money in account" is entirely manual.
Four digital products sit as ZIPs, 85 content pieces wait in queue, 74 merch concepts
are designed but not listed. Every upload, post, and tracking step is a checklist item
done by hand across 6+ platforms. There is no unified status view and no way to know
what's listed where.

## Solution

A Claude Code plugin that wraps existing Python revenue scripts with slash commands
and an autonomous agent, adds browser automation for platforms without APIs (Gumroad,
Redbubble), and maintains a JSONL ledger synced to Airtable for tracking.

## Architecture

```
+-----------------------------------------------------+
|                  revenue-ops plugin                   |
+----------+----------+----------+-----------+---------+
| Commands |  Agents  |  Skill   |   Hook    | Ledger  |
| (4)      |  (2)     |  (1)     |   (1)     | (JSONL) |
+----------+----------+----------+-----------+---------+
|            Existing Python Scripts                     |
|  revenue_engine  shopify_bridge  package_products      |
|  content_spin    merch_pod_pipeline                    |
+-------------------------------------------------------+
|  Browser Agent (Playwright)                            |
|  Gumroad uploads  Redbubble uploads  POD setup         |
+-------------------------------------------------------+
|  Airtable Sync (Revenue Records)                       |
+-------------------------------------------------------+
```

## Components

### Commands (4)

| Command | Purpose | Implementation |
|---------|---------|---------------|
| `/revenue-status` | Dashboard showing products per platform, content posted, revenue, pending actions | Reads `artifacts/revenue/ledger.jsonl`, formats summary |
| `/list-product` | List a product on a platform | Runs `package_products.py` if needed, calls Shopify bridge or browser agent |
| `/push-content` | Post content to platforms | Picks from content queue, governs, posts, updates ledger |
| `/revenue-run` | Full pipeline cycle | Generate -> govern -> post -> list -> sync Airtable -> report |

### Agents (2)

**revenue-ops** — Main conversational agent for revenue operations.
- Handles natural language: "Push governance toolkit to Gumroad", "What sold this week?"
- Tools: Read, Write, Bash, Glob, Grep
- Triggers: user mentions revenue, products, selling, listings, content for revenue

**revenue-uploader** — Browser-driven upload agent for platforms without APIs.
- Uploads ZIPs to Gumroad (title, price, description, file attachment)
- Uploads art to Redbubble (PNG, product types, tags, markup)
- Visual verification of listings
- Tools: Playwright browser tools
- Triggers: from revenue-ops agent or /list-product when target is Gumroad/Redbubble

### Skill (1)

**revenue-pipeline** — Knowledge base for revenue operations:
- Platform upload flows (Gumroad, Shopify, Redbubble, Printful)
- Product catalog: 4 digital products with prices, descriptions, file locations
- Content queue structure and governance requirements
- Airtable schema for Revenue Records (appMDRF5kiLNWleI5)
- Pricing strategy and merch markup guidelines (20-30% above base)
- Social platform character limits and voice guidelines

### Hook (1)

**PostToolUse on Bash** — Watches for revenue script executions.
When detects `revenue_engine.py`, `shopify_bridge.py`, `package_products.py`,
`content_spin.py`, or `merch_pod_pipeline.py`, prompts Claude to update the
ledger with results.

### Revenue Ledger

Location: `artifacts/revenue/ledger.jsonl`

Schema per entry:
```json
{
  "ts": "ISO-8601 timestamp",
  "action": "product_listed|content_posted|revenue_recorded|upload_attempted|sync_airtable",
  "platform": "gumroad|shopify|redbubble|printful|linkedin|bluesky|mastodon|x|medium|huggingface",
  "product": "product slug or null",
  "title": "content title or null",
  "price": 0.00,
  "amount": 0.00,
  "url": "listing/post URL or null",
  "status": "live|draft|failed|pending",
  "metadata": {}
}
```

### Airtable Sync

Target: Revenue Records table in `appMDRF5kiLNWleI5`
Sync trigger: After each ledger write, push new entries to Airtable
Direction: Local ledger is source of truth, Airtable is read-friendly mirror

## Platforms (v1)

| Platform | Method | Product Types |
|----------|--------|--------------|
| Gumroad | Browser agent | Digital products (ZIPs) |
| Shopify | `shopify_bridge.py` | Digital products, POD merch |
| Redbubble | Browser agent | Character art merch |
| Printful | Via Shopify integration | POD merch |
| LinkedIn | `revenue_engine.py` | Long-form content |
| Bluesky | `revenue_engine.py` | Short-form content |
| Mastodon | `revenue_engine.py` | Short-form content |
| X/Twitter | `revenue_engine.py` | Short-form content |
| Medium | `revenue_engine.py` | Blog posts |
| HuggingFace | `revenue_engine.py` | Dataset/model cards |

## Existing Scripts (no changes needed)

| Script | Role |
|--------|------|
| `scripts/revenue_engine.py` | Content generation + governance + publishing |
| `scripts/shopify_bridge.py` | Shopify CLI + Admin API bridge |
| `scripts/package_products.py` | ZIP package builder |
| `scripts/content_spin.py` | 5 topics -> 63 variations |
| `scripts/merch_pod_pipeline.py` | Character art merch management |

## File Structure

```
revenue-ops/
  .claude-plugin/
    plugin.json
  skills/
    revenue-pipeline/
      SKILL.md
  commands/
    revenue-status.md
    list-product.md
    push-content.md
    revenue-run.md
  agents/
    revenue-ops.md
    revenue-uploader.md
  hooks/
    hooks.json
  README.md
```

## Success Criteria

1. `/revenue-status` shows a clear dashboard of all products and content across platforms
2. `/list-product governance` uploads the governance toolkit to Gumroad via browser
3. `/push-content linkedin` posts the next queued content piece to LinkedIn
4. `/revenue-run` executes the full pipeline end-to-end
5. Revenue ledger tracks every action with timestamps
6. Airtable Revenue Records stays in sync
7. User can say "list everything on Gumroad" and the agent handles it
