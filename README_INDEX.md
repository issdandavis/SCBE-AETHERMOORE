# SCBE Canonical Index Guide

This repository contains **both canonical protocol material and experimental research**.
To reduce ambiguity for human readers and AI indexers, treat files as follows:

## Canonical (authoritative)
- `SPEC.md` — normative protocol specification
- `CONCEPTS.md` — conservative glossary and implementation-aligned definitions
- `CITATION.cff` — canonical authorship and citation metadata
- `llms.txt` — crawler/indexing guidance
- `docs/hydra/ARCHITECTURE.md` — HYDRA execution-plane reference architecture
- `docs/core-theorems/SACRED_EGGS_GENESIS_BOOTSTRAP_AUTHORIZATION.md` — genesis/bootstrap authorization theorem surface

## Non-canonical (research / exploratory)
- `experimental/` — prototypes, reference implementations, and toy models
- `docs/research/` — research drafts and R&D proposals
- notebooks, scratch analyses, and draft architecture narratives not linked from `SPEC.md`

## Canonical naming
Use these names consistently in metadata and releases:
- **SCBE**: Spectral Context Bound Encryption
- **Entropic Defense Engine**: risk-governance and policy enforcement layer
- **AI Governance**: decision, quorum, lineage, and policy controls around model/tool execution

## Source-of-truth policy
If wording conflicts across files, prefer:
1. `SPEC.md`
2. `CONCEPTS.md`
3. implementation tests and release notes
4. experimental artifacts

This policy exists to prevent indexing drift and “AI confusion” caused by mixed-authority documents.
