# SCBE-AETHERMOORE Codebase & Research Review

Saved: 2026-03-26
Status: Working synthesis packet
Purpose: Preserve the cross-repo review notes, current experimental framing, and immediate action lanes in one repo-local document.

## Source note

This document preserves a user-supplied cross-repo codebase and research review covering:
- `issdandavis/SCBE-AETHERMOORE`
- `scbe-security-gate`
- `Entropicdefenseengineproposal`
- `SCBE-QUANTUM-PROTO`
- `AI-Generated-Agents`

It also records the current internal framing adjustment:
- the strongest sellable invention is not Bible-specific interpretation
- the stronger claim is `multi-channel semantic constraint detection via structured absence`

---

## Executive summary

Across the specified repositories, the core defensive substrate lives in `issdandavis/SCBE-AETHERMOORE`, which contains:
- a 14-layer pipeline implemented in both Python and TypeScript
- a six-axis semantic weighting system
- multiple benchmark scripts and an adversarial prompt corpus
- a substantial HYDRA orchestration layer
- two different PQC representations: one liboqs-oriented wrapper and one demo/simplified lattice module that is not cryptographically sound as written

The remaining repos primarily provide conceptual prototypes, proposal/demo UI, and minimal scaffolding.

Key credibility and research risks identified in the review:
- the 14-layer pipeline exists in Python and TS implementations that do not fully agree on formulas and invariants
- null-space signatures are benchmarkable and useful, but they can inflate false positives when treated as a universal gate
- HYDRA is a real orchestration surface, but parts of the lattice governance story are closer to simulation than standards-grade PQC
- some public-facing benchmark claims need tighter reproducibility and canonical script/document links

---

## High-signal findings preserved from the review

### 1. Canonicality and reproducibility risk

The 14-layer pipeline exists in two main implementations:
- TypeScript kernel pipeline
- Python pipeline

The review notes that they do not fully agree on formulas and invariants, especially around the harmonic wall layer and some theorem statements. Until one implementation is declared canonical and the other is test-matched against it, strong claims remain packaging-fragile.

### 2. Null-space signatures are real but should not be oversold as a universal hard gate

The review correctly identifies null-space signatures as implemented and benchmarkable through features such as:
- null ratios
- energy
- pattern strings
- helix-related features

But it also notes a critical limitation already reflected in internal benchmark notes: null features can drive false positives up when used as a universal hard decision rule. The better positioning is:
- secondary classifier
- attribution feature
- structured-absence signal
- execution-risk modifier

### 3. HYDRA is substantial

HYDRA is not vapor. The review identifies a coherent orchestration surface built around:
- spine
- head
- switchboard / workflow orchestration
- FastAPI routes
- action governance / turnstile patterns

This should be treated as a product surface, not a side note.

### 4. PQC story needs precision

The review distinguishes two different realities:
- a credible `liboqs`-oriented direction in `pqc_core.py`
- a simplified demo-style `dual_lattice.py` that is not currently standards-grade crypto

This is materially important. Public copy should not blur:
- standards-backed wrapper direction
- demo/simulation governance math

### 5. Public benchmark claims need one canonical proof spine

The review notes that strong claims like `91/91 blocked, 0 false positives` require a single canonical proof path with:
- exact scripts
- commit hash
- corpus hash
- expected outputs
- honest scope notes

That aligns with the repo-side cleanup already started through:
- `docs/eval/README.md`
- `docs/eval/manifest.json`
- `scripts/eval/run_scbe_eval.ps1`

---

## Repository-by-repository notes preserved from the review

### SCBE-AETHERMOORE

Positioning and scope:
- README presents a 14-layer AI safety/governance system with SDKs, CLI, docs, and HYDRA operations content.

Canonical 14 layers inventory:
- `LAYER_INDEX.md` enumerates L1-L14 and points to implementation locations.

Core code reality identified by the review:
- `packages/kernel/src/pipeline14.ts` implements 14 steps with explicit state transforms and a bounded harmonic score at L12.
- `src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py` implements a similar pipeline with different details and theorem-helper commentary.

