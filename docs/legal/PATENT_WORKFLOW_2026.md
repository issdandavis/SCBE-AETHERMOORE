# Patent Workflow 2026

Status: internal workflow for SCBE patent preparation. Not legal advice.

## Goal

Prepare the SCBE-AETHERMOORE non-provisional utility patent packet with the
same discipline used for book production:

- one canonical working folder,
- clear draft stages,
- spelling/style cleanup,
- source-backed claim support,
- attorney handoff questions,
- filing-readiness checks.

## Official Sources To Use

Use official USPTO pages as the control source before relying on blogs or AI
summaries:

- Nonprovisional utility application guide:
  `https://www.uspto.gov/patents/basics/apply/utility-patent`
- Patent Center:
  `https://patentcenter.uspto.gov`
- DOCX filing guidance:
  `https://www.uspto.gov/patents/docx`
- USPTO fee schedule:
  `https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule`
- USPTO forms:
  `https://www.uspto.gov/patents/apply/forms`
- Patent Public Search:
  `https://ppubs.uspto.gov/pubwebapp/`
- Inventors Assistance Center:
  `https://www.uspto.gov/learning-and-resources/support-centers/inventors-assistance-center-iac`
- Patent and Trademark Resource Centers:
  `https://www.uspto.gov/learning-and-resources/support-centers/patent-and-trademark-resource-centers`

## Canonical Repo Files

Working packet:

- `docs/legal/SCBE_NONPROVISIONAL_WORKING_PACKET_2026-05-28.md`

Existing source material:

- `docs/PATENT_DETAILED_DESCRIPTION.md`
- `docs/PATENT_CLAIMS_COVERAGE.md`
- `docs/SCBE_PATENT_PORTFOLIO.md`
- `docs/business/PATENT_FIGURES.txt`

Implementation anchors:

- `src/symphonic_cipher/scbe_aethermoore/organic_hyperbolic.py`
- `src/symphonic_cipher/scbe_aethermoore/layers_9_12.py`
- `src/symphonic_cipher/scbe_aethermoore/layer_13.py`
- `src/governance/runtime_gate.py`
- `src/governance/bijective_tamper.py`
- `src/governance/identifier_canonicality.py`
- `src/tokenizer/ss1.ts`
- `packages/kernel/src/hyperbolic.ts`
- `packages/kernel/src/languesMetric.ts`
- `src/agentic/quarantine_lock.py`

## Required Filing Parts

A non-provisional utility application should be prepared as a coordinated packet:

1. Application data sheet.
2. Specification.
3. Claims.
4. Abstract.
5. Drawings, if needed to understand claimed subject matter.
6. Inventor oath/declaration.
7. Fee payment.
8. Micro entity certification, if applicable.

The USPTO utility guide states that a nonprovisional utility application must
include a specification with description and at least one claim, drawings when
necessary, an oath or declaration, and required filing/search/examination fees.

## Stage Workflow

### Stage 0 - Evidence Freeze

Purpose: preserve what existed before rewriting.

Actions:

- Export the filed provisional packet and receipt from Patent Center.
- Store a local read-only copy outside generated folders.
- Record the provisional application number, filing date, title, and inventor.
- Record repo commit hashes for code evidence being cited.
- Do not rely on memory for what the provisional contains; inspect the actual
  filed document.

Output:

- `docs/legal/provisional_inventory_YYYY-MM-DD.md`

### Stage 1 - Invention Boundary

Purpose: separate core invention from later improvements.

Actions:

- Identify which claim families are fully disclosed in the provisional.
- Mark newer items as one of:
  - supported by provisional,
  - likely continuation material,
  - likely CIP/new-matter material,
  - product-only detail not worth claiming now.

Output:

- Updated support table in the working packet.

### Stage 2 - Claim Drafting

Purpose: build claim sets counsel can refine.

Preferred first filing shape:

- 3 independent claims maximum.
- 20 total claims maximum.
- No multiple dependent claims unless counsel wants them.

Recommended independent claims:

- Method claim: hyperbolic governance gate.
- System claim: runtime enforcement architecture.
- Computer-readable-medium claim: tamper-aware governance.

Every claim element must have a support citation:

- specification section,
- figure number if applicable,
- code file and line where implemented.

Output:

- `docs/legal/claims_draft_vN.md`
- `docs/legal/claim_support_matrix_vN.md`

### Stage 3 - Specification Cleanup

Purpose: turn the detailed description into filing-ready language.

Rules:

- Use plain technical terms before SCBE coined terms.
- Keep coined terms in definitions and examples.
- Avoid unsupported absolutes such as "impossible," "cannot ever," or
  "military-grade" unless counsel specifically approves.
- Say "in some embodiments" when describing optional surfaces.
- Keep formulas consistent across claims, spec, figures, and code.

Output:

- `docs/legal/specification_draft_vN.md`

### Stage 4 - Drawing Packet

Purpose: make every figure support claim language.

Minimum figure set:

- Fourteen-layer pipeline.
- Hyperbolic embedding and trusted region.
- Harmonic wall cost curve.
- Semantic weighting axes.
- Runtime decision gate.
- Bijective tamper/canonicality flow.
- Agent bus/API/CLI deployment architecture.
- Quarantine containment flow.

Output:

- `docs/legal/figure_list_vN.md`
- formal drawings prepared from `docs/business/PATENT_FIGURES.txt`

### Stage 5 - Prior Art Search

Purpose: find what an examiner may cite before the examiner does.

Search tools:

- USPTO Patent Public Search.
- Google Patents.
- Lens.org.
- Semantic Scholar / arXiv for non-patent literature.

Search themes:

- hyperbolic access control,
- hyperbolic anomaly detection,
- Poincare embeddings for cybersecurity,
- AI prompt injection firewall,
- agent governance runtime,
- semantic authorization,
- cryptographic semantic encoding,
- Unicode canonicalization tamper detection,
- LLM tool-use quarantine or containment.

Output:

- `docs/legal/prior_art_search_log_vN.md`

### Stage 6 - Filing Readiness Review

Purpose: final check before Patent Center.

Checklist:

- Claims count reviewed.
- Independent claim count reviewed.
- Drawings referenced by spec.
- Each claimed feature appears in spec.
- No new matter added accidentally after final priority check.
- Abstract under normal USPTO expectations.
- Application data sheet complete.
- Oath/declaration ready.
- Micro entity form ready.
- DOCX accepted by Patent Center validation.
- Fees confirmed on current USPTO fee schedule.

Output:

- `docs/legal/filing_readiness_checklist_YYYY-MM-DD.md`

## Language Cleanup Rules

Use the spelling/style sheet:

- `docs/legal/PATENT_STYLE_SHEET_2026.md`

Before attorney handoff, run one pass for:

- spelling,
- consistent capitalization,
- formula consistency,
- no lore-only terms in claims,
- no unsupported marketing phrases,
- code/support citations attached to every important mechanism.

## What We Should Not Do

- Do not file claims that the provisional does not support without flagging
  priority risk.
- Do not treat AI-generated legal text as final legal advice.
- Do not let product roadmap language enter claims unless it is implemented or
  fully described.
- Do not pay avoidable USPTO surcharges caused by paper filing, non-DOCX filing,
  excess independent claims, or excess total claims unless counsel approves.
