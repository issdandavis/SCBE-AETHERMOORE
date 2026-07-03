# AetherMoore Publishing Company Blueprint

## Mission

Help authors and tiny teams ship clean book files without becoming print-layout
technicians.

## Wedge

Most self-publishing pain is not writing. It is conversion, margins, cover wrap
math, EPUB checks, DOCX fallback, file naming, and repeatable upload discipline.
BookForge makes those steps deterministic enough to package.

## Product Ladder

| Offer | Price | Buyer | Promise |
|---|---:|---|---|
| BookForge Publishing Kit | $19 | Author with a manuscript | Turn Markdown into a KDP build folder with presets and checklists. |
| BookForge Build Audit | $99 | Author stuck before upload | Review one project folder and return the next three fixes. |
| KDP Upload Prep Sprint | $199 | Author near launch | Produce the upload folder, page-count note, cover-size note, and final checklist. |
| Done-For-You BookForge Build | $500 | Busy solo author | Convert one manuscript into interior PDF, cover-wrap proof, EPUB, DOCX, and launch handoff. |
| Small Press Retainer | $250/month+ | Repeat publisher | Monthly template maintenance, build QA, and product-page refreshes. |

## Operating Roles

- Publisher/operator: owns buyer promise, checkout, refund boundary, delivery
  date, and final communication.
- Production editor: cleans Markdown, front matter, headings, scene breaks, and
  metadata.
- Build operator: runs BookForge, validates outputs, records page count, and
  rebuilds cover after KDP preview feedback.
- Launch assistant: prepares blurb, product description, categories/keywords
  draft, and email/social copy.

One person can fill all roles at first. Keep the roles separate in checklists so
the work can later be delegated.

## Proof Surfaces

- Engine source: `packages/bookforge/`.
- Product kit source: `products/bookforge-publishing-company/`.
- Public proof page: `docs/bookforge-publishing-kit.html`.
- Package page: `docs/packages/scbe-bookforge.html`.
- Build script: `scripts/system/build_bookforge_publishing_company.py`.
- Release artifacts: `artifacts/bookforge-publishing-company/latest/`.

## Boundaries

This is a publishing operations company, not a law firm, tax office, literary
agency, or Amazon approval guarantee.

Each buyer deliverable should say:

- KDP rules can change; final acceptance is decided by KDP.
- Author owns manuscript rights and permissions.
- Buyer is responsible for legal, tax, ISBN, copyright registration, and ad
  spend decisions.
- AI-assisted text should be reviewed by the author before publication.

