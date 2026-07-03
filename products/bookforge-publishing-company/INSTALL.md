# Install And Publish Path

## Recommended Buyer Path

1. Install Python 3.11+.
2. Install pandoc.
3. Optional but recommended: install MiKTeX on Windows or TeX Live on macOS/Linux
   for XeLaTeX typography.
4. Install BookForge.
5. Copy one profile from `profiles/` into the book folder as `bookforge.json`.
6. Put the manuscript beside it as `manuscript.md`.
7. Run `bookforge build`.
8. Upload the generated files to KDP and use KDP Print Previewer for final
   approval checks.

## Current Engine Status

The local engine is ready, but the public PyPI package must be published before
the simple `pip install scbe-bookforge` step works for customers.

Until then, use the built wheel included by the packager when available:

```powershell
pip install engine-dist\scbe_bookforge-0.1.0-py3-none-any.whl
```

## Pro Typography Path

`bookforge` can fall back to ReportLab for interior PDFs, but the strongest
selling point is the XeLaTeX path. Verify these tools before promising the pro
interior workflow:

```powershell
pandoc --version
xelatex --version
bookforge info bookforge.json
bookforge interior bookforge.json
```