Six tongues:
- formalized in docs and implemented programmatically with multiple profiles and flux modifiers.

Hyperbolic / Poincare usage:
- present in harmonic / hyperbolic utilities.

Null-space benchmarks:
- implemented in benchmark scripts and verification docs.

Adversarial corpus and harness:
- `tests/adversarial/attack_corpus.py` defines the 91-attack suite and benign baseline set.
- `tests/adversarial/scbe_harness.py` currently contains a syntactic / stub tongue-coordinate lane that should be replaced or supplemented by a stronger semantic coordinate path.

HYDRA orchestration:
- spine, head, and API routes were identified as real, integrated components.

PQC primitives:
- `pqc_core.py` is the stronger standards-aligned direction.
- `dual_lattice.py` is demo/simplified and should be clearly labeled or renamed.

### scbe-security-gate

This repo reads as a security/math prototype and companion thought-space.

The review highlights:
- a hyperbolic-space trust model in `MULTI_AGENT_THREAT_MODEL.md`
- forward-secure ratcheting / anti-replay tests in `tests/test_entropic_quantum_system.py`
- a six-constructed-language system in `SIX_SACRED_TONGUES_CODEX.md`

Critical naming-collision note from the review:
- the six constructed-language family is not the same thing as the six numeric axes in SCBE-AETHERMOORE
- public naming should separate these concepts more clearly

### Entropicdefenseengineproposal

The review treats this as a UI/demo/pitch surface rather than proof of correctness.

Key note:
- any literal pass/fail numbers in the UI should be wired to live artifacts or labeled clearly as mock/simulated

### SCBE-QUANTUM-PROTO

Currently minimal scaffolding.

### AI-Generated-Agents

Currently minimal / placeholder public framing; needs a purpose statement and structure note.

---

## Literature mapping preserved from the review

The external review mapped SCBE constructs to recognizable literature lanes:
- hyperbolic embeddings / Poincare ball usage
- subspace anomaly and spectral signature analogs
- energy-based and quadratic attractor systems
- alpha/omega limit-set framing for trajectory analysis
- multi-view consensus / remainder signals
- FIPS 203 and FIPS 204 grounding for ML-KEM / ML-DSA

High-value takeaway:
- novelty should not be framed as `using hyperbolic geometry`
- novelty is better framed as:
  - interpretable multi-axis semantic projection
  - structured absence / null-space signatures
  - multi-profile disagreement / remainder signaling
  - execution gating and orchestrated downstream control

---

## Current experiment framing update

### Honest experimental report currently in scope

Reported result summary:
- Biblical probes: `14/60` = `23.3%`
- Software controls: `8/24` = `33.3%`
- Noise: `0/12` = `0.0%`

Interpretation:
1. The detector is real because noise stays at zero while real prompts score above zero.
2. Mild domain specificity exists because software prompts score higher than biblical probes.
3. The gap is not strong enough to support a Bible-specialization product story.
4. The model appears shallow on structural concept activation across both domains.

### Correct product framing from this result

The stronger commercial statement is:

`SCBE detects structured absence across multiple semantic channels to verify that required concepts are actually present, not just that banned keywords are absent.`

This should replace weaker or narrower framings such as:
- Bible-aware deep understanding
- covenant-specific mastery
- theology-specific detector claims

Better framing:
- multi-channel semantic constraint detection
- structured absence / null-space signatures
- required semantic channels
- useful for compliance, governance, safety, policy, domain-specific control, and execution gating

Biblical/covenantal probes should be treated as:
- a research case study
- an exploratory domain probe
- not the core public product claim

---

## Immediate implications for docs and product surfaces

### Lead with these
- HydraArmor integration path
- Null-space signatures / structured absence
- reproducible benchmark and eval pack
- architecture overview with one canonical source-of-truth statement

### Stop leading with these on first-contact pages
- Bible-specific framing
- mythology-heavy language in engineering entry points
- broad theorem/cosmology framing without direct artifacts
- crypto claims that blur standards-backed wrappers and demo modules

### Recommended public product sentence

