# Research Ingestion Rights Operating Model

Last updated: 2026-04-09  
Status: operational guide for source registration, rights classification, and training-route decisions

## Purpose

This guide defines how SCBE-AETHERMOORE should classify government, research, documentation, and internal note sources before they enter:

- the Obsidian-first local vault flow,
- retrieval and citation systems,
- internal training lanes,
- or public/open-source training datasets.

This model exists to preserve value from lawful access without collapsing all sources into one training bucket.

## Core Rule

Ingest broadly. Reuse selectively. Publish carefully.

Authorized access is not the same thing as unrestricted redistribution.

## Canonical Inputs for This Lane

- `config/research/source_registry.json`
- `schemas/source_registry_record.schema.json`
- `schemas/ingestion_rights_record.schema.json`
- `scripts/classify_ingestion_rights.py`
- `docs/specs/DARPA_PREP_PROPOSAL_INTELLIGENCE_SPEC.md`

## Local Vault Rule

The current Obsidian vault is the repo-local `notes/` tree.

Use local notes as:

- exploratory memory,
- internal context,
- and promotion candidates.

Do not treat them as public-training truth by default.

## Required Source Dimensions

Every source must be registered with:

- `channel`
- `authority_class`
- `access_level`
- `redistribution_status`
- `training_status`

These fields decide whether the source can flow into:

- internal RAG,
- internal training,
- public training,
- metadata extraction only,
- or citation-only handling.

## Rights and Training Status Meanings

### Access Level

- `public` — accessible without private account standing
- `authorized_internal` — accessible because you are the lawful/authorized user
- `restricted` — sensitive or blocked from routine ingestion

### Redistribution Status

- `publishable` — okay to reference or repackage publicly within normal citation and licensing limits
- `internal_only` — store and use internally only
- `unclear` — needs review before external use
- `blocked` — do not redistribute

### Training Status

- `allowed_public_training` — can enter public/open-source training lanes
- `internal_training_only` — can enter internal fine-tuning or private memory systems only
- `retrieval_only` — keep for retrieval, scoring, citation, and metadata extraction only
- `blocked` — do not use for training

## Government and Research Examples

### Public government/research sources

Usually safe for citation, metadata extraction, and often public-training inclusion:

- SAM.gov public API results
- DARPA public program pages
- arXiv paper metadata and public papers
- public BAA PDFs and public agency guidance

### Authorized internal sources

Usually internal-only or retrieval-only:

- DARPA submission portal pages
- SAM.gov account-only registration views
- your own submission workflows and opportunity dashboards
- internal proposal drafts and cost notes

### Internal notes and operator files

Usually internal-training-only or retrieval-only:

- `docs/operations/DARPA_SAM_GOV_CONTACTS_AND_PROPOSAL_STATUS.md`
- `docs/legal/SAM_GOV_REGISTRATION_RECORD.md`
- proposal planning notes
- vault-only capture notes

## Operating Pattern

1. Register the source in `config/research/source_registry.json`.
2. Classify each captured artifact with `scripts/classify_ingestion_rights.py`.
3. Route the resulting rights record into one of these lanes:
   - internal RAG
   - internal training
   - public/open-source training
   - retrieval/metadata only
4. Promote only after local verification.

## Promotion Guard

Before an artifact is allowed into a public/open-source dataset:

- the source must be registered as `publishable`
- the training status must be `allowed_public_training`
- the artifact must not come from an authorized portal dump or internal proposal draft
- reviewer notes should record why promotion is allowed

## Example Commands

List registered sources:

```powershell
python .\scripts\classify_ingestion_rights.py --list-sources
```

Classify a SAM.gov API capture:

```powershell
python .\scripts\classify_ingestion_rights.py `
  --source-id sam_gov_public_api `
  --artifact-ref "artifacts/sam_gov/darpa_query_2026-04-09.json" `
  --artifact-type api_result `
  --reviewed-by issdandavis
```

Classify a DARPA portal text dump:

```powershell
python .\scripts\classify_ingestion_rights.py `
  --source-id darpa_submission_portal `
  --artifact-ref "notes/darpa/open_solicitations_2026-04-09.md" `
  --artifact-type portal_dump `
  --reviewed-by issdandavis
```

## Relationship to DARPA Prep

This rights model does not replace the DARPA Prep product schema.

- `DARPA Prep` answers: what is the opportunity and how do we score readiness?
- `Research Ingestion Rights` answers: are we allowed to train on or publish this source, and under what handling rules?

Use both together.
