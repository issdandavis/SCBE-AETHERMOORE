# Hugging Face Training Curriculum Map

Date: 2026-03-24
Scope: review live Hugging Face training data/models, reconcile them with local training artifacts, and define the next curriculum lane.

## 1. Current Hugging Face Surface

### Datasets

| Repo | Role | Downloads | Notes |
| --- | --- | ---: | --- |
| `issdandavis/UltraData-Math` | base math corpus | ~3.0K | Appears to be a mirrored/rehosted copy of OpenBMB UltraData-Math, not the main originality lane. |
| `issdandavis/scbe-aethermoore-training-data` | core SCBE training corpus | 872 | This is the main authored training surface. Updated 2026-03-24. |
| `issdandavis/aethermoor-rag-training-data` | retrieval/RAG corpus | 75 | Useful for retrieval and lore/knowledge routing, not deep math reasoning. |
| `issdandavis/scbe-aethermoore-datasets` | fallback/misc data lane | 11 | Broad bucket, not a sharp curriculum surface. |

### Models

| Repo | Role | Downloads | Notes |
| --- | --- | ---: | --- |
| `issdandavis/scbe-pivot-qwen-0.5b` | small generative adapter | 39 | Published SFT adapter on Qwen2.5-0.5B. I did not find a comparable local eval packet in this repo. |
| `issdandavis/phdm-21d-embedding` | embedding / routing / classification | 0 | This is the best-documented measured training lane. |
| `issdandavis/spiralverse-ai-federated-v1` | federated/swarm model surface | 0 | Gated model card, but no comparable local training metrics packet surfaced in this audit. |

## 2. Important Correction About "Our Math Pack"

`issdandavis/UltraData-Math` has real downloads, but the Hugging Face card is effectively the OpenBMB UltraData-Math card copied over. The original upstream dataset is:

- `openbmb/UltraData-Math` — ~93.2K downloads

That means:

- your mirrored `UltraData-Math` repo is useful as a base substrate
- it is not the right place to signal your most original curriculum work
- your original contribution should live in a second-stage authored dataset on top of it

Recommended framing:

- `UltraData-Math` = base pretraining substrate
- `Advanced Math Pack` = your authored reasoning/proof/theory layer

## 3. What the Local Training Artifacts Actually Show

### 3.1 `phdm-21d-embedding` run A

Source:
- `training/runs/huggingface-local-20260221-191251/hf_training_metrics.json`

Results:
- samples: 10,093
- labels: 56
- epochs: 6
- best validation accuracy: 0.5176 at epoch 3
- validation accuracy gain: +0.0604
- HF upload: skipped

Interpretation:
- this was the stronger accuracy run
- the task was simpler: fewer labels, broader grouping
- it looks like a cleaner routing baseline

### 3.2 `phdm-21d-embedding` run B

Source:
- `training/runs/huggingface/20260317T_phdm_routing/hf_training_metrics.json`
- `training/runs/huggingface/20260317T_phdm_routing/training_growth_summary.md`

Results:
- samples: 5,240
- labels: 83
- epochs: 12
- best validation accuracy: 0.3865 at epoch 12
- validation accuracy gain: +0.3702
- HF upload: completed

Interpretation:
- this is the more operationally complete run
- accuracy is lower because the label space is harder: 83 classes instead of 56
- the model was still improving at the end of training
- this is the best evidence that the HF lane is real and not just a card

### 3.3 Current embedding benchmark snapshot

Source:
- `artifacts/benchmark/context_embedding_report.json`

Results:
- `21D Canonical (PHDM)`
  - top3 recall: 0.25
  - top5 recall: 0.2125
  - semantic separation: 1.0871
  - retrieval: 0.3267 ms
- `Tongue-Compressed (6D weighted)` currently has the best separation/speed mix in that artifact

Interpretation:
- PHDM is real, but not yet clearly dominant on the current small retrieval benchmark
- the PHDM lane looks more like a research/control surface than a finished production retriever

