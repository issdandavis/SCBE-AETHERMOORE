# SCBE Black Box

Status: proof-of-value MVP

## Product

SCBE Black Box is a self-serve workstation failure explainer.

Promise:

> Run one command. Get a plain-English answer for what is likely to break your PC, AI job, or local automation next.

This is not sold as "governance" or "receipts." Those are internal proof layers.
The buyer-facing pain is simple: "my machine or workflow died, tell me why."

## First Sellable Wedge

Windows workstation black-box report:

- unexpected shutdown / Event 41
- BSOD / bugcheck signal
- disk and filesystem warnings
- WHEA hardware warnings
- low disk space before long jobs fail
- low memory before browser/model jobs hang
- top memory processes for context

## Self-Serve Only

No installation service.

The first product is a download/run tool:

```powershell
python scripts/system/scbe_black_box.py
```

It writes:

- `artifacts/black_box/latest_black_box_report.json`
- `artifacts/black_box/latest_black_box_report.txt`

## Why This Proves Value

The output is immediately legible:

```text
[HIGH] Windows recorded an unexpected shutdown
Why: Event 41 means Windows restarted without a clean shutdown.
Do:  Correlate the minutes before this event with disk, driver, WHEA, BugCheck, and power events below.
Evidence: 2026-06-16T03:14:00Z Microsoft-Windows-Kernel-Power #41...
```

That is the buyer moment. They do not need to care about the internal SCBE stack.

## Payment Shape

Use the Workcell/Black Box download as the low-friction entry:

- `$9` one-time: Black Box local report pack
- `$29` one-time: Workcell + Black Box bundle
- `$9/mo` later: hosted alerting/text-message lane

The monthly product should wait until alerting exists. The one-time product can ship now.

## Next Build

1. Add email/webhook alert output.
2. Add scheduled task instructions.
3. Add a simple HTML report.
4. Add optional Twilio/SMS route only after email/webhook works.
