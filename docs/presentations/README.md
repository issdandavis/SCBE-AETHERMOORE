# Presentations

Marp-format Markdown sources for voice-over-friendly slide decks.

## Files

- `SYSTEMS_BLUEPRINT.md` — full 18-slide walkthrough of the SCBE-AETHERMOORE
  systems architecture (problem → 14-layer pipeline → axioms → Sacred Tongues
  → fleet → PUF → adversarial cost → federal/commercial path → contact). Each
  slide carries speaker notes in HTML comments; voice-over should follow the
  notes, not the on-slide bullets.

## Why Marp

Marp is Markdown + YAML frontmatter that renders to slides. One source file,
multiple output formats:

- HTML (best for browser-based voice-over recording with OBS / Loom)
- PDF (best for handout / leave-behind / SAM.gov filings)
- PPTX (best when the audience explicitly asked for PowerPoint)

The source is plain text, version-controlled, and the Mermaid diagrams render
inline without any external image files to manage.

## Render

### Easiest — VS Code preview
Install the **Marp for VS Code** extension. Open the `.md` file. Right-click
the editor, "Open Preview to the Side." Edit / preview live. Use the export
icon in the preview pane to save HTML / PDF / PPTX.

### CLI (one-time install)

```powershell
npm install -g @marp-team/marp-cli
```

Then from the repo root:

```powershell
# HTML (interactive — best for voice-over recording)
marp docs/presentations/SYSTEMS_BLUEPRINT.md -o docs/presentations/build/SYSTEMS_BLUEPRINT.html

# PDF (handout)
marp docs/presentations/SYSTEMS_BLUEPRINT.md --pdf -o docs/presentations/build/SYSTEMS_BLUEPRINT.pdf

# PPTX (PowerPoint)
marp docs/presentations/SYSTEMS_BLUEPRINT.md --pptx -o docs/presentations/build/SYSTEMS_BLUEPRINT.pptx

# All three at once
marp docs/presentations/SYSTEMS_BLUEPRINT.md --html --pdf --pptx -o docs/presentations/build/SYSTEMS_BLUEPRINT
```

### Mermaid in PPTX export

Marp's PPTX exporter rasterizes Mermaid diagrams to PNG inside the slide.
Quality is good but the diagrams become images, not editable shapes.

If you want editable PowerPoint shapes (rare), use the HTML export, screenshot
the Mermaid panel, and paste into PowerPoint manually. Most voice-over flows
don't need editable shapes.

## Voice-over recording

Recommended: open the HTML build in Chrome, open OBS, capture the browser
window, hit record, advance through slides reading from the speaker notes.

The speaker notes are inside `<!-- ... -->` HTML comments on every slide.
They're not visible in the rendered slide but they ARE visible in the source
markdown if you have it open in a second window.

Marp HTML also has a presenter view: press `p` in the slide deck to open a
second window with current slide, next slide, and speaker notes side by side.
Record the main window; read from the presenter window.

## Editing

The whole deck is one `.md` file. Each `---` is a slide break. Edit the
markdown, save, the preview updates live in VS Code. No need to touch
PowerPoint.

If you want to add a slide:
1. Add a new `---` separator
2. Write the slide content in markdown
3. Add `<!-- SPEAKER NOTES: ... -->` at the bottom

If you want to remove a slide:
1. Delete from the `---` above it through the `---` below it

If you want to reorder slides:
1. Cut and paste the entire slide block including its `<!-- -->` notes

## Themes

The deck uses Marp's built-in `default` theme with light style overrides in
the YAML frontmatter (`style: |` block). To change the look, edit the `theme:`
field. Built-in alternatives: `default`, `gaia`, `uncover`. For something
heavier, add a custom CSS file and reference it.

## License / OPSEC

This deck is public-facing. It re-states what's already in the public
capability statement, README, and patent claims documentation. Do NOT add
slides about:

- Pricing specifics for commercial customers (those go in private quotes)
- Identifiable customer names (until they sign a logo-use agreement)
- DARPA proposal interior content (the abstracts are the limit of what's
  cleared for public discussion until awarded)
- Any personal financial information

If a planned voice-over edit would introduce one of those, the deck moves to
SCBE-private when that exists; until then, keep it public-safe.
