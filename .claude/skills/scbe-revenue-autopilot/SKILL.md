---
name: scbe-revenue-autopilot
description: One-command revenue automation — check Stripe balance, npm/PyPI downloads, post articles to all platforms, run sell pipeline, generate daily revenue reports. Use when the user says "revenue", "money check", "daily report", "post everywhere", "sell", or "how are we doing financially".
---

# SCBE Revenue Autopilot

Automate every revenue-generating action from the terminal. No dashboards, no tab-hopping.

## When to Use This Skill

- User says "revenue check", "how's the money", "daily report", "are we making money"
- User says "post everywhere", "publish to all platforms", "blast it out"
- User says "sell", "run the sell pipeline", "push product"
- User says "check downloads", "check stripe", "check sponsors"
- User says "revenue autopilot" or invokes `/revenue-autopilot`
- At session start when doing a morning ops sweep

## Quick Commands (One-Liners)

```bash
# Full daily revenue check (Stripe + npm + PyPI + GitHub stars) -> JSON report
python scripts/system/daily_revenue_check.py

# Dry-run (no API calls, shows what would be checked)
python scripts/system/daily_revenue_check.py --dry-run

# Sell pipeline (Shopify publish + X post + connector health)
python scripts/system/sell_from_terminal.py
python scripts/system/sell_from_terminal.py --dry-run
python scripts/system/sell_from_terminal.py --x-text "New SCBE release — governance-first AI safety. Try it: npm i scbe-aethermoore"

# Post article to ALL platforms
python scripts/publish/post_all.py --file content/articles/YOUR_ARTICLE.md
python scripts/publish/post_all.py --file content/articles/YOUR_ARTICLE.md --dry-run

# Post to individual platforms
python scripts/publish/post_to_x.py --text "Your tweet"
python scripts/publish/post_to_x.py --thread content/articles/x_thread_FILE.md
python scripts/publish/post_to_devto.py --file content/articles/YOUR_ARTICLE.md
python scripts/publish/publish_discussions.py --file content/articles/YOUR_ARTICLE.md

# HYDRA content pipeline (governed 5-stage conveyor)
python -m hydra content scan
python -m hydra content publish

# Generate social media content for a topic
python scripts/publish/post_to_x.py --text "SCBE v3.2 ships a 14-layer harmonic security pipeline. Adversarial intent costs exponentially more. Open source: github.com/issdandavis/SCBE-AETHERMOORE"
```

---

## Action 1: Post Article to All Platforms

Publishes a single article to Dev.to, GitHub Discussions, HuggingFace, and X as a thread.

### Workflow

1. Verify the article exists and passes QA gate:
   ```bash
   python scripts/publish/content_qa.py --file content/articles/YOUR_ARTICLE.md
   ```
2. Post to GitHub Discussions (primary, always first):
   ```bash
   python scripts/publish/publish_discussions.py --file content/articles/YOUR_ARTICLE.md
   ```
3. Post to Dev.to (set canonical URL to GH Discussions link):
   ```bash
   python scripts/publish/post_to_devto.py --file content/articles/YOUR_ARTICLE.md
   ```
4. Post X thread (if `x_thread_*` version exists):
   ```bash
   python scripts/publish/post_to_x.py --thread content/articles/x_thread_YOUR_ARTICLE.md
   ```
5. Push dataset update to HuggingFace (if training-relevant):
   ```bash
   python src/knowledge/run_funnel.py --source local --push-hf
   ```

### One-liner (all platforms, governed)
```bash
python scripts/publish/post_all.py --file content/articles/YOUR_ARTICLE.md
```

### Required Env Vars
- `GITHUB_TOKEN` — GitHub PAT with discussion write scope
- `DEVTO_API_KEY` — Dev.to API key
- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` — X OAuth 1.0a
- `HF_TOKEN` — HuggingFace write token

---

## Action 2: Check Stripe Balance and Subscription Status

### Workflow

```bash
python scripts/system/daily_revenue_check.py --check stripe
```

Or manually via curl:
```bash
# Balance
curl -s https://api.stripe.com/v1/balance -u "$STRIPE_SECRET_KEY:" | python -m json.tool

# Recent charges (last 10)
curl -s "https://api.stripe.com/v1/charges?limit=10" -u "$STRIPE_SECRET_KEY:" | python -m json.tool

