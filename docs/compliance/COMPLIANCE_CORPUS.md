# Compliance corpus (local review and training prep)

This repo keeps **public, official** texts that align with SCBE-style systems: AI governance
(NIST AI RMF), security baselines (NIST CSF, SP 800-171 where relevant), and EU legal instruments
(GDPR, EU AI Act) as **HTML from EUR-Lex**. Purchase-only standards (ISO full documents,
proprietary SOC 2 packs) are **indexed but not auto-downloaded** — acquire those under license
and store them **outside** git if your license forbids redistribution.

## Quick fetch (PDFs only, small set)

From the repository root:

```bash
python scripts/system/fetch_public_compliance_corpus.py --only nist_ai_rmf_100_1,nist_csf_2_0,nist_sp800_171_rev3
```

Preview without downloading:

```bash
python scripts/system/fetch_public_compliance_corpus.py --dry-run --only nist_ai_rmf_100_1
```

Large EUR-Lex pages (GDPR, EU AI Act HTML):

```bash
python scripts/system/fetch_public_compliance_corpus.py --include-large
```

Artifacts land under `docs/compliance/corpus/fetched/` with a `fetch_index.json` checksum manifest.
That folder is ignored by git by default so you do not accidentally commit multi-megabyte HTML;
remove or adjust `docs/compliance/corpus/fetched/.gitignore` if you intentionally version excerpts.

## Review workflow

1. Run the fetcher for the PDF bundle first (fast, stable URLs).
2. Open `fetch_index.json` and confirm `sha256` for supply-chain awareness.
3. For training: chunk **short factual excerpts** with citations (title, section, URL, retrieval date),
   not full redistribution of paywalled ISO text.
4. Map recurring themes (accountability, documentation, risk tiers, third-party supply chain)
   to your governance gates and cross-talk rationale fields — that alignment is the reusable signal.

## Manifest

Curated list: `config/compliance/public_sources.json`.

## Related

- Training surfaces without leaking credentials: `npm run training:hub` and
  `scripts/system/training_surfaces_connect.py`.
