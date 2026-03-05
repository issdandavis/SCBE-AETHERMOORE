# scbe-ops-control — Unified Multi-Agent Operations Skill

**Date:** 2026-03-04
**Author:** Claude (agent.claude)
**Status:** Building

## Problem

Cross-talk between Claude, Codex, Gemini, and other agents uses 4 separate
surfaces (JSON packets, JSONL lanes, Obsidian markdown, agents/*.md logs).
Packets get dropped, agents miss handoffs, there's no delivery verification.

## Solution

One skill (`scbe-ops-control`) that wraps all coordination into a single
entry point with guaranteed delivery to all surfaces and ACK verification.

## Operations

| Op | Trigger | What it does |
|----|---------|-------------|
| SEND | "send cross-talk", "handoff to codex" | Write to all 4 surfaces atomically |
| ACK | "ack packet", "acknowledge handoff" | Confirm receipt with proof |
| STATUS | "agent status", "what's active" | Scan all surfaces, report unacked |
| VERIFY | "verify handoff", "check delivery" | Confirm packet in all 4 surfaces |
| ROSTER | "who's active", "show agents" | Read squad + session signons |
| HEALTH | "health check", "system status" | Run connector checks |

## 4 Delivery Surfaces

1. `artifacts/agent_comm/{YYYYMMDD}/cross-talk-*.json` — machine-readable
2. `artifacts/agent_comm/github_lanes/cross_talk.jsonl` — lane bus
3. Obsidian `Cross Talk.md` — human-readable, other AIs read this
4. `agents/{agent}.md` — per-agent log

## Packet Schema

```json
{
  "packet_id": "{agent}-{op}-{timestamp}-{hash6}",
  "created_at": "ISO8601",
  "from": "agent.claude",
  "to": "agent.codex",
  "intent": "handoff|ack|status|lane_claim|sync",
  "status": "done|in_progress|pending|blocked",
  "summary": "Human-readable description",
  "artifacts": ["file1", "file2"],
  "next": "What receiving agent should do",
  "ack_required": true,
  "ack_received": null,
  "delivery": {
    "json_packet": true,
    "jsonl_lane": true,
    "obsidian": true,
    "agent_log": true
  }
}
```

## Files

- Skill: `.claude/skills/scbe-ops-control/SKILL.md`
- Script: `scripts/system/ops_control.py` (unified bus)
- Config: `.scbe/ops_control_config.json` (surfaces, timeouts)
