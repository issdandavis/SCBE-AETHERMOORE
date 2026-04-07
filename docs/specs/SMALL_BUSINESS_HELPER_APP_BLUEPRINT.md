# Small Business Helper App Blueprint

Status: active blueprint  
Date: 2026-03-31  
Scope: mobile chat lane, training export loop, and near-term product architecture for the Small Business Helper app

## What Exists Now

- Mobile product surface: [small-business-helper.html](/C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/small-business-helper.html)
- Shared chat engine with session storage, compare-model lanes, and export actions: [polly-hf-chat.js](/C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/static/polly-hf-chat.js)
- Generic chat surface linked back to the helper lane: [chat.html](/C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/chat.html)
- Mobile operator notes: [CHAT_SETUP.md](/C:/Users/issda/SCBE-AETHERMOORE/kindle-app/CHAT_SETUP.md)
- Existing seed trainer for Polly chat: [train_polly_chat_sft.py](/C:/Users/issda/SCBE-AETHERMOORE/scripts/train_polly_chat_sft.py)
- New export ingester for mobile helper captures: [ingest_small_business_helper_exports.py](/C:/Users/issda/SCBE-AETHERMOORE/scripts/ingest_small_business_helper_exports.py)

## Product Goal

Ship one mobile assistant that can:

1. Serve small-business workflows in a constrained, read-first mode.
2. Capture conversations with Polly and stronger comparison models in the same thread.
3. Turn those conversations into governed local training data.
4. Feed the resulting corpus into the existing SCBE SFT and Hugging Face training lanes.

This is the shortest path from "chat app" to "small-business helper that improves from real operator use."

## Training Stance

The phone lane is not only a product surface. It is also a training stage.

The progression should be:

1. emulator phone lane
2. personal-extension assistant
3. governed delegation lane
4. small-business helper product

That progression is defined in [PHONE_AS_TRAINING_LANE.md](/C:/Users/issda/SCBE-AETHERMOORE/docs/specs/PHONE_AS_TRAINING_LANE.md).

The important design consequence is that the mobile lane should train for:
- short high-value answers
- persistent session continuity
- quick triage and drafting
- compare-lane capture when it improves training quality
- zero dependence on provider secret entry on-device

## Runtime Shape

### Client lane

- The helper runs inside the Kindle/Capacitor shell.
- Sessions persist locally in browser storage, so the phone lane survives restarts.
- One prompt can fan out to the primary Polly model plus optional larger comparison models.
- The compare lane is product work first and training work second. It exists to capture stronger answer shapes without forcing the main UX into a benchmark screen.

### Export lane

- `Export thread` writes the full bundle as JSON.
- `Export SFT` writes flat JSONL rows for quick inspection.
- `Export feedback` writes lightweight preference records.

The canonical export for training should be the thread bundle JSON, because it preserves system prompt, session identity, lane labels, and model provenance.

### Ingestion lane

- Run the ingester against one file or a directory of downloads:

```powershell
python scripts/ingest_small_business_helper_exports.py `
  artifacts/mobile_exports/small-business-helper `
  --out training-data/sft/small_business_helper_mobile.jsonl
```

- The ingester converts thread bundles into chat-format `messages` rows.
- It preserves metadata such as model, lane, session ID, exported source, and title.
- It skips initial boilerplate assistant text and skips `error` lane messages.
- It deduplicates by `(user, assistant, model)` so repeated exports do not bloat the corpus.

## Data Contract

The output corpus lands in [small_business_helper_mobile.jsonl](/C:/Users/issda/SCBE-AETHERMOORE/training-data/sft/small_business_helper_mobile.jsonl) and follows the repo-native chat shape:

```json
{
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "track": "polly_chat",
  "source_type": "small_business_helper_mobile",
  "quality": "captured",
  "surface": "small_business_helper",
  "source": "artifacts/mobile_exports/small-business-helper/example.json",
  "metadata": {
    "session_id": "scbe-chat-...",
    "model": "issdandavis/scbe-pivot-qwen-0.5b",
    "lane": "primary"
  }
}
```

This shape is compatible with the existing chat-corpus merge path in [merge_chat_sft_corpus.py](/C:/Users/issda/SCBE-AETHERMOORE/scripts/merge_chat_sft_corpus.py) and with the current Polly seed trainer assumptions.

## Delivery Phases

### Phase 0: Base lane

- Helper page exists.
- Session persistence exists.
- Compare-model capture exists.
- Export actions exist.

### Phase 1: Training loop

- Move exported helper bundles into `artifacts/mobile_exports/small-business-helper/`.
- Ingest them into `training-data/sft/small_business_helper_mobile.jsonl`.
- The default `merge_chat_sft_corpus.py` path now auto-includes `small_business_helper_mobile.jsonl` when the file exists.
- Score captured mobile conversations not just for answer quality, but for "personal extension" behavior: continuity, brevity, routing quality, and next-step usefulness.

### Phase 2: Governance tightening

- Add task-mode routing for bookkeeping, customer replies, inventory, and compliance review.
- Add stronger refusal paths for legal, destructive, or financial execution claims.
- Add proxy-backed server route for public deployment so no raw token is shipped to browsers.

### Phase 3: Productization

- User profiles or business profiles.
- Structured workspace memory per business.
- Read-only connectors first.
- Write actions only behind explicit quarantine and review gates.

## Immediate Build Backlog

1. Wire the helper into every phone-shell preset surface so it is launchable without manual URLs.
2. Add a local import screen so downloaded thread bundles can be reviewed on-device before ingest.
3. Add preference-pair conversion from exported feedback into a DPO-ready dataset.
4. Add Android emulator smoke coverage for helper launch, compare lane, and export buttons.
5. Add mobile QA criteria for personal-extension behavior so the phone lane trains the right assistant before we expand business-tool execution.

## Revenue Fit

This app is the front door for the Small Business Helper product spec in [SMALL_BUSINESS_HELPER.md](/C:/Users/issda/SCBE-AETHERMOORE/docs/specs/SMALL_BUSINESS_HELPER.md).

The free version is the governed chat lane. Paid value starts when the app can remember the business context, pull in read-only business data, and prove that its guidance is self-auditing rather than generic chat.
