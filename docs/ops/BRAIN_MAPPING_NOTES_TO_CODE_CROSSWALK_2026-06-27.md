# Brain Mapping Notes to Code Crosswalk - 2026-06-27

Source: Issac's pasted brain mapping / PHDM / 21D conservation-law notes from chat on 2026-06-27.

Audit method: static local comparison against the repo. No tests, builds, or training runs were executed during this pass.

## Bottom line

The notes are not just loose theory. A large part of the architecture already exists as code, especially under `src/ai_brain/*`, with older or parallel Python/browser implementations in `python/scbe/*`, `agents/browser/*`, `aether-browser/src/*`, `api/main.py`, and `agents/agent_bus.py`.

The strongest product path is to treat `src/ai_brain/*` as the canonical product core, keep Python as research/compatibility, and wire the browser/runtime gates into AetherDesk as visible telemetry and control. The main risk is overclaiming validation: many AUC/perfect-separation numbers are present in comments/tests, but this audit did not confirm a persisted run artifact for the exact 100-trial claim.

## Claim-to-code matrix

| Claim / idea from notes | Local status | Evidence | Honest handling |
|---|---:|---|---|
| 21D unified brain state | Implemented/prototyped | `src/ai_brain/unified-state.ts`; `python/scbe/brain.py`; `python/scbe/phdm_embedding.py` | Keep as core state model. Confirm one canonical vector layout and stop duplicating incompatible 21D meanings. |
| Golden-ratio weighting / six tongues in state | Implemented/prototyped | `src/ai_brain/unified-state.ts`; `aether-browser/src/scbe_security_layer.py`; `agents/agent_bus.py` | Use as routing/weighting semantics, not security hardness by itself. |
| Poincare / hyperbolic containment | Implemented/prototyped | `src/ai_brain/unified-state.ts`; `python/scbe/brain.py`; `agents/browser/phdm_brain.py`; `agents/browser/bounds_checker.py` | Real gate/projection pattern. Phrase as containment thresholds and projections, not literal impossibility. |
| Conservation laws / RefactorAlign | Implemented/test surface exists | `src/ai_brain/conservation.ts`; `tests/ai_brain/conservation.test.ts` | Good candidate for a release gate. Needs current test artifact before using in external claims. |
| Phase + distance, curvature, Lissajous, drift, six-tonic detectors | Implemented/prototyped | `src/ai_brain/detection.ts`; duplicate Python/symphonic surfaces | Keep as orthogonal detector suite. AUC numbers must be backed by saved JSON artifacts. |
| End-to-end brain pipeline | Implemented/test surface exists | `src/ai_brain/brain-integration.ts`; `tests/ai_brain/brain-integration.test.ts` | Strong internal target. Do not claim current perfect separation until result artifact is saved or rerun. |
| GeoSeal immune response / quarantine | Implemented/prototyped | `src/ai_brain/immune-response.ts`; `agents/browser/action_validator.py`; `api/main.py`; `bin/geoseal.cjs` from prior memory | Productize as runtime safety lane for browser/agent actions. |
| PHDM 16-polyhedra / Hamiltonian thought paths | Implemented/prototyped | `python/scbe/brain.py`; `python/scbe/phdm_polyhedra.py`; `src/ai_brain/phdm-core.ts`; `tests/ai_brain/phdm-core.test.ts` | Needs canonical TS/Python alignment. Treat Hamiltonian path as validation/repair structure, not a neural replacement claim yet. |
| Flux states Polly/Quasi/Demi | Implemented/prototyped | `src/ai_brain/flux-states.ts`; `python/scbe/brain.py` | Useful runtime mode control for AetherDesk: normal, defensive, emergency. |
| Quasicrystal / sparse hyperbolic octree | Implemented/prototyped | `src/ai_brain/quasi-space.ts`; `tests/ai_brain/quasi-space.test.ts` | Keep as visualization/storage/reasoning scaffold. Needs measured product use. |
| Swarm formations / consensus | Implemented/prototyped | `src/ai_brain/swarm-formation.ts`; `agents/agent_bus.py`; `api/main.py` | Avoid calling simple majority vote PBFT/BFT unless the actual protocol is implemented. |
| Sacred Tongue compilation / STIB / conlang coding | Implemented/prototyped | `agents/agent_bus.py`; `python/scbe/tongue_isa.py`; `python/scbe/tongue_isa_binary.py`; mixed-expression lane draft | This is directly relevant to the mixed-expression coding goal. It should become a small executable demo lane. |
| Symphonic/audio audit axis | Partial/prototype | `agents/browser/action_validator.py`; `src/symphonic_cipher/*` | Keep as optional verifier/telemetry, not a release blocker. |
| Geometric impossibility | Overclaim as written | Multiple gates project/deny by thresholds | Reframe: invalid states become high-cost, projected, quarantined, or denied by implementation gates. |
| Multipliers as security | Overclaim as written | Sacred tongue weights, harmonic cost terms | Reframe: multipliers are cost/routing/priority weights. They are not cryptographic hardness alone. |
| Perfect AUC / 0% FP / 4.2 ms | Claimed in code comments/tests, not verified in this pass | `src/ai_brain/detection.ts`; `src/ai_brain/brain-integration.ts`; test files | Need saved artifact under `artifacts/ai_brain/` or a rerun before external release claims. |

