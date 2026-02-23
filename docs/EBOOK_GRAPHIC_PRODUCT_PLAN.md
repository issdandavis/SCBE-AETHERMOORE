# E-Book Graphic Product Plan (Hand-Painted Grim-Dark, Kid-Safe)

## Positioning
- Format: illustrated short e-books + printable art plates.
- Visual direction: old-school hand-painted look, grim-dark atmosphere, still age-appropriate.
- Audience: kids/teens + parents + fantasy worldbuilding fans.

## Product Stack
1. Starter e-book (20-40 pages)
- Story + 8-12 full-page illustrations.

2. Lore Companion PDF
- Character cards, map sheet, symbol guide.

3. Print Pack
- 8 printable plates (A4/Letter), grayscale + color variants.

## Guardrails (important)
- Keep themes non-explicit, no graphic violence.
- Emphasize courage, mystery, teamwork, and consequences.
- Use a content rating line on each listing.

## Folder Layout
- `products/ebooks/<title>/manuscript/`
- `products/ebooks/<title>/art/`
- `products/ebooks/<title>/exports/`
- `products/ebooks/<title>/listing/`

## Listing Bundle Checklist
- Cover image (1:1 + 16:9)
- Product description (short + long)
- 5 preview images
- EPUB/PDF export
- Keywords/tags

## Automation Fit
- Use `xops:run` queue items for:
  - launch post
  - reply engagement
  - merch action checks
- Use `scripts/polly_clay_squad.py` if you want browser-governed product page validation before posting.
