# SpiralAuth AI Operations Package

SpiralAuth is an intent-bound AI operations envelope for agents, automation tools, and command routers. It does not replace the SCBE security stack. Sacred Eggs and the separate authorization/security systems remain responsible for authority; SpiralAuth binds a request's declared intent, execution modality, policy context, timestamp, nonce, and body hash into a canonical envelope that can be integrity-checked, logged, replay-checked, and evaluated by an AI governance gate.

## What It Does

- Converts a command into a structured intent envelope.
- Adds execution modality: deterministic, adaptive, read-only probe, delegated, or emergency.
- Preserves a private lexicon or Sacred Tongues/conlang layer as an intent-labeling and routing layer.
- Computes harmonic or spectral fingerprints as additional consistency evidence.
- Applies an optional keyed integrity check to the canonical envelope.
- Rejects body tamper, associated-data tamper, stale timestamps, replay, and wrong-session operation packets.
- Routes the checked request through AI operation gates such as `ALLOW`, `QUARANTINE`, `ESCALATE`, or `DENY`.

## Defensible Operational Claims

- The conlang layer is not encryption by itself. Its role is proprietary AI command taxonomy, intent labeling, and routing.
- Authority is handled separately by Sacred Eggs and the SCBE security stack.
- SpiralAuth improves AI operation control because the system records what kind of execution was requested before an agent or tool acts.
- Tamper and replay hygiene come from canonical hashing, optional keyed integrity checks, nonce/timestamp checks, and replay guards.
- Audit value comes from stable envelope fields: `intent_id`, `phase`, `schema_hash`, `canonical_body_hash`, `request_id`, `session_id`, and AI policy decision metadata.

## Existing Proof Points In This Repo

- `src/spiralauth/index.ts` provides the sellable SDK surface for packaging and checking intent-bound AI operation envelopes.
- `tests/spiralauth/spiralauth.test.ts` verifies valid envelopes and rejects modality tamper, body tamper, stale envelopes, and unknown private-lexicon tokens.
- `src/crypto/envelope.ts` uses AES-256-GCM with authenticated associated data, HKDF key derivation, nonce discipline, timestamp/TTL enforcement, and replay checks.
- `tests/acceptance.tamper.test.ts` verifies AAD tamper, body tamper, and timestamp skew rejection.
- `src/symphonic/HybridCrypto.ts` signs intents with an HMAC-bound harmonic signature envelope.
- `tests/symphonic/symphonic.test.ts` verifies valid intent signatures, rejects tampered intents, rejects wrong keys, and supports compact signatures.
- `src/gateway/authorize-service.ts` exposes an authorization route that turns kernel decisions into HTTP decisions.
- `public/spiralauth.html` is the buyer-facing demo for intent-modulated command authentication.

## Product Positioning

Tagline:

> Security decides who is allowed. SpiralAuth tells the AI system what kind of operation it is allowed to perform.

Primary buyer:

- AI agent framework builders.
- Enterprise AI governance teams.
- Internal platform teams routing tool calls across LLMs, scripts, CI, cloud jobs, or local agents.
- Platform teams that need auditable tool-use envelopes for AI actions.

Initial paid wedge:

- A developer SDK plus hosted policy dashboard for AI operation envelopes, replay rejection, and intent policy logs.

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
3. The method of claim 1 further comprising checking integrity of the canonical intent envelope using keyed authentication or authenticated encryption with associated data.
4. The method of claim 1 further comprising computing a harmonic, spectral, or multi-representation consistency fingerprint for the command request and storing the fingerprint as non-authoritative intent evidence.
5. The method of claim 1 further comprising evaluating the checked envelope against a policy engine that maps the request to an AI operation decision.
6. The method of claim 5 wherein the AI operation decision comprises one of allow, quarantine, escalate, or deny.
7. The method of claim 1 wherein a private constructed-language vocabulary maps command tokens to intent classes before envelope routing.
8. The method of claim 7 wherein the private vocabulary is used for command classification and routing and is not required as the sole cryptographic secret.

## Next Build Steps

1. Add an Express middleware example using `signSpiralAuthCommand` and `verifySpiralAuthEnvelope`.
2. Add a `spiralauth` CLI wrapper for signing, verifying, and tamper-demo smoke tests.
3. Add one buyer-facing README with copy-paste SDK examples.
4. Publish the demo page and link it from the main demo index.
5. Keep all claims worded as AI operation routing and audit, not replacement security, physics-based cryptography, or language-only cryptography.
