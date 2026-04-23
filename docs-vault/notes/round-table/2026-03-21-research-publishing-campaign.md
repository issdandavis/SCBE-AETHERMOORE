# Research Publishing Campaign - March 21, 2026

Campaign id: `research-campaign-20260322T071217Z`

## What shipped
- Articles: 3
- Post packages: 30
- Platforms covered: 9
- Claim gate pass: True
- Claims checked: 100
- Dispatch publish events: 30

## Articles
- `governed-cli-product-surface` :: The Governed CLI Is the Product Surface
  Source: `content/articles/research/2026-03-21-governed-cli-product-surface.md`
  Sites: bluesky, devto, github, huggingface_dataset, huggingface_model, linkedin, mastodon, medium, reddit_machinelearning, substack
- `programmatic-hf-training-lane` :: Programmatic Hugging Face Training Needs a Governed Staging Lane
  Source: `content/articles/research/2026-03-21-programmatic-hf-training-lane.md`
  Sites: bluesky, devto, github, huggingface_dataset, huggingface_model, linkedin, mastodon, medium, reddit_machinelearning, substack
- `protected-corpus-before-training` :: Do Not Train on Raw Ops Logs: Build a Protected Corpus First
  Source: `content/articles/research/2026-03-21-protected-corpus-before-training.md`
  Sites: bluesky, devto, github, huggingface_dataset, huggingface_model, linkedin, mastodon, medium, reddit_machinelearning, substack

## Commands
```bash
python scripts/publish/build_research_campaign.py
python scripts/publish/post_all.py --campaign-posts artifacts/publish_campaigns/latest/campaign_posts.json --dry-run
```

## Why this matters
- The article lane is now tied to real repo sources and explicit anchors.
- Every generated post package can be claim-checked before distribution.
- The dispatch plan is structured enough to feed the publishing autopilot later.
