# Centaur Message Routing Bus Governance

Date: 2026-04-26

## Purpose

Define the governance boundary for an SCBE message-routing bus that connects:

- human to human;
- human to AI;
- AI to human;
- AI to AI;
- human with AI to another human or AI;
- AI with human oversight to another human or AI.

The bus is allowed to move messages. It is not allowed to become an ungoverned remote-control shell.

## Core Principle

Governance is the product boundary.

If SCBE cannot keep its agents constrained, auditable, recoverable, and aligned with the sender's authority, then SCBE is not ready to operate the routing bus.

The horse metaphor is useful operationally: AI workers can carry force, speed, and pattern recognition, but the bus must provide the reins, tack, arena gates, and handler logs.

## Public Interface, Proprietary Depth

The public surface should expose enough to prove the bus is useful and safe:

- message envelope;
- governance gates;
- route states;
- triplet ledger format;
- two-tokenizer verification contract;
- receipts and verification commands.

The proprietary surface should remain behind private adapters and private training assets:

- which tokenizer pairs are selected for which message classes;
- scoring weights for tokenizer agreement;
- model-routing policy;
- risk thresholds;
- trained adapters;
- customer-specific compliance gates;
- private channel connectors.

This lets the same system serve multiple uses without giving away the full method. Public users can verify that messages are governed and tamper-evident. Private deployments get the stronger tokenizer pairs, routing intelligence, and domain-specific gates.

## Bus Invariant

Every inbound message becomes one of these objects:

1. `status_ping`
2. `help_request`
3. `task_request`
4. `draft_message`
5. `send_request`
6. `acknowledgement`
7. `blocked_or_quarantined`

No inbound message becomes direct shell execution.

## Required Envelope

Every routed message must carry:

- sender identity;
- recipient identity;
- sender class: `human`, `ai`, or `human_with_ai`;
- recipient class: `human`, `ai`, `agent_group`, or `external_service`;
- intent;
- risk class;
- message body;
- provenance;
- requested channel;
- required tests or review gates;
- receipt target;
- acknowledgement policy.

## Governance Gates

1. Identity gate
   - Is the sender known?
   - Is the channel authorized for this sender?

2. Intent gate
   - Is this a status ping, task request, draft, send request, or unknown instruction?

3. Authority gate
   - Can this sender ask this recipient to do this?
   - Can this channel carry this message class?

4. Risk gate
   - Low: queue packet and acknowledge.
   - Medium: queue packet and request review.
   - High: quarantine and require explicit human approval.

5. Content gate
   - Secrets, credentials, private phone numbers, verification codes, and controlled files must not be forwarded automatically.

6. Execution gate
   - The bus never executes shell commands from messages.
   - The bus emits packets for Codex, Claude, Clawbot, or another worker to inspect.
   - Workers may act only through their normal governed tool boundaries.

7. Receipt gate
   - Every delivery attempt writes a receipt.
   - Receipts contain metadata, not raw secrets.

8. Triplet verification gate
   - Every routed message should be commit-able to a local triplet ledger.
   - Triplet fields are `previous_hash`, `current_hash`, and `ack_hash`.
   - Each chain record is composed from two tokenizer views over the same message envelope.
   - `previous_hash` links the record to prior bus state.
   - `current_hash` commits the envelope and route metadata.
   - `ack_hash` commits acknowledgement or next-hop receipt data when available.
   - `tokenizer_a` commits a byte/hex-oriented view.
   - `tokenizer_b` commits a second structural view.
   - The two-tokenizer pair gets its own `tokenizer_pair_hash`; verification fails if either view drifts.
   - This is blockchain-style tamper evidence, not a paid public blockchain dependency.

## Current Implemented Slice

Telegram inbound bridge:

- `scripts/system/telegram_alert_ops.py`
- Owner chat is checked against `TELEGRAM_OWNER_ID` or `TELEGRAM_CHAT_ID`.
- `/ping` returns a bridge health acknowledgement.
- `/task`, `/act`, `/codex`, or plain text from the owner chat becomes a SCBE task packet.
- The bridge writes packets through `scripts/system/ops_control.py`.
- Telegram replies contain packet identifiers, not execution output.
- Telegram task packets commit to `artifacts/message_bus/telegram_triplet_ledger.jsonl` through `scripts/system/message_triplet_ledger.py`.

Regression tests:

- `tests/test_telegram_alert_ops.py`
- Verifies token redaction.
- Verifies owner-chat gate.
- Verifies shell-like text is still only classified as a task request.
- Verifies triplet ledger append and tamper detection.
- Verifies DIBBS reminder output contains no phone number.

## Near-Term Build Plan

1. Generalize the Telegram bridge into `message_routing_bus.py`.
2. Add channel adapters:
   - Telegram;
   - Proton Bridge;
   - Gmail;
   - local packet queue;
   - future n8n/Zapier webhook.
3. Add envelope schema for message routing.
4. Add approval states:
   - `drafted`;
   - `queued`;
   - `needs_review`;
   - `approved`;
   - `sent`;
   - `blocked`;
   - `acknowledged`.
5. Add route tests:
   - human to AI;
   - AI to human;
   - AI to AI;
   - human with AI to AI;
   - AI with human approval to external service.

## Non-Goals

- No fake cellular carrier.
- No direct remote shell from Telegram.
- No automatic forwarding of verification codes.
- No raw `.env` forwarding.
- No unreviewed government or contract submissions.
