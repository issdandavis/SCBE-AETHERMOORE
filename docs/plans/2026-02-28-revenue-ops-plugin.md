# Revenue Ops Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Claude Code plugin that wraps the SCBE revenue pipeline into slash commands, agents, a skill, and a hook — with a JSONL ledger synced to Airtable.

**Architecture:** Thin plugin shell at `C:\Users\issda\.claude\plugins\revenue-ops\` with 4 commands calling existing Python scripts in `SCBE-AETHERMOORE/scripts/`, 2 agents (conversational + browser uploader), 1 knowledge skill, and 1 PostToolUse hook that tracks revenue actions in a JSONL ledger.

**Tech Stack:** Claude Code plugin system (markdown files, plugin.json), existing Python scripts (revenue_engine.py, shopify_bridge.py, package_products.py, content_spin.py), Playwright browser tools, Airtable API.

---

### Task 1: Create Plugin Scaffold

**Files:**
- Create: `C:\Users\issda\.claude\plugins\revenue-ops\.claude-plugin\plugin.json`
- Create: `C:\Users\issda\.claude\plugins\revenue-ops\README.md`
- Create directories: `skills/`, `commands/`, `agents/`, `hooks/`

**Step 1: Create plugin directory structure**

Run:
```bash
mkdir -p "C:/Users/issda/.claude/plugins/revenue-ops/.claude-plugin"
mkdir -p "C:/Users/issda/.claude/plugins/revenue-ops/skills/revenue-pipeline"
mkdir -p "C:/Users/issda/.claude/plugins/revenue-ops/commands"
mkdir -p "C:/Users/issda/.claude/plugins/revenue-ops/agents"
mkdir -p "C:/Users/issda/.claude/plugins/revenue-ops/hooks"
```

**Step 2: Write plugin.json**

Write to `C:\Users\issda\.claude\plugins\revenue-ops\.claude-plugin\plugin.json`:
```json
{
  "name": "revenue-ops",
  "version": "0.1.0",
  "description": "Revenue pipeline operations — list products, push content, track sales across Gumroad, Shopify, Redbubble, and social platforms. Wraps SCBE revenue scripts with slash commands, agents, and a JSONL ledger synced to Airtable.",
  "author": {
    "name": "Issac Davis (MoeShaun)",
    "email": "issdandavis@gmail.com"
  }
}
```

**Step 3: Write README.md**

Write to `C:\Users\issda\.claude\plugins\revenue-ops\README.md`:
```markdown
# revenue-ops

Revenue pipeline operations for SCBE-AETHERMOORE.

## Commands

| Command | Purpose |
|---------|---------|
| `/revenue-status` | Dashboard: products per platform, content posted, revenue, pending actions |
| `/list-product` | List a product on a platform (Gumroad, Shopify, Redbubble) |
| `/push-content` | Post content to social platforms from the content queue |
| `/revenue-run` | Full pipeline: generate -> govern -> post -> list -> sync |

## Agents

- **revenue-ops** — Conversational agent for natural language revenue operations
- **revenue-uploader** — Browser-driven upload agent for Gumroad/Redbubble

## Prerequisites

- Python 3.11+ with scripts in `C:\Users\issda\SCBE-AETHERMOORE\scripts\`
- Playwright plugin enabled (for browser uploads)
- Environment variables: SHOPIFY_SHOP, AIRTABLE_API_KEY, AIRTABLE_BASE_ID

## Ledger

All actions are tracked in `C:\Users\issda\SCBE-AETHERMOORE\artifacts\revenue\ledger.jsonl`
```

**Step 4: Create the revenue ledger directory**

Run:
```bash
mkdir -p "C:/Users/issda/SCBE-AETHERMOORE/artifacts/revenue"
```

**Step 5: Commit**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git init && git add -A && git commit -m "feat: scaffold revenue-ops plugin structure"
```

---

### Task 2: Create `/revenue-status` Command

**Files:**
- Create: `C:\Users\issda\.claude\plugins\revenue-ops\commands\revenue-status.md`

**Step 1: Write the command file**

Write to `C:\Users\issda\.claude\plugins\revenue-ops\commands\revenue-status.md`:
```markdown
---
name: revenue-status
description: "Show revenue dashboard — products listed, content posted, sales, pending actions"
allowed-tools: ["Bash", "Read", "Glob"]
---

