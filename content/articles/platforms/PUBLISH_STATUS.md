# SCBE Article Publishing Status — 2026-03-17

Article: **How a DnD Campaign Became an AI Governance Framework**
Worldbuilding: **Welcome to Aethermoor: Where Languages Are Architecture**

## POSTED (API)

| Platform | Status | URL |
|---|---|---|
| Dev.to | POSTED | https://dev.to/issdandavis/how-a-dnd-campaign-became-an-ai-governance-framework-25ne |
| GitHub Discussions (tech) | ALREADY EXISTED | (previously posted) |
| GitHub Discussions (worldbuilding) | POSTED | https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/531 |
| HuggingFace (dataset) | POSTED | https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data/discussions/2 |
| HuggingFace (phdm model) | POSTED | https://huggingface.co/issdandavis/phdm-21d-embedding/discussions/2 |
| HuggingFace (spiralverse model) | POSTED | https://huggingface.co/issdandavis/spiralverse-ai-federated-v1/discussions/1 |
| Telegram (owner notification) | SENT | Direct message to PollyBot owner |

## NEEDS MANUAL POSTING (formatted versions saved)

| Platform | File | Notes |
|---|---|---|
| X/Twitter | `platforms/x_thread_dnd_to_governance.md` | OAuth 1.0a 401 -- tokens need refresh. Run `post_to_x.py --auth` to re-authorize |
| Reddit r/MachineLearning | `platforms/reddit_machinelearning.md` | No Reddit API token. Post with [R] tag. |
| Reddit r/worldbuilding | `platforms/reddit_worldbuilding.md` | Creative post, not tech. |
| Reddit r/isekai + r/litrpg | `platforms/reddit_isekai_litrpg.md` | Fiction angle, references book. |
| Reddit r/artificial | `platforms/reddit_artificial.md` | Accessible version for general AI audience. |
| Reddit r/gamedev | `platforms/reddit_gamedev.md` | Focuses on emergent linguistics from AI games. |
| LinkedIn | `platforms/linkedin_article.md` | No LinkedIn API token. Enterprise/compliance angle. |
| Medium | `platforms/medium_article.md` | No Medium API token. Full article with frontmatter. |
| Bluesky | `platforms/bluesky_thread.md` | No Bluesky token. 5-post thread format. |
| Mastodon | `platforms/mastodon_thread.md` | No Mastodon token. 3-post thread with hashtags. |
| Substack | `platforms/substack_article.md` | Email/password only, no API. Newsletter format. |
| World Anvil | `platforms/world_anvil_aethermoor.md` | User token exists but app key is REPLACE_ME. Worldbuilding content. |

## TOKEN STATUS

| Service | Token Status | Action Needed |
|---|---|---|
| X/Twitter | OAuth 1.0a expired (401) | Run `post_to_x.py --auth` |
| Reddit | No token | Create app at reddit.com/prefs/apps |
| LinkedIn | No token | Create app at linkedin.com/developers |
| Medium | No token | Get integration token at medium.com/me/settings |
| Bluesky | No token | Use app password from bsky.app/settings |
| Mastodon | No token | Create app on your instance |
| Slack | Token expired (12hr limit) | Re-authenticate |
| Discord | Bot not in guilds | Add bot to a server |
| World Anvil | App key pending | Request at worldanvil.com/api/auth/key |
| Substack | Email/password only | No REST API available |

## FILES CREATED

### Platform-formatted articles
- `content/articles/platforms/x_thread_dnd_to_governance.md`
- `content/articles/platforms/reddit_machinelearning.md`
- `content/articles/platforms/reddit_worldbuilding.md`
- `content/articles/platforms/reddit_isekai_litrpg.md`
- `content/articles/platforms/reddit_artificial.md`
- `content/articles/platforms/reddit_gamedev.md`
- `content/articles/platforms/linkedin_article.md`
- `content/articles/platforms/medium_article.md`
- `content/articles/platforms/bluesky_thread.md`
- `content/articles/platforms/mastodon_thread.md`
- `content/articles/platforms/substack_article.md`
- `content/articles/platforms/huggingface_discussion.md`
- `content/articles/platforms/world_anvil_aethermoor.md`

### New articles
- `content/articles/2026-03-17-welcome-to-aethermoor-worldbuilding.md` (creative worldbuilding post)

---

# SCBE Article Publishing Status — 2026-04-01

Article: **The First Agent Product Surface Is a Local MCP**

## POSTED (API)

| Platform | Status | URL |
|---|---|---|
| GitHub Discussions (tech) | POSTED | https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/912 |
| HuggingFace (phdm model) | POSTED | https://huggingface.co/issdandavis/phdm-21d-embedding/discussions/5 |
| Bluesky | POSTED | https://bsky.app/profile/issdandavis.bsky.social/post/3miieoqm7gp25 |

## STAGED / READY

| Platform | File | Notes |
|---|---|---|
| Medium | `content/articles/medium_2026-04-01-local-mcp-operator-surface.md` | Full article is formatted and ready, but `MEDIUM_TOKEN` is missing. |
| Substack | `content/articles/substack_2026-04-01-local-mcp-operator-surface.md` | Newsletter version is ready. Repo has no Substack API publisher. |
| LinkedIn | `content/articles/linkedin_2026-04-01-local-mcp-operator-surface.md` | Short professional version is ready for manual posting. |
| Dev.to | `content/articles/devto_2026-04-01-local-mcp-operator-surface.md` | Article is ready, but `DEVTO_API_KEY` is still `REPLACE_ME`. |

## BLOCKERS

| Platform | Blocker |
|---|---|
| Dev.to | No live API key configured. |
| Medium | No live integration token configured. |
| Substack | No repo-native API lane; manual or browser flow needed. |

## FILES CREATED

- `content/articles/research/2026-04-01-local-mcp-operator-surface.md`
- `content/articles/research/2026-04-01-source-roots-stop-agent-drift.md`
- `content/articles/devto_2026-04-01-local-mcp-operator-surface.md`
- `content/articles/medium_2026-04-01-local-mcp-operator-surface.md`
- `content/articles/substack_2026-04-01-local-mcp-operator-surface.md`
- `content/articles/linkedin_2026-04-01-local-mcp-operator-surface.md`
- `content/articles/huggingface_2026-04-01-local-mcp-operator-surface.md`
