# Packet Schema

## Required

- `packet_id` string
- `session_id` string
- `codename` string
- `created_at` UTC ISO timestamp
- `sender` string
- `recipient` string
- `task_id` string
- `summary` string
- `status` one of: `in_progress`, `blocked`, `done`, `verify`

## Optional

- `next_action` string
- `where` string
- `why` string
- `how` string
- `risk` one of: `low`, `medium`, `high`
- `proof` string array

## Bus and Mirrors

- Packet JSON file: `artifacts/agent_comm/<day>/cross-talk-*.json`
- Lane bus JSONL: `artifacts/agent_comm/github_lanes/cross_talk.jsonl`
- Human mirror: `notes/_inbox.md`
