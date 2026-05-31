# Free-First Agent And Storage Policy

Date: 2026-05-08

## Goal

Customers should be able to use the Aethermoor Bus agent experience without bringing their own model API keys.

The system should survive connection loss and degraded providers by falling back instead of breaking:

1. local/cloud model if available,
2. zero-credit public-source tools,
3. deterministic offline mode,
4. local export so user data can leave the bus without paid platform storage.

## Runtime Policy

Default customer experience:

- no customer model API key required;
- backend owns any configured Hugging Face or hosted provider token;
- local Ollama can be used when the deployment can reach it;
- deterministic offline responses remain available when no live model answers;
- public-source search uses zero-credit endpoints;
- cloud spend should be opt-in and capped by deployment configuration.

Current surfaces:

- `api/agent/chat.js` - provider order: Ollama, Hugging Face, offline.
- `api/agent/search.js` - zero-credit public-source search fanout.
- `api/agent/health.js` - reports chat and storage policy.
- `api/agent/storage.js` - zero-server-storage export packet builder and provider option registry.

## Storage Policy

Do not make AetherMoore the default file host yet.

Default storage should be:

1. **Download to this device** - browser-generated export packet.
2. **Browser local storage** - small local history, preferences, and feedback.
3. **User-owned cloud handoff** - GitHub, Dropbox, OneDrive, or Google Drive buttons.

This keeps the customer experience free while still letting files leave the bus.

Supported storage options:

| Provider | Cost to AetherMoore | Auth | Mode |
| --- | --- | --- | --- |
| Local download | zero | none | browser download |
| Browser local storage | zero | none | local storage |
| GitHub | zero if user-owned | user/server token | external handoff |
| Dropbox | zero if user-owned | user OAuth/manual upload | external handoff |
| OneDrive | zero if user-owned | user OAuth/local sync/manual upload | external handoff |
| Google Drive | zero if user-owned | user OAuth/local sync/manual upload | external handoff |

## Product Rule

The product can say:

> Customers do not need to bring model keys for the default experience. Aethermoor Bus runs free-first: local model when available, configured backend fallback when enabled, zero-credit research sources, and offline mode when disconnected. Storage defaults to device-local export, with optional handoff to user-owned cloud accounts.

The product should not say:

> Unlimited free cloud AI and free cloud file hosting.

That would create uncontrolled cost exposure.

## Next Frontend Slice

Add storage buttons to the mobile/web agent UI:

- Save to device
- Keep on this device
- Send to GitHub
- Send to Dropbox
- Send to OneDrive
- Send to Google Drive

The first two should work immediately. The cloud buttons can begin as export/download handoffs, then upgrade to OAuth flows later.
