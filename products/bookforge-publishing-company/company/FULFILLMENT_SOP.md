# BookForge Fulfillment SOP

## Intake

Collect:

- Manuscript file.
- Desired trim size.
- Paperback or hardcover.
- Paper type and ink type.
- Page count if already known.
- Title, subtitle, author, publisher/imprint, ISBN statement.
- Cover concept or finished cover assets.
- Blurb and author bio.
- Deadline and KDP account owner.

Use `templates/author-intake.md`.

## Project Setup

1. Create a clean project folder.
2. Copy the closest profile from `profiles/`.
3. Rename it to `bookforge.json`.
4. Put the manuscript at `manuscript.md`.
5. Put blurb data at `blurb.json`.
6. Run:

```powershell
bookforge info bookforge.json
bookforge build bookforge.json --blurb blurb.json
```

## QA Gate

Before delivery, verify:

- Interior PDF opens.
- EPUB opens.
- DOCX opens.
- Cover wrap dimensions match BookForge spine math.
- File names are simple ASCII names.
- No unsupported placeholder text remains.
- Page count is recorded.
- Profile and generated outputs are delivered together.

## KDP Two-Pass Cover Workflow

1. Build the interior.
2. Upload the interior to KDP.
3. Read the page count reported by KDP Print Previewer.
4. Update `page_count` in `bookforge.json`.
5. Rebuild the cover wrap.
6. Upload the rebuilt cover.
7. Review previewer warnings.

## Delivery Folder

Deliver:

- `interior.pdf`
- `cover-wrap.pdf`
- `book.epub`
- `book.docx`
- `bookforge.json`
- `blurb.json`
- `BUILD_RECEIPT.md`
- `KDP_UPLOAD_CHECKLIST.md`

