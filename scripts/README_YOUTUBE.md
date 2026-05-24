YouTube automation scripts

Files:

- scripts/video/verify.js — run ffprobe and produce a verification JSON receipt.
- scripts/video/quality_gate.js — run upload-readiness checks, including story-mode completion checks.
- scripts/video/story_package.js — one command to build metadata, run the story quality gate, and emit a manifest.
- scripts/youtube/upload.js — perform a resumable upload to YouTube using OAuth2 refresh token and produce a receipt JSON.

Usage (local):

1. Install ffmpeg and mediainfo.
2. Set environment variables (see scripts/.env.sample) or export YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN, YT_CHANNEL_ID.
3. Verify:
   node scripts/video/verify.js --file ./out/video.mp4 --out ./verify.json
4. Package a story video before upload:
   node scripts/video/story_package.js --video ./out/video.mp4 --title "Story Chapter" --description-file ./out/description.md --chapters ./out/chapters.json --srt ./out/captions.srt --source-text ./manuscript/chapter.md --tags "AetherMoore,audiobook,story" --out-dir ./out/package
5. Upload the verified manifest:
   node scripts/youtube/upload.js --manifest ./out/package/video-package.json --privacy private --chunk-size-mb 8 --receipt-out ./yt-receipt.json
6. Upload a raw file only when you are deliberately bypassing the package gate:
   node scripts/youtube/upload.js --file ./out/video.mp4 --title "My video" --description "desc" --privacy private --chunk-size-mb 8 --receipt-out ./yt-receipt.json

Notes:

- The upload script exchanges the refresh token for an access token using Google's OAuth2 token endpoint, initiates a resumable upload, then performs chunked PUTs using the returned upload URL. On retryable failures it asks YouTube which byte range is committed and resumes from there.
- The GitHub Actions workflow .github/workflows/video-upload.yml runs verify, story quality gate, manifest packaging, and upload using repository secrets.
