# Telegram + OpenClaw-Style 24x7 Execution Plan

Date: 2026-02-27

## Goal
Match the 24x7 user experience pattern seen in OpenClaw while keeping SCBE governance controls and your existing HYDRA/n8n bridge architecture.

## What OpenClaw Is Doing (Pattern To Copy)
OpenClaw's 24x7 pattern is not one single feature. It is a stack:
1. A persistent gateway process that owns chat channels.
2. Multi-channel adapters (Telegram, WhatsApp, Discord, Slack, etc.) with deterministic routing back to the same channel.
3. Built-in operator diagnostics (`status`, `doctor`, `gateway inspect`, logs) for fast recovery.
4. Access controls at channel edge (pairing, allowlist, group policies).

Telegram-specific behavior documented by OpenClaw:
- Production-ready Bot API integration.
- Long polling by default; webhook mode optional.
- Pairing/allowlist/group policies and mention controls.
- Thread-aware session routing and per-chat/per-thread sequencing.

## What n8n Adds For True 24x7
n8n queue mode provides scale and resilience:
1. Main instance receives webhooks/triggers.
2. Redis brokers execution IDs.
3. Worker pool executes jobs and writes status/results.
4. Optional webhook processors scale inbound webhook traffic.
5. Worker health endpoints (`/healthz`, `/healthz/readiness`) can be monitored.

Important Telegram reliability notes in n8n docs:
- Telegram webhooks must use HTTPS.
- Telegram app allows only one webhook URL at a time (test vs prod can collide).
- Reverse proxy websocket configuration can cause trigger "stuck listening" symptoms.

## Existing SCBE Assets You Already Have
- Bridge API: `workflows/n8n/scbe_n8n_bridge.py`
- n8n local bootstrap: `workflows/n8n/start_n8n_local.ps1`
- Published workflow set under `workflows/n8n/`
- 24x7 watchdog scripts under `scripts/system/`
- Ops runbook: `docs/ops/AGENT_24X7_OPERATIONS.md`

## New 24x7 Hardening Added In This Session
`scripts/system/watchdog_agent_stack.ps1` now supports Telegram incident alerts:
- Reads `SCBE_TELEGRAM_BOT_TOKEN` and `SCBE_TELEGRAM_CHAT_ID` from environment.
- Sends alert when stack becomes unhealthy.
- Sends alert on recovery success.
- Sends alert on recovery failure.

This gives you OpenClaw-like operator visibility even when unattended.

## Practical Workflow Patterns To Add Next
Use these as patterns (not blind copy-paste) and route all actions through SCBE governance:

1. Telegram command router + memory
- Trigger: Telegram message.
- Parse command and intent.
- Route to `v1/agent/task` (bridge).
- Persist task/result summary to Notion and HF dataset queue.
- Respond to Telegram with result or job ID.

2. Telegram incident/ops bot
- Trigger: schedule every 3-5 minutes.
- Check bridge/browser/n8n health endpoints.
- If degraded, call watchdog and post Telegram alert.
- On repeated failures, open GitHub issue automatically.

3. Telegram research bot with browser lane
- Trigger: `/research <query>` in Telegram.
- Queue browser research task through bridge.
- Save evidence JSON + governance decision record.
- Reply with summary plus artifact path.

4. Telegram to Airtable/Hugging Face funnel
- Trigger: approved classified message payload from Telegram.
- Normalize into row schema.
- Upsert Airtable record.
- Append training/event record to HF dataset staging.
- Return transaction ID to Telegram.

## Suggested Architecture (SCBE Version)
1. Edge: Telegram Trigger node(s) in n8n.
2. Guard: signature/API-key check + command allowlist before tool execution.
3. Orchestration: n8n queue mode (Redis + workers).
4. Execution: SCBE bridge + browser service + HYDRA workers.
5. State: Notion (human ops), Airtable (structured ops), HF dataset (training/events).
6. Recovery: watchdog + Telegram incident alerts.
7. Audit: keep `summary.json`, `audit.json`, `decision_record.json` artifacts enabled.

## Rollout Sequence (Fastest Path)
1. Keep your current local stack as-is and verify health.
2. Enable Telegram alert env vars and test one forced restart event.
3. Move n8n to queue mode with Redis and at least one worker.
4. Separate production Telegram bot from test bot to avoid webhook collisions.
5. Add one Telegram command workflow (`/status`, `/research`, `/task`) first.
6. Add Notion + Airtable + HF writes only after command path is stable.

## References
- OpenClaw channels overview: https://docs.openclaw.ai/channels/index
- OpenClaw Telegram channel docs: https://docs.openclaw.ai/channels/telegram
- OpenClaw health checks: https://docs.openclaw.ai/gateway-and-ops/health-checks
- OpenClaw diagnose system: https://docs.openclaw.ai/gateway-and-ops/diagnose-system
- OpenClaw gateway and ops: https://docs.openclaw.ai/gateway-and-ops/index
- n8n queue mode: https://docs.n8n.io/hosting/scaling/queue-mode/
- n8n Telegram Trigger common issues: https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.telegramtrigger/common-issues/
- n8n Telegram templates list: https://n8n.io/workflows/?integrations=telegram

