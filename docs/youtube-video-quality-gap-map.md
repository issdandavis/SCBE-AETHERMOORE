# YouTube / AI Video Quality Gap Map

Date: 2026-05-23

Purpose:

Map what the repo already has, what the current AI/video ecosystem provides, and what is still missing to make higher-quality videos and upload them reliably.

## What We Already Have

### In `SCBE-AETHERMOORE`

- `scripts/video/verify.js`
  - Runs `ffprobe`.
  - Checks video/audio stream presence.
  - Checks basic codec recommendations.
  - Computes SHA256.
  - Writes verification receipt JSON.

- `scripts/youtube/upload.js`
  - OAuth refresh token flow.
  - YouTube resumable upload session.
  - Chunked upload with retry/resume from YouTube `Range` header.
  - Processing-status polling.
  - Upload receipt JSON.

- `.github/workflows/video-upload.yml`
  - Manual `workflow_dispatch`.
  - Installs ffmpeg.
  - Runs verify.
  - Runs a dry-run GeoSeal safety check.
  - Uploads to YouTube.
  - Stores receipts as artifacts.

- `scripts/publish/youtube_video_tool.py`
  - Existing inspection/editor utility surface.
  - Includes surgical audio segment replacement and append-ending support.

### In `miracle-memory-book`

- `_studio/story_video.py`
  - Chapter text + audio to illustrated story video.
  - Beat extraction.
  - Image generation/cached beat images.
  - MP4 composition.
  - Caption sidecar generation.

- `_studio/parallax_video.py`
  - Parallax-style video path.

- `_studio/qa_video.py`
  - Existing frame/QA tooling.

- `_studio/audio_patches/`
  - Real local patch lane for bad narration spans.

- `upload_miracle_youtube.py`
  - Book-specific upload lane.

## Current External Baseline

### YouTube Upload Requirements

Official YouTube guidance still favors:

- MP4 container.
- Fast Start / `moov` atom at the front.
- H.264 High Profile.
- Progressive scan.
- 4:2:0 chroma.
- AAC-LC or Opus audio.
- 48 kHz sample rate.
- Matching source frame rate.

For chapters, YouTube expects manual timestamps in the description; the first timestamp should start at `00:00`.

For reliable uploads, Google documents resumable uploads using `Content-Range`, `308 Resume Incomplete`, and `Range` headers to continue after interruption. Our Node uploader now follows this pattern.

### AI Video Generation Market

Closed/API tools:

- Google Veo on Vertex/Gemini API: high-fidelity text/image-to-video, short generated clips, native audio in newer versions.
- Runway Gen-4/Gen-4.5: strong controllability, world consistency, API surface.
- Kling API: commercial video generation, including higher-resolution offerings.
- OpenAI Sora status is unstable/discontinued as a normal product according to current public pages/news; do not build a hard dependency on it.

Open/local tools:

- Wan series.
- HunyuanVideo.
- LTX Video.
- CogVideoX.
- Mochi.
- ComfyUI as the practical orchestration shell.

The open/local models are useful for generated B-roll, reference-image animation, and controlled visual experiments, but long-form continuity, exact text timing, and scene-to-scene character consistency still need a pipeline around them.

## What Is Missing

### 1. A Real Pre-Upload Quality Gate

Current verify is codec-level. Missing checks:

- black frame detection;
- frozen frame detection;
- audio silence detection;
- audio clipping;
- loudness target, e.g. integrated LUFS;
- audio/video duration mismatch;
- end-tail check: last speech line vs final video duration;
- SRT completeness;
- SRT final cue near audio end;
- manual chapter formatting validation;
- thumbnail dimensions and file size;
- title/description/tags metadata validation;
- faststart/moov validation;
- bitrate/profile/pixel format details.

### 2. Narrative Video QA

For story videos, codec correctness is not enough.

Missing checks:

- does the video start right;
- does the video end right;
- does the final line finish cleanly;
- are there unwanted mid-sentence cuts;
- is there an intro/outro;
- are chapter openers/closers present;
- do captions match source text;
- are post-chapter and pre-chapter bridging lines present;
- does the scene begin out of nowhere;
- does the chapter end before the emotional beat lands;
- does narration drift away from manuscript intent.

### 3. Visual Quality Scoring

Missing checks:

- image sharpness/blur;
- blank frame / failed generated image detection;
- repeated frame overuse;
- motion continuity;
- text artifacts in generated images;
- anachronistic objects;
- character/costume consistency;
- shot variety;
- face/hand deformation detection;
- visual relevance to chapter beat.

Potential local tools:

- FFmpeg filters: `blackdetect`, `freezedetect`, `silencedetect`, `astats`, `ebur128`.
- OpenCV for blur, histogram, duplicate-frame, and blank-frame checks.
- CLIP/image-text similarity for beat-image relevance.
- OCR to catch unwanted text in generated images.
- VMAF/libvmaf for encode quality when comparing source vs compressed output.

### 4. Better Render Presets

Current outputs appear workable but not fully standardized.

Need named presets:

- `youtube-1080p-story`
- `youtube-4k-upscale`
- `youtube-shorts`
- `youtube-audiobook-static`
- `youtube-preview-clip`

Each should define:

