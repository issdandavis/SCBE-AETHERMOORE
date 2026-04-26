# DIBBS And SCBE Communications Infrastructure

Date: 2026-04-26

## Purpose

Capture the lawful communications plan for DIBBS follow-up, contract operations, and future SCBE field-agent coordination.

This is not a plan to transmit on cellular bands directly. The near-term goal is a carrier-agnostic communications bus that can route reminders and operational messages through existing lawful channels.

## Current Practical Channel Stack

1. Telegram
   - Existing useful path for fast operator alerts and preview messages.
   - Repo evidence: `scripts/outreach/cold_outreach_pipeline.py` has Telegram preview support.
   - Best use now: personal operations alerts, draft previews, status pings, and agent-bus notifications.
   - Verified 2026-04-26 through `scripts/system/telegram_alert_ops.py`: `getMe` succeeded, private owner-chat `sendMessage` succeeded, webhook info returned no error and zero pending updates.

2. Proton Bridge
   - Existing working local email path.
   - Best use now: auditable federal/contact reminders, sent-message records, contract follow-up, and dry-run-first outreach.

3. Gmail
   - Useful secondary mailbox and CC anchor.
   - Best use now: redundancy, receipt confirmation, and search-friendly recordkeeping.

4. Twilio SMS
   - Optional paid bridge only if credentials and budget are available.
   - Best use later: urgent SMS fallback for specific trusted contacts.
   - Do not make Twilio mandatory for core workflows.

5. Google Voice
   - Do not depend on it for automation. It has no stable supported automation API for this use case.

## Cellular-Like Architecture

Build the system as a message router, not as a radio carrier first.

```text
event or task
  -> policy gate
  -> contact / channel resolver
  -> route selection
  -> send through Telegram, Proton, Gmail, local app, or optional SMS
  -> receipt ledger
  -> follow-up scheduler
```

This gives the operational value of a cellular service without requiring spectrum, towers, carrier agreements, or paid infrastructure.

## Long-Term Hardware Lane

If SCBE later needs private-device connectivity, the lawful upgrade path is private LTE/5G through CBRS in the United States.

CBRS is the relevant private-network lane:

- shared 3.5 GHz band;
- requires certified equipment;
- requires Spectrum Access System coordination;
- useful for a local site, lab, warehouse, farm, test range, or private agent-device network.

Do not transmit on cellular bands directly with uncertified equipment or unauthorized spectrum access.

## DIBBS Address Verification Use Case

Current issue:

- DIBBS / DLA physical address verification postcard was requested 2026-04-20.
- First postcard was sent 2026-04-21.
- Expected check date is Monday 2026-04-27.

Operational rule:

- Use Telegram or Proton reminders to coordinate the mailbox check.
- Do not store family phone numbers in tracked repo files.
- Do not paste the verification code into public docs, public repos, or public chats.
- Record only status states in tracked docs: `not arrived`, `arrived`, `code entered`.

Local helper:

```powershell
python scripts/system/dibbs_address_verification_reminder.py --write-email-draft
python scripts/system/proton_mail_ops.py send-draft --draft-file artifacts/proton_mail/dibbs/dibbs_address_verification_reminder_20260427.md
```

The send command is dry-run unless `--execute` is added.

Telegram helper:

```powershell
python scripts/system/dibbs_address_verification_reminder.py --write-telegram-message
python scripts/system/telegram_alert_ops.py --load-dotenv send --message-file artifacts/telegram_alerts/dibbs_address_verification_reminder_20260427.txt --write-receipt
```

Telegram receipts are local generated artifacts under `artifacts/telegram_alerts/` and should not be committed.

## Build Branches

1. Telegram alert adapter
   - Wrap existing Telegram preview code into a reusable `send_alert` helper.
   - Inputs: event type, priority, message body, optional task link.
   - Output: sent / failed receipt.

2. Channel resolver
   - Pick Telegram, Proton, Gmail, local notification, or SMS based on urgency, cost, and recipient.

3. Receipt ledger
   - Store non-secret metadata only: channel, timestamp, recipient label, delivery status, related task.

4. Follow-up scheduler
   - Generate next-action reminders without storing private contact details in tracked files.

5. Future CBRS/private LTE appendix
   - Keep as an infrastructure research lane, not a current dependency.

## Cost Discipline

Use free or already-paid channels first:

- Telegram for instant messages;
- Proton/Gmail for auditable records;
- local app notifications where possible;
- Twilio only for high-value SMS fallback;
- CBRS/private LTE only when there is a funded hardware reason.
