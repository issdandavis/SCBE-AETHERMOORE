# Toolchain

## Open-Source-First Stack

- `Pandoc`
  - Use for source-to-EPUB, DOCX, and PDF conversion.

- `Sigil`
  - Use for EPUB polishing when the generated file needs manual cleanup.

- `EPUBCheck`
  - Use for EPUB validation.

- `Scribus`
  - Use for print layout when the interior needs precise print design beyond simple novel formatting.

- `Kindle Previewer`
  - Use for Kindle-facing preview and sanity checks.

- `Adobe Digital Editions`
  - Use as a second-opinion EPUB reader, not as a Kindle emulator.

## Commercial-Assist Stack

- `Adobe`
  - Use when art, cover composition, or print-exact layout needs more control.

- `Canva`
  - Use for fast cover mockups and marketing assets.

## Selection Heuristics

### Text-heavy novel

Use:
- Pandoc
- EPUBCheck
- Kindle Previewer

Add Sigil only if cleanup is needed.

### Ornamented or art-forward print edition

Use:
- Pandoc for initial conversion
- Scribus or Adobe for print-final PDF

### AI art generation workflow

Use:
- prompt pack
- motif sheet
- must-avoid list
- output size targets

Do not start by generating random cover variants.

## Repo-Specific Builder Rule

If the current repo already ships a publication script, prefer the local builder over a generic pipeline.

Current example:

- `C:\Users\issda\SCBE-AETHERMOORE\content\book\build_kdp.py`
  - Builds a KDP-oriented DOCX for `The Six Tongues Protocol`
  - Use this first for the live Aethermoor book workflow, then review the output in Kindle-facing and print-facing tools

## Formatting Guardrails

1. Do not depend on exact body fonts in reflowable ebooks.
2. Treat asides and note blocks as paragraph styles, not floating sidebars.
3. Keep fixed-layout exceptional.
4. Preview on at least one Kindle-facing tool and one non-Kindle EPUB reader.
