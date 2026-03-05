---
name: scbe-sitrep
description: Generate a deduplicated situation report from cross-talk packets, git log, and session signons. Use when starting a session, asking "what happened", "what's stuck", "catch me up", "sitrep", "status report", or any time you need a quick briefing on multi-agent activity.
---

# SCBE Sitrep — Session Situation Report

You are generating a concise, actionable briefing from the multi-agent cross-talk bus.
The problem this solves: the inbox has hundreds of packets with massive duplication.
This skill deduplicates by task_slug, classifies by priority, and delivers a tight report.

## When to Use This Skill

- User says "sitrep", "status", "what happened", "catch me up", "briefing"
- At session start to understand what changed since last session
- Before planning new work (to avoid duplicating in-progress lanes)
- After a long autonomous run to see results

## Quick Command

```bash
python scripts/system/sitrep.py              # Last 24 hours, text
python scripts/system/sitrep.py --hours 8    # Last 8 hours
python scripts/system/sitrep.py --json       # Machine-readable
python scripts/system/sitrep.py --since 2026-03-04  # Since specific date
python scripts/system/sitrep.py --output artifacts/sitrep_latest.json --json
```

## What It Does

1. **Scans** all JSON packets in `artifacts/agent_comm/{date}/` folders
2. **Parses** `notes/_inbox.md` cross-talk lines
3. **Deduplicates** by task_slug — keeps only the latest packet per unique task
4. **Classifies** into priority buckets:
   - **BLOCKED** — tasks that hit errors or are waiting on something
   - **NEEDS ACK** — packets with `ack_required: true` that haven't been acknowledged
   - **IN PROGRESS** — active work lanes
   - **DONE** — completed work
5. **Pulls** recent git commits for code-level context
6. **Checks** active session signons

## How to Present the Report

After running the script, present the results to the user in this order:

### 1. Headlines
- Total packets seen vs unique tasks (shows dedup ratio)
- Count per bucket: X blocked, Y needs ack, Z in progress, W done

### 2. Action Items (BLOCKED + NEEDS ACK)
- These need immediate attention
- For BLOCKED: identify the blocker and suggest a fix
- For NEEDS ACK: list what needs to be acknowledged

### 3. Active Lanes (IN PROGRESS)
- What's currently being worked on and by whom
- Flag any that look stale (>2 hours with no update)

### 4. Completed Work (DONE)
- Brief summary of what shipped
- Highlight anything that affects current planning

### 5. Git Activity
- Recent commits grouped by area (feature, fix, etc.)

## Integration with Other Skills

- After sitrep, use `scbe-ops-control` ACK command to clear pending acks
- Use `scbe-flock-shepherd` if blocked items need agent reassignment
- Use `scbe-training-pipeline` if training lanes need attention
- Use `scbe-shopify-store-ops` if Shopify lanes are in progress

## Artifact Output

When `--output` is specified, the report is saved for cross-session reference.
Recommended: `artifacts/sitrep_latest.json` for machine use,
or `artifacts/sitrep_{date}.txt` for human review.
