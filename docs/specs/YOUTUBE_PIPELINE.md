# YouTube Video Pipeline — Operator Runbook

End-to-end pipeline for producing narrated SCBE videos from a Marp slide deck
and uploading them to YouTube.

**Status:** ready 2026-05-09. Tested end-to-end on a 2-slide synthetic deck;
not yet run against a real OAuth flow (that requires you to click "Allow" in
a browser once).

---

## Pieces

| Component | What it is | Where it lives |
|---|---|---|
| `scripts/video/deck_to_video.py` | Marp deck → narrated MP4 | repo |
| `scripts/video/upload_to_youtube.py` | Wrapper around `youtubeuploader` | repo |
| `scripts/video/install_youtube_mcp.ps1` | Register MCP server with Claude Code | repo |
| `youtubeuploader.exe` | Go binary, OAuth + upload | `~/.local/bin/` |
| `ffmpeg.exe` | Video composition | WinGet / PATH |
| `pyttsx3` (Python pkg) | Windows SAPI text-to-speech | pip |
| `client_secrets.json` | Your Google OAuth client secret | `~/.secrets/youtube/` (you put it there) |
| `youtube-data-mcp-server` | npm MCP server for chat-driven uploads | npx-on-demand |

---

## One-time setup (do these once, in order)

### 1. Move your OAuth client secret out of Downloads

Your file currently sits at:
```text
C:\Users\issda\Downloads\client_secret_165664533862-0e9qpk65a50mmtq4n9anbs5jcbe948ei.apps.googleusercontent.com.json
```

Move it to the canonical location and rename it:

```powershell
mkdir -Force "$env:USERPROFILE\.secrets\youtube"
Move-Item `
  "$env:USERPROFILE\Downloads\client_secret_165664533862-0e9qpk65a50mmtq4n9anbs5jcbe948ei.apps.googleusercontent.com.json" `
  "$env:USERPROFILE\.secrets\youtube\client_secrets.json"
```

The classifier blocked Claude from doing this for you — credential moves are
sensitive enough that they require explicit human action. After the move,
the file lives in your home zone (`~/.secrets/youtube/`), outside any git
repo.

### 2. Verify dependencies

```powershell
& "$env:USERPROFILE\.local\bin\youtubeuploader.exe" -h | Select-Object -First 3
ffmpeg -version | Select-Object -First 1
python -c "import pyttsx3; print('pyttsx3 OK')"
```

All three should print without errors. (All three were installed during the
2026-05-09 setup pass.)

### 3. Register the MCP server (so chat can drive uploads)

```powershell
pwsh scripts/video/install_youtube_mcp.ps1
```

This reads your `client_secrets.json`, extracts the client ID + secret, and
registers `youtube-data-mcp-server` as an MCP server in Claude Code. After
running, restart Claude Code and run `claude mcp list` — you should see
`youtube` in the connected servers.

---

## Producing a video from the blueprint deck

```powershell
python scripts/video/deck_to_video.py docs/presentations/SYSTEMS_BLUEPRINT.md `
    --out artifacts/videos/SYSTEMS_BLUEPRINT.mp4
```

What this does, step by step:

1. Parses the deck into 18 slides with their speaker notes
2. Uses Marp to render each slide as a 1920×1080 PNG
3. For each slide, generates voice-over WAV via Windows SAPI (Microsoft David
   default; pass `--voice "...Zira..."` for the female voice)
4. Composites each slide PNG + audio into a per-slide MP4 with ffmpeg
5. Concatenates all 18 segments into a single MP4

Output is written to `artifacts/videos/` which is gitignored.

### Picking a different voice

```powershell
python scripts/video/deck_to_video.py docs/presentations/SYSTEMS_BLUEPRINT.md --list-voices
```

Pass the voice ID you want via `--voice`.

### Speech rate

Default is 180 (Windows SAPI's words-per-minute proxy). For a slower delivery,
try 150. For faster, 220.

```powershell
python scripts/video/deck_to_video.py ... --rate 150
```

---

## Uploading to YouTube

### First time — interactive OAuth

```powershell
python scripts/video/upload_to_youtube.py artifacts/videos/SYSTEMS_BLUEPRINT.mp4 `
    --title "SCBE Systems Blueprint" `
    --description "14-layer governance pipeline walkthrough" `
    --tags "AI safety,governance,SCBE,Aethermoore" `
    --privacy private
