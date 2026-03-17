---
name: scbe-art-generator
description: Generate visual assets for the SCBE/Aethermoore project — manhwa panels, character sheets, website hero images, social media cards, product diagrams, and marketing banners. Use when creating any visual content for the project.
---

# SCBE Art Generator

Generate visual assets across the full spectrum: narrative manhwa art, marketing materials, and technical diagrams.

## Image Generation Backends

| Backend | Best For | Script |
|---------|----------|--------|
| HF Inference (FLUX.1-schnell) | Manhwa panels, character sheets | `scripts/gen_ch01_panels.py` |
| Grok Image Gen | Quick concept art, style tests | `scripts/grok_image_gen.py` |
| Local Pillow/FFmpeg | Compositing, strips, video | `scripts/assemble_manhwa_strip.py` |

## Manhwa Character Art

Existing pipeline for narrative panels and character sheets:
- Scene definitions in script dicts (extensible per chapter)
- 800px wide vertical webtoon format, sliced to 1280px max per segment
- Characters: Marcus Chen, Polly, Kael Nightwhisper (see `spiralverse_canon.md`)

## Website and Marketing Assets

### Landing Page Hero Images

Dark tech aesthetic with SCBE visual language. Use for landing pages, README headers, pitch decks.

**Prompt template — Poincare Disk Visualization:**
```
A dark futuristic visualization of a Poincare disk model, glowing cyan and
violet geodesic lines curving inward on a black background, faint hexagonal
lattice overlay, particles flowing along hyperbolic paths toward a central
bright node, cinematic lighting, 16:9 aspect ratio, ultra-detailed digital art,
no text, no watermark
```

**Prompt template — Lattice Defense Wall:**
```
Abstract visualization of a 14-layer security pipeline, concentric geometric
shells radiating outward from a glowing core, each layer a different hue from
deep violet to electric blue to gold, crystalline lattice connections between
layers, dark void background with faint star field, hyper-detailed sci-fi
concept art, 16:9, no text
```

**Prompt template — Sacred Tongues Tokenizer:**
```
Six interconnected glowing spheres arranged in a golden-ratio spiral, each a
different color (crimson, amber, teal, violet, silver, gold), thin luminous
filaments connecting them in a 6D web, dark background with subtle geometric
patterns, abstract data visualization style, 16:9, no text, no watermark
```

### Social Media Cards (1200x630 for Twitter/LinkedIn)

Designed for Open Graph previews and social sharing.

**Prompt template — Product Announcement Card:**
```
Wide banner image, dark gradient background from midnight blue to black,
geometric lattice pattern fading into the edges, central glowing orb with
concentric defense rings, subtle circuit-board traces in the background, clean
modern tech aesthetic, 1200x630 pixels, no text, no watermark
```

**Prompt template — Blog Post Header:**
```
Abstract digital art header, flowing data streams in cyan and magenta converging
on a hyperbolic surface, dark background, soft bokeh particles, futuristic
minimalist style suitable for a tech blog header, 1200x630, no text
```

**Prompt template — Launch/Event Card:**
```
Dramatic wide-angle view of a geometric fortress made of translucent hexagonal
panels, glowing from within with warm gold light, set against a deep space
background with nebula colors, epic sci-fi key art, 1200x630, no text
```

### Product and Architecture Diagrams

For technical documentation, pitch decks, and README visuals.

**Prompt template — Architecture Overview:**
```
Isometric technical diagram style illustration, a vertical stack of 14
translucent platform layers connected by glowing data conduits, each layer a
different shade from violet at bottom to gold at top, clean white background
with subtle grid, modern infographic aesthetic, no text, no watermark
```

**Prompt template — Agent Swarm Visualization:**
```
Top-down view of a network of autonomous agents represented as glowing nodes
in a dark space, connected by pulsing data lines, a central shepherd node
larger and brighter, smaller worker nodes arranged in clusters, particle
effects along connections, dark background, technical visualization style,
no text
```

**Prompt template — Governance Pipeline Flow:**
```
Abstract flowchart visualization, data flowing left to right through colored
gates (green ALLOW, yellow QUARANTINE, orange ESCALATE, red DENY), each gate
a geometric archway with scanning beams, dark environment with volumetric
lighting, clean sci-fi UI aesthetic, 16:9, no text
```

## Post-Processing Workflow

1. Generate raw image with backend of choice.
2. Resize/crop to target dimensions (Pillow or ImageMagick).
3. For social cards: leave bottom-right 300x100 clear for text overlay.
4. For hero images: ensure focal point is center-weighted for responsive cropping.
5. Export as WebP (quality 90) for web, PNG for print/pitch decks.

```python
from PIL import Image

# Resize for social card
img = Image.open("raw_hero.png")
card = img.resize((1200, 630), Image.LANCZOS)
card.save("social_card.webp", quality=90)
```

## Output Locations

| Asset Type | Directory |
|------------|-----------|
| Manhwa panels | `artifacts/manhwa/` |
| Hero images | `artifacts/marketing/hero/` |
| Social cards | `artifacts/marketing/social/` |
| Architecture diagrams | `artifacts/marketing/diagrams/` |
| Style tests | `artifacts/manhwa/style_tests/` |

## Guardrails

1. All generated images must be no-text, no-watermark unless explicitly adding branded text in post-processing.
2. Maintain consistent color palette: midnight blue, cyan, violet, gold, crimson.
3. Never generate images depicting real people.
4. Keep prompt templates versioned -- when a prompt produces good results, save it to `artifacts/marketing/prompt_log.jsonl`.