# Revenue Status Dashboard

Show the user a complete revenue status report.

## Steps

1. Read the product catalog to show what's built:
```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/package_products.py --list
```

2. Read the revenue ledger for recent activity:
- File: `C:\Users\issda\SCBE-AETHERMOORE\artifacts\revenue\ledger.jsonl`
- If file doesn't exist, report "No activity tracked yet"
- Parse each JSONL line and group by action type

3. Check content queue size:
```bash
ls C:\Users\issda\SCBE-AETHERMOORE\artifacts\content_queue/*.json 2>/dev/null | wc -l
```

4. Check spin queue size:
```bash
ls C:\Users\issda\SCBE-AETHERMOORE\artifacts\spin_queue/*.json 2>/dev/null | wc -l
```

5. Present a dashboard like this:

```
REVENUE DASHBOARD
=================

PRODUCTS (4 built)
  [n8n]         $49  — Gumroad: not listed | Shopify: not listed
  [governance]  $29  — Gumroad: not listed | Shopify: not listed
  [spin]        $19  — Gumroad: not listed | Shopify: not listed
  [hydra]        $9  — Gumroad: not listed | Shopify: not listed

CONTENT
  Queue: 85 pieces | Spin: 63 variations | Posted this week: 0

MERCH
  Redbubble: 0/11 designs listed | Printful: 0/74 variants

REVENUE (last 30 days)
  Total: $0.00 | Gumroad: $0 | Shopify: $0

PENDING ACTIONS
  1. List 4 products on Gumroad (use /list-product)
  2. Post 5 content pieces (use /push-content)
  3. Upload character art to Redbubble (use /list-product redbubble)
```

6. Cross-reference with ledger to fill in actual "listed" / "posted" / "revenue" values.

## Tips
- If the ledger is empty, emphasize the "PENDING ACTIONS" section
- Always show the next 3 most impactful actions the user can take
```

**Step 2: Verify file exists and is valid markdown**

Run:
```bash
cat "C:/Users/issda/.claude/plugins/revenue-ops/commands/revenue-status.md" | head -5
```
Expected: Shows the frontmatter starting with `---`

**Step 3: Commit**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git add commands/revenue-status.md && git commit -m "feat: add /revenue-status command"
```

---

### Task 3: Create `/list-product` Command

**Files:**
- Create: `C:\Users\issda\.claude\plugins\revenue-ops\commands\list-product.md`

**Step 1: Write the command file**

Write to `C:\Users\issda\.claude\plugins\revenue-ops\commands\list-product.md`:
```markdown
---
name: list-product
description: "List a product on a platform (Gumroad, Shopify, or Redbubble)"
argument-hint: "[product] [platform]"
allowed-tools: ["Bash", "Read", "Write", "Glob", "Agent"]
---

# List Product

List a digital product or merch on a selling platform.

## Arguments

- `product`: Product key (n8n, governance, spin, hydra, merch, all) — or omit to see catalog
- `platform`: Target platform (gumroad, shopify, redbubble) — or omit to list on all

Examples:
- `/list-product` — show product catalog and ask what to list
- `/list-product governance gumroad` — list governance toolkit on Gumroad
- `/list-product all gumroad` — list all 4 products on Gumroad
- `/list-product merch redbubble` — upload character art to Redbubble

## Steps

### If no arguments: Show catalog
```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/package_products.py --list
```
Then ask: "Which product and platform?"

### If product + platform specified:

1. **Ensure ZIP is built** (for digital products):
```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/package_products.py [product_key]
```

2. **Route by platform**:

   **Gumroad**: Launch the `revenue-uploader` agent to:
   - Navigate to gumroad.com/products/new
   - Fill: title, price, description (from product README)
   - Upload the ZIP file from `artifacts/products/`
   - Capture the listing URL

   **Shopify**: Run shopify_bridge.py:
   ```bash
   cd C:\Users\issda\SCBE-AETHERMOORE
   python scripts/shopify_bridge.py products
   ```

   **Redbubble**: Launch the `revenue-uploader` agent to:
   - Navigate to redbubble.com/portfolio/manage
   - Upload each character art PNG
   - Enable product types, set tags and markup
   - Read manifest from `artifacts/products/redbubble_manifest.json`

3. **Update ledger** after successful listing:
   Append to `C:\Users\issda\SCBE-AETHERMOORE\artifacts\revenue\ledger.jsonl`:
   ```json
   {"ts":"[ISO-8601]","action":"product_listed","platform":"[platform]","product":"[slug]","price":[price],"url":"[url]","status":"live"}
   ```

4. **Report result** to user with listing URL and next suggested action.
```

