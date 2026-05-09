# Polly training capture — privacy-by-default contract

`api/polly/chat.js` can durably capture consented chat turns for training. As of
2026-05-09 the capture path is **off by default**. Two independent gates must
both be on for any record to leave the Vercel runtime:

1. **Per-message consent** — the request body must include `consent_to_train: true`.
   `docs/hire.html` ships an unchecked checkbox bound to the widget's
   `setConsent(boolean)` method, so the default user state is no-consent.
2. **Server-side enable** — the Vercel project must set
   `POLLY_TRAIN_DISPATCH_ENABLED=true`. Anything else (unset, `false`, `0`)
   short-circuits `dispatchTrainingTurn` to `{ ok: false, reason: 'disabled' }`.

When both gates are on, `dispatchTrainingTurn` fires a GitHub
`repository_dispatch` event of type `polly_training_turn` with the record as
`client_payload`. Vercel still writes a `polly_train_v1` line to its function
log (private to the project) regardless of dispatch state, so commerce-intent
turns remain auditable per-deploy without leaving Vercel.

## Where the data goes

The `polly-training-capture` workflow consumes the dispatched event and tries to
append the record to `training-data/polly-chat-live/{YYYY-MM}.jsonl` on `main`.

That path is **gitignored** at `.gitignore:92` (`training-data/**/*.jsonl`), so
the workflow's commit step deliberately no-ops with a "no tracked changes to
commit" message. Records reach the runner filesystem, get appended to a shard,
and are discarded when the runner shuts down.

This is intentional — until a private destination is wired, the workflow's job
is to (a) prove the dispatch path works end-to-end and (b) keep the option
open. **Do not turn `POLLY_TRAIN_DISPATCH_ENABLED=true` in production unless one
of the persistence options below is in place.**

## To make capture durable, pick one

- **Private companion repo** (preferred for low volume): create
  `issdandavis/polly-chat-live` as a private repository, set
  `POLLY_TRAIN_REPO=issdandavis/polly-chat-live` on Vercel, and update the
  workflow's `actions/checkout` `ref` to that repo. The training-data gitignore
  no longer applies, so the commit step will land actual files.
- **Private HF dataset**: replace the workflow's commit step with a
  `huggingface_hub.HfApi().upload_file` call against `issdandavis/polly-chat-live`
  with `private=True`. Requires `HF_TOKEN` as a workflow secret.
- **S3 with bucket policy**: forward the runner-local file to a private S3
  bucket via `aws s3 cp` with object lifecycle configured.

Whichever destination is chosen, document it here and revisit the
[`docs/deployment/VERCEL_COST_GUARD.md`](VERCEL_COST_GUARD.md) entry — additional
storage and CI cycles attach to this surface.

## What never leaves the runtime, even when capture is enabled

The chat handler caps `user` at 4 KB and `assistant` at 8 KB before
dispatching, and the workflow uses a Python heredoc to read `PAYLOAD` from the
environment without echoing it to the action log. Workflow logs on the public
repo therefore see only the shard path and a row counter, not the chat content.

## Smoke-checking the contract

```bash
# Default state should be disabled.
unset POLLY_TRAIN_DISPATCH_ENABLED
node -e "process.env.POLLY_TRAIN_DISPATCH_ENABLED='';\
require('./api/_polly_train_capture').dispatchTrainingTurn({ts:1}).then(r=>console.log(r))"
# expected: { ok: false, reason: 'disabled' }
```

The vitest contract lives at
`tests/api/polly_commerce_js.test.ts` — `polly training capture
(repository_dispatch)` describe block. The "defaults to disabled" case is the
load-bearing assertion.
