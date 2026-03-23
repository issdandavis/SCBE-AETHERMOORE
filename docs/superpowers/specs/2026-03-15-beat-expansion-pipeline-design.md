# Beat Expansion Pipeline — Ch01 Proof-of-Work

**Date:** 2026-03-15
**Status:** Approved
**Approach:** B+ (Beat Expansion with Layout-First Storyboarding)

## Core Insight

The current 30-panel ch01 reads like a slide deck summarizing the book, not like reading the book. Each panel is a standalone illustration of a plot point. What's missing is the connective tissue — the multiple mental images a single line of prose produces.

"The screen went white" isn't one image. It's Marcus's eyes widening, the monitor flaring, the white eating the desk, his hands disappearing. Sequential art IS multiple images per moment.

## The Rule

Each moment gets as many frames as it takes to feel smooth. No fixed counts per beat type. Read the prose, see what it shows you, draw that. Panel SIZE carries the emotion — small panels for speed and intimacy, full-bleed for impact and awe, gaps for silence.

## Pipeline

### Stage 1: Frame Script
Read ch01 line by line. For each moment, write out every mental image the prose produces. No filtering, no constraints. The book IS the script. Output: `ch01_frame_script_v4.md` — a flat list of frames with size hints and emotional role.

### Stage 2: Layout Blueprint
Convert the frame script into a JSON shot list with pixel dimensions and gap values per frame. This can be done in code or optionally previewed in Figma/Canva. The output is `ch01_layout_blueprint.json` — consumable by the generation and assembly stages.

### Stage 3: Generation
Generate images to fit the blueprint. Model routing follows the manhwa-cinematic-forge skill's rules (standard for batch/detail, Ultra for hero/establishing/splash). Each prompt knows its dimensions and its neighbors. Existing `scripts/gen_ch01_v3_full.py` and the forge skill are the implementation foundation.

### Stage 4: Assembly
Compose into the final vertical strip with PIL/Canva. Gutters, gaps, text overlays, SFX.

### Stage 5: Iterate
Look at what reads well. Regen the weak frames. Repeat until it reads like the book. Drawing is recursive refinement — rough pass, refine, refine, converge.

## Visual Anchor

The book cover is the reader's only visual reference: Marcus from behind, green monitor glow, coffee mug, dark office, city through the window. Tech-noir, grounded. Everything else — Polly, crystal library, Aethermoor — exists only in the reader's imagination from the prose.

## Scope

- Ch01 is the proof-of-work. **This supersedes the roadmap's 12-16 panel target for ep01.**
- Frame count: as many as it takes (estimated 80-120)
- Layout tools: JSON shot list (code-native), optionally Figma/Canva for visual preview
- Generation: Imagen 4.0 + Ultra for hero frames (see manhwa-cinematic-forge for routing)
- Storage: ~100-150MB per chapter at current resolution. For multi-chapter rollout, assemble final strips then clean raw panels, or push completed chapters to cloud before starting the next. 5.8GB free means one chapter at a time.
- Once ch01 is validated, the process applies to the other 42 episodes

## Coordination

Codex is running parallel on:
- LoRA training prep (consistency system)
- Character/environment swatch sheets
- Image consistency operating doc

This spec covers the narrative pipeline — what to generate and how to arrange it. Codex's consistency work covers how to make it look coherent across frames.

## What Success Looks Like

You scroll through ch01 and it feels like reading the book. You feel the stale coffee, the white-out creeps across multiple panels, Polly's "We have infrastructure" hits like a reveal, and the Aethermoor reveal takes your breath after a long silent gap.
