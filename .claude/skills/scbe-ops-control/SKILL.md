---
name: scbe-ops-control
description: Unified multi-agent operations — send/ack/verify cross-talk across all 4 surfaces (JSON packets, JSONL lanes, Obsidian, agent logs), check agent roster, run health checks. Use when coordinating with Codex/Gemini/other agents, sending handoffs, checking what's active, or verifying delivery.
---

# SCBE Ops Control — Multi-Agent Command Center

You are the operations controller for a multi-agent AI system. Your job is to ensure
reliable communication between Claude, Codex, Gemini, and other agents through
guaranteed delivery to all coordination surfaces.

## When to Use This Skill

- User says "send cross-talk", "handoff to codex", "post update", "sync agents"
- User says "what's active", "agent status", "who's working on what"
- User says "verify handoff", "check delivery", "did codex get it"
- User says "health check", "system status"
- User says "ack", "acknowledge", "confirm receipt"
- Before/after any multi-agent coordination task
- At session start (check for unacked packets addressed to you)

## Operations

### SEND — Post cross-talk to all surfaces

Write the same packet to ALL 4 surfaces. If any surface fails, report it.

**Surfaces:**
1. `SCBE-AETHERMOORE/artifacts/agent_comm/{YYYYMMDD}/cross-talk-{agent}-{task}-{timestamp}.json`
2. `SCBE-AETHERMOORE/artifacts/agent_comm/github_lanes/cross_talk.jsonl` (append one line)
3. `C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\AI Workspace\Cross Talk.md` (append markdown block)
4. `SCBE-AETHERMOORE/agents/{from_agent}.md` (append log entry)

**Packet format (JSON):**
```json
{
  "packet_id": "{from}-{intent}-{YYYYMMDDTHHMMSSZ}-{6char_hash}",
  "created_at": "2026-03-04T02:10:00Z",
  "from": "agent.claude",
  "to": "agent.codex",
  "intent": "handoff|ack|sync|lane_claim|status_update|smoke|asset_drop",
  "status": "done|in_progress|pending|blocked",
  "summary": "One-sentence description of work done or requested",
  "artifacts": ["relative/path/to/file1", "relative/path/to/file2"],
  "next": "What the receiving agent should do next",
  "ack_required": true
}
```

**Obsidian format (append to Cross Talk.md):**
```markdown
## {created_at} | {Agent} | {task_slug}

- status: {status}
- summary: {summary}
- artifacts:
  - {artifact1}
  - {artifact2}
- next: {next}
```

**JSONL format (append one line to cross_talk.jsonl):**
Same as JSON packet but on a single line.

**Agent log format (append to agents/{agent}.md):**
```
- {created_at} {from} -> {to} | {intent} | {status} | {task_slug} | {summary} ({first_artifact_path})
```

### ACK — Acknowledge a received packet

1. Read the packet being acknowledged
2. Write an ACK packet to all 4 surfaces with:
   - `intent: "ack"`
   - `summary: "ACK {original_packet_id}: {brief confirmation}"`
   - `artifacts: [{proof files showing work was received/acted on}]`

### STATUS — Show active lanes and pending handoffs

1. Scan `artifacts/agent_comm/` for recent packets (last 24h)
2. Read `artifacts/agent_comm/github_lanes/cross_talk.jsonl` (last 10 entries)
3. Read Obsidian `Cross Talk.md` (last 5 entries)
4. Read `.scbe/agent_squad.json` for registered agents
5. Read `artifacts/agent_comm/session_signons.jsonl` for active sessions
6. Report:
   - Active agents (signed on in last 4 hours)
   - Pending handoffs (status != done, no ACK)
   - Stale packets (>30 min, ack_required but no ack)
   - Active lanes (in_progress tasks)

### VERIFY — Check delivery of a specific packet

1. Given a packet_id, check all 4 surfaces for its presence
2. Report which surfaces have it and which are missing
3. If any missing, offer to re-deliver to the missing surfaces

### ROSTER — Show agent registry

1. Read `.scbe/agent_squad.json`
2. Read `artifacts/agent_comm/session_signons.jsonl` (last 10)
3. Show table: agent, provider, model, last_seen, current_task

### HEALTH — System health check

1. Run: `python scripts/connector_health_check.py` (if available)
2. Check GCP VM: `curl -s https://34.134.99.90:8001/health`
3. Check n8n bridge: `curl -s http://127.0.0.1:8001/health`
4. Check AetherNet: `curl -s http://127.0.0.1:8300/health`
5. Report pass/fail for each service

## Session Start Protocol

At the beginning of every session where this skill is invoked:

1. **Check inbox**: Read last 5 entries from `Cross Talk.md` and last 5 JSON packets in `artifacts/agent_comm/`
2. **Find unacked**: Look for packets addressed to `agent.claude` with `ack_required: true` and no corresponding ACK
3. **Report**: Tell the user what's pending
4. **Sign on**: Write a session signon to `artifacts/agent_comm/session_signons.jsonl`

## Error Handling

- If Obsidian vault path doesn't exist (OneDrive not synced): skip that surface, warn user
- If artifacts/agent_comm/ dir doesn't exist: create it
- If agents/{agent}.md doesn't exist: create it with header
- Always report which surfaces succeeded and which failed
- Never silently drop a delivery failure

## Key Paths

| Surface | Path |
|---------|------|
| JSON packets | `SCBE-AETHERMOORE/artifacts/agent_comm/{YYYYMMDD}/` |
| JSONL lane | `SCBE-AETHERMOORE/artifacts/agent_comm/github_lanes/cross_talk.jsonl` |
| Obsidian | `C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\AI Workspace\Cross Talk.md` |
| Agent logs | `SCBE-AETHERMOORE/agents/{agent}.md` |
| Squad registry | `SCBE-AETHERMOORE/.scbe/agent_squad.json` |
| Session signons | `SCBE-AETHERMOORE/artifacts/agent_comm/session_signons.jsonl` |
| Health check | `SCBE-AETHERMOORE/scripts/connector_health_check.py` |

## Integration with Existing Skills

This skill is the **coordination layer**. Other skills handle execution:
- `scbe-flock-shepherd` — spawn/manage agents (invoke when ROSTER shows need)
- `scbe-fleet-deploy` — deploy artifacts (invoke after SEND confirms handoff)
- `scbe-browser-swarm-ops` — browser tasks (invoke for browser lane work)
- `scbe-training-pipeline` — training data (invoke for training lane work)
- `scbe-governance-gate` — governance scan (invoke for any governance check)