**Step 2: Commit**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git add commands/list-product.md && git commit -m "feat: add /list-product command"
```

---

### Task 4: Create `/push-content` Command

**Files:**
- Create: `C:\Users\issda\.claude\plugins\revenue-ops\commands\push-content.md`

**Step 1: Write the command file**

Write to `C:\Users\issda\.claude\plugins\revenue-ops\commands\push-content.md`:
```markdown
---
name: push-content
description: "Post content to social platforms from the queue"
argument-hint: "[platform] [count]"
allowed-tools: ["Bash", "Read", "Write", "Glob"]
---

# Push Content

Post content from the queue to social platforms.

## Arguments

- `platform`: Target (linkedin, bluesky, mastodon, x, medium, all) — or omit for all
- `count`: Number of pieces to post (default: 5)

Examples:
- `/push-content` — post 5 pieces across all platforms
- `/push-content linkedin 3` — post 3 pieces to LinkedIn
- `/push-content all 10` — post 10 pieces across all platforms

## Steps

1. **Check content queue**:
```bash
ls C:\Users\issda\SCBE-AETHERMOORE\artifacts\content_queue/*.json 2>/dev/null | wc -l
```

2. **If queue is empty, generate content**:
```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/revenue_engine.py generate
```

3. **Select pieces** for the target platform:
   - Read JSON files from `artifacts/content_queue/`
   - Filter by platform if specified
   - Pick the top N pieces (by governance score, highest first)

4. **Governance scan** each piece:
```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/revenue_engine.py publish
```

5. **Present content** to user for approval before posting:
   Show each piece with title, platform, body preview (first 100 chars), governance score.
   Ask: "Post these? (y/n/edit)"

6. **Post** (currently the scripts write to queue; actual posting needs platform API keys):
   - Twitter/X: Needs TWITTER_BEARER_TOKEN
   - LinkedIn: Needs LINKEDIN_ACCESS_TOKEN
   - Bluesky: Needs BLUESKY_DID + BLUESKY_TOKEN
   - Mastodon: Needs MASTODON_INSTANCE + MASTODON_TOKEN
   - Medium: Needs MEDIUM_TOKEN

   If tokens are missing, show the content and provide copy-paste-ready text for manual posting.

7. **Update ledger** for each posted piece:
   ```json
   {"ts":"[ISO-8601]","action":"content_posted","platform":"[platform]","title":"[title]","status":"posted"}
   ```

8. **Report**: "Posted X pieces to Y platforms. Z in queue remaining."
```

**Step 2: Commit**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git add commands/push-content.md && git commit -m "feat: add /push-content command"
```

---

### Task 5: Create `/revenue-run` Command

**Files:**
- Create: `C:\Users\issda\.claude\plugins\revenue-ops\commands\revenue-run.md`

**Step 1: Write the command file**

