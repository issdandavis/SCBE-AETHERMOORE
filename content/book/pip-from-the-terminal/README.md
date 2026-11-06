# pip from the Terminal

Canonical source and KDP build project for a practical pip guide.

## Build

From the repository root:

```powershell
$env:PYTHONPATH = "$PWD\packages\bookforge\src"
python -m scbe_bookforge info content\book\pip-from-the-terminal\bookforge.json
python -m scbe_bookforge build content\book\pip-from-the-terminal\bookforge.json --no-cover
```

After the PDF page count is stable, set `page_count` in `bookforge.json`, then:

```powershell
python -m scbe_bookforge cover content\book\pip-from-the-terminal\bookforge.json --blurb content\book\pip-from-the-terminal\blurb.json
```

## Source of truth

- `manuscript.md`: publication text
- `SOURCES.md`: dated research ledger
- `bookforge.json`: format and metadata
- `kdp-metadata.md`: upload fields and disclosure notes
- `build/`: generated artifacts; never edit these by hand

The current draft was checked against Python 3.12.10 and pip 26.2.2 on
2026-10-28. Recheck volatile commands and KDP rules before every new edition.
