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

## Getting a refresh token

1. Google Cloud Console → APIs & Services → Credentials → Create OAuth 2.0 Client ID (type: Desktop)
2. Enable YouTube Data API v3
3. Use OAuth Playground or a local script to exchange for a refresh token with scope:
   `https://www.googleapis.com/auth/youtube.upload`
4. Add `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` as GitHub secrets:
   Settings → Secrets and variables → Actions → New repository secret

## CI workflow

`.github/workflows/video-upload.yml` — trigger via `workflow_dispatch` in the GitHub UI.

Runs: ffprobe verify → GeoSeal safety check (dry-run) → chunked resumable upload → artifact receipt.
