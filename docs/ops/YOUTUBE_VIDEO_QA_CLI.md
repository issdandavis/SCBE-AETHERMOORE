# YouTube Video QA CLI

Status: local-first preflight and repair tool.

Completed render does not mean completed video. The video file itself has to pass a media gate before upload: container probe, audio/video duration check, script runtime comparison, tail-audio check, transcript/caption artifact check, subscribe/notification CTA check, and optional transcript-ending alignment.

## Inspect Before Upload

```powershell
python scripts/publish/youtube_video_tool.py inspect `
  --file artifacts/youtube/scbe_voice_pilot.mp4 `
  --script artifacts/youtube/scbe_voice_pilot.md `
  --captions artifacts/youtube/scbe_voice_pilot.srt `
  --description "Subscribe and ring the notification bell for the next SCBE build." `
  --require-youtube-treatment `
  --title "The System Has To Tell The Truth"
```

The report is written to:

```text
artifacts/youtube/reviews/<video-name>.inspection.json
```

The report contains multiple understandings of the same video:

- container probe from `ffprobe`
- source script runtime estimate
- final audio-tail silence scan
- optional transcript-ending alignment
- YouTube treatment gate: description, subscribe/bell CTA, captions
- upload gate result and readiness score

## Plan An Upload

```powershell
python scripts/publish/youtube_video_tool.py plan-upload `
  --file artifacts/youtube/scbe_voice_pilot.mp4 `
  --script artifacts/youtube/scbe_voice_pilot.md `
  --captions artifacts/youtube/scbe_voice_pilot.srt `
  --description-file artifacts/youtube/scbe_voice_pilot.description.txt `
  --require-youtube-treatment `
  --title "The System Has To Tell The Truth"
```

If the score passes the threshold, the tool prints the existing uploader command:

```powershell
python scripts/publish/post_to_youtube.py --file artifacts/youtube/VIDEO.mp4 --title "..." --privacy unlisted
```

Uploads remain unlisted first. Public release stays a separate human approval step.

## Export Frames For AI Review

Sample frames so an AI or human can inspect visual continuity instead of trusting the render job:

```powershell
python scripts/publish/youtube_video_tool.py frames `
  --file artifacts/youtube/scbe_voice_pilot.mp4 `
  --fps 1 `
  --out-dir artifacts/youtube/reviews/scbe_voice_pilot.frames
```

For full frame-by-frame export:

```powershell
python scripts/publish/youtube_video_tool.py frames `
  --file artifacts/youtube/scbe_voice_pilot.mp4 `
  --every-frame `
  --out-dir artifacts/youtube/reviews/scbe_voice_pilot.frames.full
```

The command writes `frames_manifest.json` beside the exported images. This is the starting point for transcript-to-frame alignment: captions provide the time map, sampled frames provide the visual state.

## Review The Ending Fast

```powershell
python scripts/publish/youtube_video_tool.py tail `
  --file artifacts/youtube/scbe_voice_pilot.mp4 `
  --seconds 12 `
  --out artifacts/youtube/reviews/scbe_voice_pilot.tail.mp4
```

This creates a short clip of the final seconds so an AI or human can check whether the ending actually lands.

## Append A Fixed Ending

Render or record only the missing ending as a small MP4, then append it:

```powershell
python scripts/publish/youtube_video_tool.py append-ending `
  --file artifacts/youtube/old_video.mp4 `
  --ending artifacts/youtube/fixed_ending.mp4 `
  --out artifacts/youtube/old_video.fixed.mp4
```

If the clips use different codecs:

```powershell
python scripts/publish/youtube_video_tool.py append-ending `
  --file artifacts/youtube/old_video.mp4 `
  --ending artifacts/youtube/fixed_ending.mp4 `
  --out artifacts/youtube/old_video.fixed.mp4 `
  --reencode
```

This still creates a new output file, but it avoids regenerating the whole video from scratch.

## Gate Meaning

- `80+`: usable for unlisted upload planning.
- `60-79`: inspect manually; likely repairable.
- `<60`: do not upload until the flagged media issue is fixed.

Primary failure cases:

- no audio stream
- no video stream
- zero or unreadable duration
- script estimate is much longer than the rendered video
- final tail is mostly silent
- transcript does not contain the script ending
- missing captions/transcript artifact
- missing YouTube description or subscribe/notification CTA

## Next Phase

- Upload caption files through the YouTube captions endpoint after the unlisted upload.
- Generate multilingual captions from the source transcript, then require language-specific review before public release.
- Align caption timecodes to exported frames so AI can inspect the video frame by frame against what is being said.
- Add composed background music stems as separate artifacts. The target is not generic stock music: use score-sheet style parts, classical instrumentation, and the conlang meaning layer as metadata tied to notes, waves, and emotional intent.
- Move from still-image videos toward cinematic audiobook-to-movie/anime renders once the QA gate can inspect motion, audio, transcript alignment, and ending completeness reliably.
