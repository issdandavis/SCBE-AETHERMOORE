---
name: scbe-article-posting
description: Publish articles and content across all platforms — GitHub Discussions, Dev.to, X/Twitter, Buffer, YouTube, and more. Use when posting, scheduling, or managing content distribution for SCBE/Aethermoore.
---

# SCBE Article Posting

Publish governed content across all distribution channels from the terminal.

## Quick Post Commands

One-liner commands for each platform:

```bash
# GitHub Discussions (primary — 40+ articles live)
python scripts/publish/publish_discussions.py --file content/articles/YOUR_ARTICLE.md

# X/Twitter (OAuth 2.0 PKCE)
python scripts/publish/post_to_x.py --text "Your tweet text here"
python scripts/publish/post_to_x.py --thread content/articles/x_thread_FILE.md

# Buffer (scheduled multi-platform)
python scripts/publish/post_to_buffer.py --file content/articles/YOUR_ARTICLE.md

# All platforms at once (governed pipeline)
python scripts/publish/post_all.py --file content/articles/YOUR_ARTICLE.md

# YouTube (video from article — TTS + slides)
python scripts/publish/article_to_video.py --input content/articles/YOUR_ARTICLE.md --output artifacts/youtube/
python scripts/publish/post_to_youtube.py --file artifacts/youtube/YOUR_VIDEO.mp4 --title "Title" --privacy unlisted

# HYDRA content pipeline (5-stage governed conveyor)
python -m hydra content scan      # Scan for new content
python -m hydra content stage     # Stage for review
python -m hydra content review    # Run QA gates
python -m hydra content approve   # Approve passing content
python -m hydra content publish   # Publish approved content
python -m hydra content stats     # View pipeline stats
```

## Content Pipeline (HYDRA 5-Stage)

```
Scan -> Stage -> Review (QA gate) -> Approve -> Publish
```

State persists at `artifacts/content_pipeline/pipeline_state.json`.
QA gate: `scripts/publish/content_qa.py` (checks length, citations, formatting, SEO).

## SEO Best Practices Checklist

Run through this checklist before publishing every article:

### Title and Headlines
- [ ] Title is 50-60 characters (max 70 for search display)
- [ ] Title contains the primary keyword near the front
- [ ] Title is specific and promises a clear takeaway
- [ ] H2/H3 subheadings use secondary keywords naturally

### Meta and Open Graph
- [ ] Meta description is 150-160 characters with primary keyword
- [ ] `og:title`, `og:description`, `og:image` tags are set (1200x630 image)
- [ ] Twitter card type is `summary_large_image`
- [ ] Canonical URL is set if cross-posting

### Content Structure
- [ ] First paragraph contains the primary keyword within the first 100 words
- [ ] Article is at least 800 words (1500+ for pillar content)
- [ ] Includes at least 2-3 internal links to other SCBE content
- [ ] Includes at least 1-2 external authoritative links (arXiv, docs, standards)
- [ ] Code blocks have language annotations (```python, ```typescript)
- [ ] Images have descriptive alt text

### Keywords and Readability
- [ ] Primary keyword appears 3-5 times naturally (not stuffed)
- [ ] Secondary keywords appear 1-2 times each
- [ ] Sentences average under 25 words
- [ ] Paragraphs are 2-4 sentences max
- [ ] Uses bullet points or numbered lists for scanability

### Technical SEO
- [ ] URL slug is short, lowercase, hyphenated (e.g., `poincare-cost-scaling`)
- [ ] No orphan pages — article is linked from at least one index/hub page
- [ ] Published date and author are machine-readable (JSON-LD or front matter)
- [ ] No broken links (run `scripts/publish/content_qa.py` to check)

### Platform-Specific Notes

| Platform | Key SEO Factor |
|----------|---------------|
| GitHub Discussions | Use Discussion category labels; first line is indexed as summary |
| Dev.to | Set `canonical_url` to your primary URL; use 3-4 tags max |
| X/Twitter | First tweet of thread carries all the weight; include image |
| YouTube | Title keyword in first 3 words; description first 2 lines matter |
| Medium | Subtitle field is the meta description; 5 tags max |
| Substack | Subject line is the SEO title; preview text is meta description |

## Article Source Locations

| Location | Content Type |
|----------|-------------|
| `content/articles/` | Markdown articles ready for publishing |
| `content/articles/x_thread_*.md` | X/Twitter thread formatted posts |
| `docs/research/` | Research notes (convert to articles before publishing) |
| `artifacts/content_pipeline/` | Pipeline state and QA reports |

## Key Files

| File | Purpose |
|------|---------|
| `scripts/publish/post_all.py` | Multi-platform publisher |
| `scripts/publish/publish_discussions.py` | GitHub Discussions publisher |
| `scripts/publish/post_to_x.py` | X/Twitter OAuth 2.0 publisher |
| `scripts/publish/post_to_buffer.py` | Buffer scheduled posting |
| `scripts/publish/content_qa.py` | QA gate (38+ article checks) |
| `scripts/publish/enrich_from_arxiv.py` | Auto-add arXiv citations to fix QA failures |
| `hydra/content_pipeline.py` | 5-stage governed conveyor |
| `artifacts/content_pipeline/pipeline_state.json` | Pipeline state |

## Guardrails

1. All articles pass `content_qa.py` before publishing.
2. Cross-posted articles must set `canonical_url` to avoid duplicate content penalties.
3. Never publish API keys, tokens, or secrets in article content.
4. Rate limits: X (300 tweets/3hr), GitHub API (5000/hr), Buffer (per plan).
5. Keep `pipeline_state.json` committed after each publish run for audit trail.
