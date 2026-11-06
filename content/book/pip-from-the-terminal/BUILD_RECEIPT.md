# Build Receipt — pip from the Terminal

Built and verified: 2026-10-28
Source runtime: Python 3.12.10, pip 26.2.2
Builder: SCBE Bookforge source tree

## Canonical source

- `manuscript.md`: 3,602 words, 37 headings, 62 fenced code blocks, 67 list items
- `bookforge.json`: paperback, 6 x 9 inches, white paper, black ink, no bleed
- Final interior page count: 26
- Computed spine: 0.058552 inches
- Spine text: omitted because KDP only prints spine text above 79 pages

## Generated files

| File | Bytes | SHA-256 |
|---|---:|---|
| `build/manuscript-interior.pdf` | 126,159 | `2fa36ce95aec0ba0af4005039b3a7a39667739f07239b19f85e5274ac6253484` |
| `build/manuscript-cover-wrap.pdf` | 90,229 | `7577cc0d068227d723d699a1234722c798b4e5708e8d1a9ea14c0c947f2515d9` |
| `build/manuscript.epub` | 35,913 | `da756a4726eb137c48ea29fb55512b8196e55711a3a98b563fed064a319f8b09` |
| `build/manuscript.docx` | 24,438 | `3bcf8ddeeb59f663971433c3cf7104acf9edaa6651d8bfd1baeb5533682ee734` |

## Verification

- Bookforge smoke tests: **8 passed**
- Interior PDF: **26 pages**, every page **6 x 9 inches**
- Cover wrap: **12.308551 x 9.25 inches**, matching 6 x 9 trim, 0.125-inch bleed, and the computed spine
- EPUB: `mimetype` is the first ZIP member; **17 XHTML content files**
- DOCX: `word/document.xml` present
- Extracted PDF text contains `python -m pip wheel`,
  `--requirements-from-script`, `--build-constraint`, and the Sources section
- Visual review: introduction, dense wheel-command page, two source pages, and full cover wrap inspected
- Generated-prose residue scan: no matches for the selected stock opener,
  puffery, corporate, and formulaic-closer patterns

## Commands

```powershell
$env:PYTHONPATH = "$PWD\packages\bookforge\src"
python -m pytest packages\bookforge\tests\test_smoke.py -q
python -m scbe_bookforge build content\book\pip-from-the-terminal\bookforge.json --blurb content\book\pip-from-the-terminal\blurb.json
```

## Publication gates still requiring a human

- Run EPUBCheck; it was not installed on this machine.
- Open the EPUB in Kindle Previewer and inspect narrow phone, tablet, and
  e-reader views.
- Upload the PDF and wrap to KDP Print Previewer.
- Replace the placeholder ISBN language if a purchased ISBN is used.
- Confirm metadata, categories, keywords, rights, territories, and price.
- Select **AI-generated text: Yes** under KDP's current disclosure rule.
- Order and inspect a physical proof before publishing.

No KDP upload was attempted.
