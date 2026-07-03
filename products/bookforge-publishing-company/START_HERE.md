# BookForge Publishing Company Kit

This kit is the practical AetherMoore publishing lane: a small, sellable
publishing operation built around `scbe-bookforge`.

## What This Is

BookForge turns Markdown manuscripts into KDP-ready interior PDFs, cover-wrap
proofs, EPUB files, and DOCX files. The open-source engine is the machine. This
kit is the business wrapper around it:

- KDP-ready profile presets.
- A starter manuscript.
- Blurb and launch templates.
- Author intake.
- Fulfillment SOP.
- Quality gates.
- Offer ladder for selling the work.

## First Build

From the repo root:

```powershell
python -m pytest packages\bookforge\tests -q
python -m build --sdist --wheel --outdir artifacts\bookforge-dist packages\bookforge
python scripts\system\build_bookforge_publishing_company.py --json
```

If PyPI is still pending, include the wheel from `artifacts/bookforge-dist` with
the customer delivery. Once PyPI is live, the buyer path becomes:

```powershell
pip install scbe-bookforge
bookforge build bookforge.json
```

## Product Position

Sell the kit as a $19 self-serve publishing operations pack for authors and
small presses who already have a manuscript and need the boring KDP details to
stop being mysterious.

Do not sell it as a guarantee of Amazon approval, bestseller performance, tax
advice, legal advice, ISBN registration, cover design taste, or copyediting.

## Company Shape

- Imprint: AetherMoore Publishing.
- Engine: BookForge.
- Entry product: BookForge Publishing Kit.
- Service upsell: KDP Build Sprint.
- Ongoing product lane: repeatable genre templates, prompt packs, and book
  production checklists.

