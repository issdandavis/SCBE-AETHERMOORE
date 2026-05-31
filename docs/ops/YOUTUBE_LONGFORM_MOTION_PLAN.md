# YouTube Longform Motion Plan

## What The Current Pipeline Does

The existing article video pipeline is mostly a narrated slide composer:

```text
markdown article
-> parse title, code blocks, sections
-> split text into narration segments
-> generate TTS per segment with Kokoro or Edge TTS
-> draw static slides with Pillow
-> hold each slide for the segment duration
-> compose MP4 with FFmpeg
```

Main script:

```text
scripts/publish/article_to_video.py
```

Long chapter/audiobook variant:

```text
scripts/publish/chapter_video_pipeline.py
```

That means the videos can already be long, but the visual layer is mostly still
images.

## Why It Looks Static

The current renderer stores:

- narration audio,
- slide PNGs,
- segment durations,
- thumbnail PNG,
- final MP4.

It does not yet store:

- scene state,
- camera movement,
- character/body poses,
- per-beat animation,
- control frames,
- visual continuity checks.

## Upgrade Ladder

### Level 1: Better Still Videos

Keep the current slide architecture but improve packaging.

- stronger first 10 seconds,
- more deliberate chapter cards,
- better outro,
- captions,
- thumbnail variants,
- tail review before upload.

This is cheap and should remain the baseline.

### Level 2: Moving Slides

Turn slides into motion without changing content generation.

Add:

- slow zoom,
- pan,
- parallax background,
- animated accent lines,
- code typing reveal,
- waveform or subtitle pulse,
- section transition cards.

This can be done with Pillow frame generation or FFmpeg filters. It is the
lowest-cost way to make existing videos feel less static.

### Level 3: Beat Storyboards

For each narration segment, create a storyboard beat:

```text
segment text
-> visual intent
-> scene type
-> objects/entities
-> camera motion
-> control sketch
-> rendered clip
```

This is where `src/video_lattice/` starts mattering.

Use:

- `tiny_engine.py` for compact pocket worlds,
- `sketch_pad.py` for SVG/PNG control sketches,
- `pose_polygons.py` for bodies/hands,
- `temporal_tracker.py` for visual drift,
- `frame_corrector.py` for repair signals.

### Level 4: Pocket-Dimension Engine Videos

Instead of generating arbitrary visuals, the AI operates a small symbolic world:

```text
pocket world state
-> AI/world director proposes delta
-> lattice scores coherence
-> best delta wins
-> world renders SVG/PNG frame
-> FFmpeg turns frames into clip
```

This borrows from old game design: store rules, tiles, sprites, and deltas
instead of raw pixels. It is much cheaper than neural video for every frame.

Current pieces:

- `src/video_lattice/tiny_engine.py`
- `src/video_lattice/gpt_world.py`
- `scripts/video_lattice/pocket_director_demo.py`

### Level 5: Hybrid Neural Video

Use the pocket engine and sketchpad as control inputs for AI video generation.

```text
script beat
-> pocket state
-> control sketch
-> image/video model clip
-> lattice visual check
-> accept or regenerate
```

This is where generated motion can become richer while still being grounded by
geometry and continuity checks.

## Practical Next Build

Build a `longform_motion_video.py` wrapper that accepts an article and produces
a richer package:

```powershell
python scripts/publish/longform_motion_video.py --file content/articles/ARTICLE.md
```

First version should:

1. reuse `article_to_video.py` parsing and TTS,
2. create a visual beat plan per segment,
3. generate motion frames from slides or pocket worlds,
4. compose with FFmpeg,
5. run `youtube_video_tool.py inspect`,
6. write a repair plan.

## Release Standard

For longform videos, minimum expected artifacts:

- final MP4,
- thumbnail,
- captions/transcript,
- description,
- frame sample manifest,
- tail clip,
- QA inspection JSON,
- optional control-frame manifest.

Longer videos are fine, but they need chapter structure and stronger QA because
small pacing problems compound over time.
