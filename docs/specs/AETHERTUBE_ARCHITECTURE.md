# AetherTube — SCBE-Governed Video Platform Architecture

**Status**: Research + existing components inventory
**Date**: 2026-03-26
**Goal**: Self-hosted video platform with governance, tongue-classification, and training loop

## What YouTube Actually Is (5 core systems)

| System | What It Does | Scale |
|--------|-------------|-------|
| **Upload Pipeline** | Ingest → safety scan → transcode → store | 500hrs/min uploaded |
| **Content Delivery** | Adaptive streaming (HLS/DASH) via CDN edge nodes | 2.5B users |
| **Recommendation** | Two-stage: candidate generation → ranking | Billions of predictions/day |
| **Metadata/Search** | Title, desc, tags, chapters → full-text + semantic search | 800M+ videos |
| **Monetization** | Ads, memberships, Super Chat, merchandise shelf | $31B/year |

## What We Already Have

### Production-Ready

| Component | File | What It Does |
|-----------|------|-------------|
| Video frame generator | `src/video/generator.ts` | Hyperbolic fractal frames, streaming |
| Audio synthesis | `src/video/audio.ts` | Harmonic weighting, Poincare-modulated pitch |
| Video watermark | `src/video/watermark.ts` | Lattice-based provenance watermarks |
| Security integration | `src/video/security-integration.ts` | Fractal fingerprints, audit reels |
| TTS narration | `scripts/narrate_book.py` | Kokoro ONNX, am_adam voice, 24kHz |
| Voice profiling | `scripts/audiobook/narrator_voice_system.py` | 18 character profiles, emotion modulation |
| Manhwa strip assembly | `scripts/assemble_manhwa_strip.py` | Webtoon vertical scroll, panel assembly |
| YouTube transcript pull | `scripts/apollo/youtube_transcript_collector.py` | Free API, 18 curated channels |
| YouTube metadata sync | `scripts/apollo/youtube_metadata_sync.py` | Batch update titles/desc/tags |
| Video review/scoring | `scripts/apollo/video_review.py` | 4-dimension quality scoring |
| Governance gate | `src/governance/runtime_gate.py` | Content safety for all uploads |
| ffmpeg | System install | Transcoding, thumbnails, audio extraction |
| Whisper | Python package | Caption/transcript generation |

### Missing (Need to Build)

| Component | What's Needed | Difficulty |
|-----------|--------------|------------|
| HLS/DASH streaming | Segment videos + generate manifests | Medium |
| Web video player | HLS.js or Video.js integration | Easy |
| Upload-to-own-platform | Receive video, trigger pipeline | Medium |
| Recommendation engine | Tongue-weighted candidate + ranking | Hard |
| Self-hosted storage | Local + S3/MinIO for renditions | Easy |
| Live streaming | RTMP ingest → HLS output | Hard |
| Kokoro → voice wiring | Connect narrator_voice_system to TTS | Easy |

## AetherTube Pipeline

```
UPLOAD
  User/agent submits video file
    ↓
GOVERNANCE GATE (L1-L13)
  Runtime gate scans metadata + first 30s audio transcript
  Decision: ALLOW → continue | QUARANTINE → review | DENY → reject
    ↓
TRANSCODE (ffmpeg)
  Original → 360p, 720p, 1080p (H.264)
  Extract thumbnail at 25% mark
  Generate HLS segments (2-10s each)
    ↓
CAPTION (Whisper)
  Audio → transcript → VTT subtitles
  Tongue classification on transcript text
    ↓
TONGUE CLASSIFY
  Run transcript through Sacred Tongue activation:
    KO score, AV score, RU score, CA score, UM score, DR score
  Tag video with primary + secondary tongues
    ↓
STORE
  Local: artifacts/aethertube/videos/{id}/
    ├── original.mp4
    ├── 360p/  (HLS segments)
    ├── 720p/  (HLS segments)
    ├── 1080p/ (HLS segments)
    ├── master.m3u8 (adaptive manifest)
    ├── thumbnail.jpg
    ├── captions.vtt
    └── metadata.json
    ↓
INDEX
  Add to search index (SQLite FTS5 or Meilisearch)
  Register in recommendation graph
    ↓
TRAINING LOOP
  Transcript → SFT pairs (automatic)
  Watch patterns → recommendation training data
  Review scores → quality improvement signal
```

