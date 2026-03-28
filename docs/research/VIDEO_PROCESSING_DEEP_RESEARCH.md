# Video Processing Deep Research

**Date**: 2026-03-27
**Wave**: 1
**Author**: SCBE Research Pipeline
**Status**: Complete

---

## Table of Contents

1. [How Video Streaming Actually Works](#1-how-video-streaming-actually-works)
2. [Frame Rates and What "Real-Time" Means](#2-frame-rates-and-what-real-time-means)
3. [How Subtitle/Caption Tracks Work as Temporal Indexes](#3-how-subtitlecaption-tracks-work-as-temporal-indexes)
4. [Current State of Real-Time AI Video Inference](#4-current-state-of-real-time-ai-video-inference)
5. [The Gap: Frame-Level Detection vs. Meaning-Level Understanding](#5-the-gap-frame-level-detection-vs-meaning-level-understanding)
6. [The Insight: Subtitle Track as "Speed of Light" Reference Line](#6-the-insight-subtitle-track-as-speed-of-light-reference-line)
7. [Architecture Proposal: Subtitle-Aligned Frame Sampling](#7-architecture-proposal-subtitle-aligned-frame-sampling)
8. [Mapping to SCBE Multi-Model Parking System](#8-mapping-to-scbe-multi-model-parking-system)
9. [Hardware Reference Tables](#9-hardware-reference-tables)
10. [Cost Estimates](#10-cost-estimates)
11. [Sources](#11-sources)

---

## 1. How Video Streaming Actually Works

### The Fundamental Model

Video streaming does not send a single continuous file. It breaks video into **small HTTP-deliverable segments** (typically 2-10 seconds each), described by a **manifest file** that a client reads to decide what to fetch next.

There are two dominant protocols:

### HLS (HTTP Live Streaming)

Developed by Apple. The industry default.

```
Source Video
  → Encoder (H.264/H.265/AV1)
  → Segmenter (splits into .ts or .fmp4 chunks, 2-6 seconds each)
  → Manifest (.m3u8 playlist file)
  → CDN edge servers
  → Player fetches manifest, then segments sequentially
```

**Key facts:**
- Each segment is an independent HTTP GET request
- The `.m3u8` manifest lists all available quality levels (adaptive bitrate)
- Player measures bandwidth and switches quality levels mid-stream
- Standard latency: 15-30 seconds (because the player buffers 3-5 segments ahead)
- LL-HLS (Low-Latency): splits segments into **partial segments** of 200-500ms, delivered via chunked transfer encoding. Real-world latency: **2-5 seconds**

### DASH (MPEG-DASH)

International standard (ISO/IEC 23009-1). Not controlled by a single company.

```
Source Video
  → Encoder (same codecs)
  → Segmenter (splits into .m4s fragments)
  → MPD manifest (XML describing bitrates, segment URLs, timing)
  → CDN → Player
```

**Key facts:**
- Uses Media Presentation Description (MPD), an XML manifest
- Codec-agnostic (supports H.264, H.265, VP9, AV1)
- LL-DASH achieves similar 2-3 second latency to LL-HLS
- More flexible than HLS for DRM integration

### CMAF: The 2025-2026 Unifier

CMAF (Common Media Application Format) won a Technical Emmy Award in 2025 and effectively ended the container debate. It creates **one set of fragmented MP4 (fMP4) files** and generates two lightweight manifests — one `.m3u8` for HLS and one `.mpd` for DASH — both pointing at the same underlying video data.

**Result**: encode once, serve everywhere. Storage costs cut roughly in half.

### CDN Delivery Architecture

```
Origin Server (S3, GCS, or on-prem)
  → CDN Edge PoPs (200-300 locations globally)
  → Last-mile ISP
  → Client player

Typical path latency:
  Origin → Edge: 50-200ms (cached after first request)
  Edge → Client: 5-30ms
  Total first-byte: 50-100ms for cached content
```

### Codec Landscape (2026)

| Codec | Status | Typical Use |
|-------|--------|-------------|
| **H.264/AVC** | Universal, safest default | Everything, legacy devices |
| **H.265/HEVC** | ~50% better compression, patent issues | Apple devices, premium content |
| **VP9** | Royalty-free, good support | YouTube, Google ecosystem |
| **AV1** | Royalty-free, best compression | Growing adoption, modern browsers |

AV1 encoding is still 5-10x slower than H.264 at equivalent quality, limiting its use for real-time applications. For pre-encoded content, AV1 saves 30-50% bandwidth over H.264.

---

## 2. Frame Rates and What "Real-Time" Means

### The Math of Frame Rates

| Frame Rate | Time Per Frame | Use Case |
|-----------|---------------|----------|
| **24 fps** | 41.67 ms | Cinema, streaming movies |
| **25 fps** | 40.00 ms | PAL broadcast |
| **30 fps** | 33.33 ms | NTSC broadcast, most web video |
| **48 fps** | 20.83 ms | HFR cinema (Hobbit) |
| **60 fps** | 16.67 ms | Gaming, sports broadcast |
| **120 fps** | 8.33 ms | High-end gaming, slow-motion capture |
| **240 fps** | 4.17 ms | High-speed cameras, slow-mo replay |

### What "Real-Time" Actually Means

"Real-time" has different definitions depending on context:

| Context | Real-Time Means | Latency Budget |
|---------|----------------|---------------|
| **Video streaming** | Glass-to-glass < 1 second | 200-1000 ms |
| **Video conferencing** | Conversational delay < 150ms | 50-150 ms |
| **Autonomous driving** | Photon-to-brake | < 50 ms |
| **Military drone** | Sensor-to-decision | 50-100 ms |
| **AI inference on video** | Per-frame processing | Must be < 1/fps (e.g., < 33ms at 30fps) |
| **Human perception** | "Feels instant" | < 100 ms |

**Critical insight**: To process every frame of a 30fps video in real-time, your inference pipeline must complete in under 33ms. At 60fps, under 16.7ms. This is the hard constraint that drives all video AI architecture decisions.

### The Bandwidth Reality

| Resolution | Bitrate (typical) | Data per second | Data per hour |
|-----------|-------------------|----------------|--------------|
| 480p | 1.5 Mbps | 187 KB/s | 675 MB |
| 720p | 3-5 Mbps | 500 KB/s | 1.8 GB |
| 1080p | 5-8 Mbps | 875 KB/s | 3.15 GB |
| 4K | 15-25 Mbps | 2.5 MB/s | 9 GB |
| 8K | 50-80 Mbps | 8.75 MB/s | 31.5 GB |

---

## 3. How Subtitle/Caption Tracks Work as Temporal Indexes

### Subtitle Format Anatomy

**SRT (SubRip Text)** — the simplest and most universal:

```srt
1
00:00:01,000 --> 00:00:04,500
The experiment begins at the quantum level.

2
00:00:05,200 --> 00:00:08,900
Each particle carries information about its origin.

3
00:00:09,500 --> 00:00:13,000
Watch what happens when we increase the field strength.
```

**WebVTT (Web Video Text Tracks)** — the web standard, richer metadata:

```vtt
WEBVTT

00:00:01.000 --> 00:00:04.500
The experiment begins at the quantum level.

00:00:05.200 --> 00:00:08.900
Each particle carries information about its origin.

NOTE This is a scene transition

00:00:09.500 --> 00:00:13.000 position:10% align:left
Watch what happens when we <b>increase</b> the field strength.
```

### What Makes Subtitles a Temporal Index

Subtitles are not just text overlays. They are a **sparse temporal map of meaning**:

1. **Discrete time windows**: Each subtitle has a start time and end time, typically 1-7 seconds
2. **Meaning boundaries**: Subtitle breaks correspond to sentence or clause boundaries — places where meaning shifts
3. **Scene alignment**: Professional subtitles are timed to scene cuts and speaker changes
4. **Speech-silence mapping**: Gaps between subtitles mark silence, transitions, or non-verbal content
5. **Language-level semantic compression**: A 2-hour movie has ~1,500-2,000 subtitle entries, compressing the entire audio channel into ~15,000 words

### Subtitle Synchronization Methods

Modern sync tools use a powerful approach: they discretize both the audio stream and the subtitle track into **10ms windows**, then cross-correlate to find the optimal alignment. The ffsubsync tool achieves this by:

1. Running a Voice Activity Detector (VAD) on the audio
2. Checking each 10ms window: "Is speech happening?"
3. Checking the subtitle track: "Is a subtitle active at this timestamp?"
4. Cross-correlating the two binary signals to find the offset

This reveals that subtitles and audio are **fundamentally the same signal** at different levels of abstraction: the audio is the raw waveform, and the subtitles are the meaning-compressed version of that waveform.

### Subtitle Density as a Complexity Proxy

| Content Type | Subtitles/min | Words/min | Silence Ratio |
|-------------|--------------|-----------|---------------|
| Action movie | 3-5 | 40-70 | 40-60% |
| Drama/dialogue | 8-12 | 120-180 | 15-30% |
| Documentary | 10-15 | 150-200 | 10-20% |
| Lecture/tutorial | 12-18 | 160-220 | 5-15% |
| Music video | 2-4 | 30-60 | 60-80% |

---

## 4. Current State of Real-Time AI Video Inference

### Edge Hardware Performance (2025-2026)

**NVIDIA Jetson Family**:

| Device | AI Compute | Memory | Power | YOLOv8n FPS | YOLOv8x FPS | Price |
|--------|-----------|--------|-------|-------------|-------------|-------|
| Jetson Orin Nano 8GB | 40 TOPS | 8 GB | 15W | 80 (INT8) | ~15 | ~$250 |
| Jetson Orin NX 16GB | 100 TOPS | 16 GB | 25W | 65 (INT8) | ~30 | ~$600 |
| Jetson AGX Orin 32GB | 275 TOPS | 32 GB | 40W | 120+ (INT8) | 75 (INT8) | ~$1,000 |
| **Jetson T4000** (2026) | 1200 TOPS (FP4) | 64 GB | TBD | Real-time 4K | Real-time 4K | TBD |

**Other Edge Accelerators**:

| Device | AI Compute | Power | Use Case | Price |
|--------|-----------|-------|----------|-------|
| Google Coral TPU | 4 TOPS | 2W | Simple classification | ~$60 |
| Intel Movidius | 4 TOPS | 1.5W | Drone vision | ~$80 |
| Hailo-8 | 26 TOPS | 2.5W | Smart cameras | ~$100 |
| Axelera Metis | 214 TOPS | TBD | High-throughput vision | TBD |

### Cloud GPU Inference

| GPU | TOPS (INT8) | Memory | Per-frame latency (YOLOv8x) | Cost/hr |
|-----|------------|--------|---------------------------|---------|
| T4 | 130 | 16 GB | ~12ms | $0.50 |
| A10G | 250 | 24 GB | ~7ms | $1.00 |
| L4 | 485 | 24 GB | ~5ms | $0.80 |
| A100 | 624 | 80 GB | ~3ms | $3.00 |
| H100 | 1979 | 80 GB | ~1.5ms | $8.00 |

### Real-Time Speech-to-Text (Whisper and Competitors)

| System | Latency | Hardware | WER | Streaming? |
|--------|---------|----------|-----|-----------|
| Whisper Large v3 (batch) | 2-5s per 30s chunk | GPU | 4.2% | No |
| Whisper-Streaming | 3.3s end-to-end | GPU | ~5% | Yes (chunked) |
| **WhisperFlow** (2025) | **0.5-1.0s per word** | CPU (MacBook Air, 7W) | ~5% | Yes |
| Deepgram Nova-3 | 300-500ms | Cloud API | 3.8% | Yes (WebSocket) |
| AssemblyAI Universal-2 | 300ms | Cloud API | 4.0% | Yes |
| faster-whisper (CTranslate2) | 1-2s per 30s | GPU | 4.2% | Chunked |

**Key finding**: WhisperFlow (December 2024 paper) achieves sub-second per-word latency on a laptop CPU at 7 watts. This means real-time subtitle generation is now feasible on edge devices without a GPU.

### Tesla FSD as the Gold Standard

Tesla's Full Self-Driving represents the most demanding real-time video processing system deployed at scale:

- **48 neural networks** processing inputs from **8 cameras** simultaneously
- **HW3**: 144 TOPS, dual NPU, 36 TOPS each, 14nm TSMC
- **HW4/AI4**: significantly higher TOPS, FP16 precision, processes full 5MP camera feed
- **Processing rate**: 36 Hz (27.8ms per cycle), processing all 8 cameras per cycle
- **Pipeline**: 2D images → Bird's Eye View transformation → 3D occupancy network → 3D Gaussian rendering
- **Latency**: Near-zero between photon capture and inference output
- **Power**: ~72W for the compute module

**Lesson**: Tesla proves that real-time multi-camera video AI is possible at consumer scale — but requires purpose-built silicon and tight hardware-software co-design.

### Military Drone Processing

Defense sector video AI benchmarks (2025-2026):

| Metric | Current Achievement |
|--------|-------------------|
| End-to-end video processing latency | **100ms** on edge hardware |
| Edge compute to cloud latency (best case) | 20-40ms |
| Edge-only latency (no cloud) | **< 5ms** |
| Object detection + tracking | Real-time at 720p on 15W edge devices |
| Power budget for full AI stack | 15W (edge processor only) |
| Communication-denied operation | Full capability maintained |

**Key lesson**: Military systems assume cloud connectivity is unreliable. All critical inference must run on-device. The 15W power budget drives extreme model optimization.

---

## 5. The Gap: Frame-Level Detection vs. Meaning-Level Understanding

### What Current Systems Can Do (Frame-Level)

Per-frame AI can tell you:
- Objects present (YOLO, SSD, Faster R-CNN): "person", "car", "gun"
- Faces detected and recognized
- Scene classification: "indoor", "outdoor", "office"
- Motion vectors: "object moving left at 5px/frame"
- Optical character recognition: text visible in frame
- Anomaly detection: "frame differs significantly from previous"

**Latency**: 3-33ms per frame depending on model size and hardware.

### What Current Systems Cannot Do (Meaning-Level)

Per-frame AI cannot tell you:
- **Why** someone is doing something
- **What** is being said (needs audio track)
- **Story context**: "This is a flashback sequence"
- **Emotional arc**: "The character is becoming more desperate"
- **Narrative significance**: "This object will be important later"
- **Causal chains**: "A happened because of B three minutes ago"
- **Intent**: "The person is searching for something"

### The Fundamental Asymmetry

```
VISUAL CHANNEL (video frames):
  - 30 frames/second = 108,000 frames/hour
  - Each frame: 1920x1080 = 2,073,600 pixels = ~6MB raw
  - Total raw data: ~648 GB/hour
  - Information density per frame: LOW (99%+ redundancy between adjacent frames)

SEMANTIC CHANNEL (subtitles/speech):
  - ~150 words/minute = 9,000 words/hour
  - ~15,000 tokens/hour
  - ~60 KB/hour as text
  - Information density: HIGH (every word matters)
```

**The ratio**: The visual channel produces **10 million times** more raw data than the semantic channel, but carries only marginally more unique information for understanding "what is happening."

### Scene Change Detection: The State of the Art

The CVPR 2025 paper "Adaptive Keyframe Sampling for Long Video Understanding" introduced AKS, which:
1. Samples candidate frames uniformly
2. Scores each frame using a **composite metric**: perceptual sharpness + luminance stability + temporal diversity
3. Selects the minimum set of keyframes that maximizes information coverage
4. Achieves SOTA on long-video understanding benchmarks with **far fewer frames** than uniform sampling

Azure AI Video Indexer uses a similar approach: detecting shot boundaries via color scheme and visual feature changes in adjacent frames, then selecting representative keyframes per shot.

**But both approaches are blind to semantics.** They sample based on visual change, not meaning change. A character whispering a plot-critical secret looks identical to a character whispering something trivial — same visual features, same shot, same lighting.

---

## 6. The Insight: Subtitle Track as "Speed of Light" Reference Line

### The Core Idea

In physics, the speed of light is the reference velocity against which all other motion is measured. In video processing, the **subtitle track is the reference temporal signal** against which all visual processing should be measured.

```
TIME →  0s    5s    10s   15s   20s   25s   30s
        ┌─────┬─────┬─────┬─────┬─────┬─────┐

VISUAL: ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■  (900 frames at 30fps)
        Every frame processed = 900 inference calls

SUBTITLE: ──[A]───  ──[B]──  ─────  ──[C]────
        3 meaning-change events = 3 + boundary frames = ~12 inference calls

SAVINGS: 900 → 12 = 98.7% reduction in compute
```

### Why This Works

1. **Speech drives narrative**: In virtually all video content (movies, tutorials, surveillance with audio, meetings), the audio channel carries the primary semantic signal
2. **Visual changes correlate with speech changes**: Scene cuts, camera angle changes, and action beats are synchronized with dialogue and narration in professional content
3. **Silence is informative**: Gaps between subtitles mark transitions, establishing shots, or non-verbal sequences that can be handled with a single keyframe
4. **Subtitle boundaries are meaning boundaries**: Professional subtitles break at clause and sentence boundaries — exactly where a human would say "something new is happening"

### The Reference Line Analogy

```
PHYSICS:
  - Speed of light = c = 299,792,458 m/s
  - Everything else is measured relative to c
  - Objects at rest: v = 0 (maximum time dilation)
  - Objects near c: extreme effects, requires full processing

VIDEO PROCESSING:
  - Subtitle track = the "speed of light" temporal backbone
  - Frames during speech = meaningful, process them (near c)
  - Frames during silence = potentially idle, sample sparsely (at rest)
  - Frames at subtitle boundaries = TRANSITION POINTS, always capture
```

### When the Subtitle Signal Fails

The subtitle track is not sufficient for:
- **Pure visual content**: nature documentaries with no narration, music videos, surveillance
- **Action sequences**: rapid physical events that outpace dialogue
- **Visual jokes/reveals**: meaning carried entirely by what is shown, not said
- **Multi-stream content**: picture-in-picture, split-screen where visuals diverge from audio

**Solution**: Use subtitle boundaries as the primary sampling signal but maintain a **minimum keyframe rate** (e.g., 1 frame per 2 seconds) as a visual safety net, plus scene-change detection as a secondary trigger.

---

## 7. Architecture Proposal: Subtitle-Aligned Frame Sampling

### System Overview

```
INPUT VIDEO STREAM
       │
       ├──→ [Audio Track] ──→ [Whisper Real-Time] ──→ [Subtitle Generator]
       │                                                      │
       │                                              [Temporal Index]
       │                                                      │
       ├──→ [Frame Buffer] ←── SAMPLE COMMANDS ←──── [Sampling Controller]
       │         │                                            │
       │         │                                    [Scene Change Detector]
       │         │                                    (visual backup signal)
       │         │
       │    [Selected Frames]
       │         │
       │    [Edge Vision Model] ──→ [Frame Annotations]
       │                                    │
       │                            [Semantic Merger]
       │                                    │
       └──→ [Output: Annotated Timeline with Sparse Frame + Full Subtitle Coverage]
```

### Component Specifications

#### A. Real-Time Speech-to-Text (Subtitle Generator)

**Recommended**: WhisperFlow or faster-whisper with streaming chunks

| Parameter | Value |
|-----------|-------|
| Model | whisper-large-v3 or distil-whisper |
| Input | 16kHz mono audio, 30-second chunks |
| Output | Timestamped word-level transcription |
| Latency | 0.5-1.0s per word (WhisperFlow) |
| Hardware | CPU only (7W on MacBook Air) |
| Accuracy | ~5% WER (English) |

**Output format** (word-level timestamps):

```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 4.2,
      "text": "The experiment begins at the quantum level.",
      "words": [
        {"word": "The", "start": 0.0, "end": 0.15},
        {"word": "experiment", "start": 0.18, "end": 0.72},
        {"word": "begins", "start": 0.75, "end": 1.1},
        ...
      ]
    }
  ]
}
```

#### B. Sampling Controller

The controller decides WHICH frames to send to the vision model:

```
RULES:
1. On subtitle START: capture frame at subtitle.start_time
2. On subtitle END: capture frame at subtitle.end_time
3. During silence > 2s: capture 1 frame per 2 seconds
4. On scene change (visual detector): capture frame regardless
5. On semantic keyword trigger: capture burst (3 frames over 1s)
   Keywords: action verbs, emotion words, proper nouns

MAXIMUM RATE: 5 frames/second (to prevent overwhelming vision model)
MINIMUM RATE: 0.5 frames/second (visual safety net)
```

**Expected frame selection**:

| Content Type | Frames/min (subtitle-aligned) | vs. Every Frame (30fps) | Reduction |
|-------------|------------------------------|------------------------|-----------|
| Dialogue-heavy | 30-50 | 1,800 | 96-98% |
| Documentary | 40-60 | 1,800 | 96-97% |
| Action movie | 60-100 | 1,800 | 94-97% |
| Lecture/tutorial | 40-60 | 1,800 | 96-97% |
| Silent/music | 15-30 | 1,800 | 98-99% |

#### C. Edge Vision Model

**Recommended**: YOLOv8n (nano) for object detection + CLIP ViT-B/32 for scene understanding

| Model | Task | Latency (Jetson Orin Nano) | Latency (cloud T4) |
|-------|------|--------------------------|-------------------|
| YOLOv8n (INT8) | Object detection | 12.5ms | 4ms |
| CLIP ViT-B/32 | Scene embedding | 15ms | 5ms |
| Combined | Full annotation | ~30ms | ~10ms |

At 5 frames/second max rate: 30ms * 5 = 150ms of compute per second = **15% GPU utilization** on edge hardware.

#### D. Semantic Merger

Combines subtitle text with frame annotations into a unified timeline:

```json
{
  "timestamp": 4.2,
  "trigger": "subtitle_boundary",
  "speech": "The experiment begins at the quantum level.",
  "visual": {
    "objects": ["person", "laboratory equipment", "monitor"],
    "scene": "indoor laboratory",
    "clip_embedding": [0.12, -0.34, ...],
    "confidence": 0.92
  },
  "semantic_delta": 0.67,
  "governance_flag": "ALLOW"
}
```

### End-to-End Latency Budget

```
Audio capture → Whisper transcription:    500-1000ms
Frame capture → Vision inference:          30ms (edge) / 10ms (cloud)
Subtitle boundary → Frame selection:       < 1ms
Semantic merge:                            < 5ms
─────────────────────────────────────────────────────
Total pipeline latency:                    ~1-1.5 seconds from audio
                                           ~35ms from visual trigger
```

This means the system runs **1-1.5 seconds behind real-time** for speech-triggered sampling, and **~35ms behind** for visually-triggered sampling. For most applications (content moderation, search indexing, surveillance review), 1.5 seconds is well within acceptable bounds.

---

## 8. Mapping to SCBE Multi-Model Parking System

### The Direct Mapping

The subtitle-aligned video processing architecture maps precisely onto SCBE's Multi-Model Parking System (see `docs/specs/AETHERBROWSER_MULTI_MODEL_PARKING.md`):

```
PARKING SYSTEM          →    VIDEO PROCESSING SYSTEM
────────────────────────────────────────────────────
Parker (tiny, free)     →    Whisper + Subtitle Generator
                              Watches the audio stream continuously
                              Costs nearly nothing (CPU only, 7W)
                              Fills out the temporal index

Router (mid, cheap)     →    Sampling Controller + Scene Change Detector
                              Decides which frames matter
                              Classifies: speech/silence/transition/action
                              Routes frames to vision model only when needed

Heavy (big, expensive)  →    Edge/Cloud Vision Model (YOLO + CLIP)
                              Only runs on selected frames (2-5% of total)
                              Does the expensive spatial reasoning
                              Exits immediately after annotation

Summary Sheet           →    Semantic Merger output
                              Combines speech + vision into timeline
                              Ready for downstream consumption
                              Structured, token-efficient format
```

### Token Savings Calculation

**Without parking (process every frame)**:
- 30fps * 60s * 60min = 108,000 frames/hour
- Each frame through CLIP: ~500 tokens of context
- Total: 54,000,000 tokens/hour
- At $0.003/1K tokens (cheap vision model): **$162/hour**

**With subtitle-aligned parking**:
- ~40 frames/minute * 60 = 2,400 frames/hour
- Each frame through CLIP: ~500 tokens
- Subtitle text: ~9,000 words = ~12,000 tokens/hour
- Total: 1,212,000 tokens/hour
- At $0.003/1K tokens: **$3.64/hour**

**Savings: 97.8% reduction in compute cost.**

### SCBE Governance Integration

Each frame annotation passes through the SCBE governance gate:

```
Frame annotation
  → L3-4: Weighted transform (subtitle importance score)
  → L5: Hyperbolic distance (how far from "safe" baseline)
  → L12: Harmonic wall H(d, pd) = 1/(1 + d_H + 2*pd)
  → L13: Risk decision: ALLOW / QUARANTINE / ESCALATE / DENY

Examples:
  - "Person talking in office" → ALLOW (d_H ≈ 0, H ≈ 1.0)
  - "Weapon detected + threatening speech" → ESCALATE (d_H > 2.0, H < 0.15)
  - "No speech, unusual motion pattern" → QUARANTINE (ambiguous)
```

### Sacred Tongues Encoding for Video Events

Video events can be encoded in the Sacred Tongues tokenizer:

| Tongue | Video Role | Example |
|--------|-----------|---------|
| **KO** (Intent) | Why is this event significant? | "speaker_intent: explain" |
| **AV** (Metadata) | Frame timestamp, resolution, source | "ts:4200ms res:1080p cam:front" |
| **RU** (Binding) | Linking frames to subtitle segments | "frame_432 ↔ subtitle_7" |
| **CA** (Compute) | Processing cost, model used | "yolov8n:12ms clip:15ms" |
| **UM** (Security) | Governance flag, threat score | "flag:ALLOW score:0.02" |
| **DR** (Structure) | Position in narrative timeline | "act:2 scene:7 beat:rising" |

---

## 9. Hardware Reference Tables

### Recommended Configurations

#### Tier 1: Laptop/Desktop Development (~$0 incremental)

| Component | Spec | Role |
|-----------|------|------|
| CPU | Any modern x86_64 | Whisper inference (WhisperFlow) |
| RAM | 16GB+ | Frame buffer |
| Storage | SSD, 100GB free | Segment cache |
| GPU (optional) | Any NVIDIA with 4GB+ VRAM | Vision model acceleration |
| **Total cost** | **$0** (existing hardware) | |

**Performance**: ~2 frames/second vision inference on CPU, real-time Whisper on CPU.

#### Tier 2: Edge Deployment (~$300-600)

| Component | Spec | Role |
|-----------|------|------|
| Compute | NVIDIA Jetson Orin Nano 8GB | Vision + Whisper |
| Storage | 256GB NVMe | Local processing |
| Camera | USB3 or CSI | Direct feed |
| Power | 15W | Battery or PoE |
| **Total cost** | **~$350** | |

**Performance**: 80fps YOLOv8n (INT8), real-time Whisper, 5+ subtitle-aligned frames/second easily.

#### Tier 3: Cloud Production (~$50-200/month)

| Component | Spec | Role | Cost/month |
|-----------|------|------|-----------|
| Compute | AWS g5.xlarge (1x A10G) | Vision inference | $76/mo (spot) |
| Whisper | CPU instance (c6i.xlarge) | Speech-to-text | $50/mo |
| Storage | S3 Standard | Segments + annotations | $23/TB |
| CDN | CloudFront | Delivery | $0.085/GB (first 10TB) |
| **Total** | | | **~$150/mo** for moderate load |

#### Tier 4: High-Scale Production

| Component | Spec | Monthly Cost |
|-----------|------|-------------|
| Inference | 4x L4 GPUs (GKE) | $500 |
| Whisper | 8x CPU pods (auto-scaling) | $300 |
| Storage | GCS multi-region | $200 |
| CDN | Cloudflare Pro (50TB included) | $20 |
| Orchestration | GKE Autopilot | $150 |
| **Total** | | **~$1,170/mo** |

**Capacity**: ~500 concurrent video streams with subtitle-aligned processing.

---

## 10. Cost Estimates

### Per-Hour Processing Costs

| Approach | Frames Processed/hr | Compute Cost/hr | Storage/hr |
|----------|--------------------|--------------------|-----------|
| Every frame (30fps) | 108,000 | $3.00 (cloud GPU) | 2.5 GB |
| Every 10th frame | 10,800 | $0.30 | 250 MB |
| Scene-change only | ~3,600 | $0.10 | 85 MB |
| **Subtitle-aligned** | **~2,400** | **$0.07** | **55 MB** |
| Subtitle + visual backup | ~3,000 | $0.09 | 70 MB |

### CDN Delivery Costs (per 1,000 viewers)

| Quality | Bitrate | GB/hour | CloudFront Cost/hr | Cloudflare Pro Cost/hr |
|---------|---------|---------|-------------------|---------------------|
| 480p | 1.5 Mbps | 675 GB | $57 | ~$0.01* |
| 720p | 4 Mbps | 1,800 GB | $153 | ~$0.01* |
| 1080p | 7 Mbps | 3,150 GB | $268 | ~$0.01* |
| 4K | 20 Mbps | 9,000 GB | $765 | ~$0.01* |

*Cloudflare Pro is $20/mo flat with 50TB included, but their ToS restricts video-only CDN usage.

### Annotation Storage Costs

| Data Type | Size per hour | S3 Cost/TB/mo | Annual for 1000hrs |
|-----------|-------------|---------------|-------------------|
| Raw subtitle JSON | 60 KB | $23 | $0.001 |
| Frame annotations | 2 MB | $23 | $0.046 |
| CLIP embeddings | 5 MB | $23 | $0.115 |
| Selected keyframes (JPEG) | 50 MB | $23 | $1.15 |
| **Full annotation set** | **~57 MB** | | **$1.31/year** |

The annotation layer is essentially free to store — three orders of magnitude cheaper than the video itself.

---

## 11. Sources

### Video Streaming Architecture
- [Mastering Video Streaming Protocols: HLS, DASH, and more](https://medium.com/@agustin.ignacio.rossi/mastering-video-streaming-protocols-hls-dash-and-more-for-system-design-success-462a237b3f50)
- [What Is HLS Streaming (2026 Update)](https://www.dacast.com/blog/hls-streaming-protocol/)
- [HLS and DASH Protocols - Modern Video Streaming Architecture](https://oboe.com/learn/modern-video-streaming-architecture-pv29gb/hls-and-dash-protocols-ry3d76)
- [DASH vs HLS in 2026: Latency, DRM & Protocol Guide](https://swarmify.com/blog/dash-vs-hls-streaming-protocols-compared/)
- [Core technologies for streaming workflows: a 2026 architectural reassessment](https://blog.eltrovemo.com/2181/core-technologies-for-streaming-workflows-a-2026-architectural-reassessment-part-1/)
- [Comprehensive Guide to the HLS Protocol (2025)](https://www.videosdk.live/developer-hub/hls/hls-protocol)
- [HLS vs DASH vs MP4: Ultimate Streaming Format Comparison 2026](https://m3u8-player.net/blog/hls-dash-mp4-streaming-formats-comparison/)

### Real-Time AI Video Inference
- [The Best LLMs For Real-Time Inference On Edge In 2026](https://www.siliconflow.com/articles/en/best-LLMs-for-real-time-inference-on-edge)
- [On-Device LLMs in 2026: What Changed, What Matters](https://www.edge-ai-vision.com/2026/01/on-device-llms-in-2026-what-changed-what-matters-whats-next/)
- [2026 AI story: Inference at the edge, not just scale in the cloud](https://www.rdworldonline.com/2026-ai-story-inference-at-the-edge-not-just-scale-in-the-cloud/)
- [NVIDIA Unveils AI Grid Architecture for Distributed Edge Inference at GTC 2026](https://blockchain.news/news/nvidia-ai-grid-distributed-edge-inference-gtc-2026)
- [Accelerate AI Inference for Edge and Robotics with NVIDIA Jetson T4000](https://developer.nvidia.com/blog/accelerate-ai-inference-for-edge-and-robotics-with-nvidia-jetson-t4000-and-nvidia-jetpack-7-1)
- [Top 15 Edge AI Chip Makers with Use Cases in 2026](https://research.aimultiple.com/edge-ai-chips/)

### Subtitle Synchronization
- [ffsubsync: Automagically synchronize subtitles with video](https://github.com/smacke/ffsubsync)
- [AutoSubSync: Automatic subtitle synchronization tool](https://github.com/denizsafak/AutoSubSync)
- [Generate SRT and VTT subtitles using an API - Shotstack](https://shotstack.io/learn/generate-srt-vtt-subtitles-api/)

### Scene Detection and Keyframe Extraction
- [Scene Detection Policies and Keyframe Extraction Strategies for Large-Scale Video Analysis](https://arxiv.org/abs/2506.00667)
- [Adaptive Keyframe Sampling for Long Video Understanding (CVPR 2025)](https://arxiv.org/abs/2502.21271)
- [Azure AI Video Indexer: Scene, Shot, and Keyframe Detection](https://learn.microsoft.com/en-us/azure/azure-video-indexer/scene-shot-keyframe-detection-insight)

### Military Drone Video Processing
- [Defense Sector Trends in 2026: Edge AI, Autonomous Drones, Real-Time Battlefield Intelligence](https://www.prnewswire.com/news-releases/moonage-media-with-defense-sector-trends-in-2026-the-rise-of-edge-ai-autonomous-drones-and-real-time-battlefield-intelligence---and-why-maris-techs-technology-is-the-answer-to-this-market-need-302708187.html)
- [Military AI Video Solutions: Real-Time Intelligence at the Edge](https://www.maris-tech.com/blog/military-ai-video-solutions-real-time-intelligence-at-the-tactical-edge/)
- [AI-Powered Edge Video Intelligence Solutions for UAVs](https://www.unmannedsystemstechnology.com/2026/03/ai-powered-edge-video-intelligence-solutions-for-uavs-unmanned-systems/)
- [AI in Military Drones: Transforming Modern Warfare (2025-2030)](https://www.marketsandmarkets.com/ResearchInsight/ai-in-military-drones-transforming-modern-warfare.asp)
- [Real-Time Drone Data Processing with Edge Computing](https://anvil.so/post/real-time-drone-data-processing-with-edge-computing)

### Tesla FSD Architecture
- [Tesla's Neural Network Revolution: How FSD Replaced 300,000 Lines of Code](https://www.fredpope.com/blog/machine-learning/tesla-fsd-12)
- [Decoding Tesla's Core AI and Hardware Architecture](https://applyingai.com/2025/07/decoding-teslas-core-ai-and-hardware-architecture-a-ceos-perspective/)
- [The FSD v13 Paradox: Testing HW3 Limits and the AI4 Future](https://www.teslaacessories.com/blogs/news/the-fsd-v13-paradox-testing-hw3-limits-and-the-ai4-future-executive-summary-as-of-march-12-2026-the-tesla-community-stands-at-a-critical-juncture.-the-release-of-full-self-driving-fsd-v13-marks-a-monumental-shift-in-neural-network-architecture.-for-t)
- [Tesla AI's New Architecture with FSD v13 Software Stack](https://creativestrategies.com/research/tesla-ai-autonomy-fsd-v13-update/)

### Whisper and Real-Time Speech-to-Text
- [WhisperFlow: Speech Foundation Models in Real Time](https://arxiv.org/abs/2412.11272)
- [Turning Whisper into Real-Time Transcription System](https://arxiv.org/html/2307.14743)
- [Is Whisper Still #1? 2025 Benchmarks & 2026 Outlook](https://diyai.io/ai-tools/speech-to-text/can-whisper-still-win-transcription-benchmarks/)
- [Top APIs and Models for Real-Time Speech Recognition in 2026](https://www.assemblyai.com/blog/best-api-models-for-real-time-speech-recognition-and-transcription)
- [Best Open Source STT Model in 2026 (with Benchmarks)](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks)

### Edge Hardware Benchmarks
- [YOLOv8 Performance Benchmarks on NVIDIA Jetson Devices](https://www.seeedstudio.com/blog/2023/03/30/yolov8-performance-benchmarks-on-nvidia-jetson-devices/)
- [Achieving 60 FPS YOLOv8 on Jetson Orin NX with INT8](https://www.simalabs.ai/resources/60-fps-yolov8-jetson-orin-nx-int8-quantization-simabit)
- [YOLOv8/Jetson/Deepstream Benchmark: Orin Nano, NX, TX2](https://medium.com/@MaroJEON/yolov8-jetson-deepstream-benchmark-test-orin-nano-4gb-8gb-nx-tx2-f3993f9c8d2f)

### CDN Pricing
- [CDN Pricing War 2025: One Is 70% Cheaper](https://blog.blazingcdn.com/en-us/what-are-the-current-prices-for-major-cdn-providers)
- [Amazon CloudFront CDN Pricing](https://aws.amazon.com/cloudfront/pricing/)
- [Amazon CloudFront Pricing 2026 Guide](https://go-cloud.io/amazon-cloudfront-pricing/)
- [Analyzing CDN Cost Efficiency: A Developer's Comparison](https://transloadit.com/devtips/analyzing-cdn-cost-efficiency-a-developer-s-comparison/)
