---
name: scbe-youtube-factory
description: Generate faceless narrated videos from SCBE articles and upload or iterate them for YouTube. Use when creating, previewing, improving, or publishing videos from article content.
---

# SCBE YouTube Factory

Generate faceless narrated videos from SCBE articles and upload to YouTube, with iterative quality improvement.

## When To Use

- User wants to create YouTube videos from articles
- User says "make a video", "youtube", "faceless video", "narrate this"
- User wants to improve an existing video (voice, visuals, pacing)
- Batch video generation for the channel

## Pipeline

```
Article (markdown) → Parse → TTS (Kokoro am_adam) → Slides (Pillow) → FFmpeg → MP4 → YouTube Upload
```

## Pick Good Content

Best articles for video (in order):
1. **X threads** — already segmented into bite-size pieces, 2-4 min videos
2. **Technical explainers** — GitHub Discussion articles about HYDRA, hyperbolic geometry, Sacred Tongues
3. **Story content** — Everweave/Spiralverse lore, isekai story chapters
4. **Tutorials** — how-to articles with code blocks (syntax highlighted slides)

Use `hydra content review` to see QA-approved articles. Pick ones with score >= 80 and word count 200-2000.

## Commands

### Generate video
```bash
python scripts/publish/article_to_video.py --file content/articles/ARTICLE.md
```

### Change voice
```bash
# Kokoro voices (local, high quality, FREE)
--voice kokoro:am_adam        # male, natural (DEFAULT)
--voice kokoro:am_michael     # male, deeper
--voice kokoro:bm_george      # British male
--voice kokoro:af_heart       # female, warm
--voice kokoro:bf_emma        # British female

# Edge-TTS voices (cloud, free, unlimited)
--voice en-US-AndrewMultilingualNeural   # warm, confident male
--voice en-US-ChristopherNeural          # authoritative male
--voice en-GB-RyanNeural                 # British male
```

### Preview without generating
```bash
python scripts/publish/article_to_video.py --file ARTICLE.md --dry-run
```

### Generate thumbnail only
```bash
python scripts/publish/article_to_video.py --file ARTICLE.md --thumbnail-only
```

### Upload to YouTube
```bash
# First time: authenticate
python scripts/publish/post_to_youtube.py --auth

# Upload (unlisted by default — safe for iteration)
python scripts/publish/post_to_youtube.py \
  --file artifacts/youtube/VIDEO.mp4 \
  --title "Video Title" \
  --article content/articles/ARTICLE.md \
  --tags "AI Safety,SCBE,Issac Daniel Davis" \
  --privacy unlisted

# Make public when happy
python scripts/publish/post_to_youtube.py \
  --file artifacts/youtube/VIDEO.mp4 \
  --title "Video Title" \
  --privacy public
```

### Batch generate
```bash
# Generate videos for all approved articles
for f in content/articles/x_thread_*.md; do
  python scripts/publish/article_to_video.py --file "$f"
done
```

## Iteration Loop

1. Generate → upload unlisted → user watches
2. User gives feedback ("too fast", "voice weird on segment 3", "add more pauses")
3. Adjust (voice, speed, segment splitting, slide design)
4. Regenerate → re-upload unlisted
5. Repeat until quality is good
6. Flip to public

## Video Output Location

- Videos: `artifacts/youtube/*.mp4`
- Thumbnails: `artifacts/youtube/*.thumb.png`
- Evidence: `artifacts/publish_browser/youtube_*.json`

## Dependencies

```bash
pip install kokoro-onnx soundfile edge-tts pillow pygments
# FFmpeg must be on PATH (installed via: winget install Gyan.FFmpeg)
# Kokoro model files in repo root: kokoro-v1.0.onnx, voices-v1.0.bin
```

## YouTube Channel

- Channel: Issac "Izreal" Davis (@id8461)
- Channel ID: UCO9aJ-ZH0Ddg_F0Dr655WIQ
- OAuth tokens: config/connector_oauth/.youtube_tokens.json
- Note: Refresh tokens expire every 7 days in Testing mode. Re-auth with --auth when needed.
- Custom thumbnails need channel phone verification.

## Future Improvements

- Manhwa/comic panel visuals (Canva/Firefly API)
- Manim math animations for geometry content
- Podcastfy 2-host conversation format
- Background music (royalty-free, mixed low)
- SRT subtitles burned into video
- Animated code typing effect
- Chapter markers in YouTube description

## Guardrails

- Always upload as UNLISTED first
- Never auto-publish to public without user approval
- Credit "Issac Daniel Davis" (ISSAC with two S's) in all descriptions
- Include SCBE-AETHERMOORE GitHub link in every video description
