# BookForge Publishing Company

Status: operating foundation built locally on 2026-07-02.

## Offer

AetherMoore Publishing sells a self-serve BookForge Publishing Kit first, then
uses the same workflow for paid build audits and done-for-you KDP preparation.

## Why This Can Sell

The customer is not buying an abstract code package. They are buying a clean
upload path:

- profiles for common KDP trims,
- a starter manuscript,
- a blurb template,
- a KDP upload checklist,
- a fulfillment SOP,
- and the BookForge engine that builds interior PDF, cover wrap, EPUB, and DOCX.

## Product Ladder

1. BookForge Publishing Kit: `$19`, self-serve.
2. BookForge Build Audit: `$99`, one book folder reviewed.
3. KDP Upload Prep Sprint: `$199`, one near-final book prepared for upload.
4. Done-For-You BookForge Build: `$500`, one full build and delivery handoff.
5. Small Press Retainer: `$250/month+`, recurring production support.

## Source Paths

- Product kit source: `products/bookforge-publishing-company/`
- Public proof page: `docs/bookforge-publishing-kit.html`
- Package page: `docs/packages/scbe-bookforge.html`
- Offer registry: `docs/offers.json`
- Packager: `scripts/system/build_bookforge_publishing_company.py`
- Output: `artifacts/bookforge-publishing-company/latest/`

## Readiness

Ready locally:

- BookForge tests pass.
- XeLaTeX hyperref bug fixed in source.
- Local wheel and sdist can be built.
- Product kit can be packaged into a ZIP.

External blockers:

- `scbe-bookforge` must still be published to PyPI before public install copy is
  fully true.
- A dedicated Stripe delivery link can be added after the manual-delivery product
  proves demand.

