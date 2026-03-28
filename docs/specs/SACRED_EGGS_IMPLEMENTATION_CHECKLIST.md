# SCBE-AETHERMOORE Sacred Eggs: Implementation Checklist

Status: draft

Goal: implement the Sacred Eggs ritual-based genesis protocol on top of SS1, with deterministic logging and Notion/Obsidian-friendly documentation surfaces.

## Local source material (no API truncation)

- Notion export JSONL: `training-data/notion_raw_clean.jsonl`
- Mirror generator: `scripts/notion_export_to_markdown.py` (outputs to `docs/notion/mirror/`)

## 1. Current repo state (already exists)

- SS1 tokenizer + envelope helpers exist in TypeScript: [src/tokenizer/ss1.ts](../../src/tokenizer/ss1.ts)
- AetherAuth doc already uses SS1 envelopes for key storage: [docs/AETHERAUTH_IMPLEMENTATION.md](../AETHERAUTH_IMPLEMENTATION.md)
- Sacred Eggs are referenced at the architecture level: [docs/AGENT_ARCHITECTURE.md](../AGENT_ARCHITECTURE.md)
- Sacred Egg term is also used in a game mechanic (separate): [src/game/sacredEggs.ts](../../src/game/sacredEggs.ts)

## 2. Deliverables

- Canonical TS implementation of Sacred Egg packets (solitary, triadic, ring_descent)
- Canonical Python implementation (for runtime services and offline vault ops)
- Deterministic tests for shape binding, tongue consistency, and tamper/fail-to-noise behavior
- A thin Notion connector sync for Sacred Egg event logs
- Optional: ingest Notion export into a local markdown mirror without truncation

## 3. TypeScript tasks

- Add a new module (recommended): `src/crypto/sacred_eggs/`
- Define core types:
  - `SacredEggPacket` (shape_id, genesis_id, ritual_mode, ss1_envelope, witnesses)
  - `SolitaryEggPacket`
  - `TriadicEggPacket`
  - `RingDescentEggPacket`
- Implement core functions:
  - `computeShapeId(packet)`
  - `validateShape(packet)`
  - `sealEgg(payloadBytes, genesisPolicy, ctx)` -> packet
  - `hatchEgg(packet, proofs, ctx)` -> allow/deny/quarantine + payloadBytes (or noise)
- Ensure `shape_id` is authenticated:
  - bind `shape_id` into AAD
  - enforce tongue consistency for each SS1 field

## 4. Python tasks

- Add a new module (recommended): `python/sacred_eggs/`
- Mirror the TS packet types and validation rules.
- Provide offline utilities:
  - seal/unseal SS1 blobs
  - batch verify event logs
  - deterministic fail-to-noise on invalid hatch

## 5. Tests

- SS1 roundtrip (already partially covered by TS envelope helpers):
  - serialize/deserialize
  - create/parse envelope bytes
- Sacred Egg tests:
  - shape_id deterministic and stable
  - any field omission fails
  - tongue mismatch fails
  - AAD tamper fails
  - tag/ciphertext tamper fails
  - fail-to-noise path is deterministic (same invalid input -> same noise)

## 6. Notion connector + export

- Connector lane:
  - write Sacred Egg event logs into the Notion "AI Sacred Events Log" database (event_id, timestamp, actor, action, status, protocol_version, ring_position, payload_digest)
- Export lane (recommended for full-fidelity docs without API truncation):
  - locate the Notion export zip/folder
  - extract Sacred Eggs pages
  - mirror into `docs/09-notion-mirror/` (or into your Obsidian vault) with stable filenames

## 7. Open questions (to resolve before coding)

- Exact canonical field set for shape_id (do we always require `aad` and `nonce`, or keep them optional?)
- Quorum rule representation for `triadic` and `ring_descent`
- Default fail-to-noise function (HMAC vs hash, key source, determinism requirements)
- Where to persist genesis policies (repo JSON, Notion DB, or Obsidian vault as source of truth)
