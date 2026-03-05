---
name: scbe-crosstalk-workflow
description: "Use when Claude and Codex work in parallel and need to send, receive, or verify deterministic handoff packets across JSON, JSONL bus, and notes mirror."
---

# SCBE Cross-Talk Workflow

Use this skill when two AI agents (Claude and Codex) are working in the same repo and need deterministic, auditable communication packets.

## When To Use

- Starting a new coordinated session with another agent
- Posting task updates, blockers, or handoffs
- Acknowledging received packets (ACK)
- Verifying packet delivery across all 3 surfaces
- At session start: check for unacked packets addressed to you

## Surfaces (Write to ALL 3)

1. **JSON packet**: `artifacts/agent_comm/{YYYYMMDD}/cross-talk-{agent}-{task}-{timestamp}.json`
2. **JSONL lane bus**: `artifacts/agent_comm/github_lanes/cross_talk.jsonl` (append)
3. **Notes mirror**: `notes/_inbox.md` (append)

## Packet Format

```json
{
  "packet_id": "cross-talk-agent.claude-taskslug-20260304T120000Z",
  "session_id": "guid",
  "codename": "steady-falcon",
  "created_at": "2026-03-04T12:00:00.000Z",
  "sender": "agent.claude",
  "recipient": "agent.codex",
  "task_id": "TASK-SLUG",
  "summary": "One-sentence description",
  "status": "in_progress|blocked|done|verify",
  "next_action": "What recipient should do",
  "where": "file or location",
  "why": "reason",
  "how": "approach",
  "risk": "low|medium|high",
  "proof": ["path/to/artifact"]
}
```

## How to SEND (Claude side)

Write the packet JSON to all 3 surfaces using Write + Edit tools:

```python
# Generate packet
import json
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
day = now.strftime("%Y%m%d")
stamp = now.strftime("%Y%m%dT%H%M%SZ")
packet = {
    "packet_id": f"cross-talk-agent.claude-{task_slug}-{stamp}",
    "session_id": session_id,
    "codename": codename,
    "created_at": now.isoformat(),
    "sender": "agent.claude",
    "recipient": "agent.codex",
    "task_id": task_id,
    "summary": summary,
    "status": status,
    "next_action": next_action,
}
```

1. Write JSON file to `artifacts/agent_comm/{day}/{packet_id}.json`
2. Append compressed JSON line to `artifacts/agent_comm/github_lanes/cross_talk.jsonl`
3. Append line to `notes/_inbox.md`: `- [{timestamp}] agent.claude -> agent.codex | {task_id} | {status} | {summary}`

## How to SEND (Using Codex emitter script)

```powershell
& "C:/Users/issda/.codex/skills/scbe-claude-crosstalk-workflow/scripts/emit_crosstalk_packet.ps1" `
  -RepoRoot "C:/Users/issda/SCBE-AETHERMOORE" `
  -NewSession `
  -Sender "agent.claude" `
  -Recipient "agent.codex" `
  -TaskId "YOUR-TASK-ID" `
  -Summary "What you did or need" `
  -Status "in_progress" `
  -NextAction "What codex should do"
```

## How to ACK

Send a packet with `task_id` = original task_id, `status` = "done", `summary` = "ACK {original_packet_id}: confirmed".

## How to VERIFY

```powershell
python "C:/Users/issda/.codex/skills/scbe-claude-crosstalk-workflow/scripts/crosstalk_skill_audit.py" `
  --repo-root "C:/Users/issda/SCBE-AETHERMOORE"
```

Add `--repair` to fix missing entries on any surface.

## Session State

Session state persists at `artifacts/agent_comm/session_state/{agent_slug}.json`:
```json
{"sender": "agent.claude", "session_id": "guid", "codename": "steady-falcon", "updated_at": "ISO"}
```

## Guardrails

- Never include secrets or tokens in any packet field
- Append-only flow — never edit prior packets
- Use `status=blocked` instead of silent failure
- Keep `TaskId` stable for a task lifecycle
- Check `notes/_inbox.md` at session start for pending work
