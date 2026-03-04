# Pipedream workflows for World Anvil

Use these recipes to automate World Anvil data pulls with the existing authenticated API routes. Each step references the backend endpoints under `/api/world-anvil/*`.

> Prerequisites: set `WORLD_ANVIL_API_KEY` in the backend and ensure your session cookie is forwarded to Pipedream HTTP steps (or swap the HTTP steps for the built-in OAuth/session strategy you prefer).

## 1) Manual fetch + AI summary
**Use case:** on-demand endpoint that fetches a world, grabs the latest articles, and summarizes them with OpenAI.

1. **Trigger:** `HTTP` → method `POST`, path `/world-anvil/summarize`.
2. **Fetch world:** `HTTP` step → `GET {{env.BACKEND_URL}}/api/world-anvil/world/{{steps.trigger.event.body.worldId}}`.
3. **Fetch articles:** `HTTP` step → `GET {{env.BACKEND_URL}}/api/world-anvil/world/{{steps.trigger.event.body.worldId}}/articles?limit=20`.
4. **AI summarize:** `OpenAI` action → model `gpt-4o-mini` (or your choice), prompt with the world metadata + article titles to produce a short digest.
5. **Return:** Respond with the AI summary and raw data payloads for debugging.

## 2) Scheduled timeline digest to Slack
**Use case:** nightly digest of timeline updates for a world.

1. **Trigger:** `Scheduler` → daily at your preferred time.
2. **List timelines:** `HTTP` step → `GET {{env.BACKEND_URL}}/api/world-anvil/world/{{params.worldId}}/timelines`.
3. **Loop timelines:** `Code` step (Node.js) to iterate timelines and build a message payload.
4. **Send to Slack:** `Slack` action → post the formatted digest (timeline name, era count, last updated) to your channel.

## 3) Article search webhook
**Use case:** search World Anvil from other systems (e.g., Notion buttons or Discord slash commands).

1. **Trigger:** `HTTP` → method `POST`, path `/world-anvil/search`.
2. **Search:** `HTTP` step → `GET {{env.BACKEND_URL}}/api/world-anvil/world/{{steps.trigger.event.body.worldId}}/search?q={{encodeURIComponent(steps.trigger.event.body.term)}}`.
3. **Return:** Provide the top matches (title, URL, excerpt) to the caller.

### Tips
- Add a `Datastore` step if you want to cache world IDs or store last-run timestamps between workflows.
- Use `env.BACKEND_URL` as a Pipedream environment variable that points to your running backend instance.
- If you need to fan out per-world, attach a `Datastore` of worlds from `/api/world-anvil/worlds` and loop over it in scheduled jobs.
