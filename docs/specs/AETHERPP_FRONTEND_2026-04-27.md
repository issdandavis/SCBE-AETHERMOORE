# Aether++ Front-End

**Date:** 2026-04-27
**Status:** v0.1 implemented as a thin compiler layer
**Code:** `scripts/aetherpp_interpreter.py`
**Tests:** `tests/test_aetherpp_interpreter.py`

## Verdict on the Rough Draft

The draft has the right direction: Aether++ should be an English-like front-end that compiles into Six Tongues transport, GeoSeal route payloads, and agent-bus execution records.

The draft should not copy tokenizer code inline. The repository already has canonical tokenizer surfaces. Aether++ must import those surfaces, prove round-trip correctness, and emit route payloads that existing runners can consume.

The draft also mentions `ContinuousIntentField`, `AethermoorSpacaitaSystem`, and `Spacaita` as if they are implemented runtime primitives. They are not currently canonical repo primitives. In v0.1, Aether++ records a `continuous_intent_field` gate as metadata only and marks it as not authorization.

## Canonical Boundary

Aether++ uses these repo surfaces:

- `src.crypto.sacred_tongues.SACRED_TONGUE_TOKENIZER` for byte-level Sacred Tongue encoding.
- `src.geoseal_cli.compute_seal` for deterministic GeoSeal-style seals.
- `src.geoseal_cli.phi_wall_cost`, `phi_wall_tier`, and `phi_trust_score` for fold-risk metadata.
- `/runtime/run-route` request shape from `src/api/geoseal_service.py` as the route target.

It does not use `tools/aethermoore.py` as the canonical tokenizer because that file is a standalone compatibility CLI with its own generated token scheme.

## v0.1 Language Contract

The interpreter accepts period-delimited sentences:

```text
create spacaita system with 4 manifolds.
apply discrete fold 0.8 to manifold 0 with goal 0.95 in tongue KO.
cross propagate from manifold 0 to manifold 2.
encode "def add(a, b): return a + b" and seal with GeoSeal in tongue KO.
run route.
```

It emits:

- `schema_version: aetherpp_route_payload_v1`
- source hash
- intent-gate metadata
- manifold events
- propagation events
- Sacred Tongue token streams
- token round-trip proof
- deterministic seal
- a `route_request` compatible with the GeoSeal runtime service shape

## What This Is

Aether++ is a front-end compiler for governed route payloads.

It is useful for:

- training examples where English commands map to route payloads;
- AI-to-AI bus messages that need a deterministic execution shell;
- cross-tongue coding workflows where the prompt, code, token stream, and seal must stay together;
- future CLI integration under `python -m src.geoseal_cli`.

## What This Is Not

- Not a new tokenizer.
- Not a separate encryption system.
- Not a real continuous-intent authorization gate yet.
- Not a replacement for frozen evals, executable gates, or model-promotion tests.

## Run

```bash
python scripts/aetherpp_interpreter.py "create spacaita system with 4 manifolds. encode \"def add(a, b): return a + b\" and seal with GeoSeal in tongue KO. run route." --out execution_shell.json
```

```bash
PYTHONPATH=. python -m pytest tests/test_aetherpp_interpreter.py -v
```

## Next Implementation Fold

The next useful fold is a `geoseal aetherpp` subcommand that calls this interpreter and optionally posts the resulting `route_request` to `/runtime/run-route`. That should happen only after the current payload schema stabilizes through tests.

