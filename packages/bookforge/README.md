# scbe-bookforge

Markdown to a KDP print/Kindle handoff packet. It builds paperback interiors and wraps, Kindle EPUBs, and editable DOCX files. Hardcover interiors are supported, but a final case-laminate cover must be laid out against the exact template downloaded from KDP for that book; Bookforge intentionally refuses to guess hinge and wrap geometry.

Built because we got tired of Word templates and Vellum subscriptions for self-publishing on Amazon KDP.

## What it does

```
manuscript.md  ─►  bookforge build  ─►  interior.pdf  +  cover-wrap.pdf  +  book.epub  +  book.docx
```

- **Interior PDF**: real book typography via XeLaTeX (hyphenation, microtype, widow/orphan control). Falls back to ReportLab if XeLaTeX isn't installed.
- **Cover wrap PDF**: full back + spine + front with bleed. Spine width is computed from page count and paper type using the actual KDP formula (`pages × 0.0025 in` for cream B&W).
- **EPUB**: pandoc-native, with title/subtitle/author/identifier metadata.
- **DOCX**: pandoc-native, with TOC.
- **Local Book Studio**: open `docs/bookforge-writing-studio.html` in the repository site to import a manuscript and cover locally, tune edition and ornament options, generate a draft blurb/cover brief, inspect image values, and export a preflight packet. Its Story Fire Graph maps chapters, recurring characters, and high-intensity moments into a filterable local timeline with JSON export. Files stay in the browser unless you explicitly download an export.

## Install

```bash
pip install scbe-bookforge
```

For the better-typography path, also install:

- **pandoc** — <https://pandoc.org/installing.html>
- **MiKTeX** (Windows) or **TeX Live** (macOS/Linux) — provides `xelatex`

If `xelatex` is missing, bookforge automatically uses its ReportLab fallback.

## Quick start

Drop a `bookforge.json` next to your manuscript:

```json
{
  "title": "Your Book Title",
  "subtitle": "An Optional Subtitle",
  "author": "Your Name",
  "copyright_year": 2026,
  "publisher": "Your Name",
  "isbn": "Print ISBN: printed on back cover (free KDP ISBN)",
  "edition_statement": "First edition",
  "source": "manuscript.md",
  "output_dir": "build",
  "trim": "5.5x8.5",
  "page_count": 320,
  "print": {
    "paper": "cream",
    "ink": "bw",
    "cover_finish": "matte"
  },
  "epigraph": {
    "enabled": true,
    "text": "Your epigraph text.",
    "attribution": "Source"
  },
  "dedication": "To whoever this is for."
}
```

Build everything:

```bash
bookforge build
```

Or one at a time:

```bash
bookforge interior
bookforge cover
bookforge epub
bookforge docx
bookforge info       # show resolved profile + spine width
```

Outputs land in `output_dir`.

## Profile reference

