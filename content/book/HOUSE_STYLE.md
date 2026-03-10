# The Six Tongues Protocol — House Style Guide

**Author**: Issac Davis
**Series**: SCBE-AETHERMOORE
**Copyright**: 2026 Issac Daniel Davis
**Patent**: USPTO Provisional #63/961,403

---

## Editions

### Reader Edition
Clean fiction. No technical annotations inline. Reads as a novel.
- Front matter: title page, copyright, dedication, epigraph, TOC
- Body: chapters with scene breaks (centered `* * *`)
- Back matter: acknowledgments, about the author, series note
- No SCBE Layer Notes anywhere in the text

### Annotated Edition
Same fiction body + endnotes per chapter mapping story to SCBE architecture.
- Same front/back matter as Reader Edition
- Adds: "Notes on the Architecture" appendix at the end
- Each chapter's notes appear as a numbered appendix entry
- Inline superscript markers in the text point to endnotes (e.g., "the Protocol verified his existence^1")
- Notes written for technical readers who want the mapping

---

## Trim & Layout (Print)

| Parameter | Value |
|-----------|-------|
| Trim size | 5.5 x 8.5 in (US Trade) |
| Inside margin | 0.75 in |
| Outside margin | 0.5 in |
| Top margin | 0.75 in |
| Bottom margin | 0.75 in |
| Font (body) | Garamond or Palatino, 11pt |
| Font (chapter titles) | Same family, small caps, 18pt |
| Line spacing | 1.15 |
| First line indent | 0.3 in (no indent after scene break or chapter start) |
| Scene break | `* * *` centered, extra space above/below |
| Chapter start | new page, drop cap or small caps first line, title centered |
| Page numbers | centered bottom, no number on chapter-start pages |
| Headers | author name (verso), book title (recto), no header on chapter starts |

## Trim & Layout (Ebook/EPUB)

| Parameter | Value |
|-----------|-------|
| Body text | Default (no forced font/size — reflowable) |
| Chapter breaks | Page break before each chapter |
| TOC | Hyperlinked, auto-generated from headings |
| Scene breaks | `* * *` centered |
| No forced page numbers | Reflowable text only |
| Images | None in v1 (text-only) |

---

## Typography Rules

- **Em dashes**: `--` in markdown source, rendered as `—` in output. No spaces around em dashes.
- **Ellipsis**: Three periods with no spaces `...`
- **Italics**: `*word*` for emphasis, internal thought, foreign words (Sacred Tongue phrases)
- **Bold**: Never used in body text. Reserved for chapter titles and front matter only.
- **Quotes**: Straight quotes in markdown, curly/smart quotes in output.
- **Numbers**: Spelled out below 100. Exceptions: times (3:14 AM), line numbers, technical measurements.

---

## Voice & POV

- **POV**: Third person limited, anchored to Marcus Chen
- **Tense**: Past
- **Narrator voice**: Dry, sardonic, engineering-brained. Sentence rhythm varies — short punchy fragments for tension, long flowing sentences for wonder/description.
- **Internal thought**: Italics, no "he thought" tag. `*I intend to understand.*`
- **Polly's dialogue**: Sharp, sarcastic, warm underneath. Bird body-language tells (feather-smoothing = softening, storm-flatten = distress, corvid head-tilt = curiosity).
- **Technical concepts**: Always grounded in sensory metaphor first, named second. Reader should feel it before they understand it.
- **Humor**: Coping mechanism. Marcus uses it to manage fear. Polly uses it to manage centuries of grief.

---

## Character Style Notes

### Marcus Chen
- Engineer brain narrates everything as system analysis
- Drinks dead coffee. Eats badly. Lives in his own head.
- Casual internal voice: "Gotchu," "void-pit-thing," "Fine. He'd had worse Saturdays."
- Threat assessment runs on autopilot even when terrified

### Polly (Polivara Kwevara)
- **True form**: Raven. Graduation cap, monocle, bowtie. This is her real shape.
- **Humanoid form**: Winged girl, obsidian eyes, feather-hair. An adaptation for communicating with refugees.
- **First appearance (Ch1)**: Raven on shelf, full academic regalia. Speaks as raven. Shapeshifts to humanoid to pull Marcus up ("Easier this way. Hands are useful.")
- **Transformation**: Casual, not dramatic — "unfolding, like a window being resized." Accessories de-render. Eyes stay the same.
- Raven form = relaxed, comfortable, familiar territory
- Humanoid form = business, needs hands, formal situations
- Obsidian eyes stay the same in both forms (the tell)
- "Caw-fee?" — doesn't know Earth things, parses them phonetically
- 500+ years old. Has seen dozens of refugees. Still cares enough to be annoyed.

### The Architect (Izack Thorne)
- Referenced, not present (yet). Built the current governance system.
- Quotes carved into walls of the Deep Library.
- Polly reacts physically (feathers storm-flatten) when he's mentioned.

### Kael Thorne
- Izack's son. Not yet introduced in expanded chapters.
- The "almost beautiful" routing pattern in Ch 1 is the first seed.
- The empty seventh pedestal in Ch 2 is the second seed.
- Redemption arc, not villain arc. His understanding became a vulnerability.

---

## Scene Break Convention

Within a chapter, time/location shifts use:

```
* * *
```

Major section breaks (e.g., Earth → Aethermoor transit in Ch 1) use:

```
---
```

---

## Sacred Tongue Rendering

When characters speak in Sacred Tongues:
- Phrase in italics: *"Kor'shael lumenis."*
- Translation immediately after in normal text, indented or as narrator gloss
- No footnotes in Reader Edition for tongue phrases — the universal translation handles it narratively

---

## File Structure

```
content/book/
  HOUSE_STYLE.md              # This file
  source/                     # Markdown master files (both editions derive from these)
    front-matter.md
    ch01-protocol-handshake.md
    ch02-the-language-barrier.md
    ...
    back-matter.md
    appendix-architecture-notes.md
  reader-edition/             # Clean fiction output
    ch01.md
    ch02.md
    ...
  annotated-edition/          # Fiction + endnotes
    ch01.md
    ch02.md
    ...
    appendix.md
```

Source files are the single point of truth. Reader and annotated editions are derived outputs.
