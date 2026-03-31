# Advanced AI Dispatch Spine

Last updated: 2026-03-29

## Purpose

This is the lightweight dispatch layer for SCBE multi-agent work. It exists to move work faster without letting agents collide on files, drift into ambiguous ownership, or disappear into ad hoc chat.

The dispatch spine does not replace:

- `scripts/system/browser_chain_dispatcher.py`
- `src/aetherbrowser/router.py`
- `src/aetherbrowser/trilane_router.py`
- `scripts/system/crosstalk_relay.py`

It sits above them and turns those surfaces into a queueable work system.

## Core model

Every task becomes one packet with:

- `task_id`
- `title`
- `goal`
- `capability`
- `priority`
- `write_scope`
- `dependencies`
- `payload`
- `route`
- `lease_owner`
- `lease_expires_at`

The goal is simple:

1. enqueue bounded work
2. route it to the right lane
3. lease it to exactly one worker
4. release stale work
5. close work with explicit completion or failure

## Why this fits the existing SCBE system

The repo already has most of the hard parts:

- `browser_chain_dispatcher.py` knows how to map browser work onto tentacles
- `OctoArmorRouter` and `TriLaneRouter` already express routing preference and lane choice
- `crosstalk_relay.py` already carries deterministic agent-to-agent packets
- `docs/system/SMALL_AGENT_REFERENCE_CENTER.md` already frames small-agent cards plus a task queue

What was missing was the spine that holds them together.

## Files

- Runtime: `scripts/system/advanced_ai_dispatch.py`
- Registry: `config/system/advanced_ai_dispatch_capabilities.json`
- Queue database: `artifacts/dispatch_spine/dispatch.db`

## State model

Supported task states:

- `queued`
- `running`
- `completed`
- `failed`

The queue is lease-driven. A worker claims a task for a bounded lease window. If the worker disappears, the lease can be released and the task goes back to `queued`.

## Routing

Capabilities are defined in the registry. Today the core lanes are:

- `browser.navigate`
- `browser.research`
- `code.patch`
- `docs.publish`
- `system.admin`
- `relay.sync`

Browser capabilities are automatically enriched through the existing browser dispatcher so a packet can carry a real browser route instead of just a vague label.

## CLI

Initialize the queue:

```powershell
python scripts/system/advanced_ai_dispatch.py init
```

Enqueue work:

```powershell
python scripts/system/advanced_ai_dispatch.py enqueue `
  --title "Fix research page mobile nav" `
  --goal "Repair mobile navigation and accessibility on the research hub." `
  --capability docs.publish `
  --write-scope docs/research/index.html,docs/sitemap.xml `
  --requested-by agent.codex
```

Enqueue browser work with route enrichment:

```powershell
python scripts/system/advanced_ai_dispatch.py enqueue `
  --title "Inspect GitHub PR surface" `
  --goal "Open the PR, capture status, and summarize blockers." `
  --capability browser.research `
  --payload "{\"domain\":\"github.com\",\"task_type\":\"research\",\"repo\":\"issdandavis/SCBE-AETHERMOORE\"}" `
  --requested-by agent.browser
```

Claim work:

```powershell
python scripts/system/advanced_ai_dispatch.py claim `
  --worker-id agent.docs `
  --capability docs.publish
```

Complete work:

```powershell
python scripts/system/advanced_ai_dispatch.py complete `
  --task-id task-20260329-120000-ab12cd `
  --worker-id agent.docs `
  --summary "Research page mobile nav repaired and metadata updated."
```

Release stale leases:

```powershell
python scripts/system/advanced_ai_dispatch.py release-stale --max-age-minutes 45
```

Status view:

```powershell
python scripts/system/advanced_ai_dispatch.py status
```

## Design rules

1. Route by capability, not by brand name of the model.
2. Keep `write_scope` explicit.
3. Use one lease owner at a time.
4. Requeue stale work instead of silently losing it.
5. Use crosstalk as the evidence lane, not as the queue itself.

## Next extensions

- add packet templates for common lanes
- emit optional crosstalk packets on state transitions
- add registry-level path constraints
- add review-gate packets before merge or publish
- bridge queue events into the small-agent reference center