- resolution;
- fps;
- codec/profile;
- CRF or bitrate;
- audio sample rate/channels/bitrate;
- loudness target;
- faststart;
- caption output;
- thumbnail output;
- QA gates.

### 5. Asset Manifest And Receipts

Current receipts exist for verify/upload, but the full video object needs a manifest:

- source manuscript hash;
- audio file hash;
- SRT hash;
- thumbnail hash;
- render preset;
- ffmpeg command;
- chapter timestamps;
- intro/outro version;
- QA result;
- upload receipt;
- YouTube video ID.

This prevents uploading the wrong regenerated artifact.

### 6. AI Video Generation Orchestrator

The repo has generation pieces, but not a provider-agnostic orchestrator.

Needed:

- beat manifest;
- prompt pack per beat;
- provider adapter: local/ComfyUI, Veo, Runway, Kling, existing image pipeline;
- reference image/cast lock;
- retry/cost ledger;
- output normalization;
- generated clip QA;
- fallback to still/parallax when generation fails.

Do not make long videos directly from AI video generators yet. Better approach:

1. Manuscript/audio defines timing.
2. Beat sheet defines visual intent.
3. Generate short clips or stills per beat.
4. QA each clip/still.
5. Compose deterministically with FFmpeg.
6. Verify the final video.

### 7. YouTube Packaging Inspector

Before upload, inspect:

- title length and clarity;
- description has overview;
- description has chapters starting at `00:00`;
- links are present if required;
- CTA present if desired;
- thumbnail exists;
- captions exist;
- tags/category/privacy are sane;
- made-for-kids flag intentional;
- upload is unlisted/private unless explicitly approved public.

### 8. Post-Upload Verification

After upload:

- poll processing until complete or timeout;
- fetch `videos.list` status/snippet;
- confirm privacy;
- confirm title/description/tags;
- confirm duration approximately matches local;
- confirm captions uploaded if using captions API;
- confirm thumbnail set;
- store final receipt.

## Best Next Build Order

### Phase 1: Quality Gate

Implemented:

- `scripts/video/quality_gate.js`
  - Base media checks: streams, codecs, resolution, audio/video duration, black/freeze/silence, SRT continuity, thumbnail size, chapter syntax, MP4 faststart, loudness/peak warnings.
  - Story mode: `--story` requires captions, chapters, CTA/next-chapter treatment, final captions near the media ending, final sentence punctuation, no black/frozen ending, and optional source-text final-word alignment.
  - Outputs `summary.readinessScore` and `summary.storyReady`.

- `scripts/video/story_package.js`
  - One command for the agent-bus lane: metadata package -> story quality gate -> upload manifest.
  - Produces `youtube-metadata.json`, `quality-gate.json`, and `video-package.json` in one output folder.

- `scripts/video/package_manifest.js`
  - Carries `quality.readinessScore`, `quality.storyReady`, and `quality.storyMode`.

- `scripts/youtube/upload.js`
  - Refuses manifests whose quality gate failed or whose story readiness is explicitly false.

Remaining gaps:

- Captions are checked structurally, but not yet word-for-word aligned across the full video.
- Visual relevance to the manuscript beat still needs CLIP/OCR/frame-sampling support.
- Automatic intro/outro repair is not wired here yet; this gate detects the issue and blocks upload.

- wraps `ffprobe`;
- runs ffmpeg filters;
- validates codec/render rules;
- validates SRT/chapter metadata;
- emits `quality-gate.json`;
- exits nonzero on hard failures.

This is the highest value because it catches bad endings, silence, missing captions, and wrong files before upload.

### Phase 2: Story Package Manifest

Implemented initial version: `scripts/video/package_manifest.js`.

- collect mp4/srt/thumb/metadata;
- hash all assets;
- verify expected durations;
- write one manifest.

### Phase 3: YouTube Metadata Packager

Implemented initial version: `scripts/youtube/package.js`.

- generate title/description/tags/chapters;
- validate YouTube chapter syntax;
- write upload-ready metadata JSON.

### Phase 4: Upload From Manifest

Implemented initial version: `scripts/youtube/upload.js --manifest video-package.json`.

The uploader refuses a manifest whose quality summary is explicitly failed and uploads the exact checked file with manifest metadata.

### Phase 5: AI Visual Provider Adapters

Build provider adapters only after the gate exists:

- local ComfyUI/Wan/Hunyuan;
- Veo;
- Runway;
- Kling.

This avoids generating more videos than we can inspect.

## Minimal MVP Definition

MVP is not "generate prettier video."

MVP is:

1. Take a rendered MP4 + SRT + thumbnail + metadata.
2. Prove it starts and ends correctly.
3. Prove captions and chapters are complete.
4. Prove audio is not clipped/silent/cut.
5. Prove render settings are YouTube-safe.
6. Upload privately/unlisted through resumable chunks.
7. Save receipts and video ID.

Only after that should generation quality be expanded.

## Sources

- YouTube Help: recommended upload encoding settings.
- Google Developers: YouTube Data API resumable upload protocol.
- YouTube Help: video chapters.
- Google Cloud / Gemini API: Veo video generation.
- Runway API/docs: Gen-4 model references and prompting.
- Kling API documentation.
- Research/open ecosystem: Wan, HunyuanVideo, LTX Video, CogVideoX, ComfyUI.
