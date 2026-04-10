# DARPA Prep Proposal Intelligence Spec

## Purpose

DARPA Prep is a source-grounded proposal intelligence system for federal R&D opportunities. The product is not a generic chat assistant. It ingests official opportunity materials, normalizes them into structured records, maps proposal drafts against explicit requirements, and returns citation-backed readiness diagnostics.

The primary users are proposers rather than agencies:

- startups pursuing DARPA, SBIR, STTR, NSF, DOE, or DIU opportunities
- university labs preparing research submissions
- defense-tech consultants supporting proposal development
- small contractors moving into federal R&D lanes

## Product Boundaries

The system must not:

- invent compliance requirements
- infer deadlines without citing an official source
- claim public access to proprietary winning proposals
- present unsupported legal, contracting, or registration advice as fact

The system must:

- preserve provenance for every extracted requirement
- distinguish solicitation types and submission paths
- expose confidence and unresolved ambiguity
- require human review before final submission use

## Canonical Inputs

The ingestion layer must distinguish source classes instead of collapsing them into one corpus:

- `solicitation` - BAA, RFP, NOFO, OA, or opportunity notice text
- `amendment` - official modifications or corrections to a solicitation
- `award_notice` - public award metadata or summaries
- `agency_guidance` - official proposer instructions, FAQs, templates, or registration guidance
- `public_proposal_artifact` - public white papers, abstracts, example structures, or proposer-facing templates
- `user_capability_data` - lab profile, prior work, staffing, past performance, teaming data
- `proposal_draft` - user-uploaded proposal sections, white papers, slides, budgets, and attachments

## Core Entities

### Opportunity

An `opportunity` record represents one federal R&D opportunity in normalized form.

Required fields:

- `opportunity_id`
- `source_system` (`DARPA`, `SAM.gov`, `Grants.gov`, `agency_portal`)
- `instrument_type` (`contract`, `grant`, `cooperative_agreement`, `other_transaction`, `unknown`)
- `title`
- `agency`
- `solicitation_number`
- `submission_path`
- `deadline`
- `citations`

### Requirement

A `requirement` is a proposal-relevant obligation or evaluation target extracted from a solicitation or guidance source.

Required fields:

- `requirement_id`
- `opportunity_id`
- `category` (`eligibility`, `format`, `technical`, `evaluation`, `registration`, `budget`, `security`, `export_control`, `submission`)
- `priority` (`critical`, `high`, `medium`, `low`)
- `text`
- `source_section`
- `citations`

### Proposal Section

A `proposal_section` is a user-provided draft unit mapped against one or more requirements.

Required fields:

- `section_id`
- `proposal_id`
- `title`
- `content_excerpt`
- `mapped_requirement_ids`
- `citation_links`

### Compliance Item

A `compliance_item` expresses whether a requirement is satisfied, unsupported, weakly addressed, contradicted, or not yet addressed.

Required fields:

- `requirement_id`
- `proposal_id`
- `status` (`addressed`, `weak`, `missing`, `contradicted`, `not_applicable`)
- `evidence_section_ids`
- `confidence`
- `review_required`

### Readiness Score

A `readiness_score` summarizes proposal state without hiding why the score exists.

Dimensions:

- `technical_fit`
- `completeness`
- `compliance`
- `transition_alignment`
- `teaming_readiness`
- `submission_readiness`
- `overall`

Each score must include:

- numeric value between `0.0` and `1.0`
- explanation text
- citations to the requirements or draft sections that drove it

## Functional Modules

### 1. Opportunity Parser

The parser converts official opportunity material into normalized records.

Outputs:

- title and solicitation metadata
- instrument type
- deadline and submission path
- evaluation criteria
- eligibility markers
- security or export-control markers
- source-backed section references

### 2. Compliance Matrix Generator

The compliance matrix maps normalized requirements to proposal evidence.

Minimum output columns:

- `requirement_id`
- `requirement_text`
- `category`
- `priority`
- `status`
- `evidence_section_ids`
- `confidence`
- `source_section`

### 3. Readiness Scoring Engine

The scoring engine must be explainable and section-aware. It should score based on:

- explicit requirement coverage
- evaluation criterion alignment
- evidence density
- contradictions or unsupported claims
- missing submission prerequisites

### 4. Source-Linked Draft Assistant

The assistant may suggest improvements only when each suggestion is grounded in one or more citations. It must surface the cited requirement, guidance section, or official opportunity text alongside the recommendation.

### 5. Risk Review Layer

The risk layer flags:

- unsupported claims
- stale or conflicting deadlines
- registration prerequisites not yet satisfied
- mismatch between proposal claims and opportunity scope
- section omissions for high-priority requirements

## Non-Goals

This system is not initially responsible for:

- autonomous proposal submission
- legal sign-off
- proprietary "winning proposal" modeling without licensed access
- replacing human capture, pricing, or contracting judgment

## Minimal API Surface

The first useful API set should be narrow and schema-backed.

### `POST /v1/opportunities/normalize`

Input:

- raw solicitation or guidance document

Output:

- normalized `opportunity` record
- extracted `requirements`

### `POST /v1/proposals/analyze`

Input:

- normalized opportunity record
- user proposal draft sections

Output:

- compliance matrix
- readiness score bundle
- source-linked risk findings

### `POST /v1/proposals/chat`

Input:

- analysis bundle
- user question

Output:

- citation-backed answer only

## Success Criteria

The MVP is successful when it can:

- parse a real BAA or federal opportunity into structured records
- produce a compliance matrix against a user draft
- return an explainable readiness score bundle
- answer user questions with citations instead of freeform hallucination

## Relationship to Existing SCBE Work

This spec should remain compatible with:

- route-consistency records for multi-view training
- model-trace records for low-trust note and assistant extraction
- source-grounded governance scoring for proposal-risk review

The product lane is separate from patent language and should be treated as an operational build target rather than an IP memo.
