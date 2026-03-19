# Research Publishing and Search Handoff

**Date:** 2026-03-19
**Status:** Completed with partial platform blockage
**Scope:** refine article drafts, ground claims with official sources, publish what could be published, and record search visibility state

---

## What was completed

### Drafts and platform variants

Created internal research drafts:

- `content/articles/research/2026-03-19-domain-separated-ai-governance.md`
- `content/articles/research/2026-03-19-phonetic-bootstrapping-from-fiction.md`
- `content/articles/research/2026-03-19-curving-the-browser.md`
- `content/articles/research/2026-03-19-research-source-pack.md`

Created public-facing platform variants:

- `content/articles/devto_domain_separated_ai_governance.md`
- `content/articles/platforms/2026-03-19-hf-phonetic-bootstrapping.md`
- `content/articles/platforms/2026-03-19-hf-curving-the-browser.md`

### Claim support and evidence

Built supporting research and evidence artifacts:

- `artifacts/research_publishing/20260319/official_source_notes.md`
- `artifacts/research_publishing/20260319/campaign_posts.json`
- `artifacts/research_publishing/20260319/search_visibility_plan.md`
- `artifacts/research_publishing/20260319/self_context_pack.json`
- `artifacts/research_publishing/20260319/claim_gate_report.json`

Claim gate result:

- `Claims checked: 9`
- `failed: 0`
- `pass: True`

### Official source basis

Primary official or primary-reference support used in the article lane:

- NIST AI RMF Playbook
- NIST Zero Trust Architecture
- W3C Secure Contexts
- RFC 6454
- Google Search Essentials / How Search Works / crawlable links / sitemap guidance
- International Phonetic Association references
- CMU Pronouncing Dictionary
- TIMIT / STC-TIMIT reference material

---

## Public publishing result

### Published successfully

Hugging Face discussion posts are live:

1. Phonetic article  
   `https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data/discussions/4`

2. Curved browser article  
   `https://huggingface.co/issdandavis/phdm-21d-embedding/discussions/4`

Evidence:

- `artifacts/publish_browser/huggingface_discussion_20260319T135135994157Z.json`
- `artifacts/publish_browser/huggingface_discussion_20260319T135137383569Z.json`

Both URLs were fetched and returned HTTP 200 with public page metadata present.

### Blocked lane

Dev.to post attempt failed:

- file: `content/articles/devto_domain_separated_ai_governance.md`
- evidence: `artifacts/publish_browser/devto_20260319T135103Z.json`
- failure: `HTTP 401 unauthorized`

This is an auth problem, not a content problem.

---

## Search visibility state

The two Hugging Face pages are:

- public
- fetchable
- canonicalized
- eligible to be discovered

What is **not** confirmed yet:

- exact-title indexing in Google or other web search

Exact-title web checks did **not** show immediate indexing. That is consistent with Google's own guidance: eligibility and accessibility do not guarantee immediate crawl or index inclusion.

Search state artifact:

- `artifacts/research_publishing/20260319/search_visibility_plan.md`

---

## GitHub state

Repo-backed notes now exist locally in this branch.

Web GitHub posting was not used in this lane because `gh auth status` was invalid during the publishing pass. If needed later, fix GitHub auth first and then post or mirror these notes to a GitHub discussion/issue/PR comment intentionally.

---

## Recommended next actions

1. Repair Dev.to credentials and rerun `scripts/publish/post_to_devto.py`.
2. Repair GitHub CLI auth if a GitHub discussion or issue mirror is required.
3. Re-check search indexing after crawl delay instead of assuming same-day visibility.
4. If stronger search visibility is needed, publish matching articles on a property you control directly and add a crawl path there.

---

## Bottom line

The research-writing and evidence pass is done. Two public Hugging Face posts are live, claims were support-gated, Dev.to is blocked on auth, and search visibility is in the correct "public but not yet proven indexed" state.
