# Synthetic Data Privacy Blueprint

## Goal

Turn operational artifacts and conversations into synthetic training data without leaking user-identifying information, while preserving enough structure to support high-quality model training and later audit.

## Non-Negotiable Distinction

If the data can be decoded with a key, it is not de-identified. It is pseudonymized or tokenized.

That distinction matters:

- De-identified data is meant to break the link to a person.
- Pseudonymized data keeps the link, but moves it behind a protected key or token vault.
- For sensitive workflows, generate synthetic data from the pseudonymized layer and publish only the synthetic outputs.

## Proposed Architecture

### 1. Ingest and classify

- Label every source item as `public`, `internal`, `sensitive`, or `restricted`.
- Separate content from identifiers at ingest time.
- Store provenance, timestamps, and source hashes for every transformation.

### 2. Replace sensitive entities before generation

- Replace names, emails, phones, account ids, addresses, and other identifiers with deterministic codenames.
- Use a token vault for reversible lookup.
- Use strong encryption for the vault and keep keys separate from the content store.
- Use format-preserving encryption only where preserving structure is necessary for downstream tooling.

### 3. Generate synthetic conversations from the protected layer

- Use the pseudonymized corpus as the seed layer.
- Expand it with instruction bootstrapping and conversation synthesis.
- Keep generation prompts focused on role, task, constraints, and domain facts rather than user identity.
- Use critique or feedback loops to increase factuality and reduce extractive copying.

### 4. Audit before training

- Run exact-substring and n-gram leakage checks against the source corpus.
- Run nearest-neighbor or embedding leakage checks against the source corpus.
- Run canary prompts for memorization and identity reconstruction.
- Block export if the synthetic output is too extractive or if identifiers survive normalization.

### 5. Publish only audited artifacts

- Keep the token vault private.
- Publish synthetic conversations, method registries, and training manifests.
- Version every run so the training data lineage is recoverable.

## DNA Replication Analogy That Actually Maps

The useful biological analogy is not "biology is magical." It is "biology scales by templating, proofreading, and checkpoints."

- Origin points: shard the corpus into well-defined starting domains.
- Template copying: generate from structured protected records, not from raw uncontrolled memory.
- Leading and lagging strands: support both fast-path generation and slower repair/refinement passes.
- Proofreading: check every generation pass for leakage and inconsistency.
- Mismatch repair: repair or discard rows that fail privacy or factuality checks.
- Checkpoints: do not advance to publish or delete until the audit gates pass.

That is the right micro-to-macro mapping: chemistry to replication machinery is like bytes to transforms; cells to tissues is like records to datasets; checkpoints keep local errors from becoming system-wide failure.

## Immediate Repo Follow-Ups

1. Add a `token-vault` layer for deterministic codename assignment and reversible lookup.
2. Add a `synthetic-conversation-builder` that reads protected rows and emits multi-turn training conversations.
3. Add a `privacy-audit` pass with exact-match, near-match, and identifier-recovery checks.
4. Push only audited synthetic datasets and run manifests to Hugging Face.

## Recommended Policy

- Never train directly on raw sensitive conversations.
- Never let reversible keys live in the same store as exported training rows.
- Never delete originals because a single cloud copy exists.
- Prefer two independently verified destinations before destructive cleanup.

## Sources

- HHS OCR de-identification guidance:
  https://www.hhs.gov/sites/default/files/ocr/privacy/hipaa/understanding/coveredentities/De-identification/hhs_deid_guidance.pdf
- HHS minimum necessary guidance:
  https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/minimum-necessary-requirement/index.html
- NIST SP 800-38G Rev. 1 (2nd Public Draft), format-preserving encryption:
  https://csrc.nist.gov/pubs/sp/800/38/g/r1/2pd
- Self-Instruct (arXiv 2212.10560):
  https://doi.org/10.48550/arXiv.2212.10560
- PATE framework (arXiv 1802.08908):
  https://arxiv.org/abs/1802.08908
- SynDial synthetic clinical dialogue generation (arXiv 2408.06285):
  https://arxiv.org/abs/2408.06285
- DNA replication mechanisms:
  https://www.ncbi.nlm.nih.gov/books/NBK26850/
- DNA proofreading and repair overview:
  https://www.ncbi.nlm.nih.gov/books/NBK9940/
