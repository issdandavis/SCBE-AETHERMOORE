# AI Authors and Book Publishing Space — 2026-05-03

## Working Position

AI involvement is not the core quality problem. The market problem is low-effort publishing: incoherent books, weak continuity, misleading presentation, poor formatting, fake authority, and author catalogs that do not build reader trust.

The useful SCBE lane is not "AI book spam." It is governed publishing:

1. disclose AI-generated material when Kindle Direct Publishing requires it,
2. score the manuscript as a whole story,
3. check production quality before upload,
4. keep final publish human-confirmed,
5. let the author build a real portfolio instead of dumping noise.

## Current Platform Reality

Kindle Direct Publishing requires authors to disclose AI-generated text, images, or translations when publishing a new book or republishing an edited book. Amazon distinguishes AI-generated content from AI-assisted content: generated content is actual text/images/translations created by an AI tool; assisted content is author-created work refined, corrected, or improved with AI tools. The author remains responsible for rights, accuracy, and customer experience.

Vellum's KDP upload guide mirrors the same operational reality: before previewing an ebook or paperback, the publisher must answer the AI-generated-content question, upload the manuscript/cover, run the previewer, and approve the result. That matches our intended automation boundary: AI can prepare, inspect, and navigate, but final approval should stay human.

## Market Signal

The indie author tooling space has normalized AI as a workflow aid: brainstorming, editing, research, covers, marketing copy, and audiobook experimentation. The more useful guides do not sell AI as a magic bestseller button. They emphasize that AI lowers production friction, while reader connection, voice, quality, marketing, and catalog trust still decide outcomes.

The reader/publisher backlash is not imaginary. Reporting around the 2026 "Shy Girl" controversy focused on trust, detection, and quality control. The most useful failure signals named in the coverage are practical, not moral: gaps in logic, melodramatic over-patterning, and formulaic prose. Those are exactly the kinds of defects a story-quality gate should look for.

The Authors Guild's Human Authored initiative shows the other side of the market: some readers and authors want explicit human-authorship certification. That does not mean AI-assisted or AI-generated work cannot be sold; it means transparency is becoming a product signal.

There is also research pressure from the other direction. A 2025 arXiv preprint reported that fine-tuned AI outputs could be preferred by readers in blind tests, while plain prompted outputs were penalized by expert readers for style and quality. The lesson for us is not "publish raw AI." The lesson is that quality depends on process, review, and style control.

## Tools Authors Actually Use

Common author-facing formatting and publishing tools:

- Vellum: polished ebook/print formatting, Mac-first, common among indie authors.
- Atticus: cross-platform writing plus formatting.
- Kindle Create: Amazon's free formatting tool.
- Scrivener: long-form drafting and manuscript organization.
- Reedsy Book Editor: browser-based manuscript formatting and export.
- Adobe InDesign: professional layout, heavier and less author-friendly.

SCBE should not clone all of these. The gap we can own is the governed layer around them:

- manuscript source manifest,
- story-quality score,
- visual format report,
- AI disclosure packet,
- KDP upload packet,
- human publish confirmation.

## Proposed SCBE Quality Tiers

Use quality tiers instead of a binary "AI/human" judgment:

| Tier | Score | Meaning | Action |
|---|---:|---|---|
| Do Not Publish Quality Risk | 0-59 | Likely harms readers and author reputation | Revise heavily |
| Draft Needs Revision | 60-74 | Some usable material, but not enough coherence | Fix story-level issues |
| Publishable With Review | 75-84 | Coherent enough for a controlled release | Human proof + formatting check |
| Portfolio Ready | 85-94 | Strengthens author catalog | Publish after final review |
| Flagship | 95-100 | Strong enough to anchor marketing | Launch campaign eligible |

## Gate Dimensions

The gate should score the book, not the tool that helped write it:

1. Whole-story coherence: does the beginning, middle, and ending form one intelligible arc?
2. Character continuity: do character motives, relationships, and voice remain stable?
3. Plot causality: do events happen because of prior choices instead of random drift?
4. Prose readability: is the sentence-level experience smooth enough for paying readers?
5. Originality and reader value: does the book offer a reason to exist?
6. Portfolio fit: does this book build a credible author catalog?
7. Production readiness: does the file look professional in ebook/print preview?

## Implementation Path

The current repo now has the right first pieces:

- `content/book/kdp_submission_packet.json` records AI disclosure and human review.
- `content/book/story_quality_packet.json` records the craft/portfolio rubric.
- `scripts/publish/kdp_story_quality_gate.py` scores the manuscript as a book.
- `scripts/publish/kdp_visual_format_report.py` checks the generated DOCX layout.
- `scripts/publish/kdp_acceptance_gate.py` blocks upload unless the packet is reviewable.

Next useful upgrades:

1. Add an evaluator packet format so multiple human/AI reviewers can score the same book independently.
2. Add a chapter-level continuity diff that flags names, places, timeline, and unresolved setup/payoff.
3. Add a "reader promise" field: what the book claims to deliver and whether the manuscript actually pays it off.
4. Add launch-readiness checks: cover, description, categories, keywords, sample pages, and author-page consistency.
5. Keep KDP publishing human-confirmed even if every gate passes.

## Sources

- Amazon Kindle Direct Publishing Content Guidelines: https://kdp.amazon.com/en_US/help/topic/G200672390
- Amazon Kindle Direct Publishing publish overview: https://kdp.amazon.com/en_US/publish
- Vellum KDP upload guide: https://help.vellum.pub/uploading/kdp/
- Associated Press on Authors Guild Human Authored certification: https://apnews.com/article/human-authored-ai-guild-books-writers-84c261d8393f96ec85cfdf3261e08736
- The Week on the Shy Girl AI-book controversy: https://theweek.com/culture-life/books/shy-girl-ai-books-hachette
- arXiv preprint, "Readers Prefer Outputs of AI Trained on Copyrighted Books over Expert Human Writers": https://arxiv.org/abs/2510.13939
- Books.by AI tools for self-publishing authors guide: https://books.by/guides/ai-tools-for-self-publishing
