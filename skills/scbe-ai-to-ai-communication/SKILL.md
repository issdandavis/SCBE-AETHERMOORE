name: scbe-ai-to-ai-communication
description: Standardized packet-based coordination protocol for autonomous AI-to-AI handoff, status sharing, and evidence logging across Codex/Claude/agent workflows.

## When to use
- Cross-agent handoffs and task ownership transfers.
- Multi-agent status and blocker synchronization.
- Evidence-backed progress reports before touching shared code paths.

## Protocol (minimal)
Write a small packet per handoff with:
- `task_id` (B1-HB / B2-SHOP / B3-DYN / B4-P6)
- `sender`, `recipient`
- `status` (`in_progress`, `blocked`, `done`)
- `summary`
- `proof` list of command outputs / file paths
- `next_action`
- `risk` (`low`, `medium`, `high`)

## Canonical Packet Fields
Required keys:
- `packet_id`, `created_at`, `sender`, `recipient`, `intent`, `status`, `repo`, `branch`
- `task_id`, `summary`, `proof`, `next_action`, `risk`, `gates`

## Run a packet
```bash
python skills/scbe-ai-to-ai-communication/scripts/emit_ai_comm_packet.py \
  --sender codex --recipient claude \
  --intent handoff --status done \
  --task-id B3-DYN \
  --summary "handoff summary text" \
  --proof "path/to/artifact.json" \
  --next-action "next step"
```

## Storage
- Default packet directory: `~/OneDrive/Dropbox/SCBE-AI-Comm/packets`
- Keep packet payload JSON and update Obsidian notes (`notes/_inbox.md`, `_context.md`, `open_tasks_...`) for continuity.

## Safety
- Never include raw secrets, tokens, or `.env` contents.
- Include file-level proof references instead of copying sensitive data.
