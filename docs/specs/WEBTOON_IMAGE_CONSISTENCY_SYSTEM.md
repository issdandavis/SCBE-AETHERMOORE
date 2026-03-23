# Webtoon Image Consistency System

This is the practical system for getting better image results consistently in the Six Tongues webtoon lane.

## Core Rule

Do not rely on prompt wording alone.

Consistency comes from five things used together:

1. one anchor chapter
2. one visual memory packet
3. one packet-level generation profile
4. locked character anchors and environment rules
5. one quality gate before render

In this repo, `ch01` is the anchor chapter.

## What Changed

The webtoon pipeline now supports a packet-level `generation_profile` that can carry:

- `model_id`
- `default_steps`
- `guidance_scale`
- `trigger_phrases`
- `style_adapter`

That means the prompt packet can now tell the generator:

- which base model to use
- which trigger phrase to prepend
- which LoRA adapter to load
- what default render settings to use

## Files That Matter

- [webtoon_gen.py](/C:/Users/issda/SCBE-AETHERMOORE/scripts/webtoon_gen.py)
- [webtoon_quality_gate.py](/C:/Users/issda/SCBE-AETHERMOORE/scripts/webtoon_quality_gate.py)
- [ch01_prompts.json](/C:/Users/issda/SCBE-AETHERMOORE/artifacts/webtoon/panel_prompts/ch01_prompts.json)
- [WEBTOON_CH01_VISUAL_MEMORY_PACKET.md](/C:/Users/issda/SCBE-AETHERMOORE/docs/specs/WEBTOON_CH01_VISUAL_MEMORY_PACKET.md)
- [train_art_lora_colab.py](/C:/Users/issda/SCBE-AETHERMOORE/scripts/train_art_lora_colab.py)

## Recommended Workflow

