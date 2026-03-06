# Daily Social Updates Runbook

Workflow: `.github/workflows/daily-social-updates.yml`

## What it does

1. Generates daily update posts from recent commit activity.
2. Runs `post_all.py` in dry-run mode and saves evidence.
3. Optionally runs live publish for X + GitHub Discussions.
4. Prefers Buffer for live X distribution when Buffer credentials are configured.

## Local Commands

```bash
python scripts/publish/generate_daily_system_update.py --json
python scripts/publish/post_all.py --dry-run --only x,github,linkedin --github-glob "YYYY-MM-DD-system-update.md" --github-limit 1
```

## Live Publish Controls

Scheduled live publish is enabled only when repository secret `SCBE_SOCIAL_LIVE`
is set to `true`.

Preferred live social (Buffer) secrets:
- `BUFFER_ACCESS_TOKEN`
- `BUFFER_PROFILE_IDS` (optional, comma-separated profile IDs; if omitted the script tries auto-discovery)

Fallback X secrets for direct X posting:
- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_ACCESS_TOKEN`
- `X_REFRESH_TOKEN`
- OR OAuth 1.0a set:
  - `X_API_KEY`
  - `X_API_SECRET`
  - `X_ACCESS_TOKEN`
  - `X_ACCESS_TOKEN_SECRET`

If `SCBE_SOCIAL_LIVE=true`, live logic is:
1. Publish GitHub Discussions.
2. Publish via Buffer if Buffer secrets are configured.
3. Otherwise, publish direct to X if X secrets are configured.
4. Otherwise, log skip notice.

Manual live run:
- GitHub Actions → `Daily Social Updates` → `Run workflow` with `live_publish=true`.

## Evidence

Each run writes evidence in `artifacts/publish_browser/`.
