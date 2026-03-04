---
name: scbe-article-posting
description: Write, format, and publish long-form articles across 12+ platforms from SCBE-AETHERMOORE source material. Handles platform-specific formatting (Medium, LinkedIn, Dev.to, Reddit, LessWrong, Hacker News, Twitter/X threads, arXiv preprints, HuggingFace model cards, GitHub Discussions/Gists, Bluesky, Mastodon). Use when asked to "post articles", "write marketing content", "publish to Medium/LinkedIn/etc", "create a thread", or "promote SCBE".
---

# SCBE Article Posting

End-to-end skill for writing and publishing SCBE-AETHERMOORE articles across platforms.

## Workflow

### Phase 1: Source Material

Read existing content assets before writing anything:

```
C:\Users\issda\SCBE-AETHERMOORE\docs\M5_MESH_PRODUCT_SERVICE_BLUEPRINT.md
C:\Users\issda\SCBE-AETHERMOORE\docs\M6_SEED_MULTI_NODAL_NETWORK_SPEC.md
C:\Users\issda\SCBE-AETHERMOORE\docs\plans\2026-02-26-geoseed-network-design.md
C:\Users\issda\SCBE-AETHERMOORE\docs\patent\PATENT_6_HARMONIC_CRYPTOGRAPHY.md
C:\Users\issda\SCBE-AETHERMOORE\content\articles\*  (existing articles)
```

Key topics to draw from:
- **Geometric Skull / PHDM**: H(d,R) = R^(d^2), Poincare ball zones, 16 polyhedra
- **Sacred Tongues**: KO/AV/RU/CA/UM/DR, phi-weighted, neurotransmitter analogs
- **GeoSeed Network**: Cl(6,0) Clifford algebra, icosahedral grids, 642 vertices/grid
- **Harmonic Cryptography**: Pythagorean comma, polyrhythmic cipher rings, voice leading
- **Browser-as-a-Service**: Governed browser swarm, tongue-weighted Dijkstra routing
- **M5 Mesh Foundry**: Sellable data-governance product ($6,500 launch, $2,500/mo)
- **14-Layer Pipeline**: L1-L14 with 5 quantum axioms
- **Post-Quantum Crypto**: ML-KEM-768, ML-DSA-65, AES-256-GCM

### Phase 2: Write Articles

Save all articles to `C:\Users\issda\SCBE-AETHERMOORE\content\articles\`.

Naming convention: `{platform}_{topic_slug}.md`

#### Platform Format Rules

| Platform | Format | Length | Key Rules |
|----------|--------|--------|-----------|
| **Medium** | Markdown, narrative | 1500-3000 words | Hook title, subheadings, code blocks, no frontmatter |
| **LinkedIn** | Professional tone | 800-1500 words | Business value focus, CISO/CTO audience, pricing OK |
| **Dev.to** | Markdown + frontmatter | 1000-2500 words | Tags (max 4), code examples, tutorial style |
| **Twitter/X** | Thread format | 10-15 tweets | Number format "1/N", 280 char limit, hook first tweet |
| **Reddit** | Self-post markdown | 500-2000 words | TL;DR at top, "Looking For" section, limitations |
| **LessWrong** | Epistemic status header | 1000-3000 words | "What This Is Not" section, formal, falsifiable claims |
| **Hacker News** | Show HN format | 500-1500 words | Technical focus, no hype, link to code |
| **arXiv** | Academic preprint | 3000-6000 words | Abstract, sections, references, ORCID: 0009-0002-3936-9369 |
| **HuggingFace** | Model card | 500-1500 words | YAML frontmatter with tags, BibTeX citation, usage code |
| **GitHub Discussion** | Announcement/Ideas | 300-1000 words | Link to related gists/repos/HF |
| **GitHub Gist** | Full article as .md | Any length | Public, descriptive title |
| **Bluesky** | Short posts | 300 char limit | Link to full article, hashtags |
| **Mastodon** | Short posts | 500 char limit | Hashtags, CW for technical |

### Phase 3: Publish

#### API-Based (Preferred — Fast, Reliable)

**HuggingFace** (authenticated via `huggingface_hub`):
```python
from huggingface_hub import HfApi, create_repo
api = HfApi()
create_repo("issdandavis/geoseed-network", repo_type="model", exist_ok=True)
api.upload_file(
    path_or_fileobj=content.encode("utf-8"),
    path_in_repo="README.md",
    repo_id="issdandavis/geoseed-network",
    repo_type="model",
    commit_message="Update model card"
)
```

**GitHub Gists** (authenticated via `gh` CLI):
```bash
gh gist create content/articles/article.md --desc "Title" --public
```

**GitHub Discussions** (authenticated via `gh` CLI):
```bash
# Get repo ID + category IDs first:
gh api graphql -f query='{ repository(owner:"issdandavis", name:"SCBE-AETHERMOORE") { id, discussionCategories(first:10) { nodes { id name } } } }'

