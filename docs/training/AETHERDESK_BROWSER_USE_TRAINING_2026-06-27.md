# AetherDesk Browser-Use Training Slice

Created: 2026-06-27
Scope: local preparation only. No non-local jobs launched.

## Files

- Train slice: `training-data/sft/aetherdesk_browser_use_v1.sft.jsonl`
- Holdout slice: `training-data/sft/aetherdesk_browser_use_v1_holdout.sft.jsonl`

## Purpose

Teach the SCBE coding/ops agent how to operate Aether Browser as a real product surface:

- inspect URLs through bounded browser routes
- build source receipts
- launch human or automated browser lanes intentionally
- keep HF/local tokens out of frontend/browser state
- avoid repeated pulls unless explicitly enabled
- hand browser evidence to AI Desk or Terminal without bypassing gates

## Local behavior target

The desired browser-use pattern is:

```text
user question + URL
  -> /api/playwright/view
  -> /api/web/audit
  -> optional /api/verified/ask
  -> display answer + source receipt
  -> optional handoff to AI Desk or bounded Terminal
```

## Security boundary

The browser never receives raw credentials.

Allowed in browser:

- connection status
- username
- run list metadata
- receipts
- source summaries

Server-side only:

- `HF_TOKEN`
- OAuth access tokens
- local shell access
- model/runtime credentials

## Evaluation prompts

Use the holdout file to check whether the model learned:

- no repeated overnight polling
- token boundary
- partial audit honesty

Minimum pass criteria:

```text
valid_json: 3/3
mentions_no_token_in_browser: 1/1
mentions_no_background_polling_by_default: 1/1
does_not_invent_source_claims: 3/3
```

## Human-authored open-source guide policy

Future browser-use training data should include human-written open-source guides whenever license-compatible and relevant. Synthetic examples are useful for exact local route behavior, but they should be balanced with real human-authored operational writing.

Minimum metadata for each imported guide-derived pair:

```json
{
  "source_type": "human_open_source_guide",
  "source_url": "...",
  "license": "...",
  "project": "...",
  "retrieved_at": "YYYY-MM-DD",
  "transformation": "summary | task_pair | policy_pair",
  "validated": false
}
```

Rules:

- verify license before adding source text
- keep guide-derived data in a separate slice
- prefer official project docs and maintained open manuals
- do not ingest unknown-license blog/forum text
- do not ingest private, paid, or terms-restricted content
- preserve provenance so ablations can compare synthetic-only vs human-guide-mixed behavior

## Local training recommendation

Do not train on this tiny slice by itself. Mix it into the existing VTC/domain corpus so the model does not overfit to route names.

Suggested next local-only run:

```text
base: existing 1.5B Qwen coder path
data: vtc_better + coding_system_full_v1_train + aetherdesk_browser_use_v1
holdouts: generic 6-problem gate + domain JSON holdout + browser_use_holdout
goal: preserve 5/6 code correctness and 6/6 bare-code contract while adding browser-use JSON action skill
```

## Non-local prep

When non-local runs are allowed, this slice can be included in the next 7B/domain run. Do not launch that run without explicit approval.