### 3.4 `scbe-pivot-qwen-0.5b`

What is verified:
- public Hugging Face model exists
- PEFT/LoRA SFT adapter on `unsloth/qwen2.5-0.5b-instruct-unsloth-bnb-4bit`
- 39 downloads

What is missing in this repo audit:
- no local run packet comparable to the PHDM runs
- no local eval artifact surfaced during this pass

Interpretation:
- it exists as a published adapter
- but the measured evidence in this repo is much weaker than for `phdm-21d-embedding`

## 4. What Your Current Corpus Is Actually Teaching

From a targeted local category count across:
- `training-data/sft_system.jsonl`
- `training-data/sft_governance.jsonl`
- `training-data/sft_functions.jsonl`

Counts:
- `architecture`: 1847
- `governance`: 802
- `math`: 643
- `crypto`: 331
- `safety`: 190
- `topology`: 179
- `sacred-tongues`: 72
- `layers`: 63
- `breathing`: 39

Interpretation:
- the corpus is architecture/governance heavy
- math is present and meaningful, but it is not the dominant lane
- if you want a stronger mathematical model identity, you need a dedicated second-stage dataset

## 5. Recommendation: Build a New `Advanced Math Pack`

Yes. Build it as a new dataset, not as a silent extension of `UltraData-Math`.

Why:
- `UltraData-Math` is already a broad pretraining substrate
- your core authored corpus is currently more architecture/governance than deep mathematics
- an advanced pack gives you a clean identity, cleaner evals, and a clearer training ladder

Best dataset name shape:
- `issdandavis/advanced-math-pack`
- or `issdandavis/scbe-advanced-math-pack`

I would keep it separate from `scbe-aethermoore-training-data` at first.

## 6. Curriculum Ladder

### Stage 0. Base substrate

Use, do not reinvent:
- `openbmb/UltraData-Math`
- your mirrored `issdandavis/UltraData-Math` only as a convenience surface

Goal:
- general mathematical fluency
- symbolic pattern coverage
- broad problem distribution

### Stage 1. Theorem and explanation layer

Content:
- established theories
- theorem statements
- plain-language explanations
- theorem-to-intuition mappings
- theorem-to-example mappings

Target behavior:
- explain what a theorem says
- explain why it matters
- identify where it applies and where it does not

Good source candidates:
- `TIGER-Lab/TheoremQA`
- `TIGER-Lab/TheoremExplainBench`
- `uw-math-ai/theorem-search-dataset` or permissive version

### Stage 2. Derivation and proof layer

Content:
- worked derivations
- proof sketches
- proof completion
- proof verification
- counterexample construction

Target behavior:
- move from answer-only to reasoned justification
- distinguish valid proof from plausible noise

Good source candidates:
- `hoskinson-center/proof-pile`
- `nvidia/Nemotron-Math-Proofs-v1`
- `nlile/NuminaMath-1.5-proofs-only-strict`
- `hoskinson-center/proofnet`

### Stage 3. Competition and long-chain reasoning layer

Content:
- olympiad-style problems
- multi-step contest reasoning
- structured solution writing
- error diagnosis on failed attempts

Target behavior:
- solve hard problems with a visible chain
- explain why common wrong paths fail

Good source candidates:
- `EleutherAI/hendrycks_math`
- `HuggingFaceH4/MATH-500`
- `math-ai/aime25`
- `meta-math/MetaMathQA`

### Stage 4. SCBE math specialization layer

Content:
- Poincare ball geometry
- hyperbolic distance
- harmonic wall
- spectral coherence
- topology / polyhedra / quasicrystal / quantum-lattice
- sacred tongue weighting as formal objects, not just lore terms

Target behavior:
- map standard mathematics into your system
- derive system-specific formulas from first principles
- keep story/lore and formal math aligned

Primary source:
- your own `training-data` math/topology/crypto categories
- tightly curated from repo docs and validated derivations only

