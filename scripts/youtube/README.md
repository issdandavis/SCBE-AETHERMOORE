# scripts/youtube

Node.js YouTube upload pipeline using OAuth2 refresh tokens and the resumable upload API.

## Scripts

### `upload.js`

Resumable upload with receipt output.

```bash
node scripts/youtube/upload.js \
  --file path/to/video.mp4 \
  --title "My Video" \
  --description "Description here" \
  --privacy private \
  --chunk-size-mb 8 \
  --receipt-out upload-receipt.json
```

Uploads use YouTube's resumable protocol in chunks. If a chunk fails with a retryable error, the script queries the upload session for the committed byte range and resumes from there.

Upload from a verified package manifest:

```bash
node scripts/youtube/upload.js \
  --manifest video-package.json \
  --chunk-size-mb 8 \
  --receipt-out upload-receipt.json
```

The uploader refuses manifests whose quality summary is explicitly failed.

### `package.js`

Build an upload-ready YouTube metadata JSON package.

```bash
node scripts/youtube/package.js \
  --out youtube-metadata.json \
  --title "My Video" \
  --description "Description here" \
  --privacy private
```

**Required env vars** (add as GitHub Actions secrets or export locally):

```
YT_CLIENT_ID       # OAuth2 client ID from Google Cloud Console
YT_CLIENT_SECRET   # OAuth2 client secret
YT_REFRESH_TOKEN   # Long-lived refresh token (see below)
```

**Optional:**

```
YT_CHANNEL_ID      # Target channel (defaults to authenticated user's channel)
YT_CHUNK_SIZE_MB   # Default chunk size if --chunk-size-mb is omitted
YT_UPLOAD_MAX_RETRIES
```

### `scripts/video/verify.js`

ffprobe wrapper — validates codec, resolution, streams, and produces sha256 receipt.

```bash
node scripts/video/verify.js --file path/to/video.mp4 --out verify-receipt.json
```

Exit 0 = all checks pass. Exit 1 = warnings (audio/video codec issues). Exit 2 = error.

### `scripts/video/quality_gate.js`

Runs deeper pre-upload checks: stream validity, codec sanity, audio/video duration match, black frames, frozen frames, end silence, SRT ending, thumbnail size, and chapter syntax.

```bash
node scripts/video/quality_gate.js \
  --file path/to/video.mp4 \
  --srt path/to/captions.srt \
  --thumbnail path/to/thumb.jpg \
  --metadata youtube-metadata.json \
  --out quality-gate.json
```

Story videos should run the stricter story gate. This verifies the upload package has captions, YouTube chapters, a CTA/next-chapter treatment, final captions near the media ending, sentence-ending punctuation, and optional source-text final-word alignment.

```bash
node scripts/video/quality_gate.js \
  --file path/to/story.mp4 \
  --srt path/to/captions.srt \
  --metadata youtube-metadata.json \
  --source-text path/to/manuscript.md \
  --story \
  --out quality-gate.json
```

The report includes `summary.readinessScore` and `summary.storyReady`. A story package is not upload-ready unless `storyReady` is true.

### `scripts/video/story_package.js`

One-command local packaging for story uploads. It builds YouTube metadata, runs the strict story quality gate, and writes the final upload manifest.

```bash
node scripts/video/story_package.js \
  --video path/to/story.mp4 \
  --title "Story Chapter 1" \
  --description-file path/to/description.md \
  --chapters path/to/chapters.json \
  --srt path/to/captions.srt \
  --source-text path/to/manuscript.md \
  --tags "AetherMoore,audiobook,story" \
  --out-dir artifacts/youtube/story-chapter-1
```

### `scripts/video/package_manifest.js`

Builds the upload package manifest from the verified assets.

```bash
node scripts/video/package_manifest.js \
  --video path/to/video.mp4 \
  --srt path/to/captions.srt \
  --thumbnail path/to/thumb.jpg \
  --metadata youtube-metadata.json \
  --quality-report quality-gate.json \
  --out video-package.json
```

## Getting a refresh token

1. Google Cloud Console → APIs & Services → Credentials → Create OAuth 2.0 Client ID (type: Desktop)
2. Enable YouTube Data API v3
3. Use OAuth Playground or a local script to exchange for a refresh token with scope:
   `https://www.googleapis.com/auth/youtube.upload`
4. Add `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` as GitHub secrets:
   Settings → Secrets and variables → Actions → New repository secret

## CI workflow

`.github/workflows/video-upload.yml` — trigger via `workflow_dispatch` in the GitHub UI.

Runs: ffprobe verify → YouTube metadata package → quality gate → video package manifest → GeoSeal safety check (dry-run) → chunked resumable upload from manifest → artifact receipt.