| Field | Default | Notes |
|---|---|---|
| `title` | *required* | Book title |
| `subtitle` | `""` | Optional |
| `author` | `""` | |
| `copyright_year` | `2026` | |
| `publisher` | author | Imprint name shown on copyright page |
| `isbn` | `""` | Use literal `"Print ISBN: printed on back cover (free KDP ISBN)"` for KDP free ISBNs |
| `edition_statement` | `"First edition"` | |
| `creative_nonfiction_notice` | `""` | Shown on copyright page if set |
| `dedication` | `""` | Renders a dedication page if set |
| `epigraph.enabled` | `false` | |
| `epigraph.text` | `""` | |
| `epigraph.attribution` | `""` | |
| `source` | *required* | Path to manuscript Markdown, relative to the profile |
| `output_dir` | `"build"` | Relative to the profile |
| `binding` | `"paperback"` | `paperback` or `hardcover` (hardcover adds 0.125" to inner margin) |
| `trim` | `"5.5x8.5"` | Or `"5x8"`, `"5.25x8"`, `"6x9"`, or `{"width_in": W, "height_in": H}` |
| `page_count` | `null` | **Required for cover wrap.** Build the interior first; KDP's previewer will report the page count, paste it back here, rebuild the cover. |
| `print.paper` | `"cream"` | `cream` or `white` (affects spine math) |
| `print.ink` | `"bw"` | `bw`, `color_standard`, `color_premium` |
| `print.cover_finish` | `"matte"` | Informational |
| `cover_art` | `null` | Optional front-cover image path, relative to the profile |
| `cover.simulated_gold` | `false` | Uses process-color gold artwork. This is not metallic foil, gilding, or spot ink. |
| `cover.background_color` | `"#0b1720"` | Back/spine process-color background |
| `ornament.style` | `"none"` | `none`, `water_channel`, `rose`, or `gold_rule` for ReportLab interiors |
| `ornament.color` | `"#587b73"` | Process-color ornament color |
| `ornament.opacity` | `0.28` | Ornament opacity from 0 to 1 |
| `typography.body_font` | `"Georgia"` | Any installed font; bookforge looks for it via fontspec (XeLaTeX) or `C:\Windows\Fonts` (ReportLab) |
| `typography.body_size_pt` | `10.75` | |
| `typography.leading_pt` | `14.0` | |
| `typography.first_line_indent_in` | `0.22` | |
| `typography.chapter_title_size_pt` | `17.0` | |
| `typography.part_title_size_pt` | `18.0` | |
| `margins.top_in` | `0.62` | |
| `margins.bottom_in` | `0.68` | |
| `margins.inside_in` | `0.75` | Inner margin (gutter side) |
| `margins.outside_in` | `0.5` | |
| `margins.hardcover_inside_bonus_in` | `0.125` | Extra inner margin when `binding="hardcover"` |
| `interior_engine` | `"auto"` | `auto`, `xelatex`, or `reportlab` |

### Back-cover blurb

The cover wrap defaults are intentionally bland. Pass `--blurb path/to/blurb.json` to populate them, or put the fields directly into your profile:

```json
{
  "hook": "Single line at the top of the back.",
  "blurb_paragraphs": [
    "First paragraph.",
    "Second paragraph.",
    "Third paragraph."
  ],
  "author_bio": "Optional bio.",
  "bottom_left_caption": "A WORK OF CREATIVE NONFICTION"
}
```

## Manuscript conventions

- One `# H1` line at the top of the file is treated as the book title and skipped (the title page comes from the profile).
- `## Chapter N. Title` → typeset chapter; gets its own page break + recto opening.
- `## Part N. Title` → typeset part heading.
- `---` on its own line → typeset scene break (`* * *`).
- `*italic*` and `**bold**` work as expected.
- Smart quotes are produced automatically (pandoc's `markdown+smart`).

## Spine math

Bookforge uses the KDP formulas:

| Paper type | Inches per page |
|---|---|
| Cream, B&W | 0.0025 |
| White, B&W | 0.002252 |
| Color, standard | 0.002252 |
| Color, premium | 0.002347 |

`spine_width = page_count × per_page`. Cover wrap dimensions = `(0.125 + trim_w + spine + trim_w + 0.125) × (0.125 + trim_h + 0.125)`.

If KDP's previewer flags your cover by more than ~0.05", regenerate using the page count KDP reports for the interior you uploaded.

These factors are for paperback. Hardcover covers require KDP's exact case-laminate template and include hinge and wrap regions that cannot be derived from paperback bleed math alone.

## Print-color limits

Bookforge's image inspector reports effective DPI, luminance, clipped shadows/highlights, and saturation, and its browser editor can make non-destructive preview adjustments before exporting a PNG. It does not perform ICC soft proofing or replace a physical proof. KDP does not print metallic spot colors, so the gold option is a simulated CMYK/process-color look. Always inspect the uploaded files in KDP Print Previewer and order a proof for color-critical work.

Bookforge prepares files; it does not publish them or claim a private KDP upload API. Upload the exported manuscript and cover through your KDP Bookshelf and approve them in Print Previewer.

## Programmatic use

```python
from scbe_bookforge import load_profile, build_all

profile = load_profile("my-book/bookforge.json")
artifacts = build_all(profile)
print(artifacts)
# {"interior_pdf": ..., "cover_pdf": ..., "epub": ..., "docx": ...}
```

## License

MIT or Apache 2.0, at your option.
