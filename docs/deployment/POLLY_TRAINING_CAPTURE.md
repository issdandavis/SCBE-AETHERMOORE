# Polly training capture — private HF dataset contract

`api/polly/chat.js` durably captures consented chat turns and pushes them to
the **private** Hugging Face dataset
[`issdandavis/polly-chat-live`](https://huggingface.co/datasets/issdandavis/polly-chat-live)
(visible only to the dataset owner). As of 2026-05-09 the path is wired
end-to-end: widget → Vercel Function → GitHub `repository_dispatch` →
`polly-training-capture` workflow → `huggingface_hub.upload_file` →
private dataset.

## What capture does (default)

By default everything is on:

- Widget checkbox at `docs/hire.html` ships **checked** — `consentToTrain: true`
- `POLLY_TRAIN_DISPATCH_ENABLED` defaults to `'true'` in `api/_polly_train_capture.js`
  unless explicitly set to `'false'` on Vercel
- Workflow runs on every dispatched event and uploads one JSON file per turn

To turn capture off per-deploy, set `POLLY_TRAIN_DISPATCH_ENABLED=false` on
Vercel. To turn capture off per-conversation, the user unticks the checkbox.

## Required secrets

Set once on the GitHub repository (Settings → Secrets and variables → Actions):

| Secret | Where to get it | Purpose |
|---|---|---|
| `HF_TOKEN` | <https://huggingface.co/settings/tokens> | workflow uploads to the private dataset |
| `GITHUB_TOKEN` (auto) | provided by GitHub | dispatch event from Vercel uses this |

Set on the Vercel project (Settings → Environment Variables):

| Var | Value | Purpose |
|---|---|---|
| `POLLY_TRAIN_GITHUB_TOKEN` | a fine-grained PAT with `Contents: read` and `Metadata: read` on `issdandavis/SCBE-AETHERMOORE` | Vercel-side dispatch auth (or set `GITHUB_TOKEN` if your env already has one) |
| `POLLY_TRAIN_DISPATCH_ENABLED` | `true` (default) or `false` | per-deploy kill switch |
| `POLLY_TRAIN_REPO` | optional, defaults to `issdandavis/SCBE-AETHERMOORE` | which repo receives the dispatch event |
| `POLLY_HF_DATASET` (workflow var) | optional, defaults to `issdandavis/polly-chat-live` | which HF dataset receives the records — set as a repo *variable*, not secret |

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
- Each consented turn = 1 GitHub Actions minute (workflow runtime ~30s).
- At 100 turns/day that's ~3000 minutes/month — within free GitHub Actions
  allotment for personal accounts (2000) plus public-repo concession.

If volume grows past ~500 turns/day, batch the workflow (e.g. trigger every
N minutes) instead of per-event.

## What never leaves the runtime

- Vercel function logs see a `polly_train_v1 {...}` line per consented turn
  (private to the project).
- Workflow logs see only `uploaded to private dataset: {repo}/{path}` —
  PAYLOAD is read via env var into Python without echoing.
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
