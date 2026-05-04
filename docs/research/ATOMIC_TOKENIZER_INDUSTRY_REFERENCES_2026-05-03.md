# Atomic Tokenizer And Chemical Reaction AI References - 2026-05-03

## Purpose

This note anchors the SCBE atomic-tokenizer and chemical-fusion ideas against current chemistry AI references so release, benchmark, and app-store packaging can describe the system without overclaiming.

## Local SCBE Anchors

| Surface | Role |
|---|---|
| `notes/theory/atomic-tokenizer-chemistry-unified.md` | Canonical draft for "one alphabet, many decoders": chemistry, mathematics, pipeline semantics, and governance read the same token stream through different projections. |
| `notes/theory/knowledge-graph-fill.md` | Epistemic-status map. Lists STISA plus Atomic Tokenization as implemented feature engineering: 256-row lookup table per tongue, 8-dimensional atomic feature vector, six-channel trit vector, and chemical fusion. |
| `python/scbe/atomic_tokenization.py` | Runtime finite semantic lattice: semantic elements carry symbol, Z, group, period, valence, electronegativity, and witness-stable state. |
| `python/scbe/chemical_fusion.py` | Runtime reconstruction vote with channel weights, edge tension, coherence penalty, and valence pressure. |
| `config/model_training/coding-agent-qwen-atomic-workflow-stage6.json` | Coding-agent training profile that preserves code, semantic overlay, structural chemistry frame, and resource-aware workflow composition. |
| `config/model_training/chemistry-qwen-primary.json` | Chemistry-only profile for reaction classes, atom conservation, product prediction, stability, and packet layouts. |
| `config/model_training/aligned-foundations-qwen-primary.json` | Cross-lane profile aligning mathematics, English, Sacred Tongues, binary transport, chemistry packets, and coding primaries. |

## Industry Parallels

| Reference | What It Shows | Why It Matters For SCBE |
|---|---|---|
| Molecular Transformer, IBM Research / ACS Central Science, 2019 | Reaction prediction can be framed as sequence-to-sequence translation between SMILES reactant/reagent strings and product strings, with strong benchmark accuracy and uncertainty estimates. | Supports the "chemistry as language" premise, but SCBE should not claim novelty there. |
| IBM enzymatic Molecular Transformer, 2021 | Reaction SMILES tokens can be combined with natural-language enzyme descriptions so context changes predicted products. | Closest external parallel to SCBE context tokens such as `hv`, `pH=7`, or governance-state tags changing interpretation without changing the alphabet. |
| BARTReact / SELFIES, Franklin Open, 2024 | SELFIES-based reaction modeling uses a molecular representation that constrains outputs toward chemically valid molecules. | Supports the bijective/constrained-tokenizer direction: representation can reduce invalid emissions before model reasoning. |
| ChemCrow, arXiv 2023 | LLM chemistry agents become more useful when connected to expert tools for synthesis, drug discovery, and materials design. | Supports SCBE's agent harness direction: domain tools and gates matter more than a raw chat model. |
| Review of LLMs and Autonomous Agents in Chemistry, arXiv 2024 | Chemistry agents need better data integration, interpretability, multimodal/tool collaboration, and standard benchmarks. | Supports the release roadmap: benchmark the harness, expose provenance, and keep interpretable packet/gate outputs. |

## What SCBE Should Claim

SCBE should frame the contribution as:

> Chemistry-style token invariants for governed agentic coding and AI-to-AI coordination.

Do not claim "invented chemical AI" or "invented reaction prediction." Those are established fields.

The stronger claim is that SCBE maps chemistry-inspired invariants onto an agent harness:

| Chemistry Term | SCBE Harness Meaning |
|---|---|
| atom | token, provider, action primitive, or workflow card |
| valence | branching capacity, tool handoff capacity, or maximum safe outgoing bonds |
| electronegativity | risk pull, conflict pressure, or authority friction |
| bond | allowed handoff edge with cost and required signal |
| molecule | stable pair or triad formation |
| reaction | task workflow through planner, executor, verifier, and merge gate |
| catalyst | stronger judge, verifier, benchmark, or deterministic tool |
| residue | compact changelog, release note, or context digest retained after the temporary work file is deleted |
| conservation | bijective state preservation, hashes, atom counts, or packet round-trip checks |
| stability | tests, route gates, packet integrity, and release-readiness status |

## Benchmark Hypothesis

The testable hypothesis for the agent harness is:

> A compound-agent scheduler that chooses pairs and triads from valence, bond cost, signal requirement, provider availability, and residue digest will outperform random or fixed provider routing on coding-agent benchmark tasks.

Minimum viable benchmark:

1. Build model atoms from the current provider matrix.
2. Build allowed bonds from route-switch cost and required signal.
3. Form molecules as pairs and triads.
4. Run the same task set through:
   - fixed single model,
   - random pair,
   - fixed pair,
   - chemically selected pair or triad.
5. Score:
   - task pass rate,
   - tokens sent,
   - context bytes retained,
   - test pass rate,
   - invalid handoff count,
   - release-note or changelog accuracy.

## Packaging Implication

For public release and app-store packaging, describe this as an operator-facing coordination engine:

- visible launch surface: Vercel bridge and GitHub Pages;
- installable package: `scbe-aethermoore` npm/PyPI and `geoseal` command-line interface;
- app target: AetherBrowse package under `kindle-app/`;
- benchmark target: agentic coding harness with pair/triad coordination and deterministic handoff packets.

## Source Links

- IBM Molecular Transformer: https://researcher.ibm.com/publications/molecular-transformer-a-model-for-uncertainty-calibrated-chemical-reaction-prediction
- IBM enzymatic Molecular Transformer: https://research.ibm.com/publications/predicting-enzymatic-reactions-with-a-molecular-transformer
- BARTReact / SELFIES: https://www.sciencedirect.com/science/article/pii/S2773186324000367
- ChemCrow: https://arxiv.org/abs/2304.05376
- Review of Large Language Models and Autonomous Agents in Chemistry: https://arxiv.org/abs/2407.01603