```

A browser window will pop up asking you to sign in to your Google account
and grant the YouTube upload scope. Click Allow once. The OAuth refresh
token is cached at `~/.secrets/youtube/request.token` and never asks again.

The default `--privacy` is `private` — even if you forget the flag you
cannot accidentally publish to the world.

### Every subsequent upload

Headless. No browser. Just runs.

### Going public

```powershell
python scripts/video/upload_to_youtube.py artifacts/videos/SYSTEMS_BLUEPRINT.mp4 `
    --title "..." --description "..." --tags "..." `
    --privacy public
```

The script prints a 3-second warning and a chance to Ctrl-C before any
public upload.

---

## Driving from chat (after MCP install)

Once the MCP server is registered and Claude Code restarted, you can drive
uploads from chat:

> "Upload artifacts/videos/SYSTEMS_BLUEPRINT.mp4 to YouTube as private with
> title 'SCBE Systems Blueprint v1' and tags AI safety, governance, SCBE."

Claude will call the youtube-data-mcp-server tools instead of running the
Python script. Same outcome, conversational interface.

The MCP server can also pull metadata, search videos, and (depending on its
exact capabilities) edit titles/descriptions of existing uploads. Run
`claude mcp get youtube` after install to see the tool list.

---

## Quotas and limits

- **YouTube Data API quota:** 10,000 units / day default
- **One upload:** ~1,600 units → about 6 uploads/day at default quota
- **Quota request:** if you need more, file a quota increase via the Google
  Cloud Console — for a personal account this is usually granted on appeal
  with a brief explanation
- **Per-video size:** 256 GB or 12 hours, whichever is less
- **Daily upload limit:** 100 videos / 24 hours (well above quota anyway)

---

## Security model

**The OAuth client secret is the keys to your YouTube channel.** Treat it
like a password.

- Lives at `~/.secrets/youtube/client_secrets.json` (home zone, not in any repo)
- Never committed to git (the `.secrets/` pattern is gitignored even at the
  in-repo path)
- Never echoed to chat or printed in script output
- Stored on-disk in plaintext — if your laptop is compromised, the secret
  is compromised. Rotate it via the Google Cloud Console (APIs & Services
  → Credentials → that OAuth client → Reset secret) if that ever happens
- The OAuth refresh token cached at `~/.secrets/youtube/request.token` is
  scoped to YouTube upload only — it cannot read your Gmail or Drive

If you ever need to revoke access entirely:

1. Google Account → Security → Third-party apps with account access → revoke
2. Delete `~/.secrets/youtube/request.token` (forces fresh OAuth on next run)

---

## Troubleshooting

### "client_secrets.json not found"
Did you do step 1 above? The file must be at
`~/.secrets/youtube/client_secrets.json` (or pass `--client-secrets PATH`).

### "youtubeuploader not in PATH"
The binary is at `~/.local/bin/youtubeuploader.exe`. PowerShell may not have
that on PATH by default. Either add `$env:USERPROFILE\.local\bin` to PATH,
or invoke via the full path.

### "ffmpeg not in PATH"
WinGet should have set it up. If not, run:
```powershell
winget install Gyan.FFmpeg
```
Then restart your shell.

### MCP server doesn't appear after install
Restart Claude Code. The MCP registry is loaded at startup, not live-reloaded.

### Upload fails with "quota exceeded"
You've hit the 10,000-unit daily quota. Either wait 24h or request a quota
increase in the Google Cloud Console.

### TTS voice sounds robotic
Windows SAPI voices are basic but free. For better quality:
- ElevenLabs (paid; better voices) — would require swapping pyttsx3 for
  the elevenlabs SDK in `deck_to_video.py`
- Piper (free, local, requires a 50MB voice model download) — same swap
- Recording your own voice and using `--audio path/to/voiceover.wav` (not
  yet implemented; would be a 30-line addition to `deck_to_video.py`)

---

## Files

- `scripts/video/deck_to_video.py` — production
- `scripts/video/upload_to_youtube.py` — upload wrapper
- `scripts/video/install_youtube_mcp.ps1` — MCP registration helper
- `docs/presentations/SYSTEMS_BLUEPRINT.md` — the Marp deck source
- `docs/presentations/build/` — rendered HTML/PDF/PPTX (gitignored)
- `artifacts/videos/` — produced MP4s (gitignored)
- `~/.secrets/youtube/client_secrets.json` — OAuth client secret (you place
  it there, never in repo)
- `~/.secrets/youtube/request.token` — OAuth refresh token cache (auto-created
  on first OAuth)
