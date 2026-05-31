# Polly training capture — private HF dataset contract

`api/polly/chat.js` and `api/polly/lead.js` durably capture consented turns
and lead submissions, pushing each as a single JSON file to the **private**
Hugging Face dataset
[`issdandavis/polly-chat-live`](https://huggingface.co/datasets/issdandavis/polly-chat-live)
(visible only to the dataset owner).

Path (since PR #1503, 2026-05-09): widget → Vercel Function →
`api/_polly_hf_upload.js` → HF NDJSON commit endpoint → private dataset.
The upload is awaited via `Promise.allSettled` so the serverless runtime
doesn't kill the function before the commit returns. Direct upload uses
`HF_TOKEN` only — no GitHub PAT required for the data path.

A parallel `repository_dispatch` to the `polly-training-capture` workflow
fires the **notification side effects** (GitHub issue + SMTP email) on
lead records. Direct HF upload remains the primary signal even when the
GitHub PAT isn't configured.

## What capture does (default)

By default everything is on:

- Widget checkbox at `docs/hire.html` ships **checked** — `consentToTrain: true`
- Vercel direct HF upload is enabled when `HF_TOKEN` is present on the project
- `POLLY_TRAIN_DISPATCH_ENABLED` controls only the GitHub notification dispatch
  path; it defaults to `'true'` in `api/_polly_train_capture.js` unless
  explicitly set to `'false'` on Vercel
- The workflow runs on dispatched lead events and files/sends notifications; it
  no longer uploads chat turns to Hugging Face

To turn direct capture off per-deploy, remove or rotate the Vercel `HF_TOKEN`
used by `api/_polly_hf_upload.js`. To turn lead notifications off per-deploy,
set `POLLY_TRAIN_DISPATCH_ENABLED=false` on Vercel. To turn capture off
per-conversation, the user unticks the checkbox.

## Required secrets

Set once on the GitHub repository (Settings → Secrets and variables → Actions):

| Secret | Where to get it | Purpose |
|---|---|---|
| `HF_TOKEN` | <https://huggingface.co/settings/tokens> | optional fallback for other HF workflows; the live Polly data path uses the Vercel `HF_TOKEN` |
| `GITHUB_TOKEN` (auto) | provided by GitHub | dispatch event from Vercel uses this |
| `POLLY_LEAD_SMTP_*` | your SMTP provider | optional email notifications for lead records; see `docs/deployment/POLLY_LEAD_EMAIL_SMTP.md` |

Set on the Vercel project (Settings → Environment Variables):

| Var | Value | Purpose |
|---|---|---|
| `POLLY_TRAIN_GITHUB_TOKEN` | a fine-grained PAT with `Contents: read` and `Metadata: read` on `issdandavis/SCBE-AETHERMOORE` | Vercel-side dispatch auth (or set `GITHUB_TOKEN` if your env already has one) |
| `POLLY_TRAIN_DISPATCH_ENABLED` | `true` (default) or `false` | per-deploy kill switch |
| `POLLY_TRAIN_REPO` | optional, defaults to `issdandavis/SCBE-AETHERMOORE` | which repo receives the dispatch event |
| `POLLY_HF_DATASET` | optional, defaults to `issdandavis/polly-chat-live` | which HF dataset receives the records |
| `HF_TOKEN` | Hugging Face write token | direct private dataset upload from the Vercel function |

## Path layout in the dataset

Each turn becomes one file:

```
polly-chat-live/
  2026-05-09/
    20260509T203412-a4f7c2.json
    20260509T203518-9bc81d.json
    ...
  2026-05-10/
    ...
```

Per-turn JSON shape (capped at 4 KB user / 8 KB assistant before upload):

```json
{
  "ts": 1715201652,
  "session_id": "hire-1715201640000",
  "intent": "research",
  "provider": "research",
  "user": "...",
  "assistant": "...",
  "page_context": "/hire",
  "transport": "vercel-polly-chat"
}
```

A daily consolidation script (TODO) can collapse the per-turn files into a
single `polly-chat-live/{YYYY-MM}.jsonl` shard for easier training-data import.

## Cost / volume notes

- HF dataset commits are free for accounts with a paid plan; the user has HF Pro.
- Consented chat turns do **not** consume GitHub Actions minutes; they upload
  directly from Vercel to Hugging Face.
- Lead submissions may consume one short GitHub Actions run for issue/email
  notifications when dispatch is enabled.

If lead volume grows past ~500/day, batch only the notification dispatch path.
The direct HF data path can remain one file per event unless commit volume
becomes inconvenient for dataset browsing.

## What never leaves the runtime

- Vercel function logs see a `polly_train_v1 {...}` line per consented turn
  (private to the project).
- Workflow logs see only lead notification side effects. Full lead contact and
  description stay in the private HF dataset and SMTP email body.
- The dataset itself is private; only the owner (Issac) and any explicit
  collaborators can list or download files.

## Smoke-checking the contract

```bash
# Disable for the next deploy
echo "POLLY_TRAIN_DISPATCH_ENABLED=false" | vercel env add POLLY_TRAIN_DISPATCH_ENABLED production

# Re-enable (or unset to use the on-by-default behaviour)
vercel env rm POLLY_TRAIN_DISPATCH_ENABLED production

# Local: confirm dispatch shape without firing it
node -e "console.log(require('./api/_polly_train_capture').trainConfig())"
```

Vitest contract: `tests/api/polly_commerce_js.test.ts` →
`polly training capture (repository_dispatch)`. The "defaults to enabled" case
is the load-bearing assertion.