## What we actually have

1. A real TS brain core exists under `src/ai_brain/*`.
2. A real Python research/compatibility brain exists under `python/scbe/*`.
3. Runtime browser/agent safety gates exist under `agents/browser/*`, `aether-browser/src/*`, and `api/main.py`.
4. Sacred Tongue / STIB-style compilation exists in `agents/agent_bus.py` and related Python modules.
5. Tests exist for many of these pieces, but this pass did not run them.
6. The repo needs a claim-evidence-result discipline before public release.

## Product interpretation

The practical product is not "the AI brain is proven alive." The practical product is:

- AetherDesk gives the AI a computer-like workspace.
- The brain core tracks every action as a 21D state with gates, mode changes, and receipts.
- GeoSeal/PHDM decide whether actions are allowed, quarantined, denied, or need human approval.
- Sacred Tongues and STIB give the AI extra coding notations and translation lanes.
- The validation gate decides whether a model/system improvement is real before we train or release.

That product can compete because it makes the AI's workspace inspectable, constrained, and iterative rather than just another chat box.

## Task list

### P0 - make claims safe and usable

- [ ] Find or regenerate the exact 100-trial brain-integration result artifact and save it under `artifacts/ai_brain/`. Do not externally claim perfect separation until this exists.
- [ ] Create a `CLAIMS_MATRIX.md` that maps every public claim to code path, test path, and result artifact.
- [ ] Pick `src/ai_brain/*` as canonical product core unless a specific Python-only feature blocks that.
- [ ] Reframe docs from "geometric impossibility" to "threshold/projection/quarantine containment".
- [ ] Reframe tongue multipliers as cost/routing weights, not standalone security hardness.
- [ ] Reframe swarm voting as majority/consensus unless true BFT/PBFT is implemented.

### P1 - wire the brain into AetherDesk

- [ ] Add a visible Brain/GeoSeal telemetry panel to AetherDesk: state vector summary, flux mode, detector scores, quarantine/allow/deny receipts.
- [ ] Bridge `BrainIntegrationPipeline` to browser actions through `agents/browser/action_validator.py` and `api/main.py`.
- [ ] Add a local CLI command for brain checks: feed an action, return decision, receipt, and detector breakdown.
- [ ] Keep host control bounded: terminal/powershell/browser/word-processor actions should be allowlisted and receipt-backed.
- [ ] Turn `POLLY/QUASI/DEMI` into actual AetherDesk modes: normal work, defensive work, emergency safe mode.

### P1 - make conlang coding executable

- [ ] Promote the mixed-expression coding lane into a small demo that compiles a packet through Python/Haskell/C++/STIB-style segments.
- [ ] Route the demo through existing `agents/agent_bus.py` tongue compile / binary functions where possible.
- [ ] Add one "does it compile or execute" receipt per segment.
- [ ] Keep the conlangs as brushes/tools for the AI, but measure them by emitted working artifacts.

### P2 - clean duplicates and release order

- [ ] Compare TS `src/ai_brain/*` against Python `python/scbe/*` and decide which features are canonical, ported, deprecated, or research-only.
- [ ] Consolidate duplicate `src/symphonic_cipher/scbe_aethermoore/ai_brain/*` behavior or clearly mark it as archived/experimental.
- [ ] Create result serializers for AUC, false positive rate, latency, detector breakdown, and release receipts.
- [ ] Add rounded-decimal / jitter data for the known remaining gap.
- [ ] Produce a public-safe release note that separates implemented, tested, prototype, and theory.

### P3 - training and model integration later

- [ ] Train/evaluate only after the runtime gates and claim matrix are clean.
- [ ] Use human-authored and verified open-source training data where possible.
- [ ] Preserve provenance tags: human original, AI output, verified research, unverified research, corrected human spelling, code, tests, production, tools.
- [ ] Avoid AI-only training mirrors. Keep human anchors and execution-verified outputs.
- [ ] Teach small models to follow AetherDesk routines through fill-in-the-blank guides, multiple-choice route selection, and scored code-assignment checklists.

## Release target order

1. Internal local: Brain check CLI + AetherDesk telemetry panel.
2. Developer demo: mixed-expression coding lane with receipts.
3. Evidence release: claim matrix + result artifacts.
4. Package release: npm/PyPI surfaces for GeoSeal/brain checks.
5. Training release: small-model user guide and routine corpus.
6. Public product: AetherDesk as AI workbench with browser, terminal, files, tools, Colab/HF lanes, and safety receipts.

## Working rule

For this system, the final gate is simple: does the generated thing compile, run, or produce a verifiable receipt in front of the user? If not, it stays in research or design.
