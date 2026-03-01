---
name: scbe-content-publisher
description: Publish governed content to 9 platforms simultaneously — Twitter/X, LinkedIn, Bluesky, Mastodon, WordPress, Medium, GitHub, HuggingFace, and custom endpoints. All content passes 14-layer governance before posting.
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - SCBE_API_KEY
      bins:
        - curl
    primaryEnv: SCBE_API_KEY
    tags:
      - content
      - publishing
      - social-media
      - marketing
      - governance
      - scbe
---

# SCBE Content Publisher

Publish content across 9 platforms at once — every piece scanned by the 14-layer governance pipeline before it goes live. No more accidentally posting harmful, off-brand, or risky content.

## Supported Platforms

| Platform | Content Types | Governance Check |
|----------|--------------|------------------|
| Twitter/X | Tweets, threads | Yes (280 char + link preview) |
| LinkedIn | Posts, articles | Yes (professional tone check) |
| Bluesky | Posts | Yes |
| Mastodon | Toots | Yes |
| WordPress | Blog posts | Yes (full article scan) |
| Medium | Articles | Yes (full article scan) |
| GitHub | README, discussions | Yes (code + docs scan) |
| HuggingFace | Model cards, datasets | Yes (technical content scan) |
| Custom webhook | Any JSON payload | Yes |

## When to Use

Use this skill when the user asks you to:
- Publish content to social media
- Cross-post across multiple platforms
- Schedule content for later
- Create a content campaign
- Distribute announcements

## Steps

### 1. Prepare content

Format your content as a JSON payload:

```json
{
  "title": "Your Post Title",
  "body": "The main content body. Can be multiple paragraphs.",
  "platforms": ["twitter", "linkedin", "bluesky"],
  "tags": ["ai-safety", "governance"],
  "schedule": null,
  "agent_id": "<YOUR_AGENT_NAME>"
}
```

### 2. Submit to the content buffer

```bash
curl -s -X POST "https://scbe-governance.aethermoore.com/v1/content/publish" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SCBE_API_KEY" \
  -d '{
    "title": "<TITLE>",
    "body": "<CONTENT>",
    "platforms": ["twitter", "linkedin", "bluesky"],
    "tags": ["<TAG1>", "<TAG2>"],
    "schedule": null
  }'
```

Local fallback:
```bash
curl -s -X POST "http://localhost:8001/v1/buffer/post" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SCBE_API_KEY" \
  -d '{"title":"<TITLE>","body":"<CONTENT>","platforms":["twitter"]}'
```

### 3. Read the governance result

```json
{
  "status": "published",
  "governance": {
    "decision": "ALLOW",
    "risk_score": 0.08,
    "tongue": "AV"
  },
  "published_to": ["twitter", "linkedin", "bluesky"],
  "failed": [],
  "content_id": "cnt-abc123",
  "audit_hash": "7f3a2b..."
}
```

### 4. Handle governance blocks

If governance returns QUARANTINE or DENY:
- **QUARANTINE**: Content is held in the buffer. Tell the user: "Your content was flagged for review (risk: X). Would you like to edit it or publish anyway?"
- **DENY**: Content is blocked. Tell the user why and suggest edits.

## Firebase backend (governance persistence)

- Copy `firebase-config.example.json` to `firebase-config.json` and keep the real file private.
- Point the service to a service-account secret via secret store:

```bash
python - <<'PY'
from src.security.secret_store import set_secret
set_secret(
    "FIREBASE_SERVICE_ACCOUNT_KEY",
    '{\"type\":\"service_account\",...}',
    tongue="DR",
)
PY
```

- Optional environment fallback:
  - `FIREBASE_SERVICE_ACCOUNT_KEY`
  - `FIREBASE_CREDENTIALS_PATH`
  - `GOOGLE_APPLICATION_CREDENTIALS`
  - `FIREBASE_PROJECT_ID`

### Utility

`skills/clawhub/scbe-content-publisher/utils/firebase_client.py` defines a singleton `FirebaseClient` that:
- reads `firebase-config.json` for frontend config,
- loads service credentials from `FIREBASE_SERVICE_ACCOUNT_KEY`,
- exposes `.db`, `.auth`, and `.storage` properties for publisher tasks.

## Content Spin (Bonus)

Generate platform-optimized variations from a single piece:

```bash
curl -s -X POST "https://scbe-governance.aethermoore.com/v1/content/spin" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SCBE_API_KEY" \
  -d '{
    "source": "<ORIGINAL_CONTENT>",
    "platforms": ["twitter", "linkedin", "medium"],
    "style": "professional"
  }'
```

This uses Fibonacci content multiplication — 1 source becomes up to 63 variations across 7 platforms.

## Free Tier

- 10 publishes per day
- 3 platforms per publish
- Basic governance scan

## Pro Tier ($19/month)

- Unlimited publishes
- All 9 platforms
- Content spin engine
- Scheduling
- Analytics dashboard
- Audit trail
