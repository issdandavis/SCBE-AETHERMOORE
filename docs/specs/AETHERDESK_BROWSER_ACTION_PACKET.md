# AetherDesk Browser Action Packet

Date: 2026-06-27
Status: draft v1
Scope: Aether Browser, AI controls, human controls, source receipts, and terminal handoff

## Purpose

Aether Browser should feel like a real product, not a chat box wrapped around a webview. Human controls and AI controls need a shared action language so browser tasks can be reviewed, paused, replayed, and trained.

The browser action packet is that shared language.

## Product model

Aether Browser has four lanes:

| Lane | Human surface | AI surface | Notes |
|---|---|---|---|
| `answer` | Ask box, source cards | Synthesizer | Perplexity-like answer with receipts. |
| `browse` | URL bar, preview, tabs | Page reader | Human drives, AI explains. |
| `audit` | Checklist, source compare | Verifier | Finds gaps, claims, risks, and missing evidence. |
| `agent` | Run controls, pause, receipts | Planner/executor | Bounded automation with explicit stop rules. |

## Packet shape

```json
{
  "schema": "aetherdesk.browser.action.v1",
  "id": "act_20260627_browser_audit_001",
  "createdAt": "2026-06-27T00:00:00-07:00",
  "createdBy": "human",
  "skillId": "browser-audit",
  "mode": "audit",
  "state": "draft",
  "query": "Review this page and tell me what is real, missing, and risky.",
  "target": {
    "url": "https://example.org",
    "label": "example.org",
    "sourceType": "web"
  },
  "humanControls": {
    "canEditQuery": true,
    "canApproveNetwork": true,
    "canPause": true,
    "canOpenTerminal": false
  },
  "aiControls": {
    "planner": "local-first",
    "model": "scbe-coder",
    "mayBrowse": "ask",
    "mayUseTerminal": false,
    "mayWriteFiles": false
  },
  "toolPlan": [
    {
      "tool": "open_url",
      "reason": "Read the target page once.",
      "requiresApproval": false
    },
    {
      "tool": "extract_claims",
      "reason": "Separate claims from evidence.",
      "requiresApproval": false
    }
  ],
  "networkPolicy": {
    "mode": "ask",
    "maxInitialFetches": 1,
    "polling": "off",
    "allowedDomains": [],
    "blockedDomains": []
  },
  "authBoundary": {
    "browserMaySeeSecrets": false,
    "serverSideTokenOnly": true,
    "safeMetadataOnly": true
  },
  "terminalBoundary": {
    "enabled": false,
    "profile": "none",
    "allowedCommands": []
  },
  "outputs": {
    "answerFormat": "markdown",
    "receiptFormat": "json",
    "saveToNotebook": false
  },
  "stopRules": [
    "stop-after-first-answer",
    "no-repeated-polling",
    "stop-before-paid-compute",
    "stop-before-publish",
    "stop-before-delete"
  ]
}
```

## Packet states

| State | Meaning |
|---|---|
| `draft` | Created by a skill card or human input, not runnable yet. |
| `ready` | Required fields are present and safe. |
| `needs_approval` | Waiting for human approval for network, terminal, paid compute, or write action. |
| `running` | A bounded action is executing. |
| `paused` | Human or policy paused the action. |
| `done` | Completed with a receipt. |
| `blocked` | Cannot continue without new info or approval. |
| `failed` | Runtime or environment failure. |

## Allowed tool verbs

Initial local verbs:

| Verb | Risk | Description |
|---|---|---|
| `open_url` | low | Open one URL in the browser preview. |
| `summarize_page` | low | Summarize visible or fetched page content. |
| `extract_claims` | low | List claims and implied evidence needs. |
| `compare_sources` | medium | Compare multiple sources after approval. |
| `audit_page` | medium | Produce risk, source, and missing-evidence report. |
| `call_local_model` | low | Use local model for transformation or explanation. |
| `save_note` | medium | Write a local notebook/product note. |
| `open_terminal_profile` | high | Open allowlisted terminal profile only. |
| `create_task` | medium | Append a product/backlog task. |

Forbidden without explicit approval:

- Raw arbitrary shell.
- Deleting files.
- Publishing packages.
- Paid remote training or evals.
- Background repeated polling.
- Exposing raw OAuth or HF tokens to browser state.

## Receipt shape

```json
{
  "schema": "aetherdesk.browser.receipt.v1",
  "actionId": "act_20260627_browser_audit_001",
  "finishedAt": "2026-06-27T00:00:00-07:00",
  "state": "done",
  "sources": [
    {
      "url": "https://example.org",
      "usedFor": "target page",
      "confidence": "direct"
    }
  ],
  "actions": [
    {
      "verb": "open_url",
      "result": "ok"
    }
  ],
  "filesWritten": [],
  "skipped": [
    {
      "reason": "No external comparison requested.",
      "risk": "low"
    }
  ],
  "stopReason": "stop-after-first-answer"
}
```

## UI requirements

Minimum product UI:

- URL bar with safe hostname fallback for malformed input.
- Mode rail for answer, browse, audit, and agent.
- Human-visible source cards.
- Human-visible run controls: approve, pause, stop, save.
- AI-visible plan preview before actions.
- Receipt drawer after actions.
- "No repeated polling" shown as a boundary when live data is disabled.

## Training implications

Positive examples should teach:

- Choose the smallest lane that satisfies the task.
- Ask before network expansion.
- Keep tokens and secrets server-side.
- Produce receipts.
- Stop cleanly when the user goes to bed or asks for local-light work.

Negative examples should teach:

- Do not loop-poll logs repeatedly.
- Do not train or publish while the user asked not to.
- Do not expose HF_TOKEN or OAuth tokens in browser state.
- Do not claim a build passed if it was not run.
- Do not treat a draft skill card as a verified tool.

## First implementation target

The current static AetherDesk browser can use this spec without backend changes:

- Skill card creates a packet.
- Browser stores the pending packet in local app state.
- Browser renders query, mode, source card, and stop rules.
- No network action runs until the human clicks a control.