`SCBE-AETHERMOORE is a runtime governance layer for AI agents that detects unsafe or incomplete reasoning using structured absence across semantic channels, session-aware scoring, and geometry-based containment.`

---

## Preserved file-to-component fix list from the review

### High-priority repo-level fixes
- Add a canonical architecture page and clearly declare the authoritative pipeline implementation.
- Add a canonical benchmark page with exact commands, corpus hash, commit hash, and expected outputs.
- Separate demo crypto modules from standards-oriented PQC wrappers in names and docs.
- Reduce naming collision between `Sacred Tongues` numeric axes and constructed-language/cipher families.
- Split product language from narrative/theory language on public surfaces.

### Specific fix themes preserved from the review
- `README.md`: include canonical architecture and reproducible benchmark status
- `LAYER_INDEX.md`: add canonical formulas and test anchors
- `packages/kernel/src/pipeline14.ts` and Python pipeline: reconcile numerically with shared fixture tests
- `tests/adversarial/scbe_harness.py`: separate lexical baseline from semantic/hyperbolic detector
- null-space benchmark scripts: make thresholds configurable and output ROC/threshold artifacts
- `hydra/spine.py`: treat governance as pluggable and separate demo lattice from PQC-backed lattice
- `src/crypto/dual_lattice.py`: rename or sharply qualify as demo/simulation if it remains non-standards-grade

---

## Suggested experiments preserved from the review

### Core evaluation matrix
Expand beyond the existing attack and tiny benign set into:
- Attack set `A`
- Large benign set `B`
- Hard-negative benign set `H`

Report:
- recall on `A`
- FPR on `B` and `H`
- AUROC / AUPRC if continuous scores exist
- calibration if trust/risk is probabilistic
- runtime and tail latency

### Ablation protocol
The review suggests a single matrix runner with toggles like:
- lexical on/off
- tongue mapping: stub / keyword / embedding
- hyperbolic on/off
- null features: off / attribution / soft gate
- remainder profiles: phi / moon / foam / all

### Noise and paraphrase robustness
Evaluate:
- homoglyph / whitespace perturbations
- paraphrases
- translation round-trips

### Cross-detector comparison discipline
If comparing against external detectors:
- match scope fairly
- label multilingual or jailbreak subsets clearly
- do not overclaim superiority outside the comparator’s stated scope

---

## Patent-framing notes preserved from the review

Not legal advice.

The review proposes stronger novelty framing around:
- interpretable low-dimensional semantic axes
- null-space signatures over those axes
- multi-profile disagreement / remainder signals
- execution gating / allow-quarantine-escalate-deny control
- orchestrator-level constrained execution modes

Important differentiation note:
- novelty is not `using hyperbolic geometry`
- novelty is the combined safety-control architecture built on interpretable axes, structured absence, disagreement, and gated downstream execution

---

## Internal synthesis note

This review substantially agrees with the current repo-side cleanup direction:
- the system is stronger than the presentation
- the core value is real
- the public surface needs compression and canonicality

The most important synthesis point is:
- the invention is the detector and governed execution stack
- not a Bible-specific detector
- not the broadest possible cosmology framing

The strongest near-term message is:
- `multi-channel semantic constraint detection via structured absence`

---

## Action lanes captured from this note

### Documentation and packaging
1. Keep one canonical architecture page and one canonical eval page.
2. Keep benchmark claims tied to reproducible artifacts only.
3. Move Bible/covenantal framing into research pages, not product entry points.

### Benchmarking
1. Finish the eval pack so it runs cleanly end-to-end on Windows.
2. Build a larger benign and hard-negative benign corpus.
3. Treat null-space as attribution / secondary risk signal unless a calibrated classifier proves otherwise.

### Architecture and code
1. Reconcile Python and TS pipeline formulas.
2. Separate demo lattice governance from real PQC-backed modules.
3. Tighten HYDRA governance interfaces and execution logging.

---

## Preservation note

This file is intended as a stable preserved note for:
- the supplied cross-repo review
- the current null-space framing update
- packaging and credibility decisions that follow from both

If this becomes canonical input to future work, create a linked shorter derivative document for public-facing use rather than editing this source note destructively.