Write to `C:\Users\issda\.claude\plugins\revenue-ops\commands\revenue-run.md`:
```markdown
---
name: revenue-run
description: "Run the full revenue pipeline: generate -> govern -> post -> list -> sync"
allowed-tools: ["Bash", "Read", "Write", "Glob", "Agent"]
---

# Full Revenue Pipeline Run

Execute the complete revenue cycle in order.

## Pipeline Steps

1. **Package products** (ensure ZIPs are fresh):
```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/package_products.py
```

2. **Generate content** (create new pieces from topic seeds):
```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/revenue_engine.py generate
```

3. **Spin content** (create platform variations):
```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/content_spin.py
```

4. **Governance scan** all content:
```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts/revenue_engine.py publish
```

5. **Show summary** and ask user what to push:
   - N products ready to list (which platforms?)
   - N content pieces passed governance (post now?)
   - N merch designs ready (upload to Redbubble?)

6. **Execute** user-approved actions:
   - For product listings: delegate to `/list-product` logic
   - For content posting: delegate to `/push-content` logic
   - For merch uploads: launch `revenue-uploader` agent

7. **Sync to Airtable**:
   Read `artifacts/revenue/ledger.jsonl` and push new entries to Airtable Revenue Records.
   ```bash
   cd C:\Users\issda\SCBE-AETHERMOORE
   python -c "
   import json, os, requests
   AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY', '')
   BASE_ID = 'appMDRF5kiLNWleI5'
   TABLE = 'Revenue Records'
   ledger = 'artifacts/revenue/ledger.jsonl'
   if not AIRTABLE_API_KEY:
       print('AIRTABLE_API_KEY not set — skip sync')
   elif not os.path.exists(ledger):
       print('No ledger yet — skip sync')
   else:
       entries = [json.loads(l) for l in open(ledger) if l.strip()]
       print(f'Syncing {len(entries)} entries to Airtable...')
       # Actual sync would POST to Airtable API here
       print('Sync complete')
   "
   ```

8. **Final report**: Show `/revenue-status` dashboard with updated numbers.

## Tips
- This command is the "do everything" button
- Always show what will happen before doing it
- Never auto-post without user confirmation
```

**Step 2: Commit**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git add commands/revenue-run.md && git commit -m "feat: add /revenue-run full pipeline command"
```

---

### Task 6: Create `revenue-ops` Agent

**Files:**
- Create: `C:\Users\issda\.claude\plugins\revenue-ops\agents\revenue-ops.md`

**Step 1: Write the agent file**

Write to `C:\Users\issda\.claude\plugins\revenue-ops\agents\revenue-ops.md`:
```markdown
---
identifier: revenue-ops
whenToUse: >-
  Use this agent when the user discusses revenue, selling, product listings, content
  publishing for monetization, or sales tracking. Trigger when user mentions "revenue",
  "sell", "list on Gumroad", "list on Shopify", "push to Redbubble", "content queue",
  "what sold", "how's revenue", "monetize", "product pipeline", or asks about the
  status of digital products, merch, or content across selling platforms.
model: sonnet
color: green

<example>
user: "Push the governance toolkit to Gumroad"
assistant: "I'll use the revenue-ops agent to package and list the governance toolkit on Gumroad."
</example>

<example>
user: "What's our revenue situation?"
assistant: "Let me use the revenue-ops agent to pull the revenue dashboard and ledger status."
</example>

<example>
user: "Generate some LinkedIn content and queue it"
assistant: "I'll use the revenue-ops agent to generate and govern LinkedIn content from our topic seeds."
</example>

<example>
user: "List everything we have on all platforms"
assistant: "Let me launch the revenue-ops agent to list all products across Gumroad, Shopify, and Redbubble."
</example>
---

You are the SCBE Revenue Operations agent. You manage the full pipeline from built products to money in account.

## Your Tools

You wrap these existing Python scripts in `C:\Users\issda\SCBE-AETHERMOORE\scripts\`:

| Script | Command | Purpose |
|--------|---------|---------|
| `package_products.py` | `python scripts/package_products.py [key]` | Build ZIP packages |
| `revenue_engine.py` | `python scripts/revenue_engine.py [cmd]` | Generate/publish content |
| `shopify_bridge.py` | `python scripts/shopify_bridge.py [cmd]` | Shopify operations |
| `content_spin.py` | `python scripts/content_spin.py` | Content multiplication |
| `merch_pod_pipeline.py` | `python scripts/merch_pod_pipeline.py` | Merch management |

Always `cd C:\Users\issda\SCBE-AETHERMOORE` before running scripts.

## Product Catalog

| Key | Name | Price | ZIP |
|-----|------|-------|-----|
| n8n | SCBE n8n Workflow Starter Pack | $49 | scbe-n8n-workflow-pack-v1.0.0.zip |
| governance | AI Governance Toolkit | $29 | scbe-ai-governance-toolkit-v1.0.0.zip |
| spin | Content Spin Engine | $19 | scbe-content-spin-engine-v1.0.0.zip |
| hydra | HYDRA Agent Templates | $9 | scbe-hydra-agent-templates-v1.0.0.zip |

ZIPs are in: `C:\Users\issda\SCBE-AETHERMOORE\artifacts\products\`

## Revenue Ledger

Location: `C:\Users\issda\SCBE-AETHERMOORE\artifacts\revenue\ledger.jsonl`

After every revenue action, append a JSONL line:
```json
{"ts":"2026-02-28T10:00:00Z","action":"product_listed","platform":"gumroad","product":"scbe-n8n-workflow-pack","price":49.00,"url":"https://...","status":"live"}
```

Action types: `product_listed`, `content_posted`, `revenue_recorded`, `upload_attempted`, `sync_airtable`

## Platforms

| Platform | Method | For |
|----------|--------|-----|
| Gumroad | Browser (revenue-uploader agent) | Digital products |
| Shopify | shopify_bridge.py | Digital products + POD |
| Redbubble | Browser (revenue-uploader agent) | Character art merch |
| LinkedIn | revenue_engine.py | Long-form content |
| Bluesky | revenue_engine.py | Short-form content |
| Mastodon | revenue_engine.py | Short-form content |
| X/Twitter | revenue_engine.py | Short-form content |
| Medium | revenue_engine.py | Blog posts |

## Rules

1. Always check the ledger before listing — don't double-list products
2. Always run governance scan before posting content
3. Never auto-post without showing the user what will be posted first
4. Update the ledger after every successful action
5. If a platform API key is missing, provide copy-paste-ready content for manual posting
6. For Gumroad/Redbubble uploads, delegate to the `revenue-uploader` agent
```

