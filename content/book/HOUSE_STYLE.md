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

## What This Book Is

A fun adventure about family-building, presented through the analytical mind of a burnt-out systems engineer who falls through reality and finds the people he didn't know he was missing. The technical layer is real. The danger is real. But the reason Marcus stays is not the system — it is the people. Domestic endings are not lesser endings. Home-building beats empire-building. The deepest truth in the book is two people walking through a garden after a festival.

The world's deeper reasons for existing the way it does — Izack's Everweave origins, the four-generation Spiralverse, Clay's creation on the beach, the Third Thread, the Codex Eternis — exist beneath the surface like bedrock. The book doesn't need to explain all of it. The characters carry it.

## Voice & POV

- **POV**: Third person limited, anchored to Marcus Chen
- **Tense**: Past
- **Narrator voice**: Dry, sardonic, engineering-brained, funnier than it means to be. Sentence rhythm varies — short punchy fragments for tension, long flowing sentences for wonder/description. The humor is never optional. Even in the darkest chapters, Marcus is coping through observation and wit.
- **Internal thought**: Italics, no "he thought" tag. `*I intend to understand.*`
- **Polly's dialogue**: Sharp, sarcastic, warm underneath. Bird body-language tells (feather-smoothing = softening, storm-flatten = distress, corvid head-tilt = curiosity). She has been doing this for five hundred years and she still cares enough to be annoyed.
- **Technical concepts**: Always grounded in sensory metaphor first, named second. Reader should feel it before they understand it. Marcus notices systems; natives see magic. Both are true. Neither should flatten the other.
- **Humor**: The book's engine. Marcus uses it to manage fear. Polly uses it to manage centuries of grief. Bram uses it to manage infrastructure. The humor makes the wonder survivable and the danger bearable. Without it, this is a textbook.

---

## Character Style Notes

### Marcus Chen — The Engineer
- Engineer brain narrates everything as system analysis, but the best moments are when the analysis fails and the feeling lands anyway
- Drinks dead coffee. Eats badly. Lives in his own head. Hasn't been home since Thursday.
- Casual internal voice: "Gotchu," "void-pit-thing," "Fine. He'd had worse Saturdays," "My LinkedIn is not prepared for this career pivot."
- Threat assessment runs on autopilot even when terrified
- Stays not because he can't leave, but because he chose to. The choice matters more than the system.
- He is having fun. Even when scared. Part of him is delighted.

### Polly (Polivara Kwevara) — The Keeper
- **True form**: Raven. Graduation cap, monocle, bowtie. This is her real shape.
- **Humanoid form**: Winged girl, obsidian eyes, feather-hair. An adaptation for communicating with refugees.
- **First appearance (Ch1)**: Raven on shelf, full academic regalia. Speaks as raven. Shapeshifts to humanoid to pull Marcus up ("Easier this way. Hands are useful.")
- **Transformation**: Casual, not dramatic — "unfolding, like a window being resized." Accessories de-render. Eyes stay the same.
- Raven form = relaxed, comfortable, familiar territory
- Humanoid form = business, needs hands, formal situations
- Obsidian eyes stay the same in both forms (the tell)
- "Caw-fee?" — doesn't know Earth things, parses them phonetically
- 500+ years old. Has seen dozens of refugees. Still cares enough to be annoyed.
- Her grief for Izack appears as precision, not collapse. Her hope for Marcus appears as proximity, not declaration.
- The sleep-caw is canon. She settled six inches from his outstretched hand the first night.

### The Architect (Izack Thorne)
- Referenced, not present (yet). Built the current governance system because he believed magic was communication, not domination.
- In the deeper lore: elven warlock, displaced by experiment failure, met Polly in a cave as co-equal, married Aria, planted the World Tree, created Clay from sand and need on a beach. His philosophy became the six tongues. His sacrifice became the substrate.
- Quotes carved into walls. Pipe smoke carrying equations. Untouched tea.
- Polly reacts physically (feathers storm-flatten) when he's mentioned.
- He is not tragic. He is load-bearing. Those are different things.

### Kael Thorne — The Spiral-Walker
- Izack's youngest son. Not villain — reformer with the wrong architecture.
- The "almost beautiful" routing pattern in Ch 1 is the first seed.
- The empty seventh pedestal in Ch 2 is the second seed.
- Right about the gap at 14. Weaponized by handlers at 16. Erasure, not death.
- His code is still running in the infrastructure — not malware, but unfinished work.
- Redemption arc, not villain arc. His understanding became a vulnerability.

### Senna Thorne — Continuity
- Youngest daughter. Carries the family, the Council, the system. Left hand adjusts right cuff — the leak in the armor.
- Her composure cracks not into vulnerability but into the person the composure was built to protect.
- The romance with Marcus is slow, subtle, earned. A tilt of the mouth. A garden walk at the end.

### Bram Cortez — Infrastructure
- Big, gruff, technically precise. Treats systems like living things, people like field conditions until proven otherwise.
- "I hate how useful you are already" = highest compliment.
- Swears in Draumric. Best maintenance coffee in the routing basement.

### Alexander Thorne — The Steady One
- Eldest. Chose the outer ring because staying would have turned grief structural.
- Warm, unhurried, dirt on cuffs. Asks the right questions and listens with his whole body.
- The brother Marcus never had. Festival lights are their bonding scene.

### Aria Ravencrest Thorne — The Boundary
- Izack's wife. The reason the world stayed standing. Gardening clothes, copper braids, dirt under nails.
- "Neither of you was right. Both of you were necessary" — the World Tree's first words, revealed through Aria.

### Lyra Thorne — Probability
- Materializes at the optimal moment for maximum embarrassment. Delivers truth disguised as teasing.
- "The gate is not blushing. You are."

### Mira Thorne — The Verdant Tithe
- Chose silence. Speaks in scalpels disguised as gentleness.
- Names what Marcus and Senna are avoiding before they can name it themselves.

### The Clay Rule
- Clay (Clayborn in the book) is the first creation — made from sand and need on a beach.
- Proof that need can create personhood. Proof that collaboration produces life, not just power.
- If the magic wouldn't make room for Clay to exist, the scene has drifted too far toward sterile system language.

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
