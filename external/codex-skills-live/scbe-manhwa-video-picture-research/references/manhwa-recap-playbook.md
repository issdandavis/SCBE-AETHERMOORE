# Manhwa Recap Playbook

## Production Targets
- Working canvas: 1600 px wide
- Export width: 800 px
- Typical episode density: 40-60 panels
- Gutter pacing:
  - 50 px: fast beats
  - 140 px: normal dialogue pacing
  - 400 px+: dramatic pause or reveal
- End episodes on a cliffhanger.

## Character Consistency Stack
1. Train LoRA with 10-30 high-quality character images.
2. Use IPAdapter for identity anchoring from reference art.
3. Use ControlNet OpenPose to lock body language and action continuity.
4. Orchestrate in ComfyUI with fixed seed ranges for recurring cast.

## Audio Mix Targets
- Narration target: -18 to -22 LUFS
- Music bed: 10-15 dB below narration (often -30 to -25 LUFS)
- EQ carve: reduce 2-4 kHz in music so narration remains clear
- SFX: punctuate transitions and impacts; avoid continuous SFX wash

## Motion Strategy
- Default: Ken Burns / zoompan for panel-to-video conversion
- Hero moments: 2.5D parallax shots
- AI-generated motion: use only for selected shots where style drift is acceptable

## Output Formats
- Shorts/TikTok: 1080x1920 @ 30fps
- YouTube long-form: 1920x1080 @ 24fps
