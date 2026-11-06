# Guided Evidence Bus

Status: implemented locally; not yet published

## System map

```text
user or agent objective
  -> /ride or guided_evidence
  -> named route preset (fixed source stops and budgets)
  -> workspace search + scripts/research_api_bus.py
  -> complete per-source artifacts in SCBE_HOME/evidence/
  -> deterministic normalization and cross-source grouping
  -> compact context packet (E-number links + keywords)
  -> four-digest packet receipt + append-only receipt chain
  -> search_evidence / verify_evidence
```

| Node                 | Path                          | Role                                                                          | Authority/status               |
| -------------------- | ----------------------------- | ----------------------------------------------------------------------------- | ------------------------------ |
| Conversation runtime | `lib/agent-runtime.js`        | Exposes tools and steers research toward one bounded route                    | Existing runtime, modified     |
| Route/tool surface   | `lib/tool-registry.js`        | Allows only named presets and bounded arguments                               | Existing registry, modified    |
| Packet engine        | `lib/guided-evidence.js`      | Stores raw responses, emits compact references, searches and verifies packets | New                            |
| Receipt engine       | `lib/multi-hash-receipt.js`   | Canonical encoding, four digest views, previous-root chain and verification   | New                            |
| Tool receipt ledger  | `lib/session-store.js`        | Applies the chained receipt to every agent tool outcome                       | Existing store, upgraded       |
| Research adapters    | `scripts/research_api_bus.py` | Existing source-specific API normalization                                    | Reused; no new network adapter |

## Contracts and invariants

- A route name selects source stops from code; model text cannot provide an executable or endpoint.
- Source count is at most 6 and each source returns at most 5 records.
- External queries use an argument array with `shell: false`.
- Complete responses never appear in the compact tool result. They are stored under a workspace-keyed `SCBE_HOME/evidence` directory.
- Packet references carry stable `E` identifiers, source, title, safe URL, artifact pointer and item proof root.
- Cross-checks mean matching normalized identifiers/titles from at least two source names. They are not truth claims.
- Receipt canonicalization rejects cycles and non-finite numbers.
- Every chained record binds its sequence, previous root, payload and envelope through SHA-256, SHA3-256, BLAKE2s-256 and BLAKE2b-512.
- The chain pointer is a compound root containing all four domain-separated digest components; subsequent records anchor that complete root.
- Existing v1 tool receipts become a hashed legacy prefix. Once a v2 record anchors that prefix, mutation is detected.
- Hashes provide tamper evidence. Transferable authenticity still requires the secure agent-bus HMAC/ML-DSA layer.

## Budgets and stop conditions

- Context packet budget: 256-4,000 estimated tokens; default 1,200.
- Workspace search: 2 seconds, 1,500 files, 1 MiB per file.
- External source process: 40 seconds per stop.
- Ledger verification: 32 MiB maximum before append refuses.
- A malformed receipt chain refuses new appends.
- A missing external research bus produces an explicit failed stop; it never becomes an arbitrary shell fallback.
- A clean npm install supports the self-contained `code` route. Internet-backed stops require the trusted monorepo adapter until a packaged adapter is reviewed.

## Verification

Focused tests live in `tests/guided-evidence.test.cjs` and cover canonical hashes,
legacy anchoring, chain tamper rejection, compact packet generation, keyword
retrieval, complete packet verification and retained-artifact tamper rejection.

Verified on 2026-10-29:

- Focused conversation/security suite: 19 passed, 0 failed.
- Full CLI suite: 231 tests; 228 passed, 3 expected skips, 0 failed.
- `npm run selftest`: passed.
- `npm run pack:dry`: 86 files, including both new engines and this map.
- `npm run release:gate`: clean consumer install passed; the installed package created and verified a four-hash `code`-route packet.
