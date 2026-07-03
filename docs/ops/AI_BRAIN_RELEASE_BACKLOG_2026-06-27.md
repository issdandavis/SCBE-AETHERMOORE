# AI Brain Release Backlog - 2026-06-27

This is the working order for turning the brain mapping notes into usable product surfaces. It intentionally starts with evidence and integration before new training.

## P0 - evidence discipline

- [ ] Locate or regenerate the exact 100-trial / 20-agent / 100-step brain integration result and save it to `artifacts/ai_brain/`.
- [ ] Add a small artifact writer to the brain integration runner so future metrics are persisted automatically.
- [ ] Add a release checklist item: no public metric claim without an artifact file.
- [ ] Update external-facing wording to avoid overclaims: no "geometric impossibility", no multiplier-as-hardness, no PBFT label unless implemented.
- [ ] Decide canonical core: default to `src/ai_brain/*`; mark Python copies as research/compat unless specifically promoted.

## P1 - AetherDesk integration

- [ ] Add a Brain/GeoSeal panel to AetherDesk with: mode, detector scores, state summary, last decision, last receipt.
- [ ] Route browser/terminal/action requests through a bounded brain gate before execution.
- [ ] Surface `ALLOW`, `QUARANTINE`, `DENY`, and `HUMAN_REVIEW` as visible product states.
- [ ] Keep terminal and PowerShell controls allowlisted by profile, not arbitrary host-shell text.
- [ ] Add a lightweight local CLI: `scbe brain check <action.json>` or equivalent.

## P1 - conlang coding lane

- [ ] Promote `scripts/system/mixed_expression_lane.py` into a documented executable demo.
- [ ] Connect the mixed-expression packet to `agents/agent_bus.py` tongue/STIB compile functions where possible.
- [ ] Require a compile/execute/receipt outcome for every segment.
- [ ] Add examples: Python start, Haskell expression, C++ function, custom binary/STIB patch.
- [ ] Use this lane to prove the six conlangs are useful coding tools, not just labels.

## P2 - consolidation

- [ ] Compare `src/ai_brain/*`, `python/scbe/*`, and `src/symphonic_cipher/scbe_aethermoore/ai_brain/*` feature by feature.
- [ ] Mark each duplicate feature as canonical, port-needed, archived, or research-only.
- [ ] Create one import surface for product code and one namespace for research experiments.
- [ ] Create `docs/ops/AI_BRAIN_PUBLIC_SAFE_WORDING.md` for launch copy.
- [ ] Add `docs/ops/AI_BRAIN_EVIDENCE_INDEX.md` linking claims, code, tests, and artifacts.

## P2 - data and training prep

- [ ] Build small-model user guides for AetherDesk routines: fill-in blanks, multiple choice route selection, scored long-form code assignments.
- [ ] Tag training data provenance: human original, user voice, AI output, verified research, unverified research, executable code, test, production, tool use.
- [ ] Preserve human spelling with corrections, e.g. `coool(cool)`, so models learn realistic user input and likely correction.
- [ ] Keep human-authored and open-source human data in the blend where possible.
- [ ] Avoid AI-only self-training mirrors; require human anchors and execution-verified generated rows.

## P3 - later training and cloud

- [ ] Do no new paid training until P0 artifacts and the product gate are clean.
- [ ] Use local GPU for small inference/eval where practical.
- [ ] Use Colab/HF only for workloads that exceed local capacity or need fast iteration.
- [ ] Before a 7B or larger run, define the eval gate, domain holdout, artifact output, and stop condition.

## Current next concrete task

Build the AetherDesk Brain/GeoSeal panel and route one safe action through it. That turns the architecture from notes into a visible product behavior.

## Added after 21D conservation-law note

- [ ] Resolve the 21D state mismatch: current product layout versus conservation-law layout.
- [ ] Add `BrainState21Conservation` as a named typed schema instead of overloading the existing product vector.
- [ ] Add claim-gate manifest entries for every high-risk metric claim.
- [ ] Use `scripts/system/claim_gate_adapter.py` to emit validation-gate-compatible JSON reports from saved claim metadata.
- [ ] Run `validation_gate.py` only on reports with real baseline/trained/control numbers and independent verifier metadata.

## Added after UTF/Python transfer issue

- [x] Add a text transference gate: `python/scbe/transference_gate.py`.
- [x] Add `UTF_TRANSFER` to the Rosetta concept seed data.
- [ ] Route BOM/UTF validation reports through `python -m python.scbe.transference_gate normalize` before passing them to strict Python tools.
- [ ] Keep STIB reserved for executable opcode/program binaries; do not misuse it for arbitrary text.

## Added after Infinity Library direction

- [x] Add language/library proof-level spec: `docs/specs/LIS_BIBLIOTECA_DE_INFINITY_LANGUAGE_LIBRARY_2026-06-27.md`.
- [x] Add initial language face registry: `python/scbe/language_library_registry.py`.
- [ ] Promote verified faces only when receipt paths exist.
- [ ] Add missing conlangs and external languages as `concept`, `book`, `emitter`, `parser`, `interpreter`, `compiler`, or `verified` rows.
- [ ] Connect the registry to AetherDesk so the AI sees which brushes are safe to execute and which are reference-only.