## Recommendation Engine (SCBE-Native)

### Stage 1: Candidate Generation
```
Input: viewer profile (tongue preferences, watch history, trust level)
Output: ~50 candidate videos

Signals:
  - Tongue match: viewer's preferred tongues vs video's tongue classification
  - Recency: newer content weighted higher
  - Creator trust: Fibonacci trust level of the uploader
  - Completion rate: videos similar viewers finished
```

### Stage 2: Ranking
```
Input: ~50 candidates
Output: ordered list for feed/sidebar

Score = w1*tongue_match + w2*trust_score + w3*freshness + w4*completion_prediction

SCBE additions:
  - Fibonacci trust modulates visibility (CORE creators get boosted)
  - Null-space detection on recommendations (don't show content from blind spots)
  - Governance cost check (high-cost content needs higher viewer trust)
```

## What Makes AetherTube Different

| Feature | YouTube | AetherTube |
|---------|---------|-----------|
| Content safety | Post-hoc moderation + AI flags | Pre-publish 14-layer governance gate |
| Creator trust | Subscriber count (gameable) | Fibonacci ladder (earnable, drops on violation) |
| Content classification | ML topic labels | Sacred Tongue 6D semantic activation |
| Recommendations | Engagement-optimized | Tongue-matched + trust-weighted |
| Watermarking | ContentID (proprietary) | Lattice-based hyperbolic watermarks (open) |
| Training loop | Internal only | Every video auto-generates SFT pairs |
| Privacy | Tracks everything | Tor-compatible, self-hosted option |
| Federation | Walled garden | ActivityPub-compatible (PeerTube interop) |
| Voice | No native TTS | Kokoro ONNX local TTS for narration |
| Dark web content | Blocked | Governed access via SpaceTor |

## Technology Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Transcoding | ffmpeg (installed) | Industry standard, free |
| Streaming | HLS via hls.js | Browser-native, adaptive bitrate |
| Player | Video.js or custom | Open source, plugin ecosystem |
| Storage | Local + MinIO (S3-compatible) | Free locally, cheap to scale |
| Search | SQLite FTS5 | Zero-dependency, fast |
| Captions | Whisper (installed) | Free, local, accurate |
| TTS | Kokoro ONNX (installed) | Local, Apache 2.0, near-ElevenLabs quality |
| Watermark | `src/video/watermark.ts` (built) | Hyperbolic lattice-based |
| Security | `src/video/security-integration.ts` (built) | Fractal fingerprints |
| Governance | `src/governance/runtime_gate.py` (built) | 14-layer + Fibonacci trust |
| CDN | Cloudflare free tier | Already on their DNS |
| Federation | PeerTube ActivityPub | 1000+ instances, 600K+ videos |

## Build Order (Smallest to Largest)

### Phase 1: Wire existing pieces (days)
1. Connect `narrator_voice_system.py` to Kokoro TTS (currently generates scripts only)
2. Build `ffmpeg_transcode.py` — input video → HLS segments + thumbnail + manifest
3. Build `aethertube_upload.py` — governance gate → transcode → store → index

### Phase 2: Serve and play (week)
4. HLS player page (`docs/aethertube/player.html`) using hls.js
5. Video index page listing all hosted videos with tongue tags
6. Self-review loop: upload → Whisper caption → review score → metadata fix

### Phase 3: Recommend and discover (weeks)
7. Tongue-weighted recommendation engine
8. Search index (SQLite FTS5 on titles + transcripts)
9. Federation via ActivityPub (PeerTube interop)

### Phase 4: Scale (months)
10. Multi-resolution adaptive streaming
11. Live streaming (RTMP ingest)
12. MinIO object storage for renditions
13. CDN edge caching via Cloudflare
