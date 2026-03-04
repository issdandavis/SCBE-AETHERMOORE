# World Anvil Integration

The backend exposes authenticated routes for exploring your World Anvil content with an API key-only flow—no OAuth setup required. Add the `WORLD_ANVIL_API_KEY` secret from your World Anvil account before calling any endpoints.

## What you can do today
- Read-only navigation: fetch worlds, articles, categories, maps, and timelines.
- Search articles within a world using the built-in search endpoint.
- Check API connectivity and pull the account profile tied to the API key.

If you need automation or multi-system fan-out, pair these routes with Pipedream using the recipes in [`docs/PIPEDREAM_WORLD_ANVIL_WORKFLOWS.md`](./PIPEDREAM_WORLD_ANVIL_WORKFLOWS.md).

## Checking connectivity
- `GET /api/world-anvil/status` → `{ connected: boolean }`
- `GET /api/world-anvil/user` → returns the profile tied to the API key

## World navigation
- `GET /api/world-anvil/worlds` → list worlds for the account
- `GET /api/world-anvil/world/:worldId` → fetch world metadata
- `GET /api/world-anvil/world/:worldId/articles` → list articles (supports `limit` & `offset`)
- `GET /api/world-anvil/article/:articleId` → fetch an article
- `GET /api/world-anvil/world/:worldId/categories` → list categories
- `GET /api/world-anvil/world/:worldId/maps` → list maps
- `GET /api/world-anvil/world/:worldId/timelines` → list timelines
- `GET /api/world-anvil/timeline/:timelineId` → fetch a timeline
- `GET /api/world-anvil/world/:worldId/search?q=term` → search articles within a world

All routes require a signed-in session and are rate limited via the shared API limiter.
