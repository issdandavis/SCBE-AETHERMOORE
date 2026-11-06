# KNOCK-V video evidence

KNOCK-V gives an agent a synchronized, tamper-evident view of a local video. It
is an evidence preparation layer rather than a trainer or a video model.

```text
local video
  -> FFprobe metadata
  -> timestamped FFmpeg frames
  -> 16 kHz mono audio
  -> timestamped transcript segments
  -> content-addressed manifest
  -> hash-verified time-window query
  -> vision/audio/text model
```

Build a bundle:

```powershell
python scripts/video_lattice/build_knock_v.py input.mp4 output.knockv `
  --transcript transcript.json --sample-fps 1
```

Read a synchronized window:

```powershell
python scripts/video_lattice/query_knock_v.py output.knockv --start 30 --end 40
```

The builder accepts a local media file and optional timestamped transcript JSON.
URLs are not downloaded. It records the source hash, media-tool versions, source
streams, sampled frame timestamps and hashes, audio hash, transcript timing,
timeline hash, and a bundle identifier. Queries verify the manifest, indexes,
selected frames, and audio before returning absolute artifact paths.

Every bundle is marked:

```text
training_eligible = false
ANALYSIS_ONLY_SEPARATE_SIGNED_TRAINING_ADMISSION_REQUIRED
```

Watching and training therefore remain separate actions. A later training
pipeline must receive a signed rights/provenance decision; public availability
alone is not admission.

Five unit tests and a real two-second FFmpeg smoke test pass. The smoke produced
four synchronized frames, audio, and two transcript segments and detected
artifact tampering. The remaining integration is a model adapter that selects a
time window, sends its frames to a vision model, its audio to a speech/audio
model, merges those observations with the transcript, and stores a derived
KNOCK-V interpretation receipt.
