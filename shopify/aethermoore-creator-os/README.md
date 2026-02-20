# Aethermore Creator OS Theme

This theme is a UI shell for the SCBE/Aethermoore universe. It is intentionally split:

- Core truth: SCBE engine, governance, compliance
- Content truth: codex/lore/architecture docs
- Theme role: render, route intents, never compute policy

## Scaffold Included

- `layout/theme.liquid`
- `templates/index.json`
- `templates/product.json`
- `templates/page.codex.json`
- `templates/page.blueprint.json`
- `sections/hero-creator-os.liquid`
- `sections/codex-entry.liquid`
- `sections/blueprint-display.liquid`
- `sections/fractal-gallery.liquid`
- `sections/system-card-grid.liquid`
- `sections/protocol-timeline.liquid`
- `snippets/glyph-divider.liquid`
- `snippets/signed-zero-icon.liquid`
- `snippets/fractal-border.liquid`
- `snippets/parameter-readout.liquid`
- `snippets/soliton-visual.liquid`
- `assets/aether.css`
- `assets/aether.js`
- `assets/soliton.png`
- `assets/spiralverse-hero.png`
- `assets/spiralverse-field.png`
- `assets/protocol-diagram-001.png`
- `assets/protocol-diagram-002.png`
- `config/settings_schema.json`

## Pipeline Notes

- Dynamic content blocks: pull Notion pages into Shopify metafields, then render from section settings/blocks.
- Codex entries: auto-generate from source docs and publish to page templates.
- Asset pipeline: upload, resize, optimize, attach media to products.

