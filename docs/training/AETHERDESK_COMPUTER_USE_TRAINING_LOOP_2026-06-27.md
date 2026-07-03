# AetherDesk Computer-Use Training Loop

Date: 2026-06-27
Status: first local implementation slice

## Goal

Train an AI to use AetherDesk like a full local computer:

- home screen
- browser/internet
- terminal
- PowerShell
- notebook/word-processing surface
- files
- AI Desk
- SCBE coding systems
- release staging

The model should plan actions, but AetherDesk should execute through bounded tools and write receipts.

## Current implementation slice

Added local browser-side trace recording:

- `C:/Users/issda/AetherDesk/react-desktop/src/training/traceRecorder.js`
- `C:/Users/issda/SCBE-AETHERMOORE/scripts/aetherdesk_episode_to_sft.py`

The recorder stores local events in browser `localStorage` under:

- `aetherdesk.training.trace.v1`
- `aetherdesk.training.episode.v1`

Retention policy:

- Keep only the newest 1,000 events.
- Keep the trace log under about 2 MB in browser storage.
- Export useful traces, curate them into compact SFT rows, then clear raw traces.
- Do not keep screenshots, page dumps, command logs, or large artifacts forever inside browser storage.
- Long-lived training artifacts belong in curated JSONL files with provenance, not raw UI event history.

The converter turns exported trace JSONL into SFT rows.

## Trace event shape

```json
{
  "schema": "aetherdesk.trace.event.v1",
  "episode_id": "ep_local",
  "timestamp": "2026-06-27T00:00:00.000Z",
  "type": "desktop.open_app",
  "payload": {
    "app": "browser"
  }
}
```

## High-value events

| Event | Meaning |
|---|---|
| `desktop.open_app` | Human or agent opened an app from the desktop shell. |
| `skill.open` | A skill card or browser preset was selected. |
| `browser.tool_post` | Browser sent a bounded request to a local route. |
| `terminal.submit` | Terminal command was submitted through the bounded terminal lane. |
| `powershell.run` | PowerShell runner command was submitted. |
| `training_trace.downloaded` | Trace JSONL was downloaded for curation. |

## SFT conversion

Manual conversion command after exporting a trace:

```powershell
python C:\Users\issda\SCBE-AETHERMOORE\scripts\aetherdesk_episode_to_sft.py C:\path\to\aetherdesk-trace.jsonl -o C:\Users\issda\SCBE-AETHERMOORE\training-data\sft\aetherdesk_computer_use_from_traces.sft.jsonl
```

The converter intentionally marks rows:

```json
{
  "validated": false,
  "requires_curation": true
}
```

That prevents raw traces from being treated as release-quality training data before review.

## Training stages

1. Navigation: open apps, switch windows, use the home screen.
2. Browser use: answer, browse, audit, agent modes with receipts.
3. Terminal/PowerShell: bounded commands with redaction.
4. Notebook/doc work: draft, revise, package.
5. SCBE coding systems: GeoSeal, tokenizers, compiler/binary/music lanes.
6. Release staging: prepare official artifacts, then stop for approval.

## Safety boundaries

- Browser state must not contain raw tokens.
- Trace recorder redacts common token/password shapes.
- Trace storage is bounded by count and approximate byte size.
- Delete, publish, paid compute, git push, and training runs remain approval-gated.
- Raw traces are not automatically trusted.
- Human-authored open-source data remains the anti-collapse anchor.

## Next implementation steps

1. Add a visible Training Recorder app/panel inside AetherDesk.
2. Add receipt drawer integration.
3. Export browser receipts directly to trace events.
4. Add curation UI: approve, reject, label, and validate trace rows.
5. Add eval suite for AetherDesk computer-use tasks.
6. Only then run fine-tuning.