**Step 2: Commit**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git add agents/revenue-ops.md && git commit -m "feat: add revenue-ops conversational agent"
```

---

### Task 7: Create `revenue-uploader` Agent

**Files:**
- Create: `C:\Users\issda\.claude\plugins\revenue-ops\agents\revenue-uploader.md`

**Step 1: Write the agent file**

Write to `C:\Users\issda\.claude\plugins\revenue-ops\agents\revenue-uploader.md`:
```markdown
---
identifier: revenue-uploader
whenToUse: >-
  Use this agent when products need to be uploaded to platforms that require browser
  interaction — specifically Gumroad (digital product uploads) and Redbubble (art/merch
  uploads). Trigger when the revenue-ops agent or /list-product command needs to upload
  files to a platform without a direct API. Also trigger when user says "upload to
  Gumroad", "list on Redbubble", "upload merch", or "upload product to [platform]".
model: sonnet
color: orange

<example>
user: "Upload the governance toolkit to Gumroad"
assistant: "I'll use the revenue-uploader agent to navigate Gumroad and upload the product."
</example>

<example>
user: "Put all the character art on Redbubble"
assistant: "Let me launch the revenue-uploader agent to upload each character design to Redbubble."
</example>

<example>
user: "List the n8n workflow pack on Gumroad for $49"
assistant: "I'll use the revenue-uploader agent to create the Gumroad listing."
</example>
---

You are the Revenue Uploader — a browser automation agent that uploads products to selling platforms.

## Gumroad Upload Flow

To list a digital product on Gumroad:

1. Navigate to `https://gumroad.com` and check login status
2. If not logged in, tell the user to log in first, then resume
3. Navigate to `https://gumroad.com/products/new`
4. Fill product form:
   - **Name**: Product name from catalog
   - **Price**: Product price
   - **Description**: Copy from product README in `artifacts/products/[product-dir]/README.md`
   - **File**: Upload ZIP from `artifacts/products/[slug]-v[version].zip`
5. Click "Add product" or equivalent submit button
6. Capture the product URL from the success page
7. Return the URL for ledger tracking

## Redbubble Upload Flow

To upload character art:

1. Read the manifest: `C:\Users\issda\SCBE-AETHERMOORE\artifacts\products\redbubble_manifest.json`
2. Navigate to `https://www.redbubble.com/portfolio/manage`
3. If not logged in, tell the user to log in first
4. For each design in the manifest:
   - Click "Add new work"
   - Upload the PNG file
   - Set title, tags (aethermoor, fantasy art, character names)
   - Enable all product types
   - Set markup to 25% above base
   - Save/publish
5. Report how many designs were uploaded

## Browser Tools

Use Playwright browser tools:
- `browser_navigate` to go to URLs
- `browser_snapshot` to see the current page
- `browser_click` to interact with elements
- `browser_fill_form` to enter text
- `browser_file_upload` to upload files
- `browser_take_screenshot` for verification

