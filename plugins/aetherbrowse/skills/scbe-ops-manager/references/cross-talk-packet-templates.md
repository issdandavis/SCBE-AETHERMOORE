# Cross-Talk Packet Templates

Copy-paste templates for every cross-talk intent type. Replace placeholders in `{braces}`.

## ACK Packet

Acknowledge receipt of another agent's work:

```json
{
  "packet_id": "cross-talk-agent-claude-{task-slug}-{ISO8601}Z",
  "created_at": "{ISO8601}",
  "session_id": "{session_id}",
  "codename": "{codename}",
  "sender": "agent.claude",
  "recipient": "agent.{target}",
  "intent": "ack",
  "status": "in_progress",
  "repo": "SCBE-AETHERMOORE",
  "branch": "{branch}",
  "task_id": "{UPPER-KEBAB-TASK}",
  "summary": "ACK on {what was received}. {What will be done next}.",
  "proof": ["{file_path_or_commit}"],
  "next_action": "{concrete next step}",
  "risk": "low",
  "gates": {"governance_packet": true, "tests_requested": []}
}
```

## Handoff Packet

Pass work to another agent with context:

```json
{
  "packet_id": "cross-talk-agent-claude-{task-slug}-{ISO8601}Z",
  "created_at": "{ISO8601}",
  "session_id": "{session_id}",
  "codename": "{codename}",
  "sender": "agent.claude",
  "recipient": "agent.{target}",
  "intent": "handoff",
  "status": "done",
  "repo": "SCBE-AETHERMOORE",
  "branch": "{branch}",
  "task_id": "{UPPER-KEBAB-TASK}",
  "summary": "{What was completed and what needs to happen next}.",
  "proof": ["{file1}", "{file2}"],
  "next_action": "{What the recipient should do}",
  "risk": "low",
  "where": "{environment}",
  "why": "{business reason}",
  "how": "{technical approach}",
  "gates": {"governance_packet": true, "tests_requested": []}
}
```

## Ship Packet

Announce a committed/deployed deliverable:

```json
{
  "packet_id": "cross-talk-agent-claude-{task-slug}-{ISO8601}Z",
  "created_at": "{ISO8601}",
  "sender": "agent.claude",
  "recipient": "agent.{target}",
  "intent": "ship",
  "status": "done",
  "repo": "SCBE-AETHERMOORE",
  "branch": "{branch}",
  "task_id": "{UPPER-KEBAB-TASK}",
  "summary": "Shipped {what}: {details}.",
  "proof": ["commit {hash}", "{deploy_url}"],
  "next_action": "{What to test or use}",
  "risk": "low",
  "gates": {"governance_packet": true, "tests_requested": []}
}
```

## Sync Packet

Status update without transferring ownership:

```json
{
  "packet_id": "cross-talk-agent-claude-{task-slug}-{ISO8601}Z",
  "created_at": "{ISO8601}",
  "sender": "agent.claude",
  "recipient": "agent.{target}",
  "intent": "sync",
  "status": "in_progress",
  "repo": "SCBE-AETHERMOORE",
  "branch": "{branch}",
  "task_id": "{UPPER-KEBAB-TASK}",
  "summary": "{Current status and progress}.",
  "proof": ["{evidence}"],
  "next_action": "{What happens next from this agent}",
  "risk": "low",
  "gates": {"governance_packet": true, "tests_requested": []}
}
```

## Lane Assignment Packet

Assign a monetization or work lane to an agent:

```json
{
  "packet_id": "cross-talk-agent-claude-{task-slug}-{ISO8601}Z",
  "created_at": "{ISO8601}",
  "session_id": "{session_id}",
  "codename": "{codename}",
  "sender": "agent.claude",
  "recipient": "agent.{target}",
  "intent": "lane_assignment",
  "status": "in_progress",
  "repo": "SCBE-AETHERMOORE",
  "branch": "{branch}",
  "task_id": "{LANE-TASK-ID}",
  "summary": "Own {lane name}: {lane description}.",
  "proof": ["{related files}"],
  "next_action": "{Deliverable expected and how to emit done packet}",
  "risk": "low",
  "where": "{execution environment}",
  "why": "{business justification}",
  "how": "{approach}",
  "gates": {"governance_packet": true, "tests_requested": []}
}
```

## Session Sign-On Entry

Append to `artifacts/agent_comm/session_signons.jsonl`:

```json
{"session_id": "sess-{ISO8601}-{hex6}", "codename": "{Name}", "agent": "agent.claude", "started_at": "{ISO8601}", "status": "active", "goals": ["{goal1}", "{goal2}"]}
```

When verified: re-append with `"status": "verified"`.

## Obsidian Entry Format

Append to `Cross Talk.md`:

```markdown
## {ISO8601} | Claude | {TASK-ID}

**Status**: {status}
**Intent**: {intent}
**Summary**: {summary}
**Proof**: {comma-separated list}
**Next**: {next_action}
```

## Packet ID Convention

Format: `cross-talk-agent-{sender_short}-{task-slug}-{timestamp}Z`

- `sender_short`: `claude`, `codex`, `gemini`, `grok`
- `task-slug`: lowercase kebab from task_id
- `timestamp`: `YYYYMMDDTHHMMSS` or with milliseconds `YYYYMMDDTHHMMSSsssZ`

## File Naming Convention

Dated packets go to: `artifacts/agent_comm/{YYYYMMDD}/{packet_id}.json`
JSONL bus line goes to: `artifacts/agent_comm/github_lanes/cross_talk.jsonl`