# Create discussion:
gh api graphql -f query='mutation { createDiscussion(input: { repositoryId:"R_kgDOQ7csuQ", categoryId:"DIC_kwDOQ7csuc4C2BLl", title:"...", body:"..." }) { discussion { url } } }'
```

**Discussion category IDs** (SCBE-AETHERMOORE):
- Announcements: `DIC_kwDOQ7csuc4C2BLl`
- General: `DIC_kwDOQ7csuc4C2BLm`
- Ideas: `DIC_kwDOQ7csuc4C2BLo`
- Q&A: `DIC_kwDOQ7csuc4C2BLn`
- Show and tell: `DIC_kwDOQ7csuc4C2BLp`
- Polls: `DIC_kwDOQ7csuc4C2BLq`

**Dev.to** (via browser CSRF or API key):
```python
# If logged in via browser, use CSRF approach:
fetch('/articles', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf_token},
    body: JSON.stringify({article: {title, body_markdown, tags, published: true}})
})
# If API key available (DEVTO_API_KEY env var):
requests.post("https://dev.to/api/articles", headers={"api-key": key}, json={...})
```

#### Script-Based (Credential-Dependent)

Publishing scripts at `scripts/publish/`:

| Script | Env Vars Needed |
|--------|----------------|
| `post_to_reddit.py` | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` |
| `post_to_medium.py` | `MEDIUM_TOKEN` |
| `post_to_twitter.py` | `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` |
| `post_to_linkedin.py` | `LINKEDIN_ACCESS_TOKEN` |
| `post_to_hackernews.py` | `HN_USERNAME`, `HN_PASSWORD` |
| `post_all.py` | Runs all above, skips missing creds |

```bash
# Check what's configured:
python scripts/publish/post_all.py --dry-run

# Post to everything:
python scripts/publish/post_all.py

# Post to one platform:
python scripts/publish/post_all.py --only medium
```

#### Browser-Based (Fallback)

Use `mcp__claude-in-chrome__*` tools when:
- No API credentials available
- Platform has no API (LessWrong, some Reddit subs)
- Need to log in interactively

**Important browser lessons learned:**
- Medium's contentEditable editor does NOT sync with React state via `fill()` or `execCommand`. Use Medium's API instead (`MEDIUM_TOKEN`).
- Dev.to's textarea loses formatting when filled via Playwright. Use the CSRF/fetch approach instead.
- LinkedIn requires email/password login — ask user for credentials or use API token.
- Always try API first, browser second.

### Phase 4: Track & Commit

After publishing:
1. `git add content/articles/` and commit
2. `git push origin <branch>`
3. Log what was published where in a summary

## Author Info

- **Author**: Issac Daniel Davis
- **GitHub**: issdandavis
- **HuggingFace**: issdandavis
- **ORCID**: 0009-0002-3936-9369
- **Location**: Port Angeles, WA
- **Patent**: USPTO #63/961,403

## Standard Links (Include in Every Article)

```
Code: https://github.com/issdandavis/SCBE-AETHERMOORE
Dataset: https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data
Model: https://huggingface.co/issdandavis/geoseed-network
Patent: USPTO #63/961,403 (provisional)
```

## Already Published

Track what's been published to avoid duplicates:

| Platform | Article | URL | Date |
|----------|---------|-----|------|
| Dev.to | Browser-as-a-Service | /issdandavis/building-a-governed-browser-as-a-service-... (ID 3302539) | 2026-03-02 |
| HuggingFace | GeoSeed Model Card | https://huggingface.co/issdandavis/geoseed-network | 2026-03-02 |
| GitHub Gist | arXiv Preprint | https://gist.github.com/issdandavis/0f873ff5443ba6d2b9e16e2e2bbeb490 | 2026-03-02 |
| GitHub Gist | Harmonic Crypto | https://gist.github.com/issdandavis/6ea7ae9ef4b54e36dc88e51c0d7fb4bf | 2026-03-02 |
| GitHub Gist | LessWrong Article | https://gist.github.com/issdandavis/af6015ab3cfcdad304473e9ae0feafa6 | 2026-03-02 |
| GitHub Gist | Reddit Article | https://gist.github.com/issdandavis/b5c7e445f49bd755815dde3791ce3786 | 2026-03-02 |
| GitHub Discussion | Geometric Containment (Ideas) | https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/338 | 2026-03-02 |
| GitHub Discussion | GeoSeed Announcement | https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/339 | 2026-03-02 |