### 1. Repair and validate the packet

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
python scripts\webtoon_quality_gate.py --packet artifacts\webtoon\panel_prompts\ch01_prompts.json --auto-fix --rewrite-prompts --write-back --strict
```

This ensures the packet has:

- governed metadata
- compiled prompts
- generation profile defaults
- a readable visual memory packet

### 2. Dry-run the prompts before spending GPU time

```powershell
python scripts\webtoon_gen.py --batch artifacts\webtoon\panel_prompts\ch01_prompts.json --dry-run
```

Use this to confirm:

- the trigger phrase is present
- the prompt text reads correctly
- the manifest writes cleanly

### 3. Render locally with the packet profile

```powershell
python scripts\webtoon_gen.py --batch artifacts\webtoon\panel_prompts\ch01_prompts.json
```

If the packet contains a style adapter, the generator will try to load it automatically.

### 4. Force a specific adapter or trigger phrase

Use this when you want to override the packet or test a new model lane.

```powershell
python scripts\webtoon_gen.py --batch artifacts\webtoon\panel_prompts\ch01_prompts.json --adapter-repo issdandavis/six-tongues-art-lora --adapter-name six-tongues-style --adapter-scale 0.9 --trigger-phrase sixtongues_style --strict-adapter
```

### 5. Generate the LoRA training notebook

```powershell
python scripts\train_art_lora_colab.py
```

This now writes three artifacts:

- the Colab notebook
- a local JSON training plan
- a local Markdown report with weighting and dataset recommendations

The important rule is honest now:

- the current LoRA lane is a shared-trigger DreamBooth-style run
- anchor and hero images are weighted harder by repeated copies
- you should rerun the packet generator after every approved dataset wave

Useful override example:

```powershell
python scripts\train_art_lora_colab.py --target-effective-epochs 72 --quality-weight anchor=6 --quality-weight hero=5
```

Generated outputs:

- [six_tongues_lora_training.ipynb](/C:/Users/issda/SCBE-AETHERMOORE/artifacts/webtoon/six_tongues_lora_training.ipynb)
- [six_tongues_lora_training_plan.json](/C:/Users/issda/SCBE-AETHERMOORE/artifacts/webtoon/six_tongues_lora_training_plan.json)
- [six_tongues_lora_training_report.md](/C:/Users/issda/SCBE-AETHERMOORE/artifacts/webtoon/six_tongues_lora_training_report.md)

### 6. Assemble and review the chapter strip

```powershell
python scripts\assemble_manhwa_strip.py --chapter ch01 --prefer-hq
```

Then review the reader assets in:

- [kindle-app/www/manhwa/ch01/hq](/C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/manhwa/ch01/hq)
- [artifacts/manhwa/strips/ch01](/C:/Users/issda/SCBE-AETHERMOORE/artifacts/manhwa/strips/ch01)

### 7. Build a fine-edit packet for Canva or Adobe

Do this after a dry-run or a real render pass when a few panels are close but still need human cleanup.

```powershell
python scripts\build_manhwa_edit_packet.py --packet artifacts\webtoon\panel_prompts\ch01_prompts_v4.json --limit 6
```

If you already rendered through the router and want the packet to point at the real image outputs:

```powershell
python scripts\build_manhwa_edit_packet.py --packet artifacts\webtoon\panel_prompts\ch01_prompts_v4.json --manifest artifacts\webtoon\generated_router\ch01\ch01_prompts_v4_router_manifest.json --limit 6
```

Force a specific app lane when you already know the edit target:

```powershell
python scripts\build_manhwa_edit_packet.py --packet artifacts\webtoon\panel_prompts\ch01_prompts_v4.json --manifest artifacts\webtoon\generated_router\ch01\ch01_prompts_v4_router_manifest.json --only ch01-v4-p13 --app photoshop --edit-goal "Repair anatomy, lighting, and hand shape without changing the beat."
python scripts\build_manhwa_edit_packet.py --packet artifacts\webtoon\panel_prompts\ch01_prompts_v4.json --manifest artifacts\webtoon\generated_router\ch01\ch01_prompts_v4_router_manifest.json --only ch01-v4-p31 --app canva --edit-goal "Turn this into a thumbnail with readable title text and promo framing."
python scripts\build_manhwa_edit_packet.py --packet artifacts\webtoon\panel_prompts\ch01_prompts_v4.json --manifest artifacts\webtoon\generated_router\ch01\ch01_prompts_v4_router_manifest.json --only ch01-v4-p45 --app adobe-express --edit-goal "Prepare a social promo variant with quick layout cleanup."
```

The packet writes:

- `edit_packet.json`
- `edit_packet.md`
- `contact_sheet.html`

Use the app lanes like this:

- `photoshop` for paintover, anatomy repair, masking, relighting, and continuity cleanup
- `canva` for thumbnails, captions, poster layouts, speech bubble cleanup, and promo packaging
- `adobe-express` for fast social variants, template-driven presentation, and lightweight packaging edits

## Decision Rules

- Use the base model only for exploration and composition tests.
- Use the trigger phrase plus LoRA adapter for reference-chapter work.
- Treat `hq` as the review lane and `generated` as the draft lane.
- Do not promote a generated panel into canon unless it still matches the visual memory packet.

## What To Lock

Lock these across the active arc:

- Marcus face shape, hair, build, exhaustion cues
- Polly raven form props and eye treatment
- Polly human form eye treatment, feather-hair, wings, fingers
- Earth office lighting logic
- crystal archive lighting logic
- Aethermoor exterior geometry logic

Allow style flex only on purpose:

- comedy
- impact
- memory
- infographic overlays

## Failure Pattern To Avoid

If you skip the consistency profile, the model will usually drift in one of these ways:

- Marcus changes ethnicity or age
- Polly loses the academic-regalia identity
- crystal spaces become generic fantasy glow
- Earth scenes become generic cyberpunk
- spectacle panels overpower quieter beats

## Training Loop

Treat art training as a loop, not a one-time run:

1. generate or collect candidate images
2. keep only approved anchors, hero frames, and good panels
3. rerun `train_art_lora_colab.py`
4. train the adapter
5. render the eval prompts
6. promote only the runs that still match the memory packet

If you want more improvement, add better anchors first, not just more random renders.

## Short Version

Use this loop:

```powershell
python scripts\webtoon_quality_gate.py --packet artifacts\webtoon\panel_prompts\ch01_prompts.json --auto-fix --rewrite-prompts --write-back --strict
python scripts\webtoon_gen.py --batch artifacts\webtoon\panel_prompts\ch01_prompts.json --dry-run
python scripts\train_art_lora_colab.py
python scripts\webtoon_gen.py --batch artifacts\webtoon\panel_prompts\ch01_prompts.json --adapter-repo issdandavis/six-tongues-art-lora --adapter-name six-tongues-style --adapter-scale 0.9 --trigger-phrase sixtongues_style
python scripts\assemble_manhwa_strip.py --chapter ch01 --prefer-hq
```
