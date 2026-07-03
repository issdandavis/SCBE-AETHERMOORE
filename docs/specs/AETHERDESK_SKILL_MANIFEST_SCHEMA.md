# AetherDesk Skill Manifest Schema

Date: 2026-06-27
Status: draft v1
Scope: local-first AetherDesk skills, browser presets, CLI/MCP routes, and future training examples

## Purpose

AetherDesk skills should not stay as loose UI cards. Each skill needs a small manifest that can be rendered in the desktop, called by an agent, audited by a human, and converted into training examples.

This schema defines the local contract for that manifest.

## Design rules

- Local-first by default.
- Browser-visible data must not include raw secrets.
- Any network action must declare its purpose and stop rule.
- Any terminal action must route through an allowlisted profile.
- Paid cloud, training, publishing, deletion, and long polling require explicit approval.
- Every skill must describe what receipt it leaves behind.
- Human-authored open-source guides should be added when license-compatible and relevant.

## Manifest shape

```json
{
  "schema": "aetherdesk.skill.v1",
  "id": "browser-audit",
  "version": "0.1.0",
  "title": "Browser Audit",
  "shortTitle": "Audit",
  "category": "research",
  "status": "draft",
  "risk": "medium",
  "summary": "Review a page, collect sources, and produce a concise audit with receipts.",
  "userGoal": "I want a sourced answer without exposing tokens or launching uncontrolled browser automation.",
  "routes": {
    "primaryApp": "browser",
    "secondaryApps": ["notebook", "terminal"],
    "cliCommand": "aether skill run browser-audit",
    "mcpTool": "aether.skill.browser_audit"
  },
  "inputs": [
    {
      "name": "url",
      "type": "url",
      "required": false,
      "description": "The page or site to inspect."
    },
    {
      "name": "question",
      "type": "text",
      "required": true,
      "description": "The user's research question."
    }
  ],
  "outputs": [
    {
      "name": "answer",
      "type": "markdown",
      "description": "Short answer with source references."
    },
    {
      "name": "receipt",
      "type": "json",
      "description": "Actions taken, sources used, stop conditions, and any skipped checks."
    }
  ],
  "permissions": {
    "network": "ask",
    "filesystem": "local-notes-only",
    "terminalProfile": "none",
    "secrets": "server-side-only",
    "paidCompute": "forbidden-without-approval"
  },
  "modelPolicy": {
    "preferred": "local",
    "fallback": "manual",
    "remoteAllowed": false,
    "trainingAllowed": false
  },
  "browserPolicy": {
    "modes": ["answer", "browse", "audit", "agent"],
    "maxInitialFetches": 1,
    "polling": "off-by-default",
    "sourceRequirement": "cite-links-when-network-used"
  },
  "receipts": {
    "required": true,
    "pathHint": "docs/product-manual/AUTOLOG.jsonl",
    "fields": ["timestamp", "skillId", "actions", "sources", "files", "stopReason"]
  },
  "training": {
    "includeInSft": true,
    "holdoutRequired": true,
    "negativeExamples": ["secret-in-browser", "unbounded-polling", "unsourced-answer"]
  },
  "openSourceGuides": [
    {
      "title": "Human-authored guide or docs source",
      "url": "https://example.org",
      "license": "unknown",
      "usage": "reference-only-until-license-confirmed"
    }
  ],
  "ui": {
    "accent": "blue",
    "icon": "globe",
    "primaryAction": "Open in Browser",
    "secondaryActions": ["Save note", "Create task"]
  }
}
```

## Required fields

| Field | Required | Notes |
|---|---:|---|
| `schema` | yes | Must be `aetherdesk.skill.v1`. |
| `id` | yes | Lowercase slug. Stable across releases. |
| `version` | yes | Semver for the manifest, not the app. |
| `title` | yes | Human-readable name. |
| `category` | yes | One of the known skill categories below. |
| `status` | yes | `draft`, `local`, `verified`, `deprecated`. |
| `risk` | yes | `low`, `medium`, `high`. |
| `summary` | yes | One sentence. |
| `routes.primaryApp` | yes | Where the skill opens first. |
| `permissions` | yes | Explicit boundary declaration. |
| `receipts.required` | yes | Product skills should leave receipts. |

## Categories

Initial copied skill categories:

| Category | Examples |
|---|---|
| `research` | Deep Research, Browser Audit, Grounding, TOS Scanner |
| `build` | Docs Builder, Slides Builder, Design System Extractor |
| `analysis` | SQL Insight, Sheet Analyzer, Weighted Scorer |
| `security` | Secure Code Review, Compliance Checklist |
| `testing` | Test Suite Architect, Agent Training Dashboard |
| `business` | Pricing Lab, SaaS Metrics, Campaign Planner |
| `workflow` | Long-Form Workflow, Process Doc, Structured Minutes |
| `style` | Theme Factory, Copy Edit, Humanizer |

## Permission levels

| Permission | Values | Meaning |
|---|---|---|
| `network` | `none`, `ask`, `allowed` | Whether the skill may fetch internet sources. |
| `filesystem` | `none`, `local-notes-only`, `workspace`, `explicit-paths` | Where the skill may write. |
| `terminalProfile` | `none`, `read-only`, `build`, `custom` | Terminal lane, never raw arbitrary shell by default. |
| `secrets` | `none`, `server-side-only` | Secrets never enter browser-visible state. |
| `paidCompute` | `forbidden-without-approval`, `ask`, `allowed` | Default is approval-gated. |

## Browser handoff contract

When a skill opens the browser, it should emit a browser action packet, not free text. The action packet spec lives in:

`docs/specs/AETHERDESK_BROWSER_ACTION_PACKET.md`

Minimum browser handoff:

```json
{
  "schema": "aetherdesk.browser.action.v1",
  "skillId": "browser-audit",
  "mode": "audit",
  "query": "Compare this page against public docs and produce a receipt.",
  "networkPolicy": "ask",
  "stopRules": ["no-repeated-polling", "stop-after-first-answer"]
}
```

## Validation checklist

- The manifest can render as a card without extra fields.
- The skill can open one primary app route.
- The skill declares whether it may use network, terminal, filesystem, paid compute, and secrets.
- The browser can convert it into an action packet.
- Training can convert it into positive and negative examples.
- A human can understand what it will do before it runs.

## Release target

For a first public-feeling AetherDesk skill marketplace:

- 12 to 20 manifests checked into the app.
- Browser, AI Desk, Notebook, Files, Terminal, and Training Dashboard all represented.
- At least 4 skill cards are wired to real local actions.
- Every non-wired skill is clearly labeled as draft or guide-only.
- No raw token appears in browser state or localStorage.

