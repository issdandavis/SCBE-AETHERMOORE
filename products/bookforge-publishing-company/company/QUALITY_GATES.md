# BookForge Quality Gates

## Gate 1: Source Hygiene

- One H1 title at the top of the manuscript.
- Chapter headings use H2.
- Scene breaks use `---` on a line by itself.
- No hidden notes meant only for the author.
- No unsupported control characters.
- File names are ASCII.

## Gate 2: Build Hygiene

- `bookforge info` succeeds.
- `bookforge interior` succeeds.
- `bookforge cover --blurb blurb.json` succeeds when `page_count` is set.
- `bookforge epub` succeeds.
- `bookforge docx` succeeds.

## Gate 3: KDP Hygiene

Use current KDP documentation as the final external rule source:

- KDP trim, bleed, and margin guidance:
  https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6
- KDP paperback submission guidelines:
  https://kdp.amazon.com/en_US/help/topic/G201857950
- KDP cover calculator and templates:
  https://kdp.amazon.com/cover-calculator
- KDP paperback cover requirements:
  https://kdp.amazon.com/en_US/help/topic/G201953020

Important constraints to keep visible:

- Covers are single PDF wrap files.
- Cover bleed is 0.125 inch on top, bottom, and outside edges.
- Cover width is bleed + back + spine + front + bleed.
- Cover height is bleed + trim height + bleed.
- Spine text is only for books above the KDP page-count threshold.
- KDP Print Previewer is the final upload check.

## Gate 4: Delivery Hygiene

- Include a build receipt.
- Include exact commands used.
- Include tool availability notes.
- Include any warnings that remain.
- Do not claim Amazon approval until Amazon/KDP has actually approved the title.

