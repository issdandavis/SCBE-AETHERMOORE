# Daily Social Updates Runbook

Workflow: `.github/workflows/daily-social-updates.yml`

## What it does

1. Generates daily update posts from recent commit activity.
2. Runs `post_all.py` in dry-run mode and saves evidence.
3. Optionally runs live publish for X + GitHub Discussions.

## Local Commands

```bash
python scripts/publish/generate_daily_system_update.py --json
python scripts/publish/post_all.py --dry-run --only x,github,linkedin --github-glob "YYYY-MM-DD-system-update.md" --github-limit 1
```

## Live Publish Controls

Scheduled live publish is enabled only when repository secret `SCBE_SOCIAL_LIVE`
is set to `true`.

Required X secrets for live X posting:
- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_ACCESS_TOKEN`
- `X_REFRESH_TOKEN`

Manual live run:
- GitHub Actions → `Daily Social Updates` → `Run workflow` with `live_publish=true`.

## Evidence

Each run writes evidence in `artifacts/publish_browser/`.
