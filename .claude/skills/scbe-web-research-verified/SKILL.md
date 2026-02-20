---
name: scbe-web-research-verified
description: Run verifiable web research across mainstream news, niche outlets, and academic primary sources, then return dated evidence with confidence scoring. Use when asked to research current events, science claims, market context, or source-grounded recommendations.
---

# SCBE Web Research Verified

Use this workflow to collect high-signal evidence and avoid low-quality citations.

## Workflow

1. Define the question in one sentence.
2. Set time window and geography.
3. Gather sources from three buckets: established outlets, niche domain outlets, primary or academic sources.
4. Extract claims with publication date and direct URL.
5. Cross-check each claim with at least one independent source.
6. Score confidence for each claim.
7. Return a concise evidence brief.

## Source Priority

1. Primary documentation, official datasets, standards, and peer-reviewed papers.
2. Major outlets with transparent editorial process.
3. Niche outlets with demonstrated domain expertise.
4. Social posts only as leads, never as sole evidence for factual claims.

## Output Contract

1. `research_brief.md` with summary and key findings.
2. `evidence_table.csv` with `claim`, `source`, `published_at`, `verified_with`, `confidence`.
3. `open_questions.md` with unresolved items and next checks.

## Guardrails

1. Prefer timestamped sources and include exact dates.
2. Separate facts from inference.
3. Flag contradictions instead of forcing consensus.
4. Include links for every non-trivial claim.
