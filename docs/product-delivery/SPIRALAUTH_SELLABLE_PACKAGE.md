# SpiralAuth Sellable Package

SpiralAuth is an intent-bound authorization layer for AI agents, automation tools, and command routers. It does not replace cryptography. It binds a request's declared intent, execution modality, policy context, timestamp, nonce, and body hash into a canonical envelope that can be authenticated, logged, replay-checked, and evaluated by a governance gate.

## What It Does

- Converts a command into a structured intent envelope.
- Adds execution modality: deterministic, adaptive, read-only probe, delegated, or emergency.
- Preserves a private lexicon or Sacred Tongues/conlang layer as an intent-labeling and routing layer.
- Computes harmonic or spectral fingerprints as additional consistency evidence.
- Signs the canonical envelope using standard keyed authentication.
- Rejects body tamper, associated-data tamper, stale timestamps, replay, and wrong-session verification.
- Routes the verified request through policy gates such as `ALLOW`, `QUARANTINE`, `ESCALATE`, or `DENY`.

## Defensible Security Claims

- The conlang layer is not encryption by itself. Its role is proprietary command taxonomy, intent labeling, and friction against casual prompt/command injection.
- The cryptographic boundary is standard keyed authentication over canonical request data.
- Security improves because the system authenticates what kind of execution was requested, not only who sent the request.
- Tamper resistance comes from canonical hashing, keyed signatures or AEAD, nonce/timestamp checks, and replay guards.
- Audit value comes from stable envelope fields: `intent_id`, `phase`, `schema_hash`, `canonical_body_hash`, `request_id`, `session_id`, and policy decision metadata.

## Existing Proof Points In This Repo

- `src/crypto/envelope.ts` uses AES-256-GCM with authenticated associated data, HKDF key derivation, nonce discipline, timestamp/TTL enforcement, and replay checks.
- `tests/acceptance.tamper.test.ts` verifies AAD tamper, body tamper, and timestamp skew rejection.
- `src/symphonic/HybridCrypto.ts` signs intents with an HMAC-bound harmonic signature envelope.
- `tests/symphonic/symphonic.test.ts` verifies valid intent signatures, rejects tampered intents, rejects wrong keys, and supports compact signatures.
- `src/gateway/authorize-service.ts` exposes an authorization route that turns kernel decisions into HTTP decisions.
- `public/spiralauth.html` is the buyer-facing demo for intent-modulated command authentication.

## Product Positioning

Tagline:

> Authentication tells you who made a request. SpiralAuth also binds what execution mode the request was allowed to mean.

Primary buyer:

- AI agent framework builders.
- Enterprise AI governance teams.
- Internal platform teams routing tool calls across LLMs, scripts, CI, cloud jobs, or local agents.
- Security teams that need auditable tool-use envelopes for AI actions.

Initial paid wedge:

- A developer SDK plus hosted policy dashboard for AI command-envelope signing, replay rejection, and intent policy logs.

## Minimal Commercial SKU

Developer package:

- TypeScript SDK exports.
- Browser demo.
- CLI example.
- Express middleware example.
- Policy configuration examples.
- Tamper/replay test suite.

Pro package:

- Audit log viewer.
- Webhook verification.
- Team policy files.
- Agent/tool registry.
- Hosted verification endpoint.

Enterprise package:

- On-prem verification service.
- SSO/SIEM integration.
- Custom intent taxonomy.
- Compliance export.
- Support for customer-specific command lexicons.

## Patent-Safe Claim Skeleton

1. A computer-implemented method comprising receiving a command request and generating a canonical intent envelope containing at least an intent identifier, execution modality, phase, timestamp, nonce, schema hash, body hash, and request identifier.
2. The method of claim 1 further comprising deriving one or more verification keys from a master key and at least a session identifier and the intent identifier.
3. The method of claim 1 further comprising authenticating the canonical intent envelope using keyed authentication or authenticated encryption with associated data.
4. The method of claim 1 further comprising computing a harmonic, spectral, or multi-representation consistency fingerprint for the command request and storing the fingerprint as non-authoritative intent evidence.
5. The method of claim 1 further comprising evaluating the authenticated envelope against a policy engine that maps the request to an authorization decision.
6. The method of claim 5 wherein the authorization decision comprises one of allow, quarantine, escalate, or deny.
7. The method of claim 1 wherein a private constructed-language vocabulary maps command tokens to intent classes before envelope authentication.
8. The method of claim 7 wherein the private vocabulary is used for command classification and routing and is not required as the sole cryptographic secret.

## Next Build Steps

1. Add a small `spiralauth` CLI wrapper around `HybridCrypto.signCompact` and `verifyCompact`.
2. Add an Express middleware example using `createEnvelope` and `verifyEnvelope`.
3. Add one buyer-facing README with copy-paste examples.
4. Add a five-minute smoke test script that signs, tampers, rejects, and verifies.
5. Publish the demo page and link it from the main demo index.
6. Keep all claims worded as intent-bound authorization, not physics-based or language-only cryptography.