# Active subscriptions
curl -s "https://api.stripe.com/v1/subscriptions?status=active&limit=10" -u "$STRIPE_SECRET_KEY:" | python -m json.tool
```

### Required Env Vars
- `STRIPE_SECRET_KEY` — Stripe secret key (rk_live_* or sk_live_*)

### Output
- Balance available and pending amounts (per currency)
- Active subscription count and MRR estimate
- Last 10 charge amounts and dates

---

## Action 3: Check npm/PyPI Download Counts

### Workflow

```bash
python scripts/system/daily_revenue_check.py --check downloads
```

Or manually:
```bash
# npm weekly downloads
curl -s "https://api.npmjs.org/downloads/point/last-week/scbe-aethermoore" | python -m json.tool

# PyPI recent downloads (last 30 days via pypistats)
curl -s "https://pypistats.org/api/packages/scbe-aethermoore/recent" | python -m json.tool
```

### Required Env Vars
- None (public APIs)

### Output
- npm: weekly download count, package version
- PyPI: last-day, last-week, last-month download counts

---

## Action 4: Generate and Post Social Media Content

### Workflow

1. Draft a tweet or thread about a recent feature/release:
   ```bash
   # Single tweet
   python scripts/publish/post_to_x.py --text "SCBE ships post-quantum crypto + 14-layer harmonic security. Adversarial attacks cost exponentially more. npm i scbe-aethermoore"

   # Thread from file
   python scripts/publish/post_to_x.py --thread content/articles/x_thread_YOUR_TOPIC.md --dry-run
   python scripts/publish/post_to_x.py --thread content/articles/x_thread_YOUR_TOPIC.md
   ```

2. Schedule via Buffer (multi-platform):
   ```bash
   python scripts/publish/post_to_buffer.py --file content/articles/YOUR_ARTICLE.md
   ```

### Content Templates

**Product launch tweet:**
```
[Product name] just shipped [key feature].

[One-line value prop].

Try it: [link]

#AIGovernance #OpenSource #SCBE
```

**Metric milestone tweet:**
```
[metric] downloads this week on [platform].

[What the project does in one line].

Star it: github.com/issdandavis/SCBE-AETHERMOORE
```

### Required Env Vars
- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- `BUFFER_ACCESS_TOKEN` (optional, for scheduled posts)

---

## Action 5: Check Ko-fi and GitHub Sponsors Status

### Workflow

```bash
python scripts/system/daily_revenue_check.py --check sponsors
```

Or manually:
```bash
# GitHub Sponsors (requires PAT with read:org scope)
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ viewer { sponsorsListing { isPublic } sponsors(first:10) { totalCount nodes { sponsorEntity { ... on User { login } } } } } }"}' \
  https://api.github.com/graphql | python -m json.tool

# Ko-fi — no public API; check https://ko-fi.com/issdandavis manually
# or use the Ko-fi webhook integration if configured
```

### Required Env Vars
- `GITHUB_TOKEN` — with `read:org` scope for sponsors query
- Ko-fi: no API token needed (webhook-based or manual check)

### Output
- GitHub Sponsors count and list of sponsor usernames
- Ko-fi status (webhook data if available, otherwise "check manually" note)

---

## Action 6: Run the Sell Pipeline

The full terminal-first monetization pipeline.

### Workflow

```bash
# Full run: Shopify publish + X post + connector health
python scripts/system/sell_from_terminal.py --x-text "SCBE v3.2 — AI safety with teeth. npm i scbe-aethermoore"

# Dry run (check credentials, skip actual publish)
python scripts/system/sell_from_terminal.py --dry-run

# Skip Shopify, just post and check health
python scripts/system/sell_from_terminal.py --skip-shopify --x-text "New update!"

# Strict mode (fail on any connector health issue)
python scripts/system/sell_from_terminal.py --strict-health
```

### Required Env Vars
- `SHOPIFY_SHOP` or `SHOPIFY_SHOP_DOMAIN`
- `SHOPIFY_ACCESS_TOKEN` or `SHOPIFY_ADMIN_TOKEN`
- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- `STRIPE_SECRET_KEY`
- `GITHUB_TOKEN`, `NOTION_TOKEN`, `HF_TOKEN` (for health checks)

### Output
- Report at `artifacts/monetization/terminal_sell_report.json`
- Includes: secret summary (masked), action results, connector health

---

## Action 7: Generate Daily Revenue Report

Runs all checks and produces a single JSON report.

### Workflow

```bash
# Full daily check
python scripts/system/daily_revenue_check.py

