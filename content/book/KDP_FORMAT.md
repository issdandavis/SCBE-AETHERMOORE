# KDP Formatting Runbook

This project keeps source chapters in `content/book/source/` and emits KDP manuscript bundles through:

`scripts/book/build_kdp_manuscript.py`

## Quick Build

Build reader edition through Chapter 15:

```powershell
python scripts/book/build_kdp_manuscript.py --edition reader --max-chapter 15
```

Build annotated edition through its current cutoff (Chapter 6):

```powershell
python scripts/book/build_kdp_manuscript.py --edition annotated --max-chapter 6
```

Build with conversion targets (requires `pandoc` in `PATH`):

```powershell
python scripts/book/build_kdp_manuscript.py --edition reader --max-chapter 15 --pandoc-docx --pandoc-epub
```

## Outputs

Per edition, files are written to:

`artifacts/book/kdp/<edition>/`

- `six-tongues-protocol-<edition>-print.md`
- `six-tongues-protocol-<edition>-ebook.md`
- `build-metadata.json`
- Optional: `*.docx` and `*.epub` when pandoc flags are used

`build-metadata.json` includes:

- chapter count included
- total words
- estimated print pages at 275 words/page
- per-section word counts

## KDP Upload Notes

- Print trim target: `5.5 x 8.5 in` (from `HOUSE_STYLE.md`)
- Use the `*-print.docx` output for paperback upload
- Use the `*.epub` output for Kindle ebook upload
- Keep print and ebook editions aligned to the same chapter cutoff (`--max-chapter`)
- Re-run the builder after any chapter or appendix edit

## Recommended Current Command

```powershell
python scripts/book/build_kdp_manuscript.py --edition reader --max-chapter 15 --pandoc-docx --pandoc-epub
```
