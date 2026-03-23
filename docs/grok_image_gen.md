# SCBE Image Generator Guide

## Overview

`scripts/grok_image_gen.py` is now a multi-backend image router.

Despite the filename, it is not a Grok-specific generator. It currently routes across:

1. `imagen-ultra` — Google Imagen 4.0 Ultra
2. `imagen` — Google Imagen 4.0 Standard
3. `hf` — Hugging Face hosted `black-forest-labs/FLUX.1-schnell`
4. `zimage` — Hugging Face hosted SDXL Turbo

Auto-pick order is:

`imagen-ultra -> imagen -> hf -> zimage`

That matches the current production rule for manhwa work:

- `imagen-ultra` for hero panels, reveals, and establishing shots
- `imagen` for batch panels, breathing panels, and detail coverage
- `hf` / `zimage` as fallback lanes, not the primary quality path

## Requirements

- `GEMINI_API_KEY` for Imagen Standard and Ultra
- `HF_TOKEN` for Hugging Face FLUX and Z-Image lanes

Check current availability:

```powershell
python scripts/grok_image_gen.py --check
python scripts/grok_image_gen.py --list-backends
```

## Usage

Basic auto-pick:

```powershell
python scripts/grok_image_gen.py --prompt "manhwa webtoon panel, exhausted engineer at a desk" -o artifacts/generated/desk.png
```

Force Imagen Ultra:

```powershell
python scripts/grok_image_gen.py --backend imagen-ultra --aspect 3:4 --prompt "manhwa webtoon panel, over-the-shoulder night desk, curved monitor, amber lamp, city skyline" -o artifacts/generated/desk-ultra.png
```

Force Imagen Standard:

```powershell
python scripts/grok_image_gen.py --backend imagen --aspect 3:4 --prompt "macro coffee mug with residue ring, green terminal reflection, dark wood desk" -o artifacts/generated/coffee-standard.png
```

Force Hugging Face FLUX fallback:

```powershell
python scripts/grok_image_gen.py --backend hf --prompt "manhwa webtoon panel, crystal archive corridor, warm amber light" -o artifacts/generated/archive-flux.png
```

## Important Constraints

- `--reference` is not fully wired yet. The script now fails closed instead of pretending reference-guided consistency is working.
- There is no seed flag in the current router. If deterministic or image-to-image continuity is needed, that must be added explicitly rather than assumed.
- This script does not replace the structured `webtoon_gen.py` packet flow. Use it for direct image generation lanes, spot tests, or quick panel experiments.

## Recommended Manhwa Workflow

1. Use the governed storyboard and prompt packet flow first.
2. Use `imagen-ultra` for hero panels only.
3. Use `imagen` for batch generation.
4. Treat Gemini image edit as surgical fix-only, not general enhancement.
5. Do not claim consistency features that are not implemented in code.

## Troubleshooting

- If Imagen backends show missing, export `GEMINI_API_KEY`.
- If Hugging Face backends show missing, export `HF_TOKEN`.
- If a prompt works in Standard but not Ultra, keep the prompt and only change backend first before rewriting the composition.
