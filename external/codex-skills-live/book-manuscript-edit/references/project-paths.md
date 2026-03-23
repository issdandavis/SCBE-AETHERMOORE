# Project Paths

## Source of Truth

- `C:\Users\issda\SCBE-AETHERMOORE\content\book\reader-edition\`
  - Primary chapter and interlude Markdown files.

- `C:\Users\issda\SCBE-AETHERMOORE\content\book\source\`
  - Alternate source edition files. Read before mirroring edits because the text may differ.

## Build and Sync Tools

- `C:\Users\issda\SCBE-AETHERMOORE\content\book\build_kdp.py`
  - Rebuild the KDP review DOCX.

- `C:\Users\issda\SCBE-AETHERMOORE\content\book\sync_docx_to_md.py`
  - Push LibreOffice DOCX edits back into Markdown.

- `C:\Users\issda\SCBE-AETHERMOORE\content\book\INDEX.md`
  - Controls book order and packaging context.

- `C:\Users\issda\SCBE-AETHERMOORE\content\book\HOUSE_STYLE.md`
  - Formatting and manuscript style rules.

- `C:\Users\issda\.claude\projects\C--Users-issda\memory\feedback_writing_style.md`
  - Issac voice notes for prose work.

## Generated Artifacts

- `C:\Users\issda\SCBE-AETHERMOORE\content\book\the-six-tongues-protocol-kdp.docx`
  - Main KDP review artifact.

- `C:\Users\issda\SCBE-AETHERMOORE\content\book\the-six-tongues-protocol-kdp.odt`
  - LibreOffice-adjacent artifact if needed for local review.

## Command Loop

Rebuild:

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
python content\book\build_kdp.py
```

Open in LibreOffice:

```powershell
start "" "C:\Program Files\LibreOffice\program\soffice.exe" --writer "C:\Users\issda\SCBE-AETHERMOORE\content\book\the-six-tongues-protocol-kdp.docx"
```

Reverse-sync from DOCX:

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
python content\book\sync_docx_to_md.py
```
