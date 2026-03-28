# SCBE-AETHERMOORE Sacred Eggs: Genesis Protocol (Spec)

Status: draft

This spec consolidates the Sacred Eggs material captured in Notion (Ritual-Based Genesis Protocol; Sacred Egg Data Packets; Complete Integration Pack) with the existing SS1 implementation in this repo.

## Local source material (no API truncation)

- Notion export JSONL: `training-data/notion_raw_clean.jsonl`
- Notion index/datasheet: `training-data/datasheets/notion_datasheet_latest.json`
- Mirror generator: `scripts/notion_export_to_markdown.py` (outputs to `docs/notion/mirror/`)
- Prior systems model doc: `docs/01-architecture/sacred-eggs-systems-model.md`

## 1. What Sacred Eggs Are

A Sacred Egg is a sealed packet that carries a payload plus a hatch policy, such that:

- The payload is never stored or transmitted in plaintext.
- Hatching is only allowed when evidence, authority, and context satisfy a defined protocol.
- On failure, the system fails closed and can optionally fail-to-noise.

Sacred Eggs are intended for:

- high-risk secrets (API keys, signing keys, vault material)
- long-lived AI services with autonomous workflows
- multi-party or multi-surface governance (transfer, disputes, archival)

## 2. Canonical Container: SS1 (SpiralSeal / Spiralverse System 1)

SS1 provides a deterministic envelope shape and a bijective byte-to-token encoding using the Six Sacred Tongues.

### 2.1 Envelope fields

Canonical compact envelope shape (string form):

`SS1|kid=...|salt=RU:<spell-text>|ct=CA:<spell-text>|tag=DR:<spell-text>|aad=AV:<spell-text>|nonce=KO:<spell-text>`

Notes:

- `aad` and `nonce` are optional in the TypeScript implementation.
- Notion guidance: compact format (one tongue marker per field) is the production standard; verbose per-token markers are for debugging/logging.

### 2.2 Field-to-tongue mapping (repo canonical)

These domains are defined in [src/tokenizer/ss1.ts](../../src/tokenizer/ss1.ts):

- `KO` = Nonce / Flow / Control
- `AV` = AAD / Context / I/O
- `RU` = Salt / Binding / Policy
- `CA` = Ciphertext / Compute
- `UM` = Redaction / Security (not used by default SS1 envelope fields, but available)
- `DR` = Auth Tags / Schema

### 2.3 Implementation references in this repo

- SS1 tokenizer + envelope helpers: [src/tokenizer/ss1.ts](../../src/tokenizer/ss1.ts)
- SS1 envelope usage for AetherAuth: [docs/AETHERAUTH_IMPLEMENTATION.md](../AETHERAUTH_IMPLEMENTATION.md)
- Full SS1 reference (archival): [docs/08-reference/archive/SPIRALSEAL_SS1_COMPLETE.md](../08-reference/archive/SPIRALSEAL_SS1_COMPLETE.md)

## 3. Genesis Protocol

A Genesis Protocol is the binding policy that gives a Sacred Egg its identity and rules. At minimum it should define:

- `genesis_id` (stable ID for the protocol version)
- `owner_id` (the human or service authority)
- `ring_policy` (which trust-ring states are allowed to hatch)
- `ritual_mode` (solitary, triadic, ring_descent)
- `quorum_rule` (for multi-party)
- `expiry_policy` (time bound / rotation)
- `logging_policy` (what must be recorded)

## 4. Self-Detect Shape (shape + tag invariant)

Your requirement: `self_detect_shape(self_shape + self_tag)`.

This spec defines that as a concrete invariant:

- Every Sacred Egg MUST carry a canonical `shape_id`.
- The cryptographic tag (or an additional witness) MUST authenticate `shape_id` and the envelope field set.
- Any mismatch in shape, tongues, or required fields MUST fail closed.

### 4.1 Canonical shape_id

Define `shape_id` as a stable, deterministic string. Example:

`SS1/compact/v1|fields=kid,salt,ct,tag,aad,nonce|tongues=salt:RU,ct:CA,tag:DR,aad:AV,nonce:KO`

### 4.2 Binding shape into authentication

Recommended binding strategy:

- Include `shape_id` inside AAD bytes.
- Use AEAD so that any `shape_id` tampering invalidates the tag.

In other words, the verified tag implies the verified shape.

### 4.3 Tongue consistency check

On parse/hatch, validate:

- `salt` tokens are RU
- `ct` tokens are CA
- `tag` tokens are DR
- if present: `aad` tokens are AV
- if present: `nonce` tokens are KO

This is already mechanically supported by SS1 tongue detection helpers.

## 5. Ritual Modes (Notion-aligned)

The Notion packet spec describes three ritual modes to implement:

- `solitary`: single authority incubates and hatches
- `triadic`: multi-egg / multi-party binding, quorum-based hatch
- `ring_descent`: controlled OUTER -> INNER privilege descent, with additional evidence requirements

Each ritual mode must define:

- required approvers / witnesses
- allowed transitions
- what gets logged
- what data must be redacted or destroyed after seal ("yolk zeroing")

## 6. Event Logging (Notion-aligned)

Notion includes an "AI Sacred Events Log" concept with fields like:

- event_id
- timestamp
- actor
- action
- status
- protocol_version
- ring_position
- language_pair
- payload (digest or handle, not plaintext)

Sacred Eggs should emit structured events for:

- create
- seal
- hatch_request
- hatch_allow / hatch_deny / hatch_quarantine
- witness_attest
- revoke / rotate

## 7. Naming note

This repo also has a game mechanic called "Sacred Egg Hatching" in [src/game/sacredEggs.ts](../../src/game/sacredEggs.ts). That is separate from the cryptographic Sacred Eggs genesis protocol.

If we implement the cryptographic system in TS, prefer a distinct module path such as `src/crypto/sacred_eggs/` to avoid collisions.
