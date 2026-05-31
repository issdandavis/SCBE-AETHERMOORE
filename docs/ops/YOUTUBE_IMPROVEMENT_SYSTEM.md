# YouTube Improvement System

## Goal

Make every SCBE YouTube video pass a repeatable improvement loop before it goes
public:

1. package the video,
2. inspect media quality,
3. inspect script/transcript fit,
4. inspect thumbnail/title/description/tags,
5. inspect visual continuity,
6. repair the smallest failing piece,
7. upload unlisted,
8. publish only after human review.

## Current Repo Surfaces

- `scripts/publish/article_to_video.py`
  - turns articles into narrated faceless videos.
- `scripts/publish/youtube_video_tool.py`
  - pre-upload inspection, frame export, tail clips, upload planning.
- `scripts/publish/post_to_youtube.py`
  - direct YouTube upload.
- `scripts/youtube/package.js`
  - metadata package builder.
- `scripts/youtube/upload.js`
  - resumable YouTube uploader from a manifest.
- `scripts/apollo/video_review.py`
  - channel/video metadata review scoring.
- `src/video_lattice/`
  - visual continuity, pose/depth/geometry, sketch/control-frame testing.

## Quality Gates

### 1. Content Gate

The script should answer:

- Is the first 10 seconds clear?
- Does the viewer know why to keep watching?
- Is there one central promise?
- Does the ending land instead of stopping abruptly?
- Is there a natural subscribe/follow CTA?

Repair actions:

- rewrite the hook,
- split long paragraphs,
- add chapter beats,
- rewrite the final 20 seconds,
- add a pinned-comment prompt.

### 2. Audio Gate

The audio should pass:

- no missing audio stream,
- no end silence,
- no clipped peaks,
- natural pacing,
- voice matches topic mood,
- transcript/captions exist.

Repair actions:

- regenerate only the bad segment,
- add pauses between sections,
- normalize loudness,
- append fixed ending instead of rerendering the full video.

### 3. Visual Gate

The visual track should pass:

- no black or frozen frame sections,
- thumbnail exists and is readable,
- frames match the spoken topic,
- no severe anatomy drift for character/body videos,
- no severe depth/pose uncertainty where the viewer needs clarity.

Repair actions:

- export sampled frames,
- run lattice inspection,
- replace bad frames or sections,
- add control sketches for body/hand scenes,
- reduce style aggression when geometry is unstable.

### 4. Metadata Gate

The YouTube package should pass:

- title is specific and searchable,
- thumbnail matches the title promise,
- description has 2-4 useful paragraphs,
- tags are focused, not spammy,
- chapters exist for longer videos,
- SCBE/Aethermoore links are present when relevant.

Repair actions:

- generate three title options,
- generate one thumbnail concept per title,
- rewrite description from the transcript,
- trim tags to the real topic cluster.

## Commands

### Generate From Article

```powershell
python scripts/publish/article_to_video.py --file content/articles/ARTICLE.md
```

### Inspect Before Upload

```powershell
python scripts/publish/youtube_video_tool.py inspect `
  --file artifacts/youtube/VIDEO.mp4 `
  --script artifacts/youtube/VIDEO.md `
  --captions artifacts/youtube/VIDEO.srt `
  --description-file artifacts/youtube/VIDEO.description.txt `
  --require-youtube-treatment `
  --title "TITLE"
```

### Export Frames For Review

```powershell
python scripts/publish/youtube_video_tool.py frames `
  --file artifacts/youtube/VIDEO.mp4 `
  --fps 1 `
  --out-dir artifacts/youtube/reviews/VIDEO.frames
```

### Review The Ending

```powershell
python scripts/publish/youtube_video_tool.py tail `
  --file artifacts/youtube/VIDEO.mp4 `
  --seconds 12 `
  --out artifacts/youtube/reviews/VIDEO.tail.mp4
```

### Plan Upload

```powershell
python scripts/publish/youtube_video_tool.py plan-upload `
  --file artifacts/youtube/VIDEO.mp4 `
  --script artifacts/youtube/VIDEO.md `
  --captions artifacts/youtube/VIDEO.srt `
  --description-file artifacts/youtube/VIDEO.description.txt `
  --require-youtube-treatment `
  --title "TITLE"
```

## Video-Lattice Upgrade Path

The current video lattice can improve future videos by adding an internal
visual state before rendering:

```text
script beat
-> scene plan
-> pocket-dimension world state
-> skeleton/polygon sketch
-> control frame manifest
-> rendered frame/video
-> lattice inspection
-> correction or accept
```

This is how we get away from static slideshow videos without jumping straight
to expensive raw neural video generation. The engine stores compact rules and
control frames, then uses rendering only at the last step.

## Release Rule

No public upload should happen directly from first render.

Minimum release path:

1. render,
2. inspect,
3. upload unlisted,
4. watch tail and skim frames,
5. fix small failures,
6. publish.

If a video fails only the ending, repair the ending. Do not rerender the whole
video unless the structure is wrong.