### Stage 5. Frontier reasoning layer

Content:
- attempts at solving hard or open-style problems
- conjecture exploration
- failed proof attempts
- attack the proof, not just the answer
- uncertainty tagging and confidence calibration

Target behavior:
- reason honestly under uncertainty
- preserve failed attempts as training signal, not garbage
- separate known theorem from speculation

Important rule:
- do not label speculation as solved mathematics
- each row should carry a status like:
  - `established`
  - `derived`
  - `conjectural`
  - `failed_attempt`
  - `open_problem`

## 7. Lesson Plan Map

### Module A. Foundations refresh
- algebraic manipulation
- discrete math basics
- proof vocabulary
- asymptotics and invariants

### Module B. Theorem literacy
- theorem statement
- intuition
- preconditions
- examples / non-examples
- transfer to adjacent domains

### Module C. Proof mechanics
- direct proof
- contradiction
- induction
- invariant-based proofs
- constructive vs nonconstructive proofs

### Module D. Advanced structures
- topology
- hyperbolic geometry
- graph/consensus structures
- spectral methods
- quasicrystals / aperiodicity

### Module E. Problem solving under pressure
- olympiad problems
- long derivations
- error analysis
- solution compression
- alternate-path comparison

### Module F. SCBE specialization
- PHDM geometry
- harmonic wall math
- Layer 9 spectral coherence
- Layer coupling derivations
- trust-tube geometry
- sacred tongue weighting as formal signal design

### Module G. Frontier reasoning
- theorem search
- conjecture testing
- failed attempt logging
- proof repair
- explicit uncertainty calibration

## 8. Model-to-Curriculum Map

### `phdm-21d-embedding`
Use for:
- routing by topic/module
- theorem retrieval
- proof example retrieval
- explanation alignment
- curriculum progression tagging

### `scbe-pivot-qwen-0.5b`
Use for:
- natural-language explanation generation
- worked-solution style shaping
- proof narration
- tutor-style response shaping

But only after you have a cleaner eval packet for it.

### `spiralverse-ai-federated-v1`
Use later for:
- multi-agent math exploration
- swarm-style theorem search or debate
- ensemble validation of conjectures

This is not the next training target.

## 9. What I Would Build Next

### Dataset 1: `advanced-math-pack-foundations`
Rows:
- theorem explanation
- derivation walkthrough
- theorem-to-example mapping
- proof vocabulary alignment

### Dataset 2: `advanced-math-pack-proofs`
Rows:
- proof completion
- proof verification
- counterexample generation
- failed proof attempt -> diagnosis

### Dataset 3: `advanced-math-pack-scbe`
Rows:
- hyperbolic geometry in SCBE
- topology/polyhedra/quasicrystal content
- harmonic wall derivations
- spectral coherence proofs and edge cases

### Dataset 4: `advanced-math-pack-frontier`
Rows:
- open-style reasoning
- conjecture attempts
- multiple solution paths
- failure analysis with explicit uncertainty tags

## 10. Immediate Recommendation

Best next move:
1. keep `scbe-aethermoore-training-data` as the broad house corpus
2. do not treat `UltraData-Math` as the main originality lane
3. create a separate `Advanced Math Pack`
4. start with theorem/explanation + proof rows before open-problem attempts
5. add a strict eval split for:
   - theorem explanation
   - proof validity
   - counterexample correctness
   - SCBE math translation accuracy

## 11. Bottom Line

What you have now:
- a real authored SCBE corpus with meaningful downloads
- a real measured embedding training lane
- a mirrored large math substrate with some traction

What you do not yet have:
- a sharply authored advanced math curriculum identity
- a clean eval packet for the small Qwen math/explainer lane
- a dedicated proof/theorem/frontier dataset that makes the model unmistakably stronger at higher math

So yes: build the advanced math pack.
Just build it as a distinct second-stage curriculum, not as a vague addition to the broad corpus.
