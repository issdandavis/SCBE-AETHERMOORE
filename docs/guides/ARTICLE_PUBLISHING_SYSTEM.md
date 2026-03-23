# Article Publishing System

This is the repo-native publishing lane for SCBE research articles.

## What It Does

1. Builds code-backed article campaign packages from canonical research articles.
2. Emits per-site payload files for GitHub, Hugging Face, Dev.to, LinkedIn, Medium, Substack, Reddit, Bluesky, and Mastodon.
3. Runs a local claim gate against explicit source anchors.
4. Emits a dispatch plan and a repo-local Obsidian note.
5. Lets `post_all.py` consume the generated manifest instead of relying only on filename prefixes.

## Main Commands

Build the campaign:

```bash
python scripts/publish/build_research_campaign.py
```

Dry-run the publisher against the generated manifest:

```bash
python scripts/publish/post_all.py --campaign-posts artifacts/publish_campaigns/latest/campaign_posts.json --dry-run
```

Dry-run only the channels with live repo support:

```bash
python scripts/publish/post_all.py --campaign-posts artifacts/publish_campaigns/latest/campaign_posts.json --dry-run --only github,huggingface,devto
```

## Outputs

- `artifacts/publish_campaigns/<campaign_id>/campaign_manifest.json`
- `artifacts/publish_campaigns/<campaign_id>/campaign_posts.json`
- `artifacts/publish_campaigns/<campaign_id>/claim_gate_report.json`
- `artifacts/publish_campaigns/<campaign_id>/dispatch_plan.json`
- `artifacts/publish_campaigns/<campaign_id>/repo_obsidian_note.md`
- `content/articles/platforms/generated/<campaign_id>/...`
- `notes/round-table/2026-03-21-research-publishing-campaign.md`

## Current Live Posting Support

- `github`: supported through `publish_discussions.py`
- `huggingface`: supported through `post_to_huggingface_discussion.py`
- `devto`: supported through `post_to_devto.py`
- `linkedin`, `medium`, `substack`, `reddit`, `bluesky`, `mastodon`: staged payloads only

## Why This Exists

The article lane should not depend on memory, hand-copying, or vague claims. The point of this system is to keep every post tied to:

- a canonical source article
- explicit repo paths
- a claim gate with source anchors
- reproducible payload files
