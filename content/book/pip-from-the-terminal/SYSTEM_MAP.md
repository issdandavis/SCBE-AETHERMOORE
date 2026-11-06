# pip from the Terminal — Publication System Map

Status: ACTIVE BUILD MAP
Checked: 2026-10-28

## Capability

Produce one cited, versioned Markdown manuscript about pip and Python terminal
workflows, then generate a 6 x 9 inch KDP print interior, Kindle EPUB, and review
DOCX from that source.

## Nodes

| Node | Path or authority | Role | Status |
|---|---|---|---|
| User source | This project folder and supplied `pip wheel --help` output | Scope and requested command coverage | VERIFIED |
| Runtime evidence | Python 3.12.10 and pip 26.2.2 on ISACLAPTOP | Command names, help, and smoke tests | VERIFIED 2026-10-28 |
| External authority | Official pip, PyPA, Python, Wheel, pip-audit, and KDP pages listed in `SOURCES.md` | Volatile technical and platform rules | VERIFIED 2026-10-28 |
| Canonical manuscript | `manuscript.md` | Source of truth for prose and command examples | NEW |
| Publication profile | `bookforge.json` | Metadata, trim, typography, and output paths | NEW; reuses Bookforge schema |
| Renderer | `packages/bookforge` | PDF, EPUB, DOCX, and cover generation | REUSED; ReportLab fallback extended for code and lists |
| Generated artifacts | `build/` | KDP interior, EPUB, DOCX, cover proof, and receipts | GENERATED; do not hand-edit |
| Human review | Kindle Previewer, KDP Print Previewer, proof copy | Final device, print, rights, and metadata decisions | REQUIRED |

## Edges and invariants

```text
official docs + local pip help + tested examples
    -> SOURCES.md + manuscript.md
    -> bookforge.json
    -> Bookforge
    -> PDF + EPUB + DOCX
    -> text/size/page audit
    -> KDP human preview and disclosure
```

- Technical claims must resolve to a source in `SOURCES.md` or a dated local
  command test.
- The published edition must state the tested pip and Python versions.
- `python -m pip` is the default form; platform launchers are explained where
  they differ.
- The print interior is no-bleed, black-and-white, 6 x 9 inches.
- Cover spine math is calculated only after the interior page count is stable.
- Because an AI system drafted actual text, the KDP upload packet records the
  manuscript as AI-generated text under Amazon's current definition.

## Build gate

- Reused component: SCBE Bookforge and its nonfiction profile.
- New component: the manuscript, source ledger, metadata packet, and technical
  code/list support in Bookforge's ReportLab fallback.
- Inputs: UTF-8 Markdown, JSON profile, official URLs, pip 26.2.2 help.
- Outputs: valid PDF, EPUB, DOCX, extracted-text audit, and page count.
- Rollback: remove this new folder and revert the three scoped Bookforge files.
- Stop conditions: missing command text, visible Markdown fences, overflow or
  unreadable code, invalid EPUB/DOCX, unverified volatile command claims, or a
  KDP profile outside current trim/page rules.

## Post-build evidence

- Canonical manuscript: 3,602 words, 62 code blocks.
- Bookforge smoke tests: 8 passed.
- Outputs: 26-page 6 x 9 PDF, 17-document EPUB, DOCX, and calibrated cover wrap.
- Cover gate fixed: books with 79 or fewer pages no longer receive spine text.
- EPUB chapter split updated from deprecated `--epub-chapter-level` to
  `--split-level=2`, matching Bookforge's H2 chapter convention.
- Exact artifact hashes and remaining human review gates are recorded in
  `BUILD_RECEIPT.md`.
