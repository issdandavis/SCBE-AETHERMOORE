# AetherNet Firebase Handoff (2026-02-28)

## Active wiring status
- `src/fleet/firebase_connector.py` already provides:
  - `save_post`, `save_reply`, `save_reaction`, `create_platform_dispatch_rows`, `update_platform_dispatch`,
    `record_governance_event`, `get_feed`, `get_feed_since`, `get_feed_poll`-style polling, and platform stats.
- `src/aaoe/aethernet_service.py` now:
  - Writes replies/reactions to Firebase collections.
  - Exposes `/feed/poll` for timestamp polling.
  - Exposes `/feed/stream` SSE stream for near-real-time updates.
  - Adds strict Firebase auth toggle `AAE_REQUIRE_FIREBASE_AUTH` for mutable routes.
  - Adds `/economy/monetization` planning endpoint.
- Local secret-first Firebase client added at:
  - `skills/clawhub/scbe-content-publisher/utils/firebase_client.py`
- Firebase config example added:
  - `firebase-config.example.json`

## Required environment/secrets
- `AAE_REQUIRE_FIREBASE_AUTH=1` (optional)
- `FIREBASE_PROJECT_ID`
- `FIREBASE_SERVICE_ACCOUNT_KEY` (preferred, tokenized via secret store)
- `FIREBASE_CREDENTIALS_PATH` (optional, local json key file)

## Quick local wiring
```bash
# 1) Keep template for platform config
cp firebase-config.example.json firebase-config.json

# 2) Start from service directory
python -m uvicorn src.aaoe.aethernet_service:app --reload --port 8300
```

## Endpoint map
- `POST /feed/post` (req includes optional `platforms`)
- `GET /feed`
- `GET /feed/poll?since=...`
- `GET /feed/stream` (SSE)
- `POST /feed/{post_id}/reply`
- `POST /feed/{post_id}/react`
- `GET /economy/monetization`

## Schema source of truth
- `docs/03-deployment/aethernet_firestore_schema.md`

## Next recommended steps
1. Add a CI check to block committing `firebase-config.json`.
2. Add a small UI dashboard page that subscribes to `/feed/stream`.
3. Add alerting when Firebase sync fails during reply/reaction saves.