# Output goes to artifacts/revenue/daily_check.json
# Also prints a one-line summary to stdout
```

### What It Checks
1. **Stripe**: balance (available + pending), active subscriptions, recent charges
2. **npm**: weekly downloads for `scbe-aethermoore`
3. **PyPI**: recent downloads (day/week/month) for `scbe-aethermoore`
4. **GitHub**: stars, forks, open issues, watchers for `issdandavis/SCBE-AETHERMOORE`

### Output Contract

Report saved to: `artifacts/revenue/daily_check.json`

```json
{
  "generated_at_utc": "2026-03-17T12:00:00+00:00",
  "stripe": {
    "status": "ok",
    "balance_available": [{"amount": 9774, "currency": "usd"}],
    "balance_pending": [{"amount": 0, "currency": "usd"}],
    "active_subscriptions": 0,
    "recent_charges_count": 5,
    "recent_charges_total_cents": 4900
  },
  "npm": {
    "status": "ok",
    "package": "scbe-aethermoore",
    "downloads_last_week": 142
  },
  "pypi": {
    "status": "ok",
    "package": "scbe-aethermoore",
    "downloads_last_day": 12,
    "downloads_last_week": 85,
    "downloads_last_month": 340
  },
  "github": {
    "status": "ok",
    "repo": "issdandavis/SCBE-AETHERMOORE",
    "stars": 23,
    "forks": 4,
    "open_issues": 12,
    "watchers": 23
  },
  "summary_line": "Stripe $97.74 avail | npm 142/wk | PyPI 340/mo | GH 23 stars"
}
```

### Required Env Vars
- `STRIPE_SECRET_KEY` — Stripe API key
- `GITHUB_TOKEN` — GitHub PAT (public repo data works without, but rate limits are low)

### One-line summary format
```
Stripe $97.74 avail | npm 142/wk | PyPI 340/mo | GH 23 stars
```

---

## Full Morning Autopilot Sequence

Run this every morning to get a complete revenue picture and push content:

```bash
# 1. Revenue snapshot
python scripts/system/daily_revenue_check.py

# 2. Sell pipeline (connector health + optional Shopify publish)
python scripts/system/sell_from_terminal.py --dry-run

# 3. Check for new articles ready to publish
python -m hydra content scan
python -m hydra content stats

# 4. Publish approved content
python -m hydra content publish

# 5. Post to X about latest work
python scripts/publish/post_to_x.py --text "Morning build. SCBE revenue autopilot running. Ship every day."
```

---

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Daily revenue check | `artifacts/revenue/daily_check.json` |
| Sell pipeline report | `artifacts/monetization/terminal_sell_report.json` |
| Content pipeline state | `artifacts/content_pipeline/pipeline_state.json` |
| Connector health | `artifacts/connector_health/terminal_sell_health.json` |
| Publish evidence | `artifacts/publish_browser/` |

---

## Integration with Existing Skills

| Skill | When to Chain |
|-------|--------------|
| `scbe-article-posting` | After drafting content, use for governed multi-platform publishing |
| `scbe-shopify-cli-windows` | For Shopify product management and catalog updates |
| `scbe-ops-control` | Cross-talk handoffs after revenue milestones |
| `scbe-training-pipeline` | Feed revenue/download data back into training datasets |
| `scbe-browser-swarm-ops` | For browser-based revenue tasks (Ko-fi, manual platforms) |

---

## Key Files

| File | Purpose |
|------|---------|
| `scripts/system/daily_revenue_check.py` | Daily revenue aggregator (Stripe + npm + PyPI + GitHub) |
| `scripts/system/sell_from_terminal.py` | Terminal-first sell pipeline (Shopify + X + health) |
| `scripts/publish/post_all.py` | Multi-platform article publisher |
| `scripts/publish/post_to_x.py` | X/Twitter OAuth publisher |
| `scripts/publish/post_to_devto.py` | Dev.to API publisher |
| `scripts/publish/publish_discussions.py` | GitHub Discussions publisher |
| `scripts/publish/post_to_buffer.py` | Buffer scheduled posting |
| `scripts/connector_health_check.py` | Connector health checker |
| `hydra/content_pipeline.py` | 5-stage governed content conveyor |

---

## Guardrails

1. Never log or print raw API keys/tokens. Use `src/security/secret_store.py` for masked output.
2. Always `--dry-run` first if unsure about a publish action.
3. Rate limits: Stripe (100/sec), npm registry (no auth needed), X (300 tweets/3hr), GitHub API (5000/hr authenticated).
4. Revenue reports go to `artifacts/revenue/` only -- never commit secrets into reports.
5. Cross-posted articles must set `canonical_url` to avoid SEO penalties.
6. The daily check script exits 0 even if individual APIs fail -- check the `status` field in each section of the JSON output.