## Rules

1. Always take a screenshot after each major step for verification
2. If login is required, pause and ask the user to log in manually
3. Never store or handle passwords
4. If an upload fails, report the error and suggest manual fallback
5. After successful upload, return the listing URL for the ledger
```

**Step 2: Commit**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git add agents/revenue-uploader.md && git commit -m "feat: add revenue-uploader browser agent"
```

---

### Task 8: Create `revenue-pipeline` Skill

**Files:**
- Create: `C:\Users\issda\.claude\plugins\revenue-ops\skills\revenue-pipeline\SKILL.md`

**Step 1: Write the skill file**

Write to `C:\Users\issda\.claude\plugins\revenue-ops\skills\revenue-pipeline\SKILL.md`:
```markdown
---
name: revenue-pipeline
description: >-
  Use this skill when working on revenue operations, product listings, content
  publishing for monetization, merch pipeline, or sales tracking across Gumroad,
  Shopify, Redbubble, and social platforms. Triggers when user asks about "revenue
  pipeline", "product catalog", "content queue", "merch", "how to list", "pricing
  strategy", "upload to [platform]", or revenue-related workflow decisions.
---

# Revenue Pipeline Operations

## Product Catalog

Four digital products built as ZIPs in `SCBE-AETHERMOORE/artifacts/products/`:

| Product | Slug | Price | Script |
|---------|------|-------|--------|
| SCBE n8n Workflow Starter Pack | scbe-n8n-workflow-pack | $49 | `package_products.py n8n` |
| AI Governance Toolkit | scbe-ai-governance-toolkit | $29 | `package_products.py governance` |
| Content Spin Engine | scbe-content-spin-engine | $19 | `package_products.py spin` |
| HYDRA Agent Templates | scbe-hydra-agent-templates | $9 | `package_products.py hydra` |

Build all: `python scripts/package_products.py`
List all: `python scripts/package_products.py --list`

## Content Pipeline

Content flows: Topic Seeds -> Generation -> Governance Scan -> Queue -> Platform Post

- **Generate**: `python scripts/revenue_engine.py generate` — 5 topics x 5 platforms = 25 pieces
- **Spin**: `python scripts/content_spin.py` — Fibonacci multiplication to 63+ variations
- **Publish**: `python scripts/revenue_engine.py publish` — governance scan + queue
- **Full**: `python scripts/revenue_engine.py full` — generate + publish in one

Content queue: `artifacts/content_queue/*.json`
Spin queue: `artifacts/spin_queue/*.json`

## Platform-Specific Notes

### Gumroad
- No API needed for basic listing — use browser
- Support email delivery and PDF watermarking
- Cover images from Adobe Express character art
- Copy product descriptions from README.md in each ZIP

### Shopify
- Store: `lucrative-sponsorship-app-1`
- Bridge: `scripts/shopify_bridge.py`
- Commands: `status`, `products`, `blog`, `theme`, `app`
- Env: `SHOPIFY_SHOP` environment variable
- Printful app for POD merch

### Redbubble
- Upload individual PNGs (character portraits from Adobe Express)
- Enable all product types per design
- Tags: aethermoor, fantasy art, character names
- Markup: 20-30% above base price
- Manifest: `artifacts/products/redbubble_manifest.json`

### Social Platforms
- Twitter/X: 280 chars, needs TWITTER_BEARER_TOKEN
- LinkedIn: 3000 chars, needs LINKEDIN_ACCESS_TOKEN
- Bluesky: short, needs BLUESKY_DID + BLUESKY_TOKEN
- Mastodon: short, needs MASTODON_INSTANCE + MASTODON_TOKEN
- Medium: blog posts, needs MEDIUM_TOKEN

## Revenue Ledger

File: `artifacts/revenue/ledger.jsonl`
Each line is a JSON object with:
- `ts` — ISO-8601 timestamp
- `action` — product_listed, content_posted, revenue_recorded, upload_attempted, sync_airtable
- `platform` — gumroad, shopify, redbubble, linkedin, bluesky, mastodon, x, medium, huggingface
- `product` — product slug or null
- `title` — content title or null
- `price` / `amount` — dollar values
- `url` — listing or post URL
- `status` — live, draft, failed, pending

## Airtable Sync

- Base: `appMDRF5kiLNWleI5` (Aethermoor Bug & Project Tracker)
- Table: Revenue Records
- Sync: push new ledger entries after each action
- Env: `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`

## Governance

All content passes through L14 governance scan before posting:
- Safety check (antivirus membrane)
- Quality check (length, links, tags)
- AI detection resistance (marker scanning)
- Rate limiting (max 10 posts/day)
- Score >= 0.5 required to pass

## Merch Pipeline

- 11 character designs (Eldrin, Aria, Polly, Kael, Zara, Spirit, Izack, Clay, World Tree, logo, infographic)
- 8 product types per design (t-shirts, hoodies, posters, mugs, phone cases, tote bags, stickers, canvas)
- 74+ merch variants total
- Script: `scripts/merch_pod_pipeline.py`
- Payloads: `artifacts/products/printful_payloads.json`

## Pricing Strategy

- Digital products: $9-$49 (value-based)
- Merch: 20-30% markup above POD base cost
- Kindle (Avalon Codex): $4.99 ebook, $14.99 paperback
- Future SaaS: tiered monthly (see M5 Mesh Product Blueprint)
```

**Step 2: Commit**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git add skills/ && git commit -m "feat: add revenue-pipeline knowledge skill"
```

---

### Task 9: Create PostToolUse Hook

**Files:**
- Create: `C:\Users\issda\.claude\plugins\revenue-ops\hooks\hooks.json`

**Step 1: Write the hooks.json file**

Write to `C:\Users\issda\.claude\plugins\revenue-ops\hooks\hooks.json`:
```json
[
  {
    "event": "PostToolUse",
    "tool": "Bash",
    "type": "prompt",
    "prompt": "If the Bash command just executed involved any of these revenue scripts: revenue_engine.py, shopify_bridge.py, package_products.py, content_spin.py, or merch_pod_pipeline.py — then append a ledger entry to C:\\Users\\issda\\SCBE-AETHERMOORE\\artifacts\\revenue\\ledger.jsonl describing what happened. Use this JSON format on one line: {\"ts\":\"ISO-8601\",\"action\":\"[type]\",\"platform\":\"[platform]\",\"product\":\"[slug or null]\",\"title\":\"[title or null]\",\"price\":0,\"amount\":0,\"url\":\"\",\"status\":\"[status]\",\"metadata\":{}}. If the command was not a revenue script, do nothing."
  }
]
```

**Step 2: Commit**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git add hooks/ && git commit -m "feat: add PostToolUse hook for revenue ledger tracking"
```

---

### Task 10: Validate Plugin

**Step 1: Run plugin-validator agent**

Use the `plugin-dev:plugin-validator` agent to validate the complete plugin at `C:\Users\issda\.claude\plugins\revenue-ops\`.

**Step 2: Fix any critical issues found by the validator**

Common things to check:
- plugin.json has correct schema
- All command frontmatter fields are valid
- Agent frontmatter has required fields (identifier, whenToUse, model)
- Skill SKILL.md has name and description in frontmatter
- hooks.json is valid JSON array

**Step 3: Run skill-reviewer agent on the revenue-pipeline skill**

Use the `plugin-dev:skill-reviewer` agent to review skill quality.

**Step 4: Fix any issues and commit**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git add -A && git commit -m "fix: address validation findings"
```

---

### Task 11: Test Plugin

**Step 1: Verify plugin loads in Claude Code**

The plugin should be auto-discovered at `C:\Users\issda\.claude\plugins\revenue-ops\` since it's in the user's plugins directory.

Start a new Claude Code session and check:
- `/revenue-status` appears as a command
- `/list-product` appears as a command
- `/push-content` appears as a command
- `/revenue-run` appears as a command

**Step 2: Test /revenue-status**

Run `/revenue-status` and verify it shows the product catalog and pending actions.

**Step 3: Test revenue-ops agent triggering**

Say "what's our revenue situation?" and verify the revenue-ops agent is suggested/used.

**Step 4: Verify ledger directory exists**

```bash
ls -la C:/Users/issda/SCBE-AETHERMOORE/artifacts/revenue/
```

**Step 5: Final commit with any test fixes**

```bash
cd "C:/Users/issda/.claude/plugins/revenue-ops"
git add -A && git commit -m "test: verify plugin loads and commands work"
```
