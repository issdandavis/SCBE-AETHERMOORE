# Nightly Roundup Publish Log — 2026-03-31

## Website
- Added `docs/articles/2026-03-31-nightly-roundup.html`
- Linked roundup from `docs/articles/index.html`
- Added roundup URL to `docs/sitemap.xml`

## Source content
- Generated `content/articles/2026-03-31-system-update.md`
- Generated `content/articles/x_thread_system_update_2026_03_31.md`
- Generated `content/articles/linkedin_system_update_2026_03_31.md`

## Publishing evidence
- GitHub Discussion posted: https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/896
- GitHub evidence: `artifacts/publish_browser/github_discussions_20260331T091005Z.json`
- Bluesky posted: https://bsky.app/profile/issdandavis.bsky.social/post/3midtijmubb22
- Post-all dry-run evidence: `artifacts/publish_browser/post_all_20260331T090822Z.json`

## Remaining blockers
- X live post blocked by missing OAuth session (`python scripts/publish/post_to_x.py --auth`)
- LinkedIn repo lane is content-staged only; no live API publisher in repo
